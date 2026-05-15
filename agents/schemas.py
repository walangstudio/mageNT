"""Pydantic response schemas for mageNT agents.

These are the source of truth for the structured output contract every
review/audit agent must emit. They're injected into the prompt as JSON-Schema
(via ``model_json_schema()``) and used at eval time to validate the response
round-trips: ``SchemaCls.model_validate_json(response)`` either returns a
typed object or raises ``ValidationError``.
"""

from __future__ import annotations

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field, ConfigDict


# --------- shared primitives ----------------------------------------------------

Severity = Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"]
Confidence = Literal["high", "medium", "low"]


class _Strict(BaseModel):
    """Reject unknown keys so the contract holds tightly."""

    model_config = ConfigDict(extra="forbid")


# --------- security_engineer ----------------------------------------------------

class SecurityFinding(_Strict):
    severity: Severity
    title: str = Field(..., description="One-line title of the finding.")
    file: Optional[str] = Field(None, description="Path the finding lives in.")
    line: Optional[int] = Field(None, ge=1)
    cwe: Optional[str] = Field(None, description="e.g. CWE-89")
    confidence: Confidence
    attack: str = Field(..., description="How an attacker exploits this in 1-3 sentences.")
    fix: str = Field(..., description="Smallest viable remediation, with code if <10 lines.")


class SecurityReport(_Strict):
    findings: List[SecurityFinding]
    summary: Dict[Severity, int] = Field(
        ..., description="Count per severity. Use 0 for missing tiers."
    )


# --------- system_architect (ADR shape) -----------------------------------------

class ADROption(_Strict):
    name: str
    trade_off: str = Field(..., description="One-line trade-off summary.")


class ADRConsequences(_Strict):
    positive: List[str] = Field(default_factory=list)
    negative_accepted: List[str] = Field(default_factory=list)
    follow_ups: List[str] = Field(default_factory=list)


class ADR(_Strict):
    id: int = Field(..., ge=1)
    title: str
    context: str = Field(..., description="2-5 sentences: forces and constraints.")
    options_considered: List[ADROption] = Field(..., min_length=2, max_length=4)
    decision: str = Field(..., description="Chosen option in one sentence.")
    consequences: ADRConsequences


# --------- delivery_manager (release readiness) ---------------------------------

PhaseStatus = Literal["COMPLETE", "PARTIAL", "MISSING", "BLOCKED"]
PhaseName = Literal[
    "Requirements", "Design", "Development", "Test", "Security",
    "Performance", "Docs", "Deployment", "Rollback", "Monitoring",
]


class PhaseRow(_Strict):
    phase: PhaseName
    status: PhaseStatus
    evidence: Optional[str] = Field(None, description="Link, ticket, file path, or 'none'.")
    owner: Optional[str] = None
    notes: Optional[str] = None


class Risk(_Strict):
    severity: Severity
    description: str
    owner: Optional[str] = None
    mitigation: str
    due: Optional[str] = None


class ReleaseAudit(_Strict):
    recommendation: Literal["GO", "NO-GO", "GO-WITH-CONDITIONS"]
    summary: str = Field(..., description="One-line rationale.")
    phases: List[PhaseRow]
    risks: List[Risk] = Field(default_factory=list)
    conditions_to_flip: List[str] = Field(
        default_factory=list,
        description="Smallest set of actions that flips to GO.",
    )


# --------- debugging_expert -----------------------------------------------------

class DebugReport(_Strict):
    reproduction: str = Field(..., description="Steps a colleague can run to see it.")
    root_cause: str = Field(..., description="The actual cause, not a symptom.")
    evidence: List[str] = Field(default_factory=list, description="file:line cites.")
    minimum_fix: str = Field(..., description="Smallest patch; code snippet if <10 lines.")
    verification: str = Field(..., description="How to confirm the fix.")


# --------- performance_engineer -------------------------------------------------

class PerfHypothesis(_Strict):
    rank: int = Field(..., ge=1)
    hypothesis: str
    likelihood: Confidence
    cheapest_falsification: str = Field(..., description="Smallest experiment to disprove.")


class PerfHypothesisReport(_Strict):
    summary: str
    hypotheses: List[PerfHypothesis]
    leading_action: str = Field(..., description="What to do next based on the leading hypothesis.")


# --------- database_administrator ----------------------------------------------

class IndexRecommendation(_Strict):
    severity: Severity
    issue: str
    table: str
    columns: List[str]
    ddl: str = Field(..., description="The exact CREATE INDEX or schema-change SQL.")
    expected_plan_delta: str = Field(..., description="What changes in EXPLAIN.")


class IndexAuditReport(_Strict):
    findings: List[IndexRecommendation]
    summary: Dict[Severity, int]


# --------- qa_engineer (test design) -------------------------------------------

TestKind = Literal["happy_path", "negative", "edge"]


class TestCase(_Strict):
    kind: TestKind
    name: str
    given: str
    when: str
    then: str


class TestPlan(_Strict):
    summary: str
    cases: List[TestCase]


# --------- team_lead (coordinator outputs) --------------------------------------

class SynthesisFinding(_Strict):
    severity: Severity
    title: str = Field(..., description="One-line headline.")
    source_tasks: List[str] = Field(
        ...,
        min_length=1,
        description="Which teammates' outputs support this finding.",
    )
    detail: str = Field(..., description="Concrete claim. 1-4 sentences.")


class DissentingView(_Strict):
    topic: str = Field(..., description="What the disagreement is about.")
    positions: List[str] = Field(
        ...,
        min_length=2,
        description="Each entry is '<task>: <position>' so readers can see who said what.",
    )
    recommended_resolution: Optional[str] = None


class SynthesisReport(_Strict):
    """Merged findings across a phase's teammate outputs.

    Produced by `magent_team_synthesize`; consumed by borch's Brain to
    decide whether to merge, retask, or escalate. The contract is the
    machine-parseable replacement for free-form team-lead prose.
    """

    summary: str = Field(..., description="One-paragraph headline.")
    findings: List[SynthesisFinding] = Field(default_factory=list)
    dissenting_views: List[DissentingView] = Field(default_factory=list)
    recommended_actions: List[str] = Field(
        default_factory=list,
        description="Smallest viable next steps, ordered by priority.",
    )
    open_questions: List[str] = Field(default_factory=list)


# --- team_lead: team composition from a fuzzy brief --------------------------

# Constrained to the magent specialist surface so callers (borch) can rely
# on these being installable subagent types. Update in lockstep with the
# agent_registry in server.py.
TeammateAgentType = Literal[
    "team_lead",
    "system_architect",
    "security_engineer",
    "performance_engineer",
    "qa_engineer",
    "delivery_manager",
    "database_administrator",
    "cloud_architect",
    "devops_engineer",
    "business_analyst",
    "product_manager",
    "debugging_expert",
    "sdet",
]


class TeammateSpec(_Strict):
    name: str = Field(
        ...,
        min_length=1,
        max_length=40,
        description="Short identifier the orchestrator and chat use. Alphanumeric + '-' + '_'.",
    )
    agent_type: TeammateAgentType
    prompt: str = Field(
        ...,
        min_length=10,
        description="The teammate's task framed as a directive — what to do, what to produce.",
    )
    files_scope: Optional[List[str]] = Field(
        None,
        description="Files or directories this teammate owns (advisory; worktree is structural).",
    )
    model: Optional[Literal["opus", "sonnet", "haiku"]] = Field(
        None,
        description="Optional model override. Defaults to the teammate's seniority-mapped pick.",
    )


class TeamComposition(_Strict):
    """Output of `magent_team_compose` — turns a fuzzy human brief into a
    schema-validated team manifest that borch can materialise directly."""

    rationale: str = Field(
        ...,
        description="2-4 sentences: why these teammates, why this scope split.",
    )
    teammates: List[TeammateSpec] = Field(..., min_length=1, max_length=8)
    suggested_phase: str = Field(
        default="default",
        description="Phase name the orchestrator should put these tasks under.",
    )


# --- system_architect: plan approval gate ------------------------------------

class PlanApproval(_Strict):
    """Output of `magent_plan_approve` — does the proposed teammate plan
    satisfy the supplied approval_criteria? Used by Brain when a teammate
    submits a plan-mode plan before transitioning to Running."""

    approved: bool
    feedback: str = Field(
        ...,
        description="One-paragraph rationale. When approved=False, this is the actionable change-set the teammate must address.",
    )
    blocking_concerns: List[str] = Field(
        default_factory=list,
        description="Discrete blockers the teammate must resolve before re-submitting. Empty when approved=True.",
    )
    optional_suggestions: List[str] = Field(
        default_factory=list,
        description="Nice-to-haves the teammate may incorporate but aren't gating.",
    )


# --- team_lead: mid-flight retask -------------------------------------------

class RetaskAddition(_Strict):
    name: str = Field(..., min_length=1, max_length=40)
    agent_type: TeammateAgentType
    prompt: str = Field(..., min_length=10)
    rationale: str = Field(..., description="Why this teammate is needed now (1-2 sentences).")


class RetaskModification(_Strict):
    target_name: str = Field(..., description="Which existing teammate this modifies.")
    prompt_addendum: str = Field(
        ...,
        description="Extra direction to append to the teammate's prompt. Don't rewrite their entire mission.",
    )
    rationale: str


class RetaskDrop(_Strict):
    target_name: str
    rationale: str = Field(..., description="Why this teammate's current scope is obsolete.")


class RetaskDelta(_Strict):
    """Output of `magent_team_retask` — what changes to the running team in
    response to new evidence. Empty add/modify/drop lists means "no change";
    Brain treats that as a no-op. Otherwise Brain applies the delta against
    the live team state."""

    rationale: str = Field(
        ...,
        description="One-paragraph: why the team needs to change now.",
    )
    add_tasks: List[RetaskAddition] = Field(default_factory=list)
    modify_tasks: List[RetaskModification] = Field(default_factory=list)
    drop_tasks: List[RetaskDrop] = Field(default_factory=list)


# --------- registry -------------------------------------------------------------

# Map agent name → schema class. Used by run_matrix to dispatch validation.
AGENT_SCHEMAS = {
    "security_engineer": SecurityReport,
    "system_architect": ADR,
    "delivery_manager": ReleaseAudit,
    "debugging_expert": DebugReport,
    "performance_engineer": PerfHypothesisReport,
    "database_administrator": IndexAuditReport,
    "qa_engineer": TestPlan,
}

# Coordinator schemas — emitted by team_lead-style tools, not by individual
# specialist agents. Kept separate so eval/dispatch logic that iterates
# AGENT_SCHEMAS doesn't accidentally treat synthesis as a specialist task.
COORDINATOR_SCHEMAS = {
    "team_synthesis": SynthesisReport,
    "team_composition": TeamComposition,
    "plan_approval": PlanApproval,
    "retask_delta": RetaskDelta,
}
