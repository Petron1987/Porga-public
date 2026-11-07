import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

from pydantic import ValidationError

from porga.core import operations, projects
from porga.core.config import Settings, load_env
from porga.core.locking import StoreBusy
from porga.core.store import Store
from porga.project_protocols import CharterDraft
from porga.protocols import ProjectSpec
from porga.workflow import execute, resume

DEMO = {
    "goal": "Summarize Porga's approved operating principles with traceable evidence.",
    "evidence": [
        {
            "id": "charter",
            "title": "Porga operating principles (synthetic demo)",
            "text": "Porga creates bounded teams, verifies artifacts, and requires human approval "
            "for evolution decisions.",
        },
        {
            "id": "governance",
            "title": "Porga governance (synthetic demo)",
            "text": "Research agents may read the approved evidence bundle. They may not execute "
            "shell commands, publish externally, or approve their own proposals.",
        },
    ],
}


def parser():
    p = argparse.ArgumentParser(description="Porga local governed organization kernel")
    p.add_argument("--data-dir", type=Path, help="Local state directory (default .porga)")
    sub = p.add_subparsers(dest="command", required=True)
    for command in ("demo", "run"):
        c = sub.add_parser(command)
        c.add_argument("--mode", choices=["mock", "openai"], default=None)
        c.add_argument("--request-key", help="Reuse the same result for identical input/config")
        if command == "run":
            c.add_argument("--project", type=Path, required=True)
    show = sub.add_parser("inspect")
    show.add_argument("run_id")
    for command in ("approve", "reject"):
        c = sub.add_parser(command, help="Record a human decision; never deploys changes")
        c.add_argument("proposal_id")
        c.add_argument("--actor", required=True)
        c.add_argument("--note", required=True)
        c.add_argument("--confirm", action="store_true", help="Explicit human confirmation")
    sub.add_parser("status")
    sub.add_parser("doctor")
    for command in ("report", "recover", "cancel"):
        c = sub.add_parser(command)
        c.add_argument("run_id")
    c = sub.add_parser("resume")
    c.add_argument("run_id")
    c.add_argument(
        "--allow-replay",
        action="store_true",
        help="Human authorization to repeat an incomplete online step; may cost more",
    )
    sub.add_parser("health")
    sub.add_parser("backup")
    c = sub.add_parser("restore")
    c.add_argument("backup", type=Path)
    sub.add_parser("evaluate")
    sub.add_parser("readiness")
    project = sub.add_parser("project", help="Owner intake, authorization and final acceptance")
    actions = project.add_subparsers(dest="project_action", required=True)
    c = actions.add_parser("draft")
    source = c.add_mutually_exclusive_group(required=True)
    source.add_argument("--goal", help="Start a draft; missing critical answers are returned")
    source.add_argument("--spec", type=Path, help="Reviewed charter JSON")
    for action in ("inspect", "revise", "authorize", "run", "accept"):
        c = actions.add_parser(action)
        c.add_argument("project_id")
        if action == "revise":
            c.add_argument("--spec", type=Path, required=True)
        if action in ("authorize", "accept"):
            c.add_argument("--actor", required=True)
            c.add_argument("--note", required=True)
            c.add_argument("--confirm", action="store_true")
        if action == "authorize":
            c.add_argument("--digest", required=True, help="Digest returned by project inspect")
            c.add_argument("--allow-openai", action="store_true")
        if action == "accept":
            c.add_argument("--run-id", required=True)
        if action == "run":
            c.add_argument("--mode", choices=["mock", "openai"], default=None)
            c.add_argument("--request-key")
    actions.add_parser("registry", help="List code-reviewed roles and capabilities")
    ext = sub.add_parser("external", help="Use Porga from an independent consuming project")
    actions = ext.add_subparsers(dest="external_action", required=True)
    for action in (
        "preview",
        "attach",
        "inspect",
        "authorize",
        "run",
        "report",
        "accept",
        "resume",
        "cancel",
        "recover",
        "health",
        "backup",
    ):
        c = actions.add_parser(action)
        c.add_argument("--manifest", type=Path, required=True)
        if action in ("authorize", "accept"):
            c.add_argument("--actor", required=True)
            c.add_argument("--note", required=True)
            c.add_argument("--confirm", action="store_true")
        if action == "authorize":
            c.add_argument("--digest", required=True)
            c.add_argument("--allow-openai", action="store_true")
        if action in ("report", "accept", "resume", "cancel", "recover"):
            c.add_argument("run_id")
        if action == "resume":
            c.add_argument("--allow-replay", action="store_true")
        if action == "run":
            c.add_argument("--request-key")
    return p


def project_command(args, store, settings):
    action = args.project_action
    if action == "registry":
        from porga.organization.registry import CAPABILITIES, definitions

        return {
            "agents": [d.model_dump(mode="json") for d in definitions()],
            "capabilities": [c.model_dump(mode="json") for c in CAPABILITIES],
        }
    if action in ("draft", "revise"):
        data = (
            json.loads(args.spec.read_text(encoding="utf-8-sig"))
            if args.spec
            else {"project": {"goal": args.goal}}
        )
        draft = CharterDraft.model_validate(data)
        return (
            projects.create(store, draft)
            if action == "draft"
            else projects.revise(store, args.project_id, draft)
        )
    if action == "inspect":
        return projects.inspect(store, args.project_id)
    if action == "run":
        return asyncio.run(
            projects.execute_project(store, args.project_id, settings, request_key=args.request_key)
        )
    if not args.confirm:
        raise ValueError("Review the charter/outcome and pass explicit --confirm")
    if action == "authorize":
        return projects.authorize(
            store,
            args.project_id,
            args.digest,
            args.actor,
            args.note,
            allow_openai=args.allow_openai,
        )
    return projects.accept(store, args.project_id, args.run_id, args.actor, args.note)


def external_command(args):
    from porga.api import ProjectClient, RunOptions

    client = ProjectClient(args.manifest)
    action = args.external_action
    if action in ("authorize", "accept") and not args.confirm:
        raise ValueError("Owner review and explicit --confirm are required")
    if action == "authorize":
        return client.authorize(
            args.digest, actor=args.actor, note=args.note, allow_openai=args.allow_openai
        )
    if action == "accept":
        return client.accept(args.run_id, actor=args.actor, note=args.note)
    if action == "run":
        # External commands never implicitly read the caller's .env or use PORGA_DATA_DIR.
        values = Settings.from_env(mode="mock", data_dir=Path(".")).model_dump(
            exclude={"mode", "data_dir"}
        )
        return asyncio.run(
            client.run(options=RunOptions.model_validate(values), request_key=args.request_key)
        )
    if action == "resume":
        return asyncio.run(client.resume(args.run_id, allow_replay=args.allow_replay))
    if action in ("report", "cancel", "recover"):
        return getattr(client, "export" if action == "report" else action)(args.run_id)
    return getattr(client, action)()


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.command == "external":
            if args.data_dir is not None:
                raise ValueError("External state is defined by the manifest, not --data-dir")
            result = external_command(args)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 2 if result.get("validation_passed") is False else 0
        load_env()
        if args.command in ("demo", "run", "doctor", "readiness") or (
            args.command == "project" and args.project_action == "run"
        ):
            settings = Settings.from_env(mode=getattr(args, "mode", None), data_dir=args.data_dir)
        else:
            # Inspection/recovery must still work when live model configuration is broken.
            settings = Settings(data_dir=args.data_dir or os.getenv("PORGA_DATA_DIR", ".porga"))
        if args.command == "doctor":
            import importlib.metadata

            result = {
                "python": sys.version.split()[0],
                "agents_sdk": importlib.metadata.version("openai-agents"),
                "mode": settings.mode,
                "data_dir": str(settings.data_dir.resolve()),
                "api_key_present": bool(os.environ.get("OPENAI_API_KEY")),
                "tracing": "disabled",
            }
        else:
            store = Store(settings.data_dir)
            if args.command == "project":
                result = project_command(args, store, settings)
                print(json.dumps(result, ensure_ascii=False, indent=2))
                return 2 if result.get("validation_passed") is False else 0
            elif args.command in ("demo", "run"):
                data = (
                    DEMO
                    if args.command == "demo"
                    else json.loads(args.project.read_text(encoding="utf-8-sig"))
                )
                project = ProjectSpec.model_validate(data)
                result = asyncio.run(
                    execute(project, settings, store, request_key=args.request_key)
                )
                print(json.dumps(result, ensure_ascii=False, indent=2))
                return 0 if result["validation_passed"] else 2
            elif args.command == "inspect":
                result = store.snapshot(args.run_id)
            elif args.command == "resume":
                result = asyncio.run(resume(args.run_id, store, allow_replay=args.allow_replay))
                print(json.dumps(result, ensure_ascii=False, indent=2))
                return 0 if result["validation_passed"] else 2
            elif args.command == "health":
                result = operations.health(store)
                print(json.dumps(result, ensure_ascii=False, indent=2))
                return 0 if result["ok"] else 2
            elif args.command == "backup":
                result = operations.backup(store)
            elif args.command == "restore":
                result = operations.restore(store, args.backup)
            elif args.command == "report":
                result = operations.export_report(store, args.run_id)
            elif args.command == "recover":
                result = operations.recover(store, args.run_id)
            elif args.command == "cancel":
                result = operations.cancel(store, args.run_id)
            elif args.command == "evaluate":
                from porga.evolution.evaluation import evaluate

                result = evaluate()
                print(json.dumps(result, ensure_ascii=False, indent=2))
                return 0 if result["passed"] else 2
            elif args.command == "readiness":
                result = operations.readiness(store, settings)
            elif args.command == "status":
                with store.connect() as db:
                    result = {
                        "runs": [
                            dict(r)
                            for r in db.execute(
                                "SELECT id,mode,status,created_at FROM runs "
                                "ORDER BY created_at DESC"
                            )
                        ],
                        "proposals": [
                            dict(r)
                            for r in db.execute("SELECT id,run_id,status,deployment FROM proposals")
                        ],
                        "projects": [
                            dict(r)
                            for r in db.execute(
                                "SELECT p.id,p.active_revision,max(c.revision) AS latest_revision "
                                "FROM projects p JOIN charters c ON c.project_id=p.id GROUP BY p.id"
                            )
                        ],
                    }
            else:
                if not args.confirm:
                    raise ValueError("Human decision requires --confirm after reviewing inspect")
                result = {
                    "proposal_id": args.proposal_id,
                    "status": store.decide(
                        args.proposal_id, args.command == "approve", args.actor, args.note
                    ),
                    "deployment": "not_applied",
                }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except StoreBusy:
        print("Porga is busy in another process. Retry after that task exits.", file=sys.stderr)
        return 3
    except (ValidationError, ValueError):
        # Avoid Pydantic's raw input echo: configuration and project fields may hold secrets.
        print(
            "Invalid input or decision. Check schema, configuration, and proposal state.",
            file=sys.stderr,
        )
        return 2
    except (Exception, KeyboardInterrupt) as exc:
        print(f"Run stopped ({type(exc).__name__}); inspect local audit state.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
