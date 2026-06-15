"""Cross-platform mobile project detection + static store-review detectors.

Backs the app_store_check skill. Unlike the guidance-only blocks that ship in
app_store_check.py, this module actually reads the project: it detects the
framework (native iOS/Android, Expo, React Native, Flutter, Tauri,
Capacitor/Cordova), resolves the real manifest surfaces to scan, runs static
detectors for the mechanically-checkable Apple App Store / Google Play rejection
rules, and renders a findings table + an accept/reject verdict.

Heuristic checks (e.g. "API used but purpose string missing") are reported as
`warn`, not `fail`, so they surface without hard-failing on a guess. Only
deterministic checks (empty purpose string, missing `android:exported`,
target SDK below floor) drive a LIKELY-REJECT verdict.
"""

from __future__ import annotations

import json
import os
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Floors are date-gated; bump these as Apple/Google move the line.
ANDROID_TARGET_SDK_FLOOR = 35          # new apps + updates since 2025-08-31
IOS_SDK_FLOOR_NOTE = "iOS 18 SDK / Xcode 16 now; iOS 26 SDK from 2026-04-28"

ANDROID_NS = "http://schemas.android.com/apk/res/android"

# Directories that never hold first-party submission surfaces; skip for speed
# and to avoid false signals from vendored SDKs.
_SKIP_DIRS = {
    "node_modules", "Pods", "build", ".git", "DerivedData", ".dart_tool",
    ".gradle", ".expo", "dist", "vendor", ".idea", ".vscode", "Carthage",
    "__pycache__", ".next", "coverage",
}

_SRC_EXTS = {
    ".swift", ".m", ".mm", ".h", ".kt", ".java", ".dart",
    ".js", ".jsx", ".ts", ".tsx",
}
_MAX_SRC_FILES = 600
_MAX_FILE_BYTES = 400_000

_PLACEHOLDER_PURPOSE = {
    "", "todo", "description", "your usage description", "usage description",
    "permission", "string", "none", "n/a", "tbd",
}

# concept -> iOS Info.plist purpose key it requires
_IOS_PURPOSE_KEYS: Dict[str, str] = {
    "camera": "NSCameraUsageDescription",
    "microphone": "NSMicrophoneUsageDescription",
    "location": "NSLocationWhenInUseUsageDescription",
    "contacts": "NSContactsUsageDescription",
    "photos": "NSPhotoLibraryUsageDescription",
    "tracking": "NSUserTrackingUsageDescription",
    "calendar": "NSCalendarsUsageDescription",
    "motion": "NSMotionUsageDescription",
    "bluetooth": "NSBluetoothAlwaysUsageDescription",
    "faceid": "NSFaceIDUsageDescription",
    "speech": "NSSpeechRecognitionUsageDescription",
}

# concept -> regexes that indicate the capability is used (first-party src+config)
_SIGNAL_PATTERNS: Dict[str, List[str]] = {
    "camera": [r"AVCaptureDevice", r"UIImagePickerController", r"expo-camera",
               r"react-native-vision-camera", r"react-native-camera",
               r"\bimage_picker\b", r"Permission\.CAMERA"],
    "microphone": [r"AVAudioSession", r"expo-av\b", r"react-native-audio",
                   r"RECORD_AUDIO", r"Permission\.(MICROPHONE|RECORD_AUDIO)"],
    "location": [r"CLLocationManager", r"expo-location", r"geolocator\b",
                 r"react-native-geolocation", r"ACCESS_FINE_LOCATION",
                 r"@react-native-community/geolocation"],
    "contacts": [r"CNContactStore", r"expo-contacts", r"react-native-contacts",
                 r"READ_CONTACTS", r"flutter_contacts"],
    "photos": [r"PHPhotoLibrary", r"PHPickerViewController", r"expo-media-library",
               r"READ_MEDIA_IMAGES", r"\bphoto_manager\b"],
    "tracking": [r"ATTrackingManager", r"requestTrackingAuthorization",
                 r"AppTrackingTransparency", r"expo-tracking-transparency",
                 r"com\.google\.android\.gms\.permission\.AD_ID"],
    "calendar": [r"EKEventStore", r"expo-calendar", r"READ_CALENDAR"],
    "motion": [r"CMMotionManager", r"CMPedometer", r"expo-sensors",
               r"ACTIVITY_RECOGNITION"],
    "bluetooth": [r"CBCentralManager", r"expo-bluetooth", r"react-native-ble",
                  r"BLUETOOTH_CONNECT"],
    "faceid": [r"NSFaceIDUsageDescription", r"LAContext", r"expo-local-authentication",
               r"local_auth\b"],
    "speech": [r"SFSpeechRecognizer", r"expo-speech"],
    "account": [r"\bsignUp\b", r"\bsignIn\b", r"createUser", r"\blogin\b",
                r"firebase/auth", r"supabase\.auth", r"Auth0",
                r"createUserWithEmail"],
    "delete_account": [r"delete[\s_-]?account", r"deleteUser", r"deleteAccount",
                       r"account[\s_-]?deletion", r"removeAccount"],
    "social_login": [r"GoogleSignIn", r"FBSDKLoginKit", r"react-native-fbsdk",
                     r"@react-native-google-signin", r"LoginManager",
                     r"signInWithFacebook", r"signInWithGoogle", r"google_sign_in",
                     r"flutter_facebook_auth"],
    "siwa": [r"ASAuthorizationAppleIDProvider", r"SignInWithApple",
             r"expo-apple-authentication", r"@invertase/react-native-apple-authentication",
             r"sign_in_with_apple"],
    "payment_sdk": [r"\bStripe\b", r"@stripe/stripe-react-native", r"tipsi-stripe",
                    r"\bBraintree\b", r"\bPayPal\b", r"flutter_stripe",
                    r"razorpay"],
    "privacy_policy": [r"privacy[\s_-]?policy", r"privacyPolicy", r"/privacy"],
    "ads": [r"react-native-google-mobile-ads", r"google_mobile_ads", r"AdMob",
            r"GADBannerView", r"AppLovin", r"expo-ads", r"com\.google\.android\.gms\.ads"],
}

_COMPILED_SIGNALS = {
    concept: [re.compile(p, re.IGNORECASE) for p in pats]
    for concept, pats in _SIGNAL_PATTERNS.items()
}

# Required-reason API trigger symbols (privacy manifest); presence in source
# means a PrivacyInfo.xcprivacy must declare the matching category.
_REQUIRED_REASON_SYMBOLS = [
    "UserDefaults", "NSUserDefaults", "systemUptime", "mach_absolute_time",
    ".modificationDate", "getattrlist", "statfs", "statvfs",
    "volumeAvailableCapacity", "activeInputModes",
]

# Android permissions that need a Play Console declaration / prominent disclosure.
_ANDROID_SENSITIVE_PERMS = [
    "ACCESS_BACKGROUND_LOCATION", "QUERY_ALL_PACKAGES", "MANAGE_EXTERNAL_STORAGE",
    "SEND_SMS", "READ_SMS", "RECEIVE_SMS", "READ_CALL_LOG", "WRITE_CALL_LOG",
    "PROCESS_OUTGOING_CALLS",
]


# --------------------------------------------------------------------------- #
# Data model
# --------------------------------------------------------------------------- #
@dataclass
class MobileProject:
    root: Path
    frameworks: List[str] = field(default_factory=list)
    stores: List[str] = field(default_factory=list)
    ios_surfaces: List[Path] = field(default_factory=list)
    android_surfaces: List[Path] = field(default_factory=list)
    config_files: List[Path] = field(default_factory=list)
    so_files: List[Path] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    @property
    def recognized(self) -> bool:
        return bool(self.frameworks)


@dataclass
class Finding:
    id: str
    store: str            # "ios" | "android"
    title: str
    severity: str         # "HARD" | "SOFT"
    status: str           # "pass" | "fail" | "warn" | "unknown"
    ref: str
    evidence: str = ""
    fix: str = ""


# --------------------------------------------------------------------------- #
# Filesystem helpers
# --------------------------------------------------------------------------- #
def _read_text(path: Path) -> str:
    try:
        if path.stat().st_size > _MAX_FILE_BYTES:
            return path.read_text(encoding="utf-8", errors="replace")[:_MAX_FILE_BYTES]
        return path.read_text(encoding="utf-8", errors="replace")
    except (OSError, ValueError):
        return ""


def _rel(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _lineno(text: str, idx: int) -> int:
    return text.count("\n", 0, idx) + 1


def _walk(root: Path):
    """Yield (dirpath, filenames), pruning heavy/vendored dirs."""
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
        yield Path(dirpath), filenames


# --------------------------------------------------------------------------- #
# Detection
# --------------------------------------------------------------------------- #
def detect_mobile_project(root: Path) -> MobileProject:
    root = Path(root).resolve()
    proj = MobileProject(root=root)

    info_plists: List[Path] = []
    xcprivacy: List[Path] = []
    pbxproj: List[Path] = []
    android_manifests: List[Path] = []
    gradle: List[Path] = []
    so_files: List[Path] = []
    config_files: List[Path] = []

    config_names = {
        "app.json", "app.config.js", "app.config.ts", "eas.json", "package.json",
        "pubspec.yaml", "tauri.conf.json", "capacitor.config.json",
        "capacitor.config.ts", "capacitor.config.js", "config.xml", "Podfile",
    }

    for dirpath, filenames in _walk(root):
        for name in filenames:
            p = dirpath / name
            low = name.lower()
            if name == "Info.plist" or low.endswith("-info.plist"):
                info_plists.append(p)
            elif low.endswith(".xcprivacy"):
                xcprivacy.append(p)
            elif name == "project.pbxproj":
                pbxproj.append(p)
            elif name == "AndroidManifest.xml":
                android_manifests.append(p)
            elif name in ("build.gradle", "build.gradle.kts"):
                gradle.append(p)
            elif low.endswith(".so"):
                so_files.append(p)
            elif name in config_names:
                config_files.append(p)

    cfg_by_name = {p.name: p for p in config_files}

    def _cfg_text(name: str) -> str:
        p = cfg_by_name.get(name)
        return _read_text(p) if p else ""

    frameworks: List[str] = []

    # Tauri
    if (root / "src-tauri" / "tauri.conf.json").exists() or "tauri.conf.json" in cfg_by_name:
        frameworks.append("tauri")
    # Flutter
    if "flutter:" in _cfg_text("pubspec.yaml") or "sdk: flutter" in _cfg_text("pubspec.yaml"):
        frameworks.append("flutter")
    # Expo vs bare React Native
    app_json = _cfg_text("app.json")
    has_expo = (
        '"expo"' in app_json
        or "app.config.js" in cfg_by_name
        or "app.config.ts" in cfg_by_name
        or "expo" in _cfg_text("package.json")
    )
    pkg = _cfg_text("package.json")
    has_rn = bool(re.search(r'"react-native"\s*:', pkg))
    if has_expo:
        frameworks.append("expo")
    elif has_rn:
        frameworks.append("react_native")
    # Capacitor / Cordova (hybrid webviews)
    if any(n.startswith("capacitor.config") for n in cfg_by_name):
        frameworks.append("capacitor")
    if "config.xml" in cfg_by_name and "cordova" in _cfg_text("config.xml").lower():
        frameworks.append("cordova")

    cross = {"expo", "react_native", "flutter", "capacitor", "cordova"}
    if not (set(frameworks) & cross) and "tauri" not in frameworks:
        if info_plists or pbxproj:
            frameworks.append("native_ios")
        if android_manifests or gradle:
            frameworks.append("native_android")

    # Resolve stores in scope + surfaces
    stores: List[str] = []
    ios_surfaces = info_plists + xcprivacy + pbxproj
    android_surfaces = _pick_main_manifests(android_manifests) + gradle

    if set(frameworks) & cross:
        stores = ["ios", "android"]
        if not info_plists and not pbxproj:
            proj.notes.append(
                "Native iOS project not generated yet — run the prebuild/native "
                "build (e.g. `expo prebuild`, `flutter build ios`) then re-run for "
                "Info.plist / privacy-manifest checks."
            )
        if not android_manifests:
            proj.notes.append(
                "Native Android project not generated yet — run the prebuild/native "
                "build then re-run for AndroidManifest checks."
            )
    else:
        if "native_ios" in frameworks or info_plists or pbxproj:
            stores.append("ios")
        if "native_android" in frameworks or android_manifests or gradle:
            stores.append("android")

    if "tauri" in frameworks:
        gen_apple = (root / "src-tauri" / "gen" / "apple").exists()
        gen_android = (root / "src-tauri" / "gen" / "android").exists()
        if gen_apple or info_plists:
            if "ios" not in stores:
                stores.append("ios")
        if gen_android or android_manifests:
            if "android" not in stores:
                stores.append("android")
        if not gen_apple and not gen_android and not info_plists and not android_manifests:
            proj.notes.append(
                "Tauri desktop project, or mobile targets not initialized — run "
                "`tauri ios init` / `tauri android init` to generate native "
                "projects for store checks."
            )

    proj.frameworks = frameworks
    proj.stores = stores
    proj.ios_surfaces = ios_surfaces
    proj.android_surfaces = android_surfaces
    proj.config_files = config_files
    proj.so_files = so_files
    return proj


def _pick_main_manifests(manifests: List[Path]) -> List[Path]:
    """Prefer src/main manifests; fall back to all if none match."""
    main = [m for m in manifests if "src/main" in str(m).replace("\\", "/")]
    return main or manifests


def _safe_xml_root(path: Path) -> Optional[ET.Element]:
    """Parse XML, refusing any DTD/entity content (XXE / billion-laughs guard).

    AndroidManifest.xml never legitimately carries a DOCTYPE or ENTITY, so a
    file that does is hostile; skip it rather than expand it.
    """
    text = _read_text(path)
    if not text or "<!DOCTYPE" in text or "<!ENTITY" in text:
        return None
    try:
        return ET.fromstring(text)
    except ET.ParseError:
        return None


# --------------------------------------------------------------------------- #
# Signal collection (bounded first-party scan)
# --------------------------------------------------------------------------- #
_RR_RX = re.compile("|".join(re.escape(s) for s in _REQUIRED_REASON_SYMBOLS))


def _collect_signals(proj: MobileProject) -> Dict[str, str]:
    """Map concept -> 'file:line' of the first matching evidence.

    A single bounded walk feeds every detector: capability concepts plus the
    privacy-manifest required-reason symbols (stored under ``__required_reason__``).
    Required-reason symbols (UserDefaults, systemUptime, …) live in source, so
    this source scan is the only place they can be found.
    """
    signals: Dict[str, str] = {}
    remaining = set(_COMPILED_SIGNALS)
    scanned = 0

    # config files first (deps/plugins are the strongest cross-platform signal)
    haystacks: List[Path] = list(proj.config_files)
    for dirpath, filenames in _walk(proj.root):
        if scanned >= _MAX_SRC_FILES:
            break
        for name in filenames:
            if scanned >= _MAX_SRC_FILES:
                break
            if Path(name).suffix.lower() in _SRC_EXTS:
                haystacks.append(dirpath / name)
                scanned += 1

    for path in haystacks:
        if not remaining and "__required_reason__" in signals:
            break
        text = _read_text(path)
        if not text:
            continue
        for concept in list(remaining):
            for rx in _COMPILED_SIGNALS[concept]:
                m = rx.search(text)
                if m:
                    signals[concept] = f"{_rel(proj.root, path)}:{_lineno(text, m.start())}"
                    remaining.discard(concept)
                    break
        if "__required_reason__" not in signals:
            m = _RR_RX.search(text)
            if m:
                signals["__required_reason__"] = (
                    f"{_rel(proj.root, path)}:{_lineno(text, m.start())} ({m.group(0)})"
                )
    return signals


def _gather_ios_config_text(proj: MobileProject) -> str:
    parts = [_read_text(p) for p in proj.ios_surfaces]
    for name in ("app.json", "app.config.js", "app.config.ts"):
        p = next((c for c in proj.config_files if c.name == name), None)
        if p:
            parts.append(_read_text(p))
    return "\n".join(parts)


# --------------------------------------------------------------------------- #
# iOS detectors
# --------------------------------------------------------------------------- #
def _check_ios(proj: MobileProject, signals: Dict[str, str]) -> List[Finding]:
    if not proj.ios_surfaces and "ios" not in proj.stores:
        return []
    out: List[Finding] = []
    ios_text = _gather_ios_config_text(proj)

    # 1. Empty / placeholder purpose strings (deterministic HARD)
    purpose_re = re.compile(
        r"<key>\s*(NS\w*UsageDescription)\s*</key>\s*<string>(.*?)</string>",
        re.DOTALL,
    )
    json_purpose_re = re.compile(r'"(NS\w*UsageDescription)"\s*:\s*"(.*?)"')
    empties: List[str] = []
    for plist in proj.ios_surfaces:
        if plist.suffix != ".plist":
            continue
        text = _read_text(plist)
        for m in purpose_re.finditer(text):
            key, val = m.group(1), (m.group(2) or "").strip()
            if val.lower() in _PLACEHOLDER_PURPOSE or val.lower() == key.lower():
                empties.append(f"{_rel(proj.root, plist)}:{_lineno(text, m.start())} ({key})")
    for m in json_purpose_re.finditer(ios_text):
        key, val = m.group(1), (m.group(2) or "").strip()
        if val.lower() in _PLACEHOLDER_PURPOSE:
            empties.append(f"{key} (empty in Expo/JSON config)")
    if empties:
        out.append(Finding(
            "ios.purpose_empty", "ios",
            "Empty/placeholder Info.plist purpose string", "HARD", "fail",
            "ITMS-90683 / Guideline 5.1.1", evidence="; ".join(empties[:8]),
            fix="Give every *UsageDescription a specific, user-facing reason.",
        ))
    elif any(p.suffix == ".plist" for p in proj.ios_surfaces):
        out.append(Finding(
            "ios.purpose_empty", "ios",
            "Info.plist purpose strings non-empty", "HARD", "pass",
            "ITMS-90683 / Guideline 5.1.1",
        ))

    # 2. Capability used but purpose key missing (heuristic warn).
    # Only meaningful once a real Info.plist exists: Expo/RN/Flutter generate the
    # plist from plugin config at prebuild, so a missing raw key pre-prebuild is
    # not yet a defect (the prebuild note covers that case).
    if any(p.suffix == ".plist" for p in proj.ios_surfaces):
        missing: List[str] = []
        for concept, key in _IOS_PURPOSE_KEYS.items():
            if concept in signals and key not in ios_text:
                missing.append(f"{key} (used at {signals[concept]})")
        if missing:
            out.append(Finding(
                "ios.purpose_missing", "ios",
                "Permission API used without its Info.plist purpose key", "HARD",
                "warn", "ITMS-90683 / Guideline 5.1.1",
                evidence="; ".join(missing[:8]),
                fix="Add the matching *UsageDescription for each capability you use.",
            ))

    # 3. Privacy manifest required-reason APIs (HARD). Required-reason symbols
    # live in source; the signal scan is the only place they surface.
    rr_hit = signals.get("__required_reason__")
    if rr_hit:
        has_xcprivacy = any(p.suffix == ".xcprivacy" for p in proj.ios_surfaces)
        if has_xcprivacy:
            out.append(Finding(
                "ios.privacy_manifest", "ios",
                "PrivacyInfo.xcprivacy present for required-reason APIs", "HARD",
                "pass", "ITMS-91053/91055/91061",
            ))
        else:
            native_exists = any(p.suffix == ".plist" for p in proj.ios_surfaces)
            out.append(Finding(
                "ios.privacy_manifest", "ios",
                "Required-reason API used without PrivacyInfo.xcprivacy", "HARD",
                "warn" if not native_exists else "fail",
                "ITMS-91053/91055/91061", evidence=str(rr_hit),
                fix="Ship PrivacyInfo.xcprivacy with NSPrivacyAccessedAPITypes + a "
                    "valid reason code; bundled named SDKs need their own manifest.",
            ))

    # 4. Encryption export flag (SOFT — build stall)
    if any(p.suffix == ".plist" for p in proj.ios_surfaces) or "infoPlist" in ios_text:
        if "ITSAppUsesNonExemptEncryption" not in ios_text:
            out.append(Finding(
                "ios.encryption", "ios",
                "ITSAppUsesNonExemptEncryption not declared", "SOFT", "warn",
                "Export Compliance",
                fix="Set ITSAppUsesNonExemptEncryption=false for HTTPS-only apps to "
                    "skip the manual upload prompt.",
            ))

    # 5. ATS arbitrary loads (SOFT)
    if re.search(r"NSAllowsArbitraryLoads\s*</key>\s*<true/>", ios_text) or \
       re.search(r'"NSAllowsArbitraryLoads"\s*:\s*true', ios_text):
        scoped = "NSExceptionDomains" in ios_text
        out.append(Finding(
            "ios.ats", "ios",
            "NSAllowsArbitraryLoads=true" + (" (scoped)" if scoped else " (unscoped)"),
            "SOFT", "warn", "App Transport Security",
            fix="Remove arbitrary loads or scope insecure hosts via NSExceptionDomains.",
        ))

    out += _check_shared(proj, signals, "ios")

    # Sign in with Apple (SOFT, iOS-only)
    if "social_login" in signals and "siwa" not in signals:
        out.append(Finding(
            "ios.siwa", "ios",
            "Third-party social login without Sign in with Apple", "SOFT", "warn",
            "Guideline 4.8", evidence=f"social login at {signals['social_login']}",
            fix="Offer Sign in with Apple (or a privacy-equivalent option) alongside "
                "third-party social login.",
        ))

    # SDK floor note (informational; can't be read from source pre-archive)
    out.append(Finding(
        "ios.sdk_floor", "ios", "Build SDK / Xcode floor", "SOFT", "unknown",
        "App Store SDK requirement", evidence=IOS_SDK_FLOOR_NOTE,
        fix="Build with a currently-accepted Xcode/SDK; verify DTSDKName/DTXcode in "
            "the produced build.",
    ))
    return out


# --------------------------------------------------------------------------- #
# Android detectors
# --------------------------------------------------------------------------- #
def _check_android(proj: MobileProject, signals: Dict[str, str]) -> List[Finding]:
    if not proj.android_surfaces and "android" not in proj.stores:
        return []
    out: List[Finding] = []
    manifests = [p for p in proj.android_surfaces if p.name == "AndroidManifest.xml"]
    gradles = [p for p in proj.android_surfaces if p.name.startswith("build.gradle")]

    # 1. android:exported explicit (deterministic HARD)
    missing_exported: List[str] = []
    parsed_any = False
    for m in manifests:
        comps = _android_components_missing_exported(m)
        if comps is not None:
            parsed_any = True
            for comp in comps:
                missing_exported.append(f"{_rel(proj.root, m)}: <{comp[0]} {comp[1]}>")
    if missing_exported:
        out.append(Finding(
            "android.exported", "android",
            "intent-filter component missing android:exported", "HARD", "fail",
            "Android 12 (API 31) behavior change",
            evidence="; ".join(missing_exported[:8]),
            fix="Set android:exported explicitly on every activity/service/receiver "
                "that declares an <intent-filter>.",
        ))
    elif parsed_any:
        out.append(Finding(
            "android.exported", "android",
            "android:exported set on all intent-filter components", "HARD", "pass",
            "Android 12 (API 31) behavior change",
        ))

    # 2. targetSdk floor (deterministic HARD when found)
    target = _android_target_sdk(gradles, manifests)
    if target is None:
        out.append(Finding(
            "android.target_sdk", "android",
            "targetSdk not found in build config", "HARD", "unknown",
            "Play target API level policy",
            fix=f"Set targetSdk >= {ANDROID_TARGET_SDK_FLOOR} in build.gradle.",
        ))
    elif target < ANDROID_TARGET_SDK_FLOOR:
        out.append(Finding(
            "android.target_sdk", "android",
            f"targetSdk {target} below floor {ANDROID_TARGET_SDK_FLOOR}", "HARD",
            "fail", "Play target API level policy",
            evidence=f"targetSdk={target}",
            fix=f"Raise targetSdk to >= {ANDROID_TARGET_SDK_FLOOR} for new/updated apps.",
        ))
    else:
        out.append(Finding(
            "android.target_sdk", "android",
            f"targetSdk {target} meets floor {ANDROID_TARGET_SDK_FLOOR}", "HARD",
            "pass", "Play target API level policy",
        ))

    # 3. Foreground service types (API 34+)
    fgs_issues: List[str] = []
    for m in manifests:
        fgs_issues += _android_fgs_issues(m, proj.root)
    if fgs_issues:
        out.append(Finding(
            "android.fgs_type", "android",
            "Foreground service missing type or matching permission", "HARD", "warn",
            "Android 14 (API 34) foreground service types",
            evidence="; ".join(fgs_issues[:8]),
            fix="Add android:foregroundServiceType + the matching "
                "FOREGROUND_SERVICE_<TYPE> permission, and declare the type in Play "
                "Console.",
        ))

    # 4. Sensitive permissions needing Console declaration
    sens: List[str] = []
    for m in manifests:
        text = _read_text(m)
        for perm in _ANDROID_SENSITIVE_PERMS:
            mo = re.search(re.escape(perm), text)
            if mo:
                sens.append(f"{perm} @ {_rel(proj.root, m)}:{_lineno(text, mo.start())}")
    if sens:
        out.append(Finding(
            "android.sensitive_perms", "android",
            "Sensitive permission requires a Play Console declaration", "SOFT", "warn",
            "Play permissions & sensitive APIs policy",
            evidence="; ".join(sens[:8]),
            fix="Justify each via the Play Console declaration form, or remove/scope "
                "it (e.g. prefer scoped <queries> over QUERY_ALL_PACKAGES).",
        ))

    # 5. 16 KB native page alignment
    if proj.so_files:
        out.append(Finding(
            "android.so_align", "android",
            f"{len(proj.so_files)} native .so present — verify 16 KB alignment",
            "SOFT", "warn", "16 KB page-size requirement (since 2025-11-01)",
            evidence=_rel(proj.root, proj.so_files[0]),
            fix="Build with AGP >= 8.5.1 / NDK r28 so ELF load segments are "
                "16384-aligned (p_align).",
        ))

    out += _check_shared(proj, signals, "android")
    return out


def _android_components_missing_exported(manifest: Path) -> Optional[List[Tuple[str, str]]]:
    root = _safe_xml_root(manifest)
    if root is None:
        return None
    name_attr = f"{{{ANDROID_NS}}}name"
    exported_attr = f"{{{ANDROID_NS}}}exported"
    out: List[Tuple[str, str]] = []
    for tag in ("activity", "service", "receiver"):
        for el in root.iter(tag):
            if el.find("intent-filter") is None:
                continue
            if el.get(exported_attr) is None:
                out.append((tag, el.get(name_attr, "?")))
    return out


def _android_fgs_issues(manifest: Path, root: Path) -> List[str]:
    m_root = _safe_xml_root(manifest)
    if m_root is None:
        return []
    name_attr = f"{{{ANDROID_NS}}}name"
    type_attr = f"{{{ANDROID_NS}}}foregroundServiceType"
    perms = {el.get(name_attr, "") for el in m_root.iter("uses-permission")}
    uses_fgs = any("FOREGROUND_SERVICE" in p for p in perms)
    issues: List[str] = []
    typed_service = False
    # A service is only "foreground" if it declares a type; ordinary bound/
    # background services need no type, so flag a missing permission per typed
    # service, and (once) a declared FGS permission with no typed service.
    for svc in m_root.iter("service"):
        fgs_type = svc.get(type_attr)
        if not fgs_type:
            continue
        typed_service = True
        svc_name = svc.get(name_attr, "?")
        for t in fgs_type.split("|"):
            want = f"android.permission.FOREGROUND_SERVICE_{t.strip().upper()}"
            if want not in perms:
                issues.append(f"{svc_name}: missing {want}")
    if uses_fgs and not typed_service:
        issues.append(
            "FOREGROUND_SERVICE permission declared but no <service> sets "
            "android:foregroundServiceType"
        )
    return issues


def _android_target_sdk(gradles: List[Path], manifests: List[Path]) -> Optional[int]:
    rx = re.compile(r"targetSdk(?:Version)?\s*[=\s(]\s*['\"]?(\d{1,3})\b", re.IGNORECASE)
    for g in gradles:
        m = rx.search(_read_text(g))
        if m:
            return int(m.group(1))
    rx2 = re.compile(r'targetSdkVersion\s*=\s*"(\d{1,3})"')
    for man in manifests:
        m = rx2.search(_read_text(man))
        if m:
            return int(m.group(1))
    return None


# --------------------------------------------------------------------------- #
# Shared (both stores) guideline-level detectors
# --------------------------------------------------------------------------- #
def _check_shared(proj: MobileProject, signals: Dict[str, str], store: str) -> List[Finding]:
    out: List[Finding] = []
    ref = "Guideline 5.1.1(v)" if store == "ios" else "Play account/data deletion policy"

    if "account" in signals and "delete_account" not in signals:
        out.append(Finding(
            f"{store}.account_deletion", store,
            "Account creation found, no in-app account deletion", "SOFT", "warn",
            ref, evidence=f"account flow at {signals['account']}",
            fix="Offer in-app account deletion" + (
                " (Apple 5.1.1(v))." if store == "ios"
                else " plus a Play Console data-deletion URL."),
        ))

    pp_ref = "Guideline 5.1.1(i)" if store == "ios" else "Play User Data / Data safety policy"
    data_concepts = {"location", "contacts", "camera", "photos", "tracking", "account", "ads"}
    if (data_concepts & signals.keys()) and "privacy_policy" not in signals:
        out.append(Finding(
            f"{store}.privacy_policy", store,
            "Collects user data but no privacy policy link found", "SOFT", "warn",
            pp_ref,
            fix="Link a privacy policy in the store listing and in-app; describe data "
                "collected, use, retention, and third-party sharing.",
        ))

    if "payment_sdk" in signals:
        pay_ref = "Guideline 3.1.1 (IAP)" if store == "ios" else "Play Payments policy"
        out.append(Finding(
            f"{store}.payments", store,
            "Third-party payment SDK present — confirm not for digital goods",
            "SOFT", "warn", pay_ref, evidence=f"at {signals['payment_sdk']}",
            fix=("Use StoreKit IAP" if store == "ios" else "Use Google Play Billing")
                + " for digital content/subscriptions; external SDKs are physical "
                  "goods/services only.",
        ))

    if "ads" in signals:
        ad_ref = "Guideline 2.5.18 (Ads)" if store == "ios" else "Play Ads policy"
        out.append(Finding(
            f"{store}.ads", store,
            "Ads SDK present — confirm disclosure & non-disruptive placement",
            "SOFT", "warn", ad_ref, evidence=f"at {signals['ads']}",
            fix="No full-screen/interstitial ads at unexpected moments; clearly mark "
                "ads; honor age rating / Families rules.",
        ))
    return out


# --------------------------------------------------------------------------- #
# Verdict + report
# --------------------------------------------------------------------------- #
def run_checks(proj: MobileProject, platforms: List[str]) -> List[Finding]:
    if not proj.recognized and not proj.config_files:
        return []
    signals = _collect_signals(proj)
    findings: List[Finding] = []
    if "ios" in platforms:
        findings += _check_ios(proj, signals)
    if "android" in platforms:
        findings += _check_android(proj, signals)
    return findings


def verdict(findings: List[Finding]) -> str:
    hard_fail = any(f.severity == "HARD" and f.status == "fail" for f in findings)
    if hard_fail:
        return "LIKELY-REJECT"
    conditions = any(
        f.status in ("fail", "warn")
        or (f.severity == "HARD" and f.status == "unknown")
        for f in findings
    )
    return "GO-WITH-CONDITIONS" if conditions else "GO"


_STATUS_ICON = {"pass": "✅", "fail": "❌", "warn": "⚠️", "unknown": "❓"}
_VERDICT_ICON = {"GO": "🟢", "GO-WITH-CONDITIONS": "🟡", "LIKELY-REJECT": "🔴"}


def render_report(proj: MobileProject, findings: List[Finding], decision: str) -> str:
    lines = ["# App Store Submission Validation", ""]
    fw = ", ".join(proj.frameworks) if proj.frameworks else "none detected"
    lines.append(f"- **Project:** `{proj.root}`")
    lines.append(f"- **Detected framework:** {fw}")
    lines.append(f"- **Stores in scope:** {', '.join(proj.stores) or '(none — showing generic checklist)'}")
    lines.append(f"- **Verdict:** {_VERDICT_ICON.get(decision, '')} **{decision}**")
    lines.append("")

    if proj.notes:
        lines.append("> " + "\n> ".join(proj.notes))
        lines.append("")

    if not findings:
        lines.append(
            "_No mechanical findings (no recognized mobile project at this path, "
            "or native projects not generated yet). Use the manual checklist below._"
        )
        return "\n".join(lines)

    by_store: Dict[str, List[Finding]] = {}
    for f in findings:
        by_store.setdefault(f.store, []).append(f)

    for store in ("ios", "android"):
        store_findings = by_store.get(store)
        if not store_findings:
            continue
        title = "Apple App Store" if store == "ios" else "Google Play"
        lines.append(f"## {title} — automated findings")
        lines.append("")
        lines.append("| | Severity | Check | Evidence | Ref |")
        lines.append("|---|---|---|---|---|")
        for f in store_findings:
            icon = _STATUS_ICON.get(f.status, "•")
            ev = (f.evidence or "").replace("|", "\\|")
            lines.append(f"| {icon} | {f.severity} | {f.title} | {ev} | {f.ref} |")
        lines.append("")
        fixes = [f for f in store_findings if f.status in ("fail", "warn") and f.fix]
        if fixes:
            lines.append("**Fixes:**")
            for f in fixes:
                lines.append(f"- {_STATUS_ICON.get(f.status)} {f.title}: {f.fix}")
            lines.append("")

    legend = ("Legend: ✅ pass · ❌ HARD fail (blocks submission) · ⚠️ likely issue / "
              "confirm · ❓ can't verify statically. " + (
                  "Any ❌ = LIKELY-REJECT." ))
    lines.append(legend)
    lines.append("")
    return "\n".join(lines)
