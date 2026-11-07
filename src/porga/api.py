"""Public Python API v1 for independent consuming projects (single trusted local owner)."""

import json
import sqlite3
from pathlib import Path

from porga.core import operations, projects
from porga.core.config import Settings
from porga.core.integration import load_manifest, prepare, scoped_path, verify_live
from porga.core.store import Store, uid
from porga.integration_protocols import ExternalProjectSpec, RunOptions

__all__ = ["ExternalProjectSpec", "ProjectClient", "RunOptions"]


class ProjectClient:
    """Owns no global project registry. Every manifest resolves relative to its own directory."""

    def __init__(self, manifest: str | Path):
        self.manifest = Path(manifest).absolute()

    def preview(self):
        """Validate files and return the complete reviewable snapshot, without creating state."""
        draft = prepare(self.manifest)
        binding = draft.external
        return {
            "project_key": binding.spec.project_key,
            "root": binding.root,
            "state_dir": str(scoped_path(Path(binding.root), binding.spec.state_dir)),
            "output_dir": str(scoped_path(Path(binding.root), binding.spec.output_dir)),
            "digest": projects.digest(draft.model_dump(mode="json")),
            "charter": draft.model_dump(mode="json"),
            "authorized": False,
        }

    def _context(self):
        root, spec, _ = load_manifest(self.manifest)
        state = scoped_path(root, spec.state_dir)
        # Refuse an unrelated store BEFORE Store() could migrate or write to it.
        database = scoped_path(root, spec.state_dir + "/porga.sqlite3")
        if database.exists():
            try:
                with sqlite3.connect(database.as_uri() + "?mode=ro", uri=True) as db:
                    rows = db.execute(
                        "SELECT content FROM charters c WHERE revision=("
                        "SELECT max(revision) FROM charters WHERE project_id=c.project_id)"
                    ).fetchall()
                    if len(rows) != 1:
                        raise ValueError("External state must belong to exactly one project")
                    old = json.loads(rows[0][0]).get("external")
                    if (
                        not old
                        or old["root"] != str(root)
                        or old["spec"]["project_key"] != spec.project_key
                    ):
                        raise ValueError("State belongs to another project")
            except sqlite3.DatabaseError as exc:
                raise ValueError(
                    "Use an empty directory or this external project's own state"
                ) from exc
        elif state.exists() and any(state.iterdir()):
            raise ValueError("First attachment requires an empty state directory")
        return root, spec, state

    @staticmethod
    def _project(store):
        with store.connect() as db:
            row = db.execute("SELECT id FROM projects").fetchone()
            if not row:
                raise ValueError("Attach the project first")
            return row[0]

    def attach(self):
        """Idempotently persist a draft; changed content appends an unapproved revision."""
        draft = prepare(self.manifest)
        _, _, state = self._context()
        store = Store(state)
        with store.exclusive():
            with store.connect() as db:
                row = db.execute("SELECT id FROM projects").fetchone()
            if not row:
                return projects.create(store, draft)
            old = projects.inspect(store, row[0])
            if old["digest"] == projects.digest(draft.model_dump(mode="json")):
                return old
            return projects.revise(store, row[0], draft)

    def _attached(self):
        _, _, state = self._context()
        if not (state / "porga.sqlite3").is_file():
            raise ValueError("Attach the project first")
        store = Store(state)
        return store, self._project(store)

    def inspect(self):
        store, pid = self._attached()
        return projects.inspect(store, pid)

    def authorize(self, digest: str, *, actor: str, note: str, allow_openai: bool = False):
        """Host/owner action; never expose this method as a model tool."""
        store, pid = self._attached()
        return projects.authorize(store, pid, digest, actor, note, allow_openai=allow_openai)

    async def run(self, *, options: RunOptions | None = None, request_key: str | None = None):
        store, pid = self._attached()
        with store.connect() as db:
            _, draft = projects.authorized(db, pid)
        verify_live(draft, store.path.parent)
        settings = Settings(
            **(options or RunOptions()).model_dump(), mode=draft.mode, data_dir=store.path.parent
        )
        return await projects.execute_project(store, pid, settings, request_key=request_key)

    def _run(self, store, pid, run_id):
        with store.connect() as db:
            if not db.execute(
                "SELECT 1 FROM run_projects WHERE run_id=? AND project_id=?", (run_id, pid)
            ).fetchone():
                raise ValueError("Run belongs to another project")

    def inspect_run(self, run_id: str):
        store, pid = self._attached()
        self._run(store, pid, run_id)
        return store.snapshot(run_id)

    async def resume(self, run_id: str, *, allow_replay: bool = False):
        from porga.workflow import resume

        store, pid = self._attached()
        self._run(store, pid, run_id)
        return await resume(run_id, store, allow_replay=allow_replay)

    def accept(self, run_id: str, *, actor: str, note: str):
        store, pid = self._attached()
        self._run(store, pid, run_id)
        return projects.accept(store, pid, run_id, actor, note)

    def cancel(self, run_id: str):
        store, pid = self._attached()
        self._run(store, pid, run_id)
        return operations.cancel(store, run_id)

    def recover(self, run_id: str):
        store, pid = self._attached()
        self._run(store, pid, run_id)
        return operations.recover(store, run_id)

    def health(self):
        store, _ = self._attached()
        return operations.health(store)

    def backup(self):
        store, _ = self._attached()
        return operations.backup(store)

    def decide(self, run_id: str, *, approve: bool, actor: str, note: str):
        store, pid = self._attached()
        self._run(store, pid, run_id)
        with store.connect() as db:
            proposal = db.execute("SELECT id FROM proposals WHERE run_id=?", (run_id,)).fetchone()
        if not proposal:
            raise ValueError("No completed proposal")
        return {
            "status": store.decide(proposal[0], approve, actor, note),
            "deployment": "not_applied",
        }

    def export(self, run_id: str):
        """Write a new uniquely named directory; never overwrite existing consumer files."""
        store, pid = self._attached()
        self._run(store, pid, run_id)
        root, spec, _ = self._context()
        # The current contract must be reviewed; exports may contain the complete evidence bundle.
        with store.connect() as db:
            _, draft = projects.charter(db, pid)
        verify_live(draft, store.path.parent)
        report = operations.export_report(store, run_id)
        folder = scoped_path(root, spec.output_dir + "/" + run_id + "-" + uid()[:12])
        folder.mkdir(parents=True, exist_ok=False)
        for key, filename in (("report", "report.md"), ("json", "snapshot.json")):
            with (folder / filename).open("xb") as handle:
                handle.write(Path(report[key]).read_bytes())
        return {"report": str(folder / "report.md"), "json": str(folder / "snapshot.json")}
