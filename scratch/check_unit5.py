import sys
sys.path.insert(0, ".")
from src.pdf_inspector.core.document_parser import DocumentParser
from src.pdf_inspector.engine.runner import AuditRunner

path = r'C:\Users\HBS\Downloads\322206_Impact2e_AmE_L1_AnswerKeys_WB_Unit_5 (1).pdf'
doc = DocumentParser(path).parse()
all_nodes = [n for n in doc.structure_tree.find_all_nodes() if n.tag != "StructTreeRoot"]
print(f"Total nodes: {len(all_nodes)}")

rep = AuditRunner().run(doc)
counts = rep.get_category_counts('PDF/UA')
for cat, c in counts.items():
    if "Structure" in cat:
        print(f"{cat}: Passed={c.get('passed',0)}, Warned={c.get('warned',0)}, Failed={c.get('failed',0)}")

for r in rep.results:
    if "Structure" in r.category and r.status.value != "PASS":
        print(f"[{r.category}] [{r.status.value}] {r.message}")
