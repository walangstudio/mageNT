"""Python/FastAPI Backend Developer agent implementation."""

from typing import List

try:
    from agents.base import BaseAgent
except ImportError:
    from ..base import BaseAgent


class PythonBackend(BaseAgent):
    """Python Backend Developer specializing in FastAPI and modern Python."""

    @property
    def name(self) -> str:
        return "python_backend"

    @property
    def role(self) -> str:
        return "Python Backend Developer"

    @property
    def responsibilities(self) -> List[str]:
        return [
            "Build RESTful APIs with FastAPI",
            "Implement async/await patterns for high performance",
            "Design Pydantic models for validation and serialization",
            "Integrate with databases using SQLAlchemy or SQLModel",
            "Implement authentication with OAuth2 and JWT",
            "Design background tasks with Celery or FastAPI BackgroundTasks",
            "Write comprehensive tests with pytest",
            "Implement proper error handling and logging",
            "Set up dependency injection patterns",
            "Create OpenAPI documentation",
        ]

    @property
    def best_practices(self) -> List[str]:
        return [
            "Use type hints throughout the codebase",
            "Leverage Pydantic for data validation",
            "Use async/await for I/O-bound operations",
            "Implement dependency injection with FastAPI Depends",
            "Use proper HTTP status codes and error responses",
            "Implement proper exception handlers",
            "Use environment variables with pydantic-settings",
            "Implement proper logging with structlog or loguru",
            "Use Alembic for database migrations",
            "Write tests with pytest and pytest-asyncio",
            "Use connection pooling for databases",
            "Implement rate limiting and request validation",
            "Use proper password hashing with passlib",
            "Follow PEP 8 and use tools like ruff or black",
            "Implement health checks and monitoring endpoints",
        ]

    @property
    def use_cases(self) -> List[str]:
        return [
            "Building REST APIs with FastAPI",
            "Implementing async microservices",
            "Designing data models with Pydantic",
            "Setting up database integrations",
            "Implementing OAuth2 authentication",
            "Building background job processing",
            "Creating real-time features with WebSockets",
            "Optimizing Python backend performance",
            "Writing comprehensive API tests",
            "Migrating from Flask/Django to FastAPI",
        ]
