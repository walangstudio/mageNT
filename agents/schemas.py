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
