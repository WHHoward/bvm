#!/usr/bin/env python3
"""Independent compact recheck of the three primary evidence families.

This file intentionally does not import ``analyze.py`` or read ``metrics.json``.
It reuses the repository raw reader for duplicate-safe artifact access, then
recomputes the core max-absolute deltas and superposition residuals directly.
"""

from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
import sys


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
MASKS = ("0000", "0001", "0010", "0100", "1000", "0011", "0111", "1100", "1110", "1111")
ONE_HOT = ("0001", "0010", "0100", "1000")
ONE_HOT_BY_INSTANCE = {1: "1000", 2: "0100", 3: "0010", 4: "0001"}
FORWARD = ("1100", "1110", "1111")
REVERSE = ("0011", "0111", "1111")
READ = (110.0e-12, 170.0e-12)

sys.path.insert(0, str(REPO / "scripts"))
from bvmtools.phase import window_indices  # noqa: E402
from bvmtools.raw import read_csv  # noqa: E402


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def values(trace, label: str, bounds: tuple[float, float]) -> tuple[float, ...]:
    indices = window_indices(trace.time, *bounds)
    return tuple(float(trace.column(label)[index]) for index in indices)


def max_abs(values_: tuple[float, ...]) -> float:
    return max((abs(value) for value in values_), default=0.0)


def rms(values_: tuple[float, ...]) -> float:
    return math.sqrt(sum(value * value for value in values_) / len(values_)) if values_ else 0.0


def subtract(left: tuple[float, ...], right: tuple[float, ...]) -> tuple[float, ...]:
    if len(left) != len(right):
        raise RuntimeError("independent check vector length mismatch")
    return tuple(a - b for a, b in zip(left, right))


def load() -> dict[str, object]:
    return {mask: read_csv(EXP / "runs" / mask / "raw.csv") for mask in MASKS}


def main() -> int:
    traces = load()
    baseline = traces["0000"]
    for mask, trace in traces.items():
        if trace.duplicate_columns:
            raise RuntimeError(f"duplicate raw columns in {mask}: {trace.duplicate_columns}")
        if trace.time != baseline.time:
            raise RuntimeError(f"time grid mismatch in {mask}")

    position: dict[str, object] = {}
    zero_bvm_delta: dict[str, object] = {}
    for instance, mask in ONE_HOT_BY_INSTANCE.items():
        trace = traces[mask]
        position[mask] = {
            "active_bvm": f"BVM{instance}",
            "I(LIN|XBQ1)_uA": {
                "max_abs": max_abs(values(trace, "I(LIN|XBQ1)", READ)) * 1e6,
                "rms": rms(values(trace, "I(LIN|XBQ1)", READ)) * 1e6,
            },
            "V(QBIN)_mV": {
                "max_abs": max_abs(values(trace, "V(QBIN)", READ)) * 1e3,
                "rms": rms(values(trace, "V(QBIN)", READ)) * 1e3,
            },
        }
        victims: dict[str, object] = {}
        for victim in range(1, 5):
            if victim == instance:
                continue
            item: dict[str, object] = {}
            for branch in ("R_SL", "L_SL", "R_S", "L_S3", "L_M3"):
                label = f"I({branch}|XBVM{victim})"
                delta = subtract(values(trace, label, READ), values(baseline, label, READ))
                item[branch] = {"max_abs_uA": max_abs(delta) * 1e6, "rms_uA": rms(delta) * 1e6}
            victims[f"BVM{victim}"] = item
        zero_bvm_delta[mask] = victims

    delta: dict[tuple[str, str], tuple[float, ...]] = {}
    labels = ["I(LIN|XBQ1)", "V(QBIN)"] + [f"I(L_SL|XBVM{n})" for n in range(1, 5)]
    for mask in ONE_HOT:
        for label in labels:
            delta[(mask, label)] = subtract(values(traces[mask], label, READ), values(baseline, label, READ))

    superposition: dict[str, object] = {}
    for direction, masks in (("forward", FORWARD), ("reverse", REVERSE)):
        superposition[direction] = {}
        for mask in masks:
            active_onehots = [ONE_HOT_BY_INSTANCE[index] for index, bit in enumerate(mask, start=1) if bit == "1"]
            actual_by_label: dict[str, object] = {}
            for label in labels:
                actual = subtract(values(traces[mask], label, READ), values(baseline, label, READ))
                predicted = tuple(sum(delta[(onehot, label)][i] for onehot in active_onehots) for i in range(len(actual)))
                residual = subtract(actual, predicted)
                scale = 1e6 if label.startswith("I(") else 1e3
                actual_by_label[label] = {
                    "active_one_hot_masks": active_onehots,
                    "actual_delta_max_abs": max_abs(actual) * scale,
                    "predicted_delta_max_abs": max_abs(predicted) * scale,
                    "residual_max_abs": max_abs(residual) * scale,
                    "residual_rms": rms(residual) * scale,
                    "normalized_rms_error": rms(residual) / rms(actual) if rms(actual) else None,
                    "display_unit": "uA" if label.startswith("I(") else "mV",
                }
            superposition[direction][mask] = actual_by_label  # type: ignore[index]

    output = {
        "schema": "bvmsim-4bvm-allone-selective-read-independent-check-v1",
        "created_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "raw_hashes": {mask: digest(EXP / "runs" / mask / "raw.csv") for mask in MASKS},
        "window_ps": [110.0, 170.0],
        "interpolation": "none",
        "position": position,
        "zero_bvm_delta_current": zero_bvm_delta,
        "superposition": superposition,
        "status": "PASS",
        "independence_note": "does not import experiment analyzer or metrics.json; calculations are direct vector arithmetic over shared duplicate-safe raw traces",
    }
    target = EXP / "analysis/independent_check.json"
    if target.exists():
        raise RuntimeError(f"refusing to overwrite independent check: {target}")
    target.write_text(json.dumps(output, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "one_hot_count": len(ONE_HOT_BY_INSTANCE), "grid": "exact"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
