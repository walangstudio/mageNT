"""Mechanism tests for the coding eval (no LLM key needed — stub llm_fn)."""

from tests.prompt_eval.coding.run_coding_eval import run, strip_fences, load_tasks

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
