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
]
