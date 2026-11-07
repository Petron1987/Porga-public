# Roadmap · reconciled A1 architecture

Current local software: **v0.4.0**, a governed local kernel with external project SDK/CLI,
explicit file/egress boundaries, version pins, charter authorization,
two bounded team profiles, separate owner acceptance, durable governance and recovery.
This is the first M1 slice, not completion of general dynamic teaming.
The external consumer contract extends this slice; it does not add a scheduler or real evolution.
A1 is the long-term design baseline, not a new runtime release. Original-discussion source
and gaps: [audit](design/conversation-audit.md) and [40 requirements](design/requirements.json).

| Milestone | Delivered capability required | Main prerequisite |
|---|---|---|
| B0 (preserved) | Fixed Research/QA, artifacts, gates, budgets, decisions, recovery | Historical 45-test local baseline |
| M1 (first slice delivered) | Charter authorization, two registry profiles, graph snapshot and acceptance; broader candidate/reuse lifecycle still pending | 75 offline tests; real model/owner task acceptance pending |
| M2 | Durable task graph, attempt/lease/fencing, outbox/inbox, bounded local scheduler | M1 task and version contracts |
| M3 | Six scoped knowledge types and evaluated declarative Skill promotion | M1 identity and M2 provenance |
| M4 | One actual candidate improvement independently evaluated, approved, released and reversible | M2/M3 plus frozen evaluation policy |
| M5 | Measured split/merge/replace/retire organization experiments | M4 evaluation and release pipeline |
| M6 | Public/synthetic industry blueprints with traceable business feedback | Synthetic templates may start after M1; improvement claims need M4/M5 |
| M7 (separate scope) | Shared authenticated service, server state and operations | Owner confirms multi-device/multi-user need |

## External adoption priorities · owner-confirmed 2026-11-06

The next integration work follows this order. These are planned delivery steps, not new
implemented capabilities or permission to publish. All entry points use the same kernel,
project isolation, budgets, authorization and verification.

| Order | Planned work | Current state / relation to M1–M7 |
|---|---|---|
| 1 | Improve lightweight SDK/CLI activation so unfinished projects can begin easily | SDK/CLI exist in v0.4; initialization, bounded discovery and generated intake drafts remain planned M1 extensions |
| 2 | Provide a thin integration Skill so existing AI assistants can use Porga correctly | Not implemented; wraps the approved SDK/CLI workflow, independently of M3 learned Skill promotion |
| 3 | Add an MCP interface for structured calls from AI assistants | Not implemented; adapter over the same application services, with no self-approval or permission expansion |
| 4 | Build Worker and HTTP services when sustained background work or remote access is needed | Not implemented; local durable execution maps to M2, authenticated shared/remote services to the relevant M7 scope |

No project maturity test is required: a draft, partial project or document directory may
enter intake. Data access, model egress, spending and writes still need explicit authority.
Installation/import does not start scanning, billing or background work; one explicit
activation should lead to bounded discovery and a reviewable agreement with few critical
questions. Missing project information becomes work to clarify, not an invented answer.

Worker and HTTP delivery are separate decisions. M2 reliability remains a prerequisite
where long-running work needs it; an MCP adapter does not establish durable execution.
The knowledge/evolution milestones M3–M5 retain their existing dependencies and acceptance
gates. Detailed scope and acceptance are in the
[integration delivery sequence](architecture/delivery-plan.md#integration-delivery-sequence).

Exact deliverables, fault cases, dependencies and acceptance conditions:
[A1 delivery plan](architecture/delivery-plan.md).
For a proposed 1.0 scope and a directory-by-milestone map, see the
[1.0 architecture and release path](architecture/release-path.md).

P0–P4 maturity stages are not software version numbers. No stage is complete merely
because a directory, protocol class, architecture diagram or improvement proposal exists.
No milestone grants permissions for paid calls, private data, external actions or publication.
