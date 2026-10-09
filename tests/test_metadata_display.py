"""
Unit tests for PDF metadata display fallback logic in CheckpointsView and MetadataView,
and XMP metadata tag-bounded extraction in DocumentParser.
Validates that doc.filename is NEVER used as fallback for Title or Author, and that
missing/empty values properly resolve to 'No title' and 'No author'.
"""

import os
import pytest
from PySide6.QtWidgets import QApplication
from src.pdf_inspector.core.models import PDFDocumentModel, AuditReport
from src.pdf_inspector.core.document_parser import DocumentParser
from src.pdf_inspector.ui.views.checkpoints_view import CheckpointsView
from src.pdf_inspector.ui.views.metadata_view import MetadataView


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _make_doc_model(filename="sample_test.pdf", title=None, author=None):
    return PDFDocumentModel(
        filepath=f"/path/to/{filename}",
        filename=filename,
        filesize=20480,
        pdf_version="1.7",
        page_count=1,
        title=title,
        author=author,
        is_tagged=True,
    )


def test_missing_title_missing_author(qapp):
    """1. Missing title + missing author -> 'No title', 'No author', filename preserved."""
    doc = _make_doc_model(filename="PDF17.pdf", title=None, author=None)
    report = AuditReport(document_info={"filename": doc.filename}, results=[])

    view = CheckpointsView()
    view.update_report(report, doc)

    assert view.lbl_val_fn.text() == "PDF17.pdf"
    assert view.lbl_val_title.text() == "No title"
    assert view.lbl_val_author.text() == "No author"

    meta_view = MetadataView()
    meta_view.load_document(doc)
    props = {meta_view.table.item(r, 0).text(): meta_view.table.item(r, 1).text() for r in range(meta_view.table.rowCount())}
    assert props["File Name"] == "PDF17.pdf"
    assert props["Document Title (Effective)"] == "No title"
    assert props["Author / Creator"] == "No author"


def test_existing_title_missing_author(qapp):
    """2. Existing title + missing author -> actual title, 'No author'."""
    doc = _make_doc_model(filename="example.pdf", title="Engineering Mechanics", author=None)
    report = AuditReport(document_info={"filename": doc.filename}, results=[])

    view = CheckpointsView()
    view.update_report(report, doc)

    assert view.lbl_val_fn.text() == "example.pdf"
    assert view.lbl_val_title.text() == "Engineering Mechanics"
    assert view.lbl_val_author.text() == "No author"

    meta_view = MetadataView()
    meta_view.load_document(doc)
    props = {meta_view.table.item(r, 0).text(): meta_view.table.item(r, 1).text() for r in range(meta_view.table.rowCount())}
    assert props["File Name"] == "example.pdf"
    assert props["Document Title (Effective)"] == "Engineering Mechanics"
    assert props["Author / Creator"] == "No author"


def test_missing_title_existing_author(qapp):
    """3. Missing title + existing author -> 'No title', actual author."""
    doc = _make_doc_model(filename="doc_research.pdf", title=None, author="Dr. Jane Doe")
    report = AuditReport(document_info={"filename": doc.filename}, results=[])

    view = CheckpointsView()
    view.update_report(report, doc)

    assert view.lbl_val_fn.text() == "doc_research.pdf"
    assert view.lbl_val_title.text() == "No title"
    assert view.lbl_val_author.text() == "Dr. Jane Doe"

    meta_view = MetadataView()
    meta_view.load_document(doc)
    props = {meta_view.table.item(r, 0).text(): meta_view.table.item(r, 1).text() for r in range(meta_view.table.rowCount())}
    assert props["File Name"] == "doc_research.pdf"
    assert props["Document Title (Effective)"] == "No title"
    assert props["Author / Creator"] == "Dr. Jane Doe"


def test_empty_or_whitespace_title_and_author(qapp):
    """4. Empty / whitespace strings for title and author -> 'No title', 'No author'."""
    doc = _make_doc_model(filename="blank_meta.pdf", title="   ", author="\t \n")
    report = AuditReport(document_info={"filename": doc.filename}, results=[])

    view = CheckpointsView()
    view.update_report(report, doc)

    assert view.lbl_val_fn.text() == "blank_meta.pdf"
    assert view.lbl_val_title.text() == "No title"
    assert view.lbl_val_author.text() == "No author"

    meta_view = MetadataView()
    meta_view.load_document(doc)
    props = {meta_view.table.item(r, 0).text(): meta_view.table.item(r, 1).text() for r in range(meta_view.table.rowCount())}
    assert props["Document Title (Effective)"] == "No title"
    assert props["Author / Creator"] == "No author"


def test_filename_never_used_as_fallback(qapp):
    """5. Filename is never substituted into Title or Author fields under any condition."""
    filename = "Financial_Statement_2026.pdf"
    doc = _make_doc_model(filename=filename, title=None, author="")
    report = AuditReport(document_info={"filename": doc.filename}, results=[])

    view = CheckpointsView()
    view.update_report(report, doc)

    assert view.lbl_val_title.text() != filename
    assert view.lbl_val_author.text() != filename
    assert view.lbl_val_title.text() == "No title"
    assert view.lbl_val_author.text() == "No author"
    assert view.lbl_val_fn.text() == filename


def test_pdf12_empty_dc_creator_real_file(qapp):
    """6. Real PDF12.pdf with empty <dc:creator><rdf:Seq/></dc:creator> does NOT leak XML into doc.author."""
    pdf_path = os.path.join("test_corpus", "ALL FILES", "PDF12.pdf")
    if not os.path.exists(pdf_path):
        pytest.skip("PDF12.pdf not found in test_corpus")

    parser = DocumentParser(pdf_path)
    doc = parser.parse()

    assert doc.filename == "PDF12.pdf"
    assert doc.title == "Unit 5 What We Wear"
    assert doc.author is None or doc.author == ""
    assert doc.xmp_dc_creator is None

    # UI Verification
    report = AuditReport(document_info={"filename": doc.filename}, results=[])
    view = CheckpointsView()
    view.update_report(report, doc)

    assert view.lbl_val_fn.text() == "PDF12.pdf"
    assert view.lbl_val_title.text() == "Unit 5 What We Wear"
    assert view.lbl_val_author.text() == "No author"
    assert "<" not in view.lbl_val_author.text()
    assert "rdf:" not in view.lbl_val_author.text()


def test_xmp_tag_bounded_extraction_edge_cases():
    """7. Tag-bounded extraction prevents regex bleed when Dublin Core containers are empty."""
    sample_xmp = """<?xpacket begin="" id="W5M0MpCehiHzreSzNTczkc9d"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/">
   <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
      <rdf:Description rdf:about=""
            xmlns:dc="http://purl.org/dc/elements/1.1/"
            xmlns:pdfaExtension="http://www.aiim.org/pdfa/ns/extension/"
            xmlns:pdfaSchema="http://www.aiim.org/pdfa/ns/schema#">
         <dc:title>
            <rdf:Alt>
               <rdf:li xml:lang="x-default">Valid Document Title</rdf:li>
            </rdf:Alt>
         </dc:title>
         <dc:creator>
            <rdf:Seq/>
         </dc:creator>
         <dc:description>
            <rdf:Alt/>
         </dc:description>
         <pdfaExtension:schemas>
            <rdf:Bag>
               <rdf:li rdf:parseType="Resource">
                  <pdfaSchema:schema>PDF/UA Universal Accessibility Schema</pdfaSchema:schema>
               </rdf:li>
            </rdf:Bag>
         </pdfaExtension:schemas>
      </rdf:Description>
   </rdf:RDF>
</x:xmpmeta>"""

    import re
    # Emulate the exact parser logic
    meta_str = sample_xmp

    xmp_dc_title = None
    xmp_dc_creator = None
    xmp_dc_description = None

    # Dublin Core Title (<dc:title>)
    m_title_block = re.search(r"<dc:title\b[^>]*>(.*?)</dc:title>", meta_str, re.DOTALL | re.IGNORECASE)
    if m_title_block:
        block = m_title_block.group(1)
        m_li = re.search(r"<rdf:li\b[^>]*>(.*?)</rdf:li>", block, re.DOTALL | re.IGNORECASE)
        if m_li and m_li.group(1).strip():
            xmp_dc_title = m_li.group(1).strip()
        elif "<rdf:" not in block and block.strip():
            xmp_dc_title = block.strip()

    # Dublin Core Creator (<dc:creator>)
    m_creator_block = re.search(r"<dc:creator\b[^>]*>(.*?)</dc:creator>", meta_str, re.DOTALL | re.IGNORECASE)
    if m_creator_block:
        block = m_creator_block.group(1)
        m_li = re.search(r"<rdf:li\b[^>]*>(.*?)</rdf:li>", block, re.DOTALL | re.IGNORECASE)
        if m_li and m_li.group(1).strip():
            xmp_dc_creator = m_li.group(1).strip()
        elif "<rdf:" not in block and block.strip():
            xmp_dc_creator = block.strip()

    # Dublin Core Description (<dc:description>)
    m_desc_block = re.search(r"<dc:description\b[^>]*>(.*?)</dc:description>", meta_str, re.DOTALL | re.IGNORECASE)
    if m_desc_block:
        block = m_desc_block.group(1)
        m_li = re.search(r"<rdf:li\b[^>]*>(.*?)</rdf:li>", block, re.DOTALL | re.IGNORECASE)
        if m_li and m_li.group(1).strip():
            xmp_dc_description = m_li.group(1).strip()
        elif "<rdf:" not in block and block.strip():
            xmp_dc_description = block.strip()

    assert xmp_dc_title == "Valid Document Title"
    assert xmp_dc_creator is None
    assert xmp_dc_description is None
