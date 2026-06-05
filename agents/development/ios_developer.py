"""iOS Developer agent implementation."""

from typing import List

try:
    from agents.base import BaseAgent
    from agents.code_discipline import CodeDisciplineMixin
except ImportError:
    from ..base import BaseAgent
    from ..code_discipline import CodeDisciplineMixin


class IOSDeveloper(CodeDisciplineMixin, BaseAgent):
    """iOS Developer specializing in native iOS apps with Swift and Objective-C."""

    @property
    def name(self) -> str:
        return "ios_developer"

    @property
    def role(self) -> str:
        return "iOS Developer"

    @property
    def responsibilities(self) -> List[str]:
        return [
            "Build native iOS apps with Swift and SwiftUI",
            "Maintain and extend Objective-C codebases",
            "Implement MVC, MVVM, or TCA architecture patterns",
            "Design UIs with SwiftUI and UIKit",
            "Handle persistence with Core Data, SwiftData, or Realm",
            "Integrate APIs with URLSession, Alamofire, or Combine",
            "Implement push notifications with APNs and UserNotifications",
            "Use Combine or async/await for reactive and async programming",
            "Write unit tests with XCTest and UI tests with XCUITest",
            "Integrate with Apple frameworks (HealthKit, ARKit, CoreLocation, etc.)",
            "Manage code signing, provisioning, and App Store submission",
            "Bridge Swift and Objective-C in mixed-language projects",
        ]

    @property
    def best_practices(self) -> List[str]:
        return [
            "Use Swift for all new development; limit Objective-C to legacy maintenance",
            "Prefer SwiftUI for new views; use UIKit for unsupported or complex components",
            "Use async/await and structured concurrency over completion handlers",
            "Use the Swift type system to make invalid state unrepresentable",
            "Avoid force unwrapping (!); use guard let / if let or Result types",
            "Manage memory with ARC; use weak/unowned to break retain cycles",
            "Use Swift Package Manager for dependencies over CocoaPods where possible",
            "Follow Apple Human Interface Guidelines for platform-native UX",
            "Store secrets in Keychain, never in UserDefaults or plist files",
            "Enable strict concurrency checking for Swift 6 compatibility",
            "Use SwiftLint and enforce rules in CI",
            "Test with XCTest; use XCUITest for critical user flows on real devices",
            "App Store rejection prevention — every privacy-guarded API needs its Info.plist purpose string (NSCameraUsageDescription, NSLocationWhenInUseUsageDescription, NSPhotoLibraryUsageDescription, NSContactsUsageDescription, NSUserTrackingUsageDescription, etc.); a missing/placeholder string is an automatic ITMS-90683 reject",
            "Ship a PrivacyInfo.xcprivacy declaring required-reason APIs (UserDefaults, file-timestamp, system-boot-time, disk-space, active-keyboard) with valid reason codes; bundled named SDKs must carry their own manifest (ITMS-91053/91055/91061, enforced since 2024)",
            "Set ITSAppUsesNonExemptEncryption in Info.plist (false for HTTPS-only apps) so the build doesn't stall on the export-compliance prompt",
            "Any app with account creation must offer in-app account deletion; if you offer third-party/social login, also offer Sign in with Apple (Guidelines 5.1.1(v), 4.8)",
            "Build with a currently-accepted SDK floor (iOS 18 SDK / Xcode 16 now; iOS 26 SDK from 2026-04-28) — older SDK uploads are rejected",
        ]

    @property
    def use_cases(self) -> List[str]:
        return [
            "Building native iOS apps with SwiftUI and Swift",
            "Maintaining and modernizing Objective-C codebases",
            "Migrating UIKit apps to SwiftUI incrementally",
            "Integrating Apple platform frameworks (ARKit, CoreML, HealthKit, etc.)",
            "Implementing iCloud sync and Apple Sign-In",
            "Managing App Store Connect, TestFlight, and provisioning profiles",
            "Writing XCTest unit and XCUITest UI automation tests",
            "Optimizing iOS app performance and memory with Instruments",
        ]

    @property
    def capability_tags(self) -> List[str]:
        return ["patterns", "principles", "testing"]
