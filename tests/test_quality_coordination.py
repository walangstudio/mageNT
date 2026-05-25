"""Tests for the 0.7.x code-quality + coordination improvements."""

import pytest

from rules import RulesEngine, RulesConfig
from agents.spec_schemas import Task
from utils.implement_runner import _ordered_tasks


# ---- #2 dependency-aware task ordering ------------------------------------

def _task(tid, deps):
    return Task(
        id=tid, title=f"task {tid}", files=[f"f{tid}"], parallel_safe=True,
        fr_ids=[f"FR-00{tid[-1]}"], failing_test_path=f"t{tid}", depends_on=deps,
    )


def test_ordered_tasks_respects_depends_on():
    out = [t.id for t in _ordered_tasks([_task("T003", ["T001"]), _task("T001", []), _task("T002", ["T001"])])]
    assert out.index("T001") < out.index("T002")
    assert out.index("T001") < out.index("T003")


def test_ordered_tasks_ignores_deps_outside_subset():
    assert [t.id for t in _ordered_tasks([_task("T002", ["T001"])])] == ["T002"]


def test_ordered_tasks_detects_cycle():
    with pytest.raises(RuntimeError, match="cycle"):
        _ordered_tasks([_task("T001", ["T002"]), _task("T002", ["T001"])])


# ---- #3 config-driven thresholds + release profile ------------------------

CFG = {
    "categories": {"security": True, "coding_style": True, "testing": True,
                   "git": True, "performance": True},
    "fail_on_warnings": False,
    "rule_settings": {"file-size-limit": {"max_lines": 123},
                      "mutation-score-minimum": {"min_score": 70}},
}


def test_from_dict_applies_friendly_name_thresholds():
    eng = RulesEngine(RulesConfig.from_dict(CFG))
    assert eng._rule_instances["file-size-limit"]._max_lines == 123
    assert eng._rule_instances["mutation-score-minimum"]._min_score == 70


def test_release_profile_makes_warnings_block():
    assert RulesConfig.from_dict(CFG, profile="release").fail_on_warnings is True
    assert RulesConfig.from_dict(CFG).fail_on_warnings is False


# ---- #4 mutation-score rule -----------------------------------------------

def test_mutation_rule_absent_metadata_passes():
    eng = RulesEngine(RulesConfig.from_dict(CFG))
    assert eng.check_code("x = 1\n", "x.py").passed


def test_mutation_rule_low_score_flags():
    eng = RulesEngine(RulesConfig.from_dict(CFG))
    report = eng.check_code("x = 1\n", "x.py", mutation_score=10)
    names = [r.rule_name for r in report.results if not r.passed]
    assert "mutation-score-minimum" in names


# ---- #1 partial-result resilience -----------------------------------------

VALID_AUDIT = (
    '{"spec_id":"S1","phases":[{"phase":"Requirements","status":"COMPLETE"}],'
    '"reviewer_findings":[],"recommendation":"GO"}'
)


def test_multi_agent_phase_excludes_failed_contributor(tmp_path):
    from utils.spec_pipeline import run_multi_agent_phase
    from utils.spec_store import SpecStore

    store = SpecStore(tmp_path)

    def fake_llm(name, system_prompt, user_task, context, **kwargs):
        if "Consolidate" in user_task:                 # the merger call
            return VALID_AUDIT, {}
        if name == "performance_engineer":             # this reviewer always fails
            raise RuntimeError("timeout")
        return f"{name} review text", {}

    res = run_multi_agent_phase(
        spec_store=store, spec_id="S1", kind="audit",
        agent_names=["delivery_manager", "security_engineer",
                     "performance_engineer", "qa_engineer"],
        merger_agent="delivery_manager",
        user_intent="Audit it.",
        llm_call=fake_llm,
    )
    assert res.failed_contributors == ["performance_engineer"]


# ---- new agents + execution skills ----------------------------------------

NEW_AGENTS = ["code_reviewer", "refactoring_specialist", "observability_engineer",
              "data_engineer", "ml_engineer", "accessibility_specialist"]


def test_new_agents_registered():
    import server
    for a in NEW_AGENTS:
        assert a in server.AGENT_CLASSES, a


def test_code_reviewer_can_join_audit_findings():
    from agents.spec_schemas import ReviewerFinding
    f = ReviewerFinding(reviewer="code_reviewer", summary="needs more tests here", blocking=True)
    assert f.reviewer == "code_reviewer"


def test_execution_skills_registered_and_run():
    from utils.skill_registry import build_skill_registry
    reg = build_skill_registry()
    for s in ["lint", "typecheck", "format", "mutation_test", "dependency_audit"]:
        assert s in reg, s
    # lint runs and is skip-safe when no linter is installed
    out = reg["lint"].execute(path=".")
    assert "passed" in out["context"]
