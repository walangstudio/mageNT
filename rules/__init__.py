"""
Rules Engine for mageNT.

Provides a comprehensive rules system for code validation and best practices.
Rules can be enabled/disabled and configured via settings.
"""

from typing import Dict, List, Optional, Set, Type, Any
from dataclasses import dataclass, field
from enum import Enum

from .base import (
    BaseRule,
    RuleCategory,
    RuleContext,
    RuleResult,
    RuleSeverity,
    RuleViolation,
)
from .security import SECURITY_RULES
from .coding_style import CODING_STYLE_RULES
from .testing import TESTING_RULES
from .git_workflow import GIT_WORKFLOW_RULES
from .performance import PERFORMANCE_RULES


@dataclass
class RulesConfig:
    """Configuration for the rules engine."""

    # Enabled rule categories
    enabled_categories: Set[RuleCategory] = field(
        default_factory=lambda: {cat for cat in RuleCategory}
    )

    # Explicitly disabled rules by name
    disabled_rules: Set[str] = field(default_factory=set)

    # Explicitly enabled rules (overrides category disable)
    enabled_rules: Set[str] = field(default_factory=set)

    # Minimum severity to report
    min_severity: RuleSeverity = RuleSeverity.INFO

    # Rule-specific configurations
    rule_configs: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # Whether to fail on warnings
    fail_on_warnings: bool = False


@dataclass
class RulesReport:
    """Complete report from rules engine evaluation."""

    passed: bool
    total_rules_checked: int
    violations_by_severity: Dict[RuleSeverity, int]
    violations_by_category: Dict[RuleCategory, int]
    results: List[RuleResult]

    @property
    def total_violations(self) -> int:
        return sum(self.violations_by_severity.values())

    @property
    def has_errors(self) -> bool:
        return self.violations_by_severity.get(RuleSeverity.ERROR, 0) > 0

    @property
    def has_warnings(self) -> bool:
        return self.violations_by_severity.get(RuleSeverity.WARNING, 0) > 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary for JSON serialization."""
        return {
            "passed": self.passed,
            "total_rules_checked": self.total_rules_checked,
            "total_violations": self.total_violations,
            "violations_by_severity": {
                sev.value: count for sev, count in self.violations_by_severity.items()
            },
            "violations_by_category": {
                cat.value: count for cat, count in self.violations_by_category.items()
            },
            "results": [
                {
                    "rule_name": r.rule_name,
                    "passed": r.passed,
                    "message": r.message,
                    "violations": [
                        {
                            "rule_name": v.rule_name,
                            "message": v.message,
                            "severity": v.severity.value,
                            "line_number": v.line_number,
                            "column": v.column,
                            "suggestion": v.suggestion,
                            "code_snippet": v.code_snippet,
                        }
                        for v in r.violations
                    ],
                }
                for r in self.results
                if not r.passed
            ],
        }

    def format_text(self) -> str:
        """Format report as human-readable text."""
        lines = []
        lines.append("=" * 60)
        lines.append("RULES VALIDATION REPORT")
        lines.append("=" * 60)
        lines.append(f"Status: {'✓ PASSED' if self.passed else '✗ FAILED'}")
        lines.append(f"Rules checked: {self.total_rules_checked}")
        lines.append(f"Total violations: {self.total_violations}")
        lines.append("")

        if self.total_violations > 0:
            lines.append("Violations by severity:")
            for sev in [RuleSeverity.ERROR, RuleSeverity.WARNING, RuleSeverity.INFO]:
                count = self.violations_by_severity.get(sev, 0)
                if count > 0:
                    icon = "✗" if sev == RuleSeverity.ERROR else "⚠" if sev == RuleSeverity.WARNING else "ℹ"
                    lines.append(f"  {icon} {sev.value}: {count}")

            lines.append("")
            lines.append("-" * 60)
            lines.append("VIOLATIONS:")
            lines.append("-" * 60)

            for result in self.results:
                if not result.passed:
                    for violation in result.violations:
                        icon = "✗" if violation.severity == RuleSeverity.ERROR else "⚠" if violation.severity == RuleSeverity.WARNING else "ℹ"
                        location = f":{violation.line_number}" if violation.line_number else ""
                        lines.append(f"\n{icon} [{violation.rule_name}]{location}")
                        lines.append(f"   {violation.message}")
                        if violation.code_snippet:
                            lines.append(f"   Code: {violation.code_snippet}")
                        if violation.suggestion:
                            lines.append(f"   Fix: {violation.suggestion}")

        lines.append("")
        lines.append("=" * 60)
        return "\n".join(lines)


class RulesEngine:
    """
    Main rules engine that coordinates rule execution.

    The RulesEngine is designed to work with ANY LLM that calls the MCP server.
    It returns validation results and guidance that the calling LLM can use
    to improve code quality.
    """

    # All available rules organized by category
    ALL_RULES: Dict[RuleCategory, List[Type[BaseRule]]] = {
        RuleCategory.SECURITY: SECURITY_RULES,
        RuleCategory.CODING_STYLE: CODING_STYLE_RULES,
        RuleCategory.TESTING: TESTING_RULES,
        RuleCategory.GIT: GIT_WORKFLOW_RULES,
        RuleCategory.PERFORMANCE: PERFORMANCE_RULES,
    }

    def __init__(self, config: Optional[RulesConfig] = None):
        """Initialize the rules engine with optional configuration."""
        self.config = config or RulesConfig()
        self._rule_instances: Dict[str, BaseRule] = {}
        self._initialize_rules()

    def _initialize_rules(self) -> None:
        """Initialize rule instances based on configuration."""
        for category, rule_classes in self.ALL_RULES.items():
            for rule_class in rule_classes:
                # Get rule-specific config if any
                rule_config = self.config.rule_configs.get(rule_class.__name__, {})

                # Create instance
                try:
                    rule = rule_class(**rule_config) if rule_config else rule_class()
                    self._rule_instances[rule.name] = rule
                except Exception as e:
                    # Log error but continue
                    print(f"Warning: Failed to initialize rule {rule_class.__name__}: {e}")

    # Severity ordering for comparison (higher number = more severe)
    SEVERITY_ORDER = {
        RuleSeverity.INFO: 0,
        RuleSeverity.WARNING: 1,
        RuleSeverity.ERROR: 2,
    }

    def get_enabled_rules(self) -> List[BaseRule]:
        """Get list of enabled rules based on configuration."""
        enabled = []

        for rule in self._rule_instances.values():
            # Check if explicitly disabled
            if rule.name in self.config.disabled_rules:
                if rule.name not in self.config.enabled_rules:
                    continue

            # Check if category is enabled
            if rule.category not in self.config.enabled_categories:
                if rule.name not in self.config.enabled_rules:
                    continue

            # Check severity threshold (use numeric ordering, not string comparison)
            rule_severity_level = self.SEVERITY_ORDER.get(rule.severity, 0)
            min_severity_level = self.SEVERITY_ORDER.get(self.config.min_severity, 0)
            if rule_severity_level < min_severity_level:
                continue

            enabled.append(rule)

        return enabled

    def check(self, context: RuleContext) -> RulesReport:
        """
        Run all enabled rules against the provided context.

        Args:
            context: The rule context containing code, file info, and metadata

        Returns:
            RulesReport with all results
        """
        results = []
        violations_by_severity: Dict[RuleSeverity, int] = {sev: 0 for sev in RuleSeverity}
        violations_by_category: Dict[RuleCategory, int] = {cat: 0 for cat in RuleCategory}

        enabled_rules = self.get_enabled_rules()

        for rule in enabled_rules:
            try:
                result = rule.check(context)
                results.append(result)

                # Count violations
                for violation in result.violations:
                    violations_by_severity[violation.severity] += 1
                    violations_by_category[rule.category] += 1

            except Exception as e:
                # Rule failed to execute - report as error
                results.append(
                    RuleResult(
                        rule_name=rule.name,
                        passed=False,
                        violations=[
                            RuleViolation(
                                rule_name=rule.name,
                                message=f"Rule execution failed: {str(e)}",
                                severity=RuleSeverity.ERROR,
                            )
                        ],
                        message=f"Rule execution error: {str(e)}",
                    )
                )
                violations_by_severity[RuleSeverity.ERROR] += 1
                violations_by_category[rule.category] += 1

        # Determine overall pass/fail
        has_errors = violations_by_severity[RuleSeverity.ERROR] > 0
        has_warnings = violations_by_severity[RuleSeverity.WARNING] > 0

        passed = not has_errors
        if self.config.fail_on_warnings and has_warnings:
            passed = False

        return RulesReport(
            passed=passed,
            total_rules_checked=len(enabled_rules),
            violations_by_severity=violations_by_severity,
            violations_by_category=violations_by_category,
            results=results,
        )

    def check_code(
        self,
        code: str,
        file_path: Optional[str] = None,
        **metadata
    ) -> RulesReport:
        """
        Convenience method to check code string.

        Args:
            code: The code to check
            file_path: Optional file path for context
            **metadata: Additional metadata (commit_message, branch_name, etc.)

        Returns:
            RulesReport with all results
        """
        context = RuleContext(
            code=code,
            file_path=file_path,
            file_content=code,
            metadata=metadata,
        )
        return self.check(context)

    def get_rule(self, rule_name: str) -> Optional[BaseRule]:
        """Get a specific rule by name."""
        return self._rule_instances.get(rule_name)

    def get_guidance(self, rule_name: str) -> Optional[str]:
        """Get guidance text for a specific rule."""
        rule = self.get_rule(rule_name)
        return rule.get_guidance() if rule else None

    def get_all_guidance(self) -> Dict[str, str]:
        """Get guidance for all enabled rules."""
        return {
            rule.name: rule.get_guidance()
            for rule in self.get_enabled_rules()
        }

    def list_rules(self) -> Dict[str, Dict[str, Any]]:
        """List all available rules with their metadata."""
        rules_info = {}

        for rule in self._rule_instances.values():
            enabled = (
                rule.category in self.config.enabled_categories
                and rule.name not in self.config.disabled_rules
            ) or rule.name in self.config.enabled_rules

            rules_info[rule.name] = {
                "name": rule.name,
                "description": rule.description,
                "category": rule.category.value,
                "severity": rule.severity.value,
                "enabled": enabled,
            }

        return rules_info


# Convenience function for quick checks
def check_code(
    code: str,
    file_path: Optional[str] = None,
    categories: Optional[List[str]] = None,
    **metadata
) -> RulesReport:
    """
    Quick function to check code against rules.

    Args:
        code: The code to check
        file_path: Optional file path
        categories: Optional list of category names to enable
        **metadata: Additional metadata

    Returns:
        RulesReport
    """
    config = RulesConfig()

    if categories:
        config.enabled_categories = {
            RuleCategory(cat) for cat in categories if cat in [c.value for c in RuleCategory]
        }

    engine = RulesEngine(config)
    return engine.check_code(code, file_path, **metadata)


# Export public interface
__all__ = [
    # Core classes
    "RulesEngine",
    "RulesConfig",
    "RulesReport",
    # Base types
    "BaseRule",
    "RuleCategory",
    "RuleContext",
    "RuleResult",
    "RuleSeverity",
    "RuleViolation",
    # Convenience function
    "check_code",
    # Rule collections
    "SECURITY_RULES",
    "CODING_STYLE_RULES",
    "TESTING_RULES",
    "GIT_WORKFLOW_RULES",
    "PERFORMANCE_RULES",
]
