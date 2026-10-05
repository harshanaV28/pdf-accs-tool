import pymupdf
import re

doc = pymupdf.open(r"C:\Users\HBS\Downloads\Work_Documentation_Administrative_Fillable_1_accessible.pdf")

for xref in [1435, 1390, 1400, 1410]:
    try:
        s = doc.xref_stream(xref).decode("latin1", errors="ignore")
        arts = len(re.findall(r"/Artifact\s*(?:<<.*?>>)?\s*B[DM]C", s, re.DOTALL))
        dos = re.findall(r"/(\w+)\s+Do", s)
        print(f"xref {xref}: len={len(s)}, artifacts={arts}, Do={dos}")
    except Exception as e:
        print(f"xref {xref} err: {e}")
