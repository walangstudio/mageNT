"""Builders for spec-kit compatible output.

Generates spec.md, plan.md, and task files in the format that
borch's speckit::parse() (borch/src/spec/speckit.rs) can consume.

borch expects:
- specs/{spec_id}/spec.md  (first 50 lines used as context)
- specs/{spec_id}/tasks/*.md  (YAML frontmatter with name + files, body is prompt)
"""

from datetime import datetime, timezone
from typing import List, Dict, Any


def build_speckit_spec(
    project_name: str,
    description: str,
    requirements: List[str],
) -> str:
    """Generate a spec-kit format spec.md from raw requirements."""
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    branch = _slugify(project_name)

    # Group requirements into user stories (P1, P2, P3...)
    stories = _requirements_to_stories(requirements)
    fr_items = _requirements_to_fr(requirements)
    sc_items = _requirements_to_sc(requirements)

    stories_md = _format_stories(stories)
    fr_md = _format_fr(fr_items)
    sc_md = _format_sc(sc_items)

    return f"""# Feature Specification: {project_name}

**Feature Branch**: `{branch}`
**Created**: {date}
**Status**: Draft

## Description

{description}

## User Scenarios & Testing

{stories_md}

### Edge Cases

- What happens when invalid input is provided?
- How does the system handle concurrent operations?

## Requirements

### Functional Requirements

{fr_md}

### Key Entities

- [NEEDS CLARIFICATION: identify key data entities from requirements]

## Success Criteria

### Measurable Outcomes

{sc_md}

## Assumptions

- Standard development environment with required dependencies
- Requirements listed above represent the complete initial scope
"""


def build_speckit_plan(
    project_name: str,
    spec_content: str,
    arch_content: str,
) -> str:
    """Generate a spec-kit format plan.md."""
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    branch = _slugify(project_name)

    return f"""# Implementation Plan: {project_name}

**Branch**: `{branch}` | **Date**: {date} | **Spec**: specs/{branch}/spec.md

## Summary

{arch_content[:500]}

## Technical Context

Extracted from architecture spec. See arch_spec.md for full details.

## Project Structure

```text
src/
tests/
```

## Phases

Phase 1: Setup - Project initialization and dependencies
Phase 2: Foundation - Core models and infrastructure
Phase 3+: User Stories - Implementation by priority

## Notes

- Full architecture spec: arch_spec.md
- Full requirements: spec.md
"""


def build_speckit_tasks(
    spec_content: str,
    arch_content: str,
    requirements: List[str] | None = None,
) -> List[Dict[str, Any]]:
    """Generate spec-kit compatible task dicts.

    Each dict has: name, files, prompt, phase.
    These become individual .md files in the tasks/ directory.
    """
    tasks = []

    # Phase 1: Setup
    tasks.append({
        "name": "project-setup",
        "files": "src/,tests/,package.json",
        "prompt": (
            "Initialize the project structure based on the architecture spec.\n\n"
            "Create the directory layout, install dependencies, and configure "
            "build tools as specified in the tech stack.\n\n"
            f"## Architecture\n{arch_content[:2000]}"
        ),
        "phase": 1,
    })

    # Phase 2: Foundation
    tasks.append({
        "name": "core-models",
        "files": "src/models/",
        "prompt": (
            "Implement core data models and database schema based on the architecture spec.\n\n"
            "Create all entities, relationships, and migrations.\n\n"
            f"## Architecture\n{arch_content[:2000]}"
        ),
        "phase": 2,
    })

    # Extract user stories from spec and create tasks for each
    stories = _extract_stories_from_spec(spec_content)
    if not stories and requirements:
        stories = _requirements_to_stories(requirements)

    for i, story in enumerate(stories):
        phase = 3 + i
        story_name = _slugify(story["title"])
        tasks.append({
            "name": f"story-{story_name}",
            "files": f"src/,tests/",
            "prompt": (
                f"Implement User Story {i + 1}: {story['title']}\n\n"
                f"Priority: {story['priority']}\n\n"
                f"{story['description']}\n\n"
                f"## Acceptance Criteria\n{story.get('acceptance', 'See spec.md')}\n\n"
                f"## Architecture\n{arch_content[:1000]}"
            ),
            "phase": phase,
        })

    # Final phase: Polish
    tasks.append({
        "name": "polish-and-verify",
        "files": "src/,tests/,docs/",
        "prompt": (
            "Final quality pass:\n"
            "- Run all tests and fix failures\n"
            "- Code cleanup and documentation\n"
            "- Performance optimization\n"
            "- Security hardening\n\n"
            f"## Full Spec\n{spec_content[:1000]}"
        ),
        "phase": 100,
    })

    return tasks


def build_speckit_requirements_spec_task() -> str:
    """Prompt for business_analyst to produce spec-kit formatted spec."""
    return """Generate a structured requirements specification in spec-kit format.

Output MUST follow this exact structure:

# Feature Specification: [PROJECT NAME]

## User Scenarios & Testing

For each major requirement, create a prioritized user story:

### User Story N - [Title] (Priority: P1/P2/P3)
[Description]
**Why this priority**: [Justification]
**Independent Test**: [How to test independently]
**Acceptance Scenarios**:
1. **Given** [state], **When** [action], **Then** [outcome]

## Requirements

### Functional Requirements
- **FR-001**: System MUST [capability]
- **FR-002**: System MUST [capability]

### Key Entities
- **[Entity]**: [Description and relationships]

## Success Criteria

### Measurable Outcomes
- **SC-001**: [Measurable metric]
- **SC-002**: [Measurable metric]

Mark unclear items with [NEEDS CLARIFICATION: question].
Be terse. Output only the spec content."""


# --- Internal helpers ---

def _slugify(s: str) -> str:
    return (
        s.lower()
        .replace(" ", "-")
        .replace("_", "-")
        .strip("-")
    )


def _requirements_to_stories(requirements: List[str]) -> List[Dict[str, str]]:
    """Map raw requirements into user story structures."""
    stories = []
    for i, req in enumerate(requirements):
        stories.append({
            "title": req[:80],
            "description": req,
            "priority": f"P{min(i + 1, 3)}",
            "acceptance": f"**Given** the system is running, **When** {req.lower()}, **Then** the feature works as specified",
        })
    return stories


def _requirements_to_fr(requirements: List[str]) -> List[Dict[str, str]]:
    """Map requirements to FR-xxx items."""
    return [
        {"id": f"FR-{i + 1:03d}", "text": req}
        for i, req in enumerate(requirements)
    ]


def _requirements_to_sc(requirements: List[str]) -> List[Dict[str, str]]:
    """Map requirements to SC-xxx success criteria."""
    return [
        {"id": f"SC-{i + 1:03d}", "text": f"Requirement '{req[:60]}' is fully implemented and tested"}
        for i, req in enumerate(requirements)
    ]


def _format_stories(stories: List[Dict[str, str]]) -> str:
    parts = []
    for i, s in enumerate(stories):
        parts.append(
            f"### User Story {i + 1} - {s['title']} (Priority: {s['priority']})\n\n"
            f"{s['description']}\n\n"
            f"**Why this priority**: Core requirement #{i + 1}\n\n"
            f"**Independent Test**: Verify this story works in isolation\n\n"
            f"**Acceptance Scenarios**:\n\n"
            f"1. {s['acceptance']}\n"
        )
    return "\n---\n\n".join(parts)


def _format_fr(items: List[Dict[str, str]]) -> str:
    return "\n".join(f"- **{item['id']}**: System MUST {item['text']}" for item in items)


def _format_sc(items: List[Dict[str, str]]) -> str:
    return "\n".join(f"- **{item['id']}**: {item['text']}" for item in items)


def _extract_stories_from_spec(spec_content: str) -> List[Dict[str, str]]:
    """Extract user stories from an existing spec.md (best-effort)."""
    import re
    stories = []
    pattern = re.compile(
        r"###\s+User Story\s+\d+\s*-\s*(.+?)\s*\(Priority:\s*(P\d+)\)",
        re.IGNORECASE,
    )
    for match in pattern.finditer(spec_content):
        title = match.group(1).strip()
        priority = match.group(2).strip()
        # Extract description: text between this header and next ### or ##
        start = match.end()
        next_header = re.search(r"\n##", spec_content[start:])
        end = start + next_header.start() if next_header else len(spec_content)
        description = spec_content[start:end].strip()[:500]
        stories.append({
            "title": title,
            "description": description,
            "priority": priority,
            "acceptance": "See spec.md",
        })
    return stories
