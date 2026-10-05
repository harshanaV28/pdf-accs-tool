import sys
sys.path.insert(0, ".")
from src.pdf_inspector.core.document_parser import DocumentParser
from src.pdf_inspector.core.models import CheckResult, CheckStatus, Severity

def test_on_doc(pdf_path, name):
    doc = DocumentParser(pdf_path).parse()
    if not doc or not doc.structure_tree:
        print(f"{name}: Untagged")
        return

    # Build node-parent map
    nodes_with_parents = []
    def _walk(curr, parent):
        if curr.tag != "StructTreeRoot":
            nodes_with_parents.append((curr, parent))
        for child in curr.children:
            _walk(child, curr)
    _walk(doc.structure_tree, None)

    all_nodes = [n for n, p in nodes_with_parents]
    total_tags = len(all_nodes)

    invalid_nodes = []
    warned_nodes = []

    grouping_tags = {
        "DOCUMENT", "PART", "ART", "SECT", "DIV", "BLOCKQUOTE",
        "TOC", "TOCI", "INDEX", "NONSTRUCT", "PRIVATE"
    }
    inline_leaf_types = {"FIGURE", "FORMULA", "FORM", "NOTE"}

    for node, parent in nodes_with_parents:
        std_upper = (node.standard_tag or "").upper()
        raw_upper = (node.tag or "").upper()

        # 1. Missing or invalid tag
        if not node.tag or not node.standard_tag:
            invalid_nodes.append((node, f"Structure element has missing or empty tag type.", Severity.CRITICAL))
            continue

        # 2. Artifact in Structure Tree (Matterhorn 01-001)
        if node.is_artifact or std_upper == "ARTIFACT" or raw_upper == "ARTIFACT" or node.attributes.get("O") == "/Artifact":
            invalid_nodes.append((node, f"Artifact element <{node.tag}> must not be present in the structure tree.", Severity.CRITICAL))
            continue

        # 3. Missing /Pg on element with marked content (Matterhorn 13-001, ISO 32000-1 Table 323)
        if node.mcids and not node.page and not node.has_pg_attr:
            invalid_nodes.append((node, f"Structure element <{node.tag}> contains marked content but lacks an explicit page reference (/Pg).", Severity.HIGH))
            continue

        # 4. Empty structure element (Matterhorn 13-005)
        has_content = bool(
            node.children
            or node.mcids
            or node.alt_text
            or node.actual_text
            or node.expanded_text
            or (node.text_content and node.text_content.strip())
        )
        if not has_content and std_upper not in grouping_tags:
            invalid_nodes.append((node, f"Structure element <{node.tag}> is empty and contains no marked content or children.", Severity.HIGH))
            continue

        # 5. Possibly inappropriate use of structure element (Matterhorn 01-006)
        if std_upper in inline_leaf_types:
            # Check if used at block level (direct child of grouping container or root)
            parent_is_block = (
                parent is None
                or parent.tag == "StructTreeRoot"
                or (parent.standard_tag or "").upper() in ("DOCUMENT", "PART", "ART", "SECT", "DIV")
            )
            placement = node.attributes.get("Placement", "").strip("/ ").lower()
            if parent_is_block and placement != "block":
                warned_nodes.append((
                    node,
                    f'Possibly inappropriate use of a "{node.tag}" structure element. Inline element is used at block level without Placement=Block attribute.',
                    Severity.LOW
                ))
                continue

        # 6. Structural container without children or content (Matterhorn 13-008)
        if std_upper in ("SECT", "DIV", "PART", "ART") and not node.children and not node.mcids:
            warned_nodes.append((
                node,
                f"Structural container <{node.tag}> in structure tree has no children or content.",
                Severity.LOW
            ))
            continue

    passed_count = max(0, total_tags - len(invalid_nodes) - len(warned_nodes))
    print(f"=== {name} (Total tags: {total_tags}) ===")
    print(f"  Passed: {passed_count}")
    print(f"  Warned: {len(warned_nodes)}")
    print(f"  Failed: {len(invalid_nodes)}")
    if warned_nodes:
        print("  Sample warnings:")
        for n, msg, s in warned_nodes[:3]:
            print(f"    - {msg} (<{n.tag}>, page {n.page})")
    if invalid_nodes:
        print("  Sample failures:")
        for n, msg, s in invalid_nodes[:3]:
            print(f"    - {msg} (<{n.tag}>, page {n.page})")

test_on_doc(r"C:\Users\HBS\Downloads\58-78 (2).pdf", "58-78 (2).pdf")
test_on_doc(r"C:\Users\HBS\Downloads\SF_Chapter 16 202-269.pdf", "SF_Chapter 16 202-269.pdf")
