# Porga

**Self-Evolving Agent Organization System** · Porga Community 0.4.0 Alpha

Porga records a project charter, asks for missing critical answers and requires explicit
owner authorization before project execution. The authorized deliverable selects a bounded
Research/QA or Evidence Auditor/QA team from a code-reviewed registry. Tasks, artifacts,
the pinned organization and decisions persist locally. The Python OpenAI Agents SDK runs
the agents; a deterministic kernel owns authority. Final owner acceptance is recorded
separately from evolution proposal approval.

This is an executable first slice, not yet a continuously self-improving organization.
The complete intended organization/evolution system is described in [vision](docs/vision.md).
[The original discussion audit](docs/design/conversation-audit.zh-CN.md) lists 40 extracted
items with sources, actual v0.2 behavior and remaining gaps. Documented goals are not
implemented capabilities; a proposal or approval is not deployed self-improvement.
The [A1 architecture plan](docs/architecture/target.zh-CN.md) develops those gaps into
domain contracts, durable execution, knowledge/evolution governance and an
[acceptance-driven implementation sequence](docs/architecture/delivery-plan.zh-CN.md).
The A1 design remains the long-term target. v0.3 implements the first bounded M1 slice;
it does not complete general dynamic organization or autonomous evolution.

The [owner-confirmed adoption roadmap](docs/roadmap.md)
prioritizes lightweight SDK/CLI activation, a thin integration Skill, MCP, then Worker/HTTP
when sustained background work or remote access is needed. These planned adapters share
one kernel; they do not imply new implemented features or public-release authorization.

v0.2 adds checkpoint recovery, duplicate request protection, persistent per-run/shared daily
budgets, cross-process execution locking, cooperative cancellation, verified backup/restore,
artifact integrity checks, and report export. It is suitable for controlled local offline
trials with public/synthetic evidence. Real model quality has not been accepted for production.

v0.3 adds [project intake and authorization](docs/m1-projects.zh-CN.md), immutable charter
revisions, two approved team profiles, a validated task graph, source-coverage gates for
audits, and final owner acceptance tied to exact outcome hashes. Legacy `demo`/`run` remain
available as operator-invoked kernel exercises; use `project` for charter-governed work.

v0.4 adds the [external project contract](docs/external-project-contract.zh-CN.md).
Independent projects install Porga and call `porga.api.ProjectClient` or the `external` CLI;
their data, state and outputs stay in their own directories. Exact version pins, bounded
file manifests and explicit data egress authorization are enforced before execution/resume.
Classification defaults to private and model egress to deny. A private classification
never by itself permits sending content to OpenAI. All bundled examples are synthetic.

See [v0.4 verification](docs/verification-v0.4.md) for local tests and installed-wheel
acceptance. Get the Community wheel from the
[official GitHub releases](https://github.com/Petron1987/Porga-public/releases).
Install it in a local Python environment with the bundled dependency lock file:

```powershell
python -m pip install -c requirements.lock.txt ./porga-0.4.0-py3-none-any.whl
```

Run this command from the extracted source archive with the downloaded wheel alongside
`requirements.lock.txt`. Porga Community 0.4.0 is distributed through GitHub Releases.

## Use from an independent project

Copy `examples/external-project/` to a separate directory and use an installed Porga:

```powershell
python -m porga external preview --manifest "YOUR_PROJECT/porga.project.json"
python -m porga external attach --manifest "YOUR_PROJECT/porga.project.json"
```

The manifest's directory is the consumer root; relative paths never depend on the calling
directory. Attach only creates a reviewable draft. Follow the [contract guide](docs/external-project-contract.zh-CN.md)
to authorize, run, inspect and accept. A Python host can use the public SDK without importing
SQLite or internal modules. Installation does not start a background process or grant data access.

## Quick start (Windows PowerShell)

Python 3.11+ and Git are required. From a fresh checkout, create a local environment:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -c requirements.lock.txt -e ".[dev]"
```

From the repository root, no key or network is needed after dependencies are installed:

```powershell
.\.venv\Scripts\python.exe -m porga doctor
.\.venv\Scripts\python.exe -m porga demo --mode mock
.\.venv\Scripts\python.exe -m porga run --mode mock --project examples/project.json
.\.venv\Scripts\python.exe -m porga status
.\.venv\Scripts\python.exe -m porga readiness
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check src tests
```

Mock mode runs the **actual SDK Agent/Runner**, including a real `read_evidence` function
tool call, structured output validation, lifecycle persistence, and verification. Its
deterministic answers are synthetic fixtures; no live research or model intelligence is claimed.
Tests block outbound socket connections.

## Start a governed project

```powershell
.\.venv\Scripts\python.exe -m porga project draft --goal "Compare the supplied public sources"
# Or load a complete synthetic charter and review its returned ID, digest and limits:
.\.venv\Scripts\python.exe -m porga project draft --spec examples/charter-audit.json
.\.venv\Scripts\python.exe -m porga project inspect PROJECT_ID
.\.venv\Scripts\python.exe -m porga project authorize PROJECT_ID --digest DIGEST --actor owner --note "Reviewed scope, evidence and limits" --confirm
.\.venv\Scripts\python.exe -m porga project run PROJECT_ID --mode mock --request-key first-project-run
.\.venv\Scripts\python.exe -m porga report RUN_ID
.\.venv\Scripts\python.exe -m porga project accept PROJECT_ID --run-id RUN_ID --actor owner --note "Reviewed criteria and accepted outcome" --confirm
```

No answer or authorization is inferred from silence. `project revise PROJECT_ID --spec FILE`
appends a draft; new execution waits for that revision's authorization. Resume uses the
original run's approved revision and recorded limits. The intake is currently a local CLI
returning structured questions, not a conversational assistant. Subjective criteria require
owner review; provenance checks alone do not establish goal satisfaction.

## Inspect and decide

`demo` prints `run_id` and `proposal_id`. Replace the placeholders with those values:

```powershell
.\.venv\Scripts\python.exe -m porga inspect RUN_ID
.\.venv\Scripts\python.exe -m porga approve PROPOSAL_ID --actor owner --note "Reviewed the evidence; approve next experiment" --confirm
# Or:
.\.venv\Scripts\python.exe -m porga reject PROPOSAL_ID --actor owner --note "More evidence required" --confirm
```

The default run stops at `awaiting_approval`. A failed gate stops at `validation_failed`;
failed proposals cannot be approved. Each proposal accepts one durable decision. Approval
means permission to consider the next experiment; **it never changes code, tools, policy,
or deployment**. A new validated change pipeline is required for actual adoption.

State is stored in `.porga/porga.sqlite3` and survives process restarts. Use
`python -m porga --data-dir OTHER_LOCAL_FOLDER demo` to isolate an experiment.
Runtime data is ignored by Git and is not automatically shared across computers.

## Local operations

```powershell
# Repeating the same key with identical input/config returns the original result.
.\.venv\Scripts\python.exe -m porga demo --request-key first-trial
.\.venv\Scripts\python.exe -m porga report RUN_ID
.\.venv\Scripts\python.exe -m porga health
.\.venv\Scripts\python.exe -m porga backup
# Restore into a NEW empty data directory; never overwrites a populated store.
.\.venv\Scripts\python.exe -m porga --data-dir .porga-restored restore BACKUP_PATH
.\.venv\Scripts\python.exe -m porga evaluate
```

After a hard crash, `recover RUN_ID` marks abandoned active work interrupted, without
replaying requests. `resume RUN_ID` reuses completed stages and reruns only unfinished work.
Resuming incomplete online work requires `--allow-replay`, which authorizes possible extra
cost. Unknown requests retain budget reservations. Stored run limits/prices remain fixed.
`cancel RUN_ID` requests a stop at the next boundary; an already-sent request can still bill.
One OS lock prevents concurrent workflows against the same local store and releases on exit.
See the [local operations guide](docs/operations.zh-CN.md) for exact procedures.

## Online mode (explicit opt-in)

```powershell
Copy-Item .env.example .env
# Edit .env locally: OPENAI_API_KEY, PORGA_MODEL, and current input/output prices.
.\.venv\Scripts\python.exe -m porga run --mode openai --project examples/project.json
```

Set a model available to your API account that supports tools and structured output.
There is deliberately no guessed model or price default. The API key is read from the
environment; `.env` supports simple literal assignments and never executes expressions.
Live mode sends the goal, evidence, generated report, and schemas to OpenAI's official API.
Only supply data you authorize for that purpose. Hosted tracing is disabled and requests
use `store=False`. Local artifacts intentionally retain the supplied content; audit events
contain only IDs, status, error class, and usage metadata.

Limits cover requests, prompt bytes, output tokens, durable total token reservations,
per-run/shared daily estimated USD, and per-request timeout. Daily budgets use UTC+08:00
reservation dates and apply across runs in the same data directory. Retries are disabled.
Unknown/failed calls
retain their reservation. Dollar estimates depend on the prices you configure and are
not a billing guarantee; configure a provider-side budget too when operating online.

## Layout

```text
src/porga/
  core/           # SQLite, immutable policy/config, budgets, independent gates
  organization/   # Chief of Staff and bounded Agent Factory
  evolution/      # Evidence-backed proposals (no automatic deployment)
  protocols.py    # Versioned Pydantic contracts
  project_protocols.py # Charter, registry and organization contracts
  runtime.py      # SDK Model adapters, real SDK execution, tracing controls
  workflow.py     # Deterministic lifecycle orchestration
  cli.py          # Local operator interface and explicit decision command
protocols/        # Generated JSON Schemas
docs/            # Charter, architecture, protocols, governance, roadmap
examples/        # Public-safe synthetic evidence only
tests/           # Offline acceptance and failure-path tests
scripts/         # Schema generation and local checks
```

## Scope and limits

The local pilot performs evidence-bounded research from a caller-supplied bundle. It does not browse
the web, fetch citations, execute generated code, or prove a narrative's semantic truth.
The deterministic gate checks source IDs/exact quotes and honors an independent QA veto.
The offline QA response is a fixture; live QA uses a separate SDK agent/context.

This is a single-user, single-host CLI. The OS account can edit its own database; actor
names and hashes provide auditability, not cryptographic identity or tamper-proof storage.
Model capabilities are restricted by the available tools, not by an OS process sandbox.
Handled errors are audited; abandoned `running` tasks require explicit recovery. Checkpoints
and budget reservations persist, but there is no automatic replay of ambiguous paid requests.
Additive database migrations preserve v0.1/v0.2 records, with a pre-upgrade snapshot
(`pre-v0.2.sqlite3` for v0.1, `pre-v0.3.sqlite3` for v0.2, `pre-v0.4.sqlite3` for v0.3).
v0.2 runs still support resume;
v0.1 runs lack recorded settings and remain inspectable/decidable only. Database version 3
is refused by older software; rollback uses the old snapshot in a separate data directory.

Public visibility and licensing remain owner decisions. The runtime does not create or
publish Git repositories; publication is separate from evolution approval.
See the [historical verification record](docs/verification.md).
中文上手说明：[本地运行与人工审批](docs/quickstart.zh-CN.md)。
Current baseline: [v0.4 verification](docs/verification-v0.4.md).
Porga Community 0.4.0 is available under the [MIT License](LICENSE).
Report issues with a sanitized reproduction in the
[public issue tracker](https://github.com/Petron1987/Porga-public/issues).

## References

Implemented against installed `openai-agents==0.24.0`, inspecting its interfaces locally.
Official documentation: [Agents SDK quickstart](https://developers.openai.com/api/docs/guides/agents/quickstart)
and [running agents](https://developers.openai.com/api/docs/guides/agents/running-agents).
