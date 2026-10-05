"""
Semantic Reading Preview View
Simulates the document's logical reading sequence using PDF tags, structure elements,
headings, lists, figures, alternative text and other accessibility metadata.
This is a semantic preview and is not a replacement for testing with an actual screen reader.
"""

from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextBrowser, QLabel,
    QPushButton, QFrame, QFileDialog, QMessageBox, QApplication
)
from PySide6.QtCore import Qt
from ...core.models import PDFDocumentModel
from ...engine.semantic_reading import SemanticReadingEngine, SemanticReadingResult


class SemanticReaderView(QWidget):
    """View presenting the logical accessibility structure and semantic reading preview."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.engine = SemanticReadingEngine()
        self.last_result: Optional[SemanticReadingResult] = None
        self.current_doc: Optional[PDFDocumentModel] = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Header Card matching required specifications
        header = QFrame()
        header.setStyleSheet("background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 8px; padding: 12px;")
        h_layout = QVBoxLayout(header)
        h_layout.setContentsMargins(8, 6, 8, 6)
        h_layout.setSpacing(6)

        title_row = QHBoxLayout()
        info_title = QLabel("📖 <b>Semantic Reading Preview</b>")
        info_title.setStyleSheet("font-size: 14px; color: #1e3a8a; font-weight: 700;")
        title_row.addWidget(info_title)
        title_row.addStretch()

        self.btn_copy = QPushButton("📋 Copy Text")
        self.btn_copy.setToolTip("Copy semantic reading sequence as structured text")
        self.btn_copy.setStyleSheet("font-size: 11px; padding: 3px 8px;")
        self.btn_copy.clicked.connect(self._copy_text)
        title_row.addWidget(self.btn_copy)

        self.btn_export = QPushButton("💾 Export Transcript")
        self.btn_export.setToolTip("Save semantic preview to file (.txt or .html)")
        self.btn_export.setStyleSheet("font-size: 11px; padding: 3px 8px;")
        self.btn_export.clicked.connect(self._export_transcript)
        title_row.addWidget(self.btn_export)

        h_layout.addLayout(title_row)

        desc_lbl = QLabel(
            "Simulates the document's logical reading sequence using PDF tags, structure elements, headings, lists, "
            "figures, alternative text and other accessibility metadata. This is a semantic preview and is not a "
            "replacement for testing with an actual screen reader."
        )
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet("color: #334155; font-size: 12px; line-height: 1.4;")
        h_layout.addWidget(desc_lbl)

        info_notice = QLabel(
            "ℹ️ <i>Semantic preview based on PDF accessibility structure. Validate final reading behavior with a real screen reader.</i>"
        )
        info_notice.setWordWrap(True)
        info_notice.setMinimumWidth(100)
        info_notice.setStyleSheet("color: #64748b; font-size: 11px; border-top: 1px solid #dbeafe; padding-top: 4px;")
        h_layout.addWidget(info_notice)

        layout.addWidget(header)

        # Transcript display
        self.text_browser = QTextBrowser()
        self.text_browser.setOpenExternalLinks(True)
        self.text_browser.setStyleSheet("""
            QTextBrowser {
                background-color: #ffffff;
                border: 1px solid #cbd5e1;
                border-radius: 8px;
                padding: 16px;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", sans-serif;
                font-size: 13px;
                line-height: 1.6;
            }
        """)
        layout.addWidget(self.text_browser)

    def load_document(self, doc: PDFDocumentModel):
        """Generates and renders the semantic reading sequence."""
        self.current_doc = doc
        self.last_result = self.engine.generate(doc)
        self.text_browser.setHtml(self.last_result.html)

    def _copy_text(self):
        """Copies the plain text semantic stream to clipboard."""
        if not self.last_result:
            return
        clipboard = QApplication.clipboard()
        clipboard.setText(self.last_result.plain_text)
        QMessageBox.information(
            self, "Copied",
            "Semantic reading sequence copied to clipboard."
        )

    def _export_transcript(self):
        """Exports the semantic reading preview to a file."""
        if not self.last_result:
            return

        filepath, selected_filter = QFileDialog.getSaveFileName(
            self, "Export Semantic Reading Preview",
            "semantic_reading_preview.html",
            "HTML File (*.html);;Text File (*.txt)"
        )
        if not filepath:
            return

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                if filepath.endswith(".txt"):
                    f.write(self.last_result.plain_text)
                else:
                    f.write(self.last_result.html)
            QMessageBox.information(self, "Export Successful", f"Preview saved to:\n{filepath}")
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", f"Failed to save file:\n{e}")


# Backward-compatible alias for existing imports and test references
ScreenReaderView = SemanticReaderView
