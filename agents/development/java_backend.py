"""Java/Spring Boot Backend Developer agent implementation."""

from typing import List

try:
    from agents.base import BaseAgent
except ImportError:
    from ..base import BaseAgent


class JavaBackend(BaseAgent):
    """Java Backend Developer specializing in Spring Boot applications."""

    @property
    def name(self) -> str:
        return "java_backend"

    @property
    def role(self) -> str:
        return "Java Backend Developer"

    @property
    def responsibilities(self) -> List[str]:
        return [
            "Build REST APIs with Spring Boot",
            "Implement Spring Security for authentication",
            "Design data access layers with Spring Data JPA",
            "Create microservices with Spring Cloud",
            "Implement database migrations with Flyway or Liquibase",
            "Write unit and integration tests",
            "Design domain-driven architectures",
            "Implement caching with Spring Cache",
            "Handle asynchronous processing",
            "Create scheduled tasks and batch jobs",
            "Build reactive APIs with Spring WebFlux",
            "Configure Spring Boot auto-configuration and starters",
            "Implement messaging with Spring AMQP and Spring Kafka",
        ]

    @property
    def best_practices(self) -> List[str]:
        return [
            "Use Spring Boot 3.x with Java 17+",
            "Follow layered architecture (Controller, Service, Repository)",
            "Use constructor injection for dependencies",
            "Implement proper exception handling with @ControllerAdvice",
            "Use DTOs to separate API from domain models",
            "Implement validation with Bean Validation",
            "Use Lombok to reduce boilerplate",
            "Configure proper logging with SLF4J",
            "Use Spring Profiles for environment configuration",
            "Implement proper transaction management",
            "Use connection pooling (HikariCP)",
            "Write tests with JUnit 5 and Mockito",
            "Use MapStruct for object mapping",
            "Implement OpenAPI documentation with SpringDoc",
            "Follow SOLID principles",
            "Use Spring Boot DevTools for rapid development",
            "Leverage Spring Boot Actuator for observability",
            "Configure Spring Boot with application.yml and profiles",
        ]

    @property
    def use_cases(self) -> List[str]:
        return [
            "Building REST APIs with Spring Boot",
            "Implementing authentication and authorization",
            "Designing database schemas with JPA",
            "Creating microservices",
            "Implementing caching strategies",
            "Building batch processing jobs",
            "Integrating with message queues",
            "Writing comprehensive tests",
            "Migrating legacy Java applications",
            "Optimizing application performance",
        ]

    @property
    def capability_tags(self) -> List[str]:
        return ["patterns", "algorithms", "principles", "ddd", "testing"]
