"""
Document Settings Rules (ISO 14289-1, Clause 7.10)
Verifies that ViewerPreferences displays the document title in the window frame and page tab order follows the structure tree.
"""

from typing import List
from ..rule_base import BaseRule
from ...core.models import PDFDocumentModel, CheckResult, CheckStatus, Severity


class DisplayDocTitleRule(BaseRule):
    rule_id = "PDFUA-SETTINGS-001"
    name = "Document settings"
    category = "Document settings"
    standard = "PDF/UA"
    severity = Severity.HIGH
    description = "ViewerPreferences must have DisplayDocTitle set to true so user agents display the document title in the title bar (ISO 14289-1, Clause 7.10)."
    remediation_template = "In Acrobat Pro, open File > Properties > Initial View, and under 'Window Options' set 'Show' to 'Document Title' instead of 'File Name'."

    def evaluate(self, doc: PDFDocumentModel) -> List[CheckResult]:
        results = []

        if not doc.display_doc_title:
            results.append(self.create_result(
                status=CheckStatus.FAIL,
                message="DisplayDocTitle is not set to true. The window title bar will show the filename instead of the document title.",
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

        # Check Tab order for pages
        non_structure_tabs = []
        for p in doc.pages:
            if p.tab_order_mode != "S":
                non_structure_tabs.append(p.page_number)

        if non_structure_tabs and doc.is_tagged:
            results.append(self.create_result(
                status=CheckStatus.FAIL,
                message=f"Tab order on page(s) {non_structure_tabs[:8]} is not explicitly set to Structure Order (/Tabs /S).",
                evidence=f"Pages without /Tabs /S: {non_structure_tabs[:8]} (total: {len(non_structure_tabs)})",
                page=non_structure_tabs[0],
                custom_severity=Severity.HIGH,
                custom_remediation="In Acrobat Pro Page Thumbnails panel, select all pages, open Page Properties, and set Tab Order to 'Use Document Structure'."
            ))
        else:
            results.append(self.create_result(
                status=CheckStatus.PASS,
                message="Page tab navigation conforms to document structure order.",
                evidence="Tab order is set to Structure (/Tabs /S) across pages."
            ))

        # Check 3: MarkInfo Suspects (ISO 14289-1 Clause 7.18, Matterhorn Checkpoint 31-003)
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
