"""
Interactive PDF Canvas & Viewer Widget
Integrates standard scrollable document inspection with a high-precision PAC Visual Issue Locator:
- PAC Split Callout View: Page overview with green projection lines and magnified red-framed issue crop
- Full Document View: High-fidelity scrollable page viewer with glowing bounding box overlays
"""

from typing import Optional, Tuple, List, Any, Dict
import pymupdf

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
    QPushButton, QComboBox, QLineEdit, QToolBar, QFrame, QSizePolicy,
    QStackedWidget, QButtonGroup
)
from PySide6.QtCore import Qt, Signal, QRectF
from PySide6.QtGui import QImage, QPixmap, QPainter, QColor, QPen, QBrush

from ...core.models import CheckResult
from .pac_visual_locator import PACVisualLocatorWidget


class PageDisplayWidget(QLabel):
    """Draws the rendered page pixmap and any active bounding box highlight overlays."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.current_pixmap: Optional[QPixmap] = None
        self.active_bbox: Optional[Tuple[float, float, float, float]] = None  # (x0, y0, x1, y1) in PDF pts
        self.page_size: Tuple[float, float] = (0.0, 0.0)  # (width, height) in PDF points
        self.scale_factor: float = 1.0

    def set_page_image(
        self,
        pixmap: QPixmap,
        page_size: Tuple[float, float],
        scale: float,
        highlight_bbox: Optional[Tuple[float, float, float, float]] = None
    ):
        self.current_pixmap = pixmap
        self.page_size = page_size
        self.scale_factor = scale
        self.active_bbox = highlight_bbox
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self.current_pixmap:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Center pixmap
        px_x = (self.width() - self.current_pixmap.width()) // 2
        px_y = (self.height() - self.current_pixmap.height()) // 2
        painter.drawPixmap(px_x, px_y, self.current_pixmap)

        # Draw highlight overlay if bbox is provided
        if self.active_bbox and self.scale_factor > 0:
            x0, y0, x1, y1 = self.active_bbox
            sx0 = px_x + (x0 * self.scale_factor)
            sy0 = px_y + (y0 * self.scale_factor)
            sw = max(10, (x1 - x0) * self.scale_factor)
            sh = max(10, (y1 - y0) * self.scale_factor)

            rect = QRectF(sx0, sy0, sw, sh)

            # Draw glowing highlight fill and border
            fill_color = QColor(239, 68, 68, 55)  # Red translucent
            border_color = QColor(220, 38, 38, 220)  # Solid red

            painter.setBrush(QBrush(fill_color))
            painter.setPen(QPen(border_color, 2.5, Qt.SolidLine))
            painter.drawRoundedRect(rect, 4, 4)

            # Corner pins
            pin_pen = QPen(QColor(185, 28, 28), 3)
            painter.setPen(pin_pen)
            pin_len = min(12.0, sw / 3, sh / 3)
            # Top-left
            painter.drawLine(sx0, sy0, sx0 + pin_len, sy0)
            painter.drawLine(sx0, sy0, sx0, sy0 + pin_len)
            # Top-right
            painter.drawLine(sx0 + sw, sy0, sx0 + sw - pin_len, sy0)
            painter.drawLine(sx0 + sw, sy0, sx0 + sw, sy0 + pin_len)
            # Bottom-left
            painter.drawLine(sx0, sy0 + sh, sx0 + pin_len, sy0 + sh)
            painter.drawLine(sx0, sy0 + sh, sx0, sy0 + sh - pin_len)
            # Bottom-right
            painter.drawLine(sx0 + sw, sy0 + sh, sx0 + sw - pin_len, sy0 + sh)
            painter.drawLine(sx0 + sw, sy0 + sh, sx0 + sw, sy0 + sh - pin_len)

        painter.end()


class PDFCanvas(QWidget):
    """Complete viewer widget containing PAC Visual Locator and Standard Page Canvas."""

    page_changed = Signal(int)
    finding_navigation_requested = Signal(int)  # offset -1 or +1

    def __init__(self, parent=None):
        super().__init__(parent)
        self.doc: Optional[pymupdf.Document] = None
        self.doc_model: Optional[Any] = None
        self.current_filepath: Optional[str] = None
        self.current_page_idx: int = 0  # 0-indexed
        self.zoom: float = 1.25
        self.rotation: int = 0
        self.highlight_bbox: Optional[Tuple[float, float, float, float]] = None
        self.current_finding: Optional[CheckResult] = None

        self._init_ui()


    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 1. Main Viewer Toolbar
        self.toolbar = QToolBar()
        self.toolbar.setStyleSheet("background: #ffffff; border-bottom: 1px solid #e2e8f0; padding: 4px 8px;")

        # View Mode Toggle: [ 📑 PAC Split View ] / [ 📄 Document View ]
        self.btn_mode_pac = QPushButton("📑 PAC Split View")
        self.btn_mode_pac.setCheckable(True)
        self.btn_mode_pac.setChecked(True)
        self.btn_mode_pac.setStyleSheet("font-weight: 600; padding: 4px 10px;")
        self.toolbar.addWidget(self.btn_mode_pac)

        self.btn_mode_doc = QPushButton("📄 Document View")
        self.btn_mode_doc.setCheckable(True)
        self.btn_mode_doc.setStyleSheet("font-weight: 600; padding: 4px 10px;")
        self.toolbar.addWidget(self.btn_mode_doc)

        self.mode_group = QButtonGroup(self)
        self.mode_group.setExclusive(True)
        self.mode_group.addButton(self.btn_mode_pac)
        self.mode_group.addButton(self.btn_mode_doc)
        self.btn_mode_pac.clicked.connect(lambda: self.set_view_mode("pac"))
        self.btn_mode_doc.clicked.connect(lambda: self.set_view_mode("doc"))

        self.toolbar.addSeparator()

        # Navigation
        self.btn_prev = QPushButton("◀ Prev Page")
        self.btn_prev.clicked.connect(self.prev_page)
        self.toolbar.addWidget(self.btn_prev)

        self.page_input = QLineEdit("1")
        self.page_input.setFixedWidth(40)
        self.page_input.setAlignment(Qt.AlignCenter)
        self.page_input.returnPressed.connect(self._on_page_jump)
        self.toolbar.addWidget(self.page_input)

        self.lbl_page_total = QLabel(" / 1 ")
        self.lbl_page_total.setStyleSheet("color: #64748b; font-weight: 500;")
        self.toolbar.addWidget(self.lbl_page_total)

        self.btn_next = QPushButton("Next Page ▶")
        self.btn_next.clicked.connect(self.next_page)
        self.toolbar.addWidget(self.btn_next)

        self.toolbar.addSeparator()

        # Zoom Controls
        self.btn_zoom_out = QPushButton("🔍 -")
        self.btn_zoom_out.clicked.connect(self.zoom_out)
        self.toolbar.addWidget(self.btn_zoom_out)

        self.zoom_combo = QComboBox()
        self.zoom_combo.addItems(["50%", "75%", "100%", "125%", "150%", "200%", "Fit Width", "Fit Page"])
        self.zoom_combo.setCurrentText("125%")
        self.zoom_combo.currentTextChanged.connect(self._on_zoom_combo_changed)
        self.toolbar.addWidget(self.zoom_combo)

        self.btn_zoom_in = QPushButton("🔍 +")
        self.btn_zoom_in.clicked.connect(self.zoom_in)
        self.toolbar.addWidget(self.btn_zoom_in)

        self.toolbar.addSeparator()

        # Rotate
        self.btn_rotate = QPushButton("🔄 Rotate")
        self.btn_rotate.clicked.connect(self.rotate_clockwise)
        self.toolbar.addWidget(self.btn_rotate)

        # Clear Highlight
        self.btn_clear_hl = QPushButton("✖ Clear Highlight")
        self.btn_clear_hl.clicked.connect(self.clear_highlight)
        self.toolbar.addWidget(self.btn_clear_hl)

        layout.addWidget(self.toolbar)

        # 2. Stacked Views (0: PAC Visual Locator, 1: Standard Scrollable Canvas)
        self.stack = QStackedWidget()

        # View 0: PAC Visual Locator
        self.pac_locator = PACVisualLocatorWidget()
        self.pac_locator.full_view_requested.connect(lambda: self.set_view_mode("doc"))
        self.pac_locator.finding_navigation_requested.connect(self.finding_navigation_requested.emit)
        self.stack.addWidget(self.pac_locator)

        # View 1: Standard Scroll Area
        self.scroll_area = QScrollArea()
        self.scroll_area.setStyleSheet("background-color: #525659; border: none;")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setAlignment(Qt.AlignCenter)

        self.page_display = PageDisplayWidget()
        self.scroll_area.setWidget(self.page_display)
        self.stack.addWidget(self.scroll_area)

        layout.addWidget(self.stack, 1)

    def set_view_mode(self, mode: str):
        """Switches between 'pac' and 'doc' view modes."""
        if mode == "pac":
            self.btn_mode_pac.setChecked(True)
            self.stack.setCurrentIndex(0)
            if self.current_finding:
                self.pac_locator.load_finding(
                    self.doc,
                    self.current_finding,
                    page_num=self.current_page_idx + 1,
                    bbox=self.highlight_bbox,
                    doc_model=self.doc_model
                )
            elif self.doc:
                dummy_finding = CheckResult(
                    check_id="NAV",
                    name=f"Page {self.current_page_idx + 1} Inspection",
                    category="Visual Inspection",
                    standard="PDF/UA",
                    status=CheckStatus.PASS,
                    severity=CheckResult.__annotations__.get("severity", None) or "INFO",
                    message=f"Inspect page {self.current_page_idx + 1}",
                    page=self.current_page_idx + 1,
                    bounding_box=self.highlight_bbox
                )
                self.pac_locator.load_finding(self.doc, dummy_finding, self.current_page_idx + 1, self.highlight_bbox, doc_model=self.doc_model)
        else:
            self.btn_mode_doc.setChecked(True)
            self.stack.setCurrentIndex(1)
            self.render_current_page()

    def load_document(self, filepath: str, password: Optional[str] = None, doc_model: Optional[Any] = None):
        """Loads a PDF document into the viewer."""
        if self.doc:
            try:
                self.doc.close()
            except Exception:
                pass

        self.current_filepath = filepath
        self.doc_model = doc_model
        self.doc = pymupdf.open(filepath)
        if self.doc.needs_pass and password:
            self.doc.authenticate(password)

        self.current_page_idx = 0
        self.rotation = 0
        self.highlight_bbox = None
        self.lbl_page_total.setText(f" / {len(self.doc)} ")
        self.render_current_page()

    def render_current_page(self):
        """Renders the current page at the current zoom and rotation."""
        if not self.doc or len(self.doc) == 0:
            return

        page = self.doc[self.current_page_idx]
        mat = pymupdf.Matrix(self.zoom, self.zoom).prerotate(self.rotation)
        pix = page.get_pixmap(matrix=mat, alpha=False)

        # Convert PyMuPDF pixmap to QImage
        img_format = QImage.Format_RGB888
        qimg = QImage(pix.samples, pix.width, pix.height, pix.stride, img_format)
        pixmap = QPixmap.fromImage(qimg)

        rect = page.rect
        self.page_display.set_page_image(
            pixmap=pixmap,
            page_size=(rect.width, rect.height),
            scale=self.zoom,
            highlight_bbox=self.highlight_bbox
        )

        self.page_input.setText(str(self.current_page_idx + 1))
        self.btn_prev.setEnabled(self.current_page_idx > 0)
        self.btn_next.setEnabled(self.current_page_idx < len(self.doc) - 1)
        self.page_changed.emit(self.current_page_idx + 1)

    def go_to_page(
        self,
        page_num_1based: int,
        bbox: Optional[Tuple[float, float, float, float]] = None,
        finding: Optional[CheckResult] = None,
        doc_model: Optional[Any] = None
    ):
        """Navigates to a specific page and displays finding in PAC Visual Locator format."""
        if not self.doc:
            return

        if doc_model:
            self.doc_model = doc_model

        target_idx = max(0, min(len(self.doc) - 1, page_num_1based - 1))
        self.current_page_idx = target_idx
        self.highlight_bbox = bbox
        self.current_finding = finding

        # When a finding is targeted, activate PAC visual locator view
        if finding:
            self.set_view_mode("pac")
            self.pac_locator.load_finding(self.doc, finding, page_num=page_num_1based, bbox=bbox, doc_model=self.doc_model)
        else:
            self.render_current_page()

        # Scroll to highlighted element if in document view
        if bbox and self.stack.currentIndex() == 1:
            y_center = int(((bbox[1] + bbox[3]) / 2) * self.zoom)
            self.scroll_area.verticalScrollBar().setValue(max(0, y_center - 150))

    def show_finding_visual_locator(self, finding: CheckResult, doc_model: Optional[Any] = None):
        """Directly activates PAC visual locator for a given CheckResult."""
        if doc_model:
            self.doc_model = doc_model
        target_page = finding.page or 1
        self.go_to_page(target_page, finding.bounding_box, finding=finding, doc_model=self.doc_model)


    def next_page(self):
        if self.doc and self.current_page_idx < len(self.doc) - 1:
            self.current_page_idx += 1
            self.highlight_bbox = None
            if self.stack.currentIndex() == 0 and self.current_finding:
                self.pac_locator.load_finding(self.doc, self.current_finding, page_num=self.current_page_idx + 1)
            else:
                self.render_current_page()

    def prev_page(self):
        if self.doc and self.current_page_idx > 0:
            self.current_page_idx -= 1
            self.highlight_bbox = None
            if self.stack.currentIndex() == 0 and self.current_finding:
                self.pac_locator.load_finding(self.doc, self.current_finding, page_num=self.current_page_idx + 1)
            else:
                self.render_current_page()

    def _on_page_jump(self):
        try:
            target = int(self.page_input.text().strip())
            self.go_to_page(target)
        except ValueError:
            self.page_input.setText(str(self.current_page_idx + 1))

    def zoom_in(self):
        self.zoom = min(4.0, round(self.zoom + 0.25, 2))
        self.zoom_combo.setCurrentText(f"{int(self.zoom * 100)}%")
        self.render_current_page()

    def zoom_out(self):
        self.zoom = max(0.25, round(self.zoom - 0.25, 2))
        self.zoom_combo.setCurrentText(f"{int(self.zoom * 100)}%")
        self.render_current_page()

    def _on_zoom_combo_changed(self, text: str):
        if not self.doc:
            return
        if text.endswith("%"):
            try:
                self.zoom = float(text.replace("%", "")) / 100.0
                self.render_current_page()
            except ValueError:
                pass
        elif text == "Fit Width":
            viewport_w = self.scroll_area.viewport().width() - 40
            page_w = self.doc[self.current_page_idx].rect.width
            if page_w > 0:
                self.zoom = round(viewport_w / page_w, 2)
                self.render_current_page()
        elif text == "Fit Page":
            viewport_h = self.scroll_area.viewport().height() - 40
            page_h = self.doc[self.current_page_idx].rect.height
            if page_h > 0:
                self.zoom = round(viewport_h / page_h, 2)
                self.render_current_page()

    def rotate_clockwise(self):
        self.rotation = (self.rotation + 90) % 360
        self.render_current_page()

    def clear_highlight(self):
        self.highlight_bbox = None
        self.current_finding = None
        self.render_current_page()

    def close_document(self):
        if self.doc:
            try:
                self.doc.close()
            except Exception:
                pass
            self.doc = None
        self.page_display.set_page_image(QPixmap(), (0, 0), 1.0, None)
