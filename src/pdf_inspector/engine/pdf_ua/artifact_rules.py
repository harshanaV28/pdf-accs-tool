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


class ArtifactInsideTaggedContentRule(BaseRule):
    rule_id = "PDFUA-ART-003"
    name = "Artifacts inside tagged content"
    category = "Content"
    standard = "PDF/UA"
    severity = Severity.HIGH
    description = "Content marked as an artifact must not be present inside tagged content (ISO 14289-1:2013 Clause 7.1, Matterhorn Checkpoint 01-003)."
    remediation_template = "Move the artifact outside of tagged content sequences in the page content stream or remove the enclosing structural tags in Acrobat Pro."

    def evaluate(self, doc: PDFDocumentModel) -> List[CheckResult]:
        results = []
        artifacts = doc.all_artifacts
        if not artifacts:
            results.append(self.create_result(
                status=CheckStatus.PASS,
                message="No content marked as Artifact is present inside tagged content.",
                evidence="Artifacts inside tagged content count: 0",
                items_count=1
            ))
            return results

        invalid_artifacts = [a for a in artifacts if a.is_inside_tagged]
        valid_artifacts = [a for a in artifacts if not a.is_inside_tagged]

        if invalid_artifacts:
            for art in invalid_artifacts:
                obj_ref_parts = []
                if art.parent_tag:
                    if art.parent_mcid is not None:
                        obj_ref_parts.append(f"<{art.parent_tag} MCID={art.parent_mcid}>")
                    else:
                        obj_ref_parts.append(f"<{art.parent_tag}>")
                if art.xobject_name:
                    obj_ref_parts.append(f"/{art.xobject_name}")
                else:
                    obj_ref_parts.append("/Artifact")
                obj_ref = " -> ".join(obj_ref_parts)

                evidence = f"Artifact present inside tagged content <{art.parent_tag or 'TaggedContent'}> on page {art.page_number}."
                if art.text_snippet:
                    evidence += f" Content: \"{art.text_snippet[:100]}\""

                results.append(self.create_result(
                    status=CheckStatus.FAIL,
                    message="Artifact present inside tagged content.",
                    evidence=evidence,
                    page=art.page_number,
                    bounding_box=art.bbox,
                    object_reference=obj_ref,
                    custom_severity=Severity.HIGH,
                    custom_remediation=self.remediation_template,
                    items_count=1
                ))

            if valid_artifacts:
                results.append(self.create_result(
                    status=CheckStatus.PASS,
                    message=f"{len(valid_artifacts)} artifact(s) correctly placed outside tagged content.",
                    evidence=f"Artifact content validation passed: {len(valid_artifacts)}/{len(artifacts)}",
                    items_count=len(valid_artifacts)
                ))
        else:
            results.append(self.create_result(
                status=CheckStatus.PASS,
                message=f"All {len(valid_artifacts)} artifact(s) are correctly placed outside tagged content.",
                evidence=f"Artifact content validation passed: {len(valid_artifacts)}/{len(artifacts)}",
                items_count=len(valid_artifacts) if valid_artifacts else 1
            ))

        return results
