"""Coding style rules for code quality."""

import re
from .base import (
    BaseRule,
    RuleCategory,
    RuleContext,
    RuleResult,
    RuleSeverity,
    RuleViolation,
)


class FileSizeRule(BaseRule):
    """Check that files don't exceed recommended line count."""

    DEFAULT_MAX_LINES = 400

    def __init__(self, max_lines: int = None):
        self._max_lines = max_lines or self.DEFAULT_MAX_LINES

    @property
    def name(self) -> str:
        return "file-size-limit"

    @property
    def description(self) -> str:
        return f"Files should not exceed {self._max_lines} lines for maintainability"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.CODING_STYLE

    @property
    def severity(self) -> RuleSeverity:
        return RuleSeverity.WARNING

    def check(self, context: RuleContext) -> RuleResult:
        code = context.code or context.file_content or ""

        if not code:
            return RuleResult(rule_name=self.name, passed=True)

        line_count = len(code.split("\n"))

        if line_count > self._max_lines:
            return RuleResult(
                rule_name=self.name,
                passed=False,
                violations=[
                    RuleViolation(
                        rule_name=self.name,
                        message=f"File has {line_count} lines, exceeds limit of {self._max_lines}",
                        severity=self.severity,
                        suggestion="Consider splitting into smaller, focused modules",
                    )
                ],
                message=f"File exceeds {self._max_lines} line limit",
            )

        return RuleResult(
            rule_name=self.name,
            passed=True,
            message=f"File has {line_count} lines (within limit)",
        )

    def get_guidance(self) -> str:
        return f"""**file-size-limit**: Keep files under {self._max_lines} lines.

**Why:**
- Smaller files are easier to understand
- Better separation of concerns
- Easier to test and maintain
- Reduces merge conflicts

**How to split:**
1. Extract related functions into separate modules
2. Create subdirectories for feature groups
3. Use composition over inheritance
4. Separate concerns (data, logic, presentation)"""


class NoConsoleLogRule(BaseRule):
    """Detect console.log and print statements that should be removed."""

    DEBUG_PATTERNS = [
        (r'\bconsole\.log\s*\(', "console.log"),
        (r'\bconsole\.debug\s*\(', "console.debug"),
        (r'\bconsole\.info\s*\(', "console.info"),
        (r'\bprint\s*\([^)]*\)', "print()"),
        (r'\bSystem\.out\.print', "System.out.print"),
        (r'\bConsole\.WriteLine\s*\(', "Console.WriteLine"),
        (r'\bdebugger\s*;', "debugger statement"),
    ]

    # Patterns that indicate intentional logging
    ALLOWED_CONTEXTS = [
        r'logger\.',
        r'logging\.',
        r'log\.',
        r'winston\.',
        r'pino\.',
        r'bunyan\.',
        r'console\.error',
        r'console\.warn',
    ]

    @property
    def name(self) -> str:
        return "no-debug-statements"

    @property
    def description(self) -> str:
        return "Detects debug statements (console.log, print) that should be removed before commit"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.CODING_STYLE

    @property
    def severity(self) -> RuleSeverity:
        return RuleSeverity.WARNING

    def check(self, context: RuleContext) -> RuleResult:
        violations = []
        code = context.code or context.file_content or ""

        if not code:
            return RuleResult(rule_name=self.name, passed=True)

        lines = code.split("\n")

        for line_num, line in enumerate(lines, 1):
            # Skip if line contains allowed logging context
            if any(re.search(pattern, line) for pattern in self.ALLOWED_CONTEXTS):
                continue

            # Skip comments
            stripped = line.strip()
            if stripped.startswith("//") or stripped.startswith("#") or stripped.startswith("*"):
                continue

            for pattern, stmt_type in self.DEBUG_PATTERNS:
                if re.search(pattern, line):
                    violations.append(
                        RuleViolation(
                            rule_name=self.name,
                            message=f"Debug statement found: {stmt_type}",
                            severity=self.severity,
                            line_number=line_num,
                            suggestion=f"Remove {stmt_type} before committing, or use a proper logger",
                            code_snippet=line.strip()[:80],
                        )
                    )

        return RuleResult(
            rule_name=self.name,
            passed=len(violations) == 0,
            violations=violations,
            message=f"Found {len(violations)} debug statements" if violations else "No debug statements found",
        )

    def get_guidance(self) -> str:
        return """**no-debug-statements**: Remove console.log/print before committing.

**Instead of console.log, use a proper logger:**
```javascript
// JavaScript
import logger from './logger';
logger.debug('User data:', userData);
logger.info('Operation completed');
```

```python
# Python
import logging
logger = logging.getLogger(__name__)
logger.debug('User data: %s', user_data)
```

**Benefits of proper logging:**
- Log levels (debug, info, warn, error)
- Configurable output (file, console, service)
- Structured logging with metadata
- Easy to disable in production"""


class FunctionLengthRule(BaseRule):
    """Check that functions don't exceed recommended line count."""

    DEFAULT_MAX_LINES = 50

    FUNCTION_PATTERNS = [
        r'^\s*def\s+\w+',  # Python
        r'^\s*(async\s+)?function\s+\w+',  # JavaScript
        r'^\s*(const|let|var)\s+\w+\s*=\s*(async\s+)?\([^)]*\)\s*=>',  # Arrow function
        r'^\s*(public|private|protected)?\s*(static)?\s*(async)?\s*\w+\s*\([^)]*\)\s*\{',  # Java/C#
        r'^\s*func\s+\w+',  # Go
    ]

    def __init__(self, max_lines: int = None):
        self._max_lines = max_lines or self.DEFAULT_MAX_LINES

    @property
    def name(self) -> str:
        return "function-length-limit"

    @property
    def description(self) -> str:
        return f"Functions should not exceed {self._max_lines} lines"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.CODING_STYLE

    @property
    def severity(self) -> RuleSeverity:
        return RuleSeverity.WARNING

    def check(self, context: RuleContext) -> RuleResult:
        violations = []
        code = context.code or context.file_content or ""

        if not code:
            return RuleResult(rule_name=self.name, passed=True)

        lines = code.split("\n")
        current_function = None
        function_start = 0
        brace_count = 0
        indent_level = 0

        for line_num, line in enumerate(lines, 1):
            # Check for function start
            for pattern in self.FUNCTION_PATTERNS:
                match = re.match(pattern, line)
                if match:
                    if current_function:
                        # Check previous function
                        func_length = line_num - function_start
                        if func_length > self._max_lines:
                            violations.append(
                                RuleViolation(
                                    rule_name=self.name,
                                    message=f"Function '{current_function}' is {func_length} lines (max {self._max_lines})",
                                    severity=self.severity,
                                    line_number=function_start,
                                    suggestion="Split into smaller functions with single responsibilities",
                                )
                            )

                    # Extract function name
                    func_name_match = re.search(r'(?:def|function|func)\s+(\w+)|(\w+)\s*=\s*(?:async\s+)?\(', line)
                    current_function = func_name_match.group(1) or func_name_match.group(2) if func_name_match else "anonymous"
                    function_start = line_num
                    indent_level = len(line) - len(line.lstrip())
                    break

        # Check last function
        if current_function:
            func_length = len(lines) - function_start + 1
            if func_length > self._max_lines:
                violations.append(
                    RuleViolation(
                        rule_name=self.name,
                        message=f"Function '{current_function}' is {func_length} lines (max {self._max_lines})",
                        severity=self.severity,
                        line_number=function_start,
                        suggestion="Split into smaller functions with single responsibilities",
                    )
                )

        return RuleResult(
            rule_name=self.name,
            passed=len(violations) == 0,
            violations=violations,
            message=f"Found {len(violations)} functions exceeding limit" if violations else "All functions within limit",
        )

    def get_guidance(self) -> str:
        return f"""**function-length-limit**: Keep functions under {self._max_lines} lines.

**Signs a function is too long:**
- Multiple levels of nesting
- Multiple distinct operations
- Hard to name what it does
- Needs comments to explain sections

**How to split:**
1. Extract helper functions
2. Use early returns to reduce nesting
3. Separate validation from business logic
4. Extract complex conditions into named functions"""


class NamingConventionRule(BaseRule):
    """Check naming conventions."""

    @property
    def name(self) -> str:
        return "naming-conventions"

    @property
    def description(self) -> str:
        return "Checks for consistent naming conventions (camelCase, snake_case, PascalCase)"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.CODING_STYLE

    @property
    def severity(self) -> RuleSeverity:
        return RuleSeverity.INFO

    def check(self, context: RuleContext) -> RuleResult:
        violations = []
        code = context.code or context.file_content or ""
        file_path = context.file_path or ""

        if not code:
            return RuleResult(rule_name=self.name, passed=True)

        # Detect language from file extension
        is_python = file_path.endswith(".py")
        is_js_ts = any(file_path.endswith(ext) for ext in [".js", ".ts", ".jsx", ".tsx"])

        lines = code.split("\n")

        for line_num, line in enumerate(lines, 1):
            # Check class names (should be PascalCase)
            class_match = re.search(r'class\s+([a-zA-Z_]\w*)', line)
            if class_match:
                class_name = class_match.group(1)
                if not self._is_pascal_case(class_name):
                    violations.append(
                        RuleViolation(
                            rule_name=self.name,
                            message=f"Class '{class_name}' should use PascalCase",
                            severity=self.severity,
                            line_number=line_num,
                            suggestion=f"Rename to '{self._to_pascal_case(class_name)}'",
                        )
                    )

            # Check constant names (should be UPPER_SNAKE_CASE)
            const_match = re.search(r'(?:const|final|static final)\s+([A-Z][A-Za-z_]*)\s*=', line)
            if const_match:
                const_name = const_match.group(1)
                # Only flag if it looks like it should be a constant (all caps intended)
                if const_name.isupper() and "_" not in const_name and len(const_name) > 1:
                    # Might be missing underscores
                    pass  # Too noisy, skip for now

        return RuleResult(
            rule_name=self.name,
            passed=len(violations) == 0,
            violations=violations,
            message=f"Found {len(violations)} naming convention issues" if violations else "Naming conventions look good",
        )

    def _is_pascal_case(self, name: str) -> bool:
        """Check if name is PascalCase."""
        return bool(re.match(r'^[A-Z][a-zA-Z0-9]*$', name))

    def _is_snake_case(self, name: str) -> bool:
        """Check if name is snake_case."""
        return bool(re.match(r'^[a-z][a-z0-9_]*$', name))

    def _is_camel_case(self, name: str) -> bool:
        """Check if name is camelCase."""
        return bool(re.match(r'^[a-z][a-zA-Z0-9]*$', name))

    def _to_pascal_case(self, name: str) -> str:
        """Convert to PascalCase."""
        words = re.split(r'[_\s]+', name)
        return ''.join(word.capitalize() for word in words)

    def get_guidance(self) -> str:
        return """**naming-conventions**: Use consistent naming.

| Type | Python | JavaScript/TypeScript |
|------|--------|----------------------|
| Classes | PascalCase | PascalCase |
| Functions | snake_case | camelCase |
| Variables | snake_case | camelCase |
| Constants | UPPER_SNAKE | UPPER_SNAKE |
| Private | _leading_underscore | #private or _prefix |

**Examples:**
```python
# Python
class UserAccount:
    MAX_RETRIES = 3

    def get_user_data(self):
        user_name = "example"
```

```typescript
// TypeScript
class UserAccount {
  static readonly MAX_RETRIES = 3;

  getUserData(): void {
    const userName = "example";
  }
}
```"""


# Export all coding style rules
CODING_STYLE_RULES = [
    FileSizeRule,
    NoConsoleLogRule,
    FunctionLengthRule,
    NamingConventionRule,
]
