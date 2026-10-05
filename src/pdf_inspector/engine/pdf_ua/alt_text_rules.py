"""
Alternative Descriptions Rules (ISO 14289-1, Clause 7.18)
Verifies that Figures, Formulas, and other graphical elements have meaningful alternative descriptions.
"""

from typing import List
import re
from ..rule_base import BaseRule
from ...core.models import PDFDocumentModel, CheckResult, CheckStatus, Severity

# Placeholder and filename regexes
FILENAME_PATTERN = re.compile(r"^.*\.(png|jpe?g|gif|bmp|tiff|svg|webp|ico|pdf)$", re.IGNORECASE)
PLACEHOLDER_PATTERN = re.compile(r"^(image|figure|photo|graphic|picture|placeholder|untitled|alt text)$", re.IGNORECASE)


class FigureAlternativeTextRule(BaseRule):
    rule_id = "PDFUA-ALT-001"
    name = "Alternative Descriptions"
    category = "Alternative Descriptions"
    standard = "PDF/UA"
    severity = Severity.HIGH
    description = "Every Figure and Formula element must possess an alternative description (/Alt) or /ActualText (ISO 14289-1, Clause 7.18)."
    remediation_template = "In Acrobat Pro, right-click Figure tag > Properties > Tag tab > Alternative Text, and enter a descriptive alternative."

    def evaluate(self, doc: PDFDocumentModel) -> List[CheckResult]:
        results = []
        if not doc.structure_tree:
            # If not tagged at all, figure check returns warning
            return [self.create_result(
                status=CheckStatus.WARNING,
                message="Cannot verify figure alternate descriptions because document is untagged.",
                evidence="No structure tree available."
            )]

        figure_nodes = doc.structure_tree.find_all_by_standard_tag("Figure")
        formula_nodes = doc.structure_tree.find_all_by_standard_tag("Formula")
        all_graphics = figure_nodes + formula_nodes

        if not all_graphics and not doc.images:
            results.append(self.create_result(
                status=CheckStatus.PASS,
                message="No graphical figures or formulas found in the document.",
                evidence="Graphic elements count: 0"
            ))
            return results

        missing_alt = []
        placeholder_alt = []

        for node in all_graphics:
            alt = (node.alt_text or node.actual_text or "").strip()
            page = node.page or 1
            bbox = node.bbox

            if not alt:
                missing_alt.append((node.tag, page, bbox, node.id))
            elif FILENAME_PATTERN.match(alt) or PLACEHOLDER_PATTERN.match(alt) or len(alt) <= 2:
                placeholder_alt.append((node.tag, alt, page, bbox, node.id))

        # Check for untagged images
        untagged_images = [img for img in doc.images if not img.is_artifact and not img.has_alt]

        if missing_alt:
            for tag, pg, bbox, nid in missing_alt:
                results.append(self.create_result(
                    status=CheckStatus.FAIL,
                    message=f"<{tag}> element lacks an alternative description (/Alt).",
                    evidence=f"<{tag}> on page {pg} has no /Alt or /ActualText.",
                    page=pg,
                    bounding_box=bbox,
                    object_reference=f"<{tag} id='{nid}'>",
                    custom_severity=Severity.HIGH,
                    custom_remediation="Add an informative alternative description describing the visual content of the figure."
                ))

        if placeholder_alt:
            for tag, text, pg, bbox, nid in placeholder_alt:
                results.append(self.create_result(
                    status=CheckStatus.WARNING,
                    message=f"<{tag}> has suspicious placeholder or filename alternative text: '{text}'.",
                    evidence=f"Alternative text: '{text}' on page {pg}",
                    page=pg,
                    bounding_box=bbox,
                    object_reference=f"<{tag} id='{nid}'>",
                    custom_severity=Severity.MEDIUM,
                    custom_remediation="Replace file names or generic placeholders with meaningful descriptive alt text."
                ))

        if untagged_images:
            for img in untagged_images[:5]:
                results.append(self.create_result(
                    status=CheckStatus.FAIL,
                    message=f"Image on page {img.page} is not tagged as Figure or marked as Artifact.",
                    evidence=f"Image dimensions {img.width}x{img.height} at {img.bbox}",
                    page=img.page,
                    bounding_box=img.bbox,
                    object_reference=f"Image {img.id}",
                    custom_severity=Severity.HIGH,
                    custom_remediation="Tag the image as a <Figure> with alt text, or mark it as an Artifact if purely decorative."
                ))

        if not missing_alt and not placeholder_alt and not untagged_images:
            passed_cnt = len(all_graphics) if all_graphics else len(doc.images)
            results.append(self.create_result(
                status=CheckStatus.PASS,
                message=f"All {passed_cnt} figure/formula element(s) have valid alternative descriptions.",
                evidence="All graphical elements contain non-empty descriptive text.",
                items_count=passed_cnt
            ))
        elif not missing_alt and not untagged_images and placeholder_alt:
            passed_cnt = max(0, len(all_graphics) - len(placeholder_alt))
            if passed_cnt > 0:
                results.append(self.create_result(
                    status=CheckStatus.PASS,
                    message=f"{passed_cnt} figure/formula element(s) have valid alternative descriptions.",
                    evidence=f"Passed figures: {passed_cnt}/{len(all_graphics)}",
                    items_count=passed_cnt
                ))

        return results
