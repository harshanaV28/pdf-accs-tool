"""
Tag Tree View
Interactive hierarchical explorer for the PDF Logical Structure Tree (/StructTreeRoot).
Displays structural tags, standard role mappings, alt text, and element attributes.
"""

from typing import Optional, Dict, Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QSplitter, QGroupBox, QLabel, QTextBrowser, QHeaderView
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QFont, QColor
from ...core.models import StructureNode


class TagTreeWidgetItem(QTreeWidgetItem):
    """Tree widget item holding reference to a StructureNode."""

    def __init__(self, node: StructureNode):
        super().__init__()
        self.node = node
        self._format_item()

    def _format_item(self):
        tag_display = f"<{self.node.tag}>"
        if self.node.standard_tag != self.node.tag and self.node.tag != "StructTreeRoot":
            tag_display += f"  (→ <{self.node.standard_tag}>)"

        self.setText(0, tag_display)
        self.setFont(0, QFont("Consolas", 10, QFont.Bold))

        # Page column
        pg_str = str(self.node.page) if self.node.page else ""
        self.setText(1, pg_str)
        self.setTextAlignment(1, Qt.AlignCenter)

        # Alt / Title / Description column
        desc = self.node.alt_text or self.node.actual_text or self.node.title or ""
        self.setText(2, desc[:60] + ("..." if len(desc) > 60 else ""))

        # Tag-specific icons/colors
        tag_up = self.node.standard_tag.upper()
        if tag_up in ("H1", "H2", "H3", "H4", "H5", "H6"):
            self.setForeground(0, QColor("#1d4ed8"))
        elif tag_up in ("FIGURE", "FORMULA"):
            self.setForeground(0, QColor("#b45309"))
        elif tag_up in ("TABLE", "TR", "TH", "TD"):
            self.setForeground(0, QColor("#047857"))
        elif tag_up == "LINK":
            self.setForeground(0, QColor("#7c3aed"))


class TagTreeView(QWidget):
    """View presenting the logical tag hierarchy and selected node attributes."""

    tag_selected = Signal(object)  # StructureNode

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        splitter = QSplitter(Qt.Horizontal)

        # 1. Left Tree Widget
        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)

        lbl_tree = QLabel("Document Structure Tree")
        lbl_tree.setStyleSheet("font-weight: 700; font-size: 13px; color: #1e293b;")
        left_layout.addWidget(lbl_tree)

        self.tree = QTreeWidget()
        self.tree.setColumnCount(3)
        self.tree.setHeaderLabels(["Structure Element", "Page", "Title / Alt Text"])
        self.tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tree.header().setSectionResizeMode(1, QHeaderView.Fixed)
        self.tree.header().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.tree.setColumnWidth(1, 55)

        self.tree.itemSelectionChanged.connect(self._on_item_selected)
        left_layout.addWidget(self.tree)
        splitter.addWidget(left_container)

        # 2. Right Node Properties Panel
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)

        prop_group = QGroupBox("Selected Tag Properties")
        prop_layout = QVBoxLayout(prop_group)

        self.lbl_tag = QLabel("Tag: -")
        self.lbl_tag.setStyleSheet("font-weight: 700; font-size: 13px; color: #2563eb;")
        prop_layout.addWidget(self.lbl_tag)

        self.lbl_std_tag = QLabel("Standard Type: -")
        prop_layout.addWidget(self.lbl_std_tag)

        self.lbl_page = QLabel("Page: -")
        prop_layout.addWidget(self.lbl_page)

        self.lbl_obj = QLabel("Object #: -")
        prop_layout.addWidget(self.lbl_obj)

        self.lbl_alt = QLabel("Alt Text: None")
        self.lbl_alt.setWordWrap(True)
        prop_layout.addWidget(self.lbl_alt)

        self.lbl_actual = QLabel("Actual Text: None")
        self.lbl_actual.setWordWrap(True)
        prop_layout.addWidget(self.lbl_actual)

        self.lbl_lang = QLabel("Language (/Lang): Inherited")
        prop_layout.addWidget(self.lbl_lang)

        prop_layout.addWidget(QLabel("<b>Element Attributes & Dictionary:</b>"))
        self.txt_attrs = QTextBrowser()
        self.txt_attrs.setStyleSheet("background: #f8fafc; border: 1px solid #e2e8f0; font-family: monospace; font-size: 11px;")
        prop_layout.addWidget(self.txt_attrs)

        right_layout.addWidget(prop_group)
        splitter.addWidget(right_container)

        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter)

    def load_structure_tree(self, root_node: Optional[StructureNode]):
        """Populates the tree widget with the structure node hierarchy."""
        self.tree.clear()
        if not root_node:
            item = QTreeWidgetItem(["(No Logical Structure Tree / Untagged PDF)", "", ""])
            self.tree.addTopLevelItem(item)
            return

        top_item = self._create_tree_item(root_node)
        self.tree.addTopLevelItem(top_item)
        top_item.setExpanded(True)

        # Expand first child container as well
        if top_item.childCount() > 0:
            top_item.child(0).setExpanded(True)

    def _create_tree_item(self, node: StructureNode) -> TagTreeWidgetItem:
        item = TagTreeWidgetItem(node)
        for child in node.children:
            child_item = self._create_tree_item(child)
            item.addChild(child_item)
        return item

    def _on_item_selected(self):
        items = self.tree.selectedItems()
        if not items or not isinstance(items[0], TagTreeWidgetItem):
            return

        node = items[0].node
        self.lbl_tag.setText(f"Tag: <{node.tag}>")
        self.lbl_std_tag.setText(f"Standard Type: <{node.standard_tag}>")
        self.lbl_page.setText(f"Page: {node.page or 'Document'}")
        self.lbl_obj.setText(f"Object #: {node.obj_num or 'N/A'}")
        self.lbl_alt.setText(f"Alt Text: {node.alt_text or 'None'}")
        self.lbl_actual.setText(f"Actual Text: {node.actual_text or 'None'}")
        self.lbl_lang.setText(f"Language: {node.lang or 'Default'}")

        # Format attributes
        attr_lines = []
        if node.mcids:
            attr_lines.append(f"MCIDs: {node.mcids}")
        for k, v in node.attributes.items():
            attr_lines.append(f"{k}: {v}")

        self.txt_attrs.setPlainText("\n".join(attr_lines) if attr_lines else "No special attributes.")
        self.tag_selected.emit(node)
