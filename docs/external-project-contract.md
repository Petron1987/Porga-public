# External Project Contract v1

Porga Community 0.4.0 provides an experimental local SDK and CLI for independent projects. The consumer owns its evidence, rules, state, and acceptance decisions. Porga receives a reviewed snapshot of explicitly listed sources.

## Manifest and scope

The directory containing the manifest is the project root. Paths resolve relative to that directory, regardless of the caller's working directory.

| Field | Contract |
|---|---|
| schema_version | String "1". Unknown fields and versions are rejected. |
| project_key | Stable project identifier, bound to the canonical root in the state database. |
| porga_version | Exact installed software version, currently 0.4.0. |
| sources | One to eight explicit files with ID, title, relative path, and lowercase SHA-256 of raw bytes. |
| state_dir and output_dir | Distinct scoped paths. The defaults are .porga and porga-results. |
| goal and deliverable | A stated objective and either research_report or evidence_audit. |
| success_criteria and non_goals | The conditions the owner reviews and the exclusions the workflow must respect. |
| classification | Defaults to private. Use public_synthetic only when it accurately describes the evidence. |
| egress and mode | Default to deny and mock. Online mode requires openai egress, consent, and a positive budget. |
| max_usd and max_calls | Per-run limits. The lower of the manifest and host limits applies. |
| require_all_sources | Defaults to true. Enables the deterministic source coverage check. |

The v1 adapter accepts complete small UTF-8 text, Markdown, or JSON files. A file can contain at most 16,000 bytes and 8 to 4,000 decoded characters. Prepare and label excerpts separately when using larger or unsupported materials. JSON is treated as text evidence.

The adapter rejects absolute paths, parent traversal, drive or UNC paths, device names, alternate streams, symlinks, junctions, hard links, and internal paths such as .env, .git, and .venv. State and output directories cannot be used as sources. The example includes a Git ignore file for the default state and output locations.

## Consent and stored data

Online execution requires explicit mode and egress configuration, a positive budget, a reviewed charter snapshot, and owner authorization with the separate OpenAI consent flag. Configure the key, model, and prices on the host. The SDK authorization method is reserved for the trusted host or owner.

An online call may send the goal, evidence, criteria, exclusions, and intermediate outputs to the provider. The local database and exported snapshot can contain the complete evidence bundle. Store them as project data. The egress setting controls Porga's model path and does not provide host-wide network isolation.

## CLI walkthrough

Install the Community wheel, open PowerShell at the extracted source root, and copy the supplied synthetic project to an independent folder. Run each block separately and resolve any nonzero exit before continuing.

```powershell
$porgaExample = (Resolve-Path 'examples/external-project').Path
$porgaTrial = Join-Path ([IO.Path]::GetTempPath()) ("porga-trial-" + [guid]::NewGuid().ToString('N'))
Copy-Item -LiteralPath $porgaExample -Destination $porgaTrial -Recurse
$porgaManifest = Join-Path $porgaTrial 'porga.project.json'
python -m porga external preview --manifest $porgaManifest
$porgaDraft = python -m porga external attach --manifest $porgaManifest | ConvertFrom-Json
python -m porga external inspect --manifest $porgaManifest
```

Preview produces a reviewable snapshot without creating state. Attach saves a draft without granting authority. Review the objective, evidence, limits, and digest, then authorize the synthetic trial as its owner.

```powershell
python -m porga external authorize --manifest $porgaManifest --digest $porgaDraft.digest --actor owner --note "Reviewed the synthetic trial scope" --confirm
$porgaRun = python -m porga external run --manifest $porgaManifest --request-key first-task | ConvertFrom-Json
if ($LASTEXITCODE -ne 0 -or -not $porgaRun.validation_passed) { throw 'Trial did not pass verification.' }
$porgaReport = python -m porga external report $porgaRun.run_id --manifest $porgaManifest | ConvertFrom-Json
Get-Content -LiteralPath $porgaReport.report
```

The supplied manifest uses mock mode and denies egress. Check the source coverage and the actual report against the charter, then record acceptance.

```powershell
python -m porga external accept $porgaRun.run_id --manifest $porgaManifest --actor owner --note "Reviewed the report against the charter" --confirm
```

Expect owner_accepted. Repeating the same request key with identical authorized input reuses the run. Each export uses a unique output directory. The CLI does not implicitly read the caller's .env or use PORGA_DATA_DIR and PORGA_MODE to override the manifest.

## Python SDK

```python
from porga.api import ProjectClient, RunOptions

client = ProjectClient("path/to/porga.project.json")
preview = client.preview()
draft = client.attach()
# The owner reviews the full draft before calling authorize.
client.authorize(draft["digest"], actor="owner", note="Reviewed the charter")
result = await client.run(options=RunOptions(), request_key="first-task")
snapshot = client.inspect_run(result["run_id"])
files = client.export(result["run_id"])
```

RunOptions provides host model, price, and limit settings. It does not override the manifest path or mode. Inspect, accept, decide, cancel, recover, resume, health, and backup are available. Decisions do not deploy changes.

## Versioning and recovery

Manifest semantics and complete evidence snapshots enter the digest. Formatting-only JSON changes are ignored. Changes to approved semantics or evidence require a new revision and authorization. Before authorization, execution, or recovery, Porga rechecks file and project boundaries. Moving the project root or changing the state directory does not transfer authorization.

Resume uses the original approved snapshot and budget. Restore matching evidence before resuming, or authorize a new task. An unknown online request requires explicit replay permission. Database version 3 fences older code out of external project state. The v0.3-to-v0.4 migration creates pre-v0.4.sqlite3; use that snapshot in a separate location with matching old code for rollback.

## Wheel acceptance and planned activation

Use the verified wheel from [GitHub Releases](https://github.com/Petron1987/Porga-public/releases). The development command is `python -m pip wheel --no-deps --wheel-dir dist .`. Run `python scripts/check_external_consumer.py dist` for the synthetic SDK and CLI check. See [v0.4 verification](verification-v0.4.md) for its scope.

| Planned 0.5 case | Acceptance evidence |
|---|---|
| A05-01 Explicit activation | A directory with partial material enters intake only after activation. Scope, proposed files, gaps, and key questions are visible. |
| A05-02 File boundary | Unapproved paths, links, unsupported formats, and oversized sources are refused or marked partial. Source bytes stay intact. |
| A05-03 Repeat and revise | Identical input reuses a draft. Changed evidence or budget creates a reviewable revision. |
| A05-04 Activation to export | The synthetic loop records the approved digest, run, coverage, export, and separate owner acceptance. |
| A05-05 Thin integration Skill | Supported hosts use the same SDK or CLI and expose clear authorization and failure states. Owner actions stay with the trusted host. |

See [project intake](architecture/project-genesis.md) for team selection cases.
