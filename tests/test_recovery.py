import asyncio
import json
import subprocess
import sys

import pytest

from porga.core.locking import StoreBusy
from porga.core.operations import cancel, recover
from porga.runtime import Runtime
from porga.workflow import execute, resume


class FailResearch(Runtime):
    def model(self, output, use_tool=False):
        model = super().model(output, use_tool)
        if use_tool:

            async def failure(*args, **kwargs):
                raise RuntimeError("synthetic failure after reservation")

            model.inner.get_response = failure
        return model


async def test_resume_reuses_completed_checkpoint_and_retains_failed_spend(
    project, settings, store
):
    with pytest.raises(RuntimeError):
        await execute(project, settings, store, runtime_class=FailResearch)
    with store.connect() as db:
        run_id = db.execute("SELECT id FROM runs").fetchone()[0]
        plan_id = db.execute("SELECT id FROM artifacts WHERE kind='plan'").fetchone()[0]
    r = await resume(run_id, store)
    assert r["validation_passed"] and r["model_calls"] == 5
    snapshot = store.snapshot(run_id)
    assert [a["id"] for a in snapshot["artifacts"] if a["kind"] == "plan"] == [plan_id]
    assert len([t for t in snapshot["tasks"] if t["role"] == "chief"]) == 1
    assert len([r for r in snapshot["reservations"] if r["status"] == "reserved"]) == 1


async def test_request_key_deduplicates_but_rejects_changed_input(project, settings, store):
    r = await execute(project, settings, store, request_key="user-job-1")
    assert await execute(project, settings, store, request_key="user-job-1") == r
    with pytest.raises(ValueError, match="different input"):
        await execute(
            project.model_copy(update={"goal": "different goal"}),
            settings,
            store,
            request_key="user-job-1",
        )
    with store.connect() as db:
        assert db.execute("SELECT count(*) FROM runs").fetchone()[0] == 1


def test_crashed_worker_releases_real_os_lock_and_recovers(project, settings, store):
    # This is a separate real process using os._exit, not an exception simulation.
    script = """
import os, sys
from pathlib import Path
from porga.core.store import Store
store = Store(Path(sys.argv[1]))
with store.exclusive():
    run_id = store.start({'goal':'synthetic crash','evidence':[]}, 'mock')
    store.task(run_id, 'chief')
    print(run_id, flush=True)
    os._exit(17)
"""
    process = subprocess.run(
        [sys.executable, "-c", script, str(settings.data_dir)],
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert process.returncode == 17
    run_id = process.stdout.strip()
    assert recover(store, run_id)["status"] == "interrupted"
    assert store.snapshot(run_id)["tasks"][0]["status"] == "failed"


def test_process_lock_prevents_second_worker(settings, store):
    script = """
import sys
from pathlib import Path
from porga.core.store import Store
from porga.core.locking import StoreBusy
try:
    with Store(Path(sys.argv[1])).exclusive():
        sys.exit(10)
except StoreBusy:
    sys.exit(0)
"""
    with store.exclusive():
        p = subprocess.run([sys.executable, "-c", script, str(settings.data_dir)], timeout=20)
    assert p.returncode == 0


async def test_busy_store_cannot_run_or_recover(project, settings, store):
    with store.exclusive(), pytest.raises(StoreBusy):
        await execute(project, settings, store)


async def test_online_resume_requires_explicit_replay_authorization(
    project, settings, store, monkeypatch
):
    with pytest.raises(RuntimeError):
        await execute(project, settings, store, runtime_class=FailResearch)
    with store.connect() as db:
        r = db.execute("SELECT * FROM runs").fetchone()
        config = json.loads(r["settings_json"])
        config.update(mode="openai", model="test", input_price="1", output_price="2")
        db.execute(
            "UPDATE runs SET mode='openai',settings_json=? WHERE id=?",
            (json.dumps(config), r["id"]),
        )
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-no-request")
    with pytest.raises(ValueError, match="allow-replay"):
        await resume(r["id"], store)


async def test_cooperative_cancellation_persists_settled_usage(project, settings, store):
    started = asyncio.Event()
    proceed = asyncio.Event()

    class SlowResearch(Runtime):
        def model(self, output, use_tool=False):
            model = super().model(output, use_tool)
            if use_tool:
                original = model.inner.get_response

                async def paused(*args, **kwargs):
                    started.set()
                    await proceed.wait()
                    return await original(*args, **kwargs)

                model.inner.get_response = paused
            return model

    task = asyncio.create_task(execute(project, settings, store, runtime_class=SlowResearch))
    await asyncio.wait_for(started.wait(), timeout=5)
    with store.connect() as db:
        run_id = db.execute("SELECT id FROM runs").fetchone()[0]
    assert cancel(store, run_id)["status"] == "cancel_requested"
    proceed.set()
    from porga.core.lifecycle import RunCancelled

    with pytest.raises(RunCancelled):
        await task
    snapshot = store.snapshot(run_id)
    assert snapshot["run"]["status"] == "cancelled"
    assert len(snapshot["reservations"]) == 2
    assert all(r["status"] == "settled" for r in snapshot["reservations"])
    with pytest.raises(ValueError):
        await resume(run_id, store)


async def test_checkpoint_tampering_blocks_resume(project, settings, store):
    with pytest.raises(RuntimeError):
        await execute(project, settings, store, runtime_class=FailResearch)
    with store.connect() as db:
        run_id = db.execute("SELECT id FROM runs").fetchone()[0]
        db.execute("UPDATE artifacts SET content='{}'")
    with pytest.raises(ValueError, match="tampered"):
        await resume(run_id, store)
