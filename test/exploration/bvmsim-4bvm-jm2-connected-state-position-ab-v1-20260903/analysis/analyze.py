#!/usr/bin/env python3
"""分析 JM2-connected 4-BVM 六状态 A/B Quick。

本文件只拥有 task-local 的窗口、state mapping 和报告语义。raw reader、phase/
area、waveform、KCL 和 strict local event list 均来自共享 bvmtools；尤其不把
phase turns、whole-window voltage area 或局部活动直接称为 SFQ count。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import Any, Mapping, Sequence

REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
A_ROOT = REPO / "test/exploration/bvmsim-4bvm-state-position-closure-v1-20260903"
SOLVER = REPO / "build/josim-cli"
PLOTTER = REPO / "scripts/josim-plot2.py"
METRIC_SPEC = REPO / "docs/research/METRIC_SPEC_V2.md"
VARIANT = REPO / "test/exploration/bvmsim-jm2-connected-single-ab-v1-20260903/variants/bvm_jm2_connected.cir"
HISTORICAL_BVM = REPO / "BVMSim/bvm_cell.cir"
HISTORICAL_QB = REPO / "BVMSim/BQ.cir"
HISTORICAL_JTL = REPO / "BVMSim/library_josim/jtl2.cir"
SHARED_JJMIT = REPO / "circuits/models/jjmit.cir"
STATES = ("0000", "1000", "0100", "0010", "0001", "1111")
ONE_HOT = ("1000", "0100", "0010", "0001")
STORAGE_BRANCHES = ("L_M1", "L_M2", "L_M3", "L_PM", "L_PSL")

WINDOWS_PS: "OrderedDict[str, tuple[float, float]]" = OrderedDict(
    (
        ("PRE", (0.0, 50.0)),
        ("WRITE0", (50.0, 70.0)),
        ("READ0", (70.0, 90.0)),
        ("WRITE1", (90.0, 101.0)),
        ("POST_WRITE1", (101.0, 105.0)),
        ("PRE_READ1", (105.0, 110.0)),
        ("READ1", (110.0, 170.0)),
        ("TAIL", (170.0, 200.0)),
    )
)
WINDOWS_S = OrderedDict(
    (name, (left * 1.0e-12, right * 1.0e-12))
    for name, (left, right) in WINDOWS_PS.items()
)
PLATEAU_WRITE0 = (51.0e-12, 60.0e-12)
PLATEAU_READ0 = (71.0e-12, 80.0e-12)
PLATEAU_WRITE1 = (91.0e-12, 100.0e-12)
PLATEAU_READ1 = (111.0e-12, 120.0e-12)
SCAN = (0.0, 200.0e-12)
ACTIVITY_CURRENT_A = 1.0e-6
ACTIVITY_VOLTAGE_V = 1.0e-6
PLATEAU_TOLERANCE_A = 0.1e-6
COMPARISON_RATIO = 1.10

sys.path.insert(0, str(REPO / "scripts"))
from bvmtools.compare import compare_windowed_series, exact_time_grid_identity  # noqa: E402
from bvmtools.kcl import kcl_window_metrics, linear_kcl_residual  # noqa: E402
from bvmtools.metrics import phase_area_window  # noqa: E402
from bvmtools.onset import first_persistent_exceedance  # noqa: E402
from bvmtools.phase import TAU, continuous_unwrap, phase_window_metrics, window_indices  # noqa: E402
from bvmtools.provenance import sha256_file, solver_provenance  # noqa: E402
from bvmtools.probes import (  # noqa: E402
    flatten_probe_labels,
    historical_bvm_array_probes,
    historical_jtl_probes,
    original_bvmsim_qb_probes,
)
from bvmtools.raw import RawTrace, read_csv  # noqa: E402
from bvmtools.sfq import StrictLocalEventSpec, strict_event_list  # noqa: E402
from bvmtools.sl_probes import historical_sensing_line_endpoint_probes  # noqa: E402
from bvmtools.stimulus import validate_bvm_write_read_protocol, validate_expected_plateau  # noqa: E402
from bvmtools.waveform import trapezoid_integral, waveform_window_metrics  # noqa: E402


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO.resolve()).as_posix()


def digest(path: Path) -> str:
    return sha256_file(path)


def sig(trace: RawTrace, label: str) -> tuple[float, ...]:
    return trace.column(label)  # type: ignore[return-value]


def win(name: str) -> tuple[float, float]:
    return WINDOWS_S[name]


def labels_from_groups(*groups: Sequence[str]) -> tuple[str, ...]:
    output: list[str] = []
    for group in groups:
        for label in group:
            if label not in output:
                output.append(label)
    return tuple(output)


def all_required_labels() -> tuple[str, ...]:
    controls = tuple(
        f"I(I_{control}{number})"
        for number in range(1, 5)
        for control in ("WL", "BL", "SE")
    )
    return labels_from_groups(
        controls,
        flatten_probe_labels(historical_bvm_array_probes(4)),
        flatten_probe_labels(historical_sensing_line_endpoint_probes()),
        flatten_probe_labels(original_bvmsim_qb_probes()),
        flatten_probe_labels(historical_jtl_probes(6)),
    )


def core_required_labels() -> tuple[str, ...]:
    controls = tuple(
        f"I(I_{control}{number})"
        for number in range(1, 5)
        for control in ("WL", "BL", "SE")
    )
    return labels_from_groups(
        controls,
        flatten_probe_labels(historical_bvm_array_probes(4)),
        flatten_probe_labels(original_bvmsim_qb_probes()),
        flatten_probe_labels(historical_jtl_probes(6)),
    )


def json_write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def grid_fact(trace: RawTrace) -> dict[str, object]:
    steps = trace.dt
    return {
        "sample_count": trace.sample_count,
        "start_ps": trace.time[0] * 1.0e12,
        "end_ps": trace.time[-1] * 1.0e12,
        "dt_min_ps": min(steps) * 1.0e12,
        "dt_max_ps": max(steps) * 1.0e12,
        "uniform": all(step == steps[0] for step in steps),
        "duplicate_columns": trace.duplicate_columns,
        "interpolation": "none",
    }


def onset_fact(times: Sequence[float], values: Sequence[float], bounds: tuple[float, float], threshold: float) -> dict[str, object]:
    selected = [index for index, value in enumerate(times) if bounds[0] <= value < bounds[1]]
    local_times = [float(times[index]) for index in selected]
    local_values = [float(values[index]) for index in selected]
    result = dict(first_persistent_exceedance(local_times, local_values, threshold, min_consecutive_samples=2))
    for key in ("first_time_s", "persistence_start_s", "persistence_end_s"):
        if result.get(key) is not None:
            result[f"{key[:-2]}_ps"] = float(result[key]) * 1.0e12
    result["meaning"] = "descriptive activity localization only; not an SFQ count"
    return result


def waveform_fact(trace: RawTrace, label: str, bounds: tuple[float, float], unit: str, threshold: float) -> dict[str, object]:
    values = sig(trace, label)
    result = dict(waveform_window_metrics(trace.time, values, bounds, unit=unit))
    selected = window_indices(trace.time, *bounds)
    abs_index = max(selected, key=lambda index: abs(float(values[index])))
    factor = 1.0e6 if unit == "A" else 1.0e3 if unit == "V" else 1.0
    result.update(
        {
            "label": label,
            "raw_unit": "A" if unit == "A" else "V" if unit == "V" else "raw",
            "abs_peak_value": abs(float(values[abs_index])) * factor,
            "abs_peak_time_ps": trace.time[abs_index] * 1.0e12,
            "activity_threshold_si": threshold,
            "activity_threshold_display": threshold * factor,
            "onset": onset_fact(trace.time, [abs(float(value)) for value in values], bounds, threshold),
        }
    )
    return result


def phase_fact(trace: RawTrace, phase_label: str, voltage_label: str, bounds: tuple[float, float]) -> dict[str, object]:
    result = phase_area_window(
        trace.time,
        sig(trace, phase_label),
        sig(trace, voltage_label),
        bounds,
        voltage_to_phase_sign=1,
        reporting_direction=1,
        include_segments=False,
    )
    result.update({"phase_label": phase_label, "voltage_label": voltage_label, "same_jj": True, "count_authority": False})
    return result


def artifact_qa(connected: Mapping[str, RawTrace], omitted: Mapping[str, RawTrace], omitted_endpoint: Mapping[str, RawTrace]) -> dict[str, object]:
    issues: dict[str, list[str]] = {}
    expected_all = set(all_required_labels())
    expected_core = set(core_required_labels())
    for state in STATES:
        found: list[str] = []
        metadata = json.loads((EXP / "runs" / state / "metadata.json").read_text(encoding="utf-8"))
        raw_path = EXP / "runs" / state / "raw.csv"
        b, a, ae = connected[state], omitted[state], omitted_endpoint[state]
        if int(metadata.get("exit_code", 1)) != 0:
            found.append("SOLVER_EXIT_NONZERO")
        if metadata.get("artifact_status") != "EXECUTION_COMPLETE":
            found.append("EXECUTION_INCOMPLETE")
        if metadata.get("raw_sha256") != digest(raw_path):
            found.append("RAW_HASH_MISMATCH")
        if metadata.get("run_log_sha256") != digest(EXP / "runs" / state / "run.log"):
            found.append("RUN_LOG_HASH_MISMATCH")
        if metadata.get("model_warning_detected"):
            found.append("MODEL_WARNING")
        if b.duplicate_columns or a.duplicate_columns or ae.duplicate_columns:
            found.append("DUPLICATE_RAW_HEADER")
        if expected_all - set(b.headers):
            found.append("CONNECTED_PROBE_MISSING")
        if expected_core - set(a.headers):
            found.append("OMITTED_CORE_PROBE_MISSING")
        if expected_all - set(ae.headers):
            found.append("OMITTED_ENDPOINT_PROBE_MISSING")
        if not exact_time_grid_identity(b.time, a.time) or not exact_time_grid_identity(b.time, ae.time):
            found.append("TIME_GRID_MISMATCH")
        if not (b.time[0] >= 45.0e-12 and b.time[-1] <= 200.0e-12):
            found.append("UNEXPECTED_OUTPUT_RANGE")
        deck_text = (EXP / "runs" / state / "deck.cir").read_text(encoding="utf-8")
        if "bvm_jm2_connected.cir" not in deck_text or "BVMSim/bvm_cell.cir" in deck_text or "circuits/bvm/bvm_cell.cir" in deck_text:
            found.append("WRONG_BVM_INCLUDE")
        issues[state] = found
    return {
        "status": "ARTIFACT_VALID" if not any(issues.values()) else "ARTIFACT_INVALID",
        "all_states_valid": not any(issues.values()),
        "per_state_issues": issues,
        "raw_policy": "immutable raw.csv; independent run directories",
        "source_authority": "historical BVMSim JM2-connected task-local variant; not canonical BVM",
    }


def control_record(trace: RawTrace, state: str) -> dict[str, object]:
    output: dict[str, object] = {"state": state, "bvm_protocol": {}, "write1_read1": {}}
    for number in range(1, 5):
        wl, bl, se = f"I(I_WL{number})", f"I(I_BL{number})", f"I(I_SE{number})"
        protocol = validate_bvm_write_read_protocol(
            trace,
            trace.time,
            write_window_s=PLATEAU_WRITE0,
            read_window_s=PLATEAU_READ0,
            expected_write={wl: -100.0e-6, bl: -100.0e-6},
            expected_read={wl: 100.0e-6, se: 100.0e-6},
            tolerance=PLATEAU_TOLERANCE_A,
            unit="A",
        )
        bl_read0 = validate_expected_plateau(trace.time, sig(trace, bl), PLATEAU_READ0, 0.0, tolerance=PLATEAU_TOLERANCE_A, unit="A")
        bit_level = 100.0e-6 if state[number - 1] == "1" else -100.0e-6
        write1 = validate_expected_plateau(trace.time, sig(trace, bl), PLATEAU_WRITE1, bit_level, tolerance=PLATEAU_TOLERANCE_A, unit="A")
        read1 = {
            wl: validate_expected_plateau(trace.time, sig(trace, wl), PLATEAU_READ1, 100.0e-6, tolerance=PLATEAU_TOLERANCE_A, unit="A"),
            se: validate_expected_plateau(trace.time, sig(trace, se), PLATEAU_READ1, 100.0e-6, tolerance=PLATEAU_TOLERANCE_A, unit="A"),
            bl: validate_expected_plateau(trace.time, sig(trace, bl), PLATEAU_READ1, 0.0, tolerance=PLATEAU_TOLERANCE_A, unit="A"),
        }
        output["bvm_protocol"][f"BVM{number}"] = {"write0_read0": protocol, "read0_bl_zero": bl_read0}
        output["write1_read1"][f"BVM{number}"] = {"write1_bl": write1, "read1": read1}
    output["status"] = "PROTOCOL_VALID" if all(
        item["write0_read0"]["status"] == "PROTOCOL_VALID" and item["read0_bl_zero"]["status"] == "PASS"
        for item in output["bvm_protocol"].values()
    ) and all(
        item["write1_bl"]["status"] == "PASS" and all(value["status"] == "PASS" for value in item["read1"].values())
        for item in output["write1_read1"].values()
    ) else "PROTOCOL_MISMATCH"
    return output


def state_level(trace: RawTrace, label: str) -> dict[str, object]:
    return phase_window_metrics(trace.time, sig(trace, label), win("PRE_READ1"))


def retention_fact(trace: RawTrace, label: str) -> dict[str, object]:
    pre = state_level(trace, label)
    tail = phase_window_metrics(trace.time, sig(trace, label), win("TAIL"))
    difference = float(tail["mean_turns"]) - float(pre["mean_turns"])
    noise = max(float(pre["p2p_turns"]), float(tail["p2p_turns"]))
    return {
        "pre_read1": pre,
        "tail": tail,
        "tail_minus_pre_mean_turns": difference,
        "tail_minus_pre_abs_turns": abs(difference),
        "observed_noise_bound_turns": noise,
        "retention_observation": "STABLE_WITHIN_OBSERVED_P2P" if abs(difference) <= noise else "SHIFTED_OR_NOT_STABLE",
        "stored_eligibility_is_task_local": True,
    }


def level_difference(current: dict[str, object], baseline: dict[str, object]) -> dict[str, object]:
    difference = float(current["mean_turns"]) - float(baseline["mean_turns"])
    noise = max(float(current["p2p_turns"]), float(baseline["p2p_turns"]))
    return {
        "mean_difference_turns": difference,
        "abs_difference_turns": abs(difference),
        "within_window_noise_bound_turns": noise,
        "descriptive_separation": "DISTINCT_FROM_0000" if abs(difference) > noise else "NOT_SEPARATED_OR_AMBIGUOUS",
        "threshold_policy": "observed one-hot-vs-0000 separation compared only with observed p2p; no old ±0.938-turn threshold",
    }


def state_closure(connected: Mapping[str, RawTrace]) -> dict[str, object]:
    baseline = connected["0000"]
    output: dict[str, object] = {}
    for state in STATES:
        trace = connected[state]
        per_bvm: dict[str, object] = {}
        zero_shift_count = 0
        for number in range(1, 5):
            levels = {j: state_level(trace, f"P(B_{j}|XBVM{number})") for j in ("JM1", "JM2")}
            base_levels = {j: state_level(baseline, f"P(B_{j}|XBVM{number})") for j in ("JM1", "JM2")}
            shifts = {j: level_difference(levels[j], base_levels[j]) for j in levels}
            retention = {j: retention_fact(trace, f"P(B_{j}|XBVM{number})") for j in ("JM1", "JM2")}
            eligible = all(item["retention_observation"] == "STABLE_WITHIN_OBSERVED_P2P" for item in retention.values())
            bit = int(state[number - 1])
            zero_shift = bit == 0 and any(item["descriptive_separation"] == "DISTINCT_FROM_0000" for item in shifts.values())
            zero_shift_count += int(zero_shift)
            per_bvm[f"BVM{number}"] = {
                "commanded_bit": bit,
                "phase_levels_pre_read1": levels,
                "phase_difference_from_0000": shifts,
                "retention_pre_read1_to_tail": retention,
                "stored_eligibility_descriptive": eligible,
                "zero_bvm_internal_shift_descriptive": zero_shift,
                "storage_currents_pre_read1": {
                    branch: waveform_fact(trace, f"I({branch}|XBVM{number})", win("PRE_READ1"), "A", ACTIVITY_CURRENT_A)
                    for branch in STORAGE_BRANCHES
                },
                "sl_voltage_pre_read1": waveform_fact(trace, f"V(SL{number})", win("PRE_READ1"), "V", ACTIVITY_VOLTAGE_V),
                "sl_current_pre_read1": waveform_fact(trace, f"I(L_SL|XBVM{number})", win("PRE_READ1"), "A", ACTIVITY_CURRENT_A),
            }
        output[state] = {
            "commanded_state": state,
            "per_bvm": per_bvm,
            "zero_bvm_internal_shift_count_descriptive": zero_shift_count,
            "actual_state_label": "not forced; observed vector is per-BVM JM1/JM2 plus retention/current telemetry",
        }
    return output


def delta_series(trace: RawTrace, baseline: RawTrace, label: str, *, center_pre: bool = False) -> tuple[float, ...]:
    values = sig(trace, label)
    base = sig(baseline, label)
    if not exact_time_grid_identity(trace.time, baseline.time):
        raise RuntimeError(f"baseline time grid mismatch: {label}")
    if not center_pre:
        return tuple(float(value) - float(reference) for value, reference in zip(values, base))
    pre = window_indices(trace.time, *win("PRE_READ1"))
    trace_center = median(float(values[index]) for index in pre)
    base_center = median(float(base[index]) for index in pre)
    return tuple((float(value) - trace_center) - (float(reference) - base_center) for value, reference in zip(values, base))


def delta_fact(trace: RawTrace, baseline: RawTrace, label: str, bounds: tuple[float, float], unit: str, threshold: float, *, center_pre: bool = False) -> dict[str, object]:
    delta = delta_series(trace, baseline, label, center_pre=center_pre)
    result = dict(waveform_window_metrics(trace.time, delta, bounds, unit=unit))
    selected = window_indices(trace.time, *bounds)
    abs_index = max(selected, key=lambda index: abs(delta[index]))
    factor = 1.0e6 if unit == "A" else 1.0e3
    result.update(
        {
            "label": label,
            "difference_convention": "centered_one_hot_minus_centered_0000_same_side" if center_pre else "one_hot_minus_0000_same_side",
            "centered_by": "PRE_READ1 median" if center_pre else None,
            "abs_peak_value": abs(delta[abs_index]) * factor,
            "abs_peak_time_ps": trace.time[abs_index] * 1.0e12,
            "onset": onset_fact(trace.time, [abs(value) for value in delta], bounds, threshold),
            "activity_only": True,
        }
    )
    return result


def relation(a: float, b: float) -> str:
    aa, bb = abs(float(a)), abs(float(b))
    if aa == 0.0 and bb == 0.0:
        return "SIMILAR"
    if aa == 0.0:
        return "LARGER_CONNECTED"
    ratio = bb / aa
    if ratio >= COMPARISON_RATIO:
        return "LARGER_CONNECTED"
    if ratio <= 1.0 / COMPARISON_RATIO:
        return "SMALLER_CONNECTED"
    return "SIMILAR"


def compare_delta(omitted: dict[str, object], connected: dict[str, object]) -> dict[str, object]:
    fields = ("minimum", "maximum", "max_abs", "p2p", "rms", "signed_time_integral")
    result: dict[str, object] = {
        "comparison_qualifier": "ratio >=1.10 or <=1/1.10 is descriptive ordering only; not a scientific threshold",
        "fields": {},
    }
    for field in fields:
        left, right = float(omitted[field]), float(connected[field])
        result["fields"][field] = {
            "omitted": left,
            "connected": right,
            "connected_minus_omitted": right - left,
            "relation_by_absolute_magnitude": relation(left, right),
            "sign_changed": left != 0.0 and right != 0.0 and left * right < 0.0,
        }
    result["abs_peak_time_change_ps"] = (
        float(connected["abs_peak_time_ps"]) - float(omitted["abs_peak_time_ps"])
    )
    return result


def cross_coupling(connected: Mapping[str, RawTrace], omitted_endpoint: Mapping[str, RawTrace]) -> dict[str, object]:
    output: dict[str, object] = {}
    for state in ONE_HOT:
        active = next(index for index, bit in enumerate(state, start=1) if bit == "1")
        b, b0 = connected[state], connected["0000"]
        a, a0 = omitted_endpoint[state], omitted_endpoint["0000"]
        four_grid = all(exact_time_grid_identity(x.time, y.time) for x, y in ((a, a0), (b, b0), (a, b), (a0, b0)))
        zero_cells: dict[str, object] = {}
        for number, bit in enumerate(state, start=1):
            if bit == "1":
                continue
            current_label, voltage_label = f"I(L_SL|XBVM{number})", f"V(SL{number})"
            windows: dict[str, object] = {}
            for name in ("READ0", "READ1"):
                bounds = win(name)
                a_i, b_i = delta_fact(a, a0, current_label, bounds, "A", ACTIVITY_CURRENT_A)
                a_v, b_v = delta_fact(a, a0, voltage_label, bounds, "V", ACTIVITY_VOLTAGE_V)
                a_ci = delta_fact(a, a0, current_label, bounds, "A", ACTIVITY_CURRENT_A, center_pre=True)
                b_ci = delta_fact(b, b0, current_label, bounds, "A", ACTIVITY_CURRENT_A, center_pre=True)
                a_cv = delta_fact(a, a0, voltage_label, bounds, "V", ACTIVITY_VOLTAGE_V, center_pre=True)
                b_cv = delta_fact(b, b0, voltage_label, bounds, "V", ACTIVITY_VOLTAGE_V, center_pre=True)
                windows[name] = {
                    "state_conditioned": {
                        "current": {"omitted": a_i, "connected": b_i, "omitted_vs_connected": compare_delta(a_i, b_i)},
                        "voltage": {"omitted": a_v, "connected": b_v, "omitted_vs_connected": compare_delta(a_v, b_v)},
                    },
                    "read_associated_centered": {
                        "current": {"omitted": a_ci, "connected": b_ci, "omitted_vs_connected": compare_delta(a_ci, b_ci)},
                        "voltage": {"omitted": a_cv, "connected": b_cv, "omitted_vs_connected": compare_delta(a_cv, b_cv)},
                    },
                    "window_role": "READ0 negative control before WRITE1" if name == "READ0" else "READ1 response association window",
                }
            zero_cells[f"BVM{number}"] = {"commanded_bit": 0, "victim_label": "stored-0 only if retention eligibility supports it; otherwise commanded-0", "windows": windows}
        active_current = f"I(L_SL|XBVM{active})"
        active_voltage = f"V(SL{active})"
        active_cell = {
            "bvm": f"BVM{active}",
            "commanded_bit": 1,
            "windows": {
                name: {
                    "current": {"omitted": delta_fact(a, a0, active_current, win(name), "A", ACTIVITY_CURRENT_A), "connected": delta_fact(b, b0, active_current, win(name), "A", ACTIVITY_CURRENT_A)},
                    "voltage": {"omitted": delta_fact(a, a0, active_voltage, win(name), "V", ACTIVITY_VOLTAGE_V), "connected": delta_fact(b, b0, active_voltage, win(name), "V", ACTIVITY_VOLTAGE_V)},
                }
                for name in ("READ0", "READ1")
            },
        }
        output[state] = {
            "active_bvm": active_cell,
            "zero_cells": zero_cells,
            "four_track_exact_grid_gate": four_grid,
            "baseline": {"omitted": "same A-side 0000 endpoint raw", "connected": "same B-side 0000 raw"},
        }
    return output


def position_input(connected: Mapping[str, RawTrace], omitted: Mapping[str, RawTrace]) -> dict[str, object]:
    specs = (("V(QBIN)", "V", ACTIVITY_VOLTAGE_V), ("I(LIN|XBQ1)", "A", ACTIVITY_CURRENT_A))
    output: dict[str, object] = {"connected": {}, "omitted": {}, "connected_vs_omitted": {}, "spread": {}}
    for side, traces in (("connected", connected), ("omitted", omitted)):
        base = traces["0000"]
        for state in ONE_HOT:
            output[side][state] = {}
            for label, unit, threshold in specs:
                output[side][state][label] = {
                    "raw_one_hot": waveform_fact(traces[state], label, win("READ1"), unit, threshold),
                    "minus_0000": delta_fact(traces[state], base, label, win("READ1"), unit, threshold),
                }
    for state in ONE_HOT:
        output["connected_vs_omitted"][state] = {}
        for label, unit, _ in specs:
            scale = 1.0e3 if unit == "V" else 1.0e6
            output["connected_vs_omitted"][state][label] = {
                "raw_one_hot": compare_windowed_series(omitted[state].time, sig(omitted[state], label), connected[state].time, sig(connected[state], label), win("READ1"), value_scale=scale, unit="mV" if unit == "V" else "uA", include_correlation=True),
                "minus_0000": compare_windowed_series(omitted[state].time, delta_series(omitted[state], omitted["0000"], label), connected[state].time, delta_series(connected[state], connected["0000"], label), win("READ1"), value_scale=scale, unit="mV" if unit == "V" else "uA", include_correlation=True),
            }
    for side in ("connected", "omitted"):
        output["spread"][side] = {}
        for label, unit, _ in specs:
            for basis in ("raw_one_hot", "minus_0000"):
                values = [float(output[side][state][label][basis]["abs_peak_value"]) for state in ONE_HOT]
                output["spread"][side][f"{label}:{basis}"] = {
                    "display_unit": "mV" if unit == "V" else "uA",
                    "minimum_abs_peak": min(values),
                    "maximum_abs_peak": max(values),
                    "spread_abs_peak": max(values) - min(values),
                    "state_order_low_to_high": [state for _, state in sorted(zip(values, ONE_HOT))],
                }
    return output


def strict_spec(state: str, phase_label: str, voltage_label: str, raw_hash: str) -> StrictLocalEventSpec:
    return StrictLocalEventSpec(
        id="JM2_CONNECTED_4BVM_LOCAL_EVENT_DIAGNOSTIC_V1", scope="task-local", status="POST_HOC_EXPLORATORY",
        provenance_status="RECORDED", mapping_status="EXACT_RAW_LABEL_SAME_JJ", phase_column=phase_label,
        voltage_column=voltage_label, branch_endpoints="same JJ phase/voltage branch", voltage_to_phase_sign=1,
        reporting_direction=1, run_id=state, window_id="READ1", raw_sha256=raw_hash,
        metric_spec={"path": rel(METRIC_SPEC), "version": "2.0.0", "sha256": digest(METRIC_SPEC)},
        tolerance={
            "id": "task-local-diagnostic", "scope": "task-local diagnostic only", "evidence": "same JJ phase-area plus segmentation", "status": "POST_HOC_EXPLORATORY",
            "phase_area_residual_abs_floor_turns": 0.05, "phase_area_residual_relative": 0.10, "complete_min_turns": 1.0,
            "clean_upper_turns": 1.15, "post_range_max_turns": 1.0, "post_tail_p2p_max_turns": 0.25,
        },
        compatibility_profile="STRICT_EVENT_ANCHOR_COMPATIBILITY_V1",
    )


def strict_summary(trace: RawTrace, state: str, phase_label: str, voltage_label: str, raw_hash: str) -> dict[str, object]:
    try:
        result = strict_event_list(
            trace.time, sig(trace, phase_label), sig(trace, voltage_label), event_window_s=win("READ1"), scan_window_s=SCAN,
            retrap_max_p2p_turns=0.25, spec=strict_spec(state, phase_label, voltage_label, raw_hash),
        )
        return {
            "status": "DIAGNOSTIC_VALID", "method": result["mode"], "complete_segment_count": result["complete_segment_count"],
            "clean_separated_event_count": result["clean_separated_event_count"], "largest_segment_turns": result["largest_segment_turns"],
            "any_segment_spans_over_1_15_turns": result["any_segment_spans_over_1_15_turns"], "continuous_multi_turn_running": result["continuous_multi_turn_running"],
            "complete_event_onset_times_ps": result["complete_event_onset_times_ps"], "clean_event_onset_times_ps": result["clean_event_onset_times_ps"],
            "clean_event_directions": result["clean_event_directions"], "claim_ceiling": "LOCAL_JUNCTION_ONLY; not downstream transport count",
        }
    except Exception as exc:
        return {"status": "DIAGNOSTIC_ERROR", "error": str(exc), "claim_ceiling": "no event interpretation"}


def qb_jtl(connected: Mapping[str, RawTrace]) -> tuple[dict[str, object], dict[str, object]]:
    qb: dict[str, object] = {}
    jtl: dict[str, object] = {}
    for state in STATES:
        trace, raw_hash = connected[state], digest(EXP / "runs" / state / "raw.csv")
        qb[state] = {
            "input_output": {
                label: {name: waveform_fact(trace, label, win(name), unit, threshold) for name in ("READ0", "READ1")}
                for label, unit, threshold in (("V(QBIN)", "V", ACTIVITY_VOLTAGE_V), ("V(QBOUT)", "V", ACTIVITY_VOLTAGE_V), ("I(LIN|XBQ1)", "A", ACTIVITY_CURRENT_A))
            },
            "BJ2_same_jj": {name: phase_fact(trace, "P(BJ2|XBQ1)", "V(BJ2|XBQ1)", win(name)) for name in ("READ0", "READ1", "TAIL")},
            "BJ2_strict_local_diagnostic": strict_summary(trace, state, "P(BJ2|XBQ1)", "V(BJ2|XBQ1)", raw_hash),
        }
        jtl[state] = {}
        for stage in range(1, 7):
            jtl[state][f"JTL{stage}"] = {}
            for branch in ("B01", "B02"):
                p, v = f"P({branch}|XJTL1_{stage})", f"V({branch}|XJTL1_{stage})"
                jtl[state][f"JTL{stage}"][branch] = {
                    "same_jj": {name: phase_fact(trace, p, v, win(name)) for name in ("READ0", "READ1", "TAIL")},
                    "strict_local_diagnostic": strict_summary(trace, state, p, v, raw_hash) if branch == "B02" else {"status": "NOT_REQUIRED_FOR_SUMMARY"},
                }
    return qb, jtl


def qb_kcl(connected: Mapping[str, RawTrace]) -> dict[str, object]:
    equations = OrderedDict(
        (
            ("node_1_Lin_minus_BJs", {"I_Lin": 1.0, "I_BJs": -1.0}),
            ("node_2_BJs_minus_BJ1_RJ1_L1", {"I_BJs": 1.0, "I_BJ1": -1.0, "I_RJ1": -1.0, "I_L1": -1.0}),
            ("node_3_L1_plus_bias_minus_L2", {"I_L1": 1.0, "I_bias": 1.0, "I_L2": -1.0}),
            ("node_4_L2_minus_BJ2_RJ2_L3", {"I_L2": 1.0, "I_BJ2": -1.0, "I_RJ2": -1.0, "I_L3": -1.0}),
        )
    )
    labels = {"I_Lin": "I(LIN|XBQ1)", "I_BJs": "I(BJS|XBQ1)", "I_L1": "I(L1|XBQ1)", "I_bias": "I(IB|XBQ1)", "I_L2": "I(L2|XBQ1)", "I_BJ1": "I(BJ1|XBQ1)", "I_RJ1": "I(RJ1|XBQ1)", "I_BJ2": "I(BJ2|XBQ1)", "I_RJ2": "I(RJ2|XBQ1)", "I_L3": "I(L3|XBQ1)"}
    result: dict[str, object] = {
        "orientation": {
            "I_Lin": "QB input -> node 1", "I_BJs": "node 1 -> node 2", "I_L1": "node 2 -> BIAS node 3", "I_bias": "ground -> BIAS node 3", "I_L2": "BIAS node 3 -> node 4", "I_BJ1": "node 2 -> ground", "I_RJ1": "node 2 -> ground", "I_BJ2": "node 4 -> ground", "I_RJ2": "node 4 -> ground", "I_L3": "node 4 -> QB output"
        },
        "equations": {},
    }
    for state in STATES:
        trace = connected[state]
        branches = {name: sig(trace, label) for name, label in labels.items()}
        result["equations"][state] = {}
        for equation, coefficients in equations.items():
            residual = linear_kcl_residual({key: branches[key] for key in coefficients}, coefficients)
            result["equations"][state][equation] = {
                "coefficients": coefficients,
                "windows": {name: kcl_window_metrics(trace.time, residual, win(name), unit="A") for name in ("READ0", "READ1")},
            }
    return result


def ab_core(connected: Mapping[str, RawTrace], omitted: Mapping[str, RawTrace]) -> dict[str, object]:
    labels = [*(f"P(B_{j}|XBVM{n})" for n in range(1, 5) for j in ("JM1", "JM2")), *(f"I(L_SL|XBVM{n})" for n in range(1, 5)), *(f"V(SL{n})" for n in range(1, 5)), "V(QBIN)", "I(LIN|XBQ1)", "P(BJ2|XBQ1)", "P(B02|XJTL1_6)"]
    output: dict[str, object] = {}
    for state in STATES:
        output[state] = {
            label: {
                name: compare_windowed_series(omitted[state].time, sig(omitted[state], label), connected[state].time, sig(connected[state], label), win(name), value_scale=1.0 / TAU if label.startswith("P(") else 1.0e3 if label.startswith("V(") else 1.0e6, unit="turns" if label.startswith("P(") else "mV" if label.startswith("V(") else "uA", include_correlation=True)
                for name in ("READ0", "READ1")
            }
            for label in labels
        }
    return {"difference_convention": "connected_minus_omitted", "signals": output}


def independent_match(metrics: Mapping[str, object]) -> dict[str, object]:
    path = EXP / "analysis/independent_check.json"
    if not path.is_file():
        return {"status": "MISSING", "path": rel(path)}
    independent = json.loads(path.read_text(encoding="utf-8"))
    checks: list[dict[str, object]] = []
    for state in ONE_HOT:
        main_value = metrics["position_input"]["connected"][state]["I(LIN|XBQ1)"]["raw_one_hot"]["abs_peak_value"]
        check_value = independent["position"][state]["I(LIN|XBQ1)_uA"]["max_abs"]
        checks.append({"name": f"position_{state}_lin_abs_peak", "main": main_value, "independent": check_value, "match": math.isclose(float(main_value), float(check_value), rel_tol=0.0, abs_tol=1.0e-9)})
        for bvm, record in metrics["cross_coupling"][state]["zero_cells"].items():
            main_cross = record["windows"]["READ1"]["state_conditioned"]["current"]["connected"]["max_abs"]
            check_cross = independent["zero_bvm_delta_current"][state][bvm]["connected"]["max_abs_uA"]
            checks.append({"name": f"cross_{state}_{bvm}_lin_abs_peak", "main": main_cross, "independent": check_cross, "match": math.isclose(float(main_cross), float(check_cross), rel_tol=0.0, abs_tol=1.0e-9)})
    for state in STATES:
        main_phase = metrics["qb"][state]["BJ2_same_jj"]["READ1"]["phase_delta_turns"]
        independent_phase = independent["same_jj_phase_area"][state]["BJ2_READ1"]["phase_delta_turns"]
        checks.append({"name": f"BJ2_{state}_phase_delta", "main": main_phase, "independent": independent_phase, "match": math.isclose(float(main_phase), float(independent_phase), rel_tol=0.0, abs_tol=1.0e-12)})
    return {"status": "PASS" if all(item["match"] for item in checks) else "FAIL", "path": rel(path), "checks": checks, "assertion_count": len(checks)}


def fmt(value: object, digits: int = 4) -> str:
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "是" if value else "否"
    if isinstance(value, (int, float)):
        return f"{float(value):.{digits}g}"
    return str(value)


def reports(metrics: dict[str, object]) -> tuple[str, str, str]:
    qa = metrics["artifact_qa"]
    position = metrics["position_input"]
    lin_spread = position["spread"]["connected"]["I(LIN|XBQ1):raw_one_hot"]
    qbin_spread = position["spread"]["connected"]["V(QBIN):raw_one_hot"]
    cross = metrics["cross_coupling"]
    rows: list[str] = []
    total, active = 0, 0
    relations: dict[str, int] = {}
    max_zero = (0.0, "")
    for state in ONE_HOT:
        for bvm, record in cross[state]["zero_cells"].items():
            total += 1
            item = record["windows"]["READ1"]["state_conditioned"]["current"]
            peak = float(item["connected"]["max_abs"])
            if peak >= 1.0:
                active += 1
            if peak > max_zero[0]:
                max_zero = (peak, f"{state}/{bvm}")
            rel_name = item["omitted_vs_connected"]["fields"]["max_abs"]["relation_by_absolute_magnitude"]
            relations[rel_name] = relations.get(rel_name, 0) + 1
            rows.append(f"| {state} | {bvm} | {fmt(item['omitted']['max_abs'])} | {fmt(item['connected']['max_abs'])} | {rel_name} | {fmt(item['omitted_vs_connected']['abs_peak_time_change_ps'])} |")
    transport: list[str] = []
    for state in STATES:
        values = [fmt(metrics["jtl"][state][f"JTL{stage}"]["B02"]["strict_local_diagnostic"].get("clean_separated_event_count")) for stage in range(1, 7)]
        transport.append(f"| {state} | " + " | ".join(values) + " |")
    observations = [
        f"六个 connected raw 的 artifact QA 为 `{qa['status']}`，且这不是物理 PASS。",
        f"connected one-hot 的 READ1 `I(LIN|XBQ1)` raw 峰值 spread 为 {fmt(lin_spread['spread_abs_peak'])} uA（{fmt(lin_spread['minimum_abs_peak'])}–{fmt(lin_spread['maximum_abs_peak'])} uA）；`V(QBIN)` spread 为 {fmt(qbin_spread['spread_abs_peak'])} mV。",
        f"12 个 active→zero cell pair 中，connected state-conditioned READ1 Delta I 的 {active} 个超过 1 uA 描述性 floor；最大为 {fmt(max_zero[0])} uA（{max_zero[1]}）。",
        f"这 12 个 pair 的 connected-vs-omitted `max_abs` 描述性关系计数为 {relations}；方向没有预先假定。",
        "READ0 被作为 WRITE1 前的负控制；centered difference 与原始 state-conditioned difference 都保留，避免把 WRITE1 后状态偏移误写成唯一 READ 因果。",
    ]
    report = """# JM2-connected 4-BVM 六状态 A/B Quick 报告

## 首要问题与边界

本轮优先回答：一个 active-1 BVM 是否会把其他 commanded/stored-0 BVM 的 READ
response 拉离 `0000`，以及该 cross-coupling 在 JM2 omitted/connected 之间如何
变化；`I(LIN|XBQ1)` 的 position dependence 是并列问题。A/B 只改变 BVM include。

原始差分是 `X(one-hot)-X(0000)`。为避免将 WRITE1 后残留误写成 READ 因果，另
报告以各自 `PRE_READ1` median 中心化后的 difference-in-differences。`READ0`
发生在 WRITE1 之前，是负控制；本实验没有 READ=0/no-read 控制，因此 centered
结果仍是 READ-associated/state-conditioned evidence，不是唯一因果证明。

## 关键观察（Observed / Derived）

""" + "\n".join(f"- {item}" for item in observations) + """

## Zero-cell READ1 response

下表只展示 state-conditioned `Delta I_LSL` 的 `max_abs`，单位 uA；完整的
`Delta V_SL`、centered difference、signed integral、RMS、onset 和 timing 在
`analysis/metrics.json`。每一行是 4×3 矩阵中的一个 pair，不池化。

| one-hot | zero BVM | JM2 omitted | JM2 connected | connected vs omitted | abs-peak time change (ps) |
|---|---:|---:|---:|---|---:|
""" + "\n".join(rows) + """

## Position-dependent QB input

`metrics.json` 同时保存四个 one-hot 的 raw `V(QBIN)`/`I(LIN|XBQ1)`、各侧
`one-hot-0000` 校正值和 omitted/connected 对照。所有逐点比较均要求 exact time
grid，未做插值。它们是波形统计，不能作为 SFQ count。

## QB/JTL

下表是 connected B02 的 strict local diagnostic clean-separated event count，
只作局部相位/事件结构观察，绝不等同于整条链的 transport count。

| state | JTL1 | JTL2 | JTL3 | JTL4 | JTL5 | JTL6 |
|---|---:|---:|---:|---:|---:|---:|
""" + "\n".join(transport) + """

同一 junction 的 phase displacement 与 voltage area 在 `metrics.json` 的 `qb`
和 `jtl` 中对齐；JoSIM `P(...)` 是 rad，turns 只由 continuous unwrap 后除以
`2*pi` 得到。phase/area、local activity 和下游身份匹配必须分开看。

## 证据分层

- **Observed**：六个 B-side raw、四组控制、每个 BVM 内部 P/V/I 和 SL telemetry、
  所有 sensing endpoint、QBin/QBout/Lin、QB branch、六级 JTL B01/B02 P/V。
- **Derived**：同侧 raw delta、PRE_READ1-centered difference-in-differences、
  position baseline correction、same-JJ phase-area、strict local diagnostic、
  QB KCL residual、A/B numeric relations。
- **Inference（有边界）**：非零 zero-cell delta 表示在此历史 shared network 中
  可以观察到 active-state-conditioned 的 victim response；A/B 大小关系只属于
  这个 fixture，不能升级为机制或普适结论。
- **Unknown**：connected-side 是否满足真正存储语义、canonical BVM、single-BVM、
  timestep convergence、process margin、paper mechanism identity 和系统 SFQ
  一一对应传输。

## 当前处置

本轮保持 `NO_CLEAR_STRICT_CLASSIFICATION` / `QUICK_AMBIGUOUS`，没有把任何
phase/area/local activity 变成 Gate，也没有执行下一项实验。
"""
    brief = """# RESULT BRIEF — JM2-connected 4-BVM 六状态 A/B Quick

## 1. 本轮内容

完成 task-local JM2-connected 四 BVM 六状态 A/B Quick。B 侧仅使用已审阅
`bvm_jm2_connected.cir` variant；A 侧使用既有 omitted endpoint raw。

## 2. 最重要的结果

""" + "\n".join(f"- {item}" for item in observations[:5]) + """

## 3. 物理含义

每个 one-hot/zero-cell pair 的 raw delta、PRE_READ1-centered delta 和
omitted-vs-connected 比较已经单独保存。因此可以讨论 shared sensing network
中的 state-conditioned cross-coupling，但不能把非零 delta 当作唯一 READ 因果、
SFQ 接收计数或论文机制证明。

## 4. 不证明什么

不证明 canonical/single-BVM 兼容性、SFQ 一一对应、timestep 收敛、工艺裕度、
T1、paper-level claim 或任何 Gate。

## 5. 当前状态

`NO_CLEAR_STRICT_CLASSIFICATION` / `QUICK_AMBIGUOUS`；等待用户审阅，停止。

## 6. 后续选项（不执行）

1. 用户检查 six-state standalone plots、三个 focused comparison plots 与 REPORT。
2. 若需要，另行授权更细的 zero-cell coupling 时间窗诊断。
3. 若需要，另行授权 canonical BVM 对照；本轮没有创建或运行。
"""
    independent_count = metrics["independent_check"].get("assertion_count", "—")
    review = f"""# REVIEW — JM2-connected 4-BVM six-state A/B Quick

## Adversarial checks

- A/B 的 `0000` baseline 分侧使用；没有用 active state 或跨拓扑 baseline。
- state mapping 固定为 `b3b2b1b0 -> BVM1/BVM2/BVM3/BVM4`；zero-cell 主表保留
  完整 4×3 pair，不用总和掩盖位置和符号。
- 四条轨迹（A one-hot、A 0000、B one-hot、B 0000）逐点比较前有 exact-grid gate；
  不满足时禁止插值。
- `READ0` 作为 WRITE1 前负控制；`PRE_READ1` 到 `TAIL` 的 retention 先报告，
  不机械重用旧 ±0.938 turn threshold。
- exact raw labels、duplicate header、metadata/hash、solver exit、model warning、
  variant identity 和 canonical BVM 排除均检查。
- plot2 只负责描述图；phase display 使用 rad/(2*pi)，不从 HTML 外观推断事件。

## Independent numerical check

`analysis/independent_check.py` 不读取 `metrics.json`，独立复算 Lin position 峰值、
zero-cell Delta I 和 BJ2 phase-area；主分析与其有 `{independent_count}` 项匹配断言。

## 限制与审阅状态

这是 historical BVMSim task-local variant 的 exploratory A/B。zero-cell response
的机制解释必须保持 bounded inference；本文件不授予 Formal/Gate/paper authority。
已请求只读 Sol XHigh reviewer 检查 baseline、centered delta、position 和
local-to-downstream overclaim；该审阅不修改仓库。
"""
    return report, brief, review


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=EXP / "analysis/metrics.json")
    args = parser.parse_args()
    connected = {state: read_csv(EXP / "runs" / state / "raw.csv") for state in STATES}
    omitted = {state: read_csv(A_ROOT / "runs" / state / "raw.csv") for state in STATES}
    omitted_endpoint = {state: read_csv(A_ROOT / "runs_sl_endpoints" / state / "raw.csv") for state in STATES}
    qa = artifact_qa(connected, omitted, omitted_endpoint)
    if not qa["all_states_valid"]:
        raise RuntimeError(f"artifact invalid; refusing physical interpretation: {qa}")
    metrics: dict[str, object] = {
        "schema": "bvmsim-4bvm-jm2-connected-state-position-ab-metrics-v2",
        "analysis_version": "JM2_CONNECTED_4BVM_SIX_STATE_POSITION_AB_ANALYSIS_V2",
        "created_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "experiment_id": EXP.name,
        "source_class": "HISTORICAL_BVMSIM_JM2_CONNECTED_VARIANT",
        "artifact_qa": qa,
        "time_grids": {
            "connected": {state: grid_fact(connected[state]) for state in STATES},
            "omitted_formal": {state: grid_fact(omitted[state]) for state in STATES},
            "omitted_endpoint": {state: grid_fact(omitted_endpoint[state]) for state in STATES},
            "a_b_exact_all_states": all(exact_time_grid_identity(connected[state].time, omitted[state].time) for state in STATES),
            "connected_endpoint_exact_all_states": all(exact_time_grid_identity(connected[state].time, omitted_endpoint[state].time) for state in STATES),
            "interpolation": "none",
        },
        "controls": {state: control_record(connected[state], state) for state in STATES},
        "state_closure": state_closure(connected),
        "position_input": position_input(connected, omitted),
        "cross_coupling": cross_coupling(connected, omitted_endpoint),
        "ab_core": ab_core(connected, omitted),
    }
    qb, jtl = qb_jtl(connected)
    metrics["qb"], metrics["jtl"] = qb, jtl
    metrics["qb_kcl"] = qb_kcl(connected)
    metrics["provenance"] = {
        "root_provenance": {"path": rel(EXP / "provenance.json"), "sha256": digest(EXP / "provenance.json")},
        "variant": {"path": rel(VARIANT), "sha256": digest(VARIANT)},
        "historical_bvm": {"path": rel(HISTORICAL_BVM), "sha256": digest(HISTORICAL_BVM)},
        "historical_qb": {"path": rel(HISTORICAL_QB), "sha256": digest(HISTORICAL_QB)},
        "historical_jtl": {"path": rel(HISTORICAL_JTL), "sha256": digest(HISTORICAL_JTL)},
        "shared_jjmit": {"path": rel(SHARED_JJMIT), "sha256": digest(SHARED_JJMIT)},
        "metric_spec": {"path": rel(METRIC_SPEC), "sha256": digest(METRIC_SPEC), "version": "2.0.0"},
        "solver": solver_provenance(SOLVER, cwd=REPO),
        "plotter": {"path": rel(PLOTTER), "sha256": digest(PLOTTER)},
        "connected_raw_sha256": {state: digest(EXP / "runs" / state / "raw.csv") for state in STATES},
        "omitted_formal_raw_sha256": {state: digest(A_ROOT / "runs" / state / "raw.csv") for state in STATES},
        "omitted_endpoint_raw_sha256": {state: digest(A_ROOT / "runs_sl_endpoints" / state / "raw.csv") for state in STATES},
    }
    metrics["independent_check"] = independent_match(metrics)
    metrics["classification"] = {
        "primary": "NO_CLEAR_STRICT_CLASSIFICATION",
        "quick_label": "QUICK_AMBIGUOUS",
        "ceiling": "exploratory bounded evidence; no Formal/Gate/paper claim",
        "phase_turns_are_not_sfq_count": True,
    }
    json_write(args.output, metrics)
    report, brief, review = reports(metrics)
    (EXP / "analysis/REPORT.md").write_text(report, encoding="utf-8")
    (EXP / "RESULT_BRIEF.md").write_text(brief, encoding="utf-8")
    (EXP / "analysis/REVIEW.md").write_text(review, encoding="utf-8")
    (EXP / "analysis/human-gate.yaml").write_text(
        "state: AWAITING_USER_REVIEW\nuser_reviewed: false\nnext_step_authorized: false\nautomatic_next_experiment: false\nstage_b_authorized: false\nnext_action: STOP\nreview_note: \"本实验结果等待用户审阅；不得自动启动 follow-up。\"\n",
        encoding="utf-8",
    )
    json_write(
        EXP / "analysis/provenance.json",
        {
            "schema": "bvmsim-4bvm-jm2-connected-postrun-provenance-v1",
            "experiment_id": EXP.name,
            "created_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
            "analysis_script": {"path": rel(Path(__file__)), "sha256": digest(Path(__file__))},
            "metrics": {"path": rel(args.output), "sha256": digest(args.output)},
            "connected_raw_sha256": metrics["provenance"]["connected_raw_sha256"],
            "independent_check": metrics["independent_check"],
        },
    )
    print(json.dumps({"status": "PASS", "artifact_status": qa["status"], "independent_check": metrics["independent_check"]["status"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
