"""
Unit tests for new Quality Rules:
- QUAL-BOUND-001 (TaggedContentPageBoundariesRule)
- QUAL-TOC-001 (TOCIContainsLinkRule)
- QUAL-TOC-002 (TOCILinkDestinationRule)
- QUAL-TEXT-001 (TextElementAltTextQualityRule)
- QUAL-NOTE-001 (NoteReferencedQualityRule)
- QUAL-NOTE-002 (NoteContainsLabelQualityRule)
- QUAL-NOTE-003 (ParagraphContainsNoteQualityRule)
"""

import pytest
from src.pdf_inspector.core.models import (
    PDFDocumentModel, PageModel, StructureNode, CheckStatus, Severity, LinkModel
)
from src.pdf_inspector.engine.quality.quality_rules import (
    TaggedContentPageBoundariesRule,
    TOCIContainsLinkRule,
    TOCILinkDestinationRule,
    TextElementAltTextQualityRule,
    NoteReferencedQualityRule,
    NoteContainsLabelQualityRule,
    ParagraphContainsNoteQualityRule,
)


def test_tagged_content_page_boundaries_pass():
    page = PageModel(
        page_number=1,
        width=612.0,
        height=792.0,
        mcid_bboxes={
            0: (50.0, 50.0, 200.0, 100.0),
            1: (100.0, 150.0, 400.0, 300.0)
        }
    )
    doc = PDFDocumentModel(
        filepath="sample.pdf",
        filename="sample.pdf",
        filesize=1000,
        pdf_version="1.7",
        page_count=1,
        is_tagged=True,
        pages=[page]
    )

    rule = TaggedContentPageBoundariesRule()
    results = rule.evaluate(doc)
    assert len(results) == 1
    assert results[0].status == CheckStatus.PASS


def test_tagged_content_page_boundaries_fail():
    page = PageModel(
        page_number=1,
        width=612.0,
        height=792.0,
        mcid_bboxes={
            0: (50.0, 50.0, 200.0, 100.0),
            1: (700.0, 850.0, 800.0, 900.0)  # Strictly outside page
        },
        mcid_texts={1: "Off-screen text"}
    )
    doc = PDFDocumentModel(
        filepath="sample.pdf",
        filename="sample.pdf",
        filesize=1000,
        pdf_version="1.7",
        page_count=1,
        is_tagged=True,
        pages=[page]
    )

    rule = TaggedContentPageBoundariesRule()
    results = rule.evaluate(doc)
    assert len(results) == 1
    assert results[0].status == CheckStatus.WARNING
    assert "MCID 1" in results[0].message


def test_toci_contains_link_rule():
    rule = TOCIContainsLinkRule()

    # Case 1: No TOCI -> []
    root_no_toci = StructureNode(id="root", tag="StructTreeRoot", standard_tag="StructTreeRoot")
    doc_no_toci = PDFDocumentModel(
        filepath="sample.pdf", filename="sample.pdf", filesize=1000, pdf_version="1.7",
        page_count=1, is_tagged=True, structure_tree=root_no_toci
    )
    assert rule.evaluate(doc_no_toci) == []

    # Case 2: TOCI without Link -> FAIL
    toci_no_link = StructureNode(id="toci1", tag="TOCI", standard_tag="TOCI", page=1)
    root_no_link = StructureNode(id="root", tag="StructTreeRoot", standard_tag="StructTreeRoot", children=[toci_no_link])
    doc_no_link = PDFDocumentModel(
        filepath="sample.pdf", filename="sample.pdf", filesize=1000, pdf_version="1.7",
        page_count=1, is_tagged=True, structure_tree=root_no_link
    )
    res_no_link = rule.evaluate(doc_no_link)
    assert len(res_no_link) == 1
    assert res_no_link[0].status == CheckStatus.FAIL

    # Case 3: TOCI with Link -> PASS
    link_child = StructureNode(id="lnk1", tag="Link", standard_tag="Link", page=1)
    toci_valid = StructureNode(id="toci1", tag="TOCI", standard_tag="TOCI", page=1, children=[link_child])
    root_valid = StructureNode(id="root", tag="StructTreeRoot", standard_tag="StructTreeRoot", children=[toci_valid])
    doc_valid = PDFDocumentModel(
        filepath="sample.pdf", filename="sample.pdf", filesize=1000, pdf_version="1.7",
        page_count=1, is_tagged=True, structure_tree=root_valid
    )
    res_valid = rule.evaluate(doc_valid)
    assert len(res_valid) == 1
    assert res_valid[0].status == CheckStatus.PASS


def test_toci_link_destination_rule():
    rule = TOCILinkDestinationRule()

    # Case 1: TOCI with link having destination -> PASS
    link_child = StructureNode(id="lnk1", tag="Link", standard_tag="Link", page=1, attributes={"Dest": "Chapter1"})
    toci = StructureNode(id="toci1", tag="TOCI", standard_tag="TOCI", page=1, children=[link_child])
    root = StructureNode(id="root", tag="StructTreeRoot", standard_tag="StructTreeRoot", children=[toci])
    doc = PDFDocumentModel(
        filepath="sample.pdf", filename="sample.pdf", filesize=1000, pdf_version="1.7",
        page_count=1, is_tagged=True, structure_tree=root
    )
    results = rule.evaluate(doc)
    assert len(results) == 1
    assert results[0].status == CheckStatus.PASS


def test_text_element_alt_text_rule():
    rule = TextElementAltTextQualityRule()

    # Case 1: Normal text elements without Alt -> PASS
    p_node = StructureNode(id="p1", tag="P", standard_tag="P", text_content="Normal paragraph text")
    root = StructureNode(id="root", tag="StructTreeRoot", standard_tag="StructTreeRoot", children=[p_node])
    doc = PDFDocumentModel(
        filepath="sample.pdf", filename="sample.pdf", filesize=1000, pdf_version="1.7",
        page_count=1, is_tagged=True, structure_tree=root
    )
    res = rule.evaluate(doc)
    assert len(res) == 1
    assert res[0].status == CheckStatus.PASS

    # Case 2: Text element with inappropriate Alt masking text -> WARNING
    p_bad = StructureNode(id="p2", tag="P", standard_tag="P", text_content="Real text content", alt_text="Masking alt text")
    root_bad = StructureNode(id="root", tag="StructTreeRoot", standard_tag="StructTreeRoot", children=[p_bad])
    doc_bad = PDFDocumentModel(
        filepath="sample.pdf", filename="sample.pdf", filesize=1000, pdf_version="1.7",
        page_count=1, is_tagged=True, structure_tree=root_bad
    )
    res_bad = rule.evaluate(doc_bad)
    assert len(res_bad) == 1
    assert res_bad[0].status == CheckStatus.WARNING


def test_note_referenced_quality_rule():
    rule = NoteReferencedQualityRule()

    # Case 1: No notes -> []
    root_empty = StructureNode(id="root", tag="StructTreeRoot", standard_tag="StructTreeRoot")
    doc_empty = PDFDocumentModel(
        filepath="sample.pdf", filename="sample.pdf", filesize=1000, pdf_version="1.7",
        page_count=1, is_tagged=True, structure_tree=root_empty
    )
    assert rule.evaluate(doc_empty) == []

    # Case 2: Note without Reference -> WARNING
    note = StructureNode(id="note1", tag="Note", standard_tag="Note", page=1)
    root = StructureNode(id="root", tag="StructTreeRoot", standard_tag="StructTreeRoot", children=[note])
    doc = PDFDocumentModel(
        filepath="sample.pdf", filename="sample.pdf", filesize=1000, pdf_version="1.7",
        page_count=1, is_tagged=True, structure_tree=root
    )
    res = rule.evaluate(doc)
    assert len(res) == 1
    assert res[0].status == CheckStatus.WARNING

    # Case 3: Note with Reference -> PASS
    ref = StructureNode(id="ref1", tag="Reference", standard_tag="Reference", page=1, attributes={"Ref": "note1"})
    root_with_ref = StructureNode(id="root", tag="StructTreeRoot", standard_tag="StructTreeRoot", children=[ref, note])
    doc_with_ref = PDFDocumentModel(
        filepath="sample.pdf", filename="sample.pdf", filesize=1000, pdf_version="1.7",
        page_count=1, is_tagged=True, structure_tree=root_with_ref
    )
    res_pass = rule.evaluate(doc_with_ref)
    assert len(res_pass) == 1
    assert res_pass[0].status == CheckStatus.PASS


def test_note_contains_label_quality_rule():
    rule = NoteContainsLabelQualityRule()

    # Case 1: Note without Lbl -> WARNING
    note_no_lbl = StructureNode(id="note1", tag="Note", standard_tag="Note", page=1)
    root = StructureNode(id="root", tag="StructTreeRoot", standard_tag="StructTreeRoot", children=[note_no_lbl])
    doc = PDFDocumentModel(
        filepath="sample.pdf", filename="sample.pdf", filesize=1000, pdf_version="1.7",
        page_count=1, is_tagged=True, structure_tree=root
    )
    res = rule.evaluate(doc)
    assert len(res) == 1
    assert res[0].status == CheckStatus.WARNING

    # Case 2: Note with Lbl -> PASS
    lbl = StructureNode(id="lbl1", tag="Lbl", standard_tag="Lbl", page=1, text_content="1")
    note_with_lbl = StructureNode(id="note1", tag="Note", standard_tag="Note", page=1, children=[lbl])
    root_lbl = StructureNode(id="root", tag="StructTreeRoot", standard_tag="StructTreeRoot", children=[note_with_lbl])
    doc_lbl = PDFDocumentModel(
        filepath="sample.pdf", filename="sample.pdf", filesize=1000, pdf_version="1.7",
        page_count=1, is_tagged=True, structure_tree=root_lbl
    )
    res_lbl = rule.evaluate(doc_lbl)
    assert len(res_lbl) == 1
    assert res_lbl[0].status == CheckStatus.PASS


def test_paragraph_contains_note_quality_rule():
    rule = ParagraphContainsNoteQualityRule()

    # Note inside P -> PASS
    note = StructureNode(id="note1", tag="Note", standard_tag="Note", page=1)
    p_node = StructureNode(id="p1", tag="P", standard_tag="P", page=1, children=[note])
    root = StructureNode(id="root", tag="StructTreeRoot", standard_tag="StructTreeRoot", children=[p_node])
    doc = PDFDocumentModel(
        filepath="sample.pdf", filename="sample.pdf", filesize=1000, pdf_version="1.7",
        page_count=1, is_tagged=True, structure_tree=root
    )
    res = rule.evaluate(doc)
    assert len(res) == 1
    assert res[0].status == CheckStatus.PASS
