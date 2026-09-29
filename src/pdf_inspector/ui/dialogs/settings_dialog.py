"""
Settings Dialog
Configuration options for standards conformance levels and UI theme.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QCheckBox, QPushButton, QGroupBox
)
from PySide6.QtCore import Qt


class SettingsDialog(QDialog):
    """Application preferences and configuration dialog."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings & Preferences")
        self.setFixedSize(420, 320)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Standards Group
        grp_std = QGroupBox("Standards & Conformance Levels")
        l_std = QVBoxLayout(grp_std)

        l_std.addWidget(QLabel("Target WCAG Level:"))
        self.combo_wcag = QComboBox()
        self.combo_wcag.addItems(["WCAG 2.1 Level AA (Default)", "WCAG 2.1 Level AAA", "WCAG 2.2 Level AA"])
        l_std.addWidget(self.combo_wcag)

        self.chk_matterhorn = QCheckBox("Enable Matterhorn Protocol 1.1 Automated Rules")
        self.chk_matterhorn.setChecked(True)
        l_std.addWidget(self.chk_matterhorn)

        self.chk_quality = QCheckBox("Include Authoring Quality & Heuristic Warnings")
        self.chk_quality.setChecked(True)
        l_std.addWidget(self.chk_quality)

        layout.addWidget(grp_std)

        # UI & Reporting Group
        grp_ui = QGroupBox("Reporting & Display")
        l_ui = QVBoxLayout(grp_ui)

        self.chk_auto_jump = QCheckBox("Automatically jump to page on finding click")
        self.chk_auto_jump.setChecked(True)
        l_ui.addWidget(self.chk_auto_jump)

        self.chk_high_dpi = QCheckBox("Enable High-DPI canvas rendering")
        self.chk_high_dpi.setChecked(True)
        l_ui.addWidget(self.chk_high_dpi)

        layout.addWidget(grp_ui)
        layout.addStretch()

        # Buttons
        btns = QHBoxLayout()
        btns.addStretch()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btns.addWidget(btn_cancel)

        btn_save = QPushButton("Save Preferences")
        btn_save.setObjectName("primaryBtn")
        btn_save.clicked.connect(self.accept)
        btns.addWidget(btn_save)

        layout.addLayout(btns)
