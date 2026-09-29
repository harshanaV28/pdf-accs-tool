"""
Artifact Rules (ISO 14289-1, Clause 7.1 & Matterhorn Protocol Checkpoint 01-001)
Validates that artifacts are correctly handled and never included as tags within the structure tree.
"""

from typing import List
from ..rule_base import BaseRule
from ...core.models import PDFDocumentModel, CheckResult, CheckStatus, Severity


class ArtifactInStructureTreeRule(BaseRule):
    rule_id = "PDFUA-ARTIFACT-001"
    name = "Artifacts in Structure Tree"
    category = "Content"
    standard = "PDF/UA"
    severity = Severity.HIGH
    description = "Artifacts must not be tagged as structural elements inside the logical structure tree (ISO 14289-1, Clause 7.1)."
    remediation_template = "Remove the <Artifact> tag from the Structure Tree in Acrobat Pro. Mark it as an Artifact in the page content stream instead."

    def evaluate(self, doc: PDFDocumentModel) -> List[CheckResult]:
        results = []
        if not doc.structure_tree:
            return results

        all_nodes = doc.structure_tree.find_all_nodes()
        artifact_nodes = [n for n in all_nodes if n.standard_tag.upper() == "ARTIFACT" or n.tag.upper() == "ARTIFACT"]

        if artifact_nodes:
            for n in artifact_nodes[:5]:
                results.append(self.create_result(
                    status=CheckStatus.FAIL,
                    message=f"Illegal <Artifact> element found inside the logical structure tree on page {n.page or 'Doc'}.",
                    evidence=f"Structure tag <{n.tag}> on page {n.page}",
                    page=n.page,
                    object_reference=f"<{n.tag} id='{n.id}'>",
                    custom_severity=Severity.HIGH,
                    custom_remediation="Delete the Artifact tag from the tag tree; artifacts must only exist in page content streams."
                ))
        else:
            results.append(self.create_result(
                status=CheckStatus.PASS,
                message="No illegal <Artifact> tags present in the structure tree.",
                evidence="Structure tree artifact check passed."
            ))

        return results
