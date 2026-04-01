"""
tests/test_bpm_detector.py
──────────────────────────
Unit tests cho BPMDetector (Thành viên 4)
"""

import os
import sys
import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.bpm_detector import BPMDetector


SR = 44100


def make_beat_signal(bpm: float = 120.0, duration_sec: float = 5.0,
                     sr: int = SR) -> np.ndarray:
    """
    Tạo tín hiệu nhịp nhân tạo bằng cách đặt các pulse đều đặn theo BPM.
    """
    n_samples = int(sr * duration_sec)
    signal = np.zeros(n_samples, dtype=np.float32)
    beat_interval = sr * 60.0 / bpm
    i = 0
    while i < n_samples:
        end = min(i + int(sr * 0.02), n_samples)  # pulse 20ms
        signal[i:end] = 1.0
        i += int(beat_interval)
    return signal


class TestBPMDetectorInit:
    def test_default_state(self):
        d = BPMDetector()
        assert d.bpm == pytest.approx(0.0)
        assert d.tempo_ratio == pytest.approx(1.0)
        assert d.pitch_steps == pytest.approx(0.0)

    def test_custom_sample_rate(self):
        d = BPMDetector(sample_rate=22050)
        assert d.sample_rate == 22050


class TestTempoRatio:
    def test_default_no_change(self):
        from core.bpm_detector import LIBROSA_AVAILABLE
        if not LIBROSA_AVAILABLE:
            pytest.skip("librosa không có")
        d = BPMDetector()
        d.tempo_ratio = 1.0
        x = make_beat_signal()
        y = d.time_stretch(x)
        assert len(y) == pytest.approx(len(x), rel=0.05)

    def test_passthrough_without_librosa(self, monkeypatch):
        """Nếu không có librosa, time_stretch trả về input gốc."""
        import core.bpm_detector as bd
        monkeypatch.setattr(bd, "LIBROSA_AVAILABLE", False)
        d = BPMDetector()
        d.tempo_ratio = 1.5
        x = make_beat_signal()
        y = d.time_stretch(x)
        assert np.array_equal(y, x)


class TestPitchShift:
    def test_no_shift(self):
        d = BPMDetector()
        d.pitch_steps = 0.0
        x = make_beat_signal()
        y = d.pitch_shift(x)
        assert np.array_equal(y, x)  # không đổi khi 0 steps

    def test_passthrough_without_librosa(self, monkeypatch):
        import core.bpm_detector as bd
        monkeypatch.setattr(bd, "LIBROSA_AVAILABLE", False)
        d = BPMDetector()
        d.pitch_steps = 2.0
        x = make_beat_signal()
        y = d.pitch_shift(x)
        assert np.array_equal(y, x)


class TestBPMSync:
    def test_get_tempo_ratio_no_bpm(self):
        """Khi bpm=0, ratio trả về 1.0."""
        d = BPMDetector()
        ratio = d.get_tempo_ratio_for_target_bpm(128.0)
        assert ratio == pytest.approx(1.0)

    def test_get_tempo_ratio_calculation(self):
        d = BPMDetector()
        d.bpm = 120.0
        ratio = d.get_tempo_ratio_for_target_bpm(128.0)
        assert ratio == pytest.approx(128.0 / 120.0, rel=1e-4)
        assert d.tempo_ratio == pytest.approx(128.0 / 120.0, rel=1e-4)

    def test_tempo_ratio_increases_bpm(self):
        d = BPMDetector()
        d.bpm = 100.0
        ratio = d.get_tempo_ratio_for_target_bpm(150.0)
        assert ratio > 1.0

    def test_tempo_ratio_decreases_bpm(self):
        d = BPMDetector()
        d.bpm = 140.0
        ratio = d.get_tempo_ratio_for_target_bpm(100.0)
        assert ratio < 1.0


class TestProcessPipeline:
    def test_process_returns_array(self):
        d = BPMDetector()
        x = make_beat_signal()
        y = d.process(x)
        assert isinstance(y, np.ndarray)

    def test_process_stereo(self):
        d = BPMDetector()
        x = np.stack([make_beat_signal(), make_beat_signal()], axis=1)
        y = d.process(x)
        assert isinstance(y, np.ndarray)
