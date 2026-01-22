"""Built-in hooks for mageNT."""

from .validation import (
    ValidateCodeBeforeEditHook,
    CheckSecurityHook,
    PreCommitValidationHook,
)
from .logging import (
    LogToolUsageHook,
    LogSessionHook,
)
from .automation import (
    AutoFormatHook,
    AutoTestHook,
)

# All built-in hooks
BUILTIN_HOOKS = [
    ValidateCodeBeforeEditHook,
    CheckSecurityHook,
    PreCommitValidationHook,
    LogToolUsageHook,
    LogSessionHook,
    AutoFormatHook,
    AutoTestHook,
]

__all__ = [
    "BUILTIN_HOOKS",
    "ValidateCodeBeforeEditHook",
    "CheckSecurityHook",
    "PreCommitValidationHook",
    "LogToolUsageHook",
    "LogSessionHook",
    "AutoFormatHook",
    "AutoTestHook",
]
