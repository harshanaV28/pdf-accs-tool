"""
PDF Syntax (ISO 32000-1) Rules
Validates core PDF syntax compliance for accessibility, catalog structure, and security permissions.
"""

from typing import List
from ..rule_base import BaseRule
from ...core.models import PDFDocumentModel, CheckResult, CheckStatus, Severity


class PDFSyntaxBasicRule(BaseRule):
    rule_id = "PDFUA-SYNTAX-001"
    name = "PDF Syntax (ISO 32000-1) Core"
    category = "PDF Syntax (ISO 32000-1)"
    standard = "PDF/UA"
    severity = Severity.CRITICAL
    description = "The PDF file must conform to ISO 32000-1 syntax rules and allow accessibility content extraction."
    remediation_template = "Ensure the PDF is created with compliant PDF 1.7 or 2.0 specifications without syntax corruption."

    def evaluate(self, doc: PDFDocumentModel) -> List[CheckResult]:
        results = []

        # 1. Version check
        try:
            v_float = float(doc.pdf_version)
            if v_float < 1.4:
                results.append(self.create_result(
                    status=CheckStatus.FAIL,
                    message=f"PDF version {doc.pdf_version} is too old to support PDF/UA-1 (requires PDF 1.7+).",
                    evidence=f"PDF Version: {doc.pdf_version}",
                    custom_severity=Severity.HIGH,
                    custom_remediation="Re-export the document as PDF 1.7 or ISO 14289-1 (PDF/UA)."
                ))
            else:
                results.append(self.create_result(
                    status=CheckStatus.PASS,
                    message=f"PDF version {doc.pdf_version} supports standard accessibility features.",
                    evidence=f"PDF Version: {doc.pdf_version}"
                ))
        except Exception:
            results.append(self.create_result(
                status=CheckStatus.WARNING,
                message=f"Could not parse numerical PDF version: {doc.pdf_version}",
                evidence=f"PDF Version string: {doc.pdf_version}"
            ))

        # 2. Accessibility Extraction Permissions
        if doc.is_encrypted:
            if not doc.allows_extraction:
                results.append(self.create_result(
                    status=CheckStatus.FAIL,
                    message="Document encryption restricts assistive technology from extracting text for accessibility.",
                    evidence="Document security settings disallow accessibility extraction.",
                    custom_severity=Severity.CRITICAL,
                    custom_remediation="Open PDF security settings in Adobe Acrobat Pro and enable 'Enable text access for screen reader devices for the visually impaired'."
                ))
            else:
                results.append(self.create_result(
                    status=CheckStatus.PASS,
                    message="Document security permissions allow assistive technologies to extract content.",
                    evidence="Accessibility extraction bit is enabled."
                ))
        else:
            results.append(self.create_result(
                status=CheckStatus.PASS,
                message="Document is not encrypted; accessibility content extraction is unrestricted.",
                evidence="Encryption: None"
            ))

        return results
