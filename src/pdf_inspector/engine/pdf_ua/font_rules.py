"""
Font Rules (ISO 14289-1, Clause 7.2)
Verifies that all glyphs are embedded and map reliably to Unicode characters.
"""

from typing import List
from ..rule_base import BaseRule
from ...core.models import PDFDocumentModel, CheckResult, CheckStatus, Severity


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
            results.append(self.create_result(
                status=CheckStatus.PASS,
                message="No text fonts detected in document (or document contains no text).",
                evidence="Font count: 0"
            ))
            return results

        unembedded = [f for f in doc.fonts if not f.is_embedded and f.is_used]
        if unembedded:
            for f in unembedded:
                results.append(self.create_result(
                    status=CheckStatus.FAIL,
                    message=f"Font '{f.name}' is not embedded.",
                    evidence=f"Font: {f.name}, Subtype: {f.subtype}, Used on page(s): {f.pages}",
                    page=f.pages[0] if f.pages else 1,
                    object_reference=f"Font {f.name}",
                    custom_remediation=f"Open document in Acrobat Pro Preflight, select 'Embed missing fonts', and save the file."
                ))
        else:
            results.append(self.create_result(
                status=CheckStatus.PASS,
                message=f"All {len(doc.fonts)} font(s) in the document are embedded.",
                evidence=f"Total embedded fonts: {len(doc.fonts)}"
            ))

        return results


class FontToUnicodeRule(BaseRule):
    rule_id = "PDFUA-FONT-002"
    name = "ToUnicode CMaps"
    category = "Fonts"
    standard = "PDF/UA"
    severity = Severity.HIGH
    description = "Fonts must provide Unicode mapping (ToUnicode CMap) so assistive technology can reliably voice the text."
    remediation_template = "Re-export PDF with full Unicode mappings or standard TrueType/OpenType font embedding."

    def evaluate(self, doc: PDFDocumentModel) -> List[CheckResult]:
        results = []
        if not doc.fonts:
            return results

        missing_tounicode = [f for f in doc.fonts if not f.has_tounicode and f.is_used and f.subtype not in ("Type0", "Type3")]
        if missing_tounicode:
            for f in missing_tounicode:
                results.append(self.create_result(
                    status=CheckStatus.WARNING,
                    message=f"Font '{f.name}' lacks an explicit /ToUnicode mapping stream.",
                    evidence=f"Font: {f.name}, Encoding: {f.encoding}, Pages: {f.pages}",
                    page=f.pages[0] if f.pages else 1,
                    object_reference=f"Font {f.name}",
                    custom_remediation=f"Convert font to OpenType/TrueType with explicit Unicode mappings before exporting to PDF."
                ))
        else:
            results.append(self.create_result(
                status=CheckStatus.PASS,
                message="All fonts have valid Unicode mapping tables.",
                evidence="ToUnicode verification passed."
            ))

        return results
