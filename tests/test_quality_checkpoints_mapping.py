"""
Tests for Phase 9A Quality Checkpoints Aggregation & Presentation Layer.
Verifies that existing engine findings (PDF/UA, WCAG, Quality, AI) are correctly
mapped and presented in the Quality tab without duplicate engine rules or normative status mutation.
"""

import pytest
from PySide6.QtWidgets import QApplication
from src.pdf_inspector.core.models import PDFDocumentModel, AuditReport, CheckResult, CheckStatus, Severity
from src.pdf_inspector.ui.views.checkpoints_view import CheckpointsView
from src.pdf_inspector.ui.views.detailed_results_view import DetailedResultsView


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_quality_category_rule_mappings_coverage():
    """Verify all defined Quality categories map to registered engine rule IDs."""
    expected_categories = [
        "Document Quality",
        "Heading Structure",
        "Content Quality",
        "Alternative Text Quality",
        "Link & Navigation Quality",
        "List Quality",
        "Table Quality",
        "Structure & Note Quality"
    ]
    assert CheckpointsView.QUALITY_CATEGORIES == expected_categories

    for cat in expected_categories:
        assert cat in CheckpointsView.QUALITY_RULE_MAPPINGS
        rule_ids = CheckpointsView.QUALITY_RULE_MAPPINGS[cat]
        assert len(rule_ids) > 0


def test_quality_checkpoints_view_aggregation(qapp):
    """Verify Quality matrix accurately counts findings mapped from existing engine checks."""
    doc = PDFDocumentModel(
        filepath="/test/sample.pdf",
        filename="sample.pdf",
        filesize=1024,
        pdf_version="1.7",
        page_count=5,
        title="Valid Title",
        is_tagged=True
    )

    results = [
        # Document Quality
        CheckResult(
            check_id="PDFUA-META-002",
            name="XMP Document Title",
            category="Metadata",
            standard="PDF/UA",
            status=CheckStatus.PASS,
            severity=Severity.HIGH,
            message="Title is valid"
        ),
        CheckResult(
            check_id="PDFUA-SETTINGS-001",
            name="DisplayDocTitle",
            category="Document settings",
            standard="PDF/UA",
            status=CheckStatus.FAIL,
            severity=Severity.HIGH,
            message="DisplayDocTitle is false"
        ),
        # Heading Structure
        CheckResult(
            check_id="QUAL-HEAD-001",
            name="Heading Hierarchy Integrity",
            category="Heading Structure",
            standard="Quality",
            status=CheckStatus.WARNING,
            severity=Severity.MEDIUM,
            message="Skipped heading level"
        ),
        # Link Quality
        CheckResult(
            check_id="QUAL-LINK-001",
            name="Meaningful Link Labels",
            category="Link Quality",
            standard="Quality",
            status=CheckStatus.PASS,
            severity=Severity.LOW,
            message="All links meaningful"
        ),
        # Table Quality
        CheckResult(
            check_id="QUAL-TABLE-001",
            name="Table Regularity & Symmetry",
            category="Table Quality",
            standard="Quality",
            status=CheckStatus.PASS,
            severity=Severity.LOW,
            message="Tables regular"
        ),
    ]

    report = AuditReport(document_info={"filename": doc.filename}, results=results)

    view = CheckpointsView()
    view.update_report(report, doc)

    # Document Quality row (index 0): 1 passed (META-002), 1 failed (SETTINGS-001)
    item_doc_q_name = view.table_quality.item(0, 0).text()
    item_doc_q_pass = view.table_quality.item(0, 1).text()
    item_doc_q_warn = view.table_quality.item(0, 2).text()
    item_doc_q_fail = view.table_quality.item(0, 3).text()
    assert "❌" in item_doc_q_name
    assert item_doc_q_pass == "1"
    assert item_doc_q_warn == "-"
    assert item_doc_q_fail == "1"

    # Heading Structure row (index 1): 1 warned (QUAL-HEAD-001)
    item_head_q_name = view.table_quality.item(1, 0).text()
    item_head_q_pass = view.table_quality.item(1, 1).text()
    item_head_q_warn = view.table_quality.item(1, 2).text()
    item_head_q_fail = view.table_quality.item(1, 3).text()
    assert "⚠️" in item_head_q_name
    assert item_head_q_pass == "-"
    assert item_head_q_warn == "1"
    assert item_head_q_fail == "-"


def test_detailed_results_filter_by_rule_ids(qapp):
    """Verify DetailedResultsView can filter directly by rule IDs when navigating from Quality category."""
    results = [
        CheckResult(
            check_id="PDFUA-META-002",
            name="XMP Document Title",
            category="Metadata",
            standard="PDF/UA",
            status=CheckStatus.PASS,
            severity=Severity.HIGH,
            message="Title is valid"
        ),
        CheckResult(
            check_id="PDFUA-FIG-001",
            name="Figure Bounding Box",
            category="Graphics",
            standard="PDF/UA",
            status=CheckStatus.PASS,
            severity=Severity.HIGH,
            message="Figure BBox valid"
        ),
        CheckResult(
            check_id="QUAL-HEAD-001",
            name="Heading Hierarchy Integrity",
            category="Heading Structure",
            standard="Quality",
            status=CheckStatus.WARNING,
            severity=Severity.MEDIUM,
            message="Skipped heading level"
        ),
    ]

    view = DetailedResultsView()
    view.set_findings(results)
    assert len(view.filtered_findings) == 3

    # Filter by Document Quality mapped rule IDs
    doc_q_rules = CheckpointsView.QUALITY_RULE_MAPPINGS["Document Quality"]
    view.filter_by_rule_ids(doc_q_rules, standard="All Standards", category_label="Document Quality")

    assert len(view.filtered_findings) == 1
    assert view.filtered_findings[0].check_id == "PDFUA-META-002"
