"""
PDF Structure Tree Parser
Parses the Logical Structure Tree (/StructTreeRoot) using pikepdf and resolves
custom role mappings to ISO 32000-1 standard structure types.
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


class StructureTreeParser:
    """Extracts and builds the hierarchical StructureNode tree from a pikepdf document."""

    def __init__(self, pdf: pikepdf.Pdf, role_map: Dict[str, str], page_map: Dict[Any, int]):
        self.pdf = pdf
        self.role_map = role_map
        self.page_map = page_map  # Map pikepdf page object ref -> 1-based page number
        self.node_counter = 0

    def parse(self) -> Optional[StructureNode]:
        """Parses the root StructTreeRoot if present."""
        try:
            if "/StructTreeRoot" not in self.pdf.Root:
                return None

            root_obj = self.pdf.Root.StructTreeRoot
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
            # Check if this is a StructElem or MCR (Marked Content Reference) or OBJR
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

            # It's a structural element /StructElem
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

            # Attributes
            attrs: Dict[str, Any] = {}
            if "/A" in item:
                a_val = item["/A"]
                if isinstance(a_val, pikepdf.Dictionary):
                    for k, v in a_val.items():
                        attrs[str(k).strip("/")] = str(v)

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

            parent_node.children.append(child_node)

        elif isinstance(item, (int, pikepdf.Integer)):
            # Direct MCID on parent
            parent_node.mcids.append(int(item))

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
