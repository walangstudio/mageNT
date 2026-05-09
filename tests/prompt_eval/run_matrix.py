"""Multi-model, multi-condition prompt eval matrix.

Runs N models x {magent, baseline} x M tasks via an OpenAI-compatible endpoint
(NVIDIA NIM, OpenRouter, etc.) and judges each response with a single judge
model. Externally-collected responses (e.g. from Claude via the Agent tool)
can be judged via --judge-from <json>.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import certifi
import httpx
import openai
import yaml

EVAL_DIR = Path(__file__).parent.resolve()
REPO = EVAL_DIR.parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import server  # type: ignore  # noqa: E402
from tests.prompt_eval.parseability import validate as validate_schema  # type: ignore  # noqa: E402

BASELINE_SYSTEM = (
    "You are a senior software engineer. Answer the user directly and concretely. "
    "Use Markdown if it helps. Do not preface with disclaimers."
)


def magent_system(agent_name: str) -> str:
    cls = server.AGENT_CLASSES[agent_name]
    spec = (cls.__doc__ or "").strip().splitlines()[0] if cls.__doc__ else ""
    a = cls({"expertise_level": "principal", "specialization": spec})
    return a.get_system_prompt()


def render_user(task: Dict[str, Any]) -> str:
    parts = [task["prompt"].rstrip()]
    if task.get("code"):
        parts += ["", "```", task["code"].rstrip(), "```"]
    return "\n".join(parts)


def make_client(base_url: str, api_key: str, insecure: bool) -> openai.OpenAI:
    http = httpx.Client(verify=not insecure, timeout=180.0)
    return openai.OpenAI(base_url=base_url, api_key=api_key, http_client=http)


def call_model(client: openai.OpenAI, model: str, system: str, user: str,
               max_tokens: int = 2048) -> str:
    resp = client.chat.completions.create(
        model=model,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return resp.choices[0].message.content or ""


def parse_judge_json(raw: str) -> Dict[str, Any]:
    raw = (raw or "").strip()
    if raw.startswith("```"):
        # strip code fence
        body = raw.split("```", 2)
        if len(body) >= 2:
            raw = body[1]
            if raw.lower().startswith("json"):
                raw = raw[4:].lstrip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        s = raw.find("{")
        e = raw.rfind("}")
        if 0 <= s < e:
            try:
                return json.loads(raw[s:e + 1])
            except json.JSONDecodeError:
                pass
    return {"error": "non_json", "raw": raw[:600]}


def judge_one(client: openai.OpenAI, judge_model: str, judge_system: str,
              task_meta: Dict[str, Any], response: str) -> Dict[str, Any]:
    user = (
        f"Task id: {task_meta['id']}\n"
        f"Agent: {task_meta['agent']}\n"
        f"Title: {task_meta.get('title','')}\n\n"
        f"=== Response under evaluation ===\n{response}\n=== end response ==="
    )
    raw = call_model(client, judge_model, judge_system, user, max_tokens=1200)
    return parse_judge_json(raw)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default=os.environ.get("OPENAI_BASE_URL"))
    ap.add_argument("--api-key", default=os.environ.get("NVIDIA_API_KEY")
                    or os.environ.get("OPENAI_API_KEY"))
    ap.add_argument("--insecure", action="store_true",
                    help="Disable TLS verify (Avast/proxy MITM environments).")
    ap.add_argument("--judge-model", default="mistralai/mistral-large-3-675b-instruct-2512")
    ap.add_argument("--models", nargs="*", default=[],
                    help="Model IDs to run. Empty = skip generation, only judge --judge-from.")
    ap.add_argument("--tasks", nargs="*", type=int, default=[1, 3, 7])
    ap.add_argument("--conditions", nargs="+", default=["new", "baseline"])
    ap.add_argument("--out", default=None)
    ap.add_argument("--inputs-only", action="store_true",
                    help="Print prepared cells (system+user) as JSON and exit; do not call any API.")
    ap.add_argument("--judge-from", default=None,
                    help="Path to JSON list of pre-collected responses to judge.")
    ap.add_argument("--max-tokens", type=int, default=2048)
    ap.add_argument("--validate-schema", action="store_true",
                    help="Validate every response against the agent's Pydantic schema; "
                         "record `parseable` and `validation_error` per cell.")
    args = ap.parse_args()

    if not args.base_url or not args.api_key:
        print("ERROR: set --base-url and --api-key (or OPENAI_BASE_URL + NVIDIA_API_KEY env vars).",
              file=sys.stderr)
        return 2

    tasks_data = yaml.safe_load((EVAL_DIR / "tasks.yaml").read_text(encoding="utf-8"))["tasks"]
    chosen = [t for t in tasks_data if t["id"] in args.tasks]
    judge_system = (EVAL_DIR / "judge_prompt.txt").read_text(encoding="utf-8")

    cells: List[Dict[str, Any]] = []
    for t in chosen:
        user = render_user(t)
        for cond in args.conditions:
            sys_p = magent_system(t["agent"]) if cond == "new" else BASELINE_SYSTEM
            for m in args.models:
                cells.append({
                    "task_id": t["id"], "agent": t["agent"], "title": t["title"],
                    "model": m, "condition": cond,
                    "system": sys_p, "user": user,
                })

    if args.inputs_only:
        print(json.dumps(cells, indent=2))
        return 0

    client = make_client(args.base_url, args.api_key, args.insecure)
    runs: List[Dict[str, Any]] = []

    for i, c in enumerate(cells, 1):
        tag = f"[{i}/{len(cells)}] {c['model']} cond={c['condition']} task={c['task_id']}"
        t0 = time.time()
        try:
            resp = call_model(client, c["model"], c["system"], c["user"], args.max_tokens)
        except Exception as e:
            print(f"{tag} GEN ERROR: {e}", flush=True)
            runs.append({k: c[k] for k in ("task_id", "agent", "title", "model", "condition")}
                        | {"error_gen": str(e)})
            continue
        gen_dt = time.time() - t0
        try:
            judgment = judge_one(client, args.judge_model, judge_system,
                                 {"id": c["task_id"], "agent": c["agent"], "title": c["title"]},
                                 resp)
        except Exception as e:
            judgment = {"error": f"judge: {e}"}
        cell_record = {
            "task_id": c["task_id"], "agent": c["agent"], "title": c["title"],
            "model": c["model"], "condition": c["condition"],
            "system_chars": len(c["system"]),
            "response": resp, "judgment": judgment, "gen_seconds": round(gen_dt, 2),
        }
        if args.validate_schema:
            ok, err, _ = validate_schema(c["agent"], resp)
            cell_record["parseable"] = ok
            cell_record["validation_error"] = err
        runs.append(cell_record)
        score = (judgment.get("total") if isinstance(judgment, dict) else None) or "?"
        parse_tag = ""
        if args.validate_schema:
            parse_tag = f" parse={'OK' if cell_record['parseable'] else 'FAIL'}"
        print(f"{tag} -> {gen_dt:.1f}s, judge total={score}{parse_tag}", flush=True)

    # Judge externally-collected responses (e.g. from Claude Agent)
    if args.judge_from:
        ext_list = json.loads(Path(args.judge_from).read_text(encoding="utf-8"))
        for j, ext in enumerate(ext_list, 1):
            try:
                judgment = judge_one(client, args.judge_model, judge_system,
                                     {"id": ext["task_id"], "agent": ext["agent"],
                                      "title": ext.get("title", "")},
                                     ext["response"])
            except Exception as e:
                judgment = {"error": f"judge: {e}"}
            cell = {**ext, "judgment": judgment}
            if args.validate_schema:
                ok, err, _ = validate_schema(ext["agent"], ext["response"])
                cell["parseable"] = ok
                cell["validation_error"] = err
            runs.append(cell)
            parse_tag = ""
            if args.validate_schema:
                parse_tag = f" parse={'OK' if cell['parseable'] else 'FAIL'}"
            print(f"[ext {j}/{len(ext_list)}] {ext['model']} cond={ext['condition']} "
                  f"task={ext['task_id']} -> total={judgment.get('total','?')}{parse_tag}", flush=True)

    out_path = args.out or str(EVAL_DIR / "results"
                               / f"matrix-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json")
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(json.dumps({"runs": runs}, indent=2), encoding="utf-8")
    print(f"\nWrote {out_path}  ({len(runs)} runs)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
