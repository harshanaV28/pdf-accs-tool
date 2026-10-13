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
    category = "Natural language"
    standard = "PDF/UA"
    severity = Severity.HIGH
    description = "Characters mapped to Unicode Private Use Area (PUA: U+E000 to U+F8FF) must have an /ActualText replacement."
    remediation_template = "Replace custom icon/symbol font glyphs with standard Unicode symbols or enclose in a Span with /ActualText."

    def evaluate(self, doc: PDFDocumentModel) -> List[CheckResult]:
        results = []
        unexempt_findings = []

        def is_pua(c: str) -> bool:
            cp = ord(c)
            return (0xE000 <= cp <= 0xF8FF) or (0xF0000 <= cp <= 0x10FFFD)

        # 1. Structure Tree evaluation
        if doc.structure_tree:
            all_nodes = doc.structure_tree.find_all_nodes()
            for node in all_nodes:
                txt = node.text_content or ""
                pua_chars = [c for c in txt if is_pua(c)]
                if not pua_chars:
                    continue

                # Conforming exceptions per ISO 14289-1 Clause 7.2:
                # - Inside a Formula/Math element (Clause 7.5)
                # - Covered by /ActualText or /Alt on the element or an ancestor
                # - Marked as an Artifact/decorative element
                if node.is_in_formula() or node.has_actual_text_ancestor() or node.is_artifact_ancestor():
                    continue

                unexempt_findings.append({
                    "page": node.page or 1,
                    "count": len(pua_chars),
                    "first_hex": hex(ord(pua_chars[0])),
                    "tag": node.tag,
                    "bbox": node.bbox,
                    "object_ref": f"<{node.tag} id='{node.id}'>"
                })

        # 2. Check for PUA characters in page text outside the structure tree
        if not doc.structure_tree:
            for p in doc.pages:
                pua_chars = [c for c in p.text if is_pua(c)]
                if not pua_chars:
                    continue
                art_texts = [a.text_snippet for a in doc.all_artifacts if a.page_number == p.page_number and a.text_snippet]
                unexempt_page_chars = [c for c in pua_chars if not any(c in at for at in art_texts)]
                if unexempt_page_chars:
                    unexempt_findings.append({
                        "page": p.page_number,
                        "count": len(unexempt_page_chars),
                        "first_hex": hex(ord(unexempt_page_chars[0])),
                        "tag": "PageText",
                        "bbox": None,
                        "object_ref": f"Page {p.page_number}"
                    })

        if unexempt_findings:
            for finding in unexempt_findings[:5]:
                pg = finding["page"]
                cnt = finding["count"]
                first_hex = finding["first_hex"]
                tag = finding["tag"]
                results.append(self.create_result(
                    status=CheckStatus.WARNING,
                    message=f"<{tag}> element on page {pg} contains {cnt} character(s) mapped to Unicode Private Use Area ({first_hex}) without /ActualText.",
                    evidence=f"PUA character {first_hex} in <{tag}> on page {pg}",
                    page=pg,
                    bounding_box=finding["bbox"],
                    object_reference=finding["object_ref"],
                    custom_severity=Severity.HIGH,
                    custom_remediation="Assign /ActualText to the PUA glyph span or replace with standard Unicode characters so screen readers can voice its meaning.",
                    items_count=cnt
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
    category = "Natural language"
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
