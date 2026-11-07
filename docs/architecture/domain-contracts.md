# A1 Domain Contracts

These objects describe planned interfaces. The [runtime protocols](../protocols.md) define accepted inputs for 0.4.

| Object | Identity and invariants |
|---|---|
| Project and CharterRevision | Immutable revision with goal, exclusions, success criteria, source scope, resources, assumptions, and stop conditions. |
| CapabilitySpec and AgentDefinition | Versioned input/output contract, allowed capabilities, runtime dependencies, evaluation, and retirement conditions. |
| AgentBinding and OrganizationRevision | Project-scoped pinned definitions, role permissions, allocation, graph, and selection evidence. Effective authority is the intersection of applicable policies. |
| TaskGraph, Task, and Attempt | A bounded graph with known dependencies. Each attempt records its lease generation, input revision, usage, and outcome. |
| ArtifactManifest and VerificationRecord | Evidence and results bind to content digests, rule versions, and an independent verifier. |
| MemoryRecord and SkillPackage | Scope, provenance, validity, verification, immutable version, and revocation. A Skill references already allowed tools. |
| ExperimentPlan and ExperimentResult | Freeze baseline, candidate, data, criteria, and costs before evaluation. Keep all case results. |
| ApprovalRecord and ReleaseManifest | Bind exact digests, policies, decisions, and compatible prior versions. Activation is separate from approval. |

Workspace, project, organization, role binding, task, and attempt have distinct identities. Protocol, software, database, policy, evaluation, and release versions evolve independently. Store timestamps consistently and make the budget day boundary explicit.

Commands are requests. Audit events are persisted facts. The kernel authenticates scope, enforces unique request keys with input fingerprints, and verifies aggregate revisions. Project, organization, task, tool, memory, evaluation, and release services own their records. Events contain references and metadata rather than sensitive raw content.

Migrate additively where possible. Preserve history, old reservations, and project identity. Unknown historical provenance stays unknown. Validate backups and migrations in isolated state before changing read/write paths.

## 0.7 knowledge acceptance

| Case | Pass criteria |
|---|---|
| K07-01 Reuse | A task can trace a project fact to a source, verifier, and applicable version. |
| K07-02 Isolation | A different project cannot read records or infer their contents or counts. |
| K07-03 Revocation | Expiry or contradictory evidence blocks new use and exposes affected dependencies. |
| K07-04 Classification | Raw evidence and hypotheses remain distinct from verified facts. |
| K07-05 Skill | A reviewed, evaluated package is digest-bound and does not expand permissions. |
| K07-06 Migration | Old artifacts, approvals, usage, and unknown states survive migration. |
| K07-07 Recovery | A failure leaves no partial migration, and a compatible backup restores independently. |

See [knowledge and evolution](evolution-memory.md).
