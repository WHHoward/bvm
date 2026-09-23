#!/usr/bin/env python3
"""Create and reopen-QA the immutable raw handoff ZIP."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

from common import ROOT, cases, read_json, run_dir, sha256, write_json

ZIP_PATH = ROOT / "handoff" / "bvm-bq-cb-gap-2x1-v2-20260923_raw_handoff.zip"
QA_PATH = ROOT / "handoff" / "PACKAGE_QA.json"
EXCLUDED_NAMES = {"__pycache__", ".git"}


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def archive_files() -> list[Path]:
    paths = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT)
        if any(part in EXCLUDED_NAMES for part in rel.parts) or path.suffix == ".pyc":
            continue
        if path == ZIP_PATH or path == QA_PATH or path.name.endswith(".tmp"):
            continue
        paths.append(path)
    return sorted(paths, key=lambda item: item.relative_to(ROOT).as_posix())


def file_records(paths: list[Path]) -> list[dict[str, Any]]:
    return [{"path": path.relative_to(ROOT).as_posix(), "sha256": sha256(path),
             "bytes": path.stat().st_size} for path in paths]


def run_closure() -> dict[str, dict[str, str]]:
    closure = {}
    for case in cases():
        run_id = case["run_id"]
        directory = run_dir(run_id)
        metadata = read_json(directory / "metadata.json")
        raw = directory / "raw.csv"
        deck = directory / "actual_deck.cir"
        raw_qa = read_json(directory / "analysis" / "raw_qa.json")
        analysis_qa = read_json(directory / "analysis" / "analysis_qa.json")
        independent_qa = read_json(directory / "analysis" / "independent_check.json")
        if metadata.get("raw", {}).get("sha256") != sha256(raw):
            raise RuntimeError(f"raw hash mismatch before packaging: {run_id}")
        if metadata.get("deck", {}).get("sha256") != sha256(deck):
            raise RuntimeError(f"deck hash mismatch before packaging: {run_id}")
        if raw_qa.get("status") != "PASS" or analysis_qa.get("status") != "PASS" or independent_qa.get("status") != "PASS":
            raise RuntimeError(f"per-run raw/mechanical/independent QA is not PASS: {run_id}")
        closure[run_id] = {"raw_path": raw.relative_to(ROOT).as_posix(), "raw_sha256": sha256(raw),
                           "deck_path": deck.relative_to(ROOT).as_posix(), "deck_sha256": sha256(deck),
                           "metadata_path": (directory / "metadata.json").relative_to(ROOT).as_posix(),
                           "source_manifest_path": (directory / "source_manifest.json").relative_to(ROOT).as_posix(),
                           "independent_check_path": (directory / "analysis" / "independent_check.json").relative_to(ROOT).as_posix(),
                           "independent_check_sha256": sha256(directory / "analysis" / "independent_check.json")}
    return closure


def package() -> dict[str, Any]:
    result = read_json(ROOT / "result.json")
    if result.get("status") != "EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW":
        raise RuntimeError("result is not finalized at the required review boundary")
    preflight = read_json(ROOT / "analysis" / "PREFLIGHT_QA.json")
    execution = read_json(ROOT / "analysis" / "EXECUTION.json")
    plot_qa = read_json(ROOT / "qa" / "plot_qa.json")
    compare_qa = read_json(ROOT / "qa" / "comparison_qa.json")
    if preflight.get("status") != "PASS" or execution.get("status") != "ALL_FOUR_SOLVES_RAW_AND_INDEPENDENT_QA_PASS":
        raise RuntimeError("preflight/execution QA did not pass")
    if plot_qa.get("status") != "PASS" or compare_qa.get("status") != "PASS":
        raise RuntimeError("standalone/comparison visualization QA did not pass")
    if ZIP_PATH.exists():
        raise RuntimeError(f"immutable package already exists; refusing overwrite: {ZIP_PATH}")
    closure = run_closure()
    paths = archive_files()
    required = {
        "PREFLIGHT.md", "experiment.yaml", "REGRESSION_MATRIX.json", "README.md",
        "RESULT_BRIEF.md", "result.json", "EVIDENCE_MANIFEST.md",
        "RAW_ANALYSIS_HANDOFF_MANIFEST.json", "analysis/PREFLIGHT_QA.json",
        "analysis/SOURCE_LOCK.json", "analysis/EXECUTION.json",
        "analysis/plot_manifest.json", "qa/plot_qa.json", "qa/comparison_qa.json",
        "analysis/TRANSFORMATION_REGISTRY.json", "analysis/PHASE_AREA_MAPPING.json",
        "analysis/comparison_summary.json", "analysis/REVIEW.md", "analysis/NUMERICAL_REVIEW.md",
        "references/METRIC_SPEC_V2.md", "references/V1_INCIDENT_REPORT.md",
        "plots/index.html", "plots/comparison/index.html",
    }
    all_rel = {path.relative_to(ROOT).as_posix() for path in paths}
    missing = sorted(required - all_rel)
    if missing:
        raise RuntimeError(f"required handoff items missing: {missing}")
    for run_id, item in closure.items():
        required_run = [item["raw_path"], item["deck_path"], item["metadata_path"],
                        item["source_manifest_path"], f"runs/{run_id}/stimulus.inc",
                        f"runs/{run_id}/stdout.txt", f"runs/{run_id}/stderr.txt",
                        f"runs/{run_id}/run.log",
                        f"runs/{run_id}/solve_receipt.json", f"runs/{run_id}/analysis/raw_qa.json",
                        f"runs/{run_id}/analysis/analysis_qa.json", f"runs/{run_id}/analysis/metrics.json",
                        f"runs/{run_id}/analysis/independent_check.json",
                        f"plots/{run_id}/review.html", f"plots/{run_id}/stimulus.html"]
        absent = [name for name in required_run if name not in all_rel]
        if absent:
            raise RuntimeError(f"incomplete package closure for {run_id}: {absent}")
        raw_path = ROOT / item["raw_path"]
        if raw_path.stat().st_size >= 100_000_000:
            raise RuntimeError(f"raw exceeds ordinary Git single-file limit; stop for storage policy review: {raw_path}")
    records = file_records(paths)
    ZIP_PATH.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(ZIP_PATH, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in paths:
            archive.write(path, path.relative_to(ROOT).as_posix())

    archive_hash = sha256(ZIP_PATH)
    archive_bytes = ZIP_PATH.stat().st_size
    with zipfile.ZipFile(ZIP_PATH, "r") as archive:
        bad_member = archive.testzip()
        if bad_member:
            raise RuntimeError(f"ZIP CRC validation failed: {bad_member}")
        names = set(archive.namelist())
        if len(names) != len(records):
            raise RuntimeError("ZIP member count differs from expected file count")
        member_hashes = {}
        for record in records:
            data = archive.read(record["path"])
            actual = hashlib.sha256(data).hexdigest()
            member_hashes[record["path"]] = actual
            if actual != record["sha256"] or len(data) != record["bytes"]:
                raise RuntimeError(f"ZIP member hash/size mismatch: {record['path']}")
        for run_id, item in closure.items():
            if member_hashes.get(item["raw_path"]) != item["raw_sha256"] or member_hashes.get(item["deck_path"]) != item["deck_sha256"]:
                raise RuntimeError(f"reopened ZIP run evidence mismatch: {run_id}")
            archived_meta = json.loads(archive.read(item["metadata_path"]))
            if archived_meta.get("raw", {}).get("sha256") != item["raw_sha256"]:
                raise RuntimeError(f"archived metadata raw hash mismatch: {run_id}")
            archived_independent = json.loads(archive.read(item["independent_check_path"]))
            if (archived_independent.get("status") != "PASS" or
                    member_hashes.get(item["independent_check_path"]) != item["independent_check_sha256"]):
                raise RuntimeError(f"archived independent arithmetic QA invalid: {run_id}")
        if not required.issubset(names):
            raise RuntimeError("reopened ZIP is missing required handoff members")
        archived_plot_qa = json.loads(archive.read("qa/plot_qa.json"))
        archived_compare_qa = json.loads(archive.read("qa/comparison_qa.json"))
        if archived_plot_qa.get("status") != "PASS" or archived_compare_qa.get("status") != "PASS":
            raise RuntimeError("visualization QA is not PASS inside reopened archive")

    qa = {"schema": "bvm-bq-cb-gap-package-qa-v2", "status": "PASS",
          "package_path": ZIP_PATH.relative_to(ROOT).as_posix(),
          "package_sha256": archive_hash, "package_bytes": archive_bytes,
          "file_count": len(records), "included_file_sha256": {item["path"]: item["sha256"] for item in records},
          "authorized_run_ids": [case["run_id"] for case in cases()],
          "cumulative_solver_invocations_including_v1_incident": 5,
          "v1_incident_data_included": False,
          "run_evidence": closure, "preflight_status": preflight["status"],
          "raw_mechanical_qa": "PASS", "independent_raw_arithmetic_qa": "PASS",
          "standalone_plot_qa": plot_qa["status"],
          "comparison_plot_qa": compare_qa["status"],
          "reopened_archive_verified": True, "archive_crc_verified": True,
          "raws_immutable_and_hash_checked": True,
          "ordinary_git_single_file_limit_bytes": 100_000_000,
          "storage_policy": "ordinary_git; no Git LFS or external storage",
          "storage_policy_review_recommended": archive_bytes >= 100_000_000,
          "created_at": now()}
    write_json(QA_PATH, qa)
    return qa


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def main() -> int:
    parser = argparse.ArgumentParser(description="Package all authorized raw evidence and QA the reopened ZIP")
    parser.add_argument("--dry-run", action="store_true", help="validate the planned archive closure without writing ZIP")
    args = parser.parse_args()
    if args.dry_run:
        closure = run_closure()
        paths = archive_files()
        print(json.dumps({"package_path": ZIP_PATH.relative_to(ROOT).as_posix(),
                          "authorized_runs": list(closure), "run_raw_bytes": {
                              run_id: (ROOT / item["raw_path"]).stat().st_size for run_id, item in closure.items()},
                          "expected_file_count": len(paths), "physical_solve_executed": False,
                          "package_created": False}, ensure_ascii=False, indent=2))
        return 0
    qa = package()
    print(json.dumps(qa, ensure_ascii=False, indent=2))
    return 0 if qa["status"] == "PASS" else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError, json.JSONDecodeError, zipfile.BadZipFile) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
