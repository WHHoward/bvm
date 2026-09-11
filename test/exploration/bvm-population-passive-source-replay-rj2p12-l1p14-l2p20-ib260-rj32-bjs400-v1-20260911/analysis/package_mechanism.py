#!/usr/bin/env python3
"""Build and post-archive-QA the immutable evidence-only handoff."""

from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from pathlib import Path


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
PACKAGE_RELATIVE = "handoff/bvm-population-passive-source-replay-rj2p12-l1p14-l2p20-ib260-rj32-bjs400-v1-20260911_raw_handoff.zip"
PASSIVE = ("PASSIVE_N2_0011", "PASSIVE_N3_0111", "PASSIVE_N4_1111")
REPLAY = ("REPLAY_N2_0011_RJ2P12", "REPLAY_N3_0111_RJ2P12", "REPLAY_N4_1111_RJ2P12")
REFERENCES = ("ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_0011", "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_0111", "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_1111")

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
    raw = read_json("qa/raw_qa.json")
    deck = read_json("qa/deck_diff_qa.json")
    protocol = read_json("qa/protocol_audit.json")
    replay_fidelity = read_json("qa/replay_fidelity_qa.json")
    replay_preflight = read_json("qa/replay_preflight.json")
    independent = read_json("qa/independent_review.json")
    response = read_json("qa/response_qa.json")
    viz = read_json("qa/visualization_qa.json")
    mechanical = read_json("mechanical_summary.json")
    required_pass = {"raw": raw, "deck": deck, "protocol": protocol, "replay_fidelity": replay_fidelity, "replay_preflight": replay_preflight, "independent": independent, "response": response, "viz": viz, "mechanical": mechanical}
    failures = [f"{name} status={item.get('status')}" for name, item in required_pass.items() if item.get("status") != "PASS"]
    if execution.get("status") != "PASS" or execution.get("total_solver_solve_invocations") != 6 or execution.get("exact_total_physical_solve_count") != 6 or execution.get("unauthorized_extra_solves") != 0:
        failures.append("combined execution is not exact six-solve PASS")
    if tuple(execution.get("run_order", ())) != PASSIVE + REPLAY:
        failures.append("combined execution order mismatch")
    package = build_package(EXP, package_path=PACKAGE_RELATIVE, physics_solve_count=6, scientific_analysis_performed=False, include_plots=False)
    zip_path = EXP / PACKAGE_RELATIVE
    with zipfile.ZipFile(zip_path) as archive:
        names = archive.namelist()
        name_set = set(names)
        if len(names) != len(name_set):
            failures.append("ZIP duplicate entry names")
        if archive.testzip() is not None:
            failures.append("ZIP CRC failure")
        if any(name.startswith("visualization/plots/") for name in name_set):
            failures.append("plots were included despite include_plots=false")
        if any(name.endswith(".pyc") or "__pycache__/" in name for name in name_set):
            failures.append("Python cache artifact included")
        required = {
            "experiment.yaml", "PREFLIGHT.md", "SOURCE_MANIFEST.json", "HANDOFF_README.md", "RESULT_BRIEF.md", "EVIDENCE_MANIFEST.md", "RAW_ANALYSIS_HANDOFF_MANIFEST.json", "mechanical_summary.json", "visualization/manifest.json", "qa/raw_qa.json", "qa/deck_diff_qa.json", "qa/provenance.json", "qa/execution_summary_combined.json", "qa/transformation_registry.json", "qa/protocol_audit.json", "qa/replay_fidelity_qa.json", "qa/replay_preflight.json", "qa/response_qa.json", "qa/independent_review.json", "qa/visualization_qa.json", "analysis/MECHANISM_REVIEW.md", "analysis/mechanism_metrics.json", "analysis/replay_source_manifest.json", "data/PASSIVE_N2_0011_JSL8_source.csv", "data/PASSIVE_N3_0111_JSL8_source.csv", "data/PASSIVE_N4_1111_JSL8_source.csv",
        }
        failures.extend(f"missing package entry: {name}" for name in sorted(required - name_set))
        for run in PASSIVE + REPLAY:
            for suffix in ("deck.cir", "raw.csv", "metadata.json", "run.log"):
                if f"runs/{run}/{suffix}" not in name_set:
                    failures.append(f"missing run artifact: {run}/{suffix}")
        for run in REFERENCES:
            for suffix in ("deck.cir", "raw.csv", "metadata.json", "run.log"):
                if f"references/closed_loop_rj2p12/{run}/{suffix}" not in name_set:
                    failures.append(f"missing reference artifact: {run}/{suffix}")
        for run in PASSIVE:
            name = f"data/{run}_JSL8_source.csv"
            if name not in name_set:
                failures.append(f"missing source snapshot: {name}")
        for relative in ("raw.csv", "deck.cir"):
            for run in PASSIVE + REPLAY:
                local = EXP / "runs" / run / relative
                archived = f"runs/{run}/{relative}"
                if archived in name_set and hashlib.sha256(archive.read(archived)).hexdigest() != sha256(local):
                    failures.append(f"run archive hash mismatch: {run}/{relative}")
        for run in REFERENCES:
            for relative in ("raw.csv", "deck.cir", "metadata.json", "run.log"):
                local = EXP / "references/closed_loop_rj2p12" / run / relative
                archived = f"references/closed_loop_rj2p12/{run}/{relative}"
                if archived in name_set and hashlib.sha256(archive.read(archived)).hexdigest() != sha256(local):
                    failures.append(f"reference archive hash mismatch: {run}/{relative}")
        for run in PASSIVE:
            local = EXP / "data" / f"{run}_JSL8_source.csv"
            archived = f"data/{run}_JSL8_source.csv"
            if archived in name_set and hashlib.sha256(archive.read(archived)).hexdigest() != sha256(local):
                failures.append(f"source snapshot archive hash mismatch: {run}")
    qa_path = EXP / "handoff/PACKAGE_QA.json"
    qa = json.loads(qa_path.read_text(encoding="utf-8"))
    qa.update({"status": "PASS" if not failures and package.get("status") == "PASS" else "FAIL", "package_path": PACKAGE_RELATIVE, "canonical_zip_sha256": sha256(zip_path), "canonical_zip_bytes": zip_path.stat().st_size, "new_physical_solve_count": 6, "reference_case_count": 3, "logical_case_count": 6, "unauthorized_extra_solves": 0, "scientific_analysis_performed": False, "standalone_html_count": 21, "comparison_html_count": 7, "zip_committed": False, "package_authority": "Git authoritative; local Drive mirror is a byte-identical analysis mirror only", "custom_package_qa_failures": failures})
    qa_path.write_text(json.dumps(qa, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    result = {"status": qa["status"], "package": str(zip_path), "sha256": qa["canonical_zip_sha256"], "bytes": qa["canonical_zip_bytes"], "new_physical_solve_count": 6, "reference_case_count": 3, "failures": failures}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if qa["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
