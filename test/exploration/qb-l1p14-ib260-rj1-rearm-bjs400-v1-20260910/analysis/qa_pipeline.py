#!/usr/bin/env python3
"""Raw, deck and registered mechanical QA for RJ1 post-slip re-arm navigation."""

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
    BQ400,
    CONTROL_KINDS,
    FIXED,
    AUTH as AUTHORITY_SOURCE_EXPERIMENT,
    MASKS,
    NEW_RUNS,
    REUSE_RUNS,
    RUN_TO_MASK,
    RUN_TO_RJ1,
    REUSE_RUNS as PREPARE_REUSE_RUNS,
    build_deck,
    control_line,
    normalized_deck,
    pre_read_controls,
)
sys.path.insert(0, str(REPO / "scripts"))
from bvmtools.phase import continuous_unwrap, window_indices  # noqa: E402
from bvmtools.raw import read_csv  # noqa: E402


OPTIONAL_UNKNOWN = {"V(IB|XBQ1)"}
ALL_CASES = tuple(REUSE_RUNS) + tuple(NEW_RUNS)
CASE_RJ1 = {**{run_id: 12.0 for run_id in REUSE_RUNS}, **RUN_TO_RJ1}
ORIGINS = OrderedDict(
    (
        ("CONTROL_ORIGIN", {"window": (70e-12, 110e-12), "baseline": (61e-12, 70e-12)}),
        ("FINAL_ORIGIN", {"window": (110e-12, 200e-12), "baseline": (101e-12, 110e-12)}),
    )
)
PRE_SWITCH_WINDOW = (110e-12, 114.5e-12)
RATIO_AREA_TOLERANCE_A_S = 1e-18
RATIO_CANCELLATION_FRACTION = 0.01
BJ1_SECOND_THRESHOLD_TURNS = 1.5
BJ1_ROLLBACK_DROP_TURNS = 0.25
SECOND_SURGE_MIN_SEPARATION_PS = 1.0


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
    root = "runs" if case_id in NEW_RUNS else "references/reused"
    return EXP / root / case_id / "raw.csv"


def deck_path(case_id: str) -> Path:
    root = "runs" if case_id in NEW_RUNS else "references/reused"
    return EXP / root / case_id / "deck.cir"


def source_experiment(case_id: str) -> str:
    if case_id in NEW_RUNS:
        return str(EXP.relative_to(REPO))
    return str(AUTHORITY_SOURCE_EXPERIMENT.relative_to(REPO))


def source_run(case_id: str) -> str:
    if case_id in NEW_RUNS:
        return f"runs/{case_id}"
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


def selected(trace: Any, label: str, window: tuple[float, float]) -> tuple[tuple[float, ...], tuple[float, ...]]:
    indexes = window_indices(trace.time, *window)
    values = tuple(float(value) for value in trace.column(label))
    return tuple(trace.time[index] for index in indexes), tuple(values[index] for index in indexes)


def area(trace: Any, label: str, window: tuple[float, float]) -> float | None:
    times, values = selected(trace, label, window)
    return trapezoid(times, values) if len(times) >= 2 else None


def extrema(trace: Any, label: str, window: tuple[float, float]) -> dict[str, float | None]:
    _times, values = selected(trace, label, window)
    if not values:
        return {"max": None, "min": None, "max_abs": None}
    return {"max": max(values), "min": min(values), "max_abs": max(abs(value) for value in values)}


def phase_origin_diagnostic(trace: Any, label: str, origin_name: str) -> dict[str, Any]:
    spec = ORIGINS[origin_name]
    unwrapped = continuous_unwrap(tuple(trace.column(label)))
    baseline_indices = window_indices(trace.time, *spec["baseline"])
    origin_indices = window_indices(trace.time, *spec["window"])
    if not baseline_indices or not origin_indices:
        return {"status": "UNKNOWN", "reason": "registered phase/baseline window has no samples", "not_event_time": True, "not_event_count": True}
    baseline = unwrapped[baseline_indices[0]]
    relative = tuple((unwrapped[index] - baseline) / (2.0 * math.pi) for index in origin_indices)
    half_index = next((index for index, value in zip(origin_indices, relative) if value >= 0.5), None)
    second_index = next((index for index, value in zip(origin_indices, relative) if value >= BJ1_SECOND_THRESHOLD_TURNS), None)
    max_position = max(range(len(relative)), key=relative.__getitem__)
    max_value = relative[max_position]
    after_max = relative[max_position:]
    rollback = any(value <= max_value - BJ1_ROLLBACK_DROP_TURNS for value in after_max[1:])
    additional_forward = max_value >= BJ1_SECOND_THRESHOLD_TURNS
    return {
        "status": "DERIVED",
        "label": label,
        "origin": origin_name,
        "raw_unit": "rad",
        "display_unit": "turns",
        "conversion": "continuous_unwrap(raw_rad)/(2*pi)",
        "baseline_window_ps": [spec["baseline"][0] * 1e12, spec["baseline"][1] * 1e12],
        "origin_window_ps": [spec["window"][0] * 1e12, spec["window"][1] * 1e12],
        "baseline_reference_time_ps": trace.time[baseline_indices[0]] * 1e12,
        "first_half_turn_timing_diagnostic_ps": trace.time[half_index] * 1e12 if half_index is not None else None,
        "first_half_turn_diagnostic_found": half_index is not None,
        "second_threshold_turns": BJ1_SECOND_THRESHOLD_TURNS,
        "second_threshold_timing_diagnostic_ps": trace.time[second_index] * 1e12 if second_index is not None else None,
        "second_threshold_diagnostic_found": second_index is not None,
        "second_threshold_label": "MECHANICAL_THRESHOLD_ONLY",
        "max_continuous_relative_phase_turns": max(relative),
        "min_continuous_relative_phase_turns": min(relative),
        "final_continuous_relative_phase_turns": relative[-1],
        "time_of_max_forward_phase_ps": trace.time[origin_indices[max_position]] * 1e12,
        "additional_forward_excursion_candidate": additional_forward,
        "rollback_candidate": rollback,
        "only_first_progression_candidate": bool(max_value >= 0.5 and not additional_forward and not rollback),
        "diagnostic_label": "MECHANICAL_DIAGNOSTIC_ONLY",
        "not_event_time": True,
        "not_event_count": True,
        "scientific_interpretation_performed": False,
    }


def zero_crossings(trace: Any, label: str, window: tuple[float, float]) -> dict[str, Any]:
    indexes = window_indices(trace.time, *window)
    values = tuple(float(value) for value in trace.column(label))
    exact: list[float] = []
    transitions: list[float] = []
    for left, right in zip(indexes, indexes[1:]):
        a, b = values[left], values[right]
        if a == 0.0:
            exact.append(trace.time[left] * 1e12)
        if a == 0.0 and b == 0.0:
            continue
        if (a < 0.0 < b) or (a > 0.0 > b):
            # Stored-sample time only; no interpolated crossing is produced.
            transitions.append(trace.time[right] * 1e12)
    if indexes and values[indexes[-1]] == 0.0:
        exact.append(trace.time[indexes[-1]] * 1e12)
    return {
        "status": "DERIVED",
        "label": label,
        "window_ps": [window[0] * 1e12, window[1] * 1e12],
        "exact_zero_sample_times_ps": exact,
        "sign_transition_stored_sample_times_ps": transitions,
        "interpolation": False,
    }


def jtl_progression(trace: Any, origin_name: str) -> dict[str, Any]:
    spec = ORIGINS[origin_name]
    baseline_indices = window_indices(trace.time, *spec["baseline"])
    origin_indices = window_indices(trace.time, *spec["window"])
    first_times: dict[str, float | None] = OrderedDict()
    second_times: dict[str, float | None] = OrderedDict()
    if not baseline_indices or not origin_indices:
        return {"status": "UNKNOWN", "reason": "registered JTL window has no samples", "label": "MECHANICAL_CANDIDATE_ONLY"}
    for stage in range(1, 7):
        label = f"P(B01|XJTL1_{stage})"
        raw = tuple(trace.column(label))
        unwrapped = continuous_unwrap(raw)
        baseline = unwrapped[baseline_indices[0]]
        relative = tuple((unwrapped[index] - baseline) / (2.0 * math.pi) for index in origin_indices)
        first = next((trace.time[index] * 1e12 for index, value in zip(origin_indices, relative) if value >= 0.5), None)
        second = next((trace.time[index] * 1e12 for index, value in zip(origin_indices, relative) if value >= 1.5), None)
        first_times[f"JTL{stage}"] = first
        second_times[f"JTL{stage}"] = second

    def ordered(values: dict[str, float | None]) -> bool:
        return all(value is not None for value in values.values()) and all(
            values[f"JTL{index}"] < values[f"JTL{index + 1}"] for index in range(1, 6)
        )

    first_candidate = ordered(first_times)
    second_candidate = ordered(second_times) and all(
        second_times[f"JTL{stage}"] > first_times[f"JTL{stage}"]
        for stage in range(1, 7)
        if second_times[f"JTL{stage}"] is not None and first_times[f"JTL{stage}"] is not None
    )
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
    times, values = selected(trace, label, window)
    positive = tuple(max(value, 0.0) for value in values)
    negative = tuple(min(value, 0.0) for value in values)
    return {
        "positive_V_s": trapezoid(times, positive) if len(times) >= 2 else None,
        "negative_V_s": trapezoid(times, negative) if len(times) >= 2 else None,
        "window_ps": [window[0] * 1e12, window[1] * 1e12],
        "formula": "trapezoid(actual stored grid, max(V,0) or min(V,0))",
        "status": "DERIVED" if len(times) >= 2 else "UNKNOWN",
    }


def origin_summary(trace: Any, origin_name: str) -> tuple[dict[str, Any], dict[str, float | None]]:
    window = ORIGINS[origin_name]["window"]
    receiver = {
        label: extrema(trace, label, window)
        for label in ("I(L1|XBQ1)", "I(IB|XBQ1)", "I(L2|XBQ1)", "I(RJ1|XBQ1)", "V(RJ1|XBQ1)")
    }
    l1_zero = zero_crossings(trace, "I(L1|XBQ1)", window)
    voltage_times, voltage = selected(trace, "V(RJ1|XBQ1)", window)
    current_indices = window_indices(trace.time, *window)
    current = tuple(float(trace.column("I(RJ1|XBQ1)")[index]) for index in current_indices)
    energy = trapezoid(voltage_times, tuple(v * i for v, i in zip(voltage, current))) if len(voltage_times) >= 2 else None
    receiver.update({
        "I(L1|XBQ1)": {**receiver["I(L1|XBQ1)"], "zero_crossing": l1_zero},
        "I(L2|XBQ1)": receiver["I(L2|XBQ1)"],
        "I(RJ1|XBQ1)": receiver["I(RJ1|XBQ1)"],
        "V(RJ1|XBQ1)": receiver["V(RJ1|XBQ1)"],
    })
    source = {
        "I(B_JSL8)": extrema(trace, "I(B_JSL8)", window),
        "I(LIN|XBQ1)": extrema(trace, "I(LIN|XBQ1)", window),
        "V(QBIN)": extrema(trace, "V(QBIN)", window),
        "V(COMMON_SL)": extrema(trace, "V(COMMON_SL)", window),
        "signed_areas_A_s": {
            "I(B_JSL8)": area(trace, "I(B_JSL8)", window),
            "I(LIN|XBQ1)": area(trace, "I(LIN|XBQ1)", window),
        },
    }
    terminal = {
        "V(JTL6_OUT)_signed_area_V_s": area(trace, "V(JTL6_OUT)", window),
        "I(R_TERM)_signed_area_A_s": area(trace, "I(R_TERM)", window),
        "window_ps": [window[0] * 1e12, window[1] * 1e12],
        "formula": "trapezoid(actual stored time grid, signal)",
        "status": "DERIVED",
        "label": f"{origin_name}_SUPPORT_WINDOW",
    }
    summary = {
        "window_ps": [window[0] * 1e12, window[1] * 1e12],
        "phase_diagnostics": {
            "BJ1": phase_origin_diagnostic(trace, "P(BJ1|XBQ1)", origin_name),
            "BJ2": phase_origin_diagnostic(trace, "P(BJ2|XBQ1)", origin_name),
        },
        "receiver_diagnostics": {
            "descriptives": receiver,
            "BJ1_voltage_area": signed_components(trace, "V(BJ1|XBQ1)", window),
            "RJ1_dissipated_energy": {
                "value_J": energy,
                "formula": "trapezoid(actual stored grid, V(RJ1|XBQ1)*I(RJ1|XBQ1))",
                "orientation": "as emitted by registered branch labels; no sign correction",
                "window_ps": [window[0] * 1e12, window[1] * 1e12],
                "status": "DERIVED" if energy is not None else "UNKNOWN",
            },
        },
        "source_side_diagnostics": source,
        "jtl_progression_diagnostics": jtl_progression(trace, origin_name),
        "terminal_diagnostics": terminal,
    }
    ratio_inputs = {
        "I(B_JSL8)": area(trace, "I(B_JSL8)", PRE_SWITCH_WINDOW),
        "I(LIN|XBQ1)": area(trace, "I(LIN|XBQ1)", PRE_SWITCH_WINDOW),
    }
    return summary, ratio_inputs


def whole_run_terminal(trace: Any) -> dict[str, Any]:
    window = (0.0, 200e-12)
    return {
        "V(JTL6_OUT)_signed_area_V_s": area(trace, "V(JTL6_OUT)", window),
        "I(R_TERM)_signed_area_A_s": area(trace, "I(R_TERM)", window),
        "window_ps": [0.0, 200.0],
        "formula": "trapezoid(actual stored time grid, signal)",
        "label": "WHOLE_RUN_TOTAL_ONLY",
        "not_population_count": True,
        "status": "DERIVED",
    }


def post_first_bj1_rearm_diagnostics(trace: Any) -> dict[str, Any]:
    """Record post-anchor navigation arithmetic without classifying events."""

    final_phase = phase_origin_diagnostic(trace, "P(BJ1|XBQ1)", "FINAL_ORIGIN")
    final_bj2_phase = phase_origin_diagnostic(trace, "P(BJ2|XBQ1)", "FINAL_ORIGIN")
    final_window = ORIGINS["FINAL_ORIGIN"]["window"]
    final_bj1_area = signed_components(trace, "V(BJ1|XBQ1)", final_window)
    anchor_ps = final_phase.get("first_half_turn_timing_diagnostic_ps")
    if anchor_ps is None:
        return {
            "status": "UNKNOWN",
            "t_BJ1_half_ps": None,
            "BJ1_max_turns": final_phase.get("max_continuous_relative_phase_turns"),
            "BJ1_final_turns": final_phase.get("final_continuous_relative_phase_turns"),
            "BJ1_positive_voltage_area": final_bj1_area.get("positive_V_s"),
            "BJ1_negative_voltage_area": final_bj1_area.get("negative_V_s"),
            "L1_post_anchor_min": None,
            "L1_post_anchor_max": None,
            "L1_sign_transitions": [],
            "L1_first_negative_to_positive_time_ps": None,
            "post_first_bj1_L1_negative_to_positive_candidate": "UNKNOWN",
            "L2_post_anchor_min": None,
            "L2_post_anchor_max": None,
            "L2_post_anchor_peak_time_ps": None,
            "second_L2_surge_proxy": "UNKNOWN",
            "BJ2_max_turns": final_bj2_phase.get("max_continuous_relative_phase_turns"),
            "BJ2_final_turns": final_bj2_phase.get("final_continuous_relative_phase_turns"),
            "BJ2_second_threshold_candidate": "UNKNOWN",
            "JTL_threshold_diagnostics": {"CONTROL_ORIGIN": None, "FINAL_ORIGIN": None},
            "label": "MECHANICAL_REARM_PROXY_ONLY",
            "reason": "no FINAL-origin BJ1 +0.5-turn navigation anchor",
        }
    anchor_s = float(anchor_ps) * 1e-12
    post_window = (anchor_s, 200e-12)
    indexes = window_indices(trace.time, *post_window)
    if len(indexes) < 2:
        return {
            "status": "UNKNOWN",
            "t_BJ1_half_ps": anchor_ps,
            "post_anchor_window_ps": [anchor_ps, 200.0],
            "BJ1_max_turns": final_phase.get("max_continuous_relative_phase_turns"),
            "BJ1_final_turns": final_phase.get("final_continuous_relative_phase_turns"),
            "BJ1_positive_voltage_area": final_bj1_area.get("positive_V_s"),
            "BJ1_negative_voltage_area": final_bj1_area.get("negative_V_s"),
            "L1_post_anchor_min": None,
            "L1_post_anchor_max": None,
            "L1_sign_transitions": [],
            "L1_first_negative_to_positive_time_ps": None,
            "post_first_bj1_L1_negative_to_positive_candidate": "UNKNOWN",
            "L2_post_anchor_min": None,
            "L2_post_anchor_max": None,
            "L2_post_anchor_peak_time_ps": None,
            "second_L2_surge_proxy": "UNKNOWN",
            "BJ2_max_turns": final_bj2_phase.get("max_continuous_relative_phase_turns"),
            "BJ2_final_turns": final_bj2_phase.get("final_continuous_relative_phase_turns"),
            "BJ2_second_threshold_candidate": "UNKNOWN",
            "JTL_threshold_diagnostics": {"CONTROL_ORIGIN": None, "FINAL_ORIGIN": None},
            "label": "MECHANICAL_REARM_PROXY_ONLY",
            "reason": "post-anchor window has fewer than two stored samples",
        }

    l1 = tuple(float(trace.column("I(L1|XBQ1)")[index]) for index in indexes)
    l2 = tuple(float(trace.column("I(L2|XBQ1)")[index]) for index in indexes)
    times_ps = tuple(trace.time[index] * 1e12 for index in indexes)
    sign_transitions: list[dict[str, Any]] = []
    negative_to_positive: list[float] = []
    for position, (left, right) in enumerate(zip(l1, l1[1:])):
        if left == 0.0:
            sign_transitions.append({"time_ps": times_ps[position], "direction": "exact_zero_sample"})
        if (left < 0.0 < right) or (left > 0.0 > right):
            direction = "negative_to_positive" if left < 0.0 < right else "positive_to_negative"
            sign_transitions.append({"time_ps": times_ps[position + 1], "direction": direction, "interpolation": False})
            if direction == "negative_to_positive":
                negative_to_positive.append(times_ps[position + 1])
    if l1[-1] == 0.0:
        sign_transitions.append({"time_ps": times_ps[-1], "direction": "exact_zero_sample"})

    local_maxima: list[dict[str, float]] = []
    for position in range(1, len(l2) - 1):
        if l2[position] > l2[position - 1] and l2[position] > l2[position + 1]:
            local_maxima.append({"time_ps": times_ps[position], "value_A": l2[position]})
    second_surge = any(
        local_maxima[right]["time_ps"] - local_maxima[left]["time_ps"] >= SECOND_SURGE_MIN_SEPARATION_PS
        for left in range(len(local_maxima))
        for right in range(left + 1, len(local_maxima))
    )
    largest_local = max(local_maxima, key=lambda item: item["value_A"]) if local_maxima else None
    peak_position = max(range(len(l2)), key=l2.__getitem__)
    return {
        "status": "DERIVED",
        "t_BJ1_half_ps": anchor_ps,
        "anchor_label": "first FINAL-origin BJ1 +0.5-turn timing diagnostic; not an event onset",
        "post_anchor_window_ps": [anchor_ps, 200.0],
        "BJ1_max_turns": final_phase.get("max_continuous_relative_phase_turns"),
        "BJ1_final_turns": final_phase.get("final_continuous_relative_phase_turns"),
        "BJ1_positive_voltage_area": final_bj1_area.get("positive_V_s"),
        "BJ1_negative_voltage_area": final_bj1_area.get("negative_V_s"),
        "L1_post_anchor_min": min(l1),
        "L1_post_anchor_max": max(l1),
        "L1_sign_transitions": sign_transitions,
        "L1_first_negative_to_positive_time_ps": negative_to_positive[0] if negative_to_positive else None,
        "post_first_bj1_L1_negative_to_positive_candidate": True if negative_to_positive else False,
        "rearm_label": "MECHANICAL_REARM_PROXY_ONLY",
        "L2_post_anchor_min": min(l2),
        "L2_post_anchor_max": max(l2),
        "L2_post_anchor_peak_time_ps": times_ps[peak_position],
        "L2_largest_local_maximum": largest_local,
        "L2_local_maxima": local_maxima,
        "second_L2_surge_proxy": second_surge,
        "second_surge_label": "MECHANICAL_SECOND_SURGE_PROXY_ONLY",
        "second_surge_min_separation_ps": SECOND_SURGE_MIN_SEPARATION_PS,
        "BJ2_max_turns": final_bj2_phase.get("max_continuous_relative_phase_turns"),
        "BJ2_final_turns": final_bj2_phase.get("final_continuous_relative_phase_turns"),
        "BJ2_second_threshold_candidate": final_bj2_phase.get("second_threshold_diagnostic_found", False),
        "BJ2_second_threshold_timing_diagnostic_ps": final_bj2_phase.get("second_threshold_timing_diagnostic_ps"),
        "BJ2_second_threshold_label": "MECHANICAL_THRESHOLD_ONLY",
        "JTL_threshold_diagnostics": {"CONTROL_ORIGIN": None, "FINAL_ORIGIN": "see FINAL_ORIGIN.jtl_progression_diagnostics"},
        "post_anchor_source_support": {
            "I(B_JSL8)_max_abs_A": max(abs(float(trace.column("I(B_JSL8)")[index])) for index in indexes),
            "I(LIN|XBQ1)_max_abs_A": max(abs(float(trace.column("I(LIN|XBQ1)")[index])) for index in indexes),
            "I(B_JSL8)_signed_area_A_s": area(trace, "I(B_JSL8)", post_window),
            "I(LIN|XBQ1)_signed_area_A_s": area(trace, "I(LIN|XBQ1)", post_window),
            "raw_direct": True,
            "cropped_raw_artifact": False,
        },
        "not_event_count": True,
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
    times, values = selected(trace, label, window)
    return trapezoid(times, tuple(abs(value) for value in values)) if len(times) >= 2 else None


def ratio_diagnostics(traces: dict[str, Any], inputs: dict[str, dict[str, float | None]]) -> dict[str, Any]:
    output: dict[str, Any] = OrderedDict()
    for rj1 in (12.0, 16.0, 24.0, 32.0):
        mask0001 = next(run_id for run_id in ALL_CASES if CASE_RJ1[run_id] == rj1 and run_id.rsplit("_", 1)[1] == "0001")
        mask0011 = next(run_id for run_id in ALL_CASES if CASE_RJ1[run_id] == rj1 and run_id.rsplit("_", 1)[1] == "0011")
        output[f"RJ1_{int(rj1)}"] = {
            "RJ1_ohm": rj1,
            "mask_0001_case_id": mask0001,
            "mask_0011_case_id": mask0011,
            "ratio_semantics": "0011 numerator / 0001 denominator; mechanical diagnostic only",
            "MECHANICAL_PRE_SWITCH_PROXY": {
                "window_ps": [110.0, 114.5],
                "I(B_JSL8)_signed_area_ratio": ratio_record(
                    inputs[mask0011]["I(B_JSL8)"], inputs[mask0001]["I(B_JSL8)"],
                    denominator_abs_area=absolute_area(traces[mask0001], "I(B_JSL8)", PRE_SWITCH_WINDOW),
                ),
                "I(LIN)_signed_area_ratio": ratio_record(
                    inputs[mask0011]["I(LIN|XBQ1)"], inputs[mask0001]["I(LIN|XBQ1)"],
                    denominator_abs_area=absolute_area(traces[mask0001], "I(LIN|XBQ1)", PRE_SWITCH_WINDOW),
                ),
                "label": "MECHANICAL_PRE_SWITCH_PROXY; not proof of population scaling",
            },
        }
    return output


def deck_diff() -> dict[str, Any]:
    failures: list[str] = []
    normalized: set[tuple[str, ...]] = set()
    pre_read: set[tuple[str, ...]] = set()
    pair_checks: dict[str, Any] = {}
    records: dict[str, Any] = {}
    bq = BQ400.read_text(encoding="utf-8")
    if "BJs 1 2 jjmit area=4" not in bq or "BJs 1 2 jjmit area=3" in bq:
        failures.append("BJS400 source is not exactly area=4")
    for run_id in NEW_RUNS:
        text = deck_path(run_id).read_text(encoding="utf-8")
        rj1 = RUN_TO_RJ1[run_id]
        mask = RUN_TO_MASK[run_id]
        for required in (".param L1_VALUE=1.4p", ".param IB_VALUE=260u", f".param RJ1_VALUE={rj1:g}", ".tran 0.1p 200p", "P(BJS|XBQ1) V(BJS|XBQ1) I(BJS|XBQ1)"):
            if required not in text:
                failures.append(f"{run_id}: missing {required}")
        if any(text.count(f"XBVM{index} ") != 1 for index in range(1, 5)):
            failures.append(f"{run_id}: BVM topology count mismatch")
        for instance in range(1, 5):
            for kind in CONTROL_KINDS:
                if control_line(instance, kind, mask[instance - 1] == "1") not in text:
                    failures.append(f"{run_id}: control mismatch {kind}{instance}")
        normalized.add(normalized_deck(text))
        pre_read.add(pre_read_controls(text))
        records[run_id] = {"rj1_ohm": rj1, "mask": mask, "deck_sha256": sha256(deck_path(run_id)), "deck_bytes": deck_path(run_id).stat().st_size}
    if len(normalized) != 1:
        failures.append("new decks differ outside RJ1 and final-read controls")
    if len(pre_read) != 1:
        failures.append("new controls differ before 110ps")
    for rj1 in (16.0, 24.0, 32.0):
        pair = tuple(run_id for run_id in NEW_RUNS if RUN_TO_RJ1[run_id] == rj1)
        if len(pair) != 2:
            failures.append(f"RJ1={rj1}: mask pair incomplete")
        else:
            if normalized_deck(deck_path(pair[0]).read_text(encoding="utf-8")) != normalized_deck(deck_path(pair[1]).read_text(encoding="utf-8")):
                failures.append(f"RJ1={rj1}: mask pair has non-mask deck difference")
            pair_checks[str(int(rj1))] = {"mask_pair": pair, "pre_110ps_equal": pre_read_controls(deck_path(pair[0]).read_text(encoding="utf-8")) == pre_read_controls(deck_path(pair[1]).read_text(encoding="utf-8"))}
    historical_failures: list[str] = []
    for run_id in REUSE_RUNS:
        source_text = deck_path(run_id).read_text(encoding="utf-8")
        mask = run_id.rsplit("_", 1)[1]
        expected = build_deck(12.0, mask)
        if normalized_deck(source_text) != normalized_deck(expected) or pre_read_controls(source_text) != pre_read_controls(expected):
            historical_failures.append(run_id)
    if historical_failures:
        failures.append("historical RJ1=12 deck comparability failed: " + ",".join(historical_failures))
    return {
        "schema": "bjs400-rj1-rearm-deck-diff-qa-v1",
        "status": "PASS" if not failures else "FAIL",
        "new_run_count": len(NEW_RUNS),
        "reused_case_count": len(REUSE_RUNS),
        "fixed_L1_pH": FIXED["L1_pH"],
        "fixed_IBias_uA": FIXED["IBias_uA"],
        "fixed_BJS_area": 4,
        "new_RJ1_values_ohm": [16.0, 24.0, 32.0],
        "same_mask_only_RJ1_difference": len(normalized) == 1,
        "mask_pair_only_final_read_difference": len(pre_read) == 1,
        "normalized_new_decks_identical": len(normalized) == 1,
        "historical_deck_comparability": "PASS" if not historical_failures else "FAIL",
        "pair_checks": pair_checks,
        "runs": records,
        "failures": failures,
    }


def main() -> int:
    preflight = json.loads((EXP / "analysis/preflight.json").read_text(encoding="utf-8"))
    relation = head_relation(str(preflight["head"]))
    execution = json.loads((EXP / "qa/execution_summary.json").read_text(encoding="utf-8"))
    execution_ok = (
        execution.get("status") == "PASS"
        and execution.get("solver_solve_invocations") == 6
        and execution.get("exact_new_physical_solve_count") == 6
        and execution.get("reused_physical_case_count") == 2
        and execution.get("unauthorized_extra_solves") == 0
        and execution.get("failed_runs") == []
    )
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
        raw_records[case_id] = {
            "case_id": case_id,
            "path": str(path.relative_to(REPO)),
            "sha256": pre_hashes[case_id],
            "bytes": path.stat().st_size,
            "header_count": len(trace.headers),
            "sample_count": trace.sample_count,
            "first_timestamp_s": trace.time[0],
            "last_timestamp_s": trace.time[-1],
            "dt_min_s": min(trace.dt),
            "dt_max_s": max(trace.dt),
            "stored_time_grid_sha256": grid_hash,
            "strictly_increasing_time": qa["strictly_increasing_time"],
            "finite_values": qa["nan_inf_status"] == "PASS",
            "duplicate_columns": trace.duplicate_columns,
            "required_probe_status": "UNKNOWN" if unknown and not missing_required else ("PASS" if not missing else "FAIL"),
            "missing_probes": missing,
            "unknown_probes": unknown,
            "physical_solve_this_experiment": case_id in NEW_RUNS,
            "raw_immutable": True,
        }
        try:
            origin_records: dict[str, Any] = {}
            origin_inputs: dict[str, float | None] = {}
            for origin_name in ORIGINS:
                origin_records[origin_name], origin_inputs = origin_summary(trace, origin_name)
            post_rearm = post_first_bj1_rearm_diagnostics(trace)
            post_rearm["JTL_threshold_diagnostics"] = {
                origin_name: origin_records[origin_name]["jtl_progression_diagnostics"]
                for origin_name in ORIGINS
            }
            cases[case_id] = {
                "case_id": case_id,
                "L1_pH": FIXED["L1_pH"],
                "IBias_uA": FIXED["IBias_uA"],
                "RJ1_ohm": CASE_RJ1[case_id],
                "mask": case_id.rsplit("_", 1)[1],
                "source_experiment": source_experiment(case_id),
                "source_run": source_run(case_id),
                "physical_solve_this_experiment": case_id in NEW_RUNS,
                "scientific_interpretation_performed": False,
                "CONTROL_ORIGIN": origin_records["CONTROL_ORIGIN"],
                "FINAL_ORIGIN": origin_records["FINAL_ORIGIN"],
                "POST_FIRST_BJ1_REARM_DIAGNOSTICS": post_rearm,
                "control_complete_downstream_candidate": {
                    "value": origin_records["CONTROL_ORIGIN"]["jtl_progression_diagnostics"]["complete_progression_candidate"],
                    "label": "MECHANICAL_CANDIDATE_ONLY",
                },
                "terminal_control_area": origin_records["CONTROL_ORIGIN"]["terminal_diagnostics"],
                "terminal_final_area": origin_records["FINAL_ORIGIN"]["terminal_diagnostics"],
                "terminal_whole_run_area": whole_run_terminal(trace),
                "whole_run_terminal": whole_run_terminal(trace),
                "notes": [
                    "CONTROL_ORIGIN and FINAL_ORIGIN are separate mechanical windows.",
                    "JTL progression fields are MECHANICAL_CANDIDATE_ONLY, not event/SFQ counts.",
                    "Whole-run terminal area is WHOLE_RUN_TOTAL_ONLY and not a population count.",
                    "Continuous phase turns are not SFQ counts or fluxoid counts.",
                ],
                "raw_provenance": {"path": str(path.relative_to(REPO)), "sha256": pre_hashes[case_id]},
            }
            ratio_inputs[case_id] = origin_inputs
        except Exception as exc:
            raw_failures.append(f"{case_id}: mechanical arithmetic failure: {exc}")
    post_hashes = {case_id: sha256(raw_path(case_id)) for case_id in pre_hashes}
    raw_ok = not raw_failures and len(traces) == len(ALL_CASES) and len(grid_hashes) == 1 and pre_hashes == post_hashes
    raw_qa = {
        "schema": "bjs400-rj1-rearm-raw-qa-v1",
        "status": "PASS" if raw_ok else "FAIL",
        "artifact_validity": "VALID" if raw_ok else "INVALID",
        "experiment_id": EXP.name,
        "created_at_local": now(),
        "head": relation["head"],
        "execution_status": "PASS" if execution_ok else "FAIL",
        "new_physical_solve_count": 6,
        "reused_physical_case_count": 2,
        "exact_logical_case_count": 8,
        "unauthorized_extra_solves": 0,
        "cases": raw_records,
        "pre_analysis_sha256": pre_hashes,
        "post_analysis_sha256": post_hashes,
        "raw_unchanged_pre_to_post": pre_hashes == post_hashes,
        "common_time_grid": len(grid_hashes) == 1,
        "stored_grid_hashes": sorted(grid_hashes),
        "required_probe_missing_is_not_fabricated": True,
        "raw_files_modified": 0,
        "scientific_analysis_performed": False,
        "failures": raw_failures,
    }
    decks = deck_diff()
    ratios = ratio_diagnostics(traces, ratio_inputs) if raw_ok else {}
    mechanical_status = "PASS" if raw_ok and decks["status"] == "PASS" and len(cases) == len(ALL_CASES) else "FAIL"
    mechanical_summary = {
        "schema": "bjs400-rj1-rearm-mechanical-summary-v2",
        "experiment_id": EXP.name,
        "created_at_local": now(),
        "status": mechanical_status,
        "scientific_interpretation_performed": False,
        "fixed_point": {"L1_pH": 1.4, "IBias_uA": 260.0, "BJS_area": 4, "BJS_Ic_uA": 400.0},
        "rj1_values_ohm": [12.0, 16.0, 24.0, 32.0],
        "masks": list(MASKS),
        "logical_case_count": 8,
        "historical_reuse_count": 2,
        "new_physical_solve_count": 6,
        "case_order": list(ALL_CASES),
        "phase_convention": "raw P radians; independently continuous_unwrap(raw)/(2*pi) for diagnostic turns only",
        "origin_windows": {
            name: {"window_ps": [spec["window"][0] * 1e12, spec["window"][1] * 1e12], "baseline_ps": [spec["baseline"][0] * 1e12, spec["baseline"][1] * 1e12]}
            for name, spec in ORIGINS.items()
        },
        "pre_switch_proxy_window_ps": [110.0, 114.5],
        "area_semantics": "trapezoid on actual stored time grid; half-open windows; no interpolation/resampling",
        "dedicated_sections": ["CONTROL_ORIGIN", "FINAL_ORIGIN", "POST_FIRST_BJ1_REARM_DIAGNOSTICS"],
        "post_first_bj1_rearm_policy": {
            "anchor": "first FINAL-origin BJ1 +0.5-turn timing diagnostic",
            "l1_label": "MECHANICAL_REARM_PROXY_ONLY",
            "l2_label": "MECHANICAL_SECOND_SURGE_PROXY_ONLY",
            "bj2_label": "MECHANICAL_THRESHOLD_ONLY",
            "jtl_label": "MECHANICAL_CANDIDATE_ONLY",
            "second_surge_min_separation_ps": SECOND_SURGE_MIN_SEPARATION_PS,
            "no_event_or_sfq_classification": True,
        },
        "ratio_policy": {
            "numerator_denominator": "0011 / 0001",
            "signed_area_tolerance_A_s": RATIO_AREA_TOLERANCE_A_S,
            "cancellation_fraction": RATIO_CANCELLATION_FRACTION,
            "ambiguous_status": "UNKNOWN",
        },
        "post_first_bj1_rearm_diagnostics": {
            "section_name": "POST_FIRST_BJ1_REARM_DIAGNOSTICS",
            "anchor": "first FINAL-origin BJ1 +0.5-turn timing diagnostic",
            "l1_negative_to_positive_label": "MECHANICAL_REARM_PROXY_ONLY",
            "l2_second_surge_label": "MECHANICAL_SECOND_SURGE_PROXY_ONLY",
            "bj2_second_threshold_label": "MECHANICAL_THRESHOLD_ONLY",
            "jtl_candidate_label": "MECHANICAL_CANDIDATE_ONLY",
            "second_surge_min_separation_ps": SECOND_SURGE_MIN_SEPARATION_PS,
            "no_event_or_sfq_classification": True,
        },
        "cases": cases,
        "ratio_diagnostics": ratios,
        "notes": [
            "CONTROL_ORIGIN and FINAL_ORIGIN remain separate; no control response is combined with final response.",
            "POST_FIRST_BJ1_REARM_DIAGNOSTICS uses a stored-time BJ1 +0.5 navigation anchor and is not proof of physical re-arm.",
            "JTL stage timing candidates use fixed thresholds and are MECHANICAL_CANDIDATE_ONLY.",
            "No field is an event count, SFQ count, control PASS/FAIL, threshold, optimum or mechanism conclusion.",
            "Scientific interpretation is NOT_PERFORMED.",
        ],
    }
    provenance = {
        "schema": "bjs400-rj1-rearm-provenance-v1",
        "experiment_id": EXP.name,
        "head_at_qa": relation["head"],
        "preflight": "analysis/preflight.json",
        "source_manifest": "SOURCE_MANIFEST.json",
        "reuse_manifest": "REUSED_REFERENCE_MANIFEST.json",
        "execution_summary": "qa/execution_summary.json",
        "mechanical_summary": "mechanical_summary.json",
        "solver": "build/josim-cli",
        "new_runs": {
            run_id: {
                "deck": str(deck_path(run_id).relative_to(REPO)),
                "deck_sha256": sha256(deck_path(run_id)),
                "raw": str(raw_path(run_id).relative_to(REPO)),
                "raw_sha256": pre_hashes.get(run_id),
                "metadata": str((EXP / "runs" / run_id / "metadata.json").relative_to(REPO)),
                "run_log": str((EXP / "runs" / run_id / "run.log").relative_to(REPO)),
                "physical_solve_this_experiment": True,
            }
            for run_id in NEW_RUNS
        },
        "reused_runs": {
            run_id: {
                "reference": str((EXP / "references/reused" / run_id).relative_to(REPO)),
                "source_experiment": str(AUTHORITY_SOURCE_EXPERIMENT.relative_to(REPO)),
                "source_run": f"runs/{run_id}",
                "raw_sha256": pre_hashes.get(run_id),
                "deck_sha256": sha256(deck_path(run_id)),
                "physical_solve_this_experiment": False,
            }
            for run_id in REUSE_RUNS
        },
        "runs": {},
        "all_logical_cases": list(ALL_CASES),
        "scientific_analysis_performed": False,
    }
    provenance["runs"] = {**provenance["new_runs"], **provenance["reused_runs"]}
    transformations = {
        "schema": "bjs400-rj1-rearm-transformation-registry-v1",
        "raw_immutable": True,
        "scientific_analysis_performed": False,
        "transformations": [
            {"name": "origin_separation", "operation": "separate CONTROL_ORIGIN [70,110) and FINAL_ORIGIN [110,200) windows", "scope": "mechanical navigation only"},
            {"name": "phase_display", "operation": "continuous_unwrap(raw_rad)/(2*pi)", "scope": "diagnostic/display only", "not_event_count": True},
            {"name": "jtl_candidate_navigation", "operation": "fixed +0.5 and +1.5 threshold timing across P(B01) stage order", "scope": "MECHANICAL_CANDIDATE_ONLY", "not_event_count": True},
            {"name": "area_integration", "operation": "trapezoid on actual stored time values; half-open registered windows", "scope": "mechanical arithmetic only", "interpolation": False},
            {"name": "standalone_plot_input", "operation": "raw.csv direct; no crop/resample/derived CSV", "scope": "visualization"},
            {"name": "comparison_plot_input", "operation": "temporary full-run merged CSV under /tmp only; deleted after render", "scope": "visualization"},
        ],
    }
    write_json(EXP / "qa/raw_qa.json", raw_qa)
    write_json(EXP / "qa/deck_diff_qa.json", decks)
    write_json(EXP / "mechanical_summary.json", mechanical_summary)
    write_json(EXP / "qa/provenance.json", provenance)
    write_json(EXP / "qa/transformation_registry.json", transformations)
    result = {
        "status": "PASS" if raw_ok and decks["status"] == "PASS" and execution_ok and relation["status"] == "PASS" and mechanical_status == "PASS" else "FAIL",
        "execution_status": "PASS" if execution_ok else "FAIL",
        "raw_status": raw_qa["status"],
        "deck_status": decks["status"],
        "mechanical_summary_status": mechanical_status,
        "head_relation": relation["relation"],
        "logical_case_count": len(ALL_CASES),
        "raw_failures": raw_failures,
        "scientific_analysis_performed": False,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
