import socket

import pytest

from porga.cli import DEMO
from porga.core.config import Settings
from porga.core.store import Store
from porga.protocols import ProjectSpec


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    original_connect = socket.socket.connect
    original_pair = socket.socketpair

    def deny(*args, **kwargs):
        raise AssertionError("Network is forbidden in offline tests")

    def local_pair(*args, **kwargs):
        # Windows implements socketpair with loopback TCP for asyncio's internal pipe.
        # Permit only that synchronous stdlib operation, not arbitrary model connections.
        with monkeypatch.context() as local:
            local.setattr(socket.socket, "connect", original_connect)
            return original_pair(*args, **kwargs)

    monkeypatch.setattr(socket.socket, "connect", deny)
    monkeypatch.setattr(socket.socket, "connect_ex", deny)
    monkeypatch.setattr(socket, "create_connection", deny)
    monkeypatch.setattr(socket, "socketpair", local_pair)
    monkeypatch.setenv("OPENAI_AGENTS_DISABLE_TRACING", "1")


@pytest.fixture
def project():
    return ProjectSpec.model_validate(DEMO)


@pytest.fixture
def settings(tmp_path):
    return Settings(data_dir=tmp_path)


@pytest.fixture
def store(tmp_path):
    return Store(tmp_path)
