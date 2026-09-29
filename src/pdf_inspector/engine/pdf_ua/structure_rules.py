"""
Structure Elements & Tree Rules (ISO 14289-1, Clause 7.1 & 7.4)
Validates logical tag hierarchy, proper nesting of lists/tables/headings, and structure tree integrity.
"""

from typing import List
from ..rule_base import BaseRule
from ...core.models import PDFDocumentModel, CheckResult, CheckStatus, Severity, StructureNode


class StructureTreeIntegrityRule(BaseRule):
    rule_id = "PDFUA-TREE-001"
    name = "Structure Tree Root"
    category = "Structure tree"
    standard = "PDF/UA"
    severity = Severity.CRITICAL
    description = "The structure tree must have a valid StructTreeRoot with a top-level Document or Part container."
    remediation_template = "Ensure the root of the structure tree is tagged as Document or Part in Acrobat Pro Tag Tree."

    def evaluate(self, doc: PDFDocumentModel) -> List[CheckResult]:
        results = []
        if not doc.structure_tree:
            results.append(self.create_result(
                status=CheckStatus.FAIL,
                message="No StructTreeRoot exists in the document.",
                evidence="StructTreeRoot is missing from Catalog.",
                custom_severity=Severity.CRITICAL,
                custom_remediation="Add structural tags to the document using an accessible PDF creator or Acrobat Pro."
            ))
            return results

        root_children = doc.structure_tree.children
        if not root_children:
            results.append(self.create_result(
                status=CheckStatus.FAIL,
                message="StructTreeRoot contains no children (empty structure tree).",
                evidence="StructTreeRoot /K is empty.",
                custom_remediation="Ensure tags contain document content."
            ))
        else:
            first_tags = [c.standard_tag.upper() for c in root_children]
            if any(t in ("DOCUMENT", "PART", "SECT", "ARTICLE") for t in first_tags):
                results.append(self.create_result(
                    status=CheckStatus.PASS,
                    message="Structure tree has a compliant top-level structural container.",
                    evidence=f"Top-level tag(s): {first_tags}"
                ))
            else:
                results.append(self.create_result(
                    status=CheckStatus.WARNING,
                    message=f"Structure tree root should ideally start with <Document> or <Part>, found: {first_tags}",
                    evidence=f"Root tags: {first_tags}",
                    custom_remediation="Wrap top-level contents inside a <Document> tag."
                ))

        return results


class StructureNestingRule(BaseRule):
    rule_id = "PDFUA-STRUCT-001"
    name = "Structure Elements Nesting"
    category = "Structure Elements"
    standard = "PDF/UA"
    severity = Severity.HIGH
    description = "Structural elements must be nested logically according to ISO 32000-1 (e.g. TR inside Table, LI inside L)."
    remediation_template = "Fix nesting in the Tag Tree so lists contain LI, tables contain TR, and TR contains TH/TD."

    def evaluate(self, doc: PDFDocumentModel) -> List[CheckResult]:
        results = []
        if not doc.structure_tree:
            return results

        all_nodes = doc.structure_tree.find_all_nodes()
        nesting_errors = []

        for node in all_nodes:
            tag = node.standard_tag.upper()

            # Check Table children
            if tag == "TABLE":
                for child in node.children:
                    ctag = child.standard_tag.upper()
                    if ctag not in ("TR", "THEAD", "TBODY", "TFOOT", "CAPTION"):
                        nesting_errors.append((f"<Table> should only contain TR/Caption/Thead/Tbody, found <{child.tag}>", node.page or child.page or 1, f"Table > {child.tag}"))

            # Check TR children
            elif tag == "TR":
                for child in node.children:
                    ctag = child.standard_tag.upper()
                    if ctag not in ("TH", "TD"):
                        nesting_errors.append((f"<TR> should only contain TH or TD, found <{child.tag}>", node.page or child.page or 1, f"TR > {child.tag}"))

            # Check List children
            elif tag == "L":
                for child in node.children:
                    ctag = child.standard_tag.upper()
                    if ctag not in ("LI", "CAPTION"):
                        nesting_errors.append((f"<L> (List) should only contain LI, found <{child.tag}>", node.page or child.page or 1, f"L > {child.tag}"))

        if nesting_errors:
            for msg, pg, obj_ref in nesting_errors[:5]:  # Report first 5
                results.append(self.create_result(
                    status=CheckStatus.FAIL,
                    message=msg,
                    evidence=f"Invalid child relationship in structure tree: {obj_ref}",
                    page=pg,
                    object_reference=obj_ref,
                    custom_remediation="Rearrange tags in Acrobat Pro Tag Tree so structural parent-child rules are satisfied."
                ))
        else:
            results.append(self.create_result(
                status=CheckStatus.PASS,
                message="All structural lists, tables, and container elements conform to standard nesting rules.",
                evidence="Nesting validation passed."
            ))

        return results


class EmptyStructureElementsRule(BaseRule):
    rule_id = "PDFUA-STRUCT-002"
    name = "Empty Structure Elements"
    category = "Structure Elements"
    standard = "PDF/UA"
    severity = Severity.LOW
    description = "Structure elements should not be empty unless they serve as structural grouping containers."
    remediation_template = "Delete empty tags or attach content to them."

    def evaluate(self, doc: PDFDocumentModel) -> List[CheckResult]:
        results = []
        if not doc.structure_tree:
            return results

        all_nodes = doc.structure_tree.find_all_nodes()
        leaf_empty = []

        for node in all_nodes:
            tag = node.standard_tag.upper()
            # Non-grouping leaf node that has no children, no MCID, and no alt text
            if tag in ("P", "H1", "H2", "H3", "H4", "H5", "H6", "SPAN", "LINK") and not node.children and not node.mcids and not node.alt_text:
                leaf_empty.append((node.tag, node.page or 1))

        if leaf_empty:
            for tag, pg in leaf_empty[:5]:
                results.append(self.create_result(
                    status=CheckStatus.WARNING,
                    message=f"Empty structure element <{tag}> has no child tags or marked content.",
                    evidence=f"<{tag}> on page {pg} is empty.",
                    page=pg,
                    object_reference=f"<{tag}>",
                    custom_remediation="Remove empty tags in the tag tree."
                ))
        else:
            results.append(self.create_result(
                status=CheckStatus.PASS,
                message="No superfluous empty leaf structure tags detected.",
                evidence="Structure completeness validated."
            ))

        return results
