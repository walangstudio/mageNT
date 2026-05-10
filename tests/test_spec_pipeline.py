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
    NFRTargets,
    FeatureSpec,
    FunctionalRequirement,
    UserStory,
    GivenWhenThen,
    ImplementationPlan,
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
