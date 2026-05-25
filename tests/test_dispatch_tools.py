"""Guards on the teams-mode tool allocation in tools/generate_dispatch.py."""

from tools.generate_dispatch import TEAMS_TOOLS, _TEAMS_IMPLEMENTER

ADVISORY = {"business_analyst", "product_manager", "ui_ux_designer", "team_lead",
            "security_engineer", "code_reviewer"}
WEB_AGENTS = {"security_engineer", "debugging_expert", "cli_installer_developer"}


def test_advisory_agents_cannot_write():
    for name in ADVISORY:
        tools = TEAMS_TOOLS[name]
        assert "Edit" not in tools and "Write" not in tools, name


def test_web_tools_only_on_intended_agents():
    granted = {n for n, t in TEAMS_TOOLS.items() if "WebFetch" in t or "WebSearch" in t}
    assert granted == WEB_AGENTS
    for name in WEB_AGENTS:
        assert {"WebFetch", "WebSearch"} <= set(TEAMS_TOOLS[name]), name


def test_architect_and_delivery_stay_implementers():
    # Deliberate divergence from the 2026-05-18 rec: their deliverable is a
    # committed file (ADR / release runbook), so they keep Edit/Write.
    for name in ("system_architect", "delivery_manager"):
        assert TEAMS_TOOLS[name] == _TEAMS_IMPLEMENTER, name


def test_no_agent_gets_the_spawn_tool():
    for name, tools in TEAMS_TOOLS.items():
        assert "Agent" not in tools, name
