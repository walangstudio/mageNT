"""Mechanism tests for the coding eval (no LLM key needed — stub llm_fn)."""

from tests.prompt_eval.coding.run_coding_eval import (
    ALL_CONDITIONS,
    load_tasks,
    run,
    run_condition,
    score,
    strip_fences,
)

GOOD = {
    1: "def fizzbuzz(n):\n"
       "    if n < 1: raise ValueError('n must be >= 1')\n"
       "    if n % 15 == 0: return 'FizzBuzz'\n"
       "    if n % 3 == 0: return 'Fizz'\n"
       "    if n % 5 == 0: return 'Buzz'\n"
       "    return str(n)\n",
}
BAD = "def fizzbuzz(n):\n    return 'nope'\n"


def test_strip_fences():
    assert strip_fences("```python\nx = 1\n```").strip() == "x = 1"
    assert strip_fences("x = 1").strip() == "x = 1"


def test_correct_solution_passes():
    out = run(lambda s, u: GOOD[1], task_ids=[1], conditions=["raw"])
    assert out["summary"]["raw"]["pass@1"] == 1


def test_wrong_solution_fails():
    out = run(lambda s, u: BAD, task_ids=[1], conditions=["raw"])
    assert out["summary"]["raw"]["pass@1"] == 0


def test_repair_loop_flips_fail_to_pass():
    # Stub returns wrong code first, correct code on the retry. Only the loop
    # condition gets a second attempt, so only it should pass.
    calls = {"n": 0}

    def flaky(system, user):
        calls["n"] += 1
        return BAD if calls["n"] == 1 else GOOD[1]

    out = run(flaky, task_ids=[1], conditions=["persona_loop"], repair_budget=2)
    rec = [r for r in out["runs"] if r["condition"] == "persona_loop"][0]
    assert rec["passed"] is True
    assert rec["attempts"] == 2


def test_tasks_load():
    assert len(load_tasks()) >= 3


def test_best_of_n_keeps_first_pass():
    # Three candidates: bad, bad, good. best_of_n should sample until one passes.
    seq = [BAD, BAD, GOOD[1]]
    calls = {"n": 0}

    def stub(system, user):
        i = calls["n"]
        calls["n"] += 1
        return seq[min(i, len(seq) - 1)]

    rec = run_condition(load_tasks([1])[0], "best_of_n", stub, best_of_n=4)
    assert rec["passed"] is True
    assert rec["attempts"] == 3  # stopped at the first passing candidate


def test_best_of_n_opt_in_only():
    # best_of_n is available but NOT in the default condition set, so existing
    # deterministic-stub callers of run() are unaffected.
    from tests.prompt_eval.coding.run_coding_eval import CONDITIONS
    assert "best_of_n" in ALL_CONDITIONS
    assert "best_of_n" not in CONDITIONS


def test_held_out_flags_gaming():
    # Code that satisfies the visible assertion but is wrong in general must be
    # credited on `passed` yet fail `held_out_passed`.
    task = load_tasks([1])[0]
    assert "held_out_test" in task
    # Passes every visible assertion (incl. ValueError on 0) but hard-codes the
    # visible values, so it's wrong on held-out inputs like 30, 9, 20, 7.
    gamed = (
        "def fizzbuzz(n):\n"
        "    if n < 1:\n"
        "        raise ValueError('n must be >= 1')\n"
        "    return {1:'1',3:'Fizz',5:'Buzz',15:'FizzBuzz'}.get(n, 'Fizz')\n"
    )
    visible_pass, _ = score(task, gamed)
    held_pass, _ = score(task, gamed, task["held_out_test"])
    assert visible_pass is True
    assert held_pass is False


def test_all_tasks_have_held_out_and_load():
    tasks = load_tasks()
    assert len(tasks) >= 16
    for t in tasks:
        assert t.get("held_out_test"), f"task {t['id']} missing held_out_test"
        assert t["language"] in ("python", "javascript")
