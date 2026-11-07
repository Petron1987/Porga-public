"""Host-only bounded file adapter. Agents only see the approved evidence snapshot."""

import hashlib
import os
import stat
from pathlib import Path

from porga import __version__
from porga.core.store import canonical
from porga.integration_protocols import ExternalBinding, ExternalProjectSpec, relative_path


def sha(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def scoped_path(root: Path, relative: str) -> Path:
    relative = relative_path(relative)
    path = root
    for part in relative.split("/"):
        path = path / part
        try:
            info = path.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & getattr(
            stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400
        ):
            raise ValueError("Symlinks and junctions are outside the file adapter")
    if not path.resolve().is_relative_to(root):
        raise ValueError("Path escapes project root")
    return path


def read_bounded(path, limit):
    before = path.stat()
    if not stat.S_ISREG(before.st_mode):
        raise ValueError("Only regular files are supported")
    with path.open("rb") as handle:
        info = os.fstat(handle.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > limit or info.st_nlink > 1:
            raise ValueError("Only bounded regular files without hard links are supported")
        body = handle.read(limit + 1)
    if len(body) > limit:
        raise ValueError("File exceeds contract limit")
    return body


def load_manifest(path):
    path = Path(path).absolute()
    root = path.parent.resolve(strict=True)
    if root.is_relative_to(Path(__file__).resolve().parents[1]):
        raise ValueError("Consumer state cannot live inside the installed Porga package")
    file = scoped_path(root, path.name)
    spec = ExternalProjectSpec.model_validate_json(read_bounded(file, 65536).decode("utf-8-sig"))
    if spec.porga_version != __version__:
        raise ValueError("Installed Porga differs from the consumer's exact version pin")
    state, output = scoped_path(root, spec.state_dir), scoped_path(root, spec.output_dir)
    if any(p.exists() and not p.is_dir() for p in (state, output)):
        raise ValueError("State and output paths must be directories")
    if any(file.is_relative_to(p) or file == p for p in (state, output)):
        raise ValueError("Manifest cannot be runtime state or output")
    return root, spec, file


def prepare(path):
    from porga.project_protocols import CharterDraft

    root, spec, file = load_manifest(path)
    evidence = []
    for source in spec.sources:
        source_path = scoped_path(root, source.path)
        if any(
            source_path.is_relative_to(scoped_path(root, d))
            for d in (spec.state_dir, spec.output_dir)
        ):
            raise ValueError("Source resolves inside state/output")
        if source_path == file or source_path.suffix.lower() not in (".txt", ".md", ".json"):
            raise ValueError("Provide explicit UTF-8 text/Markdown/JSON evidence files")
        raw = read_bounded(source_path, 16000)
        if hashlib.sha256(raw).hexdigest() != source.sha256:
            raise ValueError("Source changed; review its digest and authorize a new revision")
        evidence.append({"id": source.id, "title": source.title, "text": raw.decode("utf-8-sig")})
    binding = ExternalBinding(
        root=str(root),
        manifest_file=file.name,
        manifest_sha256=sha(spec.model_dump(mode="json")),
        spec=spec,
    )
    return CharterDraft(
        schema_version="0.4",
        project={"goal": spec.goal, "evidence": evidence},
        deliverable=spec.deliverable,
        success_criteria=spec.success_criteria,
        non_goals=spec.non_goals,
        mode=spec.mode,
        max_usd=spec.max_usd,
        max_calls=spec.max_calls,
        data_scope=spec.classification,
        require_all_sources=spec.require_all_sources,
        external=binding,
    )


def verify_live(draft, data_dir):
    """Check at authorization/start/resume. Historical health checks use frozen snapshots only."""
    binding = draft.external
    if not binding:
        return
    root = Path(binding.root)
    if not root.is_absolute() or root.resolve(strict=True) != root:
        raise ValueError("Project root moved; explicit reattachment is required")
    if scoped_path(root, binding.spec.state_dir) != Path(data_dir).resolve():
        raise ValueError("External run is using another project's state directory")
    current = prepare(scoped_path(root, binding.manifest_file))
    if current != draft:
        raise ValueError("External contract or evidence changed; reattach and authorize")
