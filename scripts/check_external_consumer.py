"""Offline wheel acceptance in a separate synthetic consumer; never authorizes real data."""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("wheel", type=Path)
args = parser.parse_args()
wheel = args.wheel.resolve(strict=True)
if wheel.is_dir():
    wheels = list(wheel.glob("porga-*.whl"))
    if len(wheels) != 1:
        raise ValueError("Choose exactly one locally built Porga wheel")
    wheel = wheels[0]
repo = Path(__file__).resolve().parents[1]
env = {k: v for k, v in os.environ.items() if k not in {"OPENAI_API_KEY", "PYTHONPATH"}}
env["OPENAI_AGENTS_DISABLE_TRACING"] = "1"

with tempfile.TemporaryDirectory(prefix="porga-consumer-") as temp:
    root = Path(temp)
    vendor = root / "installed"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--no-index",
            "--no-deps",
            "--target",
            str(vendor),
            str(wheel),
        ],
        env=env,
        capture_output=True,
        check=True,
    )
    project = root / "independent-project"
    shutil.copytree(repo / "examples/external-project", project)
    cwd = root / "unrelated-working-directory"
    cwd.mkdir()
    code = """
import asyncio, hashlib, importlib.metadata, json, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import porga
from porga.api import ProjectClient
assert Path(porga.__file__).is_relative_to(Path(sys.argv[1]))
assert importlib.metadata.version('porga') == porga.__version__
client=ProjectClient(sys.argv[2])
source=client.manifest.parent/'principles.txt'
before=hashlib.sha256(source.read_bytes()).hexdigest()
draft=client.attach()
assert not draft['authorized']
client.authorize(draft['digest'],actor='packaging-test',note='Synthetic packaging fixture only')
result=asyncio.run(client.run(request_key='wheel-acceptance'))
assert result['validation_passed'] and result['model_calls']==4 and result['estimated_usd']=='0'
report=client.export(result['run_id'])
assert Path(report['report']).is_file()
assert hashlib.sha256(source.read_bytes()).hexdigest()==before
client.accept(result['run_id'],actor='packaging-test',note='Synthetic fixture acceptance')
assert client.inspect_run(result['run_id'])['proposals'][0]['status']=='pending'
assert client.health()['ok']
assert not (Path.cwd()/'.porga').exists()
print(json.dumps({'wheel_import':True,'version':porga.__version__,'external_project':True,
                 'source_unchanged':True,'sdk_loop':'passed','calls':4,'usd':'0'}))
"""
    result = subprocess.run(
        [sys.executable, "-I", "-c", code, str(vendor), str(project / "porga.project.json")],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    )
    summary = json.loads(result.stdout)
    cli = (
        "import sys;sys.path.insert(0,sys.argv[1]);from porga.cli import main;"
        "raise SystemExit(main(sys.argv[2:]))"
    )
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-c",
            cli,
            str(vendor),
            "external",
            "inspect",
            "--manifest",
            str(project / "porga.project.json"),
        ],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    )
    assert json.loads(result.stdout)["status"] == "owner_accepted"
    summary["installed_cli"] = "passed"
    print(json.dumps(summary))
