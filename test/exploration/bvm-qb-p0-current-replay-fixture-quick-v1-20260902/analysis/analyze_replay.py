#!/usr/bin/env python3
"""Analyze the single P0-current replay Quick Probe.

The analyzer consumes the existing P0/I0 raw plus the one new RP raw.  It
does not run JoSIM.  Input fidelity and W2 PRE are fail-closed gates for all
W3/W4 interpretation.  Phase is always handled as raw JoSIM radians followed
by continuous unwrap and explicit division by 2*pi; local strict labels are
not SFQ counts or downstream-delivery claims.
"""

from __future__ import annotations

import csv
import json
import math
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from statistics import median
from typing import Any, Iterable, Mapping

import yaml

REPO = Path(__file__).resolve().parents[4]
ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "analysis"
PLOTS = ROOT / "plots"
CONFIG_PATH = ROOT / "experiment.yaml"
sys.path.insert(0, str(REPO / "scripts"))

from bvmtools.compare import (  # noqa: E402
    TimeGridMismatch,
    compare_series,
    compare_windowed_series,
    exact_time_grid_identity,
)
from bvmtools.kcl import kcl_window_metrics, linear_kcl_residual  # noqa: E402
from bvmtools.phase import TAU, continuous_unwrap, window_indices  # noqa: E402
from bvmtools.provenance import file_snapshot, git_snapshot, sha256_file, solver_provenance  # noqa: E402
from bvmtools.raw import RawTrace, read_csv  # noqa: E402
from bvmtools.sfq import StrictLocalEventSpec, strict_event_summary  # noqa: E402
from bvmtools.waveform import waveform_metrics  # noqa: E402


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO.resolve()).as_posix()


def resolve(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    if path.parts and path.parts[0] in {"docs", "circuits", "scripts", "build", "test"}:
        return (REPO / path).resolve()
    return (ROOT / path).resolve()


def load_config() -> dict[str, Any]:
    value = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("experiment.yaml must contain a mapping")
    return value


def selected(trace: RawTrace, signal: str, config: Mapping[str, Any]) -> tuple[float, ...]:
    occurrences = config.get("signals", {}).get("signal_occurrences", {})
    occurrence = occurrences.get(signal) if isinstance(occurrences, Mapping) else None
    values = trace.column(signal, occurrence=occurrence)
    if not isinstance(values, tuple) or (values and isinstance(values[0], tuple)):
        raise ValueError(f"signal {signal!r} was not selected as one exact column")
    return tuple(float(value) for value in values)


def window_seconds(config: Mapping[str, Any], name: str) -> tuple[float, float]:
    interval = config["windows_ps"][name]
    return float(interval[0]) * 1.0e-12, float(interval[1]) * 1.0e-12


def strict_window_seconds(config: Mapping[str, Any], key: str) -> tuple[float, float]:
    interval = config["strict_event"][key]
    return float(interval[0]) * 1.0e-12, float(interval[1]) * 1.0e-12


def phase_radians(trace: RawTrace, signal: str, config: Mapping[str, Any]) -> tuple[float, ...]:
    return tuple(continuous_unwrap(selected(trace, signal, config)))


def centered_phase_turns(
    trace: RawTrace, signal: str, config: Mapping[str, Any], pre_name: str = "W2_pre_read_idle"
) -> tuple[tuple[float, ...], float]:
    values = phase_radians(trace, signal, config)
    indices = window_indices(trace.time, *window_seconds(config, pre_name))
    if len(indices) < 2:
        raise ValueError(f"phase PRE window has fewer than two samples: {signal}")
    baseline = median(values[index] for index in indices)
    return tuple((value - baseline) / TAU for value in values), baseline / TAU


def phase_unit(signal: str) -> bool:
    return signal.startswith("P(")


def comparison(
    left_trace: RawTrace,
    left_values: tuple[float, ...],
    right_trace: RawTrace,
    right_values: tuple[float, ...],
    interval_ps: Iterable[float],
    *,
    unit: str,
    scale: float,
) -> dict[str, Any]:
    interval = tuple(float(value) * 1.0e-12 for value in interval_ps)
    if not exact_time_grid_identity(left_trace.time, right_trace.time):
        return {
            "status": "GRID_MISMATCH",
            "time_grid_exact": False,
            "window_ps": [float(interval_ps[0]), float(interval_ps[1])],
            "unit": unit,
        }
    result = compare_windowed_series(
        left_trace.time,
        left_values,
        right_trace.time,
        right_values,
        interval,
        value_scale=scale,
        unit=unit,
        include_correlation=True,
    )
    result.pop("pointwise_difference", None)
    return {str(key): value for key, value in result.items()}


def full_comparison(
    left_trace: RawTrace,
    left_values: tuple[float, ...],
    right_trace: RawTrace,
    right_values: tuple[float, ...],
    *,
    unit: str,
    scale: float,
) -> dict[str, Any]:
    if not exact_time_grid_identity(left_trace.time, right_trace.time):
        return {"status": "GRID_MISMATCH", "time_grid_exact": False, "unit": unit}
    result = compare_series(
        left_trace.time,
        left_values,
        right_trace.time,
        right_values,
        interpolation=None,
        include_correlation=True,
    )
    return {
        "status": str(result["status"]),
        "time_grid_exact": bool(result["time_grid_exact"]),
        "interpolation_mode": str(result["interpolation_mode"]),
        "sample_count": int(result["sample_count"]),
        "max_abs_error": float(result["max_abs_difference"]) * scale,
        "rms_error": float(result["rms_difference"]) * scale,
        "p95_abs_error": float(result["p95_abs_difference"]) * scale,
        "correlation": result.get("correlation"),
        "unit": unit,
    }


def area_summary(trace: RawTrace, values: tuple[float, ...]) -> dict[str, float | int]:
    result = waveform_metrics(trace.time, values)
    return {
        "sample_count": int(result["sample_count"]),
        "signed_area_A_ps": float(result["signed_time_integral"]) * 1.0e12,
        "positive_area_A_ps": float(result["positive_area"]) * 1.0e12,
        "negative_area_A_ps": float(result["negative_area"]) * 1.0e12,
        "minimum_A": float(result["minimum"]),
        "maximum_A": float(result["maximum"]),
    }


def load_traces(config: Mapping[str, Any]) -> tuple[dict[str, RawTrace], dict[str, dict[str, Any]]]:
    paths = {
        "P0": resolve(config["references"]["P0"]["raw"]),
        "I0": resolve(config["references"]["I0"]["raw"]),
        "RP": resolve(config["candidate"]["raw"]),
    }
    traces: dict[str, RawTrace] = {}
    records: dict[str, dict[str, Any]] = {}
    for key, path in paths.items():
        trace = read_csv(path)
        traces[key] = trace
        record = file_snapshot(path, relative_to=REPO)
        record["qa"] = trace.qa()
        record["configured_sha256"] = (
            config["references"][key]["raw_sha256"] if key in ("P0", "I0") else None
        )
        record["configured_hash_match"] = (
            record["configured_sha256"] is None
            or str(record["configured_sha256"]).casefold() == str(record["sha256"]).casefold()
        )
        records[key] = record
    return traces, records


def input_fidelity(
    traces: Mapping[str, RawTrace], config: Mapping[str, Any]
) -> dict[str, Any]:
    p0 = traces["P0"]
    rp = traces["RP"]
    source = selected(p0, config["candidate"]["source_signal"], config)
    replay = selected(rp, config["candidate"]["replay_output_signal"], config)
    exact_grid = exact_time_grid_identity(p0.time, rp.time)
    if exact_grid:
        result = full_comparison(p0, source, rp, replay, unit="A", scale=1.0)
    else:
        result = {"status": "GRID_MISMATCH", "time_grid_exact": False, "unit": "A"}
    p0_area = area_summary(p0, source)
    rp_area = area_summary(rp, replay)
    area_difference = {
        "signed_area_A_ps": rp_area["signed_area_A_ps"] - p0_area["signed_area_A_ps"],
        "positive_area_A_ps": rp_area["positive_area_A_ps"] - p0_area["positive_area_A_ps"],
        "negative_area_A_ps": rp_area["negative_area_A_ps"] - p0_area["negative_area_A_ps"],
    }
    max_uA = float(result.get("max_abs_error", math.inf)) * 1.0e6
    rms_uA = float(result.get("rms_error", math.inf)) * 1.0e6
    pass_value = exact_grid and max_uA <= 1.0e-6
    return {
        "status": "PASS" if pass_value else "FAIL",
        "source_signal": config["candidate"]["source_signal"],
        "source_occurrence": config["candidate"]["source_occurrence"],
        "replay_output_signal": config["candidate"]["replay_output_signal"],
        "source_orientation": config["candidate"]["source_orientation"],
        "positive_current_direction": config["candidate"]["positive_current_direction"],
        "sample_count_P0": p0.sample_count,
        "sample_count_RP": rp.sample_count,
        "grid_identity": exact_grid,
        "comparison": result,
        "max_abs_error_uA": max_uA,
        "rms_error_uA": rms_uA,
        "p95_abs_error_uA": float(result.get("p95_abs_error", math.inf)) * 1.0e6,
        "correlation": result.get("correlation"),
        "P0_area": p0_area,
        "RP_area": rp_area,
        "area_difference": area_difference,
        "criterion": "exact time grid and max_abs_error <= 1.0e-6 uA",
        "interpretation_allowed": pass_value,
    }


def pre_state(
    traces: Mapping[str, RawTrace], config: Mapping[str, Any]
) -> dict[str, Any]:
    p0 = traces["P0"]
    rp = traces["RP"]
    pre = config["windows_ps"]["W2_pre_read_idle"]
    records: dict[str, Any] = {}
    for signal in config["signals"]["pre_currents"]:
        records[signal] = comparison(
            p0,
            selected(p0, signal, config),
            rp,
            selected(rp, signal, config),
            pre,
            unit="uA",
            scale=1.0e6,
        )
        records[signal]["threshold_max_abs"] = float(config["pre_state_rule"]["current_max_abs_difference_uA"])
        records[signal]["pass"] = records[signal].get("status") == "VALID" and float(records[signal].get("max_abs_difference", math.inf)) <= records[signal]["threshold_max_abs"]
    for signal in config["signals"]["pre_phases"]:
        p0_values, p0_baseline = centered_phase_turns(p0, signal, config)
        rp_values, rp_baseline = centered_phase_turns(rp, signal, config)
        records[signal] = comparison(p0, p0_values, rp, rp_values, pre, unit="turns", scale=1.0)
        records[signal]["P0_W2_median_turns"] = p0_baseline
        records[signal]["RP_W2_median_turns"] = rp_baseline
        records[signal]["threshold_max_abs"] = float(config["pre_state_rule"]["phase_max_abs_difference_turns"])
        records[signal]["pass"] = records[signal].get("status") == "VALID" and float(records[signal].get("max_abs_difference", math.inf)) <= records[signal]["threshold_max_abs"]
    passed = all(bool(item.get("pass")) for item in records.values())
    return {
        "status": "PASS" if passed else "FAIL",
        "window_ps": list(pre),
        "phase_semantics": config["pre_state_rule"]["phase_semantics"],
        "all_signals_required": True,
        "signals": records,
        "interpretation_allowed": passed,
    }


def trajectory_values(
    trace: RawTrace, signal: str, config: Mapping[str, Any]
) -> tuple[tuple[float, ...], str, float]:
    if phase_unit(signal):
        values, _baseline = centered_phase_turns(trace, signal, config)
        return values, "turns", 1.0
    return tuple(value * 1.0e6 for value in selected(trace, signal, config)), "uA", 1.0


def trajectory_closure(
    traces: Mapping[str, RawTrace], config: Mapping[str, Any]
) -> dict[str, Any]:
    records: dict[str, dict[str, Any]] = {}
    for window_name in ("W3_read", "W4_post_read_observation"):
        interval = config["windows_ps"][window_name]
        records[window_name] = {}
        for signal in config["signals"]["primary_trajectory"]:
            p0_values, unit, scale = trajectory_values(traces["P0"], signal, config)
            rp_values, _unit, _scale = trajectory_values(traces["RP"], signal, config)
            i0_values, _unit, _scale = trajectory_values(traces["I0"], signal, config)
            rp_gap = comparison(traces["P0"], p0_values, traces["RP"], rp_values, interval, unit=unit, scale=scale)
            i0_gap = comparison(traces["P0"], p0_values, traces["I0"], i0_values, interval, unit=unit, scale=scale)
            floor = float(config["trajectory_closure_rule"]["reference_gap_floor"]["phase_rms_turns" if unit == "turns" else "current_rms_uA"])
            denominator = float(i0_gap.get("rms_difference", math.nan))
            ratio = denominator and float(rp_gap.get("rms_difference", math.inf)) / denominator if math.isfinite(denominator) and denominator > floor else None
            records[window_name][signal] = {
                "unit": unit,
                "P0_vs_RP": rp_gap,
                "P0_vs_I0": i0_gap,
                "RP_minus_P0_RMS": rp_gap.get("rms_difference"),
                "I0_minus_P0_RMS": i0_gap.get("rms_difference"),
                "reference_gap_floor": floor,
                "C_x": ratio,
                "C_x_status": "DEFINED" if ratio is not None else "NOT_DEFINED_SMALL_REFERENCE_GAP",
                "closure_pass": ratio is not None and ratio <= float(config["trajectory_closure_rule"]["threshold"]),
            }
    return {
        "status": "VALID",
        "windows": list(records),
        "records": records,
        "formula": config["trajectory_closure_rule"]["ratio"],
        "difference_convention": config["trajectory_closure_rule"]["difference_convention"],
        "phase_semantics": config["trajectory_closure_rule"]["phase_semantics"],
    }


def supporting_trajectory(
    traces: Mapping[str, RawTrace], config: Mapping[str, Any]
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for window_name in ("W3_read", "W4_post_read_observation"):
        result[window_name] = {}
        interval = config["windows_ps"][window_name]
        for signal in config["signals"]["supporting_trajectory"]:
            p0 = selected(traces["P0"], signal, config)
            rp = selected(traces["RP"], signal, config)
            i0 = selected(traces["I0"], signal, config)
            result[window_name][signal] = {
                "unit": "uA",
                "P0_vs_RP": comparison(traces["P0"], p0, traces["RP"], rp, interval, unit="uA", scale=1.0e6),
                "P0_vs_I0": comparison(traces["P0"], p0, traces["I0"], i0, interval, unit="uA", scale=1.0e6),
            }
    return result


def strict_for(case: str, trace: RawTrace, raw_hash: str, config: Mapping[str, Any], metric_hash: str) -> dict[str, Any]:
    declaration = config["strict_event"]
    spec_mapping = {
        "id": config["strict_event"]["tolerance"]["id"],
        "scope": "task-local",
        "status": "FROZEN",
        "mapping_status": declaration["mapping_status"],
        "phase_column": declaration["phase"],
        "voltage_column": declaration["voltage"],
        "branch_endpoints": declaration["branch_endpoints"],
        "voltage_to_phase_sign": declaration["voltage_to_phase_sign"],
        "reporting_direction": declaration["reporting_direction"],
        "run_id": f"{config['id']}/{case}",
        "window_id": "W3-read-95-110ps-activity-95-115ps-post-115-130ps-tail-125-130ps",
        "raw_sha256": raw_hash,
        "metric_spec": declaration["metric_spec"],
        "tolerance": declaration["tolerance"],
        "compatibility_profile": declaration["profile"],
    }
    spec = StrictLocalEventSpec.from_mapping(spec_mapping)
    return strict_event_summary(
        trace.time,
        selected(trace, declaration["phase"], config),
        selected(trace, declaration["voltage"], config),
        activity_window_s=strict_window_seconds(config, "activity_window_ps"),
        post_window_s=strict_window_seconds(config, "post_window_ps"),
        post_tail_window_s=strict_window_seconds(config, "post_tail_window_ps"),
        spec=spec,
        actual_raw_sha256=raw_hash,
        actual_metric_spec_sha256=metric_hash,
    )


def strict_local_closure(strict_results: Mapping[str, Any], config: Mapping[str, Any]) -> dict[str, Any]:
    p0 = strict_results["P0"]
    rp = strict_results["RP"]
    p0_segment = p0.get("largest_monotonic_segment") or {}
    rp_segment = rp.get("largest_monotonic_segment") or {}
    keys = {
        "phase_reported_turns": "phase_abs_difference_turns",
        "area_reported_turns": "area_abs_difference_phi0",
    }
    differences: dict[str, float | None] = {}
    for source_key, _limit_key in keys.items():
        left = p0_segment.get(source_key)
        right = rp_segment.get(source_key)
        differences[source_key] = abs(float(right) - float(left)) if left is not None and right is not None else None
    endpoints = []
    for key in ("start_time_ps", "end_time_ps"):
        left = p0_segment.get(key)
        right = rp_segment.get(key)
        endpoints.append(abs(float(right) - float(left)) if left is not None and right is not None else math.inf)
    endpoint_difference = max(endpoints) if endpoints else math.inf
    limits = config["strict_event"]["closure_to_P0"]
    close = (
        differences["phase_reported_turns"] is not None
        and differences["area_reported_turns"] is not None
        and differences["phase_reported_turns"] <= float(limits["phase_abs_difference_turns"])
        and differences["area_reported_turns"] <= float(limits["area_abs_difference_phi0"])
        and endpoint_difference <= float(limits["endpoint_abs_difference_ps"])
    )
    class_match = p0.get("compatibility_classification") == rp.get("compatibility_classification")
    return {
        "status": "PASS" if class_match and close else "FAIL",
        "P0_classification": p0.get("compatibility_classification"),
        "RP_classification": rp.get("compatibility_classification"),
        "classification_matches": class_match,
        "P0_largest_segment": p0_segment,
        "RP_largest_segment": rp_segment,
        "absolute_differences": differences,
        "endpoint_max_abs_difference_ps": endpoint_difference,
        "limits": limits,
        "largest_segment_close": close,
        "same_segment_area_compared": True,
        "post_boundedness_P0": p0.get("post_boundedness"),
        "post_boundedness_RP": rp.get("post_boundedness"),
        "second_complete_segment_P0": p0.get("second_complete_segment_present"),
        "second_complete_segment_RP": rp.get("second_complete_segment_present"),
    }


def strict_anchor_regression(config: Mapping[str, Any], strict_results: Mapping[str, Any]) -> dict[str, Any]:
    declaration = config["strict_anchor_regression"]
    summary_path = resolve(declaration["summary_csv"])
    expected = declaration["expected"]
    found: dict[str, Any] = {}
    if not summary_path.is_file():
        return {"status": "FAIL", "reason": f"missing anchor summary {rel(summary_path)}"}
    with summary_path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            key = f"{row.get('fixture')} {row.get('width_ps')} {row.get('jsl_load')}"
            if key in expected and row.get("role") == "logical1_read":
                found[key] = row
    checks: list[dict[str, Any]] = []
    for key, target in expected.items():
        row = found.get(key)
        if row is None:
            checks.append({"anchor": key, "pass": False, "reason": "missing row"})
            continue
        numeric_fields = ("largest_monotonic_segment_turns", "same_segment_voltage_area_turns")
        numeric_pass = all(abs(float(row[field]) - float(target[field])) <= float(declaration["numeric_tolerance"]) for field in numeric_fields)
        class_pass = row["strict_classification"] == target["strict_classification"]
        count_pass = int(row["complete_segment_count"]) == int(target["complete_segment_count"])
        checks.append({"anchor": key, "pass": numeric_pass and class_pass and count_pass, "row": row, "expected": target})
    current_i0 = strict_results.get("I0", {})
    current_i0_target = expected.get("replay 13 12x320")
    current_i0_segment = current_i0.get("largest_monotonic_segment") or {}
    current_i0_check = {
        "phase_turns": current_i0_segment.get("phase_reported_turns"),
        "area_phi0": current_i0_segment.get("area_reported_turns"),
        "classification": current_i0.get("compatibility_classification"),
        "pass": bool(current_i0_target)
        and current_i0.get("compatibility_classification") == current_i0_target["strict_classification"]
        and abs(float(current_i0_segment.get("phase_reported_turns")) - float(current_i0_target["largest_monotonic_segment_turns"])) <= float(declaration["numeric_tolerance"])
        and abs(float(current_i0_segment.get("area_reported_turns")) - float(current_i0_target["same_segment_voltage_area_turns"])) <= float(declaration["numeric_tolerance"]),
    }
    return {
        "status": "PASS" if all(bool(item["pass"]) for item in checks) and current_i0_check["pass"] else "FAIL",
        "source": rel(summary_path),
        "numeric_tolerance": declaration["numeric_tolerance"],
        "checks": checks,
        "current_I0_13ps_check": current_i0_check,
    }


KCL_EQUATIONS: dict[str, dict[str, float]] = {
    "input": {"I(LIN|XBQ)": 1.0, "I(BJS|XBQ)": -1.0},
    "node2": {"I(BJS|XBQ)": 1.0, "I(BJL1|XBQ)": -1.0, "I(RJ1|XBQ)": -1.0, "I(L1|XBQ)": -1.0},
    "node3": {"I(L1|XBQ)": 1.0, "I(RB|XBQ)": 1.0, "I(L2|XBQ)": -1.0},
    "node4": {"I(L2|XBQ)": 1.0, "I(BJL2|XBQ)": -1.0, "I(RJ2|XBQ)": -1.0, "I(L0|XBQ)": -1.0},
}


def kcl_results(traces: Mapping[str, RawTrace], config: Mapping[str, Any]) -> dict[str, Any]:
    tolerance = float(config["kcl_rule"]["tolerance_uA"])
    result: dict[str, Any] = {}
    windows = config["kcl_rule"]["windows"]
    for case in ("P0", "RP", "I0"):
        trace = traces[case]
        result[case] = {}
        for name, coefficients in KCL_EQUATIONS.items():
            branches = {signal: selected(trace, signal, config) for signal in coefficients}
            residual = linear_kcl_residual(branches, coefficients)
            result[case][name] = {}
            for window_name in windows:
                interval = config["windows_ps"][window_name]
                metrics = kcl_window_metrics(trace.time, residual, window_seconds(config, window_name), unit="A")
                metrics["tolerance_uA"] = tolerance
                metrics["pass"] = float(metrics["max_abs_uA"]) <= tolerance
                result[case][name][window_name] = metrics
    return {
        "implementation": "scripts/bvmtools/kcl.py",
        "equations": config["kcl_rule"]["equations"],
        "tolerance_uA": tolerance,
        "results": result,
        "status": "PASS" if all(bool(item["pass"]) for case in result.values() for equation in case.values() for item in equation.values()) else "FAIL",
    }


PLOT_SPECS = [
    ("I(P0 · Lin input)", "P0", "I(LIN|XBQ)"),
    ("I(RP · replay input)", "RP", "I(I_REPLAY)"),
    ("I(I0 · replay input)", "I0", "I(I_REPLAY)"),
    ("P(P0 · BJs)", "P0", "P(BJS|XBQ)"),
    ("P(RP · BJs)", "RP", "P(BJS|XBQ)"),
    ("P(I0 · BJs)", "I0", "P(BJS|XBQ)"),
    ("P(P0 · BJL1)", "P0", "P(BJL1|XBQ)"),
    ("P(RP · BJL1)", "RP", "P(BJL1|XBQ)"),
    ("P(I0 · BJL1)", "I0", "P(BJL1|XBQ)"),
    ("I(P0 · L1)", "P0", "I(L1|XBQ)"),
    ("I(RP · L1)", "RP", "I(L1|XBQ)"),
    ("I(I0 · L1)", "I0", "I(L1|XBQ)"),
    ("I(P0 · RB)", "P0", "I(RB|XBQ)"),
    ("I(RP · RB)", "RP", "I(RB|XBQ)"),
    ("I(I0 · RB)", "I0", "I(RB|XBQ)"),
    ("I(P0 · L2)", "P0", "I(L2|XBQ)"),
    ("I(RP · L2)", "RP", "I(L2|XBQ)"),
    ("I(I0 · L2)", "I0", "I(L2|XBQ)"),
    ("P(P0 · BJL2)", "P0", "P(BJL2|XBQ)"),
    ("P(RP · BJL2)", "RP", "P(BJL2|XBQ)"),
    ("P(I0 · BJL2)", "I0", "P(BJL2|XBQ)"),
]


def write_plot(traces: Mapping[str, RawTrace], config: Mapping[str, Any]) -> dict[str, Any]:
    PLOTS.mkdir(parents=True, exist_ok=True)
    input_path = ANALYSIS / "plot_input.csv"
    output_path = PLOTS / "RESULT_OVERVIEW.html"
    columns = [label for label, _case, _signal in PLOT_SPECS]
    # Cache every selected series before writing rows.  Recomputing a complete
    # continuous unwrap inside the row loop would turn this derived-artifact
    # writer into an accidental O(N^2) operation for the 13,599-sample raw.
    series_cache: dict[tuple[str, str], tuple[float, ...]] = {}
    for _label, case, signal in PLOT_SPECS:
        key = (case, signal)
        if key not in series_cache:
            series_cache[key] = (
                phase_radians(traces[case], signal, config)
                if phase_unit(signal)
                else selected(traces[case], signal, config)
            )
    with input_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["time", *columns])
        for index, time_value in enumerate(traces["P0"].time):
            row: list[float] = [time_value]
            for _label, case, signal in PLOT_SPECS:
                row.append(series_cache[(case, signal)][index])
            writer.writerow(row)
    command = [
        sys.executable,
        str(REPO / "scripts/josim-plot2.py"),
        str(input_path),
        "-t",
        "sep_comb",
        "-c",
        "dark",
        "-j",
        "2pi",
        "-s",
        *columns,
        "-x",
        str(output_path),
        "-w",
        "BVM→QB P0 current replay Quick：关键输入与 QB 轨迹",
    ]
    plot_run = subprocess.run(command, cwd=REPO, capture_output=True, text=True, check=False)
    (ROOT / "logs/plotter.stdout.txt").write_text(plot_run.stdout, encoding="utf-8")
    (ROOT / "logs/plotter.stderr.txt").write_text(plot_run.stderr, encoding="utf-8")
    if plot_run.returncode != 0 or not output_path.is_file() or output_path.stat().st_size == 0:
        raise RuntimeError(f"josim-plot2 failed with exit {plot_run.returncode}: {plot_run.stderr[-1000:]}")
    html = output_path.read_text(encoding="utf-8")
    missing = [column for column in columns if column not in html]
    if missing:
        raise RuntimeError(f"plot HTML does not contain selected labels: {missing}")
    metadata = {
        "schema_version": "CLASSIC_JOSIM_PLOT_V1",
        "generated_at": now(),
        "experiment_id": rel(ROOT),
        "plot_path": rel(output_path),
        "derived_input": rel(input_path),
        "generated_from": "scripts/josim-plot2.py",
        "style": "CLASSIC_LOCKED",
        "mode": "compact",
        "profile": "sep_comb/dark/-j 2pi",
        "command": command,
        "plotter_exit_code": plot_run.returncode,
        "group_count": 7,
        "signal_count": len(columns),
        "key_groups": [
            "input current",
            "BJs phase",
            "BJL1 phase",
            "L1 current",
            "RB current",
            "L2 current",
            "BJL2 phase",
        ],
        "columns": columns,
        "phase_input_semantics": "continuous unwrapped raw radians; plot2 displays P columns as rad/(2*pi) turns",
        "scientific_authority": "raw evidence and analysis report; visualization is descriptive and not event/Gate authority",
        "input_snapshot": file_snapshot(input_path, relative_to=REPO),
        "output_snapshot": file_snapshot(output_path, relative_to=REPO),
    }
    (PLOTS / "RESULT_OVERVIEW.metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return metadata


def execution_record() -> dict[str, Any]:
    path = ROOT / "logs/execution.json"
    if not path.is_file():
        return {"status": "MISSING", "exit_code": None}
    record = json.loads(path.read_text(encoding="utf-8"))
    record["status"] = "PASS" if record.get("exit_code") == 0 else "FAIL"
    return record


def closure_ready(input_result: Mapping[str, Any], pre_result: Mapping[str, Any], artifact_valid: bool) -> bool:
    return artifact_valid and input_result.get("status") == "PASS" and pre_result.get("status") == "PASS"


def outcome(
    input_result: Mapping[str, Any],
    pre_result: Mapping[str, Any],
    closure: Mapping[str, Any],
    strict_closure: Mapping[str, Any] | None,
    artifact_valid: bool,
    config: Mapping[str, Any],
) -> tuple[str, str, dict[str, Any]]:
    if not artifact_valid or input_result.get("status") != "PASS" or pre_result.get("status") != "PASS":
        return "REPLAY_INVALID", "QUICK_INVALID", {"reason": "artifact, input fidelity, or PRE gate failed"}
    records = [
        item
        for window in closure.get("records", {}).values()
        for item in window.values()
        if item.get("C_x") is not None
    ]
    threshold = float(config["trajectory_closure_rule"]["threshold"])
    qualified = bool(records) and all(float(item["C_x"]) <= threshold for item in records) and bool(strict_closure and strict_closure.get("status") == "PASS")
    narrow = [float(item["C_x"]) for item in records if float(item["C_x"]) > threshold]
    partial = bool(strict_closure and strict_closure.get("status") == "PASS") and len(narrow) == 1 and narrow[0] <= 0.20 and len(records) >= 1
    details = {
        "nondegenerate_ratio_count": len(records),
        "ratio_threshold": threshold,
        "ratios_above_threshold": narrow,
        "qualified_rule_satisfied": qualified,
        "partial_rule_satisfied": partial,
        "strict_local_closure_status": strict_closure.get("status") if strict_closure else None,
    }
    if qualified:
        return "CURRENT_REPLAY_FIXTURE_QUALIFIED", "QUICK_PROMISING", details
    if partial:
        return "PARTIAL_CURRENT_REPLAY_CLOSURE", "QUICK_AMBIGUOUS", details
    return "CURRENT_ONLY_REPLAY_INSUFFICIENT", "QUICK_OPPOSITE", details


def fmt(value: Any, digits: int = 8) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, bool):
        return "PASS" if value else "FAIL"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if not math.isfinite(number):
        return "N/A"
    return f"{number:.{digits}g}"


def strict_row(case: str, value: Mapping[str, Any]) -> str:
    segment = value.get("largest_monotonic_segment") or {}
    post = value.get("post_boundedness") or {}
    return (
        f"| {case} | `{value.get('compatibility_classification')}` | "
        f"[{fmt(segment.get('start_time_ps'))}, {fmt(segment.get('end_time_ps'))}] ps | "
        f"{fmt(segment.get('phase_reported_turns'))} | {fmt(segment.get('area_reported_turns'))} | "
        f"{fmt(segment.get('phase_area_residual_turns'))} | {fmt(value.get('complete_segment_count'))} | "
        f"{str(value.get('second_complete_segment_present'))} | {fmt(post.get('bounded'))} |"
    )


def write_reports(
    config: Mapping[str, Any],
    metrics: Mapping[str, Any],
    plot: Mapping[str, Any],
    execution: Mapping[str, Any],
) -> None:
    input_result = metrics["input_replay_fidelity"]
    pre = metrics["pre_state"]
    disposition = metrics["disposition"]
    observations = [
        f"输入 fidelity：P0 `I(LIN|XBQ)` → RP `I(I_REPLAY)` 为 `{input_result['status']}`，exact grid={input_result['grid_identity']}，max error={fmt(input_result['max_abs_error_uA'])} µA，RMS={fmt(input_result['rms_error_uA'])} µA。",
        f"W2 PRE：{pre['status']}；五个 current 和三个 W2-median-centered phase 均按预注册阈值检查。",
        f"W3/W4 closure：共 {metrics['trajectory_closure']['summary']['nondegenerate_count']} 个非退化 Cx，最大 Cx={fmt(metrics['trajectory_closure']['summary']['max_C_x'])}。",
        f"RP BJL2 strict local：`{metrics['strict_local']['RP']['compatibility_classification']}`，P0 为 `{metrics['strict_local']['P0']['compatibility_classification']}`。",
        f"KCL：{metrics['kcl']['status']}（共享 `scripts/bvmtools/kcl.py`，tolerance={fmt(metrics['kcl']['tolerance_uA'])} µA）。",
    ]
    brief = [
        "# BVM_QB_P0_CURRENT_REPLAY_FIXTURE_QUICK_V1 — Result brief",
        "",
        f"结论标签：`{disposition['fixture_label']}` / `{disposition['quick_label']}`。",
        "",
        "## 改变、保持与目的",
        "",
        "- 改变：只新增一个 ideal current source RP，将 P0 完整 `I(LIN|XBQ)` 原样 replay 到 QB IN。",
        "- 保持：QB topology、Lin/L0/L1/L2、BJs/BJL1/BJL2、RJ1/RJ2/RB、IBIAS=35 µA、R_LOAD=10 Ω、JJ model、solver、步长和 stop time。",
        "- 目的：判断 current-only replay 是否足以复现 P0 的输入、PRE 与内部轨迹；I0 仅作为既有 reference gap。",
        "",
        "## 关键观察",
        "",
    ]
    brief.extend(f"- {item}" for item in observations)
    brief += [
        "",
        "## 这意味着什么",
        "",
        f"- 当前单点、当前模型和冻结窗口下，结果属于 `{disposition['quick_label']}` 所对应的 exploratory evidence。",
        "- 任何 `C_x` 都只是 trajectory closure；strict BJL2 也只是同一 JJ 的 phase/area compatibility。",
        "",
        "## 不能证明什么",
        "",
        "- 不能把 phase turns 当成 SFQ count，不能证明 downstream/JTL delivery、source-impedance mechanism、硬件行为或 Formal BVM→QB Gate。",
        "- 不能外推到其他 READ 宽度、负载、偏置、Ic、时间步长或拓扑。",
        "",
        "## 后续可选项（本次不执行，最多三项）",
        "",
        "1. 在用户重新授权后，选择一个固定的 receiver-side follow-up 做独立验证。",
        "2. 在用户重新授权后，针对当前 fixture 设计最小的 source/load sensitivity 对照。",
        "3. 暂停实验，先由用户审阅 raw、closure 表和 strict local 证据。",
        "",
        f"最终工作流状态：`{metrics['workflow']['state']}` / `{metrics['workflow']['next_action']}`。",
    ]
    (ROOT / "RESULT_BRIEF.md").write_text("\n".join(brief) + "\n", encoding="utf-8")

    lines = [
        "# Analysis report — BVM_QB_P0_CURRENT_REPLAY_FIXTURE_QUICK_V1",
        "",
        f"生成时间：`{metrics['generated_at']}`；artifact status：`{metrics['artifact_status']}`；fixture：`{disposition['fixture_label']}`；Quick：`{disposition['quick_label']}`。",
        "",
        "## 1. Provenance and scope",
        "",
        f"- 新 science run：仅 `RP/run-01`，runner exit={execution.get('exit_code')}；P0/I0 raw 均复用，不重跑。",
        f"- solver：`{config['fixed_conditions']['solver']} {config['fixed_conditions']['solver_version']}`；`.tran {config['fixed_conditions']['timestep_ps']}p {config['fixed_conditions']['stop_ps']}p`。",
        f"- RP deck：`{config['candidate']['deck']}`；literal PWL pairs={config['candidate']['generation']['pairs_per_continuation_line']} per continuation line is the formatting block size, not a resampling operation.",
        "- 物理路径：P0 是 BVM→12×320 JSL→QB；RP 是 current-only ideal source→同一 QB；I0 是既有 ideal replay reference。",
        "",
        "## 2. Input replay fidelity",
        "",
        "| item | value |",
        "|---|---:|",
        f"| P0 samples | {input_result['sample_count_P0']} |",
        f"| RP samples | {input_result['sample_count_RP']} |",
        f"| exact time grid | `{input_result['grid_identity']}` |",
        f"| max abs error | {fmt(input_result['max_abs_error_uA'])} µA |",
        f"| RMS error | {fmt(input_result['rms_error_uA'])} µA |",
        f"| correlation | {fmt(input_result['correlation'])} |",
        f"| signed area difference | {fmt(input_result['area_difference']['signed_area_A_ps'])} A·ps |",
        f"| positive area difference | {fmt(input_result['area_difference']['positive_area_A_ps'])} A·ps |",
        f"| negative area difference | {fmt(input_result['area_difference']['negative_area_A_ps'])} A·ps |",
        f"| fidelity disposition | `{input_result['status']}` |",
        "",
        "面积是同一输入波形的 waveform diagnostic；它不是 SFQ quantity。若本节失败，则不解释下列 W3/W4。",
        "",
        "## 3. W2 PRE state",
        "",
        f"判定：`{pre['status']}`；current max-abs limit={config['pre_state_rule']['current_max_abs_difference_uA']} µA，phase max-abs limit={config['pre_state_rule']['phase_max_abs_difference_turns']} turns。",
        "",
        "| signal | unit | max abs difference | pass |",
        "|---|---|---:|---|",
    ]
    for signal, item in pre.get("signals", {}).items():
        lines.append(f"| `{signal}` | {item.get('unit')} | {fmt(item.get('max_abs_difference'))} | `{fmt(item.get('pass'))}` |")
    lines += [
        "",
        "phase 在每个 case 内先完整 continuous unwrap，再用各自 W2 median 居中；没有以 active/read response 设阈值。",
        "",
        "## 4. W3/W4 trajectory closure",
        "",
        f"公式：`{metrics['trajectory_closure']['formula']}`；reference gap floor 按单位固定。当前 summary：nondegenerate={metrics['trajectory_closure']['summary']['nondegenerate_count']}，pass={metrics['trajectory_closure']['summary']['pass_count']}，max Cx={fmt(metrics['trajectory_closure']['summary']['max_C_x'])}。",
        "",
        "| window | signal | unit | RMS(RP-P0) | RMS(I0-P0) | Cx | Cx status |",
        "|---|---|---|---:|---:|---:|---|",
    ]
    for window_name in ("W3_read", "W4_post_read_observation"):
        for signal, item in metrics["trajectory_closure"]["records"].get(window_name, {}).items():
            lines.append(f"| {window_name} | `{signal}` | {item['unit']} | {fmt(item['RP_minus_P0_RMS'])} | {fmt(item['I0_minus_P0_RMS'])} | {fmt(item['C_x'])} | `{item['C_x_status']}` |")
    lines += [
        "",
        "Supporting currents (`I(RJ1)`, `I(RB)`, `I(RJ2)`, `I(L0)`) are retained in `metrics.json`; they are not added to the compact plot or promotion criterion。",
        "",
        "## 5. BJL2 strict local result",
        "",
        "| case | classification | largest segment | phase delta (turns) | same-segment area (Phi0) | residual (turns) | complete n | second complete | post bounded |",
        "|---|---|---|---:|---:|---:|---:|---|---|",
    ]
    for case in ("P0", "RP", "I0"):
        lines.append(strict_row(case, metrics["strict_local"][case]))
    strict_close = metrics.get("strict_local_closure", {})
    lines += [
        "",
        f"P0↔RP strict local closure：`{strict_close.get('status')}`；classification match=`{strict_close.get('classification_matches')}`；same-segment phase/area/endpoint differences 分别为 {fmt((strict_close.get('absolute_differences') or {}).get('phase_reported_turns'))} turns、{fmt((strict_close.get('absolute_differences') or {}).get('area_reported_turns'))} Φ0、{fmt(strict_close.get('endpoint_max_abs_difference_ps'))} ps。",
        "- 该表沿用 shared `StrictLocalEventSpec`/`strict_event_summary`：activity `[95,115) ps`，post `[115,130) ps`，tail `[125,130) ps`；local compatibility 不是 SFQ count、downstream delivery 或 system Gate。",
        "",
        "## 6. KCL",
        "",
        f"实现：`{metrics['kcl']['implementation']}`；全 case/window/equation status=`{metrics['kcl']['status']}`，tolerance={metrics['kcl']['tolerance_uA']} µA。四条方程、每个窗口的 max/p95/RMS 在 `metrics.json` 中完整保留。",
        "",
        "## 7. Strict-anchor regression",
        "",
        f"既有 9 ps / 13 ps replay anchors：`{metrics['strict_anchor_regression']['status']}`；该检查只消费历史 strict summary，不重跑历史 raw。13 ps I0 当前复算也列在该字段中。",
        "",
        "## 8. Evidence labels",
        "",
        "### Observed",
        "",
        "- RP 是唯一新增 JoSIM raw；P0/I0 raw、QB/JJ snapshots 和现有 9/13 ps strict anchor 均保留。",
        "- CSV 时间列、信号列、raw hash、runner command/exit、solver provenance 和唯一 plot 输入/输出均有记录。",
        "",
        "### Derived",
        "",
        "- 输入误差、PRE 差异、W3/W4 RMS、Cx、KCL residual 和同一 BJL2 的 phase/area 数值均由 raw 直接计算；没有插值。",
        "- 相位报告统一为 continuous unwrap(raw radians)/(2π) turns；图只显示关键数据。",
        "",
        "### Inference",
        "",
        f"- 在本次冻结条件下，fixture disposition 是 `{disposition['fixture_label']}`；这只回答 current-only replay 是否可作为隔离夹具。",
        "",
        "### Unknown / not proven",
        "",
        "- 没有证明物理 BVM→QB route 已解决，没有证明 source impedance 是唯一机制，没有证明 SFQ delivery、硬件行为、timestep convergence 或 Formal Gate。",
        "",
        "## 9. Visualization and stop",
        "",
        f"- 唯一图：`{plot.get('plot_path', plot.get('path'))}`；`{plot['style']}`，`{plot['profile']}`，{plot['group_count']} groups / {plot['signal_count']} key traces。",
        f"- 最终 workflow：`{metrics['workflow']['state']}`，`{metrics['workflow']['next_action']}`；user_reviewed=false，next_step_authorized=false，automatic flags=false。",
    ]
    (ANALYSIS / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_gate(metrics: Mapping[str, Any]) -> None:
    gate = {
        "task_id": "BVM_QB_P0_CURRENT_REPLAY_FIXTURE_QUICK_V1",
        "state": "AWAITING_USER_REVIEW",
        "outcome": metrics["disposition"]["fixture_label"],
        "quick_label": metrics["disposition"]["quick_label"],
        "physical_disposition": "EXPLORATORY_ONLY",
        "user_reviewed": False,
        "next_step_authorized": False,
        "next_action": "STOP",
        "automatic_promotion": False,
        "automatic_next_experiment": False,
        "new_science_runs": 1,
        "created_at": now(),
        "note": "One authorized current-replay Quick Probe complete; await user review. No automatic follow-up.",
    }
    (ANALYSIS / "human-gate.yaml").write_text(yaml.safe_dump(gate, allow_unicode=True, sort_keys=False), encoding="utf-8")


def main() -> int:
    config = load_config()
    traces, raw_records = load_traces(config)
    metric_path = resolve(config["strict_event"]["metric_spec"]["path"])
    metric_hash = sha256_file(metric_path)
    if metric_hash != config["strict_event"]["metric_spec"]["sha256"]:
        raise RuntimeError("metric spec hash differs from frozen preregistration")
    execution = execution_record()
    raw_valid = all(record["qa"]["status"] == "VALID" and record["configured_hash_match"] for record in raw_records.values())
    artifact_valid = raw_valid and execution.get("exit_code") == 0
    input_result = input_fidelity(traces, config) if artifact_valid else {
        "status": "FAIL",
        "grid_identity": False,
        "max_abs_error_uA": math.inf,
        "rms_error_uA": math.inf,
        "correlation": None,
        "area_difference": {},
        "interpretation_allowed": False,
    }
    pre_result = pre_state(traces, config) if artifact_valid and input_result.get("status") == "PASS" else {
        "status": "SKIPPED_INPUT_FIDELITY_FAIL",
        "signals": {},
        "interpretation_allowed": False,
    }
    interpretation_allowed = closure_ready(input_result, pre_result, artifact_valid)
    if interpretation_allowed:
        closure = trajectory_closure(traces, config)
        closure["supporting"] = supporting_trajectory(traces, config)
        metric_strict = {case: strict_for(case, traces[case], raw_records[case]["sha256"], config, metric_hash) for case in ("P0", "RP", "I0")}
        strict_close = strict_local_closure(metric_strict, config)
        anchors = strict_anchor_regression(config, metric_strict)
    else:
        closure = {"status": "SKIPPED_PRECONDITION_FAIL", "records": {}, "summary": {"nondegenerate_count": 0, "pass_count": 0, "max_C_x": None}, "supporting": {}}
        metric_strict = {case: {"status": "SKIPPED_PRECONDITION_FAIL", "compatibility_classification": None} for case in ("P0", "RP", "I0")}
        strict_close = {"status": "SKIPPED_PRECONDITION_FAIL"}
        anchors = {"status": "SKIPPED_PRECONDITION_FAIL"}
    if interpretation_allowed:
        all_records = [item for window in closure["records"].values() for item in window.values()]
        ratios = [float(item["C_x"]) for item in all_records if item.get("C_x") is not None]
        closure["summary"] = {
            "nondegenerate_count": len(ratios),
            "pass_count": sum(value <= float(config["trajectory_closure_rule"]["threshold"]) for value in ratios),
            "max_C_x": max(ratios) if ratios else None,
        }
    kcl = kcl_results(traces, config) if artifact_valid else {"status": "SKIPPED_ARTIFACT_INVALID", "implementation": "scripts/bvmtools/kcl.py"}
    fixture_label, quick_label, outcome_details = outcome(input_result, pre_result, closure, strict_close, artifact_valid, config)
    plot = write_plot(traces, config) if artifact_valid else {"path": None, "style": "CLASSIC_LOCKED", "profile": "sep_comb/dark/-j 2pi", "group_count": 0, "signal_count": 0}
    analysis_script_paths = [ROOT / "analysis/analyze_replay.py", ROOT / "analysis/build_replay_deck.py", ROOT / "analysis/run_once.py", ROOT / "analysis/review_replay.py"]
    metrics: dict[str, Any] = {
        "schema_version": "BVM_QB_P0_CURRENT_REPLAY_FIXTURE_QUICK_V1",
        "generated_at": now(),
        "status": "AWAITING_USER_REVIEW",
        "artifact_status": "VALID" if artifact_valid else "INVALID",
        "disposition": {
            "fixture_label": fixture_label,
            "quick_label": quick_label,
            "physical_disposition": "EXPLORATORY_ONLY",
            "details": outcome_details,
        },
        "new_science_runs": [{"case": "RP", "run_id": "RP/run-01", "raw": rel(resolve(config["candidate"]["raw"]))}],
        "new_science_run_count": 1,
        "input_replay_fidelity": input_result,
        "pre_state": pre_result,
        "trajectory_closure": closure,
        "strict_local": metric_strict,
        "strict_local_closure": strict_close,
        "strict_anchor_regression": anchors,
        "kcl": kcl,
        "raw_records": raw_records,
        "execution": execution,
        "full_time_grid_exact": all(exact_time_grid_identity(traces["P0"].time, traces[key].time) for key in ("I0", "RP")),
        "metric_spec": {"path": rel(metric_path), "sha256": metric_hash, "version": config["strict_event"]["metric_spec"]["version"]},
        "visualization": plot,
        "workflow": {
            "state": "AWAITING_USER_REVIEW",
            "user_reviewed": False,
            "next_step_authorized": False,
            "next_action": "STOP",
            "automatic_promotion": False,
            "automatic_next_experiment": False,
        },
        "interpretation_boundary": "Exploratory current-replay fixture only; no system Gate, SFQ count, downstream delivery, mechanism proof, or hardware claim.",
    }
    (ANALYSIS / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    provenance = {
        "task_id": config["id"],
        "generated_at": metrics["generated_at"],
        "repository": git_snapshot(REPO),
        "head_before_gate_transition": config["head_before_gate_transition"],
        "authorization_gate_transition_commit": config["authorization_gate_transition_commit"],
        "preflight_head": config["preflight_head"],
        "preflight_base_after_authorization": config["base_head_after_authorization"],
        "solver": solver_provenance(REPO / config["fixed_conditions"]["solver"], cwd=REPO),
        "metric_spec": file_snapshot(metric_path, relative_to=REPO),
        "references": {
            "P0_raw": raw_records["P0"],
            "I0_raw": raw_records["I0"],
            "P0_deck": file_snapshot(resolve(config["references"]["P0"]["deck"]), relative_to=REPO),
            "I0_deck": file_snapshot(resolve(config["references"]["I0"]["deck"]), relative_to=REPO),
            "QB_snapshot": file_snapshot(ROOT / config["references"]["qb_snapshot"]["path"], relative_to=REPO),
            "JJ_snapshot": file_snapshot(ROOT / config["references"]["jj_snapshot"]["path"], relative_to=REPO),
        },
        "candidate": {
            "deck": file_snapshot(ROOT / config["candidate"]["deck"], relative_to=REPO),
            "raw": raw_records["RP"],
            "execution": execution,
        },
        "analysis_scripts": {rel(path): sha256_file(path) for path in analysis_script_paths},
        "independent_review": file_snapshot(ANALYSIS / "independent_review.json", relative_to=REPO) if (ANALYSIS / "independent_review.json").is_file() else None,
        "commands": {
            "deck_generation": "python3 analysis/build_replay_deck.py",
            "science_run": execution.get("command"),
            "analysis": [sys.executable, rel(ROOT / "analysis/analyze_replay.py")],
            "independent_review": [sys.executable, rel(ROOT / "analysis/review_replay.py")],
            "plot": plot.get("command"),
        },
        "fixed_conditions": config["fixed_conditions"],
        "orientation_verification": json.loads((ROOT / "logs/generate-deck.json").read_text(encoding="utf-8")) if (ROOT / "logs/generate-deck.json").is_file() else None,
        "visualization": plot,
        "no_historical_raw_rewrite": True,
    }
    (ANALYSIS / "provenance.json").write_text(json.dumps(provenance, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_gate(metrics)
    write_reports(config, metrics, plot, execution)
    print(json.dumps({
        "status": metrics["status"],
        "artifact_status": metrics["artifact_status"],
        "fixture_label": fixture_label,
        "quick_label": quick_label,
        "input_replay_fidelity": input_result["status"],
        "pre_state": pre_result["status"],
        "strict_RP": metric_strict["RP"].get("compatibility_classification"),
        "strict_P0": metric_strict["P0"].get("compatibility_classification"),
        "plot": plot.get("plot_path", plot.get("path")),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (KeyError, RuntimeError, ValueError) as error:
        print(f"analyze_replay: {error}", file=sys.stderr)
        raise SystemExit(2)
