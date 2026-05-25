"""Format skill — checks (or applies) the project's formatter for real."""

from pathlib import Path
from typing import Any, Dict, List

try:
    from skills.base import BaseSkill
    from skills.quality._exec import detect_stacks, run_cmd, summarize
except ImportError:
    from ..base import BaseSkill
    from ._exec import detect_stacks, run_cmd, summarize

# stack -> (tool, check_argv, apply_argv)
_FORMATTERS = {
    "python": ("black", ["black", "--check", "."], ["black", "."]),
    "node": ("prettier", ["npx", "--no-install", "prettier", "--check", "."],
             ["npx", "--no-install", "prettier", "--write", "."]),
    "go": ("gofmt", ["gofmt", "-l", "."], ["gofmt", "-w", "."]),
    "rust": ("cargo fmt", ["cargo", "fmt", "--check"], ["cargo", "fmt"]),
}


class FormatCode(BaseSkill):
    @property
    def name(self) -> str:
        return "format"

    @property
    def slash_command(self) -> str:
        return "/format"

    @property
    def description(self) -> str:
        return "Check (or apply with apply=true) the project's formatter (black/prettier/gofmt/rustfmt)"

    @property
    def category(self) -> str:
        return "quality"

    @property
    def allowed_tools(self) -> List[str]:
        return ["Read", "Grep", "Glob", "Bash", "Edit", "Write"]

    @property
    def parameters(self) -> List[Dict[str, Any]]:
        return [
            {"name": "path", "type": "string",
             "description": "Project root (default: current directory)", "required": False},
            {"name": "apply", "type": "boolean",
             "description": "Apply formatting in place instead of just checking", "required": False},
        ]

    def execute(self, **kwargs) -> Dict[str, Any]:
        root = Path(kwargs.get("path") or ".").resolve()
        apply = bool(kwargs.get("apply", False))
        results = []
        for stack in detect_stacks(root):
            fmt = _FORMATTERS.get(stack)
            if not fmt:
                continue
            tool, check_argv, apply_argv = fmt
            argv = apply_argv if apply else check_argv
            rc, out = run_cmd(argv, root)
            if rc is None:
                results.append({"tool": f"{stack}:{tool}", "returncode": None,
                                "passed": True, "skipped": True, "output": f"{tool} not installed"})
                continue
            # gofmt -l lists unformatted files on stdout with rc 0; non-empty == fail
            passed = rc == 0 and not (tool == "gofmt" and out.strip())
            results.append({"tool": f"{stack}:{tool}", "returncode": rc,
                            "passed": passed, "skipped": False, "output": out})
        return summarize("Format" + (" (apply)" if apply else " (check)"), results, {"applied": apply})
