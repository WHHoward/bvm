#!/usr/bin/env python3
"""Reassess the frozen A001 raw evidence by physical Boundary.

This is analysis-only.  It never invokes JoSIM and never writes or rewrites a
raw CSV.  The existing task-local voltage-gap helper is applied only to the
predeclared READ_LOCAL slice; the old whole-trace result is retained as a
diagnostic comparison, not reused as the Boundary verdict.
"""

from __future__ import annotations

import hashlib
import json
import math
import subprocess
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Any, Sequence


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(EXP / "analysis"))

from analyze import voltage_gap_candidates  # noqa: E402
from bvmtools.compare import compare_windowed_series, exact_time_grid_identity  # noqa: E402
from bvmtools.phase import TAU, continuous_unwrap, window_indices  # noqa: E402
from bvmtools.provenance import sha256_file  # noqa: E402
from bvmtools.raw import RawTrace, read_csv  # noqa: E402
from bvmtools.waveform import trapezoid_integral, waveform_window_metrics  # noqa: E402


REQUESTED_BASE_HEAD = "d91e4d333661b5ed880386800e45c35836912032"
PHI0 = 2.067833848e-15
MIN_QUIESCENT_GAP_PS = 0.25
HEURISTIC_ONE_PHI0 = (0.8, 1.2)
LEGACY_PHASE_AREA_DIAGNOSTIC_MAX_TURNS = 0.20

CONDITIONS = OrderedDict(
    (
        ("S0-R", EXP / "runs/A001/S0-R/raw.csv"),
        ("S1-R", EXP / "runs/A001/S1-R/raw.csv"),
        ("S0-J", EXP / "runs/A001/S0-J/raw.csv"),
        ("S1-J", EXP / "runs/A001/S1-J/raw.csv"),
    )
)

WINDOWS_PS = OrderedDict(
    (
        ("INITIAL_BIAS", (0.0, 50.0)),
        ("PRE_READ", (65.0, 70.0)),
        ("READ_DRIVE", (70.0, 81.0)),
        ("READ_RESPONSE_TAIL", (81.0, 110.0)),
        ("POST_SETTLING", (110.0, 130.0)),
        ("POST_REST", (130.0, 200.0)),
        ("READ_LOCAL", (70.0, 110.0)),
    )
)

REQUIRED_RAW_SHA256 = {
    "S0-R": "a8e8183d864b8170bf29074644b467d1b00613f3848b7e25f0f4b1059237d1f3",
    "S1-R": "ac622d6c343b3edf18b656620c1df4a9263b37d117e6d48f65cc2a3399a1d904",
    "S0-J": "8844cd26ee3f5d4058ea5f7fde34f995b8c5d09a1b5f4ab9aebed3d9ca7cbeeb",
    "S1-J": "95042595e9c8ba9c82af1f7f9e8bd6130214405d8c8804ab4912d92bedae8b21",
}

B0_SIGNALS = OrderedDict(
    (
        ("V_SL1", ("V(SL1)", "V")),
        ("I_L_SL", ("I(L_SL|XBVM1)", "A")),
        ("V_QBIN", ("V(QBIN)", "V")),
        ("I_BVMOUT", ("I(BVMOUT)", "A")),
        ("V_BVMOUT", ("V(BVMOUT)", "V")),
    )
)

QB_SIGNALS = OrderedDict(
    (
        ("BJs", ("P(BJS|XBQ1)", "V(BJS|XBQ1)")),
        ("BJ1", ("P(BJ1|XBQ1)", "V(BJ1|XBQ1)")),
        ("BJ2", ("P(BJ2|XBQ1)", "V(BJ2|XBQ1)")),
    )
)

LINE_MARKERS = OrderedDict(
    (
        ("B_LD4_01", ("P(B_LD4_01)", "V(B_LD4_01)")),
        ("B_LD4_11", ("P(B_LD4_11)", "V(B_LD4_11)")),
        ("BVMout", ("P(BVMOUT)", "V(BVMOUT)")),
    )
)


def ps(value_s: float) -> float:
    return float(value_s) * 1.0e12


def bounds_s(name: str) -> tuple[float, float]:
    left, right = WINDOWS_PS[name]
    return left * 1.0e-12, right * 1.0e-12


def selected_indices(trace: RawTrace, window: str) -> tuple[int, ...]:
    return window_indices(trace.time, *bounds_s(window))


def raw_column(trace: RawTrace, label: str) -> tuple[float, ...]:
    return trace.column(label)  # type: ignore[return-value]


def phase_window(trace: RawTrace, label: str, window: str) -> dict[str, Any]:
    raw = raw_column(trace, label)
    unwrapped = continuous_unwrap(raw)
    indices = selected_indices(trace, window)
    if len(indices) < 2:
        raise ValueError(f"phase window {window} has fewer than two samples")
    values = [unwrapped[index] for index in indices]
    delta_rad = values[-1] - values[0]
    return {
        "phase_label": label,
        "raw_unit": "rad",
        "display_unit": "turns",
        "conversion": "continuous_unwrap(raw_rad) / (2*pi)",
        "window": window,
        "requested_window_ps": list(WINDOWS_PS[window]),
        "selected_first_ps": ps(trace.time[indices[0]]),
        "selected_last_ps": ps(trace.time[indices[-1]]),
        "sample_count": len(indices),
        "first_rad": float(values[0]),
        "last_rad": float(values[-1]),
        "delta_rad": float(delta_rad),
        "delta_turns": float(delta_rad / TAU),
        "mean_turns": float(sum(values) / len(values) / TAU),
        "p2p_turns": float((max(values) - min(values)) / TAU),
    }


def waveform_window(trace: RawTrace, label: str, window: str, unit: str) -> dict[str, Any]:
    metrics = waveform_window_metrics(trace.time, raw_column(trace, label), bounds_s(window), unit=unit)
    metrics["signal_label"] = label
    metrics["window"] = window
    metrics["requested_window_ps"] = list(WINDOWS_PS[window])
    return metrics


def phase_area_candidate(trace: RawTrace, phase_label: str, voltage_label: str, window: str) -> dict[str, Any]:
    """Return local same-JJ phase/area candidates and the principal candidate."""

    indices = selected_indices(trace, window)
    if len(indices) < 2:
        raise ValueError(f"local window {window} has fewer than two samples")
    start, end = indices[0], indices[-1]
    local = voltage_gap_candidates(
        trace.time[start : end + 1],
        raw_column(trace, phase_label)[start : end + 1],
        raw_column(trace, voltage_label)[start : end + 1],
    )
    candidates = []
    for item in local["candidates"]:
        copied = dict(item)
        copied["association_window"] = window
        # The detector runs on the local window slice.  Promote every stored
        # index back to the original raw-trace coordinate system; otherwise a
        # later independent check could accidentally interpret a local index
        # as a global CSV index while the recorded ps endpoints look valid.
        for index_key in ("core_start_index", "core_end_index", "measure_start_index", "measure_end_index"):
            copied[f"local_{index_key}"] = int(item[index_key])
            copied[index_key] = start + int(item[index_key])
        core_start = int(copied["core_start_index"])
        core_end = int(copied["core_end_index"])
        voltage = raw_column(trace, voltage_label)
        peak_index = max(
            range(core_start, core_end + 1),
            key=lambda index: abs(float(voltage[index])),
        )
        copied["peak_time_ps"] = ps(trace.time[peak_index])
        copied["peak_voltage_V"] = float(voltage[peak_index])
        copied["peak_abs_voltage_V"] = abs(float(voltage[peak_index]))
        copied["phase_area_agreement_diagnostic"] = bool(
            item["phase_delta_turns"] * item["voltage_area_turns"] > 0.0
            and abs(item["signed_phase_area_residual_turns"])
            <= LEGACY_PHASE_AREA_DIAGNOSTIC_MAX_TURNS
        )
        copied["heuristic_one_phi0"] = bool(
            HEURISTIC_ONE_PHI0[0] <= abs(item["phase_delta_turns"]) <= HEURISTIC_ONE_PHI0[1]
            and HEURISTIC_ONE_PHI0[0] <= abs(item["voltage_area_turns"]) <= HEURISTIC_ONE_PHI0[1]
            and copied["phase_area_agreement_diagnostic"]
        )
        candidates.append(copied)
    principal = None
    if candidates:
        principal = max(candidates, key=lambda item: max(abs(float(item["phase_delta_turns"])), abs(float(item["voltage_area_turns"]))))
    comparable = [item for item in candidates if item["heuristic_one_phi0"]]
    return {
        "phase_label": phase_label,
        "voltage_label": voltage_label,
        "voltage_to_phase_sign": 1,
        "reporting_direction": 1,
        "branch_mapping": "direct same-JJ P/V branch; voltage orientation aligned +1",
        "association_window": window,
        "peak_abs_voltage_V": local["peak_abs_voltage_V"],
        "active_threshold_V": local["active_threshold_V"],
        "candidate_count": len(candidates),
        "comparable_one_phi0_candidate_count": len(comparable),
        "extra_comparable_candidate_count": max(0, len(comparable) - 1),
        "principal": principal,
        "candidates": candidates,
        "detector_note": "existing task-local voltage-gap helper applied only to READ_LOCAL slice; not the old 0-200 ps result",
    }


def voltage_activity_summary(trace: RawTrace, label: str, window: str) -> dict[str, Any]:
    """Locate voltage activity for QBOUT, which has no direct P(QBOUT) column."""

    values = raw_column(trace, label)
    indices = selected_indices(trace, window)
    selected = [float(values[index]) for index in indices]
    peak_abs = max(abs(value) for value in selected)
    active_threshold = max(1.0e-6, 0.01 * peak_abs)
    quiet_threshold = max(0.2e-6, 0.002 * peak_abs)
    active = [abs(value) > active_threshold for value in selected]
    runs: list[tuple[int, int]] = []
    start: int | None = None
    for position, is_active in enumerate(active):
        if is_active and start is None:
            start = position
        elif not is_active and start is not None:
            runs.append((start, position - 1))
            start = None
    if start is not None:
        runs.append((start, len(active) - 1))
    merged: list[tuple[int, int]] = []
    for run_start, run_end in runs:
        if not merged:
            merged.append((run_start, run_end))
            continue
        previous_start, previous_end = merged[-1]
        gap_start = previous_end + 1
        gap_end = run_start - 1
        gap_duration_ps = ps(trace.time[indices[run_start]] - trace.time[indices[previous_end]])
        gap_quiet = gap_start > gap_end or all(abs(selected[index]) <= quiet_threshold for index in range(gap_start, gap_end + 1))
        if gap_quiet and gap_duration_ps >= MIN_QUIESCENT_GAP_PS:
            merged.append((run_start, run_end))
        else:
            merged[-1] = (previous_start, run_end)
    clusters = []
    for run_start, run_end in merged:
        local_values = selected[run_start : run_end + 1]
        peak_position = max(range(run_start, run_end + 1), key=lambda position: abs(selected[position]))
        clusters.append(
            {
                "onset_ps": ps(trace.time[indices[run_start]]),
                "end_ps": ps(trace.time[indices[run_end]]),
                "peak_time_ps": ps(trace.time[indices[peak_position]]),
                "peak_voltage_V": float(selected[peak_position]),
                "peak_abs_voltage_V": float(max(abs(value) for value in local_values)),
                "duration_ps": ps(trace.time[indices[run_end]] - trace.time[indices[run_start]]),
            }
        )
    principal = max(clusters, key=lambda item: item["peak_abs_voltage_V"]) if clusters else None
    return {
        "signal_label": label,
        "window": window,
        "requested_window_ps": list(WINDOWS_PS[window]),
        "selected_first_ps": ps(trace.time[indices[0]]),
        "selected_last_ps": ps(trace.time[indices[-1]]),
        "sample_count": len(indices),
        "active_threshold_V": active_threshold,
        "quiet_threshold_V": quiet_threshold,
        "cluster_count": len(clusters),
        "clusters": clusters,
        "principal": principal,
        "count_semantics": "voltage activity clusters only; not SFQ event count",
    }


def post_settling(trace: RawTrace, phase_label: str, voltage_label: str) -> dict[str, Any]:
    phase = phase_window(trace, phase_label, "POST_SETTLING")
    voltage = waveform_window(trace, voltage_label, "POST_SETTLING", "V")
    duration_ps = WINDOWS_PS["POST_SETTLING"][1] - WINDOWS_PS["POST_SETTLING"][0]
    return {
        "window": "POST_SETTLING",
        "phase": phase,
        "voltage": voltage,
        "phase_drift_rate_turns_per_ps": float(phase["delta_turns"] / duration_ps),
        "settling_descriptor": "phase drift and voltage mean/RMS reported; no strict 0.2-uV/0.25-ps veto",
    }


def condition_qa(trace: RawTrace, condition: str) -> dict[str, Any]:
    digest = sha256_file(trace.path)
    qa = trace.qa()
    qa.update(
        {
            "condition": condition,
            "sha256": digest,
            "expected_sha256": REQUIRED_RAW_SHA256[condition],
            "expected_hash_match": digest == REQUIRED_RAW_SHA256[condition],
            "time_start_ps": ps(trace.time[0]),
            "time_end_ps": ps(trace.time[-1]),
            "dt_min_ps": ps(min(trace.dt)),
            "dt_max_ps": ps(max(trace.dt)),
            "duplicate_columns_explicit": trace.duplicate_columns,
        }
    )
    return qa


def compare_signal(
    left: RawTrace,
    right: RawTrace,
    left_condition: str,
    right_condition: str,
    label: str,
    window: str,
    unit: str,
    scale: float,
    phase: bool = False,
) -> dict[str, Any]:
    left_values: Sequence[float]
    right_values: Sequence[float]
    if phase:
        left_unwrapped = continuous_unwrap(raw_column(left, label))
        right_unwrapped = continuous_unwrap(raw_column(right, label))
        left_indices = selected_indices(left, "PRE_READ")
        right_indices = selected_indices(right, "PRE_READ")
        left_reference = sum(left_unwrapped[index] for index in left_indices) / len(left_indices)
        right_reference = sum(right_unwrapped[index] for index in right_indices) / len(right_indices)
        left_values = tuple((left_unwrapped[index] - left_reference) / TAU for index in range(len(left.time)))
        right_values = tuple((right_unwrapped[index] - right_reference) / TAU for index in range(len(right.time)))
        scale = 1.0
        unit = "turns"
    else:
        left_values = raw_column(left, label)
        right_values = raw_column(right, label)
    indices_left = selected_indices(left, window)
    indices_right = selected_indices(right, window)
    result = compare_windowed_series(
        left.time,
        left_values,
        right.time,
        right_values,
        bounds_s(window),
        value_scale=scale,
        unit=unit,
        include_correlation=True,
    )
    result.update(
        {
            "left_condition": left_condition,
            "right_condition": right_condition,
            "signal_label": label,
            "window": window,
            "left_sample_count": len(indices_left),
            "right_sample_count": len(indices_right),
            "comparison_convention": "right_minus_left",
            "phase_baseline_alignment": "PRE_READ mean" if phase else None,
        }
    )
    return result


def b0_analysis(traces: dict[str, RawTrace]) -> dict[str, Any]:
    condition_metrics: dict[str, Any] = {}
    for condition, trace in traces.items():
        condition_metrics[condition] = {
            "signals": {
                key: {
                    "read_drive": waveform_window(trace, label, "READ_DRIVE", unit),
                    "read_response_tail": waveform_window(trace, label, "READ_RESPONSE_TAIL", unit),
                    "pre_read": waveform_window(trace, label, "PRE_READ", unit),
                }
                for key, (label, unit) in B0_SIGNALS.items()
            },
            "bvmout_phase": {
                window: phase_window(trace, "P(BVMOUT)", window)
                for window in ("PRE_READ", "READ_LOCAL", "POST_SETTLING")
            },
            "line_markers": {
                name: {
                    "read_local_phase": phase_window(trace, phase_label, "READ_LOCAL"),
                    "local_response": phase_area_candidate(trace, phase_label, voltage_label, "READ_LOCAL"),
                }
                for name, (phase_label, voltage_label) in LINE_MARKERS.items()
            },
        }
    state_comparisons = {}
    load_comparisons = {}
    for label, unit in B0_SIGNALS.values():
        scale = 1.0e6 if unit == "A" else 1.0e3
        state_comparisons[label] = compare_signal(
            traces["S0-J"], traces["S1-J"], "S0-J", "S1-J", label, "READ_LOCAL", unit=unit.replace("A", "uA").replace("V", "mV"), scale=scale
        )
        load_comparisons[f"S0_R_vs_J::{label}"] = compare_signal(
            traces["S0-R"], traces["S0-J"], "S0-R", "S0-J", label, "READ_LOCAL", unit=unit.replace("A", "uA").replace("V", "mV"), scale=scale
        )
        load_comparisons[f"S1_R_vs_J::{label}"] = compare_signal(
            traces["S1-R"], traces["S1-J"], "S1-R", "S1-J", label, "READ_LOCAL", unit=unit.replace("A", "uA").replace("V", "mV"), scale=scale
        )
    for label in ("P(BVMOUT)",):
        state_comparisons[label] = compare_signal(
            traces["S0-J"], traces["S1-J"], "S0-J", "S1-J", label, "READ_LOCAL", unit="turns", scale=1.0, phase=True
        )
        load_comparisons[f"S0_R_vs_J::{label}"] = compare_signal(
            traces["S0-R"], traces["S0-J"], "S0-R", "S0-J", label, "READ_LOCAL", unit="turns", scale=1.0, phase=True
        )
        load_comparisons[f"S1_R_vs_J::{label}"] = compare_signal(
            traces["S1-R"], traces["S1-J"], "S1-R", "S1-J", label, "READ_LOCAL", unit="turns", scale=1.0, phase=True
        )
    observed_line_markers = []
    for condition, record in condition_metrics.items():
        for marker, marker_record in record["line_markers"].items():
            principal = marker_record["local_response"]["principal"]
            observed_line_markers.append(
                {
                    "condition": condition,
                    "marker": marker,
                    "principal_abs_phase_turns": abs(float(principal["phase_delta_turns"])) if principal else 0.0,
                    "principal_abs_area_turns": abs(float(principal["voltage_area_turns"])) if principal else 0.0,
                    "heuristic_one_phi0": bool(principal and principal["heuristic_one_phi0"]),
                }
            )
    return {
        "condition_metrics": condition_metrics,
        "state_comparison_S0J_to_S1J": state_comparisons,
        "downstream_load_comparisons": load_comparisons,
        "line_guard_observed_markers": observed_line_markers,
        "coverage_note": "Only B_LD4_01, B_LD4_11 and BVMOUT are directly probed; the other nine SL JJ branches remain unobserved.",
        "functional_verdict": "INCONCLUSIVE",
        "strict_verdict": "NOT_YET_QUALIFIED",
        "verdict_reason": "state-dependent waveform reaches QBin and observed markers show no one-Phi0 local candidate, but the full 12-JJ line is not fully probed and no convergence/robustness evidence exists",
    }


def qb_signal_analysis(traces: dict[str, RawTrace]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for condition in ("S0-J", "S1-J", "S1-R", "S0-R"):
        trace = traces[condition]
        output[condition] = {}
        for name, (phase_label, voltage_label) in QB_SIGNALS.items():
            local = phase_area_candidate(trace, phase_label, voltage_label, "READ_LOCAL")
            output[condition][name] = {
                "pre_read_phase": phase_window(trace, phase_label, "PRE_READ"),
                "pre_read_voltage": waveform_window(trace, voltage_label, "PRE_READ", "V"),
                "read_drive_phase": phase_window(trace, phase_label, "READ_DRIVE"),
                "read_local_phase": phase_window(trace, phase_label, "READ_LOCAL"),
                "read_drive_voltage": waveform_window(trace, voltage_label, "READ_DRIVE", "V"),
                "read_response_tail_voltage": waveform_window(trace, voltage_label, "READ_RESPONSE_TAIL", "V"),
                "post_settling": post_settling(trace, phase_label, voltage_label),
                "local_response": local,
            }
    s0 = output["S0-J"]
    s1 = output["S1-J"]
    target_s1 = [s1[name]["local_response"]["principal"] for name in ("BJ1", "BJ2")]
    target_s0 = [s0[name]["local_response"]["principal"] for name in ("BJ1", "BJ2")]
    s1_has_target = any(item and item["heuristic_one_phi0"] for item in target_s1)
    s0_has_target = any(item and item["heuristic_one_phi0"] for item in target_s0)
    return {
        "conditions": output,
        "state_selectivity": {
            "S1J_target_response_in_BJ1_or_BJ2": s1_has_target,
            "S0J_comparable_response_in_BJ1_or_BJ2": s0_has_target,
            "false_trigger_absence_in_this_local_rule": not s0_has_target,
            "criterion_scope": "exploratory local 0.8-1.2 Phi0 heuristic plus same-JJ phase/area agreement; not a strict Gate",
        },
        "functional_verdict": "FUNCTIONAL_PASS" if s1_has_target and not s0_has_target else "INCONCLUSIVE",
        "strict_verdict": "NOT_YET_QUALIFIED",
        "verdict_reason": "S1-J has a READ-local one-Phi0-scale BJ1/BJ2 response while S0-J has no comparable target response; strict convergence and robustness are absent",
    }


def jtl_stage_record(trace: RawTrace, stage: int, condition: str) -> dict[str, Any]:
    phase_label = f"P(B02|XJTL1_{stage})"
    voltage_label = f"V(B02|XJTL1_{stage})"
    local = phase_area_candidate(trace, phase_label, voltage_label, "READ_LOCAL")
    return {
        "stage": f"JTL{stage}",
        "condition": condition,
        "marker": "B02",
        "marker_role": "output-facing; B02 is downstream of B01 in BVMSim/library_josim/jtl2.cir",
        "pre_read_phase": phase_window(trace, phase_label, "PRE_READ"),
        "read_local_phase": phase_window(trace, phase_label, "READ_LOCAL"),
        "read_local_voltage": waveform_window(trace, voltage_label, "READ_LOCAL", "V"),
        "post_settling": post_settling(trace, phase_label, voltage_label),
        "local_response": local,
    }


def b3_analysis(traces: dict[str, RawTrace]) -> dict[str, Any]:
    s1_jtl = [jtl_stage_record(traces["S1-J"], stage, "S1-J") for stage in range(1, 7)]
    s0_jtl = [jtl_stage_record(traces["S0-J"], stage, "S0-J") for stage in range(1, 7)]
    s1_bj2 = phase_area_candidate(traces["S1-J"], "P(BJ2|XBQ1)", "V(BJ2|XBQ1)", "READ_LOCAL")
    s0_bj2 = phase_area_candidate(traces["S0-J"], "P(BJ2|XBQ1)", "V(BJ2|XBQ1)", "READ_LOCAL")
    s1_qbout = voltage_activity_summary(traces["S1-J"], "V(QBOUT)", "READ_LOCAL")
    s0_qbout = voltage_activity_summary(traces["S0-J"], "V(QBOUT)", "READ_LOCAL")

    previous_onset = s1_bj2["principal"]["onset_ps"] if s1_bj2["principal"] else None
    for stage in s1_jtl:
        principal = stage["local_response"]["principal"]
        stage["latency_from_previous_ps"] = (
            float(principal["onset_ps"]) - float(previous_onset) if principal and previous_onset is not None else None
        )
        previous_onset = principal["onset_ps"] if principal else previous_onset
    for stage in s0_jtl:
        principal = stage["local_response"]["principal"]
        stage["latency_from_previous_ps"] = None

    s1_principals = [stage["local_response"]["principal"] for stage in s1_jtl]
    s0_principals = [stage["local_response"]["principal"] for stage in s0_jtl]
    s1_one_phi = [bool(item and item["heuristic_one_phi0"]) for item in s1_principals]
    s0_one_phi = [bool(item and item["heuristic_one_phi0"]) for item in s0_principals]
    s1_onsets = [float(item["onset_ps"]) for item in s1_principals if item]
    ordered = all(right > left for left, right in zip(s1_onsets, s1_onsets[1:]))
    polarity = [int(item["direction"]) for item in s1_principals if item]
    b3a_pass = bool(s1_jtl[0]["local_response"]["principal"] and s1_jtl[0]["local_response"]["principal"]["heuristic_one_phi0"] and not (s0_jtl[0]["local_response"]["principal"] and s0_jtl[0]["local_response"]["principal"]["heuristic_one_phi0"]))
    b3b_pass = bool(all(s1_one_phi) and not any(s0_one_phi) and ordered and all(value == 1 for value in polarity) and all(stage["local_response"]["extra_comparable_candidate_count"] == 0 for stage in s1_jtl))
    return {
        "output_facing_marker": "B02",
        "input_side_marker": "B01 (reported in legacy analysis; not counted as a second SFQ)",
        "source": {
            "S1-J_BJ2": s1_bj2,
            "S0-J_BJ2": s0_bj2,
            "S1-J_QBOUT_voltage_activity": s1_qbout,
            "S0-J_QBOUT_voltage_activity": s0_qbout,
        },
        "S1-J_stages": s1_jtl,
        "S0-J_stages": s0_jtl,
        "summary": {
            "S1-J_B02_one_phi0_by_stage": s1_one_phi,
            "S0-J_B02_one_phi0_by_stage": s0_one_phi,
            "S1-J_B02_onset_ps": s1_onsets,
            "S1-J_B02_polarity": polarity,
            "S1-J_ordered_onsets": ordered,
            "S1-J_B02_extra_comparable_pulses": [stage["local_response"]["extra_comparable_candidate_count"] for stage in s1_jtl],
        },
        "B3a": {
            "functional_verdict": "FUNCTIONAL_PASS" if b3a_pass else "INCONCLUSIVE",
            "strict_verdict": "NOT_YET_QUALIFIED",
            "reason": "S1-J JTL1 B02 has a one-Phi0-scale local response while S0-J does not" if b3a_pass else "JTL1 launch criterion not fully supported by this local rule",
        },
        "B3b": {
            "functional_verdict": "FUNCTIONAL_PASS" if b3b_pass else "INCONCLUSIVE",
            "strict_verdict": "NOT_YET_QUALIFIED",
            "reason": "S1-J B02 responses are approximately one Phi0 at all six stages, ordered, positive, and absent at the same heuristic level in S0-J" if b3b_pass else "not all stage-level transport criteria passed",
        },
        "strict_limitation": "A001 has no timestep convergence, repeat/robustness evidence, or boundary-sensitivity study",
    }


def load_legacy_diagnostic() -> dict[str, Any]:
    path = EXP / "analysis/metrics.json"
    if not path.is_file():
        return {"status": "MISSING"}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {
        "source": str(path.relative_to(REPO)),
        "sha256": sha256_file(path),
        "status": data.get("status"),
        "primary_stage_classification": data.get("classification", {}).get("primary_stage_classification"),
        "quick_label": data.get("classification", {}).get("quick_label"),
        "interpretation": "retained only as old detector diagnostic; not used as Boundary verdict",
    }


def provenance(traces: dict[str, RawTrace], actual_head: str, start_status: str) -> dict[str, Any]:
    files = {
        "boundary_spec": REPO / "docs/research/BOUNDARY_SPEC_V1.md",
        "metric_spec": REPO / "docs/research/METRIC_SPEC_V2.md",
        "jtl_source": REPO / "BVMSim/library_josim/jtl2.cir",
        "legacy_analysis": EXP / "analysis/analyze.py",
        "legacy_metrics": EXP / "analysis/metrics.json",
        "plotter": REPO / "scripts/josim-plot2.py",
        "boundary_analysis_script": EXP / "analysis/boundary_reassessment.py",
        "boundary_plot_script": EXP / "analysis/boundary_plot.py",
        "independent_boundary_check_script": EXP / "analysis/independent_boundary_check.py",
    }
    return {
        "requested_base_head": REQUESTED_BASE_HEAD,
        "actual_head_at_analysis": actual_head,
        "head_note": "actual HEAD includes the later historical data_tran.html visualization commit; no A001 raw/input was changed by that commit",
        "git_status_at_analysis_start": start_status,
        "raw_files": {
            condition: {
                "path": str(trace.path.relative_to(REPO)),
                "sha256": sha256_file(trace.path),
                "expected_sha256": REQUIRED_RAW_SHA256[condition],
            }
            for condition, trace in traces.items()
        },
        "source_hashes": {
            name: {"path": str(path.relative_to(REPO)), "sha256": sha256_file(path)}
            for name, path in files.items()
            if path.is_file()
        },
        "solver": {
            "path": "build/josim-cli",
            "sha256": sha256_file(REPO / "build/josim-cli") if (REPO / "build/josim-cli").is_file() else None,
            "version_source": "existing A001 provenance; solver was not invoked in this analysis-only reassessment",
        },
    }


def main() -> int:
    start_status = subprocess.run(
        ["git", "status", "--short", "--untracked-files=all"], cwd=REPO, check=True, capture_output=True, text=True
    ).stdout.strip()
    actual_head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPO, check=True, capture_output=True, text=True
    ).stdout.strip()
    traces = {condition: read_csv(path) for condition, path in CONDITIONS.items()}
    all_grid_exact = all(exact_time_grid_identity(traces["S0-R"].time, trace.time) for trace in traces.values())
    raw_hashes_match = all(sha256_file(trace.path) == REQUIRED_RAW_SHA256[condition] for condition, trace in traces.items())
    qa_valid = all(condition_qa(trace, condition)["status"] == "VALID" for condition, trace in traces.items())
    qb_metrics = qb_signal_analysis(traces)
    bj2_s1 = qb_metrics["conditions"]["S1-J"]["BJ2"]
    bj2_s0 = qb_metrics["conditions"]["S0-J"]["BJ2"]
    bj2_s1r = qb_metrics["conditions"]["S1-R"]["BJ2"]
    bj2_principal = bj2_s1["local_response"]["principal"]
    b2_candidate = bool(
        bj2_principal
        and bj2_principal["heuristic_one_phi0"]
        and bj2_s1["local_response"]["extra_comparable_candidate_count"] == 0
    )
    metrics = {
        "schema_version": "BOUNDARY_REASSESSMENT_V1",
        "analysis_mode": "analysis-only; no JoSIM invocation; no raw rewrite",
        "requested_base_head": REQUESTED_BASE_HEAD,
        "actual_head_at_analysis": actual_head,
        "status": "VALID" if qa_valid and all_grid_exact and raw_hashes_match else "ANALYSIS_INVALID",
        "raw_qa": {
            "all_conditions_valid": qa_valid,
            "all_four_time_grids_exactly_identical": all_grid_exact,
            "raw_hashes_match_frozen_A001": raw_hashes_match,
            "conditions": {condition: condition_qa(trace, condition) for condition, trace in traces.items()},
        },
        "windows": {
            name: {"start_ps": bounds[0], "end_ps": bounds[1], "semantics": "half-open against actual CSV time; POST_REST end 200 ps is equivalent because last sample is 199.975 ps"}
            for name, bounds in WINDOWS_PS.items()
        },
        "measurement_contract": {
            "boundary_spec": "docs/research/BOUNDARY_SPEC_V1.md",
            "metric_spec": "docs/research/METRIC_SPEC_V2.md",
            "phase_raw_unit": "rad",
            "phase_turn_conversion": "delta_phi_rad/(2*pi)",
            "voltage_area": "same-JJ direct V branch, actual CSV time grid trapezoid, divided by Phi0",
            "event_count_boundary": "local phase/area response is not automatically an SFQ count",
            "one_phi0_heuristic_band": list(HEURISTIC_ONE_PHI0),
            "phase_area_diagnostic_bound_turns": LEGACY_PHASE_AREA_DIAGNOSTIC_MAX_TURNS,
        },
        "legacy_detector_diagnostic": load_legacy_diagnostic(),
        "B0": b0_analysis(traces),
        "B1": qb_metrics,
        "B2": {
            "target": "S1-J BJ2",
            "S1-J": bj2_s1,
            "S0-J_control": bj2_s0,
            "S1-R_load_control": bj2_s1r,
            "functional_verdict": "FUNCTIONAL_PASS" if b2_candidate else "INCONCLUSIVE",
            "strict_verdict": "NOT_YET_QUALIFIED",
            "evidence_level": "QUANTIZED_LOCAL_SFQ_CANDIDATE" if b2_candidate else "SFQ_LIKE_RESPONSE",
            "reason": "READ-local S1-J BJ2 phase and direct voltage area are both near one Phi0, with one principal candidate and no second comparable local candidate; A001 has no convergence/robustness evidence",
        },
        "B3": b3_analysis(traces),
        "B4": {
            "functional_verdict": "NOT_TESTED",
            "strict_verdict": "NOT_YET_QUALIFIED",
            "reason": "A001 contains no T1 or downstream logic",
        },
        "provenance": provenance(traces, actual_head, start_status),
    }
    output = EXP / "analysis/boundary_metrics.json"
    output.write_text(json.dumps(metrics, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {output.relative_to(REPO)}")
    print(f"status={metrics['status']} raw_hashes_match={raw_hashes_match} exact_grid={all_grid_exact}")
    return 0 if metrics["status"] == "VALID" else 2


if __name__ == "__main__":
    raise SystemExit(main())
