"""
PAC Parity and Regression Tests
Verifies that the audit results, status badges, tag count, and checkpoint metrics
match PAC (PDF Accessibility Checker / Matterhorn Protocol) for benchmark PDFs.
"""

import os
import pytest
from src.pdf_inspector.core.document_parser import DocumentParser
from src.pdf_inspector.engine.runner import AuditRunner
from src.pdf_inspector.core.models import CheckStatus
from src.pdf_inspector.reporting.pdf_report import PDFReportGenerator
from src.pdf_inspector.reporting.html_report import HTMLReportGenerator

BENCHMARK_PDF = r"C:\Users\HBS\Downloads\58-78 (2).pdf"


@pytest.mark.skipif(not os.path.exists(BENCHMARK_PDF), reason="Benchmark PDF not found in Downloads")
def test_pac_parity_benchmark_58_78():
    doc = DocumentParser(BENCHMARK_PDF).parse()
    assert doc is not None

    # 1. Tags count must match PAC (454 tags, excluding StructTreeRoot)
    all_nodes = doc.structure_tree.find_all_nodes() if doc.structure_tree else []
    tag_nodes = [n for n in all_nodes if n.tag != "StructTreeRoot"]
    assert len(tag_nodes) == 454

    # 2. Run Audit
    runner = AuditRunner()
    report = runner.run(doc)

    # 3. PDF/UA Checkpoints Parity
    pdfua_counts = report.get_category_counts("PDF/UA")
    
    # Fonts: 1 failed (Times-Roman)
    assert pdfua_counts["Fonts"]["failed"] == 1
    font_failures = [
        r for r in report.results 
        if r.standard == "PDF/UA" and r.category == "Fonts" and r.status == CheckStatus.FAIL
    ]
    assert any("Times-Roman" in f.message for f in font_failures)

    # Structure elements: Passed 63, Failed 1 (LI containing Span)
    assert pdfua_counts["Structure elements"]["passed"] == 63
    assert pdfua_counts["Structure elements"]["failed"] == 1
    struct_failures = [
        r for r in report.results 
        if r.standard == "PDF/UA" and r.category == "Structure elements" and r.status == CheckStatus.FAIL
    ]
    assert any("LI" in f.message and "Span" in f.message for f in struct_failures)

    # Document settings: Passed 3, Failed 0
    assert pdfua_counts["Document settings"]["passed"] == 3
    assert pdfua_counts["Document settings"]["failed"] == 0

    # 4. WCAG & Quality Tab Status Badges
    wcag_counts = report.get_category_counts("WCAG")
    wcag_failed = sum(c.get("failed", 0) for c in wcag_counts.values())
    assert wcag_failed > 0  # ❌ WCAG

    qual_counts = report.get_category_counts("Quality")
    qual_failed = sum(c.get("failed", 0) for c in qual_counts.values())
    qual_warned = sum(c.get("warned", 0) for c in qual_counts.values())
    assert qual_failed == 0
    assert qual_warned > 0  # ⚠️ Quality (Heading hierarchy starts at H3)

    # 5. Report Generators must handle angle brackets (<LI>, <Span>, etc.) safely
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_out = os.path.join(tmpdir, "audit_report.pdf")
        html_out = os.path.join(tmpdir, "audit_report.html")
        PDFReportGenerator.generate(report, pdf_out)
        assert os.path.getsize(pdf_out) > 0
        HTMLReportGenerator.generate(report, html_out)
        assert os.path.getsize(html_out) > 0


def test_pac_exact_case_role_mapping():
    from src.pdf_inspector.engine.pdf_ua.role_map_rules import RoleMappingValidityRule
    from src.pdf_inspector.core.models import StructureNode, PDFDocumentModel, CheckStatus

    rule = RoleMappingValidityRule()

    # /LBody (proper camelcase standard tag) should pass
    root_valid = StructureNode("root", "StructTreeRoot", "StructTreeRoot")
    node_valid = StructureNode("n1", "LBody", "LBody")
    root_valid.children.append(node_valid)
    doc_valid = PDFDocumentModel(
        filepath="", filename="test.pdf", filesize=100, pdf_version="1.7",
        page_count=1, is_tagged=True, structure_tree=root_valid, role_map={}
    )
    res_valid = rule.evaluate(doc_valid)
    assert any(r.status == CheckStatus.PASS for r in res_valid)
    assert not any(r.status == CheckStatus.FAIL for r in res_valid)

    # /Lbody (lowercase b) is non-standard in ISO 32000-1 and unmapped -> must FAIL like PAC
    root_invalid = StructureNode("root", "StructTreeRoot", "StructTreeRoot")
    node_invalid = StructureNode("n2", "Lbody", "Lbody")
    root_invalid.children.append(node_invalid)
    doc_invalid = PDFDocumentModel(
        filepath="", filename="test.pdf", filesize=100, pdf_version="1.7",
        page_count=1, is_tagged=True, structure_tree=root_invalid, role_map={}
    )
    res_invalid = rule.evaluate(doc_invalid)
    assert any(r.status == CheckStatus.FAIL and "Non-standard structure type \"Lbody\"" in r.message for r in res_invalid)


def test_pac_structure_tree_heading_warnings():
    from src.pdf_inspector.engine.pdf_ua.structure_rules import StructureTreeIntegrityRule
    from src.pdf_inspector.core.models import StructureNode, PDFDocumentModel, CheckStatus

    rule = StructureTreeIntegrityRule()
    root = StructureNode("root", "StructTreeRoot", "StructTreeRoot")
    # First heading starts at H2 (should generate warning like PAC)
    h2 = StructureNode("h2", "H2", "H2")
    # Skipped heading to H4 (should generate warning)
    h4 = StructureNode("h4", "H4", "H4")
    root.children.extend([h2, h4])

    doc = PDFDocumentModel(
        filepath="", filename="headings.pdf", filesize=100, pdf_version="1.7",
        page_count=1, is_tagged=True, structure_tree=root
    )
    res = rule.evaluate(doc)
    warnings = [r for r in res if r.status == CheckStatus.WARNING]
    assert len(warnings) >= 2
    assert any("First heading in structure tree is <H2>" in w.message for w in warnings)
    assert any("Structure tree heading hierarchy skips from H2 to H4" in w.message for w in warnings)


def test_pac_tab_order_fail():
    from src.pdf_inspector.engine.pdf_ua.annotation_rules import PageTabOrderRule
    from src.pdf_inspector.core.models import StructureNode, PageModel, PDFDocumentModel, CheckStatus

    rule = PageTabOrderRule()
    pg = PageModel(page_number=1, width=612.0, height=792.0, has_tab_order=False, tab_order_mode="None", annotations_count=1)
    root = StructureNode("root", "StructTreeRoot", "StructTreeRoot")
    doc = PDFDocumentModel(
        filepath="", filename="taborder.pdf", filesize=100, pdf_version="1.7",
        page_count=1, is_tagged=True, structure_tree=root, pages=[pg], display_doc_title=True
    )
    res = rule.evaluate(doc)
    tab_fails = [r for r in res if r.status == CheckStatus.FAIL and "tab order" in r.message.lower()]
    assert len(tab_fails) == 1


WORK_DOC_PDF = r"C:\Users\HBS\Downloads\Work_Documentation_Administrative_Fillable_1_accessible.pdf"


@pytest.mark.skipif(not os.path.exists(WORK_DOC_PDF), reason="Work_Documentation PDF not found in Downloads")
def test_pac_parity_artifacts_inside_tagged_content():
    """Verifies that PAI detects exactly 41 artifacts inside tagged content on Work_Documentation PDF matching PAC."""
    from src.pdf_inspector.engine.pdf_ua.artifact_rules import ArtifactInsideTaggedContentRule
    
    doc = DocumentParser(WORK_DOC_PDF).parse()
    assert doc is not None

    rule = ArtifactInsideTaggedContentRule()
    results = rule.evaluate(doc)

    fails = [r for r in results if r.status == CheckStatus.FAIL]
    passes = [r for r in results if r.status == CheckStatus.PASS]

    # PAC reports exactly 41 errors
    assert len(fails) == 41
    # Checkpoint passed count
    assert sum(r.items_count for r in passes) == 356

    # Verify failure pages match PAC (13 pages)
    expected_pages = {27, 29, 31, 33, 57, 59, 61, 63, 64, 65, 67, 69, 71}
    actual_pages = {r.page for r in fails}
    assert actual_pages == expected_pages

    # Check page 27 finding details (visual highlight rect and McGraw text)
    p27_fails = [r for r in fails if r.page == 27]
    assert len(p27_fails) == 3
    sample = p27_fails[0]
    assert sample.bounding_box is not None
    # Rect around (92.3, 170.18, 106.36, 379.87)
    assert abs(sample.bounding_box[0] - 92.30) < 1.0
    assert abs(sample.bounding_box[1] - 170.18) < 1.0
    assert "Figure" in sample.object_reference
    assert "Fm2" in sample.object_reference
    assert "McGraw" in sample.evidence

    # Run full AuditRunner and verify Content checkpoint counts
    runner = AuditRunner()
    report = runner.run(doc)
    pdfua_counts = report.get_category_counts("PDF/UA")
    assert pdfua_counts["Content"]["failed"] == 41
    assert pdfua_counts["Content"]["passed"] >= 356


def test_artifact_inside_tagged_content_synthetic():
    """Unit test for ArtifactInsideTaggedContentRule with synthetic document models."""
    from src.pdf_inspector.engine.pdf_ua.artifact_rules import ArtifactInsideTaggedContentRule
    from src.pdf_inspector.core.models import ArtifactOccurrenceModel, PageModel, PDFDocumentModel
    
    rule = ArtifactInsideTaggedContentRule()

    # 1. Clean document: all artifacts outside tagged content
    pg1 = PageModel(page_number=1, width=612.0, height=792.0, artifacts=[
        ArtifactOccurrenceModel(page_number=1, is_inside_tagged=False),
        ArtifactOccurrenceModel(page_number=1, is_inside_tagged=False),
    ])
    doc_clean = PDFDocumentModel(
        filepath="", filename="clean.pdf", filesize=100, pdf_version="1.7",
        page_count=1, pages=[pg1]
    )
    res_clean = rule.evaluate(doc_clean)
    assert all(r.status == CheckStatus.PASS for r in res_clean)
    assert not any(r.status == CheckStatus.FAIL for r in res_clean)

    # 2. Document with invalid artifact inside tagged content
    pg2 = PageModel(page_number=1, width=612.0, height=792.0, artifacts=[
        ArtifactOccurrenceModel(
            page_number=1,
            is_inside_tagged=True,
            parent_tag="P",
            parent_mcid=3,
            bbox=(50.0, 100.0, 200.0, 150.0),
            text_snippet="Decorative separator"
        )
    ])
    doc_invalid = PDFDocumentModel(
        filepath="", filename="invalid.pdf", filesize=100, pdf_version="1.7",
        page_count=1, pages=[pg2]
    )
    res_invalid = rule.evaluate(doc_invalid)
    fails = [r for r in res_invalid if r.status == CheckStatus.FAIL]
    assert len(fails) == 1
    assert fails[0].page == 1
    assert fails[0].bounding_box == (50.0, 100.0, 200.0, 150.0)
    assert "<P MCID=3>" in fails[0].object_reference
    assert "Decorative separator" in fails[0].evidence



