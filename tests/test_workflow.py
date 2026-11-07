import asyncio
import json
from decimal import Decimal

import pytest

from porga.core.budget import BudgetExceeded
from porga.core.store import Store
from porga.runtime import Runtime
from porga.workflow import execute


async def test_full_sdk_loop_persists_pending_and_survives_restart(project, settings, store):
    result = await execute(project, settings, store)
    assert result["status"] == "awaiting_approval"
    assert result["model_calls"] == 4  # chief, research tool request + final, qa
    assert result["estimated_usd"] == "0"
    snapshot = Store(settings.data_dir).snapshot(result["run_id"])
    assert [t["role"] for t in snapshot["tasks"]] == ["chief", "research", "qa"]
    assert all(t["status"] == "completed" for t in snapshot["tasks"])
    assert {a["kind"] for a in snapshot["artifacts"]} == {"plan", "research", "qa", "evaluation"}
    assert snapshot["proposals"][0]["status"] == "pending"
    assert snapshot["decisions"] == []
    assert any(e["type"] == "tool_used" for e in snapshot["events"])


async def test_explicit_human_decision_is_durable_and_once(project, settings, store):
    result = await execute(project, settings, store)
    p = result["proposal_id"]
    status = store.decide(p, True, "human-owner", "Reviewed evidence and next experiment")
    assert status == "approved"
    s = Store(settings.data_dir).snapshot(result["run_id"])
    assert s["decisions"][0]["actor"] == "human-owner"
    assert s["proposals"][0]["deployment"] == "not_applied"
    with pytest.raises(ValueError, match="already decided"):
        store.decide(p, False, "human-owner", "duplicate")


async def test_human_reject(project, settings, store):
    result = await execute(project, settings, store)
    assert store.decide(result["proposal_id"], False, "owner", "Needs more evidence") == "rejected"


class FabricatingRuntime(Runtime):
    def model(self, output, use_tool=False):
        if "findings" in output:
            output = {
                **output,
                "findings": [{"evidence_id": "invented", "quote": "Invented evidence statement"}],
            }
        return super().model(output, use_tool)


async def test_lying_qa_cannot_bypass_deterministic_gate(project, settings, store):
    result = await execute(project, settings, store, runtime_class=FabricatingRuntime)
    assert result["status"] == "validation_failed"
    with pytest.raises(ValueError, match="cannot be approved"):
        store.decide(result["proposal_id"], True, "owner", "Try bypass")


class RejectingRuntime(Runtime):
    def model(self, output, use_tool=False):
        if "passed" in output:
            output = {"passed": False, "issues": ["Unsupported summary"]}
        return super().model(output, use_tool)


async def test_qa_veto_is_binding(project, settings, store):
    result = await execute(project, settings, store, runtime_class=RejectingRuntime)
    assert not result["validation_passed"]


@pytest.mark.parametrize(
    "limits",
    [
        {"max_calls": 1},
        {"max_tokens": 1},
        {"max_usd": Decimal("0.000001"), "input_price": Decimal("100")},
    ],
)
async def test_budget_stop_leaves_failed_audit(project, settings, store, limits):
    with pytest.raises(BudgetExceeded):
        await execute(project, settings.model_copy(update=limits), store)
    with store.connect() as db:
        assert db.execute("SELECT status FROM runs").fetchone()[0] == "failed"
        assert db.execute("SELECT count(*) FROM proposals").fetchone()[0] == 0
        assert db.execute("SELECT count(*) FROM tasks WHERE status='running'").fetchone()[0] == 0


class TimeoutRuntime(Runtime):
    def model(self, output, use_tool=False):
        model = super().model(output, use_tool)

        async def stalled(*args, **kwargs):
            await asyncio.sleep(1)

        model.inner.get_response = stalled
        return model


async def test_timeout_retains_reservation_and_logs_no_payload(project, settings, store):
    with pytest.raises(TimeoutError):
        await execute(
            project,
            settings.model_copy(update={"timeout_seconds": 0.01}),
            store,
            runtime_class=TimeoutRuntime,
        )
    with store.connect() as db:
        events = [dict(r) for r in db.execute("SELECT * FROM events")]
    assert any(e["type"] == "model_reserved" for e in events)
    assert not any(e["type"] == "model_usage" for e in events)
    assert project.goal not in json.dumps(events)


async def test_tampered_evaluation_blocks_approval(project, settings, store):
    r = await execute(project, settings, store)
    with store.connect() as db:
        db.execute("UPDATE artifacts SET content='{}' WHERE kind='evaluation'")
    with pytest.raises(ValueError, match="tampered"):
        store.decide(r["proposal_id"], True, "owner", "Reviewed")


class InvalidPlanRuntime(Runtime):
    def model(self, output, use_tool=False):
        if "roles" in output:
            output = {**output, "roles": ["qa", "qa"]}
        return super().model(output, use_tool)


async def test_chief_cannot_expand_or_skip_team(project, settings, store):
    from porga.organization.factory import PermissionDenied

    with pytest.raises(PermissionDenied):
        await execute(project, settings, store, runtime_class=InvalidPlanRuntime)


class MalformedRuntime(Runtime):
    def model(self, output, use_tool=False):
        return super().model({"unexpected_admin_field": True}, use_tool)


async def test_malformed_model_output_stops_before_specialists(project, settings, store):
    from agents.exceptions import ModelBehaviorError

    with pytest.raises(ModelBehaviorError):
        await execute(project, settings, store, runtime_class=MalformedRuntime)
    with store.connect() as db:
        assert db.execute("SELECT status FROM runs").fetchone()[0] == "failed"
        assert db.execute("SELECT count(*) FROM tasks").fetchone()[0] == 1
        assert db.execute("SELECT count(*) FROM proposals").fetchone()[0] == 0
