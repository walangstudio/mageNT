"""Git workflow rules for version control best practices."""

import re
from .base import (
    BaseRule,
    RuleCategory,
    RuleContext,
    RuleResult,
    RuleSeverity,
    RuleViolation,
)


class CommitMessageRule(BaseRule):
    """Check commit message format and quality."""

    # Conventional Commits types
    VALID_TYPES = [
        "feat", "fix", "docs", "style", "refactor", "perf",
        "test", "build", "ci", "chore", "revert"
    ]

    @property
    def name(self) -> str:
        return "commit-message-format"

    @property
    def description(self) -> str:
        return "Commit messages should follow Conventional Commits format"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.GIT

    @property
    def severity(self) -> RuleSeverity:
        return RuleSeverity.WARNING

    def check(self, context: RuleContext) -> RuleResult:
        commit_message = context.metadata.get("commit_message", "")

        if not commit_message:
            return RuleResult(rule_name=self.name, passed=True)

        violations = []
        lines = commit_message.split("\n")
        subject = lines[0] if lines else ""

        # Check subject line length
        if len(subject) > 72:
            violations.append(
                RuleViolation(
                    rule_name=self.name,
                    message=f"Subject line is {len(subject)} chars (max 72)",
                    severity=self.severity,
                    suggestion="Keep subject line under 72 characters",
                )
            )

        # Check for conventional commit format
        conventional_pattern = r'^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\(.+\))?: .+'
        if not re.match(conventional_pattern, subject):
            violations.append(
                RuleViolation(
                    rule_name=self.name,
                    message="Subject doesn't follow Conventional Commits format",
                    severity=self.severity,
                    suggestion="Use format: type(scope): description (e.g., 'feat(auth): add login')",
                )
            )

        # Check for capitalization after colon
        colon_match = re.search(r': ([A-Z])', subject)
        if colon_match:
            violations.append(
                RuleViolation(
                    rule_name=self.name,
                    message="Description should start with lowercase letter",
                    severity=RuleSeverity.INFO,
                    suggestion="Use lowercase after the colon: 'feat: add feature' not 'feat: Add feature'",
                )
            )

        # Check for period at end of subject
        if subject.endswith("."):
            violations.append(
                RuleViolation(
                    rule_name=self.name,
                    message="Subject line should not end with a period",
                    severity=RuleSeverity.INFO,
                    suggestion="Remove the trailing period from the subject line",
                )
            )

        # Check for blank line between subject and body
        if len(lines) > 1 and lines[1].strip():
            violations.append(
                RuleViolation(
                    rule_name=self.name,
                    message="Missing blank line between subject and body",
                    severity=RuleSeverity.INFO,
                    suggestion="Add a blank line after the subject line",
                )
            )

        return RuleResult(
            rule_name=self.name,
            passed=len([v for v in violations if v.severity == RuleSeverity.WARNING or v.severity == RuleSeverity.ERROR]) == 0,
            violations=violations,
            message=f"Found {len(violations)} commit message issues" if violations else "Commit message looks good",
        )

    def get_guidance(self) -> str:
        return """**commit-message-format**: Follow Conventional Commits.

**Format:**
```
type(scope): description

[optional body]

[optional footer]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Formatting (no code change)
- `refactor`: Code restructuring
- `perf`: Performance improvement
- `test`: Adding tests
- `build`: Build system changes
- `ci`: CI configuration
- `chore`: Maintenance tasks

**Examples:**
```
feat(auth): add password reset flow
fix(api): handle null response from payment gateway
docs: update API documentation for v2
refactor(utils): extract date formatting helpers
```

**Rules:**
- Subject line max 72 characters
- Use imperative mood ("add" not "added")
- No period at end of subject
- Blank line before body"""


class BranchNamingRule(BaseRule):
    """Check branch naming conventions."""

    VALID_PREFIXES = [
        "feature/", "feat/",
        "fix/", "bugfix/", "hotfix/",
        "docs/", "doc/",
        "refactor/",
        "test/",
        "chore/",
        "release/",
        "experiment/",
    ]

    @property
    def name(self) -> str:
        return "branch-naming-convention"

    @property
    def description(self) -> str:
        return "Branch names should follow naming conventions"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.GIT

    @property
    def severity(self) -> RuleSeverity:
        return RuleSeverity.INFO

    def check(self, context: RuleContext) -> RuleResult:
        branch_name = context.metadata.get("branch_name", "")

        if not branch_name:
            return RuleResult(rule_name=self.name, passed=True)

        violations = []

        # Skip main branches
        if branch_name in ["main", "master", "develop", "dev", "staging", "production"]:
            return RuleResult(rule_name=self.name, passed=True)

        # Check for valid prefix
        has_valid_prefix = any(branch_name.startswith(prefix) for prefix in self.VALID_PREFIXES)
        if not has_valid_prefix:
            violations.append(
                RuleViolation(
                    rule_name=self.name,
                    message=f"Branch '{branch_name}' doesn't have a standard prefix",
                    severity=self.severity,
                    suggestion=f"Use prefixes like: {', '.join(self.VALID_PREFIXES[:5])}",
                )
            )

        # Check for spaces or special characters
        if re.search(r'[^a-zA-Z0-9/_\-.]', branch_name):
            violations.append(
                RuleViolation(
                    rule_name=self.name,
                    message="Branch name contains invalid characters",
                    severity=RuleSeverity.WARNING,
                    suggestion="Use only alphanumeric characters, hyphens, underscores, and slashes",
                )
            )

        # Check for uppercase
        if branch_name != branch_name.lower():
            violations.append(
                RuleViolation(
                    rule_name=self.name,
                    message="Branch name should be lowercase",
                    severity=RuleSeverity.INFO,
                    suggestion=f"Use '{branch_name.lower()}' instead",
                )
            )

        return RuleResult(
            rule_name=self.name,
            passed=len([v for v in violations if v.severity != RuleSeverity.INFO]) == 0,
            violations=violations,
            message=f"Found {len(violations)} branch naming issues" if violations else "Branch name looks good",
        )

    def get_guidance(self) -> str:
        return """**branch-naming-convention**: Use consistent branch names.

**Format:** `type/description` or `type/ticket-description`

**Prefixes:**
- `feature/` or `feat/` - New features
- `fix/` or `bugfix/` - Bug fixes
- `hotfix/` - Urgent production fixes
- `docs/` - Documentation
- `refactor/` - Code refactoring
- `test/` - Test additions
- `chore/` - Maintenance

**Examples:**
```
feature/user-authentication
fix/login-validation-error
hotfix/payment-timeout
docs/api-documentation
feat/JIRA-123-add-export
```

**Rules:**
- Use lowercase
- Use hyphens to separate words
- Include ticket number if applicable
- Keep it descriptive but concise"""


class NoDirectMainCommitRule(BaseRule):
    """Warn against committing directly to main/master branches."""

    PROTECTED_BRANCHES = ["main", "master", "production", "prod"]

    @property
    def name(self) -> str:
        return "no-direct-main-commit"

    @property
    def description(self) -> str:
        return "Avoid committing directly to main/master branches"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.GIT

    @property
    def severity(self) -> RuleSeverity:
        return RuleSeverity.WARNING

    def check(self, context: RuleContext) -> RuleResult:
        branch_name = context.metadata.get("branch_name", "")

        if not branch_name:
            return RuleResult(rule_name=self.name, passed=True)

        if branch_name.lower() in self.PROTECTED_BRANCHES:
            return RuleResult(
                rule_name=self.name,
                passed=False,
                violations=[
                    RuleViolation(
                        rule_name=self.name,
                        message=f"Committing directly to '{branch_name}' branch",
                        severity=self.severity,
                        suggestion="Create a feature branch and use pull requests instead",
                    )
                ],
                message=f"Direct commit to protected branch '{branch_name}'",
            )

        return RuleResult(
            rule_name=self.name,
            passed=True,
            message="Not committing to protected branch",
        )

    def get_guidance(self) -> str:
        return """**no-direct-main-commit**: Use pull requests for main branches.

**Why:**
- Code review catches bugs
- CI/CD runs before merge
- History is cleaner
- Easier to revert changes

**Workflow:**
1. Create feature branch: `git checkout -b feature/my-change`
2. Make commits on feature branch
3. Push and create pull request
4. Get code review
5. Merge via PR (squash or merge commit)

**If you need to commit to main:**
```bash
# Check current branch first
git branch --show-current

# If on main, create a branch
git checkout -b feature/my-change
```"""


class GitignoreRule(BaseRule):
    """Check for proper .gitignore configuration."""

    COMMON_IGNORES = {
        "python": ["__pycache__/", "*.pyc", ".venv/", "venv/", ".env", "*.egg-info/"],
        "node": ["node_modules/", ".env", "dist/", "build/", ".next/"],
        "general": [".DS_Store", "*.log", ".idea/", ".vscode/", "*.swp"],
    }

    SENSITIVE_FILES = [
        ".env",
        ".env.local",
        ".env.production",
        "credentials.json",
        "secrets.yaml",
        "*.pem",
        "*.key",
        "id_rsa",
    ]

    @property
    def name(self) -> str:
        return "gitignore-config"

    @property
    def description(self) -> str:
        return "Check that .gitignore includes common patterns and sensitive files"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.GIT

    @property
    def severity(self) -> RuleSeverity:
        return RuleSeverity.WARNING

    def check(self, context: RuleContext) -> RuleResult:
        gitignore_content = context.metadata.get("gitignore_content", "")
        project_type = context.metadata.get("project_type", "general")

        if gitignore_content is None:
            return RuleResult(
                rule_name=self.name,
                passed=False,
                violations=[
                    RuleViolation(
                        rule_name=self.name,
                        message="No .gitignore file found",
                        severity=self.severity,
                        suggestion="Create a .gitignore file with appropriate patterns",
                    )
                ],
                message="Missing .gitignore",
            )

        violations = []

        # Check for sensitive files
        for sensitive in self.SENSITIVE_FILES:
            pattern = sensitive.replace("*", "")
            if pattern not in gitignore_content and sensitive not in gitignore_content:
                violations.append(
                    RuleViolation(
                        rule_name=self.name,
                        message=f"Sensitive file pattern '{sensitive}' not in .gitignore",
                        severity=RuleSeverity.WARNING,
                        suggestion=f"Add '{sensitive}' to .gitignore",
                    )
                )

        return RuleResult(
            rule_name=self.name,
            passed=len(violations) == 0,
            violations=violations,
            message=f"Found {len(violations)} missing .gitignore patterns" if violations else ".gitignore looks good",
        )

    def get_guidance(self) -> str:
        return """**gitignore-config**: Maintain a proper .gitignore.

**Essential patterns:**
```gitignore
# Environment
.env
.env.local
.env.*.local

# Dependencies
node_modules/
__pycache__/
venv/

# Build output
dist/
build/
*.egg-info/

# IDE
.idea/
.vscode/
*.swp

# OS
.DS_Store
Thumbs.db

# Secrets (CRITICAL)
*.pem
*.key
credentials.json
```

**Generate .gitignore:**
- https://gitignore.io
- `npx gitignore node`
- `curl https://raw.githubusercontent.com/github/gitignore/main/Python.gitignore`"""


# Export all git workflow rules
GIT_WORKFLOW_RULES = [
    CommitMessageRule,
    BranchNamingRule,
    NoDirectMainCommitRule,
    GitignoreRule,
]
