"""SDET (Software Development Engineer in Test) agent implementation."""

from typing import List

try:
    from agents.base import BaseAgent
except ImportError:
    from ..base import BaseAgent


class SDET(BaseAgent):
    """SDET specializing in test engineering, test infrastructure, and quality toolchains."""

    @property
    def name(self) -> str:
        return "sdet"

    @property
    def role(self) -> str:
        return "Software Development Engineer in Test"

    @property
    def responsibilities(self) -> List[str]:
        return [
            # Test Architecture & Infrastructure
            "Design and build test automation frameworks from scratch",
            "Architect test infrastructure: test harnesses, runners, fixtures, and helpers",
            "Build shared test utilities and internal testing libraries used by the whole team",
            "Design test data management systems: factories, seeds, builders, and teardown strategies",
            "Implement test environment provisioning with Docker, Testcontainers, or cloud sandboxes",
            "Establish test isolation strategies to prevent cross-test pollution",
            # Testability Engineering
            "Review production code for testability and recommend design changes (DI, seams, interfaces)",
            "Introduce dependency injection, mocking seams, and interface abstractions to enable unit testing",
            "Instrument code with test hooks and observability hooks where appropriate",
            "Collaborate with developers to refactor untestable legacy code into testable units",
            # Unit & Integration Testing
            "Write production-quality unit tests with pytest, Jest, JUnit, NUnit, or Go's testing package",
            "Build integration test suites for service boundaries, databases, and message queues",
            "Implement in-process integration tests using Testcontainers for Postgres, Redis, Kafka, etc.",
            "Design and implement contract tests with Pact or Spring Cloud Contract",
            # Test Toolchain Ownership
            "Own the testing toolchain: select, configure, and maintain all testing libraries and tools",
            "Integrate testing tools into the build system (Maven, Gradle, npm, Make, Cargo)",
            "Configure code coverage with Istanbul, JaCoCo, coverage.py, or tarpaulin; enforce thresholds",
            "Set up mutation testing with Stryker, PITest, or mutmut to measure test suite quality",
            "Implement property-based testing with Hypothesis, fast-check, or QuickCheck",
            # CI/CD Quality Gates
            "Design CI quality gates: test stage ordering, parallelisation, sharding, and pass/fail thresholds",
            "Integrate all test types into CI/CD pipelines (GitHub Actions, Jenkins, GitLab CI)",
            "Implement flaky test detection, quarantine, and automatic retry logic in CI",
            "Build test result dashboards and publish reports as CI artifacts",
            # Test Strategy & Metrics
            "Define the test pyramid ratios and enforce them across the codebase",
            "Track and improve test metrics: coverage %, flakiness rate, mean time to green",
            "Conduct test gap analysis against requirements and acceptance criteria",
            "Write testing guidelines and runbooks for the development team",
        ]

    @property
    def best_practices(self) -> List[str]:
        return [
            "Treat test code as production code — same standards for review, naming, and refactoring",
            "Design for testability first: prefer dependency injection and interface-driven design",
            "Follow the test pyramid: maximize unit tests, minimize E2E tests",
            "Each test should verify one behaviour and fail for exactly one reason",
            "Use test doubles (mocks, stubs, fakes) at the right layer — don't mock what you own",
            "Use Testcontainers or equivalent for integration tests that need real infrastructure",
            "Set and enforce coverage thresholds in CI; treat drops as build failures",
            "Run mutation testing periodically to find tests that pass without actually asserting anything",
            "Quarantine flaky tests immediately and track them as first-class bugs",
            "Use property-based testing for boundary conditions and data-driven scenarios",
            "Generate deterministic test data with factories; never depend on prod data snapshots",
            "Keep test suites fast: parallelize, shard, and cache aggressively",
            "Name tests as behaviour specifications: `test_user_cannot_login_with_expired_token`",
            "Write assertion messages that explain what the expected state means, not just the value",
            "Version control test infrastructure alongside application code",
        ]

    @property
    def use_cases(self) -> List[str]:
        return [
            "Designing a unit test framework and folder structure for a new codebase",
            "Refactoring legacy code to be testable without changing behaviour",
            "Building a Testcontainers-based integration test suite for a microservice",
            "Setting up code coverage enforcement in CI with JaCoCo or coverage.py",
            "Implementing mutation testing with Stryker or PITest to validate test quality",
            "Creating a shared test data factory library for a multi-service system",
            "Designing a CI quality gate strategy with parallelisation and sharding",
            "Implementing property-based tests with Hypothesis or fast-check",
            "Building a contract testing layer with Pact between frontend and backend",
            "Setting up a flaky test quarantine process and tracking system",
            "Writing testing guidelines and onboarding docs for a development team",
            "Conducting a test gap analysis against a requirements spec or acceptance checklist",
        ]

    @property
    def capability_tags(self) -> List[str]:
        return ["testing"]
