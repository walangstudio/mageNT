"""Pre-commit hook that injects active task FR-IDs into commit messages.

When ``magent_implement`` is running a task, the active spec_id and task_id are
written to ``specs/<spec_id>/.active_task`` (a single line). This hook reads
that pointer, looks up the task's ``fr_ids``, and prepends ``[FR-001, FR-002] ``
to the commit message if it isn't already present. Result: every implementation
commit traces back to the FRs it satisfies — closes the spec → commit
traceability loop.

If no active task pointer exists (normal hand-coding), the hook is a no-op.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

from hooks.base import BaseHook, HookContext, HookPriority, HookResult, HookType


_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_SPECS_DIR = _REPO_ROOT / "specs"


def _read_active_task() -> Optional[tuple[str, str]]:
    """Return ``(spec_id, task_id)`` from any spec dir's ``.active_task`` file."""
    if not _SPECS_DIR.is_dir():
        return None
    for spec_dir in _SPECS_DIR.iterdir():
        if not spec_dir.is_dir():
            continue
        marker = spec_dir / ".active_task"
        if marker.exists():
            try:
                content = marker.read_text(encoding="utf-8").strip()
                if content:
                    return (spec_dir.name, content)
            except OSError:
                continue
    return None


def _lookup_fr_ids(spec_id: str, task_id: str) -> List[str]:
    tasks_path = _SPECS_DIR / spec_id / "tasks.json"
    if not tasks_path.exists():
        return []
    try:
        data = json.loads(tasks_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    for t in data.get("tasks", []):
        if t.get("id") == task_id:
            return list(t.get("fr_ids", []))
    return []


class FRIdCommitTagHook(BaseHook):
    """Prepend ``[FR-XXX] `` to commit messages from active magent_implement tasks."""

    @property
    def name(self) -> str:
        return "fr-id-commit-tag"

    @property
    def description(self) -> str:
        return (
            "Prepends [FR-XXX] tags from the active magent_implement task to the "
            "commit message. Closes spec → commit traceability."
        )

    @property
    def hook_type(self) -> HookType:
        return HookType.PRE_COMMIT

    @property
    def priority(self) -> HookPriority:
        return HookPriority.NORMAL

    async def execute(self, context: HookContext) -> HookResult:
        if not context.commit_message:
            return HookResult.success("no commit message to tag")

        active = _read_active_task()
        if not active:
            return HookResult.success("no active magent_implement task — no-op")

        spec_id, task_id = active
        fr_ids = _lookup_fr_ids(spec_id, task_id)
        if not fr_ids:
            return HookResult.success(
                f"active task {task_id} in spec {spec_id} has no fr_ids — no-op"
            )

        # Idempotent: skip if any of the fr_ids already appear in the message.
        msg = context.commit_message
        if any(fr in msg for fr in fr_ids):
            return HookResult.success("FR-IDs already present in commit message")

        tag = f"[{', '.join(fr_ids)}] "
        new_msg = tag + msg
        return HookResult.modify(
            allow=True,
            message=f"prepended {tag.strip()}",
            modified_data={"commit_message": new_msg},
        )
