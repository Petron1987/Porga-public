# v0.3 local verification · 2026-11-05

Windows / Python 3.11.9 / openai-agents 0.24.0. The software version is 0.3.0;
this is an Early Alpha single-user local pilot, implementing the first bounded M1 slice.

| Check actually performed | Result |
|---|---|
| pytest, including the prior 45-test baseline | 75 passed |
| Ruff src/tests/scripts | Passed |
| Dependency consistency | No broken requirements |
| Generated interchange schemas | 16 from runtime models |
| Two deliverable profiles through actual SDK Agent/Runner | Research/QA and Evidence Auditor/QA, each 4 mock calls / USD 0 |
| Offline budget accounting with configured live prices | Stored per-run limit 0, mock estimated cost 0; live zero budgets refused |
| Revision, authorization and input/cost/call boundaries | Stale/missing/excess authority rejected before specialist execution; direct execution substitution rejected before any model call |
| Audit with omitted source and permissive mock QA | Deterministic coverage gate failed; owner acceptance rejected |
| Owner acceptance | Independent record; evolution proposal still pending and never deployed |
| Restart and revision change | Old run resumed its original authorized charter/organization; new charter required new authorization |
| Data upgrade | v0.1 and v0.2 fixtures preserved; v0.2 snapshot written before additive version-2 migration |
| Backup/restore | New project/authorization/acceptance retained; draft-only destination and damaged records refused |

Tests prohibit outbound connections. Online adapter tests use an in-memory HTTP transport;
no paid model call or real project consent was fabricated. Human labels in temporary test
databases are synthetic fixtures. A complete example draft in the delivered local review
directory awaits actual owner authorization.

The prior remote check returned a startup failure with zero jobs. The cause remained
undetermined, and the acceptance results above describe local verification.

Remaining limits: two explicit profiles rather than arbitrary goal-driven organization;
serial checkpoints rather than a general task-graph scheduler; fixture mock intelligence;
human review of subjective success criteria; no measured live-model acceptance, memory/Skill
promotion, recurring article/video learning, real candidate adoption/rollback or multi-user
authentication. Hashes detect ordinary corruption; they cannot secure a database against
its trusted local operator. Production readiness remains false.
