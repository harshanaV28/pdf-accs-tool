"""
Tests for Quality Checkpoints Aggregation & Presentation Layer.
Verifies that existing and newly implemented engine findings
are correctly mapped and presented in the Quality tab without duplicate engine rules.
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
    """Verify all 16 defined Quality checkpoints map to registered engine rule IDs."""
    expected_categories = [
        "Validity of document title",
        "Artifacted content on page body",
        "Tagged text consists of only whitespace",
        "Tagged content exists outside the page boundaries",
        "Presence of headings",
        "Presence of bookmarks",
        '"TOCI" elements contain "Link" elements',
        '"TOCI" elements correctly linked to headings',
        "Validity of alternative texts",
        "Alternative text on text elements",
        'Completeness of "Link" elements',
        'Formal correctness of "LI" elements',
        'Completeness of "Table" elements',
        '"Note" elements are referenced',
        '"Note" elements contain "Lbl" elements',
        '"P" elements contain "Note" elements',
    ]
    assert CheckpointsView.QUALITY_CATEGORIES == expected_categories
    assert len(CheckpointsView.QUALITY_CATEGORIES) == 16

    for cat in expected_categories:
        assert cat in CheckpointsView.QUALITY_RULE_MAPPINGS
        rule_ids = CheckpointsView.QUALITY_RULE_MAPPINGS[cat]
        assert len(rule_ids) > 0


def test_quality_checkpoints_view_aggregation(qapp):
    """Verify Quality matrix accurately counts findings mapped from existing and new engine checks."""
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
        # Validity of document title
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
        # Presence of headings
        CheckResult(
            check_id="QUAL-HEAD-001",
            name="Heading Hierarchy Integrity",
            category="Heading Structure",
            standard="Quality",
            status=CheckStatus.WARNING,
            severity=Severity.MEDIUM,
            message="Skipped heading level"
        ),
        # Completeness of "Link" elements
        CheckResult(
            check_id="QUAL-LINK-001",
            name="Meaningful Link Labels",
            category="Link Quality",
            standard="Quality",
            status=CheckStatus.PASS,
            severity=Severity.LOW,
            message="All links meaningful"
        ),
        # Completeness of "Table" elements
        CheckResult(
            check_id="QUAL-TABLE-001",
            name="Table Regularity & Symmetry",
            category="Table Quality",
            standard="Quality",
            status=CheckStatus.PASS,
            severity=Severity.LOW,
            message="Tables regular"
        ),
        # Tagged content exists outside the page boundaries
        CheckResult(
            check_id="QUAL-BOUND-001",
            name="Tagged Content Page Boundaries",
            category="Content Quality",
            standard="Quality",
            status=CheckStatus.PASS,
            severity=Severity.HIGH,
            message="All content in bounds"
        ),
    ]

    report = AuditReport(document_info={"filename": doc.filename}, results=results)

    view = CheckpointsView()
    view.update_report(report, doc)

    # 1. Validity of document title (row 0): 1 passed (META-002)
    item_title_name = view.table_quality.item(0, 0).text()
    item_title_pass = view.table_quality.item(0, 1).text()
    item_title_warn = view.table_quality.item(0, 2).text()
    item_title_fail = view.table_quality.item(0, 3).text()
    assert "✅" in item_title_name
    assert item_title_pass == "1"
    assert item_title_warn == "-"
    assert item_title_fail == "-"

    # 4. Tagged content exists outside the page boundaries (row 3): 1 passed
    item_bound_name = view.table_quality.item(3, 0).text()
    item_bound_pass = view.table_quality.item(3, 1).text()
    assert "✅" in item_bound_name
    assert item_bound_pass == "1"

    # 5. Presence of headings (row 4): 1 warned (QUAL-HEAD-001)
    item_head_name = view.table_quality.item(4, 0).text()
    item_head_pass = view.table_quality.item(4, 1).text()
    item_head_warn = view.table_quality.item(4, 2).text()
    item_head_fail = view.table_quality.item(4, 3).text()
    assert "⚠️" in item_head_name
    assert item_head_pass == "-"
    assert item_head_warn == "1"
    assert item_head_fail == "-"

    # Unpopulated checkpoint shows '-' and '⊘' (e.g. row 6: TOCI elements contain Link elements)
    item_toci_name = view.table_quality.item(6, 0).text()
    item_toci_pass = view.table_quality.item(6, 1).text()
    item_toci_warn = view.table_quality.item(6, 2).text()
    item_toci_fail = view.table_quality.item(6, 3).text()
    assert "⊘" in item_toci_name
    assert item_toci_pass == "-"
    assert item_toci_warn == "-"
    assert item_toci_fail == "-"


def test_detailed_results_filter_by_rule_ids(qapp):
    """Verify DetailedResultsView can filter directly by rule IDs when navigating from Quality checkpoint."""
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

    # Filter by "Validity of document title" mapped rule IDs
    title_rules = CheckpointsView.QUALITY_RULE_MAPPINGS["Validity of document title"]
    view.filter_by_rule_ids(title_rules, standard="All Standards", category_label="Validity of document title")

    assert len(view.filtered_findings) == 1
    assert view.filtered_findings[0].check_id == "PDFUA-META-002"
