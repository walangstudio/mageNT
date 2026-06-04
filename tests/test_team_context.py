"""Guards on the team-protocol gate and the app_store_check skill.

The Wave-7 review found GA Agent-tool teammates opting out of the report/
shutdown protocol because the old gate keyed on the deprecated
CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS env var and exempted "one-shot subagents".
These tests pin the capability-based rewrite so it can't regress.
"""

from tools.generate_dispatch import (
    PROTOCOL_BANNER,
    TEAM_CONTEXT_BLOCK,
    render_subagent,
)


def test_gate_is_not_env_var_based():
    # The stale gate keyed the whole protocol on an env var the agent cannot
    # read, and exempted any "one-shot subagent" — which a GA background/worktree
    # spawn reads itself as. Both must be gone.
    assert "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1)" not in TEAM_CONTEXT_BLOCK
    assert "a one-shot subagent, or by borch" not in TEAM_CONTEXT_BLOCK


def test_gate_is_capability_based():
    block = TEAM_CONTEXT_BLOCK
    assert "you can `SendMessage`" in block or "SendMessage` available" in block
    # Must explicitly cover the GA TeamCreate + Agent path incl. background/worktree.
    assert "TeamCreate" in block and "run_in_background" in block
    assert "worktree" in block


def test_completion_report_rule_present():
    block = TEAM_CONTEXT_BLOCK
    assert "REPORT ON COMPLETION" in block
    # A clean commit without a report must be called out as not-delivered.
    assert "commit with no report" in block.lower() or "unreported commit" in block.lower()


def test_shutdown_handshake_still_present():
    # The fix unblocks the existing handshake; it must remain intact.
    assert "shutdown_response" in TEAM_CONTEXT_BLOCK
    assert "plan_approval_response" in TEAM_CONTEXT_BLOCK
    assert "request_id" in TEAM_CONTEXT_BLOCK


def test_shutdown_directive_leads_block():
    # Field regression (2026-06-04): a 0.7.5 teammate received a shutdown_request
    # and idled instead of acking. Root cause was salience — the block opened
    # with the teammate-detection + one-shot/JSON-only hedge, burying the action.
    # Pin action-first ordering: the binding shutdown directive must come BEFORE
    # the one-shot exemption hedge, so it can't regress back to hedge-first.
    block = TEAM_CONTEXT_BLOCK
    assert block.lstrip().startswith("## Team Context")
    lead = block.index("STOP — READ THIS FIRST")
    hedge = block.index("The ONLY exemption is a true one-shot")
    assert lead < hedge, "shutdown directive must lead the hedge"
    # The exact response object must appear in the leading directive, not only
    # deep in rule 5.
    assert block.index('"type":"shutdown_response"') < hedge


def test_render_subagent_has_primacy_banner():
    # The role body re-anchors a "do one task then stop" identity between the
    # default teammate prompt and the trailing block; the banner gives the
    # protocol primacy as well as recency. Render a real agent and assert the
    # banner leads, the role follows, and the full block still trails.
    import server

    name, cls = next(iter(server.AGENT_CLASSES.items()))
    out = render_subagent(name, cls, {"mode": "subagent"}, teams_mode=True)
    assert "<team_protocol_priority>" in out
    banner_at = out.index(PROTOCOL_BANNER)
    role_at = out.index("<role>")
    block_at = out.index(TEAM_CONTEXT_BLOCK)
    assert banner_at < role_at < block_at, "banner leads, role middle, block trails"


def test_cross_scope_and_wireup_and_trace_rules_present():
    block = TEAM_CONTEXT_BLOCK
    assert "CROSS-SCOPE MINIMAL EDITS" in block
    assert "WIRE-UP IS PART OF THE FEATURE" in block
    assert "TRACE BEFORE YOU CODE" in block


def test_app_store_check_registered_and_runs():
    from skills import SKILL_REGISTRY, get_skill
    from utils.skill_registry import build_skill_registry

    assert "app_store_check" in SKILL_REGISTRY
    assert "app_store_check" in build_skill_registry()

    skill = get_skill("app_store_check")
    assert skill.category == "quality"

    out_both = skill.execute(platform="both")
    assert out_both["success"] is True
    g = out_both["guidance"]
    assert "Info.plist" in g and "targetSdkVersion" in g

    out_ios = skill.execute(platform="ios")
    assert "Info.plist" in out_ios["guidance"]
    assert "targetSdkVersion" not in out_ios["guidance"]

    out_android = skill.execute(platform="android")
    assert "targetSdkVersion" in out_android["guidance"]
    assert "Info.plist" not in out_android["guidance"]
