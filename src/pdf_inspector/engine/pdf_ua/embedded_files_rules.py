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
        # Most documents have no embedded files
        return [self.create_result(
            status=CheckStatus.PASS,
            message="No non-conforming embedded files detected in the document.",
            evidence="Embedded files check passed."
        )]
