"""Per-task implementation driver — turns a TaskList into real code + git commits.

For each ``Task``:

1. Write ``specs/<spec_id>/.active_task`` so the FR-ID PRE_COMMIT hook sees it.
2. Build a focused user prompt: the task spec + the relevant FRs + the plan
   excerpt + the failing test source.
3. Dispatch the agent (default: ``fullstack_developer``) with the
   ``TaskImplementation`` schema as the response contract.
4. Apply the agent's ``files: List[FileWrite]`` to the project root.
5. Run the auto-detected test framework against ``failing_test_path``;
   capture exit code as ``test_passed``.
6. ``git add`` the touched files + the test file, ``git commit`` with the
   task title (PRE_COMMIT hook prepends ``[FR-XXX] `` automatically).
7. Capture ``CommitTrace`` (fr_id × task_id × commit_sha × files × test_passed).

After all tasks: assemble ``ImplementationTrace``, persist via spec_store.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

try:
    from agents.spec_schemas import (
        CommitTrace, FeatureSpec, ImplementationPlan, ImplementationTrace,
        Task, TaskImplementation, TaskList,
    )
except ImportError:  # pragma: no cover
    from ..agents.spec_schemas import (  # type: ignore
        CommitTrace, FeatureSpec, ImplementationPlan, ImplementationTrace,
        Task, TaskImplementation, TaskList,
    )

try:
    from utils.test_framework_detector import detect, TestFramework
except ImportError:  # pragma: no cover
    from .test_framework_detector import detect, TestFramework  # type: ignore

try:
    from utils.spec_store import SpecStore
except ImportError:  # pragma: no cover
    from .spec_store import SpecStore  # type: ignore

try:
    from utils.spec_pipeline import _default_llm_call, _extract_and_validate
except ImportError:  # pragma: no cover
    from .spec_pipeline import _default_llm_call, _extract_and_validate  # type: ignore


@dataclass
class TaskOutcome:
    task_id: str
    fr_ids: List[str]
    files_written: List[str]
    test_passed: bool
    commit_sha: Optional[str]
    error: Optional[str] = None


@dataclass
class ImplementRunResult:
    spec_id: str
    workspace: Path
    outcomes: List[TaskOutcome]
    trace: ImplementationTrace


def _git(workspace: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    """Run a git command in the workspace. Returns the completed process."""
    return subprocess.run(
        ["git", *args],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=check,
    )


def _ensure_git_repo(workspace: Path) -> None:
    """Init the workspace as a git repo if not already one."""
    workspace.mkdir(parents=True, exist_ok=True)
    if (workspace / ".git").is_dir():
        return
    _git(workspace, "init", "-q")
    # Default identity so commits work on a fresh sandbox without ~/.gitconfig.
    try:
        _git(workspace, "config", "user.email", "magent@local")
        _git(workspace, "config", "user.name", "magent")
    except subprocess.CalledProcessError:
        pass


def _write_active_task(spec_dir: Path, task_id: str) -> None:
    (spec_dir / ".active_task").write_text(task_id, encoding="utf-8")


def _clear_active_task(spec_dir: Path) -> None:
    p = spec_dir / ".active_task"
    if p.exists():
        p.unlink()


def _repair_jsonish(text: str) -> Optional[str]:
    """Try to repair common LLM JSON corruption: bare newlines / tabs inside
    double-quoted strings. Conservative — only escapes raw control chars when
    we're confident we're inside a string literal.
    """
    if not text:
        return None
    out = []
    in_str = False
    escape = False
    for ch in text:
        if in_str:
            if escape:
                out.append(ch); escape = False
                continue
            if ch == "\\":
                out.append(ch); escape = True
                continue
            if ch == '"':
                in_str = False
                out.append(ch); continue
            if ch == "\n":
                out.append("\\n"); continue
            if ch == "\r":
                out.append("\\r"); continue
            if ch == "\t":
                out.append("\\t"); continue
            out.append(ch)
        else:
            if ch == '"':
                in_str = True
            out.append(ch)
    return "".join(out)


# NOTE: deliberately a schema-shape example, NOT example code. Smaller models
# (~20B) tend to verbatim-copy whatever code appears in the example; we want
# them to invent code that satisfies the failing test, not parrot stubs.
_EXAMPLE_TASK_IMPL_SHAPE = '''{
  "task_id": "<T###>",
  "files": [
    {"path": "<relative/file/path.ext>", "content": "<full file source as a single string>"},
    {"path": "<another/file.ext>",       "content": "<full file source as a single string>"}
  ],
  "test_passed": <true | false>,
  "notes": "<optional notes>"
}'''


def _build_task_prompt(
    task: Task,
    spec: FeatureSpec,
    plan: ImplementationPlan,
    failing_test_source: str,
    framework: TestFramework,
) -> str:
    """Build the user message for a single task.

    Tight prompt — designed to fit within mid-size local model context budgets
    (gpt-oss-20b, qwen-14b, llama-8b). The full failing test source is NOT
    included — the agent only sees the test PATH + the FR statements, and
    must implement code that satisfies the FRs. This trades some test-aware
    optimization for a much smaller prompt that local models can actually
    process. Frontier models (Claude, GPT-OSS-120b) get the same prompt
    and produce equivalent code without the test-source crutch.
    """
    relevant_frs = [r for r in spec.requirements if r.id in task.fr_ids]
    return (
        f"Task {task.id}: {task.title}\n"
        f"Files: {task.files}\n"
        f"FR(s) to satisfy:\n"
        + "\n".join(f"  - {r.id} ({r.rfc2119}): {r.statement}" for r in relevant_frs)
        + f"\n\nLanguage: {plan.tech_stack.language}\n"
        + f"Test runner: {framework.runner_command.format(path=task.failing_test_path)}\n"
        + f"\nOutput ONE JSON object matching this shape (replace <placeholders>):\n"
        + f"{_EXAMPLE_TASK_IMPL_SHAPE}\n"
        + f"\nRules: task_id=\"{task.id}\". files is a LIST of "
        + "{path, content} (NOT a dict). content is FULL working code, not stubs. "
        + "test_passed is a bool. JSON only — no fences."
    )


def _coerce_task_implementation(raw_text: str, task_id: str) -> Tuple[Optional[TaskImplementation], Optional[str]]:
    """Tolerant parser. Handles three common model output shapes:

    1. The canonical TaskImplementation shape (preferred).
    2. ``{"TaskImplementation": {...}}`` — wrapped in a top-level key.
    3. ``{"src/store.py": "<content>", "src/cli.py": "<content>", ...}`` — a dict
       mapping path→content with no other fields. Coerced to FileWrite list.
    """
    from agents.spec_schemas import FileWrite as _FileWrite
    try:
        from tests.prompt_eval.parseability import _extract_json
        blob = _extract_json(raw_text) or raw_text
    except ImportError:
        blob = raw_text
    if not blob:
        return None, "no JSON found in response"
    import json as _json
    # Mid-size local models often emit literal newlines inside `content`
    # strings instead of escaping them. ``strict=False`` accepts those control
    # characters and is the right call for code-payload JSON.
    data = None
    last_err = None
    try:
        data = _json.loads(blob, strict=False)
    except _json.JSONDecodeError as e:
        last_err = str(e)
        # Repair pass 1: escape bare newlines inside double-quoted strings.
        repaired = _repair_jsonish(blob)
        if repaired is not None:
            try:
                data = _json.loads(repaired, strict=False)
            except _json.JSONDecodeError as e2:
                last_err = str(e2)
        # Repair pass 2: ast.literal_eval (handles Python-dict notation —
        # single quotes, unquoted keys when paired with Python-syntax values).
        if data is None:
            try:
                import ast as _ast
                data = _ast.literal_eval(blob)
            except (ValueError, SyntaxError) as e3:
                pass
        if data is None:
            return None, f"invalid JSON: {last_err}"
    # Unwrap if top-level is a single key like "TaskImplementation".
    if isinstance(data, dict) and len(data) == 1:
        only = next(iter(data.values()))
        if isinstance(only, dict) and ("files" in only or "task_id" in only):
            data = only
    if not isinstance(data, dict):
        return None, "JSON root is not an object"
    # Path→content dict shape: every value is a string.
    is_path_dict = (
        "files" not in data
        and data
        and all(isinstance(k, str) and isinstance(v, str) for k, v in data.items())
    )
    if is_path_dict:
        coerced = {
            "task_id": task_id,
            "files": [{"path": k, "content": v} for k, v in data.items()],
            "test_passed": False,
            "notes": "(path→content dict coerced)",
        }
        try:
            return TaskImplementation.model_validate(coerced), None
        except Exception as e:
            return None, f"path-dict coerce failed: {e}"
    # Path-list-of-dicts shape: try as-is.
    try:
        return TaskImplementation.model_validate(data), None
    except Exception as e:
        return None, str(e)[:400]


def _apply_files(workspace: Path, files: List[Any]) -> List[str]:
    """Write every FileWrite to the workspace. Returns relative paths written."""
    written: List[str] = []
    for fw in files:
        rel = fw.path.lstrip("/").replace("\\", "/")
        # Refuse path-traversal escapes and absolute paths.
        target = (workspace / rel).resolve()
        if not str(target).startswith(str(workspace.resolve())):
            raise ValueError(f"refusing path-traversal write to {fw.path!r}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(fw.content, encoding="utf-8")
        written.append(rel)
    return written


def _run_test_verbose(framework: TestFramework, workspace: Path, test_path: str) -> Tuple[bool, str]:
    """Run the framework's runner against one test file. Returns (passed, output)."""
    if framework.name == "unknown":
        return False, "no test framework detected"
    cmd_str = framework.runner_command.format(path=test_path)
    try:
        proc = subprocess.run(
            cmd_str, cwd=workspace, shell=True,
            capture_output=True, text=True, timeout=120,
        )
        return proc.returncode == 0, ((proc.stdout or "") + (proc.stderr or "")).strip()
    except subprocess.TimeoutExpired:
        return False, "test run timed out after 120s"
    except Exception as exc:  # noqa: BLE001
        return False, f"test run error: {exc}"


def _run_test(framework: TestFramework, workspace: Path, test_path: str) -> bool:
    """Run the framework's runner against a single test file. Returns True on exit 0."""
    return _run_test_verbose(framework, workspace, test_path)[0]


_FAIL_MARKERS = (
    "Error", "Exception", "assert", "AssertionError", "FAILED", "Traceback",
    "E   ", "expected", "actual", "!=", "Expected", "Received",
)


def _excerpt_failure(output: str, limit: int = 2000) -> str:
    """Pull the signal out of a test runner's output for repair feedback.

    A raw 2500-char truncation often clips the assertion and keeps pytest's
    collection banner. This keeps the lines that carry the diagnosis (assertion
    / exception / expected-vs-actual) plus the tail, which is what the model
    needs to fix the code.
    """
    if not output:
        return "(no test output)"
    lines = output.splitlines()
    keep, seen = [], set()
    for ln in lines:
        s = ln.strip()
        if s and s not in seen and any(m in ln for m in _FAIL_MARKERS):
            keep.append(ln.rstrip())
            seen.add(s)
    parts = []
    if keep:
        parts.append("Key lines:\n" + "\n".join(keep[:25]))
    tail = [ln.rstrip() for ln in lines[-12:] if ln.strip()]
    if tail:
        parts.append("Tail:\n" + "\n".join(tail))
    text = "\n\n".join(parts) or output
    return text[:limit]


def _rules_errors(project_dir: Path, files_written: List[str]) -> str:
    """ERROR-level rule violations on the written files (release profile).

    Returns a diagnostics string for repair feedback, or "" when clean or the
    rules engine is unavailable (never blocks on its own absence).
    """
    try:
        from rules import RulesEngine, RulesConfig
    except Exception:  # noqa: BLE001
        return ""
    engine = RulesEngine(RulesConfig(fail_on_warnings=False))
    lines = []
    for rel in files_written:
        fp = (project_dir / rel).resolve()
        try:
            report = engine.check_code(fp.read_text(encoding="utf-8"), rel)
        except OSError:
            continue
        for r in report.results:
            for v in r.violations:
                if getattr(v.severity, "value", "") == "error":
                    lines.append(f"{rel}: [{v.rule_name}] {v.message}")
    return "\n".join(lines)


def _commit(workspace: Path, files: List[str], task_title: str,
              fr_ids: List[str]) -> Optional[str]:
    """Stage + commit. Returns commit SHA or None if commit failed (e.g. nothing to commit)."""
    try:
        _git(workspace, "add", *files)
        # Empty-commit guard: skip if nothing staged.
        status = _git(workspace, "status", "--porcelain", check=False)
        if not status.stdout.strip():
            return None
        prefix = f"[{', '.join(fr_ids)}] " if fr_ids else ""
        msg = f"{prefix}{task_title}"
        _git(workspace, "commit", "-m", msg)
        sha = _git(workspace, "rev-parse", "HEAD").stdout.strip()
        return sha
    except subprocess.CalledProcessError as e:
        return None


def _ordered_tasks(run_tasks: List[Task]) -> List[Task]:
    """Order tasks so every task runs after its `depends_on` (Kahn's algorithm).

    Only deps that are themselves in `run_tasks` constrain ordering — deps
    outside the set (done in a prior run, or deliberately excluded via
    task_ids) are ignored. Stable: ties keep the original task order. Raises on
    a dependency cycle (the schema validates deps exist but not acyclicity).
    """
    by_id = {t.id: t for t in run_tasks}
    indeg = {t.id: sum(1 for d in t.depends_on if d in by_id) for t in run_tasks}
    ready = [t.id for t in run_tasks if indeg[t.id] == 0]
    ordered: List[Task] = []
    while ready:
        tid = ready.pop(0)
        ordered.append(by_id[tid])
        for t in run_tasks:
            if tid in t.depends_on and indeg.get(t.id, 0) > 0:
                indeg[t.id] -= 1
                if indeg[t.id] == 0:
                    ready.append(t.id)
    if len(ordered) != len(run_tasks):
        seen = {t.id for t in ordered}
        stuck = sorted(t.id for t in run_tasks if t.id not in seen)
        raise RuntimeError(f"Dependency cycle among tasks: {stuck}")
    return ordered


@dataclass
class _Attempt:
    """Outcome of one generate -> apply -> verify cycle (a best-of-N candidate)."""
    ti: Optional[Any]
    files_written: List[str]
    test_passed: bool
    test_out: str
    rule_errs: str
    parse_err: Optional[str]
    apply_err: Optional[str]
    usage: Dict[str, Any]


def _attempt_once(llm_call, agent_name, sys_prompt, user_task, schema_dict,
                   task_id, project_dir, framework, test_rel, temperature):
    """Generate one candidate, apply it, run the failing test + rules.

    Tolerates injected ``llm_call`` stubs that don't accept the schema /
    temperature kwargs (falls back progressively). Returns ``(_Attempt, raw)``.
    """
    try:
        raw, usage = llm_call(agent_name, sys_prompt, user_task, None,
                               response_schema=schema_dict,
                               schema_name="TaskImplementation",
                               temperature=temperature)
    except TypeError:
        try:
            raw, usage = llm_call(agent_name, sys_prompt, user_task, None,
                                   response_schema=schema_dict,
                                   schema_name="TaskImplementation")
        except TypeError:
            raw, usage = llm_call(agent_name, sys_prompt, user_task, None)

    ti, err = _coerce_task_implementation(raw, task_id)
    if ti is None:
        return _Attempt(None, [], False, "", "", err or "invalid", None, usage), raw
    if ti.task_id != task_id:
        ti = ti.model_copy(update={"task_id": task_id})
    try:
        files = _apply_files(project_dir, ti.files)
    except ValueError as ve:
        return _Attempt(ti, [], False, "", "", None, str(ve), usage), raw
    test_passed, test_out = _run_test_verbose(framework, project_dir, test_rel)
    rule_errs = _rules_errors(project_dir, files)
    return _Attempt(ti, files, test_passed, test_out, rule_errs, None, None, usage), raw


def _select_best(attempts: List["_Attempt"]) -> "_Attempt":
    """Execution-based selection: prefer a fully-passing candidate, else one that
    at least parsed and applied cleanly, else the first."""
    for a in attempts:
        if a.test_passed and not a.rule_errs:
            return a
    for a in attempts:
        if a.parse_err is None and a.apply_err is None:
            return a
    return attempts[0]


def _resolve_bon(best_of_n, bon_temperature):
    """Defaults from providers config when not explicitly passed."""
    if best_of_n is not None and bon_temperature is not None:
        return max(1, best_of_n), bon_temperature
    try:
        from utils.llm_adapter import _load_providers_config
    except ImportError:  # pragma: no cover
        from .llm_adapter import _load_providers_config  # type: ignore
    cfg = _load_providers_config()
    if best_of_n is None:
        best_of_n = cfg.get("code_best_of_n", 1)
    if bon_temperature is None:
        bon_temperature = cfg.get("code_best_of_n_temperature", 0.4)
    return max(1, best_of_n), bon_temperature


def run_implementation(
    spec_store: SpecStore,
    spec_id: str,
    project_dir: Path,
    agent_name: str = "fullstack_developer",
    task_ids: Optional[List[str]] = None,
    llm_call: Callable = _default_llm_call,
    repair_budget: int = 3,
    best_of_n: Optional[int] = None,
    bon_temperature: Optional[float] = None,
) -> ImplementRunResult:
    """Drive the full per-task implementation loop.

    ``project_dir`` is where files land + commits happen. If it is not yet a
    git repo, this initialises one.
    """
    spec_dir = spec_store._spec_dir(spec_id)
    spec = spec_store.load_artifact(spec_id, "feature_spec")
    plan = spec_store.load_artifact(spec_id, "plan")
    tasks: TaskList = spec_store.load_artifact(spec_id, "tasks")
    if not (spec and plan and tasks):
        raise RuntimeError("Spec, plan, or tasks artifact missing — run earlier phases first.")

    project_dir = Path(project_dir).resolve()
    _ensure_git_repo(project_dir)
    framework = detect(project_dir)
    if framework.name == "unknown":
        # Fall back to the framework the spec dir's tests use.
        framework = detect(spec_dir)

    wanted_ids = set(task_ids) if task_ids else {t.id for t in tasks.tasks}
    run_tasks = _ordered_tasks([t for t in tasks.tasks if t.id in wanted_ids])

    best_of_n, bon_temperature = _resolve_bon(best_of_n, bon_temperature)
    schema_dict = TaskImplementation.model_json_schema()
    outcomes: List[TaskOutcome] = []
    commit_traces: List[CommitTrace] = []

    for task in run_tasks:
        # Read the failing test the sdet wrote for this task; supports either
        # spec-dir-relative or project-dir-relative paths.
        test_full = (spec_dir / task.failing_test_path).resolve()
        if not test_full.exists():
            test_full = (project_dir / task.failing_test_path).resolve()
        failing_test_source = (
            test_full.read_text(encoding="utf-8") if test_full.exists() else ""
        )

        # Resolve where the failing test lands in the project (stable across
        # repair iterations).
        project_test = (project_dir / task.failing_test_path).resolve()
        if not str(project_test).startswith(str(project_dir)):
            project_test = (project_dir / Path(task.failing_test_path).name).resolve()
        project_test.parent.mkdir(parents=True, exist_ok=True)
        if test_full.exists() and not project_test.exists():
            shutil.copy2(test_full, project_test)
        test_rel = str(project_test.relative_to(project_dir)).replace("\\", "/")

        base_prompt = _build_task_prompt(task, spec, plan, failing_test_source, framework)
        sys_prompt = (
            "You are a senior implementer. Output a single TaskImplementation JSON "
            "object — no prose, no code fence. Files must be COMPLETE contents, "
            "not diffs. Do not include the failing test in `files` — only "
            "production code that makes it pass."
        )

        _write_active_task(spec_dir, task.id)
        try:
            # generate -> apply -> verify -> repair, up to repair_budget retries.
            # Attempt 0 draws best_of_n diverse candidates and execution-selects;
            # repair attempts are single-sample with accumulated feedback.
            files_written: List[str] = []
            test_passed = False
            last_error = None
            feedback = ""
            for attempt in range(repair_budget + 1):
                user_task = base_prompt + feedback
                n = best_of_n if (attempt == 0 and best_of_n > 1) else 1
                temp = bon_temperature if n > 1 else None

                tries: List[_Attempt] = []
                last_raw = ""
                for cand in range(n):
                    a, last_raw = _attempt_once(
                        llm_call, agent_name, sys_prompt, user_task, schema_dict,
                        task.id, project_dir, framework, test_rel, temp,
                    )
                    spec_store.record_phase_cost(spec_id, "implementation_trace", {
                        "task": task.id, "agent": agent_name, "attempt": attempt,
                        "candidate": cand, **a.usage,
                    })
                    tries.append(a)
                    if a.test_passed and not a.rule_errs:
                        break  # first fully-passing candidate wins
                a = _select_best(tries)

                if a.ti is None:
                    debug_path = spec_dir / f".debug_{task.id}_raw.txt"
                    try:
                        debug_path.write_text(last_raw, encoding="utf-8")
                    except OSError:
                        pass
                    last_error = f"agent output invalid: {a.parse_err}; raw saved to {debug_path.name}"
                    feedback = (
                        f"\n\nPREVIOUS ATTEMPT was not valid TaskImplementation JSON: "
                        f"{a.parse_err}\nReturn ONLY a valid TaskImplementation JSON object."
                    )
                    continue
                if a.apply_err:
                    last_error = a.apply_err
                    feedback = f"\n\nPREVIOUS ATTEMPT could not be applied: {a.apply_err}\nFix the file paths/contents."
                    continue

                files_written = a.files_written
                # If best-of-N picked a candidate that ISN'T the last one tried,
                # a later candidate overwrote its files on disk; re-apply the
                # winner so disk == selection before commit. (When the winner is
                # the last candidate, disk already matches.)
                if n > 1 and a is not tries[-1]:
                    try:
                        files_written = _apply_files(project_dir, a.ti.files)
                    except ValueError:
                        files_written = a.files_written
                test_passed = a.test_passed
                if test_passed and not a.rule_errs:
                    last_error = None
                    break

                last_error = "verification failed (test or rules)"
                diag = []
                if not test_passed:
                    diag.append(f"FAILING TEST did not pass. Key diagnostics:\n{_excerpt_failure(a.test_out)}")
                if a.rule_errs:
                    diag.append(f"BLOCKING rule violations:\n{a.rule_errs[:1500]}")
                feedback = (
                    "\n\nPREVIOUS ATTEMPT FAILED verification. Fix these and return "
                    "the COMPLETE corrected files:\n" + "\n\n".join(diag)
                )

            commit_sha = _commit(
                project_dir, files_written + [test_rel], task.title, task.fr_ids,
            ) if files_written else None

            outcomes.append(TaskOutcome(
                task_id=task.id, fr_ids=task.fr_ids,
                files_written=files_written, test_passed=test_passed,
                commit_sha=commit_sha,
                error=None if (test_passed and files_written) else last_error,
            ))
            if commit_sha:
                for fr in task.fr_ids:
                    commit_traces.append(CommitTrace(
                        fr_id=fr, task_id=task.id, commit_sha=commit_sha,
                        files=files_written, test_passed=test_passed,
                    ))
        finally:
            _clear_active_task(spec_dir)

    trace = ImplementationTrace(spec_id=spec_id, commits=commit_traces)
    spec_store.save_artifact(spec_id, "implementation_trace", trace)
    return ImplementRunResult(
        spec_id=spec_id, workspace=project_dir,
        outcomes=outcomes, trace=trace,
    )
