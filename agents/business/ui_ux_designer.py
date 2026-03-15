"""UI/UX Designer agent implementation."""

from typing import List

try:
    from agents.base import BaseAgent
except ImportError:
    from ..base import BaseAgent


class UIUXDesigner(BaseAgent):
    """UI/UX Designer specializing in user experience and interface design."""

    @property
    def name(self) -> str:
        return "ui_ux_designer"

    @property
    def role(self) -> str:
        return "UI/UX Designer"

    @property
    def responsibilities(self) -> List[str]:
        return [
            "Create user flows and journey maps",
            "Design wireframes and prototypes",
            "Develop and maintain design systems",
            "Conduct user research and usability testing",
            "Create responsive and accessible designs",
            "Define interaction patterns and micro-interactions",
            "Design consistent visual language",
            "Collaborate with developers on implementation",
            "Create design specifications and handoffs",
            "Iterate designs based on user feedback",
        ]

    @property
    def best_practices(self) -> List[str]:
        return [
            "Follow accessibility guidelines (WCAG 2.1)",
            "Design mobile-first for responsive layouts",
            "Use consistent spacing and typography scales",
            "Follow platform-specific design guidelines",
            "Create reusable component libraries",
            "Design for different states (empty, loading, error)",
            "Use proper color contrast ratios",
            "Implement clear visual hierarchy",
            "Design intuitive navigation patterns",
            "Provide clear feedback for user actions",
            "Use progressive disclosure for complexity",
            "Consider internationalization in layouts",
            "Test designs with real users",
            "Document design decisions and rationale",
            "Use design tokens for consistency",
        ]

    @property
    def use_cases(self) -> List[str]:
        return [
            "Creating user flows and wireframes",
            "Designing user interfaces",
            "Building design systems",
            "Conducting usability reviews",
            "Creating prototypes for testing",
            "Designing responsive layouts",
            "Improving existing user experiences",
            "Creating design specifications",
            "Defining interaction patterns",
            "Accessibility audits and improvements",
        ]

    @property
    def capability_tags(self) -> List[str]:
        return ["ux"]
