# A1 Architecture Decisions

These decisions guide implementation and acceptance. They do not authorize paid requests, external writes, publication, or multi-user services.

| ID | Decision | Revisit when |
|---|---|---|
| A01 | Keep five logical layers with the owner above them. | The owner changes the product boundary. |
| A02 | Start with a modular Python application and explicit ports. | Independent scaling or service isolation is necessary. |
| A03 | Use the OpenAI Agents SDK for runtime execution. | A task, quality, or cost requirement warrants another adapter. |
| A04 | Start with durable local state, Outbox/Inbox, and a bounded worker. | Long waits, compensation, or worker version changes exceed the design. |
| A05 | Use receipts and reconciliation for uncertain effects. | A connector offers verified idempotency guarantees. |
| A06 | Define scoped, versioned knowledge before vector search. | Retrieval tests show a need for another index. |
| A07 | Test one prompt or declarative Skill improvement before organization changes. | M4 comparison and rollback pass. |
| A08 | Record approval and activate a release as separate actions. | Authorization or compatibility changes. |
| A09 | Require human decisions for adoption under the current policy. | The owner authorizes a separately evaluated policy. |
| A10 | Pin immutable organization revisions to running work. | Emergency revocation or migration requires explicit handling. |
| A11 | Use public or synthetic domain templates and fixtures. | A real use case has its own reviewed authorization. |
| A12 | Consider a server store only for an approved shared-service need. | Identity, isolation, and operations requirements are agreed. |
| A13 | Deliver SDK/CLI activation, a thin Skill, MCP, then Worker/HTTP as needed. | Integration acceptance or actual long-running work changes the priority. |

See the [integration delivery sequence](delivery-plan.md#integration-delivery-sequence). Community 0.4.0 uses MIT and the official repository is `Petron1987/Porga-public`. Model quality targets, deployment, external publication, and new licensing decisions require separate review. Treat a protocol, diagram, or mock run as evidence only for the capability it actually exercises.
