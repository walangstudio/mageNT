"""Provider for the new XML-tagged mageNT prompts (current main)."""

from __future__ import annotations

import os
import sys
from typing import Tuple

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import server  # type: ignore  # noqa: E402


def render(agent_name: str, user_prompt: str) -> Tuple[str, str]:
    cls = server.AGENT_CLASSES[agent_name]
    spec = (cls.__doc__ or "").strip().splitlines()[0] if cls.__doc__ else ""
    agent = cls({"expertise_level": "principal", "specialization": spec})
    return agent.get_system_prompt(), user_prompt
