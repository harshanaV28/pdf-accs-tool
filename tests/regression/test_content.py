"""
Regression tests for Content Stream and Marked Content Rules:
- Tagged PDF mark & StructTreeRoot presence (PDFUA-CONTENT-001)
- Real Content Tagged / Unmarked Content Detection (PDFUA-CONTENT-002)
- Artifact inside tagged content (PDFUA-ART-003)
- Tagged content inside artifact (PDFUA-CONTENT-004)
- MCID reference integrity / orphan MCIDs (PDFUA-CONTENT-005)
"""

import pytest
from src.pdf_inspector.core.models import (
    PDFDocumentModel, PageModel, StructureNode, ContentOccurrenceModel,
    ArtifactOccurrenceModel, CheckStatus
)
from src.pdf_inspector.engine.pdf_ua.content_rules import (
    TaggedPDFRule,
    ContentTaggedRule,
    TaggedInsideArtifactRule,
    MCIDStructureReferenceRule,
)
from src.pdf_inspector.engine.pdf_ua.artifact_rules import (
    ArtifactInStructureTreeRule,
    ArtifactInsideTaggedContentRule,
)


class TestContentRegression:
    def test_tagged_pdf_rule(self):
        rule = TaggedPDFRule()

        # Case 1: Untagged
        doc_untagged = PDFDocumentModel(
            filepath="", filename="untagged.pdf", filesize=100, pdf_version="1.7",
            page_count=1, is_tagged=False, structure_tree=None
        )
        res1 = rule.evaluate(doc_untagged)
        assert len(res1) == 1
        assert res1[0].status == CheckStatus.FAIL

        # Case 2: Tagged
        root = StructureNode("root", "StructTreeRoot", "StructTreeRoot")
        doc_tagged = PDFDocumentModel(
            filepath="", filename="tagged.pdf", filesize=100, pdf_version="1.7",
            page_count=1, is_tagged=True, structure_tree=root
        )
        res2 = rule.evaluate(doc_tagged)
        assert len(res2) == 1
        assert res2[0].status == CheckStatus.PASS

    def test_unmarked_real_content_rule(self):
        rule = ContentTaggedRule()

        # Case 1: Page has unmarked text / path painting operator
        unmarked_occ = ContentOccurrenceModel(
            page_number=1,
            operator_type="text",
            operator_name="Tj",
            is_unmarked_real_content=True,
            snippet="Untagged body paragraph"
        )
        p1 = PageModel(
            page_number=1, width=600, height=800,
            content_occurrences=[unmarked_occ],
            unmarked_real_content_count=1
        )
        doc_unmarked = PDFDocumentModel(
            filepath="", filename="unmarked.pdf", filesize=100, pdf_version="1.7",
            page_count=1, is_tagged=True, pages=[p1]
        )
        res1 = rule.evaluate(doc_unmarked)
        assert len(res1) >= 1
        assert any(r.status == CheckStatus.FAIL and "Page 1 contains real content" in r.message for r in res1)

        # Case 2: Page has unmarked XObject Do operator
        unmarked_do = ContentOccurrenceModel(
            page_number=2,
            operator_type="xobject",
            operator_name="Do",
            is_unmarked_real_content=True,
            xobject_name="Meta51",
            snippet="XObject /Meta51 Do"
        )
        p_do = PageModel(
            page_number=2, width=600, height=800,
            content_occurrences=[unmarked_do],
            unmarked_real_content_count=1
        )
        doc_do = PDFDocumentModel(
            filepath="", filename="unmarked_do.pdf", filesize=100, pdf_version="1.7",
            page_count=2, is_tagged=True, pages=[PageModel(page_number=1, width=600, height=800), p_do]
        )
        res_do = rule.evaluate(doc_do)
        assert any(r.status == CheckStatus.FAIL and "Page 2 contains real content" in r.message for r in res_do)

        # Case 3: Clean page (all real content in MCID or Artifact)
        p2 = PageModel(
            page_number=1, width=600, height=800,
            content_occurrences=[],
            unmarked_real_content_count=0
        )
        doc_marked = PDFDocumentModel(
            filepath="", filename="clean.pdf", filesize=100, pdf_version="1.7",
            page_count=1, is_tagged=True, pages=[p2]
        )
        res2 = rule.evaluate(doc_marked)
        assert len(res2) == 1
        assert res2[0].status == CheckStatus.PASS

    def test_tagged_inside_artifact_rule(self):
        rule = TaggedInsideArtifactRule()

        # Case 1: Page has tagged sequence inside Artifact
        p_bad = PageModel(page_number=2, width=600, height=800, tagged_in_artifact_count=2)
        doc_bad = PDFDocumentModel(
            filepath="", filename="nested_art.pdf", filesize=100, pdf_version="1.7",
            page_count=2, is_tagged=True, pages=[PageModel(page_number=1, width=600, height=800), p_bad]
        )
        res_bad = rule.evaluate(doc_bad)
        assert any(r.status == CheckStatus.FAIL and r.page == 2 for r in res_bad)

        # Case 2: Clean pages
        p_good = PageModel(page_number=1, width=600, height=800, tagged_in_artifact_count=0)
        doc_good = PDFDocumentModel(
            filepath="", filename="clean_art.pdf", filesize=100, pdf_version="1.7",
            page_count=1, is_tagged=True, pages=[p_good]
        )
        res_good = rule.evaluate(doc_good)
        assert len(res_good) == 1
        assert res_good[0].status == CheckStatus.PASS

    def test_artifact_inside_tagged_content_rule(self):
        rule = ArtifactInsideTaggedContentRule()

        # Case 1: Artifact inside tagged content
        art_bad = ArtifactOccurrenceModel(
            page_number=1, is_inside_tagged=True, parent_tag="P", parent_mcid=0, text_snippet="Artifact inside P"
        )
        doc_bad = PDFDocumentModel(
            filepath="", filename="art_in_p.pdf", filesize=100, pdf_version="1.7",
            page_count=1, is_tagged=True, pages=[PageModel(page_number=1, width=600, height=800, artifacts=[art_bad])]
        )
        res_bad = rule.evaluate(doc_bad)
        assert any(r.status == CheckStatus.FAIL for r in res_bad)

        # Case 2: Artifact legitimately placed outside tagged content
        art_good = ArtifactOccurrenceModel(
            page_number=1, is_inside_tagged=False
        )
        doc_good = PDFDocumentModel(
            filepath="", filename="clean_art.pdf", filesize=100, pdf_version="1.7",
            page_count=1, is_tagged=True, pages=[PageModel(page_number=1, width=600, height=800, artifacts=[art_good])]
        )
        res_good = rule.evaluate(doc_good)
        assert all(r.status == CheckStatus.PASS for r in res_good)

    def test_mcid_reference_integrity_rule(self):
        rule = MCIDStructureReferenceRule()

        # Case 1: Page has MCID 0, 1, but structure tree only references MCID 0
        node = StructureNode("p1", "P", "P", mcids=[0])
        root = StructureNode("root", "StructTreeRoot", "StructTreeRoot", children=[node])
        page1 = PageModel(page_number=1, width=600, height=800, mcids=[0, 1])
        doc_orphan = PDFDocumentModel(
            filepath="", filename="orphan.pdf", filesize=100, pdf_version="1.7",
            page_count=1, is_tagged=True, structure_tree=root, pages=[page1]
        )
        res_orphan = rule.evaluate(doc_orphan)
        assert any(r.status == CheckStatus.FAIL and "not referenced" in r.message for r in res_orphan)

        # Case 2: All MCIDs properly referenced
        node2 = StructureNode("p2", "P", "P", mcids=[0, 1])
        root2 = StructureNode("root", "StructTreeRoot", "StructTreeRoot", children=[node2])
        doc_valid = PDFDocumentModel(
            filepath="", filename="valid_mcid.pdf", filesize=100, pdf_version="1.7",
            page_count=1, is_tagged=True, structure_tree=root2, pages=[page1]
        )
        res_valid = rule.evaluate(doc_valid)
        assert len(res_valid) == 1
        assert res_valid[0].status == CheckStatus.PASS
