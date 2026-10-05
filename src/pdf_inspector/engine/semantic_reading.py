"""
Semantic Reading Engine
Generates the document's logical accessibility reading sequence based strictly on the
PDF Logical Structure Tree (/StructTreeRoot), structure elements, tag hierarchy,
headings, lists, tables, figures, alternative text, and accessibility metadata.

Important:
This produces a structural semantic reading preview to inspect the document's
tag-based reading sequence. It does not claim to reproduce the exact synthesized
speech output of specific screen readers (NVDA, JAWS, VoiceOver, Narrator).
"""

from typing import List, Dict, Optional, Tuple, Any
import html
from dataclasses import dataclass, field
from ..core.models import PDFDocumentModel, StructureNode


@dataclass
class SemanticItem:
    """Represents a single linear semantic reading element."""
    tag: str
    standard_tag: str
    role_display: str
    content: str = ""
    alt_text: Optional[str] = None
    actual_text: Optional[str] = None
    extracted_graphic_text: Optional[str] = None
    ai_description: Optional[str] = None
    expanded_text: Optional[str] = None
    is_artifact: bool = False
    is_missing_alt: bool = False
    is_empty_alt: bool = False
    is_empty_heading: bool = False
    has_decoding_error: bool = False
    decoding_error_msg: str = ""
    page: Optional[int] = None
    obj_num: Optional[int] = None
    depth: int = 0
    children: List['SemanticItem'] = field(default_factory=list)


@dataclass
class SemanticReadingResult:
    """Complete output of the semantic reading sequence."""
    is_tagged: bool
    html: str
    plain_text: str
    items: List[SemanticItem]
    total_headings: int = 0
    total_figures: int = 0
    total_lists: int = 0
    total_tables: int = 0
    total_paragraphs: int = 0
    warnings: List[str] = field(default_factory=list)


class SemanticReadingEngine:
    """Parses PDF accessibility structure into a structured semantic reading sequence."""

    INFO_BANNER_HTML = (
        "<div style='background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 6px; padding: 12px; margin-bottom: 16px;'>"
        "<div style='font-weight: 700; color: #1e3a8a; font-size: 14px; margin-bottom: 4px;'>"
        "📖 Semantic Reading Preview"
        "</div>"
        "<div style='color: #334155; font-size: 12px; line-height: 1.5;'>"
        "Simulates the document's logical reading sequence using PDF tags, structure elements, headings, lists, figures, "
        "alternative text and other accessibility metadata. This is a semantic preview and is not a replacement for testing with an actual screen reader."
        "</div>"
        "<div style='margin-top: 8px; padding-top: 8px; border-top: 1px solid #dbeafe; color: #64748b; font-size: 11px; font-style: italic;'>"
        "ℹ️ Semantic preview based on PDF accessibility structure. Validate final reading behavior with a real screen reader."
        "</div>"
        "</div>"
    )

    UNTAGGED_WARNING_TEXT = "Semantic reading order unavailable — document is not sufficiently tagged."

    def __init__(self):
        self.total_headings = 0
        self.total_figures = 0
        self.total_lists = 0
        self.total_tables = 0
        self.total_paragraphs = 0
        self.warnings: List[str] = []

    def generate(self, doc: PDFDocumentModel) -> SemanticReadingResult:
        """Generates the semantic reading sequence for a PDF document."""
        self.total_headings = 0
        self.total_figures = 0
        self.total_lists = 0
        self.total_tables = 0
        self.total_paragraphs = 0
        self.warnings = []

        if not doc.is_tagged or not doc.structure_tree:
            return self._build_untagged_result(doc)

        items: List[SemanticItem] = []
        self._linearize_node(doc.structure_tree, items, depth=0)

        # Build HTML and Plain Text streams
        html_buffer: List[str] = [
            self.INFO_BANNER_HTML,
            f"<div style='border-bottom: 2px solid #e2e8f0; padding-bottom: 10px; margin-bottom: 16px;'>",
            f"<span style='font-size: 16px; font-weight: 700; color: #0f172a;'>{html.escape(doc.title or doc.filename)}</span>",
            f"<div style='color: #64748b; font-size: 12px; margin-top: 4px;'>",
            f"Language: <strong>{html.escape(doc.language or 'Not specified')}</strong> &bull; ",
            f"Pages: <strong>{doc.page_count}</strong> &bull; ",
            f"Tags: <strong>{len([n for n in doc.structure_tree.find_all_nodes() if n.tag != 'StructTreeRoot'])}</strong>",
            f"</div></div>"
        ]

        text_buffer: List[str] = [
            f"SEMANTIC READING PREVIEW",
            f"Document: {doc.title or doc.filename}",
            f"Language: {doc.language or 'Not specified'}",
            f"Pages: {doc.page_count}",
            f"{'=' * 60}\n"
        ]

        for item in items:
            self._render_item(item, html_buffer, text_buffer)

        return SemanticReadingResult(
            is_tagged=True,
            html="".join(html_buffer),
            plain_text="\n".join(text_buffer),
            items=items,
            total_headings=self.total_headings,
            total_figures=self.total_figures,
            total_lists=self.total_lists,
            total_tables=self.total_tables,
            total_paragraphs=self.total_paragraphs,
            warnings=self.warnings
        )

    def _linearize_node(self, node: StructureNode, out_items: List[SemanticItem], depth: int = 0):
        tag = node.standard_tag.upper()

        # Document & Grouping Containers -> Transparently traverse children in reading sequence
        if tag in ("STRUCTTREEROOT", "DOCUMENT", "PART", "ART", "SECT", "DIV", "TOC", "TOCI", "INDEX", "NONSTRUCT", "PRIVATE"):
            for child in node.children:
                self._linearize_node(child, out_items, depth)
            return

        # 1. Headings (H, H1, H2, H3, H4, H5, H6)
        if tag in ("H", "H1", "H2", "H3", "H4", "H5", "H6"):
            self.total_headings += 1
            level = tag[1] if len(tag) > 1 and tag[1].isdigit() else str(min(6, max(1, depth + 1)))
            readable_text = node.get_readable_text()

            item = SemanticItem(
                tag=node.tag,
                standard_tag=tag,
                role_display=f"HEADING LEVEL {level}",
                content=readable_text,
                page=node.page,
                obj_num=node.obj_num,
                depth=depth,
                has_decoding_error=node.has_decoding_error,
                decoding_error_msg=node.decoding_error_msg
            )
            if not readable_text:
                item.is_empty_heading = True
            out_items.append(item)
            return

        # 2. Figures & Graphics (FIGURE, FORMULA, MATH)
        if tag in ("FIGURE", "FORMULA", "MATH"):
            self.total_figures += 1
            is_artifact = node.is_decorative()
            clean_alt = node.alt_text.strip().replace("\x00", "") if node.alt_text is not None else None
            clean_actual = node.actual_text.strip().replace("\x00", "") if node.actual_text is not None else None
            clean_extracted = (
                node.extracted_graphic_text.strip().replace("\x00", "")
                if node.extracted_graphic_text
                else node.text_content.strip().replace("\x00", "")
            )

            is_missing_alt = (node.alt_text is None and not is_artifact)
            is_empty_alt = (node.alt_text is not None and not clean_alt and not is_artifact)

            role_name = "FORMULA" if tag in ("FORMULA", "MATH") else "FIGURE"

            item = SemanticItem(
                tag=node.tag,
                standard_tag=tag,
                role_display=role_name,
                alt_text=clean_alt,
                actual_text=clean_actual,
                extracted_graphic_text=clean_extracted if clean_extracted else None,
                ai_description=node.ai_description,
                is_artifact=is_artifact,
                is_missing_alt=is_missing_alt,
                is_empty_alt=is_empty_alt,
                page=node.page,
                obj_num=node.obj_num,
                depth=depth,
                has_decoding_error=node.has_decoding_error,
                decoding_error_msg=node.decoding_error_msg
            )
            out_items.append(item)
            return

        # 3. Artifacts / Decorative Elements
        if node.is_decorative():
            item = SemanticItem(
                tag=node.tag,
                standard_tag="Artifact",
                role_display="DECORATIVE / ARTIFACT",
                is_artifact=True,
                page=node.page,
                obj_num=node.obj_num,
                depth=depth
            )
            out_items.append(item)
            return

        # 4. Lists (L) & List Items (LI)
        if tag == "L":
            self.total_lists += 1
            list_item = SemanticItem(
                tag=node.tag,
                standard_tag="L",
                role_display="LIST",
                depth=depth,
                page=node.page,
                obj_num=node.obj_num
            )
            for child in node.children:
                self._linearize_node(child, list_item.children, depth + 1)
            out_items.append(list_item)
            return

        if tag == "LI":
            # Extract marker/label if Lbl is present
            lbl_text = ""
            for child in node.children:
                if child.standard_tag.upper() == "LBL":
                    lbl_text = child.get_readable_text()
                    break

            li_item = SemanticItem(
                tag=node.tag,
                standard_tag="LI",
                role_display="LIST ITEM",
                content=lbl_text,
                depth=depth,
                page=node.page,
                obj_num=node.obj_num
            )
            for child in node.children:
                if child.standard_tag.upper() != "LBL":
                    self._linearize_node(child, li_item.children, depth + 1)

            # Fallback: If no children produced content, extract text directly from LI
            if not li_item.children:
                li_text = node.get_readable_text()
                if lbl_text and li_text.startswith(lbl_text):
                    li_text = li_text[len(lbl_text):].strip()
                if li_text:
                    li_item.children.append(SemanticItem(
                        tag="P",
                        standard_tag="P",
                        role_display="PARAGRAPH",
                        content=li_text,
                        depth=depth + 1,
                        page=node.page,
                        obj_num=node.obj_num
                    ))

            out_items.append(li_item)
            return

        if tag == "LBODY":
            if node.children:
                for child in node.children:
                    self._linearize_node(child, out_items, depth)
            else:
                body_txt = node.get_readable_text()
                if body_txt:
                    out_items.append(SemanticItem(
                        tag=node.tag,
                        standard_tag="P",
                        role_display="PARAGRAPH",
                        content=body_txt,
                        depth=depth,
                        page=node.page,
                        obj_num=node.obj_num
                    ))
            return

        # 5. Tables (TABLE, TR, TH, TD, CAPTION)
        if tag == "TABLE":
            self.total_tables += 1
            caption_text = ""
            for child in node.children:
                if child.standard_tag.upper() == "CAPTION":
                    caption_text = child.get_readable_text()
                    break

            table_item = SemanticItem(
                tag=node.tag,
                standard_tag="TABLE",
                role_display="TABLE",
                content=caption_text or (node.title or ""),
                depth=depth,
                page=node.page,
                obj_num=node.obj_num
            )
            for child in node.children:
                if child.standard_tag.upper() != "CAPTION":
                    self._linearize_node(child, table_item.children, depth + 1)
            out_items.append(table_item)
            return

        if tag in ("TR", "THEAD", "TBODY", "TFOOT"):
            for child in node.children:
                self._linearize_node(child, out_items, depth)
            return

        if tag in ("TH", "TD"):
            cell_type = "Header" if tag == "TH" else "Cell"
            cell_text = node.get_readable_text()
            item = SemanticItem(
                tag=node.tag,
                standard_tag=tag,
                role_display=f"TABLE {cell_type.upper()}",
                content=cell_text,
                depth=depth,
                page=node.page,
                obj_num=node.obj_num
            )
            out_items.append(item)
            return

        # 6. Paragraphs (P) & Semantic Text Blocks (BlockQuote, Caption, Note)
        if tag in ("P", "BLOCKQUOTE", "CAPTION", "NOTE", "SPAN"):
            if tag == "P":
                self.total_paragraphs += 1

            # If node contains nested structural blocks like Figure, Table, or List, traverse children
            has_nested_blocks = any(c.standard_tag.upper() in ("FIGURE", "FORMULA", "TABLE", "L", "H", "H1", "H2", "H3", "H4", "H5", "H6") for c in node.children)
            if has_nested_blocks:
                for child in node.children:
                    self._linearize_node(child, out_items, depth)
                return

            p_text = node.get_readable_text()
            if p_text:
                item = SemanticItem(
                    tag=node.tag,
                    standard_tag=tag,
                    role_display=tag if tag in ("P", "BLOCKQUOTE", "NOTE", "CAPTION") else "TEXT",
                    content=p_text,
                    actual_text=node.actual_text,
                    expanded_text=node.expanded_text,
                    page=node.page,
                    obj_num=node.obj_num,
                    depth=depth,
                    has_decoding_error=node.has_decoding_error,
                    decoding_error_msg=node.decoding_error_msg
                )
                out_items.append(item)
                return

        # 7. Links
        if tag == "LINK":
            link_text = node.get_readable_text() or node.alt_text or "Link"
            item = SemanticItem(
                tag=node.tag,
                standard_tag="LINK",
                role_display="LINK",
                content=link_text,
                page=node.page,
                obj_num=node.obj_num,
                depth=depth
            )
            out_items.append(item)
            return

        # Fallback: Traverse children or capture inline text if present
        node_text = node.get_readable_text(recursive=False)
        if node_text and not node.children:
            item = SemanticItem(
                tag=node.tag,
                standard_tag=tag,
                role_display="TEXT",
                content=node_text,
                page=node.page,
                obj_num=node.obj_num,
                depth=depth
            )
            out_items.append(item)
            return

        for child in node.children:
            self._linearize_node(child, out_items, depth)

    def _render_item(self, item: SemanticItem, html_out: List[str], text_out: List[str]):
        """Renders a single SemanticItem into both HTML and Plain Text streams."""
        indent = "  " * item.depth

        # --- Decoding Warning (if present) ---
        if item.has_decoding_error:
            warn_msg = item.decoding_error_msg or "Character extraction anomaly detected."
            html_out.append(
                f"<div style='background: #fff1f2; border: 1px solid #fecdd3; border-radius: 4px; padding: 4px 8px; margin: 4px 0; font-size: 11px; color: #be123c;'>"
                f"⚠️ <strong>Character Extraction Warning:</strong> {html.escape(warn_msg)}"
                f"</div>"
            )
            text_out.append(f"{indent}[Character Extraction Warning: {warn_msg}]")

        # --- 1. Headings ---
        if item.standard_tag in ("H", "H1", "H2", "H3", "H4", "H5", "H6"):
            if not item.is_empty_heading and item.content:
                html_out.append(
                    f"<div style='margin: 14px 0 6px 0;'>"
                    f"<span style='background: #dbeafe; color: #1e40af; font-size: 10px; font-weight: 700; padding: 2px 8px; border-radius: 4px; text-transform: uppercase;'>"
                    f"{html.escape(item.role_display)}</span>"
                    f"<div style='font-size: 15px; font-weight: 700; color: #0f172a; margin-top: 4px;'>"
                    f"{html.escape(item.content)}"
                    f"</div></div>"
                )
                text_out.append(f"{indent}{item.role_display}\n{indent}{item.content}\n")
            else:
                html_out.append(
                    f"<div style='margin: 14px 0 6px 0; background: #fffbeb; border: 1px solid #fde68a; border-radius: 6px; padding: 10px;'>"
                    f"<span style='background: #fef3c7; color: #92400e; font-size: 10px; font-weight: 700; padding: 2px 8px; border-radius: 4px; text-transform: uppercase;'>"
                    f"{html.escape(item.role_display)}</span>"
                    f"<div style='font-size: 13px; font-style: italic; color: #b45309; margin: 4px 0; font-weight: 600;'>"
                    f"[No readable text available]"
                    f"</div>"
                    f"<div style='font-size: 11px; color: #64748b; font-family: monospace; line-height: 1.4;'>"
                    f"Structure role: {html.escape(item.tag)}<br/>"
                    f"Page: {item.page or 'Unknown'}<br/>"
                    f"Object: {item.obj_num or 'Unknown'}"
                    f"</div></div>"
                )
                text_out.append(
                    f"{indent}{item.role_display}\n"
                    f"{indent}[No readable text available]\n"
                    f"{indent}Structure role: {item.tag}\n"
                    f"{indent}Page: {item.page or 'Unknown'}\n"
                    f"{indent}Object: {item.obj_num or 'Unknown'}\n"
                )
            return

        # --- 2. Figures & Graphics ---
        if item.standard_tag in ("FIGURE", "FORMULA", "MATH"):
            tag_label = "FORMULA" if item.standard_tag in ("FORMULA", "MATH") else "FIGURE"

            # Case A: Decorative / Artifact
            if item.is_artifact:
                html_out.append(
                    f"<div style='margin: 8px 0; padding: 8px 12px; background: #f8fafc; border-left: 4px solid #94a3b8; border-radius: 4px;'>"
                    f"<span style='background: #e2e8f0; color: #475569; font-size: 10px; font-weight: 700; padding: 2px 6px; border-radius: 3px;'>"
                    f"{tag_label} &bull; DECORATIVE / ARTIFACT</span>"
                    f"<div style='color: #64748b; font-size: 12px; margin-top: 4px; font-style: italic;'>"
                    f"Alternative text not required"
                    f"</div>"
                    f"<div style='font-size: 10px; color: #94a3b8; margin-top: 2px; font-family: monospace;'>"
                    f"Page: {item.page or 'Unknown'} | Object: {item.obj_num or 'Unknown'}"
                    f"</div></div>"
                )
                text_out.append(
                    f"{indent}{tag_label}\n"
                    f"{indent}Decorative / Artifact\n"
                    f"{indent}Alternative text not required\n"
                )
                return

            # Case B: Valid Alternative Text
            if item.alt_text:
                extra_html = ""
                extra_text = ""
                if item.extracted_graphic_text:
                    extra_html += (
                        f"<div style='margin-top: 6px; padding: 4px 8px; background: #ffffff; border: 1px dashed #cbd5e1; border-radius: 4px;'>"
                        f"<span style='color: #475569; font-size: 11px; font-weight: 600;'>Extracted graphic text:</span> "
                        f"<span style='color: #334155; font-size: 12px;'>{html.escape(item.extracted_graphic_text)}</span>"
                        f"</div>"
                    )
                    extra_text += f"\n{indent}Extracted graphic text:\n{indent}{item.extracted_graphic_text}"

                if item.ai_description:
                    extra_html += (
                        f"<div style='margin-top: 6px; padding: 4px 8px; background: #faf5ff; border: 1px dashed #c084fc; border-radius: 4px;'>"
                        f"<span style='color: #6b21a8; font-size: 11px; font-weight: 600;'>AI-generated description:</span> "
                        f"<span style='color: #581c87; font-size: 12px; font-style: italic;'>{html.escape(item.ai_description)}</span>"
                        f"</div>"
                    )
                    extra_text += f"\n{indent}AI-generated description:\n{indent}{item.ai_description}"

                html_out.append(
                    f"<div style='margin: 8px 0; padding: 10px 14px; background: #f0fdf4; border-left: 4px solid #22c55e; border-radius: 4px;'>"
                    f"<span style='background: #dcfce7; color: #166534; font-size: 10px; font-weight: 700; padding: 2px 6px; border-radius: 3px;'>"
                    f"{tag_label}</span>"
                    f"<div style='margin-top: 4px; font-size: 12px; color: #166534; font-weight: 600;'>Alternative text:</div>"
                    f"<div style='color: #14532d; font-size: 13px; margin-top: 2px;'>{html.escape(item.alt_text)}</div>"
                    f"{extra_html}</div>"
                )
                text_out.append(f"{indent}{tag_label}\n{indent}Alternative text:\n{indent}{item.alt_text}{extra_text}\n")
                return

            # Case C: Empty Alternative Text
            if item.is_empty_alt:
                extra_html = ""
                extra_text = ""
                if item.extracted_graphic_text:
                    extra_html += (
                        f"<div style='margin-top: 6px; padding: 4px 8px; background: #ffffff; border: 1px dashed #cbd5e1; border-radius: 4px;'>"
                        f"<span style='color: #475569; font-size: 11px; font-weight: 600;'>Extracted graphic text:</span> "
                        f"<span style='color: #334155; font-size: 12px;'>{html.escape(item.extracted_graphic_text)}</span>"
                        f"</div>"
                    )
                    extra_text += f"\n{indent}Extracted graphic text:\n{indent}{item.extracted_graphic_text}"

                html_out.append(
                    f"<div style='margin: 8px 0; padding: 10px 14px; background: #fffbeb; border-left: 4px solid #f59e0b; border-radius: 4px;'>"
                    f"<span style='background: #fef3c7; color: #92400e; font-size: 10px; font-weight: 700; padding: 2px 6px; border-radius: 3px;'>"
                    f"{tag_label}</span>"
                    f"<div style='margin-top: 4px; font-size: 12px; color: #b45309; font-weight: 600;'>Alternative text: [Empty string / whitespace]</div>"
                    f"<div style='font-size: 11px; color: #92400e; margin-top: 2px;'>"
                    f"⚠️ Figure has an empty /Alt attribute. If meaningful, provide descriptive alternative text; if decorative, mark as an Artifact."
                    f"</div>"
                    f"{extra_html}</div>"
                )
                text_out.append(f"{indent}{tag_label}\n{indent}Alternative text: [Empty string / whitespace]{extra_text}\n")
                return

            # Case D: Missing Alternative Text
            extra_html = ""
            extra_text = ""
            if item.extracted_graphic_text:
                extra_html += (
                    f"<div style='margin-top: 6px; padding: 4px 8px; background: #ffffff; border: 1px dashed #cbd5e1; border-radius: 4px;'>"
                    f"<span style='color: #475569; font-size: 11px; font-weight: 600;'>Extracted graphic text:</span> "
                    f"<span style='color: #334155; font-size: 12px;'>{html.escape(item.extracted_graphic_text)}</span>"
                    f"</div>"
                )
                extra_text += f"\n{indent}Extracted graphic text:\n{indent}{item.extracted_graphic_text}"

            html_out.append(
                f"<div style='margin: 8px 0; padding: 10px 14px; background: #fef2f2; border-left: 4px solid #ef4444; border-radius: 4px;'>"
                f"<span style='background: #fee2e2; color: #991b1b; font-size: 10px; font-weight: 700; padding: 2px 6px; border-radius: 3px;'>"
                f"{tag_label}</span>"
                f"<div style='margin-top: 4px; font-size: 12px; color: #dc2626; font-weight: 700;'>Alternative text: Missing</div>"
                f"<div style='font-size: 10px; color: #7f1d1d; margin-top: 2px; font-family: monospace;'>"
                f"Structure role: {html.escape(item.tag)} | Page: {item.page or 'Unknown'} | Object: {item.obj_num or 'Unknown'}"
                f"</div>"
                f"{extra_html}</div>"
            )
            text_out.append(f"{indent}{tag_label}\n{indent}Alternative text: Missing{extra_text}\n")
            return

        # --- 3. Lists (L) & List Items (LI) ---
        if item.standard_tag == "L":
            html_out.append(
                f"<div style='margin: 10px 0 10px {item.depth * 14}px; border-left: 2px solid #cbd5e1; padding-left: 10px;'>"
                f"<span style='background: #f1f5f9; color: #475569; font-size: 10px; font-weight: 700; padding: 2px 6px; border-radius: 3px;'>"
                f"LIST</span>"
            )
            text_out.append(f"{indent}LIST")
            for child in item.children:
                self._render_item(child, html_out, text_out)
            html_out.append("</div>")
            return

        if item.standard_tag == "LI":
            marker = f" &bull; {html.escape(item.content)}" if item.content else ""
            marker_plain = f" {item.content}" if item.content else ""
            html_out.append(
                f"<div style='margin: 6px 0 6px 8px; border-left: 2px solid #93c5fd; padding-left: 10px;'>"
                f"<span style='background: #e0f2fe; color: #0369a1; font-size: 10px; font-weight: 700; padding: 2px 6px; border-radius: 3px;'>"
                f"LIST ITEM{marker}</span>"
            )
            text_out.append(f"{indent}  LIST ITEM{marker_plain}")
            for child in item.children:
                self._render_item(child, html_out, text_out)
            html_out.append("</div>")
            return

        # --- 4. Tables ---
        if item.standard_tag == "TABLE":
            caption_str = f" &bull; {html.escape(item.content)}" if item.content else ""
            caption_plain = f" - {item.content}" if item.content else ""
            html_out.append(
                f"<div style='margin: 12px 0; border: 1px solid #cbd5e1; border-radius: 6px; background: #f8fafc; padding: 10px;'>"
                f"<div style='font-weight: 700; color: #047857; font-size: 12px; margin-bottom: 6px;'>"
                f"📊 TABLE{caption_str}</div>"
            )
            text_out.append(f"{indent}TABLE{caption_plain}")
            for child in item.children:
                self._render_item(child, html_out, text_out)
            html_out.append("</div>")
            return

        if item.standard_tag in ("TH", "TD"):
            prefix = "Header" if item.standard_tag == "TH" else "Row / Cell"
            badge_color = "#dcfce7" if item.standard_tag == "TH" else "#f1f5f9"
            text_color = "#166534" if item.standard_tag == "TH" else "#475569"
            html_out.append(
                f"<div style='margin: 3px 0 3px 12px; font-size: 12px;'>"
                f"<span style='background: {badge_color}; color: {text_color}; font-size: 9px; font-weight: 700; padding: 1px 5px; border-radius: 3px; margin-right: 4px;'>"
                f"{prefix}</span> "
                f"<span style='color: #1e293b;'>{html.escape(item.content)}</span>"
                f"</div>"
            )
            text_out.append(f"{indent}  {prefix}: {item.content}")
            return

        # --- 5. Paragraphs & General Text Blocks ---
        if item.standard_tag in ("P", "BLOCKQUOTE", "CAPTION", "NOTE", "TEXT"):
            badge_name = item.standard_tag if item.standard_tag in ("P", "BLOCKQUOTE", "NOTE") else "Paragraph"
            html_out.append(
                f"<div style='margin: 6px 0; color: #334155; font-size: 13px; line-height: 1.6;'>"
                f"<span style='background: #f8fafc; color: #64748b; font-size: 9px; font-weight: 600; padding: 1px 5px; border-radius: 3px; margin-right: 6px;'>"
                f"{badge_name}</span>"
                f"{html.escape(item.content)}"
                f"</div>"
            )
            text_out.append(f"{indent}{item.content}\n")
            return

        # --- 6. Links ---
        if item.standard_tag == "LINK":
            html_out.append(
                f"<span style='color: #2563eb; text-decoration: underline; font-weight: 500;'>"
                f"🔗 {html.escape(item.content)}</span> "
            )
            text_out.append(f"{indent}Link: {item.content}")
            return

        # --- Default Fallback ---
        if item.content:
            html_out.append(f"<div style='margin: 4px 0;'>{html.escape(item.content)}</div>")
            text_out.append(f"{indent}{item.content}")

    def _build_untagged_result(self, doc: PDFDocumentModel) -> SemanticReadingResult:
        """Produces a standardized untagged explanation without fabricating a reading order."""
        banner = (
            "<div style='background: #fef2f2; border: 1px solid #f87171; border-radius: 8px; padding: 16px; margin-bottom: 16px;'>"
            "<h3 style='color: #991b1b; margin-top: 0; font-size: 15px;'>⚠️ " + self.UNTAGGED_WARNING_TEXT + "</h3>"
            "<p style='color: #7f1d1d; font-size: 13px; line-height: 1.5; margin: 4px 0 0 0;'>"
            "This document does not contain a valid PDF Logical Structure Tree (/StructTreeRoot) or Tagged PDF MarkInfo. "
            "A reliable semantic reading sequence cannot be derived without structure tags. Assistive technologies cannot determine "
            "programmatic reading order, semantic headings, lists, tables, or alternative descriptions."
            "</p>"
            "</div>"
        )
        plain = (
            f"{self.UNTAGGED_WARNING_TEXT}\n"
            f"This document is untagged. No reliable semantic reading sequence can be derived without PDF structure tags."
        )
        return SemanticReadingResult(
            is_tagged=False,
            html=banner,
            plain_text=plain,
            items=[],
            warnings=[self.UNTAGGED_WARNING_TEXT]
        )
