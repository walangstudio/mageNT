"""Provider for everything-claude-code reference prompts.

Reads markdown subagent files from a sibling clone of everything-claude-code.
Override the location with the ``ECC_ROOT`` environment variable.

Mapping is best-effort — not every mageNT agent has a 1:1 ECC equivalent.
"""

from __future__ import annotations

import os
from typing import Optional, Tuple

DEFAULT_ECC_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "everything-claude-code")
)

# mageNT name -> ECC subagent file (relative to <ECC_ROOT>/agents/)
ECC_AGENT_MAP = {
    "security_engineer": "security-reviewer.md",
    "qa_engineer": "tdd-guide.md",
    "system_architect": "architect.md",
    "delivery_manager": "planner.md",
    "debugging_expert": "build-error-resolver.md",
    "performance_engineer": "harness-optimizer.md",
    "database_administrator": "database-reviewer.md",
}


def _strip_frontmatter(text: str) -> str:
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            return text[end + 4 :].lstrip("\n")
    return text


def render(agent_name: str, user_prompt: str) -> Tuple[str, str]:
    root = os.environ.get("ECC_ROOT", DEFAULT_ECC_ROOT)
    rel: Optional[str] = ECC_AGENT_MAP.get(agent_name)
    if not rel:
        raise KeyError(f"No ECC mapping for agent {agent_name!r}")
    path = os.path.join(root, "agents", rel)
    if not os.path.isfile(path):
        raise FileNotFoundError(
            f"ECC agent file missing: {path}. Set ECC_ROOT or update ECC_AGENT_MAP."
        )
    with open(path, "r", encoding="utf-8") as f:
        body = _strip_frontmatter(f.read())
    return body.rstrip(), user_prompt
