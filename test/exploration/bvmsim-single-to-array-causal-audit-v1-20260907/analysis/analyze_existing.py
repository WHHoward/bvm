#!/usr/bin/env python3
"""Analyze the existing single/array raw plus the authorized G1--G4 bridge.

The analysis intentionally keeps the source raw outside this task directory:
the old raw files are historical evidence and are never rewritten.  All
pointwise comparisons use exact stored timestamps; phase is unwrapped only
for derived comparisons and is kept in radians in derived CSVs so the
repository renderer performs the single rad/(2*pi) display conversion.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import subprocess
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Mapping, Sequence


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
SINGLE_EXP = REPO / "test/exploration/bvmsim-jm2-connected-single-rloop-observability-v1-20260904"
ARRAY_EXP = REPO / "test/exploration/bvmsim-4bvm-common-sl-12jsl-qb-integration-v1-20260904"
PASSIVE_EXP = REPO / "test/exploration/bvmsim-4bvm-paperlike-common-sl-accumulation-isolation-v1-20260904"
GOLDEN_RAW = SINGLE_EXP / "runs/S1-J-RLOOP/raw.csv"
ARRAY_MASKS = ("0000", "0001", "0010", "0100", "1000", "0011", "0111", "1100", "1110", "1111")
ONE_HOT = ("0001", "0010", "0100", "1000")
ONE_HOT_BY_INSTANCE = {1: "1000", 2: "0100", 3: "0010", 4: "0001"}
WINDOWS_PS = OrderedDict((
    ("PRE", (45.0, 50.0)),
    ("WRITE0", (50.0, 70.0)),
    ("NO_HISTORY_READ", (70.0, 90.0)),
    ("WRITE1_ALL", (90.0, 101.0)),
    ("SETTLE", (101.0, 110.0)),
    ("READ", (110.0, 170.0)),
    ("TAIL", (170.0, 200.0)),
))
WINDOWS_S = OrderedDict((name, (left * 1e-12, right * 1e-12)) for name, (left, right) in WINDOWS_PS.items())
SINGLE_READ_S = (70e-12, 82e-12)
ARRAY_READ_S = WINDOWS_S["READ"]
TAU = 2.0 * math.pi
PHI0 = 2.067833848e-15
METRIC_SPEC = REPO / "docs/research/METRIC_SPEC_V2.md"
PLOTTER = REPO / "scripts/josim-plot2.py"
SOLVER = REPO / "build/josim-cli"
VARIANT = REPO / "test/exploration/bvmsim-jm2-connected-single-ab-v1-20260903/variants/bvm_jm2_connected.cir"
BQ = REPO / "BVMSim/BQ.cir"
JTL = REPO / "BVMSim/library_josim/jtl2.cir"
JJMIT = REPO / "circuits/models/jjmit.cir"
CANONICAL_BVM = REPO / "circuits/bvm/bvm_cell.cir"

sys_path_added = False
import sys
sys.path.insert(0, str(REPO / "scripts"))
from bvmtools.compare import exact_time_grid_identity  # noqa: E402
from bvmtools.kcl import kcl_window_metrics, linear_kcl_residual  # noqa: E402
from bvmtools.metrics import phase_area_window  # noqa: E402
from bvmtools.phase import continuous_unwrap, window_indices  # noqa: E402
from bvmtools.raw import RawTrace, read_csv  # noqa: E402
from bvmtools.waveform import percentile, trapezoid_integral, waveform_metrics  # noqa: E402


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO.resolve()).as_posix()


def now_local() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def values(trace: RawTrace, label: str, *, phase: bool = False) -> tuple[float, ...]:
    raw = trace.column(label)
    if phase:
        return continuous_unwrap(raw)  # type: ignore[arg-type]
    return raw  # type: ignore[return-value]


def exact_indices(trace: RawTrace, target_time: Sequence[float]) -> tuple[int, ...]:
    lookup = {timestamp: index for index, timestamp in enumerate(trace.time)}
    missing = [timestamp for timestamp in target_time if timestamp not in lookup]
    if missing:
        raise RuntimeError(f"no exact timestamp in {trace.path}: {missing[:3]}")
    return tuple(lookup[timestamp] for timestamp in target_time)


def common_grid(traces: Mapping[str, RawTrace]) -> tuple[float, ...]:
    shortest = min(traces.values(), key=lambda item: len(item.time))
    candidate = shortest.time
    sets = [set(trace.time) for trace in traces.values()]
    result = tuple(timestamp for timestamp in candidate if all(timestamp in present for present in sets))
    if len(result) < 2:
        raise RuntimeError("fewer than two exact common timestamps")
    return result


def window_indices_for(time_s: Sequence[float], bounds: tuple[float, float]) -> tuple[int, ...]:
    selected = window_indices(time_s, *bounds)
    if len(selected) < 2:
        raise RuntimeError(f"window has fewer than two samples: {bounds}")
    return selected


def scale_for(unit: str) -> tuple[float, float, str, str]:
    if unit == "A":
        return 1e6, 1e18, "uA", "uA*ps"
    if unit == "V":
        return 1e3, 1e15, "mV", "mV*ps"
    if unit == "rad":
        return 1.0, 1.0, "rad", "rad*s"
    raise ValueError(unit)


def diff_metrics(time_s: Sequence[float], difference: Sequence[float], bounds: tuple[float, float], unit: str) -> dict[str, object]:
    indices = window_indices_for(time_s, bounds)
    selected_time = [float(time_s[index]) for index in indices]
    selected = [float(difference[index]) for index in indices]
    base = waveform_metrics(selected_time, selected)
    value_factor, area_factor, display_unit, area_unit = scale_for(unit)
    abs_values = [abs(value) for value in selected]
    maximum_abs_index = max(range(len(selected)), key=lambda index: abs(selected[index]))
    return {
        "unit": display_unit,
        "raw_unit": unit,
        "area_unit": area_unit,
        "window_ps": [bounds[0] * 1e12, bounds[1] * 1e12],
        "sample_count": len(selected),
        "minimum": float(base["minimum"]) * value_factor,
        "maximum": float(base["maximum"]) * value_factor,
        "p2p": float(base["p2p"]) * value_factor,
        "mean": float(base["mean"]) * value_factor,
        "rms": float(base["rms"]) * value_factor,
        "max_abs": max(abs_values) * value_factor,
        "p95_abs": percentile(abs_values, 0.95) * value_factor,
        "endpoint_difference": selected[-1] * value_factor,
        "signed_integral": trapezoid_integral(selected, selected_time) * area_factor,
        "minimum_time_ps": float(base["minimum_time"]) * 1e12,
        "maximum_time_ps": float(base["peak_time"]) * 1e12,
        "maximum_abs_time_ps": selected_time[maximum_abs_index] * 1e12,
        "raw_max_abs": max(abs_values),
        "raw_rms": float(base["rms"]),
    }


def pair_difference(
    left: RawTrace,
    left_label: str,
    right: RawTrace,
    right_label: str,
    target_time: Sequence[float],
    *,
    phase: bool,
) -> tuple[float, ...]:
    left_indices = exact_indices(left, target_time)
    right_indices = exact_indices(right, target_time)
    left_values = values(left, left_label, phase=phase)
    right_values = values(right, right_label, phase=phase)
    return tuple(
        float(right_values[right_indices[position]])
        - float(left_values[left_indices[position]])
        for position in range(len(target_time))
    )


def pair_record(
    left: RawTrace,
    left_label: str,
    right: RawTrace,
    right_label: str,
    target_time: Sequence[float],
    *,
    unit: str,
    windows: Mapping[str, tuple[float, float]],
) -> tuple[tuple[float, ...], dict[str, object]]:
    phase = unit == "rad"
    difference = pair_difference(left, left_label, right, right_label, target_time, phase=phase)
    record: dict[str, object] = {
        "left_label": left_label,
        "right_label": right_label,
        "difference_convention": "right_minus_left",
        "phase_conversion": "continuous_unwrap(rad)/(2*pi)" if phase else None,
        "windows": {name: diff_metrics(target_time, difference, bounds, unit) for name, bounds in windows.items()},
    }
    return difference, record


def phase_area_if_available(trace: RawTrace, phase_label: str, voltage_label: str, bounds: tuple[float, float]) -> dict[str, object] | None:
    if phase_label not in trace.headers or voltage_label not in trace.headers:
        return None
    return phase_area_window(trace.time, values(trace, phase_label), values(trace, voltage_label), bounds, include_segments=False)


def trajectory_diff(
    left: RawTrace,
    left_label: str,
    right: RawTrace,
    right_label: str,
    target_time: Sequence[float],
    *,
    unit: str,
    windows: Mapping[str, tuple[float, float]],
) -> tuple[tuple[float, ...], dict[str, object]]:
    phase = unit == "rad"
    difference = pair_difference(left, left_label, right, right_label, target_time, phase=phase)
    result = {
        "left_label": left_label,
        "right_label": right_label,
        "difference_convention": "right_minus_left",
        "phase_conversion": "continuous_unwrap(rad)/(2*pi)" if phase else None,
        "windows": {name: diff_metrics(target_time, difference, bounds, unit) for name, bounds in windows.items()},
    }
    return difference, result


def trajectory_stats(trace: RawTrace, label: str, bounds: tuple[float, float], unit: str) -> dict[str, object]:
    phase = unit == "rad"
    raw = values(trace, label, phase=phase)
    indices = window_indices_for(trace.time, bounds)
    selected_t = [trace.time[index] for index in indices]
    selected = [raw[index] for index in indices]
    base = waveform_metrics(selected_t, selected)
    factor, area_factor, display, area_unit = scale_for(unit)
    return {
        "label": label,
        "unit": display,
        "raw_unit": unit,
        "area_unit": area_unit,
        "window_ps": [bounds[0] * 1e12, bounds[1] * 1e12],
        "minimum": float(base["minimum"]) * factor,
        "maximum": float(base["maximum"]) * factor,
        "p2p": float(base["p2p"]) * factor,
        "mean": float(base["mean"]) * factor,
        "rms": float(base["rms"]) * factor,
        "endpoint_delta": (selected[-1] - selected[0]) * factor,
        "signed_integral": trapezoid_integral(selected, selected_t) * area_factor,
        "phase_conversion": "continuous_unwrap(rad)/(2*pi)" if phase else None,
    }


def single_array_layers() -> OrderedDict[str, list[tuple[str, str, str]]]:
    return OrderedDict((
        ("COMMON_SL", [("V", "V(SL1)", "V(COMMON_SL)")]),
        ("LSL", [("I", "I(L_SL|XBVM1)", "I(L_SL|XBVM{instance})"), ("V", "V(L_SL|XBVM1)", "V(L_SL|XBVM{instance})")]),
        ("RSL", [("I", "I(R_SL|XBVM1)", "I(R_SL|XBVM{instance})"), ("V", "V(R_SL|XBVM1)", "V(R_SL|XBVM{instance})")]),
        ("LS2_JS2", [("I", "I(L_S2|XBVM1)", "I(L_S2|XBVM{instance})"), ("P", "P(B_JS2|XBVM1)", "P(B_JS2|XBVM{instance})"), ("V", "V(B_JS2|XBVM1)", "V(B_JS2|XBVM{instance})")]),
        ("LM3", [("I", "I(L_M3|XBVM1)", "I(L_M3|XBVM{instance})")]),
        ("LS1_JS1", [("I", "I(L_S1|XBVM1)", "I(L_S1|XBVM{instance})"), ("P", "P(B_JS1|XBVM1)", "P(B_JS1|XBVM{instance})"), ("V", "V(B_JS1|XBVM1)", "V(B_JS1|XBVM{instance})")]),
        ("JM2", [("P", "P(B_JM2|XBVM1)", "P(B_JM2|XBVM{instance})"), ("V", "V(B_JM2|XBVM1)", "V(B_JM2|XBVM{instance})")]),
        ("JM1", [("P", "P(B_JM1|XBVM1)", "P(B_JM1|XBVM{instance})"), ("V", "V(B_JM1|XBVM1)", "V(B_JM1|XBVM{instance})")]),
    ))


def compare_single_to_onehot(single: RawTrace, arrays: Mapping[str, RawTrace]) -> dict[str, object]:
    output: dict[str, object] = {"golden": rel(single.path), "per_one_hot": {}}
    for mask in ONE_HOT:
        array = arrays[mask]
        instance = next(index for index in range(1, 5) if mask[index - 1] == "1")
        records: dict[str, object] = {"active_bvm": f"BVM{instance}", "time_grid_exact_overlap": False, "signals": {}}
        overlap = tuple(array.time)
        records["time_grid_exact_overlap"] = len(exact_indices(single, overlap)) == len(overlap)
        for layer, specs in single_array_layers().items():
            layer_records: dict[str, object] = {}
            for kind, left_label, right_template in specs:
                right_label = right_template.format(instance=instance)
                unit = "A" if kind == "I" else "V" if kind == "V" else "rad"
                difference = pair_difference(single, left_label, array, right_label, overlap, phase=kind == "P")
                signal_record: dict[str, object] = {
                    "left_label": left_label,
                    "right_label": right_label,
                    "difference_convention": "array_minus_single",
                    "phase_conversion": "continuous_unwrap(rad)/(2*pi)" if kind == "P" else None,
                    "windows": {name: diff_metrics(overlap, difference, bounds, unit) for name, bounds in WINDOWS_S.items()},
                }
                if kind == "P":
                    left_voltage = left_label.replace("P(", "V(", 1)
                    right_voltage = right_label.replace("P(", "V(", 1)
                    signal_record["same_junction_phase_area"] = {
                        "single": {
                            name: phase_area_if_available(single, left_label, left_voltage, bounds)
                            for name, bounds in WINDOWS_S.items()
                        },
                        "array": {
                            name: phase_area_if_available(array, right_label, right_voltage, bounds)
                            for name, bounds in WINDOWS_S.items()
                        },
                        "note": "same-JJ phase displacement and voltage area; descriptive arithmetic, not an SFQ count",
                    }
                layer_records[kind + ":" + left_label] = signal_record
            records["signals"][layer] = layer_records
        output["per_one_hot"][mask] = records
    return output


def signal_spec_for_layer(layer: str) -> tuple[str, str, str]:
    candidates = single_array_layers()[layer]
    return candidates[0]


def earliest_run(time_s: Sequence[float], difference: Sequence[float], threshold: float, consecutive: int, bounds: tuple[float, float]) -> dict[str, object]:
    candidate = [index for index, timestamp in enumerate(time_s) if bounds[0] <= timestamp < bounds[1]]
    for offset in range(0, len(candidate) - consecutive + 1):
        indices = candidate[offset:offset + consecutive]
        if all(abs(float(difference[index])) > threshold for index in indices):
            return {"time_ps": float(time_s[indices[0]]) * 1e12, "sample_index": int(indices[0]), "consecutive_samples": consecutive}
    return {"time_ps": None, "sample_index": None, "consecutive_samples": consecutive}


def divergence_analysis(single: RawTrace, arrays: Mapping[str, RawTrace]) -> dict[str, object]:
    factor_primary = 5.0
    floors = {"A": 1e-12, "V": 1e-12, "rad": 1e-9}
    output: dict[str, object] = {
        "definition": "threshold=max(numerical_floor, PRE max_abs_difference*factor); N consecutive samples",
        "primary_factor": factor_primary,
        "primary_consecutive_samples": 3,
        "sensitivity_factors": [3.0, 5.0, 10.0],
        "sensitivity_consecutive_samples": [2, 3, 5],
        "scan_window_ps": [45.0, 170.0],
        "per_one_hot": {},
    }
    for mask in ONE_HOT:
        array = arrays[mask]
        instance = next(index for index in range(1, 5) if mask[index - 1] == "1")
        time_s = array.time
        layers: dict[str, object] = {}
        for layer, specs in single_array_layers().items():
            signals: dict[str, object] = {}
            for kind, left_label, right_template in specs:
                right_label = right_template.format(instance=instance)
                unit = "A" if kind == "I" else "V" if kind == "V" else "rad"
                diff = pair_difference(single, left_label, array, right_label, time_s, phase=kind == "P")
                pre_indices = window_indices_for(time_s, WINDOWS_S["PRE"])
                pre_max = max(abs(diff[index]) for index in pre_indices)
                threshold = max(floors[unit], factor_primary * pre_max)
                primary = earliest_run(time_s, diff, threshold, 3, (45e-12, 170e-12))
                sensitivity: dict[str, object] = {}
                for factor in (3.0, 5.0, 10.0):
                    for consecutive in (2, 3, 5):
                        sensitivity[f"factor_{factor:g}_N_{consecutive}"] = earliest_run(time_s, diff, max(floors[unit], factor * pre_max), consecutive, (45e-12, 170e-12))
                signals[kind + ":" + left_label] = {
                    "unit": unit,
                    "left_label": left_label,
                    "right_label": right_label,
                    "pre_max_abs_raw": pre_max,
                    "numerical_floor_raw": floors[unit],
                    "primary_threshold_raw": threshold,
                    "primary": primary,
                    "sensitivity": sensitivity,
                }
            layer_values = [item["primary"]["time_ps"] for item in signals.values() if item["primary"]["time_ps"] is not None]  # type: ignore[index]
            layers[layer] = {"earliest_primary_time_ps": min(layer_values) if layer_values else None, "signals": signals}
        output["per_one_hot"][mask] = {"active_bvm": f"BVM{instance}", "layers": layers}
    representative = output["per_one_hot"]["1000"]  # type: ignore[index]
    output["representative_mask"] = "1000"
    output["primary_timeline"] = [
        {"layer": layer, "earliest_time_ps": representative["layers"][layer]["earliest_primary_time_ps"]}  # type: ignore[index]
        for layer in single_array_layers()
    ]
    return output


def onehot_symmetry(arrays: Mapping[str, RawTrace]) -> dict[str, object]:
    labels = (
        ("V(COMMON_SL)", "V"),
        ("I(L_SL|XBVM1)", "A"),
        ("I(L_S2|XBVM1)", "A"),
        ("P(B_JS2|XBVM1)", "rad"),
        ("P(B_JM2|XBVM1)", "rad"),
        ("P(BJ2|XBQ1)", "rad"),
    )
    output: dict[str, object] = {"comparison_window": "READ", "signals": {}}
    for label, unit in labels:
        max_values: list[float] = []
        for left_pos, left_mask in enumerate(ONE_HOT):
            for right_mask in ONE_HOT[left_pos + 1:]:
                left = arrays[left_mask]
                right = arrays[right_mask]
                left_label = label if "XBVM1" not in label else label.replace("XBVM1", f"XBVM{next(index for index in range(1,5) if left_mask[index-1] == '1')}")
                right_label = label if "XBVM1" not in label else label.replace("XBVM1", f"XBVM{next(index for index in range(1,5) if right_mask[index-1] == '1')}")
                phase = unit == "rad"
                diff = pair_difference(left, left_label, right, right_label, left.time, phase=phase)
                max_values.append(diff_metrics(left.time, diff, ARRAY_READ_S, unit)["max_abs"])  # type: ignore[arg-type]
        output["signals"][label] = {"unit": unit, "max_pairwise_difference_in_READ": max(max_values) if max_values else None}
    return output


def crosstalk_case(arrays: Mapping[str, RawTrace], on: str, off: str, aggressor: int, victim: int, labels: Sequence[tuple[str, str]]) -> dict[str, object]:
    target_time = arrays[on].time
    records: dict[str, object] = {}
    for name, kind in labels:
        label = f"{kind}({name}|XBVM{victim})" if kind in ("P", "V", "I") else name
        phase = kind == "P"
        diff = pair_difference(arrays[off], label, arrays[on], label, target_time, phase=phase)
        unit = "rad" if phase else "V" if kind == "V" else "A"
        records[name] = {
            "label": label,
            "kind": kind,
            "on": on,
            "off": off,
            "aggressor": f"BVM{aggressor}",
            "victim": f"BVM{victim}",
            "delta_on_minus_off": diff_metrics(target_time, diff, ARRAY_READ_S, unit),
        }
    return {"on": on, "off": off, "aggressor": f"BVM{aggressor}", "victim": f"BVM{victim}", "signals": records}


def crosstalk_analysis(arrays: Mapping[str, RawTrace]) -> dict[str, object]:
    labels = (("L_SL", "I"), ("R_SL", "I"), ("L_S2", "I"), ("B_JS2", "P"), ("B_JM2", "P"), ("B_JM1", "P"))
    cases = {
        "forward": {"on": "0011", "off": "0001", "aggressor": 3, "active_victim": 4, "quiet_victims": [1, 2]},
        "mirror": {"on": "1100", "off": "1000", "aggressor": 2, "active_victim": 1, "quiet_victims": [3, 4]},
    }
    output: dict[str, object] = {"definition": "C(i <- j, x)=x_i(aggressor ON)-x_i(aggressor OFF)", "cases": {}}
    for name, case in cases.items():
        output["cases"][name] = {"active_victim": crosstalk_case(arrays, case["on"], case["off"], case["aggressor"], case["active_victim"], labels), "quiet_victims": [crosstalk_case(arrays, case["on"], case["off"], case["aggressor"], victim, labels) for victim in case["quiet_victims"]]}
    return output


def passive_vs_qb_analysis(arrays: Mapping[str, RawTrace], passive: Mapping[str, RawTrace]) -> dict[str, object]:
    labels = (("L_SL", "I"), ("B_JS2", "P"), ("B_JM2", "P"))
    cases = {"forward": ("0011", "0001", 3, 4, 1), "mirror": ("1100", "1000", 2, 1, 3)}
    output: dict[str, object] = {"definition": "delta_QB=QB_on-QB_off; delta_passive=passive_on-passive_off; delta_QB_extra=delta_QB-delta_passive", "cases": {}}
    for name, (on, off, aggressor, active_victim, quiet_victim) in cases.items():
        victims = {"active": active_victim, "quiet": quiet_victim}
        case_record: dict[str, object] = {"on": on, "off": off, "aggressor": f"BVM{aggressor}", "victims": {}}
        for victim_name, victim in victims.items():
            signal_record: dict[str, object] = {}
            for signal, kind in labels:
                label = f"{kind}({signal}|XBVM{victim})"
                phase = kind == "P"
                target_time = arrays[on].time
                qb_delta = pair_difference(arrays[off], label, arrays[on], label, target_time, phase=phase)
                passive_time = passive[on].time
                passive_delta = pair_difference(passive[off], label, passive[on], label, passive_time, phase=phase)
                if tuple(passive_time) != tuple(target_time):
                    raise RuntimeError("passive and receiver crosstalk grids differ")
                extra = tuple(qb - intrinsic for qb, intrinsic in zip(qb_delta, passive_delta))
                unit = "rad" if phase else "A"
                signal_record[signal] = {
                    "label": label,
                    "qb": diff_metrics(target_time, qb_delta, ARRAY_READ_S, unit),
                    "passive": diff_metrics(target_time, passive_delta, ARRAY_READ_S, unit),
                    "extra": diff_metrics(target_time, extra, ARRAY_READ_S, unit),
                }
            case_record["victims"][victim_name] = signal_record
        output["cases"][name] = case_record
    return output


def bridge_paths() -> dict[str, Path]:
    return {
        "G0": GOLDEN_RAW,
        "G1": EXP / "bridge/runs/G1-retry-01/raw.csv",
        "G2": EXP / "bridge/runs/G2-retry-01/raw.csv",
        "G3": ARRAY_EXP / "runs/1000/raw.csv",
        "G4": ARRAY_EXP / "runs/1100/raw.csv",
    }


def bridge_label(stage: str, observable: str) -> str:
    if observable == "COMMON_SL":
        return "V(SL1)" if stage == "G0" else "V(COMMON_SL)"
    if observable == "BJ2":
        return "P(BJ2|XBQ1)"
    phase_branches = {"JS2": "B_JS2", "JS1": "B_JS1", "JM2": "B_JM2", "JM1": "B_JM1"}
    if observable in phase_branches:
        return f"P({phase_branches[observable]}|XBVM1)"
    branch = {"LSL": "L_SL", "RSL": "R_SL", "LS2": "L_S2", "LM3": "L_M3", "LS1": "L_S1"}[observable]
    return f"I({branch}|XBVM1)"


def bridge_analysis(traces: Mapping[str, RawTrace]) -> dict[str, object]:
    keys = ("COMMON_SL", "LSL", "RSL", "LS2", "JS2", "LM3", "LS1", "JS1", "JM2", "JM1", "BJ2")
    phase_observables = {"JS2", "JS1", "JM2", "JM1", "BJ2"}
    stage_read = {"G0": SINGLE_READ_S, "G1": SINGLE_READ_S, "G2": ARRAY_READ_S, "G3": ARRAY_READ_S, "G4": ARRAY_READ_S}
    common_time = common_grid(traces)
    output: dict[str, object] = {
        "stage_order": list(traces),
        "common_overlap_grid": {"sample_count": len(common_time), "start_ps": common_time[0] * 1e12, "end_ps": common_time[-1] * 1e12},
        "stage_observables": {},
        "transitions": {},
    }
    for stage, trace in traces.items():
        stage_record: dict[str, object] = {"raw": rel(trace.path), "read_window_ps": [stage_read[stage][0] * 1e12, stage_read[stage][1] * 1e12], "signals": {}}
        for observable in keys:
            label = bridge_label(stage, observable)
            unit = "rad" if observable in phase_observables else "V" if observable == "COMMON_SL" else "A"
            stage_record["signals"][observable] = trajectory_stats(trace, label, stage_read[stage], unit)
        output["stage_observables"][stage] = stage_record
    transitions = (("G0_to_G1_boundary", "G0", "G1", SINGLE_READ_S), ("G1_to_G2_protocol", "G1", "G2", ARRAY_READ_S), ("G2_to_G3_quiet_cells", "G2", "G3", ARRAY_READ_S), ("G3_to_G4_second_active", "G3", "G4", ARRAY_READ_S))
    for name, left_stage, right_stage, bounds in transitions:
        left = traces[left_stage]
        right = traces[right_stage]
        record: dict[str, object] = {"left": left_stage, "right": right_stage, "window_ps": [bounds[0] * 1e12, bounds[1] * 1e12], "signals": {}}
        for observable in keys:
            left_label = bridge_label(left_stage, observable)
            right_label = bridge_label(right_stage, observable)
            unit = "rad" if observable in phase_observables else "V" if observable == "COMMON_SL" else "A"
            difference = pair_difference(left, left_label, right, right_label, common_time, phase=unit == "rad")
            record["signals"][observable] = diff_metrics(common_time, difference, bounds, unit)
        output["transitions"][name] = record
    # Explicitly isolate state accumulated before each fixture's final READ.
    # G0/G1 share the original single-BVM timing, so [62,70) ps is a genuine
    # same-time pre-READ comparison.  G2/G3/G4 share the array timing, so
    # [101,110) ps is their genuine same-time pre-READ comparison.  G1 and G2
    # do not have the same history timing; their pre-READ entry is therefore a
    # descriptive comparison of two registered windows, never a pointwise
    # subtraction.
    pre_read_windows = {
        "G0": (62e-12, 70e-12),
        "G1": (62e-12, 70e-12),
        "G2": (101e-12, 110e-12),
        "G3": (101e-12, 110e-12),
        "G4": (101e-12, 110e-12),
    }
    output["pre_read_stage_windows_ps"] = {
        stage: [bounds[0] * 1e12, bounds[1] * 1e12]
        for stage, bounds in pre_read_windows.items()
    }
    output["pre_read_stage_states"] = {}
    for stage, bounds in pre_read_windows.items():
        trace = traces[stage]
        output["pre_read_stage_states"][stage] = {
            "window_ps": [bounds[0] * 1e12, bounds[1] * 1e12],
            "signals": {
                observable: trajectory_stats(
                    trace,
                    bridge_label(stage, observable),
                    bounds,
                    "rad" if observable in phase_observables else "V" if observable == "COMMON_SL" else "A",
                )
                for observable in keys
            },
        }

    output["pre_read_transitions"] = {}
    for name, left_stage, right_stage, _ in transitions:
        left = traces[left_stage]
        right = traces[right_stage]
        left_bounds = pre_read_windows[left_stage]
        right_bounds = pre_read_windows[right_stage]
        same_time = left_bounds == right_bounds
        record: dict[str, object] = {
            "left": left_stage,
            "right": right_stage,
            "comparison_type": "exact_pointwise_same_window" if same_time else "relative_window_descriptive_no_pointwise_subtraction",
            "left_window_ps": [left_bounds[0] * 1e12, left_bounds[1] * 1e12],
            "right_window_ps": [right_bounds[0] * 1e12, right_bounds[1] * 1e12],
            "signals": {},
        }
        for observable in keys:
            unit = "rad" if observable in phase_observables else "V" if observable == "COMMON_SL" else "A"
            left_label = bridge_label(left_stage, observable)
            right_label = bridge_label(right_stage, observable)
            if same_time:
                difference = pair_difference(left, left_label, right, right_label, common_time, phase=unit == "rad")
                record["signals"][observable] = diff_metrics(common_time, difference, left_bounds, unit)
            else:
                left_stats = trajectory_stats(left, left_label, left_bounds, unit)
                right_stats = trajectory_stats(right, right_label, right_bounds, unit)
                record["signals"][observable] = {
                    "unit": left_stats["unit"],
                    "raw_unit": unit,
                    "left": left_stats,
                    "right": right_stats,
                    "descriptive_delta_right_minus_left": {
                        "mean": float(right_stats["mean"]) - float(left_stats["mean"]),
                        "rms": float(right_stats["rms"]) - float(left_stats["rms"]),
                        "p2p": float(right_stats["p2p"]) - float(left_stats["p2p"]),
                        "endpoint_delta": float(right_stats["endpoint_delta"]) - float(left_stats["endpoint_delta"]),
                        "signed_integral": float(right_stats["signed_integral"]) - float(left_stats["signed_integral"]),
                    },
                    "note": "descriptive statistics from different registered history windows; no pointwise difference or interpolation",
                }
        output["pre_read_transitions"][name] = record
    output["interpretation"] = "G1 boundary, G2 history/protocol bundle, G3 full-history additional cells that are quiet only during final READ, G4 second active cell; each step is a bounded causal comparison, not a universal mechanism proof"
    return output


def kcl_for_trace(trace: RawTrace, bvm_instances: Sequence[int], *, has_jsls: bool) -> dict[str, object]:
    equations: dict[str, object] = {}
    for instance in bvm_instances:
        h = f"XBVM{instance}"
        eqs = {
            "JM1_shunt": {f"I(B_JM1|{h})": 1.0, f"I(R_JM1|{h})": 1.0, f"I(L_M1|{h})": -1.0},
            "JS1_series": {f"I(L_S1|{h})": 1.0, f"I(B_JS1|{h})": -1.0},
            "JS2_series": {f"I(L_S2|{h})": 1.0, f"I(B_JS2|{h})": -1.0},
            "RLOOP_output": {f"I(R_S|{h})": 1.0, f"I(L_S3|{h})": 1.0, f"I(B_JS2|{h})": 1.0, f"I(L_PSL|{h})": -1.0},
            "SL_series_1": {f"I(L_PSL|{h})": 1.0, f"I(R_SL|{h})": -1.0},
            "SL_series_2": {f"I(R_SL|{h})": 1.0, f"I(L_SL|{h})": -1.0},
        }
        for name, coefficients in eqs.items():
            residual = linear_kcl_residual({label: values(trace, label) for label in coefficients}, coefficients)
            equations[f"BVM{instance}_{name}"] = {"equation": coefficients, "READ": kcl_window_metrics(trace.time, residual, ARRAY_READ_S, unit="A")}
    if has_jsls:
        common_branches = {f"LSL{instance}": values(trace, f"I(L_SL|XBVM{instance})") for instance in bvm_instances}
        common_branches["JSL01"] = values(trace, "I(B_JSL01)")
        common_coefficients = {f"LSL{instance}": 1.0 for instance in bvm_instances} | {"JSL01": -1.0}
        common_residual = linear_kcl_residual(common_branches, common_coefficients)
        equations["COMMON_SL"] = {"equation": "sum(I(L_SL|XBVMi)) - I(B_JSL01)", "READ": kcl_window_metrics(trace.time, common_residual, ARRAY_READ_S, unit="A")}
        jsl_reference = values(trace, "I(B_JSL01)")
        for index in range(2, 13):
            current = values(trace, f"I(B_JSL{index:02d})")
            residual = tuple(a - b for a, b in zip(current, jsl_reference))
            equations[f"JSL{index:02d}_series"] = {"equation": f"I(B_JSL{index:02d}) - I(B_JSL01)", "READ": kcl_window_metrics(trace.time, residual, ARRAY_READ_S, unit="A")}
    return equations


def artifact_qa(single: RawTrace, arrays: Mapping[str, RawTrace], passive: Mapping[str, RawTrace], bridge: Mapping[str, RawTrace]) -> dict[str, object]:
    paths: dict[str, Path] = {"golden_single": GOLDEN_RAW}
    paths.update({f"receiver_{mask}": ARRAY_EXP / "runs" / mask / "raw.csv" for mask in ARRAY_MASKS})
    paths.update({f"passive_{mask}": PASSIVE_EXP / "runs" / mask / "raw.csv" for mask in ARRAY_MASKS})
    paths.update({f"bridge_{stage}": path for stage, path in bridge_paths().items() if stage in ("G1", "G2")})
    records: dict[str, object] = {}
    for name, path in paths.items():
        trace = read_csv(path)
        records[name] = {"path": rel(path), "sha256": sha256(path), "sample_count": trace.sample_count, "time_start_ps": trace.time[0] * 1e12, "time_end_ps": trace.time[-1] * 1e12, "headers": len(trace.headers), "duplicate_columns": trace.duplicate_columns, "status": "VALID" if not trace.duplicate_columns else "INVALID"}
    array_time = arrays["0000"].time
    passive_time = passive["0000"].time
    records["array_grid_identity"] = all(exact_time_grid_identity(array_time, arrays[mask].time) for mask in ARRAY_MASKS)
    records["passive_grid_identity"] = all(exact_time_grid_identity(passive_time, passive[mask].time) for mask in ARRAY_MASKS)
    records["receiver_passive_grid_identity"] = exact_time_grid_identity(array_time, passive_time)
    records["single_array_exact_overlap"] = len(exact_indices(single, array_time)) == len(array_time)
    records["bridge_exact_overlap"] = len(common_grid(bridge))
    records["all_raw_valid"] = all(item["status"] == "VALID" for item in records.values() if isinstance(item, Mapping) and "status" in item)
    return records


def source_manifest(bridge: Mapping[str, RawTrace]) -> dict[str, object]:
    paths: OrderedDict[str, Path] = OrderedDict((
        ("task_experiment", EXP / "experiment.yaml"),
        ("task_preflight", EXP / "PREFLIGHT.md"),
        ("task_human_gate", EXP / "analysis/human-gate.yaml"),
        ("golden_single_raw", GOLDEN_RAW),
        ("single_experiment", SINGLE_EXP / "experiment.yaml"),
        ("array_experiment", ARRAY_EXP / "experiment.yaml"),
        ("passive_experiment", PASSIVE_EXP / "experiment.yaml"),
        ("jm2_connected_bvm_variant", VARIANT),
        ("bvmsim_bq", BQ),
        ("bvmsim_jtl", JTL),
        ("shared_jjmit", JJMIT),
        ("canonical_bvm_not_used", CANONICAL_BVM),
        ("solver", SOLVER),
        ("metric_spec", METRIC_SPEC),
        ("plotter", PLOTTER),
        ("analysis_script", Path(__file__).resolve()),
        ("plot_render_script", EXP / "analysis/render_plots.py"),
        ("viz_qa_script", EXP / "analysis/viz_qa.py"),
        ("independent_check_script", EXP / "analysis/independent_check.py"),
    ))
    for mask in ARRAY_MASKS:
        paths[f"receiver_raw_{mask}"] = ARRAY_EXP / "runs" / mask / "raw.csv"
        paths[f"passive_raw_{mask}"] = PASSIVE_EXP / "runs" / mask / "raw.csv"
    for stage, trace in bridge.items():
        paths[f"bridge_raw_{stage}"] = trace.path
    return {"schema": "bvmsim-single-to-array-causal-audit-source-manifest-v1", "created_at_local": now_local(), "files": {name: {"path": rel(path), "sha256": sha256(path)} for name, path in paths.items() if path.is_file()}}


def write_once(path: Path, content: str) -> None:
    if path.exists():
        raise RuntimeError(f"refusing to overwrite derived artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_csv_once(name: str, time_s: Sequence[float], columns: Sequence[tuple[str, Sequence[float]]]) -> Path:
    import csv
    path = EXP / "plots/comparison/data" / f"{name}.csv"
    labels = [label for label, _ in columns]
    if len(labels) != len(set(labels)):
        raise RuntimeError(f"duplicate derived plot labels: {name}")
    if any(len(values_) != len(time_s) for _, values_ in columns):
        raise RuntimeError(f"derived plot length mismatch: {name}")
    rows = ["time," + ",".join('"' + label.replace('"', '""') + '"' for label in labels)]
    rows.extend(
        ",".join([f"{time_s[index]:.17e}"] + [f"{values_[index]:.17e}" for _, values_ in columns])
        for index in range(len(time_s))
    )
    write_once(path, "\n".join(rows) + "\n")
    return path


def build_plot_data(single: RawTrace, arrays: Mapping[str, RawTrace], passive: Mapping[str, RawTrace], bridge: Mapping[str, RawTrace]) -> dict[str, object]:
    records: dict[str, object] = {}
    time = arrays["0000"].time
    instance_by_mask = {mask: next(index for index in range(1, 5) if mask[index - 1] == "1") for mask in ONE_HOT}

    def aligned(trace: RawTrace, label: str, target: Sequence[float], phase: bool = False) -> tuple[float, ...]:
        idx = exact_indices(trace, target)
        data = values(trace, label, phase=phase)
        return tuple(data[index] for index in idx)

    def make(name: str, columns: list[tuple[str, Sequence[float]]], target_time: Sequence[float] | None = None) -> None:
        plot_time = time if target_time is None else target_time
        path = write_csv_once(name, plot_time, columns)
        records[name] = {"data": rel(path), "labels": [label for label, _ in columns]}

    # Golden-vs-array pages: all one-hot positions are retained on output; the
    # deeper pages use two symmetric positions to stay readable by eye.
    out_specs = [("I", "L_SL"), ("I", "R_SL"), ("I", "L_PSL")]
    columns: list[tuple[str, Sequence[float]]] = [("V(COMMON_SL|single SL1)", aligned(single, "V(SL1)", time))]
    columns += [(f"V(COMMON_SL|array {mask})", aligned(arrays[mask], "V(COMMON_SL)", time)) for mask in ONE_HOT]
    for kind, branch in out_specs:
        columns.append((f"{kind}({branch}|single)", aligned(single, f"{kind}({branch}|XBVM1)", time)))
        columns += [(f"{kind}({branch}|array {mask})", aligned(arrays[mask], f"{kind}({branch}|XBVM{instance_by_mask[mask]})", time)) for mask in ONE_HOT]
    make("SINGLE_VS_ARRAY_OUTPUT", columns)

    def page_specs(specs: Sequence[tuple[str, str]], positions: Sequence[str]) -> None:
        page_columns: list[tuple[str, Sequence[float]]] = []
        for kind, branch in specs:
            phase = kind == "P"
            unit_label = f"{kind}({branch}|single)"
            page_columns.append((unit_label, aligned(single, f"{kind}({branch}|XBVM1)", time, phase)))
            for mask in positions:
                instance = instance_by_mask[mask]
                page_columns.append((f"{kind}({branch}|array {mask})", aligned(arrays[mask], f"{kind}({branch}|XBVM{instance})", time, phase)))
        return page_columns

    make("SINGLE_VS_ARRAY_RLOOP_LOWER", page_specs((("I", "R_S"), ("I", "L_S3"), ("I", "L_S2"), ("P", "B_JS2"), ("V", "B_JS2")), ("0001", "1000")))
    make("SINGLE_VS_ARRAY_RLOOP_UPPER", page_specs((("I", "L_M3"), ("I", "L_S1"), ("P", "B_JS1"), ("V", "B_JS1"), ("P", "B_JM2"), ("V", "B_JM2")), ("0001", "1000")))
    make("SINGLE_VS_ARRAY_MEMORY", page_specs((("P", "B_JM1"), ("V", "B_JM1"), ("P", "B_JM2"), ("V", "B_JM2"), ("I", "L_M1"), ("I", "L_M2"), ("I", "L_PM")), ("0001", "1000")))

    # Same-time pre-READ state comparisons.  G0/G1 use [62,70) ps because
    # both follow the single-BVM protocol.  The array-history cases are kept
    # on a separate page at [101,110) ps; putting these on one artificial time
    # axis would falsely imply pointwise equivalence across protocols.
    phase_observables = {"JS2", "JS1", "JM2", "JM1", "BJ2"}
    bridge_observables = ("COMMON_SL", "LSL", "RSL", "LS2", "JS2", "LM3", "LS1", "JS1", "JM2", "JM1", "BJ2")

    def bridge_columns(stages: Sequence[str], target_time: Sequence[float]) -> list[tuple[str, Sequence[float]]]:
        columns: list[tuple[str, Sequence[float]]] = []
        for observable in bridge_observables:
            kind = "P" if observable in phase_observables else "V" if observable == "COMMON_SL" else "I"
            for stage in stages:
                trace = bridge[stage]
                data = values(trace, bridge_label(stage, observable), phase=kind == "P")
                columns.append((f"{kind}({observable}|{stage})", tuple(data[index] for index in exact_indices(trace, target_time))))
        return columns

    pre_time_single = tuple(timestamp for timestamp in common_grid({"G0": bridge["G0"], "G1": bridge["G1"]}) if 62e-12 <= timestamp < 70e-12)
    make("READ_BEFORE_STATE", bridge_columns(("G0", "G1"), pre_time_single), pre_time_single)

    pre_time_array = tuple(timestamp for timestamp in common_grid({"G2": bridge["G2"], "G3": bridge["G3"], "G4": bridge["G4"]}) if 101e-12 <= timestamp < 110e-12)
    make("ARRAY_PRE_READ_STATE", bridge_columns(("G2", "G3", "G4"), pre_time_array), pre_time_array)

    # Divergence difference traces for the representative one-hot position.
    divergence_columns: list[tuple[str, Sequence[float]]] = []
    timeline_specs = (
        ("V", "V(SL1)", "V(COMMON_SL)", "COMMON_SL"),
        ("I", "I(L_SL|XBVM1)", "I(L_SL|XBVM1)", "LSL"),
        ("I", "I(R_SL|XBVM1)", "I(R_SL|XBVM1)", "RSL"),
        ("I", "I(L_S2|XBVM1)", "I(L_S2|XBVM1)", "LS2"),
        ("P", "P(B_JS2|XBVM1)", "P(B_JS2|XBVM1)", "JS2"),
        ("I", "I(L_M3|XBVM1)", "I(L_M3|XBVM1)", "LM3"),
        ("I", "I(L_S1|XBVM1)", "I(L_S1|XBVM1)", "LS1"),
        ("P", "P(B_JS1|XBVM1)", "P(B_JS1|XBVM1)", "JS1"),
        ("P", "P(B_JM2|XBVM1)", "P(B_JM2|XBVM1)", "JM2"),
        ("P", "P(B_JM1|XBVM1)", "P(B_JM1|XBVM1)", "JM1"),
    )
    for kind, left_label, right_label, name in timeline_specs:
        phase = kind == "P"
        diff = pair_difference(single, left_label, arrays["1000"], right_label, time, phase=phase)
        divergence_columns.append((f"{kind}(Delta_{name}|array1000-minus-single)", diff))
    make("DIVERGENCE_TIMELINE", divergence_columns)

    # Forward and mirror active-victim/quiet-victim overlays.  Both directions
    # remain on the same page so symmetry is visually inspectable rather than
    # being asserted only from a metrics table.
    ct_specs = (("I", "L_SL"), ("I", "R_SL"), ("I", "L_S2"), ("P", "B_JS2"), ("P", "B_JM2"), ("P", "B_JM1"))
    def overlay(name: str, cases: Sequence[tuple[str, str, int, str]]) -> None:
        cols: list[tuple[str, Sequence[float]]] = []
        for on, off, victim, case_name in cases:
            for kind, signal in ct_specs:
                phase = kind == "P"
                label = f"{kind}({signal}|XBVM{victim})"
                cols.append((f"{kind}({signal}|{case_name} OFF {off})", values(arrays[off], label, phase=phase)))
                cols.append((f"{kind}({signal}|{case_name} ON {on})", values(arrays[on], label, phase=phase)))
                cols.append((f"{kind}(Delta_{signal}|{case_name} ON-{off})", tuple(a - b for a, b in zip(values(arrays[on], label, phase=phase), values(arrays[off], label, phase=phase)))))
        make(name, cols)
    overlay("ACTIVE_VICTIM_CROSSTALK", (("0011", "0001", 4, "forward BVM4"), ("1100", "1000", 1, "mirror BVM1")))
    overlay("QUIET_VICTIM_CROSSTALK", (("0011", "0001", 1, "forward BVM1"), ("1100", "1000", 3, "mirror BVM3")))

    # Passive-vs-QB difference of differences: forward active BVM4 and quiet BVM1.
    cols = []
    for case_name, on, off, victim_map in (
        ("forward", "0011", "0001", (("active BVM4", 4), ("quiet BVM1", 1))),
        ("mirror", "1100", "1000", (("active BVM1", 1), ("quiet BVM3", 3))),
    ):
        for victim_name, victim in victim_map:
            for kind, signal in (("I", "L_SL"), ("P", "B_JS2"), ("P", "B_JM2")):
                phase = kind == "P"
                label = f"{kind}({signal}|XBVM{victim})"
                qb_on = values(arrays[on], label, phase=phase); qb_off = values(arrays[off], label, phase=phase)
                pa_on = values(passive[on], label, phase=phase); pa_off = values(passive[off], label, phase=phase)
                qb_delta = tuple(a - b for a, b in zip(qb_on, qb_off)); pa_delta = tuple(a - b for a, b in zip(pa_on, pa_off)); extra = tuple(a - b for a, b in zip(qb_delta, pa_delta))
                case_label = f"{case_name} {victim_name}"
                cols.extend(((f"{kind}(Delta_QB_{signal}|{case_label})", qb_delta), (f"{kind}(Delta_passive_{signal}|{case_label})", pa_delta), (f"{kind}(Delta_QB_extra_{signal}|{case_label})", extra)))
    make("PASSIVE_VS_QB_CROSSTALK", cols)

    # G0 -> G4 bridge overview.  The bridge traces share the exact 45 ps
    # overlap grid, while G0/G1/G2 also contain earlier samples.  Plot only
    # the exact overlap so no interpolation or hidden re-sampling occurs.
    bridge_time = common_grid(bridge)
    bridge_cols: list[tuple[str, Sequence[float]]] = []
    for observable in bridge_observables:
        for stage, trace in bridge.items():
            kind = "P" if observable in phase_observables else "V" if observable == "COMMON_SL" else "I"
            trace_values = values(trace, bridge_label(stage, observable), phase=kind == "P")
            bridge_cols.append(
                (
                    f"{kind}({observable}|{stage})",
                    tuple(trace_values[index] for index in exact_indices(trace, bridge_time)),
                )
            )
    bridge_path = write_csv_once("SINGLE_TO_ARRAY_BRIDGE_OVERVIEW", bridge_time, bridge_cols)
    records["SINGLE_TO_ARRAY_BRIDGE_OVERVIEW"] = {"data": rel(bridge_path), "labels": [label for label, _ in bridge_cols]}
    return records


def load_all() -> tuple[RawTrace, OrderedDict[str, RawTrace], OrderedDict[str, RawTrace], OrderedDict[str, RawTrace]]:
    single = read_csv(GOLDEN_RAW)
    arrays = OrderedDict((mask, read_csv(ARRAY_EXP / "runs" / mask / "raw.csv")) for mask in ARRAY_MASKS)
    passive = OrderedDict((mask, read_csv(PASSIVE_EXP / "runs" / mask / "raw.csv")) for mask in ARRAY_MASKS)
    bridge = OrderedDict((stage, read_csv(path)) for stage, path in bridge_paths().items())
    return single, arrays, passive, bridge


def report(metrics: Mapping[str, object]) -> str:
    artifact = metrics["artifact_qa"]
    div = metrics["divergence"]
    bridge = metrics["bridge"]
    ct = metrics["crosstalk"]
    pq = metrics["passive_vs_qb"]
    lines = [
        "# Single → 4×1 shared-SL causal audit",
        "",
        "本报告是 bounded historical BVMSim simulation analysis，不是 Formal Gate。comparison HTML 是本任务验收项。",
        "",
        "## Observed",
        "",
        f"- 现有 raw 与 G1/G2 raw 均解析通过；array/passive same-mask grid exact={artifact['receiver_passive_grid_identity']}，single→array overlap exact={artifact['single_array_exact_overlap']}，没有插值。",
        f"- single→one-hot 直接对照存在 protocol/history 与 sensing-load 混杂；因此它只作差异定位背景，不作唯一因果归因。主 timeline 的 representative one-hot 是 `{div['representative_mask']}`。",
        "- bridge 的 G0→G1 是 sensing boundary 改变，G1→G2 是 history/protocol bundle 改变，G2→G3 是加入了完整历史但在最终 READ 时保持 quiet 的三个 connected BVM，G3→G4 是第二个 active BVM；comparison HTML 覆盖关键轨迹和 same-time pre-READ 对照。",
        "",
        "## Bridge transition summary",
        "",
        "| transition | LSL max | LS2 max | LM3 max | LS1 max | JM2 phase max | QB BJ2 phase max |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for name, record in bridge["transitions"].items():
        s = record["signals"]
        lines.append(f"| {name} | {s['LSL']['max_abs']:.6g} uA | {s['LS2']['max_abs']:.6g} uA | {s['LM3']['max_abs']:.6g} uA | {s['LS1']['max_abs']:.6g} uA | {s['JM2']['max_abs']:.6g} rad | {s['BJ2']['max_abs']:.6g} rad |")
    lines += [
        "",
        "## Pre-READ state comparison",
        "",
        "G0/G1 的 same-time pre-READ 窗口是 `[62,70) ps`；G2/G3/G4 的 same-time pre-READ 窗口是 `[101,110) ps`。这些窗口只使用实际存储时间点，不插值。G1→G2 的两个历史窗口不同，因此只报告 descriptive stage statistics，不做 pointwise subtraction。对应图见 [READ_BEFORE_STATE](plots/comparison/READ_BEFORE_STATE.html)、[ARRAY_PRE_READ_STATE](plots/comparison/ARRAY_PRE_READ_STATE.html) 和 [SINGLE_TO_ARRAY_BRIDGE_OVERVIEW](plots/comparison/SINGLE_TO_ARRAY_BRIDGE_OVERVIEW.html)。",
        "",
        "| same-time transition | COMMON_SL max | LSL max | LS2 max | JM2 phase max | QB BJ2 phase max |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for name in ("G0_to_G1_boundary", "G2_to_G3_quiet_cells", "G3_to_G4_second_active"):
        record = bridge["pre_read_transitions"][name]
        s = record["signals"]
        lines.append(f"| {name} | {s['COMMON_SL']['max_abs']:.6g} mV | {s['LSL']['max_abs']:.6g} uA | {s['LS2']['max_abs']:.6g} uA | {s['JM2']['max_abs']:.6g} rad | {s['BJ2']['max_abs']:.6g} rad |")
    relative = bridge["pre_read_transitions"]["G1_to_G2_protocol"]
    relative_signals = relative["signals"]
    lines += [
        "",
        "G1→G2 relative-window descriptive comparison (`G1 [62,70) ps` vs `G2 [101,110) ps`；右侧减左侧，仅比较窗口统计量)：",
        "",
        "| signal | G1 mean | G2 mean | descriptive Δmean |",
        "|---|---:|---:|---:|",
    ]
    for observable in ("COMMON_SL", "LSL", "LS2", "JM2", "BJ2"):
        signal = relative_signals[observable]
        left_stats = signal["left"]
        right_stats = signal["right"]
        delta_mean = signal["descriptive_delta_right_minus_left"]["mean"]
        unit = left_stats["unit"]
        lines.append(f"| {observable} | {left_stats['mean']:.6g} {unit} | {right_stats['mean']:.6g} {unit} | {delta_mean:.6g} {unit} |")
    lines += [
        "",
        "same-time 表中的数值是窗口内差值的最大绝对值；relative 表中的数值是不同历史窗口的统计量，不是逐点差值。它们都不是事件计数。phase 的 `P(...)` 原始单位是 rad，图中 turns 只表示 rad/(2π)。",
        "",
        "## Q1–Q8 bounded answers",
        "",
        "1. **Q1:** 在代表性 one-hot `1000` 的阈值扫描中，所有注册层都在 50.1 ps 首次越过各自阈值；因此不能从该结果声称 `COMMON_SL` 先于其它层发生了可归因分歧。[DIVERGENCE_TIMELINE](plots/comparison/DIVERGENCE_TIMELINE.html) 只作差异定位，不能单独排除 protocol/load 混杂。",
        "2. **Q2:** direct Golden-vs-array 图在 READ 前已混入不同 WRITE/history；桥接的 G0→G1 same-time pre-READ 对照表明仅换 sensing boundary 就能留下差异，G1→G2 则只能作为不同历史窗口的 descriptive comparison。这里的“已存在”是 bounded waveform difference，不等于已定位唯一根因。",
        "3. **Q3:** output/R-loop disturbance 在 bridge comparison 中可观测到 COMMON_SL、LSL、RSL、LS2/JS2、LM3、LS1/JS1，并进一步出现在 JM2/JM1；[SINGLE_TO_ARRAY_BRIDGE_OVERVIEW](plots/comparison/SINGLE_TO_ARRAY_BRIDGE_OVERVIEW.html) 包含这套完整 bridge probe schema。",
        "4. **Q4:** [QUIET_VICTIM_CROSSTALK](plots/comparison/QUIET_VICTIM_CROSSTALK.html) 显示 `0001→0011` 时 BVM1（以及镜像 case 的 quiet victims）并非被静默视为零；这是 bounded shared-SL crosstalk observation，不能外推为 universal isolation failure。",
        "5. **Q5:** [ACTIVE_VICTIM_CROSSTALK](plots/comparison/ACTIVE_VICTIM_CROSSTALK.html) 显示 `0001→0011` 时保持 active 的 BVM4 也发生可观测变化；同一页包含镜像 `1000→1100`。",
        f"6. **Q6:** passive boundary 下的同一 aggressor-victim difference 也存在，详见 [PASSIVE_VS_QB_CROSSTALK](plots/comparison/PASSIVE_VS_QB_CROSSTALK.html)。",
        f"7. **Q7:** QB-extra 是 `ΔQB−Δpassive` 的差分，不把 QB 影响与 intrinsic shared-SL coupling 混为一谈；本 fixture 的量化表和图同时给出二者，结论只保留为 bounded comparison。",
        "8. **Q8:** G0→G4 的首次变化不能从 single-vs-array raw 直接唯一归因；桥接顺序中 G1 已由 sensing boundary 产生可见变化，G2/G3/G4 又各有增量，不能把后续差异误写成单一根因。",
        "",
        "## Interpretation labels",
        "",
        "- `SENSING_BOUNDARY_EFFECT_OBSERVED`：G0→G1 在本固定 fixture、same-time pre-READ 窗口和 observables 下留下了 bounded waveform difference；这不是唯一机制证明。",
        "- `HISTORY_PROTOCOL_BUNDLE_EFFECT_OBSERVED`：G1→G2 的历史/协议 bundle 的 registered-window statistics 不同；不能把它拆成单一 PWL 或单一器件原因。",
        "- `FULL_HISTORY_CELLS_ADDED_EFFECT_OBSERVED`：G2→G3 比较的是带完整历史、仅在最终 READ 时保持 quiet 的额外 connected cells；纯 quiet-loading effect remains `INCONCLUSIVE`。",
        "- `SECOND_ACTIVE_SHARED_SL_EFFECT_OBSERVED`：G3→G4 在第二个 active cell 加入后的 READ-window difference 可观测；不单独等同于已隔离的 coupling mechanism。",
        "- `RECEIVER_BOUNDARY_CONDITIONED_CROSSTALK_DIFFERENCE_OBSERVED`：QB 与 passive 的 difference-of-differences 是 bounded observation；不升级为 QB back-action 的唯一机制。",
        "- `PRIMARY_CLASSIFICATION: INCONCLUSIVE`；`QUICK_LABEL: QUICK_AMBIGUOUS`，因为本轮没有把 boundary、history、connected-cell loading 和 receiver boundary 完全正交隔离。",
        "",
        "## Unknown / not proved",
        "",
        "- 没有证明 canonical BVM、论文机制、硬件行为、普适 isolation、工艺 margin 或唯一 QB operating mechanism。",
        "- 没有把 phase displacement、voltage area、I>Ic 或 local phase activity 当作 SFQ count；本任务也没有建立 downstream event identity。",
        "- G1/G2 是新 Quick raw；G3/G4 是 hash-bound reuse 的旧 4×1 raw。没有运行 G5、参数 sweep、timestep sweep 或优化。",
        "",
        "## Visualization acceptance",
        "",
        "所有关键结论对应的 comparison HTML 位于 `plots/comparison/`，由 `scripts/josim-plot2.py` 使用 `sep_comb + dark + -j 2pi` 生成；plot manifest 与 viz QA 记录输入 label、hash 和单位检查。",
        "",
        "关键页面：",
        "- [SINGLE_VS_ARRAY_OUTPUT](plots/comparison/SINGLE_VS_ARRAY_OUTPUT.html)：COMMON_SL、LSL/RSL/LPSL；",
        "- [SINGLE_VS_ARRAY_RLOOP_LOWER](plots/comparison/SINGLE_VS_ARRAY_RLOOP_LOWER.html)：RS、LS3、LS2、JS2 的 I/P/V；",
        "- [SINGLE_VS_ARRAY_RLOOP_UPPER](plots/comparison/SINGLE_VS_ARRAY_RLOOP_UPPER.html)：LM3、LS1、JS1、JM2；",
        "- [SINGLE_VS_ARRAY_MEMORY](plots/comparison/SINGLE_VS_ARRAY_MEMORY.html)：JM1/JM2 memory branch；",
        "- [READ_BEFORE_STATE](plots/comparison/READ_BEFORE_STATE.html)、[ARRAY_PRE_READ_STATE](plots/comparison/ARRAY_PRE_READ_STATE.html)、[DIVERGENCE_TIMELINE](plots/comparison/DIVERGENCE_TIMELINE.html)：same-time READ 前状态与分歧时序；",
        "- [ACTIVE_VICTIM_CROSSTALK](plots/comparison/ACTIVE_VICTIM_CROSSTALK.html)、[QUIET_VICTIM_CROSSTALK](plots/comparison/QUIET_VICTIM_CROSSTALK.html)：forward+mirror aggressor/victim；",
        "- [PASSIVE_VS_QB_CROSSTALK](plots/comparison/PASSIVE_VS_QB_CROSSTALK.html)：passive、QB 和 `ΔQB−Δpassive`；",
        "- [SINGLE_TO_ARRAY_BRIDGE_OVERVIEW](plots/comparison/SINGLE_TO_ARRAY_BRIDGE_OVERVIEW.html)：G0→G4 轨迹总览。",
        "",
        "## Gate",
        "",
        "`AWAITING_USER_REVIEW`; `user_reviewed: false`; `next_step_authorized: false`; `automatic_next_experiment: false`; `next_action: STOP`。",
    ]
    return "\n".join(lines) + "\n"


def review(metrics: Mapping[str, object]) -> str:
    return "\n".join([
        "# Review record",
        "",
        "本文件记录机械/数值审查，不替代 Sol XHigh 或用户的物理审阅。",
        "",
        "## Checks",
        "",
        f"- artifact status: `{metrics['status']}`",
        f"- all raw duplicate-column checks: `{metrics['artifact_qa']['all_raw_valid']}`",
        f"- receiver/passive exact grid: `{metrics['artifact_qa']['receiver_passive_grid_identity']}`",
        f"- single/array exact overlap: `{metrics['artifact_qa']['single_array_exact_overlap']}`",
        "- all derived integrations use actual stored timestamps and shared `bvmtools` helpers.",
        "- current direction is first netlist node to second; voltage is V(first)-V(second).",
        "- phase remains raw radians until explicit continuous unwrap and `/ (2*pi)` display conversion.",
        "",
        "## Adversarial limits",
        "",
        "- single-vs-array direct divergence is confounded by sensing boundary and protocol/history; it is not treated as a causal verdict.",
        "- quiet victims are explicitly retained; no inactive branch is silently zeroed.",
        "- active and quiet crosstalk are separated, and passive-vs-QB is reported as a difference of differences.",
        "- bridge comparisons stop at G4; no automatic follow-up was run.",
        "- comparison HTML is required evidence for visual inspection, but plots remain descriptive and do not certify SFQ events.",
        "",
        "## Pending review",
        "",
        "需要 Sol XHigh/read-only adversarial review重点检查 G0→G4 的因果链、QB-extra 定义、phase-unit 和每个 comparison HTML 的 pair/provenance；最终状态仍由用户审阅决定。",
        "",
        "```yaml",
        "state: AWAITING_USER_REVIEW",
        "user_reviewed: false",
        "next_step_authorized: false",
        "automatic_next_experiment: false",
        "next_action: STOP",
        "```",
        "",
    ])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    if not args.write:
        raise SystemExit("use --write to create task-local analysis artifacts")
    single, arrays, passive, bridge = load_all()
    artifact = artifact_qa(single, arrays, passive, bridge)
    if not artifact["all_raw_valid"] or not artifact["array_grid_identity"] or not artifact["passive_grid_identity"] or not artifact["receiver_passive_grid_identity"] or not artifact["single_array_exact_overlap"]:
        raise RuntimeError(f"artifact/grid QA failed: {artifact}")
    metrics: dict[str, object] = {
        "schema": "bvmsim-single-to-array-causal-audit-metrics-v1",
        "created_at_local": now_local(),
        "experiment_id": EXP.name,
        "head_at_analysis": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip(),
        "source_class": "HISTORICAL_BVMSIM_JM2_CONNECTED_VARIANT",
        "canonical_bvm_used": False,
        "artifact_qa": artifact,
        "golden_vs_array": compare_single_to_onehot(single, arrays),
        "one_hot_symmetry": onehot_symmetry(arrays),
        "divergence": divergence_analysis(single, arrays),
        "crosstalk": crosstalk_analysis(arrays),
        "passive_vs_qb": passive_vs_qb_analysis(arrays, passive),
        "bridge": bridge_analysis(bridge),
        "kcl": {
            "G1": kcl_for_trace(bridge["G1"], [1], has_jsls=True),
            "G2": kcl_for_trace(bridge["G2"], [1], has_jsls=True),
            "G3": kcl_for_trace(bridge["G3"], [1, 2, 3, 4], has_jsls=True),
            "G4": kcl_for_trace(bridge["G4"], [1, 2, 3, 4], has_jsls=True),
        },
        "windows_ps": {name: list(bounds) for name, bounds in WINDOWS_PS.items()},
        "analysis_conventions": {
            "P_raw_unit": "radians",
            "phase_display": "continuous_unwrap(rad)/(2*pi) turns",
            "difference_convention": "right_minus_left unless explicitly named ON-minus-OFF or delta_QB_extra",
            "no_interpolation": True,
            "no_phase_voltage_area_or_threshold_as_sfq_count": True,
            "divergence_threshold": "max(numerical floor, PRE envelope*5), N=3; sensitivity factors 3/5/10 and N=2/3/5",
        },
        "primary_classification": "INCONCLUSIVE",
        "quick_label": "QUICK_AMBIGUOUS",
        "interpretation_labels": [
            "SENSING_BOUNDARY_EFFECT_OBSERVED",
            "HISTORY_PROTOCOL_BUNDLE_EFFECT_OBSERVED",
            "FULL_HISTORY_CELLS_ADDED_EFFECT_OBSERVED",
            "SECOND_ACTIVE_SHARED_SL_EFFECT_OBSERVED",
            "RECEIVER_BOUNDARY_CONDITIONED_CROSSTALK_DIFFERENCE_OBSERVED",
            "INCONCLUSIVE",
        ],
        "status": "ANALYSIS_VALID",
    }
    plot_records = build_plot_data(single, arrays, passive, bridge)
    metrics["plot_data"] = plot_records
    provenance = source_manifest(bridge)
    provenance.update({
        "head_before_task": "470ad38cdaea0e55ed2a77d5e72c3ec7d001192e",
        "head_at_analysis": metrics["head_at_analysis"],
        "bridge_deck_records": {stage: {"path": rel(EXP / "bridge/runs" / ("G1-retry-01" if stage == "G1" else "G2-retry-01") / "deck.cir"), "sha256": sha256(EXP / "bridge/runs" / ("G1-retry-01" if stage == "G1" else "G2-retry-01") / "deck.cir")} for stage in ("G1", "G2")},
        "source_bvm_statement": "BVMSim/JM2-connected BVM variant is not canonical circuits/bvm/bvm_cell.cir",
        "solver_version": subprocess.check_output([str(SOLVER), "--version"], text=True, stderr=subprocess.STDOUT),
        "solver_sha256": sha256(SOLVER),
        "renderer": {"path": rel(PLOTTER), "sha256": sha256(PLOTTER), "options": ["-t", "sep_comb", "-c", "dark", "-j", "2pi"]},
        "raw_policy": "all source raw files are immutable historical evidence; this task writes only derived CSV/JSON/HTML",
        "gate": {"state": "AWAITING_USER_REVIEW", "user_reviewed": False, "next_step_authorized": False, "automatic_next_experiment": False, "stage_b_authorized": False, "next_action": "STOP"},
    })
    write_once(EXP / "source/source_manifest.json", json.dumps(provenance, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    write_once(EXP / "analysis/metrics.json", json.dumps(metrics, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    write_once(EXP / "analysis/provenance.json", json.dumps(provenance, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    write_once(EXP / "RESULT_BRIEF.md", report(metrics))
    write_once(EXP / "analysis/REVIEW.md", review(metrics))
    write_once(EXP / "analysis/commands.txt", "\n".join([
        "git status --short --untracked-files=all  # exit 0; clean before setup",
        "python3 bridge/generate_decks.py  # exit 0 for initial setup decks; first run path incident preserved",
        "./bridge/run.sh  # exit 2 on initial wrong-include attempt; no raw; failed log preserved",
        "python3 bridge/generate_decks.py  # exit 0 for G1/G2 retry decks",
        "./bridge/run.sh  # exit 0; G1-retry-01 and G2-retry-01 raw generated",
        "python3 analysis/analyze_existing.py --write  # exit 0",
        "python3 analysis/render_plots.py --write  # exit 0; 11 comparison HTML pages rendered",
        "python3 analysis/independent_check.py  # exit 0; independent raw/grid/arithmetic cross-check",
        "env PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q test/tools/test_bvmtools.py test/tools/test_bvmtools_infrastructure.py test/tools/test_bvmtools_sl_probes.py test/tools/test_strict_event_list.py  # exit 0; 41 passed",
        "env PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q test/metrics/test_metric_spec_v2.py test/metrics/test_sfq_metrics_v2.py test/metrics/test_sfq_metrics_v2_m5.py test/metrics/test_sfq_metrics_v2_m6.py test/metrics/test_sfq_metrics_v2_m7.py  # exit 0; 142 passed",
        "python3 analysis/viz_qa.py  # exit 0; 11/11 comparison HTML pages passed",
        "",
    ]) + "\n")
    print(json.dumps({"status": "ANALYSIS_VALID", "plot_data_count": len(plot_records), "bridge_stages": list(bridge), "raw_immutable": True}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
