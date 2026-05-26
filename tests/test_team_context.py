"""Guards on the team-protocol gate and the app_store_check skill.

The Wave-7 review found GA Agent-tool teammates opting out of the report/
shutdown protocol because the old gate keyed on the deprecated
CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS env var and exempted "one-shot subagents".
These tests pin the capability-based rewrite so it can't regress.
"""

from tools.generate_dispatch import TEAM_CONTEXT_BLOCK


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
