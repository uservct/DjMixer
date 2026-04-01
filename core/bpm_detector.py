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

    # ── BPM Detection ─────────────────────────────────────────────────────────

    def detect_bpm(self, audio_data: np.ndarray) -> float:
        """
        Phát hiện BPM từ numpy audio array (mono float32).
        Trả về giá trị BPM (float). Trả về 0.0 nếu không detect được.
        """
        if not LIBROSA_AVAILABLE:
            return 0.0
        try:
            # librosa beat_track cần mono float32
            mono = audio_data if audio_data.ndim == 1 else audio_data.mean(axis=1)
            mono = mono.astype(np.float32)
            tempo, _ = librosa.beat.beat_track(y=mono, sr=self.sample_rate)
            self.bpm = float(tempo) if np.isscalar(tempo) else float(tempo[0])
            return self.bpm
        except Exception as exc:  # noqa: BLE001
            print(f"[BPMDetector] detect_bpm lỗi: {exc}")
            return 0.0

    def detect_bpm_from_file(self, file_path: str) -> float:
        """Phát hiện BPM trực tiếp từ file (WAV/FLAC)."""
        if not LIBROSA_AVAILABLE or not SF_AVAILABLE:
            return 0.0
        try:
            data, sr = sf.read(file_path, always_2d=True)
            self.sample_rate = sr
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
