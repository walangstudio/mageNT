"""Repair-feedback excerpting in the implement runner."""

from utils.implement_runner import _excerpt_failure


def test_empty():
    assert _excerpt_failure("") == "(no test output)"


def test_keeps_pytest_assertion_line():
    out = "\n".join([
        "============ test session starts ============",
        "collected 2 items",
        "test_solution.py F",
        "E       assert fizzbuzz(9) == 'Fizz'",
        "E       AssertionError",
        "============ 1 failed, 1 passed in 0.03s ============",
    ])
    ex = _excerpt_failure(out)
    assert "assert fizzbuzz(9)" in ex
    assert "AssertionError" in ex
    # The collection banner is noise; the signal lines are preferred.
    assert "Key lines:" in ex


def test_keeps_node_assert_diff():
    out = "\n".join([
        "node:assert AssertionError [ERR_ASSERTION]:",
        "+ actual - expected",
        "+ [1, 2, 3, 4]",
        "- [1, 2, 3]",
    ])
    ex = _excerpt_failure(out)
    assert "AssertionError" in ex
    assert "actual" in ex


def test_respects_limit():
    out = "Error: x\n" * 5000
    assert len(_excerpt_failure(out, limit=500)) <= 500
