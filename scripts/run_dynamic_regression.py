"""
Dynamic 20-PDF Accessibility Engine Regression Evaluator
Computes all statistics and comparisons dynamically from test_corpus/PAC_Results_Filled_v2.xlsx
and the actual PDF files with zero hardcoded values or PDF-specific branching.
"""

import os
import sys
import json
import datetime
import zipfile
import xml.etree.ElementTree as ET
from collections import defaultdict

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
from pdf_inspector.core.document_parser import DocumentParser
from pdf_inspector.engine.runner import AuditRunner
from pdf_inspector.core.models import CheckStatus


def load_excel_reference(xlsx_path: str):
    """Dynamically parses Excel reference rows without external dependencies."""
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

    ref_by_pdf = defaultdict(list)
    for r in rows[1:]:
        if len(r) >= 5 and r[0]:
            pdf_id = r[0].strip()
            page = r[1].strip()
            category = r[2].strip()
            check_name = r[3].strip()
            pac_result = r[4].strip()
            pac_message = r[5].strip() if len(r) > 5 else ''
            severity = r[6].strip() if len(r) > 6 else ''
            notes = r[7].strip() if len(r) > 7 else ''
            ref_by_pdf[pdf_id].append({
                'pdf_id': pdf_id,
                'page': page,
                'category': category,
                'check_name': check_name,
                'status': pac_result,
                'message': pac_message,
                'severity': severity,
                'notes': notes
            })
    return ref_by_pdf


def run_regression():
    ref_all = load_excel_reference('test_corpus/PAC_Results_Filled_v2.xlsx')
    runner = AuditRunner()

    corpus_dir = 'test_corpus/ALL FILES'
    pdf_files = sorted([f for f in os.listdir(corpus_dir) if f.lower().endswith('.pdf')])

    per_pdf = {}
    total_ref_records = 0
    total_engine_findings = 0
    total_engine_item_checks = 0

    for pdf_file in pdf_files:
        pdf_key = os.path.splitext(pdf_file)[0]
        full_path = os.path.join(corpus_dir, pdf_file)
        
        doc = DocumentParser(full_path).parse()
        report = runner.run(doc)
        
        ref_list = ref_all.get(pdf_key, [])
        ref_pass = sum(1 for r in ref_list if r['status'] == 'PASS')
        ref_fail = sum(1 for r in ref_list if r['status'] == 'FAIL')
        ref_warn = sum(1 for r in ref_list if r['status'] == 'WARNING')
        ref_info = sum(1 for r in ref_list if r['status'] in ('INFO', 'MANUAL REVIEW'))
        
        ref_font_records = [r for r in ref_list if r['category'] == 'Fonts' and r['check_name'] == 'Font Embedding']
        ref_font_pass = sum(1 for r in ref_font_records if r['status'] == 'PASS')
        ref_font_fail = sum(1 for r in ref_font_records if r['status'] == 'FAIL')
        ref_font_warn = sum(1 for r in ref_font_records if r['status'] == 'WARNING')
        ref_font_info = sum(1 for r in ref_font_records if r['status'] in ('INFO', 'MANUAL REVIEW'))
        
        engine_font_records = [r for r in report.results if r.check_id == 'PDFUA-FONT-001']
        engine_font_pass = sum(1 for r in engine_font_records if r.status == CheckStatus.PASS)
        engine_font_fail = sum(1 for r in engine_font_records if r.status in (CheckStatus.FAIL, CheckStatus.ERROR))
        engine_font_warn = sum(1 for r in engine_font_records if r.status == CheckStatus.WARNING)
        engine_font_info = sum(1 for r in engine_font_records if r.status == CheckStatus.MANUAL_REVIEW)

        if ref_font_fail == engine_font_fail and ref_font_warn == engine_font_warn:
            font_match_status = 'MATCH'
        elif engine_font_fail > ref_font_fail and ref_font_fail > 0:
            font_match_status = 'ENGINE_FOUND_ADDITIONAL_OCCURRENCES'
        elif engine_font_fail < ref_font_fail:
            font_match_status = 'ENGINE_MISSED_FAILURES'
        elif ref_font_pass > 0 and engine_font_fail > 0:
            font_match_status = 'STATUS_DISAGREEMENT'
        else:
            font_match_status = 'EVALUATION_DIFFERENCE'

        cat_counts = report.get_category_counts('PDF/UA')
        for std in ['WCAG', 'Quality', 'AI']:
            std_counts = report.get_category_counts(std)
            for cat, c_dict in std_counts.items():
                if cat not in cat_counts:
                    cat_counts[cat] = c_dict
                else:
                    for k, v in c_dict.items():
                        cat_counts[cat][k] += v

        findings_pass = sum(1 for r in report.results if r.status == CheckStatus.PASS)
        findings_fail = sum(1 for r in report.results if r.status in (CheckStatus.FAIL, CheckStatus.ERROR))
        findings_warn = sum(1 for r in report.results if r.status == CheckStatus.WARNING)
        
        total_ref_records += len(ref_list)
        total_engine_findings += report.total_findings_count
        total_engine_item_checks += report.total_checks

        per_pdf[pdf_key] = {
            'page_count': doc.page_count,
            'fonts_count': len(doc.fonts),
            'is_tagged': doc.is_tagged,
            'reference': {
                'total': len(ref_list),
                'passed': ref_pass,
                'failed': ref_fail,
                'warned': ref_warn,
                'info': ref_info
            },
            'reference_font_embedding': {
                'total': len(ref_font_records),
                'passed': ref_font_pass,
                'failed': ref_font_fail,
                'warned': ref_font_warn,
                'info': ref_font_info
            },
            'engine_font_embedding': {
                'total_records': len(engine_font_records),
                'passed': engine_font_pass,
                'failed': engine_font_fail,
                'warned': engine_font_warn,
                'info': engine_font_info,
                'match_status': font_match_status
            },
            'engine_findings': {
                'total': report.total_findings_count,
                'passed': findings_pass,
                'failed': findings_fail,
                'warned': findings_warn
            },
            'engine_item_checks': {
                'total': report.total_checks,
                'passed': report.total_passed,
                'failed': report.total_failed,
                'warned': report.total_warned
            },
            'compliance_score': report.compliance_score,
            'categories': cat_counts
        }

    output_data = {
        'timestamp': datetime.datetime.now().isoformat(),
        'total_reference_records': total_ref_records,
        'total_engine_findings': total_engine_findings,
        'total_engine_item_checks': total_engine_item_checks,
        'per_pdf': per_pdf
    }

    os.makedirs('REPORT', exist_ok=True)
    with open('REPORT/regression_results.json', 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2)

    md_lines = []
    md_lines.append('# 20-PDF Accessibility Engine Regression Report (Phase 3)')
    md_lines.append('')
    md_lines.append(f'- **Evaluation Timestamp**: {output_data["timestamp"]}')
    md_lines.append(f'- **Total Reference Records (Oracle)**: {total_ref_records}')
    md_lines.append(f'- **Total Engine Findings (Issues/CheckResults)**: {total_engine_findings}')
    md_lines.append(f'- **Total Engine Evaluated Checks (Item Checks)**: {total_engine_item_checks}')
    md_lines.append('')
    md_lines.append('## 1. Overall Summary Comparison across all 20 PDFs')
    md_lines.append('')
    md_lines.append('| PDF | Pages | Tagged | Ref Total | Ref Pass | Ref Fail | Ref Warn/Info | Engine Findings (P/F/W) | Engine Item Checks (P/F/W) | Score |')
    md_lines.append('|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|')

    for pdf_key, info in sorted(per_pdf.items()):
        p_cnt = info['page_count']
        tagged = 'Yes' if info['is_tagged'] else 'No'
        ref = info['reference']
        ef = info['engine_findings']
        ec = info['engine_item_checks']
        score = f"{info['compliance_score']} %"
        md_lines.append(f'| {pdf_key} | {p_cnt} | {tagged} | {ref["total"]} | {ref["passed"]} | {ref["failed"]} | {ref["warned"] + ref["info"]} | {ef["passed"]}/{ef["failed"]}/{ef["warned"]} | {ec["passed"]}/{ec["failed"]}/{ec["warned"]} | {score} |')

    md_lines.append('')
    md_lines.append('## 2. Dynamic Font Embedding Evaluation Comparison')
    md_lines.append('')
    md_lines.append('| PDF | Total Fonts | Ref Font Rows (Oracle) | Ref Fails | Engine Font Records | Engine Fails | Dynamic Match Status |')
    md_lines.append('|:---|:---:|:---:|:---:|:---:|:---:|:---:|')

    for pdf_key, info in sorted(per_pdf.items()):
        f_cnt = info['fonts_count']
        rf = info['reference_font_embedding']
        ef = info['engine_font_embedding']
        md_lines.append(f'| {pdf_key} | {f_cnt} | {rf["total"]} | {rf["failed"]} | {ef["total_records"]} | {ef["failed"]} | {ef["match_status"]} |')

    with open('REPORT/regression_results.md', 'w', encoding='utf-8') as f:
        f.write('\n'.join(md_lines))

    print('Successfully generated dynamic regression results!')


if __name__ == '__main__':
    run_regression()
