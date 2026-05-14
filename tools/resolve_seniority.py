"""Resolve effective expertise_level for an agent across config layers.

Resolution order (highest wins):

    1. CLI overrides       dict passed to resolve()
    2. Project config      ./magent.seniority.yaml in CWD
    3. User config         ~/.magent/seniority.yaml
    4. Install profile     config/seniority_profiles.yaml::<profile>
    5. Class default       expertise_level on the agent class
    6. Fallback            "senior"

The resolver is called once at install time by tools/generate_dispatch.py so
the resolved level bakes into the rendered subagent markdown. No runtime
lookup, no surprises.

Valid level values: "principal", "staff", "senior", "" (empty = no level word
in the role line — used for specialist roles like business_analyst).
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

import yaml

VALID_LEVELS = {"principal", "staff", "senior", ""}

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_PROFILES_PATH = os.path.join(_REPO_ROOT, "config", "seniority_profiles.yaml")
_USER_CONFIG = os.path.expanduser("~/.magent/seniority.yaml")
_PROJECT_CONFIG = os.path.abspath("magent.seniority.yaml")


def _load_yaml(path: str) -> Dict[str, Any]:
    if not path or not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return data if isinstance(data, dict) else {}
    except (OSError, yaml.YAMLError):
        return {}


def _load_profile(profile: Optional[str]) -> Dict[str, str]:
    if not profile or profile == "default":
        return {}
    profiles = _load_yaml(_PROFILES_PATH)
    section = profiles.get(profile)
    return section if isinstance(section, dict) else {}


def _validate(level: Any) -> Optional[str]:
    if level is None:
        return None
    if not isinstance(level, str):
        return None
    candidate = level.strip().lower()
    return candidate if candidate in VALID_LEVELS else None


def resolve(
    agent_name: str,
    class_default: str = "senior",
    *,
    cli_overrides: Optional[Dict[str, str]] = None,
    profile: Optional[str] = None,
) -> str:
    """Return the resolved expertise_level for ``agent_name``."""
    for source in (
        cli_overrides or {},
        _load_yaml(_PROJECT_CONFIG),
        _load_yaml(_USER_CONFIG),
        _load_profile(profile),
    ):
        if agent_name in source:
            v = _validate(source[agent_name])
            if v is not None:
                return v
    v = _validate(class_default)
    return v if v is not None else "senior"


def resolve_all(
    agent_names,
    class_defaults: Dict[str, str],
    *,
    cli_overrides: Optional[Dict[str, str]] = None,
    profile: Optional[str] = None,
) -> Dict[str, str]:
    """Resolve levels for a batch of agents in one call."""
    return {
        n: resolve(
            n,
            class_defaults.get(n, "senior"),
            cli_overrides=cli_overrides,
            profile=profile,
        )
        for n in agent_names
    }


def parse_cli_overrides(spec: Optional[str]) -> Dict[str, str]:
    """Parse a ``--seniority a=principal,b=senior`` string into a dict."""
    if not spec:
        return {}
    out: Dict[str, str] = {}
    for pair in spec.split(","):
        if "=" not in pair:
            continue
        k, _, v = pair.partition("=")
        k = k.strip()
        v = v.strip()
        if k and _validate(v) is not None:
            out[k] = v.lower()
    return out
