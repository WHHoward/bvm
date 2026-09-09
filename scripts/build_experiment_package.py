#!/usr/bin/env python3
"""Build and mechanically verify an immutable scientific-review package.

This tool is deliberately separate from ``build_evidence_bundle.py``.  The
latter is a frozen josim-handoff/v1 pre-receipt manifest builder; this module
owns the default experiment ZIP introduced by the evidence-first workflow.

The ZIP contains the registered experiment definition, every selected run's
deck/raw/log/metadata, mechanical QA and visualization navigation.  The
detached ``PACKAGE_QA.json`` records the final archive hash.  Keeping that QA
file beside (rather than inside) the archive avoids a self-hash cycle.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import subprocess
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

import yaml


CONTRACT_SENTENCE = "This experiment is governed by docs/EXPERIMENT_CONTRACT.md."
PACKAGE_SCHEMA = "josim-experiment-evidence-package-v1"
PACKAGE_QA_SCHEMA = "josim-experiment-package-qa-v1"
REQUIRED_ANALYSIS = (
    "raw_qa.json",
    "deck_diff_qa.json",
    "provenance.json",
    "execution_summary.json",
    "transformation_registry.json",
)
DEFAULT_VIZ_MANIFEST = "analysis/visualization_manifest.json"
DEFAULT_VIZ_QA = "analysis/visualization_qa.json"
DEFAULT_VIZ_NAVIGATION = "analysis/run_summaries"
SAFE_EXPERIMENT_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
STORAGE_REVIEW_THRESHOLD_BYTES = 100 * 1024 * 1024


class PackageError(RuntimeError):
    """The requested package is incomplete or failed post-archive QA."""


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_if_absent(path: Path, text: str) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _load_config(root: Path) -> dict[str, Any]:
    path = root / "experiment.yaml"
    if not path.is_file():
        raise PackageError(f"missing experiment definition: {path}")
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise PackageError(f"invalid experiment YAML: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise PackageError("experiment.yaml must contain a mapping")
    experiment_id = value.get("id", value.get("experiment_id"))
    if not isinstance(experiment_id, str) or not SAFE_EXPERIMENT_ID.fullmatch(experiment_id):
        raise PackageError("experiment.yaml must declare a safe id/experiment_id")
    return value


def _relative(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise PackageError(f"package path must be inside experiment root: {path}") from exc


def _resolve_inside(root: Path, value: str | Path) -> Path:
    candidate = Path(value)
    path = candidate if candidate.is_absolute() else root / candidate
    path = path.resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise PackageError(f"package path escapes experiment root: {value}") from exc
    return path


def _git_context(root: Path) -> dict[str, Any]:
    try:
        top = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--show-toplevel"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        head = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return {"repository": None, "head": None}
    return {"repository": top, "head": head}


def _run_matrix_entries(config: dict[str, Any]) -> list[Any]:
    authorized = config.get("authorized_runs")
    if isinstance(authorized, list):
        return authorized
    matrix = config.get("run_matrix")
    if isinstance(matrix, list):
        return matrix
    if isinstance(matrix, dict) and isinstance(matrix.get("runs"), list):
        return matrix["runs"]
    return []


def _entry_run_path(root: Path, entry: Any) -> Path:
    if isinstance(entry, str):
        value = entry
    elif isinstance(entry, dict):
        value = entry.get("directory", entry.get("path", entry.get("id")))
    else:
        value = None
    if not isinstance(value, str) or not value:
        raise PackageError(f"authorized run entry must name a directory: {entry!r}")
    path = _resolve_inside(root, value)
    if path.parent != (root / "runs").resolve():
        # Accept a bare run id as a convenience, but keep all other entries
        # below runs/ and prevent accidental recursive directory packaging.
        bare = (root / "runs" / value).resolve()
        if bare.is_dir():
            path = bare
    if path.parent != (root / "runs").resolve():
        raise PackageError(f"authorized run must be an immediate child of runs/: {value}")
    return path


def discover_run_dirs(
    root: Path,
    config: dict[str, Any],
    *,
    requested_attempt: str | None = None,
) -> list[Path]:
    runs_root = root / "runs"
    if requested_attempt is not None:
        if not re.fullmatch(r"A\d{3,}", requested_attempt):
            raise PackageError("attempt must look like A001")
        candidates = [(runs_root / requested_attempt).resolve()]
    else:
        entries = _run_matrix_entries(config)
        if entries:
            candidates = [_entry_run_path(root, entry) for entry in entries]
        elif runs_root.is_dir():
            candidates = sorted((path.resolve() for path in runs_root.iterdir() if path.is_dir()))
        else:
            candidates = []
    if not candidates:
        raise PackageError("no authorized run directories found")
    if len(set(candidates)) != len(candidates):
        raise PackageError("authorized run matrix contains duplicate directories")
    for path in candidates:
        if not path.is_dir():
            raise PackageError(f"authorized run directory does not exist: {path}")
    return candidates


def _raw_summary(path: Path) -> dict[str, Any]:
    """Read only the raw time column for package metadata; never rewrite raw."""

    try:
        with path.open(newline="", encoding="utf-8-sig") as stream:
            reader = csv.reader(stream)
            header = next(reader)
            matches = [index for index, name in enumerate(header) if name == "time"]
            if len(matches) != 1:
                matches = [index for index, name in enumerate(header) if name.casefold() == "time"]
            if len(matches) != 1:
                raise PackageError(f"raw time column is ambiguous or missing: {path}")
            time_index = matches[0]
            times: list[float] = []
            for row in reader:
                if not row or not any(cell.strip() for cell in row):
                    continue
                if len(row) != len(header):
                    raise PackageError(f"raw row width mismatch: {path}")
                value = float(row[time_index])
                if not math.isfinite(value) or (times and value <= times[-1]):
                    raise PackageError(f"raw time is non-finite or non-increasing: {path}")
                times.append(value)
    except (OSError, StopIteration, ValueError) as exc:
        raise PackageError(f"cannot mechanically read raw CSV: {path}: {exc}") from exc
    if len(times) < 2:
        raise PackageError(f"raw CSV needs at least two samples: {path}")
    return {
        "sample_count": len(times),
        "first_timestamp": times[0],
        "last_timestamp": times[-1],
        "time_unit": "seconds in raw CSV",
    }


def _file_record(root: Path, path: Path) -> dict[str, Any]:
    return {
        "path": _relative(root, path),
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
    }


def _ensure_source_manifest(root: Path, config: dict[str, Any], run_dirs: list[Path]) -> Path:
    path = root / "SOURCE_MANIFEST.json"
    if path.is_file():
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise PackageError(f"invalid SOURCE_MANIFEST.json: {exc}") from exc
        if not isinstance(value, dict):
            raise PackageError("SOURCE_MANIFEST.json must contain a mapping")
        return path

    configured = config.get("sources", [])
    git = _git_context(root)
    repository = Path(git["repository"]) if isinstance(git.get("repository"), str) else None

    def resolve_source(value: str) -> Path:
        candidate = Path(value)
        choices = [candidate] if candidate.is_absolute() else [root / candidate]
        if not candidate.is_absolute() and repository is not None:
            choices.append(repository / candidate)
        for choice in choices:
            if choice.is_file():
                return choice.resolve()
        return choices[0].resolve()

    source_entries: list[dict[str, Any]] = []
    if isinstance(configured, list):
        for item in configured:
            if not isinstance(item, dict) or not isinstance(item.get("path"), str):
                raise PackageError("sources entries must be mappings with a path")
            source = resolve_source(item["path"])
            if not source.is_file():
                raise PackageError(f"configured source does not exist: {source}")
            try:
                git_path = None
                if repository is not None and source.resolve().is_relative_to(repository.resolve()):
                    git_path = source.resolve().relative_to(repository.resolve()).as_posix()
                repo_relative = subprocess.run(
                    ["git", "-C", str(root), "ls-files", "--full-name", "--", git_path or str(source)],
                    check=False,
                    capture_output=True,
                    text=True,
                ).stdout.strip() or None
            except OSError:
                repo_relative = None
            source_entries.append({
                "repo_relative_path": repo_relative,
                "path": _relative(root, source) if source.resolve().is_relative_to(root.resolve()) else str(source),
                "sha256": sha256_file(source),
                "bytes": source.stat().st_size,
                "role": item.get("role", "experiment source"),
            })
    else:
        deck_value = config.get("deck")
        if isinstance(deck_value, str):
            deck = resolve_source(deck_value)
            if deck.is_file():
                source_entries.append({
                    "repo_relative_path": None,
                    "path": _relative(root, deck),
                    "sha256": sha256_file(deck),
                    "bytes": deck.stat().st_size,
                    "role": "registered deck source",
                })
        run = config.get("run")
        if isinstance(run, dict) and isinstance(run.get("solver"), str):
            solver = resolve_source(run["solver"])
            if solver.is_file():
                source_entries.append({
                    "repo_relative_path": None,
                    "path": str(solver),
                    "sha256": sha256_file(solver),
                    "bytes": solver.stat().st_size,
                    "role": "solver identity",
                })
    for run_dir in run_dirs:
        deck = run_dir / "deck.cir"
        source_entries.append({
            "repo_relative_path": None,
            "path": _relative(root, deck),
            "sha256": sha256_file(deck),
            "bytes": deck.stat().st_size,
            "role": "executed deck",
        })
    manifest = {
        "schema": "josim-source-manifest-v1",
        "experiment_id": config.get("id", config.get("experiment_id")),
        "created_at": _now(),
        "sources": source_entries,
    }
    _write_json(path, manifest)
    return path


def _configured_analysis_paths(root: Path, config: dict[str, Any]) -> dict[str, Path]:
    package = config.get("package", {})
    mapping = package.get("analysis_files", {}) if isinstance(package, dict) else {}
    if not isinstance(mapping, dict):
        raise PackageError("package.analysis_files must be a mapping")
    paths: dict[str, Path] = {}
    for name in REQUIRED_ANALYSIS:
        value = mapping.get(name, f"analysis/{name}")
        if not isinstance(value, str):
            raise PackageError(f"package.analysis_files.{name} must be a path")
        paths[name] = _resolve_inside(root, value)
    return paths


def _configured_visualization_paths(root: Path, config: dict[str, Any]) -> tuple[Path, Path, Path]:
    visualization = config.get("visualization", {})
    if not isinstance(visualization, dict):
        visualization = {}
    manifest_value = visualization.get("manifest_path", DEFAULT_VIZ_MANIFEST)
    qa_value = visualization.get("qa_path", DEFAULT_VIZ_QA)
    navigation_value = visualization.get("navigation_path", DEFAULT_VIZ_NAVIGATION)
    if not all(isinstance(value, str) for value in (manifest_value, qa_value, navigation_value)):
        raise PackageError("visualization manifest/qa/navigation paths must be strings")
    return (
        _resolve_inside(root, manifest_value),
        _resolve_inside(root, qa_value),
        _resolve_inside(root, navigation_value),
    )


def _require_files(paths: Iterable[Path], label: str) -> None:
    missing = [str(path) for path in paths if not path.is_file()]
    if missing:
        raise PackageError(f"missing {label}: {', '.join(missing)}")


def _require_pass_json(path: Path, label: str) -> None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PackageError(f"{label} is not valid JSON: {path}: {exc}") from exc
    if not isinstance(value, dict) or value.get("status") != "PASS":
        raise PackageError(f"{label} is not PASS: {path}")


def _require_json_mapping(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PackageError(f"{label} is not valid JSON: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise PackageError(f"{label} must contain a mapping: {path}")
    return value


def _validate_visualization_manifest(
    root: Path,
    config: dict[str, Any],
    manifest_path: Path,
    qa_path: Path,
    run_dirs: list[Path],
) -> None:
    manifest = _require_json_mapping(manifest_path, "visualization manifest")
    qa = _require_json_mapping(qa_path, "visualization QA")
    entries = manifest.get("standalone_entries", manifest.get("standalone", []))
    if not isinstance(entries, list) or not entries:
        raise PackageError("visualization manifest has no standalone entries")
    declared_hashes = manifest.get("raw_hashes")
    if isinstance(declared_hashes, dict):
        for run_dir in run_dirs:
            expected = declared_hashes.get(run_dir.name)
            if expected is not None and expected != sha256_file(run_dir / "raw.csv"):
                raise PackageError(f"visualization manifest raw hash is stale: {run_dir.name}")
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        run_id = entry.get("run_id")
        if isinstance(run_id, str) and run_id in {path.name for path in run_dirs}:
            expected = entry.get("input_raw_sha256", entry.get("raw_sha256"))
            raw_value = entry.get("input_raw", f"runs/{run_id}/raw.csv")
            if isinstance(expected, str) and isinstance(raw_value, str):
                raw_path = _resolve_inside(root, raw_value)
                if not raw_path.is_file():
                    raise PackageError(f"visualization entry raw path is missing: {raw_path}")
                if expected != sha256_file(raw_path):
                    raise PackageError(f"visualization entry raw hash is stale: {run_id}")
    visualization = config.get("visualization", {})
    if isinstance(visualization, dict) and visualization.get("comparison_required") is True:
        comparisons = manifest.get("comparison_entries", manifest.get("comparison", []))
        if not isinstance(comparisons, list) or not comparisons:
            raise PackageError("comparison visualization is required but absent")
    gates = qa.get("semantic_completeness_gates", {})
    if isinstance(gates, dict):
        failed = []
        for name, value in gates.items():
            if isinstance(value, dict):
                value = value.get("status")
            if value in {"FAIL", False}:
                failed.append(name)
        if failed:
            raise PackageError("visualization semantic QA failed: " + ", ".join(failed))


def _add_tree(paths: set[Path], root: Path, directory: Path) -> None:
    if not directory.exists():
        return
    if directory.is_file():
        paths.add(directory)
        return
    paths.update(path for path in directory.rglob("*") if path.is_file())


def _navigation_files(navigation: Path, root: Path, run_dirs: list[Path]) -> list[Path]:
    if navigation.is_file():
        return [navigation]
    if not navigation.is_dir():
        raise PackageError(f"missing per-run visualization navigation: {navigation}")
    files = sorted(path for path in navigation.rglob("*") if path.is_file())
    if not files:
        raise PackageError(f"visualization navigation is empty: {navigation}")
    lower_names = [path.as_posix().casefold() for path in files]
    for run_dir in run_dirs:
        run_name = run_dir.name.casefold()
        if not any(run_name in name for name in lower_names):
            raise PackageError(f"no per-run visualization navigation for {run_dir.name}")
    return files


def _make_evidence_manifest(root: Path, config: dict[str, Any], run_dirs: list[Path], package_path: Path) -> Path:
    path = root / "EVIDENCE_MANIFEST.md"
    if path.exists():
        expected = _relative(root, package_path)
        if expected not in path.read_text(encoding="utf-8"):
            raise PackageError(f"EVIDENCE_MANIFEST.md names a different package: {path}")
        return path
    lines = [
        f"# Evidence manifest — {config.get('id', config.get('experiment_id'))}",
        "",
        "This is an evidence-only handoff. Scientific interpretation is `NOT PERFORMED`.",
        "",
        f"- Experiment ID: `{config.get('id', config.get('experiment_id'))}`",
        f"- HEAD: `{_git_context(root).get('head') or 'NOT_IN_GIT'}`",
        "- Purpose: `scientific-review handoff`",
        f"- Authorized runs: {', '.join(f'`{p.name}`' for p in run_dirs)}",
        "- Mechanical QA: `see analysis/*.json`",
        "- Standard visualization: `see visualization manifest and QA`",
        f"- Evidence ZIP: `{_relative(root, package_path)}`",
        "- Evidence ZIP SHA-256: `see adjacent handoff/PACKAGE_QA.json; detached to avoid self-hash cycle`",
        "- Missing probes / UNKNOWN: `preserved in mechanical QA and visualization QA`",
        "- Unauthorized follow-up: `none`",
        "- Scientific interpretation: `NOT PERFORMED`",
        "- Status: `AWAITING_SCIENTIFIC_REVIEW`",
        "",
    ]
    _write_if_absent(path, "\n".join(lines))
    return path


def _make_raw_handoff_manifest(
    root: Path,
    config: dict[str, Any],
    run_dirs: list[Path],
    package_path: Path,
    source_manifest: Path,
) -> Path:
    path = root / "RAW_ANALYSIS_HANDOFF_MANIFEST.json"
    if path.exists():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise PackageError(f"invalid RAW_ANALYSIS_HANDOFF_MANIFEST.json: {path}") from exc
        if isinstance(existing, dict) and existing.get("package_relative_path") not in {
            _relative(root, package_path),
            None,
        }:
            raise PackageError(f"RAW_ANALYSIS_HANDOFF_MANIFEST.json names a different package: {path}")
        existing_runs = existing.get("runs") if isinstance(existing, dict) else None
        if isinstance(existing_runs, dict):
            for run_dir in run_dirs:
                entry = existing_runs.get(run_dir.name)
                if isinstance(entry, dict) and entry.get("raw_sha256") not in {
                    None,
                    sha256_file(run_dir / "raw.csv"),
                }:
                    raise PackageError(f"RAW_ANALYSIS_HANDOFF_MANIFEST.json has a stale raw hash: {run_dir.name}")
        return path
    git = _git_context(root)
    runs: dict[str, Any] = {}
    for run_dir in run_dirs:
        raw = run_dir / "raw.csv"
        deck = run_dir / "deck.cir"
        metadata = run_dir / "metadata.json"
        log = run_dir / "run.log"
        summary = _raw_summary(raw)
        runs[run_dir.name] = {
            "run_id": run_dir.name,
            "raw_relative_path": _relative(root, raw),
            "raw_sha256": sha256_file(raw),
            "raw_bytes": raw.stat().st_size,
            **summary,
            "deck_relative_path": _relative(root, deck),
            "deck_sha256": sha256_file(deck),
            "metadata_relative_path": _relative(root, metadata),
            "run_log_relative_path": _relative(root, log),
        }
    analysis_paths = _configured_analysis_paths(root, config)
    visualization_manifest, visualization_qa, _ = _configured_visualization_paths(root, config)
    artifact_paths = {
        "experiment_definition": root / "experiment.yaml",
        "preflight": root / "PREFLIGHT.md",
        "provenance": analysis_paths["provenance.json"],
        "visualization_manifest": visualization_manifest,
        "visualization_qa": visualization_qa,
        "source_manifest": source_manifest,
    }
    manifest = {
        "schema": "josim-raw-analysis-handoff-manifest-v1",
        "package_schema": PACKAGE_SCHEMA,
        "experiment_id": config.get("id", config.get("experiment_id")),
        "repository": git.get("repository"),
        "head": git.get("head"),
        "purpose": "scientific-review handoff",
        "created_at": _now(),
        "package_relative_path": _relative(root, package_path),
        "physics_solve_count": config.get("physics_solve_count", len(run_dirs)),
        "scientific_analysis_performed": False,
        "runs": runs,
        "source_manifest_path": _relative(root, source_manifest),
        "included_artifacts": {
            name: _file_record(root, artifact)
            for name, artifact in artifact_paths.items()
            if artifact.is_file()
        },
    }
    _write_json(path, manifest)
    return path


def _archive_write(package_path: Path, root: Path, paths: Iterable[Path]) -> list[str]:
    names: dict[str, Path] = {}
    for path in paths:
        name = _relative(root, path)
        if name in names and names[name] != path:
            raise PackageError(f"duplicate archive path: {name}")
        names[name] = path
    package_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(package_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(names):
            info = zipfile.ZipInfo(name)
            # Stable archive metadata makes reruns easier to compare while
            # retaining the source bytes exactly.
            info.date_time = (1980, 1, 1, 0, 0, 0)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, names[name].read_bytes())
    return sorted(names)


def _post_archive_qa(
    package_path: Path,
    root: Path,
    archive_names: list[str],
    run_dirs: list[Path],
    source_hashes: dict[str, str],
) -> dict[str, Any]:
    failures: list[str] = []
    archived_raw: dict[str, str] = {}
    archived_deck: dict[str, str] = {}
    with zipfile.ZipFile(package_path, "r") as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            failures.append("ZIP contains duplicate names")
        if set(names) != set(archive_names):
            failures.append("ZIP entry list differs from the declared archive set")
        for run_dir in run_dirs:
            raw_name = _relative(root, run_dir / "raw.csv")
            deck_name = _relative(root, run_dir / "deck.cir")
            if raw_name not in names:
                failures.append(f"missing archived raw: {raw_name}")
            else:
                archived_raw[run_dir.name] = hashlib.sha256(archive.read(raw_name)).hexdigest()
            if deck_name not in names:
                failures.append(f"missing archived deck: {deck_name}")
            else:
                archived_deck[run_dir.name] = hashlib.sha256(archive.read(deck_name)).hexdigest()
    for run_dir in run_dirs:
        run_id = run_dir.name
        if archived_raw.get(run_id) != source_hashes[f"{run_id}:raw"]:
            failures.append(f"archived raw hash mismatch: {run_id}")
        if archived_deck.get(run_id) != source_hashes[f"{run_id}:deck"]:
            failures.append(f"archived deck hash mismatch: {run_id}")
    return {
        "archived_raw_sha256": archived_raw,
        "archived_deck_sha256": archived_deck,
        "failures": failures,
    }


def build_package(
    experiment_root: str | Path,
    *,
    requested_attempt: str | None = None,
    package_path: str | Path | None = None,
    physics_solve_count: int = 0,
    scientific_analysis_performed: bool = False,
    include_plots: bool = False,
) -> dict[str, Any]:
    """Build a package and leave a detached FAIL record on early rejection."""

    try:
        return _build_package(
            experiment_root,
            requested_attempt=requested_attempt,
            package_path=package_path,
            physics_solve_count=physics_solve_count,
            scientific_analysis_performed=scientific_analysis_performed,
            include_plots=include_plots,
        )
    except PackageError as exc:
        root = Path(experiment_root).resolve()
        if root.is_dir():
            qa_path = root / "handoff" / "PACKAGE_QA.json"
            if not qa_path.exists():
                requested = str(package_path) if package_path is not None else None
                _write_json(qa_path, {
                    "schema": PACKAGE_QA_SCHEMA,
                    "package_schema": PACKAGE_SCHEMA,
                    "status": "FAIL",
                    "created_at": _now(),
                    "package_path": requested,
                    "package_sha256": None,
                    "package_bytes": None,
                    "package_file_count": None,
                    "physics_solve_count_during_packaging": 0,
                    "physics_solve_count": physics_solve_count,
                    "raw_files_modified": 0,
                    "analysis_performed": False,
                    "scientific_analysis_performed": scientific_analysis_performed,
                    "zip_committed": False,
                    "failures": [str(exc)],
                })
        raise


def _build_package(
    experiment_root: str | Path,
    *,
    requested_attempt: str | None = None,
    package_path: str | Path | None = None,
    physics_solve_count: int = 0,
    scientific_analysis_performed: bool = False,
    include_plots: bool = False,
) -> dict[str, Any]:
    """Build one new package and return its detached PACKAGE_QA record."""

    root = Path(experiment_root).resolve()
    if not root.is_dir():
        raise PackageError(f"experiment root does not exist: {root}")
    config = _load_config(root)
    experiment_id = str(config.get("id", config.get("experiment_id")))
    run_dirs = discover_run_dirs(root, config, requested_attempt=requested_attempt)
    contract = root / "PREFLIGHT.md"
    if not contract.is_file() or CONTRACT_SENTENCE not in contract.read_text(encoding="utf-8"):
        raise PackageError(f"PREFLIGHT.md must contain the mandatory contract sentence: {contract}")
    required_run_files = [path for run in run_dirs for path in (
        run / "deck.cir", run / "raw.csv", run / "metadata.json", run / "run.log"
    )]
    _require_files(required_run_files, "authorized run evidence")
    analysis_paths = _configured_analysis_paths(root, config)
    _require_files(analysis_paths.values(), "mechanical QA")
    _require_pass_json(analysis_paths["raw_qa.json"], "raw QA")
    _require_pass_json(analysis_paths["deck_diff_qa.json"], "deck diff QA")
    provenance = _require_json_mapping(analysis_paths["provenance.json"], "provenance")
    execution = _require_json_mapping(analysis_paths["execution_summary.json"], "execution summary")
    transformation = _require_json_mapping(analysis_paths["transformation_registry.json"], "transformation registry")
    if execution.get("scientific_analysis_performed") is True:
        raise PackageError("execution summary contains scientific analysis; package the pre-review evidence instead")
    if transformation.get("raw_immutable") is False:
        raise PackageError("transformation registry does not preserve immutable raw")
    if not any(key in provenance for key in ("raw", "raw_files", "runs", "raw_sha256")):
        raise PackageError("provenance does not record the raw artifact")
    visualization_manifest, visualization_qa, navigation = _configured_visualization_paths(root, config)
    _require_files((visualization_manifest, visualization_qa), "visualization manifest/QA")
    _require_pass_json(visualization_qa, "visualization QA")
    _validate_visualization_manifest(root, config, visualization_manifest, visualization_qa, run_dirs)
    navigation_files = _navigation_files(navigation, root, run_dirs)

    handoff_dir = root / "handoff"
    default_package = handoff_dir / f"{experiment_id}_raw_handoff.zip"
    if package_path is None:
        archive_path = default_package.resolve()
    else:
        archive_path = _resolve_inside(root, package_path)
    if not archive_path.is_relative_to(root):
        raise PackageError("package path must be inside the experiment root")
    if archive_path.exists():
        raise PackageError(f"refusing to overwrite immutable evidence ZIP: {archive_path}")

    source_manifest = _ensure_source_manifest(root, config, run_dirs)
    evidence_manifest = _make_evidence_manifest(root, config, run_dirs, archive_path)
    raw_handoff_manifest = _make_raw_handoff_manifest(root, config, run_dirs, archive_path, source_manifest)

    # Snapshot raw/deck hashes immediately before archive creation.  The
    # package operation itself has no write path into runs/.
    source_hashes: dict[str, str] = {}
    for run in run_dirs:
        source_hashes[f"{run.name}:raw"] = sha256_file(run / "raw.csv")
        source_hashes[f"{run.name}:deck"] = sha256_file(run / "deck.cir")

    archive_paths: set[Path] = {
        root / "experiment.yaml",
        contract,
        evidence_manifest,
        raw_handoff_manifest,
        source_manifest,
        visualization_manifest,
        visualization_qa,
    }
    result_brief = root / "RESULT_BRIEF.md"
    if result_brief.is_file():
        archive_paths.add(result_brief)
    human_gate = root / "human-gate.yaml"
    if human_gate.is_file():
        archive_paths.add(human_gate)
    for path in analysis_paths.values():
        archive_paths.add(path)
    preflight_json = root / "analysis" / "preflight.json"
    if preflight_json.is_file():
        archive_paths.add(preflight_json)
    visualization_derived = root / "analysis" / "visualization_derived"
    _add_tree(archive_paths, root, visualization_derived)
    archive_paths.update(navigation_files)
    for run in run_dirs:
        # Include all files in a run, while still requiring the four canonical
        # names above.  Additional solver-native raw outputs remain available
        # without changing which file is the immutable raw.csv authority.
        _add_tree(archive_paths, root, run)
    for name in ("experiment.json", "run_matrix.json", "metric_spec.yaml", "metric_spec.yml"):
        candidate = root / name
        if candidate.is_file():
            archive_paths.add(candidate)
    for name in ("inputs", "variants", "models", "fixture"):
        _add_tree(archive_paths, root, root / name)
    package_config = config.get("package", {})
    additional = package_config.get("additional_paths", []) if isinstance(package_config, dict) else []
    if additional:
        if not isinstance(additional, list) or any(not isinstance(item, str) for item in additional):
            raise PackageError("package.additional_paths must be a list of paths")
        for item in additional:
            candidate = _resolve_inside(root, item)
            if not candidate.exists():
                raise PackageError(f"configured package path does not exist: {candidate}")
            _add_tree(archive_paths, root, candidate)
    if include_plots or (isinstance(package_config, dict) and package_config.get("include_plots") is True):
        _add_tree(archive_paths, root, root / "plots")

    archive_names = _archive_write(archive_path, root, archive_paths)
    internal = _post_archive_qa(archive_path, root, archive_names, run_dirs, source_hashes)
    package_sha = sha256_file(archive_path)
    package_bytes = archive_path.stat().st_size
    raw_unchanged = {
        run.name: sha256_file(run / "raw.csv") == source_hashes[f"{run.name}:raw"]
        for run in run_dirs
    }
    failures = list(internal["failures"])
    if not all(raw_unchanged.values()):
        failures.append("a source raw.csv changed during packaging")
    qa: dict[str, Any] = {
        "schema": PACKAGE_QA_SCHEMA,
        "package_schema": PACKAGE_SCHEMA,
        "status": "PASS" if not failures else "FAIL",
        "created_at": _now(),
        "package_path": _relative(root, archive_path),
        "package_absolute_path": str(archive_path),
        "package_sha256": package_sha,
        "package_bytes": package_bytes,
        "package_file_count": len(archive_names),
        "authorized_runs": [run.name for run in run_dirs],
        "all_authorized_runs_present": not failures,
        "all_raw_files_present": all(run.name in internal["archived_raw_sha256"] for run in run_dirs),
        "source_raw_sha256": {run.name: source_hashes[f"{run.name}:raw"] for run in run_dirs},
        "archived_raw_sha256": internal["archived_raw_sha256"],
        "source_deck_sha256": {run.name: source_hashes[f"{run.name}:deck"] for run in run_dirs},
        "archived_deck_sha256": internal["archived_deck_sha256"],
        "raw_hash_before_after": {
            run.name: {
                "before_archive": source_hashes[f"{run.name}:raw"],
                "after_archive": sha256_file(run / "raw.csv"),
                "unchanged": raw_unchanged[run.name],
            }
            for run in run_dirs
        },
        "raw_files_modified": 0 if all(raw_unchanged.values()) else None,
        "physics_solve_count_during_packaging": 0,
        "physics_solve_count": physics_solve_count,
        "analysis_performed": False,
        "scientific_analysis_performed": scientific_analysis_performed,
        "zip_committed": False,
        "storage_policy": (
            "STORAGE_POLICY_REVIEW_RECOMMENDED"
            if package_bytes > STORAGE_REVIEW_THRESHOLD_BYTES
            else "DEFAULT_GIT_COMMIT"
        ),
        "detached_qa": True,
        "notes": "PACKAGE_QA stays outside the ZIP to avoid a self-hash circularity.",
        "failures": failures,
    }
    qa_path = handoff_dir / "PACKAGE_QA.json"
    _write_json(qa_path, qa)
    if failures:
        raise PackageError(f"PACKAGE_QA FAIL: {'; '.join(failures)}")
    return {**qa, "qa_path": _relative(root, qa_path)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a JoSIM experiment scientific-review ZIP")
    parser.add_argument("experiment", help="experiment directory containing experiment.yaml")
    parser.add_argument("--attempt", help="package one Compact attempt such as A001")
    parser.add_argument("--output", help="optional ZIP path inside the experiment directory")
    parser.add_argument("--include-plots", action="store_true", help="include rendered plots in addition to navigation")
    args = parser.parse_args(argv)
    try:
        result = build_package(
            args.experiment,
            requested_attempt=args.attempt,
            package_path=args.output,
            include_plots=args.include_plots,
        )
    except PackageError as exc:
        print(f"PACKAGE FAIL: {exc}")
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
