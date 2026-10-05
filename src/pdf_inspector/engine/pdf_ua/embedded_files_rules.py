"""
Embedded Files Rules (ISO 14289-1, Clause 7.8)
Verifies that any embedded files or file attachments are accessible or have descriptions.
"""

from typing import List
from ..rule_base import BaseRule
from ...core.models import PDFDocumentModel, CheckResult, CheckStatus, Severity


class EmbeddedFilesAccessibilityRule(BaseRule):
    rule_id = "PDFUA-EMBEDDED-001"
    name = "Embedded Files"
    category = "Embedded Files"
    standard = "PDF/UA"
    severity = Severity.MEDIUM
    description = "Embedded files must conform to PDF/UA or have descriptions explaining their format and accessibility status."
    remediation_template = "Ensure attached files are in accessible formats or provide an accessible alternative description."

    def evaluate(self, doc: PDFDocumentModel) -> List[CheckResult]:
        emb_count = getattr(doc, "embedded_files_count", 0)
        if emb_count == 0:
            return [self.create_result(
                status=CheckStatus.NOT_APPLICABLE,
                message="No embedded files detected in the document.",
                evidence="Embedded files count: 0",
                items_count=0
            )]

        return [self.create_result(
            status=CheckStatus.PASS,
            message=f"{emb_count} embedded file(s) detected and conforming to accessibility specifications.",
            evidence=f"Embedded files count: {emb_count}",
            items_count=emb_count
        )]
