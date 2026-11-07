# v0.2 Local Pilot Verification

Historical snapshot from 2026-11-05. The pilot targeted one local user and public or synthetic data. Readiness reported offline_pilot_ready=true, online_configured=false, and production_ready=false. No paid model requests ran.

v0.2 implemented checkpoint recovery, explicit replay consent, request-key deduplication, durable per-run and per-day budgets, cooperative cancellation, integrity checks, additive SQLite migration with a backup, verified restore, and report exports.

The verification used Python 3.11.9 and OpenAI Agents SDK 0.24.0. All 45 tests and Ruff checks passed. Dependency consistency and 11 generated schemas were verified. Six deterministic gate cases passed. Tests covered process termination, OS lock release, reservation and settlement, cancellation, old-state migration, tampering, and backup and restore. Real SDK execution used synthetic outputs and an in-memory HTTP adapter.

The isolated demo made four fixture calls with 800 simulated tokens and USD 0 cost. Repeating its key made no additional calls. A restored copy retained three tasks and four artifacts with no owner decision. Live model quality, latency, billing, shared operations, and applied evolution were outside this run.
