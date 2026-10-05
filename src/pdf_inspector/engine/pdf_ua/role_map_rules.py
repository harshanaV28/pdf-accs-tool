"""
Role Mapping Rules (ISO 14289-1, Clause 7.4.4)
Verifies that any custom non-standard tags are mapped via /RoleMap to valid ISO 32000-1 structure types.
"""

from typing import List
from ..rule_base import BaseRule
from ...core.models import PDFDocumentModel, CheckResult, CheckStatus, Severity
from ...core.structure_tree import STANDARD_STRUCTURE_TYPES_EXACT, resolve_role


class RoleMappingValidityRule(BaseRule):
    rule_id = "PDFUA-ROLE-001"
    name = "Role Mapping"
    category = "Role mapping"
    standard = "PDF/UA"
    severity = Severity.HIGH
    description = "Non-standard structure types must be mapped in the /RoleMap dictionary directly or indirectly to standard structure types (ISO 14289-1, Clause 7.4.4)."
    remediation_template = "Open the Role Map in Acrobat Pro (Tags Panel > Options > Edit Role Map) and map custom tags to standard PDF tags."

    def evaluate(self, doc: PDFDocumentModel) -> List[CheckResult]:
        results = []
        if not doc.structure_tree:
            return results

        all_nodes = [n for n in doc.structure_tree.find_all_nodes() if n.tag != "StructTreeRoot"]
        total_tags = len(all_nodes)
        unmapped_nodes = []
        circular_nodes = []

        for node in all_nodes:
            std_role, is_mapped, is_circ = resolve_role(node.tag, doc.role_map)
            if is_circ:
                circular_nodes.append(node)
            elif std_role not in STANDARD_STRUCTURE_TYPES_EXACT:
                unmapped_nodes.append((node, std_role))

        if circular_nodes:
            for node in circular_nodes[:5]:
                results.append(self.create_result(
                    status=CheckStatus.FAIL,
                    message=f"Circular role mapping detected for tag <{node.tag}>.",
                    evidence=f"Tag: <{node.tag}> -> {doc.role_map.get(node.tag)}",
                    page=node.page or 1,
                    object_reference=f"<{node.tag}>",
                    custom_severity=Severity.HIGH,
                    custom_remediation=f"Edit the Role Map and remove the circular loop for <{node.tag}>.",
                    items_count=1
                ))
            if len(circular_nodes) > 5:
                rem = len(circular_nodes) - 5
                results.append(self.create_result(
                    status=CheckStatus.FAIL,
                    message=f"{rem} additional circular role mapping(s) detected.",
                    evidence="Circular role mappings present.",
                    custom_severity=Severity.HIGH,
                    custom_remediation="Edit Role Map to break circular references.",
                    items_count=rem
                ))

        if unmapped_nodes:
            for node, std_r in unmapped_nodes[:5]:
                results.append(self.create_result(
                    status=CheckStatus.FAIL,
                    message=f'Non-standard structure type "{node.tag}" is neither mapped to a standard structure type nor to another non-standard structure type.',
                    evidence=f'Tag "{node.tag}" not found in /RoleMap or does not resolve to an ISO 32000-1 standard type.',
                    page=node.page or 1,
                    object_reference=f"<{node.tag}>",
                    custom_severity=Severity.HIGH,
                    custom_remediation=f'Map "{node.tag}" to a standard tag (e.g. LBody, P, H1, Span, Div) in the Role Map.',
                    items_count=1
                ))
            if len(unmapped_nodes) > 5:
                rem = len(unmapped_nodes) - 5
                results.append(self.create_result(
                    status=CheckStatus.FAIL,
                    message=f"{rem} additional non-standard structure element(s) are unmapped in /RoleMap.",
                    evidence="Unmapped custom structure types in document.",
                    custom_severity=Severity.HIGH,
                    custom_remediation="Map all custom tags to standard ISO structure types in Role Map.",
                    items_count=rem
                ))

        error_count = len(circular_nodes) + len(unmapped_nodes)
        passed_count = max(0, total_tags - error_count)
        if passed_count > 0:
            results.append(self.create_result(
                status=CheckStatus.PASS,
                message=f"{passed_count} structure element(s) have valid standard or mapped roles.",
                evidence=f"Validated roles: {passed_count}/{total_tags} (RoleMap entries: {len(doc.role_map)})",
                items_count=passed_count
            ))

        return results
