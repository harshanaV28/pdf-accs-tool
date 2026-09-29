"""
Export Dialog
Provides interactive options for exporting audit reports to PDF, HTML, JSON, or CSV formats.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QRadioButton,
    QPushButton, QGroupBox, QFileDialog, QButtonGroup
)
from PySide6.QtCore import Qt


class ExportDialog(QDialog):
    """Report export options dialog."""

    def __init__(self, default_filename: str = "report", parent=None):
        super().__init__(parent)
        self.default_filename = default_filename
        self.selected_format = "pdf"
        self.selected_filepath = ""
        self.setWindowTitle("Export Accessibility Audit Report")
        self.setFixedSize(400, 260)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        grp = QGroupBox("Select Report Format")
        l_grp = QVBoxLayout(grp)
        l_grp.setSpacing(8)

        self.rb_pdf = QRadioButton("📄 Formal PDF Audit Report (Publication-Grade)")
        self.rb_pdf.setChecked(True)
        l_grp.addWidget(self.rb_pdf)

        self.rb_html = QRadioButton("🌐 Interactive HTML Report (Standalone Browser View)")
        l_grp.addWidget(self.rb_html)

        self.rb_json = QRadioButton("⚙️ Machine-Readable JSON Export (CI/CD Pipeline)")
        l_grp.addWidget(self.rb_json)

        self.rb_csv = QRadioButton("📊 Spreadsheet CSV Export (Findings List)")
        l_grp.addWidget(self.rb_csv)

        layout.addWidget(grp)
        layout.addStretch()

        btns = QHBoxLayout()
        btns.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btns.addWidget(btn_cancel)

        btn_export = QPushButton("Choose Destination & Export")
        btn_export.setObjectName("primaryBtn")
        btn_export.clicked.connect(self._choose_and_export)
        btns.addWidget(btn_export)

        layout.addLayout(btns)

    def _choose_and_export(self):
        if self.rb_pdf.isChecked():
            fmt = "pdf"
            filter_str = "PDF Document (*.pdf)"
            ext = ".pdf"
        elif self.rb_html.isChecked():
            fmt = "html"
            filter_str = "HTML File (*.html)"
            ext = ".html"
        elif self.rb_json.isChecked():
            fmt = "json"
            filter_str = "JSON File (*.json)"
            ext = ".json"
        else:
            fmt = "csv"
            filter_str = "CSV File (*.csv)"
            ext = ".csv"

        path, _ = QFileDialog.getSaveFileName(
            self,
            f"Save {fmt.upper()} Report",
            f"{self.default_filename}_accessibility_report{ext}",
            filter_str
        )
        if path:
            self.selected_format = fmt
            self.selected_filepath = path
            self.accept()
