#!/usr/bin/env python3
"""Extract R12 DCSFQ input current and build the preregistered R13 replay batch."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[2]
R12 = REPO / "test/exploration/bvm-sfq-receiver-r12a-dcsfq-bvm-reaudit-20260823"
R12_RAW = R12 / "raw"
INPUTS = ROOT / "inputs"
METRICS = ROOT / "analysis" / "input-waveform-metrics.json"

CASES = {
    "read1": R12_RAW / "phase-b-read1/run-01.csv",
    "read0": R12_RAW / "phase-b-read0/run-01.csv",
    "logical1-read0-control": R12_RAW / "phase-b-logical1-read0-control/run-01.csv",
    "logical0-read0-control": R12_RAW / "phase-b-logical0-read0-control/run-01.csv",
}
TRANSFORMS = ("raw-replay", "c1-rectify", "c2-hold20", "c3-rectify-hold20")
ACTIVITY = (94.0, 130.0)
HOLD_PS = 20.0
PHI0 = 2.067833848e-15


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def load_current(path: Path) -> tuple[np.ndarray, np.ndarray]:
    with path.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    time_ps = np.asarray([float(row["time"]) * 1e12 for row in rows], dtype=float)
    current_a = np.asarray([float(row["I(L1|XCONV)"]) for row in rows], dtype=float)
    if not np.all(np.diff(time_ps) > 0):
        raise ValueError(f"non-monotonic time: {path}")
    if len(time_ps) < 2 or abs(time_ps[0]) > 1e-9:
        raise ValueError(f"unexpected time origin: {path}")
    # Extend only the final sample to the requested .tran stop; no waveform
    # amplitude or intermediate sample is altered.
    if time_ps[-1] < 170.0 - 1e-9:
        time_ps = np.append(time_ps, 170.0)
        current_a = np.append(current_a, current_a[-1])
    return time_ps, current_a


def window_mask(time_ps: np.ndarray, bounds: tuple[float, float]) -> np.ndarray:
    return (time_ps >= bounds[0]) & (time_ps < bounds[1])


def current_area(time_ps: np.ndarray, current_a: np.ndarray) -> float:
    # A * ps -> microampere * ps.
    return float(np.trapezoid(current_a, time_ps) * 1e6)


def support_envelope(time_ps: np.ndarray, values: np.ndarray, predicate) -> dict[str, float | None]:
    indices = np.flatnonzero(predicate(values))
    if not len(indices):
        return {"start_ps": None, "end_ps": None, "duration_ps": 0.0}
    return {
        "start_ps": float(time_ps[indices[0]]),
        "end_ps": float(time_ps[indices[-1]]),
        "duration_ps": float(time_ps[indices[-1]] - time_ps[indices[0]]),
    }


def lobe_clusters(time_ps: np.ndarray, values: np.ndarray, predicate) -> list[dict[str, float]]:
    indices = np.flatnonzero(predicate(values))
    if not len(indices):
        return []
    clusters: list[dict[str, float]] = []
    start = previous = int(indices[0])
    for index in indices[1:]:
        index = int(index)
        if index != previous + 1:
            segment = values[start : previous + 1]
            clusters.append(
                {
                    "start_ps": float(time_ps[start]),
                    "end_ps": float(time_ps[previous]),
                    "duration_ps": float(time_ps[previous] - time_ps[start]),
                    "min_uA": float(np.min(segment) * 1e6),
                    "max_uA": float(np.max(segment) * 1e6),
                }
            )
            start = index
        previous = index
    segment = values[start : previous + 1]
    clusters.append(
        {
            "start_ps": float(time_ps[start]),
            "end_ps": float(time_ps[previous]),
            "duration_ps": float(time_ps[previous] - time_ps[start]),
            "min_uA": float(np.min(segment) * 1e6),
            "max_uA": float(np.max(segment) * 1e6),
        }
    )
    return clusters


def make_waveforms(time_ps: np.ndarray, current_a: np.ndarray) -> tuple[dict[str, np.ndarray], dict[str, object]]:
    activity = window_mask(time_ps, ACTIVITY)
    favorable = np.maximum(current_a, 0.0)
    opposite = np.minimum(current_a, 0.0)
    peak_index = np.flatnonzero(activity)[np.argmax(favorable[activity])]
    peak = float(favorable[peak_index])
    peak_time = float(time_ps[peak_index])
    hold = (time_ps >= peak_time) & (time_ps < peak_time + HOLD_PS)
    hold_wave = np.where(hold, peak, 0.0)
    waveforms = {
        "raw-replay": current_a,
        "c1-rectify": favorable,
        "c2-hold20": np.where(hold, opposite + peak, current_a),
        "c3-rectify-hold20": np.where(hold, peak, favorable),
    }
    metrics = {
        "activity_window_ps": list(ACTIVITY),
        "hold_ps": HOLD_PS,
        "favorable_peak_uA": peak * 1e6,
        "favorable_peak_time_ps": peak_time,
        "hold_start_ps": peak_time,
        "hold_end_ps": peak_time + HOLD_PS,
        "raw": {
            "positive_peak_uA": float(np.max(current_a[activity]) * 1e6),
            "negative_peak_uA": float(np.min(current_a[activity]) * 1e6),
            "signed_area_uA_ps": current_area(time_ps[activity], current_a[activity]),
            "absolute_area_uA_ps": current_area(time_ps[activity], np.abs(current_a[activity])),
            "positive_area_uA_ps": current_area(time_ps[activity], favorable[activity]),
            "negative_area_uA_ps": current_area(time_ps[activity], opposite[activity]),
            "positive_support": support_envelope(time_ps[activity], current_a[activity], lambda x: x > 0.0),
            "negative_support": support_envelope(time_ps[activity], current_a[activity], lambda x: x < 0.0),
            "positive_lobe_clusters": lobe_clusters(time_ps[activity], current_a[activity], lambda x: x > 0.0),
            "negative_lobe_clusters": lobe_clusters(time_ps[activity], current_a[activity], lambda x: x < 0.0),
        },
        "transforms": {},
    }
    for name, waveform in waveforms.items():
        metrics["transforms"][name] = {
            "positive_peak_uA": float(np.max(waveform[activity]) * 1e6),
            "negative_peak_uA": float(np.min(waveform[activity]) * 1e6),
            "signed_area_uA_ps": current_area(time_ps[activity], waveform[activity]),
            "absolute_area_uA_ps": current_area(time_ps[activity], np.abs(waveform[activity])),
            "hold_active": name in ("c2-hold20", "c3-rectify-hold20"),
        }
    return waveforms, metrics


def format_time(time_ps: float) -> str:
    if abs(time_ps) < 1e-14:
        return "0"
    return f"{time_ps:.10g}p"


def format_current(current_a: float) -> str:
    value_uA = current_a * 1e6
    if abs(value_uA) < 1e-12:
        return "0"
    return f"{value_uA:.12g}u"


def pwl_lines(time_ps: np.ndarray, waveform: np.ndarray) -> list[str]:
    tokens: list[str] = []
    for time, current in zip(time_ps, waveform):
        tokens.extend((format_time(float(time)), format_current(float(current))))
    pairs_per_line = 12
    lines: list[str] = []
    for start in range(0, len(tokens), pairs_per_line * 2):
        chunk = " ".join(tokens[start : start + pairs_per_line * 2])
        suffix = ")" if start + pairs_per_line * 2 >= len(tokens) else ""
        prefix = "I_REPLAY 0 IN_REPLAY pwl(" if start == 0 else "+ "
        lines.append(f"{prefix}{chunk}{suffix}")
    return lines


def netlist(case: str, transform: str, time_ps: np.ndarray, waveform: np.ndarray) -> str:
    lines = [
        f"* R13-A {case} {transform}: DCSFQ_BVM current replay.",
        ".include ../../../../../circuits/models/jjmit.cir",
        ".include ../../../../../circuits/interface/DCSFQ_BVM.cir",
        "XREPLAY IN_REPLAY Q_REPLAY THmitll_DCSFQ_BVM",
        "R_LOAD Q_REPLAY 0 10",
    ]
    lines.extend(pwl_lines(time_ps, waveform))
    lines.extend(
        [
            ".tran 0.0125p 170p",
            ".print P(B1|XREPLAY) V(B1|XREPLAY) I(B1|XREPLAY) P(B2|XREPLAY) V(B2|XREPLAY) I(B2|XREPLAY) P(B3|XREPLAY) V(B3|XREPLAY) I(B3|XREPLAY)",
            ".print I(L1|XREPLAY) I(L2|XREPLAY) I(L3|XREPLAY) I(L4|XREPLAY) I(L5|XREPLAY) I(L6|XREPLAY) I(LB1|XREPLAY) I(LB2|XREPLAY) I(IB1|XREPLAY) I(IB2|XREPLAY) I(RB1|XREPLAY) I(RB2|XREPLAY) I(RB3|XREPLAY)",
            ".print V(Q_REPLAY) I(R_LOAD)",
            ".end",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    all_metrics: dict[str, object] = {
        "experiment": "R13-A",
        "source_experiment": "R12-A",
        "source_head": "ebe24984771255f002499ec9bef35e9953c87d28",
        "source_column": "I(L1|XCONV)",
        "source_direction": "a_to_node1",
        "favorable_polarity": "positive",
        "source_raw": {},
    }
    for case, path in CASES.items():
        time_ps, current_a = load_current(path)
        waveforms, metrics = make_waveforms(time_ps, current_a)
        metrics["source_path"] = str(path.relative_to(REPO))
        metrics["source_sha256"] = sha256(path)
        all_metrics["source_raw"][case] = metrics
        for transform in TRANSFORMS:
            directory = INPUTS / transform
            directory.mkdir(parents=True, exist_ok=True)
            (directory / f"{case}.cir").write_text(
                netlist(case, transform, time_ps, waveforms[transform])
            )
    # A descriptive, data-derived marker for the read1-only positive tail:
    # after read0's last positive lobe above 10 uA, report read1 positive
    # support above the same fixed 10 uA descriptive level.
    read0_time, read0_current = load_current(CASES["read0"])
    activity = window_mask(read0_time, ACTIVITY)
    read0_indices = np.flatnonzero(activity & (read0_current > 10e-6))
    if len(read0_indices):
        cutoff = float(read0_time[read0_indices[-1]])
        read1_time, read1_current = load_current(CASES["read1"])
        read1_indices = np.flatnonzero(
            window_mask(read1_time, ACTIVITY)
            & (read1_time >= cutoff)
            & (read1_current > 10e-6)
        )
        all_metrics["read1_middle_running_tail_marker"] = {
            "descriptive_threshold_uA": 10.0,
            "read0_last_positive_above_threshold_ps": cutoff,
            "read1_positive_support_after_cutoff_ps": [
                float(read1_time[read1_indices[0]]),
                float(read1_time[read1_indices[-1]]),
            ]
            if len(read1_indices)
            else None,
            "note": "descriptive envelope only; not an event counter or conditioning boundary",
        }
    METRICS.write_text(json.dumps(all_metrics, indent=2, sort_keys=True) + "\n")
    print(json.dumps(all_metrics["read1_middle_running_tail_marker"], indent=2))
    for case, metrics in all_metrics["source_raw"].items():
        raw = metrics["raw"]
        print(
            f"{case}: peak+={raw['positive_peak_uA']:.6g}uA "
            f"peak-={raw['negative_peak_uA']:.6g}uA "
            f"signed={raw['signed_area_uA_ps']:.6g}uA*ps "
            f"abs={raw['absolute_area_uA_ps']:.6g}uA*ps"
        )


if __name__ == "__main__":
    main()
