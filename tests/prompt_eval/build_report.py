"""Combine matrix run JSONs into a side-by-side markdown report."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any, Dict, List, Optional

DIMS = ["opinionatedness", "scope_discipline", "output_structure", "conciseness",
        "actionability", "parseability", "template_adherence"]


def load_runs(paths: List[str]) -> List[Dict[str, Any]]:
    runs: List[Dict[str, Any]] = []
    for p in paths:
        data = json.loads(Path(p).read_text(encoding="utf-8"))
        if isinstance(data, dict) and "runs" in data:
            runs.extend(data["runs"])
        elif isinstance(data, list):
            runs.extend(data)
    return runs


def score_of(judgment: Any) -> Dict[str, int]:
    if not isinstance(judgment, dict) or "scores" not in judgment:
        return {d: 0 for d in DIMS} | {"total": 0}
    out = {}
    for d in DIMS:
        s = judgment["scores"].get(d, {})
        out[d] = int(s.get("score", 0)) if isinstance(s, dict) else 0
    out["total"] = int(judgment.get("total", sum(out[d] for d in DIMS)))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--inputs", nargs="+", required=True, help="JSON files to combine")
    ap.add_argument("--out", default="tests/prompt_eval/results/report.md")
    args = ap.parse_args()

    runs = load_runs(args.inputs)
    # Index: (task_id, model, condition) -> scores
    by_key: Dict[tuple, Dict[str, int]] = {}
    parse_by_key: Dict[tuple, Optional[bool]] = {}
    titles: Dict[int, str] = {}
    agents: Dict[int, str] = {}
    for r in runs:
        if r.get("error_gen") or "judgment" not in r:
            continue
        key = (r["task_id"], r["model"], r["condition"])
        by_key[key] = score_of(r["judgment"])
        if "parseable" in r:
            parse_by_key[key] = bool(r["parseable"])
        titles[r["task_id"]] = r.get("title", "")
        agents[r["task_id"]] = r.get("agent", "")

    models = sorted({k[1] for k in by_key.keys()})
    tasks = sorted({k[0] for k in by_key.keys()})

    out = []
    out.append("# mageNT Prompt Eval — Multi-Model Matrix\n")
    out.append(f"Models: {len(models)} · Tasks: {len(tasks)} · Conditions: new (with magent prompts) vs baseline (vanilla senior-engineer system prompt).\n")
    out.append(f"Judge: `mistralai/mistral-large-3-675b-instruct-2512` (NVIDIA NIM). Rubric: 7 dims × 1–5, total /35.\n")
    out.append("")

    # Per-task scoreboard
    for tid in tasks:
        out.append(f"## Task #{tid} — {titles.get(tid,'')}  (agent: `{agents.get(tid,'?')}`)\n")
        out.append("| Model | new total | baseline total | Δ (new−base) | new opin / scope / struct / conc / act | baseline opin / scope / struct / conc / act |")
        out.append("|---|---:|---:|---:|---|---|")
        rows = []
        for m in models:
            n = by_key.get((tid, m, "new"))
            b = by_key.get((tid, m, "baseline"))
            if not n and not b:
                continue
            delta = (n["total"] if n else 0) - (b["total"] if b else 0)
            n_dims = "/".join(str(n[d]) for d in DIMS) if n else "—"
            b_dims = "/".join(str(b[d]) for d in DIMS) if b else "—"
            rows.append((m, n["total"] if n else None, b["total"] if b else None, delta, n_dims, b_dims))
        # sort by Δ desc
        rows.sort(key=lambda r: (-(r[3]), -(r[1] or 0)))
        for m, nt, bt, d, nd, bd in rows:
            sign = f"+{d}" if d > 0 else str(d)
            out.append(f"| `{m}` | {nt if nt is not None else '—'} | {bt if bt is not None else '—'} | **{sign}** | {nd} | {bd} |")
        out.append("")

    # Per-model summary across tasks
    out.append("## Aggregate per model (mean total over tasks)\n")
    out.append("| Model | new mean | baseline mean | Δ |")
    out.append("|---|---:|---:|---:|")
    summary = []
    for m in models:
        ns = [by_key[(t, m, "new")]["total"] for t in tasks if (t, m, "new") in by_key]
        bs = [by_key[(t, m, "baseline")]["total"] for t in tasks if (t, m, "baseline") in by_key]
        if not ns and not bs:
            continue
        nm = round(mean(ns), 2) if ns else None
        bm = round(mean(bs), 2) if bs else None
        d = round((nm or 0) - (bm or 0), 2)
        summary.append((m, nm, bm, d))
    summary.sort(key=lambda r: (-(r[3]), -(r[1] or 0)))
    for m, nm, bm, d in summary:
        sign = f"+{d}" if d > 0 else str(d)
        out.append(f"| `{m}` | {nm if nm is not None else '—'} | {bm if bm is not None else '—'} | **{sign}** |")
    out.append("")

    # Per-dimension delta (mean across all tasks and models)
    out.append("## Per-dimension impact of magent prompts (mean Δ across all model×task pairs)\n")
    out.append("| Dimension | mean baseline | mean new | Δ |")
    out.append("|---|---:|---:|---:|")
    for d in DIMS:
        ns = [by_key[k][d] for k in by_key if k[2] == "new"]
        bs = [by_key[k][d] for k in by_key if k[2] == "baseline"]
        if not ns or not bs:
            continue
        nm, bm = round(mean(ns), 2), round(mean(bs), 2)
        delta = round(nm - bm, 2)
        sign = f"+{delta}" if delta > 0 else str(delta)
        out.append(f"| {d} | {bm} | {nm} | **{sign}** |")
    out.append("")

    # Footer: cells, win rate
    pairs = [(by_key[(t, m, "new")]["total"] - by_key[(t, m, "baseline")]["total"])
             for t in tasks for m in models
             if (t, m, "new") in by_key and (t, m, "baseline") in by_key]
    wins = sum(1 for d in pairs if d > 0)
    losses = sum(1 for d in pairs if d < 0)
    ties = sum(1 for d in pairs if d == 0)
    out.append(f"_Pairwise judge-total comparison ({len(pairs)} model×task cells): magent **wins {wins}**, ties {ties}, loses {losses}._\n")

    # Parseability table — surfaces the structural win the rubric is blind to.
    if parse_by_key:
        out.append("## Parseability (schema validates against Pydantic contract)\n")
        out.append("| Model | new parseable | baseline parseable | Δ |")
        out.append("|---|---|---|---:|")
        rows = []
        for m in models:
            n_total = sum(1 for t in tasks if (t, m, "new") in parse_by_key)
            n_ok = sum(1 for t in tasks if parse_by_key.get((t, m, "new")) is True)
            b_total = sum(1 for t in tasks if (t, m, "baseline") in parse_by_key)
            b_ok = sum(1 for t in tasks if parse_by_key.get((t, m, "baseline")) is True)
            if n_total == 0 and b_total == 0:
                continue
            n_pct = (n_ok / n_total * 100) if n_total else 0
            b_pct = (b_ok / b_total * 100) if b_total else 0
            rows.append((m, n_ok, n_total, n_pct, b_ok, b_total, b_pct, n_pct - b_pct))
        rows.sort(key=lambda r: -r[7])
        for m, no, nt, np_, bo, bt, bp, d in rows:
            sign = f"+{d:.0f}pp" if d > 0 else f"{d:.0f}pp"
            out.append(f"| `{m}` | {no}/{nt} ({np_:.0f}%) | {bo}/{bt} ({bp:.0f}%) | **{sign}** |")
        out.append("")
        # Aggregate
        all_new = [v for k, v in parse_by_key.items() if k[2] == "new"]
        all_base = [v for k, v in parse_by_key.items() if k[2] == "baseline"]
        n_pct = sum(all_new) / len(all_new) * 100 if all_new else 0
        b_pct = sum(all_base) / len(all_base) * 100 if all_base else 0
        out.append(
            f"_Aggregate parseability: magent **{sum(all_new)}/{len(all_new)} = {n_pct:.0f}%** "
            f"vs baseline **{sum(all_base)}/{len(all_base)} = {b_pct:.0f}%** "
            f"(Δ {n_pct - b_pct:+.0f}pp). "
            f"This is the contract win the v1 judge-total comparison was blind to._\n"
        )

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text("\n".join(out), encoding="utf-8")
    print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
