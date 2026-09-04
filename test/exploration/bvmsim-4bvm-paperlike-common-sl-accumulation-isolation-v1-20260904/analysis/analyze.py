#!/usr/bin/env python3
"""Analyze the fixed common-SL topology experiment.

The task-local code owns mask semantics and interpretation.  Raw parsing,
phase unwrapping, waveform arithmetic, comparison, KCL and strict local
event semantics come from the shared bvmtools modules.  No QB/JTL signal is
read by this analyzer.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, Sequence


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
OLD_EXP = REPO / "test/exploration/bvmsim-4bvm-allone-selective-read-additivity-isolation-v1-20260904"
METRIC_SPEC = REPO / "docs/research/METRIC_SPEC_V2.md"
SOLVER = REPO / "build/josim-cli"
MASKS = ("0000", "0001", "0010", "0100", "1000", "0011", "0111", "1100", "1110", "1111")
ONE_HOT = ("0001", "0010", "0100", "1000")
ONE_HOT_BY_INSTANCE = {1: "1000", 2: "0100", 3: "0010", 4: "0001"}
FORWARD = ("1100", "1110", "1111")
REVERSE = ("0011", "0111", "1111")
WINDOWS_PS = OrderedDict(
    (
        ("PRE", (45.0, 50.0)),
        ("WRITE0", (50.0, 70.0)),
        ("NO_HISTORY_READ", (70.0, 90.0)),
        ("WRITE1_ALL", (90.0, 101.0)),
        ("SETTLE", (101.0, 110.0)),
        ("READ", (110.0, 170.0)),
        ("TAIL", (170.0, 200.0)),
    )
)
WINDOWS = OrderedDict((name, (left * 1e-12, right * 1e-12)) for name, (left, right) in WINDOWS_PS.items())
READ = WINDOWS["READ"]
SETTLE = WINDOWS["SETTLE"]
TAIL = WINDOWS["TAIL"]
PLATEAU_WRITE0 = (51e-12, 60e-12)
PLATEAU_WRITE1 = (91e-12, 100e-12)
PLATEAU_READ = (111e-12, 120e-12)
PLATEAU_TOLERANCE_A = 0.1e-6
JJ_NAMES = ("B_JM1", "B_JM2", "B_JS1", "B_JS2")
KCL_BRANCHES = OrderedDict(
    (
        ("JM1_shunt", ("B_JM1", "R_JM1", "L_M1")),
        ("SE_RLOOP", ("B_JS1", "L_PSE", "R_S", "L_S3")),
        ("RLOOP_output", ("R_S", "L_S3", "B_JS2", "L_PSL")),
        ("SL_series_1", ("L_PSL", "R_SL")),
        ("SL_series_2", ("R_SL", "L_SL")),
    )
)

sys.path.insert(0, str(REPO / "scripts"))
from bvmtools.compare import compare_series, exact_time_grid_identity  # noqa: E402
from bvmtools.kcl import kcl_window_metrics, linear_kcl_residual  # noqa: E402
from bvmtools.metrics import phase_area_window  # noqa: E402
from bvmtools.phase import TAU, continuous_unwrap, phase_window_metrics, window_indices  # noqa: E402
from bvmtools.raw import RawTrace, read_csv  # noqa: E402
from bvmtools.sfq import StrictLocalEventSpec, strict_event_list  # noqa: E402
from bvmtools.stimulus import validate_expected_plateau  # noqa: E402
from bvmtools.waveform import trapezoid_integral, waveform_metrics, waveform_window_metrics  # noqa: E402


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO.resolve()).as_posix()


def values(trace: RawTrace, label: str) -> tuple[float, ...]:
    return trace.column(label)  # type: ignore[return-value]


def selected_indices(trace: RawTrace, bounds: tuple[float, float]) -> tuple[int, ...]:
    indices = window_indices(trace.time, *bounds)
    if len(indices) < 2:
        raise RuntimeError(f"window has fewer than two samples: {bounds}")
    return indices


def wstats(trace: RawTrace, label: str, bounds: tuple[float, float], unit: str) -> dict[str, object]:
    result = dict(waveform_window_metrics(trace.time, values(trace, label), bounds, unit=unit))
    result["label"] = label
    result["raw_unit"] = unit
    return result


def vstats(time_s: Sequence[float], vector: Sequence[float], bounds: tuple[float, float], unit: str) -> dict[str, object]:
    result = dict(waveform_window_metrics(time_s, vector, bounds, unit=unit))
    result["raw_unit"] = unit
    return result


def phase_turns(trace: RawTrace, label: str) -> tuple[float, ...]:
    return tuple(value / TAU for value in continuous_unwrap(values(trace, label)))


def phase_stats(trace: RawTrace, label: str, bounds: tuple[float, float]) -> dict[str, object]:
    result = dict(phase_window_metrics(trace.time, values(trace, label), bounds))
    result["label"] = label
    return result


def phase_delta_stats(left: RawTrace, right: RawTrace, label: str, bounds: tuple[float, float]) -> dict[str, object]:
    if not exact_time_grid_identity(left.time, right.time):
        raise RuntimeError(f"phase delta requires exact grid identity: {label}")
    delta = tuple(a - b for a, b in zip(phase_turns(left, label), phase_turns(right, label)))
    result = vstats(left.time, delta, bounds, "raw")
    result.update({"label": label, "raw_unit": "turns", "display_unit": "turns", "phase_conversion": "difference of continuous_unwrap(rad)/(2*pi)"})
    return result


def grid_record(trace: RawTrace) -> dict[str, object]:
    return {
        "sample_count": trace.sample_count,
        "time_start_ps": trace.time[0] * 1e12,
        "time_last_sample_ps": trace.time[-1] * 1e12,
        "dt_min_ps": min(trace.dt) * 1e12,
        "dt_max_ps": max(trace.dt) * 1e12,
        "uniform_exact": all(value == trace.dt[0] for value in trace.dt),
        "interpolation": "none",
    }


def protocol_record(trace: RawTrace, mask: str) -> dict[str, object]:
    per_bvm: dict[str, object] = {}
    statuses: list[str] = []
    for instance in range(1, 5):
        labels = {control: f"I(I_{control}{instance})" for control in ("WL", "BL", "SE")}
        checks: dict[str, object] = {}
        checks["WRITE0_WL"] = validate_expected_plateau(trace.time, values(trace, labels["WL"]), PLATEAU_WRITE0, -100e-6, tolerance=PLATEAU_TOLERANCE_A, unit="A")
        checks["WRITE0_BL"] = validate_expected_plateau(trace.time, values(trace, labels["BL"]), PLATEAU_WRITE0, -100e-6, tolerance=PLATEAU_TOLERANCE_A, unit="A")
        checks["WRITE1_WL"] = validate_expected_plateau(trace.time, values(trace, labels["WL"]), PLATEAU_WRITE1, 100e-6, tolerance=PLATEAU_TOLERANCE_A, unit="A")
        checks["WRITE1_BL"] = validate_expected_plateau(trace.time, values(trace, labels["BL"]), PLATEAU_WRITE1, 100e-6, tolerance=PLATEAU_TOLERANCE_A, unit="A")
        expected_read = 100e-6 if mask[instance - 1] == "1" else 0.0
        checks["READ_WL"] = validate_expected_plateau(trace.time, values(trace, labels["WL"]), PLATEAU_READ, expected_read, tolerance=PLATEAU_TOLERANCE_A, unit="A")
        checks["READ_SE"] = validate_expected_plateau(trace.time, values(trace, labels["SE"]), PLATEAU_READ, expected_read, tolerance=PLATEAU_TOLERANCE_A, unit="A")
        checks["READ_BL"] = validate_expected_plateau(trace.time, values(trace, labels["BL"]), PLATEAU_READ, 0.0, tolerance=PLATEAU_TOLERANCE_A, unit="A")
        checks["NO_HISTORY_WL"] = validate_expected_plateau(trace.time, values(trace, labels["WL"]), WINDOWS["NO_HISTORY_READ"], 0.0, tolerance=PLATEAU_TOLERANCE_A, unit="A")
        checks["NO_HISTORY_BL"] = validate_expected_plateau(trace.time, values(trace, labels["BL"]), WINDOWS["NO_HISTORY_READ"], 0.0, tolerance=PLATEAU_TOLERANCE_A, unit="A")
        checks["NO_HISTORY_SE"] = validate_expected_plateau(trace.time, values(trace, labels["SE"]), WINDOWS["NO_HISTORY_READ"], 0.0, tolerance=PLATEAU_TOLERANCE_A, unit="A")
        statuses.extend(str(item["status"]) for item in checks.values())  # type: ignore[index]
        per_bvm[f"BVM{instance}"] = checks
    return {"status": "PROTOCOL_VALID" if all(item == "PASS" for item in statuses) else "PROTOCOL_INVALID", "mask": mask, "per_bvm": per_bvm}


def state_record(trace: RawTrace) -> dict[str, object]:
    per_bvm: dict[str, object] = {}
    for instance in range(1, 5):
        hierarchy = f"XBVM{instance}"
        per_bvm[f"BVM{instance}"] = {
            "stored_state_settle": {name: phase_stats(trace, f"P({name}|{hierarchy})", SETTLE) for name in ("B_JM1", "B_JM2")},
            "read_junctions": {
                name: {
                    "phase": phase_stats(trace, f"P({name}|{hierarchy})", READ),
                    "voltage": wstats(trace, f"V({name}|{hierarchy})", READ, "V"),
                    "current": wstats(trace, f"I({name}|{hierarchy})", READ, "A"),
                }
                for name in JJ_NAMES
            },
        }
    return {"per_bvm": per_bvm}


def output_record(trace: RawTrace) -> dict[str, object]:
    per_bvm: dict[str, object] = {}
    for instance in range(1, 5):
        hierarchy = f"XBVM{instance}"
        per_bvm[f"BVM{instance}"] = {
            "current": {name: wstats(trace, f"I({name}|{hierarchy})", READ, "A") for name in ("L_PSL", "R_SL", "L_SL")},
            "voltage": {name: wstats(trace, f"V({name}|{hierarchy})", READ, "V") for name in ("L_PSL", "R_SL", "L_SL")},
        }
    return {"per_bvm": per_bvm}


def strict_load_spec(mask: str, index: int, raw_hash: str) -> StrictLocalEventSpec:
    return StrictLocalEventSpec(
        id="COMMON_SL_LOAD_LOCAL_EVENT_V1",
        scope="task-local",
        status="POST_HOC_EXPLORATORY",
        provenance_status="RAW_HASH_BOUND",
        mapping_status="DIRECT_SHARED_LOAD_BRANCH_P_V",
        phase_column=f"P(B_COL_LOAD{index:02d})",
        voltage_column=f"V(B_COL_LOAD{index:02d})",
        branch_endpoints="first_node_to_second_node; COMMON_SL->COL01->...->0",
        voltage_to_phase_sign=1,
        reporting_direction=1,
        run_id=mask,
        window_id="READ",
        raw_sha256=raw_hash,
        metric_spec={"path": rel(METRIC_SPEC), "version": "2.0.0", "sha256": digest(METRIC_SPEC)},
        tolerance={
            "id": "COMMON_SL_LOAD_DIAGNOSTIC_ONLY",
            "scope": "task-local",
            "evidence": "detect local complete phase segments; not a functional Gate",
            "status": "POST_HOC_EXPLORATORY",
            "phase_area_residual_abs_floor_turns": 0.05,
            "phase_area_residual_relative": 0.25,
            "complete_min_turns": 0.75,
            "clean_upper_turns": 1.15,
            "post_range_max_turns": 0.25,
            "post_tail_p2p_max_turns": 0.25,
        },
        compatibility_profile="STRICT_EVENT_ANCHOR_COMPATIBILITY_V1",
    )


def shared_load_record(trace: RawTrace, mask: str, raw_hash: str) -> dict[str, object]:
    per_jj: dict[str, object] = {}
    any_complete = False
    for index in range(1, 13):
        name = f"B_COL_LOAD{index:02d}"
        spec = strict_load_spec(mask, index, raw_hash)
        events = strict_event_list(
            trace.time,
            values(trace, f"P({name})"),
            values(trace, f"V({name})"),
            event_window_s=READ,
            scan_window_s=(100e-12, 200e-12),
            retrap_max_p2p_turns=0.25,
            spec=spec,
        )
        complete = int(events["complete_segment_count"] or 0)
        any_complete = any_complete or complete > 0
        phase = phase_stats(trace, f"P({name})", READ)
        current = wstats(trace, f"I({name})", READ, "A")
        per_jj[name] = {
            "phase_read": phase,
            "voltage_read": wstats(trace, f"V({name})", READ, "V"),
            "current_read": current,
            "current_to_ic_ratio_max_abs": float(current["max_abs"]) / 500.0,  # current is uA
            "strict_local_event_diagnostic": {
                key: events[key]
                for key in ("complete_segment_count", "clean_separated_event_count", "largest_segment_turns", "any_segment_spans_over_1_15_turns", "continuous_multi_turn_running", "complete_event_onset_times_ps", "clean_event_onset_times_ps", "clean_event_directions")
            },
        }
    first_current = values(trace, "I(B_COL_LOAD01)")
    series_mismatch: dict[str, object] = {}
    for index in range(2, 13):
        name = f"B_COL_LOAD{index:02d}"
        comparison = compare_series(trace.time, first_current, trace.time, values(trace, f"I({name})"), interpolation=None, include_correlation=True)
        comparison.pop("pointwise_difference", None)
        series_mismatch[name] = {
            "max_abs_uA": float(comparison["max_abs_difference"]) * 1e6,
            "rms_uA": float(comparison["rms_difference"]) * 1e6,
            "correlation": comparison.get("correlation"),
            "time_grid_exact": comparison["time_grid_exact"],
        }
    return {
        "model": "jjmit area=5.0",
        "declared_ic_uA": 500.0,
        "direct_common_current_authority": "I(B_COL_LOAD01)",
        "common_node_voltage": wstats(trace, "V(COMMON_SL)", READ, "V"),
        "first_load_current": wstats(trace, "I(B_COL_LOAD01)", READ, "A"),
        "per_jj": per_jj,
        "series_current_mismatch_vs_B_COL_LOAD01": series_mismatch,
        "strict_complete_event_seen": any_complete,
        "non_switching_assumption": "NOT_VIOLATED_BY_STRICT_LOCAL_EVENT_DIAGNOSTIC" if not any_complete else "VIOLATED_STRICT_LOCAL_EVENT_DIAGNOSTIC",
    }


def bvm_kcl_record(trace: RawTrace) -> dict[str, object]:
    per_bvm: dict[str, object] = {}
    for instance in range(1, 5):
        hierarchy = f"XBVM{instance}"
        equations = {
            "JM1_shunt": {"B_JM1": values(trace, f"I(B_JM1|{hierarchy})"), "R_JM1": values(trace, f"I(R_JM1|{hierarchy})"), "L_M1": values(trace, f"I(L_M1|{hierarchy})")},
            "SE_RLOOP": {"B_JS1": values(trace, f"I(B_JS1|{hierarchy})"), "L_PSE": values(trace, f"I(L_PSE|{hierarchy})"), "R_S": values(trace, f"I(R_S|{hierarchy})"), "L_S3": values(trace, f"I(L_S3|{hierarchy})")},
            "RLOOP_output": {"R_S": values(trace, f"I(R_S|{hierarchy})"), "L_S3": values(trace, f"I(L_S3|{hierarchy})"), "B_JS2": values(trace, f"I(B_JS2|{hierarchy})"), "L_PSL": values(trace, f"I(L_PSL|{hierarchy})")},
            "SL_series_1": {"L_PSL": values(trace, f"I(L_PSL|{hierarchy})"), "R_SL": values(trace, f"I(R_SL|{hierarchy})")},
            "SL_series_2": {"R_SL": values(trace, f"I(R_SL|{hierarchy})"), "L_SL": values(trace, f"I(L_SL|{hierarchy})")},
        }
        coefficients = {
            "JM1_shunt": {"B_JM1": 1, "R_JM1": 1, "L_M1": -1},
            "SE_RLOOP": {"B_JS1": 1, "L_PSE": 1, "R_S": -1, "L_S3": -1},
            "RLOOP_output": {"R_S": 1, "L_S3": 1, "B_JS2": 1, "L_PSL": -1},
            "SL_series_1": {"L_PSL": 1, "R_SL": -1},
            "SL_series_2": {"R_SL": 1, "L_SL": -1},
        }
        per_bvm[f"BVM{instance}"] = {}
        for equation, branches in equations.items():
            residual = linear_kcl_residual(branches, coefficients[equation])
            per_bvm[f"BVM{instance}"][equation] = {
                "orientation": "positive current from first netlist node to second",
                "residual": {"READ": kcl_window_metrics(trace.time, residual, READ, unit="A"), "SETTLE": kcl_window_metrics(trace.time, residual, SETTLE, unit="A")},
            }
    common_branches = {f"LSL{instance}": values(trace, f"I(L_SL|XBVM{instance})") for instance in range(1, 5)}
    common_branches["COMMON_LOAD"] = values(trace, "I(B_COL_LOAD01)")
    common_residual = linear_kcl_residual(common_branches, {f"LSL{instance}": 1 for instance in range(1, 5)} | {"COMMON_LOAD": -1})
    return {
        "orientation": "BVM L_SL is internal->COMMON_SL; B_COL_LOAD01 is COMMON_SL->COL01",
        "per_bvm": per_bvm,
        "common_sl_column": {"equation": "sum(I(L_SL|XBVM1..4)) - I(B_COL_LOAD01)", "residual": {"READ": kcl_window_metrics(trace.time, common_residual, READ, unit="A"), "SETTLE": kcl_window_metrics(trace.time, common_residual, SETTLE, unit="A")}},
    }


def compact_compare(time_s: Sequence[float], left: Sequence[float], right: Sequence[float], bounds: tuple[float, float], unit: str, scale: float) -> dict[str, object]:
    indices = window_indices(time_s, *bounds)
    t = [float(time_s[index]) for index in indices]
    left_selected = [float(left[index]) for index in indices]
    right_selected = [float(right[index]) for index in indices]
    result = compare_series(t, left_selected, t, right_selected, interpolation=None, include_correlation=True)
    result.pop("pointwise_difference", None)
    for key in ("max_abs_difference", "rms_difference", "p95_abs_difference"):
        result[key] = float(result[key]) * scale
    result["unit"] = unit
    result["difference_convention"] = "right_minus_left"
    result["window_ps"] = [bounds[0] * 1e12, bounds[1] * 1e12]
    return result


def delta_vector(trace: RawTrace, baseline: RawTrace, label: str) -> tuple[float, ...]:
    if not exact_time_grid_identity(trace.time, baseline.time):
        raise RuntimeError(f"time grid mismatch for {label}")
    return tuple(a - b for a, b in zip(values(trace, label), values(baseline, label)))


def max_abs(values_: Sequence[float]) -> float:
    return max((abs(float(value)) for value in values_), default=0.0)


def peak_time_ps(time_s: Sequence[float], values_: Sequence[float]) -> float:
    return float(time_s[max(range(len(values_)), key=lambda index: abs(float(values_[index])))]) * 1e12


def one_hot_position(traces: Mapping[str, RawTrace]) -> dict[str, object]:
    records: dict[str, object] = {}
    active_stats: dict[str, object] = {}
    current_vectors: list[Sequence[float]] = []
    for mask in ONE_HOT:
        instance = next(index for index, bit_value in enumerate(mask, start=1) if bit_value == "1")
        trace = traces[mask]
        label = "I(B_COL_LOAD01)"
        active_label = f"I(L_SL|XBVM{instance})"
        current_vectors.append(values(trace, label))
        active_stats[mask] = {
            "active_bvm": f"BVM{instance}",
            "common_current": wstats(trace, label, READ, "A"),
            "common_voltage": wstats(trace, "V(COMMON_SL)", READ, "V"),
            "active_rsl": wstats(trace, f"I(R_SL|XBVM{instance})", READ, "A"),
            "active_lsl": wstats(trace, active_label, READ, "A"),
        }
        records[mask] = active_stats[mask]
    pairwise: list[dict[str, object]] = []
    for i, left_mask in enumerate(ONE_HOT):
        for right_mask in ONE_HOT[i + 1:]:
            comparison = compact_compare(traces[left_mask].time, current_vectors[i], current_vectors[ONE_HOT.index(right_mask)], READ, "uA", 1e6)
            comparison.update({"left": left_mask, "right": right_mask})
            pairwise.append(comparison)
    common_stats = [float(active_stats[mask]["common_current"]["rms"]) for mask in ONE_HOT]  # type: ignore[index]
    return {"per_one_hot": records, "pairwise_common_current": pairwise, "common_current_rms_uA_range": [min(common_stats), max(common_stats)], "common_current_rms_uA_spread": max(common_stats) - min(common_stats)}


def inactive_isolation(traces: Mapping[str, RawTrace]) -> dict[str, object]:
    baseline = traces["0000"]
    per_one_hot: dict[str, object] = {}
    for mask in ONE_HOT:
        active = next(index for index, bit_value in enumerate(mask, start=1) if bit_value == "1")
        victims: dict[str, object] = {}
        for victim in range(1, 5):
            if victim == active:
                continue
            hierarchy = f"XBVM{victim}"
            victims[f"BVM{victim}"] = {
                "commanded_read_bit": 0,
                "signals": {
                    "RSL": {"delta": vstats(traces[mask].time, delta_vector(traces[mask], baseline, f"I(R_SL|{hierarchy})"), READ, "A")},
                    "LSL": {"delta": vstats(traces[mask].time, delta_vector(traces[mask], baseline, f"I(L_SL|{hierarchy})"), READ, "A")},
                    "RS": {"delta": vstats(traces[mask].time, delta_vector(traces[mask], baseline, f"I(R_S|{hierarchy})"), READ, "A")},
                    "LS3": {"delta": vstats(traces[mask].time, delta_vector(traces[mask], baseline, f"I(L_S3|{hierarchy})"), READ, "A")},
                    "JS1_phase": {"delta": phase_delta_stats(traces[mask], baseline, f"P(B_JS1|{hierarchy})", READ)},
                    "JS2_phase": {"delta": phase_delta_stats(traces[mask], baseline, f"P(B_JS2|{hierarchy})", READ)},
                    "LM3": {"delta": vstats(traces[mask].time, delta_vector(traces[mask], baseline, f"I(L_M3|{hierarchy})"), READ, "A")},
                },
            }
        per_one_hot[mask] = {"active_bvm": f"BVM{active}", "inactive_victims": victims}
    return {"baseline": "0000 same stored-1111 no-history run", "per_one_hot": per_one_hot}


def inactive_max(metrics: Mapping[str, object], signal: str, field: str = "max_abs") -> float:
    maximum = 0.0
    for item in metrics["per_one_hot"].values():  # type: ignore[union-attr]
        for victim in item["inactive_victims"].values():  # type: ignore[index]
            maximum = max(maximum, float(victim["signals"][signal]["delta"][field]))  # type: ignore[index]
    return maximum


def superposition_summary(traces: Mapping[str, RawTrace], label: str, masks: Sequence[str]) -> dict[str, object]:
    baseline = traces["0000"]
    onehot_delta = {mask: delta_vector(traces[mask], baseline, label) for mask in ONE_HOT}
    result: dict[str, object] = {}
    for mask in masks:
        active_onehots = [ONE_HOT_BY_INSTANCE[index] for index, bit_value in enumerate(mask, start=1) if bit_value == "1"]
        actual = delta_vector(traces[mask], baseline, label)
        predicted = tuple(sum(onehot_delta[onehot][index] for onehot in active_onehots) for index in range(len(actual)))
        residual = tuple(actual[index] - predicted[index] for index in range(len(actual)))
        comparison = compact_compare(traces[mask].time, predicted, actual, READ, "uA" if label.startswith("I(") else "mV", 1e6 if label.startswith("I(") else 1e3)
        result[mask] = {
            "active_one_hot_masks": active_onehots,
            "actual_delta": vstats(traces[mask].time, actual, READ, "A" if label.startswith("I(") else "V"),
            "predicted_delta": vstats(traces[mask].time, predicted, READ, "A" if label.startswith("I(") else "V"),
            "residual_actual_minus_predicted": vstats(traces[mask].time, residual, READ, "A" if label.startswith("I(") else "V"),
            "comparison_predicted_left_actual_right": comparison,
            "residual_peak_abs_time_ps": peak_time_ps(traces[mask].time, residual),
            "actual_peak_abs_time_ps": peak_time_ps(traces[mask].time, actual),
            "predicted_peak_abs_time_ps": peak_time_ps(traces[mask].time, predicted),
        }
    return {"label": label, "definition": "Delta(mask)=mask-0000; predicted=sum(one-hot Delta); residual=actual-predicted", "per_mask": result}


def additivity(traces: Mapping[str, RawTrace]) -> dict[str, object]:
    labels = OrderedDict((
        ("direct_common_current", "I(B_COL_LOAD01)"),
        ("sum_bvm_output_current", "SUM_BVM_OUTPUT"),
        ("common_voltage", "V(COMMON_SL)"),
    ))
    derived: dict[str, tuple[float, ...]] = {}
    for mask, trace in traces.items():
        derived[f"{mask}:SUM_BVM_OUTPUT"] = tuple(sum(values(trace, f"I(L_SL|XBVM{instance})")[index] for instance in range(1, 5)) for index in range(trace.sample_count))
    summary: dict[str, object] = {}
    for direction, masks in (("forward", FORWARD), ("reverse", REVERSE)):
        summary[direction] = {}
        for mask in masks:
            active_onehots = [ONE_HOT_BY_INSTANCE[index] for index, bit_value in enumerate(mask, start=1) if bit_value == "1"]
            per_signal: dict[str, object] = {}
            for key, label in labels.items():
                actual_trace = traces[mask]
                baseline = traces["0000"]
                if label == "SUM_BVM_OUTPUT":
                    actual = tuple(derived[f"{mask}:SUM_BVM_OUTPUT"][i] - derived["0000:SUM_BVM_OUTPUT"][i] for i in range(actual_trace.sample_count))
                    onehot = {onehot_mask: tuple(derived[f"{onehot_mask}:SUM_BVM_OUTPUT"][i] - derived["0000:SUM_BVM_OUTPUT"][i] for i in range(actual_trace.sample_count)) for onehot_mask in ONE_HOT}
                else:
                    actual = delta_vector(actual_trace, baseline, label)
                    onehot = {onehot_mask: delta_vector(traces[onehot_mask], baseline, label) for onehot_mask in ONE_HOT}
                predicted = tuple(sum(onehot[onehot_mask][i] for onehot_mask in active_onehots) for i in range(actual_trace.sample_count))
                residual = tuple(actual[i] - predicted[i] for i in range(actual_trace.sample_count))
                is_current = key != "common_voltage"
                unit = "uA" if is_current else "mV"
                factor = 1e6 if is_current else 1e3
                actual_si_unit = "A" if is_current else "V"
                per_signal[key] = {
                    "actual_delta": vstats(actual_trace.time, actual, READ, actual_si_unit),
                    "predicted_delta": vstats(actual_trace.time, predicted, READ, actual_si_unit),
                    "residual_actual_minus_predicted": vstats(actual_trace.time, residual, READ, actual_si_unit),
                    "comparison_predicted_left_actual_right": compact_compare(actual_trace.time, predicted, actual, READ, unit, factor),
                    "peak_time_actual_ps": peak_time_ps(actual_trace.time, actual),
                    "peak_time_predicted_ps": peak_time_ps(actual_trace.time, predicted),
                    "peak_time_difference_ps": peak_time_ps(actual_trace.time, actual) - peak_time_ps(actual_trace.time, predicted),
                    "normalized_rms_error": (math.sqrt(sum(value * value for value in residual) / len(residual)) / math.sqrt(sum(value * value for value in actual) / len(actual))) if any(actual) else None,
                }
            summary[direction][mask] = {"active_one_hot_masks": active_onehots, "signals": per_signal}
    return {"baseline": "0000", "directions": summary}


def active_loading(traces: Mapping[str, RawTrace]) -> dict[str, object]:
    result: dict[str, object] = {}
    for direction, masks, instance in (("forward", ("1000", "1100", "1110", "1111"), 1), ("reverse", ("0001", "0011", "0111", "1111"), 4)):
        result[direction] = {"tracked_bvm": f"BVM{instance}", "per_mask": {mask: {"RSL": wstats(traces[mask], f"I(R_SL|XBVM{instance})", READ, "A"), "LSL": wstats(traces[mask], f"I(L_SL|XBVM{instance})", READ, "A"), "common_current": wstats(traces[mask], "I(B_COL_LOAD01)", READ, "A"), "common_voltage": wstats(traces[mask], "V(COMMON_SL)", READ, "V")} for mask in masks}}
    return result


def old_distributed_comparison(new_traces: Mapping[str, RawTrace]) -> dict[str, object]:
    old_traces = {mask: read_csv(OLD_EXP / "runs" / mask / "raw.csv") for mask in MASKS}
    old_base = old_traces["0000"]
    for mask in MASKS:
        if old_traces[mask].duplicate_columns:
            raise RuntimeError(f"old reference duplicate columns in {mask}: {old_traces[mask].duplicate_columns}")
        if not exact_time_grid_identity(old_traces[mask].time, old_base.time):
            raise RuntimeError(f"old reference grid mismatch in {mask}")
    def position_set(traces: Mapping[str, RawTrace]) -> dict[str, object]:
        entries: dict[str, object] = {}
        vectors: list[tuple[str, Sequence[float]]] = []
        for mask in ONE_HOT:
            instance = next(index for index, bit_value in enumerate(mask, start=1) if bit_value == "1")
            label = f"I(L_SL|XBVM{instance})"
            vectors.append((mask, values(traces[mask], label)))
            entries[mask] = {"active_bvm": f"BVM{instance}", "active_lsl": wstats(traces[mask], label, READ, "A")}
        pairwise = []
        for i, (left_mask, left) in enumerate(vectors):
            for right_mask, right in vectors[i + 1:]:
                item = compact_compare(traces[left_mask].time, left, right, READ, "uA", 1e6)
                item.update({"left": left_mask, "right": right_mask})
                pairwise.append(item)
        return {"per_one_hot": entries, "pairwise_active_lsl": pairwise}
    def max_inactive(traces: Mapping[str, RawTrace]) -> float:
        maximum = 0.0
        for mask in ONE_HOT:
            active = next(index for index, bit_value in enumerate(mask, start=1) if bit_value == "1")
            for victim in range(1, 5):
                if victim == active:
                    continue
                delta = delta_vector(traces[mask], traces["0000"], f"I(L_SL|XBVM{victim})")
                maximum = max(maximum, float(vstats(traces[mask].time, delta, READ, "A")["max_abs"]))
        return maximum
    def sum_additivity(traces: Mapping[str, RawTrace]) -> dict[str, object]:
        def total(trace: RawTrace) -> tuple[float, ...]:
            return tuple(sum(values(trace, f"I(L_SL|XBVM{instance})")[i] for instance in range(1, 5)) for i in range(trace.sample_count))
        deltas = {mask: tuple(a - b for a, b in zip(total(traces[mask]), total(traces["0000"]))) for mask in MASKS}
        result: dict[str, object] = {}
        for mask in ("1100", "1110", "1111", "0011", "0111"):
            active = [ONE_HOT_BY_INSTANCE[index] for index, bit_value in enumerate(mask, start=1) if bit_value == "1"]
            predicted = tuple(sum(deltas[onehot][i] for onehot in active) for i in range(len(deltas[mask])))
            residual = tuple(deltas[mask][i] - predicted[i] for i in range(len(predicted)))
            result[mask] = {"residual": vstats(traces[mask].time, residual, READ, "A"), "actual": vstats(traces[mask].time, deltas[mask], READ, "A"), "predicted": vstats(traces[mask].time, predicted, READ, "A")}
        return result
    old_pos = position_set(old_traces)
    new_pos = position_set({mask: new_traces[mask] for mask in ONE_HOT + ("0000",)})
    return {
        "reference": rel(OLD_EXP),
        "raw_read_only": True,
        "topology": "old distributed per-BVM sensing network with historical terminal load",
        "primary_metrics": {
            "old_one_hot_active_lsl": old_pos,
            "new_common_sl_active_lsl": new_pos,
            "old_inactive_lsl_max_abs_uA": max_inactive(old_traces),
            "new_inactive_lsl_max_abs_uA": inactive_max({"per_one_hot": inactive_isolation(new_traces)["per_one_hot"]}, "LSL"),
            "old_sum_bvm_output_additivity": sum_additivity(old_traces),
        },
        "comparison_limit": "old fixture has no direct shared-load current authority; comparison is bounded to BVM endpoint current/position/inactive/additivity context",
    }


def artifact_qa(traces: Mapping[str, RawTrace]) -> dict[str, object]:
    records: dict[str, object] = {}
    for mask, trace in traces.items():
        metadata = EXP / "runs" / mask / "metadata.json"
        record = json.loads(metadata.read_text(encoding="utf-8"))
        records[mask] = {
            "raw": {"path": rel(trace.path), "sha256": digest(trace.path), "qa": trace.qa()},
            "metadata_exit_code": record.get("exit_code"),
            "execution_status": record.get("execution_status"),
            "deck_sha256": digest(EXP / "runs" / mask / "deck.cir"),
            "log_sha256": digest(EXP / "runs" / mask / "run.log"),
        }
    grid_equal = all(exact_time_grid_identity(traces["0000"].time, trace.time) for trace in traces.values())
    return {"status": "ARTIFACT_VALID" if grid_equal and all(item["execution_status"] == "RUN_PASS" and item["metadata_exit_code"] == 0 for item in records.values()) else "ARTIFACT_INVALID", "time_grid_identity_all_masks": grid_equal, "interpolation": "none", "per_mask": records}


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def report(metrics: Mapping[str, object]) -> str:
    artifact = metrics["artifact_qa"]
    protocol = metrics["protocol"]
    load_violated = bool(metrics["shared_load_summary"]["assumption_violated"])  # type: ignore[index]
    pos = metrics["one_hot_position"]
    inactive = metrics["inactive_isolation"]
    add = metrics["additivity"]
    lines = [
        "# HISTORICAL BVMSIM JM2-connected common-SL topology causality Quick",
        "",
        f"实验目录：`{EXP.name}`。这是 Exploration/Quick 结果，不是论文机制证明。分析生成时间：`{datetime.now(timezone.utc).astimezone().isoformat(timespec='seconds')}`。",
        "",
        "## 1. 实验边界",
        "",
        "固定 historical JM2-connected BVM、内部 `R_SL=12Ω`、原 BVM 参数、原 no-history stimulus、`dt=0.1 ps`；只把四个 BVM 的输出端接到共同 `COMMON_SL`，并使用一条共享的 12×500µA JJ load。没有 QB、JTL、10Ω termination，也没有调参。",
        "",
        "`P(...)` 原始单位是 rad；本报告中的 phase turns 只表示 `continuous_unwrap(rad)/(2π)`。它们不是 SFQ event count。",
        "",
        "## 2. Artifact / protocol",
        "",
        f"- raw artifact QA: `{artifact['status']}`；十个 mask 均独立保存，所有 mask exact grid identity=`{artifact['time_grid_identity_all_masks']}`，无插值。",
        f"- stimulus protocol: `{metrics['protocol_status']}`；每个 mask 都先 WRITE0、all-four WRITE1，再执行一次 final selective READ。",
        f"- shared-load strict local diagnostic: `{metrics['shared_load_summary']['status']}`。" if isinstance(metrics.get("shared_load_summary"), Mapping) else "",
        "",
        "## 3. 关键观察",
        "",
        f"1. one-hot 的直接 shared-load current `I(B_COL_LOAD01)` 在四个位置的 READ RMS 范围为 `{pos['common_current_rms_uA_range'][0]:.6g}–{pos['common_current_rms_uA_range'][1]:.6g} uA`，位置 spread 为 `{pos['common_current_rms_uA_spread']:.6g} uA`。这只描述位置依赖，不预设其是否足够小。",
        f"2. inactive BVM 相对于同一 stored-1111 的 `0000` 控制出现的最大 READ 差分：RSL `{inactive_max(inactive, 'RSL', 'max_abs'):.6g} uA`，LSL `{inactive_max(inactive, 'LSL', 'max_abs'):.6g} uA`，RS `{inactive_max(inactive, 'RS', 'max_abs'):.6g} uA`，LS3 `{inactive_max(inactive, 'LS3', 'max_abs'):.6g} uA`，JS1 phase `{inactive_max(inactive, 'JS1_phase', 'max_abs'):.6g} turns`，JS2 phase `{inactive_max(inactive, 'JS2_phase', 'max_abs'):.6g} turns`。这是当前 common-SL fixture 中的 observed cross-coupling/back-action evidence。",
        f"3. common current 的 multi-active superposition residual（最大 READ residual across forward/reverse masks）为 `{max(float(add['directions'][direction][mask]['signals']['direct_common_current']['residual_actual_minus_predicted']['max_abs']) for direction in ('forward','reverse') for mask in add['directions'][direction]):.6g} uA`；没有预设 5%/10% threshold。",
        f"4. shared 12-JJ load 的 strict local event diagnostic 未发现 complete event；`assumption_violated={load_violated}`。因此当前报告{'' if not load_violated else '不能继续把它当作 non-switching paper-like load'}。",
        "",
        "## 4. 受限物理含义",
        "",
        "在本固定网络和本十个 mask 内，active BVM 对 common SL 的响应、inactive BVM 的 back-action 和多 active 的非加性应分别作为 topology-caused observed evidence 报告；它们不能被提升为独立 unit-current、普适 RSL isolation 或论文机制身份。",
        "",
        "旧 distributed fixture 只作为 read-only context；由于旧网络没有 `I(B_COL_LOAD01)` 这一直接 shared-load authority，old/new 对照不被写成同一测量量的等价替换。",
        "",
        "## 5. 不证明什么",
        "",
        "本轮不证明 canonical BVM、QB/JTL 接收、SFQ 传输、硬件行为、工艺裕量、参数最优性、timestep convergence、论文机制身份或任意其它未测 mask。相位累计、voltage area、I>Ic 或局部 activity 都没有被用作 SFQ 计数。",
        "",
        "## 6. 当前状态",
        "",
        "`COMMON_SL_TOPOLOGY_QUICK_ANALYSIS_COMPLETE`；primary interpretation 保持 bounded/descriptive，等待用户审阅。shared-load assumption 若违反则本报告只保留原始和诊断结果，不解释 linear accumulation。",
        "",
        "## 7. 下一步选项（不自动执行）",
        "",
        "1. 用户审阅本轮 topology evidence；2. 若确有必要，另行授权针对 load switching 的独立诊断；3. 另行授权才讨论 QB/JTL 接入。",
    ]
    return "\n".join(line for line in lines if line is not None) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    traces = {mask: read_csv(EXP / "runs" / mask / "raw.csv") for mask in MASKS}
    for mask, trace in traces.items():
        if trace.duplicate_columns:
            raise RuntimeError(f"duplicate columns in new raw {mask}: {trace.duplicate_columns}")
    artifact = artifact_qa(traces)
    protocols = {mask: protocol_record(traces[mask], mask) for mask in MASKS}
    states = {mask: state_record(traces[mask]) for mask in MASKS}
    outputs = {mask: output_record(traces[mask]) for mask in MASKS}
    loads = {mask: shared_load_record(traces[mask], mask, digest(traces[mask].path)) for mask in MASKS}
    kcl = {mask: bvm_kcl_record(traces[mask]) for mask in MASKS}
    position = one_hot_position(traces)
    isolation = inactive_isolation(traces)
    superposition = additivity(traces)
    metrics: dict[str, object] = {
        "schema": "bvmsim-paperlike-common-sl-metrics-v1",
        "experiment_id": EXP.name,
        "created_at_local": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "source_class": "HISTORICAL_BVMSIM_JM2_CONNECTED_VARIANT",
        "canonical_bvm_used": False,
        "qb_jtl_metrics": "NOT_PRESENT_AND_NOT_ANALYZED",
        "fixed_parameters": {"internal_rsl_ohm": 12.0, "timestep_ps": 0.1, "shared_load_junction_count": 12, "shared_load_ic_uA": 500.0, "tuning": "none"},
        "windows_ps": {name: list(bounds) for name, bounds in WINDOWS_PS.items()},
        "artifact_qa": artifact,
        "protocol": protocols,
        "protocol_status": "PROTOCOL_VALID" if all(item["status"] == "PROTOCOL_VALID" for item in protocols.values()) else "PROTOCOL_INVALID",
        "state": states,
        "output": outputs,
        "shared_load": loads,
        "shared_load_summary": {
            "status": "VALID_DIAGNOSTIC" if not any(bool(item["strict_complete_event_seen"]) for item in loads.values()) else "COLUMN_LOAD_NONSWITCHING_ASSUMPTION_VIOLATED",
            "assumption_violated": any(bool(item["strict_complete_event_seen"]) for item in loads.values()),
            "per_mask": {mask: item["non_switching_assumption"] for mask, item in loads.items()},
        },
        "kcl": kcl,
        "one_hot_position": position,
        "inactive_isolation": isolation,
        "additivity": superposition,
        "active_cell_loading": active_loading(traces),
        "old_distributed_comparison": old_distributed_comparison(traces),
        "interpretation": {
            "status": "BOUNDED_DESCRIPTIVE_ONLY",
            "primary_question": "topology causality of common-SL replacement",
            "no_threshold_invention": True,
            "no_phase_to_sfq_count": True,
        },
    }
    metrics["analysis_status"] = "ANALYSIS_VALID" if artifact["status"] == "ARTIFACT_VALID" and metrics["protocol_status"] == "PROTOCOL_VALID" else "ANALYSIS_INVALID"
    if args.write:
        write_json(EXP / "analysis/metrics.json", metrics)
        (EXP / "analysis/REPORT.md").write_text(report(metrics), encoding="utf-8")
    print(json.dumps({"status": metrics["analysis_status"], "masks": len(MASKS), "grid_identity": artifact["time_grid_identity_all_masks"], "shared_load_status": metrics["shared_load_summary"]["status"]}, ensure_ascii=False))
    return 0 if metrics["analysis_status"] == "ANALYSIS_VALID" else 1


if __name__ == "__main__":
    raise SystemExit(main())
