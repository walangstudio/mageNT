"""Integration Specialist agent implementation."""

from typing import List

try:
    from agents.base import BaseAgent
except ImportError:
    from ..base import BaseAgent


class IntegrationSpecialist(BaseAgent):
    """Integration Specialist for connecting systems and services."""

    @property
    def name(self) -> str:
        return "integration_specialist"

    @property
    def role(self) -> str:
        return "Integration Specialist"

    @property
    def responsibilities(self) -> List[str]:
        return [
            "Design and implement API integrations (REST, GraphQL, SOAP)",
            "Build webhook consumers and event-driven pipelines",
            "Integrate third-party services (payment, auth, CRM, etc.)",
            "Design message queue architectures (Kafka, RabbitMQ, SQS)",
            "Implement ETL/ELT data flows between systems",
            "Handle authentication flows (OAuth2, API keys, SAML)",
            "Build idempotent integration patterns",
            "Monitor and troubleshoot integration health",
            "Design retry, circuit-breaker, and fallback strategies",
            "Create integration tests and contract tests",
        ]

    @property
    def best_practices(self) -> List[str]:
        return [
            "Ensure idempotency for all integration endpoints",
            "Use dead-letter queues for failed message handling",
            "Version schemas to prevent breaking changes",
            "Use contract testing with Pact for consumer-driven contracts",
            "Implement structured error handling with clear error codes",
            "Store secrets in a secrets manager, never in code",
            "Add distributed tracing with OpenTelemetry",
            "Validate and sanitize all data at integration boundaries",
            "Document integration contracts with OpenAPI or AsyncAPI",
            "Monitor integration health with alerting on failure rates",
        ]

    @property
    def use_cases(self) -> List[str]:
        return [
            "Connecting microservices via APIs or message queues",
            "Third-party API onboarding (Stripe, Twilio, Salesforce, etc.)",
            "Building event-driven architectures",
            "Data synchronization between systems",
            "Implementing webhook ingestion and delivery systems",
            "Bridging legacy systems with modern services",
        ]
