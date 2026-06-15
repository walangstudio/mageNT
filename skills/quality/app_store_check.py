"""App store submission validation skill.

Detects the mobile framework (native iOS/Android, Expo, React Native, Flutter,
Tauri, Capacitor/Cordova), runs static detectors for the mechanically-checkable
Apple App Store and Google Play rejection rules (file:line evidence), emits an
accept/reject verdict (GO / GO-WITH-CONDITIONS / LIKELY-REJECT), then appends a
reviewer-judgment checklist covering the full Apple guidelines (5 sections) and
Google Play policy categories. The static scan lives in ``_mobile.py``; this
file owns the manual checklists and the skill surface.

Run it inside a mobile project root (``project_path`` defaults to the current
directory); ``platform`` auto-derives from the detected framework.

Sources (verify against canonical pages at use time — Apple's reason-code page
is JS-rendered):
- Apple App Store Review Guidelines (developer.apple.com/app-store/review/guidelines)
- developer.apple.com: Info.plist usage keys, required-reason API + privacy
  manifest docs, SDK minimums, encryption export compliance
- Google Play Developer Program Policies / policy center: target API level,
  Android 12 exported / Android 14 foreground-service-type changes, sensitive
  permissions, Data safety, account/data deletion, Play Billing, 16 KB pages
"""

from pathlib import Path
from typing import Any, Dict, List

try:
    from skills.base import BaseSkill
    from skills.quality._mobile import (
        detect_mobile_project, run_checks, verdict, render_report,
    )
except ImportError:  # package-relative fallback
    from ..base import BaseSkill
    from ._mobile import (
        detect_mobile_project, run_checks, verdict, render_report,
    )


_IOS_GUIDANCE = """## Apple App Store Review Guidelines — pre-submission checklist

Surfaces: `Info.plist`, `*.xcprivacy`, `project.pbxproj`, `*.swift`/`*.m`, and
App Store Connect metadata. The automated findings above cover the mechanical
rules; the items below are reviewer-judgment calls — confirm each before you
submit (check `file:line` evidence where relevant).

### 1. Safety
- [ ] 1.1 No objectionable/defamatory/violent/sexual content.
- [ ] 1.2 User-generated content has filtering, in-app reporting, user blocking, and a published contact.
- [ ] 1.4 Health/medical claims are substantiated; no encouragement of physical harm.
- [ ] 1.5 An easy way to contact the developer exists in the app or metadata.

### 2. Performance
- [ ] 2.1 App is complete: no crashes on a real device, no broken links, no placeholder text/content.
- [ ] 2.1 A working demo account (or demo mode) is in Review Notes when login is required; the backend is live during review.
- [ ] 2.3 Metadata accurate: screenshots show the app in use (not just splash/login); description matches behavior.
- [ ] 2.3.2 In-app purchases are disclosed in the description/screenshots.
- [ ] 2.5.1 Only public APIs; runs on a current iOS; no deprecated/private API.

### 3. Business
- [ ] 3.1.1 Digital goods/subscriptions sell through StoreKit in-app purchase only — not a custom payment SDK.
- [ ] 3.1.1(a) Any external-purchase link uses the correct entitlement for its storefront.
- [ ] 3.1.2 Subscriptions deliver ongoing value, are ≥ 7-day, and state terms clearly before purchase.

### 4. Design
- [ ] 4.2 Minimum functionality: app-like, useful/unique — not a repackaged website or link collection.
- [ ] 4.3 Not a spam/copycat duplicate of an existing app.
- [ ] 4.8 If third-party/social login is the primary sign-in, offer a privacy-equivalent option (Sign in with Apple or equivalent: name/email-only, hide-my-email, no ad tracking without consent).

### 5. Legal
- [ ] 5.1.1(i) Privacy policy linked in metadata AND in-app; names data collected, use, retention, and third-party sharing.
- [ ] 5.1.1(ii) Each permission purpose string clearly describes the use; consent is withdrawable.
- [ ] 5.1.1(v) If the app has accounts, in-app account deletion is available.
- [ ] 5.1.2 App Tracking Transparency prompt precedes any cross-app/website tracking.
- [ ] 5.1.5 Location is used only when relevant, with consent.
- [ ] 5.2 All content/IP is owned or properly licensed.
"""

_ANDROID_GUIDANCE = """## Google Play Developer Program Policies — pre-submission checklist

Surfaces: `AndroidManifest.xml`, `build.gradle(.kts)`, and the Play Console
(Data safety, declarations, app content). The automated findings above cover the
mechanical rules; confirm the judgment calls below.

### Privacy, Deception & Device Abuse / User Data
- [ ] Privacy policy linked in the store listing AND in-app.
- [ ] Data safety form matches what the app (and its SDKs) actually collects/shares.
- [ ] Sensitive permissions (background location, `QUERY_ALL_PACKAGES`, all-files-access, SMS/Call Log) are justified via the Console declaration, or removed/scoped.
- [ ] Account deletion: an in-app route AND a web data-deletion URL in the Console.
- [ ] targetSdkVersion meets the current Play floor; foreground services declare a type.

### Monetization & Ads
- [ ] Digital goods/subscriptions use Google Play Billing (physical goods/services excepted).
- [ ] Ads are non-disruptive: no unexpected full-screen interstitials, ads are clearly labeled, and they respect the content rating / Families rules.

### Store Listing & Promotion
- [ ] Title/description/screenshots are accurate — no misleading claims or keyword stuffing.

### Spam, Functionality & UX
- [ ] App is fully functional with no crashes/broken flows; not a thin web wrapper or copycat.

### Families (if the app targets children)
- [ ] Designed for Families compliant: no disallowed ads/SDKs, correct content rating, parental controls.

### Intellectual Property / Impersonation
- [ ] No unauthorized brands/IP; the app does not impersonate another app or developer.
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
            "Auto-detect a mobile project (native, Expo, React Native, Flutter, "
            "Tauri), scan it for Apple App Store / Google Play rejection rules, "
            "and report a checklist + accept/reject verdict"
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
            "While inside a mobile project — run it to see the pass/fail checklist + verdict",
            "Adding a permission-guarded API (camera, location, contacts, tracking)",
            "Bumping target SDK, adding a foreground service, or shipping native libs",
            "Auditing an Expo/React Native/Flutter/Tauri app before release",
        ]

    @property
    def parameters(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "project_path",
                "type": "string",
                "description": "Mobile project root to scan (default: current directory)",
                "required": False,
            },
            {
                "name": "platform",
                "type": "string",
                "description": "ios | android | both | auto (default auto — derived from the detected framework)",
                "required": False,
            },
        ]

    @property
    def workflow(self) -> List[str]:
        return [
            "Run against the project root (pass project_path = the current directory).",
            "Read the detected framework + automated findings table; fix every ❌ HARD finding.",
            "Resolve the verdict: any ❌ = LIKELY-REJECT; ⚠️/❓ = GO-WITH-CONDITIONS.",
            "Walk the manual checklist for reviewer-judgment items (Apple 5 sections / Play policies).",
            "For Expo/RN/Flutter/Tauri, generate native projects (prebuild/build) first so Info.plist & privacy-manifest checks have something to read.",
        ]

    def execute(self, **kwargs) -> Dict[str, Any]:
        raw_platform = str(kwargs.get("platform") or "auto").lower()
        if raw_platform not in ("ios", "android", "both", "auto"):
            raw_platform = "auto"
        project_path = str(kwargs.get("project_path") or ".")
        root = Path(project_path).resolve()

        project = detect_mobile_project(root)

        if raw_platform == "auto":
            platforms = list(project.stores) or ["ios", "android"]
        elif raw_platform == "both":
            platforms = ["ios", "android"]
        else:
            platforms = [raw_platform]

        findings = run_checks(project, platforms)
        decision = verdict(findings)
        report = render_report(project, findings, decision)

        sections = [report, "---", "## Manual checklist (reviewer-judgment items)", ""]
        if "ios" in platforms:
            sections.append(_IOS_GUIDANCE)
        if "android" in platforms:
            sections.append(_ANDROID_GUIDANCE)

        guidance = "\n".join(sections)
        return {
            "guidance": guidance,
            "context": {
                "platform": raw_platform,
                "platforms": platforms,
                "project_path": str(root),
                "framework": project.frameworks,
                "verdict": decision,
                "findings": [f.__dict__ for f in findings],
            },
            "success": decision != "LIKELY-REJECT",
        }
