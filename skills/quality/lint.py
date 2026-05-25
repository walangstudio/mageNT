"""Lint skill — runs the project's linter(s) for real."""

from pathlib import Path
from typing import Any, Dict, List

try:
    from skills.base import BaseSkill
    from skills.quality._exec import detect_stacks, run_cmd, summarize
except ImportError:
    from ..base import BaseSkill
    from ._exec import detect_stacks, run_cmd, summarize

# stack -> (tool, argv). First installed tool per stack wins.
_LINTERS = {
    "python": [("ruff", ["ruff", "check", "."]), ("flake8", ["flake8", "."])],
    "node": [("eslint", ["npx", "--no-install", "eslint", "."])],
    "go": [("golangci-lint", ["golangci-lint", "run"]), ("go", ["go", "vet", "./..."])],
    "rust": [("clippy", ["cargo", "clippy", "--quiet"])],
}


class Lint(BaseSkill):
    @property
    def name(self) -> str:
        return "lint"

    @property
    def slash_command(self) -> str:
        return "/lint"

    @property
    def description(self) -> str:
        return "Run the project's linter (ruff/eslint/golangci-lint/clippy) and return pass/fail + findings"

    @property
    def category(self) -> str:
        return "quality"

    @property
    def allowed_tools(self) -> List[str]:
        return ["Read", "Grep", "Glob", "Bash"]

    @property
    def parameters(self) -> List[Dict[str, Any]]:
        return [{"name": "path", "type": "string",
                 "description": "Project root to lint (default: current directory)",
                 "required": False}]

    def execute(self, **kwargs) -> Dict[str, Any]:
        root = Path(kwargs.get("path") or ".").resolve()
        results = []
        for stack in detect_stacks(root):
            for tool, argv in _LINTERS.get(stack, []):
                rc, out = run_cmd(argv, root)
                if rc is None:
                    continue  # tool not installed, try next for this stack
                results.append({"tool": f"{stack}:{tool}", "returncode": rc,
                                "passed": rc == 0, "skipped": False, "output": out})
                break
            else:
                if stack in _LINTERS:
                    results.append({"tool": f"{stack}:linter", "returncode": None,
                                    "passed": True, "skipped": True,
                                    "output": "no linter installed"})
        return summarize("Lint", results)
