"""
Unit tests for PDF/UA and WCAG Rules
"""

import pytest
from src.pdf_inspector.core.models import (
    PDFDocumentModel, PageModel, StructureNode, FontModel, ImageModel, CheckStatus
)
from src.pdf_inspector.engine.pdf_ua.syntax_rules import PDFSyntaxBasicRule
from src.pdf_inspector.engine.pdf_ua.font_rules import FontEmbeddingRule
from src.pdf_inspector.engine.pdf_ua.content_rules import TaggedPDFRule
from src.pdf_inspector.engine.pdf_ua.language_rules import DocumentLanguageRule
from src.pdf_inspector.engine.pdf_ua.metadata_rules import MetadataCompletenessRule
from src.pdf_inspector.engine.pdf_ua.document_settings_rules import DisplayDocTitleRule
from src.pdf_inspector.engine.wcag.wcag_rules import WCAGTextAlternativesRule, WCAGNavigableRule


def test_tagged_pdf_rule():
    rule = TaggedPDFRule()

    # Case 1: Untagged document
    doc_untagged = PDFDocumentModel(
        filepath="", filename="untagged.pdf", filesize=100, pdf_version="1.7",
        page_count=1, is_tagged=False, structure_tree=None
    )
    res = rule.evaluate(doc_untagged)
    assert res[0].status == CheckStatus.FAIL

    # Case 2: Tagged document with structure tree
    doc_tagged = PDFDocumentModel(
        filepath="", filename="tagged.pdf", filesize=100, pdf_version="1.7",
        page_count=1, is_tagged=True, structure_tree=StructureNode("root", "StructTreeRoot", "StructTreeRoot")
    )
    res = rule.evaluate(doc_tagged)
    assert res[0].status == CheckStatus.PASS


def test_font_embedding_rule():
    rule = FontEmbeddingRule()

    # Case 1: One unembedded font used on one page
    f1 = FontModel("Helvetica", "Type1", is_embedded=False, is_subset=False, has_tounicode=True, encoding="WinAnsi", pages=[1], is_used=True)
    doc1 = PDFDocumentModel(filepath="", filename="f.pdf", filesize=10, pdf_version="1.7", page_count=1, fonts=[f1])
    res1 = rule.evaluate(doc1)
    assert len(res1) == 1
    assert res1[0].status == CheckStatus.FAIL
    assert res1[0].page == 1
    assert res1[0].items_count == 1

    # Case 2: One unembedded font used on multiple pages (4 pages -> 4 FAIL evaluation records)
    f2 = FontModel("Arial", "TrueType", is_embedded=False, is_subset=False, has_tounicode=True, encoding="WinAnsi", pages=[1, 2, 3, 4], is_used=True)
    doc2 = PDFDocumentModel(filepath="", filename="f.pdf", filesize=10, pdf_version="1.7", page_count=4, fonts=[f2])
    res2 = rule.evaluate(doc2)
    fail_res2 = [r for r in res2 if r.status == CheckStatus.FAIL]
    assert len(fail_res2) == 4
    assert [r.page for r in fail_res2] == [1, 2, 3, 4]
    for r in fail_res2:
        assert r.items_count == 1

    # Case 3: Multiple unembedded fonts on distinct pages
    f3_1 = FontModel("Helvetica-Bold", "Type1", is_embedded=False, is_subset=False, has_tounicode=True, encoding="WinAnsi", pages=[1, 4], is_used=True)
    f3_2 = FontModel("Helvetica", "Type1", is_embedded=False, is_subset=False, has_tounicode=True, encoding="WinAnsi", pages=[1, 2, 3], is_used=True)
    f3_3 = FontModel("ABCDEF+Courier", "Type1", is_embedded=True, is_subset=True, has_tounicode=True, encoding="WinAnsi", pages=[1, 2, 3, 4], is_used=True)
    doc3 = PDFDocumentModel(filepath="", filename="f.pdf", filesize=10, pdf_version="1.7", page_count=4, fonts=[f3_1, f3_2, f3_3])
    res3 = rule.evaluate(doc3)
    fail_res3 = [r for r in res3 if r.status == CheckStatus.FAIL]
    assert len(fail_res3) == 5  # 2 for f3_1 + 3 for f3_2
    pass_res3 = [r for r in res3 if r.status == CheckStatus.PASS]
    assert len(pass_res3) == 1
    assert pass_res3[0].items_count == 1  # 1 embedded font passed

    # Case 4: All embedded fonts
    f4 = FontModel("ABCDEF+Arial", "TrueType", is_embedded=True, is_subset=True, has_tounicode=True, encoding="WinAnsi", pages=[1, 2], is_used=True)
    doc4 = PDFDocumentModel(filepath="", filename="f.pdf", filesize=10, pdf_version="1.7", page_count=2, fonts=[f4])
    res4 = rule.evaluate(doc4)
    assert len(res4) == 1
    assert res4[0].status == CheckStatus.PASS
    assert res4[0].items_count == 1

    # Case 5: A font listed in the PDF but not actually used (is_used=False) -> should NOT produce failures
    f5_unused = FontModel("UnusedFont", "Type1", is_embedded=False, is_subset=False, has_tounicode=False, encoding="Custom", pages=[1, 2], is_used=False)
    f5_used = FontModel("ABCDEF+Arial", "TrueType", is_embedded=True, is_subset=True, has_tounicode=True, encoding="WinAnsi", pages=[1], is_used=True)
    doc5 = PDFDocumentModel(filepath="", filename="f.pdf", filesize=10, pdf_version="1.7", page_count=2, fonts=[f5_unused, f5_used])
    res5 = rule.evaluate(doc5)
    fail_res5 = [r for r in res5 if r.status == CheckStatus.FAIL]
    assert len(fail_res5) == 0
    assert any(r.status == CheckStatus.PASS for r in res5)

    # Case 6: Same font family appearing with different subsets/identities
    f6_1 = FontModel("ABCDEF+Arial", "TrueType", is_embedded=True, is_subset=True, has_tounicode=True, encoding="WinAnsi", pages=[1], is_used=True)
    f6_2 = FontModel("GHIJKL+Arial", "TrueType", is_embedded=True, is_subset=True, has_tounicode=True, encoding="WinAnsi", pages=[2], is_used=True)
    doc6 = PDFDocumentModel(filepath="", filename="f.pdf", filesize=10, pdf_version="1.7", page_count=2, fonts=[f6_1, f6_2])
    res6 = rule.evaluate(doc6)
    assert all(r.status == CheckStatus.PASS for r in res6)
    assert res6[0].items_count == 2


def test_language_rule():
    rule = DocumentLanguageRule()

    # Missing language
    doc_nolang = PDFDocumentModel(filepath="", filename="l.pdf", filesize=10, pdf_version="1.7", page_count=1, language=None)
    assert rule.evaluate(doc_nolang)[0].status == CheckStatus.FAIL

    # Valid BCP 47
    doc_valid = PDFDocumentModel(filepath="", filename="l.pdf", filesize=10, pdf_version="1.7", page_count=1, language="en-US")
    assert rule.evaluate(doc_valid)[0].status == CheckStatus.PASS


def test_display_doc_title_rule():
    rule = DisplayDocTitleRule()

    doc_false = PDFDocumentModel(filepath="", filename="d.pdf", filesize=10, pdf_version="1.7", page_count=1, display_doc_title=False)
    assert rule.evaluate(doc_false)[0].status == CheckStatus.FAIL

    doc_true = PDFDocumentModel(filepath="", filename="d.pdf", filesize=10, pdf_version="1.7", page_count=1, display_doc_title=True)
    assert rule.evaluate(doc_true)[0].status == CheckStatus.PASS


def test_wcag_text_alternatives():
    rule = WCAGTextAlternativesRule()

    # Image missing alt text
    img_no_alt = ImageModel("img1", 1, (10, 10, 100, 100), 200, 200, "RGB", has_alt=False)
    doc_bad = PDFDocumentModel(filepath="", filename="i.pdf", filesize=10, pdf_version="1.7", page_count=1, images=[img_no_alt])
    assert rule.evaluate(doc_bad)[0].status == CheckStatus.FAIL

    # Image with alt text
    img_alt = ImageModel("img2", 1, (10, 10, 100, 100), 200, 200, "RGB", has_alt=True, alt_text="Bar chart showing growth")
    doc_good = PDFDocumentModel(filepath="", filename="i.pdf", filesize=10, pdf_version="1.7", page_count=1, images=[img_alt])
    assert rule.evaluate(doc_good)[0].status == CheckStatus.PASS


def test_parent_tree_integrity_rule():
    from src.pdf_inspector.engine.pdf_ua.parent_tree_rules import ParentTreeIntegrityRule
    rule = ParentTreeIntegrityRule()

    # Case 1: Tagged but missing ParentTree
    tree = StructureNode("root", "StructTreeRoot", "StructTreeRoot")
    doc_no_pt = PDFDocumentModel(
        filepath="", filename="p.pdf", filesize=10, pdf_version="1.7", page_count=1,
        is_tagged=True, structure_tree=tree, has_parent_tree=False
    )
    assert any(r.status == CheckStatus.FAIL for r in rule.evaluate(doc_no_pt))

    # Case 2: Tagged with valid ParentTree
    doc_with_pt = PDFDocumentModel(
        filepath="", filename="p.pdf", filesize=10, pdf_version="1.7", page_count=1,
        is_tagged=True, structure_tree=tree, has_parent_tree=True, parent_tree_valid=True,
        parent_tree_entries_count=2
    )
    assert any(r.status == CheckStatus.PASS for r in rule.evaluate(doc_with_pt))


def test_artifact_in_structure_tree_rule():
    from src.pdf_inspector.engine.pdf_ua.artifact_rules import ArtifactInStructureTreeRule
    rule = ArtifactInStructureTreeRule()

    # Case 1: Artifact tag erroneously inside structure tree
    art_node = StructureNode("art1", "Artifact", "Artifact")
    tree_bad = StructureNode("root", "StructTreeRoot", "StructTreeRoot", children=[art_node])
    doc_bad = PDFDocumentModel(
        filepath="", filename="a.pdf", filesize=10, pdf_version="1.7", page_count=1,
        is_tagged=True, structure_tree=tree_bad
    )
    assert any(r.status == CheckStatus.FAIL for r in rule.evaluate(doc_bad))

    # Case 2: Clean structure tree with no Artifact tags
    p_node = StructureNode("p1", "P", "P")
    tree_good = StructureNode("root", "StructTreeRoot", "StructTreeRoot", children=[p_node])
    doc_good = PDFDocumentModel(
        filepath="", filename="a.pdf", filesize=10, pdf_version="1.7", page_count=1,
        is_tagged=True, structure_tree=tree_good
    )
    assert any(r.status == CheckStatus.PASS for r in rule.evaluate(doc_good))


def test_annotation_tagged_rule():
    from src.pdf_inspector.engine.pdf_ua.annotation_rules import AnnotationTaggedRule
    from src.pdf_inspector.core.models import AnnotationModel
    rule = AnnotationTaggedRule()

    # Case 1: Untagged link annotation
    ann_bad = AnnotationModel(id="ann1", page=1, subtype="Link", rect=(10, 10, 100, 30), is_tagged=False)
    doc_bad = PDFDocumentModel(
        filepath="", filename="ann.pdf", filesize=10, pdf_version="1.7", page_count=1,
        is_tagged=True, annotations=[ann_bad]
    )
    assert any(r.status == CheckStatus.FAIL for r in rule.evaluate(doc_bad))

    # Case 2: Tagged link annotation
    ann_good = AnnotationModel(id="ann2", page=1, subtype="Link", rect=(10, 10, 100, 30), is_tagged=True)
    doc_good = PDFDocumentModel(
        filepath="", filename="ann.pdf", filesize=10, pdf_version="1.7", page_count=1,
        is_tagged=True, annotations=[ann_good]
    )
    assert any(r.status == CheckStatus.PASS for r in rule.evaluate(doc_good))


def test_page_tab_order_rule():
    from src.pdf_inspector.engine.pdf_ua.annotation_rules import PageTabOrderRule
    from src.pdf_inspector.core.models import PageModel, AnnotationModel
    rule = PageTabOrderRule()

    # Case 1: Page with annotations but missing /Tabs /S -> FAIL
    p_bad = PageModel(page_number=1, width=612, height=792, tab_order_mode="Unspecified", annotations_count=2)
    doc_bad = PDFDocumentModel(
        filepath="", filename="tab.pdf", filesize=10, pdf_version="1.7", page_count=1,
        is_tagged=True, pages=[p_bad]
    )
    res_bad = rule.evaluate(doc_bad)
    assert any(r.status == CheckStatus.FAIL for r in res_bad)
    assert res_bad[0].page == 1

    # Case 2: Page with annotations having /Tabs /S -> PASS
    p_good = PageModel(page_number=1, width=612, height=792, tab_order_mode="S", annotations_count=2)
    doc_good = PDFDocumentModel(
        filepath="", filename="tab.pdf", filesize=10, pdf_version="1.7", page_count=1,
        is_tagged=True, pages=[p_good]
    )
    res_good = rule.evaluate(doc_good)
    assert any(r.status == CheckStatus.PASS for r in res_good)

    # Case 3: Page without annotations -> PASS
    p_no_annot = PageModel(page_number=1, width=612, height=792, tab_order_mode="Unspecified", annotations_count=0)
    doc_no_annot = PDFDocumentModel(
        filepath="", filename="tab.pdf", filesize=10, pdf_version="1.7", page_count=1,
        is_tagged=True, pages=[p_no_annot]
    )
    assert any(r.status == CheckStatus.PASS for r in rule.evaluate(doc_no_annot))


def test_metadata_completeness_rule():
    rule = MetadataCompletenessRule()

    # Missing Title
    doc_notitle = PDFDocumentModel(
        filepath="", filename="m.pdf", filesize=10, pdf_version="1.7", page_count=1,
        title=None
    )
    assert any(r.status == CheckStatus.FAIL and "Title" in r.message for r in rule.evaluate(doc_notitle))

    # Fully populated metadata with PDF/UA declaration
    doc_complete = PDFDocumentModel(
        filepath="", filename="m.pdf", filesize=10, pdf_version="1.7", page_count=1,
        title="Valid Accessibility Report", author="Audit Team", subject="Auditing",
        pdfua_identifier_present=True
    )
    assert any(r.status == CheckStatus.PASS for r in rule.evaluate(doc_complete))


def test_form_field_accessibility_rule():
    from src.pdf_inspector.engine.pdf_ua.form_rules import FormFieldAccessibilityRule
    from src.pdf_inspector.core.models import FormFieldModel
    rule = FormFieldAccessibilityRule()

    # Case 1: Form field missing /TU tooltip
    f_bad = FormFieldModel(name="SignatureField", field_type="Sig", tooltip=None, page=1)
    doc_bad = PDFDocumentModel(filepath="", filename="form_bad.pdf", filesize=100, pdf_version="1.7", page_count=1, form_fields=[f_bad])
    res_bad = rule.evaluate(doc_bad)
    assert any(r.status == CheckStatus.FAIL and "/TU" in r.message for r in res_bad)

    # Case 2: Form field with valid /TU tooltip
    f_good = FormFieldModel(name="EmailField", field_type="Text", tooltip="Enter your email address", page=1)
    doc_good = PDFDocumentModel(filepath="", filename="form_good.pdf", filesize=100, pdf_version="1.7", page_count=1, form_fields=[f_good])
    res_good = rule.evaluate(doc_good)
    assert any(r.status == CheckStatus.PASS for r in res_good)
    assert not any(r.status == CheckStatus.FAIL for r in res_good)

    # Case 3: Document without form fields
    doc_empty = PDFDocumentModel(filepath="", filename="form_none.pdf", filesize=100, pdf_version="1.7", page_count=1, form_fields=[])
    res_empty = rule.evaluate(doc_empty)
    assert any(r.status == CheckStatus.PASS for r in res_empty)


def test_table_structure_headers_rule():
    from src.pdf_inspector.engine.pdf_ua.table_rules import TableStructureHeadersRule
    from src.pdf_inspector.core.models import TableModel
    rule = TableStructureHeadersRule()

    # Case 1: Table with header cells
    t_good = TableModel(id="tbl1", page=1, rows_count=3, cols_count=3, has_headers=True, header_cells_count=3, data_cells_count=6)
    doc_good = PDFDocumentModel(filepath="", filename="tbl_good.pdf", filesize=100, pdf_version="1.7", page_count=1, tables=[t_good])
    res_good = rule.evaluate(doc_good)
    assert any(r.status == CheckStatus.PASS and "header cell(s)" in r.message for r in res_good)

    # Case 2: Table without header cells
    t_bad = TableModel(id="tbl2", page=2, rows_count=3, cols_count=3, has_headers=False, header_cells_count=0, data_cells_count=9)
    doc_bad = PDFDocumentModel(filepath="", filename="tbl_bad.pdf", filesize=100, pdf_version="1.7", page_count=2, tables=[t_bad])
    res_bad = rule.evaluate(doc_bad)
    assert any(r.status == CheckStatus.FAIL and "no designated header" in r.message for r in res_bad)


def test_bookmark_structure_rule():
    from src.pdf_inspector.engine.pdf_ua.document_settings_rules import BookmarkStructureRule
    from src.pdf_inspector.core.models import BookmarkModel
    rule = BookmarkStructureRule()

    # Case 1: Document > 20 pages without bookmarks -> WARNING
    doc_long_nobookmarks = PDFDocumentModel(filepath="", filename="long.pdf", filesize=100, pdf_version="1.7", page_count=25, bookmarks=[])
    res_long = rule.evaluate(doc_long_nobookmarks)
    assert any(r.status == CheckStatus.WARNING for r in res_long)

    # Case 2: Document <= 20 pages without bookmarks -> PASS (informational)
    doc_short_nobookmarks = PDFDocumentModel(filepath="", filename="short.pdf", filesize=100, pdf_version="1.7", page_count=10, bookmarks=[])
    res_short = rule.evaluate(doc_short_nobookmarks)
    assert any(r.status == CheckStatus.PASS and "optional" in r.message for r in res_short)

    # Case 3: Document with bookmarks -> PASS
    b1 = BookmarkModel(title="Chapter 1", level=1, page=1)
    doc_with_bm = PDFDocumentModel(filepath="", filename="bm.pdf", filesize=100, pdf_version="1.7", page_count=30, bookmarks=[b1])
    res_bm = rule.evaluate(doc_with_bm)
    assert any(r.status == CheckStatus.PASS and "contains" in r.message for r in res_bm)

