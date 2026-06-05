"""Spec-level code constraints — enforce what the test can't.

A failing test pins *behaviour*; it does not pin *forbidden means*. A spec that
says "evaluate the expression, no `eval()`" is satisfied by `return eval(expr)`
as far as the test is concerned. This module extracts the banned/required tokens
a FeatureSpec declares (explicitly via `FunctionalRequirement.constraints`, or
implicitly from the prose) and checks the written code against them, so the
implement loop treats a violated MUST-NOT as a real failure instead of a silent
pass.

Two sources, in priority order:
1. **Explicit** — `FunctionalRequirement.constraints` (a typed `forbid`/`require`
   list). Durable and unambiguous; prefer this for anything non-obvious.
2. **Heuristic** — a deliberately narrow scan of FR / success-criteria prose for
   the common "no `eval()`" / "without using subprocess" shape. Conservative by
   design (only `token()` forms and a small dangerous-builtin allowlist) so it
   almost never invents a constraint that wasn't meant.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional


@dataclass(frozen=True)
class CodeConstraint:
    """A single banned (`forbid`) or mandatory (`require`) code token."""

    kind: str            # "forbid" | "require"
    pattern: str         # identifier/token (e.g. "eval", "os.system") or regex
    message: str = ""    # why — surfaced to the implementer on violation
    regex: bool = False  # treat `pattern` as a raw regex
    source: str = ""     # FR id or "heuristic", for diagnostics


# Negation cues and the small filler vocabulary that sits between them and the
# banned token in natural prose ("must not use eval()", "without calling exec").
_NEG = r"(?:no|without|not|never|do not|don't|must not|cannot|can't|forbidden|disallow(?:ed)?|avoid)"
_FILLER = r"(?:\s+(?:use|using|call(?:ing)?|invoke|invoking|the|a|any|direct|directly|python(?:'s)?|built-?in))*"
_DANGEROUS = ("eval", "exec", "os.system", "subprocess", "__import__", "compile")

_RE_PAREN = re.compile(_NEG + _FILLER + r"\s+([A-Za-z_][\w.]*)\s*\(\s*\)", re.I)
_RE_DANGEROUS = re.compile(
    _NEG + _FILLER + r"\s+(" + "|".join(re.escape(d) for d in _DANGEROUS) + r")\b",
    re.I,
)

_LINE_COMMENT = re.compile(r"(#|//).*$", re.M)
_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.S)


def _heuristic(text: str, source: str) -> List[CodeConstraint]:
    if not text:
        return []
    found: List[CodeConstraint] = []
    seen = set()
    # Paren form ("no eval()") is the stronger signal; the dangerous-token form
    # ("no eval") is the fallback. Track tokens already captured so the two
    # passes don't emit overlapping entries for the same banned token.
    for m in _RE_PAREN.finditer(text):
        tok = m.group(1)
        if tok.lower() in seen:
            continue
        seen.add(tok.lower())
        found.append(CodeConstraint("forbid", tok, f"spec forbids {tok}()", source=source))
    for m in _RE_DANGEROUS.finditer(text):
        tok = m.group(1).lower()
        if tok in seen:
            continue
        seen.add(tok)
        found.append(CodeConstraint("forbid", tok, f"spec forbids {tok}", source=source))
    return found


def extract_constraints(spec) -> List[CodeConstraint]:
    """Collect code constraints from a FeatureSpec (explicit + heuristic).

    Duck-typed: anything exposing `.requirements` (each with `.statement` and an
    optional `.constraints`) and `.success_criteria` works, so tests can pass a
    lightweight stand-in. Returns a de-duplicated list; empty when the spec
    declares none (the common case → zero behaviour change downstream).
    """
    out: List[CodeConstraint] = []
    for fr in getattr(spec, "requirements", []) or []:
        fid = getattr(fr, "id", "FR")
        for c in getattr(fr, "constraints", []) or []:
            out.append(CodeConstraint(
                kind=getattr(c, "kind", "forbid"),
                pattern=getattr(c, "pattern", ""),
                message=getattr(c, "message", "") or f"{fid} constraint",
                regex=bool(getattr(c, "regex", False)),
                source=fid,
            ))
        out.extend(_heuristic(getattr(fr, "statement", "") or "", fid))
    for crit in getattr(spec, "success_criteria", []) or []:
        out.extend(_heuristic(crit or "", "success_criteria"))

    seen, deduped = set(), []
    for c in out:
        if not c.pattern:
            continue
        key = (c.kind, c.pattern.lower(), c.regex)
        if key not in seen:
            seen.add(key)
            deduped.append(c)
    return deduped


def _strip_comments(code: str) -> str:
    """Drop line/block comments so a banned token echoed in a comment (often the
    spec instruction itself) doesn't read as a violation."""
    return _LINE_COMMENT.sub("", _BLOCK_COMMENT.sub("", code))


def _matcher(c: CodeConstraint) -> re.Pattern:
    if c.regex:
        return re.compile(c.pattern)
    # Token match: word-boundaried, not preceded by an identifier char or dot, so
    # `eval(` matches but `my_eval` / `evaluate` / `foo.eval` do not. A dot in
    # the pattern (os.system) is escaped to a literal.
    return re.compile(r"(?<![\w.])" + re.escape(c.pattern) + r"\b")


def check_code(code: str, constraints: Iterable[CodeConstraint]) -> List[str]:
    """Return one diagnostic string per violated constraint in `code`."""
    body = _strip_comments(code)
    msgs: List[str] = []
    for c in constraints:
        hit = bool(_matcher(c).search(body))
        if c.kind == "forbid" and hit:
            why = f" — {c.message}" if c.message else ""
            msgs.append(f"forbidden '{c.pattern}' is used{why}")
        elif c.kind == "require" and not hit:
            why = f" — {c.message}" if c.message else ""
            msgs.append(f"required '{c.pattern}' is missing{why}")
    return msgs


def check_files(project_dir: Path, files_written: Iterable[str],
                constraints: Iterable[CodeConstraint]) -> str:
    """Constraint diagnostics across the written files, or "" when clean.

    Mirrors `implement_runner._rules_errors`' return shape so it folds into the
    same repair-feedback / selection channel.
    """
    constraints = list(constraints)
    if not constraints:
        return ""
    project_dir = Path(project_dir)
    lines: List[str] = []
    for rel in files_written:
        fp = (project_dir / rel).resolve()
        try:
            code = fp.read_text(encoding="utf-8")
        except OSError:
            continue
        for msg in check_code(code, constraints):
            lines.append(f"{rel}: {msg}")
    return "\n".join(lines)
