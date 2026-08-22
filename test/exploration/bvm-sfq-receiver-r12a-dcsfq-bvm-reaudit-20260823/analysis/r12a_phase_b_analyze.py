#!/usr/bin/env python3
"""Evidence extraction for the gated R12-A canonical cascade.

No legacy fast-event counter is used.  Every phase/area value is computed from
the same raw JJ P/V columns and the same time interval.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path

import numpy as np


PHI0 = 2.067833848e-15
ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[2]
RAW = ROOT / "raw"
ANALYSIS = ROOT / "analysis"

WINDOWS = {"pre": (85.0, 94.0), "activity": (94.0, 130.0), "post": (130.0, 165.0)}
CASES = {
    "read1": {
        "raw": RAW / "phase-b-read1/run-01.csv",
        "canonical": REPO / "test/exploration/bvm-internal-readout-20260819/raw/pos-read-single/run-01.csv",
    },
    "read0": {
        "raw": RAW / "phase-b-read0/run-01.csv",
        "canonical": REPO / "test/exploration/bvm-internal-readout-20260819/raw/neg-init-pos-read/run-01.csv",
    },
    "logical1-read0-control": {
        "raw": RAW / "phase-b-logical1-read0-control/run-01.csv",
        "canonical": REPO / "test/exploration/bvm-internal-readout-20260819/raw/pos-control/run-01.csv",
    },
    "logical0-read0-control": {
        "raw": RAW / "phase-b-logical0-read0-control/run-01.csv",
        "canonical": REPO / "test/exploration/bvm-internal-readout-20260819/raw/neg-control/run-01.csv",
    },
}

CONVERTER_PHASE = [
    "P(B1|XCONV)",
    "P(B2|XCONV)",
    "P(B3|XCONV)",
]
JTL_PHASE = [
    "P(B1|XJTL1)",
    "P(B2|XJTL1)",
    "P(B1|XJTL2)",
    "P(B2|XJTL2)",
]
BVM_PHASE = [
    "P(B_JM1|XBVM1)",
    "P(B_JM2|XBVM1)",
    "P(B_JS1|XBVM1)",
    "P(B_JS2|XBVM1)",
]
PHASE_COLUMNS = CONVERTER_PHASE + JTL_PHASE + BVM_PHASE
CURRENT_COLUMNS = [
    "I(B1|XCONV)",
    "I(B2|XCONV)",
    "I(B3|XCONV)",
    "I(L1|XCONV)",
    "I(L2|XCONV)",
    "I(L3|XCONV)",
    "I(L4|XCONV)",
    "I(L5|XCONV)",
    "I(L6|XCONV)",
    "I(LB1|XCONV)",
    "I(LB2|XCONV)",
    "I(IB1|XCONV)",
    "I(IB2|XCONV)",
    "I(RB1|XCONV)",
    "I(RB2|XCONV)",
    "I(RB3|XCONV)",
    "I(B1|XJTL1)",
    "I(B2|XJTL1)",
    "I(B1|XJTL2)",
    "I(B2|XJTL2)",
    "I(R_TERM)",
]
GUARD_COLUMNS = [
    "V(SL1)",
    "V(N6|XBVM1)",
    "I(L_SL|XBVM1)",
    "I(L_PSL|XBVM1)",
    "P(B_JM1|XBVM1)",
    "P(B_JM2|XBVM1)",
    "P(B_JS1|XBVM1)",
    "P(B_JS2|XBVM1)",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def load_csv(path: Path) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    with path.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError(f"empty CSV: {path}")
    fields = list(rows[0].keys())
    time_ps = np.asarray([float(row["time"]) * 1e12 for row in rows], dtype=float)
    arrays = {
        field: np.asarray([float(row[field]) for row in rows], dtype=float)
        for field in fields
        if field != "time"
    }
    if not np.all(np.isfinite(time_ps)) or not np.all(np.diff(time_ps) > 0):
        raise ValueError(f"invalid time axis: {path}")
    if not all(np.all(np.isfinite(values)) for values in arrays.values()):
        raise ValueError(f"non-finite data: {path}")
    return time_ps, arrays


def mask(time_ps: np.ndarray, window: tuple[float, float]) -> np.ndarray:
    return (time_ps >= window[0]) & (time_ps < window[1])


def median(values: np.ndarray) -> float:
    return float(np.median(values))


def p2p(values: np.ndarray) -> float:
    return float(np.max(values) - np.min(values))


def rms(values: np.ndarray) -> float:
    return float(np.sqrt(np.mean(values * values)))


def integrate(time_ps: np.ndarray, values: np.ndarray) -> float:
    return float(np.trapezoid(values, time_ps * 1e-12) / PHI0)


def turns(delta_rad: float) -> float:
    return float(delta_rad / (2.0 * math.pi))


def largest_monotonic_segment(
    time_ps: np.ndarray, phase: np.ndarray, voltage: np.ndarray, active: np.ndarray
) -> dict[str, object]:
    """Return the largest descriptive monotonic segment, not an event count."""
    indices = np.flatnonzero(active)
    if len(indices) < 2:
        return {
            "direction": "none",
            "start_ps": None,
            "end_ps": None,
            "turns": 0.0,
            "voltage_area_turns": 0.0,
            "phase_area_residual_turns": 0.0,
        }
    delta = np.diff(phase[indices])
    best: tuple[float, str, int, int, float] | None = None
    for sign, direction in ((1.0, "positive"), (-1.0, "negative")):
        good = sign * delta >= 0.0
        cursor = 0
        while cursor < len(good):
            while cursor < len(good) and not good[cursor]:
                cursor += 1
            if cursor >= len(good):
                break
            end_cursor = cursor
            while end_cursor + 1 < len(good) and good[end_cursor + 1]:
                end_cursor += 1
            start = indices[cursor]
            end = indices[end_cursor + 1]
            phase_delta = float(phase[end] - phase[start])
            magnitude = sign * phase_delta
            candidate = (magnitude, direction, start, end, phase_delta)
            if best is None or candidate[0] > best[0]:
                best = candidate
            cursor = end_cursor + 1
    if best is None:
        return {
            "direction": "none",
            "start_ps": None,
            "end_ps": None,
            "turns": 0.0,
            "voltage_area_turns": 0.0,
            "phase_area_residual_turns": 0.0,
        }
    _, direction, start, end, phase_delta = best
    area = integrate(time_ps[start : end + 1], voltage[start : end + 1])
    return {
        "direction": direction,
        "start_ps": float(time_ps[start]),
        "end_ps": float(time_ps[end]),
        "turns": turns(phase_delta),
        "voltage_area_turns": area,
        "phase_area_residual_turns": float(area - turns(phase_delta)),
    }


def phase_metrics(time_ps, arrays, phase_col: str, voltage_col: str) -> dict[str, object]:
    phase = np.unwrap(arrays[phase_col])
    active = mask(time_ps, WINDOWS["activity"])
    pre = mask(time_ps, WINDOWS["pre"])
    post = mask(time_ps, WINDOWS["post"])
    start = np.flatnonzero(active)[0]
    end = np.flatnonzero(active)[-1]
    segment = largest_monotonic_segment(time_ps, phase, arrays[voltage_col], active)
    return {
        "pre_phase_rad": median(phase[pre]),
        "post_phase_rad": median(phase[post]),
        "pre_to_post_turns": turns(median(phase[post]) - median(phase[pre])),
        "activity_range_turns": turns(np.max(phase[active]) - np.min(phase[active])),
        "activity_window_phase_turns": turns(phase[end] - phase[start]),
        "activity_window_v_area_turns": integrate(
            time_ps[start : end + 1], arrays[voltage_col][start : end + 1]
        ),
        "post_phase_p2p_turns": turns(p2p(phase[post])),
        "post_voltage_rms_V": rms(arrays[voltage_col][post]),
        "largest_monotonic_segment": segment,
    }


def window_metrics(time_ps, arrays, columns: list[str]) -> dict[str, object]:
    result: dict[str, object] = {}
    for column in columns:
        if column not in arrays:
            continue
        result[column] = {}
        for label, bounds in WINDOWS.items():
            values = arrays[column][mask(time_ps, bounds)]
            result[column][label] = {
                "median": median(values),
                "min": float(np.min(values)),
                "max": float(np.max(values)),
                "p2p": p2p(values),
                "rms": rms(values),
            }
    return result


def guard_delta(time_ps, arrays, canonical_time, canonical_arrays) -> dict[str, object]:
    result: dict[str, object] = {}
    for column in GUARD_COLUMNS:
        direct = arrays[column][mask(time_ps, WINDOWS["post"])]
        canonical = canonical_arrays[column][mask(canonical_time, WINDOWS["post"])]
        direct_median = median(direct)
        canonical_median = median(canonical)
        direct_p2p = p2p(direct)
        canonical_p2p = p2p(canonical)
        result[column] = {
            "direct_post_median": direct_median,
            "canonical_post_median": canonical_median,
            "post_median_delta": direct_median - canonical_median,
            "direct_post_p2p": direct_p2p,
            "canonical_post_p2p": canonical_p2p,
            "post_p2p_ratio_to_canonical": direct_p2p / canonical_p2p
            if canonical_p2p
            else None,
        }
    return result


def analyze_case(name: str, spec: dict[str, Path]) -> dict[str, object]:
    time_ps, arrays = load_csv(spec["raw"])
    required = []
    for phase_col in CONVERTER_PHASE + JTL_PHASE + BVM_PHASE:
        required += [phase_col, phase_col.replace("P(", "V(", 1)]
    required += CURRENT_COLUMNS + ["V(SL1)", "V(CONV_Q)", "V(JTL_MID)", "V(JTL_OUT)"]
    required += ["I(L_SL|XBVM1)", "I(L_PSL|XBVM1)", "V(N6|XBVM1)"]
    missing = sorted(set(column for column in required if column not in arrays))
    if missing:
        raise ValueError(f"{name}: missing columns: {missing}")

    converter = {
        phase: phase_metrics(time_ps, arrays, phase, phase.replace("P(", "V(", 1))
        for phase in CONVERTER_PHASE
    }
    jtl = {
        phase: phase_metrics(time_ps, arrays, phase, phase.replace("P(", "V(", 1))
        for phase in JTL_PHASE
    }
    bvm = {
        phase: phase_metrics(time_ps, arrays, phase, phase.replace("P(", "V(", 1))
        for phase in BVM_PHASE
    }
    canonical_time, canonical_arrays = load_csv(spec["canonical"])
    return {
        "raw_path": str(spec["raw"].relative_to(ROOT)),
        "raw_sha256": sha256(spec["raw"]),
        "canonical_raw_path": str(spec["canonical"].relative_to(REPO)),
        "canonical_raw_sha256": sha256(spec["canonical"]),
        "rows": int(len(time_ps)),
        "time_start_ps": float(time_ps[0]),
        "time_end_ps": float(time_ps[-1]),
        "dt_ps_median": float(np.median(np.diff(time_ps))),
        "windows_ps": WINDOWS,
        "converter": converter,
        "jtl": jtl,
        "bvm": bvm,
        "currents": window_metrics(time_ps, arrays, CURRENT_COLUMNS),
        "signals": window_metrics(
            time_ps,
            arrays,
            [
                "V(SL1)",
                "V(N6|XBVM1)",
                "I(L_SL|XBVM1)",
                "I(L_PSL|XBVM1)",
                "V(CONV_Q)",
                "V(JTL_MID)",
                "V(JTL_OUT)",
                "I(R_TERM)",
            ],
        ),
        "guard_delta_vs_canonical": guard_delta(
            time_ps, arrays, canonical_time, canonical_arrays
        ),
    }


def fmt(value, digits=7):
    if value is None or (isinstance(value, float) and not math.isfinite(value)):
        return "n/a"
    return f"{value:.{digits}g}"


def main() -> None:
    results = {name: analyze_case(name, spec) for name, spec in CASES.items()}
    payload = {
        "experiment": "R12-A",
        "phase": "B",
        "head_before_experiment": "ca610ce73bf78ddc99edf3f03197be1968bfe8b2",
        "phi0_Wb": PHI0,
        "results": results,
    }
    (ANALYSIS / "phase-b-metrics.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n"
    )

    print("case,stage,junction,activity_range_turns,largest_segment_turns,segment_area_turns,post_p2p_turns")
    for name, result in results.items():
        for stage, table in (("converter", result["converter"]), ("jtl", result["jtl"])):
            for junction, metrics in table.items():
                segment = metrics["largest_monotonic_segment"]
                print(
                    f"{name},{stage},{junction},"
                    f"{fmt(metrics['activity_range_turns'])},"
                    f"{fmt(segment['turns'])},"
                    f"{fmt(segment['voltage_area_turns'])},"
                    f"{fmt(metrics['post_phase_p2p_turns'])}"
                )
    print("wrote analysis/phase-b-metrics.json")


if __name__ == "__main__":
    main()
