"""
Top Navigation Ribbon
Application header with title branding, document open shortcuts, rescan, export, and settings.
"""

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QPushButton, QToolButton,
    QMenu, QSizePolicy
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QAction, QFont


class TopBar(QWidget):
    """Top application ribbon bar."""

    open_pdf_requested = Signal()
    open_folder_requested = Signal()
    batch_scan_requested = Signal()
    rescan_requested = Signal()
    export_report_requested = Signal()
    settings_requested = Signal()
    about_requested = Signal()
    help_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        self.setFixedHeight(54)
        self.setStyleSheet("""
            TopBar {
                background-color: #ffffff;
                border-bottom: 1px solid #e2e8f0;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 6, 14, 6)
        layout.setSpacing(10)

        # Brand Title
        brand_layout = QHBoxLayout()
        brand_layout.setSpacing(8)

        lbl_logo = QLabel("🔍")
        lbl_logo.setStyleSheet("font-size: 20px;")
        brand_layout.addWidget(lbl_logo)

        lbl_app = QLabel("PDF Accessibility Inspector")
        lbl_app.setFont(QFont("Segoe UI", 12, QFont.Bold))
        lbl_app.setStyleSheet("color: #0f172a;")
        brand_layout.addWidget(lbl_app)

        layout.addLayout(brand_layout)
        layout.addSpacing(20)

        # Action Buttons
        self.btn_open = QPushButton("📂 Open PDF")
        self.btn_open.setObjectName("primaryBtn")
        self.btn_open.clicked.connect(self.open_pdf_requested)
        layout.addWidget(self.btn_open)

        self.btn_batch = QPushButton("📁 Batch Scan")
        self.btn_batch.clicked.connect(self.batch_scan_requested)
        layout.addWidget(self.btn_batch)

        self.btn_rescan = QPushButton("🔄 Rescan")
        self.btn_rescan.setEnabled(False)
        self.btn_rescan.clicked.connect(self.rescan_requested)
        layout.addWidget(self.btn_rescan)

        self.btn_export = QPushButton("📄 Export Report")
        self.btn_export.setEnabled(False)
        self.btn_export.clicked.connect(self.export_report_requested)
        layout.addWidget(self.btn_export)

        layout.addStretch()

        # Settings & About
        self.btn_settings = QPushButton("⚙️ Settings")
        self.btn_settings.clicked.connect(self.settings_requested)
        layout.addWidget(self.btn_settings)

        self.btn_help = QPushButton("❓ Help")
        self.btn_help.clicked.connect(self.help_requested)
        layout.addWidget(self.btn_help)

        self.btn_about = QPushButton("ℹ️ About")
        self.btn_about.clicked.connect(self.about_requested)
        layout.addWidget(self.btn_about)

    def set_document_loaded(self, loaded: bool):
        self.btn_rescan.setEnabled(loaded)
        self.btn_export.setEnabled(loaded)
