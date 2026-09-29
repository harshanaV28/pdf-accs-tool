"""Quality & Ergonomics checks."""

from .quality_rules import (
    HeadingHierarchyQualityRule,
    TableRegularityQualityRule,
    LinkQualityRule,
)

QUALITY_RULES = [
    HeadingHierarchyQualityRule(),
    TableRegularityQualityRule(),
    LinkQualityRule(),
]

__all__ = [
    "QUALITY_RULES",
    "HeadingHierarchyQualityRule",
    "TableRegularityQualityRule",
    "LinkQualityRule",
]
