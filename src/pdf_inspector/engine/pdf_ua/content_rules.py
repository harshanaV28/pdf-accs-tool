"""
Content Rules (ISO 14289-1:2014, Clause 7.1 & Matterhorn Protocol Checkpoint 01)
Verifies that all real content is tagged within the structure tree or marked as an artifact,
and verifies marked content sequence integrity and ParentTree/MCID associations.
"""

from typing import List, Set, Dict
from ..rule_base import BaseRule
from ...core.models import PDFDocumentModel, CheckResult, CheckStatus, Severity


class TaggedPDFRule(BaseRule):
    rule_id = "PDFUA-CONTENT-001"
    name = "Tagged PDF"
    category = "Content"
    standard = "PDF/UA"
    severity = Severity.CRITICAL
    description = "The document must be marked as a Tagged PDF in the document Catalog dictionary (ISO 14289-1, Clause 7.1 / Matterhorn 01-001)."
    remediation_template = "In Acrobat Pro, open Accessibility tool and select 'Add Tags to Document', or check 'Document is tagged PDF' in authoring tool export settings."

    def evaluate(self, doc: PDFDocumentModel) -> List[CheckResult]:
        if doc.is_tagged and doc.structure_tree is not None:
            return [self.create_result(
                status=CheckStatus.PASS,
                message="Document is explicitly marked as a Tagged PDF with a structure tree.",
                evidence="Catalog /MarkInfo /Marked is true and /StructTreeRoot exists."
            )]

        return [self.create_result(
            status=CheckStatus.FAIL,
            message="Document is NOT a Tagged PDF. Assistive technologies cannot determine reading order or semantics.",
            evidence=f"is_tagged: {doc.is_tagged}, StructTreeRoot present: {doc.structure_tree is not None}",
            custom_severity=Severity.CRITICAL,
            custom_remediation="Tag the document using an accessible PDF authoring tool or Adobe Acrobat Pro's 'Autotag Document' feature."
        )]


class ContentTaggedRule(BaseRule):
    rule_id = "PDFUA-CONTENT-002"
    name = "Real Content Tagged"
    category = "Content"
    standard = "PDF/UA"
    severity = Severity.HIGH
    description = "All real content on each page must be tagged in the structure tree or marked as an Artifact (ISO 14289-1, Clause 7.1 / Matterhorn 01-002, 01-005)."
    remediation_template = "Inspect untagged elements in the PDF structure pane and tag them or mark them as background artifacts."

    def evaluate(self, doc: PDFDocumentModel) -> List[CheckResult]:
        results = []
        if not doc.is_tagged:
            return results

        # 1. Check pages with unmarked real content operations
        unmarked_pages: Dict[int, List[str]] = {}
        for p in doc.pages:
            unmarked_occs = [occ for occ in p.content_occurrences if occ.is_unmarked_real_content]
            if unmarked_occs or p.unmarked_real_content_count > 0:
                snippets = [occ.snippet for occ in unmarked_occs if occ.snippet]
                unmarked_pages[p.page_number] = snippets

        if unmarked_pages:
            for pg_num, snippets in list(unmarked_pages.items())[:5]:
                snip_str = f" Content: \"{snippets[0]}\"" if snippets else ""
                results.append(self.create_result(
                    status=CheckStatus.FAIL,
                    message=f"Page {pg_num} contains real content that is neither enclosed in marked content (/MCID) nor marked as an Artifact.",
                    evidence=f"Unmarked content on page {pg_num}.{snip_str}",
                    page=pg_num,
                    custom_severity=Severity.HIGH,
                    custom_remediation="Tag the unmarked content in the logical structure tree or mark it as an Artifact."
                ))
            if len(unmarked_pages) > 5:
                rem = len(unmarked_pages) - 5
                results.append(self.create_result(
                    status=CheckStatus.FAIL,
                    message=f"{rem} additional page(s) contain unmarked real content.",
                    evidence=f"Total pages with unmarked content: {len(unmarked_pages)}",
                    custom_severity=Severity.HIGH,
                    custom_remediation="Review and tag untagged content across pages."
                ))
        else:
            results.append(self.create_result(
                status=CheckStatus.PASS,
                message="All real content is enclosed in marked content tags or marked as Artifacts.",
                evidence=f"Validated content streams across all {doc.page_count} page(s)."
            ))

        return results


class TaggedInsideArtifactRule(BaseRule):
    rule_id = "PDFUA-CONTENT-004"
    name = "Tagged Content inside Artifact"
    category = "Content"
    standard = "PDF/UA"
    severity = Severity.HIGH
    description = "Tagged content (marked content sequences) must not be present inside an artifact (ISO 14289-1, Clause 7.1 / Matterhorn 01-004)."
    remediation_template = "Remove enclosing artifact tags around tagged content sequences in the page content stream."

    def evaluate(self, doc: PDFDocumentModel) -> List[CheckResult]:
        results = []
        if not doc.is_tagged:
            return results

        invalid_pages = []
        for p in doc.pages:
            if p.tagged_in_artifact_count > 0:
                invalid_pages.append((p.page_number, p.tagged_in_artifact_count))

        if invalid_pages:
            for pg_num, cnt in invalid_pages:
                results.append(self.create_result(
                    status=CheckStatus.FAIL,
                    message=f"Page {pg_num} has tagged content sequence(s) incorrectly nested inside an Artifact sequence.",
                    evidence=f"{cnt} tagged sequence(s) inside Artifact on page {pg_num}.",
                    page=pg_num,
                    custom_severity=Severity.HIGH,
                    custom_remediation="Move tagged content outside artifact blocks in page content stream."
                ))
        else:
            results.append(self.create_result(
                status=CheckStatus.PASS,
                message="No tagged content sequences are enclosed within artifact blocks.",
                evidence="Nesting of tagged content outside artifacts validated."
            ))

        return results


class MCIDStructureReferenceRule(BaseRule):
    rule_id = "PDFUA-CONTENT-005"
    name = "MCID Reference Integrity"
    category = "Content"
    standard = "PDF/UA"
    severity = Severity.HIGH
    description = "Every marked-content identifier (/MCID) in page content streams must be referenced by a structure element in the structure tree (ISO 14289-1, Clause 7.1 / Matterhorn 01-005)."
    remediation_template = "Associate orphan MCID marked content sequences with matching structure elements or mark them as Artifacts."

    def evaluate(self, doc: PDFDocumentModel) -> List[CheckResult]:
        results = []
        if not doc.is_tagged or not doc.structure_tree:
            return results

        # Collect all MCIDs referenced in the structure tree
        tree_mcids: Set[int] = set()
        all_nodes = doc.structure_tree.find_all_nodes()
        for node in all_nodes:
            for mcid in node.mcids:
                tree_mcids.add(mcid)

        # Check for orphan page MCIDs
        orphan_pages = []
        for p in doc.pages:
            orphans = [mcid for mcid in p.mcids if mcid not in tree_mcids]
            if orphans:
                orphan_pages.append((p.page_number, orphans))

        if orphan_pages:
            for pg_num, orphans in orphan_pages[:5]:
                results.append(self.create_result(
                    status=CheckStatus.FAIL,
                    message=f"Page {pg_num} contains marked content MCID(s) {orphans[:5]} not referenced by any structure element.",
                    evidence=f"Orphan MCIDs on page {pg_num}: {orphans}",
                    page=pg_num,
                    custom_severity=Severity.HIGH,
                    custom_remediation="Ensure every /MCID in page content streams is referenced in the structure tree."
                ))
        else:
            results.append(self.create_result(
                status=CheckStatus.PASS,
                message="All marked-content identifiers (MCIDs) are properly referenced in the structure tree.",
                evidence="MCID structure tree mapping verified."
            ))

        return results


class StructureMCIDExistenceRule(BaseRule):
    rule_id = "PDFUA-CONTENT-006"
    name = "Structure Element MCID Existence"
    category = "Content"
    standard = "PDF/UA"
    severity = Severity.HIGH
    description = "Every marked-content identifier (MCID) referenced by a structure element must exist on the associated page."
    remediation_template = "Ensure structure tree elements only reference MCIDs that actually exist in the page content stream."

    def evaluate(self, doc: PDFDocumentModel) -> List[CheckResult]:
        results = []
        if not doc.is_tagged or not doc.structure_tree:
            return results

        invalid_refs = []
        for node in doc.structure_tree.find_all_nodes():
            if not node.mcids:
                continue

            entries = getattr(node, "mcid_entries", [])
            if entries:
                for mcid, explicit_pg in entries:
                    pg_num = explicit_pg or node.page
                    if not pg_num:
                        continue
                    page = next((p for p in doc.pages if p.page_number == pg_num), None)
                    if not page:
                        continue
                    if mcid not in page.mcids:
                        invalid_refs.append((node, mcid, pg_num))
            else:
                pg_num = node.page
                if not pg_num:
                    continue
                page = next((p for p in doc.pages if p.page_number == pg_num), None)
                if not page:
                    continue
                for mcid in node.mcids:
                    if mcid not in page.mcids:
                        invalid_refs.append((node, mcid, pg_num))
                    
        if invalid_refs:
            for node, mcid, pg_num in invalid_refs[:5]:
                results.append(self.create_result(
                    status=CheckStatus.FAIL,
                    message=f"Structure element <{node.tag}> references MCID {mcid} which does not exist on page {pg_num}.",
                    evidence=f"Invalid MCID reference: {mcid} on page {pg_num}",
                    page=pg_num,
                    object_reference=f"<{node.tag}>",
                    custom_severity=Severity.HIGH,
                    custom_remediation="Recreate tags or repair structure tree references."
                ))
            if len(invalid_refs) > 5:
                rem = len(invalid_refs) - 5
                results.append(self.create_result(
                    status=CheckStatus.FAIL,
                    message=f"{rem} additional invalid MCID references found.",
                    evidence=f"Total invalid MCID refs: {len(invalid_refs)}",
                    custom_severity=Severity.HIGH,
                    custom_remediation="Rebuild document structure tree."
                ))
        else:
            results.append(self.create_result(
                status=CheckStatus.PASS,
                message="All MCIDs referenced by the structure tree exist on their respective pages.",
                evidence="Structure MCID references verified."
            ))

        return results


class NestedMarkedContentRule(BaseRule):
    rule_id = "PDFUA-CONTENT-007"
    name = "Nested Marked Content"
    category = "Content"
    standard = "PDF/UA"
    severity = Severity.HIGH
    description = "Marked content sequences must not be nested inside other marked content sequences."
    remediation_template = "Flatten nested marked content tags in the page content stream."

    def evaluate(self, doc: PDFDocumentModel) -> List[CheckResult]:
        results = []
        if not doc.is_tagged:
            return results

        nested_pages = []
        for p in doc.pages:
            nested_occs = [occ for occ in p.content_occurrences if occ.is_inside_tagged and occ.mcid is not None]
            if nested_occs:
                nested_pages.append((p.page_number, len(nested_occs)))

        if nested_pages:
            for pg_num, cnt in nested_pages[:5]:
                results.append(self.create_result(
                    status=CheckStatus.FAIL,
                    message=f"Page {pg_num} contains {cnt} nested marked content sequence(s).",
                    evidence=f"Nested marked content found on page {pg_num}.",
                    page=pg_num,
                    custom_severity=Severity.HIGH,
                    custom_remediation="Flatten marked content sequences."
                ))
            if len(nested_pages) > 5:
                rem = len(nested_pages) - 5
                results.append(self.create_result(
                    status=CheckStatus.FAIL,
                    message=f"{rem} additional page(s) contain nested marked content sequences.",
                    evidence=f"Total pages with nested sequences: {len(nested_pages)}",
                    custom_severity=Severity.HIGH,
                    custom_remediation="Review and fix nested content across pages."
                ))
        else:
            results.append(self.create_result(
                status=CheckStatus.PASS,
                message="No nested marked content sequences detected.",
                evidence="Marked content hierarchy validated."
            ))

        return results
