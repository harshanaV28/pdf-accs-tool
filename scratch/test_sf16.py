import sys
sys.path.insert(0, ".")
from src.pdf_inspector.core.document_parser import DocumentParser
from src.pdf_inspector.engine.runner import AuditRunner

doc = DocumentParser(r'C:\Users\HBS\Downloads\SF_Chapter 16 202-269.pdf').parse()
runner = AuditRunner()
report = runner.run(doc)
pdfua = report.get_category_counts('PDF/UA')
print('=== PDF/UA CHECKPOINT COUNTS ===')
for cat, counts in pdfua.items():
    p = counts.get('passed', 0)
    w = counts.get('warned', 0)
    f = counts.get('failed', 0)
    print(f'{cat:25}: Passed={p:6} | Warned={w:6} | Failed={f:6}')

print('\n=== STRUCTURE TREE FINDINGS ===')
for r in report.results:
    if r.category == 'Structure tree':
        print(f'[{r.status.value}] {r.message} (items={r.items_count})')
