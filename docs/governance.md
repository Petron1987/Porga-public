# Governance and operating limits

## Capability matrix

| Actor | Allowed | Denied |
|---|---|---|
| Chief | Propose bounded question and Research/QA plan | Spawn arbitrary roles, alter policy |
| Research | Read this project's evidence through a zero-argument tool | Paths, URLs, shell, writes |
| QA | Review supplied report and original evidence | Tools, policy edits, self-approval |
| Kernel | Validate, persist, meter, propose | External publication |
| Human CLI | Inspect, approve/reject once | Automatic deployment (not implemented) |

Factory limits are role-specific and constrained by immutable PermissionPolicy. Unknown
fields/capabilities fail validation. There are no generic code execution or web tools.
An adversarial model can still generate misleading text, so deterministic gates and human
review remain necessary. Do not treat model prose as an instruction to grant permissions.

## Costs and logs

Each model call reserves a conservative serialized byte/token allowance with a framing
margin and capped output. The ledger rejects calls that exceed per-run request/token/USD
limits; reported usage replaces the reservation only on successful responses. Missing
usage, timeout, and errors stop the run and retain the reservation in audit history.
Prices are owner-configured estimates. v0.2 shares a transactionally reserved daily estimate
cap across runs/processes in the same data directory, by UTC+08:00 reservation date. This
is not an account-wide cap across separate directories/computers. No pricing API or billing
reconciliation is implemented. Original task budgets remain fixed during resume; unfinished
online work requires explicit replay authorization and keeps unknown-call reservations.

SDK hosted tracing is disabled programmatically. Online Responses requests use store=false;
this is not a claim of zero data retention by the provider. No prompt/response/key values
are placed in audit metadata or echoed in CLI errors. The local database stores project
evidence and full artifacts, so protect that directory using OS account permissions and
delete/archive it according to your own data policy. Git ignores it by default.

## Approval and integrity

`--confirm`, actor, and note are required for a CLI decision. Agents have no approval tool.
This protects the application workflow, not against a user or other process able to edit
the same local files. A local actor string is an attribution label, not authentication.
Approvals check all linked run artifacts and project content, not only the evaluation.
Content hashes detect accidental/tampered content unless a local attacker also changes
the hashes; external signing and tamper-evident storage are deferred.

## Publication

The official Community repository is `Petron1987/Porga-public`. The owner approves
publication and licensing decisions. Inspect the tree and history to be published for
private data and credentials. Distribute source, protocols, tests, documentation, and
synthetic examples. The [MIT License](../LICENSE) applies to this Community distribution.

The owner is the sole maintainer after publication. Only the owner writes to the official
repository, merges changes, creates tags and releases, or changes settings and access.
Readers and trial users can use an issue to report a problem with a sanitized reproduction.
The owner decides whether and how to incorporate the feedback.

Review access before publication and after any access change. Remove write, maintain, and
admin grants to other people and check app installations, deploy keys, token scopes, and
workflow permissions. Keep CI at contents read and publish releases manually as owner.
This policy applies to the official repository. An approved license governs what people
may do with their separate copies.
