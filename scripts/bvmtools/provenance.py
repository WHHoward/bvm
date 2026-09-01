"""Shared provenance helpers for future JoSIM experiments."""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path
from typing import Iterable


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def file_snapshot(path: str | Path, *, relative_to: str | Path | None = None) -> dict[str, object]:
    file_path = Path(path)
    record: dict[str, object] = {
        "path": str(file_path),
        "sha256": sha256_file(file_path),
        "bytes": file_path.stat().st_size,
    }
    if relative_to is not None:
        try:
            record["relative_path"] = file_path.resolve().relative_to(Path(relative_to).resolve()).as_posix()
        except ValueError:
            record["relative_path"] = None
    return record


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()


def git_snapshot(repo: str | Path = ".") -> dict[str, object]:
    repo_path = Path(repo).resolve()
    status = _git(repo_path, "status", "--short", "--untracked-files=all")
    return {
        "repo": str(repo_path),
        "head": _git(repo_path, "rev-parse", "HEAD"),
        "dirty": bool(status),
        "status_porcelain": status,
    }


def solver_provenance(
    solver: str | Path,
    *,
    cwd: str | Path | None = None,
) -> dict[str, object]:
    solver_path = Path(solver).resolve()
    record: dict[str, object] = {
        "path": str(solver_path),
        "exists": solver_path.is_file(),
    }
    if not solver_path.is_file():
        return record
    record["sha256"] = sha256_file(solver_path)
    version = subprocess.run(
        [str(solver_path), "--version"],
        cwd=Path(cwd).resolve() if cwd is not None else None,
        check=False,
        capture_output=True,
        text=True,
    )
    record["version_returncode"] = version.returncode
    record["version_stdout"] = version.stdout.strip()
    record["version_stderr"] = version.stderr.strip()
    return record


def snapshot_inputs(
    paths: Iterable[str | Path], *, relative_to: str | Path | None = None
) -> list[dict[str, object]]:
    return [file_snapshot(path, relative_to=relative_to) for path in paths]
