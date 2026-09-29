"""
End-to-End Tests with Synthetic PDFs
Tests document parsing, rule engine evaluation, and report aggregation on real PDF files.
"""

import os
import pytest
from scripts.generate_sample_pdfs import generate_samples
from src.pdf_inspector.core.document_parser import DocumentParser
from src.pdf_inspector.engine.runner import AuditRunner
from src.pdf_inspector.core.models import CheckStatus


@pytest.fixture(scope="session")
def sample_pdf_paths(tmp_path_factory):
    out_dir = tmp_path_factory.mktemp("pdf_samples")
    acc_path, inacc_path = generate_samples(str(out_dir))
    return acc_path, inacc_path


def test_accessible_pdf_audit(sample_pdf_paths):
    acc_path, _ = sample_pdf_paths
    parser = DocumentParser(acc_path)
    doc = parser.parse()

    assert doc.is_tagged is True
    assert doc.language == "en-US"
    assert doc.display_doc_title is True
    assert doc.pdfua_identifier_present is True
    assert doc.structure_tree is not None

    runner = AuditRunner()
    report = runner.run(doc)

    assert report.total_failed == 0
    assert report.compliance_score >= 85.0


def test_inaccessible_pdf_audit(sample_pdf_paths):
    _, inacc_path = sample_pdf_paths
    parser = DocumentParser(inacc_path)
    doc = parser.parse()

    assert doc.is_tagged is False
    assert doc.language is None

    runner = AuditRunner()
    report = runner.run(doc)

    assert report.total_failed > 0
    failures = [r for r in report.results if r.status == CheckStatus.FAIL]
    failed_ids = [f.check_id for f in failures]

    # Must catch untagged, missing title, missing language, missing alt text
    assert "PDFUA-CONTENT-001" in failed_ids  # Tagged PDF check
    assert "PDFUA-LANG-001" in failed_ids     # Language check
    assert "PDFUA-SETTINGS-001" in failed_ids # DisplayDocTitle check
