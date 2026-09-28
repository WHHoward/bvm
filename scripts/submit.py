#!/usr/bin/env python3
"""Global submit workflow: scoped source commit -> QA'd bundles -> package commit -> optional push.

For a single scope that already owns scripts/submit.py, this command delegates to that
series-specific workflow. Otherwise it snapshots new directories, emits lineage-bound
deltas after a full snapshot, splits large deltas by run, and splits full component plots.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
MIRROR_DEFAULT = Path("/mnt/d/BVM_Backages")
MAX_GIT_FILE_BYTES = 100_000_000
TAG_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
COMPONENTS = ("BVM", "QB", "CB", "ACC", "GAP")


def git(args: list[str], *, check: bool = True, capture: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=REPO, text=True, capture_output=capture, check=check)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO.resolve()).as_posix()


def iso_now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def upstream() -> str:
    result = git(["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"], check=False)
    if result.returncode or not result.stdout.strip():
        raise RuntimeError("cannot determine the current branch upstream")
    return result.stdout.strip()


def head() -> str:
    return git(["rev-parse", "HEAD"]).stdout.strip()


def parse_porcelain_z(data: str) -> dict[str, str]:
    parts = data.split("\0")
    found: dict[str, str] = {}
    i = 0
    while i < len(parts):
        record = parts[i]
        i += 1
        if len(record) < 4:
            continue
        status, path = record[:2], record[3:]
        found[path] = status.strip() or "?"
        if "R" in status or "C" in status:
            if i < len(parts) and parts[i]:
                found[parts[i]] = "D"
                i += 1
    return found


def parse_name_status_z(data: str) -> dict[str, str]:
    parts = data.split("\0")
    found: dict[str, str] = {}
    i = 0
    while i < len(parts):
        status = parts[i]
        i += 1
        if not status or i >= len(parts):
            continue
        first = parts[i]
        i += 1
        if status.startswith(("R", "C")):
            second = parts[i] if i < len(parts) else ""
            i += 1
            found[first] = "D"
            if second:
                found[second] = "A"
        else:
            found[first] = status[0]
    return found


def committed_changes(base: str, tip: str) -> dict[str, str]:
    output = git(["diff", "--name-status", "-z", f"{base}..{tip}", "--"]).stdout
    return parse_name_status_z(output)


def working_changes() -> dict[str, str]:
    output = git(["status", "--porcelain=v1", "-z", "--untracked-files=all"]).stdout
    return parse_porcelain_z(output)


def untracked_files() -> list[str]:
    output = git(["ls-files", "--others", "--exclude-standard", "-z"]).stdout
    return [item for item in output.split("\0") if item]


def generated_cache_path(path_text: str) -> bool:
    path = Path(path_text)
    return ("__pycache__" in path.parts or path.suffix == ".pyc" or
            any(part in {".pytest_cache", ".ruff_cache", ".mypy_cache", "node_modules"} for part in path.parts) or
            path.name == ".DS_Store" or path.name.endswith(".tmp"))


def normalize_scopes(values: list[str] | None, base: str, tip: str) -> list[Path]:
    if values:
        scopes = []
        for value in values:
            candidate = (REPO / value).resolve() if not Path(value).is_absolute() else Path(value).resolve()
            try:
                candidate.relative_to(REPO.resolve())
            except ValueError as exc:
                raise RuntimeError(f"scope escapes repository: {value}") from exc
            if not candidate.is_dir():
                raise RuntimeError(f"scope is not an existing directory: {value}")
            scopes.append(candidate)
    else:
        changed = set(committed_changes(base, tip)) | set(working_changes()) | set(untracked_files())
        roots = set()
        for value in changed:
            parts = Path(value).parts
            if len(parts) >= 3 and parts[:2] == ("test", "exploration"):
                roots.add(REPO / parts[0] / parts[1] / parts[2])
        scopes = sorted(roots)
    unique = sorted(set(scopes))
    for index, left in enumerate(unique):
        for right in unique[index + 1:]:
            if left in right.parents or right in left.parents:
                raise RuntimeError(f"overlapping scopes are not allowed: {rel(left)} and {rel(right)}")
    if not unique:
        raise RuntimeError("no experiment scopes selected or detected")
    return unique


def in_scope(path_text: str, scopes: list[Path]) -> bool:
    path = (REPO / path_text).resolve()
    return any(path == scope or scope in path.parents for scope in scopes)


def is_package_output(path_text: str, scopes: list[Path]) -> bool:
    path = Path(path_text)
    if not in_scope(path_text, scopes) or "handoff" not in path.parts:
        return False
    return path.suffix.lower() == ".zip" or path.name == "PACKAGE_QA.json" or "PACKAGE_QA" in path.name


def scoped_delta(base: str, tip: str, scopes: list[Path]) -> dict[str, str]:
    changes = committed_changes(base, tip)
    for path, status in working_changes().items():
        if status != "??":
            changes[path] = status
    for path in untracked_files():
        if generated_cache_path(path):
            continue
        changes[path] = "A"
    return {path: status for path, status in changes.items()
            if in_scope(path, scopes) and not is_package_output(path, scopes)}


def source_bundle_candidates(scope: Path) -> list[Path]:
    """Return only the immutable source bundle whose identity matches this scope."""
    package = scope / "handoff" / f"{scope.name}_source_bundle_v1.zip"
    return [package] if package.is_file() else []


def scope_has_source_changes(scope: Path, changes: dict[str, str]) -> bool:
    """Whether source/evidence changed in this scope, excluding generated packages."""
    return any(in_scope(path, [scope]) and not is_package_output(path, [scope])
               and not generated_cache_path(path) for path in changes)


def source_stage_paths(scopes: list[Path]) -> list[str]:
    paths = [path for path, status in working_changes().items()
             if status != "??" and in_scope(path, scopes) and not is_package_output(path, scopes)]
    paths.extend(path for path in untracked_files()
                 if in_scope(path, scopes) and not is_package_output(path, scopes) and not generated_cache_path(path))
    for support_path in ("scripts/test_submit.py", "scripts/SUBMIT_REVIEW.md"):
        if (REPO / support_path).is_file():
            paths.append(support_path)
    script_rel = rel(Path(__file__))
    if Path(__file__).exists():
        paths.append(script_rel)
    return sorted(set(paths))


def assert_no_pre_staged_outside(allowed: set[str]) -> None:
    staged = git(["diff", "--cached", "--name-only", "-z"]).stdout.split("\0")
    outside = sorted(item for item in staged if item and item not in allowed)
    if outside:
        raise RuntimeError("pre-staged changes outside this submission scope: " + ", ".join(outside))


def file_records(sources: list[tuple[Path, str]]) -> list[dict[str, Any]]:
    records = []
    names = set()
    for source, member in sources:
        if member in names:
            raise RuntimeError(f"duplicate package member: {member}")
        names.add(member)
        if not source.is_file() or source.is_symlink():
            raise RuntimeError(f"package source is missing or not a regular file: {source}")
        records.append({"repo_path": rel(source), "archive_path": member,
                        "sha256": sha256(source), "bytes": source.stat().st_size})
    return records


def _read_delta_manifest(package: Path) -> dict[str, Any]:
    try:
        with zipfile.ZipFile(package, "r") as archive:
            return json.loads(archive.read("DELTA_MANIFEST.json"))
    except (KeyError, json.JSONDecodeError, zipfile.BadZipFile) as exc:
        raise RuntimeError(f"delta package has no valid DELTA_MANIFEST.json: {package}") from exc


def _delta_payload_hashes(manifest: dict[str, Any], package: Path) -> dict[str, str]:
    hashes = manifest.get("included_file_sha256")
    records = manifest.get("included_files")
    if not isinstance(hashes, dict) or not isinstance(records, list):
        raise RuntimeError(f"delta manifest has no file/hash closure: {package}")
    record_hashes = {}
    for record in records:
        member, digest = record.get("archive_path"), record.get("sha256")
        if not member or not digest or member in record_hashes:
            raise RuntimeError(f"delta manifest has duplicate/incomplete included file records: {package}")
        record_hashes[member] = digest
    if record_hashes != hashes:
        raise RuntimeError(f"delta manifest included file list/hash map disagree: {package}")
    return hashes


def _source_hashes_from_qa(qa: dict[str, Any]) -> dict[str, str]:
    return {path: digest for path, digest in qa.get("included_file_sha256", {}).items()
            if path not in {"BUNDLE_MANIFEST.json", "README_BUNDLE.txt"}}


def _compose_delta_layers(base_package: Path, base_qa: dict[str, Any],
                          layers: list[dict[str, Any]], *,
                          seen: set[Path] | None = None
                          ) -> tuple[dict[str, str], dict[str, dict[str, str]], set[str]]:
    hashes = _source_hashes_from_qa(base_qa)
    raw_sources = {
        path: {"source_package_name": base_package.name,
               "source_package_sha256": base_qa["package_sha256"]}
        for path in hashes if path.endswith("raw.csv")
    }
    deleted_paths: set[str] = set()
    same_head_paths: dict[str, set[str]] = {}
    for entry in layers:
        package_name = entry.get("package_name")
        package_sha = entry.get("package_sha256")
        package_head = entry.get("head_commit")
        if (not package_name or Path(package_name).name != package_name or
                not package_name.endswith(".zip") or not package_sha or not package_head):
            raise RuntimeError("delta checkpoint contains an incomplete package identity")
        package = base_package.with_name(package_name)
        qa_path = package.with_name(f"{package.stem}_PACKAGE_QA.json")
        qa = verify_existing_bundle(package, qa_path, _seen=seen)
        if (qa.get("bundle_type") != "directory_snapshot_delta" or
                qa.get("package_sha256") != package_sha or qa.get("head_commit") != package_head or
                qa.get("base_package_name") != base_package.name or
                qa.get("base_package_sha256") != base_qa["package_sha256"]):
            raise RuntimeError(f"delta checkpoint package identity mismatch: {package}")
        manifest = _read_delta_manifest(package)
        if manifest.get("base_commit") != base_qa.get("source_commit"):
            raise RuntimeError(f"delta checkpoint points at a different full-base commit: {package}")
        layer_hashes = _delta_payload_hashes(manifest, package)
        paths_for_head = same_head_paths.setdefault(package_head, set())
        overlap = paths_for_head.intersection(layer_hashes)
        if overlap:
            raise RuntimeError(f"delta checkpoint duplicates members within one head: {sorted(overlap)}")
        paths_for_head.update(layer_hashes)
        for path, digest in layer_hashes.items():
            hashes[path] = digest
            deleted_paths.discard(path)
            if path.endswith("raw.csv"):
                raw_sources[path] = {"source_package_name": package.name,
                                     "source_package_sha256": package_sha}
        for path in manifest.get("deleted_files", []):
            if path.startswith("runs/") and path.endswith("/raw.csv"):
                raise RuntimeError(f"delta checkpoint deletes historical raw evidence: {path}")
            hashes.pop(path, None)
            raw_sources.pop(path, None)
            deleted_paths.add(path)
    return hashes, raw_sources, deleted_paths


def verify_existing_bundle(package: Path, qa_path: Path, *,
                           _seen: set[Path] | None = None) -> dict[str, Any]:
    seen = set(_seen or ())
    package_resolved = package.resolve()
    if package_resolved in seen:
        raise RuntimeError(f"cyclic delta package lineage detected: {package}")
    seen.add(package_resolved)
    if not package.is_file() or not qa_path.is_file():
        raise RuntimeError(f"incomplete prebuilt bundle/QA pair: {package}")
    qa = json.loads(qa_path.read_text(encoding="utf-8"))
    if qa.get("package_path") and qa["package_path"] != rel(package):
        raise RuntimeError(f"prebuilt bundle QA names a different package path: {package}")
    if qa.get("status") != "PASS" or qa.get("package_sha256") != sha256(package):
        raise RuntimeError(f"prebuilt bundle QA/SHA mismatch: {package}")
    if qa.get("package_bytes") != package.stat().st_size or package.stat().st_size >= MAX_GIT_FILE_BYTES:
        raise RuntimeError(f"prebuilt package exceeds or mismatches ordinary Git limit: {package}")
    expected = qa.get("included_file_sha256", {})
    with zipfile.ZipFile(package, "r") as archive:
        if archive.testzip() is not None or set(archive.namelist()) != set(expected):
            raise RuntimeError(f"prebuilt package CRC/member set mismatch: {package}")
        for member, digest in expected.items():
            if hashlib.sha256(archive.read(member)).hexdigest() != digest:
                raise RuntimeError(f"prebuilt package member hash mismatch: {package}!/{member}")
        if qa.get("bundle_type") == "directory_snapshot_delta":
            manifest = json.loads(archive.read("DELTA_MANIFEST.json"))
            if (manifest.get("base_package_name") != qa.get("base_package_name") or
                    manifest.get("base_package_sha256") != qa.get("base_package_sha256") or
                    manifest.get("base_commit") != qa.get("base_commit") or
                    manifest.get("head_commit") != qa.get("source_commit") or
                    manifest.get("prior_delta_head_commit") != qa.get("prior_delta_head_commit") or
                    (manifest.get("base_delta_packages") or []) !=
                    (qa.get("base_delta_packages") or [])):
                raise RuntimeError(f"delta package/base identity mismatch: {package}")
            payload_hashes = _delta_payload_hashes(manifest, package)
            if any(expected.get(path) != digest for path, digest in payload_hashes.items()):
                raise RuntimeError(f"delta payload hashes disagree with package QA: {package}")
            base_package = package.with_name(manifest["base_package_name"])
            base_qa_path = base_package.with_name(f"{base_package.stem}_PACKAGE_QA.json")
            base_qa = verify_existing_bundle(base_package, base_qa_path, _seen=seen)
            if (base_qa.get("package_sha256") != manifest["base_package_sha256"] or
                    base_qa.get("source_commit") != manifest.get("base_commit")):
                raise RuntimeError(f"delta package references a different base identity: {package}")
            prior_layers = manifest.get("base_delta_packages") or []
            prior_heads = [entry.get("head_commit") for entry in prior_layers]
            package_names = [entry.get("package_name") for entry in prior_layers]
            if (any(not isinstance(head, str) or not head for head in prior_heads) or
                    None in package_names or len(package_names) != len(set(package_names))):
                raise RuntimeError(f"delta checkpoint has malformed package ordering: {package}")
            distinct_heads = list(dict.fromkeys(prior_heads))
            for previous, current in zip(distinct_heads, distinct_heads[1:]):
                if git(["merge-base", "--is-ancestor", previous, current], check=False).returncode:
                    raise RuntimeError(f"delta checkpoint heads are not in ancestry order: {package}")
            expected_prior_head = prior_heads[-1] if prior_heads else None
            if manifest.get("prior_delta_head_commit") != expected_prior_head:
                raise RuntimeError(f"delta package prior-checkpoint head mismatch: {package}")
            # A sibling delta package shares the same complete prior package set.
            # Remove the full package from the recursion stack before verifying
            # sibling layers, since each independently references that same base.
            layer_seen = set(seen)
            layer_seen.discard(base_package.resolve())
            base_hashes, raw_sources, _base_deleted = _compose_delta_layers(
                base_package, base_qa, prior_layers, seen=layer_seen)
            if (manifest.get("base_delta_packages") or []) != prior_layers:
                raise RuntimeError(f"delta package checkpoint list mismatch: {package}")
            for reference in manifest.get("referenced_existing_raw_sha256", []):
                source = raw_sources.get(reference.get("raw_path"))
                if (base_hashes.get(reference.get("raw_path")) != reference.get("raw_sha256") or
                        not source or
                        source.get("source_package_name") != reference.get("source_package_name") or
                        source.get("source_package_sha256") != reference.get("source_package_sha256")):
                    raise RuntimeError(f"delta package existing-raw reference mismatch: {package}")
    return qa


def component_bundle_specs(scope: Path, tag: str) -> list[dict[str, Any]]:
    manifest_path = scope / "analysis" / "component_plot_manifest_v1.json"
    qa_path = scope / "qa" / "component_plot_qa_v1.json"
    package_qa_path = scope / "handoff" / "PACKAGE_QA.json"
    base_qa = json.loads(package_qa_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    plot_qa = json.loads(qa_path.read_text(encoding="utf-8"))
    base_zip = scope / base_qa["package_path"]
    if (base_qa.get("status") != "PASS" or sha256(base_zip) != base_qa.get("package_sha256") or
            plot_qa.get("status") != "PASS" or manifest.get("parent_package_sha256") != base_qa.get("package_sha256")):
        raise RuntimeError(f"component plot/base package QA is not consistent: {scope}")
    raw_in_base = base_qa.get("included_file_sha256", {})
    entries = manifest.get("entries", [])
    if len(entries) != 20:
        raise RuntimeError(f"expected 20 component plots in {scope}, found {len(entries)}")
    expected_runs = {"N0_00", "N1_01", "N1_10", "N2_11"}
    specs: list[dict[str, Any]] = []
    for component in ("BVM", "QB", "CB", "ACC", "GAP"):
        selected = [item for item in entries if item.get("component") == component]
        if {item.get("run_id") for item in selected} != expected_runs or len(selected) != 4:
            raise RuntimeError(f"component plot coverage mismatch for {component}")
        raw_by_run = {}
        sources: list[tuple[Path, str]] = [
            (manifest_path, "analysis/component_plot_manifest_v1.json"),
            (qa_path, "qa/component_plot_qa_v1.json"),
            (scope / "scripts" / "plot_components.py", "scripts/plot_components.py"),
            (scope / "plots" / "assets" / "plotly.min.js", "plots/assets/plotly.min.js"),
        ]
        for item in selected:
            html_path = scope / item["path"]
            if not html_path.is_file() or sha256(html_path) != item["sha256"]:
                raise RuntimeError(f"component plot hash mismatch: {item['path']}")
            sources.append((html_path, item["path"]))
            run_id = item["run_id"]
            raw_path = scope / item["raw_path"]
            if sha256(raw_path) != item["raw_sha256"] or raw_in_base.get(f"runs/{run_id}/raw.csv") != item["raw_sha256"]:
                raise RuntimeError(f"component raw does not match base ZIP/plot manifest: {run_id}")
            raw_by_run[run_id] = item["raw_sha256"]
        package_name = f"{scope.name}_component_{component}_{tag}.zip"
        target = scope / "handoff" / package_name
        qa_target = scope / "handoff" / f"{scope.name}_component_{component}_{tag}_PACKAGE_QA.json"
        index_bytes = component_index(component, selected)
        readme = (f"{component} full-run component plots; 0-199.99 ps, actual stored samples only.\n"
                  f"Base raw handoff SHA-256: {base_qa['package_sha256']}\n"
                  "No raw CSVs are duplicated; exact raw paths/hashes are recorded in the embedded manifest.\n"
                  "Rendered by classic josim-plot2.py; no scientific interpretation.\n").encode("utf-8")
        specs.append({"name": package_name, "kind": "component_views_delta", "scope": scope,
                      "target": target, "qa_path": qa_target, "sources": sources,
                      "extra_members": {"COMPONENT_INDEX.html": index_bytes},
                      "readme": readme,
                      "base_name": base_zip.name, "base_sha": base_qa["package_sha256"],
                      "raw_by_run": raw_by_run, "component": component})
    return specs


def component_index(component: str, entries: list[dict[str, Any]]) -> bytes:
    links = []
    for item in sorted(entries, key=lambda value: value["run_id"]):
        path = html.escape(item["path"])
        run_id = html.escape(item["run_id"])
        mask = html.escape(item.get("mask") or item["run_id"].split("_")[-1])
        links.append(f"<li><a href='{path}'>{run_id} / mask {mask}</a></li>")
    body = ("<!doctype html><html><head><meta charset='utf-8'><title>" + html.escape(component) +
            " full-run component views</title></head><body><h1>" + html.escape(component) +
            " full-run component views</h1><p>Complete stored time range only; classic josim-plot2. "
            "P is radians; -j 2pi is navigation only, not SFQ count.</p><ul>" +
            "\n".join(links) + "</ul></body></html>\n")
    return body.encode("utf-8")


def snapshot_bundle_spec(scope: Path, tag: str, base_qa: dict[str, Any]) -> dict[str, Any] | None:
    candidates = sorted((scope / "runs" / "N1_10").glob("snapshot*.zip"))
    if not candidates:
        return None
    raw_hash = base_qa.get("included_file_sha256", {}).get("runs/N1_10/raw.csv")
    if not raw_hash:
        raise RuntimeError("canonical package has no N1_10 raw identity for snapshot attachments")
    sources = [(path, path.relative_to(scope).as_posix()) for path in candidates]
    target = scope / "handoff" / f"{scope.name}_N1_10_snapshots_{tag}.zip"
    qa_path = scope / "handoff" / f"{scope.name}_N1_10_snapshots_{tag}_PACKAGE_QA.json"
    return {"name": target.name, "kind": "source_snapshot_attachments", "scope": scope,
            "target": target, "qa_path": qa_path, "sources": sources,
            "extra_members": {},
            "readme": (
                f"N1_10 source snapshot ZIP attachments, preserved exactly.\n"
                f"Base raw handoff SHA-256: {base_qa['package_sha256']}\n"
                f"N1_10 raw SHA-256: {raw_hash}\nNo new simulation or interpretation.\n").encode("utf-8"),
            "base_name": Path(base_qa["package_path"]).name,
            "base_sha": base_qa["package_sha256"], "raw_by_run": {"N1_10": raw_hash}}


def legacy_oversize(scope: Path) -> tuple[Path, Path] | None:
    package = scope / "handoff" / f"{scope.name}_component_views_v1.zip"
    qa_path = scope / "handoff" / f"{scope.name}_component_views_v1_PACKAGE_QA.json"
    if not package.exists() and not qa_path.exists():
        return None
    if not package.is_file() or not qa_path.is_file():
        raise RuntimeError(f"incomplete generated aggregate package pair: {package}")
    qa = json.loads(qa_path.read_text(encoding="utf-8"))
    expected_paths = {rel(package), package.relative_to(scope).as_posix()}
    if (qa.get("status") != "PASS" or qa.get("package_path") not in expected_paths or
            qa.get("package_sha256") != sha256(package)):
        raise RuntimeError(f"generated aggregate package QA/hash invalid: {package}")
    if qa.get("bundle_type") != "component_views_supplement":
        raise RuntimeError(f"refusing to retire a package with an unexpected bundle type: {package}")
    if package.stat().st_size < MAX_GIT_FILE_BYTES:
        return None
    if git(["ls-files", "--error-unmatch", rel(package)], check=False).returncode == 0:
        raise RuntimeError(f"refusing to retire a tracked package: {package}")
    return package, qa_path


def parse_component_metadata(scope: Path, base_qa: dict[str, Any]) -> list[dict[str, Any]]:
    component_manifest = scope / "analysis" / "component_plot_manifest_v1.json"
    if not component_manifest.is_file():
        return []
    return component_bundle_specs(scope, json.loads(component_manifest.read_text(encoding="utf-8")))


def build_generic_snapshot(scope: Path, tag: str, *, exclude_html: bool = False) -> dict[str, Any]:
    sources = []
    excluded_files = []
    for path in sorted(scope.rglob("*")):
        if not path.is_file() or path.is_symlink() or "handoff" in path.relative_to(scope).parts or "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        if exclude_html and path.suffix.lower() == ".html":
            excluded_files.append(path.relative_to(scope).as_posix())
            continue
        sources.append((path, path.relative_to(scope).as_posix()))
    target = scope / "handoff" / f"{scope.name}_snapshot_{tag}.zip"
    qa_path = scope / "handoff" / f"{scope.name}_snapshot_{tag}_PACKAGE_QA.json"
    return {"name": target.name, "kind": "directory_snapshot", "scope": scope,
            "target": target, "qa_path": qa_path, "sources": sources,
            "extra_members": {},
            "readme": (
                f"Byte-preserving snapshot of {scope.name}.\n"
                + ("Generated HTML was explicitly excluded by --exclude-html; local HTML files were left untouched.\n"
                   if exclude_html else "")
                + "Archive integrity and member hashes are checked; this package does not certify\n"
                + "solver identity, raw semantics, or scientific validity.\n").encode("utf-8"),
            "excluded_files": excluded_files,
            "base_name": None, "base_sha": None, "raw_by_run": {}}


def latest_generic_snapshot(scope: Path, ancestor: str) -> tuple[Path, Path, dict[str, Any]] | None:
    """Select the newest QA-passed full snapshot reachable from the current upstream."""
    candidates = []
    for package in sorted((scope / "handoff").glob(f"{scope.name}_snapshot_*.zip")):
        qa_path = package.with_name(f"{package.stem}_PACKAGE_QA.json")
        qa = verify_existing_bundle(package, qa_path)
        if qa.get("bundle_type") != "directory_snapshot":
            continue
        source_commit = qa.get("source_commit")
        if not source_commit or git(["merge-base", "--is-ancestor", source_commit, ancestor], check=False).returncode:
            continue
        distance = int(git(["rev-list", "--count", f"{source_commit}..{ancestor}"]).stdout.strip())
        candidates.append((distance, package, qa_path, qa))
    if not candidates:
        return None
    nearest = min(item[0] for item in candidates)
    newest = [item for item in candidates if item[0] == nearest]
    if len({item[3]["package_sha256"] for item in newest}) > 1:
        raise RuntimeError(f"ambiguous newest full-snapshot base packages in {scope}")
    _, package, qa_path, qa = sorted(newest, key=lambda item: item[1].name)[0]
    return package, qa_path, qa


def _git_blob_sha256(commit: str, repo_path: str) -> str | None:
    result = subprocess.run(["git", "show", f"{commit}:{repo_path}"], cwd=REPO,
                            capture_output=True, check=False)
    if result.returncode:
        return None
    return hashlib.sha256(result.stdout).hexdigest()


def _delta_source_checkpoint(scope: Path, base_package: Path, base_qa: dict[str, Any],
                             head_commit: str, package_set: list[dict[str, Any]],
                             *, ancestor: str) -> dict[str, Any]:
    hashes, raw_sources, deleted = _compose_delta_layers(base_package, base_qa, package_set)
    full_commit = base_qa["source_commit"]
    changes = committed_changes(full_commit, head_commit)
    for repo_path, status in changes.items():
        if (not in_scope(repo_path, [scope]) or is_package_output(repo_path, [scope]) or
                generated_cache_path(repo_path)):
            continue
        member = Path(repo_path).relative_to(scope.relative_to(REPO)).as_posix()
        if status == "D":
            if member not in deleted:
                raise RuntimeError(f"previous delta checkpoint omits deleted member: {member}")
            continue
        expected = _git_blob_sha256(head_commit, repo_path)
        if expected is None or hashes.get(member) != expected:
            raise RuntimeError(f"previous delta checkpoint does not cover committed member/hash: {repo_path}")
    if git(["merge-base", "--is-ancestor", head_commit, ancestor], check=False).returncode:
        raise RuntimeError(f"delta checkpoint head is not an ancestor of upstream: {head_commit}")
    return {"head_commit": head_commit, "base_hashes": hashes, "raw_sources": raw_sources,
            "deleted_files": deleted, "base_delta_packages": package_set}


def latest_generic_delta_checkpoint(scope: Path, base_package: Path, base_qa: dict[str, Any],
                                    ancestor: str) -> dict[str, Any]:
    """Return the newest complete QA-passed delta set layered over a full snapshot."""
    groups: dict[str, list[tuple[Path, dict[str, Any], dict[str, Any]]]] = {}
    for package in sorted((scope / "handoff").glob(f"{scope.name}_delta_*.zip")):
        qa_path = package.with_name(f"{package.stem}_PACKAGE_QA.json")
        qa = verify_existing_bundle(package, qa_path)
        if qa.get("bundle_type") != "directory_snapshot_delta":
            continue
        manifest = _read_delta_manifest(package)
        if (manifest.get("base_package_name") != base_package.name or
                manifest.get("base_package_sha256") != base_qa.get("package_sha256") or
                manifest.get("base_commit") != base_qa.get("source_commit")):
            continue
        checkpoint_head = manifest.get("head_commit")
        if not checkpoint_head or qa.get("head_commit") != checkpoint_head:
            raise RuntimeError(f"delta QA head does not match its manifest: {package}")
        if git(["merge-base", "--is-ancestor", checkpoint_head, ancestor], check=False).returncode:
            continue
        for package_file in (package, qa_path):
            if git(["cat-file", "-e", f"{ancestor}:{rel(package_file)}"], check=False).returncode:
                raise RuntimeError(f"delta checkpoint artifact is not committed at upstream: {package_file}")
        groups.setdefault(checkpoint_head, []).append((package, qa, manifest))
    if not groups:
        return {"head_commit": base_qa["source_commit"],
                "base_hashes": _source_hashes_from_qa(base_qa),
                "raw_sources": {
                    path: {"source_package_name": base_package.name,
                           "source_package_sha256": base_qa["package_sha256"]}
                    for path in _source_hashes_from_qa(base_qa) if path.endswith("raw.csv")},
                "deleted_files": set(), "base_delta_packages": []}

    distance_by_head = {
        commit: int(git(["rev-list", "--count", f"{commit}..{ancestor}"]).stdout.strip())
        for commit in groups
    }
    nearest_distance = min(distance_by_head.values())
    newest = [commit for commit, distance in distance_by_head.items() if distance == nearest_distance]
    if len(newest) != 1:
        raise RuntimeError(f"ambiguous newest delta checkpoint heads in {scope}: {sorted(newest)}")
    head_commit = newest[0]
    selected = sorted(groups[head_commit], key=lambda item: item[0].name)
    inherited_sets = [item[2].get("base_delta_packages") or [] for item in selected]
    inherited_heads = [item[2].get("prior_delta_head_commit") for item in selected]
    if any(value != inherited_sets[0] for value in inherited_sets[1:]) or any(
            value != inherited_heads[0] for value in inherited_heads[1:]):
        raise RuntimeError(f"delta packages at {head_commit} disagree on their prior checkpoint")
    inherited = list(inherited_sets[0])
    current_entries = [{"package_name": package.name, "package_sha256": qa["package_sha256"],
                        "head_commit": head_commit}
                       for package, qa, _ in selected]
    package_set = inherited + current_entries
    seen_names = [entry["package_name"] for entry in package_set]
    if len(seen_names) != len(set(seen_names)):
        raise RuntimeError(f"delta checkpoint repeats a package identity in {scope}")
    prior_head = inherited_heads[0]
    if inherited and prior_head != inherited[-1]["head_commit"]:
        raise RuntimeError(f"delta checkpoint prior-head metadata is inconsistent in {scope}")
    if not inherited and prior_head is not None:
        raise RuntimeError(f"delta checkpoint names a prior head but no prior packages in {scope}")
    return _delta_source_checkpoint(scope, base_package, base_qa, head_commit,
                                    package_set, ancestor=ancestor)


def classify_delta_members(current: list[dict[str, Any]], base_hashes: dict[str, str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    """Return added, modified, and removed paths by comparing scope-relative hashes."""
    current_by_path = {item["archive_path"]: item for item in current}
    added = [item for path, item in current_by_path.items() if path not in base_hashes]
    modified = [item for path, item in current_by_path.items()
                if path in base_hashes and item["sha256"] != base_hashes[path]]
    removed = sorted(path for path in base_hashes
                     if path not in {"BUNDLE_MANIFEST.json", "README_BUNDLE.txt"} and path not in current_by_path)
    return (sorted(added, key=lambda item: item["archive_path"]),
            sorted(modified, key=lambda item: item["archive_path"]), removed)


def delta_group(path: str) -> str:
    parts = Path(path).parts
    if len(parts) >= 3 and parts[0] == "runs":
        return parts[1]
    return "metadata"


def build_generic_delta_specs(scope: Path, tag: str, base_package: Path, base_qa: dict[str, Any],
                              *, exclude_html: bool = False,
                              checkpoint: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    current_sources: list[tuple[Path, str]] = []
    excluded_files = []
    for path in sorted(scope.rglob("*")):
        relative = path.relative_to(scope)
        if (not path.is_file() or path.is_symlink() or "handoff" in relative.parts or
                "__pycache__" in relative.parts or path.suffix == ".pyc"):
            continue
        if exclude_html and path.suffix.lower() == ".html":
            excluded_files.append(relative.as_posix())
            continue
        current_sources.append((path, relative.as_posix()))

    current_records = file_records(current_sources)
    base_hashes = (checkpoint["base_hashes"] if checkpoint else
                   _source_hashes_from_qa(base_qa))
    raw_sources = (checkpoint["raw_sources"] if checkpoint else {
        path: {"source_package_name": base_package.name,
               "source_package_sha256": base_qa["package_sha256"]}
        for path in base_hashes if path.endswith("raw.csv")})
    prior_delta_packages = checkpoint["base_delta_packages"] if checkpoint else []
    prior_delta_head = checkpoint["head_commit"] if prior_delta_packages else None
    added, modified, removed = classify_delta_members(current_records, base_hashes)
    deleted_raw = [path for path in removed if path.startswith("runs/") and path.endswith("/raw.csv")]
    if deleted_raw:
        raise RuntimeError("refusing to package a deletion of historical raw evidence: " + ", ".join(deleted_raw))
    for item in modified:
        if item["archive_path"].startswith("runs/") and item["archive_path"].endswith("/raw.csv"):
            raise RuntimeError(f"refusing to package a modified historical raw: {item['archive_path']}")
    if not added and not modified and not removed:
        return []

    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in added + modified:
        grouped.setdefault(delta_group(item["archive_path"]), []).append(item)
    references = []
    for raw_path, source in sorted(raw_sources.items()):
        digest = base_hashes.get(raw_path)
        if digest is not None:
            references.append({"raw_path": raw_path, "raw_sha256": digest,
                               **source})

    specs = []
    for group, items in sorted(grouped.items()):
        sources = [(REPO / item["source_repo_path"], item["archive_path"]) for item in items]
        payload_bytes = sum(item["bytes"] for item in items)
        if payload_bytes >= MAX_GIT_FILE_BYTES:
            raise RuntimeError(f"delta group exceeds the 100MB safety threshold; split further: {group} ({payload_bytes} bytes)")
        included_hashes = {item["archive_path"]: item["sha256"] for item in items}
        new_files = [item["archive_path"] for item in items if item["archive_path"] not in base_hashes]
        modified_files = [item["archive_path"] for item in items if item["archive_path"] in base_hashes]
        run_ids = sorted({Path(item["archive_path"]).parts[1] for item in items
                          if len(Path(item["archive_path"]).parts) >= 3 and Path(item["archive_path"]).parts[0] == "runs"})
        physical_solves = 0
        for run_id in run_ids:
            result_path = scope / "runs" / run_id / "result.json"
            raw_path = scope / "runs" / run_id / "raw.csv"
            if raw_path.is_file() and "runs/" + run_id + "/raw.csv" in included_hashes and result_path.is_file():
                result = json.loads(result_path.read_text(encoding="utf-8"))
                physical_solves += int(result.get("physical_solve_count", 0))

        package_name = f"{scope.name}_delta_{tag}_{group}.zip"
        target = scope / "handoff" / package_name
        qa_target = scope / "handoff" / f"{scope.name}_delta_{tag}_{group}_PACKAGE_QA.json"
        manifest = {
            "schema": "josim-submit-delta-v1",
            "package_type": "directory_snapshot_delta",
            "base_package_name": base_package.name,
            "base_package_sha256": base_qa["package_sha256"],
            "base_commit": base_qa["source_commit"],
            "prior_delta_head_commit": prior_delta_head,
            "base_delta_packages": prior_delta_packages,
            "head_commit": "PENDING_SOURCE_COMMIT",
            "included_files": items,
            "included_file_sha256": included_hashes,
            "new_files": new_files,
            "modified_files": modified_files,
            "deleted_files": removed,
            "referenced_existing_cases": references,
            "referenced_existing_raw_sha256": references,
            "new_physical_solve_count": physical_solves,
            "reused_point_count": 0,
            "excluded_files": excluded_files,
        }
        delta_bytes = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        readme = (f"Incremental evidence for {scope.name}; group={group}.\n"
                  f"Base package: {base_package.name} ({base_qa['package_sha256']})\n"
                  f"Full-base commit: {base_qa['source_commit']}\n"
                  + (f"Prior delta checkpoint: {prior_delta_head}; {len(prior_delta_packages)} package(s).\n"
                     if prior_delta_packages else "No prior delta checkpoint.\n")
                  + "Only new/modified evidence is included; unchanged evidence is hash-referenced.\n"
                  + ("Generated HTML was explicitly excluded and remains local.\n" if exclude_html else "")
                  + "No solver execution or scientific interpretation was performed by this package step.\n").encode("utf-8")
        specs.append({"name": package_name, "kind": "directory_snapshot_delta", "scope": scope,
                      "target": target, "qa_path": qa_target, "sources": sources,
                      "extra_members": {"DELTA_MANIFEST.json": delta_bytes},
                      "readme": readme, "excluded_files": excluded_files,
                      "base_name": base_package.name, "base_sha": base_qa["package_sha256"],
                      "base_delta_packages": prior_delta_packages,
                      "prior_delta_head_commit": prior_delta_head,
                      "raw_by_run": {Path(item["archive_path"]).parts[1]: included_hashes[item["archive_path"]]
                                     for item in items if item["archive_path"].endswith("/raw.csv")},
                      "delta_manifest": manifest, "delta_group": group})
    if removed and not grouped:
        raise RuntimeError("delta contains only deletions; refusing an empty evidence archive")
    return specs


def package_specs(scopes: list[Path], tag: str, retire_flag: bool, *,
                  exclude_html: bool = False) -> tuple[list[dict[str, Any]], list[tuple[Path, Path]]]:
    specs: list[dict[str, Any]] = []
    retire: list[tuple[Path, Path]] = []
    remote_commit = git(["rev-parse", upstream()]).stdout.strip()
    changes = scoped_delta(remote_commit, head(), scopes)
    for scope in scopes:
        existing = source_bundle_candidates(scope)
        if existing:
            for package in existing:
                qa_path = package.with_name(f"{package.stem}_PACKAGE_QA.json")
                verify_existing_bundle(package, qa_path)
                specs.append({"name": package.name, "kind": "prebuilt_bundle_reuse", "scope": scope,
                              "target": package, "qa_path": qa_path, "existing": True})

        plot_manifest = scope / "analysis" / "component_plot_manifest_v1.json"
        if plot_manifest.is_file():
            base_qa = json.loads((scope / "handoff" / "PACKAGE_QA.json").read_text(encoding="utf-8"))
            component_specs = component_bundle_specs(scope, tag)
            specs.extend(component_specs)
            snapshot_spec = snapshot_bundle_spec(scope, tag, base_qa)
            if snapshot_spec:
                specs.append(snapshot_spec)
            old = legacy_oversize(scope)
            if old:
                if not retire_flag:
                    raise RuntimeError(f"over-limit aggregate requires explicit replacement authorization: {old[0]}")
                retire.append(old)
        elif scope_has_source_changes(scope, changes) or not existing:
            specs.append(build_generic_snapshot(scope, tag, exclude_html=exclude_html))
    return specs, retire


def source_status_paths(scopes: list[Path]) -> list[str]:
    paths = []
    for rel_path, status in working_changes().items():
        if status == "??":
            continue
        if not any((REPO / rel_path).resolve() == scope or scope in (REPO / rel_path).resolve().parents for scope in scopes):
            continue
        if package_output_path(rel_path):
            continue
        paths.append(rel_path)
    for rel_path in untracked_files():
        if generated_cache_path(rel_path):
            continue
        if not any((REPO / rel_path).resolve() == scope or scope in (REPO / rel_path).resolve().parents for scope in scopes):
            continue
        if package_output_path(rel_path):
            continue
        paths.append(rel_path)
    return sorted(set(paths))


def package_output_path(rel_path: str) -> bool:
    path = Path(rel_path)
    if "handoff" not in path.parts:
        return False
    return path.suffix.lower() == ".zip" or path.name == "PACKAGE_QA.json" or "PACKAGE_QA" in path.name


def mirror_collision(path: Path, mirror_dir: Path) -> bool:
    target = mirror_dir / path.name
    return target.exists() and sha256(target) != sha256(path)


def bundle_plan(scopes: list[Path], specs: list[dict[str, Any]], retire: list[tuple[Path, Path]]) -> dict[str, Any]:
    source_paths = source_status_paths(scopes)
    package_plan = []
    for spec in specs:
        if spec.get("existing"):
            package_plan.append({"path": rel(spec["target"]), "status": "REUSE_QA_PASS",
                                 "bytes": spec["target"].stat().st_size})
            continue
        if spec["target"].exists() or spec["qa_path"].exists():
            raise FileExistsError(f"refusing to overwrite immutable package/QA target: {spec['target']}")
        records = file_records(spec["sources"])
        source_bytes = sum(item["bytes"] for item in records)
        if source_bytes >= MAX_GIT_FILE_BYTES:
            raise RuntimeError(f"bundle inputs exceed the 100MB safety threshold; split the scope: {spec['name']} ({source_bytes} bytes)")
        package_plan.append({"path": rel(spec["target"]), "status": "CREATE", "file_count": len(records)+len(spec.get("extra_members", {}))+2,
                             "uncompressed_source_bytes": source_bytes,
                             "excluded_files": spec.get("excluded_files", []),
                             "base_package_name": spec.get("base_name"),
                             "base_package_sha256": spec.get("base_sha"),
                             "prior_delta_head_commit": spec.get("prior_delta_head_commit"),
                             "base_delta_packages": spec.get("base_delta_packages", []),
                             "delta_group": spec.get("delta_group"),
                             "qa_path": rel(spec["qa_path"])})
    return {"source_paths": source_paths, "packages": package_plan,
            "retire": [rel(pkg) for pkg, _ in retire]}


def file_records(sources: list[tuple[Path, str]]) -> list[dict[str, Any]]:
    records = []
    seen = set()
    for source, member in sources:
        if member in seen:
            raise RuntimeError(f"duplicate package member: {member}")
        seen.add(member)
        if not source.is_file() or source.is_symlink():
            raise RuntimeError(f"missing/non-regular bundle input: {source}")
        records.append({"source_repo_path": rel(source), "archive_path": member,
                        "sha256": sha256(source), "bytes": source.stat().st_size})
    return records


def archive_bundle(spec: dict[str, Any], source_commit: str) -> dict[str, Any]:
    target, qa_path = spec["target"], spec["qa_path"]
    if target.exists() or qa_path.exists():
        if target.is_file() and qa_path.is_file():
            qa = verify_existing_bundle(target, qa_path)
            return {"path": rel(target), "qa_path": rel(qa_path), "sha256": qa["package_sha256"],
                    "bytes": qa["package_bytes"], "status": "REUSE_QA_PASS"}
        raise FileExistsError(f"refusing to overwrite incomplete/immutable bundle: {target}")
    records = file_records(spec["sources"])
    extras = dict(spec.get("extra_members", {}))
    if "DELTA_MANIFEST.json" in extras:
        delta_manifest = dict(spec["delta_manifest"])
        delta_manifest["head_commit"] = source_commit
        extras["DELTA_MANIFEST.json"] = (json.dumps(delta_manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    if sum(item["bytes"] for item in records) + sum(len(value) for value in extras.values()) >= MAX_GIT_FILE_BYTES:
        raise RuntimeError(f"bundle exceeds ordinary Git size threshold before compression: {spec['name']}")
    base_name, base_sha = spec.get("base_name"), spec.get("base_sha")
    raw_by_run = spec.get("raw_by_run", {})
    internal_manifest = "BUNDLE_MANIFEST.json"
    internal_readme = "README_BUNDLE.txt"
    manifest = {"schema": "josim-submit-bundle-v1", "bundle_name": spec["name"],
                "bundle_type": spec["kind"], "source_commit": source_commit,
                "parent_package_name": base_name, "parent_package_sha256": base_sha,
                "raw_sha256_by_run": raw_by_run,
                "scientific_interpretation_performed": False,
                "excluded_files": spec.get("excluded_files", []),
                "included_files": records,
                "additional_members": {name: hashlib.sha256(data).hexdigest() for name, data in extras.items()}}
    if spec.get("readme") is not None:
        readme = spec["readme"]
    elif spec["kind"] == "component_views_delta":
        readme = (f"Full-run {spec['component']} component plots.\nBase raw handoff SHA-256: {base_sha}\n"
                  "All raw samples are in the referenced base handoff; this bundle contains plots, QA, and renderer.\n"
                  "No new simulation or scientific interpretation.\n").encode("utf-8")
    else:
        readme = (f"Workspace package: {spec['name']}\nBase package: {base_name or 'none'}\n"
                  "Exact member hashes are in BUNDLE_MANIFEST.json. No simulation or scientific interpretation.\n").encode("utf-8")
    manifest_bytes = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(prefix=f".{target.stem}.", suffix=".tmp", dir=target.parent, delete=False) as stream:
        temp_path = Path(stream.name)
    try:
        with zipfile.ZipFile(temp_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            for record, (source, _) in zip(records, spec["sources"], strict=True):
                archive.write(source, record["archive_path"])
            for name, data in extras.items():
                archive.writestr(name, data)
            archive.writestr(internal_manifest, manifest_bytes)
            archive.writestr(internal_readme, readme)
        if temp_path.stat().st_size >= MAX_GIT_FILE_BYTES:
            raise RuntimeError(f"compressed bundle exceeds GitHub 100MB hard limit: {spec['name']} ({temp_path.stat().st_size} bytes)")
        with zipfile.ZipFile(temp_path, "r") as archive:
            if archive.testzip() is not None:
                raise RuntimeError(f"ZIP CRC failure: {spec['name']}")
            expected = {item["archive_path"] for item in records} | set(extras) | {internal_manifest, internal_readme}
            if set(archive.namelist()) != expected:
                raise RuntimeError(f"ZIP member closure mismatch: {spec['name']}")
            included_hashes = {}
            for record in records:
                data = archive.read(record["archive_path"])
                digest = hashlib.sha256(data).hexdigest()
                if digest != record["sha256"] or len(data) != record["bytes"]:
                    raise RuntimeError(f"ZIP member hash mismatch: {record['archive_path']}")
                included_hashes[record["archive_path"]] = digest
            for name, data in extras.items():
                packed = archive.read(name)
                if packed != data:
                    raise RuntimeError(f"ZIP extra member mismatch: {name}")
                included_hashes[name] = hashlib.sha256(data).hexdigest()
            included_hashes[internal_manifest] = hashlib.sha256(archive.read(internal_manifest)).hexdigest()
            included_hashes[internal_readme] = hashlib.sha256(archive.read(internal_readme)).hexdigest()
        os.link(temp_path, target)
    finally:
        temp_path.unlink(missing_ok=True)
    qa = {"schema": "josim-submit-package-qa-v1", "status": "PASS",
          "bundle_name": spec["name"], "bundle_type": spec["kind"],
          "package_path": rel(target), "package_sha256": sha256(target),
          "package_bytes": target.stat().st_size, "file_count": len(included_hashes),
          "source_commit": source_commit, "parent_package_name": base_name,
          "parent_package_sha256": base_sha, "raw_sha256_by_run": raw_by_run,
          "included_file_sha256": included_hashes,
          "reopened_zip_crc_and_member_hashes_pass": True}
    if spec.get("delta_manifest"):
        qa.update({key: spec["delta_manifest"][key] for key in (
            "base_package_name", "base_package_sha256", "base_commit", "new_files",
            "modified_files", "deleted_files", "referenced_existing_raw_sha256",
            "new_physical_solve_count", "reused_point_count")})
        qa["prior_delta_head_commit"] = spec["delta_manifest"].get("prior_delta_head_commit")
        qa["base_delta_packages"] = spec["delta_manifest"].get("base_delta_packages", [])
        qa["head_commit"] = source_commit
    qa_path.write_text(json.dumps(qa, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"path": rel(target), "qa_path": rel(qa_path), "sha256": qa["package_sha256"],
            "bytes": qa["package_bytes"], "status": qa["status"]}


def check_existing_component_package(qa_path: Path, target: Path) -> dict[str, Any]:
    qa = verify_existing_bundle(target, qa_path)
    return {"path": rel(target), "qa_path": rel(qa_path), "sha256": qa["package_sha256"],
            "bytes": qa["package_bytes"], "status": "REUSE_QA_PASS"}


def retire_overlimit_aggregate(scope: Path, retire: list[tuple[Path, Path]], enabled: bool) -> list[str]:
    if not retire:
        return []
    if not enabled:
        raise RuntimeError("over-limit generated aggregate exists; rerun with --retire-overlimit-generated after split bundles pass QA")
    retired = []
    for package, qa_path in retire:
        qa = json.loads(qa_path.read_text(encoding="utf-8"))
        if qa.get("status") != "PASS" or qa.get("package_sha256") != sha256(package) or package.stat().st_size < MAX_GIT_FILE_BYTES:
            raise RuntimeError(f"aggregate does not match exact authorized retirement conditions: {package}")
        package.unlink()
        qa_path.unlink()
        retired.extend([rel(package), rel(qa_path)])
    return retired


def copy_mirror(packages: list[Path], mirror_dir: Path) -> list[dict[str, Any]]:
    mirror_dir.mkdir(parents=True, exist_ok=True)
    copied = []
    for package in packages:
        target = mirror_dir / package.name
        source_hash = sha256(package)
        if target.exists():
            if sha256(target) != source_hash:
                raise RuntimeError(f"Drive mirror name collision with different bytes: {target}")
            copied.append({"path": str(target), "sha256": source_hash, "status": "ALREADY_MATCHES"})
            continue
        shutil.copy2(package, target)
        mirror_hash = sha256(target)
        if mirror_hash != source_hash:
            raise RuntimeError(f"Drive mirror SHA mismatch: {target}")
        copied.append({"path": str(target), "sha256": mirror_hash, "status": "COPIED"})
    return copied


def verify_mirror_targets(packages: list[Path], mirror_dir: Path) -> None:
    if not mirror_dir.is_dir():
        raise RuntimeError(f"Drive mirror directory is not accessible: {mirror_dir}")
    for package in packages:
        target = mirror_dir / package.name
        if target.exists() and sha256(target) != sha256(package):
            raise RuntimeError(f"Drive mirror name collision with different bytes: {target}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Submit scoped JoSIM changes using one-shot commit/package/push stages")
    parser.add_argument("--tag", required=True)
    parser.add_argument("--scope", action="append", help="repository-relative experiment directory; repeatable; default auto-detects")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-push", action="store_true", help="commit and package locally, skip push and Drive mirror")
    parser.add_argument("--message", help="source commit message")
    parser.add_argument("--retire-overlimit-generated", action="store_true",
                        help="remove the exact uncommitted oversized aggregate after QA-passed split packages exist")
    parser.add_argument("--exclude-html", action="store_true",
                        help="for generic snapshots only, exclude generated .html files while leaving them untouched locally")
    parser.add_argument("--mirror-dir", default=str(MIRROR_DEFAULT))
    args = parser.parse_args()
    if not TAG_RE.fullmatch(args.tag):
        raise RuntimeError(f"invalid submission tag: {args.tag!r}")

    remote = upstream()
    remote_commit = git(["rev-parse", remote]).stdout.strip()
    scopes = normalize_scopes(args.scope, remote_commit, head())
    local_submit_scopes = [scope for scope in scopes if (scope / "scripts" / "submit.py").is_file()]
    if local_submit_scopes:
        if args.exclude_html:
            raise RuntimeError("--exclude-html is implemented for generic snapshots; use the scope's local submit workflow")
        if len(scopes) != 1:
            raise RuntimeError("a scope with its own submit.py must be submitted separately")
        local = local_submit_scopes[0] / "scripts" / "submit.py"
        command = [sys.executable, str(local), args.tag]
        if args.dry_run:
            command.append("--dry-run")
        if args.no_push:
            command.append("--no-push")
        if args.message:
            command.extend(["--message", args.message])
        return subprocess.run(command, cwd=REPO).returncode

    changes = scoped_delta(remote_commit, head(), scopes)
    work_paths = source_stage_paths(scopes)
    if work_paths and rel(Path(__file__)) not in work_paths:
        work_paths.append(rel(Path(__file__)))
    assert_no_pre_staged_outside(set(work_paths))
    specs: list[dict[str, Any]] = []
    retire_candidates: list[tuple[Path, Path]] = []
    reused_packages: list[dict[str, Any]] = []
    for scope in scopes:
        prebuilt = source_bundle_candidates(scope)
        if prebuilt:
            for package in prebuilt:
                qa_path = package.with_name(package.stem + "_PACKAGE_QA.json")
                reused_packages.append({"path": rel(package), "qa_path": rel(qa_path),
                                        "sha256": verify_existing_bundle(package, qa_path)["package_sha256"],
                                        "bytes": package.stat().st_size})
        manifest = scope / "analysis" / "component_plot_manifest_v1.json"
        if manifest.is_file():
            base_qa = json.loads((scope / "handoff" / "PACKAGE_QA.json").read_text(encoding="utf-8"))
            specs.extend(component_bundle_specs(scope, args.tag))
            snapshot_spec = snapshot_bundle_spec(scope, args.tag, base_qa)
            if snapshot_spec:
                specs.append(snapshot_spec)
            old = legacy_oversize(scope)
            if old:
                retire_candidates.append(old)
        elif scope_has_source_changes(scope, changes) or not prebuilt:
            base = latest_generic_snapshot(scope, remote_commit)
            if base:
                base_package, _, base_qa = base
                checkpoint = latest_generic_delta_checkpoint(
                    scope, base_package, base_qa, remote_commit)
                specs.extend(build_generic_delta_specs(scope, args.tag, base_package, base_qa,
                                                       exclude_html=args.exclude_html,
                                                       checkpoint=checkpoint))
            else:
                specs.append(build_generic_snapshot(scope, args.tag, exclude_html=args.exclude_html))

    plans = bundle_plan(scopes, specs, retire_candidates)
    mirror_dir = Path(args.mirror_dir).expanduser().resolve()
    if args.dry_run:
        print(json.dumps({"status": "DRY_RUN_PASS", "tag": args.tag,
                          "branch": git(["branch", "--show-current"]).stdout.strip(),
                          "head": head(), "upstream": remote, "upstream_commit": remote_commit,
                          "scopes": [rel(path) for path in scopes],
                          "source_change_count": len(changes),
                          "source_changes": [{"status": changes[path], "path": path} for path in sorted(changes)],
                          "worktree_source_paths": work_paths,
                          "reused_packages": reused_packages,
                          "new_package_plan": plans["packages"],
                          "exclude_html": args.exclude_html,
                          "retired_overlimit_candidates": plans["retire"],
                          "retire_flag": args.retire_overlimit_generated,
                          "exclude_html": args.exclude_html,
                          "push": "SKIPPED" if args.no_push else remote,
                          "mirror_dir": str(mirror_dir), "no_files_modified": True},
                         ensure_ascii=False, indent=2))
        return 0

    # Source commit: stage only the explicitly scoped worktree changes and the global entry point.
    if work_paths:
        git(["add", "-A", "--", *work_paths], capture=False)
        if git(["diff", "--cached", "--quiet"], check=False).returncode != 0:
            message = args.message or f"experiment: submit {args.tag} additions"
            git(["commit", "-m", message], capture=False)
    source_commit = head()

    package_results: list[dict[str, Any]] = []
    package_paths: list[Path] = []
    for package in reused_packages:
        zip_path, qa_path = REPO / package["path"], REPO / package["qa_path"]
        verify_existing_bundle(zip_path, qa_path)
        package_paths.extend([zip_path, qa_path])
        package_results.append({**package, "status": "REUSE_QA_PASS"})
    for spec in specs:
        result = archive_bundle(spec, source_commit)
        package_paths.extend([spec["target"], spec["qa_path"]])
        package_results.append(result)

    retired = []
    for scope in scopes:
        old = legacy_oversize(scope)
        if old:
            retired.extend(retire_overlimit_aggregate(scope, [old], args.retire_overlimit_generated))

    if package_paths:
        unique_paths = sorted(set(package_paths))
        zip_paths = [path for path in unique_paths if path.suffix.lower() == ".zip"]
        if not args.no_push:
            verify_mirror_targets(zip_paths, mirror_dir)
        # Package paths are explicit; force-add is required for detached QA files
        # ignored by repository-wide patterns, without staging unrelated ignored data.
        git(["add", "-f", "--", *[rel(path) for path in unique_paths]], capture=False)
        if git(["diff", "--cached", "--quiet"], check=False).returncode != 0:
            git(["commit", "-m", f"package: archive {args.tag} additions"], capture=False)

    if not args.no_push:
        pushed = git(["push"], check=False, capture=False)
        if pushed.returncode != 0:
            print(json.dumps({"status": "LOCAL_COMPLETE_PUSH_FAILED", "head": head(),
                              "packages": package_results, "retired_generated_files": retired},
                             ensure_ascii=False, indent=2), file=sys.stderr)
            return 3
        mirror_results = copy_mirror([path for path in package_paths if path.suffix.lower() == ".zip"], mirror_dir)
    else:
        mirror_results = []

    print(json.dumps({"status": "SUBMIT_COMPLETE", "source_commit": source_commit,
                      "final_commit": head(), "packages": package_results,
                      "retired_generated_files": retired,
                      "push": "SKIPPED" if args.no_push else "PASS",
                      "mirror": mirror_results if not args.no_push else "PENDING_PUSH"},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
