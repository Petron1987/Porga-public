"""External consumer contract v1. No plugins, credentials or executable configuration."""

import re
from decimal import Decimal
from typing import Literal

from pydantic import Field, field_validator, model_validator

from porga.protocols import Contract


def relative_path(value: str) -> str:
    value = value.replace("\\", "/")
    parts = value.split("/")
    if (
        not value
        or len(value) > 240
        or any(
            not p
            or p in (".", "..")
            or p.endswith((".", " "))
            or any(c in p for c in ':*?"<>|\x00')
            or any(ord(c) < 32 for c in p)
            for p in parts
        )
    ):
        raise ValueError("Use a bounded relative path without traversal, drives or streams")
    for p in parts:
        stem = p.split(".")[0].upper()
        if stem in {"CON", "PRN", "AUX", "NUL"} or re.fullmatch(r"(?:COM|LPT)[1-9]", stem):
            raise ValueError("Reserved device path")
        if p.lower() in {".git", ".venv", "node_modules", "__pycache__"} or p.lower().startswith(
            ".env"
        ):
            raise ValueError("Credential, dependency and repository internals are not sources")
    return value


class SourceFile(Contract):
    id: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,39}$")
    title: str = Field(min_length=1, max_length=200)
    path: str
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")

    _path = field_validator("path")(relative_path)


class ExternalProjectSpec(Contract):
    schema_version: Literal["1"] = "1"
    project_key: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,59}$")
    porga_version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    state_dir: str = ".porga"
    output_dir: str = "porga-results"
    sources: list[SourceFile] = Field(min_length=1, max_length=8)
    goal: str = Field(min_length=1, max_length=1000)
    deliverable: Literal["research_report", "evidence_audit"]
    success_criteria: list[str] = Field(min_length=1, max_length=8)
    non_goals: list[str] = Field(min_length=1, max_length=8)
    classification: Literal["public_synthetic", "private"] = "private"
    egress: Literal["deny", "openai"] = "deny"
    mode: Literal["mock", "openai"] = "mock"
    max_usd: Decimal = Field(default=Decimal(0), ge=0, le=100, allow_inf_nan=False)
    max_calls: int = Field(default=6, ge=4, le=20)
    require_all_sources: bool = True

    _paths = field_validator("state_dir", "output_dir")(relative_path)

    @model_validator(mode="after")
    def boundaries(self):
        state, output = self.state_dir.casefold(), self.output_dir.casefold()
        if state == output or state.startswith(output + "/") or output.startswith(state + "/"):
            raise ValueError("State and output directories must be disjoint")
        if len({s.id for s in self.sources}) != len(self.sources) or len(
            {s.path.casefold() for s in self.sources}
        ) != len(self.sources):
            raise ValueError("Source IDs and paths must be unique")
        if not self.goal.strip() or any(
            not s.strip() or len(s) > 500 for s in self.success_criteria + self.non_goals
        ):
            raise ValueError("Goal, criteria and exclusions must be nonblank and bounded")
        if self.mode == "openai" and (self.egress != "openai" or self.max_usd <= 0):
            raise ValueError("Online mode requires declared OpenAI egress and a positive budget")
        for source in self.sources:
            if any(
                source.path.casefold() == d or source.path.casefold().startswith(d + "/")
                for d in (state, output)
            ):
                raise ValueError("Sources cannot be runtime state or output")
        return self


class ExternalBinding(Contract):
    root: str
    manifest_file: str
    manifest_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    spec: ExternalProjectSpec

    _path = field_validator("manifest_file")(relative_path)


class RunOptions(Contract):
    """Host resource limits/prices; manifest limits additionally apply. No path or mode override."""

    model: str = ""
    input_price: Decimal = Field(default=Decimal(0), ge=0, allow_inf_nan=False)
    output_price: Decimal = Field(default=Decimal(0), ge=0, allow_inf_nan=False)
    max_usd: Decimal = Field(default=Decimal("0.50"), ge=0, allow_inf_nan=False)
    daily_max_usd: Decimal = Field(default=Decimal("2.00"), gt=0, allow_inf_nan=False)
    max_calls: int = Field(default=6, ge=1, le=20)
    max_tokens: int = Field(default=80000, ge=1)
    max_output_tokens: int = Field(default=1600, ge=128, le=4096)
    max_input_bytes: int = Field(default=16000, ge=1024, le=64000)
    timeout_seconds: float = Field(default=45, gt=0, le=300, allow_inf_nan=False)
