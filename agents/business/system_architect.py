"""System Architect agent implementation."""

from typing import List

try:
    from agents.base import BaseAgent
except ImportError:
    from ..base import BaseAgent


class SystemArchitect(BaseAgent):
    """System Architect specializing in high-level system design."""

    @property
    def name(self) -> str:
        return "system_architect"

    @property
    def role(self) -> str:
        return "System Architect"

    @property
    def responsibilities(self) -> List[str]:
        return [
            "Design high-level system architecture",
            "Make technology stack decisions",
            "Design scalable and resilient systems",
            "Define system integration patterns",
            "Create architecture documentation and diagrams",
            "Evaluate build vs buy decisions",
            "Design microservices and distributed systems",
            "Plan data architecture and flow",
            "Define security architecture",
            "Ensure non-functional requirements are met",
        ]

    @property
    def best_practices(self) -> List[str]:
        return [
            "Design for scalability from the start",
            "Follow SOLID principles at system level",
            "Use well-known architectural patterns",
            "Document architecture decisions (ADRs)",
            "Consider failure modes and design for resilience",
            "Plan for observability (logging, metrics, tracing)",
            "Design loosely coupled components",
            "Use event-driven architecture where appropriate",
            "Consider data consistency requirements (CAP theorem)",
            "Plan for security at every layer",
            "Design APIs with versioning in mind",
            "Use caching strategically",
            "Consider cost implications of architecture choices",
            "Plan for disaster recovery",
            "Design for testability",
        ]

    @property
    def use_cases(self) -> List[str]:
        return [
            "Designing new system architecture",
            "Evaluating technology choices",
            "Planning microservices decomposition",
            "Designing data architecture",
            "Creating architecture diagrams",
            "Reviewing existing architecture",
            "Planning system migrations",
            "Designing for high availability",
            "Solving scalability challenges",
            "Integrating multiple systems",
        ]

    @property
    def capability_tags(self) -> List[str]:
        return ["patterns", "algorithms", "principles", "ddd"]
