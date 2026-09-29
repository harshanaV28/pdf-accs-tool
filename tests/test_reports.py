"""
Unit tests for Report Generators (PDF, HTML, JSON, CSV)
"""

import os
import json
import pytest
from src.pdf_inspector.core.models import AuditReport, CheckResult, CheckStatus, Severity
from src.pdf_inspector.reporting.pdf_report import PDFReportGenerator
from src.pdf_inspector.reporting.html_report import HTMLReportGenerator
from src.pdf_inspector.reporting.json_exporter import JSONExporter, CSVExporter


@pytest.fixture
def sample_report():
    doc_info = {
        "filename": "sample_audit.pdf",
        "filepath": "/path/to/sample_audit.pdf",
        "filesize": 102400,
        "page_count": 3,
        "pdf_version": "1.7",
        "title": "Accessibility Sample",
        "language": "en",
        "is_tagged": True,
        "pdfua_declared": True,
    }
    results = [
        CheckResult("PDFUA-001", "Tagged PDF", "Content", "PDF/UA", CheckStatus.PASS, Severity.CRITICAL, "Passed tagged check"),
        CheckResult("PDFUA-002", "Alt Text", "Alternative Descriptions", "PDF/UA", CheckStatus.FAIL, Severity.HIGH, "Missing alt text on Figure", page=2),
        CheckResult("WCAG-2.4", "Headings", "2.4 Navigable", "WCAG", CheckStatus.WARNING, Severity.MEDIUM, "Heading skip detected", page=1),
    ]
    return AuditReport(document_info=doc_info, results=results)


def test_pdf_report_generation(sample_report, tmp_path):
    pdf_out = os.path.join(tmp_path, "report.pdf")
    PDFReportGenerator.generate(sample_report, pdf_out)
    assert os.path.exists(pdf_out)
    assert os.path.getsize(pdf_out) > 1000


def test_html_report_generation(sample_report, tmp_path):
    html_out = os.path.join(tmp_path, "report.html")
    HTMLReportGenerator.generate(sample_report, html_out)
    assert os.path.exists(html_out)
    with open(html_out, "r", encoding="utf-8") as f:
        content = f.read()
        assert "PDF Accessibility Audit Report" in content
        assert "sample_audit.pdf" in content
        assert "PDFUA-002" in content


def test_json_and_csv_export(sample_report, tmp_path):
    json_out = os.path.join(tmp_path, "report.json")
    JSONExporter.export(sample_report, json_out)
    assert os.path.exists(json_out)
    with open(json_out, "r", encoding="utf-8") as f:
        data = json.load(f)
        assert data["application"] == "PDF Accessibility Inspector"
        assert len(data["findings"]) == 3

    csv_out = os.path.join(tmp_path, "report.csv")
    CSVExporter.export(sample_report, csv_out)
    assert os.path.exists(csv_out)
    with open(csv_out, "r", encoding="utf-8") as f:
        csv_text = f.read()
        assert "PDFUA-001" in csv_text
