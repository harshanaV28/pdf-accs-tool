"""
ParentTree Rules (ISO 14289-1, Clause 7.1 & Matterhorn Protocol Checkpoint 01-002, 01-003)
Verifies integrity of the /ParentTree number tree mapping pages and annotations to structure elements.
"""

from typing import List
from ..rule_base import BaseRule
from ...core.models import PDFDocumentModel, CheckResult, CheckStatus, Severity


class ParentTreeIntegrityRule(BaseRule):
    rule_id = "PDFUA-TREE-002"
    name = "ParentTree Integrity"
    category = "Structure tree"
    standard = "PDF/UA"
    severity = Severity.HIGH
    description = "The structure tree must include a valid /ParentTree number tree that accurately maps page content and annotations to structural elements."
    remediation_template = "Regenerate tags and the ParentTree in Acrobat Pro or re-export using a PDF/UA compliant authoring tool."

    def evaluate(self, doc: PDFDocumentModel) -> List[CheckResult]:
        results = []
        if not doc.is_tagged or not doc.structure_tree:
            return results

        if not doc.has_parent_tree:
            results.append(self.create_result(
                status=CheckStatus.FAIL,
                message="/StructTreeRoot is missing the mandatory /ParentTree number tree.",
                evidence="StructTreeRoot has no /ParentTree entry.",
                custom_severity=Severity.HIGH,
                custom_remediation="Add or reconstruct the ParentTree using an accessible PDF tool."
            ))
            return results

        if not doc.parent_tree_valid:
            results.append(self.create_result(
                status=CheckStatus.WARNING,
                message="/ParentTree number tree exists but contains no valid entry mappings.",
                evidence=f"ParentTree entries count: {doc.parent_tree_entries_count}",
                custom_severity=Severity.MEDIUM,
                custom_remediation="Verify that structural elements and marked content references are indexed in the ParentTree."
            ))
        else:
            results.append(self.create_result(
                status=CheckStatus.PASS,
                message=f"/ParentTree number tree is present and valid with {doc.parent_tree_entries_count} mapped entries.",
                evidence=f"ParentTree entries: {doc.parent_tree_entries_count}",
                items_count=0
            ))

        # Check page /StructParents
        pages_missing_struct_parents = []
        for p in doc.pages:
            if p.mcids and p.struct_parents_id is None:
                pages_missing_struct_parents.append(p.page_number)

        if pages_missing_struct_parents:
            results.append(self.create_result(
                status=CheckStatus.FAIL,
                message=f"Page(s) {pages_missing_struct_parents[:5]} contain marked content (MCIDs) but lack /StructParents page dictionary entry.",
                evidence=f"Pages missing /StructParents: {pages_missing_struct_parents}",
                page=pages_missing_struct_parents[0],
                custom_severity=Severity.HIGH,
                custom_remediation="Ensure every page with marked content defines a /StructParents index pointing into the ParentTree.",
                items_count=1
            ))
        else:
            results.append(self.create_result(
                status=CheckStatus.PASS,
                message="All pages with marked content possess valid /StructParents attributes.",
                evidence="Page StructParents validated.",
                items_count=0
            ))

        return results
