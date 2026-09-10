#!/usr/bin/env python3
"""Raw, deck and registered mechanical QA for the staged RJ2 search."""

from __future__ import annotations

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
sys.path.insert(0, str(EXP / "analysis"))
from prepare_experiment import (  # noqa: E402
    AUTH as AUTHORITY_SOURCE_EXPERIMENT,
    BQ400,
    BQ_RJ2,
    CONTROL_KINDS,
    FIXED,
    MASKS,
    NEW_RUNS,
    REUSE_RUNS,
    RJ2_VALUES,
    RUN_TO_RJ2,
    RUN_TO_MASK,
    build_deck,
    control_line,
    normalized_deck,
    pre_read_controls,
)
sys.path.insert(0, str(REPO / "scripts"))
from bvmtools.phase import continuous_unwrap, window_indices  # noqa: E402
from bvmtools.raw import read_csv  # noqa: E402


OPTIONAL_UNKNOWN = {"V(IB|XBQ1)"}
REGISTERED_NEW_RUNS = tuple(NEW_RUNS)
ALL_CASES = tuple(REUSE_RUNS) + REGISTERED_NEW_RUNS
CASE_L2 = {run_id: 2.0 for run_id in ALL_CASES}
CASE_RJ2 = {**{run_id: 10.0 for run_id in REUSE_RUNS}, **RUN_TO_RJ2}
ORIGINS = OrderedDict(
    (
        ("CONTROL_ORIGIN", {"window": (70e-12, 110e-12), "baseline": (61e-12, 70e-12)}),
        ("FINAL_ORIGIN", {"window": (110e-12, 200e-12), "baseline": (101e-12, 110e-12)}),
    )
)
PRE_SWITCH_WINDOW = (110e-12, 114.5e-12)
DIFF_START = 110e-12
DIFF_TO_121 = 121e-12
DIFF_TO_140 = 140e-12
BJ1_HALF_TURNS = 0.5
BJ2_REGEN_TURNS = 0.9
SECOND_THRESHOLD_TURNS = 1.5
SECOND_SURGE_MIN_SEPARATION_PS = 1.0
RATIO_AREA_TOLERANCE_A_S = 1e-18
RATIO_CANCELLATION_FRACTION = 0.01


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def raw_path(case_id: str) -> Path:
    root = "runs" if case_id in REGISTERED_NEW_RUNS else "references/reused"
    return EXP / root / case_id / "raw.csv"


def deck_path(case_id: str) -> Path:
    root = "runs" if case_id in REGISTERED_NEW_RUNS else "references/reused"
    return EXP / root / case_id / "deck.cir"


def source_experiment(case_id: str) -> str:
    return str(EXP.relative_to(REPO)) if case_id in NEW_RUNS else str(AUTHORITY_SOURCE_EXPERIMENT.relative_to(REPO))


def source_run(case_id: str) -> str:
    return f"runs/{case_id}"


def expected_probes() -> set[str]:
    probes: set[str] = set()
    for instance in range(1, 5):
        probes.update(f"I(I_{kind}{instance})" for kind in CONTROL_KINDS)
        header = f"XBVM{instance}"
        for jj in ("B_JM1", "B_JM2", "B_JS1", "B_JS2"):
            probes.update(f"{kind}({jj}|{header})" for kind in ("P", "V", "I"))
        for branch in ("L_M1", "L_M2", "L_M3", "L_PM", "R_JM1", "L_S1", "L_S2", "R_S", "L_S3", "R_SE", "L_PSE", "L_PSL", "R_SL", "L_SL"):
            probes.update(f"{kind}({branch}|{header})" for kind in ("I", "V"))
    probes.add("V(COMMON_SL)")
    for index in range(1, 9):
        probes.update((f"P(B_JSL{index})", f"V(B_JSL{index})", f"I(B_JSL{index})"))
    probes.update(("V(QBIN)", "V(QBOUT)", "I(LIN|XBQ1)", "V(LIN|XBQ1)"))
    for jj in ("BJS", "BJ1"):
        probes.update((f"P({jj}|XBQ1)", f"V({jj}|XBQ1)", f"I({jj}|XBQ1)"))
    for branch in ("RJ1", "L1"):
        probes.update((f"I({branch}|XBQ1)", f"V({branch}|XBQ1)"))
    probes.update(("I(IB|XBQ1)", "V(IB|XBQ1)", "I(L2|XBQ1)", "V(L2|XBQ1)"))
    probes.update(("P(BJ2|XBQ1)", "V(BJ2|XBQ1)", "I(BJ2|XBQ1)"))
    probes.update(("I(RJ2|XBQ1)", "V(RJ2|XBQ1)", "I(L3|XBQ1)", "V(L3|XBQ1)"))
    for stage in range(1, 7):
        header = f"XJTL1_{stage}"
        for jj in ("B01", "B02"):
            probes.update((f"P({jj}|{header})", f"V({jj}|{header})", f"I({jj}|{header})"))
        probes.add(f"V(JTL{stage}_OUT)")
    probes.add("I(R_TERM)")
    return probes


def head_relation(preflight_head: str) -> dict[str, Any]:
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()
    if head == preflight_head:
        return {"status": "PASS", "head": head, "preflight_head": preflight_head, "relation": "EXACT"}
    changed = set(subprocess.check_output(["git", "diff", "--name-only", f"{preflight_head}..{head}"], cwd=REPO, text=True).splitlines())
    allowed = {str(EXP.relative_to(REPO) / "PREFLIGHT.md"), str(EXP.relative_to(REPO) / "analysis/preflight.json")}
    distance = int(subprocess.check_output(["git", "rev-list", "--count", f"{preflight_head}..{head}"], cwd=REPO, text=True).strip())
    status = "PASS" if distance == 1 and changed == allowed else "FAIL"
    return {"status": status, "head": head, "preflight_head": preflight_head, "relation": "PREFLIGHT_ONLY_SEAL_COMMIT" if status == "PASS" else "UNEXPECTED", "changed_paths": sorted(changed), "commit_distance": distance}


def trapezoid(times: tuple[float, ...], values: tuple[float, ...]) -> float:
    return sum((values[index] + values[index + 1]) * 0.5 * (times[index + 1] - times[index]) for index in range(len(values) - 1))


def selected(trace: Any, label: str, window: tuple[float, float]) -> tuple[tuple[int, ...], tuple[float, ...], tuple[float, ...]]:
    indexes = window_indices(trace.time, *window)
    values = tuple(float(value) for value in trace.column(label))
    return indexes, tuple(trace.time[index] for index in indexes), tuple(values[index] for index in indexes)


def area(trace: Any, label: str, window: tuple[float, float]) -> float | None:
    _indexes, times, values = selected(trace, label, window)
    return trapezoid(times, values) if len(times) >= 2 else None


def extrema(trace: Any, label: str, window: tuple[float, float]) -> dict[str, float | None]:
    _indexes, _times, values = selected(trace, label, window)
    if not values:
        return {"max": None, "min": None, "max_abs": None}
    return {"max": max(values), "min": min(values), "max_abs": max(abs(value) for value in values)}


def local_maxima(times: tuple[float, ...], values: tuple[float, ...]) -> list[dict[str, float]]:
    return [
        {"time_ps": times[index] * 1e12, "value_A": values[index]}
        for index in range(1, len(values) - 1)
        if values[index] > values[index - 1] and values[index] > values[index + 1]
    ]


def first_threshold_index(relative: tuple[float, ...], indexes: tuple[int, ...], threshold: float) -> int | None:
    return next((index for index, value in zip(indexes, relative) if value >= threshold), None)


def phase_origin_diagnostic(trace: Any, label: str, origin_name: str) -> dict[str, Any]:
    spec = ORIGINS[origin_name]
    unwrapped = continuous_unwrap(tuple(trace.column(label)))
    baseline_indexes = window_indices(trace.time, *spec["baseline"])
    origin_indexes = window_indices(trace.time, *spec["window"])
    if not baseline_indexes or not origin_indexes:
        return {"status": "UNKNOWN", "reason": "registered phase/baseline window has no samples", "not_event_time": True, "not_event_count": True}
    baseline = unwrapped[baseline_indexes[0]]
    relative = tuple((unwrapped[index] - baseline) / (2.0 * math.pi) for index in origin_indexes)
    half_index = first_threshold_index(relative, origin_indexes, BJ1_HALF_TURNS)
    regen_index = first_threshold_index(relative, origin_indexes, BJ2_REGEN_TURNS)
    second_index = first_threshold_index(relative, origin_indexes, SECOND_THRESHOLD_TURNS)
    max_position = max(range(len(relative)), key=relative.__getitem__)
    max_value = relative[max_position]
    rollback = any(value <= max_value - 0.25 for value in relative[max_position + 1:])
    return {
        "status": "DERIVED",
        "label": label,
        "origin": origin_name,
        "raw_unit": "rad",
        "display_unit": "turns",
        "conversion": "continuous_unwrap(raw_rad)/(2*pi)",
        "baseline_window_ps": [spec["baseline"][0] * 1e12, spec["baseline"][1] * 1e12],
        "origin_window_ps": [spec["window"][0] * 1e12, spec["window"][1] * 1e12],
        "baseline_reference_time_ps": trace.time[baseline_indexes[0]] * 1e12,
        "first_half_turn_timing_diagnostic_ps": trace.time[half_index] * 1e12 if half_index is not None else None,
        "first_half_turn_sample_index": half_index,
        "first_0p9_turn_timing_diagnostic_ps": trace.time[regen_index] * 1e12 if regen_index is not None else None,
        "first_0p9_turn_sample_index": regen_index,
        "first_1p5_turn_timing_diagnostic_ps": trace.time[second_index] * 1e12 if second_index is not None else None,
        "first_1p5_turn_sample_index": second_index,
        "max_continuous_relative_phase_turns": max(relative),
        "min_continuous_relative_phase_turns": min(relative),
        "final_continuous_relative_phase_turns": relative[-1],
        "time_of_max_forward_phase_ps": trace.time[origin_indexes[max_position]] * 1e12,
        "additional_forward_excursion_candidate": max_value >= SECOND_THRESHOLD_TURNS,
        "rollback_candidate": rollback,
        "diagnostic_label": "MECHANICAL_DIAGNOSTIC_ONLY",
        "second_threshold_label": "MECHANICAL_THRESHOLD_ONLY",
        "not_event_time": True,
        "not_event_count": True,
        "scientific_interpretation_performed": False,
    }


def zero_crossings(trace: Any, label: str, window: tuple[float, float]) -> dict[str, Any]:
    indexes = window_indices(trace.time, *window)
    values = tuple(float(value) for value in trace.column(label))
    exact: list[float] = []
    transitions: list[dict[str, Any]] = []
    for left, right in zip(indexes, indexes[1:]):
        a, b = values[left], values[right]
        if a == 0.0:
            exact.append(trace.time[left] * 1e12)
        if (a < 0.0 < b) or (a > 0.0 > b):
            transitions.append({
                "time_ps": trace.time[right] * 1e12,
                "direction": "negative_to_positive" if a < 0.0 < b else "positive_to_negative",
                "interpolation": False,
            })
    if indexes and values[indexes[-1]] == 0.0:
        exact.append(trace.time[indexes[-1]] * 1e12)
    return {"status": "DERIVED", "label": label, "window_ps": [window[0] * 1e12, window[1] * 1e12], "exact_zero_sample_times_ps": exact, "sign_transition_stored_sample_times": transitions, "interpolation": False}


def jtl_progression(trace: Any, origin_name: str) -> dict[str, Any]:
    spec = ORIGINS[origin_name]
    baseline_indexes = window_indices(trace.time, *spec["baseline"])
    origin_indexes = window_indices(trace.time, *spec["window"])
    first_times: dict[str, float | None] = OrderedDict()
    second_times: dict[str, float | None] = OrderedDict()
    if not baseline_indexes or not origin_indexes:
        return {"status": "UNKNOWN", "reason": "registered JTL window has no samples", "candidate_label": "MECHANICAL_CANDIDATE_ONLY"}
    for stage in range(1, 7):
        raw = tuple(trace.column(f"P(B01|XJTL1_{stage})"))
        unwrapped = continuous_unwrap(raw)
        baseline = unwrapped[baseline_indexes[0]]
        relative = tuple((unwrapped[index] - baseline) / (2.0 * math.pi) for index in origin_indexes)
        first = first_threshold_index(relative, origin_indexes, 0.5)
        second = first_threshold_index(relative, origin_indexes, 1.5)
        first_times[f"JTL{stage}"] = trace.time[first] * 1e12 if first is not None else None
        second_times[f"JTL{stage}"] = trace.time[second] * 1e12 if second is not None else None

    def ordered(values: dict[str, float | None]) -> bool:
        return all(value is not None for value in values.values()) and all(values[f"JTL{index}"] < values[f"JTL{index + 1}"] for index in range(1, 6))

    first_candidate = ordered(first_times)
    second_candidate = ordered(second_times)
    return {
        "status": "DERIVED",
        "origin": origin_name,
        "signal": "P(B01|XJTL1_stage)",
        "raw_unit": "rad",
        "display_unit": "turns",
        "conversion": "continuous_unwrap(raw_rad)/(2*pi)",
        "window_ps": [spec["window"][0] * 1e12, spec["window"][1] * 1e12],
        "first_candidate_threshold_turns": 0.5,
        "second_candidate_threshold_turns": 1.5,
        "first_stage_half_turn_timing_ps": first_times,
        "second_stage_threshold_timing_ps": second_times,
        "first_relevant_progression_start_ps": first_times["JTL1"],
        "first_relevant_progression_terminal_ps": first_times["JTL6"],
        "second_progression_start_ps": second_times["JTL1"],
        "second_progression_terminal_ps": second_times["JTL6"],
        "complete_progression_candidate": first_candidate,
        "second_separated_progression_candidate": second_candidate,
        "candidate_label": "MECHANICAL_CANDIDATE_ONLY",
        "not_event_count": True,
        "not_sfq_count": True,
    }


def signed_components(trace: Any, label: str, window: tuple[float, float]) -> dict[str, Any]:
    _indexes, times, values = selected(trace, label, window)
    return {
        "positive_V_s": trapezoid(times, tuple(max(value, 0.0) for value in values)) if len(times) >= 2 else None,
        "negative_V_s": trapezoid(times, tuple(min(value, 0.0) for value in values)) if len(times) >= 2 else None,
        "window_ps": [window[0] * 1e12, window[1] * 1e12],
        "formula": "trapezoid(actual stored grid, max(V,0) or min(V,0))",
        "status": "DERIVED" if len(times) >= 2 else "UNKNOWN",
    }


def origin_summary(trace: Any, origin_name: str) -> dict[str, Any]:
    window = ORIGINS[origin_name]["window"]
    l2_indexes, l2_times, l2_values = selected(trace, "I(L2|XBQ1)", window)
    maxima = local_maxima(l2_times, l2_values)
    if maxima:
        first_surge = maxima[0]
    elif l2_values:
        position = max(range(len(l2_values)), key=l2_values.__getitem__)
        first_surge = {"time_ps": l2_times[position] * 1e12, "value_A": l2_values[position], "method": "global_max_fallback"}
    else:
        first_surge = None
    receiver = {
        label: extrema(trace, label, window)
        for label in ("I(L1|XBQ1)", "I(IB|XBQ1)", "I(L2|XBQ1)", "V(L2|XBQ1)", "I(RJ1|XBQ1)", "V(RJ1|XBQ1)", "I(RJ2|XBQ1)", "V(RJ2|XBQ1)", "I(L3|XBQ1)", "V(L3|XBQ1)", "V(BJ2|XBQ1)", "V(QBOUT)")
    }


    receiver["I(L1|XBQ1)"]["zero_crossing"] = zero_crossings(trace, "I(L1|XBQ1)", window)
    voltage_indexes, voltage_times, voltage = selected(trace, "V(RJ1|XBQ1)", window)
    current = tuple(float(trace.column("I(RJ1|XBQ1)")[index]) for index in voltage_indexes)
    energy = trapezoid(voltage_times, tuple(v * i for v, i in zip(voltage, current))) if len(voltage_times) >= 2 else None
    source = {
        "I(B_JSL8)": extrema(trace, "I(B_JSL8)", window),
        "I(LIN|XBQ1)": extrema(trace, "I(LIN|XBQ1)", window),
        "V(QBIN)": extrema(trace, "V(QBIN)", window),
        "V(COMMON_SL)": extrema(trace, "V(COMMON_SL)", window),
        "signed_areas_A_s": {"I(B_JSL8)": area(trace, "I(B_JSL8)", window), "I(LIN|XBQ1)": area(trace, "I(LIN|XBQ1)", window)},
    }
    return {
        "window_ps": [window[0] * 1e12, window[1] * 1e12],
        "phase_diagnostics": {"BJ1": phase_origin_diagnostic(trace, "P(BJ1|XBQ1)", origin_name), "BJ2": phase_origin_diagnostic(trace, "P(BJ2|XBQ1)", origin_name)},
        "receiver_diagnostics": {
            "descriptives": receiver,
            "BJ1_voltage_area": signed_components(trace, "V(BJ1|XBQ1)", window),
            "RJ1_dissipated_energy": {"value_J": energy, "formula": "trapezoid(actual stored grid, V(RJ1|XBQ1)*I(RJ1|XBQ1))", "orientation": "as emitted; no sign correction", "window_ps": [window[0] * 1e12, window[1] * 1e12], "status": "DERIVED" if energy is not None else "UNKNOWN"},
            "L2_principal_first_surge": {"value": first_surge, "local_maxima": maxima, "label": "MECHANICAL_DIAGNOSTIC_ONLY"},
        },
        "source_side_diagnostics": source,
        "jtl_progression_diagnostics": jtl_progression(trace, origin_name),
        "terminal_diagnostics": {
            "V(JTL6_OUT)_signed_area_V_s": area(trace, "V(JTL6_OUT)", window),
            "I(R_TERM)_signed_area_A_s": area(trace, "I(R_TERM)", window),
            "window_ps": [window[0] * 1e12, window[1] * 1e12],
            "formula": "trapezoid(actual stored time grid, signal)",
            "label": f"{origin_name}_SUPPORT_WINDOW",
            "status": "DERIVED",
        },
    }


def multi_evidence_response(trace: Any, origin_name: str, origin_record: dict[str, Any]) -> dict[str, Any]:
    """Record a bounded multi-signal progression candidate without calling it an event."""
    bj1 = origin_record["phase_diagnostics"]["BJ1"]
    bj2 = origin_record["phase_diagnostics"]["BJ2"]
    jtl = origin_record["jtl_progression_diagnostics"]
    terminal = origin_record["terminal_diagnostics"]
    qbout = extrema(trace, "V(QBOUT)", ORIGINS[origin_name]["window"])
    checks = {
        "BJ1_half_turn_marker": bj1.get("first_half_turn_sample_index") is not None,
        "BJ2_0p9_turn_marker": bj2.get("first_0p9_turn_sample_index") is not None,
        "QBOUT_direct_signal": qbout.get("max_abs") is not None and qbout.get("max_abs") > 0.0,
        "ordered_JTL1_to_JTL6_candidate": jtl.get("complete_progression_candidate") is True,
        "terminal_direct_area": terminal.get("V(JTL6_OUT)_signed_area_V_s") is not None,
    }
    return {
        "status": "BOUNDED_RESULT" if all(checks.values()) else "NO_COMPLETE_MULTI_EVIDENCE_CANDIDATE",
        "origin": origin_name,
        "evidence_order": ["BJ1", "BJ2", "QBOUT", "ordered_JTL1_to_JTL6", "terminal"],
        "checks": checks,
        "QBOUT_descriptive_extrema": qbout,
        "JTL_diagnostics": jtl,
        "terminal_diagnostics": terminal,
        "label": "MECHANICAL_MULTI_EVIDENCE_CANDIDATE_ONLY",
        "not_event_count": True,
        "not_sfq_count": True,
        "scientific_interpretation_performed": False,
    }


def control_guardrail(origin_record: dict[str, Any], response_record: dict[str, Any]) -> dict[str, Any]:
    candidate = response_record["status"] == "BOUNDED_RESULT"
    return {
        "status": "UNSUITABLE_WORKING_POINT" if candidate else "CLEAN",
        "response_candidate": candidate,
        "rule": "a complete multi-evidence downstream progression in ZERO_STATE_READ_CONTROL makes the RJ2 point unsuitable",
        "evidence": response_record,
        "label": "BOUNDED_RESULT_GUARDRAIL_ONLY",
        "scientific_interpretation_performed": False,
    }


def whole_run_terminal(trace: Any) -> dict[str, Any]:
    window = (0.0, 200e-12)
    return {"V(JTL6_OUT)_signed_area_V_s": area(trace, "V(JTL6_OUT)", window), "I(R_TERM)_signed_area_A_s": area(trace, "I(R_TERM)", window), "window_ps": [0.0, 200.0], "formula": "trapezoid(actual stored time grid, signal)", "label": "WHOLE_RUN_TOTAL_ONLY", "not_population_count": True, "status": "DERIVED"}


def diff_area(trace: Any, start_s: float, end_s: float) -> float | None:
    indexes = window_indices(trace.time, start_s, end_s)
    values = tuple(float(trace.column("V(BJ1|XBQ1)")[index]) - float(trace.column("V(BJ2|XBQ1)")[index]) for index in indexes)
    times = tuple(trace.time[index] for index in indexes)
    return trapezoid(times, values) if len(times) >= 2 else None


def cumulative_diff(trace: Any, start_s: float, end_s: float) -> dict[str, Any]:
    indexes = window_indices(trace.time, start_s, end_s)
    times = tuple(trace.time[index] for index in indexes)
    values = tuple(float(trace.column("V(BJ1|XBQ1)")[index]) - float(trace.column("V(BJ2|XBQ1)")[index]) for index in indexes)
    if len(times) < 2:
        return {"status": "UNKNOWN", "value_V_s": None, "reason": "fewer_than_two_stored_samples"}
    cumulative = [0.0]
    for index in range(len(times) - 1):
        cumulative.append(cumulative[-1] + (values[index] + values[index + 1]) * 0.5 * (times[index + 1] - times[index]))
    return {"status": "DERIVED", "value_V_s": cumulative[-1], "max_cumulative_V_s": max(cumulative), "min_cumulative_V_s": min(cumulative), "sample_count": len(times), "start_time_ps": times[0] * 1e12, "last_sample_time_ps": times[-1] * 1e12, "formula": "cumulative trapezoid(actual stored time grid, V(BJ1)-V(BJ2))"}


def diff_segment(trace: Any, name: str, start_s: float | None, end_s: float | None) -> dict[str, Any]:
    base = {"name": name, "label": "DERIVED_DIFFERENTIAL_VOLTAGE_IMPULSE / MECHANICAL_NAVIGATION_ONLY", "formula": "trapezoid(actual stored grid, V(BJ1|XBQ1)-V(BJ2|XBQ1))", "unit": "V_s"}
    if start_s is None or end_s is None or end_s <= start_s:
        return {**base, "status": "UNKNOWN", "value_V_s": None, "reason": "missing_or_nonordered_navigation_anchors"}
    value = diff_area(trace, start_s, end_s)
    return {**base, "status": "DERIVED" if value is not None else "UNKNOWN", "value_V_s": value, "window_ps": [start_s * 1e12, end_s * 1e12]}


def differential_voltage_impulse(trace: Any, final_record: dict[str, Any], l2: float) -> dict[str, Any]:
    bj1 = final_record["phase_diagnostics"]["BJ1"]
    bj2 = final_record["phase_diagnostics"]["BJ2"]
    t_bj1 = bj1.get("first_half_turn_timing_diagnostic_ps")
    t_bj2 = bj2.get("first_0p9_turn_timing_diagnostic_ps")
    t1 = t_bj1 * 1e-12 if t_bj1 is not None else None
    t2 = t_bj2 * 1e-12 if t_bj2 is not None else None
    anchor_start = t2
    cumulative_after_anchor = cumulative_diff(trace, anchor_start, DIFF_TO_140) if anchor_start is not None else {"status": "UNKNOWN", "value_V_s": None, "reason": "missing_first_BJ2_0p9_anchor"}
    l1_values = tuple(float(value) for value in trace.column("I(L1|XBQ1)"))
    anchor_index = bj2.get("first_0p9_turn_sample_index")
    l1_anchor = l1_values[anchor_index] if isinstance(anchor_index, int) and 0 <= anchor_index < len(l1_values) else None
    required: dict[str, Any]
    ratio: dict[str, Any]
    if l1_anchor is None or l1_anchor >= 0.0:
        required = {"status": "UNKNOWN", "value_V_s": None, "formula": "-(L1+L2)*I(L1_anchor)", "unit": "V_s", "reason": "I(L1_anchor) is missing or not negative", "label": "MECHANICAL_PROXY_ONLY"}
        ratio = {"status": "UNKNOWN", "ratio": None, "reason": "required impulse is not defined", "label": "MECHANICAL_PROXY_ONLY"}
    else:
        required_value = -((FIXED["L1_pH"] + l2) * 1e-12) * l1_anchor
        required = {"status": "DERIVED", "value_V_s": required_value, "L1_anchor_A": l1_anchor, "L1_plus_L2_H": (FIXED["L1_pH"] + l2) * 1e-12, "formula": "-(L1+L2)*I(L1_anchor)", "unit": "V_s", "label": "MECHANICAL_PROXY_ONLY"}
        available = max(0.0, float(cumulative_after_anchor.get("max_cumulative_V_s", 0.0))) if cumulative_after_anchor.get("status") == "DERIVED" else None
        ratio = {"status": "DERIVED" if available is not None else "UNKNOWN", "ratio": available / required_value if available is not None and required_value > 0.0 else None, "available_max_positive_cumulative_V_s": available, "required_V_s": required_value, "label": "MECHANICAL_PROXY_ONLY"}
    component_windows = OrderedDict(
        (
            ("110_to_first_BJ1_half", (DIFF_START, t1)),
            ("first_BJ1_half_to_first_BJ2_0p9", (t1, t2)),
            ("first_BJ2_anchor_to_121", (t2, DIFF_TO_121)),
            ("121_to_140", (DIFF_TO_121, DIFF_TO_140)),
            ("first_BJ2_anchor_to_140", (t2, DIFF_TO_140)),
            ("first_BJ2_anchor_to_200", (t2, 200e-12)),
            ("110_to_121", (DIFF_START, DIFF_TO_121)),
            ("110_to_140", (DIFF_START, DIFF_TO_140)),
            ("110_to_200", (DIFF_START, 200e-12)),
        )
    )
    component_areas = {
        name: {
            "BJ1_signed_area_V_s": area(trace, "V(BJ1|XBQ1)", window) if window[0] is not None and window[1] > window[0] else None,
            "BJ2_signed_area_V_s": area(trace, "V(BJ2|XBQ1)", window) if window[0] is not None and window[1] > window[0] else None,
            "window_ps": [window[0] * 1e12, window[1] * 1e12] if window[0] is not None else None,
            "formula": "trapezoid(actual stored time grid, direct same-direction voltage)",
            "status": "DERIVED" if window[0] is not None and window[1] > window[0] else "UNKNOWN",
        }
        for name, window in component_windows.items()
    }
    return {
        "status": "DERIVED" if t1 is not None or t2 is not None else "UNKNOWN",
        "signal": "V(BJ1|XBQ1)-V(BJ2|XBQ1)",
        "raw_unit": "V",
        "integral_unit": "V_s",
        "A_DIFF_cumulative_definition": "cumulative trapezoid on actual stored time grid from 110ps",
        "anchor_times_ps": {"t_BJ1_half_ps": t_bj1, "t_BJ2_0p9_ps": t_bj2},
        "A_DIFF_pre_first_BJ1": diff_segment(trace, "A_DIFF_pre_first_BJ1", DIFF_START, t1),
        "A_DIFF_first_BJ1_to_first_BJ2": diff_segment(trace, "A_DIFF_first_BJ1_to_first_BJ2", t1, t2),
        "A_DIFF_post_BJ2_to_121": diff_segment(trace, "A_DIFF_post_BJ2_to_121", t2, DIFF_TO_121),
        "A_DIFF_121_to_140": diff_segment(trace, "A_DIFF_121_to_140", DIFF_TO_121, DIFF_TO_140),
        "A_DIFF_cumulative_landmarks": {
            "from_110_to_121": cumulative_diff(trace, DIFF_START, DIFF_TO_121),
            "from_110_to_140": cumulative_diff(trace, DIFF_START, DIFF_TO_140),
            "from_110_to_200": cumulative_diff(trace, DIFF_START, 200e-12),
        },
        "A_DIFF_cumulative_after_BJ2_anchor_to_140": cumulative_after_anchor,
        "component_voltage_areas": component_areas,
        "A_REQUIRED_TO_L1_ZERO": required,
        "rearm_impulse_completion_ratio": ratio,
        "labels": ["DERIVED_DIFFERENTIAL_VOLTAGE_IMPULSE", "MECHANICAL_NAVIGATION_ONLY", "MECHANICAL_PROXY_ONLY"],
        "not_switching_energy": True,
        "not_sfq_count": True,
        "scientific_interpretation_performed": False,
    }


def post_first_bj2_rearm(trace: Any, final_record: dict[str, Any], l2: float) -> dict[str, Any]:
    bj1 = final_record["phase_diagnostics"]["BJ1"]
    bj2 = final_record["phase_diagnostics"]["BJ2"]
    anchor_ps = bj2.get("first_0p9_turn_timing_diagnostic_ps")
    anchor_index = bj2.get("first_0p9_turn_sample_index")
    if not isinstance(anchor_index, int) or anchor_index < 0 or anchor_index >= len(trace.time):
        return {"status": "UNKNOWN", "t_BJ1_half_ps": bj1.get("first_half_turn_timing_diagnostic_ps"), "t_BJ2_0p9_ps": anchor_ps, "post_first_bj2_L1_negative_to_positive_candidate": "UNKNOWN", "second_L2_surge_proxy": "UNKNOWN", "label": "MECHANICAL_REARM_PROXY_ONLY", "reason": "missing first FINAL-origin BJ2 +0.9 navigation anchor"}
    anchor_s = trace.time[anchor_index]
    post_indexes = tuple(index for index, value in enumerate(trace.time) if anchor_s <= value < 200e-12)
    if len(post_indexes) < 2:
        return {"status": "UNKNOWN", "t_BJ1_half_ps": bj1.get("first_half_turn_timing_diagnostic_ps"), "t_BJ2_0p9_ps": anchor_ps, "post_first_bj2_L1_negative_to_positive_candidate": "UNKNOWN", "second_L2_surge_proxy": "UNKNOWN", "label": "MECHANICAL_REARM_PROXY_ONLY", "reason": "post-anchor window has fewer than two stored samples"}
    times_ps = tuple(trace.time[index] * 1e12 for index in post_indexes)
    l1 = tuple(float(trace.column("I(L1|XBQ1)")[index]) for index in post_indexes)
    l2_values = tuple(float(trace.column("I(L2|XBQ1)")[index]) for index in post_indexes)
    transitions: list[dict[str, Any]] = []
    negative_to_positive: list[float] = []
    for position, (left, right) in enumerate(zip(l1, l1[1:])):
        if left == 0.0:
            transitions.append({"time_ps": times_ps[position], "direction": "exact_zero_sample"})
        if (left < 0.0 < right) or (left > 0.0 > right):
            direction = "negative_to_positive" if left < 0.0 < right else "positive_to_negative"
            transitions.append({"time_ps": times_ps[position + 1], "direction": direction, "interpolation": False})
            if direction == "negative_to_positive":
                negative_to_positive.append(times_ps[position + 1])
    if l1[-1] == 0.0:
        transitions.append({"time_ps": times_ps[-1], "direction": "exact_zero_sample"})
    first_recross_index = None
    positive_dwell_end_index = None
    for position in range(1, len(l1)):
        if l1[position - 1] < 0.0 < l1[position]:
            first_recross_index = position
            positive_dwell_end_index = next((candidate for candidate in range(position + 1, len(l1)) if l1[candidate] <= 0.0), len(l1) - 1)
            break
    before_121 = tuple(value for index, value in zip(post_indexes, l1) if trace.time[index] < DIFF_TO_121)
    before_140 = tuple(value for index, value in zip(post_indexes, l1) if trace.time[index] < DIFF_TO_140)
    l2_maxima = local_maxima(tuple(trace.time[index] for index in post_indexes), l2_values)
    second_surge = any(l2_maxima[right]["time_ps"] - l2_maxima[left]["time_ps"] >= SECOND_SURGE_MIN_SEPARATION_PS for left in range(len(l2_maxima)) for right in range(left + 1, len(l2_maxima)))
    l2_peak = max(range(len(l2_values)), key=l2_values.__getitem__)
    return {
        "status": "DERIVED",
        "t_BJ1_half_ps": bj1.get("first_half_turn_timing_diagnostic_ps"),
        "t_BJ2_0p9_ps": anchor_ps,
        "anchor_label": "POST_FIRST_REGEN_NAVIGATION_ANCHOR; not an event boundary",
        "post_anchor_window_ps": [anchor_ps, 200.0],
        "L1_at_post_regen_anchor_A": l1[0],
        "L1_post_anchor_min": min(l1),
        "L1_post_anchor_max_before_121_A": max(before_121) if before_121 else None,
        "L1_post_anchor_max_before_140_A": max(before_140) if before_140 else None,
        "L1_post_anchor_max_A": max(l1),
        "L1_sign_transitions": transitions,
        "L1_first_negative_to_positive_time_ps": negative_to_positive[0] if negative_to_positive else None,
        "L1_positive_dwell_duration_ps": ((times_ps[positive_dwell_end_index] - times_ps[first_recross_index]) if first_recross_index is not None and positive_dwell_end_index is not None else None),
        "L1_positive_dwell_end_time_ps": times_ps[positive_dwell_end_index] if positive_dwell_end_index is not None else None,
        "recrossing_observation": "OBSERVED_L1_RECROSSING" if negative_to_positive else "NO_OBSERVED_L1_RECROSSING",
        "post_first_bj2_L1_negative_to_positive_candidate": True if negative_to_positive else False,
        "rearm_label": "MECHANICAL_REARM_PROXY_ONLY",
        "L2_post_anchor_min_A": min(l2_values),
        "L2_post_anchor_max_A": max(l2_values),
        "L2_post_anchor_peak_time_ps": times_ps[l2_peak],
        "L2_post_anchor_local_maxima": l2_maxima,
        "second_L2_surge_proxy": second_surge,
        "second_surge_min_separation_ps": SECOND_SURGE_MIN_SEPARATION_PS,
        "second_surge_label": "MECHANICAL_SECOND_SURGE_PROXY_ONLY",
        "BJ2_max_turns": bj2.get("max_continuous_relative_phase_turns"),
        "BJ2_final_turns": bj2.get("final_continuous_relative_phase_turns"),
        "BJ2_second_threshold_candidate": bj2.get("first_1p5_turn_timing_diagnostic_ps") is not None,
        "BJ2_second_threshold_timing_diagnostic_ps": bj2.get("first_1p5_turn_timing_diagnostic_ps"),
        "BJ2_second_threshold_label": "MECHANICAL_THRESHOLD_ONLY",
        "post_anchor_source_support": {
            "I(B_JSL8)_max_abs_A": max(abs(float(trace.column("I(B_JSL8)")[index])) for index in post_indexes),
            "I(LIN|XBQ1)_max_abs_A": max(abs(float(trace.column("I(LIN|XBQ1)")[index])) for index in post_indexes),
            "I(B_JSL8)_signed_area_A_s": area(trace, "I(B_JSL8)", (anchor_s, 200e-12)),
            "I(LIN|XBQ1)_signed_area_A_s": area(trace, "I(LIN|XBQ1)", (anchor_s, 200e-12)),
            "raw_direct": True,
            "cropped_raw_artifact": False,
        },
        "labels": ["MECHANICAL_REARM_PROXY_ONLY", "MECHANICAL_SECOND_SURGE_PROXY_ONLY", "MECHANICAL_THRESHOLD_ONLY"],
        "not_event_count": True,
        "scientific_interpretation_performed": False,
    }


def post_anchor_progression(trace: Any, final_record: dict[str, Any], start_index: int | None = None) -> dict[str, Any]:
    """Record second-progression evidence after the registered BJ2 anchor."""
    anchor = start_index if start_index is not None else final_record["phase_diagnostics"]["BJ2"].get("first_0p9_turn_sample_index")
    if not isinstance(anchor, int) or anchor < 0 or anchor >= len(trace.time):
        return {"status": "UNKNOWN", "reason": "missing first FINAL-origin BJ2 +0.9 navigation anchor", "label": "MECHANICAL_SECOND_RESPONSE_CANDIDATE_ONLY", "scientific_interpretation_performed": False}
    post_indexes = tuple(index for index in range(anchor, len(trace.time)) if trace.time[index] < 200e-12)

    def second_marker(label: str) -> int | None:
        continuous = continuous_unwrap(tuple(trace.column(label)))
        baseline = continuous[anchor]
        return next((index for index in post_indexes if (continuous[index] - baseline) / (2.0 * math.pi) >= 0.5), None)

    bj1_index = second_marker("P(BJ1|XBQ1)")
    bj2_index = second_marker("P(BJ2|XBQ1)")
    jtl_times: dict[str, float | None] = OrderedDict()
    for stage in range(1, 7):
        index = second_marker(f"P(B01|XJTL1_{stage})")
        jtl_times[f"JTL{stage}"] = trace.time[index] * 1e12 if index is not None else None
    ordered = all(value is not None for value in jtl_times.values()) and all(jtl_times[f"JTL{index}"] < jtl_times[f"JTL{index + 1}"] for index in range(1, 6))
    qbout = extrema(trace, "V(QBOUT)", (trace.time[anchor], 200e-12))
    terminal_area = area(trace, "V(JTL6_OUT)", (trace.time[anchor], 200e-12))
    checks = {
        "second_BJ1_progression_candidate": bj1_index is not None,
        "second_BJ2_progression_candidate": bj2_index is not None,
        "second_QBOUT_direct_signal": qbout.get("max_abs") is not None and qbout.get("max_abs") > 0.0,
        "second_ordered_JTL1_to_JTL6_candidate": ordered,
        "second_terminal_direct_area": terminal_area is not None,
    }
    return {
        "status": "BOUNDED_RESULT" if all(checks.values()) else "NO_SECOND_COMPLETE_MULTI_EVIDENCE_CANDIDATE",
        "anchor_time_ps": trace.time[anchor] * 1e12,
        "anchor_sample_index": anchor,
        "second_BJ1_marker_time_ps": trace.time[bj1_index] * 1e12 if bj1_index is not None else None,
        "second_BJ2_marker_time_ps": trace.time[bj2_index] * 1e12 if bj2_index is not None else None,
        "second_ordered_JTL_marker_times_ps": jtl_times,
        "checks": checks,
        "second_QBOUT_descriptive_extrema": qbout,
        "second_terminal_V_JTL6_OUT_signed_area_V_s": terminal_area,
        "label": "MECHANICAL_SECOND_RESPONSE_CANDIDATE_ONLY",
        "not_event_count": True,
        "not_sfq_count": True,
        "scientific_interpretation_performed": False,
    }


BJ1_NOMINAL_IC_A = 90e-6  # area=0.9 * canonical model icrit=0.1mA; load-line diagnostic only


def indexed_area(trace: Any, label: str, indices: tuple[int, ...]) -> float | None:
    if len(indices) < 2:
        return None
    return trapezoid(tuple(trace.time[index] for index in indices), tuple(float(trace.column(label)[index]) for index in indices))


def positive_segments(trace: Any, anchor_index: int) -> list[dict[str, Any]]:
    post_indexes = tuple(index for index in range(anchor_index, len(trace.time)) if trace.time[index] < 200e-12)
    values = tuple(float(trace.column("I(L1|XBQ1)")[index]) for index in post_indexes)
    segments: list[list[int]] = []
    for index, value in zip(post_indexes, values):
        if value > 0.0:
            if not segments or index != segments[-1][-1] + 1:
                segments.append([index])
            else:
                segments[-1].append(index)
    output: list[dict[str, Any]] = []
    continuous_bj1 = continuous_unwrap(tuple(trace.column("P(BJ1|XBQ1)")))
    continuous_bj2 = continuous_unwrap(tuple(trace.column("P(BJ2|XBQ1)")))
    l1_values = tuple(float(value) for value in trace.column("I(L1|XBQ1)"))
    for position, segment in enumerate(segments):
        start = segment[0]
        end = segment[-1]
        peak = max(segment, key=lambda index: l1_values[index])
        rollback_end = segments[position + 1][0] if position + 1 < len(segments) else len(trace.time)
        rollback_indices = tuple(index for index in range(end + 1, rollback_end) if trace.time[index] < 200e-12)
        start_turn_bj1 = continuous_bj1[start]
        start_turn_bj2 = continuous_bj2[start]
        segment_tuple = tuple(segment)
        bj1_phase = tuple((continuous_bj1[index] - start_turn_bj1) / (2.0 * math.pi) for index in segment_tuple)
        bj2_phase = tuple((continuous_bj2[index] - start_turn_bj2) / (2.0 * math.pi) for index in segment_tuple)
        segment_start_ps = trace.time[start] * 1e12
        segment_end_ps = trace.time[end] * 1e12
        output.append({
            "segment_index": position + 1,
            "start_sample_index": start,
            "end_sample_index": end,
            "label": "FIRST_POSITIVE_L1_EXCURSION" if position == 0 else "POST_FIRST_SECOND_POSITIVE_L1_CANDIDATE",
            "start_time_ps": segment_start_ps,
            "end_time_ps": segment_end_ps,
            "positive_dwell_duration_ps": segment_end_ps - segment_start_ps,
            "sample_count": len(segment_tuple),
            "first_sample_is_strict_negative_to_positive": start > anchor_index and l1_values[start - 1] < 0.0 < l1_values[start],
            "L1_peak_A": l1_values[peak],
            "L1_peak_uA": l1_values[peak] * 1e6,
            "L1_peak_time_ps": trace.time[peak] * 1e12,
            "L1_rollback_min_A": min((l1_values[index] for index in rollback_indices), default=None),
            "L1_rollback_min_time_ps": (trace.time[min(rollback_indices, key=lambda index: l1_values[index])] * 1e12) if rollback_indices else None,
            "BJ1_diagnostics": {
                "I_BJ1_max_abs_A": max(abs(float(trace.column("I(BJ1|XBQ1)")[index])) for index in segment_tuple),
                "I_BJ1_at_L1_peak_A": float(trace.column("I(BJ1|XBQ1)")[peak]),
                "I_BJ1_signed_area_A_s": indexed_area(trace, "I(BJ1|XBQ1)", segment_tuple),
                "V_BJ1_signed_area_V_s": indexed_area(trace, "V(BJ1|XBQ1)", segment_tuple),
                "phase_advance_at_L1_peak_turns": bj1_phase[segment_tuple.index(peak)],
                "max_additional_forward_phase_turns": max(bj1_phase),
                "phase_rollback_after_peak_candidate": any(value <= max(bj1_phase) - 0.25 for value in bj1_phase[segment_tuple.index(peak) + 1:]),
                "reaches_second_navigation_threshold": max(bj1_phase) >= SECOND_THRESHOLD_TURNS,
                "nominal_Ic_A": BJ1_NOMINAL_IC_A,
                "max_abs_over_nominal_Ic": max(abs(float(trace.column("I(BJ1|XBQ1)")[index])) for index in segment_tuple) / BJ1_NOMINAL_IC_A,
                "label": "DERIVED_LOAD_LINE_DIAGNOSTIC; not switching proof",
            },
            "BJ2_diagnostics": {
                "V_BJ2_signed_area_V_s": indexed_area(trace, "V(BJ2|XBQ1)", segment_tuple),
                "phase_advance_at_L1_peak_turns": bj2_phase[segment_tuple.index(peak)],
                "max_additional_forward_phase_turns": max(bj2_phase),
            },
            "receiver_diagnostics": {
                "I(L2|XBQ1)_max_abs_A": max(abs(float(trace.column("I(L2|XBQ1)")[index])) for index in segment_tuple),
                "I(RJ2|XBQ1)_max_abs_A": max(abs(float(trace.column("I(RJ2|XBQ1)")[index])) for index in segment_tuple),
                "V(RJ2|XBQ1)_signed_area_V_s": indexed_area(trace, "V(RJ2|XBQ1)", segment_tuple),
                "V(QBOUT)_signed_area_V_s": indexed_area(trace, "V(QBOUT)", segment_tuple),
            },
            "source_support": {
                label: {"max_abs_A": max(abs(float(trace.column(label)[index])) for index in segment_tuple), "signed_area_A_s": indexed_area(trace, label, segment_tuple)}
                for label in ("I(B_JSL8)", "I(LIN|XBQ1)")
            },
            "timing_relative_to_READ_end": {
                "peak_time_ps": trace.time[peak] * 1e12,
                "relation": "BEFORE_READ_END" if trace.time[peak] < 121e-12 else "AFTER_READ_END",
                "offset_from_121ps": trace.time[peak] * 1e12 - 121.0,
            },
            "not_event_count": True,
            "not_sfq_count": True,
        })
    return output


def second_trigger_analysis(trace: Any, final_record: dict[str, Any]) -> dict[str, Any]:
    anchor_index = final_record["phase_diagnostics"]["BJ2"].get("first_0p9_turn_sample_index")
    if not isinstance(anchor_index, int):
        return {"status": "UNKNOWN", "reason": "missing first BJ2 +0.9 navigation anchor", "label": "SECOND_TRIGGER_DIAGNOSTIC_ONLY", "scientific_interpretation_performed": False}
    segments = positive_segments(trace, anchor_index)
    first = segments[0] if segments else None
    later = segments[1:]
    strongest = max(later, key=lambda item: item["L1_peak_A"]) if later else None
    first_max = first.get("L1_peak_A") if first else None
    second_max = strongest.get("L1_peak_A") if strongest else None
    state_gap = {
        "L1_first_minus_strongest_second_A": first_max - second_max if first_max is not None and second_max is not None else None,
        "BJ1_max_abs_first_minus_strongest_second_A": (first["BJ1_diagnostics"]["I_BJ1_max_abs_A"] - strongest["BJ1_diagnostics"]["I_BJ1_max_abs_A"]) if first and strongest else None,
        "BJ1_phase_max_first_minus_strongest_second_turns": (first["BJ1_diagnostics"]["max_additional_forward_phase_turns"] - strongest["BJ1_diagnostics"]["max_additional_forward_phase_turns"]) if first and strongest else None,
        "comparison_label": "DERIVED_STATE_GAP; no success threshold implied",
    }
    second_start_index = strongest.get("start_sample_index") if strongest else None
    second_progression = post_anchor_progression(trace, final_record, start_index=second_start_index)
    return {
        "status": "DERIVED",
        "anchor_time_ps": trace.time[anchor_index] * 1e12,
        "anchor_sample_index": anchor_index,
        "positive_segment_count": len(segments),
        "all_positive_segments": segments,
        "first_successful_regeneration_reference": first,
        "strongest_second_positive_excursion": strongest,
        "state_gap_first_vs_strongest_second": state_gap,
        "second_complete_multi_evidence_candidate": second_progression,
        "second_progression_anchor_type": "strongest_later_positive_L1_segment_start" if second_start_index is not None else "UNKNOWN",
        "second_trigger_gap_reduced_but_not_closed_candidate": bool(first and strongest and second_progression.get("status") != "BOUNDED_RESULT" and second_max > first_max),
        "label": "SECOND_TRIGGER_DIAGNOSTIC_ONLY",
        "not_event_count": True,
        "not_sfq_count": True,
        "scientific_interpretation_performed": False,
    }


def ratio_record(numerator: float | None, denominator: float | None, *, denominator_abs_area: float | None) -> dict[str, Any]:
    if numerator is None or denominator is None or not math.isfinite(numerator) or not math.isfinite(denominator):
        return {"status": "UNKNOWN", "ratio": None, "reason": "missing_or_nonfinite_operand", "unit": "A_s"}
    if abs(denominator) <= RATIO_AREA_TOLERANCE_A_S:
        return {"status": "UNKNOWN", "ratio": None, "reason": "denominator_at_or_below_1e-18_A_s", "unit": "A_s"}
    if denominator_abs_area is not None and abs(denominator) < RATIO_CANCELLATION_FRACTION * denominator_abs_area:
        return {"status": "UNKNOWN", "ratio": None, "reason": "signed_area_is_cancellation_sensitive_below_1_percent_of_absolute_area", "unit": "A_s"}
    return {"status": "DERIVED", "ratio": numerator / denominator, "numerator_A_s": numerator, "denominator_A_s": denominator, "unit": "A_s"}


def absolute_area(trace: Any, label: str, window: tuple[float, float]) -> float | None:
    _indexes, times, values = selected(trace, label, window)
    return trapezoid(times, tuple(abs(value) for value in values)) if len(times) >= 2 else None


def pre_switch_ratios(traces: dict[str, Any], ratio_inputs: dict[str, dict[str, float | None]]) -> dict[str, Any]:
    output: dict[str, Any] = OrderedDict()
    active_values = sorted({CASE_RJ2[run_id] for run_id in ALL_CASES})
    for rj2 in active_values:
        mask0001 = next(run_id for run_id in ALL_CASES if CASE_RJ2[run_id] == rj2 and run_id.rsplit("_", 1)[1] == "0001")
        mask0011 = next(run_id for run_id in ALL_CASES if CASE_RJ2[run_id] == rj2 and run_id.rsplit("_", 1)[1] == "0011")
        output[f"RJ2_{rj2:g}"] = {
            "RJ2_ohm": rj2,
            "mask_0001_case_id": mask0001,
            "mask_0011_case_id": mask0011,
            "ratio_semantics": "0011 numerator / 0001 denominator; mechanical diagnostic only",
            "MECHANICAL_PRE_SWITCH_PROXY": {
                "window_ps": [110.0, 114.5],
                "I(B_JSL8)_signed_area_ratio": ratio_record(ratio_inputs[mask0011]["I(B_JSL8)"], ratio_inputs[mask0001]["I(B_JSL8)"], denominator_abs_area=absolute_area(traces[mask0001], "I(B_JSL8)", PRE_SWITCH_WINDOW)),
                "I(LIN)_signed_area_ratio": ratio_record(ratio_inputs[mask0011]["I(LIN|XBQ1)"], ratio_inputs[mask0001]["I(LIN|XBQ1)"], denominator_abs_area=absolute_area(traces[mask0001], "I(LIN|XBQ1)", PRE_SWITCH_WINDOW)),
                "label": "MECHANICAL_PRE_SWITCH_PROXY; not a population or re-arm conclusion",
            },
        }
    return output


def bq_delta() -> dict[str, Any]:
    base = BQ400.read_text(encoding="utf-8").splitlines()
    variant = BQ_RJ2.read_text(encoding="utf-8").splitlines()
    changes = [(index + 1, before, after) for index, (before, after) in enumerate(zip(base, variant)) if before != after]
    valid = len(base) == len(variant) and len(changes) == 2 and any("RJ2 4 0 4" in before and after == "RJ2 4 0 {RJ2_VALUE}" for _line, before, after in changes) and any("Only the active BQ element values for L1, RJ1 and IBias" in before and "RJ2" in after for _line, before, after in changes)
    return {"status": "PASS" if valid else "FAIL", "changed_lines": changes, "only_RJ2_parameter_exposure": valid}


def deck_diff() -> dict[str, Any]:
    failures: list[str] = []
    normalized: set[tuple[str, ...]] = set()
    pre_read: set[tuple[str, ...]] = set()
    records: dict[str, Any] = {}
    for run_id in NEW_RUNS:
        text = deck_path(run_id).read_text(encoding="utf-8")
        rj2 = RUN_TO_RJ2[run_id]
        mask = RUN_TO_MASK[run_id]
        for required in (".param L1_VALUE=1.4p", ".param IB_VALUE=260u", ".param RJ1_VALUE=32", f".param RJ2_VALUE={rj2:g}", ".include ../../inputs/BQ_parameterized_bjs400_rj2.cir", ".tran 0.1p 200p", "P(BJS|XBQ1) V(BJS|XBQ1) I(BJS|XBQ1)"):
            if required not in text:
                failures.append(f"{run_id}: missing {required}")
        if ".param L2_VALUE" in text:
            failures.append(f"{run_id}: unexpected L2 parameter perturbation")
        if any(text.count(f"XBVM{index} ") != 1 for index in range(1, 5)):
            failures.append(f"{run_id}: BVM topology count mismatch")
        for instance in range(1, 5):
            for kind in CONTROL_KINDS:
                if control_line(instance, kind, mask[instance - 1] == "1") not in text:
                    failures.append(f"{run_id}: control mismatch {kind}{instance}")
        normalized.add(normalized_deck(text))
        pre_read.add(pre_read_controls(text))
        records[run_id] = {"L2_pH": FIXED["L2_pH"], "RJ2_ohm": rj2, "mask": mask, "deck_sha256": sha256(deck_path(run_id)), "deck_bytes": deck_path(run_id).stat().st_size}
    if len(normalized) != 1:
        failures.append("new decks differ outside registered RJ2 and final-read controls")
    if len(pre_read) != 1:
        failures.append("new controls differ before 110ps")
    historical_failures: list[str] = []
    for run_id in REUSE_RUNS:
        source_text = deck_path(run_id).read_text(encoding="utf-8")
        expected = build_deck(10.0, run_id.rsplit("_", 1)[1])
        if normalized_deck(source_text) != normalized_deck(expected) or pre_read_controls(source_text) != pre_read_controls(expected):
            historical_failures.append(run_id)
    if historical_failures:
        failures.append("historical L2=2.0/RJ2=10 deck comparability failed: " + ",".join(historical_failures))
    delta = bq_delta()
    if delta["status"] != "PASS":
        failures.append("BQ RJ2 parameterization delta is not exact")
    return {
        "schema": "bjs400-rj2-highside-second-trigger-deck-diff-qa-v2",
        "status": "PASS" if not failures else "FAIL",
        "new_run_count": len(NEW_RUNS),
        "reused_case_count": len(REUSE_RUNS),
        "fixed_L1_pH": FIXED["L1_pH"],
        "fixed_IBias_uA": FIXED["IBias_uA"],
        "fixed_RJ1_ohm": FIXED["RJ1_ohm"],
        "fixed_BJS_area": 4,
        "new_RJ2_values_ohm": list(sorted({RUN_TO_RJ2[run_id] for run_id in NEW_RUNS})),
        "fixed_L2_pH": FIXED["L2_pH"],
        "same_mask_only_RJ2_difference": len(normalized) == 1,
        "mask_pair_only_final_read_difference": len(pre_read) == 1,
        "normalized_new_decks_identical": len(normalized) == 1,
        "historical_deck_comparability": "PASS" if not historical_failures else "FAIL",
        "bq_parameterization_delta": delta,
        "runs": records,
        "failures": failures,
    }


def main() -> int:
    execution = json.loads((EXP / "qa/execution_summary.json").read_text(encoding="utf-8"))
    global ALL_CASES, NEW_RUNS, CASE_L2, CASE_RJ2
    active_new_runs = tuple(execution.get("run_order", ()))
    if not active_new_runs or any(run_id not in REGISTERED_NEW_RUNS for run_id in active_new_runs):
        raise RuntimeError("execution summary does not contain a non-empty registered RJ2 prefix")
    if active_new_runs != tuple(run_id for run_id in REGISTERED_NEW_RUNS if run_id in active_new_runs):
        raise RuntimeError("execution run order is not a registered ascending RJ2 prefix")
    NEW_RUNS = active_new_runs
    ALL_CASES = tuple(REUSE_RUNS) + active_new_runs
    CASE_L2 = {run_id: 2.0 for run_id in ALL_CASES}
    CASE_RJ2 = {**{run_id: 10.0 for run_id in REUSE_RUNS}, **{run_id: RUN_TO_RJ2[run_id] for run_id in NEW_RUNS}}
    preflight = json.loads((EXP / "analysis/preflight.json").read_text(encoding="utf-8"))
    relation = head_relation(str(preflight["head"]))
    actual_new_count = len(active_new_runs)
    early_stop_valid = actual_new_count == 6 or (actual_new_count < 6 and isinstance(execution.get("early_stop_reason"), str) and execution.get("registered_unrun_values"))
    execution_ok = execution.get("status") == "PASS" and execution.get("solver_solve_invocations") == actual_new_count and execution.get("exact_new_physical_solve_count") == actual_new_count and execution.get("reused_physical_case_count") == 2 and execution.get("unauthorized_extra_solves") == 0 and execution.get("failed_runs") == [] and early_stop_valid
    reuse_manifest = json.loads((EXP / "REUSED_REFERENCE_MANIFEST.json").read_text(encoding="utf-8"))
    raw_records: dict[str, Any] = {}
    raw_failures: list[str] = []
    grid_hashes: set[str] = set()
    pre_hashes: dict[str, str] = {}
    traces: dict[str, Any] = {}
    cases: dict[str, Any] = OrderedDict()
    ratio_inputs: dict[str, dict[str, float | None]] = {}
    required = expected_probes()
    for case_id in ALL_CASES:
        path = raw_path(case_id)
        if not path.is_file():
            raw_failures.append(f"{case_id}: missing raw.csv")
            continue
        try:
            trace = read_csv(path)
        except Exception as exc:
            raw_failures.append(f"{case_id}: raw reader failure: {exc}")
            continue
        pre_hashes[case_id] = sha256(path)
        traces[case_id] = trace
        qa = trace.qa()
        missing = sorted(required - set(trace.headers))
        unknown = sorted(set(missing) & OPTIONAL_UNKNOWN)
        missing_required = sorted(set(missing) - OPTIONAL_UNKNOWN)
        grid_hash = hashlib.sha256("\n".join(f"{value:.17g}" for value in trace.time).encode()).hexdigest()
        grid_hashes.add(grid_hash)
        if trace.sample_count != 1999 or trace.time[0] != 0.0 or trace.time[-1] != 1.999e-10:
            raw_failures.append(f"{case_id}: time/sample range mismatch")
        if qa["nan_inf_status"] != "PASS" or not qa["strictly_increasing_time"]:
            raw_failures.append(f"{case_id}: finite/monotonic failure")
        if missing_required:
            raw_failures.append(f"{case_id}: missing required probes {','.join(missing_required)}")
        if case_id in REUSE_RUNS and pre_hashes[case_id] != reuse_manifest["references"][case_id]["artifacts"]["raw.csv"]["source_sha256"]:
            raw_failures.append(f"{case_id}: reused raw hash mismatch")
        raw_records[case_id] = {"case_id": case_id, "path": str(path.relative_to(REPO)), "sha256": pre_hashes[case_id], "bytes": path.stat().st_size, "header_count": len(trace.headers), "sample_count": trace.sample_count, "first_timestamp_s": trace.time[0], "last_timestamp_s": trace.time[-1], "dt_min_s": min(trace.dt), "dt_max_s": max(trace.dt), "stored_time_grid_sha256": grid_hash, "strictly_increasing_time": qa["strictly_increasing_time"], "finite_values": qa["nan_inf_status"] == "PASS", "duplicate_columns": trace.duplicate_columns, "required_probe_status": "UNKNOWN" if unknown and not missing_required else ("PASS" if not missing else "FAIL"), "missing_probes": missing, "unknown_probes": unknown, "physical_solve_this_experiment": case_id in NEW_RUNS, "raw_immutable": True}
        try:
            origin_records = {origin_name: origin_summary(trace, origin_name) for origin_name in ORIGINS}
            post = post_first_bj2_rearm(trace, origin_records["FINAL_ORIGIN"], CASE_L2[case_id])
            diff = differential_voltage_impulse(trace, origin_records["FINAL_ORIGIN"], CASE_L2[case_id])
            control_response = multi_evidence_response(trace, "CONTROL_ORIGIN", origin_records["CONTROL_ORIGIN"])
            final_response = multi_evidence_response(trace, "FINAL_ORIGIN", origin_records["FINAL_ORIGIN"])
            control = control_guardrail(origin_records["CONTROL_ORIGIN"], control_response)
            second = post_anchor_progression(trace, origin_records["FINAL_ORIGIN"])
            second_trigger = second_trigger_analysis(trace, origin_records["FINAL_ORIGIN"])
            ratio_inputs[case_id] = {"I(B_JSL8)": area(trace, "I(B_JSL8)", PRE_SWITCH_WINDOW), "I(LIN|XBQ1)": area(trace, "I(LIN|XBQ1)", PRE_SWITCH_WINDOW)}
            first_response_name = f"FIRST_RESPONSE_{case_id.rsplit('_', 1)[1]}"
            cases[case_id] = {"case_id": case_id, "L1_pH": FIXED["L1_pH"], "L2_pH": CASE_L2[case_id], "RJ2_ohm": CASE_RJ2[case_id], "IBias_uA": FIXED["IBias_uA"], "RJ1_ohm": FIXED["RJ1_ohm"], "mask": case_id.rsplit("_", 1)[1], "source_experiment": source_experiment(case_id), "source_run": source_run(case_id), "physical_solve_this_experiment": case_id in NEW_RUNS, "scientific_interpretation_performed": False, "raw_provenance": {"path": str(path.relative_to(REPO)), "sha256": pre_hashes[case_id]}, "CONTROL_ORIGIN": origin_records["CONTROL_ORIGIN"], "FINAL_ORIGIN": origin_records["FINAL_ORIGIN"], "CONTROL_HARD_GUARDRAIL": control, first_response_name: final_response, "POST_FIRST_BJ2_REARM": post, "SECOND_RESPONSE_AFTER_FIRST_BJ2": second, "SECOND_TRIGGER_ANALYSIS": second_trigger, "DIFFERENTIAL_VOLTAGE_IMPULSE": diff, "terminal_control_area": origin_records["CONTROL_ORIGIN"]["terminal_diagnostics"], "terminal_final_area": origin_records["FINAL_ORIGIN"]["terminal_diagnostics"], "terminal_whole_run_area": whole_run_terminal(trace), "whole_run_terminal": whole_run_terminal(trace), "notes": ["CONTROL_ORIGIN and FINAL_ORIGIN are separate mechanical windows.", "FIRST_RESPONSE is a multi-signal mechanical candidate, not an event/SFQ count.", "POST_FIRST_BJ2_REARM uses a stored navigation anchor, not an event boundary.", "SECOND_TRIGGER_ANALYSIS compares first and later positive L1 excursions and is not a regeneration count.", "SECOND_RESPONSE_AFTER_FIRST_BJ2 is only a mechanical multi-evidence candidate.", "Differential-voltage integrals and phase thresholds are mechanical/proxy diagnostics, not switching energy or SFQ counts."]}
        except Exception as exc:
            raw_failures.append(f"{case_id}: mechanical arithmetic failure: {exc}")
    for case_id in REGISTERED_NEW_RUNS:
        if case_id not in active_new_runs:
            run_dir = EXP / "runs" / case_id
            if any((run_dir / name).exists() for name in ("raw.csv", "metadata.json", "run.log")):
                raw_failures.append(f"unrun case has physical artifact after registered early stop: {case_id}")
    post_hashes = {case_id: sha256(raw_path(case_id)) for case_id in pre_hashes}
    raw_ok = not raw_failures and len(traces) == len(ALL_CASES) and len(grid_hashes) == 1 and pre_hashes == post_hashes
    raw_qa = {"schema": "bjs400-rj2-highside-second-trigger-raw-qa-v2", "status": "PASS" if raw_ok else "FAIL", "artifact_validity": "VALID" if raw_ok else "INVALID", "experiment_id": EXP.name, "created_at_local": now(), "head": relation["head"], "execution_status": "PASS" if execution_ok else "FAIL", "new_physical_solve_count": actual_new_count, "authorized_new_physical_solve_max": 6, "reused_physical_case_count": 2, "registered_logical_case_count": 8, "observed_logical_case_count": len(ALL_CASES), "unrun_preserved_cases": sorted(set(REUSE_RUNS + tuple(REGISTERED_NEW_RUNS)) - set(ALL_CASES)), "unauthorized_extra_solves": 0, "cases": raw_records, "pre_analysis_sha256": pre_hashes, "post_analysis_sha256": post_hashes, "raw_unchanged_pre_to_post": pre_hashes == post_hashes, "common_time_grid": len(grid_hashes) == 1, "stored_grid_hashes": sorted(grid_hashes), "required_probe_missing_is_not_fabricated": True, "raw_files_modified": 0, "scientific_analysis_performed": False, "failures": raw_failures}
    decks = deck_diff()
    ratios = pre_switch_ratios(traces, ratio_inputs) if raw_ok else {}
    control_guardrail_cases = {case_id: cases[case_id]["CONTROL_HARD_GUARDRAIL"]["status"] for case_id in cases}
    first_response_cases = {case_id: cases[case_id].get(f"FIRST_RESPONSE_{cases[case_id]['mask']}", {}).get("status") for case_id in cases}
    recross_cases = [case_id for case_id in cases if cases[case_id]["POST_FIRST_BJ2_REARM"].get("recrossing_observation") == "OBSERVED_L1_RECROSSING"]
    second_response_cases = [case_id for case_id in cases if cases[case_id]["SECOND_TRIGGER_ANALYSIS"].get("second_complete_multi_evidence_candidate", {}).get("status") == "BOUNDED_RESULT"]
    baseline_0011 = next((case_id for case_id in cases if cases[case_id]["mask"] == "0011" and CASE_RJ2[case_id] == 10.0), None)
    baseline_analysis = cases[baseline_0011]["SECOND_TRIGGER_ANALYSIS"] if baseline_0011 is not None else {}
    baseline_second = baseline_analysis.get("strongest_second_positive_excursion") or {}
    baseline_bj1 = baseline_second.get("BJ1_diagnostics", {})
    rj2_state_comparison: dict[str, Any] = OrderedDict()
    gap_reduced_cases: list[str] = []
    for case_id in cases:
        if cases[case_id]["mask"] != "0011" or baseline_0011 is None:
            continue
        analysis = cases[case_id]["SECOND_TRIGGER_ANALYSIS"]
        second_peak = analysis.get("strongest_second_positive_excursion") or {}
        bj1_peak = second_peak.get("BJ1_diagnostics", {})
        current_l1 = second_peak.get("L1_peak_A")
        current_bj1 = bj1_peak.get("I_BJ1_max_abs_A")
        current_phase = bj1_peak.get("max_additional_forward_phase_turns")
        baseline_l1 = baseline_second.get("L1_peak_A")
        baseline_bj1_value = baseline_bj1.get("I_BJ1_max_abs_A")
        baseline_phase = baseline_bj1.get("max_additional_forward_phase_turns")
        row = {
            "case_id": case_id,
            "RJ2_ohm": CASE_RJ2[case_id],
            "baseline_case_id": baseline_0011,
            "baseline_second_L1_peak_A": baseline_l1,
            "second_L1_peak_A": current_l1,
            "second_L1_peak_delta_A": current_l1 - baseline_l1 if current_l1 is not None and baseline_l1 is not None else None,
            "baseline_second_BJ1_max_abs_A": baseline_bj1_value,
            "second_BJ1_max_abs_A": current_bj1,
            "second_BJ1_max_abs_delta_A": current_bj1 - baseline_bj1_value if current_bj1 is not None and baseline_bj1_value is not None else None,
            "baseline_second_BJ1_phase_max_turns": baseline_phase,
            "second_BJ1_phase_max_turns": current_phase,
            "second_BJ1_phase_delta_turns": current_phase - baseline_phase if current_phase is not None and baseline_phase is not None else None,
            "comparison_label": "DERIVED_RJ2_STATE_COMPARISON; no success threshold implied",
        }
        rj2_state_comparison[case_id] = row
        if case_id != baseline_0011 and analysis.get("second_complete_multi_evidence_candidate", {}).get("status") != "BOUNDED_RESULT" and ((row["second_L1_peak_delta_A"] is not None and row["second_L1_peak_delta_A"] > 0.0) or (row["second_BJ1_max_abs_delta_A"] is not None and row["second_BJ1_max_abs_delta_A"] > 0.0) or (row["second_BJ1_phase_delta_turns"] is not None and row["second_BJ1_phase_delta_turns"] > 0.0)):
            gap_reduced_cases.append(case_id)
    control_failure_cases = [case_id for case_id, status in control_guardrail_cases.items() if status != "CLEAN"]
    first_response_failure_cases = [case_id for case_id, status in first_response_cases.items() if status != "BOUNDED_RESULT"]
    failure_cases = sorted(set(control_failure_cases + first_response_failure_cases), key=lambda case_id: (CASE_RJ2[case_id], case_id))
    first_guardrail_failure_boundary = CASE_RJ2[failure_cases[0]] if failure_cases else None
    runs_after_first_guardrail_failure = [case_id for case_id in active_new_runs if first_guardrail_failure_boundary is not None and CASE_RJ2[case_id] > first_guardrail_failure_boundary]
    protocol_audit = {
        "schema": "bjs400-rj2-highside-second-trigger-protocol-audit-v2",
        "status": "FAIL" if runs_after_first_guardrail_failure else "PASS",
        "rule": "complete the current RJ2 pair, then stop before any higher RJ2 pair after a CONTROL or first-response failure boundary",
        "first_guardrail_failure_boundary_RJ2_ohm": first_guardrail_failure_boundary,
        "first_guardrail_failure_cases": [case_id for case_id in failure_cases if CASE_RJ2[case_id] == first_guardrail_failure_boundary] if first_guardrail_failure_boundary is not None else [],
        "executor_run_order": list(active_new_runs),
        "runs_after_first_guardrail_failure": runs_after_first_guardrail_failure,
        "executor_stop_reason": execution.get("early_stop_reason"),
        "corrected_second_response_candidate_cases": second_response_cases,
        "stage_decision_recorded": bool(execution.get("stage_decisions")),
        "raw_history_preserved": True,
        "scientific_interpretation_performed": False,
    }
    if control_failure_cases or first_response_failure_cases:
        bounded_outcome = "OUTCOME_C_FIRST_RESPONSE_OR_CONTROL_GUARDRAIL_FAILURE"
    elif second_response_cases:
        bounded_outcome = "OUTCOME_A_SECOND_MULTI_EVIDENCE_RESPONSE_CANDIDATE"
    elif gap_reduced_cases:
        bounded_outcome = "SECOND_TRIGGER_GAP_REDUCED_BUT_NOT_CLOSED"
    else:
        bounded_outcome = "BOUNDED_RESULT_NO_OBSERVED_L1_RECROSSING_IN_REGISTERED_RJ2_MATRIX"
    mechanical_status = "PASS" if raw_ok and decks["status"] == "PASS" and len(cases) == len(ALL_CASES) else "FAIL"
    mechanical_summary = {"schema": "bjs400-rj2-highside-second-trigger-mechanical-summary-v2", "experiment_id": EXP.name, "created_at_local": now(), "status": mechanical_status, "scientific_interpretation_performed": False, "fixed_point": {"L1_pH": 1.4, "L2_pH": 2.0, "IBias_uA": 260.0, "RJ1_ohm": 32.0, "RJ2_ohm": 10.0, "BJS_area": 4, "BJS_Ic_uA": 400.0}, "rj2_values_ohm": [10.0, *RJ2_VALUES], "registered_logical_case_count": 8, "observed_logical_case_count": len(ALL_CASES), "masks": list(MASKS), "historical_reuse_count": 2, "new_physical_solve_count": actual_new_count, "authorized_new_physical_solve_max": 6, "unrun_preserved_cases": sorted(set(REUSE_RUNS + tuple(REGISTERED_NEW_RUNS)) - set(ALL_CASES)), "case_order": list(ALL_CASES), "dedicated_sections": ["CONTROL_ORIGIN", "FINAL_ORIGIN", "FIRST_RESPONSE_0001", "FIRST_RESPONSE_0011", "POST_FIRST_BJ2_REARM", "SECOND_TRIGGER_ANALYSIS", "SECOND_RESPONSE_AFTER_FIRST_BJ2", "DIFFERENTIAL_VOLTAGE_IMPULSE", "TIMING_RELATIVE_TO_READ"], "bounded_outcome": bounded_outcome, "control_guardrail_cases": control_guardrail_cases, "first_response_cases": first_response_cases, "observed_l1_recrossing_cases": recross_cases, "second_response_candidate_cases": second_response_cases, "second_trigger_gap_reduced_cases": gap_reduced_cases, "rj2_state_comparison_0011": rj2_state_comparison, "control_failure_cases": control_failure_cases, "first_response_failure_cases": first_response_failure_cases, "protocol_audit_status": protocol_audit["status"], "first_guardrail_failure_boundary_RJ2_ohm": first_guardrail_failure_boundary, "phase_convention": "raw P radians; continuous_unwrap(raw)/(2*pi) for diagnostic turns only", "windows": {name: {"window_ps": [spec["window"][0] * 1e12, spec["window"][1] * 1e12], "baseline_ps": [spec["baseline"][0] * 1e12, spec["baseline"][1] * 1e12]} for name, spec in ORIGINS.items()}, "pre_switch_proxy_window_ps": [110.0, 114.5], "differential_windows": {"A_DIFF_pre_first_BJ1": [110.0, "first BJ1 +0.5 marker"], "A_DIFF_first_BJ1_to_first_BJ2": ["first BJ1 +0.5 marker", "first BJ2 +0.9 marker"], "A_DIFF_post_BJ2_to_121": ["first BJ2 +0.9 marker", 121.0], "A_DIFF_121_to_140": [121.0, 140.0]}, "area_semantics": "trapezoid on actual stored time grid; half-open windows; no interpolation/resampling", "thresholds": {"BJ1_half_turn": 0.5, "BJ2_regeneration_navigation": 0.9, "second_threshold": 1.5, "JTL_first": 0.5, "JTL_second": 1.5}, "post_first_bj2_policy": {"anchor": "first FINAL-origin BJ2 +0.9 timing diagnostic", "l1_label": "MECHANICAL_REARM_PROXY_ONLY", "l2_label": "MECHANICAL_SECOND_SURGE_PROXY_ONLY", "required_impulse_label": "MECHANICAL_PROXY_ONLY", "no_event_or_sfq_classification": True}, "ratio_policy": {"numerator_denominator": "0011 / 0001", "signed_area_tolerance_A_s": RATIO_AREA_TOLERANCE_A_S, "cancellation_fraction": RATIO_CANCELLATION_FRACTION, "ambiguous_status": "UNKNOWN"}, "cases": cases, "ratio_diagnostics": ratios, "notes": ["All metrics are MECHANICAL or DERIVED only.", "No phase threshold, differential impulse, L1 sign transition, L2 surge, terminal area or JTL progression field is an event/SFQ count.", "The bounded outcome is a registered evidence label, not scientific interpretation.", "The protocol audit is separate from raw artifact validity.", "Scientific interpretation is NOT_PERFORMED."]}
    provenance = {"schema": "bjs400-rj2-highside-second-trigger-provenance-v2", "experiment_id": EXP.name, "head_at_qa": relation["head"], "preflight": "analysis/preflight.json", "source_manifest": "SOURCE_MANIFEST.json", "reuse_manifest": "REUSED_REFERENCE_MANIFEST.json", "execution_summary": "qa/execution_summary.json", "mechanical_summary": "mechanical_summary.json", "solver": "build/josim-cli", "new_runs": {run_id: {"deck": str(deck_path(run_id).relative_to(REPO)), "deck_sha256": sha256(deck_path(run_id)), "raw": str(raw_path(run_id).relative_to(REPO)), "raw_sha256": pre_hashes.get(run_id), "metadata": str((EXP / "runs" / run_id / "metadata.json").relative_to(REPO)), "run_log": str((EXP / "runs" / run_id / "run.log").relative_to(REPO)), "physical_solve_this_experiment": True} for run_id in active_new_runs}, "reused_runs": {run_id: {"reference": str((EXP / "references/reused" / run_id).relative_to(REPO)), "source_experiment": str(AUTHORITY_SOURCE_EXPERIMENT.relative_to(REPO)), "source_run": f"runs/{run_id}", "raw_sha256": pre_hashes.get(run_id), "deck_sha256": sha256(deck_path(run_id)), "physical_solve_this_experiment": False} for run_id in REUSE_RUNS}, "unrun_preserved_decks": {run_id: {"deck": str(deck_path(run_id).relative_to(REPO)), "deck_sha256": sha256(deck_path(run_id))} for run_id in REGISTERED_NEW_RUNS if run_id not in active_new_runs}, "runs": {}, "all_registered_logical_cases": list(REUSE_RUNS) + list(REGISTERED_NEW_RUNS), "observed_logical_cases": list(ALL_CASES), "scientific_analysis_performed": False}
    provenance["runs"] = {**provenance["new_runs"], **provenance["reused_runs"]}
    transformations = {"schema": "bjs400-rj2-highside-second-trigger-transformation-registry-v2", "raw_immutable": True, "scientific_analysis_performed": False, "transformations": [{"name": "origin_separation", "operation": "CONTROL_ORIGIN [70,110) and FINAL_ORIGIN [110,200)", "scope": "mechanical navigation"}, {"name": "first_second_positive_excursion", "operation": "stored-sample positive L1 segments after first BJ2 +0.9 anchor", "scope": "SECOND_TRIGGER_DIAGNOSTIC_ONLY", "not_event_count": True}, {"name": "differential_voltage_impulse", "operation": "V(BJ1)-V(BJ2) and actual-grid cumulative/segment trapezoids", "scope": "DERIVED_DIFFERENTIAL_VOLTAGE_IMPULSE / MECHANICAL_NAVIGATION_ONLY", "not_switching_energy": True}, {"name": "post_first_bj2_rearm", "operation": "stored-anchor L1 transitions and L2 local maxima", "scope": "MECHANICAL_REARM_PROXY_ONLY / MECHANICAL_SECOND_SURGE_PROXY_ONLY"}, {"name": "phase_display", "operation": "continuous_unwrap(raw_rad)/(2*pi)", "scope": "diagnostic/display only", "not_event_count": True}, {"name": "area_integration", "operation": "trapezoid on actual stored time values; half-open windows", "scope": "mechanical arithmetic", "interpolation": False}, {"name": "stage_selection", "operation": "stage decision consumes only the just-completed RJ2 pair; higher pairs remain unsolved until CONTINUE", "scope": "protocol guardrail"}, {"name": "standalone_plot_input", "operation": "raw.csv direct; no crop/resample/derived CSV", "scope": "visualization"}, {"name": "comparison_plot_input", "operation": "temporary full-run merged CSV under /tmp only; deleted after render", "scope": "visualization"}]}
    write_json(EXP / "qa/raw_qa.json", raw_qa)
    write_json(EXP / "qa/deck_diff_qa.json", decks)
    write_json(EXP / "mechanical_summary.json", mechanical_summary)
    write_json(EXP / "qa/provenance.json", provenance)
    write_json(EXP / "qa/transformation_registry.json", transformations)
    write_json(EXP / "qa/protocol_audit.json", protocol_audit)
    result = {"status": "PASS" if raw_ok and decks["status"] == "PASS" and execution_ok and relation["status"] == "PASS" and mechanical_status == "PASS" else "FAIL", "execution_status": "PASS" if execution_ok else "FAIL", "raw_status": raw_qa["status"], "deck_status": decks["status"], "mechanical_summary_status": mechanical_status, "protocol_audit_status": protocol_audit["status"], "bounded_outcome": bounded_outcome, "observed_l1_recrossing_cases": recross_cases, "second_response_candidate_cases": second_response_cases, "second_trigger_gap_reduced_cases": gap_reduced_cases, "control_failure_cases": control_failure_cases, "first_response_failure_cases": first_response_failure_cases, "head_relation": relation["relation"], "logical_case_count": len(ALL_CASES), "raw_failures": raw_failures, "scientific_analysis_performed": False}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
