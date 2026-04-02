"""
core/audio_engine.py
────────────────────
Thành viên 1 – Audio Engine & File Handler  (v2 – sounddevice streaming)

Kiến trúc mới:
  - soundfile.read()  → load toàn bộ audio thành numpy array
  - sounddevice.OutputStream + callback → phát từng chunk ~10ms
  - Trong callback: chunk → EffectsChain.process() → volume → loa
  - Seek: chỉ cần di chuyển con trỏ _pos (sample index)
  - Pause/Resume: dừng/khởi động lại stream
  - Tempo: đọc nhiều/ít mẫu hơn mỗi chunk rồi resample → thay đổi tốc độ
"""

import threading
import numpy as np
import soundfile as sf

try:
    import sounddevice as sd
    SD_AVAILABLE = True
except ImportError:
    SD_AVAILABLE = False
    print("[AudioEngine] sounddevice không tìm thấy! Chạy: pip install sounddevice")


CHUNK_SIZE = 2048   # số mẫu mỗi callback (~46ms ở 44100Hz)


class AudioEngine:
    """
    Phát audio theo từng chunk thông qua sounddevice.OutputStream.
    Mỗi chunk đi qua EffectsChain trước khi ra loa → EQ/Filter/Echo/Reverb hoạt động.

    Attributes
    ----------
    deck_id      : str          – "A" hoặc "B"
    file_path    : str          – đường dẫn file đang load
    is_playing   : bool         – đang phát (không phải paused)
    is_paused    : bool         – đang tạm dừng
    volume       : float        – âm lượng tổng 0.0 → 1.0
    speed_ratio  : float        – tốc độ phát (1.0=bình thường, 1.2=nhanh hơn 20%)
    duration     : float        – tổng thời lượng (giây)
    waveform     : np.ndarray   – waveform mono float32 để vẽ
    sample_rate  : int          – sample rate
    effects_chain: EffectsChain – chuỗi effects áp dụng real-time
    """

    def __init__(self, deck_id: str = "A"):
        self.deck_id = deck_id
        self.file_path: str = ""
        self.is_playing: bool = False
        self.is_paused: bool = False
        self._volume: float = 1.0
        self.speed_ratio: float = 1.0   # 0.5 → 2.0
        self.duration: float = 0.0
        self.sample_rate: int = 44100
        self.waveform: np.ndarray = np.array([])

        # Dữ liệu audio đầy đủ [N_samples, 2_channels]
        self._audio_data: np.ndarray | None = None
        # Con trỏ vị trí hiện tại (sample index)
        self._pos: int = 0

        # sounddevice stream
        self._stream: "sd.OutputStream | None" = None

        # Lock bảo vệ _pos và _audio_data khỏi race condition
        self._lock = threading.Lock()

        # Effects chain (được gán từ bên ngoài qua set_effects_chain)
        self.effects_chain = None

        # Tap callback nhận chunk output sau khi xử lý (deck_id, chunk)
        self.output_tap = None

        # Callback khi track kết thúc tự nhiên
        self.on_track_end = None

    # ── Load ─────────────────────────────────────────────────────────────────

    def load(self, file_path: str) -> bool:
        """
        Load file âm thanh vào bộ nhớ.
        Hỗ trợ: WAV, FLAC, OGG, AIFF (và MP3 nếu có ffmpeg).
        Trả về True nếu thành công.
        """
        try:
            self.stop()
            self.file_path = file_path

            # Đọc toàn bộ file vào numpy array
            data, self.sample_rate = sf.read(file_path, always_2d=True, dtype="float32")

            # Đảm bảo stereo (2 kênh)
            if data.shape[1] == 1:
                data = np.concatenate([data, data], axis=1)
            elif data.shape[1] > 2:
                data = data[:, :2]

            self._audio_data = data.astype(np.float32)
            self.duration = len(data) / self.sample_rate
            self.waveform = data.mean(axis=1).astype(np.float32)
            self._pos = 0

            # Reset trạng thái filter trong effects_chain (tránh artifact)
            if self.effects_chain is not None:
                self.effects_chain.reset_state()

            return True

        except Exception as exc:
            print(f"[AudioEngine-{self.deck_id}] Lỗi load: {exc}")
            self._audio_data = None
            self.duration = 0.0
            self.waveform = np.array([])
            return False

    # ── Playback controls ────────────────────────────────────────────────────

    def play(self):
        """
        Phát hoặc resume nhạc.
        Nếu đang paused → resume (giữ vị trí).
        Nếu chưa phát   → play từ vị trí _pos hiện tại.
        """
        if not SD_AVAILABLE or self._audio_data is None:
            return
        if self.is_playing:
            return

        self.is_playing = True
        self.is_paused = False
        self._start_stream()

    def pause(self):
        """Tạm dừng, giữ vị trí hiện tại."""
        if not self.is_playing:
            return
        self.is_playing = False
        self.is_paused = True
        self._stop_stream()

    def stop(self):
        """Dừng và reset về đầu track."""
        self.is_playing = False
        self.is_paused = False
        self._stop_stream()
        with self._lock:
            self._pos = 0

    def toggle_play_pause(self):
        """Chuyển đổi Play/Pause."""
        if self.is_playing:
            self.pause()
        else:
            self.play()

    # ── Seek ─────────────────────────────────────────────────────────────────

    def seek(self, position_sec: float):
        """Nhảy tới vị trí position_sec (giây). Hoạt động cả khi đang phát."""
        if self._audio_data is None:
            return
        position_sec = max(0.0, min(position_sec, self.duration))
        with self._lock:
            self._pos = int(position_sec * self.sample_rate)
            self._pos = min(self._pos, len(self._audio_data) - 1)

        # Reset filter state để tránh artifact khi seek
        if self.effects_chain is not None:
            self.effects_chain.reset_state()

    # ── Position ─────────────────────────────────────────────────────────────

    def get_position(self) -> float:
        """Trả về vị trí phát hiện tại (giây)."""
        if self._audio_data is None or self.sample_rate == 0:
            return 0.0
        return min(self._pos / self.sample_rate, self.duration)

    def get_position_ratio(self) -> float:
        """Trả về vị trí phát dưới dạng tỉ lệ 0.0 → 1.0."""
        if self.duration <= 0:
            return 0.0
        return self.get_position() / self.duration

    # ── Volume ───────────────────────────────────────────────────────────────

    @property
    def volume(self) -> float:
        return self._volume

    @volume.setter
    def volume(self, value: float):
        """Đặt âm lượng 0.0 → 1.0. Áp dụng ngay trong callback tiếp theo."""
        self._volume = max(0.0, min(1.0, value))

    # ── Effects ──────────────────────────────────────────────────────────────

    def set_effects_chain(self, chain):
        """Gắn EffectsChain vào engine. Được gọi từ MainWindow."""
        self.effects_chain = chain

    def is_loaded(self) -> bool:
        return self._audio_data is not None

    # ── Stream management ────────────────────────────────────────────────────

    def _start_stream(self):
        """Khởi động sounddevice OutputStream."""
        if not SD_AVAILABLE:
            return
        self._stop_stream()
        try:
            self._stream = sd.OutputStream(
                samplerate=self.sample_rate,
                channels=2,
                dtype="float32",
                blocksize=CHUNK_SIZE,
                callback=self._audio_callback,
                finished_callback=self._on_stream_finished,
            )
            self._stream.start()
        except Exception as exc:
            print(f"[AudioEngine-{self.deck_id}] Lỗi khởi động stream: {exc}")
            self.is_playing = False

    def _stop_stream(self):
        """Dừng và đóng stream."""
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None

    # ── Audio callback (chạy trong audio thread, ~every 46ms) ────────────────

    def _audio_callback(self, outdata: np.ndarray, frames: int, time_info, status):
        """
        Callback của sounddevice – được gọi mỗi ~46ms.
        Đọc chunk từ _audio_data → áp dụng effects → áp dụng volume → output.
        """
        with self._lock:
            if not self.is_playing or self._audio_data is None:
                outdata[:] = 0
                return

            # ── Tính số mẫu nguồn cần đọc theo speed_ratio ──
            # speed_ratio > 1 → đọc nhiều mẫu hơn → nhạc nhanh
            # speed_ratio < 1 → đọc ít mẫu hơn   → nhạc chậm
            src_frames = max(1, int(frames * self.speed_ratio))

            pos = self._pos
            end = min(pos + src_frames, len(self._audio_data))
            chunk = self._audio_data[pos:end].copy()
            self._pos = end

            # ── Resample chunk về đúng `frames` điểm ──
            if len(chunk) == 0:
                outdata[:] = 0
                return

            if len(chunk) != frames:
                # Linear interpolation để resize chunk
                x_old = np.linspace(0, 1, len(chunk))
                x_new = np.linspace(0, 1, frames)
                resampled = np.zeros((frames, 2), dtype=np.float32)
                resampled[:, 0] = np.interp(x_new, x_old, chunk[:, 0])
                resampled[:, 1] = np.interp(x_new, x_old, chunk[:, 1])
                chunk = resampled

            # ── Hết track ──
            if self._pos >= len(self._audio_data):
                self.is_playing = False
                # Gọi callback trên thread riêng (tránh deadlock)
                if self.on_track_end:
                    threading.Thread(
                        target=self.on_track_end,
                        args=(self.deck_id,),
                        daemon=True,
                    ).start()

        # ── Áp dụng Effects Chain (NGOÀI lock để tránh block) ──
        if self.effects_chain is not None:
            try:
                chunk = self.effects_chain.process(chunk)
            except Exception as exc:
                pass  # Không để lỗi crash audio thread

        # ── Áp dụng volume ──
        chunk = chunk * self._volume

        # ── Clip và output ──
        np.clip(chunk, -1.0, 1.0, out=chunk)
        outdata[:] = chunk

        # ── Tap output cho recorder / monitor ──
        if self.output_tap is not None:
            try:
                self.output_tap(self.deck_id, chunk)
            except Exception:
                pass

    def _on_stream_finished(self):
        """Callback khi stream kết thúc (gọi bởi sounddevice)."""
        pass  # Đã xử lý trong _audio_callback

    # ── Info ──────────────────────────────────────────────────────────────────

    def get_info(self) -> dict:
        import os
        return {
            "deck": self.deck_id,
            "file": os.path.basename(self.file_path) if self.file_path else "—",
            "duration": self.duration,
            "sample_rate": self.sample_rate,
            "is_playing": self.is_playing,
            "is_paused": self.is_paused,
            "volume": self._volume,
            "speed_ratio": self.speed_ratio,
            "position": round(self.get_position(), 2),
        }
