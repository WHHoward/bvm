#!/usr/bin/env python3
"""Independent compact recheck; does not import analyze.py or metrics.json."""

from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
MASKS = ("0000", "0001", "0010", "0100", "1000", "0011", "0111", "1100", "1110", "1111")
ONE_HOT = ("0001", "0010", "0100", "1000")
ONE_HOT_BY_INSTANCE = {1: "1000", 2: "0100", 3: "0010", 4: "0001"}
READ = (110e-12, 170e-12)

sys.path.insert(0, str(REPO / "scripts"))
from bvmtools.compare import exact_time_grid_identity  # noqa: E402
from bvmtools.kcl import kcl_window_metrics, linear_kcl_residual  # noqa: E402
from bvmtools.phase import window_indices  # noqa: E402
from bvmtools.raw import read_csv  # noqa: E402


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def vals(trace, label: str) -> tuple[float, ...]:
    return trace.column(label)  # type: ignore[return-value]


def selected(trace, label: str) -> tuple[float, ...]:
    indices = window_indices(trace.time, *READ)
    return tuple(float(vals(trace, label)[index]) for index in indices)


def max_abs(values: tuple[float, ...]) -> float:
    return max((abs(value) for value in values), default=0.0)


def rms(values: tuple[float, ...]) -> float:
    return math.sqrt(sum(value * value for value in values) / len(values)) if values else 0.0


def subtract(left: tuple[float, ...], right: tuple[float, ...]) -> tuple[float, ...]:
    if len(left) != len(right):
        raise RuntimeError("independent vector length mismatch")
    return tuple(a - b for a, b in zip(left, right))


def main() -> int:
    traces = {mask: read_csv(EXP / "runs" / mask / "raw.csv") for mask in MASKS}
    baseline = traces["0000"]
    for mask, trace in traces.items():
        if trace.duplicate_columns:
            raise RuntimeError(f"duplicate raw columns in {mask}: {trace.duplicate_columns}")
        if not exact_time_grid_identity(trace.time, baseline.time):
            raise RuntimeError(f"time-grid mismatch in {mask}")

    onehot: dict[str, object] = {}
    for mask in ONE_HOT:
        instance = next(index for index, bit in enumerate(mask, start=1) if bit == "1")
        current = selected(traces[mask], "I(B_COL_LOAD01)")
        onehot[mask] = {
            "active_bvm": f"BVM{instance}",
            "common_current_max_abs_uA": max_abs(current) * 1e6,
            "common_current_rms_uA": rms(current) * 1e6,
            "active_lsl_max_abs_uA": max_abs(selected(traces[mask], f"I(L_SL|XBVM{instance})")) * 1e6,
        }

    inactive: dict[str, object] = {}
    for mask in ONE_HOT:
        active = next(index for index, bit in enumerate(mask, start=1) if bit == "1")
        victims: dict[str, object] = {}
        for victim in range(1, 5):
            if victim == active:
                continue
            victims[f"BVM{victim}"] = {}
            for branch in ("R_SL", "L_SL", "R_S", "L_S3"):
                delta = subtract(selected(traces[mask], f"I({branch}|XBVM{victim})"), selected(baseline, f"I({branch}|XBVM{victim})"))
                victims[f"BVM{victim}"][branch] = {"max_abs_uA": max_abs(delta) * 1e6, "rms_uA": rms(delta) * 1e6}
        inactive[mask] = victims

    delta = {mask: subtract(selected(traces[mask], "I(B_COL_LOAD01)"), selected(baseline, "I(B_COL_LOAD01)")) for mask in MASKS}
    additivity: dict[str, object] = {}
    for mask in ("0011", "0111", "1100", "1110", "1111"):
        active_onehots = [ONE_HOT_BY_INSTANCE[index] for index, bit in enumerate(mask, start=1) if bit == "1"]
        predicted = tuple(sum(delta[onehot][i] for onehot in active_onehots) for i in range(len(delta[mask])))
        residual = subtract(delta[mask], predicted)
        additivity[mask] = {
            "active_one_hot_masks": active_onehots,
            "actual_delta_max_abs_uA": max_abs(delta[mask]) * 1e6,
            "predicted_delta_max_abs_uA": max_abs(predicted) * 1e6,
            "residual_max_abs_uA": max_abs(residual) * 1e6,
            "residual_rms_uA": rms(residual) * 1e6,
            "normalized_rms_error": rms(residual) / rms(delta[mask]) if rms(delta[mask]) else None,
        }

    kcl_max: dict[str, float] = {}
    for mask, trace in traces.items():
        max_value = 0.0
        for instance in range(1, 5):
            h = f"XBVM{instance}"
            equations = (
                ({"a": vals(trace, f"I(B_JM1|{h})"), "b": vals(trace, f"I(R_JM1|{h})"), "c": vals(trace, f"I(L_M1|{h})")}, {"a": 1, "b": 1, "c": -1}),
                ({"a": vals(trace, f"I(B_JS1|{h})"), "b": vals(trace, f"I(L_PSE|{h})"), "c": vals(trace, f"I(R_S|{h})"), "d": vals(trace, f"I(L_S3|{h})")}, {"a": 1, "b": 1, "c": -1, "d": -1}),
                ({"a": vals(trace, f"I(R_S|{h})"), "b": vals(trace, f"I(L_S3|{h})"), "c": vals(trace, f"I(B_JS2|{h})"), "d": vals(trace, f"I(L_PSL|{h})")}, {"a": 1, "b": 1, "c": 1, "d": -1}),
                ({"a": vals(trace, f"I(L_PSL|{h})"), "b": vals(trace, f"I(R_SL|{h})")}, {"a": 1, "b": -1}),
                ({"a": vals(trace, f"I(R_SL|{h})"), "b": vals(trace, f"I(L_SL|{h})")}, {"a": 1, "b": -1}),
            )
            for branches, coefficients in equations:
                residual = linear_kcl_residual(branches, coefficients)
                max_value = max(max_value, kcl_window_metrics(trace.time, residual, READ, unit="A")["max_abs_uA"])
        common = {f"LSL{i}": vals(trace, f"I(L_SL|XBVM{i})") for i in range(1, 5)}
        common["load"] = vals(trace, "I(B_COL_LOAD01)")
        residual = linear_kcl_residual(common, {f"LSL{i}": 1 for i in range(1, 5)} | {"load": -1})
        max_value = max(max_value, kcl_window_metrics(trace.time, residual, READ, unit="A")["max_abs_uA"])
        kcl_max[mask] = max_value

    result = {
        "schema": "bvmsim-paperlike-common-sl-independent-check-v1",
        "raw_hashes": {mask: digest(EXP / "runs" / mask / "raw.csv") for mask in MASKS},
        "exact_grid_all_masks": True,
        "one_hot": onehot,
        "inactive_isolation": inactive,
        "additivity_direct_common_current": additivity,
        "kcl_read_max_abs_uA_by_mask": kcl_max,
        "does_not_import_primary_analysis": True,
    }
    output = EXP / "analysis/independent_check.json"
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "output": str(output), "max_direct_additivity_residual_uA": max(item["residual_max_abs_uA"] for item in additivity.values()), "max_kcl_residual_uA": max(kcl_max.values())}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
