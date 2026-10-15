"""
GUI Quality Checkpoint Interaction and Navigation Test
Verifies:
1. Quality tab displays exactly 16 canonical PAC checkpoints in correct order.
2. Clicking a Quality checkpoint row opens Detailed Findings filtered to that checkpoint.
3. Automatically selects the first finding and navigates PDF canvas to its page/location.
4. Clicking a finding in Detailed Findings navigates the PDF canvas to the target page.
5. Tab switching across standards (PDF/UA, WCAG, Quality, AI) updates preview without kicking out of Checkpoints view.
"""

import os
import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from src.pdf_inspector.ui.main_window import MainWindow
from src.pdf_inspector.ui.views.checkpoints_view import CheckpointsView
from src.pdf_inspector.core.models import CheckResult, CheckStatus, Severity
from src.pdf_inspector.core.document_parser import DocumentParser
from src.pdf_inspector.engine.runner import AuditRunner


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_quality_checkpoints_gui_interaction(qapp):
    win = MainWindow()
    assert win is not None

    # Verify CheckpointsView Quality table definition has 16 checkpoints
    assert len(CheckpointsView.QUALITY_CATEGORIES) == 16
    assert "Validity of alternate text" in CheckpointsView.QUALITY_CATEGORIES

    table_q = win.checkpoints_view.table_quality
    assert table_q.rowCount() == 16

    # Verify canonical order
    expected_checkpoints = [
        "Validity of document title",
        "Artifacted content on page body",
        "Tagged text consists of only whitespace",
        "Tagged content exists outside of the page boundaries",
        "Presence of headings",
        "Presence of bookmarks (document outline) if there are headings",
        '"TOCI" elements contain "Link" elements',
        '"TOCI" elements correctly linked to headings',
        "Alternative text on text elements",
        "Validity of alternate text",
        'Completeness of "Link" elements',
        'Formal correctness of "LI" elements',
        'Completeness of "Table" elements',
        '"Note" elements are referenced',
        '"Note" elements contain "Lbl" elements',
        '"P" elements contain "Note" elements',
    ]
    for r, name in enumerate(expected_checkpoints):
        item = table_q.item(r, 0)
        assert item is not None
        assert name in item.text(), f"Row {r} expected {name}, got {item.text()}"

    # Create mock findings for testing interaction and navigation
    mock_results = [
        CheckResult(
            check_id="QUAL-ALT-001",
            name="Validity of alternate text",
            status=CheckStatus.PASS,
            severity=Severity.INFO,
            message="Alternative text is concise and descriptive.",
            category="Alternative Descriptions",
            standard="Quality",
            page=42,
            bounding_box=(50.0, 100.0, 200.0, 150.0),
            items_count=1
        ),
        CheckResult(
            check_id="QUAL-ALT-001",
            name="Validity of alternate text",
            status=CheckStatus.PASS,
            severity=Severity.INFO,
            message="Alternative text on diagram is valid.",
            category="Alternative Descriptions",
            standard="Quality",
            page=75,
            bounding_box=(60.0, 120.0, 220.0, 180.0),
            items_count=1
        ),
        CheckResult(
            check_id="QUAL-HEAD-001",
            name="Heading hierarchy",
            status=CheckStatus.PASS,
            severity=Severity.INFO,
            message="Headings follow logical hierarchy.",
            category="Headings",
            standard="Quality",
            page=12,
            items_count=1
        )
    ]

    from src.pdf_inspector.core.models import AuditReport, PDFDocumentModel
    doc_model = PDFDocumentModel(
        filepath="", filename="sample.pdf", filesize=1024, pdf_version="1.7",
        page_count=100, is_tagged=True
    )
    report = AuditReport(document_info={"filename": "sample.pdf"}, results=mock_results)

    win._on_audit_finished(doc_model, report)

    # 1. Verify Checkpoints view starts on Checkpoints (index 1)
    assert win.center_stack.currentIndex() == 1

    # 2. Verify tab switching inside CheckpointsView does NOT kick out of CheckpointsView
    win.checkpoints_view.tab_widget.setCurrentIndex(2)  # Quality tab
    qapp.processEvents()
    assert win.center_stack.currentIndex() == 1, "Tab switching must stay on CheckpointsView"

    # 3. Simulate clicking the "Validity of alternate text" row in Quality table (row 9)
    alt_row = 9
    assert "Validity of alternate text" in table_q.item(alt_row, 0).text()
    table_q.cellClicked.emit(alt_row, 0)
    qapp.processEvents()

    # Must have opened Detailed Findings (index 2)
    assert win.center_stack.currentIndex() == 2, "Clicking checkpoint must open Detailed Findings"

    # Filtered findings must contain strictly QUAL-ALT-001 findings
    assert len(win.detailed_view.filtered_findings) == 2
    assert win.detailed_view.table.rowCount() == 2
    assert all(r.check_id == "QUAL-ALT-001" for r in win.detailed_view.filtered_findings)

    # First finding must be automatically selected and displayed in Right Panel
    assert win.right_panel.current_finding is not None
    assert win.right_panel.current_finding.check_id == "QUAL-ALT-001"
    assert win.right_panel.current_finding.page == 42

    # PDF viewer must have been navigated to page 42
    assert win.pdf_viewer.current_page_idx == 41  # 0-indexed page 42
    assert win.pdf_viewer.highlight_bbox == (50.0, 100.0, 200.0, 150.0)

    # 4. Simulate clicking the second finding (page 75) in Detailed Findings table
    win.detailed_view.table.selectRow(1)
    qapp.processEvents()

    assert win.right_panel.current_finding.page == 75
    assert win.pdf_viewer.current_page_idx == 74  # 0-indexed page 75
    assert win.pdf_viewer.highlight_bbox == (60.0, 120.0, 220.0, 180.0)

    # 5. Simulate double clicking the finding -> must navigate to PDF Viewer view (index 3)
    item = win.detailed_view.table.item(1, 0)
    win.detailed_view.table.itemDoubleClicked.emit(item)
    qapp.processEvents()
    assert win.center_stack.currentIndex() == 3, "Double clicking finding must open PDF Viewer"

    win.close()


@pytest.mark.skipif(
    not os.path.exists(r"C:\Users\defaultuser0\Downloads\miktex 389.pdf"),
    reason="miktex 389.pdf not found in Downloads"
)
def test_miktex_389_gui_quality_interaction(qapp):
    pdf_path = r"C:\Users\defaultuser0\Downloads\miktex 389.pdf"
    doc = DocumentParser(pdf_path).parse()
    report = AuditRunner().run(doc)

    win = MainWindow()
    win._on_audit_finished(doc, report)

    # 1. Verify Quality tab
    win.checkpoints_view.tab_widget.setCurrentIndex(2)
    qapp.processEvents()
    table_q = win.checkpoints_view.table_quality

    # Exactly 16 checkpoints
    assert table_q.rowCount() == 16
    alt_row = 9
    assert "Validity of alternate text" in table_q.item(alt_row, 0).text()
    # 23 passed
    assert table_q.item(alt_row, 1).text() == "23"

    # 2. Click "Validity of alternate text" row
    table_q.cellClicked.emit(alt_row, 0)
    qapp.processEvents()

    # Opened Detailed Findings
    assert win.center_stack.currentIndex() == 2
    assert sum(r.items_count for r in win.detailed_view.filtered_findings) == 23
    assert win.detailed_view.table.rowCount() >= 1

    # First finding navigated
    first_f = win.detailed_view.filtered_findings[0]
    assert win.right_panel.current_finding == first_f
    if first_f.page:
        assert win.pdf_viewer.current_page_idx == first_f.page - 1

    win.close()
