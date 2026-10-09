# Standards & Checkpoint Mapping

PDF Accessibility Inspector implements automated checks and manual inspection workflows grounded in international standards and technical accessibility guidelines:
- **PDF/UA-1 (ISO 14289-1:2014)**
- **PDF 1.7 / 2.0 (ISO 32000-1 / ISO 32000-2)**
- **WCAG 2.1 & WCAG 2.2 (Level A & AA)**
- **Matterhorn Protocol 1.1 Checkpoints**

---

## 1. PDF/UA-1 & Matterhorn Protocol 1.1 Mappings

| Rule ID | Category | Matterhorn Checkpoint | ISO 14289-1 Clause | Rule Summary & Evaluation Logic |
|---|---|---|---|---|
| `PDFUA-CONTENT-001` | Content | 01-001 | 7.1 | Catalog `/MarkInfo /Marked` must be true and `/StructTreeRoot` must exist. |
| `PDFUA-CONTENT-002` | Content | 01-002, 01-005 | 7.1 | All real content operations (text `Tj`/`TJ`, paths `S`/`f`/`B`, XObjects `Do`) must be enclosed in marked content sequences (`/MCID`) or marked as `/Artifact`. |
| `PDFUA-ART-003` | Content | 01-003 | 7.1 | Content marked as an Artifact must not be nested inside tagged content sequences. |
| `PDFUA-CONTENT-004` | Content | 01-004 | 7.1 | Tagged content sequences (`/MCID`) must not be nested inside an `/Artifact` marked content block. |
| `PDFUA-CONTENT-005` | Content | 01-005 | 7.1 | Every `/MCID` marked content identifier in page content streams must be referenced by a structure element in the structure tree. |
| `PDFUA-ARTIFACT-001` | Content | 01-001 | 7.1 | `<Artifact>` elements must not exist as structural nodes within the structure tree. |
| `PDFUA-FONT-001` | Fonts | 14-001 | 7.2 | All fonts used for rendering real text must be embedded (fully embedded or valid subset). |
| `PDFUA-FONT-002` | Fonts | 14-002 | 7.2 | All fonts must include a `/ToUnicode` mapping dictionary to map character codes to Unicode. |
| `PDFUA-LANG-001` | Natural language | 12-001 | 7.3 | Primary document language (`/Lang`) must be specified in the document Catalog dictionary. |
| `PDFUA-LANG-002` | Natural language | 12-002 | 7.3 | The `/Lang` string must conform to a valid IETF BCP 47 language tag (e.g. `en-US`, `fr-CA`). |
| `PDFUA-META-001` | Metadata | 06-001 | 7.9 | Catalog dictionary must contain a standard XMP metadata stream (`/Metadata`). |
| `PDFUA-META-002` | Metadata | 06-003 | 7.9 | XMP metadata stream must contain the document title in the Dublin Core namespace (`<dc:title>`). Legacy trailer `/Info /Title` does not satisfy this clause. |
| `PDFUA-META-003` | Metadata | 06-002 | 7.9 | XMP metadata stream must declare PDF/UA conformance (`pdfaProperty` or `pdfuaid:part="1"`). |
| `PDFUA-SETTINGS-001` | Document settings | 07-001 | 7.10 | `/ViewerPreferences` dictionary must specify `/DisplayDocTitle true`. |
| `PDFUA-SETTINGS-003` | Document settings | 21-002 | 7.19 | Documents with more than 20 pages must include bookmarks for document outline navigation. |
| `PDFUA-ANNOT-001` | Annotations | 19-001 | 7.18 | All interactive annotations must be associated with a structure element in the structure tree. |
| `PDFUA-ANNOT-002` | Annotations | 17-001 | 7.18.1 | In tagged documents, each page containing annotations must specify Structure tab order (`/Tabs /S`). |
| `PDFUA-FORM-001` | Forms | 08-001, 08-003 | 7.18 | Interactive form fields must define accessible tooltips (`/TU`) and valid field names (`/T`). |
| `PDFUA-LIST-001` | Structure elements | 28-001, 28-002 | 7.4 | `<L>` must contain `<LI>` (or `<Caption>`), and `<LI>` must contain `<Lbl>` and/or `<LBody>`. |
| `PDFUA-TABLE-001` | Tables | 15-001 | 7.5 | Data tables must include header cells (`<TH>`) and maintain valid `Table` > `TR` > `TH`/`TD` structure. |
| `PDFUA-TREE-001` | Structure tree | 13-001 | 7.1 | Logical structure tree root `/StructTreeRoot` must be present, non-empty, and conform to ISO 32000-1 Clause 14.8.4 parent-child admissibility. |
| `PDFUA-STRUCT-001` | Structure elements | 13-002 | 7.4 | Structural elements must follow standard containment and nesting rules. |
| `PDFUA-STRUCT-002` | Structure elements | 13-005 | 7.1 | Structure elements must not be empty unless serving as structural grouping containers. |
| `PDFUA-FIG-001` | Structure elements | 16-001 | 7.3 | A `<Figure>` structure element appearing entirely on a single page must specify a valid `/BBox` attribute array. |
| `PDFUA-ROLE-001` | Role mapping | 13-003 | 7.4.4 | Custom structure types must be mapped to standard ISO 32000-1 roles in `/RoleMap`. |
| `PDFUA-ROLE-002` | Role mapping | 13-004 | 7.4.4 | `/RoleMap` must not contain circular mappings. |
| `PDFUA-ALT-001` | Alternative Descriptions | 09-001 | 7.3 | All `<Figure>` elements representing non-decorative visuals must provide non-empty `/Alt` text. |

---

## 2. WCAG 2.1 & 2.2 Principles and Success Criteria

| Rule ID | Guideline / SC | Standard | Rule Summary & Evaluation Logic |
|---|---|---|---|
| `WCAG-1.1.1` | SC 1.1.1 Non-text Content | WCAG | Verifies that images and figures provide meaningful alternative text descriptions (`/Alt`). |
| `WCAG-1.2` | Guideline 1.2 Time-based Media | WCAG | Checks for embedded audio, video, or rich media annotations requiring synchronized captions or transcripts. |
| `WCAG-1.3` | SC 1.3.1 Info & Relationships<br>SC 1.3.2 Meaningful Sequence | WCAG | Validates heading tags (`H1`-`H6`), table headers (`TH`), list structures (`L`/`LI`), and reading order sequence. |
| `WCAG-1.4` | SC 1.4.3 Contrast (Minimum)<br>SC 1.4.11 Non-text Contrast | WCAG | Evaluates text luminance against page background colors. |
| `WCAG-2.1` | SC 2.1.1 Keyboard<br>SC 2.1.2 No Keyboard Trap | WCAG | Ensures page tab navigation order is set to `/Tabs /S` (Structure order) for keyboard focus navigation. |
| `WCAG-2.2` | SC 2.2.1 Timing Adjustable | WCAG | Verifies document does not define automated page transition timeouts or unpauseable slide flips. |
| `WCAG-2.3` | SC 2.3.1 Three Flashes or Below | WCAG | Checks for rapid flashing animations or multimedia streams. |
| `WCAG-2.4` | SC 2.4.2 Page Titled<br>SC 2.4.4 Link Purpose<br>SC 2.4.5 Multiple Ways<br>SC 2.4.6 Headings & Labels | WCAG | Validates document title and `/DisplayDocTitle`, heading structure, bookmarks for multi-page documents, and flags ambiguous link text ("click here", "read more"). |
| `WCAG-2.5` | SC 2.5.3 Label in Name | WCAG | Checks that interactive form field labels and tooltips match visible on-screen prompts. |
| `WCAG-3.1` | SC 3.1.1 Language of Page<br>SC 3.1.2 Language of Parts | WCAG | Ensures default document language is declared (`/Lang`) and span-level language changes are tagged. |
| `WCAG-3.2` | SC 3.2.1 On Focus<br>SC 3.2.2 On Input | WCAG | Verifies interactive form fields and controls execute without unannounced submit actions or context jumps. |
| `WCAG-3.3` | SC 3.3.2 Labels or Instructions | WCAG | Verifies interactive form fields provide accessible tooltips/descriptions (`/TU`). |
| `WCAG-4.1` | SC 4.1.2 Name, Role, Value | WCAG | Checks structure tree completeness, accessibility extraction permissions, valid `/RoleMap` resolution without cycles, and tagging of interactive annotations. |

---

## 3. Quality & Ergonomics Checks

| Rule ID | Category | Standard | Rule Summary & Evaluation Logic |
|---|---|---|---|
| `QUAL-HEAD-001` | Heading Structure | Quality | Flags skipped heading levels (e.g. `H1` jumping directly to `H3` or `H4`), missing `H1` main title, or unnumbered headings. |
| `QUAL-STRUCT-001` | Structure Quality | Quality | Identifies empty structural container tags (`Sect`, `Div`, `Part`) and inappropriate nesting patterns. |
| `QUAL-TABLE-001` | Table Quality | Quality | Audits table matrix regularity and flags irregular column/row spans lacking proper attributes. |
| `QUAL-LINK-001` | Link Quality | Quality | Identifies vague link text ("click here", "more info", "details") and bare URL anchor text. |
| `QUAL-SIM-001` | Screen Reader Simulation | Quality | Linearizes the document according to logical structure tree reading order, extracting synthesized text, headings, list markers, and image descriptions. |
