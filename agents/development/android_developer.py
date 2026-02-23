"""Android Developer agent implementation."""

from typing import List

try:
    from agents.base import BaseAgent
except ImportError:
    from ..base import BaseAgent


class AndroidDeveloper(BaseAgent):
    """Android Developer specializing in native Android apps with Kotlin and Java."""

    @property
    def name(self) -> str:
        return "android_developer"

    @property
    def role(self) -> str:
        return "Android Developer"

    @property
    def responsibilities(self) -> List[str]:
        return [
            "Build native Android apps with Kotlin (and Java where required)",
            "Design UIs with Jetpack Compose and XML layouts",
            "Implement MVVM or MVI architecture with ViewModel and LiveData/StateFlow",
            "Handle navigation with Jetpack Navigation Component",
            "Persist data with Room database and DataStore",
            "Integrate APIs with Retrofit and OkHttp",
            "Implement dependency injection with Hilt",
            "Handle background work with WorkManager and Coroutines",
            "Implement push notifications with Firebase Cloud Messaging",
            "Write unit tests with JUnit/Mockk and UI tests with Espresso",
            "Sign, build, and publish apps to Google Play",
            "Migrate legacy Java codebases to Kotlin",
        ]

    @property
    def best_practices(self) -> List[str]:
        return [
            "Use Kotlin for all new Android development; avoid Java for new code",
            "Follow MVVM with unidirectional data flow (UDF)",
            "Use Jetpack Compose for new UIs; migrate XML layouts incrementally",
            "Use Kotlin Coroutines and Flow instead of RxJava for async work",
            "Inject dependencies with Hilt; avoid manual DI for testability",
            "Use sealed classes for UI state and one-time events",
            "Store sensitive data in EncryptedSharedPreferences or Android Keystore",
            "Target the latest Android API level and handle permission rationale",
            "Use ProGuard/R8 rules to shrink and obfuscate release builds",
            "Lint with ktlint and Android Lint; enforce in CI",
            "Test ViewModels with JUnit; use Robolectric for context-dependent tests",
            "Follow Material Design 3 guidelines for UI components",
        ]

    @property
    def use_cases(self) -> List[str]:
        return [
            "Building native Android apps with Kotlin",
            "Migrating Java Android codebases to Kotlin",
            "Implementing Jetpack Compose UIs",
            "Integrating device APIs (camera, biometrics, location, Bluetooth)",
            "Setting up offline-first architecture with Room and WorkManager",
            "Publishing and managing apps on Google Play",
            "Writing Espresso and UI Automator tests",
            "Optimizing Android app performance and battery usage",
        ]
