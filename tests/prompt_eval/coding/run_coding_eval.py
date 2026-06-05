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
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import yaml

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

EVAL_DIR = os.path.dirname(os.path.abspath(__file__))
TASKS_PATH = os.path.join(EVAL_DIR, "coding_tasks.yaml")

CONDITIONS = ["raw", "persona", "persona_loop"]
# best_of_n is opt-in (needs a sampling temperature); not in the default set so
# run()'s deterministic-stub callers are unaffected.
ALL_CONDITIONS = CONDITIONS + ["best_of_n"]

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


def score(task: Dict[str, Any], code: str, test_src: Optional[str] = None) -> tuple[bool, str]:
    """Write solution + a test to a temp dir, run it, return (passed, output).

    test_src defaults to the visible `test`; pass task["held_out_test"] to score
    the final code against the never-shown edge cases.
    """
    test_src = task["test"] if test_src is None else test_src
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        (root / task["solution_file"]).write_text(code, encoding="utf-8")
        (root / task["test_file"]).write_text(test_src, encoding="utf-8")
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
    repair_budget: int = 2, best_of_n: int = 4,
) -> Dict[str, Any]:
    sys_p = system_prompt(condition, task["agent"], task["solution_file"])
    passed, out, used, final_code = False, "", 0, ""

    if condition == "best_of_n":
        # Sample N independent candidates (diversity via the provider's
        # temperature), keep the first that passes the visible test.
        for i in range(best_of_n):
            used = i + 1
            final_code = strip_fences(llm_fn(sys_p, task["prompt"]))
            passed, out = score(task, final_code)
            if passed:
                break
    else:
        attempts = (repair_budget + 1) if condition == "persona_loop" else 1
        feedback = ""
        for i in range(attempts):
            used = i + 1
            final_code = strip_fences(llm_fn(sys_p, task["prompt"] + feedback))
            passed, out = score(task, final_code)
            if passed:
                break
            feedback = f"\n\nPREVIOUS ATTEMPT FAILED the tests:\n{out[:1500]}\nReturn the COMPLETE corrected file."

    rec = {"condition": condition, "passed": passed, "attempts": used}
    if task.get("held_out_test"):
        # Robustness / anti-gaming: does the FINAL code also pass edge cases it
        # never saw? Only credit it if the visible test passed too.
        ho_pass, _ = score(task, final_code, task["held_out_test"])
        rec["held_out_passed"] = bool(passed and ho_pass)
    return rec


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


def _anthropic_llm(model: str, temperature: float = 0.0) -> Callable[[str, str], str]:
    from anthropic import Anthropic
    client = Anthropic()

    def call(system: str, user: str) -> str:
        resp = client.messages.create(
            model=model, max_tokens=2048, system=system, temperature=temperature,
            messages=[{"role": "user", "content": user}],
        )
        return "".join(b.text for b in resp.content if hasattr(b, "text"))
    return call


def _nvidia_llm(model: str, temperature: float = 0.0) -> Callable[[str, str], str]:
    """OpenAI-compatible endpoint (NVIDIA NIM by default). truststore handles
    corporate TLS interception. Key from env NVIDIA_API_KEY."""
    import truststore
    truststore.inject_into_ssl()
    from openai import OpenAI

    base = os.environ.get("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
    client = OpenAI(base_url=base, api_key=os.environ["NVIDIA_API_KEY"])

    def call(system: str, user: str) -> str:
        last = None
        for _ in range(3):
            try:
                r = client.chat.completions.create(
                    model=model, temperature=temperature, max_tokens=4096,
                    messages=[{"role": "system", "content": system},
                              {"role": "user", "content": user}],
                )
                m = r.choices[0].message
                return m.content or getattr(m, "reasoning_content", "") or ""
            except Exception as e:  # noqa: BLE001
                last = e
                time.sleep(3)
        raise last
    return call


def make_llm(provider: str, model: str, temperature: float) -> Callable[[str, str], str]:
    if provider == "nvidia":
        return _nvidia_llm(model, temperature)
    if provider == "anthropic":
        return _anthropic_llm(model, temperature)
    raise ValueError(f"unknown provider: {provider}")


def main(argv: Optional[List[str]] = None) -> int:
    import argparse
    import json
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--provider", default="nvidia", choices=["nvidia", "anthropic"])
    p.add_argument("--model", default="meta/llama-3.1-8b-instruct")
    p.add_argument("--tasks", nargs="*", type=int, default=None)
    p.add_argument("--conditions", nargs="+", default=CONDITIONS,
                   help=f"any of {ALL_CONDITIONS}; best_of_n is opt-in (N calls/task)")
    p.add_argument("--trials", type=int, default=3)
    p.add_argument("--repair-budget", type=int, default=3)
    p.add_argument("--best-of-n", type=int, default=4)
    p.add_argument("--temperature", type=float, default=0.0,
                   help="code-gen temperature for raw/persona/persona_loop")
    p.add_argument("--bon-temperature", type=float, default=0.4,
                   help="sampling temperature for the best_of_n condition")
    p.add_argument("--out", default=None)
    args = p.parse_args(argv)

    key = {"nvidia": "NVIDIA_API_KEY", "anthropic": "ANTHROPIC_API_KEY"}[args.provider]
    if not os.environ.get(key):
        print(f"Set {key} to run live (or import run() with a custom llm_fn).")
        return 0

    tasks = load_tasks(args.tasks)
    llm_cold = make_llm(args.provider, args.model, args.temperature)
    llm_hot = (make_llm(args.provider, args.model, args.bon_temperature)
               if "best_of_n" in args.conditions else llm_cold)

    runs = []
    for trial in range(args.trials):
        for task in tasks:
            for cond in args.conditions:
                t0 = time.time()
                llm = llm_hot if cond == "best_of_n" else llm_cold
                r = run_condition(task, cond, llm, args.repair_budget, args.best_of_n)
                r.update({"trial": trial, "task_id": task["id"], "title": task["title"],
                          "difficulty": task.get("difficulty", "?"),
                          "language": task.get("language", "?"),
                          "secs": round(time.time() - t0, 1)})
                runs.append(r)
                ho = r.get("held_out_passed")
                ho_s = "" if ho is None else f" held_out={ho!s:<5}"
                print(f"  t{trial} #{r['task_id']:<2} {r['title'][:22]:<22} {cond:<13} "
                      f"pass={r['passed']!s:<5} att={r['attempts']}{ho_s} ({r['secs']}s)",
                      flush=True)

    print(f"\nmodel: {args.model}   provider: {args.provider}   "
          f"trials: {args.trials}   tasks: {len(tasks)}")
    print("pass-rate by condition (visible test):")
    summary = {}
    for c in args.conditions:
        cr = [r for r in runs if r["condition"] == c]
        vis = sum(r["passed"] for r in cr)
        hocr = [r for r in cr if "held_out_passed" in r]
        ho = sum(r["held_out_passed"] for r in hocr)
        summary[c] = {"visible": vis, "n": len(cr),
                      "held_out": ho, "held_out_n": len(hocr)}
        ho_s = f"   held-out {ho}/{len(hocr)}" if hocr else ""
        print(f"  {c:<13} {vis}/{len(cr)} ({100*vis//max(len(cr),1)}%){ho_s}")

    print("\nper-task pass-rate (visible, passes across trials):")
    hdr = "  {:<24} {:<8} {:<4}".format("task", "lang", "diff")
    for c in args.conditions:
        hdr += f" {c[:11]:>11}"
    print(hdr)
    for task in tasks:
        row = "  {:<24} {:<8} {:<4}".format(
            task["title"][:24], task.get("language", "?")[:8], task.get("difficulty", "?")[:4])
        for c in args.conditions:
            tr = [r for r in runs if r["task_id"] == task["id"] and r["condition"] == c]
            row += f" {sum(x['passed'] for x in tr):>5}/{len(tr):<5}"
        print(row)

    out = args.out
    if out:
        with open(out, "w", encoding="utf-8") as f:
            json.dump({"model": args.model, "provider": args.provider,
                       "trials": args.trials, "summary": summary, "runs": runs},
                      f, indent=2)
        print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
