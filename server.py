"""mageNT MCP Server - Multi-Agent Software Development Team.

This MCP server provides a complete software development team with specialized
agent roles accessible through Claude Desktop and Claude Code.

Works with ANY LLM that supports MCP - returns guidance that the calling LLM
can use to improve code quality and development workflows.
"""

import sys
from typing import Any, Dict, Optional, List

from mcp.server import Server
from mcp.types import Tool, TextContent

from utils.config_loader import ConfigLoader
from workflows.templates import WorkflowOrchestrator

# Import rules and hooks systems
from rules import RulesEngine, RulesConfig, RuleContext, RuleCategory, check_code
from hooks import HooksEngine, HooksConfig, HookContext, HookType, get_default_engine

# Import all agent types
# Business agents
from agents.business.business_analyst import BusinessAnalyst
from agents.business.product_manager import ProductManager
from agents.business.system_architect import SystemArchitect
from agents.business.ui_ux_designer import UIUXDesigner
from agents.business.technical_writer import TechnicalWriter

# Development agents
from agents.development.react_developer import ReactDeveloper
from agents.development.nodejs_backend import NodeJSBackend
from agents.development.fullstack_developer import FullStackDeveloper
from agents.development.nextjs_developer import NextJSDeveloper
from agents.development.python_backend import PythonBackend
from agents.development.api_developer import APIDeveloper
from agents.development.vue_developer import VueDeveloper
from agents.development.java_backend import JavaBackend
from agents.development.go_backend import GoBackend
from agents.development.dotnet_backend import DotNetBackend
from agents.development.mobile_developer import MobileDeveloper

# Data agents
from agents.data.database_administrator import DatabaseAdministrator

# Quality agents
from agents.quality.qa_engineer import QAEngineer
from agents.quality.security_engineer import SecurityEngineer
from agents.quality.performance_engineer import PerformanceEngineer
from agents.quality.automation_qa import AutomationQA
from agents.quality.debugging_expert import DebuggingExpert

# Infrastructure agents
from agents.infrastructure.devops_engineer import DevOpsEngineer
from agents.infrastructure.cloud_architect import CloudArchitect

# Map agent names to their classes
AGENT_CLASSES = {
    # Business
    "business_analyst": BusinessAnalyst,
    "product_manager": ProductManager,
    "system_architect": SystemArchitect,
    "ui_ux_designer": UIUXDesigner,
    "technical_writer": TechnicalWriter,
    # Development
    "react_developer": ReactDeveloper,
    "nodejs_backend": NodeJSBackend,
    "fullstack_developer": FullStackDeveloper,
    "nextjs_developer": NextJSDeveloper,
    "python_backend": PythonBackend,
    "api_developer": APIDeveloper,
    "vue_developer": VueDeveloper,
    "java_backend": JavaBackend,
    "go_backend": GoBackend,
    "dotnet_backend": DotNetBackend,
    "mobile_developer": MobileDeveloper,
    # Data
    "database_administrator": DatabaseAdministrator,
    # Quality
    "qa_engineer": QAEngineer,
    "security_engineer": SecurityEngineer,
    "performance_engineer": PerformanceEngineer,
    "automation_qa": AutomationQA,
    "debugging_expert": DebuggingExpert,
    # Infrastructure
    "devops_engineer": DevOpsEngineer,
    "cloud_architect": CloudArchitect,
}


class MageNTServer:
    """mageNT MCP Server implementation."""

    def __init__(self, config_path: Optional[str] = None):
        """Initialize the mageNT server.

        Args:
            config_path: Optional path to config.yaml
        """
        self.config_loader = ConfigLoader(config_path)
        self.agent_registry: Dict[str, Any] = {}
        self.server = Server("magent-mcp")

        # Load enabled agents
        self._load_agents()

        # Initialize workflow orchestrator
        workflows_config = self.config_loader.get_enabled_workflows()
        self.workflow_orchestrator = WorkflowOrchestrator(
            workflows_config, self.agent_registry
        )

        # Initialize rules engine
        self.rules_engine = RulesEngine()
        print(f"Rules engine loaded with {len(self.rules_engine.list_rules())} rules", file=sys.stderr)

        # Initialize hooks engine
        self.hooks_engine = get_default_engine()
        print(f"Hooks engine loaded with {len(self.hooks_engine.list_hooks())} hooks", file=sys.stderr)

        # Register MCP tools
        self._register_tools()

    def _load_agents(self) -> None:
        """Load all enabled agents from configuration."""
        enabled_agents = self.config_loader.get_enabled_agents()

        for agent_name, agent_config in enabled_agents.items():
            agent_class = AGENT_CLASSES.get(agent_name)
            if agent_class:
                agent = agent_class(agent_config)
                self.agent_registry[agent_name] = agent
                print(f"Loaded agent: {agent.role} ({agent_name})", file=sys.stderr)
            else:
                print(
                    f"Warning: Agent '{agent_name}' is enabled but not implemented yet",
                    file=sys.stderr,
                )

        print(f"Total agents loaded: {len(self.agent_registry)}", file=sys.stderr)

    def _register_tools(self) -> None:
        """Register all MCP tools for agents and workflows."""

        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            """List all available tools."""
            tools = []

            # Add agent consultation tools
            for agent_name, agent in self.agent_registry.items():
                tools.append(
                    Tool(
                        name=f"consult_{agent_name}",
                        description=agent.get_tool_description(),
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "task": {
                                    "type": "string",
                                    "description": f"The task or question for the {agent.role}",
                                },
                                "context": {
                                    "type": "string",
                                    "description": "Optional additional context or project information",
                                },
                            },
                            "required": ["task"],
                        },
                    )
                )

            # Add workflow tools
            tools.extend([
                Tool(
                    name="list_workflows",
                    description="List all available workflow templates for common project types",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                    },
                ),
                Tool(
                    name="start_workflow",
                    description="Start a workflow to guide multi-agent collaboration for a project",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "workflow_name": {
                                "type": "string",
                                "description": "Name of the workflow (e.g., 'full_stack_web', 'api_service')",
                            },
                            "task_description": {
                                "type": "string",
                                "description": "Description of the project or task",
                            },
                        },
                        "required": ["workflow_name", "task_description"],
                    },
                ),
                Tool(
                    name="list_agents",
                    description="List all available agents and their capabilities",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                    },
                ),
            ])

            # Add rules tools
            tools.extend([
                Tool(
                    name="check_code",
                    description="Check code against best practice rules (security, style, testing, performance). Returns violations and suggestions for improvement.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "code": {
                                "type": "string",
                                "description": "The code to check",
                            },
                            "file_path": {
                                "type": "string",
                                "description": "Optional file path for context (helps detect language)",
                            },
                            "categories": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Optional list of categories to check: security, coding_style, testing, git, performance",
                            },
                        },
                        "required": ["code"],
                    },
                ),
                Tool(
                    name="list_rules",
                    description="List all available code quality rules with their descriptions and categories",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                    },
                ),
                Tool(
                    name="get_rule_guidance",
                    description="Get detailed guidance for a specific rule including examples and best practices",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "rule_name": {
                                "type": "string",
                                "description": "Name of the rule (e.g., 'no-hardcoded-secrets', 'sql-injection-prevention')",
                            },
                        },
                        "required": ["rule_name"],
                    },
                ),
            ])

            # Add hooks tools
            tools.extend([
                Tool(
                    name="list_hooks",
                    description="List all available automation hooks and their status",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                    },
                ),
                Tool(
                    name="run_pre_commit_hooks",
                    description="Run pre-commit validation hooks to check commit message and staged changes",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "commit_message": {
                                "type": "string",
                                "description": "The commit message to validate",
                            },
                            "branch_name": {
                                "type": "string",
                                "description": "Current branch name",
                            },
                            "file_changes": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of changed file paths",
                            },
                        },
                        "required": ["commit_message"],
                    },
                ),
                Tool(
                    name="validate_code_edit",
                    description="Validate a code edit before applying it (checks security, style, etc.)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "Path to the file being edited",
                            },
                            "old_content": {
                                "type": "string",
                                "description": "Original file content",
                            },
                            "new_content": {
                                "type": "string",
                                "description": "New file content after edit",
                            },
                        },
                        "required": ["file_path", "new_content"],
                    },
                ),
            ])

            return tools

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Any) -> list[TextContent]:
            """Handle tool calls."""

            # Handle agent consultation tools
            if name.startswith("consult_"):
                agent_name = name.replace("consult_", "")
                agent = self.agent_registry.get(agent_name)

                if not agent:
                    return [
                        TextContent(
                            type="text",
                            text=f"Error: Agent '{agent_name}' not found or not enabled",
                        )
                    ]

                task = arguments.get("task", "")
                if not task or not isinstance(task, str) or not task.strip():
                    return [
                        TextContent(
                            type="text",
                            text="Error: 'task' argument is required and must be a non-empty string",
                        )
                    ]
                context = arguments.get("context")

                result = agent.process_request(task=task, context=context)

                # Return the guidance for Claude to follow
                response = [
                    TextContent(
                        type="text",
                        text=f"You are now consulting with the {agent.role}.\n\n{result['guidance']}",
                    )
                ]

                return response

            # Handle workflow tools
            elif name == "list_workflows":
                workflows = self.workflow_orchestrator.list_workflows()

                if not workflows:
                    return [
                        TextContent(
                            type="text",
                            text="No workflows are currently enabled.",
                        )
                    ]

                workflow_list = ["Available Workflows:\n"]
                for wf in workflows:
                    workflow_list.append(f"**{wf['name']}**")
                    workflow_list.append(f"  Description: {wf['description']}")
                    workflow_list.append(f"  Steps: {wf['steps']}")
                    workflow_list.append(f"  Agents: {wf['agents']}")
                    workflow_list.append("")

                return [TextContent(type="text", text="\n".join(workflow_list))]

            elif name == "start_workflow":
                workflow_name = arguments.get("workflow_name", "")
                task_description = arguments.get("task_description", "")

                if not workflow_name or not isinstance(workflow_name, str) or not workflow_name.strip():
                    return [
                        TextContent(
                            type="text",
                            text="Error: 'workflow_name' argument is required and must be a non-empty string",
                        )
                    ]
                if not task_description or not isinstance(task_description, str) or not task_description.strip():
                    return [
                        TextContent(
                            type="text",
                            text="Error: 'task_description' argument is required and must be a non-empty string",
                        )
                    ]

                # Validate workflow
                is_valid, validation_msg = self.workflow_orchestrator.validate_workflow(
                    workflow_name
                )

                if not is_valid:
                    return [
                        TextContent(
                            type="text",
                            text=f"Cannot start workflow: {validation_msg}",
                        )
                    ]

                # Generate workflow plan
                plan = self.workflow_orchestrator.get_workflow_plan(
                    workflow_name, task_description
                )

                response = [
                    TextContent(
                        type="text",
                        text=f"{plan}\n\nYou can now proceed to consult each agent in sequence using their respective tools.",
                    )
                ]

                return response

            elif name == "list_agents":
                if not self.agent_registry:
                    return [
                        TextContent(
                            type="text",
                            text="No agents are currently enabled. Check your config.yaml file.",
                        )
                    ]

                agent_list = ["Available Agents:\n"]
                for agent_name, agent in self.agent_registry.items():
                    agent_list.append(f"**{agent.role}** (`consult_{agent_name}`)")
                    agent_list.append(f"  Expertise: {agent.specialization}")
                    agent_list.append(f"  Level: {agent.expertise_level}")
                    agent_list.append("")

                return [TextContent(type="text", text="\n".join(agent_list))]

            # Handle rules tools
            elif name == "check_code":
                code = arguments.get("code", "")
                if not code or not isinstance(code, str):
                    return [
                        TextContent(
                            type="text",
                            text="Error: 'code' argument is required and must be a string",
                        )
                    ]
                file_path = arguments.get("file_path")
                categories = arguments.get("categories")

                # Build config if categories specified
                config = None
                if categories:
                    try:
                        enabled_cats = {RuleCategory(cat) for cat in categories if cat in [c.value for c in RuleCategory]}
                        if enabled_cats:
                            config = RulesConfig(enabled_categories=enabled_cats)
                    except ValueError:
                        pass

                engine = RulesEngine(config) if config else self.rules_engine
                report = engine.check_code(code, file_path)

                # Format response
                response_text = report.format_text()

                # Add guidance for violations
                if not report.passed:
                    response_text += "\n\n## Guidance for Fixing Issues:\n"
                    seen_rules = set()
                    for result in report.results:
                        if not result.passed and result.rule_name not in seen_rules:
                            guidance = engine.get_guidance(result.rule_name)
                            if guidance:
                                response_text += f"\n{guidance}\n"
                                seen_rules.add(result.rule_name)

                return [TextContent(type="text", text=response_text)]

            elif name == "list_rules":
                rules = self.rules_engine.list_rules()

                if not rules:
                    return [TextContent(type="text", text="No rules are currently enabled.")]

                # Group by category
                by_category: Dict[str, List] = {}
                for rule_name, info in rules.items():
                    cat = info["category"]
                    if cat not in by_category:
                        by_category[cat] = []
                    by_category[cat].append(info)

                lines = ["# Available Rules\n"]
                for category, category_rules in by_category.items():
                    lines.append(f"\n## {category.upper()}\n")
                    for rule in category_rules:
                        status = "✓" if rule["enabled"] else "✗"
                        lines.append(f"- **{rule['name']}** [{rule['severity']}] {status}")
                        lines.append(f"  {rule['description']}")

                return [TextContent(type="text", text="\n".join(lines))]

            elif name == "get_rule_guidance":
                rule_name = arguments.get("rule_name", "")
                if not rule_name or not isinstance(rule_name, str) or not rule_name.strip():
                    return [
                        TextContent(
                            type="text",
                            text="Error: 'rule_name' argument is required and must be a non-empty string",
                        )
                    ]
                guidance = self.rules_engine.get_guidance(rule_name)

                if guidance:
                    return [TextContent(type="text", text=guidance)]
                else:
                    return [TextContent(type="text", text=f"Rule '{rule_name}' not found. Use list_rules to see available rules.")]

            # Handle hooks tools
            elif name == "list_hooks":
                hooks = self.hooks_engine.list_hooks()

                if not hooks:
                    return [TextContent(type="text", text="No hooks are currently registered.")]

                # Group by hook type
                by_type: Dict[str, List] = {}
                for hook_name, info in hooks.items():
                    ht = info["hook_type"]
                    if ht not in by_type:
                        by_type[ht] = []
                    by_type[ht].append(info)

                lines = ["# Available Hooks\n"]
                for hook_type, type_hooks in by_type.items():
                    lines.append(f"\n## {hook_type.upper()}\n")
                    for hook in type_hooks:
                        status = "✓ enabled" if hook["enabled"] else "✗ disabled"
                        lines.append(f"- **{hook['name']}** ({status})")
                        lines.append(f"  {hook['description']}")

                return [TextContent(type="text", text="\n".join(lines))]

            elif name == "run_pre_commit_hooks":
                commit_message = arguments.get("commit_message", "")
                if not commit_message or not isinstance(commit_message, str) or not commit_message.strip():
                    return [
                        TextContent(
                            type="text",
                            text="Error: 'commit_message' argument is required and must be a non-empty string",
                        )
                    ]
                branch_name = arguments.get("branch_name")
                file_changes = arguments.get("file_changes", [])

                # Run pre-commit hooks (already in async context)
                report = await self.hooks_engine.execute_pre_commit(
                    commit_message=commit_message,
                    branch_name=branch_name,
                    file_changes=file_changes,
                )

                # Format response
                status = "✓ PASSED" if report.passed else "✗ BLOCKED"
                lines = [
                    f"# Pre-Commit Validation: {status}",
                    f"\nHooks run: {report.total_hooks_run}",
                    f"Successful: {report.successful}",
                    f"Failed: {report.failed}",
                ]

                if report.combined_message:
                    lines.append(f"\n## Details:\n{report.combined_message}")

                return [TextContent(type="text", text="\n".join(lines))]

            elif name == "validate_code_edit":
                file_path = arguments.get("file_path", "")
                if not file_path or not isinstance(file_path, str) or not file_path.strip():
                    return [
                        TextContent(
                            type="text",
                            text="Error: 'file_path' argument is required and must be a non-empty string",
                        )
                    ]
                old_content = arguments.get("old_content", "")
                new_content = arguments.get("new_content", "")
                if not new_content or not isinstance(new_content, str):
                    return [
                        TextContent(
                            type="text",
                            text="Error: 'new_content' argument is required and must be a string",
                        )
                    ]

                # Create hook context
                context = HookContext(
                    hook_type=HookType.PRE_EDIT,
                    file_path=file_path,
                    old_content=old_content,
                    new_content=new_content,
                )

                # Run validation (already in async context)
                report = await self.hooks_engine.execute(context)

                # Also run rules check on the new content
                rules_report = self.rules_engine.check_code(new_content, file_path)

                # Combine results
                status = "✓ VALID" if (report.passed and rules_report.passed) else "⚠ ISSUES FOUND"
                lines = [f"# Code Edit Validation: {status}\n"]

                if not rules_report.passed:
                    lines.append("## Code Quality Issues:")
                    lines.append(rules_report.format_text())

                if report.combined_message:
                    lines.append(f"\n## Hook Results:\n{report.combined_message}")

                if report.passed and rules_report.passed:
                    lines.append("No issues found. Code edit looks good!")

                return [TextContent(type="text", text="\n".join(lines))]

            else:
                return [
                    TextContent(
                        type="text",
                        text=f"Error: Unknown tool '{name}'",
                    )
                ]

    async def run(self) -> None:
        """Run the MCP server."""
        from mcp.server.stdio import stdio_server

        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options(),
            )


def main():
    """Main entry point for the server."""
    import asyncio

    # Allow optional config path as command-line argument
    config_path = sys.argv[1] if len(sys.argv) > 1 else None

    try:
        server = MageNTServer(config_path)
        print("mageNT MCP Server starting...", file=sys.stderr)
        asyncio.run(server.run())
    except Exception as e:
        print(f"Error starting server: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
