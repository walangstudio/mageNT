"""Guards on the framework specialist agents: expo_developer, tauri_developer,
and the deepened flutter_developer. Registration + that the best-practices carry
the researched, framework-specific knowledge."""

import server
from agents.development.expo_developer import ExpoDeveloper
from agents.development.tauri_developer import TauriDeveloper
from agents.development.flutter_developer import FlutterDeveloper
from utils.skill_registry import AGENT_SKILL_AFFINITIES


def _bp(cls):
    return " ".join(cls({}).best_practices).lower()


def test_expo_and_tauri_registered():
    assert server.AGENT_CLASSES.get("expo_developer") is ExpoDeveloper
    assert server.AGENT_CLASSES.get("tauri_developer") is TauriDeveloper


def test_expo_identity_and_knowledge():
    agent = ExpoDeveloper({})
    assert agent.name == "expo_developer"
    assert agent.role == "Expo Developer"
    bp = _bp(ExpoDeveloper)
    for token in ("expo router", "eas", "config plugin", "expo install",
                  "runtime version", "expo modules api"):
        assert token in bp, token


def test_tauri_identity_and_knowledge():
    agent = TauriDeveloper({})
    assert agent.name == "tauri_developer"
    assert agent.role == "Tauri Developer"
    bp = _bp(TauriDeveloper)
    for token in ("tauri::command", "capabilit", "permission", "updater",
                  "wkwebview", "ios init"):
        assert token in bp, token


def test_flutter_deepened_with_modern_practices():
    bp = _bp(FlutterDeveloper)
    for token in ("riverpod_generator", "pigeon", "shorebird", "impeller",
                  "--wasm", "patrol"):
        assert token in bp, token


def test_framework_agents_have_app_store_affinity():
    for name in ("expo_developer", "tauri_developer"):
        assert name in AGENT_SKILL_AFFINITIES
        assert "app_store_check" in AGENT_SKILL_AFFINITIES[name]
