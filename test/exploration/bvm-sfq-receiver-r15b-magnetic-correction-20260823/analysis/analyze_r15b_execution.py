#!/usr/bin/env python3
"""R15-B execution analysis.

This deliberately does not use scripts/sfq_metrics.py.  Local event evidence is
computed from the same junction, same monotonic segment, and same-JJ voltage
area.  The source comparison uses the accepted no-receiver BVM raw fixtures.
"""

from __future__ import annotations

import csv
import json
import math
import subprocess
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
PHI0 = 2.067833848e-15
TWOPI = 2.0 * math.pi
WINDOWS = {
    "settled": (80.0, 90.0),
    "activity": (94.0, 130.0),
    "post": (150.0, 170.0),
}

CASES = {
    "logical1-read": {"state": 1, "read": 1, "baseline": "pos-read-single"},
    "logical0-read": {"state": 0, "read": 1, "baseline": "neg-read-single"},
    "logical1-read0-control": {"state": 1, "read": 0, "baseline": "pos-control"},
    "logical0-read0-control": {"state": 0, "read": 0, "baseline": "neg-control"},
}

BASELINE_ROOT = Path("/home/howard/JoSIM/test/exploration/bvm-internal-readout-20260819/raw")

PHASE_PAIRS = {
    "B_DET": ("P(B_DET|XAFQ)", "V(B_DET|XAFQ)"),
    "B_SET": ("P(B_SET|XAFQ)", "V(B_SET|XAFQ)"),
    "B_Q": ("P(B_Q|XAFQ)", "V(B_Q|XAFQ)"),
    "B_OUT": ("P(B_OUT|XAFQ)", "V(B_OUT|XAFQ)"),
    "B1": ("P(B1|XDCS)", "V(B1|XDCS)"),
    "B2": ("P(B2|XDCS)", "V(B2|XDCS)"),
    "B3": ("P(B3|XDCS)", "V(B3|XDCS)"),
}

CURRENT_COLUMNS = [
    "I(B_DET|XAFQ)",
    "I(B_SET|XAFQ)",
    "I(B_Q|XAFQ)",
    "I(B_OUT|XAFQ)",
    "I(L_TX|XAFQ)",
    "I(L_S|XAFQ)",
    "I(L_Q|XAFQ)",
    "I(L_FQ|XAFQ)",
    "I(L_FO|XAFQ)",
    "I(L_CTL|XAFQ)",
    "I(L_INJ|XAFQ)",
    "I(R_IN|XAFQ)",
    "I(R_Q|XAFQ)",
    "I(R_F|XAFQ)",
    "I(R_SRC|XAFQ)",
    "I(I_DET|XAFQ)",
    "I(I_SET|XAFQ)",
    "I(I_OUT|XAFQ)",
    "I(L1|XDCS)",
    "I(B1|XDCS)",
    "I(B2|XDCS)",
    "I(B3|XDCS)",
    "I(R_DCS_LOAD)",
]

VOLTAGE_COLUMNS = [
    "V(DCS_A)",
    "V(DCS_Q)",
    "V(SL1)",
    "V(N6|XBVM1)",
]

SOURCE_COLUMNS = [
    "V(SL1)",
    "V(N6|XBVM1)",
    "I(L_SL|XBVM1)",
    "P(B_JM1|XBVM1)",
    "P(B_JM2|XBVM1)",
    "P(B_JS1|XBVM1)",
    "P(B_JS2|XBVM1)",
    "V(B_JM1|XBVM1)",
    "V(B_JM2|XBVM1)",
    "V(B_JS1|XBVM1)",
    "V(B_JS2|XBVM1)",
]


def load_csv(path: Path) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    with path.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError(f"empty CSV: {path}")
    columns = list(rows[0])
    t_ps = np.asarray([float(row["time"]) for row in rows], dtype=float) * 1e12
    data = {
        column: np.asarray([float(row[column]) for row in rows], dtype=float)
        for column in columns
        if column != "time"
    }
    return t_ps, data


def mask(t_ps: np.ndarray, window: tuple[float, float]) -> np.ndarray:
    return (t_ps >= window[0]) & (t_ps < window[1])


def p2p(values: np.ndarray) -> float:
    return float(np.max(values) - np.min(values))


def stats(values: np.ndarray, scale: float = 1.0) -> dict[str, float]:
    scaled = values * scale
    return {
        "min": float(np.min(scaled)),
        "max": float(np.max(scaled)),
        "p2p": float(np.ptp(scaled)),
        "mean": float(np.mean(scaled)),
        "median": float(np.median(scaled)),
    }


def monotonic_segments(t_ps: np.ndarray, phase: np.ndarray, window: tuple[float, float]) -> list[dict[str, float]]:
    m = mask(t_ps, window)
    indices = np.flatnonzero(m)
    if len(indices) < 2:
        return []
    unwrapped = np.unwrap(phase[m])
    derivative = np.diff(unwrapped)
    signs = np.sign(derivative)
    nonzero = np.flatnonzero(signs)
    if len(nonzero) == 0:
        return []
    # A zero finite-difference sample inherits the previous non-zero direction.
    for pos in range(1, len(signs)):
        if signs[pos] == 0:
            signs[pos] = signs[pos - 1]
    if signs[0] == 0:
        signs[0] = 1.0
        for pos in range(1, len(signs)):
            if signs[pos] == 0:
                signs[pos] = signs[pos - 1]
    starts = [0]
    for pos in range(1, len(signs)):
        if signs[pos] != signs[pos - 1]:
            starts.append(pos)
    segments: list[dict[str, float]] = []
    for start, next_start in zip(starts, starts[1:] + [len(unwrapped) - 1]):
        end = next_start
        if end <= start:
            continue
        global_indices = indices[start : end + 1]
        phase_delta_rad = float(unwrapped[end] - unwrapped[start])
        area_turns = float(
            np.trapezoid(
                # The paired voltage column is added by phase_metrics().
                np.zeros(end - start + 1),
                t_ps[global_indices] * 1e-12,
            )
        )
        segments.append(
            {
                "start_index": int(global_indices[0]),
                "end_index": int(global_indices[-1]),
                "start_ps": float(t_ps[global_indices[0]]),
                "end_ps": float(t_ps[global_indices[-1]]),
                "phase_delta_turns": phase_delta_rad / TWOPI,
                "phase_abs_turns": abs(phase_delta_rad) / TWOPI,
                "_area_placeholder": area_turns,
            }
        )
    return sorted(segments, key=lambda item: item["phase_abs_turns"], reverse=True)


def phase_metrics(t_ps: np.ndarray, data: dict[str, np.ndarray], phase_col: str, voltage_col: str) -> dict[str, object]:
    phase = data[phase_col]
    voltage = data[voltage_col]
    result: dict[str, object] = {}
    for label, window in WINDOWS.items():
        m = mask(t_ps, window)
        unwrapped = np.unwrap(phase[m])
        result[f"{label}_activity_range_turns"] = float(np.ptp(unwrapped) / TWOPI)
        result[f"{label}_phase_start_rad"] = float(unwrapped[0])
        result[f"{label}_phase_end_rad"] = float(unwrapped[-1])
        result[f"{label}_voltage_uV"] = stats(voltage[m], 1e6)
        segments = monotonic_segments(t_ps, phase, window)
        if segments:
            best = dict(segments[0])
            indices = np.arange(best["start_index"], best["end_index"] + 1)
            area_turns = float(np.trapezoid(voltage[indices], t_ps[indices] * 1e-12) / PHI0)
            best.pop("_area_placeholder", None)
            best["same_segment_voltage_area_turns"] = area_turns
            best["phase_area_residual_turns"] = area_turns - best["phase_delta_turns"]
            best["complete_candidate"] = bool(
                best["phase_abs_turns"] >= 1.0
                and abs(best["phase_area_residual_turns"])
                <= max(0.02, 0.05 * best["phase_abs_turns"])
            )
            result[f"{label}_largest_monotonic_segment"] = best
            result[f"{label}_complete_candidate_count"] = int(
                sum(
                    abs(item["phase_delta_turns"]) >= 1.0
                    for item in segments
                )
            )
        else:
            result[f"{label}_largest_monotonic_segment"] = None
            result[f"{label}_complete_candidate_count"] = 0
    return result


def current_window_metrics(t_ps: np.ndarray, data: dict[str, np.ndarray], column: str) -> dict[str, object]:
    result: dict[str, object] = {}
    values = data[column]
    for label, window in WINDOWS.items():
        m = mask(t_ps, window)
        result[label] = stats(values[m], 1e6)
    return result


def dcsfq_input_metrics(t_ps: np.ndarray, data: dict[str, np.ndarray]) -> dict[str, object]:
    current = data["I(L1|XDCS)"]
    m = mask(t_ps, WINDOWS["activity"])
    t = t_ps[m]
    i_ua = current[m] * 1e6
    dt_ps = np.diff(t)
    positive = i_ua[:-1] > 0.0
    positive_area = float(np.sum(np.maximum(i_ua[:-1], 0.0) * dt_ps))
    negative_area = float(np.sum(np.minimum(i_ua[:-1], 0.0) * dt_ps))
    signed_area = positive_area + negative_area
    pos_indices = np.flatnonzero(i_ua > 0.0)
    above_10 = np.flatnonzero(i_ua > 10.0)
    return {
        "positive_peak_uA": float(np.max(i_ua)),
        "negative_peak_uA": float(np.min(i_ua)),
        "signed_area_uA_ps": signed_area,
        "positive_area_uA_ps": positive_area,
        "negative_area_uA_ps": negative_area,
        "favorable_positive_occupancy_ps": float(np.sum(dt_ps[positive])),
        "favorable_positive_span_ps": (
            float(t[pos_indices[-1]] - t[pos_indices[0]]) if len(pos_indices) else 0.0
        ),
        "positive_over_10uA_span_ps": (
            float(t[above_10[-1]] - t[above_10[0]]) if len(above_10) else 0.0
        ),
        "dcs_a_voltage_uV": stats(data["V(DCS_A)"][m], 1e6),
        "steering_current_uA": {
            column: stats(data[column][m], 1e6)
            for column in [
                "I(L_INJ|XAFQ)",
                "I(R_SRC|XAFQ)",
                "I(L_CTL|XAFQ)",
                "I(L_FQ|XAFQ)",
                "I(L_FO|XAFQ)",
            ]
        },
    }


def source_metrics(t_ps: np.ndarray, data: dict[str, np.ndarray], baseline_t: np.ndarray, baseline: dict[str, np.ndarray]) -> dict[str, object]:
    result: dict[str, object] = {}
    for column in SOURCE_COLUMNS:
        entry: dict[str, object] = {}
        for label, window in WINDOWS.items():
            m = mask(t_ps, window)
            bm = mask(baseline_t, window)
            values = data[column][m]
            base = baseline[column][bm]
            scale = 1e6 if column.startswith("V(") else (1.0 if column.startswith("P(") else 1e6)
            entry[label] = {
                "receiver": stats(values, scale),
                "canonical_no_receiver": stats(base, scale),
                "p2p_difference_scaled": float((p2p(values) - p2p(base)) * scale),
                "rms_waveform_difference_scaled": float(np.sqrt(np.mean((values - base) ** 2)) * scale),
            }
        result[column] = entry
    return result


def artifact_metrics(path: Path, t_ps: np.ndarray, data: dict[str, np.ndarray]) -> dict[str, object]:
    exit_path = ROOT / "logs" / f"{path.stem}.exitcode.txt"
    exit_code = int(exit_path.read_text().strip()) if exit_path.exists() else None
    finite = bool(np.all(np.isfinite(t_ps)) and all(np.all(np.isfinite(v)) for v in data.values()))
    dt = np.diff(t_ps)
    return {
        "path": str(path.relative_to(ROOT)),
        "bytes": path.stat().st_size,
        "exit_code": exit_code,
        "rows": int(len(t_ps)),
        "start_ps": float(t_ps[0]),
        "end_ps": float(t_ps[-1]),
        "dt_median_ps": float(np.median(dt)),
        "dt_max_ps": float(np.max(dt)),
        "strictly_increasing_time": bool(np.all(dt > 0.0)),
        "finite": finite,
        "required_columns_present": all(
            column in data
            for column in tuple(column for pair in PHASE_PAIRS.values() for column in pair)
            + tuple(CURRENT_COLUMNS)
        ),
    }


def main() -> None:
    all_metrics: dict[str, object] = {
        "experiment": "R15-B",
        "analysis": "same-junction continuous phase and same-segment voltage area",
        "phi0_Wb": PHI0,
        "windows_ps": WINDOWS,
        "references_uA": {
            "R1a_passive_secondary": 5.564,
            "R12_68p4_controlled_no_event": 68.4,
            "R13_110p2_actual_read1_subthreshold": 110.2,
            "R12_300_controlled_one_event_reference": 300.0,
        },
        "cases": {},
    }
    summary_rows: list[dict[str, object]] = []
    for case, info in CASES.items():
        path = ROOT / "raw" / f"{case}.csv"
        t_ps, data = load_csv(path)
        baseline_path = BASELINE_ROOT / info["baseline"] / "run-01.csv"
        baseline_t, baseline_data = load_csv(baseline_path)
        phases = {
            name: phase_metrics(t_ps, data, pcol, vcol)
            for name, (pcol, vcol) in PHASE_PAIRS.items()
        }
        currents = {
            column: current_window_metrics(t_ps, data, column)
            for column in CURRENT_COLUMNS
            if column in data
        }
        all_metrics["cases"][case] = {
            "logical_state": info["state"],
            "read": info["read"],
            "artifact": artifact_metrics(path, t_ps, data),
            "phases": phases,
            "currents": currents,
            "dcsfq_input": dcsfq_input_metrics(t_ps, data),
            "source_guards": source_metrics(t_ps, data, baseline_t, baseline_data),
        }
        detector = phases["B_DET"]["activity_largest_monotonic_segment"]
        b3 = phases["B3"]["activity_largest_monotonic_segment"]
        summary_rows.append(
            {
                "case": case,
                "B_DET_activity_range_turns": phases["B_DET"]["activity_activity_range_turns"],
                "B_DET_largest_segment_turns": detector["phase_delta_turns"] if detector else None,
                "B_DET_area_turns": detector["same_segment_voltage_area_turns"] if detector else None,
                "B_SET_largest_segment_turns": phases["B_SET"]["activity_largest_monotonic_segment"]["phase_delta_turns"],
                "B_Q_largest_segment_turns": phases["B_Q"]["activity_largest_monotonic_segment"]["phase_delta_turns"],
                "B_OUT_largest_segment_turns": phases["B_OUT"]["activity_largest_monotonic_segment"]["phase_delta_turns"],
                "B3_largest_segment_turns": b3["phase_delta_turns"] if b3 else None,
                "B3_area_turns": b3["same_segment_voltage_area_turns"] if b3 else None,
                "L1_positive_peak_uA": all_metrics["cases"][case]["dcsfq_input"]["positive_peak_uA"],
                "L1_negative_peak_uA": all_metrics["cases"][case]["dcsfq_input"]["negative_peak_uA"],
                "L1_signed_area_uA_ps": all_metrics["cases"][case]["dcsfq_input"]["signed_area_uA_ps"],
            }
        )

    read1 = all_metrics["cases"]["logical1-read"]
    read0 = all_metrics["cases"]["logical0-read"]
    controls = [
        all_metrics["cases"]["logical1-read0-control"],
        all_metrics["cases"]["logical0-read0-control"],
    ]
    detector_read1 = read1["phases"]["B_DET"]["activity_largest_monotonic_segment"]
    detector_read0 = read0["phases"]["B_DET"]["activity_largest_monotonic_segment"]
    active_names = ["B_SET", "B_Q", "B_OUT"]
    active_read1_complete = any(
        read1["phases"][name]["activity_complete_candidate_count"] > 0 for name in active_names
    )
    active_read0_complete = any(
        read0["phases"][name]["activity_complete_candidate_count"] > 0 for name in active_names
    )
    active_control_complete = any(
        control["phases"][name]["activity_complete_candidate_count"] > 0
        for control in controls
        for name in active_names
    )
    dcsfq_read1_complete = read1["phases"]["B3"]["activity_complete_candidate_count"] > 0
    dcsfq_read0_or_control_complete = (
        read0["phases"]["B3"]["activity_complete_candidate_count"] > 0
        or any(control["phases"]["B3"]["activity_complete_candidate_count"] > 0 for control in controls)
    )
    all_metrics["stage_verdict"] = {
        "stage1_detector_preserved": bool(
            detector_read1
            and abs(detector_read1["phase_delta_turns"]) >= 1.0
            and detector_read0
            and abs(detector_read0["phase_delta_turns"]) < 1.0
            and all(
                control["phases"]["B_DET"]["activity_complete_candidate_count"] == 0
                for control in controls
            )
        ),
        "stage2_active_state_compression": bool(
            active_read1_complete and not active_read0_complete and not active_control_complete
        ),
        "stage3_active_gain_established": bool(
            read1["dcsfq_input"]["positive_peak_uA"] > 5.564
            and read1["dcsfq_input"]["positive_peak_uA"] > read0["dcsfq_input"]["positive_peak_uA"]
        ),
        "stage4_dcsfq_one_shot": bool(
            dcsfq_read1_complete and not dcsfq_read0_or_control_complete
        ),
        "active_read1_complete": active_read1_complete,
        "active_read0_complete": active_read0_complete,
        "active_control_complete": active_control_complete,
        "dcsfq_read1_complete": dcsfq_read1_complete,
        "dcsfq_read0_or_control_complete": dcsfq_read0_or_control_complete,
        "control_stability_gate": bool(
            all(
                control["phases"][name]["activity_complete_candidate_count"] == 0
                and control["phases"][name]["post_complete_candidate_count"] == 0
                for control in [all_metrics["cases"]["logical1-read0-control"]]
                for name in ["B_DET", "B_SET", "B_Q", "B_OUT", "B1", "B2", "B3"]
            )
        ),
        "verdict": "ACTIVE_STAGE_NO_TRIGGER",
    }
    if not all_metrics["stage_verdict"]["control_stability_gate"]:
        all_metrics["stage_verdict"]["verdict"] = "FREE_RUNNING"
    elif all_metrics["stage_verdict"]["stage4_dcsfq_one_shot"]:
        all_metrics["stage_verdict"]["verdict"] = "DCSFQ_ONE_SHOT_PASS"
    elif all_metrics["stage_verdict"]["stage2_active_state_compression"]:
        all_metrics["stage_verdict"]["verdict"] = "ACTIVE_GAIN_ESTABLISHED_DCSFQ_SUBTHRESHOLD"

    metrics_path = ROOT / "analysis" / "r15b-execution-metrics.json"
    metrics_path.write_text(json.dumps(all_metrics, indent=2, sort_keys=True) + "\n")
    with (ROOT / "analysis" / "r15b-case-summary.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summary_rows[0]))
        writer.writeheader()
        writer.writerows(summary_rows)
    print(json.dumps(all_metrics["stage_verdict"], indent=2, sort_keys=True))
    print(f"wrote {metrics_path}")


if __name__ == "__main__":
    main()
