"""Custom UI widgets for PDF Accessibility Inspector."""

from .status_badge import StatusBadge, SeverityBadge
from .finding_details_panel import FindingDetailsPanel
from .pdf_canvas import PDFCanvas

__all__ = [
    "StatusBadge",
    "SeverityBadge",
    "FindingDetailsPanel",
    "PDFCanvas",
]
