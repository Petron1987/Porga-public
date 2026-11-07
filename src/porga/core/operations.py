"""Local operator functions. None is available as a model tool."""

import hashlib
import json
import sqlite3
from pathlib import Path

from porga.core.migrations import DATABASE_VERSION
from porga.core.store import canonical, uid


def check_run(db, run_id):
    run = db.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
    if not run:
        raise ValueError("Run not found")
    if (
        run["project_sha256"]
        and hashlib.sha256(run["project"].encode()).hexdigest() != run["project_sha256"]
    ):
        raise ValueError("Project content is tampered")
    for artifact in db.execute("SELECT * FROM artifacts WHERE run_id=?", (run_id,)):
        if hashlib.sha256(artifact["content"].encode()).hexdigest() != artifact["sha256"]:
            raise ValueError("Artifact content is tampered")
    for task in db.execute("SELECT * FROM tasks WHERE run_id=? AND status='completed'", (run_id,)):
        artifact = db.execute(
            "SELECT * FROM artifacts WHERE id=?", (task["artifact_id"],)
        ).fetchone()
        kind = "plan" if task["role"] == "chief" else task["role"]
        if not artifact or artifact["run_id"] != run_id or artifact["kind"] != kind:
            raise ValueError("Task checkpoint linkage is invalid")
    binding = db.execute("SELECT * FROM run_projects WHERE run_id=?", (run_id,)).fetchone()
    org = db.execute("SELECT * FROM run_organizations WHERE run_id=?", (run_id,)).fetchone()
    if binding:
        from porga.core.config import Settings
        from porga.core.projects import authorized, digest
        from porga.organization.registry import organization, worker_for
        from porga.protocols import PermissionPolicy, ProjectSpec

        row, draft = authorized(db, binding["project_id"], binding["revision"])
        config = Settings.model_validate_json(run["settings_json"])
        if (
            row["sha256"] != binding["charter_digest"]
            or run["mode"] != draft.mode
            or config.mode != draft.mode
            or canonical(
                ProjectSpec.model_validate(draft.project.model_dump()).model_dump(mode="json")
            )
            != run["project"]
            or config.max_calls > draft.max_calls
            or config.max_usd > draft.max_usd
        ):
            raise ValueError("Run differs from authorized charter")
        expected = organization(
            binding["project_id"],
            binding["revision"],
            draft,
            [worker_for(draft.deliverable), "qa"],
            PermissionPolicy(),
        )
        if org:
            if digest(json.loads(org["content"])) != org["sha256"]:
                raise ValueError("Organization content is tampered")
            if canonical(expected.model_dump(mode="json")) != org["content"]:
                raise ValueError("Organization differs from approved registry")
        elif db.execute(
            "SELECT 1 FROM tasks WHERE run_id=? AND role!='chief'", (run_id,)
        ).fetchone():
            raise ValueError("Specialist run lacks pinned organization")
    elif org:
        raise ValueError("Organization lacks charter binding")


def result(store, run_id):
    from porga.core.budget import totals

    with store.connect() as db:
        check_run(db, run_id)
        run = db.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
        p = db.execute("SELECT * FROM proposals WHERE run_id=?", (run_id,)).fetchone()
        if not p:
            raise ValueError("Run has no completed proposal; inspect or resume it")
        calls, tokens, usd = totals(db, run_id)
        binding = db.execute("SELECT * FROM run_projects WHERE run_id=?", (run_id,)).fetchone()
        return {
            "run_id": run_id,
            "status": run["status"],
            "proposal_id": p["id"],
            "validation_passed": bool(p["evidence_passed"]),
            "model_calls": calls,
            "tokens": tokens,
            "estimated_usd": str(usd),
            "mode": run["mode"],
            "project_binding": dict(binding) if binding else None,
            "owner_accepted": bool(
                db.execute("SELECT 1 FROM project_acceptances WHERE run_id=?", (run_id,)).fetchone()
            ),
        }


def recover(store, run_id):
    with store.exclusive(), store.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        check_run(db, run_id)
        run = db.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
        if run["status"] not in ("running", "cancel_requested"):
            raise ValueError("Only abandoned active runs require recovery")
        status = "cancelled" if run["status"] == "cancel_requested" else "interrupted"
        db.execute("UPDATE runs SET status=? WHERE id=?", (status, run_id))
        db.execute(
            "UPDATE tasks SET status='failed' WHERE run_id=? AND status='running'", (run_id,)
        )
        store.event(db, run_id, "run_recovered", {"status": status})
    return {"run_id": run_id, "status": status, "requests_replayed": 0}


def cancel(store, run_id):
    with store.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT status FROM runs WHERE id=?", (run_id,)).fetchone()
        if not row or row[0] not in ("running", "failed", "interrupted"):
            raise ValueError("Run cannot be cancelled in its current state")
        status = "cancel_requested" if row[0] == "running" else "cancelled"
        db.execute("UPDATE runs SET status=? WHERE id=?", (status, run_id))
        store.event(db, run_id, "operator_cancelled", {"status": status})
    return {"run_id": run_id, "status": status}


def health(store):
    with store.connect() as db:
        db.execute("BEGIN")
        problems = [r[0] for r in db.execute("PRAGMA integrity_check") if r[0] != "ok"]
        problems += ["foreign_key_violation" for _ in db.execute("PRAGMA foreign_key_check")]
        for run in db.execute("SELECT id FROM runs"):
            try:
                check_run(db, run[0])
            except ValueError:
                problems.append("artifact_or_project_integrity")
        from porga.core.projects import check_project

        for project in db.execute("SELECT id FROM projects"):
            try:
                check_project(db, project[0])
            except ValueError:
                problems.append("charter_or_acceptance_integrity")
        counts = {
            r[0]: r[1] for r in db.execute("SELECT status,count(*) FROM runs GROUP BY status")
        }
        pending = db.execute(
            "SELECT count(*) FROM reservations WHERE status='reserved'"
        ).fetchone()[0]
    return {
        "ok": not problems,
        "database_version": DATABASE_VERSION,
        "problems": problems,
        "runs_by_status": counts,
        "unsettled_reservations": pending,
    }


def readiness(store, settings):
    import os

    from porga.evolution.evaluation import evaluate

    state = health(store)
    gates = evaluate()
    active = state["runs_by_status"].get("running", 0)
    active += state["runs_by_status"].get("cancel_requested", 0)
    configured = True
    try:
        settings.model_copy(update={"mode": "openai"}).validate_online()
    except ValueError:
        configured = False
    return {
        "target": "single-user local public/synthetic evidence",
        "offline_pilot_ready": state["ok"] and gates["passed"] and active == 0,
        "data_health": state,
        "kernel_regression_passed": gates["passed"],
        "online_configured": configured,
        "api_key_present": bool(os.environ.get("OPENAI_API_KEY")),
        "production_ready": False,
        "remaining_gates": [
            "owner-run live model acceptance on representative public tasks",
            "owner-defined quality/cost targets and backup retention policy",
            "this build has no multi-user authentication or automatic evolution",
        ],
    }


def backup(store):
    folder = store.path.parent / "backups"
    folder.mkdir(exist_ok=True)
    path = folder / f"porga-{uid()}.sqlite3"
    try:
        with store.connect() as source, sqlite3.connect(path) as destination:
            source.backup(destination)
            if destination.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise ValueError("Backup integrity check failed")
    except BaseException:
        path.unlink(missing_ok=True)
        raise
    return {"backup": str(path.resolve()), "verified": True}


def restore(store, source: Path):
    if not source.is_file() or source.resolve() == store.path.resolve():
        raise ValueError("Choose an existing backup file")
    with store.exclusive():
        with sqlite3.connect(f"{source.resolve().as_uri()}?mode=ro", uri=True) as origin:
            origin.row_factory = sqlite3.Row
            if (
                origin.execute("PRAGMA integrity_check").fetchone()[0] != "ok"
                or origin.execute("PRAGMA user_version").fetchone()[0] != DATABASE_VERSION
            ):
                raise ValueError("Unsupported or corrupt backup")
            origin.execute("SELECT id FROM runs LIMIT 1")
            if origin.execute("PRAGMA foreign_key_check").fetchone():
                raise ValueError("Backup has invalid references")
            origin.execute("SELECT id FROM reservations LIMIT 1")
            for row in origin.execute("SELECT id FROM runs"):
                check_run(origin, row[0])
            from porga.core.projects import check_project

            for row in origin.execute("SELECT id FROM projects"):
                check_project(origin, row[0])
            with store.connect() as db:
                if any(
                    db.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
                    for table in (
                        "runs",
                        "tasks",
                        "artifacts",
                        "proposals",
                        "decisions",
                        "events",
                        "reservations",
                        "projects",
                        "charters",
                        "project_authorizations",
                        "run_projects",
                        "run_organizations",
                        "project_acceptances",
                    )
                ):
                    raise ValueError("Restore destination must be an empty data directory")
                origin.backup(db)
    return {"restored": True, "health": health(store)}


def export_report(store, run_id):
    summary = result(store, run_id)
    snapshot = store.snapshot(run_id)
    run_id = snapshot["run"]["id"]
    folder = store.path.parent / "reports"
    folder.mkdir(exist_ok=True)
    path = folder / f"{run_id}.md"
    lines = [
        "# Porga research report",
        "",
        f"Mode: {summary['mode']}",
        f"Status: {summary['status']}",
        "",
        "## Goal",
        "",
        snapshot["run"]["project"]["goal"],
    ]
    if snapshot["project_binding"]:
        lines += [
            "",
            "## Authorized organization",
            "",
            "```json",
            json.dumps(
                {
                    "binding": snapshot["project_binding"],
                    "organization": snapshot["organization"],
                    "owner_accepted": summary["owner_accepted"],
                    "owner_acceptance": snapshot["owner_acceptance"],
                },
                ensure_ascii=False,
                indent=2,
            ).replace("`", "\\u0060"),
            "```",
        ]
    for artifact in snapshot["artifacts"]:
        lines += [
            "",
            "## " + artifact["kind"],
            "",
            "```json",
            json.dumps(artifact["content"], ensure_ascii=False, indent=2).replace("`", "\\u0060"),
            "```",
        ]
    lines += [
        "",
        "## Proposal and decisions",
        "",
        "```json",
        json.dumps(
            {"proposals": snapshot["proposals"], "decisions": snapshot["decisions"]},
            ensure_ascii=False,
            indent=2,
        ).replace("`", "\\u0060"),
        "```",
        "",
        "Provenance checks do not establish semantic truth or external freshness.",
        "Approval records a human decision; no deployment is performed.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    json_path = folder / f"{run_id}.json"
    json_path.write_text(canonical(snapshot) + "\n", encoding="utf-8")
    return {"report": str(path.resolve()), "json": str(json_path.resolve())}
