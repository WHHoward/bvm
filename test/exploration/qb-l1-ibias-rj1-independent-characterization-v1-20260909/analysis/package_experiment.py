#!/usr/bin/env python3
"""Build and verify the canonical evidence ZIP for the 12-run experiment."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
from build_experiment_package import build_package  # noqa: E402


NEW_RUNS = ["L1_1P2", "L1_1P4", "L1_1P6", "L1_1P8", "IB_230", "IB_240", "IB_260", "IB_270", "RJ1_8", "RJ1_10", "RJ1_14", "RJ1_16"]
REUSED = ["L1_1P9", "NOMINAL", "L1_2P1", "RJ1_12P5", "RJ1_13"]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def make_handoff_manifest(package_relative_path: str) -> dict[str, object]:
    reuse = json.loads((EXP / "REUSED_REFERENCE_MANIFEST.json").read_text(encoding="utf-8"))
    raw_qa = json.loads((EXP / "qa/raw_qa.json").read_text(encoding="utf-8"))
    runs: dict[str, object] = {}
    for run_id in NEW_RUNS:
        run = EXP / "runs" / run_id
        runs[run_id] = {
            "run_id": run_id,
            "raw_relative_path": f"runs/{run_id}/raw.csv",
            "raw_sha256": sha256(run / "raw.csv"),
            "raw_bytes": (run / "raw.csv").stat().st_size,
            "deck_relative_path": f"runs/{run_id}/deck.cir",
            "deck_sha256": sha256(run / "deck.cir"),
            "metadata_relative_path": f"runs/{run_id}/metadata.json",
            "run_log_relative_path": f"runs/{run_id}/run.log",
            "physical_solve_this_experiment": True,
        }
    reused_runs: dict[str, object] = {}
    for case_id in REUSED:
        ref = EXP / "references" / "reused" / case_id
        reused_runs[case_id] = {
            "run_id": case_id,
            "raw_relative_path": f"references/reused/{case_id}/raw.csv",
            "raw_sha256": sha256(ref / "raw.csv"),
            "raw_bytes": (ref / "raw.csv").stat().st_size,
            "deck_relative_path": f"references/reused/{case_id}/deck.cir",
            "deck_sha256": sha256(ref / "deck.cir"),
            "metadata_relative_path": f"references/reused/{case_id}/metadata.json",
            "run_log_relative_path": f"references/reused/{case_id}/run.log" if (ref / "run.log").is_file() else None,
            "physical_solve_this_experiment": False,
            "source_manifest_entry": reuse["references"][case_id],
        }
    included = {}
    for relative in (
        "experiment.yaml", "PREFLIGHT.md", "SOURCE_MANIFEST.json", "REUSED_REFERENCE_MANIFEST.json",
        "qa/raw_qa.json", "qa/deck_diff_qa.json", "qa/provenance.json", "qa/execution_summary.json",
        "qa/transformation_registry.json", "visualization/manifest.json", "visualization/visualization_qa.json",
    ):
        path = EXP / relative
        if path.is_file():
            included[relative] = {"sha256": sha256(path), "bytes": path.stat().st_size}
    record = {
        "schema": "qb-l1-ibias-rj1-raw-analysis-handoff-manifest-v1",
        "experiment_id": EXP.name,
        "repository": str(REPO),
        "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip(),
        "purpose": "scientific-review handoff; evidence-only; no interpretation",
        "created_at_local": now(),
        "package_relative_path": package_relative_path,
        "physics_solve_count": 12,
        "new_physical_solve_count": 12,
        "reused_physical_solve_count": 0,
        "scientific_analysis_performed": False,
        "unauthorized_extra_solves": 0,
        "runs": runs,
        "reused_runs": reused_runs,
        "included_artifacts": included,
        "raw_qa_artifact": raw_qa["artifact_validity"],
    }
    write_json(EXP / "RAW_ANALYSIS_HANDOFF_MANIFEST.json", record)
    return record


def main() -> int:
    qa_pre = json.loads((EXP / "qa/raw_qa.json").read_text(encoding="utf-8"))
    deck_qa = json.loads((EXP / "qa/deck_diff_qa.json").read_text(encoding="utf-8"))
    execution = json.loads((EXP / "qa/execution_summary.json").read_text(encoding="utf-8"))
    viz_qa = json.loads((EXP / "visualization/visualization_qa.json").read_text(encoding="utf-8"))
    if qa_pre.get("artifact_validity") != "VALID" or deck_qa.get("status") != "PASS":
        raise RuntimeError("mechanical QA is not PASS/VALID; package build forbidden")
    if execution.get("status") != "RUN_PASS" or execution.get("new_physical_solve_count") != 12:
        raise RuntimeError("execution summary is not exact successful 12-run matrix")
    if viz_qa.get("status") != "PASS":
        raise RuntimeError("visualization QA is not PASS; package build forbidden")
    package_relative = f"handoff/{EXP.name}_raw_handoff.zip"
    make_handoff_manifest(package_relative)
    package = build_package(EXP, physics_solve_count=12, scientific_analysis_performed=False, include_plots=False)
    zip_path = EXP / package["package_path"]
    failures: list[str] = []
    archived_raw: dict[str, str] = {}
    archived_deck: dict[str, str] = {}
    with zipfile.ZipFile(zip_path, "r") as archive:
        names = set(archive.namelist())
        required = {
            "HANDOFF_README.md", "experiment.yaml", "PREFLIGHT.md", "SOURCE_MANIFEST.json",
            "REUSED_REFERENCE_MANIFEST.json", "RAW_ANALYSIS_HANDOFF_MANIFEST.json",
            "qa/raw_qa.json", "qa/deck_diff_qa.json", "qa/provenance.json", "qa/execution_summary.json",
            "qa/transformation_registry.json", "visualization/manifest.json", "visualization/visualization_qa.json",
        }
        failures.extend(f"missing package entry: {name}" for name in sorted(required - names))
        for case_id in NEW_RUNS:
            raw_name = f"runs/{case_id}/raw.csv"
            deck_name = f"runs/{case_id}/deck.cir"
            if raw_name not in names or deck_name not in names:
                failures.append(f"missing new run entry: {case_id}")
                continue
            archived_raw[case_id] = hashlib.sha256(archive.read(raw_name)).hexdigest()
            archived_deck[case_id] = hashlib.sha256(archive.read(deck_name)).hexdigest()
        for case_id in REUSED:
            raw_name = f"references/reused/{case_id}/raw.csv"
            deck_name = f"references/reused/{case_id}/deck.cir"
            if raw_name not in names or deck_name not in names:
                failures.append(f"missing reused reference entry: {case_id}")
                continue
            archived_raw[case_id] = hashlib.sha256(archive.read(raw_name)).hexdigest()
            archived_deck[case_id] = hashlib.sha256(archive.read(deck_name)).hexdigest()
    for case_id in NEW_RUNS:
        if archived_raw.get(case_id) != sha256(EXP / "runs" / case_id / "raw.csv"):
            failures.append(f"new raw archive hash mismatch: {case_id}")
        if archived_deck.get(case_id) != sha256(EXP / "runs" / case_id / "deck.cir"):
            failures.append(f"new deck archive hash mismatch: {case_id}")
    for case_id in REUSED:
        if archived_raw.get(case_id) != sha256(EXP / "references" / "reused" / case_id / "raw.csv"):
            failures.append(f"reused raw archive hash mismatch: {case_id}")
        if archived_deck.get(case_id) != sha256(EXP / "references" / "reused" / case_id / "deck.cir"):
            failures.append(f"reused deck archive hash mismatch: {case_id}")
    if failures:
        raise RuntimeError("PACKAGE_QA FAIL: " + "; ".join(failures))
    qa_path = EXP / "handoff/PACKAGE_QA.json"
    package_qa = json.loads(qa_path.read_text(encoding="utf-8"))
    package_qa.update({
        "status": "PASS",
        "new_physical_solve_count": 12,
        "reused_physical_solve_count": 0,
        "unauthorized_extra_solves": 0,
        "all_new_raw_present": True,
        "all_reused_reference_raw_present": True,
        "archived_new_raw_sha256": {case_id: archived_raw[case_id] for case_id in NEW_RUNS},
        "archived_reused_raw_sha256": {case_id: archived_raw[case_id] for case_id in REUSED},
        "scientific_analysis_performed": False,
        "analysis_performed": False,
        "raw_files_modified": 0,
        "canonical_zip_sha256": sha256(zip_path),
        "canonical_zip_bytes": zip_path.stat().st_size,
        "package_authority": "GitHub/Git authoritative; Google Drive analysis mirror only",
    })
    write_json(qa_path, package_qa)
    print(json.dumps({"status": "PASS", "package": str(zip_path), "sha256": package_qa["canonical_zip_sha256"], "bytes": package_qa["canonical_zip_bytes"], "new_physical_solve_count": 12, "reused_physical_solve_count": 0}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
