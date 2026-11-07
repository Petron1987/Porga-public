"""Explicit online opt-in; offline ignores all API credentials."""

import os
from decimal import Decimal
from pathlib import Path
from typing import Literal

from pydantic import Field

from porga.protocols import Contract


class Settings(Contract):
    mode: Literal["mock", "openai"] = "mock"
    data_dir: Path = Path(".porga")
    model: str = ""
    input_price: Decimal = Field(default=Decimal("0"), ge=0, allow_inf_nan=False)
    output_price: Decimal = Field(default=Decimal("0"), ge=0, allow_inf_nan=False)
    max_usd: Decimal = Field(default=Decimal("0.50"), ge=0, allow_inf_nan=False)
    daily_max_usd: Decimal = Field(default=Decimal("2.00"), gt=0, allow_inf_nan=False)
    max_calls: int = Field(default=6, ge=1, le=20)
    max_tokens: int = Field(default=80000, ge=1)
    max_output_tokens: int = Field(default=1600, ge=128, le=4096)
    max_input_bytes: int = Field(default=16000, ge=1024, le=64000)
    timeout_seconds: float = Field(default=45, gt=0, le=300, allow_inf_nan=False)

    def validate_online(self):
        if self.mode == "openai":
            if not os.environ.get("OPENAI_API_KEY"):
                raise ValueError("Online mode requires OPENAI_API_KEY")
            if (
                not self.model
                or self.input_price <= 0
                or self.output_price <= 0
                or self.max_usd <= 0
            ):
                raise ValueError("Online mode requires model, positive prices and budget")

    @classmethod
    def from_env(cls, mode=None, data_dir=None):
        names = {
            "model": "PORGA_MODEL",
            "input_price": "PORGA_INPUT_USD_PER_MILLION",
            "output_price": "PORGA_OUTPUT_USD_PER_MILLION",
            "max_usd": "PORGA_MAX_USD",
            "daily_max_usd": "PORGA_DAILY_MAX_USD",
            "max_calls": "PORGA_MAX_CALLS",
            "max_tokens": "PORGA_MAX_TOKENS",
            "max_output_tokens": "PORGA_MAX_OUTPUT_TOKENS",
            "max_input_bytes": "PORGA_MAX_INPUT_BYTES",
            "timeout_seconds": "PORGA_TIMEOUT_SECONDS",
        }
        values = {k: os.environ[v] for k, v in names.items() if os.environ.get(v)}
        return cls(
            **values,
            mode=mode or os.getenv("PORGA_MODE", "mock"),
            data_dir=data_dir or os.getenv("PORGA_DATA_DIR", ".porga"),
        )


def load_env(path: Path = Path(".env")):
    """Small literal dotenv subset: NAME=value, no shell interpolation/execution."""
    if not path.exists():
        return
    allowed = {"OPENAI_API_KEY", "OPENAI_AGENTS_DISABLE_TRACING"}
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, value = line.partition("=")
        key = key.strip()
        if sep and (key.startswith("PORGA_") or key in allowed):
            os.environ.setdefault(key, value.strip().strip("\"'"))
