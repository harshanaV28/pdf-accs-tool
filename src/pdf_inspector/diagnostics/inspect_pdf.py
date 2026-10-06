"""
Developer PDF Diagnostic Tool
Parses a PDF file and outputs structured JSON metadata, catalog state,
structure tree nodes, role mappings, and content stream tokens.
"""

import sys
import json
import os
from typing import Dict, Any

# Ensure project root is in sys.path when script is executed directly
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.pdf_inspector.core.document_parser import DocumentParser


def inspect_pdf(filepath: str) -> Dict[str, Any]:
    """Generates structured diagnostic JSON for a given PDF file."""
    if not os.path.exists(filepath):
        return {"error": f"File not found: {filepath}"}

    parser = DocumentParser(filepath)
    doc = parser.parse()

    # Collect structure tree summary
    struct_summary = {
        "has_struct_tree": doc.structure_tree is not None,
        "total_elements": len(doc.structure_tree.find_all_nodes()) if doc.structure_tree else 0,
        "role_map": doc.role_map,
        "parent_tree_entries": doc.parent_tree_entries_count
    }

    # Pages content summary
    pages_summary = []
    for p in doc.pages:
        pages_summary.append({
            "page_number": p.page_number,
            "mcid_count": len(p.mcids),
            "mcids": p.mcids[:20],
            "artifact_count": len(p.artifacts),
            "unmarked_content_count": p.unmarked_real_content_count,
            "tagged_in_artifact_count": p.tagged_in_artifact_count,
            "artifact_in_tagged_count": p.artifact_in_tagged_count,
            "tab_order": p.tab_order_mode,
            "has_struct_parents": p.struct_parents_id is not None
        })

    return {
        "document": {
            "filename": doc.filename,
            "filesize": doc.filesize,
            "pdf_version": doc.pdf_version,
            "page_count": doc.page_count,
            "is_tagged": doc.is_tagged,
            "is_encrypted": doc.is_encrypted,
            "allows_extraction": doc.allows_extraction,
            "language": doc.language
        },
        "metadata": {
            "legacy_info_title": doc.doc_info_title,
            "legacy_info_author": doc.doc_info_author,
            "legacy_info_subject": doc.doc_info_subject,
            "xmp_metadata_present": doc.xmp_metadata_present,
            "xmp_dc_title": doc.xmp_dc_title,
            "xmp_dc_creator": doc.xmp_dc_creator,
            "xmp_dc_description": doc.xmp_dc_description,
            "pdfua_identifier_present": doc.pdfua_identifier_present,
            "pdfua_part": doc.pdfua_part
        },
        "viewer_preferences": {
            "display_doc_title": doc.display_doc_title
        },
        "structure": struct_summary,
        "pages": pages_summary
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m src.pdf_inspector.diagnostics.inspect_pdf <file.pdf>")
        sys.exit(1)

    filepath = sys.argv[1]
    result = inspect_pdf(filepath)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
