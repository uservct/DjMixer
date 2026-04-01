"""
core/mixer.py
─────────────
Thành viên 2 – Mixer Logic & Crossfader

Xử lý logic trộn âm thanh giữa Deck A và Deck B thông qua crossfader,
cùng với master volume và cue monitoring.
"""

import numpy as np
from core.audio_engine import AudioEngine


class Mixer:
    """
    Điều phối việc trộn âm thanh giữa hai Deck A và B.

    Crossfader:
      - Giá trị 0.0  → chỉ nghe Deck A (Deck B tắt tiếng)
      - Giá trị 0.5  → nghe cả hai deck bằng nhau
      - Giá trị 1.0  → chỉ nghe Deck B (Deck A tắt tiếng)

    Curve "equal-power" (sin/cos) giúp volume tổng không bị giảm ở giữa.
    """

    CURVE_LINEAR = "linear"
    CURVE_EQUAL_POWER = "equal_power"

    def __init__(self, deck_a: AudioEngine, deck_b: AudioEngine):
        self.deck_a = deck_a
        self.deck_b = deck_b

        self._crossfader: float = 0.5   # 0.0 → 1.0
        self._master_volume: float = 1.0
        self._curve: str = self.CURVE_EQUAL_POWER

        # Áp dụng ngay sau khi khởi tạo
        self._apply_volumes()

    # ── Crossfader ───────────────────────────────────────────────────────────

    @property
    def crossfader(self) -> float:
        return self._crossfader

    @crossfader.setter
    def crossfader(self, value: float):
        """Đặt crossfader 0.0 → 1.0 và áp dụng vào cả 2 deck."""
        self._crossfader = max(0.0, min(1.0, value))
        self._apply_volumes()

    def _apply_volumes(self):
        """
        Tính toán volume cho từng deck dựa theo crossfader và master volume,
        sau đó cập nhật trực tiếp vào AudioEngine.
        """
        vol_a, vol_b = self._calc_deck_volumes(self._crossfader)
        self.deck_a.volume = vol_a * self._master_volume
        self.deck_b.volume = vol_b * self._master_volume

    def _calc_deck_volumes(self, cf: float) -> tuple[float, float]:
        """
        Trả về (vol_a, vol_b) dựa theo crossfader và curve đang dùng.
        """
        if self._curve == self.CURVE_EQUAL_POWER:
            angle = cf * (np.pi / 2)
            vol_a = float(np.cos(angle))
            vol_b = float(np.sin(angle))
        else:  # linear
            vol_a = 1.0 - cf
            vol_b = cf
        return vol_a, vol_b

    # ── Master volume ────────────────────────────────────────────────────────

    @property
    def master_volume(self) -> float:
        return self._master_volume

    @master_volume.setter
    def master_volume(self, value: float):
        self._master_volume = max(0.0, min(1.0, value))
        self._apply_volumes()

    # ── Curve ────────────────────────────────────────────────────────────────

    def set_curve(self, curve: str):
        """Đổi crossfader curve: 'linear' hoặc 'equal_power'."""
        if curve in (self.CURVE_LINEAR, self.CURVE_EQUAL_POWER):
            self._curve = curve
            self._apply_volumes()

    # ── Utility ──────────────────────────────────────────────────────────────

    def get_crossfader_volumes(self) -> tuple[float, float]:
        """Trả về (vol_a, vol_b) hiện tại (không nhân master)."""
        return self._calc_deck_volumes(self._crossfader)

    def get_status(self) -> dict:
        return {
            "crossfader": self._crossfader,
            "master_volume": self._master_volume,
            "curve": self._curve,
            "vol_a": self.deck_a.volume,
            "vol_b": self.deck_b.volume,
        }
