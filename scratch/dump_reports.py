import pymupdf
import sys

def inspect_pdf(path, outfile):
    with open(outfile, "w", encoding="utf-8") as out:
        out.write(f"=== {path} ===\n")
        doc = pymupdf.open(path)
        out.write(f"Pages: {len(doc)}\n")
        for i, page in enumerate(doc):
            text = page.get_text()
            out.write(f"\n--- PAGE {i+1} ---\n")
            out.write(text)

inspect_pdf("REPORT/SF_Chapter 16 202-269_PAC_UA_Report.pdf", "scratch/pac_report.txt")
inspect_pdf("REPORT/SF_Chapter 16 202-269_accessibility_report.pdf", "scratch/our_report.txt")
print("Dumped reports to scratch/")
