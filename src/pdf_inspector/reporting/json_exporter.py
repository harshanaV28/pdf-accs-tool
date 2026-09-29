"""
JSON and CSV Audit Exporter
Exports AuditReport objects to structured machine-readable formats.
"""

import json
import csv
from typing import Dict, Any
from ..core.models import AuditReport


class JSONExporter:
    """Exports audit reports to formatted JSON."""

    @staticmethod
    def export(report: AuditReport, output_filepath: str):
        data: Dict[str, Any] = {
            "application": "PDF Accessibility Inspector",
            "version": "1.0.0",
            "generated_at": report.timestamp,
            "document": report.document_info,
            "summary": {
                "total_checks": len(report.results),
                "passed": report.total_passed,
                "warned": report.total_warned,
                "failed": report.total_failed,
                "manual_review": report.total_manual,
                "compliance_score_percent": report.compliance_score,
            },
            "category_breakdown": {
                "PDF/UA": report.get_category_counts("PDF/UA"),
                "WCAG": report.get_category_counts("WCAG"),
                "Quality": report.get_category_counts("Quality"),
                "AI": report.get_category_counts("AI"),
            },
            "findings": [r.to_dict() for r in report.results]
        }

        with open(output_filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)


class CSVExporter:
    """Exports audit findings to CSV format."""

    @staticmethod
    def export(report: AuditReport, output_filepath: str):
        fields = [
            "Check ID", "Rule Name", "Category", "Standard",
            "Status", "Severity", "Page", "Message",
            "Object Reference", "Evidence", "Remediation"
        ]

        with open(output_filepath, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(fields)
            for r in report.results:
                writer.writerow([
                    r.check_id,
                    r.name,
                    r.category,
                    r.standard,
                    r.status.value,
                    r.severity.value,
                    r.page or "Doc",
                    r.message,
                    r.object_reference,
                    r.evidence,
                    r.remediation
                ])
