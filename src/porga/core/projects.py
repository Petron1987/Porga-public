"""Owner intake, sealed charter revisions and final acceptance; never a model tool."""

import hashlib
import json
from decimal import Decimal

from porga.core.config import Settings
from porga.core.operations import check_run
from porga.core.store import canonical, timestamp, uid
from porga.project_protocols import CharterDraft
from porga.protocols import ProjectSpec


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def actor_note(actor, note):
    if not actor.strip() or len(actor) > 120 or not note.strip() or len(note) > 2000:
        raise ValueError("Bounded human actor and decision note required")


def questions(draft):
    result = []
    if draft.deliverable is None:
        result.append(
            {
                "field": "deliverable",
                "question": "Do you need a research report or an audit of evidence coverage?",
                "choices": ["research_report", "evidence_audit"],
            }
        )
    if not draft.success_criteria:
        result.append(
            {
                "field": "success_criteria",
                "question": "What result would you accept? Specify the acceptance criteria.",
            }
        )
    if not draft.non_goals:
        result.append({"field": "non_goals", "question": "What is out of scope?"})
    if draft.mode is None or draft.max_usd is None:
        missing = (["mode"] if draft.mode is None else []) + (
            ["max_usd"] if draft.max_usd is None else []
        )
        result.append(
            {
                "field": "resources",
                "missing_fields": missing,
                "question": "Provide "
                + ", ".join(missing)
                + ". Use mock or openai for mode. Set max_usd as the per-run USD limit.",
            }
        )
    if draft.data_scope is None or not draft.project.evidence:
        missing = (["data_scope"] if draft.data_scope is None else []) + (
            ["evidence"] if not draft.project.evidence else []
        )
        result.append(
            {
                "field": "data",
                "missing_fields": missing,
                "question": "Provide "
                + ", ".join(missing)
                + ". Use only authorized public or synthetic evidence.",
            }
        )
    return result


def create(store, draft):
    draft = CharterDraft.model_validate(draft)
    project_id = uid()
    with store.connect() as db:
        db.execute("INSERT INTO projects VALUES(?,?,?)", (project_id, None, timestamp()))
        body = draft.model_dump(mode="json")
        db.execute(
            "INSERT INTO charters VALUES(?,?,?,?,?)",
            (project_id, 1, canonical(body), digest(body), timestamp()),
        )
        store.event(db, project_id, "charter_drafted", {"revision": 1})
    return inspect(store, project_id)


def charter(db, project_id, revision=None):
    row = db.execute(
        "SELECT * FROM charters WHERE project_id=? "
        + ("ORDER BY revision DESC LIMIT 1" if revision is None else "AND revision=?"),
        (project_id,) if revision is None else (project_id, revision),
    ).fetchone()
    if not row or hashlib.sha256(row["content"].encode()).hexdigest() != row["sha256"]:
        raise ValueError("Charter missing or tampered")
    return row, CharterDraft.model_validate_json(row["content"])


def inspect(store, project_id):
    with store.connect() as db:
        db.execute("BEGIN")
        check_project(db, project_id)
        row, draft = charter(db, project_id)
        project = db.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
        authorized = db.execute(
            "SELECT * FROM project_authorizations WHERE project_id=? AND revision=?",
            (project_id, row["revision"]),
        ).fetchone()
        accepted = db.execute(
            "SELECT * FROM project_acceptances WHERE project_id=? ORDER BY revision", (project_id,)
        ).fetchall()
    missing = questions(draft)
    return {
        "project_id": project_id,
        "revision": row["revision"],
        "digest": row["sha256"],
        "active_revision": project["active_revision"],
        "charter": draft.model_dump(mode="json"),
        "questions": missing,
        "ready_for_authorization": not missing,
        "authorized": bool(authorized and authorized["digest"] == row["sha256"]),
        "acceptances": [dict(r) for r in accepted],
        "status": "owner_accepted"
        if any(r["revision"] == row["revision"] for r in accepted)
        else "authorized"
        if authorized
        else "needs_answers"
        if missing
        else "awaiting_owner_authorization",
    }


def revise(store, project_id, draft):
    draft = CharterDraft.model_validate(draft)
    with store.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        row, _ = charter(db, project_id)
        revision = row["revision"] + 1
        body = draft.model_dump(mode="json")
        db.execute(
            "INSERT INTO charters VALUES(?,?,?,?,?)",
            (project_id, revision, canonical(body), digest(body), timestamp()),
        )
        store.event(db, project_id, "charter_revised", {"revision": revision})
    return inspect(store, project_id)


def authorize(store, project_id, expected_digest, actor, note, *, allow_openai=False):
    actor_note(actor, note)
    with store.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        row, draft = charter(db, project_id)
        if draft.external:
            from porga.core.integration import verify_live

            verify_live(draft, store.path.parent)
            if draft.mode == "openai" and not allow_openai:
                raise ValueError("External data egress requires explicit allow-openai confirmation")
        if row["sha256"] != expected_digest:
            raise ValueError("Stale charter digest; review current revision")
        if questions(draft):
            raise ValueError("Critical intake answers are missing")
        if draft.mode == "openai" and draft.max_usd <= 0:
            raise ValueError("Online execution requires a positive authorized budget")
        old = db.execute(
            "SELECT 1 FROM project_authorizations WHERE project_id=? AND revision=?",
            (project_id, row["revision"]),
        ).fetchone()
        if old:
            raise ValueError("Revision already authorized")
        db.execute(
            "INSERT INTO project_authorizations VALUES(?,?,?,?,?,?)",
            (project_id, row["revision"], expected_digest, actor, note, timestamp()),
        )
        db.execute(
            "UPDATE projects SET active_revision=? WHERE id=?", (row["revision"], project_id)
        )
        store.event(
            db,
            project_id,
            "charter_authorized",
            {
                "revision": row["revision"],
                "openai_egress": bool(draft.external and draft.mode == "openai" and allow_openai),
            },
        )
    return inspect(store, project_id)


def authorized(db, project_id, revision=None):
    project = db.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
    if not project or project["active_revision"] is None:
        raise ValueError("Project has no authorized charter")
    if revision is None:
        latest = db.execute(
            "SELECT max(revision) FROM charters WHERE project_id=?", (project_id,)
        ).fetchone()[0]
        if latest != project["active_revision"]:
            raise ValueError("Newer charter draft awaits authorization")
    revision = revision or project["active_revision"]
    row, draft = charter(db, project_id, revision)
    auth = db.execute(
        "SELECT * FROM project_authorizations WHERE project_id=? AND revision=?",
        (project_id, revision),
    ).fetchone()
    if not auth or auth["digest"] != row["sha256"] or questions(draft):
        raise ValueError("Charter authorization missing or invalid")
    return row, draft


def run_context(store, run_id):
    with store.connect() as db:
        context = db.execute("SELECT * FROM run_projects WHERE run_id=?", (run_id,)).fetchone()
        if not context:
            return None
        row, draft = authorized(db, context["project_id"], context["revision"])
        if row["sha256"] != context["charter_digest"]:
            raise ValueError("Run is not bound to the approved charter")
        return dict(context), draft


async def execute_project(
    store, project_id, settings: Settings, *, request_key=None, runtime_class=None
):
    from porga.workflow import execute

    with store.connect() as db:
        row, draft = authorized(db, project_id)
    if settings.mode != draft.mode:
        raise ValueError("Execution mode differs from the approved charter")
    bounded = settings.model_copy(
        update={
            "max_calls": min(settings.max_calls, draft.max_calls),
            "max_usd": min(settings.max_usd, draft.max_usd),
        }
    )
    if draft.mode == "mock":
        # Offline fixture usage is not provider usage, regardless of local live price settings.
        bounded = bounded.model_copy(update={"input_price": Decimal(0), "output_price": Decimal(0)})
    kwargs = {} if runtime_class is None else {"runtime_class": runtime_class}
    return await execute(
        ProjectSpec.model_validate(draft.project.model_dump()),
        bounded,
        store,
        request_key=request_key,
        charter_context=(project_id, row["revision"], row["sha256"]),
        **kwargs,
    )


def accept(store, project_id, run_id, actor, note):
    actor_note(actor, note)
    with store.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        check_run(db, run_id)
        binding = db.execute(
            "SELECT * FROM run_projects WHERE run_id=? AND project_id=?", (run_id, project_id)
        ).fetchone()
        if not binding:
            raise ValueError("Run belongs to another project or legacy execution")
        row, _ = authorized(db, project_id, binding["revision"])
        active = db.execute(
            "SELECT active_revision FROM projects WHERE id=?", (project_id,)
        ).fetchone()
        if active[0] != binding["revision"] or row["sha256"] != binding["charter_digest"]:
            raise ValueError("Final acceptance must match the current authorized revision")
        authorized(db, project_id)  # A pending newer draft also blocks final acceptance.
        status = db.execute("SELECT status FROM runs WHERE id=?", (run_id,)).fetchone()[0]
        if status not in ("awaiting_approval", "approved", "rejected"):
            raise ValueError("Final acceptance requires a completed successful run")
        gate = db.execute(
            "SELECT * FROM artifacts WHERE run_id=? AND kind='evaluation'", (run_id,)
        ).fetchone()
        if not gate or json.loads(gate["content"]).get("passed") is not True:
            raise ValueError("Run did not pass independent gates")
        if db.execute(
            "SELECT 1 FROM project_acceptances WHERE project_id=? AND revision=?",
            (project_id, binding["revision"]),
        ).fetchone():
            raise ValueError("Revision already accepted")
        evidence_digest = outcome_digest(db, run_id)
        db.execute(
            "INSERT INTO project_acceptances VALUES(?,?,?,?,?,?,?)",
            (project_id, binding["revision"], run_id, actor, note, evidence_digest, timestamp()),
        )
        store.event(
            db,
            project_id,
            "owner_accepted_outcome",
            {"run_id": run_id, "revision": binding["revision"]},
        )
    return {
        "project_id": project_id,
        "run_id": run_id,
        "status": "owner_accepted",
        "evidence_digest": evidence_digest,
        "evolution_deployment": "not_applied",
    }


def outcome_digest(db, run_id):
    binding = db.execute("SELECT * FROM run_projects WHERE run_id=?", (run_id,)).fetchone()
    org = db.execute("SELECT sha256 FROM run_organizations WHERE run_id=?", (run_id,)).fetchone()
    if not binding or not org:
        raise ValueError("Outcome lacks pinned charter/organization")
    return digest(
        {
            "binding": dict(binding),
            "organization": org[0],
            "artifacts": {
                r["id"]: r["sha256"]
                for r in db.execute("SELECT id,sha256 FROM artifacts WHERE run_id=?", (run_id,))
            },
        }
    )


def check_project(db, project_id):
    project = db.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
    if not project:
        raise ValueError("Project missing")
    if not db.execute("SELECT 1 FROM charters WHERE project_id=?", (project_id,)).fetchone():
        raise ValueError("Project lacks charter")
    for row in db.execute("SELECT revision FROM charters WHERE project_id=?", (project_id,)):
        charter(db, project_id, row[0])
    for auth in db.execute(
        "SELECT * FROM project_authorizations WHERE project_id=?", (project_id,)
    ):
        row, draft = charter(db, project_id, auth["revision"])
        if row["sha256"] != auth["digest"] or questions(draft):
            raise ValueError("Authorization differs from charter")
    if project["active_revision"] is not None:
        authorized(db, project_id, project["active_revision"])
    for accepted in db.execute(
        "SELECT * FROM project_acceptances WHERE project_id=?", (project_id,)
    ):
        check_run(db, accepted["run_id"])
        binding = db.execute(
            "SELECT * FROM run_projects WHERE run_id=?", (accepted["run_id"],)
        ).fetchone()
        if (
            not binding
            or (binding["project_id"], binding["revision"]) != (project_id, accepted["revision"])
            or accepted["evidence_digest"] != outcome_digest(db, accepted["run_id"])
        ):
            raise ValueError("Accepted outcome evidence differs")
