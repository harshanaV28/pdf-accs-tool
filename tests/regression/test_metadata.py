"""
Regression tests for Metadata Rules:
- XMP Metadata stream presence (PDFUA-META-001)
- Dublin Core Title in XMP vs Legacy Info Dictionary (PDFUA-META-002)
- PDF/UA Identifier in XMP (PDFUA-META-003)
- DisplayDocTitle setting (PDFUA-SETTINGS-001)
"""

import pytest
from src.pdf_inspector.core.models import PDFDocumentModel, CheckStatus
from src.pdf_inspector.engine.pdf_ua.metadata_rules import (
    XMPMetadataStreamRule,
    XMPDocumentTitleRule,
    PDFUAIdentifierRule,
    MetadataCompletenessRule,
)
from src.pdf_inspector.engine.pdf_ua.document_settings_rules import DisplayDocTitleRule


class TestMetadataRegression:
    def test_xmp_stream_presence(self):
        rule = XMPMetadataStreamRule()

        # Case 1: No XMP stream present
        doc_no_xmp = PDFDocumentModel(
            filepath="", filename="no_xmp.pdf", filesize=100, pdf_version="1.7",
            page_count=1, xmp_metadata_present=False
        )
        res = rule.evaluate(doc_no_xmp)
        assert len(res) == 1
        assert res[0].status == CheckStatus.FAIL
        assert "No XMP metadata stream found" in res[0].message

        # Case 2: XMP stream present
        doc_with_xmp = PDFDocumentModel(
            filepath="", filename="xmp.pdf", filesize=100, pdf_version="1.7",
            page_count=1, xmp_metadata_present=True
        )
        res2 = rule.evaluate(doc_with_xmp)
        assert len(res2) == 1
        assert res2[0].status == CheckStatus.PASS

    def test_dublin_core_title_vs_legacy_info(self):
        """
        Critical rule: ISO 14289-1 Clause 7.9 requires title in XMP dc:title.
        Legacy /Info /Title CANNOT satisfy this requirement.
        """
        rule = XMPDocumentTitleRule()

        # Case 1: Legacy /Info /Title exists, but XMP dc:title is missing -> MUST FAIL
        doc_legacy_only = PDFDocumentModel(
            filepath="", filename="legacy.pdf", filesize=100, pdf_version="1.7",
            page_count=1, xmp_metadata_present=True,
            doc_info_title="Legacy Document Title",
            xmp_dc_title=None,
            title="Legacy Document Title"
        )
        res_legacy = rule.evaluate(doc_legacy_only)
        assert len(res_legacy) == 1
        assert res_legacy[0].status == CheckStatus.FAIL
        assert "Legacy DocumentInfo /Title" in res_legacy[0].evidence or "XMP" in res_legacy[0].message

        # Case 2: XMP dc:title is whitespace only -> MUST FAIL
        doc_empty_xmp = PDFDocumentModel(
            filepath="", filename="empty_title.pdf", filesize=100, pdf_version="1.7",
            page_count=1, xmp_metadata_present=True,
            xmp_dc_title="   ",
            title="   "
        )
        res_empty = rule.evaluate(doc_empty_xmp)
        assert len(res_empty) == 1
        assert res_empty[0].status == CheckStatus.FAIL

        # Case 3: XMP dc:title is present and valid -> PASS
        doc_valid_xmp = PDFDocumentModel(
            filepath="", filename="valid_title.pdf", filesize=100, pdf_version="1.7",
            page_count=1, xmp_metadata_present=True,
            doc_info_title="Legacy Title",
            xmp_dc_title="Annual Accessibility Compliance Report",
            title="Annual Accessibility Compliance Report"
        )
        res_valid = rule.evaluate(doc_valid_xmp)
        assert len(res_valid) == 1
        assert res_valid[0].status == CheckStatus.PASS
        assert "Annual Accessibility Compliance Report" in res_valid[0].message

    def test_pdfua_identifier_rule(self):
        rule = PDFUAIdentifierRule()

        # Case 1: Missing PDF/UA identifier
        doc_no_id = PDFDocumentModel(
            filepath="", filename="no_id.pdf", filesize=100, pdf_version="1.7",
            page_count=1, xmp_metadata_present=True,
            pdfua_identifier_present=False
        )
        res1 = rule.evaluate(doc_no_id)
        assert len(res1) == 1
        assert res1[0].status == CheckStatus.FAIL
        assert "pdfaProperty" in res1[0].message or "pdfuaid:part" in res1[0].message

        # Case 2: Present PDF/UA identifier
        doc_with_id = PDFDocumentModel(
            filepath="", filename="with_id.pdf", filesize=100, pdf_version="1.7",
            page_count=1, xmp_metadata_present=True,
            pdfua_identifier_present=True,
            pdfua_part=1
        )
        res2 = rule.evaluate(doc_with_id)
        assert len(res2) == 1
        assert res2[0].status == CheckStatus.PASS
        assert "Part 1" in res2[0].message

    def test_display_doc_title_rule(self):
        rule = DisplayDocTitleRule()

        # Case 1: DisplayDocTitle is False
        doc_false = PDFDocumentModel(
            filepath="", filename="false_title.pdf", filesize=100, pdf_version="1.7",
            page_count=1, display_doc_title=False
        )
        res1 = rule.evaluate(doc_false)
        assert any(r.status == CheckStatus.FAIL and "DisplayDocTitle" in r.message for r in res1)

        # Case 2: DisplayDocTitle is True
        doc_true = PDFDocumentModel(
            filepath="", filename="true_title.pdf", filesize=100, pdf_version="1.7",
            page_count=1, display_doc_title=True
        )
        res2 = rule.evaluate(doc_true)
        assert any(r.status == CheckStatus.PASS and "DisplayDocTitle" in r.message for r in res2)
