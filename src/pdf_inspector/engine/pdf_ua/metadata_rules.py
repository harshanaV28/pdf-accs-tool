"""
Metadata Rules (ISO 14289-1:2014, Clause 7.9 & Matterhorn Protocol Checkpoint 06)
Verifies presence of XMP metadata stream, Dublin Core title (dc:title), and PDF/UA identification.
"""

from typing import List
from ..rule_base import BaseRule
from ...core.models import PDFDocumentModel, CheckResult, CheckStatus, Severity


class XMPMetadataStreamRule(BaseRule):
    rule_id = "PDFUA-META-001"
    name = "XMP Metadata Stream"
    category = "Metadata"
    standard = "PDF/UA"
    severity = Severity.HIGH
    description = "The document Catalog dictionary must contain a standard XMP metadata stream (ISO 14289-1, Clause 7.9 / Matterhorn 06-001)."
    remediation_template = "Add standard XMP metadata to the document using an accessible PDF creator or Adobe Acrobat Pro Preflight."

    def evaluate(self, doc: PDFDocumentModel) -> List[CheckResult]:
        if not doc.xmp_metadata_present:
            return [self.create_result(
                status=CheckStatus.FAIL,
                message="No XMP metadata stream found in the PDF catalog dictionary.",
                evidence="Catalog dictionary lacks /Metadata stream entry.",
                custom_severity=Severity.HIGH,
                custom_remediation="Add standard XMP metadata stream in Catalog."
            )]
        return [self.create_result(
            status=CheckStatus.PASS,
            message="XMP metadata stream is present in the document Catalog.",
            evidence="Catalog /Metadata stream exists."
        )]


class XMPDocumentTitleRule(BaseRule):
    rule_id = "PDFUA-META-002"
    name = "XMP Document Title"
    category = "Metadata"
    standard = "PDF/UA"
    severity = Severity.HIGH
    description = "The XMP metadata stream must contain the document title in Dublin Core namespace (<dc:title>) (ISO 14289-1, Clause 7.9 / Matterhorn 06-003)."
    remediation_template = "In Adobe Acrobat Pro, open File > Properties > Description, enter a Title, and save to synchronize XMP dc:title."

    def evaluate(self, doc: PDFDocumentModel) -> List[CheckResult]:
        has_xmp = doc.xmp_metadata_present
        xmp_title = doc.xmp_dc_title
        info_title = doc.doc_info_title

        if not has_xmp:
            evidence = (
                f"Legacy DocumentInfo /Title: {'YES: ' + repr(info_title) if info_title else 'MISSING'}\n"
                f"XMP metadata stream: MISSING\n"
                f"XMP dc:title: MISSING\n"
                f"Therefore PDF/UA document title requirement: FAIL"
            )
            return [self.create_result(
                status=CheckStatus.FAIL,
                message="Document Title is missing from XMP metadata (XMP stream is missing).",
                evidence=evidence,
                custom_severity=Severity.HIGH,
                custom_remediation="Embed an XMP metadata stream containing <dc:title>."
            )]

        if not xmp_title or not xmp_title.strip():
            evidence = (
                f"Legacy DocumentInfo /Title: {'YES: ' + repr(info_title) if info_title else 'MISSING'}\n"
                f"XMP metadata stream: PRESENT\n"
                f"XMP dc:title: MISSING\n"
                f"Therefore PDF/UA document title requirement: FAIL"
            )
            return [self.create_result(
                status=CheckStatus.FAIL,
                message="Document Title is missing from XMP metadata (<dc:title> is empty or missing).",
                evidence=evidence,
                custom_severity=Severity.HIGH,
                custom_remediation="Provide a concise, descriptive document Title in File > Properties > Description."
            )]

        evidence = (
            f"XMP dc:title: '{xmp_title}'\n"
            f"Legacy DocumentInfo /Title: '{info_title or ''}'"
        )
        return [self.create_result(
            status=CheckStatus.PASS,
            message=f"Document Title is defined in XMP metadata: '{xmp_title}'.",
            evidence=evidence
        )]


class PDFUAIdentifierRule(BaseRule):
    rule_id = "PDFUA-META-003"
    name = "PDF/UA Identifier"
    category = "Metadata"
    standard = "PDF/UA"
    severity = Severity.HIGH
    description = "The XMP metadata stream must contain the PDF/UA identifier flag (pdfuaid:part=1) (ISO 14289-1, Clause 7.9 / Matterhorn 06-004)."
    remediation_template = "In Adobe Acrobat Preflight, run 'Fix PDF/UA identifier' or re-export from your authoring tool with PDF/UA options enabled."

    def evaluate(self, doc: PDFDocumentModel) -> List[CheckResult]:
        if not doc.pdfua_identifier_present:
            evidence = (
                f"XMP metadata stream present: {'YES' if doc.xmp_metadata_present else 'NO'}\n"
                f"pdfuaid:part declaration: MISSING"
            )
            return [self.create_result(
                status=CheckStatus.FAIL,
                message="PDF/UA identification flag (pdfuaid:part=1) is missing from XMP metadata.",
                evidence=evidence,
                custom_severity=Severity.HIGH,
                custom_remediation="Add PDF/UA identifier using Acrobat Preflight or your PDF/UA export setting."
            )]

        return [self.create_result(
            status=CheckStatus.PASS,
            message=f"Document declares PDF/UA compliance (Part {doc.pdfua_part or 1}).",
            evidence=f"pdfuaid:part={doc.pdfua_part or 1} found in XMP metadata."
        )]


# Backwards-compatible alias for existing test runners
class MetadataCompletenessRule(BaseRule):
    rule_id = "PDFUA-META-001"
    name = "Metadata"
    category = "Metadata"
    standard = "PDF/UA"
    severity = Severity.HIGH

    def __init__(self):
        self._sub_rules = [
            XMPMetadataStreamRule(),
            XMPDocumentTitleRule(),
            PDFUAIdentifierRule()
        ]

    def evaluate(self, doc: PDFDocumentModel) -> List[CheckResult]:
        results = []
        for r in self._sub_rules:
            results.extend(r.evaluate(doc))
        return results
