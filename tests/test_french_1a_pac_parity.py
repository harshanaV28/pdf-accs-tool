"""
PAC Parity Verification Test for French 1A_7654-1-17.pdf
Validates that our accessibility inspector matches the official axes4 PAC validation results
and checkpoint counts for untagged image-based PDFs.
"""

import os
import pytest
from src.pdf_inspector.core.document_parser import DocumentParser
from src.pdf_inspector.engine.runner import AuditRunner
from src.pdf_inspector.core.models import CheckStatus

TEST_PDF = os.path.join(os.path.dirname(__file__), "..", "test_samples", "French 1A_7654-1-17.pdf")


@pytest.mark.skipif(not os.path.exists(TEST_PDF), reason="French 1A sample PDF not found")
def test_french_1a_pac_parity_counts():
    doc = DocumentParser(TEST_PDF).parse()
    assert doc is not None
    assert doc.page_count == 17
    assert doc.is_tagged is False
    assert len(doc.images) == 288
    assert len(doc.fonts) == 0

    runner = AuditRunner()
    report = runner.run(doc)
    pdfua = report.get_category_counts("PDF/UA")

    # 1. PDF Syntax: 36 passed (17 pages * 2 page-level checks + 2 document-level checks), 0 failed
    assert pdfua["PDF Syntax (ISO 32000-1)"]["passed"] == 36
    assert pdfua["PDF Syntax (ISO 32000-1)"]["failed"] == 0
    assert pdfua["PDF Syntax (ISO 32000-1)"]["warned"] == 0

    # 2. Fonts: 0 passed, 0 failed, 0 warned (renders as '-' in PAC Matrix)
    assert pdfua["Fonts"]["passed"] == 0
    assert pdfua["Fonts"]["failed"] == 0
    assert pdfua["Fonts"]["warned"] == 0

    # 3. Content: 0 passed, 288 failed (all 288 untagged images fail Checkpoint 01), 0 warned
    assert pdfua["Content"]["passed"] == 0
    assert pdfua["Content"]["failed"] == 288
    assert pdfua["Content"]["warned"] == 0

    # 4. Embedded Files: 0 passed, 0 failed, 0 warned (renders as '-' in PAC Matrix)
    assert pdfua["Embedded Files"]["passed"] == 0
    assert pdfua["Embedded Files"]["failed"] == 0
    assert pdfua["Embedded Files"]["warned"] == 0

    # 5. Natural language: 0 passed, 1 failed (missing /Lang), 0 warned
    assert pdfua["Natural language"]["passed"] == 0
    assert pdfua["Natural language"]["failed"] == 1
    assert pdfua["Natural language"]["warned"] == 0

    # 6. Logical structure categories: not applicable on untagged document (all 0 / '-' in PAC)
    assert pdfua["Structure elements"]["passed"] == 0
    assert pdfua["Structure elements"]["failed"] == 0
    assert pdfua["Structure elements"]["warned"] == 0

    assert pdfua["Structure tree"]["passed"] == 0
    assert pdfua["Structure tree"]["failed"] == 0
    assert pdfua["Structure tree"]["warned"] == 0

    assert pdfua["Role mapping"]["passed"] == 0
    assert pdfua["Role mapping"]["failed"] == 0
    assert pdfua["Role mapping"]["warned"] == 0
