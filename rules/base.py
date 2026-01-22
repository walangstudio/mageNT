"""Base class for rules."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum


class RuleSeverity(Enum):
    """Rule severity levels."""
    ERROR = "error"      # Must be fixed before proceeding
    WARNING = "warning"  # Should be fixed but not blocking
    INFO = "info"        # Informational only


class RuleCategory(Enum):
    """Rule categories."""
    SECURITY = "security"
    CODING_STYLE = "coding_style"
    TESTING = "testing"
    GIT = "git"
    PERFORMANCE = "performance"


@dataclass
class RuleContext:
    """Context for rule checking."""
    code: Optional[str] = None
    file_path: Optional[str] = None
    file_content: Optional[str] = None
    commit_message: Optional[str] = None
    diff: Optional[str] = None
    project_type: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RuleViolation:
    """A single rule violation."""
    rule_name: str
    message: str
    severity: RuleSeverity
    line_number: Optional[int] = None
    column: Optional[int] = None
    suggestion: Optional[str] = None
    code_snippet: Optional[str] = None


@dataclass
class RuleResult:
    """Result of a rule check."""
    rule_name: str
    passed: bool
    violations: List[RuleViolation] = field(default_factory=list)
    message: Optional[str] = None

    @property
    def has_errors(self) -> bool:
        return any(v.severity == RuleSeverity.ERROR for v in self.violations)

    @property
    def has_warnings(self) -> bool:
        return any(v.severity == RuleSeverity.WARNING for v in self.violations)


class BaseRule(ABC):
    """Abstract base class for all rules.

    Rules are checks that can be run against code, commits, or other
    artifacts to enforce best practices and standards.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for the rule."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of what this rule checks."""
        pass

    @property
    @abstractmethod
    def category(self) -> RuleCategory:
        """Category this rule belongs to."""
        pass

    @property
    def severity(self) -> RuleSeverity:
        """Default severity for violations of this rule."""
        return RuleSeverity.WARNING

    @property
    def enabled(self) -> bool:
        """Whether this rule is enabled by default."""
        return True

    @abstractmethod
    def check(self, context: RuleContext) -> RuleResult:
        """Run the rule check.

        Args:
            context: The context to check against

        Returns:
            RuleResult with pass/fail status and any violations
        """
        pass

    def get_guidance(self) -> str:
        """Get guidance text explaining this rule and how to fix violations."""
        return f"**{self.name}**: {self.description}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert rule to dictionary representation."""
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "severity": self.severity.value,
            "enabled": self.enabled,
        }
