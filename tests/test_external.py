import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
from pathlib import Path

import pytest
from pydantic import ValidationError

from porga import __version__
from porga.api import ProjectClient, RunOptions
from porga.cli import main
from porga.core import projects
from porga.core.config import Settings
from porga.core.operations import health
from porga.core.store import Store, canonical
from porga.project_protocols import CharterDraft


def consumer(root, **changes):
    root.mkdir(parents=True, exist_ok=True)
    source = root / "evidence.txt"
    source.write_bytes(b"Synthetic service requires exact quotes and separate QA review.\n")
    data = {
        "schema_version": "1",
        "project_key": "consumer",
        "porga_version": __version__,
        "goal": "Audit the supplied synthetic operating principles.",
        "deliverable": "evidence_audit",
        "success_criteria": ["Cover every supplied source."],
        "non_goals": ["No external publication or modification of source files."],
        "sources": [
            {
                "id": "principles",
                "title": "Synthetic principles",
                "path": source.name,
                "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            }
        ],
        **changes,
    }
    path = root / "porga.project.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return ProjectClient(path)


def update(client, **changes):
    data = json.loads(client.manifest.read_text(encoding="utf-8"))
    data.update(changes)
    client.manifest.write_text(json.dumps(data), encoding="utf-8")


def authorize(client):
    p = client.attach()
    client.authorize(p["digest"], actor="test-owner", note="Synthetic integration consent")
    return p


async def test_independent_consumer_full_lifecycle_never_modifies_source(tmp_path, monkeypatch):
    root = tmp_path / "Consumer A"
    client = consumer(root)
    original = (root / "evidence.txt").read_bytes()
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    preview = client.preview()
    assert (
        preview["charter"]["data_scope"] == "private"
    )  # Conservative default, never relabeled public.
    assert not (root / ".porga").exists() and not (elsewhere / ".porga").exists()
    p = client.attach()
    assert p["status"] == "awaiting_owner_authorization"
    assert client.attach()["project_id"] == p["project_id"]
    with pytest.raises(ValueError, match="no authorized"):
        await client.run()
    client.authorize(p["digest"], actor="owner", note="Reviewed synthetic test evidence")
    result = await client.run(request_key="first")
    assert result["validation_passed"] and result["model_calls"] == 4
    assert result["estimated_usd"] == "0"
    snap = client.inspect_run(result["run_id"])
    assert snap["charter"]["external"]["root"] == str(root)
    assert snap["charter_authorization"]["actor"] == "owner"
    first, second = client.export(result["run_id"]), client.export(result["run_id"])
    assert Path(first["report"]).is_relative_to(root / "porga-results")
    assert first != second and Path(first["report"]).exists()
    assert (
        client.accept(result["run_id"], actor="owner", note="Read synthetic result")["status"]
        == "owner_accepted"
    )
    assert client.inspect_run(result["run_id"])["proposals"][0]["status"] == "pending"
    assert (
        client.decide(result["run_id"], approve=True, actor="owner", note="Next experiment only")[
            "deployment"
        ]
        == "not_applied"
    )
    assert client.health()["ok"] and Path(client.backup()["backup"]).exists()
    assert (root / "evidence.txt").read_bytes() == original
    assert not (elsewhere / ".porga").exists()


@pytest.mark.parametrize(
    "path",
    [
        "../outside.txt",
        "/etc/passwd",
        "C:/secrets.txt",
        "//server/share/a.txt",
        "a/../../x",
        "a.txt:secret",
        "NUL.txt",
        ".env",
        ".git/config",
        ".venv/a.txt",
    ],
)
def test_unsafe_source_paths_rejected_before_state_creation(tmp_path, path):
    client = consumer(tmp_path)
    source = json.loads(client.manifest.read_text())["sources"][0]
    update(client, sources=[{**source, "path": path}])
    with pytest.raises(ValueError):
        client.attach()
    assert not (tmp_path / ".porga").exists()


@pytest.mark.parametrize(
    "change",
    [
        {"porga_version": "99.0.0"},
        {"schema_version": "99"},
        {"module": "untrusted.plugin"},
        {"output_dir": ".porga/reports"},
        {"state_dir": "../shared"},
        {"mode": "openai", "egress": "deny", "max_usd": "1"},
        {"mode": "openai", "egress": "openai", "max_usd": "0"},
    ],
)
def test_invalid_configuration_fails_closed(tmp_path, change):
    client = consumer(tmp_path, **change)
    with pytest.raises(ValueError):
        client.preview()
    assert not (tmp_path / ".porga").exists()


async def test_file_change_requires_new_snapshot_and_authorization_even_on_low_level_entry(
    tmp_path,
):
    client = consumer(tmp_path)
    old = authorize(client)
    source = tmp_path / "evidence.txt"
    source.write_bytes(
        b"Updated synthetic evidence: changes require review and a new authorization.\n"
    )
    from porga.protocols import ProjectSpec
    from porga.workflow import execute

    store = Store(tmp_path / ".porga")
    settings = Settings(data_dir=tmp_path / ".porga", max_usd=0)
    with pytest.raises(ValueError, match="Source changed"):
        await execute(
            ProjectSpec.model_validate(old["charter"]["project"]),
            settings,
            store,
            charter_context=(old["project_id"], old["revision"], old["digest"]),
        )
    with pytest.raises(ValueError):
        await client.run()
    data = json.loads(client.manifest.read_text())
    data["sources"][0]["sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
    update(client, **data)
    revised = client.attach()
    assert revised["revision"] == 2 and not revised["authorized"]
    with pytest.raises(ValueError, match="Stale"):
        client.authorize(old["digest"], actor="owner", note="Stale review")
    with pytest.raises(ValueError, match="Newer"):
        await client.run()
    client.authorize(revised["digest"], actor="owner", note="New evidence reviewed")
    assert (await client.run())["validation_passed"]
    assert health(store)["ok"]


async def test_egress_is_explicit_and_also_enforced_by_core_authorization(tmp_path, monkeypatch):
    client = consumer(tmp_path, mode="openai", egress="openai", max_usd="0.05")
    p = client.attach()
    store = Store(tmp_path / ".porga")
    with pytest.raises(ValueError, match="allow-openai"):
        projects.authorize(store, p["project_id"], p["digest"], "owner", "Missing egress consent")
    assert not client.inspect()["authorized"]
    client.authorize(
        p["digest"], actor="owner", note="Synthetic OpenAI egress consent", allow_openai=True
    )
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ValueError, match="API_KEY"):
        await client.run(options=RunOptions(model="test-model", input_price=1, output_price=1))
    with store.connect() as db:
        assert db.execute("SELECT count(*) FROM runs").fetchone()[0] == 0
        event = json.loads(
            db.execute("SELECT metadata FROM events WHERE type='charter_authorized'").fetchone()[0]
        )
        assert event["openai_egress"]


async def test_projects_have_isolated_state_and_cannot_use_other_run_or_cloned_database(tmp_path):
    a, b = consumer(tmp_path / "a"), consumer(tmp_path / "b")
    authorize(a)
    authorize(b)
    result = await a.run()
    for action in (b.inspect_run, b.export):
        with pytest.raises(ValueError, match="another project"):
            action(result["run_id"])
    assert b.inspect()["acceptances"] == []
    c = consumer(tmp_path / "c")
    shutil.copytree(tmp_path / "a" / ".porga", tmp_path / "c" / ".porga")
    before = (tmp_path / "c" / ".porga/porga.sqlite3").read_bytes()
    with pytest.raises(ValueError, match="another project"):
        c.attach()
    assert (tmp_path / "c" / ".porga/porga.sqlite3").read_bytes() == before


@pytest.mark.parametrize("kind", ["source", "state", "output"])
def test_symlink_escape_rejected(tmp_path, kind):
    client = consumer(tmp_path / "project")
    outside = tmp_path / "outside"
    outside.mkdir()
    path = (
        client.manifest.parent
        / {"source": "link.txt", "state": ".porga", "output": "porga-results"}[kind]
    )
    target = outside / "evidence.txt" if kind == "source" else outside
    if kind == "source":
        target.write_text("External unapproved contents", encoding="utf-8")
    try:
        path.symlink_to(target, target_is_directory=kind != "source")
    except OSError:
        pytest.skip("Host does not permit symlink creation")
    if kind == "source":
        data = json.loads(client.manifest.read_text())
        update(client, sources=[{**data["sources"][0], "path": "link.txt"}])
    with pytest.raises(ValueError, match="Symlinks"):
        client.preview()


def test_file_bounds_hash_and_unknown_decoders_rejected(tmp_path):
    client = consumer(tmp_path)
    source = tmp_path / "evidence.txt"
    source.write_bytes(b"a" * 16001)
    with pytest.raises(ValueError, match="bounded"):
        client.preview()
    source.write_bytes(b"Changed evidence")
    with pytest.raises(ValueError, match="Source changed"):
        client.preview()
    data = json.loads(client.manifest.read_text())
    update(client, sources=[{**data["sources"][0], "path": "execute.py"}])
    with pytest.raises(ValueError, match="explicit UTF-8"):
        client.preview()


def test_private_evidence_cannot_bypass_binding_via_legacy_charter():
    with pytest.raises(ValidationError, match="requires an external"):
        CharterDraft(project={"goal": "Secret task"}, data_scope="private")


@pytest.mark.skipif(os.name != "nt", reason="Windows junction policy")
def test_windows_junction_escape_is_rejected_without_following_target(tmp_path):
    client = consumer(tmp_path / "project")
    outside = tmp_path / "outside"
    outside.mkdir()
    link = client.manifest.parent / "porga-results"
    assert link.absolute().is_relative_to(tmp_path) and outside.absolute().is_relative_to(tmp_path)

    def quote(path):
        return "'" + str(path).replace("'", "''") + "'"

    command = (
        f"New-Item -ItemType Junction -Path {quote(link)} -Target {quote(outside)} "
        "-ErrorAction Stop | Out-Null"
    )
    subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
        capture_output=True,
        check=True,
        timeout=20,
    )
    with pytest.raises(ValueError, match="junctions"):
        client.preview()
    assert list(outside.iterdir()) == []


def test_v03_upgrade_writes_rollback_snapshot_and_fences_old_code(tmp_path):
    from porga.core.migrations import DATABASE_VERSION

    store = Store(tmp_path)
    with store.connect() as db:
        db.execute("PRAGMA user_version=2")
    Store(tmp_path)
    with sqlite3.connect(tmp_path / "pre-v0.4.sqlite3") as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 2
    with store.connect() as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == DATABASE_VERSION == 3


def test_hard_link_source_rejected(tmp_path):
    client = consumer(tmp_path / "project")
    outside = tmp_path / "outside.txt"
    outside.write_bytes(b"Synthetic outside source, not a permitted regular snapshot.")
    linked = client.manifest.parent / "linked.txt"
    os.link(outside, linked)
    update(
        client,
        sources=[
            {
                "id": "linked",
                "title": "Synthetic link",
                "path": "linked.txt",
                "sha256": hashlib.sha256(outside.read_bytes()).hexdigest(),
            }
        ],
    )
    with pytest.raises(ValueError, match="hard links"):
        client.preview()


async def test_resume_rejects_contract_change_before_model_call(tmp_path):
    from porga.runtime import Runtime
    from porga.workflow import resume

    class Interrupt(Runtime):
        async def run(self, agent, payload, **kwargs):
            if agent.name == "evidence_auditor":
                raise RuntimeError("Synthetic interruption")
            return await super().run(agent, payload, **kwargs)

    client = consumer(tmp_path)
    p = authorize(client)
    store = Store(tmp_path / ".porga")
    with pytest.raises(RuntimeError):
        await projects.execute_project(
            store, p["project_id"], Settings(data_dir=tmp_path / ".porga"), runtime_class=Interrupt
        )
    with store.connect() as db:
        rid = db.execute("SELECT id FROM runs").fetchone()[0]
        count = db.execute("SELECT count(*) FROM reservations").fetchone()[0]
    update(client, goal="Changed objective requires a new review.")
    with pytest.raises(ValueError, match="contract or evidence changed"):
        await resume(rid, store)
    with store.connect() as db:
        assert db.execute("SELECT count(*) FROM reservations").fetchone()[0] == count
        assert db.execute("SELECT status FROM runs").fetchone()[0] == "failed"


async def test_resume_cannot_turn_a_private_offline_run_into_online_via_settings(tmp_path):
    from porga.workflow import resume

    client = consumer(tmp_path)
    authorize(client)
    with pytest.raises(RuntimeError):
        # BudgetExceeded is a RuntimeError; stop after chief without any live model.
        await client.run(options=RunOptions(max_calls=1))
    store = Store(tmp_path / ".porga")
    with store.connect() as db:
        row = db.execute("SELECT id,settings_json FROM runs").fetchone()
        config = json.loads(row["settings_json"])
        config["mode"] = "openai"
        db.execute("UPDATE runs SET settings_json=? WHERE id=?", (json.dumps(config), row["id"]))
    with pytest.raises(ValueError, match="differs from authorized"):
        await resume(row["id"], store, allow_replay=True)


async def test_historical_v03_charter_without_binding_field_remains_readable(
    project, settings, store
):
    draft = CharterDraft(
        project=project.model_dump(include={"goal", "evidence"}),
        deliverable="research_report",
        success_criteria=["Use exact quotes"],
        non_goals=["No publication"],
        data_scope="public_synthetic",
        mode="mock",
        max_usd=0,
    )
    p = projects.create(store, draft)
    projects.authorize(store, p["project_id"], p["digest"], "owner", "Legacy consent fixture")
    result = await projects.execute_project(store, p["project_id"], settings)
    body = draft.model_dump(mode="json")
    body.pop("external")
    old_digest = projects.digest(body)
    with store.connect() as db:
        db.execute("UPDATE charters SET content=?,sha256=?", (canonical(body), old_digest))
        db.execute("UPDATE project_authorizations SET digest=?", (old_digest,))
        db.execute("UPDATE run_projects SET charter_digest=?", (old_digest,))
    assert projects.inspect(store, p["project_id"])["authorized"]
    assert store.snapshot(result["run_id"])["charter"].get("external") is None
    assert health(store)["ok"]


def test_cli_has_no_ambient_state_or_dotenv_dependency(tmp_path, monkeypatch, capsys):
    client = consumer(tmp_path / "project")
    cwd = tmp_path / "unrelated"
    cwd.mkdir()
    (cwd / ".env").write_text("PORGA_MAX_CALLS=invalid\n", encoding="utf-8")
    monkeypatch.chdir(cwd)
    monkeypatch.setenv("PORGA_DATA_DIR", str(cwd / "wrong-state"))
    monkeypatch.setenv("PORGA_MODE", "invalid-mode")
    base = ["external"]
    manifest = ["--manifest", str(client.manifest)]
    assert main([*base, "preview", *manifest]) == 0
    assert not json.loads(capsys.readouterr().out)["authorized"]
    assert main([*base, "attach", *manifest]) == 0
    p = json.loads(capsys.readouterr().out)
    command = [
        *base,
        "authorize",
        *manifest,
        "--digest",
        p["digest"],
        "--actor",
        "owner",
        "--note",
        "Test",
    ]
    assert main(command) == 2
    capsys.readouterr()
    assert main([*command, "--confirm"]) == 0
    capsys.readouterr()
    assert main([*base, "run", *manifest]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["validation_passed"]
    assert not (cwd / "wrong-state").exists() and not (cwd / ".porga").exists()
