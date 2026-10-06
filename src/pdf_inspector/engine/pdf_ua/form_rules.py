"""
Form Field Accessibility Rules (ISO 14289-1:2014, Clause 7.18 & Matterhorn Protocol Checkpoint 08)
Verifies that interactive form fields define accessible names (/TU tooltip), are properly tagged,
and have valid field names.
"""

from typing import List
from ..rule_base import BaseRule
from ...core.models import PDFDocumentModel, CheckResult, CheckStatus, Severity


class FormFieldAccessibilityRule(BaseRule):
    rule_id = "PDFUA-FORM-001"
    name = "Form Field Tooltips & Names"
    category = "Forms"
    standard = "PDF/UA"
    severity = Severity.HIGH
    description = "Every interactive form field must possess an accessible tooltip/description (/TU) and a valid field name (ISO 14289-1, Clause 7.18 / Matterhorn 08-001, 08-003)."
    remediation_template = "In Acrobat Pro, open Prepare Form tool, double click each field, and under 'Tooltip' enter a descriptive label."

    def evaluate(self, doc: PDFDocumentModel) -> List[CheckResult]:
        results = []
        if not doc.form_fields:
            results.append(self.create_result(
                status=CheckStatus.PASS,
                message="No interactive form fields found in document.",
                evidence="Form field count: 0",
                items_count=0
            ))
            return results

        missing_tu = []
        unnamed_fields = []

        for f in doc.form_fields:
            if not f.tooltip or not f.tooltip.strip():
                missing_tu.append(f)
            if not f.name or f.name.strip() in ("", "UnnamedField"):
                unnamed_fields.append(f)

        if missing_tu:
            for f in missing_tu:
                results.append(self.create_result(
                    status=CheckStatus.FAIL,
                    message=f"Form field '{f.name}' on page {f.page} has no tooltip/description (/TU).",
                    evidence=f"Field '{f.name}' (Type: {f.field_type}) on page {f.page} lacks /TU entry.",
                    page=f.page,
                    bounding_box=f.bbox,
                    object_reference=f"FormField '{f.name}'",
                    custom_severity=Severity.HIGH,
                    custom_remediation="Add a descriptive tooltip (/TU) to the form field in Acrobat Form Editor.",
                    items_count=1
                ))

        if unnamed_fields:
            for f in unnamed_fields:
                results.append(self.create_result(
                    status=CheckStatus.FAIL,
                    message=f"Form field on page {f.page} lacks a valid field name (/T).",
                    evidence=f"Field on page {f.page} has empty or missing name.",
                    page=f.page,
                    bounding_box=f.bbox,
                    object_reference="FormField",
                    custom_severity=Severity.HIGH,
                    custom_remediation="Assign a descriptive name (/T) to the form field.",
                    items_count=1
                ))

        failing_field_ids = set(id(f) for f in missing_tu) | set(id(f) for f in unnamed_fields)
        passed_count = len(doc.form_fields) - len(failing_field_ids)
        if passed_count > 0:
            results.append(self.create_result(
                status=CheckStatus.PASS,
                message=f"{passed_count} of {len(doc.form_fields)} form field(s) have valid tooltip descriptions and names.",
                evidence=f"Accessible form fields: {passed_count}/{len(doc.form_fields)}",
                items_count=passed_count
            ))

        return results
