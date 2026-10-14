"""
Annotation Rules (ISO 14289-1, Clause 7.18 & Matterhorn Protocol Checkpoint 19-001)
Verifies that all interactive annotations on pages are properly tagged in the structure tree.
"""

from typing import List
from ..rule_base import BaseRule
from ...core.models import PDFDocumentModel, CheckResult, CheckStatus, Severity


class AnnotationTaggedRule(BaseRule):
    rule_id = "PDFUA-ANNOT-001"
    name = "Annotations Tagged"
    category = "Content"
    standard = "PDF/UA"
    severity = Severity.HIGH
    description = "All interactive annotations (links, form fields, notes) must be associated with a structure element in the logical structure tree (ISO 14289-1, Clause 7.18)."
    remediation_template = "Tag untagged annotations or link them using an OBJR (Object Reference) in Acrobat Pro."

    def evaluate(self, doc: PDFDocumentModel) -> List[CheckResult]:
        results = []
        if not doc.is_tagged or not doc.annotations:
            return results

        untagged_annots = [a for a in doc.annotations if not a.is_tagged and a.subtype in ("Link", "Widget", "Text")]
        if untagged_annots:
            for a in untagged_annots[:5]:
                results.append(self.create_result(
                    status=CheckStatus.FAIL,
                    message=f"Annotation of type '{a.subtype}' on page {a.page} is not associated with any structure element.",
                    evidence=f"Annotation {a.id} at {a.rect}",
                    page=a.page,
                    bounding_box=a.rect,
                    object_reference=f"Annotation {a.id}",
                    custom_severity=Severity.HIGH,
                    custom_remediation=f"Wrap the {a.subtype} annotation in a matching structure tag (<Link> or <Form>)."
                ))
        else:
            results.append(self.create_result(
                status=CheckStatus.PASS,
                message=f"All {len(doc.annotations)} annotation(s) are associated with the logical structure tree.",
                evidence="Annotation tagging verified."
            ))

        return results


class PageTabOrderRule(BaseRule):
    rule_id = "PDFUA-ANNOT-002"
    name = "Page Tab Order"
    category = "Annotations"
    standard = "PDF/UA"
    severity = Severity.HIGH
    description = "In a tagged document, each page containing interactive annotations must specify /Tabs /S to ensure navigation order conforms to document structure order (ISO 14289-1:2014, Clause 7.18.1 / Matterhorn Checkpoint 17-001)."
    remediation_template = "In Acrobat Pro Page Thumbnails panel, select page properties and set Tab Order to 'Use Document Structure'."

    def evaluate(self, doc: PDFDocumentModel) -> List[CheckResult]:
        results = []
        if not doc.pages:
            return results

        violating_pages = [p.page_number for p in doc.pages if p.tab_order_mode != "S"]
        has_annots = any(
            getattr(p, "annotations_count", 0) > 0
            or p.links_count > 0
            or any(a.page == p.page_number for a in doc.annotations)
            for p in doc.pages
        )

        if violating_pages and (not doc.is_tagged or has_annots):
            results.append(self.create_result(
                status=CheckStatus.FAIL,
                message=f"{len(violating_pages)} page(s) do not specify Structure tab order (/Tabs /S).",
                evidence=f"Pages lacking /Tabs /S: {violating_pages[:5]}",
                page=violating_pages[0],
                custom_severity=Severity.HIGH,
                custom_remediation="In Acrobat Pro Page Thumbnails, set Page Properties > Tab Order to 'Use Document Structure' (/Tabs /S).",
                items_count=1
            ))
        else:
            applicable_pages = sum(
                1 for p in doc.pages
                if getattr(p, "has_tab_order", False)
                or p.tab_order_mode == "S"
                or p.links_count > 0
                or getattr(p, "annotations_count", 0) > 0
            )
            items_cnt = max(1, applicable_pages)
            results.append(self.create_result(
                status=CheckStatus.PASS,
                message="All pages specify Structure tab order (/Tabs /S) or contain no interactive annotations.",
                evidence=f"Page tab navigation conforms to document structure order (/Tabs /S) across {items_cnt} page(s).",
                items_count=items_cnt
            ))

        return results
