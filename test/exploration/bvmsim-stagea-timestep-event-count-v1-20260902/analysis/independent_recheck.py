#!/usr/bin/env python3
"""Independent arithmetic recheck for the timestep Quick.

This is deliberately not a second event detector.  It reuses the repository
raw reader, then independently recomputes selected net phase, same-segment
phase delta, and voltage-area values from the immutable raw samples.  Segment
boundaries come from the production metric record and are checked, not
rediscovered here.
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
METRICS = EXP / "analysis/metrics.json"
OUTPUT = EXP / "analysis/independent_recheck.json"
PHI0 = 2.067833848e-15
TAU = 2.0 * math.pi

sys.path.insert(0, str(REPO / "scripts"))
from bvmtools.raw import RawTrace, read_csv  # noqa: E402


RUNS = {
    "T100": EXP / "runs/T100/attempt-02/raw.csv",
    "T050": EXP / "runs/T050/attempt-01/raw.csv",
    "T025": EXP / "runs/T025/attempt-01/raw.csv",
    "T0125": EXP / "runs/T0125/attempt-01/raw.csv",
    "T100_FULL": EXP / "runs/T100_FULL/attempt-01/raw.csv",
}
WINDOW = (110.0e-12, 170.0e-12)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def unwrap(values: tuple[float, ...]) -> tuple[float, ...]:
    """Independent continuous unwrap with no call to bvmtools.phase."""

    if not values:
        raise ValueError("cannot unwrap an empty sequence")
    output = [float(values[0])]
    previous_raw = float(values[0])
    for value in values[1:]:
        current_raw = float(value)
        delta = current_raw - previous_raw
        while delta > math.pi:
            delta -= TAU
        while delta < -math.pi:
            delta += TAU
        output.append(output[-1] + delta)
        previous_raw = current_raw
    return tuple(output)


def exact_index(trace: RawTrace, time_s: float) -> int:
    matches = [index for index, value in enumerate(trace.time) if value == time_s]
    if len(matches) != 1:
        raise AssertionError(f"expected one exact timestamp {time_s!r}, found {len(matches)}")
    return matches[0]


def direct_segment(
    trace: RawTrace,
    phase_name: str,
    voltage_name: str,
    start_s: float,
    end_s: float,
) -> dict[str, float]:
    phase = unwrap(trace.column(phase_name))  # type: ignore[arg-type]
    voltage = trace.column(voltage_name)
    start = exact_index(trace, start_s)
    end = exact_index(trace, end_s)
    if end <= start:
        raise AssertionError("segment endpoint order is invalid")
    area_wb = sum(
        0.5 * (float(voltage[index - 1]) + float(voltage[index]))
        * (trace.time[index] - trace.time[index - 1])
        for index in range(start + 1, end + 1)
    )
    phase_turns = (phase[end] - phase[start]) / TAU
    area_turns = area_wb / PHI0
    return {
        "start_time_ps": trace.time[start] * 1.0e12,
        "end_time_ps": trace.time[end] * 1.0e12,
        "phase_turns_direct": phase_turns,
        "area_turns_direct": area_turns,
        "phase_area_residual_turns_direct": phase_turns - area_turns,
        "sample_count": float(end - start + 1),
    }


def direct_window_net(trace: RawTrace, phase_name: str) -> float:
    phase = unwrap(trace.column(phase_name))  # type: ignore[arg-type]
    indices = [index for index, time_s in enumerate(trace.time) if WINDOW[0] <= time_s < WINDOW[1]]
    if len(indices) < 2:
        raise AssertionError("READ1 has fewer than two samples")
    return (phase[indices[-1]] - phase[indices[0]]) / TAU


def exact_compare(
    first: RawTrace,
    second: RawTrace,
    name: str,
    *,
    first_occurrence: int | None = None,
    second_occurrence: int | None = None,
) -> dict[str, Any]:
    first_values = first.column(name, occurrence=first_occurrence)  # type: ignore[arg-type]
    second_values = second.column(name, occurrence=second_occurrence)  # type: ignore[arg-type]
    second_index = {time: index for index, time in enumerate(second.time)}
    pairs = [
        (index, second_index[time])
        for index, time in enumerate(first.time)
        if time in second_index
    ]
    if not pairs:
        return {"signal": name, "status": "NO_EXACT_OVERLAP"}
    differences = [abs(float(first_values[i]) - float(second_values[j])) for i, j in pairs]
    return {
        "signal": name,
        "first_occurrence": first_occurrence,
        "second_occurrence": second_occurrence,
        "sample_count": len(pairs),
        "max_abs_difference": max(differences, default=0.0),
        "first_time_ps": first.time[pairs[0][0]] * 1.0e12,
        "last_time_ps": first.time[pairs[-1][0]] * 1.0e12,
    }


def segment_record(
    metrics: dict[str, Any], run_id: str, signal_name: str, predicate
) -> dict[str, Any] | None:
    segments = metrics["runs"][run_id]["signals"][signal_name]["windows"]["READ1_RESPONSE"]["event_list"]["segments"]
    matches = [item for item in segments if predicate(item)]
    return matches[0] if matches else None


def compare_recorded_direct(recorded: dict[str, Any], direct: dict[str, float]) -> dict[str, Any]:
    return {
        "recorded_start_time_ps": recorded["start_time_ps"],
        "recorded_end_time_ps": recorded["end_time_ps"],
        "direct_start_time_ps": direct["start_time_ps"],
        "direct_end_time_ps": direct["end_time_ps"],
        "recorded_phase_turns": recorded["phase_reported_turns"],
        "direct_phase_turns": direct["phase_turns_direct"],
        "phase_turn_error": direct["phase_turns_direct"] - recorded["phase_reported_turns"],
        "recorded_area_turns": recorded["area_reported_turns"],
        "direct_area_turns": direct["area_turns_direct"],
        "area_turn_error": direct["area_turns_direct"] - recorded["area_reported_turns"],
        "recorded_residual_turns": recorded["phase_area_residual_turns"],
        "direct_residual_turns": direct["phase_area_residual_turns_direct"],
        "residual_turn_error": direct["phase_area_residual_turns_direct"] - recorded["phase_area_residual_turns"],
    }


def main() -> int:
    metrics = json.loads(METRICS.read_text(encoding="utf-8"))
    traces = {run_id: read_csv(path) for run_id, path in RUNS.items()}

    net_phase: dict[str, float] = {}
    selected_segments: dict[str, Any] = {}
    for run_id, trace in traces.items():
        net_phase[run_id] = direct_window_net(trace, "P(BJ2|XBQ1)")
        bj2_record = segment_record(
            metrics,
            run_id,
            "BJ2",
            lambda item: bool(item["onset_in_event_window"])
            and abs(float(item["phase_reported_turns"])) >= 3.0,
        )
        if bj2_record is None:
            raise AssertionError(f"no BJ2 main segment matched {run_id}")
        bj2_direct = direct_segment(
            trace,
            "P(BJ2|XBQ1)",
            "V(BJ2|XBQ1)",
            float(bj2_record["start_time_s"]),
            float(bj2_record["end_time_s"]),
        )
        selected_segments[f"{run_id}:BJ2_main"] = compare_recorded_direct(bj2_record, bj2_direct)

        fifth_record = segment_record(
            metrics,
            run_id,
            "JTL6.B02",
            lambda item: bool(item["onset_in_event_window"])
            and int(item.get("event_window_event_index") or 0) == 5,
        )
        if fifth_record is None:
            selected_segments[f"{run_id}:JTL6_B02_event5"] = {
                "status": "NOT_PRESENT",
                "meaning": "this run has no fifth complete event in JTL6.B02",
            }
        else:
            fifth_direct = direct_segment(
                trace,
                "P(B02|XJTL1_6)",
                "V(B02|XJTL1_6)",
                float(fifth_record["start_time_s"]),
                float(fifth_record["end_time_s"]),
            )
            selected_segments[f"{run_id}:JTL6_B02_event5"] = compare_recorded_direct(fifth_record, fifth_direct)

    historical = read_csv(REPO / "BVMSim/data_tran.csv")
    t100 = traces["T100"]
    t025 = traces["T025"]
    stage_m0 = read_csv(REPO / "test/exploration/bvmsim-qb-strict-qualification-v1-20260902/raw/m0/run-01.csv")
    stage_s1 = read_csv(REPO / "test/exploration/bvmsim-qb-strict-qualification-v1-20260902/raw/s1/run-01.csv")
    migration_checks = [
        exact_compare(historical, t100, "I(BVMOUT)"),
        exact_compare(historical, t100, "V(QBIN)"),
        exact_compare(historical, t100, "V(QBOUT)"),
        exact_compare(historical, t100, "P(BJ1|XBQ1)"),
        exact_compare(historical, t100, "P(B01|XJTL1_1)"),
        exact_compare(historical, t100, "V(O2)", first_occurrence=0),
        exact_compare(historical, t100, "V(O2)", first_occurrence=1),
    ]
    control_checks = [
        exact_compare(stage_m0, t100, "P(BJ2|XBQ1)"),
        exact_compare(stage_m0, t100, "P(B01|XJTL1_1)"),
        exact_compare(stage_s1, t025, "P(BJ2|XBQ1)"),
        exact_compare(stage_s1, t025, "P(B01|XJTL1_1)"),
    ]

    all_errors = []
    for record in selected_segments.values():
        if record.get("status") == "NOT_PRESENT":
            continue
        all_errors.extend(
            abs(float(record[key]))
            for key in ("phase_turn_error", "area_turn_error", "residual_turn_error")
        )
    all_errors.extend(float(item["max_abs_difference"]) for item in migration_checks + control_checks)
    result = {
        "status": "PASS_WITHIN_SERIALIZED_NUMERICAL_PRECISION" if max(all_errors, default=0.0) <= 1.0e-9 else "REVIEW_REQUIRED",
        "method": "independent unwrap + direct trapezoid area on exact raw samples; no interpolation and no event rediscovery",
        "phi0_wb": PHI0,
        "metrics_sha256": sha256(METRICS),
        "raw_sha256": {run_id: sha256(path) for run_id, path in RUNS.items()},
        "bj2_read1_net_turns_direct": net_phase,
        "selected_segment_rechecks": selected_segments,
        "reference_exact_grid_checks": {
            "historical_vs_new_T100": migration_checks,
            "stage_a_M0_vs_new_T100_and_S1_vs_new_T025": control_checks,
        },
        "interpretation_boundary": "arithmetic agreement validates recorded values only; it does not validate SFQ identity, transport origin, timestep convergence, or branch causality",
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "max_abs_error": max(all_errors, default=0.0), "output": str(OUTPUT)}))
    return 0 if result["status"] == "PASS_WITHIN_SERIALIZED_NUMERICAL_PRECISION" else 1


if __name__ == "__main__":
    raise SystemExit(main())
