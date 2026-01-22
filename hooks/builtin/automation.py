"""Automation hooks for development workflow."""

import re
from typing import Optional, List, Dict, Any
from ..base import (
    BaseHook,
    HookContext,
    HookResult,
    HookType,
    HookPriority,
)


class AutoFormatHook(BaseHook):
    """Suggest or apply automatic code formatting."""

    # File extensions and their formatters
    FORMATTERS: Dict[str, Dict[str, Any]] = {
        ".py": {
            "name": "black/ruff",
            "command": "black {file} or ruff format {file}",
            "check": r"^\s{4}",  # Check for consistent indentation
        },
        ".js": {
            "name": "prettier",
            "command": "prettier --write {file}",
            "check": r";\s*$",  # Check for semicolons
        },
        ".ts": {
            "name": "prettier",
            "command": "prettier --write {file}",
            "check": r";\s*$",
        },
        ".jsx": {"name": "prettier", "command": "prettier --write {file}"},
        ".tsx": {"name": "prettier", "command": "prettier --write {file}"},
        ".json": {"name": "prettier", "command": "prettier --write {file}"},
        ".go": {"name": "gofmt", "command": "gofmt -w {file}"},
        ".rs": {"name": "rustfmt", "command": "rustfmt {file}"},
    }

    @property
    def name(self) -> str:
        return "auto-format"

    @property
    def description(self) -> str:
        return "Suggests code formatting commands for edited files"

    @property
    def hook_type(self) -> HookType:
        return HookType.POST_EDIT

    @property
    def priority(self) -> HookPriority:
        return HookPriority.LOW

    async def execute(self, context: HookContext) -> HookResult:
        """Suggest formatting for the edited file."""
        file_path = context.file_path

        if not file_path:
            return HookResult.success()

        # Find matching formatter
        for ext, formatter in self.FORMATTERS.items():
            if file_path.endswith(ext):
                command = formatter["command"].replace("{file}", file_path)
                return HookResult.success(
                    message=f"Consider running formatter: {command}",
                    formatter=formatter["name"],
                    command=command,
                    file_extension=ext,
                )

        return HookResult.success()


class AutoTestHook(BaseHook):
    """Suggest running tests after code changes."""

    # Test file patterns and commands
    TEST_CONFIGS: Dict[str, Dict[str, Any]] = {
        "python": {
            "source_pattern": r"\.py$",
            "test_patterns": [r"test_.*\.py$", r".*_test\.py$"],
            "commands": ["pytest", "python -m pytest"],
            "package_indicator": "pytest.ini|pyproject.toml|setup.py",
        },
        "javascript": {
            "source_pattern": r"\.(js|jsx)$",
            "test_patterns": [r".*\.test\.(js|jsx)$", r".*\.spec\.(js|jsx)$"],
            "commands": ["npm test", "yarn test", "jest"],
            "package_indicator": "package.json",
        },
        "typescript": {
            "source_pattern": r"\.(ts|tsx)$",
            "test_patterns": [r".*\.test\.(ts|tsx)$", r".*\.spec\.(ts|tsx)$"],
            "commands": ["npm test", "yarn test", "jest", "vitest"],
            "package_indicator": "package.json|tsconfig.json",
        },
        "go": {
            "source_pattern": r"\.go$",
            "test_patterns": [r".*_test\.go$"],
            "commands": ["go test ./..."],
            "package_indicator": "go.mod",
        },
        "rust": {
            "source_pattern": r"\.rs$",
            "test_patterns": [],  # Tests are in same files
            "commands": ["cargo test"],
            "package_indicator": "Cargo.toml",
        },
    }

    def __init__(self, auto_suggest: bool = True):
        self._auto_suggest = auto_suggest
        self._changed_files: List[str] = []

    @property
    def name(self) -> str:
        return "auto-test"

    @property
    def description(self) -> str:
        return "Suggests running relevant tests after code changes"

    @property
    def hook_type(self) -> HookType:
        return HookType.POST_EDIT

    @property
    def priority(self) -> HookPriority:
        return HookPriority.LOW

    async def execute(self, context: HookContext) -> HookResult:
        """Suggest tests to run."""
        file_path = context.file_path

        if not file_path:
            return HookResult.success()

        # Track changed file
        if file_path not in self._changed_files:
            self._changed_files.append(file_path)

        # Detect project type and suggest tests
        for lang, config in self.TEST_CONFIGS.items():
            if re.search(config["source_pattern"], file_path):
                # Check if this is a test file
                is_test_file = any(
                    re.search(pattern, file_path)
                    for pattern in config.get("test_patterns", [])
                )

                suggestions = []

                if is_test_file:
                    # Run this specific test
                    suggestions.append(f"Run this test: {file_path}")
                else:
                    # Suggest running related tests
                    test_file = self._find_test_file(file_path, config)
                    if test_file:
                        suggestions.append(f"Run related test: {test_file}")

                # Always suggest running all tests
                for cmd in config["commands"][:2]:  # Limit to 2 suggestions
                    suggestions.append(f"Run all tests: {cmd}")

                if suggestions:
                    return HookResult.success(
                        message="Consider running tests:\n- " + "\n- ".join(suggestions),
                        language=lang,
                        suggestions=suggestions,
                        changed_file=file_path,
                    )

        return HookResult.success()

    def _find_test_file(self, source_path: str, config: Dict[str, Any]) -> Optional[str]:
        """Find the test file for a source file."""
        import os

        base_name = os.path.basename(source_path)
        name, ext = os.path.splitext(base_name)
        dir_path = os.path.dirname(source_path)

        # Common test file naming patterns
        test_names = [
            f"test_{name}{ext}",
            f"{name}_test{ext}",
            f"{name}.test{ext}",
            f"{name}.spec{ext}",
        ]

        # Check in same directory and tests subdirectory
        for test_name in test_names:
            potential_paths = [
                os.path.join(dir_path, test_name),
                os.path.join(dir_path, "tests", test_name),
                os.path.join(dir_path, "__tests__", test_name),
            ]
            for path in potential_paths:
                # We can't check if file exists without file system access
                # Return the most likely path
                pass

        # Return a suggested path
        if config.get("test_patterns"):
            if "test_" in config["test_patterns"][0]:
                return f"tests/test_{name}{ext}"
            elif ".test." in config["test_patterns"][0]:
                return f"{name}.test{ext}"
            elif ".spec." in config["test_patterns"][0]:
                return f"{name}.spec{ext}"

        return None

    def get_changed_files(self) -> List[str]:
        """Get list of files changed in this session."""
        return self._changed_files.copy()

    def clear_changed_files(self) -> None:
        """Clear the list of changed files."""
        self._changed_files.clear()
