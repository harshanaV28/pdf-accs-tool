"""Quality & Ergonomics checks."""

from .quality_rules import (
    HeadingHierarchyQualityRule,
    StructureQualityRule,
    TableRegularityQualityRule,
    LinkQualityRule,
)

QUALITY_RULES = [
    HeadingHierarchyQualityRule(),
    StructureQualityRule(),
    TableRegularityQualityRule(),
    LinkQualityRule(),
]

__all__ = [
    "QUALITY_RULES",
    "HeadingHierarchyQualityRule",
    "StructureQualityRule",
    "TableRegularityQualityRule",
    "LinkQualityRule",
]
