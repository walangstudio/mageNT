"""Spec-level code constraints: extraction, matching, and the implement gate."""

import json
import shutil
import subprocess

import pytest

from agents.spec_schemas import (
    Component, Constraint, FeatureSpec, FunctionalRequirement, GivenWhenThen,
    ImplementationPlan, Task, TaskList, TechStack, UserStory,
)
from utils.constraints import (
    CodeConstraint, check_code, check_files, extract_constraints,
)


# ---- heuristic extraction from prose --------------------------------------

def _spec(statement, constraints=None, success=("the test passes",)):
    return FeatureSpec(
        spec_id="S1", feature_name="F",
        user_stories=[UserStory(
            priority="P1", title="story",
            why="because it is needed",
            independent_test="call the function and check the value",
            scenarios=[GivenWhenThen(
                given="a valid input value", when="the function is called once",
                then="it returns the documented result")],
        )],
        requirements=[FunctionalRequirement(
            id="FR-001", statement=statement, rfc2119="MUST",
            constraints=constraints or [])],
        success_criteria=list(success),
    )


@pytest.mark.parametrize("statement,banned", [
    ("System MUST evaluate the expression; no eval().", "eval"),
    ("System MUST parse input and must not use eval() anywhere.", "eval"),
    ("System MUST compute the result without using subprocess.", "subprocess"),
    ("System MUST sanitize paths and never call os.system.", "os.system"),
])
def test_heuristic_forbids_from_statement(statement, banned):
    cons = extract_constraints(_spec(statement))
    assert any(c.kind == "forbid" and c.pattern == banned for c in cons), cons


def test_heuristic_from_success_criteria():
    cons = extract_constraints(_spec(
        "System MUST evaluate arithmetic correctly.",
        success=("implemented with no eval()",)))
    assert any(c.kind == "forbid" and c.pattern == "eval" for c in cons)


def test_no_constraints_when_none_declared():
    assert extract_constraints(_spec("System MUST return the sum of two ints.")) == []


def test_explicit_constraint_carried_through():
    cons = extract_constraints(_spec(
        "System MUST build the query safely.",
        constraints=[Constraint(kind="forbid", pattern="os.system", message="shell injection")]))
    c = next(c for c in cons if c.pattern == "os.system")
    assert c.kind == "forbid" and c.source == "FR-001" and "injection" in c.message


def test_explicit_and_heuristic_dedupe():
    cons = extract_constraints(_spec(
        "System MUST evaluate input; no eval().",
        constraints=[Constraint(kind="forbid", pattern="eval")]))
    assert sum(1 for c in cons if c.pattern == "eval" and c.kind == "forbid") == 1


# ---- matching code --------------------------------------------------------

def _forbid(tok, regex=False):
    return [CodeConstraint("forbid", tok, regex=regex)]


def test_forbid_flags_call():
    assert check_code("def f(e):\n    return eval(e)\n", _forbid("eval"))


def test_forbid_clean_passes():
    assert check_code("def f(a, b):\n    return a + b\n", _forbid("eval")) == []


def test_forbid_word_boundary_no_false_positive():
    # `evaluate` and `my_eval` and `ast.literal_eval` must NOT trip a forbid-eval.
    code = "import ast\ndef evaluate(e):\n    return ast.literal_eval(e)\n"
    assert check_code(code, _forbid("eval")) == []


def test_forbid_dotted_token():
    assert check_code("import os\nos.system('ls')\n", _forbid("os.system"))


def test_forbid_ignores_comment_mention():
    # The spec instruction is often echoed in a comment; that's not a use.
    code = "def f(e):\n    # do not use eval here\n    return int(e)\n"
    assert check_code(code, _forbid("eval")) == []


def test_require_missing_flagged_then_satisfied():
    req = [CodeConstraint("require", "async def", message="must be async")]
    assert check_code("def f():\n    pass\n", req)
    assert check_code("async def f():\n    pass\n", req) == []


def test_regex_constraint():
    cons = [CodeConstraint("forbid", r"import\s+requests", regex=True)]
    assert check_code("import requests\n", cons)
    assert check_code("import httpx\n", cons) == []


def test_check_files_reads_disk(tmp_path):
    (tmp_path / "a.py").write_text("def f(e):\n    return eval(e)\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("x = 1\n", encoding="utf-8")
    out = check_files(tmp_path, ["a.py", "b.py"], _forbid("eval"))
    assert "a.py" in out and "b.py" not in out


def test_check_files_empty_constraints_short_circuits(tmp_path):
    assert check_files(tmp_path, ["nope.py"], []) == ""


# ---- end-to-end gate through run_implementation ---------------------------

_GIT = shutil.which("git")


def _build_spec_store(tmp_path, banned_constraint):
    from utils.spec_store import SpecStore

    store = SpecStore(tmp_path / "specs")
    sid = "con-e2e"
    store.save_artifact(sid, "feature_spec", FeatureSpec(
        spec_id=sid, feature_name="adder",
        user_stories=[UserStory(
            priority="P1", title="add two ints",
            why="core behaviour the caller relies on",
            independent_test="call solve('1+1') and expect 2",
            scenarios=[GivenWhenThen(
                given="a string like '1+1'", when="solve is called with it",
                then="it returns the integer sum")],
        )],
        requirements=[FunctionalRequirement(
            id="FR-001", statement="System MUST add the two integers in the input.",
            rfc2119="MUST",
            constraints=[Constraint(kind="forbid", pattern="eval")] if banned_constraint else [])],
        success_criteria=["solve('1+1') returns 2"],
    ))
    store.save_artifact(sid, "plan", ImplementationPlan(
        spec_id=sid, tech_stack=TechStack(language="Python", framework="none"),
        components=[Component(name="solution", responsibility="implement solve()",
                              owns_fr_ids=["FR-001"])],
    ))
    store.save_artifact(sid, "tasks", TaskList(
        spec_id=sid, tasks=[Task(
            id="T001", title="implement solve", files=["solution.py"],
            parallel_safe=True, fr_ids=["FR-001"], failing_test_path="test_solve.py")],
    ))
    store.write_failing_test(sid, "test_solve.py",
                             "from solution import solve\n"
                             "def test_ok():\n    assert solve('1+1') == 2\n")
    return store, sid


def _ti_json(code):
    return json.dumps({"task_id": "T001",
                       "files": [{"path": "solution.py", "content": code}],
                       "test_passed": True, "notes": ""})


def _stub_llm(code):
    def llm(agent_name, system_prompt, user_task, context,
            response_schema=None, schema_name="Response", temperature=None):
        return _ti_json(code), {}
    return llm


def _seq_llm(codes):
    """Returns each code in turn across calls (clamps to the last)."""
    state = {"i": 0}

    def llm(agent_name, system_prompt, user_task, context,
            response_schema=None, schema_name="Response", temperature=None):
        i = min(state["i"], len(codes) - 1)
        state["i"] += 1
        return _ti_json(codes[i]), {}
    return llm


def test_constraints_for_task_scopes_to_owning_frs():
    from utils.constraints import CodeConstraint
    from utils.implement_runner import _constraints_for_task

    task = Task(id="T001", title="impl", files=["a.py"], parallel_safe=True,
                fr_ids=["FR-001"], failing_test_path="t.py")
    cons = [
        CodeConstraint("forbid", "eval", source="FR-001"),       # applies
        CodeConstraint("forbid", "exec", source="FR-002"),       # other FR — excluded
        CodeConstraint("forbid", "os.system", source="success_criteria"),  # spec-wide
    ]
    lines = "\n".join(_constraints_for_task(task, cons))
    assert "`eval`" in lines and "`os.system`" in lines and "`exec`" not in lines


@pytest.mark.skipif(_GIT is None, reason="git not available")
def test_forbidden_means_fails_even_when_test_passes(tmp_path):
    from utils.implement_runner import run_implementation

    store, sid = _build_spec_store(tmp_path, banned_constraint=True)
    project = tmp_path / "project"
    project.mkdir()
    res = run_implementation(
        spec_store=store, spec_id=sid, project_dir=project,
        agent_name="python_backend",
        llm_call=_stub_llm("def solve(e):\n    return eval(e)\n"),
        repair_budget=0,
    )
    o = res.outcomes[0]
    assert o.test_passed is True            # the test really did pass
    assert o.error and "constraint" in o.error.lower()   # ...but it's not a clean pass


def test_declared_constraint_reaches_the_prompt():
    # Under passthrough the loop never runs, so the constraint must be stated in
    # the prompt the host completes — not only enforced after the fact.
    from utils.constraints import CodeConstraint
    from utils.implement_runner import _build_task_prompt

    task = Task(id="T001", title="impl", files=["solution.py"], parallel_safe=True,
                fr_ids=["FR-001"], failing_test_path="t.py")
    spec = _spec("System MUST evaluate the input.")
    plan = ImplementationPlan(
        spec_id="S1", tech_stack=TechStack(language="Python", framework="none"),
        components=[Component(name="c", responsibility="do the thing", owns_fr_ids=["FR-001"])])
    from utils.test_framework_detector import _DEFAULTS
    cons = [CodeConstraint("forbid", "eval", message="injection risk", source="FR-001")]
    prompt = _build_task_prompt(task, spec, plan, "", _DEFAULTS["pytest"], cons)
    assert "Hard constraints" in prompt and "`eval`" in prompt and "injection risk" in prompt


@pytest.mark.skipif(_GIT is None, reason="git not available")
def test_constraint_obeyed_is_clean_pass(tmp_path):
    from utils.implement_runner import run_implementation

    store, sid = _build_spec_store(tmp_path, banned_constraint=True)
    project = tmp_path / "project"
    project.mkdir()
    res = run_implementation(
        spec_store=store, spec_id=sid, project_dir=project,
        agent_name="python_backend",
        llm_call=_stub_llm("def solve(e):\n    a, b = e.split('+')\n    return int(a) + int(b)\n"),
        repair_budget=0,
    )
    o = res.outcomes[0]
    assert o.test_passed is True and o.error is None


@pytest.mark.skipif(_GIT is None, reason="git not available")
def test_repair_loop_recovers_from_constraint_violation(tmp_path):
    # Attempt 0 violates (eval); the feedback drives attempt 1 to a clean fix.
    from utils.implement_runner import run_implementation

    store, sid = _build_spec_store(tmp_path, banned_constraint=True)
    project = tmp_path / "project"
    project.mkdir()
    res = run_implementation(
        spec_store=store, spec_id=sid, project_dir=project,
        agent_name="python_backend",
        llm_call=_seq_llm([
            "def solve(e):\n    return eval(e)\n",                       # violates
            "def solve(e):\n    a, b = e.split('+')\n    return int(a) + int(b)\n",  # clean
        ]),
        repair_budget=1,
    )
    o = res.outcomes[0]
    assert o.error is None and o.test_passed is True
    # The committed result must record a clean pass.
    assert res.trace.commits and all(c.test_passed for c in res.trace.commits)
