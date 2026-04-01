"""
tests/test_effects.py
─────────────────────
Unit tests cho Audio Effects (Thành viên 3)
"""

import os
import sys
import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.effects import (
    lowpass_filter, highpass_filter, echo_effect,
    reverb_effect, EQ3Band, EffectsChain
)


SR = 44100  # sample rate mẫu


def make_sine(freq_hz: float = 440.0, duration_sec: float = 0.1,
              sr: int = SR) -> np.ndarray:
    """Sinh sóng sin đơn kênh."""
    t = np.linspace(0, duration_sec, int(sr * duration_sec), endpoint=False)
    return np.sin(2 * np.pi * freq_hz * t).astype(np.float32)


def make_stereo(data: np.ndarray) -> np.ndarray:
    return np.stack([data, data], axis=1)


class TestLowpassFilter:
    def test_output_shape_mono(self):
        x = make_sine(440.0)
        y = lowpass_filter(x, cutoff_hz=500.0, sample_rate=SR)
        assert y.shape == x.shape

    def test_output_shape_stereo(self):
        x = make_stereo(make_sine(440.0))
        y = lowpass_filter(x, cutoff_hz=500.0, sample_rate=SR)
        assert y.shape == x.shape

    def test_attenuates_high_freq(self):
        """Tần số cao nên bị giảm sau khi lọc thông thấp."""
        high = make_sine(8000.0, duration_sec=0.5)
        low  = make_sine(100.0,  duration_sec=0.5)
        filtered_high = lowpass_filter(high, cutoff_hz=500.0, sample_rate=SR)
        filtered_low  = lowpass_filter(low,  cutoff_hz=500.0, sample_rate=SR)
        energy_high = np.mean(filtered_high ** 2)
        energy_low  = np.mean(filtered_low  ** 2)
        assert energy_high < energy_low


class TestHighpassFilter:
    def test_output_shape_mono(self):
        x = make_sine(440.0)
        y = highpass_filter(x, cutoff_hz=500.0, sample_rate=SR)
        assert y.shape == x.shape

    def test_attenuates_low_freq(self):
        """Tần số thấp nên bị giảm sau khi lọc thông cao."""
        high = make_sine(8000.0, duration_sec=0.5)
        low  = make_sine(100.0,  duration_sec=0.5)
        filtered_high = highpass_filter(high, cutoff_hz=500.0, sample_rate=SR)
        filtered_low  = highpass_filter(low,  cutoff_hz=500.0, sample_rate=SR)
        energy_high = np.mean(filtered_high ** 2)
        energy_low  = np.mean(filtered_low  ** 2)
        assert energy_low < energy_high


class TestEQ3Band:
    def test_neutral_gain(self):
        """0 dB gain không thay đổi tín hiệu đáng kể."""
        eq = EQ3Band(SR)
        x = make_sine(440.0, duration_sec=0.2)
        y = eq.process(x)
        assert y.shape == x.shape
        # Năng lượng không thay đổi quá 10%
        assert abs(np.mean(y**2) - np.mean(x**2)) < 0.1 * np.mean(x**2)

    def test_boost_bass(self):
        """Boost bass làm năng lượng tín hiệu tần số thấp tăng."""
        eq = EQ3Band(SR)
        eq.bass_gain_db = 6.0
        x = make_sine(100.0, duration_sec=0.2)
        y = eq.process(x)
        assert np.mean(y**2) > np.mean(x**2)

    def test_output_clipped(self):
        """Output không vượt quá phạm vi [-1, 1]."""
        eq = EQ3Band(SR)
        eq.bass_gain_db = 12.0
        x = make_sine(100.0, duration_sec=0.1)
        y = eq.process(x)
        assert np.all(y >= -1.0)
        assert np.all(y <= 1.0)

    def test_stereo_input(self):
        eq = EQ3Band(SR)
        x = make_stereo(make_sine(440.0))
        y = eq.process(x)
        assert y.shape == x.shape


class TestEchoEffect:
    def test_output_shape(self):
        x = make_sine(440.0, duration_sec=1.0)
        y = echo_effect(x, delay_sec=0.2, feedback=0.3, sample_rate=SR)
        assert y.shape == x.shape

    def test_output_clipped(self):
        x = make_sine(440.0, duration_sec=1.0)
        y = echo_effect(x, delay_sec=0.1, feedback=0.5, sample_rate=SR)
        assert np.all(y >= -1.0)
        assert np.all(y <= 1.0)

    def test_stereo_echo(self):
        x = make_stereo(make_sine(440.0, duration_sec=1.0))
        y = echo_effect(x, delay_sec=0.2, feedback=0.3, sample_rate=SR)
        assert y.shape == x.shape


class TestReverbEffect:
    def test_output_shape(self):
        x = make_sine(440.0, duration_sec=1.0)
        y = reverb_effect(x, room_size=0.5, damping=0.5, sample_rate=SR)
        assert y.shape == x.shape

    def test_output_clipped(self):
        x = make_sine(440.0, duration_sec=1.0)
        y = reverb_effect(x)
        assert np.all(y >= -1.0)
        assert np.all(y <= 1.0)


class TestEffectsChain:
    def test_process_passthrough(self):
        """Khi tất cả effects tắt, output ≈ input (chỉ EQ 0 dB)."""
        chain = EffectsChain(SR)
        x = make_sine(440.0, duration_sec=0.2)
        y = chain.process(x)
        assert y.shape == x.shape

    def test_echo_enabled(self):
        chain = EffectsChain(SR)
        chain.echo_enabled = True
        x = make_sine(440.0, duration_sec=1.0)
        y = chain.process(x)
        assert y.shape == x.shape

    def test_reverb_enabled(self):
        chain = EffectsChain(SR)
        chain.reverb_enabled = True
        x = make_sine(440.0, duration_sec=1.0)
        y = chain.process(x)
        assert y.shape == x.shape

    def test_all_effects_enabled(self):
        chain = EffectsChain(SR)
        chain.lowpass_enabled = True
        chain.echo_enabled = True
        chain.reverb_enabled = True
        x = make_sine(440.0, duration_sec=1.0)
        y = chain.process(x)
        assert y.shape == x.shape
