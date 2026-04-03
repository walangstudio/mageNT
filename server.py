"""mageNT MCP Server - Multi-Agent Software Development Team.

This MCP server provides a complete software development team with specialized
agent roles accessible through Claude Desktop and Claude Code.

Works with ANY LLM that supports MCP - returns guidance that the calling LLM
can use to improve code quality and development workflows.
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional, List

from mcp.server import Server
from mcp.types import Tool, TextContent

from utils.config_loader import ConfigLoader
from workflows.templates import WorkflowOrchestrator
from utils.spec_store import SpecStore
from utils.skill_registry import build_skill_registry
from utils.parallel_orchestrator import ParallelOrchestrator
from utils.spec_builder import (
    build_requirements_spec_context,
    build_requirements_spec_task,
    build_arch_spec_task,
    build_audit_task,
    parse_audit_to_json,
)
from utils.mememo_client import MememoAdapter, format_memories
from utils.speckit_builder import (
    build_speckit_spec,
    build_speckit_plan,
    build_speckit_tasks,
    build_speckit_requirements_spec_task,
)

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
from agents.business.delivery_manager import DeliveryManager

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
from agents.development.integration_specialist import IntegrationSpecialist
from agents.development.rust_backend import RustBackend
from agents.development.svelte_developer import SvelteDeveloper
from agents.development.flutter_developer import FlutterDeveloper
from agents.development.react_native_developer import ReactNativeDeveloper
from agents.development.android_developer import AndroidDeveloper
from agents.development.ios_developer import IOSDeveloper
from agents.development.php_developer import PHPDeveloper
from agents.development.tui_developer import TUIDeveloper
from agents.development.cli_installer_developer import CLIInstallerDeveloper

# Data agents
from agents.data.database_administrator import DatabaseAdministrator

# Quality agents
from agents.quality.qa_engineer import QAEngineer
from agents.quality.security_engineer import SecurityEngineer
from agents.quality.performance_engineer import PerformanceEngineer
from agents.quality.automation_qa import AutomationQA
from agents.quality.sdet import SDET
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
    "delivery_manager": DeliveryManager,
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
    "integration_specialist": IntegrationSpecialist,
    "rust_backend": RustBackend,
    "svelte_developer": SvelteDeveloper,
    "flutter_developer": FlutterDeveloper,
    "react_native_developer": ReactNativeDeveloper,
    "android_developer": AndroidDeveloper,
    "ios_developer": IOSDeveloper,
    "php_developer": PHPDeveloper,
    "tui_developer": TUIDeveloper,
    "cli_installer_developer": CLIInstallerDeveloper,
    # Data
    "database_administrator": DatabaseAdministrator,
    # Quality
    "qa_engineer": QAEngineer,
    "security_engineer": SecurityEngineer,
    "performance_engineer": PerformanceEngineer,
    "automation_qa": AutomationQA,
    "sdet": SDET,
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

        # Initialize SDD components
        self.spec_store = SpecStore(Path(__file__).parent / "specs")
        self.skill_registry = build_skill_registry()
        self.parallel_orchestrator = ParallelOrchestrator(
            self.agent_registry, self.skill_registry, self.spec_store
        )
        print(f"SDD: {len(self.skill_registry)} skills loaded", file=sys.stderr)

        # Initialize rules engine
        self.rules_engine = RulesEngine()
        print(f"Rules engine loaded with {len(self.rules_engine.list_rules())} rules", file=sys.stderr)

        # Initialize hooks engine
        self.hooks_engine = get_default_engine()
        print(f"Hooks engine loaded with {len(self.hooks_engine.list_hooks())} hooks", file=sys.stderr)

        # Initialize mememo adapter (lazy -- embedding model loads on first use)
        self.mememo = MememoAdapter()
        if self.mememo.available:
            print("mememo: available (lazy init)", file=sys.stderr)

        # Session tracking for mememo persistence
        self._session_actions: list[str] = []
        self._session_context: str = ""

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
                                "format": {
                                    "type": "string",
                                    "enum": ["text", "json"],
                                    "description": "Output format. 'json' wraps response in structured JSON with agent, verdict, guidance fields. Default: 'text'.",
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

            # Add skill tools
            for skill_name, skill in self.skill_registry.items():
                tools.append(
                    Tool(
                        name=f"skill_{skill_name}",
                        description=skill.get_tool_description(),
                        inputSchema=skill.get_input_schema(),
                    )
                )

            # Add SDD tools
            tools.extend([
                Tool(
                    name="create_spec",
                    description="Generate a structured requirements spec for a project. Returns spec_id used by other SDD tools.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "project_name": {"type": "string", "description": "Name of the project"},
                            "description": {"type": "string", "description": "Brief project description"},
                            "requirements": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of requirements or acceptance criteria",
                            },
                            "spec_format": {
                                "type": "string",
                                "enum": ["default", "speckit"],
                                "description": "Output format. 'speckit' generates spec-kit compatible files (spec.md, plan.md, tasks/). Default: 'default'.",
                            },
                        },
                        "required": ["project_name", "description", "requirements"],
                    },
                ),
                Tool(
                    name="generate_speckit_tasks",
                    description="Generate spec-kit compatible task files from an existing spec and architecture spec. Creates tasks/ directory consumable by borch's spec converter.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "spec_id": {"type": "string", "description": "Spec ID returned by create_spec"},
                        },
                        "required": ["spec_id"],
                    },
                ),
                Tool(
                    name="create_arch_spec",
                    description="Generate a technical architecture spec from a requirements spec. Requires create_spec to have been called first.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "spec_id": {"type": "string", "description": "Spec ID returned by create_spec"},
                        },
                        "required": ["spec_id"],
                    },
                ),
                Tool(
                    name="run_parallel_agents",
                    description="Run multiple agents in parallel against the arch spec. Phase 'build' for implementation guidance, 'qa' for quality review.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "spec_id": {"type": "string", "description": "Spec ID returned by create_spec"},
                            "phase": {"type": "string", "description": "'build' or 'qa'"},
                            "agents": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Optional list of agent names. Auto-detected from arch spec if omitted.",
                            },
                        },
                        "required": ["spec_id", "phase"],
                    },
                ),
                Tool(
                    name="audit_spec",
                    description="Audit phase results against the original requirements checklist. Returns per-requirement MET/PARTIAL/MISSING status and a GO/NO_GO decision.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "spec_id": {"type": "string", "description": "Spec ID returned by create_spec"},
                            "phase_results": {
                                "type": "object",
                                "description": "Optional dict of agent_name -> result text. Loaded from last run_parallel_agents if omitted.",
                            },
                            "format": {
                                "type": "string",
                                "enum": ["markdown", "json"],
                                "description": "Output format. 'json' returns structured per-requirement status. Default: 'markdown'.",
                            },
                        },
                        "required": ["spec_id"],
                    },
                ),
                Tool(
                    name="list_specs",
                    description="List all spec-driven development specs created in this workspace.",
                    inputSchema={"type": "object", "properties": {}},
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

            # Add mememo tools (available even when mememo is not installed -- returns helpful message)
            tools.append(
                Tool(
                    name="recall_project_context",
                    description="Search project memory for relevant context, decisions, and prior work. Uses mememo for semantic search across persistent memories.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query (e.g., 'authentication decisions', 'recent spec audits')",
                            },
                            "top_k": {
                                "type": "integer",
                                "description": "Number of results (default: 5)",
                            },
                            "tags": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Filter by tags (AND logic)",
                            },
                        },
                        "required": ["query"],
                    },
                ),
            )

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
                output_format = arguments.get("format", "text")

                # Enrich context with mememo project memory
                if self.mememo.available:
                    memories = await self.mememo.recall_context(task, top_k=3)
                    if memories:
                        prior = format_memories(memories)
                        context = f"{context}\n\n## Prior Context\n{prior}" if context else f"## Prior Context\n{prior}"

                llm_result = agent.dispatch_to_llm(task=task, context=context)
                if llm_result is not None:
                    response_text = llm_result
                else:
                    result = agent.process_request(task=task, context=context)
                    response_text = result['guidance']

                # Track for session summary
                self._session_actions.append(f"Consulted {agent_name}: {task[:100]}")

                # Capture instincts from agent guidance (fire-and-forget)
                if self.mememo.available:
                    await self.mememo.capture(
                        pre_extracted=[{
                            "type": "analysis",
                            "content": f"[{agent_name}] {task[:200]}\n\n{response_text[:1000]}",
                            "tags": ["magent", "consult", agent_name],
                        }],
                    )

                if output_format == "json":
                    return [TextContent(type="text", text=json.dumps({
                        "agent": agent_name,
                        "verdict": "REVIEW",
                        "guidance": response_text,
                        "issues": [],
                        "suggestions": [],
                    }, indent=2))]

                return [TextContent(type="text", text=response_text)]

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

                tdd_nudge = (
                    "\n\n---\n💡 **Would you like to follow Test-Driven Development (TDD)?**\n"
                    "Use `start_workflow` with `workflow_name: tdd` to apply a red-green-refactor cycle instead. "
                    "TDD works well for this type of project — it's entirely optional."
                ) if workflow_name != "tdd" else ""

                response = [
                    TextContent(
                        type="text",
                        text=f"{plan}\n\nYou can now proceed to consult each agent in sequence using their respective tools.{tdd_nudge}",
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
                    agent_list.append(f"  Level: {agent.expertise_level.capitalize()}")
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

            # Handle skill tools
            elif name.startswith("skill_"):
                skill_name = name.removeprefix("skill_")
                skill = self.skill_registry.get(skill_name)
                if not skill:
                    return [TextContent(type="text", text=f"Error: Skill '{skill_name}' not found")]
                result = skill.execute(**arguments)
                return [TextContent(type="text", text=result["guidance"])]

            # Handle SDD tools
            elif name == "create_spec":
                project_name = arguments.get("project_name", "").strip()
                description = arguments.get("description", "").strip()
                requirements = arguments.get("requirements", [])
                spec_format = arguments.get("spec_format", "default")
                if isinstance(requirements, str):
                    requirements = [line.strip() for line in requirements.splitlines() if line.strip()]
                if not project_name:
                    return [TextContent(type="text", text="Error: 'project_name' is required")]
                if not requirements:
                    return [TextContent(type="text", text="Error: 'requirements' must be a non-empty list")]

                spec_id = SpecStore.make_spec_id(project_name)

                if spec_format == "speckit":
                    # Generate spec-kit compatible output
                    spec_content = build_speckit_spec(project_name, description, requirements)

                    # Refine via BA if LLM dispatch available
                    ba = self.agent_registry.get("business_analyst")
                    if ba:
                        task = build_speckit_requirements_spec_task()
                        context = build_requirements_spec_context(project_name, description, requirements)
                        llm_result = ba.dispatch_to_llm(task=task, context=context)
                        if llm_result:
                            spec_content = llm_result

                    spec_path = self.spec_store.create_speckit(spec_id, project_name, spec_content)
                    refinement = spec_content
                else:
                    # Default format
                    spec_path = self.spec_store.create(spec_id, project_name, description, requirements)

                    ba = self.agent_registry.get("business_analyst")
                    refinement = ""
                    if ba:
                        task = build_requirements_spec_task()
                        context = build_requirements_spec_context(project_name, description, requirements)
                        llm_result = ba.dispatch_to_llm(task=task, context=context)
                        if llm_result:
                            spec_path.write_text(llm_result, encoding="utf-8")
                            refinement = llm_result
                        else:
                            refinement = spec_path.read_text(encoding="utf-8")
                    else:
                        refinement = spec_path.read_text(encoding="utf-8")

                tdd_nudge = (
                    "\n\n---\n💡 **Would you like to follow Test-Driven Development (TDD)?**\n"
                    "Use `start_workflow` with `workflow_name: tdd` to apply a red-green-refactor cycle for this project. "
                    "It's entirely optional — you can proceed with `create_arch_spec` to continue the standard spec-driven flow."
                )

                # Store spec creation in mememo
                self._session_actions.append(f"Created spec {spec_id}: {project_name} (format: {spec_format})")
                if self.mememo.available:
                    await self.mememo.store_memory(
                        content=f"Created spec {spec_id}: {project_name}\n{description}",
                        type="context",
                        tags=["magent", "spec", spec_id],
                    )

                return [TextContent(type="text", text="\n".join([
                    f"# Spec Created",
                    f"spec_id: {spec_id}",
                    f"format: {spec_format}",
                    f"path: {spec_path}",
                    f"",
                    refinement,
                ]) + tdd_nudge)]

            elif name == "generate_speckit_tasks":
                spec_id = arguments.get("spec_id", "").strip()
                if not spec_id:
                    return [TextContent(type="text", text="Error: 'spec_id' is required")]
                if not self.spec_store.exists(spec_id):
                    return [TextContent(type="text", text=f"Error: Spec '{spec_id}' not found. Run create_spec first.")]

                spec_data = self.spec_store.load(spec_id)
                try:
                    arch_data = self.spec_store.load_arch_spec(spec_id)
                    arch_content = arch_data["content"]
                except Exception:
                    arch_content = ""

                # Generate plan.md
                project_name = spec_data["meta"].get("project_name", spec_id)
                plan_content = build_speckit_plan(project_name, spec_data["content"], arch_content)
                plan_path = self.spec_store.save_speckit_plan(spec_id, plan_content)

                # Generate task files
                tasks = build_speckit_tasks(spec_data["content"], arch_content)
                task_paths = self.spec_store.save_speckit_tasks(spec_id, tasks)

                self._session_actions.append(f"Generated speckit tasks for {spec_id}: {len(task_paths)} tasks")

                lines = [
                    f"# spec-kit Tasks Generated",
                    f"spec_id: {spec_id}",
                    f"plan: {plan_path}",
                    f"tasks: {len(task_paths)} files",
                    "",
                ]
                for p in task_paths:
                    lines.append(f"- {p.name}")

                return [TextContent(type="text", text="\n".join(lines))]

            elif name == "create_arch_spec":
                spec_id = arguments.get("spec_id", "").strip()
                if not spec_id:
                    return [TextContent(type="text", text="Error: 'spec_id' is required")]
                if not self.spec_store.exists(spec_id):
                    return [TextContent(type="text", text=f"Error: Spec '{spec_id}' not found. Run create_spec first.")]

                spec_data = self.spec_store.load(spec_id)
                task = build_arch_spec_task()

                arch = self.agent_registry.get("system_architect")
                if arch:
                    # requirements spec is the context; task is the instruction
                    llm_result = arch.dispatch_to_llm(task=task, context=spec_data["content"])
                    arch_content = llm_result if llm_result else arch.process_request(task=task, context=spec_data["content"])["guidance"]
                else:
                    arch_content = f"# Architecture Spec\n\n(system_architect agent not available — enable it in config.yaml)\n\n## Requirements Reference\n\n{spec_data['content']}"

                arch_path = self.spec_store.save_arch_spec(spec_id, arch_content)

                return [TextContent(type="text", text="\n".join([
                    f"# Architecture Spec Created",
                    f"spec_id: {spec_id}",
                    f"path: {arch_path}",
                    f"",
                    arch_content,
                ]))]

            elif name == "run_parallel_agents":
                spec_id = arguments.get("spec_id", "").strip()
                phase = arguments.get("phase", "build").strip()
                agents = arguments.get("agents")

                if not spec_id:
                    return [TextContent(type="text", text="Error: 'spec_id' is required")]
                if phase not in ("build", "qa"):
                    return [TextContent(type="text", text="Error: 'phase' must be 'build' or 'qa'")]
                if agents is not None and not agents:
                    return [TextContent(type="text", text="Error: 'agents' must be a non-empty list or omitted for auto-detection")]
                if not self.spec_store.exists(spec_id):
                    return [TextContent(type="text", text=f"Error: Spec '{spec_id}' not found")]
                if not self.spec_store.arch_spec_exists(spec_id):
                    return [TextContent(type="text", text=f"Error: arch_spec.md not found for '{spec_id}'. Run create_arch_spec first.")]

                outcome = await self.parallel_orchestrator.run_phase(spec_id, phase, agents)

                lines = [
                    f"# Parallel Agent Run: {phase.upper()}",
                    f"spec_id: {spec_id}",
                    f"duration_ms: {outcome['duration_ms']}",
                    f"agents: {', '.join(outcome['results'].keys())}",
                    "",
                ]
                for agent_name, result in outcome["results"].items():
                    agent = self.agent_registry.get(agent_name)
                    display_name = agent.role if agent else agent_name.replace("_", " ").title()
                    skills = outcome["skills_invoked"].get(agent_name, [])
                    lines.append(f"## {display_name}")
                    if skills:
                        lines.append(f"_Skills invoked: {', '.join(skills)}_")
                    lines.append(result)
                    lines.append("")

                return [TextContent(type="text", text="\n".join(lines))]

            elif name == "audit_spec":
                spec_id = arguments.get("spec_id", "").strip()
                phase_results = arguments.get("phase_results")
                output_format = arguments.get("format", "markdown")

                if not spec_id:
                    return [TextContent(type="text", text="Error: 'spec_id' is required")]
                if not self.spec_store.exists(spec_id):
                    return [TextContent(type="text", text=f"Error: Spec '{spec_id}' not found")]

                spec_data = self.spec_store.load(spec_id)
                try:
                    arch_data = self.spec_store.load_arch_spec(spec_id)
                    arch_content = arch_data["content"]
                except Exception:
                    arch_content = "(arch spec not available)"

                if not phase_results:
                    phase_results = self.spec_store.load_all_phase_results(spec_id)
                if not phase_results:
                    return [TextContent(type="text", text="Error: No phase results found for this spec. Run run_parallel_agents first.")]

                audit_prompt = build_audit_task(spec_data["content"], arch_content, phase_results)

                dm = self.agent_registry.get("delivery_manager")
                if dm:
                    llm_result = dm.dispatch_to_llm(task=audit_prompt)
                    audit_text = llm_result if llm_result else dm.process_request(task=audit_prompt)["guidance"]
                else:
                    audit_text = audit_prompt

                # Store audit decision in mememo
                audit_json = parse_audit_to_json(audit_text, spec_id)
                go_no_go = audit_json.get("go_no_go", "NO-GO") if audit_json.get("status") != "GUIDANCE_ONLY" else "GUIDANCE_ONLY"
                self._session_actions.append(f"Audit {spec_id}: {go_no_go}")
                if self.mememo.available and go_no_go != "GUIDANCE_ONLY":
                    await self.mememo.store_decision(
                        problem=f"Delivery readiness for {spec_id}",
                        alternatives=["Ship as-is", "Fix gaps first"],
                        chosen=go_no_go,
                        rationale=audit_json.get("summary", audit_text[:500]),
                        tags=["magent", "audit", spec_id],
                    )

                if output_format == "json":
                    return [TextContent(type="text", text=json.dumps(audit_json, indent=2))]

                return [TextContent(type="text", text="\n".join([
                    f"# Delivery Audit: {spec_id}",
                    "",
                    audit_text,
                ]))]

            elif name == "list_specs":
                specs = self.spec_store.list_specs()
                if not specs:
                    return [TextContent(type="text", text="No specs found. Use create_spec to start.")]
                lines = ["# Specs\n"]
                for s in specs:
                    lines.append(f"- **{s.get('project_name', '?')}** (`{s.get('spec_id', '?')}`) — status: {s.get('status', '?')}")
                return [TextContent(type="text", text="\n".join(lines))]

            elif name == "recall_project_context":
                query = arguments.get("query", "").strip()
                if not query:
                    return [TextContent(type="text", text="Error: 'query' is required")]

                if not self.mememo.available:
                    return [TextContent(type="text", text="mememo is not available. Install mememo in the same Python environment to enable project memory.")]

                top_k = arguments.get("top_k", 5)
                tags = arguments.get("tags")
                memories = await self.mememo.recall_context(query, top_k=top_k, tags=tags)

                if not memories:
                    return [TextContent(type="text", text="No relevant context found.")]

                lines = [f"# Project Context ({len(memories)} results)\n"]
                for m in memories:
                    sim = f"{m.get('similarity', 0):.2f}"
                    mtype = m.get("type", "?")
                    mtags = m.get("tags", [])
                    tag_str = f" [{', '.join(mtags)}]" if mtags else ""
                    lines.append(f"### [{mtype}]{tag_str} (similarity: {sim})")
                    lines.append(m.get("content", "")[:1000])
                    lines.append("")
                return [TextContent(type="text", text="\n".join(lines))]

            else:
                return [
                    TextContent(
                        type="text",
                        text=f"Error: Unknown tool '{name}'",
                    )
                ]

    def _build_session_summary(self) -> str:
        if not self._session_actions:
            return "No actions recorded."
        lines = [f"mageNT session ({len(self._session_actions)} actions):"]
        for action in self._session_actions[-50:]:  # cap at 50
            lines.append(f"- {action}")
        return "\n".join(lines)

    async def run(self) -> None:
        """Run the MCP server."""
        from mcp.server.stdio import stdio_server

        # Recall recent project context from mememo on start
        if self.mememo.available:
            memories = await self.mememo.recall_context(
                "recent work, decisions, and project context", top_k=5
            )
            if memories:
                self._session_context = format_memories(memories)
                print(f"mememo: recalled {len(memories)} context memories", file=sys.stderr)

        try:
            async with stdio_server() as (read_stream, write_stream):
                await self.server.run(
                    read_stream,
                    write_stream,
                    self.server.create_initialization_options(),
                )
        finally:
            # Persist session summary to mememo on shutdown
            if self.mememo.available and self._session_actions:
                await self.mememo.end_session(
                    summary=self._build_session_summary(),
                    tags=["magent-session"],
                )


def main():
    """Main entry point for the server."""
    import argparse
    import asyncio
    from utils.config_loader import set_global_override

    parser = argparse.ArgumentParser(description="mageNT MCP Server")
    parser.add_argument("config", nargs="?", default=None, help="Path to config.yaml")
    parser.add_argument(
        "--llm-dispatch", action="store_true",
        help="Enable LLM dispatch (overrides config.yaml llm_dispatch setting)",
    )
    args = parser.parse_args()

    if args.llm_dispatch:
        set_global_override("llm_dispatch", True)

    try:
        server = MageNTServer(args.config)
        print("mageNT MCP Server starting...", file=sys.stderr)
        if args.llm_dispatch:
            print("LLM dispatch: enabled via --llm-dispatch flag", file=sys.stderr)
        asyncio.run(server.run())
    except Exception as e:
        print(f"Error starting server: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
