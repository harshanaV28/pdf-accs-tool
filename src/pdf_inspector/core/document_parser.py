"""
PDF Document Parser
Combines pikepdf (deep PDF structural dictionary inspection, StructTreeRoot, ParentTree)
and pymupdf (high-speed rendering, text extraction, visual bounding boxes, annotations)
into a unified, exhaustive PDFDocumentModel.
"""

from typing import Dict, List, Optional, Tuple, Any, Set
import os
import re
import logging
import pikepdf
import pymupdf

from .models import (
    PDFDocumentModel, PageModel, StructureNode, FontModel,
    ImageModel, TableModel, ListModel, LinkModel, FormFieldModel,
    AnnotationModel, BookmarkModel, ArtifactOccurrenceModel
)
from .structure_tree import StructureTreeParser, resolve_role, parse_number_tree

logger = logging.getLogger(__name__)

# Regex for parsing marked content sequences in PDF content streams
MCID_PATTERN = re.compile(r"/(\w+)\s*<<\s*[^>]*?/MCID\s+(\d+)[^>]*?>>\s*BDC", re.DOTALL)
ARTIFACT_PATTERN = re.compile(r"/Artifact(?:\s*<<[^>]*?>>)?\s*B[DM]C", re.DOTALL)
ART_XOBJECT_PATTERN = re.compile(r'(/(\w+)\s*(?:<<.*?>>)?\s*B[DM]C)|(\bEMC\b)|(/(\w+)\s+Do\b)', re.DOTALL)
CONTENT_TOKEN_PATTERN = re.compile(r'(/(\w+)\s+(<<.*?>>|/\w+)\s*BDC|/(\w+)\s+BMC|(\bEMC\b)|(/(\w+)\s+Do\b))', re.DOTALL)


class DocumentParser:
    """Parses a PDF file into a complete, in-memory PDFDocumentModel."""

    def __init__(self, filepath: str, password: Optional[str] = None):
        self.filepath = filepath
        self.filename = os.path.basename(filepath)
        self.filesize = os.path.getsize(filepath) if os.path.exists(filepath) else 0
        self.password = password

    def parse(self) -> PDFDocumentModel:
        """Executes full document extraction."""
        if not os.path.exists(self.filepath):
            raise FileNotFoundError(f"PDF file does not exist: {self.filepath}")

        try:
            pike_doc = pikepdf.open(self.filepath, password=self.password or "")
        except pikepdf.PasswordError:
            raise PermissionError("Password required — analysis cannot continue until the document is unlocked.")
        except pikepdf.PdfError as pe:
            raise ValueError(f"PDF '{self.filename}' is corrupt or malformed: {pe}")
        except Exception as e:
            raise RuntimeError(f"Failed to open PDF '{self.filename}': {e}")

        try:
            fitz_doc = pymupdf.open(self.filepath)
            if fitz_doc.needs_pass:
                if self.password:
                    auth_success = fitz_doc.authenticate(self.password)
                    if not auth_success:
                        pike_doc.close()
                        fitz_doc.close()
                        raise PermissionError("Password required — analysis cannot continue until the document is unlocked.")
                else:
                    pike_doc.close()
                    fitz_doc.close()
                    raise PermissionError("Password required — analysis cannot continue until the document is unlocked.")
        except PermissionError:
            raise
        except Exception as e:
            pike_doc.close()
            raise ValueError(f"Failed to render PDF '{self.filename}': {e}")

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

            doc_info_title = doc_info.get("Title")
            doc_info_author = doc_info.get("Author")
            doc_info_subject = doc_info.get("Subject")
            doc_info_keywords = doc_info.get("Keywords")
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
                    allows_extraction = fitz_doc.permissions & pymupdf.PDF_PERM_ACCESSIBILITY != 0
                except Exception:
                    allows_extraction = True

            # ViewerPreferences -> DisplayDocTitle
            display_doc_title = False
            if "/ViewerPreferences" in pike_doc.Root:
                vp = pike_doc.Root["/ViewerPreferences"]
                if isinstance(vp, pikepdf.Dictionary) and "/DisplayDocTitle" in vp:
                    display_doc_title = bool(vp["/DisplayDocTitle"])

            # MarkInfo -> Suspects (ISO 14289-1 Clause 7.18, Matterhorn Checkpoint 31-003)
            has_suspects = False
            if "/MarkInfo" in pike_doc.Root:
                mi = pike_doc.Root["/MarkInfo"]
                if isinstance(mi, pikepdf.Dictionary) and "/Suspects" in mi:
                    has_suspects = bool(mi["/Suspects"])

            # XMP Metadata & PDF/UA Identification
            xmp_metadata_present = "/Metadata" in pike_doc.Root
            xmp_dc_title = None
            xmp_dc_creator = None
            xmp_dc_description = None
            pdfua_identifier_present = False
            pdfua_part = None

            if xmp_metadata_present:
                try:
                    meta_bytes = bytes(pike_doc.Root.Metadata.read_bytes())
                    meta_str = meta_bytes.decode("utf-8", errors="ignore")

                    # Dublin Core Title (<dc:title>)
                    m_title = re.search(r"<dc:title>.*?<rdf:li[^>]*>(.*?)</rdf:li>", meta_str, re.DOTALL | re.IGNORECASE)
                    if m_title:
                        xmp_dc_title = m_title.group(1).strip()
                    else:
                        m_title_direct = re.search(r"<dc:title>(.*?)</dc:title>", meta_str, re.DOTALL | re.IGNORECASE)
                        if m_title_direct and "<rdf:li" not in m_title_direct.group(1):
                            xmp_dc_title = m_title_direct.group(1).strip()

                    # Dublin Core Creator
                    m_creator = re.search(r"<dc:creator>.*?<rdf:li[^>]*>(.*?)</rdf:li>", meta_str, re.DOTALL | re.IGNORECASE)
                    if m_creator:
                        xmp_dc_creator = m_creator.group(1).strip()

                    # Dublin Core Description
                    m_desc = re.search(r"<dc:description>.*?<rdf:li[^>]*>(.*?)</rdf:li>", meta_str, re.DOTALL | re.IGNORECASE)
                    if m_desc:
                        xmp_dc_description = m_desc.group(1).strip()

                    # PDF/UA Identification (pdfuaid:part)
                    m_part = re.search(r"<pdfuaid:part>(\d+)</pdfuaid:part>", meta_str, re.IGNORECASE)
                    if m_part:
                        pdfua_identifier_present = True
                        pdfua_part = int(m_part.group(1))
                    elif "pdfuaid" in meta_str.lower() or "iso 14289" in meta_str.lower():
                        pdfua_identifier_present = True
                        pdfua_part = 1
                except Exception as e:
                    logger.debug(f"Failed parsing XMP stream: {e}")

            # Display title preference: prefer XMP dc:title, fallback to Info title for UI display
            title = xmp_dc_title or doc_info_title

            # ParentTree & RoleMap
            has_parent_tree = False
            parent_tree_valid = False
            parent_tree_entries_count = 0
            role_map: Dict[str, str] = {}

            if "/StructTreeRoot" in pike_doc.Root:
                struct_root = pike_doc.Root["/StructTreeRoot"]
                if "/RoleMap" in struct_root and isinstance(struct_root["/RoleMap"], pikepdf.Dictionary):
                    for custom_tag, mapped_tag in struct_root["/RoleMap"].items():
                        role_map[str(custom_tag).strip("/")] = str(mapped_tag).strip("/")

                if "/ParentTree" in struct_root:
                    has_parent_tree = True
                    try:
                        pt_entries = parse_number_tree(struct_root["/ParentTree"])
                        parent_tree_entries_count = len(pt_entries)
                        parent_tree_valid = parent_tree_entries_count > 0
                    except Exception as e:
                        logger.debug(f"Error parsing ParentTree: {e}")

            # Page mapping for Structure Tree
            page_map = {}
            for idx, p in enumerate(pike_doc.pages, start=1):
                if hasattr(p, "objgen"):
                    page_map[p.objgen] = idx
                    page_map[p.objgen[0]] = idx
                page_map[id(p)] = idx

            # 2. Extract Pages with MCIDs, content occurrences, artifacts, and geometry
            pages: List[PageModel] = []
            page_mcid_data: Dict[int, Dict[int, Tuple[str, Tuple[float, float, float, float]]]] = {}
            page_artifact_xobjs: Dict[int, Set[str]] = {}
            xobject_artifact_cache: Dict[int, Tuple[int, List[str]]] = {}

            STREAM_TOKEN_RE = re.compile(
                r'(?P<bdc>/(\w+)\s+(<<.*?>>|/\w+)\s*BDC)'
                r'|(?P<bmc>/(\w+)\s+BMC)'
                r'|(?P<emc>\bEMC\b)'
                r'|(?P<do>/(\w+)\s+Do\b)'
                r'|(?P<text_tj>(?:\((?:\\.|[^()\\])*\)|\[(?:\\.|[^\]\\])*\])\s*(?:TJ|Tj|\'|"))'
                r'|(?P<paint>\b(?:sh|f\*|b\*|B\*|f|F|S|s|B|b)\b)',
                re.DOTALL
            )

            for page_idx, pike_page in enumerate(pike_doc.pages, start=1):
                fitz_page = fitz_doc[page_idx - 1]
                rect = fitz_page.rect
                rotation = fitz_page.rotation
                text = fitz_page.get_text("text")

                # Check Tab order and StructParents on page dictionary
                tab_mode = "Unspecified"
                has_tab = False
                annots_count = 0
                struct_parents_id = None
                mcids_found: List[int] = []
                mcid_bboxes: Dict[int, Tuple[float, float, float, float]] = {}
                mcid_texts: Dict[int, str] = {}
                art_xobjs: Set[str] = set()
                page_artifacts: List[ArtifactOccurrenceModel] = []
                page_content_occs: List[ContentOccurrenceModel] = []
                unmarked_count = 0
                tagged_in_art_count = 0
                art_in_tagged_count = 0

                # Collect XObjects defined on this page
                xobj_info: Dict[str, Dict[str, Any]] = {}
                try:
                    for xo in fitz_page.get_xobjects():
                        xobj_info[xo[1]] = {"xref": xo[0], "rect": xo[3]}
                except Exception as e:
                    logger.debug(f"Error checking page xobjects: {e}")

                try:
                    if "/Annots" in pike_page:
                        try:
                            annots_count = len(pike_page["/Annots"])
                        except Exception:
                            annots_count = 0

                    if "/Tabs" in pike_page:
                        has_tab = True
                        tab_mode = str(pike_page["/Tabs"]).strip("/")

                    if "/StructParents" in pike_page:
                        struct_parents_id = int(pike_page["/StructParents"])

                    # Parse MCIDs, Artifacts, and marked content tokens from page contents stream
                    if "/Contents" in pike_page:
                        contents_obj = pike_page["/Contents"]
                        raw_stream = b""
                        if isinstance(contents_obj, pikepdf.Array):
                            for stream_part in contents_obj:
                                if hasattr(stream_part, "read_bytes"):
                                    raw_stream += stream_part.read_bytes() + b"\n"
                        elif hasattr(contents_obj, "read_bytes"):
                            raw_stream = contents_obj.read_bytes()

                        stream_text = raw_stream.decode("latin1", errors="ignore")
                        for match in MCID_PATTERN.finditer(stream_text):
                            mcid_num = int(match.group(2))
                            if mcid_num not in mcids_found:
                                mcids_found.append(mcid_num)

                        # Marked content stack tracking
                        stack: List[Dict[str, Any]] = []

                        for m in STREAM_TOKEN_RE.finditer(stream_text):
                            if m.group("bdc"):
                                bdc_m = re.match(r"/(\w+)\s+(<<.*?>>|/\w+)\s*BDC", m.group("bdc"), re.DOTALL)
                                tag = bdc_m.group(1) if bdc_m else "Span"
                                props = bdc_m.group(2) if bdc_m else ""
                                mcid = None
                                if props.startswith("<<") and "/MCID" in props:
                                    mc_match = re.search(r"/MCID\s+(\d+)", props)
                                    if mc_match:
                                        mcid = int(mc_match.group(1))

                                is_art = (tag.lower() == "artifact" or "/artifact" in props.lower())
                                in_tagged = any(s["mcid"] is not None for s in stack)
                                in_art = any(s["is_artifact"] for s in stack)

                                if is_art:
                                    if in_tagged:
                                        art_in_tagged_count += 1
                                        ancestor = next(s for s in reversed(stack) if s["mcid"] is not None)
                                        page_artifacts.append(ArtifactOccurrenceModel(
                                            page_number=page_idx,
                                            is_inside_tagged=True,
                                            parent_tag=ancestor["tag"],
                                            parent_mcid=ancestor["mcid"],
                                            bbox=None,
                                            text_snippet=""
                                        ))
                                    else:
                                        page_artifacts.append(ArtifactOccurrenceModel(
                                            page_number=page_idx,
                                            is_inside_tagged=False
                                        ))
                                else:
                                    if in_art and mcid is not None:
                                        tagged_in_art_count += 1
                                        page_content_occs.append(ContentOccurrenceModel(
                                            page_number=page_idx,
                                            operator_type="marked_content",
                                            operator_name="BDC",
                                            mcid=mcid,
                                            tag=tag,
                                            is_inside_artifact=True
                                        ))

                                stack.append({"tag": tag, "mcid": mcid, "is_artifact": is_art})

                            elif m.group("bmc"):
                                bmc_m = re.match(r"/(\w+)\s+BMC", m.group("bmc"))
                                tag = bmc_m.group(1) if bmc_m else "Span"
                                is_art = (tag.lower() == "artifact")
                                in_tagged = any(s["mcid"] is not None for s in stack)
                                in_art = any(s["is_artifact"] for s in stack)

                                if is_art:
                                    if in_tagged:
                                        art_in_tagged_count += 1
                                        ancestor = next(s for s in reversed(stack) if s["mcid"] is not None)
                                        page_artifacts.append(ArtifactOccurrenceModel(
                                            page_number=page_idx,
                                            is_inside_tagged=True,
                                            parent_tag=ancestor["tag"],
                                            parent_mcid=ancestor["mcid"],
                                            bbox=None,
                                            text_snippet=""
                                        ))
                                    else:
                                        page_artifacts.append(ArtifactOccurrenceModel(
                                            page_number=page_idx,
                                            is_inside_tagged=False
                                        ))

                                stack.append({"tag": tag, "mcid": None, "is_artifact": is_art})

                            elif m.group("emc"):
                                if stack:
                                    stack.pop()

                            elif m.group("text_tj"):
                                tj_txt = m.group("text_tj")
                                in_tagged = any(s["mcid"] is not None for s in stack)
                                in_art = any(s["is_artifact"] for s in stack)
                                if not in_tagged and not in_art:
                                    # Text operator executed outside of any marked content sequence
                                    unmarked_count += 1
                                    page_content_occs.append(ContentOccurrenceModel(
                                        page_number=page_idx,
                                        operator_type="text",
                                        operator_name="Tj/TJ",
                                        is_unmarked_real_content=True,
                                        snippet=tj_txt[:60]
                                    ))

                            elif m.group("paint"):
                                paint_op = m.group("paint")
                                in_tagged = any(s["mcid"] is not None for s in stack)
                                in_art = any(s["is_artifact"] for s in stack)
                                if not in_tagged and not in_art:
                                    # Path painting outside marked content
                                    unmarked_count += 1
                                    page_content_occs.append(ContentOccurrenceModel(
                                        page_number=page_idx,
                                        operator_type="path",
                                        operator_name=paint_op,
                                        is_unmarked_real_content=True
                                    ))

                            elif m.group("do"):
                                do_m = re.match(r"/(\w+)\s+Do", m.group("do"))
                                xname = do_m.group(1) if do_m else ""
                                in_tagged = any(s["mcid"] is not None for s in stack)
                                in_art = any(s["is_artifact"] for s in stack)

                                if any(s["tag"].lower() == "artifact" for s in stack):
                                    art_xobjs.add(xname)

                                if xname in xobj_info:
                                    xo_entry = xobj_info[xname]
                                    xref = xo_entry["xref"]
                                    xo_rect = xo_entry["rect"]

                                    if xref not in xobject_artifact_cache:
                                        try:
                                            xo_stream = fitz_doc.xref_stream(xref).decode("latin1", errors="ignore")
                                            xo_art_matches = ARTIFACT_PATTERN.findall(xo_stream)
                                            snippets: List[str] = []
                                            for art_block in re.findall(r"/Artifact\s*(?:<<.*?>>)?\s*B[DM]C(.*?)EMC", xo_stream, re.DOTALL):
                                                tjs = re.findall(r"\(([^)]+)\)\s*Tj|\[(.*?)\]\s*TJ", art_block)
                                                for tj_str, tj_arr in tjs:
                                                    s_txt = tj_str or tj_arr
                                                    parts = re.findall(r"\((.*?)\)", s_txt) if tj_arr else [tj_str]
                                                    cleaned = re.sub(r"\\[0-7]{1,3}", "", " ".join(parts))
                                                    cleaned = re.sub(r"\\[nrtbf\\()]", "", cleaned).strip()
                                                    if sum(c.isalnum() for c in cleaned) >= 3:
                                                        snippets.append(cleaned)
                                            xobject_artifact_cache[xref] = (len(xo_art_matches), snippets)
                                        except Exception:
                                            xobject_artifact_cache[xref] = (0, [])

                                    xo_arts_cnt, xo_snippets = xobject_artifact_cache[xref]
                                    if xo_arts_cnt > 0:
                                        snippet_text = xo_snippets[0] if xo_snippets else f"Artifact in Form XObject /{xname}"
                                        bbox_tuple = (float(xo_rect[0]), float(xo_rect[1]), float(xo_rect[2]), float(xo_rect[3])) if xo_rect else None

                                        if in_tagged:
                                            art_in_tagged_count += xo_arts_cnt
                                            ancestor = next(s for s in reversed(stack) if s["mcid"] is not None)
                                            for _ in range(xo_arts_cnt):
                                                page_artifacts.append(ArtifactOccurrenceModel(
                                                    page_number=page_idx,
                                                    is_inside_tagged=True,
                                                    parent_tag=ancestor["tag"],
                                                    parent_mcid=ancestor["mcid"],
                                                    xobject_name=xname,
                                                    xobject_xref=xref,
                                                    bbox=bbox_tuple,
                                                    text_snippet=snippet_text
                                                ))
                                        else:
                                            for _ in range(xo_arts_cnt):
                                                page_artifacts.append(ArtifactOccurrenceModel(
                                                    page_number=page_idx,
                                                    is_inside_tagged=False,
                                                    xobject_name=xname,
                                                    xobject_xref=xref,
                                                    bbox=bbox_tuple,
                                                    text_snippet=snippet_text
                                                ))
                                    elif not in_tagged and not in_art:
                                        # Form XObject containing real content executed outside marked content
                                        unmarked_count += 1
                                        page_content_occs.append(ContentOccurrenceModel(
                                            page_number=page_idx,
                                            operator_type="xobject",
                                            operator_name="Do",
                                            is_unmarked_real_content=True,
                                            xobject_name=xname,
                                            snippet=f"XObject /{xname} Do"
                                        ))
                                elif not in_tagged and not in_art:
                                    # XObject Do outside marked content and not in xobj_info
                                    unmarked_count += 1
                                    page_content_occs.append(ContentOccurrenceModel(
                                        page_number=page_idx,
                                        operator_type="xobject",
                                        operator_name="Do",
                                        is_unmarked_real_content=True,
                                        xobject_name=xname,
                                        snippet=f"XObject /{xname} Do"
                                    ))

                except Exception as e:
                    logger.debug(f"Error checking page dictionary: {e}")

                page_artifact_xobjs[page_idx] = art_xobjs

                # Image and link counts
                img_list = fitz_page.get_images()
                links_list = fitz_page.get_links()

                # Map text blocks to bounding boxes as approximation for MCIDs if present
                if mcids_found:
                    blocks = fitz_page.get_text("blocks")
                    for idx, b in enumerate(blocks):
                        if idx < len(mcids_found):
                            target_mcid = mcids_found[idx]
                            mcid_bboxes[target_mcid] = (b[0], b[1], b[2], b[3])
                            mcid_texts[target_mcid] = b[4].strip()

                page_mcid_data[page_idx] = {
                    mcid: (mcid_texts.get(mcid, ""), mcid_bboxes.get(mcid, (0, 0, 0, 0)))
                    for mcid in mcids_found
                }

                pages.append(PageModel(
                    page_number=page_idx,
                    width=rect.width,
                    height=rect.height,
                    rotation=rotation,
                    text=text,
                    images_count=len(img_list),
                    links_count=len(links_list),
                    has_structure=is_tagged and (len(mcids_found) > 0 or len(page_artifacts) > 0),
                    has_tab_order=has_tab,
                    tab_order_mode=tab_mode,
                    struct_parents_id=struct_parents_id,
                    mcids=mcids_found,
                    mcid_bboxes=mcid_bboxes,
                    mcid_texts=mcid_texts,
                    artifacts=page_artifacts,
                    content_occurrences=page_content_occs,
                    unmarked_real_content_count=unmarked_count,
                    tagged_in_artifact_count=tagged_in_art_count,
                    artifact_in_tagged_count=art_in_tagged_count,
                    annotations_count=annots_count
                ))

            # 3. Structure Tree
            tree_parser = StructureTreeParser(pike_doc, role_map, page_map, page_mcid_data)
            structure_tree = tree_parser.parse()

            # 4. Extract Fonts
            fonts = self._extract_fonts(fitz_doc, pike_doc)

            # 5. Extract Images & Figures
            images = self._extract_images(fitz_doc, structure_tree, page_artifact_xobjs)

            # 6. Extract Tables
            tables = self._extract_tables(structure_tree)

            # 7. Extract Lists (<L>)
            lists = self._extract_lists(structure_tree)

            # 8. Extract Links
            links = self._extract_links(fitz_doc, structure_tree)

            # 9. Extract Form Fields
            form_fields = self._extract_form_fields(fitz_doc, pike_doc)

            # 10. Extract Annotations
            annotations = self._extract_annotations(fitz_doc, pike_doc, structure_tree)

            # 11. Extract Bookmarks
            bookmarks = self._extract_bookmarks(fitz_doc)

            # 12. Check Embedded Files count
            try:
                embedded_files_count = fitz_doc.embfile_count()
            except Exception:
                embedded_files_count = 0

            return PDFDocumentModel(
                filepath=self.filepath,
                filename=self.filename,
                filesize=self.filesize,
                pdf_version=pdf_version,
                page_count=page_count,
                title=title,
                author=doc_info_author or xmp_dc_creator,
                subject=doc_info_subject or xmp_dc_description,
                keywords=doc_info_keywords,
                creator=creator,
                producer=producer,
                creation_date=creation_date,
                modification_date=mod_date,
                language=language,
                is_tagged=is_tagged,
                is_encrypted=is_encrypted,
                allows_extraction=allows_extraction,
                display_doc_title=display_doc_title,
                has_suspects=has_suspects,
                doc_info_title=doc_info_title,
                doc_info_author=doc_info_author,
                doc_info_subject=doc_info_subject,
                doc_info_keywords=doc_info_keywords,
                xmp_metadata_present=xmp_metadata_present,
                xmp_dc_title=xmp_dc_title,
                xmp_dc_creator=xmp_dc_creator,
                xmp_dc_description=xmp_dc_description,
                pdfua_identifier_present=pdfua_identifier_present,
                pdfua_part=pdfua_part,
                has_parent_tree=has_parent_tree,
                parent_tree_valid=parent_tree_valid,
                parent_tree_entries_count=parent_tree_entries_count,
                role_map=role_map,
                pages=pages,
                structure_tree=structure_tree,
                fonts=fonts,
                images=images,
                tables=tables,
                lists=lists,
                links=links,
                form_fields=form_fields,
                annotations=annotations,
                bookmarks=bookmarks,
                raw_metadata=doc_info,
                embedded_files_count=embedded_files_count
            )
        finally:
            fitz_doc.close()
            pike_doc.close()

    def _extract_fonts(self, fitz_doc: pymupdf.Document, pike_doc: pikepdf.Pdf) -> List[FontModel]:
        """Extracts all fonts and verifies embedding and ToUnicode maps."""
        font_dict: Dict[Any, FontModel] = {}

        for page_idx in range(len(fitz_doc)):
            page = fitz_doc[page_idx]
            font_list = page.get_fonts(full=True)
            for f in font_list:
                xref = f[0]
                ext = f[1] if len(f) > 1 else ""
                subtype = f[2] if len(f) > 2 else "Unknown"
                basefont = f[3] if len(f) > 3 else "Unknown"
                encoding = f[5] if len(f) > 5 else "Custom"

                font_key = xref if xref > 0 else basefont

                if font_key in font_dict:
                    if (page_idx + 1) not in font_dict[font_key].pages:
                        font_dict[font_key].pages.append(page_idx + 1)
                    continue

                is_subset = "+" in basefont and len(basefont.split("+")[0]) == 6
                # If PyMuPDF found an embedded font extension (cff, ttf, otf, cid, etc.), it is embedded
                is_embedded = bool(ext and ext.lower() not in ("", "n/a", "none")) or is_subset
                has_tounicode = False
                has_standard_encoding = str(encoding).strip("/") in (
                    "WinAnsiEncoding", "MacRomanEncoding", "StandardEncoding",
                    "PDFDocEncoding", "Identity-H", "Identity-V"
                )

                font_obj = None
                try:
                    font_obj = pike_doc.get_object((xref, 0))
                except Exception:
                    try:
                        if 0 < xref < len(pike_doc.objects):
                            font_obj = pike_doc.objects[xref]
                    except Exception:
                        pass

                if font_obj is not None:
                    if "/ToUnicode" in font_obj:
                        has_tounicode = True

                    if "/FontDescriptor" in font_obj:
                        fd = font_obj["/FontDescriptor"]
                        if any(k in fd for k in ("/FontFile", "/FontFile2", "/FontFile3")):
                            is_embedded = True

                    if "/DescendantFonts" in font_obj:
                        try:
                            for df in font_obj["/DescendantFonts"]:
                                if "/FontDescriptor" in df:
                                    df_fd = df["/FontDescriptor"]
                                    if any(k in df_fd for k in ("/FontFile", "/FontFile2", "/FontFile3")):
                                        is_embedded = True
                                if "/ToUnicode" in df:
                                    has_tounicode = True
                        except Exception:
                            pass

                    if "/Encoding" in font_obj:
                        try:
                            enc_val = font_obj["/Encoding"]
                            if isinstance(enc_val, pikepdf.Name):
                                enc_str = str(enc_val).strip("/")
                                if enc_str in ("WinAnsiEncoding", "MacRomanEncoding", "StandardEncoding"):
                                    has_standard_encoding = True
                            elif isinstance(enc_val, pikepdf.Dictionary) and "/BaseEncoding" in enc_val:
                                base_enc = str(enc_val["/BaseEncoding"]).strip("/")
                                if base_enc in ("WinAnsiEncoding", "MacRomanEncoding", "StandardEncoding"):
                                    has_standard_encoding = True
                        except Exception:
                            pass

                font_dict[font_key] = FontModel(
                    name=basefont,
                    subtype=subtype,
                    is_embedded=is_embedded,
                    is_subset=is_subset,
                    has_tounicode=has_tounicode,
                    encoding=str(encoding),
                    pages=[page_idx + 1],
                    is_used=True,
                    xref=xref,
                    has_standard_encoding=has_standard_encoding
                )

        # Check usage for non-embedded fonts to prevent false positives from unused resource entries
        page_spans_cache: Dict[int, Set[str]] = {}
        for font in font_dict.values():
            if not font.is_embedded:
                font_is_used = False
                base_clean = font.name.split("+")[-1].lower().replace(" ", "").replace("-", "")
                for p_num in font.pages:
                    p_idx = p_num - 1
                    if p_idx not in page_spans_cache:
                        p_spans: Set[str] = set()
                        try:
                            p_dict = fitz_doc[p_idx].get_text("dict", flags=0)
                            for b in p_dict.get("blocks", []):
                                for l in b.get("lines", []):
                                    for s in l.get("spans", []):
                                        f_name = s.get("font", "")
                                        if f_name:
                                            p_spans.add(f_name)
                                            p_spans.add(f_name.split("+")[-1].lower().replace(" ", "").replace("-", ""))
                        except Exception:
                            pass
                        page_spans_cache[p_idx] = p_spans

                    p_spans = page_spans_cache[p_idx]
                    if font.name in p_spans or base_clean in p_spans or any(base_clean in s for s in p_spans):
                        font_is_used = True
                        break
                font.is_used = font_is_used

        return list(font_dict.values())

    def _extract_images(
        self,
        fitz_doc: pymupdf.Document,
        struct_tree: Optional[StructureNode],
        page_artifact_xobjs: Optional[Dict[int, Set[str]]] = None
    ) -> List[ImageModel]:
        """Extracts images and maps them to Structure /Figure elements or Artifacts."""
        images: List[ImageModel] = []
        page_artifact_xobjs = page_artifact_xobjs or {}

        figures_by_page: Dict[int, List[StructureNode]] = {}
        if struct_tree:
            for fn in struct_tree.find_all_by_standard_tag("Figure"):
                p = fn.page or 0
                figures_by_page.setdefault(p, []).append(fn)

        for page_idx in range(len(fitz_doc)):
            page = fitz_doc[page_idx]
            page_num = page_idx + 1
            p_art_xobjs = page_artifact_xobjs.get(page_num, set())

            # Using page.get_images() is ~40x faster than get_image_info() on large files
            page_imgs = page.get_images()
            for img in page_imgs:
                xref = img[0]
                width = img[2] if len(img) > 2 else 0
                height = img[3] if len(img) > 3 else 0
                cs = img[5] if len(img) > 5 else "RGB"
                name = img[7] if len(img) > 7 else ""

                # Check if this image was placed inside an /Artifact marked content sequence
                is_artifact = (name in p_art_xobjs) or str(name).startswith("Fm")

                # Match against Figure structure nodes on this page
                candidate_figs = figures_by_page.get(page_num) or figures_by_page.get(0, [])
                matched_node = candidate_figs[0] if candidate_figs else None

                # If matched to a figure that has alt text, it's not an untagged image
                has_alt = bool(matched_node and (matched_node.alt_text or matched_node.actual_text))
                alt_val = (matched_node.alt_text or matched_node.actual_text or "").strip() if matched_node else ""

                bbox_tuple = (0.0, 0.0, float(width), float(height))
                if matched_node and matched_node.bbox:
                    bbox_tuple = matched_node.bbox
                elif not is_artifact and not has_alt:
                    try:
                        rects = page.get_image_rects(xref)
                        if rects:
                            bbox_tuple = (rects[0].x0, rects[0].y0, rects[0].x1, rects[0].y1)
                    except Exception:
                        pass

                images.append(ImageModel(
                    id=f"img_p{page_num}_{xref}",
                    page=page_num,
                    bbox=bbox_tuple,
                    width=width,
                    height=height,
                    colorspace=cs,
                    has_alt=has_alt,
                    alt_text=alt_val,
                    is_artifact=is_artifact,
                    structure_element_id=matched_node.id if matched_node else None
                ))

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

            page_val = t_node.page
            if page_val is None and t_node.pages_spanned:
                page_val = t_node.pages_spanned[0]
            if page_val is None:
                page_val = 1

            tables.append(TableModel(
                id=f"table_{idx + 1}",
                page=page_val,
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

    def _extract_lists(self, struct_tree: Optional[StructureNode]) -> List[ListModel]:
        """Extracts List (<L>) structural nodes and checks LI / Lbl / LBody nesting."""
        lists: List[ListModel] = []
        if not struct_tree:
            return lists

        list_nodes = struct_tree.find_all_by_standard_tag("L")
        for idx, l_node in enumerate(list_nodes):
            li_nodes = [c for c in l_node.children if c.standard_tag.upper() == "LI"]
            has_labels = False
            # Check Matterhorn Checkpoint 28-001: All direct children of L must be LI or Caption
            is_valid_l = len(l_node.children) > 0 and all(c.standard_tag.upper() in ("LI", "CAPTION") for c in l_node.children)

            # Check Matterhorn Checkpoint 28-002: All direct children of LI must be Lbl and/or LBody
            is_valid_li = True
            for li in li_nodes:
                child_tags = [c.standard_tag.upper() for c in li.children]
                if "LBL" in child_tags:
                    has_labels = True
                if not (len(li.children) > 0 and all(t in ("LBL", "LBODY", "CAPTION") for t in child_tags)):
                    is_valid_li = False

            is_valid = is_valid_l and is_valid_li

            page_val = l_node.page
            if page_val is None and l_node.pages_spanned:
                page_val = l_node.pages_spanned[0]
            if page_val is None:
                page_val = 1

            lists.append(ListModel(
                id=f"list_{idx + 1}",
                page=page_val,
                items_count=len(li_nodes),
                is_valid_structure=is_valid,
                has_labels=has_labels,
                bbox=l_node.bbox
            ))

        return lists

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
                    page_dest += 1

                link_text = page.get_text("text", clip=rect).strip()
                if not link_text and uri:
                    link_text = uri

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
        """Extracts interactive form fields and checks accessible tooltips /TU, including inherited attributes."""
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

                    try:
                        if w.xref and w.xref in pike_doc.objects:
                            annot_obj = pike_doc.objects[w.xref]
                            if "/TU" in annot_obj:
                                tooltip = str(annot_obj["/TU"]).strip()
                            elif "/Parent" in annot_obj:
                                curr = annot_obj["/Parent"]
                                while curr is not None:
                                    if "/TU" in curr:
                                        tooltip = str(curr["/TU"]).strip()
                                        break
                                    curr = curr.get("/Parent", None)
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

    def _extract_annotations(
        self,
        fitz_doc: pymupdf.Document,
        pike_doc: pikepdf.Pdf,
        struct_tree: Optional[StructureNode]
    ) -> List[AnnotationModel]:
        """Extracts all page annotations and checks if they are linked to the structure tree."""
        annots: List[AnnotationModel] = []
        has_link_nodes = bool(struct_tree.find_all_by_standard_tag("Link")) if struct_tree else False
        has_form_nodes = bool(struct_tree.find_all_by_standard_tag("Form")) if struct_tree else False

        for page_idx in range(len(fitz_doc)):
            page = fitz_doc[page_idx]
            page_num = page_idx + 1

            for a in page.annots():
                subtype = a.type[1] if isinstance(a.type, tuple) and len(a.type) > 1 else "Unknown"
                rect = (a.rect.x0, a.rect.y0, a.rect.x1, a.rect.y1)
                struct_parent = None
                is_tagged = False

                # Query pikepdf annotation object
                try:
                    if a.xref and a.xref in pike_doc.objects:
                        annot_obj = pike_doc.objects[a.xref]
                        if "/StructParent" in annot_obj:
                            struct_parent = int(annot_obj["/StructParent"])
                            is_tagged = True
                except Exception:
                    pass

                # If subtype is Link or Widget and struct_tree has link/form
                if not is_tagged:
                    if subtype == "Link" and has_link_nodes:
                        is_tagged = True
                    elif subtype == "Widget" and has_form_nodes:
                        is_tagged = True

                annots.append(AnnotationModel(
                    id=f"annot_p{page_num}_{a.xref}",
                    page=page_num,
                    subtype=subtype,
                    rect=rect,
                    struct_parent=struct_parent,
                    is_tagged=is_tagged,
                    contents=a.info.get("content", "")
                ))

        return annots

    def _extract_bookmarks(self, fitz_doc: pymupdf.Document) -> List[BookmarkModel]:
        """Extracts document table of contents / bookmarks hierarchy."""
        toc = fitz_doc.get_toc()
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
