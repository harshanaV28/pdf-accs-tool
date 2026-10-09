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

        # 1. Header & Version Syntax Validation (ISO 32000-1 Clause 7.5.2)
        # Validates that the document defines a recognized, well-formed PDF version identifier (e.g. 1.0 - 2.0).
        # Under ISO 32000-1 and PDF/UA-1, valid standard specification version headers (including PDF 1.3 - 2.0)
        # conform to PDF file syntax requirements.
        try:
            v_str = (doc.pdf_version or "").strip()
            v_float = float(v_str) if v_str else None
            if v_float is not None and (1.0 <= v_float <= 2.5):
                results.append(self.create_result(
                    status=CheckStatus.PASS,
                    message=f"PDF header specifies valid specification version {doc.pdf_version} (ISO 32000-1).",
                    evidence=f"PDF Version: {doc.pdf_version}"
                ))
            else:
                results.append(self.create_result(
                    status=CheckStatus.FAIL,
                    message=f"PDF file header contains an invalid or unrecognized version identifier: '{doc.pdf_version}' (ISO 32000-1, Clause 7.5.2).",
                    evidence=f"Invalid PDF Version: {doc.pdf_version}",
                    custom_severity=Severity.HIGH,
                    custom_remediation="Re-save or rebuild the PDF with a standard, valid PDF specification header (%PDF-1.0 to %PDF-2.0)."
                ))
        except Exception:
            results.append(self.create_result(
                status=CheckStatus.FAIL,
                message=f"PDF file header contains a malformed, unparseable version string: '{doc.pdf_version}' (ISO 32000-1, Clause 7.5.2).",
                evidence=f"Malformed PDF Version string: {doc.pdf_version}",
                custom_severity=Severity.HIGH,
                custom_remediation="Ensure the file begins with a valid header (e.g. %PDF-1.7)."
            ))

        # 2. Accessibility Extraction Permissions (ISO 32000-1 Clause 7.6 / ISO 14289-1 Clause 7.1)
        if doc.is_encrypted:
            if not doc.allows_extraction:
                results.append(self.create_result(
                    status=CheckStatus.FAIL,
                    message="Document encryption restricts assistive technology from extracting text for accessibility (ISO 14289-1, Clause 7.1).",
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
