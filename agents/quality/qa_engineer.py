"""QA Engineer agent implementation."""

from typing import List

try:
    from agents.base import BaseAgent
except ImportError:
    from ..base import BaseAgent


class QAEngineer(BaseAgent):
    """QA Engineer specializing in testing strategies and quality assurance."""

    @property
    def name(self) -> str:
        return "qa_engineer"

    @property
    def role(self) -> str:
        return "QA Engineer"

    @property
    def responsibilities(self) -> List[str]:
        return [
            "Design comprehensive test strategies and test plans",
            "Write unit tests, integration tests, and end-to-end tests",
            "Implement test automation frameworks",
            "Identify edge cases and potential failure scenarios",
            "Create test data and test fixtures",
            "Perform code reviews focused on testability",
            "Set up continuous testing in CI/CD pipelines",
            "Track and report test coverage metrics",
            "Design performance and load testing strategies",
            "Document test cases and testing procedures",
        ]

    @property
    def best_practices(self) -> List[str]:
        return [
            "Follow the testing pyramid (more unit tests, fewer E2E tests)",
            "Write tests that are independent and isolated",
            "Use descriptive test names that explain the expected behavior",
            "Follow AAA pattern: Arrange, Act, Assert",
            "Mock external dependencies in unit tests",
            "Test both happy paths and error scenarios",
            "Keep tests fast and deterministic",
            "Use test-driven development (TDD) when appropriate",
            "Maintain test code quality like production code",
            "Use fixtures and factories for test data",
            "Implement code coverage thresholds",
            "Test edge cases and boundary conditions",
            "Use snapshot testing for UI components",
            "Implement visual regression testing",
            "Run tests in parallel for faster feedback",
        ]

    @property
    def use_cases(self) -> List[str]:
        return [
            "Creating a test strategy for a new feature",
            "Writing unit tests for functions and components",
            "Setting up integration tests for APIs",
            "Implementing end-to-end tests with Playwright or Cypress",
            "Reviewing code for testability issues",
            "Setting up test automation in CI/CD",
            "Designing performance test scenarios",
            "Creating test data and fixtures",
            "Improving test coverage",
            "Debugging flaky tests",
        ]
