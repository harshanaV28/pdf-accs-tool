"""
Document Settings Rules (ISO 14289-1:2014, Clause 7.10 & 7.19, Matterhorn Checkpoints 07-001, 07-003, 21-002, 31-003)
Verifies ViewerPreferences /DisplayDocTitle, page tab navigation order, document bookmarks, and MarkInfo /Suspects.
"""

from typing import List
from ..rule_base import BaseRule
from ...core.models import PDFDocumentModel, CheckResult, CheckStatus, Severity


class DisplayDocTitleRule(BaseRule):
    rule_id = "PDFUA-SETTINGS-001"
    name = "DisplayDocTitle"
    category = "Document settings"
    standard = "PDF/UA"
    severity = Severity.HIGH
    description = "ViewerPreferences dictionary must contain /DisplayDocTitle set to true (ISO 14289-1, Clause 7.10 / Matterhorn 07-001)."
    remediation_template = "In Acrobat Pro, open File > Properties > Initial View, and under 'Window Options' set 'Show' to 'Document Title' instead of 'File Name'."

    def evaluate(self, doc: PDFDocumentModel) -> List[CheckResult]:
        results = []

        if not doc.display_doc_title:
            results.append(self.create_result(
                status=CheckStatus.FAIL,
                message="DisplayDocTitle is not set to true. User agents will display the filename instead of the document title.",
                evidence="ViewerPreferences/DisplayDocTitle is false or missing.",
                custom_severity=Severity.HIGH,
                custom_remediation="Set Initial View > Show > Document Title in File Properties."
            ))
        else:
            results.append(self.create_result(
                status=CheckStatus.PASS,
                message="DisplayDocTitle is set to true in ViewerPreferences.",
                evidence="ViewerPreferences/DisplayDocTitle is true."
            ))

        # Check 2: MarkInfo Suspects (ISO 14289-1 Clause 7.18, Matterhorn Checkpoint 31-003)
        if getattr(doc, "has_suspects", False):
            results.append(self.create_result(
                status=CheckStatus.FAIL,
                message="The Suspects entry in the MarkInfo dictionary is set to true.",
                evidence="MarkInfo /Suspects is true.",
                custom_severity=Severity.HIGH,
                custom_remediation="Resolve OCR suspects or remove /Suspects from the MarkInfo dictionary."
            ))
        else:
            results.append(self.create_result(
                status=CheckStatus.PASS,
                message="Document MarkInfo dictionary has no OCR suspect flags.",
                evidence="MarkInfo /Suspects is absent or false."
            ))

        return results


class BookmarkStructureRule(BaseRule):
    rule_id = "PDFUA-SETTINGS-003"
    name = "Document Bookmarks"
    category = "Document settings"
    standard = "PDF/UA"
    severity = Severity.MEDIUM
    description = "Documents with more than 20 pages must include bookmarks for document outline navigation (ISO 14289-1, Clause 7.19 / Matterhorn 21-002)."
    remediation_template = "Generate bookmarks in Acrobat Pro from headings or table of contents."

    def evaluate(self, doc: PDFDocumentModel) -> List[CheckResult]:
        if doc.bookmarks:
            return [self.create_result(
                status=CheckStatus.PASS,
                message=f"Document contains {len(doc.bookmarks)} bookmark outline item(s).",
                evidence=f"Bookmarks present: {len(doc.bookmarks)} top-level item(s)."
            )]
        elif doc.page_count > 20:
            return [self.create_result(
                status=CheckStatus.WARNING,
                message=f"Document has {doc.page_count} pages but lacks bookmarks for navigation (ISO 14289-1, Clause 7.19).",
                evidence=f"Page count: {doc.page_count} (> 20 pages threshold), Bookmarks: 0",
                custom_severity=Severity.MEDIUM,
                custom_remediation="Add document bookmarks in Acrobat Pro for documents exceeding 20 pages."
            )]
        else:
            return [self.create_result(
                status=CheckStatus.PASS,
                message=f"Document has {doc.page_count} pages; bookmarks are optional for documents with 20 or fewer pages.",
                evidence=f"Page count: {doc.page_count} (<= 20 pages threshold)"
            )]
