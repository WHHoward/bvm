#!/usr/bin/env python3
"""Raw-first analysis for the registered L3/BJ2 targeted combination."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
THRESHOLDS = (0.5, 1.5, 2.5, 3.5, 4.5)
CONTROL_WINDOWS = {
    "ZERO_STATE_READ_CONTROL": (70.0, 81.0),
    "POST_CONTROL_IDLE": (81.0, 90.0),
    "WRITE1": (90.0, 101.0),
    "SETTLE": (101.0, 110.0),
}
FINAL_WINDOW = (110.0, 200.0)
CONTROL_PEAK_THRESHOLD_V = 2.0e-4
CONTROL_CURRENT_THRESHOLD_A = 2.0e-5
PEAK_GAP_PS = 2.5
PHI0 = 2.067833848e-15

BVM_REQUIRED = tuple(f"I(L_SL|XBVM{index})" for index in range(1, 5)) + ("V(COMMON_SL)",)
JSL_REQUIRED = tuple(f"{kind}(B_JSL{index})" for index in range(1, 9) for kind in ("P", "V", "I"))
QB_REQUIRED = (
    "V(QBIN)", "I(LIN|XBQ1)", "V(LIN|XBQ1)", "I(L1|XBQ1)", "V(L1|XBQ1)",
    "I(L2|XBQ1)", "V(L2|XBQ1)", "I(L3|XBQ1)", "V(L3|XBQ1)",
    "I(RJ1|XBQ1)", "V(RJ1|XBQ1)", "I(RJ2|XBQ1)", "V(RJ2|XBQ1)",
    "P(BJS|XBQ1)", "V(BJS|XBQ1)", "I(BJS|XBQ1)",
    "P(BJ1|XBQ1)", "V(BJ1|XBQ1)", "I(BJ1|XBQ1)",
    "P(BJ2|XBQ1)", "V(BJ2|XBQ1)", "I(BJ2|XBQ1)", "V(QBOUT)",
)
JTL_REQUIRED = tuple(
    item
    for stage in range(1, 7)
    for item in (
        f"P(B01|XJTL1_{stage})", f"V(B01|XJTL1_{stage})", f"I(B01|XJTL1_{stage})",
        f"P(B02|XJTL1_{stage})", f"V(B02|XJTL1_{stage})", f"I(B02|XJTL1_{stage})",
        f"V(JTL{stage}_OUT)",
    )
) + ("I(R_TERM)",)
REQUIRED = BVM_REQUIRED + JSL_REQUIRED + QB_REQUIRED + JTL_REQUIRED

REFERENCE_CASES = {
    "canonical_L3_1p3_BJ2_2p0": {
        "0011": EXP / "references/canonical_l3p13/0011/raw.csv",
        "0111": EXP / "references/canonical_l3p13/0111/raw.csv",
    },
    "L3_2p0_BJ2_2p0": {
        "0011": EXP / "references/l3p20/0011/raw.csv",
        "0111": EXP / "references/l3p20/0111/raw.csv",
    },
    "L3_1p3_BJ2_2p2": {
        "0011": EXP / "references/bj2p22_l3p13/0011/raw.csv",
        "0111": EXP / "references/bj2p22_l3p13/0111/raw.csv",
    },
}

sys.path.insert(0, str(REPO / "scripts"))
from bvmtools.phase import continuous_unwrap  # noqa: E402
from bvmtools.raw import RawTrace, read_csv  # noqa: E402


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def load(path: Path) -> RawTrace:
    trace = read_csv(path)
    if trace.duplicate_columns:
        raise RuntimeError(f"duplicate raw columns: {path}: {trace.duplicate_columns}")
    missing = [label for label in REQUIRED if label not in trace.headers]
    if missing:
        raise RuntimeError(f"missing required targeted-combination probes: {path}: {missing}")
    if len(trace.time) != 1999 or trace.time[0] != 0.0 or trace.time[-1] != 1.999e-10:
        raise RuntimeError(f"unexpected actual time grid: {path}")
    if any(right <= left for left, right in zip(trace.time, trace.time[1:])):
        raise RuntimeError(f"non-increasing actual time grid: {path}")
    for label in REQUIRED:
        if not all(math.isfinite(value) for value in trace.column(label)):
            raise RuntimeError(f"non-finite required probe: {path}: {label}")
    return trace


def indices(trace: RawTrace, start_ps: float, end_ps: float) -> list[int]:
    return [index for index, time in enumerate(trace.time) if start_ps <= time * 1.0e12 < end_ps]


def trapezoid(times: tuple[float, ...], values: list[float], selected: list[int]) -> float:
    total = 0.0
    for left, right in zip(selected, selected[1:]):
        if right == left + 1:
            total += 0.5 * (values[left] + values[right]) * (times[right] - times[left])
    return total


def phase_info(trace: RawTrace, label: str) -> dict[str, Any]:
    raw = tuple(trace.column(label))
    unwrapped = tuple(continuous_unwrap(raw))
    base = next(index for index, time in enumerate(trace.time) if time * 1.0e12 >= 101.0)
    relative = tuple((value - unwrapped[base]) / (2.0 * math.pi) for value in unwrapped[base:])
    threshold_times = {
        f"{threshold:g}": next(
            (trace.time[index + base] * 1.0e12 for index, value in enumerate(relative) if value >= threshold),
            None,
        )
        for threshold in THRESHOLDS
    }
    return {
        "label": label,
        "raw_unit": "radians",
        "baseline_time_ps": trace.time[base] * 1.0e12,
        "threshold_navigation_times_ps": threshold_times,
        "max_relative_turns": max(relative),
        "final_relative_turns": relative[-1],
        "rollback_turns_diagnostic": max(relative) - relative[-1],
        "semantic_role": "PHASE_NAVIGATION_ONLY; not an SFQ count",
    }


def phase_window_max(trace: RawTrace, label: str, start_ps: float, end_ps: float) -> float | None:
    raw = tuple(trace.column(label))
    unwrapped = tuple(continuous_unwrap(raw))
    base = next(index for index, time in enumerate(trace.time) if time * 1.0e12 >= 101.0)
    selected = indices(trace, start_ps, end_ps)
    return max(((unwrapped[index] - unwrapped[base]) / (2.0 * math.pi) for index in selected), default=None)


def positive_peaks(trace: RawTrace, label: str, start_ps: float, end_ps: float, threshold: float) -> list[dict[str, float]]:
    values = list(trace.column(label))
    times = [time * 1.0e12 for time in trace.time]
    candidates = [
        index for index in range(1, len(values) - 1)
        if start_ps <= times[index] < end_ps
        and values[index] >= threshold
        and values[index] >= values[index - 1]
        and values[index] > values[index + 1]
    ]
    selected: list[int] = []
    for index in candidates:
        if not selected or times[index] - times[selected[-1]] > PEAK_GAP_PS:
            selected.append(index)
        elif values[index] > values[selected[-1]]:
            selected[-1] = index
    return [{"peak_time_ps": times[index], "peak_value": values[index], "sample_index": index} for index in selected]


def match_after(peaks: list[dict[str, float]], source_times: list[float | None]) -> list[dict[str, float]]:
    selected: list[dict[str, float]] = []
    cursor = 0
    for source_time in source_times:
        if source_time is None:
            break
        while cursor < len(peaks) and peaks[cursor]["peak_time_ps"] <= source_time:
            cursor += 1
        if cursor == len(peaks):
            break
        selected.append(peaks[cursor])
        cursor += 1
    return selected


def terminal_pulses(trace: RawTrace) -> dict[str, Any]:
    values = list(trace.column("V(JTL6_OUT)"))
    times = [time * 1.0e12 for time in trace.time]
    active = indices(trace, *FINAL_WINDOW)
    peaks = positive_peaks(trace, "V(JTL6_OUT)", *FINAL_WINDOW, CONTROL_PEAK_THRESHOLD_V)
    if not peaks:
        area = trapezoid(trace.time, values, active)
        return {"pulse_count": 0, "pulses": [], "total_area_V_s": area, "total_area_over_phi0": area / PHI0, "not_event_count": True}
    peak_indices = [int(peak["sample_index"]) for peak in peaks]
    valleys = [min(range(left, right + 1), key=lambda index: values[index]) for left, right in zip(peak_indices, peak_indices[1:])]
    bounds = [active[0], *valleys, active[-1]]
    pulses = []
    for ordinal, peak in enumerate(peaks):
        selected = list(range(bounds[ordinal], bounds[ordinal + 1] + 1))
        area = trapezoid(trace.time, values, selected)
        pulses.append({
            "pulse_index": ordinal + 1,
            "peak_time_ps": peak["peak_time_ps"],
            "peak_value_V": peak["peak_value"],
            "signed_area_V_s": area,
            "area_over_phi0": area / PHI0,
            "left_boundary_ps": times[bounds[ordinal]],
            "right_boundary_ps": times[bounds[ordinal + 1]],
            "sample_count": len(selected),
        })
    total = trapezoid(trace.time, values, active)
    return {
        "pulse_count": len(pulses),
        "pulses": pulses,
        "peak_separation_ps": [pulses[index + 1]["peak_time_ps"] - pulses[index]["peak_time_ps"] for index in range(len(pulses) - 1)],
        "total_area_V_s": total,
        "total_area_over_phi0": total / PHI0,
        "not_event_count": True,
    }


def ordered_control_chain(trace: RawTrace, start_ps: float, end_ps: float) -> list[list[float]]:
    q = positive_peaks(trace, "V(QBOUT)", start_ps, end_ps, CONTROL_PEAK_THRESHOLD_V)
    stages = [positive_peaks(trace, f"V(JTL{stage}_OUT)", start_ps, end_ps, CONTROL_PEAK_THRESHOLD_V) for stage in range(1, 7)]
    chains: list[list[float]] = []
    for q_peak in q:
        cursor = q_peak["peak_time_ps"]
        chain = [cursor]
        success = True
        for stage_peaks in stages:
            candidate = next((peak for peak in stage_peaks if peak["peak_time_ps"] > cursor), None)
            if candidate is None:
                success = False
                break
            cursor = candidate["peak_time_ps"]
            chain.append(cursor)
        if success:
            chains.append(chain)
    return chains


def control_info(trace: RawTrace) -> dict[str, Any]:
    windows: dict[str, Any] = {}
    complete_chain_count = 0
    for name, (start_ps, end_ps) in CONTROL_WINDOWS.items():
        chain = ordered_control_chain(trace, start_ps, end_ps)
        complete_chain_count += len(chain)
        downstream = {
            label: positive_peaks(trace, label, start_ps, end_ps, CONTROL_PEAK_THRESHOLD_V)
            for label in ("V(QBOUT)", "V(JTL1_OUT)", "V(JTL2_OUT)", "V(JTL3_OUT)", "V(JTL4_OUT)", "V(JTL5_OUT)", "V(JTL6_OUT)")
        }
        terminal_current = list(trace.column("I(R_TERM)"))
        selected = indices(trace, start_ps, end_ps)
        jtl6 = list(trace.column("V(JTL6_OUT)"))
        windows[name] = {
            "window_ps": [start_ps, end_ps],
            "complete_downstream_chain_count": len(chain),
            "complete_downstream_chains_ps": chain,
            "downstream_peak_counts": {label: len(values) for label, values in downstream.items()},
            "max_abs_terminal_current_A": max((abs(terminal_current[index]) for index in selected), default=0.0),
            "max_abs_JTL6_V": max((abs(jtl6[index]) for index in selected), default=0.0),
            "forbidden_chain_only": True,
        }
    return {
        "status": "CONTROL_CONTAMINATED" if complete_chain_count > 0 else "CLEAN",
        "complete_downstream_chain_count": complete_chain_count,
        "windows": windows,
        "thresholds": {"QBOUT_V": CONTROL_PEAK_THRESHOLD_V, "JTL_V": CONTROL_PEAK_THRESHOLD_V, "terminal_current_A_diagnostic": CONTROL_CURRENT_THRESHOLD_A},
        "criterion": "unintended complete QBOUT->JTL1..6 chain inside registered 70-110 ps history windows",
        "rollback_excluded_from_control": True,
        "phase_rollback_recorded_separately": True,
    }


def source_feedback(trace: RawTrace) -> dict[str, Any]:
    values = list(trace.column("I(B_JSL8)"))
    current = {}
    for name, window in (("110_112", (110.0, 112.0)), ("110_121", (110.0, 121.0)), ("121_124", (121.0, 124.0)), ("121_126", (121.0, 126.0))):
        selected = indices(trace, *window)
        current[name] = {
            "window_ps": list(window),
            "signed_area_A_s": trapezoid(trace.time, values, selected),
            "max_positive_current_A": max((values[index] for index in selected), default=None),
            "formula": "trapezoid(actual stored time grid, I(B_JSL8))",
        }
    post = indices(trace, 110.0, 200.0)
    crossing = None
    positive_seen = False
    for index in post:
        if values[index] > 1.0e-9:
            positive_seen = True
        elif positive_seen and values[index] < -1.0e-9:
            crossing = trace.time[index] * 1.0e12
            break
    return {
        "I_B_JSL8": current,
        "max_positive_current_A_110_200": max((values[index] for index in post), default=None),
        "first_sustained_positive_to_negative_crossing_ps": crossing,
        "positive_negative_threshold_A": 1.0e-9,
        "not_event_count": True,
    }


def sampled_currents(trace: RawTrace) -> dict[str, Any]:
    records = []
    for requested in (118.0, 120.0, 121.0, 122.0, 123.0, 124.0, 126.0):
        index = min(range(len(trace.time)), key=lambda item: abs(trace.time[item] * 1.0e12 - requested))
        actual = trace.time[index] * 1.0e12
        records.append({
            "requested_time_ps": requested,
            "actual_grid_time_ps": actual,
            "I_L1_A": trace.column("I(L1|XBQ1)")[index],
            "I_L2_A": trace.column("I(L2|XBQ1)")[index],
            "I_L3_A": trace.column("I(L3|XBQ1)")[index],
        })
    return {"actual_grid_only": True, "samples": records}


def case_evidence(trace: RawTrace) -> dict[str, Any]:
    phase_labels = {"BJ1": "P(BJ1|XBQ1)", "BJ2": "P(BJ2|XBQ1)", **{f"JTL{stage}": f"P(B01|XJTL1_{stage})" for stage in range(1, 7)}}
    phase = {name: phase_info(trace, label) for name, label in phase_labels.items()}
    phase_counts = {name: sum(value is not None for value in item["threshold_navigation_times_ps"].values()) for name, item in phase.items()}
    phase_count = min(phase_counts.values())
    source_times = [phase["BJ2"]["threshold_navigation_times_ps"].get(f"{THRESHOLDS[index]:g}") for index in range(phase_count)]
    jtl6_times = [phase["JTL6"]["threshold_navigation_times_ps"].get(f"{THRESHOLDS[index]:g}") for index in range(phase_count)]
    q_raw = positive_peaks(trace, "V(QBOUT)", *FINAL_WINDOW, CONTROL_PEAK_THRESHOLD_V)
    terminal = terminal_pulses(trace)
    q_matched = match_after(q_raw, source_times)
    terminal_matched = match_after(terminal["pulses"], jtl6_times)
    terminal["matched_candidate_pulses"] = terminal_matched
    terminal["matched_candidate_count"] = len(terminal_matched)
    complete_count = min(phase_count, len(q_matched), len(terminal_matched))
    ordered: dict[str, bool] = {}
    chain_times: dict[str, list[float | None]] = {}
    for ordinal in range(1, complete_count + 1):
        threshold = f"{THRESHOLDS[ordinal - 1]:g}"
        chain: list[float | None] = [
            phase["BJ1"]["threshold_navigation_times_ps"].get(threshold),
            phase["BJ2"]["threshold_navigation_times_ps"].get(threshold),
            q_matched[ordinal - 1]["peak_time_ps"] if len(q_matched) >= ordinal else None,
        ]
        chain.extend(phase[f"JTL{stage}"]["threshold_navigation_times_ps"].get(threshold) for stage in range(1, 7))
        chain.append(terminal_matched[ordinal - 1]["peak_time_ps"] if len(terminal_matched) >= ordinal else None)
        chain_times[str(ordinal)] = chain
        ordered[str(ordinal)] = all(value is not None for value in chain) and all(left < right for left, right in zip(chain, chain[1:]))
    reset_window = indices(trace, 121.0, 130.0)
    l1 = list(trace.column("I(L1|XBQ1)"))
    l2 = list(trace.column("I(L2|XBQ1)"))
    vdiff = [left - right for left, right in zip(trace.column("V(BJ1|XBQ1)"), trace.column("V(BJ2|XBQ1)"))]
    first_zero = next((trace.time[index] * 1.0e12 for index in reset_window if l1[index] == 0.0 or (index > reset_window[0] and l1[index - 1] * l1[index] < 0.0)), None)
    internal_reset = {
        "window_ps": [121.0, 130.0],
        "peak_I_L1_A": max((l1[index] for index in reset_window), default=None),
        "min_I_L1_A": min((l1[index] for index in reset_window), default=None),
        "first_I_L1_zero_or_sign_change_ps": first_zero,
        "peak_I_L2_A": max((l2[index] for index in reset_window), default=None),
        "peak_BJ1_minus_BJ2_voltage_V": max((vdiff[index] for index in reset_window), default=None),
        "min_BJ1_minus_BJ2_voltage_V": min((vdiff[index] for index in reset_window), default=None),
        "integral_118_121_V_s": trapezoid(trace.time, vdiff, indices(trace, 118.0, 121.0)),
        "integral_121_124_V_s": trapezoid(trace.time, vdiff, indices(trace, 121.0, 124.0)),
        "integral_124_128_V_s": trapezoid(trace.time, vdiff, indices(trace, 124.0, 128.0)),
        "BJ1_max_relative_turns": phase["BJ1"]["max_relative_turns"],
        "BJ1_final_relative_turns": phase["BJ1"]["final_relative_turns"],
        "BJ1_rollback_turns_diagnostic": phase["BJ1"]["rollback_turns_diagnostic"],
        "BJ2_max_relative_turns": phase["BJ2"]["max_relative_turns"],
        "BJ2_final_relative_turns": phase["BJ2"]["final_relative_turns"],
        "BJ2_rollback_turns_diagnostic": phase["BJ2"]["rollback_turns_diagnostic"],
        "max_fourth_cycle_BJ1_relative_turns_120_150": phase_window_max(trace, "P(BJ1|XBQ1)", 120.0, 150.0),
        "max_fourth_cycle_BJ2_relative_turns_120_150": phase_window_max(trace, "P(BJ2|XBQ1)", 120.0, 150.0),
    }
    return {
        "phase_navigation": phase,
        "phase_count_by_track": phase_counts,
        "phase_supported_count": phase_count,
        "qbout_raw_peak_navigation": q_raw,
        "qbout_matched_candidate_navigation": q_matched,
        "terminal": terminal,
        "complete_response_candidate_count": complete_count,
        "ordered_chain_by_candidate": ordered,
        "ordered_chain_times_ps": chain_times,
        "control": control_info(trace),
        "internal_reset": internal_reset,
        "window_currents": sampled_currents(trace),
        "source_feedback": source_feedback(trace),
        "not_sfq_count": True,
        "phase_navigation_only": True,
    }


def classify_case(case: dict[str, Any], *, is_n2: bool) -> dict[str, Any]:
    if case["control"]["status"] != "CLEAN":
        return {"classification": "CONTROL_CONTAMINATED", "control_status": "CONTROL_CONTAMINATED", "evidence_status": "INCONCLUSIVE"}
    count = case["complete_response_candidate_count"]
    ordered = case["ordered_chain_by_candidate"]
    if is_n2:
        name = "N2_2_COMPLETE" if count == 2 and ordered.get("1") and ordered.get("2") else "N2_NOT_2"
        return {"classification": name, "control_status": "CLEAN", "evidence_status": "BOUNDED_RESULT" if name == "N2_2_COMPLETE" else "INCONCLUSIVE"}
    if count == 3 and all(ordered.get(str(index), False) for index in (1, 2, 3)) and not ordered.get("4", False):
        return {"classification": "N3_3_COMPLETE", "control_status": "CLEAN", "evidence_status": "BOUNDED_RESULT"}
    if count >= 4 and ordered.get("4", False):
        return {"classification": "N3_4_COMPLETE", "control_status": "CLEAN", "evidence_status": "BOUNDED_RESULT"}
    if count >= 3:
        return {"classification": "N3_MULTIPLICITY_AMBIGUOUS", "control_status": "CLEAN", "evidence_status": "INCONCLUSIVE"}
    return {"classification": "N3_OTHER_OR_INCOMPLETE", "control_status": "CLEAN", "evidence_status": "INCONCLUSIVE"}


def response_record(case: dict[str, Any], ordinal: int) -> dict[str, Any]:
    threshold = f"{THRESHOLDS[ordinal - 1]:g}"
    terminal = case["terminal"].get("matched_candidate_pulses", [])
    q = case["qbout_matched_candidate_navigation"]
    times = {
        "BJ1_ps": case["phase_navigation"]["BJ1"]["threshold_navigation_times_ps"].get(threshold),
        "BJ2_ps": case["phase_navigation"]["BJ2"]["threshold_navigation_times_ps"].get(threshold),
        "QBOUT_peak_ps": q[ordinal - 1]["peak_time_ps"] if len(q) >= ordinal else None,
        "JTL1_ps": case["phase_navigation"]["JTL1"]["threshold_navigation_times_ps"].get(threshold),
        "JTL6_ps": case["phase_navigation"]["JTL6"]["threshold_navigation_times_ps"].get(threshold),
        "terminal_peak_ps": terminal[ordinal - 1]["peak_time_ps"] if len(terminal) >= ordinal else None,
    }
    return {"ordinal": ordinal, "threshold_navigation_level_turns": THRESHOLDS[ordinal - 1], "times_ps": times, "ordered_chain": case["ordered_chain_by_candidate"].get(str(ordinal), False), "phase_navigation_only": True}


def case_summary(case: dict[str, Any], *, is_n2: bool) -> dict[str, Any]:
    count = case["complete_response_candidate_count"]
    return {
        "classification": classify_case(case, is_n2=is_n2),
        "complete_response_candidate_count": count,
        "ordered_chain_by_candidate": case["ordered_chain_by_candidate"],
        "control": case["control"],
        "responses": [response_record(case, ordinal) for ordinal in range(1, min(count, 4) + 1)],
        "second_response": response_record(case, 2) if count >= 2 else None,
        "fourth_response": response_record(case, 4) if count >= 4 and not is_n2 else None,
        "terminal": {key: case["terminal"].get(key) for key in ("pulse_count", "matched_candidate_count", "peak_separation_ps", "total_area_over_phi0", "not_event_count")},
        "internal_reset": case["internal_reset"],
        "window_currents": case["window_currents"],
        "source_feedback": case["source_feedback"],
        "phase_navigation_only": True,
        "not_sfq_count": True,
    }


def analyze_pair(point_id: str, changes: dict[str, float], n2_path: Path, n3_path: Path) -> dict[str, Any]:
    candidate_n2_case, candidate_n3_case = case_evidence(load(n2_path)), case_evidence(load(n3_path))
    reference_evidence: dict[str, dict[str, dict[str, Any]]] = {}
    reference_hashes: dict[str, dict[str, str]] = {}
    for name, cases in REFERENCE_CASES.items():
        reference_evidence[name] = {mask: case_evidence(load(path)) for mask, path in cases.items()}
        reference_hashes[name] = {mask: sha256(path) for mask, path in cases.items()}
    n2_class = classify_case(candidate_n2_case, is_n2=True)
    n3_class = classify_case(candidate_n3_case, is_n2=False)
    if n2_class["classification"] == "CONTROL_CONTAMINATED" or n3_class["classification"] == "CONTROL_CONTAMINATED":
        outcome_class = "D"
    elif n2_class["classification"] == "N2_2_COMPLETE" and n3_class["classification"] == "N3_3_COMPLETE":
        outcome_class = "S"
    elif n3_class["classification"] in {"N3_MULTIPLICITY_AMBIGUOUS", "N3_OTHER_OR_INCOMPLETE"}:
        outcome_class = "D"
    elif n2_class["classification"] == "N2_2_COMPLETE" and n3_class["classification"] == "N3_4_COMPLETE":
        outcome_class = "A"
    elif n2_class["classification"] != "N2_2_COMPLETE" and n3_class["classification"] == "N3_3_COMPLETE":
        outcome_class = "B"
    elif n2_class["classification"] != "N2_2_COMPLETE" and n3_class["classification"] == "N3_4_COMPLETE":
        outcome_class = "C"
    else:
        outcome_class = "D"
    labels = {
        "S": "DIRECT_2_TO_3_L3_BJ2_CANDIDATE",
        "A": "N2_RESCUED_BUT_N3_FOURTH_REMAINS",
        "B": "N3_SUPPRESSED_BUT_N2_NOT_RESCUED",
        "C": "L3_BJ2_COMBINATION_UNFAVORABLE",
        "D": "N3_FOURTH_HANDOFF_BOUNDARY_CASE",
    }
    reference_summaries = {
        name: {
            "raw_paths": {mask: path.relative_to(REPO).as_posix() for mask, path in cases.items()},
            "raw_sha256": reference_hashes[name],
            "n2": case_summary(reference_evidence[name]["0011"], is_n2=True),
            "n3": case_summary(reference_evidence[name]["0111"], is_n2=False),
        }
        for name, cases in REFERENCE_CASES.items()
    }
    return {
        "schema": "bvm-qb-l3-bj2-targeted-combination-point-result-v1",
        "experiment_id": EXP.name,
        "created_at_local": now(),
        "point_id": point_id,
        "changes": changes,
        "n2": {"raw_path": n2_path.relative_to(REPO).as_posix(), "raw_sha256": sha256(n2_path), "classification": n2_class, "evidence": candidate_n2_case},
        "n3": {"raw_path": n3_path.relative_to(REPO).as_posix(), "raw_sha256": sha256(n3_path), "classification": n3_class, "evidence": candidate_n3_case},
        "references": reference_summaries,
        "comparisons": {
            "n2": {"candidate": case_summary(candidate_n2_case, is_n2=True), "references": {name: case_summary(reference_evidence[name]["0011"], is_n2=True) for name in REFERENCE_CASES}},
            "n3": {"candidate": case_summary(candidate_n3_case, is_n2=False), "references": {name: case_summary(reference_evidence[name]["0111"], is_n2=False) for name in REFERENCE_CASES}},
            "comparison_axis": "candidate L3=2.0/BJ2=2.2 versus canonical, L3-only and BJ2-only raw references",
        },
        "candidate_class": outcome_class,
        "candidate_label": labels[outcome_class],
        "raw_authority": True,
        "screening_classification_performed": True,
        "scientific_review_performed": False,
        "phase_navigation_only": True,
        "not_sfq_count": True,
        "notes": [
            "complete response requires BJ1->BJ2->QBOUT->JTL1..6->terminal temporal support",
            "reference comparisons are descriptive raw-derived diagnostics, not parameter ranking",
            "CONTROL uses only registered pre-FINAL history windows; FINAL/Tail rollback is separate",
            "phase/peak/area values are not SFQ counts",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--point-id", required=True)
    parser.add_argument("--changes", required=True)
    parser.add_argument("--n2", type=Path, required=True)
    parser.add_argument("--n3", type=Path, required=True)
    args = parser.parse_args()
    result = analyze_pair(args.point_id, json.loads(args.changes), args.n2.resolve(), args.n3.resolve())
    output = EXP / "screening/results" / f"{args.point_id}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "point_id": args.point_id, "candidate_class": result["candidate_class"], "candidate_label": result["candidate_label"], "n2": result["n2"]["classification"]["classification"], "n3": result["n3"]["classification"]["classification"], "control_n2": result["n2"]["classification"]["control_status"], "control_n3": result["n3"]["classification"]["control_status"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
