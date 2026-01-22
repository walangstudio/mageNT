"""Test script to validate mageNT installation and configuration."""

import sys
import io
from pathlib import Path

# Ensure UTF-8 output on Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def test_imports():
    """Test that all required modules can be imported."""
    print("Testing imports...")
    try:
        import yaml
        print("  ✓ yaml")
    except ImportError as e:
        print(f"  ✗ yaml - {e}")
        return False

    try:
        import mcp
        print("  ✓ mcp")
    except ImportError as e:
        print(f"  ✗ mcp - {e}")
        return False

    try:
        from utils.config_loader import ConfigLoader
        print("  ✓ utils.config_loader")
    except ImportError as e:
        print(f"  ✗ utils.config_loader - {e}")
        return False

    try:
        from agents.base import BaseAgent
        print("  ✓ agents.base")
    except ImportError as e:
        print(f"  ✗ agents.base - {e}")
        return False

    try:
        from agents.business.business_analyst import BusinessAnalyst
        print("  ✓ agents.business.business_analyst")
    except ImportError as e:
        print(f"  ✗ agents.business.business_analyst - {e}")
        return False

    return True


def test_config():
    """Test configuration loading."""
    print("\nTesting configuration...")
    try:
        from utils.config_loader import ConfigLoader

        config = ConfigLoader()
        print(f"  ✓ Config loaded from: {config.config_path}")

        enabled_agents = config.get_enabled_agents()
        print(f"  ✓ Enabled agents: {len(enabled_agents)}")

        for agent_name in enabled_agents:
            print(f"    - {agent_name}")

        workflows = config.get_enabled_workflows()
        print(f"  ✓ Enabled workflows: {len(workflows)}")

        for workflow_name in workflows:
            print(f"    - {workflow_name}")

        return True
    except Exception as e:
        print(f"  ✗ Config error: {e}")
        return False


def test_agents():
    """Test agent instantiation."""
    print("\nTesting agent creation...")
    try:
        from agents.business.business_analyst import BusinessAnalyst
        from agents.development.react_developer import ReactDeveloper
        from agents.development.nodejs_backend import NodeJSBackend
        from agents.quality.automation_qa import AutomationQA
        from agents.quality.debugging_expert import DebuggingExpert

        test_config = {
            "enabled": True,
            "expertise_level": "senior",
            "specialization": "Test"
        }

        agents = [
            ("BusinessAnalyst", BusinessAnalyst),
            ("ReactDeveloper", ReactDeveloper),
            ("NodeJSBackend", NodeJSBackend),
            ("AutomationQA", AutomationQA),
            ("DebuggingExpert", DebuggingExpert),
        ]

        for agent_name, agent_class in agents:
            agent = agent_class(test_config)
            print(f"  ✓ {agent_name}: {agent.role}")
            prompt = agent.get_system_prompt()
            if len(prompt) > 0:
                print(f"    - System prompt: {len(prompt)} chars")
            else:
                print(f"    ✗ System prompt is empty")
                return False

        return True
    except Exception as e:
        print(f"  ✗ Agent creation error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_skills():
    """Test skills system."""
    print("\nTesting skills system...")
    try:
        from skills import list_skills, get_skill, SKILL_REGISTRY

        skills = list_skills()
        print(f"  ✓ Skills loaded: {len(skills)}")

        for skill_info in skills:
            print(f"    - {skill_info['slash_command']}: {skill_info['name']}")

        # Test a specific skill
        scaffold_react = get_skill("scaffold_react")
        if scaffold_react:
            result = scaffold_react.execute(project_name="test-app")
            if result.get("success"):
                print(f"  ✓ scaffold_react executed successfully")
            else:
                print(f"  ✗ scaffold_react execution failed")
                return False
        else:
            print(f"  ✗ scaffold_react skill not found")
            return False

        return True
    except Exception as e:
        print(f"  ✗ Skills error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_version_provider():
    """Test version provider."""
    print("\nTesting version provider...")
    try:
        from utils.version_provider import VersionProvider

        provider = VersionProvider()
        print("  ✓ VersionProvider initialized")

        # Note: Actual network requests are skipped in test to avoid dependencies
        # Just verify the class is importable and instantiable
        print("  ✓ Version provider ready (network tests skipped)")

        return True
    except Exception as e:
        print(f"  ✗ Version provider error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_server_init():
    """Test server initialization."""
    print("\nTesting server initialization...")
    try:
        # Don't actually run the server, just test initialization
        from utils.config_loader import ConfigLoader
        from workflows.templates import WorkflowOrchestrator

        config = ConfigLoader()
        print("  ✓ ConfigLoader initialized")

        enabled_agents = config.get_enabled_agents()
        workflows = config.get_enabled_workflows()

        # Mock agent registry
        agent_registry = {}
        orchestrator = WorkflowOrchestrator(workflows, agent_registry)
        print("  ✓ WorkflowOrchestrator initialized")

        workflow_list = orchestrator.list_workflows()
        print(f"  ✓ Workflows available: {len(workflow_list)}")

        return True
    except Exception as e:
        print(f"  ✗ Server initialization error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("mageNT Installation Test")
    print("=" * 60)

    results = []

    results.append(("Imports", test_imports()))
    results.append(("Configuration", test_config()))
    results.append(("Agents", test_agents()))
    results.append(("Skills", test_skills()))
    results.append(("Version Provider", test_version_provider()))
    results.append(("Server", test_server_init()))

    print("\n" + "=" * 60)
    print("Test Results")
    print("=" * 60)

    all_passed = True
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")
        if not passed:
            all_passed = False

    print("=" * 60)

    if all_passed:
        print("\n✓ All tests passed! mageNT is ready to use.")
        print("\nNext steps:")
        print("1. Add mageNT to your Claude Desktop config (see SETUP.md)")
        print("2. Restart Claude Desktop")
        print("3. Try: 'Can you list the available agents?'")
        return 0
    else:
        print("\n✗ Some tests failed. Please check the errors above.")
        print("\nCommon fixes:")
        print("- Run: pip install -r requirements.txt")
        print("- Check config.yaml exists and is valid")
        print("- See SETUP.md for detailed troubleshooting")
        return 1


if __name__ == "__main__":
    sys.exit(main())
