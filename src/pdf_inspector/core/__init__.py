"""Core models and parsing engines for PDF Accessibility Inspector."""

from .models import (
    CheckStatus, Severity, CheckResult, StructureNode,
    FontModel, ImageModel, TableModel, ListModel, LinkModel, FormFieldModel,
    AnnotationModel, BookmarkModel, PageModel, PDFDocumentModel, AuditReport,
    ArtifactOccurrenceModel
)
from .document_parser import DocumentParser
from .structure_tree import StructureTreeParser, resolve_role, STANDARD_STRUCTURE_TYPES
from .visual_locator import VisualLocatorResolver

__all__ = [
    "CheckStatus",
    "Severity",
    "CheckResult",
    "StructureNode",
    "FontModel",
    "ImageModel",
    "TableModel",
    "LinkModel",
    "FormFieldModel",
    "BookmarkModel",
    "PageModel",
    "PDFDocumentModel",
    "AuditReport",
    "ArtifactOccurrenceModel",
    "DocumentParser",
    "StructureTreeParser",
    "VisualLocatorResolver",
    "resolve_role",
    "STANDARD_STRUCTURE_TYPES",
]

