"""Workflow template management and orchestration."""

from typing import Any, Dict, List, Optional

try:
    from utils.prompt_builder import PromptBuilder
except ImportError:
    from ..utils.prompt_builder import PromptBuilder


class WorkflowOrchestrator:
    """Orchestrates multi-agent workflows."""

    def __init__(self, workflows_config: Dict[str, Any], agent_registry: Dict[str, Any]):
        """Initialize the workflow orchestrator.

        Args:
            workflows_config: Workflow configurations from config.yaml
            agent_registry: Registry of available agents
        """
        self.workflows_config = workflows_config
        self.agent_registry = agent_registry

    def get_workflow(self, workflow_name: str) -> Optional[Dict[str, Any]]:
        """Get a workflow template by name.

        Args:
            workflow_name: Name of the workflow

        Returns:
            Workflow configuration or None if not found
        """
        return self.workflows_config.get(workflow_name)

    def list_workflows(self) -> List[Dict[str, str]]:
        """List all available workflows.

        Returns:
            List of workflow summaries with name, description, and steps
        """
        workflows = []
        for name, config in self.workflows_config.items():
            if config.get('enabled', True):
                steps = config.get('steps', [])
                agent_names = [step.get('agent', 'unknown') for step in steps]
                workflows.append({
                    'name': name,
                    'description': config.get('description', ''),
                    'steps': len(steps),
                    'agents': ', '.join(agent_names),
                })
        return workflows

    def get_workflow_plan(self, workflow_name: str, task_description: str) -> str:
        """Generate a workflow execution plan.

        Args:
            workflow_name: Name of the workflow
            task_description: Description of the task

        Returns:
            Formatted workflow plan as a string
        """
        workflow = self.get_workflow(workflow_name)
        if not workflow:
            return f"Error: Workflow '{workflow_name}' not found"

        steps = workflow.get('steps', [])
        if not steps:
            return f"Error: Workflow '{workflow_name}' has no steps"

        plan_parts = [
            f"Workflow: {workflow_name}",
            f"Description: {workflow.get('description', 'N/A')}",
            f"Task: {task_description}",
            "",
            "Execution Plan:",
            "",
        ]

        for i, step in enumerate(steps, 1):
            agent_name = step.get('agent', 'unknown')
            step_desc = step.get('description', 'No description')
            agent = self.agent_registry.get(agent_name)

            if agent:
                agent_role = agent.role
                plan_parts.append(f"{i}. {agent_role} ({agent_name})")
            else:
                plan_parts.append(f"{i}. {agent_name} (NOT ENABLED)")

            plan_parts.append(f"   Task: {step_desc}")
            plan_parts.append("")

        plan_parts.extend([
            "This workflow will guide you through each step.",
            "You can execute the workflow automatically or consult each agent manually.",
        ])

        return "\n".join(plan_parts)

    def generate_step_context(
        self,
        workflow_name: str,
        current_step: int,
        task_description: str,
        previous_outputs: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """Generate context for a workflow step.

        Args:
            workflow_name: Name of the workflow
            current_step: Current step number (1-indexed)
            task_description: Original task description
            previous_outputs: Outputs from previous steps

        Returns:
            Context string for the current step
        """
        workflow = self.get_workflow(workflow_name)
        if not workflow:
            return ""

        steps = workflow.get('steps', [])
        total_steps = len(steps)

        return PromptBuilder.build_workflow_context(
            workflow_name=workflow_name,
            current_step=current_step,
            total_steps=total_steps,
            previous_outputs=previous_outputs,
        )

    def validate_workflow(self, workflow_name: str) -> tuple[bool, str]:
        """Validate that a workflow can be executed.

        Args:
            workflow_name: Name of the workflow

        Returns:
            Tuple of (is_valid, error_message)
        """
        workflow = self.get_workflow(workflow_name)
        if not workflow:
            return False, f"Workflow '{workflow_name}' not found"

        if not workflow.get('enabled', True):
            return False, f"Workflow '{workflow_name}' is disabled"

        steps = workflow.get('steps', [])
        if not steps:
            return False, f"Workflow '{workflow_name}' has no steps"

        # Check if all required agents are enabled
        missing_agents = []
        for step in steps:
            agent_name = step.get('agent')
            if not agent_name:
                return False, "Workflow has a step without an agent"

            if agent_name not in self.agent_registry:
                missing_agents.append(agent_name)

        if missing_agents:
            return False, f"Required agents not enabled: {', '.join(missing_agents)}"

        return True, "Workflow is valid"

    def get_workflow_summary(self, workflow_name: str) -> str:
        """Get a human-readable summary of a workflow.

        Args:
            workflow_name: Name of the workflow

        Returns:
            Formatted summary string
        """
        workflow = self.get_workflow(workflow_name)
        if not workflow:
            return f"Workflow '{workflow_name}' not found"

        is_valid, validation_msg = self.validate_workflow(workflow_name)

        summary_parts = [
            f"Workflow: {workflow_name}",
            f"Description: {workflow.get('description', 'N/A')}",
            f"Status: {'Enabled' if workflow.get('enabled', True) else 'Disabled'}",
            f"Valid: {validation_msg}",
            "",
        ]

        steps = workflow.get('steps', [])
        if steps:
            summary_parts.append(f"Steps ({len(steps)}):")
            for i, step in enumerate(steps, 1):
                agent_name = step.get('agent', 'unknown')
                step_desc = step.get('description', 'No description')
                agent = self.agent_registry.get(agent_name)
                status = "✓" if agent else "✗"
                summary_parts.append(f"  {status} {i}. {agent_name}: {step_desc}")
        else:
            summary_parts.append("No steps defined")

        return "\n".join(summary_parts)
