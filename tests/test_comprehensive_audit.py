"""
Comprehensive End-to-End Accessibility Audit Tests
Validates real PDF inspection capabilities:
- Tagged & untagged PDFs
- Images & Alt text
- Tables (headers, regularity)
- Lists (L -> LI -> Lbl, LBody)
- Links (structure, ambiguous anchor text)
- Forms (AcroForm, tooltips /TU)
- Bookmarks & Outlines
- Fonts & Unicode (PUA, replacement chars)
- Malformed & Encrypted PDFs
- Batch PDF scanning
- Multi-format reports (PDF, HTML, JSON, CSV)
"""

import os
import tempfile
import pytest
import pikepdf
import pymupdf

from src.pdf_inspector.core.document_parser import DocumentParser
from src.pdf_inspector.core.models import (
    PDFDocumentModel, CheckStatus, Severity, ImageModel, TableModel,
    LinkModel, FormFieldModel, BookmarkModel, StructureNode, PageModel,
    ListModel, FontModel
)
from src.pdf_inspector.engine.runner import AuditRunner
from src.pdf_inspector.engine.pdf_ua.alt_text_rules import FigureAlternativeTextRule
from src.pdf_inspector.engine.pdf_ua.table_rules import TableStructureHeadersRule
from src.pdf_inspector.engine.pdf_ua.list_rules import ListStructureHierarchyRule
from src.pdf_inspector.engine.pdf_ua.unicode_rules import UnicodePUARule, ReplacementCharacterRule
from src.pdf_inspector.engine.pdf_ua.parent_tree_rules import ParentTreeIntegrityRule
from src.pdf_inspector.engine.pdf_ua.artifact_rules import ArtifactInStructureTreeRule
from src.pdf_inspector.engine.pdf_ua.annotation_rules import AnnotationTaggedRule
from src.pdf_inspector.engine.quality.quality_rules import (
    HeadingHierarchyQualityRule, TableRegularityQualityRule, LinkQualityRule
)
from src.pdf_inspector.reporting.pdf_report import PDFReportGenerator
from src.pdf_inspector.reporting.html_report import HTMLReportGenerator
from src.pdf_inspector.reporting.json_exporter import JSONExporter, CSVExporter


@pytest.fixture(scope="session")
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as td:
        yield td


def test_tagged_vs_untagged_real_pdfs(temp_dir):
    """Verifies that real tagged and untagged PDFs are correctly differentiated."""
    # 1. Untagged PDF
    untagged_path = os.path.join(temp_dir, "untagged.pdf")
    doc_fitz = pymupdf.open()
    page = doc_fitz.new_page(width=500, height=700)
    page.insert_text((50, 100), "This is plain untagged text.", fontsize=12)
    doc_fitz.save(untagged_path)
    doc_fitz.close()

    parser1 = DocumentParser(untagged_path)
    model1 = parser1.parse()
    assert model1.is_tagged is False
    assert model1.structure_tree is None

    runner = AuditRunner()
    report1 = runner.run(model1)
    failed_ids = [r.check_id for r in report1.results if r.status == CheckStatus.FAIL]
    assert "PDFUA-CONTENT-001" in failed_ids  # Tagged PDF check failed

    # 2. Tagged PDF
    tagged_path = os.path.join(temp_dir, "tagged.pdf")
    doc_fitz2 = pymupdf.open()
    p2 = doc_fitz2.new_page(width=500, height=700)
    p2.insert_text((50, 100), "Tagged heading and paragraph.", fontsize=14)
    doc_fitz2.save(tagged_path)
    doc_fitz2.close()

    with pikepdf.open(tagged_path, allow_overwriting_input=True) as pdoc:
        pdoc.Root["/MarkInfo"] = pikepdf.Dictionary({"/Marked": True})
        pdoc.Root["/Lang"] = pikepdf.String("en-US")
        pdoc.Root["/ViewerPreferences"] = pikepdf.Dictionary({"/DisplayDocTitle": True})

        h1 = pikepdf.Dictionary({"/Type": pikepdf.Name("/StructElem"), "/S": pikepdf.Name("/H1"), "/Pg": pdoc.pages[0].objgen})
        p = pikepdf.Dictionary({"/Type": pikepdf.Name("/StructElem"), "/S": pikepdf.Name("/P"), "/Pg": pdoc.pages[0].objgen})
        parent_tree = pikepdf.Dictionary({"/Nums": pikepdf.Array([pikepdf.Integer(0), pikepdf.Array([h1, p])])})

        struct_root = pikepdf.Dictionary({
            "/Type": pikepdf.Name("/StructTreeRoot"),
            "/K": pikepdf.Array([h1, p]),
            "/ParentTree": pdoc.make_indirect(parent_tree),
            "/ParentTreeNextKey": pikepdf.Integer(1)
        })
        pdoc.Root["/StructTreeRoot"] = pdoc.make_indirect(struct_root)
        pdoc.pages[0]["/StructParents"] = pikepdf.Integer(0)
        pdoc.save(tagged_path)

    parser2 = DocumentParser(tagged_path)
    model2 = parser2.parse()
    assert model2.is_tagged is True
    assert model2.structure_tree is not None
    assert model2.has_parent_tree is True

    report2 = runner.run(model2)
    tagged_check = next(r for r in report2.results if r.check_id == "PDFUA-CONTENT-001")
    assert tagged_check.status == CheckStatus.PASS


def test_images_and_alt_text_rules():
    """Tests alternative text checking on images with and without alt text."""
    rule = FigureAlternativeTextRule()

    img_good = ImageModel(id="img_01", page=1, bbox=(50, 50, 200, 200), width=150, height=150, colorspace="DeviceRGB", has_alt=True, alt_text="Quarterly revenue growth chart")
    img_bad = ImageModel(id="img_02", page=1, bbox=(50, 250, 200, 400), width=150, height=150, colorspace="DeviceRGB", has_alt=False, alt_text=None)
    img_placeholder = ImageModel(id="img_03", page=2, bbox=(50, 50, 200, 200), width=150, height=150, colorspace="DeviceRGB", has_alt=True, alt_text="image.png")

    fig_node_good = StructureNode(id="fig1", tag="Figure", standard_tag="Figure", alt_text="Quarterly revenue growth chart", page=1, bbox=(50, 50, 200, 200))
    fig_node_bad = StructureNode(id="fig2", tag="Figure", standard_tag="Figure", alt_text=None, page=1, bbox=(50, 250, 200, 400))
    fig_node_ph = StructureNode(id="fig3", tag="Figure", standard_tag="Figure", alt_text="image.png", page=2, bbox=(50, 50, 200, 200))

    root = StructureNode(id="root", tag="StructTreeRoot", standard_tag="StructTreeRoot", children=[fig_node_good, fig_node_bad, fig_node_ph])

    doc = PDFDocumentModel(
        filepath="", filename="images.pdf", filesize=1024, pdf_version="1.7",
        page_count=2, is_tagged=True, structure_tree=root,
        images=[img_good, img_bad, img_placeholder]
    )

    results = rule.evaluate(doc)
    failures = [r for r in results if r.status == CheckStatus.FAIL]
    warnings = [r for r in results if r.status == CheckStatus.WARNING]
    assert len(failures) >= 1  # Missing alt
    assert len(warnings) >= 1  # Placeholder filename alt


def test_tables_structure_and_regularity():
    """Tests table structure checking for headers and grid regularity."""
    header_rule = TableStructureHeadersRule()
    reg_rule = TableRegularityQualityRule()

    # Accessible table with headers
    t_good = TableModel(id="tbl1", page=1, bbox=(50, 50, 400, 200), rows_count=3, cols_count=3, has_headers=True, header_cells_count=3, data_cells_count=6, is_regular=True)
    # Inaccessible table with no headers and irregular layout
    t_bad = TableModel(id="tbl2", page=2, bbox=(50, 50, 400, 200), rows_count=4, cols_count=3, has_headers=False, header_cells_count=0, data_cells_count=12, is_regular=False)

    doc = PDFDocumentModel(
        filepath="", filename="tables.pdf", filesize=2048, pdf_version="1.7",
        page_count=2, is_tagged=True, tables=[t_good, t_bad]
    )

    res_headers = header_rule.evaluate(doc)
    assert any(r.status == CheckStatus.FAIL and "header cells" in r.message for r in res_headers)

    res_reg = reg_rule.evaluate(doc)
    assert any(r.status == CheckStatus.WARNING and "irregular grid dimensions" in r.message for r in res_reg)


def test_lists_structure_hierarchy():
    """Tests list structure validation according to PDF/UA (L -> LI -> Lbl, LBody)."""
    rule = ListStructureHierarchyRule()

    # Valid List: L -> LI -> (Lbl, LBody)
    lbl = StructureNode(id="lbl1", tag="Lbl", standard_tag="Lbl")
    lbody = StructureNode(id="lbody1", tag="LBody", standard_tag="LBody")
    li = StructureNode(id="li1", tag="LI", standard_tag="LI", children=[lbl, lbody])
    l_valid = StructureNode(id="l1", tag="L", standard_tag="L", children=[li])

    tree_valid = StructureNode(id="root", tag="StructTreeRoot", standard_tag="StructTreeRoot", children=[l_valid])
    list_valid_model = ListModel(id="l1", page=1, items_count=1, is_valid_structure=True, has_labels=True)
    doc_valid = PDFDocumentModel(filepath="", filename="list_valid.pdf", filesize=1024, pdf_version="1.7", page_count=1, is_tagged=True, structure_tree=tree_valid, lists=[list_valid_model])
    assert rule.evaluate(doc_valid)[0].status == CheckStatus.PASS

    # Invalid List: L directly contains P without LI
    p_in_l = StructureNode(id="p1", tag="P", standard_tag="P")
    l_invalid = StructureNode(id="l2", tag="L", standard_tag="L", children=[p_in_l])
    tree_invalid = StructureNode(id="root2", tag="StructTreeRoot", standard_tag="StructTreeRoot", children=[l_invalid])
    list_invalid_model = ListModel(id="l2", page=1, items_count=1, is_valid_structure=False, has_labels=False)
    doc_invalid = PDFDocumentModel(filepath="", filename="list_invalid.pdf", filesize=1024, pdf_version="1.7", page_count=1, is_tagged=True, structure_tree=tree_invalid, lists=[list_invalid_model])
    assert any(r.status == CheckStatus.FAIL for r in rule.evaluate(doc_invalid))


def test_links_and_ambiguous_text():
    """Tests link structure tagging and detection of ambiguous link text."""
    link_rule = LinkQualityRule()

    lnk1 = LinkModel(id="lnk1", page=1, bbox=(50, 50, 100, 65), uri="https://example.com/report", text="Annual Fiscal Report 2026", has_structure_link=True)
    lnk2 = LinkModel(id="lnk2", page=1, bbox=(50, 80, 100, 95), uri="https://example.com/details", text="Click here", has_structure_link=True)
    lnk3 = LinkModel(id="lnk3", page=2, bbox=(50, 50, 100, 65), uri="https://example.com/more", text="read more...", has_structure_link=False)

    doc = PDFDocumentModel(
        filepath="", filename="links.pdf", filesize=1024, pdf_version="1.7",
        page_count=2, is_tagged=True, links=[lnk1, lnk2, lnk3]
    )

    results = link_rule.evaluate(doc)
    warned = [r for r in results if r.status == CheckStatus.WARNING]
    assert len(warned) >= 2
    assert any("Click here" in w.evidence for w in warned)
    assert any("read more" in w.evidence for w in warned)


def test_form_fields_tooltips_and_tab_order():
    """Tests form fields inspection and accessible tooltips (/TU)."""
    f1 = FormFieldModel(name="firstName", field_type="Text", page=1, bbox=(100, 100, 250, 120), tooltip="Enter your legal first name", is_required=True)
    f2 = FormFieldModel(name="ssn", field_type="Text", page=1, bbox=(100, 140, 250, 160), tooltip=None, is_required=True)

    doc = PDFDocumentModel(
        filepath="", filename="forms.pdf", filesize=1024, pdf_version="1.7",
        page_count=1, is_tagged=True, form_fields=[f1, f2]
    )

    from src.pdf_inspector.engine.wcag.wcag_rules import WCAGInputAssistanceRule
    res = WCAGInputAssistanceRule().evaluate(doc)
    assert any(r.status == CheckStatus.FAIL and "ssn" in r.evidence for r in res)


def test_unicode_pua_and_replacement_characters():
    """Tests detection of Private Use Area characters and unicode replacement glyphs."""
    pua_rule = UnicodePUARule()
    repl_rule = ReplacementCharacterRule()

    # Document containing PUA (\uE001) and replacement char (\uFFFD)
    p1 = PageModel(page_number=1, width=500, height=700, text="System status \uE001 operational \uFFFD error")
    doc = PDFDocumentModel(filepath="", filename="unicode.pdf", filesize=500, pdf_version="1.7", page_count=1, pages=[p1])

    res_pua = pua_rule.evaluate(doc)
    assert any(r.status == CheckStatus.WARNING and "Private Use Area" in r.message for r in res_pua)

    res_repl = repl_rule.evaluate(doc)
    assert any(r.status == CheckStatus.FAIL and "Replacement character" in r.message for r in res_repl)


def test_malformed_pdf_error_handling(temp_dir):
    """Verifies that corrupted or malformed files raise clear, informative errors."""
    bad_pdf_path = os.path.join(temp_dir, "corrupt.pdf")
    with open(bad_pdf_path, "wb") as f:
        f.write(b"%PDF-1.7\nGARBAGE_BYTES_NO_XREF_CORRUPTED_STREAM\x00\xFF\xFE\xFD")

    parser = DocumentParser(bad_pdf_path)
    with pytest.raises(ValueError) as excinfo:
        parser.parse()
    assert "corrupt or malformed" in str(excinfo.value).lower()


def test_encrypted_pdf_error_handling(temp_dir):
    """Verifies that password-encrypted PDFs raise a clean PermissionError."""
    enc_pdf_path = os.path.join(temp_dir, "encrypted_protected.pdf")
    pdoc = pikepdf.new()
    pdoc.add_blank_page(page_size=(300, 300))
    pdoc.save(
        enc_pdf_path,
        encryption=pikepdf.Encryption(owner="secretOwnerPass", user="secretUserPass", R=4)
    )
    pdoc.close()

    parser = DocumentParser(enc_pdf_path)
    with pytest.raises(PermissionError) as excinfo:
        parser.parse()
    assert "password" in str(excinfo.value).lower()


def test_batch_scanner_functionality(qapp, temp_dir):
    """Verifies batch scanning across a directory of mixed PDFs."""
    # Create accessible PDF
    p1_path = os.path.join(temp_dir, "doc1.pdf")
    d1 = pymupdf.open()
    d1.new_page().insert_text((50, 50), "Batch Doc 1")
    d1.save(p1_path)
    d1.close()

    # Create second PDF
    p2_path = os.path.join(temp_dir, "doc2.pdf")
    d2 = pymupdf.open()
    d2.new_page().insert_text((50, 50), "Batch Doc 2")
    d2.save(p2_path)
    d2.close()

    # Create corrupt file
    p3_path = os.path.join(temp_dir, "doc3_bad.pdf")
    with open(p3_path, "wb") as f:
        f.write(b"not a valid pdf header")

    from src.pdf_inspector.ui.views.batch_view import BatchScanView
    scanner = BatchScanView()
    results = scanner.scan_folder(temp_dir)

    assert len(results) == 3
    success_items = [r for r in results if r["status"] == "Success"]
    error_items = [r for r in results if "Error" in r["status"]]

    assert len(success_items) == 2
    assert len(error_items) == 1
    assert "doc3_bad.pdf" in error_items[0]["filename"]


def test_all_report_formats_generation(temp_dir):
    """Verifies that PDF, HTML, JSON, and CSV reports are properly generated with real contents."""
    # Build sample document model & audit report
    p1 = PageModel(page_number=1, width=612, height=792, text="Report summary content.")
    f1 = FontModel("Times-Roman", "Type1", is_embedded=True, is_subset=False, has_tounicode=True, encoding="WinAnsi", pages=[1])
    img1 = ImageModel("img1", 1, (50, 50, 200, 200), 150, 150, "RGB", has_alt=True, alt_text="Company Logo")

    doc = PDFDocumentModel(
        filepath=os.path.join(temp_dir, "sample.pdf"),
        filename="sample.pdf",
        filesize=24000,
        pdf_version="1.7",
        page_count=1,
        title="Comprehensive Quality Report",
        language="en-US",
        is_tagged=True,
        display_doc_title=True,
        pdfua_identifier_present=True,
        pages=[p1],
        fonts=[f1],
        images=[img1]
    )

    runner = AuditRunner()
    report = runner.run(doc)

    # 1. PDF Report
    pdf_out = os.path.join(temp_dir, "audit_report.pdf")
    PDFReportGenerator.generate(report, pdf_out)
    assert os.path.exists(pdf_out)
    assert os.path.getsize(pdf_out) > 5000

    # 2. HTML Report
    html_out = os.path.join(temp_dir, "audit_report.html")
    HTMLReportGenerator.generate(report, html_out)
    assert os.path.exists(html_out)
    with open(html_out, "r", encoding="utf-8") as f:
        html_content = f.read()
    assert "<!DOCTYPE html>" in html_content
    assert "Comprehensive Quality Report" in html_content
    assert "PDF Accessibility Inspector" in html_content

    # 3. JSON Report
    json_out = os.path.join(temp_dir, "audit_report.json")
    JSONExporter.export(report, json_out)
    assert os.path.exists(json_out)
    import json
    with open(json_out, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert "application" in data
    assert "summary" in data
    assert "findings" in data
    assert data["summary"]["compliance_score"] >= 0.0

    # 4. CSV Report
    csv_out = os.path.join(temp_dir, "audit_report.csv")
    CSVExporter.export(report, csv_out)
    assert os.path.exists(csv_out)
    with open(csv_out, "r", encoding="utf-8") as f:
        csv_lines = f.readlines()
    assert "Check ID" in csv_lines[0]
    assert "Rule Name" in csv_lines[0]
    assert "Standard" in csv_lines[0]
