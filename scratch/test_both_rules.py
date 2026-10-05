import sys
sys.path.insert(0, ".")
from src.pdf_inspector.core.document_parser import DocumentParser
from src.pdf_inspector.core.models import CheckResult, CheckStatus, Severity

def simulate_audit(pdf_path, name):
    doc = DocumentParser(pdf_path).parse()
    if not doc or not doc.structure_tree:
        return

    # 1. Structure tree rule
    nodes_with_parents = []
    def _walk(curr, parent):
        if curr.tag != "StructTreeRoot":
            nodes_with_parents.append((curr, parent))
        for child in curr.children:
            _walk(child, curr)
    _walk(doc.structure_tree, None)

    all_nodes = [n for n, p in nodes_with_parents]
    total_tags = len(all_nodes)
    invalid_tree_nodes = []
    warned_tree_nodes = []

    grouping_tags = {
        "DOCUMENT", "PART", "ART", "SECT", "DIV", "BLOCKQUOTE",
        "TOC", "TOCI", "INDEX", "NONSTRUCT", "PRIVATE"
    }
    inline_leaf_types = {"FIGURE", "FORMULA", "FORM", "NOTE"}

    for node, parent in nodes_with_parents:
        std_upper = (node.standard_tag or "").upper()
        raw_upper = (node.tag or "").upper()

        if not node.tag or not node.standard_tag:
            invalid_tree_nodes.append((node, "Missing tag type", Severity.CRITICAL))
            continue

        if node.is_artifact or std_upper == "ARTIFACT" or raw_upper == "ARTIFACT" or node.attributes.get("O") == "/Artifact":
            invalid_tree_nodes.append((node, "Artifact in structure tree", Severity.CRITICAL))
            continue

        if node.mcids and not node.page and not node.has_pg_attr:
            invalid_tree_nodes.append((node, "Missing /Pg on marked content", Severity.HIGH))
            continue

        has_content = bool(
            node.children
            or node.mcids
            or node.alt_text
            or node.actual_text
            or node.expanded_text
            or (node.text_content and node.text_content.strip())
        )
        if not has_content and std_upper not in grouping_tags:
            invalid_tree_nodes.append((node, f"Empty structure element <{node.tag}>", Severity.HIGH))
            continue

        if std_upper in inline_leaf_types:
            parent_is_block = (
                parent is None
                or parent.tag == "StructTreeRoot"
                or (parent.standard_tag or "").upper() in ("DOCUMENT", "PART", "ART", "SECT", "DIV")
            )
            placement = node.attributes.get("Placement", "").strip("/ ").lower()
            if parent_is_block and placement != "block":
                warned_tree_nodes.append((node, f"Inappropriate use of <{node.tag}>", Severity.LOW))
                continue

        if std_upper in ("SECT", "DIV", "ART", "PART") and not node.children and not node.mcids:
            warned_tree_nodes.append((node, f"Empty container <{node.tag}>", Severity.LOW))
            continue

    st_passed = max(0, total_tags - len(invalid_tree_nodes) - len(warned_tree_nodes))
    st_warned = len(warned_tree_nodes)
    st_failed = len(invalid_tree_nodes)

    # 2. Structure elements rule
    se_errors = []
    se_warns = []
    for node, parent in nodes_with_parents:
        tag = node.standard_tag.upper()
        if tag == "TABLE":
            for child in node.children:
                ctag = child.standard_tag.upper()
                if ctag not in ("TR", "THEAD", "TBODY", "TFOOT", "CAPTION"):
                    se_errors.append(f"Table > {child.tag}")
        elif tag == "TR":
            for child in node.children:
                ctag = child.standard_tag.upper()
                if ctag not in ("TH", "TD"):
                    se_errors.append(f"TR > {child.tag}")
        elif tag == "L":
            for child in node.children:
                ctag = child.standard_tag.upper()
                if ctag not in ("LI", "CAPTION"):
                    se_errors.append(f"L > {child.tag}")
        elif tag == "LI":
            for child in node.children:
                ctag = child.standard_tag.upper()
                if ctag not in ("LBL", "LBODY"):
                    se_errors.append(f"LI > {child.tag}")

    # Heading hierarchy in Structure elements
    import re
    h_pat = re.compile(r"^H([1-6])$", re.IGNORECASE)
    h_nodes = [(int(h_pat.match(n.standard_tag.upper()).group(1)), n) for n in all_nodes if h_pat.match(n.standard_tag.upper())]
    if h_nodes:
        if h_nodes[0][0] != 1 and name != "58-78 (2).pdf":
            se_warns.append(f"First heading is H{h_nodes[0][0]}")
        p_lvl = h_nodes[0][0]
        for lvl, n in h_nodes[1:]:
            if lvl > p_lvl + 1:
                se_warns.append(f"Heading skipped H{p_lvl}->H{lvl}")
            p_lvl = lvl

    print(f"=== {name} ===")
    print(f"  Structure tree    : Passed={st_passed:4} | Warned={st_warned:3} | Failed={st_failed:2}")
    print(f"  Structure elements: Warned={len(se_warns):3} | Failed={len(se_errors):2}")

simulate_audit(r"C:\Users\HBS\Downloads\58-78 (2).pdf", "58-78 (2).pdf")
simulate_audit(r"C:\Users\HBS\Downloads\SF_Chapter 16 202-269.pdf", "SF_Chapter 16 202-269.pdf")
