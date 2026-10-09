"""
Quality & Ergonomics Checks Suite
Audits structural quality, heading hierarchy leaps, container placement heuristics,
table layout regularity, and authoring best practices.
"""

from typing import List, Dict, Any, Set, Optional
import re
from ..rule_base import BaseRule
from ...core.models import PDFDocumentModel, CheckResult, CheckStatus, Severity, StructureNode


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


class TaggedContentPageBoundariesRule(BaseRule):
    """
    Validates that marked content sequences and structure elements are located within page boundaries.
    Matterhorn Protocol Checkpoint 01-006 / ISO 32000-1 §14.8.
    """
    rule_id = "QUAL-BOUND-001"
    name = "Tagged Content Page Boundaries"
    category = "Content Quality"
    standard = "Quality"
    severity = Severity.HIGH
    machine_testable = True
    description = "Tagged content and structure elements must reside within visible page boundaries (CropBox/MediaBox)."
    remediation_template = "Ensure all tagged content is placed within the printable and visible area of the page."

    def evaluate(self, doc: PDFDocumentModel) -> List[CheckResult]:
        results = []
        if not doc.is_tagged or not doc.pages:
            return results

        out_of_bounds = []
        for page in doc.pages:
            w = page.width
            h = page.height
            if w <= 0 or h <= 0:
                continue

            for mcid, bbox in page.mcid_bboxes.items():
                if bbox and len(bbox) == 4:
                    x0, y0, x1, y1 = bbox
                    # Element is strictly outside if right <= 0 or top <= 0 or left >= w or bottom >= h
                    if (x1 <= -0.5 or y1 <= -0.5 or x0 >= w + 0.5 or y0 >= h + 0.5) and (x1 > x0 and y1 > y0):
                        snippet = page.mcid_texts.get(mcid, "")
                        out_of_bounds.append((page.page_number, mcid, bbox, snippet))

        if out_of_bounds:
            for pg_num, mcid, bbox, snip in out_of_bounds[:5]:
                snip_str = f" Content: \"{snip[:50]}\"" if snip else ""
                results.append(self.create_result(
                    status=CheckStatus.WARNING,
                    message=f"Tagged content with MCID {mcid} on page {pg_num} lies entirely outside page boundaries {bbox}.{snip_str}",
                    evidence=f"Page {pg_num} bbox {bbox} exceeds page dimension",
                    page=pg_num,
                    bounding_box=bbox,
                    object_reference=f"MCID {mcid}",
                    custom_severity=Severity.HIGH,
                    custom_remediation="Adjust content coordinates so marked content resides within page boundaries."
                ))
            if len(out_of_bounds) > 5:
                rem = len(out_of_bounds) - 5
                results.append(self.create_result(
                    status=CheckStatus.WARNING,
                    message=f"{rem} additional tagged content elements lie outside page boundaries.",
                    evidence=f"Total out-of-bounds elements: {len(out_of_bounds)}",
                    custom_severity=Severity.HIGH,
                    custom_remediation="Inspect and relocate out-of-bounds elements into visible page coordinates."
                ))
        else:
            results.append(self.create_result(
                status=CheckStatus.PASS,
                message="All tagged content sequences are situated within visible page boundaries.",
                evidence=f"Page boundary checks verified across {len(doc.pages)} page(s)."
            ))

        return results


class TOCIContainsLinkRule(BaseRule):
    """
    Validates that TOCI elements contain Link elements.
    ISO 14289-1:2014, Clause 7.8 / Matterhorn Protocol Checkpoint 18-001.
    """
    rule_id = "QUAL-TOC-001"
    name = "TOCI Elements Contain Link Elements"
    category = "Heading & Navigation Quality"
    standard = "Quality"
    severity = Severity.HIGH
    machine_testable = True
    description = "Every Table of Contents Item (<TOCI>) element must contain a <Link> element."
    remediation_template = "Enclose table of contents entries in <Link> structure tags targeting corresponding document sections."

    def evaluate(self, doc: PDFDocumentModel) -> List[CheckResult]:
        results = []
        if not doc.structure_tree:
            return results

        all_nodes = doc.structure_tree.find_all_nodes()
        toci_nodes = [n for n in all_nodes if (n.standard_tag or "").upper() == "TOCI" or (n.tag or "").upper() == "TOCI"]

        if not toci_nodes:
            # Zero applicable TOCI elements -> returns [] (N/A / '-')
            return results

        invalid_toci = []
        valid_count = 0

        for toci in toci_nodes:
            descendants = toci.find_all_nodes()
            has_link = any(
                ((d.standard_tag or "").upper() == "LINK" or (d.tag or "").upper() == "LINK")
                for d in descendants if d != toci
            )
            if not has_link:
                invalid_toci.append(toci)
            else:
                valid_count += 1

        if invalid_toci:
            for toci in invalid_toci[:5]:
                results.append(self.create_result(
                    status=CheckStatus.FAIL,
                    message=f"<TOCI> element on page {toci.page or 1} does not contain a <Link> element (Matterhorn 18-001).",
                    evidence=f"TOCI element <{toci.tag} id='{toci.id}'> without child <Link>",
                    page=toci.page or 1,
                    object_reference=f"<{toci.tag} id='{toci.id}'>",
                    custom_severity=Severity.HIGH,
                    custom_remediation="Add a <Link> tag inside the <TOCI> element."
                ))
            if len(invalid_toci) > 5:
                rem = len(invalid_toci) - 5
                results.append(self.create_result(
                    status=CheckStatus.FAIL,
                    message=f"{rem} additional <TOCI> elements lack <Link> elements.",
                    evidence=f"Total invalid TOCI elements: {len(invalid_toci)}",
                    custom_severity=Severity.HIGH,
                    custom_remediation="Ensure all TOCI elements contain nested Link tags."
                ))

        if valid_count > 0:
            results.append(self.create_result(
                status=CheckStatus.PASS,
                message=f"{valid_count} <TOCI> element(s) contain valid <Link> elements.",
                evidence=f"TOCI link containment validated ({valid_count}/{len(toci_nodes)}).",
                items_count=valid_count
            ))

        return results


class TOCILinkDestinationRule(BaseRule):
    """
    Validates that Link elements inside TOCI elements target valid headings/destinations.
    ISO 14289-1:2014, Clause 7.8 / Matterhorn Protocol Checkpoint 18-002.
    """
    rule_id = "QUAL-TOC-002"
    name = "TOCI Elements Linked to Headings"
    category = "Heading & Navigation Quality"
    standard = "Quality"
    severity = Severity.MEDIUM
    machine_testable = True
    description = "Link elements inside <TOCI> elements must link to valid destinations or headings."
    remediation_template = "Set valid destination links for Table of Contents entries."

    def evaluate(self, doc: PDFDocumentModel) -> List[CheckResult]:
        results = []
        if not doc.structure_tree:
            return results

        all_nodes = doc.structure_tree.find_all_nodes()
        toci_nodes = [n for n in all_nodes if (n.standard_tag or "").upper() == "TOCI" or (n.tag or "").upper() == "TOCI"]

        if not toci_nodes:
            return results

        valid_count = 0
        invalid_links = []

        for toci in toci_nodes:
            descendants = toci.find_all_nodes()
            link_nodes = [d for d in descendants if d != toci and ((d.standard_tag or "").upper() == "LINK" or (d.tag or "").upper() == "LINK")]
            if not link_nodes:
                continue

            for lnk_node in link_nodes:
                matching_link = None
                for l in doc.links:
                    if l.page == (lnk_node.page or toci.page):
                        matching_link = l
                        break

                if matching_link and (matching_link.destination_page is not None or matching_link.uri or matching_link.is_internal):
                    valid_count += 1
                elif lnk_node.attributes.get("Dest") or lnk_node.attributes.get("URI") or lnk_node.obj_num:
                    valid_count += 1
                else:
                    invalid_links.append((toci, lnk_node))

        if invalid_links:
            for toci, lnk in invalid_links[:5]:
                results.append(self.create_result(
                    status=CheckStatus.WARNING,
                    message=f"Link element inside <TOCI> on page {toci.page or 1} lacks a resolvable target destination (Matterhorn 18-002).",
                    evidence=f"TOCI <{toci.tag}> Link <{lnk.tag}> unresolved destination",
                    page=toci.page or 1,
                    object_reference=f"<{lnk.tag} id='{lnk.id}'>",
                    custom_severity=Severity.MEDIUM,
                    custom_remediation="Assign a valid internal page or heading destination to the TOCI link."
                ))
        if valid_count > 0:
            results.append(self.create_result(
                status=CheckStatus.PASS,
                message=f"{valid_count} <TOCI> link(s) connect to valid destinations.",
                evidence=f"TOCI destination validation passed: {valid_count} item(s).",
                items_count=valid_count
            ))

        return results


class TextElementAltTextQualityRule(BaseRule):
    """
    Validates that text structure elements do not inappropriately use /Alt text attributes.
    Matterhorn Protocol Checkpoint 13-004 / ISO 14289-1 §7.1.
    """
    rule_id = "QUAL-TEXT-001"
    name = "Alternative Text on Text Elements"
    category = "Alternative Text Quality"
    standard = "Quality"
    severity = Severity.MEDIUM
    machine_testable = True
    description = "Text structure elements should not use /Alt attributes unless replacing non-standard characters."
    remediation_template = "Remove /Alt attributes from standard text tags (<P>, <Span>, <H1>-<H6>) and keep text directly in content streams."

    TEXT_TAGS = {"P", "SPAN", "H1", "H2", "H3", "H4", "H5", "H6", "LBODY", "TH", "TD", "QUOTE", "BIBENTRY"}

    def evaluate(self, doc: PDFDocumentModel) -> List[CheckResult]:
        results = []
        if not doc.structure_tree:
            return results

        all_nodes = doc.structure_tree.find_all_nodes()
        text_nodes = [n for n in all_nodes if (n.standard_tag or "").upper() in self.TEXT_TAGS]

        if not text_nodes:
            return results

        inappropriate_alt = []
        for node in text_nodes:
            if node.alt_text and node.alt_text.strip():
                # Check if it overrides readable text
                if node.text_content and len(node.text_content.strip()) > 1:
                    inappropriate_alt.append(node)

        if inappropriate_alt:
            for node in inappropriate_alt[:5]:
                results.append(self.create_result(
                    status=CheckStatus.WARNING,
                    message=f"Text element <{node.tag}> on page {node.page or 1} carries an /Alt attribute '{node.alt_text[:40]}' masking underlying text.",
                    evidence=f"<{node.tag}> on page {node.page} has /Alt: \"{node.alt_text[:50]}\"",
                    page=node.page or 1,
                    object_reference=f"<{node.tag} id='{node.id}'>",
                    custom_severity=Severity.MEDIUM,
                    custom_remediation="Remove /Alt attribute from text elements and use /ActualText or direct text content instead."
                ))
            if len(inappropriate_alt) > 5:
                rem = len(inappropriate_alt) - 5
                results.append(self.create_result(
                    status=CheckStatus.WARNING,
                    message=f"{rem} additional text element(s) carry masking /Alt attributes.",
                    evidence=f"Total text elements with /Alt: {len(inappropriate_alt)}",
                    custom_severity=Severity.MEDIUM,
                    custom_remediation="Review and clean /Alt attributes from text structure tags."
                ))
        else:
            results.append(self.create_result(
                status=CheckStatus.PASS,
                message="Text structure elements avoid inappropriate /Alt attributes.",
                evidence=f"Verified {len(text_nodes)} text structure elements."
            ))

        return results


class NoteReferencedQualityRule(BaseRule):
    """
    Validates that <Note> elements are referenced by a <Reference> element.
    ISO 14289-1:2014, Clause 7.7 / Matterhorn Protocol Checkpoint 17-001.
    """
    rule_id = "QUAL-NOTE-001"
    name = "Note Elements are Referenced"
    category = "Structure & Note Quality"
    standard = "Quality"
    severity = Severity.HIGH
    machine_testable = True
    description = "Every <Note> element must be referenced by a <Reference> structure element."
    remediation_template = "Add a <Reference> tag at the point of citation pointing to the corresponding <Note> element."

    def evaluate(self, doc: PDFDocumentModel) -> List[CheckResult]:
        results = []
        if not doc.structure_tree:
            return results

        all_nodes = doc.structure_tree.find_all_nodes()
        note_nodes = [n for n in all_nodes if (n.standard_tag or "").upper() == "NOTE" or (n.tag or "").upper() == "NOTE"]

        if not note_nodes:
            # Zero Note elements in document -> return [] (displays '-' in UI)
            return results

        ref_nodes = [n for n in all_nodes if (n.standard_tag or "").upper() == "REFERENCE" or (n.tag or "").upper() == "REFERENCE"]
        ref_ids = set()
        for r in ref_nodes:
            if r.attributes.get("Ref"):
                ref_ids.add(str(r.attributes.get("Ref")))
            if r.id:
                ref_ids.add(r.id)

        unreferenced = []
        valid_count = 0

        for note in note_nodes:
            is_ref = False
            if note.id in ref_ids or str(note.obj_num) in ref_ids:
                is_ref = True
            elif ref_nodes and any(r.page == note.page for r in ref_nodes):
                is_ref = True

            if is_ref:
                valid_count += 1
            else:
                unreferenced.append(note)

        if unreferenced:
            for note in unreferenced[:5]:
                results.append(self.create_result(
                    status=CheckStatus.WARNING,
                    message=f"<Note> element on page {note.page or 1} is not referenced by any <Reference> element (Matterhorn 17-001).",
                    evidence=f"Note <{note.tag} id='{note.id}'> on page {note.page}",
                    page=note.page or 1,
                    object_reference=f"<{note.tag} id='{note.id}'>",
                    custom_severity=Severity.HIGH,
                    custom_remediation="Add a <Reference> element referencing this <Note> ID."
                ))
            if len(unreferenced) > 5:
                rem = len(unreferenced) - 5
                results.append(self.create_result(
                    status=CheckStatus.WARNING,
                    message=f"{rem} additional <Note> elements lack corresponding <Reference> elements.",
                    evidence=f"Total unreferenced notes: {len(unreferenced)}",
                    custom_severity=Severity.HIGH,
                    custom_remediation="Ensure all footnotes/notes are referenced."
                ))

        if valid_count > 0:
            results.append(self.create_result(
                status=CheckStatus.PASS,
                message=f"{valid_count} <Note> element(s) are referenced by <Reference> elements.",
                evidence=f"Note references validated ({valid_count}/{len(note_nodes)}).",
                items_count=valid_count
            ))

        return results


class NoteContainsLabelQualityRule(BaseRule):
    """
    Validates that <Note> elements contain <Lbl> elements.
    ISO 14289-1:2014, Clause 7.7 / Matterhorn Protocol Checkpoint 17-002.
    """
    rule_id = "QUAL-NOTE-002"
    name = "Note Elements Contain Lbl Elements"
    category = "Structure & Note Quality"
    standard = "Quality"
    severity = Severity.MEDIUM
    machine_testable = True
    description = "A <Note> element should contain a <Lbl> element for note numbering or label identification."
    remediation_template = "Insert a <Lbl> element inside the <Note> element enclosing the footnote number or bullet."

    def evaluate(self, doc: PDFDocumentModel) -> List[CheckResult]:
        results = []
        if not doc.structure_tree:
            return results

        all_nodes = doc.structure_tree.find_all_nodes()
        note_nodes = [n for n in all_nodes if (n.standard_tag or "").upper() == "NOTE" or (n.tag or "").upper() == "NOTE"]

        if not note_nodes:
            return results

        missing_lbl = []
        valid_count = 0

        for note in note_nodes:
            has_lbl = any(
                ((c.standard_tag or "").upper() == "LBL" or (c.tag or "").upper() == "LBL")
                for c in note.children
            )
            if has_lbl:
                valid_count += 1
            else:
                missing_lbl.append(note)

        if missing_lbl:
            for note in missing_lbl[:5]:
                results.append(self.create_result(
                    status=CheckStatus.WARNING,
                    message=f"<Note> element on page {note.page or 1} does not contain a <Lbl> element (Matterhorn 17-002).",
                    evidence=f"Note <{note.tag} id='{note.id}'> missing <Lbl>",
                    page=note.page or 1,
                    object_reference=f"<{note.tag} id='{note.id}'>",
                    custom_severity=Severity.MEDIUM,
                    custom_remediation="Add a <Lbl> element inside the <Note> element."
                ))
            if len(missing_lbl) > 5:
                rem = len(missing_lbl) - 5
                results.append(self.create_result(
                    status=CheckStatus.WARNING,
                    message=f"{rem} additional <Note> elements lack <Lbl> elements.",
                    evidence=f"Total notes missing Lbl: {len(missing_lbl)}",
                    custom_severity=Severity.MEDIUM,
                    custom_remediation="Ensure Note elements contain Lbl tags."
                ))

        if valid_count > 0:
            results.append(self.create_result(
                status=CheckStatus.PASS,
                message=f"{valid_count} <Note> element(s) contain <Lbl> elements.",
                evidence=f"Note label validation passed ({valid_count}/{len(note_nodes)}).",
                items_count=valid_count
            ))

        return results


class ParagraphContainsNoteQualityRule(BaseRule):
    """
    Validates that inline <Note> elements are structured within paragraph or section contexts.
    ISO 14289-1:2014, Clause 7.7.
    """
    rule_id = "QUAL-NOTE-003"
    name = "P Elements Contain Note Elements"
    category = "Structure & Note Quality"
    standard = "Quality"
    severity = Severity.LOW
    machine_testable = True
    description = "Inline <Note> elements should be properly nested inside paragraph (<P>) or block container elements."
    remediation_template = "Place inline notes within paragraph (<P>) or section (<Sect>) elements rather than unparented at root."

    def evaluate(self, doc: PDFDocumentModel) -> List[CheckResult]:
        results = []
        if not doc.structure_tree:
            return results

        all_nodes = doc.structure_tree.find_all_nodes()
        note_nodes = [n for n in all_nodes if (n.standard_tag or "").upper() == "NOTE" or (n.tag or "").upper() == "NOTE"]

        if not note_nodes:
            return results

        root_child_ids = {c.id for c in doc.structure_tree.children}
        orphan_notes = []
        valid_count = 0

        for note in note_nodes:
            # If note is a direct child of StructTreeRoot without grouping container
            if note.id in root_child_ids:
                orphan_notes.append(note)
            else:
                valid_count += 1

        if orphan_notes:
            for note in orphan_notes[:5]:
                results.append(self.create_result(
                    status=CheckStatus.WARNING,
                    message=f"<Note> element on page {note.page or 1} is located directly at root outside paragraph context.",
                    evidence=f"Unparented Note <{note.tag} id='{note.id}'>",
                    page=note.page or 1,
                    object_reference=f"<{note.tag} id='{note.id}'>",
                    custom_severity=Severity.LOW,
                    custom_remediation="Nest the <Note> element within a <P> or <Sect> tag."
                ))
        if valid_count > 0:
            results.append(self.create_result(
                status=CheckStatus.PASS,
                message=f"{valid_count} <Note> element(s) are properly nested inside block containers.",
                evidence=f"Note nesting verified ({valid_count}/{len(note_nodes)}).",
                items_count=valid_count
            ))

        return results
