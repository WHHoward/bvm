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
    "tests/test_component_render.py", "tests/test_evidence_package.py",
    "tests/test_plot_run.py", "tests/test_t1_output_mode.py",
    "tests/test_topology_render.py",
}
EXTERNAL_PLATFORM_PATHS = {
    "circuits/qb/BQ_0928.cir", "circuits/CB/CB_0928.cir",
}
EXTERNAL_EXPERIMENT_PATHS = {
    "test/exploration/t1-periodic-clock-20ghz-20260928",
}
CATEGORIES = (
    "raw", "plots", "run_manifests_qa", "source_snapshots", "batch_metadata",
    "platform_reproduction_metadata", "standalone_experiment_metadata", "other",
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
    try:
        relative = path.relative_to(SERIES)
    except ValueError:
        # The two explicitly managed 0928 canonical component sources live at
        # repository scope rather than below this experiment series.
        relative = path.relative_to(REPO)
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
    pathspecs = [rel(SERIES), *sorted(EXTERNAL_PLATFORM_PATHS),
                 *sorted(EXTERNAL_EXPERIMENT_PATHS)]
    result = subprocess.run(
        ["git", "status", "--short", "--untracked-files=all", "--", *pathspecs],
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
    raw = git("diff", "--name-status", base, head, "--", rel(SERIES),
              *sorted(EXTERNAL_PLATFORM_PATHS), *sorted(EXTERNAL_EXPERIMENT_PATHS))
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
    for experiment_root in EXTERNAL_EXPERIMENT_PATHS:
        prefix = experiment_root.rstrip("/") + "/"
        if repo_path.startswith(prefix):
            return repo_path
    return None


def _raw_case_id(raw_path: str) -> str:
    for experiment_root in EXTERNAL_EXPERIMENT_PATHS:
        prefix = experiment_root.rstrip("/") + "/runs/"
        if raw_path.startswith(prefix):
            return Path(raw_path[len(prefix):]).parts[0]
    return Path(raw_path).parts[1]


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
                is_run_raw = series_path.endswith("/raw.csv") and (
                    series_path.startswith("runs/")
                    or any(series_path.startswith(root.rstrip("/") + "/runs/")
                           for root in EXTERNAL_EXPERIMENT_PATHS)
                )
                if is_run_raw:
                    digest = file_hashes.get(member)
                    if isinstance(digest, str):
                        run_id = _raw_case_id(series_path)
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
                known_cases[_raw_case_id(raw_path)] = record
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
    for repo_path in sorted(EXTERNAL_PLATFORM_PATHS):
        source = REPO / repo_path
        if not source.is_file() or source.is_symlink():
            if mode == "full":
                raise RuntimeError(f"required canonical component source is missing: {repo_path}")
            continue
        if mode == "full" or repo_path in changes:
            members.append(PackageMember(source, repo_path,
                                         "platform_reproduction_metadata"))
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


def _standalone_experiment_members(
    mode: str, changes: dict[str, str], known_cases: dict[str, dict[str, str]],
    include_plots: bool,
) -> tuple[list[PackageMember], list[dict[str, Any]], list[dict[str, Any]],
           list[dict[str, str]], dict[str, str]]:
    members: list[PackageMember] = []
    experiments: list[dict[str, Any]] = []
    runs: list[dict[str, Any]] = []
    references: list[dict[str, str]] = []
    statuses: dict[str, str] = {}

    for root_relative in sorted(EXTERNAL_EXPERIMENT_PATHS):
        root = REPO / root_relative
        root_prefix = root_relative.rstrip("/") + "/"
        root_changes = {path: status for path, status in changes.items()
                        if path.startswith(root_prefix)}
        if not root.exists():
            if root_changes:
                raise RuntimeError(f"standalone experiment path disappeared: {root_relative}")
            continue
        if root.is_symlink() or not root.is_dir():
            raise RuntimeError(f"standalone experiment root must be a real directory: {root_relative}")
        if mode == "delta" and not root_changes:
            continue
        for name in ("README.md", "PREFLIGHT.md", "experiment.yaml", "USER_CASE.env",
                     "analysis/metric_spec.json"):
            if not (root / name).is_file():
                raise RuntimeError(f"standalone experiment definition is missing: {root / name}")
        manifest_path = root / "experiment_manifest.json"
        if not manifest_path.is_file():
            raise RuntimeError(f"standalone experiment manifest is missing: {manifest_path}")
        experiment = json.loads(manifest_path.read_text(encoding="utf-8"))
        experiment_id = str(experiment.get("experiment_id", ""))
        rows = experiment.get("runs")
        if (experiment.get("status") != "COMPLETE_MECHANICAL"
                or experiment.get("authorized_solve_count") != 1
                or not experiment_id or not isinstance(rows, list) or len(rows) != 1):
            raise RuntimeError(f"standalone experiment is not mechanically complete: {root_relative}")
        preflight = root / "PREFLIGHT.md"
        if (not preflight.is_file()
                or "This experiment is governed by docs/EXPERIMENT_CONTRACT.md."
                not in preflight.read_text(encoding="utf-8")):
            raise RuntimeError(f"standalone PREFLIGHT is missing or invalid: {root_relative}")

        experiment_new_solves = 0
        experiment_run_ids: list[str] = []
        for row in rows:
            if not isinstance(row, dict):
                raise RuntimeError(f"malformed standalone run entry in {root_relative}")
            run_id = str(row.get("run_id", ""))
            relative_run = str(row.get("path", ""))
            if (not run_id or Path(relative_run).parts != ("runs", run_id)
                    or run_id != "A001_T1_CLK_ONLY"):
                raise RuntimeError(f"unsafe/unexpected standalone run identity: {run_id!r}")
            run_dir = (root / relative_run).resolve()
            try:
                run_dir.relative_to((root / "runs").resolve())
            except ValueError as exc:
                raise RuntimeError(f"standalone run path escapes runs/: {relative_run}") from exc
            raw_path = run_dir / "raw.csv"
            result_path = run_dir / "result.json"
            provenance_path = run_dir / "provenance.json"
            metadata_path = run_dir / "metadata.json"
            raw_qa_path = run_dir / "analysis/raw_qa.json"
            metric_path = run_dir / "analysis/clock_cycle_metrics.json"
            plot_manifest_path = run_dir / "analysis/plot_manifest.json"
            plot_qa_path = run_dir / "analysis/plot_qa.json"
            probe_path = run_dir / "probe_manifest.json"
            parameter_path = run_dir / "parameter_manifest.json"
            topology_path = run_dir / "topology_manifest.json"
            source_path = run_dir / "source_manifest.json"
            deck_path = run_dir / "actual_deck.cir"
            required = (raw_path, result_path, provenance_path, metadata_path, raw_qa_path,
                        metric_path, run_dir / "analysis/clock_cycle_metrics.csv",
                        plot_manifest_path, plot_qa_path, probe_path, source_path, deck_path,
                        parameter_path, topology_path,
                        run_dir / "PREFLIGHT.md", run_dir / "USER_CASE.snapshot.env",
                        run_dir / "USER_CASE.snapshot.json", run_dir / "RESULT_BRIEF.md",
                        run_dir / "run.log")
            missing = [str(path) for path in required if not path.is_file()]
            if missing:
                raise RuntimeError(f"standalone run {run_id} is missing required evidence: {missing}")

            result = json.loads(result_path.read_text(encoding="utf-8"))
            provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            raw_qa = json.loads(raw_qa_path.read_text(encoding="utf-8"))
            metrics = json.loads(metric_path.read_text(encoding="utf-8"))
            plot_manifest = json.loads(plot_manifest_path.read_text(encoding="utf-8"))
            plot_qa = json.loads(plot_qa_path.read_text(encoding="utf-8"))
            probe = json.loads(probe_path.read_text(encoding="utf-8"))
            source_manifest = json.loads(source_path.read_text(encoding="utf-8"))
            parameters = json.loads(parameter_path.read_text(encoding="utf-8"))
            topology = json.loads(topology_path.read_text(encoding="utf-8"))
            effective_t1_parameters = parameters.get("t1")
            if not isinstance(effective_t1_parameters, dict):
                effective_t1_parameters = parameters.get("parameters")
            if not isinstance(effective_t1_parameters, dict):
                effective_t1_parameters = {}
            topology_clock = topology.get("clock", {})
            topology_clock_mode = topology.get("clock_mode")
            if topology_clock_mode is None and isinstance(topology_clock, dict):
                topology_clock_mode = topology_clock.get("mode")
            raw_sha = sha256(raw_path)
            deck_text = deck_path.read_text(encoding="utf-8")
            expected_clock_lines = (
                "V_TRIG_CLK CLK_RAW 0 PULSE(0 1.2m 170p 1p 1p 2p 50p)",
                "R_TRIG_CLK CLK_RAW CLK 5",
                "V_BIAS1 N_BIAS1 0 DC 1.8m", "V_BIAS2 N_BIAS2 0 DC 1.8m",
                "V_BIAS3 N_BIAS3 0 DC 1.8m",
                "XT1 0 CLK S C N_BIAS1 N_BIAS2 N_BIAS3 T1",
            )
            expected_probes = {
                "V(CLK_RAW)", "V(CLK)", "I(R_TRIG_CLK)", "V(S)", "V(C)",
                *{f"{quantity}({jj}|XT1)" for jj in ("B_J2", "B_J3", "B_J7", "B_J9", "B_J11")
                  for quantity in ("P", "V")},
            }
            source_rows = source_manifest.get("sources", [])
            source_roles = {str(item.get("role")) for item in source_rows
                            if isinstance(item, dict)}
            if (row.get("physical_solve_count") != 1
                    or row.get("artifact_status") != "VALID"
                    or row.get("solver_exit_code") != 0
                    or row.get("raw_sha256") != raw_sha
                    or result.get("run_id") != run_id
                    or result.get("status") != "MECHANICAL_QA_PASS_AWAITING_USER_REVIEW"
                    or result.get("artifact_status") != "VALID"
                    or result.get("solver_exit_code") != 0
                    or result.get("physical_solve_count") != 1
                    or result.get("raw_sha256") != raw_sha
                    or provenance.get("run_id") != run_id
                    or provenance.get("physical_solve_count") != 1
                    or provenance.get("raw", {}).get("sha256") != raw_sha
                    or provenance.get("actual_deck", {}).get("sha256") != sha256(deck_path)
                    or provenance.get("parameter_manifest", {}).get("sha256") != sha256(parameter_path)
                    or provenance.get("topology_manifest", {}).get("sha256") != sha256(topology_path)
                    or metadata.get("run_id") != run_id
                    or metadata.get("physical_solve_count") != 1
                    or metadata.get("raw_sha256") != raw_sha
                    or provenance.get("source_manifest", {}).get("sha256") != sha256(source_path)
                    or raw_qa.get("status") != "PASS"
                    or raw_qa.get("sha256") != raw_sha
                    or raw_qa.get("sha256_after_plot") != raw_sha
                    or raw_qa.get("raw_immutable") is not True
                    or metrics.get("status") != "DERIVED_ARITHMETIC_ONLY"
                    or metrics.get("raw_sha256") != raw_sha
                    or len(metrics.get("cycles", [])) != 4
                    or plot_qa.get("status") != "PASS"
                    or plot_qa.get("raw_sha256_before") != raw_sha
                    or plot_qa.get("raw_sha256_after") != raw_sha
                    or plot_manifest.get("raw_sha256") != raw_sha
                    or effective_t1_parameters.get("T1_CLK_MODE") != "PULSE"
                    or topology_clock_mode != "PULSE"
                    or topology.get("data_input", {}).get("node") != "0"
                    or probe.get("profile") != "debug"):
                raise RuntimeError(f"standalone run mechanical closure failed: {run_id}")
            if (any(line not in deck_text for line in expected_clock_lines)
                    or "R_CLK_QUIET" in deck_text
                    or source_roles != {"T1", "JJMIT_MODEL"}
                    or not expected_probes.issubset({str(item.get("label"))
                                                     for item in probe.get("signals", [])} ) ):
                raise RuntimeError(f"standalone run deck/source/probe closure failed: {run_id}")
            raw_headers = raw_qa.get("headers", [])
            probe_labels = [str(item.get("label")) for item in probe.get("signals", [])]
            if (not isinstance(raw_headers, list) or len(probe_labels) != len(set(probe_labels))
                    or not set(probe_labels).issubset(set(raw_headers))):
                raise RuntimeError(f"standalone run probe manifest does not close against raw: {run_id}")
            plot_pages = plot_qa.get("pages", [])
            manifest_pages = plot_manifest.get("pages", [])
            if not isinstance(plot_pages, list) or len(plot_pages) != 5 or len(manifest_pages) != 5:
                raise RuntimeError(f"standalone run plot page inventory is incomplete: {run_id}")
            qa_by_path = {str(page.get("path")): page for page in plot_pages if isinstance(page, dict)}
            for page in manifest_pages:
                relative_page = str(page.get("file", ""))
                qa_page = qa_by_path.get(f"plots/{relative_page}")
                plot_file = (run_dir / "plots" / relative_page).resolve()
                try:
                    plot_file.relative_to((run_dir / "plots").resolve())
                except ValueError as exc:
                    raise RuntimeError(f"plot path escapes standalone plots/: {relative_page}") from exc
                if (qa_page is None or not plot_file.is_file()
                        or qa_page.get("status") != "PASS"
                        or qa_page.get("sha256") != sha256(plot_file)):
                    raise RuntimeError(f"standalone plot QA/hash mismatch: {relative_page}")
            source_rows = source_manifest.get("sources", [])
            if not isinstance(source_rows, list) or len(source_rows) != 2:
                raise RuntimeError(f"standalone source closure is incomplete: {run_id}")
            for source in source_rows:
                if not isinstance(source, dict):
                    raise RuntimeError(f"malformed standalone source entry in {run_id}")
                canonical = REPO / str(source.get("path", ""))
                if not canonical.is_file() or sha256(canonical) != source.get("sha256"):
                    raise RuntimeError(f"standalone source hash mismatch: {canonical}")

            raw_repo_path = f"{root_relative}/{relative_run}/raw.csv"
            known = known_cases.get(raw_repo_path) or known_cases.get(run_id)
            reused = mode == "delta" and known is not None
            if reused and known.get("raw_sha256") != raw_sha:
                raise RuntimeError(f"standalone raw conflicts with verified base package: {run_id}")
            if reused:
                references.append({"source_case": run_id, "raw_path": raw_repo_path,
                                   "raw_sha256": raw_sha,
                                   "source_package": str(known.get("source_package", "verified base chain"))})
            else:
                experiment_new_solves += 1
            experiment_run_ids.append(run_id)
            runs.append({"experiment_id": experiment_id, "run_id": run_id,
                         "raw_path": raw_repo_path, "raw_sha256": raw_sha,
                         "reused": reused})

        experiments.append({"experiment_id": experiment_id, "path": root_relative,
                            "status": "COMPLETE_MECHANICAL", "run_ids": experiment_run_ids,
                            "new_physical_solve_count": experiment_new_solves})
        for path in sorted(item for item in root.rglob("*") if item.is_file()):
            if path.is_symlink():
                raise RuntimeError(f"standalone experiment contains a symlink: {path}")
            relative = path.relative_to(root).as_posix()
            repo_path = f"{root_relative}/{relative}"
            if "__pycache__" in path.parts or path.suffix == ".pyc":
                continue
            if path.parent.name == "handoff" and path.suffix.lower() == ".zip":
                continue
            if path.suffix.lower() == ".html" and not include_plots:
                continue
            # A newly authorized standalone run is a self-contained evidence
            # unit. Include all of its non-HTML members, including required
            # JSON manifests ignored by the repository-wide *.json rule.
            # Later deltas reference that run and include only changed files.
            if (mode == "delta" and repo_path not in root_changes
                    and experiment_new_solves == 0):
                continue
            if path.suffix.lower() == ".html":
                category = "plots"
            elif relative.endswith("/raw.csv"):
                category = "raw"
            elif "/snapshot/sources/" in relative:
                category = "source_snapshots"
            elif relative.startswith("runs/"):
                category = "run_manifests_qa"
            else:
                category = "standalone_experiment_metadata"
            members.append(PackageMember(path, repo_path, category))
            if mode == "delta":
                status = root_changes.get(repo_path)
                if status in {"A", "?"}:
                    statuses[repo_path] = "A"
                elif status == "M":
                    statuses[repo_path] = "M"
                elif experiment_new_solves > 0:
                    statuses[repo_path] = "A"
                else:
                    raise RuntimeError(
                        f"standalone changed member has no git-diff status: {repo_path}"
                    )

    return members, experiments, runs, references, statuses



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
                     statuses: dict[str, str],
                     standalone_experiments: list[dict[str, Any]],
                     standalone_solve_count: int) -> dict[str, Any]:
    new_files: list[str] = []
    modified_files: list[str] = []
    if base:
        for record in records:
            path = str(record["source_path"])
            in_scope = (path.startswith(SERIES_REL + "/")
                        or path in EXTERNAL_PLATFORM_PATHS
                        or any(path.startswith(root.rstrip("/") + "/")
                               for root in EXTERNAL_EXPERIMENT_PATHS))
            if not in_scope:
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
        external_path = any(raw_path.startswith(root.rstrip("/") + "/")
                            for root in EXTERNAL_EXPERIMENT_PATHS)
        if not raw_path.startswith(SERIES_REL + "/") and not external_path:
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
        "standalone_experiments": standalone_experiments,
        "included_runs": selected_runs,
        "referenced_existing_cases": normalized_references,
        "reproduction_tools": tools,
        "new_physical_solve_count": (
            sum(int(batch["new_physical_solve_count"]) for batch in selected_batches)
            + int(standalone_solve_count)
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
                                                  list[dict[str, str]], dict[str, dict[str, str]]]:
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
    return (list(members.values()), selected_batches, selected_runs, excluded_batches,
            references, known_cases)


def build_plan(mode: str, tag: str, base_commit: str | None = None,
               include_plots: bool = False) -> dict[str, Any]:
    if mode not in {"full", "delta"}:
        raise RuntimeError(f"unsupported package mode: {mode}")
    if not TAG_RE.fullmatch(tag):
        raise RuntimeError(f"invalid package tag: {tag!r}")
    head = head_commit()
    base = select_base(base_commit, head) if mode == "delta" else None
    evidence_members, selected_batches, selected_runs, excluded_batches, references, known_cases = \
        _select_batches(mode, base, include_plots)
    platform_members, statuses = _platform_members(mode, base, head)
    changes: dict[str, str] = {}
    if base:
        changes.update(committed_changes(str(base["base_commit"]), head))
    changes.update(worktree_changes())
    standalone_members, standalone_experiments, standalone_runs, standalone_references, \
        standalone_statuses = _standalone_experiment_members(
            mode, changes, known_cases, include_plots
        )
    statuses.update(standalone_statuses)
    references.extend(standalone_references)
    selected_runs.extend(standalone_runs)
    standalone_solve_count = sum(
        int(item["new_physical_solve_count"]) for item in standalone_experiments
    )
    members_by_path: dict[str, PackageMember] = {}
    for member in (*evidence_members, *platform_members, *standalone_members):
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
        standalone_experiments=standalone_experiments,
        standalone_solve_count=standalone_solve_count,
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
        "standalone_experiments": manifest.get("standalone_experiments", []),
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
    qa["standalone_experiments"] = plan["manifest"].get("standalone_experiments", [])
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
                        help="include mode-specific QA-verified derived HTML pages")
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
