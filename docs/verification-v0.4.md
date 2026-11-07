# v0.4 external contract verification · 2026-11-06

Scope: the first external consumer contract v1 and public Python SDK/CLI, still Early Alpha.
Windows / Python 3.11.9 / openai-agents 0.24.0. External inputs were synthetic fixtures.

| Check actually performed | Observed result |
|---|---|
| pytest, preserving prior 75-test baseline | 105 passed, 3 skipped |
| Ruff src/tests/scripts | Passed |
| Editable package install / dependency consistency | v0.4.0 / no broken requirements |
| Runtime-derived schemas | 19 generated |
| Wheel build | porga-0.4.0-py3-none-any.whl |
| Independent installed-wheel SDK and CLI | Passed from an unrelated working directory, import verified from installed wheel contents |
| SDK mock vertical loop | 4 actual SDK model calls, fixture usage, USD 0; independent QA, output export, owner acceptance and pending evolution proposal |
| External source and state | Source unchanged; state/output in consumer root; no implicit working-directory .porga |
| Boundaries | Traversal, absolute paths, drives/UNC/streams, sensitive paths, hard links, Windows junctions, unrelated state/run IDs rejected |
| Revisions/consent | Changed source/manifest requires renewed approval; core authorization also requires explicit OpenAI egress consent |
| Recovery | Changed external contract rejected before another call; corrupted saved mode cannot turn a private offline task online |
| Legacy data | Old 0.3 charters without external field readable; version-3 compatibility fence and pre-v0.4 backup verified |

The three skipped cases require symlink-creation privileges unavailable on this host.
The separate real Windows directory-junction test passed. CI is configured to run symlink
cases on Linux; no new remote CI result is claimed. Earlier GitHub startup_failure has not
been diagnosed or shown fixed by this work. This iteration has not been pushed.

Wheel SHA-256: `3d6739a5957ea5de7340962e06b403414fe41274e8598151de7a9cac4b05b8fa`.
The consumer checker installs the local wheel with --no-index --no-deps, then uses this
environment's installed dependencies. It checks that Porga itself comes from the wheel,
not the editable source checkout. This is not a clean-machine acceptance test.

All authorization/acceptance records generated during tests belong to temporary synthetic
fixtures. The delivered external demo remains unapproved. No real-data authorization,
live model request, API purchase, GitHub publication, collaborator change or license choice
was performed. State/export files contain evidence snapshots and must remain private.

Not implemented: general document parsers, arbitrary plugins, project relocation/migration
wizard, shared cross-project budget coordinator, OS-enforced process isolation, 24-hour
worker/scheduler, multi-user service, measured model-quality acceptance, knowledge/Skill
promotion or actual evolution adoption/rollback. Production readiness remains false.
