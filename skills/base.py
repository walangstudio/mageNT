"""Base class for all skills."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BaseSkill(ABC):
    """Abstract base class for all skills.

    Skills are self-contained actions that can be invoked via
    slash commands or MCP tools. Each skill provides guidance
    and templates for specific development tasks.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for the skill (used in tool registration)."""
        pass

    @property
    @abstractmethod
    def slash_command(self) -> str:
        """Slash command to invoke this skill (e.g., '/scaffold-react')."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Short description of what this skill does."""
        pass

    @property
    @abstractmethod
    def category(self) -> str:
        """Category of the skill (scaffold, analysis, testing, version, security)."""
        pass

    @property
    def parameters(self) -> List[Dict[str, Any]]:
        """List of parameters this skill accepts.

        Returns:
            List of dicts with 'name', 'type', 'description', 'required' keys.
        """
        return []

    @property
    def allowed_tools(self) -> List[str]:
        """Claude Code tools this skill is allowed to invoke.

        Consumed by tools/generate_dispatch.py to populate the SKILL.md
        ``allowed-tools`` frontmatter. Default to read-only review tools;
        scaffold/edit skills should override.
        """
        return ["Read", "Grep", "Glob", "Bash"]

    @property
    def when_to_activate(self) -> List[str]:
        """Bullet points for the skill's "When to Activate" section."""
        return []

    @property
    def workflow(self) -> List[str]:
        """Numbered steps for the skill's workflow body."""
        return []

    @property
    def output_schema(self) -> str:
        """Templated output the skill should produce. Empty = none."""
        return ""

    @abstractmethod
    def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the skill with given parameters.

        Returns:
            Dict containing:
                - 'guidance': Instructions/templates for Claude to follow
                - 'context': Additional context or metadata
                - 'success': Boolean indicating if skill executed successfully
        """
        pass

    def get_tool_description(self) -> str:
        """Generate MCP tool description."""
        return f"{self.description}\n\nSlash command: {self.slash_command}"

    def get_input_schema(self) -> Dict[str, Any]:
        """Generate MCP tool input schema."""
        properties = {}
        required = []

        for param in self.parameters:
            properties[param["name"]] = {
                "type": param.get("type", "string"),
                "description": param.get("description", ""),
            }
            if param.get("required", False):
                required.append(param["name"])

        return {
            "type": "object",
            "properties": properties,
            "required": required,
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert skill to dictionary representation."""
        return {
            "name": self.name,
            "slash_command": self.slash_command,
            "description": self.description,
            "category": self.category,
            "parameters": self.parameters,
        }
