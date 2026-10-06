"""
Tests for Row-Level Regression Comparator
Verifies classification logic (MATCH, STATUS_MISMATCH, MISSING_FROM_ENGINE,
ENGINE_ONLY, REFERENCE_ORACLE_OMISSION) with synthetic records.
"""

import pytest
from src.pdf_inspector.diagnostics.regression_comparator import (
    RowLevelComparator,
    NormalizedRecord,
    ComparisonClassification,
    ComparisonItem
)


def test_comparator_exact_match():
    comparator = RowLevelComparator()
    pac = [
        NormalizedRecord(pdf_id="PDF01", page=1, category="Fonts", check_name="Font Embedding", status="FAIL", source="PAC_EXCEL"),
        NormalizedRecord(pdf_id="PDF01", page=None, category="Document", check_name="Tagged PDF", status="PASS", source="PAC_EXCEL"),
    ]
    eng = [
        NormalizedRecord(pdf_id="PDF01", page=1, category="Fonts", check_name="Font Embedding", status="FAIL", source="ENGINE"),
        NormalizedRecord(pdf_id="PDF01", page=None, category="Document", check_name="Tagged PDF", status="PASS", source="ENGINE"),
    ]

    items = comparator.compare_pdf("PDF01", pac, eng)
    assert len(items) == 2
    assert all(item.classification == ComparisonClassification.MATCH for item in items)


def test_comparator_status_mismatch():
    comparator = RowLevelComparator()
    pac = [
        NormalizedRecord(pdf_id="PDF02", page=1, category="Document", check_name="Document Title", status="FAIL", source="PAC_EXCEL"),
    ]
    eng = [
        NormalizedRecord(pdf_id="PDF02", page=1, category="Document", check_name="Document Title", status="PASS", source="ENGINE"),
    ]

    items = comparator.compare_pdf("PDF02", pac, eng)
    assert len(items) == 1
    assert items[0].classification == ComparisonClassification.STATUS_MISMATCH
    assert "Status mismatch" in items[0].details


def test_comparator_missing_from_engine():
    comparator = RowLevelComparator()
    pac = [
        NormalizedRecord(pdf_id="PDF03", page=2, category="Images", check_name="Alternate Text", status="PASS", source="PAC_EXCEL"),
    ]
    eng = []

    items = comparator.compare_pdf("PDF03", pac, eng)
    assert len(items) == 1
    assert items[0].classification == ComparisonClassification.MISSING_FROM_ENGINE


def test_comparator_engine_only():
    comparator = RowLevelComparator()
    pac = []
    eng = [
        NormalizedRecord(pdf_id="PDF04", page=1, category="Content", check_name="Real Content Tagged", status="FAIL", source="ENGINE"),
    ]

    items = comparator.compare_pdf("PDF04", pac, eng)
    assert len(items) == 1
    assert items[0].classification == ComparisonClassification.ENGINE_ONLY


def test_comparator_reference_oracle_omission():
    comparator = RowLevelComparator()
    pac = [
        NormalizedRecord(pdf_id="PDF03", page=1, category="Fonts", check_name="Font Embedding", status="FAIL", source="PAC_EXCEL"),
    ]
    eng = [
        NormalizedRecord(pdf_id="PDF03", page=1, category="Fonts", check_name="Font Embedding", status="FAIL", source="ENGINE"),
        NormalizedRecord(pdf_id="PDF03", page=7, category="Fonts", check_name="Font Embedding", status="FAIL", evidence="Page: 7", source="ENGINE"),
    ]

    items = comparator.compare_pdf("PDF03", pac, eng)
    assert len(items) == 2
    p1_item = next(i for i in items if i.page == 1)
    p7_item = next(i for i in items if i.page == 7)

    assert p1_item.classification == ComparisonClassification.MATCH
    assert p7_item.classification == ComparisonClassification.REFERENCE_ORACLE_OMISSION


def test_comparator_scope_reconciliation_match():
    """Verifies that a document-scoped PAC row matches a page-scoped engine evaluation."""
    comparator = RowLevelComparator()
    pac = [
        NormalizedRecord(pdf_id="PDF01", page=None, category="Tables", check_name="Table Headers (TH)", status="PASS", source="PAC_EXCEL"),
    ]
    eng = [
        NormalizedRecord(pdf_id="PDF01", page=3, category="Tables", check_name="Table Headers (TH)", status="PASS", source="ENGINE"),
    ]

    items = comparator.compare_pdf("PDF01", pac, eng)
    assert len(items) == 1
    assert items[0].classification == ComparisonClassification.MATCH
    assert "Matched across scopes" in items[0].details


def test_comparator_scope_reconciliation_multiple_pages():
    """Verifies matching multiple document-scoped PAC rows against multiple page-scoped engine rows."""
    comparator = RowLevelComparator()
    pac = [
        NormalizedRecord(pdf_id="PDF01", page=None, category="Tables", check_name="Table Headers (TH)", status="PASS", source="PAC_EXCEL"),
        NormalizedRecord(pdf_id="PDF01", page=None, category="Tables", check_name="Table Headers (TH)", status="PASS", source="PAC_EXCEL"),
    ]
    eng = [
        NormalizedRecord(pdf_id="PDF01", page=1, category="Tables", check_name="Table Headers (TH)", status="PASS", source="ENGINE"),
        NormalizedRecord(pdf_id="PDF01", page=2, category="Tables", check_name="Table Headers (TH)", status="PASS", source="ENGINE"),
        NormalizedRecord(pdf_id="PDF01", page=3, category="Tables", check_name="Table Headers (TH)", status="PASS", source="ENGINE"),
    ]

    items = comparator.compare_pdf("PDF01", pac, eng)
    assert len(items) == 3
    matches = [i for i in items if i.classification == ComparisonClassification.MATCH]
    engine_only = [i for i in items if i.classification == ComparisonClassification.ENGINE_ONLY]
    assert len(matches) == 2
    assert len(engine_only) == 1


def test_comparator_scope_reconciliation_status_mismatch():
    """Verifies that differing statuses across scopes result in STATUS_MISMATCH."""
    comparator = RowLevelComparator()
    pac = [
        NormalizedRecord(pdf_id="PDF09", page=None, category="Tables", check_name="Table Headers (TH)", status="FAIL", source="PAC_EXCEL"),
    ]
    eng = [
        NormalizedRecord(pdf_id="PDF09", page=2, category="Tables", check_name="Table Headers (TH)", status="PASS", source="ENGINE"),
    ]

    items = comparator.compare_pdf("PDF09", pac, eng)
    assert len(items) == 1
    assert items[0].classification == ComparisonClassification.STATUS_MISMATCH
    assert "Status mismatch across scopes" in items[0].details


def test_comparator_rule_mappings():
    """Verifies canonical rule mappings for PDFUA-META-002 and PDFUA-ANNOT-002."""
    from src.pdf_inspector.diagnostics.regression_comparator import RULE_ID_TO_PAC_CHECK
    assert RULE_ID_TO_PAC_CHECK["PDFUA-META-002"] == ("Document", "Document Title")
    assert "PDFUA-META-001" not in RULE_ID_TO_PAC_CHECK
    assert RULE_ID_TO_PAC_CHECK["PDFUA-ANNOT-002"] == ("Annotations", "Tab Order")
