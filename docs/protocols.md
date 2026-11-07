# Protocols · local pilot 0.4

Source of truth: `src/porga/protocols.py` and `src/porga/project_protocols.py`.
External consumer types are in `src/porga/integration_protocols.py`; public SDK in `porga.api`.
Generated interchange schemas are in
`protocols/*.schema.json`; run `python scripts/generate_schemas.py` after changes.
All contracts reject extra fields. Model outputs use SDK structured output validation.
These are minimal slices of the original target contracts. The v0.2 gaps were recorded in the
[source audit](design/conversation-audit.zh-CN.md). Matching protocol names do not establish
full implementation of the original design. See [v0.3 scope](m1-projects.zh-CN.md) for the
new bounded charter/organization slice; knowledge and experiment/adoption remain future work.

| Contract | Core fields / invariant |
|---|---|
| ProjectSpec | schema_version=0.1, bounded goal and approved evidence bundle |
| AgentSpec | research/evidence_auditor/qa, version 0.1 or 0.3, allowlisted capabilities |
| TaskSpec | run/role/status/artifact linkage; lifecycle owned by kernel |
| Artifact | run, kind, canonical content and SHA-256 |
| PermissionPolicy | max two specialists; shell/external_write/self_approve=false |
| EvaluationGate | named boolean checks, issues, combined acceptance |
| EvolutionProposal | linked evaluation, pending/approved/rejected, never applied |
| Plan / ResearchReport / QAReview | structured outputs from each SDK agent |
| RunSpec (0.2) | running/failed/interrupted/cancel_requested/cancelled and final states |
| CharterDraft (0.3) | goal/evidence, deliverable, success criteria, non-goals, mode, cost/call limits, data scope |
| CapabilitySpec / AgentDefinition (0.3) | code-reviewed registry, bounded tool permissions and output contracts |
| TaskGraph (0.3) | unique IDs, known dependencies, acyclic, separate producer and dependent QA |
| OrganizationRevision (0.3) | project/charter revision, selected definitions, graph and selection rationale |
| ExternalProjectSpec (1) | exact software pin, explicit source paths/digests, state/output paths, classification, egress and task limits |
| ExternalBinding (1) | canonical project root, manifest path/digest and frozen contract |
| RunOptions | host model/prices and resource limits, no path/mode override |

External charters use version 0.4 and embed the binding. Legacy 0.3 charters remain readable.
Private classification requires an external binding and never implicitly allows egress.
See [external contract v1](external-project-contract.zh-CN.md) for live boundary checks,
explicit OpenAI consent and historical snapshot semantics.

## State transitions

- Task: running -> completed or failed. `pending` is reserved for a future queue.
- Run: running -> awaiting_approval or validation_failed; handled exception -> failed.
- Run after a decision: approved or rejected.
- Abandoned running -> interrupted through explicit recover; failed/interrupted -> running
  through explicit resume, using original stored settings and completed checkpoints.
- Active cancellation: running -> cancel_requested -> cancelled at a checked boundary.
- Proposal: pending -> approved or rejected, exactly once. Failed/tampered evaluation
  prevents approval. Rejection is still allowed.
- Deployment: always not_applied. No implicit state transition applies a proposal.
- Charter: draft -> needs_answers or awaiting_owner_authorization -> authorized. Revisions
  append records and need a new digest-bound authorization; no in-place revision edits.
- Outcome: owner_accepted is a separate durable record, bound to charter/organization/artifact
  hashes after successful gates. It does not modify a run's proposal decision or deploy anything.

## Gate semantics

Every evidence ID must be unique, every finding must refer to an approved source, every
quote must be a literal substring of that source, and QA must pass with zero issues.
These checks establish bounded provenance, not source authenticity/freshness or proof
that the generated summary follows logically. Input evidence remains operator-approved
data. Unknown sources and fabricated quotes fail even if the model QA says "passed".
Evidence audits (or require_all_sources=true) additionally require every approved evidence ID
to appear in findings. These gates do not automatically evaluate arbitrary natural-language
success criteria; those are passed to agents and reviewed by the human accepting the outcome.

## Compatibility

Project/agent protocols retain 0.1 wire compatibility. RunSpec is additive at version 0.2.
SQLite user_version=1 adds run configuration, request key, project digest, and durable
reservations through an additive migration, with a pre-upgrade backup. Original records
remain inspectable; legacy runs cannot resume because their original settings are unknown.
SQLite user_version=2 adds projects, immutable charter revisions, explicit authorizations,
run/charter bindings, organization snapshots and acceptance records. v0.2 data is backed up
to pre-v0.3.sqlite3 before upgrade; existing checkpoints and budgets remain. Old code refuses
the upgraded database. Future database versions are refused. See [migration/rollback](m1-projects.zh-CN.md).

user_version=3 fences older programs from external/private contracts without dropping data
or changing tables. v0.3 upgrades write pre-v0.4.sqlite3 first; rollback uses the old code
with that snapshot in a separate directory. Health uses frozen evidence; start/resume
also verify the current manifest, root, source hashes and state binding.
