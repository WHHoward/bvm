#!/usr/bin/env python3
"""Independent raw-only recheck of the central causal comparisons.

This script deliberately does not import ``analyze.py`` and does not consume
``metrics.json``.  It repeats the key vector arithmetic directly from the
immutable receiver-loaded and passive same-mask raw files.  It is a
mechanical consistency check, not a second physical interpretation.
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
PASSIVE = REPO / "test/exploration/bvmsim-4bvm-paperlike-common-sl-accumulation-isolation-v1-20260904"
MASKS = ("0000", "0001", "0010", "0100", "1000", "0011", "0111", "1100", "1110", "1111")
ONE_HOT = ("0001", "0010", "0100", "1000")
ONE_HOT_BY_INSTANCE = {1: "1000", 2: "0100", 3: "0010", 4: "0001"}
MULTI_ACTIVE = ("0011", "0111", "1100", "1110", "1111")
READ = (110.0e-12, 170.0e-12)
PHI0 = 2.067833848e-15
TAU = 2.0 * math.pi

sys.path.insert(0, str(REPO / "scripts"))
from bvmtools.phase import continuous_unwrap, window_indices  # noqa: E402
from bvmtools.raw import read_csv  # noqa: E402


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def selected(trace, bounds: tuple[float, float], label: str | None = None) -> tuple[float, ...]:
    ix = window_indices(trace.time, *bounds)
    if label is None:
        return tuple(float(trace.time[i]) for i in ix)
    values = trace.column(label)
    return tuple(float(values[i]) for i in ix)


def max_abs(values: tuple[float, ...]) -> float:
    return max((abs(value) for value in values), default=0.0)


def rms(values: tuple[float, ...]) -> float:
    return math.sqrt(sum(value * value for value in values) / len(values)) if values else 0.0


def difference(left: tuple[float, ...], right: tuple[float, ...]) -> tuple[float, ...]:
    if len(left) != len(right):
        raise RuntimeError("independent check vector length mismatch")
    return tuple(a - b for a, b in zip(left, right))


def integral(values: tuple[float, ...], times: tuple[float, ...]) -> float:
    return sum(0.5 * (values[i] + values[i + 1]) * (times[i + 1] - times[i]) for i in range(len(values) - 1))


def lsl_sum(trace, bounds: tuple[float, float] = READ) -> tuple[float, ...]:
    rows = [selected(trace, bounds, f"I(L_SL|XBVM{instance})") for instance in range(1, 5)]
    return tuple(sum(row[i] for row in rows) for i in range(len(rows[0])))


def scaled_pair(values: tuple[float, ...], factor: float) -> dict[str, float]:
    return {"max_abs": max_abs(values) * factor, "rms": rms(values) * factor}


def phase_area(trace, phase_label: str, voltage_label: str, bounds: tuple[float, float] = READ) -> dict[str, float]:
    times = selected(trace, bounds)
    phase = selected(trace, bounds, phase_label)
    voltage = selected(trace, bounds, voltage_label)
    unwrapped = continuous_unwrap(phase)
    phase_turns = (unwrapped[-1] - unwrapped[0]) / TAU
    area_turns = integral(voltage, times) / PHI0
    return {
        "phase_delta_turns": phase_turns,
        "voltage_area_turns": area_turns,
        "residual_turns": phase_turns - area_turns,
        "phase_p2p_turns": (max(unwrapped) - min(unwrapped)) / TAU,
        "not_an_sfq_count": True,
    }


def waveform(trace, label: str, factor: float) -> dict[str, float]:
    values = selected(trace, READ, label)
    return {"min": min(values) * factor, "max": max(values) * factor, "max_abs": max_abs(values) * factor, "endpoint_delta": (values[-1] - values[0]) * factor}


def source_plateau_check(trace, label: str, bounds: tuple[float, float], expected: float) -> dict[str, object]:
    values = selected(trace, bounds, label)
    error = max(abs(value - expected) for value in values)
    return {"expected_uA": expected * 1e6, "max_abs_error_uA": error * 1e6, "pass": error <= 0.1e-6}


def main() -> int:
    traces = {mask: read_csv(EXP / "runs" / mask / "raw.csv") for mask in MASKS}
    passive = {mask: read_csv(PASSIVE / "runs" / mask / "raw.csv") for mask in MASKS}
    base_time = traces["0000"].time
    grid = {}
    for mask in MASKS:
        grid[mask] = {
            "array_exact": traces[mask].time == base_time,
            "passive_exact": passive[mask].time == traces[mask].time,
        }
        if not grid[mask]["array_exact"] or not grid[mask]["passive_exact"]:
            raise RuntimeError(f"time grid mismatch in {mask}; no interpolation permitted")

    source_checks: dict[str, object] = {}
    for mask, trace in traces.items():
        source_checks[mask] = {
            "all_controls": all(
                source_plateau_check(trace, f"I(I_{control}{instance})", (111e-12, 120e-12), 100e-6 if mask[instance - 1] == "1" and control in {"WL", "SE"} else 0.0)["pass"]
                for instance in range(1, 5)
                for control in ("WL", "BL", "SE")
            )
        }

    common_kcl: dict[str, object] = {}
    series_kcl: dict[str, object] = {}
    boundary_kcl: dict[str, object] = {}
    passive_delta: dict[str, object] = {}
    for mask in MASKS:
        trace = traces[mask]
        source = tuple(sum(selected(trace, READ, f"I(L_SL|XBVM{instance})")[i] for instance in range(1, 5)) for i in range(len(selected(trace, READ))))
        jsl01 = selected(trace, READ, "I(B_JSL01)")
        common_residual = difference(source, jsl01)
        common_kcl[mask] = scaled_pair(common_residual, 1e6)
        series_kcl[mask] = {}
        for index in range(2, 13):
            series_kcl[mask][f"JSL01-JSL{index:02d}"] = scaled_pair(difference(jsl01, selected(trace, READ, f"I(B_JSL{index:02d})")), 1e6)  # type: ignore[index]
        boundary_kcl[mask] = scaled_pair(difference(selected(trace, READ, "I(B_JSL12)"), selected(trace, READ, "I(LIN|XBQ1)")), 1e6)
        old_sum = lsl_sum(passive[mask])
        new_sum = lsl_sum(trace)
        passive_delta[mask] = {
            "SUM_LSL_new_minus_passive_uA": scaled_pair(difference(new_sum, old_sum), 1e6),
            "JSL01_new_minus_passive_terminal_uA": scaled_pair(difference(jsl01, selected(passive[mask], READ, "I(B_COL_LOAD01)")), 1e6),
        }

    one_hot_symmetry: dict[str, object] = {}
    symmetry_labels = {
        "SUM_LSL": None,
        "JSL01": "I(B_JSL01)",
        "LIN": "I(LIN|XBQ1)",
        "QBIN": "V(QBIN)",
    }
    for left_index, left_mask in enumerate(ONE_HOT):
        for right_mask in ONE_HOT[left_index + 1 :]:
            item: dict[str, object] = {}
            for name, label in symmetry_labels.items():
                left = lsl_sum(traces[left_mask]) if label is None else selected(traces[left_mask], READ, label)
                right = lsl_sum(traces[right_mask]) if label is None else selected(traces[right_mask], READ, label)
                scale = 1e6 if name != "QBIN" else 1e3
                item[name] = scaled_pair(difference(left, right), scale)
            one_hot_symmetry[f"{left_mask}_vs_{right_mask}"] = item

    additivity: dict[str, object] = {}
    zero = traces["0000"]
    labels = {"SUM_LSL": None, "JSL01": "I(B_JSL01)", "LIN": "I(LIN|XBQ1)", "QBIN": "V(QBIN)"}
    one_hot_delta: dict[tuple[str, str], tuple[float, ...]] = {}
    for mask in ONE_HOT:
        for name, label in labels.items():
            left = lsl_sum(traces[mask]) if label is None else tuple(traces[mask].column(label))
            right = lsl_sum(zero) if label is None else tuple(zero.column(label))
            one_hot_delta[(mask, name)] = difference(left, right)
    for mask in MULTI_ACTIVE:
        active = [ONE_HOT_BY_INSTANCE[i] for i in range(1, 5) if mask[i - 1] == "1"]
        item: dict[str, object] = {"active_one_hot_masks": active, "signals": {}}
        for name, label in labels.items():
            actual_left = lsl_sum(traces[mask]) if label is None else tuple(traces[mask].column(label))
            actual_zero = lsl_sum(zero) if label is None else tuple(zero.column(label))
            actual = difference(actual_left, actual_zero)
            predicted = tuple(sum(one_hot_delta[(onehot, name)][i] for onehot in active) for i in range(len(actual)))
            residual = difference(actual, predicted)
            factor = 1e6 if name != "QBIN" else 1e3
            item["signals"][name] = {  # type: ignore[index]
                "actual_delta": scaled_pair(actual, factor),
                "predicted_delta": scaled_pair(predicted, factor),
                "residual": scaled_pair(residual, factor),
                "normalized_rms": rms(residual) / rms(actual) if rms(actual) else None,
            }
        additivity[mask] = item

    population: dict[str, object] = {}
    for mask, trace in traces.items():
        population[mask] = {
            "commanded_population": mask.count("1"),
            "SUM_LSL_uA": waveform_metrics_tuple(lsl_sum(trace), trace),
            "JSL01_uA": waveform(trace, "I(B_JSL01)", 1e6),
            "LIN_uA": waveform(trace, "I(LIN|XBQ1)", 1e6),
            "QBIN_mV": waveform(trace, "V(QBIN)", 1e3),
            "BJ2": phase_area(trace, "P(BJ2|XBQ1)", "V(BJ2|XBQ1)"),
            "JTL6_B02": phase_area(trace, "P(B02|XJTL1_6)", "V(B02|XJTL1_6)"),
        }

    output = {
        "schema": "bvmsim-common-sl-12jsl-qb-independent-check-v1",
        "created_at_local": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "experiment_id": EXP.name,
        "raw_hashes": {mask: digest(EXP / "runs" / mask / "raw.csv") for mask in MASKS},
        "passive_raw_hashes": {mask: digest(PASSIVE / "runs" / mask / "raw.csv") for mask in MASKS},
        "time_grid": grid,
        "interpolation": "none",
        "source_protocol": source_checks,
        "common_sl_kcl_read_uA": common_kcl,
        "jsl_series_kcl_read_uA": series_kcl,
        "jsl12_to_lin_boundary_kcl_read_uA": boundary_kcl,
        "receiver_minus_passive_source_context": passive_delta,
        "one_hot_symmetry_read": one_hot_symmetry,
        "additivity_under_qb_load_read": additivity,
        "population": population,
        "independence_note": "does not import analyze.py or metrics.json; direct arithmetic over bvmtools.raw traces",
        "status": "PASS",
    }
    target = EXP / "analysis/independent_check.json"
    if target.exists():
        raise RuntimeError(f"refusing to overwrite immutable independent check: {target}")
    target.write_text(json.dumps(output, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "mask_count": len(MASKS), "grid_exact": True, "interpolation": "none"}, ensure_ascii=False))
    return 0


def waveform_metrics_tuple(values: tuple[float, ...], trace) -> dict[str, float]:
    return {"min_uA": min(values) * 1e6, "max_uA": max(values) * 1e6, "max_abs_uA": max_abs(values) * 1e6, "endpoint_delta_uA": (values[-1] - values[0]) * 1e6}


if __name__ == "__main__":
    raise SystemExit(main())
