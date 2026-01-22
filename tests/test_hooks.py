"""Tests for the Hooks system."""

import pytest
import asyncio
from hooks import (
    HooksEngine,
    HooksConfig,
    HookContext,
    HookResult,
    HookType,
    HookPriority,
    BaseHook,
    CallableHook,
    hook,
    get_default_engine,
)


class TestHooksEngine:
    """Test the main hooks engine."""

    def test_engine_initialization(self):
        """Test that engine initializes correctly."""
        engine = HooksEngine()
        assert engine is not None

    def test_default_engine_loads_builtin_hooks(self):
        """Test that default engine loads built-in hooks."""
        engine = get_default_engine()
        hooks = engine.list_hooks()
        assert len(hooks) > 0

    def test_register_function_hook(self):
        """Test registering a function as a hook."""
        engine = HooksEngine()

        def my_hook(context):
            return HookResult.success("Hook executed")

        engine.register_function(
            name="test-hook",
            description="A test hook",
            hook_type=HookType.PRE_TOOL,
            func=my_hook,
        )

        hooks = engine.list_hooks()
        assert "test-hook" in hooks

    def test_register_callable_hook(self):
        """Test registering a CallableHook."""
        engine = HooksEngine()

        hook = CallableHook(
            name="callable-hook",
            description="A callable hook",
            hook_type=HookType.POST_TOOL,
            func=lambda ctx: HookResult.success(),
        )

        engine.register(hook)
        assert engine.get_hook("callable-hook") is not None

    def test_decorator_creates_hook(self):
        """Test that @hook decorator creates a hook."""
        from hooks import hook as hook_decorator

        @hook_decorator("decorated-hook", "A decorated hook", HookType.PRE_TOOL)
        def my_decorated_hook(context):
            return HookResult.success()

        assert isinstance(my_decorated_hook, CallableHook)
        assert my_decorated_hook.name == "decorated-hook"

    def test_execute_hooks(self):
        """Test executing hooks."""
        engine = HooksEngine()

        results = []

        def hook1(ctx):
            results.append("hook1")
            return HookResult.success()

        def hook2(ctx):
            results.append("hook2")
            return HookResult.success()

        engine.register_function("hook1", "Test 1", HookType.PRE_TOOL, hook1, HookPriority.HIGH)
        engine.register_function("hook2", "Test 2", HookType.PRE_TOOL, hook2, HookPriority.LOW)

        context = HookContext(hook_type=HookType.PRE_TOOL, tool_name="test_tool")

        report = asyncio.get_event_loop().run_until_complete(engine.execute(context))

        assert report.passed
        assert report.successful == 2
        # Hooks should run in priority order
        assert results == ["hook1", "hook2"]

    def test_blocking_hook(self):
        """Test that a failing hook blocks the operation."""
        engine = HooksEngine()

        def blocking_hook(ctx):
            return HookResult.failure("Operation blocked")

        engine.register_function("blocker", "Blocks operations", HookType.PRE_TOOL, blocking_hook)

        context = HookContext(hook_type=HookType.PRE_TOOL)
        report = asyncio.get_event_loop().run_until_complete(engine.execute(context))

        assert not report.passed
        assert report.blocked

    def test_disable_hook(self):
        """Test disabling a hook."""
        engine = HooksEngine()

        def my_hook(ctx):
            return HookResult.success()

        engine.register_function("disableable", "Can be disabled", HookType.PRE_TOOL, my_hook)

        # Disable it
        engine.disable_hook("disableable")

        hooks = engine.list_hooks()
        assert not hooks["disableable"]["enabled"]

        # Re-enable it
        engine.enable_hook("disableable")
        hooks = engine.list_hooks()
        assert hooks["disableable"]["enabled"]

    def test_unregister_hook(self):
        """Test unregistering a hook."""
        engine = HooksEngine()

        def my_hook(ctx):
            return HookResult.success()

        engine.register_function("removable", "Can be removed", HookType.PRE_TOOL, my_hook)
        assert engine.get_hook("removable") is not None

        engine.unregister("removable")
        assert engine.get_hook("removable") is None

    def test_tool_filter(self):
        """Test that tool filter works."""
        engine = HooksEngine()

        calls = []

        def filtered_hook(ctx):
            calls.append(ctx.tool_name)
            return HookResult.success()

        engine.register_function(
            "filtered",
            "Only for specific tools",
            HookType.PRE_TOOL,
            filtered_hook,
            tool_filter=["allowed_tool"],
        )

        # Should run for allowed tool
        ctx1 = HookContext(hook_type=HookType.PRE_TOOL, tool_name="allowed_tool")
        asyncio.get_event_loop().run_until_complete(engine.execute(ctx1))
        assert "allowed_tool" in calls

        # Should NOT run for other tools
        ctx2 = HookContext(hook_type=HookType.PRE_TOOL, tool_name="other_tool")
        asyncio.get_event_loop().run_until_complete(engine.execute(ctx2))
        assert "other_tool" not in calls

    def test_pre_commit_hooks(self):
        """Test pre-commit hook execution."""
        engine = HooksEngine()

        def commit_validator(ctx):
            msg = ctx.commit_message
            if not msg or len(msg) < 10:
                return HookResult.failure("Commit message too short")
            return HookResult.success()

        engine.register_function(
            "commit-validator",
            "Validates commit messages",
            HookType.PRE_COMMIT,
            commit_validator,
        )

        # Good commit message
        report = asyncio.get_event_loop().run_until_complete(
            engine.execute_pre_commit(
                commit_message="feat(auth): add user login functionality",
                branch_name="feature/auth",
            )
        )
        assert report.passed

        # Bad commit message
        report = asyncio.get_event_loop().run_until_complete(
            engine.execute_pre_commit(commit_message="fix")
        )
        assert not report.passed

    def test_hook_modifies_data(self):
        """Test that hooks can modify data."""
        engine = HooksEngine()

        def modifier_hook(ctx):
            return HookResult.modify(
                {"extra_field": "added"},
                message="Data modified"
            )

        engine.register_function("modifier", "Modifies data", HookType.PRE_TOOL, modifier_hook)

        context = HookContext(hook_type=HookType.PRE_TOOL)
        report = asyncio.get_event_loop().run_until_complete(engine.execute(context))

        assert report.passed
        assert report.modified_data is not None
        assert report.modified_data.get("extra_field") == "added"


class TestHookResult:
    """Test HookResult helper methods."""

    def test_success_result(self):
        """Test creating a success result."""
        result = HookResult.success("Operation successful")
        assert result.allow
        assert result.message == "Operation successful"

    def test_failure_result(self):
        """Test creating a failure result."""
        result = HookResult.failure("Operation failed")
        assert not result.allow
        assert result.message == "Operation failed"

    def test_modify_result(self):
        """Test creating a modify result."""
        result = HookResult.modify({"key": "value"}, "Data modified")
        assert result.allow
        assert result.modified_data == {"key": "value"}


class TestBuiltinHooks:
    """Test built-in hooks."""

    def test_builtin_hooks_load(self):
        """Test that built-in hooks can be loaded."""
        from hooks.builtin import BUILTIN_HOOKS
        assert len(BUILTIN_HOOKS) > 0

    def test_validation_hooks_exist(self):
        """Test that validation hooks exist."""
        from hooks.builtin.validation import (
            ValidateCodeBeforeEditHook,
            CheckSecurityHook,
            PreCommitValidationHook,
        )

        # Instantiate to verify they work
        h1 = ValidateCodeBeforeEditHook()
        h2 = CheckSecurityHook()
        h3 = PreCommitValidationHook()

        assert h1.name == "validate-code-before-edit"
        assert h2.name == "check-security"
        assert h3.name == "pre-commit-validation"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
