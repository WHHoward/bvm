#!/usr/bin/env python3
"""Build and verify the final two-solve Stage A/Stage B evidence ZIP."""

from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from pathlib import Path


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
PACKAGE_RELATIVE = "handoff/bvm-closed-boundary-current-replay-rj2p12-l1p14-l2p20-ib260-rj32-bjs400-v1-20260911_stage-b-v1_raw_handoff.zip"
RUNS = ("CLOSED_CURRENT_REPLAY_N2_0011_RJ2P12", "CLOSED_CURRENT_REPLAY_N3_0111_RJ2P12")
REFERENCES = ("ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_0011", "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_0111")
sys.path.insert(0, str(REPO / "scripts"))
from build_experiment_package import build_package  # noqa: E402


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(relative: str) -> dict:
    return json.loads((EXP / relative).read_text(encoding="utf-8"))


def main() -> int:
    execution = read_json("qa/execution_summary_combined.json")
    stage_a_execution = read_json("qa/execution_summary.json")
    raw = read_json("qa/raw_qa_stage_b.json")
    deck = read_json("qa/deck_diff_qa_stage_b.json")
    protocol = read_json("qa/protocol_audit_stage_b.json")
    response = read_json("qa/stage_b_response_qa.json")
    scientific = read_json("qa/stage_b_scientific_review.json")
    independent = read_json("qa/independent_review_stage_b.json")
    viz = read_json("qa/visualization_qa_stage_b.json")
    mechanical = read_json("mechanical_summary_stage_b.json")
    failures = [f"{name} status={value.get('status')}" for name, value in {"raw": raw, "deck": deck, "protocol": protocol, "response": response, "scientific": scientific, "independent": independent, "viz": viz, "mechanical": mechanical}.items() if value.get("status") != "PASS"]
    if execution.get("status") != "PASS" or execution.get("total_solver_solve_invocations") != 2 or execution.get("exact_total_physical_solve_count") != 2 or execution.get("unauthorized_extra_solves") != 0 or tuple(execution.get("run_order", ())) != RUNS:
        failures.append("combined execution is not exact two-solve PASS")
    if stage_a_execution.get("status") != "PASS" or stage_a_execution.get("solver_solve_invocations") != 1:
        failures.append("Stage A execution prefix changed")
    if scientific.get("stage_b_outcome") != "CLOSED_BOUNDARY_CURRENT_REPLAY_REPRODUCES_N3_FOUR_RESPONSE" or scientific.get("combined_outcome") != "CLOSED_BOUNDARY_CURRENT_REPLAY_REPRODUCES_N2_2_AND_N3_4":
        failures.append("final Stage B outcome marker mismatch")
    package = build_package(EXP, package_path=PACKAGE_RELATIVE, physics_solve_count=2, scientific_analysis_performed=False, include_plots=False)
    zip_path = EXP / PACKAGE_RELATIVE
    with zipfile.ZipFile(zip_path) as archive:
        names = archive.namelist()
        name_set = set(names)
        required = {"experiment.yaml", "PREFLIGHT.md", "SOURCE_MANIFEST.json", "SOURCE_MANIFEST_STAGE_B.json", "HANDOFF_README.md", "RESULT_BRIEF.md", "EVIDENCE_MANIFEST.md", "RAW_ANALYSIS_HANDOFF_MANIFEST.json", "mechanical_summary.json", "mechanical_summary_stage_b.json", "visualization/manifest.json", "qa/raw_qa_stage_b.json", "qa/deck_diff_qa_stage_b.json", "qa/provenance_stage_b.json", "qa/execution_summary_combined.json", "qa/transformation_registry_stage_b.json", "qa/protocol_audit_stage_b.json", "qa/stage_b_response_qa.json", "qa/stage_b_scientific_review.json", "qa/independent_review_stage_b.json", "qa/visualization_qa_stage_b.json", "analysis/STAGE_B_REVIEW.md", "analysis/mechanism_metrics_stage_b.json", "analysis/stage_b_authorization.json", "data/CLOSED_LOOP_N2_I_BJSL8_source.csv", "data/CLOSED_LOOP_N3_I_BJSL8_source.csv"}
        failures.extend(f"missing package entry: {item}" for item in sorted(required - name_set))
        for run in RUNS:
            for suffix in ("deck.cir", "raw.csv", "metadata.json", "run.log"):
                if f"runs/{run}/{suffix}" not in name_set:
                    failures.append(f"missing run artifact: {run}/{suffix}")
        for reference in REFERENCES:
            for suffix in ("deck.cir", "raw.csv", "metadata.json", "run.log"):
                if f"references/closed_loop_rj2p12/{reference}/{suffix}" not in name_set:
                    failures.append(f"missing reference artifact: {reference}/{suffix}")
        if len(names) != len(name_set) or archive.testzip() is not None:
            failures.append("ZIP duplicate names or CRC failure")
        if any(name.startswith("visualization/plots/") for name in name_set):
            failures.append("plots unexpectedly included in raw handoff")
        if any(name.endswith(".pyc") or "__pycache__/" in name for name in name_set):
            failures.append("cache artifact included")
        for run in RUNS:
            for suffix in ("raw.csv", "deck.cir"):
                local = EXP / "runs" / run / suffix
                archived = f"runs/{run}/{suffix}"
                if archived in name_set and hashlib.sha256(archive.read(archived)).hexdigest() != sha256(local):
                    failures.append(f"run archive hash mismatch: {run}/{suffix}")
        for reference in REFERENCES:
            for suffix in ("raw.csv", "deck.cir", "metadata.json", "run.log"):
                local = EXP / "references/closed_loop_rj2p12" / reference / suffix
                archived = f"references/closed_loop_rj2p12/{reference}/{suffix}"
                if archived in name_set and hashlib.sha256(archive.read(archived)).hexdigest() != sha256(local):
                    failures.append(f"reference archive hash mismatch: {reference}/{suffix}")
        for mask in ("N2", "N3"):
            local = EXP / "data" / f"CLOSED_LOOP_{mask}_I_BJSL8_source.csv"
            archived = f"data/CLOSED_LOOP_{mask}_I_BJSL8_source.csv"
            if archived in name_set and hashlib.sha256(archive.read(archived)).hexdigest() != sha256(local):
                failures.append(f"source snapshot archive hash mismatch: {mask}")
    qa_path = EXP / "handoff/PACKAGE_QA.json"
    qa = json.loads(qa_path.read_text(encoding="utf-8"))
    qa.update({"status": "PASS" if not failures and package.get("status") == "PASS" else "FAIL", "package_path": PACKAGE_RELATIVE, "canonical_zip_sha256": sha256(zip_path), "canonical_zip_bytes": zip_path.stat().st_size, "new_physical_solve_count": 2, "stage_a_physical_solve_count": 1, "stage_b_physical_solve_count": 1, "stage_b_started": True, "scientific_analysis_performed": True, "zip_committed": False, "custom_package_qa_failures": failures, "package_authority": "Git authoritative; Drive local analysis mirror only"})
    qa_path.write_text(json.dumps(qa, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": qa["status"], "package": str(zip_path), "sha256": qa["canonical_zip_sha256"], "bytes": qa["canonical_zip_bytes"], "total_physical_solves": 2, "stage_b_outcome": scientific.get("stage_b_outcome"), "failures": failures}, ensure_ascii=False, indent=2))
    return 0 if qa["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
