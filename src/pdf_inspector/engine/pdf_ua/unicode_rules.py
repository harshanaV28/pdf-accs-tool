"""
Unicode Mapping & Glyph Rules (ISO 14289-1, Clause 7.2 & Matterhorn Protocol Checkpoints 10-001, 10-002)
Detects Private Use Area (PUA) codepoints and replacement characters (U+FFFD) lacking /ActualText.
"""

from typing import List
import re
from ..rule_base import BaseRule
from ...core.models import PDFDocumentModel, CheckResult, CheckStatus, Severity


class UnicodePUARule(BaseRule):
    rule_id = "PDFUA-UNICODE-001"
    name = "Unicode Private Use Area"
    category = "Fonts"
    standard = "PDF/UA"
    severity = Severity.HIGH
    description = "Characters mapped to Unicode Private Use Area (PUA: U+E000 to U+F8FF) must have an /ActualText replacement."
    remediation_template = "Replace custom icon/symbol font glyphs with standard Unicode symbols or enclose in a Span with /ActualText."

    def evaluate(self, doc: PDFDocumentModel) -> List[CheckResult]:
        results = []
        pua_pages = []

        for p in doc.pages:
            # Check for PUA range: \uE000 - \uF8FF
            pua_chars = [c for c in p.text if 0xE000 <= ord(c) <= 0xF8FF]
            if pua_chars:
                pua_pages.append((p.page_number, len(pua_chars), hex(ord(pua_chars[0]))))

        if pua_pages:
            for pg, cnt, first_hex in pua_pages[:5]:
                results.append(self.create_result(
                    status=CheckStatus.WARNING,
                    message=f"Page {pg} contains {cnt} character(s) mapped to Unicode Private Use Area (e.g. {first_hex}).",
                    evidence=f"PUA count: {cnt} on page {pg}",
                    page=pg,
                    custom_severity=Severity.HIGH,
                    custom_remediation="Assign /ActualText to the PUA glyph span so screen readers can voice its meaning."
                ))
        else:
            results.append(self.create_result(
                status=CheckStatus.PASS,
                message="No unannounced Unicode Private Use Area (PUA) glyphs detected.",
                evidence="PUA character check passed.",
                items_count=0
            ))

        return results


class ReplacementCharacterRule(BaseRule):
    rule_id = "PDFUA-UNICODE-002"
    name = "Replacement Characters"
    category = "Fonts"
    standard = "PDF/UA"
    severity = Severity.HIGH
    description = "Text should not contain unmapped glyph replacement characters (U+FFFD)."
    remediation_template = "Ensure font embedding and ToUnicode CMaps map every glyph to a real character."

    def evaluate(self, doc: PDFDocumentModel) -> List[CheckResult]:
        results = []
        r_pages = []

        for p in doc.pages:
            if "\uFFFD" in p.text:
                r_pages.append(p.page_number)

        if r_pages:
            results.append(self.create_result(
                status=CheckStatus.FAIL,
                message=f"Replacement character (U+FFFD / unmapped glyph) detected on page(s): {r_pages[:5]}.",
                evidence=f"Pages with U+FFFD: {r_pages}",
                page=r_pages[0],
                custom_severity=Severity.HIGH,
                custom_remediation="Fix font encoding or re-embed the font with a complete ToUnicode table.",
                items_count=len(r_pages)
            ))
        else:
            results.append(self.create_result(
                status=CheckStatus.PASS,
                message="No replacement characters (U+FFFD) detected in extracted text.",
                evidence="Glyph mapping integrity verified.",
                items_count=0
            ))

        return results
