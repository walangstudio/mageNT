"""Logging hooks for tracking and auditing."""

import json
from datetime import datetime
from typing import Optional, List
from ..base import (
    BaseHook,
    HookContext,
    HookResult,
    HookType,
    HookPriority,
)


class LogToolUsageHook(BaseHook):
    """Log all tool usage for auditing and analytics."""

    def __init__(self, log_file: Optional[str] = None):
        self._log_file = log_file
        self._log_buffer: List[dict] = []

    @property
    def name(self) -> str:
        return "log-tool-usage"

    @property
    def description(self) -> str:
        return "Logs all MCP tool invocations for auditing and analytics"

    @property
    def hook_type(self) -> HookType:
        return HookType.POST_TOOL

    @property
    def priority(self) -> HookPriority:
        return HookPriority.LOWEST  # Run after everything else

    async def execute(self, context: HookContext) -> HookResult:
        """Log the tool usage."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "tool_name": context.tool_name,
            "session_id": context.session_id,
            "file_path": context.file_path,
            "metadata": {
                k: v for k, v in context.metadata.items()
                if k not in ["file_content", "code"]  # Don't log large content
            },
        }

        # Add to buffer
        self._log_buffer.append(log_entry)

        # Write to file if configured
        if self._log_file:
            try:
                with open(self._log_file, "a") as f:
                    f.write(json.dumps(log_entry) + "\n")
            except Exception as e:
                # Don't fail the operation due to logging errors
                pass

        return HookResult.success(logged=True, entry=log_entry)

    def get_logs(self) -> List[dict]:
        """Get all logged entries."""
        return self._log_buffer.copy()

    def clear_logs(self) -> None:
        """Clear the log buffer."""
        self._log_buffer.clear()


class LogSessionHook(BaseHook):
    """Log session start and end events."""

    def __init__(self):
        self._sessions: dict = {}

    @property
    def name(self) -> str:
        return "log-session"

    @property
    def description(self) -> str:
        return "Logs session lifecycle events (start, end, duration)"

    @property
    def hook_type(self) -> HookType:
        return HookType.SESSION_START  # Also handles SESSION_END

    @property
    def priority(self) -> HookPriority:
        return HookPriority.LOWEST

    def should_run(self, context: HookContext) -> bool:
        """Run for both session start and end."""
        return context.hook_type in (HookType.SESSION_START, HookType.SESSION_END)

    async def execute(self, context: HookContext) -> HookResult:
        """Log session event."""
        session_id = context.session_id or "unknown"

        if context.hook_type == HookType.SESSION_START:
            self._sessions[session_id] = {
                "start_time": datetime.utcnow(),
                "metadata": context.metadata,
            }
            return HookResult.success(
                message=f"Session {session_id} started",
                session_id=session_id,
            )

        elif context.hook_type == HookType.SESSION_END:
            session_data = self._sessions.pop(session_id, None)
            if session_data:
                duration = (datetime.utcnow() - session_data["start_time"]).total_seconds()
                return HookResult.success(
                    message=f"Session {session_id} ended after {duration:.1f}s",
                    session_id=session_id,
                    duration_seconds=duration,
                )
            return HookResult.success(
                message=f"Session {session_id} ended (no start recorded)",
                session_id=session_id,
            )

        return HookResult.success()

    def get_active_sessions(self) -> dict:
        """Get currently active sessions."""
        return {
            sid: {
                "start_time": data["start_time"].isoformat(),
                "duration_seconds": (datetime.utcnow() - data["start_time"]).total_seconds(),
            }
            for sid, data in self._sessions.items()
        }
