#!/usr/bin/env python3
"""Independent arithmetic recheck for the generated metrics.

This is a reviewer-side cross-check: it uses csv.DictReader and NumPy for
the already recorded candidate index intervals, rather than importing the
experiment analyzer's arithmetic functions.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np


EXP = Path(__file__).resolve().parents[1]
PHI0 = 2.067833848e-15
TAU = 2.0 * np.pi


def load(path: Path) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    fields = list(rows[0])
    assert len(fields) == len(set(fields)), f"duplicate header in {path}"
    time = np.asarray([float(row["time"]) for row in rows], dtype=float)
    data = {
        name: np.asarray([float(row[name]) for row in rows], dtype=float)
        for name in fields
        if name != "time"
    }
    return time, data


def main() -> int:
    metrics = json.loads((EXP / "analysis/metrics.json").read_text(encoding="utf-8"))
    max_phase_error = 0.0
    max_area_error = 0.0
    max_kcl_uA = 0.0
    for condition, record in metrics["conditions"].items():
        raw_path = EXP / "runs/A001" / condition / "raw.csv"
        time, data = load(raw_path)
        assert np.all(np.diff(time) > 0.0)
        for signal_name, signal_record in record["signals"].items():
            if signal_record.get("status") != "VALID":
                continue
            phase_label = signal_record["phase_label"]
            voltage_label = signal_record["voltage_label"]
            phase = np.unwrap(data[phase_label])
            voltage = data[voltage_label]
            for candidate in signal_record["candidates"]:
                left = int(candidate["measure_start_index"])
                right = int(candidate["measure_end_index"])
                phase_turns = float((phase[right] - phase[left]) / TAU)
                area_turns = float(np.trapezoid(voltage[left : right + 1], time[left : right + 1]) / PHI0)
                max_phase_error = max(max_phase_error, abs(phase_turns - float(candidate["phase_delta_turns"])))
                max_area_error = max(max_area_error, abs(area_turns - float(candidate["voltage_area_turns"])))
        branches = {
            name: data[label]
            for name, label in {
                "lin": "I(LIN|XBQ1)",
                "bjs": "I(BJS|XBQ1)",
                "l1": "I(L1|XBQ1)",
                "l2": "I(L2|XBQ1)",
                "l3": "I(L3|XBQ1)",
                "bj1": "I(BJ1|XBQ1)",
                "rj1": "I(RJ1|XBQ1)",
                "bj2": "I(BJ2|XBQ1)",
                "rj2": "I(RJ2|XBQ1)",
                "bias": "I(I_QB_BIAS)",
            }.items()
        }
        residuals = (
            branches["lin"] - branches["bjs"],
            branches["bjs"] - branches["bj1"] - branches["rj1"] - branches["l1"],
            branches["l1"] + branches["bias"] - branches["l2"],
            branches["l2"] - branches["bj2"] - branches["rj2"] - branches["l3"],
        )
        max_kcl_uA = max(max_kcl_uA, max(float(np.max(np.abs(residual))) for residual in residuals) * 1.0e6)
    print(f"max_phase_recheck_error_turns={max_phase_error:.3e}")
    print(f"max_area_recheck_error_turns={max_area_error:.3e}")
    print(f"max_kcl_residual_uA={max_kcl_uA:.3e}")
    assert max_phase_error < 1.0e-12
    assert max_area_error < 1.0e-12
    assert max_kcl_uA < 1.0e-3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
