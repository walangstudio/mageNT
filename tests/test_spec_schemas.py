"""Validator coverage for agents/spec_schemas.py.

These tests pin the structural rules that competitors enforce only by
convention — tautological GIVEN/WHEN/THEN, missing RFC 2119 verbs,
duplicate FR-IDs, etc.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from agents.spec_schemas import (
    SPEC_SCHEMAS,
    Audit,
    ClarificationLog,
    Constitution,
    FeatureSpec,
    FunctionalRequirement,
    GivenWhenThen,
    ImplementationPlan,
    NFRTargets,
    PhaseAudit,
    SpecDelta,
    Task,
    TaskList,
    TechStack,
    Component,
    Clarification,
    UserStory,
)


# ---------- helpers --------------------------------------------------------

def _ok_gwt() -> GivenWhenThen:
    return GivenWhenThen(
        given="An empty todo store at ~/.todo.json",
        when="The user runs `todo add buy-milk`",
        then="`todo list` outputs `1. buy-milk` on a single line",
    )


def _ok_user_story() -> UserStory:
    return UserStory(
        priority="P1",
        title="Add task",
        why="Core flow; no other story matters without it.",
        independent_test="Run `todo add x && todo list` and assert `x` appears.",
        scenarios=[_ok_gwt()],
    )


def _ok_fr(id_: str = "FR-001", verb: str = "MUST") -> FunctionalRequirement:
    return FunctionalRequirement(
        id=id_,
        statement=f"System {verb} persist tasks across CLI invocations.",
        rfc2119=verb,
    )


def _ok_spec() -> FeatureSpec:
    return FeatureSpec(
        spec_id="todo-cli-x",
        feature_name="Add task",
        user_stories=[_ok_user_story()],
        requirements=[_ok_fr()],
        success_criteria=["round-trip: add then list returns the same task"],
    )


# ---------- Constitution ---------------------------------------------------

class TestConstitution:
    def test_happy_path(self):
        c = Constitution(
            project_name="todo-cli",
            principles=["Prefer the boring choice", "No PII in logs", "Single binary"],
            nfr_targets=NFRTargets(latency_p99_ms=50),
        )
        assert c.project_name == "todo-cli"
        assert len(c.principles) == 3

    def test_minimum_three_principles(self):
        with pytest.raises(ValidationError):
            Constitution(
                project_name="x",
                principles=["only one"],
                nfr_targets=NFRTargets(),
            )

    def test_empty_project_name_rejected(self):
        with pytest.raises(ValidationError):
            Constitution(
                project_name="",
                principles=["a", "b", "c"],
                nfr_targets=NFRTargets(),
            )


# ---------- GivenWhenThen tautology rejection ------------------------------

class TestGivenWhenThen:
    def test_happy_path(self):
        _ok_gwt()  # no exception

    @pytest.mark.parametrize("bad", [
        "feature works as specified",
        "should work as expected",
        "the feature should be ok",
        "should work correctly",
    ])
    def test_tautological_then_rejected(self, bad: str):
        with pytest.raises(ValidationError, match="tautological"):
            GivenWhenThen(
                given="An empty store exists",
                when="The user runs `todo add x`",
                then=bad,
            )

    def test_when_must_differ_from_given(self):
        with pytest.raises(ValidationError, match="WHEN must differ from GIVEN"):
            GivenWhenThen(
                given="The system is in state A",
                when="The system is in state A",
                then="The output contains `1. x`",
            )

    def test_then_must_differ_from_when(self):
        with pytest.raises(ValidationError, match="THEN must differ from WHEN"):
            GivenWhenThen(
                given="An empty store exists",
                when="The user runs `todo add x` — output is `added`",
                then="The user runs `todo add x` — output is `added`",
            )

    def test_too_short_field_rejected(self):
        with pytest.raises(ValidationError):
            GivenWhenThen(given="x", when="y", then="z")


# ---------- FunctionalRequirement -----------------------------------------

class TestFunctionalRequirement:
    def test_happy_path(self):
        fr = _ok_fr()
        assert fr.id == "FR-001"

    def test_id_pattern(self):
        with pytest.raises(ValidationError):
            FunctionalRequirement(id="FR-1", statement="System MUST do x.", rfc2119="MUST")
        with pytest.raises(ValidationError):
            FunctionalRequirement(id="REQ-001", statement="System MUST do x.", rfc2119="MUST")

    def test_statement_must_contain_rfc2119_verb(self):
        with pytest.raises(ValidationError, match="RFC 2119"):
            FunctionalRequirement(
                id="FR-002",
                statement="System should accept user input.",
                rfc2119="MUST",
            )

    def test_should_verb_works(self):
        fr = FunctionalRequirement(
            id="FR-003",
            statement="System SHOULD log to stdout when verbose.",
            rfc2119="SHOULD",
        )
        assert fr.rfc2119 == "SHOULD"


# ---------- FeatureSpec ----------------------------------------------------

class TestFeatureSpec:
    def test_happy_path(self):
        s = _ok_spec()
        assert s.feature_name == "Add task"
        assert len(s.requirements) == 1

    def test_duplicate_fr_ids_rejected(self):
        with pytest.raises(ValidationError, match="unique"):
            FeatureSpec(
                spec_id="x",
                feature_name="x",
                user_stories=[_ok_user_story()],
                requirements=[
                    _ok_fr("FR-001"),
                    _ok_fr("FR-001"),
                ],
                success_criteria=["x"],
            )

    def test_all_clarifications_aggregated(self):
        s = FeatureSpec(
            spec_id="x", feature_name="x",
            user_stories=[_ok_user_story()],
            requirements=[
                FunctionalRequirement(
                    id="FR-001",
                    statement="System MUST authenticate.",
                    rfc2119="MUST",
                    needs_clarification=["which auth method?"],
                ),
            ],
            success_criteria=["x"],
            needs_clarification=["which database?"],
        )
        all_q = s.all_clarifications()
        assert "which database?" in all_q
        assert any("FR-001:" in q and "auth method" in q for q in all_q)


# ---------- TaskList -------------------------------------------------------

class TestTaskList:
    def _ok_task(self, id_="T001", deps=None):
        return Task(
            id=id_,
            title="Implement persistence layer",
            files=["src/store.py"],
            parallel_safe=True,
            fr_ids=["FR-001"],
            failing_test_path="tests/T001-persistence.py",
            depends_on=deps or [],
        )

    def test_happy_path(self):
        tl = TaskList(spec_id="x", tasks=[self._ok_task()])
        assert len(tl.tasks) == 1

    def test_id_pattern(self):
        with pytest.raises(ValidationError):
            Task(
                id="T1",
                title="x", files=["f"], parallel_safe=True,
                fr_ids=["FR-001"], failing_test_path="t",
            )

    def test_duplicate_task_ids_rejected(self):
        with pytest.raises(ValidationError, match="unique"):
            TaskList(spec_id="x", tasks=[self._ok_task("T001"), self._ok_task("T001")])

    def test_dependency_must_exist(self):
        with pytest.raises(ValidationError, match="depends on missing task"):
            TaskList(spec_id="x", tasks=[self._ok_task("T001", deps=["T999"])])


# ---------- ImplementationPlan + Audit + SpecDelta -------------------------

class TestPlanAuditDelta:
    def test_plan_round_trip(self):
        p = ImplementationPlan(
            spec_id="x",
            tech_stack=TechStack(language="Python", framework="Click"),
            components=[Component(
                name="store",
                responsibility="Persist tasks to disk as JSON.",
                owns_fr_ids=["FR-001"],
            )],
        )
        assert p.tech_stack.language == "Python"

    def test_audit_round_trip(self):
        a = Audit(
            spec_id="x",
            phases=[PhaseAudit(phase="Test", status="COMPLETE", evidence="pytest 5/5")],
            recommendation="GO",
        )
        assert a.recommendation == "GO"

    def test_clarification_log_must_be_non_empty(self):
        with pytest.raises(ValidationError):
            ClarificationLog(spec_id="x", items=[])

    def test_spec_delta_must_have_at_least_one_change(self):
        with pytest.raises(ValidationError, match="at least one change"):
            SpecDelta(spec_id="x", base_version="v1")

    def test_spec_delta_added_only_works(self):
        d = SpecDelta(
            spec_id="x", base_version="v1",
            added=[_ok_fr("FR-008")],
        )
        assert len(d.added) == 1


# ---------- Registry sanity ------------------------------------------------

def test_registry_keys_match_classes():
    expected = {
        "constitution", "feature_spec", "clarification_log", "plan",
        "tasks", "task_implementation", "implementation_trace",
        "audit", "spec_delta",
    }
    assert set(SPEC_SCHEMAS) == expected


def test_every_registered_schema_emits_json_schema():
    for name, cls in SPEC_SCHEMAS.items():
        schema = cls.model_json_schema()
        assert isinstance(schema, dict) and "properties" in schema, \
            f"{name} did not emit a usable JSON schema"
