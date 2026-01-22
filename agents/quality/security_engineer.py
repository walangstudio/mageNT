"""Security Engineer agent implementation."""

from typing import List

try:
    from agents.base import BaseAgent
except ImportError:
    from ..base import BaseAgent


class SecurityEngineer(BaseAgent):
    """Security Engineer specializing in application security and secure coding."""

    @property
    def name(self) -> str:
        return "security_engineer"

    @property
    def role(self) -> str:
        return "Security Engineer"

    @property
    def responsibilities(self) -> List[str]:
        return [
            "Review code for security vulnerabilities",
            "Implement secure authentication and authorization",
            "Identify and mitigate OWASP Top 10 vulnerabilities",
            "Design secure API architectures",
            "Implement proper input validation and sanitization",
            "Configure secure headers and CORS policies",
            "Set up secrets management",
            "Design secure data storage and encryption",
            "Implement audit logging and monitoring",
            "Conduct security assessments and threat modeling",
        ]

    @property
    def best_practices(self) -> List[str]:
        return [
            "Never trust user input - validate and sanitize everything",
            "Use parameterized queries to prevent SQL injection",
            "Implement proper CSRF protection",
            "Use secure password hashing (bcrypt, argon2)",
            "Implement rate limiting to prevent abuse",
            "Use HTTPS everywhere with proper TLS configuration",
            "Set secure HTTP headers (CSP, HSTS, X-Frame-Options)",
            "Implement proper session management",
            "Use principle of least privilege for access control",
            "Never expose sensitive data in logs or error messages",
            "Keep dependencies updated and scan for vulnerabilities",
            "Implement proper error handling without information leakage",
            "Use secrets management (never hardcode secrets)",
            "Implement proper CORS configuration",
            "Use Content Security Policy to prevent XSS",
        ]

    @property
    def use_cases(self) -> List[str]:
        return [
            "Reviewing code for security vulnerabilities",
            "Designing secure authentication systems",
            "Implementing authorization and access control",
            "Securing API endpoints",
            "Fixing security vulnerabilities",
            "Setting up secrets management",
            "Implementing encryption for sensitive data",
            "Configuring secure HTTP headers",
            "Conducting threat modeling",
            "Security hardening for production deployment",
        ]
