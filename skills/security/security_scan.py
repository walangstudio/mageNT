"""Security scan skill."""

from typing import Any, Dict, List

try:
    from skills.base import BaseSkill
except ImportError:
    from ..base import BaseSkill


class SecurityScan(BaseSkill):
    """Run security analysis on code."""

    @property
    def name(self) -> str:
        return "security_scan"

    @property
    def slash_command(self) -> str:
        return "/security-scan"

    @property
    def description(self) -> str:
        return "Run security analysis to identify vulnerabilities and security issues"

    @property
    def category(self) -> str:
        return "security"

    @property
    def parameters(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "scan_type",
                "type": "string",
                "description": "Type of scan: dependencies, code, secrets, or all",
                "required": False,
            },
            {
                "name": "language",
                "type": "string",
                "description": "Programming language for code scanning",
                "required": False,
            },
        ]

    def execute(self, **kwargs) -> Dict[str, Any]:
        scan_type = kwargs.get("scan_type", "all")
        language = kwargs.get("language", "auto")

        guidance = f"""# Security Scan Guide

## Scan Configuration
- Scan Type: {scan_type}
- Language: {language}

## 1. Dependency Vulnerability Scanning

### npm (Node.js)
```bash
# Built-in audit
npm audit

# With fix suggestions
npm audit fix

# Generate detailed report
npm audit --json > audit-report.json

# Using Snyk
npx snyk test
```

### Python
```bash
# Using pip-audit
pip install pip-audit
pip-audit

# Using safety
pip install safety
safety check

# Using Snyk
snyk test --file=requirements.txt
```

### Java (Maven)
```bash
# OWASP Dependency Check
mvn org.owasp:dependency-check-maven:check

# Using Snyk
snyk test --file=pom.xml
```

### .NET
```bash
# Built-in vulnerability check
dotnet list package --vulnerable

# Using Snyk
snyk test --file=*.csproj
```

### Go
```bash
# Using govulncheck
go install golang.org/x/vuln/cmd/govulncheck@latest
govulncheck ./...

# Using Snyk
snyk test
```

## 2. Static Code Analysis (SAST)

### Multi-Language Tools

#### Semgrep (Recommended)
```bash
# Install
pip install semgrep

# Run with auto-detection
semgrep --config auto .

# Run with specific rulesets
semgrep --config p/security-audit .
semgrep --config p/owasp-top-ten .

# CI-friendly output
semgrep --config auto --json -o results.json .
```

#### SonarQube
```bash
# Using Docker
docker run -d --name sonarqube -p 9000:9000 sonarqube

# Run scanner
sonar-scanner \\
  -Dsonar.projectKey=my-project \\
  -Dsonar.sources=. \\
  -Dsonar.host.url=http://localhost:9000
```

### Language-Specific Tools

#### JavaScript/TypeScript
```bash
# ESLint with security plugin
npm install -D eslint-plugin-security
# Add to .eslintrc: plugins: ['security']

eslint --ext .js,.ts .
```

#### Python
```bash
# Bandit
pip install bandit
bandit -r src/

# With specific tests
bandit -r src/ -ll -ii
```

#### Java
```bash
# SpotBugs with Find Security Bugs
mvn com.github.spotbugs:spotbugs-maven-plugin:check
```

#### Go
```bash
# gosec
go install github.com/securego/gosec/v2/cmd/gosec@latest
gosec ./...
```

## 3. Secret Detection

### Gitleaks (Recommended)
```bash
# Install
brew install gitleaks  # or download from GitHub releases

# Scan current directory
gitleaks detect --source .

# Scan git history
gitleaks detect --source . --log-opts="--all"

# Generate report
gitleaks detect --source . --report-path=secrets-report.json
```

### TruffleHog
```bash
# Install
pip install trufflehog

# Scan directory
trufflehog filesystem .

# Scan git repo
trufflehog git file://./
```

### git-secrets (AWS)
```bash
# Install
brew install git-secrets

# Register AWS patterns
git secrets --register-aws

# Scan
git secrets --scan
```

## 4. OWASP Top 10 Checklist

### A01: Broken Access Control
- [ ] Verify authorization on every request
- [ ] Deny by default
- [ ] Implement proper CORS
- [ ] Disable directory listing

### A02: Cryptographic Failures
- [ ] Use strong encryption (AES-256, RSA-2048+)
- [ ] Use HTTPS everywhere
- [ ] Don't store sensitive data unnecessarily
- [ ] Use secure password hashing (bcrypt, argon2)

### A03: Injection
- [ ] Use parameterized queries (prepared statements)
- [ ] Validate and sanitize all input
- [ ] Use ORMs properly
- [ ] Escape output based on context

### A04: Insecure Design
- [ ] Threat modeling performed
- [ ] Security requirements defined
- [ ] Secure design patterns used

### A05: Security Misconfiguration
- [ ] Remove default credentials
- [ ] Disable unnecessary features
- [ ] Keep software updated
- [ ] Proper error handling (no stack traces)

### A06: Vulnerable Components
- [ ] Regular dependency audits
- [ ] Remove unused dependencies
- [ ] Use only trusted sources
- [ ] Monitor for vulnerabilities

### A07: Authentication Failures
- [ ] Multi-factor authentication
- [ ] Strong password policies
- [ ] Secure session management
- [ ] Rate limiting on login

### A08: Software and Data Integrity
- [ ] Verify software signatures
- [ ] Use integrity checks (SRI)
- [ ] Secure CI/CD pipeline

### A09: Security Logging Failures
- [ ] Log security events
- [ ] Protect logs from tampering
- [ ] Include sufficient detail
- [ ] Monitor and alert

### A10: Server-Side Request Forgery
- [ ] Validate URLs and IPs
- [ ] Use allowlists for destinations
- [ ] Disable unnecessary protocols

## 5. Security Headers Check

### Check Current Headers
```bash
# Using curl
curl -I https://your-site.com

# Key headers to verify:
# - Content-Security-Policy
# - X-Content-Type-Options: nosniff
# - X-Frame-Options: DENY
# - Strict-Transport-Security
# - X-XSS-Protection: 0 (deprecated, use CSP)
```

### Online Tools
- https://securityheaders.com
- https://observatory.mozilla.org

## 6. Quick Security Fixes

### SQL Injection Prevention
```javascript
// Bad
const query = `SELECT * FROM users WHERE id = ${{userId}}`

// Good (parameterized)
const query = 'SELECT * FROM users WHERE id = $1'
db.query(query, [userId])
```

### XSS Prevention
```javascript
// Bad
element.innerHTML = userInput

// Good
element.textContent = userInput
// Or use DOMPurify for HTML
element.innerHTML = DOMPurify.sanitize(userInput)
```

### Authentication
```javascript
// Use secure password hashing
import bcrypt from 'bcryptjs'
const hash = await bcrypt.hash(password, 12)

// Use secure session tokens
import crypto from 'crypto'
const token = crypto.randomBytes(32).toString('hex')
```

## 7. CI/CD Security Integration

### GitHub Actions Example
```yaml
name: Security Scan

on: [push, pull_request]

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Run Semgrep
        uses: returntocorp/semgrep-action@v1
        with:
          config: p/security-audit

      - name: Run npm audit
        run: npm audit --audit-level=high

      - name: Run Gitleaks
        uses: gitleaks/gitleaks-action@v2
```

## Next Steps

1. Run dependency audit for your project
2. Run static code analysis
3. Scan for secrets in codebase
4. Review OWASP checklist items
5. Set up automated scanning in CI/CD
"""

        return {
            "guidance": guidance,
            "context": {
                "scan_type": scan_type,
                "language": language,
            },
            "success": True,
        }
