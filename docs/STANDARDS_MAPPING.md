# Standards & Checkpoint Mapping

PDF Accessibility Inspector implements automated checks and manual inspection workflows based on international standards and established technical guidelines.

---

## 1. PDF/UA-1 (ISO 14289-1:2014) & Matterhorn Protocol 1.1

The application maps its rules directly into the 11 functional categories:

| Checkpoint Category | Standards Clause | Automated Checks |
|---|---|---|
| **PDF Syntax (ISO 32000-1)** | ISO 32000-1, Clause 7.5 | Catalog structure, linear xref validity, valid EOF marker, encryption permissions for assistive technology |
| **Fonts** | ISO 14289-1, Clause 7.2 | Font embedding (all glyphs embedded or subsetted), `/ToUnicode` CMaps presence for glyph-to-Unicode mapping |
| **Content** | ISO 14289-1, Clause 7.1 | Tagged PDF flag (`/Marked true`), all real content enclosed in tagged structure or marked as `/Artifact` |
| **Embedded Files** | ISO 14289-1, Clause 7.8 | Embedded files have description and conform to accessibility requirements |
| **Natural language** | ISO 14289-1, Clause 7.3 | Document default language defined (`/Lang`), valid IETF BCP 47 language code, span-level language tags |
| **Structure Elements** | ISO 14289-1, Clause 7.4 | Proper tag nesting (e.g. `L` > `LI` > `Lbl`/`LBody`, `Table` > `TR` > `TH`/`TD`), empty structure elements |
| **Structure tree** | ISO 14289-1, Clause 7.1 | `/StructTreeRoot` validity, single root `Document` element, no cyclic structure relationships, ParentTree integrity |
| **Role mapping** | ISO 14289-1, Clause 7.4.4 | Custom structure types mapped via `/RoleMap` to standard ISO 32000-1 types, circular mapping detection |
| **Alternative Descriptions** | ISO 14289-1, Clause 7.18 | `/Figure` and `/Formula` elements have non-empty `/Alt` or `/ActualText`, no meaningless filenames as alt text |
| **Metadata** | ISO 14289-1, Clause 7.9 | XMP metadata stream present, document Title in Dublin Core (`dc:title`), PDF/UA identifier (`pdfuaid:part=1`) |
| **Document settings** | ISO 14289-1, Clause 7.10 | `/ViewerPreferences` has `DisplayDocTitle` set to `true`, tab order set to `/Tabs /S` (Structure order) |

---

## 2. WCAG 2.1 & 2.2 Principles and Guidelines

The application validates the 13 WCAG Guidelines:

| Guideline | WCAG SC | Automated & Heuristic Checks |
|---|---|---|
| **1.1 Text Alternatives** | 1.1.1 Non-text Content | Missing `/Alt` on Figures, empty alt text, formula alt descriptions, decorative image artifact verification |
| **1.2 Time-based Media** | 1.2.1 - 1.2.3 Audio/Video | Identification of embedded multimedia annotations, rich media screen reader compatibility |
| **1.3 Adaptable** | 1.3.1 Info & Relationships<br>1.3.2 Meaningful Sequence | Structure tags, headings (H1-H6), table headers (TH, scope), list hierarchies, reading order sequence |
| **1.4 Distinguishable** | 1.4.1 Use of Color<br>1.4.3 Contrast (Min)<br>1.4.11 Non-text Contrast | Heuristic text-to-background luminance contrast analysis, color dependency flags |
| **2.1 Keyboard Accessible** | 2.1.1 Keyboard<br>2.1.2 No Keyboard Trap | Form fields keyboard focusable, link annotations accessible, tab order conforms to structure tree |
| **2.2 Enough Time** | 2.2.1 Timing Adjustable | Document timeouts or automated page flips in presentations |
| **2.3 Seizures & Reactions**| 2.3.1 Three Flashes | Animated content checks in multimedia streams |
| **2.4 Navigable** | 2.4.2 Page Titled<br>2.4.4 Link Purpose<br>2.4.6 Headings & Labels | Window title displays document title (`DisplayDocTitle true`), meaningful link labels (flags bare URLs or 'click here') |
| **2.5 Input Modalities** | 2.5.3 Label in Name | Accessible form field labels match visible text prompts |
| **3.1 Readable** | 3.1.1 Language of Page<br>3.1.2 Language of Parts | Document `/Lang` present and valid; language changes tagged with `/Lang` attribute on structure elements |
| **3.2 Predictable** | 3.2.1 On Focus<br>3.2.2 On Input | Form field action triggers don't unexpectedly jump focus or submit without warning |
| **3.3 Input Assistance** | 3.3.2 Labels or Instructions | Form controls have descriptive `/TU` (tooltips/accessible names), required field indicators |
| **4.1 Compatible** | 4.1.2 Name, Role, Value | Proper semantic tagging of interactive controls, links, tables, and document structures |

---

## 3. Quality & Ergonomics Checks
In addition to formal pass/fail requirements, the inspector evaluates authoring quality:
- **Heading Hierarchy**: Detects skipped levels (e.g. H1 followed directly by H3 or H4), multiple H1 headings, or documents lacking an H1.
- **Table Structure Quality**: Validates that data tables have at least one header row or column, detects merged cells without proper `ColSpan`/`RowSpan`, flags empty data cells.
- **Link Clarity**: Identifies ambiguous link text ("read more", "click here", "details", "link", raw URLs).
- **Simulated Screen Reader Output**: Linearizes the document according to logical reading order and provides a transcript of how screen readers pronounce tags, headings, tables, and images.
