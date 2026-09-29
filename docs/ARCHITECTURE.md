# PDF Accessibility Inspector - Architecture & Design

## 1. System Overview
**PDF Accessibility Inspector** is an independent, enterprise-grade Windows desktop application engineered for comprehensive validation, inspection, and remediation guidance of PDF documents against:
- **PDF/UA-1 (ISO 14289-1:2014)**
- **PDF 1.7 / 2.0 Syntax (ISO 32000-1 / ISO 32000-2)**
- **WCAG 2.1 & WCAG 2.2 (Level A & AA)**
- **Matterhorn Protocol 1.1 Checkpoints**

The application provides a deep, native inspection engine built in Python and Qt (PySide6), leveraging low-level PDF structural parsing via `pikepdf` (QPDF C++ backend) and high-fidelity rendering, visual highlighting, and text extraction via `pymupdf` (MuPDF C backend).

---

## 2. High-Level Architecture Pipeline

```
┌────────────────────────────────────────────────────────────────────────┐
│                        User Interface (PySide6)                        │
│ ┌────────────┐ ┌───────────────┐ ┌───────────────┐ ┌─────────────────┐ │
│ │ Top Ribbon │ │ Left Sidebar  │ │ Center Canvas │ │  Right Details  │ │
│ │  Controls  │ │  Navigation   │ │ (Viewer/Grid) │ │ Finding Inspector│ │
│ └────────────┘ └───────────────┘ └───────────────┘ └─────────────────┘ │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Events & Selections
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        Controller & State Bus                          │
│          - Document State, Audit State, View State, Highlights         │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Triggers
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                       PDF Inspection Pipeline                          │
│                                                                        │
│   PDF File (Local / Drag & Drop)                                       │
│      │                                                                 │
│      ▼                                                                 │
│   [DocumentParser] (pikepdf + pymupdf)                                 │
│      ├── Syntax & Header validation                                    │
│      ├── Low-level Catalog, Pages, ViewerPreferences, MarkInfo         │
│      ├── Structure Tree Builder (StructTreeRoot, ParentTree, MCID)     │
│      ├── RoleMap & Standard Types Resolver                             │
│      ├── Font Extractor (Embedded, Subsets, ToUnicode CMaps)           │
│      ├── Image & Figure Extractor (Alt text, Bounding boxes, Artifacts)│
│      ├── Table Grid & Header Hierarchy Builder (TR, TH, TD, Scope)     │
│      ├── Form & Annotations Extractor (TU / Tooltips, Tab Order)       │
│      └── Bookmarks & Link Destinations Extractor                       │
│      │                                                                 │
│      ▼                                                                 │
│   [PDFDocumentModel] (Unified In-Memory Document Model)                │
│      │                                                                 │
│      ▼                                                                 │
│   [Rule Engine & Check Runner]                                         │
│      ├── PDF/UA Checkpoint Suite (ISO 14289-1)                         │
│      ├── WCAG Checkpoint Suite (WCAG 2.1 / 2.2 AA)                     │
│      ├── Quality & Ergo Heuristics (Headings, Tables, Contrast)        │
│      ├── AI & Heuristic Intelligence (Alt Quality, Readability, Repair)│
│      └── Manual Review Categorizer                                     │
│      │                                                                 │
│      ▼                                                                 │
│   [AuditReport]                                                        │
│      ├── Summary & Compliance Scores (PDF/UA, WCAG, Quality)           │
│      ├── Checkpoint Aggregations (Passed, Warned, Failed, Manual)      │
│      └── Detailed CheckResults with Bounding Boxes & Remediation       │
│                                                                        │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Export
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                         Report Generators                              │
│   ├── Publication PDF Audit Report (ReportLab)                         │
│   ├── Interactive Standalone HTML Report                               │
│   └── Machine-Readable JSON / CSV Data Export                          │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Data Models

### 3.1 CheckResult
Every individual rule execution produces a standardized `CheckResult`:
- `check_id` (str): e.g., `PDFUA-01-001`, `WCAG-1.1.1-01`, `QUAL-HEAD-02`
- `name` (str): Human-readable short checkpoint title
- `category` (str): Checkpoint category (e.g., `Natural language`, `Structure Elements`, `1.1 Text Alternatives`)
- `standard` (str): `PDF/UA`, `WCAG`, `Quality`, or `AI`
- `status` (CheckStatus): `PASS`, `FAIL`, `WARNING`, `MANUAL_REVIEW`, `NOT_APPLICABLE`, `ERROR`
- `severity` (Severity): `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`, `INFO`
- `message` (str): One-line summary of findings
- `description` (str): Detailed context on standard requirement
- `evidence` (str): Exact technical PDF dictionary keys, object numbers, or extracted content
- `page` (int | None): 1-based page number where issue occurs (or None if document-wide)
- `bounding_box` (tuple | None): `(x0, y0, x1, y1)` in PDF user points for visual overlay
- `object_reference` (str): e.g., `Object #42 (StructElem /Figure)`
- `remediation` (str): Actionable step-by-step instructions for fixing in authoring tools (Word, InDesign, Acrobat Pro)
- `confidence` (float): 0.0 - 1.0 (1.0 for deterministic machine checks)
- `machine_testable` (bool): True if machine validated; False if flagged for manual review

---

## 4. PDF Structure & Tag Tree Engine

### 4.1 Role Mapping
PDF/UA requires all custom structure tags to be mapped in `/RoleMap` to standard structure types defined in ISO 32000-1 (Section 14.8.4):
- Grouping: `Document`, `Part`, `Art`, `Sect`, `Div`, `BlockQuote`, `Caption`, `TOC`, `TOCI`, `Index`, `NonStruct`, `Private`
- Paragraph-like: `P`, `H`, `H1`, `H2`, `H3`, `H4`, `H5`, `H6`
- List: `L`, `LI`, `Lbl`, `LBody`
- Table: `Table`, `TR`, `TH`, `TD`
- Inline: `Span`, `Quote`, `Note`, `Reference`, `BibEntry`, `Code`, `Link`, `Annot`
- Illustration: `Figure`, `Formula`, `Form`

The engine resolves every tag through the document's `/RoleMap` dictionary recursively to determine its effective standard role. Circular mappings and unmapped custom tags are flagged as violations.

### 4.2 ParentTree and Marked Content ID (MCID)
The engine cross-references structural elements (`/StructElem`) with page content streams using:
- The `/ParentTree` number tree in `/StructTreeRoot`
- Marked Content sequences with `/MCID` tags in the page stream
- Object references (`/OBJR`) for Annotations and Form Fields

---

## 5. Security & Isolation
- Completely runs locally on the user's workstation.
- Never sends PDF content or metadata to external networks.
- Safe parsing via pikepdf and PyMuPDF handles corrupt and malformed documents gracefully without crashing the UI.
