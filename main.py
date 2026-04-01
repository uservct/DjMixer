"""
main.py
───────
Entry point của ứng dụng DJ Mixer.

Chạy:  python main.py
"""

import sys
import os

# Thêm root vào sys.path để import module trong project
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont, QFontDatabase
from PyQt6.QtCore import Qt


def main():
    # Cấu hình High DPI
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("DJ Mixer")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("LTAT Group")

    # Font mặc định
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    # Import sau khi QApplication đã tạo (tránh lỗi Qt)
    from gui.main_window import MainWindow

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
