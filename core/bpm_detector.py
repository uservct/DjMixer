"""
core/bpm_detector.py
────────────────────
Thành viên 4 – BPM Detection & Tempo Control

Cung cấp:
  - Phát hiện BPM tự động từ numpy audio array bằng librosa
  - Điều chỉnh tempo (time-stretch) không thay đổi pitch
  - Điều chỉnh pitch (pitch-shift) không thay đổi tempo
"""

import numpy as np
from math import gcd

try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False
    print("[BPMDetector] librosa không tìm thấy. BPM detection bị vô hiệu.")

try:
    import soundfile as sf
    SF_AVAILABLE = True
except ImportError:
    SF_AVAILABLE = False

try:
    from scipy.signal import resample_poly
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False


class BPMDetector:
    """
    Phát hiện BPM và điều chỉnh tempo / pitch cho một Deck.

    Attributes
    ----------
    sample_rate : int   – sample rate của audio
    bpm         : float – BPM phát hiện được (0 nếu chưa detect)
    tempo_ratio : float – hệ số tempo (1.0 = bình thường, 1.1 = nhanh hơn 10%)
    pitch_steps : float – số nửa cung pitch shift (0 = không đổi, ±12 = ±1 octave)
    """

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.bpm: float = 0.0
        self.tempo_ratio: float = 1.0
        self.pitch_steps: float = 0.0
        self.max_detect_seconds: int = 90

    def _to_mono_float32(self, audio_data: np.ndarray) -> np.ndarray:
        """Chuẩn hóa audio về mono float32, xử lý cả (n, ch) và (ch, n)."""
        arr = np.asarray(audio_data)
        if arr.size == 0:
            return np.array([], dtype=np.float32)

        if arr.ndim == 1:
            mono = arr
        elif arr.ndim == 2:
            # Thường có dạng (samples, channels). Nếu ngược lại vẫn xử lý được.
            mono = arr.mean(axis=1) if arr.shape[0] >= arr.shape[1] else arr.mean(axis=0)
        else:
            mono = arr.reshape(-1)

        return mono.astype(np.float32, copy=False)

    def _resample_safe(
        self,
        mono: np.ndarray,
        orig_sr: int,
        target_sr: int,
    ) -> np.ndarray:
        """Resample có fallback, tránh lỗi thiếu dependency như resampy/soxr."""
        if orig_sr == target_sr:
            return mono

        # Cố gắng dùng librosa trước
        try:
            return librosa.resample(
                mono,
                orig_sr=orig_sr,
                target_sr=target_sr,
                res_type="kaiser_fast",
            ).astype(np.float32, copy=False)
        except Exception:
            pass

        # Fallback bằng scipy nếu có
        if SCIPY_AVAILABLE:
            g = gcd(orig_sr, target_sr)
            up = target_sr // g
            down = orig_sr // g
            return resample_poly(mono, up, down).astype(np.float32, copy=False)

        # Không thể resample thì trả về gốc để không crash
        return mono

    # ── BPM Detection ─────────────────────────────────────────────────────────

    def detect_bpm(self, audio_data: np.ndarray) -> float:
        """
        Phát hiện BPM từ numpy audio array (mono float32).
        Trả về giá trị BPM (float). Trả về 0.0 nếu không detect được.
        """
        if not LIBROSA_AVAILABLE:
            return 0.0
        try:
            mono = self._to_mono_float32(audio_data)
            if mono.size == 0:
                return 0.0

            # Giới hạn dữ liệu phân tích để tránh treo UI khi bài quá dài.
            max_samples = int(self.sample_rate * self.max_detect_seconds)
            if max_samples > 0 and mono.shape[0] > max_samples:
                mono = mono[:max_samples]

            # Resample xuống 22050Hz để tăng tốc phân tích.
            analysis_sr = 22050
            if self.sample_rate != analysis_sr:
                mono = self._resample_safe(mono, self.sample_rate, analysis_sr)
            else:
                analysis_sr = self.sample_rate

            # Ước lượng tempo từ onset envelope (nhanh, ổn định hơn cho realtime UI).
            onset_env = librosa.onset.onset_strength(y=mono, sr=analysis_sr)
            tempo = librosa.feature.tempo(
                onset_envelope=onset_env,
                sr=analysis_sr,
                aggregate=np.median,
            )
            bpm = float(tempo[0]) if np.size(tempo) else 0.0
            self.bpm = bpm if np.isfinite(bpm) else 0.0
            return self.bpm
        except Exception as exc:  # noqa: BLE001
            print(f"[BPMDetector] detect_bpm lỗi: {exc}")
            return 0.0

    def detect_bpm_from_file(self, file_path: str) -> float:
        """Phát hiện BPM trực tiếp từ file (WAV/FLAC), chỉ đọc một phần đầu file."""
        if not LIBROSA_AVAILABLE or not SF_AVAILABLE:
            return 0.0
        try:
            with sf.SoundFile(file_path) as audio_file:
                self.sample_rate = audio_file.samplerate
                max_frames = int(self.sample_rate * self.max_detect_seconds)
                frames_to_read = min(len(audio_file), max_frames)
                data = audio_file.read(
                    frames=frames_to_read,
                    dtype="float32",
                    always_2d=True,
                )
            return self.detect_bpm(data)
        except Exception as exc:  # noqa: BLE001
            print(f"[BPMDetector] detect_bpm_from_file lỗi: {exc}")
            return 0.0

    # ── Tempo / Pitch ──────────────────────────────────────────────────────────

    def time_stretch(self, audio_data: np.ndarray) -> np.ndarray:
        """
        Thay đổi tempo mà không đổi pitch (time-stretching).
        tempo_ratio = 1.0: không thay đổi
        tempo_ratio = 1.5: nhanh hơn 50%
        tempo_ratio = 0.75: chậm hơn 25%
        """
        if not LIBROSA_AVAILABLE or abs(self.tempo_ratio - 1.0) < 1e-4:
            return audio_data

        try:
            mono = audio_data if audio_data.ndim == 1 else audio_data.mean(axis=1)
            mono = mono.astype(np.float32)
            stretched = librosa.effects.time_stretch(y=mono, rate=self.tempo_ratio)
            # Nếu stereo, nhân đôi kênh
            if audio_data.ndim == 2:
                stretched = np.stack([stretched, stretched], axis=1)
            return stretched.astype(np.float32)
        except Exception as exc:  # noqa: BLE001
            print(f"[BPMDetector] time_stretch lỗi: {exc}")
            return audio_data

    def pitch_shift(self, audio_data: np.ndarray) -> np.ndarray:
        """
        Thay đổi pitch mà không đổi tempo (pitch-shifting).
        pitch_steps: số nửa cung (semitone), +12 = lên 1 octave, -12 = xuống 1 octave.
        """
        if not LIBROSA_AVAILABLE or abs(self.pitch_steps) < 1e-4:
            return audio_data

        try:
            mono = audio_data if audio_data.ndim == 1 else audio_data.mean(axis=1)
            mono = mono.astype(np.float32)
            shifted = librosa.effects.pitch_shift(
                y=mono, sr=self.sample_rate, n_steps=self.pitch_steps
            )
            if audio_data.ndim == 2:
                shifted = np.stack([shifted, shifted], axis=1)
            return shifted.astype(np.float32)
        except Exception as exc:  # noqa: BLE001
            print(f"[BPMDetector] pitch_shift lỗi: {exc}")
            return audio_data

    def process(self, audio_data: np.ndarray) -> np.ndarray:
        """Áp dụng cả time-stretch và pitch-shift liên tiếp."""
        out = self.time_stretch(audio_data)
        out = self.pitch_shift(out)
        return out

    # ── BPM Sync ──────────────────────────────────────────────────────────────

    def get_tempo_ratio_for_target_bpm(self, target_bpm: float) -> float:
        """
        Tính tempo_ratio cần thiết để match target_bpm.
        Ví dụ: track ở 120 BPM, muốn play ở 128 BPM → ratio = 128/120 ≈ 1.067
        """
        if self.bpm <= 0:
            return 1.0
        ratio = target_bpm / self.bpm
        self.tempo_ratio = ratio
        return ratio
