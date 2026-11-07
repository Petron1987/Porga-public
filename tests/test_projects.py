import json
import sqlite3
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError

from porga.cli import DEMO, main
from porga.core import projects
from porga.core.migrations import DATABASE_VERSION, migrate_v1
from porga.core.operations import backup, export_report, health, restore
from porga.core.store import Store
from porga.organization.factory import PermissionDenied
from porga.organization.registry import organization
from porga.project_protocols import CharterDraft, TaskGraph
from porga.protocols import AgentSpec, PermissionPolicy
from porga.runtime import Runtime
from porga.workflow import resume


def spec(deliverable="research_report", **changes):
    return CharterDraft.model_validate(
        {
            "project": DEMO,
            "deliverable": deliverable,
            "success_criteria": ["Trace every finding to an exact quote; identify limitations."],
            "non_goals": ["No web browsing, production decisions or external publication."],
            "data_scope": "public_synthetic",
            "mode": "mock",
            "max_usd": "0",
            **changes,
        }
    )


def approved(store, draft=None):
    p = projects.create(store, draft or spec())
    projects.authorize(store, p["project_id"], p["digest"], "test-owner", "Synthetic test consent")
    return p["project_id"]


def test_intake_groups_missing_answers_without_reasking_known_fields(store):
    p = projects.create(store, {"project": {"goal": "Analyze public sources"}, "mode": "mock"})
    assert p["status"] == "needs_answers" and not p["authorized"]
    assert len(p["questions"]) == 5
    resource = next(q for q in p["questions"] if q["field"] == "resources")
    assert resource["missing_fields"] == ["max_usd"]
    updated = projects.revise(store, p["project_id"], spec())
    assert updated["questions"] == [] and updated["status"] == "awaiting_owner_authorization"
    assert not updated["authorized"]
    with store.connect() as db:
        assert db.execute("SELECT count(*) FROM project_authorizations").fetchone()[0] == 0


async def test_critical_missing_answers_and_no_authorization_block_execution(store, settings):
    p = projects.create(store, {"project": {"goal": "Analyze public sources"}})
    with pytest.raises(ValueError, match="missing"):
        projects.authorize(store, p["project_id"], p["digest"], "owner", "Reviewed")
    with pytest.raises(ValueError, match="no authorized"):
        await projects.execute_project(store, p["project_id"], settings)
    with store.connect() as db:
        assert db.execute("SELECT count(*) FROM runs").fetchone()[0] == 0


async def test_revisions_seal_authority_and_stale_digest_is_rejected(store, settings):
    pid = approved(store)
    old = projects.inspect(store, pid)
    new = projects.revise(store, pid, spec(non_goals=["No external writes or publication."]))
    assert new["revision"] == 2 and new["active_revision"] == 1
    with pytest.raises(ValueError, match="Stale"):
        projects.authorize(store, pid, old["digest"], "owner", "Stale review")
    with pytest.raises(ValueError, match="Newer"):
        await projects.execute_project(store, pid, settings)
    with store.connect() as db:
        assert projects.charter(db, pid, 1)[0]["sha256"] == old["digest"]
        assert db.execute("SELECT count(*) FROM runs").fetchone()[0] == 0
    projects.authorize(store, pid, new["digest"], "owner", "Reviewed new scope")
    result = await projects.execute_project(store, pid, settings)
    assert result["project_binding"]["revision"] == 2


@pytest.mark.parametrize(
    "deliverable,worker",
    [
        ("research_report", "research"),
        ("evidence_audit", "evidence_auditor"),
    ],
)
async def test_two_profiles_run_real_sdk_and_separate_final_acceptance(
    store, settings, deliverable, worker
):
    pid = approved(store, spec(deliverable))
    result = await projects.execute_project(store, pid, settings, request_key="first")
    assert result["validation_passed"] and result["model_calls"] == 4
    assert result["estimated_usd"] == "0" and not result["owner_accepted"]
    snap = store.snapshot(result["run_id"])
    assert [t["role"] for t in snap["tasks"]] == ["chief", worker, "qa"]
    assert [n["role"] for n in snap["organization"]["task_graph"]["nodes"]] == [
        "chief",
        worker,
        "qa",
    ]
    assert [a["role"] for a in snap["organization"]["agents"]] == [worker, "qa"]
    assert snap["organization"]["agents"][1]["permissions"] == []
    assert any(e["type"] == "tool_used" for e in snap["events"])
    report = export_report(store, result["run_id"])
    assert "Authorized organization" in Path(report["report"]).read_text(encoding="utf-8")
    accepted = projects.accept(store, pid, result["run_id"], "owner", "Read and accepted outcome")
    assert accepted["status"] == "owner_accepted"
    after = Store(settings.data_dir).snapshot(result["run_id"])
    assert after["proposals"][0]["status"] == "pending" and after["decisions"] == []
    assert after["proposals"][0]["deployment"] == "not_applied"
    again = await projects.execute_project(store, pid, settings, request_key="first")
    assert again["run_id"] == result["run_id"] and again["owner_accepted"]
    with pytest.raises(ValueError, match="already accepted"):
        projects.accept(store, pid, result["run_id"], "owner", "Duplicate")
    assert health(store)["ok"]


class OmittingRuntime(Runtime):
    def model(self, output, use_tool=False):
        if "findings" in output:
            output = {**output, "findings": output["findings"][:1]}
        return super().model(output, use_tool)


async def test_audit_gate_rejects_missing_source_even_when_qa_says_passed(store, settings):
    pid = approved(store, spec("evidence_audit"))
    result = await projects.execute_project(store, pid, settings, runtime_class=OmittingRuntime)
    assert result["status"] == "validation_failed"
    gate = next(
        a for a in store.snapshot(result["run_id"])["artifacts"] if a["kind"] == "evaluation"
    )
    assert not gate["content"]["checks"]["all_sources_covered"]
    with pytest.raises(ValueError, match="successful"):
        projects.accept(store, pid, result["run_id"], "owner", "Cannot accept failed gate")


async def test_authorized_profile_cannot_be_swapped_by_model(store, settings):
    class WrongTeam(Runtime):
        def model(self, output, use_tool=False):
            if "roles" in output:
                output = {**output, "roles": ["research", "qa"]}
            return super().model(output, use_tool)

    pid = approved(store, spec("evidence_audit"))
    with pytest.raises(PermissionDenied):
        await projects.execute_project(store, pid, settings, runtime_class=WrongTeam)
    with store.connect() as db:
        assert db.execute("SELECT count(*) FROM tasks").fetchone()[0] == 1


async def test_idempotency_key_cannot_cross_project_boundary(store, settings):
    first, second = approved(store), approved(store)
    await projects.execute_project(store, first, settings, request_key="shared")
    with pytest.raises(ValueError, match="another charter"):
        await projects.execute_project(store, second, settings, request_key="shared")
    with store.connect() as db:
        assert db.execute("SELECT count(*) FROM runs").fetchone()[0] == 1


@pytest.mark.parametrize("change", ["project", "limits"])
async def test_low_level_execution_checks_charter_before_model_calls(store, settings, change):
    from porga.protocols import ProjectSpec
    from porga.workflow import execute

    pid = approved(store, spec(max_calls=4))
    p = projects.inspect(store, pid)
    project = ProjectSpec.model_validate(
        {**DEMO, "goal": "Different unauthorized objective"} if change == "project" else DEMO
    )
    config = settings.model_copy(
        update={"max_calls": 20 if change == "limits" else 4, "max_usd": Decimal(0)}
    )
    with pytest.raises(ValueError, match="exceed authorized"):
        await execute(project, config, store, charter_context=(pid, p["revision"], p["digest"]))
    with store.connect() as db:
        assert db.execute("SELECT count(*) FROM runs").fetchone()[0] == 0
        assert db.execute("SELECT count(*) FROM reservations").fetchone()[0] == 0


async def test_offline_project_is_free_even_with_live_price_settings(store, settings):
    pid = approved(store)
    priced = settings.model_copy(update={"input_price": Decimal(100), "output_price": Decimal(100)})
    result = await projects.execute_project(store, pid, priced)
    assert result["estimated_usd"] == "0" and result["model_calls"] == 4
    config = json.loads(store.snapshot(result["run_id"])["run"]["settings_json"])
    assert Decimal(config["max_usd"]) == 0


async def test_mode_and_budget_cannot_expand_owner_authority(store, settings, monkeypatch):
    pid = approved(store, spec(mode="openai", max_usd="0.10", max_calls=4))
    with pytest.raises(ValueError, match="mode"):
        await projects.execute_project(store, pid, settings)

    async def capture(project, config, store, **kwargs):
        return config

    monkeypatch.setattr("porga.workflow.execute", capture)
    config = await projects.execute_project(
        store,
        pid,
        settings.model_copy(update={"mode": "openai", "max_usd": Decimal("1.00"), "max_calls": 20}),
    )
    assert config.max_usd == Decimal("0.10") and config.max_calls == 4
    p = projects.create(store, spec(mode="openai", max_usd="0"))
    with pytest.raises(ValueError, match="positive"):
        projects.authorize(store, p["project_id"], p["digest"], "owner", "Zero live budget")


@pytest.mark.parametrize(
    "policy,roles",
    [
        (PermissionPolicy(max_subagents=1), ["research", "qa"]),
        (PermissionPolicy(capabilities=()), ["research", "qa"]),
        (PermissionPolicy(), ["research", "research"]),
        (PermissionPolicy(), ["admin", "qa"]),
    ],
)
def test_registry_rejects_expansion_or_missing_verifier(policy, roles):
    with pytest.raises(PermissionDenied):
        organization("project", 1, spec(), roles, policy)


@pytest.mark.parametrize(
    "change",
    [
        {"role": "admin"},
        {"capabilities": ["shell"]},
        {"external_write": True},
    ],
)
def test_unknown_roles_tools_and_extra_authority_rejected(change):
    with pytest.raises(ValidationError):
        AgentSpec.model_validate({"role": "research", **change})


@pytest.mark.parametrize(
    "nodes",
    [
        [
            {"id": "chief", "role": "chief", "depends_on": ["verify"]},
            {"id": "produce", "role": "research", "depends_on": ["chief"]},
            {"id": "verify", "role": "qa", "depends_on": ["produce"]},
        ],
        [
            {"id": "chief", "role": "chief"},
            {"id": "produce", "role": "research", "depends_on": ["missing"]},
            {"id": "verify", "role": "qa", "depends_on": ["produce"]},
        ],
        [
            {"id": "chief", "role": "chief"},
            {"id": "one", "role": "research"},
            {"id": "two", "role": "research"},
        ],
        [
            {"id": "chief", "role": "chief"},
            {"id": "produce", "role": "research"},
            {"id": "verify", "role": "qa"},
        ],
    ],
)
def test_task_graph_rejects_cycles_unknown_dependencies_and_missing_independence(nodes):
    with pytest.raises(ValidationError):
        TaskGraph(nodes=nodes)


@pytest.mark.parametrize(
    "table,column,value",
    [
        ("charters", "content", "{}"),
        ("run_organizations", "content", "{}"),
        ("project_acceptances", "evidence_digest", "incorrect"),
    ],
)
async def test_health_and_restore_reject_changed_authority_or_outcome(
    store, settings, tmp_path, table, column, value
):
    pid = approved(store)
    result = await projects.execute_project(store, pid, settings)
    projects.accept(store, pid, result["run_id"], "owner", "Reviewed")
    with store.connect() as db:
        db.execute(f"UPDATE {table} SET {column}=?", (value,))
    assert not health(store)["ok"]
    saved = backup(store)
    with pytest.raises(ValueError):
        restore(Store(tmp_path / "restored"), Path(saved["backup"]))


async def test_backup_restores_project_acceptance_and_refuses_draft_only_target(
    store, settings, tmp_path
):
    pid = approved(store, spec("evidence_audit"))
    result = await projects.execute_project(store, pid, settings)
    projects.accept(store, pid, result["run_id"], "owner", "Reviewed coverage")
    saved = backup(store)
    dest = Store(tmp_path / "restored")
    assert restore(dest, Path(saved["backup"]))["health"]["ok"]
    assert projects.inspect(dest, pid)["status"] == "owner_accepted"
    draft_only = Store(tmp_path / "draft-only")
    projects.create(draft_only, {"project": {"goal": "Keep this draft"}})
    with pytest.raises(ValueError, match="empty"):
        restore(draft_only, Path(saved["backup"]))


async def test_resume_pins_original_charter_and_organization_after_new_revision(store, settings):
    class StopProducer(Runtime):
        async def run(self, agent, payload, **kwargs):
            if agent.name == "evidence_auditor":
                raise RuntimeError("Synthetic interruption")
            return await super().run(agent, payload, **kwargs)

    pid = approved(store, spec("evidence_audit"))
    with pytest.raises(RuntimeError):
        await projects.execute_project(store, pid, settings, runtime_class=StopProducer)
    with store.connect() as db:
        rid = db.execute("SELECT id FROM runs").fetchone()[0]
    new = projects.revise(store, pid, spec("research_report"))
    projects.authorize(store, pid, new["digest"], "owner", "New future scope")
    result = await resume(rid, store)
    assert result["project_binding"]["revision"] == 1 and result["validation_passed"]
    assert store.snapshot(rid)["organization"]["agents"][0]["role"] == "evidence_auditor"
    with pytest.raises(ValueError, match="current authorized"):
        projects.accept(store, pid, rid, "owner", "Stale outcome")


def test_v02_migration_preserves_data_and_writes_rollback_backup(tmp_path):
    schema = (Path(__file__).parent / "fixtures/v01.sql").read_text(encoding="utf-8")
    with sqlite3.connect(tmp_path / "porga.sqlite3") as db:
        db.executescript(schema)
        migrate_v1(db)
        db.execute("PRAGMA user_version=1")
        db.execute(
            "INSERT INTO runs(id,mode,status,project,created_at) VALUES(?,?,?,?,?)",
            ("old", "mock", "failed", json.dumps(DEMO), "2026-11-05"),
        )
        db.execute(
            "INSERT INTO events(run_id,type,metadata,created_at) VALUES(?,?,?,?)",
            ("old", "historical", "{}", "2026-11-05"),
        )
    upgraded = Store(tmp_path)
    assert (tmp_path / "pre-v0.3.sqlite3").exists()
    assert upgraded.snapshot("old")["events"][0]["type"] == "historical"
    assert upgraded.snapshot("old")["project_binding"] is None
    with upgraded.connect() as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == DATABASE_VERSION
    with sqlite3.connect(tmp_path / "pre-v0.3.sqlite3") as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 1
    assert Store(tmp_path).snapshot("old")["run"]["status"] == "failed"


def test_cli_intake_authorize_run_accept_requires_explicit_confirm(tmp_path, capsys, monkeypatch):
    args = ["--data-dir", str(tmp_path)]
    path = tmp_path / "charter.json"
    path.write_text(spec("evidence_audit").model_dump_json(), encoding="utf-8")
    monkeypatch.setenv("PORGA_MAX_TOKENS", "invalid")
    assert main([*args, "project", "draft", "--spec", str(path)]) == 0
    p = json.loads(capsys.readouterr().out)
    pid = p["project_id"]
    auth = [
        *args,
        "project",
        "authorize",
        pid,
        "--digest",
        p["digest"],
        "--actor",
        "owner",
        "--note",
        "Synthetic CLI test",
    ]
    assert main(auth) == 2
    capsys.readouterr()
    assert not projects.inspect(Store(tmp_path), pid)["authorized"]
    assert main([*auth, "--confirm"]) == 0
    capsys.readouterr()
    monkeypatch.delenv("PORGA_MAX_TOKENS")
    assert main([*args, "project", "run", pid, "--mode", "mock"]) == 0
    result = json.loads(capsys.readouterr().out)
    accept = [
        *args,
        "project",
        "accept",
        pid,
        "--run-id",
        result["run_id"],
        "--actor",
        "owner",
        "--note",
        "Reviewed outcome",
    ]
    assert main(accept) == 2
    capsys.readouterr()
    assert main([*accept, "--confirm"]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "owner_accepted"
