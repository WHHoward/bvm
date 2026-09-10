#!/usr/bin/env python3
"""Build and mechanically verify the timestep spot-check raw handoff."""

from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from pathlib import Path


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
PACKAGE_RELATIVE = "handoff/qb-rj2p12-timestep-robustness-l1p14-l2p20-ib260-rj32-bjs400-v1-20260910_raw_handoff.zip"
sys.path.insert(0, str(REPO / "scripts"))
from build_experiment_package import build_package  # noqa: E402


NEW_RUNS = ("ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_DT0050_0001", "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_DT0050_0011", "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_DT0025_0001", "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_DT0025_0011")
REUSE_RUNS = ("ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_DT0100_0001", "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_DT0100_0011")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    execution = json.loads((EXP / "qa/execution_summary.json").read_text(encoding="utf-8"))
    raw = json.loads((EXP / "qa/raw_qa.json").read_text(encoding="utf-8"))
    deck = json.loads((EXP / "qa/deck_diff_qa.json").read_text(encoding="utf-8"))
    timestep = json.loads((EXP / "qa/timestep_qa.json").read_text(encoding="utf-8"))
    independent = json.loads((EXP / "qa/independent_review.json").read_text(encoding="utf-8"))
    viz = json.loads((EXP / "qa/visualization_qa.json").read_text(encoding="utf-8"))
    mechanical = json.loads((EXP / "mechanical_summary.json").read_text(encoding="utf-8"))
    if raw.get("status") != "PASS" or raw.get("artifact_validity") != "VALID" or deck.get("status") != "PASS" or timestep.get("status") != "PASS" or independent.get("status") != "PASS" or viz.get("status") != "PASS" or mechanical.get("status") != "PASS":
        raise RuntimeError("one or more timestep evidence QA artifacts are not PASS")
    if execution.get("status") != "PASS" or execution.get("exact_new_physical_solve_count") != 4 or execution.get("solver_solve_invocations") != 4 or execution.get("reused_physical_case_count") != 2 or execution.get("unauthorized_extra_solves") != 0 or tuple(execution.get("run_order", ())) != NEW_RUNS:
        raise RuntimeError("execution summary is not exact 4-new/2-reuse PASS")
    package = build_package(EXP, package_path=PACKAGE_RELATIVE, physics_solve_count=4, scientific_analysis_performed=False, include_plots=False)
    zip_path = EXP / package["package_path"]
    required = {"experiment.yaml", "PREFLIGHT.md", "SOURCE_MANIFEST.json", "REUSED_REFERENCE_MANIFEST.json", "HANDOFF_README.md", "RESULT_BRIEF.md", "EVIDENCE_MANIFEST.md", "RAW_ANALYSIS_HANDOFF_MANIFEST.json", "mechanical_summary.json", "qa/raw_qa.json", "qa/deck_diff_qa.json", "qa/execution_summary.json", "qa/timestep_qa.json", "qa/provenance.json", "qa/transformation_registry.json", "qa/visualization_qa.json", "qa/independent_review.json", "analysis/REVIEW.md", "analysis/TIMESTEP_REVIEW.md", "analysis/second_response_oracle.py", "analysis/independent_timestep_review.py", "visualization/manifest.json"}
    failures: list[str] = []
    with zipfile.ZipFile(zip_path) as archive:
        names = archive.namelist()
        name_set = set(names)
        failures.extend(f"missing package entry: {name}" for name in sorted(required - name_set))
        if len(names) != len(name_set):
            failures.append("duplicate ZIP entry names")
        if any(name.startswith("plots/") for name in name_set):
            failures.append("plots unexpectedly included in raw handoff")
        if any(name.endswith(".pyc") or "__pycache__/" in name for name in name_set):
            failures.append("Python cache artifact unexpectedly included")
        for run_id in NEW_RUNS:
            for suffix in ("deck.cir", "raw.csv", "metadata.json", "run.log"):
                if f"runs/{run_id}/{suffix}" not in name_set:
                    failures.append(f"missing new artifact: {run_id}/{suffix}")
        for run_id in REUSE_RUNS:
            for suffix in ("deck.cir", "raw.csv", "metadata.json", "run.log"):
                if f"references/reused/{run_id}/{suffix}" not in name_set:
                    failures.append(f"missing reused artifact: {run_id}/{suffix}")
        if archive.testzip() is not None:
            failures.append("ZIP CRC test failed")
    for run_id in NEW_RUNS:
        for suffix in ("raw.csv", "deck.cir"):
            local = EXP / "runs" / run_id / suffix
            with zipfile.ZipFile(zip_path) as archive:
                if hashlib.sha256(archive.read(f"runs/{run_id}/{suffix}")).hexdigest() != sha256(local):
                    failures.append(f"new archive hash mismatch: {run_id}/{suffix}")
    if failures:
        raise RuntimeError("PACKAGE_QA FAIL: " + "; ".join(failures))
    qa_path = EXP / "handoff/PACKAGE_QA.json"
    qa = json.loads(qa_path.read_text(encoding="utf-8"))
    qa.update({"status": "PASS", "package_path": PACKAGE_RELATIVE, "new_physical_solve_count": 4, "reused_physical_case_count": 2, "logical_case_count": 6, "unauthorized_extra_solves": 0, "scientific_analysis_performed": False, "canonical_timestep_ps": 0.1, "spot_checked_timestep_ps": [0.05, 0.025], "standalone_html_count": 18, "comparison_html_count": 2, "canonical_zip_sha256": sha256(zip_path), "canonical_zip_bytes": zip_path.stat().st_size, "zip_committed": False, "package_authority": "Git authoritative; Drive analysis mirror only"})
    qa_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "package": str(zip_path), "sha256": qa["canonical_zip_sha256"], "bytes": qa["canonical_zip_bytes"], "new_physical_solve_count": 4, "reused_physical_case_count": 2, "scientific_analysis_performed": False}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
