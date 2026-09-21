#!/usr/bin/env python3
"""Evidence packaging with explicit immutable FULL and traceable DELTA modes."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

SERIES = Path(__file__).resolve().parents[1]
REPO = next(path for path in (SERIES, *SERIES.parents) if (path / ".git").exists())
CHECKPOINTS = SERIES / "analysis" / "PACKAGE_CHECKPOINTS.json"


def sha256(path: Path) -> str:
    import hashlib
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def repo_rel(path: Path) -> str:
    return path.resolve().relative_to(REPO.resolve()).as_posix()


def git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()


def git_ok(commit: str) -> bool:
    return subprocess.run(["git", "cat-file", "-e", f"{commit}^{{commit}}"], cwd=REPO, capture_output=True, check=False).returncode == 0


def is_ancestor(base: str, head: str) -> bool:
    return subprocess.run(["git", "merge-base", "--is-ancestor", base, head], cwd=REPO, capture_output=True, check=False).returncode == 0


def excluded(path: Path) -> bool:
    return "__pycache__" in path.parts or path.suffix == ".pyc" or path.name == "PACKAGE_QA.json" or (path.parent.name == "handoff" and path.suffix == ".zip")


def all_full_files() -> list[Path]:
    return [path for path in sorted(SERIES.rglob("*")) if path.is_file() and not excluded(path)]


def checkpoint_registry() -> list[dict[str, Any]]:
    if not CHECKPOINTS.is_file():
        return []
    data = json.loads(CHECKPOINTS.read_text(encoding="utf-8"))
    return list(data.get("checkpoints", []))


def select_base(explicit: str | None, head: str) -> dict[str, Any]:
    candidates = checkpoint_registry()
    if explicit:
        if not git_ok(explicit):
            raise RuntimeError(f"base commit does not exist: {explicit}")
        matches = [item for item in candidates if item.get("head_commit") == explicit]
        if not matches:
            raise RuntimeError("explicit base commit has no registered successful package identity; add it to analysis/PACKAGE_CHECKPOINTS.json first")
        base = matches[-1]
    else:
        valid = []
        for item in candidates:
            commit = item.get("head_commit")
            package = REPO / item.get("package_path", "")
            if not commit or not git_ok(commit) or not package.is_file():
                continue
            if item.get("package_sha256") != sha256(package):
                continue
            valid.append(item)
        if not valid:
            raise RuntimeError("cannot determine a verified delta base from a successful package checkpoint; use --base-commit only after registering its package identity")
        base = valid[-1]
    commit = base.get("head_commit")
    if not commit or not git_ok(commit) or not is_ancestor(commit, head):
        raise RuntimeError(f"invalid delta ancestry: base={commit}, head={head}")
    return {"base_package_name": base.get("package_name"), "base_package_path": base.get("package_path"), "base_package_sha256": base.get("package_sha256"), "base_commit": commit}


def tracked_changes(base: str, head: str) -> dict[str, str]:
    output = subprocess.check_output(["git", "diff", "--name-status", base, head, "--", repo_rel(SERIES)], cwd=REPO, text=True)
    result: dict[str, str] = {}
    for line in output.splitlines():
        if not line.strip():
            continue
        status, path = line.split("\t", 1)
        result[path] = status[0]
    return result


def worktree_changes() -> dict[str, str]:
    output = subprocess.check_output(["git", "status", "--short", "--untracked-files=all", "--", repo_rel(SERIES)], cwd=REPO, text=True)
    result: dict[str, str] = {}
    for line in output.splitlines():
        if len(line) < 4:
            continue
        status = line[:2].strip() or "?"
        result[line[3:]] = status[0]
    return result


def delta_files(base: str, head: str) -> tuple[list[Path], dict[str, str]]:
    statuses = tracked_changes(base, head)
    statuses.update(worktree_changes())
    paths = []
    for relative, status in statuses.items():
        path = REPO / relative
        if path.is_file() and not excluded(path):
            paths.append(path)
    return sorted(set(paths)), statuses


def existing_references(files: list[Path]) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for path in files:
        if path.name != "BATCH_MANIFEST.json":
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        for point in data.get("points", []):
            if point.get("source_type") == "REUSED_EXISTING":
                refs.append({"source_case": point.get("source_case"), "raw_path": point.get("raw_path"), "raw_sha256": point.get("raw_sha256"), "source_batch": data.get("batch_id")})
    unique = {(item.get("source_case"), item.get("raw_sha256")): item for item in refs}
    return list(unique.values())


def exists_at_commit(commit: str, path: Path) -> bool:
    return subprocess.run(["git", "cat-file", "-e", f"{commit}:{repo_rel(path)}"], cwd=REPO, capture_output=True, check=False).returncode == 0


def batch_counts(base_commit: str, files: list[Path]) -> tuple[int, int]:
    batch_case_ids: set[str] = set()
    for path in files:
        if path.name != "BATCH_MANIFEST.json":
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        for point in data.get("points", []):
            for key in ("case_id", "source_case", "case_path"):
                value = point.get(key)
                if value:
                    batch_case_ids.add(Path(str(value)).name)
    new_solves = reused = 0
    for path in files:
        if path.name != "BATCH_QA.json":
            relative = path.relative_to(SERIES)
            is_user_result = len(relative.parts) == 3 and relative.parts[0] == "runs" and relative.parts[2] == "result.json"
            if not is_user_result or exists_at_commit(base_commit, path) or relative.parts[1] in batch_case_ids:
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001
                continue
            new_solves += int(data.get("physical_solve_count", 0))
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        new_solves += int(data.get("new_physical_solve_count", 0))
        reused += int(data.get("reused_points", 0))
    return new_solves, reused


def file_hashes(files: list[Path]) -> dict[str, str]:
    return {repo_rel(path): sha256(path) for path in files}


def delta_manifest(base: dict[str, Any], head: str, files: list[Path], statuses: dict[str, str]) -> dict[str, Any]:
    new_files = []
    modified_files = []
    for path in files:
        rel = repo_rel(path)
        if not subprocess.run(["git", "cat-file", "-e", f"{base['base_commit']}:{rel}"], cwd=REPO, capture_output=True, check=False).returncode == 0:
            new_files.append(rel)
        else:
            modified_files.append(rel)
    new_solves, reused = batch_counts(base["base_commit"], files)
    return {"schema": "bvm-rloop-delta-manifest-v1", "package_type": "delta", "base_package_name": base["base_package_name"], "base_package_sha256": base["base_package_sha256"], "base_commit": base["base_commit"], "head_commit": head, "included_files": [repo_rel(path) for path in files], "included_file_sha256": file_hashes(files), "new_files": sorted(new_files), "modified_files": sorted(modified_files), "referenced_existing_cases": existing_references(files), "new_physical_solve_count": new_solves, "reused_point_count": reused}


def print_plan(mode: str, tag: str, head: str, files: list[Path], manifest: dict[str, Any] | None, estimated_bytes: int) -> None:
    print(f"PACKAGE PREVIEW\n\nmode={mode}\ntag={tag}\nhead_commit={head}")
    if manifest:
        print(f"base_package={manifest['base_package_name']}\nbase_sha256={manifest['base_package_sha256']}\nbase_commit={manifest['base_commit']}")
        print("\nNEW FILES")
        print("\n".join(manifest["new_files"]) or "none")
        print("\nMODIFIED FILES")
        print("\n".join(manifest["modified_files"]) or "none")
        print("\nREFERENCED EXISTING CASES")
        print("\n".join(f"{ref.get('source_case')} raw={ref.get('raw_sha256')}" for ref in manifest["referenced_existing_cases"]) or "none")
        print(f"\nnew_physical_solve_count={manifest['new_physical_solve_count']}\nreused_point_count={manifest['reused_point_count']}")
    print(f"\nincluded_file_count={len(files)}\nestimated_uncompressed_bytes={estimated_bytes}\nNo archive created.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Create immutable FULL or traceable DELTA evidence package")
    parser.add_argument("--mode", choices=("full", "delta"), default="delta")
    parser.add_argument("--tag", required=True)
    parser.add_argument("--base-commit")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    head = git_head()
    base = select_base(args.base_commit, head) if args.mode == "delta" else None
    if args.mode == "full":
        files = all_full_files(); manifest = None
    else:
        files, statuses = delta_files(base["base_commit"], head)
        manifest = delta_manifest(base, head, files, statuses)
    estimated = sum(path.stat().st_size for path in files)
    if args.dry_run:
        print_plan(args.mode, args.tag, head, files, manifest, estimated)
        return 0
    handoff = SERIES / "handoff"; handoff.mkdir(parents=True, exist_ok=True)
    package = handoff / f"{SERIES.name}_{args.mode}_{args.tag}.zip"
    if package.exists():
        raise RuntimeError(f"refusing to overwrite existing package: {package}")
    with zipfile.ZipFile(package, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in files:
            archive.write(path, repo_rel(path))
        if manifest is not None:
            archive.writestr("DELTA_MANIFEST.json", json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    package_hash = sha256(package)
    mirror = Path("/mnt/d/BVM_Backages") / package.name
    mirror.parent.mkdir(parents=True, exist_ok=True)
    if mirror.exists():
        raise RuntimeError(f"refusing to overwrite existing mirror: {mirror}")
    shutil.copy2(package, mirror)
    mirror_hash = sha256(mirror)
    qa = {"schema": "bvm-rloop-one-shot-package-qa-v2", "status": "PASS" if package_hash == mirror_hash else "FAIL", "created_at": datetime.now().astimezone().isoformat(timespec="seconds"), "package_type": args.mode, "package": repo_rel(package), "package_sha256": package_hash, "package_bytes": package.stat().st_size, "package_file_count": len(files) + (1 if manifest is not None else 0), "included_file_sha256": file_hashes(files), "mirror": str(mirror), "mirror_sha256": mirror_hash, "mirror_bytes": mirror.stat().st_size, "head_commit": head, "raw_immutable": True, "scientific_interpretation_performed": False}
    if manifest is not None:
        qa.update({"base_package_name": manifest["base_package_name"], "base_package_sha256": manifest["base_package_sha256"], "base_commit": manifest["base_commit"], "referenced_existing_cases": manifest["referenced_existing_cases"], "new_physical_solve_count": manifest["new_physical_solve_count"], "reused_point_count": manifest["reused_point_count"]})
    (SERIES / "analysis" / "PACKAGE_QA.json").write_text(json.dumps(qa, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(qa, ensure_ascii=False, indent=2))
    return 0 if qa["status"] == "PASS" else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"ERROR: {exc}")
        raise SystemExit(2)
