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
    PDFDocumentModel, PageModel, StructureNode, CheckStatus, Severity, LinkModel, TableModel, ArtifactOccurrenceModel
)
from src.pdf_inspector.engine.quality.quality_rules import (
    TaggedContentPageBoundariesRule,
    TOCIContainsLinkRule,
    TOCILinkDestinationRule,
    TextElementAltTextQualityRule,
    NoteReferencedQualityRule,
    NoteContainsLabelQualityRule,
    ParagraphContainsNoteQualityRule,
    HeadingHierarchyQualityRule,
    TableRegularityQualityRule,
    ArtifactedContentOnPageBodyRule,
    LinkCompletenessQualityRule,
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


def test_heading_hierarchy_quality_rule():
    rule = HeadingHierarchyQualityRule()

    # Case 1: Valid hierarchy (H1 -> H2 -> H3) -> PASS only
    h1 = StructureNode(id="h1", tag="H1", standard_tag="H1", page=1)
    h2 = StructureNode(id="h2", tag="H2", standard_tag="H2", page=1)
    h3 = StructureNode(id="h3", tag="H3", standard_tag="H3", page=2)
    root_valid = StructureNode(id="root", tag="StructTreeRoot", standard_tag="StructTreeRoot", children=[h1, h2, h3])
    doc_valid = PDFDocumentModel(filepath="", filename="h.pdf", filesize=10, pdf_version="1.7", page_count=2, is_tagged=True, structure_tree=root_valid)
    res_valid = rule.evaluate(doc_valid)
    assert len(res_valid) == 1
    assert res_valid[0].status == CheckStatus.PASS
    assert res_valid[0].items_count == 1

    # Case 2: First heading is H2 (starts with non-H1) -> WARNING only, no dual PASS
    root_bad_start = StructureNode(id="root", tag="StructTreeRoot", standard_tag="StructTreeRoot", children=[h2, h3])
    doc_bad_start = PDFDocumentModel(filepath="", filename="h.pdf", filesize=10, pdf_version="1.7", page_count=2, is_tagged=True, structure_tree=root_bad_start)
    res_bad_start = rule.evaluate(doc_bad_start)
    assert len(res_bad_start) == 1
    assert res_bad_start[0].status == CheckStatus.WARNING
    assert "instead of <H1>" in res_bad_start[0].message
    assert not any(r.status == CheckStatus.PASS for r in res_bad_start)

    # Case 3: Skipped jump (H1 -> H3) -> WARNING only, no dual PASS
    root_skip = StructureNode(id="root", tag="StructTreeRoot", standard_tag="StructTreeRoot", children=[h1, h3])
    doc_skip = PDFDocumentModel(filepath="", filename="h.pdf", filesize=10, pdf_version="1.7", page_count=2, is_tagged=True, structure_tree=root_skip)
    res_skip = rule.evaluate(doc_skip)
    assert len(res_skip) == 1
    assert res_skip[0].status == CheckStatus.WARNING
    assert "Heading level skipped" in res_skip[0].message
    assert not any(r.status == CheckStatus.PASS for r in res_skip)

    # Case 4: No headings in document -> WARNING
    root_none = StructureNode(id="root", tag="StructTreeRoot", standard_tag="StructTreeRoot", children=[])
    doc_none = PDFDocumentModel(filepath="", filename="h.pdf", filesize=10, pdf_version="1.7", page_count=1, is_tagged=True, structure_tree=root_none)
    res_none = rule.evaluate(doc_none)
    assert len(res_none) == 1
    assert res_none[0].status == CheckStatus.WARNING


def test_table_regularity_quality_rule():
    rule = TableRegularityQualityRule()

    # Case 1: No tables -> []
    doc_notables = PDFDocumentModel(filepath="", filename="t.pdf", filesize=10, pdf_version="1.7", page_count=1, tables=[])
    assert rule.evaluate(doc_notables) == []

    # Case 2: All regular tables -> PASS
    t1 = TableModel(id="tbl1", page=1, rows_count=3, cols_count=3, has_headers=True, header_cells_count=3, data_cells_count=6, is_regular=True, bbox=(0, 0, 100, 100))
    t2 = TableModel(id="tbl2", page=2, rows_count=2, cols_count=2, has_headers=True, header_cells_count=2, data_cells_count=2, is_regular=True, bbox=(0, 0, 100, 100))
    doc_all_regular = PDFDocumentModel(filepath="", filename="t.pdf", filesize=10, pdf_version="1.7", page_count=2, tables=[t1, t2])
    res_reg = rule.evaluate(doc_all_regular)
    assert len(res_reg) == 1
    assert res_reg[0].status == CheckStatus.PASS
    assert res_reg[0].items_count == 2

    # Case 3: Mixed regular and irregular tables -> WARNING for irregular, PASS for regular
    t_irreg = TableModel(id="tbl3", page=3, rows_count=4, cols_count=3, has_headers=True, header_cells_count=3, data_cells_count=9, is_regular=False, bbox=(0, 0, 100, 100))
    doc_mixed = PDFDocumentModel(filepath="", filename="t.pdf", filesize=10, pdf_version="1.7", page_count=3, tables=[t1, t_irreg])
    res_mixed = rule.evaluate(doc_mixed)
    assert len(res_mixed) == 2
    warns = [r for r in res_mixed if r.status == CheckStatus.WARNING]
    passes = [r for r in res_mixed if r.status == CheckStatus.PASS]
    assert len(warns) == 1
    assert len(passes) == 1
    assert passes[0].items_count == 1


def test_artifacted_content_on_page_body_rule():
    rule = ArtifactedContentOnPageBodyRule()

    # Case 1: No artifacts -> []
    p0 = PageModel(page_number=1, width=612, height=792, artifacts=[])
    doc_noart = PDFDocumentModel(filepath="", filename="a.pdf", filesize=10, pdf_version="1.7", page_count=1, pages=[p0])
    assert rule.evaluate(doc_noart) == []

    # Case 2: Strictly pagination artifact -> PASS with items_count=0
    art_page = ArtifactOccurrenceModel(page_number=1, is_inside_tagged=False, text_snippet="Page 1 of 5")
    p1 = PageModel(page_number=1, width=612, height=792, artifacts=[art_page])
    doc_pag = PDFDocumentModel(filepath="", filename="a.pdf", filesize=10, pdf_version="1.7", page_count=1, pages=[p1])
    res_pag = rule.evaluate(doc_pag)
    assert len(res_pag) == 1
    assert res_pag[0].status == CheckStatus.PASS
    assert res_pag[0].items_count == 0

    # Case 3: Readable body text artifact -> WARNING
    art_body = ArtifactOccurrenceModel(page_number=1, is_inside_tagged=False, text_snippet="Important substantive text in body")
    p2 = PageModel(page_number=1, width=612, height=792, artifacts=[art_body])
    doc_body = PDFDocumentModel(filepath="", filename="a.pdf", filesize=10, pdf_version="1.7", page_count=1, pages=[p2])
    res_body = rule.evaluate(doc_body)
    assert len(res_body) == 1
    assert res_body[0].status == CheckStatus.WARNING
    assert res_body[0].items_count == 1


def test_link_completeness_quality_rule():
    rule = LinkCompletenessQualityRule()

    # Case 1: No links -> []
    root_empty = StructureNode(id="root", tag="StructTreeRoot", standard_tag="StructTreeRoot")
    doc_nolinks = PDFDocumentModel(filepath="", filename="l.pdf", filesize=10, pdf_version="1.7", page_count=1, is_tagged=True, structure_tree=root_empty)
    assert rule.evaluate(doc_nolinks) == []

    # Case 2: Complete link with text -> PASS with items_count=0
    lnk_good = StructureNode(id="lnk1", tag="Link", standard_tag="Link", page=1, text_content="Visit Website")
    root_good = StructureNode(id="root", tag="StructTreeRoot", standard_tag="StructTreeRoot", children=[lnk_good])
    doc_good = PDFDocumentModel(filepath="", filename="l.pdf", filesize=10, pdf_version="1.7", page_count=1, is_tagged=True, structure_tree=root_good)
    res_good = rule.evaluate(doc_good)
    assert len(res_good) == 1
    assert res_good[0].status == CheckStatus.PASS
    assert res_good[0].items_count == 0

    # Case 3: Incomplete empty link -> FAIL with items_count=1
    lnk_bad = StructureNode(id="lnk2", tag="Link", standard_tag="Link", page=1, text_content="")
    root_bad = StructureNode(id="root", tag="StructTreeRoot", standard_tag="StructTreeRoot", children=[lnk_bad])
    doc_bad = PDFDocumentModel(filepath="", filename="l.pdf", filesize=10, pdf_version="1.7", page_count=1, is_tagged=True, structure_tree=root_bad)
    res_bad = rule.evaluate(doc_bad)
    assert len(res_bad) == 1
    assert res_bad[0].status == CheckStatus.FAIL
    assert res_bad[0].items_count == 1
