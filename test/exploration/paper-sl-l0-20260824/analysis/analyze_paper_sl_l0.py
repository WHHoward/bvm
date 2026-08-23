#!/usr/bin/env python3
"""Direct phase/voltage-area and source-guard audit for PAPER-SL-L0.

This script intentionally does not call scripts/sfq_metrics.py.  JSL phase is
raw JoSIM radians; all turns and voltage areas are derived from the same CSV
time axis and the same JJ/segment.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw"
BASE = ROOT.parent / "bvm-internal-readout-20260819" / "raw"
PHI0 = 2.067833848e-15
TWO_PI = 2.0 * math.pi

CASES = {
    "logical1-read": "pos-read-single",
    # Canonical same +READ comparison: negative initialization with +100 uA
    # READ, not the separately archived negative-polarity READ fixture.
    "logical0-read": "neg-init-pos-read",
    "logical1-read0-control": "pos-control",
    "logical0-read0-control": "neg-control",
}
WINDOWS = {
    "startup": (0.0, 30.0),
    "pre_read": (80.0, 90.0),
    "read_activity": (94.0, 130.0),
    "post": (140.0, 170.0),
    "full": (0.0, 170.0),
}
JSL = tuple(f"B_LD{i}" for i in range(1, 13))
STORAGE = (
    "P(B_JM1|XBVM1)",
    "P(B_JM2|XBVM1)",
    "P(B_JS1|XBVM1)",
    "P(B_JS2|XBVM1)",
)
SOURCE = (
    "V(SL1)",
    "V(N6|XBVM1)",
    "I(L_SL|XBVM1)",
    "I(L_PSL|XBVM1)",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def load_csv(path: Path) -> dict[str, np.ndarray]:
    with path.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError(f"empty CSV: {path}")
    arrays = {
        key: np.asarray([float(row[key]) for row in rows], dtype=float)
        for key in rows[0]
    }
    time_s = arrays["time"]
    if not np.all(np.isfinite(time_s)) or np.any(np.diff(time_s) <= 0):
        raise ValueError(f"invalid time axis: {path}")
    arrays["time_s"] = time_s
    arrays["time_ps"] = time_s * 1.0e12
    return arrays


def mask(time_ps: np.ndarray, bounds: tuple[float, float]) -> np.ndarray:
    return (time_ps >= bounds[0]) & (time_ps < bounds[1])


def area_turns(time_s: np.ndarray, voltage: np.ndarray) -> float:
    return float(np.trapezoid(voltage, time_s) / PHI0)


def monotonic_segments(
    time_ps: np.ndarray, phase_rad: np.ndarray, voltage: np.ndarray
) -> list[dict[str, float]]:
    if len(phase_rad) < 2:
        return []
    phase = np.unwrap(phase_rad)
    delta = np.diff(phase)
    signs = np.sign(delta)
    nonzero = np.flatnonzero(signs)
    if nonzero.size == 0:
        return []
    for index in range(len(signs)):
        if signs[index] == 0:
            left = nonzero[nonzero < index]
            right = nonzero[nonzero > index]
            signs[index] = signs[left[-1]] if left.size else signs[right[0]]
    starts = [0]
    for index in range(1, len(signs)):
        if signs[index] != signs[index - 1]:
            starts.append(index)
    ends = starts[1:] + [len(signs)]
    result = []
    for start, end in zip(starts, ends):
        if end <= start:
            continue
        phase_delta = float(phase[end] - phase[start])
        turns = phase_delta / TWO_PI
        voltage_area = area_turns(
            time_ps[start : end + 1] * 1e-12,
            voltage[start : end + 1],
        )
        result.append(
            {
                "start_ps": float(time_ps[start]),
                "end_ps": float(time_ps[end]),
                "direction": int(signs[start]),
                "phase_delta_turns": turns,
                "abs_turns": abs(turns),
                "same_jj_voltage_area_turns": voltage_area,
                "area_minus_phase_turns": voltage_area - turns,
                "complete_phase_area_consistent": bool(
                    abs(turns) >= 1.0
                    and abs(voltage_area) >= 0.8
                    and abs(voltage_area - turns)
                    <= max(0.05, 0.10 * abs(turns))
                ),
            }
        )
    return result


def phase_metrics(
    data: dict[str, np.ndarray], phase_name: str, voltage_name: str
) -> dict[str, object]:
    time_ps = data["time_ps"]
    phase = np.unwrap(data[phase_name])
    result: dict[str, object] = {
        "full_range_turns": float((np.max(phase) - np.min(phase)) / TWO_PI),
        "full_endpoint_turns": float((phase[-1] - phase[0]) / TWO_PI),
        "windows": {},
    }
    for label, bounds in WINDOWS.items():
        m = mask(time_ps, bounds)
        local_phase = phase[m]
        local_voltage = data[voltage_name][m]
        if len(local_phase) < 2:
            result["windows"][label] = {"valid": False}
            continue
        segments = monotonic_segments(
            time_ps[m], data[phase_name][m], local_voltage
        )
        segments.sort(key=lambda item: item["abs_turns"], reverse=True)
        result["windows"][label] = {
            "valid": True,
            "range_turns": float((np.max(local_phase) - np.min(local_phase)) / TWO_PI),
            "endpoint_turns": float((local_phase[-1] - local_phase[0]) / TWO_PI),
            "voltage_area_turns": area_turns(
                data["time_s"][m], local_voltage
            ),
            "largest_monotonic_segment": segments[0] if segments else None,
            "complete_segments": [
                item for item in segments if item["complete_phase_area_consistent"]
            ],
        }
    result["complete_segments_full"] = result["windows"]["full"][
        "complete_segments"
    ]
    return result


def scalar_window(data: dict[str, np.ndarray], name: str, bounds: tuple[float, float]) -> dict[str, float]:
    values = data[name][mask(data["time_ps"], bounds)]
    return {
        "min": float(np.min(values)),
        "max": float(np.max(values)),
        "p2p": float(np.max(values) - np.min(values)),
        "median": float(np.median(values)),
    }


def waveform_features(
    data: dict[str, np.ndarray], name: str, bounds: tuple[float, float]
) -> dict[str, float]:
    m = mask(data["time_ps"], bounds)
    t = data["time_s"][m]
    values = data[name][m]
    positive = np.maximum(values, 0.0)
    negative = np.minimum(values, 0.0)
    threshold = 0.10 * max(abs(float(np.max(values))), abs(float(np.min(values))))
    active = np.abs(values) >= threshold if threshold else np.zeros_like(values, dtype=bool)
    return {
        "min": float(np.min(values)),
        "max": float(np.max(values)),
        "p2p": float(np.max(values) - np.min(values)),
        "signed_area_uA_ps": float(np.trapezoid(values, t) * 1e18),
        "positive_area_uA_ps": float(np.trapezoid(positive, t) * 1e18),
        "negative_area_uA_ps": float(np.trapezoid(negative, t) * 1e18),
        "duration_abs_ge_10pct_peak_ps": float(
            np.sum(np.diff(data["time_ps"][m])[active[:-1]])
        )
        if len(values) > 1
        else 0.0,
    }


def current_series_metrics(data: dict[str, np.ndarray]) -> dict[str, object]:
    time_ps = data["time_ps"]
    names = [f"I(B_LD{i})" for i in range(1, 13)]
    result = {}
    for label, bounds in WINDOWS.items():
        m = mask(time_ps, bounds)
        matrix = np.vstack([data[name][m] for name in names])
        spread = np.max(matrix, axis=0) - np.min(matrix, axis=0)
        result[label] = {
            "current_min_uA": float(np.min(matrix) * 1e6),
            "current_max_uA": float(np.max(matrix) * 1e6),
            "current_p2p_uA": float((np.max(matrix) - np.min(matrix)) * 1e6),
            "max_instantaneous_series_spread_uA": float(np.max(spread) * 1e6),
            "median_instantaneous_series_spread_uA": float(np.median(spread) * 1e6),
        }
    return result


def guard_metrics(
    loaded: dict[str, np.ndarray], baseline: dict[str, np.ndarray]
) -> dict[str, object]:
    result = {}
    for name in STORAGE + SOURCE:
        item = {"loaded": {}, "canonical": {}, "loaded_minus_canonical": {}}
        for label, bounds in WINDOWS.items():
            lv = scalar_window(loaded, name, bounds)
            bv = scalar_window(baseline, name, bounds)
            item["loaded"][label] = lv
            item["canonical"][label] = bv
            item["loaded_minus_canonical"][label] = {
                key: lv[key] - bv[key] for key in ("min", "max", "p2p", "median")
            }
        result[name] = item
    return result


def one_case(case_id: str, baseline_id: str) -> dict[str, object]:
    loaded_path = RAW / case_id / "run-01.csv"
    baseline_path = BASE / baseline_id / "run-01.csv"
    loaded = load_csv(loaded_path)
    baseline = load_csv(baseline_path)
    required = set(STORAGE + SOURCE + ("V(NJSL11)",))
    required.update(
        f"{kind}(B_LD{i})"
        for i in range(1, 13)
        for kind in ("P", "V", "I")
    )
    missing = sorted(required - loaded.keys())
    if missing:
        raise ValueError(f"{case_id}: missing columns: {missing}")

    jsl_phase = {}
    for i in range(1, 13):
        jj = f"B_LD{i}"
        jsl_phase[jj] = phase_metrics(loaded, f"P({jj})", f"V({jj})")

    source_features = {
        name: waveform_features(loaded, name, WINDOWS["read_activity"])
        for name in SOURCE
    }
    source_baseline_features = {
        name: waveform_features(baseline, name, WINDOWS["read_activity"])
        for name in SOURCE
    }
    stack_current = current_series_metrics(loaded)
    guard = guard_metrics(loaded, baseline)
    read_complete = [
        jj
        for jj, item in jsl_phase.items()
        if item["windows"]["read_activity"]["complete_segments"]
    ]
    full_complete = [
        jj for jj, item in jsl_phase.items() if item["complete_segments_full"]
    ]
    return {
        "case": case_id,
        "baseline_case": baseline_id,
        "raw_sha256": sha256(loaded_path),
        "baseline_sha256": sha256(baseline_path),
        "rows": len(loaded["time_s"]),
        "time_start_ps": float(loaded["time_ps"][0]),
        "time_end_ps": float(loaded["time_ps"][-1]),
        "jsl_phase": jsl_phase,
        "source_features_read_activity": source_features,
        "source_baseline_features_read_activity": source_baseline_features,
        "stack_current": stack_current,
        "guards": guard,
        "complete_jjs_read_activity": read_complete,
        "complete_jjs_full": full_complete,
        "all_jsl_non_switching": not full_complete,
    }


def main() -> None:
    cases = {
        case_id: one_case(case_id, baseline_id)
        for case_id, baseline_id in CASES.items()
    }
    jsl_table = []
    for case_id, case in cases.items():
        for jj, item in case["jsl_phase"].items():
            activity = item["windows"]["read_activity"]
            largest = activity["largest_monotonic_segment"] or {}
            current = case["stack_current"]["read_activity"]
            jsl_table.append(
                {
                    "case": case_id,
                    "jj": jj,
                    "activity_range_turns": activity["range_turns"],
                    "largest_segment_turns": largest.get("phase_delta_turns", 0.0),
                    "same_segment_area_turns": largest.get(
                        "same_jj_voltage_area_turns", 0.0
                    ),
                    "area_minus_phase_turns": largest.get(
                        "area_minus_phase_turns", 0.0
                    ),
                    "complete": bool(
                        activity["complete_segments"]
                    ),
                    "stack_current_min_uA": current["current_min_uA"],
                    "stack_current_max_uA": current["current_max_uA"],
                }
            )

    out_json = ROOT / "analysis" / "metrics.json"
    out_csv = ROOT / "analysis" / "jsl-summary.csv"
    out_json.write_text(
        json.dumps(
            {
                "document_type": "paper_sl_l0_direct_phase_area_audit",
                "phi0_wb": PHI0,
                "windows_ps": WINDOWS,
                "cases": cases,
                "jsl_summary": jsl_table,
                "method": "raw JoSIM P radians, continuous unwrap, same-JJ same-segment voltage area using actual CSV time; no fast_events",
            },
            indent=2,
        )
        + "\n"
    )
    with out_csv.open("w", newline="") as handle:
        fields = list(jsl_table[0].keys())
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(jsl_table)

    print("case,jjs_with_read_complete,maximum_read_activity_range_turns,maximum_read_segment_turns,maximum_read_segment_area_turns")
    for case_id, item in cases.items():
        ranges = [v["windows"]["read_activity"]["range_turns"] for v in item["jsl_phase"].values()]
        segments = [
            (v["windows"]["read_activity"]["largest_monotonic_segment"] or {})
            for v in item["jsl_phase"].values()
        ]
        max_segment = max((abs(v.get("phase_delta_turns", 0.0)) for v in segments), default=0.0)
        max_area = max((abs(v.get("same_jj_voltage_area_turns", 0.0)) for v in segments), default=0.0)
        print(f"{case_id},{','.join(item['complete_jjs_read_activity']) or 'none'},{max(ranges):.9g},{max_segment:.9g},{max_area:.9g}")


if __name__ == "__main__":
    main()
