"""Security rules for code validation."""

import re
from typing import List, Pattern
from .base import (
    BaseRule,
    RuleCategory,
    RuleContext,
    RuleResult,
    RuleSeverity,
    RuleViolation,
)


class NoHardcodedSecretsRule(BaseRule):
    """Detect hardcoded secrets, API keys, and passwords in code."""

    # Patterns that indicate potential secrets
    SECRET_PATTERNS: List[tuple] = [
        (r'(?i)(api[_-]?key|apikey)\s*[=:]\s*["\'][a-zA-Z0-9_\-]{20,}["\']', "API key"),
        (r'(?i)(secret[_-]?key|secretkey)\s*[=:]\s*["\'][a-zA-Z0-9_\-]{20,}["\']', "Secret key"),
        (r'(?i)(password|passwd|pwd)\s*[=:]\s*["\'][^"\']{8,}["\']', "Password"),
        (r'(?i)(token|auth[_-]?token)\s*[=:]\s*["\'][a-zA-Z0-9_\-]{20,}["\']', "Auth token"),
        (r'(?i)(private[_-]?key)\s*[=:]\s*["\']-----BEGIN', "Private key"),
        (r'sk-[a-zA-Z0-9]{20,}', "OpenAI API key"),
        (r'sk-proj-[a-zA-Z0-9]{20,}', "OpenAI project key"),
        (r'sk-ant-[a-zA-Z0-9\-]{20,}', "Anthropic API key"),
        (r'ghp_[a-zA-Z0-9]{36}', "GitHub personal access token"),
        (r'gho_[a-zA-Z0-9]{36}', "GitHub OAuth token"),
        (r'github_pat_[a-zA-Z0-9]{22}_[a-zA-Z0-9]{59}', "GitHub fine-grained PAT"),
        (r'xox[baprs]-[a-zA-Z0-9\-]{10,}', "Slack token"),
        (r'AKIA[0-9A-Z]{16}', "AWS access key ID"),
        (r'(?i)aws[_-]?secret[_-]?access[_-]?key\s*[=:]\s*["\'][a-zA-Z0-9/+=]{40}["\']', "AWS secret key"),
    ]

    @property
    def name(self) -> str:
        return "no-hardcoded-secrets"

    @property
    def description(self) -> str:
        return "Detects hardcoded secrets, API keys, passwords, and tokens in code"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.SECURITY

    @property
    def severity(self) -> RuleSeverity:
        return RuleSeverity.ERROR

    def check(self, context: RuleContext) -> RuleResult:
        violations = []
        code = context.code or context.file_content or ""

        if not code:
            return RuleResult(rule_name=self.name, passed=True)

        lines = code.split("\n")

        for line_num, line in enumerate(lines, 1):
            # Skip comments
            stripped = line.strip()
            if stripped.startswith("#") or stripped.startswith("//"):
                continue

            for pattern, secret_type in self.SECRET_PATTERNS:
                matches = re.finditer(pattern, line)
                for match in matches:
                    # Check if it's likely an environment variable reference
                    if self._is_env_var_reference(line, match.start()):
                        continue

                    violations.append(
                        RuleViolation(
                            rule_name=self.name,
                            message=f"Potential {secret_type} found",
                            severity=self.severity,
                            line_number=line_num,
                            column=match.start() + 1,
                            suggestion=f"Use environment variables instead: os.environ.get('{secret_type.upper().replace(' ', '_')}')",
                            code_snippet=self._mask_secret(line),
                        )
                    )

        return RuleResult(
            rule_name=self.name,
            passed=len(violations) == 0,
            violations=violations,
            message=f"Found {len(violations)} potential secrets" if violations else "No secrets detected",
        )

    def _is_env_var_reference(self, line: str, position: int) -> bool:
        """Check if the match is actually an environment variable reference."""
        env_patterns = [
            r'os\.environ',
            r'os\.getenv',
            r'process\.env',
            r'Environment\.GetEnvironmentVariable',
            r'\$\{?\w+\}?',  # Shell variable
        ]
        for pattern in env_patterns:
            if re.search(pattern, line[:position + 20]):
                return True
        return False

    def _mask_secret(self, line: str) -> str:
        """Mask potential secrets in the code snippet."""
        # Mask anything that looks like a secret value
        masked = re.sub(r'["\'][a-zA-Z0-9_\-/+=]{20,}["\']', '"***MASKED***"', line)
        return masked

    def get_guidance(self) -> str:
        return """**no-hardcoded-secrets**: Never commit secrets to version control.

**What to do instead:**
1. Use environment variables: `os.environ.get('API_KEY')`
2. Use a secrets manager (AWS Secrets Manager, HashiCorp Vault)
3. Use `.env` files (add to `.gitignore`)
4. Use configuration services

**If you've already committed a secret:**
1. Rotate the credential immediately
2. Use `git filter-branch` or BFG Repo-Cleaner to remove from history
3. Force push and notify team members"""


class SQLInjectionRule(BaseRule):
    """Detect potential SQL injection vulnerabilities."""

    SQL_INJECTION_PATTERNS = [
        (r'f["\']SELECT .+\{[^}]+\}', "f-string in SELECT"),
        (r'f["\']INSERT .+\{[^}]+\}', "f-string in INSERT"),
        (r'f["\']UPDATE .+\{[^}]+\}', "f-string in UPDATE"),
        (r'f["\']DELETE .+\{[^}]+\}', "f-string in DELETE"),
        (r'["\']SELECT .+["\'] \+ ', "String concatenation in SELECT"),
        (r'["\']INSERT .+["\'] \+ ', "String concatenation in INSERT"),
        (r'["\']UPDATE .+["\'] \+ ', "String concatenation in UPDATE"),
        (r'["\']DELETE .+["\'] \+ ', "String concatenation in DELETE"),
        (r'\.format\([^)]+\).*(?:SELECT|INSERT|UPDATE|DELETE)', "format() in SQL"),
        (r'% [^%]+(?:SELECT|INSERT|UPDATE|DELETE)', "% formatting in SQL"),
        (r'`SELECT .+\$\{', "Template literal in SELECT (JS)"),
    ]

    @property
    def name(self) -> str:
        return "sql-injection-prevention"

    @property
    def description(self) -> str:
        return "Detects potential SQL injection vulnerabilities from string interpolation"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.SECURITY

    @property
    def severity(self) -> RuleSeverity:
        return RuleSeverity.ERROR

    def check(self, context: RuleContext) -> RuleResult:
        violations = []
        code = context.code or context.file_content or ""

        if not code:
            return RuleResult(rule_name=self.name, passed=True)

        lines = code.split("\n")

        for line_num, line in enumerate(lines, 1):
            for pattern, issue_type in self.SQL_INJECTION_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    violations.append(
                        RuleViolation(
                            rule_name=self.name,
                            message=f"Potential SQL injection: {issue_type}",
                            severity=self.severity,
                            line_number=line_num,
                            suggestion="Use parameterized queries instead of string interpolation",
                            code_snippet=line.strip()[:100],
                        )
                    )

        return RuleResult(
            rule_name=self.name,
            passed=len(violations) == 0,
            violations=violations,
            message=f"Found {len(violations)} potential SQL injection points" if violations else "No SQL injection vulnerabilities detected",
        )

    def get_guidance(self) -> str:
        return """**sql-injection-prevention**: Always use parameterized queries.

**Bad (vulnerable):**
```python
cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")
cursor.execute("SELECT * FROM users WHERE id = " + user_id)
```

**Good (safe):**
```python
cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
```

**For ORMs:**
```python
# SQLAlchemy
User.query.filter_by(id=user_id).first()

# Django
User.objects.filter(id=user_id).first()
```"""


class XSSPreventionRule(BaseRule):
    """Detect potential XSS vulnerabilities."""

    XSS_PATTERNS = [
        (r'innerHTML\s*=', "Direct innerHTML assignment"),
        (r'outerHTML\s*=', "Direct outerHTML assignment"),
        (r'document\.write\s*\(', "document.write usage"),
        (r'\.html\s*\([^)]*\$', "jQuery .html() with variable"),
        (r'dangerouslySetInnerHTML', "React dangerouslySetInnerHTML"),
        (r'v-html\s*=', "Vue v-html directive"),
        (r'\[innerHTML\]\s*=', "Angular innerHTML binding"),
        (r'@Html\.Raw\s*\(', ".NET Html.Raw"),
        (r'\|safe\s*\}\}', "Django/Jinja safe filter"),
        (r'mark_safe\s*\(', "Django mark_safe"),
    ]

    @property
    def name(self) -> str:
        return "xss-prevention"

    @property
    def description(self) -> str:
        return "Detects potential XSS vulnerabilities from unsafe HTML handling"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.SECURITY

    @property
    def severity(self) -> RuleSeverity:
        return RuleSeverity.ERROR

    def check(self, context: RuleContext) -> RuleResult:
        violations = []
        code = context.code or context.file_content or ""

        if not code:
            return RuleResult(rule_name=self.name, passed=True)

        lines = code.split("\n")

        for line_num, line in enumerate(lines, 1):
            for pattern, issue_type in self.XSS_PATTERNS:
                if re.search(pattern, line):
                    violations.append(
                        RuleViolation(
                            rule_name=self.name,
                            message=f"Potential XSS vulnerability: {issue_type}",
                            severity=self.severity,
                            line_number=line_num,
                            suggestion="Sanitize user input before rendering as HTML",
                            code_snippet=line.strip()[:100],
                        )
                    )

        return RuleResult(
            rule_name=self.name,
            passed=len(violations) == 0,
            violations=violations,
            message=f"Found {len(violations)} potential XSS vulnerabilities" if violations else "No XSS vulnerabilities detected",
        )

    def get_guidance(self) -> str:
        return """**xss-prevention**: Sanitize all user input before rendering as HTML.

**Use text content instead of HTML:**
```javascript
// Bad
element.innerHTML = userInput;

// Good
element.textContent = userInput;
```

**Sanitize when HTML is needed:**
```javascript
import DOMPurify from 'dompurify';
element.innerHTML = DOMPurify.sanitize(userInput);
```

**React:**
```jsx
// Avoid dangerouslySetInnerHTML
// If needed, sanitize first:
<div dangerouslySetInnerHTML={{__html: DOMPurify.sanitize(content)}} />
```"""


class InputValidationRule(BaseRule):
    """Check for proper input validation."""

    UNSAFE_PATTERNS = [
        (r'eval\s*\(', "eval() usage"),
        (r'exec\s*\(', "exec() usage"),
        (r'subprocess\..*shell\s*=\s*True', "subprocess with shell=True"),
        (r'os\.system\s*\(', "os.system usage"),
        (r'os\.popen\s*\(', "os.popen usage"),
        (r'child_process\.exec\s*\(', "child_process.exec"),
        (r'new Function\s*\(', "new Function() constructor"),
        (r'setTimeout\s*\(\s*["\']', "setTimeout with string"),
        (r'setInterval\s*\(\s*["\']', "setInterval with string"),
    ]

    @property
    def name(self) -> str:
        return "input-validation"

    @property
    def description(self) -> str:
        return "Detects unsafe code execution patterns that may process unvalidated input"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.SECURITY

    @property
    def severity(self) -> RuleSeverity:
        return RuleSeverity.ERROR

    def check(self, context: RuleContext) -> RuleResult:
        violations = []
        code = context.code or context.file_content or ""

        if not code:
            return RuleResult(rule_name=self.name, passed=True)

        lines = code.split("\n")

        for line_num, line in enumerate(lines, 1):
            for pattern, issue_type in self.UNSAFE_PATTERNS:
                if re.search(pattern, line):
                    violations.append(
                        RuleViolation(
                            rule_name=self.name,
                            message=f"Unsafe code execution: {issue_type}",
                            severity=self.severity,
                            line_number=line_num,
                            suggestion="Avoid dynamic code execution; use safer alternatives",
                            code_snippet=line.strip()[:100],
                        )
                    )

        return RuleResult(
            rule_name=self.name,
            passed=len(violations) == 0,
            violations=violations,
            message=f"Found {len(violations)} unsafe execution patterns" if violations else "No unsafe execution patterns detected",
        )

    def get_guidance(self) -> str:
        return """**input-validation**: Avoid dynamic code execution.

**Avoid:**
- `eval()` - Use `JSON.parse()` for JSON
- `exec()` - Use specific functions instead
- `os.system()` - Use `subprocess.run()` with list args
- `shell=True` - Pass command as list instead

**Safe subprocess:**
```python
# Bad
os.system(f"ls {user_dir}")
subprocess.run(f"ls {user_dir}", shell=True)

# Good
subprocess.run(["ls", user_dir], check=True)
```"""


# Export all security rules
SECURITY_RULES = [
    NoHardcodedSecretsRule,
    SQLInjectionRule,
    XSSPreventionRule,
    InputValidationRule,
]
