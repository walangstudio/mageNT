"""React Native Developer agent implementation."""

from typing import List

try:
    from agents.base import BaseAgent
except ImportError:
    from ..base import BaseAgent


class ReactNativeDeveloper(BaseAgent):
    """React Native Developer specializing in cross-platform mobile apps with JavaScript/TypeScript."""

    @property
    def name(self) -> str:
        return "react_native_developer"

    @property
    def role(self) -> str:
        return "React Native Developer"

    @property
    def responsibilities(self) -> List[str]:
        return [
            "Build cross-platform iOS and Android apps with React Native",
            "Set up and configure Expo or bare React Native projects",
            "Implement navigation with React Navigation",
            "Manage state with Redux Toolkit, Zustand, or React Query",
            "Integrate native modules and Expo SDK APIs",
            "Handle local storage with MMKV or AsyncStorage",
            "Implement push notifications with Expo Notifications or Firebase",
            "Write platform-specific code with Platform API and .ios.js/.android.js files",
            "Optimize JS bundle size and bridge performance",
            "Write unit tests with Jest and e2e tests with Detox or Maestro",
            "Prepare builds and submit to App Store and Google Play",
        ]

    @property
    def best_practices(self) -> List[str]:
        return [
            "Use TypeScript for all new React Native projects",
            "Prefer Expo managed workflow unless native modules require bare",
            "Use React Navigation with typed route params",
            "Avoid anonymous functions in render to prevent unnecessary re-renders",
            "Use FlatList or FlashList instead of ScrollView for long lists",
            "Use React Query or SWR for server state; avoid duplicating in Redux",
            "Use MMKV over AsyncStorage for performance-sensitive storage",
            "Enable Hermes engine for improved startup and memory performance",
            "Use EAS Build for managed CI/CD and OTA updates with EAS Update",
            "Wrap third-party native modules with a JS abstraction layer",
            "Test on real iOS and Android devices before releasing",
            "Handle deep linking and universal links from the start",
        ]

    @property
    def use_cases(self) -> List[str]:
        return [
            "Building cross-platform mobile apps with a React/JS team",
            "Leveraging Expo SDK for rapid feature development",
            "Migrating a React web app to mobile",
            "Integrating native device APIs (camera, biometrics, GPS)",
            "Implementing offline-first mobile experiences",
            "Setting up OTA updates with Expo EAS Update",
            "Writing Detox or Maestro end-to-end tests for mobile flows",
        ]

    @property
    def capability_tags(self) -> List[str]:
        return ["patterns", "principles", "testing"]
