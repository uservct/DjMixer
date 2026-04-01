"""
gui/waveform_widget.py
──────────────────────
Thành viên 5 – Waveform Visualization

Widget hiển thị waveform audio bằng pyqtgraph với:
  - Waveform tổng thể (thumbnail)
  - Playhead di chuyển theo thời gian thực
  - Màu sắc riêng cho Deck A (cyan) và Deck B (magenta)
"""

import numpy as np
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtCore import Qt, QTimer
try:
    import pyqtgraph as pg
    PYQTGRAPH_AVAILABLE = True
except ImportError:
    PYQTGRAPH_AVAILABLE = False

from PyQt6.QtWidgets import QLabel


class WaveformWidget(QWidget):
    """
    Widget vẽ waveform của một deck.

    Parameters
    ----------
    deck_id : str  – "A" hoặc "B"
    color   : str  – màu waveform (hex hoặc tên màu)
    parent  : QWidget | None
    """

    DECK_COLORS = {"A": "#00e5ff", "B": "#ff4081"}
    PLAYHEAD_COLOR = "#ffffff"
    BG_COLOR = "#0d1117"

    def __init__(self, deck_id: str = "A", parent=None):
        super().__init__(parent)
        self.deck_id = deck_id
        self._color = self.DECK_COLORS.get(deck_id, "#00e5ff")
        self._waveform: np.ndarray = np.array([])
        self._duration: float = 0.0
        self._position: float = 0.0
        self._position_getter = None  # callable trả về position hiện tại

        self._build_ui()

        # Timer cập nhật playhead
        self._timer = QTimer(self)
        self._timer.setInterval(50)  # 20 FPS
        self._timer.timeout.connect(self._update_playhead)
        self._timer.start()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        if PYQTGRAPH_AVAILABLE:
            pg.setConfigOptions(antialias=True, background=self.BG_COLOR)

            self._plot = pg.PlotWidget()
            self._plot.setBackground(self.BG_COLOR)
            self._plot.setMinimumHeight(85)
            self._plot.showGrid(x=False, y=False)
            self._plot.getAxis("bottom").hide()
            self._plot.getAxis("left").hide()

            # Waveform curve
            pen = pg.mkPen(color=self._color, width=1)
            self._curve = self._plot.plot(pen=pen)

            # Playhead (đường dọc trắng)
            self._playhead = pg.InfiniteLine(
                pos=0, angle=90,
                pen=pg.mkPen(color=self.PLAYHEAD_COLOR, width=2)
            )
            self._plot.addItem(self._playhead)

            layout.addWidget(self._plot)
        else:
            # Fallback nếu không có pyqtgraph
            label = QLabel(f"Waveform Deck {self.deck_id}\n(Cài pyqtgraph để xem)")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet(
                f"color: {self._color}; background: {self.BG_COLOR}; "
                "border-radius: 6px; font-size: 11px;"
            )
            label.setMinimumHeight(85)
            layout.addWidget(label)

    # ── Public API ────────────────────────────────────────────────────────────

    def set_waveform(self, waveform: np.ndarray, duration: float):
        """
        Cập nhật waveform data mới.
        waveform: numpy array float32 mono, normalized [-1, 1]
        duration: tổng thời lượng (giây)
        """
        self._waveform = waveform
        self._duration = duration

        if not PYQTGRAPH_AVAILABLE or len(waveform) == 0:
            return

        # Downsample để vẽ nhanh hơn (max 4000 điểm)
        n_points = min(len(waveform), 4000)
        indices = np.linspace(0, len(waveform) - 1, n_points, dtype=int)
        y = waveform[indices]
        x = np.linspace(0, duration, n_points)

        self._curve.setData(x, y)
        self._plot.setXRange(0, duration, padding=0)
        self._plot.setYRange(-1.2, 1.2, padding=0)

    def set_position_getter(self, getter):
        """Đăng ký callable trả về position hiện tại (giây)."""
        self._position_getter = getter

    def set_position(self, position_sec: float):
        """Cập nhật vị trí playhead trực tiếp."""
        self._position = position_sec
        if PYQTGRAPH_AVAILABLE:
            self._playhead.setValue(position_sec)

    def clear(self):
        """Xóa waveform."""
        self._waveform = np.array([])
        self._duration = 0.0
        if PYQTGRAPH_AVAILABLE:
            self._curve.setData([], [])
            self._playhead.setValue(0)

    # ── Timer callback ────────────────────────────────────────────────────────

    def _update_playhead(self):
        if self._position_getter and PYQTGRAPH_AVAILABLE:
            pos = self._position_getter()
            self._playhead.setValue(pos)
