"""
PDF Accessibility Inspector - Core Data Models
Provides immutable and structured definitions for document analysis, structural tags,
check results, and accessibility audit reports.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Tuple, Any
import datetime


class CheckStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    WARNING = "WARNING"
    MANUAL_REVIEW = "MANUAL REVIEW"
    NOT_APPLICABLE = "NOT APPLICABLE"
    ERROR = "ERROR"

    @property
    def is_problem(self) -> bool:
        return self in (CheckStatus.FAIL, CheckStatus.WARNING, CheckStatus.ERROR)


class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


@dataclass
class CheckResult:
    """Standardized finding result for any automated or manual rule."""
    check_id: str
    name: str
    category: str
    standard: str  # "PDF/UA", "WCAG", "Quality", "AI"
    status: CheckStatus
    severity: Severity
    message: str
    description: str = ""
    evidence: str = ""
    page: Optional[int] = None
    bounding_box: Optional[Tuple[float, float, float, float]] = None  # (x0, y0, x1, y1)
    object_reference: str = ""
    remediation: str = ""
    confidence: float = 1.0
    machine_testable: bool = True
    manual_review_required: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "check_id": self.check_id,
            "name": self.name,
            "category": self.category,
            "standard": self.standard,
            "status": self.status.value,
            "severity": self.severity.value,
            "message": self.message,
            "description": self.description,
            "evidence": self.evidence,
            "page": self.page,
            "bounding_box": list(self.bounding_box) if self.bounding_box else None,
            "object_reference": self.object_reference,
            "remediation": self.remediation,
            "confidence": self.confidence,
            "machine_testable": self.machine_testable,
            "manual_review_required": self.manual_review_required,
        }


@dataclass
class StructureNode:
    """Represents a structural element within the PDF Logical Structure Tree."""
    id: str
    tag: str
    standard_tag: str
    title: Optional[str] = None
    alt_text: Optional[str] = None
    actual_text: Optional[str] = None
    lang: Optional[str] = None
    page: Optional[int] = None
    mcids: List[int] = field(default_factory=list)
    attributes: Dict[str, Any] = field(default_factory=dict)
    children: List['StructureNode'] = field(default_factory=list)
    text_content: str = ""
    bbox: Optional[Tuple[float, float, float, float]] = None
    obj_num: Optional[int] = None

    def find_all_by_standard_tag(self, target_tag: str) -> List['StructureNode']:
        results = []
        if self.standard_tag.upper() == target_tag.upper():
            results.append(self)
        for child in self.children:
            results.extend(child.find_all_by_standard_tag(target_tag))
        return results

    def find_all_nodes(self) -> List['StructureNode']:
        all_nodes = [self]
        for child in self.children:
            all_nodes.extend(child.find_all_nodes())
        return all_nodes


@dataclass
class FontModel:
    """Represents a font dictionary in the PDF document."""
    name: str
    subtype: str
    is_embedded: bool
    is_subset: bool
    has_tounicode: bool
    encoding: str
    pages: List[int] = field(default_factory=list)
    is_used: bool = True


@dataclass
class ImageModel:
    """Represents an image or figure on a specific PDF page."""
    id: str
    page: int
    bbox: Tuple[float, float, float, float]
    width: int
    height: int
    colorspace: str
    has_alt: bool
    alt_text: str = ""
    is_artifact: bool = False
    structure_element_id: Optional[str] = None


@dataclass
class TableModel:
    """Represents a data or layout table extracted from the structure tree."""
    id: str
    page: int
    rows_count: int
    cols_count: int
    has_headers: bool
    header_cells_count: int
    data_cells_count: int
    summary: Optional[str] = None
    is_regular: bool = True
    bbox: Optional[Tuple[float, float, float, float]] = None


@dataclass
class LinkModel:
    """Represents a hyperlink annotation and its structure association."""
    id: str
    page: int
    text: str
    uri: str
    is_internal: bool = False
    destination_page: Optional[int] = None
    alt_text: Optional[str] = None
    has_structure_link: bool = False
    bbox: Optional[Tuple[float, float, float, float]] = None


@dataclass
class FormFieldModel:
    """Represents an interactive AcroForm form field."""
    name: str
    field_type: str
    tooltip: Optional[str] = None
    label: Optional[str] = None
    page: int = 1
    is_required: bool = False
    tab_order: Optional[str] = None
    bbox: Optional[Tuple[float, float, float, float]] = None


@dataclass
class BookmarkModel:
    """Represents a document outline (bookmark) item."""
    title: str
    level: int
    page: int
    children: List['BookmarkModel'] = field(default_factory=list)


@dataclass
class PageModel:
    """Represents metadata and geometry for a single PDF page."""
    page_number: int  # 1-indexed
    width: float
    height: float
    rotation: int
    text: str
    images_count: int = 0
    links_count: int = 0
    has_structure: bool = False
    has_tab_order: bool = False
    tab_order_mode: str = "Unspecified"


@dataclass
class PDFDocumentModel:
    """Unified in-memory model of the parsed PDF document."""
    filepath: str
    filename: str
    filesize: int
    pdf_version: str
    page_count: int
    title: Optional[str] = None
    author: Optional[str] = None
    subject: Optional[str] = None
    keywords: Optional[str] = None
    creator: Optional[str] = None
    producer: Optional[str] = None
    creation_date: Optional[str] = None
    modification_date: Optional[str] = None
    language: Optional[str] = None
    is_tagged: bool = False
    is_encrypted: bool = False
    allows_extraction: bool = True
    display_doc_title: bool = False
    xmp_metadata_present: bool = False
    pdfua_identifier_present: bool = False
    pdfua_part: Optional[int] = None
    role_map: Dict[str, str] = field(default_factory=dict)
    pages: List[PageModel] = field(default_factory=list)
    structure_tree: Optional[StructureNode] = None
    fonts: List[FontModel] = field(default_factory=list)
    images: List[ImageModel] = field(default_factory=list)
    tables: List[TableModel] = field(default_factory=list)
    links: List[LinkModel] = field(default_factory=list)
    form_fields: List[FormFieldModel] = field(default_factory=list)
    bookmarks: List[BookmarkModel] = field(default_factory=list)
    raw_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AuditReport:
    """Complete summary and detailed collection of audit results."""
    document_info: Dict[str, Any]
    results: List[CheckResult]
    timestamp: str = field(default_factory=lambda: datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    def get_results_by_standard(self, standard: str) -> List[CheckResult]:
        return [r for r in self.results if r.standard.upper() == standard.upper()]

    def get_category_counts(self, standard: str) -> Dict[str, Dict[str, int]]:
        """Returns {category_name: {'passed': X, 'warned': Y, 'failed': Z, 'manual': W}}"""
        counts: Dict[str, Dict[str, int]] = {}
        for r in self.get_results_by_standard(standard):
            if r.category not in counts:
                counts[r.category] = {"passed": 0, "warned": 0, "failed": 0, "manual": 0}
            if r.status == CheckStatus.PASS:
                counts[r.category]["passed"] += 1
            elif r.status == CheckStatus.WARNING:
                counts[r.category]["warned"] += 1
            elif r.status in (CheckStatus.FAIL, CheckStatus.ERROR):
                counts[r.category]["failed"] += 1
            elif r.status == CheckStatus.MANUAL_REVIEW:
                counts[r.category]["manual"] += 1
        return counts

    @property
    def total_passed(self) -> int:
        return sum(1 for r in self.results if r.status == CheckStatus.PASS)

    @property
    def total_warned(self) -> int:
        return sum(1 for r in self.results if r.status == CheckStatus.WARNING)

    @property
    def total_failed(self) -> int:
        return sum(1 for r in self.results if r.status in (CheckStatus.FAIL, CheckStatus.ERROR))

    @property
    def total_manual(self) -> int:
        return sum(1 for r in self.results if r.status == CheckStatus.MANUAL_REVIEW)

    @property
    def compliance_score(self) -> float:
        total = self.total_passed + self.total_warned + self.total_failed
        if total == 0:
            return 100.0
        return round((self.total_passed / total) * 100.0, 1)
