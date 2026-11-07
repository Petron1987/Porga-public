# A1 Delivery and Acceptance Plan

Advance by observable acceptance evidence. Preserve the prior working path at each stage. Use approved public or synthetic cases and start offline. The 0.4 local pilot delivers a bounded portion of M1, including the external project contract. See the [release path](release-path.md).

| Stage | Depends on | Deliverable and acceptance |
|---|---|---|
| B0 | Existing baseline | Research and QA, artifacts, independent gates, budget, decisions, cancellation, recovery, and backups. |
| M1 | B0 | Authorized project charters, an approved capability registry, pinned organizations, and task graphs. Different goals yield explainable plans. Missing authority, unsupported capabilities, cycles, and invalid QA stop execution. |
| M2 | M1 task and version contracts | Durable attempts, leases, outbox, inbox, cancellation, and bounded scheduling. Exercise crashes, duplicate delivery, expiry, reconciliation, and budgets. See [execution governance](execution-governance.md). |
| M3 | M1 identity and M2 provenance | Scoped, versioned knowledge and declarative Skills. Verify provenance, expiry, revocation, and cross-project isolation. |
| M4 | M2, M3, and frozen evaluation rules | Independently compare one candidate against a baseline. Record approval separately from adoption, monitor the result, and exercise rollback. |
| M5 | M4 | Compare a split, merge, replacement, or retirement. Preserve verification independence, old tasks, and history. Show measurable improvement without increasing authority. |
| M6 | M1 for synthetic templates, M4/M5 for improvement claims | Run at least two domain templates on the same kernel. Track evidence and feedback while keeping domain rules and project state separate. |
| M7 | Explicit shared-service need and separate scope | Authenticate and isolate tenants, migrate to a server store, and validate backups, access, concurrency, spending, and recovery. |

P0 is a governed kernel. P1 adds bounded team execution. P2 adds knowledge and measured improvements. P3 changes organization topology with evidence. P4 addresses authorized continuing operations. These levels describe capabilities and do not map directly to package versions.

Record faults, unknown external results, and negative experiments. Reject candidates that miss acceptance criteria. M7 and any production action need explicit owner review.

## Integration delivery sequence

1. **SDK and CLI activation.** An independent project may be unfinished. Explicit activation creates a reviewable intake proposal, limited inventory, and evidence list. Install and import remain side-effect free. Preserve source boundaries, hashes, egress consent, and budget checks.
2. **Thin integration Skill.** Guide supported assistants through the same approved SDK or CLI. Keep authorization, budget, recovery, and verification in the kernel. M3 Skill promotion is a separate mechanism.
3. **MCP adapter.** Expose a bounded set of structured operations, including preview, authorized submission, status, results, and cancellation. Test equivalent input, duplicated submission, disconnects, and forbidden scope. Reliable background jobs depend on the necessary M2 acceptance.
4. **Worker and HTTP services.** Add a local worker for a documented recurring or long-running need. Consider HTTP for a separate remote-access need. Validate bounded operation and reconcile crashes, costs, and unknown effects. Remote services need identity and isolation and cannot assume access to client-local files.

See the [external project contract](../external-project-contract.md) and the [current M1 implementation](../m1-projects.md).
