#!/usr/bin/env python3
"""Analyze the single-BVMSim-BVM to QB matched 2x2 Quick.

The shared bvmtools modules own CSV parsing, phase unwrapping, actual-grid
integration, exact-grid comparison, and KCL arithmetic.  This file adds only
the task-local voltage-activity/quiescent-gap candidate association requested
for this experiment; it deliberately does not modify the shared SFQ tooling.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

from bvmtools.compare import compare_series, exact_time_grid_identity  # noqa: E402
from bvmtools.kcl import kcl_window_metrics, linear_kcl_residual  # noqa: E402
from bvmtools.phase import TAU, continuous_unwrap, phase_window_metrics, window_indices  # noqa: E402
from bvmtools.provenance import file_snapshot, git_snapshot, sha256_file, solver_provenance  # noqa: E402
from bvmtools.raw import RawTrace, read_csv  # noqa: E402
from bvmtools.sfq import PHI0  # noqa: E402
from bvmtools.waveform import trapezoid_integral, waveform_window_metrics  # noqa: E402


BASE_HEAD = "61627bdaf1c76395106ddbcabfcae572a5920ebd"
SOLVER = REPO / "build/josim-cli"
METRIC_WINDOWS_PS: "OrderedDict[str, tuple[float, float]]" = OrderedDict(
    (
        ("PRE", (0.0, 50.0)),
        ("WRITE", (50.0, 62.0)),
        ("READ", (70.0, 82.0)),
        ("POST", (82.0, 200.0)),
        ("FULL", (0.0, 200.0)),
    )
)
CONDITIONS = OrderedDict(
    (
        ("S0-R", EXP / "runs/A001/S0-R/raw.csv"),
        ("S1-R", EXP / "runs/A001/S1-R/raw.csv"),
        ("S0-J", EXP / "runs/A001/S0-J/raw.csv"),
        ("S1-J", EXP / "runs/A001/S1-J/raw.csv"),
    )
)
MIN_QUIESCENT_GAP_S = 0.25e-12
MIN_CANDIDATE_DURATION_S = 0.05e-12
ACTIVE_FLOOR_V = 1.0e-6
ACTIVE_RELATIVE = 0.01
QUIET_FLOOR_V = 0.2e-6
QUIET_RELATIVE = 0.002
NEAR_UNIT_MIN_TURNS = 0.75
NEAR_UNIT_MAX_TURNS = 1.25
PHASE_AREA_RESIDUAL_MAX_TURNS = 0.20

QB_SIGNALS = OrderedDict(
    (
        ("BJs", ("P(BJS|XBQ1)", "V(BJS|XBQ1)", "I(BJS|XBQ1)")),
        ("BJ1", ("P(BJ1|XBQ1)", "V(BJ1|XBQ1)", "I(BJ1|XBQ1)")),
        ("BJ2", ("P(BJ2|XBQ1)", "V(BJ2|XBQ1)", "I(BJ2|XBQ1)")),
    )
)
BVM_SIGNALS = OrderedDict(
    (
        ("B_JM1", ("P(B_JM1|XBVM1)", "V(B_JM1|XBVM1)", "I(B_JM1|XBVM1)")),
        ("B_LD4_01", ("P(B_LD4_01)", "V(B_LD4_01)", "I(B_LD4_01)")),
        ("B_LD4_11", ("P(B_LD4_11)", "V(B_LD4_11)", "I(B_LD4_11)")),
        ("BVMout", ("P(BVMOUT)", "V(BVMOUT)", "I(BVMOUT)")),
    )
)
JTL_SIGNALS = OrderedDict(
    (
        (
            f"JTL{stage}",
            OrderedDict(
                (
                    ("B01", (f"P(B01|XJTL1_{stage})", f"V(B01|XJTL1_{stage})", None)),
                    ("B02", (f"P(B02|XJTL1_{stage})", f"V(B02|XJTL1_{stage})", None)),
                )
            ),
        )
        for stage in range(1, 7)
    )
)


def json_write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def time_ps(value_s: float) -> float:
    return float(value_s) * 1.0e12


def registered_window(name: str) -> tuple[float, float]:
    left, right = METRIC_WINDOWS_PS[name]
    return left * 1.0e-12, right * 1.0e-12


def signal(trace: RawTrace, label: str) -> tuple[float, ...]:
    """Select an exact unique label through the duplicate-safe reader."""

    return trace.column(label)  # type: ignore[return-value]


def has_signal(trace: RawTrace, label: str | None) -> bool:
    return bool(label) and label in trace.headers


def active_runs(mask: list[bool]) -> list[tuple[int, int]]:
    """Return contiguous true runs."""

    output: list[tuple[int, int]] = []
    start: int | None = None
    for index, active in enumerate(mask):
        if active and start is None:
            start = index
        elif not active and start is not None:
            output.append((start, index - 1))
            start = None
    if start is not None:
        output.append((start, len(mask) - 1))
    return output


def _quiet_duration_before(time_s: tuple[float, ...], abs_v: list[float], index: int, threshold: float) -> float:
    cursor = index - 1
    while cursor >= 0 and abs_v[cursor] <= threshold:
        cursor -= 1
    first = cursor + 1
    return time_s[index] - time_s[first] if index > first else 0.0


def _quiet_duration_after(time_s: tuple[float, ...], abs_v: list[float], index: int, threshold: float) -> float:
    cursor = index + 1
    while cursor < len(time_s) and abs_v[cursor] <= threshold:
        cursor += 1
    last = cursor - 1
    return time_s[last] - time_s[index] if last > index else 0.0


def voltage_gap_candidates(
    time_s: tuple[float, ...], phase_raw: tuple[float, ...], voltage_v: tuple[float, ...]
) -> dict[str, Any]:
    """Segment voltage activity by a preregistered quiescent-gap rule.

    A candidate begins/ends at the active-threshold crossing.  The phase and
    area are measured on the candidate's same-JJ trace, including one adjacent
    sample on either side when available.  A long low-voltage interval is the
    separator; direction changes are not used as the event boundary.
    """

    if not (len(time_s) == len(phase_raw) == len(voltage_v)):
        raise ValueError("candidate inputs must have equal lengths")
    if len(time_s) < 2:
        raise ValueError("candidate inputs need at least two samples")
    peak_abs_v = max(abs(float(value)) for value in voltage_v)
    active_threshold_v = max(ACTIVE_FLOOR_V, ACTIVE_RELATIVE * peak_abs_v)
    quiet_threshold_v = max(QUIET_FLOOR_V, QUIET_RELATIVE * peak_abs_v)
    abs_v = [abs(float(value)) for value in voltage_v]
    runs = active_runs([value >= active_threshold_v for value in abs_v])
    merged: list[tuple[int, int]] = []
    for start, end in runs:
        if not merged:
            merged.append((start, end))
            continue
        previous_start, previous_end = merged[-1]
        gap_start = previous_end + 1
        gap_end = start - 1
        gap_duration_s = time_s[start] - time_s[previous_end]
        gap_is_quiet = gap_start > gap_end or all(
            abs_v[index] <= quiet_threshold_v for index in range(gap_start, gap_end + 1)
        )
        if gap_is_quiet and gap_duration_s >= MIN_QUIESCENT_GAP_S:
            merged.append((start, end))
        else:
            merged[-1] = (previous_start, end)

    unwrapped = continuous_unwrap(phase_raw)
    candidates: list[dict[str, Any]] = []
    for ordinal, (core_start, core_end) in enumerate(merged, start=1):
        measure_start = max(0, core_start - 1)
        measure_end = min(len(time_s) - 1, core_end + 1)
        phase_delta_rad = unwrapped[measure_end] - unwrapped[measure_start]
        phase_turns = phase_delta_rad / TAU
        area_wb = trapezoid_integral(
            voltage_v[measure_start : measure_end + 1],
            time_s[measure_start : measure_end + 1],
        )
        area_turns = area_wb / PHI0
        residual_turns = phase_turns - area_turns
        area_consistent = bool(
            abs(phase_turns) >= 1.0
            and abs(area_turns) > 0.0
            and phase_turns * area_turns > 0.0
            and abs(residual_turns) <= PHASE_AREA_RESIDUAL_MAX_TURNS
        )
        pre_quiet_s = _quiet_duration_before(time_s, abs_v, core_start, quiet_threshold_v)
        post_quiet_s = _quiet_duration_after(time_s, abs_v, core_end, quiet_threshold_v)
        near_unit = bool(
            NEAR_UNIT_MIN_TURNS <= abs(phase_turns) <= NEAR_UNIT_MAX_TURNS
            and area_consistent
        )
        complete = area_consistent
        clean_separated = bool(
            near_unit
            and pre_quiet_s >= MIN_QUIESCENT_GAP_S
            and post_quiet_s >= MIN_QUIESCENT_GAP_S
        )
        candidates.append(
            {
                "ordinal": ordinal,
                "core_start_index": core_start,
                "core_end_index": core_end,
                "measure_start_index": measure_start,
                "measure_end_index": measure_end,
                "onset_ps": time_ps(time_s[core_start]),
                "end_ps": time_ps(time_s[core_end]),
                "measure_start_ps": time_ps(time_s[measure_start]),
                "measure_end_ps": time_ps(time_s[measure_end]),
                "duration_ps": time_ps(time_s[core_end] - time_s[core_start]),
                "direction": 1 if phase_turns > 0.0 else -1 if phase_turns < 0.0 else 0,
                "delta_phase_rad": phase_delta_rad,
                "phase_delta_turns": phase_turns,
                "voltage_area_wb": area_wb,
                "voltage_area_turns": area_turns,
                "signed_phase_area_residual_turns": residual_turns,
                "pre_quiet_ps": time_ps(pre_quiet_s),
                "post_quiet_ps": time_ps(post_quiet_s),
                "pre_retrap": pre_quiet_s >= MIN_QUIESCENT_GAP_S,
                "post_retrap": post_quiet_s >= MIN_QUIESCENT_GAP_S,
                "phase_area_consistent": area_consistent,
                "complete_segment": complete,
                "near_unit": near_unit,
                "clean_separated_event": clean_separated,
                "windows_touched": [
                    name
                    for name, bounds in METRIC_WINDOWS_PS.items()
                    if time_ps(time_s[core_start]) < bounds[1]
                    and time_ps(time_s[core_end]) >= bounds[0]
                ],
            }
        )

    full_delta_turns = (unwrapped[-1] - unwrapped[0]) / TAU
    complete_count = sum(bool(item["complete_segment"]) for item in candidates)
    clean_count = sum(bool(item["clean_separated_event"]) for item in candidates)
    largest = max((abs(float(item["phase_delta_turns"])) for item in candidates), default=0.0)
    window_counts: dict[str, dict[str, int]] = {}
    for name, (left, right) in METRIC_WINDOWS_PS.items():
        selected = [item for item in candidates if left <= float(item["onset_ps"]) < right]
        window_counts[name] = {
            "candidate_count": len(selected),
            "complete_segment_count": sum(bool(item["complete_segment"]) for item in selected),
            "clean_separated_event_count": sum(bool(item["clean_separated_event"]) for item in selected),
        }
    return {
        "status": "VALID",
        "method": "voltage_activity_then_quiescent_gap_then_same_jj_phase_area",
        "peak_abs_voltage_V": peak_abs_v,
        "active_threshold_V": active_threshold_v,
        "quiescent_threshold_V": quiet_threshold_v,
        "min_quiescent_gap_ps": time_ps(MIN_QUIESCENT_GAP_S),
        "candidate_count": len(candidates),
        "complete_segment_count": complete_count,
        "clean_separated_event_count": clean_count,
        "largest_segment_turns_abs": largest,
        "continuous_multiturn_running": bool(
            any(
                abs(float(item["phase_delta_turns"])) > 1.15
                and not bool(item["clean_separated_event"])
                for item in candidates
            )
        ),
        "continuous_active_segment_without_retrap": bool(
            any(
                abs(float(item["phase_delta_turns"])) >= 1.0
                and not bool(item["pre_retrap"] and item["post_retrap"])
                for item in candidates
            )
        ),
        "full_trace_endpoint_delta_turns": full_delta_turns,
        "full_trace_phase_range_turns": (max(unwrapped) - min(unwrapped)) / TAU,
        "window_counts_by_onset": window_counts,
        "candidates": candidates,
    }


def phase_windows(trace: RawTrace, phase_label: str) -> dict[str, Any]:
    phase = signal(trace, phase_label)
    output: dict[str, Any] = {}
    for name in ("PRE", "WRITE", "READ", "POST"):
        left, right = registered_window(name)
        indices = window_indices(trace.time, left, right)
        if len(indices) >= 2:
            output[name] = phase_window_metrics(trace.time, phase, (left, right))
    return output


def waveform_windows(trace: RawTrace, voltage_label: str | None, current_label: str | None) -> dict[str, Any]:
    output: dict[str, Any] = {"voltage": {}, "current": {}}
    for key, label, unit, target in (
        ("voltage", voltage_label, "V", output["voltage"]),
        ("current", current_label, "A", output["current"]),
    ):
        if not has_signal(trace, label):
            continue
        values = signal(trace, label)  # type: ignore[arg-type]
        for name in ("PRE", "WRITE", "READ", "POST"):
            left, right = registered_window(name)
            if len(window_indices(trace.time, left, right)) >= 2:
                target[name] = waveform_window_metrics(trace.time, values, (left, right), unit=unit)
    return output


def event_signal_result(trace: RawTrace, name: str, labels: tuple[str | None, str | None, str | None]) -> dict[str, Any]:
    phase_label, voltage_label, current_label = labels
    missing = [label for label in (phase_label, voltage_label) if not has_signal(trace, label)]
    if missing:
        return {"status": "MISSING_SIGNAL", "missing": missing}
    phase = signal(trace, phase_label)  # type: ignore[arg-type]
    voltage = signal(trace, voltage_label)  # type: ignore[arg-type]
    result = voltage_gap_candidates(trace.time, phase, voltage)
    result["signal_name"] = name
    result["phase_label"] = phase_label
    result["voltage_label"] = voltage_label
    result["current_label"] = current_label
    result["phase_windows"] = phase_windows(trace, phase_label)  # type: ignore[arg-type]
    result["waveform_windows"] = waveform_windows(trace, voltage_label, current_label)
    return result


def trace_qa(trace: RawTrace) -> dict[str, Any]:
    qa = dict(trace.qa())
    dt = list(trace.dt)
    expected = 0.025e-12
    qa.update(
        {
            "time_start_ps": time_ps(trace.time[0]),
            "time_end_ps": time_ps(trace.time[-1]),
            "dt_min_ps": time_ps(min(dt)),
            "dt_max_ps": time_ps(max(dt)),
            "expected_dt_ps": 0.025,
            "off_nominal_dt_count": sum(abs(value - expected) > 1.0e-24 for value in dt),
            "time_grid_actual_values_used": True,
        }
    )
    return qa


def qb_kcl(trace: RawTrace) -> dict[str, Any]:
    branch_labels = {
        "I_Lin": "I(LIN|XBQ1)",
        "I_BJs": "I(BJS|XBQ1)",
        "I_L1": "I(L1|XBQ1)",
        "I_L2": "I(L2|XBQ1)",
        "I_L3": "I(L3|XBQ1)",
        "I_BJ1": "I(BJ1|XBQ1)",
        "I_RJ1": "I(RJ1|XBQ1)",
        "I_BJ2": "I(BJ2|XBQ1)",
        "I_RJ2": "I(RJ2|XBQ1)",
        "I_bias": "I(I_QB_BIAS)",
    }
    missing = [label for label in branch_labels.values() if not has_signal(trace, label)]
    if missing:
        return {"status": "MISSING_SIGNAL", "missing": missing}
    branches = {name: signal(trace, label) for name, label in branch_labels.items()}
    equations = OrderedDict(
        (
            ("node_1_Lin_minus_BJs", ({"I_Lin": 1.0, "I_BJs": -1.0})),
            ("node_2_BJs_to_BJ1_RJ1_L1", ({"I_BJs": 1.0, "I_BJ1": -1.0, "I_RJ1": -1.0, "I_L1": -1.0})),
            ("bias_L1_plus_source_minus_L2", ({"I_L1": 1.0, "I_bias": 1.0, "I_L2": -1.0})),
            ("node_4_L2_to_BJ2_RJ2_L3", ({"I_L2": 1.0, "I_BJ2": -1.0, "I_RJ2": -1.0, "I_L3": -1.0})),
        )
    )
    output: dict[str, Any] = {
        "status": "VALID",
        "orientation": {
            "I_Lin": "IN -> QB node 1",
            "I_BJs": "QB node 1 -> QB node 2",
            "I_L1": "QB node 2 -> BIAS",
            "I_bias": "0 -> BIAS",
            "I_L2": "BIAS -> QB node 4",
            "I_BJ1": "QB node 2 -> 0",
            "I_RJ1": "QB node 2 -> 0",
            "I_BJ2": "QB node 4 -> 0",
            "I_RJ2": "QB node 4 -> 0",
            "I_L3": "QB node 4 -> OUT",
        },
        "equations": {},
    }
    for equation_name, coefficients in equations.items():
        selected_branches = {name: branches[name] for name in coefficients}
        residual = linear_kcl_residual(selected_branches, coefficients)
        output["equations"][equation_name] = {
            "coefficients": coefficients,
            "windows": {
                name: kcl_window_metrics(trace.time, residual, registered_window(name), unit="A")
                for name in ("PRE", "WRITE", "READ", "POST", "FULL")
            },
        }
    return output


def condition_result(condition: str, trace: RawTrace) -> dict[str, Any]:
    signals: dict[str, Any] = {}
    for name, labels in BVM_SIGNALS.items():
        signals[name] = event_signal_result(trace, name, labels)
    for name, labels in QB_SIGNALS.items():
        signals[name] = event_signal_result(trace, name, labels)
    if any(has_signal(trace, labels[0]) for labels in JTL_SIGNALS["JTL1"].values()):
        for stage, stage_signals in JTL_SIGNALS.items():
            for branch, labels in stage_signals.items():
                signals[f"{stage}.{branch}"] = event_signal_result(trace, f"{stage}.{branch}", labels)

    current_pairs = {
        "B_LD4_01_to_B_LD4_11": ("I(B_LD4_01)", "I(B_LD4_11)"),
        "B_LD4_11_to_BVMout": ("I(B_LD4_11)", "I(BVMOUT)"),
    }
    series_checks: dict[str, Any] = {}
    for name, (left_label, right_label) in current_pairs.items():
        if has_signal(trace, left_label) and has_signal(trace, right_label):
            left = signal(trace, left_label)
            right = signal(trace, right_label)
            comparison = compare_series(trace.time, left, trace.time, right)
            comparison.pop("pointwise_difference", None)
            comparison["difference_unit"] = "A"
            series_checks[name] = comparison

    return {
        "condition": condition,
        "raw_path": str(CONDITIONS[condition].relative_to(REPO)),
        "qa": trace_qa(trace),
        "signals": signals,
        "qb_chain_first_read_candidate": {
            "any_voltage_candidate": first_chain_candidate({"signals": signals}, clean_only=False, window="READ"),
            "strict_clean_candidate": first_chain_candidate({"signals": signals}, clean_only=True, window="READ"),
        },
        "qb_chain_first_full_trace_candidate": {
            "any_voltage_candidate": first_chain_candidate({"signals": signals}, clean_only=False, window="FULL"),
            "strict_clean_candidate": first_chain_candidate({"signals": signals}, clean_only=True, window="FULL"),
        },
        "qb_kcl": qb_kcl(trace),
        "sensing_line_series_current_checks": series_checks,
    }


def read_candidate_events(result: dict[str, Any], signal_name: str, window: str = "READ", clean_only: bool = False) -> list[dict[str, Any]]:
    record = result["signals"].get(signal_name, {})
    candidates = record.get("candidates", []) if record.get("status") == "VALID" else []
    lower, upper = METRIC_WINDOWS_PS[window]
    selected = [item for item in candidates if lower <= float(item["onset_ps"]) < upper]
    if clean_only:
        selected = [item for item in selected if item.get("clean_separated_event") is True]
    return selected


def first_chain_candidate(result: dict[str, Any], clean_only: bool, window: str = "FULL") -> dict[str, Any] | None:
    candidates_with_names: list[tuple[str, dict[str, Any]]] = []
    for signal_name in ("BJs", "BJ1", "BJ2"):
        candidates_with_names.extend(
            (signal_name, item)
            for item in read_candidate_events(result, signal_name, window=window, clean_only=clean_only)
        )
    if not candidates_with_names:
        return None
    signal_name, item = min(candidates_with_names, key=lambda pair: float(pair[1]["onset_ps"]))
    return {
        "junction": signal_name,
        "onset_ps": item["onset_ps"],
        "phase_delta_turns": item["phase_delta_turns"],
        "clean_separated_event": item["clean_separated_event"],
        "window_association": window,
    }


def match_onsets(upstream: list[dict[str, Any]], downstream: list[dict[str, Any]]) -> list[dict[str, Any]]:
    remaining = list(downstream)
    matches: list[dict[str, Any]] = []
    for item in upstream:
        if not remaining:
            break
        later = [candidate for candidate in remaining if float(candidate["onset_ps"]) >= float(item["onset_ps"])]
        selected = later[0] if later else remaining[0]
        remaining.remove(selected)
        matches.append(
            {
                "upstream_onset_ps": item["onset_ps"],
                "downstream_onset_ps": selected["onset_ps"],
                "latency_ps": float(selected["onset_ps"]) - float(item["onset_ps"]),
                "upstream_direction": item["direction"],
                "downstream_direction": selected["direction"],
            }
        )
    return matches


def transport_result(condition_result_value: dict[str, Any]) -> dict[str, Any]:
    stages: list[dict[str, Any]] = []
    source = read_candidate_events(condition_result_value, "BJ2", clean_only=True)
    for stage in range(1, 7):
        b01_name = f"JTL{stage}.B01"
        b02_name = f"JTL{stage}.B02"
        b01 = condition_result_value["signals"].get(b01_name, {})
        b02 = condition_result_value["signals"].get(b02_name, {})
        b01_clean = read_candidate_events(condition_result_value, b01_name, clean_only=True)
        b02_clean = read_candidate_events(condition_result_value, b02_name, clean_only=True)
        b01_all = read_candidate_events(condition_result_value, b01_name, clean_only=False)
        stages.append(
            {
                "stage": f"JTL{stage}",
                "B01": {
                    "status": b01.get("status", "MISSING_SIGNAL"),
                    "candidate_count": len(b01_all),
                    "complete_segment_count": b01.get("complete_segment_count", 0),
                    "clean_event_count": len(b01_clean),
                    "polarity": [item["direction"] for item in b01_clean],
                    "onset_ps": [item["onset_ps"] for item in b01_clean],
                    "phase_delta_turns": [item["phase_delta_turns"] for item in b01_clean],
                    "matches_to_BJ2": match_onsets(source, b01_clean),
                },
                "B02": {
                    "status": b02.get("status", "MISSING_SIGNAL"),
                    "candidate_count": len(read_candidate_events(condition_result_value, b02_name, clean_only=False)),
                    "complete_segment_count": b02.get("complete_segment_count", 0),
                    "clean_event_count": len(b02_clean),
                    "polarity": [item["direction"] for item in b02_clean],
                    "onset_ps": [item["onset_ps"] for item in b02_clean],
                    "phase_delta_turns": [item["phase_delta_turns"] for item in b02_clean],
                    "matches_to_BJ2": match_onsets(source, b02_clean),
                },
            }
        )
    return {
        "source": "BJ2",
        "source_clean_event_count": len(source),
        "source_clean_onset_ps": [item["onset_ps"] for item in source],
        "stages": stages,
    }


def load_backaction(results: dict[str, dict[str, Any]], traces: dict[str, RawTrace]) -> dict[str, Any]:
    pairs = (("S0-R", "S0-J"), ("S1-R", "S1-J"))
    output: dict[str, Any] = {}
    for direct_name, jtl_name in pairs:
        direct_trace = traces[direct_name]
        jtl_trace = traces[jtl_name]
        direct = results[direct_name]
        jtl = results[jtl_name]
        left_phase = continuous_unwrap(signal(direct_trace, "P(BJ2|XBQ1)"))
        right_phase = continuous_unwrap(signal(jtl_trace, "P(BJ2|XBQ1)"))
        left_voltage = signal(direct_trace, "V(BJ2|XBQ1)")
        right_voltage = signal(jtl_trace, "V(BJ2|XBQ1)")
        left_indices = window_indices(direct_trace.time, *registered_window("READ"))
        right_indices = window_indices(jtl_trace.time, *registered_window("READ"))
        grid_exact = exact_time_grid_identity(direct_trace.time, jtl_trace.time)
        if not grid_exact or len(left_indices) != len(right_indices):
            output[f"{direct_name}_vs_{jtl_name}"] = {"status": "TIME_GRID_MISMATCH"}
            continue
        left_phase_turns = [
            (left_phase[index] - left_phase[left_indices[0]]) / TAU for index in left_indices
        ]
        right_phase_turns = [
            (right_phase[index] - right_phase[right_indices[0]]) / TAU for index in right_indices
        ]
        comparison_phase = compare_series(
            [direct_trace.time[index] for index in left_indices],
            left_phase_turns,
            [jtl_trace.time[index] for index in right_indices],
            right_phase_turns,
            include_correlation=True,
        )
        comparison_voltage = compare_series(
            [direct_trace.time[index] for index in left_indices],
            [left_voltage[index] for index in left_indices],
            [jtl_trace.time[index] for index in right_indices],
            [right_voltage[index] for index in right_indices],
            include_correlation=True,
        )
        comparison_phase.pop("pointwise_difference", None)
        comparison_voltage.pop("pointwise_difference", None)
        output[f"{direct_name}_vs_{jtl_name}"] = {
            "status": "VALID",
            "window": "READ",
            "time_grid_exact": grid_exact,
            "BJ2_phase_baseline_aligned_turns": comparison_phase,
            "BJ2_voltage_V": comparison_voltage,
            "direct_read_clean_event_count": len(read_candidate_events(direct, "BJ2", clean_only=True)),
            "jtl_read_clean_event_count": len(read_candidate_events(jtl, "BJ2", clean_only=True)),
        }
    return output


def classify(results: dict[str, dict[str, Any]], transports: dict[str, Any]) -> dict[str, Any]:
    s0_direct = results["S0-R"]
    s1_direct = results["S1-R"]
    s0_jtl = results["S0-J"]
    s1_jtl = results["S1-J"]
    s0_read_counts = [
        len(read_candidate_events(item, "BJ2", clean_only=True)) for item in (s0_direct, s0_jtl)
    ]
    s1_bj2_clean = len(read_candidate_events(s1_direct, "BJ2", clean_only=True))
    s1_jtl_bj2_clean = len(read_candidate_events(s1_jtl, "BJ2", clean_only=True))
    s1_jtl_counts = [
        len(read_candidate_events(s1_jtl, f"JTL{stage}.B01", clean_only=True)) for stage in range(1, 7)
    ]
    extra_complete = []
    for condition, record in results.items():
        for signal_name in ("BJs", "BJ1", "BJ2"):
            summary = record["signals"].get(signal_name, {})
            read_count = summary.get("window_counts_by_onset", {}).get("READ", {}).get("complete_segment_count", 0)
            outside = sum(
                summary.get("window_counts_by_onset", {}).get(name, {}).get("complete_segment_count", 0)
                for name in ("PRE", "WRITE", "POST")
            )
            if outside:
                extra_complete.append({"condition": condition, "signal": signal_name, "outside_read_complete_segments": outside, "read_complete_segments": read_count})

    strong = (
        max(s0_read_counts, default=0) == 0
        and s1_bj2_clean == 4
        and s1_jtl_bj2_clean == 4
        and s1_jtl_counts == [4, 4, 4, 4, 4, 4]
        and not extra_complete
    )
    if strong:
        primary = "FOUR_SEPARATED_SFQ_TRANSPORT_SUPPORTED"
        quick = "QUICK_PROMISING"
    elif s1_jtl_bj2_clean > 0 and any(count < s1_jtl_bj2_clean for count in s1_jtl_counts):
        primary = "LOCAL_MULTI_SFQ_WITH_TRANSPORT_LOSS"
        quick = "QUICK_AMBIGUOUS"
    elif s1_bj2_clean > 0 and s1_jtl_counts and all(count == s1_bj2_clean for count in s1_jtl_counts):
        primary = "OTHER_SEPARATED_MULTI_SFQ_TRANSPORT_SUPPORTED"
        quick = "QUICK_AMBIGUOUS"
    elif any(
        record["signals"].get(signal_name, {}).get("continuous_multiturn_running")
        for record in results.values()
        for signal_name in ("BJs", "BJ1", "BJ2")
    ):
        primary = "CONTINUOUS_MULTI_TURN_RUNNING_STATE"
        quick = "QUICK_OPPOSITE_OR_AMBIGUOUS"
    elif any(
        record["signals"].get(signal_name, {}).get("candidate_count", 0) > 0
        for record in results.values()
        for signal_name in ("BJs", "BJ1", "BJ2")
    ):
        primary = "MULTI_PHASE_ACTIVITY_ONLY"
        quick = "QUICK_AMBIGUOUS"
    else:
        primary = "NO_CLEAR_STRICT_CLASSIFICATION"
        quick = "QUICK_AMBIGUOUS"
    return {
        "primary_stage_classification": primary,
        "quick_label": quick,
        "basis": {
            "S0-R_and_S0-J_read_BJ2_clean_counts": s0_read_counts,
            "S1-R_read_BJ2_clean_count": s1_bj2_clean,
            "S1-J_read_BJ2_clean_count": s1_jtl_bj2_clean,
            "S1-J_JTL1_to_JTL6_B01_clean_counts": s1_jtl_counts,
            "complete_segments_outside_read": extra_complete,
        },
        "not_proven": [
            "canonical BVM compatibility",
            "four-BVM or single-BVM generalization beyond this fixture",
            "one BVM contribution implies one SFQ",
            "timestep convergence or process margin",
            "paper mechanism identity or unique QB operating mechanism",
        ],
    }


def provenance(traces: dict[str, RawTrace], timestamp: str) -> dict[str, Any]:
    source_paths = [
        REPO / "BVMSim/bvm_cell.cir",
        REPO / "circuits/qb/bq_cell_bvmsim_v1.cir",
        REPO / "circuits/models/jjmit.cir",
        REPO / "BVMSim/library_josim/jtl2.cir",
        REPO / "scripts/josim-plot2.py",
        EXP / "experiment.yaml",
        EXP / "run.sh",
        EXP / "analysis/analyze.py",
        EXP / "analysis/plot.py",
        EXP / "analysis/test_analyze.py",
        EXP / "analysis/independent_recheck.py",
    ]
    run_files: list[dict[str, Any]] = []
    for condition, raw_trace in traces.items():
        run_dir = EXP / "runs/A001" / condition
        for path in (run_dir / "deck.cir", run_dir / "raw.csv", run_dir / "run.log", run_dir / "command.txt"):
            if path.is_file():
                run_files.append(file_snapshot(path, relative_to=REPO))
    return {
        "generated_at": timestamp,
        "base_head_requested": BASE_HEAD,
        "head_at_analysis": subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, check=True, capture_output=True, text=True).stdout.strip(),
        "git": git_snapshot(REPO),
        "source_files": [file_snapshot(path, relative_to=REPO) for path in source_paths if path.is_file()],
        "solver": solver_provenance(SOLVER, cwd=REPO),
        "raw_files": run_files,
        "raw_sha256_by_condition": {condition: sha256_file(trace.path) for condition, trace in traces.items()},
        "raw_time_grid_by_condition": {
            condition: {
                "sample_count": trace.sample_count,
                "time_start_s": trace.time[0],
                "time_end_s": trace.time[-1],
                "dt_min_s": min(trace.dt),
                "dt_max_s": max(trace.dt),
            }
            for condition, trace in traces.items()
        },
        "analysis_algorithm": {
            "script": str((EXP / "analysis/analyze.py").relative_to(REPO)),
            "sha256": sha256_file(EXP / "analysis/analyze.py"),
            "shared_modules": [
                "bvmtools.raw.read_csv",
                "bvmtools.phase.continuous_unwrap",
                "bvmtools.waveform.trapezoid_integral",
                "bvmtools.compare.compare_series",
                "bvmtools.kcl.linear_kcl_residual",
                "bvmtools.kcl.kcl_window_metrics",
            ],
            "task_local_detector": "voltage activity -> quiescent gap -> same-JJ phase/area; no bvmtools rewrite",
            "thresholds": {
                "active_floor_V": ACTIVE_FLOOR_V,
                "active_relative_to_peak": ACTIVE_RELATIVE,
                "quiet_floor_V": QUIET_FLOOR_V,
                "quiet_relative_to_peak": QUIET_RELATIVE,
                "min_quiescent_gap_ps": time_ps(MIN_QUIESCENT_GAP_S),
                "min_candidate_duration_ps": time_ps(MIN_CANDIDATE_DURATION_S),
                "near_unit_turns": [NEAR_UNIT_MIN_TURNS, NEAR_UNIT_MAX_TURNS],
                "phase_area_residual_max_turns": PHASE_AREA_RESIDUAL_MAX_TURNS,
            },
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--timestamp", default=None)
    args = parser.parse_args()
    timestamp = args.timestamp or datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    traces = {condition: read_csv(path) for condition, path in CONDITIONS.items()}
    grid_identity = all(
        exact_time_grid_identity(traces["S0-R"].time, traces[condition].time)
        for condition in CONDITIONS
    )
    results = {condition: condition_result(condition, trace) for condition, trace in traces.items()}
    transport = {condition: transport_result(results[condition]) for condition in ("S0-J", "S1-J")}
    backaction = load_backaction(results, traces)
    classification = classify(results, transport)
    metrics = {
        "analysis_version": "BVM_QB_SINGLE_BVMSIM_MATCHED_2X2_QUICK_V1_ANALYSIS_V1",
        "status": "VALID" if all(record["qa"]["status"] == "VALID" for record in results.values()) else "ANALYSIS_INVALID",
        "time_grid": {
            "all_four_exactly_identical": grid_identity,
            "interpolation_used": False,
            "actual_grid_used_for_integration": True,
        },
        "thresholds": {
            "active_floor_V": ACTIVE_FLOOR_V,
            "active_relative_to_peak": ACTIVE_RELATIVE,
            "quiet_floor_V": QUIET_FLOOR_V,
            "quiet_relative_to_peak": QUIET_RELATIVE,
            "min_quiescent_gap_ps": time_ps(MIN_QUIESCENT_GAP_S),
            "min_candidate_duration_ps": time_ps(MIN_CANDIDATE_DURATION_S),
            "near_unit_turns": [NEAR_UNIT_MIN_TURNS, NEAR_UNIT_MAX_TURNS],
            "phase_area_residual_max_turns": PHASE_AREA_RESIDUAL_MAX_TURNS,
        },
        "conditions": results,
        "transport": transport,
        "load_backaction": backaction,
        "classification": classification,
        "interpretation_boundary": {
            "phase_turns_are_not_automatically_SFQ_count": True,
            "event_count_requires_same_JJ_phase_area_and_retrap": True,
            "plots_are_descriptive_only": True,
        },
    }
    json_write(EXP / "analysis/metrics.json", metrics)
    json_write(EXP / "analysis/provenance.json", provenance(traces, timestamp))
    return 0 if metrics["status"] == "VALID" else 2


if __name__ == "__main__":
    raise SystemExit(main())
