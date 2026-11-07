"""Exercise the actual Responses adapter against an in-memory HTTP transport, never the API."""

import json
from decimal import Decimal

import httpx2
import pytest
from openai import AsyncOpenAI, InternalServerError

from porga.workflow import execute


def online(settings):
    return settings.model_copy(
        update={
            "mode": "openai",
            "model": "test-model",
            "input_price": Decimal("1"),
            "output_price": Decimal("2"),
        }
    )


def install_transport(monkeypatch, handler):
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-adapter-test-key")

    def client(**kwargs):
        return AsyncOpenAI(
            **kwargs, http_client=httpx2.AsyncClient(transport=httpx2.MockTransport(handler))
        )

    monkeypatch.setattr("openai.AsyncOpenAI", client)


async def test_online_requests_use_structured_output_tools_and_no_store(
    project, settings, store, monkeypatch
):
    requests = []
    fixtures = [
        {"research_question": project.goal, "roles": ["research", "qa"]},
        None,
        {
            "summary": "Evidence-only report",
            "findings": [{"evidence_id": e.id, "quote": e.text} for e in project.evidence],
            "uncertainties": ["Freshness unverified"],
        },
        {"passed": True, "issues": []},
    ]

    def handler(request):
        body = json.loads(request.content)
        requests.append(body)
        assert request.url.host == "api.openai.com"
        assert body["store"] is False
        assert body["max_output_tokens"] == settings.max_output_tokens
        index = len(requests) - 1
        if index == 1:
            assert [t["name"] for t in body["tools"]] == ["read_evidence"]
            output = [
                {
                    "type": "function_call",
                    "name": "read_evidence",
                    "arguments": "{}",
                    "id": "fc_test",
                    "call_id": "call_test",
                    "status": "completed",
                }
            ]
        else:
            output = [
                {
                    "type": "message",
                    "id": f"msg_{index}",
                    "role": "assistant",
                    "status": "completed",
                    "content": [
                        {
                            "type": "output_text",
                            "text": json.dumps(fixtures[index]),
                            "annotations": [],
                        }
                    ],
                }
            ]
        return httpx2.Response(
            200,
            json={
                "id": f"resp_{index}",
                "object": "response",
                "created_at": 0,
                "status": "completed",
                "model": "test-model",
                "output": output,
                "usage": {
                    "input_tokens": 100,
                    "output_tokens": 100,
                    "total_tokens": 200,
                    "input_tokens_details": {"cached_tokens": 0},
                    "output_tokens_details": {"reasoning_tokens": 0},
                },
            },
        )

    install_transport(monkeypatch, handler)
    result = await execute(project, online(settings), store)
    assert result["validation_passed"] and result["mode"] == "openai"
    assert len(requests) == 4 and result["model_calls"] == 4
    assert Decimal(result["estimated_usd"]) == Decimal("0.0012")
    assert any(item.get("type") == "function_call_output" for item in requests[2]["input"])
    assert "synthetic-adapter-test-key" not in json.dumps(store.snapshot(result["run_id"]))


async def test_provider_error_is_not_retried_and_retains_reservation(
    project, settings, store, monkeypatch
):
    calls = []

    def handler(request):
        calls.append(1)
        return httpx2.Response(500, json={"error": {"message": "synthetic failure"}})

    install_transport(monkeypatch, handler)
    with pytest.raises(InternalServerError):
        await execute(project, online(settings), store)
    assert len(calls) == 1
    with store.connect() as db:
        assert db.execute("SELECT status FROM runs").fetchone()[0] == "failed"
        reserved = db.execute("SELECT count(*) FROM events WHERE type='model_reserved'")
        assert reserved.fetchone()[0] == 1
        assert db.execute("SELECT count(*) FROM events WHERE type='model_usage'").fetchone()[0] == 0
        assert db.execute("SELECT count(*) FROM proposals").fetchone()[0] == 0
