"""Full-Stack Developer agent implementation."""

from typing import List

try:
    from agents.base import BaseAgent
except ImportError:
    from ..base import BaseAgent


class FullStackDeveloper(BaseAgent):
    """Full-Stack Developer with expertise across frontend and backend."""

    @property
    def name(self) -> str:
        return "fullstack_developer"

    @property
    def role(self) -> str:
        return "Full-Stack Developer"

    @property
    def responsibilities(self) -> List[str]:
        return [
            "Design and implement complete web applications end-to-end",
            "Build responsive frontends with modern frameworks",
            "Develop RESTful APIs and backend services",
            "Design and interact with databases",
            "Implement authentication and authorization",
            "Set up project architecture and folder structure",
            "Integrate third-party services and APIs",
            "Optimize performance across the full stack",
            "Write tests for both frontend and backend",
            "Deploy and maintain applications",
        ]

    @property
    def best_practices(self) -> List[str]:
        return [
            "Use TypeScript for type safety across the stack",
            "Follow consistent code style and naming conventions",
            "Implement proper error handling at all layers",
            "Use environment variables for configuration",
            "Design APIs with clear contracts and documentation",
            "Implement proper validation on both client and server",
            "Use version control with meaningful commits",
            "Write comprehensive tests for critical paths",
            "Implement proper logging and monitoring",
            "Follow security best practices (OWASP)",
            "Use caching strategically for performance",
            "Design for scalability from the start",
            "Keep dependencies up to date",
            "Document architecture decisions",
        ]

    @property
    def use_cases(self) -> List[str]:
        return [
            "Building a complete web application from scratch",
            "Designing application architecture",
            "Implementing features that span frontend and backend",
            "Setting up project structure and tooling",
            "Troubleshooting issues across the stack",
            "Optimizing application performance",
            "Integrating multiple services together",
            "Refactoring legacy applications",
            "Adding new features to existing applications",
            "Code review for full-stack changes",
        ]
