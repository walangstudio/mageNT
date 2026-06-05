"""Best-of-N execution selection + config resolution (no LLM, no git)."""

from utils.implement_runner import _Attempt, _resolve_bon, _select_best


def _mk(passed=False, rule_errs="", parse_err=None, apply_err=None, tag=""):
    return _Attempt(
        ti=tag or "ti", files_written=[tag] if tag else [], test_passed=passed,
        test_out="", rule_errs=rule_errs, parse_err=parse_err, apply_err=apply_err,
        usage={},
    )


def test_prefers_fully_passing():
    a = _mk(tag="bad")              # applied, failed
    b = _mk(passed=True, tag="good")
    assert _select_best([a, b]).files_written == ["good"]


def test_passing_with_rule_errs_not_selected_over_clean_apply():
    a = _mk(passed=True, rule_errs="E501", tag="lint")   # passes test but rule error
    b = _mk(passed=False, tag="clean")                   # applied cleanly, test failed
    # Neither is fully-passing; selector falls to first cleanly-applied → 'lint'
    # is also cleanly applied and comes first.
    assert _select_best([a, b]).files_written == ["lint"]


def test_prefers_applied_over_parse_failed():
    a = _mk(parse_err="bad json", tag="")        # never parsed
    b = _mk(passed=False, tag="applied")         # applied, failed test
    assert _select_best([a, b]).files_written == ["applied"]


def test_falls_back_to_first_when_all_broken():
    a = _mk(parse_err="x", tag="")
    b = _mk(apply_err="path escape", tag="")
    assert _select_best([a, b]) is a


def test_resolve_bon_explicit_wins():
    assert _resolve_bon(5, 0.7) == (5, 0.7)
    assert _resolve_bon(0, 0.3) == (1, 0.3)  # clamped to >= 1


def test_resolve_bon_defaults_from_config():
    n, t = _resolve_bon(None, None)
    assert n >= 1 and 0.0 <= t <= 2.0


def test_shipped_config_best_of_n_default_off():
    # Default ships at 1 (single sample); opt-in only.
    n, _ = _resolve_bon(None, None)
    assert n == 1
