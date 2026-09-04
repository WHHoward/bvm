#!/usr/bin/env python3
"""Read-only analysis of the historical single-BVM versus 4-BVM 1000 fixture.

This task deliberately consumes existing raw CSVs only.  It does not run a
JoSIM simulation, alter a deck, or implement a second raw/phase/SFQ parser.
The
task-local code owns only the comparison windows, signal mapping, derived
delta waveforms, timing correlation, and report wording.
"""

from __future__ import annotations

import csv
import json
import math
import statistics
import subprocess
import sys
from collections import OrderedDict
from datetime import datetime
from pathlib import Path
from typing import Iterable, Mapping, Sequence


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
SINGLE_ROOT = REPO / "test/exploration/bvmsim-jm2-connected-single-ab-v1-20260903"
FOUR_ROOT = REPO / "test/exploration/bvmsim-4bvm-jm2-connected-state-position-ab-v1-20260903"
VARIANT = SINGLE_ROOT / "variants/bvm_jm2_connected.cir"
HISTORICAL_BVM = REPO / "BVMSim/bvm_cell.cir"
HISTORICAL_QB = REPO / "BVMSim/BQ.cir"
HISTORICAL_JTL = REPO / "BVMSim/library_josim/jtl2.cir"
SHARED_JJMIT = REPO / "circuits/models/jjmit.cir"
CANONICAL_BVM = REPO / "circuits/bvm/bvm_cell.cir"
PLOTTER = REPO / "scripts/josim-plot2.py"
SOLVER = REPO / "build/josim-cli"

SINGLE_RUNS = {
    "S0": SINGLE_ROOT / "runs/S0-J-JM2C/raw/run-01.csv",
    "S1": SINGLE_ROOT / "runs/S1-J-JM2C/raw/run-01.csv",
}
FOUR_RUNS = {
    "1000": FOUR_ROOT / "runs/1000/raw.csv",
    "0000": FOUR_ROOT / "runs/0000/raw.csv",
}

# Existing task-local protocol windows.  The single reference's final 5 ps
# before READ is used to match the 4-BVM PRE_READ1 window exactly in duration.
SINGLE_WINDOWS_PS = OrderedDict(
    (
        ("PRE_READ", (65.0, 70.0)),
        ("READ", (70.0, 82.0)),
        ("EARLY_RESPONSE", (82.0, 100.0)),
        ("TAIL", (170.0, 200.0)),
        ("READ_OVERLAY", (70.0, 130.0)),
    )
)
FOUR_WINDOWS_PS = OrderedDict(
    (
        ("PRE_READ1", (105.0, 110.0)),
        ("READ1", (110.0, 170.0)),
        ("EARLY_RESPONSE", (121.0, 140.0)),
        ("TAIL", (170.0, 200.0)),
        ("READ_OVERLAY", (110.0, 170.0)),
    )
)

JJ_NAMES = ("JM1", "JM2", "JS1", "JS2")
STORAGE_BRANCHES = ("L_M1", "L_M2", "L_M3", "L_PM")
SENSING_BRANCHES = ("L_PSL", "L_SL")
ALL_BRANCHES = STORAGE_BRANCHES + SENSING_BRANCHES

PRE_READ_SIGNAL_NAMES = (
    "JM1_phase",
    "JM2_phase",
    "L_M1",
    "L_M2",
    "L_M3",
    "L_PM",
    "L_PSL",
    "L_SL",
    "SL_voltage",
)


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO.resolve()).as_posix()


def sha256(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def json_write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def ps_window(kind: str, name: str) -> tuple[float, float]:
    source = SINGLE_WINDOWS_PS if kind == "single" else FOUR_WINDOWS_PS
    left, right = source[name]
    return left * 1.0e-12, right * 1.0e-12


def indices(trace, bounds: tuple[float, float]) -> tuple[int, ...]:
    from bvmtools.phase import window_indices

    return window_indices(trace.time, *bounds)


def values(trace, label: str) -> tuple[float, ...]:
    # Raw headers are checked before this call.  RawTrace refuses implicit
    # selection of duplicate labels, so no pandas-style renaming is possible.
    return trace.column(label)  # type: ignore[return-value]


def phase_label(junction: str, number: int) -> str:
    return f"P(B_{junction}|XBVM{number})"


def voltage_label(junction: str, number: int) -> str:
    return f"V(B_{junction}|XBVM{number})"


def current_label(junction: str, number: int) -> str:
    return f"I(B_{junction}|XBVM{number})"


def branch_label(branch: str, number: int) -> str:
    return f"I({branch}|XBVM{number})"


def all_bvm_labels(number: int) -> tuple[str, ...]:
    labels: list[str] = []
    for junction in JJ_NAMES:
        labels.extend((phase_label(junction, number), voltage_label(junction, number), current_label(junction, number)))
    labels.extend(branch_label(branch, number) for branch in ALL_BRANCHES)
    labels.append(f"V(SL{number})")
    return tuple(labels)


def require_labels(trace, labels: Iterable[str], context: str) -> None:
    if trace.duplicate_columns:
        raise RuntimeError(f"{context}: duplicate raw columns {trace.duplicate_columns}")
    missing = [label for label in labels if label not in trace.headers]
    if missing:
        raise RuntimeError(f"{context}: missing exact labels {missing}")


def grid_fact(trace) -> dict[str, object]:
    dt_ps = [float(value) * 1.0e12 for value in trace.dt]
    gaps = [
        {
            "from_ps": float(trace.time[index]) * 1.0e12,
            "to_ps": float(trace.time[index + 1]) * 1.0e12,
            "dt_ps": dt_ps[index],
        }
        for index in range(len(dt_ps))
        if dt_ps[index] > 0.11
    ]
    return {
        "sample_count": trace.sample_count,
        "start_ps": float(trace.time[0]) * 1.0e12,
        "end_ps": float(trace.time[-1]) * 1.0e12,
        "dt_min_ps": min(dt_ps),
        "dt_max_ps": max(dt_ps),
        "uniform": all(value == dt_ps[0] for value in dt_ps),
        "large_gaps": gaps,
        "duplicate_columns": trace.duplicate_columns,
        "interpolation": "none",
    }


def shifted_grid_ps(trace, bounds: tuple[float, float]) -> tuple[float, ...]:
    selected = indices(trace, bounds)
    if len(selected) < 2:
        raise RuntimeError(f"window has fewer than two samples: {bounds}")
    origin = trace.time[selected[0]]
    # This is a representation of the existing sample positions after a
    # declared time-origin shift, not interpolation or resampling.
    return tuple(round((trace.time[index] - origin) * 1.0e12, 12) for index in selected)


def exact_shifted_grid(trace_a, bounds_a: tuple[float, float], trace_b, bounds_b: tuple[float, float]) -> dict[str, object]:
    grid_a = shifted_grid_ps(trace_a, bounds_a)
    grid_b = shifted_grid_ps(trace_b, bounds_b)
    return {
        "exact_shifted_grid": grid_a == grid_b,
        "sample_count_a": len(grid_a),
        "sample_count_b": len(grid_b),
        "relative_grid_a_ps": list(grid_a),
        "relative_grid_b_ps": list(grid_b),
        "interpolation": "none",
    }


def local_arrays(trace, label: str, bounds: tuple[float, float], *, phase: bool = False) -> tuple[list[float], list[float]]:
    selected = indices(trace, bounds)
    time = [float(trace.time[index]) for index in selected]
    raw = values(trace, label)
    if phase:
        from bvmtools.phase import continuous_unwrap

        unwrapped = continuous_unwrap(raw)
        data = [float(unwrapped[index]) for index in selected]
    else:
        data = [float(raw[index]) for index in selected]
    return time, data


def display_factor(kind: str) -> tuple[float, str, str]:
    if kind == "A":
        return 1.0e6, "uA", "uA*ps"
    if kind == "V":
        return 1.0e3, "mV", "mV*ps"
    if kind == "P":
        return 1.0 / (2.0 * math.pi), "turns (rad/2pi)", "turns*ps"
    raise ValueError(kind)


def kind_for_label(label: str) -> str:
    prefix = label[0]
    return {"I": "A", "V": "V", "P": "P"}[prefix]


def scaled_stats(time_s: Sequence[float], data: Sequence[float], kind: str, *, peak_time_offset_ps: float = 0.0) -> dict[str, object]:
    from bvmtools.waveform import waveform_metrics

    if len(time_s) != len(data) or len(data) < 2:
        raise ValueError("statistics require equal arrays with at least two samples")
    factor, unit, area_unit = display_factor(kind)
    base = waveform_metrics(time_s, data)
    abs_index = max(range(len(data)), key=lambda index: abs(float(data[index])))
    return {
        "kind": kind,
        "unit": unit,
        "area_unit": area_unit,
        "sample_count": len(data),
        "minimum": float(base["minimum"]) * factor,
        "maximum": float(base["maximum"]) * factor,
        "p2p": float(base["p2p"]) * factor,
        "mean": float(base["mean"]) * factor,
        "median": float(base["median"]) * factor,
        "rms": float(base["rms"]) * factor,
        "max_abs": float(base["max_abs"]) * factor,
        "signed_time_integral": float(base["signed_time_integral"]) * factor * 1.0e12,
        "peak_value": float(base["peak_value"]) * factor,
        "peak_time_ps": float(base["peak_time"]) * 1.0e12 + peak_time_offset_ps,
        "minimum_value": float(base["minimum_value"]) * factor,
        "minimum_time_ps": float(base["minimum_time"]) * 1.0e12 + peak_time_offset_ps,
        "abs_peak_value": abs(float(data[abs_index])) * factor,
        "abs_peak_time_ps": float(time_s[abs_index]) * 1.0e12 + peak_time_offset_ps,
        "zero_crossing_count": int(base["zero_crossing_count"]),
    }


def metric(trace, label: str, bounds: tuple[float, float]) -> dict[str, object]:
    kind = kind_for_label(label)
    time, data = local_arrays(trace, label, bounds, phase=kind == "P")
    return scaled_stats(time, data, kind, peak_time_offset_ps=0.0)


def phase_area_fact(trace, junction: str, number: int, bounds: tuple[float, float]) -> dict[str, object]:
    from bvmtools.metrics import phase_area_window

    result = phase_area_window(
        trace.time,
        values(trace, phase_label(junction, number)),
        values(trace, voltage_label(junction, number)),
        bounds,
        voltage_to_phase_sign=1,
        reporting_direction=1,
        include_segments=False,
    )
    return {
        "phase_label": phase_label(junction, number),
        "voltage_label": voltage_label(junction, number),
        "phase_delta_turns": float(result["phase_delta_turns"]),
        "voltage_area_turns": float(result["voltage_area_turns"]),
        "phase_area_residual_turns": float(result["phase_area_residual_turns"]),
        "window_first_ps": float(result["window_first_ps"]),
        "window_last_ps": float(result["window_last_ps"]),
        "same_jj": True,
        "count_authority": False,
    }


def waveform_window(trace, label: str, bounds: tuple[float, float]) -> dict[str, object]:
    return metric(trace, label, bounds)


def pre_pattern(trace, number: int, bounds: tuple[float, float]) -> dict[str, object]:
    return {
        "LM1_mean_uA": waveform_window(trace, branch_label("L_M1", number), bounds)["mean"],
        "LM2_mean_uA": waveform_window(trace, branch_label("L_M2", number), bounds)["mean"],
        "LM3_mean_uA": waveform_window(trace, branch_label("L_M3", number), bounds)["mean"],
        "LPM_mean_uA": waveform_window(trace, branch_label("L_PM", number), bounds)["mean"],
    }


def retention(trace, number: int, pre_bounds: tuple[float, float], tail_bounds: tuple[float, float]) -> dict[str, object]:
    output: dict[str, object] = {}
    for name, label in (
        ("JM1_phase", phase_label("JM1", number)),
        ("JM2_phase", phase_label("JM2", number)),
        ("LM1", branch_label("L_M1", number)),
        ("LM2", branch_label("L_M2", number)),
        ("LM3", branch_label("L_M3", number)),
        ("LPM", branch_label("L_PM", number)),
    ):
        pre = metric(trace, label, pre_bounds)
        tail = metric(trace, label, tail_bounds)
        output[name] = {
            "pre_mean": pre["mean"],
            "tail_mean": tail["mean"],
            "tail_minus_pre_mean": float(tail["mean"]) - float(pre["mean"]),
            "pre_p2p": pre["p2p"],
            "tail_p2p": tail["p2p"],
            "display_unit": pre["unit"],
        }
    return output


def bvm_internal_summary(trace, number: int, windows: Mapping[str, tuple[float, float]]) -> dict[str, object]:
    signals: dict[str, object] = {}
    for name, label in (
        *((f"{junction}_P", phase_label(junction, number)) for junction in JJ_NAMES),
        *((f"{junction}_V", voltage_label(junction, number)) for junction in JJ_NAMES),
        *((f"{junction}_I", current_label(junction, number)) for junction in JJ_NAMES),
        *((branch, branch_label(branch, number)) for branch in ALL_BRANCHES),
        ("SL_voltage", f"V(SL{number})"),
    ):
        signals[name] = {
            window_name: metric(trace, label, bounds)
            for window_name, bounds in windows.items()
        }
    phase_area: dict[str, object] = {}
    for junction in JJ_NAMES:
        phase_area[junction] = {
            window_name: phase_area_fact(trace, junction, number, bounds)
            for window_name, bounds in windows.items()
            if window_name in {"PRE_READ", "PRE_READ1", "READ", "READ1", "EARLY_RESPONSE", "TAIL"}
        }
    return {
        "signals": signals,
        "same_jj_phase_area": phase_area,
        "pre_read_pattern": pre_pattern(trace, number, next(iter(windows.values()))),
    }


def rjm1_kcl(trace, number: int, windows: Mapping[str, tuple[float, float]]) -> dict[str, object]:
    from bvmtools.kcl import kcl_window_metrics, linear_kcl_residual

    voltage = values(trace, voltage_label("JM1", number))
    jm1 = values(trace, current_label("JM1", number))
    lm1 = values(trace, branch_label("L_M1", number))
    rjm1 = tuple(float(value) / 8.0 for value in voltage)
    residual = linear_kcl_residual(
        {
            "I(L_M1)": lm1,
            "I(JM1)": jm1,
            "I(R_JM1_reconstructed)": rjm1,
        },
        {"I(L_M1)": 1.0, "I(JM1)": -1.0, "I(R_JM1_reconstructed)": -1.0},
    )
    result: dict[str, object] = {
        "topology_equation": "I(L_M1, 7->0) - I(B_JM1, 2->7) - V(B_JM1, 2-7)/8ohm = 0",
        "orientation": {
            "B_JM1": "2 -> 7",
            "R_JM1": "2 -> 7",
            "L_M1": "7 -> 0",
            "reconstructed_R_JM1": "V(B_JM1)/8ohm, same 2->7 sign",
        },
        "rjm1_current": {},
        "residual": {},
    }
    for window_name, bounds in windows.items():
        selected = indices(trace, bounds)
        local_time = [trace.time[index] for index in selected]
        result["rjm1_current"][window_name] = scaled_stats(  # type: ignore[index]
            local_time,
            [rjm1[index] for index in selected],
            "A",
        )
        result["residual"][window_name] = kcl_window_metrics(  # type: ignore[index]
            trace.time, residual, bounds, unit="A"
        )
    return result


def median_on_window(trace, label: str, bounds: tuple[float, float], *, phase: bool) -> float:
    _, data = local_arrays(trace, label, bounds, phase=phase)
    return float(statistics.median(data))


def delta_series(trace_a, trace_b, label: str, *, phase: bool) -> tuple[list[float], list[float]]:
    # Both 4-BVM traces are exact-grid identical.  The explicit check is kept
    # at the call site so this helper cannot silently interpolate.
    if trace_a.time != trace_b.time:
        raise RuntimeError("delta_series requires exact identical time grids")
    a = values(trace_a, label)
    b = values(trace_b, label)
    if phase:
        from bvmtools.phase import continuous_unwrap

        a = continuous_unwrap(a)
        b = continuous_unwrap(b)
    return [float(t) for t in trace_a.time], [float(x) - float(y) for x, y in zip(a, b)]


def delta_fact(trace_a, trace_b, label: str, windows: Mapping[str, tuple[float, float]]) -> dict[str, object]:
    kind = kind_for_label(label)
    phase = kind == "P"
    time, data = delta_series(trace_a, trace_b, label, phase=phase)
    if "PRE_READ1" not in windows:
        raise RuntimeError("difference-in-differences requires a PRE_READ1 centering window")
    # The centered READ/early-response values are explicitly centered by the
    # PRE_READ1 1000-minus-0000 median.  Do not recompute a different median
    # inside each later window: that would erase the state-conditioned level
    # change the comparison is intended to expose.
    pre_bounds = windows["PRE_READ1"]
    pre_median_a = median_on_window(trace_a, label, pre_bounds, phase=phase)
    pre_median_b = median_on_window(trace_b, label, pre_bounds, phase=phase)
    pre_offset = pre_median_a - pre_median_b
    output: dict[str, object] = {}
    for window_name, bounds in windows.items():
        selected = [index for index, value in enumerate(time) if bounds[0] <= value < bounds[1]]
        local_t = [time[index] for index in selected]
        local_y = [data[index] for index in selected]
        raw = scaled_stats(local_t, local_y, kind)
        centered = [data[index] - pre_offset for index in selected]
        centered_stats = scaled_stats(local_t, centered, kind)
        output[window_name] = {
            "raw_1000_minus_0000": raw,
            "centered_difference_in_differences": centered_stats,
            "pre_median_1000_raw": pre_median_a,
            "pre_median_0000_raw": pre_median_b,
            "center_offset_raw": pre_offset,
        }
    return {"label": label, "kind": kind, "windows": output}


def comparison_stats(
    reference_trace,
    reference_bounds: tuple[float, float],
    target_trace,
    target_bounds: tuple[float, float],
    label_reference: str,
    label_target: str,
    *,
    phase: bool,
    normalize_phase_to_local_start: bool = False,
) -> dict[str, object]:
    grid = exact_shifted_grid(reference_trace, reference_bounds, target_trace, target_bounds)
    if not grid["exact_shifted_grid"]:
        raise RuntimeError(f"non-identical shifted grids for {label_reference} / {label_target}")
    ref_time, ref = local_arrays(reference_trace, label_reference, reference_bounds, phase=phase)
    target_time, target = local_arrays(target_trace, label_target, target_bounds, phase=phase)
    if len(ref) != len(target):
        raise RuntimeError("comparison arrays have different lengths")
    # Remove only the initial phase offset for P overlays.  Current and voltage
    # retain their physical levels.
    if phase and normalize_phase_to_local_start:
        ref = [value - ref[0] for value in ref]
        target = [value - target[0] for value in target]
    difference = [float(right) - float(left) for left, right in zip(ref, target)]
    kind = "P" if phase else kind_for_label(label_reference)
    ref_stats = scaled_stats(ref_time, ref, kind)
    target_stats = scaled_stats(target_time, target, kind)
    diff_stats = scaled_stats(ref_time, difference, kind)
    from bvmtools.compare import compare_series

    # Compare on the explicitly verified shifted grid, represented from the
    # rounded stored-position tokens.  This avoids treating two equivalent
    # time origins (70 ps versus 110 ps) as an interpolation problem.
    ref_local_time = [float(value) * 1.0e-12 for value in grid["relative_grid_a_ps"]]
    target_local_time = [float(value) * 1.0e-12 for value in grid["relative_grid_b_ps"]]
    compared = compare_series(ref_local_time, ref, target_local_time, target, interpolation=None, include_correlation=True)
    ref_mean = float(ref_stats["mean"])
    target_mean = float(target_stats["mean"])
    denominator = max(
        abs(ref_mean),
        1.0e-12 if kind == "P" else 1.0e-6 if kind == "A" else 1.0e-6,
    )
    return {
        "grid": {
            "exact_shifted_grid": True,
            "sample_count": len(ref),
            "interpolation": "none",
            "relative_grid_ps": grid["relative_grid_a_ps"],
        },
        "reference": ref_stats,
        "target": target_stats,
        "target_minus_reference": diff_stats,
        "mean_difference_display": target_mean - ref_mean,
        "absolute_mean_difference_display": abs(target_mean - ref_mean),
        "relative_mean_difference": abs(target_mean - ref_mean) / denominator,
        "zero_lag_correlation": compared.get("correlation"),
        "phase_overlay_normalized_to_local_start": bool(phase and normalize_phase_to_local_start),
    }


def read_aligned_pair(trace_ref, ref_bounds, trace_target, target_bounds, label_ref, label_target, phase):
    ref_time, ref_data = local_arrays(trace_ref, label_ref, ref_bounds, phase=phase)
    target_time, target_data = local_arrays(trace_target, label_target, target_bounds, phase=phase)
    grid = exact_shifted_grid(trace_ref, ref_bounds, trace_target, target_bounds)
    if not grid["exact_shifted_grid"] or len(ref_data) != len(target_data):
        raise RuntimeError("aligned pair does not have an exact common stored grid")
    local_t = [float(value) - ref_time[0] for value in ref_time]
    if phase:
        ref_data = [value - ref_data[0] for value in ref_data]
        target_data = [value - target_data[0] for value in target_data]
    return local_t, ref_data, target_data


def timing_fact(
    time_s: Sequence[float],
    data: Sequence[float],
    kind: str,
    *,
    absolute_origin_ps: float,
    threshold_context: tuple[Sequence[float], Sequence[float]] | None = None,
    window_start_ps: float | None = None,
) -> dict[str, object]:
    from bvmtools.onset import first_persistent_exceedance

    factor, unit, _ = display_factor(kind)
    threshold = 1.0e-6 if kind in {"A", "V"} else None
    abs_index = max(range(len(data)), key=lambda index: abs(float(data[index])))
    window_first: dict[str, object] | None = None
    context_first: dict[str, object] | None = None
    window_first_status = "NOT_APPLICABLE"
    if threshold is not None:
        raw = first_persistent_exceedance(
            time_s,
            [abs(float(value)) for value in data],
            threshold,
            min_consecutive_samples=2,
        )
        window_first = dict(raw)
        for key in ("first_time_s", "persistence_start_s", "persistence_end_s"):
            if window_first.get(key) is not None:
                window_first[f"{key[:-2]}_ps"] = float(window_first[key]) * 1.0e12 + absolute_origin_ps
        window_first["meaning"] = "first persistent threshold sample inside the displayed window; descriptive activity only, not a response onset or SFQ count"
        window_first_status = "WITHIN_WINDOW_OR_NOT_FOUND"
        if threshold_context is not None:
            context_time_s, context_data = threshold_context
            context_raw = first_persistent_exceedance(
                context_time_s,
                [abs(float(value)) for value in context_data],
                threshold,
                min_consecutive_samples=2,
            )
            context_first = dict(context_raw)
            for key in ("first_time_s", "persistence_start_s", "persistence_end_s"):
                if context_first.get(key) is not None:
                    context_first[f"{key[:-2]}_ps"] = float(context_first[key]) * 1.0e12 + absolute_origin_ps
            context_first["meaning"] = "first persistent threshold sample in the pre-read-plus-read context; descriptive activity only"
            context_time_ps = context_first.get("first_time_ps")
            if context_time_ps is not None and window_start_ps is not None and float(context_time_ps) < window_start_ps - 1.0e-9:
                window_first_status = "PRE_EXISTING_ACTIVITY_LEFT_CENSORED"
            elif context_time_ps is None:
                window_first_status = "NO_PERSISTENT_THRESHOLD_IN_CONTEXT"
            else:
                window_first_status = "THRESHOLD_FIRST_OBSERVED_IN_OR_AFTER_WINDOW"
    return {
        "kind": kind,
        "unit": unit,
        "threshold_si": threshold,
        "threshold_meaning": "descriptive only" if threshold is not None else "not applicable",
        "max_abs": max(abs(float(value)) for value in data) * factor,
        "abs_peak_time_ps": float(time_s[abs_index]) * 1.0e12 + absolute_origin_ps,
        "window_first_persistent_exceedance": window_first,
        "context_first_persistent_exceedance": context_first,
        "window_first_status": window_first_status,
        "window_start_ps": window_start_ps,
    }


def pearson(a: Sequence[float], b: Sequence[float]) -> float | None:
    if len(a) != len(b) or not a:
        return None
    mean_a = sum(a) / len(a)
    mean_b = sum(b) / len(b)
    aa = [float(value) - mean_a for value in a]
    bb = [float(value) - mean_b for value in b]
    denominator = math.sqrt(sum(value * value for value in aa) * sum(value * value for value in bb))
    if denominator == 0.0:
        return 1.0 if aa == bb else None
    return sum(x * y for x, y in zip(aa, bb)) / denominator


def best_lag(left: Sequence[float], right: Sequence[float], time_s: Sequence[float], max_lag_ps: float = 20.0) -> dict[str, object]:
    if len(left) != len(right) or len(left) != len(time_s) or len(left) < 3:
        return {"status": "NOT_DEFINED"}
    dt_ps = statistics.median(
        (float(time_s[index + 1]) - float(time_s[index])) * 1.0e12
        for index in range(len(time_s) - 1)
    )
    max_samples = min(len(left) - 2, max(1, int(math.floor(max_lag_ps / dt_ps))))
    candidates: list[tuple[float, int, int]] = []
    # Positive lag means the right/downstream position is compared later than
    # the left/upstream position: left(t) with right(t + lag).
    for lag in range(-max_samples, max_samples + 1):
        if lag >= 0:
            a = left[: len(left) - lag] if lag else left
            b = right[lag:] if lag else right
        else:
            shift = -lag
            a = left[shift:]
            b = right[: len(right) - shift]
        coefficient = pearson(a, b)
        if coefficient is not None and math.isfinite(float(coefficient)):
            candidates.append((float(coefficient), lag, len(a)))
    if not candidates:
        return {"status": "NOT_DEFINED"}
    # Maximize correlation; retain the smallest absolute lag on ties.
    coefficient, lag, sample_count = max(candidates, key=lambda item: (item[0], -abs(item[1])))
    zero = pearson(left, right)
    return {
        "status": "VALID",
        "best_lag_samples": lag,
        "best_lag_ps": lag * dt_ps,
        "positive_lag_means_right_delayed": True,
        "best_lag_correlation": coefficient,
        "zero_lag_correlation": zero,
        "sample_count_at_best_lag": sample_count,
        "search_range_ps": [-max_samples * dt_ps, max_samples * dt_ps],
        "method": "existing exact samples; demeaned Pearson correlation; no interpolation",
    }


def write_csv(path: Path, time_s: Sequence[float], columns: Mapping[str, Sequence[float]]) -> None:
    if len(time_s) < 2:
        raise ValueError("derived CSV requires at least two time samples")
    if len(set(columns)) != len(columns):
        raise ValueError("derived CSV has duplicate labels")
    if any(len(data) != len(time_s) for data in columns.values()):
        raise ValueError("derived CSV columns have unequal lengths")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["time", *columns.keys()])
        for index, time in enumerate(time_s):
            writer.writerow([f"{float(time):.12e}", *[f"{float(data[index]):.12e}" for data in columns.values()]])


def run_plot(input_path: Path, output_path: Path, title: str, labels: Sequence[str]) -> dict[str, object]:
    command = [
        sys.executable,
        str(PLOTTER),
        str(input_path),
        "-x",
        str(output_path),
        "-t",
        "sep_comb",
        "-c",
        "dark",
        "-j",
        "2pi",
        "-w",
        title,
        "-s",
        *labels,
    ]
    result = subprocess.run(command, cwd=REPO, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"plot failed ({result.returncode}): {' '.join(command)}\n{result.stderr}")
    return {
        "path": rel(output_path),
        "input": rel(input_path),
        "title": title,
        "labels": list(labels),
        "command": [str(item) for item in command],
        "returncode": result.returncode,
        "renderer": rel(PLOTTER),
        "layout": "sep_comb",
        "color": "dark",
        "phase_jump": "2pi",
    }


def plot_standalone(trace, source_path: Path, number: int, state_name: str, title: str, output_name: str, kind: str, records: list[dict[str, object]]) -> None:
    labels = [
        phase_label("JM1", number),
        phase_label("JM2", number),
        phase_label("JS1", number),
        phase_label("JS2", number),
        branch_label("L_M1", number),
        branch_label("L_M2", number),
        branch_label("L_M3", number),
        branch_label("L_PM", number),
        branch_label("L_PSL", number),
        branch_label("L_SL", number),
        f"V(SL{number})",
    ]
    output = EXP / "plots" / f"{output_name}.html"
    records.append(run_plot(source_path, output, title, labels))


def build_overlay_csv(reference_trace, reference_bounds, target_trace, target_bounds, number: int, ref_name: str, target_name: str, output_path: Path) -> tuple[list[str], dict[str, object]]:
    pairs = [
        (phase_label(junction, 1), phase_label(junction, number), f"P({ref_name}_{junction})", f"P({target_name}_{junction})", True)
        for junction in JJ_NAMES
    ]
    pairs.extend(
        (branch_label(branch, 1), branch_label(branch, number), f"I({ref_name}_{branch})", f"I({target_name}_{branch})", False)
        for branch in ("L_M1", "L_M2", "L_M3", "L_PM", "L_PSL", "L_SL")
    )
    ref_time, _, _ = read_aligned_pair(reference_trace, reference_bounds, target_trace, target_bounds, pairs[0][0], pairs[0][1], True)
    columns: dict[str, Sequence[float]] = {}
    comparison: dict[str, object] = {}
    for ref_label, target_label, out_ref, out_target, is_phase in pairs:
        local_t, ref_data, target_data = read_aligned_pair(reference_trace, reference_bounds, target_trace, target_bounds, ref_label, target_label, is_phase)
        columns[out_ref] = ref_data
        columns[out_target] = target_data
        comparison[out_ref] = comparison_stats(
            reference_trace,
            reference_bounds,
            target_trace,
            target_bounds,
            ref_label,
            target_label,
            phase=is_phase,
            normalize_phase_to_local_start=True,
        )
    write_csv(output_path, [float(value) for value in ref_time], columns)
    return list(columns), {"comparison": comparison, "source_grid": "exact shifted stored timestamps; no interpolation"}


def build_delta_csv(trace_1000, trace_0000, number: int, output_path: Path, *, bounds: tuple[float, float]) -> tuple[list[str], dict[str, object]]:
    selected = indices(trace_1000, bounds)
    local_time = [float(trace_1000.time[index]) - float(trace_1000.time[selected[0]]) for index in selected]
    columns: dict[str, Sequence[float]] = {}
    labels: list[str] = []
    for junction in JJ_NAMES:
        label_1000 = phase_label(junction, number)
        label_0000 = phase_label(junction, number)
        _, delta = delta_series(trace_1000, trace_0000, label_1000, phase=True)
        out = f"P(Delta_{junction}_BVM{number})"
        columns[out] = [delta[index] for index in selected]
        labels.append(out)
    for branch in ("L_M1", "L_M2", "L_M3", "L_PM", "L_PSL", "L_SL"):
        label = branch_label(branch, number)
        _, delta = delta_series(trace_1000, trace_0000, label, phase=False)
        out = f"I(Delta_{branch}_BVM{number})"
        columns[out] = [delta[index] for index in selected]
        labels.append(out)
    sl_label = f"V(SL{number})"
    _, delta = delta_series(trace_1000, trace_0000, sl_label, phase=False)
    out = f"V(Delta_SL{number})"
    columns[out] = [delta[index] for index in selected]
    labels.append(out)
    write_csv(output_path, local_time, columns)
    return labels, {"time_origin_ps": float(trace_1000.time[selected[0]]) * 1.0e12, "window_ps": [bounds[0] * 1.0e12, bounds[1] * 1.0e12]}


def build_sensing_csv(trace_1000, trace_0000, output_path: Path, bounds: tuple[float, float]) -> tuple[list[str], dict[str, object]]:
    selected = indices(trace_1000, bounds)
    origin = trace_1000.time[selected[0]]
    columns: dict[str, Sequence[float]] = {}
    labels: list[str] = []
    for number in range(1, 5):
        label = f"V(SL{number})"
        _, delta = delta_series(trace_1000, trace_0000, label, phase=False)
        out = f"V(Delta_SL{number})"
        columns[out] = [delta[index] for index in selected]
        labels.append(out)
    write_csv(output_path, [float(trace_1000.time[index]) - float(origin) for index in selected], columns)
    return labels, {"time_origin_ps": float(origin) * 1.0e12, "window_ps": [bounds[0] * 1.0e12, bounds[1] * 1.0e12]}


def build_timing_csv(trace_1000, trace_0000, output_path: Path, bounds: tuple[float, float]) -> tuple[list[str], dict[str, object]]:
    selected = indices(trace_1000, bounds)
    origin = trace_1000.time[selected[0]]
    columns: dict[str, Sequence[float]] = {}
    labels: list[str] = []
    for number in range(1, 5):
        label = branch_label("L_SL", number)
        _, delta = delta_series(trace_1000, trace_0000, label, phase=False)
        out = f"I(Delta_LSL{number})"
        columns[out] = [delta[index] for index in selected]
        labels.append(out)
    for number in range(1, 5):
        label = f"V(SL{number})"
        _, delta = delta_series(trace_1000, trace_0000, label, phase=False)
        out = f"V(Delta_SL{number})"
        columns[out] = [delta[index] for index in selected]
        labels.append(out)
    write_csv(output_path, [float(trace_1000.time[index]) - float(origin) for index in selected], columns)
    return labels, {"time_origin_ps": float(origin) * 1.0e12, "window_ps": [bounds[0] * 1.0e12, bounds[1] * 1.0e12]}


def build_reconstruction_csv(trace, output_path: Path, bounds: tuple[float, float], *, residual: bool = False) -> tuple[list[str], dict[str, object]]:
    selected = indices(trace, bounds)
    origin = trace.time[selected[0]]
    columns: dict[str, Sequence[float]] = {}
    labels: list[str] = []
    for number in range(1, 5):
        voltage = values(trace, voltage_label("JM1", number))
        jm1 = values(trace, current_label("JM1", number))
        lm1 = values(trace, branch_label("L_M1", number))
        data = (
            [float(lm1[index]) - float(jm1[index]) - float(voltage[index]) / 8.0 for index in selected]
            if residual
            else [float(voltage[index]) / 8.0 for index in selected]
        )
        prefix = "KCL_RESIDUAL" if residual else "RJM1_RECON"
        out = f"I({prefix}_BVM{number})"
        columns[out] = data
        labels.append(out)
    write_csv(output_path, [float(trace.time[index]) - float(origin) for index in selected], columns)
    return labels, {"time_origin_ps": float(origin) * 1.0e12, "window_ps": [bounds[0] * 1.0e12, bounds[1] * 1.0e12], "unit_source": "A"}


def timing_analysis(trace_1000, trace_0000, bounds: tuple[float, float], early_bounds: tuple[float, float]) -> dict[str, object]:
    output: dict[str, object] = {"windows": {}, "pairwise_cross_correlation": {}}
    for window_name, window in (("READ1", bounds), ("EARLY_RESPONSE", early_bounds)):
        window_data: dict[str, object] = {}
        for signal_name, kind in (("V(SL)", "V"), ("I(L_SL)", "A"), ("V(JS1)", "V"), ("V(JS2)", "V"), ("I(L_M3)", "A"), ("I(L_PM)", "A")):
            position: dict[str, object] = {}
            for number in range(1, 5):
                label = f"V(SL{number})" if signal_name == "V(SL)" else branch_label("L_SL", number) if signal_name == "I(L_SL)" else voltage_label("JS1", number) if signal_name == "V(JS1)" else voltage_label("JS2", number) if signal_name == "V(JS2)" else branch_label("L_M3", number) if signal_name == "I(L_M3)" else branch_label("L_PM", number)
                time, data = delta_series(trace_1000, trace_0000, label, phase=False)
                selected = [index for index, value in enumerate(time) if window[0] <= value < window[1]]
                local_time = [time[index] for index in selected]
                local_data = [data[index] for index in selected]
                # The threshold diagnostic is also evaluated from PRE_READ1
                # through the displayed window.  If it is already active
                # before the window starts, the in-window first sample is
                # explicitly marked left-censored rather than called an
                # onset/propagation time.
                context_start = ps_window("four", "PRE_READ1")[0]
                context_selected = [index for index, value in enumerate(time) if context_start <= value < window[1]]
                context_time = [time[index] for index in context_selected]
                context_data = [data[index] for index in context_selected]
                position[f"BVM{number}"] = timing_fact(
                    local_time,
                    local_data,
                    kind,
                    absolute_origin_ps=0.0,
                    threshold_context=(context_time, context_data),
                    window_start_ps=window[0] * 1.0e12,
                )
            window_data[signal_name] = position
        output["windows"][window_name] = window_data

    for signal_name, kind in (("V(SL)", "V"), ("I(L_SL)", "A"), ("V(JS1)", "V"), ("V(JS2)", "V"), ("I(L_M3)", "A"), ("I(L_PM)", "A")):
        label_by_number = {
            number: f"V(SL{number})" if signal_name == "V(SL)" else branch_label("L_SL", number) if signal_name == "I(L_SL)" else voltage_label("JS1", number) if signal_name == "V(JS1)" else voltage_label("JS2", number) if signal_name == "V(JS2)" else branch_label("L_M3", number) if signal_name == "I(L_M3)" else branch_label("L_PM", number)
            for number in range(1, 5)
        }
        time0, delta0 = delta_series(trace_1000, trace_0000, label_by_number[1], phase=False)
        selected0 = [index for index, value in enumerate(time0) if bounds[0] <= value < bounds[1]]
        output["pairwise_cross_correlation"][signal_name] = {}
        for downstream in (2, 3, 4):
            time_n, delta_n = delta_series(trace_1000, trace_0000, label_by_number[downstream], phase=False)
            if time_n != time0:
                raise RuntimeError("cross-correlation requires exact 1000/0000 time grid")
            output["pairwise_cross_correlation"][signal_name][f"BVM1_vs_BVM{downstream}"] = best_lag(
                [delta0[index] for index in selected0],
                [delta_n[index] for index in selected0],
                [time0[index] for index in selected0],
            )
    return output


def source_snapshot(paths: Iterable[Path]) -> dict[str, object]:
    return {rel(path): {"sha256": sha256(path), "bytes": path.stat().st_size} for path in paths}


def format_number(value: object, digits: int = 4) -> str:
    if value is None:
        return "UNKNOWN"
    if isinstance(value, bool):
        return str(value)
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if not math.isfinite(number):
        return "UNKNOWN"
    return f"{number:.{digits}g}"


def plot_manifest(records: list[dict[str, object]], raw_hashes_before: Mapping[str, str], raw_hashes_after: Mapping[str, str]) -> dict[str, object]:
    return {
        "schema": "bvmsim-single-vs-1000-internal-read-coupling-plot-manifest-v1",
        "renderer": rel(PLOTTER),
        "renderer_sha256": sha256(PLOTTER),
        "layout": "sep_comb",
        "color": "dark",
        "phase_jump": "2pi",
        "phase_display": "P raw radians divided by 2*pi; labels are turns, never SFQ count",
        "standalone_before_comparison": True,
        "raw_hashes_before": dict(raw_hashes_before),
        "raw_hashes_after": dict(raw_hashes_after),
        "raw_unchanged": dict(raw_hashes_before) == dict(raw_hashes_after),
        "plots": records,
    }


def generate_report(metrics: Mapping[str, object]) -> str:
    single = metrics["single"]
    four = metrics["four"]
    dd = metrics["difference_in_differences"]
    pre_compare = metrics["pre_read_reference_comparison"]
    timing = metrics["timing"]
    observability = metrics["observability"]

    patterns = []
    for state in ("S0", "S1"):
        pattern = single[state]["pre_read_pattern"]
        patterns.append(
            f"- {state} PRE_READ 的循环电流均值（uA）：LM1={format_number(pattern['LM1_mean_uA'])}，LM2={format_number(pattern['LM2_mean_uA'])}，LM3={format_number(pattern['LM3_mean_uA'])}，LPM={format_number(pattern['LPM_mean_uA'])}。"
        )

    reference_rows = []
    for number in range(1, 5):
        bvm_name = f"BVM{number}"
        item = pre_compare[bvm_name]
        jm1 = item["signals"]["JM1_phase"]
        lm1 = item["signals"]["L_M1"]
        lsl = item["signals"]["L_SL"]
        sl = item["signals"]["SL_voltage"]
        reference_rows.append(
            f"| {bvm_name} | {'S1' if number == 1 else 'S0'} | {format_number(jm1['reference']['mean'])} | {format_number(jm1['target']['mean'])} | {format_number(jm1['mean_difference_display'])} | {format_number(lm1['mean_difference_display'])} | {format_number(lsl['mean_difference_display'])} | {format_number(sl['mean_difference_display'])} |"
        )

    coupling_rows = []
    for number in range(1, 5):
        item = dd[f"BVM{number}"]
        lsl = item["L_SL"]["windows"]["READ1"]["raw_1000_minus_0000"]
        sl = item["SL_voltage"]["windows"]["READ1"]["raw_1000_minus_0000"]
        jm1 = item["JM1_phase"]["windows"]["READ1"]["raw_1000_minus_0000"]
        jm2 = item["JM2_phase"]["windows"]["READ1"]["raw_1000_minus_0000"]
        coupling_rows.append(
            f"| BVM{number} | {format_number(jm1['max_abs'])} | {format_number(jm2['max_abs'])} | {format_number(lsl['max_abs'])} | {format_number(sl['max_abs'])} | {format_number(item['L_SL']['windows']['READ1']['centered_difference_in_differences']['max_abs'])} |"
        )

    victim_phase_rows = []
    for number in (2, 3, 4):
        target = four["1000"]["bvm"][f"BVM{number}"]["same_jj_phase_area"]
        control = four["0000"]["bvm"][f"BVM{number}"]["same_jj_phase_area"]
        target_js1 = target["JS1"]["READ1"]
        target_js2 = target["JS2"]["READ1"]
        control_js1 = control["JS1"]["READ1"]
        control_js2 = control["JS2"]["READ1"]
        victim_phase_rows.append(
            f"| BVM{number} | {format_number(target_js1['phase_delta_turns'])} | {format_number(target_js1['voltage_area_turns'])} | {format_number(target_js2['phase_delta_turns'])} | {format_number(target_js2['voltage_area_turns'])} | {format_number(control_js1['phase_delta_turns'])} | {format_number(control_js2['phase_delta_turns'])} |"
        )

    timing_rows = []
    for number in range(1, 5):
        item = timing["windows"]["READ1"]
        v = item["V(SL)"][f"BVM{number}"]
        i = item["I(L_SL)"][f"BVM{number}"]
        v_on = v["window_first_persistent_exceedance"].get("first_time_ps") if v.get("window_first_persistent_exceedance") else None
        i_on = i["window_first_persistent_exceedance"].get("first_time_ps") if i.get("window_first_persistent_exceedance") else None
        timing_rows.append(
            f"| BVM{number} | {format_number(v['abs_peak_time_ps'])} | {format_number(v_on)} | {v['window_first_status']} | {format_number(i['abs_peak_time_ps'])} | {format_number(i_on)} | {i['window_first_status']} |"
        )

    kcl_rows = []
    for context, item in metrics["rjm1_kcl"].items():
        for window_name in ("READ", "READ1"):
            if window_name not in item["residual"]:
                continue
            residual = item["residual"][window_name]
            kcl_rows.append(
                f"| {context} | {window_name} | {format_number(residual['max_abs_uA'])} | {format_number(residual['rms_uA'])} |"
            )

    corr_rows = []
    for signal_name in ("V(SL)", "I(L_SL)"):
        item = timing["pairwise_cross_correlation"][signal_name]
        for pair in ("BVM1_vs_BVM2", "BVM1_vs_BVM3", "BVM1_vs_BVM4"):
            fact = item[pair]
            corr_rows.append(
                f"| {signal_name} | {pair} | {format_number(fact.get('best_lag_ps'))} | {format_number(fact.get('zero_lag_correlation'))} | {format_number(fact.get('best_lag_correlation'))} |"
            )

    victim_nonzero = []
    for number in (2, 3, 4):
        read_max = float(dd[f"BVM{number}"]["L_SL"]["windows"]["READ1"]["raw_1000_minus_0000"]["max_abs"])
        pre_max = float(dd[f"BVM{number}"]["L_SL"]["windows"]["PRE_READ1"]["raw_1000_minus_0000"]["max_abs"])
        victim_nonzero.append((number, read_max, pre_max))
    strongest = max(victim_nonzero, key=lambda item: item[1])
    all_victims_changed = all(item[1] > item[2] for item in victim_nonzero)

    return f"""# SINGLE-vs-1000 INTERNAL READ COUPLING ANALYSIS

## 1. Question

本分析只回答一个问题：在同一 JM2-connected historical BVMSim shared-sensing
fixture 中，把 BVM1 从 `0` 改成 `1` 后，仍为 commanded-0 的 BVM2/BVM3/BVM4
是否出现 READ-associated 内部/输出波形变化；并用 single-BVM `S0/S1` 作物理
参考。

## 2. Data reused / no new simulation

只读取已有的 `S0-J-JM2C`、`S1-J-JM2C`、4-BVM `1000` 和同拓扑 `0000` raw、deck
及其历史模型。没有执行 JoSIM 仿真，只记录 solver 版本信息；没有生成新的 raw，
没有覆盖旧报告或旧 metrics。
所有 raw 使用共享 `bvmtools.raw` 精确列名读取；本任务涉及的 raw 无重复列。

## 3. What was held fixed

`1000` 与 `0000` 共享 4-BVM topology、JM2-connected BVM variant、sensing line、
original QB、six-stage historical JTL、10 ohm termination、stimulus protocol、
timestep 和 prior READ0 history；主要 state-conditioned 改变是 BVM1 的 WRITE1
bit。需要保留的因果边界是：现有 protocol 的 READ0 在 WRITE1 之前，且没有
WRITE1 之后的 state-matched READ=0/no-read control；因此 `1000-0000` 是
state-conditioned 对照，不是把 READ 驱动、自由演化和 shared-load feedback
完全分离的纯 READ 因果对照。single reference 只用于参考，不被当作严格同历史
A/B 因果对照。canonical
`circuits/bvm/bvm_cell.cir` 未使用；本报告的 source authority 是 historical
BVMSim JM2-connected variant。

## 4. Analysis limitations

- single 与 4-BVM raw 的完整时间列各有历史输出间隔差异，故没有全窗硬拼；PRE_READ
  用 single `[65,70)` 对齐 4-BVM `[105,110)`，READ overlay 用 single `[70,130)`
  对齐 4-BVM `[110,170)`。这些比较均只使用 exact shifted stored timestamps，
  不插值。
- `1000-0000` 是 exact full-grid difference；centered difference-in-differences
  仅作为 READ-associated 的描述性辅助，中心为各 trace 自己的 PRE_READ1 median。
- `P(...)` 原始单位是 rad；本报告的 phase turns 只来自 continuous unwrap(rad)/(2*pi)。
  phase displacement、voltage area 和局部波形都不等于 SFQ count。
- 当前 raw 没有 `I(R_S)`、`I(L_S3)` 的直接 probe；这两个并联支路的分流不能唯一
  拆分，属于 `OBSERVABILITY_GAP`。`R_JM1` 由实际 topology 的 `V(B_JM1)/8 ohm`
  重建；`I(L_S1)`、`I(L_S2)` 和 `I(R_SL)` 可分别由已确认的串联关系用已有
  `I(B_JS1)`、`I(B_JS2)` 和 `I(L_PSL)/I(L_SL)` 得到，不能再列为同等级缺口。
- 本任务 provenance 绑定了本次实际读取的 raw、deck、模型和分析/绘图工具哈希；
  父实验的执行元数据仍以父目录的历史记录为准，本任务不重建或改写它们。

## 5. OBSERVED — single S0/S1 internal reference

{chr(10).join(patterns)}

这些数值是 raw window means，不是先验模式。完整的 JM1/JM2/JS1/JS2 P/V/I、各
loop branch 和同 JJ phase-area 数值在 `analysis/metrics.json` 的 `single` 中。
READ 的 phase-area 也只作为同一 JJ 的一致性描述，不作为事件计数。

## 6. OBSERVED — 1000 PRE_READ1 vs single references

`BVM1` 对 single `S1`，`BVM2–4` 对 single `S0`；下表给出 PRE_READ matching
window 的 phase level（turns）、以及 target-reference 的均值差。电流单位 uA，
SL 电压单位 mV。

| position | single ref | JM1 ref mean (turns) | 1000 mean (turns) | JM1 mean diff (turns) | LM1 mean diff (uA) | LSL mean diff (uA) | SL voltage mean diff (mV) |
|---|---|---:|---:|---:|---:|---:|---:|
{chr(10).join(reference_rows)}

这一步只能支持“PRE_READ 内部水平与 isolated reference 的数值相似/不同”的
观察，不能写成 state completely identical。各 signal 的 mean difference、
relative/absolute difference、p2p 和 target retention 见 `pre_read_reference_comparison`。

## 7. OBSERVED — 1000 vs 0000 state-conditioned response

原始差分定义为 `1000 - 0000`。READ1 中 BVM2/BVM3/BVM4 的 `I(L_SL)` 差分相对其
PRE_READ1 差分分别为：{', '.join(f'BVM{n} {format_number(read, 4)} vs PRE {format_number(pre, 4)} uA max_abs' for n, read, pre in victim_nonzero)}。
最大 victim 差分为 BVM{strongest[0]} 的 {format_number(strongest[1])} uA。
“READ 中有变化”在本窗口的描述性判断为 `{all_victims_changed}`，但这里不设物理
阈值，需结合波形和 retention 一起审阅。

| position | Delta JM1 phase max_abs (turns) | Delta JM2 phase max_abs (turns) | Delta LSL max_abs (uA) | Delta SL max_abs (mV) | centered Delta LSL max_abs (uA) |
|---|---:|---:|---:|---:|---:|
{chr(10).join(coupling_rows)}

这些是 readout waveform changes。BVM2/BVM3/BVM4 的 JM1/JM2 storage markers 的
PRE_READ1→TAIL 数值保留在 `metrics.json` 的 `retention`；本轮不把 commanded-0
自动升级为 universally correct stored-0。

### Victim R-loop phase activity

`1000` 中 commanded-0 victim 的 JS1/JS2 在 READ1 出现了大幅 local phase-area
变化；下表同时保留同位置 `0000` control。它们是同一 JJ 的端点 phase delta 与
`V dt / Phi0` area 一致性描述，不是 SFQ event count，也不是完整 fluxoid retention。

| position | 1000 JS1 phase delta (turns) | 1000 JS1 Vdt (turns) | 1000 JS2 phase delta (turns) | 1000 JS2 Vdt (turns) | 0000 JS1 phase delta (turns) | 0000 JS2 phase delta (turns) |
|---|---:|---:|---:|---:|---:|---:|
{chr(10).join(victim_phase_rows)}

## 8. OBSERVED — RJM1 current reconstruction + LM1 KCL

variant topology 明确为 `B_JM1: 2->7`、`R_JM1: 2->7`、`L_M1: 7->0`，因此固定
使用：`I(L_M1) - I(B_JM1) - V(B_JM1)/8 ohm = 0`。没有翻转符号来追求好结果。

| context | window | KCL residual max_abs (uA) | KCL residual RMS (uA) |
|---|---|---:|---:|
{chr(10).join(kcl_rows)}

完整的重建电流与每个窗口 residual 在 `metrics.json` 的 `rjm1_kcl`。这是对
LM1 变化中 Josephson branch 与 8 ohm shunt 分配的约束；不是隐藏 branch 的直接
观测。

## 9. OBSERVED — timing / propagation

对 `1000-0000` delta，abs-peak time 不依赖 threshold。固定 1 uA/1 uV 只用于
描述性 activity localization；下面的“首个持续阈值样本”不是响应 onset。若
PRE_READ1 已经越过阈值，则标记为 `PRE_EXISTING_ACTIVITY_LEFT_CENSORED`，不能用作
传播延迟。READ1 结果如下，时间为 raw absolute ps。

| position | Delta V(SL) abs peak (ps) | Delta V(SL) window-first threshold (ps) | V threshold status | Delta I(LSL) abs peak (ps) | Delta I(LSL) window-first threshold (ps) | I threshold status |
|---|---:|---:|---|---:|---:|---|
{chr(10).join(timing_rows)}

`BVM1` 与 BVM2–4 的 pairwise correlation（正 lag 表示右侧/下游位置较晚）如下：

| signal | pair | best lag (ps) | zero-lag r | best-lag r |
|---|---|---:|---:|---:|
{chr(10).join(corr_rows)}

若多个位置接近同步或 lag 方向不稳定，应优先讨论 common READ drive、global
boundary perturbation 和 shared-load feedback；这些 timing/correlation 结果
不能单独证明单向 traveling disturbance 或唯一传播路径。完整的 JS1/JS2、LM3、
LPM timing 也在 `metrics.json`。

## 10. INFERENCE

在当前历史 fixture 和当前观测窗口内，`1000-0000` 若干 commanded-0 BVM 的
READ-associated `LSL/SL/internal` delta 明显高于其 PRE_READ1 delta，且其 JM1/JM2
retention marker 没有被同样地解释为 storage command 改变，则证据与如下解释相容：

`BVM1 stored-state / READ dynamics -> BVM1 LSL branch -> shared sensing-line
boundary -> other BVM boundary conditions -> their R-loop/internal redistribution`。

这应称为 shared-sensing-network readout cross-coupling / back-action / cross-loading
的 bounded inference，而不是“BVM1 电流直接流进 BVM2”。single-vs-1000 只提供
reference context；`1000-0000` 只能提供 state-conditioned association/localization，
不能单独分离 READ 驱动、自由演化与 shared-load feedback，也不能确定唯一 causal
path。

## 11. UNKNOWN

- `R_S || L_S3` 两支电流没有直接 probe，当前不能唯一决定 resistive 与 inductive
  partition；状态：`OBSERVABILITY_GAP`。
- 未证明 canonical BVM、单 BVM 与 4-BVM 完全可互换、QB 无关、论文机制身份、纯
  电阻/纯电感作用、单向传播或任何普适器件结论。
- 未将任何 phase turn 解释为 SFQ count；未做新事件实验、timestep convergence、
  margin、sweep 或参数优化。

## 12. Minimal next option

`PROPOSED_NOT_AUTHORIZED`：若用户审阅后仍需拆分 R-loop branch，只做 probe-only
rerun，增加 `I(R_S|XBVM1..4)`、`I(L_S3|XBVM1..4)`；本轮没有运行该建议。

## 13. Human gate

`AWAITING_USER_REVIEW`

- `user_reviewed: false`
- `next_step_authorized: false`
- `automatic_next_experiment: false`

本轮到此停止。
"""


def main() -> int:
    sys.path.insert(0, str(REPO / "scripts"))
    from bvmtools.provenance import git_snapshot, solver_provenance
    from bvmtools.raw import read_csv
    from bvmtools.compare import exact_time_grid_identity

    import argparse

    parser = argparse.ArgumentParser(description="Read-only single-vs-1000 internal READ coupling analysis")
    parser.add_argument("--regenerate", action="store_true", help="允许重建本任务已生成的 task-local outputs")
    args = parser.parse_args()

    initial_git = git_snapshot(REPO)
    own_prefix = rel(EXP) + "/"
    unrelated_status = [
        line for line in str(initial_git["status_porcelain"]).splitlines()
        if own_prefix not in line
    ]
    if unrelated_status:
        raise RuntimeError(f"analysis requires no unrelated dirty paths: {unrelated_status}")
    # A previous failed attempt may have left only partial plots.  Those are
    # task-local generated artifacts and may be regenerated; a completed
    # metrics file is the immutable completion marker and blocks overwrite.
    if (EXP / "analysis/metrics.json").exists() and (EXP / "analysis/SINGLE_VS_1000_INTERNAL_READ_COUPLING_REPORT.md").exists() and not args.regenerate:
        raise RuntimeError(f"refusing to overwrite completed task-local output: {EXP}")

    single = {name: read_csv(path) for name, path in SINGLE_RUNS.items()}
    four = {name: read_csv(path) for name, path in FOUR_RUNS.items()}
    require_labels(single["S0"], all_bvm_labels(1), "single S0")
    require_labels(single["S1"], all_bvm_labels(1), "single S1")
    for state, trace in four.items():
        for number in range(1, 5):
            require_labels(trace, all_bvm_labels(number), f"4-BVM {state} BVM{number}")
    if not exact_time_grid_identity(single["S0"].time, single["S1"].time):
        raise RuntimeError("single S0/S1 time grids are not exact identical")
    if not exact_time_grid_identity(four["1000"].time, four["0000"].time):
        raise RuntimeError("1000/0000 time grids are not exact identical")

    raw_paths = [*SINGLE_RUNS.values(), *FOUR_RUNS.values()]
    raw_hashes_before = {rel(path): sha256(path) for path in raw_paths}

    single_summary = {
        state: {
            "path": rel(SINGLE_RUNS[state]),
            "sha256": sha256(SINGLE_RUNS[state]),
            "grid": grid_fact(single[state]),
            **bvm_internal_summary(single[state], 1, {name: ps_window("single", name) for name in SINGLE_WINDOWS_PS}),
            "retention": retention(single[state], 1, ps_window("single", "PRE_READ"), ps_window("single", "TAIL")),
            "rjm1_kcl": rjm1_kcl(single[state], 1, {name: ps_window("single", name) for name in ("PRE_READ", "READ", "EARLY_RESPONSE", "TAIL")}),
        }
        for state in ("S0", "S1")
    }

    four_summary: dict[str, object] = {}
    for state in ("1000", "0000"):
        four_summary[state] = {
            "path": rel(FOUR_RUNS[state]),
            "sha256": sha256(FOUR_RUNS[state]),
            "grid": grid_fact(four[state]),
            "bvm": {
                f"BVM{number}": {
                    **bvm_internal_summary(four[state], number, {name: ps_window("four", name) for name in FOUR_WINDOWS_PS}),
                    "retention": retention(four[state], number, ps_window("four", "PRE_READ1"), ps_window("four", "TAIL")),
                    "rjm1_kcl": rjm1_kcl(four[state], number, {name: ps_window("four", name) for name in ("PRE_READ1", "READ1", "EARLY_RESPONSE", "TAIL")}),
                }
                for number in range(1, 5)
            },
        }

    # Single versus 1000 reference comparisons.  PRE_READ uses matched 5 ps
    # windows; READ overlay uses a matched 60 ps local time window.
    pre_compare: dict[str, object] = {}
    overlay_compare: dict[str, object] = {}
    reference_state = {1: "S1", 2: "S0", 3: "S0", 4: "S0"}
    comparison_signal_map = [
        ("JM1_phase", lambda n: phase_label("JM1", n), True),
        ("JM2_phase", lambda n: phase_label("JM2", n), True),
        ("JS1_phase", lambda n: phase_label("JS1", n), True),
        ("JS2_phase", lambda n: phase_label("JS2", n), True),
        ("L_M1", lambda n: branch_label("L_M1", n), False),
        ("L_M2", lambda n: branch_label("L_M2", n), False),
        ("L_M3", lambda n: branch_label("L_M3", n), False),
        ("L_PM", lambda n: branch_label("L_PM", n), False),
        ("L_SL", lambda n: branch_label("L_SL", n), False),
        ("SL_voltage", lambda n: f"V(SL{n})", False),
    ]
    for number in range(1, 5):
        ref_state = reference_state[number]
        pre_compare[f"BVM{number}"] = {
            "reference_state": ref_state,
            "reference_run": f"single_{ref_state}",
            "window_definition": {
                "reference_ps": [65.0, 70.0],
                "target_ps": [105.0, 110.0],
                "exact_shifted_grid": exact_shifted_grid(single[ref_state], ps_window("single", "PRE_READ"), four["1000"], ps_window("four", "PRE_READ1")),
            },
            "signals": {},
            "retention_target": four_summary["1000"]["bvm"][f"BVM{number}"]["retention"],  # type: ignore[index]
        }
        overlay_compare[f"BVM{number}"] = {"reference_state": ref_state, "signals": {}}
        for name, label_fn, is_phase in comparison_signal_map:
            label_ref = label_fn(1)
            label_target = label_fn(number)
            pre_compare[f"BVM{number}"]["signals"][name] = comparison_stats(  # type: ignore[index]
                single[ref_state], ps_window("single", "PRE_READ"), four["1000"], ps_window("four", "PRE_READ1"), label_ref, label_target, phase=is_phase
            )
            overlay_compare[f"BVM{number}"]["signals"][name] = comparison_stats(  # type: ignore[index]
                single[ref_state], ps_window("single", "READ_OVERLAY"), four["1000"], ps_window("four", "READ_OVERLAY"), label_ref, label_target, phase=is_phase,
                normalize_phase_to_local_start=is_phase,
            )

    # Exact-grid state-conditioned difference and centered difference-in-
    # differences for all requested internal/sensing observables.
    dd_signal_map: list[tuple[str, str, bool]] = []
    for name in ("JM1", "JM2", "JS1", "JS2"):
        dd_signal_map.append((f"{name}_phase", name, True))
        dd_signal_map.append((f"{name}_voltage", name, False))
        dd_signal_map.append((f"{name}_current", name, False))
    for branch in ALL_BRANCHES:
        dd_signal_map.append((branch, branch, False))
    dd_signal_map.append(("SL_voltage", "SL", False))
    dd: dict[str, object] = {}
    dd_windows = {
        "PRE_READ1": ps_window("four", "PRE_READ1"),
        "READ1": ps_window("four", "READ1"),
        "EARLY_RESPONSE": ps_window("four", "EARLY_RESPONSE"),
    }
    for number in range(1, 5):
        item: dict[str, object] = {}
        for name, base, is_phase in dd_signal_map:
            if base in JJ_NAMES:
                label = phase_label(base, number) if is_phase else voltage_label(base, number) if "voltage" in name else current_label(base, number)
            elif base == "SL":
                label = f"V(SL{number})"
            else:
                label = branch_label(base, number)
            item[name] = delta_fact(four["1000"], four["0000"], label, dd_windows)
        dd[f"BVM{number}"] = item

    # KCL is retained separately for all requested contexts.
    kcl_summary: dict[str, object] = {}
    for state in ("S0", "S1"):
        kcl_summary[f"single_{state}"] = single_summary[state]["rjm1_kcl"]
    for state in ("1000", "0000"):
        for number in range(1, 5):
            kcl_summary[f"{state}_BVM{number}"] = four_summary[state]["bvm"][f"BVM{number}"]["rjm1_kcl"]  # type: ignore[index]

    timing = timing_analysis(four["1000"], four["0000"], ps_window("four", "READ1"), ps_window("four", "EARLY_RESPONSE"))

    topology_text = VARIANT.read_text(encoding="utf-8")
    topology_checks = {
        "jm1_shunt": "R_JM1   2       7       8" in topology_text,
        "jm1_junction": "B_JM1   2       7" in topology_text,
        "lm1": "L_M1    7       0" in topology_text,
        "rs_and_ls3_parallel": "R_S     6       10" in topology_text and "L_S3    6       10" in topology_text,
        "strict_series_ls1_js1_topology": "L_S1    4       5" in topology_text and "B_JS1   5       6" in topology_text,
        "strict_series_ls2_js2_topology": "L_S2    8       9" in topology_text and "B_JS2   9       10" in topology_text,
        "lpsl_rsl_lsl_series_topology": all(token in topology_text for token in ("L_PSL   10      11", "R_SL    11      12", "L_SL    12      SL")),
    }
    if not all(topology_checks.values()):
        raise RuntimeError(f"topology checks failed: {topology_checks}")

    observability = {
        "directly_observed": [
            "JM1/JM2/JS1/JS2 P/V/I",
            "I(L_M1), I(L_M2), I(L_M3), I(L_PM), I(L_PSL), I(L_SL)",
            "V(SL1..SL4)",
        ],
        "reconstructed": ["I(R_JM1)=V(B_JM1)/8ohm"],
        "observability_gap": {
            "status": "OBSERVABILITY_GAP",
            "unresolved_parallel_partition": ["I(R_S)", "I(L_S3)"],
            "cannot_unique_partition": "R_S || L_S3 current partition",
            "derivable_from_confirmed_series_topology": [
                "I(L_S1)=I(B_JS1)",
                "I(L_S2)=I(B_JS2)",
                "I(R_SL)=I(L_PSL)=I(L_SL)",
            ],
            "reconstructed_elsewhere": ["I(R_JM1)=V(B_JM1)/8ohm"],
            "proposed_not_authorized": ["I(R_S|XBVM1..4)", "I(L_S3|XBVM1..4)"],
        },
        "topology_checks": topology_checks,
    }

    # Create the task-local output directory only after all read-only data and
    # topology checks have passed.
    EXP.mkdir(parents=True, exist_ok=True)
    (EXP / "analysis").mkdir(exist_ok=True)
    (EXP / "plots/data").mkdir(parents=True, exist_ok=True)

    records: list[dict[str, object]] = []
    plot_bound = ps_window("four", "READ_OVERLAY")
    # A-F: standalone views.  The plotter itself handles phase rad/(2*pi).
    plot_standalone(single["S0"], SINGLE_RUNS["S0"], 1, "S0", "SINGLE S0 INTERNAL READ — JM2-connected", "SINGLE_REFERENCE_S0_INTERNAL_READ", "single", records)
    plot_standalone(single["S1"], SINGLE_RUNS["S1"], 1, "S1", "SINGLE S1 INTERNAL READ — JM2-connected", "SINGLE_REFERENCE_S1_INTERNAL_READ", "single", records)
    for number in range(1, 5):
        plot_standalone(four["1000"], FOUR_RUNS["1000"], number, "1000", f"4-BVM 1000 BVM{number} INTERNAL READ", f"1000_BVM{number}_INTERNAL_READ", "four", records)

    # G-J: reference overlays.
    for number in range(1, 5):
        ref_state = reference_state[number]
        labels, _ = build_overlay_csv(
            single[ref_state], ps_window("single", "READ_OVERLAY"), four["1000"], ps_window("four", "READ_OVERLAY"), number,
            f"SINGLE_{ref_state}", f"1000_BVM{number}", EXP / "plots/data" / f"SINGLE_{ref_state}_VS_1000_BVM{number}.csv",
        )
        records.append(run_plot(EXP / "plots/data" / f"SINGLE_{ref_state}_VS_1000_BVM{number}.csv", EXP / "plots" / f"SINGLE_{'S1' if number == 1 else 'S0'}_VS_1000_BVM{number}.html", f"SINGLE {ref_state} vs 1000 BVM{number} — READ aligned", labels))

    # K-N: raw 1000-0000 internal delta for each position.
    for number in range(1, 5):
        data_path = EXP / "plots/data" / f"1000_MINUS_0000_BVM{number}.csv"
        labels, _ = build_delta_csv(four["1000"], four["0000"], number, data_path, bounds=(105.0e-12, 170.0e-12))
        records.append(run_plot(data_path, EXP / "plots" / f"1000_MINUS_0000_BVM{number}.html", f"1000 minus 0000 — BVM{number} internal READ delta", labels))

    # O-P: sensing position and timing views.
    sensing_path = EXP / "plots/data/1000_MINUS_0000_SENSING_POSITION_OVERLAY.csv"
    labels, _ = build_sensing_csv(four["1000"], four["0000"], sensing_path, (105.0e-12, 170.0e-12))
    records.append(run_plot(sensing_path, EXP / "plots/1000_MINUS_0000_SENSING_POSITION_OVERLAY.html", "1000 minus 0000 — sensing position overlay", labels))
    timing_path = EXP / "plots/data/1000_MINUS_0000_TIMING_PROPAGATION.csv"
    labels, _ = build_timing_csv(four["1000"], four["0000"], timing_path, (110.0e-12, 170.0e-12))
    records.append(run_plot(timing_path, EXP / "plots/1000_MINUS_0000_TIMING_PROPAGATION.html", "1000 minus 0000 — timing / propagation diagnostics", labels))

    # Q-R: core branch reconstruction views, restricted to 1000 READ1.
    rjm_path = EXP / "plots/data/RJM1_CURRENT_RECONSTRUCTION.csv"
    labels, _ = build_reconstruction_csv(four["1000"], rjm_path, (105.0e-12, 170.0e-12), residual=False)
    records.append(run_plot(rjm_path, EXP / "plots/RJM1_CURRENT_RECONSTRUCTION.html", "1000 — reconstructed R_JM1 current", labels))
    kcl_path = EXP / "plots/data/LM1_KCL_RESIDUAL.csv"
    labels, _ = build_reconstruction_csv(four["1000"], kcl_path, (105.0e-12, 170.0e-12), residual=True)
    records.append(run_plot(kcl_path, EXP / "plots/LM1_KCL_RESIDUAL.html", "1000 — LM1 KCL residual", labels))

    raw_hashes_after = {rel(path): sha256(path) for path in raw_paths}
    if raw_hashes_before != raw_hashes_after:
        raise RuntimeError("source raw hash changed during analysis/visualization")

    metrics = {
        "schema": "bvmsim-single-vs-1000-internal-read-coupling-metrics-v1",
        "analysis_version": "SINGLE_VS_1000_INTERNAL_READ_COUPLING_ANALYSIS_V1",
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "source_class": "HISTORICAL_BVMSIM_JM2_CONNECTED_VARIANT",
        "authority_boundary": "historical task-local analysis; canonical BVM not used",
        "no_new_simulation": True,
        "causal_boundary": {
            "read0_precedes_write1": True,
            "post_write_state_matched_read0_or_no_read_control": False,
            "interpretation": "1000_minus_0000 is state-conditioned association/localization; it does not uniquely isolate READ drive, free evolution, and shared-load feedback",
        },
        "git_before_analysis": initial_git,
        "solver_recorded_not_invoked": solver_provenance(SOLVER, cwd=REPO),
        "raw_hashes_before": raw_hashes_before,
        "raw_hashes_after": raw_hashes_after,
        "raw_unchanged": raw_hashes_before == raw_hashes_after,
        "time_grids": {
            "single_S0_vs_S1_exact": True,
            "four_1000_vs_0000_exact": True,
            "single_full_vs_four_full_exact": False,
            "single_vs_four_pre_read_shifted": exact_shifted_grid(single["S0"], ps_window("single", "PRE_READ"), four["1000"], ps_window("four", "PRE_READ1")),
            "single_vs_four_read_overlay_shifted": exact_shifted_grid(single["S0"], ps_window("single", "READ_OVERLAY"), four["1000"], ps_window("four", "READ_OVERLAY")),
            "comparison_policy": "exact stored samples only; no interpolation",
        },
        "source_files": source_snapshot([VARIANT, HISTORICAL_BVM, HISTORICAL_QB, HISTORICAL_JTL, SHARED_JJMIT, CANONICAL_BVM, PLOTTER, *raw_paths, *[FOUR_ROOT / f"runs/{state}/deck.cir" for state in ("1000", "0000")], *[SINGLE_ROOT / f"runs/{state}-J-JM2C/deck.cir" for state in ("S0", "S1")]]),
        "windows_ps": {
            "single": {name: list(bounds) for name, bounds in SINGLE_WINDOWS_PS.items()},
            "four_bvm": {name: list(bounds) for name, bounds in FOUR_WINDOWS_PS.items()},
            "pre_read_match": {"single": [65.0, 70.0], "four_bvm": [105.0, 110.0]},
            "read_overlay_match": {"single": [70.0, 130.0], "four_bvm": [110.0, 170.0]},
        },
        "single": single_summary,
        "four": four_summary,
        "pre_read_reference_comparison": pre_compare,
        "single_vs_1000_read_overlay": overlay_compare,
        "difference_in_differences": dd,
        "rjm1_kcl": kcl_summary,
        "timing": timing,
        "observability": observability,
        "visualization": {
            "plot_count": len(records),
            "standalone_count": 6,
            "comparison_count": 12,
            "renderer": rel(PLOTTER),
            "renderer_sha256": sha256(PLOTTER),
            "layout": "sep_comb",
            "color": "dark",
            "phase_jump": "2pi",
            "plot_manifest": rel(EXP / "analysis/plot_manifest.json"),
        },
        "human_gate": {
            "state": "AWAITING_USER_REVIEW",
            "user_reviewed": False,
            "next_step_authorized": False,
            "automatic_next_experiment": False,
        },
    }
    json_write(EXP / "analysis/metrics.json", metrics)
    json_write(EXP / "analysis/plot_manifest.json", plot_manifest(records, raw_hashes_before, raw_hashes_after))
    json_write(EXP / "analysis/provenance.json", {
        "schema": "bvmsim-single-vs-1000-internal-read-coupling-provenance-v1",
        "created_at": metrics["created_at"],
        "head_before_analysis": initial_git["head"],
        "starting_worktree": initial_git,
        "source_class": "HISTORICAL_BVMSIM_JM2_CONNECTED_VARIANT",
        "source_files": metrics["source_files"],
        "solver": metrics["solver_recorded_not_invoked"],
        "raw_unchanged": metrics["raw_unchanged"],
        "no_new_simulation": True,
        "canonical_bvm_not_used": True,
        "analysis_script": {"path": rel(Path(__file__)), "sha256": sha256(Path(__file__))},
        "plot_renderer": {"path": rel(PLOTTER), "sha256": sha256(PLOTTER)},
        "sol_xhigh_review": {
            "path": rel(EXP / "analysis/SOL_XHIGH_REVIEW.md"),
            "sha256": sha256(EXP / "analysis/SOL_XHIGH_REVIEW.md"),
            "status": "NEED_REVISION_CORRECTED_TASK_LOCAL_OUTPUTS",
        },
        "input_experiment_reports_read_only": [rel(SINGLE_ROOT / "analysis/REPORT.md"), rel(FOUR_ROOT / "analysis/REPORT.md")],
    })
    (EXP / "analysis/SINGLE_VS_1000_INTERNAL_READ_COUPLING_REPORT.md").write_text(generate_report(metrics), encoding="utf-8")
    (EXP / "analysis/human-gate.yaml").write_text(
        "state: AWAITING_USER_REVIEW\nuser_reviewed: false\nnext_step_authorized: false\nautomatic_next_experiment: false\nnext_action: STOP\n",
        encoding="utf-8",
    )
    (EXP / "PREFLIGHT.md").write_text(
        f"""# Read-only preflight — SINGLE-vs-1000 INTERNAL READ COUPLING ANALYSIS\n\n- HEAD before analysis: `{initial_git['head']}`\n- Starting worktree: no unrelated dirty paths; only this task-local scaffold was present\n- JoSIM: only version/hash provenance was recorded; no simulation was run\n- Canonical BVM: not used\n- Raw policy: existing raw CSVs immutable; hashes checked before/after\n- Time-grid policy: exact stored samples only; no interpolation\n- Created at: `{metrics['created_at']}`\n\nSource raw/deck/model hashes and the observed grid gaps are in `analysis/provenance.json` and `analysis/metrics.json`.\n""",
        encoding="utf-8",
    )
    (EXP / "experiment.yaml").write_text(
        """task_id: SINGLE_VS_1000_INTERNAL_READ_COUPLING_ANALYSIS_V1\nexperiment_id: bvmsim-single-vs-1000-internal-read-coupling-v1-20260904\nstudy_phase: EXPLORATION\nmode: READ_ONLY_ANALYSIS\nnew_simulation: false\ncanonical_bvm_used: false\ninputs:\n  single_reference: test/exploration/bvmsim-jm2-connected-single-ab-v1-20260903/\n  four_bvm_target: test/exploration/bvmsim-4bvm-jm2-connected-state-position-ab-v1-20260903/\n  target_states: [1000, 0000]\ncomparison:\n  primary: 1000_minus_0000\n  reference_mapping: BVM1->S1, BVM2->S0, BVM3->S0, BVM4->S0\n  interpolation: forbidden\n  phase_display: continuous_unwrap(rad)/(2*pi)\n  phase_is_sfq_count: false\nwindows_ps:\n  single_pre_read_match: [65, 70]\n  four_pre_read1: [105, 110]\n  single_read_overlay: [70, 130]\n  four_read_overlay: [110, 170]\n  four_early_response: [121, 140]\nobservability:\n  reconstruct: I_RJM1_equals_V_BJM1_div_8ohm\n  gap: R_S_parallel_L_S3_partition\n  status: OBSERVABILITY_GAP\nprohibited:\n  - JoSIM rerun\n  - circuit or parameter change\n  - timestep or load change\n  - sweep or optimization\n  - automatic probe-only rerun\nhuman_gate:\n  state: AWAITING_USER_REVIEW\n  user_reviewed: false\n  next_step_authorized: false\n  automatic_next_experiment: false\n""",
        encoding="utf-8",
    )
    (EXP / "analysis/TEST_COMMANDS.md").write_text(
        """# Commands and exit status\n\n- `python3 analysis/analyze.py`: PASS (read-only raw analysis plus task-local derived CSV/HTML/report generation).\n- JoSIM command: not run by authorization boundary.\n- Plot renderer: `scripts/josim-plot2.py -t sep_comb -c dark -j 2pi`: all generated plots returned exit code 0.\n- Raw SHA-256 before/after: identical; see `analysis/provenance.json`.\n\nThe analysis script uses shared `bvmtools.raw`, `phase`, `metrics`, `compare`, `kcl`, `onset`, and `waveform`; no local raw parser or SFQ event counter was added.\n""",
        encoding="utf-8",
    )
    print(json.dumps({"status": "PASS", "experiment": rel(EXP), "plot_count": len(records), "raw_unchanged": True}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
