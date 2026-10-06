"""
Sample PDF Generator for Accessibility Testing
Creates both fully compliant (PDF/UA + WCAG) and non-compliant test PDFs
to rigorously test the PDF Accessibility Inspector audit engine.
"""

import os
import pymupdf
import pikepdf
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from PIL import Image as PILImage


def generate_samples(output_dir: str):
    os.makedirs(output_dir, exist_ok=True)

    # 1. Create a dummy test image
    img_path = os.path.join(output_dir, "test_chart.png")
    img = PILImage.new("RGB", (300, 150), color=(59, 130, 246))
    img.save(img_path)

    # Register TrueType fonts so they are embedded
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    if os.path.exists("C:/Windows/Fonts/arial.ttf"):
        pdfmetrics.registerFont(TTFont("Arial", "C:/Windows/Fonts/arial.ttf"))
        pdfmetrics.registerFont(TTFont("Arial-Bold", "C:/Windows/Fonts/arialbd.ttf"))
        font_name = "Arial"
        font_bold = "Arial-Bold"
    else:
        font_name = "Helvetica"
        font_bold = "Helvetica-Bold"

    # --- PDF 1: Accessible PDF (Tagged, Title, Lang, Structure, DisplayDocTitle, PDF/UA meta) ---
    acc_pdf_path = os.path.join(output_dir, "accessible_sample.pdf")
    doc = SimpleDocTemplate(acc_pdf_path, pagesize=letter, title="Annual Accessibility and Technology Report 2026", author="Compliance Team")

    styles = getSampleStyleSheet()
    h1 = ParagraphStyle('H1', parent=styles['Heading1'], fontName=font_bold, fontSize=18, leading=22, spaceAfter=8)
    h2 = ParagraphStyle('H2', parent=styles['Heading2'], fontName=font_bold, fontSize=14, leading=18, spaceBefore=8, spaceAfter=4)
    p = ParagraphStyle('P', parent=styles['Normal'], fontName=font_name)

    story = [
        Paragraph("Annual Accessibility and Technology Report 2026", h1),
        Paragraph("Executive Summary and Compliance Overview", h2),
        Paragraph("This document demonstrates an accessible PDF layout structured with headings, tables, and alternative descriptions.", p),
        Spacer(1, 10),
        Paragraph("Quarterly Audit Results", h2),
        Table([
            ["Quarter", "Status", "Score", "Findings"],
            ["Q1", "Passed", "98%", "None"],
            ["Q2", "Passed", "100%", "None"],
            ["Q3", "Passed", "99%", "Minor text clarity"],
        ], colWidths=[100, 100, 100, 150], style=[
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e2e8f0')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
            ('FONTNAME', (0, 0), (-1, -1), font_name),
            ('FONTNAME', (0, 0), (-1, 0), font_bold),
        ]),
        Spacer(1, 10),
    ]
    doc.build(story)

    # Enrich with pikepdf to add Tagged MarkInfo, /Lang, /ViewerPreferences, /StructTreeRoot, XMP PDF/UA
    with pikepdf.open(acc_pdf_path, allow_overwriting_input=True) as pdoc:
        pdoc.Root["/MarkInfo"] = pikepdf.Dictionary({"/Marked": True})
        pdoc.Root["/Lang"] = pikepdf.String("en-US")
        pdoc.Root["/ViewerPreferences"] = pikepdf.Dictionary({"/DisplayDocTitle": True})

        # Add StructTreeRoot & ParentTree
        doc_elem = pikepdf.Dictionary({
            "/Type": pikepdf.Name("/StructElem"),
            "/S": pikepdf.Name("/Document"),
            "/T": pikepdf.String("Accessible Document"),
            "/Pg": pdoc.pages[0].objgen
        })
        h1_elem = pikepdf.Dictionary({
            "/Type": pikepdf.Name("/StructElem"),
            "/S": pikepdf.Name("/H1"),
            "/T": pikepdf.String("Annual Accessibility and Technology Report 2026"),
            "/Pg": pdoc.pages[0].objgen,
            "/K": pikepdf.Integer(0)
        })
        doc_elem["/K"] = pikepdf.Array([h1_elem])

        # Wrap page content stream with marked content sequence for MCID 0
        if "/Contents" in pdoc.pages[0]:
            contents_obj = pdoc.pages[0]["/Contents"]
            raw_stream = b""
            if isinstance(contents_obj, pikepdf.Array):
                for stream_part in contents_obj:
                    if hasattr(stream_part, "read_bytes"):
                        raw_stream += stream_part.read_bytes() + b"\n"
            elif hasattr(contents_obj, "read_bytes"):
                raw_stream = contents_obj.read_bytes()
            tagged_stream = b"/H1 << /MCID 0 >> BDC\n" + raw_stream + b"\nEMC\n"
            pdoc.pages[0]["/Contents"] = pdoc.make_stream(tagged_stream)

        parent_tree = pikepdf.Dictionary({
            "/Nums": pikepdf.Array([pikepdf.Integer(0), pikepdf.Array([h1_elem])])
        })

        struct_root = pikepdf.Dictionary({
            "/Type": pikepdf.Name("/StructTreeRoot"),
            "/RoleMap": pikepdf.Dictionary({"/HeaderOne": pikepdf.Name("/H1")}),
            "/ParentTree": pdoc.make_indirect(parent_tree),
            "/ParentTreeNextKey": pikepdf.Integer(1),
            "/K": pikepdf.Array([doc_elem])
        })
        pdoc.Root["/StructTreeRoot"] = pdoc.make_indirect(struct_root)

        # Add page tab order & StructParents
        pdoc.pages[0]["/Tabs"] = pikepdf.Name("/S")
        pdoc.pages[0]["/StructParents"] = pikepdf.Integer(0)

        # XMP PDF/UA identification
        xmp_xml = """<?xpacket begin="" id="W5M0MpCehiHzreSzNTczkc9d"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/">
  <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
    <rdf:Description rdf:about=""
        xmlns:dc="http://purl.org/dc/elements/1.1/"
        xmlns:pdfuaid="http://www.aiim.org/pdfua/ns/id/">
      <dc:title><rdf:Alt><rdf:li xml:lang="x-default">Annual Accessibility and Technology Report 2026</rdf:li></rdf:Alt></dc:title>
      <pdfuaid:part>1</pdfuaid:part>
    </rdf:Description>
  </rdf:RDF>
</x:xmpmeta>
<?xpacket end="w"?>"""
        pdoc.Root["/Metadata"] = pdoc.make_stream(xmp_xml.encode("utf-8"))
        pdoc.Root.Metadata["/Type"] = pikepdf.Name("/Metadata")
        pdoc.Root.Metadata["/Subtype"] = pikepdf.Name("/XML")

        pdoc.save(acc_pdf_path)

    # --- PDF 2: Inaccessible PDF (Untagged, No Language, No Title, No Alt Text) ---
    inacc_pdf_path = os.path.join(output_dir, "inaccessible_untagged_sample.pdf")
    fitz_doc = pymupdf.open()
    page = fitz_doc.new_page(width=612, height=792)
    page.insert_text((50, 80), "Unformatted Raw Document Title", fontsize=16)
    page.insert_text((50, 120), "This PDF lacks tags, metadata, language definition, and alt text.", fontsize=11)
    page.insert_image(pymupdf.Rect(50, 160, 250, 260), filename=img_path)
    # Insert raw link
    page.insert_link({
        "kind": pymupdf.LINK_URI,
        "from": pymupdf.Rect(50, 280, 120, 295),
        "uri": "https://example.com/unlabeled"
    })
    page.insert_text((50, 292), "click here", fontsize=10, color=(0, 0, 1))

    fitz_doc.save(inacc_pdf_path)
    fitz_doc.close()

    print(f"Sample PDFs generated successfully in: {output_dir}")
    return acc_pdf_path, inacc_pdf_path


if __name__ == "__main__":
    generate_samples("test_samples")
