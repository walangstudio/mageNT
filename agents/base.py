"""Base agent class for all specialized agents."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

try:
    from utils.prompt_builder import PromptBuilder
except ImportError:
    from ..utils.prompt_builder import PromptBuilder


class BaseAgent(ABC):
    """Base class for all specialized agents.

    Each agent represents an expert team member with specific skills.
    Agents provide system prompts that guide Claude's responses.
    """

    def __init__(self, config: Dict[str, Any]):
        """Initialize the agent.

        Args:
            config: Agent configuration from config.yaml
        """
        self.config = config
        self.expertise_level = config.get('expertise_level', 'senior')
        self.specialization = config.get('specialization', '')
        self.enabled = config.get('enabled', True)

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

    def get_system_prompt(self, context: Optional[str] = None) -> str:
        """Generate the system prompt for this agent.

        Args:
            context: Optional additional context (e.g., workflow state)

        Returns:
            System prompt string that guides Claude's responses.
        """
        return PromptBuilder.build_agent_prompt(
            role=self.role,
            expertise_level=self.expertise_level,
            specialization=self.specialization,
            responsibilities=self.responsibilities,
            best_practices=self.best_practices,
            context=context,
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

        # Build the full context
        full_context = []
        if previous_outputs:
            full_context.append("=== Previous Work ===")
            for output in previous_outputs:
                agent_name = output.get('agent', 'Unknown')
                result = output.get('result', 'No output')
                full_context.append(f"\n{agent_name}:\n{result}\n")

        if context:
            full_context.append(f"=== Additional Context ===\n{context}\n")

        full_context.append(f"=== Your Task ===\n{task}")

        return {
            "agent": self.name,
            "role": self.role,
            "system_prompt": system_prompt,
            "task": task,
            "full_context": "\n".join(full_context),
            "guidance": (
                f"Respond as a {self.expertise_level} {self.role}. "
                f"{system_prompt}\n\n"
                f"Now address this task:\n{task}"
            ),
        }

    def __repr__(self) -> str:
        """String representation of the agent."""
        return f"{self.__class__.__name__}(name='{self.name}', role='{self.role}')"
