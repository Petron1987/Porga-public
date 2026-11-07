# A1 Knowledge and Evolution

Keep raw artifacts, scoped knowledge, and reusable capabilities distinct. The six knowledge types are Evidence, Fact, Hypothesis, Decision, Skill, and Lesson. Record origin, version, applicability, trust, validation, expiry, contradictions, and downstream references. A candidate may be quarantined, verified, or activated. An active record can expire, be superseded, or be revoked. Filter scope and validity before ranking results.

Use verified knowledge within the originating project. Cross-project promotion requires an independent evaluation, review of provenance and access, and removal of sensitive information. A declarative Skill pins its instructions, interfaces, tests, resources, and allowed tool references. Its activation grants no new tools.

The organization engine identifies capability gaps, reuses approved definitions, and proposes bounded teams. Splitting, merging, replacing, or retiring roles requires evidence, compatibility, QA independence, and a plan for tasks and knowledge. A change affects future assignments. Existing work retains its pinned version unless an explicit security or recovery decision intervenes.

## 0.8 first improvement acceptance

Freeze baseline, candidate, development and holdout data, metrics, safety gates, budget, and stop conditions. Compare the same tasks and configurations and retain failures. Quality and cost are separate from policy gates. Synthetic fixtures demonstrate control flow; claims of improvement require representative comparisons.

| Case | Pass criteria |
|---|---|
| I08-01 Frozen experiment | Evaluation and case selection are independent of the candidate. |
| I08-02 Negative cases | Reject missing evidence, unauthorized scope, leakage, or safety failures and retain costs. |
| I08-03 Changed candidate | A different digest, evaluation, or policy invalidates the old approval. |
| I08-04 Separate adoption | Approval is recorded before a separate owner action. Duplicate activation cannot advance the release twice. |
| I08-05 Rollback | Stop new assignments, restore a compatible release, and reconcile outstanding work and effects. |

## 0.9 organization and domain acceptance

| Case | Pass criteria |
|---|---|
| O09-01 Split | A clear handoff and measurable comparison show the effect without widening permissions. |
| O09-02 Merge | Reject merging independent QA into the evaluated role. |
| O09-03 Replace or retire | New work binds to effective versions and old work drains, pauses, or migrates explicitly. |
| O09-04 Revert | Restore the previous compatible organization and preserve history. |
| O09-05 Reuse | Run two synthetic domain templates on the same kernel with isolated records and scoped acceptance. |

Track business value, independent quality, costs, coordination, human interventions, validated improvements, and safety. A failed or inconclusive candidate is useful recorded evidence. See [external learning](external-learning.md) and [domain contracts](domain-contracts.md).
