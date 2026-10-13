"""
List Structure Rules (ISO 14289-1, Clause 7.4 & Matterhorn Protocol Checkpoint 14-001)
Validates strict list structure hierarchy: <L> contains <LI>, which contains <Lbl> and/or <LBody>.
"""

from typing import List
from ..rule_base import BaseRule
from ...core.models import PDFDocumentModel, CheckResult, CheckStatus, Severity


class ListStructureHierarchyRule(BaseRule):
    rule_id = "PDFUA-LIST-001"
    name = "List Structure Hierarchy"
    category = "Structure elements"
    standard = "PDF/UA"
    severity = Severity.HIGH
    description = "A list (<L>) must contain only list items (<LI>), and each <LI> must contain only list label (<Lbl>) and/or list body (<LBody>) elements."
    remediation_template = "In Acrobat Pro Tags panel, re-nest list elements so that L contains LI, and LI contains Lbl and LBody."

    def evaluate(self, doc: PDFDocumentModel) -> List[CheckResult]:
        results = []
        if not doc.lists:
            return [self.create_result(
                status=CheckStatus.PASS,
                message="No lists detected in document (or document contains no list structures).",
                evidence="List count: 0",
                items_count=0
            )]

        invalid_lists = [l for l in doc.lists if not l.is_valid_structure]
        passed_lists = [l for l in doc.lists if l.is_valid_structure]
        fail_items_count = 0 if doc.structure_tree else 1
        if invalid_lists:
            for l in invalid_lists[:5]:
                results.append(self.create_result(
                    status=CheckStatus.FAIL,
                    message=f"List on page {l.page} has an invalid structural hierarchy (violates L -> LI -> Lbl/LBody nesting).",
                    evidence=f"List {l.id} with {l.items_count} item(s) on page {l.page}",
                    page=l.page,
                    object_reference=f"List {l.id}",
                    custom_severity=Severity.HIGH,
                    custom_remediation="Restructure the list so each item is enclosed in an <LI> containing <Lbl> (bullet/number) and <LBody> (text).",
                    items_count=fail_items_count
                ))
            if len(invalid_lists) > 5:
                rem = len(invalid_lists) - 5
                results.append(self.create_result(
                    status=CheckStatus.FAIL,
                    message=f"{rem} additional list(s) have invalid structural hierarchies.",
                    evidence=f"Invalid list count: {len(invalid_lists)}",
                    custom_severity=Severity.HIGH,
                    custom_remediation="Restructure lists according to ISO 14289-1 clause 7.4.",
                    items_count=rem * fail_items_count
                ))
            if passed_lists:
                results.append(self.create_result(
                    status=CheckStatus.PASS,
                    message=f"{len(passed_lists)} of {len(doc.lists)} list(s) conform to ISO standard structural list hierarchies.",
                    evidence=f"Valid lists: {len(passed_lists)}/{len(doc.lists)}",
                    items_count=0
                ))
        else:
            results.append(self.create_result(
                status=CheckStatus.PASS,
                message=f"All {len(doc.lists)} list(s) conform to ISO standard structural list hierarchies.",
                evidence=f"Total valid lists: {len(doc.lists)}"
            ))

        return results
