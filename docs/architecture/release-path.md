# Porga Release Path

The running baseline is **Community 0.4.0 Alpha**. It delivers the first bounded M1 slice. OpenAI Agents SDK supplies the model and tool loop. Porga owns authorization, planning, state, spending, verification, and release boundaries. SQLite and Pydantic support local persistence and data validation.

| Proposed version | Scope | Acceptance evidence |
|---|---|---|
| 0.1–0.4 | Local kernel, recovery, charter authorization, bounded teams, external SDK and CLI. | Versioned verification records and a synthetic external project. |
| 0.5 | Lightweight activation, explainable team selection, thin integration Skill. | Scoped intake, required review, fixed definitions, and an accepted result. |
| 0.6 | Bounded MCP interface and durable local work when needed. | Equivalent entry points, deduplication, crash recovery, budgets, and cancellation. |
| 0.7 | Project-scoped knowledge and declarative Skill promotion. | Provenance, isolation, expiry, revocation, and migration. |
| 0.8 | One independently validated improvement. | Frozen baseline and holdout, separate owner approval and adoption, monitored rollback. |
| 0.9 | Evidence-based organization changes and domain template reuse. | Controlled comparisons and isolated synthetic projects. |
| 1.0 | Stable local workflows, external contracts, and release maintenance. | Representative cases, clean installation, compatibility, upgrade, recovery, and rollback. |

Version numbers are planning labels. Advance after acceptance. Multi-user service, HTTP, and a permanently running worker depend on demonstrated needs and their own authorization.

Keep SDK/CLI adapters above shared application services. Use [project intake](project-genesis.md), [execution](execution-governance.md), [domain contracts](domain-contracts.md), and [evolution](evolution-memory.md) to guide implementation. See [operations](../operations.md#10-release-acceptance-draft) for release verification. Do not create empty modules to represent planned features. Maintain explicit responsibilities and add code only as each deliverable arrives.

For each acceptance case, record the candidate version, input or environment, observed result, and limits. The [delivery plan](delivery-plan.md) defines milestone dependencies. The [governance policy](../governance.md#publication) defines ownership and publication controls.
