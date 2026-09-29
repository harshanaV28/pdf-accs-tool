"""
Rule Base & Registry
Defines the abstract interface for all accessibility rules across standards.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Tuple, Any
from ..core.models import PDFDocumentModel, CheckResult, CheckStatus, Severity


class BaseRule(ABC):
    """Abstract base class for all accessibility checking rules."""

    rule_id: str = "RULE-000"
    name: str = "Base Rule"
    category: str = "General"
    standard: str = "PDF/UA"  # "PDF/UA", "WCAG", "Quality", "AI"
    severity: Severity = Severity.MEDIUM
    description: str = ""
    remediation_template: str = ""
    machine_testable: bool = True

    @abstractmethod
    def evaluate(self, doc: PDFDocumentModel) -> List[CheckResult]:
        """Evaluates this rule against the parsed document model and returns check results."""
        pass

    def create_result(
        self,
        status: CheckStatus,
        message: str,
        evidence: str = "",
        page: Optional[int] = None,
        bounding_box: Optional[Tuple[float, float, float, float]] = None,
        object_reference: str = "",
        custom_severity: Optional[Severity] = None,
        custom_remediation: Optional[str] = None,
        confidence: float = 1.0,
        manual_review_required: bool = False
    ) -> CheckResult:
        """Convenience factory for creating a structured CheckResult."""
        return CheckResult(
            check_id=self.rule_id,
            name=self.name,
            category=self.category,
            standard=self.standard,
            status=status,
            severity=custom_severity or self.severity,
            message=message,
            description=self.description,
            evidence=evidence,
            page=page,
            bounding_box=bounding_box,
            object_reference=object_reference,
            remediation=custom_remediation or self.remediation_template,
            confidence=confidence,
            machine_testable=self.machine_testable and not manual_review_required,
            manual_review_required=manual_review_required or (status == CheckStatus.MANUAL_REVIEW)
        )
