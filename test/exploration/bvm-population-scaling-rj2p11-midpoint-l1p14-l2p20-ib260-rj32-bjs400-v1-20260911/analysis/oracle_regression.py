#!/usr/bin/env python3
"""Run the generalized navigation oracle on immutable RJ2=12 references."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(EXP / "analysis"))
from bvmtools.raw import read_csv  # noqa: E402
from population_oracle import MAX_RESPONSES, generalized_response_oracle  # noqa: E402


MASKS = ("0001", "0011", "0111", "1111")


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def raw_path(mask: str) -> Path:
    return EXP / "references/rj2p12" / f"ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_{mask}/raw.csv"


def main() -> int:
    failures: list[str] = []
    records: dict[str, object] = {}
    for mask in MASKS:
        path = raw_path(mask)
        if not path.is_file():
            failures.append(f"missing regression raw: {mask}")
            continue
        oracle = generalized_response_oracle(read_csv(path))
        records[mask] = {"raw_path": str(path.relative_to(REPO)), "response_count_candidate": oracle["response_count_candidate"], "status": oracle["status"], "response_statuses": [record["status"] for record in oracle["response_records"]], "phase_thresholds": [record["phase_landmark_times_ps"] for record in oracle["response_records"]], "voltage_cluster_counts": oracle["voltage_signal_cluster_counts"], "terminal_status": oracle["terminal_pulse_analysis"]["status"], "hamming_weight_used_as_oracle_input": oracle["hamming_weight_used_as_oracle_input"]}
        if oracle.get("hamming_weight_used_as_oracle_input") is not False:
            failures.append(f"{mask}: oracle reports hamming-weight coupling")
    if MAX_RESPONSES != 4:
        failures.append(f"oracle max response support is not 4: {MAX_RESPONSES}")
    snapshot = {"schema": "bjs400-rj2p11-n-response-oracle-regression-v1", "experiment_id": EXP.name, "created_at_local": now(), "marker": "ORACLE_REGRESSION_PASS" if not failures else "ORACLE_REGRESSION_FAIL", "status": "PASS" if not failures else "FAIL", "physical_solve_count": 0, "raw_files_modified": 0, "reference_cases": list(MASKS), "max_supported_responses": MAX_RESPONSES, "response_thresholds_turns": [index - 0.5 for index in range(1, MAX_RESPONSES + 1)], "hamming_weight_used_as_oracle_input": False, "scientific_authority": "raw waveform; this regression is subordinate mechanical QA", "cases": records, "failures": failures, "scientific_interpretation_performed": False}
    (EXP / "qa").mkdir(parents=True, exist_ok=True)
    (EXP / "qa/oracle_regression.json").write_text(json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lines = ["# RJ2=11 midpoint generalized oracle regression", "", snapshot["marker"], "", f"Status: `{snapshot['status']}`. No solver was invoked and no raw file was modified.", "", "The detector supports navigation response indices 1–4 using cumulative 0.5, 1.5, 2.5 and 3.5 turn thresholds from the common FINAL-origin baseline. Hamming weight is not passed to the detector. RJ2=12 references are used only to exercise the navigation code before RJ2=11 solves.", "", "| reference mask | response candidates reported | terminal segmentation |", "|:---:|---:|:---|"]
    for mask in MASKS:
        row = records.get(mask, {})
        lines.append(f"| {mask} | {row.get('response_count_candidate')} | {row.get('terminal_status')} |")
    lines.extend(["", "Phase landmarks, voltage clusters and terminal pulse-local areas are supporting mechanical evidence; no response candidate is labeled an SFQ count.", ""])
    (EXP / "analysis/ORACLE_REGRESSION.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"status": snapshot["status"], "marker": snapshot["marker"], "physical_solve_count": 0, "raw_files_modified": 0, "reference_response_counts": {mask: value.get("response_count_candidate") for mask, value in records.items()}, "failures": failures}, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
