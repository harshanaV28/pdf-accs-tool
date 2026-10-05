import sys
sys.path.insert(0, ".")
from src.pdf_inspector.core.document_parser import DocumentParser
from src.pdf_inspector.engine.runner import AuditRunner

for name in ['58-78 (2).pdf', 'SF_Chapter 16 202-269.pdf']:
    path = f'C:/Users/HBS/Downloads/{name}'
    doc = DocumentParser(path).parse()
    rep = AuditRunner().run(doc)
    counts = rep.get_category_counts('PDF/UA')
    st = counts.get('Structure tree', {})
    se = counts.get('Structure elements', {})
    print(f'=== {name} ===')
    print(f'  Structure tree    : Passed={st.get("passed",0)}, Warned={st.get("warned",0)}, Failed={st.get("failed",0)}')
    print(f'  Structure elements: Passed={se.get("passed",0)}, Warned={se.get("warned",0)}, Failed={se.get("failed",0)}')
