"""
PDF Document Parser
Combines pikepdf (deep PDF structural dictionary inspection) and pymupdf
(high-speed rendering, text extraction, visual bounding boxes) into a unified
PDFDocumentModel.
"""

from typing import Dict, List, Optional, Tuple, Any
import os
import re
import logging
import pikepdf
import pymupdf

from .models import (
    PDFDocumentModel, PageModel, StructureNode, FontModel,
    ImageModel, TableModel, LinkModel, FormFieldModel, BookmarkModel
)
from .structure_tree import StructureTreeParser, resolve_role

logger = logging.getLogger(__name__)


class DocumentParser:
    """Parses a PDF file into a complete, in-memory PDFDocumentModel."""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.filename = os.path.basename(filepath)
        self.filesize = os.path.getsize(filepath) if os.path.exists(filepath) else 0

    def parse(self) -> PDFDocumentModel:
        """Executes full document extraction."""
        pike_doc = pikepdf.open(self.filepath)
        fitz_doc = pymupdf.open(self.filepath)

        try:
            # 1. Basic Document Information
            pdf_version = str(getattr(pike_doc, "pdf_version", "1.7"))
            page_count = len(fitz_doc)

            # Metadata from Info dictionary
            doc_info = {}
            if "/Info" in pike_doc.trailer:
                info_dict = pike_doc.trailer["/Info"]
                for k, v in info_dict.items():
                    key = str(k).strip("/")
                    try:
                        doc_info[key] = str(v)
                    except Exception:
                        doc_info[key] = ""

            title = doc_info.get("Title")
            author = doc_info.get("Author")
            subject = doc_info.get("Subject")
            keywords = doc_info.get("Keywords")
            creator = doc_info.get("Creator")
            producer = doc_info.get("Producer")
            creation_date = doc_info.get("CreationDate")
            mod_date = doc_info.get("ModDate")

            # Document language
            language = None
            if "/Lang" in pike_doc.Root:
                language = str(pike_doc.Root["/Lang"]).strip()

            # Tagged PDF check
            is_tagged = False
            if "/MarkInfo" in pike_doc.Root:
                mark_info = pike_doc.Root["/MarkInfo"]
                if isinstance(mark_info, pikepdf.Dictionary) and "/Marked" in mark_info:
                    is_tagged = bool(mark_info["/Marked"])

            # Encryption / Extraction permissions
            is_encrypted = pike_doc.is_encrypted
            allows_extraction = True
            if is_encrypted:
                try:
                    # Check accessibility extraction bit in permissions
                    allows_extraction = fitz_doc.permissions & pymupdf.PDF_PERM_ACCESSIBILITY != 0
                except Exception:
                    allows_extraction = True

            # ViewerPreferences -> DisplayDocTitle
            display_doc_title = False
            if "/ViewerPreferences" in pike_doc.Root:
                vp = pike_doc.Root["/ViewerPreferences"]
                if isinstance(vp, pikepdf.Dictionary) and "/DisplayDocTitle" in vp:
                    display_doc_title = bool(vp["/DisplayDocTitle"])

            # XMP Metadata & PDF/UA Identification
            xmp_metadata_present = "/Metadata" in pike_doc.Root
            pdfua_identifier_present = False
            pdfua_part = None

            if xmp_metadata_present:
                try:
                    meta_bytes = bytes(pike_doc.Root.Metadata.read_bytes())
                    meta_str = meta_bytes.decode("utf-8", errors="ignore")

                    # Check for Dublin Core title in XMP if not found in Info
                    if not title:
                        m_title = re.search(r"<dc:title>.*?<rdf:li[^>]*>(.*?)</rdf:li>", meta_str, re.DOTALL | re.IGNORECASE)
                        if m_title:
                            title = m_title.group(1).strip()

                    # Check for PDF/UA identifier: <pdfuaid:part>1</pdfuaid:part>
                    m_part = re.search(r"<pdfuaid:part>(\d+)</pdfuaid:part>", meta_str, re.IGNORECASE)
                    if m_part:
                        pdfua_identifier_present = True
                        pdfua_part = int(m_part.group(1))
                    elif "pdfua" in meta_str.lower() or "iso 14289" in meta_str.lower():
                        pdfua_identifier_present = True
                        pdfua_part = 1
                except Exception as e:
                    logger.debug(f"Failed parsing XMP stream: {e}")

            # RoleMap
            role_map: Dict[str, str] = {}
            if "/StructTreeRoot" in pike_doc.Root:
                struct_root = pike_doc.Root["/StructTreeRoot"]
                if "/RoleMap" in struct_root and isinstance(struct_root["/RoleMap"], pikepdf.Dictionary):
                    for custom_tag, mapped_tag in struct_root["/RoleMap"].items():
                        role_map[str(custom_tag).strip("/")] = str(mapped_tag).strip("/")

            # Page mapping for Structure Tree
            page_map = {}
            for idx, p in enumerate(pike_doc.pages, start=1):
                if hasattr(p, "objgen"):
                    page_map[p.objgen] = idx

            # 2. Extract Pages
            pages: List[PageModel] = []
            for page_idx in range(1, page_count + 1):
                fitz_page = fitz_doc[page_idx - 1]
                rect = fitz_page.rect
                rotation = fitz_page.rotation
                text = fitz_page.get_text("text")

                # Check Tab order on page dictionary
                tab_mode = "Unspecified"
                has_tab = False
                try:
                    pike_page = pike_doc.pages[page_idx - 1]
                    if "/Tabs" in pike_page:
                        has_tab = True
                        tab_mode = str(pike_page["/Tabs"]).strip("/")
                except Exception:
                    pass

                # Image and link counts
                img_list = fitz_page.get_images()
                links_list = fitz_page.get_links()

                pages.append(PageModel(
                    page_number=page_idx,
                    width=rect.width,
                    height=rect.height,
                    rotation=rotation,
                    text=text,
                    images_count=len(img_list),
                    links_count=len(links_list),
                    has_structure=is_tagged,
                    has_tab_order=has_tab,
                    tab_order_mode=tab_mode
                ))

            # 3. Structure Tree
            tree_parser = StructureTreeParser(pike_doc, role_map, page_map)
            structure_tree = tree_parser.parse()

            # 4. Extract Fonts
            fonts = self._extract_fonts(fitz_doc, pike_doc)

            # 5. Extract Images & Figures
            images = self._extract_images(fitz_doc, structure_tree)

            # 6. Extract Tables
            tables = self._extract_tables(structure_tree)

            # 7. Extract Links
            links = self._extract_links(fitz_doc, structure_tree)

            # 8. Extract Form Fields
            form_fields = self._extract_form_fields(fitz_doc, pike_doc)

            # 9. Extract Bookmarks
            bookmarks = self._extract_bookmarks(fitz_doc)

            return PDFDocumentModel(
                filepath=self.filepath,
                filename=self.filename,
                filesize=self.filesize,
                pdf_version=pdf_version,
                page_count=page_count,
                title=title,
                author=author,
                subject=subject,
                keywords=keywords,
                creator=creator,
                producer=producer,
                creation_date=creation_date,
                modification_date=mod_date,
                language=language,
                is_tagged=is_tagged,
                is_encrypted=is_encrypted,
                allows_extraction=allows_extraction,
                display_doc_title=display_doc_title,
                xmp_metadata_present=xmp_metadata_present,
                pdfua_identifier_present=pdfua_identifier_present,
                pdfua_part=pdfua_part,
                role_map=role_map,
                pages=pages,
                structure_tree=structure_tree,
                fonts=fonts,
                images=images,
                tables=tables,
                links=links,
                form_fields=form_fields,
                bookmarks=bookmarks,
                raw_metadata=doc_info
            )
        finally:
            fitz_doc.close()
            pike_doc.close()

    def _extract_fonts(self, fitz_doc: pymupdf.Document, pike_doc: pikepdf.Pdf) -> List[FontModel]:
        """Extracts all fonts and verifies embedding and ToUnicode maps."""
        font_dict: Dict[str, FontModel] = {}

        for page_idx in range(len(fitz_doc)):
            page = fitz_doc[page_idx]
            font_list = page.get_fonts(full=True)
            for f in font_list:
                # f is (xref, ext, type, basefont, name, encoding)
                basefont = f[3] if len(f) > 3 else "Unknown"
                subtype = f[2] if len(f) > 2 else "Unknown"
                encoding = f[5] if len(f) > 5 else "Custom"
                xref = f[0]

                is_subset = "+" in basefont and len(basefont.split("+")[0]) == 6
                is_embedded = False
                has_tounicode = False

                # Query pikepdf object for exact descriptor details
                try:
                    if xref and xref in pike_doc.objects:
                        font_obj = pike_doc.objects[xref]
                        if "/ToUnicode" in font_obj:
                            has_tounicode = True

                        if "/FontDescriptor" in font_obj:
                            fd = font_obj["/FontDescriptor"]
                            if any(k in fd for k in ("/FontFile", "/FontFile2", "/FontFile3")):
                                is_embedded = True
                except Exception:
                    pass

                if basefont in font_dict:
                    if (page_idx + 1) not in font_dict[basefont].pages:
                        font_dict[basefont].pages.append(page_idx + 1)
                else:
                    font_dict[basefont] = FontModel(
                        name=basefont,
                        subtype=subtype,
                        is_embedded=is_embedded or is_subset,
                        is_subset=is_subset,
                        has_tounicode=has_tounicode,
                        encoding=str(encoding),
                        pages=[page_idx + 1]
                    )

        # Collect actually used font names in page text spans
        used_font_names = set()
        for page in fitz_doc:
            td = page.get_text("dict")
            for block in td.get("blocks", []):
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        fn = span.get("font", "").lower().replace(" ", "")
                        if fn:
                            used_font_names.add(fn)

        for f in font_dict.values():
            if not used_font_names:
                f.is_used = False
            else:
                clean_base = f.name.lower().replace(" ", "")
                if "+" in clean_base:
                    clean_base = clean_base.split("+")[-1]
                f.is_used = any(clean_base in u or u in clean_base for u in used_font_names)

        return list(font_dict.values())

    def _extract_images(self, fitz_doc: pymupdf.Document, struct_tree: Optional[StructureNode]) -> List[ImageModel]:
        """Extracts images and maps them to Structure /Figure elements."""
        images: List[ImageModel] = []
        figure_nodes: List[StructureNode] = []
        if struct_tree:
            figure_nodes = struct_tree.find_all_by_standard_tag("Figure")

        fig_index = 0
        for page_idx in range(len(fitz_doc)):
            page = fitz_doc[page_idx]
            page_num = page_idx + 1
            image_info_list = page.get_image_info(xrefs=True)

            for img_info in image_info_list:
                bbox_tuple = tuple(img_info.get("bbox", (0, 0, 0, 0)))
                width = img_info.get("width", 0)
                height = img_info.get("height", 0)
                cs = img_info.get("cs-name", "RGB")

                # Match with Figure node if page matches
                matched_node = None
                for fn in figure_nodes:
                    if fn.page == page_num or fn.page is None:
                        matched_node = fn
                        break

                has_alt = bool(matched_node and matched_node.alt_text and matched_node.alt_text.strip())
                alt_val = matched_node.alt_text.strip() if (matched_node and matched_node.alt_text) else ""

                images.append(ImageModel(
                    id=f"img_p{page_num}_{img_info.get('xref', len(images))}",
                    page=page_num,
                    bbox=bbox_tuple,
                    width=width,
                    height=height,
                    colorspace=cs,
                    has_alt=has_alt,
                    alt_text=alt_val,
                    structure_element_id=matched_node.id if matched_node else None
                ))
                fig_index += 1

        return images

    def _extract_tables(self, struct_tree: Optional[StructureNode]) -> List[TableModel]:
        """Extracts Table structural nodes and checks header cells."""
        tables: List[TableModel] = []
        if not struct_tree:
            return tables

        table_nodes = struct_tree.find_all_by_standard_tag("Table")
        for idx, t_node in enumerate(table_nodes):
            tr_nodes = t_node.find_all_by_standard_tag("TR")
            th_nodes = t_node.find_all_by_standard_tag("TH")
            td_nodes = t_node.find_all_by_standard_tag("TD")

            rows_count = len(tr_nodes)
            th_count = len(th_nodes)
            td_count = len(td_nodes)
            cols_count = max((len(tr.find_all_by_standard_tag("TH")) + len(tr.find_all_by_standard_tag("TD"))) for tr in tr_nodes) if tr_nodes else 0

            tables.append(TableModel(
                id=f"table_{idx + 1}",
                page=t_node.page or 1,
                rows_count=rows_count,
                cols_count=cols_count,
                has_headers=th_count > 0,
                header_cells_count=th_count,
                data_cells_count=td_count,
                summary=t_node.title,
                is_regular=(th_count + td_count) == (rows_count * cols_count) if (rows_count > 0 and cols_count > 0) else True,
                bbox=t_node.bbox
            ))

        return tables

    def _extract_links(self, fitz_doc: pymupdf.Document, struct_tree: Optional[StructureNode]) -> List[LinkModel]:
        """Extracts links from page annotations and associates them with Link structure elements."""
        links: List[LinkModel] = []
        link_nodes: List[StructureNode] = []
        if struct_tree:
            link_nodes = struct_tree.find_all_by_standard_tag("Link")

        for page_idx in range(len(fitz_doc)):
            page = fitz_doc[page_idx]
            page_num = page_idx + 1
            for l in page.get_links():
                rect = l.get("from", (0, 0, 0, 0))
                uri = l.get("uri", "")
                page_dest = l.get("page", None)
                if page_dest is not None:
                    page_dest += 1  # 1-indexed

                # Extract visible text under this link rect
                link_text = page.get_text("text", clip=rect).strip()
                if not link_text and uri:
                    link_text = uri

                # Check if matching structure tag exists
                matched_node = next((ln for ln in link_nodes if ln.page == page_num), None)

                links.append(LinkModel(
                    id=f"link_p{page_num}_{len(links) + 1}",
                    page=page_num,
                    text=link_text,
                    uri=uri or (f"Page {page_dest}" if page_dest else "Internal"),
                    is_internal=bool(page_dest),
                    destination_page=page_dest,
                    alt_text=matched_node.alt_text if matched_node else None,
                    has_structure_link=matched_node is not None,
                    bbox=(rect.x0, rect.y0, rect.x1, rect.y1) if hasattr(rect, "x0") else tuple(rect)
                ))

        return links

    def _extract_form_fields(self, fitz_doc: pymupdf.Document, pike_doc: pikepdf.Pdf) -> List[FormFieldModel]:
        """Extracts interactive form fields and checks accessible tooltips /TU."""
        fields: List[FormFieldModel] = []
        for page_idx in range(len(fitz_doc)):
            page = fitz_doc[page_idx]
            page_num = page_idx + 1
            widgets = page.widgets()
            if widgets:
                for w in widgets:
                    name = w.field_name or "UnnamedField"
                    ftype = w.field_type_string or "Widget"
                    tooltip = None
                    rect = (w.rect.x0, w.rect.y0, w.rect.x1, w.rect.y1) if w.rect else None

                    # Retrieve /TU from low-level annotation dict
                    try:
                        if w.xref and w.xref in pike_doc.objects:
                            annot_obj = pike_doc.objects[w.xref]
                            if "/TU" in annot_obj:
                                tooltip = str(annot_obj["/TU"]).strip()
                    except Exception:
                        pass

                    fields.append(FormFieldModel(
                        name=name,
                        field_type=ftype,
                        tooltip=tooltip,
                        label=w.field_label or name,
                        page=page_num,
                        is_required=False,
                        bbox=rect
                    ))

        return fields

    def _extract_bookmarks(self, fitz_doc: pymupdf.Document) -> List[BookmarkModel]:
        """Extracts document table of contents / bookmarks hierarchy."""
        toc = fitz_doc.get_toc()  # [[lvl, title, page, ...], ...]
        bookmarks: List[BookmarkModel] = []
        stack: List[Tuple[int, BookmarkModel]] = []

        for item in toc:
            lvl = item[0]
            title = item[1]
            page = item[2]
            bm = BookmarkModel(title=title, level=lvl, page=page)

            while stack and stack[-1][0] >= lvl:
                stack.pop()

            if stack:
                stack[-1][1].children.append(bm)
            else:
                bookmarks.append(bm)

            stack.append((lvl, bm))

        return bookmarks
