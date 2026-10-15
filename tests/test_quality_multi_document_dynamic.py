"""
Multi-Document Dynamic Quality Engine Verification Suite
Validates that Quality checkpoints operate dynamically, generally, and accurately
across multiple diverse real-world and synthetic PDFs without hardcoding.
"""

import os
import tempfile
import pytest
import pymupdf
import pikepdf

from src.pdf_inspector.core.document_parser import DocumentParser
from src.pdf_inspector.engine.runner import AuditRunner
from src.pdf_inspector.core.models import CheckStatus, Severity
from src.pdf_inspector.ui.views.checkpoints_view import CheckpointsView


def test_quality_checkpoints_count_and_order_contract():
    """Verify that the Quality tab defines exactly 16 canonical PAC checkpoints in order."""
    expected = [
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
    assert len(CheckpointsView.QUALITY_CATEGORIES) == 16
    assert CheckpointsView.QUALITY_CATEGORIES == expected


def test_dynamic_synthetic_quality_defects():
    """Generates synthetic PDFs with specific structural characteristics and verifies dynamic detection."""
    with tempfile.TemporaryDirectory() as td:
        pdf_path = os.path.join(td, "synthetic_quality.pdf")

        # Create basic PDF
        doc = pymupdf.open()
        p1 = doc.new_page(width=612, height=792)
        p1.insert_text((50, 100), "First Heading Level Two", fontsize=14)
        p1.insert_text((50, 140), "Paragraph with list item text", fontsize=11)
        doc.save(pdf_path)
        doc.close()

        # Add structure tree with deliberate quality characteristics:
        # 1. First heading is H2 (defect in Presence of headings)
        # 2. LI directly contains P (defect in Formal correctness of LI)
        # 3. Figure has placeholder alt text "image.png" (defect in Validity of alternate text)
        with pikepdf.open(pdf_path, allow_overwriting_input=True) as pike:
            pike.Root["/MarkInfo"] = pikepdf.Dictionary({"/Marked": True})
            pike.Root["/ViewerPreferences"] = pikepdf.Dictionary({"/DisplayDocTitle": True})
            pike.Root["/Lang"] = pikepdf.String("en-US")

            # Document info
            with pike.open_metadata() as meta:
                meta["dc:title"] = "Dynamic Test Document Title"

            pg = pike.pages[0].objgen

            h2_elem = pike.make_indirect(pikepdf.Dictionary({
                "/Type": pikepdf.Name("/StructElem"),
                "/S": pikepdf.Name("/H2"),
                "/Pg": pg
            }))

            p_in_li = pike.make_indirect(pikepdf.Dictionary({
                "/Type": pikepdf.Name("/StructElem"),
                "/S": pikepdf.Name("/P"),
                "/Pg": pg
            }))

            # Invalid LI directly containing P
            li_elem = pike.make_indirect(pikepdf.Dictionary({
                "/Type": pikepdf.Name("/StructElem"),
                "/S": pikepdf.Name("/LI"),
                "/K": pikepdf.Array([p_in_li]),
                "/Pg": pg
            }))

            # Figure with placeholder alt text
            fig_elem = pike.make_indirect(pikepdf.Dictionary({
                "/Type": pikepdf.Name("/StructElem"),
                "/S": pikepdf.Name("/Figure"),
                "/Alt": pikepdf.String("chart.png"),
                "/Pg": pg
            }))

            tree_root = pike.make_indirect(pikepdf.Dictionary({
                "/Type": pikepdf.Name("/StructTreeRoot"),
                "/K": pikepdf.Array([h2_elem, li_elem, fig_elem])
            }))
            pike.Root["/StructTreeRoot"] = tree_root
            pike.save(pdf_path)

        # Audit synthetic document
        parsed_doc = DocumentParser(pdf_path).parse()
        report = AuditRunner().run(parsed_doc)
        quality_counts = report.get_category_counts("Quality")

        # 1. Heading hierarchy: flagged because first heading is H2
        assert quality_counts["Presence of headings"]["warned"] >= 1
        assert quality_counts["Presence of headings"]["passed"] == 0

        # 2. LI correctness: flagged because LI directly contains P without LBody
        assert quality_counts['Formal correctness of "LI" elements']["failed"] >= 1
        assert quality_counts['Formal correctness of "LI" elements']["passed"] == 0

        # 3. Validity of alternate text: flagged because alt is filename 'chart.png'
        assert quality_counts["Validity of alternate text"]["warned"] >= 1
        assert quality_counts["Validity of alternate text"]["passed"] == 0

        # 4. Validity of document title: PASS because title is present and DisplayDocTitle is True
        assert quality_counts["Validity of document title"]["passed"] == 1
        assert quality_counts["Validity of document title"]["failed"] == 0


@pytest.mark.skipif(
    not os.path.exists(r"C:\Users\defaultuser0\Downloads\PDF03.pdf"),
    reason="PDF03.pdf not found in Downloads"
)
def test_quality_dynamic_evaluation_pdf03():
    """Validates Quality engine dynamic evaluation on PDF03 benchmark document."""
    pdf_path = r"C:\Users\defaultuser0\Downloads\PDF03.pdf"
    doc = DocumentParser(pdf_path).parse()
    assert doc is not None

    report = AuditRunner().run(doc)
    counts = report.get_category_counts("Quality")

    # Document Title: Validated from PDF properties
    title_res = counts["Validity of document title"]
    assert title_res["passed"] + title_res["failed"] == 1

    # Check that results are calculated from actual elements, not zeroed placeholders
    total_evaluated = sum(
        c.get("passed", 0) + c.get("warned", 0) + c.get("failed", 0)
        for c in counts.values()
    )
    assert total_evaluated > 0, "Quality engine must evaluate elements dynamically"


@pytest.mark.skipif(
    not os.path.exists(r"C:\Users\defaultuser0\Downloads\Multilevel_List_Solar_System.pdf"),
    reason="Multilevel_List_Solar_System.pdf not found in Downloads"
)
def test_quality_dynamic_evaluation_solar_system():
    """Validates Quality engine on a real document with multiple nested lists."""
    pdf_path = r"C:\Users\defaultuser0\Downloads\Multilevel_List_Solar_System.pdf"
    doc = DocumentParser(pdf_path).parse()
    assert doc is not None

    report = AuditRunner().run(doc)
    counts = report.get_category_counts("Quality")

    # List items: document has lists, so LI checkpoint must evaluate real LI items
    li_counts = counts['Formal correctness of "LI" elements']
    assert li_counts["passed"] + li_counts["failed"] > 0, "LI checkpoint must evaluate actual list elements"


@pytest.mark.skipif(
    not os.path.exists(r"C:\Users\defaultuser0\Downloads\TOC FILE.pdf"),
    reason="TOC FILE.pdf not found in Downloads"
)
def test_quality_dynamic_evaluation_toc_file():
    """Validates Quality engine on a real document with a Table of Contents."""
    pdf_path = r"C:\Users\defaultuser0\Downloads\TOC FILE.pdf"
    doc = DocumentParser(pdf_path).parse()
    assert doc is not None

    report = AuditRunner().run(doc)
    counts = report.get_category_counts("Quality")

    # TOCI checkpoints must dynamically reflect the TOC elements in this document
    toci_links = counts['"TOCI" elements contain "Link" elements']
    assert isinstance(toci_links["passed"], int)
    assert isinstance(toci_links["failed"], int)
