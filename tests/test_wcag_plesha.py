"""
Test script to run WCAG audit on Plesha PDF and verify exact counts.
"""

import os
import pytest
from src.pdf_inspector.core.document_parser import DocumentParser
from src.pdf_inspector.engine.runner import AuditRunner

PLESHA_PATH = os.path.expanduser(r"~\Downloads\Plesha_EngineeringMechanics_3e_Chap016_ISM_A11y_with_injected_alt (1) 2.pdf")


@pytest.mark.skipif(not os.path.exists(PLESHA_PATH), reason="Plesha PDF not in Downloads")
def test_plesha_wcag_audit():
    parser = DocumentParser(PLESHA_PATH)
    doc = parser.parse()
    assert doc is not None

    runner = AuditRunner()
    report = runner.run(doc)

    wcag_counts = report.get_category_counts("WCAG")

    # 1.1 Text Alternatives: 288 Figures + 3380 Formulas = 3668 total (2906 PASS, 762 FAIL)
    assert wcag_counts["1.1 Text Alternatives"]["passed"] == 2906
    assert wcag_counts["1.1 Text Alternatives"]["failed"] == 762

    # Check that zero-applicable categories report 0 / '-'
    assert wcag_counts.get("1.2 Time-based Media", {}).get("passed", 0) == 0
    assert wcag_counts.get("2.2 Enough Time", {}).get("passed", 0) == 0
    assert wcag_counts.get("2.3 Seizures and Physical Reactions", {}).get("passed", 0) == 0
    assert wcag_counts.get("2.5 Input Modalities", {}).get("passed", 0) == 0
    assert wcag_counts.get("3.2 Predictable", {}).get("passed", 0) == 0
    assert wcag_counts.get("4.1 Compatible", {}).get("passed", 0) == 540


@pytest.mark.skipif(not os.path.exists(PLESHA_PATH), reason="Plesha PDF not in Downloads")
def test_plesha_quality_audit():
    parser = DocumentParser(PLESHA_PATH)
    doc = parser.parse()
    assert doc is not None

    runner = AuditRunner()
    report = runner.run(doc)

    quality_counts = report.get_category_counts("Quality")
    assert quality_counts["Tagged text consists of only whitespace"]["warned"] == 4
    assert quality_counts["Formal correctness of \"LI\" elements"]["passed"] == 14
    assert quality_counts["Completeness of \"Table\" elements"]["passed"] == 6
