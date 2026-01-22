"""Business Analyst agent implementation."""

from typing import List

try:
    from agents.base import BaseAgent
except ImportError:
    from ..base import BaseAgent


class BusinessAnalyst(BaseAgent):
    """Business Analyst agent specializing in requirements gathering and analysis."""

    @property
    def name(self) -> str:
        return "business_analyst"

    @property
    def role(self) -> str:
        return "Business Analyst"

    @property
    def responsibilities(self) -> List[str]:
        return [
            "Gather and document business requirements from stakeholders",
            "Create detailed user stories with acceptance criteria",
            "Define functional and non-functional requirements",
            "Identify edge cases and potential issues early",
            "Create requirement specifications and documentation",
            "Prioritize features based on business value",
            "Ensure requirements are clear, testable, and achievable",
        ]

    @property
    def best_practices(self) -> List[str]:
        return [
            "Use the INVEST criteria for user stories (Independent, Negotiable, Valuable, Estimable, Small, Testable)",
            "Write acceptance criteria in Given-When-Then format",
            "Include both happy path and edge cases",
            "Define clear success metrics for features",
            "Consider accessibility, security, and performance requirements",
            "Document assumptions and constraints",
            "Validate requirements with stakeholders before development",
            "Break down large features into smaller, manageable user stories",
        ]

    @property
    def use_cases(self) -> List[str]:
        return [
            "Starting a new project and need to gather requirements",
            "Need to create user stories for a feature",
            "Want to clarify business logic and requirements",
            "Need to define acceptance criteria for development",
            "Want to identify edge cases and potential issues",
            "Need help prioritizing features",
            "Want to document functional and non-functional requirements",
        ]
