"""
Tests for TaggedTextOnlyWhitespaceQualityRule (QUAL-WHITE-001).
Tests synthetic documents and structure trees covering all required cases:
1. Marked-content sequence containing only a space decoded via font mapping -> WARNING.
2. Sequence containing meaningful text -> PASS (not flagged).
3. Whitespace-only /Alt or /ActualText -> WARNING.
4. Meaningful /ActualText replacing whitespace in the underlying content -> PASS.
5. Missing or unusable font mappings with non-whitespace glyphs -> Not flagged as whitespace.
6. Nested structure elements (parent <P> and child <Span>) -> No duplicate findings.
7. Inline child <Span> with space inside non-whitespace parent <P> -> Not flagged.
8. Document with no whitespace-only tagged text -> PASS with items_count=0.
"""

import pytest
from src.pdf_inspector.core.models import (
    PDFDocumentModel, PageModel, StructureNode, CheckStatus, Severity
)
from src.pdf_inspector.engine.quality.quality_rules import TaggedTextOnlyWhitespaceQualityRule


def create_base_doc():
    doc = PDFDocumentModel(
        filepath="dummy.pdf",
        filename="dummy.pdf",
        filesize=1000,
        page_count=1,
        pdf_version="1.7",
        is_tagged=True
    )
    root = StructureNode(id="root", tag="StructTreeRoot", standard_tag="StructTreeRoot")
    doc.structure_tree = root
    doc.pages = [PageModel(page_number=1, width=612, height=792)]
    return doc, root


def test_marked_content_whitespace_flagged():
    doc, root = create_base_doc()
    # Paragraph with text_content consisting only of whitespace
    p_node = StructureNode(
        id="p1",
        tag="P",
        standard_tag="P",
        page=1,
        text_content="   \n\t  ",
        parent=root
    )
    root.children.append(p_node)

    rule = TaggedTextOnlyWhitespaceQualityRule()
    results = rule.evaluate(doc)

    assert len(results) == 1
    assert results[0].status == CheckStatus.WARNING
    assert results[0].check_id == "QUAL-WHITE-001"
    assert results[0].page == 1
    assert results[0].items_count == 1
    assert "<P>" in results[0].message


def test_meaningful_text_not_flagged():
    doc, root = create_base_doc()
    p_node = StructureNode(
        id="p1",
        tag="P",
        standard_tag="P",
        page=1,
        text_content="Hello World",
        parent=root
    )
    root.children.append(p_node)

    rule = TaggedTextOnlyWhitespaceQualityRule()
    results = rule.evaluate(doc)

    assert len(results) == 1
    assert results[0].status == CheckStatus.PASS
    assert results[0].items_count == 0


def test_whitespace_actual_text_flagged():
    doc, root = create_base_doc()
    p_node = StructureNode(
        id="p1",
        tag="P",
        standard_tag="P",
        page=1,
        actual_text="   ",
        text_content="",
        parent=root
    )
    root.children.append(p_node)

    rule = TaggedTextOnlyWhitespaceQualityRule()
    results = rule.evaluate(doc)

    assert len(results) == 1
    assert results[0].status == CheckStatus.WARNING
    assert results[0].items_count == 1


def test_whitespace_alt_text_on_text_element_flagged():
    doc, root = create_base_doc()
    caption_node = StructureNode(
        id="c1",
        tag="Caption",
        standard_tag="Caption",
        page=1,
        alt_text="  \r\n  ",
        text_content="",
        parent=root
    )
    root.children.append(caption_node)

    rule = TaggedTextOnlyWhitespaceQualityRule()
    results = rule.evaluate(doc)

    assert len(results) == 1
    assert results[0].status == CheckStatus.WARNING
    assert results[0].items_count == 1


def test_meaningful_actual_text_over_whitespace_not_flagged():
    doc, root = create_base_doc()
    # Underlying text is whitespace, but author provided valid /ActualText replacement
    span_node = StructureNode(
        id="s1",
        tag="Span",
        standard_tag="Span",
        page=1,
        actual_text="geometric",
        text_content="   ",
        parent=root
    )
    root.children.append(span_node)

    rule = TaggedTextOnlyWhitespaceQualityRule()
    results = rule.evaluate(doc)

    assert len(results) == 1
    assert results[0].status == CheckStatus.PASS
    assert results[0].items_count == 0


def test_nested_elements_no_duplicate_findings():
    doc, root = create_base_doc()
    p_node = StructureNode(
        id="p1",
        tag="P",
        standard_tag="P",
        page=1,
        text_content="   ",
        parent=root
    )
    span_child = StructureNode(
        id="s1",
        tag="Span",
        standard_tag="Span",
        page=1,
        text_content=" ",
        parent=p_node
    )
    p_node.children.append(span_child)
    root.children.append(p_node)

    rule = TaggedTextOnlyWhitespaceQualityRule()
    results = rule.evaluate(doc)

    # Exactly 1 warning on the paragraph, not duplicate on both P and Span
    assert len(results) == 1
    assert results[0].status == CheckStatus.WARNING
    assert results[0].items_count == 1
    assert "<P>" in results[0].message


def test_inline_space_span_inside_meaningful_p_not_flagged():
    doc, root = create_base_doc()
    p_node = StructureNode(
        id="p1",
        tag="P",
        standard_tag="P",
        page=1,
        text_content="Hello World",
        parent=root
    )
    # Inline span for spacing between styled words
    span_child = StructureNode(
        id="s1",
        tag="Span",
        standard_tag="Span",
        page=1,
        text_content=" ",
        parent=p_node
    )
    p_node.children.append(span_child)
    root.children.append(p_node)

    rule = TaggedTextOnlyWhitespaceQualityRule()
    results = rule.evaluate(doc)

    # No warning because the parent paragraph has meaningful text
    assert len(results) == 1
    assert results[0].status == CheckStatus.PASS
    assert results[0].items_count == 0


def test_document_with_no_whitespace_issues():
    doc, root = create_base_doc()
    h1_node = StructureNode(
        id="h1",
        tag="H1",
        standard_tag="H1",
        page=1,
        text_content="Document Title",
        parent=root
    )
    p_node = StructureNode(
        id="p1",
        tag="P",
        standard_tag="P",
        page=1,
        text_content="Normal paragraph content.",
        parent=root
    )
    root.children.extend([h1_node, p_node])

    rule = TaggedTextOnlyWhitespaceQualityRule()
    results = rule.evaluate(doc)

    assert len(results) == 1
    assert results[0].status == CheckStatus.PASS
    assert results[0].items_count == 0


def test_mcid_texts_whitespace_from_page_model():
    doc, root = create_base_doc()
    doc.pages[0].mcid_texts = {10: "   "}
    p_node = StructureNode(
        id="p1",
        tag="P",
        standard_tag="P",
        page=1,
        mcids=[10],
        mcid_entries=[(10, 1)],
        parent=root
    )
    root.children.append(p_node)

    rule = TaggedTextOnlyWhitespaceQualityRule()
    results = rule.evaluate(doc)

    assert len(results) == 1
    assert results[0].status == CheckStatus.WARNING
    assert results[0].items_count == 1
    assert results[0].page == 1


def test_unusable_font_mapping_non_whitespace_not_flagged():
    doc, root = create_base_doc()
    doc.pages[0].mcid_texts = {10: "X"}
    p_node = StructureNode(
        id="p1",
        tag="P",
        standard_tag="P",
        page=1,
        mcids=[10],
        mcid_entries=[(10, 1)],
        parent=root
    )
    root.children.append(p_node)

    rule = TaggedTextOnlyWhitespaceQualityRule()
    results = rule.evaluate(doc)

    assert len(results) == 1
    assert results[0].status == CheckStatus.PASS
    assert results[0].items_count == 0


def test_synthetic_pdf_stream_and_cmap_decoding(tmp_path):
    import pikepdf
    # Build a tiny synthetic tagged PDF with marked content using font /C0 mapping code 3 to space
    pdf = pikepdf.new()
    
    # Simple CMap stream
    cmap_content = b"""/CIDInit /ProcSet findresource begin
12 dict begin
begincmap
1 begincodespacerange
<0000> <FFFF>
endcodespacerange
1 beginbfchar
<0003> <0020>
endbfchar
endcmap
CMapName currentdict /CMap defineresource pop
end
end"""
    cmap_stream = pdf.make_stream(cmap_content)

    font_dict = pikepdf.Dictionary({
        "/Type": pikepdf.Name("/Font"),
        "/Subtype": pikepdf.Name("/Type0"),
        "/BaseFont": pikepdf.Name("/TestFont"),
        "/Encoding": pikepdf.Name("/Identity-H"),
        "/ToUnicode": cmap_stream
    })

    # Content stream with marked content
    content_stream_data = b"""BT
/Caption <</MCID 0>> BDC
/F0 12 Tf
<0003> Tj
EMC
ET"""
    page_stream = pdf.make_stream(content_stream_data)

    page_dict = pikepdf.Dictionary({
        "/Type": pikepdf.Name("/Page"),
        "/MediaBox": pikepdf.Array([0, 0, 612, 792]),
        "/Contents": page_stream,
        "/Resources": pikepdf.Dictionary({
            "/Font": pikepdf.Dictionary({
                "/F0": font_dict
            })
        })
    })

    pdf.pages.append(pikepdf.Page(page_dict))
    pdf_file = str(tmp_path / "synthetic_whitespace.pdf")
    pdf.save(pdf_file)
    pdf.close()

    # Now create doc model referencing this file
    doc = PDFDocumentModel(
        filepath=pdf_file,
        filename="synthetic_whitespace.pdf",
        filesize=2000,
        page_count=1,
        pdf_version="1.7",
        is_tagged=True
    )
    root = StructureNode(id="root", tag="StructTreeRoot", standard_tag="StructTreeRoot")
    doc.structure_tree = root
    doc.pages = [PageModel(page_number=1, width=612, height=792)]
    caption_node = StructureNode(
        id="c1",
        tag="Caption",
        standard_tag="Caption",
        page=1,
        mcids=[0],
        mcid_entries=[(0, 1)],
        parent=root
    )
    root.children.append(caption_node)

    rule = TaggedTextOnlyWhitespaceQualityRule()
    results = rule.evaluate(doc)

    assert len(results) == 1
    assert results[0].status == CheckStatus.WARNING
    assert results[0].items_count == 1
    assert "<Caption>" in results[0].message

