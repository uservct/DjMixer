"""
utils/audio_recorder.py
───────────────────────
Thành viên 6 – Audio Recorder

Ghi âm master output (hỗn hợp của 2 deck) ra file WAV.
Sử dụng soundfile để ghi, PyQt6 QFileDialog để chọn thư mục lưu.
"""

import os
import threading
import time
import queue
import numpy as np
import soundfile as sf
from datetime import datetime


class AudioRecorder:
    """
    Ghi âm output của DJ Mixer ra file WAV.

    Cách dùng:
      recorder = AudioRecorder(sample_rate=44100)
      recorder.start_recording()
      # ... feed dữ liệu qua recorder.write_chunk(data) ...
      recorder.stop_recording()
      # File được lưu tự động
    """

    def __init__(self, sample_rate: int = 44100, channels: int = 2,
                 output_dir: str = "recordings"):
        self.sample_rate = sample_rate
        self.channels = channels
        self.output_dir = output_dir
        self._is_recording: bool = False
        self._output_file: str = ""
        self._writer: sf.SoundFile | None = None
        self._lock = threading.Lock()
        self._chunks_written: int = 0
        self._start_time: float = 0.0
        self._last_write_time: float = 0.0
        self._deck_chunks: dict[str, np.ndarray] = {
            "A": np.zeros((0, channels), dtype=np.float32),
            "B": np.zeros((0, channels), dtype=np.float32),
        }

        os.makedirs(output_dir, exist_ok=True)

    # ── Control ───────────────────────────────────────────────────────────────

    def start_recording(self, file_path: str = "") -> str:
        """
        Bắt đầu ghi âm.
        Nếu file_path rỗng, tự tạo tên file theo thời gian.
        Trả về đường dẫn file sẽ được ghi.
        """
        if self._is_recording:
            return self._output_file

        if not file_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = os.path.join(self.output_dir, f"mix_{timestamp}.wav")

        self._output_file = file_path
        self._writer = sf.SoundFile(
            file_path, mode="w",
            samplerate=self.sample_rate,
            channels=self.channels,
            format="WAV", subtype="PCM_16"
        )
        self._is_recording = True
        self._chunks_written = 0
        self._start_time = time.time()
        self._last_write_time = 0.0
        self._deck_chunks["A"] = np.zeros((0, self.channels), dtype=np.float32)
        self._deck_chunks["B"] = np.zeros((0, self.channels), dtype=np.float32)
        print(f"[Recorder] Bắt đầu ghi: {file_path}")
        return file_path

    def stop_recording(self) -> str:
        """
        Dừng ghi âm và đóng file.
        Trả về đường dẫn file đã ghi.
        """
        if not self._is_recording:
            return ""
        self._is_recording = False
        with self._lock:
            if self._writer:
                self._writer.close()
                self._writer = None
        elapsed = time.time() - self._start_time
        print(f"[Recorder] Dừng ghi. Thời lượng: {elapsed:.1f}s → {self._output_file}")
        return self._output_file

    def write_chunk(self, data: np.ndarray):
        """
        Ghi một chunk audio vào file.
        data: numpy array float32, shape [N] hoặc [N, channels]
        """
        if not self._is_recording or self._writer is None:
            return
        with self._lock:
            # Đảm bảo đúng số kênh
            if data.ndim == 1:
                data = np.stack([data, data], axis=1)
            elif data.shape[1] != self.channels:
                data = data[:, :self.channels]
            # Clip và convert
            data_int = np.clip(data, -1.0, 1.0)
            try:
                self._writer.write(data_int)
                self._chunks_written += 1
            except Exception as exc:  # noqa: BLE001
                print(f"[Recorder] write_chunk lỗi: {exc}")

    def write_deck_chunk(self, deck_id: str, data: np.ndarray):
        """
        Nhận chunk theo từng deck và ghi master mix.
        Dùng time-gate để tránh ghi 2 lần/chu kỳ khi cả 2 deck đều callback.
        """
        if not self._is_recording or self._writer is None:
            return

        chunk = np.asarray(data, dtype=np.float32)
        if chunk.size == 0:
            return

        if chunk.ndim == 1:
            chunk = np.stack([chunk, chunk], axis=1)
        elif chunk.ndim == 2 and chunk.shape[1] != self.channels:
            if chunk.shape[0] == self.channels:
                chunk = chunk.T
            if chunk.shape[1] != self.channels:
                chunk = chunk[:, :1]
                if self.channels == 2:
                    chunk = np.repeat(chunk, 2, axis=1)

        with self._lock:
            key = "A" if str(deck_id).upper().startswith("A") else "B"
            self._deck_chunks[key] = chunk

            # Mỗi callback audio khoảng 46ms (2048/44100).
            # Chỉ ghi tối đa 1 lần mỗi 35ms để tránh bị nhân đôi data.
            now = time.time()
            if self._last_write_time > 0 and (now - self._last_write_time) < 0.035:
                return

            a = self._deck_chunks.get("A")
            b = self._deck_chunks.get("B")

            if a is None or len(a) == 0:
                if b is None or len(b) == 0:
                    return
                a = np.zeros_like(b)
            if b is None or len(b) == 0:
                b = np.zeros_like(a)

            n = min(len(a), len(b))
            if n <= 0:
                return

            mixed = a[:n] + b[:n]
            np.clip(mixed, -1.0, 1.0, out=mixed)

            try:
                self._writer.write(mixed)
                self._chunks_written += 1
                self._last_write_time = now
            except Exception as exc:  # noqa: BLE001
                print(f"[Recorder] write_deck_chunk lỗi: {exc}")

    # ── Status ────────────────────────────────────────────────────────────────

    @property
    def is_recording(self) -> bool:
        return self._is_recording

    def get_elapsed(self) -> float:
        """Trả về số giây đã ghi."""
        if not self._is_recording:
            return 0.0
        return time.time() - self._start_time

    def get_output_file(self) -> str:
        return self._output_file

    def get_chunks_written(self) -> int:
        return self._chunks_written

    def choose_output_path(self, parent=None) -> str:
        """Mở hộp thoại chọn vị trí lưu file ghi âm (PyQt6)."""
        try:
            from PyQt6.QtWidgets import QFileDialog
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_name = os.path.join(self.output_dir, f"mix_{timestamp}.wav")
            file_path, _ = QFileDialog.getSaveFileName(
                parent, "Lưu file ghi âm", default_name,
                "WAV Files (*.wav);;All Files (*)"
            )
            return file_path
        except Exception as exc:  # noqa: BLE001
            print(f"[Recorder] choose_output_path lỗi: {exc}")
            return ""
