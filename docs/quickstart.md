# Local Quickstart

For an independent consuming project, follow the [external project walkthrough](external-project-contract.md#cli-walkthrough). For development from source, install the locked development dependencies using the [README](../README.md).

```powershell
python -m porga doctor
python -m porga readiness
python -m porga demo --mode mock --request-key first-trial
python -m porga inspect RUN_ID
python -m porga report RUN_ID
```

Replace RUN_ID with the value returned by the demo. Review the report, QA, evidence checks, and proposal. To record a reviewed proposal decision, use `python -m porga approve PROPOSAL_ID --actor owner --note "Reviewed the evidence" --confirm`, or use `reject` with your reason. Proposal approval is separate from accepting a project's outcome and from deployment.

Start charter-based work with the [project intake guide](m1-projects.md). Use public or synthetic evidence for an initial trial. The offline model exercises real SDK orchestration with fixture outputs. The [operations guide](operations.md) covers budgets, recovery, and backups.
