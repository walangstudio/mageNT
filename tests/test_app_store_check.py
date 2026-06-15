"""Tests for the cross-platform app_store_check skill + its _mobile backend.

Detection runs over real temp project trees; the deterministic detectors
(empty purpose string, missing android:exported, target SDK below floor) must
drive a LIKELY-REJECT verdict, while heuristic checks stay non-fatal.
"""

from pathlib import Path

from skills import get_skill
from skills.quality._mobile import (
    Finding, detect_mobile_project, render_report, run_checks, verdict,
)


def _write(path: Path, content: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


_MANIFEST_HEAD = (
    '<manifest xmlns:android="http://schemas.android.com/apk/res/android" '
    'package="com.example.app">'
)


# --------------------------------------------------------------------------- #
# Framework detection
# --------------------------------------------------------------------------- #
def test_detect_expo(tmp_path):
    _write(tmp_path / "app.json", '{"expo": {"name": "x"}}')
    _write(tmp_path / "package.json",
           '{"dependencies": {"expo": "^50", "react-native": "0.73"}}')
    proj = detect_mobile_project(tmp_path)
    assert "expo" in proj.frameworks
    assert set(proj.stores) == {"ios", "android"}


def test_detect_bare_react_native_not_expo(tmp_path):
    _write(tmp_path / "package.json", '{"dependencies": {"react-native": "0.73"}}')
    _write(tmp_path / "ios" / "App" / "Info.plist", "<plist></plist>")
    proj = detect_mobile_project(tmp_path)
    assert "react_native" in proj.frameworks
    assert "expo" not in proj.frameworks


def test_detect_flutter(tmp_path):
    _write(tmp_path / "pubspec.yaml", "name: x\nflutter:\n  sdk: flutter\n")
    proj = detect_mobile_project(tmp_path)
    assert "flutter" in proj.frameworks
    assert set(proj.stores) == {"ios", "android"}


def test_detect_tauri_mobile(tmp_path):
    _write(tmp_path / "src-tauri" / "tauri.conf.json", "{}")
    _write(tmp_path / "src-tauri" / "gen" / "android" / "app" / "src" / "main"
           / "AndroidManifest.xml", _MANIFEST_HEAD + "</manifest>")
    proj = detect_mobile_project(tmp_path)
    assert "tauri" in proj.frameworks
    assert "android" in proj.stores


def test_detect_native_ios(tmp_path):
    _write(tmp_path / "MyApp.xcodeproj" / "project.pbxproj", "// pbx")
    _write(tmp_path / "MyApp" / "Info.plist", "<plist></plist>")
    proj = detect_mobile_project(tmp_path)
    assert "native_ios" in proj.frameworks
    assert proj.stores == ["ios"]


def test_detect_capacitor(tmp_path):
    _write(tmp_path / "capacitor.config.json", "{}")
    _write(tmp_path / "package.json", '{"dependencies": {"@capacitor/core": "5"}}')
    proj = detect_mobile_project(tmp_path)
    assert "capacitor" in proj.frameworks


# --------------------------------------------------------------------------- #
# Deterministic detectors -> LIKELY-REJECT
# --------------------------------------------------------------------------- #
def test_android_missing_exported_is_hard_fail(tmp_path):
    manifest = _MANIFEST_HEAD + """
  <application>
    <activity android:name=".MainActivity">
      <intent-filter>
        <action android:name="android.intent.action.MAIN"/>
        <category android:name="android.intent.category.LAUNCHER"/>
      </intent-filter>
    </activity>
  </application>
</manifest>"""
    _write(tmp_path / "android" / "app" / "src" / "main" / "AndroidManifest.xml", manifest)
    _write(tmp_path / "android" / "app" / "build.gradle",
           "android { defaultConfig { targetSdk 35 } }")
    _write(tmp_path / "package.json", '{"dependencies": {"react-native": "0.73"}}')
    proj = detect_mobile_project(tmp_path)
    findings = run_checks(proj, ["android"])
    exported = [f for f in findings if f.id == "android.exported"]
    assert exported and exported[0].status == "fail"
    assert verdict(findings) == "LIKELY-REJECT"


def test_android_target_sdk_below_floor_is_hard_fail(tmp_path):
    _write(tmp_path / "android" / "app" / "src" / "main" / "AndroidManifest.xml",
           _MANIFEST_HEAD + "</manifest>")
    _write(tmp_path / "android" / "app" / "build.gradle",
           "android { defaultConfig { targetSdk 33 } }")
    _write(tmp_path / "package.json", '{"dependencies": {"react-native": "0.73"}}')
    proj = detect_mobile_project(tmp_path)
    findings = run_checks(proj, ["android"])
    target = [f for f in findings if f.id == "android.target_sdk"][0]
    assert target.status == "fail"
    assert verdict(findings) == "LIKELY-REJECT"


def test_ios_empty_purpose_string_is_hard_fail(tmp_path):
    plist = ('<?xml version="1.0"?><plist><dict>'
             '<key>NSCameraUsageDescription</key><string></string>'
             '</dict></plist>')
    _write(tmp_path / "ios" / "App" / "Info.plist", plist)
    _write(tmp_path / "MyApp.xcodeproj" / "project.pbxproj", "// pbx")
    proj = detect_mobile_project(tmp_path)
    findings = run_checks(proj, ["ios"])
    pe = [f for f in findings if f.id == "ios.purpose_empty"][0]
    assert pe.status == "fail"
    assert verdict(findings) == "LIKELY-REJECT"


def test_ios_clean_native_has_no_failures(tmp_path):
    plist = ('<?xml version="1.0"?><plist><dict>'
             '<key>NSCameraUsageDescription</key>'
             '<string>Scan receipts with the camera.</string>'
             '<key>ITSAppUsesNonExemptEncryption</key><false/>'
             '</dict></plist>')
    _write(tmp_path / "ios" / "App" / "Info.plist", plist)
    _write(tmp_path / "MyApp.xcodeproj" / "project.pbxproj", "// pbx")
    proj = detect_mobile_project(tmp_path)
    findings = run_checks(proj, ["ios"])
    assert not any(f.status == "fail" for f in findings)
    assert verdict(findings) in ("GO", "GO-WITH-CONDITIONS")


def test_ios_required_reason_without_manifest_is_flagged(tmp_path):
    _write(tmp_path / "ios" / "App" / "Info.plist",
           '<?xml version="1.0"?><plist><dict>'
           '<key>ITSAppUsesNonExemptEncryption</key><false/></dict></plist>')
    _write(tmp_path / "MyApp.xcodeproj" / "project.pbxproj", "// pbx")
    _write(tmp_path / "ios" / "App" / "Store.swift",
           "import Foundation\nlet d = UserDefaults.standard\n")
    proj = detect_mobile_project(tmp_path)
    findings = run_checks(proj, ["ios"])
    pm = [f for f in findings if f.id == "ios.privacy_manifest"]
    assert pm and pm[0].status in ("fail", "warn")


def test_ios_required_reason_with_xcprivacy_passes(tmp_path):
    _write(tmp_path / "ios" / "App" / "Info.plist",
           '<?xml version="1.0"?><plist><dict></dict></plist>')
    _write(tmp_path / "ios" / "App" / "PrivacyInfo.xcprivacy", "<plist></plist>")
    _write(tmp_path / "MyApp.xcodeproj" / "project.pbxproj", "// pbx")
    _write(tmp_path / "ios" / "App" / "Store.swift", "let d = UserDefaults.standard\n")
    proj = detect_mobile_project(tmp_path)
    findings = run_checks(proj, ["ios"])
    pm = [f for f in findings if f.id == "ios.privacy_manifest"][0]
    assert pm.status == "pass"


def test_android_fgs_typed_service_missing_permission(tmp_path):
    manifest = _MANIFEST_HEAD + """
  <uses-permission android:name="android.permission.FOREGROUND_SERVICE"/>
  <application>
    <service android:name=".SyncService" android:foregroundServiceType="dataSync"/>
  </application>
</manifest>"""
    _write(tmp_path / "android" / "app" / "src" / "main" / "AndroidManifest.xml", manifest)
    _write(tmp_path / "android" / "app" / "build.gradle",
           "android { defaultConfig { targetSdk 35 } }")
    _write(tmp_path / "package.json", '{"dependencies": {"react-native": "0.73"}}')
    proj = detect_mobile_project(tmp_path)
    findings = run_checks(proj, ["android"])
    fgs = [f for f in findings if f.id == "android.fgs_type"]
    assert fgs and "FOREGROUND_SERVICE_DATASYNC" in fgs[0].evidence


def test_android_bound_service_not_flagged_as_foreground(tmp_path):
    manifest = _MANIFEST_HEAD + """
  <application>
    <service android:name=".PlainService" android:exported="false"/>
  </application>
</manifest>"""
    _write(tmp_path / "android" / "app" / "src" / "main" / "AndroidManifest.xml", manifest)
    _write(tmp_path / "android" / "app" / "build.gradle",
           "android { defaultConfig { targetSdk 35 } }")
    _write(tmp_path / "package.json", '{"dependencies": {"react-native": "0.73"}}')
    proj = detect_mobile_project(tmp_path)
    findings = run_checks(proj, ["android"])
    assert not [f for f in findings if f.id == "android.fgs_type"]


# --------------------------------------------------------------------------- #
# Verdict logic
# --------------------------------------------------------------------------- #
def test_verdict_levels():
    assert verdict([]) == "GO"
    assert verdict([Finding("a", "ios", "t", "HARD", "pass", "r")]) == "GO"
    assert verdict([Finding("a", "ios", "t", "SOFT", "unknown", "r")]) == "GO"
    assert verdict([Finding("a", "ios", "t", "SOFT", "warn", "r")]) == "GO-WITH-CONDITIONS"
    assert verdict([Finding("a", "ios", "t", "HARD", "unknown", "r")]) == "GO-WITH-CONDITIONS"
    assert verdict([Finding("a", "ios", "t", "HARD", "fail", "r")]) == "LIKELY-REJECT"


# --------------------------------------------------------------------------- #
# Report + skill surface
# --------------------------------------------------------------------------- #
def test_render_report_has_verdict_and_framework(tmp_path):
    _write(tmp_path / "pubspec.yaml", "name: x\nflutter:\n  sdk: flutter\n")
    proj = detect_mobile_project(tmp_path)
    findings = run_checks(proj, ["ios", "android"])
    report = render_report(proj, findings, verdict(findings))
    assert "Verdict" in report
    assert "flutter" in report


def test_skill_execute_reports_verdict_and_framework(tmp_path):
    _write(tmp_path / "pubspec.yaml", "name: x\nflutter:\n  sdk: flutter\n")
    out = get_skill("app_store_check").execute(project_path=str(tmp_path))
    assert out["context"]["verdict"] in ("GO", "GO-WITH-CONDITIONS", "LIKELY-REJECT")
    assert "flutter" in out["context"]["framework"]
    assert "Manual checklist" in out["guidance"]


def test_skill_platform_filtering(tmp_path):
    skill = get_skill("app_store_check")
    ios = skill.execute(platform="ios", project_path=str(tmp_path))["guidance"]
    assert "Info.plist" in ios and "targetSdkVersion" not in ios
    android = skill.execute(platform="android", project_path=str(tmp_path))["guidance"]
    assert "targetSdkVersion" in android and "Info.plist" not in android


def test_skill_likely_reject_sets_success_false(tmp_path):
    _write(tmp_path / "android" / "app" / "src" / "main" / "AndroidManifest.xml",
           _MANIFEST_HEAD + "</manifest>")
    _write(tmp_path / "android" / "app" / "build.gradle",
           "android { defaultConfig { targetSdk 30 } }")
    _write(tmp_path / "package.json", '{"dependencies": {"react-native": "0.73"}}')
    out = get_skill("app_store_check").execute(
        platform="android", project_path=str(tmp_path))
    assert out["context"]["verdict"] == "LIKELY-REJECT"
    assert out["success"] is False
