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

DEFAULT_THRESHOLD_RAD = 0.3


def rad_to_turns(phase_delta_rad: float) -> float:
    """Explicit rad -> turns conversion: delta_rad / (2*pi)."""
    return phase_delta_rad / (2.0 * math.pi)


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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "M4 unit-layer metrics for JoSIM phase-mode CSVs. "
            "Columns P(<name>) are raw phase in RADIANS; "
            "phase_delta_turns = phase_delta_rad / (2*pi). "
            "This is NOT a physical Gate (see M5/M6/M9)."
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
    args = parser.parse_args(argv)

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
