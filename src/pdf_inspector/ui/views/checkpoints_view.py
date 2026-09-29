"""
Checkpoints View
Renders the primary tabbed inspection matrix matching the user reference screenshots:
Tabs for [PDF/UA], [WCAG], [Quality], [AI], columns for [Checkpoint], [Passed], [Warned], [Failed],
and bottom navigation toolbar buttons.
"""

from typing import Optional, Dict, List, Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QTableWidget,
    QTableWidgetItem, QHeaderView, QPushButton, QLabel, QFrame
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QIcon, QColor, QFont
from ...core.models import AuditReport, CheckStatus


class CheckpointTableWidget(QTableWidget):
    """Custom table displaying checkpoint categories with counts and status icons."""

    category_selected = Signal(str, str)  # (standard, category_name)

    def __init__(self, categories: List[str], standard_name: str, parent=None):
        super().__init__(parent)
        self.categories = categories
        self.standard_name = standard_name
        self._init_ui()

    def _init_ui(self):
        self.setColumnCount(4)
        self.setHorizontalHeaderLabels(["Checkpoint", "Passed", "Warned", "Failed"])
        self.verticalHeader().setVisible(False)
        self.setSelectionBehavior(QTableWidget.SelectRows)
        self.setSelectionMode(QTableWidget.SingleSelection)
        self.setEditTriggers(QTableWidget.NoEditTriggers)
        self.setShowGrid(True)
        self.setAlternatingRowColors(True)

        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Fixed)
        header.setSectionResizeMode(2, QHeaderView.Fixed)
        header.setSectionResizeMode(3, QHeaderView.Fixed)
        self.setColumnWidth(1, 100)
        self.setColumnWidth(2, 100)
        self.setColumnWidth(3, 100)

        self.setRowCount(len(self.categories))
        for row, cat in enumerate(self.categories):
            # Checkpoint name item
            item_name = QTableWidgetItem(f"🚫  {cat}")
            item_name.setFont(QFont("Segoe UI", 10))
            self.setItem(row, 0, item_name)

            # Passed, Warned, Failed counters initialized empty
            for col in range(1, 4):
                item_cnt = QTableWidgetItem("-")
                item_cnt.setTextAlignment(Qt.AlignCenter)
                self.setItem(row, col, item_cnt)

        self.cellDoubleClicked.connect(self._on_row_double_click)

    def update_counts(self, counts_by_cat: Dict[str, Dict[str, int]]):
        """Updates the row numbers and status icons based on actual audit results."""
        for row, cat in enumerate(self.categories):
            c_data = counts_by_cat.get(cat, {"passed": 0, "warned": 0, "failed": 0, "manual": 0})
            p = c_data["passed"]
            w = c_data["warned"]
            f = c_data["failed"]

            # Choose icon
            if f > 0:
                icon_str = "❌"
            elif w > 0:
                icon_str = "⚠️"
            elif p > 0:
                icon_str = "✅"
            else:
                icon_str = "⚪"

            item_name = self.item(row, 0)
            if item_name:
                item_name.setText(f"{icon_str}  {cat}")

            # Passed column
            item_p = self.item(row, 1)
            if item_p:
                item_p.setText(str(p) if p > 0 else "0")
                if p > 0:
                    item_p.setForeground(QColor("#166534"))
                    item_p.setFont(QFont("Segoe UI", 10, QFont.Bold))

            # Warned column
            item_w = self.item(row, 2)
            if item_w:
                item_w.setText(str(w) if w > 0 else "0")
                if w > 0:
                    item_w.setForeground(QColor("#b45309"))
                    item_w.setFont(QFont("Segoe UI", 10, QFont.Bold))

            # Failed column
            item_f = self.item(row, 3)
            if item_f:
                item_f.setText(str(f) if f > 0 else "0")
                if f > 0:
                    item_f.setForeground(QColor("#dc2626"))
                    item_f.setFont(QFont("Segoe UI", 10, QFont.Bold))

    def _on_row_double_click(self, row: int, col: int):
        if 0 <= row < len(self.categories):
            cat_name = self.categories[row]
            self.category_selected.emit(self.standard_name, cat_name)


class CheckpointsView(QWidget):
    """Container view providing the tabbed Checkpoints interface and bottom action toolbar."""

    request_rescan = Signal()
    request_detailed_results = Signal()
    request_pdf_report = Signal()
    request_tag_tree = Signal()
    request_statistics = Signal()
    request_preview = Signal()
    category_selected = Signal(str, str)  # (standard, category)

    PDF_UA_CATEGORIES = [
        "PDF Syntax (ISO 32000-1)",
        "Fonts",
        "Content",
        "Embedded Files",
        "Natural language",
        "Structure Elements",
        "Structure tree",
        "Role mapping",
        "Alternative Descriptions",
        "Metadata",
        "Document settings",
    ]

    WCAG_CATEGORIES = [
        "1.1 Text Alternatives",
        "1.2 Time-based Media",
        "1.3 Adaptable",
        "1.4 Distinguishable",
        "2.1 Keyboard Accessible",
        "2.2 Enough Time",
        "2.3 Seizures and Physical Reactions",
        "2.4 Navigable",
        "2.5 Input Modalities",
        "3.1 Readable",
        "3.2 Predictable",
        "3.3 Input Assistance",
        "4.1 Compatible",
    ]

    QUALITY_CATEGORIES = [
        "Heading Structure",
        "Table Quality",
        "Link Quality",
    ]

    AI_CATEGORIES = [
        "AI Alt-Text Evaluation",
        "Cognitive Accessibility",
        "Structural AI",
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Top row containing Tabs and Rescan button
        tabs_header_layout = QHBoxLayout()
        tabs_header_layout.setContentsMargins(6, 6, 6, 0)

        self.tab_widget = QTabWidget()

        # PDF/UA Table
        self.table_pdf_ua = CheckpointTableWidget(self.PDF_UA_CATEGORIES, "PDF/UA")
        self.table_pdf_ua.category_selected.connect(self.category_selected)
        self.tab_widget.addTab(self.table_pdf_ua, "PDF/UA")

        # WCAG Table
        self.table_wcag = CheckpointTableWidget(self.WCAG_CATEGORIES, "WCAG")
        self.table_wcag.category_selected.connect(self.category_selected)
        self.tab_widget.addTab(self.table_wcag, "WCAG")

        # Quality Table
        self.table_quality = CheckpointTableWidget(self.QUALITY_CATEGORIES, "Quality")
        self.table_quality.category_selected.connect(self.category_selected)
        self.tab_widget.addTab(self.table_quality, "Quality")

        # AI Table
        self.table_ai = CheckpointTableWidget(self.AI_CATEGORIES, "AI")
        self.table_ai.category_selected.connect(self.category_selected)
        self.tab_widget.addTab(self.table_ai, "AI")

        # Corner reload button matching screenshot
        self.btn_refresh = QPushButton("🔄")
        self.btn_refresh.setToolTip("Rescan Document")
        self.btn_refresh.setFixedSize(32, 28)
        self.btn_refresh.setStyleSheet("font-size: 14px; border-radius: 4px; background: #ffffff;")
        self.btn_refresh.clicked.connect(self.request_rescan)
        self.tab_widget.setCornerWidget(self.btn_refresh, Qt.TopRightCorner)

        main_layout.addWidget(self.tab_widget)

        # 2. Bottom Toolbar matching the screenshot layout
        bottom_bar = QFrame()
        bottom_bar.setStyleSheet("background-color: #f8fafc; border-top: 1px solid #e2e8f0; padding: 6px;")
        bottom_layout = QHBoxLayout(bottom_bar)
        bottom_layout.setContentsMargins(10, 4, 10, 4)
        bottom_layout.setSpacing(8)

        self.btn_detail = QPushButton("📋 Results in detail")
        self.btn_detail.clicked.connect(self.request_detailed_results)
        bottom_layout.addWidget(self.btn_detail)

        self.btn_report = QPushButton("📄 PDF report")
        self.btn_report.clicked.connect(self.request_pdf_report)
        bottom_layout.addWidget(self.btn_report)

        bottom_layout.addStretch()

        # Icon buttons: Tree, Stats, Preview
        self.btn_tree = QPushButton("🌳 Tag Tree")
        self.btn_tree.clicked.connect(self.request_tag_tree)
        bottom_layout.addWidget(self.btn_tree)

        self.btn_stats = QPushButton("📊 Statistics")
        self.btn_stats.clicked.connect(self.request_statistics)
        bottom_layout.addWidget(self.btn_stats)

        self.btn_preview = QPushButton("👁 Preview")
        self.btn_preview.clicked.connect(self.request_preview)
        bottom_layout.addWidget(self.btn_preview)

        main_layout.addWidget(bottom_bar)

    def update_report(self, report: AuditReport):
        """Updates all tables with report counts."""
        self.table_pdf_ua.update_counts(report.get_category_counts("PDF/UA"))
        self.table_wcag.update_counts(report.get_category_counts("WCAG"))
        self.table_quality.update_counts(report.get_category_counts("Quality"))
        self.table_ai.update_counts(report.get_category_counts("AI"))
