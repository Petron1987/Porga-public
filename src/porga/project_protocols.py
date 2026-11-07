"""Project intake and bounded organization contracts, additive to legacy run protocols."""

from decimal import Decimal
from typing import Literal

from pydantic import Field, model_validator

from porga.integration_protocols import ExternalBinding
from porga.protocols import Contract, Evidence

Role = Literal["chief", "research", "evidence_auditor", "qa"]


class ProjectInput(Contract):
    goal: str = Field(min_length=1, max_length=1000)
    evidence: list[Evidence] = Field(default_factory=list, max_length=8)


class CharterDraft(Contract):
    schema_version: Literal["0.3", "0.4"] = "0.3"
    project: ProjectInput
    deliverable: Literal["research_report", "evidence_audit"] | None = None
    success_criteria: list[str] = Field(default_factory=list, max_length=8)
    non_goals: list[str] = Field(default_factory=list, max_length=8)
    budget_scope: Literal["per_run"] = "per_run"
    max_usd: Decimal | None = Field(default=None, ge=0, le=100, allow_inf_nan=False)
    max_calls: int = Field(default=6, ge=4, le=20)
    data_scope: Literal["public_synthetic", "private"] | None = None
    external: ExternalBinding | None = None
    mode: Literal["mock", "openai"] | None = None
    require_all_sources: bool = False

    @model_validator(mode="after")
    def bounded_text(self):
        if not self.project.goal.strip() or len({e.id for e in self.project.evidence}) != len(
            self.project.evidence
        ):
            raise ValueError("A nonblank goal and unique evidence IDs are required")
        if any(not s.strip() or len(s) > 500 for s in self.success_criteria + self.non_goals):
            raise ValueError("Criteria and scope entries must be nonblank and bounded")
        if self.data_scope == "private" and self.external is None:
            raise ValueError("Private evidence requires an external project contract")
        if self.external:
            from porga.core.integration import sha

            spec = self.external.spec
            if self.schema_version != "0.4":
                raise ValueError("External charters require protocol version 0.4")
            if self.external.manifest_sha256 != sha(spec.model_dump(mode="json")):
                raise ValueError("External manifest digest differs")
            if (
                self.project.goal != spec.goal
                or self.deliverable != spec.deliverable
                or self.success_criteria != spec.success_criteria
                or self.non_goals != spec.non_goals
                or self.mode != spec.mode
                or self.max_usd != spec.max_usd
                or self.max_calls != spec.max_calls
                or self.data_scope != spec.classification
                or self.require_all_sources != spec.require_all_sources
                or [(e.id, e.title) for e in self.project.evidence]
                != [(s.id, s.title) for s in spec.sources]
            ):
                raise ValueError("Charter differs from external contract")
        return self


class CapabilitySpec(Contract):
    id: str
    purpose: str
    permissions: tuple[Literal["read_evidence"], ...]
    output_contract: Literal["ResearchReport", "QAReview"]


class AgentDefinition(Contract):
    role: Role
    version: Literal["0.3"] = "0.3"
    purpose: str
    capability_id: str
    permissions: tuple[Literal["read_evidence"], ...]
    output_contract: Literal["ResearchReport", "QAReview"]


class TaskNode(Contract):
    id: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,39}$")
    role: Role
    depends_on: list[str] = Field(default_factory=list, max_length=8)


class TaskGraph(Contract):
    nodes: list[TaskNode] = Field(min_length=3, max_length=8)

    @model_validator(mode="after")
    def acyclic(self):
        by_id = {n.id: n for n in self.nodes}
        if len(by_id) != len(self.nodes):
            raise ValueError("Duplicate task ID")
        producers = {n.id for n in self.nodes if n.role in ("research", "evidence_auditor")}
        verifiers = [n for n in self.nodes if n.role == "qa"]
        chiefs = [n for n in self.nodes if n.role == "chief"]
        if len(chiefs) != 1 or not producers or len(verifiers) != 1:
            raise ValueError("A chief, producer and separate QA are required")
        if set(verifiers[0].depends_on) != producers:
            raise ValueError("QA must depend on every producer")
        complete = set()
        while len(complete) < len(self.nodes):
            ready = {
                n.id for n in self.nodes if n.id not in complete and set(n.depends_on) <= complete
            }
            if not ready:
                raise ValueError("Unknown dependency or cycle")
            complete.update(ready)
        return self


class OrganizationRevision(Contract):
    schema_version: Literal["0.3"] = "0.3"
    project_id: str
    charter_revision: int
    agents: list[AgentDefinition]
    task_graph: TaskGraph
    rationale: str
