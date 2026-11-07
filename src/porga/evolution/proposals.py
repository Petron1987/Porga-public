def suggest(gate):
    if gate.passed:
        return (
            "Evaluate a reusable evidence-first research template on a held-out task set",
            "Current task passed provenance and independent QA. This single run is baseline "
            "evidence only; improvement is unproven. Compare quality and cost before adoption.",
        )
    return (
        "Repair research provenance checks and rerun independent evaluation",
        "Validation failed: "
        + ", ".join(gate.issues)
        + ". This proposal cannot be approved until a new run passes.",
    )
