"""Testing rules for code quality."""

import re
from .base import (
    BaseRule,
    RuleCategory,
    RuleContext,
    RuleResult,
    RuleSeverity,
    RuleViolation,
)


class TestCoverageRule(BaseRule):
    """Check that test coverage meets minimum threshold."""

    DEFAULT_MIN_COVERAGE = 80

    def __init__(self, min_coverage: int = None):
        self._min_coverage = min_coverage or self.DEFAULT_MIN_COVERAGE

    @property
    def name(self) -> str:
        return "test-coverage-minimum"

    @property
    def description(self) -> str:
        return f"Test coverage should be at least {self._min_coverage}%"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.TESTING

    @property
    def severity(self) -> RuleSeverity:
        return RuleSeverity.WARNING

    def check(self, context: RuleContext) -> RuleResult:
        # This rule checks coverage from metadata if provided
        coverage = context.metadata.get("test_coverage")

        if coverage is None:
            return RuleResult(
                rule_name=self.name,
                passed=True,
                message="No coverage data provided (run tests with coverage to check)",
            )

        if coverage < self._min_coverage:
            return RuleResult(
                rule_name=self.name,
                passed=False,
                violations=[
                    RuleViolation(
                        rule_name=self.name,
                        message=f"Test coverage is {coverage}%, minimum required is {self._min_coverage}%",
                        severity=self.severity,
                        suggestion=f"Add tests to increase coverage by {self._min_coverage - coverage}%",
                    )
                ],
                message=f"Coverage {coverage}% is below minimum {self._min_coverage}%",
            )

        return RuleResult(
            rule_name=self.name,
            passed=True,
            message=f"Test coverage is {coverage}% (meets {self._min_coverage}% minimum)",
        )

    def get_guidance(self) -> str:
        return f"""**test-coverage-minimum**: Maintain at least {self._min_coverage}% test coverage.

**Running coverage:**
```bash
# Python
pytest --cov=src --cov-report=term-missing

# JavaScript/TypeScript
npm test -- --coverage

# Go
go test -coverprofile=coverage.out ./...
```

**Focus on:**
- Critical business logic
- Edge cases and error paths
- Integration points
- Recently changed code"""


class TestNamingRule(BaseRule):
    """Check that test functions follow naming conventions."""

    TEST_PATTERNS = [
        # Python pytest/unittest
        (r'def\s+(test_\w+)', "test_"),
        # JavaScript/TypeScript Jest/Vitest
        (r'(?:it|test)\s*\(\s*["\'](.+?)["\']', "it/test"),
        # Go
        (r'func\s+(Test\w+)', "Test"),
    ]

    @property
    def name(self) -> str:
        return "test-naming-convention"

    @property
    def description(self) -> str:
        return "Test names should clearly describe what is being tested"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.TESTING

    @property
    def severity(self) -> RuleSeverity:
        return RuleSeverity.INFO

    def check(self, context: RuleContext) -> RuleResult:
        violations = []
        code = context.code or context.file_content or ""
        file_path = context.file_path or ""

        # Only check test files
        if not self._is_test_file(file_path):
            return RuleResult(rule_name=self.name, passed=True)

        if not code:
            return RuleResult(rule_name=self.name, passed=True)

        lines = code.split("\n")

        for line_num, line in enumerate(lines, 1):
            for pattern, prefix in self.TEST_PATTERNS:
                match = re.search(pattern, line)
                if match:
                    test_name = match.group(1)
                    issues = self._check_test_name(test_name)
                    if issues:
                        violations.append(
                            RuleViolation(
                                rule_name=self.name,
                                message=f"Test name '{test_name}': {issues}",
                                severity=self.severity,
                                line_number=line_num,
                                suggestion="Use format: 'should [expected behavior] when [condition]'",
                            )
                        )

        return RuleResult(
            rule_name=self.name,
            passed=len(violations) == 0,
            violations=violations,
            message=f"Found {len(violations)} test naming issues" if violations else "Test names look good",
        )

    def _is_test_file(self, file_path: str) -> bool:
        """Check if this is a test file."""
        test_indicators = [
            "test_",
            "_test.",
            ".test.",
            ".spec.",
            "tests/",
            "__tests__/",
            "_test/",
        ]
        return any(indicator in file_path.lower() for indicator in test_indicators)

    def _check_test_name(self, name: str) -> str:
        """Check test name quality, return issue description or empty string."""
        # Too short
        if len(name) < 10:
            return "name is too short to be descriptive"

        # Just a number or generic
        if re.match(r'^test_?\d+$', name, re.IGNORECASE):
            return "name should describe behavior, not just be numbered"

        # No action word
        action_words = ['should', 'returns', 'throws', 'creates', 'handles', 'validates', 'when', 'given']
        name_lower = name.lower().replace('_', ' ')
        if not any(word in name_lower for word in action_words):
            return "name should describe expected behavior"

        return ""

    def get_guidance(self) -> str:
        return """**test-naming-convention**: Use descriptive test names.

**Good patterns:**
```python
# Python
def test_user_creation_returns_valid_id():
def test_login_fails_with_invalid_password():
def test_should_raise_error_when_email_missing():
```

```javascript
// JavaScript
it('should return user data when authenticated')
it('throws validation error for invalid email')
test('handles empty cart gracefully')
```

**Formula:** `test_[unit]_[expected_behavior]_when_[condition]`"""


class TestFileExistsRule(BaseRule):
    """Check that source files have corresponding test files."""

    @property
    def name(self) -> str:
        return "test-file-exists"

    @property
    def description(self) -> str:
        return "Source files should have corresponding test files"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.TESTING

    @property
    def severity(self) -> RuleSeverity:
        return RuleSeverity.INFO

    def check(self, context: RuleContext) -> RuleResult:
        file_path = context.file_path or ""

        if not file_path:
            return RuleResult(rule_name=self.name, passed=True)

        # Skip if this is already a test file
        if self._is_test_file(file_path):
            return RuleResult(rule_name=self.name, passed=True)

        # Skip non-code files
        if not self._is_source_file(file_path):
            return RuleResult(rule_name=self.name, passed=True)

        # Check metadata for test file existence
        has_test_file = context.metadata.get("has_test_file")

        if has_test_file is False:
            expected_test_paths = self._get_expected_test_paths(file_path)
            return RuleResult(
                rule_name=self.name,
                passed=False,
                violations=[
                    RuleViolation(
                        rule_name=self.name,
                        message=f"No test file found for {file_path}",
                        severity=self.severity,
                        suggestion=f"Create test file at one of: {', '.join(expected_test_paths[:2])}",
                    )
                ],
                message="Missing test file",
            )

        return RuleResult(
            rule_name=self.name,
            passed=True,
            message="Test file check passed or not applicable",
        )

    def _is_test_file(self, file_path: str) -> bool:
        """Check if this is a test file."""
        test_indicators = ["test_", "_test.", ".test.", ".spec.", "tests/", "__tests__/"]
        return any(indicator in file_path.lower() for indicator in test_indicators)

    def _is_source_file(self, file_path: str) -> bool:
        """Check if this is a source code file."""
        source_extensions = [".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".java", ".cs", ".rb"]
        return any(file_path.endswith(ext) for ext in source_extensions)

    def _get_expected_test_paths(self, file_path: str) -> list:
        """Get expected test file paths for a source file."""
        import os
        base, ext = os.path.splitext(file_path)
        filename = os.path.basename(base)
        dirname = os.path.dirname(file_path)

        paths = []

        if ext == ".py":
            paths.extend([
                f"{dirname}/test_{filename}{ext}",
                f"{dirname}/tests/test_{filename}{ext}",
                f"tests/{filename}_test{ext}",
            ])
        elif ext in [".js", ".ts", ".jsx", ".tsx"]:
            paths.extend([
                f"{base}.test{ext}",
                f"{base}.spec{ext}",
                f"{dirname}/__tests__/{filename}{ext}",
            ])
        elif ext == ".go":
            paths.append(f"{base}_test{ext}")

        return paths

    def get_guidance(self) -> str:
        return """**test-file-exists**: Every source file should have tests.

**Naming conventions:**
| Language | Source | Test |
|----------|--------|------|
| Python | user.py | test_user.py |
| JS/TS | user.ts | user.test.ts or user.spec.ts |
| Go | user.go | user_test.go |
| Java | User.java | UserTest.java |

**Where to put tests:**
- Same directory (Go, some JS projects)
- `tests/` subdirectory (Python)
- `__tests__/` directory (Jest)
- `src/test/` (Java/Maven)"""


class AssertionQualityRule(BaseRule):
    """Check for quality assertions in tests."""

    WEAK_ASSERTIONS = [
        (r'assert\s+True\s*$', "assert True is meaningless"),
        (r'expect\([^)]+\)\.toBeTruthy\(\)', "toBeTruthy is often too weak"),
        (r'assert\s+\w+\s*$', "bare assert without comparison"),
        (r'\.toBe\(true\)', "consider more specific assertion"),
    ]

    GOOD_ASSERTIONS = [
        r'assertEqual',
        r'assertEquals',
        r'assertRaises',
        r'toEqual',
        r'toThrow',
        r'toContain',
        r'toHaveLength',
        r'assert.*==',
    ]

    @property
    def name(self) -> str:
        return "assertion-quality"

    @property
    def description(self) -> str:
        return "Test assertions should be specific and meaningful"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.TESTING

    @property
    def severity(self) -> RuleSeverity:
        return RuleSeverity.INFO

    def check(self, context: RuleContext) -> RuleResult:
        violations = []
        code = context.code or context.file_content or ""
        file_path = context.file_path or ""

        # Only check test files
        if not self._is_test_file(file_path):
            return RuleResult(rule_name=self.name, passed=True)

        if not code:
            return RuleResult(rule_name=self.name, passed=True)

        lines = code.split("\n")

        for line_num, line in enumerate(lines, 1):
            for pattern, issue in self.WEAK_ASSERTIONS:
                if re.search(pattern, line):
                    violations.append(
                        RuleViolation(
                            rule_name=self.name,
                            message=issue,
                            severity=self.severity,
                            line_number=line_num,
                            suggestion="Use specific assertions like assertEqual, toEqual, etc.",
                            code_snippet=line.strip()[:60],
                        )
                    )

        return RuleResult(
            rule_name=self.name,
            passed=len(violations) == 0,
            violations=violations,
            message=f"Found {len(violations)} weak assertions" if violations else "Assertions look good",
        )

    def _is_test_file(self, file_path: str) -> bool:
        """Check if this is a test file."""
        test_indicators = ["test_", "_test.", ".test.", ".spec.", "tests/", "__tests__/"]
        return any(indicator in file_path.lower() for indicator in test_indicators)

    def get_guidance(self) -> str:
        return """**assertion-quality**: Use specific, meaningful assertions.

**Weak assertions (avoid):**
```python
assert result  # What should result be?
assert True    # Always passes
```

**Strong assertions (prefer):**
```python
assert result == expected_value
assert len(items) == 3
assert "error" in message
assertRaises(ValueError, func, bad_arg)
```

**JavaScript/TypeScript:**
```javascript
// Weak
expect(result).toBeTruthy();

// Strong
expect(result).toEqual({ id: 1, name: 'test' });
expect(items).toHaveLength(3);
expect(() => fn()).toThrow(ValidationError);
```"""


# Export all testing rules
TESTING_RULES = [
    TestCoverageRule,
    TestNamingRule,
    TestFileExistsRule,
    AssertionQualityRule,
]
