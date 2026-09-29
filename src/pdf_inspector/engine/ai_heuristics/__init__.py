"""AI & Heuristic Intelligence rules."""

from .ai_rules import (
    AIAltTextQualityRule,
    ReadabilityCognitiveRule,
    OutlineSuggestionRule,
)

AI_RULES = [
    AIAltTextQualityRule(),
    ReadabilityCognitiveRule(),
    OutlineSuggestionRule(),
]

__all__ = [
    "AI_RULES",
    "AIAltTextQualityRule",
    "ReadabilityCognitiveRule",
    "OutlineSuggestionRule",
]
