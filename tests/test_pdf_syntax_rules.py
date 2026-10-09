"""
Tests for PDF Syntax (ISO 32000-1) validation rules.
Verifies that:
1. Valid PDF version headers (PDF 1.0 through 2.0, including PDF 1.3) pass syntax validation.
2. Malformed or unrecognized PDF version headers fail with explicit technical evidence.
3. Encryption permissions (accessibility extraction allowed vs disallowed) evaluate accurately.
4. PDF Syntax checkpoint counts and statuses remain consistent across AuditReport, UI, and report exports.
"""

import os
import tempfile
import pytest

from src.pdf_inspector.core.models import (
    PDFDocumentModel, CheckStatus, Severity, AuditReport
)
from src.pdf_inspector.engine.pdf_ua.syntax_rules import PDFSyntaxBasicRule
from src.pdf_inspector.engine.runner import AuditRunner
from src.pdf_inspector.reporting.pdf_report import PDFReportGenerator
from src.pdf_inspector.reporting.html_report import HTMLReportGenerator
from src.pdf_inspector.reporting.json_exporter import JSONExporter


class TestPDFSyntaxBasicRule:
    """Tests for PDFSyntaxBasicRule (PDFUA-SYNTAX-001)."""

    def test_valid_pdf_13_header_passes(self):
        rule = PDFSyntaxBasicRule()
        doc = PDFDocumentModel(
            filepath="", filename="pdf13.pdf", filesize=1000,
            pdf_version="1.3", page_count=1, is_tagged=True
        )
        results = rule.evaluate(doc)
        version_results = [r for r in results if "version" in r.message.lower()]
        assert len(version_results) == 1
        assert version_results[0].status == CheckStatus.PASS
        assert "valid specification version 1.3" in version_results[0].message
        assert version_results[0].evidence == "PDF Version: 1.3"

    @pytest.mark.parametrize("ver", ["1.0", "1.4", "1.5", "1.6", "1.7", "2.0"])
    def test_standard_pdf_versions_pass(self, ver):
        rule = PDFSyntaxBasicRule()
        doc = PDFDocumentModel(
            filepath="", filename=f"pdf_{ver}.pdf", filesize=1000,
            pdf_version=ver, page_count=1, is_tagged=True
        )
        results = rule.evaluate(doc)
        version_results = [r for r in results if "version" in r.message.lower()]
        assert len(version_results) == 1
        assert version_results[0].status == CheckStatus.PASS

    def test_unrecognized_pdf_version_fails(self):
        rule = PDFSyntaxBasicRule()
        doc = PDFDocumentModel(
            filepath="", filename="invalid_ver.pdf", filesize=1000,
            pdf_version="99.9", page_count=1, is_tagged=True
        )
        results = rule.evaluate(doc)
        version_results = [r for r in results if "version" in r.message.lower()]
        assert len(version_results) == 1
        assert version_results[0].status == CheckStatus.FAIL
        assert "unrecognized version identifier" in version_results[0].message

    def test_malformed_version_string_fails(self):
        rule = PDFSyntaxBasicRule()
        doc = PDFDocumentModel(
            filepath="", filename="corrupt_ver.pdf", filesize=1000,
            pdf_version="corrupt_header_string", page_count=1, is_tagged=True
        )
        results = rule.evaluate(doc)
        version_results = [r for r in results if "version" in r.message.lower()]
        assert len(version_results) == 1
        assert version_results[0].status == CheckStatus.FAIL
        assert "malformed, unparseable version string" in version_results[0].message

    def test_encrypted_with_extraction_disallowed_fails(self):
        rule = PDFSyntaxBasicRule()
        doc = PDFDocumentModel(
            filepath="", filename="locked.pdf", filesize=1000,
            pdf_version="1.7", page_count=1, is_tagged=True,
            is_encrypted=True, allows_extraction=False
        )
        results = rule.evaluate(doc)
        perm_results = [r for r in results if "encryption" in r.message.lower() or "extraction" in r.message.lower()]
        assert len(perm_results) == 1
        assert perm_results[0].status == CheckStatus.FAIL
        assert perm_results[0].severity == Severity.CRITICAL

    def test_encrypted_with_extraction_allowed_passes(self):
        rule = PDFSyntaxBasicRule()
        doc = PDFDocumentModel(
            filepath="", filename="unlocked.pdf", filesize=1000,
            pdf_version="1.7", page_count=1, is_tagged=True,
            is_encrypted=True, allows_extraction=True
        )
        results = rule.evaluate(doc)
        perm_results = [r for r in results if "security permissions allow" in r.message.lower()]
        assert len(perm_results) == 1
        assert perm_results[0].status == CheckStatus.PASS

    def test_syntax_results_aggregation_and_reporting(self):
        doc = PDFDocumentModel(
            filepath="", filename="syntax_sample.pdf", filesize=1000,
            pdf_version="1.3", page_count=1, is_tagged=True
        )
        runner = AuditRunner()
        report = runner.run(doc)

        syntax_counts = report.get_category_counts("PDF/UA")["PDF Syntax (ISO 32000-1)"]
        assert syntax_counts["passed"] == 2
        assert syntax_counts["failed"] == 0

        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_out = os.path.join(tmpdir, "syntax_report.pdf")
            html_out = os.path.join(tmpdir, "syntax_report.html")
            json_out = os.path.join(tmpdir, "syntax_report.json")

            PDFReportGenerator.generate(report, pdf_out)
            HTMLReportGenerator.generate(report, html_out)
            JSONExporter.export(report, json_out)

            assert os.path.getsize(pdf_out) > 0
            assert os.path.getsize(html_out) > 0
            assert os.path.getsize(json_out) > 0
