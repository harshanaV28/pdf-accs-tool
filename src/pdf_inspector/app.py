"""
PDF Accessibility Inspector - Main Application Entry Point
"""

import sys
import os
import time
import tempfile
import traceback

# Ensure sys.path contains necessary parent roots for both direct execution and frozen packaging
_current_dir = os.path.dirname(os.path.abspath(__file__))
_src_dir = os.path.dirname(_current_dir)
_root_dir = os.path.dirname(_src_dir)
for _p in (_root_dir, _src_dir):
    if _p and _p not in sys.path:
        sys.path.insert(0, _p)

# Safe stream setup for Windows GUI mode where stdout/stderr may be None
class _SafeStream:
    def write(self, data):
        pass
    def flush(self):
        pass

if sys.stdout is None:
    sys.stdout = _SafeStream()
if sys.stderr is None:
    sys.stderr = _SafeStream()


def run_packaged_verification() -> int:
    """
    Runs a complete self-verification test suite from within the packaged executable.
    Executes actual PDF generation, parsing, rule evaluation (41 rules), and report generation.
    All operations are guarded with error handling and logging.
    """
    log_path = os.path.join(tempfile.gettempdir(), "pdf_inspector_verification.log")

    def _log(msg: str):
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(msg + "\n")
        except Exception:
            pass
        try:
            if sys.stdout and not isinstance(sys.stdout, _SafeStream):
                sys.stdout.write(msg + "\n")
                sys.stdout.flush()
        except Exception:
            pass

    _log("=== EXECUTABLE SELF-VERIFICATION SUITE ===")
    t_start = time.perf_counter()

    try:
        try:
            from .core.document_parser import DocumentParser
            from .engine.runner import AuditRunner
            from .reporting.pdf_report import PDFReportGenerator
            from .reporting.html_report import HTMLReportGenerator
            from .reporting.json_exporter import JSONExporter, CSVExporter
        except (ImportError, ValueError):
            from pdf_inspector.core.document_parser import DocumentParser
            from pdf_inspector.engine.runner import AuditRunner
            from pdf_inspector.reporting.pdf_report import PDFReportGenerator
            from pdf_inspector.reporting.html_report import HTMLReportGenerator
            from pdf_inspector.reporting.json_exporter import JSONExporter, CSVExporter

        import pymupdf
        import pikepdf

        _log("1. Standalone Runtime: OK")
        _log(f"2. Executable Binary: {sys.executable}")

        td = tempfile.mkdtemp()
        sample_pdf = os.path.join(td, "verify_doc.pdf")
        
        t0 = time.perf_counter()
        doc = pymupdf.open()
        p = doc.new_page(width=612, height=792)
        p.insert_text((50, 80), "Self-Verification Document Title", fontsize=16)
        p.insert_text((50, 110), "Standard paragraph text for accessibility verification.")
        doc.save(sample_pdf)
        doc.close()

        with pikepdf.open(sample_pdf, allow_overwriting_input=True) as pike:
            pike.Root["/MarkInfo"] = pikepdf.Dictionary({"/Marked": True})
            pike.Root["/Lang"] = pikepdf.String("en-US")
            pike.Root["/ViewerPreferences"] = pikepdf.Dictionary({"/DisplayDocTitle": True})
            h1 = pikepdf.Dictionary({"/Type": pikepdf.Name("/StructElem"), "/S": pikepdf.Name("/H1"), "/Pg": pike.pages[0].objgen})
            p_elem = pikepdf.Dictionary({"/Type": pikepdf.Name("/StructElem"), "/S": pikepdf.Name("/P"), "/Pg": pike.pages[0].objgen})
            pt = pikepdf.Dictionary({"/Nums": pikepdf.Array([pikepdf.Integer(0), pikepdf.Array([h1, p_elem])])})
            sr = pikepdf.Dictionary({
                "/Type": pikepdf.Name("/StructTreeRoot"),
                "/K": pikepdf.Array([h1, p_elem]),
                "/ParentTree": pike.make_indirect(pt),
                "/ParentTreeNextKey": pikepdf.Integer(1)
            })
            pike.Root["/StructTreeRoot"] = pike.make_indirect(sr)
            pike.pages[0]["/StructParents"] = pikepdf.Integer(0)
            pike.save(sample_pdf)

        t_synth = time.perf_counter() - t0
        _log(f"3. PDF Generation & Tagging: OK ({t_synth:.3f}s)")

        # Test parser
        t0 = time.perf_counter()
        parser = DocumentParser(sample_pdf)
        doc_model = parser.parse()
        t_parse = time.perf_counter() - t0
        _log(f"4. Real PDF Parser: OK (Tagged: {doc_model.is_tagged}, Pages: {doc_model.page_count}, Time: {t_parse:.3f}s)")
        assert doc_model.is_tagged is True, "Document must be detected as tagged"

        # Test runner across 41 rules
        t0 = time.perf_counter()
        runner = AuditRunner()
        report = runner.run(doc_model)
        t_rules = time.perf_counter() - t0
        _log(f"5. Rule Engine: OK ({len(report.results)} rules evaluated | Score: {report.compliance_score}% | Time: {t_rules:.3f}s)")
        assert len(report.results) >= 41, f"Expected >= 41 rules, got {len(report.results)}"

        # Test reports
        t0 = time.perf_counter()
        pdf_out = os.path.join(td, "report.pdf")
        html_out = os.path.join(td, "report.html")
        json_out = os.path.join(td, "report.json")
        csv_out = os.path.join(td, "report.csv")

        PDFReportGenerator.generate(report, pdf_out)
        HTMLReportGenerator.generate(report, html_out)
        JSONExporter.export(report, json_out)
        CSVExporter.export(report, csv_out)
        t_reports = time.perf_counter() - t0

        assert os.path.exists(pdf_out) and os.path.getsize(pdf_out) > 1000, "PDF report generation failed"
        assert os.path.exists(html_out) and os.path.getsize(html_out) > 1000, "HTML report generation failed"
        assert os.path.exists(json_out) and os.path.getsize(json_out) > 500, "JSON export failed"
        assert os.path.exists(csv_out) and os.path.getsize(csv_out) > 200, "CSV export failed"

        _log(f"6. Report Exporters: OK (PDF: {os.path.getsize(pdf_out)}B, HTML: {os.path.getsize(html_out)}B, JSON: {os.path.getsize(json_out)}B, CSV: {os.path.getsize(csv_out)}B | Time: {t_reports:.3f}s)")
        
        t_total = time.perf_counter() - t_start
        _log(f"=== ALL PACKAGED EXECUTABLE CHECKS PASSED in {t_total:.2f}s ===")
        return 0

    except Exception as e:
        _log(f"[ERROR] Executable self-verification failed: {e}")
        _log(traceback.format_exc())
        return 1


def main():
    if "--verify" in sys.argv or "--test" in sys.argv:
        ret = run_packaged_verification()
        sys.exit(ret)

    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QIcon

    try:
        from .ui.main_window import MainWindow
    except (ImportError, ValueError):
        from pdf_inspector.ui.main_window import MainWindow

    # High-DPI support
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("PDF Accessibility Inspector")
    app.setOrganizationName("PDF Accessibility Inspector")
    app.setApplicationVersion("1.0.0")

    # Set icon if exists
    icon_path = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "icons", "app_icon.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    window = MainWindow()
    window.show()

    # Open file passed via command line argument (e.g. drag onto exe or Open With)
    if len(sys.argv) > 1 and not sys.argv[1].startswith("--"):
        initial_file = sys.argv[1]
        if os.path.exists(initial_file) and initial_file.lower().endswith(".pdf"):
            window.load_pdf_file(initial_file)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
