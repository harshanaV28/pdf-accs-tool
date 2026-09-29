"""
Metadata Rules (ISO 14289-1, Clause 7.9)
Verifies presence of XMP metadata, Dublin Core title (dc:title), and PDF/UA identification.
"""

from typing import List
from ..rule_base import BaseRule
from ...core.models import PDFDocumentModel, CheckResult, CheckStatus, Severity


class MetadataCompletenessRule(BaseRule):
    rule_id = "PDFUA-META-001"
    name = "Metadata"
    category = "Metadata"
    standard = "PDF/UA"
    severity = Severity.HIGH
    description = "The PDF must contain an XMP metadata stream containing a document title (dc:title) and a PDF/UA identifier."
    remediation_template = "In Adobe Acrobat Pro, open File > Properties > Description, enter a Title, and in Preflight run 'Fix PDF/UA identifier'."

    def evaluate(self, doc: PDFDocumentModel) -> List[CheckResult]:
        results = []

        # 1. XMP Stream presence
        if not doc.xmp_metadata_present:
            results.append(self.create_result(
                status=CheckStatus.FAIL,
                message="No XMP metadata stream found in the PDF catalog dictionary.",
                evidence="Catalog dictionary lacks /Metadata entry.",
                custom_severity=Severity.HIGH,
                custom_remediation="Add standard XMP metadata to the document."
            ))
        else:
            results.append(self.create_result(
                status=CheckStatus.PASS,
                message="XMP metadata stream is present.",
                evidence="Catalog/Metadata exists."
            ))

        # 2. Document Title
        if not doc.title or not doc.title.strip():
            results.append(self.create_result(
                status=CheckStatus.FAIL,
                message="Document Title is missing from metadata.",
                evidence="dc:title is empty or missing.",
                custom_severity=Severity.HIGH,
                custom_remediation="Provide a concise, descriptive document Title in File > Properties > Title."
            ))
        else:
            results.append(self.create_result(
                status=CheckStatus.PASS,
                message=f"Document Title is defined: '{doc.title}'.",
                evidence=f"Title: '{doc.title}'"
            ))

        # 3. PDF/UA Identifier
        if not doc.pdfua_identifier_present:
            results.append(self.create_result(
                status=CheckStatus.WARNING,
                message="PDF/UA identification flag (pdfuaid:part=1) is missing from XMP metadata.",
                evidence="XMP lacks <pdfuaid:part>1</pdfuaid:part> namespace declaration.",
                custom_severity=Severity.MEDIUM,
                custom_remediation="Add PDF/UA identifier using Acrobat Preflight or your PDF/UA export setting."
            ))
        else:
            results.append(self.create_result(
                status=CheckStatus.PASS,
                message=f"Document declares PDF/UA compliance (Part {doc.pdfua_part or 1}).",
                evidence="pdfuaid:part found in XMP metadata."
            ))

        return results
