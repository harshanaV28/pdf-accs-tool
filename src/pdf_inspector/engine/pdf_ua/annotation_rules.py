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
        if not doc.annotations:
            return [self.create_result(
                status=CheckStatus.PASS,
                message="No interactive annotations found in document.",
                evidence="Annotation count: 0"
            )]

        untagged_annots = [a for a in doc.annotations if not a.is_tagged and a.subtype in ("Link", "Widget", "Text")]
        if untagged_annots and doc.is_tagged:
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
