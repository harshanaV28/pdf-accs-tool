"""
Screen Reader Preview View
Simulates how assistive technologies (NVDA, JAWS, VoiceOver) linearize, voice,
and announce structural elements, headings, lists, tables, and alternative descriptions.
"""

from typing import Optional, List
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextBrowser, QLabel,
    QPushButton, QFrame
)
from PySide6.QtCore import Qt
from ...core.models import PDFDocumentModel, StructureNode


class ScreenReaderView(QWidget):
    """View presenting a linearized assistive technology speech transcript."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # Header Info Banner
        header = QFrame()
        header.setStyleSheet("background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 6px; padding: 10px;")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(8, 4, 8, 4)

        info_lbl = QLabel(
            "🔊 <b>Screen Reader Preview (Linearized Speech Simulation)</b><br/>"
            "<span style='color: #475569; font-size: 11px;'>"
            "Demonstrates the exact reading order and speech announcements (tags, headings, lists, alt text) voiced by screen readers."
            "</span>"
        )
        h_layout.addWidget(info_lbl)
        layout.addWidget(header)

        # Transcript display
        self.text_browser = QTextBrowser()
        self.text_browser.setStyleSheet("""
            QTextBrowser {
                background-color: #ffffff;
                border: 1px solid #cbd5e1;
                border-radius: 8px;
                padding: 16px;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                font-size: 13px;
                line-height: 1.6;
            }
        """)
        layout.addWidget(self.text_browser)

    def load_document(self, doc: PDFDocumentModel):
        """Generates the speech linearization transcript."""
        if not doc.is_tagged or not doc.structure_tree:
            self._render_untagged_preview(doc)
            return

        html_parts = [
            f"<div style='border-bottom: 2px solid #e2e8f0; padding-bottom: 12px; margin-bottom: 16px;'>"
            f"<h2 style='margin:0; color:#1e293b;'>Screen Reader Speech Stream</h2>"
            f"<p style='color:#64748b; font-size:12px; margin:4px 0 0 0;'>"
            f"Document Title: <strong>{doc.title or 'Untitled'}</strong> | Language: <strong>{doc.language or 'Default'}</strong>"
            f"</p></div>"
        ]

        # Traverse structure tree nodes in reading order
        self._linearize_node(doc.structure_tree, html_parts)

        self.text_browser.setHtml("".join(html_parts))

    def _linearize_node(self, node: StructureNode, out_list: List[str]):
        tag = node.standard_tag.upper()

        if tag == "STRUCTTREEROOT":
            for child in node.children:
                self._linearize_node(child, out_list)
            return

        # Heading tags
        if tag in ("H1", "H2", "H3", "H4", "H5", "H6"):
            level = tag[1]
            out_list.append(
                f"<div style='margin: 12px 0 6px 0;'>"
                f"<span style='background:#dbeafe; color:#1e40af; font-size:10px; font-weight:700; padding:2px 6px; border-radius:4px;'>"
                f"HEADING LEVEL {level}</span> "
                f"<strong style='font-size: 15px; color:#0f172a;'>{node.title or node.actual_text or '[Heading Text]'}</strong>"
                f"</div>"
            )

        # Figures / Graphics
        elif tag in ("FIGURE", "FORMULA"):
            alt_display = node.alt_text or node.actual_text
            if alt_display:
                out_list.append(
                    f"<div style='background:#fef3c7; border-left:4px solid #f59e0b; padding:6px 10px; margin:8px 0; border-radius:4px;'>"
                    f"<span style='color:#92400e; font-weight:700; font-size:11px;'>GRAPHIC:</span> "
                    f"<span style='color:#78350f;'>\"{alt_display}\"</span>"
                    f"</div>"
                )
            else:
                out_list.append(
                    f"<div style='background:#fee2e2; border-left:4px solid #ef4444; padding:6px 10px; margin:8px 0; border-radius:4px;'>"
                    f"<span style='color:#991b1b; font-weight:700; font-size:11px;'>GRAPHIC (MISSING ALT TEXT):</span> "
                    f"<span style='color:#b91c1c;'>[Unlabeled Image on Page {node.page or '?'}]</span>"
                    f"</div>"
                )

        # Tables
        elif tag == "TABLE":
            summary = f" - \"{node.title}\"" if node.title else ""
            out_list.append(
                f"<div style='border:1px solid #cbd5e1; border-radius:6px; padding:10px; margin:12px 0; background:#f8fafc;'>"
                f"<div style='font-weight:700; color:#047857; margin-bottom:6px;'>TABLE{summary}</div>"
            )
            for child in node.children:
                self._linearize_node(child, out_list)
            out_list.append("</div>")
            return

        # Links
        elif tag == "LINK":
            link_text = node.alt_text or node.actual_text or "[Hyperlink]"
            out_list.append(
                f"<span style='color:#2563eb; text-decoration:underline; font-weight:500;'>🔗 {link_text}</span> "
            )

        # Paragraphs & general blocks
        elif tag == "P":
            p_text = node.actual_text or node.title or ""
            out_list.append(f"<p style='margin: 6px 0; color:#334155;'>{p_text}</p>")

        # Lists
        elif tag == "L":
            out_list.append("<ul style='margin: 6px 0; padding-left: 20px;'>")
            for child in node.children:
                self._linearize_node(child, out_list)
            out_list.append("</ul>")
            return

        elif tag == "LI":
            out_list.append("<li style='margin: 3px 0;'>")
            for child in node.children:
                self._linearize_node(child, out_list)
            out_list.append("</li>")
            return

        # Recurse children
        for child in node.children:
            self._linearize_node(child, out_list)

    def _render_untagged_preview(self, doc: PDFDocumentModel):
        html = (
            "<div style='background:#fee2e2; border:1px solid #f87171; border-radius:8px; padding:16px; margin-bottom:16px;'>"
            "<h3 style='color:#991b1b; margin-top:0;'>⚠️ Untagged Document Warning</h3>"
            "<p style='color:#7f1d1d;'>"
            "This PDF is not a Tagged PDF and does not possess a Logical Structure Tree (/StructTreeRoot). "
            "Screen readers cannot determine headings, reading order, table grids, or alternative descriptions. "
            "Assistive technology will fall back to raw geometric page text extraction."
            "</p></div>"
        )
        for p in doc.pages[:5]:
            html += (
                f"<div style='border:1px solid #e2e8f0; border-radius:6px; padding:12px; margin-bottom:10px;'>"
                f"<strong>--- Page {p.page_number} ---</strong><br/>"
                f"<pre style='font-family:monospace; color:#475569;'>{p.text[:400] + ('...' if len(p.text)>400 else '')}</pre>"
                f"</div>"
            )
        self.text_browser.setHtml(html)
