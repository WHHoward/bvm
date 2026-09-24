#!/usr/bin/env python3
"""Immutable FULL/DELTA package planning and creation for this series."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any

SERIES = Path(__file__).resolve().parents[1]
REPO = next(path for path in (SERIES, *SERIES.parents) if (path / ".git").exists())
CHECKPOINTS = SERIES / "analysis" / "PACKAGE_CHECKPOINTS.json"
PACKAGE_QA = SERIES / "analysis" / "PACKAGE_QA.json"
MIRROR = Path("/mnt/d/BVM_Backages")
TAG_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")


def sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO.resolve()).as_posix()


def git(*args: str, check: bool = True) -> str:
    result = subprocess.run(["git", *args], cwd=REPO, check=check,
                            capture_output=True, text=True)
    return result.stdout.strip()


def head_commit() -> str:
    return git("rev-parse", "HEAD")


def excluded(path: Path) -> bool:
    relative = path.relative_to(SERIES)
    return (
        "__pycache__" in relative.parts
        or path.suffix == ".pyc"
        or path.name == "PACKAGE_QA.json"
        or (path.parent.name == "handoff" and path.suffix.lower() == ".zip")
    )


def checkpoint_entries() -> list[dict[str, Any]]:
    if not CHECKPOINTS.is_file():
        raise RuntimeError(f"checkpoint registry missing: {CHECKPOINTS}")
    content = json.loads(CHECKPOINTS.read_text(encoding="utf-8"))
    return list(content.get("checkpoints", []))


def _verified_entry(entry: dict[str, Any]) -> bool:
    try:
        path = (REPO / entry["package_path"]).resolve()
        path.relative_to(SERIES.resolve())
        commit = str(entry["head_commit"])
        package_type = str(entry["package_type"])
        package_sha = str(entry["package_sha256"])
    except (KeyError, ValueError):
        return False
    if package_type not in {"full", "delta"} or not path.is_file():
        return False
    if not re.fullmatch(r"[0-9a-f]{40}", commit) or not re.fullmatch(r"[0-9a-f]{64}", package_sha):
        return False
    commit_exists = subprocess.run(
        ["git", "cat-file", "-e", f"{commit}^{{commit}}"], cwd=REPO,
        capture_output=True, check=False,
    ).returncode == 0
    if not commit_exists:
        return False
    return sha256(path) == package_sha


def select_base(explicit: str | None, current_head: str) -> dict[str, Any]:
    entries = checkpoint_entries()
    if explicit:
        matches = [entry for entry in entries if entry.get("head_commit") == explicit]
        if not matches:
            raise RuntimeError("explicit base commit is not registered in PACKAGE_CHECKPOINTS.json")
        candidates = matches
    else:
        candidates = entries
    valid = [entry for entry in candidates if _verified_entry(entry)]
    if not valid:
        raise RuntimeError("no verified package checkpoint is available as DELTA base")
    base = valid[-1]
    commit = str(base["head_commit"])
    if subprocess.run(
        ["git", "merge-base", "--is-ancestor", commit, current_head], cwd=REPO,
        capture_output=True, check=False,
    ).returncode != 0:
        raise RuntimeError(f"DELTA base is not an ancestor of HEAD: {commit}")
    return {
        "base_package_name": base["package_name"],
        "base_package_path": base["package_path"],
        "base_package_sha256": base["package_sha256"],
        "base_commit": commit,
    }


def worktree_changes() -> dict[str, str]:
    raw = git("status", "--short", "--untracked-files=all", "--", rel(SERIES))
    changed: dict[str, str] = {}
    for line in raw.splitlines():
        if len(line) < 4:
            continue
        status = line[:2].strip() or "?"
        changed[line[3:]] = status[0]
    return changed


def committed_changes(base: str, head: str) -> dict[str, str]:
    raw = git("diff", "--name-status", base, head, "--", rel(SERIES))
    result: dict[str, str] = {}
    for line in raw.splitlines():
        if not line.strip():
            continue
        status, path = line.split("\t", 1)
        result[path] = status[0]
    return result


def changed_files(base: str | None, head: str) -> tuple[list[Path], dict[str, str]]:
    if base:
        statuses = committed_changes(base, head)
    else:
        statuses = {}
    statuses.update(worktree_changes())
    paths = []
    for relative in statuses:
        path = REPO / relative
        if path.is_file() and not excluded(path):
            paths.append(path)
    return sorted(set(paths)), statuses


def all_full_files() -> list[Path]:
    return [path for path in sorted(SERIES.rglob("*"))
            if path.is_file() and not excluded(path)]


def hash_map(files: list[Path]) -> dict[str, str]:
    return {rel(path): sha256(path) for path in files}


def _exists_at_commit(commit: str, path: Path) -> bool:
    return subprocess.run(
        ["git", "cat-file", "-e", f"{commit}:{rel(path)}"], cwd=REPO,
        capture_output=True, check=False,
    ).returncode == 0


def _new_solve_count(result: dict[str, Any], existed_at_base: bool) -> int:
    return 0 if existed_at_base else int(result.get("physical_solve_count", 0))


def _run_counts(files: list[Path], base_commit: str | None) -> tuple[int, int]:
    solves = reused = 0
    for path in files:
        if path.name != "result.json":
            continue
        existed_at_base = base_commit is not None and _exists_at_commit(base_commit, path)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        solves += _new_solve_count(data, existed_at_base)
        reused += int(data.get("reused_point_count", 0))
    return solves, reused


def _existing_references(files: list[Path]) -> list[dict[str, Any]]:
    references: list[dict[str, Any]] = []
    for path in files:
        if path.suffix != ".json":
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        for item in data.get("referenced_existing_cases", []):
            if isinstance(item, dict) and item.get("raw_path") and item.get("raw_sha256"):
                references.append(item)
    unique = {(item.get("source_case"), item.get("raw_path"), item.get("raw_sha256")): item
              for item in references}
    return [unique[key] for key in sorted(unique, key=lambda value: tuple(str(part) for part in value))]


def package_manifest(mode: str, tag: str, head: str, files: list[Path],
                     base: dict[str, Any] | None, statuses: dict[str, str]) -> dict[str, Any]:
    hashes = hash_map(files)
    new_files: list[str] = []
    modified_files: list[str] = []
    if base:
        for path in files:
            relative = rel(path)
            exists = subprocess.run(
                ["git", "cat-file", "-e", f"{base['base_commit']}:{relative}"],
                cwd=REPO, capture_output=True, check=False,
            ).returncode == 0
            (modified_files if exists else new_files).append(relative)
    solves, reused = _run_counts(files, base["base_commit"] if base else None)
    manifest: dict[str, Any] = {
        "schema": "bvm-qb-cb-array-package-manifest-v1",
        "package_type": mode,
        "tag": tag,
        "head_commit": head,
        "included_files": [rel(path) for path in files],
        "included_file_sha256": hashes,
        "new_files": sorted(new_files),
        "modified_files": sorted(modified_files),
        "new_physical_solve_count": solves,
        "reused_point_count": reused,
        "referenced_existing_cases": _existing_references(files),
        "scientific_interpretation_performed": False,
    }
    if base:
        manifest.update(base)
    return manifest


def build_plan(mode: str, tag: str, base_commit: str | None = None) -> dict[str, Any]:
    if mode not in {"full", "delta"}:
        raise RuntimeError(f"unsupported package mode: {mode}")
    if not TAG_RE.fullmatch(tag):
        raise RuntimeError(f"invalid package tag: {tag!r}")
    head = head_commit()
    base = select_base(base_commit, head) if mode == "delta" else None
    if mode == "full":
        files = all_full_files()
        statuses: dict[str, str] = {}
        package_manifest_path = "FULL_MANIFEST.json"
    else:
        assert base is not None
        files, statuses = changed_files(base["base_commit"], head)
        package_manifest_path = "DELTA_MANIFEST.json"
    manifest = package_manifest(mode, tag, head, files, base, statuses)
    package_name = f"{SERIES.name}_{mode}_{tag}.zip"
    package_path = SERIES / "handoff" / package_name
    mirror_path = MIRROR / package_name
    if package_path.exists():
        raise RuntimeError(f"refusing to overwrite package: {package_path}")
    if mirror_path.exists():
        raise RuntimeError(f"refusing to overwrite mirror target: {mirror_path}")
    dirty_paths = [path for path in worktree_changes()
                   if not excluded(REPO / path)]
    return {
        "mode": mode, "tag": tag, "head_commit": head,
        "base": base, "files": files, "statuses": statuses,
        "dirty_source_paths": dirty_paths,
        "manifest": manifest, "manifest_path": package_manifest_path,
        "package_path": package_path, "mirror_path": mirror_path,
        "estimated_uncompressed_bytes": sum(path.stat().st_size for path in files),
    }


def print_plan(plan: dict[str, Any]) -> None:
    manifest = plan["manifest"]
    print(json.dumps({
        "status": "PACKAGE_DRY_RUN_PASS",
        "mode": plan["mode"], "tag": plan["tag"],
        "head_commit": plan["head_commit"],
        "base": plan["base"],
        "new_files": manifest["new_files"],
        "modified_files": manifest["modified_files"],
        "included_file_count": len(plan["files"]),
        "estimated_uncompressed_bytes": plan["estimated_uncompressed_bytes"],
        "package_path": rel(plan["package_path"]),
        "mirror_path": str(plan["mirror_path"]),
        "new_physical_solve_count": manifest["new_physical_solve_count"],
        "reused_point_count": manifest["reused_point_count"],
        "dirty_source_paths": plan["dirty_source_paths"],
        "archive_created": False,
        "mirror_created": False,
    }, ensure_ascii=False, indent=2))


def create_package(plan: dict[str, Any]) -> dict[str, Any]:
    if plan["dirty_source_paths"]:
        raise RuntimeError("commit source/evidence before packaging; dirty paths: "
                           + ", ".join(plan["dirty_source_paths"]))
    package_path: Path = plan["package_path"]
    mirror_path: Path = plan["mirror_path"]
    if package_path.exists() or mirror_path.exists():
        raise RuntimeError("package or mirror target appeared after planning; refusing overwrite")
    mirror_dir = mirror_path.parent
    if not mirror_dir.is_dir():
        raise RuntimeError(f"Drive mirror directory is not accessible: {mirror_dir}")
    package_path.parent.mkdir(parents=True, exist_ok=True)

    manifest_name = plan["manifest_path"]
    manifest_bytes = (json.dumps(plan["manifest"], ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()
    expected = dict(plan["manifest"]["included_file_sha256"])
    expected[manifest_name] = hashlib.sha256(manifest_bytes).hexdigest()
    temp_path: Path | None = None
    with tempfile.NamedTemporaryFile(prefix=f".{package_path.stem}.", suffix=".tmp",
                                     dir=package_path.parent, delete=False) as stream:
        temp_path = Path(stream.name)
    try:
        with zipfile.ZipFile(temp_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            for path in plan["files"]:
                archive.write(path, rel(path))
            archive.writestr(manifest_name, manifest_bytes)
        with zipfile.ZipFile(temp_path, "r") as archive:
            if archive.testzip() is not None:
                raise RuntimeError("created archive failed ZIP CRC validation")
            if set(archive.namelist()) != set(expected):
                raise RuntimeError("created archive member list differs from package manifest")
            for member, digest in expected.items():
                if hashlib.sha256(archive.read(member)).hexdigest() != digest:
                    raise RuntimeError(f"archive member hash mismatch: {member}")
        os.link(temp_path, package_path)
    finally:
        if temp_path:
            temp_path.unlink(missing_ok=True)

    package_sha = sha256(package_path)
    shutil.copyfile(package_path, mirror_path)
    mirror_sha = sha256(mirror_path)
    qa = {
        "schema": "bvm-qb-cb-array-package-qa-v1",
        "status": "PASS" if package_sha == mirror_sha else "FAIL",
        "package_type": plan["mode"], "package_name": package_path.name,
        "package_path": rel(package_path), "package_sha256": package_sha,
        "package_bytes": package_path.stat().st_size,
        "mirror_path": str(mirror_path), "mirror_sha256": mirror_sha,
        "mirror_bytes": mirror_path.stat().st_size,
        "head_commit": plan["head_commit"],
        "included_file_sha256": expected,
        "zip_crc_pass": True, "member_sha256_pass": True,
        "scientific_interpretation_performed": False,
    }
    if plan["base"]:
        qa.update(plan["base"])
    qa["new_physical_solve_count"] = plan["manifest"]["new_physical_solve_count"]
    qa["reused_point_count"] = plan["manifest"]["reused_point_count"]
    qa["referenced_existing_cases"] = plan["manifest"]["referenced_existing_cases"]
    PACKAGE_QA.write_text(json.dumps(qa, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                          encoding="utf-8")
    return qa


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create an immutable FULL or DELTA evidence package")
    parser.add_argument("--mode", choices=("full", "delta"), default="delta")
    parser.add_argument("--tag", required=True)
    parser.add_argument("--base-commit")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    try:
        plan = build_plan(args.mode, args.tag, args.base_commit)
        if args.dry_run:
            print_plan(plan)
            return 0
        qa = create_package(plan)
        print(json.dumps(qa, ensure_ascii=False, indent=2))
        return 0 if qa["status"] == "PASS" else 2
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
