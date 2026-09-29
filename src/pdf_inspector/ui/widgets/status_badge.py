"""
Status Badge Widget
Draws pill badges for CheckStatus (PASS, FAIL, WARN, MANUAL) and Severity levels.
"""

from PySide6.QtWidgets import QLabel
from PySide6.QtCore import Qt
from ...core.models import CheckStatus, Severity


class StatusBadge(QLabel):
    """Pill badge showing colored status."""

    def __init__(self, status: CheckStatus, parent=None):
        super().__init__(parent)
        self.setStatus(status)

    def setStatus(self, status: CheckStatus):
        self.setText(f" {status.value} ")
        self.setAlignment(Qt.AlignCenter)

        style_map = {
            CheckStatus.PASS: "background-color: #dcfce7; color: #166534; border: 1px solid #86efac;",
            CheckStatus.FAIL: "background-color: #fee2e2; color: #991b1b; border: 1px solid #fca5a5;",
            CheckStatus.WARNING: "background-color: #fef3c7; color: #92400e; border: 1px solid #fcd34d;",
            CheckStatus.MANUAL_REVIEW: "background-color: #e0f2fe; color: #075985; border: 1px solid #7dd3fc;",
            CheckStatus.ERROR: "background-color: #f3e8ff; color: #6b21a8; border: 1px solid #d8b4fe;",
            CheckStatus.NOT_APPLICABLE: "background-color: #f1f5f9; color: #64748b; border: 1px solid #cbd5e1;",
        }

        css = style_map.get(status, "background-color: #f1f5f9; color: #64748b;")
        self.setStyleSheet(f"""
            QLabel {{
                {css}
                border-radius: 4px;
                padding: 2px 6px;
                font-weight: 700;
                font-size: 11px;
            }}
        """)


class SeverityBadge(QLabel):
    """Pill badge showing severity level."""

    def __init__(self, severity: Severity, parent=None):
        super().__init__(parent)
        self.setSeverity(severity)

    def setSeverity(self, severity: Severity):
        self.setText(f" {severity.value} ")
        self.setAlignment(Qt.AlignCenter)

        style_map = {
            Severity.CRITICAL: "background-color: #ffe4e6; color: #9f1239; border: 1px solid #fda4af;",
            Severity.HIGH: "background-color: #fee2e2; color: #991b1b; border: 1px solid #fca5a5;",
            Severity.MEDIUM: "background-color: #ffedd5; color: #9a3412; border: 1px solid #fdba74;",
            Severity.LOW: "background-color: #fef9c3; color: #854d0e; border: 1px solid #fde047;",
            Severity.INFO: "background-color: #f0fdf4; color: #166534; border: 1px solid #bbf7d0;",
        }

        css = style_map.get(severity, "background-color: #f1f5f9; color: #64748b;")
        self.setStyleSheet(f"""
            QLabel {{
                {css}
                border-radius: 4px;
                padding: 2px 6px;
                font-weight: 600;
                font-size: 10px;
            }}
        """)
