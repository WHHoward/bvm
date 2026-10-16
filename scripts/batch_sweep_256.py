#!/usr/bin/env python3
"""Resume-safe, A-major scheduler for the fixed V9 SE375 4x4 input matrix.

This wrapper only changes CASE_NAME/A/B in the existing USER_CASE.env, gates
each solve with ./try.sh --dry-run, invokes ./try.sh --run-local once, validates
mechanical artifacts, and archives each run with the existing platform archiver.
It never reads output amplitudes to make a scientific decision.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SERIES = ROOT / "test" / "exploration" / "sfq_clock_two_read_v1"
RUNS = SERIES / "runs"
USER_CASE = SERIES / "USER_CASE.env"
BATCH_INDEX = RUNS / "BATCH_INDEX_SE375.csv"
FULL_INDEX = RUNS / "FULL256_SE375_INDEX.csv"
PENDING_DIR = RUNS / "PENDING_UPLOAD"
D_TARGET = Path("/mnt/d/BVM_Backages")
D_TARGET_LABEL = r"LOCAL_PATH:D:\BVM_Backages"
RUN_ID_RE = re.compile(r"^V9R\d{3,}_[-A-Za-z0-9_]+$")
CASE_NAME_RE = re.compile(r"^SE375_A([0-9]|1[0-5])_B([0-9]|1[0-5])_FULL256$")
FIXED = {
    "PROTOCOL": "V9_SHARED_ROW_SE_BL",
    "ROUNDS": "3",
    "READ_INTERVAL_PS": "80",
    "CLOCK_PERIOD_PS": "80",
    "SE_CLOCK_DELAY_PS": "68",
    "WRITE_START_PS": "50",
    "FIRST_READ_PS": "110",
    "DT_PS": "0.01",
    "STOP_PS": "400",
    "WL_WRITE_AMPLITUDE": "400u",
    "BL_WRITE_AMPLITUDE": "400u",
    "BL_READ_AMPLITUDE": "400u",
    "SE_READ_AMPLITUDE": "375u",
    "PROBE_PROFILE": "OUTPUTS",
    "CUSTOM_PROBES_FILE": "",
}
INDEX_FIELDS = [
    "A", "B", "EXPECTED_PRODUCT", "A_POPCOUNT", "B_POPCOUNT", "RUN_ID",
    "RUN_STATUS", "ARTIFACT_QA_STATUS", "RAW_SHA256", "GIT_COMMIT",
    "ARCHIVE_STATUS", "DRIVE_FILE_ID", "CLOUD_VERIFY_STATUS",
    "CLOUD_CONTENT_SHA256_STATUS", "SCIENTIFIC_STATUS", "ARCHIVE_PATH",
    "ARCHIVE_SHA256", "FAILURE_REASON",
]
CONTRACT_SENTENCE = "This experiment is governed by docs/EXPERIMENT_CONTRACT.md."


class BatchError(RuntimeError):
    pass


def _load_platform():
    path = SERIES / "scripts" / "platform.py"
    spec = importlib.util.spec_from_file_location("v9_platform_batch", path)
    if spec is None or spec.loader is None:
        raise BatchError(f"cannot load the existing V9 platform: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PLATFORM = _load_platform()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(*args: str, check: bool = True) -> str:
    result = subprocess.run(
        ["git", "-C", str(ROOT), *args], text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    if check and result.returncode:
        raise BatchError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout.strip()


def _head() -> str:
    return _git("rev-parse", "HEAD")


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with tmp.open("xb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


def _read_env() -> tuple[bytes, dict[str, str]]:
    if USER_CASE.is_symlink() or not USER_CASE.is_file():
        raise BatchError(f"USER_CASE.env missing or symlinked: {USER_CASE}")
    current = USER_CASE.read_bytes()
    current_values = PLATFORM.parse_env_text(current.decode("utf-8-sig"))
    relative = USER_CASE.relative_to(ROOT).as_posix()
    baseline_result = subprocess.run(
        ["git", "-C", str(ROOT), "show", f"HEAD:{relative}"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    if baseline_result.returncode:
        raise BatchError(f"cannot read committed USER_CASE.env: {baseline_result.stderr.decode(errors='replace')}")
    baseline = baseline_result.stdout
    baseline_text = baseline.decode("utf-8-sig")
    values = PLATFORM.parse_env_text(baseline_text)
    if current != baseline:
        changed = {key for key in values if current_values.get(key) != values.get(key)}
        match = CASE_NAME_RE.fullmatch(current_values.get("CASE_NAME", ""))
        if not match or changed - {"CASE_NAME", "A", "B"}:
            raise BatchError("USER_CASE.env differs from HEAD outside an interrupted FULL256 case")
        if current_values.get("A") != match.group(1) or current_values.get("B") != match.group(2):
            raise BatchError("interrupted USER_CASE case name and operands disagree")
    for key, expected in FIXED.items():
        if values.get(key) != expected:
            raise BatchError(f"fixed USER_CASE value drift: {key}={values.get(key)!r}, expected {expected!r}")
        if current_values.get(key) != expected:
            raise BatchError(f"fixed USER_CASE value drift in working file: {key}={current_values.get(key)!r}")
    return baseline, values


def _render_env(original: bytes, a: int, b: int) -> bytes:
    values = PLATFORM.parse_env_text(original.decode("utf-8-sig"))
    desired = {
        **{key: values[key] for key in values if key not in {"CASE_NAME", "A", "B"}},
        "CASE_NAME": f"SE375_A{a}_B{b}_FULL256",
        "A": str(a),
        "B": str(b),
    }
    for key, expected in FIXED.items():
        if desired.get(key) != expected:
            raise BatchError(f"USER_CASE edit would change frozen parameter {key}")
    text = original.decode("utf-8-sig")
    lines = text.splitlines(keepends=True)
    replacements = {"CASE_NAME": desired["CASE_NAME"], "A": desired["A"], "B": desired["B"]}
    found: set[str] = set()
    result: list[str] = []
    for line in lines:
        stripped = line.strip()
        if "=" in stripped and not stripped.startswith("#"):
            key = stripped.split("=", 1)[0].strip()
            if key in replacements:
                ending = "\r\n" if line.endswith("\r\n") else "\n" if line.endswith("\n") else ""
                result.append(f"{key}={replacements[key]}{ending}")
                found.add(key)
                continue
        result.append(line)
    if found != set(replacements):
        raise BatchError(f"could not update exactly CASE_NAME/A/B; found {sorted(found)}")
    rendered = "".join(result).encode("utf-8")
    parsed = PLATFORM.parse_env_text(rendered.decode("utf-8-sig"))
    if parsed != desired:
        raise BatchError("rendered USER_CASE differs outside CASE_NAME/A/B")
    return rendered


def _index_row(a: int, b: int) -> dict[str, str]:
    return {
        "A": str(a), "B": str(b), "EXPECTED_PRODUCT": str(a * b),
        "A_POPCOUNT": str(a.bit_count()), "B_POPCOUNT": str(b.bit_count()),
        "RUN_ID": "", "RUN_STATUS": "NOT_RUN", "ARTIFACT_QA_STATUS": "NOT_RUN",
        "RAW_SHA256": "", "GIT_COMMIT": "", "ARCHIVE_STATUS": "NOT_RUN",
        "DRIVE_FILE_ID": "", "CLOUD_VERIFY_STATUS": "NOT_CHECKED",
        "CLOUD_CONTENT_SHA256_STATUS": "NOT_CHECKED",
        "SCIENTIFIC_STATUS": "NOT_ANALYZED", "ARCHIVE_PATH": "",
        "ARCHIVE_SHA256": "", "FAILURE_REASON": "",
    }


def _read_index() -> dict[tuple[int, int], dict[str, str]] | None:
    if not FULL_INDEX.is_file():
        return None
    with FULL_INDEX.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != INDEX_FIELDS:
            raise BatchError(f"FULL256 index columns mismatch: {reader.fieldnames}")
        rows = list(reader)
    mapping: dict[tuple[int, int], dict[str, str]] = {}
    run_ids: set[str] = set()
    for row in rows:
        try:
            pair = (int(row["A"]), int(row["B"]))
        except (TypeError, ValueError) as exc:
            raise BatchError("FULL256 index has malformed A/B") from exc
        if pair in mapping or not 0 <= pair[0] <= 15 or not 0 <= pair[1] <= 15:
            raise BatchError(f"FULL256 index has duplicate/out-of-range pair: {pair}")
        if row["RUN_ID"]:
            if not RUN_ID_RE.fullmatch(row["RUN_ID"]) or row["RUN_ID"] in run_ids:
                raise BatchError(f"FULL256 index has malformed/duplicate RUN_ID: {row['RUN_ID']}")
            run_ids.add(row["RUN_ID"])
            if row["ARTIFACT_QA_STATUS"] != "ARTIFACT_QA_PASS" or not row["RAW_SHA256"]:
                raise BatchError(f"FULL256 index marks a run complete without passing artifact QA: {pair}")
        elif row["RUN_STATUS"].startswith("COMPLETED"):
            raise BatchError(f"FULL256 index marks an input complete without RUN_ID: {pair}")
        if row["EXPECTED_PRODUCT"] != str(pair[0] * pair[1]):
            raise BatchError(f"FULL256 expected-product metadata mismatch for {pair}")
        if row["A_POPCOUNT"] != str(pair[0].bit_count()) or row["B_POPCOUNT"] != str(pair[1].bit_count()):
            raise BatchError(f"FULL256 popcount metadata mismatch for {pair}")
        if row["SCIENTIFIC_STATUS"] != "NOT_ANALYZED":
            raise BatchError(f"scientific status was modified for {pair}")
        mapping[pair] = row
    if len(mapping) != 256:
        raise BatchError(f"FULL256 index must have 256 unique pairs, found {len(mapping)}")
    return mapping


def _write_index(rows: dict[tuple[int, int], dict[str, str]]) -> None:
    from io import StringIO
    buffer = StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=INDEX_FIELDS, lineterminator="\n")
    writer.writeheader()
    for pair in sorted(rows):
        writer.writerow(rows[pair])
    _atomic_write(FULL_INDEX, buffer.getvalue().encode("utf-8"))


def _run_dirs() -> list[Path]:
    found = []
    for path in RUNS.iterdir():
        if path.is_symlink():
            if re.match(r"^V9R\d{3,}_", path.name):
                raise BatchError(f"run directory is a symlink: {path}")
            continue
        if path.is_dir() and re.match(r"^V9R\d{3,}_", path.name):
            if not (path / "manifest.json").is_file():
                raise BatchError(f"incomplete allocated run directory; refusing reuse: {path}")
            found.append(path)
    return sorted(found)


def _verify_run(run_dir: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BatchError(f"invalid run manifest: {run_dir}: {exc}") from exc
    if manifest.get("run_id") != run_dir.name or not RUN_ID_RE.fullmatch(run_dir.name):
        raise BatchError(f"run identity mismatch: {run_dir}")
    config = manifest.get("effective_config")
    if not isinstance(config, dict):
        raise BatchError(f"manifest has no effective_config: {run_dir.name}")
    try:
        a, b = int(config["A"]), int(config["B"])
    except (KeyError, ValueError, TypeError) as exc:
        raise BatchError(f"invalid input identity: {run_dir.name}") from exc
    if not 0 <= a <= 15 or not 0 <= b <= 15:
        raise BatchError(f"input out of range: {run_dir.name}")
    if manifest.get("operands") != {"A": a, "B": b} or manifest.get("rounds") != 3:
        raise BatchError(f"manifest operands/rounds mismatch: {run_dir.name}")
    for key, value in FIXED.items():
        if config.get(key) != value:
            raise BatchError(f"frozen config drift in {run_dir.name}: {key}={config.get(key)!r}")
    try:
        snapshot = PLATFORM.parse_env_text((run_dir / "USER_CASE.snapshot.env").read_text(encoding="utf-8-sig"))
    except (OSError, PLATFORM.PlatformError) as exc:
        raise BatchError(f"invalid env snapshot in {run_dir.name}: {exc}") from exc
    if snapshot != config:
        raise BatchError(f"env snapshot/effective_config mismatch: {run_dir.name}")
    ctx = PLATFORM.build_case(snapshot)
    if (run_dir / "deck.cir").read_text(encoding="utf-8") != ctx["deck"]:
        raise BatchError(f"deck differs from frozen V9 render: {run_dir.name}")
    if (run_dir / "stimulus.inc").read_text(encoding="utf-8") != ctx["stimulus"]:
        raise BatchError(f"stimulus differs from fixed V9 render: {run_dir.name}")
    if ctx["probes"] != list(PLATFORM.DEFAULT_PROBES):
        raise BatchError(f"probe profile is not exactly OUTPUTS: {run_dir.name}")
    if manifest.get("topology_qa", {}).get("status") != "PASS":
        raise BatchError(f"topology QA failed: {run_dir.name}")
    if manifest.get("solver_exit_code") != 0 or manifest.get("status") != "ARTIFACT_QA_PASS":
        raise BatchError(f"run is not mechanically complete: {run_dir.name}")
    raw = run_dir / "raw.csv"
    try:
        qa = PLATFORM._raw_integrity(raw, list(PLATFORM.DEFAULT_PROBES))
        PLATFORM._archive_inputs(run_dir, manifest)
    except (OSError, PLATFORM.PlatformError, KeyError, TypeError, ValueError) as exc:
        raise BatchError(f"raw/evidence manifest QA failed: {run_dir.name}: {exc}") from exc
    if qa.get("status") != "PASS" or qa.get("raw_sha256") != manifest.get("raw_integrity", {}).get("raw_sha256"):
        raise BatchError(f"raw QA/hash mismatch: {run_dir.name}")
    if manifest.get("visualization", {}).get("status") != "PASS" or not (run_dir / "res.html").is_file():
        raise BatchError(f"output visualization QA/file failed: {run_dir.name}")
    preflight = run_dir / "PREFLIGHT.md"
    if not preflight.is_file() or CONTRACT_SENTENCE not in preflight.read_text(encoding="utf-8"):
        raise BatchError(f"per-run PREFLIGHT is missing the mandatory experiment contract: {run_dir.name}")
    if (run_dir / "custom.html").exists() or (run_dir / "archive_receipt.json").is_symlink():
        raise BatchError(f"unexpected/symlinked output artifact: {run_dir.name}")
    source_manifest, _ = PLATFORM._source_closure()
    expected_sources = {item["file"]: item["sha256"] for item in source_manifest["source_closure"]}
    actual_sources = {item["file"]: item["sha256"] for item in manifest.get("frozen_sources", [])}
    if actual_sources != expected_sources:
        raise BatchError(f"frozen source closure differs from V9 authority: {run_dir.name}")
    frozen_dir = run_dir / "sources_frozen"
    if {p.name for p in frozen_dir.iterdir() if p.is_file()} != set(expected_sources):
        raise BatchError(f"unexpected/missing frozen source file: {run_dir.name}")
    for name, digest in expected_sources.items():
        path = run_dir / "sources_frozen" / name
        if not path.is_file() or sha256(path) != digest:
            raise BatchError(f"frozen source SHA mismatch: {run_dir.name}/{name}")
    solver = PLATFORM._solver_path()
    if solver is None or PLATFORM.sha256_file(solver) != manifest.get("execution_environment", {}).get("josim_binary_sha256"):
        raise BatchError(f"solver binary identity differs from recorded run: {run_dir.name}")
    expected_paths = {record["path"] for record in manifest.get("evidence_files", [])}
    expected_paths.add("manifest.json")
    if (run_dir / "archive_receipt.json").is_file():
        expected_paths.add("archive_receipt.json")
    actual_paths = {
        path.relative_to(run_dir).as_posix()
        for path in run_dir.rglob("*")
        if path.is_file() and not path.is_symlink() and not path.name.endswith(".tmp")
    }
    if actual_paths != expected_paths:
        raise BatchError(f"run has unmanifested/missing files: {run_dir.name}")
    if manifest.get("visualization", {}).get("res_probe_labels") != list(PLATFORM.DEFAULT_PROBES):
        raise BatchError(f"res.html probe set differs from OUTPUTS: {run_dir.name}")
    return manifest, qa


def _batch_index() -> dict[tuple[int, int], dict[str, str]]:
    if not BATCH_INDEX.is_file():
        raise BatchError(f"missing prior SE375 batch index: {BATCH_INDEX}")
    with BATCH_INDEX.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != 24:
        raise BatchError(f"expected 24 registered G1/G2/G3 rows, found {len(rows)}")
    out = {}
    for row in rows:
        pair = (int(row["A"]), int(row["B"]))
        if (pair in out or not 0 <= pair[0] <= 15 or not 0 <= pair[1] <= 15 or
                row["artifact_qa_status"] != "ARTIFACT_QA_PASS"):
            raise BatchError(f"duplicate or invalid prior batch row: {pair}")
        out[pair] = row
    return out


def _archive_fields(run_dir: Path, run_id: str) -> dict[str, str]:
    receipt_path = run_dir / "archive_receipt.json"
    if receipt_path.is_file():
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        archive_path = Path(receipt["drive_path"])
        if not archive_path.is_file() or archive_path.stat().st_size != receipt["zip_bytes"]:
            raise BatchError(f"archive receipt target missing/size mismatch: {run_id}")
        if sha256(archive_path) != receipt["zip_sha256"]:
            raise BatchError(f"archive receipt SHA mismatch: {run_id}")
        return {
            "ARCHIVE_STATUS": receipt["archive_status"],
            "DRIVE_FILE_ID": receipt.get("drive_file_id") or "",
            "CLOUD_VERIFY_STATUS": receipt.get("cloud_sync_status", "UNCONFIRMED"),
            "CLOUD_CONTENT_SHA256_STATUS": "NOT_VERIFIED",
            "ARCHIVE_PATH": str(archive_path),
            "ARCHIVE_SHA256": receipt["zip_sha256"],
        }
    if run_id == "V9R001_SMOKE_A1_B1_80P68_SE375U":
        package = RUNS / "handoff" / "runs_snapshot_SMOKE_A1_B1_80P68.zip"
        qa_path = RUNS / "handoff" / "runs_snapshot_SMOKE_A1_B1_80P68_PACKAGE_QA.json"
        qa = json.loads(qa_path.read_text(encoding="utf-8"))
        if not package.is_file() or sha256(package) != qa.get("package_sha256") or qa.get("status") != "PASS":
            raise BatchError("V9R001 GitHub evidence package is missing or invalid")
        with zipfile.ZipFile(package) as archive:
            if archive.testzip() is not None:
                raise BatchError("V9R001 package CRC check failed")
            raw_member = f"{run_id}/raw.csv"
            if hashlib.sha256(archive.read(raw_member)).hexdigest() != qa["included_file_sha256"][raw_member]:
                raise BatchError("V9R001 packaged raw SHA mismatch")
        return {
            "ARCHIVE_STATUS": "GITHUB_PACKAGE_PRESENT",
            "DRIVE_FILE_ID": "",
            "CLOUD_VERIFY_STATUS": "UNCONFIRMED",
            "CLOUD_CONTENT_SHA256_STATUS": "NOT_VERIFIED",
            "ARCHIVE_PATH": str(package.relative_to(ROOT)),
            "ARCHIVE_SHA256": qa["package_sha256"],
        }
    return {
        "ARCHIVE_STATUS": "NOT_ARCHIVED",
        "DRIVE_FILE_ID": "",
        "CLOUD_VERIFY_STATUS": "NOT_CHECKED",
        "CLOUD_CONTENT_SHA256_STATUS": "NOT_CHECKED",
        "ARCHIVE_PATH": "",
        "ARCHIVE_SHA256": "",
    }


def _new_index() -> dict[tuple[int, int], dict[str, str]]:
    prior = _batch_index()
    dirs = _run_dirs()
    manifests: dict[tuple[int, int], tuple[Path, dict[str, Any]]] = {}
    for run_dir in dirs:
        try:
            manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
            config = manifest["effective_config"]
            pair = (int(config["A"]), int(config["B"]))
        except (OSError, json.JSONDecodeError, KeyError, ValueError, TypeError) as exc:
            raise BatchError(f"cannot establish run input identity: {run_dir}: {exc}") from exc
        if pair in manifests:
            raise BatchError(f"multiple run IDs claim input {pair}; refusing ambiguous skip")
        manifests[pair] = (run_dir, manifest)
    smoke_pair = (1, 1)
    if smoke_pair not in manifests or len(manifests) != 25:
        raise BatchError(f"expected exactly 25 unique prior inputs including 1x1; found {len(manifests)}")
    if set(prior) | {smoke_pair} != set(manifests):
        raise BatchError("prior BATCH_INDEX plus V9R001 does not match existing manifest input set")
    rows = {(a, b): _index_row(a, b) for a in range(16) for b in range(16)}
    for pair, (run_dir, manifest) in manifests.items():
        manifest, rawqa = _verify_run(run_dir)
        a, b = pair
        batch_row = prior.get(pair)
        if batch_row and batch_row["run_id"] != run_dir.name:
            raise BatchError(f"prior index run_id mismatch for {pair}")
        if batch_row and batch_row["raw_sha256"] != rawqa["raw_sha256"]:
            raise BatchError(f"prior index raw SHA mismatch for {pair}")
        row = rows[pair]
        row.update({
            "RUN_ID": run_dir.name,
            "RUN_STATUS": "COMPLETED_EXISTING",
            "ARTIFACT_QA_STATUS": "ARTIFACT_QA_PASS",
            "RAW_SHA256": rawqa["raw_sha256"],
            "GIT_COMMIT": manifest.get("execution_environment", {}).get("parent_head", ""),
            "SCIENTIFIC_STATUS": "NOT_ANALYZED",
        })
        row.update(_archive_fields(run_dir, run_dir.name))
    return rows


def _validate_index_against_runs(rows: dict[tuple[int, int], dict[str, str]], *, deep_a: int | None = None) -> dict[tuple[int, int], tuple[Path, dict[str, Any]]]:
    dirs = _run_dirs()
    manifests: dict[tuple[int, int], tuple[Path, dict[str, Any]]] = {}
    ids: set[str] = set()
    for run_dir in dirs:
        manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
        config = manifest.get("effective_config", {})
        pair = (int(config.get("A", -1)), int(config.get("B", -1)))
        if pair in manifests or run_dir.name in ids:
            raise BatchError(f"duplicate manifest identity for input {pair}")
        ids.add(run_dir.name)
        manifests[pair] = (run_dir, manifest)
    for pair, row in rows.items():
        if row["RUN_STATUS"] == "ARTIFACT_QA_FAIL" or row["ARTIFACT_QA_STATUS"] == "ARTIFACT_QA_FAIL":
            raise BatchError(f"index records a mechanical failure for {pair}; manual review required")
        found = manifests.get(pair)
        if row["RUN_ID"]:
            if found is None or found[0].name != row["RUN_ID"]:
                raise BatchError(f"index run ID has no matching manifest: {pair}/{row['RUN_ID']}")
            if row["RAW_SHA256"] != found[1].get("raw_integrity", {}).get("raw_sha256"):
                raise BatchError(f"index/manifest raw SHA mismatch: {pair}")
            if row["ARTIFACT_QA_STATUS"] != "ARTIFACT_QA_PASS":
                raise BatchError(f"completed index row has non-pass artifact status: {pair}")
            if deep_a is None or pair[0] == deep_a:
                manifest, rawqa = _verify_run(found[0])
                if row["RAW_SHA256"] != rawqa["raw_sha256"]:
                    raise BatchError(f"deep raw QA/index SHA mismatch: {pair}")
        elif found is not None:
            # A process may have stopped after the immutable run was written but
            # before the FULL256 index was updated. Recover only after full QA.
            manifest, rawqa = _verify_run(found[0])
            if manifest["effective_config"]["CASE_NAME"] != f"SE375_A{pair[0]}_B{pair[1]}_FULL256":
                raise BatchError(f"unindexed run has unexpected case identity: {found[0].name}")
            row.update({
                "RUN_ID": found[0].name,
                "RUN_STATUS": "COMPLETED_RECOVERED",
                "ARTIFACT_QA_STATUS": "ARTIFACT_QA_PASS",
                "RAW_SHA256": rawqa["raw_sha256"],
                "GIT_COMMIT": manifest.get("execution_environment", {}).get("parent_head", ""),
            })
            row.update(_archive_fields(found[0], found[0].name))
    return manifests


def _write_initial_index_if_missing() -> dict[tuple[int, int], dict[str, str]]:
    rows = _read_index()
    if rows is None:
        rows = _new_index()
        _write_index(rows)
    return rows


def _print_plan(a: int, rows: dict[tuple[int, int], dict[str, str]], limit: int | None) -> list[int]:
    pending = [b for b in range(16) if not rows[(a, b)]["RUN_ID"]]
    selected = pending[:limit] if limit is not None else pending
    print(json.dumps({
        "status": "DRY_RUN_PASS",
        "batch_a": a,
        "historical_or_completed_valid_count": 256 - sum(not r["RUN_ID"] for r in rows.values()),
        "missing_in_batch": len(pending),
        "planned_new_runs": [{"A": a, "B": b, "CASE_NAME": f"SE375_A{a}_B{b}_FULL256"} for b in selected],
        "physical_solve_count": 0,
        "archive_target": str(D_TARGET),
    }, ensure_ascii=False, indent=2))
    return selected


def _status_paths() -> list[str]:
    raw = _git("status", "--porcelain=v1", "--untracked-files=all")
    return [line[3:] for line in raw.splitlines() if len(line) >= 4]


def _check_scope() -> None:
    runs_prefix = "test/exploration/sfq_clock_two_read_v1/runs/"
    exact = {
        "test/exploration/sfq_clock_two_read_v1/USER_CASE.env",
        f"{runs_prefix}run_index.json",
        f"{runs_prefix}FULL256_SE375_INDEX.csv",
        "test/exploration/sfq_clock_two_read_v1/experiment.yaml",
        "test/exploration/sfq_clock_two_read_v1/FULL256_PREFLIGHT.md",
    }
    outside = []
    for path in _status_paths():
        if path in exact:
            continue
        if path.startswith(f"{runs_prefix}PENDING_UPLOAD/") and path.endswith(".zip"):
            continue
        parts = Path(path).parts
        if len(parts) >= 5 and "/".join(parts[:4]) == runs_prefix.rstrip("/") and RUN_ID_RE.fullmatch(parts[4]):
            continue
        outside.append(path)
    if outside:
        raise BatchError("unrelated worktree changes block batch execution: " + ", ".join(outside))


def _case_config(original: bytes, a: int, b: int) -> bytes:
    rendered = _render_env(original, a, b)
    values = PLATFORM.parse_env_text(rendered.decode("utf-8-sig"))
    if values["CASE_NAME"] != f"SE375_A{a}_B{b}_FULL256" or values["A"] != str(a) or values["B"] != str(b):
        raise BatchError("case renderer produced unexpected CASE_NAME/A/B")
    return rendered


def _validate_dry_run(output: str, a: int, b: int) -> None:
    required = (
        "DRY RUN PASS — solver_invoked=false; physical_solve_count=0",
        f"CASE: SE375_A{a}_B{b}_FULL256 | PROTOCOL=V9_SHARED_ROW_SE_BL",
        f"A={a} B={b} ROUNDS=3",
        "READ_STARTS_PS: 110,190,270",
        "CLK_PWL_STARTS_PS: 178,258,338",
        '"SE_READ_AMPLITUDE": "375u"',
        "PROBES: output=8; custom_diagnostics=0 (OUTPUTS)",
        "STATIC TOPOLOGY QA: PASS",
    )
    missing = [item for item in required if item not in output]
    if missing:
        raise BatchError(f"dry-run gate failed for A={a}, B={b}: {missing}")


def _archive_new_run(run_id: str) -> dict[str, str]:
    run_dir = RUNS / run_id
    available, message = PLATFORM._drive_write_probe(D_TARGET)
    if available:
        try:
            receipt = PLATFORM.archive_completed_run(
                run_id, target_dir=D_TARGET, runs_dir=RUNS,
                folder_id=D_TARGET_LABEL,
            )
            return {
                "ARCHIVE_STATUS": receipt["archive_status"],
                "DRIVE_FILE_ID": receipt.get("drive_file_id") or "",
                "CLOUD_VERIFY_STATUS": "UNCONFIRMED",
                "CLOUD_CONTENT_SHA256_STATUS": "NOT_VERIFIED",
                "ARCHIVE_PATH": receipt["drive_path"],
                "ARCHIVE_SHA256": receipt["zip_sha256"],
            }
        except (OSError, PLATFORM.PlatformError, zipfile.BadZipFile) as exc:
            # Fall back only if the exact D target became unavailable. If it
            # remains writable, treat a package/hash error as mechanical FAIL.
            still_available, _ = PLATFORM._drive_write_probe(D_TARGET)
            if still_available:
                raise BatchError(f"D archive failed while target remains writable: {exc}") from exc
            message = str(exc)
    pending = RUNS / "PENDING_UPLOAD"
    pending.mkdir(parents=True, exist_ok=True)
    try:
        info = PLATFORM.create_archive(run_dir, target_dir=pending, folder_id="LOCAL_PENDING_UPLOAD")
    except (OSError, PLATFORM.PlatformError, zipfile.BadZipFile) as exc:
        raise BatchError(f"D archive unavailable ({message}) and local pending ZIP failed: {exc}") from exc
    receipt = {
        "schema": "sfq-clock-two-read-local-pending-receipt-v1",
        "run_id": run_id,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "archive_status": "LOCAL_ZIP_READY_PENDING_UPLOAD",
        **info,
        "cloud_sync_status": "UNCONFIRMED",
        "cloud_sync_note": "ZIP is local only; no Drive File ID or cloud readback is available.",
    }
    PLATFORM._write_receipt_no_overwrite(run_dir / "archive_receipt.json", receipt)
    return {
        "ARCHIVE_STATUS": "ARCHIVE_PENDING",
        "DRIVE_FILE_ID": "",
        "CLOUD_VERIFY_STATUS": "UNCONFIRMED",
        "CLOUD_CONTENT_SHA256_STATUS": "NOT_VERIFIED",
        "ARCHIVE_PATH": info["drive_path"],
        "ARCHIVE_SHA256": info["zip_sha256"],
    }


def _execute_batch(a: int, rows: dict[tuple[int, int], dict[str, str]], limit: int | None) -> int:
    selected = _print_plan(a, rows, limit)
    if not selected:
        print(f"A={a}: all 16 inputs already have valid evidence; no solver call.")
        return 0
    original, base_values = _read_env()
    original_head = _head()
    _write_index(rows)  # durable RUNNING state before the first case
    current_write: bytes | None = None
    solves = 0
    try:
        for b in selected:
            row = rows[(a, b)]
            row.update({
                "RUN_STATUS": "RUNNING",
                "ARTIFACT_QA_STATUS": "NOT_RUN",
                "GIT_COMMIT": original_head,
                "FAILURE_REASON": "",
            })
            _write_index(rows)
            config_bytes = _case_config(original, a, b)
            _atomic_write(USER_CASE, config_bytes)
            current_write = config_bytes
            dry = subprocess.run(
                ["./try.sh", "--dry-run"], cwd=SERIES,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=False,
            )
            if dry.returncode != 0:
                row.update({"RUN_STATUS": "NOT_RUN", "ARTIFACT_QA_STATUS": "ARTIFACT_QA_FAIL",
                            "FAILURE_REASON": f"dry-run exit={dry.returncode}: {dry.stdout[-1200:]}"})
                _write_index(rows)
                raise BatchError(f"dry-run failed for A={a}, B={b}; physical solve not called")
            _validate_dry_run(dry.stdout, a, b)
            if USER_CASE.read_bytes() != config_bytes:
                raise BatchError("USER_CASE.env changed between dry-run and solve")
            run = subprocess.run(
                ["./try.sh", "--run-local"], cwd=SERIES,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=False,
            )
            solves += 1
            try:
                summary = json.loads(run.stdout)
            except json.JSONDecodeError as exc:
                row.update({"RUN_STATUS": "ARTIFACT_QA_FAIL", "ARTIFACT_QA_STATUS": "ARTIFACT_QA_FAIL",
                            "FAILURE_REASON": f"runner output not JSON; exit={run.returncode}: {run.stdout[-1200:]}"})
                _write_index(rows)
                raise BatchError(f"runner did not return parseable status for A={a}, B={b}; no retry") from exc
            run_id = summary.get("run_id")
            if not isinstance(run_id, str) or not RUN_ID_RE.fullmatch(run_id) or run_id in {r["RUN_ID"] for r in rows.values()}:
                raise BatchError(f"runner returned invalid/reused RUN_ID for A={a}, B={b}: {run_id!r}")
            run_dir = RUNS / run_id
            row["RUN_ID"] = run_id
            row["RUN_STATUS"] = "ARTIFACT_QA_FAIL"
            row["ARTIFACT_QA_STATUS"] = summary.get("status", "ARTIFACT_QA_FAIL")
            row["RAW_SHA256"] = summary.get("raw_sha256") or ""
            _write_index(rows)
            if run.returncode != 0 or summary.get("status") != "ARTIFACT_QA_PASS" or summary.get("solver_exit_code") != 0:
                row["FAILURE_REASON"] = f"runner exit={run.returncode}; status={summary.get('status')}"
                _write_index(rows)
                raise BatchError(f"solver/mechanical QA failed for A={a}, B={b}; raw preserved; no retry")
            manifest, _ = _verify_run(run_dir)
            if manifest["effective_config"]["CASE_NAME"] != f"SE375_A{a}_B{b}_FULL256":
                raise BatchError(f"run manifest identity mismatch after solve: {run_id}")
            row.update({
                "RUN_STATUS": "COMPLETED",
                "ARTIFACT_QA_STATUS": "ARTIFACT_QA_PASS",
                "RAW_SHA256": manifest["raw_integrity"]["raw_sha256"],
                "GIT_COMMIT": manifest.get("execution_environment", {}).get("parent_head", original_head),
                "SCIENTIFIC_STATUS": "NOT_ANALYZED",
            })
            _write_index(rows)
            archive_fields = _archive_new_run(run_id)
            row.update(archive_fields)
            _write_index(rows)
            print(json.dumps({
                "batch_a": a, "A": a, "B": b, "run_id": run_id,
                "solver_exit_code": 0, "artifact_qa_status": "ARTIFACT_QA_PASS",
                "raw_sha256": row["RAW_SHA256"],
                "archive_status": row["ARCHIVE_STATUS"],
                "cloud_verify_status": row["CLOUD_VERIFY_STATUS"],
                "scientific_status": "NOT_ANALYZED",
            }), flush=True)
    finally:
        if current_write is not None:
            now = USER_CASE.read_bytes()
            if now == current_write:
                _atomic_write(USER_CASE, original)
            elif now != original:
                raise BatchError("USER_CASE.env changed externally; preserved unexpected contents instead of overwriting")
    print(json.dumps({"batch_a": a, "new_physical_solves": solves,
                      "batch_status": "COMPLETE" if all(rows[(a, b)]["RUN_STATUS"].startswith("COMPLETED") for b in range(16)) else "INCOMPLETE",
                      "user_case_restored": USER_CASE.read_bytes() == original}), flush=True)
    return solves


def _check_input_args(args: argparse.Namespace) -> None:
    if args.a is not None and not 0 <= args.a <= 15:
        raise BatchError("--a must be 0..15")
    if args.limit is not None and args.limit < 1:
        raise BatchError("--limit must be positive")
    if args.initialize:
        if args.a is not None or args.limit is not None:
            raise BatchError("--initialize does not take --a or --limit")
    elif args.a is None:
        raise BatchError("select exactly one A row with --a 0..15")
    if args.limit is not None and not args.execute:
        raise BatchError("--limit is only valid with --execute")


def _self_test() -> None:
    pairs = [(a, b) for a in range(16) for b in range(16)]
    if len(pairs) != 256 or len(set(pairs)) != 256:
        raise BatchError("matrix enumerator failed the 256 unique-pair check")
    original, values = _read_env()
    names: set[str] = set()
    for a, b in pairs:
        rendered = _render_env(original, a, b)
        changed = PLATFORM.parse_env_text(rendered.decode("utf-8-sig"))
        for key, value in values.items():
            if key not in {"CASE_NAME", "A", "B"} and changed[key] != value:
                raise BatchError(f"env renderer altered frozen key {key}")
        expected_name = f"SE375_A{a}_B{b}_FULL256"
        if changed["CASE_NAME"] != expected_name or expected_name in names:
            raise BatchError("case-name renderer mismatch")
        names.add(expected_name)
        ctx = PLATFORM.build_case(changed)
        if ctx["topology_qa"]["status"] != "PASS" or ctx["probes"] != list(PLATFORM.DEFAULT_PROBES):
            raise BatchError("platform render self-test failed topology/probe QA")
        checked = ctx["checked"]
        expected_rows = "".join(str((a >> bit) & 1) for bit in range(4))
        expected_columns = "".join(str((b >> (3 - bit)) & 1) for bit in range(4))
        if (checked["row_bits_R1_lsb_first"] != expected_rows or
                checked["column_bits_C1_msb_first"] != expected_columns):
            raise BatchError(f"rendered input mapping mismatch: A={a}, B={b}")
    prior = _batch_index()
    if len(prior) != 24 or len(set(prior) | {(1, 1)}) != 25:
        raise BatchError("historical-input set self-test failed")
    print(json.dumps({
        "status": "SELF_TEST_PASS", "matrix_pairs": len(pairs),
        "historical_unique_inputs": 25, "authorized_new_inputs": len(set(pairs) - set(prior) - {(1, 1)}),
        "env_changes_limited_to": ["CASE_NAME", "A", "B"],
        "static_case_renders": 256,
        "physical_solve_count": 0,
    }, indent=2))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--self-test", action="store_true", help="check matrix/env/render invariants only; no files or solver")
    mode.add_argument("--initialize", action="store_true", help="validate the existing 25 and create the 256-row index")
    mode.add_argument("--dry-run", action="store_true", help="validate one A row and print missing inputs; no files or solver")
    mode.add_argument("--execute", action="store_true", help="run only missing inputs for one A row, in B order")
    parser.add_argument("--a", type=int, help="one multiplicand A row (0..15)")
    parser.add_argument("--limit", type=int, help="execute at most N missing inputs; used for the authorized smoke run")
    args = parser.parse_args(argv)
    try:
        if args.self_test:
            _self_test()
            return 0
        _check_input_args(args)
        _read_env()
        _check_scope()
        index = _read_index()
        if args.initialize:
            if index is None:
                index = _new_index()
                _write_index(index)
                print(json.dumps({"status": "INDEX_INITIALIZED", "rows": 256,
                                  "existing_valid_inputs": sum(bool(row["RUN_ID"]) for row in index.values()),
                                  "remaining_authorized_solves": sum(not row["RUN_ID"] for row in index.values()),
                                  "index_path": str(FULL_INDEX)}, indent=2))
            else:
                manifests = _validate_index_against_runs(index, deep_a=None)
                print(json.dumps({"status": "INDEX_VALID", "rows": len(index),
                                  "manifest_count": len(manifests), "index_path": str(FULL_INDEX)}, indent=2))
            return 0
        if index is None:
            raise BatchError("run --initialize first; index creation is a separate pre-solve step")
        manifests = _validate_index_against_runs(index, deep_a=args.a)
        _print_plan(args.a, index, args.limit)
        if args.dry_run:
            print(json.dumps({"solver_invoked": False, "run_dirs_seen": len(manifests),
                              "worktree_unchanged": True}, indent=2))
            return 0
        return 0 if _execute_batch(args.a, index, args.limit) >= 0 else 1
    except (BatchError, OSError, ValueError, KeyError, TypeError, json.JSONDecodeError,
            PLATFORM.PlatformError, zipfile.BadZipFile) as exc:
        print(f"BATCH_STOP: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
