"""
Role Mapping Rules (ISO 14289-1, Clause 7.4.4)
Verifies that any custom non-standard tags are mapped via /RoleMap to valid ISO 32000-1 structure types.
"""

from typing import List
from ..rule_base import BaseRule
from ...core.models import PDFDocumentModel, CheckResult, CheckStatus, Severity
from ...core.structure_tree import STANDARD_STRUCTURE_TYPES, resolve_role


class RoleMappingValidityRule(BaseRule):
    rule_id = "PDFUA-ROLE-001"
    name = "Role Mapping"
    category = "Role mapping"
    standard = "PDF/UA"
    severity = Severity.HIGH
    description = "Non-standard structure types must be mapped in the /RoleMap dictionary directly or indirectly to standard structure types."
    remediation_template = "Open the Role Map in Acrobat Pro (Tags Panel > Options > Edit Role Map) and map custom tags to standard PDF tags."

    def evaluate(self, doc: PDFDocumentModel) -> List[CheckResult]:
        results = []
        if not doc.structure_tree:
            return results

        all_nodes = doc.structure_tree.find_all_nodes()
        unmapped_tags = set()
        circular_tags = set()

        for node in all_nodes:
            if node.tag == "StructTreeRoot":
                continue
            std_role, is_mapped, is_circ = resolve_role(node.tag, doc.role_map)
            if is_circ:
                circular_tags.add(node.tag)
            elif std_role.upper() not in STANDARD_STRUCTURE_TYPES:
                unmapped_tags.add(node.tag)

        if circular_tags:
            for tag in circular_tags:
                results.append(self.create_result(
                    status=CheckStatus.FAIL,
                    message=f"Circular role mapping detected for tag <{tag}>.",
                    evidence=f"Tag: <{tag}> -> {doc.role_map.get(tag)}",
                    custom_severity=Severity.HIGH,
                    custom_remediation=f"Edit the Role Map and remove the circular loop for <{tag}>."
                ))

        if unmapped_tags:
            for tag in unmapped_tags:
                results.append(self.create_result(
                    status=CheckStatus.FAIL,
                    message=f"Custom structure type <{tag}> is not mapped to any standard ISO 32000-1 structure type.",
                    evidence=f"Tag <{tag}> not found in /RoleMap or does not resolve to standard type.",
                    custom_severity=Severity.HIGH,
                    custom_remediation=f"Map <{tag}> to a standard tag (e.g. P, H1, Span, Div) in the Role Map."
                ))

        if not circular_tags and not unmapped_tags:
            results.append(self.create_result(
                status=CheckStatus.PASS,
                message="All custom structure types are properly mapped to standard structure types.",
                evidence=f"RoleMap size: {len(doc.role_map)}"
            ))

        return results
