# 🎧 DJ Mixer - Python

Ứng dụng DJ Mixer desktop viết bằng Python cho môn **Lập trình Âm thanh**.

## Tính năng chính

- Phát 2 deck độc lập: **Deck A** và **Deck B**
- Load file audio: `.wav`, `.flac`, `.ogg`, `.mp3`, `.aiff`, `.aif`
- Điều khiển transport: Play/Pause, Stop, Seek
- Mixer trung tâm:
    - Crossfader (Linear / Equal Power)
    - Master Volume
- Hiệu ứng real-time theo từng deck:
    - EQ 3 dải (Bass / Mid / Treble)
    - Low-pass / High-pass
    - Echo (delay + feedback)
    - Reverb
- Tempo & Pitch control trên từng deck
- BPM detection (chạy nền, không block UI)
- Waveform visualization + playhead theo thời gian thực
- Ghi âm master output ra file WAV trong thư mục `recordings/`

## Kiến trúc hiện tại

- `core/audio_engine.py`: playback bằng `sounddevice.OutputStream` + callback theo chunk
- `core/effects.py`: effects chain stateful cho xử lý liên tục giữa các chunk
- `core/mixer.py`: tính volume Deck A/B từ crossfader + master
- `core/bpm_detector.py`: BPM detect + xử lý tempo/pitch
- `gui/*`: giao diện PyQt6 (deck, mixer, effects, waveform, main window)
- `utils/audio_recorder.py`: thu và ghi master mix WAV
- `utils/file_handler.py`: validate file + metadata helpers

## Công nghệ sử dụng

- **GUI**: PyQt6
- **Playback/IO**: sounddevice, soundfile
- **DSP/Analysis**: numpy, scipy, librosa
- **Waveform**: pyqtgraph
- **Test**: pytest

## Cài đặt dependencies

### Cách 1 (khuyên dùng Windows) – 1 click

Chạy file [install_dependencies.bat](install_dependencies.bat):

- Lần đầu: tự tạo `venv`, cài pip từ `requirements.txt`, rồi chạy app.
- Các lần sau: chạy app luôn (bỏ qua cài đặt).

### Cách 2 – thủ công

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## Chạy ứng dụng

```bash
python main.py
```

hoặc double-click [Run_DjMixer.bat](Run_DjMixer.bat).

## Chạy tests

```bash
pytest tests/ -v
```

## Cấu trúc thư mục

```
DjMixer/
├── main.py
├── requirements.txt
├── Run_DjMixer.bat
├── core/
│   ├── audio_engine.py
│   ├── mixer.py
│   ├── effects.py
│   └── bpm_detector.py
├── gui/
│   ├── main_window.py
│   ├── deck_widget.py
│   ├── mixer_panel.py
│   ├── effects_panel.py
│   └── waveform_widget.py
├── utils/
│   ├── audio_recorder.py
│   └── file_handler.py
├── recordings/
└── tests/
        ├── test_audio_engine.py
        ├── test_mixer.py
        ├── test_effects.py
        └── test_bpm_detector.py
```

## Ghi chú

- Với file MP3, môi trường thiếu backend decode có thể gây lỗi đọc file; nên ưu tiên WAV/FLAC/OGG để ổn định.
- `run_djmixer.bat` hiện là wrapper gọi lại launcher chính.

## Nhóm thực hiện

- Thành viên 1: Audio Engine & File Handler
- Thành viên 2: Mixer Logic & Crossfader
- Thành viên 3: Audio Effects (EQ, Reverb, Echo, Filter)
- Thành viên 4: BPM Detection & Tempo Control
- Thành viên 5: GUI & Waveform Visualization
- Thành viên 6: Recording, Integration & Documentation
