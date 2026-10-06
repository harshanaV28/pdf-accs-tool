"""
Quality & Ergonomics Checks Suite
Audits structural quality, heading hierarchy leaps, container placement heuristics,
table layout regularity, and authoring best practices.
"""

from typing import List, Dict, Any, Set
import re
from ..rule_base import BaseRule
from ...core.models import PDFDocumentModel, CheckResult, CheckStatus, Severity


class HeadingHierarchyQualityRule(BaseRule):
    rule_id = "QUAL-HEAD-001"
    name = "Heading Hierarchy Integrity"
    category = "Heading Structure"
    standard = "Quality"
    severity = Severity.MEDIUM
    machine_testable = False
    description = "Headings should follow a logical progressive hierarchy without skipping levels (e.g. H1 followed by H3)."
    remediation_template = "Adjust heading levels in your authoring tool so they increment smoothly without skipping levels."

    def evaluate(self, doc: PDFDocumentModel) -> List[CheckResult]:
        results = []
        if not doc.structure_tree:
            return results

        all_nodes = doc.structure_tree.find_all_nodes()
        heading_pattern = re.compile(r"^H([1-6])$", re.IGNORECASE)

        heading_list = []
        for n in all_nodes:
            std_tag = n.standard_tag or ""
            m = heading_pattern.match(std_tag)
            if m:
                level = int(m.group(1))
                heading_list.append((level, n.tag, n.page or 1, n.id))

        if not heading_list:
            results.append(self.create_result(
                status=CheckStatus.WARNING,
                message="No numbered heading tags (<H1>-<H6>) found in the document.",
                evidence="Total headings: 0",
                custom_remediation="Structure the document sections with <H1>, <H2>, etc.",
                confidence=0.8,
                manual_review_required=False
            ))
            return results

        # Check first heading
        first_level, first_tag, first_pg, first_id = heading_list[0]
        if first_level != 1:
            results.append(self.create_result(
                status=CheckStatus.WARNING,
                message=f"The first heading in the document is <{first_tag}> (level {first_level}) instead of <H1>.",
                evidence=f"First heading: <{first_tag}> on page {first_pg}",
                page=first_pg,
                object_reference=f"<{first_tag} id='{first_id}'>",
                custom_remediation="Start the document heading hierarchy with an <H1> main title.",
                confidence=0.85
            ))

        # Check for skipped levels
        skipped_jumps = []
        prev_level = 0
        for lvl, tag, pg, nid in heading_list:
            if prev_level > 0 and lvl > prev_level + 1:
                skipped_jumps.append((prev_level, lvl, tag, pg, nid))
            prev_level = lvl

        if skipped_jumps:
            for p_lvl, c_lvl, tag, pg, nid in skipped_jumps[:5]:
                results.append(self.create_result(
                    status=CheckStatus.WARNING,
                    message=f"Heading level skipped from H{p_lvl} directly to H{c_lvl} (<{tag}>) on page {pg}.",
                    evidence=f"Jump: H{p_lvl} -> H{c_lvl}",
                    page=pg,
                    object_reference=f"<{tag} id='{nid}'>",
                    custom_severity=Severity.MEDIUM,
                    custom_remediation=f"Demote <{tag}> to <H{p_lvl + 1}> or insert an intervening <H{p_lvl + 1}> section.",
                    confidence=0.85
                ))
        else:
            results.append(self.create_result(
                status=CheckStatus.PASS,
                message=f"Heading hierarchy is logically consistent across all {len(heading_list)} heading(s).",
                evidence=f"Headings validated: {len(heading_list)}"
            ))

        return results


class StructureQualityRule(BaseRule):
    rule_id = "QUAL-STRUCT-001"
    name = "Structural Quality & Ergonomics"
    category = "Structure Quality"
    standard = "Quality"
    severity = Severity.LOW
    machine_testable = False
    description = "Evaluates structural quality heuristics including empty container elements and placement semantics."
    remediation_template = "Review structure tags to ensure containers are appropriately populated and meaningful."

    def evaluate(self, doc: PDFDocumentModel) -> List[CheckResult]:
        results = []
        if not doc.structure_tree:
            return results

        all_nodes = [n for n in doc.structure_tree.find_all_nodes() if n.tag != "StructTreeRoot"]
        empty_containers = []

        for node in all_nodes:
            std_role = node.standard_tag or "Span"
            if std_role in ("Sect", "Div", "Part", "Art", "BlockQuote") and not node.children and not node.mcids:
                empty_containers.append((node.tag, node.page or 1))

        if empty_containers:
            for tag, pg in empty_containers[:3]:
                results.append(self.create_result(
                    status=CheckStatus.WARNING,
                    message=f"Empty structural container <{tag}> on page {pg} contains no child tags or content.",
                    evidence=f"Empty container <{tag}> on page {pg}",
                    page=pg,
                    object_reference=f"<{tag}>",
                    custom_remediation="Remove empty structural containers from the tag tree or assign content to them.",
                    confidence=0.8
                ))
        else:
            results.append(self.create_result(
                status=CheckStatus.PASS,
                message="Structural containers are well-populated without empty groupings.",
                evidence="Container quality validated."
            ))

        return results


class TableRegularityQualityRule(BaseRule):
    rule_id = "QUAL-TABLE-001"
    name = "Table Regularity & Symmetry"
    category = "Table Quality"
    standard = "Quality"
    severity = Severity.MEDIUM
    machine_testable = False
    description = "Data tables should maintain consistent column/row dimensions and avoid unannounced irregularity."
    remediation_template = "Ensure table cells align evenly and provide descriptive column and row headers."

    def evaluate(self, doc: PDFDocumentModel) -> List[CheckResult]:
        results = []
        if not doc.tables:
            return [self.create_result(
                status=CheckStatus.PASS,
                message="No data tables found in document.",
                evidence="Tables count: 0"
            )]

        irregular_tables = [t for t in doc.tables if not t.is_regular]
        if irregular_tables:
            for t in irregular_tables:
                results.append(self.create_result(
                    status=CheckStatus.WARNING,
                    message=f"Table on page {t.page} has irregular grid dimensions (possible unannounced spanned cells).",
                    evidence=f"Table {t.id}: {t.rows_count} rows, {t.cols_count} cols",
                    page=t.page,
                    object_reference=f"Table {t.id}",
                    custom_remediation="Verify column/row span attributes (ColSpan/RowSpan) on irregular table cells.",
                    confidence=0.8
                ))
        else:
            results.append(self.create_result(
                status=CheckStatus.PASS,
                message=f"All {len(doc.tables)} table(s) have regular matrix structures.",
                evidence="Table symmetry validated."
            ))

        return results


class LinkQualityRule(BaseRule):
    rule_id = "QUAL-LINK-001"
    name = "Meaningful Link Labels"
    category = "Link Quality"
    standard = "Quality"
    severity = Severity.LOW
    machine_testable = False
    description = "Hyperlink labels should be meaningful out of context to assist screen reader users."
    remediation_template = "Replace vague labels like 'click here' or bare URLs with clear descriptions of the destination."

    def evaluate(self, doc: PDFDocumentModel) -> List[CheckResult]:
        results = []
        if not doc.links:
            return [self.create_result(
                status=CheckStatus.PASS,
                message="No hyperlinks found in document.",
                evidence="Links count: 0"
            )]

        VAGUE_PATTERNS = re.compile(r"^(click\s+here|read\s+more|learn\s+more|more\s+info|more\s+details|link|here|more)(\.{0,3}|…)?$", re.IGNORECASE)
        vague_links = [l for l in doc.links if VAGUE_PATTERNS.match(l.text.strip())]
        if vague_links:
            for vl in vague_links[:5]:
                results.append(self.create_result(
                    status=CheckStatus.WARNING,
                    message=f"Ambiguous link label '{vl.text.strip()}' on page {vl.page} provides insufficient context out of context.",
                    evidence=f"Link text: '{vl.text.strip()}' targeting {vl.uri}",
                    page=vl.page,
                    bounding_box=vl.bbox,
                    custom_remediation="Change the link label to describe the specific destination or topic (e.g., 'Download Annual Report 2026').",
                    confidence=0.9
                ))

        bare_urls = [l for l in doc.links if l.text.strip().startswith(("http://", "https://", "www."))]
        if bare_urls:
            results.append(self.create_result(
                status=CheckStatus.WARNING,
                message=f"{len(bare_urls)} link(s) use raw URL strings as their anchor text.",
                evidence=f"Sample raw URL: '{bare_urls[0].text[:40]}...'",
                page=bare_urls[0].page,
                bounding_box=bare_urls[0].bbox,
                custom_remediation="Provide human-readable link text instead of full URL strings.",
                confidence=0.9
            ))

        if not vague_links and not bare_urls:
            results.append(self.create_result(
                status=CheckStatus.PASS,
                message="All hyperlink anchor labels appear meaningful and avoid bare URLs.",
                evidence="Link labels checked."
            ))

        return results
