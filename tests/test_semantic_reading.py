"""
Unit and Regression Tests for Semantic Reading Engine
Validates the logical reading sequence, heading text resolution, figure alt text separation,
list hierarchy preservation, mathematical content distinction, and untagged handling.
"""

import pytest
from src.pdf_inspector.core.models import (
    PDFDocumentModel, StructureNode, PageModel, CheckStatus
)
from src.pdf_inspector.engine.semantic_reading import (
    SemanticReadingEngine, SemanticReadingResult, SemanticItem
)


@pytest.fixture
def base_doc():
    """Returns a basic tagged PDFDocumentModel fixture."""
    root = StructureNode(
        id="root",
        tag="StructTreeRoot",
        standard_tag="StructTreeRoot",
        title="Root"
    )
    return PDFDocumentModel(
        filepath="test.pdf",
        filename="test.pdf",
        filesize=1024,
        pdf_version="1.7",
        page_count=1,
        title="Accessible Engineering Report",
        is_tagged=True,
        structure_tree=root
    )


def test_heading_with_valid_text(base_doc):
    """1. Heading with valid text renders real text and never '[Heading Text]'."""
    h1 = StructureNode(
        id="h1_1",
        tag="H1",
        standard_tag="H1",
        text_content="Chapter 15 Solutions",
        page=1,
        obj_num=101
    )
    base_doc.structure_tree.children = [h1]

    engine = SemanticReadingEngine()
    result = engine.generate(base_doc)

    assert result.is_tagged is True
    assert result.total_headings == 1
    assert "HEADING LEVEL 1" in result.plain_text
    assert "Chapter 15 Solutions" in result.plain_text
    assert "[Heading Text]" not in result.plain_text
    assert "[Heading Text]" not in result.html


def test_heading_with_no_extractable_text(base_doc):
    """2. Heading with no extractable text shows technical metadata and never '[Heading Text]'."""
    h2 = StructureNode(
        id="h2_empty",
        tag="H2",
        standard_tag="H2",
        text_content="",
        title="",
        actual_text=None,
        page=300,
        obj_num=3798
    )
    base_doc.structure_tree.children = [h2]

    engine = SemanticReadingEngine()
    result = engine.generate(base_doc)

    assert result.total_headings == 1
    assert "HEADING LEVEL 2" in result.plain_text
    assert "[No readable text available]" in result.plain_text
    assert "Structure role: H2" in result.plain_text
    assert "Page: 300" in result.plain_text
    assert "Object: 3798" in result.plain_text
    assert "[Heading Text]" not in result.plain_text
    assert "[Heading Text]" not in result.html


def test_figure_with_valid_alt_text(base_doc):
    """3. Figure with valid Alt text displays Alternative text clearly."""
    fig = StructureNode(
        id="fig_1",
        tag="Figure",
        standard_tag="Figure",
        alt_text="Diagram of a four-stroke internal combustion engine showing intake cycle.",
        page=5,
        obj_num=202
    )
    base_doc.structure_tree.children = [fig]

    engine = SemanticReadingEngine()
    result = engine.generate(base_doc)

    assert result.total_figures == 1
    assert "FIGURE" in result.plain_text
    assert "Alternative text:" in result.plain_text
    assert "Diagram of a four-stroke internal combustion engine" in result.plain_text
    assert "Missing" not in result.plain_text


def test_figure_with_missing_alt(base_doc):
    """4. Figure with missing Alt displays 'Alternative text: Missing' and technical metadata."""
    fig = StructureNode(
        id="fig_missing",
        tag="Figure",
        standard_tag="Figure",
        alt_text=None,
        page=12,
        obj_num=505
    )
    base_doc.structure_tree.children = [fig]

    engine = SemanticReadingEngine()
    result = engine.generate(base_doc)

    assert result.total_figures == 1
    assert "FIGURE" in result.plain_text
    assert "Alternative text: Missing" in result.plain_text
    assert "Page: 12" in result.html
    assert "Object: 505" in result.html


def test_decorative_artifact_element(base_doc):
    """5. Decorative artifact displays 'Alternative text not required'."""
    artifact = StructureNode(
        id="art_1",
        tag="Figure",
        standard_tag="Figure",
        is_artifact=True,
        page=1,
        obj_num=10
    )
    base_doc.structure_tree.children = [artifact]

    engine = SemanticReadingEngine()
    result = engine.generate(base_doc)

    assert "Decorative / Artifact" in result.plain_text
    assert "Alternative text not required" in result.plain_text
    assert "Missing" not in result.plain_text


def test_figure_containing_extracted_graphic_text(base_doc):
    """6. Figure with extracted graphic text clearly separates it from author Alt text."""
    fig = StructureNode(
        id="fig_with_text",
        tag="Figure",
        standard_tag="Figure",
        alt_text="Quarterly Financial Trend Chart",
        extracted_graphic_text="Revenue: $4.2M, Expenses: $2.1M",
        page=8,
        obj_num=303
    )
    base_doc.structure_tree.children = [fig]

    engine = SemanticReadingEngine()
    result = engine.generate(base_doc)

    assert "Alternative text:" in result.plain_text
    assert "Quarterly Financial Trend Chart" in result.plain_text
    assert "Extracted graphic text:" in result.plain_text
    assert "Revenue: $4.2M, Expenses: $2.1M" in result.plain_text


def test_list_containing_text_and_figure(base_doc):
    """7. List structure preserves hierarchy and renders figure without bullet marker."""
    fig_in_list = StructureNode(
        id="fig_li",
        tag="Figure",
        standard_tag="Figure",
        alt_text="Step 1 screenshot showing setup wizard dialog.",
        page=2,
        obj_num=401
    )
    p_in_list = StructureNode(
        id="p_li",
        tag="P",
        standard_tag="P",
        text_content="Click the Next button shown below to proceed.",
        page=2,
        obj_num=402
    )
    lbl = StructureNode(
        id="lbl_1",
        tag="Lbl",
        standard_tag="Lbl",
        text_content="1.",
        page=2
    )
    li = StructureNode(
        id="li_1",
        tag="LI",
        standard_tag="LI",
        children=[lbl, p_in_list, fig_in_list],
        page=2
    )
    l_node = StructureNode(
        id="l_1",
        tag="L",
        standard_tag="L",
        children=[li],
        page=2
    )
    base_doc.structure_tree.children = [l_node]

    engine = SemanticReadingEngine()
    result = engine.generate(base_doc)

    assert result.total_lists == 1
    assert "LIST" in result.plain_text
    assert "LIST ITEM 1." in result.plain_text
    assert "Click the Next button shown below" in result.plain_text
    assert "Step 1 screenshot showing setup wizard dialog." in result.plain_text
    # Verify no bullet marker is forced before the figure
    assert "• GRAPHIC" not in result.plain_text
    assert "&bull; GRAPHIC" not in result.html


def test_nested_headings_hierarchy(base_doc):
    """8. Nested headings preserve sequential levels and real text."""
    h1 = StructureNode(id="h1", tag="H1", standard_tag="H1", text_content="Unit 1: Aerodynamics")
    h2 = StructureNode(id="h2", tag="H2", standard_tag="H2", text_content="Section 1.1: Lift and Drag")
    h3 = StructureNode(id="h3", tag="H3", standard_tag="H3", text_content="Topic 1.1.1: Boundary Layer Transition")
    base_doc.structure_tree.children = [h1, h2, h3]

    engine = SemanticReadingEngine()
    result = engine.generate(base_doc)

    assert result.total_headings == 3
    assert "HEADING LEVEL 1" in result.plain_text
    assert "Unit 1: Aerodynamics" in result.plain_text
    assert "HEADING LEVEL 2" in result.plain_text
    assert "Section 1.1: Lift and Drag" in result.plain_text
    assert "HEADING LEVEL 3" in result.plain_text
    assert "Topic 1.1.1: Boundary Layer Transition" in result.plain_text


def test_mathematical_vector_content(base_doc):
    """9. Mathematical content distinguishes actual text, alt text, and AI interpretation."""
    math_node = StructureNode(
        id="math_1",
        tag="Formula",
        standard_tag="Formula",
        actual_text="\\vec{F} = m \\vec{a}",
        alt_text="Vector F equals mass times vector acceleration",
        extracted_graphic_text="F = ma",
        ai_description="Newton's second law of motion in vector notation.",
        page=15,
        obj_num=880
    )
    base_doc.structure_tree.children = [math_node]

    engine = SemanticReadingEngine()
    result = engine.generate(base_doc)

    assert "FORMULA" in result.plain_text
    assert "Vector F equals mass times vector acceleration" in result.plain_text
    assert "Extracted graphic text:" in result.plain_text
    assert "F = ma" in result.plain_text
    assert "AI-generated description:" in result.plain_text
    assert "Newton's second law of motion" in result.plain_text


def test_untagged_pdf_handling():
    """10. Untagged PDF explicitly reports semantic reading order unavailable."""
    untagged_doc = PDFDocumentModel(
        filepath="untagged.pdf",
        filename="untagged.pdf",
        filesize=2048,
        pdf_version="1.4",
        page_count=3,
        is_tagged=False,
        structure_tree=None
    )

    engine = SemanticReadingEngine()
    result = engine.generate(untagged_doc)

    assert result.is_tagged is False
    assert "Semantic reading order unavailable — document is not sufficiently tagged." in result.plain_text
    assert "Semantic reading order unavailable — document is not sufficiently tagged." in result.html
    assert len(result.items) == 0


def test_missing_structure_tree_handling():
    """11. Tagged marked document with missing structure tree fails gracefully."""
    broken_doc = PDFDocumentModel(
        filepath="broken.pdf",
        filename="broken.pdf",
        filesize=2048,
        pdf_version="1.7",
        page_count=2,
        is_tagged=True,
        structure_tree=None
    )

    engine = SemanticReadingEngine()
    result = engine.generate(broken_doc)

    assert result.is_tagged is False
    assert "Semantic reading order unavailable — document is not sufficiently tagged." in result.plain_text


def test_unicode_extraction_failure(base_doc):
    """12. Unicode extraction failure triggers warning without silently inventing text."""
    p_bad = StructureNode(
        id="p_bad",
        tag="P",
        standard_tag="P",
        text_content="Equation: \ufffd\ufffd unknown symbols",
        has_decoding_error=True,
        decoding_error_msg="Unmapped font encoding glyphs detected.",
        page=4
    )
    base_doc.structure_tree.children = [p_bad]

    engine = SemanticReadingEngine()
    result = engine.generate(base_doc)

    assert "Character Extraction Warning:" in result.html or "Character Extraction Warning" in result.plain_text
    assert "Unmapped font encoding glyphs detected." in result.plain_text
    assert "\ufffd\ufffd unknown symbols" in result.plain_text
