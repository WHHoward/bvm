#!/usr/bin/env python3
"""Build and verify the targeted-combination evidence ZIP."""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
import zipfile
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
PACKAGE_RELATIVE = "handoff/bvm-qb-l3-bj2-targeted-combination-v1-20260911_raw_handoff.zip"
sys.path.insert(0, str(REPO / "scripts"))
from build_experiment_package import build_package  # noqa: E402


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO.resolve()).as_posix()


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def clean_cache() -> None:
    cache = EXP / "analysis/__pycache__"
    if cache.is_dir():
        shutil.rmtree(cache)
    for path in EXP.rglob("*.pyc"):
        path.unlink()


def main() -> int:
    clean_cache()
    qa_names = ("raw_qa.json", "deck_diff_qa.json", "provenance.json", "execution_summary.json", "transformation_registry.json", "independent_target.json", "visualization_qa.json")
    qa = {name: json.loads((EXP / "qa" / name).read_text(encoding="utf-8")) for name in qa_names}
    state = json.loads((EXP / "screening/target_state.json").read_text(encoding="utf-8"))
    mechanical = json.loads((EXP / "mechanical_summary.json").read_text(encoding="utf-8"))
    failures: list[str] = []
    for name in qa_names:
        if qa[name].get("status") != "PASS":
            failures.append(f"{name} not PASS")
    if mechanical.get("status") != "PASS" or mechanical.get("scientific_interpretation_performed") is not False:
        failures.append("mechanical summary not PASS/evidence-only")
    if state.get("final_marker") != "EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW":
        failures.append("final marker missing")
    if failures:
        raise RuntimeError("cannot package target evidence: " + "; ".join(failures))
    execution = qa["execution_summary.json"]
    package = build_package(EXP, package_path=PACKAGE_RELATIVE, physics_solve_count=int(execution["actual_new_physical_solve_count"]), scientific_analysis_performed=False, include_plots=False)
    zip_path = EXP / package["package_path"]
    required = {
        "experiment.yaml", "PREFLIGHT.md", "SOURCE_MANIFEST.json", "HANDOFF_README.md", "RESULT_BRIEF.md", "EVIDENCE_MANIFEST.md", "mechanical_summary.json",
        "screening/TARGET_MATRIX.json", "screening/TARGET_TABLE.md", "screening/TARGET_RESULTS.json", "screening/TARGET_RESULTS.md", "qa/raw_qa.json", "qa/deck_diff_qa.json", "qa/provenance.json", "qa/execution_summary.json", "qa/transformation_registry.json", "qa/independent_target.json", "visualization/manifest.json", "qa/visualization_qa.json", "RAW_ANALYSIS_HANDOFF_MANIFEST.json",
    }
    with zipfile.ZipFile(zip_path, "r") as archive:
        names_in_zip = set(archive.namelist())
        failures = [f"missing package entry: {name}" for name in sorted(required - names_in_zip)]
        if len(names_in_zip) != len(archive.namelist()):
            failures.append("duplicate ZIP entry")
        if archive.testzip() is not None:
            failures.append("ZIP CRC failure")
        if any(name.endswith(".pyc") or "__pycache__/" in name or name.endswith(".tmp") for name in names_in_zip):
            failures.append("cache/temporary artifact entered package")
        for run_id in sorted(path.name for path in (EXP / "runs").iterdir() if path.is_dir()):
            for suffix in ("deck.cir", "raw.csv", "metadata.json", "run.log"):
                entry = f"runs/{run_id}/{suffix}"
                if entry not in names_in_zip:
                    failures.append(f"missing run entry: {entry}")
            for suffix in ("deck.cir", "raw.csv"):
                entry = f"runs/{run_id}/{suffix}"
                if entry in names_in_zip and hashlib.sha256(archive.read(entry)).hexdigest() != sha256(EXP / "runs" / run_id / suffix):
                    failures.append(f"archive hash mismatch: {entry}")
        if not any(name.startswith("references/") for name in names_in_zip):
            failures.append("reference artifacts missing")
        if not any(name.startswith("visualization/plots/") for name in names_in_zip):
            failures.append("permanent visualization plots missing")
    if failures:
        raise RuntimeError("PACKAGE_QA FAIL: " + "; ".join(failures))
    qa_path = EXP / "handoff/PACKAGE_QA.json"
    record = json.loads(qa_path.read_text(encoding="utf-8")) if qa_path.is_file() else {}
    record.update({"status": "PASS", "experiment_id": EXP.name, "package_path": PACKAGE_RELATIVE, "canonical_zip_sha256": sha256(zip_path), "canonical_zip_bytes": zip_path.stat().st_size, "logical_new_point_count": 1, "logical_new_case_count": 2, "screening_new_physical_solve_count": execution["screening_new_physical_solve_count"], "actual_new_physical_solve_count": execution["actual_new_physical_solve_count"], "validation_new_physical_solve_count": execution["validation_new_physical_solve_count"], "reference_raw_count": 6, "unauthorized_extra_solve_count": 0, "raw_files_modified": 0, "scientific_analysis_performed": False, "zip_committed": False, "drive_mirror_status": "PENDING_AFTER_COMMIT", "plots_in_package": True})
    write_json(qa_path, record)
    print(json.dumps({"status": "PASS", "package": rel(zip_path), "sha256": record["canonical_zip_sha256"], "bytes": record["canonical_zip_bytes"], "actual_new_physical_solve_count": record["actual_new_physical_solve_count"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
