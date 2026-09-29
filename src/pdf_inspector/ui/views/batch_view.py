"""
Batch Scan View
Scans multiple PDF documents in a directory and produces an aggregated compliance report.
"""

from typing import List, Dict, Any, Optional
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QFileDialog, QProgressBar, QLabel
)
from PySide6.QtCore import Qt, Signal
from ...core.document_parser import DocumentParser
from ...engine.runner import AuditRunner


class BatchScanView(QWidget):
    """View for scanning folders of PDF documents."""

    document_opened = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.runner = AuditRunner()
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Top bar
        top_layout = QHBoxLayout()
        self.btn_select_folder = QPushButton("📁 Select Folder to Batch Scan")
        self.btn_select_folder.setObjectName("primaryBtn")
        self.btn_select_folder.clicked.connect(self._select_folder)
        top_layout.addWidget(self.btn_select_folder)

        self.lbl_status = QLabel("Select a directory containing PDF files.")
        self.lbl_status.setStyleSheet("color: #64748b; font-size: 12px;")
        top_layout.addWidget(self.lbl_status)
        top_layout.addStretch()

        layout.addLayout(top_layout)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Batch results table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Filename", "Score", "Tagged", "Passed", "Warnings", "Failures"])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.itemDoubleClicked.connect(self._on_row_double_click)
        layout.addWidget(self.table)

    def _select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder Containing PDFs")
        if not folder:
            return

        pdf_files = [os.path.join(folder, f) for f in os.listdir(folder) if f.lower().endswith(".pdf")]
        if not pdf_files:
            self.lbl_status.setText(f"No PDF files found in {folder}.")
            return

        self.lbl_status.setText(f"Scanning {len(pdf_files)} PDF file(s)...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(len(pdf_files))
        self.progress_bar.setValue(0)

        self.table.setRowCount(len(pdf_files))
        for idx, pdf_path in enumerate(pdf_files):
            filename = os.path.basename(pdf_path)
            try:
                parser = DocumentParser(pdf_path)
                doc = parser.parse()
                report = self.runner.run(doc)

                self.table.setItem(idx, 0, QTableWidgetItem(filename))
                self.table.setItem(idx, 1, QTableWidgetItem(f"{report.compliance_score}%"))
                self.table.setItem(idx, 2, QTableWidgetItem("Yes" if doc.is_tagged else "No"))
                self.table.setItem(idx, 3, QTableWidgetItem(str(report.total_passed)))
                self.table.setItem(idx, 4, QTableWidgetItem(str(report.total_warned)))
                self.table.setItem(idx, 5, QTableWidgetItem(str(report.total_failed)))

                # Store full path in item user data
                self.table.item(idx, 0).setData(Qt.UserRole, pdf_path)
            except Exception as e:
                self.table.setItem(idx, 0, QTableWidgetItem(f"{filename} (Error)"))
                self.table.setItem(idx, 1, QTableWidgetItem("Err"))

            self.progress_bar.setValue(idx + 1)

        self.progress_bar.setVisible(False)
        self.lbl_status.setText(f"Completed scanning {len(pdf_files)} PDF file(s). Double-click a row to open.")

    def _on_row_double_click(self, item):
        row = item.row()
        item_zero = self.table.item(row, 0)
        if item_zero:
            pdf_path = item_zero.data(Qt.UserRole)
            if pdf_path and os.path.exists(pdf_path):
                self.document_opened.emit(pdf_path)
