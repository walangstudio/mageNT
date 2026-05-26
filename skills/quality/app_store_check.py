"""App store submission validation skill.

Static-analysis checklist that flags Apple App Store and Google Play rejection
rules before submission, so a build doesn't bounce on review. Guidance-only:
emits the detectors (file + pattern + what to flag) for the host to run via
Grep/Read; it does not mutate files.

Sources (verify against canonical pages at use time — Apple's reason-code page
is JS-rendered and reason codes are corroborated via secondary sources):
- Apple App Store Review Guidelines (5.1.1 privacy / account deletion, 4.8 SIWA)
- developer.apple.com: Info.plist usage keys, required-reason API + privacy
  manifest docs, upcoming SDK minimum requirements, encryption export compliance
- Google Play: target API level requirement; Android 12 exported / Android 14
  foreground-service-type behavior changes; sensitive-permission policy pages;
  16 KB page-size guide
"""

from typing import Any, Dict, List

try:
    from skills.base import BaseSkill
except ImportError:
    from ..base import BaseSkill


_IOS_GUIDANCE = """## Apple App Store — static rejection checks

Input surfaces: `*.swift` / `*.m` / `*.mm`, `Info.plist`, `*.xcprivacy`,
`*.xcodeproj` / `project.pbxproj`, linked `.framework` / `.a`.

### HARD (automated / guaranteed rejection)

**1. Info.plist purpose strings (ITMS-90683).** A privacy-guarded API linked
without its `*UsageDescription` key (or with an empty/placeholder value) is an
automatic upload reject. Grep source for each symbol; assert the key exists in
`Info.plist`, is non-empty, and is not literally the key name.

| Symbol / usage | Required Info.plist key |
|---|---|
| `AVCaptureDevice`, camera `UIImagePickerController` | `NSCameraUsageDescription` |
| `AVAudioSession` record, audio capture | `NSMicrophoneUsageDescription` |
| `CLLocationManager` whenInUse | `NSLocationWhenInUseUsageDescription` |
| `requestAlwaysAuthorization` / background loc | `NSLocationAlwaysAndWhenInUseUsageDescription` (+ WhenInUse) |
| `PHPhotoLibrary`, `PHPickerViewController` | `NSPhotoLibraryUsageDescription` / `NSPhotoLibraryAddUsageDescription` |
| `CNContactStore` | `NSContactsUsageDescription` |
| `EKEventStore` | `NSCalendarsUsageDescription` (iOS 17+: `NSCalendarsFullAccessUsageDescription`) |
| `CMMotionManager`, `CMPedometer` | `NSMotionUsageDescription` |
| `CBCentralManager` | `NSBluetoothAlwaysUsageDescription` |
| `LAContext` (Face ID) | `NSFaceIDUsageDescription` |
| `SFSpeechRecognizer` | `NSSpeechRecognitionUsageDescription` |
| `ATTrackingManager.requestTrackingAuthorization` | `NSUserTrackingUsageDescription` |
| `HKHealthStore` | `NSHealthShareUsageDescription` / `NSHealthUpdateUsageDescription` |
| Bonjour / `NWBrowser` local network | `NSLocalNetworkUsageDescription` |

**2. Privacy manifest required-reason APIs (ITMS-91053/91055/91061).** If any
trigger symbol appears in first-party source, require a matching
`NSPrivacyAccessedAPITypes` category in `PrivacyInfo.xcprivacy` with at least one
valid reason code. Bundled SDKs on Apple's named list must each carry their own
`.xcprivacy`. If `NSPrivacyTracking` is true, `NSPrivacyTrackingDomains` must be
non-empty.

| Category | Trigger symbols | Example valid reason codes |
|---|---|---|
| `...FileTimestamp` | `stat`, `fstat`, `.modificationDate`, `getattrlist` | `DDA9.1`, `C617.1`, `3B52.1`, `0A2A.1` |
| `...SystemBootTime` | `systemUptime`, `mach_absolute_time`, `KERN_BOOTTIME` | `35F9.1`, `8FFB.1` |
| `...DiskSpace` | `statfs`, `statvfs`, `volumeAvailableCapacity` | `85F4.1`, `E174.1`, `7D9E.1`, `B728.1` |
| `...ActiveKeyboard` | `activeInputModes` | `3EC4.1`, `54BD.1` |
| `...UserDefaults` | `UserDefaults`, `NSUserDefaults` | `CA92.1`, `1C8F.1`, `C56D.1`, `AC6B.1` |

**3. SDK / Xcode floor (date-gated).** Parse `DTSDKName` / `DTXcode`; flag below
the active floor (iOS 18 SDK / Xcode 16 now; iOS 26 SDK from 2026-04-28).

### SOFT (reviewer discretion / build stall — flag with evidence)

- `ITSAppUsesNonExemptEncryption` absent → build stalls on the manual prompt.
  Set `false` for HTTPS-only apps. If a non-exempt crypto lib (OpenSSL,
  libsodium, custom cipher) is linked and the key is `false`, flag as likely
  misdeclared.
- `NSAllowsArbitraryLoads = true` under `NSAppTransportSecurity` → justify or
  scope via `NSExceptionDomains`.
- Account deletion (Guideline 5.1.1(v)): if source has signup/account-creation
  flows but no delete-account route/string/API call, flag for manual confirm.
- Sign in with Apple (Guideline 4.8): if a social-login SDK (`GoogleSignIn`,
  `FBSDKLoginKit`) is linked and `ASAuthorizationAppleIDProvider` is absent,
  flag (exemptions exist).
- Private-API usage (ITMS-90338): scan for underscore-prefixed Apple SDK
  selectors; evidence-only, high false-positive risk.
"""

_ANDROID_GUIDANCE = """## Google Play — static rejection checks

Input surfaces: `AndroidManifest.xml`, `build.gradle(.kts)`, `jniLibs/` + `.so`
(ELF `p_align`), dependency graph.

### HARD

**1. `android:exported` explicit (API 31+).** Every `<activity>` /`<service>` /
`<receiver>` with a child `<intent-filter>` must set `android:exported`
explicitly, or the build/install fails. Parse the manifest; flag any such
component missing it.

**2. targetSdkVersion floor.** Parse `targetSdk` from `build.gradle(.kts)`
(preferred) or manifest. Flag `< 35` for new submissions/updates (required
since 2025-08-31); `< 34` is hard-unavailable to new users.

**3. Foreground service types (API 34+).** For each foreground `<service>`,
require `android:foregroundServiceType`; for each declared type, require the
matching `FOREGROUND_SERVICE_<TYPE>` `uses-permission` plus base
`FOREGROUND_SERVICE`. The type must also be declared in Play Console.

**4. Sensitive permissions needing a Console declaration** (manifest presence
without an approved declaration → removal). Flag each:
`ACCESS_BACKGROUND_LOCATION`, `QUERY_ALL_PACKAGES` (prefer scoped `<queries>`),
`MANAGE_EXTERNAL_STORAGE`, `SEND_SMS`/`READ_SMS`/`READ_CALL_LOG`/etc. (default
SMS/Phone handlers only), `com.google.android.gms.permission.AD_ID`.

**5. 16 KB native page alignment (since 2025-11-01).** If the project ships
native `.so` (`jniLibs/`, `externalNativeBuild`, NDK), require AGP >= 8.5.1 and
16384-aligned ELF load segments (`p_align`). Pure Kotlin/Java is auto-compliant.

### SOFT

- AAB + Play App Signing: flag APK-only release packaging (won't pass upload).
- Privacy policy URL: if any sensitive permission / data-collecting SDK is
  present, require a policy URL somewhere in the project; Console field can't be
  checked statically.
- Data safety alignment: map data-collecting permissions/SDKs (location,
  contacts, camera, AD_ID/ads) to expected Data safety categories and emit a
  "verify these are declared in Console" checklist.
"""


class AppStoreCheck(BaseSkill):
    """Validate a mobile project against Apple/Google submission requirements."""

    @property
    def name(self) -> str:
        return "app_store_check"

    @property
    def slash_command(self) -> str:
        return "/app-store-check"

    @property
    def description(self) -> str:
        return (
            "Static-analysis checklist that flags Apple App Store and Google "
            "Play rejection rules before submission"
        )

    @property
    def category(self) -> str:
        return "quality"

    @property
    def allowed_tools(self) -> List[str]:
        return ["Read", "Grep", "Glob", "Bash"]

    @property
    def when_to_activate(self) -> List[str]:
        return [
            "Before submitting an iOS or Android build to the App Store / Play",
            "Adding a permission-guarded API (camera, location, contacts, tracking)",
            "Bumping target SDK, adding a foreground service, or shipping native libs",
            "Auditing an Expo/React Native/Flutter app's produced native projects",
        ]

    @property
    def parameters(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "platform",
                "type": "string",
                "description": "ios | android | both (default both)",
                "required": False,
            },
            {
                "name": "project_path",
                "type": "string",
                "description": "Path to the mobile project root to scan",
                "required": False,
            },
        ]

    @property
    def workflow(self) -> List[str]:
        return [
            "Locate the platform manifests (Info.plist / *.xcprivacy / project.pbxproj; AndroidManifest.xml / build.gradle).",
            "Run each detector below with Grep/Read against source and config.",
            "Report findings grouped HARD vs SOFT, each with file:line evidence.",
            "For Expo/RN/Flutter, scan the produced native dirs (ios/, android/) after prebuild, not just app.json.",
        ]

    def execute(self, **kwargs) -> Dict[str, Any]:
        platform = str(kwargs.get("platform", "both") or "both").lower()
        if platform not in ("ios", "android", "both"):
            platform = "both"
        project_path = kwargs.get("project_path", "")

        sections = ["# App Store Submission Validation"]
        if project_path:
            sections.append(f"\nProject: `{project_path}`")
        sections.append(
            "\nRun the detectors below. HARD = automated/guaranteed rejection; "
            "fix before submitting. SOFT = reviewer discretion or upload stall; "
            "flag with evidence. Cite `file:line` for every finding."
        )

        if platform in ("ios", "both"):
            sections.append("\n" + _IOS_GUIDANCE)
        if platform in ("android", "both"):
            sections.append("\n" + _ANDROID_GUIDANCE)

        sections.append(
            "\n## Output\n"
            "For each finding: `[HARD|SOFT] <rule> — <file:line> — <fix>`. "
            "End with a go/no-go: any unresolved HARD finding = NO-GO."
        )

        guidance = "\n".join(sections)
        return {
            "guidance": guidance,
            "context": {
                "platform": platform,
                "project_path": project_path,
            },
            "success": True,
        }
