# v0.3 Project Intake, Teams, and Acceptance

The first implemented M1 slice supports one local owner and public or synthetic evidence. See the [external project contract](external-project-contract.md) for the v0.4 consumer boundary.

Draft intake asks for the deliverable, acceptance criteria, exclusions, model mode, spending limits, and approved sources. Known fields are retained. The CLI persists charter revisions and returns missing fields for review. The normal chain uses four calls. The default cap is six calls per run.

```powershell
python -m porga project draft --spec examples/charter-research.json
python -m porga project inspect PROJECT_ID
python -m porga project authorize PROJECT_ID --digest DIGEST --actor owner --note "Reviewed the charter" --confirm
python -m porga project run PROJECT_ID --mode mock --request-key my-first-project
python -m porga report RUN_ID
python -m porga project accept PROJECT_ID --run-id RUN_ID --actor owner --note "Accepted the result" --confirm
```

Replace placeholders with actual IDs and the reviewed digest. Use `project revise PROJECT_ID --spec FILE` to append a revision. A complete draft still requires explicit authorization. New runs use the latest authorized revision. Resume retains the original charter, organization, and budget. Deduplication binds the request key to the same project, revision, input, and settings.

| Deliverable | Producer | Verification |
|---|---|---|
| research_report | Research | Independent QA and deterministic source and quotation checks. |
| evidence_audit | Evidence Auditor | The same checks plus required coverage of every approved source. |

The Chief proposes a structured plan, and the kernel selects only reviewed registry roles and capabilities. The saved organization records version, permissions, task dependencies, and selection rationale. The executor runs a serial checkpoint workflow. Natural-language acceptance criteria require owner review.

Starting a project, accepting a result, and approving an evolution proposal are separate decisions. Acceptance applies once to an eligible verified run for the current authorized revision. Proposal approval records a decision and does not deploy changes. The actor label is local attribution, not authentication.

## Upgrade and rollback

v0.3 migrates SQLite user_version 1 to 2 and creates pre-v0.3.sqlite3 before migration. Historical runs, checkpoints, reservations, and decisions are preserved. Older software must use a compatible snapshot in a separate location. Restore accepts the current database version and refuses populated destinations, including those with draft projects. To migrate an old backup, copy it to a separate empty data directory as porga.sqlite3 and run health with the new code. Preserve the original backup.

See the [delivery plan](architecture/delivery-plan.md) for the remaining M1 and later milestones.
