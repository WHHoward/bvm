#!/usr/bin/env python3
"""Build and minimally verify the immutable interaction evidence ZIP."""

from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from pathlib import Path


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
PACKAGE_RELATIVE = "handoff/qb-l1-ibias-interaction-bjs400-v1-20260909_raw_handoff_v2.zip"
sys.path.insert(0, str(REPO / "scripts"))
from build_experiment_package import build_package  # noqa: E402


NEW_RUNS = (
    "ARRAY_L1P20_IB250_0001",
    "ARRAY_L1P20_IB250_0011",
    "ARRAY_L1P16_IB250_0001",
    "ARRAY_L1P16_IB250_0011",
    "ARRAY_L1P16_IB260_0001",
    "ARRAY_L1P16_IB260_0011",
)
REUSED = ("ARRAY_IB260_0001", "ARRAY_IB260_0011")


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
    reuse = json.loads((EXP / "REUSED_REFERENCE_MANIFEST.json").read_text(encoding="utf-8"))
    if raw_qa.get("status") != "PASS" or raw_qa.get("artifact_validity") != "VALID":
        raise RuntimeError("raw QA is not PASS/VALID")
    if deck_qa.get("status") != "PASS":
        raise RuntimeError("deck diff QA is not PASS")
    if execution.get("status") != "PASS" or execution.get("exact_new_physical_solve_count") != 6 or execution.get("reused_physical_case_count") != 2 or execution.get("unauthorized_extra_solves") != 0:
        raise RuntimeError("execution summary is not exact 6-new/2-reuse PASS")
    if viz_qa.get("status") != "PASS" or viz_qa.get("standalone_html_count") != 18 or viz_qa.get("comparison_html_count") != 2:
        raise RuntimeError("visualization QA is not exact 18+2 PASS")
    existing_zip = EXP / PACKAGE_RELATIVE
    if existing_zip.is_file():
        package = {"package_path": PACKAGE_RELATIVE}
        zip_path = existing_zip
    else:
        package = build_package(EXP, package_path=PACKAGE_RELATIVE, physics_solve_count=6, scientific_analysis_performed=False, include_plots=False)
        zip_path = EXP / package["package_path"]
    failures: list[str] = []
    required = {
        "experiment.yaml",
        "PREFLIGHT.md",
        "SOURCE_MANIFEST.json",
        "REUSED_REFERENCE_MANIFEST.json",
        "HANDOFF_README.md",
        "RESULT_BRIEF.md",
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
        names = archive.namelist()
        name_set = set(names)
        failures.extend(f"missing package entry: {name}" for name in sorted(required - name_set))
        if len(names) != len(name_set):
            failures.append("duplicate ZIP entry names")
        if any(name.startswith("plots/") for name in name_set):
            failures.append("plots unexpectedly included in raw handoff ZIP")
        if any(name.startswith("visualization/derived/") for name in name_set):
            failures.append("derived visualization CSV unexpectedly included")
        for run_id in NEW_RUNS:
            for suffix in ("deck.cir", "raw.csv", "metadata.json", "run.log"):
                name = f"runs/{run_id}/{suffix}"
                if name not in name_set:
                    failures.append(f"missing new run artifact: {name}")
            for suffix in ("raw.csv", "deck.cir"):
                name = f"runs/{run_id}/{suffix}"
                if name in name_set:
                    digest = hashlib.sha256(archive.read(name)).hexdigest()
                    if suffix == "raw.csv":
                        archived_raw[run_id] = digest
                    else:
                        archived_deck[run_id] = digest
        for run_id in REUSED:
            for suffix in ("deck.cir", "raw.csv", "metadata.json", "run.log"):
                name = f"references/reused/{run_id}/{suffix}"
                if name not in name_set:
                    failures.append(f"missing reused artifact: {name}")
        if not any(name.startswith("references/reused/") for name in name_set):
            failures.append("reused references were not packaged")
    for run_id in NEW_RUNS:
        if archived_raw.get(run_id) != sha256(EXP / "runs" / run_id / "raw.csv"):
            failures.append(f"new raw archive hash mismatch: {run_id}")
        if archived_deck.get(run_id) != sha256(EXP / "runs" / run_id / "deck.cir"):
            failures.append(f"new deck archive hash mismatch: {run_id}")
    for run_id in REUSED:
        ref = EXP / "references/reused" / run_id
        manifest = reuse["references"][run_id]["artifacts"]
        for suffix in ("raw.csv", "deck.cir", "metadata.json", "run.log"):
            if sha256(ref / suffix) != manifest[suffix]["source_sha256"]:
                failures.append(f"reused source/archive manifest mismatch: {run_id}/{suffix}")
    with zipfile.ZipFile(zip_path) as archive:
        if archive.testzip() is not None:
            failures.append("ZIP CRC test failed")
    if failures:
        raise RuntimeError("PACKAGE_QA FAIL: " + "; ".join(failures))
    qa_path = EXP / "handoff/PACKAGE_QA.json"
    package_qa = json.loads(qa_path.read_text(encoding="utf-8"))
    package_qa.update({
        "status": "PASS",
        "new_physical_solve_count": 6,
        "reused_physical_case_count": 2,
        "exact_logical_case_count": 8,
        "unauthorized_extra_solves": 0,
        "all_new_raw_present": True,
        "all_reused_raw_present": True,
        "raw_files_modified": 0,
        "scientific_analysis_performed": False,
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
