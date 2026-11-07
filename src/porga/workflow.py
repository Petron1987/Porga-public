"""Deterministic, checkpointed execution with explicit local recovery."""

import re

from porga.core.budget import Ledger
from porga.core.config import Settings
from porga.core.lifecycle import RunCancelled, ensure_running
from porga.core.operations import check_run, result
from porga.core.projects import run_context
from porga.core.store import canonical
from porga.core.verification import verify
from porga.evolution.proposals import suggest
from porga.organization.chief import create_chief
from porga.organization.factory import AgentFactory, PermissionDenied
from porga.organization.registry import organization, worker_for
from porga.protocols import AgentSpec, PermissionPolicy, Plan, ProjectSpec, QAReview, ResearchReport
from porga.runtime import Runtime


async def execute(
    project, settings, store, *, runtime_class=Runtime, request_key=None, charter_context=None
):
    settings.validate_online()
    if request_key is not None and not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", request_key):
        raise ValueError("Use a bounded alphanumeric request key")
    with store.exclusive():
        run_id = store.start(
            project.model_dump(mode="json"),
            settings.mode,
            settings.model_dump(mode="json"),
            request_key,
            charter_context,
        )
        with store.connect() as db:
            has_proposal = db.execute(
                "SELECT 1 FROM proposals WHERE run_id=?", (run_id,)
            ).fetchone()
            has_events = db.execute(
                "SELECT count(*) FROM events WHERE run_id=?", (run_id,)
            ).fetchone()[0]
        if has_proposal:
            return result(store, run_id)
        if has_events > 1:
            raise ValueError("Existing unfinished run: inspect, recover if abandoned, then resume")
        return await _drive(project, settings, store, run_id, runtime_class)


async def resume(run_id, store, *, allow_replay=False, runtime_class=Runtime):
    with store.exclusive(), store.connect() as db:
        check_run(db, run_id)
        row = db.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
        if row["status"] not in ("failed", "interrupted") or not row["settings_json"]:
            raise ValueError("Resume requires a failed/interrupted v0.2 run")
        settings = Settings.model_validate_json(row["settings_json"])
        context = run_context(store, run_id)
        if context and context[1].external:
            from porga.core.integration import verify_live

            verify_live(context[1], store.path.parent)
        settings.validate_online()
        incomplete = db.execute(
            "SELECT 1 FROM tasks WHERE run_id=? AND status!='completed'", (run_id,)
        ).fetchone()
        if settings.mode == "openai" and incomplete and not allow_replay:
            raise ValueError(
                "Online replay may incur additional cost; explicit allow-replay required"
            )
        project = ProjectSpec.model_validate_json(row["project"])
        db.execute("UPDATE runs SET status='running' WHERE id=?", (run_id,))
        store.event(db, run_id, "run_resumed", {"allow_replay": allow_replay})
        db.commit()
        # Keep the OS lock for the entire asynchronous workflow, not the DB transaction.
        return await _drive(project, settings, store, run_id, runtime_class)


async def _drive(project, settings, store, run_id, runtime_class):
    runtime = None
    try:
        ledger = Ledger(settings, store, run_id)
        runtime = runtime_class(settings, ledger)
        context = run_context(store, run_id)
        worker = worker_for(context[1].deliverable) if context else "research"
        owner_scope = (
            {
                "success_criteria": context[1].success_criteria,
                "non_goals": context[1].non_goals,
                "deliverable": context[1].deliverable,
            }
            if context
            else {}
        )

        async def stage(role, kind, output_type, build_agent, payload, turns=1):
            with store.connect() as db:
                ensure_running(db, run_id)
                saved = db.execute(
                    "SELECT a.content FROM tasks t JOIN artifacts a "
                    "ON a.id=t.artifact_id WHERE t.run_id=? AND t.role=? "
                    "AND t.status='completed'",
                    (run_id, role),
                ).fetchone()
            if saved:
                return output_type.model_validate_json(saved[0])
            task = store.task(run_id, role)
            output = await runtime.run(build_agent(), payload, turns=turns)
            store.complete_task(run_id, task, kind, output.model_dump(mode="json"))
            return output

        plan = await stage(
            "chief",
            "plan",
            Plan,
            lambda: create_chief(runtime, project.goal, worker),
            {"goal": project.goal, "owner_scope": owner_scope},
        )
        if plan.roles != [worker, "qa"]:
            raise PermissionDenied("Team differs from the authorized task profile")
        if context:
            binding, draft = context
            manifest = organization(
                binding["project_id"], binding["revision"], draft, plan.roles, PermissionPolicy()
            )
            from porga.core.projects import digest

            body = manifest.model_dump(mode="json")
            with store.connect() as db:
                saved = db.execute(
                    "SELECT * FROM run_organizations WHERE run_id=?", (run_id,)
                ).fetchone()
                if saved and saved["sha256"] != digest(body):
                    raise ValueError("Organization differs from the run's pinned revision")
                if not saved:
                    db.execute(
                        "INSERT INTO run_organizations VALUES(?,?,?)",
                        (run_id, canonical(body), digest(body)),
                    )
        factory = AgentFactory(PermissionPolicy(), project, runtime, store, run_id)
        report = await stage(
            worker,
            worker,
            ResearchReport,
            lambda: factory.create(
                AgentSpec(
                    role=worker,
                    capabilities=("read_evidence",),
                    version="0.3" if context else "0.1",
                ),
                {
                    "summary": (
                        "Evidence coverage audit; external accuracy remains unverified."
                        if worker == "evidence_auditor"
                        else "Evidence-bounded research; no external market claims verified."
                    ),
                    "findings": [
                        {"evidence_id": e.id, "quote": e.text[:500]} for e in project.evidence
                    ],
                    "uncertainties": ["Source freshness and broader applicability are unverified."],
                },
            ),
            {"question": plan.research_question, "owner_scope": owner_scope},
            turns=2,
        )
        qa = await stage(
            "qa",
            "qa",
            QAReview,
            lambda: factory.create(
                AgentSpec(role="qa", version="0.3" if context else "0.1"),
                {"passed": True, "issues": []},
            ),
            {
                "report": report.model_dump(mode="json"),
                "evidence": [e.model_dump() for e in project.evidence],
                "owner_scope": owner_scope,
            },
        )
        gate = verify(
            project,
            report,
            qa,
            require_all_sources=bool(
                context
                and (context[1].require_all_sources or context[1].deliverable == "evidence_audit")
            ),
        )
        change, rationale = suggest(gate)
        store.finish(run_id, gate.model_dump(mode="json"), change, rationale)
        return result(store, run_id)
    except BaseException as exc:
        status = store.fail(run_id, type(exc).__name__)
        if status == "cancelled" and not isinstance(exc, RunCancelled):
            raise RunCancelled("Cancelled by operator") from exc
        raise
    finally:
        if runtime:
            await runtime.close()
