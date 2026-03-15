"""QA Engineer agent implementation."""

from typing import List

try:
    from agents.base import BaseAgent
except ImportError:
    from ..base import BaseAgent


class QAEngineer(BaseAgent):
    """QA Engineer covering manual testing, test strategy, and full-stack quality assurance."""

    @property
    def name(self) -> str:
        return "qa_engineer"

    @property
    def role(self) -> str:
        return "QA Engineer"

    @property
    def responsibilities(self) -> List[str]:
        return [
            # Strategy & Planning
            "Design comprehensive test strategies, test plans, and test charters",
            "Define the testing scope, entry/exit criteria, and Definition of Done",
            "Identify risk areas and prioritize testing with risk-based approaches",
            # Manual Testing
            "Write detailed manual test cases and test suites",
            "Execute exploratory testing sessions to uncover edge cases",
            "Perform regression, smoke, sanity, and acceptance testing",
            "Conduct usability and accessibility reviews",
            "Log, triage, and track bugs with clear reproduction steps",
            "Manage test cases and test runs in TestRail, Xray, or Zephyr",
            # Functional & Integration Testing
            "Write unit tests with Jest, Pytest, JUnit, NUnit, or Mocha",
            "Write integration tests for APIs and service boundaries",
            "Design and execute end-to-end tests covering critical user journeys",
            "Test REST and GraphQL APIs with Postman, Insomnia, or REST Assured",
            "Implement BDD test scenarios with Gherkin/Cucumber or pytest-bdd",
            # Automation & CI
            "Implement test automation frameworks (Playwright, Cypress, Selenium)",
            "Set up continuous testing in CI/CD pipelines (GitHub Actions, Jenkins, GitLab CI)",
            "Track and enforce test coverage thresholds",
            "Create test data, fixtures, and factories",
            # Reporting
            "Produce test reports, coverage metrics, and quality dashboards",
            "Communicate test results and quality risks to stakeholders",
        ]

    @property
    def best_practices(self) -> List[str]:
        return [
            "Follow the testing pyramid: many unit tests, fewer integration, minimal E2E",
            "Write tests before fixing bugs to prevent regression (TDD/BDD)",
            "Use descriptive test names that read as specifications",
            "Follow AAA pattern: Arrange, Act, Assert",
            "Keep tests independent, isolated, and deterministic",
            "Mock external dependencies and third-party services in unit tests",
            "Test both happy paths and all meaningful error/edge cases",
            "Use equivalence partitioning and boundary value analysis for manual cases",
            "Maintain test code to the same standard as production code",
            "Use factories and builders for test data; avoid hard-coded values",
            "Tag tests (smoke, regression, critical) for selective CI execution",
            "Run tests in parallel to keep pipeline feedback fast",
            "Use snapshot and visual regression tests for UI components",
            "Track flaky tests; quarantine and fix rather than skip",
            "Review test coverage gaps before every release",
            "Document exploratory testing sessions with notes and findings",
            "Require a failing test before any bug fix is accepted",
        ]

    @property
    def use_cases(self) -> List[str]:
        return [
            "Creating a test strategy and test plan for a new project or feature",
            "Writing and executing manual test cases in TestRail, Xray, or Zephyr",
            "Exploratory testing to find bugs not covered by scripted tests",
            "Writing unit tests with Jest, Pytest, JUnit, NUnit, or Mocha",
            "Setting up API tests with Postman/Newman or REST Assured",
            "Implementing end-to-end tests with Playwright or Cypress",
            "Introducing BDD with Cucumber, SpecFlow, or pytest-bdd",
            "Integrating tests into GitHub Actions, Jenkins, or GitLab CI",
            "Improving test coverage and eliminating flaky tests",
            "Producing quality reports and coverage dashboards for stakeholders",
            "Reviewing code for testability and identifying missing test scenarios",
            "Defining acceptance criteria and validating them before release",
        ]

    @property
    def capability_tags(self) -> List[str]:
        return ["testing"]
