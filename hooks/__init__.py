"""
Hooks Engine for mageNT.

Provides a hook system for automation and validation at key points
in the development workflow. Works with ANY LLM that calls the MCP server.
"""

from typing import Dict, List, Optional, Type, Any, Callable, Union
from dataclasses import dataclass, field
import asyncio
import threading

from .base import (
    BaseHook,
    CallableHook,
    HookContext,
    HookResult,
    HookType,
    HookPriority,
    SyncHook,
    hook,
)


@dataclass
class HooksConfig:
    """Configuration for the hooks engine."""

    # Globally enabled/disabled
    enabled: bool = True

    # Disabled hook names
    disabled_hooks: set = field(default_factory=set)

    # Enabled hook types
    enabled_types: set = field(
        default_factory=lambda: {ht for ht in HookType}
    )

    # Whether to continue on hook failure
    continue_on_failure: bool = False

    # Maximum hooks to run per event
    max_hooks_per_event: int = 50


@dataclass
class HooksReport:
    """Report of hook execution results."""

    hook_type: HookType
    total_hooks_run: int
    successful: int
    failed: int
    blocked: bool
    results: List[tuple]  # (hook_name, HookResult)
    combined_message: Optional[str] = None
    modified_data: Optional[Dict[str, Any]] = None

    @property
    def passed(self) -> bool:
        """Whether all hooks passed and operation is allowed."""
        return not self.blocked and self.failed == 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "hook_type": self.hook_type.value,
            "total_hooks_run": self.total_hooks_run,
            "successful": self.successful,
            "failed": self.failed,
            "blocked": self.blocked,
            "passed": self.passed,
            "combined_message": self.combined_message,
            "results": [
                {
                    "hook_name": name,
                    "allow": result.allow,
                    "message": result.message,
                }
                for name, result in self.results
            ],
        }


class HooksEngine:
    """
    Main hooks engine that manages and executes hooks.

    The HooksEngine is designed to work with ANY LLM that calls the MCP server.
    It provides automation and validation hooks that enhance the development
    workflow regardless of which LLM is being used.
    """

    def __init__(self, config: Optional[HooksConfig] = None):
        """Initialize the hooks engine."""
        self.config = config or HooksConfig()
        self._hooks: Dict[HookType, List[BaseHook]] = {ht: [] for ht in HookType}
        self._hook_instances: Dict[str, BaseHook] = {}
        self._lock = threading.RLock()  # Reentrant lock for thread-safety

    def register(self, hook: BaseHook) -> None:
        """
        Register a hook with the engine.

        Args:
            hook: The hook to register
        """
        with self._lock:
            if hook.name in self._hook_instances:
                # Replace existing hook
                old_hook = self._hook_instances[hook.name]
                self._hooks[old_hook.hook_type].remove(old_hook)

            self._hooks[hook.hook_type].append(hook)
            self._hook_instances[hook.name] = hook

            # Sort by priority
            self._hooks[hook.hook_type].sort(key=lambda h: h.priority.value)

    def register_function(
        self,
        name: str,
        description: str,
        hook_type: HookType,
        func: Callable[[HookContext], Union[HookResult, bool, None]],
        priority: HookPriority = HookPriority.NORMAL,
        tool_filter: Optional[List[str]] = None,
    ) -> None:
        """
        Register a function as a hook.

        Args:
            name: Unique hook name
            description: What the hook does
            hook_type: When the hook runs
            func: The function to execute
            priority: Execution priority
            tool_filter: Tool names to filter (for tool hooks)
        """
        hook = CallableHook(
            name=name,
            description=description,
            hook_type=hook_type,
            func=func,
            priority=priority,
            tool_filter=tool_filter,
        )
        self.register(hook)

    def unregister(self, hook_name: str) -> bool:
        """
        Unregister a hook by name.

        Args:
            hook_name: Name of the hook to remove

        Returns:
            True if hook was found and removed
        """
        with self._lock:
            if hook_name not in self._hook_instances:
                return False

            hook = self._hook_instances.pop(hook_name)
            self._hooks[hook.hook_type].remove(hook)
            return True

    def get_hook(self, name: str) -> Optional[BaseHook]:
        """Get a hook by name."""
        with self._lock:
            return self._hook_instances.get(name)

    def list_hooks(self) -> Dict[str, Dict[str, Any]]:
        """List all registered hooks with their metadata."""
        with self._lock:
            return {
                name: {
                    "name": hook.name,
                    "description": hook.description,
                    "hook_type": hook.hook_type.value,
                    "priority": hook.priority.value,
                    "enabled": hook.name not in self.config.disabled_hooks,
                }
                for name, hook in self._hook_instances.items()
            }

    def enable_hook(self, hook_name: str) -> bool:
        """Enable a disabled hook."""
        with self._lock:
            if hook_name in self.config.disabled_hooks:
                self.config.disabled_hooks.remove(hook_name)
                return True
            return False

    def disable_hook(self, hook_name: str) -> bool:
        """Disable a hook."""
        with self._lock:
            if hook_name in self._hook_instances:
                self.config.disabled_hooks.add(hook_name)
                return True
            return False

    def get_hooks_for_type(self, hook_type: HookType) -> List[BaseHook]:
        """Get all enabled hooks for a specific type."""
        with self._lock:
            if not self.config.enabled:
                return []

            if hook_type not in self.config.enabled_types:
                return []

            return [
                h for h in self._hooks[hook_type]
                if h.name not in self.config.disabled_hooks
            ]

    async def execute(self, context: HookContext) -> HooksReport:
        """
        Execute all hooks for the given context.

        Args:
            context: The hook context

        Returns:
            HooksReport with all results
        """
        hook_type = context.hook_type
        hooks = self.get_hooks_for_type(hook_type)

        results: List[tuple] = []
        successful = 0
        failed = 0
        blocked = False
        messages = []
        modified_data = {}

        for i, hook in enumerate(hooks[:self.config.max_hooks_per_event]):
            # Check if hook should run
            if not hook.should_run(context):
                continue

            try:
                result = await hook.execute(context)
                results.append((hook.name, result))

                if result.allow:
                    successful += 1
                    if result.message:
                        messages.append(f"[{hook.name}] {result.message}")
                    if result.modified_data:
                        modified_data.update(result.modified_data)
                else:
                    failed += 1
                    blocked = True
                    if result.message:
                        messages.append(f"[{hook.name}] BLOCKED: {result.message}")

                # Check if we should stop the chain
                if result.stop_chain:
                    break

                # Check if blocked and not continuing on failure
                if blocked and not self.config.continue_on_failure:
                    break

            except Exception as e:
                failed += 1
                results.append((
                    hook.name,
                    HookResult.failure(f"Hook execution error: {str(e)}")
                ))
                messages.append(f"[{hook.name}] ERROR: {str(e)}")

                if not self.config.continue_on_failure:
                    blocked = True
                    break

        return HooksReport(
            hook_type=hook_type,
            total_hooks_run=successful + failed,
            successful=successful,
            failed=failed,
            blocked=blocked,
            results=results,
            combined_message="\n".join(messages) if messages else None,
            modified_data=modified_data if modified_data else None,
        )

    async def execute_pre_tool(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
        **metadata
    ) -> HooksReport:
        """
        Execute pre-tool hooks.

        Args:
            tool_name: Name of the tool being called
            tool_args: Arguments to the tool
            **metadata: Additional metadata

        Returns:
            HooksReport
        """
        context = HookContext(
            hook_type=HookType.PRE_TOOL,
            tool_name=tool_name,
            tool_args=tool_args,
            metadata=metadata,
        )
        return await self.execute(context)

    async def execute_post_tool(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
        tool_result: Any,
        **metadata
    ) -> HooksReport:
        """
        Execute post-tool hooks.

        Args:
            tool_name: Name of the tool that was called
            tool_args: Arguments that were passed
            tool_result: Result from the tool
            **metadata: Additional metadata

        Returns:
            HooksReport
        """
        context = HookContext(
            hook_type=HookType.POST_TOOL,
            tool_name=tool_name,
            tool_args=tool_args,
            tool_result=tool_result,
            metadata=metadata,
        )
        return await self.execute(context)

    async def execute_pre_commit(
        self,
        commit_message: str,
        branch_name: Optional[str] = None,
        file_changes: Optional[List[str]] = None,
        **metadata
    ) -> HooksReport:
        """
        Execute pre-commit hooks.

        Args:
            commit_message: The commit message
            branch_name: Current branch name
            file_changes: List of changed files
            **metadata: Additional metadata

        Returns:
            HooksReport
        """
        context = HookContext(
            hook_type=HookType.PRE_COMMIT,
            commit_message=commit_message,
            branch_name=branch_name,
            metadata={
                "file_changes": file_changes or [],
                **metadata,
            },
        )
        return await self.execute(context)

    def load_builtin_hooks(self) -> None:
        """Load all built-in hooks."""
        from .builtin import BUILTIN_HOOKS

        for hook_class in BUILTIN_HOOKS:
            try:
                hook = hook_class()
                self.register(hook)
            except Exception as e:
                print(f"Warning: Failed to load built-in hook {hook_class.__name__}: {e}")


# Create a default engine instance
_default_engine: Optional[HooksEngine] = None
_default_engine_lock = threading.Lock()


def get_default_engine() -> HooksEngine:
    """Get the default hooks engine instance."""
    global _default_engine
    if _default_engine is None:
        with _default_engine_lock:
            # Double-check after acquiring lock
            if _default_engine is None:
                _default_engine = HooksEngine()
                _default_engine.load_builtin_hooks()
    return _default_engine


# Export public interface
__all__ = [
    # Core classes
    "HooksEngine",
    "HooksConfig",
    "HooksReport",
    # Base types
    "BaseHook",
    "CallableHook",
    "SyncHook",
    "HookContext",
    "HookResult",
    "HookType",
    "HookPriority",
    # Decorator
    "hook",
    # Default instance
    "get_default_engine",
]
