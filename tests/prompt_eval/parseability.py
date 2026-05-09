"""Schema validation helper for the eval harness.

Looks up the Pydantic schema for the agent under test, attempts to coerce the
raw response into JSON (stripping ```json fences and prose), and reports
whether ``Schema.model_validate_json(...)`` succeeds.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, Optional, Tuple

try:
    from agents.schemas import AGENT_SCHEMAS  # type: ignore
except ImportError:  # pragma: no cover - exercised only outside the eval harness
    AGENT_SCHEMAS = {}


_FENCE_RE = re.compile(r"^```(?:json)?\s*\n(.*?)\n```\s*$", re.DOTALL | re.IGNORECASE)


def _extract_json(text: str) -> Optional[str]:
    """Return the JSON document from a model response, or None.

    Strategy: code fence first, then largest balanced ``{...}`` slice. If the
    response was truncated mid-JSON (common at hard ``max_tokens`` limits), we
    return the partial slice so the caller's validator surfaces a precise
    Pydantic error rather than the generic "no JSON object found".
    """
    if not text:
        return None
    s = text.strip()
    m = _FENCE_RE.match(s)
    if m:
        return m.group(1).strip()
    start = s.find("{")
    if start < 0:
        return None
    # Scan for a balanced object; track string state so brace chars inside
    # strings don't confuse depth.
    depth = 0
    in_str = False
    escape = False
    for i in range(start, len(s)):
        c = s[i]
        if in_str:
            if escape:
                escape = False
            elif c == "\\":
                escape = True
            elif c == '"':
                in_str = False
            continue
        if c == '"':
            in_str = True
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return s[start:i + 1]
    # Fell off the end with depth > 0 → response was truncated. Return what we
    # have so Pydantic gives a precise error.
    return s[start:]


def validate(agent_name: str, response: str) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
    """Validate ``response`` against the agent's schema.

    Returns ``(parseable, error_message, parsed_dict)``. ``parsed_dict`` is the
    raw dict on success, useful for richer downstream checks.
    """
    cls = AGENT_SCHEMAS.get(agent_name)
    if cls is None:
        return (False, f"no schema registered for agent '{agent_name}'", None)
    blob = _extract_json(response or "")
    if blob is None:
        return (False, "no JSON object found in response", None)
    try:
        obj = cls.model_validate_json(blob)
    except Exception as e:  # ValidationError or JSON parse error
        return (False, str(e)[:500], None)
    return (True, None, obj.model_dump())
