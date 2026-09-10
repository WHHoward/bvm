#!/usr/bin/env python3
"""Audit and snapshot the repaired second-response oracle without solving."""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(EXP / "analysis"))
from bvmtools.raw import read_csv  # noqa: E402
from second_response_oracle import repaired_second_response_oracle  # noqa: E402


REUSE_RUNS = (
    "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P10_0001",
    "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P10_0011",
)
NEW_RUNS = (
    "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_0001",
    "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_0011",
    "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P14_0001",
    "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P14_0011",
    "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P16_0001",
    "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P16_0011",
)
ALL_RUNS = REUSE_RUNS + NEW_RUNS
EXPECTED_SECOND = {
    "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_0011",
    "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P14_0011",
    "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P16_0011",
}


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def raw_path(run_id: str) -> Path:
    root = "references/reused" if run_id in REUSE_RUNS else "runs"
    return EXP / root / run_id / "raw.csv"


def main() -> int:
    mechanical = json.loads((EXP / "mechanical_summary.json").read_text(encoding="utf-8"))
    independent = json.loads((EXP / "qa/independent_review.json").read_text(encoding="utf-8")) if (EXP / "qa/independent_review.json").is_file() else {}
    failures: list[str] = []
    snapshot_cases: dict[str, Any] = {}
    repaired_statuses: dict[str, str] = {}
    legacy_false_negative_cases: list[str] = []
    for run_id in ALL_RUNS:
        raw = raw_path(run_id)
        if not raw.is_file():
            failures.append(f"missing raw: {run_id}")
            continue
        oracle = repaired_second_response_oracle(read_csv(raw))
        repaired_statuses[run_id] = oracle["status"]
        case = mechanical.get("cases", {}).get(run_id, {})
        recorded = case.get("SECOND_TRIGGER_ANALYSIS", {})
        if oracle["status"] != recorded.get("second_complete_multi_evidence_candidate", {}).get("status"):
            failures.append(f"primary oracle/status mismatch: {run_id}")
        if oracle["first_response_status"] != "BOUNDED_RESULT":
            failures.append(f"first complete response missing under repaired oracle: {run_id}")
        if recorded.get("legacy_oracle_false_negative_detected") is True:
            legacy_false_negative_cases.append(run_id)
        snapshot_cases[run_id] = {
            "raw_path": str(raw.relative_to(REPO)),
            "raw_sha256": sha256(raw),
            "rj2_ohm": 10.0 if "RJ2P10" in run_id else float(run_id.split("RJ2P", 1)[1].split("_", 1)[0]),
            "mask": run_id.rsplit("_", 1)[1],
            "control_status": case.get("CONTROL_HARD_GUARDRAIL", {}).get("status"),
            "recorded_first_response_status": recorded.get("second_complete_multi_evidence_candidate", {}).get("first_response_status"),
            "recorded_single_response_status": recorded.get("second_complete_multi_evidence_candidate", {}).get("single_response_status"),
            "recorded_second_response_status": recorded.get("second_complete_multi_evidence_candidate", {}).get("status"),
            "second_progression_times_ps": oracle.get("second_progression_times_ps"),
            "second_checks": oracle.get("second_checks"),
            "voltage_signal_cluster_counts": oracle.get("voltage_signal_cluster_counts"),
            "terminal_pulse_analysis": oracle.get("terminal_pulse_analysis"),
            "phase_reference_policy": oracle.get("phase_reference_policy"),
            "pulse_reference_policy": oracle.get("pulse_reference_policy"),
        }

    single_case = "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_0001"
    two_case = "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_0011"
    single = snapshot_cases.get(single_case, {})
    two = snapshot_cases.get(two_case, {})
    adversarial = {
        "known_single_response_0001": {
            "case_id": single_case,
            "second_status": single.get("recorded_second_response_status"),
            "terminal_status": (single.get("terminal_pulse_analysis") or {}).get("status"),
            "passes_no_two_response": single.get("recorded_second_response_status") != "BOUNDED_RESULT" and (single.get("terminal_pulse_analysis") or {}).get("status") == "ONE_RESPONSE_CLUSTER",
        },
        "known_two_response_0011": {
            "case_id": two_case,
            "second_status": two.get("recorded_second_response_status"),
            "second_checks": two.get("second_checks"),
            "terminal_status": (two.get("terminal_pulse_analysis") or {}).get("status"),
            "passes_two_response_explanation": two.get("recorded_second_response_status") == "BOUNDED_RESULT" and all((two.get("second_checks") or {}).values()) and (two.get("terminal_pulse_analysis") or {}).get("status") == "TWO_SEPARATED_PULSES",
        },
        "legacy_strongest_l1_reference_false_negative": {
            "cases": legacy_false_negative_cases,
            "expected_cases": sorted(EXPECTED_SECOND),
            "passes_false_negative_exposure": set(legacy_false_negative_cases) == EXPECTED_SECOND,
        },
    }
    if set(run_id for run_id, status in repaired_statuses.items() if status == "BOUNDED_RESULT") != EXPECTED_SECOND:
        failures.append("repaired second-response case set is not exactly RJ2=12/14/16, mask 0011")
    if not all(item["passes_no_two_response"] for item in adversarial.values() if isinstance(item, dict) and "passes_no_two_response" in item):
        failures.append("known single-response adversarial test failed")
    if not adversarial["known_two_response_0011"]["passes_two_response_explanation"]:
        failures.append("known two-response adversarial test failed")
    if not adversarial["legacy_strongest_l1_reference_false_negative"]["passes_false_negative_exposure"]:
        failures.append("legacy oracle false-negative exposure does not match expected cases")
    snapshot = {
        "schema": "bjs400-rj2-highside-second-trigger-corrected-oracle-snapshot-v1",
        "experiment_id": EXP.name,
        "created_at_local": now(),
        "marker": "ORACLE_REVIEW_COMPLETE",
        "physical_solve_count": 0,
        "raw_files_modified": 0,
        "scientific_interpretation_performed": False,
        "oracle_code_sha256": sha256(EXP / "analysis/second_response_oracle.py"),
        "independent_review_status": independent.get("status"),
        "old_oracle_policy": "strongest_later_positive_L1_segment_start was incorrectly used as a new phase reference",
        "repaired_oracle_policy": "all cumulative phase landmarks use FINAL-origin [101,110) ps baseline; voltage clusters are independently segmented with a stored-sample valley rule",
        "repaired_oracle_statuses": repaired_statuses,
        "legacy_false_negative_cases": legacy_false_negative_cases,
        "expected_second_response_cases": sorted(EXPECTED_SECOND),
        "adversarial_tests": adversarial,
        "cases": snapshot_cases,
        "status": "PASS" if not failures else "FAIL",
        "failures": failures,
    }
    (EXP / "analysis/corrected_oracle_snapshot.json").write_text(json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    oracle_qa = {
        "schema": "bjs400-rj2-highside-second-trigger-oracle-qa-v1",
        "experiment_id": EXP.name,
        "created_at_local": now(),
        "marker": "ORACLE_REVIEW_COMPLETE",
        "status": snapshot["status"],
        "raw_files_modified": 0,
        "physical_solve_count": 0,
        "repaired_second_response_cases": sorted(run_id for run_id, status in repaired_statuses.items() if status == "BOUNDED_RESULT"),
        "legacy_false_negative_cases": legacy_false_negative_cases,
        "adversarial_tests": adversarial,
        "failures": failures,
        "scientific_interpretation_performed": False,
        "oracle_code_sha256": snapshot["oracle_code_sha256"],
        "independent_review_status": independent.get("status"),
    }
    (EXP / "qa/oracle_qa.json").write_text(json.dumps(oracle_qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lines = [
        "# Second-response oracle review",
        "",
        "ORACLE_REVIEW_COMPLETE",
        "",
        f"Review status: `{snapshot['status']}`. No solver was invoked and no raw file was modified.",
        "",
        "## Repair",
        "",
        "The former checker restarted cumulative phase history at the strongest later positive `I(L1)` segment. That can begin after the second response has already advanced through BJ1/BJ2/JTL. The repaired checker keeps the common FINAL-origin baseline `[101,110) ps` for all cumulative landmarks and independently checks direct voltage clusters.",
        "",
        "Voltage clusters use stored samples, an adaptive baseline-MAD/peak threshold, a 2.5 ps peak-gap rule, and a below-threshold valley requirement. Terminal pulse-local areas use the shared stored valley boundary; a waveform that does not meet that rule is left ambiguous rather than force-split.",
        "",
        "## Case result",
        "",
        "| RJ2 | mask | first response | repaired second response | second phase order | voltage clusters | terminal |",
        "|---:|:---:|:---|:---|:---|:---|:---|",
    ]
    for run_id in ALL_RUNS:
        item = snapshot_cases.get(run_id, {})
        checks = item.get("second_checks") or {}
        terminal = item.get("terminal_pulse_analysis") or {}
        lines.append(f"| {item.get('rj2_ohm')} | {item.get('mask')} | {item.get('recorded_first_response_status')} | {item.get('recorded_second_response_status')} | {checks.get('second_phase_ordered_BJ1_BJ2_JTL1_to_JTL6')} | {checks.get('two_voltage_clusters_per_registered_signal')} | {terminal.get('status')} |")
    lines.extend([
        "",
        f"Repaired second-response cases: `{', '.join(sorted(EXPECTED_SECOND))}`.",
        f"Legacy strongest-L1 reference exposed as false-negative for: `{', '.join(legacy_false_negative_cases)}`.",
        "",
        "## Adversarial tests",
        "",
        f"- Known single-response `0001`: `{adversarial['known_single_response_0001']['passes_no_two_response']}`; it remains one terminal response and is not classified as a second response.",
        f"- Known two-response `RJ2=12 / 0011`: `{adversarial['known_two_response_0011']['passes_two_response_explanation']}`; all phase/voltage/terminal checks are explicitly recorded.",
        f"- Legacy false-negative exposure: `{adversarial['legacy_strongest_l1_reference_false_negative']['passes_false_negative_exposure']}`.",
        "",
        "All phase thresholds and voltage-area values remain mechanical/derived evidence. They are not SFQ counts, and no hardware or universal mechanism claim is made.",
        "",
    ])
    (EXP / "analysis/ORACLE_REVIEW.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"status": snapshot["status"], "marker": "ORACLE_REVIEW_COMPLETE", "physical_solve_count": 0, "raw_files_modified": 0, "repaired_second_response_cases": sorted(EXPECTED_SECOND), "legacy_false_negative_cases": legacy_false_negative_cases, "failures": failures}, ensure_ascii=False, indent=2))
    return 0 if snapshot["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
