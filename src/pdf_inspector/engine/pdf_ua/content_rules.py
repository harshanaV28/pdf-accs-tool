"""
Content Rules (ISO 14289-1, Clause 7.1)
Verifies that all meaningful document content is tagged within the logical structure tree.
"""

from typing import List
from ..rule_base import BaseRule
from ...core.models import PDFDocumentModel, CheckResult, CheckStatus, Severity


class TaggedPDFRule(BaseRule):
    rule_id = "PDFUA-CONTENT-001"
    name = "Tagged PDF"
    category = "Content"
    standard = "PDF/UA"
    severity = Severity.CRITICAL
    description = "The document must be marked as a Tagged PDF in the document Catalog dictionary (ISO 14289-1, Clause 7.1)."
    remediation_template = "In Acrobat Pro, open Accessibility tool and select 'Add Tags to Document', or check 'Document is tagged PDF' in Word/InDesign export settings."

    def evaluate(self, doc: PDFDocumentModel) -> List[CheckResult]:
        results = []
        if doc.is_tagged and doc.structure_tree is not None:
            results.append(self.create_result(
                status=CheckStatus.PASS,
                message="Document is explicitly marked as a Tagged PDF with a structure tree.",
                evidence="Catalog/MarkInfo/Marked is true and StructTreeRoot exists."
            ))
        else:
            results.append(self.create_result(
                status=CheckStatus.FAIL,
                message="Document is NOT a Tagged PDF. Assistive technologies cannot determine reading order or semantics.",
                evidence=f"is_tagged: {doc.is_tagged}, StructTreeRoot present: {doc.structure_tree is not None}",
                custom_severity=Severity.CRITICAL,
                custom_remediation="Tag the document using an accessible PDF authoring tool or Adobe Acrobat Pro's 'Autotag Document' feature."
            ))

        return results


class ContentTaggedRule(BaseRule):
    rule_id = "PDFUA-CONTENT-002"
    name = "Real Content Tagged"
    category = "Content"
    standard = "PDF/UA"
    severity = Severity.HIGH
    description = "All real content on each page must be tagged or marked as an Artifact."
    remediation_template = "Inspect untagged elements in the PDF structure pane and tag them or mark them as background artifacts."

    def evaluate(self, doc: PDFDocumentModel) -> List[CheckResult]:
        results = []
        if not doc.is_tagged:
            return results

        # Check pages that have text but no structure tags associated
        pages_without_tags = []
        for p in doc.pages:
            if p.text.strip() and not p.has_structure:
                pages_without_tags.append(p.page_number)

        if pages_without_tags:
            results.append(self.create_result(
                status=CheckStatus.FAIL,
                message=f"Pages {pages_without_tags} contain text but have no associated structure tags.",
                evidence=f"Untagged page numbers: {pages_without_tags}",
                page=pages_without_tags[0],
                custom_remediation="Tag the missing content on these pages."
            ))
        else:
            results.append(self.create_result(
                status=CheckStatus.PASS,
                message="All pages with text content are associated with the structure tree.",
                evidence=f"Total pages checked: {doc.page_count}"
            ))

        return results
