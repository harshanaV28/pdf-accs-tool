"""
PDF Accessibility Inspector - Main Application Entry Point
"""

import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from .ui.main_window import MainWindow


def main():
    # High-DPI support
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("PDF Accessibility Inspector")
    app.setOrganizationName("PDF Accessibility Inspector")
    app.setApplicationVersion("1.0.0")

    # Set icon if exists
    icon_path = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "icons", "app_icon.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    window = MainWindow()
    window.show()

    # Open file passed via command line argument (e.g. drag onto exe or Open With)
    if len(sys.argv) > 1:
        initial_file = sys.argv[1]
        if os.path.exists(initial_file) and initial_file.lower().endswith(".pdf"):
            window.load_pdf_file(initial_file)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
