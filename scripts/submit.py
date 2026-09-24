#!/usr/bin/env python3
"""Global submit workflow: scoped source commit -> QA'd bundles -> package commit -> optional push.

For a single scope that already owns scripts/submit.py, this command delegates to that
series-specific workflow. Otherwise it snapshots new directories, splits full component
plots into per-family bundles, and preserves the canonical raw handoff as the base.
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


def verify_existing_bundle(package: Path, qa_path: Path) -> dict[str, Any]:
    if not package.is_file() or not qa_path.is_file():
        raise RuntimeError(f"incomplete prebuilt bundle/QA pair: {package}")
    qa = json.loads(qa_path.read_text(encoding="utf-8"))
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


def build_generic_snapshot(scope: Path, tag: str) -> dict[str, Any]:
    sources = []
    for path in sorted(scope.rglob("*")):
        if not path.is_file() or path.is_symlink() or "handoff" in path.relative_to(scope).parts or "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        sources.append((path, path.relative_to(scope).as_posix()))
    target = scope / "handoff" / f"{scope.name}_snapshot_{tag}.zip"
    qa_path = scope / "handoff" / f"{scope.name}_snapshot_{tag}_PACKAGE_QA.json"
    return {"name": target.name, "kind": "directory_snapshot", "scope": scope,
            "target": target, "qa_path": qa_path, "sources": sources,
            "extra_members": {},
            "readme": (
                f"Byte-preserving snapshot of {scope.name}.\n"
                "Archive integrity and member hashes are checked; this package does not certify\n"
                "solver identity, raw semantics, or scientific validity.\n").encode("utf-8"),
            "base_name": None, "base_sha": None, "raw_by_run": {}}


def package_specs(scopes: list[Path], tag: str, retire_flag: bool) -> tuple[list[dict[str, Any]], list[tuple[Path, Path]]]:
    specs: list[dict[str, Any]] = []
    retire: list[tuple[Path, Path]] = []
    for scope in scopes:
        existing = sorted((scope / "handoff").glob("*_source_bundle_v1.zip")) if (scope / "handoff").is_dir() else []
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
        elif not existing:
            specs.append(build_generic_snapshot(scope, tag))
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
        records = file_records(spec["sources"])
        source_bytes = sum(item["bytes"] for item in records)
        if source_bytes >= MAX_GIT_FILE_BYTES:
            raise RuntimeError(f"bundle inputs exceed the 100MB safety threshold; split the scope: {spec['name']} ({source_bytes} bytes)")
        package_plan.append({"path": rel(spec["target"]), "status": "CREATE", "file_count": len(records)+len(spec.get("extra_members", {}))+2,
                             "uncompressed_source_bytes": source_bytes,
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
    extras = spec.get("extra_members", {})
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
    parser.add_argument("--mirror-dir", default=str(MIRROR_DEFAULT))
    args = parser.parse_args()
    if not TAG_RE.fullmatch(args.tag):
        raise RuntimeError(f"invalid submission tag: {args.tag!r}")

    remote = upstream()
    remote_commit = git(["rev-parse", remote]).stdout.strip()
    scopes = normalize_scopes(args.scope, remote_commit, head())
    local_submit_scopes = [scope for scope in scopes if (scope / "scripts" / "submit.py").is_file()]
    if local_submit_scopes:
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
        prebuilt = sorted((scope / "handoff").glob("*_source_bundle_v1.zip")) if (scope / "handoff").is_dir() else []
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
        elif not prebuilt:
            generic = build_generic_snapshot(scope, args.tag)
            specs.append(generic)

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
                          "retired_overlimit_candidates": plans["retire"],
                          "retire_flag": args.retire_overlimit_generated,
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
