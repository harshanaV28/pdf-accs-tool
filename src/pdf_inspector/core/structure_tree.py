"""
PDF Structure Tree Parser
Parses the Logical Structure Tree (/StructTreeRoot), /ParentTree number tree,
and resolves custom role mappings to ISO 32000-1 standard structure types.
Links real page MCID text and geometry to structural nodes.
"""

from typing import Dict, List, Optional, Tuple, Set, Any
import logging
import pikepdf
from .models import StructureNode

logger = logging.getLogger(__name__)

# Standard structure types defined in ISO 32000-1:2008, Clause 14.8.4
STANDARD_STRUCTURE_TYPES: Set[str] = {
    # Document level & Grouping
    "DOCUMENT", "PART", "ART", "SECT", "DIV", "BLOCKQUOTE", "CAPTION",
    "TOC", "TOCI", "INDEX", "NONSTRUCT", "PRIVATE",
    # Paragraph-like & Headings
    "P", "H", "H1", "H2", "H3", "H4", "H5", "H6",
    # Lists
    "L", "LI", "LBL", "LBODY",
    # Tables
    "TABLE", "TR", "TH", "TD",
    # Inline
    "SPAN", "QUOTE", "NOTE", "REFERENCE", "BIBENTRY", "CODE", "LINK", "ANNOT",
    # Illustration & Forms
    "FIGURE", "FORMULA", "FORM",
    # Ruby & Warichu
    "RUBY", "RB", "RT", "RP", "WARICHU", "WT", "WP"
}


def resolve_role(tag: str, role_map: Dict[str, str]) -> Tuple[str, bool, bool]:
    """
    Resolves a structure type to its standard role via /RoleMap.
    Returns: (standard_role, is_mapped, is_circular)
    """
    clean_tag = tag.strip("/ ")
    curr = clean_tag
    visited = set()

    while True:
        if curr.upper() in STANDARD_STRUCTURE_TYPES:
            return curr, curr != clean_tag, False

        visited.add(curr)
        next_tag = role_map.get(curr) or role_map.get("/" + curr)
        if not next_tag:
            # Unmapped custom role
            return clean_tag, False, False

        clean_next = str(next_tag).strip("/ ")
        if clean_next in visited:
            # Circular mapping detected
            return clean_next, True, True

        curr = clean_next


def parse_number_tree(tree_obj: Any) -> Dict[int, Any]:
    """
    Recursively parses a PDF Number Tree dictionary into a Python dict {int_key: object}.
    Number trees can contain either /Nums or /Kids arrays.
    """
    results: Dict[int, Any] = {}
    if not isinstance(tree_obj, (pikepdf.Dictionary, pikepdf.Object)):
        return results

    try:
        if "/Nums" in tree_obj:
            nums = tree_obj["/Nums"]
            for i in range(0, len(nums), 2):
                if i + 1 < len(nums):
                    key = int(nums[i])
                    val = nums[i + 1]
                    results[key] = val

        elif "/Kids" in tree_obj:
            kids = tree_obj["/Kids"]
            for kid in kids:
                results.update(parse_number_tree(kid))
    except Exception as e:
        logger.debug(f"Error parsing number tree node: {e}")

    return results


class StructureTreeParser:
    """Extracts and builds the hierarchical StructureNode tree from a pikepdf document."""

    def __init__(
        self,
        pdf: pikepdf.Pdf,
        role_map: Dict[str, str],
        page_map: Dict[Any, int],
        page_mcid_data: Optional[Dict[int, Dict[int, Tuple[str, Tuple[float, float, float, float]]]]] = None
    ):
        self.pdf = pdf
        self.role_map = role_map
        self.page_map = page_map  # Map pikepdf page object ref -> 1-based page number
        self.page_mcid_data = page_mcid_data or {}  # page -> {mcid: (text, bbox)}
        self.node_counter = 0
        self.parent_tree_entries: Dict[int, Any] = {}
        self.has_parent_tree: bool = False
        self.parent_tree_valid: bool = False

    def parse(self) -> Optional[StructureNode]:
        """Parses the root StructTreeRoot and /ParentTree if present."""
        try:
            if "/StructTreeRoot" not in self.pdf.Root:
                return None

            root_obj = self.pdf.Root.StructTreeRoot

            # Parse ParentTree
            if "/ParentTree" in root_obj:
                self.has_parent_tree = True
                try:
                    self.parent_tree_entries = parse_number_tree(root_obj["/ParentTree"])
                    self.parent_tree_valid = len(self.parent_tree_entries) > 0
                except Exception as e:
                    logger.debug(f"Failed parsing ParentTree: {e}")
                    self.parent_tree_valid = False

            root_node = StructureNode(
                id="root",
                tag="StructTreeRoot",
                standard_tag="StructTreeRoot",
                title="Root",
            )

            if "/K" in root_obj:
                k_val = root_obj["/K"]
                self._parse_k(k_val, root_node)

            return root_node
        except Exception as e:
            logger.warning(f"Error parsing Structure Tree: {e}")
            return None

    def _parse_k(self, k_val: Any, parent_node: StructureNode):
        """Recursively parses the /K entry."""
        if isinstance(k_val, pikepdf.Array):
            for item in k_val:
                self._parse_k_item(item, parent_node)
        else:
            self._parse_k_item(k_val, parent_node)

    def _parse_k_item(self, item: Any, parent_node: StructureNode):
        if isinstance(item, pikepdf.Dictionary):
            elem_type = str(item.get("/Type", ""))
            if elem_type == "/MCR":
                # Marked Content Reference
                mcid = int(item.get("/MCID", -1))
                if mcid >= 0:
                    parent_node.mcids.append(mcid)
                pg_ref = item.get("/Pg")
                if pg_ref and parent_node.page is None:
                    parent_node.page = self._resolve_page_number(pg_ref)
                return

            if elem_type == "/OBJR":
                # Object reference
                pg_ref = item.get("/Pg")
                if pg_ref and parent_node.page is None:
                    parent_node.page = self._resolve_page_number(pg_ref)
                return

            # Structural element /StructElem
            self.node_counter += 1
            node_id = f"node_{self.node_counter}"

            raw_tag = str(item.get("/S", "Span")).strip("/ ")
            standard_tag, _, _ = resolve_role(raw_tag, self.role_map)

            title = str(item.get("/T")) if "/T" in item else None
            alt_text = str(item.get("/Alt")) if "/Alt" in item else None
            actual_text = str(item.get("/ActualText")) if "/ActualText" in item else None
            lang = str(item.get("/Lang")) if "/Lang" in item else None

            page_num = None
            if "/Pg" in item:
                page_num = self._resolve_page_number(item["/Pg"])

            # Attributes dictionary /A
            attrs: Dict[str, Any] = {}
            if "/A" in item:
                a_val = item["/A"]
                if isinstance(a_val, pikepdf.Dictionary):
                    for k, v in a_val.items():
                        attrs[str(k).strip("/")] = str(v)
                elif isinstance(a_val, pikepdf.Array):
                    for idx, a_elem in enumerate(a_val):
                        if isinstance(a_elem, pikepdf.Dictionary):
                            for k, v in a_elem.items():
                                attrs[f"{str(k).strip('/')}_{idx}"] = str(v)

            child_node = StructureNode(
                id=node_id,
                tag=raw_tag,
                standard_tag=standard_tag,
                title=title,
                alt_text=alt_text,
                actual_text=actual_text,
                lang=lang,
                page=page_num or parent_node.page,
                attributes=attrs,
                obj_num=getattr(item, "objgen", (None, None))[0] if hasattr(item, "objgen") else None
            )

            # Traverse /K of this element
            if "/K" in item:
                self._parse_k(item["/K"], child_node)

            # Attach actual page text and bounding box from MCID data
            self._link_mcid_data(child_node)

            parent_node.children.append(child_node)

        elif isinstance(item, (int, pikepdf.Integer)):
            # Direct MCID on parent
            parent_node.mcids.append(int(item))
            self._link_mcid_data(parent_node)

    def _link_mcid_data(self, node: StructureNode):
        """Populates node.text_content and node.bbox from real page MCID records."""
        if not node.page or not node.mcids:
            return

        page_data = self.page_mcid_data.get(node.page)
        if not page_data:
            return

        texts: List[str] = []
        bboxes: List[Tuple[float, float, float, float]] = []

        for mcid in node.mcids:
            if mcid in page_data:
                txt, box = page_data[mcid]
                if txt:
                    texts.append(txt)
                if box and any(c > 0 for c in box):
                    bboxes.append(box)

        if texts and not node.text_content:
            node.text_content = " ".join(texts)

        if bboxes and not node.bbox:
            # Union of bounding boxes
            min_x = min(b[0] for b in bboxes)
            min_y = min(b[1] for b in bboxes)
            max_x = max(b[2] for b in bboxes)
            max_y = max(b[3] for b in bboxes)
            node.bbox = (min_x, min_y, max_x, max_y)

    def _resolve_page_number(self, pg_obj: Any) -> Optional[int]:
        """Resolves a pikepdf page dictionary or indirect object to a 1-based page number."""
        try:
            if hasattr(pg_obj, "objgen"):
                return self.page_map.get(pg_obj.objgen)
            for page_idx, page in enumerate(self.pdf.pages, start=1):
                if page.objgen == getattr(pg_obj, "objgen", None):
                    return page_idx
        except Exception:
            pass
        return None
