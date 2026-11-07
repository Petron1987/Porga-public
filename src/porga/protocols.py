"""Versioned, fail-closed wire contracts. Models never receive persistence handles."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Evidence(Contract):
    id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,64}$")
    title: str = Field(min_length=1, max_length=200)
    text: str = Field(min_length=8, max_length=4000)


class ProjectSpec(Contract):
    schema_version: Literal["0.1"] = "0.1"
    goal: str = Field(min_length=1, max_length=1000)
    evidence: list[Evidence] = Field(min_length=1, max_length=8)

    @model_validator(mode="after")
    def validate_inputs(self):
        if not self.goal.strip() or len({e.id for e in self.evidence}) != len(self.evidence):
            raise ValueError("A nonblank goal and unique evidence IDs are required")
        return self


class RunSpec(Contract):
    schema_version: Literal["0.2"] = "0.2"
    id: str
    mode: Literal["mock", "openai"]
    status: Literal[
        "running",
        "failed",
        "interrupted",
        "cancel_requested",
        "cancelled",
        "awaiting_approval",
        "validation_failed",
        "approved",
        "rejected",
    ]
    request_key: str | None = None


class PermissionPolicy(Contract):
    """Hard kernel boundary, not a model-editable suggestion."""

    capabilities: tuple[Literal["read_evidence"], ...] = ("read_evidence",)
    max_subagents: int = Field(default=2, ge=1, le=2)
    external_write: Literal[False] = False
    shell: Literal[False] = False
    self_approve: Literal[False] = False


class AgentSpec(Contract):
    role: Literal["research", "evidence_auditor", "qa"]
    version: Literal["0.1", "0.3"] = "0.1"
    capabilities: tuple[Literal["read_evidence"], ...] = ()


class Plan(Contract):
    research_question: str = Field(min_length=1, max_length=1000)
    roles: list[Literal["research", "evidence_auditor", "qa"]] = Field(min_length=2, max_length=2)


class Finding(Contract):
    evidence_id: str = Field(min_length=1, max_length=64)
    quote: str = Field(min_length=8, max_length=1000)


class ResearchReport(Contract):
    summary: str = Field(min_length=1, max_length=2000)
    findings: list[Finding] = Field(min_length=1, max_length=8)
    uncertainties: list[str] = Field(max_length=8)


class QAReview(Contract):
    passed: bool
    issues: list[str] = Field(max_length=8)


class EvaluationGate(Contract):
    passed: bool
    checks: dict[str, bool]
    issues: list[str]


class TaskSpec(Contract):
    id: str
    run_id: str
    role: Literal["chief", "research", "evidence_auditor", "qa"]
    status: Literal["pending", "running", "completed", "failed"]
    artifact_id: str | None = None


class Artifact(Contract):
    id: str
    run_id: str
    kind: str
    sha256: str
    content: dict


class EvolutionProposal(Contract):
    id: str
    run_id: str
    status: Literal["pending", "approved", "rejected"]
    change: str
    rationale: str
    evaluation_id: str
    evidence_passed: bool
    deployment: Literal["not_applied"] = "not_applied"
