"""Shared output-discipline guardrails for code-emitting agents.

Grounded in measured weak-model failure modes (NIM llama-3.1-8b, raw-vs-magent
coding eval, 2026-06): the verbose senior-*specialist* persona pushed small
models toward over-engineering and contract violations that a terse "senior
engineer" prompt avoided: e.g. `parse_qs` implemented as
`from urllib.parse import parse_qs` + a self-named wrapper (→ RecursionError),
top-level demo `print()`s, and needless `Enum`/class scaffolding around trivial
logic. These anti-patterns curb exactly those modes without removing legitimate
structure (note the "trivial" / "needless" qualifiers).

Mix into a code-emitting agent BEFORE BaseAgent in the MRO:

    class PythonBackend(CodeDisciplineMixin, BaseAgent): ...

Subclasses may add their own via `extra_anti_examples`.
"""

from typing import ClassVar, List

_CODE_ANTI_EXAMPLES: List[str] = [
    "add top-level executable statements, demonstration calls, `print()`s, or "
    "`__main__` blocks; define exactly the requested symbols and nothing else",
    "import a standard-library helper that has the SAME name as the function you "
    "must implement (it shadows your definition and self-recurses); implement the "
    "logic directly",
    "wrap trivial logic in needless classes, Enums, dataclasses, or extra layers "
    "of indirection; write the simplest correct implementation that satisfies "
    "the contract",
    "change the requested names, signatures, parameter order, or return types",
    "emit explanatory prose, tutorial-style comments, or markdown code fences "
    "around the artifact; output only the code that was asked for",
]


class CodeDisciplineMixin:
    """Adds shared anti-over-engineering guardrails to a code-emitting agent."""

    #: Subclasses may override (by reassignment, not .append) to add anti-patterns.
    extra_anti_examples: ClassVar[List[str]] = []

    @property
    def anti_examples(self) -> List[str]:
        return _CODE_ANTI_EXAMPLES + list(self.extra_anti_examples)
