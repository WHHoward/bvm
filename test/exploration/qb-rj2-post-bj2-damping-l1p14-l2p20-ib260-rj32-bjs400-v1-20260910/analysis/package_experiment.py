#!/usr/bin/env python3
"""Build and verify the immutable RJ2 damping evidence ZIP."""

from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from pathlib import Path


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
PACKAGE_RELATIVE = "handoff/qb-rj2-post-bj2-damping-l1p14-l2p20-ib260-rj32-bjs400-v1-20260910_raw_handoff.zip"
sys.path.insert(0, str(REPO / "scripts"))
from build_experiment_package import build_package  # noqa: E402
NEW_RUNS = (
    "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P2_0001", "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P2_0011",
    "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P3_0001", "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P3_0011",
    "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P6_0001", "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P6_0011",
)
REUSED = ("ARRAY_L1P14_IB260_RJ32_0001", "ARRAY_L1P14_IB260_RJ32_0011")


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
    mechanical = json.loads((EXP / "mechanical_summary.json").read_text(encoding="utf-8"))
    if raw_qa.get("status") != "PASS" or raw_qa.get("artifact_validity") != "VALID":
        raise RuntimeError("raw QA is not PASS/VALID")
    if deck_qa.get("status") != "PASS":
        raise RuntimeError("deck QA is not PASS")
    if execution.get("status") != "PASS" or execution.get("exact_new_physical_solve_count") != 6 or execution.get("reused_physical_case_count") != 2 or execution.get("unauthorized_extra_solves") != 0:
        raise RuntimeError("execution QA is not exact 6-new/2-reuse PASS")
    if viz_qa.get("status") != "PASS" or viz_qa.get("standalone_html_count") != 18 or viz_qa.get("comparison_html_count") != 2:
        raise RuntimeError("visualization QA is not exact 18+2 PASS")
    if mechanical.get("status") != "PASS" or mechanical.get("scientific_interpretation_performed") is not False:
        raise RuntimeError("mechanical summary is not PASS/evidence-only")
    package = build_package(EXP, package_path=PACKAGE_RELATIVE, physics_solve_count=6, scientific_analysis_performed=False, include_plots=False)
    zip_path = EXP / package["package_path"]
    required = {
        "experiment.yaml", "PREFLIGHT.md", "SOURCE_MANIFEST.json",
        "REUSED_REFERENCE_MANIFEST.json", "HANDOFF_README.md", "RESULT_BRIEF.md",
        "EVIDENCE_MANIFEST.md", "RAW_ANALYSIS_HANDOFF_MANIFEST.json",
        "mechanical_summary.json", "qa/raw_qa.json", "qa/deck_diff_qa.json",
        "qa/provenance.json", "qa/execution_summary.json",
        "qa/transformation_registry.json", "qa/visualization_qa.json",
        "visualization/manifest.json",
    }
    failures: list[str] = []
    archived_raw: dict[str, str] = {}
    archived_deck: dict[str, str] = {}
    with zipfile.ZipFile(zip_path) as archive:
        names = archive.namelist()
        name_set = set(names)
        failures.extend(f"missing package entry: {name}" for name in sorted(required - name_set))
        if len(names) != len(name_set):
            failures.append("duplicate ZIP entry names")
        if any(name.startswith("plots/") for name in name_set):
            failures.append("plots unexpectedly included in raw handoff ZIP")
        if any(name.startswith("visualization/derived/") for name in name_set):
            failures.append("derived visualization CSV unexpectedly included")
        if any(name.endswith(".pyc") or "__pycache__/" in name for name in name_set):
            failures.append("Python cache artifact unexpectedly included")
        for run_id in NEW_RUNS:
            for suffix in ("deck.cir", "raw.csv", "metadata.json", "run.log"):
                name = f"runs/{run_id}/{suffix}"
                if name not in name_set:
                    failures.append(f"missing new artifact: {name}")
            if f"runs/{run_id}/raw.csv" in name_set:
                archived_raw[run_id] = hashlib.sha256(archive.read(f"runs/{run_id}/raw.csv")).hexdigest()
            if f"runs/{run_id}/deck.cir" in name_set:
                archived_deck[run_id] = hashlib.sha256(archive.read(f"runs/{run_id}/deck.cir")).hexdigest()
        for run_id in REUSED:
            for suffix in ("deck.cir", "raw.csv", "metadata.json", "run.log"):
                name = f"references/reused/{run_id}/{suffix}"
                if name not in name_set:
                    failures.append(f"missing reused artifact: {name}")
    for run_id in NEW_RUNS:
        if archived_raw.get(run_id) != sha256(EXP / "runs" / run_id / "raw.csv"):
            failures.append(f"new raw archive hash mismatch: {run_id}")
        if archived_deck.get(run_id) != sha256(EXP / "runs" / run_id / "deck.cir"):
            failures.append(f"new deck archive hash mismatch: {run_id}")
    with zipfile.ZipFile(zip_path) as archive:
        if archive.testzip() is not None:
            failures.append("ZIP CRC test failed")
        for run_id in REUSED:
            local = EXP / "references/reused" / run_id
            for suffix in ("raw.csv", "deck.cir", "metadata.json", "run.log"):
                name = f"references/reused/{run_id}/{suffix}"
                if hashlib.sha256(archive.read(name)).hexdigest() != sha256(local / suffix):
                    failures.append(f"reused hash mismatch: {run_id}/{suffix}")
    if failures:
        raise RuntimeError("PACKAGE_QA FAIL: " + "; ".join(failures))
    qa_path = EXP / "handoff/PACKAGE_QA.json"
    package_qa = json.loads(qa_path.read_text(encoding="utf-8"))
    package_qa.update({
        "status": "PASS",
        "package_path": PACKAGE_RELATIVE,
        "new_physical_solve_count": 6,
        "reused_physical_case_count": 2,
        "exact_logical_case_count": 8,
        "unauthorized_extra_solves": 0,
        "all_new_raw_present": True,
        "all_reused_raw_present": True,
        "raw_files_modified": 0,
        "scientific_analysis_performed": False,
        "mechanical_summary_present": True,
        "standalone_html_count": 18,
        "comparison_html_count": 2,
        "whole_run_plots_only": True,
        "no_focused_window_plots": True,
        "no_plot_only_duplicate_csv": True,
        "canonical_zip_sha256": sha256(zip_path),
        "canonical_zip_bytes": zip_path.stat().st_size,
        "package_authority": "Git authoritative; Google Drive analysis mirror only",
        "zip_committed": False,
    })
    write_json(qa_path, package_qa)
    print(json.dumps({
        "status": "PASS",
        "package": str(zip_path),
        "sha256": package_qa["canonical_zip_sha256"],
        "bytes": package_qa["canonical_zip_bytes"],
        "files": package_qa["package_file_count"],
        "new_physical_solve_count": 6,
        "reused_physical_case_count": 2,
        "scientific_analysis_performed": False,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
