"""Base agent class for all specialized agents."""

import asyncio
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Sequence, Tuple

try:
    from utils.prompt_builder import PromptBuilder
except ImportError:
    from ..utils.prompt_builder import PromptBuilder


class BaseAgent(ABC):
    """Base class for all specialized agents.

    Each agent represents an expert team member with specific skills.
    Agents provide system prompts that guide Claude's responses.
    """

    # Class-level default; subclasses override per the seniority table.
    # Values: "principal", "staff", "senior", "" (empty = no level word in role line)
    expertise_level: str = "senior"

    def __init__(self, config: Dict[str, Any]):
        """Initialize the agent.

        Args:
            config: Agent configuration from config.yaml
        """
        self.config = config
        if 'expertise_level' in config:
            self.expertise_level = config['expertise_level']
        self.specialization = config.get('specialization', '')
        self.enabled = config.get('enabled', True)

    @property
    def team_model(self) -> str:
        """Claude model alias for Claude Code agent-team teammate spawning.

        Read by tools/generate_dispatch.py to emit the frontmatter `model:`
        field. Inert outside agent-teams context.
        """
        return {
            "principal": "opus",
            "staff": "opus",
            "senior": "sonnet",
            "": "sonnet",
        }.get(self.expertise_level, "sonnet")

    @property
    @abstractmethod
    def name(self) -> str:
        """Internal name of the agent (e.g., 'business_analyst')."""
        pass

    @property
    @abstractmethod
    def role(self) -> str:
        """Human-readable role (e.g., 'Business Analyst')."""
        pass

    @property
    @abstractmethod
    def responsibilities(self) -> List[str]:
        """List of key responsibilities for this agent."""
        pass

    @property
    def best_practices(self) -> List[str]:
        """Best practices this agent should follow.

        Override in subclasses to add specific practices.
        """
        return []

    @property
    def use_cases(self) -> List[str]:
        """When to use this agent.

        Override in subclasses to specify use cases.
        """
        return ["General tasks related to " + self.role]

    @property
    def capability_tags(self) -> List[str]:
        """Capability blocks to inject into the system prompt.

        Override in subclasses to select relevant domains.
        """
        return []

    @property
    def opinionated_stance(self) -> str:
        """One-sentence opinionated framing appended to the role line."""
        return ""

    @property
    def owned_scope(self) -> List[str]:
        """What this agent decides on. Defaults to ``responsibilities``."""
        return list(self.responsibilities)

    @property
    def deferred_scope(self) -> Sequence[Tuple[str, str]]:
        """``(topic, defer_to_agent)`` pairs the agent should hand off."""
        return []

    @property
    def process_steps(self) -> List[str]:
        """Numbered procedure the agent should follow on every task."""
        return []

    @property
    def decision_heuristics(self) -> List[str]:
        """Rules of thumb. Falls back to ``best_practices`` if not set."""
        return []

    @property
    def confidence_floor(self) -> str:
        """Minimum confidence below which findings are suppressed."""
        return "medium"

    @property
    def output_format(self) -> str:
        """Templated output schema (markdown)."""
        return ""

    @property
    def escalation_rules(self) -> List[str]:
        """Conditions under which the agent should punt to a human."""
        return []

    @property
    def examples(self) -> str:
        """Optional inline good/bad examples."""
        return ""

    @property
    def anti_examples(self) -> List[str]:
        """``Do NOT`` lines to ground the model away from common failure modes."""
        return []

    @property
    def forbidden_outputs(self) -> List[str]:
        """Phrases the agent must never emit (e.g. ``overall good effort``)."""
        return []

    @property
    def output_schema_class(self):
        """Pydantic model class describing the structured response shape.

        When set, ``PromptBuilder`` emits a JSON-Schema snippet under the
        ``<output_schema>`` tag and downstream code can validate responses via
        ``cls.model_validate_json(text)``.
        """
        return None

    def get_system_prompt(self, context: Optional[str] = None) -> str:
        return PromptBuilder.build_agent_prompt(
            role=self.role,
            expertise_level=self.expertise_level,
            specialization=self.specialization,
            responsibilities=self.responsibilities,
            best_practices=self.best_practices,
            context=context,
            capability_tags=self.capability_tags,
            opinionated_stance=self.opinionated_stance,
            owned_scope=self.owned_scope,
            deferred_scope=self.deferred_scope,
            process_steps=self.process_steps,
            decision_heuristics=self.decision_heuristics,
            confidence_floor=self.confidence_floor,
            output_format=self.output_format,
            escalation_rules=self.escalation_rules,
            examples=self.examples,
            anti_examples=self.anti_examples,
            forbidden_outputs=self.forbidden_outputs,
            output_schema_class=self.output_schema_class,
        )

    def get_tool_description(self) -> str:
        """Get the MCP tool description for this agent.

        Returns:
            Tool description string for MCP tool registration.
        """
        return PromptBuilder.format_tool_description(
            agent_name=self.name,
            agent_role=self.role,
            expertise=self.specialization or "General software development",
            use_cases=self.use_cases,
        )

    def process_request(
        self,
        task: str,
        context: Optional[str] = None,
        previous_outputs: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Process a request to this agent.

        This method combines the agent's system prompt with the task
        and returns guidance for Claude to respond as this agent.

        Args:
            task: The task or question for this agent
            context: Optional workflow or project context
            previous_outputs: Optional outputs from previous workflow steps

        Returns:
            Dictionary with prompt and metadata for Claude to use.
        """
        system_prompt = self.get_system_prompt(context)

        parts = [system_prompt, "---"]
        if previous_outputs:
            parts.append("Previous work:")
            for o in previous_outputs:
                parts.append(f"{o.get('agent')}: {o.get('result', '')}")
            parts.append("---")
        parts.append(task)

        return {
            "agent": self.name,
            "role": self.role,
            "system_prompt": system_prompt,
            "task": task,
            "guidance": "\n\n".join(parts),
        }

    def dispatch_to_llm(
        self,
        task: str,
        context: Optional[str] = None,
    ) -> Optional[str]:
        """Dispatch task to an LLM if llm_dispatch is enabled in config.

        Returns the LLM response string, or None if dispatch is disabled.
        """
        try:
            from utils.config_loader import ConfigLoader
        except ImportError:
            from ..utils.config_loader import ConfigLoader

        llm_config = ConfigLoader().get_llm_config()
        if not llm_config.get("llm_dispatch", False):
            return None

        try:
            from utils.llm_adapter import dispatch
        except ImportError:
            from ..utils.llm_adapter import dispatch

        system_prompt = self.get_system_prompt()
        return dispatch(self.name, system_prompt, task, context)

    async def dispatch_to_llm_async(
        self,
        task: str,
        context: Optional[str] = None,
    ) -> Optional[str]:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.dispatch_to_llm, task, context)

    def __repr__(self) -> str:
        """String representation of the agent."""
        return f"{self.__class__.__name__}(name='{self.name}', role='{self.role}')"
