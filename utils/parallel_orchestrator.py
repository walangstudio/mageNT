"""Parallel orchestrator — run multiple agents concurrently via asyncio.gather."""

import asyncio
import re
import time
from typing import Any, Dict, List, Optional

from utils.spec_store import SpecStore
from utils.skill_registry import skills_for_arch_spec
from utils.spec_builder import build_agent_phase_task

# Per-agent LLM timeout (seconds). Prevents one slow provider from blocking all others.
_AGENT_TIMEOUT_S = 90.0

_DEFAULT_BUILD_AGENTS = [
    "system_architect",
    "react_developer",
    "python_backend",
    "ui_ux_designer",
    "database_administrator",
]
_DEFAULT_QA_AGENTS = ["qa_engineer", "security_engineer"]

# Tech keyword → agent names. Uses word-boundary matching — see _kw_match().
_KEYWORD_TO_AGENT: Dict[str, List[str]] = {
    "react": ["react_developer"],
    "next.js": ["nextjs_developer"],
    "nextjs": ["nextjs_developer"],
    "vue": ["vue_developer"],
    "svelte": ["svelte_developer"],
    "node.js": ["nodejs_backend"],
    "express": ["nodejs_backend"],
    "python": ["python_backend"],
    "fastapi": ["python_backend"],
    "django": ["python_backend"],
    "flask": ["python_backend"],
    "java": ["java_backend"],
    "spring": ["java_backend"],
    "golang": ["go_backend"],
    "rust": ["rust_backend"],
    ".net": ["dotnet_backend"],
    "dotnet": ["dotnet_backend"],
    "php": ["php_developer"],
    "laravel": ["php_developer"],
    "flutter": ["flutter_developer"],
    "react native": ["react_native_developer"],
    "android": ["android_developer"],
    "ios": ["ios_developer"],
    "swift": ["ios_developer"],
    "kotlin": ["android_developer"],
    "postgresql": ["database_administrator"],
    "mysql": ["database_administrator"],
    "mongodb": ["database_administrator"],
    "redis": ["database_administrator"],
    "kubernetes": ["devops_engineer", "cloud_architect"],
    "docker": ["devops_engineer"],
    "aws": ["cloud_architect"],
    "gcp": ["cloud_architect"],
    "azure": ["cloud_architect"],
    "graphql": ["api_developer"],
    "openapi": ["api_developer"],
    "figma": ["ui_ux_designer"],
    "wireframe": ["ui_ux_designer"],
}

# Bare "go", "api", "node", "rest", "ui", "ux" removed — too short/ambiguous, cause
# false positives even with word boundaries ("api" inside "rapid", etc.).


def _kw_match(content: str, keyword: str) -> bool:
    """Word-boundary-aware keyword match. Keyword is a plain string; re.escape handles quoting."""
    return bool(re.search(r"(?<!\w)" + re.escape(keyword) + r"(?!\w)", content, re.IGNORECASE))


def _agents_from_arch_spec(arch_spec_content: str, agent_registry: Dict[str, Any]) -> List[str]:
    found: set = set()
    for keyword, agents in _KEYWORD_TO_AGENT.items():
        if _kw_match(arch_spec_content, keyword):
            for a in agents:
                if a in agent_registry:
                    found.add(a)
    if not found:
        return [a for a in _DEFAULT_BUILD_AGENTS if a in agent_registry]
    return sorted(found)


class ParallelOrchestrator:
    def __init__(
        self,
        agent_registry: Dict[str, Any],
        skill_registry: Dict[str, Any],
        spec_store: SpecStore,
    ):
        self.agent_registry = agent_registry
        self.skill_registry = skill_registry
        self.spec_store = spec_store

    async def run_phase(
        self,
        spec_id: str,
        phase: str,
        agent_names: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        arch_data = self.spec_store.load_arch_spec(spec_id)
        arch_content = arch_data["content"]

        if agent_names is None:
            if phase == "qa":
                agent_names = [a for a in _DEFAULT_QA_AGENTS if a in self.agent_registry]
            else:
                agent_names = _agents_from_arch_spec(arch_content, self.agent_registry)

        # Filter to only agents that exist — keep filtered list for zip alignment
        valid_agents = [n for n in agent_names if n in self.agent_registry]

        start = time.monotonic()
        tasks = [
            asyncio.wait_for(
                self._run_agent(name, arch_content, phase),
                timeout=_AGENT_TIMEOUT_S,
            )
            for name in valid_agents
        ]
        results_list = await asyncio.gather(*tasks, return_exceptions=True)
        duration_ms = int((time.monotonic() - start) * 1000)

        results: Dict[str, str] = {}
        skills_invoked: Dict[str, List[str]] = {}

        for agent_name, outcome in zip(valid_agents, results_list):
            if isinstance(outcome, Exception):
                results[agent_name] = f"Error: {type(outcome).__name__}: {outcome}"
                skills_invoked[agent_name] = []
            else:
                results[agent_name] = outcome["result"]
                skills_invoked[agent_name] = outcome["skills"]

        # Persist so audit_spec can auto-load without requiring the caller to pass results
        self.spec_store.save_phase_results(spec_id, phase, results)

        return {
            "spec_id": spec_id,
            "phase": phase,
            "results": results,
            "skills_invoked": skills_invoked,
            "duration_ms": duration_ms,
        }

    async def _run_agent(
        self,
        agent_name: str,
        arch_content: str,
        phase: str,
    ) -> Dict[str, Any]:
        agent = self.agent_registry[agent_name]
        task = build_agent_phase_task(phase)

        llm_result = await agent.dispatch_to_llm_async(task=task, context=arch_content)
        if llm_result is not None:
            base_result = llm_result
        else:
            processed = agent.process_request(task=task, context=arch_content)
            base_result = processed["guidance"]

        relevant_skills = skills_for_arch_spec(arch_content, agent_name, self.skill_registry)
        skill_outputs: List[str] = []
        skill_names_used: List[str] = []

        for skill in relevant_skills:
            try:
                outcome = skill.execute()
                skill_outputs.append(f"\n### Skill: {skill.name}\n{outcome['guidance']}")
                skill_names_used.append(skill.name)
            except Exception as e:
                skill_outputs.append(f"\n### Skill: {skill.name}\n(failed: {e})")

        combined = base_result
        if skill_outputs:
            combined += "\n\n---\n## Auto-invoked Skills" + "".join(skill_outputs)

        return {"result": combined, "skills": skill_names_used}
