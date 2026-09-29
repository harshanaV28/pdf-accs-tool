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

    # Case 1: Font unembedded
    f1 = FontModel("Helvetica", "Type1", is_embedded=False, is_subset=False, has_tounicode=True, encoding="WinAnsi", pages=[1])
    doc1 = PDFDocumentModel(filepath="", filename="f.pdf", filesize=10, pdf_version="1.7", page_count=1, fonts=[f1])
    res1 = rule.evaluate(doc1)
    assert res1[0].status == CheckStatus.FAIL

    # Case 2: Font embedded
    f2 = FontModel("ABCDEF+Arial", "TrueType", is_embedded=True, is_subset=True, has_tounicode=True, encoding="WinAnsi", pages=[1])
    doc2 = PDFDocumentModel(filepath="", filename="f.pdf", filesize=10, pdf_version="1.7", page_count=1, fonts=[f2])
    res2 = rule.evaluate(doc2)
    assert res2[0].status == CheckStatus.PASS


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
