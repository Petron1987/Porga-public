# Porga project charter · draft 0.1

## Purpose

Build a reusable system that generates and operates appropriate agent organizations,
verifies their work, accumulates evidence, and proposes measurable improvements.
The brand is Porga; the descriptor is Self-Evolving Agent Organization System.

The owner's full objective is goal-driven team creation, continuous bounded operation,
verified knowledge/capability accumulation, and organizational improvement with minimal
routine human intervention. The later single-user/public-data pilot narrows current
delivery, not that long-term intent. See [vision](vision.md) and the
[source-to-code requirements](design/requirements.json).

## Four principles

1. Goals determine teams; avoid permanent roles without demonstrated need.
2. Independent evidence determines acceptance; self-scoring is insufficient.
3. Verified knowledge and methods should become reusable assets with provenance.
4. Humans retain control of purpose, risk, resources, and material change.

## First acceptance boundary

Given a goal and approved evidence, a Chief proposes a Research -> QA plan, the factory
creates exactly those two restricted agents, artifacts and tasks persist, provenance is
checked deterministically, and an evolution proposal awaits an explicit human decision.
Failures must fail closed, remain inspectable, and never trigger automatic adoption.

## v0.3 extension

The first bounded M1 slice adds persisted owner intake/authorization, two approved deliverable
profiles, pinned organization/task graphs and separate final outcome acceptance. Natural-language
criteria still require human review. General dynamic teaming and actual self-evolution remain
future work. See [implementation boundary](m1-projects.md).

## Current pilot exclusions

v0.4 supports external private classification behind an explicit file/egress contract.
Actual private project use requires a separately reviewed project authorization. Development
and verification use synthetic fixtures.

No production credentials, payments, external publishing, autonomous
code rewriting, background scheduling, cross-host shared state, or claim of measured
self-improvement. No cloud service or public release is authorized by local setup.
These are delivery exclusions, not removal of continuous operation, shared memory,
dynamic organization or evaluated evolution from the long-term design.

## Ownership and decisions

The human owner approves scope, budgets, credentials, external writes, repository
visibility, licensing, and any future deployment. The Chief can propose work within the
kernel boundary, not modify that boundary. The kernel rejects unsupported roles/tools.

## Measures and stop conditions

Track task/gate success, source coverage, independent QA vetoes, model calls, tokens,
estimated cost, and human interventions. Stop on permission violations, budget exhaustion,
timeouts, malformed output, failed verification, or uncertain authority. Improvement
requires a held-out evaluation against a versioned baseline, including regression and cost.
