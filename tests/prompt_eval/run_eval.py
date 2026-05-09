"""Prompt evaluation harness.

Loads ``tasks.yaml`` and one or more providers (current, new, ecc), renders
the system+user prompt for each task, and (optionally) calls the Anthropic
API to produce a response and a judge score.

This module is design-complete but can run in three modes:

* ``--dry-run``      — no API calls; prints what would be sent.
* ``--samples N``    — calls the model N times per (task, provider).
* default ``N=0``    — same as ``--dry-run``.

Set ``ANTHROPIC_API_KEY`` to actually run.
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import yaml

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

EVAL_DIR = os.path.dirname(os.path.abspath(__file__))
TASKS_PATH = os.path.join(EVAL_DIR, "tasks.yaml")
RUBRIC_PATH = os.path.join(EVAL_DIR, "rubric.yaml")
JUDGE_PROMPT_PATH = os.path.join(EVAL_DIR, "judge_prompt.txt")
RESULTS_DIR = os.path.join(EVAL_DIR, "results")


def _load_yaml(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _load_provider(name: str):
    return importlib.import_module(f"tests.prompt_eval.providers.{name}")


def _render_user_prompt(task: Dict[str, Any]) -> str:
    parts = [task["prompt"].rstrip()]
    if task.get("code"):
        parts += ["", "```", task["code"].rstrip(), "```"]
    return "\n".join(parts)


def _call_anthropic(system: str, user: str, model: str) -> str:
    try:
        from anthropic import Anthropic
    except ImportError as exc:
        raise RuntimeError(
            "Install the anthropic package to run the harness: pip install anthropic"
        ) from exc
    client = Anthropic()
    resp = client.messages.create(
        model=model,
        max_tokens=2048,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return "".join(block.text for block in resp.content if hasattr(block, "text"))


def _judge(response: str, task: Dict[str, Any], judge_model: str) -> Dict[str, Any]:
    with open(JUDGE_PROMPT_PATH, "r", encoding="utf-8") as f:
        judge_system = f.read()
    user = (
        f"Task id: {task['id']}\n"
        f"Agent: {task['agent']}\n"
        f"Title: {task['title']}\n\n"
        f"=== Response under evaluation ===\n{response}\n=== end response ==="
    )
    raw = _call_anthropic(judge_system, user, judge_model)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"error": "judge_returned_non_json", "raw": raw}


def run(
    providers: List[str],
    tasks: Optional[List[int]],
    samples: int,
    model: str,
    judge_model: str,
    dry_run: bool,
) -> Dict[str, Any]:
    tasks_data = _load_yaml(TASKS_PATH)["tasks"]
    if tasks:
        tasks_data = [t for t in tasks_data if t["id"] in tasks]

    results: Dict[str, Any] = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "model": model,
        "judge_model": judge_model,
        "samples": samples,
        "providers": providers,
        "runs": [],
    }

    for task in tasks_data:
        user_prompt = _render_user_prompt(task)
        for provider_name in providers:
            provider = _load_provider(provider_name)
            try:
                system, user = provider.render(task["agent"], user_prompt)
            except (KeyError, FileNotFoundError) as exc:
                results["runs"].append({
                    "task_id": task["id"],
                    "agent": task["agent"],
                    "provider": provider_name,
                    "skipped": str(exc),
                })
                continue

            entry = {
                "task_id": task["id"],
                "agent": task["agent"],
                "title": task["title"],
                "provider": provider_name,
                "system_chars": len(system),
                "user_chars": len(user),
                "responses": [],
            }

            if dry_run or samples <= 0:
                entry["dry_run"] = True
                entry["system_preview"] = system[:400]
                results["runs"].append(entry)
                continue

            for _ in range(samples):
                response = _call_anthropic(system, user, model)
                judgment = _judge(response, task, judge_model)
                entry["responses"].append({"response": response, "judgment": judgment})
            results["runs"].append(entry)

    return results


def _save_report(results: Dict[str, Any]) -> str:
    os.makedirs(RESULTS_DIR, exist_ok=True)
    ts = results["timestamp"].replace(":", "").replace("-", "")
    path = os.path.join(RESULTS_DIR, f"eval-{ts}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    return path


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--providers", nargs="+", default=["new"],
                   help="Providers to compare (current, new, ecc).")
    p.add_argument("--tasks", nargs="*", type=int, default=None,
                   help="Task IDs to run; default is all.")
    p.add_argument("--samples", type=int, default=0,
                   help="Samples per (task, provider). 0 = dry-run.")
    p.add_argument("--model", default="claude-sonnet-4-6")
    p.add_argument("--judge-model", default="claude-sonnet-4-6")
    p.add_argument("--dry-run", action="store_true",
                   help="Force dry-run regardless of samples.")
    args = p.parse_args(argv)

    results = run(
        providers=args.providers,
        tasks=args.tasks,
        samples=args.samples,
        model=args.model,
        judge_model=args.judge_model,
        dry_run=args.dry_run,
    )

    if results["samples"] > 0 and not args.dry_run:
        path = _save_report(results)
        print(f"Wrote results to {path}")
    else:
        for run_entry in results["runs"]:
            tag = run_entry.get("skipped") or (
                f"system={run_entry['system_chars']}c user={run_entry['user_chars']}c"
            )
            print(
                f"task#{run_entry['task_id']} agent={run_entry['agent']} "
                f"provider={run_entry['provider']}: {tag}"
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
