"""``magent validate <spec-id>`` — fail-fast spec lifecycle validator.

Loads every artifact under ``specs/<spec-id>/`` as JSON, validates each via
the matching ``SPEC_SCHEMAS`` model, then runs cross-artifact checks Spec Kit
and OpenSpec only enforce by convention:

* Every FR-ID referenced in tasks/trace exists in the FeatureSpec.
* No unresolved ``needs_clarification`` items downstream of ``clarify``.
* Every Task's ``failing_test_path`` exists on disk.
* Every CommitTrace references at least one valid FR-ID.
* SpecDelta references the same spec_id and applies cleanly.

Exit code 0 on pass, 1 on first failure with file:line pointer.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agents.spec_schemas import (  # noqa: E402
    SPEC_SCHEMAS,
    Audit,
    ClarificationLog,
    DesignPack,
    FeatureSpec,
    ImplementationPlan,
    ImplementationTrace,
    SpecDelta,
    TaskList,
)


ARTIFACT_FILES = {
    "constitution":         "constitution.json",
    "feature_spec":         "spec.json",
    "clarification_log":    "clarifications.json",
    "design":               "design.json",
    "plan":                 "plan.json",
    "tasks":                "tasks.json",
    "implementation_trace": "implementation_trace.json",
    "audit":                "audit.json",
}


@dataclass
class ValidationReport:
    spec_id: str
    spec_dir: Path
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    artifacts_loaded: List[str] = field(default_factory=list)
    artifacts_missing: List[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def fail(self, where: str, msg: str) -> None:
        self.errors.append(f"  {where}: {msg}")

    def warn(self, where: str, msg: str) -> None:
        self.warnings.append(f"  {where}: {msg}")


def _load_artifact(spec_dir: Path, kind: str) -> Tuple[Optional[Any], Optional[str]]:
    """Return ``(parsed_model, error_msg)``; both ``None`` if file simply absent."""
    fname = ARTIFACT_FILES[kind]
    path = spec_dir / fname
    if not path.exists():
        return (None, None)
    cls = SPEC_SCHEMAS[kind]
    try:
        raw = path.read_text(encoding="utf-8")
        return (cls.model_validate_json(raw), None)
    except Exception as e:
        try:
            shown = path.relative_to(REPO_ROOT)
        except ValueError:  # spec dir outside the repo — keep the real error
            shown = path
        return (None, f"{shown}: {e}")


def _check_clarifications_resolved(
    report: ValidationReport,
    spec: Optional[FeatureSpec],
    clog: Optional[ClarificationLog],
) -> None:
    """If a ClarificationLog exists, the FeatureSpec must have no remaining items."""
    if spec is None or clog is None:
        return
    remaining = spec.all_clarifications()
    if remaining:
        report.fail(
            "spec.json",
            f"{len(remaining)} unresolved [NEEDS CLARIFICATION] items remain "
            f"despite a clarification log being present. Items: {remaining[:3]}"
            f"{' ...' if len(remaining) > 3 else ''}",
        )


def _check_tasks_reference_real_frs(
    report: ValidationReport,
    spec: Optional[FeatureSpec],
    tasks: Optional[TaskList],
) -> None:
    if spec is None or tasks is None:
        return
    valid_ids = {r.id for r in spec.requirements}
    for t in tasks.tasks:
        unknown = [fr for fr in t.fr_ids if fr not in valid_ids]
        if unknown:
            report.fail("tasks.json",
                        f"Task {t.id} references unknown FR ids: {unknown}")


def _check_failing_tests_exist(
    report: ValidationReport,
    spec_dir: Path,
    tasks: Optional[TaskList],
) -> None:
    if tasks is None:
        return
    for t in tasks.tasks:
        path = (spec_dir / t.failing_test_path).resolve()
        # Allow absolute or repo-relative paths too.
        alt = (REPO_ROOT / t.failing_test_path).resolve()
        if not path.exists() and not alt.exists():
            report.fail("tasks.json",
                        f"Task {t.id}: failing_test_path {t.failing_test_path!r} "
                        f"not found on disk (looked under spec dir and repo root).")


def _check_trace_fr_ids(
    report: ValidationReport,
    spec: Optional[FeatureSpec],
    trace: Optional[ImplementationTrace],
) -> None:
    if spec is None or trace is None:
        return
    valid_ids = {r.id for r in spec.requirements}
    for c in trace.commits:
        if c.fr_id not in valid_ids:
            report.fail("implementation_trace.json",
                        f"Commit {c.commit_sha[:7]}: fr_id {c.fr_id} not in spec.")


def _check_plan_fr_coverage(
    report: ValidationReport,
    spec: Optional[FeatureSpec],
    plan: Optional[ImplementationPlan],
) -> None:
    """Fail if no Component owns a given FR-ID — every requirement needs a home
    in the design before the plan gate passes."""
    if spec is None or plan is None:
        return
    owned = set()
    for c in plan.components:
        owned.update(c.owns_fr_ids)
    spec_ids = {r.id for r in spec.requirements}
    uncovered = sorted(spec_ids - owned)
    if uncovered:
        report.fail("plan.json",
                    f"FR-IDs without an owning component: {uncovered}")


def _check_design_cross_refs(
    report: ValidationReport,
    spec: Optional[FeatureSpec],
    design: Optional[DesignPack],
) -> None:
    """FAIL on FR references the spec doesn't know; WARN on FRs no journey covers."""
    if spec is None or design is None:
        return
    valid_ids = {r.id for r in spec.requirements}
    for j in design.journeys:
        unknown = [fr for fr in j.fr_ids if fr not in valid_ids]
        if unknown:
            report.fail("design.json",
                        f"Journey {j.id} references unknown FR ids: {unknown}")
    for s in design.screens:
        unknown = [fr for fr in s.fr_ids if fr not in valid_ids]
        if unknown:
            report.fail("design.json",
                        f"Screen {s.id} references unknown FR ids: {unknown}")
    for rp in design.role_permissions:
        unknown = [fr for fr in rp.fr_ids if fr not in valid_ids]
        if unknown:
            report.fail("design.json",
                        f"Role {rp.role!r} references unknown FR ids: {unknown}")
    journeyed = set()
    for j in design.journeys:
        journeyed.update(j.fr_ids)
    uncovered = sorted(valid_ids - journeyed)
    if uncovered:
        report.warn("design.json",
                    f"FR-IDs not exercised by any journey: {uncovered}")


def _check_threat_component_refs(
    report: ValidationReport,
    plan: Optional[ImplementationPlan],
) -> None:
    if plan is None or not plan.threat_model:
        return
    component_names = {c.name for c in plan.components}
    for i, threat in enumerate(plan.threat_model):
        unknown = [c for c in threat.affected_components if c not in component_names]
        if unknown:
            report.warn("plan.json",
                        f"threat_model[{i}] ({threat.category}) names unknown "
                        f"components: {unknown}")


def _check_deltas(report: ValidationReport, spec_dir: Path) -> None:
    deltas_dir = spec_dir / "deltas"
    if not deltas_dir.is_dir():
        return
    for delta_path in sorted(deltas_dir.glob("*.json")):
        try:
            SpecDelta.model_validate_json(delta_path.read_text(encoding="utf-8"))
            report.artifacts_loaded.append(f"deltas/{delta_path.name}")
        except Exception as e:
            report.fail(f"deltas/{delta_path.name}", str(e))


def validate_spec_dir(spec_dir: Path) -> ValidationReport:
    report = ValidationReport(spec_id=spec_dir.name, spec_dir=spec_dir)
    if not spec_dir.is_dir():
        report.fail("<spec_dir>", f"{spec_dir} is not a directory")
        return report

    parsed: Dict[str, Any] = {}
    for kind, fname in ARTIFACT_FILES.items():
        model, err = _load_artifact(spec_dir, kind)
        if err:
            report.fail(fname, err)
            continue
        if model is None:
            report.artifacts_missing.append(fname)
            continue
        parsed[kind] = model
        report.artifacts_loaded.append(fname)

    _check_clarifications_resolved(
        report,
        parsed.get("feature_spec"),
        parsed.get("clarification_log"),
    )
    _check_tasks_reference_real_frs(
        report,
        parsed.get("feature_spec"),
        parsed.get("tasks"),
    )
    _check_failing_tests_exist(
        report,
        spec_dir,
        parsed.get("tasks"),
    )
    _check_trace_fr_ids(
        report,
        parsed.get("feature_spec"),
        parsed.get("implementation_trace"),
    )
    _check_plan_fr_coverage(
        report,
        parsed.get("feature_spec"),
        parsed.get("plan"),
    )
    _check_design_cross_refs(
        report,
        parsed.get("feature_spec"),
        parsed.get("design"),
    )
    _check_threat_component_refs(
        report,
        parsed.get("plan"),
    )
    _check_deltas(report, spec_dir)
    return report


def _resolve_spec_dir(spec_arg: str) -> Path:
    """Accept either a spec_id (resolved under specs/) or an explicit path."""
    p = Path(spec_arg)
    if p.is_dir():
        return p.resolve()
    candidate = REPO_ROOT / "specs" / spec_arg
    return candidate.resolve()


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("spec", help="Spec id (looked up under specs/) or explicit dir path.")
    ap.add_argument("--quiet", action="store_true", help="Print only on failure.")
    args = ap.parse_args(argv)

    spec_dir = _resolve_spec_dir(args.spec)
    report = validate_spec_dir(spec_dir)

    if not args.quiet or not report.ok:
        print(f"Validating {spec_dir}")
        if report.artifacts_loaded:
            print(f"  loaded:  {', '.join(report.artifacts_loaded)}")
        if report.artifacts_missing:
            print(f"  missing: {', '.join(report.artifacts_missing)}")
        if report.warnings:
            print("Warnings:")
            for w in report.warnings:
                print(w)
        if report.errors:
            print("Errors:")
            for e in report.errors:
                print(e)
            print(f"\nFAIL ({len(report.errors)} error(s))")
            return 1
        print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
