import json
from decimal import Decimal

import pytest
from pydantic import ValidationError

from porga.cli import main
from porga.core.config import Settings, load_env
from porga.core.verification import verify
from porga.organization.factory import AgentFactory, PermissionDenied
from porga.protocols import AgentSpec, PermissionPolicy, QAReview, ResearchReport


def test_protocol_rejects_unknown_capability_and_self_approval():
    with pytest.raises(ValidationError):
        AgentSpec(role="research", capabilities=("shell",))
    with pytest.raises(ValidationError):
        PermissionPolicy(self_approve=True)
    with pytest.raises(ValidationError):
        AgentSpec(role="research", hidden_admin=True)


def test_duplicate_evidence_rejected_before_execution(project):
    from porga.protocols import ProjectSpec

    data = project.model_dump()
    data["evidence"] *= 2
    with pytest.raises(ValidationError):
        ProjectSpec.model_validate(data)


def test_factory_denies_qa_evidence_tool(project, store):
    factory = AgentFactory(PermissionPolicy(), project, None, store, "no-run")
    with pytest.raises(PermissionDenied):
        factory.create(AgentSpec(role="qa", capabilities=("read_evidence",)), {})


def test_factory_team_limit(project, store):
    factory = AgentFactory(PermissionPolicy(max_subagents=1), project, None, store, "no-run")
    factory.created.add("research")
    with pytest.raises(PermissionDenied):
        factory.create(AgentSpec(role="qa"), {})


def test_exact_quote_gate_and_duplicate_ids(project):
    report = ResearchReport(
        summary="Unverified narrative",
        findings=[{"evidence_id": "charter", "quote": "Not in original evidence"}],
        uncertainties=[],
    )
    gate = verify(project, report, QAReview(passed=True, issues=[]))
    assert not gate.passed and "exact_quotes" in gate.issues
    duplicate = project.model_copy(update={"evidence": [project.evidence[0]] * 2})
    assert not verify(duplicate, report, QAReview(passed=True, issues=[])).passed


def test_online_requires_credentials_and_prices(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ValueError, match="API_KEY"):
        Settings(mode="openai").validate_online()
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-test-value")
    with pytest.raises(ValueError, match="prices"):
        Settings(mode="openai").validate_online()


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-1"])
def test_invalid_money_rejected(value):
    with pytest.raises(ValidationError):
        Settings(input_price=Decimal(value))


def test_dotenv_is_literal_and_preserves_existing(tmp_path, monkeypatch):
    monkeypatch.setenv("PORGA_MODEL", "existing")
    monkeypatch.delenv("PORGA_FAKE", raising=False)
    file = tmp_path / ".env"
    file.write_text("PORGA_MODEL=other\nPORGA_FAKE=$(echo secret)\nPATH=bad", encoding="utf-8")
    load_env(file)
    import os

    assert os.environ["PORGA_MODEL"] == "existing"
    assert os.environ["PORGA_FAKE"] == "$(echo secret)"
    assert os.environ["PATH"] != "bad"


def test_cli_requires_explicit_approval(tmp_path, capsys):
    assert (
        main(
            [
                "--data-dir",
                str(tmp_path),
                "approve",
                "missing",
                "--actor",
                "owner",
                "--note",
                "reviewed",
            ]
        )
        == 2
    )
    assert "Invalid input" in capsys.readouterr().err


def test_cli_demo_and_restart_inspection(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("PORGA_MODE", "mock")
    args = ["--data-dir", str(tmp_path)]
    assert main([*args, "demo"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert main([*args, "inspect", result["run_id"]]) == 0
    assert json.loads(capsys.readouterr().out)["proposals"][0]["status"] == "pending"
