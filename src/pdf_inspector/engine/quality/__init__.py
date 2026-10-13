"""Quality & Ergonomics checks."""

from .quality_rules import (
    HeadingHierarchyQualityRule,
    StructureQualityRule,
    TableRegularityQualityRule,
    LinkQualityRule,
    TaggedContentPageBoundariesRule,
    TOCIContainsLinkRule,
    TOCILinkDestinationRule,
    TextElementAltTextQualityRule,
    NoteReferencedQualityRule,
    NoteContainsLabelQualityRule,
    ParagraphContainsNoteQualityRule,
    ArtifactedContentOnPageBodyRule,
    LinkCompletenessQualityRule,
    TaggedTextOnlyWhitespaceQualityRule,
)

QUALITY_RULES = [
    HeadingHierarchyQualityRule(),
    StructureQualityRule(),
    TableRegularityQualityRule(),
    LinkQualityRule(),
    TaggedContentPageBoundariesRule(),
    TOCIContainsLinkRule(),
    TOCILinkDestinationRule(),
    TextElementAltTextQualityRule(),
    NoteReferencedQualityRule(),
    NoteContainsLabelQualityRule(),
    ParagraphContainsNoteQualityRule(),
    ArtifactedContentOnPageBodyRule(),
    LinkCompletenessQualityRule(),
    TaggedTextOnlyWhitespaceQualityRule(),
]

__all__ = [
    "QUALITY_RULES",
    "HeadingHierarchyQualityRule",
    "StructureQualityRule",
    "TableRegularityQualityRule",
    "LinkQualityRule",
    "TaggedContentPageBoundariesRule",
    "TOCIContainsLinkRule",
    "TOCILinkDestinationRule",
    "TextElementAltTextQualityRule",
    "NoteReferencedQualityRule",
    "NoteContainsLabelQualityRule",
    "ParagraphContainsNoteQualityRule",
    "ArtifactedContentOnPageBodyRule",
    "LinkCompletenessQualityRule",
    "TaggedTextOnlyWhitespaceQualityRule",
]
