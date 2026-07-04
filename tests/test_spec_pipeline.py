"""End-to-end smoke for the Phase 7 spec pipeline.

Exercises the full chain — Constitution → FeatureSpec → Clarify → Plan →
Tasks (with failing test files written) → ImplementationTrace → Audit —
against a tiny ``todo-cli`` fixture using stub LLMs (no network).

Each ``stub_*`` function emits a valid Pydantic-instance JSON for the phase
under test, so every gate fires the way it would in production.
"""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

import pytest

from agents.spec_schemas import (
    Audit,
    ClarificationLog,
    Clarification,
    Constitution,
    DesignPack,
    Journey,
    NFRTargets,
    FeatureSpec,
    FunctionalRequirement,
    UserStory,
    GivenWhenThen,
    ImplementationPlan,
    Screen,
    TechStack,
    Component,
    TaskList,
    Task,
    ImplementationTrace,
    CommitTrace,
    SpecDelta,
    PhaseAudit,
    ReviewerFinding,
)
from utils.spec_pipeline import (
    GateError,
    PhaseEscalation,
    require_artifact,
    require_resolved_clarifications,
    run_multi_agent_phase,
    run_single_agent_phase,
)
from utils.spec_store import SpecStore


@pytest.fixture
def store(tmp_path: Path) -> SpecStore:
    return SpecStore(tmp_path / "specs")


SPEC_ID = "todo-cli-test"


# ---------- happy-path stubs (one per phase) -----------------------------------

def _const_stub(*_a, **_kw):
    c = Constitution(
        project_name="todo-cli",
        principles=["Prefer the boring choice", "No PII in logs", "Single binary"],
        nfr_targets=NFRTargets(latency_p99_ms=50),
    )
    return (c.model_dump_json(), {"input_tokens": 100, "output_tokens": 80})


def _spec_stub(*_a, **_kw):
    spec = FeatureSpec(
        spec_id=SPEC_ID,
        feature_name="Add task",
        user_stories=[UserStory(
            priority="P1",
            title="Add task",
            why="Core flow; nothing else matters without it.",
            independent_test="Run `todo add x && todo list` and assert `x` appears.",
            scenarios=[GivenWhenThen(
                given="An empty todo store at ~/.todo.json",
                when="The user runs `todo add buy-milk`",
                then="`todo list` outputs `1. buy-milk` on a single line",
            )],
        )],
        requirements=[
            FunctionalRequirement(
                id="FR-001",
                statement="System MUST persist tasks across CLI invocations.",
                rfc2119="MUST",
                needs_clarification=["which storage backend?"],
            ),
            FunctionalRequirement(
                id="FR-002",
                statement="System MUST list tasks in insertion order.",
                rfc2119="MUST",
            ),
        ],
        success_criteria=["round-trip: add then list returns the same task"],
        needs_clarification=["which file format?"],
    )
    return (spec.model_dump_json(), {"input_tokens": 200, "output_tokens": 200})


def _clarify_stub(*_a, **_kw):
    log = ClarificationLog(
        spec_id=SPEC_ID,
        items=[
            Clarification(
                question="which storage backend?",
                answer="JSON file at ~/.todo.json",
                addressed_fr_ids=["FR-001"],
            ),
            Clarification(
                question="which file format?",
                answer="JSON, indent=2 for human readability.",
                addressed_fr_ids=["FR-001"],
            ),
        ],
    )
    return (log.model_dump_json(), {})


def _plan_stub(*_a, **_kw):
    plan = ImplementationPlan(
        spec_id=SPEC_ID,
        tech_stack=TechStack(language="Python", framework="Click"),
        components=[
            Component(
                name="store",
                responsibility="Persist tasks to disk as JSON; load on startup.",
                owns_fr_ids=["FR-001"],
            ),
            Component(
                name="cli",
                responsibility="Parse argv and dispatch to add/list/done handlers.",
                owns_fr_ids=["FR-002"],
            ),
        ],
    )
    return (plan.model_dump_json(), {})


def _tasks_stub(*_a, **_kw):
    tl = TaskList(
        spec_id=SPEC_ID,
        tasks=[
            Task(
                id="T001",
                title="Implement persistence layer",
                files=["src/store.py"],
                parallel_safe=True,
                fr_ids=["FR-001"],
                failing_test_path="tests/test_T001-persistence.py",
            ),
            Task(
                id="T002",
                title="Implement add+list commands",
                files=["src/cli.py"],
                parallel_safe=True,
                fr_ids=["FR-002"],
                failing_test_path="tests/test_T002-cli.py",
                depends_on=["T001"],
            ),
        ],
    )
    return (tl.model_dump_json(), {})


def _trace_stub(*_a, **_kw):
    trace = ImplementationTrace(
        spec_id=SPEC_ID,
        commits=[
            CommitTrace(fr_id="FR-001", task_id="T001", commit_sha="abc1234",
                          files=["src/store.py"], test_passed=True),
            CommitTrace(fr_id="FR-002", task_id="T002", commit_sha="def5678",
                          files=["src/cli.py"], test_passed=True),
        ],
    )
    return (trace.model_dump_json(), {})


def _audit_stub(*_a, **_kw):
    audit = Audit(
        spec_id=SPEC_ID,
        phases=[
            PhaseAudit(phase="Requirements", status="COMPLETE", evidence="spec.json"),
            PhaseAudit(phase="Test", status="COMPLETE", evidence="2/2 tests pass"),
            PhaseAudit(phase="Security", status="PARTIAL", evidence="no SAST",
                        notes="defer to security_engineer for SAST"),
        ],
        reviewer_findings=[
            ReviewerFinding(reviewer="qa_engineer",
                              summary="all integration tests pass; consider edge cases.",
                              blocking=False),
        ],
        recommendation="GO-WITH-CONDITIONS",
    )
    return (audit.model_dump_json(), {})


# ---------- end-to-end happy path ----------------------------------------------

def test_full_pipeline_happy_path(store: SpecStore):
    """Constitution → spec → clarify → plan → tasks → trace → audit. All clean."""
    # 1. Constitution
    r = run_single_agent_phase(
        spec_store=store, spec_id=SPEC_ID, kind="constitution",
        agent_name="delivery_manager", user_intent="Build a todo CLI",
        llm_call=_const_stub,
    )
    assert r.attempts == 1
    assert (store.base_dir / SPEC_ID / "constitution.json").exists()

    # 2. Spec
    r = run_single_agent_phase(
        spec_store=store, spec_id=SPEC_ID, kind="feature_spec",
        agent_name="business_analyst",
        user_intent="todo CLI: add/list/done",
        llm_call=_spec_stub,
    )
    spec = store.load_artifact(SPEC_ID, "feature_spec")
    assert len(spec.requirements) == 2
    assert spec.all_clarifications()  # has open questions

    # 3. Plan must be gated until clarifications are resolved
    with pytest.raises(GateError, match="unresolved"):
        require_resolved_clarifications(spec)

    # 4. Clarify
    run_single_agent_phase(
        spec_store=store, spec_id=SPEC_ID, kind="clarification_log",
        agent_name="business_analyst", user_intent="Resolve open items",
        llm_call=_clarify_stub,
    )
    # Mark spec as clarified the same way the magent_clarify handler does
    cleaned = spec.model_copy(update={
        "needs_clarification": [],
        "requirements": [r.model_copy(update={"needs_clarification": []})
                          for r in spec.requirements],
    })
    store.save_artifact(SPEC_ID, "feature_spec", cleaned)

    # Now the gate passes
    spec = store.load_artifact(SPEC_ID, "feature_spec")
    require_resolved_clarifications(spec)

    # 5. Plan
    r = run_single_agent_phase(
        spec_store=store, spec_id=SPEC_ID, kind="plan",
        agent_name="system_architect",
        user_intent="Produce an ImplementationPlan", llm_call=_plan_stub,
    )
    plan = store.load_artifact(SPEC_ID, "plan")
    # Every FR-ID is owned by some component
    owned = {fr for c in plan.components for fr in c.owns_fr_ids}
    assert owned >= {r.id for r in spec.requirements}

    # 6. Tasks (write the failing test stubs the way magent_tasks would)
    run_single_agent_phase(
        spec_store=store, spec_id=SPEC_ID, kind="tasks",
        agent_name="sdet", user_intent="Decompose into tasks", llm_call=_tasks_stub,
    )
    tasks = store.load_artifact(SPEC_ID, "tasks")
    for t in tasks.tasks:
        store.write_failing_test(SPEC_ID, t.failing_test_path,
                                   f"def test_{t.id.lower()}():\n    assert False\n")

    # 7. Trace
    run_single_agent_phase(
        spec_store=store, spec_id=SPEC_ID, kind="implementation_trace",
        agent_name="fullstack_developer",
        user_intent="Implement the tasks", llm_call=_trace_stub,
    )
    trace = store.load_artifact(SPEC_ID, "implementation_trace")
    assert all(c.test_passed for c in trace.commits)

    # 8. Audit
    run_single_agent_phase(
        spec_store=store, spec_id=SPEC_ID, kind="audit",
        agent_name="delivery_manager",
        user_intent="Audit the implementation", llm_call=_audit_stub,
    )
    audit = store.load_artifact(SPEC_ID, "audit")
    assert audit.recommendation in {"GO", "GO-WITH-CONDITIONS"}

    # 9. Run the validator over the whole dir
    import sys as _sys
    _sys.path.insert(0, "tools")
    from validate_spec import validate_spec_dir
    report = validate_spec_dir(store.base_dir / SPEC_ID)
    assert report.ok, f"validator failed: {report.errors}"

    # 10. Cost ledger has every phase
    cost = json.loads((store.base_dir / SPEC_ID / "cost.json").read_text(encoding="utf-8"))
    expected_phases = {"constitution", "feature_spec", "clarification_log",
                        "plan", "tasks", "implementation_trace", "audit"}
    assert expected_phases.issubset(set(cost.keys()))


# ---------- multi-agent merge ------------------------------------------------

def test_multi_agent_phase_merges_contributions(store: SpecStore):
    """Multi-agent phase fans out + asks merger to consolidate into the schema."""
    contributors_called: list = []

    def _stub(agent, sys_p, user, ctx):
        contributors_called.append(agent)
        # Final call (merger) returns valid Constitution; contributors return prose.
        if "Consolidate" in user:
            c = Constitution(
                project_name="x",
                principles=["a", "b", "c"], nfr_targets=NFRTargets())
            return (c.model_dump_json(), {})
        return (f"opinion from {agent}", {})

    r = run_multi_agent_phase(
        spec_store=store, spec_id=SPEC_ID, kind="constitution",
        agent_names=["delivery_manager", "system_architect"],
        merger_agent="delivery_manager",
        user_intent="Build x", llm_call=_stub,
    )
    # Two contributors + one merger = three calls
    assert contributors_called == [
        "delivery_manager", "system_architect", "delivery_manager",
    ]
    assert r.model.project_name == "x"


# ---------- design phase (optional, UI-facing) --------------------------------

def _design_stub(*_a, **_kw):
    d = DesignPack(
        spec_id=SPEC_ID,
        journeys=[Journey(
            id="JN-001", title="Add a task", role="user",
            fr_ids=["FR-001", "FR-002"],
            steps=["open the CLI", "run todo add", "run todo list"])],
        screens=[Screen(
            id="SC-001", name="Task list", purpose="Shows all tasks in order",
            states=["default", "empty"], fr_ids=["FR-002"],
            journey_ids=["JN-001"])],
    )
    return (d.model_dump_json(), {})


def test_design_phase_persists_design_json(store: SpecStore):
    def _stub(agent, sys_p, user, ctx):
        if "Consolidate" in user:
            return _design_stub()
        return (f"ux notes from {agent}", {})

    r = run_multi_agent_phase(
        spec_store=store, spec_id=SPEC_ID, kind="design",
        agent_names=["ui_ux_designer", "business_analyst"],
        merger_agent="ui_ux_designer",
        user_intent="Produce the DesignPack", llm_call=_stub,
    )
    assert (store.base_dir / SPEC_ID / "design.json").exists()
    design = store.load_artifact(SPEC_ID, "design")
    assert design.journeys[0].id == "JN-001"
    assert r.model.screens[0].journey_ids == ["JN-001"]


# ---------- validator: coverage is a FAIL, design cross-refs -------------------

def _write_min_spec(store: SpecStore, spec_id: str) -> FeatureSpec:
    spec = FeatureSpec(
        spec_id=spec_id, feature_name="x",
        user_stories=[UserStory(
            priority="P1", title="Add", why="Core flow here.",
            independent_test="run add+list and assert",
            scenarios=[GivenWhenThen(
                given="empty store at ~/.todo",
                when="user runs `todo add x`",
                then="output shows `1. x`")])],
        requirements=[
            FunctionalRequirement(id="FR-001", statement="System MUST persist data.",
                                  rfc2119="MUST"),
            FunctionalRequirement(id="FR-002", statement="System MUST list tasks.",
                                  rfc2119="MUST"),
        ],
        success_criteria=["x"])
    store.save_artifact(spec_id, "feature_spec", spec)
    return spec


def test_validator_fails_on_uncovered_fr(store: SpecStore):
    """FR without an owning component is an ERROR, not a warning."""
    from tools.validate_spec import validate_spec_dir
    sid = "uncovered-fr"
    _write_min_spec(store, sid)
    store.save_artifact(sid, "plan", ImplementationPlan(
        spec_id=sid, tech_stack=TechStack(language="py"),
        components=[Component(name="core", responsibility="owns persistence only",
                              owns_fr_ids=["FR-001"])]))
    report = validate_spec_dir(store.base_dir / sid)
    assert not report.ok
    assert any("FR-002" in e and "owning component" in e for e in report.errors)


def test_validator_design_cross_refs(store: SpecStore):
    from tools.validate_spec import validate_spec_dir
    sid = "design-refs"
    _write_min_spec(store, sid)
    store.save_artifact(sid, "design", DesignPack(
        spec_id=sid,
        journeys=[Journey(id="JN-001", title="Add task", role="user",
                          fr_ids=["FR-001", "FR-999"], steps=["a", "b"])],
        screens=[Screen(id="SC-001", name="Home", purpose="Lists everything here")]))
    report = validate_spec_dir(store.base_dir / sid)
    # unknown FR reference is an error
    assert any("JN-001" in e and "FR-999" in e for e in report.errors)
    # FR-002 exercised by no journey is a warning
    assert any("FR-002" in w for w in report.warnings)


# ---------- gates --------------------------------------------------------------

def test_missing_artifact_raises_gate_error(store: SpecStore):
    with pytest.raises(GateError):
        require_artifact(store, "ghost-id", "constitution")


def test_unresolved_clarifications_block_downstream(store: SpecStore):
    spec = FeatureSpec(
        spec_id="x", feature_name="x",
        user_stories=[UserStory(
            priority="P1", title="Add", why="Core flow.",
            independent_test="run add+list",
            scenarios=[GivenWhenThen(
                given="empty store at ~/.todo",
                when="user runs `todo add x`",
                then="output shows `1. x`",
            )],
        )],
        requirements=[FunctionalRequirement(
            id="FR-001", statement="System MUST persist data.", rfc2119="MUST")],
        success_criteria=["x"],
        needs_clarification=["which db?"],
    )
    with pytest.raises(GateError, match="unresolved"):
        require_resolved_clarifications(spec)


# ---------- post_validate (cross-artifact checks feed the retry loop) ----------

def test_post_validate_failure_feeds_retry_and_escalates(store: SpecStore):
    """A schema-valid plan that fails post_validate is rejected like a schema
    failure — the error re-enters the prompt and exhausts the retry budget."""
    intents_seen = []

    def _stub(agent, sys_p, user, ctx, **_kw):
        intents_seen.append(user)
        return _plan_stub()

    def _reject_uncovered(plan):
        owned = {fr for c in plan.components for fr in c.owns_fr_ids}
        uncovered = sorted({"FR-001", "FR-002", "FR-003"} - owned)
        return f"components leave FR-IDs unowned: {uncovered}" if uncovered else None

    with pytest.raises(PhaseEscalation) as exc_info:
        run_single_agent_phase(
            spec_store=store, spec_id="pv-test", kind="plan",
            agent_name="system_architect", user_intent="plan it",
            llm_call=_stub, post_validate=_reject_uncovered,
        )
    assert "FR-003" in exc_info.value.last_error
    # The rejection was injected back into attempts 2 and 3.
    assert any("unowned" in u for u in intents_seen[1:])
    # Nothing was persisted.
    assert store.load_artifact("pv-test", "plan") is None


def test_post_validate_pass_persists(store: SpecStore):
    r = run_single_agent_phase(
        spec_store=store, spec_id="pv-ok", kind="plan",
        agent_name="system_architect", user_intent="plan it",
        llm_call=lambda *a, **k: _plan_stub(),
        post_validate=lambda plan: None,
    )
    assert r.attempts == 1
    assert store.load_artifact("pv-ok", "plan") is not None


# ---------- escalation ---------------------------------------------------------

def test_escalation_after_retry_budget(store: SpecStore):
    """Pipeline escalates after RETRY_BUDGET consecutive validation failures."""
    def _bad(*_a, **_kw):
        return ("not json", {})

    with pytest.raises(PhaseEscalation) as exc_info:
        run_single_agent_phase(
            spec_store=store, spec_id="esc-test", kind="constitution",
            agent_name="delivery_manager", user_intent="x", llm_call=_bad,
        )
    assert exc_info.value.attempts == 3


# ---------- spec delta -------------------------------------------------------

def test_spec_delta_persists_to_deltas_dir(store: SpecStore):
    delta = SpecDelta(
        spec_id=SPEC_ID, base_version="v1.0",
        added=[FunctionalRequirement(
            id="FR-008", statement="System MUST support tags on tasks.", rfc2119="MUST")],
    )
    path = store.save_artifact(SPEC_ID, "spec_delta", delta)
    assert path.parent.name == "deltas"
    assert path.name == "v1.0.json"
    loaded = store.load_deltas(SPEC_ID)
    assert len(loaded) == 1
    assert loaded[0].added[0].id == "FR-008"
