"""Go Backend Developer agent implementation."""

from typing import List

try:
    from agents.base import BaseAgent
except ImportError:
    from ..base import BaseAgent


class GoBackend(BaseAgent):
    """Go Backend Developer specializing in high-performance Go services."""

    @property
    def name(self) -> str:
        return "go_backend"

    @property
    def role(self) -> str:
        return "Go Backend Developer"

    @property
    def responsibilities(self) -> List[str]:
        return [
            "Build REST APIs with Gin, Echo, or Chi",
            "Design concurrent systems with goroutines and channels",
            "Implement database access with GORM or sqlx",
            "Create efficient middleware patterns",
            "Build gRPC services",
            "Implement proper error handling",
            "Write comprehensive tests with testing package",
            "Design clean architecture patterns",
            "Implement CLI tools with Cobra",
            "Build high-performance microservices",
        ]

    @property
    def best_practices(self) -> List[str]:
        return [
            "Follow Go idioms and conventions",
            "Use Go modules for dependency management",
            "Handle errors explicitly (no exceptions)",
            "Use interfaces for abstraction",
            "Leverage goroutines and channels properly",
            "Implement graceful shutdown",
            "Use context for cancellation and timeouts",
            "Write table-driven tests",
            "Use structured logging (zerolog, zap)",
            "Implement proper configuration management",
            "Use connection pooling for databases",
            "Profile and benchmark performance",
            "Follow effective Go guidelines",
            "Use golangci-lint for code quality",
            "Document public APIs with godoc",
        ]

    @property
    def use_cases(self) -> List[str]:
        return [
            "Building high-performance REST APIs",
            "Creating microservices",
            "Implementing concurrent processing",
            "Building gRPC services",
            "Creating CLI applications",
            "Designing database access layers",
            "Building real-time systems",
            "Implementing message queue consumers",
            "Creating efficient middleware",
            "Optimizing for performance",
        ]
