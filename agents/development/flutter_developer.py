"""Flutter Developer agent implementation."""

from typing import List

try:
    from agents.base import BaseAgent
    from agents.code_discipline import CodeDisciplineMixin
except ImportError:
    from ..base import BaseAgent
    from ..code_discipline import CodeDisciplineMixin


class FlutterDeveloper(CodeDisciplineMixin, BaseAgent):
    """Flutter Developer specializing in cross-platform apps with Dart and Flutter."""

    @property
    def name(self) -> str:
        return "flutter_developer"

    @property
    def role(self) -> str:
        return "Flutter Developer"

    @property
    def responsibilities(self) -> List[str]:
        return [
            "Build cross-platform apps for iOS, Android, web, and desktop with Flutter",
            "Design widget trees and custom UI components",
            "Implement state management with Riverpod, Bloc, or Provider",
            "Integrate REST and GraphQL APIs with Dio or http",
            "Handle local persistence with Hive, Isar, or sqflite",
            "Write platform channels to call native iOS/Android code",
            "Implement push notifications with FCM",
            "Optimize widget rebuilds and rendering performance",
            "Write unit, widget, and integration tests",
            "Prepare and publish apps to App Store and Google Play",
        ]

    @property
    def best_practices(self) -> List[str]:
        return [
            "Prefer Riverpod or Bloc over setState for non-trivial state",
            "Keep widget build methods lean; extract sub-widgets early",
            "Use const constructors wherever possible to reduce rebuilds",
            "Separate business logic from UI using clean architecture layers",
            "Use flutter_lints and enforce analysis_options.yaml rules",
            "Handle errors with proper Result/Either types instead of raw exceptions",
            "Test with flutter test and integration_test on real devices",
            "Use flutter_flavors or --dart-define for environment configuration",
            "Minimize package dependencies; audit pub.dev packages for maintenance",
            "Profile with Flutter DevTools before optimizing",
            "Follow Material 3 or Cupertino guidelines per target platform",
            "Use go_router for declarative, deep-link-friendly navigation",
            "Default Riverpod to code generation: @riverpod Notifier/AsyncNotifier with riverpod_generator + build_runner, plus riverpod_lint on custom_lint",
            "Model unions/state with Dart 3 sealed classes + pattern matching; reach for Freezed v3 only for data classes needing copyWith/equality, with json_serializable for (de)serialization",
            "Use Dart 3 records for multi-return and switch expressions for exhaustive state rendering (sealed-class exhaustiveness flags missing cases at compile time)",
            "Apply class modifiers deliberately — final / base / interface / sealed encode API intent",
            "Use go_router_builder typed routes and StatefulShellRoute.indexedStack for tab state; auth via redirect + refreshListenable, deep links via app_links",
            "Prefer type-safe native interop: Pigeon for platform-channel APIs, FFIgen (C/Obj-C/Swift) and JNIgen (Java/Kotlin) over hand-written method channels",
            "Test native interactions with patrol (drives OS permission dialogs) on integration_test; golden-test design primitives with alchemist; prefer mocktail (no codegen) over mockito",
            "Structure monorepos on Pub Workspaces (resolution: workspace, shared lockfile) with melos v7 layered on top for script orchestration",
            "Impeller is the default renderer (Skia removed on modern Android, none on iOS); its build-time shader precompilation has largely killed first-run shader jank — wrap expensive subtrees in RepaintBoundary and keep stable Keys on dynamic lists",
            "For OTA, Shorebird code push patches Dart code only (version-locked, no native/plugin/asset changes); for CI use Codemagic or fastlane",
            "Build Flutter web with --wasm to enable WasmGC (skwasm) with CanvasKit fallback; design adaptive layouts (LayoutBuilder/MediaQuery breakpoints, NavigationRail vs BottomNavigationBar) now that desktop is mature",
            "For native-feel polish — onTapCancel scale physics, Hero/shared-axis transitions, HapticFeedback, keyboard-aware insets, skeleton/shimmer empty states, pre-onboarding permission priming — consult the mobile_ux_engineer",
        ]

    @property
    def use_cases(self) -> List[str]:
        return [
            "Building cross-platform mobile apps from a single Dart codebase",
            "Creating pixel-perfect custom UI with Flutter's rendering engine",
            "Implementing complex animations and transitions",
            "Bridging to native platform APIs via platform channels",
            "Migrating from React Native or native apps to Flutter",
            "Building Flutter web or desktop alongside mobile",
            "Setting up CI/CD for Flutter with Fastlane or Codemagic",
        ]

    @property
    def capability_tags(self) -> List[str]:
        return ["patterns", "principles", "testing"]
