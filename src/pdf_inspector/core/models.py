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


def validate_bbox_coordinates(val: Any) -> Tuple[bool, Optional[Tuple[float, float, float, float]]]:
    """
    Validates and converts a bounding box attribute.
    Returns (is_valid, parsed_bbox_tuple).
    - Accepts integers, floats, decimal.Decimal, and pikepdf numeric types.
    - Requires exactly four numeric coordinates.
    - Rejects non-numeric strings/objects, NaN, and positive/negative infinity.
    - Preserves legitimate zero and negative coordinates.
    - Returns (False, None) for malformed, non-4-length, non-numeric, or non-finite coordinates.
    """
    if val is None or isinstance(val, (str, bytes, dict)):
        return False, None
    if not isinstance(val, (list, tuple)) and not hasattr(val, "__iter__"):
        return False, None
    try:
        if len(val) != 4:
            return False, None
        import math
        coords = []
        for x in val:
            if isinstance(x, (bool, bytes, str, dict, list)):
                return False, None
            f_val = float(x)
            if not math.isfinite(f_val):
                return False, None
            coords.append(f_val)
        return True, (coords[0], coords[1], coords[2], coords[3])
    except Exception:
        return False, None



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
    items_count: int = 1

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
            "items_count": self.items_count,
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
    mcid_entries: List[Tuple[int, Optional[int]]] = field(default_factory=list)
    attributes: Dict[str, Any] = field(default_factory=dict)
    children: List['StructureNode'] = field(default_factory=list)
    text_content: str = ""
    bbox: Optional[Tuple[float, float, float, float]] = None
    struct_bbox: Optional[Tuple[float, float, float, float]] = None
    has_explicit_bbox: bool = False
    placement: Optional[str] = None
    obj_num: Optional[int] = None
    has_pg_attr: bool = False
    pg_attr_val: Optional[int] = None
    pages_spanned: List[int] = field(default_factory=list)
    is_artifact: bool = False
    extracted_graphic_text: Optional[str] = None
    ai_description: Optional[str] = None
    expanded_text: Optional[str] = None
    has_decoding_error: bool = False
    decoding_error_msg: str = ""

    def get_readable_text(self, recursive: bool = True) -> str:
        """
        Returns human-readable text for this node.
        Prefers author-specified /ActualText, then direct text_content,
        then recursively aggregates text from child elements while preserving
        meaningful Unicode characters.
        """
        if self.actual_text and self.actual_text.strip().replace("\x00", ""):
            return self.actual_text.strip().replace("\x00", "")

        parts: List[str] = []
        if self.text_content and self.text_content.strip().replace("\x00", ""):
            parts.append(self.text_content.strip().replace("\x00", ""))

        if recursive and self.children:
            for child in self.children:
                # Do not aggregate text from independent major structures into a parent block
                if child.standard_tag.upper() not in ("FIGURE", "FORMULA", "TABLE", "NOTE"):
                    c_txt = child.get_readable_text(recursive=True)
                    if c_txt and c_txt not in parts:
                        parts.append(c_txt)

        return " ".join(parts).strip()

    def is_decorative(self) -> bool:
        """Returns True if this node represents a decorative/artifact element."""
        return (
            self.is_artifact
            or self.standard_tag.upper() == "ARTIFACT"
            or self.tag.lower() == "artifact"
            or self.attributes.get("O") == "/Artifact"
            or self.attributes.get("Type") == "/Pagination"
            or self.attributes.get("Placement") == "/Background"
        )

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
    xref: int = 0
    has_standard_encoding: bool = False


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
class AnnotationModel:
    """Represents a PDF page annotation and its association to the logical structure tree."""
    id: str
    page: int
    subtype: str
    rect: Tuple[float, float, float, float]
    struct_parent: Optional[int] = None
    is_tagged: bool = False
    contents: Optional[str] = None


@dataclass
class ListModel:
    """Represents an ordered or unordered structural list element (<L>)."""
    id: str
    page: int
    items_count: int
    is_valid_structure: bool  # L -> LI -> (Lbl, LBody)
    has_labels: bool
    bbox: Optional[Tuple[float, float, float, float]] = None


@dataclass
class ContentOccurrenceModel:
    """Represents a content or artifact sequence encountered in a page or XObject content stream."""
    page_number: int
    operator_type: str  # "text", "path", "xobject", "marked_content"
    operator_name: str  # "Tj", "TJ", "re", "Do", "BDC", "BMC", etc.
    mcid: Optional[int] = None
    tag: Optional[str] = None
    is_artifact: bool = False
    is_inside_tagged: bool = False
    is_inside_artifact: bool = False
    is_unmarked_real_content: bool = False
    xobject_name: Optional[str] = None
    bbox: Optional[Tuple[float, float, float, float]] = None
    snippet: str = ""


@dataclass
class ArtifactOccurrenceModel:
    """Represents a marked-content /Artifact sequence found in page streams or XObjects."""
    page_number: int
    is_inside_tagged: bool
    parent_tag: Optional[str] = None
    parent_mcid: Optional[int] = None
    xobject_name: Optional[str] = None
    xobject_xref: Optional[int] = None
    bbox: Optional[Tuple[float, float, float, float]] = None
    text_snippet: str = ""


@dataclass
class PageModel:
    """Represents metadata and geometry for a single PDF page."""
    page_number: int  # 1-indexed
    width: float
    height: float
    rotation: int = 0
    text: str = ""
    images_count: int = 0
    links_count: int = 0
    has_structure: bool = False
    has_tab_order: bool = False
    tab_order_mode: str = "Unspecified"
    struct_parents_id: Optional[int] = None
    mcids: List[int] = field(default_factory=list)
    mcid_bboxes: Dict[int, Tuple[float, float, float, float]] = field(default_factory=dict)
    mcid_texts: Dict[int, str] = field(default_factory=dict)
    artifacts: List[ArtifactOccurrenceModel] = field(default_factory=list)
    content_occurrences: List[ContentOccurrenceModel] = field(default_factory=list)
    unmarked_real_content_count: int = 0
    tagged_in_artifact_count: int = 0
    artifact_in_tagged_count: int = 0
    annotations_count: int = 0


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
    has_suspects: bool = False
    doc_info_title: Optional[str] = None
    doc_info_author: Optional[str] = None
    doc_info_subject: Optional[str] = None
    doc_info_keywords: Optional[str] = None
    xmp_metadata_present: bool = False
    xmp_dc_title: Optional[str] = None
    xmp_dc_creator: Optional[str] = None
    xmp_dc_description: Optional[str] = None
    pdfua_identifier_present: bool = False
    pdfua_part: Optional[int] = None
    has_parent_tree: bool = False
    parent_tree_valid: bool = False
    parent_tree_entries_count: int = 0
    role_map: Dict[str, str] = field(default_factory=dict)
    pages: List[PageModel] = field(default_factory=list)
    structure_tree: Optional[StructureNode] = None
    fonts: List[FontModel] = field(default_factory=list)
    images: List[ImageModel] = field(default_factory=list)
    tables: List[TableModel] = field(default_factory=list)
    lists: List[ListModel] = field(default_factory=list)
    links: List[LinkModel] = field(default_factory=list)
    form_fields: List[FormFieldModel] = field(default_factory=list)
    annotations: List[AnnotationModel] = field(default_factory=list)
    bookmarks: List[BookmarkModel] = field(default_factory=list)
    raw_metadata: Dict[str, Any] = field(default_factory=dict)
    embedded_files_count: int = 0

    @property
    def all_artifacts(self) -> List[ArtifactOccurrenceModel]:
        """Returns all artifact occurrences across all pages."""
        arts: List[ArtifactOccurrenceModel] = []
        for p in self.pages:
            arts.extend(p.artifacts)
        return arts

    @property
    def all_content_occurrences(self) -> List[ContentOccurrenceModel]:
        """Returns all content occurrences across all pages."""
        occs: List[ContentOccurrenceModel] = []
        for p in self.pages:
            occs.extend(p.content_occurrences)
        return occs


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
            cnt = r.items_count if (hasattr(r, "items_count") and r.items_count is not None) else 1
            if r.status == CheckStatus.PASS:
                counts[r.category]["passed"] += cnt
            elif r.status == CheckStatus.WARNING:
                counts[r.category]["warned"] += cnt
            elif r.status in (CheckStatus.FAIL, CheckStatus.ERROR):
                counts[r.category]["failed"] += cnt
            elif r.status == CheckStatus.MANUAL_REVIEW:
                counts[r.category]["manual"] += cnt
        return counts

    @property
    def total_passed(self) -> int:
        return sum(r.items_count for r in self.results if r.status == CheckStatus.PASS)

    @property
    def total_warned(self) -> int:
        return sum(r.items_count for r in self.results if r.status == CheckStatus.WARNING)

    @property
    def total_failed(self) -> int:
        return sum(r.items_count for r in self.results if r.status in (CheckStatus.FAIL, CheckStatus.ERROR))

    @property
    def total_manual(self) -> int:
        return sum(r.items_count for r in self.results if r.status == CheckStatus.MANUAL_REVIEW)

    @property
    def total_checks(self) -> int:
        """Total number of individual item-level checks evaluated across all rules."""
        return self.total_passed + self.total_warned + self.total_failed + self.total_manual

    @property
    def total_findings_count(self) -> int:
        """Total count of individual CheckResult finding objects."""
        return len(self.results)

    @property
    def compliance_score(self) -> float:
        total = self.total_passed + self.total_warned + self.total_failed
        if total == 0:
            return 100.0
        return round((self.total_passed / total) * 100.0, 1)

    @property
    def summary(self) -> Dict[str, Any]:
        """Consolidated, mathematically consistent summary dictionary."""
        return {
            "total_checks": self.total_checks,
            "passed": self.total_passed,
            "warned": self.total_warned,
            "failed": self.total_failed,
            "manual": self.total_manual,
            "compliance_score": self.compliance_score,
            "findings_count": self.total_findings_count
        }
