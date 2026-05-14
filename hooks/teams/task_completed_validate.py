#!/usr/bin/env python3
"""TaskCompleted hook: run `magent validate` when a teammate marks a task complete.

Exit codes:
  0 — accept the completion
  2 — reject (Claude Code surfaces our stderr to the teammate; they must fix
       the failing spec before retrying)

Wire-up (paste into ~/.claude/settings.json):

    "hooks": {
      "TaskCompleted": [
        {
          "matcher": ".*",
          "hooks": [
            {"type": "command",
             "command": "python <REPO>/hooks/teams/task_completed_validate.py"}
          ]
        }
      ]
    }

The hook is a no-op unless the cwd contains a ``specs/`` directory. So it is
safe to enable globally — projects without specs see no overhead.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys


def find_specs_dir(start: str) -> str | None:
    cur = os.path.abspath(start)
    for _ in range(6):
        candidate = os.path.join(cur, "specs")
        if os.path.isdir(candidate):
            return candidate
        parent = os.path.dirname(cur)
        if parent == cur:
            return None
        cur = parent
    return None


def main() -> int:
    specs = find_specs_dir(os.getcwd())
    if not specs:
        return 0

    magent = shutil.which("magent")
    if not magent:
        print(
            "task_completed_validate: `magent` not on PATH; skipping. "
            "Install the CLI or remove this hook.",
            file=sys.stderr,
        )
        return 0

    try:
        result = subprocess.run(
            [magent, "validate", specs],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        print("task_completed_validate: validator timed out after 30s.",
              file=sys.stderr)
        return 0
    except OSError as exc:
        print(f"task_completed_validate: {exc}", file=sys.stderr)
        return 0

    if result.returncode == 0:
        return 0

    sys.stderr.write(result.stdout or "")
    sys.stderr.write(result.stderr or "")
    sys.stderr.write(
        "\ntask_completed_validate: validator rejected the spec. "
        "Fix the failures above before marking the task complete.\n"
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
