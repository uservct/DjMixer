"""
gui/main_window.py
──────────────────
Thành viên 5 & 6 – Main Window

Cửa sổ chính của ứng dụng DJ Mixer. Lắp ghép tất cả widget:
  - Deck A (trái) + Deck B (phải)
  - Mixer Panel (giữa, crossfader + master volume)
  - Effects Panel A (dưới deck A) + Effects Panel B (dưới deck B)
  - Status bar (ghi âm, thời gian)
  - Toolbar: nút Record
"""

import sys
import os
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QStatusBar, QSplitter, QScrollArea,
    QApplication, QFrame
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QIcon, QPalette, QColor

from core.audio_engine import AudioEngine
from core.mixer import Mixer
from core.effects import EffectsChain
from core.bpm_detector import BPMDetector
from gui.deck_widget import DeckWidget
from gui.mixer_panel import MixerPanel
from gui.effects_panel import EffectsPanel
from utils.audio_recorder import AudioRecorder


class MainWindow(QMainWindow):
    """
    Cửa sổ chính của DJ Mixer.
    """

    APP_TITLE = "🎧 DJ Mixer – Python"
    WINDOW_MIN_W = 1100
    WINDOW_MIN_H = 750

    def __init__(self):
        super().__init__()

        # ── Khởi tạo core objects ──
        self.engine_a = AudioEngine("A")
        self.engine_b = AudioEngine("B")
        self.mixer = Mixer(self.engine_a, self.engine_b)
        self.effects_a = EffectsChain()
        self.effects_b = EffectsChain()
        self.bpm_a = BPMDetector()
        self.bpm_b = BPMDetector()
        self.recorder = AudioRecorder()

        # ── Kết nối EffectsChain vào AudioEngine ──
        # Từ đây mỗi chunk audio sẽ đi qua effects_chain.process()
        self.engine_a.set_effects_chain(self.effects_a)
        self.engine_b.set_effects_chain(self.effects_b)

        self._setup_window()
        self._apply_global_style()
        self._build_ui()

        # Timer cập nhật status bar
        self._status_timer = QTimer(self)
        self._status_timer.setInterval(500)
        self._status_timer.timeout.connect(self._update_status)
        self._status_timer.start()

    # ── Window setup ──────────────────────────────────────────────────────────

    def _setup_window(self):
        self.setWindowTitle(self.APP_TITLE)
        self.setMinimumSize(self.WINDOW_MIN_W, self.WINDOW_MIN_H)
        self.resize(1280, 820)

    def _apply_global_style(self):
        self.setStyleSheet("""
            QMainWindow, QWidget#central {
                background: #0d1117;
            }
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollBar:vertical {
                background: #161b22;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #30363d;
                border-radius: 4px;
            }
            QStatusBar {
                background: #161b22;
                color: #8b949e;
                font-size: 11px;
                border-top: 1px solid #21262d;
            }
        """)

    # ── Build UI ──────────────────────────────────────────────────────────────

    def _build_ui(self):
        central = QWidget()
        central.setObjectName("central")
        self.setCentralWidget(central)

        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ── Top bar (branding + record button) ──
        root_layout.addWidget(self._build_topbar())

        # ── Main content area ──
        content = QWidget()
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(12, 12, 12, 12)
        content_layout.setSpacing(12)

        # Deck A (left column)
        left_col = self._build_deck_column("A")

        # Center column (Mixer)
        center_col = self._build_center_column()

        # Deck B (right column)
        right_col = self._build_deck_column("B")

        content_layout.addWidget(left_col, stretch=5)
        content_layout.addWidget(center_col, stretch=2)
        content_layout.addWidget(right_col, stretch=5)

        root_layout.addWidget(content, stretch=1)

        # ── Status bar ──
        self._build_statusbar()

    def _build_topbar(self) -> QWidget:
        bar = QFrame()
        bar.setFixedHeight(56)
        bar.setStyleSheet("""
            QFrame {
                background: #161b22;
                border-bottom: 1px solid #21262d;
            }
        """)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(20, 0, 20, 0)

        # Logo / Title
        logo = QLabel("🎧  DJ MIXER")
        logo.setStyleSheet("""
            color: #f0f6fc;
            font-size: 20px;
            font-weight: bold;
            letter-spacing: 3px;
        """)
        layout.addWidget(logo)

        subtitle = QLabel("Python Edition")
        subtitle.setStyleSheet("color: #58a6ff; font-size: 12px;")
        layout.addWidget(subtitle)
        layout.addStretch()

        # Record button
        self.btn_record = QPushButton("⏺ REC")
        self.btn_record.setFixedSize(90, 34)
        self.btn_record.setStyleSheet("""
            QPushButton {
                background: #da3633;
                color: white;
                border-radius: 8px;
                font-weight: bold;
                font-size: 12px;
                border: none;
            }
            QPushButton:hover {
                background: #f85149;
            }
            QPushButton:checked {
                background: #388bfd;
            }
        """)
        self.btn_record.setCheckable(True)
        self.btn_record.clicked.connect(self._on_record_toggle)
        layout.addWidget(self.btn_record)

        return bar

    def _build_deck_column(self, deck_id: str) -> QWidget:
        col = QWidget()
        layout = QVBoxLayout(col)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        engine = self.engine_a if deck_id == "A" else self.engine_b
        bpm = self.bpm_a if deck_id == "A" else self.bpm_b
        effects = self.effects_a if deck_id == "A" else self.effects_b

        deck_widget = DeckWidget(engine, bpm, deck_id)
        effects_widget = EffectsPanel(effects, deck_id)

        if deck_id == "A":
            self.deck_a_widget = deck_widget
            self.effects_a_panel = effects_widget
        else:
            self.deck_b_widget = deck_widget
            self.effects_b_panel = effects_widget

        layout.addWidget(deck_widget, stretch=3)
        layout.addWidget(effects_widget, stretch=2)
        return col

    def _build_center_column(self) -> QWidget:
        col = QWidget()
        layout = QVBoxLayout(col)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.mixer_panel = MixerPanel(self.mixer)
        layout.addWidget(self.mixer_panel)

        # VU Meter placeholder
        vu = self._build_vu_meter()
        layout.addWidget(vu)
        layout.addStretch()
        return col

    def _build_vu_meter(self) -> QFrame:
        """VU meter đơn giản (visual only, để bổ sung sau)."""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background: rgba(22, 27, 34, 0.9);
                border: 1px solid #30363d;
                border-radius: 12px;
            }
        """)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 10, 12, 10)

        title = QLabel("VU METER")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #8b949e; font-size: 10px; letter-spacing: 1px;")
        layout.addWidget(title)

        # Simulated bars
        bars_layout = QHBoxLayout()
        bars_layout.setSpacing(3)
        self._vu_bars = []
        for i in range(16):
            bar = QLabel()
            bar.setFixedSize(9, 60)
            bar.setStyleSheet("background: #21262d; border-radius: 4px;")
            bars_layout.addWidget(bar)
            self._vu_bars.append(bar)
        layout.addLayout(bars_layout)

        # Animate VU bars (simple simulation)
        self._vu_timer = QTimer(self)
        self._vu_timer.setInterval(80)
        self._vu_timer.timeout.connect(self._animate_vu)
        self._vu_timer.start()

        return frame

    def _build_statusbar(self):
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)

        self.lbl_status = QLabel("Sẵn sàng")
        self.lbl_rec_time = QLabel("")
        self.lbl_rec_time.setStyleSheet("color: #f85149;")

        self.statusbar.addWidget(self.lbl_status)
        self.statusbar.addPermanentWidget(self.lbl_rec_time)

    # ── Record ────────────────────────────────────────────────────────────────

    def _on_record_toggle(self, checked: bool):
        if checked:
            path = self.recorder.start_recording()
            self.btn_record.setText("⏹ STOP")
            self.lbl_status.setText(f"⏺ Đang ghi: {os.path.basename(path)}")
        else:
            saved = self.recorder.stop_recording()
            self.btn_record.setText("⏺ REC")
            self.lbl_rec_time.setText("")
            if saved:
                self.lbl_status.setText(f"✅ Đã lưu: {os.path.basename(saved)}")
            else:
                self.lbl_status.setText("Sẵn sàng")

    # ── Update status ─────────────────────────────────────────────────────────

    def _update_status(self):
        if self.recorder.is_recording:
            elapsed = self.recorder.get_elapsed()
            m = int(elapsed // 60)
            s = int(elapsed % 60)
            self.lbl_rec_time.setText(f"🔴 {m:02d}:{s:02d}")

    # ── VU Meter animation ────────────────────────────────────────────────────

    def _animate_vu(self):
        import random
        playing = self.engine_a.is_playing or self.engine_b.is_playing
        colors = [
            "#238636",  # green
            "#2ea043",
            "#388bfd",  # blue mid
            "#f85149",  # red peak
        ]
        for i, bar in enumerate(self._vu_bars):
            if playing:
                height = random.randint(10, 60)
                ratio = height / 60.0
                if ratio > 0.85:
                    color = colors[3]
                elif ratio > 0.6:
                    color = colors[2]
                else:
                    color = colors[0]
                bar.setStyleSheet(
                    f"background: {color}; border-radius: 4px; min-height: {height}px; max-height: {height}px;"
                )
            else:
                bar.setStyleSheet(
                    "background: #21262d; border-radius: 4px; min-height: 4px; max-height: 4px;"
                )

    # ── Close event ───────────────────────────────────────────────────────────

    def closeEvent(self, event):
        self.engine_a.stop()
        self.engine_b.stop()
        if self.recorder.is_recording:
            self.recorder.stop_recording()
        event.accept()
