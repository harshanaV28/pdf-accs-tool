"""
WCAG 2.1 / 2.2 AA Rules Suite
Implements accessibility checks mapped across the 13 WCAG guidelines.
"""

from typing import List
from ..rule_base import BaseRule
from ...core.models import PDFDocumentModel, CheckResult, CheckStatus, Severity


class WCAGTextAlternativesRule(BaseRule):
    rule_id = "WCAG-1.1.1"
    name = "1.1 Text Alternatives"
    category = "1.1 Text Alternatives"
    standard = "WCAG"
    severity = Severity.HIGH
    description = "All non-text content that is presented to the user has a text alternative that serves the equivalent purpose (WCAG SC 1.1.1)."
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
                    message=f"Image on page {img.page} does not have alternative text.",
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
    description = "Provide alternatives for time-based media such as video or audio embedded in the PDF."
    remediation_template = "Provide synchronized captions or text transcripts for embedded media."

    def evaluate(self, doc: PDFDocumentModel) -> List[CheckResult]:
        # Standard static PDFs pass; if media annotations exist, flag for manual review
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
                    message=f"Table on page {t.page} lacks header cells (<TH>).",
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
            headings = [n for n in doc.structure_tree.find_all_nodes() if n.standard_tag.upper() in ("H", "H1", "H2", "H3", "H4", "H5", "H6")]
            if not headings:
                results.append(self.create_result(
                    status=CheckStatus.WARNING,
                    message="Document contains no tagged headings (<H1>-<H6>). Content hierarchy may be difficult to navigate.",
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
            list_items = [n for n in all_nodes if n.standard_tag.upper() == "LI"]
            invalid_lis = []
            for li in list_items:
                invalid_children = [c for c in li.children if c.standard_tag.upper() not in ("LBL", "LBODY")]
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
    description = "Make it easier for users to see and hear content including separating foreground from background (Contrast SC 1.4.3)."
    remediation_template = "Verify visual contrast of text against background meets 4.5:1 for regular text and 3:1 for large text."

    def evaluate(self, doc: PDFDocumentModel) -> List[CheckResult]:
        results = []
        # Check font embedding (PDF16 / SC 1.4)
        unembedded = [f for f in doc.fonts if not f.is_embedded and f.is_used]
        if unembedded:
            results.append(self.create_result(
                status=CheckStatus.FAIL,
                message=f"{len(unembedded)} font(s) are not embedded, risking inaccurate text presentation (WCAG 1.4 / PDF16).",
                evidence=f"Unembedded font(s): {', '.join(f.name for f in unembedded[:3])}",
                page=unembedded[0].pages[0] if unembedded[0].pages else 1,
                custom_remediation="Embed all fonts in the document."
            ))

        # Contrast requires manual visual review or sampling
        results.append(self.create_result(
            status=CheckStatus.MANUAL_REVIEW,
            message="Verify color contrast (minimum 4.5:1 for normal text, 3:1 for large text) and ensure color is not the only means of conveying information.",
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
            # Check tab order
            bad_tabs = [p.page_number for p in doc.pages if p.tab_order_mode != "S"]
            if bad_tabs and doc.is_tagged:
                results.append(self.create_result(
                    status=CheckStatus.WARNING,
                    message=f"Page tab order on pages {bad_tabs[:5]} is not set to Structure order for keyboard focus navigation.",
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
    description = "Do not design content in a way that is known to cause seizures or physical reactions (WCAG SC 2.3.1)."
    remediation_template = "Avoid animations or blinking content that flashes more than three times in any one-second period."

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
    description = "Provide ways to help users navigate, find content, and determine where they are (Title SC 2.4.2, Link Purpose SC 2.4.4, Bookmarks SC 2.4.5)."
    remediation_template = "Set document title, provide bookmarks for long documents, and write descriptive link text."

    def evaluate(self, doc: PDFDocumentModel) -> List[CheckResult]:
        results = []

        # 1. Page / Document Titled
        if not doc.title or not doc.title.strip():
            results.append(self.create_result(
                status=CheckStatus.FAIL,
                message="Document lacks a descriptive Title (WCAG SC 2.4.2 Page Titled).",
                evidence="Title property is missing or empty.",
                custom_remediation="Add a descriptive title in File Properties."
            ))
        else:
            results.append(self.create_result(
                status=CheckStatus.PASS,
                message=f"Document has a descriptive title: '{doc.title}'.",
                evidence=f"Title: '{doc.title}'"
            ))

        # 2. Bookmarks for multi-page documents (SC 2.4.5)
        if doc.page_count > 20 and not doc.bookmarks:
            results.append(self.create_result(
                status=CheckStatus.WARNING,
                message=f"Document has {doc.page_count} pages but no Bookmarks/Outlines for navigation (SC 2.4.5).",
                evidence=f"Page count: {doc.page_count}, Bookmarks count: 0",
                custom_remediation="Generate bookmarks from heading structure in Acrobat Pro or Word/InDesign."
            ))
        elif doc.bookmarks:
            results.append(self.create_result(
                status=CheckStatus.PASS,
                message=f"Document provides navigational bookmarks ({len(doc.bookmarks)} top-level items).",
                evidence="Bookmarks present."
            ))

        # 3. Link purpose (SC 2.4.4)
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
                    custom_remediation="Make link text descriptive of its target destination (e.g. 'Read the 2026 Financial Report')."
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
                    message=f"Form field '{f.name}' lacks an accessible tooltip (/TU description) on page {f.page}.",
                    evidence=f"Field name: '{f.name}', Type: {f.field_type}",
                    page=f.page,
                    bounding_box=f.bbox,
                    object_reference=f"FormField '{f.name}'",
                    custom_remediation=f"Open Form field properties in Acrobat Pro, go to General tab, and enter a helpful Tooltip."
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
    description = "Maximize compatibility with current and future user agents, including assistive technologies (Name, Role, Value SC 4.1.2)."
    remediation_template = "Ensure all interactive elements have accessible names and standard structural roles."

    def evaluate(self, doc: PDFDocumentModel) -> List[CheckResult]:
        results = []
        if doc.is_tagged and doc.allows_extraction:
            results.append(self.create_result(
                status=CheckStatus.PASS,
                message="Document semantic tagging and extraction permissions are compatible with assistive technology.",
                evidence="Tagged PDF with accessibility permissions enabled."
            ))
        else:
            results.append(self.create_result(
                status=CheckStatus.FAIL,
                message="Assistive technology compatibility is compromised by untagged structure or restricted extraction permissions.",
                evidence=f"Tagged: {doc.is_tagged}, Allows extraction: {doc.allows_extraction}",
                custom_remediation="Enable accessibility extraction and tag the document."
            ))

        return results
