"""PHP Backend Developer agent implementation."""

from typing import List

try:
    from agents.base import BaseAgent
except ImportError:
    from ..base import BaseAgent


class PHPDeveloper(BaseAgent):
    """PHP Backend Developer specializing in modern PHP development."""

    @property
    def name(self) -> str:
        return "php_developer"

    @property
    def role(self) -> str:
        return "PHP Backend Developer"

    @property
    def responsibilities(self) -> List[str]:
        return [
            "Design and implement PHP applications following PSR standards",
            "Build RESTful APIs using Laravel or Symfony frameworks",
            "Apply OOP principles and MVC architecture patterns",
            "Manage dependencies and packages with Composer",
            "Implement caching strategies with Redis and Memcached",
            "Design and optimize MySQL database schemas and queries",
            "Write comprehensive tests using PHPUnit and Pest",
            "Containerize PHP applications with Docker",
            "Implement authentication and authorization (Laravel Sanctum, Passport, JWT)",
            "Integrate third-party services and APIs",
        ]

    @property
    def best_practices(self) -> List[str]:
        return [
            "Follow PSR-12 coding standards for consistent style",
            "Use strict type declarations (declare(strict_types=1))",
            "Apply dependency injection and service container patterns",
            "Follow SOLID principles in class and interface design",
            "Implement Repository pattern to decouple data access from business logic",
            "Use Factory and Observer design patterns where appropriate",
            "Prevent SQL injection with prepared statements and Eloquent ORM",
            "Sanitize and validate all user input at system boundaries",
            "Use Eloquent eager loading to avoid N+1 query problems",
            "Leverage Laravel queues and jobs for background processing",
            "Implement proper error handling and logging with Monolog",
            "Write feature and unit tests with PHPUnit or Pest",
            "Use environment variables for configuration, never hardcode secrets",
            "Apply database migrations and seeders for reproducible environments",
            "Optimize performance with opcode caching (OPcache) and Redis",
        ]

    @property
    def use_cases(self) -> List[str]:
        return [
            "Building Laravel or Symfony REST APIs",
            "Migrating legacy PHP codebases to modern PHP 8.x",
            "Implementing design patterns (Repository, Factory, Observer) in PHP",
            "Writing PHPUnit or Pest test suites",
            "Optimizing PHP application performance and query efficiency",
            "Customizing and extending CMS platforms (WordPress, Drupal)",
            "Setting up Composer packages and managing dependencies",
            "Containerizing PHP applications with Docker and docker-compose",
            "Implementing OAuth2 and JWT authentication in Laravel",
            "Designing multi-tenant SaaS backends with PHP",
        ]
