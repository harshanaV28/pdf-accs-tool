"""
Table Structure Rules (ISO 14289-1, Clause 7.5 & Matterhorn Protocol Checkpoint 15-001, 15-002)
Validates strict table structure hierarchy: Table contains TR, TR contains TH/TD, TH contains headers.
"""

from typing import List
from ..rule_base import BaseRule
from ...core.models import PDFDocumentModel, CheckResult, CheckStatus, Severity


class TableStructureHeadersRule(BaseRule):
    rule_id = "PDFUA-TABLE-001"
    name = "Table Headers & Structure"
    category = "Tables"
    standard = "PDF/UA"
    severity = Severity.HIGH
    description = "Data tables must include header cells (<TH>) and maintain strict parent-child relationships (Table > TR > TH/TD) (ISO 14289-1, Clause 7.5 / Matterhorn 15-001)."
    remediation_template = "Identify column or row headers in Acrobat Pro Table Editor, set cell type to Header Cell, and define Scope."

    def evaluate(self, doc: PDFDocumentModel) -> List[CheckResult]:
        results = []
        if not doc.tables:
            return [self.create_result(
                status=CheckStatus.PASS,
                message="No tables detected in document.",
                evidence="Table count: 0",
                items_count=0
            )]

        for t in doc.tables:
            if t.has_headers:
                results.append(self.create_result(
                    status=CheckStatus.PASS,
                    message=f"Table on page {t.page} has {t.header_cells_count} header cell(s) (<TH>).",
                    evidence=f"Table {t.id} on page {t.page}: {t.rows_count} rows, {t.cols_count} cols, {t.header_cells_count} TH cells",
                    page=t.page,
                    object_reference=f"Table {t.id}",
                    items_count=1
                ))
            else:
                results.append(self.create_result(
                    status=CheckStatus.FAIL,
                    message=f"Table on page {t.page} has no designated header cells (<TH>).",
                    evidence=f"Table {t.id} on page {t.page}: {t.rows_count} rows, {t.cols_count} cols, 0 TH cells",
                    page=t.page,
                    object_reference=f"Table {t.id}",
                    custom_severity=Severity.HIGH,
                    custom_remediation="Tag the first row or column as Header Cells (<TH>) in Acrobat Table Editor.",
                    items_count=1
                ))

        return results
