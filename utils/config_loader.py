"""Configuration loader for mageNT MCP server.

Loads and validates agent configuration from YAML files.
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


class ConfigLoader:
    """Loads and validates configuration from YAML files."""

    def __init__(self, config_path: Optional[str] = None):
        """Initialize the config loader.

        Args:
            config_path: Path to config.yaml. If None, searches in standard locations.
        """
        self.config_path = self._find_config(config_path)
        self.config = self._load_config()
        self._validate_config()

    def _find_config(self, config_path: Optional[str]) -> Path:
        """Find the configuration file.

        Args:
            config_path: Explicit path to config file, or None to search.

        Returns:
            Path to the configuration file.

        Raises:
            FileNotFoundError: If no config file is found.
        """
        if config_path:
            path = Path(config_path)
            if path.exists():
                return path
            raise FileNotFoundError(f"Config file not found: {config_path}")

        # Search in standard locations
        search_paths = [
            Path.cwd() / "config.yaml",
            Path.cwd() / "config.yml",
            Path(__file__).parent.parent / "config.yaml",
            Path(__file__).parent.parent / "config.yml",
        ]

        for path in search_paths:
            if path.exists():
                return path

        # If no config found, use example config as default
        example_config = Path(__file__).parent.parent / "config.example.yaml"
        if example_config.exists():
            print(f"No config.yaml found, using {example_config}")
            return example_config

        raise FileNotFoundError(
            "No config file found. Copy config.example.yaml to config.yaml"
        )

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file.

        Returns:
            Configuration dictionary.
        """
        with open(self.config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        return config or {}

    def _validate_config(self) -> None:
        """Validate the configuration structure."""
        required_sections = ['agents', 'llm', 'workflows', 'server']
        for section in required_sections:
            if section not in self.config:
                raise ValueError(f"Missing required section in config: {section}")

        # Validate agents section
        if not isinstance(self.config['agents'], dict):
            raise ValueError("'agents' section must be a dictionary")

        # Validate LLM section
        llm_config = self.config['llm']
        if 'mode' not in llm_config:
            raise ValueError("'llm.mode' is required")

        valid_modes = ['claude_pro', 'api', 'local']
        if llm_config['mode'] not in valid_modes:
            raise ValueError(f"'llm.mode' must be one of: {valid_modes}")

    def get_enabled_agents(self) -> Dict[str, Dict[str, Any]]:
        """Get all enabled agents.

        Returns:
            Dictionary of enabled agents with their configurations.
        """
        enabled = {}
        for agent_name, agent_config in self.config['agents'].items():
            if agent_config.get('enabled', False):
                enabled[agent_name] = agent_config
        return enabled

    def get_agent_config(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific agent.

        Args:
            agent_name: Name of the agent.

        Returns:
            Agent configuration or None if not found.
        """
        return self.config['agents'].get(agent_name)

    def is_agent_enabled(self, agent_name: str) -> bool:
        """Check if an agent is enabled.

        Args:
            agent_name: Name of the agent.

        Returns:
            True if agent is enabled, False otherwise.
        """
        agent_config = self.get_agent_config(agent_name)
        return agent_config.get('enabled', False) if agent_config else False

    def get_llm_config(self) -> Dict[str, Any]:
        """Get LLM configuration.

        Returns:
            LLM configuration dictionary.
        """
        return self.config['llm']

    def get_llm_mode(self) -> str:
        """Get the LLM mode (claude_pro, api, or local).

        Returns:
            LLM mode string.
        """
        return self.config['llm']['mode']

    def get_workflows(self) -> Dict[str, Dict[str, Any]]:
        """Get all workflow templates.

        Returns:
            Dictionary of workflow templates.
        """
        return self.config.get('workflows', {})

    def get_enabled_workflows(self) -> Dict[str, Dict[str, Any]]:
        """Get all enabled workflow templates.

        Returns:
            Dictionary of enabled workflows.
        """
        enabled = {}
        for workflow_name, workflow_config in self.get_workflows().items():
            if workflow_config.get('enabled', True):
                enabled[workflow_name] = workflow_config
        return enabled

    def get_workflow(self, workflow_name: str) -> Optional[Dict[str, Any]]:
        """Get a specific workflow template.

        Args:
            workflow_name: Name of the workflow.

        Returns:
            Workflow configuration or None if not found.
        """
        return self.get_workflows().get(workflow_name)

    def get_server_config(self) -> Dict[str, Any]:
        """Get server configuration.

        Returns:
            Server configuration dictionary.
        """
        return self.config.get('server', {
            'name': 'magent-mcp',
            'version': '0.1.0',
            'description': 'Multi-agent software development team MCP server'
        })

    def reload(self) -> None:
        """Reload configuration from file."""
        self.config = self._load_config()
        self._validate_config()
