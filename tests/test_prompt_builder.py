"""Tests for the v2 role-line renderer.

Locks in the post-fix behaviour:
  - "You are a <Level> <Role>." with no duplication and no "specializing in" tail
  - empty expertise_level => "You are a <Role>." with no level word
  - specialization is appended only when it doesn't restate the role
"""

from __future__ import annotations

import os
import sys

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from utils.prompt_builder import PromptBuilder


def _role_line(prompt: str) -> str:
    lines = prompt.splitlines()
    idx = lines.index("<role>")
    return lines[idx + 1]


def test_role_line_clean_no_duplication():
    out = PromptBuilder.build_agent_prompt(
        role="Security Engineer",
        expertise_level="staff",
        specialization="",
        responsibilities=["Review code"],
        opinionated_stance="You assume breach.",
    )
    line = _role_line(out)
    assert line == "You are a Staff Security Engineer. You assume breach."
    assert "Security Engineer, Security Engineer" not in out
    assert "specializing in" not in out


def test_empty_level_drops_level_word():
    out = PromptBuilder.build_agent_prompt(
        role="Business Analyst",
        expertise_level="",
        specialization="",
        responsibilities=["Gather requirements"],
    )
    line = _role_line(out)
    assert line == "You are a Business Analyst."
    assert "Senior Business Analyst" not in out


def test_specialization_dropped_when_restates_role():
    # Old behaviour was to append the class docstring's first line as
    # specialization, which often started with "<Role> specializing in...".
    # The fix drops that when the role name is already in the specialization.
    out = PromptBuilder.build_agent_prompt(
        role="Security Engineer",
        expertise_level="staff",
        specialization="Security Engineer specializing in application security",
        responsibilities=["Review code"],
    )
    line = _role_line(out)
    assert line == "You are a Staff Security Engineer."
    assert "Security Engineer, Security Engineer" not in out


def test_specialization_kept_when_genuinely_extra():
    out = PromptBuilder.build_agent_prompt(
        role="Backend Developer",
        expertise_level="senior",
        specialization="Rust and async runtimes",
        responsibilities=["Write code"],
    )
    line = _role_line(out)
    assert line == "You are a Senior Backend Developer, Rust and async runtimes."


def test_principal_level_capitalized():
    out = PromptBuilder.build_agent_prompt(
        role="System Architect",
        expertise_level="principal",
        specialization="",
        responsibilities=["Make decisions"],
    )
    assert _role_line(out).startswith("You are a Principal System Architect.")
