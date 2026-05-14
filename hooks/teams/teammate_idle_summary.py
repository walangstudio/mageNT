#!/usr/bin/env python3
"""TeammateIdle hook: append a one-line status to specs/<active>/team_log.md.

Advisory only — always exits 0. Gives the team lead a single file to scan when
synthesizing teammate outputs.

Wire-up (paste into ~/.claude/settings.json):

    "hooks": {
      "TeammateIdle": [
        {
          "matcher": ".*",
          "hooks": [
            {"type": "command",
             "command": "python <REPO>/hooks/teams/teammate_idle_summary.py"}
          ]
        }
      ]
    }

If the cwd has no ``specs/<active>/`` directory the hook is a no-op.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import sys


def active_spec_dir(start: str) -> str | None:
    cur = os.path.abspath(start)
    for _ in range(6):
        specs = os.path.join(cur, "specs")
        active = os.path.join(specs, "active")
        if os.path.isdir(active):
            return active
        parent = os.path.dirname(cur)
        if parent == cur:
            return None
        cur = parent
    return None


def parse_event() -> dict:
    raw = sys.stdin.read().strip() if not sys.stdin.isatty() else ""
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"raw": raw[:200]}


def main() -> int:
    target = active_spec_dir(os.getcwd())
    if not target:
        return 0

    event = parse_event()
    teammate = (
        event.get("teammate")
        or event.get("agent_id")
        or event.get("name")
        or "unknown"
    )
    summary = (
        event.get("summary")
        or event.get("last_message")
        or event.get("status")
        or "idle"
    )
    if isinstance(summary, str) and len(summary) > 160:
        summary = summary[:159] + "…"

    line = (
        f"- {dt.datetime.now().isoformat(timespec='seconds')} "
        f"[{teammate}] {summary}\n"
    )

    log_path = os.path.join(target, "team_log.md")
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(line)
    except OSError as exc:
        sys.stderr.write(f"teammate_idle_summary: {exc}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
