"""Type-check skill — runs the project's type checker for real."""

from pathlib import Path
from typing import Any, Dict, List

try:
    from skills.base import BaseSkill
    from skills.quality._exec import detect_stacks, run_cmd, summarize
except ImportError:
    from ..base import BaseSkill
    from ._exec import detect_stacks, run_cmd, summarize

_CHECKERS = {
    "python": [("mypy", ["mypy", "."])],
    "node": [("tsc", ["npx", "--no-install", "tsc", "--noEmit"])],
    "go": [("go build", ["go", "build", "./..."])],   # compile == type check in Go
    "rust": [("cargo check", ["cargo", "check", "--quiet"])],
}


class TypeCheck(BaseSkill):
    @property
    def name(self) -> str:
        return "typecheck"

    @property
    def slash_command(self) -> str:
        return "/typecheck"

    @property
    def description(self) -> str:
        return "Run the project's type checker (mypy/tsc/go build/cargo check) and return pass/fail + errors"

    @property
    def category(self) -> str:
        return "quality"

    @property
    def allowed_tools(self) -> List[str]:
        return ["Read", "Grep", "Glob", "Bash"]

    @property
    def parameters(self) -> List[Dict[str, Any]]:
        return [{"name": "path", "type": "string",
                 "description": "Project root to check (default: current directory)",
                 "required": False}]

    def execute(self, **kwargs) -> Dict[str, Any]:
        root = Path(kwargs.get("path") or ".").resolve()
        results = []
        for stack in detect_stacks(root):
            for tool, argv in _CHECKERS.get(stack, []):
                rc, out = run_cmd(argv, root)
                if rc is None:
                    results.append({"tool": f"{stack}:{tool}", "returncode": None,
                                    "passed": True, "skipped": True,
                                    "output": f"{argv[0]} not installed"})
                    break
                results.append({"tool": f"{stack}:{tool}", "returncode": rc,
                                "passed": rc == 0, "skipped": False, "output": out})
                break
        return summarize("Type check", results)
