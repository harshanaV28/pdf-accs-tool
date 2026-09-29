"""
Detailed Results View
Renders an exhaustive, interactive grid of all individual rule results with
filtering (All, Failures, Warnings, Passed, Manual), real-time search, and instant selection.
"""

from typing import List, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QPushButton, QLineEdit, QLabel, QComboBox, QButtonGroup
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QColor, QFont
from ...core.models import CheckResult, CheckStatus, Severity


class DetailedResultsView(QWidget):
    """Detailed findings list view."""

    finding_selected = Signal(object)  # CheckResult
    finding_double_clicked = Signal(object)  # CheckResult

    def __init__(self, parent=None):
        super().__init__(parent)
        self.all_findings: List[CheckResult] = []
        self.filtered_findings: List[CheckResult] = []
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # 1. Top Filters and Search Bar
        filter_bar = QHBoxLayout()
        filter_bar.setSpacing(6)

        # Filter Buttons
        self.btn_all = QPushButton("All")
        self.btn_all.setCheckable(True)
        self.btn_all.setChecked(True)

        self.btn_fail = QPushButton("Failures")
        self.btn_fail.setCheckable(True)

        self.btn_warn = QPushButton("Warnings")
        self.btn_warn.setCheckable(True)

        self.btn_manual = QPushButton("Manual Review")
        self.btn_manual.setCheckable(True)

        self.btn_pass = QPushButton("Passed")
        self.btn_pass.setCheckable(True)

        self.filter_group = QButtonGroup(self)
        self.filter_group.setExclusive(True)
        self.filter_group.addButton(self.btn_all)
        self.filter_group.addButton(self.btn_fail)
        self.filter_group.addButton(self.btn_warn)
        self.filter_group.addButton(self.btn_manual)
        self.filter_group.addButton(self.btn_pass)
        self.filter_group.buttonClicked.connect(self._apply_filters)

        filter_bar.addWidget(self.btn_all)
        filter_bar.addWidget(self.btn_fail)
        filter_bar.addWidget(self.btn_warn)
        filter_bar.addWidget(self.btn_manual)
        filter_bar.addWidget(self.btn_pass)

        filter_bar.addSpacing(15)

        # Standard Filter
        self.combo_std = QComboBox()
        self.combo_std.addItems(["All Standards", "PDF/UA", "WCAG", "Quality", "AI"])
        self.combo_std.currentTextChanged.connect(self._apply_filters)
        filter_bar.addWidget(self.combo_std)

        filter_bar.addStretch()

        # Search Input
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Search findings (Rule ID, message, evidence)...")
        self.search_input.setFixedWidth(280)
        self.search_input.textChanged.connect(self._apply_filters)
        filter_bar.addWidget(self.search_input)

        layout.addLayout(filter_bar)

        # 2. Results Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Status", "Rule ID", "Name", "Standard", "Page", "Finding Message"])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(True)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.setSectionResizeMode(1, QHeaderView.Fixed)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Fixed)
        header.setSectionResizeMode(4, QHeaderView.Fixed)
        header.setSectionResizeMode(5, QHeaderView.Stretch)

        self.table.setColumnWidth(0, 90)
        self.table.setColumnWidth(1, 130)
        self.table.setColumnWidth(3, 85)
        self.table.setColumnWidth(4, 60)

        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        self.table.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self.table)

        # 3. Bottom count indicator
        self.lbl_count = QLabel("Showing 0 findings")
        self.lbl_count.setStyleSheet("color: #64748b; font-size: 11px;")
        layout.addWidget(self.lbl_count)

    def set_findings(self, findings: List[CheckResult]):
        """Sets the complete list of findings and updates table."""
        self.all_findings = findings
        self._apply_filters()

    def filter_by_category(self, standard: str, category: str):
        """Pre-filters table by selected category from Checkpoints view."""
        self.combo_std.setCurrentText(standard if standard in ["PDF/UA", "WCAG", "Quality", "AI"] else "All Standards")
        self.search_input.setText(category)
        self.btn_all.setChecked(True)
        self._apply_filters()

    def _apply_filters(self):
        query = self.search_input.text().lower().strip()
        std_filter = self.combo_std.currentText()

        # Status filter
        status_filter = None
        if self.btn_fail.isChecked():
            status_filter = [CheckStatus.FAIL, CheckStatus.ERROR]
        elif self.btn_warn.isChecked():
            status_filter = [CheckStatus.WARNING]
        elif self.btn_manual.isChecked():
            status_filter = [CheckStatus.MANUAL_REVIEW]
        elif self.btn_pass.isChecked():
            status_filter = [CheckStatus.PASS]

        filtered = []
        for r in self.all_findings:
            if status_filter and r.status not in status_filter:
                continue
            if std_filter != "All Standards" and r.standard.upper() != std_filter.upper():
                continue
            if query:
                combined_text = f"{r.check_id} {r.name} {r.category} {r.message} {r.evidence}".lower()
                if query not in combined_text:
                    continue
            filtered.append(r)

        self.filtered_findings = filtered
        self._render_table()

    def _render_table(self):
        self.table.setRowCount(len(self.filtered_findings))
        for row, r in enumerate(self.filtered_findings):
            # Status icon & text
            status_text = r.status.value
            item_status = QTableWidgetItem(status_text)
            item_status.setTextAlignment(Qt.AlignCenter)
            if r.status in (CheckStatus.FAIL, CheckStatus.ERROR):
                item_status.setForeground(QColor("#dc2626"))
            elif r.status == CheckStatus.WARNING:
                item_status.setForeground(QColor("#b45309"))
            elif r.status == CheckStatus.PASS:
                item_status.setForeground(QColor("#166534"))
            elif r.status == CheckStatus.MANUAL_REVIEW:
                item_status.setForeground(QColor("#0369a1"))
            self.table.setItem(row, 0, item_status)

            # Rule ID
            item_id = QTableWidgetItem(r.check_id)
            item_id.setFont(QFont("Consolas", 10))
            self.table.setItem(row, 1, item_id)

            # Name
            item_name = QTableWidgetItem(r.name)
            item_name.setFont(QFont("Segoe UI", 10, QFont.Bold))
            self.table.setItem(row, 2, item_name)

            # Standard
            item_std = QTableWidgetItem(r.standard)
            item_std.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 3, item_std)

            # Page
            item_pg = QTableWidgetItem(str(r.page) if r.page else "Doc")
            item_pg.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 4, item_pg)

            # Message
            item_msg = QTableWidgetItem(r.message)
            self.table.setItem(row, 5, item_msg)

        self.lbl_count.setText(f"Showing {len(self.filtered_findings)} of {len(self.all_findings)} finding(s)")

    def _on_selection_changed(self):
        selected_rows = self.table.selectionModel().selectedRows()
        if selected_rows:
            idx = selected_rows[0].row()
            if 0 <= idx < len(self.filtered_findings):
                self.finding_selected.emit(self.filtered_findings[idx])

    def _on_item_double_clicked(self, item):
        row = item.row()
        if 0 <= row < len(self.filtered_findings):
            self.finding_double_clicked.emit(self.filtered_findings[row])
