"""``magent_trace`` — deterministic requirement coverage matrix.

Walks the artifacts under ``specs/<spec-id>/`` and answers the traceability
question directly: for every FR, which journeys, screens, components,
endpoints, tasks, tests, and commits cover it — and what gaps remain.
No LLM involved; a pure read over the persisted JSON.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.validate_spec import ARTIFACT_FILES, _load_artifact, _resolve_spec_dir  # noqa: E402


def build_trace_report(spec_dir: Path) -> Dict[str, Any]:
    """Per-FR coverage rows + gap list. Raises ValueError when spec.json is
    absent or unparseable — there is nothing to trace without requirements."""
    spec_dir = Path(spec_dir)
    artifacts: Dict[str, Any] = {}
    for kind in ("feature_spec", "design", "plan", "tasks", "implementation_trace"):
        model, err = _load_artifact(spec_dir, kind)
        if err:
            raise ValueError(f"{ARTIFACT_FILES[kind]}: {err}")
        if model is not None:
            artifacts[kind] = model

    spec = artifacts.get("feature_spec")
    if spec is None:
        raise ValueError(f"spec.json not found under {spec_dir}; nothing to trace.")
    design = artifacts.get("design")
    plan = artifacts.get("plan")
    tasks = artifacts.get("tasks")
    trace = artifacts.get("implementation_trace")

    rows: List[Dict[str, Any]] = []
    gaps: List[str] = []
    # Coverage advice, not broken linkage — mirrors validate_spec severity
    # (backend-only FRs legitimately belong to no journey).
    warnings: List[str] = []
    valid_ids = {r.id for r in spec.requirements}

    for r in spec.requirements:
        row = {
            "fr_id": r.id,
            "rfc2119": r.rfc2119,
            "statement": r.statement,
            "journeys": [], "screens": [], "components": [],
            "endpoints": [], "tasks": [], "tests": [], "commits": [],
        }
        if design is not None:
            row["journeys"] = [j.id for j in design.journeys if r.id in j.fr_ids]
            row["screens"] = [s.id for s in design.screens if r.id in s.fr_ids]
            if not row["journeys"]:
                warnings.append(f"{r.id} appears in no journey")
        if plan is not None:
            row["components"] = [c.name for c in plan.components if r.id in c.owns_fr_ids]
            row["endpoints"] = [f"{e.method} {e.path}" for e in plan.api_contracts
                                if r.id in e.fr_ids]
            if not row["components"]:
                gaps.append(f"{r.id} has no owning component")
        if tasks is not None:
            covering = [t for t in tasks.tasks if r.id in t.fr_ids]
            row["tasks"] = [t.id for t in covering]
            row["tests"] = sorted({t.failing_test_path for t in covering})
            if not covering:
                gaps.append(f"{r.id} has no task")
            if not row["tests"]:
                gaps.append(f"{r.id} has no test")
        if trace is not None:
            row["commits"] = [c.commit_sha[:7] for c in trace.commits if c.fr_id == r.id]
            if not row["commits"]:
                gaps.append(f"{r.id} has no commit")
        rows.append(row)

    if design is not None:
        for s in design.screens:
            if not s.fr_ids:
                warnings.append(f"{s.id} covers no FR")
        for j in design.journeys:
            for fr in j.fr_ids:
                if fr not in valid_ids:
                    gaps.append(f"{j.id} references unknown {fr}")
        for s in design.screens:
            for fr in s.fr_ids:
                if fr not in valid_ids:
                    gaps.append(f"{s.id} references unknown {fr}")
        for rp in design.role_permissions:
            for fr in rp.fr_ids:
                if fr not in valid_ids:
                    gaps.append(f"role {rp.role!r} references unknown {fr}")

    return {
        "ok": not gaps,
        "spec_id": spec.spec_id,
        "gap_count": len(gaps),
        "artifacts_present": sorted(ARTIFACT_FILES[k] for k in artifacts),
        "rows": rows,
        "gaps": gaps,
        "warnings": warnings,
    }


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("spec", help="Spec id (looked up under specs/) or explicit dir path.")
    args = ap.parse_args(argv)

    spec_dir = _resolve_spec_dir(args.spec)
    try:
        report = build_trace_report(spec_dir)
    except ValueError as e:
        print(f"FAIL: {e}")
        return 1
    (spec_dir / "traceability.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
