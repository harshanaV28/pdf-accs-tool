import sys
sys.path.insert(0, ".")
from src.pdf_inspector.core.document_parser import DocumentParser
from src.pdf_inspector.engine.runner import AuditRunner

doc = DocumentParser(r'C:\Users\HBS\Downloads\miller-cacs1e-ch02.02_updated (1).pdf').parse()
rep = AuditRunner().run(doc)
counts = rep.get_category_counts('PDF/UA')

print('=== AUDIT RESULTS FOR miller-cacs1e-ch02.02_updated (1).pdf ===')
for cat in ['Structure tree', 'Structure elements', 'Role mapping', 'Fonts', 'Metadata', 'Document settings']:
    c = counts.get(cat, {})
    p = c.get('passed', 0)
    w = c.get('warned', 0)
    f = c.get('failed', 0)
    print(f"{cat:22}: Passed={p:4} | Warned={w:3} | Failed={f:3}")
