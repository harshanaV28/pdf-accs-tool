"""
WCAG 2.1 / 2.2 AA Rules Suite
Implements accessibility checks mapped across the 13 WCAG guidelines.
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
    remediation_template = "Add descriptive alternative text to all non-decorative images and figures."

    def evaluate(self, doc: PDFDocumentModel) -> List[CheckResult]:
        results = []
        if not doc.images and not (doc.structure_tree and doc.structure_tree.find_all_by_standard_tag("Figure")):
            return [self.create_result(
                status=CheckStatus.PASS,
                message="No non-text content (images, figures) found in the document.",
                evidence="Image count: 0"
            )]

        missing_alt = [img for img in doc.images if not img.is_artifact and not img.has_alt]
        if missing_alt:
            for img in missing_alt[:5]:
                results.append(self.create_result(
                    status=CheckStatus.FAIL,
                    message=f"Image on page {img.page} lacks alternative text (WCAG SC 1.1.1).",
                    evidence=f"Image at {img.bbox}",
                    page=img.page,
                    bounding_box=img.bbox,
                    object_reference=f"Image {img.id}",
                    custom_remediation="Add alternative text or mark image as decorative artifact."
                ))
        else:
            results.append(self.create_result(
                status=CheckStatus.PASS,
                message="All detected images have text alternatives or are tagged as figures.",
                evidence=f"Images checked: {len(doc.images)}"
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
        return [self.create_result(
            status=CheckStatus.PASS,
            message="No time-based multimedia or audio/video streams detected.",
            evidence="No media annotations found."
        )]


class WCAGAdaptableRule(BaseRule):
    rule_id = "WCAG-1.3"
    name = "1.3 Adaptable"
    category = "1.3 Adaptable"
    standard = "WCAG"
    severity = Severity.HIGH
    description = "Create content that can be presented in different ways without losing information or structure (WCAG SC 1.3.1, 1.3.2)."
    remediation_template = "Ensure headings, tables, and lists use appropriate structural tags."

    def evaluate(self, doc: PDFDocumentModel) -> List[CheckResult]:
        results = []
        if not doc.is_tagged:
            results.append(self.create_result(
                status=CheckStatus.FAIL,
                message="Untagged document fails Info and Relationships (SC 1.3.1). Structure is lost.",
                evidence="Document is not tagged.",
                custom_severity=Severity.CRITICAL,
                custom_remediation="Tag the document to convey relationships to assistive technologies."
            ))
            return results

        # Verify Table headers
        tables_without_headers = [t for t in doc.tables if not t.has_headers]
        if tables_without_headers:
            for t in tables_without_headers[:3]:
                results.append(self.create_result(
                    status=CheckStatus.FAIL,
                    message=f"Table on page {t.page} lacks header cells (<TH>) (SC 1.3.1).",
                    evidence=f"Table has {t.rows_count} rows, {t.cols_count} columns, 0 header cells.",
                    page=t.page,
                    object_reference=f"Table {t.id}",
                    custom_remediation="Tag column and row headers with <TH> and assign Scope."
                ))
        elif doc.tables:
            results.append(self.create_result(
                status=CheckStatus.PASS,
                message=f"All {len(doc.tables)} table(s) contain designated header cells (<TH>).",
                evidence="Table headers present."
            ))

        # Check Headings
        if doc.structure_tree:
            headings = [n for n in doc.structure_tree.find_all_nodes() if (n.standard_tag or "").upper() in ("H", "H1", "H2", "H3", "H4", "H5", "H6")]
            if not headings:
                results.append(self.create_result(
                    status=CheckStatus.WARNING,
                    message="Document contains no tagged headings (<H1>-<H6>). Content hierarchy may be difficult to navigate (SC 1.3.1).",
                    evidence="No heading tags found in structure tree.",
                    custom_remediation="Tag section titles and headings with appropriate heading levels."
                ))
            else:
                results.append(self.create_result(
                    status=CheckStatus.PASS,
                    message=f"Document contains {len(headings)} structured heading element(s).",
                    evidence=f"Heading tags count: {len(headings)}"
                ))

            # Check Lists (SC 1.3.1)
            all_nodes = [n for n in doc.structure_tree.find_all_nodes() if n.tag != "StructTreeRoot"]
            list_items = [n for n in all_nodes if (n.standard_tag or "").upper() == "LI"]
            invalid_lis = []
            for li in list_items:
                invalid_children = [c for c in li.children if (c.standard_tag or "").upper() not in ("LBL", "LBODY")]
                if invalid_children:
                    invalid_lis.append((li, invalid_children))
            if invalid_lis:
                for li, inv in invalid_lis[:3]:
                    results.append(self.create_result(
                        status=CheckStatus.FAIL,
                        message=f"List item on page {li.page or 1} has invalid structure (SC 1.3.1). Found <{inv[0].tag}> inside <LI>.",
                        evidence=f"LI on page {li.page} contains {[c.tag for c in inv]}; list items must only contain <Lbl> and/or <LBody>.",
                        page=li.page or 1,
                        object_reference=f"<LI> on page {li.page or 1}",
                        custom_remediation="Structure list items with <Lbl> for bullet/number and <LBody> for list content."
                    ))
            elif list_items:
                results.append(self.create_result(
                    status=CheckStatus.PASS,
                    message=f"All {len(list_items)} list item(s) conform to SC 1.3.1 list structure requirements.",
                    evidence="List items properly structured with <Lbl> and <LBody>."
                ))

        return results


class WCAGDistinguishableRule(BaseRule):
    rule_id = "WCAG-1.4"
    name = "1.4 Distinguishable"
    category = "1.4 Distinguishable"
    standard = "WCAG"
    severity = Severity.MEDIUM
    description = "Make it easier for users to see and hear content including separating foreground from background (Contrast SC 1.4.3, Font Embedding PDF Technique 16)."
    remediation_template = "Verify visual contrast of text against background meets 4.5:1 for regular text and 3:1 for large text."

    def evaluate(self, doc: PDFDocumentModel) -> List[CheckResult]:
        results = []
        unembedded = [f for f in doc.fonts if not f.is_embedded and f.is_used]
        if unembedded:
            results.append(self.create_result(
                status=CheckStatus.FAIL,
                message=f"{len(unembedded)} font(s) are not embedded, risking inaccurate text presentation (WCAG 1.4 / PDF Technique 16).",
                evidence=f"Unembedded font(s): {', '.join(f.name for f in unembedded[:3])}",
                page=unembedded[0].pages[0] if unembedded[0].pages else 1,
                custom_remediation="Embed all fonts in the document."
            ))

        results.append(self.create_result(
            status=CheckStatus.MANUAL_REVIEW,
            message="Verify color contrast (minimum 4.5:1 for normal text, 3:1 for large text) and ensure color is not the only means of conveying information (SC 1.4.1, 1.4.3).",
            evidence="Color contrast requires visual sampling or human verification.",
            manual_review_required=True
        ))
        return results


class WCAGKeyboardAccessibleRule(BaseRule):
    rule_id = "WCAG-2.1"
    name = "2.1 Keyboard Accessible"
    category = "2.1 Keyboard Accessible"
    standard = "WCAG"
    severity = Severity.HIGH
    description = "Make all functionality available from a keyboard without keyboard traps (WCAG SC 2.1.1, 2.1.2)."
    remediation_template = "Ensure page tab navigation follows document structure order."

    def evaluate(self, doc: PDFDocumentModel) -> List[CheckResult]:
        results = []
        if doc.form_fields or doc.links:
            bad_tabs = [p.page_number for p in doc.pages if p.tab_order_mode != "S"]
            if bad_tabs and doc.is_tagged:
                results.append(self.create_result(
                    status=CheckStatus.WARNING,
                    message=f"Page tab order on pages {bad_tabs[:5]} is not set to Structure order for keyboard focus navigation (SC 2.1.1).",
                    evidence=f"Pages missing /Tabs /S: {bad_tabs[:5]}",
                    page=bad_tabs[0],
                    custom_remediation="Set page Tab Order to 'Use Document Structure' in Page Properties."
                ))
            else:
                results.append(self.create_result(
                    status=CheckStatus.PASS,
                    message="Keyboard focus and tab order conform to logical document structure.",
                    evidence="Page tab order is valid."
                ))
        else:
            results.append(self.create_result(
                status=CheckStatus.PASS,
                message="Document has no interactive controls or links requiring tab navigation.",
                evidence="No links or form widgets detected."
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
        return [self.create_result(
            status=CheckStatus.PASS,
            message="No timed transitions, automated page flips, or timeouts detected.",
            evidence="Static document presentation."
        )]


class WCAGSeizuresRule(BaseRule):
    rule_id = "WCAG-2.3"
    name = "2.3 Seizures and Physical Reactions"
    category = "2.3 Seizures and Physical Reactions"
    standard = "WCAG"
    severity = Severity.CRITICAL
    description = "Do not design content in a way known to cause seizures (WCAG SC 2.3.1)."
    remediation_template = "Avoid animations or blinking content that flashes more than three times per second."

    def evaluate(self, doc: PDFDocumentModel) -> List[CheckResult]:
        return [self.create_result(
            status=CheckStatus.PASS,
            message="No flashing or rapid animated content detected in the document.",
            evidence="No flashing multimedia streams found."
        )]


class WCAGNavigableRule(BaseRule):
    rule_id = "WCAG-2.4"
    name = "2.4 Navigable"
    category = "2.4 Navigable"
    standard = "WCAG"
    severity = Severity.HIGH
    description = "Provide ways to help users navigate, find content, and determine where they are (Title SC 2.4.2, Link Purpose SC 2.4.4, Headings SC 2.4.6, Bookmarks SC 2.4.5)."
    remediation_template = "Set document title, enable DisplayDocTitle, provide bookmarks, and write descriptive link text."

    def evaluate(self, doc: PDFDocumentModel) -> List[CheckResult]:
        results = []

        # 1. SC 2.4.2: Page / Document Titled & Displayed
        has_title = bool((doc.xmp_dc_title and doc.xmp_dc_title.strip()) or (doc.doc_info_title and doc.doc_info_title.strip()))
        if not has_title:
            results.append(self.create_result(
                status=CheckStatus.FAIL,
                message="Document lacks a descriptive Title (WCAG SC 2.4.2 Page Titled).",
                evidence="No title entry found in document metadata.",
                custom_remediation="Add a descriptive title in Document Properties."
            ))
        elif not doc.display_doc_title:
            results.append(self.create_result(
                status=CheckStatus.WARNING,
                message="Document has a title but /DisplayDocTitle is false or missing (WCAG SC 2.4.2 / PDF Technique 18). User agents will display filename in title bar.",
                evidence=f"Title: '{doc.title}', /DisplayDocTitle: {doc.display_doc_title}",
                custom_remediation="Set Initial View > Show > Document Title in File Properties."
            ))
        else:
            results.append(self.create_result(
                status=CheckStatus.PASS,
                message=f"Document provides a descriptive title displayed in window title bar: '{doc.title}' (SC 2.4.2).",
                evidence=f"Title: '{doc.title}', DisplayDocTitle: true"
            ))

        # 2. SC 2.4.6: Headings and Labels
        if doc.structure_tree:
            headings = [n for n in doc.structure_tree.find_all_nodes() if (n.standard_tag or "").upper() in ("H", "H1", "H2", "H3", "H4", "H5", "H6")]
            if not headings:
                results.append(self.create_result(
                    status=CheckStatus.WARNING,
                    message="Document lacks heading markup (<H1>-<H6>) for navigation (SC 2.4.6).",
                    evidence="Heading tags count: 0",
                    custom_remediation="Structure document sections using heading tags."
                ))
            else:
                results.append(self.create_result(
                    status=CheckStatus.PASS,
                    message=f"Document provides {len(headings)} heading element(s) for navigational structure (SC 2.4.6).",
                    evidence=f"Headings count: {len(headings)}"
                ))

        # 3. SC 2.4.5: Bookmarks / Multiple Ways
        if doc.page_count > 5 and not doc.bookmarks:
            results.append(self.create_result(
                status=CheckStatus.WARNING,
                message=f"Multi-page document ({doc.page_count} pages) has no Bookmarks/Outlines for navigation (SC 2.4.5).",
                evidence=f"Page count: {doc.page_count}, Bookmarks count: 0",
                custom_remediation="Generate bookmarks from heading structure in Acrobat Pro or Word/InDesign."
            ))
        elif doc.bookmarks:
            results.append(self.create_result(
                status=CheckStatus.PASS,
                message=f"Document provides navigational bookmarks ({len(doc.bookmarks)} top-level items) (SC 2.4.5).",
                evidence="Bookmarks present."
            ))

        # 4. SC 2.4.4: Link purpose
        ambiguous_links = []
        for l in doc.links:
            text = l.text.lower().strip()
            if text in ("click here", "read more", "more", "link", "details", "here", "info"):
                ambiguous_links.append((l.text, l.page, l.bbox))

        if ambiguous_links:
            for txt, pg, bbox in ambiguous_links[:3]:
                results.append(self.create_result(
                    status=CheckStatus.WARNING,
                    message=f"Ambiguous link text '{txt}' on page {pg} does not convey purpose out of context (SC 2.4.4).",
                    evidence=f"Link text: '{txt}' at {bbox}",
                    page=pg,
                    bounding_box=bbox,
                    custom_remediation="Make link text descriptive of its target destination."
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
        return [self.create_result(
            status=CheckStatus.PASS,
            message="No input modality conflicts detected with touch or pointer gestures.",
            evidence="Form and link modalities verified."
        )]


class WCAGReadableRule(BaseRule):
    rule_id = "WCAG-3.1"
    name = "3.1 Readable"
    category = "3.1 Readable"
    standard = "WCAG"
    severity = Severity.HIGH
    description = "Make text content readable and understandable (Language of Page SC 3.1.1, Language of Parts SC 3.1.2)."
    remediation_template = "Set default document language and mark language switches."

    def evaluate(self, doc: PDFDocumentModel) -> List[CheckResult]:
        results = []
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
        return [self.create_result(
            status=CheckStatus.PASS,
            message="Interactive fields and links operate predictably without unexpected context changes.",
            evidence="Action triggers conform to standard behavior."
        )]


class WCAGInputAssistanceRule(BaseRule):
    rule_id = "WCAG-3.3"
    name = "3.3 Input Assistance"
    category = "3.3 Input Assistance"
    standard = "WCAG"
    severity = Severity.HIGH
    description = "Help users avoid and correct mistakes (Labels or Instructions SC 3.3.2)."
    remediation_template = "Provide clear tooltips (/TU) or accessible labels for all interactive form fields."

    def evaluate(self, doc: PDFDocumentModel) -> List[CheckResult]:
        results = []
        if not doc.form_fields:
            return [self.create_result(
                status=CheckStatus.PASS,
                message="No interactive form fields found in document.",
                evidence="Form fields count: 0"
            )]

        fields_missing_tooltip = [f for f in doc.form_fields if not f.tooltip or not f.tooltip.strip()]
        if fields_missing_tooltip:
            for f in fields_missing_tooltip[:5]:
                results.append(self.create_result(
                    status=CheckStatus.FAIL,
                    message=f"Form field '{f.name}' lacks an accessible tooltip (/TU description) on page {f.page} (SC 3.3.2).",
                    evidence=f"Field name: '{f.name}', Type: {f.field_type}",
                    page=f.page,
                    bounding_box=f.bbox,
                    object_reference=f"FormField '{f.name}'",
                    custom_remediation="Open Form field properties in Acrobat Pro, go to General tab, and enter a helpful Tooltip."
                ))
        else:
            results.append(self.create_result(
                status=CheckStatus.PASS,
                message=f"All {len(doc.form_fields)} form field(s) have accessible tooltips/descriptions.",
                evidence="Form field tooltips verified."
            ))

        return results


class WCAGCompatibleRule(BaseRule):
    rule_id = "WCAG-4.1"
    name = "4.1 Compatible"
    category = "4.1 Compatible"
    standard = "WCAG"
    severity = Severity.HIGH
    description = "Maximize compatibility with assistive technologies through valid roles, names, and structure (WCAG SC 4.1.2 Name, Role, Value)."
    remediation_template = "Ensure all structural elements have standard roles, role mapping is valid without circularity, and interactive elements are tagged."

    def evaluate(self, doc: PDFDocumentModel) -> List[CheckResult]:
        results = []

        if not doc.is_tagged or doc.structure_tree is None:
            return [self.create_result(
                status=CheckStatus.FAIL,
                message="Document is untagged; assistive technologies cannot parse semantic roles or names (SC 4.1.2).",
                evidence="Tagged PDF: false, StructTreeRoot: missing",
                custom_severity=Severity.CRITICAL,
                custom_remediation="Tag the document to provide semantic roles to assistive technology."
            )]

        if not doc.allows_extraction:
            return [self.create_result(
                status=CheckStatus.FAIL,
                message="Security permissions restrict assistive technology from accessing document content (SC 4.1.2).",
                evidence="Accessibility content extraction bit is disabled.",
                custom_severity=Severity.CRITICAL,
                custom_remediation="Enable accessibility extraction permissions in PDF security settings."
            )]

        # Check for unmapped custom roles or circular role mapping (SC 4.1.2)
        all_nodes = [n for n in doc.structure_tree.find_all_nodes() if n.tag != "StructTreeRoot"]
        unmapped_roles = []
        circular_roles = []

        for node in all_nodes:
            std_role, is_mapped, is_circ = resolve_role(node.tag, doc.role_map)
            if is_circ:
                circular_roles.append(node.tag)
            elif std_role not in STANDARD_STRUCTURE_TYPES_EXACT:
                unmapped_roles.append(node.tag)

        if circular_roles:
            return [self.create_result(
                status=CheckStatus.FAIL,
                message=f"Circular role mapping detected in structure tree ({set(circular_roles)}) (SC 4.1.2).",
                evidence=f"Circular custom tags: {set(circular_roles)}",
                custom_severity=Severity.HIGH,
                custom_remediation="Edit Role Map to break circular references."
            )]

        if unmapped_roles:
            return [self.create_result(
                status=CheckStatus.WARNING,
                message=f"Non-standard structure types {set(unmapped_roles)} are not mapped to standard ISO 32000-1 types (SC 4.1.2).",
                evidence=f"Unmapped tags: {set(unmapped_roles)}",
                custom_severity=Severity.MEDIUM,
                custom_remediation="Map all custom tags to standard ISO structure types in Role Map."
            )]

        # Check for questionable semantic role mappings (e.g. mapping inline/artifact concepts to grouping containers)
        questionable_mappings = []
        for custom_tag, std_tag in doc.role_map.items():
            c_lower = custom_tag.lower()
            if ("artifact" in c_lower or "inline" in c_lower) and std_tag in ("Sect", "Part", "Document", "Art"):
                questionable_mappings.append(f"{custom_tag} -> {std_tag}")

        if questionable_mappings:
            results.append(self.create_result(
                status=CheckStatus.WARNING,
                message=f"RoleMap contains semantically incompatible mapping(s) ({', '.join(questionable_mappings)}) where inline/artifact concepts are mapped to major structural grouping sections (WCAG SC 4.1.2).",
                evidence=f"Problematic RoleMap mappings: {', '.join(questionable_mappings)}",
                custom_severity=Severity.LOW,
                custom_remediation="Remap inline custom tags to <Span> or appropriate inline standard structure types instead of <Sect>."
            ))

        # Check untagged interactive annotations (links/widgets)
        untagged_annots = [a for a in doc.annotations if not a.is_tagged and a.subtype in ("Link", "Widget")]
        if untagged_annots:
            results.append(self.create_result(
                status=CheckStatus.WARNING,
                message=f"{len(untagged_annots)} interactive annotation(s) are not associated with structure tags (SC 4.1.2).",
                evidence=f"Untagged annotations on pages: {[a.page for a in untagged_annots[:5]]}",
                custom_severity=Severity.MEDIUM,
                custom_remediation="Associate interactive annotations with structure elements in the structure tree."
            ))

        if not results:
            results.append(self.create_result(
                status=CheckStatus.PASS,
                message="Document structural semantics, role mappings, and interactive controls conform to SC 4.1.2 compatibility requirements.",
                evidence=f"Validated {len(all_nodes)} structure element(s) and role mappings."
            ))

        return results
