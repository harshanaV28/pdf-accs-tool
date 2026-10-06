"""
Document & Metadata View
Displays comprehensive document catalog properties, XMP metadata stream,
Dublin Core entries, viewer preferences, and encryption permissions.
"""

from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QGroupBox, QTextBrowser, QSplitter, QLabel
)
from PySide6.QtCore import Qt
from ...core.models import PDFDocumentModel


class MetadataView(QWidget):
    """View presenting document catalog, XMP, and metadata."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        splitter = QSplitter(Qt.Vertical)

        # 1. Properties Table
        table_container = QWidget()
        t_layout = QVBoxLayout(table_container)
        t_layout.setContentsMargins(0, 0, 0, 0)

        lbl = QLabel("Document Properties & Catalog Settings")
        lbl.setStyleSheet("font-weight: 700; font-size: 13px; color: #1e293b;")
        t_layout.addWidget(lbl)

        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Property", "Value"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        t_layout.addWidget(self.table)

        splitter.addWidget(table_container)

        # 2. Raw Info & RoleMap dictionary box
        box_container = QWidget()
        b_layout = QVBoxLayout(box_container)
        b_layout.setContentsMargins(0, 0, 0, 0)

        lbl_raw = QLabel("RoleMap & Metadata Streams")
        lbl_raw.setStyleSheet("font-weight: 700; font-size: 13px; color: #1e293b;")
        b_layout.addWidget(lbl_raw)

        self.txt_raw = QTextBrowser()
        self.txt_raw.setStyleSheet("background: #f8fafc; border: 1px solid #e2e8f0; font-family: monospace; font-size: 11px;")
        b_layout.addWidget(self.txt_raw)

        splitter.addWidget(box_container)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        layout.addWidget(splitter)

    def load_document(self, doc: PDFDocumentModel):
        """Populates document metadata table."""
        title_display = doc.xmp_dc_title or (f"{doc.doc_info_title} (Trailer /Info only)" if doc.doc_info_title else "(Not specified)")
        props = [
            ("File Name", doc.filename),
            ("File Location", doc.filepath),
            ("File Size", f"{round(doc.filesize / 1024, 1)} KB ({doc.filesize:,} bytes)"),
            ("Page Count", str(doc.page_count)),
            ("PDF Version", f"PDF {doc.pdf_version}"),
            ("Document Title (Effective)", doc.title or "(Not specified)"),
            ("XMP Dublin Core Title (<dc:title>)", doc.xmp_dc_title or "(Missing from XMP)"),
            ("Legacy /Info Title", doc.doc_info_title or "(Not specified)"),
            ("Author / Creator", doc.xmp_dc_creator or doc.author or "(Not specified)"),
            ("Subject / Description", doc.xmp_dc_description or doc.subject or "(Not specified)"),
            ("Keywords", doc.keywords or "(Not specified)"),
            ("Application / Producer", f"{doc.creator or ''} / {doc.producer or ''}".strip(" /") or "(Not specified)"),
            ("Creation Date", doc.creation_date or "(Not specified)"),
            ("Modification Date", doc.modification_date or "(Not specified)"),
            ("Primary Language", doc.language or "(Not specified)"),
            ("Tagged PDF Status", "Yes (/MarkInfo /Marked true)" if doc.is_tagged else "No (Untagged)"),
            ("DisplayDocTitle (Initial View)", "Yes (true)" if doc.display_doc_title else "No (false)"),
            ("PDF/UA-1 Identifier", f"Yes (Part {doc.pdfua_part or 1})" if doc.pdfua_identifier_present else "No (Missing XMP PDF/UA identifier)"),
            ("XMP Metadata Stream", "Yes (Present)" if doc.xmp_metadata_present else "No (Missing)"),
            ("Encrypted", "Yes" if doc.is_encrypted else "No (Unencrypted)"),
            ("Accessibility Extraction Allowed", "Yes" if doc.allows_extraction else "No (Restricted)"),
        ]

        self.table.setRowCount(len(props))
        for row, (k, v) in enumerate(props):
            item_k = QTableWidgetItem(k)
            item_k.setFont(self.font())
            item_k.setFlags(item_k.flags() ^ Qt.ItemIsEditable)

            item_v = QTableWidgetItem(str(v))
            item_v.setFlags(item_v.flags() ^ Qt.ItemIsEditable)

            self.table.setItem(row, 0, item_k)
            self.table.setItem(row, 1, item_v)

        # Build raw details
        raw_text = ["=== ROLE MAP ENTRIES ==="]
        if doc.role_map:
            for custom_tag, target_tag in doc.role_map.items():
                raw_text.append(f"<{custom_tag}>  -->  <{target_tag}>")
        else:
            raw_text.append("No custom RoleMap dictionary defined in StructTreeRoot.")

        raw_text.append("\n=== DOCUMENT INFO DICTIONARY ===")
        for k, v in doc.raw_metadata.items():
            raw_text.append(f"/{k}: {v}")

        self.txt_raw.setPlainText("\n".join(raw_text))
