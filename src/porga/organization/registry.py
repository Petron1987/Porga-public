"""Code-reviewed capability registry; models cannot register arbitrary code or tools."""

from porga.organization.factory import PermissionDenied
from porga.project_protocols import AgentDefinition, CapabilitySpec, OrganizationRevision, TaskGraph

CAPABILITIES = (
    CapabilitySpec(
        id="synthesize_evidence",
        purpose="Synthesize bounded evidence into a report",
        permissions=("read_evidence",),
        output_contract="ResearchReport",
    ),
    CapabilitySpec(
        id="audit_evidence",
        purpose="Inspect coverage, gaps and limitations of evidence",
        permissions=("read_evidence",),
        output_contract="ResearchReport",
    ),
    CapabilitySpec(
        id="verify_report",
        purpose="Independently review a report against original sources",
        permissions=(),
        output_contract="QAReview",
    ),
)


def definitions():
    return tuple(
        AgentDefinition(
            role=role,
            purpose=c.purpose,
            capability_id=c.id,
            permissions=c.permissions,
            output_contract=c.output_contract,
        )
        for role, c in zip(("research", "evidence_auditor", "qa"), CAPABILITIES, strict=True)
    )


def worker_for(deliverable):
    return {"research_report": "research", "evidence_audit": "evidence_auditor"}[deliverable]


def organization(project_id, revision, draft, roles, policy):
    expected = [worker_for(draft.deliverable), "qa"]
    if roles != expected or len(roles) > policy.max_subagents:
        raise PermissionDenied("Team is inconsistent with approved deliverable or team limit")
    selected = [d for d in definitions() if d.role in roles]
    for definition in selected:
        if not set(definition.permissions) <= set(policy.capabilities):
            raise PermissionDenied("Definition exceeds kernel policy")
    graph = TaskGraph(
        nodes=[
            {"id": "chief", "role": "chief", "depends_on": []},
            {"id": "produce", "role": roles[0], "depends_on": ["chief"]},
            {"id": "verify", "role": "qa", "depends_on": ["produce"]},
        ]
    )
    return OrganizationRevision(
        project_id=project_id,
        charter_revision=revision,
        agents=selected,
        task_graph=graph,
        rationale="Selected approved capabilities for "
        + draft.deliverable
        + "; QA remains separate from the producer",
    )
