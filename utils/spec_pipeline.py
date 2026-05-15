"""Orchestration glue for the Phase 7 magent_* spec pipeline.

Every ``magent_*`` MCP tool dispatches into one of these helpers. The helper:

1. Loads required prior artifacts from ``SpecStore`` (refuses if missing).
2. Builds the agent prompt with prior context injected.
3. Dispatches to the driving agent(s) — single via ``llm_adapter.dispatch``
   or fan-out via ``parallel_orchestrator``.
4. Extracts JSON from the response (handles fences + truncation).
5. Validates against the matching ``SPEC_SCHEMAS`` model.
6. On schema failure: retries up to ``RETRY_BUDGET`` times with the parser
   error injected back into the prompt (Phase 7F stuck-loop detection).
7. Persists via ``SpecStore.save_artifact``.
8. Records token / cost via ``SpecStore.record_phase_cost``.

The MCP tool handlers in ``server.py`` should be thin wrappers around these
functions — no business logic in the handler.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

try:
    from agents.spec_schemas import SPEC_SCHEMAS  # noqa: E402
except ImportError:  # pragma: no cover
    from ..agents.spec_schemas import SPEC_SCHEMAS  # type: ignore

try:
    from utils.spec_store import SpecStore  # noqa: E402
except ImportError:  # pragma: no cover
    from .spec_store import SpecStore  # type: ignore

try:
    from tests.prompt_eval.parseability import _extract_json  # noqa: E402
except ImportError:  # pragma: no cover
    _extract_json = None  # type: ignore


RETRY_BUDGET = 3  # max schema-validation retries per phase before escalation


@dataclass
class PhaseResult:
    spec_id: str
    kind: str
    model: Any                       # validated Pydantic instance
    path: Path                       # on-disk persistence path
    attempts: int                    # how many LLM calls this phase took
    raw_response: str                # last response (debug)
    cost: Dict[str, Any]             # provider usage if available


@dataclass
class PhaseEscalation(Exception):
    """Raised when an agent fails schema validation RETRY_BUDGET+ times."""

    spec_id: str
    kind: str
    last_error: str
    attempts: int

    def __str__(self) -> str:  # pragma: no cover
        return (
            f"Phase '{self.kind}' for spec '{self.spec_id}' failed "
            f"after {self.attempts} attempts. Last error: {self.last_error}"
        )


# ----- LLM call adapter ---------------------------------------------------

def _default_llm_call(
    agent_name: str,
    system_prompt: str,
    user_task: str,
    context: Optional[str],
    response_schema: Optional[Dict[str, Any]] = None,
    schema_name: str = "Response",
) -> Tuple[str, Dict[str, Any]]:
    """Wrap utils.llm_adapter.dispatch_full with schema-aware routing.

    Returns ``(text, usage_dict)``. ``usage_dict`` carries ``input_tokens`` /
    ``output_tokens`` when the provider reports them.
    """
    try:
        from utils.llm_adapter import dispatch_full  # noqa: E402
    except ImportError:  # pragma: no cover
        from .llm_adapter import dispatch_full  # type: ignore
    return dispatch_full(
        agent_name, system_prompt, user_task,
        context=context,
        response_schema=response_schema,
        schema_name=schema_name,
    )


def _extract_and_validate(kind: str, raw: str) -> Tuple[Optional[Any], Optional[str]]:
    """Pull JSON from raw and validate against the kind's schema."""
    cls = SPEC_SCHEMAS[kind]
    if _extract_json is None:
        # Minimal fallback so the pipeline still functions if parseability
        # helper is unavailable.
        blob = raw
    else:
        blob = _extract_json(raw)
    if not blob:
        return None, "no JSON object found in response"
    try:
        return cls.model_validate_json(blob), None
    except Exception as e:
        return None, str(e)[:600]


# ----- Single-agent phase --------------------------------------------------

def run_single_agent_phase(
    spec_store: SpecStore,
    spec_id: str,
    kind: str,
    agent_name: str,
    user_intent: str,
    context_artifacts: Optional[Dict[str, Any]] = None,
    agent_registry: Optional[Dict[str, Any]] = None,
    llm_call: Callable[..., Tuple[str, Dict[str, Any]]] = _default_llm_call,
) -> PhaseResult:
    """Drive one agent through one phase, validate, persist.

    ``agent_registry`` is the same map the MCP server hands around
    (server.AGENT_CLASSES instances). When provided we render the v2 prompt
    via ``BaseAgent.get_system_prompt()`` so the JSON-Schema injection from
    Phase 6 lands automatically.
    """
    if kind not in SPEC_SCHEMAS:
        raise ValueError(f"Unknown phase kind: {kind!r}")

    # Build system prompt — focused on the spec-pipeline phase, not the agent's
    # default output (which is a different schema for review/audit work).
    # We extract the agent's role/stance for tone, then attach the SPEC_SCHEMAS
    # schema for this phase as the ONLY contract.
    role = agent_name.replace("_", " ").title()
    stance = ""
    if agent_registry and agent_name in agent_registry:
        agent = agent_registry[agent_name]
        if isinstance(agent, type):
            agent = agent({"expertise_level": "principal"})
        try:
            stance = agent.opinionated_stance or ""
            if hasattr(agent, "role"):
                role = f"{agent.expertise_level.capitalize()} {agent.role}"
        except Exception:
            stance = ""
    schema_cls = SPEC_SCHEMAS[kind]
    schema_dict = schema_cls.model_json_schema()
    schema_name = schema_cls.__name__

    # Important: do NOT include the schema in the system prompt. The schema
    # goes to the provider via `response_format=json_schema` (strict-mode
    # grammar constraint in LM Studio / OpenAI / NVIDIA NIM). When the schema
    # also appears in the prompt, mid-size models ~20B tend to echo the
    # schema document back as "the response". A short, schema-name-only hint
    # is enough — the grammar layer enforces the actual shape.
    system_prompt = (
        f"You are a {role}. {stance}\n\n"
        f"Output a single JSON object that is a populated INSTANCE of the "
        f"{schema_name} schema. Fill in real values for every required field. "
        f"Do NOT output the schema document itself. Do NOT wrap in code fences. "
        f"JSON only — no prose, no markdown."
    )

    # Inject prior context as INLINE markdown summary, NOT as a JSON block.
    # Mid-size models (~20B) under strict response_format=json_schema tend to
    # echo the nearest valid JSON in their context window. Sending prior
    # artifacts as a JSON block makes them likely to regurgitate it as the
    # response. Markdown bullets force the model to actually compose a new
    # JSON instance.
    context_block: Optional[str] = None
    if context_artifacts:
        parts = []
        for k, v in context_artifacts.items():
            obj = v.model_dump() if hasattr(v, "model_dump") else v
            parts.append(f"### {k}")
            # Only include essential fields per known artifact kind to keep
            # the prompt tight and prevent context-echo.
            if isinstance(obj, dict):
                if k == "feature_spec":
                    fr_lines = [
                        f"  - {r['id']} ({r['rfc2119']}): {r['statement']}"
                        for r in obj.get("requirements", [])
                    ]
                    parts.append(f"feature_name: {obj.get('feature_name','')}")
                    parts.append(f"requirements:\n" + "\n".join(fr_lines))
                elif k == "constitution":
                    parts.append(f"project_name: {obj.get('project_name','')}")
                    parts.append("principles: " + "; ".join(obj.get("principles", [])))
                elif k == "plan":
                    comps = obj.get("components", [])
                    parts.append(f"tech_stack: {obj.get('tech_stack',{}).get('language','')}"
                                  f"/{obj.get('tech_stack',{}).get('framework','')}")
                    parts.append("components:\n" + "\n".join(
                        f"  - {c.get('name','')}: owns {c.get('owns_fr_ids',[])}"
                        for c in comps
                    ))
                elif k == "audit":
                    parts.append(f"recommendation: {obj.get('recommendation','')}")
                else:
                    parts.append(json.dumps(obj, indent=2)[:400])
            else:
                parts.append(str(obj)[:400])
        context_block = "Prior context:\n" + "\n\n".join(parts)

    last_error: Optional[str] = None
    raw = ""
    usage: Dict[str, Any] = {}
    user_task = user_intent

    for attempt in range(1, RETRY_BUDGET + 1):
        # Pass schema to llm_call only if it accepts it (newer signature).
        try:
            raw, usage = llm_call(
                agent_name, system_prompt, user_task, context_block,
                response_schema=schema_dict, schema_name=schema_name,
            )
        except TypeError:
            # Older test stubs use the 4-arg signature; fall back gracefully.
            raw, usage = llm_call(agent_name, system_prompt, user_task, context_block)
        spec_store.record_phase_cost(spec_id, kind, {
            "attempt": attempt, "agent": agent_name, **usage,
        })
        model, err = _extract_and_validate(kind, raw)
        if model is not None:
            path = spec_store.save_artifact(spec_id, kind, model)
            return PhaseResult(
                spec_id=spec_id, kind=kind, model=model, path=path,
                attempts=attempt, raw_response=raw, cost=usage,
            )
        last_error = err
        # Inject the validation error back into the next attempt — the
        # canonical agent-self-repair loop.
        user_task = (
            f"{user_intent}\n\nPREVIOUS ATTEMPT FAILED schema validation: "
            f"{err}\nReturn ONLY a JSON object conforming to the schema."
        )

    raise PhaseEscalation(
        spec_id=spec_id, kind=kind,
        last_error=last_error or "unknown",
        attempts=RETRY_BUDGET,
    )


# ----- Multi-agent merge phase --------------------------------------------

def run_multi_agent_phase(
    spec_store: SpecStore,
    spec_id: str,
    kind: str,
    agent_names: List[str],
    user_intent: str,
    merger_agent: str,
    context_artifacts: Optional[Dict[str, Any]] = None,
    agent_registry: Optional[Dict[str, Any]] = None,
    llm_call: Callable[..., Tuple[str, Dict[str, Any]]] = _default_llm_call,
) -> PhaseResult:
    """Fan out to N agents, then ask ``merger_agent`` to consolidate into the schema.

    Used for ``magent_plan`` (system_architect + database_administrator + cloud_architect),
    ``magent_audit`` (delivery + security + perf + qa), and similar multi-perspective phases.
    """
    if not agent_names:
        raise ValueError("agent_names must be non-empty")

    # Pre-build prompts so we can fan out concurrently (the underlying
    # llm_adapter.dispatch_full is sync; ThreadPoolExecutor parallelises across
    # the network I/O wait per agent).
    ctx = (
        None if not context_artifacts
        else "Prior artifacts:\n```json\n"
             + json.dumps({k: v.model_dump() if hasattr(v, "model_dump") else v
                           for k, v in context_artifacts.items()}, indent=2)
             + "\n```"
    )

    def _build_sys_prompt(name: str) -> str:
        if agent_registry and name in agent_registry:
            agent = agent_registry[name]
            if isinstance(agent, type):
                agent = agent({"expertise_level": "principal"})
            return agent.get_system_prompt()
        return f"You are the {name} agent. Provide expert input on the request."

    def _one(name: str) -> Tuple[str, str, Dict[str, Any]]:
        sys_p = _build_sys_prompt(name)
        try:
            text, usage = llm_call(name, sys_p, user_intent, ctx)
        except TypeError:
            text, usage = llm_call(name, sys_p, user_intent, ctx)
        return name, text, usage

    contributions: Dict[str, str] = {}
    from concurrent.futures import ThreadPoolExecutor
    # Cap concurrency so we don't overload local LLM endpoints (LM Studio,
    # Ollama) which often only run one model at a time. 4 is comfortable.
    with ThreadPoolExecutor(max_workers=min(len(agent_names), 4)) as pool:
        for name, text, usage in pool.map(_one, agent_names):
            contributions[name] = text
            spec_store.record_phase_cost(spec_id, kind, {
                "phase_role": "contributor", "agent": name, **usage,
            })

    merger_intent = (
        f"{user_intent}\n\nConsolidate the following expert contributions into "
        f"a single JSON object conforming to the schema. Resolve conflicts by "
        f"naming the trade-off accepted.\n\n"
        + "\n\n".join(f"--- {name} ---\n{text}" for name, text in contributions.items())
    )

    return run_single_agent_phase(
        spec_store=spec_store,
        spec_id=spec_id,
        kind=kind,
        agent_name=merger_agent,
        user_intent=merger_intent,
        context_artifacts=context_artifacts,
        agent_registry=agent_registry,
        llm_call=llm_call,
    )


# ----- Gate helpers --------------------------------------------------------

class GateError(Exception):
    """Raised when an upstream artifact is missing or has unresolved blockers."""


def require_artifact(spec_store: SpecStore, spec_id: str, kind: str) -> Any:
    """Return the loaded artifact or raise GateError with a helpful message."""
    model = spec_store.load_artifact(spec_id, kind)
    if model is None:
        raise GateError(
            f"Phase gate: '{kind}' artifact not found for spec '{spec_id}'. "
            f"Run the upstream magent_* tool first."
        )
    return model


def require_resolved_clarifications(spec) -> None:
    """Raise GateError if a FeatureSpec still has open clarification items."""
    open_q = spec.all_clarifications()
    if open_q:
        raise GateError(
            f"Phase gate: spec has {len(open_q)} unresolved [NEEDS CLARIFICATION] "
            f"item(s). Run magent_clarify first. Items: {open_q[:3]}"
            f"{' ...' if len(open_q) > 3 else ''}"
        )


# ----- per-task failing test generation -----------------------------------
#
# Phase 7J fix: sdet was writing end-to-end-flow tests (subprocess CLI calls)
# that only pass when EVERY task is implemented. Per-task tests scope to the
# specific files + FRs the task touches, import directly from those modules,
# and assert observable behaviour without subprocess.

def generate_failing_test_for_task(
    task,
    spec,
    framework_name: str,
    framework_extension: str,
    llm_call: Callable = _default_llm_call,
) -> Tuple[str, Dict[str, Any]]:
    """Ask sdet to write ONE failing test scoped to a single task.

    Returns ``(test_source, usage)`` ready to be persisted. The test imports
    the task's files directly and asserts what's observable from THOSE files
    only — no subprocess calls to a CLI that other tasks own.
    """
    relevant_frs = [r for r in spec.requirements if r.id in task.fr_ids]
    relevant_scenarios: List[Any] = []
    for us in spec.user_stories:
        for sc in us.scenarios:
            if any(fr.id in sc.given + sc.when + sc.then for fr in relevant_frs):
                relevant_scenarios.append(sc)
    if not relevant_scenarios and spec.user_stories:
        relevant_scenarios = list(spec.user_stories[0].scenarios)[:1]

    # Derive a primary import target from the task's files.
    primary_files = [f for f in task.files if not f.endswith("__init__" + ".py")]
    import_hint = ""
    if primary_files:
        path = primary_files[0].replace("\\", "/")
        if path.endswith(".py") and "/" in path:
            module_path = path[:-3].replace("/", ".")
            import_hint = f"`from {module_path} import ...`"

    sys_prompt = (
        f"You are a senior SDET. Output ONLY the {framework_name} test source for "
        f"ONE test file — no prose, no markdown, no code fence. The test MUST "
        f"currently FAIL because the implementation does not yet exist. Use real "
        f"assertions (NOT `assert False`). Import the modules under test "
        f"DIRECTLY ({import_hint or 'from the task files'}). Do NOT subprocess "
        f"a CLI — exercise classes / functions directly. Keep the test scoped to "
        f"the FR(s) below; do not test functionality outside this task."
    )

    user_msg = (
        f"Write the failing test at: {task.failing_test_path}\n"
        f"Task: {task.id} — {task.title}\n"
        f"Files this task implements: {task.files}\n"
        f"FR(s) under test:\n"
        + "\n".join(f"  - {r.id} ({r.rfc2119}): {r.statement}" for r in relevant_frs)
        + f"\n\nGiven/When/Then scenarios:\n"
        + "\n".join(
            f"  GIVEN {sc.given}\n  WHEN {sc.when}\n  THEN {sc.then}\n"
            for sc in relevant_scenarios[:2]
        )
        + (f"\n\nImport hint: {import_hint}\n" if import_hint else "")
        + f"\nUse a tmp_path / temporary-file pattern so each test gets a clean "
          f"state. Assert observable outcomes (return values, file contents, "
          f"data structure shapes). Keep the file under 60 lines. Output the "
          f"raw .{framework_extension} source only — no fences, no prose."
    )

    text, usage = llm_call("sdet", sys_prompt, user_msg, None)
    text = (text or "").strip()
    # Strip code fences the model might emit despite instructions.
    if text.startswith("```"):
        body = text.split("```", 2)
        if len(body) >= 2:
            text = body[1]
            if text.lower().startswith(framework_extension.lower()):
                text = text[len(framework_extension):].lstrip()
            elif text.lower().startswith("python"):
                text = text[6:].lstrip()
    return text, usage


# ----- Coordinator: team synthesis ----------------------------------------

try:
    from agents.schemas import (
        SynthesisReport, TeamComposition, PlanApproval, RetaskDelta,
    )  # noqa: E402
except ImportError:  # pragma: no cover
    from ..agents.schemas import (
        SynthesisReport, TeamComposition, PlanApproval, RetaskDelta,
    )  # type: ignore


def run_team_synthesize(
    task_outputs: List[Dict[str, Any]],
    phase_name: str = "",
    agent_registry: Optional[Dict[str, Any]] = None,
    llm_call: Callable[..., Tuple[str, Dict[str, Any]]] = _default_llm_call,
) -> Tuple[SynthesisReport, str, Dict[str, Any]]:
    """Merge a set of teammate outputs into a single SynthesisReport.

    ``task_outputs`` is a list of dicts shaped
    ``{"name": str, "agent_type": str, "output": str}``. The synthesizer is
    `delivery_manager` (Pydantic v2 + Phase 6 prompt v2). Schema validation
    retries up to RETRY_BUDGET times before giving up.

    Returns ``(SynthesisReport, raw_text, usage_dict)``. The raw text is the
    last LLM response, useful for debugging when validation fails.
    """
    if not task_outputs:
        raise ValueError("run_team_synthesize requires at least one task output")

    schema_dict = SynthesisReport.model_json_schema()
    schema_name = "SynthesisReport"

    role = "Delivery Manager"
    stance = ""
    if agent_registry and "delivery_manager" in agent_registry:
        agent = agent_registry["delivery_manager"]
        if isinstance(agent, type):
            agent = agent({"expertise_level": "principal"})
        try:
            stance = agent.opinionated_stance or ""
            if hasattr(agent, "role"):
                role = f"{agent.expertise_level.capitalize()} {agent.role}"
        except Exception:
            stance = ""

    system_prompt = (
        f"You are a {role}. {stance}\n\n"
        f"Synthesize the teammate outputs below into a single {schema_name} "
        f"JSON instance. Surface dissenting views explicitly when teammates "
        f"disagree — name who said what. Pick the smallest viable next "
        f"actions. JSON only — no prose, no code fences."
    )

    outputs_block = []
    for o in task_outputs:
        name = o.get("name", "?")
        agent_type = o.get("agent_type", "?")
        body = (o.get("output") or "").strip()
        if len(body) > 3000:
            body = body[:3000] + "…[truncated]"
        outputs_block.append(f"### Teammate `{name}` ({agent_type})\n{body}")

    phase_line = f" for phase `{phase_name}`" if phase_name else ""
    user_task = (
        f"Synthesize these teammate outputs{phase_line}:\n\n"
        + "\n\n".join(outputs_block)
    )

    last_err = ""
    raw = ""
    usage: Dict[str, Any] = {}
    for attempt in range(1, RETRY_BUDGET + 1):
        raw, usage = llm_call(
            "delivery_manager",
            system_prompt,
            user_task,
            None,
            response_schema=schema_dict,
            schema_name=schema_name,
        )
        if _extract_json is not None:
            blob = _extract_json(raw) or raw
        else:
            blob = raw
        try:
            model = SynthesisReport.model_validate_json(blob)
            return model, raw, usage
        except Exception as e:
            last_err = str(e)[:600]
            user_task = (
                f"Your previous response failed schema validation:\n"
                f"  {last_err}\n\n"
                "Emit a valid SynthesisReport JSON instance now.\n\n"
                + user_task
            )

    raise PhaseEscalation(
        spec_id="<team>", kind="team_synthesis",
        last_error=last_err, attempts=RETRY_BUDGET,
    )


def run_team_compose(
    brief: str,
    project_context: Optional[str] = None,
    available_agent_types: Optional[List[str]] = None,
    max_teammates: int = 5,
    agent_registry: Optional[Dict[str, Any]] = None,
    llm_call: Callable[..., Tuple[str, Dict[str, Any]]] = _default_llm_call,
) -> Tuple[TeamComposition, str, Dict[str, Any]]:
    """Turn a fuzzy human brief into a schema-validated TeamComposition.

    Driven by `team_lead`. The composition lists 1..max_teammates teammates
    (each with name, agent_type from the validated literal, framed prompt,
    optional files scope + model). Schema validation retries up to
    RETRY_BUDGET times before giving up.
    """
    if not brief or not brief.strip():
        raise ValueError("run_team_compose requires a non-empty brief")

    schema_dict = TeamComposition.model_json_schema()
    schema_name = "TeamComposition"

    role = "Team Lead"
    stance = ""
    if agent_registry and "team_lead" in agent_registry:
        agent = agent_registry["team_lead"]
        if isinstance(agent, type):
            agent = agent({"expertise_level": "principal"})
        try:
            stance = agent.opinionated_stance or ""
            if hasattr(agent, "role"):
                role = f"{agent.expertise_level.capitalize()} {agent.role}"
        except Exception:
            stance = ""

    agent_types_block = (
        "\n".join(f"  - {t}" for t in available_agent_types)
        if available_agent_types
        else "(all magent specialist agent_types accepted)"
    )

    system_prompt = (
        f"You are a {role}. {stance}\n\n"
        f"Decompose the user's brief into a {schema_name} JSON instance: "
        f"pick the smallest team (1..{max_teammates} teammates) that covers "
        f"the brief without overlap. Each teammate gets a directive prompt "
        f"framed at their specialty. Avoid duplicate specialists. JSON only "
        f"— no prose, no code fences."
    )

    user_task_parts = [f"Brief: {brief.strip()}"]
    if project_context:
        user_task_parts.append(f"\nProject context (optional):\n{project_context.strip()[:2000]}")
    user_task_parts.append(f"\nAllowed agent_type values:\n{agent_types_block}")
    user_task = "\n".join(user_task_parts)

    last_err = ""
    raw = ""
    usage: Dict[str, Any] = {}
    for attempt in range(1, RETRY_BUDGET + 1):
        raw, usage = llm_call(
            "team_lead",
            system_prompt,
            user_task,
            None,
            response_schema=schema_dict,
            schema_name=schema_name,
        )
        if _extract_json is not None:
            blob = _extract_json(raw) or raw
        else:
            blob = raw
        try:
            model = TeamComposition.model_validate_json(blob)
            return model, raw, usage
        except Exception as e:
            last_err = str(e)[:600]
            user_task = (
                f"Your previous response failed schema validation:\n"
                f"  {last_err}\n\n"
                "Emit a valid TeamComposition JSON instance now.\n\n"
                + user_task
            )

    raise PhaseEscalation(
        spec_id="<team>", kind="team_composition",
        last_error=last_err, attempts=RETRY_BUDGET,
    )


def run_plan_approve(
    plan_markdown: str,
    approval_criteria: str = "",
    reviewer_agent: str = "system_architect",
    agent_registry: Optional[Dict[str, Any]] = None,
    llm_call: Callable[..., Tuple[str, Dict[str, Any]]] = _default_llm_call,
) -> Tuple[PlanApproval, str, Dict[str, Any]]:
    """Judge a teammate's plan-mode plan against the supplied criteria.

    Default reviewer is `system_architect`. Switch to `delivery_manager`
    when criteria are release/process-shaped rather than architecture-shaped.
    Schema validation retries up to RETRY_BUDGET times.
    """
    if not plan_markdown or not plan_markdown.strip():
        raise ValueError("run_plan_approve requires non-empty plan_markdown")

    if reviewer_agent not in ("system_architect", "delivery_manager"):
        raise ValueError(
            f"reviewer_agent must be 'system_architect' or 'delivery_manager', "
            f"got {reviewer_agent!r}"
        )

    schema_dict = PlanApproval.model_json_schema()
    schema_name = "PlanApproval"

    role_default = "Principal System Architect" if reviewer_agent == "system_architect" else "Principal Delivery Manager"
    role = role_default
    stance = ""
    if agent_registry and reviewer_agent in agent_registry:
        agent = agent_registry[reviewer_agent]
        if isinstance(agent, type):
            agent = agent({"expertise_level": "principal"})
        try:
            stance = agent.opinionated_stance or ""
            if hasattr(agent, "role"):
                role = f"{agent.expertise_level.capitalize()} {agent.role}"
        except Exception:
            stance = ""

    system_prompt = (
        f"You are a {role}. {stance}\n\n"
        f"Judge the plan below against the approval criteria. Approve only "
        f"when the plan demonstrably satisfies every criterion. When you "
        f"reject, the feedback must be specific enough that the teammate can "
        f"act on it directly. List blocking_concerns separately from "
        f"optional_suggestions — only blockers gate approval. JSON only — "
        f"emit a single {schema_name} instance; no prose, no fences."
    )

    criteria_block = approval_criteria.strip() if approval_criteria else (
        "(none specified — apply the reviewer's defaults: correctness, "
        "scope discipline, test coverage, observable behaviour rather than "
        "implementation detail.)"
    )

    user_task = (
        f"Approval criteria:\n{criteria_block}\n\n"
        f"Plan under review:\n{plan_markdown.strip()[:8000]}"
    )

    last_err = ""
    raw = ""
    usage: Dict[str, Any] = {}
    for attempt in range(1, RETRY_BUDGET + 1):
        raw, usage = llm_call(
            reviewer_agent,
            system_prompt,
            user_task,
            None,
            response_schema=schema_dict,
            schema_name=schema_name,
        )
        if _extract_json is not None:
            blob = _extract_json(raw) or raw
        else:
            blob = raw
        try:
            model = PlanApproval.model_validate_json(blob)
            return model, raw, usage
        except Exception as e:
            last_err = str(e)[:600]
            user_task = (
                f"Your previous response failed schema validation:\n"
                f"  {last_err}\n\n"
                "Emit a valid PlanApproval JSON instance now.\n\n"
                + user_task
            )

    raise PhaseEscalation(
        spec_id="<team>", kind="plan_approval",
        last_error=last_err, attempts=RETRY_BUDGET,
    )


def run_team_retask(
    current_team_state: str,
    new_evidence: str,
    agent_registry: Optional[Dict[str, Any]] = None,
    llm_call: Callable[..., Tuple[str, Dict[str, Any]]] = _default_llm_call,
) -> Tuple[RetaskDelta, str, Dict[str, Any]]:
    """Decide whether the running team needs to change in response to new
    evidence. Driven by `team_lead`. Output is a delta: add / modify / drop
    teammates. Empty lists across the board means "no change" and Brain
    treats it as a no-op. Retries up to RETRY_BUDGET times.

    ``current_team_state`` is a free-form-ish string built by the caller —
    typically a short summary of each live teammate's name, role, scope,
    and last-known status. ``new_evidence`` is the surfaced finding that
    might invalidate or reshape the current plan.
    """
    if not new_evidence or not new_evidence.strip():
        raise ValueError("run_team_retask requires non-empty new_evidence")

    schema_dict = RetaskDelta.model_json_schema()
    schema_name = "RetaskDelta"

    role = "Team Lead"
    stance = ""
    if agent_registry and "team_lead" in agent_registry:
        agent = agent_registry["team_lead"]
        if isinstance(agent, type):
            agent = agent({"expertise_level": "principal"})
        try:
            stance = agent.opinionated_stance or ""
            if hasattr(agent, "role"):
                role = f"{agent.expertise_level.capitalize()} {agent.role}"
        except Exception:
            stance = ""

    system_prompt = (
        f"You are a {role}. {stance}\n\n"
        f"Given the live team state and surfaced evidence, emit a "
        f"{schema_name} JSON instance describing what changes (if any) the "
        f"team needs now. Prefer modifying an existing teammate's prompt "
        f"over adding new teammates. Drop a teammate only when the evidence "
        f"makes their entire scope obsolete. When no change is warranted, "
        f"return all-empty lists with a rationale explaining why the "
        f"current team is still correct. JSON only — no prose, no fences."
    )

    user_task = (
        f"Current team state:\n{current_team_state.strip()[:3000]}\n\n"
        f"New evidence:\n{new_evidence.strip()[:3000]}"
    )

    last_err = ""
    raw = ""
    usage: Dict[str, Any] = {}
    for attempt in range(1, RETRY_BUDGET + 1):
        raw, usage = llm_call(
            "team_lead",
            system_prompt,
            user_task,
            None,
            response_schema=schema_dict,
            schema_name=schema_name,
        )
        if _extract_json is not None:
            blob = _extract_json(raw) or raw
        else:
            blob = raw
        try:
            model = RetaskDelta.model_validate_json(blob)
            return model, raw, usage
        except Exception as e:
            last_err = str(e)[:600]
            user_task = (
                f"Your previous response failed schema validation:\n"
                f"  {last_err}\n\n"
                "Emit a valid RetaskDelta JSON instance now.\n\n"
                + user_task
            )

    raise PhaseEscalation(
        spec_id="<team>", kind="retask_delta",
        last_error=last_err, attempts=RETRY_BUDGET,
    )
