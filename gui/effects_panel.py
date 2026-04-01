"""
gui/effects_panel.py
────────────────────
Thành viên 3 – Effects Panel

Panel điều khiển các hiệu ứng âm thanh cho mỗi Deck:
  - EQ 3 dải (Bass, Mid, Treble)
  - Low-pass filter
  - High-pass filter
  - Echo
  - Reverb
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QSlider, QFrame, QCheckBox, QGroupBox
)
from PyQt6.QtCore import Qt

from core.effects import EffectsChain


class EffectsPanel(QWidget):
    """
    Panel điều khiển hiệu ứng cho một Deck.
    """

    def __init__(self, effects_chain: EffectsChain, deck_id: str = "A", parent=None):
        super().__init__(parent)
        self.effects_chain = effects_chain
        self.deck_id = deck_id
        self._accent = "#00e5ff" if deck_id == "A" else "#ff4081"
        self._build_ui()
        self._connect_signals()

    def _build_ui(self):
        accent = self._accent
        self.setStyleSheet(f"""
            QWidget {{ background: transparent; }}
            QFrame#fx_frame {{
                background: rgba(22, 27, 34, 0.9);
                border: 1px solid {accent}44;
                border-radius: 12px;
            }}
            QLabel#section_title {{
                color: {accent};
                font-size: 12px;
                font-weight: bold;
                letter-spacing: 1px;
            }}
            QLabel {{
                color: #8b949e;
                font-size: 10px;
            }}
            QCheckBox {{
                color: #c9d1d9;
                font-size: 11px;
            }}
            QCheckBox::indicator {{
                width: 14px; height: 14px;
                border-radius: 3px;
                border: 1px solid #484f58;
                background: #21262d;
            }}
            QCheckBox::indicator:checked {{
                background: {accent};
                border-color: {accent};
            }}
            QSlider::groove:horizontal {{
                height: 4px;
                background: #21262d;
                border-radius: 2px;
            }}
            QSlider::handle:horizontal {{
                background: {accent};
                border-radius: 6px;
                width: 12px; height: 12px;
                margin: -4px 0;
            }}
            QSlider::sub-page:horizontal {{
                background: {accent}88;
                border-radius: 2px;
            }}
        """)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        frame = QFrame()
        frame.setObjectName("fx_frame")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        title = QLabel(f"FX – DECK {self.deck_id}")
        title.setObjectName("section_title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # ── EQ 3-Band ──
        layout.addWidget(self._make_separator("EQ"))
        layout.addLayout(self._make_eq_row("BASS", -12, 12, 0, "bass"))
        layout.addLayout(self._make_eq_row("MID ", -12, 12, 0, "mid"))
        layout.addLayout(self._make_eq_row("TREB", -12, 12, 0, "treble"))

        # ── Low-pass ──
        layout.addWidget(self._make_separator("FILTER"))
        lp_row = QHBoxLayout()
        self.chk_lowpass = QCheckBox("Low-pass")
        lp_row.addWidget(self.chk_lowpass)
        self.sld_lp_cutoff = QSlider(Qt.Orientation.Horizontal)
        self.sld_lp_cutoff.setRange(200, 18000)
        self.sld_lp_cutoff.setValue(1000)
        lp_row.addWidget(self.sld_lp_cutoff)
        self.lbl_lp = QLabel("1000Hz")
        self.lbl_lp.setFixedWidth(52)
        lp_row.addWidget(self.lbl_lp)
        layout.addLayout(lp_row)

        # ── High-pass ──
        hp_row = QHBoxLayout()
        self.chk_highpass = QCheckBox("High-pass")
        hp_row.addWidget(self.chk_highpass)
        self.sld_hp_cutoff = QSlider(Qt.Orientation.Horizontal)
        self.sld_hp_cutoff.setRange(20, 8000)
        self.sld_hp_cutoff.setValue(1000)
        hp_row.addWidget(self.sld_hp_cutoff)
        self.lbl_hp = QLabel("1000Hz")
        self.lbl_hp.setFixedWidth(52)
        hp_row.addWidget(self.lbl_hp)
        layout.addLayout(hp_row)

        # ── Echo ──
        layout.addWidget(self._make_separator("ECHO"))
        echo_en = QHBoxLayout()
        self.chk_echo = QCheckBox("Echo")
        echo_en.addWidget(self.chk_echo)
        echo_en.addStretch()
        layout.addLayout(echo_en)

        layout.addLayout(self._make_param_row("Delay", 0.05, 1.0, 0.3, "echo_delay", "s"))
        layout.addLayout(self._make_param_row("Feedback", 0.0, 0.9, 0.4, "echo_feedback", ""))

        # ── Reverb ──
        layout.addWidget(self._make_separator("REVERB"))
        rev_en = QHBoxLayout()
        self.chk_reverb = QCheckBox("Reverb")
        rev_en.addWidget(self.chk_reverb)
        rev_en.addStretch()
        layout.addLayout(rev_en)

        layout.addLayout(self._make_param_row("Room", 0.0, 1.0, 0.5, "reverb_room", ""))
        layout.addLayout(self._make_param_row("Damp", 0.0, 1.0, 0.5, "reverb_damp", ""))

        outer.addWidget(frame)

    # ── Helper builders ───────────────────────────────────────────────────────

    def _make_separator(self, text: str) -> QLabel:
        lbl = QLabel(f"── {text} ──")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet(f"color: {self._accent}88; font-size: 9px; letter-spacing: 1px;")
        return lbl

    def _make_eq_row(self, label: str, min_val: int, max_val: int,
                     default: int, band: str) -> QHBoxLayout:
        row = QHBoxLayout()
        lbl = QLabel(label)
        lbl.setFixedWidth(32)
        sld = QSlider(Qt.Orientation.Horizontal)
        sld.setRange(min_val, max_val)
        sld.setValue(default)
        val_lbl = QLabel("0 dB")
        val_lbl.setFixedWidth(42)
        setattr(self, f"sld_eq_{band}", sld)
        setattr(self, f"lbl_eq_{band}", val_lbl)
        row.addWidget(lbl)
        row.addWidget(sld)
        row.addWidget(val_lbl)
        return row

    def _make_param_row(self, label: str, min_f: float, max_f: float,
                        default_f: float, attr: str, unit: str) -> QHBoxLayout:
        row = QHBoxLayout()
        lbl = QLabel(label)
        lbl.setFixedWidth(52)
        sld = QSlider(Qt.Orientation.Horizontal)
        sld.setRange(0, 100)
        sld.setValue(int((default_f - min_f) / (max_f - min_f) * 100))
        val_lbl = QLabel(f"{default_f:.2f}{unit}")
        val_lbl.setFixedWidth(48)
        setattr(self, f"sld_{attr}", sld)
        setattr(self, f"lbl_{attr}", val_lbl)
        setattr(self, f"_min_{attr}", min_f)
        setattr(self, f"_max_{attr}", max_f)
        setattr(self, f"_unit_{attr}", unit)
        row.addWidget(lbl)
        row.addWidget(sld)
        row.addWidget(val_lbl)
        return row

    # ── Connect signals ───────────────────────────────────────────────────────

    def _connect_signals(self):
        # EQ
        self.sld_eq_bass.valueChanged.connect(
            lambda v: self._update_eq("bass", v))
        self.sld_eq_mid.valueChanged.connect(
            lambda v: self._update_eq("mid", v))
        self.sld_eq_treble.valueChanged.connect(
            lambda v: self._update_eq("treble", v))

        # Low-pass
        self.chk_lowpass.toggled.connect(
            lambda v: setattr(self.effects_chain, "lowpass_enabled", v))
        self.sld_lp_cutoff.valueChanged.connect(self._update_lp)

        # High-pass
        self.chk_highpass.toggled.connect(
            lambda v: setattr(self.effects_chain, "highpass_enabled", v))
        self.sld_hp_cutoff.valueChanged.connect(self._update_hp)

        # Echo
        self.chk_echo.toggled.connect(
            lambda v: setattr(self.effects_chain, "echo_enabled", v))
        self.sld_echo_delay.valueChanged.connect(self._update_echo_delay)
        self.sld_echo_feedback.valueChanged.connect(self._update_echo_feedback)

        # Reverb
        self.chk_reverb.toggled.connect(
            lambda v: setattr(self.effects_chain, "reverb_enabled", v))
        self.sld_reverb_room.valueChanged.connect(self._update_reverb_room)
        self.sld_reverb_damp.valueChanged.connect(self._update_reverb_damp)

    # ── Slots ─────────────────────────────────────────────────────────────────

    def _update_eq(self, band: str, value: int):
        lbl = getattr(self, f"lbl_eq_{band}")
        lbl.setText(f"{value:+d} dB")
        setattr(self.effects_chain.eq, f"{band}_gain_db", float(value))

    def _update_lp(self, value: int):
        self.effects_chain.lowpass_cutoff = float(value)
        self.lbl_lp.setText(f"{value}Hz")

    def _update_hp(self, value: int):
        self.effects_chain.highpass_cutoff = float(value)
        self.lbl_hp.setText(f"{value}Hz")

    def _update_echo_delay(self, value: int):
        min_f = self._min_echo_delay
        max_f = self._max_echo_delay
        v = min_f + (value / 100.0) * (max_f - min_f)
        self.effects_chain.echo_delay = v
        self.lbl_echo_delay.setText(f"{v:.2f}s")

    def _update_echo_feedback(self, value: int):
        min_f = self._min_echo_feedback
        max_f = self._max_echo_feedback
        v = min_f + (value / 100.0) * (max_f - min_f)
        self.effects_chain.echo_feedback = v
        self.lbl_echo_feedback.setText(f"{v:.2f}")

    def _update_reverb_room(self, value: int):
        min_f = self._min_reverb_room
        max_f = self._max_reverb_room
        v = min_f + (value / 100.0) * (max_f - min_f)
        self.effects_chain.reverb_room_size = v
        self.lbl_reverb_room.setText(f"{v:.2f}")

    def _update_reverb_damp(self, value: int):
        min_f = self._min_reverb_damp
        max_f = self._max_reverb_damp
        v = min_f + (value / 100.0) * (max_f - min_f)
        self.effects_chain.reverb_damping = v
        self.lbl_reverb_damp.setText(f"{v:.2f}")
