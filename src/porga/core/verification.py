"""Independent provenance gates. No claims of semantic truth or external freshness."""

from porga.protocols import EvaluationGate, ProjectSpec, QAReview, ResearchReport


def verify(
    project: ProjectSpec, report: ResearchReport, qa: QAReview, *, require_all_sources=False
) -> EvaluationGate:
    evidence = {e.id: e.text for e in project.evidence}
    checks = {
        "unique_evidence_ids": len(evidence) == len(project.evidence),
        "known_sources": all(f.evidence_id in evidence for f in report.findings),
        "exact_quotes": all(f.quote in evidence.get(f.evidence_id, "") for f in report.findings),
        "qa_passed": qa.passed and not qa.issues,
    }
    if require_all_sources:
        checks["all_sources_covered"] = {f.evidence_id for f in report.findings} == set(evidence)
    issues = [name for name, passed in checks.items() if not passed]
    return EvaluationGate(passed=all(checks.values()), checks=checks, issues=issues)
