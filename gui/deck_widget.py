"""
gui/deck_widget.py
──────────────────
Thành viên 5 – Deck Widget (UI cho mỗi Deck A / B)

Hiển thị:
  - Tên track đang load
  - Waveform
  - Các nút: Load, Play/Pause, Stop
  - Slider seek (vị trí phát)
  - Slider volume
  - Hiển thị BPM, thời gian phát
  - Slider tempo & pitch (từ BPMDetector)
"""

import os
import threading
from queue import Queue, Empty
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSlider, QFileDialog, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer

from core.audio_engine import AudioEngine
from core.bpm_detector import BPMDetector
from gui.waveform_widget import WaveformWidget
from utils.file_handler import format_duration, is_supported_file


class DeckWidget(QWidget):
    """
    Widget hoàn chỉnh cho một Deck (A hoặc B).
    """

    DECK_COLORS = {
        "A": {"accent": "#00e5ff", "btn_play": "#00bcd4", "btn_stop": "#ef5350"},
        "B": {"accent": "#ff4081", "btn_play": "#e91e8c", "btn_stop": "#ef5350"},
    }

    def __init__(self, engine: AudioEngine, bpm_detector: BPMDetector,
                 deck_id: str = "A", parent=None):
        super().__init__(parent)
        self.engine = engine
        self.bpm_detector = bpm_detector
        self.deck_id = deck_id
        self.colors = self.DECK_COLORS.get(deck_id, self.DECK_COLORS["A"])

        self._seeking = False  # Đang kéo seek slider không?
        self._bpm_task_id = 0
        self._bpm_queue: Queue = Queue()

        self._build_ui()
        self._connect_signals()

        # Timer cập nhật UI mỗi 100ms
        self._ui_timer = QTimer(self)
        self._ui_timer.setInterval(100)
        self._ui_timer.timeout.connect(self._update_ui)
        self._ui_timer.start()

        # Callback khi track kết thúc
        self.engine.on_track_end = self._on_track_end

    # ── Build UI ──────────────────────────────────────────────────────────────

    def _build_ui(self):
        accent = self.colors["accent"]
        self.setStyleSheet(f"""
            QWidget {{
                background: transparent;
            }}
            QLabel#deck_label {{
                color: {accent};
                font-size: 16px;
                font-weight: bold;
                letter-spacing: 2px;
            }}
            QLabel#track_name {{
                color: #c9d1d9;
                font-size: 11px;
            }}
            QLabel#time_label {{
                color: {accent};
                font-size: 22px;
                font-weight: bold;
                font-family: 'Courier New', monospace;
            }}
            QLabel#bpm_label {{
                color: #8b949e;
                font-size: 12px;
            }}
            QPushButton {{
                border-radius: 6px;
                padding: 6px 14px;
                font-weight: bold;
                font-size: 12px;
                border: none;
                color: #0d1117;
            }}
            QPushButton#btn_load {{
                background: #30363d;
                color: #c9d1d9;
                border: 1px solid #484f58;
            }}
            QPushButton#btn_load:hover {{
                background: #484f58;
            }}
            QPushButton#btn_play {{
                background: {self.colors['btn_play']};
            }}
            QPushButton#btn_play:hover {{
                background: {accent};
            }}
            QPushButton#btn_stop {{
                background: #ef5350;
            }}
            QPushButton#btn_stop:hover {{
                background: #f44336;
            }}
            QSlider::groove:horizontal {{
                border-radius: 3px;
                height: 6px;
                background: #21262d;
            }}
            QSlider::handle:horizontal {{
                background: {accent};
                border-radius: 7px;
                width: 14px;
                height: 14px;
                margin: -4px 0;
            }}
            QSlider::sub-page:horizontal {{
                background: {accent};
                border-radius: 3px;
            }}
            QFrame#deck_frame {{
                background: rgba(22, 27, 34, 0.9);
                border: 1px solid {accent}55;
                border-radius: 14px;
            }}
        """)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        # Frame chứa toàn bộ deck
        frame = QFrame()
        frame.setObjectName("deck_frame")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        # ── Header: Deck label + tên track ──
        header = QHBoxLayout()
        self.lbl_deck = QLabel(f"DECK {self.deck_id}")
        self.lbl_deck.setObjectName("deck_label")
        self.lbl_track = QLabel("— Chưa load track —")
        self.lbl_track.setObjectName("track_name")
        self.lbl_track.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        header.addWidget(self.lbl_deck)
        header.addWidget(self.lbl_track)
        header.addStretch()

        # Load button
        self.btn_load = QPushButton("📂 Load")
        self.btn_load.setObjectName("btn_load")
        self.btn_load.setFixedWidth(90)
        header.addWidget(self.btn_load)
        layout.addLayout(header)

        # ── Waveform ──
        self.waveform = WaveformWidget(deck_id=self.deck_id)
        self.waveform.set_position_getter(self.engine.get_position)
        layout.addWidget(self.waveform)

        # ── Seek slider ──
        self.seek_slider = QSlider(Qt.Orientation.Horizontal)
        self.seek_slider.setRange(0, 1000)
        self.seek_slider.setValue(0)
        layout.addWidget(self.seek_slider)

        # ── Thời gian + BPM ──
        info_row = QHBoxLayout()
        self.lbl_time = QLabel("00:00 / 00:00")
        self.lbl_time.setObjectName("time_label")
        info_row.addWidget(self.lbl_time)
        info_row.addStretch()
        self.lbl_bpm = QLabel("BPM: —")
        self.lbl_bpm.setObjectName("bpm_label")
        info_row.addWidget(self.lbl_bpm)
        layout.addLayout(info_row)

        # ── Play / Stop buttons ──
        btn_row = QHBoxLayout()
        self.btn_play = QPushButton("▶ Play")
        self.btn_play.setObjectName("btn_play")
        self.btn_play.setFixedHeight(36)
        self.btn_stop = QPushButton("■ Stop")
        self.btn_stop.setObjectName("btn_stop")
        self.btn_stop.setFixedHeight(36)
        self.btn_stop.setFixedWidth(80)
        btn_row.addWidget(self.btn_play)
        btn_row.addWidget(self.btn_stop)
        layout.addLayout(btn_row)

        # ── Volume slider ──
        vol_row = QHBoxLayout()
        lbl_vol = QLabel("VOL")
        lbl_vol.setStyleSheet(f"color: #8b949e; font-size: 10px; font-weight: bold;")
        lbl_vol.setFixedWidth(30)
        self.vol_slider = QSlider(Qt.Orientation.Horizontal)
        self.vol_slider.setRange(0, 100)
        self.vol_slider.setValue(100)
        vol_row.addWidget(lbl_vol)
        vol_row.addWidget(self.vol_slider)
        layout.addLayout(vol_row)

        # ── Tempo slider ──
        tempo_row = QHBoxLayout()
        lbl_tempo = QLabel("BPM±")
        lbl_tempo.setStyleSheet(f"color: #8b949e; font-size: 10px; font-weight: bold;")
        lbl_tempo.setFixedWidth(30)
        self.tempo_slider = QSlider(Qt.Orientation.Horizontal)
        self.tempo_slider.setRange(50, 200)   # 50% → 200% of original tempo
        self.tempo_slider.setValue(100)
        self.lbl_tempo_val = QLabel("1.00×")
        self.lbl_tempo_val.setStyleSheet(f"color: {accent}; font-size: 10px; min-width: 36px;")
        tempo_row.addWidget(lbl_tempo)
        tempo_row.addWidget(self.tempo_slider)
        tempo_row.addWidget(self.lbl_tempo_val)
        layout.addLayout(tempo_row)

        # ── Pitch slider ──
        pitch_row = QHBoxLayout()
        lbl_pitch = QLabel("KEY")
        lbl_pitch.setStyleSheet(f"color: #8b949e; font-size: 10px; font-weight: bold;")
        lbl_pitch.setFixedWidth(30)
        self.pitch_slider = QSlider(Qt.Orientation.Horizontal)
        self.pitch_slider.setRange(-12, 12)
        self.pitch_slider.setValue(0)
        self.lbl_pitch_val = QLabel("0")
        self.lbl_pitch_val.setStyleSheet(f"color: {accent}; font-size: 10px; min-width: 20px;")
        pitch_row.addWidget(lbl_pitch)
        pitch_row.addWidget(self.pitch_slider)
        pitch_row.addWidget(self.lbl_pitch_val)
        layout.addLayout(pitch_row)

        outer.addWidget(frame)

    # ── Connect signals ───────────────────────────────────────────────────────

    def _connect_signals(self):
        self.btn_load.clicked.connect(self._on_load)
        self.btn_play.clicked.connect(self._on_play_pause)
        self.btn_stop.clicked.connect(self._on_stop)
        self.vol_slider.valueChanged.connect(self._on_volume_changed)
        self.tempo_slider.valueChanged.connect(self._on_tempo_changed)
        self.pitch_slider.valueChanged.connect(self._on_pitch_changed)

        self.seek_slider.sliderPressed.connect(lambda: setattr(self, "_seeking", True))
        self.seek_slider.sliderReleased.connect(self._on_seek_released)

    # ── Slots ─────────────────────────────────────────────────────────────────

    def _on_load(self):
        path, _ = QFileDialog.getOpenFileName(
            self, f"Load Track – Deck {self.deck_id}",
            "", "Audio Files (*.wav *.flac *.ogg *.mp3 *.aiff);;All Files (*)"
        )
        if not path:
            return

        self.lbl_track.setText("⏳ Đang load...")
        self.btn_load.setEnabled(False)

        ok = self.engine.load(path)
        self.btn_load.setEnabled(True)

        if ok:
            name = os.path.basename(path)
            self.lbl_track.setText(name)
            self.waveform.set_waveform(self.engine.waveform, self.engine.duration)
            self.seek_slider.setValue(0)
            self._start_bpm_detection(path)
        else:
            self.lbl_track.setText("❌ Lỗi load file! (Thử dùng WAV/OGG)")

    def _start_bpm_detection(self, path: str):
        self._bpm_task_id += 1
        task_id = self._bpm_task_id
        self.lbl_bpm.setText("BPM: đang tính...")

        thread = threading.Thread(
            target=self._run_bpm_detection,
            args=(task_id, path),
            daemon=True,
        )
        thread.start()

        # Poll kết quả trong main thread (tránh update UI từ thread nền)
        QTimer.singleShot(100, lambda: self._poll_bpm_result(task_id, elapsed_ms=0))

    def _run_bpm_detection(self, task_id: int, path: str):
        try:
            bpm = self.bpm_detector.detect_bpm_from_file(path)
            # Fallback nếu detect từ file thất bại
            if bpm <= 0 and len(self.engine.waveform) > 0:
                bpm = self.bpm_detector.detect_bpm(self.engine.waveform)
            self._bpm_queue.put((task_id, float(bpm), None))
        except Exception as exc:  # noqa: BLE001
            self._bpm_queue.put((task_id, 0.0, str(exc)))

    def _poll_bpm_result(self, task_id: int, elapsed_ms: int):
        # Timeout mềm để tránh kẹt vĩnh viễn ở "đang tính..."
        if elapsed_ms >= 12000:
            if task_id == self._bpm_task_id:
                self.lbl_bpm.setText("BPM: —")
            return

        try:
            while True:
                result_task_id, bpm, err = self._bpm_queue.get_nowait()

                # Bỏ kết quả cũ (task đã bị thay thế do user load track mới)
                if result_task_id != self._bpm_task_id:
                    continue

                if err:
                    print(f"[Deck {self.deck_id}] BPM error: {err}")
                    self.lbl_bpm.setText("BPM: —")
                else:
                    self.lbl_bpm.setText(f"BPM: {bpm:.1f}" if bpm > 0 else "BPM: —")
                return
        except Empty:
            QTimer.singleShot(
                100,
                lambda: self._poll_bpm_result(task_id, elapsed_ms + 100),
            )

    def _on_play_pause(self):
        if not self.engine.is_loaded():
            return  # Chưa load file → không làm gì
        self.engine.toggle_play_pause()
        self._update_play_btn()

    def _on_stop(self):
        self.engine.stop()
        self._update_play_btn()
        self.seek_slider.setValue(0)

    def _on_volume_changed(self, value: int):
        self.engine.volume = value / 100.0

    def _on_tempo_changed(self, value: int):
        # value: 50 → 200 tương ứng với speed 0.5× → 2.0×
        ratio = value / 100.0
        self.engine.speed_ratio = ratio
        self.bpm_detector.tempo_ratio = ratio
        self.lbl_tempo_val.setText(f"{ratio:.2f}×")

    def _on_pitch_changed(self, value: int):
        self.bpm_detector.pitch_steps = float(value)
        sign = "+" if value > 0 else ""
        self.lbl_pitch_val.setText(f"{sign}{value}")

    def _on_seek_released(self):
        self._seeking = False
        ratio = self.seek_slider.value() / 1000.0
        self.engine.seek(ratio * self.engine.duration)

    def _on_track_end(self, deck_id: str):
        self._update_play_btn()

    # ── UI update timer ───────────────────────────────────────────────────────

    def _update_ui(self):
        # Cập nhật seek slider (chỉ khi không đang kéo)
        if not self._seeking and self.engine.duration > 0:
            ratio = self.engine.get_position_ratio()
            self.seek_slider.setValue(int(ratio * 1000))

        # Cập nhật time label
        pos = self.engine.get_position()
        dur = self.engine.duration
        self.lbl_time.setText(f"{format_duration(pos)} / {format_duration(dur)}")

        self._update_play_btn()

    def _update_play_btn(self):
        if self.engine.is_playing:
            self.btn_play.setText("⏸ Pause")
        else:
            self.btn_play.setText("▶ Play")
