#!/usr/bin/env python3
"""sfq_metrics_v2 -- M4 phase-unit foundation for JoSIM CSV metrics.

Units (M4 basis, per josim-evidence-audit/phase-evidence-contract):
    JoSIM phase-mode CSV columns ``P(<name>)`` are RAW PHASE in radians.
    Always preserve ``phase_delta_rad`` and derive
    ``phase_delta_turns = phase_delta_rad / (2*pi)``.

M4 boundary (AC4): full-trace endpoint deltas are only the unit layer.
They do NOT replace the M5 stable-window / zero-input controls, do NOT
replace the M6 same-junction voltage-area cross-check, and do NOT form a
physical Gate. Metric tolerances are not frozen until M9 (METRIC_SPEC_V2).

Naming (AC3): per-sample threshold statistics are reported only as
``over_threshold_sample_count`` and ``activity_intervals``. No
``fast_events``, ``pulse_count`` or ``sfq_count`` event semantics.

M5 extension (windowed, TASK M5-LITE-PILOT-001): deterministic pre/
activity/post windows in seconds, each half-open ``[start_s, end_s)``;
explicit per-column phase direction (exactly ``+1`` or ``-1``, never
inferred); matched zero-input control correction
``corrected_delta_rad = direction * (signal_delta_rad - control_delta_rad)``
with turns derived only AFTER the subtraction; contiguous activity
clustering with a strict ``> threshold_rad`` (equality inactive, gaps never
bridged). Windowed output keeps distinct ``signal``, ``zero_input_control``
and ``control_corrected`` namespaces. M5 clusters and over-threshold
samples are activity, never events/pulses/SFQs/fluxoids.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from typing import Any

UNITS = {
    "phase": "rad",
    "turns": "phase_delta_rad / (2*pi)",
    "time": "s",
}

DISCLAIMER = (
    "M4 unit foundation only: full-trace endpoint deltas do NOT replace "
    "the M5 stable-window/zero-input controls or the M6 same-junction "
    "voltage-area cross-check, and do NOT constitute a physical Gate. "
    "Metric tolerances are not frozen until M9 (METRIC_SPEC_V2)."
)

M5_DISCLAIMER = (
    "M5 windowed semantics: windows/direction/threshold are explicit plan "
    "inputs; activity clusters and over-threshold samples are activity, "
    "never events/pulses/SFQs/fluxoids. The M5 threshold is descriptive "
    "and unfrozen (metric tolerance freeze is M9). No physical Gate."
)

M6_DISCLAIMER = (
    "M6 same-JJ cross-check: phase and voltage area are measured on the "
    "same junction, endpoints, orientation, window and run; "
    "area_turns = orientation * trapezoid(V, actual_time) / Phi0, with no "
    "resampling or interpolation. Residuals are raw measurement-pipeline "
    "values; no physical tolerance is frozen until M9."
)

DEFAULT_THRESHOLD_RAD = 0.3

# Flux quantum in webers (same constant used in circuits/standard/DCSFQ.cir).
PHI0 = 2.067833848e-15


def rad_to_turns(phase_delta_rad: float) -> float:
    """Explicit rad -> turns conversion: delta_rad / (2*pi)."""
    return phase_delta_rad / (2.0 * math.pi)


def trapezoid_integral(values: list[float], times: list[float]) -> float:
    """Trapezoidal integral of ``values`` over the ACTUAL time axis.

    Uses the CSV's real time column; never assumes a fixed sampling interval
    and never resamples or interpolates. Requires at least two samples and
    ``len(values) == len(times)``.
    """
    if len(values) != len(times):
        raise ValueError("values and times must have equal length")
    if len(values) < 2:
        raise ValueError("trapezoid integration requires at least two samples")
    return sum(
        0.5 * (values[i] + values[i + 1]) * (times[i + 1] - times[i])
        for i in range(len(values) - 1)
    )


def file_sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _activity_stats(
    phase: list[float], times: list[float], threshold_rad: float
) -> dict[str, Any]:
    """Sample-level activity only; never an event/pulse count (AC3)."""
    diffs = [abs(phase[i + 1] - phase[i]) for i in range(len(phase) - 1)]
    over = [i for i, d in enumerate(diffs) if d > threshold_rad]
    intervals: list[dict[str, float]] = []
    if over:
        start = prev = over[0]
        for i in over[1:]:
            if i != prev + 1:
                intervals.append(
                    {
                        "start_index": start,
                        "end_index": prev,
                        "start_time_s": times[start],
                        "end_time_s": times[prev + 1],
                    }
                )
                start = i
            prev = i
        intervals.append(
            {
                "start_index": start,
                "end_index": prev,
                "start_time_s": times[start],
                "end_time_s": times[prev + 1],
            }
        )
    return {
        "over_threshold_sample_count": len(over),
        "activity_intervals": intervals,
    }


def analyze(csv_path: str, threshold_rad: float = DEFAULT_THRESHOLD_RAD) -> dict[str, Any]:
    """Extract M4 unit-layer metrics from a JoSIM phase-mode CSV."""
    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        return {
            "units": UNITS,
            "disclaimer": DISCLAIMER,
            "csv": csv_path,
            "error": "empty csv",
        }
    n = len(rows)
    t0 = float(rows[0]["time"])
    t1 = float(rows[-1]["time"])
    dt = (t1 - t0) / (n - 1) if n > 1 else 0.0
    times = [float(r["time"]) for r in rows]

    phases: dict[str, Any] = {}
    for col in rows[0].keys():
        if not col.startswith("P("):
            continue
        p = [float(r[col]) for r in rows]
        delta_rad = p[-1] - p[0]
        phases[col] = {
            "phase_delta_rad": round(delta_rad, 12),
            "phase_delta_turns": round(rad_to_turns(delta_rad), 12),
            "max_excursion_rad": round(max(abs(v - p[0]) for v in p), 12),
            "total_variation_rad": round(
                sum(abs(p[i + 1] - p[i]) for i in range(n - 1)), 12
            ),
            **_activity_stats(p, times, threshold_rad),
        }

    return {
        "metric_version": "v2",
        "units": UNITS,
        "disclaimer": DISCLAIMER,
        "csv": csv_path,
        "sha256": file_sha256(csv_path),
        "n_samples": n,
        "t_start_s": t0,
        "t_end_s": t1,
        "dt_s": dt,
        "threshold_rad": threshold_rad,
        "phases": phases,
    }


def validate_plan(plan: dict) -> dict:
    """Normalize and validate an M5 measurement plan (raises ValueError).

    Window units are seconds; every window is half-open ``[start_s, end_s)``.
    Requires ``pre_end <= activity_start`` and ``activity_end <= post_start``.
    Each declared direction must be exactly ``+1`` or ``-1`` (never inferred).
    """
    if not isinstance(plan, dict):
        raise ValueError("measurement plan must be a JSON object")
    if plan.get("schema_version") != 1:
        raise ValueError("measurement plan schema_version must be 1")
    windows = plan.get("windows_s")
    if not isinstance(windows, dict):
        raise ValueError("measurement plan must contain windows_s")
    out_windows: dict[str, tuple[float, float]] = {}
    for name in ("pre", "activity", "post"):
        w = windows.get(name)
        if not isinstance(w, list) or len(w) != 2:
            raise ValueError(f"windows_s.{name} must be a [start, end] pair")
        start, end = float(w[0]), float(w[1])
        if not (math.isfinite(start) and math.isfinite(end)):
            raise ValueError(f"windows_s.{name} bounds must be finite")
        if start > end:
            raise ValueError(f"windows_s.{name} must satisfy start <= end")
        out_windows[name] = (start, end)
    if out_windows["pre"][1] > out_windows["activity"][0]:
        raise ValueError("require pre_end <= activity_start")
    if out_windows["activity"][1] > out_windows["post"][0]:
        raise ValueError("require activity_end <= post_start")
    directions = plan.get("phase_directions")
    if not isinstance(directions, dict) or not directions:
        raise ValueError("measurement plan must declare phase_directions")
    out_dirs: dict[str, int] = {}
    for col, d in directions.items():
        if not isinstance(col, str) or not col.startswith("P("):
            raise ValueError(f"phase_directions key must be a P(...) column: {col!r}")
        if isinstance(d, bool) or not isinstance(d, (int, float)) or d not in (1.0, -1.0):
            raise ValueError(f"direction for {col} must be exactly +1 or -1")
        out_dirs[col] = int(d)
    th = plan.get("activity_threshold_rad")
    if th is None or isinstance(th, bool) or not isinstance(th, (int, float)):
        raise ValueError("measurement plan must declare numeric activity_threshold_rad")
    th = float(th)
    if not math.isfinite(th):
        raise ValueError("activity_threshold_rad must be finite")
    return {
        "schema_version": 1,
        "windows_s": out_windows,
        "phase_directions": out_dirs,
        "activity_threshold_rad": th,
    }


def _read_csv(
    csv_path: str,
    include_voltage: bool = False,
) -> tuple[list[str], list[float], dict[str, list[float]], dict[str, list[float]]]:
    """Parse a JoSIM phase-mode CSV with strict time/phase/voltage validation.

    Collects ``P(...)`` columns always and ``V(...)`` columns when
    ``include_voltage`` is set. Raises ValueError on empty input,
    non-numeric or nonfinite time/phase/voltage values, or
    non-strictly-monotonic time.
    """
    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise ValueError(f"{csv_path}: empty csv")
    header = list(rows[0].keys())
    phase_cols = [c for c in header if c.startswith("P(")]
    volt_cols = [c for c in header if c.startswith("V(")] if include_voltage else []
    times: list[float] = []
    phases: dict[str, list[float]] = {c: [] for c in phase_cols}
    voltages: dict[str, list[float]] = {c: [] for c in volt_cols}
    for i, r in enumerate(rows):
        try:
            t = float(r["time"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"{csv_path}: non-numeric time at row {i}") from exc
        if not math.isfinite(t):
            raise ValueError(f"{csv_path}: nonfinite time at row {i}")
        if i > 0 and t <= times[-1]:
            raise ValueError(f"{csv_path}: time must be strictly monotonic (row {i})")
        times.append(t)
        for c in phase_cols:
            try:
                v = float(r[c])
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(f"{csv_path}: non-numeric {c} at row {i}") from exc
            if not math.isfinite(v):
                raise ValueError(f"{csv_path}: nonfinite {c} at row {i}")
            phases[c].append(v)
        for c in volt_cols:
            try:
                v = float(r[c])
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(f"{csv_path}: non-numeric {c} at row {i}") from exc
            if not math.isfinite(v):
                raise ValueError(f"{csv_path}: nonfinite {c} at row {i}")
            voltages[c].append(v)
    return header, times, phases, voltages


def _read_phase_csv(
    csv_path: str,
) -> tuple[list[str], list[float], dict[str, list[float]]]:
    """Phase-only wrapper of :func:`_read_csv` (M5 windowed path)."""
    header, times, phases, _ = _read_csv(csv_path)
    return header, times, phases


def _window_indices(times: list[float], start_s: float, end_s: float) -> list[int]:
    """Sample indices whose time satisfies ``start_s <= t < end_s``."""
    return [i for i, t in enumerate(times) if start_s <= t < end_s]


def _window_stats(
    phase: list[float],
    times: list[float],
    indices: list[int],
    requested: tuple[float, float],
) -> dict[str, Any]:
    """Per-window statistics in raw radians; the mean is unrounded."""
    vals = [phase[i] for i in indices]
    if len(vals) < 2:
        raise ValueError(f"window {requested}: fewer than two finite samples")
    lo, hi = min(vals), max(vals)
    return {
        "requested_start_s": requested[0],
        "requested_end_s": requested[1],
        "selected_first_time_s": times[indices[0]],
        "selected_last_time_s": times[indices[-1]],
        "sample_count": len(vals),
        "mean_rad": sum(vals) / len(vals),
        "min_rad": lo,
        "max_rad": hi,
        "p2p_rad": hi - lo,
    }


def _activity_clusters(
    phase: list[float],
    times: list[float],
    activity_window: tuple[float, float],
    threshold_rad: float,
) -> tuple[list[dict[str, Any]], int]:
    """Contiguous activity clusters inside the activity window (never events).

    Returns ``(clusters, over_threshold_sample_count)``. An increment from
    sample i to i+1 qualifies only when both endpoints lie inside the
    half-open activity window and ``abs(delta_rad) > threshold_rad`` (strict;
    equality is inactive). Only consecutive qualifying increments form a
    cluster; gaps are never bridged. Clustering is kept separate from the
    activity-window statistics so clusters retain no event semantics.
    """
    start_s, end_s = activity_window
    clusters: list[dict[str, Any]] = []
    over = 0
    run: list[int] = []
    for i in range(len(phase) - 1):
        inside = times[i] >= start_s and times[i + 1] < end_s
        if inside and abs(phase[i + 1] - phase[i]) > threshold_rad:
            over += 1
            if not run:
                run = [i, i + 1]
            else:
                run[1] = i + 1
        elif run:
            clusters.append(
                {
                    "start_index": run[0],
                    "end_index": run[1],
                    "start_time_s": times[run[0]],
                    "end_time_s": times[run[1]],
                    "n_increments": run[1] - run[0],
                }
            )
            run = []
    if run:
        clusters.append(
            {
                "start_index": run[0],
                "end_index": run[1],
                "start_time_s": times[run[0]],
                "end_time_s": times[run[1]],
                "n_increments": run[1] - run[0],
            }
        )
    return clusters, over


def windowed_analyze(
    signal_csv: str, plan: dict, control_csv: str | None = None
) -> dict[str, Any]:
    """M5 windowed phase metrics with matched zero-input control.

    Semantics (TASK M5-LITE-PILOT-001): half-open windows in seconds; explicit
    per-column direction; ``corrected_delta_rad = direction *
    (signal_delta_rad - control_delta_rad)`` derived BEFORE ``/(2*pi)``;
    contiguous activity clustering with a strict threshold. Each of the pre,
    activity and post windows carries the full unrounded statistics block
    (requested bounds, selected first/last time, sample count, mean, min,
    max, peak-to-peak), and every window must contain at least two finite
    samples or the analysis fails. Clustering is reported separately
    (``activity_clusters`` + ``over_threshold_sample_count``) and never
    carries event semantics. Output keeps distinct ``signal``,
    ``zero_input_control`` and ``control_corrected`` namespaces. No
    interpolation/resampling: the control must have identical parsed headers
    and identical time arrays.
    """
    plan = validate_plan(plan)
    s_header, s_times, s_phases = _read_phase_csv(signal_csv)
    missing = [c for c in plan["phase_directions"] if c not in s_phases]
    if missing:
        raise ValueError(f"signal csv missing phase columns: {missing}")

    c_times = c_phases = None
    if control_csv is not None:
        c_header, c_times, c_phases = _read_phase_csv(control_csv)
        if c_header != s_header:
            raise ValueError(
                "control csv headers must be identical to signal headers (same order)"
            )
        if len(c_times) != len(s_times) or any(a != b for a, b in zip(c_times, s_times)):
            raise ValueError(
                "control csv time array must be identical to signal time array"
            )
        c_missing = [c for c in plan["phase_directions"] if c not in c_phases]
        if c_missing:
            raise ValueError(f"control csv missing phase columns: {c_missing}")

    windows = plan["windows_s"]
    directions = plan["phase_directions"]
    threshold = plan["activity_threshold_rad"]

    def namespace(
        times: list[float], phases: dict[str, list[float]]
    ) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for col, direction in directions.items():
            phase = phases[col]
            pre_stats = _window_stats(
                phase, times, _window_indices(times, *windows["pre"]), windows["pre"]
            )
            act_stats = _window_stats(
                phase,
                times,
                _window_indices(times, *windows["activity"]),
                windows["activity"],
            )
            post_stats = _window_stats(
                phase, times, _window_indices(times, *windows["post"]), windows["post"]
            )
            clusters, over = _activity_clusters(
                phase, times, windows["activity"], threshold
            )
            out[col] = {
                "direction": direction,
                "pre": pre_stats,
                "activity": act_stats,
                "post": post_stats,
                "activity_clusters": clusters,
                "over_threshold_sample_count": over,
                "delta_rad": post_stats["mean_rad"] - pre_stats["mean_rad"],
            }
        return out

    signal_ns = namespace(s_times, s_phases)
    control_ns = namespace(c_times, c_phases) if control_csv is not None else None

    corrected: dict[str, Any] = {}
    for col, direction in directions.items():
        signal_delta = signal_ns[col]["delta_rad"]
        control_delta = control_ns[col]["delta_rad"] if control_ns is not None else 0.0
        corrected_rad = direction * (signal_delta - control_delta)
        corrected[col] = {
            "direction": direction,
            "signal_delta_rad": signal_delta,
            "control_delta_rad": control_delta,
            "corrected_delta_rad": corrected_rad,
            "corrected_delta_turns": rad_to_turns(corrected_rad),
        }

    result: dict[str, Any] = {
        "metric_version": "v2",
        "mode": "windowed",
        "units": UNITS,
        "disclaimer": DISCLAIMER + " " + M5_DISCLAIMER,
        "threshold_status": "descriptive_unfrozen",
        "windows_s": {k: [v[0], v[1]] for k, v in windows.items()},
        "activity_threshold_rad": threshold,
        "control_applied": control_csv is not None,
        "signal": signal_ns,
        "control_corrected": corrected,
        "provenance": {
            "signal_csv": signal_csv,
            "signal_sha256": file_sha256(signal_csv),
            "control_csv": control_csv,
            "control_sha256": file_sha256(control_csv) if control_csv is not None else None,
            "alignment_note": (
                "CSV alignment cannot prove the netlist control relationship."
            ),
        },
    }
    if control_ns is not None:
        result["zero_input_control"] = control_ns
    return result


def validate_voltage_plan(plan: dict) -> dict:
    """Normalize and validate an M6 plan (raises ValueError).

    Extends the M5 plan with a ``voltage_area`` mapping section: each key is
    a phase column ``P(...)`` whose value declares ``voltage_column``
    (``V(...)``), ``orientation`` (exactly +1/-1) and ``endpoint_window``
    (a name present in ``windows_s``). The same windows are then used for
    both the phase endpoint difference and the voltage trapezoid.
    """
    if not isinstance(plan, dict):
        raise ValueError("measurement plan must be a JSON object")
    if plan.get("schema_version") != 1:
        raise ValueError("measurement plan schema_version must be 1")
    windows = plan.get("windows_s")
    if not isinstance(windows, dict):
        raise ValueError("measurement plan must contain windows_s")
    out_windows: dict[str, tuple[float, float]] = {}
    for name, w in windows.items():
        if not isinstance(w, list) or len(w) != 2:
            raise ValueError(f"windows_s.{name} must be a [start, end] pair")
        start, end = float(w[0]), float(w[1])
        if not (math.isfinite(start) and math.isfinite(end)):
            raise ValueError(f"windows_s.{name} bounds must be finite")
        if start > end:
            raise ValueError(f"windows_s.{name} must satisfy start <= end")
        out_windows[name] = (start, end)
    for first, second in (("pre", "activity"), ("activity", "post")):
        if first in out_windows and second in out_windows:
            if out_windows[first][1] > out_windows[second][0]:
                raise ValueError(f"require {first}_end <= {second}_start")
    va = plan.get("voltage_area")
    if not isinstance(va, dict) or not va:
        raise ValueError("plan must declare voltage_area mappings")
    out_va: dict[str, dict[str, Any]] = {}
    for phase_col, mapping in va.items():
        if not isinstance(phase_col, str) or not phase_col.startswith("P("):
            raise ValueError(f"voltage_area key must be a P(...) column: {phase_col!r}")
        if not isinstance(mapping, dict):
            raise ValueError(f"voltage_area[{phase_col}] must be an object")
        vcol = mapping.get("voltage_column")
        if not isinstance(vcol, str) or not vcol.startswith("V("):
            raise ValueError(
                f"voltage_area[{phase_col}].voltage_column must be a V(...) column"
            )
        orient = mapping.get("orientation")
        if isinstance(orient, bool) or not isinstance(orient, (int, float)):
            raise ValueError(f"voltage_area[{phase_col}].orientation must be +1 or -1")
        if orient not in (1.0, -1.0):
            raise ValueError(f"voltage_area[{phase_col}].orientation must be +1 or -1")
        win = mapping.get("endpoint_window")
        if not isinstance(win, str) or win not in out_windows:
            raise ValueError(
                f"voltage_area[{phase_col}].endpoint_window must name a windows_s entry"
            )
        out_va[phase_col] = {
            "voltage_column": vcol,
            "orientation": int(orient),
            "endpoint_window": win,
        }
    return {"schema_version": 1, "windows_s": out_windows, "voltage_area": out_va}


def voltage_area_analyze(
    signal_csv: str, plan: dict, control_csv: str | None = None
) -> dict[str, Any]:
    """M6 same-JJ phase vs voltage-area cross-check.

    For every declared mapping the phase endpoint difference and the
    voltage trapezoid are measured on the SAME junction, SAME run, SAME
    orientation and SAME window, using the CSV's actual time column:

    ``phase_delta_turns = (P_last - P_first) / (2*pi)``
    ``area_turns = orientation * trapezoid(V, time) / PHI0``
    ``residual_turns = phase_delta_turns - area_turns``

    Raw rad/V/s values are preserved; nothing is rounded early or made
    absolute. No resampling or interpolation is ever performed. When a
    matched control CSV is supplied, per-run results for signal and control
    are reported in full first and the 0/300-style difference is listed
    separately under ``control_corrected``.
    """
    plan = validate_voltage_plan(plan)
    s_header, s_times, s_phases, s_voltages = _read_csv(signal_csv, include_voltage=True)

    def run_namespace(
        times: list[float],
        phases: dict[str, list[float]],
        voltages: dict[str, list[float]],
    ) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for phase_col, mapping in plan["voltage_area"].items():
            vcol = mapping["voltage_column"]
            if phase_col not in phases:
                raise ValueError(f"csv missing phase column {phase_col}")
            if vcol not in voltages:
                raise ValueError(f"csv missing voltage column {vcol}")
            win = plan["windows_s"][mapping["endpoint_window"]]
            indices = _window_indices(times, *win)
            stats = _window_stats(phases[phase_col], times, indices, win)
            first, last = indices[0], indices[-1]
            phase_delta_rad = phases[phase_col][last] - phases[phase_col][first]
            area = mapping["orientation"] * trapezoid_integral(
                [voltages[vcol][i] for i in indices], [times[i] for i in indices]
            )
            out[phase_col] = {
                "phase_column": phase_col,
                "voltage_column": vcol,
                "orientation": mapping["orientation"],
                "endpoint_window": mapping["endpoint_window"],
                "window": {
                    "requested_start_s": win[0],
                    "requested_end_s": win[1],
                    "selected_first_time_s": stats["selected_first_time_s"],
                    "selected_last_time_s": stats["selected_last_time_s"],
                    "sample_count": stats["sample_count"],
                },
                "phase_first_rad": phases[phase_col][first],
                "phase_last_rad": phases[phase_col][last],
                "phase_delta_rad": phase_delta_rad,
                "phase_delta_turns": rad_to_turns(phase_delta_rad),
                "area_vs": area,
                "area_turns": area / PHI0,
                "residual_turns": rad_to_turns(phase_delta_rad) - area / PHI0,
            }
        return out

    signal_ns = run_namespace(s_times, s_phases, s_voltages)
    control_ns = None
    if control_csv is not None:
        c_header, c_times, c_phases, c_voltages = _read_csv(control_csv, include_voltage=True)
        if c_header != s_header:
            raise ValueError(
                "control csv headers must be identical to signal headers (same order)"
            )
        if len(c_times) != len(s_times) or any(a != b for a, b in zip(c_times, s_times)):
            raise ValueError(
                "control csv time array must be identical to signal time array"
            )
        control_ns = run_namespace(c_times, c_phases, c_voltages)

    result: dict[str, Any] = {
        "metric_version": "v2",
        "mode": "voltage_area_crosscheck",
        "units": {**UNITS, "flux_quantum": "Wb", "area": "V*s"},
        "disclaimer": DISCLAIMER + " " + M5_DISCLAIMER + " " + M6_DISCLAIMER,
        "runs": {"signal": signal_ns},
        "provenance": {
            "signal_csv": signal_csv,
            "signal_sha256": file_sha256(signal_csv),
            "control_csv": control_csv,
            "control_sha256": file_sha256(control_csv) if control_csv is not None else None,
            "alignment_note": (
                "CSV alignment cannot prove the netlist control relationship."
            ),
        },
    }
    if control_ns is not None:
        result["runs"]["zero_input_control"] = control_ns
        corrected: dict[str, Any] = {}
        for phase_col in plan["voltage_area"]:
            sig = signal_ns[phase_col]
            ctl = control_ns[phase_col]
            corrected[phase_col] = {
                "phase_column": phase_col,
                "voltage_column": sig["voltage_column"],
                "orientation": sig["orientation"],
                "signal_phase_delta_turns": sig["phase_delta_turns"],
                "control_phase_delta_turns": ctl["phase_delta_turns"],
                "corrected_phase_delta_turns": sig["phase_delta_turns"] - ctl["phase_delta_turns"],
                "signal_area_turns": sig["area_turns"],
                "control_area_turns": ctl["area_turns"],
                "corrected_area_turns": sig["area_turns"] - ctl["area_turns"],
                "corrected_residual_turns": (
                    (sig["phase_delta_turns"] - ctl["phase_delta_turns"])
                    - (sig["area_turns"] - ctl["area_turns"])
                ),
            }
        result["control_corrected"] = corrected
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "M4 unit-layer metrics for JoSIM phase-mode CSVs. "
            "Columns P(<name>) are raw phase in RADIANS; "
            "phase_delta_turns = phase_delta_rad / (2*pi). "
            "This is NOT a physical Gate (see M5/M6/M9). "
            "With --measurement-plan, run M5 windowed mode: pre/activity/post "
            "half-open windows, explicit direction, matched zero-input "
            "control, contiguous activity clustering (never events)."
        )
    )
    parser.add_argument("csv", help="JoSIM CSV output path")
    parser.add_argument(
        "--threshold-rad",
        type=float,
        default=DEFAULT_THRESHOLD_RAD,
        help=(
            "sample-to-sample |dphase| threshold in radians for activity "
            "classification (default 0.3); counts samples/intervals, never events"
        ),
    )
    parser.add_argument(
        "--json", metavar="OUT", help="write JSON to OUT instead of stdout"
    )
    parser.add_argument(
        "--measurement-plan",
        metavar="PLAN.json",
        help=(
            "M5 windowed mode: JSON measurement plan with windows_s, "
            "phase_directions (+1/-1) and activity_threshold_rad"
        ),
    )
    parser.add_argument(
        "--control-csv",
        metavar="CONTROL.csv",
        help=(
            "M5 windowed / M6 cross-check mode: matched zero-input control "
            "CSV (must have identical headers and identical time array)"
        ),
    )
    parser.add_argument(
        "--voltage-area",
        action="store_true",
        help=(
            "M6 same-JJ phase vs voltage-area cross-check mode: the plan's "
            "voltage_area mappings drive trapezoid(V, actual time)/Phi0 "
            "against (P_last - P_first)/(2*pi) on the same window"
        ),
    )
    args = parser.parse_args(argv)

    if args.measurement_plan is not None:
        try:
            with open(args.measurement_plan, encoding="utf-8") as f:
                plan = json.load(f)
            if args.voltage_area:
                result = voltage_area_analyze(
                    args.csv, plan, control_csv=args.control_csv
                )
            else:
                result = windowed_analyze(args.csv, plan, control_csv=args.control_csv)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            sys.stderr.write(f"error: {exc}\n")
            return 2
    else:
        result = analyze(args.csv, threshold_rad=args.threshold_rad)
    payload = json.dumps(result, indent=2)
    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            f.write(payload + "\n")
    else:
        sys.stdout.write(payload + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
