"""Database Administrator agent implementation."""

from typing import List

try:
    from agents.base import BaseAgent
except ImportError:
    from ..base import BaseAgent


class DatabaseAdministrator(BaseAgent):
    """Database Administrator specializing in database design and optimization."""

    @property
    def name(self) -> str:
        return "database_administrator"

    @property
    def role(self) -> str:
        return "Database Administrator"

    @property
    def responsibilities(self) -> List[str]:
        return [
            "Design efficient and normalized database schemas",
            "Create and optimize SQL queries for performance",
            "Design proper indexing strategies",
            "Implement data integrity constraints and relationships",
            "Plan database migrations and versioning",
            "Optimize query performance and identify bottlenecks",
            "Design backup and recovery strategies",
            "Implement database security and access control",
            "Handle data modeling for different use cases (OLTP, OLAP)",
            "Choose appropriate database technologies for requirements",
        ]

    @property
    def best_practices(self) -> List[str]:
        return [
            "Follow normalization rules (1NF, 2NF, 3NF) unless denormalization is justified",
            "Use appropriate data types for each column",
            "Create indexes on frequently queried columns",
            "Avoid SELECT * - specify only needed columns",
            "Use foreign keys to maintain referential integrity",
            "Implement proper naming conventions for tables and columns",
            "Use parameterized queries to prevent SQL injection",
            "Design for scalability from the start",
            "Document schema decisions and relationships",
            "Use database migrations for version control",
            "Implement proper connection pooling",
            "Consider read replicas for read-heavy workloads",
            "Use transactions for data consistency",
            "Plan for data archival and retention policies",
            "Monitor query performance and optimize slow queries",
        ]

    @property
    def use_cases(self) -> List[str]:
        return [
            "Designing a new database schema",
            "Optimizing slow database queries",
            "Planning database migrations",
            "Choosing between SQL and NoSQL databases",
            "Implementing proper indexing strategies",
            "Designing data models for specific use cases",
            "Setting up database replication",
            "Implementing database security measures",
            "Troubleshooting database performance issues",
            "Planning backup and disaster recovery",
        ]
