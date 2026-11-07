"""Additive migrations; never drop existing task/evidence data."""

import hashlib
import sqlite3

DATABASE_VERSION = 3


def migrate(db, path, existed):
    version = db.execute("PRAGMA user_version").fetchone()[0]
    if version > DATABASE_VERSION:
        raise ValueError("Database was created by a newer Porga version")
    if version == DATABASE_VERSION:
        return
    if existed:
        backup = path.with_name(
            {0: "pre-v0.2.sqlite3", 1: "pre-v0.3.sqlite3", 2: "pre-v0.4.sqlite3"}[version]
        )
        if not backup.exists():
            with sqlite3.connect(backup) as destination:
                db.backup(destination)
    db.execute("BEGIN IMMEDIATE")
    version = db.execute("PRAGMA user_version").fetchone()[0]
    if version == DATABASE_VERSION:
        return
    if version == 0:
        migrate_v1(db)
    if version < 2:
        migrate_v2(db)
    # Version 3 is a compatibility fence: old code must not operate on external/private charters.
    # No data is dropped and no SQL table change is required.
    db.execute(f"PRAGMA user_version={DATABASE_VERSION}")


def migrate_v1(db):
    for definition in ("settings_json TEXT", "request_key TEXT", "project_sha256 TEXT"):
        db.execute(f"ALTER TABLE runs ADD COLUMN {definition}")
    for row in db.execute("SELECT id,project FROM runs").fetchall():
        db.execute(
            "UPDATE runs SET project_sha256=? WHERE id=?",
            (hashlib.sha256(row[1].encode()).hexdigest(), row[0]),
        )
    db.execute(
        "CREATE UNIQUE INDEX request_key_unique ON runs(request_key) WHERE request_key IS NOT NULL"
    )
    db.execute("CREATE INDEX artifacts_run_kind ON artifacts(run_id,kind)")
    db.execute("CREATE INDEX tasks_run_role ON tasks(run_id,role)")
    db.execute("""CREATE TABLE reservations (
        id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(id),
        day TEXT NOT NULL, input_cap INTEGER NOT NULL, output_cap INTEGER NOT NULL,
        tokens INTEGER NOT NULL, usd TEXT NOT NULL, status TEXT NOT NULL,
        input_tokens INTEGER, output_tokens INTEGER)""")
    db.execute("CREATE INDEX reservations_day ON reservations(day)")


def migrate_v2(db):
    statements = [
        "CREATE TABLE projects (id TEXT PRIMARY KEY, active_revision INTEGER, "
        "created_at TEXT NOT NULL)",
        """CREATE TABLE charters (
            project_id TEXT NOT NULL REFERENCES projects(id), revision INTEGER NOT NULL,
            content TEXT NOT NULL, sha256 TEXT NOT NULL, created_at TEXT NOT NULL,
            PRIMARY KEY(project_id,revision))""",
        """CREATE TABLE project_authorizations (
            project_id TEXT NOT NULL, revision INTEGER NOT NULL, digest TEXT NOT NULL,
            actor TEXT NOT NULL, note TEXT NOT NULL, created_at TEXT NOT NULL,
            PRIMARY KEY(project_id,revision),
            FOREIGN KEY(project_id,revision) REFERENCES charters(project_id,revision))""",
        """CREATE TABLE run_projects (
            run_id TEXT PRIMARY KEY REFERENCES runs(id), project_id TEXT NOT NULL,
            revision INTEGER NOT NULL, charter_digest TEXT NOT NULL,
            FOREIGN KEY(project_id,revision) REFERENCES charters(project_id,revision))""",
        """CREATE TABLE run_organizations (
            run_id TEXT PRIMARY KEY REFERENCES runs(id), content TEXT NOT NULL,
            sha256 TEXT NOT NULL)""",
        """CREATE TABLE project_acceptances (
            project_id TEXT NOT NULL, revision INTEGER NOT NULL, run_id TEXT UNIQUE NOT NULL,
            actor TEXT NOT NULL, note TEXT NOT NULL, evidence_digest TEXT NOT NULL,
            created_at TEXT NOT NULL, PRIMARY KEY(project_id,revision),
            FOREIGN KEY(project_id,revision) REFERENCES charters(project_id,revision),
            FOREIGN KEY(run_id) REFERENCES runs(id))""",
    ]
    for statement in statements:
        db.execute(statement)
