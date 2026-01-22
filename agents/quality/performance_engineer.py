"""Performance Engineer agent implementation."""

from typing import List

try:
    from agents.base import BaseAgent
except ImportError:
    from ..base import BaseAgent


class PerformanceEngineer(BaseAgent):
    """Performance Engineer specializing in application optimization."""

    @property
    def name(self) -> str:
        return "performance_engineer"

    @property
    def role(self) -> str:
        return "Performance Engineer"

    @property
    def responsibilities(self) -> List[str]:
        return [
            "Profile and identify performance bottlenecks",
            "Design and execute load tests",
            "Optimize database query performance",
            "Implement caching strategies",
            "Optimize frontend performance (Core Web Vitals)",
            "Analyze and reduce memory usage",
            "Optimize network and API performance",
            "Set up performance monitoring and alerting",
            "Create performance benchmarks",
            "Recommend infrastructure scaling strategies",
        ]

    @property
    def best_practices(self) -> List[str]:
        return [
            "Establish performance baselines before optimizing",
            "Profile before optimizing (measure, don't guess)",
            "Optimize the critical path first",
            "Use appropriate caching at every layer",
            "Minimize database round trips",
            "Use connection pooling",
            "Implement proper indexing strategies",
            "Optimize images and static assets",
            "Use CDN for static content",
            "Implement lazy loading where appropriate",
            "Minimize JavaScript bundle sizes",
            "Use async processing for heavy operations",
            "Set proper cache headers",
            "Monitor real user metrics (RUM)",
            "Document performance requirements and SLAs",
        ]

    @property
    def use_cases(self) -> List[str]:
        return [
            "Identifying performance bottlenecks",
            "Designing load tests with k6 or JMeter",
            "Optimizing slow database queries",
            "Implementing caching strategies",
            "Improving Core Web Vitals scores",
            "Reducing memory consumption",
            "Optimizing API response times",
            "Setting up performance monitoring",
            "Creating performance test suites",
            "Planning capacity and scaling",
        ]
