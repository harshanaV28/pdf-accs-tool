"""
Interactive PDF Canvas & Viewer Widget
Renders PDF pages using PyMuPDF and renders illuminated bounding box overlays
for selected accessibility findings.
"""

from typing import Optional, Tuple, List
import pymupdf
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
    QPushButton, QComboBox, QLineEdit, QToolBar, QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QRectF
from PySide6.QtGui import QImage, QPixmap, QPainter, QColor, QPen, QBrush


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
            # PyMuPDF coords: y increases downwards from top-left
            sx0 = px_x + (x0 * self.scale_factor)
            sy0 = px_y + (y0 * self.scale_factor)
            sw = max(10, (x1 - x0) * self.scale_factor)
            sh = max(10, (y1 - y0) * self.scale_factor)

            rect = QRectF(sx0, sy0, sw, sh)

            # Draw glowing highlight fill and border
            fill_color = QColor(239, 68, 68, 60)  # Red translucent
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
    """Complete viewer widget containing toolbar controls and scrollable page canvas."""

    page_changed = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.doc: Optional[pymupdf.Document] = None
        self.current_page_idx: int = 0  # 0-indexed
        self.zoom: float = 1.25
        self.rotation: int = 0
        self.highlight_bbox: Optional[Tuple[float, float, float, float]] = None

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 1. Canvas Toolbar
        self.toolbar = QToolBar()
        self.toolbar.setStyleSheet("background: #ffffff; border-bottom: 1px solid #e2e8f0; padding: 4px 8px;")

        # Navigation
        self.btn_prev = QPushButton("◀ Prev")
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

        self.btn_next = QPushButton("Next ▶")
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

        # 2. Scrollable Canvas
        self.scroll_area = QScrollArea()
        self.scroll_area.setStyleSheet("background-color: #525659; border: none;")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setAlignment(Qt.AlignCenter)

        self.page_display = PageDisplayWidget()
        self.scroll_area.setWidget(self.page_display)
        layout.addWidget(self.scroll_area)

    def load_document(self, filepath: str):
        """Loads a PDF document into the viewer."""
        if self.doc:
            try:
                self.doc.close()
            except Exception:
                pass

        self.doc = pymupdf.open(filepath)
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

    def go_to_page(self, page_num_1based: int, bbox: Optional[Tuple[float, float, float, float]] = None):
        """Navigates to a specific page and optionally highlights a bounding box."""
        if not self.doc:
            return

        target_idx = max(0, min(len(self.doc) - 1, page_num_1based - 1))
        self.current_page_idx = target_idx
        self.highlight_bbox = bbox
        self.render_current_page()

        # Scroll to highlighted element if bbox is present
        if bbox:
            y_center = int(((bbox[1] + bbox[3]) / 2) * self.zoom)
            self.scroll_area.verticalScrollBar().setValue(max(0, y_center - 150))

    def next_page(self):
        if self.doc and self.current_page_idx < len(self.doc) - 1:
            self.current_page_idx += 1
            self.highlight_bbox = None
            self.render_current_page()

    def prev_page(self):
        if self.doc and self.current_page_idx > 0:
            self.current_page_idx -= 1
            self.highlight_bbox = None
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
        self.render_current_page()

    def close_document(self):
        if self.doc:
            try:
                self.doc.close()
            except Exception:
                pass
            self.doc = None
        self.page_display.set_page_image(QPixmap(), (0, 0), 1.0, None)
