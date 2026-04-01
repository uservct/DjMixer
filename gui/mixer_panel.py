"""
gui/mixer_panel.py
──────────────────
Thành viên 2 – Mixer Panel (Crossfader + Master Volume)

Panel trung tâm chứa:
  - Crossfader (kéo trái-phải để blend Deck A/B)
  - Master Volume slider
  - Hiển thị tỉ lệ A/B hiện tại
  - Chọn crossfader curve
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QSlider, QFrame, QComboBox
)
from PyQt6.QtCore import Qt

from core.mixer import Mixer


class MixerPanel(QWidget):
    """
    Panel điều khiển Crossfader và Master Volume.
    """

    def __init__(self, mixer: Mixer, parent=None):
        super().__init__(parent)
        self.mixer = mixer
        self._build_ui()
        self._connect_signals()

    def _build_ui(self):
        self.setStyleSheet("""
            QWidget {
                background: transparent;
            }
            QFrame#mixer_frame {
                background: rgba(22, 27, 34, 0.95);
                border: 1px solid #30363d;
                border-radius: 14px;
            }
            QLabel#section_title {
                color: #f0f6fc;
                font-size: 13px;
                font-weight: bold;
                letter-spacing: 1px;
            }
            QLabel#cf_label {
                color: #8b949e;
                font-size: 10px;
            }
            QLabel#ratio_label {
                color: #f0f6fc;
                font-size: 11px;
                font-weight: bold;
            }
            QSlider::groove:horizontal {
                border-radius: 4px;
                height: 8px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #00e5ff, stop:0.5 #ffffff33, stop:1 #ff4081);
            }
            QSlider::handle:horizontal {
                background: #f0f6fc;
                border-radius: 10px;
                width: 20px;
                height: 20px;
                margin: -6px 0;
                border: 2px solid #30363d;
            }
            QSlider::groove:vertical {
                border-radius: 4px;
                width: 8px;
                background: #21262d;
            }
            QSlider::handle:vertical {
                background: #f0f6fc;
                border-radius: 8px;
                width: 16px;
                height: 16px;
                margin: 0 -4px;
            }
            QSlider::sub-page:vertical {
                background: #58a6ff;
                border-radius: 4px;
            }
            QComboBox {
                background: #21262d;
                color: #c9d1d9;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 3px 8px;
                font-size: 11px;
            }
            QComboBox::drop-down {
                border: none;
            }
        """)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        frame = QFrame()
        frame.setObjectName("mixer_frame")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        # ── Title ──
        title = QLabel("⚙ MIXER")
        title.setObjectName("section_title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # ── A / B labels & crossfader ──
        cf_header = QHBoxLayout()
        lbl_a = QLabel("A")
        lbl_a.setObjectName("cf_label")
        lbl_a.setStyleSheet("color: #00e5ff; font-size: 14px; font-weight: bold;")
        lbl_b = QLabel("B")
        lbl_b.setObjectName("cf_label")
        lbl_b.setStyleSheet("color: #ff4081; font-size: 14px; font-weight: bold;")
        cf_header.addWidget(lbl_a)
        cf_header.addStretch()
        cf_header.addWidget(lbl_b)
        layout.addLayout(cf_header)

        self.cf_slider = QSlider(Qt.Orientation.Horizontal)
        self.cf_slider.setRange(0, 100)
        self.cf_slider.setValue(50)  # giữa
        self.cf_slider.setMinimumWidth(160)
        layout.addWidget(self.cf_slider)

        # Ratio label
        self.lbl_ratio = QLabel("A 50%  ←→  B 50%")
        self.lbl_ratio.setObjectName("ratio_label")
        self.lbl_ratio.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_ratio)

        # Curve selector
        curve_row = QHBoxLayout()
        lbl_curve = QLabel("Curve:")
        lbl_curve.setStyleSheet("color: #8b949e; font-size: 10px;")
        self.combo_curve = QComboBox()
        self.combo_curve.addItems(["Equal Power", "Linear"])
        curve_row.addWidget(lbl_curve)
        curve_row.addWidget(self.combo_curve)
        layout.addLayout(curve_row)

        # ── Separator ──
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #30363d;")
        layout.addWidget(sep)

        # ── Master Volume ──
        vol_row = QHBoxLayout()
        lbl_mv = QLabel("MASTER")
        lbl_mv.setStyleSheet("color: #8b949e; font-size: 10px; font-weight: bold;")
        vol_row.addWidget(lbl_mv)
        vol_row.addStretch()
        self.lbl_master_val = QLabel("100%")
        self.lbl_master_val.setStyleSheet("color: #58a6ff; font-size: 11px;")
        vol_row.addWidget(self.lbl_master_val)
        layout.addLayout(vol_row)

        self.master_slider = QSlider(Qt.Orientation.Horizontal)
        self.master_slider.setRange(0, 100)
        self.master_slider.setValue(100)
        layout.addWidget(self.master_slider)

        outer.addWidget(frame)

    # ── Connect signals ───────────────────────────────────────────────────────

    def _connect_signals(self):
        self.cf_slider.valueChanged.connect(self._on_crossfader_changed)
        self.master_slider.valueChanged.connect(self._on_master_changed)
        self.combo_curve.currentTextChanged.connect(self._on_curve_changed)

    # ── Slots ─────────────────────────────────────────────────────────────────

    def _on_crossfader_changed(self, value: int):
        cf = value / 100.0
        self.mixer.crossfader = cf
        vol_a, vol_b = self.mixer.get_crossfader_volumes()
        self.lbl_ratio.setText(
            f"A {vol_a*100:.0f}%  ←→  B {vol_b*100:.0f}%"
        )

    def _on_master_changed(self, value: int):
        self.mixer.master_volume = value / 100.0
        self.lbl_master_val.setText(f"{value}%")

    def _on_curve_changed(self, text: str):
        curve = Mixer.CURVE_EQUAL_POWER if text == "Equal Power" else Mixer.CURVE_LINEAR
        self.mixer.set_curve(curve)
