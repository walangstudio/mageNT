"""Validation hooks for code quality and security."""

from typing import Optional, List
from ..base import (
    BaseHook,
    HookContext,
    HookResult,
    HookType,
    HookPriority,
)


class ValidateCodeBeforeEditHook(BaseHook):
    """Validate code changes before they are applied."""

    @property
    def name(self) -> str:
        return "validate-code-before-edit"

    @property
    def description(self) -> str:
        return "Validates code changes against rules before applying edits"

    @property
    def hook_type(self) -> HookType:
        return HookType.PRE_EDIT

    @property
    def priority(self) -> HookPriority:
        return HookPriority.HIGH

    async def execute(self, context: HookContext) -> HookResult:
        """Validate the new code against rules."""
        new_content = context.new_content
        file_path = context.file_path

        if not new_content:
            return HookResult.success()

        # Import here to avoid circular imports
        from rules import RulesEngine, RuleContext, RuleCategory

        # Create rules engine with relevant categories
        engine = RulesEngine()

        # Build rule context
        rule_context = RuleContext(
            code=new_content,
            file_path=file_path,
            file_content=new_content,
            metadata={
                "old_content": context.old_content,
                "is_edit": True,
            },
        )

        # Run checks
        report = engine.check(rule_context)

        if report.has_errors:
            # Block the edit with error details
            error_messages = []
            for result in report.results:
                for violation in result.violations:
                    if violation.severity.value == "error":
                        error_messages.append(f"- {violation.message}")
                        if violation.suggestion:
                            error_messages.append(f"  Fix: {violation.suggestion}")

            return HookResult.failure(
                message=f"Code validation failed with {report.violations_by_severity.get('error', 0)} errors:\n"
                + "\n".join(error_messages[:5])  # Limit to first 5
            )

        if report.has_warnings:
            # Allow but warn
            warning_count = report.violations_by_severity.get("warning", 0)
            return HookResult.success(
                message=f"Code validation passed with {warning_count} warnings. Consider reviewing.",
                warnings=warning_count,
            )

        return HookResult.success()


class CheckSecurityHook(BaseHook):
    """Check for security issues in code."""

    @property
    def name(self) -> str:
        return "check-security"

    @property
    def description(self) -> str:
        return "Checks code for security vulnerabilities (secrets, injection, etc.)"

    @property
    def hook_type(self) -> HookType:
        return HookType.PRE_COMMIT

    @property
    def priority(self) -> HookPriority:
        return HookPriority.HIGHEST

    async def execute(self, context: HookContext) -> HookResult:
        """Check for security issues before commit."""
        # This hook is primarily informational - it provides guidance
        # to the calling LLM about security best practices

        file_content = context.file_content or context.new_content
        if not file_content:
            return HookResult.success()

        from rules import RulesEngine, RuleContext, RulesConfig, RuleCategory

        # Only run security rules
        config = RulesConfig(
            enabled_categories={RuleCategory.SECURITY},
            fail_on_warnings=True,  # Security warnings should be treated seriously
        )
        engine = RulesEngine(config)

        rule_context = RuleContext(
            code=file_content,
            file_path=context.file_path,
            file_content=file_content,
            metadata={
                "commit_message": context.commit_message,
                "is_commit": True,
            },
        )

        report = engine.check(rule_context)

        if not report.passed:
            issues = []
            for result in report.results:
                for violation in result.violations:
                    issues.append(f"- [{violation.rule_name}] {violation.message}")

            return HookResult.failure(
                message="Security check failed:\n" + "\n".join(issues[:5]),
                security_issues=issues,
            )

        return HookResult.success(message="Security check passed")


class PreCommitValidationHook(BaseHook):
    """Run validation before git commit."""

    @property
    def name(self) -> str:
        return "pre-commit-validation"

    @property
    def description(self) -> str:
        return "Validates code quality and commit message format before committing"

    @property
    def hook_type(self) -> HookType:
        return HookType.PRE_COMMIT

    @property
    def priority(self) -> HookPriority:
        return HookPriority.NORMAL

    async def execute(self, context: HookContext) -> HookResult:
        """Validate before commit."""
        results = []
        has_blocking_issues = False

        # Check commit message format
        if context.commit_message:
            from rules import RulesEngine, RuleContext, RulesConfig, RuleCategory

            config = RulesConfig(enabled_categories={RuleCategory.GIT})
            engine = RulesEngine(config)

            rule_context = RuleContext(
                metadata={
                    "commit_message": context.commit_message,
                    "branch_name": context.branch_name,
                },
            )

            report = engine.check(rule_context)

            if not report.passed:
                for result in report.results:
                    for violation in result.violations:
                        results.append(f"- {violation.message}")
                        if violation.severity.value == "error":
                            has_blocking_issues = True

        if has_blocking_issues:
            return HookResult.failure(
                message="Pre-commit validation failed:\n" + "\n".join(results)
            )

        if results:
            return HookResult.success(
                message="Pre-commit validation passed with suggestions:\n" + "\n".join(results)
            )

        return HookResult.success(message="Pre-commit validation passed")
