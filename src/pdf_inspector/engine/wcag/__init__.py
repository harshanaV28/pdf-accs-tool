"""WCAG 2.1 / 2.2 AA rules."""

from .wcag_rules import (
    WCAGTextAlternativesRule,
    WCAGTimeBasedMediaRule,
    WCAGAdaptableRule,
    WCAGDistinguishableRule,
    WCAGKeyboardAccessibleRule,
    WCAGEnoughTimeRule,
    WCAGSeizuresRule,
    WCAGNavigableRule,
    WCAGInputModalitiesRule,
    WCAGReadableRule,
    WCAGPredictableRule,
    WCAGInputAssistanceRule,
    WCAGCompatibleRule,
)

WCAG_RULES = [
    WCAGTextAlternativesRule(),
    WCAGTimeBasedMediaRule(),
    WCAGAdaptableRule(),
    WCAGDistinguishableRule(),
    WCAGKeyboardAccessibleRule(),
    WCAGEnoughTimeRule(),
    WCAGSeizuresRule(),
    WCAGNavigableRule(),
    WCAGInputModalitiesRule(),
    WCAGReadableRule(),
    WCAGPredictableRule(),
    WCAGInputAssistanceRule(),
    WCAGCompatibleRule(),
]

__all__ = [
    "WCAG_RULES",
    "WCAGTextAlternativesRule",
    "WCAGTimeBasedMediaRule",
    "WCAGAdaptableRule",
    "WCAGDistinguishableRule",
    "WCAGKeyboardAccessibleRule",
    "WCAGEnoughTimeRule",
    "WCAGSeizuresRule",
    "WCAGNavigableRule",
    "WCAGInputModalitiesRule",
    "WCAGReadableRule",
    "WCAGPredictableRule",
    "WCAGInputAssistanceRule",
    "WCAGCompatibleRule",
]
