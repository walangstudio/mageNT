"""Coding eval — does the magent prompt (and the verify->repair loop) actually
produce better CODE than raw Claude, or just add overhead?

Unlike the judge-based prompt eval, this scores objectively: the model emits the
full contents of a solution file, we run the hidden test, and pass@1 is the test
exit code. Three conditions per task:

  raw          — a plain "senior engineer" system prompt (≈ raw Claude).
  persona      — the magent agent's get_system_prompt() (one shot).
  persona_loop — persona + the magent verify->repair loop (re-prompt with the
                 test failure, up to repair_budget retries).

`llm_fn(system, user) -> str` is injected so this runs against any provider (or a
stub in tests). Live numbers need a real provider/key; the mechanism is unit-tested.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import yaml

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

EVAL_DIR = os.path.dirname(os.path.abspath(__file__))
TASKS_PATH = os.path.join(EVAL_DIR, "coding_tasks.yaml")

CONDITIONS = ["raw", "persona", "persona_loop"]

_OUTPUT_RULE = (
    "\n\nOutput ONLY the complete contents of {file} — no prose, no markdown "
    "fences, no explanation. The file must be runnable as-is."
)
_RAW_SYS = "You are a senior software engineer."


def load_tasks(task_ids: Optional[List[int]] = None) -> List[Dict[str, Any]]:
    with open(TASKS_PATH, "r", encoding="utf-8") as f:
        tasks = yaml.safe_load(f)["tasks"]
    if task_ids:
        tasks = [t for t in tasks if t["id"] in task_ids]
    return tasks


def system_prompt(condition: str, agent_name: str, solution_file: str) -> str:
    rule = _OUTPUT_RULE.format(file=solution_file)
    if condition == "raw":
        return _RAW_SYS + rule
    import server  # local import; heavy
    cls = server.AGENT_CLASSES[agent_name]
    return cls({"expertise_level": "senior"}).get_system_prompt() + rule


def strip_fences(text: str) -> str:
    """Pull code out of a ```fenced``` block if the model used one."""
    m = re.search(r"```(?:[\w+-]*)\n(.*?)```", text, re.DOTALL)
    return (m.group(1) if m else text).strip() + "\n"


def score(task: Dict[str, Any], code: str) -> tuple[bool, str]:
    """Write solution + hidden test to a temp dir, run the test, return (passed, output)."""
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        (root / task["solution_file"]).write_text(code, encoding="utf-8")
        (root / task["test_file"]).write_text(task["test"], encoding="utf-8")
        try:
            proc = subprocess.run(
                task["runner"], cwd=str(root), shell=True,
                capture_output=True, text=True, timeout=120,
            )
            return proc.returncode == 0, ((proc.stdout or "") + (proc.stderr or "")).strip()
        except subprocess.TimeoutExpired:
            return False, "runner timed out"


def run_condition(
    task: Dict[str, Any], condition: str, llm_fn: Callable[[str, str], str],
    repair_budget: int = 2,
) -> Dict[str, Any]:
    sys_p = system_prompt(condition, task["agent"], task["solution_file"])
    attempts = (repair_budget + 1) if condition == "persona_loop" else 1
    feedback = ""
    passed, out, used = False, "", 0
    for i in range(attempts):
        used = i + 1
        code = strip_fences(llm_fn(sys_p, task["prompt"] + feedback))
        passed, out = score(task, code)
        if passed:
            break
        feedback = f"\n\nPREVIOUS ATTEMPT FAILED the tests:\n{out[:1500]}\nReturn the COMPLETE corrected file."
    return {"condition": condition, "passed": passed, "attempts": used}


def run(llm_fn: Callable[[str, str], str], task_ids: Optional[List[int]] = None,
        conditions: Optional[List[str]] = None, repair_budget: int = 2) -> Dict[str, Any]:
    conditions = conditions or CONDITIONS
    tasks = load_tasks(task_ids)
    runs = []
    for task in tasks:
        for cond in conditions:
            r = run_condition(task, cond, llm_fn, repair_budget)
            r.update({"task_id": task["id"], "title": task["title"]})
            runs.append(r)
    return {"runs": runs, "summary": _summarize(runs, conditions)}


def _summarize(runs: List[Dict[str, Any]], conditions: List[str]) -> Dict[str, Any]:
    out = {}
    for c in conditions:
        cr = [r for r in runs if r["condition"] == c]
        out[c] = {"pass@1": sum(r["passed"] for r in cr), "n": len(cr)}
    return out


def _anthropic_llm(model: str) -> Callable[[str, str], str]:
    from anthropic import Anthropic
    client = Anthropic()

    def call(system: str, user: str) -> str:
        resp = client.messages.create(
            model=model, max_tokens=2048, system=system,
            messages=[{"role": "user", "content": user}],
        )
        return "".join(b.text for b in resp.content if hasattr(b, "text"))
    return call


def main(argv: Optional[List[str]] = None) -> int:
    import argparse
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--model", default="claude-sonnet-4-6")
    p.add_argument("--tasks", nargs="*", type=int, default=None)
    p.add_argument("--conditions", nargs="+", default=CONDITIONS)
    p.add_argument("--repair-budget", type=int, default=2)
    args = p.parse_args(argv)

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Set ANTHROPIC_API_KEY (or import run() with a custom llm_fn) to run live.")
        return 0
    result = run(_anthropic_llm(args.model), args.tasks, args.conditions, args.repair_budget)
    print("pass@1 by condition:")
    for c, s in result["summary"].items():
        print(f"  {c}: {s['pass@1']}/{s['n']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
