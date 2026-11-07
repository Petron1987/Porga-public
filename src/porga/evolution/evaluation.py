"""Fixed regression cases for the kernel gate, not an LLM quality benchmark."""

from porga.core.verification import verify
from porga.protocols import ProjectSpec, QAReview, ResearchReport


def evaluate():
    project = ProjectSpec(
        goal="Check exact evidence",
        evidence=[
            {"id": "source", "title": "Synthetic source", "text": "Human approval is required."}
        ],
    )
    report = ResearchReport(
        summary="Synthetic summary",
        findings=[{"evidence_id": "source", "quote": "Human approval is required."}],
        uncertainties=[],
    )
    qa = QAReview(passed=True, issues=[])
    cases = [
        ("valid_provenance", project, report, qa, True),
        (
            "fabricated_source",
            project,
            report.model_copy(
                update={
                    "findings": [report.findings[0].model_copy(update={"evidence_id": "unknown"})]
                }
            ),
            qa,
            False,
        ),
        (
            "fabricated_quote",
            project,
            report.model_copy(
                update={
                    "findings": [
                        report.findings[0].model_copy(update={"quote": "No approval is required."})
                    ]
                }
            ),
            qa,
            False,
        ),
        (
            "duplicate_sources",
            project.model_copy(update={"evidence": project.evidence * 2}),
            report,
            qa,
            False,
        ),
        ("qa_veto", project, report, QAReview(passed=False, issues=["unsupported"]), False),
        ("inconsistent_qa", project, report, QAReview(passed=True, issues=["unresolved"]), False),
    ]
    results = [
        {"case": name, "passed": verify(p, r, q).passed == expected}
        for name, p, r, q, expected in cases
    ]
    return {
        "suite": "kernel-provenance-v1",
        "passed": all(r["passed"] for r in results),
        "cases": results,
        "scope": "kernel regression only; real model quality unverified",
    }
