import sys
sys.path.insert(0, ".")
from src.pdf_inspector.core.document_parser import DocumentParser
from collections import Counter

doc = DocumentParser(r'C:\Users\HBS\Downloads\SF_Chapter 16 202-269.pdf').parse()
all_nodes = [n for n in doc.structure_tree.find_all_nodes() if n.tag != "StructTreeRoot"]
print(f"Total nodes: {len(all_nodes)}")

tag_counts = Counter(n.tag for n in all_nodes)
print("Tag counts top 20:")
for tag, count in tag_counts.most_common(20):
    print(f"  {tag:15}: {count}")

print("\nNode inspection:")
no_page = [n for n in all_nodes if not n.page]
print(f"Nodes without page: {len(no_page)}")

no_pg_attr = [n for n in all_nodes if not n.has_pg_attr]
print(f"Nodes without /Pg attr: {len(no_pg_attr)}")

no_content_no_children = [n for n in all_nodes if not n.children and not n.mcids and not n.alt_text and not n.actual_text and not (n.text_content and n.text_content.strip())]
print(f"Nodes with no children and no content: {len(no_content_no_children)}")
for n in no_content_no_children[:10]:
    print(f"  Empty tag: <{n.tag}> page={n.page}")

# Check headings
headings = [(n.standard_tag, n.tag, n.page) for n in all_nodes if n.standard_tag.upper().startswith("H")]
print(f"Headings: {len(headings)}")
for h in headings[:15]:
    print(f"  {h}")

# Check containers
containers = [n for n in all_nodes if n.standard_tag.upper() in ("SECT", "DIV", "PART", "ART", "BLOCKQUOTE")]
print(f"Containers: {len(containers)}")

# Check attributes
attrs_keys = Counter(k for n in all_nodes for k in n.attributes.keys())
print(f"Attributes keys: {attrs_keys}")
