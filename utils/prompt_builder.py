"""Prompt builder utilities for agent system prompts."""

from typing import Dict, List, Optional, Any


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
    ) -> str:
        """Build a system prompt for an agent.

        Args:
            role: The agent's role (e.g., "Business Analyst")
            expertise_level: Level of expertise (e.g., "senior", "principal")
            specialization: Specific areas of expertise
            responsibilities: List of key responsibilities
            best_practices: Optional list of best practices to follow
            context: Optional additional context

        Returns:
            Formatted system prompt string.
        """
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

        prompt_parts.extend([
            "",
            "As a principal-level engineer you bring deep mastery of:",
            "- Software design patterns (GoF: Creational, Structural, Behavioural; Architectural: CQRS, Event Sourcing, Saga, Strangler Fig, Sidecar)",
            "- Algorithm design and complexity analysis (Big-O, space/time trade-offs, dynamic programming, graph algorithms, concurrency patterns)",
            "- Engineering principles: SOLID, DRY, YAGNI, Law of Demeter, Separation of Concerns",
            "- Clean code, refactoring strategies, and technical debt management",
            "- Domain-Driven Design (bounded contexts, aggregates, ubiquitous language)",
        ])

        prompt_parts.extend([
            "",
            "Provide detailed, actionable guidance based on your expertise.",
            "Be specific and include code examples where appropriate.",
            "Consider edge cases and potential issues.",
        ])

        return "\n".join(prompt_parts)

    @staticmethod
    def build_workflow_context(
        workflow_name: str,
        current_step: int,
        total_steps: int,
        previous_outputs: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """Build context for a workflow step.

        Args:
            workflow_name: Name of the workflow
            current_step: Current step number (1-indexed)
            total_steps: Total number of steps
            previous_outputs: Optional list of previous step outputs

        Returns:
            Workflow context string.
        """
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
        """Format a tool description for MCP.

        Args:
            agent_name: Internal name of the agent
            agent_role: Human-readable role
            expertise: Areas of expertise
            use_cases: When to use this agent

        Returns:
            Formatted tool description.
        """
        desc_parts = [
            f"Consult the {agent_role} for guidance.",
            f"Expertise: {expertise}",
            "",
            "Use when:",
        ]

        for use_case in use_cases:
            desc_parts.append(f"- {use_case}")

        return "\n".join(desc_parts)
