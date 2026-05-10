"""Detect the test framework + conventional layout of a project.

Used by ``magent_tasks`` so the sdet agent can emit failing tests in the right
language + framework without being told. Detection is best-effort heuristic:
pyproject / package.json / go.mod / Cargo.toml first, then file extensions.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class TestFramework:
    name: str            # pytest | vitest | jest | go-test | cargo-test | unknown
    language: str        # python | typescript | javascript | go | rust | unknown
    extension: str       # py | ts | js | go | rs
    test_dir: str        # default test directory (relative)
    runner_command: str  # how to invoke a single test file
    test_filename_pattern: str  # e.g. "test_{slug}.py" or "{slug}.test.ts"


_DEFAULTS = {
    "pytest":     TestFramework("pytest",     "python",     "py", "tests/",
                                "python -m pytest {path}", "test_{slug}.py"),
    "vitest":     TestFramework("vitest",     "typescript", "ts", "tests/",
                                "npx vitest run {path}", "{slug}.test.ts"),
    "jest":       TestFramework("jest",       "javascript", "js", "tests/",
                                "npx jest {path}", "{slug}.test.js"),
    "go-test":    TestFramework("go-test",    "go",         "go", ".",
                                "go test ./{path}", "{slug}_test.go"),
    "cargo-test": TestFramework("cargo-test", "rust",       "rs", "tests/",
                                "cargo test --test {slug}", "{slug}.rs"),
    "unknown":    TestFramework("unknown",    "unknown",    "txt", "tests/",
                                "echo 'no runner detected for' {path}",
                                "T{slug}.txt"),
}


def _has(deps: dict, name: str) -> bool:
    """package.json deps lookup across deps + devDeps + peerDeps."""
    for k in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
        if isinstance(deps.get(k), dict) and name in deps[k]:
            return True
    return False


def detect(project_root: Path) -> TestFramework:
    """Inspect ``project_root`` and pick the most likely test framework."""
    root = Path(project_root).resolve()
    if not root.is_dir():
        return _DEFAULTS["unknown"]

    # 1. Python — pyproject.toml or requirements.txt with pytest
    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        text = pyproject.read_text(encoding="utf-8", errors="ignore")
        if "[tool.pytest" in text or re.search(r"\bpytest\b", text):
            return _DEFAULTS["pytest"]
    requirements = root / "requirements.txt"
    if requirements.exists() and "pytest" in requirements.read_text(
        encoding="utf-8", errors="ignore"
    ):
        return _DEFAULTS["pytest"]

    # 2. Node — package.json with vitest > jest precedence
    pkg = root / "package.json"
    if pkg.exists():
        try:
            deps = json.loads(pkg.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            deps = {}
        if _has(deps, "vitest"):
            return _DEFAULTS["vitest"]
        if _has(deps, "jest") or _has(deps, "@types/jest"):
            return _DEFAULTS["jest"]
        # default to vitest for fresh TS projects
        if _has(deps, "typescript") or (root / "tsconfig.json").exists():
            return _DEFAULTS["vitest"]
        return _DEFAULTS["jest"]

    # 3. Go
    if (root / "go.mod").exists():
        return _DEFAULTS["go-test"]

    # 4. Rust
    if (root / "Cargo.toml").exists():
        return _DEFAULTS["cargo-test"]

    # 5. File-extension heuristic
    by_ext = {}
    for path in root.rglob("*"):
        if path.is_file():
            ext = path.suffix.lstrip(".").lower()
            by_ext[ext] = by_ext.get(ext, 0) + 1
            if sum(by_ext.values()) > 200:
                break  # don't scan giant trees
    if by_ext.get("py", 0) > 0:
        return _DEFAULTS["pytest"]
    if by_ext.get("ts", 0) > 0 or by_ext.get("tsx", 0) > 0:
        return _DEFAULTS["vitest"]
    if by_ext.get("js", 0) > 0 or by_ext.get("jsx", 0) > 0:
        return _DEFAULTS["jest"]
    if by_ext.get("go", 0) > 0:
        return _DEFAULTS["go-test"]
    if by_ext.get("rs", 0) > 0:
        return _DEFAULTS["cargo-test"]

    return _DEFAULTS["unknown"]


def slugify(text: str) -> str:
    """Filesystem-safe lowercase slug used in failing-test paths."""
    s = re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-")
    return s[:60] or "scenario"


def failing_test_path(framework: TestFramework, task_id: str, scenario_title: str) -> str:
    """Compose the path a sdet-generated test should live at."""
    slug = f"{task_id}-{slugify(scenario_title)}"
    return f"{framework.test_dir.rstrip('/')}/{framework.test_filename_pattern.format(slug=slug)}"


if __name__ == "__main__":  # pragma: no cover
    import sys
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    fw = detect(target)
    print(f"Detected: {fw.name} ({fw.language}) — runner: {fw.runner_command}")
