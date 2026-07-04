"""Pydantic schemas for the spec-driven development lifecycle.

Phase 7 makes every artifact in the chain a typed, validated wire contract:
``Constitution → FeatureSpec → ClarificationLog → DesignPack (optional) →
ImplementationPlan → TaskList → ImplementationTrace → Audit → ReleaseAudit``.
``SpecDelta`` carries brownfield patches.

Custom validators reject the failure modes Spec Kit / OpenSpec catch only
by convention: tautological GIVEN/WHEN/THEN, duplicate FR-IDs, unresolved
``[NEEDS CLARIFICATION]`` markers, missing RFC 2119 verbs.
"""

from __future__ import annotations

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

try:
    from agents.schemas import ADRConsequences, ADROption
except ImportError:
    from .schemas import ADRConsequences, ADROption  # type: ignore


Priority = Literal["P1", "P2", "P3"]
RFC2119 = Literal["MUST", "SHOULD", "MAY", "MUST NOT", "SHOULD NOT"]
PhaseStatus = Literal["COMPLETE", "PARTIAL", "MISSING", "BLOCKED"]
StrideCategory = Literal[
    "spoofing", "tampering", "repudiation", "information_disclosure",
    "denial_of_service", "elevation_of_privilege",
]


_TAUTOLOGY_PHRASES = (
    "feature works as specified",
    "as expected",
    "should work",
    "should be ok",
    "works correctly",
    "behaves as expected",
    "function should work",
)


def _looks_tautological(text: str) -> Optional[str]:
    lowered = text.lower()
    for phrase in _TAUTOLOGY_PHRASES:
        if phrase in lowered:
            return phrase
    return None


def _require_unique(ids: list, label: str) -> None:
    if len(ids) != len(set(ids)):
        dupes = [i for i in ids if ids.count(i) > 1]
        raise ValueError(f"{label} must be unique. Duplicates: {sorted(set(dupes))}")


class _Strict(BaseModel):
    """Reject unknown keys and silently-coerced values."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


# --------- Constitution ----------------------------------------------------

class NFRTargets(_Strict):
    availability: Optional[str] = Field(None, description="e.g. 99.9% monthly")
    latency_p99_ms: Optional[int] = Field(None, ge=1)
    cost_ceiling_usd_month: Optional[float] = Field(None, ge=0)
    rto_minutes: Optional[int] = Field(None, ge=0)
    rpo_minutes: Optional[int] = Field(None, ge=0)


class GlossaryTerm(_Strict):
    term: str = Field(..., min_length=1)
    definition: str = Field(..., min_length=5)


class Constitution(_Strict):
    project_name: str = Field(..., min_length=1)
    principles: List[str] = Field(..., min_length=3,
                                   description="Project-wide guardrails (e.g. 'prefer boring tech', 'no PII in logs').")
    nfr_targets: NFRTargets
    tech_constraints: List[str] = Field(default_factory=list,
                                         description="Hard constraints (e.g. 'must run on Cloudflare Workers').")
    out_of_scope: List[str] = Field(default_factory=list)
    glossary: List[GlossaryTerm] = Field(
        default_factory=list,
        description="Project vocabulary: one term, one meaning, used consistently in every FR.",
    )


# --------- FeatureSpec -----------------------------------------------------

class GivenWhenThen(_Strict):
    given: str = Field(..., min_length=10)
    when: str = Field(..., min_length=10)
    then: str = Field(..., min_length=10)

    @field_validator("then")
    @classmethod
    def then_must_be_observable(cls, v: str) -> str:
        hit = _looks_tautological(v)
        if hit:
            raise ValueError(
                f"THEN must name an observable outcome; phrase '{hit}' is tautological."
            )
        return v

    @model_validator(mode="after")
    def when_then_must_differ_from_given(self):
        if self.when.strip().lower() == self.given.strip().lower():
            raise ValueError("WHEN must differ from GIVEN (no duplicate restatement).")
        if self.then.strip().lower() == self.when.strip().lower():
            raise ValueError("THEN must differ from WHEN (no duplicate restatement).")
        return self


class Constraint(_Strict):
    """A hard code-level constraint the implementation must satisfy, beyond the
    test: a banned (`forbid`) or mandatory (`require`) token. Enforced by the
    implement loop, so a passing test that uses a forbidden means still fails."""

    kind: Literal["forbid", "require"]
    pattern: str = Field(..., min_length=1,
                          description="Code token/identifier (e.g. 'eval', 'os.system'), or a regex when regex=True.")
    message: str = Field(default="",
                         description="Why — surfaced to the implementer on violation.")
    regex: bool = Field(default=False, description="Treat `pattern` as a raw regex.")


class FunctionalRequirement(_Strict):
    id: str = Field(..., pattern=r"^FR-\d{3}$",
                     description="FR-001 through FR-999, zero-padded.")
    statement: str = Field(..., min_length=10)
    rfc2119: RFC2119
    constraints: List[Constraint] = Field(default_factory=list,
                                            description="Hard banned/required code tokens, enforced beyond the test.")
    needs_clarification: List[str] = Field(default_factory=list,
                                             description="Open questions that block downstream phases.")

    @model_validator(mode="after")
    def statement_includes_rfc2119_verb(self):
        if self.rfc2119 not in self.statement:
            raise ValueError(
                f"FR statement must contain the RFC 2119 verb '{self.rfc2119}'. "
                f"Got: {self.statement!r}"
            )
        return self


class UserStory(_Strict):
    priority: Priority
    title: str = Field(..., min_length=3)
    why: str = Field(..., min_length=10,
                      description="Why this priority — business or user reason.")
    independent_test: str = Field(..., min_length=10,
                                    description="One concrete way to test this story in isolation.")
    scenarios: List[GivenWhenThen] = Field(..., min_length=1)


class FeatureSpec(_Strict):
    spec_id: str
    feature_name: str = Field(..., min_length=1)
    user_stories: List[UserStory] = Field(..., min_length=1)
    requirements: List[FunctionalRequirement] = Field(..., min_length=1)
    success_criteria: List[str] = Field(..., min_length=1,
                                          description="Measurable outcomes.")
    assumptions: List[str] = Field(default_factory=list)
    needs_clarification: List[str] = Field(default_factory=list,
                                             description="Top-level open questions; blocks magent_plan.")

    @model_validator(mode="after")
    def fr_ids_unique(self):
        _require_unique([r.id for r in self.requirements], "FR ids")
        return self

    def all_clarifications(self) -> List[str]:
        out = list(self.needs_clarification)
        for r in self.requirements:
            out.extend(f"{r.id}: {q}" for q in r.needs_clarification)
        return out


# --------- ClarificationLog ------------------------------------------------

class Clarification(_Strict):
    question: str = Field(..., min_length=5)
    answer: str = Field(..., min_length=5)
    addressed_fr_ids: List[str] = Field(default_factory=list)


class ClarificationLog(_Strict):
    spec_id: str
    items: List[Clarification] = Field(..., min_length=1)


# --------- DesignPack (UX coverage: journeys, screens, roles) ---------------

class Journey(_Strict):
    id: str = Field(..., pattern=r"^JN-\d{3}$",
                     description="JN-001 through JN-999, zero-padded.")
    title: str = Field(..., min_length=3)
    role: str = Field(..., min_length=1,
                       description="The user role walking this journey.")
    fr_ids: List[str] = Field(..., min_length=1,
                               description="FR-IDs this journey exercises.")
    steps: List[str] = Field(..., min_length=1,
                              description="Ordered user-visible steps.")


class Screen(_Strict):
    id: str = Field(..., pattern=r"^SC-\d{3}$",
                     description="SC-001 through SC-999, zero-padded.")
    name: str = Field(..., min_length=1)
    purpose: str = Field(..., min_length=10)
    states: List[str] = Field(default_factory=list,
                               description="UI states to design (e.g. default, empty, loading, error).")
    fr_ids: List[str] = Field(default_factory=list)
    journey_ids: List[str] = Field(default_factory=list,
                                     description="JN-IDs that pass through this screen.")


class RolePermission(_Strict):
    role: str = Field(..., min_length=1)
    can: List[str] = Field(..., min_length=1,
                            description="Capabilities this role holds.")
    fr_ids: List[str] = Field(default_factory=list)


class DesignPack(_Strict):
    spec_id: str
    journeys: List[Journey] = Field(..., min_length=1)
    screens: List[Screen] = Field(..., min_length=1)
    role_permissions: List[RolePermission] = Field(default_factory=list)

    @model_validator(mode="after")
    def ids_unique_and_journey_refs_exist(self):
        jn_ids = [j.id for j in self.journeys]
        _require_unique(jn_ids, "Journey ids")
        _require_unique([s.id for s in self.screens], "Screen ids")
        jn_set = set(jn_ids)
        for s in self.screens:
            for jid in s.journey_ids:
                if jid not in jn_set:
                    raise ValueError(f"Screen {s.id} references missing journey {jid}")
        return self


# --------- ImplementationPlan ----------------------------------------------

class TechStack(_Strict):
    language: str
    framework: Optional[str] = None
    database: Optional[str] = None
    runtime: Optional[str] = None
    deployment: Optional[str] = None


class Component(_Strict):
    name: str
    responsibility: str = Field(..., min_length=10)
    owns_fr_ids: List[str] = Field(default_factory=list)


class Entity(_Strict):
    name: str
    fields: Dict[str, str] = Field(..., description="field_name -> type/description")
    relationships: List[str] = Field(default_factory=list)


class APIEndpoint(_Strict):
    path: str
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]
    request_schema: Optional[str] = None
    response_schema: Optional[str] = None
    fr_ids: List[str] = Field(default_factory=list)


class ADRRecord(_Strict):
    """Architecture decision record. Accepted ADRs are immutable: change course
    by adding a new record and marking the old one superseded — never rewrite."""

    id: int = Field(..., ge=1)
    title: str = Field(..., min_length=3)
    context: str = Field(..., min_length=10,
                          description="Forces and constraints that made this decision necessary.")
    options_considered: List[ADROption] = Field(..., min_length=2, max_length=4)
    decision: str = Field(..., min_length=5)
    consequences: ADRConsequences
    status: Literal["accepted", "superseded"] = "accepted"
    superseded_by: Optional[int] = Field(
        None, description="ADR id that replaces this one; required iff status is superseded.")


class Threat(_Strict):
    category: StrideCategory
    description: str = Field(..., min_length=10)
    affected_components: List[str] = Field(..., min_length=1)
    mitigation: str = Field(..., min_length=10)
    fr_ids: List[str] = Field(default_factory=list)


class ImplementationPlan(_Strict):
    spec_id: str
    tech_stack: TechStack
    components: List[Component] = Field(..., min_length=1)
    data_model: List[Entity] = Field(default_factory=list)
    api_contracts: List[APIEndpoint] = Field(default_factory=list)
    nfr_coverage: Dict[str, str] = Field(
        default_factory=dict,
        description="non-functional concern -> mechanism that addresses it",
    )
    adrs: List[ADRRecord] = Field(default_factory=list,
                                    description="Architecturally significant decisions.")
    threat_model: List[Threat] = Field(default_factory=list,
                                         description="STRIDE threats with mitigations.")

    @model_validator(mode="after")
    def component_names_unique(self):
        _require_unique([c.name for c in self.components], "Component names")
        return self

    @model_validator(mode="after")
    def adr_ids_unique_and_supersede_refs_valid(self):
        ids = [a.id for a in self.adrs]
        _require_unique(ids, "ADR ids")
        id_set = set(ids)
        for a in self.adrs:
            if a.status == "superseded":
                if a.superseded_by is None:
                    raise ValueError(f"ADR {a.id} is superseded but names no superseded_by.")
                if a.superseded_by == a.id or a.superseded_by not in id_set:
                    raise ValueError(
                        f"ADR {a.id} superseded_by {a.superseded_by} must reference another existing ADR.")
            elif a.superseded_by is not None:
                raise ValueError(f"ADR {a.id} is accepted; superseded_by must be unset.")
        return self


# --------- TaskList --------------------------------------------------------

class Task(_Strict):
    id: str = Field(..., pattern=r"^T\d{3}$",
                     description="T001 through T999, zero-padded.")
    title: str = Field(..., min_length=3)
    files: List[str] = Field(..., min_length=1,
                              description="Concrete file paths the task touches.")
    parallel_safe: bool
    fr_ids: List[str] = Field(..., min_length=1)
    failing_test_path: str = Field(..., min_length=1,
                                     description="Path to the failing test stub generated by sdet.")
    depends_on: List[str] = Field(default_factory=list,
                                    description="T-IDs of tasks that must complete first.")


class TaskList(_Strict):
    spec_id: str
    tasks: List[Task] = Field(..., min_length=1)

    @model_validator(mode="after")
    def task_ids_unique_and_deps_exist(self):
        ids = [t.id for t in self.tasks]
        _require_unique(ids, "Task ids")
        id_set = set(ids)
        for t in self.tasks:
            for dep in t.depends_on:
                if dep not in id_set:
                    raise ValueError(f"Task {t.id} depends on missing task {dep}")
        return self


# --------- TaskImplementation (agent response per task) --------------------

class FileWrite(_Strict):
    path: str = Field(..., min_length=1,
                       description="Path relative to the project root. Created if missing.")
    content: str = Field(..., description="Full file content (NOT a diff). UTF-8.")


class TaskImplementation(_Strict):
    task_id: str = Field(..., pattern=r"^T\d{3}$")
    files: List[FileWrite] = Field(..., min_length=1,
                                     description="Files to create or overwrite to satisfy this task.")
    test_passed: bool = Field(..., description="Self-reported; verified by the runner.")
    notes: str = Field(default="", description="Anything reviewer should know.")


# --------- ImplementationTrace ---------------------------------------------

class CommitTrace(_Strict):
    fr_id: str = Field(..., pattern=r"^FR-\d{3}$")
    task_id: Optional[str] = Field(None, pattern=r"^T\d{3}$")
    commit_sha: str = Field(..., min_length=7)
    files: List[str] = Field(default_factory=list)
    test_passed: bool


class ImplementationTrace(_Strict):
    spec_id: str
    commits: List[CommitTrace] = Field(default_factory=list)


# --------- Audit -----------------------------------------------------------

class PhaseAudit(_Strict):
    phase: Literal[
        "Requirements", "Design", "Development", "Test", "Security",
        "Performance", "Docs", "Deployment", "Rollback", "Monitoring",
    ]
    status: PhaseStatus
    evidence: Optional[str] = None
    owner: Optional[str] = None
    notes: Optional[str] = None


class ReviewerFinding(_Strict):
    reviewer: Literal[
        "delivery_manager", "security_engineer", "performance_engineer", "qa_engineer",
        "code_reviewer", "accessibility_specialist",
    ]
    summary: str = Field(..., min_length=10)
    blocking: bool


class Audit(_Strict):
    spec_id: str
    phases: List[PhaseAudit] = Field(..., min_length=1)
    reviewer_findings: List[ReviewerFinding] = Field(default_factory=list)
    recommendation: Literal["GO", "NO-GO", "GO-WITH-CONDITIONS"]


# --------- SpecDelta (brownfield) ------------------------------------------

class ModifiedRequirement(_Strict):
    id: str = Field(..., pattern=r"^FR-\d{3}$")
    before: str = Field(..., min_length=10)
    after: str = Field(..., min_length=10)
    rfc2119_after: RFC2119
    reason: str = Field(..., min_length=5)
    migration: Optional[str] = None


class Rename(_Strict):
    from_id: str = Field(..., pattern=r"^FR-\d{3}$")
    to_id: str = Field(..., pattern=r"^FR-\d{3}$")
    reason: str = Field(..., min_length=5)


class SpecDelta(_Strict):
    spec_id: str
    base_version: str = Field(..., min_length=1,
                                description="e.g. 'v1.2' or a commit SHA the delta applies against.")
    added: List[FunctionalRequirement] = Field(default_factory=list)
    modified: List[ModifiedRequirement] = Field(default_factory=list)
    removed: List[str] = Field(default_factory=list,
                                description="FR-IDs removed.")
    renamed: List[Rename] = Field(default_factory=list)

    @model_validator(mode="after")
    def at_least_one_change(self):
        if not (self.added or self.modified or self.removed or self.renamed):
            raise ValueError("SpecDelta must contain at least one change.")
        return self


# --------- Registry --------------------------------------------------------

SPEC_SCHEMAS = {
    "constitution": Constitution,
    "feature_spec": FeatureSpec,
    "clarification_log": ClarificationLog,
    "design": DesignPack,
    "plan": ImplementationPlan,
    "tasks": TaskList,
    "task_implementation": TaskImplementation,
    "implementation_trace": ImplementationTrace,
    "audit": Audit,
    "spec_delta": SpecDelta,
}
