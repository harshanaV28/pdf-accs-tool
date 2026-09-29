"""
Elements View
Dedicated tabbed inspectors for document elements: Fonts, Images, Tables, Links, Form Fields, and Bookmarks.
"""

from typing import List, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTabWidget, QTableWidget, QTableWidgetItem,
    QHeaderView, QLabel, QFrame
)
from PySide6.QtCore import Qt, Signal
from ...core.models import PDFDocumentModel, FontModel, ImageModel, TableModel, LinkModel, FormFieldModel, BookmarkModel


class ElementsView(QWidget):
    """Container view with tabs for Fonts, Images, Tables, Links, Forms, and Bookmarks."""

    element_jump_requested = Signal(int, object)  # (page, bbox)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._fonts: List[FontModel] = []
        self._images: List[ImageModel] = []
        self._tables: List[TableModel] = []
        self._links: List[LinkModel] = []
        self._forms: List[FormFieldModel] = []
        self._bookmarks_flat: List[tuple] = []
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        self.tab_widget = QTabWidget()

        # 1. Fonts Tab
        self.table_fonts = self._create_table(["Font Name", "Subtype", "Embedded", "Subset", "ToUnicode", "Encoding", "Pages"])
        self.table_fonts.cellDoubleClicked.connect(self._on_font_double_clicked)
        self.tab_widget.addTab(self.table_fonts, "🔤 Fonts")

        # 2. Images Tab
        self.table_images = self._create_table(["Image ID", "Page", "Dimensions", "Color Space", "Has Alt Text", "Alternative Text", "Artifact"])
        self.table_images.cellDoubleClicked.connect(self._on_image_double_clicked)
        self.tab_widget.addTab(self.table_images, "🖼️ Images")

        # 3. Tables Tab
        self.table_tables = self._create_table(["Table ID", "Page", "Rows", "Cols", "Headers Present", "TH Cells", "TD Cells", "Regular"])
        self.table_tables.cellDoubleClicked.connect(self._on_table_double_clicked)
        self.tab_widget.addTab(self.table_tables, "📊 Tables")

        # 4. Links Tab
        self.table_links = self._create_table(["Page", "Link Anchor Text", "Destination URI / Target", "Tagged as Link", "Alt Text"])
        self.table_links.cellDoubleClicked.connect(self._on_link_double_clicked)
        self.tab_widget.addTab(self.table_links, "🔗 Links")

        # 5. Form Fields Tab
        self.table_forms = self._create_table(["Field Name", "Type", "Page", "Accessible Tooltip (/TU)", "Required"])
        self.table_forms.cellDoubleClicked.connect(self._on_form_double_clicked)
        self.tab_widget.addTab(self.table_forms, "📝 Forms")

        # 6. Bookmarks Tab
        self.table_bookmarks = self._create_table(["Level", "Bookmark Title", "Target Page"])
        self.table_bookmarks.cellDoubleClicked.connect(self._on_bookmark_double_clicked)
        self.tab_widget.addTab(self.table_bookmarks, "🔖 Bookmarks")

        layout.addWidget(self.tab_widget)

    def _create_table(self, headers: List[str]) -> QTableWidget:
        table = QTableWidget()
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.verticalHeader().setVisible(False)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setSelectionMode(QTableWidget.SingleSelection)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setAlternatingRowColors(True)
        table.setShowGrid(True)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        table.horizontalHeader().setStretchLastSection(True)
        return table

    def load_document(self, doc: PDFDocumentModel):
        """Populates all element tables with the extracted document assets."""
        self._populate_fonts(doc.fonts)
        self._populate_images(doc.images)
        self._populate_tables(doc.tables)
        self._populate_links(doc.links)
        self._populate_forms(doc.form_fields)
        self._populate_bookmarks(doc.bookmarks)

    def select_tab(self, tab_name: str):
        """Switches active sub-tab based on sidebar selection."""
        tab_map = {
            "Fonts": 0,
            "Images": 1,
            "Tables": 2,
            "Links": 3,
            "Forms": 4,
            "Bookmarks": 5,
        }
        idx = tab_map.get(tab_name)
        if idx is not None:
            self.tab_widget.setCurrentIndex(idx)

    def _populate_fonts(self, fonts: List[FontModel]):
        self._fonts = fonts
        self.table_fonts.setRowCount(len(fonts))
        for row, f in enumerate(fonts):
            self.table_fonts.setItem(row, 0, QTableWidgetItem(f.name))
            self.table_fonts.setItem(row, 1, QTableWidgetItem(f.subtype))
            self.table_fonts.setItem(row, 2, QTableWidgetItem("Yes" if f.is_embedded else "No"))
            self.table_fonts.setItem(row, 3, QTableWidgetItem("Yes" if f.is_subset else "No"))
            self.table_fonts.setItem(row, 4, QTableWidgetItem("Yes" if f.has_tounicode else "No"))
            self.table_fonts.setItem(row, 5, QTableWidgetItem(f.encoding))
            self.table_fonts.setItem(row, 6, QTableWidgetItem(", ".join(map(str, f.pages[:8]))))

    def _populate_images(self, images: List[ImageModel]):
        self._images = images
        self.table_images.setRowCount(len(images))
        for row, img in enumerate(images):
            self.table_images.setItem(row, 0, QTableWidgetItem(img.id))
            self.table_images.setItem(row, 1, QTableWidgetItem(str(img.page)))
            self.table_images.setItem(row, 2, QTableWidgetItem(f"{img.width} x {img.height}"))
            self.table_images.setItem(row, 3, QTableWidgetItem(img.colorspace))
            self.table_images.setItem(row, 4, QTableWidgetItem("Yes" if img.has_alt else "No"))
            self.table_images.setItem(row, 5, QTableWidgetItem(img.alt_text or "(None)"))
            self.table_images.setItem(row, 6, QTableWidgetItem("Yes" if img.is_artifact else "No"))

    def _populate_tables(self, tables: List[TableModel]):
        self._tables = tables
        self.table_tables.setRowCount(len(tables))
        for row, t in enumerate(tables):
            self.table_tables.setItem(row, 0, QTableWidgetItem(t.id))
            self.table_tables.setItem(row, 1, QTableWidgetItem(str(t.page)))
            self.table_tables.setItem(row, 2, QTableWidgetItem(str(t.rows_count)))
            self.table_tables.setItem(row, 3, QTableWidgetItem(str(t.cols_count)))
            self.table_tables.setItem(row, 4, QTableWidgetItem("Yes" if t.has_headers else "No"))
            self.table_tables.setItem(row, 5, QTableWidgetItem(str(t.header_cells_count)))
            self.table_tables.setItem(row, 6, QTableWidgetItem(str(t.data_cells_count)))
            self.table_tables.setItem(row, 7, QTableWidgetItem("Yes" if t.is_regular else "Irregular"))

    def _populate_links(self, links: List[LinkModel]):
        self._links = links
        self.table_links.setRowCount(len(links))
        for row, l in enumerate(links):
            self.table_links.setItem(row, 0, QTableWidgetItem(str(l.page)))
            self.table_links.setItem(row, 1, QTableWidgetItem(l.text))
            self.table_links.setItem(row, 2, QTableWidgetItem(l.uri))
            self.table_links.setItem(row, 3, QTableWidgetItem("Yes" if l.has_structure_link else "No"))
            self.table_links.setItem(row, 4, QTableWidgetItem(l.alt_text or "(None)"))

    def _populate_forms(self, fields: List[FormFieldModel]):
        self._forms = fields
        self.table_forms.setRowCount(len(fields))
        for row, f in enumerate(fields):
            self.table_forms.setItem(row, 0, QTableWidgetItem(f.name))
            self.table_forms.setItem(row, 1, QTableWidgetItem(f.field_type))
            self.table_forms.setItem(row, 2, QTableWidgetItem(str(f.page)))
            self.table_forms.setItem(row, 3, QTableWidgetItem(f.tooltip or "(Missing Tooltip)"))
            self.table_forms.setItem(row, 4, QTableWidgetItem("Yes" if f.is_required else "No"))

    def _populate_bookmarks(self, bookmarks: List[BookmarkModel]):
        flattened: List[tuple] = []

        def _flatten(items: List[BookmarkModel]):
            for b in items:
                indent = "  " * (b.level - 1)
                flattened.append((b.level, f"{indent}• {b.title}", b.page))
                if b.children:
                    _flatten(b.children)

        _flatten(bookmarks)
        self._bookmarks_flat = flattened
        self.table_bookmarks.setRowCount(len(flattened))
        for row, (lvl, title, page) in enumerate(flattened):
            self.table_bookmarks.setItem(row, 0, QTableWidgetItem(f"H{lvl}"))
            self.table_bookmarks.setItem(row, 1, QTableWidgetItem(title))
            self.table_bookmarks.setItem(row, 2, QTableWidgetItem(str(page)))

    # --- Double-click jump slots ---
    def _on_font_double_clicked(self, row: int, col: int):
        if 0 <= row < len(self._fonts):
            f = self._fonts[row]
            if f.pages:
                self.element_jump_requested.emit(f.pages[0], None)

    def _on_image_double_clicked(self, row: int, col: int):
        if 0 <= row < len(self._images):
            img = self._images[row]
            self.element_jump_requested.emit(img.page, img.bbox)

    def _on_table_double_clicked(self, row: int, col: int):
        if 0 <= row < len(self._tables):
            tbl = self._tables[row]
            self.element_jump_requested.emit(tbl.page, tbl.bbox)

    def _on_link_double_clicked(self, row: int, col: int):
        if 0 <= row < len(self._links):
            lnk = self._links[row]
            self.element_jump_requested.emit(lnk.page, lnk.bbox)

    def _on_form_double_clicked(self, row: int, col: int):
        if 0 <= row < len(self._forms):
            frm = self._forms[row]
            self.element_jump_requested.emit(frm.page, frm.bbox)

    def _on_bookmark_double_clicked(self, row: int, col: int):
        if 0 <= row < len(self._bookmarks_flat):
            lvl, title, page = self._bookmarks_flat[row]
            if page:
                self.element_jump_requested.emit(page, None)
