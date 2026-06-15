"""Guards on the mobile_ux_engineer polish agent: registration, wiring, and
that its best-practices actually carry the researched package knowledge."""

import server
from agents.development.mobile_ux_engineer import MobileUXEngineer
from utils.skill_registry import AGENT_SKILL_AFFINITIES


def test_registered_in_agent_classes():
    assert server.AGENT_CLASSES.get("mobile_ux_engineer") is MobileUXEngineer


def test_identity_and_tags():
    agent = MobileUXEngineer({"expertise_level": "principal"})
    assert agent.name == "mobile_ux_engineer"
    assert agent.role == "Mobile UX Engineer"
    assert "patterns" in agent.capability_tags


def test_best_practices_cover_the_five_polish_areas():
    bp = " ".join(MobileUXEngineer({}).best_practices).lower()
    # Real packages the research mapped the codenames to.
    for pkg in ("pressto", "moti", "expo-haptics",
                "react-native-keyboard-controller"):
        assert pkg in bp, pkg
    # Each of the five areas is represented.
    assert "scroll" in bp or "onfinalize" in bp          # press cancel-on-scroll
    assert "fade" in bp                                   # subtle animations
    assert "haptic" in bp                                 # tactile haptics
    assert "keyboard" in bp                               # keyboard behavior
    assert "skeleton" in bp or "empty" in bp              # empty states
    assert "permission" in bp                             # permission priming


def test_cross_platform_parity_present():
    bp = " ".join(MobileUXEngineer({}).best_practices).lower()
    assert "flutter" in bp and "swiftui" in bp and "compose" in bp


def test_skill_affinity_includes_app_store_check():
    assert "mobile_ux_engineer" in AGENT_SKILL_AFFINITIES
    assert "app_store_check" in AGENT_SKILL_AFFINITIES["mobile_ux_engineer"]


def test_existing_mobile_agents_reference_the_specialist():
    from agents.development.react_native_developer import ReactNativeDeveloper
    from agents.development.flutter_developer import FlutterDeveloper
    from agents.development.ios_developer import IOSDeveloper
    from agents.development.android_developer import AndroidDeveloper
    from agents.development.mobile_developer import MobileDeveloper

    for cls in (ReactNativeDeveloper, FlutterDeveloper, IOSDeveloper,
                AndroidDeveloper, MobileDeveloper):
        bp = " ".join(cls({}).best_practices)
        assert "mobile_ux_engineer" in bp, cls.__name__
