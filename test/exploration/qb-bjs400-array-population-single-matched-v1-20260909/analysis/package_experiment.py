#!/usr/bin/env python3
"""Build and minimally verify the immutable BJS400 evidence ZIP."""

from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from pathlib import Path


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
from build_experiment_package import build_package  # noqa: E402


RUN_IDS = [
    "ARRAY_L1P12_0000", "ARRAY_L1P12_1000", "ARRAY_L1P12_0001", "ARRAY_L1P12_0011",
    "ARRAY_L1P14_0000", "ARRAY_L1P14_1000", "ARRAY_L1P14_0001", "ARRAY_L1P14_0011",
    "ARRAY_IB260_0000", "ARRAY_IB260_1000", "ARRAY_IB260_0001", "ARRAY_IB260_0011",
    "ARRAY_IB270_0000", "ARRAY_IB270_1000", "ARRAY_IB270_0001", "ARRAY_IB270_0011",
    "SINGLE_L1P12_0", "SINGLE_L1P12_1", "SINGLE_L1P14_0", "SINGLE_L1P14_1",
    "SINGLE_IB260_0", "SINGLE_IB260_1", "SINGLE_IB270_0", "SINGLE_IB270_1",
]
HISTORICAL_SETTINGS = ("L1P12", "L1P14", "IB260", "IB270")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: dict[str, object]) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    raw_qa = json.loads((EXP / "qa/raw_qa.json").read_text(encoding="utf-8"))
    deck_qa = json.loads((EXP / "qa/deck_diff_qa.json").read_text(encoding="utf-8"))
    execution = json.loads((EXP / "qa/execution_summary.json").read_text(encoding="utf-8"))
    viz_qa = json.loads((EXP / "qa/visualization_qa.json").read_text(encoding="utf-8"))
    if raw_qa.get("status") != "PASS" or raw_qa.get("artifact_validity") != "VALID":
        raise RuntimeError("raw QA is not PASS/VALID")
    if deck_qa.get("status") != "PASS":
        raise RuntimeError("deck diff QA is not PASS")
    if execution.get("status") != "PASS" or execution.get("new_physical_solve_count") != 24 or execution.get("unauthorized_extra_solves") != 0:
        raise RuntimeError("execution summary is not exact 24-run PASS")
    if viz_qa.get("status") != "PASS" or viz_qa.get("standalone_html_count") != 144 or viz_qa.get("comparison_html_count") != 20:
        raise RuntimeError("visualization QA is not exact 144+20 PASS")
    package_result = build_package(EXP, physics_solve_count=24, scientific_analysis_performed=False, include_plots=False)
    zip_path = EXP / package_result["package_path"]
    failures: list[str] = []
    required = {
        "experiment.yaml",
        "PREFLIGHT.md",
        "SOURCE_MANIFEST.json",
        "HISTORICAL_BRIDGE_MANIFEST.json",
        "HANDOFF_README.md",
        "EVIDENCE_MANIFEST.md",
        "RAW_ANALYSIS_HANDOFF_MANIFEST.json",
        "qa/raw_qa.json",
        "qa/deck_diff_qa.json",
        "qa/provenance.json",
        "qa/execution_summary.json",
        "qa/transformation_registry.json",
        "qa/visualization_qa.json",
        "visualization/manifest.json",
    }
    archived_raw: dict[str, str] = {}
    archived_deck: dict[str, str] = {}
    with zipfile.ZipFile(zip_path) as archive:
        names = set(archive.namelist())
        failures.extend(f"missing package entry: {name}" for name in sorted(required - names))
        if len(names) != len(archive.namelist()):
            failures.append("duplicate ZIP entry names")
        if any(name.startswith("plots/") for name in names):
            failures.append("rendered plots unexpectedly included in raw handoff ZIP")
        if any(name.startswith("visualization/derived/") for name in names):
            failures.append("derived visualization CSV unexpectedly included in ZIP")
        for run_id in RUN_IDS:
            for suffix in ("deck.cir", "raw.csv", "metadata.json", "run.log"):
                name = f"runs/{run_id}/{suffix}"
                if name not in names:
                    failures.append(f"missing run artifact: {name}")
            raw_name = f"runs/{run_id}/raw.csv"
            deck_name = f"runs/{run_id}/deck.cir"
            if raw_name in names:
                archived_raw[run_id] = hashlib.sha256(archive.read(raw_name)).hexdigest()
            if deck_name in names:
                archived_deck[run_id] = hashlib.sha256(archive.read(deck_name)).hexdigest()
        for setting in HISTORICAL_SETTINGS:
            for suffix in ("deck.cir", "raw.csv", "metadata.json", "run.log"):
                name = f"references/historical_bjs300/{setting}/{suffix}"
                if name not in names:
                    failures.append(f"missing historical bridge artifact: {name}")
    for run_id in RUN_IDS:
        local = EXP / "runs" / run_id
        if archived_raw.get(run_id) != sha256(local / "raw.csv"):
            failures.append(f"new raw hash mismatch: {run_id}")
        if archived_deck.get(run_id) != sha256(local / "deck.cir"):
            failures.append(f"new deck hash mismatch: {run_id}")
    for setting in HISTORICAL_SETTINGS:
        local = EXP / "references/historical_bjs300" / setting
        with zipfile.ZipFile(zip_path) as archive:
            for suffix in ("raw.csv", "deck.cir", "metadata.json", "run.log"):
                name = f"references/historical_bjs300/{setting}/{suffix}"
                if hashlib.sha256(archive.read(name)).hexdigest() != sha256(local / suffix):
                    failures.append(f"historical bridge hash mismatch: {setting}/{suffix}")
    if failures:
        raise RuntimeError("PACKAGE_QA FAIL: " + "; ".join(failures))
    qa_path = EXP / "handoff/PACKAGE_QA.json"
    package_qa = json.loads(qa_path.read_text(encoding="utf-8"))
    package_qa.update({
        "status": "PASS",
        "array_physical_solve_count": 16,
        "single_physical_solve_count": 8,
        "new_physical_solve_count": 24,
        "historical_bridge_reference_count": 4,
        "unauthorized_extra_solves": 0,
        "all_authorized_runs_present": True,
        "all_raw_files_present": True,
        "raw_files_modified": 0,
        "scientific_analysis_performed": False,
        "comparison_html_count": 20,
        "standalone_html_count": 144,
        "whole_run_plots_only": True,
        "no_focused_window_plots": True,
        "no_plot_only_duplicate_csv": True,
        "zip_committed": False,
        "canonical_zip_sha256": sha256(zip_path),
        "canonical_zip_bytes": zip_path.stat().st_size,
        "package_authority": "Git authoritative; Google Drive analysis mirror only",
    })
    write_json(qa_path, package_qa)
    print(json.dumps({
        "status": "PASS",
        "package": str(zip_path),
        "sha256": package_qa["canonical_zip_sha256"],
        "bytes": package_qa["canonical_zip_bytes"],
        "files": package_qa["package_file_count"],
        "array_physical_solve_count": 16,
        "single_physical_solve_count": 8,
        "scientific_analysis_performed": False,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

