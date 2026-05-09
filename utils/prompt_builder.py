"""Prompt builder utilities for agent system prompts.

The active template (``build_agent_prompt``) is the v2 compressed form: the
``<role>`` tag is preserved as a stable prompt-cache anchor, the body is
Markdown headings, and a single inline ``Filters:`` line replaces the per-agent
filter boilerplate. ``<output_schema>`` (XML, kept) wraps the JSON-Schema
snippet derived from a Pydantic model when ``output_schema_class`` is set.
``build_legacy_agent_prompt`` is preserved for the eval harness's ``current``
provider.
"""

import json
from typing import Dict, List, Optional, Sequence, Tuple, Any


_CAPABILITY_HINT = {
    "patterns":   "GoF + architectural patterns (CQRS, Event Sourcing, Saga, Strangler Fig)",
    "algorithms": "Algorithm design, complexity analysis, concurrency patterns",
    "principles": "SOLID, DRY, YAGNI, Law of Demeter, clean code",
    "ddd":        "Domain-Driven Design (bounded contexts, aggregates)",
    "security":   "OWASP Top 10, threat modelling, least privilege, secrets management",
    "data":       "Data modelling, query optimisation, indexing, schema migrations",
    "delivery":   "SDLC, Definition of Done, risk management, go/no-go criteria",
    "ux":         "User research, WCAG, design systems, usability heuristics",
    "testing":    "Test pyramid, TDD/BDD, isolation, mocking, CI integration",
}

# Legacy multi-line capability blocks kept for ``build_legacy_agent_prompt``.
_CAPABILITY_BLOCKS = {
    "patterns":   "- Software design patterns (GoF: Creational, Structural, Behavioural; Architectural: CQRS, Event Sourcing, Saga, Strangler Fig, Sidecar)",
    "algorithms": "- Algorithm design and complexity analysis (Big-O, space/time trade-offs, dynamic programming, concurrency patterns)",
    "principles": "- Engineering principles: SOLID, DRY, YAGNI, Law of Demeter, Separation of Concerns, clean code",
    "ddd":        "- Domain-Driven Design (bounded contexts, aggregates, ubiquitous language)",
    "security":   "- Security fundamentals: OWASP Top 10, threat modelling, least privilege, secrets management, input validation",
    "data":       "- Data modelling, query optimisation, indexing strategies, schema migrations, ACID guarantees",
    "delivery":   "- SDLC, Definition of Done, risk management, go/no-go criteria, stakeholder communication",
    "ux":         "- User research methods, WCAG accessibility, design systems, information architecture, usability heuristics",
    "testing":    "- Testing pyramid, TDD/BDD, test isolation, mocking strategies, CI integration",
}


# Single shared filter line. Placed once at the top of every prompt instead of
# repeating five bullets per agent.
_UNIVERSAL_FILTERS = (
    "Filters: surface findings (false-positives ok); skip below {confidence_floor} "
    "confidence unless CRITICAL; match length to task; never restate the request "
    "or narrate; cite file:line on code."
)


class PromptBuilder:
    """Builds system prompts for agents."""

    @staticmethod
    def build_agent_prompt(
        role: str,
        expertise_level: str,
        specialization: str,
        responsibilities: List[str],
        best_practices: Optional[List[str]] = None,
        context: Optional[str] = None,
        capability_tags: Optional[List[str]] = None,
        opinionated_stance: str = "",
        owned_scope: Optional[List[str]] = None,
        deferred_scope: Optional[Sequence[Tuple[str, str]]] = None,
        process_steps: Optional[List[str]] = None,
        decision_heuristics: Optional[List[str]] = None,
        confidence_floor: str = "medium",
        output_format: str = "",
        escalation_rules: Optional[List[str]] = None,
        examples: str = "",
        anti_examples: Optional[List[str]] = None,
        forbidden_outputs: Optional[List[str]] = None,
        output_schema_class: Optional[Any] = None,
    ) -> str:
        """Assemble a v2 agent system prompt.

        Layout:
            <role>...</role>      — stable cache prefix anchor; opens with stance
            Filters: ...          — single inline universal filter line
            ## Scope              — owned + deferred (markdown)
            ## Process            — numbered steps
            ## Heuristics         — decision rules
            ## Output             — prose template (fallback when no schema)
            <output_schema>...    — JSON-Schema (XML, gates parsing) when set
            ## Escalation
            ## Anti-patterns      — Do NOT lines + Never emit phrases
            ## Examples / ## Context

        Legacy callers that only pass responsibilities/best_practices still
        produce a usable prompt — those lists are folded into Scope and
        Heuristics as a fallback.
        """

        parts: List[str] = []

        # <role> — cache prefix anchor. Specialization is merged in here.
        opener = f"You are a {expertise_level.capitalize()} {role}"
        if specialization:
            opener = f"{opener}, {specialization.strip().rstrip('.')}"
        opener += "."
        if opinionated_stance:
            opener = f"{opener} {opinionated_stance.strip()}"
        parts += ["<role>", opener, "</role>", ""]

        # Inline universal filters (one line, replaces the per-agent <filters> block).
        parts += [_UNIVERSAL_FILTERS.format(confidence_floor=confidence_floor), ""]

        # Inline capability hint (one line, replaces the multi-bullet <capabilities> block).
        if capability_tags:
            hints = [_CAPABILITY_HINT[t] for t in capability_tags if t in _CAPABILITY_HINT]
            if hints:
                parts += [f"Domain: {'; '.join(hints)}.", ""]

        # ## Scope
        owned = list(owned_scope) if owned_scope else list(responsibilities)
        parts.append("## Scope")
        parts.append("Own:")
        parts += [f"- {item}" for item in owned]
        if deferred_scope:
            parts += ["", "Defer:"]
            for topic, defer_to in deferred_scope:
                parts.append(f"- {topic} → `{defer_to}`")
        parts += ["", "Out of scope: name the right specialist and stop.", ""]

        # ## Process
        if process_steps:
            parts.append("## Process")
            for i, step in enumerate(process_steps, 1):
                parts.append(f"{i}. {step}")
            parts.append("")

        # ## Heuristics
        heuristics = list(decision_heuristics) if decision_heuristics else list(best_practices or [])
        if heuristics:
            parts.append("## Heuristics")
            parts += [f"- {h}" for h in heuristics]
            parts.append("")

        # ## Output (prose template) — used only when no Pydantic schema.
        # When `output_schema_class` is set, the schema block below replaces it.
        if output_format and not output_schema_class:
            parts += ["## Output", output_format.strip(), ""]

        # <output_schema> (XML, kept — it gates the parser).
        if output_schema_class is not None:
            try:
                schema_dict = output_schema_class.model_json_schema()
                # Compact JSON: no whitespace. Model parses fine, prompt is half the size.
                schema_json = json.dumps(schema_dict, separators=(",", ":"))
                schema_name = getattr(output_schema_class, "__name__", "Response")
                parts += [
                    "## Output",
                    f"Respond with a single JSON object conforming to the schema below. "
                    f"Downstream code parses with `{schema_name}.model_validate_json(text)`; "
                    f"non-conforming output fails the contract. Emit JSON only — no "
                    f"prose, no code fence.",
                    "<output_schema>",
                    schema_json,
                    "</output_schema>",
                    "",
                ]
            except Exception:
                # If the schema can't render (e.g. forward-ref), fall back silently.
                if output_format:
                    parts += ["## Output", output_format.strip(), ""]

        # ## Escalation
        if escalation_rules:
            parts.append("## Escalation")
            parts.append("Escalate to a human when:")
            parts += [f"- {rule}" for rule in escalation_rules]
            parts.append("")

        # ## Anti-patterns
        anti = list(anti_examples) if anti_examples else []
        forbidden = list(forbidden_outputs) if forbidden_outputs else []
        if anti or forbidden:
            parts.append("## Anti-patterns")
            for a in anti:
                parts.append(f"- Do NOT {a}")
            if forbidden:
                quoted = ", ".join(f'"{p}"' for p in forbidden)
                parts.append(f"- Never emit: {quoted}.")
            parts.append("")

        # ## Examples
        if examples:
            parts += ["## Examples", examples.strip(), ""]

        # ## Context
        if context:
            parts += ["## Context", context.strip(), ""]

        while parts and parts[-1] == "":
            parts.pop()

        return "\n".join(parts)

    @staticmethod
    def build_legacy_agent_prompt(
        role: str,
        expertise_level: str,
        specialization: str,
        responsibilities: List[str],
        best_practices: Optional[List[str]] = None,
        context: Optional[str] = None,
        capability_tags: Optional[List[str]] = None,
    ) -> str:
        """Old flat template, kept for backwards compatibility."""

        prompt_parts = [
            f"You are a {expertise_level.capitalize()} {role} with expertise in: {specialization}.",
            "",
            "Your key responsibilities:",
        ]
        for i, responsibility in enumerate(responsibilities, 1):
            prompt_parts.append(f"{i}. {responsibility}")

        if best_practices:
            prompt_parts.extend(["", "Follow these best practices:"])
            for practice in best_practices:
                prompt_parts.append(f"- {practice}")

        if context:
            prompt_parts.extend(["", "Additional context:", context])

        if capability_tags:
            blocks = [_CAPABILITY_BLOCKS[tag] for tag in capability_tags if tag in _CAPABILITY_BLOCKS]
            if blocks:
                prompt_parts.extend(["", "Deep mastery of:"])
                prompt_parts.extend(blocks)

        prompt_parts.extend([
            "",
            "Be precise and direct. Match response length to the complexity of the question.",
            "Prioritise correctness and relevance over comprehensiveness.",
        ])
        return "\n".join(prompt_parts)

    @staticmethod
    def build_workflow_context(
        workflow_name: str,
        current_step: int,
        total_steps: int,
        previous_outputs: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        context_parts = [
            f"You are working on workflow: {workflow_name}",
            f"Current step: {current_step} of {total_steps}",
        ]

        if previous_outputs:
            context_parts.extend(["", "Previous steps completed:"])
            for output in previous_outputs:
                agent = output.get('agent', 'Unknown')
                summary = output.get('summary', 'No summary')
                context_parts.append(f"- {agent}: {summary}")

        context_parts.extend(["", "Build upon the previous work and ensure consistency."])
        return "\n".join(context_parts)

    @staticmethod
    def format_tool_description(
        agent_name: str,
        agent_role: str,
        expertise: str,
        use_cases: List[str],
    ) -> str:
        triggers = use_cases[:3]
        return f"{agent_role} ({expertise}). Use for: {'; '.join(triggers)}."
