"""
Dashboard View
Executive summary landing view with drag-and-drop zone and quick action shortcuts.
"""

from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QGridLayout, QScrollArea
)
from PySide6.QtCore import Qt, Signal
from ...core.models import AuditReport, PDFDocumentModel


class DashboardView(QWidget):
    """Landing dashboard view."""

    open_pdf_requested = Signal()
    view_details_requested = Signal()
    view_pdf_requested = Signal()
    export_report_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # 1. Welcome / Drop Zone Card
        self.drop_card = QFrame()
        self.drop_card.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border: 2px dashed #93c5fd;
                border-radius: 12px;
                padding: 30px;
            }
        """)
        dc_layout = QVBoxLayout(self.drop_card)
        dc_layout.setAlignment(Qt.AlignCenter)
        dc_layout.setSpacing(10)

        lbl_icon = QLabel("📄")
        lbl_icon.setStyleSheet("font-size: 42px;")
        lbl_icon.setAlignment(Qt.AlignCenter)
        dc_layout.addWidget(lbl_icon)

        self.lbl_drop_title = QLabel("Open a PDF or Drag and Drop Here")
        self.lbl_drop_title.setStyleSheet("font-size: 17px; font-weight: 700; color: #1e293b;")
        self.lbl_drop_title.setAlignment(Qt.AlignCenter)
        dc_layout.addWidget(self.lbl_drop_title)

        lbl_drop_sub = QLabel("Analyzes internal PDF structure, PDF/UA (ISO 14289-1), WCAG 2.1/2.2 AA, and generates audit reports.")
        lbl_drop_sub.setStyleSheet("font-size: 12px; color: #64748b;")
        lbl_drop_sub.setAlignment(Qt.AlignCenter)
        dc_layout.addWidget(lbl_drop_sub)

        self.btn_open = QPushButton("📂 Open PDF Document")
        self.btn_open.setObjectName("primaryBtn")
        self.btn_open.setFixedWidth(200)
        self.btn_open.clicked.connect(self.open_pdf_requested)
        dc_layout.addWidget(self.btn_open, alignment=Qt.AlignCenter)

        layout.addWidget(self.drop_card)

        # 2. Document Status Card (Hidden until loaded)
        self.status_card = QFrame()
        self.status_card.setStyleSheet("background: #ffffff; border: 1px solid #e2e8f0; border-radius: 10px; padding: 16px;")
        self.status_card.setVisible(False)
        sc_layout = QVBoxLayout(self.status_card)

        self.lbl_doc_title = QLabel("Document: -")
        self.lbl_doc_title.setStyleSheet("font-size: 15px; font-weight: 700; color: #0f172a;")
        sc_layout.addWidget(self.lbl_doc_title)

        self.lbl_doc_meta = QLabel("-")
        self.lbl_doc_meta.setStyleSheet("font-size: 12px; color: #64748b;")
        sc_layout.addWidget(self.lbl_doc_meta)

        # Action shortcuts
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(8)

        btn_view = QPushButton("🔍 View PDF Canvas")
        btn_view.clicked.connect(self.view_pdf_requested)
        actions_layout.addWidget(btn_view)

        btn_details = QPushButton("📋 Detailed Findings")
        btn_details.clicked.connect(self.view_details_requested)
        actions_layout.addWidget(btn_details)

        btn_rep = QPushButton("📄 Export PDF Report")
        btn_rep.clicked.connect(self.export_report_requested)
        actions_layout.addWidget(btn_rep)

        actions_layout.addStretch()
        sc_layout.addLayout(actions_layout)

        layout.addWidget(self.status_card)

        layout.addStretch()
        scroll.setWidget(container)
        main_layout.addWidget(scroll)

    def load_document(self, doc: PDFDocumentModel, report: AuditReport):
        """Displays loaded document summary on dashboard."""
        self.status_card.setVisible(True)
        self.lbl_drop_title.setText(f"Loaded: {doc.filename}")

        self.lbl_doc_title.setText(f"📄 {doc.filename} — Score: {report.compliance_score}%")
        self.lbl_doc_meta.setText(
            f"Pages: {doc.page_count} | Version: PDF {doc.pdf_version} | Tagged: {'Yes' if doc.is_tagged else 'No'} | "
            f"Passed: {report.total_passed} | Warnings: {report.total_warned} | Failures: {report.total_failed}"
        )
