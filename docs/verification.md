# Local verification record

Historical v0.1 delivery record. For the current local release see
[v0.4 verification](verification-v0.4.md). Statements below describe the original snapshot.

Date: 2026-11-05 (Asia/Shanghai). This record describes commands actually run locally.

## Test environment

- Windows, Python **3.11.9** selected for the project virtual environment.
- Python 3.14.0 also installed; it was not used for project acceptance.
- Git **2.56.0.windows.2**.
- OpenAI Agents SDK **0.24.0**, OpenAI Python **3.46.0**, Pydantic **2.14.2**.
- `OPENAI_API_KEY`, `GH_TOKEN`, and `GITHUB_TOKEN` were absent in the initial environment.
- A dedicated Git repository was initialized on **main**. No remote was configured.

## Acceptance results

| Check | Observed result |
|---|---|
| Editable local installation | Succeeded |
| `python -m pytest -q` | **25 passed** |
| `python -m ruff check src tests scripts` | All checks passed |
| `python -m ruff format src tests scripts` | All 22 Python files formatted |
| `python -m pip check` | No broken requirements found |
| `python scripts/generate_schemas.py` | 10 protocol schemas generated |
| `python -m porga doctor` | Python 3.11.9, SDK 0.24.0, mock, no API key |
| `python -m porga demo --mode mock` | awaiting_approval, validation passed |
| `python -m porga run --mode mock --project examples/project.json` | awaiting_approval, validation passed |
| Ignore checks | .env, .venv, local SQLite state ignored |

The example run used **4 SDK model calls, 800 fixture tokens,
USD 0**, persisted three completed tasks and four artifacts, and remains pending a
human decision. The fixture token count is synthetic, not a provider billing measurement.

## What tests establish

The actual SDK Agent/Runner completes Chief -> Factory -> Research tool loop -> QA ->
independent gate -> proposal. Reopening the store preserves tasks/artifacts/proposals.
Tests exercise human approve/reject and duplicate decision rejection in temporary stores;
the delivered demonstration proposals were not automatically approved.

Negative paths cover forbidden capabilities, team limits, unsupported Chief plans,
fabricated sources/quotes even when QA lies, QA veto, malformed structured output,
call/token/cost budget exhaustion, timeout reservations, and tampered evaluation content.

Online adapter tests use an **in-memory HTTP transport**, exercising the real OpenAI
Responses adapter, structured outputs, tool result continuation, store=false, estimated
usage, and a 500 response without retries. All test outbound socket connections are
blocked; Windows asyncio's internal synchronous socketpair is permitted.

## Explicit limits

No live paid API request was made. Actual model/account availability, network operation,
real-world report quality, and provider billing are unverified. CI is configured for
Python 3.11/3.12 on Linux but has not run remotely. The current validation was performed
on Windows with Python 3.11. Dependency constraints capture this environment and mark
the Windows-only pywin32 package appropriately.

No GitHub repository was created, no push was attempted, and no remote visibility is
claimed. Publication requires the owner's explicit authorization. The final local commit,
cleanliness, staged sensitive-file scan, and remote status are checked at handoff and
reported in the delivery response.
