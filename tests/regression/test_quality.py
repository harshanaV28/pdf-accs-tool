"""
Regression tests for Quality & Ergonomics Rules:
- Heading Hierarchy Integrity (QUAL-HEAD-001)
- Structural Quality & Container Grouping (QUAL-STRUCT-001)
- Table Regularity & Symmetry (QUAL-TABLE-001)
- Meaningful Link Labels (QUAL-LINK-001)
"""

import pytest
from src.pdf_inspector.core.models import (
    PDFDocumentModel, StructureNode, TableModel, LinkModel, CheckStatus
)
from src.pdf_inspector.engine.quality.quality_rules import (
    HeadingHierarchyQualityRule,
    StructureQualityRule,
    TableRegularityQualityRule,
    LinkQualityRule,
)


class TestQualityRegression:
    def test_heading_hierarchy_rule(self):
        rule = HeadingHierarchyQualityRule()

        # Case 1: Skipped level H1 -> H3
        h1 = StructureNode("h1", "H1", "H1", page=1, text_content="Chapter 1")
        h3 = StructureNode("h3", "H3", "H3", page=1, text_content="Subsection")
        root_jump = StructureNode("root", "StructTreeRoot", "StructTreeRoot", children=[h1, h3])
        doc_jump = PDFDocumentModel(
            filepath="", filename="jump.pdf", filesize=100, pdf_version="1.7",
            page_count=1, is_tagged=True, structure_tree=root_jump
        )
        res_jump = rule.evaluate(doc_jump)
        assert any(r.status == CheckStatus.WARNING and "skipped" in r.message.lower() for r in res_jump)

        # Case 2: Smooth hierarchy H1 -> H2 -> H3
        h2 = StructureNode("h2", "H2", "H2", page=1, text_content="Section")
        root_smooth = StructureNode("root", "StructTreeRoot", "StructTreeRoot", children=[h1, h2, h3])
        doc_smooth = PDFDocumentModel(
            filepath="", filename="smooth.pdf", filesize=100, pdf_version="1.7",
            page_count=1, is_tagged=True, structure_tree=root_smooth
        )
        res_smooth = rule.evaluate(doc_smooth)
        assert any(r.status == CheckStatus.PASS for r in res_smooth)

    def test_structure_quality_empty_containers(self):
        rule = StructureQualityRule()

        # Case 1: Empty Sect container with no children and no MCIDs
        empty_sect = StructureNode("s1", "Sect", "Sect", page=1, children=[], mcids=[])
        root_empty = StructureNode("root", "StructTreeRoot", "StructTreeRoot", children=[empty_sect])
        doc_empty = PDFDocumentModel(
            filepath="", filename="empty_sect.pdf", filesize=100, pdf_version="1.7",
            page_count=1, is_tagged=True, structure_tree=root_empty
        )
        res_empty = rule.evaluate(doc_empty)
        assert any(r.status == CheckStatus.WARNING and "Empty structural container" in r.message for r in res_empty)

        # Case 2: Populated Sect container
        p = StructureNode("p1", "P", "P", page=1, text_content="Text")
        filled_sect = StructureNode("s2", "Sect", "Sect", page=1, children=[p])
        root_filled = StructureNode("root", "StructTreeRoot", "StructTreeRoot", children=[filled_sect])
        doc_filled = PDFDocumentModel(
            filepath="", filename="filled_sect.pdf", filesize=100, pdf_version="1.7",
            page_count=1, is_tagged=True, structure_tree=root_filled
        )
        res_filled = rule.evaluate(doc_filled)
        assert any(r.status == CheckStatus.PASS for r in res_filled)

    def test_table_regularity_rule(self):
        rule = TableRegularityQualityRule()

        # Case 1: Irregular table
        t_irreg = TableModel(
            id="t1", page=1, rows_count=3, cols_count=4,
            has_headers=True, header_cells_count=4, data_cells_count=8,
            is_regular=False, bbox=(10, 10, 200, 200)
        )
        doc_irreg = PDFDocumentModel(
            filepath="", filename="irreg.pdf", filesize=100, pdf_version="1.7",
            page_count=1, tables=[t_irreg]
        )
        res_irreg = rule.evaluate(doc_irreg)
        assert any(r.status == CheckStatus.WARNING and "irregular" in r.message.lower() for r in res_irreg)

        # Case 2: Regular table
        t_reg = TableModel(
            id="t2", page=1, rows_count=3, cols_count=3,
            has_headers=True, header_cells_count=3, data_cells_count=6,
            is_regular=True, bbox=(10, 10, 200, 200)
        )
        doc_reg = PDFDocumentModel(
            filepath="", filename="reg.pdf", filesize=100, pdf_version="1.7",
            page_count=1, tables=[t_reg]
        )
        res_reg = rule.evaluate(doc_reg)
        assert any(r.status == CheckStatus.PASS for r in res_reg)

    def test_link_quality_rule(self):
        rule = LinkQualityRule()

        # Case 1: Vague link anchor ("read more")
        l_vague = LinkModel(id="l1", page=1, text="read more", uri="https://example.com/info", bbox=(10, 10, 50, 20))
        doc_vague = PDFDocumentModel(
            filepath="", filename="vague.pdf", filesize=100, pdf_version="1.7",
            page_count=1, links=[l_vague]
        )
        res_vague = rule.evaluate(doc_vague)
        assert any(r.status == CheckStatus.WARNING and "Ambiguous link label" in r.message for r in res_vague)

        # Case 2: Bare URL string
        l_bare = LinkModel(id="l2", page=1, text="https://example.com/info", uri="https://example.com/info", bbox=(10, 10, 50, 20))
        doc_bare = PDFDocumentModel(
            filepath="", filename="bare.pdf", filesize=100, pdf_version="1.7",
            page_count=1, links=[l_bare]
        )
        res_bare = rule.evaluate(doc_bare)
        assert any(r.status == CheckStatus.WARNING and "raw URL strings" in r.message for r in res_bare)

        # Case 3: Descriptive link anchor
        l_good = LinkModel(id="l3", page=1, text="Annual Financial Report 2026 (PDF)", uri="https://example.com/annual-report", bbox=(10, 10, 50, 20))
        doc_good = PDFDocumentModel(
            filepath="", filename="good.pdf", filesize=100, pdf_version="1.7",
            page_count=1, links=[l_good]
        )
        res_good = rule.evaluate(doc_good)
        assert any(r.status == CheckStatus.PASS for r in res_good)
