import sys
import os
sys.path.insert(0, ".")
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

# Ensure off-screen / headless platform
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from src.pdf_inspector.ui.main_window import MainWindow
from src.pdf_inspector.core.document_parser import DocumentParser
from src.pdf_inspector.engine.runner import AuditRunner

def test_ui():
    app = QApplication.instance() or QApplication(sys.argv)
    window = MainWindow()
    window.resize(960, 600)
    window.show()

    # 1. Check sidebar size is preserved and >= 200
    sizes = window.main_splitter.sizes()
    print("Splitter sizes on 960x600 window:", sizes)
    assert sizes[0] >= 200, f"Sidebar too small: {sizes[0]}"

    # 2. Check table column sizes in CheckpointsView
    tbl = window.checkpoints_view.table_pdf_ua
    print("Column widths in PDF/UA table:", [tbl.columnWidth(i) for i in range(4)])
    assert tbl.columnWidth(1) == 68
    assert tbl.columnWidth(2) == 68
    assert tbl.columnWidth(3) == 68

    # 3. Load sample document
    doc = DocumentParser("test_samples/accessible_sample.pdf").parse()
    runner = AuditRunner()
    report = runner.run(doc)

    window._on_audit_finished(doc, report)

    # 4. Check that right panel is automatically populated (not "No finding selected")
    print("Finding Details Title after audit:", window.right_panel.title_label.text())
    print("Finding Details Checkpoint name:", window.right_panel.name_label.text())
    assert window.right_panel.name_label.text() != "No finding selected"

    # 5. Simulate clicking a category row
    window.checkpoints_view.table_pdf_ua._on_row_click(1, 0)
    print("After clicking row 1 (Fonts):", window.right_panel.name_label.text())
    assert "Fonts" in window.right_panel.name_label.text() or "Fonts" in window.right_panel.title_label.text()

    print("ALL UI FIX VERIFICATIONS PASSED!")

if __name__ == "__main__":
    test_ui()
