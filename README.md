# 🎧 DJ Mixer - Python

Ứng dụng DJ Mixer desktop được viết bằng Python, phục vụ môn học **Lập trình Âm thanh**.

## Tính năng
- Load và phát 2 track nhạc đồng thời (Deck A & Deck B)
- Crossfader để blend âm thanh giữa 2 deck
- Điều chỉnh BPM / tempo và pitch từng deck
- Hiệu ứng âm thanh: EQ (Bass/Mid/Treble), Reverb, Echo, Low-pass / High-pass filter
- Waveform visualization theo thời gian thực
- Ghi âm output ra file WAV

## Tech Stack
- **GUI**: PyQt6
- **Audio Playback**: pygame, pyaudio, soundfile
- **Audio Processing**: librosa, scipy, numpy
- **Waveform**: pyqtgraph
- **Testing**: pytest

## Cài đặt

```bash
# Tạo virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Linux/Mac

# Cài dependencies
pip install -r requirements.txt
```

> **Lưu ý Windows**: Nếu `pyaudio` báo lỗi, dùng:
> ```bash
> pip install pipwin && pipwin install pyaudio
> ```

## Chạy ứng dụng

```bash
python main.py
```

## Chạy tests

```bash
pytest tests/ -v
```

## Cấu trúc thư mục

```
dj_mixer/
├── main.py
├── requirements.txt
├── core/
│   ├── audio_engine.py     # Load, play, pause, seek
│   ├── mixer.py            # Crossfader, volume mixing
│   ├── effects.py          # EQ, reverb, echo, filter
│   └── bpm_detector.py     # BPM detection & tempo control
├── gui/
│   ├── main_window.py      # Cửa sổ chính
│   ├── deck_widget.py      # UI Deck A/B
│   ├── mixer_panel.py      # Crossfader panel
│   ├── effects_panel.py    # Effects controls
│   └── waveform_widget.py  # Waveform display
├── utils/
│   ├── audio_recorder.py   # Ghi âm output
│   └── file_handler.py     # Load file nhạc
└── tests/
    ├── test_audio_engine.py
    ├── test_mixer.py
    ├── test_effects.py
    └── test_bpm_detector.py
```

## Nhóm thực hiện
- Thành viên 1: Audio Engine & File Handler
- Thành viên 2: Mixer Logic & Crossfader
- Thành viên 3: Audio Effects (EQ, Reverb, Echo, Filter)
- Thành viên 4: BPM Detection & Tempo Control
- Thành viên 5: GUI & Waveform Visualization
- Thành viên 6: Recording, Integration & Documentation
