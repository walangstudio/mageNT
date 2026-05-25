"""Dependency-audit skill — runs the ecosystem vulnerability scanner for real."""

from pathlib import Path
from typing import Any, Dict, List

try:
    from skills.base import BaseSkill
    from skills.quality._exec import detect_stacks, run_cmd, summarize
except ImportError:
    from ..base import BaseSkill
    from ._exec import detect_stacks, run_cmd, summarize

_AUDITORS = {
    "python": ("pip-audit", ["pip-audit"]),
    "node": ("npm audit", ["npm", "audit"]),
    "go": ("govulncheck", ["govulncheck", "./..."]),
    "rust": ("cargo audit", ["cargo", "audit"]),
}


class DependencyAudit(BaseSkill):
    @property
    def name(self) -> str:
        return "dependency_audit"

    @property
    def slash_command(self) -> str:
        return "/dependency-audit"

    @property
    def description(self) -> str:
        return "Run the ecosystem vulnerability scanner (pip-audit/npm audit/govulncheck/cargo audit) and report advisories"

    @property
    def category(self) -> str:
        return "quality"

    @property
    def allowed_tools(self) -> List[str]:
        return ["Read", "Grep", "Glob", "Bash"]

    @property
    def parameters(self) -> List[Dict[str, Any]]:
        return [{"name": "path", "type": "string",
                 "description": "Project root (default: current directory)", "required": False}]

    def execute(self, **kwargs) -> Dict[str, Any]:
        root = Path(kwargs.get("path") or ".").resolve()
        results = []
        for stack in detect_stacks(root):
            spec = _AUDITORS.get(stack)
            if not spec:
                continue
            tool, argv = spec
            rc, out = run_cmd(argv, root)
            if rc is None:
                results.append({"tool": f"{stack}:{tool}", "returncode": None,
                                "passed": True, "skipped": True, "output": f"{tool} not installed"})
                continue
            results.append({"tool": f"{stack}:{tool}", "returncode": rc,
                            "passed": rc == 0, "skipped": False, "output": out})
        return summarize("Dependency audit", results)
