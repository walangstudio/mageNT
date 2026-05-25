"""Mutation-test skill — runs a mutation tester and reports the score.

Feeds the `mutation-score-minimum` rule: this skill produces the number the
rule grades. Mutation runs are slow, so it only runs when the tool is present
and the caller opts in (run=true); otherwise it returns setup guidance.
"""

from pathlib import Path
from typing import Any, Dict, List

try:
    from skills.base import BaseSkill
    from skills.quality._exec import detect_stacks, run_cmd, summarize
except ImportError:
    from ..base import BaseSkill
    from ._exec import detect_stacks, run_cmd, summarize

_MUTATORS = {
    "python": ("mutmut", ["mutmut", "run"]),
    "node": ("stryker", ["npx", "--no-install", "stryker", "run"]),
    "rust": ("cargo-mutants", ["cargo", "mutants"]),
}


class MutationTest(BaseSkill):
    @property
    def name(self) -> str:
        return "mutation_test"

    @property
    def slash_command(self) -> str:
        return "/mutation-test"

    @property
    def description(self) -> str:
        return "Run a mutation tester (mutmut/stryker/cargo-mutants); reports surviving mutants. Slow — pass run=true to execute."

    @property
    def category(self) -> str:
        return "quality"

    @property
    def allowed_tools(self) -> List[str]:
        return ["Read", "Grep", "Glob", "Bash"]

    @property
    def parameters(self) -> List[Dict[str, Any]]:
        return [
            {"name": "path", "type": "string",
             "description": "Project root (default: current directory)", "required": False},
            {"name": "run", "type": "boolean",
             "description": "Actually execute the (slow) mutation run; default false = guidance only", "required": False},
        ]

    def execute(self, **kwargs) -> Dict[str, Any]:
        root = Path(kwargs.get("path") or ".").resolve()
        do_run = bool(kwargs.get("run", False))
        stacks = detect_stacks(root)
        applicable = [(s, *_MUTATORS[s]) for s in stacks if s in _MUTATORS]
        if not do_run:
            tools = ", ".join(f"{s}:{t}" for s, t, _ in applicable) or "none detected"
            return {
                "guidance": (
                    "# Mutation testing (not run)\n\n"
                    f"Detected applicable tools: {tools}.\n\n"
                    "Coverage proves lines ran; mutation score proves the tests would "
                    "fail if the code were wrong. Re-invoke with run=true to execute "
                    "(slow). Feed the resulting score to check_code as `mutation_score` "
                    "so `mutation-score-minimum` can grade it."
                ),
                "context": {"ran": False, "applicable": [s for s, _, _ in applicable]},
                "success": True,
            }
        results = []
        for stack, tool, argv in applicable:
            rc, out = run_cmd(argv, root, timeout=1200)
            if rc is None:
                results.append({"tool": f"{stack}:{tool}", "returncode": None,
                                "passed": True, "skipped": True, "output": f"{tool} not installed"})
                continue
            results.append({"tool": f"{stack}:{tool}", "returncode": rc,
                            "passed": rc == 0, "skipped": False, "output": out})
        return summarize("Mutation test", results, {"ran": True})
