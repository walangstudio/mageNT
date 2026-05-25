"""Shared helpers for execution-grounded quality skills.

Unlike the older guidance-only skills, these actually run the underlying tool
via subprocess and return structured pass/fail + diagnostics. A missing tool is
reported as `skipped` (not a failure) so a project that doesn't use a given
ecosystem doesn't get a false negative.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple

_TIMEOUT = 300


def detect_stacks(root: Path) -> List[str]:
    """Which language ecosystems are present, by marker file."""
    markers = {
        "python": ("pyproject.toml", "setup.py", "setup.cfg", "requirements.txt"),
        "node": ("package.json",),
        "go": ("go.mod",),
        "rust": ("Cargo.toml",),
    }
    found = []
    for stack, files in markers.items():
        if any((root / f).exists() for f in files):
            found.append(stack)
    return found


def run_cmd(cmd: List[str], cwd: Path, timeout: int = _TIMEOUT) -> Tuple[Optional[int], str]:
    """Run a command. Returns (returncode, combined_output).

    returncode is None when the executable isn't installed (treated as skipped).
    """
    if not shutil.which(cmd[0]):
        return None, f"{cmd[0]} not installed"
    try:
        proc = subprocess.run(
            cmd, cwd=str(cwd), capture_output=True, text=True, timeout=timeout,
        )
        out = (proc.stdout or "") + (proc.stderr or "")
        return proc.returncode, out.strip()
    except subprocess.TimeoutExpired:
        return 124, f"{cmd[0]} timed out after {timeout}s"
    except OSError as exc:
        return None, f"{cmd[0]} failed to start: {exc}"


def summarize(skill: str, results: List[Dict], extra: Optional[Dict] = None) -> Dict:
    """Build the standard skill return from a list of per-tool result dicts.

    Each result dict: {tool, returncode, passed, skipped, output}.
    Overall passed = no tool failed (skipped tools don't fail the run).
    """
    ran = [r for r in results if not r["skipped"]]
    passed = all(r["passed"] for r in ran) if ran else True
    lines = [f"# {skill} result", ""]
    if not ran:
        lines.append("No applicable tool found for this project (nothing run).")
    for r in results:
        if r["skipped"]:
            lines.append(f"- ⏭️  {r['tool']}: skipped ({r['output']})")
        elif r["passed"]:
            lines.append(f"- ✅ {r['tool']}: passed")
        else:
            lines.append(f"- ❌ {r['tool']}: failed (rc={r['returncode']})")
    failed = [r for r in ran if not r["passed"]]
    if failed:
        lines.append("\n## Diagnostics")
        for r in failed:
            lines.append(f"\n### {r['tool']}\n```\n{r['output'][:4000]}\n```")
    context = {"passed": passed, "tools": results}
    if extra:
        context.update(extra)
    return {"guidance": "\n".join(lines), "context": context, "success": passed}
