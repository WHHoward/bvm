#!/usr/bin/env python3
"""Exercise the mechanical oracle on immutable boundary references only."""

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


CASES = ((10, "0001"), (10, "0011"), (11, "0011"), (11, "0111"), (12, "0011"), (12, "0111"))


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def raw_path(rj2: int, mask: str) -> Path:
    return EXP / f"references/rj2p{rj2}" / f"ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P{rj2}_{mask}/raw.csv"


def main() -> int:
    failures: list[str] = []
    records: dict[str, object] = {}
    for rj2, mask in CASES:
        path = raw_path(rj2, mask)
        key = f"RJ2P{rj2}_{mask}"
        if not path.is_file():
            failures.append(f"missing reference raw: {key}")
            continue
        oracle = generalized_response_oracle(read_csv(path))
        records[key] = {"raw_path": str(path.relative_to(REPO)), "response_count_candidate": oracle["response_count_candidate"], "status": oracle["status"], "response_statuses": [record["status"] for record in oracle["response_records"]], "phase_thresholds": [record["phase_landmark_times_ps"] for record in oracle["response_records"]], "voltage_cluster_counts": oracle["voltage_signal_cluster_counts"], "terminal_status": oracle["terminal_pulse_analysis"]["status"], "hamming_weight_used_as_oracle_input": oracle["hamming_weight_used_as_oracle_input"]}
        if oracle["hamming_weight_used_as_oracle_input"] is not False:
            failures.append(f"{key}: oracle reports hamming-weight coupling")
    if records.get("RJ2P10_0001", {}).get("response_count_candidate") != 1:
        failures.append("RJ2P10_0001: known single-response regression changed")
    if records.get("RJ2P10_0011", {}).get("response_count_candidate") != 1:
        failures.append("RJ2P10_0011: known weight-2 one-response regression changed")
    if records.get("RJ2P10_0011", {}).get("response_statuses", [])[1:] and any(status == "BOUNDED_RESULT" for status in records["RJ2P10_0011"]["response_statuses"][1:]):
        failures.append("RJ2P10_0011: false second-response candidate")
    if MAX_RESPONSES != 4:
        failures.append(f"oracle support is not four responses: {MAX_RESPONSES}")
    snapshot = {"schema": "bjs400-rj2p10-weight3-oracle-regression-v1", "experiment_id": EXP.name, "created_at_local": now(), "marker": "ORACLE_REGRESSION_PASS" if not failures else "ORACLE_REGRESSION_FAIL", "status": "PASS" if not failures else "FAIL", "physical_solve_count": 0, "raw_files_modified": 0, "reference_cases": [f"RJ2P{rj2}_{mask}" for rj2, mask in CASES], "max_supported_responses": MAX_RESPONSES, "response_thresholds_turns": [0.5, 1.5, 2.5, 3.5], "hamming_weight_used_as_oracle_input": False, "scientific_authority": "raw waveform; regression is subordinate mechanical QA", "cases": records, "failures": failures, "scientific_interpretation_performed": False}
    (EXP / "qa").mkdir(parents=True, exist_ok=True)
    (EXP / "qa/oracle_regression.json").write_text(json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lines = ["# RJ2=10 weight-3 diagnostic oracle regression", "", snapshot["marker"], "", f"Status: `{snapshot['status']}`. No solver was invoked and no raw file was modified.", "", "The mechanical navigation oracle supports cumulative 0.5/1.5/2.5/3.5 turn landmarks from the common FINAL-origin baseline and direct voltage/terminal support. It is subordinate to raw waveform review and does not receive Hamming weight.", "", "| reference case | response candidate | terminal segmentation |", "|:---|---:|:---|"]
    for rj2, mask in CASES:
        row = records.get(f"RJ2P{rj2}_{mask}", {})
        lines.append(f"| RJ2P{rj2}_{mask} | {row.get('response_count_candidate')} | {row.get('terminal_status')} |")
    lines.extend(["", "No phase landmark, voltage cluster, terminal area or response candidate is an SFQ count.", ""])
    (EXP / "analysis/ORACLE_REGRESSION.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"status": snapshot["status"], "marker": snapshot["marker"], "physical_solve_count": 0, "raw_files_modified": 0, "response_counts": {key: value.get("response_count_candidate") for key, value in records.items()}, "failures": failures}, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
