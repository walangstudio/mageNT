"""
Base classes for the Hooks system.

Hooks allow automation and validation at key points in the development workflow.
They work with ANY LLM that calls the MCP server.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union
import asyncio


class HookType(Enum):
    """Types of hooks that can be registered."""

    # Tool hooks - run before/after MCP tools
    PRE_TOOL = "pre_tool"
    POST_TOOL = "post_tool"

    # Code hooks - run on code changes
    PRE_EDIT = "pre_edit"
    POST_EDIT = "post_edit"

    # Git hooks - run on git operations
    PRE_COMMIT = "pre_commit"
    POST_COMMIT = "post_commit"
    PRE_PUSH = "pre_push"

    # Session hooks
    SESSION_START = "session_start"
    SESSION_END = "session_end"

    # Custom hooks
    CUSTOM = "custom"


class HookPriority(Enum):
    """Priority levels for hook execution order."""

    HIGHEST = 0
    HIGH = 25
    NORMAL = 50
    LOW = 75
    LOWEST = 100


@dataclass
class HookContext:
    """Context passed to hooks during execution."""

    hook_type: HookType
    tool_name: Optional[str] = None
    tool_args: Optional[Dict[str, Any]] = None
    tool_result: Optional[Any] = None
    file_path: Optional[str] = None
    file_content: Optional[str] = None
    old_content: Optional[str] = None
    new_content: Optional[str] = None
    commit_message: Optional[str] = None
    branch_name: Optional[str] = None
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "hook_type": self.hook_type.value,
            "tool_name": self.tool_name,
            "tool_args": self.tool_args,
            "file_path": self.file_path,
            "commit_message": self.commit_message,
            "branch_name": self.branch_name,
            "session_id": self.session_id,
            "metadata": self.metadata,
        }


@dataclass
class HookResult:
    """Result returned by hook execution."""

    # Whether the hook allows the operation to proceed
    allow: bool = True

    # Message to display (info, warning, or error)
    message: Optional[str] = None

    # Modified data to use instead of original
    modified_data: Optional[Dict[str, Any]] = None

    # Additional data to pass to subsequent hooks
    extra_data: Dict[str, Any] = field(default_factory=dict)

    # Whether to skip remaining hooks in chain
    stop_chain: bool = False

    @staticmethod
    def success(message: Optional[str] = None, **extra) -> "HookResult":
        """Create a successful result."""
        return HookResult(allow=True, message=message, extra_data=extra)

    @staticmethod
    def failure(message: str, **extra) -> "HookResult":
        """Create a failure result that blocks the operation."""
        return HookResult(allow=False, message=message, extra_data=extra)

    @staticmethod
    def modify(data: Dict[str, Any], message: Optional[str] = None) -> "HookResult":
        """Create a result that modifies the operation data."""
        return HookResult(allow=True, modified_data=data, message=message)


class BaseHook(ABC):
    """Abstract base class for all hooks."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique name for the hook."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Description of what the hook does."""
        pass

    @property
    @abstractmethod
    def hook_type(self) -> HookType:
        """The type of hook (when it runs)."""
        pass

    @property
    def priority(self) -> HookPriority:
        """Execution priority (lower runs first)."""
        return HookPriority.NORMAL

    @property
    def enabled(self) -> bool:
        """Whether the hook is enabled."""
        return True

    @property
    def tool_filter(self) -> Optional[List[str]]:
        """
        List of tool names this hook applies to.
        None means all tools. Only used for PRE_TOOL and POST_TOOL hooks.
        """
        return None

    @abstractmethod
    async def execute(self, context: HookContext) -> HookResult:
        """
        Execute the hook.

        Args:
            context: The hook context with relevant data

        Returns:
            HookResult indicating success/failure and any modifications
        """
        pass

    def should_run(self, context: HookContext) -> bool:
        """
        Check if this hook should run for the given context.

        Override this for custom filtering logic.
        """
        if not self.enabled:
            return False

        # Check tool filter for tool hooks
        if self.hook_type in (HookType.PRE_TOOL, HookType.POST_TOOL):
            if self.tool_filter is not None and context.tool_name:
                return context.tool_name in self.tool_filter

        return True


class SyncHook(BaseHook):
    """Base class for synchronous hooks."""

    @abstractmethod
    def execute_sync(self, context: HookContext) -> HookResult:
        """Synchronous hook execution."""
        pass

    async def execute(self, context: HookContext) -> HookResult:
        """Wrap sync execution in async."""
        return self.execute_sync(context)


class CallableHook(BaseHook):
    """Hook that wraps a callable function."""

    def __init__(
        self,
        name: str,
        description: str,
        hook_type: HookType,
        func: Callable[[HookContext], Union[HookResult, bool, None]],
        priority: HookPriority = HookPriority.NORMAL,
        tool_filter: Optional[List[str]] = None,
    ):
        self._name = name
        self._description = description
        self._hook_type = hook_type
        self._func = func
        self._priority = priority
        self._tool_filter = tool_filter
        self._enabled = True

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def hook_type(self) -> HookType:
        return self._hook_type

    @property
    def priority(self) -> HookPriority:
        return self._priority

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool):
        self._enabled = value

    @property
    def tool_filter(self) -> Optional[List[str]]:
        return self._tool_filter

    async def execute(self, context: HookContext) -> HookResult:
        """Execute the wrapped callable."""
        result = self._func(context)

        # Handle async functions
        if asyncio.iscoroutine(result):
            result = await result

        # Convert various return types to HookResult
        if result is None:
            return HookResult.success()
        elif isinstance(result, bool):
            return HookResult(allow=result)
        elif isinstance(result, HookResult):
            return result
        elif isinstance(result, str):
            return HookResult.success(message=result)
        else:
            return HookResult.success()


def hook(
    name: str,
    description: str,
    hook_type: HookType,
    priority: HookPriority = HookPriority.NORMAL,
    tool_filter: Optional[List[str]] = None,
):
    """
    Decorator to create a hook from a function.

    Usage:
        @hook("my-hook", "Does something", HookType.PRE_TOOL)
        async def my_hook(context: HookContext) -> HookResult:
            return HookResult.success()
    """

    def decorator(func: Callable) -> CallableHook:
        return CallableHook(
            name=name,
            description=description,
            hook_type=hook_type,
            func=func,
            priority=priority,
            tool_filter=tool_filter,
        )

    return decorator
