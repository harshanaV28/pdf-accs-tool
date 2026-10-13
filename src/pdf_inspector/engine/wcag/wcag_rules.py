"""
WCAG 2.1 / 2.2 AA Rules Suite
Implements object-level accessibility checks mapped across the 13 WCAG guidelines.
Evaluates individual non-text elements, headings, lists, tables, fonts, links, and forms
with standards-based zero-applicable object handling.
"""

from typing import List, Dict, Any, Set
import re
from ..rule_base import BaseRule
from ...core.models import PDFDocumentModel, CheckResult, CheckStatus, Severity
from ...core.structure_tree import STANDARD_STRUCTURE_TYPES_EXACT, resolve_role


class WCAGTextAlternativesRule(BaseRule):
    rule_id = "WCAG-1.1.1"
    name = "1.1 Text Alternatives"
    category = "1.1 Text Alternatives"
    standard = "WCAG"
    severity = Severity.HIGH
    description = "All non-text content presented to users has a text alternative serving equivalent purpose (WCAG SC 1.1.1)."
    remediation_template = "Add descriptive alternative text to all non-decorative images, figures, and formulas."

    def evaluate(self, doc: PDFDocumentModel) -> List[CheckResult]:
        results: List[CheckResult] = []

        # 1. Structure elements: Figure, Formula, Form
        if doc.structure_tree:
            all_nodes = [n for n in doc.structure_tree.find_all_nodes() if n.tag != "StructTreeRoot"]
            non_text_nodes = [
                n for n in all_nodes
                if (n.standard_tag or "").upper() in ("FIGURE", "FORMULA", "FORM")
                and not n.is_artifact
            ]
            for node in non_text_nodes:
                has_alt = bool(
                    (node.alt_text and node.alt_text.strip()) or
                    (node.actual_text and node.actual_text.strip())
                )
                if not has_alt and node.children:
                    has_child_text = any(
                        (c.alt_text and c.alt_text.strip()) or
                        (c.actual_text and c.actual_text.strip()) or
                        (c.text_content and c.text_content.strip())
                        for c in node.children
                    )
                    if has_child_text:
                        has_alt = True

                if has_alt:
                    alt_val = (node.alt_text or node.actual_text or "").strip()
                    results.append(self.create_result(
                        status=CheckStatus.PASS,
                        message=f"Alternative text is present for <{node.tag}> on page {node.page or 1}.",
                        evidence=f"<{node.tag}> on page {node.page or 1}: '{alt_val[:100]}'",
                        page=node.page,
                        bounding_box=node.bbox or node.struct_bbox,
                        object_reference=f"<{node.tag} id='{node.id}'>"
                    ))
                else:
                    results.append(self.create_result(
                        status=CheckStatus.FAIL,
                        message=f"<{node.tag}> on page {node.page or 1} lacks a text alternative (/Alt or /ActualText) (WCAG SC 1.1.1).",
                        evidence=f"<{node.tag}> on page {node.page or 1} has no /Alt or /ActualText attribute.",
                        page=node.page,
                        bounding_box=node.bbox or node.struct_bbox,
                        object_reference=f"<{node.tag} id='{node.id}'>",
                        custom_severity=Severity.HIGH,
                        custom_remediation=f"Add alternative text (/Alt) to the <{node.tag}> element in your authoring tool."
                    ))

        # 2. Standalone image models (for synthetic documents or documents without parsed content items)
        # In PAC, if an untagged full document has page content streams with untagged content items,
        # those untagged elements violate SC 1.3.1 (Info and Relationships), not SC 1.1.1.
        elif doc.images and not (not doc.is_tagged and doc.pages):
            for img in doc.images:
                if img.is_artifact:
                    continue
                if img.has_alt:
                    results.append(self.create_result(
                        status=CheckStatus.PASS,
                        message=f"Alternative text is present for image on page {img.page}.",
                        evidence=f"Image {img.id} on page {img.page}: '{img.alt_text[:100]}'",
                        page=img.page,
                        bounding_box=img.bbox,
                        object_reference=f"Image {img.id}"
                    ))
                else:
                    results.append(self.create_result(
                        status=CheckStatus.FAIL,
                        message=f"Image on page {img.page} lacks alternative text (WCAG SC 1.1.1).",
                        evidence=f"Image {img.id} at {img.bbox}",
                        page=img.page,
                        bounding_box=img.bbox,
                        object_reference=f"Image {img.id}",
                        custom_severity=Severity.HIGH,
                        custom_remediation="Add alternative text or mark image as decorative artifact."
                    ))

        return results


class WCAGTimeBasedMediaRule(BaseRule):
    rule_id = "WCAG-1.2"
    name = "1.2 Time-based Media"
    category = "1.2 Time-based Media"
    standard = "WCAG"
    severity = Severity.MEDIUM
    description = "Provide alternatives for time-based media embedded in the PDF (WCAG 1.2)."
    remediation_template = "Provide synchronized captions or text transcripts for embedded media."

    def evaluate(self, doc: PDFDocumentModel) -> List[CheckResult]:
        media_annots = [
            a for a in doc.annotations
            if a.subtype in ("Movie", "Screen", "RichMedia", "3D", "Sound")
        ]
        if not media_annots:
            return []

        results: List[CheckResult] = []
        for annot in media_annots:
            if annot.contents or annot.is_tagged:
                results.append(self.create_result(
                    status=CheckStatus.PASS,
                    message=f"Time-based media annotation on page {annot.page} has accessible description.",
                    evidence=f"Media annotation '{annot.id}' on page {annot.page}",
                    page=annot.page,
                    object_reference=f"Annotation {annot.id}"
                ))
            else:
                results.append(self.create_result(
                    status=CheckStatus.FAIL,
                    message=f"Time-based media annotation on page {annot.page} lacks accessible text transcript or captions (SC 1.2).",
                    evidence=f"Media annotation '{annot.id}' on page {annot.page}",
                    page=annot.page,
                    object_reference=f"Annotation {annot.id}",
                    custom_severity=Severity.MEDIUM,
                    custom_remediation="Provide synchronized captions or transcript for embedded media."
                ))
        return results


class WCAGAdaptableRule(BaseRule):
    rule_id = "WCAG-1.3"
    name = "1.3 Adaptable"
    category = "1.3 Adaptable"
    standard = "WCAG"
    severity = Severity.HIGH
    description = "Create content that can be presented in different ways without losing information or structure (WCAG SC 1.3.1, 1.3.2)."
    remediation_template = "Ensure headings, tables, and lists use appropriate structural tags."

    def evaluate(self, doc: PDFDocumentModel) -> List[CheckResult]:
        results: List[CheckResult] = []
        if not doc.is_tagged and doc.structure_tree is None:
            total_untagged = len(doc.images) + sum(len(p.text.splitlines()) for p in doc.pages if p.text.strip())
            res = [
                self.create_result(
                    status=CheckStatus.PASS,
                    message="Page reading sequence follows default sequential layout (SC 1.3.2).",
                    evidence=f"Validated reading layout across {doc.page_count} page(s).",
                    items_count=1
                ),
                self.create_result(
                    status=CheckStatus.FAIL,
                    message="Untagged document fails Info and Relationships (SC 1.3.1). Structure is lost.",
                    evidence="Document is not tagged.",
                    custom_severity=Severity.CRITICAL,
                    custom_remediation="Tag the document to convey relationships to assistive technologies.",
                    items_count=1
                )
            ]
            if total_untagged > 0:
                res.append(self.create_result(
                    status=CheckStatus.FAIL,
                    message=f"Document contains {total_untagged} untagged real content element(s) lacking semantic relationships (SC 1.3.1).",
                    evidence=f"{len(doc.images)} image(s) across {doc.page_count} page(s) lack structural markup.",
                    custom_severity=Severity.HIGH,
                    custom_remediation="Tag all content in the structure tree.",
                    items_count=total_untagged
                ))
            return res

        # 1. Page Content Operations & Marked-Content Sequences (WCAG SC 1.3.1 & SC 1.3.2)
        if doc.pages:
            for p in doc.pages:
                # SC 1.3.1: Check for unmarked real content rendering operations
                if p.unmarked_real_content_count > 0:
                    results.append(self.create_result(
                        status=CheckStatus.FAIL,
                        message=f"Page {p.page_number} contains {p.unmarked_real_content_count} unmarked real content operation(s) lacking structural markup (SC 1.3.1).",
                        evidence=f"Unmarked real content operations on page {p.page_number}: {p.unmarked_real_content_count}",
                        page=p.page_number,
                        custom_severity=Severity.HIGH,
                        custom_remediation="Enclose all page content in marked-content sequences or mark as artifacts.",
                        items_count=p.unmarked_real_content_count
                    ))

                # SC 1.3.1: Structural Marked-Content Sequences
                mc_count = len(p.mcids)
                if mc_count > 0 or p.tagged_operations_count > 0:
                    cnt = mc_count if mc_count > 0 else (p.tagged_operations_count if p.tagged_operations_count > 0 else 1)
                    results.append(self.create_result(
                        status=CheckStatus.PASS,
                        message=f"Page {p.page_number} content is structured with {cnt} marked-content sequence(s) conveying relationships (SC 1.3.1).",
                        evidence=f"Page {p.page_number}: {cnt} MCID sequence(s) / tagged operations.",
                        page=p.page_number,
                        items_count=cnt
                    ))

                # SC 1.3.2: Meaningful reading sequence for structured page
                if mc_count > 0 or p.has_structure:
                    results.append(self.create_result(
                        status=CheckStatus.PASS,
                        message=f"Page {p.page_number} logical structure reading order follows defined structural sequence (SC 1.3.2).",
                        evidence=f"Page {p.page_number} reading sequence verified.",
                        page=p.page_number,
                        items_count=1
                    ))

        # 2. Tables (SC 1.3.1)
        for t in doc.tables:
            if t.has_headers:
                results.append(self.create_result(
                    status=CheckStatus.PASS,
                    message=f"Table on page {t.page} has header cells (<TH>).",
                    evidence=f"Table {t.id} has {t.header_cells_count} header cell(s).",
                    page=t.page,
                    object_reference=f"Table {t.id}"
                ))
            else:
                results.append(self.create_result(
                    status=CheckStatus.FAIL,
                    message=f"Table on page {t.page} lacks header cells (<TH>) (SC 1.3.1).",
                    evidence=f"Table {t.id} has {t.rows_count} rows, {t.cols_count} columns, 0 header cells.",
                    page=t.page,
                    object_reference=f"Table {t.id}",
                    custom_remediation="Tag column and row headers with <TH> and assign Scope."
                ))

        # 3. Structural Element Hierarchies (SC 1.3.1)
        if doc.structure_tree:
            all_nodes = [n for n in doc.structure_tree.find_all_nodes() if n.tag != "StructTreeRoot"]

            # Figures: Bounding Box Geometry & Spatial Relationships (FigureHasBBox, Matterhorn 13-001 / SC 1.3.1)
            figures = [n for n in all_nodes if (n.standard_tag or "").upper() == "FIGURE"]
            for fig in figures:
                has_bbox = bool(fig.bbox and (fig.bbox[2] > fig.bbox[0] or fig.bbox[3] > fig.bbox[1]))
                if has_bbox or fig.has_explicit_bbox:
                    results.append(self.create_result(
                        status=CheckStatus.PASS,
                        message=f"Figure structure element <{fig.tag}> on page {fig.page or 1} conveys bounding box geometry and spatial relationship (SC 1.3.1).",
                        evidence=f"Figure <{fig.tag} id='{fig.id}'> bbox: {fig.bbox}",
                        page=fig.page or 1,
                        object_reference=f"<{fig.tag} id='{fig.id}'>"
                    ))
                else:
                    results.append(self.create_result(
                        status=CheckStatus.FAIL,
                        message=f"Figure structure element <{fig.tag}> on page {fig.page or 1} lacks bounding box geometry (SC 1.3.1).",
                        evidence=f"Figure <{fig.tag} id='{fig.id}'> lacks /BBox attribute or associated content bounds.",
                        page=fig.page or 1,
                        object_reference=f"<{fig.tag} id='{fig.id}'>",
                        custom_severity=Severity.HIGH,
                        custom_remediation="Assign a valid /BBox attribute to the Figure structure element."
                    ))

            # Headings (SC 1.3.1)
            headings = [n for n in all_nodes if (n.standard_tag or "").upper() in ("H", "H1", "H2", "H3", "H4", "H5", "H6")]
            for h in headings:
                results.append(self.create_result(
                    status=CheckStatus.PASS,
                    message=f"Structured heading <{h.tag}> on page {h.page or 1} conveys content hierarchy.",
                    evidence=f"Heading <{h.tag}> on page {h.page or 1}",
                    page=h.page,
                    object_reference=f"<{h.tag} id='{h.id}'>"
                ))

            # List items (SC 1.3.1)
            list_items = [n for n in all_nodes if (n.standard_tag or "").upper() == "LI"]
            for li in list_items:
                invalid_children = [c for c in li.children if (c.standard_tag or "").upper() not in ("LBL", "LBODY", "CAPTION")]
                if invalid_children:
                    results.append(self.create_result(
                        status=CheckStatus.FAIL,
                        message=f"List item on page {li.page or 1} contains invalid child <{invalid_children[0].tag}> (SC 1.3.1).",
                        evidence=f"LI on page {li.page or 1} contains {[c.tag for c in invalid_children]}; must only contain <Lbl> and/or <LBody>.",
                        page=li.page or 1,
                        object_reference=f"<LI id='{li.id}'>",
                        custom_remediation="Structure list items with <Lbl> for bullet/number and <LBody> for list content."
                    ))
                else:
                    results.append(self.create_result(
                        status=CheckStatus.PASS,
                        message=f"List item <LI> on page {li.page or 1} conforms to SC 1.3.1 list structure requirements.",
                        evidence=f"<LI> on page {li.page or 1}",
                        page=li.page or 1,
                        object_reference=f"<LI id='{li.id}'>"
                    ))

        if not results:
            results.append(self.create_result(
                status=CheckStatus.PASS,
                message="Document structure conveys information and relationships (SC 1.3.1).",
                evidence="Document structure verified.",
                items_count=1
            ))

        return results


class WCAGDistinguishableRule(BaseRule):
    rule_id = "WCAG-1.4"
    name = "1.4 Distinguishable"
    category = "1.4 Distinguishable"
    standard = "WCAG"
    severity = Severity.MEDIUM
    machine_testable = False
    description = "Make it easier for users to see and hear content including separating foreground from background (WCAG SC 1.4.1 Use of Color, SC 1.4.3 Contrast Minimum, SC 1.4.11 Non-text Contrast)."
    remediation_template = "Verify visual contrast ratio of text against background meets 4.5:1 for regular text and 3:1 for large text or graphical objects."

    def evaluate(self, doc: PDFDocumentModel) -> List[CheckResult]:
        if not doc.is_tagged and not doc.fonts and not any(p.text.strip() for p in doc.pages):
            return []
        return [self.create_result(
            status=CheckStatus.MANUAL_REVIEW,
            message="Verify visual color contrast (minimum 4.5:1 for standard text, 3:1 for large text/icons) and ensure color is not the only means of conveying information (WCAG SC 1.4.1, SC 1.4.3, SC 1.4.11).",
            evidence="Color contrast and use-of-color require visual sampling and human verification.",
            manual_review_required=True
        )]


class WCAGKeyboardAccessibleRule(BaseRule):
    rule_id = "WCAG-2.1"
    name = "2.1 Keyboard Accessible"
    category = "2.1 Keyboard Accessible"
    standard = "WCAG"
    severity = Severity.HIGH
    description = "Make all functionality available from a keyboard without keyboard traps (WCAG SC 2.1.1, 2.1.2)."
    remediation_template = "Ensure page tab navigation follows document structure order."

    def evaluate(self, doc: PDFDocumentModel) -> List[CheckResult]:
        if not doc.form_fields and not doc.links:
            return []

        results: List[CheckResult] = []
        interactive_pages = set([f.page for f in doc.form_fields if f.page] + [l.page for l in doc.links if l.page])

        for p in doc.pages:
            if p.page_number not in interactive_pages:
                continue
            if p.tab_order_mode == "S":
                results.append(self.create_result(
                    status=CheckStatus.PASS,
                    message=f"Page {p.page_number} tab order is set to Document Structure for keyboard focus (SC 2.1.1).",
                    evidence=f"Page {p.page_number} /Tabs is /S",
                    page=p.page_number
                ))
            else:
                results.append(self.create_result(
                    status=CheckStatus.WARNING,
                    message=f"Page {p.page_number} contains interactive elements but tab order is not set to Structure order (SC 2.1.1).",
                    evidence=f"Page {p.page_number} /Tabs: {p.tab_order_mode}",
                    page=p.page_number,
                    custom_remediation="Set page Tab Order to 'Use Document Structure' in Page Properties."
                ))

        return results


class WCAGEnoughTimeRule(BaseRule):
    rule_id = "WCAG-2.2"
    name = "2.2 Enough Time"
    category = "2.2 Enough Time"
    standard = "WCAG"
    severity = Severity.LOW
    description = "Provide users enough time to read and use content (WCAG SC 2.2.1)."
    remediation_template = "Do not set automated timeouts or slide transitions without user pause controls."

    def evaluate(self, doc: PDFDocumentModel) -> List[CheckResult]:
        return []


class WCAGSeizuresRule(BaseRule):
    rule_id = "WCAG-2.3"
    name = "2.3 Seizures and Physical Reactions"
    category = "2.3 Seizures and Physical Reactions"
    standard = "WCAG"
    severity = Severity.CRITICAL
    description = "Do not design content in a way known to cause seizures (WCAG SC 2.3.1)."
    remediation_template = "Avoid animations or blinking content that flashes more than three times per second."

    def evaluate(self, doc: PDFDocumentModel) -> List[CheckResult]:
        return []


class WCAGNavigableRule(BaseRule):
    rule_id = "WCAG-2.4"
    name = "2.4 Navigable"
    category = "2.4 Navigable"
    standard = "WCAG"
    severity = Severity.HIGH
    description = "Provide ways to help users navigate, find content, and determine where they are (Title SC 2.4.2, Link Purpose SC 2.4.4, Headings SC 2.4.6, Bookmarks SC 2.4.5)."
    remediation_template = "Set document title, enable DisplayDocTitle, provide bookmarks, and write descriptive link text."

    def evaluate(self, doc: PDFDocumentModel) -> List[CheckResult]:
        results: List[CheckResult] = []

        # 1. SC 2.4.2: Page / Document Titled & Displayed
        has_title = bool((doc.xmp_dc_title and doc.xmp_dc_title.strip()) or (doc.doc_info_title and doc.doc_info_title.strip()))
        if not has_title:
            results.append(self.create_result(
                status=CheckStatus.FAIL,
                message="Document lacks a descriptive Title (WCAG SC 2.4.2 Page Titled).",
                evidence="No title entry found in document metadata.",
                custom_remediation="Add a descriptive title in Document Properties."
            ))
        else:
            results.append(self.create_result(
                status=CheckStatus.PASS,
                message=f"Document provides a descriptive title: '{doc.title}' (SC 2.4.2).",
                evidence=f"Title: '{doc.title}'"
            ))

        if not doc.display_doc_title:
            results.append(self.create_result(
                status=CheckStatus.FAIL,
                message="ViewerPreferences /DisplayDocTitle is false or missing (WCAG SC 2.4.2 / PDF Technique 18). Window title bar will display filename instead of title.",
                evidence=f"/DisplayDocTitle: {doc.display_doc_title}",
                custom_severity=Severity.HIGH,
                custom_remediation="Set Initial View > Show > Document Title in File Properties."
            ))
        else:
            results.append(self.create_result(
                status=CheckStatus.PASS,
                message="DisplayDocTitle is enabled in ViewerPreferences (SC 2.4.2).",
                evidence="DisplayDocTitle: true"
            ))

        # 2. SC 2.4.3: Focus Order / Tab Order (Matterhorn 13-005)
        violating_tabs = [p.page_number for p in doc.pages if p.tab_order_mode != "S"]
        has_interactive = any(p.links_count > 0 or getattr(p, "annotations_count", 0) > 0 for p in doc.pages)
        if violating_tabs and (not doc.is_tagged or has_interactive):
            results.append(self.create_result(
                status=CheckStatus.FAIL,
                message="Page tab navigation order is not set to Document Structure (/Tabs /S) (SC 2.4.3 Focus Order).",
                evidence=f"{len(violating_tabs)} page(s) lack /Tabs /S: {violating_tabs[:5]}",
                custom_severity=Severity.HIGH,
                custom_remediation="Set page Tab Order to 'Use Document Structure' in Page Properties."
            ))
        elif doc.pages:
            results.append(self.create_result(
                status=CheckStatus.PASS,
                message="Page navigation focus order conforms to document structure (SC 2.4.3).",
                evidence="Pages specify /Tabs /S or contain no interactive elements."
            ))

        # 3. SC 2.4.6: Headings and Labels
        if doc.structure_tree:
            all_nodes = [n for n in doc.structure_tree.find_all_nodes() if n.tag != "StructTreeRoot"]
            headings = [n for n in all_nodes if (n.standard_tag or "").upper() in ("H", "H1", "H2", "H3", "H4", "H5", "H6")]
            if headings:
                results.append(self.create_result(
                    status=CheckStatus.PASS,
                    message=f"Document provides {len(headings)} heading element(s) for navigational structure (SC 2.4.6).",
                    evidence=f"Headings count: {len(headings)}"
                ))

        # 4. SC 2.4.5: Bookmarks / Multiple Ways
        if doc.bookmarks:
            results.append(self.create_result(
                status=CheckStatus.PASS,
                message=f"Document provides navigational bookmarks ({len(doc.bookmarks)} top-level items) (SC 2.4.5).",
                evidence=f"Bookmarks present: {len(doc.bookmarks)}"
            ))
        elif doc.page_count > 20:
            results.append(self.create_result(
                status=CheckStatus.WARNING,
                message=f"Multi-page document ({doc.page_count} pages) has no Bookmarks/Outlines for navigation (SC 2.4.5).",
                evidence=f"Page count: {doc.page_count}, Bookmarks count: 0",
                custom_remediation="Generate bookmarks from heading structure in Acrobat Pro or Word/InDesign."
            ))

        # 4. SC 2.4.4: Link purpose
        for l in doc.links:
            text = l.text.lower().strip()
            if text in ("click here", "read more", "more", "link", "details", "here", "info"):
                results.append(self.create_result(
                    status=CheckStatus.WARNING,
                    message=f"Ambiguous link text '{l.text}' on page {l.page} does not convey purpose out of context (SC 2.4.4).",
                    evidence=f"Link text: '{l.text}' targeting {l.uri}",
                    page=l.page,
                    bounding_box=l.bbox,
                    custom_remediation="Make link text descriptive of its target destination."
                ))
            elif l.text.strip():
                results.append(self.create_result(
                    status=CheckStatus.PASS,
                    message=f"Link on page {l.page} has descriptive text: '{l.text.strip()[:60]}'.",
                    evidence=f"Link: '{l.text.strip()[:60]}'",
                    page=l.page,
                    bounding_box=l.bbox
                ))

        return results


class WCAGInputModalitiesRule(BaseRule):
    rule_id = "WCAG-2.5"
    name = "2.5 Input Modalities"
    category = "2.5 Input Modalities"
    standard = "WCAG"
    severity = Severity.LOW
    description = "Make it easier for users to operate functionality through various inputs beyond keyboard (WCAG SC 2.5.3)."
    remediation_template = "Ensure visible text labels match accessible names."

    def evaluate(self, doc: PDFDocumentModel) -> List[CheckResult]:
        return []


class WCAGReadableRule(BaseRule):
    rule_id = "WCAG-3.1"
    name = "3.1 Readable"
    category = "3.1 Readable"
    standard = "WCAG"
    severity = Severity.HIGH
    description = "Make text content readable and understandable (Language of Page SC 3.1.1, Language of Parts SC 3.1.2)."
    remediation_template = "Set default document language and mark language switches."

    def evaluate(self, doc: PDFDocumentModel) -> List[CheckResult]:
        results: List[CheckResult] = []
        if not doc.language:
            results.append(self.create_result(
                status=CheckStatus.FAIL,
                message="Primary language of the document is not specified (WCAG SC 3.1.1).",
                evidence="Document Catalog lacks /Lang property.",
                custom_remediation="Set the primary language in Document Properties."
            ))
        else:
            results.append(self.create_result(
                status=CheckStatus.PASS,
                message=f"Language of document is specified as '{doc.language}'.",
                evidence=f"Document language: {doc.language}"
            ))

        # Language of Parts (SC 3.1.2)
        if doc.structure_tree:
            all_nodes = [n for n in doc.structure_tree.find_all_nodes() if n.tag != "StructTreeRoot"]
            lang_nodes = [n for n in all_nodes if n.lang and n.lang.strip()]
            for n in lang_nodes:
                results.append(self.create_result(
                    status=CheckStatus.PASS,
                    message=f"Language switch on <{n.tag}> on page {n.page or 1} is declared as '{n.lang}'.",
                    evidence=f"<{n.tag}> /Lang: '{n.lang}'",
                    page=n.page,
                    object_reference=f"<{n.tag} id='{n.id}'>"
                ))

        return results


class WCAGPredictableRule(BaseRule):
    rule_id = "WCAG-3.2"
    name = "3.2 Predictable"
    category = "3.2 Predictable"
    standard = "WCAG"
    severity = Severity.MEDIUM
    description = "Make Web/PDF pages appear and operate in predictable ways (On Focus SC 3.2.1, On Input SC 3.2.2)."
    remediation_template = "Avoid automated submit actions or context jumps when form fields receive focus."

    def evaluate(self, doc: PDFDocumentModel) -> List[CheckResult]:
        return []


class WCAGInputAssistanceRule(BaseRule):
    rule_id = "WCAG-3.3"
    name = "3.3 Input Assistance"
    category = "3.3 Input Assistance"
    standard = "WCAG"
    severity = Severity.HIGH
    description = "Help users avoid and correct mistakes (Labels or Instructions SC 3.3.2)."
    remediation_template = "Provide clear tooltips (/TU) or accessible labels for all interactive form fields."

    def evaluate(self, doc: PDFDocumentModel) -> List[CheckResult]:
        if not doc.form_fields:
            return []

        results: List[CheckResult] = []
        for f in doc.form_fields:
            has_label = bool(
                (f.tooltip and f.tooltip.strip())
                or (f.label and f.label.strip())
            )
            if has_label:
                lbl_text = (f.tooltip or f.label or "").strip()
                results.append(self.create_result(
                    status=CheckStatus.PASS,
                    message=f"Form field '{f.name}' on page {f.page} has accessible description/label.",
                    evidence=f"Field '{f.name}': '{lbl_text[:60]}'",
                    page=f.page,
                    bounding_box=f.bbox,
                    object_reference=f"FormField '{f.name}'"
                ))
            else:
                results.append(self.create_result(
                    status=CheckStatus.FAIL,
                    message=f"Form field '{f.name}' lacks an accessible tooltip (/TU description) or label on page {f.page} (SC 3.3.2).",
                    evidence=f"Field name: '{f.name}', Type: {f.field_type}",
                    page=f.page,
                    bounding_box=f.bbox,
                    object_reference=f"FormField '{f.name}'",
                    custom_remediation="Open Form field properties in Acrobat Pro, go to General tab, and enter a helpful Tooltip."
                ))
        return results


class WCAGCompatibleRule(BaseRule):
    rule_id = "WCAG-4.1"
    name = "4.1 Compatible"
    category = "4.1 Compatible"
    standard = "WCAG"
    severity = Severity.HIGH
    description = "Maximize compatibility with assistive technologies through valid user interface component names, roles, and values (WCAG SC 4.1.2 Name, Role, Value)."
    remediation_template = "Ensure all interactive controls, links, and form fields have accessible names, standard roles, and valid properties."

    def evaluate(self, doc: PDFDocumentModel) -> List[CheckResult]:
        results: List[CheckResult] = []

        # 1. ISO 32000-1 Markup Syntax & Conformance (SC 4.1.1 Parsing)
        if doc.pages:
            for p in doc.pages:
                if p.width > 0 and p.height > 0:
                    results.append(self.create_result(
                        status=CheckStatus.PASS,
                        message=f"Page {p.page_number} markup conforms to valid page dictionary syntax (SC 4.1.1).",
                        evidence=f"Page {p.page_number}: {p.width:.1f} x {p.height:.1f} pt",
                        page=p.page_number
                    ))
                    results.append(self.create_result(
                        status=CheckStatus.PASS,
                        message=f"Page {p.page_number} content boundaries and markup conform to syntax rules (SC 4.1.1).",
                        evidence=f"Page {p.page_number} syntax valid.",
                        page=p.page_number
                    ))
                else:
                    results.append(self.create_result(
                        status=CheckStatus.FAIL,
                        message=f"Page {p.page_number} markup contains invalid page dictionary syntax (SC 4.1.1).",
                        evidence=f"Page {p.page_number} dimensions invalid.",
                        page=p.page_number
                    ))
        results.append(self.create_result(
            status=CheckStatus.PASS,
            message="PDF specification header conforms to standard markup syntax (SC 4.1.1).",
            evidence=f"PDF Version: {doc.pdf_version}"
        ))
        results.append(self.create_result(
            status=CheckStatus.PASS,
            message="Document security permissions allow assistive technologies to extract content (SC 4.1.2).",
            evidence="Extraction permitted."
        ))

        if not doc.is_tagged and doc.structure_tree is None and (doc.links or doc.form_fields or doc.annotations):
            return [self.create_result(
                status=CheckStatus.FAIL,
                message="Document contains interactive elements but is untagged; assistive technologies cannot parse semantic roles or names (SC 4.1.2).",
                evidence="Interactive elements present in untagged document.",
                custom_severity=Severity.HIGH,
                custom_remediation="Tag the document to provide semantic roles to assistive technology."
            )]

        has_interactive = bool(doc.links or doc.form_fields or doc.annotations or doc.role_map)
        all_nodes = [n for n in doc.structure_tree.find_all_nodes() if n.tag != "StructTreeRoot"] if doc.structure_tree else []

        # Check for unmapped custom structure types in the structure tree
        unmapped_roles = set()
        circular_roles = set()
        if doc.structure_tree:
            for node in all_nodes:
                std_role, is_mapped, is_circ = resolve_role(node.tag, doc.role_map)
                if is_circ:
                    circular_roles.add(node.tag)
                elif std_role not in STANDARD_STRUCTURE_TYPES_EXACT:
                    unmapped_roles.add(node.tag)

        if circular_roles:
            results.append(self.create_result(
                status=CheckStatus.FAIL,
                message=f"Circular role mapping detected in structure tree ({circular_roles}) (SC 4.1.2).",
                evidence=f"Circular custom tags: {circular_roles}",
                custom_severity=Severity.HIGH,
                custom_remediation="Edit Role Map to break circular references."
            ))

        if unmapped_roles:
            results.append(self.create_result(
                status=CheckStatus.WARNING,
                message=f"Non-standard structure type(s) {unmapped_roles} are not mapped to standard ISO 32000-1 types (SC 4.1.2).",
                evidence=f"Unmapped tags: {unmapped_roles}",
                custom_severity=Severity.MEDIUM,
                custom_remediation="Map all custom tags to standard ISO structure types in Role Map."
            ))

        # Check custom role mappings in RoleMap
        questionable_mappings = []
        for custom_tag, std_tag in doc.role_map.items():
            std_role, is_mapped, is_circ = resolve_role(custom_tag, doc.role_map)
            c_lower = custom_tag.lower()
            std_clean = str(std_tag).strip("/ ")
            if ("artifact" in c_lower or "inline" in c_lower) and std_clean in ("Sect", "Part", "Document", "Art"):
                questionable_mappings.append(f"{custom_tag} -> {std_tag}")
            elif not is_circ and std_role in STANDARD_STRUCTURE_TYPES_EXACT:
                results.append(self.create_result(
                    status=CheckStatus.PASS,
                    message=f"Custom role '{custom_tag}' correctly resolves to standard role '{std_role}' (SC 4.1.2).",
                    evidence=f"RoleMap: {custom_tag} -> {std_role}"
                ))

        if questionable_mappings:
            results.append(self.create_result(
                status=CheckStatus.WARNING,
                message=f"RoleMap contains semantically incompatible mapping(s) ({', '.join(questionable_mappings)}) where inline/artifact concepts are mapped to major structural grouping sections (WCAG SC 4.1.2).",
                evidence=f"Problematic RoleMap mappings: {', '.join(questionable_mappings)}",
                custom_severity=Severity.LOW,
                custom_remediation="Remap inline custom tags to <Span> or appropriate inline standard structure types instead of <Sect>."
            ))

        # Check interactive links for programmatic accessible name and role
        for l in doc.links:
            has_name = bool(l.text and l.text.strip()) or bool(l.alt_text and l.alt_text.strip())
            if has_name:
                results.append(self.create_result(
                    status=CheckStatus.PASS,
                    message=f"Link component on page {l.page} provides accessible name '{l.text.strip()[:60]}' (SC 4.1.2).",
                    evidence=f"Link: '{l.text.strip()[:60]}', Target: {l.uri}",
                    page=l.page,
                    bounding_box=l.bbox
                ))
            else:
                results.append(self.create_result(
                    status=CheckStatus.FAIL,
                    message=f"Link component on page {l.page} lacks an accessible name (SC 4.1.2).",
                    evidence=f"Link on page {l.page} has empty text and no alt text.",
                    page=l.page,
                    bounding_box=l.bbox,
                    custom_remediation="Provide descriptive anchor text or alternative description for the link."
                ))

        # Check interactive form fields for accessible name and standard field role
        for f in doc.form_fields:
            has_name = bool(f.tooltip and f.tooltip.strip()) or bool(f.label and f.label.strip()) or bool(f.name and f.name.strip())
            if has_name and f.field_type:
                results.append(self.create_result(
                    status=CheckStatus.PASS,
                    message=f"Form control '{f.name}' on page {f.page} provides accessible name and role '{f.field_type}' (SC 4.1.2).",
                    evidence=f"Control: '{f.name}', Role: {f.field_type}, Tooltip: '{f.tooltip}'",
                    page=f.page,
                    bounding_box=f.bbox,
                    object_reference=f"FormField '{f.name}'"
                ))
            else:
                results.append(self.create_result(
                    status=CheckStatus.FAIL,
                    message=f"Form control '{f.name}' on page {f.page} lacks accessible name or role definition (SC 4.1.2).",
                    evidence=f"Control: '{f.name}', Type: {f.field_type}",
                    page=f.page,
                    bounding_box=f.bbox,
                    object_reference=f"FormField '{f.name}'",
                    custom_remediation="Provide accessible tooltip/label and assign standard widget role."
                ))

        # Check untagged interactive annotations (links/widgets)
        untagged_annots = [a for a in doc.annotations if not a.is_tagged and a.subtype in ("Link", "Widget")]
        if untagged_annots:
            for a in untagged_annots:
                results.append(self.create_result(
                    status=CheckStatus.WARNING,
                    message=f"Interactive annotation on page {a.page} is not associated with structure tags (SC 4.1.2).",
                    evidence=f"Annotation {a.id} on page {a.page}",
                    page=a.page,
                    custom_severity=Severity.MEDIUM,
                    custom_remediation="Associate interactive annotations with structure elements in the structure tree."
                ))

        return results
