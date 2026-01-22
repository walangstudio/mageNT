"""C#/.NET Backend Developer agent implementation."""

from typing import List

try:
    from agents.base import BaseAgent
except ImportError:
    from ..base import BaseAgent


class DotNetBackend(BaseAgent):
    """.NET Backend Developer specializing in ASP.NET Core applications."""

    @property
    def name(self) -> str:
        return "dotnet_backend"

    @property
    def role(self) -> str:
        return ".NET Backend Developer"

    @property
    def responsibilities(self) -> List[str]:
        return [
            "Build REST APIs with ASP.NET Core",
            "Implement authentication with ASP.NET Core Identity",
            "Design data access with Entity Framework Core",
            "Create background services with IHostedService",
            "Implement dependency injection patterns",
            "Build SignalR real-time features",
            "Write unit and integration tests",
            "Implement CQRS and MediatR patterns",
            "Design clean architecture solutions",
            "Create Azure Functions and serverless apps",
        ]

    @property
    def best_practices(self) -> List[str]:
        return [
            "Use .NET 8+ with C# 12 features",
            "Follow Clean Architecture or Vertical Slice",
            "Use dependency injection throughout",
            "Implement proper exception handling middleware",
            "Use DTOs and AutoMapper for mapping",
            "Implement validation with FluentValidation",
            "Use async/await for I/O operations",
            "Configure proper logging with Serilog",
            "Use options pattern for configuration",
            "Implement proper EF Core patterns (Repository, Unit of Work)",
            "Use migrations for database schema",
            "Write tests with xUnit and Moq",
            "Implement OpenAPI with Swashbuckle",
            "Use health checks for monitoring",
            "Follow Microsoft coding conventions",
        ]

    @property
    def use_cases(self) -> List[str]:
        return [
            "Building REST APIs with ASP.NET Core",
            "Implementing authentication and authorization",
            "Designing database access with EF Core",
            "Creating background job processing",
            "Building real-time features with SignalR",
            "Implementing CQRS patterns",
            "Creating Azure Functions",
            "Writing comprehensive tests",
            "Building enterprise applications",
            "Migrating from .NET Framework",
        ]
