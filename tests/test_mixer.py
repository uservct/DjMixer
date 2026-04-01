"""
tests/test_mixer.py
───────────────────
Unit tests cho Mixer + Crossfader (Thành viên 2)
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import unittest.mock as mock
sys.modules["pygame"] = mock.MagicMock()
sys.modules["pygame.mixer"] = mock.MagicMock()

from core.audio_engine import AudioEngine
from core.mixer import Mixer


@pytest.fixture
def engines():
    """Trả về cặp AudioEngine mock."""
    a = AudioEngine("A")
    b = AudioEngine("B")
    return a, b


@pytest.fixture
def mixer(engines):
    a, b = engines
    return Mixer(a, b)


class TestMixerInit:
    def test_default_crossfader(self, mixer):
        assert mixer.crossfader == pytest.approx(0.5)

    def test_default_master_volume(self, mixer):
        assert mixer.master_volume == pytest.approx(1.0)

    def test_default_curve(self, mixer):
        assert mixer._curve == Mixer.CURVE_EQUAL_POWER


class TestCrossfader:
    def test_full_left(self, mixer):
        mixer.crossfader = 0.0
        vol_a, vol_b = mixer.get_crossfader_volumes()
        assert vol_a == pytest.approx(1.0, abs=1e-3)
        assert vol_b == pytest.approx(0.0, abs=1e-3)

    def test_full_right(self, mixer):
        mixer.crossfader = 1.0
        vol_a, vol_b = mixer.get_crossfader_volumes()
        assert vol_a == pytest.approx(0.0, abs=1e-3)
        assert vol_b == pytest.approx(1.0, abs=1e-3)

    def test_center_equal_power(self, mixer):
        mixer.crossfader = 0.5
        vol_a, vol_b = mixer.get_crossfader_volumes()
        # Equal-power: center ≈ 0.707 cho cả hai
        assert vol_a == pytest.approx(0.7071, abs=0.001)
        assert vol_b == pytest.approx(0.7071, abs=0.001)

    def test_clamp_above_1(self, mixer):
        mixer.crossfader = 1.5
        assert mixer.crossfader == pytest.approx(1.0)

    def test_clamp_below_0(self, mixer):
        mixer.crossfader = -0.5
        assert mixer.crossfader == pytest.approx(0.0)


class TestLinearCurve:
    def test_linear_center(self, mixer):
        mixer.set_curve(Mixer.CURVE_LINEAR)
        mixer.crossfader = 0.5
        vol_a, vol_b = mixer.get_crossfader_volumes()
        assert vol_a == pytest.approx(0.5)
        assert vol_b == pytest.approx(0.5)

    def test_linear_full_left(self, mixer):
        mixer.set_curve(Mixer.CURVE_LINEAR)
        mixer.crossfader = 0.0
        vol_a, vol_b = mixer.get_crossfader_volumes()
        assert vol_a == pytest.approx(1.0)
        assert vol_b == pytest.approx(0.0)


class TestMasterVolume:
    def test_master_half(self, mixer, engines):
        a, b = engines
        mixer.crossfader = 0.0  # Deck A full
        mixer.master_volume = 0.5
        # Deck A volume = 1.0 * 0.5 = 0.5
        assert a.volume == pytest.approx(0.5, abs=0.01)

    def test_master_clamp(self, mixer):
        mixer.master_volume = 2.0
        assert mixer.master_volume == pytest.approx(1.0)

    def test_master_zero(self, mixer, engines):
        a, b = engines
        mixer.master_volume = 0.0
        assert a.volume == pytest.approx(0.0, abs=0.01)
        assert b.volume == pytest.approx(0.0, abs=0.01)


class TestMixerStatus:
    def test_get_status_keys(self, mixer):
        status = mixer.get_status()
        assert "crossfader" in status
        assert "master_volume" in status
        assert "curve" in status
        assert "vol_a" in status
        assert "vol_b" in status
