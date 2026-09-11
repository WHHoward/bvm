#!/usr/bin/env python3
"""Build and verify the Stage A evidence-only ZIP."""

from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from pathlib import Path


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
PACKAGE_RELATIVE = "handoff/bvm-closed-boundary-current-replay-rj2p12-l1p14-l2p20-ib260-rj32-bjs400-v1-20260911_raw_handoff.zip"
RUN = "CLOSED_CURRENT_REPLAY_N2_0011_RJ2P12"
REF = "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_0011"
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
    execution = read_json("qa/execution_summary.json")
    raw = read_json("qa/raw_qa.json")
    deck = read_json("qa/deck_diff_qa.json")
    protocol = read_json("qa/protocol_audit.json")
    response = read_json("qa/stage_a_response_qa.json")
    independent = read_json("qa/independent_review.json")
    viz = read_json("qa/visualization_qa.json")
    mechanical = read_json("mechanical_summary.json")
    failures = [f"{name} status={value.get('status')}" for name, value in {"raw": raw, "deck": deck, "protocol": protocol, "response": response, "independent": independent, "viz": viz, "mechanical": mechanical}.items() if value.get("status") != "PASS"]
    if execution.get("status") != "PASS" or execution.get("solver_solve_invocations") != 1 or execution.get("exact_physical_solve_count") != 1 or execution.get("stage_b_started") is not False or execution.get("unauthorized_extra_solves") != 0:
        failures.append("execution is not exact one-solve Stage A PASS")
    if read_json("analysis/preflight.json").get("stage_b", {}).get("source_copied") is not False:
        failures.append("Stage B source was copied")
    package = build_package(EXP, package_path=PACKAGE_RELATIVE, physics_solve_count=1, scientific_analysis_performed=False, include_plots=False)
    zip_path = EXP / PACKAGE_RELATIVE
    with zipfile.ZipFile(zip_path) as archive:
        names = archive.namelist()
        name_set = set(names)
        required = {"experiment.yaml", "PREFLIGHT.md", "SOURCE_MANIFEST.json", "HANDOFF_README.md", "RESULT_BRIEF.md", "EVIDENCE_MANIFEST.md", "RAW_ANALYSIS_HANDOFF_MANIFEST.json", "mechanical_summary.json", "visualization/manifest.json", "qa/raw_qa.json", "qa/deck_diff_qa.json", "qa/provenance.json", "qa/execution_summary.json", "qa/transformation_registry.json", "qa/protocol_audit.json", "qa/stage_a_response_qa.json", "qa/independent_review.json", "qa/visualization_qa.json", "analysis/STAGE_A_REVIEW.md", "analysis/mechanism_metrics.json", "data/CLOSED_LOOP_N2_I_BJSL8_source.csv", f"references/closed_loop_rj2p12/{REF}/raw.csv"}
        failures.extend(f"missing package entry: {name}" for name in sorted(required - name_set))
        for relative in ("deck.cir", "raw.csv", "metadata.json", "run.log"):
            if f"runs/{RUN}/{relative}" not in name_set:
                failures.append(f"missing Stage A artifact: {relative}")
            if f"references/closed_loop_rj2p12/{REF}/{relative}" not in name_set:
                failures.append(f"missing source reference artifact: {relative}")
        if len(names) != len(name_set) or archive.testzip() is not None:
            failures.append("ZIP duplicate names or CRC failure")
        if any(name.startswith("visualization/plots/") for name in name_set):
            failures.append("plots unexpectedly included in raw handoff")
        if any(name.endswith(".pyc") or "__pycache__/" in name for name in name_set):
            failures.append("cache artifact included")
        for relative in ("raw.csv", "deck.cir"):
            local = EXP / "runs" / RUN / relative
            archived = f"runs/{RUN}/{relative}"
            if archived in name_set and hashlib.sha256(archive.read(archived)).hexdigest() != sha256(local):
                failures.append(f"run archive hash mismatch: {relative}")
        for relative in ("raw.csv", "deck.cir", "metadata.json", "run.log"):
            local = EXP / "references/closed_loop_rj2p12" / REF / relative
            archived = f"references/closed_loop_rj2p12/{REF}/{relative}"
            if archived in name_set and hashlib.sha256(archive.read(archived)).hexdigest() != sha256(local):
                failures.append(f"reference archive hash mismatch: {relative}")
        snapshot = EXP / "data/CLOSED_LOOP_N2_I_BJSL8_source.csv"
        if hashlib.sha256(archive.read("data/CLOSED_LOOP_N2_I_BJSL8_source.csv")).hexdigest() != sha256(snapshot):
            failures.append("source snapshot archive hash mismatch")
    qa_path = EXP / "handoff/PACKAGE_QA.json"
    qa = json.loads(qa_path.read_text(encoding="utf-8"))
    qa.update({"status": "PASS" if not failures and package.get("status") == "PASS" else "FAIL", "package_path": PACKAGE_RELATIVE, "canonical_zip_sha256": sha256(zip_path), "canonical_zip_bytes": zip_path.stat().st_size, "new_physical_solve_count": 1, "stage_b_started": False, "scientific_analysis_performed": False, "zip_committed": False, "custom_package_qa_failures": failures, "package_authority": "Git authoritative; Drive local analysis mirror only"})
    qa_path.write_text(json.dumps(qa, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": qa["status"], "package": str(zip_path), "sha256": qa["canonical_zip_sha256"], "bytes": qa["canonical_zip_bytes"], "new_physical_solve_count": 1, "stage_b_started": False, "failures": failures}, ensure_ascii=False, indent=2))
    return 0 if qa["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
