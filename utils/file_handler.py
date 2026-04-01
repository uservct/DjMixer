"""
utils/file_handler.py
─────────────────────
Thành viên 1 – File Handler

Xử lý việc mở, validate và đọc metadata từ file âm thanh.
Hỗ trợ: WAV, FLAC, OGG (thông qua soundfile).
MP3 cần pydub/ffmpeg nếu muốn đọc trực tiếp bằng soundfile.
"""

import os
from pathlib import Path

SUPPORTED_EXTENSIONS = {".wav", ".flac", ".ogg", ".mp3", ".aiff", ".aif"}


def is_supported_file(file_path: str) -> bool:
    """Kiểm tra xem file có phải định dạng được hỗ trợ không."""
    ext = Path(file_path).suffix.lower()
    return ext in SUPPORTED_EXTENSIONS


def get_file_info(file_path: str) -> dict:
    """
    Trả về thông tin metadata của file âm thanh.

    Returns
    -------
    dict với các key:
      - name     : tên file (không có đường dẫn)
      - path     : đường dẫn đầy đủ
      - size_mb  : kích thước file (MB)
      - extension: phần mở rộng
      - supported: bool
    """
    path = Path(file_path)
    size_mb = path.stat().st_size / (1024 * 1024) if path.exists() else 0.0

    info = {
        "name": path.name,
        "path": str(path.absolute()),
        "size_mb": round(size_mb, 2),
        "extension": path.suffix.lower(),
        "supported": is_supported_file(file_path),
    }

    # Cố đọc thêm thông tin bằng soundfile
    try:
        import soundfile as sf
        with sf.SoundFile(file_path) as f:
            info["sample_rate"] = f.samplerate
            info["channels"] = f.channels
            info["frames"] = f.frames
            info["duration"] = round(f.frames / f.samplerate, 2)
            info["format"] = f.format
    except Exception:  # noqa: BLE001
        pass

    return info


def format_duration(seconds: float) -> str:
    """Chuyển đổi số giây thành chuỗi mm:ss."""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"


def open_file_dialog(parent=None) -> str:
    """
    Mở hộp thoại chọn file nhạc (PyQt6).
    Trả về đường dẫn file được chọn, hoặc chuỗi rỗng nếu người dùng hủy.
    """
    try:
        from PyQt6.QtWidgets import QFileDialog
        ext_filter = "Audio Files (*.wav *.flac *.ogg *.mp3 *.aiff *.aif);;All Files (*)"
        file_path, _ = QFileDialog.getOpenFileName(
            parent, "Chọn file nhạc", "", ext_filter
        )
        return file_path
    except Exception as exc:  # noqa: BLE001
        print(f"[FileHandler] open_file_dialog lỗi: {exc}")
        return ""
