"""
About Dialog
Displays version, standards support, authoring, and legal compliance notice.
"""

from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
from PySide6.QtCore import Qt


class AboutDialog(QDialog):
    """About dialog for PDF Accessibility Inspector."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About PDF Accessibility Inspector")
        self.setFixedSize(500, 360)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # Title & Icon
        title_box = QHBoxLayout()
        lbl_icon = QLabel("🔍")
        lbl_icon.setStyleSheet("font-size: 32px;")
        title_box.addWidget(lbl_icon)

        v_titles = QVBoxLayout()
        lbl_name = QLabel("PDF Accessibility Inspector")
        lbl_name.setStyleSheet("font-size: 17px; font-weight: 800; color: #0f172a;")
        lbl_ver = QLabel("Version 1.0.0 (Windows 64-bit Standalone)")
        lbl_ver.setStyleSheet("font-size: 11px; color: #64748b;")
        v_titles.addWidget(lbl_name)
        v_titles.addWidget(lbl_ver)
        title_box.addLayout(v_titles)
        title_box.addStretch()
        layout.addLayout(title_box)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: #e2e8f0;")
        layout.addWidget(line)

        # Description
        desc = QLabel(
            "<b>Independent Professional Desktop Accessibility Tool</b><br/><br/>"
            "Engineered for comprehensive validation, interactive structural inspection, "
            "and remediation guidance based on international standards:<br/>"
            "• <b>PDF/UA-1</b> (ISO 14289-1:2014)<br/>"
            "• <b>PDF 1.7 / 2.0</b> (ISO 32000-1 / ISO 32000-2)<br/>"
            "• <b>WCAG 2.1 & 2.2</b> (Level A and AA)<br/>"
            "• <b>Matterhorn Protocol 1.1</b> Checkpoint Model<br/><br/>"
            "<span style='font-size:11px; color:#64748b;'>"
            "Legal Notice: This is an independent clean-room engineering implementation "
            "utilizing open specifications and open-source PDF parsing engines. "
            "Not affiliated with, derived from, or endorsed by PAC or third-party proprietary software."
            "</span>"
        )
        desc.setWordWrap(True)
        layout.addWidget(desc)

        layout.addStretch()

        # Close button
        btn_close = QPushButton("Close")
        btn_close.setFixedWidth(100)
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close, alignment=Qt.AlignRight)
