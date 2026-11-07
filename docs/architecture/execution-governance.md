# A1 Execution and Governance

Plan a bounded local worker after the current checkpoint workflow. Commit the task transition and Outbox message together. Consume events at least once and deduplicate with an Inbox and stable request IDs. An attempt records the worker, lease expiry, and a fencing token. An expired worker cannot commit state or settle a new attempt.

Track dependencies, ready work, claims, running attempts, waits, retries, reconciliation, cancellation, and terminal failures. Distinguish task completion from artifact acceptance. Pin configuration and budgets. A repeat claim does not reset spending.

Unknown outcomes preserve receipts and reservations and move to reconciliation. Retry pure local work only within approved limits. Repeat an external action only when its status is known or an explicit idempotency or replay policy permits it. A cancellation stops future work at a safe boundary; sent requests may still have effects or charges.

Schedules pin project, version, time zone, next trigger, budget, and a missed-trigger policy. Use the scheduled instant and version to deduplicate. Choose skip, coalesce, or bounded catch-up. A local worker depends on a running machine and process.

Effective authority comes from trusted platform, workspace, project, role, task, and action policies. Credential access stays with the host. Treat approval as scoped, digest-bound, expiring, and revocable. The owner controls changes to policy and budgets. Preserve costs in an append-only ledger. Limit queue age and size, concurrent calls, and provider capacity. Alert the owner about meaningful failures, decisions, or stop conditions.

## 0.6 interface and failure acceptance

MCP may preview authorized material, submit authorized tasks, read scoped status or results, and request cancellation. Owner-only operations remain outside model tools. Background or reconnect behavior needs the applicable M2 acceptance.

| Case | Pass criteria |
|---|---|
| E06-01 Entry points | SDK, CLI, and MCP agree on identity, request fingerprints, authorization, and scoped results. |
| E06-02 Outbox | A crash before commit leaves no work. A crash after commit allows one logical delivery. |
| E06-03 Lease | Reclaiming records a new attempt. A stale worker cannot commit or settle. |
| E06-04 Unknown outcome | Reconcile receipts and keep reservations before any approved retry. |
| E06-05 Artifact | Recover from a persisted receipt and result. Downstream work sees only one accepted outcome. |
| E06-06 Disconnect | Find the persisted submission after reconnect and stop new calls after cancellation. |
| E06-07 Schedule | Restarts and duplicate events preserve one run per planned instant and enforce catch-up bounds. |
| E06-08 Budget | Exhaustion, revoked authority, or an unavailable verifier stops additional work. |

Record task and attempt IDs, fault points, receipts, transitions, and usage evidence. See the [delivery plan](delivery-plan.md).
