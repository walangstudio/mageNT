"""Prompt builder utilities for agent system prompts."""

from typing import Dict, List, Optional, Any


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
    ) -> str:
        prompt_parts = [
            f"You are a {expertise_level} {role} with expertise in: {specialization}.",
            "",
            "Your key responsibilities:",
        ]

        for i, responsibility in enumerate(responsibilities, 1):
            prompt_parts.append(f"{i}. {responsibility}")

        if best_practices:
            prompt_parts.extend([
                "",
                "Follow these best practices:",
            ])
            for practice in best_practices:
                prompt_parts.append(f"- {practice}")

        if context:
            prompt_parts.extend([
                "",
                "Additional context:",
                context,
            ])

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
            context_parts.extend([
                "",
                "Previous steps completed:",
            ])
            for output in previous_outputs:
                agent = output.get('agent', 'Unknown')
                summary = output.get('summary', 'No summary')
                context_parts.append(f"- {agent}: {summary}")

        context_parts.extend([
            "",
            "Build upon the previous work and ensure consistency.",
        ])

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
