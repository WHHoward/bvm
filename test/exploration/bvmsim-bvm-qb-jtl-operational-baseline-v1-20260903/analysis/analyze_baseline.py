#!/usr/bin/env python3
"""Analyze the original-BQ operational baseline.

This module is intentionally a thin task-local report layer.  CSV parsing,
phase unwrapping, same-JJ phase/area arithmetic, strict local event lists and
KCL residual arithmetic come from the shared ``bvmtools`` modules.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import subprocess
import sys
from collections import OrderedDict, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

from bvmtools.kcl import kcl_window_metrics, linear_kcl_residual  # noqa: E402
from bvmtools.phase import TAU, continuous_unwrap, window_indices  # noqa: E402
from bvmtools.provenance import file_snapshot, git_snapshot, sha256_file, solver_provenance  # noqa: E402
from bvmtools.raw import RawTrace, read_csv  # noqa: E402
from bvmtools.sfq import PHI0, StrictLocalEventSpec, strict_event_list  # noqa: E402
from bvmtools.waveform import trapezoid_integral, waveform_window_metrics  # noqa: E402


PROFILE = REPO / "docs/research/BVMSIM_0P1PS_OPERATIONAL_PROFILE_V1.md"
BOUNDARY = REPO / "docs/research/BOUNDARY_SPEC_V2.md"
METRIC_SPEC = REPO / "docs/research/METRIC_SPEC_V2.md"
SOLVER = REPO / "build/josim-cli"
RENDERER = REPO / "scripts/josim-plot2.py"
EXECUTION_OUTCOMES = EXP / "analysis/execution_outcomes.json"

WINDOWS_PS: "OrderedDict[str, tuple[float, float]]" = OrderedDict(
    (
        ("PRE", (0.0, 50.0)),
        ("WRITE0", (50.0, 70.0)),
        ("READ0", (70.0, 90.0)),
        ("WRITE1", (90.0, 110.0)),
        ("READ1", (110.0, 170.0)),
        ("TAIL", (170.0, 200.0)),
    )
)
SINGLE_READ = (70.0, 140.0)
SINGLE_TAIL = (140.0, 200.0)
SINGLE_WINDOWS_PS: "OrderedDict[str, tuple[float, float]]" = OrderedDict(
    (
        ("PRE", (0.0, 50.0)),
        ("WRITE", (50.0, 70.0)),
        ("READ", SINGLE_READ),
        ("TAIL", SINGLE_TAIL),
    )
)
COUNT_TOLERANCE_TURNS = 0.25
PHASE_AREA_RESIDUAL_ABS_FLOOR = 0.05
PHASE_AREA_RESIDUAL_RELATIVE = 0.10
RETRAP_P2P_TURNS = 0.25


def json_write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def raw_path_for(record: dict[str, Any]) -> tuple[Path, str]:
    declared = REPO / record["raw"]
    # A probe-completeness repair is an immutable later attempt.  Prefer it
    # for the two single-JTL runs while retaining attempt-01 below as history.
    preferred_attempt = declared.parent.parent / "attempt-02" / "raw" / declared.name
    if record["run_id"] in {"S0-J", "S1-J"} and preferred_attempt.is_file():
        return preferred_attempt, "attempt-02-completed-jtl-probes"
    if declared.is_file():
        return declared, "declared"
    attempt = declared.parent.parent / "attempt-02" / "raw" / declared.name
    if attempt.is_file():
        return attempt, "attempt-02-corrected-command"
    raise FileNotFoundError(f"no raw for {record['run_id']}: {declared}")


def deck_path_for(record: dict[str, Any], raw_path: Path, raw_origin: str) -> Path:
    if raw_origin == "attempt-02-completed-jtl-probes":
        candidate = raw_path.parent.parent / "deck.cir"
        if candidate.is_file():
            return candidate
    return REPO / record["deck"]


def execution_artifacts(run_id: str, raw_path: Path, outcomes: dict[str, Any]) -> dict[str, Any]:
    """Bind each selected raw to its command result and solver log."""

    run_dir = raw_path.parent.parent
    command_path = run_dir / "logs/command.txt"
    log_candidates = [run_dir / "logs/run-01.log", run_dir / "logs/run-01.csv"]
    log_candidates.extend(sorted((run_dir / "logs").glob("run-01.*")))
    solver_log = next((path for path in log_candidates if path.is_file()), None)
    selected = outcomes.get("selected_runs", {}).get(run_id, {})
    recorded_exit = selected.get("exit_code")
    command_exit = None
    if command_path.is_file():
        match = re.search(r"(?m)^exit_code:\s*(-?\d+)\s*$", command_path.read_text(encoding="utf-8"))
        if match:
            command_exit = int(match.group(1))
    if recorded_exit is not None and command_exit is not None and int(recorded_exit) != command_exit:
        raise RuntimeError(f"exit-code provenance mismatch for {run_id}: outcomes={recorded_exit}, command={command_exit}")
    exit_code = recorded_exit if recorded_exit is not None else command_exit
    if exit_code is None:
        raise RuntimeError(f"no recorded exit code for selected run {run_id}")
    if solver_log is None:
        raise RuntimeError(f"no solver log for selected run {run_id}: {run_dir / 'logs'}")
    return {
        "command_log": str(command_path.relative_to(REPO)) if command_path.is_file() else None,
        "command_log_sha256": sha256(command_path) if command_path.is_file() else None,
        "solver_log": str(solver_log.relative_to(REPO)),
        "solver_log_sha256": sha256(solver_log),
        "exit_code": int(exit_code),
        "exit_code_source": "execution_outcomes.json" if command_exit is None else "execution_outcomes.json_and_command_log",
        "execution_status": "COMPLETED" if int(exit_code) == 0 else "FAILED",
    }


def sig(trace: RawTrace, label: str) -> tuple[float, ...]:
    return trace.column(label)  # type: ignore[return-value]


def window_s(name: str, *, single: bool = False) -> tuple[float, float]:
    if single:
        if name == "READ":
            return SINGLE_READ[0] * 1e-12, SINGLE_READ[1] * 1e-12
        if name == "TAIL":
            return SINGLE_TAIL[0] * 1e-12, SINGLE_TAIL[1] * 1e-12
    left, right = WINDOWS_PS[name]
    return left * 1e-12, right * 1e-12


def descriptor(trace: RawTrace, label: str, window: tuple[float, float]) -> dict[str, float | int | str]:
    values = sig(trace, label)
    indices = window_indices(trace.time, *window)
    selected = [float(values[index]) for index in indices]
    integral = trapezoid_integral(selected, [trace.time[index] for index in indices])
    return {
        "label": label,
        "sample_count": len(selected),
        "mean_uA": sum(selected) / len(selected) * 1e6,
        "rms_uA": math.sqrt(sum(value * value for value in selected) / len(selected)) * 1e6,
        "min_uA": min(selected) * 1e6,
        "max_uA": max(selected) * 1e6,
        "peak_abs_uA": max(abs(value) for value in selected) * 1e6,
        "p2p_uA": (max(selected) - min(selected)) * 1e6,
        "integral_pC": integral * 1e12,
        "window_first_ps": trace.time[indices[0]] * 1e12,
        "window_last_ps": trace.time[indices[-1]] * 1e12,
    }


def phase_area(trace: RawTrace, phase_label: str, voltage_label: str, window: tuple[float, float]) -> dict[str, Any]:
    phase_raw = sig(trace, phase_label)
    voltage = sig(trace, voltage_label)
    indices = window_indices(trace.time, *window)
    unwrapped = continuous_unwrap(phase_raw)
    start, end = indices[0], indices[-1]
    phase_delta_rad = unwrapped[end] - unwrapped[start]
    area_wb = trapezoid_integral(
        [voltage[index] for index in indices],
        [trace.time[index] for index in indices],
    )
    phase_turns = phase_delta_rad / TAU
    area_turns = area_wb / PHI0
    residual = phase_turns - area_turns
    return {
        "phase_column": phase_label,
        "voltage_column": voltage_label,
        "phase_delta_rad": phase_delta_rad,
        "phase_delta_turns": phase_turns,
        "voltage_area_wb": area_wb,
        "voltage_area_over_phi0": area_turns,
        "signed_phase_area_residual_turns": residual,
        "phase_area_consistent": abs(residual) <= max(
            PHASE_AREA_RESIDUAL_ABS_FLOOR,
            PHASE_AREA_RESIDUAL_RELATIVE * max(abs(phase_turns), abs(area_turns), 1.0),
        ),
        "window_first_ps": trace.time[start] * 1e12,
        "window_last_ps": trace.time[end] * 1e12,
        "sample_count": len(indices),
        "raw_phase_unit": "rad",
        "display_conversion": "continuous_unwrap(rad)/(2*pi)",
        "branch_orientation": "direct JoSIM branch P/V mapping; voltage_to_phase_sign=+1; reporting_direction=+1",
    }


def phase_crossing_markers(trace: RawTrace, phase_label: str, window: tuple[float, float]) -> dict[str, Any]:
    """Record integer phase-displacement crossings as timing markers only.

    These markers use the actual stored grid and linear interpolation between
    adjacent samples.  They are deliberately not an SFQ event detector or an
    event count: a running phase trajectory can cross several integer levels.
    """

    phase_raw = sig(trace, phase_label)
    indices = window_indices(trace.time, *window)
    unwrapped = continuous_unwrap(phase_raw)
    base = unwrapped[indices[0]]
    displacement = [(unwrapped[index] - base) / TAU for index in indices]
    markers: list[dict[str, float | int]] = []
    if max(displacement) > 0.0:
        targets = range(1, math.floor(max(displacement)) + 1)
        for target in targets:
            for left, right in zip(indices, indices[1:]):
                y_left = (unwrapped[left] - base) / TAU
                y_right = (unwrapped[right] - base) / TAU
                if y_left < target <= y_right and y_right > y_left:
                    fraction = (target - y_left) / (y_right - y_left)
                    crossing_s = trace.time[left] + fraction * (trace.time[right] - trace.time[left])
                    markers.append({
                        "turn_level": int(target),
                        "time_ps": crossing_s * 1.0e12,
                    })
                    break
    return {
        "marker_type": "first_upward_integer_phase_displacement_crossing",
        "phase_column": phase_label,
        "window_first_ps": trace.time[indices[0]] * 1.0e12,
        "window_last_ps": trace.time[indices[-1]] * 1.0e12,
        "reference": "unwrapped phase at first stored sample in the requested window",
        "crossings": markers,
        "crossing_times_ps": [float(item["time_ps"]) for item in markers],
        "max_displacement_turns": max(displacement),
        "endpoint_displacement_turns": displacement[-1],
        "not_an_sfq_count": True,
    }


def count_from_burst(metrics: dict[str, Any]) -> dict[str, Any]:
    phase = float(metrics["phase_delta_turns"])
    area = float(metrics["voltage_area_over_phi0"])
    if max(abs(phase), abs(area)) <= COUNT_TOLERANCE_TURNS:
        return {"count": 0, "polarity": None, "count_status": "ZERO_BURST"}
    phase_round = int(round(phase))
    area_round = int(round(area))
    same_sign = phase * area > 0.0
    near_integer = (
        abs(phase - phase_round) <= COUNT_TOLERANCE_TURNS
        and abs(area - area_round) <= COUNT_TOLERANCE_TURNS
        and phase_round != 0
        and area_round != 0
    )
    if same_sign and near_integer and phase_round == area_round:
        return {
            "count": abs(area_round),
            "polarity": 1 if area_round > 0 else -1,
            "count_status": "INTEGER_BURST_MATCH",
        }
    return {"count": None, "polarity": None, "count_status": "NON_INTEGER_OR_PHASE_AREA_MISMATCH"}


def make_spec(raw_path: Path, phase_label: str, voltage_label: str, run_id: str, window_id: str) -> StrictLocalEventSpec:
    return StrictLocalEventSpec.from_mapping(
        {
            "id": "bvmsim-operational-baseline-strict-local-v1",
            "scope": "task-local",
            "status": "POST_HOC_EXPLORATORY",
            "provenance_status": "RAW_HASHED_REPRODUCTION_ONLY",
            "analysis_role": "POST_HOC_EXPLORATORY_DIAGNOSTIC_NOT_ACCEPTANCE_GATE",
            "mapping_status": "DECLARED_DIRECT_SAME_JJ_PV",
            "phase_column": phase_label,
            "voltage_column": voltage_label,
            "branch_endpoints": f"direct JoSIM branch {phase_label}/{voltage_label}",
            "voltage_to_phase_sign": 1,
            "reporting_direction": 1,
            "run_id": run_id,
            "window_id": window_id,
            "raw_sha256": sha256_file(raw_path),
            "metric_spec": {
                "path": "docs/research/METRIC_SPEC_V2.md",
                "version": "2.0.0",
                "sha256": sha256_file(METRIC_SPEC),
            },
            "tolerance": {
                "id": "bvmsim-operational-baseline-strict-v1",
                "scope": "task-local",
                "status": "POST_HOC_EXPLORATORY",
                "evidence": "test/exploration/bvmsim-bvm-qb-jtl-operational-baseline-v1-20260903/analysis/POST_HOC_DIAGNOSTIC.md",
                "status_scope": "post_hoc_reproduction_only; not preregistered and not an acceptance gate",
                "phase_area_residual_abs_floor_turns": PHASE_AREA_RESIDUAL_ABS_FLOOR,
                "phase_area_residual_relative": PHASE_AREA_RESIDUAL_RELATIVE,
                "complete_min_turns": 1.0,
                "clean_upper_turns": 1.15,
                "post_range_max_turns": 1.0,
                "post_tail_p2p_max_turns": RETRAP_P2P_TURNS,
            },
            "compatibility_profile": "STRICT_EVENT_ANCHOR_COMPATIBILITY_V1",
        }
    )


def strict_local(trace: RawTrace, raw_path: Path, phase_label: str, voltage_label: str, run_id: str, event_window: tuple[float, float], window_id: str) -> dict[str, Any]:
    spec = make_spec(raw_path, phase_label, voltage_label, run_id, window_id)
    full_start = trace.time[0]
    dt = trace.time[-1] - trace.time[-2]
    full_end = trace.time[-1] + dt
    requested_window = event_window
    clipped_window = (max(event_window[0], full_start), min(event_window[1], full_end))
    if clipped_window[1] <= clipped_window[0]:
        raise ValueError(f"event window has no overlap with stored raw grid: {event_window}")
    result = strict_event_list(
        trace.time,
        sig(trace, phase_label),
        sig(trace, voltage_label),
        event_window_s=clipped_window,
        scan_window_s=(full_start, full_end),
        retrap_max_p2p_turns=RETRAP_P2P_TURNS,
        spec=spec,
    )
    result["analysis_authority"] = "POST_HOC_EXPLORATORY_DIAGNOSTIC_NOT_ACCEPTANCE_GATE"
    result["requested_event_window_s"] = list(requested_window)
    result["stored_grid_clipped"] = clipped_window != requested_window
    return result


def compact_strict_result(strict: dict[str, Any]) -> dict[str, Any]:
    event_keys = (
        "event_index",
        "event_window_event_index",
        "start_time_ps",
        "end_time_ps",
        "duration_ps",
        "direction",
        "phase_reported_turns",
        "area_reported_turns",
        "phase_area_residual_turns",
        "complete_segment",
        "clean_band",
        "clean_separated_event",
        "continuous_multiturn_segment",
        "retrap_or_bounded_interval",
    )
    compact = {
        key: strict[key]
        for key in (
        "mode",
        "claim_ceiling",
        "analysis_authority",
            "event_window_s",
            "scan_window_s",
            "retrap_max_p2p_turns",
            "requested_event_window_s",
            "stored_grid_clipped",
            "complete_segment_count",
            "clean_separated_event_count",
            "complete_event_onset_times_ps",
            "clean_event_onset_times_ps",
            "clean_event_directions",
            "largest_segment_turns",
            "any_segment_spans_over_1_15_turns",
            "continuous_multi_turn_running",
        )
        if key in strict
    }
    compact["complete_events"] = [
        {key: event[key] for key in event_keys if key in event}
        for event in strict["complete_events"]
    ]
    return compact


def classify_burst(
    trace: RawTrace,
    raw_path: Path,
    run_id: str,
    phase_label: str,
    voltage_label: str,
    event_window: tuple[float, float],
    window_id: str,
    expected: int,
    *,
    compact: bool = False,
) -> dict[str, Any]:
    metrics = phase_area(trace, phase_label, voltage_label, event_window)
    metrics.update(count_from_burst(metrics))
    metrics["expected_count"] = expected
    metrics["count_match"] = metrics["count"] == expected
    strict = strict_local(trace, raw_path, phase_label, voltage_label, run_id, event_window, window_id)
    metrics["strict_local"] = compact_strict_result(strict) if compact else strict
    return metrics


def diagnostic_window(
    trace: RawTrace,
    raw_path: Path,
    run_id: str,
    phase_label: str,
    voltage_label: str,
    event_window: tuple[float, float],
    window_id: str,
) -> dict[str, Any]:
    """Record every-window activity without promoting burst arithmetic to a count."""

    metrics = phase_area(trace, phase_label, voltage_label, event_window)
    metrics["burst_total_diagnostic"] = count_from_burst(metrics)
    strict = strict_local(trace, raw_path, phase_label, voltage_label, run_id, event_window, window_id)
    metrics["strict_local"] = compact_strict_result(strict)
    metrics["strict_complete_segment_count"] = strict["complete_segment_count"]
    metrics["strict_clean_separated_event_count"] = strict["clean_separated_event_count"]
    metrics["strict_complete_event_onset_times_ps"] = strict["complete_event_onset_times_ps"]
    metrics["strict_clean_event_onset_times_ps"] = strict["clean_event_onset_times_ps"]
    metrics["strict_continuous_multi_turn_running"] = strict["continuous_multi_turn_running"]
    return metrics


def diagnostic_windows(
    trace: RawTrace,
    raw_path: Path,
    run_id: str,
    phase_label: str,
    voltage_label: str,
    windows: Iterable[tuple[str, tuple[float, float]]],
) -> dict[str, Any]:
    return {
        name: diagnostic_window(
            trace,
            raw_path,
            run_id,
            phase_label,
            voltage_label,
            (left * 1e-12, right * 1e-12),
            name,
        )
        for name, (left, right) in windows
    }


def strict_selectivity_summary(windows: dict[str, Any], active_window: str) -> dict[str, Any]:
    complete = {
        name: item["strict_complete_segment_count"]
        for name, item in windows.items()
    }
    clean = {
        name: item["strict_clean_separated_event_count"]
        for name, item in windows.items()
    }
    unexpected = sum(
        int(value or 0)
        for name, value in complete.items()
        if name != active_window
    )
    return {
        "strict_complete_segments_by_window": complete,
        "strict_clean_separated_events_by_window": clean,
        "active_window": active_window,
        "unexpected_complete_segments_outside_active_window": unexpected,
        "all_windows_scanned": True,
    }


def available(trace: RawTrace, label: str) -> bool:
    return label in trace.headers


def kcl_metrics(trace: RawTrace, window: tuple[float, float]) -> dict[str, Any]:
    equations = {
        "QB_node2": (
            {name: sig(trace, name) for name in ("I(BJS|XBQ1)", "I(BJ1|XBQ1)", "I(RJ1|XBQ1)", "I(L1|XBQ1)")},
            {"I(BJS|XBQ1)": -1.0, "I(BJ1|XBQ1)": 1.0, "I(RJ1|XBQ1)": 1.0, "I(L1|XBQ1)": 1.0},
        ),
        "QB_bias_node3": (
            {name: sig(trace, name) for name in ("I(L1|XBQ1)", "I(IB|XBQ1)", "I(L2|XBQ1)")},
            {"I(L1|XBQ1)": -1.0, "I(IB|XBQ1)": -1.0, "I(L2|XBQ1)": 1.0},
        ),
        "QB_node4": (
            {name: sig(trace, name) for name in ("I(L2|XBQ1)", "I(BJ2|XBQ1)", "I(RJ2|XBQ1)", "I(L3|XBQ1)")},
            {"I(L2|XBQ1)": -1.0, "I(BJ2|XBQ1)": 1.0, "I(RJ2|XBQ1)": 1.0, "I(L3|XBQ1)": 1.0},
        ),
    }
    output: dict[str, Any] = {}
    for name, (branches, coefficients) in equations.items():
        residual = linear_kcl_residual(branches, coefficients)
        output[name] = {
            "equation_coefficients": coefficients,
            "current_orientation": "JoSIM branch current is positive from the first listed node to the second",
            "metrics": kcl_window_metrics(trace.time, residual, window, unit="A"),
        }
    return output


def four_record(record: dict[str, Any], raw_path: Path, raw_origin: str) -> dict[str, Any]:
    trace = read_csv(raw_path)
    read0 = window_s("READ0")
    read1 = window_s("READ1")
    tail = window_s("TAIL")
    expected = int(record["expected_count"])
    qb_read0 = classify_burst(trace, raw_path, record["run_id"], "P(BJ2|XBQ1)", "V(BJ2|XBQ1)", read0, "READ0", 0)
    qb_read1 = classify_burst(trace, raw_path, record["run_id"], "P(BJ2|XBQ1)", "V(BJ2|XBQ1)", read1, "READ1", expected)
    qb_read1["phase_crossing_markers"] = phase_crossing_markers(trace, "P(BJ2|XBQ1)", read1)
    jtl_stages: dict[str, Any] = {}
    for stage in range(1, 7):
        p = f"P(B02|XJTL1_{stage})"
        v = f"V(B02|XJTL1_{stage})"
        jtl_stages[f"JTL{stage}"] = {
            "B02": classify_burst(
                trace,
                raw_path,
                record["run_id"],
                p,
                v,
                read1,
                "READ1",
                expected,
                compact=stage != 6,
            ),
            "B01": {
                "phase_area": phase_area(trace, f"P(B01|XJTL1_{stage})", f"V(B01|XJTL1_{stage})", read1),
                "strict_local": compact_strict_result(
                    strict_local(
                        trace,
                        raw_path,
                        f"P(B01|XJTL1_{stage})",
                        f"V(B01|XJTL1_{stage})",
                        record["run_id"],
                        read1,
                        "READ1",
                    )
                ),
            },
        }
        jtl_stages[f"JTL{stage}"]["B02"]["phase_crossing_markers"] = phase_crossing_markers(trace, p, read1)
        jtl_stages[f"JTL{stage}"]["B02"]["all_windows"] = diagnostic_windows(
            trace, raw_path, record["run_id"], p, v, WINDOWS_PS.items()
        )
        jtl_stages[f"JTL{stage}"]["B02"]["selectivity"] = strict_selectivity_summary(
            jtl_stages[f"JTL{stage}"]["B02"]["all_windows"], "READ1"
        )
        b01_phase = f"P(B01|XJTL1_{stage})"
        b01_voltage = f"V(B01|XJTL1_{stage})"
        jtl_stages[f"JTL{stage}"]["B01"]["all_windows"] = diagnostic_windows(
            trace, raw_path, record["run_id"], b01_phase, b01_voltage, WINDOWS_PS.items()
        )
        jtl_stages[f"JTL{stage}"]["B01"]["selectivity"] = strict_selectivity_summary(
            jtl_stages[f"JTL{stage}"]["B01"]["all_windows"], "READ1"
        )
    tail_output = classify_burst(trace, raw_path, record["run_id"], "P(BJ2|XBQ1)", "V(BJ2|XBQ1)", tail, "TAIL", 0)
    qb_windows = diagnostic_windows(
        trace,
        raw_path,
        record["run_id"],
        "P(BJ2|XBQ1)",
        "V(BJ2|XBQ1)",
        WINDOWS_PS.items(),
    )
    qb_selectivity = strict_selectivity_summary(qb_windows, "READ1")
    jtl6_selectivity = jtl_stages["JTL6"]["B02"]["selectivity"]
    input_desc = descriptor(trace, "I(LIN|XBQ1)", read1)
    bvmout = phase_area(trace, "P(BVMOUT)", "V(BVMOUT)", read1)
    verdict = "FUNCTIONAL_PASS"
    failure_reasons: list[str] = []
    for label, item in (("READ0 QB", qb_read0), ("READ1 QB", qb_read1), ("TAIL QB", tail_output)):
        if not item["count_match"]:
            verdict = "FUNCTIONAL_FAIL"
            failure_reasons.append(f"{label}: observed={item['count']} expected={item['expected_count']}")
    if not jtl_stages["JTL6"]["B02"]["count_match"]:
        verdict = "FUNCTIONAL_FAIL"
        failure_reasons.append(f"JTL6 B02: observed={jtl_stages['JTL6']['B02']['count']} expected={expected}")
    if expected > 0 and not qb_read1["phase_area_consistent"]:
        verdict = "INCONCLUSIVE" if verdict == "FUNCTIONAL_PASS" else verdict
        failure_reasons.append("QB BJ2 READ1 phase/area residual outside task-local band")
    if expected > 0 and qb_read1["polarity"] != 1:
        verdict = "FUNCTIONAL_FAIL"
        failure_reasons.append(f"QB BJ2 polarity={qb_read1['polarity']}, expected=+1")
    if expected > 0 and jtl_stages["JTL6"]["B02"]["polarity"] != 1:
        verdict = "FUNCTIONAL_FAIL"
        failure_reasons.append(f"JTL6 B02 polarity={jtl_stages['JTL6']['B02']['polarity']}, expected=+1")
    for label, selectivity in (("QB BJ2", qb_selectivity), ("JTL6 B02", jtl6_selectivity)):
        outside = int(selectivity["unexpected_complete_segments_outside_active_window"])
        if outside:
            verdict = "FUNCTIONAL_FAIL"
            failure_reasons.append(f"{label}: strict complete segments outside READ1={outside}")
    return {
        "run_id": record["run_id"],
        "family": "four_bvm",
        "state": record["state"],
        "weight": expected,
        "expected_count": expected,
        "raw": str(raw_path.relative_to(REPO)),
        "raw_origin": raw_origin,
        "raw_sha256": sha256(raw_path),
        "grid": {
            "sample_count": trace.sample_count,
            "start_ps": trace.time[0] * 1e12,
            "end_ps": trace.time[-1] * 1e12,
            "dt_min_ps": min(trace.dt) * 1e12,
            "dt_max_ps": max(trace.dt) * 1e12,
            "uniform": all(value == trace.dt[0] for value in trace.dt),
            "interpolation": "none",
        },
        "input_descriptor_READ1": input_desc,
        "bvmout_READ1_phase_area": bvmout,
        "qb": {"READ0": qb_read0, "READ1": qb_read1, "TAIL": tail_output},
        "qb_selectivity": {"BJ2": qb_selectivity, "windows": qb_windows},
        "jtl": jtl_stages,
        "kcl_READ1": kcl_metrics(trace, read1),
        "functional_verdict": verdict,
        "failure_reasons": failure_reasons,
        "strict_status": {
            "BJ2_READ0_complete_segments": qb_read0["strict_local"]["complete_segment_count"],
            "BJ2_READ0_clean_separated_events": qb_read0["strict_local"]["clean_separated_event_count"],
            "BJ2_READ1_complete_segments": qb_read1["strict_local"]["complete_segment_count"],
            "BJ2_READ1_clean_separated_events": qb_read1["strict_local"]["clean_separated_event_count"],
            "BJ2_READ1_continuous_multi_turn": qb_read1["strict_local"]["continuous_multi_turn_running"],
            "JTL6_READ1_complete_segments": jtl_stages["JTL6"]["B02"]["strict_local"]["complete_segment_count"],
            "JTL6_READ1_clean_separated_events": jtl_stages["JTL6"]["B02"]["strict_local"]["clean_separated_event_count"],
        },
    }


def single_record(record: dict[str, Any], raw_path: Path, raw_origin: str) -> dict[str, Any]:
    trace = read_csv(raw_path)
    event = window_s("READ", single=True)
    tail = window_s("TAIL", single=True)
    expected = int(record["expected_count"])
    qb = classify_burst(trace, raw_path, record["run_id"], "P(BJ2|XBQ1)", "V(BJ2|XBQ1)", event, "READ", expected)
    qb["phase_crossing_markers"] = phase_crossing_markers(trace, "P(BJ2|XBQ1)", event)
    tail_output = classify_burst(trace, raw_path, record["run_id"], "P(BJ2|XBQ1)", "V(BJ2|XBQ1)", tail, "TAIL", 0)
    qb_windows = diagnostic_windows(
        trace,
        raw_path,
        record["run_id"],
        "P(BJ2|XBQ1)",
        "V(BJ2|XBQ1)",
        SINGLE_WINDOWS_PS.items(),
    )
    out: dict[str, Any] = {
        "run_id": record["run_id"],
        "family": "single_bvm",
        "state": "S1" if expected else "S0",
        "load": record["load"],
        "expected_count": expected,
        "raw": str(raw_path.relative_to(REPO)),
        "raw_origin": raw_origin,
        "raw_sha256": sha256(raw_path),
        "grid": {
            "sample_count": trace.sample_count,
            "start_ps": trace.time[0] * 1e12,
            "end_ps": trace.time[-1] * 1e12,
            "dt_min_ps": min(trace.dt) * 1e12,
            "dt_max_ps": max(trace.dt) * 1e12,
            "uniform": all(value == trace.dt[0] for value in trace.dt),
            "interpolation": "none",
        },
        "input_descriptor_READ": descriptor(trace, "I(LIN|XBQ1)", event),
        "bvmout_READ_phase_area": phase_area(trace, "P(BVMOUT)", "V(BVMOUT)", event),
        "qb": {"READ": qb, "TAIL": tail_output},
        "qb_selectivity": {"BJ2": strict_selectivity_summary(qb_windows, "READ"), "windows": qb_windows},
        "kcl_READ": kcl_metrics(trace, event),
    }
    if record["load"] == "JTL":
        stages: dict[str, Any] = {}
        for stage in range(1, 7):
            p = f"P(B02|XJTL1_{stage})"
            v = f"V(B02|XJTL1_{stage})"
            stages[f"JTL{stage}"] = classify_burst(
                trace,
                raw_path,
                record["run_id"],
                p,
                v,
                event,
                "READ",
                expected,
                compact=stage != 6,
            )
            stages[f"JTL{stage}"]["phase_crossing_markers"] = phase_crossing_markers(trace, p, event)
            stages[f"JTL{stage}"]["all_windows"] = diagnostic_windows(
                trace,
                raw_path,
                record["run_id"],
                p,
                v,
                SINGLE_WINDOWS_PS.items(),
            )
            stages[f"JTL{stage}"]["selectivity"] = strict_selectivity_summary(
                stages[f"JTL{stage}"]["all_windows"], "READ"
            )
        out["jtl"] = stages
        final = stages["JTL6"]
    else:
        out["jtl"] = None
        final = qb
    verdict = "FUNCTIONAL_PASS"
    reasons: list[str] = []
    for label, item in (("QB READ", qb), ("QB TAIL", tail_output), ("final", final)):
        target = expected if label == "QB READ" else 0 if label == "QB TAIL" else expected
        if item["count"] != target:
            verdict = "FUNCTIONAL_FAIL"
            reasons.append(f"{label}: observed={item['count']} expected={target}")
    if expected > 0 and not qb["phase_area_consistent"]:
        verdict = "INCONCLUSIVE" if verdict == "FUNCTIONAL_PASS" else verdict
        reasons.append("QB BJ2 phase/area residual outside task-local band")
    if expected > 0 and final.get("polarity") != 1:
        verdict = "FUNCTIONAL_FAIL"
        reasons.append(f"final polarity={final.get('polarity')}, expected=+1")
    outside_qb = int(out["qb_selectivity"]["BJ2"]["unexpected_complete_segments_outside_active_window"])
    if outside_qb:
        verdict = "FUNCTIONAL_FAIL"
        reasons.append(f"QB BJ2: strict complete segments outside READ={outside_qb}")
    if record["load"] == "JTL":
        outside_final = int(stages["JTL6"]["selectivity"]["unexpected_complete_segments_outside_active_window"])
        if outside_final:
            verdict = "FUNCTIONAL_FAIL"
            reasons.append(f"JTL6 B02: strict complete segments outside READ={outside_final}")
    out["functional_verdict"] = verdict
    out["failure_reasons"] = reasons
    out["unclosed_observed_verdict"] = verdict
    out["artifact_status"] = "INVALID"
    out["physical_verdict"] = "NOT_ASSESSED"
    out["artifact_invalid_reason"] = (
        "Historical single-BVM original BQ deck emits Missing model: JJMIT and "
        "Using default model; its intended JJMIT model closure is not the same as "
        "the four-BVM fixture's visible top-level model."
    )
    out["model_resolution"] = {
        "historical_bq": "BVMSim/BQ.cir",
        "observed_single_resolution": "solver_default_after_Missing_model_JJMIT_warning",
        "shared_jjmit_substitution": False,
        "comparability": "single and four-BVM runs are not like-for-like effective-model contexts",
    }
    # Keep the raw-derived numbers above for auditability, but do not expose an
    # unclosed single-BVM run as a physical PASS/FAIL result.
    out["functional_verdict"] = "ARTIFACT_INVALID"
    out["strict_status"] = {
        "BJ2_READ_complete_segments": qb["strict_local"]["complete_segment_count"],
        "BJ2_READ_clean_separated_events": qb["strict_local"]["clean_separated_event_count"],
        "BJ2_READ_continuous_multi_turn": qb["strict_local"]["continuous_multi_turn_running"],
        "final_count": final["count"],
    }
    return out


def select_position_anchors(four: Iterable[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for item in four:
        grouped[int(item["weight"])].append(item)
    output: dict[str, Any] = {}
    for weight, items in sorted(grouped.items()):
        def score(item: dict[str, Any]) -> tuple[float, float, str]:
            descriptor_item = item["input_descriptor_READ1"]
            return (
                float(descriptor_item["peak_abs_uA"]),
                abs(float(item["qb"]["READ1"]["voltage_area_over_phi0"])),
                str(item["state"]),
            )
        ordered = sorted(items, key=score)
        output[str(weight)] = {
            "states": [item["state"] for item in ordered],
            "weakest_state": ordered[0]["state"],
            "strongest_state": ordered[-1]["state"],
            "criterion": "ascending/descending READ1 I(LIN|XBQ1) peak_abs_uA, then QB BJ2 burst area magnitude, then state lexical tie-break",
            "input_peak_spread_uA": max(float(item["input_descriptor_READ1"]["peak_abs_uA"]) for item in items) - min(float(item["input_descriptor_READ1"]["peak_abs_uA"]) for item in items),
            "input_peak_min_uA": min(float(item["input_descriptor_READ1"]["peak_abs_uA"]) for item in items),
            "input_peak_max_uA": max(float(item["input_descriptor_READ1"]["peak_abs_uA"]) for item in items),
            "timing_spread_ps": max(
                float(item["qb"]["READ1"]["strict_local"]["complete_event_onset_times_ps"][0])
                if item["qb"]["READ1"]["strict_local"]["complete_event_onset_times_ps"] else float("nan")
                for item in items
            ) - min(
                float(item["qb"]["READ1"]["strict_local"]["complete_event_onset_times_ps"][0])
                if item["qb"]["READ1"]["strict_local"]["complete_event_onset_times_ps"] else float("nan")
                for item in items
            ) if all(item["qb"]["READ1"]["strict_local"]["complete_event_onset_times_ps"] for item in items) else None,
        }
    return output


def load_manifest() -> dict[str, Any]:
    return json.loads((EXP / "analysis/baseline_deck_manifest.json").read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    manifest = load_manifest()
    outcomes = json.loads(EXECUTION_OUTCOMES.read_text(encoding="utf-8"))
    results: dict[str, Any] = {"single": [], "four": []}
    execution: list[dict[str, Any]] = []
    for record in manifest["runs"]:
        raw_path, origin = raw_path_for(record)
        deck = deck_path_for(record, raw_path, origin)
        execution_meta = execution_artifacts(record["run_id"], raw_path, outcomes)
        rec = {
            "run_id": record["run_id"],
            "family": record["family"],
            "state": record["state"],
            "expected_count": record["expected_count"],
            "load": record["load"],
            "deck": str(deck.relative_to(REPO)),
            "deck_declared": record["deck"],
            "deck_sha256": sha256(deck),
            "raw": record["raw"],
            "raw_selected": str(raw_path.relative_to(REPO)),
            "raw_origin": origin,
            "raw_sha256": sha256(raw_path),
            "solver": solver_provenance(SOLVER),
        }
        rec.update(execution_meta)
        execution.append(rec)
        if args.check_only:
            continue
        if record["family"] == "single_bvm":
            results["single"].append(single_record(record, raw_path, origin))
        else:
            results["four"].append(four_record(record, raw_path, origin))
    if args.check_only:
        print(f"raw availability PASS: {len(execution)} runs")
        return 0

    four = sorted(results["four"], key=lambda item: item["state"])
    single = sorted(results["single"], key=lambda item: item["run_id"])
    results["four"] = four
    results["single"] = single
    results["position_anchors"] = select_position_anchors(four)
    results["baseline_gate"] = {
        "nominal_16_state_functional_pass": all(item["functional_verdict"] == "FUNCTIONAL_PASS" for item in four),
        "verdict_scope": "historical_four_bvm_fixture_only",
        "evidence_descriptor": "HISTORICAL_FIXTURE_COUNT_MISMATCH",
        "strict_threshold_status": "POST_HOC_EXPLORATORY_DIAGNOSTIC",
        "single_bvm_status": "INVALID_INTENDED_MODEL_CLOSURE; excluded from 16-state gate",
        "state_mapping_failures": [
            {"state": item["state"], "expected": item["expected_count"], "qb": item["qb"]["READ1"]["count"], "jtl6": item["jtl"]["JTL6"]["B02"]["count"], "reasons": item["failure_reasons"]}
            for item in four if item["functional_verdict"] != "FUNCTIONAL_PASS"
        ],
        "stop_rule": "BASELINE_FUNCTIONAL_FAIL if any nominal state fails expected 0/1/2/3/4 mapping",
    }
    results["classification"] = {
        "baseline_verdict": "BASELINE_FUNCTIONAL_FAIL",
        "evidence_descriptor": "HISTORICAL_FIXTURE_COUNT_MISMATCH",
        "primary_classification": "SELECTIVITY_OR_OVERDRIVE_FAILURE",
        "quick_label": "QUICK_OPPOSITE",
        "margin_status": "NOT_RUN_BASELINE_STOP_RULE",
        "nominal_rj1_ohm_retained": 12.0,
        "scope": "historical_four_bvm_fixture_only; exploratory classification, not Formal acceptance",
    }
    results["analysis_contract"] = {
        "status": "POST_HOC_EXPLORATORY_DIAGNOSTIC",
        "preregistration_status": "numeric burst/strict thresholds were not present in the preflight; no threshold is claimed as pre-registered",
        "count_basis": "same-JJ READ burst phase/area plus JTL6 B02 downstream marker",
        "count_tolerance_turns": COUNT_TOLERANCE_TURNS,
        "count_tolerance_role": "post_hoc_integer_display_only",
        "strict_event_thresholds_role": "post_hoc_diagnostic_only",
        "gross_mismatch_basis": "raw phase/area magnitudes differ from commanded popcount by integer-scale amounts; not a clean-event or phase-only claim",
        "fixed_quiet_gap_required": False,
        "strict_event_list_source": "scripts/bvmtools.sfq.strict_event_list",
        "net_phase_not_count": True,
    }
    metrics_path = EXP / "analysis/metrics.json"
    json_write(metrics_path, {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "experiment": EXP.name,
        "results": results,
    })
    json_write(EXP / "analysis/execution_manifest.json", {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "runs": execution,
        "execution_outcomes": str(EXECUTION_OUTCOMES.relative_to(REPO)),
        "raw_immutable": True,
    })
    provenance = {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "head_at_analysis": git_snapshot(REPO),
        "solver": solver_provenance(SOLVER),
        "files": {
            "profile": file_snapshot(PROFILE),
            "boundary_spec": file_snapshot(BOUNDARY),
            "metric_spec": file_snapshot(METRIC_SPEC),
            "renderer": file_snapshot(RENDERER),
            "analyzer": file_snapshot(Path(__file__)),
            "shared_jjmit_reference": file_snapshot(REPO / "circuits/models/jjmit.cir"),
            "canonical_bvm_reference": file_snapshot(REPO / "circuits/bvm/bvm_cell.cir"),
            "raw_sha256_index": file_snapshot(EXP / "analysis/RAW_SHA256SUMS.txt") if (EXP / "analysis/RAW_SHA256SUMS.txt").is_file() else None,
            "visualization_manifest": file_snapshot(EXP / "analysis/visualization_manifest.json") if (EXP / "analysis/visualization_manifest.json").is_file() else None,
            "historical_anchor_check": file_snapshot(EXP / "analysis/historical_anchor_check.json") if (EXP / "analysis/historical_anchor_check.json").is_file() else None,
            "review_notes": file_snapshot(EXP / "analysis/REVIEW.md") if (EXP / "analysis/REVIEW.md").is_file() else None,
            "human_gate": file_snapshot(EXP / "analysis/human-gate.yaml") if (EXP / "analysis/human-gate.yaml").is_file() else None,
            "execution_notes": file_snapshot(EXP / "analysis/EXECUTION_NOTES.md") if (EXP / "analysis/EXECUTION_NOTES.md").is_file() else None,
            "test_commands": file_snapshot(EXP / "analysis/TEST_COMMANDS.md") if (EXP / "analysis/TEST_COMMANDS.md").is_file() else None,
            "execution_outcomes": file_snapshot(EXECUTION_OUTCOMES),
            "execution_manifest": file_snapshot(EXP / "analysis/execution_manifest.json") if (EXP / "analysis/execution_manifest.json").is_file() else None,
            "metrics": file_snapshot(EXP / "analysis/metrics.json") if (EXP / "analysis/metrics.json").is_file() else None,
            "post_hoc_diagnostic": file_snapshot(EXP / "analysis/POST_HOC_DIAGNOSTIC.md") if (EXP / "analysis/POST_HOC_DIAGNOSTIC.md").is_file() else None,
            "baseline_report": file_snapshot(EXP / "analysis/BASELINE_REPORT.md") if (EXP / "analysis/BASELINE_REPORT.md").is_file() else None,
            "visualization_readme": file_snapshot(EXP / "plots/README.md") if (EXP / "plots/README.md").is_file() else None,
        },
        "historical_sources": {
            "BVMSim/BQ.cir": file_snapshot(REPO / "BVMSim/BQ.cir"),
            "BVMSim/bvm_cell.cir": file_snapshot(REPO / "BVMSim/bvm_cell.cir"),
            "BVMSim/test_bvm_mixed_0.cir": file_snapshot(REPO / "BVMSim/test_bvm_mixed_0.cir"),
            "BVMSim/library_josim/jtl2.cir": file_snapshot(REPO / "BVMSim/library_josim/jtl2.cir"),
            "BVMSim/data_tran.csv": file_snapshot(REPO / "BVMSim/data_tran.csv"),
        },
        "execution": execution,
        "analysis_contract_status": "POST_HOC_EXPLORATORY_DIAGNOSTIC_NOT_ACCEPTANCE_GATE",
        "review_disposition": "REWORK_REQUIRED; not Formal acceptance",
        "physical_acceptance": "NOT_ACCEPTED",
        "single_bvm_model_resolution_note": "single-BVM original BQ logs Missing model: JJMIT and uses solver default; single results are artifact INVALID for intended-model comparison and are excluded from the four-state gate.",
        "source_authority_note": "BVMSim/bvm_cell.cir is HISTORICAL_BVMSIM and differs from canonical circuits/bvm/bvm_cell.cir; no canonical BVM compatibility is claimed.",
    }
    json_write(EXP / "analysis/provenance.json", provenance)
    print(json.dumps({"single": len(single), "four": len(four), "baseline_gate": results["baseline_gate"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
