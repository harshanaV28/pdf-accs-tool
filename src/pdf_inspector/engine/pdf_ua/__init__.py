"""PDF/UA ISO 14289-1 rule implementations."""

from .syntax_rules import PDFSyntaxBasicRule
from .font_rules import FontEmbeddingRule, FontToUnicodeRule
from .content_rules import TaggedPDFRule, ContentTaggedRule
from .embedded_files_rules import EmbeddedFilesAccessibilityRule
from .language_rules import DocumentLanguageRule, StructureLanguageRule
from .structure_rules import StructureTreeIntegrityRule, StructureNestingRule, EmptyStructureElementsRule
from .role_map_rules import RoleMappingValidityRule
from .alt_text_rules import FigureAlternativeTextRule
from .metadata_rules import MetadataCompletenessRule
from .document_settings_rules import DisplayDocTitleRule

PDF_UA_RULES = [
    PDFSyntaxBasicRule(),
    FontEmbeddingRule(),
    FontToUnicodeRule(),
    TaggedPDFRule(),
    ContentTaggedRule(),
    EmbeddedFilesAccessibilityRule(),
    DocumentLanguageRule(),
    StructureLanguageRule(),
    StructureTreeIntegrityRule(),
    StructureNestingRule(),
    EmptyStructureElementsRule(),
    RoleMappingValidityRule(),
    FigureAlternativeTextRule(),
    MetadataCompletenessRule(),
    DisplayDocTitleRule(),
]

__all__ = [
    "PDF_UA_RULES",
    "PDFSyntaxBasicRule",
    "FontEmbeddingRule",
    "FontToUnicodeRule",
    "TaggedPDFRule",
    "ContentTaggedRule",
    "EmbeddedFilesAccessibilityRule",
    "DocumentLanguageRule",
    "StructureLanguageRule",
    "StructureTreeIntegrityRule",
    "StructureNestingRule",
    "EmptyStructureElementsRule",
    "RoleMappingValidityRule",
    "FigureAlternativeTextRule",
    "MetadataCompletenessRule",
    "DisplayDocTitleRule",
]
