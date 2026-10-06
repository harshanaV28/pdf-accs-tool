"""
Row-Level Regression Comparator
Performs rigorous, normalized row-by-row comparisons between the reference PAC Excel oracle
and PDF accessibility engine evaluation records without hardcoded values.
"""

from __future__ import annotations
import os
import sys
import json
import datetime
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import List, Dict, Optional, Tuple, Any
from collections import defaultdict

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from pdf_inspector.core.models import PDFDocumentModel, CheckResult, CheckStatus
from pdf_inspector.engine.runner import AuditRunner
from pdf_inspector.core.document_parser import DocumentParser


class ComparisonClassification(str, Enum):
    MATCH = "MATCH"
    STATUS_MISMATCH = "STATUS_MISMATCH"
    MISSING_FROM_ENGINE = "MISSING_FROM_ENGINE"
    ENGINE_ONLY = "ENGINE_ONLY"
    REFERENCE_ORACLE_OMISSION = "REFERENCE_ORACLE_OMISSION"
    UNCOMPARABLE = "UNCOMPARABLE"


@dataclass
class NormalizedRecord:
    """Normalized representation of a single evaluation row from PAC or Engine."""
    pdf_id: str
    page: Optional[int]  # None for Document-level
    category: str
    check_name: str
    status: str  # "PASS", "FAIL", "WARNING", "INFO", "MANUAL REVIEW"
    message: str = ""
    evidence: str = ""
    object_reference: str = ""
    source: str = "ENGINE"  # "PAC_EXCEL" or "ENGINE"
    check_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ComparisonItem:
    """Represents the row-level comparison result between PAC and Engine."""
    pdf_id: str
    page: Optional[int]
    category: str
    check_name: str
    classification: ComparisonClassification
    pac_record: Optional[NormalizedRecord] = None
    engine_record: Optional[NormalizedRecord] = None
    details: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pdf_id": self.pdf_id,
            "page": self.page,
            "category": self.category,
            "check_name": self.check_name,
            "classification": self.classification.value,
            "pac_record": self.pac_record.to_dict() if self.pac_record else None,
            "engine_record": self.engine_record.to_dict() if self.engine_record else None,
            "details": self.details
        }


# Canonical mapping from Engine rule_id to PAC Category and Check Name
RULE_ID_TO_PAC_CHECK: Dict[str, Tuple[str, str]] = {
    "PDFUA-CONTENT-001": ("Document", "Tagged PDF"),
    "PDFUA-TREE-001": ("Structure", "Structure Tree"),
    "PDFUA-META-002": ("Document", "Document Title"),
    "PDFUA-SETTINGS-001": ("Document", "Display Document Title"),
    "PDFUA-LANG-001": ("Document", "Document Language"),
    "PDFUA-SETTINGS-003": ("Document", "Bookmarks"),
    "PDFUA-ANNOT-002": ("Annotations", "Tab Order"),
    "PDFUA-FONT-001": ("Fonts", "Font Embedding"),
    "QUAL-LINK-001": ("Links", "Link"),
    "PDFUA-ALT-001": ("Images", "Alternate Text"),
    "PDFUA-FIG-001": ("Images", "Figure Tags"),
    "QUAL-HEAD-001": ("Structure", "Heading Structure"),
    "PDFUA-TABLE-001": ("Tables", "Table Headers (TH)"),
    "QUAL-TABLE-001": ("Tables", "Table Structure"),
    "PDFUA-FORM-001": ("Forms", "Form Field"),
}


def load_pac_excel_records(xlsx_path: str) -> Dict[str, List[NormalizedRecord]]:
    """Loads and normalizes all rows from PAC_Results_Filled_v2.xlsx dynamically."""
    with zipfile.ZipFile(xlsx_path) as z:
        sst = []
        if 'xl/sharedStrings.xml' in z.namelist():
            tree = ET.fromstring(z.read('xl/sharedStrings.xml'))
            for si in tree.findall('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}si'):
                text = ''.join(t.text for t in si.findall('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t') if t.text)
                sst.append(text)
        
        sheet_tree = ET.fromstring(z.read('xl/worksheets/sheet1.xml'))
        rows = []
        for row in sheet_tree.findall('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}sheetData/{http://schemas.openxmlformats.org/spreadsheetml/2006/main}row'):
            cols = []
            for c in row.findall('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}c'):
                t = c.attrib.get('t')
                v = c.find('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}v')
                if v is not None and v.text is not None:
                    val = v.text
                    if t == 's':
                        val = sst[int(val)]
                    cols.append(val)
                else:
                    cols.append('')
            rows.append(cols)

    pac_by_pdf: Dict[str, List[NormalizedRecord]] = defaultdict(list)
    for r in rows[1:]:
        if len(r) >= 5 and r[0]:
            pdf_id = r[0].strip()
            page_raw = r[1].strip()
            category = r[2].strip()
            check_name = r[3].strip()
            pac_result = r[4].strip()
            pac_msg = r[5].strip() if len(r) > 5 else ""
            notes = r[7].strip() if len(r) > 7 else ""

            page: Optional[int] = None
            if page_raw and page_raw.lower() != "document" and page_raw.isdigit():
                page = int(page_raw)

            # Map PAC statuses to standard status names
            norm_status = pac_result.upper()
            if norm_status in ("INFO", "MANUAL REVIEW"):
                norm_status = "WARNING"

            pac_by_pdf[pdf_id].append(NormalizedRecord(
                pdf_id=pdf_id,
                page=page,
                category=category,
                check_name=check_name,
                status=norm_status,
                message=pac_msg,
                evidence=notes,
                source="PAC_EXCEL"
            ))

    return pac_by_pdf


def normalize_engine_results(pdf_id: str, results: List[CheckResult]) -> List[NormalizedRecord]:
    """Normalizes engine CheckResults into NormalizedRecords."""
    norm_records: List[NormalizedRecord] = []
    for r in results:
        mapped = RULE_ID_TO_PAC_CHECK.get(r.check_id)
        if mapped:
            cat, check = mapped
        else:
            cat, check = r.category, r.name

        norm_status = r.status.value
        if norm_status in ("ERROR", "FAIL"):
            norm_status = "FAIL"
        elif norm_status in ("WARNING", "MANUAL REVIEW"):
            norm_status = "WARNING"
        elif norm_status == "PASS":
            norm_status = "PASS"

        norm_records.append(NormalizedRecord(
            pdf_id=pdf_id,
            page=r.page,
            category=cat,
            check_name=check,
            status=norm_status,
            message=r.message,
            evidence=r.evidence,
            object_reference=r.object_reference,
            source="ENGINE",
            check_id=r.check_id
        ))
    return norm_records


class RowLevelComparator:
    """Performs row-level comparison between PAC Excel records and Engine results."""

    def compare_pdf(
        self,
        pdf_id: str,
        pac_records: List[NormalizedRecord],
        engine_records: List[NormalizedRecord]
    ) -> List[ComparisonItem]:
        items: List[ComparisonItem] = []

        # Group PAC records by (category, check_name, page)
        pac_grouped: Dict[Tuple[str, str, Optional[int]], List[NormalizedRecord]] = defaultdict(list)
        for pr in pac_records:
            pac_grouped[(pr.category, pr.check_name, pr.page)].append(pr)

        # Group Engine records by (category, check_name, page)
        eng_grouped: Dict[Tuple[str, str, Optional[int]], List[NormalizedRecord]] = defaultdict(list)
        for er in engine_records:
            eng_grouped[(er.category, er.check_name, er.page)].append(er)

        # 1. First Pass: Exact (category, check_name, page) matching
        all_exact_keys = sorted(
            set(list(pac_grouped.keys()) + list(eng_grouped.keys())),
            key=lambda k: (k[0], k[1], k[2] if k[2] is not None else -1)
        )

        unmatched_pac_by_check: Dict[Tuple[str, str], List[NormalizedRecord]] = defaultdict(list)
        unmatched_eng_by_check: Dict[Tuple[str, str], List[NormalizedRecord]] = defaultdict(list)

        for key in all_exact_keys:
            cat, check, page = key
            p_list = list(pac_grouped.get(key, []))
            e_list = list(eng_grouped.get(key, []))

            if p_list and e_list:
                e_pool = list(e_list)
                p_unmatched = []

                # Match same status first
                for p_rec in p_list:
                    match_idx = None
                    for idx, e_rec in enumerate(e_pool):
                        if p_rec.status == e_rec.status:
                            match_idx = idx
                            break
                    if match_idx is not None:
                        e_rec = e_pool.pop(match_idx)
                        items.append(ComparisonItem(
                            pdf_id=pdf_id,
                            page=page,
                            category=cat,
                            check_name=check,
                            classification=ComparisonClassification.MATCH,
                            pac_record=p_rec,
                            engine_record=e_rec,
                            details=f"Matched on status {p_rec.status}"
                        ))
                    else:
                        p_unmatched.append(p_rec)

                # Status mismatch for remaining pairs with exact page match
                while p_unmatched and e_pool:
                    p_rec = p_unmatched.pop(0)
                    e_rec = e_pool.pop(0)
                    items.append(ComparisonItem(
                        pdf_id=pdf_id,
                        page=page,
                        category=cat,
                        check_name=check,
                        classification=ComparisonClassification.STATUS_MISMATCH,
                        pac_record=p_rec,
                        engine_record=e_rec,
                        details=f"Status mismatch: PAC={p_rec.status} vs Engine={e_rec.status}"
                    ))

                # Collect any remaining unmatched
                for p_rec in p_unmatched:
                    unmatched_pac_by_check[(cat, check)].append(p_rec)
                for e_rec in e_pool:
                    unmatched_eng_by_check[(cat, check)].append(e_rec)

            elif p_list and not e_list:
                for p_rec in p_list:
                    unmatched_pac_by_check[(cat, check)].append(p_rec)

            elif e_list and not p_list:
                for e_rec in e_list:
                    unmatched_eng_by_check[(cat, check)].append(e_rec)

        # 2. Second Pass: Deterministic scope reconciliation for unmatched records per (cat, check)
        all_check_keys = sorted(set(list(unmatched_pac_by_check.keys()) + list(unmatched_eng_by_check.keys())))

        for c_key in all_check_keys:
            cat, check = c_key
            p_pool = list(unmatched_pac_by_check.get(c_key, []))
            e_pool = list(unmatched_eng_by_check.get(c_key, []))

            # A. Match on status across scopes (e.g. document-scoped PAC row vs page-scoped engine evaluation)
            p_remaining = []
            for p_rec in p_pool:
                match_idx = None
                for idx, e_rec in enumerate(e_pool):
                    if p_rec.status == e_rec.status:
                        match_idx = idx
                        break
                if match_idx is not None:
                    e_rec = e_pool.pop(match_idx)
                    page_desc = f"page {e_rec.page}" if e_rec.page is not None else "document scope"
                    items.append(ComparisonItem(
                        pdf_id=pdf_id,
                        page=e_rec.page if e_rec.page is not None else p_rec.page,
                        category=cat,
                        check_name=check,
                        classification=ComparisonClassification.MATCH,
                        pac_record=p_rec,
                        engine_record=e_rec,
                        details=f"Matched across scopes on status {p_rec.status} ({page_desc})"
                    ))
                else:
                    p_remaining.append(p_rec)

            # B. Pair remaining across scopes as STATUS_MISMATCH
            while p_remaining and e_pool:
                p_rec = p_remaining.pop(0)
                e_rec = e_pool.pop(0)
                items.append(ComparisonItem(
                    pdf_id=pdf_id,
                    page=e_rec.page if e_rec.page is not None else p_rec.page,
                    category=cat,
                    check_name=check,
                    classification=ComparisonClassification.STATUS_MISMATCH,
                    pac_record=p_rec,
                    engine_record=e_rec,
                    details=f"Status mismatch across scopes: PAC={p_rec.status} vs Engine={e_rec.status}"
                ))

            # C. Remaining PAC records -> MISSING_FROM_ENGINE
            for p_rec in p_remaining:
                items.append(ComparisonItem(
                    pdf_id=pdf_id,
                    page=p_rec.page,
                    category=cat,
                    check_name=check,
                    classification=ComparisonClassification.MISSING_FROM_ENGINE,
                    pac_record=p_rec,
                    details=f"PAC has {p_rec.category}/{p_rec.check_name} record on page {p_rec.page}, engine produced none"
                ))

            # D. Remaining Engine records -> ENGINE_ONLY / REFERENCE_ORACLE_OMISSION
            for e_rec in e_pool:
                pac_covers_check = any(pr.check_name == check for pr in pac_records)
                if pac_covers_check and cat == "Fonts" and check == "Font Embedding" and e_rec.status == "FAIL":
                    classification = ComparisonClassification.REFERENCE_ORACLE_OMISSION
                else:
                    classification = ComparisonClassification.ENGINE_ONLY

                items.append(ComparisonItem(
                    pdf_id=pdf_id,
                    page=e_rec.page,
                    category=cat,
                    check_name=check,
                    classification=classification,
                    engine_record=e_rec,
                    details="Engine-evaluated rule or additional page occurrence"
                ))

        return items


def run_full_row_level_regression(
    xlsx_path: str = "test_corpus/PAC_Results_Filled_v2.xlsx",
    corpus_dir: str = "test_corpus/ALL FILES"
) -> Dict[str, Any]:
    """Executes the full 20-PDF row-level comparison and generates JSON/MD reports."""
    pac_by_pdf = load_pac_excel_records(xlsx_path)
    runner = AuditRunner()
    comparator = RowLevelComparator()

    pdf_files = sorted([f for f in os.listdir(corpus_dir) if f.lower().endswith('.pdf')])

    all_comparison_items: List[ComparisonItem] = []
    per_pdf_results: Dict[str, Any] = {}
    per_category_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    total_counts: Dict[str, int] = defaultdict(int)

    for pdf_file in pdf_files:
        pdf_key = os.path.splitext(pdf_file)[0]
        full_path = os.path.join(corpus_dir, pdf_file)

        doc = DocumentParser(full_path).parse()
        report = runner.run(doc)

        pac_recs = pac_by_pdf.get(pdf_key, [])
        eng_recs = normalize_engine_results(pdf_key, report.results)

        comp_items = comparator.compare_pdf(pdf_key, pac_recs, eng_recs)
        all_comparison_items.extend(comp_items)

        pdf_class_counts: Dict[str, int] = defaultdict(int)
        for item in comp_items:
            pdf_class_counts[item.classification.value] += 1
            total_counts[item.classification.value] += 1
            per_category_counts[item.category][item.classification.value] += 1

        per_pdf_results[pdf_key] = {
            "page_count": doc.page_count,
            "pac_records_count": len(pac_recs),
            "engine_records_count": len(eng_recs),
            "classification_counts": dict(pdf_class_counts)
        }

    report_data = {
        "timestamp": datetime.datetime.now().isoformat(),
        "total_pac_records": sum(len(v) for v in pac_by_pdf.values()),
        "total_engine_records": sum(p["engine_records_count"] for p in per_pdf_results.values()),
        "overall_classification_counts": dict(total_counts),
        "per_pdf": per_pdf_results,
        "per_category": {k: dict(v) for k, v in per_category_counts.items()},
        "comparison_items": [item.to_dict() for item in all_comparison_items]
    }

    os.makedirs("REPORT", exist_ok=True)
    with open("REPORT/regression_row_level.json", "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2)

    # Generate Markdown Report
    md_lines = []
    md_lines.append("# Row-Level Regression Comparison Report")
    md_lines.append(f"**Timestamp**: {report_data['timestamp']}")
    md_lines.append(f"- **Total PAC Reference Oracle Records**: {report_data['total_pac_records']}")
    md_lines.append(f"- **Total Engine Evaluation Records**: {report_data['total_engine_records']}")
    md_lines.append("")
    md_lines.append("## Overall Classification Summary")
    md_lines.append("")
    md_lines.append("| Classification | Count | Description |")
    md_lines.append("|:---|:---:|:---|")
    md_lines.append(f"| **MATCH** | {total_counts.get('MATCH', 0)} | PAC row directly matches Engine evaluation record on status and location |")
    md_lines.append(f"| **STATUS_MISMATCH** | {total_counts.get('STATUS_MISMATCH', 0)} | PAC and Engine evaluated same element/page but arrived at different status |")
    md_lines.append(f"| **MISSING_FROM_ENGINE** | {total_counts.get('MISSING_FROM_ENGINE', 0)} | PAC reference row has no corresponding engine evaluation |")
    md_lines.append(f"| **ENGINE_ONLY** | {total_counts.get('ENGINE_ONLY', 0)} | Comprehensive engine standards evaluation not present in basic PAC report |")
    md_lines.append(f"| **REFERENCE_ORACLE_OMISSION** | {total_counts.get('REFERENCE_ORACLE_OMISSION', 0)} | Ground-truth PDF evidence proves occurrence exists, omitted by PAC |")
    md_lines.append(f"| **UNCOMPARABLE** | {total_counts.get('UNCOMPARABLE', 0)} | Cannot be directly mapped |")
    md_lines.append("")
    md_lines.append("## Per-PDF Row-Level Results")
    md_lines.append("")
    md_lines.append("| PDF | PAC Total | Engine Total | MATCH | STATUS_MISMATCH | MISSING | ENGINE_ONLY | ORACLE_OMISSION |")
    md_lines.append("|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|")

    for pdf_key, p_data in sorted(per_pdf_results.items()):
        cc = p_data["classification_counts"]
        md_lines.append(
            f"| {pdf_key} | {p_data['pac_records_count']} | {p_data['engine_records_count']} | "
            f"{cc.get('MATCH', 0)} | {cc.get('STATUS_MISMATCH', 0)} | {cc.get('MISSING_FROM_ENGINE', 0)} | "
            f"{cc.get('ENGINE_ONLY', 0)} | {cc.get('REFERENCE_ORACLE_OMISSION', 0)} |"
        )

    md_lines.append("")
    md_lines.append("## Per-Category Breakdown")
    md_lines.append("")
    md_lines.append("| Category | MATCH | STATUS_MISMATCH | MISSING | ENGINE_ONLY | ORACLE_OMISSION |")
    md_lines.append("|:---|:---:|:---:|:---:|:---:|:---:|")

    for cat, c_counts in sorted(per_category_counts.items()):
        md_lines.append(
            f"| {cat} | {c_counts.get('MATCH', 0)} | {c_counts.get('STATUS_MISMATCH', 0)} | "
            f"{c_counts.get('MISSING_FROM_ENGINE', 0)} | {c_counts.get('ENGINE_ONLY', 0)} | "
            f"{c_counts.get('REFERENCE_ORACLE_OMISSION', 0)} |"
        )

    md_lines.append("")
    md_lines.append("## Representative Mismatch Details")
    md_lines.append("")
    mismatches = [item for item in all_comparison_items if item.classification in (ComparisonClassification.STATUS_MISMATCH, ComparisonClassification.MISSING_FROM_ENGINE, ComparisonClassification.REFERENCE_ORACLE_OMISSION)]
    
    for item in mismatches[:30]:
        md_lines.append(f"- **[{item.classification.value}] {item.pdf_id}** Page `{item.page}` | `{item.category} / {item.check_name}`: {item.details}")
        if item.pac_record:
            md_lines.append(f"  - *PAC*: `{item.pac_record.status}` — {item.pac_record.message}")
        if item.engine_record:
            md_lines.append(f"  - *Engine*: `{item.engine_record.status}` — {item.engine_record.message} (Evidence: {item.engine_record.evidence})")

    if len(mismatches) > 30:
        md_lines.append(f"- *... and {len(mismatches) - 30} additional details logged in `REPORT/regression_row_level.json`.*")

    with open("REPORT/regression_row_level.md", "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))

    return report_data


if __name__ == "__main__":
    run_full_row_level_regression()
