"""Real SDK runner with an offline Model and a governed online Model adapter."""

import asyncio
import json

from agents import Model, ModelSettings, RunConfig, Runner, set_tracing_disabled
from agents.items import ModelResponse
from agents.usage import Usage
from openai.types.responses import (
    ResponseFunctionToolCall,
    ResponseOutputMessage,
    ResponseOutputText,
)

from porga.core.store import uid


class OfflineModel(Model):
    """Deterministic model; SDK still validates output and executes the real tool loop."""

    def __init__(self, output, use_tool=False):
        self.output, self.use_tool = output, use_tool
        self.calls = 0

    async def get_response(self, *args, **kwargs):
        self.calls += 1
        if self.use_tool and self.calls == 1:
            output = [
                ResponseFunctionToolCall(
                    id=uid(),
                    call_id=uid(),
                    name="read_evidence",
                    arguments="{}",
                    type="function_call",
                )
            ]
        else:
            output = [
                ResponseOutputMessage(
                    id=uid(),
                    role="assistant",
                    status="completed",
                    type="message",
                    content=[
                        ResponseOutputText(
                            text=json.dumps(self.output), type="output_text", annotations=[]
                        )
                    ],
                )
            ]
        return ModelResponse(
            output=output,
            usage=Usage(requests=1, input_tokens=100, output_tokens=100, total_tokens=200),
            response_id=None,
        )

    async def stream_response(self, *args, **kwargs):
        raise NotImplementedError("Streaming is outside the v0.1 governed path")
        yield  # pragma: no cover


class GovernedModel(Model):
    def __init__(self, inner, ledger):
        self.inner, self.ledger = inner, ledger

    async def get_response(
        self,
        system_instructions,
        input,
        model_settings,
        tools,
        output_schema,
        handoffs,
        tracing,
        **kwargs,
    ):
        payload = {
            "instructions": system_instructions,
            "input": input,
            "schema": output_schema.json_schema() if output_schema else None,
            "tools": [{"name": t.name, "schema": t.params_json_schema} for t in tools],
        }
        size = len(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
        reserved = self.ledger.reserve(size)
        response = await asyncio.wait_for(
            self.inner.get_response(
                system_instructions,
                input,
                model_settings,
                tools,
                output_schema,
                handoffs,
                tracing,
                **kwargs,
            ),
            timeout=self.ledger.settings.timeout_seconds,
        )
        self.ledger.settle(reserved, response.usage)
        return response

    async def stream_response(self, *args, **kwargs):
        raise NotImplementedError("Streaming is outside the v0.1 governed path")
        yield  # pragma: no cover


class Runtime:
    def __init__(self, settings, ledger):
        set_tracing_disabled(True)
        self.settings, self.ledger = settings, ledger
        self.client = None
        settings.validate_online()
        if settings.mode == "openai":
            from openai import AsyncOpenAI

            # Only the official API endpoint. No inherited base URL or project headers.
            self.client = AsyncOpenAI(
                base_url="https://api.openai.com/v1",
                max_retries=0,
                timeout=settings.timeout_seconds,
            )

    def model(self, output, use_tool=False):
        if self.client is None:
            inner = OfflineModel(output, use_tool)
        else:
            from agents.models.openai_responses import OpenAIResponsesModel

            inner = OpenAIResponsesModel(self.settings.model, self.client)
        return GovernedModel(inner, self.ledger)

    async def run(self, agent, payload, turns=1):
        return (
            await Runner.run(
                agent,
                json.dumps(payload, ensure_ascii=False),
                max_turns=turns,
                run_config=RunConfig(
                    tracing_disabled=True,
                    trace_include_sensitive_data=False,
                    model_settings=ModelSettings(
                        max_tokens=self.settings.max_output_tokens, store=False
                    ),
                ),
            )
        ).final_output

    async def close(self):
        if self.client:
            await self.client.close()
