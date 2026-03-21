"""Prompt builders for SDD — task strings and context strings are kept separate.

Pattern:
  context = build_*_context(...)   # reference material for the LLM context window
  task    = build_*_task(...)      # instruction only — no role preamble (system prompt covers that)
  agent.dispatch_to_llm(task=task, context=context)
"""

from typing import Dict, List


def build_requirements_spec_context(
    project_name: str,
    description: str,
    requirements: List[str],
) -> str:
    req_list = "\n".join(f"- {r}" for r in requirements)
    return f"""Project: {project_name}
Description: {description}

Raw requirements:
{req_list}"""


def build_requirements_spec_task() -> str:
    return """Generate a structured requirements spec from the project information above.

Include:
1. Refined description (2-3 sentences)
2. Acceptance checklist — each item independently verifiable, formatted as:
   - [ ] item
3. Out-of-scope items (if implied by the requirements)
4. Key constraints or assumptions

Be terse. Output only the spec content."""


def build_arch_spec_task() -> str:
    return """Produce a technical architecture spec for the requirements above.

Include:
1. **Tech Stack** — language, framework, database, infrastructure
2. **Component Design** — main services/modules and their responsibilities
3. **API Contracts** — key endpoints or interfaces (brief, not exhaustive)
4. **Data Models** — core entities and relationships
5. **Non-functional requirements** — scalability, security, performance

Be explicit — commit to a stack, don't hedge with "or X or Y". Output only the arch spec content."""


def build_agent_phase_task(phase: str) -> str:
    """Instruction-only task. Arch spec is passed as context by the caller."""
    return {
        "build": (
            "Provide concrete implementation guidance for your domain based on the architecture spec above.\n\n"
            "Include: file structure, key code patterns, configuration, and integration points with other components. "
            "Be specific to the tech stack. Output actionable guidance only."
        ),
        "qa": (
            "Review the architecture above for issues in your domain.\n\n"
            "Identify concrete risks, gaps, and missing considerations. "
            "For each finding provide a remediation step. Output actionable findings only."
        ),
    }.get(
        phase,
        "Review the architecture above and provide domain-specific guidance. Output actionable guidance only.",
    )


def build_audit_task(
    spec_content: str,
    arch_spec_content: str,
    phase_results: Dict[str, str],
) -> str:
    """Full audit task including reference material and instruction.

    Passed as `task` with no separate context, since the DM needs all three
    inputs together to make a coherent checklist judgement.
    """
    results_block = "\n\n".join(
        f"### {agent}\n{result}"
        for agent, result in phase_results.items()
    )
    return f"""## Original Requirements Spec
{spec_content}

## Architecture Spec
{arch_spec_content}

## Agent Phase Results
{results_block}

---

For each item in the Acceptance Checklist above, determine:
- MET — fully addressed in the phase results
- PARTIAL — partially addressed; specify what is missing
- MISSING — not addressed at all

Output format (one line per requirement):
[MET|PARTIAL|MISSING] <requirement text> | <notes>

After the checklist output:
GO_NO_GO: GO or NO_GO
SUMMARY: one paragraph delivery assessment"""
