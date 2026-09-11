#!/usr/bin/env python3
"""Raw-first multi-stream screening analysis for one full closed-loop case/pair."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
BASELINE_RAW = EXP / "references/baseline_rj2p12/ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_0111/raw.csv"
THRESHOLDS = (0.5, 1.5, 2.5, 3.5, 4.5)
CONTROL_V_THRESHOLD = 2.0e-4
CONTROL_I_THRESHOLD = 2.0e-5
TERMINAL_PEAK_THRESHOLD = 2.0e-4
MIN_PEAK_GAP_PS = 2.5
PHI0 = 2.067833848e-15
REQUIRED = ("I(B_JSL8)", "V(QBIN)", "V(COMMON_SL)", "I(LIN|XBQ1)", "I(L1|XBQ1)", "I(L2|XBQ1)", "P(BJ1|XBQ1)", "V(BJ1|XBQ1)", "I(BJ1|XBQ1)", "P(BJ2|XBQ1)", "V(BJ2|XBQ1)", "I(BJ2|XBQ1)", "V(QBOUT)", "V(JTL1_OUT)", "V(JTL2_OUT)", "V(JTL3_OUT)", "V(JTL4_OUT)", "V(JTL5_OUT)", "V(JTL6_OUT)", "I(R_TERM)") + tuple(f"P(B01|XJTL1_{stage})" for stage in range(1, 7))

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
        raise RuntimeError(f"missing screening labels in {path}: {missing}")
    if len(trace.time) != 1999 or trace.time[0] != 0.0 or trace.time[-1] != 1.999e-10:
        raise RuntimeError(f"unexpected raw time grid: {path}")
    if any(right <= left for left, right in zip(trace.time, trace.time[1:])):
        raise RuntimeError(f"non-increasing raw time grid: {path}")
    return trace


def indices(trace: RawTrace, start_ps: float, end_ps: float) -> list[int]:
    return [index for index, time in enumerate(trace.time) if start_ps <= time * 1.0e12 < end_ps]


def integral(times_s: tuple[float, ...], values: list[float], selected: list[int]) -> float:
    total = 0.0
    for left, right in zip(selected, selected[1:]):
        if right != left + 1:
            continue
        total += 0.5 * (values[left] + values[right]) * (times_s[right] - times_s[left])
    return total


def phase_info(trace: RawTrace, label: str) -> dict[str, Any]:
    values = tuple(trace.column(label))
    unwrapped = tuple(continuous_unwrap(values))
    base = next(index for index, time in enumerate(trace.time) if time * 1.0e12 >= 101.0)
    threshold_times: dict[str, float | None] = {}
    for threshold in THRESHOLDS:
        threshold_times[f"{threshold:g}"] = next((trace.time[index] * 1.0e12 for index in range(base, len(unwrapped)) if (unwrapped[index] - unwrapped[base]) / (2.0 * math.pi) >= threshold), None)
    return {"label": label, "raw_unit": "radians", "baseline_time_ps": trace.time[base] * 1.0e12, "threshold_navigation_times_ps": threshold_times, "max_relative_turns": max((value - unwrapped[base]) / (2.0 * math.pi) for value in unwrapped[base:]), "final_relative_turns": (unwrapped[-1] - unwrapped[base]) / (2.0 * math.pi), "semantic_role": "PHASE_NAVIGATION_ONLY; not an SFQ count"}


def local_positive_peaks(trace: RawTrace, label: str, threshold: float = TERMINAL_PEAK_THRESHOLD, minimum_gap_ps: float = MIN_PEAK_GAP_PS) -> list[dict[str, float]]:
    values = list(trace.column(label))
    times = [time * 1.0e12 for time in trace.time]
    candidates = [index for index in range(1, len(values) - 1) if 110.0 <= times[index] < 200.0 and values[index] >= threshold and values[index] >= values[index - 1] and values[index] > values[index + 1]]
    selected: list[int] = []
    for index in candidates:
        if not selected or times[index] - times[selected[-1]] > minimum_gap_ps:
            selected.append(index)
        elif values[index] > values[selected[-1]]:
            selected[-1] = index
    return [{"peak_time_ps": times[index], "peak_value_V": values[index], "sample_index": index} for index in selected]


def terminal_pulses(trace: RawTrace) -> dict[str, Any]:
    values = list(trace.column("V(JTL6_OUT)"))
    times = [time * 1.0e12 for time in trace.time]
    peaks = local_positive_peaks(trace, "V(JTL6_OUT)")
    peak_indices = [int(peak["sample_index"]) for peak in peaks]
    if not peak_indices:
        return {"pulse_count": 0, "pulses": [], "total_area_V_s": integral(trace.time, values, indices(trace, 110.0, 200.0)), "total_area_over_phi0": integral(trace.time, values, indices(trace, 110.0, 200.0)) / PHI0, "locator": {"threshold_V": TERMINAL_PEAK_THRESHOLD, "minimum_gap_ps": MIN_PEAK_GAP_PS}, "not_event_count": True}
    valleys = [min(range(left, right + 1), key=lambda index: values[index]) for left, right in zip(peak_indices, peak_indices[1:])]
    bounds = [indices(trace, 110.0, 200.0)[0], *valleys, indices(trace, 110.0, 200.0)[-1]]
    pulses: list[dict[str, Any]] = []
    for ordinal, peak in enumerate(peak_indices):
        left, right = bounds[ordinal], bounds[ordinal + 1]
        selected = list(range(left, right + 1))
        area = integral(trace.time, values, selected)
        pulses.append({"pulse_index": ordinal + 1, "peak_time_ps": times[peak], "peak_value_V": values[peak], "left_valley_boundary_ps": times[left], "right_valley_boundary_ps": times[right], "signed_area_V_s": area, "area_over_phi0": area / PHI0, "sample_count": len(selected)})
    return {"pulse_count": len(pulses), "pulses": pulses, "peak_separation_ps": [pulses[index + 1]["peak_time_ps"] - pulses[index]["peak_time_ps"] for index in range(len(pulses) - 1)], "total_area_V_s": integral(trace.time, values, indices(trace, 110.0, 200.0)), "total_area_over_phi0": integral(trace.time, values, indices(trace, 110.0, 200.0)) / PHI0, "locator": {"threshold_V": TERMINAL_PEAK_THRESHOLD, "minimum_gap_ps": MIN_PEAK_GAP_PS}, "not_event_count": True}


def match_peaks_after(peaks: list[dict[str, float]], source_times: list[float]) -> list[dict[str, float]]:
    """Navigate one downstream lobe after each upstream phase landmark.

    A full raw trace can contain small QBOUT lobes between two front-end
    responses.  Positional indexing would therefore associate such a lobe
    with the next response.  The association below is only temporal
    navigation: it does not turn a lobe into an SFQ event count.
    """
    matched: list[dict[str, float]] = []
    next_peak = 0
    for source_time in source_times:
        while next_peak < len(peaks) and peaks[next_peak]["peak_time_ps"] <= source_time:
            next_peak += 1
        if next_peak >= len(peaks):
            break
        matched.append(peaks[next_peak])
        next_peak += 1
    return matched


def control_info(trace: RawTrace) -> dict[str, Any]:
    selected = indices(trace, 70.0, 110.0)
    stage = list(trace.column("V(JTL6_OUT)"))
    terminal = list(trace.column("I(R_TERM)"))
    phase_bj1 = phase_info(trace, "P(BJ1|XBQ1)")
    phase_bj2 = phase_info(trace, "P(BJ2|XBQ1)")
    phase_delta_bj1 = abs(phase_bj1["final_relative_turns"] - phase_bj1["max_relative_turns"])
    phase_delta_bj2 = abs(phase_bj2["final_relative_turns"] - phase_bj2["max_relative_turns"])
    contaminated = max((abs(stage[index]) for index in selected), default=0.0) >= CONTROL_V_THRESHOLD or max((abs(terminal[index]) for index in selected), default=0.0) >= CONTROL_I_THRESHOLD or phase_delta_bj1 > 0.5 or phase_delta_bj2 > 0.5
    return {"status": "CONTROL_CONTAMINATED" if contaminated else "CLEAN", "window_ps": [70.0, 110.0], "max_abs_JTL6_V": max((abs(stage[index]) for index in selected), default=0.0), "max_abs_terminal_A": max((abs(terminal[index]) for index in selected), default=0.0), "BJ1_max_minus_final_turns": phase_delta_bj1, "BJ2_max_minus_final_turns": phase_delta_bj2, "thresholds": {"JTL6_V": CONTROL_V_THRESHOLD, "terminal_A": CONTROL_I_THRESHOLD, "rollback_turns": 0.5}, "guardrail_only": True}


def case_evidence(trace: RawTrace) -> dict[str, Any]:
    phase_labels = {"BJ1": "P(BJ1|XBQ1)", "BJ2": "P(BJ2|XBQ1)", **{f"JTL{stage}": f"P(B01|XJTL1_{stage})" for stage in range(1, 7)}}
    phase = {name: phase_info(trace, label) for name, label in phase_labels.items()}
    phase_counts = {name: sum(value is not None for value in item["threshold_navigation_times_ps"].values()) for name, item in phase.items()}
    phase_count = min(phase_counts.values())
    qbout_peaks = local_positive_peaks(trace, "V(QBOUT)")
    terminal = terminal_pulses(trace)
    source_times = [
        phase["BJ2"]["threshold_navigation_times_ps"][f"{THRESHOLDS[index]:g}"]
        for index in range(phase_count)
    ]
    jtl6_times = [
        phase["JTL6"]["threshold_navigation_times_ps"][f"{THRESHOLDS[index]:g}"]
        for index in range(phase_count)
    ]
    matched_qbout = match_peaks_after(qbout_peaks, source_times)
    matched_terminal = match_peaks_after(terminal["pulses"], jtl6_times)
    terminal["matched_candidate_pulses"] = matched_terminal
    terminal["matched_candidate_count"] = len(matched_terminal)
    complete_count = min(phase_count, len(matched_qbout), len(matched_terminal))
    ordered: dict[str, bool] = {}
    for ordinal in range(1, complete_count + 1):
        threshold = f"{THRESHOLDS[ordinal - 1]:g}"
        chain = [phase["BJ1"]["threshold_navigation_times_ps"].get(threshold), phase["BJ2"]["threshold_navigation_times_ps"].get(threshold), matched_qbout[ordinal - 1]["peak_time_ps"] if len(matched_qbout) >= ordinal else None]
        chain.extend(phase[f"JTL{stage}"]["threshold_navigation_times_ps"].get(threshold) for stage in range(1, 7))
        chain.append(matched_terminal[ordinal - 1]["peak_time_ps"] if len(matched_terminal) >= ordinal else None)
        ordered[str(ordinal)] = all(value is not None for value in chain) and all(left < right for left, right in zip(chain, chain[1:]))
    final_phase_window = indices(trace, 121.0, 130.0)
    l1 = list(trace.column("I(L1|XBQ1)"))
    l2 = list(trace.column("I(L2|XBQ1)"))
    vdiff = [a - b for a, b in zip(trace.column("V(BJ1|XBQ1)"), trace.column("V(BJ2|XBQ1)"))]
    l1_zero = next((trace.time[index] * 1e12 for index in final_phase_window if l1[index] == 0.0 or (index > final_phase_window[0] and l1[index - 1] * l1[index] < 0.0)), None)
    return {"phase_navigation": phase, "phase_count_by_track": phase_counts, "phase_supported_count": phase_count, "qbout_raw_peak_navigation": qbout_peaks, "qbout_matched_candidate_navigation": matched_qbout, "terminal": terminal, "complete_response_candidate_count": complete_count, "ordered_chain_by_candidate": ordered, "control": control_info(trace), "internal_reset": {"window_ps": [121.0, 130.0], "peak_I_L1_A": max((l1[index] for index in final_phase_window), default=None), "min_I_L1_A": min((l1[index] for index in final_phase_window), default=None), "first_I_L1_zero_or_sign_change_ps": l1_zero, "peak_I_L2_A": max((l2[index] for index in final_phase_window), default=None), "peak_BJ1_minus_BJ2_voltage_V": max((vdiff[index] for index in final_phase_window), default=None), "min_BJ1_minus_BJ2_voltage_V": min((vdiff[index] for index in final_phase_window), default=None), "integral_121_126_V_s": integral(trace.time, vdiff, indices(trace, 121.0, 126.0)), "integral_118_121_V_s": integral(trace.time, vdiff, indices(trace, 118.0, 121.0)), "integral_121_124_V_s": integral(trace.time, vdiff, indices(trace, 121.0, 124.0)), "integral_124_128_V_s": integral(trace.time, vdiff, indices(trace, 124.0, 128.0)), "BJ1_final_relative_turns": phase["BJ1"]["final_relative_turns"], "BJ1_max_relative_turns": phase["BJ1"]["max_relative_turns"], "BJ2_final_relative_turns": phase["BJ2"]["final_relative_turns"], "BJ2_max_relative_turns": phase["BJ2"]["max_relative_turns"]}, "not_sfq_count": True}


def fourth_suppression(case: dict[str, Any], baseline: dict[str, Any] | None) -> tuple[bool, list[str]]:
    """Return bounded fourth-response weakening diagnostics against baseline."""
    notes: list[str] = []
    count = case["complete_response_candidate_count"]
    first_three_ordered = all(case["ordered_chain_by_candidate"].get(str(index), False) for index in (1, 2, 3))
    weakened = count >= 3 and first_three_ordered and not case["ordered_chain_by_candidate"].get("4", False)
    if weakened:
        notes.append("fourth full ordered chain is absent after three ordered candidates")
    if baseline is None:
        return weakened, notes
    current_phase = case["phase_navigation"]
    base_phase = baseline["phase_navigation"]
    for track in ("BJ1", "BJ2", "JTL1", "JTL6"):
        current = current_phase[track]["threshold_navigation_times_ps"].get("3.5")
        reference = base_phase[track]["threshold_navigation_times_ps"].get("3.5")
        if current is None:
            if track in {"BJ1", "BJ2"} and count >= 3 and first_three_ordered:
                weakened = True
            notes.append(f"{track}_4_navigation_ps=None")
        else:
            notes.append(f"{track}_4_navigation_ps={current:.6g}")
            if reference is not None and current - reference > 2.0:
                weakened = True
                notes.append(f"{track}_4_delay_ps={current - reference:.6g}")
    current_pulses = case["terminal"].get("matched_candidate_pulses", case["terminal"].get("pulses", []))
    base_pulses = baseline["terminal"].get("matched_candidate_pulses", baseline["terminal"].get("pulses", []))
    if len(current_pulses) < 4:
        if count >= 3 and first_three_ordered:
            weakened = True
        notes.append("terminal_4_navigation_ps=None")
    elif len(base_pulses) >= 4:
        ratio = abs(current_pulses[3]["signed_area_V_s"]) / max(abs(base_pulses[3]["signed_area_V_s"]), 1e-30)
        delay = current_pulses[3]["peak_time_ps"] - base_pulses[3]["peak_time_ps"]
        notes.extend([f"terminal_fourth_area_ratio={ratio:.6g}", f"terminal_fourth_delay_ps={delay:.6g}"])
        if ratio < 0.8 or delay > 2.0:
            weakened = True
    if not case["ordered_chain_by_candidate"].get("4", False) and count >= 3 and first_three_ordered:
        weakened = True
    return weakened, notes


def case_classification(case: dict[str, Any], baseline: dict[str, Any] | None, is_n2: bool) -> dict[str, Any]:
    control = case["control"]
    count = case["complete_response_candidate_count"]
    if control["status"] != "CLEAN":
        return {"classification": "CONTROL_CONTAMINATED", "control_status": control["status"], "evidence_status": "INCONCLUSIVE"}
    if is_n2:
        classification = "N2_2_COMPLETE" if count == 2 and case["ordered_chain_by_candidate"].get("2") else "N2_NOT_2"
        return {"classification": classification, "control_status": "CLEAN", "evidence_status": "BOUNDED_RESULT" if classification == "N2_2_COMPLETE" else "INCONCLUSIVE"}
    if count == 3 and all(case["ordered_chain_by_candidate"].get(str(index), False) for index in (1, 2, 3)) and not case["ordered_chain_by_candidate"].get("4", False):
        return {"classification": "N3_3_COMPLETE", "control_status": "CLEAN", "evidence_status": "BOUNDED_RESULT"}
    weakened, notes = fourth_suppression(case, baseline)
    if count >= 4 and case["ordered_chain_by_candidate"].get("4", False):
        return {"classification": "N3_4_COMPLETE", "control_status": "CLEAN", "evidence_status": "BOUNDED_RESULT", "fourth_weakened_relative_to_baseline": weakened, "notes": notes}
    if count >= 3:
        return {"classification": "N3_MULTIPLICITY_AMBIGUOUS", "control_status": "CLEAN", "evidence_status": "INCONCLUSIVE", "fourth_weakened_relative_to_baseline": weakened, "notes": notes}
    return {"classification": "N3_OTHER_OR_INCOMPLETE", "control_status": "CLEAN", "evidence_status": "INCONCLUSIVE"}


def analyze_pair(point_id_value: str, parameter: str, value: float, n2_path: Path, n3_path: Path) -> dict[str, Any]:
    n2_trace, n3_trace = load(n2_path), load(n3_path)
    baseline_trace = load(BASELINE_RAW)
    n2_case, n3_case = case_evidence(n2_trace), case_evidence(n3_trace)
    baseline_case = case_evidence(baseline_trace)
    n2_class, n3_class = case_classification(n2_case, None, True), case_classification(n3_case, baseline_case, False)
    if n2_class["classification"] == "N2_2_COMPLETE" and n3_class["classification"] == "N3_3_COMPLETE":
        point_class = "S"
    elif n2_class["classification"] == "N2_2_COMPLETE" and n3_class["classification"] in {"N3_4_COMPLETE", "N3_MULTIPLICITY_AMBIGUOUS"}:
        point_class = "A" if n3_class.get("fourth_weakened_relative_to_baseline") else "B"
    elif n2_class["classification"] != "N2_2_COMPLETE" and n3_class["classification"] in {"N3_3_COMPLETE", "N3_4_COMPLETE"}:
        point_class = "C"
    elif n2_class["classification"] == "CONTROL_CONTAMINATED" or n3_class["classification"] == "CONTROL_CONTAMINATED":
        point_class = "D"
    else:
        point_class = "D" if n3_case["complete_response_candidate_count"] > 4 else "B"
    return {"schema": "bvm-full-closed-loop-qb-screening-point-result-v1", "experiment_id": EXP.name, "created_at_local": now(), "point_id": point_id_value, "parameter": parameter, "value": value, "n2": {"raw_path": n2_path.relative_to(REPO).as_posix(), "raw_sha256": sha256(n2_path), "classification": n2_class, "evidence": n2_case}, "n3": {"raw_path": n3_path.relative_to(REPO).as_posix(), "raw_sha256": sha256(n3_path), "classification": n3_class, "evidence": n3_case}, "candidate_class": point_class, "candidate_label": {"S": "DIRECT_2_TO_3_CANDIDATE", "A": "PROMISING_SELECTIVE_SUPPRESSION", "B": "NEUTRAL_2_TO_4", "C": "GLOBAL_WEAKENING", "D": "WORSE_OR_UNSTABLE"}[point_class], "raw_authority": True, "scientific_analysis_performed": True, "phase_navigation_only": True, "notes": ["complete_response candidates require front-end phase navigation, QBOUT raw lobe navigation, ordered JTL phase progression and terminal evidence", "automatic cluster labels are auxiliary", "no phase/area/activity value is an SFQ count"]}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--point-id", required=True)
    parser.add_argument("--parameter", required=True)
    parser.add_argument("--value", type=float, required=True)
    parser.add_argument("--n2", type=Path, required=True)
    parser.add_argument("--n3", type=Path, required=True)
    args = parser.parse_args()
    result = analyze_pair(args.point_id, args.parameter, args.value, args.n2.resolve(), args.n3.resolve())
    output = EXP / "screening/results" / f"{args.point_id}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "point_id": args.point_id, "candidate_class": result["candidate_class"], "n2": result["n2"]["classification"]["classification"], "n3": result["n3"]["classification"]["classification"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
