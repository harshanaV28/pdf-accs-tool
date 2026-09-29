# PDF Accessibility Inspector

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Platform: Windows 10/11 64-bit](https://img.shields.io/badge/Platform-Windows%2010%2F11%2064--bit-0078D6.svg)](https://microsoft.com/windows)
[![Standards: PDF/UA & WCAG](https://img.shields.io/badge/Standards-PDF%2FUA%20%7C%20WCAG%202.1%2F2.2-green.svg)](https://www.iso.org/standard/64599.html)

**PDF Accessibility Inspector** is an independent, professional Windows desktop application engineered for deep structural auditing, interactive tag tree inspection, visual element highlighting, and comprehensive compliance reporting for PDF accessibility against **PDF/UA-1 (ISO 14289-1)**, **ISO 32000-1**, and **WCAG 2.1 / 2.2 Level AA**.

The application runs as a standalone native desktop executable:
```
dist/PDF-Accessibility-Inspector.exe
```
No Python, Node.js, command line, or external runtimes are required.

---

## Key Features

### 1. Dual-Engine Deep PDF Structural Inspection
- Combines `pikepdf` (QPDF C++ core) for low-level PDF dictionary, catalog, and StructTree analysis with `PyMuPDF` (MuPDF C core) for fast rendering, text flow analysis, and visual coordinate mapping.
- Validates `/StructTreeRoot`, `/ParentTree`, Marked Content IDs (`MCID`), `/RoleMap` custom roles, font embedding, `/ToUnicode` CMaps, `/ViewerPreferences`, and XMP metadata.

### 2. Comprehensive Compliance Rule Engine
- **PDF/UA-1 Checkpoint Suite**: PDF Syntax, Fonts, Content, Embedded Files, Natural Language, Structure Elements, Structure Tree, Role Mapping, Alternative Descriptions, Metadata, and Document Settings.
- **WCAG Checkpoint Suite**: Guidelines 1.1 through 4.1 (1.1 Text Alternatives, 1.3 Adaptable, 1.4 Distinguishable, 2.1 Keyboard, 2.4 Navigable, 3.1 Readable, 4.1 Compatible, etc.).
- **Quality & Ergonomics Engine**: Heading skipped levels, table header symmetry, ambiguous link labels, reading order anomalies.
- **AI & Heuristic Intelligence**: Alt text quality heuristics (flags placeholders or file names like "image01.jpg"), readability scores, and actionable authoring remediation advice.

### 3. Integrated PDF Viewer with Issue Highlighting
- Visual page viewer with zoom (Fit Page, Fit Width, 25% - 400%), page navigation, search, and page rotation.
- **Click-to-Highlight**: Clicking any finding in the results list automatically jumps to the affected page and renders an illuminated bounding box over the exact offending PDF element.

### 4. Interactive Tag Tree Explorer
- Hierarchical interactive tree view of the PDF's structural elements (`/StructTreeRoot` down to content items).
- Inspects attributes, standard role mappings, title, language, and alternate text for every tag.

### 5. Simulated Screen Reader Preview
- Linearizes the document according to the logical structure tree.
- Renders an assistive technology reading view showing how screen readers (JAWS, NVDA, VoiceOver) speak headings, lists, tables, and alternative descriptions.

### 6. Publication-Grade Reporting
- **PDF Audit Report**: Generates a professional, print-ready PDF audit certificate and detailed breakdown using ReportLab.
- **HTML Report**: Standalone, interactive HTML report with filtering and graphs.
- **JSON / CSV Export**: Full machine-readable export for enterprise CI/CD workflows and archiving.

---

## Application Interface Layout

```
+-------------------------------------------------------------------------------+
| Top Bar: Open PDF | Open Folder | Batch Scan | Rescan | Export | Settings     |
+-------------------------------------------------------------------------------+
| Sidebar       | Center Canvas                       | Right Inspector Panel   |
| ------------- | ----------------------------------- | ----------------------- |
| - Dashboard   | [PDF/UA] [WCAG] [Quality] [AI]      | Finding Details:        |
| - Checkpoints | ----------------------------------- | Rule ID: PDFUA-ALT-001  |
| - Tag Tree    | Checkpoint        Passed Warn  Fail | Status:  FAIL           |
| - Reader View | Natural language     1    0     0   | Severity: HIGH          |
| - Document    | Alternative Descr.   4    1     2   | Standard: PDF/UA        |
| - Statistics  | Structure Elements  12    0     0   | Page:     3             |
| - Elements:   | ----------------------------------- | Evidence:               |
|   * Fonts     | [Real PDF Viewer / Canvas Area]     | /Figure has no /Alt key |
|   * Images    | (Rendered page with bounding boxes) | Remediation:            |
|   * Tables    |                                     | Add alternate text in   |
|   * Links     |                                     | Word/InDesign/Acrobat   |
|   * Forms     |                                     | [Highlight on Page]     |
+---------------+-------------------------------------+-------------------------+
| Bottom Toolbar: [Results in detail] [PDF report] [Tree View] [Stats] [Preview]|
+-------------------------------------------------------------------------------+
```

---

## Installation & Running from Source

```powershell
# Clone or navigate to directory
cd "pdf checking tool"

# Install dependencies
pip install -r requirements.txt

# Run application
python -m src.pdf_inspector.app
```

---

## Building the Windows Executable

```powershell
python scripts/build_exe.py
```
This produces `dist/PDF-Accessibility-Inspector.exe`.
