import sys
sys.path.insert(0, ".")
from src.pdf_inspector.core.document_parser import DocumentParser
from src.pdf_inspector.engine.runner import AuditRunner

for name in ['58-78 (2).pdf', 'SF_Chapter 16 202-269.pdf']:
    path = f'C:/Users/HBS/Downloads/{name}'
    doc = DocumentParser(path).parse()
    rep = AuditRunner().run(doc)
    print(f"=== {name} ===")
    for r in rep.results:
        if r.category == "Structure elements":
            print(f"  [{r.status.value}] {r.message} (items={r.items_count})")
