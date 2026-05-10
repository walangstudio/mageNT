"""``magent`` CLI — subcommand dispatcher for the validate / generate / eval tools.

Installed via ``pip install -e .`` (pyproject.toml [project.scripts]).
Run ``magent --help`` for available subcommands.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# When run from a checkout (no install), add the repo root to sys.path so
# `agents`, `utils`, `tools`, etc. resolve.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def _cmd_validate(args: argparse.Namespace) -> int:
    from tools.validate_spec import main as validate_main
    return validate_main([args.spec])


def _cmd_generate(args: argparse.Namespace) -> int:
    from tools.generate_dispatch import main as generate_main
    forwarded = []
    if args.target:
        forwarded += ["--target", args.target]
    if args.profile:
        forwarded += ["--profile", args.profile]
    if args.dry_run:
        forwarded.append("--dry-run")
    if args.force:
        forwarded.append("--force")
    return generate_main(forwarded) or 0


def _cmd_eval(args: argparse.Namespace) -> int:
    from tests.prompt_eval.run_matrix import main as eval_main
    forwarded: list = []
    if args.models:
        forwarded += ["--models", *args.models]
    if args.tasks:
        forwarded += ["--tasks", *args.tasks]
    if args.conditions:
        forwarded += ["--conditions", *args.conditions]
    if args.validate_schema:
        forwarded.append("--validate-schema")
    if args.insecure:
        forwarded.append("--insecure")
    if args.out:
        forwarded += ["--out", args.out]
    return eval_main(forwarded)


def _cmd_status(args: argparse.Namespace) -> int:
    """List specs in the workspace + their phase status."""
    import json
    specs_dir = _REPO_ROOT / "specs"
    if not specs_dir.is_dir():
        print("No specs/ directory yet — run magent_constitution first.")
        return 0
    spec_dirs = [d for d in specs_dir.iterdir() if d.is_dir()]
    if not spec_dirs:
        print("specs/ is empty.")
        return 0
    artifacts = [
        ("constitution",         "constitution.json"),
        ("spec",                 "spec.json"),
        ("clarifications",       "clarifications.json"),
        ("plan",                 "plan.json"),
        ("tasks",                "tasks.json"),
        ("trace",                "implementation_trace.json"),
        ("audit",                "audit.json"),
    ]
    for spec_dir in sorted(spec_dirs):
        present = [name for name, fn in artifacts if (spec_dir / fn).exists()]
        cost = (spec_dir / "cost.json")
        cost_summary = ""
        if cost.exists():
            try:
                phases = json.loads(cost.read_text(encoding="utf-8"))
                total_in = sum(
                    sum(int(e.get("input_tokens", 0)) for e in entries)
                    for entries in phases.values()
                )
                total_out = sum(
                    sum(int(e.get("output_tokens", 0)) for e in entries)
                    for entries in phases.values()
                )
                cost_summary = f"  tokens: {total_in}↑ {total_out}↓"
            except Exception:
                pass
        print(f"{spec_dir.name:40s}  {' → '.join(present)}{cost_summary}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="magent",
        description="mageNT command-line interface.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    # validate
    p_val = sub.add_parser("validate", help="Validate a spec lifecycle directory.")
    p_val.add_argument("spec", help="spec_id (resolved under specs/) or explicit path")
    p_val.set_defaults(func=_cmd_validate)

    # generate
    p_gen = sub.add_parser("generate", help="Render subagent + skill markdown from agent classes.")
    p_gen.add_argument("--target", help="Output directory")
    p_gen.add_argument("--profile", choices=["full", "subagents", "skills"])
    p_gen.add_argument("--dry-run", action="store_true")
    p_gen.add_argument("--force", action="store_true")
    p_gen.set_defaults(func=_cmd_generate)

    # eval
    p_eval = sub.add_parser("eval", help="Run the prompt-eval matrix.")
    p_eval.add_argument("--models", nargs="*", default=[])
    p_eval.add_argument("--tasks", nargs="*", default=[])
    p_eval.add_argument("--conditions", nargs="+", default=["new", "baseline"])
    p_eval.add_argument("--validate-schema", action="store_true")
    p_eval.add_argument("--insecure", action="store_true")
    p_eval.add_argument("--out")
    p_eval.set_defaults(func=_cmd_eval)

    # status
    p_status = sub.add_parser("status", help="List specs + per-spec phase status + token usage.")
    p_status.set_defaults(func=_cmd_status)

    args = parser.parse_args(argv)
    return args.func(args) or 0


if __name__ == "__main__":
    raise SystemExit(main())
