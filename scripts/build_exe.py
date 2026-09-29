"""
PyInstaller Release Build Script
Builds the standalone release executable: dist/PDF-Accessibility-Inspector.exe
"""

import sys
import os
import subprocess
import shutil


def build():
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    sys.path.insert(0, root_dir)
    os.chdir(root_dir)

    print("=== Step 1: Generating application icons ===")
    from scripts.generate_app_icon import generate_icons
    generate_icons(os.path.join(root_dir, "assets", "icons"))

    icon_ico = os.path.join(root_dir, "assets", "icons", "app_icon.ico")
    main_script = os.path.join(root_dir, "src", "pdf_inspector", "app.py")

    print("=== Step 2: Running PyInstaller ===")
    # Format data paths for PyInstaller (source;dest on Windows)
    theme_data = f"{os.path.join(root_dir, 'assets', 'styles', 'theme.qss')};assets/styles"
    icon_data = f"{os.path.join(root_dir, 'assets', 'icons', 'app_icon.png')};assets/icons"

    pyinstaller_cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--windowed",
        "--name", "PDF-Accessibility-Inspector",
        "--icon", icon_ico,
        "--add-data", theme_data,
        "--add-data", icon_data,
        "--hidden-import", "pymupdf",
        "--hidden-import", "fitz",
        "--hidden-import", "pikepdf",
        "--hidden-import", "reportlab",
        "--hidden-import", "reportlab.platypus",
        "--hidden-import", "reportlab.lib",
        "--hidden-import", "reportlab.lib.styles",
        "--hidden-import", "reportlab.lib.colors",
        "--hidden-import", "reportlab.lib.pagesizes",
        "--hidden-import", "PIL",
        "--hidden-import", "PySide6.QtCore",
        "--hidden-import", "PySide6.QtGui",
        "--hidden-import", "PySide6.QtWidgets",
        "--hidden-import", "src.pdf_inspector.engine.pdf_ua",
        "--hidden-import", "src.pdf_inspector.engine.wcag",
        "--hidden-import", "src.pdf_inspector.engine.quality",
        "--hidden-import", "src.pdf_inspector.engine.ai_heuristics",
        "--hidden-import", "src.pdf_inspector.reporting.pdf_report",
        "--hidden-import", "src.pdf_inspector.reporting.html_report",
        "--hidden-import", "src.pdf_inspector.reporting.json_exporter",
        "--hidden-import", "src.pdf_inspector.ui.views.batch_view",
        "--hidden-import", "src.pdf_inspector.ui.views.checkpoints_view",
        "--hidden-import", "src.pdf_inspector.ui.views.detailed_results_view",
        "--hidden-import", "src.pdf_inspector.ui.views.dashboard_view",
        "--hidden-import", "src.pdf_inspector.ui.views.elements_view",
        "--hidden-import", "src.pdf_inspector.ui.views.metadata_view",
        "--hidden-import", "src.pdf_inspector.ui.views.screen_reader_view",
        "--hidden-import", "src.pdf_inspector.ui.views.statistics_view",
        "--hidden-import", "src.pdf_inspector.ui.views.tag_tree_view",
        main_script
    ]

    print("Executing command:\n", " ".join(pyinstaller_cmd))
    res = subprocess.run(pyinstaller_cmd)

    if res.returncode != 0:
        print(f"PyInstaller build failed with exit code {res.returncode}")
        sys.exit(res.returncode)

    exe_path = os.path.join(root_dir, "dist", "PDF-Accessibility-Inspector.exe")
    if os.path.exists(exe_path):
        size_mb = round(os.path.getsize(exe_path) / (1024 * 1024), 2)
        print("============================================================")
        print(f"BUILD SUCCESSFUL!")
        print(f"Deliverable: {exe_path} ({size_mb} MB)")
        print("============================================================")

        # Generate dist/README.txt
        readme_path = os.path.join(root_dir, "dist", "README.txt")
        readme_content = """================================================================================
PDF ACCESSIBILITY INSPECTOR (Windows x64)
Version 1.0.0
================================================================================

1. OVERVIEW
--------------------------------------------------------------------------------
PDF Accessibility Inspector is an independent, professional Windows desktop 
application engineered to audit and inspect the accessibility of PDF documents 
according to:
  * ISO 14289-1:2014 (PDF/UA-1)
  * ISO 32000-1 (PDF 1.7) / ISO 32000-2 (PDF 2.0)
  * W3C Web Content Accessibility Guidelines (WCAG 2.1 / 2.2 AA)
  * Matterhorn Protocol 1.1

The application operates completely offline with zero cloud API dependencies.
No Python installation, runtime environment, or terminal is required.

2. HOW TO RUN
--------------------------------------------------------------------------------
* Graphical Launch:
    Double-click PDF-Accessibility-Inspector.exe to start the application.

* Command-Line / Scripted Launch:
    PDF-Accessibility-Inspector.exe [path_to_pdf_file]
    Example:
    PDF-Accessibility-Inspector.exe "C:\\Documents\\AnnualReport.pdf"

* Drag & Drop:
    Drag any PDF file directly into the application window to audit it.

3. CORE FEATURES & CAPABILITIES
--------------------------------------------------------------------------------
* Checkpoints View:
    Tabbed PAC-style inspection matrix (PDF/UA, WCAG, Quality, AI) with Pass,
    Warning, and Failure metrics per category.

* Interactive Tag Tree:
    Full logical structure tree traversal (/StructTreeRoot) showing tags, 
    role maps, attributes, and direct page bounding box links.

* Screen Reader Preview:
    Reconstructs the linear acoustic reading stream voiced by assistive 
    technologies based on document structure and tag hierarchy.

* Interactive PDF Viewer:
    High-DPI page rendering with zoom (25%-400%), page navigation, and glowing
    bounding-box overlays highlighting non-compliant elements on the page.

* Dedicated Element Inspectors:
    * Fonts: Subtype, embedding, subset, ToUnicode CMaps, encoding, page usage.
    * Images: Dimensions, colorspace, alt text presence, artifact status.
    * Tables: Row/column counts, header cell presence (<TH>), matrix symmetry.
    * Links: Target URIs, structural tagging, alt text, ambiguous phrase check.
    * Forms: Field names, types, accessible tooltips (/TU), required flags.
    * Bookmarks: Outline hierarchy, heading levels, and target page resolution.

* Batch PDF Scanning:
    Scan entire folders of PDFs concurrently in the background, displaying
    aggregate compliance scores and double-click document opening.

* Multi-Format Report Export:
    * PDF Report: Multi-page formal audit certificate via ReportLab.
    * HTML Report: Responsive, standalone report with interactive filters.
    * JSON Export: Complete machine-readable audit data with metadata.
    * CSV Export: Spreadsheet-ready findings table with UTF-8 BOM.

4. AUTOMATED RULES INVENTORY (41 RULES)
--------------------------------------------------------------------------------
* PDF/UA-1 Suite (22 Rules):
    Syntax, Tagged PDF, StructTreeRoot, ParentTree, StructParents, Role Mapping,
    Font Embedding, ToUnicode, Unicode PUA, Replacement Characters, Heading
    Hierarchy, Lists (L>LI>Lbl/LBody), Tables (TH headers), Empty Elements,
    Artifacts, Annotations, Alt Text, Language, DisplayDocTitle, Metadata.

* WCAG 2.1/2.2 AA Suite (13 Rules):
    Text Alternatives (1.1.1), Info & Relationships (1.3.1), Contrast (1.4.3),
    Keyboard Tab Order (2.1.1), Navigable/Headings (2.4.1), Focus Order (2.4.3),
    Link Purpose (2.4.4), Page Titled (2.4.2), Language of Page (3.1.1),
    Input Assistance/Tooltips (3.3.2), Compatible Name/Role (4.1.2).

* Quality & Ergonomics Suite (3 Rules):
    Heading level skipped jumps, Table matrix regularity, Meaningful link text.

* AI & Heuristics Suite (3 Rules):
    Semantic alt-text evaluation, Flesch Reading Ease cognitive readability,
    Structural outline navigation consistency.

5. KNOWN LIMITATIONS & HONEST BOUNDARIES
--------------------------------------------------------------------------------
* Password-Protected PDFs:
    If a document requires a password to open, the application prompts:
    "Password required — analysis cannot continue until the document is unlocked."
    You may enter the password in the secure prompt to analyze the document.
    Brute-forcing or bypassing PDF encryption is intentionally not supported.

* Flattened / Rasterized Text Contrast:
    When text has been flattened into a pixel bitmap without vector glyph paths,
    color contrast cannot be mathematically verified and is designated as
    MANUAL REVIEW with inspection guidance.

* Audio / Video Synchronization:
    Rich media annotations containing multimedia tracks require human review
    to confirm caption accuracy and audio description timing.

================================================================================
"""
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(readme_content.strip() + "\n")
        print(f"Generated: {readme_path}")
    else:
        print("ERROR: Output executable not found in dist/")
        sys.exit(1)


if __name__ == "__main__":
    build()
