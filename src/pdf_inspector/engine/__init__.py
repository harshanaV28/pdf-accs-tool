"""PDF Accessibility Inspector Rule Engine."""

from .rule_base import BaseRule
from .runner import AuditRunner
from .pdf_ua import PDF_UA_RULES
from .wcag import WCAG_RULES
from .quality import QUALITY_RULES
from .ai_heuristics import AI_RULES

__all__ = [
    "BaseRule",
    "AuditRunner",
    "PDF_UA_RULES",
    "WCAG_RULES",
    "QUALITY_RULES",
    "AI_RULES",
]
