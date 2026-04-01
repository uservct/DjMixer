"""
tests/test_audio_engine.py
──────────────────────────
Unit tests cho AudioEngine (Thành viên 1)
"""

import os
import sys
import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ── Mock pygame để tránh cần màn hình/soundcard ──────────────────────────────
class MockSound:
    def set_volume(self, v): pass
    def play(self, start=0): return MockChannel()
    def stop(self): pass


class MockChannel:
    def stop(self): pass
    def get_busy(self): return False


# Patch pygame trước khi import AudioEngine
import unittest.mock as mock
sys.modules["pygame"] = mock.MagicMock()
sys.modules["pygame.mixer"] = mock.MagicMock()

import pygame
pygame.mixer.Sound = lambda *a, **kw: MockSound()
pygame.mixer.pre_init = mock.MagicMock()
pygame.mixer.init = mock.MagicMock()

from core.audio_engine import AudioEngine


# ── Test fixture ──────────────────────────────────────────────────────────────

@pytest.fixture
def engine():
    """Trả về AudioEngine sạch cho mỗi test."""
    return AudioEngine("A")


# ── Tests ──────────────────────────────────────────────────────────────────────

class TestAudioEngineInit:
    def test_initial_state(self, engine):
        assert engine.deck_id == "A"
        assert engine.is_playing is False
        assert engine.is_paused is False
        assert engine.volume == 1.0
        assert engine.duration == 0.0


class TestAudioEngineVolume:
    def test_set_volume_normal(self, engine):
        engine.volume = 0.5
        assert engine.volume == pytest.approx(0.5)

    def test_volume_clamp_upper(self, engine):
        engine.volume = 1.5
        assert engine.volume == pytest.approx(1.0)

    def test_volume_clamp_lower(self, engine):
        engine.volume = -0.5
        assert engine.volume == pytest.approx(0.0)

    def test_volume_zero(self, engine):
        engine.volume = 0.0
        assert engine.volume == pytest.approx(0.0)


class TestAudioEnginePosition:
    def test_get_position_default(self, engine):
        assert engine.get_position() == pytest.approx(0.0)

    def test_get_position_ratio_default(self, engine):
        assert engine.get_position_ratio() == pytest.approx(0.0)

    def test_get_position_ratio_no_duration(self, engine):
        """Không bị chia cho 0."""
        engine.duration = 0.0
        assert engine.get_position_ratio() == 0.0


class TestAudioEngineStopPause:
    def test_stop_resets_state(self, engine):
        engine.is_playing = True
        engine.stop()
        assert engine.is_playing is False
        assert engine._pause_position == 0.0

    def test_pause_when_not_playing(self, engine):
        """Pause khi không đang play không gây crash."""
        engine.is_playing = False
        engine.pause()  # không raise exception

    def test_toggle_play_pause_from_stopped(self, engine):
        """Toggle khi không có file không raise exception."""
        engine.toggle_play_pause()  # không raise exception


class TestAudioEngineInfo:
    def test_get_info_keys(self, engine):
        info = engine.get_info()
        assert "deck" in info
        assert "file" in info
        assert "duration" in info
        assert "is_playing" in info
        assert info["deck"] == "A"


class TestAudioEngineSeek:
    def test_seek_clamps_to_zero(self, engine):
        engine.duration = 10.0
        engine.seek(-5.0)
        assert engine._pause_position == pytest.approx(0.0)

    def test_seek_clamps_to_duration(self, engine):
        engine.duration = 10.0
        engine.seek(99.0)
        assert engine._pause_position == pytest.approx(10.0)

    def test_seek_normal(self, engine):
        engine.duration = 10.0
        engine.seek(3.5)
        assert engine._pause_position == pytest.approx(3.5)
