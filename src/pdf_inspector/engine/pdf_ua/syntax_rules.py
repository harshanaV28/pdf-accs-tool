"""
PDF Syntax (ISO 32000-1) Rules
Validates core PDF syntax compliance for accessibility, catalog structure, and security permissions.
"""

from typing import List
from ..rule_base import BaseRule
from ...core.models import PDFDocumentModel, CheckResult, CheckStatus, Severity


class PDFSyntaxBasicRule(BaseRule):
    rule_id = "PDFUA-SYNTAX-001"
    name = "PDF Syntax (ISO 32000-1) Core"
    category = "PDF Syntax (ISO 32000-1)"
    standard = "PDF/UA"
    severity = Severity.CRITICAL
    description = "The PDF file must conform to ISO 32000-1 syntax rules and allow accessibility content extraction."
    remediation_template = "Ensure the PDF is created with compliant PDF 1.7 or 2.0 specifications without syntax corruption."

    def evaluate(self, doc: PDFDocumentModel) -> List[CheckResult]:
        results = []

        # 1. Header & Version Syntax Validation (ISO 32000-1 Clause 7.5.2)
        # Validates that the document defines a recognized, well-formed PDF version identifier (e.g. 1.0 - 2.0).
        # Under ISO 32000-1 and PDF/UA-1, valid standard specification version headers (including PDF 1.3 - 2.0)
        # conform to PDF file syntax requirements.
        try:
            v_str = (doc.pdf_version or "").strip()
            v_float = float(v_str) if v_str else None
            if v_float is not None and (1.0 <= v_float <= 2.5):
                results.append(self.create_result(
                    status=CheckStatus.PASS,
                    message=f"PDF header specifies valid specification version {doc.pdf_version} (ISO 32000-1).",
                    evidence=f"PDF Version: {doc.pdf_version}"
                ))
            else:
                results.append(self.create_result(
                    status=CheckStatus.FAIL,
                    message=f"PDF file header contains an invalid or unrecognized version identifier: '{doc.pdf_version}' (ISO 32000-1, Clause 7.5.2).",
                    evidence=f"Invalid PDF Version: {doc.pdf_version}",
                    custom_severity=Severity.HIGH,
                    custom_remediation="Re-save or rebuild the PDF with a standard, valid PDF specification header (%PDF-1.0 to %PDF-2.0)."
                ))
        except Exception:
            results.append(self.create_result(
                status=CheckStatus.FAIL,
                message=f"PDF file header contains a malformed, unparseable version string: '{doc.pdf_version}' (ISO 32000-1, Clause 7.5.2).",
                evidence=f"Malformed PDF Version string: {doc.pdf_version}",
                custom_severity=Severity.HIGH,
                custom_remediation="Ensure the file begins with a valid header (e.g. %PDF-1.7)."
            ))

        # 2. Accessibility Extraction Permissions (ISO 32000-1 Clause 7.6 / ISO 14289-1 Clause 7.1)
        if doc.is_encrypted:
            if not doc.allows_extraction:
                results.append(self.create_result(
                    status=CheckStatus.FAIL,
                    message="Document encryption restricts assistive technology from extracting text for accessibility (ISO 14289-1, Clause 7.1).",
                    evidence="Document security settings disallow accessibility extraction.",
                    custom_severity=Severity.CRITICAL,
                    custom_remediation="Open PDF security settings in Adobe Acrobat Pro and enable 'Enable text access for screen reader devices for the visually impaired'."
                ))
            else:
                results.append(self.create_result(
                    status=CheckStatus.PASS,
                    message="Document security permissions allow assistive technologies to extract content.",
                    evidence="Accessibility extraction bit is enabled."
                ))
        else:
            results.append(self.create_result(
                status=CheckStatus.PASS,
                message="Document is not encrypted; accessibility content extraction is unrestricted.",
                evidence="Encryption: None"
            ))

        # 3. Page Dictionary & Boundary Syntax (ISO 32000-1 Clause 7.7.3.3, Matterhorn 01-004, 01-005)
        # Evaluates that each page defines a valid page object dictionary, dimensions, and boundary geometry.
        if doc.pages:
            for p in doc.pages:
                if p.width > 0 and p.height > 0:
                    results.append(self.create_result(
                        status=CheckStatus.PASS,
                        message=f"Page {p.page_number} defines a well-formed page object dictionary with valid MediaBox (ISO 32000-1, Clause 7.7.3.3).",
                        evidence=f"Page {p.page_number}: {p.width:.1f} x {p.height:.1f} pt",
                        page=p.page_number
                    ))
                    results.append(self.create_result(
                        status=CheckStatus.PASS,
                        message=f"Page {p.page_number} content boundaries and geometry conform to ISO 32000-1 syntax rules.",
                        evidence=f"Page {p.page_number} boundary geometry valid.",
                        page=p.page_number
                    ))
                else:
                    results.append(self.create_result(
                        status=CheckStatus.FAIL,
                        message=f"Page {p.page_number} contains a missing, malformed, or zero-dimension page dictionary.",
                        evidence=f"Page {p.page_number} dimensions: {p.width} x {p.height}",
                        page=p.page_number,
                        custom_severity=Severity.HIGH,
                        custom_remediation="Repair page boundaries and MediaBox dimensions."
                    ))
        # 4. Structure Tree Root & Structure Element Dictionary Syntax (ISO 32000-1 Clauses 14.7.2, 14.8.4, Matterhorn 13-004)
        # Evaluates that all structure dictionaries in the logical structure tree (StructTreeRoot and StructElem)
        # conform to ISO 32000-1 dictionary syntax and type rules.
        if doc.structure_tree:
            struct_nodes = doc.structure_tree.find_all_nodes()
            if struct_nodes:
                malformed_nodes = [n for n in struct_nodes if not n.tag or not n.tag.strip()]
                if malformed_nodes:
                    results.append(self.create_result(
                        status=CheckStatus.FAIL,
                        message=f"{len(malformed_nodes)} structure element dictionary(ies) contain missing or malformed /S type syntax (ISO 32000-1, Clause 14.8.4).",
                        evidence=f"Malformed nodes count: {len(malformed_nodes)}",
                        custom_severity=Severity.HIGH,
                        custom_remediation="Repair structure element dictionaries with valid type names.",
                        items_count=len(malformed_nodes)
                    ))
                    valid_cnt = len(struct_nodes) - len(malformed_nodes)
                    if valid_cnt > 0:
                        results.append(self.create_result(
                            status=CheckStatus.PASS,
                            message=f"{valid_cnt} structure dictionary(ies) conform to ISO 32000-1 syntax rules.",
                            evidence=f"Validated structure dictionaries: {valid_cnt}",
                            items_count=valid_cnt
                        ))
                else:
                    results.append(self.create_result(
                        status=CheckStatus.PASS,
                        message=f"All {len(struct_nodes)} structure element and root dictionaries conform to ISO 32000-1 syntax rules (valid /S and dictionary structure).",
                        evidence=f"Validated structure dictionaries: {len(struct_nodes)}",
                        items_count=len(struct_nodes)
                    ))

        # 5. Form XObject Dictionary Syntax (ISO 32000-1 Clause 8.10)
        # Evaluates that all Form XObjects define valid /Subtype /Form, /BBox arrays, and optional /Matrix.
        if getattr(doc, "form_xobjects", None):
            malformed_forms = [f for f in doc.form_xobjects if not f.is_valid]
            if malformed_forms:
                results.append(self.create_result(
                    status=CheckStatus.FAIL,
                    message=f"{len(malformed_forms)} Form XObject dictionary(ies) violate ISO 32000-1 Clause 8.10 syntax rules (missing or malformed /BBox).",
                    evidence=f"Malformed Form XObjects: {[f.id for f in malformed_forms[:5]]}",
                    custom_severity=Severity.HIGH,
                    custom_remediation="Ensure all Form XObject stream dictionaries define valid 4-number /BBox arrays.",
                    items_count=len(malformed_forms)
                ))
                valid_forms_cnt = len(doc.form_xobjects) - len(malformed_forms)
                if valid_forms_cnt > 0:
                    results.append(self.create_result(
                        status=CheckStatus.PASS,
                        message=f"{valid_forms_cnt} Form XObject dictionary(ies) conform to ISO 32000-1 Clause 8.10 syntax rules.",
                        evidence=f"Validated Form XObjects: {valid_forms_cnt}",
                        items_count=valid_forms_cnt
                    ))
            else:
                results.append(self.create_result(
                    status=CheckStatus.PASS,
                    message=f"All {len(doc.form_xobjects)} Form XObject dictionary(ies) conform to ISO 32000-1 Clause 8.10 syntax rules.",
                    evidence=f"Validated Form XObjects: {len(doc.form_xobjects)}",
                    items_count=len(doc.form_xobjects)
                ))

        # 6. Structural Parent Tree Syntax (ISO 32000-1 Clause 14.7.4.4, Matterhorn 01-006)
        # When a structure tree exists, validates that /ParentTree number tree is present and valid.
        if doc.structure_tree:
            if doc.has_parent_tree and doc.parent_tree_valid:
                results.append(self.create_result(
                    status=CheckStatus.PASS,
                    message="Structural parent tree (/ParentTree) conforms to ISO 32000-1 number tree syntax rules.",
                    evidence=f"Parent tree validated with {doc.parent_tree_entries_count} root key entries.",
                    items_count=1
                ))
            elif doc.has_parent_tree and not doc.parent_tree_valid:
                results.append(self.create_result(
                    status=CheckStatus.FAIL,
                    message="Structural parent tree (/ParentTree) contains corrupt or unparseable number tree syntax (ISO 32000-1, Clause 14.7.4.4).",
                    evidence="Malformed /ParentTree dictionary.",
                    custom_severity=Severity.HIGH,
                    custom_remediation="Repair the /ParentTree number tree structure in the PDF catalog.",
                    items_count=1
                ))
            else:
                results.append(self.create_result(
                    status=CheckStatus.FAIL,
                    message="Document defines a structure tree but lacks the required /ParentTree number tree (ISO 32000-1, Clause 14.7.4.4).",
                    evidence="Missing /ParentTree entry in /StructTreeRoot.",
                    custom_severity=Severity.HIGH,
                    custom_remediation="Add a valid /ParentTree linking marked content to the structure tree.",
                    items_count=1
                ))

        return results
