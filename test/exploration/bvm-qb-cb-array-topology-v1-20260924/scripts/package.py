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

from evidence import EvidenceError, PackageMember, discover_batch_manifests, validate_complete_batch

SERIES = Path(__file__).resolve().parents[1]
REPO = next(path for path in (SERIES, *SERIES.parents) if (path / ".git").exists())
CHECKPOINTS = SERIES / "analysis" / "PACKAGE_CHECKPOINTS.json"
PACKAGE_QA = SERIES / "analysis" / "PACKAGE_QA.json"
MIRROR = Path("/mnt/d/BVM_Backages")
TAG_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
SERIES_REL = SERIES.relative_to(REPO).as_posix()
PLATFORM_PATHS = {
    ".gitattributes", ".gitignore", "README.md", "PREFLIGHT.md",
    "USER_CASE.env", "STIMULUS.env", "config/component_reference.env",
    "scripts/components.py", "scripts/config.py", "scripts/evidence.py",
    "scripts/inspect_runs.py", "scripts/package.py", "scripts/plot_run.py",
    "scripts/probes.py", "scripts/run_case.py", "scripts/stimulus.py",
    "scripts/submit.py", "scripts/topology.py", "scripts/try_case.py",
    "submit.sh", "try.sh", "templates/base.cir",
}
CATEGORIES = (
    "raw", "plots", "run_manifests_qa", "source_snapshots", "batch_metadata",
    "platform_reproduction_metadata", "other",
)
PLOTTER = REPO / "scripts" / "josim-plot2.py"
PLOTLY_ASSET = SERIES / "plots" / "assets" / "plotly.min.js"


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
        "base_package_type": base["package_type"],
        "base_commit": commit,
    }


def worktree_changes() -> dict[str, str]:
    result = subprocess.run(
        ["git", "status", "--short", "--untracked-files=all", "--", rel(SERIES)],
        cwd=REPO, check=True, capture_output=True, text=True,
    )
    raw = result.stdout
    return parse_worktree_changes(raw)


def parse_worktree_changes(raw: str) -> dict[str, str]:
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


def _series_relative(repo_path: str) -> str | None:
    prefix = SERIES_REL.rstrip("/") + "/"
    if repo_path.startswith(prefix):
        return repo_path[len(prefix):]
    if repo_path.startswith(("batches/", "runs/")):
        return repo_path
    return None


def _read_archive_manifest(entry: dict[str, Any]) -> tuple[dict[str, Any], set[str]]:
    package_path = (REPO / str(entry["package_path"])).resolve()
    if sha256(package_path) != entry.get("package_sha256"):
        raise RuntimeError(f"checkpoint package SHA mismatch: {package_path}")
    with zipfile.ZipFile(package_path, "r") as archive:
        candidates = ("FULL_MANIFEST.json", "DELTA_MANIFEST.json")
        manifest_name = next((name for name in candidates if name in archive.namelist()), None)
        if manifest_name is None:
            raise RuntimeError(f"checkpoint has no package manifest: {package_path}")
        try:
            manifest = json.loads(archive.read(manifest_name))
        except (KeyError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"checkpoint package manifest is invalid: {package_path}") from exc
        return manifest, set(archive.namelist())


def _checkpoint_evidence(base: dict[str, Any]) -> tuple[
    set[str], dict[str, dict[str, str]], dict[str, str]
]:
    """Resolve all verified package ancestors to find cases/raw already in the base chain."""
    entries = checkpoint_entries()
    current = next((entry for entry in entries
                    if entry.get("package_name") == base.get("base_package_name")
                    and entry.get("package_sha256") == base.get("base_package_sha256")), None)
    if current is None:
        raise RuntimeError("selected DELTA base is absent from the checkpoint registry")
    chain: list[tuple[dict[str, Any], dict[str, Any]]] = []
    seen: set[str] = set()
    while current:
        digest = str(current.get("package_sha256", ""))
        if not digest or digest in seen:
            raise RuntimeError("package checkpoint ancestry contains a cycle or missing SHA")
        seen.add(digest)
        if not _verified_entry(current):
            raise RuntimeError(f"unverified package in DELTA base ancestry: {current.get('package_name')}")
        manifest, _ = _read_archive_manifest(current)
        chain.append((current, manifest))
        parent_sha = manifest.get("base_package_sha256")
        if not parent_sha:
            break
        parent = next((entry for entry in entries if entry.get("package_sha256") == parent_sha), None)
        if parent is None or parent.get("package_name") != manifest.get("base_package_name"):
            raise RuntimeError(f"DELTA base ancestry is unregistered or ambiguous: {parent_sha}")
        current = parent

    known_batches: set[str] = set()
    known_batch_hashes: dict[str, str] = {}
    known_cases: dict[str, dict[str, str]] = {}
    for entry, manifest in reversed(chain):
        package_path = (REPO / str(entry["package_path"])).resolve()
        names = set(manifest.get("included_files", []))
        file_hashes = manifest.get("included_file_sha256", {})
        with zipfile.ZipFile(package_path, "r") as archive:
            for member in sorted(names):
                series_path = _series_relative(str(member))
                if series_path is None:
                    continue
                if series_path.endswith("/raw.csv") and series_path.startswith("runs/"):
                    digest = file_hashes.get(member)
                    if isinstance(digest, str):
                        run_id = Path(series_path).parts[1]
                        record = {"raw_sha256": digest, "source_package": str(entry["package_name"])}
                        known_cases[series_path] = record
                        known_cases[run_id] = record
                if series_path.startswith("batches/") and series_path.endswith("/batch_manifest.json"):
                    try:
                        batch_data = json.loads(archive.read(member))
                    except (KeyError, json.JSONDecodeError) as exc:
                        raise RuntimeError(f"invalid packaged batch manifest: {member}") from exc
                    if batch_data.get("status") == "COMPLETE_MECHANICAL":
                        batch_id = str(batch_data.get("batch_id", ""))
                        if batch_id:
                            known_batches.add(batch_id)
                            digest = file_hashes.get(member)
                            if isinstance(digest, str):
                                known_batch_hashes[batch_id] = digest
        for reference in manifest.get("referenced_existing_cases", []):
            if not isinstance(reference, dict):
                continue
            raw_path = _series_relative(str(reference.get("raw_path", "")))
            raw_sha = reference.get("raw_sha256")
            if raw_path and isinstance(raw_sha, str):
                source_package = str(reference.get("source_package", entry["package_name"]))
                record = {"raw_sha256": raw_sha, "source_package": source_package}
                known_cases[raw_path] = record
                known_cases[Path(raw_path).parts[1]] = record
    return known_batches, known_cases, known_batch_hashes


def _platform_members(mode: str, base: dict[str, Any] | None,
                      head: str) -> tuple[list[PackageMember], dict[str, str]]:
    changes: dict[str, str] = {}
    if base:
        changes.update(committed_changes(str(base["base_commit"]), head))
    changes.update(worktree_changes())
    members: list[PackageMember] = []
    statuses: dict[str, str] = {}
    for local_path in sorted(PLATFORM_PATHS):
        source = SERIES / local_path
        if not source.is_file() or source.is_symlink():
            continue
        repo_path = rel(source)
        if mode == "full" or repo_path in changes:
            members.append(PackageMember(source, repo_path, "platform_reproduction_metadata"))
            if base:
                exists = subprocess.run(
                    ["git", "cat-file", "-e", f"{base['base_commit']}:{repo_path}"],
                    cwd=REPO, capture_output=True, check=False,
                ).returncode == 0
                statuses[repo_path] = "M" if exists else "A"
    for source, archive_path in ((PLOTTER, "reproduction/scripts/josim-plot2.py"),
                                 (PLOTLY_ASSET, "reproduction/plotly.min.js")):
        if not source.is_file() or source.is_symlink():
            raise RuntimeError(f"required plot reproduction tool is missing: {source}")
        members.append(PackageMember(source, archive_path, "platform_reproduction_metadata"))
    return members, statuses


def _member_record(member: PackageMember) -> dict[str, Any]:
    return {
        "source_path": rel(member.source),
        "archive_path": member.archive_path,
        "category": member.category,
        "bytes": member.source.stat().st_size,
        "sha256": sha256(member.source),
    }


def _size_breakdown(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    total = sum(int(item["bytes"]) for item in records)
    result = {}
    for category in CATEGORIES:
        selected = [item for item in records if item["category"] == category]
        size = sum(int(item["bytes"]) for item in selected)
        result[category] = {
            "file_count": len(selected),
            "uncompressed_bytes": size,
            "percentage": round((100.0 * size / total), 2) if total else 0.0,
        }
    return result


def _plotter_version() -> str:
    source = PLOTTER.read_text(encoding="utf-8")
    match = re.search(r"^\s*vers\s*=\s*['\"]([^'\"]+)['\"]", source, flags=re.MULTILINE)
    return match.group(1) if match else "unversioned"


def package_manifest(mode: str, tag: str, head: str, records: list[dict[str, Any]],
                     base: dict[str, Any] | None, *, selected_batches: list[dict[str, Any]],
                     selected_runs: list[dict[str, Any]], excluded_batches: list[dict[str, str]],
                     references: list[dict[str, str]], include_plots: bool,
                     statuses: dict[str, str]) -> dict[str, Any]:
    new_files: list[str] = []
    modified_files: list[str] = []
    if base:
        for record in records:
            path = str(record["source_path"])
            if not path.startswith(SERIES_REL + "/"):
                continue
            status = statuses.get(path)
            if status in {"A", "?"}:
                new_files.append(str(record["archive_path"]))
            elif status == "M":
                modified_files.append(str(record["archive_path"]))
            else:
                exists = subprocess.run(
                    ["git", "cat-file", "-e", f"{base['base_commit']}:{path}"],
                    cwd=REPO, capture_output=True, check=False,
                ).returncode == 0
                (modified_files if exists else new_files).append(str(record["archive_path"]))
    hashes = {str(item["archive_path"]): str(item["sha256"]) for item in records}
    total_bytes = sum(int(item["bytes"]) for item in records)
    categories = _size_breakdown(records)
    tools = [
        {"name": "josim-plot2.py", "version": _plotter_version(),
         "path": rel(PLOTTER), "archive_path": "reproduction/scripts/josim-plot2.py",
         "sha256": sha256(PLOTTER)},
        {"name": "shared Plotly runtime", "version": "series-pinned asset",
         "path": rel(PLOTLY_ASSET), "archive_path": "reproduction/plotly.min.js",
         "sha256": sha256(PLOTLY_ASSET)},
    ]
    normalized_references = []
    for item in references:
        raw_path = str(item["raw_path"])
        if not raw_path.startswith(SERIES_REL + "/"):
            raw_path = f"{SERIES_REL}/{raw_path.lstrip('/')}"
        normalized_references.append({**item, "raw_path": raw_path})
    manifest: dict[str, Any] = {
        "schema": "bvm-qb-cb-array-package-manifest-v2",
        "package_type": mode,
        "tag": tag,
        "head_commit": head,
        "include_plots": include_plots,
        "plot_inclusion_policy": (
            "USER_DIRECTED: derived HTML excluded by default; plot manifest/QA, raw hashes, "
            "plotter version/hash and shared asset reference retained; use --include-plots to add HTML"
        ),
        "included_files": [str(item["archive_path"]) for item in records],
        "included_file_sha256": hashes,
        "included_file_records": records,
        "new_files": sorted(new_files),
        "modified_files": sorted(modified_files),
        "uncompressed_payload_bytes": total_bytes,
        "size_breakdown": categories,
        "top_20_largest_members": sorted(
            ({"archive_path": item["archive_path"], "category": item["category"],
              "bytes": item["bytes"], "sha256": item["sha256"]} for item in records),
            key=lambda item: (-int(item["bytes"]), str(item["archive_path"])),
        )[:20],
        "selected_batches": selected_batches,
        "included_runs": selected_runs,
        "referenced_existing_cases": normalized_references,
        "reproduction_tools": tools,
        "new_physical_solve_count": sum(
            int(batch["new_physical_solve_count"]) for batch in selected_batches
        ),
        "reused_point_count": len(normalized_references),
        "excluded_batches": excluded_batches,
        "excluded_file_categories": [
            "tests/**", "tests/fixtures/**", "__pycache__", "*.pyc",
            "incomplete/failed batches", "unreferenced run directories",
            "derived plots/*.html unless --include-plots", "historical handoff ZIPs",
        ],
        "scientific_interpretation_performed": False,
    }
    if base:
        manifest.update(base)
    return manifest


def _select_batches(mode: str, base: dict[str, Any] | None,
                    include_plots: bool) -> tuple[list[PackageMember], list[dict[str, Any]],
                                                  list[dict[str, Any]], list[dict[str, str]],
                                                  list[dict[str, str]]]:
    known_batches, known_cases, known_batch_hashes = (
        _checkpoint_evidence(base) if base else (set(), {}, {})
    )
    members: dict[str, PackageMember] = {}
    selected_batches: list[dict[str, Any]] = []
    selected_runs: list[dict[str, Any]] = []
    excluded_batches: list[dict[str, str]] = []
    references: list[dict[str, str]] = []
    for manifest_path in discover_batch_manifests(SERIES):
        batch_dir = manifest_path.parent
        try:
            raw_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"cannot read candidate batch manifest: {manifest_path}") from exc
        batch_id = str(raw_manifest.get("batch_id", batch_dir.name))
        status = str(raw_manifest.get("status", "UNKNOWN"))
        if status != "COMPLETE_MECHANICAL":
            excluded_batches.append({"batch_id": batch_id, "status": status,
                                     "reason": "not COMPLETE_MECHANICAL"})
            continue
        if mode == "delta" and batch_id in known_batches:
            raw_hash = sha256(manifest_path)
            old_hash = known_batch_hashes.get(batch_id)
            if old_hash and old_hash != raw_hash:
                raise RuntimeError(f"accepted batch manifest changed after checkpoint: {batch_id}")
            excluded_batches.append({"batch_id": batch_id, "status": status,
                                     "reason": "already represented by verified base chain"})
            continue
        selection = validate_complete_batch(batch_dir, SERIES, include_plots=include_plots,
                                            known_cases=known_cases)
        if selection is None:
            continue
        for member in selection["members"]:
            archive_path = f"{SERIES_REL}/{member.archive_path}"
            if archive_path in members and members[archive_path].source != member.source:
                raise RuntimeError(f"conflicting package source for {archive_path}")
            members[archive_path] = PackageMember(member.source, archive_path, member.category)
        solve_count = sum(1 for row in selection["runs"] if not row.get("reused"))
        selected_batches.append({
            "batch_id": selection["batch_id"], "status": "COMPLETE_MECHANICAL",
            "array_size": selection["array_size"],
            "requested_masks": selection["requested_masks"],
            "probe_profile": selection["probe_profile"],
            "run_ids": [run["run_id"] for run in selection["runs"]],
            "new_physical_solve_count": solve_count,
        })
        for run in selection["runs"]:
            raw_path = str(run["raw_path"])
            selected_runs.append({**run, "raw_path": f"{SERIES_REL}/{raw_path}"})
        references.extend(selection["referenced_existing_cases"])
    return list(members.values()), selected_batches, selected_runs, excluded_batches, references


def build_plan(mode: str, tag: str, base_commit: str | None = None,
               include_plots: bool = False) -> dict[str, Any]:
    if mode not in {"full", "delta"}:
        raise RuntimeError(f"unsupported package mode: {mode}")
    if not TAG_RE.fullmatch(tag):
        raise RuntimeError(f"invalid package tag: {tag!r}")
    head = head_commit()
    base = select_base(base_commit, head) if mode == "delta" else None
    evidence_members, selected_batches, selected_runs, excluded_batches, references = \
        _select_batches(mode, base, include_plots)
    platform_members, statuses = _platform_members(mode, base, head)
    members_by_path: dict[str, PackageMember] = {}
    for member in (*evidence_members, *platform_members):
        if member.archive_path in members_by_path:
            previous = members_by_path[member.archive_path]
            if previous.source != member.source:
                raise RuntimeError(f"duplicate package archive member path: {member.archive_path}")
            continue
        members_by_path[member.archive_path] = member
    members = [members_by_path[path] for path in sorted(members_by_path)]
    records = [_member_record(member) for member in members]
    manifest = package_manifest(
        mode, tag, head, records, base, selected_batches=selected_batches,
        selected_runs=selected_runs, excluded_batches=excluded_batches,
        references=references, include_plots=include_plots, statuses=statuses,
    )
    manifest_path = "FULL_MANIFEST.json" if mode == "full" else "DELTA_MANIFEST.json"
    package_name = f"{SERIES.name}_{mode}_{tag}.zip"
    package_path = SERIES / "handoff" / package_name
    mirror_path = MIRROR / package_name
    if package_path.exists():
        raise RuntimeError(f"refusing to overwrite package: {package_path}")
    if mirror_path.exists():
        raise RuntimeError(f"refusing to overwrite mirror target: {mirror_path}")
    dirty_paths = [path for path in worktree_changes()
                   if not excluded(REPO / path) and not path.endswith("/PACKAGE_QA.json")]
    uncompressed_bytes = sum(member.source.stat().st_size for member in members)
    return {
        "mode": mode, "tag": tag, "head_commit": head, "base": base,
        "members": members, "records": records, "dirty_source_paths": dirty_paths,
        "manifest": manifest, "manifest_path": manifest_path,
        "package_path": package_path, "mirror_path": mirror_path,
        "estimated_uncompressed_bytes": uncompressed_bytes,
        "include_plots": include_plots,
    }


def print_plan(plan: dict[str, Any]) -> None:
    manifest = plan["manifest"]
    print(json.dumps({
        "status": "PACKAGE_DRY_RUN_PASS",
        "mode": plan["mode"], "tag": plan["tag"],
        "head_commit": plan["head_commit"], "base": plan["base"],
        "included_file_count": len(plan["members"]),
        "uncompressed_bytes": plan["estimated_uncompressed_bytes"],
        "size_breakdown": manifest["size_breakdown"],
        "top_20_largest_members": manifest["top_20_largest_members"],
        "selected_batches": manifest["selected_batches"],
        "included_run_count": len(manifest["included_runs"]),
        "new_physical_solve_count": manifest["new_physical_solve_count"],
        "reused_point_count": manifest["reused_point_count"],
        "referenced_existing_cases": manifest["referenced_existing_cases"],
        "excluded_batches": manifest["excluded_batches"],
        "excluded_file_categories": manifest["excluded_file_categories"],
        "include_plots": plan["include_plots"],
        "expected_package_contents": manifest["included_files"],
        "package_path": rel(plan["package_path"]),
        "mirror_path": str(plan["mirror_path"]),
        "dirty_source_paths": plan["dirty_source_paths"],
        "archive_created": False, "mirror_created": False,
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
            for member in plan["members"]:
                archive.write(member.source, member.archive_path)
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
    with zipfile.ZipFile(package_path, "r") as archive:
        infos = [entry for entry in archive.infolist() if not entry.is_dir()]
    uncompressed_bytes = sum(entry.file_size for entry in infos)
    compressed_bytes = sum(entry.compress_size for entry in infos)
    compression_ratio = compressed_bytes / uncompressed_bytes if uncompressed_bytes else 0.0
    shutil.copyfile(package_path, mirror_path)
    mirror_sha = sha256(mirror_path)
    qa = {
        "schema": "bvm-qb-cb-array-package-qa-v1",
        "status": "PASS" if package_sha == mirror_sha else "FAIL",
        "package_type": plan["mode"], "package_name": package_path.name,
        "package_path": rel(package_path), "package_sha256": package_sha,
        "package_bytes": package_path.stat().st_size,
        "uncompressed_bytes": uncompressed_bytes,
        "compressed_bytes": compressed_bytes,
        "compression_ratio": compression_ratio,
        "payload_size_breakdown": plan["manifest"]["size_breakdown"],
        "archive_member_count": len(infos),
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
    qa["included_runs"] = plan["manifest"]["included_runs"]
    qa["selected_batches"] = plan["manifest"]["selected_batches"]
    qa["include_plots"] = plan["include_plots"]
    PACKAGE_QA.write_text(json.dumps(qa, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                          encoding="utf-8")
    return qa


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create an immutable FULL or DELTA evidence package")
    parser.add_argument("--mode", choices=("full", "delta"), default="delta")
    parser.add_argument("--tag", required=True)
    parser.add_argument("--base-commit")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--include-plots", action="store_true",
                        help="include five QA-verified derived HTML pages for each selected run")
    args = parser.parse_args(argv)
    try:
        plan = build_plan(args.mode, args.tag, args.base_commit, args.include_plots)
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
