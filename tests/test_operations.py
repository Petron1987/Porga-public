import json
import sqlite3
from pathlib import Path

import pytest

from porga.cli import main
from porga.core.migrations import DATABASE_VERSION
from porga.core.operations import backup, export_report, health, restore
from porga.core.store import Store
from porga.evolution.evaluation import evaluate
from porga.workflow import execute


async def test_verified_backup_and_restore_preserves_decisions(project, settings, store, tmp_path):
    r = await execute(project, settings, store)
    store.decide(r["proposal_id"], True, "owner", "Reviewed evidence")
    saved = backup(store)
    destination = Store(tmp_path / "restored")
    from pathlib import Path

    restored = restore(destination, Path(saved["backup"]))
    assert restored["health"]["ok"]
    assert destination.snapshot(r["run_id"])["decisions"][0]["decision"] == "approved"
    with pytest.raises(ValueError, match="empty"):
        restore(destination, Path(saved["backup"]))


async def test_report_export_and_integrity_failure(project, settings, store):
    r = await execute(project, settings, store)
    output = export_report(store, r["run_id"])
    from pathlib import Path

    assert "Porga research report" in Path(output["report"]).read_text(encoding="utf-8")
    assert json.loads(Path(output["json"]).read_text(encoding="utf-8"))["run"]["id"] == r["run_id"]
    with store.connect() as db:
        db.execute("UPDATE artifacts SET content='{}' WHERE kind='research'")
    assert health(store)["ok"] is False
    with pytest.raises(ValueError, match="tampered"):
        store.decide(r["proposal_id"], True, "owner", "Must be blocked")


def test_v01_migration_backs_up_and_retains_original_runs(tmp_path):
    # Historical schema fixture works in fresh/shallow checkouts too.
    schema = (Path(__file__).parent / "fixtures/v01.sql").read_text(encoding="utf-8")
    with sqlite3.connect(tmp_path / "porga.sqlite3") as db:
        db.executescript(schema)
        db.execute(
            "INSERT INTO runs VALUES(?,?,?,?,?)",
            ("legacy", "mock", "failed", '{"goal":"legacy"}', "2026-11-05"),
        )
    upgraded = Store(tmp_path)
    assert (tmp_path / "pre-v0.2.sqlite3").exists()
    with upgraded.connect() as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == DATABASE_VERSION
        assert db.execute("SELECT id FROM runs").fetchone()[0] == "legacy"
    assert Store(tmp_path).snapshot("legacy")["run"]["status"] == "failed"


def test_fixed_gate_regression_suite():
    r = evaluate()
    assert r["passed"] and len(r["cases"]) == 6


def test_cli_operational_commands(tmp_path, capsys):
    args = ["--data-dir", str(tmp_path)]
    assert main([*args, "demo", "--request-key", "first-task"]) == 0
    r = json.loads(capsys.readouterr().out)
    assert main([*args, "report", r["run_id"]]) == 0
    assert "report" in json.loads(capsys.readouterr().out)
    assert main([*args, "health"]) == 0
    assert json.loads(capsys.readouterr().out)["ok"]
    assert main([*args, "evaluate"]) == 0
    assert json.loads(capsys.readouterr().out)["passed"]


def test_health_works_with_broken_model_configuration(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("PORGA_MAX_TOKENS", "invalid")
    assert main(["--data-dir", str(tmp_path), "health"]) == 0
    assert json.loads(capsys.readouterr().out)["ok"]


def test_readiness_does_not_claim_real_production_acceptance(settings, store, monkeypatch):
    from porga.core.operations import readiness

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    r = readiness(store, settings)
    assert r["offline_pilot_ready"]
    assert not r["production_ready"] and not r["online_configured"]
