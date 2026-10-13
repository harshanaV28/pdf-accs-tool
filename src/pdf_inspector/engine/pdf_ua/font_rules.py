"""
Font Rules (ISO 14289-1, Clause 7.2)
Verifies that all glyphs are embedded and map reliably to Unicode characters.
"""

from typing import List
from ..rule_base import BaseRule
from ...core.models import PDFDocumentModel, FontModel, CheckResult, CheckStatus, Severity


class FontEmbeddingRule(BaseRule):
    rule_id = "PDFUA-FONT-001"
    name = "Fonts Embedded"
    category = "Fonts"
    standard = "PDF/UA"
    severity = Severity.HIGH
    description = "All fonts used in the document must be embedded or embedded as subsets (ISO 14289-1, Clause 7.2)."
    remediation_template = "Embed all fonts when exporting the PDF from your authoring tool (e.g. Word, InDesign) or in Adobe Acrobat Preflight."

    def evaluate(self, doc: PDFDocumentModel) -> List[CheckResult]:
        results = []
        if not doc.fonts:
            return results

        unembedded = [f for f in doc.fonts if not f.is_embedded and f.is_used]
        if unembedded:
            for f in unembedded:
                target_pages = f.pages if f.pages else [1]
                for p in target_pages:
                    results.append(self.create_result(
                        status=CheckStatus.FAIL,
                        message=f"Font '{f.name}' is not embedded.",
                        evidence=f"Font: {f.name}, Subtype: {f.subtype}, Page: {p}",
                        page=p,
                        object_reference=f"Font {f.name}",
                        custom_remediation="Open document in Acrobat Pro Preflight, select 'Embed missing fonts', and save the file.",
                        items_count=1
                    ))
            passed_cnt = max(0, len(doc.fonts) - len(unembedded))
            if passed_cnt > 0:
                results.append(self.create_result(
                    status=CheckStatus.PASS,
                    message=f"{passed_cnt} of {len(doc.fonts)} font(s) in the document are embedded.",
                    evidence=f"Embedded fonts: {passed_cnt}/{len(doc.fonts)}",
                    items_count=passed_cnt
                ))
        else:
            results.append(self.create_result(
                status=CheckStatus.PASS,
                message=f"All {len(doc.fonts)} font(s) in the document are embedded.",
                evidence=f"Total embedded fonts: {len(doc.fonts)}",
                items_count=len(doc.fonts)
            ))

        return results


class FontToUnicodeRule(BaseRule):
    rule_id = "PDFUA-FONT-002"
    name = "ToUnicode CMaps"
    category = "Fonts"
    standard = "PDF/UA"
    severity = Severity.HIGH
    description = "Fonts must provide Unicode mapping (ToUnicode CMap or standard encoding) so assistive technology can reliably voice the text."
    remediation_template = "Re-export PDF with full Unicode mappings or standard TrueType/OpenType font embedding."

    @staticmethod
    def _has_unicode_mapping(f: FontModel) -> bool:
        """
        Determines whether a font provides a valid Unicode mapping per ISO 32000-1 §9.10.
        A font provides Unicode mappings via:
        1. An explicit /ToUnicode CMap stream.
        2. Predefined standard encodings (WinAnsiEncoding, MacRomanEncoding, StandardEncoding, PDFDocEncoding).
        """
        if f.has_tounicode:
            return True
        if getattr(f, "has_standard_encoding", False):
            return True
        clean_enc = str(f.encoding).strip("/")
        if clean_enc in (
            "WinAnsiEncoding", "MacRomanEncoding", "StandardEncoding", "PDFDocEncoding"
        ):
            return True
        return False

    def evaluate(self, doc: PDFDocumentModel) -> List[CheckResult]:
        results = []
        if not doc.fonts:
            return results

        used_fonts = [f for f in doc.fonts if f.is_used]
        if not used_fonts:
            return results

        # 1. Defect Detection: Evaluate ALL used fonts (embedded and unembedded) for Unicode mappings (Matterhorn 14-003)
        unmapped_fonts = [f for f in used_fonts if not self._has_unicode_mapping(f)]
        if unmapped_fonts:
            for f in unmapped_fonts:
                p_num = f.pages[0] if f.pages else 1
                results.append(self.create_result(
                    status=CheckStatus.WARNING,
                    message=f"Font '{f.name}' lacks a valid Unicode mapping (/ToUnicode CMap or standard encoding).",
                    evidence=f"Font: {f.name}, Subtype: {f.subtype}, Encoding: {f.encoding}, Embedded: {f.is_embedded}, Pages: {f.pages}",
                    page=p_num,
                    object_reference=f"Font {f.name}",
                    custom_remediation="Convert font to OpenType/TrueType with explicit Unicode mappings before exporting to PDF.",
                    items_count=1
                ))

        # 2. Conforming Pass Accounting:
        # Per ISO 14289-1 Clause 7.2 & Note 1, Unicode mapping extraction is guaranteed for embedded fonts.
        # An unembedded font violates Clause 7.2 (14-001) and must not be awarded a PDF/UA compliance PASS.
        # Conforming passes are awarded strictly to embedded fonts that have valid Unicode mappings.
        conforming_embedded = [f for f in used_fonts if f.is_embedded and self._has_unicode_mapping(f)]
        if conforming_embedded:
            results.append(self.create_result(
                status=CheckStatus.PASS,
                message=f"{len(conforming_embedded)} embedded font(s) provide valid Unicode mappings.",
                evidence=f"Validated Unicode mappings for {len(conforming_embedded)} font(s).",
                items_count=len(conforming_embedded)
            ))

        return results
