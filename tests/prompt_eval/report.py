"""Render an eval JSON file into a side-by-side markdown table.

Reads ``results/eval-*.json`` produced by ``run_eval.py`` and emits markdown
showing per-task rubric scores per provider.
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
from typing import Any, Dict, List

EVAL_DIR = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(EVAL_DIR, "results")
DIMENSIONS = ["opinionatedness", "scope_discipline", "output_structure", "conciseness", "actionability"]


def _avg(scores: List[float]) -> float:
    return statistics.fmean(scores) if scores else 0.0


def _per_provider(results: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    out: Dict[str, List[Dict[str, Any]]] = {}
    for run in results["runs"]:
        out.setdefault(run["provider"], []).append(run)
    return out


def _row(task_runs: Dict[str, Dict[str, Any]], providers: List[str]) -> str:
    cells: List[str] = []
    for provider in providers:
        run = task_runs.get(provider)
        if not run or run.get("skipped"):
            cells.append("—")
            continue
        per_sample_totals: List[int] = []
        for resp in run.get("responses", []):
            judgment = resp.get("judgment", {})
            if "scores" in judgment:
                per_sample_totals.append(judgment.get("total", 0))
        if per_sample_totals:
            cells.append(f"{_avg(per_sample_totals):.1f}/25")
        elif run.get("dry_run"):
            cells.append("dry-run")
        else:
            cells.append("?")
    return " | ".join(cells)


def render(results_path: str) -> str:
    with open(results_path, "r", encoding="utf-8") as f:
        results = json.load(f)
    providers = list(results.get("providers") or [])
    by_provider = _per_provider(results)

    by_task: Dict[int, Dict[str, Dict[str, Any]]] = {}
    for provider, runs in by_provider.items():
        for run in runs:
            by_task.setdefault(run["task_id"], {})[provider] = run

    lines: List[str] = []
    lines.append(f"# Prompt eval — {results.get('timestamp', '?')}")
    lines.append("")
    lines.append(f"Model: `{results.get('model')}`  Judge: `{results.get('judge_model')}`  Samples: `{results.get('samples')}`")
    lines.append("")

    header = "| Task | Agent | " + " | ".join(providers) + " |"
    sep = "|---" * (2 + len(providers)) + "|"
    lines.append(header)
    lines.append(sep)
    for task_id in sorted(by_task):
        any_run = next(iter(by_task[task_id].values()))
        row_cells = _row(by_task[task_id], providers)
        lines.append(f"| {task_id} | {any_run['agent']} | {row_cells} |")
    lines.append("")

    lines.append("## Per-dimension averages")
    for provider in providers:
        per_dim: Dict[str, List[int]] = {d: [] for d in DIMENSIONS}
        for run in by_provider.get(provider, []):
            for resp in run.get("responses", []):
                for dim in DIMENSIONS:
                    score = resp.get("judgment", {}).get("scores", {}).get(dim, {}).get("score")
                    if isinstance(score, int):
                        per_dim[dim].append(score)
        avgs = ", ".join(f"{d}={_avg(per_dim[d]):.2f}" for d in DIMENSIONS)
        lines.append(f"- **{provider}**: {avgs}")
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("results_file", nargs="?",
                   help="Path to eval-*.json. Defaults to the newest in results/.")
    p.add_argument("--out", help="Write report to this path; otherwise stdout.")
    args = p.parse_args(argv)

    path = args.results_file
    if not path:
        candidates = sorted(
            (os.path.join(RESULTS_DIR, f) for f in os.listdir(RESULTS_DIR) if f.endswith(".json")),
            key=os.path.getmtime,
        )
        if not candidates:
            print("No eval results found in results/", file=sys.stderr)
            return 1
        path = candidates[-1]

    md = render(path)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(md)
        print(f"Wrote {args.out}")
    else:
        print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
