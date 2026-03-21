"""Skill registry — instantiate all skills and map them to agents."""

import re
from typing import Dict, List, Optional

from skills.base import BaseSkill
from skills.analysis.debug import DebugCode
from skills.analysis.error_analyzer import AnalyzeError
from skills.scaffold.react import ScaffoldReact
from skills.scaffold.express import ScaffoldExpress
from skills.scaffold.fastapi import ScaffoldFastAPI
from skills.scaffold.nextjs import ScaffoldNextJS
from skills.security.security_scan import SecurityScan
from skills.testing.generate_tests import GenerateTests
from skills.testing.run_tests import RunTests
from skills.version.check_versions import CheckVersions

# Agent → skill names they can use
AGENT_SKILL_AFFINITIES: Dict[str, List[str]] = {
    "react_developer": ["scaffold_react", "generate_tests", "debug_code"],
    "nextjs_developer": ["scaffold_nextjs", "generate_tests", "debug_code"],
    "nodejs_backend": ["scaffold_express", "generate_tests", "run_tests", "debug_code"],
    "python_backend": ["scaffold_fastapi", "generate_tests", "run_tests", "debug_code"],
    "fullstack_developer": ["scaffold_react", "scaffold_fastapi", "generate_tests", "debug_code"],
    "api_developer": ["scaffold_fastapi", "scaffold_express", "generate_tests", "debug_code"],
    "vue_developer": ["generate_tests", "debug_code"],
    "svelte_developer": ["generate_tests", "debug_code"],
    "go_backend": ["generate_tests", "run_tests", "debug_code"],
    "java_backend": ["generate_tests", "run_tests", "debug_code"],
    "dotnet_backend": ["generate_tests", "run_tests", "debug_code"],
    "rust_backend": ["generate_tests", "run_tests", "debug_code"],
    "php_developer": ["generate_tests", "debug_code"],
    "mobile_developer": ["generate_tests", "debug_code"],
    "flutter_developer": ["generate_tests", "debug_code"],
    "react_native_developer": ["scaffold_react", "generate_tests", "debug_code"],
    "android_developer": ["generate_tests", "debug_code"],
    "ios_developer": ["generate_tests", "debug_code"],
    "qa_engineer": ["generate_tests", "run_tests", "analyze_error"],
    "automation_qa": ["generate_tests", "run_tests", "analyze_error"],
    "sdet": ["generate_tests", "run_tests", "debug_code", "analyze_error"],
    "security_engineer": ["security_scan", "analyze_error"],
    "debugging_expert": ["debug_code", "analyze_error"],
    "performance_engineer": ["run_tests", "analyze_error"],
    "devops_engineer": ["run_tests", "check_versions"],
    "cloud_architect": ["check_versions"],
    "database_administrator": ["analyze_error"],
    "system_architect": [],
    "business_analyst": [],
    "product_manager": [],
    "delivery_manager": [],
    "technical_writer": [],
    "ui_ux_designer": [],
    "integration_specialist": ["generate_tests", "debug_code"],
    "tui_developer": ["generate_tests", "debug_code"],
    "cli_installer_developer": ["generate_tests", "run_tests", "debug_code"],
}

# Skill name → keywords that trigger auto-selection from arch spec
TECH_KEYWORDS: Dict[str, List[str]] = {
    "scaffold_react": ["react", "vite", "jsx", "tsx", "frontend", "spa"],
    "scaffold_nextjs": ["next.js", "nextjs", "next js", "ssr", "server-side rendering"],
    "scaffold_fastapi": ["fastapi", "fast api", "python api", "python backend", "uvicorn", "pydantic"],
    "scaffold_express": ["express", "node.js", "nodejs", "node backend", "javascript backend"],
    "generate_tests": ["test", "testing", "unit test", "integration test", "pytest", "jest", "vitest"],
    "run_tests": ["ci", "continuous integration", "test runner", "test suite", "coverage"],
    "security_scan": ["security", "auth", "authentication", "authorization", "jwt", "oauth", "owasp"],
    "debug_code": ["debug", "troubleshoot", "error handling", "logging"],
    "analyze_error": ["error", "exception", "stack trace", "bug", "crash"],
    "check_versions": ["version", "dependency", "upgrade", "migration", "compatibility"],
}


def build_skill_registry() -> Dict[str, BaseSkill]:
    """Instantiate all skills and return them keyed by name."""
    skills: List[BaseSkill] = [
        DebugCode(),
        AnalyzeError(),
        ScaffoldReact(),
        ScaffoldExpress(),
        ScaffoldFastAPI(),
        ScaffoldNextJS(),
        SecurityScan(),
        GenerateTests(),
        RunTests(),
        CheckVersions(),
    ]
    return {skill.name: skill for skill in skills}


def _keyword_matches(content: str, keywords: List[str]) -> bool:
    """Word-boundary-aware keyword match. Handles dotted names like 'next.js'."""
    for kw in keywords:
        pattern = r"(?<!\w)" + re.escape(kw) + r"(?!\w)"
        if re.search(pattern, content, re.IGNORECASE):
            return True
    return False


def skills_for_arch_spec(
    arch_spec_content: str,
    agent_name: str,
    skill_registry: Dict[str, BaseSkill],
) -> List[BaseSkill]:
    """Return skills relevant to the arch spec and within the agent's affinity set."""
    agent_affinities = set(AGENT_SKILL_AFFINITIES.get(agent_name, []))
    matched = []
    for skill_name, keywords in TECH_KEYWORDS.items():
        if skill_name not in agent_affinities:
            continue
        if _keyword_matches(arch_spec_content, keywords):
            skill = skill_registry.get(skill_name)
            if skill:
                matched.append(skill)
    return matched


def get_skill(skill_name: str, skill_registry: Dict[str, BaseSkill]) -> Optional[BaseSkill]:
    return skill_registry.get(skill_name)
