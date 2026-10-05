"""
Finding Details Panel
Right sidebar panel showing exhaustive details for the currently selected CheckResult,
including technical evidence, standard citations, and actionable remediation steps.
"""

from typing import Optional, Dict, List, Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextBrowser,
    QPushButton, QGroupBox, QScrollArea, QFrame
)
from PySide6.QtCore import Signal, Qt
from ...core.models import CheckResult, CheckStatus, Severity
from .status_badge import StatusBadge, SeverityBadge


class FindingDetailsPanel(QWidget):
    """Inspector panel displaying rule evidence, explanation, and remediation."""

    highlight_requested = Signal(int, object)  # (page_num, bbox)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_finding: Optional[CheckResult] = None
        self._init_ui()

    def _init_ui(self):
        self.setMinimumWidth(280)
        self.setMaximumWidth(450)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Header title
        header_layout = QHBoxLayout()
        self.title_label = QLabel("Finding Details")
        self.title_label.setStyleSheet("font-size: 15px; font-weight: 700; color: #0f172a;")
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        main_layout.addLayout(header_layout)

        # Scroll Area for details
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(10)

        # 1. Summary Card
        self.summary_box = QGroupBox("Checkpoint")
        summary_layout = QVBoxLayout(self.summary_box)
        summary_layout.setSpacing(6)

        self.name_label = QLabel("No finding selected")
        self.name_label.setStyleSheet("font-weight: 600; font-size: 13px; color: #1e293b;")
        self.name_label.setWordWrap(True)
        summary_layout.addWidget(self.name_label)

        badges_layout = QHBoxLayout()
        self.status_badge = StatusBadge(CheckStatus.NOT_APPLICABLE)
        self.severity_badge = SeverityBadge(Severity.INFO)
        badges_layout.addWidget(self.status_badge)
        badges_layout.addWidget(self.severity_badge)
        badges_layout.addStretch()
        summary_layout.addLayout(badges_layout)

        # Metadata grid
        self.id_label = QLabel("Rule ID: -")
        self.id_label.setStyleSheet("color: #64748b; font-size: 11px;")
        summary_layout.addWidget(self.id_label)

        self.standard_label = QLabel("Standard: -")
        self.standard_label.setStyleSheet("color: #64748b; font-size: 11px;")
        summary_layout.addWidget(self.standard_label)

        self.page_label = QLabel("Page: -")
        self.page_label.setStyleSheet("color: #64748b; font-size: 11px;")
        summary_layout.addWidget(self.page_label)

        self.object_label = QLabel("Object: -")
        self.object_label.setStyleSheet("color: #64748b; font-size: 11px;")
        self.object_label.setWordWrap(True)
        summary_layout.addWidget(self.object_label)

        content_layout.addWidget(self.summary_box)

        # 2. Highlight on Page Button
        self.btn_highlight = QPushButton("🎯 Highlight on Page")
        self.btn_highlight.setObjectName("primaryBtn")
        self.btn_highlight.setEnabled(False)
        self.btn_highlight.clicked.connect(self._on_highlight_clicked)
        content_layout.addWidget(self.btn_highlight)

        # 3. Message / Explanation Box
        self.explanation_box = QGroupBox("Explanation")
        exp_layout = QVBoxLayout(self.explanation_box)
        self.txt_explanation = QTextBrowser()
        self.txt_explanation.setMaximumHeight(90)
        self.txt_explanation.setStyleSheet("background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 4px;")
        exp_layout.addWidget(self.txt_explanation)
        content_layout.addWidget(self.explanation_box)

        # 4. Evidence Box
        self.evidence_box = QGroupBox("Technical Evidence")
        ev_layout = QVBoxLayout(self.evidence_box)
        self.txt_evidence = QTextBrowser()
        self.txt_evidence.setMaximumHeight(85)
        self.txt_evidence.setStyleSheet("background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 4px; font-family: monospace; font-size: 11px;")
        ev_layout.addWidget(self.txt_evidence)
        content_layout.addWidget(self.evidence_box)

        # 5. Remediation Advice Box
        self.remediation_box = QGroupBox("Remediation Advice")
        rem_layout = QVBoxLayout(self.remediation_box)
        self.txt_remediation = QTextBrowser()
        self.txt_remediation.setMinimumHeight(110)
        self.txt_remediation.setStyleSheet("background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 4px; color: #166534;")
        rem_layout.addWidget(self.txt_remediation)
        content_layout.addWidget(self.remediation_box)

        content_layout.addStretch()
        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)

    def display_category_summary(self, standard: str, category: str, counts: Dict[str, int], findings: List[CheckResult]):
        """Displays category-level summary and highlights primary failure or warning if present."""
        p = counts.get("passed", 0)
        w = counts.get("warned", 0)
        f = counts.get("failed", 0)

        # If there are active findings (failures or warnings), display the most critical finding directly
        active_findings = [res for res in findings if res.status in (CheckStatus.FAIL, CheckStatus.ERROR, CheckStatus.WARNING)]
        if active_findings:
            # Sort with FAIL first, then WARNING
            active_findings.sort(key=lambda x: 0 if x.status in (CheckStatus.FAIL, CheckStatus.ERROR) else 1)
            primary = active_findings[0]
            self.display_finding(primary)
            self.title_label.setText(f"{category} ({len(active_findings)} issue{'s' if len(active_findings) > 1 else ''})")
            return

        # If fully passed or no failures
        self.current_finding = None
        self.title_label.setText(f"Checkpoint: {category}")
        self.name_label.setText(f"{category}")
        if f > 0:
            self.status_badge.setStatus(CheckStatus.FAIL)
            self.severity_badge.setSeverity(Severity.HIGH)
        elif w > 0:
            self.status_badge.setStatus(CheckStatus.WARNING)
            self.severity_badge.setSeverity(Severity.MEDIUM)
        else:
            self.status_badge.setStatus(CheckStatus.PASS)
            self.severity_badge.setSeverity(Severity.INFO)

        self.id_label.setText(f"Checkpoint: {category}")
        self.standard_label.setText(f"Standard: {standard}")
        self.page_label.setText(f"Passed: {p} | Warned: {w} | Failed: {f}")
        self.object_label.setText(f"Total Evaluated: {p + w + f}")

        if f == 0 and w == 0:
            self.txt_explanation.setPlainText(
                f"All checks for '{category}' passed successfully according to {standard} requirements."
            )
            self.txt_evidence.setPlainText(f"Compliance confirmed: {p} item(s) passed.")
            self.txt_remediation.setPlainText("No remediation necessary. This checkpoint conforms to accessibility requirements.")
        else:
            self.txt_explanation.setPlainText(
                f"Evaluation of '{category}' identified {f} failure(s) and {w} warning(s)."
            )
            self.txt_evidence.setPlainText(f"Passed: {p}, Warned: {w}, Failed: {f}")
            self.txt_remediation.setPlainText("Double-click this row or navigate to 'Detailed Results' to inspect individual findings and page highlights.")

        self.btn_highlight.setEnabled(False)

    def display_finding(self, finding: Optional[CheckResult]):
        """Populates panel with the selected finding's properties."""
        self.current_finding = finding
        if not finding:
            self.title_label.setText("Finding Details")
            self.name_label.setText("No finding selected")
            self.id_label.setText("Rule ID: -")
            self.standard_label.setText("Standard: -")
            self.page_label.setText("Page: -")
            self.object_label.setText("Object: -")
            self.txt_explanation.setPlainText("")
            self.txt_evidence.setPlainText("")
            self.txt_remediation.setPlainText("")
            self.btn_highlight.setEnabled(False)
            return

        self.title_label.setText("Finding Details")
        self.name_label.setText(f"{finding.name}")
        self.status_badge.setStatus(finding.status)
        self.severity_badge.setSeverity(finding.severity)

        self.id_label.setText(f"Rule ID: {finding.check_id}")
        self.standard_label.setText(f"Standard: {finding.standard} ({finding.category})")
        self.page_label.setText(f"Page: {finding.page if finding.page else 'Document-wide'}")
        self.object_label.setText(f"Target: {finding.object_reference or 'Document'}")

        self.txt_explanation.setPlainText(
            f"{finding.message}\n\n{finding.description}"
        )
        self.txt_evidence.setPlainText(finding.evidence or "No direct technical string evidence.")
        self.txt_remediation.setPlainText(finding.remediation or "Review standard accessibility guidelines.")

        can_highlight = finding.page is not None
        self.btn_highlight.setEnabled(can_highlight)

    def _on_highlight_clicked(self):
        if self.current_finding and self.current_finding.page:
            self.highlight_requested.emit(self.current_finding.page, self.current_finding.bounding_box)
