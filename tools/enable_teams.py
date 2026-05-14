"""Idempotently set CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1 in Claude Code settings.

Usage::

    python tools/enable_teams.py                # write to ~/.claude/settings.json
    python tools/enable_teams.py --check        # report state, exit 0/1
    python tools/enable_teams.py --disable      # remove the env var
    python tools/enable_teams.py --settings <p> # custom settings file

Writes JSON only — preserves existing keys and ordering best-effort. Never
creates parent dirs beyond ~/.claude/ to avoid surprising the user.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict

DEFAULT_SETTINGS = os.path.expanduser("~/.claude/settings.json")
ENV_KEY = "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS"


def load(path: str) -> Dict[str, Any]:
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"enable_teams: cannot parse {path}: {exc}", file=sys.stderr)
        sys.exit(1)
    return data if isinstance(data, dict) else {}


def save(path: str, data: Dict[str, Any]) -> None:
    parent = os.path.dirname(path)
    if parent and not os.path.isdir(parent):
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def is_enabled(data: Dict[str, Any]) -> bool:
    env = data.get("env") or {}
    return str(env.get(ENV_KEY, "")) == "1"


def enable(path: str) -> bool:
    """Return True if the file changed."""
    data = load(path)
    env = data.setdefault("env", {})
    if str(env.get(ENV_KEY, "")) == "1":
        return False
    env[ENV_KEY] = "1"
    save(path, data)
    return True


def disable(path: str) -> bool:
    data = load(path)
    env = data.get("env") or {}
    if ENV_KEY not in env:
        return False
    env.pop(ENV_KEY)
    if not env:
        data.pop("env", None)
    save(path, data)
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--settings", default=DEFAULT_SETTINGS,
                    help=f"Path to Claude settings.json (default: {DEFAULT_SETTINGS})")
    ap.add_argument("--check", action="store_true",
                    help="Report state only; exit 0 if enabled, 1 if not.")
    ap.add_argument("--disable", action="store_true",
                    help="Remove the env var instead of setting it.")
    args = ap.parse_args()

    path = os.path.expanduser(args.settings)

    if args.check:
        ok = is_enabled(load(path))
        print(f"{ENV_KEY}={'1' if ok else '(unset)'} in {path}")
        return 0 if ok else 1

    if args.disable:
        changed = disable(path)
        print(f"{'removed' if changed else 'already absent'}: {ENV_KEY} in {path}")
        return 0

    changed = enable(path)
    print(f"{'set' if changed else 'already set'}: {ENV_KEY}=1 in {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
