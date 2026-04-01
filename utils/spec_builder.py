"""Prompt builders for SDD — task strings and context strings are kept separate.

Pattern:
  context = build_*_context(...)   # reference material for the LLM context window
  task    = build_*_task(...)      # instruction only — no role preamble (system prompt covers that)
  agent.dispatch_to_llm(task=task, context=context)
"""

import re
from typing import Any, Dict, List


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


_AUDIT_LINE_RE = re.compile(
    r"^\[(MET|PARTIAL|MISSING)\]\s*(.+?)\s*\|\s*(.*)$", re.MULTILINE
)
_GO_NO_GO_RE = re.compile(r"GO_NO_GO:\s*(GO|NO.GO)", re.IGNORECASE)
_SUMMARY_RE = re.compile(r"SUMMARY:\s*(.+?)(?:\n\n|\Z)", re.DOTALL)


def parse_audit_to_json(audit_text: str, spec_id: str) -> Dict[str, Any]:
    """Parse delivery manager audit output into structured JSON.

    Returns a dict matching the contract borch expects:
    { spec_id, status, requirements: [{name, status, notes}], go_no_go, gaps }

    When audit_text doesn't match the expected format (e.g., guidance-only mode),
    returns { status: "GUIDANCE_ONLY", raw: audit_text }.
    """
    items = _AUDIT_LINE_RE.findall(audit_text)
    if not items:
        return {"spec_id": spec_id, "status": "GUIDANCE_ONLY", "raw": audit_text}

    requirements = []
    gaps = []
    for status, name, notes in items:
        status = status.upper()
        requirements.append({
            "name": name.strip(),
            "status": status,
            "notes": notes.strip(),
        })
        if status in ("PARTIAL", "MISSING"):
            gaps.append(name.strip())

    go_match = _GO_NO_GO_RE.search(audit_text)
    go_no_go = go_match.group(1).upper().replace("_", "-") if go_match else "NO-GO"

    summary_match = _SUMMARY_RE.search(audit_text)
    summary = summary_match.group(1).strip() if summary_match else ""

    all_met = all(r["status"] == "MET" for r in requirements)
    any_missing = any(r["status"] == "MISSING" for r in requirements)
    overall = "MET" if all_met else ("MISSING" if any_missing else "PARTIAL")

    return {
        "spec_id": spec_id,
        "status": overall,
        "requirements": requirements,
        "go_no_go": go_no_go,
        "gaps": gaps,
        "summary": summary,
    }
