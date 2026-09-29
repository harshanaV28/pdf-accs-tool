"""
Unit tests for Core Data Models and Calculations
"""

import pytest
from src.pdf_inspector.core.models import (
    CheckResult, CheckStatus, Severity, StructureNode,
    PDFDocumentModel, PageModel, AuditReport
)
from src.pdf_inspector.core.structure_tree import resolve_role, STANDARD_STRUCTURE_TYPES


def test_check_result_serialization():
    result = CheckResult(
        check_id="TEST-001",
        name="Test Check",
        category="Metadata",
        standard="PDF/UA",
        status=CheckStatus.FAIL,
        severity=Severity.HIGH,
        message="Test failure message",
        evidence="Catalog /Metadata missing",
        page=1,
        bounding_box=(50.0, 50.0, 200.0, 200.0),
        object_reference="DocCatalog",
        remediation="Add metadata"
    )

    d = result.to_dict()
    assert d["check_id"] == "TEST-001"
    assert d["status"] == "FAIL"
    assert d["severity"] == "HIGH"
    assert d["page"] == 1
    assert d["bounding_box"] == [50.0, 50.0, 200.0, 200.0]


def test_structure_node_search():
    root = StructureNode(id="root", tag="StructTreeRoot", standard_tag="StructTreeRoot")
    doc_node = StructureNode(id="doc", tag="Document", standard_tag="Document")
    h1_node = StructureNode(id="h1", tag="H1", standard_tag="H1", title="Title")
    p_node = StructureNode(id="p", tag="P", standard_tag="P")

    doc_node.children.extend([h1_node, p_node])
    root.children.append(doc_node)

    headings = root.find_all_by_standard_tag("H1")
    assert len(headings) == 1
    assert headings[0].id == "h1"

    all_nodes = root.find_all_nodes()
    assert len(all_nodes) == 4


def test_role_mapping_resolution():
    role_map = {
        "MainTitle": "H1",
        "SubSection": "Sect",
        "CircularA": "CircularB",
        "CircularB": "CircularA",
    }

    # Standard tag
    role, mapped, circ = resolve_role("P", role_map)
    assert role == "P"
    assert not mapped
    assert not circ

    # Custom tag mapped to standard
    role, mapped, circ = resolve_role("MainTitle", role_map)
    assert role == "H1"
    assert mapped
    assert not circ

    # Circular tag
    role, mapped, circ = resolve_role("CircularA", role_map)
    assert circ


def test_audit_report_statistics():
    results = [
        CheckResult("C1", "R1", "Cat1", "PDF/UA", CheckStatus.PASS, Severity.INFO, "Passed"),
        CheckResult("C2", "R2", "Cat1", "PDF/UA", CheckStatus.FAIL, Severity.HIGH, "Failed"),
        CheckResult("C3", "R3", "Cat2", "PDF/UA", CheckStatus.WARNING, Severity.MEDIUM, "Warned"),
        CheckResult("C4", "R4", "Cat3", "PDF/UA", CheckStatus.MANUAL_REVIEW, Severity.INFO, "Manual"),
    ]

    report = AuditReport(document_info={"filename": "test.pdf"}, results=results)
    assert report.total_passed == 1
    assert report.total_failed == 1
    assert report.total_warned == 1
    assert report.total_manual == 1
    # Compliance score = 1 passed out of (1 passed + 1 warned + 1 failed) = 33.3%
    assert report.compliance_score == 33.3
