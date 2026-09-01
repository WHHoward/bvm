#!/usr/bin/env python3
"""Read-only mechanism audit for the existing BVM -> JSL -> QB matrix.

This script deliberately does not invoke JoSIM.  It reads the 48 matrix raw
CSVs, re-computes source/load-line diagnostics, and reuses the already frozen
strict BJL2 classifications as references rather than as a new event metric.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import subprocess
from pathlib import Path
from typing import Any, Iterable

import numpy as np


TARGET = Path(__file__).resolve().parents[1]
REPO = TARGET.parents[2]
MATRIX = REPO / "test/exploration/bvm-load-qb-matrix-v1-20260901"
RAW = MATRIX / "raw"
STRICT = REPO / "test/exploration/bvm-load-qb-strict-event-reclassification-v1-20260901"
ANALYSIS = TARGET / "analysis"

RECORDED_AT = "2026-09-01T15:33:35+08:00"
PARENT_HEAD = "b761ba948d0cf64affdc0b9fb623fab05197cf21"
PHI0 = 2.067833848e-15
TWO_PI = 2.0 * math.pi
MACHINE_EPS = np.finfo(float).eps

PRE_WINDOW = (80.0, 94.0)
ACTIVITY_WINDOW = (94.0, 130.0)
POST_WINDOW = (140.0, 170.0)
PRE_DIVERGENCE_END_PS = 105.0
COMMON_STOP_PS = 170.0
IDENTITY_RELATIVE_FLOOR = 1.0e-12
SUSTAINED_DIVERGENCE_SAMPLES = 2
CENTROID_AREA_FLOOR_AS = 1.0e-20
KCL_ABS_FLOOR_A = 1.0e-12
KCL_RELATIVE_FLOOR = 1.0e-6
Z_DENOM_ABS_FLOOR_A = 1.0e-18
Z_DENOM_RELATIVE_FLOOR = 1.0e-12
SCALAR_RESIDUAL_MAX = 0.25
SCALAR_CORRELATION_MIN = 0.90
SCALAR_PEAK_SHIFT_MAX_PS = 0.05
H1_EXTENSION_SHARE_MIN = 0.80
H2_OUTSIDE_SHARE_MIN = 0.20

WIDTHS = (9, 13)
LOADS = {
    "12x320": {"count": 12, "ic_uA": 320.0},
    "8x500": {"count": 8, "ic_uA": 500.0},
}
ROLES = (
    "logical1_read",
    "logical0_read",
    "logical1_no_read_control",
    "logical0_no_read_control",
)
FIXTURES = ("source", "replay", "physical")

SOURCE_SIGNALS = {
    "12x320": [
        "I(B_LD1)", "I(B_LD12)", "I(L_SL|XBVM1)", "V(SL1)",
        "V(N6|XBVM1)", "I(L_PSL|XBVM1)",
    ],
    "8x500": [
        "I(B_LD1)", "I(B_LD8)", "I(L_SL|XBVM1)", "V(SL1)",
        "V(N6|XBVM1)", "I(L_PSL|XBVM1)",
    ],
}

QB_SIGNALS = [
    "I(I_REPLAY)", "V(IN)", "I(LIN|XBQ)",
    "P(BJS|XBQ)", "V(BJS|XBQ)", "I(BJS|XBQ)",
    "P(BJL1|XBQ)", "V(BJL1|XBQ)", "I(BJL1|XBQ)",
    "I(RJ1|XBQ)", "I(L1|XBQ)",
    "I(RB|XBQ)", "I(L2|XBQ)",
    "P(BJL2|XBQ)", "V(BJL2|XBQ)", "I(BJL2|XBQ)",
    "I(RJ2|XBQ)", "I(L0|XBQ)", "V(OUT)", "I(R_LOAD)",
]

QB_FAMILIES = {
    "QB IN/Lin": ["I(I_REPLAY)", "V(IN)", "I(LIN|XBQ)"],
    "BJs": ["P(BJS|XBQ)", "V(BJS|XBQ)", "I(BJS|XBQ)"],
    "node2/BJL1": [
        "P(BJL1|XBQ)", "V(BJL1|XBQ)", "I(BJL1|XBQ)",
        "I(RJ1|XBQ)", "I(L1|XBQ)",
    ],
    "node3": ["I(RB|XBQ)", "I(L2|XBQ)"],
    "BJL2": [
        "P(BJL2|XBQ)", "V(BJL2|XBQ)", "I(BJL2|XBQ)",
        "I(RJ2|XBQ)", "I(L0|XBQ)",
    ],
    "OUT": ["V(OUT)", "I(R_LOAD)"],
}

SOURCE_FAMILY = {
    "source waveform": ["I(B_LD1)", "I(L_SL|XBVM1)", "V(SL1)"]
}

SOURCE_DIFF_WINDOWS = (
    ("94_105ps", 94.0, 105.0, True),
    ("105_106ps", 105.0, 106.0, True),
    ("106_109ps", 106.0, 109.0, True),
    ("109_110ps", 109.0, 110.0, True),
    ("110_130ps", 110.0, 130.0, False),
)


class Trace:
    def __init__(self, path: Path, header: list[str], time_s: np.ndarray, columns: dict[str, list[np.ndarray]]):
        self.path = path
        self.header = header
        self.time_s = time_s
        self.columns = columns

    def get(self, name: str, occurrence: int = 0) -> np.ndarray:
        values = self.columns.get(name)
        if values is None or occurrence >= len(values):
            raise KeyError(f"missing {name!r} occurrence {occurrence}: {self.path}")
        return values[occurrence]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(REPO).as_posix()


def load_trace(path: Path) -> Trace:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        try:
            raw_header = [str(item).strip().strip('"') for item in next(reader)]
        except StopIteration as exc:
            raise ValueError(f"empty CSV: {path}") from exc
        if not raw_header or raw_header[0] != "time":
            raise ValueError(f"first column is not time: {path}")
        columns: dict[str, list[list[float]]] = {}
        for name in raw_header[1:]:
            columns.setdefault(name, []).append([])
        times: list[float] = []
        previous = -math.inf
        for line_number, row in enumerate(reader, start=2):
            if not row:
                continue
            if len(row) != len(raw_header):
                raise ValueError(f"column count mismatch at line {line_number}: {path}")
            time_s = float(row[0])
            if not math.isfinite(time_s) or time_s <= previous:
                raise ValueError(f"invalid time at line {line_number}: {path}")
            times.append(time_s)
            previous = time_s
            occurrence: dict[str, int] = {}
            for name, raw_value in zip(raw_header[1:], row[1:]):
                value = float(raw_value)
                if not math.isfinite(value):
                    raise ValueError(f"non-finite {name} at line {line_number}: {path}")
                index = occurrence.get(name, 0)
                columns[name][index].append(value)
                occurrence[name] = index + 1
    if len(times) < 2:
        raise ValueError(f"fewer than two samples: {path}")
    arrays = {name: [np.asarray(values, dtype=float) for values in occurrences] for name, occurrences in columns.items()}
    return Trace(path, raw_header, np.asarray(times, dtype=float), arrays)


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def case_path(fixture: str, width: int, load: str, role: str) -> Path:
    return RAW / fixture / f"{width}ps" / load / role / "run-01.csv"


def execution_index() -> dict[tuple[str, int, str, str], dict[str, Any]]:
    result: dict[tuple[str, int, str, str], dict[str, Any]] = {}
    for fixture in FIXTURES:
        path = MATRIX / "logs" / f"execution-{fixture}.json"
        if not path.exists():
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        for item in payload.get("results", []):
            result[(fixture, int(item["width_ps"]), item["load"], item["role"])] = item
    return result


def sidecar_info(path: Path) -> dict[str, Any]:
    sidecar = path.with_suffix(path.suffix + ".sha256")
    if not sidecar.exists():
        return {"exists": False, "declared_sha256": None, "matches": False, "sha256": None}
    tokens = sidecar.read_text(encoding="utf-8").split()
    declared = tokens[0] if tokens else None
    return {
        "exists": True,
        "declared_sha256": declared,
        "matches": declared == sha256(path),
        "sha256": sha256(sidecar),
    }


def required_signals(fixture: str, load: str) -> list[str]:
    if fixture == "source":
        return SOURCE_SIGNALS[load]
    if fixture == "replay":
        return QB_SIGNALS
    return SOURCE_SIGNALS[load] + QB_SIGNALS[1:]


def window_mask(time_s: np.ndarray, window: tuple[float, float], *, inclusive_end: bool = False) -> np.ndarray:
    start, end = window
    left = time_s >= start * 1e-12
    right = time_s <= end * 1e-12 if inclusive_end else time_s < end * 1e-12
    return left & right


def trapz(time_s: np.ndarray, values: np.ndarray) -> float:
    if time_s.size < 2:
        return 0.0
    return float(np.trapezoid(values, time_s) if hasattr(np, "trapezoid") else np.trapz(values, time_s))


def first_argmax(values: np.ndarray) -> int:
    return int(np.flatnonzero(values == np.max(values))[0])


def first_argmin(values: np.ndarray) -> int:
    return int(np.flatnonzero(values == np.min(values))[0])


def weighted_centroid(time_ps: np.ndarray, time_s: np.ndarray, weights: np.ndarray) -> float | None:
    area = trapz(time_s, weights)
    if abs(area) <= CENTROID_AREA_FLOOR_AS:
        return None
    return float(trapz(time_s, time_ps * weights) / area)


def effective_duration(
    trace: Trace | None,
    signal: np.ndarray,
    time_s: np.ndarray,
    activity_mask: np.ndarray,
    pre_values: np.ndarray | None,
) -> dict[str, Any]:
    if not np.any(activity_mask):
        return {"duration_ps": None, "threshold": None, "baseline": None, "status": "INVALID"}
    local = signal[activity_mask]
    local_time = time_s[activity_mask]
    baseline = float(np.median(pre_values)) if pre_values is not None and pre_values.size else 0.0
    deviations = np.abs(local - baseline)
    threshold = max(1e-18, 0.05 * float(np.max(deviations)))
    selected = deviations >= threshold
    if not np.any(selected):
        return {"duration_ps": None, "threshold": threshold, "baseline": baseline, "status": "UNDEFINED"}
    selected_time = local_time[selected] * 1e12
    return {
        "duration_ps": float(selected_time[-1] - selected_time[0]),
        "first_time_ps": float(selected_time[0]),
        "last_time_ps": float(selected_time[-1]),
        "threshold": threshold,
        "baseline": baseline,
        "status": "VALID",
    }


def series_metrics(
    time_s: np.ndarray,
    values: np.ndarray,
    window: tuple[float, float],
    *,
    kind: str,
    pre_values: np.ndarray | None = None,
) -> dict[str, Any]:
    mask = window_mask(time_s, window)
    if np.count_nonzero(mask) < 2:
        return {"status": "INCONCLUSIVE", "sample_count": int(np.count_nonzero(mask))}
    local_time_s = time_s[mask]
    local_time_ps = local_time_s * 1e12
    local = values[mask]
    if kind == "phase":
        unwrapped = np.unwrap(values)
        local_phase = unwrapped[mask]
        return {
            "status": "VALID",
            "sample_count": int(local_phase.size),
            "first_rad": float(local_phase[0]),
            "last_rad": float(local_phase[-1]),
            "delta_rad": float(local_phase[-1] - local_phase[0]),
            "delta_turns": float((local_phase[-1] - local_phase[0]) / TWO_PI),
            "range_turns": float((np.max(local_phase) - np.min(local_phase)) / TWO_PI),
        }
    imax = first_argmax(local)
    imin = first_argmin(local)
    result: dict[str, Any] = {
        "status": "VALID",
        "sample_count": int(local.size),
        "first": float(local[0]),
        "last": float(local[-1]),
        "min": float(local[imin]),
        "max": float(local[imax]),
        "p2p": float(np.max(local) - np.min(local)),
        "mean": float(np.mean(local)),
        "rms": float(np.sqrt(np.mean(local * local))),
        "max_abs": float(np.max(np.abs(local))),
        "positive_peak": float(np.max(local)),
        "positive_peak_time_ps": float(local_time_ps[imax]),
        "minimum_time_ps": float(local_time_ps[imin]),
    }
    if kind == "current":
        positive = np.maximum(local, 0.0)
        negative = np.minimum(local, 0.0)
        result.update({
            "signed_integral_As": trapz(local_time_s, local),
            "positive_integral_As": trapz(local_time_s, positive),
            "negative_integral_As": trapz(local_time_s, negative),
            "signed_integral_uA_ps": trapz(local_time_s, local) * 1e18,
            "positive_integral_uA_ps": trapz(local_time_s, positive) * 1e18,
            "negative_integral_uA_ps": trapz(local_time_s, negative) * 1e18,
            "signed_centroid_ps": weighted_centroid(local_time_ps, local_time_s, local),
            "positive_centroid_ps": weighted_centroid(local_time_ps, local_time_s, positive),
            "negative_centroid_ps": weighted_centroid(local_time_ps, local_time_s, negative),
            "effective_duration": effective_duration(
                None, values, time_s, mask, pre_values
            ),
        })
    else:
        result["integral_unit_s"] = trapz(local_time_s, local)
    return result


def signal_kind(signal: str) -> str:
    if signal.startswith("P("):
        return "phase"
    if signal.startswith("I("):
        return "current"
    return "voltage"


def signal_unit(signal: str) -> str:
    return {"phase": "turns", "current": "A", "voltage": "V"}[signal_kind(signal)]


def aligned_values(trace: Trace, signal: str) -> tuple[np.ndarray, str]:
    values = trace.get(signal)
    if signal_kind(signal) != "phase":
        return values, signal_unit(signal)
    unwrapped = np.unwrap(values)
    pre = np.flatnonzero(window_mask(trace.time_s, (0.0, PRE_DIVERGENCE_END_PS), inclusive_end=True))
    reference = unwrapped[pre[0]] if pre.size else unwrapped[0]
    return (unwrapped - reference) / TWO_PI, "turns"


def grid_check(left: Trace, right: Trace) -> dict[str, Any]:
    if left.time_s.size != right.time_s.size:
        return {"status": "INVALID", "sample_count_left": int(left.time_s.size), "sample_count_right": int(right.time_s.size)}
    delta = np.abs(left.time_s - right.time_s)
    return {
        "status": "PASS" if bool(np.array_equal(left.time_s, right.time_s)) else "PASS_WITH_NUMERICAL_TIME_TOLERANCE" if float(np.max(delta)) <= 1e-24 else "FAIL",
        "exact": bool(np.array_equal(left.time_s, right.time_s)),
        "sample_count": int(left.time_s.size),
        "max_abs_time_difference_s": float(np.max(delta)),
    }


def paired_difference(
    left: Trace,
    left_signal: str,
    right: Trace,
    right_signal: str,
    window: tuple[float, float],
    *,
    inclusive_end: bool = False,
) -> dict[str, Any]:
    grid = grid_check(left, right)
    if grid["status"] == "FAIL" or left.time_s.size != right.time_s.size:
        return {"status": "INVALID", "grid": grid}
    left_values, unit = aligned_values(left, left_signal)
    right_values, right_unit = aligned_values(right, right_signal)
    if unit != right_unit:
        return {"status": "INVALID", "reason": "unit mismatch", "grid": grid}
    mask = window_mask(left.time_s, window, inclusive_end=inclusive_end)
    if np.count_nonzero(mask) < 2:
        return {"status": "INCONCLUSIVE", "grid": grid, "sample_count": int(np.count_nonzero(mask))}
    delta = right_values - left_values
    local_delta = delta[mask]
    local_time_s = left.time_s[mask]
    local_time_ps = local_time_s * 1e12
    imax = first_argmax(np.abs(local_delta))
    result: dict[str, Any] = {
        "status": "VALID",
        "grid": grid,
        "unit": unit,
        "sample_count": int(local_delta.size),
        "max_abs": float(np.max(np.abs(local_delta))),
        "rms": float(np.sqrt(np.mean(local_delta * local_delta))),
        "mean_abs": float(np.mean(np.abs(local_delta))),
        "first_delta": float(local_delta[0]),
        "last_delta": float(local_delta[-1]),
        "max_abs_time_ps": float(local_time_ps[imax]),
    }
    if signal_kind(left_signal) == "current":
        result.update({
            "signed_integral_As": trapz(local_time_s, local_delta),
            "positive_integral_As": trapz(local_time_s, np.maximum(local_delta, 0.0)),
            "negative_integral_As": trapz(local_time_s, np.minimum(local_delta, 0.0)),
            "absolute_integral_As": trapz(local_time_s, np.abs(local_delta)),
            "signed_integral_uA_ps": trapz(local_time_s, local_delta) * 1e18,
            "positive_integral_uA_ps": trapz(local_time_s, np.maximum(local_delta, 0.0)) * 1e18,
            "negative_integral_uA_ps": trapz(local_time_s, np.minimum(local_delta, 0.0)) * 1e18,
            "absolute_integral_uA_ps": trapz(local_time_s, np.abs(local_delta)) * 1e18,
        })
    return result


def numerical_identity(
    left: Trace,
    left_signal: str,
    right: Trace,
    right_signal: str,
    *,
    end_ps: float,
) -> dict[str, Any]:
    grid = grid_check(left, right)
    if grid["status"] == "FAIL" or left.time_s.size != right.time_s.size:
        return {"status": "FAIL", "grid": grid}
    a, unit = aligned_values(left, left_signal)
    b, right_unit = aligned_values(right, right_signal)
    if unit != right_unit:
        return {"status": "FAIL", "reason": "unit mismatch", "grid": grid}
    mask = left.time_s <= end_ps * 1e-12
    if np.count_nonzero(mask) < 2:
        return {"status": "INCONCLUSIVE", "grid": grid}
    scale = max(1.0, float(np.max(np.abs(a[mask]))), float(np.max(np.abs(b[mask]))))
    tolerance = max(IDENTITY_RELATIVE_FLOOR * scale, 100.0 * MACHINE_EPS * scale)
    delta = b[mask] - a[mask]
    maximum = float(np.max(np.abs(delta)))
    return {
        "status": "PASS" if maximum <= tolerance else "FAIL",
        "unit": unit,
        "sample_count": int(np.count_nonzero(mask)),
        "max_abs": maximum,
        "rms": float(np.sqrt(np.mean(delta * delta))),
        "tolerance": tolerance,
        "scale": scale,
        "exact": bool(np.array_equal(a[mask], b[mask])),
        "grid": grid,
    }


def divergence_threshold(left: np.ndarray, right: np.ndarray, baseline_mask: np.ndarray) -> tuple[float, float, float]:
    delta = np.abs(right - left)
    baseline = float(np.percentile(delta[baseline_mask], 99.9)) if np.any(baseline_mask) else 0.0
    scale = max(1.0, float(np.max(np.abs(left))), float(np.max(np.abs(right))))
    threshold = max(10.0 * baseline, IDENTITY_RELATIVE_FLOOR * scale, 100.0 * MACHINE_EPS * scale)
    return baseline, scale, threshold


def first_divergence(
    left: Trace,
    left_signal: str,
    right: Trace,
    right_signal: str,
) -> dict[str, Any]:
    grid = grid_check(left, right)
    if grid["status"] == "FAIL" or left.time_s.size != right.time_s.size:
        return {"status": "INVALID", "grid": grid}
    a, unit = aligned_values(left, left_signal)
    b, right_unit = aligned_values(right, right_signal)
    if unit != right_unit:
        return {"status": "INVALID", "reason": "unit mismatch", "grid": grid}
    baseline_mask = left.time_s <= PRE_DIVERGENCE_END_PS * 1e-12
    post_mask = left.time_s > PRE_DIVERGENCE_END_PS * 1e-12
    baseline, scale, threshold = divergence_threshold(a, b, baseline_mask)
    above = (np.abs(b - a) > threshold) & post_mask
    starts: list[int] = []
    run = 0
    for index, flag in enumerate(above):
        run = run + 1 if flag else 0
        if run >= SUSTAINED_DIVERGENCE_SAMPLES:
            starts.append(index - SUSTAINED_DIVERGENCE_SAMPLES + 1)
            break
    result = {
        "status": "VALID",
        "unit": unit,
        "grid": grid,
        "baseline_p99_9": baseline,
        "scale": scale,
        "threshold": threshold,
        "sustained_samples": SUSTAINED_DIVERGENCE_SAMPLES,
    }
    if not starts:
        result["first_divergence"] = None
        return result
    start = starts[0]
    result["first_divergence"] = {
        "sample_index": int(start),
        "time_ps": float(left.time_s[start] * 1e12),
        "delta_at_start": float((b - a)[start]),
        "run_end_time_ps": float(left.time_s[start + SUSTAINED_DIVERGENCE_SAMPLES - 1] * 1e12),
    }
    return result


def current_metric_from_arrays(time_s: np.ndarray, values: np.ndarray, window: tuple[float, float]) -> dict[str, Any]:
    pre_mask = window_mask(time_s, PRE_WINDOW)
    return series_metrics(time_s, values, window, kind="current", pre_values=values[pre_mask])


def metric_row(
    rows: list[dict[str, Any]],
    *,
    comparison: str,
    case_a: str,
    case_b: str,
    load: str,
    signal: str,
    window: str,
    metrics_a: dict[str, Any],
    metrics_b: dict[str, Any],
) -> None:
    kind = signal_kind(signal)
    quantities = (
        ["positive_peak", "positive_peak_time_ps", "minimum_time_ps", "min", "max", "p2p", "mean", "rms", "max_abs", "integral_unit_s"]
        if kind == "voltage" else
        ["delta_rad", "delta_turns", "range_turns"]
        if kind == "phase" else
        ["positive_peak", "positive_peak_time_ps", "minimum_time_ps", "min", "max", "p2p", "mean", "rms", "max_abs", "signed_integral_As", "positive_integral_As", "negative_integral_As", "signed_integral_uA_ps", "positive_integral_uA_ps", "negative_integral_uA_ps", "signed_centroid_ps", "positive_centroid_ps", "negative_centroid_ps", "effective_duration_ps"]
    )
    for quantity in quantities:
        value_a = metrics_a.get(quantity)
        value_b = metrics_b.get(quantity)
        if quantity == "effective_duration_ps":
            value_a = (metrics_a.get("effective_duration") or {}).get("duration_ps")
            value_b = (metrics_b.get("effective_duration") or {}).get("duration_ps")
        if isinstance(value_a, (int, float)) and isinstance(value_b, (int, float)):
            delta = value_b - value_a
            ratio = value_b / value_a if value_a != 0 else None
        else:
            delta = None
            ratio = None
        rows.append({
            "comparison": comparison,
            "case_a": case_a,
            "case_b": case_b,
            "load": load,
            "signal": signal,
            "unit": signal_unit(signal),
            "quantity": quantity,
            "window": window,
            "value_a": value_a if value_a is not None else "",
            "value_b": value_b if value_b is not None else "",
            "delta_b_minus_a": delta if delta is not None else "",
            "ratio_b_over_a": ratio if ratio is not None else "",
            "notes": "P phase is continuous unwrapped phase; current area is waveform diagnostic only" if kind == "phase" else "",
        })


def source_analysis(traces: dict[tuple[str, int, str, str], Trace]) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    results: dict[str, Any] = {}
    identity: dict[str, Any] = {}
    for load in LOADS:
        left_key = ("source", 9, load, "logical1_read")
        right_key = ("source", 13, load, "logical1_read")
        left = traces[left_key]
        right = traces[right_key]
        load_result: dict[str, Any] = {"case_a": "/".join(map(str, left_key)), "case_b": "/".join(map(str, right_key)), "signals": {}}
        for signal in SOURCE_SIGNALS[load]:
            if signal not in left.columns or signal not in right.columns:
                continue
            kind = signal_kind(signal)
            pre_a = left.get(signal)[window_mask(left.time_s, PRE_WINDOW)] if kind == "current" else None
            pre_b = right.get(signal)[window_mask(right.time_s, PRE_WINDOW)] if kind == "current" else None
            metrics_a = series_metrics(left.time_s, left.get(signal), ACTIVITY_WINDOW, kind=kind, pre_values=pre_a)
            metrics_b = series_metrics(right.time_s, right.get(signal), ACTIVITY_WINDOW, kind=kind, pre_values=pre_b)
            load_result["signals"][signal] = {"a": metrics_a, "b": metrics_b}
            metric_row(rows, comparison="A_vs_B_source", case_a=rel(left.path), case_b=rel(right.path), load=load, signal=signal, window="activity_94_130ps", metrics_a=metrics_a, metrics_b=metrics_b)
            identity[f"source/{load}/{signal}"] = numerical_identity(left, signal, right, signal, end_ps=PRE_DIVERGENCE_END_PS)
            if kind == "current":
                decomposition: dict[str, Any] = {}
                for label, start, end, inclusive in SOURCE_DIFF_WINDOWS:
                    diff = paired_difference(left, signal, right, signal, (start, end), inclusive_end=inclusive)
                    decomposition[label] = diff
                    for quantity in ("signed_integral_uA_ps", "positive_integral_uA_ps", "negative_integral_uA_ps", "absolute_integral_uA_ps", "max_abs", "max_abs_time_ps"):
                        rows.append({
                            "comparison": "A_vs_B_source_difference",
                            "case_a": rel(left.path),
                            "case_b": rel(right.path),
                            "load": load,
                            "signal": signal,
                            "unit": "uA*ps" if "integral" in quantity else "A" if quantity == "max_abs" else "ps",
                            "quantity": quantity,
                            "window": label,
                            "value_a": "",
                            "value_b": "",
                            "delta_b_minus_a": diff.get(quantity, ""),
                            "ratio_b_over_a": "",
                            "notes": "difference = 13ps - 9ps; source waveform diagnostic, not SFQ quantity",
                        })
                load_result["signals"][signal]["difference_decomposition"] = decomposition
        results[load] = load_result
    # Cross-load source diagnostics are separate from the 9 ps -> 13 ps
    # comparison above.  The terminal current has different raw names in the
    # two BVM decks, so expose it under one explicit canonical label while
    # retaining the original paths in the case fields.
    left = traces[("source", 13, "8x500", "logical1_read")]
    right = traces[("source", 13, "12x320", "logical1_read")]
    cross_load: dict[str, Any] = {
        "case_a": rel(left.path),
        "case_b": rel(right.path),
        "signals": {},
    }
    cross_load_signals = (
        ("I(B_LD1)", "I(B_LD1)", "I(B_LD1)"),
        ("I(B_LDterminal)", "I(B_LD8)", "I(B_LD12)"),
        ("I(L_SL|XBVM1)", "I(L_SL|XBVM1)", "I(L_SL|XBVM1)"),
        ("V(SL1)", "V(SL1)", "V(SL1)"),
        ("V(N6|XBVM1)", "V(N6|XBVM1)", "V(N6|XBVM1)"),
        ("I(L_PSL|XBVM1)", "I(L_PSL|XBVM1)", "I(L_PSL|XBVM1)"),
    )
    for canonical, left_signal, right_signal in cross_load_signals:
        pre_left = left.get(left_signal)[window_mask(left.time_s, PRE_WINDOW)] if signal_kind(canonical) == "current" else None
        pre_right = right.get(right_signal)[window_mask(right.time_s, PRE_WINDOW)] if signal_kind(canonical) == "current" else None
        metrics_left = series_metrics(left.time_s, left.get(left_signal), ACTIVITY_WINDOW, kind=signal_kind(canonical), pre_values=pre_left)
        metrics_right = series_metrics(right.time_s, right.get(right_signal), ACTIVITY_WINDOW, kind=signal_kind(canonical), pre_values=pre_right)
        cross_load["signals"][canonical] = {
            "a": metrics_left,
            "b": metrics_right,
            "difference": paired_difference(left, left_signal, right, right_signal, ACTIVITY_WINDOW),
            "raw_signal_a": left_signal,
            "raw_signal_b": right_signal,
        }
        metric_row(rows, comparison="D_vs_B_source_13ps_ideal_load", case_a=rel(left.path), case_b=rel(right.path), load="8x500_vs_12x320", signal=canonical, window="activity_94_130ps", metrics_a=metrics_left, metrics_b=metrics_right)
    results["cross_load_13ps_ideal"] = cross_load
    return rows, results, identity


def qb_metric_comparison(
    traces: dict[tuple[str, int, str, str], Trace],
    left_key: tuple[str, int, str, str],
    right_key: tuple[str, int, str, str],
    comparison: str,
    signals: Iterable[str],
    load: str,
) -> dict[str, Any]:
    left = traces[left_key]
    right = traces[right_key]
    result: dict[str, Any] = {"comparison": comparison, "case_a": rel(left.path), "case_b": rel(right.path), "signals": {}, "kcl": {}}
    for signal in signals:
        if signal not in left.columns or signal not in right.columns:
            continue
        kind = signal_kind(signal)
        pre_a = left.get(signal)[window_mask(left.time_s, PRE_WINDOW)] if kind == "current" else None
        pre_b = right.get(signal)[window_mask(right.time_s, PRE_WINDOW)] if kind == "current" else None
        a = series_metrics(left.time_s, left.get(signal), ACTIVITY_WINDOW, kind=kind, pre_values=pre_a)
        b = series_metrics(right.time_s, right.get(signal), ACTIVITY_WINDOW, kind=kind, pre_values=pre_b)
        result["signals"][signal] = {"a": a, "b": b, "difference": paired_difference(left, signal, right, signal, ACTIVITY_WINDOW)}
        metric_row([], comparison=comparison, case_a=rel(left.path), case_b=rel(right.path), load=load, signal=signal, window="activity_94_130ps", metrics_a=a, metrics_b=b)
    return result


def qb_kcl(trace: Trace) -> dict[str, Any]:
    currents = {signal: trace.get(signal) for signal in (
        "I(LIN|XBQ)", "I(BJS|XBQ)", "I(BJL1|XBQ)", "I(RJ1|XBQ)", "I(L1|XBQ)",
        "I(RB|XBQ)", "I(L2|XBQ)", "I(L0|XBQ)", "I(BJL2|XBQ)", "I(RJ2|XBQ)",
    )}
    equation_terms = {
        "node1": (
            currents["I(LIN|XBQ)"] - currents["I(BJS|XBQ)"],
            [currents["I(LIN|XBQ)"], currents["I(BJS|XBQ)"]],
        ),
        "node2": (
            currents["I(BJS|XBQ)"] - currents["I(BJL1|XBQ)"] - currents["I(RJ1|XBQ)"] - currents["I(L1|XBQ)"],
            [currents["I(BJS|XBQ)"], currents["I(BJL1|XBQ)"], currents["I(RJ1|XBQ)"], currents["I(L1|XBQ)"]],
        ),
        "node3": (
            currents["I(L1|XBQ)"] + currents["I(RB|XBQ)"] - currents["I(L2|XBQ)"],
            [currents["I(L1|XBQ)"], currents["I(RB|XBQ)"], currents["I(L2|XBQ)"]],
        ),
        "node4": (
            currents["I(L2|XBQ)"] - currents["I(L0|XBQ)"] - currents["I(BJL2|XBQ)"] - currents["I(RJ2|XBQ)"],
            [currents["I(L2|XBQ)"], currents["I(L0|XBQ)"], currents["I(BJL2|XBQ)"], currents["I(RJ2|XBQ)"]],
        ),
    }
    result: dict[str, Any] = {}
    all_pass = True
    for node, (residual, terms) in equation_terms.items():
        mask = window_mask(trace.time_s, ACTIVITY_WINDOW)
        scale = max(1e-30, float(np.max(np.sum(np.vstack([np.abs(term[mask]) for term in terms]), axis=0))))
        tolerance = max(KCL_ABS_FLOOR_A, KCL_RELATIVE_FLOOR * scale)
        metric = current_metric_from_arrays(trace.time_s, residual, ACTIVITY_WINDOW)
        metric.update({
            "scale_A": scale,
            "tolerance_A": tolerance,
            "bound_definition": "max(1e-12 A, 1e-6 * max_t sum(abs(all terms in this KCL equation)))",
            "closure_status": "PASS" if metric["max_abs"] <= tolerance else "FAIL",
        })
        result[node] = metric
        all_pass = all_pass and metric["closure_status"] == "PASS"
    result["overall_status"] = "PASS" if all_pass else "FAIL"
    result["directions"] = {
        "node1": "I(LIN IN->1) - I(BJs 1->2)",
        "node2": "I(BJs 1->2) - I(BJL1 2->0) - I(RJ1 2->0) - I(L1 2->3)",
        "node3": "I(L1 2->3) + I(RB IB->3) - I(L2 3->4)",
        "node4": "I(L2 3->4) - I(L0 4->OUT) - I(BJL2 4->0) - I(RJ2 4->0)",
    }
    return result


def qb_comparison_rows(results: list[dict[str, Any]], comparison: dict[str, Any], comparison_name: str, left_path: str, right_path: str, load: str) -> None:
    for signal, detail in comparison["signals"].items():
        metric_row(results, comparison=comparison_name, case_a=left_path, case_b=right_path, load=load, signal=signal, window="activity_94_130ps", metrics_a=detail["a"], metrics_b=detail["b"])
        diff = detail["difference"]
        for quantity in ("max_abs", "rms", "max_abs_time_ps"):
            results.append({
                "comparison": comparison_name + "_difference",
                "case_a": left_path,
                "case_b": right_path,
                "load": load,
                "signal": signal,
                "unit": diff.get("unit", signal_unit(signal)) if quantity != "max_abs_time_ps" else "ps",
                "quantity": quantity,
                "window": "activity_94_130ps",
                "value_a": "",
                "value_b": "",
                "delta_b_minus_a": diff.get(quantity, ""),
                "ratio_b_over_a": "",
                "notes": "continuous phase comparison uses unwrapped phase; no event count",
            })


def pre_state_guard(traces: dict[tuple[str, int, str, str], Trace]) -> dict[str, Any]:
    physical = traces[("physical", 13, "12x320", "logical1_read")]
    replay = traces[("replay", 13, "12x320", "logical1_read")]
    common = ["V(IN)", "I(LIN|XBQ)", "P(BJS|XBQ)", "I(BJS|XBQ)", "P(BJL1|XBQ)", "I(BJL1|XBQ)", "P(BJL2|XBQ)", "I(BJL2|XBQ)"]
    rows: dict[str, Any] = {}
    changed = False
    for signal in common:
        result = numerical_identity(physical, signal, replay, signal, end_ps=PRE_WINDOW[1])
        rows[f"physical_vs_replay/{signal}"] = result
        changed = changed or result.get("status") == "FAIL"
    source = traces[("source", 13, "12x320", "logical1_read")]
    for signal in ("I(B_LD1)", "I(L_SL|XBVM1)", "V(SL1)"):
        result = numerical_identity(source, signal, physical, signal, end_ps=PRE_WINDOW[1])
        rows[f"grounded_source_vs_physical/{signal}"] = result
        changed = changed or result.get("status") == "FAIL"
    return {
        "status": "CHANGED" if changed else "PASS",
        "interpretation": "CHANGED means B/C initial trajectory already differs in the pre-window; it does not identify a READ-period lobe as cause.",
        "checks": rows,
    }


def backaction_analysis(traces: dict[tuple[str, int, str, str], Trace]) -> dict[str, Any]:
    source = traces[("source", 13, "12x320", "logical1_read")]
    physical = traces[("physical", 13, "12x320", "logical1_read")]
    result: dict[str, Any] = {"case_source": rel(source.path), "case_physical": rel(physical.path), "signals": {}}
    for signal in ("I(B_LD1)", "I(L_SL|XBVM1)", "V(SL1)"):
        result["signals"][signal] = {
            "source_vs_physical": paired_difference(source, signal, physical, signal, ACTIVITY_WINDOW),
        }
    ground = source.get("I(B_LD1)")
    phys = physical.get("I(B_LD1)")
    mask = window_mask(source.time_s, ACTIVITY_WINDOW)
    delta = ground - phys
    result["delta_i"] = current_metric_from_arrays(source.time_s, delta, ACTIVITY_WINDOW)
    result["delta_i"].update({
        "definition": "I_source_grounded - I_physical_JSL",
        "max_abs_time_ps": float((source.time_s[mask] * 1e12)[first_argmax(np.abs(delta[mask]))]),
    })
    result["pre_state_guard"] = pre_state_guard(traces)
    result["kcl"] = {
        "ideal_replay_13ps_12x320": qb_kcl(traces[("replay", 13, "12x320", "logical1_read")]),
        "physical_13ps_12x320": qb_kcl(traces[("physical", 13, "12x320", "logical1_read")]),
    }
    return result


def scalar_fit_for_arrays(
    time_s: np.ndarray,
    grounded: np.ndarray,
    physical: np.ndarray,
    *,
    mode: str,
) -> dict[str, Any]:
    mask = window_mask(time_s, ACTIVITY_WINDOW)
    pre = window_mask(time_s, PRE_WINDOW)
    g = grounded[mask].copy()
    p = physical[mask].copy()
    if mode == "baseline_corrected":
        g = g - float(np.median(grounded[pre]))
        p = p - float(np.median(physical[pre]))
    denominator = float(np.dot(g, g))
    if denominator <= 1e-40 or np.std(g) <= 1e-30 or np.std(p) <= 1e-30:
        return {"status": "INCONCLUSIVE", "mode": mode, "reason": "insufficient variance/denominator"}
    k = float(np.dot(g, p) / denominator)
    residual = p - k * g
    norm = float(np.linalg.norm(residual) / np.linalg.norm(p)) if np.linalg.norm(p) else None
    correlation = float(np.corrcoef(g, p)[0, 1])
    local_time_s = time_s[mask]
    local_time_ps = local_time_s * 1e12
    positive_g = np.maximum(g, 0.0)
    positive_p = np.maximum(p, 0.0)
    negative_g = np.minimum(g, 0.0)
    negative_p = np.minimum(p, 0.0)
    mg = {
        "signed": trapz(local_time_s, g),
        "positive": trapz(local_time_s, positive_g),
        "negative": trapz(local_time_s, negative_g),
    }
    mp = {
        "signed": trapz(local_time_s, p),
        "positive": trapz(local_time_s, positive_p),
        "negative": trapz(local_time_s, negative_p),
    }
    ig = first_argmax(g)
    ip = first_argmax(p)
    centroid_g = weighted_centroid(local_time_ps, local_time_s, g)
    centroid_p = weighted_centroid(local_time_ps, local_time_s, p)
    centroid_shift = centroid_p - centroid_g if centroid_p is not None and centroid_g is not None else None
    peak_shift = float(local_time_ps[ip] - local_time_ps[ig])
    max_residual_index = first_argmax(np.abs(residual))
    polarity_preserved = bool(k >= 0.0 and correlation >= 0.0)
    fit_checks = {
        "normalized_residual": norm is not None and norm <= SCALAR_RESIDUAL_MAX,
        "correlation": correlation >= SCALAR_CORRELATION_MIN,
        "positive_peak_time_shift": abs(peak_shift) <= SCALAR_PEAK_SHIFT_MAX_PS,
        "polarity_preserved": polarity_preserved,
    }
    return {
        "status": "PASS" if all(fit_checks.values()) else "FAIL",
        "mode": mode,
        "k": k,
        "normalized_residual": norm,
        "correlation": correlation,
        "signed_area_ratio": mp["signed"] / mg["signed"] if abs(mg["signed"]) > CENTROID_AREA_FLOOR_AS else None,
        "positive_area_ratio": mp["positive"] / mg["positive"] if abs(mg["positive"]) > CENTROID_AREA_FLOOR_AS else None,
        "negative_area_ratio": mp["negative"] / mg["negative"] if abs(mg["negative"]) > CENTROID_AREA_FLOOR_AS else None,
        "grounded_signed_area_As": mg["signed"],
        "physical_signed_area_As": mp["signed"],
        "grounded_positive_area_As": mg["positive"],
        "physical_positive_area_As": mp["positive"],
        "grounded_negative_area_As": mg["negative"],
        "physical_negative_area_As": mp["negative"],
        "timing_residual_ps": centroid_shift,
        "grounded_signed_centroid_ps": centroid_g,
        "physical_signed_centroid_ps": centroid_p,
        "grounded_positive_peak_time_ps": float(local_time_ps[ig]),
        "physical_positive_peak_time_ps": float(local_time_ps[ip]),
        "peak_time_shift_ps": peak_shift,
        "max_residual": float(np.max(np.abs(residual))),
        "max_residual_time_ps": float(local_time_ps[max_residual_index]),
        "polarity_preserved": polarity_preserved,
        "fit_checks": fit_checks,
        "tolerances": {
            "normalized_residual_max": SCALAR_RESIDUAL_MAX,
            "correlation_min": SCALAR_CORRELATION_MIN,
            "peak_time_shift_max_ps": SCALAR_PEAK_SHIFT_MAX_PS,
        },
    }


def scalar_analysis(traces: dict[tuple[str, int, str, str], Trace]) -> dict[str, Any]:
    source = traces[("source", 13, "12x320", "logical1_read")]
    physical = traces[("physical", 13, "12x320", "logical1_read")]
    fits = {
        "raw_origin": scalar_fit_for_arrays(source.time_s, source.get("I(B_LD1)"), physical.get("I(B_LD1)"), mode="raw_origin"),
        "baseline_corrected": scalar_fit_for_arrays(source.time_s, source.get("I(B_LD1)"), physical.get("I(B_LD1)"), mode="baseline_corrected"),
    }
    statuses = [fit["status"] for fit in fits.values()]
    result = {
        "definition": "I_physical_JSL ≈ k * I_grounded_source; no intercept",
        "window_ps": list(ACTIVITY_WINDOW),
        "fits": fits,
        "overall_model_status": "SUPPORTED" if statuses == ["PASS", "PASS"] else "DISFAVORED" if statuses == ["FAIL", "FAIL"] else "UNRESOLVED",
        "interpretation": "A fit only tests scalar shape approximation; it does not prove attenuation is sufficient to cause QB failure.",
    }
    return result


def dynamic_port_rows(traces: dict[tuple[str, int, str, str], Trace], backaction: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    detail: dict[str, Any] = {}
    for load in ("12x320", "8x500"):
        source = traces[("source", 13, load, "logical1_read")]
        physical = traces[("physical", 13, load, "logical1_read")]
        mask = window_mask(physical.time_s, ACTIVITY_WINDOW)
        source_current = source.get("I(B_LD1)")
        physical_current = physical.get("I(B_LD1)")
        denominator = source_current - physical_current
        z_mask = mask & (np.abs(denominator) > np.maximum(Z_DENOM_ABS_FLOOR_A, Z_DENOM_RELATIVE_FLOOR * np.max(np.abs(source_current))))
        quantities = {
            "V_IN": (physical.get("V(IN)"), "V", mask),
            "I_LIN": (physical.get("I(LIN|XBQ)"), "A", mask),
            "V_SL1": (physical.get("V(SL1)"), "V", mask),
            "I_source_grounded": (source_current, "A", mask),
            "I_physical_JSL": (physical_current, "A", mask),
            "DeltaI_grounded_minus_physical": (denominator, "A", mask),
            "Z_sec": (np.divide(physical.get("V(IN)"), denominator, out=np.full_like(denominator, np.nan), where=z_mask), "ohm", z_mask),
        }
        case_detail: dict[str, Any] = {"source": rel(source.path), "physical": rel(physical.path), "window_ps": list(ACTIVITY_WINDOW), "quantities": {}}
        for quantity, (values, unit, qmask) in quantities.items():
            selected = values[qmask]
            selected = selected[np.isfinite(selected)]
            valid_count = int(selected.size)
            stats = {
                "sample_count": int(np.count_nonzero(mask)),
                "valid_sample_count": valid_count,
                "mask_fraction": float(valid_count / np.count_nonzero(mask)) if np.count_nonzero(mask) else None,
                "unit": unit,
                "min": float(np.min(selected)) if valid_count else None,
                "max": float(np.max(selected)) if valid_count else None,
                "median": float(np.median(selected)) if valid_count else None,
                "p05": float(np.percentile(selected, 5)) if valid_count else None,
                "p95": float(np.percentile(selected, 95)) if valid_count else None,
                "max_abs": float(np.max(np.abs(selected))) if valid_count else None,
                "status": "VALID" if valid_count >= 2 else "INCONCLUSIVE",
                "notes": "TWO-BOUNDARY DYNAMIC SECANT DIAGNOSTIC; not a Thévenin/small-signal impedance" if quantity == "Z_sec" else "",
            }
            case_detail["quantities"][quantity] = stats
            rows.append({
                "case": f"physical/13ps/{load}/logical1_read",
                "diagnostic": "TWO-BOUNDARY DYNAMIC SECANT DIAGNOSTIC" if quantity == "Z_sec" else "dynamic_port",
                "quantity": quantity,
                "window_start_ps": ACTIVITY_WINDOW[0],
                "window_end_ps": ACTIVITY_WINDOW[1],
                **stats,
            })
        detail[load] = case_detail
    return rows, detail


def timeline_for_load(traces: dict[tuple[str, int, str, str], Trace], load: str) -> dict[str, Any]:
    source_a = traces[("source", 9, load, "logical1_read")]
    source_b = traces[("source", 13, load, "logical1_read")]
    replay_a = traces[("replay", 9, load, "logical1_read")]
    replay_b = traces[("replay", 13, load, "logical1_read")]
    family_records: list[dict[str, Any]] = []
    source_signals = [signal for signal in SOURCE_SIGNALS[load] if signal in source_a.columns and signal in source_b.columns]
    for family, signals, left, right in [("source waveform", source_signals, source_a, source_b)]:
        for signal in signals:
            result = first_divergence(left, signal, right, signal)
            family_records.append({"family": family, "signal": signal, "fixture": "source", "result": result})
    for family, signals in QB_FAMILIES.items():
        for signal in signals:
            if signal in replay_a.columns and signal in replay_b.columns:
                result = first_divergence(replay_a, signal, replay_b, signal)
                family_records.append({"family": family, "signal": signal, "fixture": "replay", "result": result})
    first_by_family: dict[str, dict[str, Any]] = {}
    for record in family_records:
        first = record["result"].get("first_divergence")
        if first is None:
            continue
        existing = first_by_family.get(record["family"])
        if existing is None or first["sample_index"] < existing["sample_index"]:
            first_by_family[record["family"]] = {
                "family": record["family"],
                "signal": record["signal"],
                **first,
                "threshold": record["result"]["threshold"],
                "unit": record["result"]["unit"],
            }
    ordered = sorted(first_by_family.values(), key=lambda item: item["sample_index"])
    bins: dict[int, list[str]] = {}
    for item in ordered:
        bins.setdefault(item["sample_index"], []).append(item["family"])
    for item in ordered:
        item["tie"] = len(bins[item["sample_index"]]) > 1
        item["tie_families"] = bins[item["sample_index"]] if item["tie"] else []
    identity: dict[str, Any] = {}
    for signal in source_signals:
        identity[f"source/{signal}"] = numerical_identity(source_a, signal, source_b, signal, end_ps=PRE_DIVERGENCE_END_PS)
    for signal in QB_SIGNALS:
        if signal in replay_a.columns and signal in replay_b.columns:
            identity[f"replay/{signal}"] = numerical_identity(replay_a, signal, replay_b, signal, end_ps=PRE_DIVERGENCE_END_PS)
    return {
        "load": load,
        "case_a": {"source": rel(source_a.path), "replay": rel(replay_a.path)},
        "case_b": {"source": rel(source_b.path), "replay": rel(replay_b.path)},
        "pre_divergence_end_ps": PRE_DIVERGENCE_END_PS,
        "identity_status": "PASS" if all(item["status"] == "PASS" for item in identity.values()) else "FAIL",
        "identity": identity,
        "family_first_divergence": ordered,
        "signal_records": family_records,
        "algorithm": "continuous unwrap for P; max(10*p99.9 baseline, 1e-12*scale, 100*eps*scale); two consecutive samples; TIE at same sample index",
    }


def load_strict_reference() -> dict[str, Any]:
    path = STRICT / "analysis/strict-event-summary.csv"
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    index = {(row["fixture"], int(row["width_ps"]), row["jsl_load"], row["role"]): row for row in rows}
    wanted = {
        "A_9ps_12x320_replay": ("replay", 9, "12x320", "logical1_read"),
        "B_13ps_12x320_replay": ("replay", 13, "12x320", "logical1_read"),
        "C_13ps_12x320_physical": ("physical", 13, "12x320", "logical1_read"),
        "D_13ps_8x500_replay": ("replay", 13, "8x500", "logical1_read"),
        "E_13ps_8x500_physical": ("physical", 13, "8x500", "logical1_read"),
    }
    return {
        "path": rel(path),
        "sha256": sha256(path),
        "cases": {name: index[key] for name, key in wanted.items()},
        "authority": "pre-existing strict BJL2 reclassification; not recomputed here",
    }


def raw_provenance(traces: dict[tuple[str, int, str, str], Trace], executions: dict[tuple[str, int, str, str], dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    matrix_manifest = MATRIX / "manifest.yaml"
    manifest_payload: dict[str, Any] = {}
    if matrix_manifest.exists():
        try:
            manifest_payload = json.loads(matrix_manifest.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            manifest_payload = {}
    cache: dict[str, Any] = {
        "parent_head": PARENT_HEAD,
        "matrix_root": rel(MATRIX),
        "matrix_manifest": {
            "path": rel(matrix_manifest),
            "sha256": sha256(matrix_manifest) if matrix_manifest.exists() else None,
            "solver": manifest_payload.get("solver"),
            "metric_spec": manifest_payload.get("metric_spec"),
        },
        "cases": [],
    }
    for fixture in FIXTURES:
        for width in WIDTHS:
            for load in LOADS:
                for role in ROLES:
                    key = (fixture, width, load, role)
                    path = case_path(*key)
                    execution = executions.get(key, {})
                    actual_sha256 = sha256(path) if path.exists() else None
                    recorded_sha256 = execution.get("raw_sha256")
                    entry: dict[str, Any] = {
                        "fixture": fixture,
                        "width_ps": width,
                        "jsl_load": load,
                        "role": role,
                        "raw_path": rel(path),
                        "raw_exists": path.exists(),
                        "raw_sha256": actual_sha256,
                        "sidecar": sidecar_info(path) if path.exists() else {"exists": False},
                        "execution": {
                            "returncode": execution.get("returncode"),
                            "stdout": execution.get("stdout"),
                            "stderr": execution.get("stderr"),
                            "recorded_raw_sha256": recorded_sha256,
                            "recorded_hash_matches": bool(actual_sha256 and recorded_sha256 == actual_sha256),
                        },
                    }
                    trace = traces.get(key)
                    if trace is not None:
                        delta = np.diff(trace.time_s)
                        entry.update({
                            "header": trace.header,
                            "sample_count": int(trace.time_s.size),
                            "start_ps": float(trace.time_s[0] * 1e12),
                            "end_ps": float(trace.time_s[-1] * 1e12),
                            "time_strictly_increasing": bool(np.all(delta > 0.0)),
                            "unique_intervals_ps": sorted({round(float(item * 1e12), 12) for item in delta}),
                            "non_nominal_interval_count": int(np.count_nonzero(np.abs(delta - 0.0125e-12) > 1e-24)),
                            "required_columns_present": [signal for signal in required_signals(fixture, load) if signal in trace.columns],
                            "required_columns_missing": [signal for signal in required_signals(fixture, load) if signal not in trace.columns],
                        })
                    entry["qa_status"] = "VALID" if (
                        entry["raw_exists"]
                        and entry["sidecar"].get("matches")
                        and entry["execution"].get("recorded_hash_matches")
                        and execution.get("returncode") == 0
                        and trace is not None
                        and not entry.get("required_columns_missing")
                        and entry.get("time_strictly_increasing")
                    ) else "INVALID"
                    entries.append(entry)
    cache["cases"] = entries
    cache["all_cases_qa_status"] = "PASS" if all(item["qa_status"] == "VALID" for item in entries) else "FAIL"
    return entries, cache


def hypothesis_table(
    source_results: dict[str, Any],
    timelines: dict[str, Any],
    backaction: dict[str, Any],
    scalar: dict[str, Any],
    dynamic: dict[str, Any],
    all_identity: bool,
) -> list[dict[str, Any]]:
    source = source_results["12x320"]["signals"]["I(B_LD1)"]
    decomposition = source["difference_decomposition"]
    abs_total = sum(float(decomposition[name].get("absolute_integral_uA_ps", 0.0)) for name, *_ in SOURCE_DIFF_WINDOWS)
    extension = sum(float(decomposition[name].get("absolute_integral_uA_ps", 0.0)) for name in ("105_106ps", "106_109ps", "109_110ps"))
    outside = abs_total - extension
    extension_share = extension / abs_total if abs_total else None
    h1_status = "SUPPORTED" if all_identity and extension_share is not None and extension_share >= H1_EXTENSION_SHARE_MIN else "DISFAVORED" if all_identity and extension_share is not None else "UNRESOLVED"
    outside_share = outside / abs_total if abs_total else None
    h2_status = "SUPPORTED" if all_identity and outside_share is not None and outside_share >= H2_OUTSIDE_SHARE_MIN else "UNRESOLVED"
    delta = backaction["delta_i"]
    input_difference = dynamic["12x320"]["quantities"]["I_LIN"]["max_abs"]
    h4_status = "SUPPORTED" if delta.get("status") == "VALID" and delta.get("max_abs", 0.0) > 0.0 and input_difference is not None and input_difference > 0.0 else "UNRESOLVED"
    h5_status = scalar["overall_model_status"]
    h6_status = "SUPPORTED" if h5_status == "DISFAVORED" else "DISFAVORED" if h5_status == "SUPPORTED" else "UNRESOLVED"
    return [
        {"id": "H1", "prediction": "READ extension mainly adds useful source duration/area", "observation": {"pre_identity": all_identity, "absolute_difference_area_uA_ps": abs_total, "extension_105_110_share": extension_share, "strict_boundary_reference": "A SUBTHRESHOLD -> B CLEAN_ONE reference"}, "status": h1_status, "allowed_wording": "bounded source-area/duration compatibility; not unique causation"},
        {"id": "H2", "prediction": "READ extension changes source shape/trailing/timing onto another nonlinear branch", "observation": {"outside_105_110_absolute_difference_share": outside_share, "decomposition_windows": list(decomposition)}, "status": h2_status, "allowed_wording": "only a shape/timing family statement if outside-extension signature is present"},
        {"id": "H3", "prediction": "QB internal current partition near BJs/BJL1/node2 is the discriminator", "observation": {"timeline_12x320": [{"family": item["family"], "signal": item["signal"], "time_ps": item["time_ps"], "tie": item.get("tie", False)} for item in timelines["12x320"]["family_first_divergence"]], "kcl_status": {name: value["overall_status"] for name, value in backaction["kcl"].items()}}, "status": "UNRESOLVED", "allowed_wording": "mediator/compatibility evidence only; no independent intervention"},
        {"id": "H4", "prediction": "physical source/load closure changes the trajectory versus grounded ideal replay", "observation": {"delta_i_max_A": delta.get("max_abs"), "delta_i_rms_A": delta.get("rms"), "pre_state_guard": backaction["pre_state_guard"]["status"], "dynamic_input_difference_max_A": input_difference}, "status": h4_status, "allowed_wording": "overall dynamic source-load interaction is supported if report conditions pass"},
        {"id": "H5", "prediction": "physical source is a scalar attenuation of grounded source", "observation": scalar["fits"], "status": "SUPPORTED" if h5_status == "SUPPORTED" else "DISFAVORED" if h5_status == "DISFAVORED" else "UNRESOLVED", "allowed_wording": "fit property only; attenuation is not a sufficient-cause proof"},
        {"id": "H6", "prediction": "scalar attenuation is insufficient; waveform/load-line reshaping is required", "observation": {"scalar_model_status": h5_status, "raw_origin_normalized_residual": scalar["fits"]["raw_origin"].get("normalized_residual"), "baseline_corrected_normalized_residual": scalar["fits"]["baseline_corrected"].get("normalized_residual")}, "status": h6_status, "allowed_wording": "bounded non-scalar waveform/load-line family, not unique device mechanism"},
        {"id": "H7", "prediction": "12x320 vs 8x500 difference is primarily source/load-line rather than fundamental BJL2 change", "observation": {"strict_reference_difference_turns": "1.016028923 - 0.973287067", "source_and_internal_comparison": "recorded in qb-internal-comparison.csv"}, "status": "UNRESOLVED", "allowed_wording": "junction count and Ic/area are confounded; no primary attribution"},
    ]


def fmt(value: Any, digits: int = 6) -> str:
    if value is None or value == "":
        return "—"
    if isinstance(value, bool):
        return "是" if value else "否"
    if isinstance(value, (float, np.floating)):
        if not math.isfinite(float(value)):
            return "—"
        return f"{float(value):.{digits}g}"
    return str(value)


def hypothesis_status(table: list[dict[str, Any]], ident: bool, raw_status: str, kcl_status: str, scalar: dict[str, Any]) -> str:
    if raw_status != "PASS" or not ident or kcl_status != "PASS":
        return "DYNAMIC_SOURCE_LOADLINE_AUDIT_INCONCLUSIVE"
    if scalar["overall_model_status"] == "UNRESOLVED":
        return "DYNAMIC_SOURCE_LOADLINE_AUDIT_INCONCLUSIVE"
    h4 = next(item for item in table if item["id"] == "H4")
    h6 = next(item for item in table if item["id"] == "H6")
    if h4["status"] == "SUPPORTED" and h6["status"] == "SUPPORTED":
        return "DYNAMIC_SOURCE_LOADLINE_MECHANISM_SUPPORTED"
    return "DYNAMIC_SOURCE_LOADLINE_AUDIT_INCONCLUSIVE"


def build_report(
    status: str,
    source_results: dict[str, Any],
    timelines: dict[str, Any],
    backaction: dict[str, Any],
    scalar: dict[str, Any],
    dynamic: dict[str, Any],
    hypotheses: list[dict[str, Any]],
    provenance: dict[str, Any],
    strict: dict[str, Any],
) -> str:
    primary_source = source_results["12x320"]["signals"]["I(B_LD1)"]
    source13 = source_results["12x320"]["signals"]["I(B_LD1)"]["b"]
    source9 = source_results["12x320"]["signals"]["I(B_LD1)"]["a"]
    delta = backaction["delta_i"]
    scalar_raw = scalar["fits"]["raw_origin"]
    scalar_bc = scalar["fits"]["baseline_corrected"]
    cross_load = source_results["cross_load_13ps_ideal"]["signals"]
    source8 = cross_load["I(B_LD1)"]["a"]
    source12 = cross_load["I(B_LD1)"]["b"]
    vsl8 = cross_load["V(SL1)"]["a"]
    vsl12 = cross_load["V(SL1)"]["b"]
    lines = [
        "# BVM_QB_DYNAMIC_SOURCE_LOADLINE_AUDIT_V1",
        "",
        f"## 1. Executive scientific result: `{status}`",
        "",
        "本轮是只读 physics-first mechanism audit：没有运行 JoSIM、没有扫参、没有修改 QB/BVM/JSL、读宽、拓扑、JTL、T1 或 magnetic coupling。所有 raw 证据来自已存在的 48-run matrix；既有 strict BJL2 分类只作为冻结 reference 使用。",
        "",
        f"最强有界结论：{'当前证据支持整体 dynamic source-load interaction，并且 scalar attenuation 不能充分描述 physical source waveform；不能唯一定位到某一颗器件。' if status == 'DYNAMIC_SOURCE_LOADLINE_MECHANISM_SUPPORTED' else '当前证据不足以闭合整体 dynamic source-load mechanism；保留为 audit inconclusive。'}",
        "",
        f"A/B 105 ps 前 identity：12x320=`{timelines['12x320']['identity_status']}`，8x500=`{timelines['8x500']['identity_status']}`；B/C pre-state guard：`{backaction['pre_state_guard']['status']}`；QB KCL closure：ideal/physical=`{backaction['kcl']['ideal_replay_13ps_12x320']['overall_status']}`/`{backaction['kcl']['physical_13ps_12x320']['overall_status']}`。",
        "",
        "## 2. Observed",
        "",
        f"- 输入目录为 `{provenance['matrix_root']}`；48/48 raw 的 hash、sidecar、执行返回码、列和时间轴 QA：`{provenance['all_cases_qa_status']}`。",
        f"- 9/13 ps source 的首个 JSL branch `I(B_LD1)` 在 12x320 activity 指标分别为 peak `{fmt(source9['positive_peak'])}` / `{fmt(source13['positive_peak'])}` A，signed area `{fmt(source9['signed_integral_uA_ps'])}` / `{fmt(source13['signed_integral_uA_ps'])}` uA·ps；这些是 waveform diagnostics，不是 SFQ quantity。",
        f"- 13 ps / 12x320 grounded source 与 physical JSL 的 `DeltaI=I_grounded-I_physical`：max abs `{fmt(delta.get('max_abs'))}` A，RMS `{fmt(delta.get('rms'))}` A，signed area `{fmt(delta.get('signed_integral_uA_ps'))}` uA·ps，最大差时间 `{fmt(delta.get('max_abs_time_ps'))}` ps。",
        f"- scalar fit raw-origin：k=`{fmt(scalar_raw.get('k'))}`，normalized residual=`{fmt(scalar_raw.get('normalized_residual'))}`，correlation=`{fmt(scalar_raw.get('correlation'))}`，peak shift=`{fmt(scalar_raw.get('peak_time_shift_ps'))}` ps，status=`{scalar_raw.get('status')}`；baseline-corrected status=`{scalar_bc.get('status')}`。",
        "",
        "## 3. Derived",
        "",
        "- A/B 轨迹的 source、QB input、BJs、node2/BJL1、node3、BJL2、OUT 的 earliest divergence 使用预注册的 numerical floor 和连续两个采样点规则；同 sampling bin 记 TIE，不超过当前时间分辨率解释。详情见 `analysis/divergence-timeline.json`。",
        "- source current 的正/负/带符号面积、centroid、first moment 和 difference-area 分解均使用 raw 实际 time 的梯形积分；它们描述 source waveform，不是量子数或事件数。",
        "- `V(IN)`–`I(LIN|XBQ)` 是有记忆的 dynamic port trajectory；`Z_sec` 仅作为 **TWO-BOUNDARY DYNAMIC SECANT DIAGNOSTIC** 保存，并已 mask 小 denominator。它不是 Thévenin impedance、不是 small-signal impedance、不是 constant physical resistor。",
        "- KCL residual 使用 netlist 端点方向：`I(LIN)=IN→1`、`I(BJs)=1→2`、`I(BJL1/RJ1)=2→0`、`I(L1)=2→3`、`I(RB)=IB→3`、`I(L2)=3→4`、`I(L0)=4→OUT`、`I(BJL2/RJ2)=4→0`。",
        "- `analysis/independent-raw-recheck.json` 通过不复用主分析函数的 raw-only 路径复算 source peak/area、B/C DeltaI、scalar residual 和 QB KCL 子集；它是机械一致性检查，不是第二个科学权威。",
        "",
        "## 4. Physics-based inference（有界）",
        "",
        "- A→B：READ extension 的 causally allowed difference 只能在 105 ps 之后；若 source difference-area 主要集中在延长区，它支持“输入可用 duration/area 参与跨越 boundary”的 family-level inference，但不排除 trailing shape/timing。",
        "- B→C：grounded source、physical JSL 和 QB `I(LIN)` 的差异支持整体 source/load closure 改变了 QB 所见 trajectory。若 pre-state 已不同，不能写成 READ 期间某一个 lobe 单独摧毁事件。",
        "- H5 scalar attenuation 的结果只说明拟合是否足够；即使 correlation 较高，也不证明 attenuation 是 QB failure 的充分原因。",
        "- 本报告不把 13 ps / 12x320 的 local BJL2 candidate 写成 JTL delivery，也不把 physical failure 归因为某一颗 BVM/JSL/QB 器件。",
        "",
        "## 5. Competing hypotheses",
        "",
        "| ID | status | 证据摘要 | 允许措辞 |",
        "|---|---|---|---|",
    ]
    for item in hypotheses:
        lines.append(f"| {item['id']} | `{item['status']}` | {json.dumps(item['observation'], ensure_ascii=False, separators=(',', ':'))} | {item['allowed_wording']} |")
    lines += [
        "",
        "## 6. A → B：9 ps subthreshold 到 13 ps clean-one reference",
        "",
        "A/B strict 数值不在本轮重新解释；这里只审计它们对应的 source 与 QB internal trajectory。A/B pre-105 identity、差分面积窗口和 earliest divergence 顺序见分析 CSV/JSON。",
        "",
        f"12x320 source `I(B_LD1)`：A peak/area=`{fmt(source9['positive_peak'])} A`/`{fmt(source9['signed_integral_uA_ps'])} uA·ps`；B peak/area=`{fmt(source13['positive_peak'])} A`/`{fmt(source13['signed_integral_uA_ps'])} uA·ps`。",
        f"12x320 causal timeline first family records：{'; '.join(f"{item['family']}@{fmt(item['time_ps'])}ps{' TIE' if item.get('tie') else ''}" for item in timelines['12x320']['family_first_divergence']) or '无超过冻结 floor 的连续 divergence'}。",
        "",
        "## 7. B → C：ideal clean-one reference 到 physical subthreshold",
        "",
        f"B/C source-load difference 的 `DeltaI` 最大绝对值为 `{fmt(delta.get('max_abs'))} A`，不是静态阻抗；pre-state guard=`{backaction['pre_state_guard']['status']}`。",
        f"physical 与 ideal replay 的 input/current trajectory、BJs/BJL1/BJL2 和 KCL closure 见 `analysis/qb-internal-comparison.csv` 及 `analysis/divergence-timeline.json`。",
        "",
        "## 8. 12x320 vs 8x500",
        "",
        "13 ps ideal 的 12x320/8x500 strict reference 分别为既有 `1.016...` 与 `0.973...` turns；本轮只比较 source、input、内部 phase/current partition。由于 JSL 数量和 JJ area/Ic 同时变化，H7 的“primarily”保持 UNRESOLVED，不能把接近一圈写成 candidate 或 margin。",
        f"source 侧 8x500→12x320 的 `I(B_LD1)` peak=`{fmt(source8['positive_peak'])}`→`{fmt(source12['positive_peak'])}` A，signed area=`{fmt(source8['signed_integral_uA_ps'])}`→`{fmt(source12['signed_integral_uA_ps'])}` uA·ps，effective duration=`{fmt((source8.get('effective_duration') or {}).get('duration_ps'))}`→`{fmt((source12.get('effective_duration') or {}).get('duration_ps'))}` ps；`V(SL1)` peak=`{fmt(vsl8['positive_peak'])}`→`{fmt(vsl12['positive_peak'])}` V。完整 source-side、QB input、BJs/BJL1/BJL2/current-partition 对照见 `analysis/source-waveform-comparison.csv` 和 `analysis/qb-internal-comparison.csv`。",
        "",
        "## 9. Dynamic load-line interpretation",
        "",
        "`V(IN)` vs `I(LIN|XBQ)` 和 `V(SL1)` vs source/JSL current 以时间可追踪的 parametric HTML 图保存。它们展示 trajectory，不是静态 load line；`Z_sec` 的全部定义、mask 和限制写在 `analysis/dynamic-port-diagnostics.csv`。",
        "",
        "## 10. What is still unknown",
        "",
        "- H1 与 H2 的 duration/area 和 shape/timing 唯一分解；",
        "- H3 具体哪一颗内部 JJ/哪条支路是 critical cause；当前只有 mediator evidence；",
        "- B/C 差异来自 pre-state、READ-period reshaping，还是二者共同作用；",
        "- 12x320 与 8x500 中 JSL 数量、Ic/area 各自贡献；",
        "- scalar fit 对 QB failure 的充分性；",
        "- Thévenin/small-signal impedance、论文 Fig.7 的器件映射、timestep robustness、无限时间稳定性、硬件行为、JTL/T1 接收和 system Gate。",
        "",
        "## 11. Parameter recommendation gate",
        "",
        "本轮不推荐具体参数或方向，也不启动 sweep。下一候选轮必须另行 preregister，并在至少 0.025/0.0125/0.00625 ps 下验证；当前 1.016 与 0.973 只能作为靠近一圈 boundary 的 mechanism reference，不能称 robust operating margin。",
        "",
        "## Provenance and evidence boundary",
        "",
        f"全部 raw SHA-256 见 `analysis/raw-provenance.json`；strict reference 见 `{strict['path']}`（SHA `{strict['sha256']}`）。Sol XHigh read-only pre-review 见 `analysis/reviewer-notes.md`。",
        "",
        "本任务完成后停止，不更新 HANDOVER/todo，不执行下一实验。",
        "",
    ]
    return "\n".join(lines)


def build_summary(status: str, hypotheses: list[dict[str, Any]], backaction: dict[str, Any], scalar: dict[str, Any], timelines: dict[str, Any]) -> str:
    h4 = next(item for item in hypotheses if item["id"] == "H4")
    h6 = next(item for item in hypotheses if item["id"] == "H6")
    return "\n".join([
        "# BVM_QB_DYNAMIC_SOURCE_LOADLINE_AUDIT_V1",
        "",
        f"状态：`{status}`",
        "",
        "只读分析既有 48-run matrix raw；没有新 JoSIM、扫参或电路修改。",
        "",
        f"- A/B 105 ps 前 identity：12x320 `{timelines['12x320']['identity_status']}`；8x500 `{timelines['8x500']['identity_status']}`",
        f"- B/C pre-state guard：`{backaction['pre_state_guard']['status']}`",
        f"- H4 overall source-load interaction：`{h4['status']}`；H5 scalar fit：`{next(item for item in hypotheses if item['id']=='H5')['status']}`；H6 non-scalar family：`{h6['status']}`",
        f"- DeltaI max abs：`{fmt(backaction['delta_i'].get('max_abs'))} A`；scalar raw fit residual：`{fmt(scalar['fits']['raw_origin'].get('normalized_residual'))}`",
        "",
        "关键证据：",
        "",
        "- `analysis/source-waveform-comparison.csv`",
        "- `analysis/qb-internal-comparison.csv`",
        "- `analysis/divergence-timeline.json`",
        "- `analysis/scalar-attenuation-test.json`",
        "- `analysis/dynamic-port-diagnostics.csv`",
        "- `analysis/hypothesis-table.json`",
        "- `analysis/independent-raw-recheck.json`",
        "- `analysis/raw-provenance.json`",
        "",
        "图只作描述性展示；严格事件、同段 phase/area、控制和步长边界不被机制图替代。",
        "本任务到此停止；下一实验必须另行 preregister。",
        "",
    ])


def main() -> str:
    current_head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, check=True, capture_output=True, text=True).stdout.strip()
    if current_head != PARENT_HEAD:
        raise RuntimeError(f"HEAD changed after preregistration: expected {PARENT_HEAD}, got {current_head}")
    traces: dict[tuple[str, int, str, str], Trace] = {}
    load_errors: list[dict[str, Any]] = []
    for fixture in FIXTURES:
        for width in WIDTHS:
            for load in LOADS:
                for role in ROLES:
                    key = (fixture, width, load, role)
                    path = case_path(*key)
                    try:
                        traces[key] = load_trace(path)
                    except (OSError, ValueError, KeyError) as exc:
                        load_errors.append({"case": key, "path": rel(path), "error": str(exc)})
    executions = execution_index()
    _entries, provenance = raw_provenance(traces, executions)
    source_rows, source_results, source_identity = source_analysis(traces)
    timeline = {load: timeline_for_load(traces, load) for load in LOADS}
    all_identity = all(item["status"] == "PASS" for item in source_identity.values()) and all(timeline[load]["identity_status"] == "PASS" for load in LOADS)
    qb_rows: list[dict[str, Any]] = []
    comparisons: dict[str, Any] = {}
    pairs = [
        ("A_vs_B_ideal_12x320", ("replay", 9, "12x320", "logical1_read"), ("replay", 13, "12x320", "logical1_read"), QB_SIGNALS, "12x320"),
        ("D_vs_B_ideal_13ps_load", ("replay", 13, "8x500", "logical1_read"), ("replay", 13, "12x320", "logical1_read"), QB_SIGNALS, "8x500_vs_12x320"),
        ("B_vs_C_qb_13ps_12x320", ("replay", 13, "12x320", "logical1_read"), ("physical", 13, "12x320", "logical1_read"), [signal for signal in QB_SIGNALS if signal != "I(I_REPLAY)"], "12x320"),
    ]
    for name, left_key, right_key, signals, load in pairs:
        comparison = qb_metric_comparison(traces, left_key, right_key, name, signals, load)
        comparisons[name] = comparison
        qb_metric_rows_before = len(qb_rows)
        qb_comparison_rows(qb_rows, comparison, name, rel(traces[left_key].path), rel(traces[right_key].path), load)
        comparison["row_count"] = len(qb_rows) - qb_metric_rows_before
    for key, trace in traces.items():
        if key[0] in {"replay", "physical"} and key[1] in {13} and key[3] == "logical1_read":
            comparisons.setdefault("kcl", {})["/".join(map(str, key))] = qb_kcl(trace)
    backaction = backaction_analysis(traces)
    dynamic_rows, dynamic = dynamic_port_rows(traces, backaction)
    scalar = scalar_analysis(traces)
    strict = load_strict_reference()
    hypotheses = hypothesis_table(source_results, timeline, backaction, scalar, dynamic, all_identity)
    kcl_status = backaction["kcl"]["ideal_replay_13ps_12x320"]["overall_status"]
    if backaction["kcl"]["physical_13ps_12x320"]["overall_status"] != "PASS":
        kcl_status = "FAIL"
    status = hypothesis_status(hypotheses, all_identity, provenance["all_cases_qa_status"], kcl_status, scalar)

    ANALYSIS.mkdir(parents=True, exist_ok=True)
    source_fields = ["comparison", "case_a", "case_b", "load", "signal", "unit", "quantity", "window", "value_a", "value_b", "delta_b_minus_a", "ratio_b_over_a", "notes"]
    write_csv(ANALYSIS / "source-waveform-comparison.csv", source_rows, source_fields)
    write_csv(ANALYSIS / "qb-internal-comparison.csv", qb_rows, source_fields)
    write_csv(ANALYSIS / "dynamic-port-diagnostics.csv", dynamic_rows, ["case", "diagnostic", "quantity", "window_start_ps", "window_end_ps", "sample_count", "valid_sample_count", "mask_fraction", "unit", "min", "max", "median", "p05", "p95", "max_abs", "status", "notes"])
    write_json(ANALYSIS / "divergence-timeline.json", {"document_type": "bvm_qb_causal_divergence_timeline", "recorded_at": RECORDED_AT, "parent_head": PARENT_HEAD, "status": "PASS" if all_identity else "STOP_NUMERICAL_OR_DECK_IDENTITY", "timelines": timeline, "b_to_c_backaction": {"delta_i": backaction["delta_i"], "pre_state_guard": backaction["pre_state_guard"]}})
    write_json(ANALYSIS / "scalar-attenuation-test.json", {"document_type": "scalar_attenuation_test", "recorded_at": RECORDED_AT, "parent_head": PARENT_HEAD, **scalar})
    write_json(ANALYSIS / "hypothesis-table.json", {"document_type": "bvm_qb_dynamic_source_loadline_hypotheses", "recorded_at": RECORDED_AT, "parent_head": PARENT_HEAD, "status": status, "hypotheses": hypotheses})
    write_json(ANALYSIS / "raw-provenance.json", provenance)
    write_json(ANALYSIS / "audit-details.json", {
        "document_type": "bvm_qb_dynamic_source_loadline_audit_details",
        "recorded_at": RECORDED_AT,
        "parent_head": PARENT_HEAD,
        "status": status,
        "load_errors": load_errors,
        "source_results": source_results,
        "source_pre_identity": source_identity,
        "qb_comparisons": comparisons,
        "backaction": backaction,
        "dynamic_port": dynamic,
        "scalar": scalar,
        "strict_reference": strict,
        "frozen_tolerances": {
            "identity_relative_floor": IDENTITY_RELATIVE_FLOOR,
            "sustained_divergence_samples": SUSTAINED_DIVERGENCE_SAMPLES,
            "centroid_area_floor_As": CENTROID_AREA_FLOOR_AS,
            "kcl_abs_floor_A": KCL_ABS_FLOOR_A,
            "kcl_relative_floor": KCL_RELATIVE_FLOOR,
            "z_sec_denominator_abs_floor_A": Z_DENOM_ABS_FLOOR_A,
            "z_sec_denominator_relative_floor": Z_DENOM_RELATIVE_FLOOR,
            "scalar_residual_max": SCALAR_RESIDUAL_MAX,
            "scalar_correlation_min": SCALAR_CORRELATION_MIN,
            "scalar_peak_shift_max_ps": SCALAR_PEAK_SHIFT_MAX_PS,
            "h1_extension_share_min": H1_EXTENSION_SHARE_MIN,
            "h2_outside_share_min": H2_OUTSIDE_SHARE_MIN,
        },
    })
    report = build_report(status, source_results, timeline, backaction, scalar, dynamic, hypotheses, provenance, strict)
    (TARGET / "REPORT.md").write_text(report, encoding="utf-8")
    (ANALYSIS / "REPORT.md").write_text(report, encoding="utf-8")
    (TARGET / "SUMMARY.md").write_text(build_summary(status, hypotheses, backaction, scalar, timeline), encoding="utf-8")
    print(status)
    print(json.dumps({
        "raw_qa": provenance["all_cases_qa_status"],
        "identity": {load: timeline[load]["identity_status"] for load in LOADS},
        "kcl": kcl_status,
        "scalar": scalar["overall_model_status"],
        "hypotheses": {item["id"]: item["status"] for item in hypotheses},
    }, ensure_ascii=False, sort_keys=True))
    return status


if __name__ == "__main__":
    main()
