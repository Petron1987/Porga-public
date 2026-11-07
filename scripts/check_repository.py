"""Small staged/tracked publication guard; never echoes suspected secret values."""

import re
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parents[1]
names = subprocess.check_output(["git", "ls-files", "-z"], cwd=root).decode().split("\0")
secret_patterns = [
    rb"sk-[A-Za-z0-9_-]{20,}",
    rb"gh[pousr]_[A-Za-z0-9]{20,}",
    rb"github_pat_[A-Za-z0-9_]{20,}",
    rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
]
blocked = []
for name in filter(None, names):
    path = Path(name)
    if (
        path.name.startswith(".env")
        and path.name != ".env.example"
        or any(
            part in {".venv", ".porga", "porga-results", "__pycache__", "runtime", "artifacts"}
            or part.startswith(".porga-")
            for part in path.parts
        )
        or path.suffix in {".db", ".sqlite3", ".key", ".pem", ".log"}
    ):
        blocked.append(name)
        continue
    content = subprocess.check_output(["git", "show", f":{name}"], cwd=root)
    if any(re.search(pattern, content) for pattern in secret_patterns):
        blocked.append(name)
if blocked:
    raise SystemExit("Publication guard failed; review filenames: " + ", ".join(blocked))
print(f"Publication guard passed: {len(list(filter(None, names)))} indexed files")
