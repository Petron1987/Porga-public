"""Single-host SQLite unit of work; content and lifecycle changes are atomic."""

import hashlib
import json
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from porga.core.lifecycle import ensure_running
from porga.core.locking import exclusive
from porga.core.migrations import DATABASE_VERSION, migrate


def uid() -> str:
    return uuid4().hex


def timestamp() -> str:
    return datetime.now(UTC).isoformat()


def canonical(value: dict) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


class Store:
    def __init__(self, root: Path):
        root.mkdir(parents=True, exist_ok=True)
        existed = (root / "porga.sqlite3").exists()
        self.path = root / "porga.sqlite3"
        with self.connect() as db:
            if db.execute("PRAGMA user_version").fetchone()[0] > DATABASE_VERSION:
                raise ValueError("Database was created by a newer Porga version")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS runs (
                    id TEXT PRIMARY KEY, mode TEXT NOT NULL, status TEXT NOT NULL,
                    project TEXT NOT NULL, created_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(id),
                    role TEXT NOT NULL, status TEXT NOT NULL, artifact_id TEXT);
                CREATE TABLE IF NOT EXISTS artifacts (
                    id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(id),
                    kind TEXT NOT NULL, sha256 TEXT NOT NULL, content TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS proposals (
                    id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(id),
                    status TEXT NOT NULL, change TEXT NOT NULL, rationale TEXT NOT NULL,
                    evaluation_id TEXT NOT NULL REFERENCES artifacts(id),
                    evidence_passed INTEGER NOT NULL,
                    deployment TEXT NOT NULL DEFAULT 'not_applied');
                CREATE TABLE IF NOT EXISTS decisions (
                    proposal_id TEXT PRIMARY KEY REFERENCES proposals(id),
                    actor TEXT NOT NULL, decision TEXT NOT NULL, note TEXT NOT NULL,
                    created_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS events (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT NOT NULL,
                    type TEXT NOT NULL, metadata TEXT NOT NULL, created_at TEXT NOT NULL);
            """)
            migrate(db, self.path, existed)

    def exclusive(self):
        return exclusive(self.path.with_suffix(".lock"))

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        try:
            with db:
                yield db
        finally:
            db.close()

    @staticmethod
    def event(db, run_id, kind, metadata=None):
        # Allowlisted metadata only; never arbitrary prompts, exception text, or keys.
        db.execute(
            "INSERT INTO events(run_id,type,metadata,created_at) VALUES(?,?,?,?)",
            (run_id, kind, canonical(metadata or {}), timestamp()),
        )

    def start(self, project, mode, settings=None, request_key=None, charter_context=None):
        run_id = uid()
        body = canonical(project)
        config = canonical(settings) if settings is not None else None
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if request_key:
                old = db.execute(
                    "SELECT * FROM runs WHERE request_key=?", (request_key,)
                ).fetchone()
                if old:
                    if (old["project"], old["mode"], old["settings_json"]) != (body, mode, config):
                        raise ValueError("Idempotency key already used for different input/config")
                    binding = db.execute(
                        "SELECT project_id,revision,charter_digest FROM "
                        "run_projects WHERE run_id=?",
                        (old["id"],),
                    ).fetchone()
                    if (tuple(binding) if binding else None) != charter_context:
                        raise ValueError("Idempotency key belongs to another charter")
                    return old["id"]
            db.execute(
                "INSERT INTO runs(id,mode,status,project,created_at,settings_json,"
                "request_key,project_sha256) VALUES(?,?,?,?,?,?,?,?)",
                (
                    run_id,
                    mode,
                    "running",
                    body,
                    timestamp(),
                    config,
                    request_key,
                    hashlib.sha256(body.encode()).hexdigest(),
                ),
            )
            if charter_context:
                from porga.core.config import Settings
                from porga.core.projects import authorized
                from porga.protocols import ProjectSpec

                project_id, revision, expected = charter_context
                row, draft = authorized(db, project_id)
                if draft.external:
                    from porga.core.integration import verify_live

                    verify_live(draft, self.path.parent)
                if row["revision"] != revision or row["sha256"] != expected or draft.mode != mode:
                    raise ValueError("Charter changed before run start")
                if not config:
                    raise ValueError("Charter execution requires recorded settings")
                limits = Settings.model_validate_json(config)
                if (
                    body
                    != canonical(
                        ProjectSpec.model_validate(draft.project.model_dump()).model_dump(
                            mode="json"
                        )
                    )
                    or limits.mode != draft.mode
                    or limits.max_calls > draft.max_calls
                    or limits.max_usd > draft.max_usd
                ):
                    raise ValueError("Input or settings exceed authorized charter")
                db.execute(
                    "INSERT INTO run_projects VALUES(?,?,?,?)",
                    (run_id, project_id, revision, expected),
                )
            self.event(db, run_id, "run_started", {"mode": mode})
        return run_id

    def task(self, run_id, role):
        task_id = uid()
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            ensure_running(db, run_id)
            db.execute(
                "INSERT INTO tasks VALUES(?,?,?,?,?)", (task_id, run_id, role, "running", None)
            )
            self.event(db, run_id, "agent_started", {"role": role, "task_id": task_id})
        return task_id

    def _artifact(self, db, run_id, kind, content):
        body = canonical(content)
        artifact_id = uid()
        db.execute(
            "INSERT INTO artifacts VALUES(?,?,?,?,?)",
            (artifact_id, run_id, kind, hashlib.sha256(body.encode()).hexdigest(), body),
        )
        return artifact_id

    def complete_task(self, run_id, task_id, kind, content):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            ensure_running(db, run_id)
            task = db.execute(
                "SELECT * FROM tasks WHERE id=? AND run_id=?", (task_id, run_id)
            ).fetchone()
            if not task or task["status"] != "running":
                raise ValueError("Task is missing or already completed")
            artifact_id = self._artifact(db, run_id, kind, content)
            db.execute(
                "UPDATE tasks SET status='completed',artifact_id=? WHERE id=? AND run_id=?",
                (artifact_id, task_id, run_id),
            )
            self.event(db, run_id, "artifact_saved", {"kind": kind, "artifact_id": artifact_id})
        return artifact_id

    def usage_event(self, run_id, kind, metadata):
        with self.connect() as db:
            self.event(db, run_id, kind, metadata)

    def finish(self, run_id, evaluation, change, rationale):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            ensure_running(db, run_id)
            evaluation_id = self._artifact(db, run_id, "evaluation", evaluation)
            proposal_id = uid()
            db.execute(
                "INSERT INTO proposals VALUES(?,?,?,?,?,?,?,?)",
                (
                    proposal_id,
                    run_id,
                    "pending",
                    change,
                    rationale,
                    evaluation_id,
                    int(evaluation["passed"]),
                    "not_applied",
                ),
            )
            db.execute(
                "UPDATE runs SET status=? WHERE id=?",
                ("awaiting_approval" if evaluation["passed"] else "validation_failed", run_id),
            )
            self.event(
                db,
                run_id,
                "proposal_created",
                {"proposal_id": proposal_id, "evaluation_passed": evaluation["passed"]},
            )
        return proposal_id

    def fail(self, run_id, error_type):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            state = db.execute("SELECT status FROM runs WHERE id=?", (run_id,)).fetchone()
            if not state or state[0] not in ("running", "cancel_requested"):
                return
            status = "cancelled" if state[0] == "cancel_requested" else "failed"
            db.execute("UPDATE runs SET status=? WHERE id=?", (status, run_id))
            db.execute(
                "UPDATE tasks SET status='failed' WHERE run_id=? AND status='running'", (run_id,)
            )
            self.event(db, run_id, "run_failed", {"error_type": error_type})
        return status

    def decide(self, proposal_id, approve, actor, note):
        if not actor.strip() or not note.strip() or len(actor) > 120 or len(note) > 2000:
            raise ValueError("A human actor and decision note are required")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM proposals WHERE id=?", (proposal_id,)).fetchone()
            if row is None:
                raise ValueError("Proposal not found")
            if row["status"] != "pending":
                raise ValueError("Proposal already decided")
            if approve:
                from porga.core.operations import check_run

                check_run(db, row["run_id"])
                gate = db.execute(
                    "SELECT * FROM artifacts WHERE id=?", (row["evaluation_id"],)
                ).fetchone()
                valid_hash = hashlib.sha256(gate["content"].encode()).hexdigest() == gate["sha256"]
                if not valid_hash or not json.loads(gate["content"])["passed"]:
                    raise ValueError("Failed or tampered evaluation cannot be approved")
            status = "approved" if approve else "rejected"
            db.execute("UPDATE proposals SET status=? WHERE id=?", (status, proposal_id))
            db.execute(
                "INSERT INTO decisions VALUES(?,?,?,?,?)",
                (proposal_id, actor, status, note, timestamp()),
            )
            db.execute("UPDATE runs SET status=? WHERE id=?", (status, row["run_id"]))
            self.event(
                db,
                row["run_id"],
                "human_decision",
                {"proposal_id": proposal_id, "decision": status},
            )
        return status

    def snapshot(self, run_id):
        with self.connect() as db:
            db.execute("BEGIN")
            run = db.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
            if not run:
                raise ValueError("Run not found")
            result = {"run": dict(run)}
            result["run"]["project"] = json.loads(result["run"]["project"])
            for table in ("tasks", "artifacts", "proposals", "events"):
                result[table] = [
                    dict(r)
                    for r in db.execute(
                        f"SELECT * FROM {table} WHERE run_id=? ORDER BY rowid", (run_id,)
                    )
                ]
            for item in result["artifacts"]:
                item["content"] = json.loads(item["content"])
            for item in result["events"]:
                item["metadata"] = json.loads(item["metadata"])
            result["decisions"] = [
                dict(r)
                for r in db.execute(
                    "SELECT d.* FROM decisions d JOIN proposals p ON p.id=d.proposal_id "
                    "WHERE p.run_id=?",
                    (run_id,),
                )
            ]
            result["reservations"] = [
                dict(r) for r in db.execute("SELECT * FROM reservations WHERE run_id=?", (run_id,))
            ]
            binding = db.execute("SELECT * FROM run_projects WHERE run_id=?", (run_id,)).fetchone()
            org = db.execute("SELECT * FROM run_organizations WHERE run_id=?", (run_id,)).fetchone()
            result["project_binding"] = dict(binding) if binding else None
            result["organization"] = json.loads(org["content"]) if org else None
            accepted = db.execute(
                "SELECT * FROM project_acceptances WHERE run_id=?", (run_id,)
            ).fetchone()
            result["owner_acceptance"] = dict(accepted) if accepted else None
            result["charter"] = None
            result["charter_authorization"] = None
            if binding:
                row = db.execute(
                    "SELECT content FROM charters WHERE project_id=? AND revision=?",
                    (binding["project_id"], binding["revision"]),
                ).fetchone()
                result["charter"] = json.loads(row[0])
                auth = db.execute(
                    "SELECT * FROM project_authorizations WHERE project_id=? AND revision=?",
                    (binding["project_id"], binding["revision"]),
                ).fetchone()
                result["charter_authorization"] = dict(auth) if auth else None
        return result
