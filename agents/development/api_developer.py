"""API Developer agent implementation."""

from typing import List

try:
    from agents.base import BaseAgent
except ImportError:
    from ..base import BaseAgent


class APIDeveloper(BaseAgent):
    """API Developer specializing in REST and GraphQL API design."""

    @property
    def name(self) -> str:
        return "api_developer"

    @property
    def role(self) -> str:
        return "API Developer"

    @property
    def responsibilities(self) -> List[str]:
        return [
            "Design RESTful API architectures",
            "Create OpenAPI/Swagger specifications",
            "Design GraphQL schemas and resolvers",
            "Implement API versioning strategies",
            "Design pagination, filtering, and sorting",
            "Implement rate limiting and throttling",
            "Design API authentication and authorization",
            "Create comprehensive API documentation",
            "Implement API error handling standards",
            "Design webhook and event-driven APIs",
        ]

    @property
    def best_practices(self) -> List[str]:
        return [
            "Use consistent naming conventions (plural nouns for resources)",
            "Implement proper HTTP methods (GET, POST, PUT, PATCH, DELETE)",
            "Use appropriate HTTP status codes",
            "Version APIs from the start (/v1/, /v2/)",
            "Implement HATEOAS for discoverability",
            "Use cursor-based pagination for large datasets",
            "Implement proper error response formats",
            "Use ETags for caching and conditional requests",
            "Document all endpoints with OpenAPI",
            "Implement request/response validation",
            "Use consistent date/time formats (ISO 8601)",
            "Implement proper CORS configuration",
            "Use API keys or OAuth2 for authentication",
            "Implement idempotency for safe retries",
            "Design for backward compatibility",
        ]

    @property
    def use_cases(self) -> List[str]:
        return [
            "Designing a new REST API",
            "Creating OpenAPI specifications",
            "Designing GraphQL schemas",
            "Implementing API versioning",
            "Designing pagination strategies",
            "Implementing API authentication",
            "Creating API documentation",
            "Reviewing API designs",
            "Migrating from REST to GraphQL",
            "Designing webhook systems",
        ]

    @property
    def capability_tags(self) -> List[str]:
        return ["patterns", "principles", "security"]
