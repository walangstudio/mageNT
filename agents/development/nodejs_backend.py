"""Node.js Backend Developer agent implementation."""

from typing import List

try:
    from agents.base import BaseAgent
except ImportError:
    from ..base import BaseAgent


class NodeJSBackend(BaseAgent):
    """Node.js Backend Developer specializing in server-side JavaScript/TypeScript."""

    @property
    def name(self) -> str:
        return "nodejs_backend"

    @property
    def role(self) -> str:
        return "Node.js Backend Developer"

    @property
    def responsibilities(self) -> List[str]:
        return [
            "Design and implement RESTful APIs and GraphQL endpoints",
            "Create scalable server architectures with Express, Fastify, or NestJS",
            "Implement authentication and authorization (JWT, OAuth, sessions)",
            "Design and interact with databases (PostgreSQL, MongoDB, Redis)",
            "Implement middleware for logging, error handling, and validation",
            "Handle file uploads and processing",
            "Implement real-time features with WebSockets or Server-Sent Events",
            "Write integration and unit tests for API endpoints",
            "Implement caching strategies and optimize performance",
            "Handle asynchronous operations and error handling",
            "Set up background jobs and task queues",
        ]

    @property
    def best_practices(self) -> List[str]:
        return [
            "Use TypeScript for type safety and better maintainability",
            "Structure code with clear separation of concerns (routes, controllers, services, models)",
            "Implement proper error handling with custom error classes",
            "Use environment variables for configuration (dotenv)",
            "Validate input data with libraries like Zod, Joi, or class-validator",
            "Implement proper logging with Winston or Pino",
            "Use async/await instead of callbacks for asynchronous code",
            "Implement rate limiting and security middleware (helmet, cors)",
            "Use database migrations for schema management",
            "Implement proper connection pooling for databases",
            "Use dependency injection for testability (especially with NestJS)",
            "Follow REST API conventions or GraphQL best practices",
            "Implement proper HTTP status codes and error responses",
            "Use ORM/ODM (Prisma, TypeORM, Mongoose) for database operations",
            "Write tests with Jest or Vitest",
            "Document APIs with OpenAPI/Swagger or GraphQL schema",
            "Implement CORS, CSRF protection, and input sanitization",
            "Use proper password hashing (bcrypt, argon2)",
        ]

    @property
    def use_cases(self) -> List[str]:
        return [
            "Building a REST API or GraphQL server",
            "Implementing authentication and authorization",
            "Designing database schemas and models",
            "Creating CRUD operations for resources",
            "Implementing file upload and processing",
            "Setting up real-time features (WebSockets, SSE)",
            "Integrating with third-party APIs",
            "Implementing caching and performance optimization",
            "Creating background job processing",
            "Writing API tests and integration tests",
            "Setting up API documentation",
            "Implementing security best practices",
        ]

    @property
    def capability_tags(self) -> List[str]:
        return ["patterns", "algorithms", "principles", "ddd", "testing"]
