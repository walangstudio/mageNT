"""Coverage-matrix builder (tools/trace_matrix.py)."""

from __future__ import annotations

import pytest

from agents.spec_schemas import (
    APIEndpoint,
    CommitTrace,
    Component,
    DesignPack,
    FeatureSpec,
    FunctionalRequirement,
    GivenWhenThen,
    ImplementationPlan,
    ImplementationTrace,
    Journey,
    Screen,
    Task,
    TaskList,
    TechStack,
    UserStory,
)
from tools.trace_matrix import build_trace_report
from tools.validate_spec import ARTIFACT_FILES


def _fr(id_: str) -> FunctionalRequirement:
    return FunctionalRequirement(
        id=id_, statement="System MUST persist tasks across invocations.",
        rfc2119="MUST")


def _spec() -> FeatureSpec:
    return FeatureSpec(
        spec_id="x", feature_name="todo",
        user_stories=[UserStory(
            priority="P1", title="Add task", why="Core flow, nothing works without it.",
            independent_test="Run add then list and assert the task appears.",
            scenarios=[GivenWhenThen(
                given="An empty todo store at ~/.todo.json",
                when="The user runs `todo add buy-milk`",
                then="`todo list` outputs `1. buy-milk` on one line")])],
        requirements=[_fr("FR-001"), _fr("FR-002")],
        success_criteria=["add-then-list round trip"])


def _write(spec_dir, kind, model):
    spec_dir.mkdir(parents=True, exist_ok=True)
    (spec_dir / ARTIFACT_FILES[kind]).write_text(
        model.model_dump_json(indent=2), encoding="utf-8")


def _full_fixture(tmp_path):
    d = tmp_path / "spec-x"
    _write(d, "feature_spec", _spec())
    _write(d, "design", DesignPack(
        spec_id="x",
        journeys=[Journey(id="JN-001", title="Add a task", role="user",
                          fr_ids=["FR-001"], steps=["open", "type", "save"])],
        screens=[Screen(id="SC-001", name="Home", purpose="Lists all the tasks",
                        fr_ids=["FR-001"], journey_ids=["JN-001"]),
                 Screen(id="SC-002", name="About", purpose="Static info page here")]))
    _write(d, "plan", ImplementationPlan(
        spec_id="x", tech_stack=TechStack(language="python"),
        components=[Component(name="core", responsibility="owns CRUD and persistence",
                              owns_fr_ids=["FR-001"])],
        api_contracts=[APIEndpoint(path="/tasks", method="POST", fr_ids=["FR-001"])]))
    _write(d, "tasks", TaskList(
        spec_id="x",
        tasks=[Task(id="T001", title="Implement add", files=["core.py"],
                    parallel_safe=True, fr_ids=["FR-001"],
                    failing_test_path="tests/test_add.py")]))
    _write(d, "implementation_trace", ImplementationTrace(
        spec_id="x",
        commits=[CommitTrace(fr_id="FR-001", task_id="T001",
                             commit_sha="abc1234def", test_passed=True)]))
    return d


def test_full_fixture_rows_and_gaps(tmp_path):
    report = build_trace_report(_full_fixture(tmp_path))
    assert report["spec_id"] == "x"
    by_id = {r["fr_id"]: r for r in report["rows"]}
    covered = by_id["FR-001"]
    assert covered["journeys"] == ["JN-001"]
    assert covered["screens"] == ["SC-001"]
    assert covered["components"] == ["core"]
    assert covered["endpoints"] == ["POST /tasks"]
    assert covered["tasks"] == ["T001"]
    assert covered["tests"] == ["tests/test_add.py"]
    assert covered["commits"] == ["abc1234"]
    # FR-002 is covered by nothing — every hard gap named
    assert not report["ok"]
    for gap in ("FR-002 has no owning component",
                "FR-002 has no task", "FR-002 has no test", "FR-002 has no commit"):
        assert gap in report["gaps"], gap
    # journey/screen coverage is advice, not broken linkage — mirrors magent_validate
    for warning in ("FR-002 appears in no journey", "SC-002 covers no FR"):
        assert warning in report["warnings"], warning
        assert warning not in report["gaps"]


def test_unknown_fr_refs_in_screens_and_roles_are_gaps(tmp_path):
    d = tmp_path / "spec-dangling"
    _write(d, "feature_spec", _spec())
    _write(d, "design", DesignPack(
        spec_id="x",
        journeys=[Journey(id="JN-001", title="Add a task", role="user",
                          fr_ids=["FR-999"], steps=["a"])],
        screens=[Screen(id="SC-001", name="Home", purpose="Lists all the tasks",
                        fr_ids=["FR-998"])],
        role_permissions=[{"role": "admin", "can": ["delete"], "fr_ids": ["FR-997"]}]))
    report = build_trace_report(d)
    assert not report["ok"]
    assert "JN-001 references unknown FR-999" in report["gaps"]
    assert "SC-001 references unknown FR-998" in report["gaps"]
    assert "role 'admin' references unknown FR-997" in report["gaps"]


def test_spec_only_run_is_clean(tmp_path):
    d = tmp_path / "spec-min"
    _write(d, "feature_spec", _spec())
    report = build_trace_report(d)
    # no downstream artifacts -> no gap claims about them
    assert report["ok"]
    assert report["gaps"] == []
    assert report["warnings"] == []
    assert len(report["rows"]) == 2


def test_missing_spec_raises(tmp_path):
    with pytest.raises(ValueError, match="spec.json not found"):
        build_trace_report(tmp_path / "empty")


def test_corrupt_artifact_raises_with_real_parse_error(tmp_path):
    # tmp_path is outside the repo — the error must carry the real parse
    # failure, not a relative_to() ValueError masking it.
    d = tmp_path / "spec-bad"
    _write(d, "feature_spec", _spec())
    (d / ARTIFACT_FILES["plan"]).write_text("{not json", encoding="utf-8")
    with pytest.raises(ValueError, match=r"(?s)plan\.json.*Invalid JSON"):
        build_trace_report(d)
