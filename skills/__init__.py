"""Skills module - slash commands and tool capabilities."""

from .base import BaseSkill

# Import all skills
from .scaffold import ScaffoldReact, ScaffoldNextJS, ScaffoldFastAPI, ScaffoldExpress
from .analysis import DebugCode, AnalyzeError
from .testing import RunTests, GenerateTests
from .version import CheckVersions
from .security import SecurityScan

# Registry of all available skills
SKILL_REGISTRY = {
    # Scaffold skills
    "scaffold_react": ScaffoldReact,
    "scaffold_nextjs": ScaffoldNextJS,
    "scaffold_fastapi": ScaffoldFastAPI,
    "scaffold_express": ScaffoldExpress,
    # Analysis skills
    "debug_code": DebugCode,
    "analyze_error": AnalyzeError,
    # Testing skills
    "run_tests": RunTests,
    "generate_tests": GenerateTests,
    # Version skills
    "check_versions": CheckVersions,
    # Security skills
    "security_scan": SecurityScan,
}


def list_skills():
    """List all available skills."""
    skills = []
    for name, skill_class in SKILL_REGISTRY.items():
        skill = skill_class()
        skills.append(skill.to_dict())
    return skills


def get_skill(name: str):
    """Get a skill instance by name."""
    skill_class = SKILL_REGISTRY.get(name)
    if skill_class:
        return skill_class()
    return None


__all__ = [
    "BaseSkill",
    "SKILL_REGISTRY",
    "list_skills",
    "get_skill",
    # Scaffold
    "ScaffoldReact",
    "ScaffoldNextJS",
    "ScaffoldFastAPI",
    "ScaffoldExpress",
    # Analysis
    "DebugCode",
    "AnalyzeError",
    # Testing
    "RunTests",
    "GenerateTests",
    # Version
    "CheckVersions",
    # Security
    "SecurityScan",
]
