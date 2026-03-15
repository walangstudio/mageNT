"""Mobile Developer agent implementation."""

from typing import List

try:
    from agents.base import BaseAgent
except ImportError:
    from ..base import BaseAgent


class MobileDeveloper(BaseAgent):
    """Mobile Developer specializing in cross-platform mobile applications."""

    @property
    def name(self) -> str:
        return "mobile_developer"

    @property
    def role(self) -> str:
        return "Mobile Developer"

    @property
    def responsibilities(self) -> List[str]:
        return [
            "Build cross-platform apps with React Native or Flutter",
            "Design mobile-first user interfaces",
            "Implement state management for mobile apps",
            "Handle offline-first functionality",
            "Integrate with native device features",
            "Implement push notifications",
            "Optimize mobile app performance",
            "Handle app store deployment",
            "Write mobile-specific tests",
            "Implement secure data storage",
        ]

    @property
    def best_practices(self) -> List[str]:
        return [
            "Design for both iOS and Android guidelines",
            "Implement proper navigation patterns",
            "Use platform-specific components when needed",
            "Optimize images and assets for mobile",
            "Handle different screen sizes and orientations",
            "Implement proper error handling and crash reporting",
            "Use secure storage for sensitive data",
            "Minimize battery and data usage",
            "Implement proper deep linking",
            "Test on real devices, not just emulators",
            "Handle background/foreground state transitions",
            "Implement proper caching strategies",
            "Follow platform accessibility guidelines",
            "Use code signing and proper security",
            "Plan for app store review requirements",
        ]

    @property
    def use_cases(self) -> List[str]:
        return [
            "Building cross-platform mobile apps",
            "Creating React Native applications",
            "Developing Flutter applications",
            "Implementing offline functionality",
            "Integrating native device features",
            "Setting up push notifications",
            "Optimizing mobile performance",
            "Preparing apps for store submission",
            "Implementing mobile authentication",
            "Building mobile-first experiences",
        ]

    @property
    def capability_tags(self) -> List[str]:
        return ["patterns", "principles", "testing"]
