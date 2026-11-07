# Local Operations

The current pilot targets a single trusted local operator. See [project intake](m1-projects.md) and the [external project contract](external-project-contract.md) for scoped project workflows.

## Runs and decisions

Use `doctor` and `readiness` to inspect the local setup. Run `python -m porga demo --mode mock --request-key first-trial` for a reproducible SDK workflow with synthetic outputs. Identical input and settings reuse a request key. Choose a new key for a changed objective or budget.

Use `status`, `inspect RUN_ID`, and `report RUN_ID` to inspect results. Legacy report exports update the named files under the data directory. External project exports use separate subdirectories. Read the original evidence when assessing whether a report satisfies its charter.

```powershell
python -m porga approve PROPOSAL_ID --actor owner --note "Reviewed the evidence" --confirm
```

A proposal decision is recorded once. Approval checks linked artifacts and project digests. It records a decision without deploying a change.

## Interruptions and costs

After confirming the old process has exited, use `recover RUN_ID` followed by `resume RUN_ID`. Recovery records interrupted state without calling a model. Resume verifies and reuses completed checkpoints. A v0.1 run without recorded settings remains inspectable but cannot resume.

Use `cancel RUN_ID` to stop at the next safe boundary. A call already sent can still be billed. Recover an abandoned cancel_requested run before concluding it stopped. Unknown online outcomes preserve their reservations. Resume such work only after explicit replay consent with `--allow-replay`. The original budget and recorded prices remain in effect.

Set the key, model, and unit prices in the host environment when opting into paid use. The local defaults are USD 0.50 per run and USD 2.00 per day per state directory. The daily boundary is UTC+08:00. Estimates are separate from provider billing. A reservation is made transactionally before each request. Failed or unknown calls retain their reservations.

## Backup and restore

```powershell
python -m porga health
python -m porga evaluate
python -m porga backup
python -m porga --data-dir .porga-restored restore BACKUP_FILE_PATH
python -m porga --data-dir .porga-restored health
```

Restore verifies a compatible snapshot and refuses a populated destination. The migration snapshots are pre-v0.2.sqlite3, pre-v0.3.sqlite3, and pre-v0.4.sqlite3. Preserve the original snapshot and run old code only against compatible state in a separate location. The external project's database binds to its root, so moving it does not transfer authorization.

Before using live models for real work, define quality and cost criteria and evaluate representative approved tasks. Health and fixed gate regression tests measure integrity and control flow.

## 1.0 release acceptance draft

| Case | Required evidence |
|---|---|
| R10-01 Clean installation | Supported OS and Python combinations, wheel digest, installed import location, and SDK/CLI synthetic outputs. |
| R10-02 Compatibility | Tested manifest and protocol versions, return fields, exit codes, exports, and negative authorization cases. |
| R10-03 Upgrade | Source version, backup integrity, migration result, historical state, and preserved reservations. |
| R10-04 Recovery | Interrupted work, failed migration, compatible rollback, and reconciliation of outstanding actions and costs. |
| R10-05 Representative tasks | Predeclared criteria, costs, actual run mode, and owner decisions for each case. |
| R10-06 Publication review | Reviewed history, files, license, install artifacts, hashes, permissions, and the owner's release decision. |

Record pass, fail, or not run for each candidate and environment. An application release, an organization rollback, and a database recovery have different scopes. Preserve upgraded data and reconcile new work before recovering from an earlier backup. See the [release path](architecture/release-path.md) and [governance](governance.md#publication).
