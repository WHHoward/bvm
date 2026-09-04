#!/usr/bin/env python3
"""Read-only OLD-1111 versus NEW-1111 history-difference audit.

This analyzer intentionally never invokes JoSIM and never modifies either
authoritative raw CSV.  It compares only exact common samples and uses the
shared bvmtools phase/waveform primitives.  The task-local interpretation is
kept here rather than being promoted into a global SFQ/event metric.
"""

from __future__ import annotations

import csv
import difflib
import hashlib
import json
import math
import re
import subprocess
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Iterable, Sequence


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
OLD_DECK = REPO / "test/exploration/bvmsim-4bvm-jm2-connected-state-position-ab-v1-20260903/runs/1111/deck.cir"
OLD_RAW = REPO / "test/exploration/bvmsim-4bvm-jm2-connected-state-position-ab-v1-20260903/runs/1111/raw.csv"
NEW_DECK = REPO / "test/exploration/bvmsim-4bvm-allone-selective-read-additivity-isolation-v1-20260904/runs/1111/deck.cir"
NEW_RAW = REPO / "test/exploration/bvmsim-4bvm-allone-selective-read-additivity-isolation-v1-20260904/runs/1111/raw.csv"
S1_RAW = REPO / "test/exploration/bvmsim-jm2-connected-single-rloop-observability-v1-20260904/runs/S1-J-RLOOP/raw.csv"

sys.path.insert(0, str(REPO / "scripts"))
from bvmtools.metrics import phase_area_window  # noqa: E402
from bvmtools.phase import TAU, continuous_unwrap, window_indices  # noqa: E402
from bvmtools.raw import RawTrace, read_csv  # noqa: E402
from bvmtools.waveform import trapezoid_integral  # noqa: E402


HEAD_BEFORE_TASK = "b8c6cbd33394b854dacf2c7348a1ebf1bc0b0d89"
OLD_RAW_SHA256 = "9563ac09d75770cd9d9c2f2a93de0f418778012e64adb40fbf118ae0561d813f"
NEW_RAW_SHA256 = "b3d421822dd893d17331016b7f954784d24c90c97f58bc362676467c7650998b"
S1_RAW_SHA256 = "4dd63aa296355a45256851f4628712732b75785ba67d69f4f2ef9ad8b0e92eab"

WINDOWS_PS = OrderedDict(
    (
        ("baseline_common", (45.0, 70.0)),
        ("history_intervention", (70.0, 81.0)),
        ("post_history_recovery", (81.0, 90.0)),
        ("write1", (90.0, 101.0)),
        ("pre_read1", (101.0, 110.0)),
        ("read1", (110.0, 121.0)),
        ("response_retrap", (121.0, 160.0)),
        ("tail", (160.0, 170.0)),
    )
)

CONTROLS = tuple(
    f"I(I_{kind}{number})"
    for number in range(1, 5)
    for kind in ("WL", "BL", "SE")
)


def _bvm_labels(number: int) -> list[str]:
    labels: list[str] = []
    for jj in ("B_JM1", "B_JM2", "B_JS1", "B_JS2"):
        labels.extend(
            [
                f"P({jj}|XBVM{number})",
                f"V({jj}|XBVM{number})",
                f"I({jj}|XBVM{number})",
            ]
        )
    labels.extend(
        [
            f"I(L_M1|XBVM{number})",
            f"I(L_M2|XBVM{number})",
            f"I(L_M3|XBVM{number})",
            f"I(L_PM|XBVM{number})",
            f"I(L_PSL|XBVM{number})",
            f"V(SL{number})",
            f"I(L_SL|XBVM{number})",
        ]
    )
    return labels


BVM_INTERNAL = tuple(
    label
    for number in range(1, 5)
    for label in _bvm_labels(number)
    if "L_PSL" not in label and "SL" not in label
)
SL = tuple(
    label
    for number in range(1, 5)
    for label in (
        f"I(L_PSL|XBVM{number})",
        f"V(SL{number})",
        f"I(L_SL|XBVM{number})",
    )
)
BVMOUT = ("P(BVMOUT)", "V(BVMOUT)", "I(BVMOUT)")
QB_INPUT = ("V(QBIN)", "V(QBOUT)", "I(LIN|XBQ1)")
QB_INTERNAL = (
    "P(BJS|XBQ1)",
    "V(BJS|XBQ1)",
    "I(BJS|XBQ1)",
    "P(BJ1|XBQ1)",
    "V(BJ1|XBQ1)",
    "I(BJ1|XBQ1)",
    "I(RJ1|XBQ1)",
    "I(L1|XBQ1)",
    "I(IB|XBQ1)",
    "I(L2|XBQ1)",
    "P(BJ2|XBQ1)",
    "V(BJ2|XBQ1)",
    "I(BJ2|XBQ1)",
    "I(RJ2|XBQ1)",
    "I(L3|XBQ1)",
)
JTL = tuple(
    f"{kind}(B{jj}|XJTL1_{stage})"
    for stage in range(1, 7)
    for jj in ("01", "02")
    for kind in ("P", "V")
)
SENSING = tuple(
    label
    for label in (
        "P(B_LD4_01)",
        "V(B_LD4_01)",
        "I(B_LD4_01)",
        "P(B_LD4_11)",
        "V(B_LD4_11)",
        "I(B_LD4_11)",
        "P(B_LD01)",
        "V(B_LD01)",
        "I(B_LD01)",
        "P(B_LD12)",
        "V(B_LD12)",
        "I(B_LD12)",
        "P(B_LD2_01)",
        "V(B_LD2_01)",
        "I(B_LD2_01)",
        "P(B_LD2_12)",
        "V(B_LD2_12)",
        "I(B_LD2_12)",
        "P(B_LD3_01)",
        "V(B_LD3_01)",
        "I(B_LD3_01)",
        "P(B_LD3_12)",
        "V(B_LD3_12)",
        "I(B_LD3_12)",
    )
)

GROUPS = OrderedDict(
    (
        ("controls", CONTROLS),
        ("bvm_internal", BVM_INTERNAL),
        ("sl", SL),
        ("bvmout", BVMOUT),
        ("qb_input", QB_INPUT),
        ("qb_internal", QB_INTERNAL),
        ("jtl", JTL),
        ("sensing", SENSING),
    )
)

LAYER_GROUPS = OrderedDict(
    (
        ("controls", CONTROLS),
        ("bvm_r_loop", BVM_INTERNAL),
        ("sl", SL),
        ("sensing", SENSING),
        ("qbin_lin", QB_INPUT),
        ("qb_internal", QB_INTERNAL),
        ("jtl", JTL),
    )
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git_value(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args], cwd=REPO, capture_output=True, text=True, check=False
    )
    return completed.stdout.strip()


def csv_time_tokens(path: Path) -> tuple[list[str], list[str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.reader(handle)
        header = next(reader)
        if header.count("time") != 1:
            raise RuntimeError(f"{path}: expected one exact time header")
        time_index = header.index("time")
        tokens = [row[time_index] for row in reader if row and any(cell.strip() for cell in row)]
    return header, tokens


def ps(value_s: float) -> float:
    return float(value_s) * 1.0e12


def time_indices(trace: RawTrace, bounds_ps: tuple[float, float]) -> tuple[int, ...]:
    return window_indices(trace.time, bounds_ps[0] * 1.0e-12, bounds_ps[1] * 1.0e-12)


def exact_index(trace: RawTrace, target_ps: float) -> tuple[int, float]:
    target_s = target_ps * 1.0e-12
    index = min(range(len(trace.time)), key=lambda item: abs(trace.time[item] - target_s))
    return index, ps(trace.time[index])


def display_spec(signal: str) -> tuple[str, str, float]:
    if signal.startswith("P"):
        return "rad", "turns", 1.0 / TAU
    if signal.startswith("V"):
        return "V", "mV", 1.0e3
    if signal.startswith("I"):
        return "A", "uA", 1.0e6
    return "raw", "raw", 1.0


def display_value(signal: str, value: float) -> float:
    return float(value) * display_spec(signal)[2]


def series_for(
    trace: RawTrace,
    signal: str,
    phase_cache: dict[str, tuple[float, ...]] | None = None,
) -> tuple[float, ...]:
    if signal.startswith("P"):
        if phase_cache is None:
            return continuous_unwrap(trace.column(signal))
        if signal not in phase_cache:
            phase_cache[signal] = continuous_unwrap(trace.column(signal))
        return phase_cache[signal]
    return trace.column(signal)


def waveform_summary(
    trace: RawTrace,
    signal: str,
    indices: Sequence[int],
    phase_cache: dict[str, tuple[float, ...]],
) -> dict[str, object]:
    values = series_for(trace, signal, phase_cache)
    selected_times = [trace.time[index] for index in indices]
    selected = [float(values[index]) for index in indices]
    native_unit, unit, factor = display_spec(signal)
    abs_index = max(range(len(selected)), key=lambda index: abs(selected[index]))
    max_index = max(range(len(selected)), key=lambda index: selected[index])
    min_index = min(range(len(selected)), key=lambda index: selected[index])
    return {
        "native_unit": native_unit,
        "unit": unit,
        "sample_count": len(selected),
        "minimum": selected[min_index] * factor,
        "maximum": selected[max_index] * factor,
        "mean": sum(selected) / len(selected) * factor,
        "rms": math.sqrt(sum(value * value for value in selected) / len(selected)) * factor,
        "peak_abs": selected[abs_index] * factor,
        "peak_abs_time_ps": ps(selected_times[abs_index]),
        "peak_positive_time_ps": ps(selected_times[max_index]),
        "minimum_time_ps": ps(selected_times[min_index]),
    }


def difference_stats(
    old: RawTrace,
    new: RawTrace,
    signal: str,
    bounds_ps: tuple[float, float],
    phase_old: dict[str, tuple[float, ...]],
    phase_new: dict[str, tuple[float, ...]],
    *,
    include_waveforms: bool = False,
) -> dict[str, object]:
    indices_old = time_indices(old, bounds_ps)
    indices_new = time_indices(new, bounds_ps)
    if len(indices_old) != len(indices_new):
        raise RuntimeError(f"{signal}: window sample counts differ without interpolation")
    times = [old.time[index] for index in indices_old]
    old_values = series_for(old, signal, phase_old)
    new_values = series_for(new, signal, phase_new)
    left = [float(old_values[index]) for index in indices_old]
    right = [float(new_values[index]) for index in indices_new]
    differences = [new_value - old_value for old_value, new_value in zip(left, right)]
    abs_index = max(range(len(differences)), key=lambda index: abs(differences[index]))
    max_index = max(range(len(differences)), key=lambda index: differences[index])
    min_index = min(range(len(differences)), key=lambda index: differences[index])
    native_unit, unit, factor = display_spec(signal)
    signed_integral = trapezoid_integral(differences, times) if len(differences) >= 2 else 0.0
    result: dict[str, object] = {
        "signal": signal,
        "native_unit": native_unit,
        "unit": unit,
        "window_ps": [bounds_ps[0], bounds_ps[1]],
        "sample_count": len(differences),
        "max_abs_difference_native": max(abs(value) for value in differences),
        "rms_difference_native": math.sqrt(
            sum(value * value for value in differences) / len(differences)
        ),
        "max_abs_difference_display": max(abs(value) for value in differences) * factor,
        "rms_difference_display": math.sqrt(
            sum(value * value for value in differences) / len(differences)
        )
        * factor,
        "max_positive_difference_display": differences[max_index] * factor,
        "max_negative_difference_display": differences[min_index] * factor,
        "peak_abs_difference_time_ps": ps(times[abs_index]),
        "first_sample_ps": ps(times[0]),
        "last_sample_ps": ps(times[-1]),
        "signed_integral_new_minus_old_native_times_s": signed_integral,
        "endpoint": {
            "old_native": left[-1],
            "new_native": right[-1],
            "new_minus_old_native": differences[-1],
            "old_display": left[-1] * factor,
            "new_display": right[-1] * factor,
            "new_minus_old_display": differences[-1] * factor,
        },
        "startpoint": {
            "old_display": left[0] * factor,
            "new_display": right[0] * factor,
            "new_minus_old_display": differences[0] * factor,
        },
    }
    if signal.startswith("P"):
        result["phase_difference_start_turns"] = differences[0] / TAU
        result["phase_difference_end_turns"] = differences[-1] / TAU
        result["phase_displacement_difference_turns"] = (differences[-1] - differences[0]) / TAU
    if include_waveforms:
        result["old_waveform"] = waveform_summary(old, signal, indices_old, phase_old)
        result["new_waveform"] = waveform_summary(new, signal, indices_new, phase_new)
    return result


def available_groups(common: set[str]) -> tuple[dict[str, tuple[str, ...]], dict[str, list[str]]]:
    selected: dict[str, tuple[str, ...]] = {}
    missing: dict[str, list[str]] = {}
    for name, labels in GROUPS.items():
        selected[name] = tuple(label for label in labels if label in common)
        missing[name] = [label for label in labels if label not in common]
    return selected, missing


def first_unequal(
    old: RawTrace,
    new: RawTrace,
    signal: str,
    start_ps: float,
    phase_old: dict[str, tuple[float, ...]],
    phase_new: dict[str, tuple[float, ...]],
) -> dict[str, object] | None:
    old_values = series_for(old, signal, phase_old)
    new_values = series_for(new, signal, phase_new)
    for index, time in enumerate(old.time):
        if ps(time) < start_ps:
            continue
        difference = float(new_values[index]) - float(old_values[index])
        if difference != 0.0:
            return {
                "signal": signal,
                "time_ps": ps(time),
                "difference_native": difference,
                "difference_display": display_value(signal, difference),
            }
    return None


def first_robust(
    old: RawTrace,
    new: RawTrace,
    signal: str,
    start_ps: float,
    phase_old: dict[str, tuple[float, ...]],
    phase_new: dict[str, tuple[float, ...]],
    persistence: int = 3,
) -> dict[str, object] | None:
    old_values = series_for(old, signal, phase_old)
    new_values = series_for(new, signal, phase_new)
    pre_indices = time_indices(old, WINDOWS_PS["baseline_common"])
    post_indices = [index for index, time in enumerate(old.time) if ps(time) >= start_ps]
    all_scale = max(
        max(abs(float(old_values[index])) for index in post_indices),
        max(abs(float(new_values[index])) for index in post_indices),
        1.0e-30,
    )
    pre_floor = max(
        abs(float(new_values[index]) - float(old_values[index])) for index in pre_indices
    )
    threshold = max(10.0 * pre_floor, 1.0e-6 * all_scale)
    for position in range(len(post_indices) - persistence + 1):
        candidate = post_indices[position]
        window = post_indices[position : position + persistence]
        if all(
            abs(float(new_values[index]) - float(old_values[index])) > threshold
            for index in window
        ):
            difference = float(new_values[candidate]) - float(old_values[candidate])
            return {
                "signal": signal,
                "time_ps": ps(old.time[candidate]),
                "difference_native": difference,
                "difference_display": display_value(signal, difference),
                "threshold_native": threshold,
                "threshold_display": threshold * display_spec(signal)[2],
                "persistence_samples": persistence,
                "definition": "max(10*pre70_max_abs, 1e-6*max(post_pair_waveform_abs_scale)); consecutive exact-grid samples",
                "descriptive_only": True,
            }
    return {
        "signal": signal,
        "time_ps": None,
        "difference_native": None,
        "difference_display": None,
        "threshold_native": threshold,
        "threshold_display": threshold * display_spec(signal)[2],
        "persistence_samples": persistence,
        "definition": "max(10*pre70_max_abs, 1e-6*max(post_pair_waveform_abs_scale)); consecutive exact-grid samples",
        "descriptive_only": True,
    }


def layer_divergence(
    old: RawTrace,
    new: RawTrace,
    labels_by_layer: OrderedDict[str, tuple[str, ...]],
    phase_old: dict[str, tuple[float, ...]],
    phase_new: dict[str, tuple[float, ...]],
) -> dict[str, object]:
    output: dict[str, object] = {}
    for layer, labels in labels_by_layer.items():
        exact = [
            item
            for label in labels
            if (item := first_unequal(old, new, label, 70.0, phase_old, phase_new)) is not None
        ]
        robust = [
            item
            for label in labels
            if (item := first_robust(old, new, label, 70.0, phase_old, phase_new)) is not None
            and item["time_ps"] is not None
        ]
        exact.sort(key=lambda item: (float(item["time_ps"]), str(item["signal"])))
        robust.sort(key=lambda item: (float(item["time_ps"]), str(item["signal"])))
        output[layer] = {
            "first_exact": exact[0] if exact else None,
            "first_robust": robust[0] if robust else None,
            "exact_by_signal": exact,
            "robust_by_signal": robust,
        }
    return output


def checkpoint_diff(
    old: RawTrace,
    new: RawTrace,
    labels: Iterable[str],
    targets_ps: Sequence[float],
    phase_old: dict[str, tuple[float, ...]],
    phase_new: dict[str, tuple[float, ...]],
) -> dict[str, object]:
    result: dict[str, object] = {}
    for target in targets_ps:
        old_index, old_actual = exact_index(old, target)
        new_index, new_actual = exact_index(new, target)
        if old_actual != new_actual:
            raise RuntimeError(f"checkpoint {target} ps does not select the same actual time")
        values: dict[str, object] = {}
        for signal in labels:
            if signal not in old.headers or signal not in new.headers:
                continue
            old_value = float(series_for(old, signal, phase_old)[old_index])
            new_value = float(series_for(new, signal, phase_new)[new_index])
            values[signal] = {
                "unit": display_spec(signal)[1],
                "old": display_value(signal, old_value),
                "new": display_value(signal, new_value),
                "new_minus_old": display_value(signal, new_value - old_value),
            }
        result[str(target)] = {"requested_ps": target, "actual_ps": old_actual, "signals": values}
    return result


def checkpoint_group_max(
    old: RawTrace,
    new: RawTrace,
    labels_by_group: OrderedDict[str, tuple[str, ...]],
    targets_ps: Sequence[float],
    phase_old: dict[str, tuple[float, ...]],
    phase_new: dict[str, tuple[float, ...]],
) -> dict[str, object]:
    output: dict[str, object] = {}
    for target in targets_ps:
        old_index, actual = exact_index(old, target)
        new_index, new_actual = exact_index(new, target)
        if actual != new_actual:
            raise RuntimeError("old/new checkpoint grids disagree")
        group_values: dict[str, object] = {}
        for group, labels in labels_by_group.items():
            per_unit: dict[str, dict[str, object]] = {}
            for signal in labels:
                old_value = float(series_for(old, signal, phase_old)[old_index])
                new_value = float(series_for(new, signal, phase_new)[new_index])
                difference_display = display_value(signal, new_value - old_value)
                unit = display_spec(signal)[1]
                current = per_unit.get(unit)
                candidate = {
                    "signal": signal,
                    "unit": unit,
                    "abs_difference": abs(difference_display),
                    "new_minus_old": difference_display,
                }
                if current is None or abs(difference_display) > float(current["abs_difference"]):
                    per_unit[unit] = candidate
            group_values[group] = per_unit
        output[str(target)] = {"actual_ps": actual, "by_group_and_unit": group_values}
    return output


def state_specs(number: int) -> list[tuple[str, str]]:
    specs: list[tuple[str, str]] = []
    for jj, short in (("B_JM1", "JM1"), ("B_JM2", "JM2"), ("B_JS1", "JS1"), ("B_JS2", "JS2")):
        specs.extend(
            [
                (f"{short}_phase_turns", f"P({jj}|XBVM{number})"),
                (f"{short}_voltage_mV", f"V({jj}|XBVM{number})"),
                (f"{short}_current_uA", f"I({jj}|XBVM{number})"),
            ]
        )
    specs.extend(
        [
            ("LM1_current_uA", f"I(L_M1|XBVM{number})"),
            ("LM2_current_uA", f"I(L_M2|XBVM{number})"),
            ("LM3_current_uA", f"I(L_M3|XBVM{number})"),
            ("LPM_current_uA", f"I(L_PM|XBVM{number})"),
            ("LPSL_current_uA", f"I(L_PSL|XBVM{number})"),
            ("SL_voltage_mV", f"V(SL{number})"),
            ("LSL_current_uA", f"I(L_SL|XBVM{number})"),
        ]
    )
    return specs


def state_vector(
    trace: RawTrace,
    phase_cache: dict[str, tuple[float, ...]],
    index: int,
    number: int,
) -> dict[str, float]:
    result: dict[str, float] = {}
    for name, signal in state_specs(number):
        if signal not in trace.headers:
            result[name] = math.nan
            continue
        result[name] = display_value(signal, series_for(trace, signal, phase_cache)[index])
    return result


def state_vector_pair(
    old: RawTrace,
    new: RawTrace,
    phase_old: dict[str, tuple[float, ...]],
    phase_new: dict[str, tuple[float, ...]],
    target_ps: float,
    number: int,
) -> dict[str, object]:
    old_index, old_actual = exact_index(old, target_ps)
    new_index, new_actual = exact_index(new, target_ps)
    if old_actual != new_actual:
        raise RuntimeError("state vector checkpoint grid mismatch")
    old_state = state_vector(old, phase_old, old_index, number)
    new_state = state_vector(new, phase_new, new_index, number)
    difference = {
        name: new_state[name] - old_state[name]
        for name in old_state
        if math.isfinite(old_state[name]) and math.isfinite(new_state[name])
    }
    return {
        "requested_ps": target_ps,
        "actual_ps": old_actual,
        "old": old_state,
        "new": new_state,
        "new_minus_old": difference,
    }


def network_specs() -> list[tuple[str, str]]:
    specs: list[tuple[str, str]] = []
    for number in range(1, 5):
        specs.extend(
            [
                (f"SL{number}_voltage_mV", f"V(SL{number})"),
                (f"LPSL{number}_current_uA", f"I(L_PSL|XBVM{number})"),
                (f"LSL{number}_current_uA", f"I(L_SL|XBVM{number})"),
            ]
        )
    specs.extend(
        [
            ("BVMOUT_phase_turns", "P(BVMOUT)"),
            ("BVMOUT_voltage_mV", "V(BVMOUT)"),
            ("BVMOUT_current_uA", "I(BVMOUT)"),
            ("QBIN_voltage_mV", "V(QBIN)"),
            ("QBOUT_voltage_mV", "V(QBOUT)"),
            ("LIN_current_uA", "I(LIN|XBQ1)"),
            ("BJS_phase_turns", "P(BJS|XBQ1)"),
            ("BJS_voltage_mV", "V(BJS|XBQ1)"),
            ("BJS_current_uA", "I(BJS|XBQ1)"),
            ("BJ1_phase_turns", "P(BJ1|XBQ1)"),
            ("BJ1_voltage_mV", "V(BJ1|XBQ1)"),
            ("BJ1_current_uA", "I(BJ1|XBQ1)"),
            ("RJ1_current_uA", "I(RJ1|XBQ1)"),
            ("L1_current_uA", "I(L1|XBQ1)"),
            ("IB_current_uA", "I(IB|XBQ1)"),
            ("L2_current_uA", "I(L2|XBQ1)"),
            ("BJ2_phase_turns", "P(BJ2|XBQ1)"),
            ("BJ2_voltage_mV", "V(BJ2|XBQ1)"),
            ("BJ2_current_uA", "I(BJ2|XBQ1)"),
            ("RJ2_current_uA", "I(RJ2|XBQ1)"),
            ("L3_current_uA", "I(L3|XBQ1)"),
        ]
    )
    return specs


def network_state_vector(
    trace: RawTrace,
    phase_cache: dict[str, tuple[float, ...]],
    index: int,
) -> dict[str, float]:
    result: dict[str, float] = {}
    for name, signal in network_specs():
        if signal not in trace.headers:
            result[name] = math.nan
            continue
        result[name] = display_value(signal, series_for(trace, signal, phase_cache)[index])
    return result


def network_state_pair(
    old: RawTrace,
    new: RawTrace,
    phase_old: dict[str, tuple[float, ...]],
    phase_new: dict[str, tuple[float, ...]],
    target_ps: float,
) -> dict[str, object]:
    old_index, actual = exact_index(old, target_ps)
    new_index, new_actual = exact_index(new, target_ps)
    if actual != new_actual:
        raise RuntimeError("network state checkpoint grid mismatch")
    old_state = network_state_vector(old, phase_old, old_index)
    new_state = network_state_vector(new, phase_new, new_index)
    diff = {
        name: new_state[name] - old_state[name]
        for name in old_state
        if math.isfinite(old_state[name]) and math.isfinite(new_state[name])
    }
    return {"requested_ps": target_ps, "actual_ps": actual, "old": old_state, "new": new_state, "new_minus_old": diff}


def pwl_number(token: str) -> float:
    match = re.fullmatch(
        r"([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)([A-Za-z]*)", token.strip()
    )
    if match is None:
        raise ValueError(f"unsupported engineering token: {token!r}")
    scale = {
        "": 1.0,
        "t": 1.0e12,
        "g": 1.0e9,
        "meg": 1.0e6,
        "k": 1.0e3,
        "m": 1.0e-3,
        "u": 1.0e-6,
        "n": 1.0e-9,
        "p": 1.0e-12,
        "f": 1.0e-15,
    }
    suffix = match.group(2).lower()
    if suffix not in scale:
        raise ValueError(f"unsupported engineering suffix: {suffix!r}")
    return float(match.group(1)) * scale[suffix]


def source_pwl_points(line: str) -> list[tuple[float, float]]:
    match = re.search(r"pwl\((.*)\)", line, re.IGNORECASE)
    if match is None:
        raise ValueError(f"no PWL expression in {line!r}")
    tokens = match.group(1).replace("+", " +").split()
    if len(tokens) % 2:
        raise ValueError(f"odd PWL token count in {line!r}")
    return [(pwl_number(tokens[index]), pwl_number(tokens[index + 1])) for index in range(0, len(tokens), 2)]


def pwl_at(points: Sequence[tuple[float, float]], time_ps: float) -> float:
    target = time_ps * 1.0e-12
    if target <= points[0][0]:
        return points[0][1]
    for (left_t, left_v), (right_t, right_v) in zip(points, points[1:]):
        if target <= right_t:
            fraction = (target - left_t) / (right_t - left_t) if right_t != left_t else 0.0
            return left_v + fraction * (right_v - left_v)
    return points[-1][1]


def deck_category(line: str) -> str:
    stripped = line.strip()
    if not stripped:
        return "blank_formatting"
    if stripped.startswith("*"):
        return "comment_provenance"
    if stripped.lower().startswith(".print"):
        return "observability_only_print"
    if re.match(r"^I_(?:WL|BL|SE)[1-4]\s", stripped, re.IGNORECASE):
        return "physics_protocol_control"
    return "other"


def deck_diff_summary() -> dict[str, object]:
    old_lines = OLD_DECK.read_text(encoding="utf-8").splitlines()
    new_lines = NEW_DECK.read_text(encoding="utf-8").splitlines()
    matcher = difflib.SequenceMatcher(a=old_lines, b=new_lines, autojunk=False)
    changes: list[dict[str, object]] = []
    categorized: dict[str, list[dict[str, object]]] = {
        "physics_protocol_control": [],
        "observability_only_print": [],
        "comment_provenance": [],
        "blank_formatting": [],
        "other": [],
    }
    for tag, old_start, old_end, new_start, new_end in matcher.get_opcodes():
        if tag == "equal":
            continue
        removed = old_lines[old_start:old_end]
        added = new_lines[new_start:new_end]
        categories = sorted({deck_category(line) for line in removed + added})
        category = categories[0] if len(categories) == 1 else "mixed_change_block"
        item = {
            "opcode": tag,
            "old_line_numbers": [old_start + 1, old_end],
            "new_line_numbers": [new_start + 1, new_end],
            "category": category,
            "removed": removed,
            "added": added,
        }
        changes.append(item)
        for side, lines, start_line in (
            ("removed", removed, old_start + 1),
            ("added", added, new_start + 1),
        ):
            for offset, line in enumerate(lines):
                line_category = deck_category(line)
                categorized.setdefault(line_category, []).append(
                    {
                        "opcode": tag,
                        "side": side,
                        "line_number": start_line + offset,
                        "line": line,
                    }
                )

    old_controls: dict[str, str] = {}
    new_controls: dict[str, str] = {}
    for line in old_lines:
        match = re.match(r"^(I_(?:WL|BL|SE)[1-4])\s", line.strip(), re.IGNORECASE)
        if match:
            old_controls[match.group(1).upper()] = line.strip()
    for line in new_lines:
        match = re.match(r"^(I_(?:WL|BL|SE)[1-4])\s", line.strip(), re.IGNORECASE)
        if match:
            new_controls[match.group(1).upper()] = line.strip()
    semantic_samples = [70.0, 75.0, 80.0, 85.0, 95.0, 115.0]
    control_semantics: dict[str, object] = {}
    for name in sorted(set(old_controls) | set(new_controls)):
        old_points = source_pwl_points(old_controls[name])
        new_points = source_pwl_points(new_controls[name])
        control_semantics[name] = {
            "samples_uA": {
                str(time): {
                    "old": pwl_at(old_points, time) * 1.0e6,
                    "new": pwl_at(new_points, time) * 1.0e6,
                    "new_minus_old": (pwl_at(new_points, time) - pwl_at(old_points, time)) * 1.0e6,
                }
                for time in semantic_samples
            },
            "old_line": old_controls[name],
            "new_line": new_controls[name],
        }

    def core_without_control_print_comment(lines: Sequence[str]) -> list[str]:
        result: list[str] = []
        for line in lines:
            category = deck_category(line)
            if category in {"comment_provenance", "observability_only_print", "physics_protocol_control", "blank_formatting"}:
                continue
            result.append(line.strip())
        return result

    old_print = [line.strip() for line in old_lines if line.strip().lower().startswith(".print")]
    new_print = [line.strip() for line in new_lines if line.strip().lower().startswith(".print")]
    source_lines_differ = [name for name in sorted(old_controls) if old_controls.get(name) != new_controls.get(name)]
    core_equal = core_without_control_print_comment(old_lines) == core_without_control_print_comment(new_lines)

    def active_lines(lines: Sequence[str]) -> list[str]:
        return [line.strip() for line in lines if line.strip() and not line.strip().startswith("*")]

    old_active = active_lines(old_lines)
    new_active = active_lines(new_lines)

    def exact_active_line(line: str) -> bool:
        return line in old_active and line in new_active

    def controls_equal_at(time_ps: float) -> bool:
        return all(
            abs(
                pwl_at(source_pwl_points(old_controls[name]), time_ps)
                - pwl_at(source_pwl_points(new_controls[name]), time_ps)
            )
            == 0.0
            for name in old_controls
        )

    return {
        "schema": "deck-diff-summary-v1",
        "old_deck_sha256": sha256(OLD_DECK),
        "new_deck_sha256": sha256(NEW_DECK),
        "line_counts": {"old": len(old_lines), "new": len(new_lines)},
        "all_changes": changes,
        "categorized_change_counts": {key: len(value) for key, value in categorized.items()},
        "physics_protocol_differences": {
            "changed_control_sources": source_lines_differ,
            "lines": categorized["physics_protocol_control"],
            "semantic_samples": control_semantics,
            "read0_semantics": {
                "old": "all BVM WL and SE are +100 uA on the 71-80 ps plateau",
                "new": "all BVM WL and SE are 0 during the 70-90 ps no-op interval",
                "difference": "OLD has an all-BVM positive READ history; NEW does not",
            },
            "write0_semantics_equal_at_55ps": controls_equal_at(55.0),
            "write1_semantics_equal_at_95ps": controls_equal_at(95.0),
            "read1_semantics_equal_at_115ps": controls_equal_at(115.0),
        },
        "observability_only_differences": {
            "old_print_line_count": len(old_print),
            "new_print_line_count": len(new_print),
            "new_only_print_lines": [line for line in new_print if line not in old_print],
            "lines": categorized["observability_only_print"],
            "interpretation": "NEW appends direct BVM branch probes; these do not alter circuit equations",
        },
        "comment_provenance_differences": {
            "lines": categorized["comment_provenance"],
            "interpretation": "comments and generated-deck provenance only",
        },
        "unexpected_nonclassified_differences": categorized["other"],
        "fixed_core_equal_after_excluding_controls_prints_comments": core_equal,
        "fixed_targets": {
            "bvm_topology_and_jm2_variant": core_equal and all(
                any(line.lower().startswith(f"xbvm{number} ") for line in old_active)
                and any(line.lower().startswith(f"xbvm{number} ") for line in new_active)
                for number in range(1, 5)
            ),
            "sensing_topology": core_equal and sum(line.startswith("B_LD") for line in old_active) == sum(line.startswith("B_LD") for line in new_active),
            "qb": core_equal and exact_active_line("xBQ1 QBin QBout BQ"),
            "jtl": core_equal and all(
                any(line.lower().startswith(f"xjtl1_{stage} ") for line in old_active)
                and any(line.lower().startswith(f"xjtl1_{stage} ") for line in new_active)
                for stage in range(1, 7)
            ),
            "final_10_ohm_load": core_equal and exact_active_line("RBQ1 o6 0 10"),
            "timestep_stop_output_start": core_equal and exact_active_line(".tran 0.1p 200p 45p"),
            "write0_semantics": controls_equal_at(55.0),
            "write1_semantics": controls_equal_at(95.0),
            "final_read1_semantics": controls_equal_at(115.0),
        },
    }


def group_window_comparisons(
    old: RawTrace,
    new: RawTrace,
    groups: dict[str, tuple[str, ...]],
    bounds_ps: tuple[float, float],
    phase_old: dict[str, tuple[float, ...]],
    phase_new: dict[str, tuple[float, ...]],
    *,
    include_waveforms: bool = False,
) -> dict[str, object]:
    output: dict[str, object] = {}
    for group, labels in groups.items():
        by_signal = {
            signal: difference_stats(
                old,
                new,
                signal,
                bounds_ps,
                phase_old,
                phase_new,
                include_waveforms=include_waveforms,
            )
            for signal in labels
        }
        output[group] = {
            "window_ps": list(bounds_ps),
            "signal_count": len(by_signal),
            "by_signal": by_signal,
        }
    return output


def key_signal_stats(
    old: RawTrace,
    new: RawTrace,
    labels: Iterable[str],
    bounds_ps: tuple[float, float],
    phase_old: dict[str, tuple[float, ...]],
    phase_new: dict[str, tuple[float, ...]],
    *,
    include_waveforms: bool = False,
) -> dict[str, object]:
    return {
        signal: difference_stats(
            old,
            new,
            signal,
            bounds_ps,
            phase_old,
            phase_new,
            include_waveforms=include_waveforms,
        )
        for signal in labels
        if signal in old.headers and signal in new.headers
    }


def integer_crossings(
    trace: RawTrace,
    phase_cache: dict[str, tuple[float, ...]],
    signal: str,
    bounds_ps: tuple[float, float],
    max_crossings: int = 8,
) -> dict[str, object]:
    indices = time_indices(trace, bounds_ps)
    phase = series_for(trace, signal, phase_cache)
    start = indices[0]
    end = indices[-1]
    baseline = phase[start]
    net_turns = (phase[end] - baseline) / TAU
    direction = 1 if net_turns >= 0.0 else -1
    crossings: list[dict[str, object]] = []
    for number in range(1, max_crossings + 1):
        target = baseline + direction * number * TAU
        found = None
        for index in range(start, end + 1):
            offset = direction * (phase[index] - baseline)
            if offset >= number * TAU:
                found = index
                break
        if found is None:
            continue
        previous_delta = phase[found] - phase[found - 1] if found > start else 0.0
        crossings.append(
            {
                "integer_index": number,
                "direction": direction,
                "direction_label": "+" if direction > 0 else "-",
                "sample_time_ps": ps(trace.time[found]),
                "phase_turns_at_sample": phase[found] / TAU,
                "offset_from_window_start_turns": (phase[found] - baseline) / TAU,
                "local_increment_rad": previous_delta,
                "sample_based_no_interpolation": True,
            }
        )
    return {
        "signal": signal,
        "window_ps": list(bounds_ps),
        "window_start_phase_turns": baseline / TAU,
        "window_end_phase_turns": phase[end] / TAU,
        "net_turns_from_window_start": net_turns,
        "direction": direction,
        "integer_crossings": crossings,
        "interpretation": "trajectory markers only; not clean SFQ event counts",
    }


def retrap_indicator(
    trace: RawTrace,
    phase_cache: dict[str, tuple[float, ...]],
    voltage_signal: str = "V(BJ2|XBQ1)",
    current_signal: str = "I(BJ2|XBQ1)",
    phase_signal: str = "P(BJ2|XBQ1)",
    bounds_ps: tuple[float, float] = (121.0, 170.0),
    threshold_mV: float = 0.05,
    persistence: int = 3,
) -> dict[str, object]:
    phase_info = integer_crossings(trace, phase_cache, phase_signal, (110.0, 170.0))
    crossings = phase_info["integer_crossings"]
    voltage = trace.column(voltage_signal)
    current = trace.column(current_signal)
    phase = series_for(trace, phase_signal, phase_cache)
    response_indices = time_indices(trace, bounds_ps)
    last_crossing = crossings[-1] if crossings else None
    last_crossing_index = None
    if last_crossing is not None:
        requested_ps = float(last_crossing["sample_time_ps"])
        last_crossing_index, _ = exact_index(trace, requested_ps)
    start_position = 0
    if last_crossing_index is not None:
        start_position = max(0, response_indices.index(last_crossing_index) + 1) if last_crossing_index in response_indices else 0
    candidate_index = None
    for position in range(start_position, len(response_indices) - persistence + 1):
        window = response_indices[position : position + persistence]
        if all(abs(float(voltage[index])) <= threshold_mV * 1.0e-3 for index in window):
            candidate_index = window[0]
            break
    tail_indices = time_indices(trace, (160.0, 170.0))
    tail_phase = [phase[index] / TAU for index in tail_indices]
    tail_voltage = [voltage[index] * 1.0e3 for index in tail_indices]
    tail_current = [current[index] * 1.0e6 for index in tail_indices]
    return {
        "indicator_definition": {
            "absolute_voltage_threshold_mV": threshold_mV,
            "persistence_samples": persistence,
            "after_last_integer_crossing": True,
            "descriptive_only": True,
            "not_a_global_retrap_or_sfq_metric": True,
        },
        "last_integer_crossing": last_crossing,
        "quiescent_like_return": None
        if candidate_index is None
        else {
            "sample_time_ps": ps(trace.time[candidate_index]),
            "voltage_mV": voltage[candidate_index] * 1.0e3,
            "current_uA": current[candidate_index] * 1.0e6,
            "phase_turns": phase[candidate_index] / TAU,
        },
        "tail_160_170ps": {
            "phase_start_turns": tail_phase[0],
            "phase_end_turns": tail_phase[-1],
            "phase_delta_turns": tail_phase[-1] - tail_phase[0],
            "voltage_min_mV": min(tail_voltage),
            "voltage_max_mV": max(tail_voltage),
            "voltage_mean_mV": sum(tail_voltage) / len(tail_voltage),
            "current_min_uA": min(tail_current),
            "current_max_uA": max(tail_current),
            "current_mean_uA": sum(tail_current) / len(tail_current),
        },
    }


def phase_trajectory_metrics(
    old: RawTrace,
    new: RawTrace,
    phase_old: dict[str, tuple[float, ...]],
    phase_new: dict[str, tuple[float, ...]],
) -> dict[str, object]:
    signal = "P(BJ2|XBQ1)"
    voltage = "V(BJ2|XBQ1)"
    old_phase_area = phase_area_window(
        old.time,
        old.column(signal),
        old.column(voltage),
        (110.0e-12, 170.0e-12),
        include_segments=False,
    )
    new_phase_area = phase_area_window(
        new.time,
        new.column(signal),
        new.column(voltage),
        (110.0e-12, 170.0e-12),
        include_segments=False,
    )
    old_crossings = integer_crossings(old, phase_old, signal, (110.0, 170.0), 6)
    new_crossings = integer_crossings(new, phase_new, signal, (110.0, 170.0), 6)
    indices = time_indices(old, (110.0, 170.0))
    old_u = phase_old[signal]
    new_u = phase_new[signal]
    phase_difference_turns = [(new_u[index] - old_u[index]) / TAU for index in indices]
    phase_diff_by_ps: dict[str, object] = {}
    for target in (110.0, 111.0, 112.0, 113.0, 114.0, 115.0, 118.0, 118.3, 119.0, 120.0, 121.0, 122.0, 124.0, 125.0, 126.0, 128.0, 129.0, 129.5, 130.0, 132.0, 135.0, 138.0, 138.8, 140.0, 141.4, 145.0, 150.0, 160.0, 169.9):
        index, actual = exact_index(old, target)
        new_index, new_actual = exact_index(new, target)
        if actual != new_actual:
            raise RuntimeError("BJ2 checkpoint grid mismatch")
        phase_diff_by_ps[str(target)] = {
            "actual_ps": actual,
            "new_minus_old_turns": (new_u[new_index] - old_u[index]) / TAU,
            "old_phase_turns": old_u[index] / TAU,
            "new_phase_turns": new_u[new_index] / TAU,
        }
    return {
        "signal": signal,
        "display_rule": "P raw radians are continuously unwrapped, then divided by 2*pi for turns",
        "same_jj_voltage_signal": voltage,
        "old_110_170": old_phase_area,
        "new_110_170": new_phase_area,
        "old_integer_crossings": old_crossings,
        "new_integer_crossings": new_crossings,
        "new_minus_old_phase_difference_turns": {
            "start_110ps": phase_difference_turns[0],
            "end_169_9ps": phase_difference_turns[-1],
            "minimum": min(phase_difference_turns),
            "maximum": max(phase_difference_turns),
            "max_abs": max(abs(value) for value in phase_difference_turns),
        },
        "trajectory_checkpoint_difference": phase_diff_by_ps,
        "crossing_timing_comparison": {
            "by_integer_index": {
                str(number): {
                    "old_ps": next(
                        (item["sample_time_ps"] for item in old_crossings["integer_crossings"] if item["integer_index"] == number),
                        None,
                    ),
                    "new_ps": next(
                        (item["sample_time_ps"] for item in new_crossings["integer_crossings"] if item["integer_index"] == number),
                        None,
                    ),
                }
                for number in range(1, 7)
            }
        },
        "pattern_assessment": {
            "label": "WHOLE_TRAJECTORY_CHANGE_WITH_LATE_EXTRA_TURN",
            "basis": [
                "QB input and BJ2 phase differences are already present at READ1 start",
                "first three sample-based crossings remain close, but the fourth crossing shifts materially",
                "NEW has a fifth crossing after OLD is already near its four-turn quiescent-like tail",
            ],
            "not_late_tail_only": True,
            "not_a_clean_event_count_claim": True,
        },
    }


def read1_control_parity(
    old: RawTrace,
    new: RawTrace,
    phase_old: dict[str, tuple[float, ...]],
    phase_new: dict[str, tuple[float, ...]],
) -> dict[str, object]:
    stats = key_signal_stats(old, new, CONTROLS, WINDOWS_PS["read1"], phase_old, phase_new)
    return {
        "window_ps": list(WINDOWS_PS["read1"]),
        "all_common_controls_exactly_equal": all(
            item["max_abs_difference_native"] == 0.0 for item in stats.values()
        ),
        "by_signal": stats,
    }


def plot_signal_sets(common: set[str]) -> list[dict[str, object]]:
    def require(labels: Iterable[str]) -> list[str]:
        missing = [label for label in labels if label not in common]
        if missing:
            raise RuntimeError(f"plot requires missing common signals: {missing}")
        return list(labels)

    bvm_jm = [f"P(B_JM{jj}|XBVM{number})" for number in range(1, 5) for jj in (1, 2)]
    bvm_jm_lm3 = bvm_jm + [f"I(L_M3|XBVM{number})" for number in range(1, 5)]
    pre70 = [
        "I(I_WL1)",
        "I(I_SE1)",
        "P(B_JM1|XBVM1)",
        "P(B_JM2|XBVM1)",
        "P(B_JS1|XBVM1)",
        "V(SL1)",
        "P(BVMOUT)",
        "V(QBIN)",
        "I(LIN|XBQ1)",
        "P(BJ2|XBQ1)",
        "P(B01|XJTL1_1)",
        "P(B02|XJTL1_6)",
    ]
    pre_read1 = bvm_jm_lm3 + [
        "V(SL1)",
        "V(SL2)",
        "V(SL3)",
        "V(SL4)",
        "P(BVMOUT)",
        "V(QBIN)",
        "I(LIN|XBQ1)",
        "P(BJS|XBQ1)",
        "P(BJ1|XBQ1)",
        "P(BJ2|XBQ1)",
    ]
    read1 = [
        "V(SL1)",
        "V(SL2)",
        "V(SL3)",
        "V(SL4)",
        "I(L_SL|XBVM1)",
        "I(L_SL|XBVM2)",
        "I(L_SL|XBVM3)",
        "I(L_SL|XBVM4)",
        "P(BVMOUT)",
        "V(BVMOUT)",
        "I(BVMOUT)",
        "V(QBIN)",
        "I(LIN|XBQ1)",
        "P(BJ2|XBQ1)",
        "V(BJ2|XBQ1)",
    ]
    qb_tail = [
        "P(BJS|XBQ1)",
        "V(BJS|XBQ1)",
        "I(BJS|XBQ1)",
        "P(BJ1|XBQ1)",
        "V(BJ1|XBQ1)",
        "I(BJ1|XBQ1)",
        "P(BJ2|XBQ1)",
        "V(BJ2|XBQ1)",
        "I(BJ2|XBQ1)",
        "I(LIN|XBQ1)",
        "V(QBIN)",
        "I(L1|XBQ1)",
        "I(L2|XBQ1)",
        "I(L3|XBQ1)",
    ]
    layers_diff = [
        "P(B_JM1|XBVM1)",
        "P(B_JM2|XBVM1)",
        "V(SL1)",
        "I(L_SL|XBVM1)",
        "P(BVMOUT)",
        "V(QBIN)",
        "I(LIN|XBQ1)",
        "P(BJ2|XBQ1)",
        "P(B02|XJTL1_6)",
    ]
    controls_all = list(CONTROLS)
    return [
        {"name": "OLD_NEW_PROTOCOL_CONTROL", "bounds_ps": [45.0, 121.0], "signals": require(controls_all), "variants": ["old", "new"], "title": "OLD vs NEW 1111 — protocol controls and the 70–81 ps history intervention"},
        {"name": "PRE70_PARITY", "bounds_ps": [45.0, 70.0], "signals": require(pre70), "variants": ["old", "new"], "title": "OLD vs NEW 1111 — exact common-grid parity before 70 ps"},
        {"name": "READ0_HISTORY_DIVERGENCE_BVM", "bounds_ps": [70.0, 90.0], "signals": require(bvm_jm_lm3 + [f"V(SL{number})" for number in range(1, 5)]), "variants": ["old", "new"], "title": "OLD vs NEW 1111 — BVM/SL response to the READ0 history"},
        {"name": "WRITE1_HISTORY_DEPENDENCE", "bounds_ps": [90.0, 101.0], "signals": require(bvm_jm_lm3 + [f"P(B_JS1|XBVM{number})" for number in range(1, 5)]), "variants": ["old", "new"], "title": "OLD vs NEW 1111 — same WRITE1 input from different history"},
        {"name": "PRE_READ1_STATE_COMPARISON", "bounds_ps": [101.0, 110.0], "signals": require(pre_read1), "variants": ["old", "new"], "title": "OLD vs NEW 1111 — residual state immediately before READ1"},
        {"name": "READ1_QBIN_LIN_COMPARISON", "bounds_ps": [110.0, 121.0], "signals": require(read1), "variants": ["old", "new"], "title": "OLD vs NEW 1111 — READ1 input and QB trajectory onset"},
        {"name": "BJ2_4_VS_5_TURN", "bounds_ps": [110.0, 170.0], "signals": require(["P(BJ2|XBQ1)", "V(BJ2|XBQ1)"]), "variants": ["old", "new", "diff"], "title": "OLD vs NEW 1111 — BJ2 four-turn versus five-turn trajectory"},
        {"name": "BJ2_CROSSING_TIMELINE", "bounds_ps": [110.0, 150.0], "signals": require(["P(BJ2|XBQ1)", "V(BJ2|XBQ1)"]), "variants": ["old", "new"], "title": "OLD vs NEW 1111 — BJ2 integer-crossing timing markers"},
        {"name": "QB_RETRAP_TAIL_COMPARISON", "bounds_ps": [121.0, 170.0], "signals": require(qb_tail), "variants": ["old", "new"], "title": "OLD vs NEW 1111 — QB response, retrap indicator, and tail"},
        {"name": "JTL6_4_VS_5", "bounds_ps": [110.0, 170.0], "signals": require(["P(B02|XJTL1_1)", "P(B02|XJTL1_6)", "V(B02|XJTL1_6)"]), "variants": ["old", "new"], "title": "OLD vs NEW 1111 — JTL1 to JTL6 downstream trajectory"},
        {"name": "OLD_MINUS_NEW_MULTI_LAYER", "bounds_ps": [45.0, 170.0], "signals": require(layers_diff), "variants": ["diff"], "title": "NEW minus OLD — cross-layer history difference (common probes)"},
    ]


def write_plot_inputs(
    old: RawTrace,
    new: RawTrace,
    phase_old: dict[str, tuple[float, ...]],
    phase_new: dict[str, tuple[float, ...]],
    common: set[str],
) -> list[dict[str, object]]:
    output_dir = EXP / "analysis" / "plot_inputs"
    output_dir.mkdir(parents=True, exist_ok=True)
    manifests: list[dict[str, object]] = []
    for spec in plot_signal_sets(common):
        bounds = (float(spec["bounds_ps"][0]), float(spec["bounds_ps"][1]))
        indices = time_indices(old, bounds)
        columns: list[tuple[str, str]] = []
        for signal in spec["signals"]:
            variants = spec["variants"]
            if "old" in variants:
                columns.append((f"{signal} [OLD]", "old:" + signal))
            if "new" in variants:
                columns.append((f"{signal} [NEW]", "new:" + signal))
            if "diff" in variants:
                if signal.startswith("P"):
                    name = f"P(NEW-OLD {signal[2:-1]})"
                elif signal.startswith("V"):
                    name = f"V(NEW-OLD {signal[2:-1]})"
                elif signal.startswith("I"):
                    name = f"I(NEW-OLD {signal[2:-1]})"
                else:
                    name = f"D(NEW-OLD {signal})"
                columns.append((name, "diff:" + signal))
        input_path = output_dir / f"{spec['name']}.csv"
        with input_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle, lineterminator="\n")
            writer.writerow(["time"] + [name for name, _ in columns])
            for index in indices:
                row: list[float] = [old.time[index]]
                for _, source in columns:
                    variant, signal = source.split(":", 1)
                    if variant == "old":
                        value = series_for(old, signal, phase_old)[index]
                    elif variant == "new":
                        value = series_for(new, signal, phase_new)[index]
                    else:
                        value = series_for(new, signal, phase_new)[index] - series_for(old, signal, phase_old)[index]
                    row.append(float(value))
                writer.writerow(row)
        manifests.append(
            {
                "name": spec["name"],
                "input": str(input_path.relative_to(EXP)),
                "output": f"plots/{spec['name']}.html",
                "title": spec["title"],
                "bounds_ps": list(bounds),
                "signals": [name for name, _ in columns],
                "renderer": "scripts/josim-plot2.py",
                "options": {"type": "sep_comb", "color": "dark", "jump": "2pi"},
                "phase_input_note": "P columns contain continuous-unwrapped radians; josim-plot2 -j 2pi displays rad/(2*pi) turns",
            }
        )
    return manifests


def jtl_stage_crossings(
    old: RawTrace,
    new: RawTrace,
    phase_old: dict[str, tuple[float, ...]],
    phase_new: dict[str, tuple[float, ...]],
) -> dict[str, object]:
    result: dict[str, object] = {}
    for stage in range(1, 7):
        signal = f"P(B02|XJTL1_{stage})"
        result[f"JTL{stage}"] = {
            "old": integer_crossings(old, phase_old, signal, (110.0, 170.0), 6),
            "new": integer_crossings(new, phase_new, signal, (110.0, 170.0), 6),
        }
    fifth_stage = None
    for stage in range(1, 7):
        crossings = result[f"JTL{stage}"]["new"]["integer_crossings"]
        if any(item["integer_index"] == 5 for item in crossings):
            fifth_stage = f"JTL{stage}"
            break
    result["first_new_jtl_stage_with_fifth_integer_crossing"] = fifth_stage
    result["interpretation"] = "B02 integer crossings are downstream trajectory markers, not clean SFQ event counts"
    return result


def max_group_entry(group_data: dict[str, object]) -> dict[str, object] | None:
    entries = list(group_data.get("by_signal", {}).values())
    if not entries:
        return None
    return max(entries, key=lambda item: float(item["max_abs_difference_display"]))


def fmt(value: object, digits: int = 6) -> str:
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        if not math.isfinite(float(value)):
            return "NaN"
        return f"{float(value):.{digits}g}"
    return str(value)


def metric_signal(metrics: dict[str, object], window_name: str, group: str, signal: str) -> dict[str, object]:
    return metrics["window_comparisons"][window_name][group]["by_signal"][signal]


def write_report(metrics: dict[str, object]) -> None:
    deck = metrics["deck_diff"]
    parity = metrics["pre70_parity"]
    divergence = metrics["first_divergence"]
    recovery = metrics["recovery"]
    write1 = metrics["write1"]
    pre = metrics["pre_read1"]
    read1 = metrics["read1"]
    bj2 = metrics["bj2_trajectory"]
    retrap = metrics["retrap"]
    jtl = metrics["jtl_downstream"]
    old_net = bj2["old_110_170"]["phase_delta_turns"]
    new_net = bj2["new_110_170"]["phase_delta_turns"]
    old_area = bj2["old_110_170"]["voltage_area_turns"]
    new_area = bj2["new_110_170"]["voltage_area_turns"]
    old_cross = bj2["old_integer_crossings"]["integer_crossings"]
    new_cross = bj2["new_integer_crossings"]["integer_crossings"]
    crossing_rows: list[str] = []
    for number in range(1, 7):
        old_time = next((item["sample_time_ps"] for item in old_cross if item["integer_index"] == number), None)
        new_time = next((item["sample_time_ps"] for item in new_cross if item["integer_index"] == number), None)
        delta = None if old_time is None or new_time is None else new_time - old_time
        crossing_rows.append(f"| {number} | {fmt(old_time, 5)} | {fmt(new_time, 5)} | {fmt(delta, 5)} |")

    layer_rows: list[str] = []
    for layer, item in divergence.items():
        exact = item["first_exact"]
        robust = item["first_robust"]
        layer_rows.append(
            f"| {layer} | {fmt(exact['time_ps'] if exact else None, 5)} ({exact['signal'] if exact else '—'}) | "
            f"{fmt(robust['time_ps'] if robust else None, 5)} ({robust['signal'] if robust else '—'}) |"
        )

    recovery_rows: list[str] = []
    for target in (81.0, 85.0, 89.9, 90.0):
        checkpoint = recovery["checkpoint_group_max"][str(target)]["by_group_and_unit"]
        def best(group: str) -> str:
            values = checkpoint[group].values()
            if not values:
                return "—"
            entry = max(values, key=lambda item: float(item["abs_difference"]))
            return f"{fmt(entry['abs_difference'], 5)} {entry['unit']} ({entry['signal']})"
        recovery_rows.append(
            f"| {target:g} | {best('bvm_internal')} | {best('sl')} | {best('qb_input')} | {best('qb_internal')} | {best('jtl')} |"
        )

    write_rows: list[str] = []
    for number in range(1, 5):
        jm1 = metric_signal(metrics, "write1", "bvm_internal", f"P(B_JM1|XBVM{number})")
        jm2 = metric_signal(metrics, "write1", "bvm_internal", f"P(B_JM2|XBVM{number})")
        lm3 = metric_signal(metrics, "write1", "bvm_internal", f"I(L_M3|XBVM{number})")
        js1 = metric_signal(metrics, "write1", "bvm_internal", f"P(B_JS1|XBVM{number})")
        js2 = metric_signal(metrics, "write1", "bvm_internal", f"P(B_JS2|XBVM{number})")
        write_rows.append(
            f"| BVM{number} | {fmt(jm1['max_abs_difference_display'], 5)} | {fmt(jm2['max_abs_difference_display'], 5)} | "
            f"{fmt(lm3['max_abs_difference_display'], 5)} | {fmt(js1['max_abs_difference_display'], 5)} | {fmt(js2['max_abs_difference_display'], 5)} |"
        )

    history_rows: list[str] = []
    for number in range(1, 5):
        jm1 = metric_signal(metrics, "history_intervention", "bvm_internal", f"P(B_JM1|XBVM{number})")
        jm2 = metric_signal(metrics, "history_intervention", "bvm_internal", f"P(B_JM2|XBVM{number})")
        lm3 = metric_signal(metrics, "history_intervention", "bvm_internal", f"I(L_M3|XBVM{number})")
        history_rows.append(
            f"| BVM{number} | {fmt(jm1['max_abs_difference_display'], 5)} | {fmt(jm2['max_abs_difference_display'], 5)} | {fmt(lm3['max_abs_difference_display'], 5)} |"
        )

    state_rows: list[str] = []
    state = pre["state_vectors"]
    for number in range(1, 5):
        delta = state[f"BVM{number}"]["new_minus_old"]
        state_rows.append(
            f"| BVM{number} | {fmt(delta['JM1_phase_turns'], 6)} | {fmt(delta['JM2_phase_turns'], 6)} | "
            f"{fmt(delta['LM1_current_uA'], 6)} | {fmt(delta['LM2_current_uA'], 6)} | {fmt(delta['LM3_current_uA'], 6)} | {fmt(delta['LPM_current_uA'], 6)} |"
        )

    network_delta = pre["network_state"]["new_minus_old"]
    reference = pre["reference_comparison_bvm1"]
    reference_rows = []
    for name in ("JM1_phase_turns", "JM2_phase_turns", "LM1_current_uA", "LM2_current_uA", "LM3_current_uA", "LPM_current_uA"):
        item = reference[name]
        reference_rows.append(
            f"| {name} | {fmt(item['old'], 7)} | {fmt(item['new'], 7)} | {fmt(item['isolated_s1_reference'], 7)} | {fmt(state['BVM1']['new_minus_old'][name], 7)} |"
        )
    read1_qbin = read1["qbin_lin_stats"]
    qbin_diff = read1_qbin["V(QBIN)"]
    lin_diff = read1_qbin["I(LIN|XBQ1)"]
    phase_difference = bj2["new_minus_old_phase_difference_turns"]
    trajectory_cp = bj2["trajectory_checkpoint_difference"]
    html_links = "\n".join(
        f"- [{name}.html](../plots/{name}.html)"
        for name in metrics["plot_manifest_names"]
    )
    report = f"""# OLD-1111 vs NEW-1111 HISTORY-DIFFERENCE CAUSAL AUDIT

本报告是只读分析，不是新的物理实验，也不判断 4 圈或 5 圈哪一个“正确”。所有差分约定为 **NEW − OLD**。

## 1. Question

本轮只追踪 `4 → 5` 的历史因果链：

1. 70 ps 前两套轨迹是否逐点一致；
2. 110 ps 的 READ1 开始前是否仍有可观测状态差异；
3. NEW 的第五个整数相位 crossing 是前四个几乎不变、尾部再多一圈，还是 READ1 一开始就已经进入了不同的 QB 轨迹。

## 2. Data authority and no-new-simulation boundary

- OLD deck/raw：`{metrics['inputs']['old']['deck']}` / `{metrics['inputs']['old']['raw']}`
- NEW deck/raw：`{metrics['inputs']['new']['deck']}` / `{metrics['inputs']['new']['raw']}`
- 两套 fixture 都是 `HISTORICAL_BVMSIM_JM2_CONNECTED_VARIANT`；本轮没有以 canonical BVM 替代它们。
- 只消费 OLD ∩ NEW 的共同探针；没有 zero-fill、替代 NEW-only branch probe 或插值。
- `simulation_invoked = {str(metrics['simulation_invoked']).lower()}`；旧/新 raw 在分析前后 SHA256 均未改变。

## 3. Deck/protocol difference audit

机械 diff 的结论：`fixed_core_equal_after_excluding_controls_prints_comments = {str(deck['fixed_core_equal_after_excluding_controls_prints_comments']).lower()}`，未分类的非注释/非 `.print`/非控制源差异数量为 `{len(deck['unexpected_nonclassified_differences'])}`。

真正的 protocol 差异是 70–81 ps：

- OLD：四个 BVM 都有 `WL=+100 µA` 和 `SE=+100 µA` 的 71–80 ps 平台；
- NEW：70–90 ps 为 no-op；
- 两套在 WRITE1（95 ps 代表点）和最终 READ1（115 ps 代表点）的源语义相同。

NEW 另外追加了直接 branch `.print` 探针；这是可观测性变化，不是物理方程变化。完整逐行分类见 [`deck_diff_summary.json`](deck_diff_summary.json)。

## 4. 45–70 ps parity

OLD 有 158 个表头（含 `time`），NEW 有 230 个；共同的非时间探针为 **{metrics['time_grid']['common_probe_count']}** 个。两套时间 token 和浮点 time tuple 都完全一致：{metrics['time_grid']['exact_time_tokens_and_values']}，窗口实际覆盖 `{fmt(parity['window_ps'][0], 5)}–{fmt(parity['window_ps'][1], 5)} ps`。

在所有共同探针、全部 `{parity['sample_count']}` 个 baseline 样本上，逐点差分都为 0：

- 最大绝对差：`{fmt(parity['all_common_max_abs_difference_native'], 8)}`（native）；
- RMS：`{fmt(parity['all_common_rms_difference_native'], 8)}`（native）；
- 非零差分样本：`{parity['nonzero_difference_count']}`。

因此可以把 70 ps 作为本次 history intervention 的 causal anchor：在现有可观测共同探针上，70 ps 前没有先行差异。70.0 ps 存储点也仍相等；第一批 exact unequal samples 出现在 70.1 ps。

## 5. First divergence and 70–81 ps history intervention

下表的 robust 时间只是 task-local 描述性诊断：相对各信号自身后段幅度的 `1e-6`，并要求 3 个连续 exact-grid 样本；它不是物理 Gate。

| layer | first exact unequal (ps) | first descriptive robust (ps) |
|---|---:|---:|
{chr(10).join(layer_rows)}

观察到的层级顺序是：70.1 ps 控制源差异、BVM 内部/SL/QBIN/QB 差异已经出现；JTL 在 70.1 ps 已有数值不等式，但达到描述性 robust 尺度要晚一些（不同 JTL observable 约 70.2–70.6 ps）。这只是观察到的时间顺序，不能单凭时间顺序把网络响应证明成唯一因果。

70–81 ps 的动态扰动以关键 common probes 表示如下（完整逐探针统计在 `history_intervention`）：

| signal | max |NEW−OLD| | RMS | peak time |
|---|---:|---:|---:|
| `P(B_JM1|XBVM1)` | {fmt(metric_signal(metrics, 'history_intervention', 'bvm_internal', 'P(B_JM1|XBVM1)')['max_abs_difference_display'], 6)} turns | {fmt(metric_signal(metrics, 'history_intervention', 'bvm_internal', 'P(B_JM1|XBVM1)')['rms_difference_display'], 6)} turns | {fmt(metric_signal(metrics, 'history_intervention', 'bvm_internal', 'P(B_JM1|XBVM1)')['peak_abs_difference_time_ps'], 6)} ps |
| `P(B_JM2|XBVM1)` | {fmt(metric_signal(metrics, 'history_intervention', 'bvm_internal', 'P(B_JM2|XBVM1)')['max_abs_difference_display'], 6)} turns | {fmt(metric_signal(metrics, 'history_intervention', 'bvm_internal', 'P(B_JM2|XBVM1)')['rms_difference_display'], 6)} turns | {fmt(metric_signal(metrics, 'history_intervention', 'bvm_internal', 'P(B_JM2|XBVM1)')['peak_abs_difference_time_ps'], 6)} ps |
| `I(L_M3|XBVM1)` | {fmt(metric_signal(metrics, 'history_intervention', 'bvm_internal', 'I(L_M3|XBVM1)')['max_abs_difference_display'], 6)} µA | {fmt(metric_signal(metrics, 'history_intervention', 'bvm_internal', 'I(L_M3|XBVM1)')['rms_difference_display'], 6)} µA | {fmt(metric_signal(metrics, 'history_intervention', 'bvm_internal', 'I(L_M3|XBVM1)')['peak_abs_difference_time_ps'], 6)} ps |
| `V(SL1)` | {fmt(metric_signal(metrics, 'history_intervention', 'sl', 'V(SL1)')['max_abs_difference_display'], 6)} mV | {fmt(metric_signal(metrics, 'history_intervention', 'sl', 'V(SL1)')['rms_difference_display'], 6)} mV | {fmt(metric_signal(metrics, 'history_intervention', 'sl', 'V(SL1)')['peak_abs_difference_time_ps'], 6)} ps |
| `V(QBIN)` | {fmt(metric_signal(metrics, 'history_intervention', 'qb_input', 'V(QBIN)')['max_abs_difference_display'], 6)} mV | {fmt(metric_signal(metrics, 'history_intervention', 'qb_input', 'V(QBIN)')['rms_difference_display'], 6)} mV | {fmt(metric_signal(metrics, 'history_intervention', 'qb_input', 'V(QBIN)')['peak_abs_difference_time_ps'], 6)} ps |
| `I(LIN|XBQ1)` | {fmt(metric_signal(metrics, 'history_intervention', 'qb_input', 'I(LIN|XBQ1)')['max_abs_difference_display'], 6)} µA | {fmt(metric_signal(metrics, 'history_intervention', 'qb_input', 'I(LIN|XBQ1)')['rms_difference_display'], 6)} µA | {fmt(metric_signal(metrics, 'history_intervention', 'qb_input', 'I(LIN|XBQ1)')['peak_abs_difference_time_ps'], 6)} ps |

四颗 BVM 的主要内部响应（同一 70–81 ps 窗口）为：

| BVM | JM1 phase max diff (turns) | JM2 phase max diff (turns) | LM3 max diff (µA) |
|---|---:|---:|---:|
{chr(10).join(history_rows)}

## 6. 81–90 ps recovery

| checkpoint | BVM internal max (unit/signals) | SL max | QB input max | QB internal max | JTL max |
|---:|---|---|---|---|---|
{chr(10).join(recovery_rows)}

这些数值说明 READ0 的影响没有在 81 ps 立刻变成共同轨迹；在 WRITE1 开始的 90 ps，仍可从共同探针中看到 residual difference。这里没有对差异强行拟合单指数。

## 7. WRITE1 trajectory from different histories

两套在 90–101 ps 施加相同的 WRITE1 输入，但内部状态不同。下表是每颗 BVM 在该窗口的最大轨迹差；phase 已按连续 unwrap 后除以 `2π`，current 为 µA。

| BVM | JM1 phase max diff (turns) | JM2 phase max diff (turns) | LM3 max diff (µA) | JS1 phase max diff (turns) | JS2 phase max diff (turns) |
|---|---:|---:|---:|---:|---:|
{chr(10).join(write_rows)}

因此“相同 WRITE1 输入”并没有把两套 waveform 重新合并成逐点相同的 trajectory。这个结果支持 history-dependent initial condition / network-state sensitivity，但不是单独证明唯一机制。

## 8. PRE_READ1：110 ps 前的四颗 BVM state

`101–110 ps` 是半开区间，最后存储点为 109.9 ps。下表是该点 `NEW−OLD` 的 BVM 状态差；phase 为 turns，current 为 µA。

| BVM | ΔJM1 phase | ΔJM2 phase | ΔLM1 | ΔLM2 | ΔLM3 | ΔLPM |
|---|---:|---:|---:|---:|---:|---:|
{chr(10).join(state_rows)}

在 109.9 ps，网络/QB 共同探针的差异为：`V(SL1)={fmt(network_delta['SL1_voltage_mV'], 6)} mV`，`V(SL2)={fmt(network_delta['SL2_voltage_mV'], 6)} mV`，`V(SL3)={fmt(network_delta['SL3_voltage_mV'], 6)} mV`，`V(SL4)={fmt(network_delta['SL4_voltage_mV'], 6)} mV`，`P(BVMOUT)={fmt(network_delta['BVMOUT_phase_turns'], 6)} turns`，`V(QBIN)={fmt(network_delta['QBIN_voltage_mV'], 6)} mV`，`I(LIN)={fmt(network_delta['LIN_current_uA'], 6)} µA`，`P(BJ2)={fmt(network_delta['BJ2_phase_turns'], 6)} turns`。

这直接回答问题②：在现有可观测量上，READ1 开始前两套系统仍没有重新收敛到同一状态。辅助的 isolated single-BVM S1 reference 仅用于量级/状态参照；它的 READ 时序与本 4-BVM old/new 不相同，因此不被当作 universal stored-1 threshold，也不把相似数值升级成逻辑状态证明。

作为辅助参照，BVM1 在 109.9 ps 的部分状态与 isolated S1 的同一采样点如下；S1 不是同 protocol 对照：

| quantity | OLD | NEW | isolated S1 | NEW−OLD |
|---|---:|---:|---:|---:|
{chr(10).join(reference_rows)}

## 9. READ1 input comparison

110–121 ps 的 WL/BL/SE common control raw waveform 逐点完全相同：`all_common_controls_exactly_equal = {str(read1['control_parity']['all_common_controls_exactly_equal']).lower()}`。

但 QB 输入在 READ1 的起点已经不是同一 waveform：

- `V(QBIN)` 在 110–121 ps 的最大差为 `{fmt(qbin_diff['max_abs_difference_display'], 6)} mV`，RMS 为 `{fmt(qbin_diff['rms_difference_display'], 6)} mV`，峰值差出现在 `{fmt(qbin_diff['peak_abs_difference_time_ps'], 6)} ps`；
- `I(LIN|XBQ1)` 最大差为 `{fmt(lin_diff['max_abs_difference_display'], 6)} µA`，RMS 为 `{fmt(lin_diff['rms_difference_display'], 6)} µA`，峰值差出现在 `{fmt(lin_diff['peak_abs_difference_time_ps'], 6)} ps`；
- 两个 QB input signal 在 110.0 ps 的 `first exact unequal` 已经成立，而不是等到第五圈尾部才第一次分叉。

## 10. BJ2：四圈与五圈的 trajectory

同一 JJ、同一 `P(BJ2|XBQ1)` 和 `V(BJ2|XBQ1)`，窗口为 `[110,170) ps`：

| quantity | OLD | NEW |
|---|---:|---:|
| phase endpoint delta | {fmt(old_net, 10)} turns | {fmt(new_net, 10)} turns |
| same-JJ voltage area / Φ0 | {fmt(old_area, 10)} turns | {fmt(new_area, 10)} turns |
| phase-area residual | {fmt(bj2['old_110_170']['phase_area_residual_turns'], 8)} turns | {fmt(bj2['new_110_170']['phase_area_residual_turns'], 8)} turns |
| integer crossings observed | {len(old_cross)} | {len(new_cross)} |

相位差轨迹 `Δφ = unwrap(NEW) − unwrap(OLD)` 在 110 ps 为 `{fmt(phase_difference['start_110ps'], 8)} turns`，到 115 ps 为 `{fmt(trajectory_cp['115.0']['new_minus_old_turns'], 8)} turns`，到 120 ps 为 `{fmt(trajectory_cp['120.0']['new_minus_old_turns'], 8)} turns`，到 138.8 ps 为 `{fmt(trajectory_cp['138.8']['new_minus_old_turns'], 8)} turns`，到 169.9 ps 为 `{fmt(phase_difference['end_169_9ps'], 8)} turns`。这不是简单的一个末端孤立尖峰。

## 11. Extra-turn localization and pattern

以下 crossing 是连续相位轨迹的整数 crossing marker，**不是 clean SFQ event count**，也没有用 whole-window phase displacement 代替严格事件判定。

| crossing index | OLD sample time (ps) | NEW sample time (ps) | NEW−OLD timing (ps) |
|---:|---:|---:|---:|
{chr(10).join(crossing_rows)}

第一至第三个 crossing 的时间仍较接近，但第四个 crossing 已从 OLD 的 `{fmt(next(item['sample_time_ps'] for item in old_cross if item['integer_index'] == 4), 6)} ps` 移到 NEW 的 `{fmt(next(item['sample_time_ps'] for item in new_cross if item['integer_index'] == 4), 6)} ps`；NEW 的第五个 crossing 为 `{fmt(next(item['sample_time_ps'] for item in new_cross if item['integer_index'] == 5), 6)} ps`，此时 OLD 已接近四圈后的 quiescent-like tail。因此最准确的描述是：

**不是“前四圈基本相同、只在尾部追加第五圈”。** 更符合现有 raw 的是 **READ1 一开始就存在小的状态/输入差异，随后整个 QB trajectory 逐步分叉，并在后段表现为 NEW 多出第五个 crossing**。也就是说，结果同时包含“late extra turn”这个表象，但因果形状更接近 `WHOLE_TRAJECTORY_CHANGE_WITH_LATE_EXTRA_TURN`。

这仍然不是 4/5 个 clean SFQ 的结论；需要独立的同 JJ segment/retrap 事件证据才能谈严格事件数。

## 12. Retrapping / tail

本报告只使用一个透明的描述性指示器：最后一个整数 crossing 之后，`|V(BJ2)| ≤ 0.05 mV` 持续 3 个 exact-grid 样本。它不是 global retrap metric。

| run | last integer crossing | quiescent-like voltage return | tail phase delta 160–170 ps |
|---|---:|---:|---:|
| OLD | {fmt(retrap['OLD']['last_integer_crossing']['sample_time_ps'], 6)} ps | {fmt(retrap['OLD']['quiescent_like_return']['sample_time_ps'], 6)} ps | {fmt(retrap['OLD']['tail_160_170ps']['phase_delta_turns'], 8)} turns |
| NEW | {fmt(retrap['NEW']['last_integer_crossing']['sample_time_ps'], 6)} ps | {fmt(retrap['NEW']['quiescent_like_return']['sample_time_ps'], 6)} ps | {fmt(retrap['NEW']['tail_160_170ps']['phase_delta_turns'], 8)} turns |

NEW 的 quiescent-like voltage return 比 OLD 晚约 `{fmt(retrap['NEW']['quiescent_like_return']['sample_time_ps'] - retrap['OLD']['quiescent_like_return']['sample_time_ps'], 6)} ps`，这与 NEW 在后段仍继续运行并获得第五个 crossing 的观察相符。

## 13. Downstream JTL

| stage | OLD B02 crossing count | NEW B02 crossing count | NEW fifth crossing |
|---|---:|---:|---:|
{chr(10).join(
    f"| {stage} | {len(jtl[stage]['old']['integer_crossings'])} | {len(jtl[stage]['new']['integer_crossings'])} | "
    f"{fmt(next((item['sample_time_ps'] for item in jtl[stage]['new']['integer_crossings'] if item['integer_index'] == 5), None), 6)} ps |"
    for stage in [f"JTL{index}" for index in range(1, 7)]
)}

在现有 common JTL phase probes 中，第五个 integer crossing 已经在 QB `BJ2` 出现，并随后在 `JTL1` 的 B02 可见；六级 JTL 继续保留它。因此当前证据更支持“QB 已先产生不同的源 trajectory，JTL 传递该差异”，不支持“第五个响应只由后级 JTL 新产生”。这仍是 trajectory-marker 证据，不是 clean SFQ transport Gate。

## 14. Compact causal timeline

| time | observed state |
|---:|---|
| 45–70 ps | 所有 157 个共同探针逐点相等。 |
| 70.0 ps | OLD/NEW 仍相等；history intervention 的边界。 |
| 70.1 ps | OLD 的 all-BVM positive READ 与 NEW no-op 造成控制差异；BVM/SL/QBIN/QB 共同探针同步出现 exact difference。 |
| 约 70.2–70.6 ps | JTL observable 由数值微差进入描述性 robust 差异，具体时间依 observable 而变。 |
| 81–90 ps | READ0 结束后差异衰减但未消失。 |
| 90–101 ps | 相同 WRITE1 从不同 history state 出发，BVM 内部 trajectory 仍不同。 |
| 109.9 ps | final READ1 前，四颗 BVM、SL、BVMout、QBIN/LIN、BJ2 均仍有可观测 residual difference。 |
| 110.0 ps | READ1 控制相同，但 QB input 已不是同一 waveform。 |
| 118.1 / 118.3 ps | NEW / OLD first BJ2 integer crossing。 |
| 129.5 ps | NEW fourth BJ2 crossing；OLD 尚未到第四个 crossing。 |
| 138.8 ps | OLD fourth BJ2 crossing。 |
| 141.4 ps | NEW fifth BJ2 crossing；OLD 已接近四圈 tail。 |
| {fmt(retrap['OLD']['quiescent_like_return']['sample_time_ps'], 6)} / {fmt(retrap['NEW']['quiescent_like_return']['sample_time_ps'], 6)} ps | OLD / NEW 的描述性 quiescent-like voltage return。 |

## 15. OBSERVED

- 70 ps 前，在当前共同探针上逐点一致；没有发现 pre-intervention hidden difference 的证据。
- 70–81 ps 的 READ0 protocol 差异确实先改变了 BVM/SL/QB 可观测轨迹，并且差异持续到 109.9 ps。
- 110 ps 的 READ1 控制相同，但 QB input 和 BJ2 trajectory 从起点已有差异。
- NEW 的第四个 crossing 明显提前，第五个 crossing 发生在 OLD 已接近 retrap-like tail 之后。
- JTL1–JTL6 的 B02 trajectory 都保留 NEW 的第五个 integer crossing；未观察到后级 JTL 首次创造第五圈。

## 16. INFERENCE

- 70–81 ps 的 history 是 `4→5` 改变的强候选前置条件；因为该 protocol 差异在 70 ps 前后具有清晰时间锚点，并在 PRE_READ1 仍可见。
- 轨迹形状不是“完全相同的前四圈 + 独立尾部第五圈”。更合理的 task-local 描述是：不同 history 造成 preconditioning，READ1 从一开始就进入略有不同的 QB 动力学轨迹，差异在后段积累为额外 crossing。
- 现有证据支持“QB 先分叉、JTL 后传递”，但不把时间先后单独当作唯一因果证明。

## 17. UNKNOWN / OBSERVABILITY GAP

- 这不是 one-variable causal A/B：OLD/NEW 的整份 deck 生成上下文和 `.print` 集合并非完全相同，虽然机械审计已将可见差异分类为 READ0 protocol 与 observability-only changes。
- 不能仅凭本轮共同 probe 断言未观测的 hidden state 没有差异；只能说当前可观测 state 已不同。
- 不能由整数 phase crossings 或 whole-window 4/5 turns 推导 clean SFQ event count、retrap event identity、收敛性或哪一结果物理正确。
- 不能据此证明 canonical BVM、single-BVM、过程裕度、T1、论文机制或唯一工作机理。

## 18. Minimal future causal experiment (PROPOSED_NOT_AUTHORIZED)

如果用户审阅后仍需做真正的因果 A/B，最小方案是在同一 NEW all-one 1111 fixture 中只切换 70–81 ps：`READ0-present` vs `READ0-absent`，其余 deck、source、probe、timestep、stop time 全部相同。该方案本轮 **未生成、未运行、未授权**。

## 19. Human gate

`state: AWAITING_USER_REVIEW`

`analysis_completed: true`

`user_reviewed: false`

`next_physical_experiment_authorized: false`

`automatic_next_experiment: false`

`next_action: STOP`

## Plots

{html_links}
"""
    (EXP / "analysis" / "OLD_VS_NEW_1111_HISTORY_CAUSAL_AUDIT.md").write_text(report, encoding="utf-8")


def main() -> int:
    raw_hash_before = {"old": sha256(OLD_RAW), "new": sha256(NEW_RAW), "s1": sha256(S1_RAW)}
    if raw_hash_before["old"] != OLD_RAW_SHA256 or raw_hash_before["new"] != NEW_RAW_SHA256:
        raise RuntimeError("authoritative OLD/NEW raw hash does not match recorded input")

    old = read_csv(OLD_RAW)
    new = read_csv(NEW_RAW)
    old_header, old_time_tokens = csv_time_tokens(OLD_RAW)
    new_header, new_time_tokens = csv_time_tokens(NEW_RAW)
    if old.time != new.time or old_time_tokens != new_time_tokens:
        raise RuntimeError("OLD/NEW time grids are not exactly identical; this audit refuses interpolation")
    if old.duplicate_columns or new.duplicate_columns:
        raise RuntimeError("duplicate raw headers require explicit occurrence handling; unexpected in this fixture")
    common = set(old.headers).intersection(new.headers)
    common.discard("time")
    selected_groups, missing_groups = available_groups(common)
    phase_old: dict[str, tuple[float, ...]] = {}
    phase_new: dict[str, tuple[float, ...]] = {}
    for signal in common:
        if signal.startswith("P"):
            phase_old[signal] = continuous_unwrap(old.column(signal))
            phase_new[signal] = continuous_unwrap(new.column(signal))

    deck = deck_diff_summary()
    pre_indices = time_indices(old, WINDOWS_PS["baseline_common"])
    pre_differences: list[float] = []
    for signal in common:
        old_series = series_for(old, signal, phase_old)
        new_series = series_for(new, signal, phase_new)
        pre_differences.extend(
            float(new_series[index]) - float(old_series[index]) for index in pre_indices
        )
    pre70 = {
        "window_ps": list(WINDOWS_PS["baseline_common"]),
        "sample_count": len(pre_indices),
        "common_probe_count": len(common),
        "all_common_max_abs_difference_native": max(abs(value) for value in pre_differences),
        "all_common_rms_difference_native": math.sqrt(sum(value * value for value in pre_differences) / len(pre_differences)),
        "nonzero_difference_count": sum(value != 0.0 for value in pre_differences),
        "exact_zero_by_group": {
            group: all(
                difference_stats(old, new, signal, WINDOWS_PS["baseline_common"], phase_old, phase_new)["max_abs_difference_native"] == 0.0
                for signal in labels
            )
            for group, labels in selected_groups.items()
        },
    }
    first_divergence = layer_divergence(old, new, LAYER_GROUPS, phase_old, phase_new)
    history_comparisons = group_window_comparisons(
        old, new, selected_groups, WINDOWS_PS["history_intervention"], phase_old, phase_new
    )
    recovery_labels = OrderedDict(
        (
            ("bvm_internal", selected_groups["bvm_internal"]),
            ("sl", selected_groups["sl"]),
            ("qb_input", selected_groups["qb_input"]),
            ("qb_internal", selected_groups["qb_internal"]),
            ("jtl", selected_groups["jtl"]),
        )
    )
    recovery = {
        "window_ps": list(WINDOWS_PS["post_history_recovery"]),
        "checkpoint_group_max": checkpoint_group_max(
            old,
            new,
            recovery_labels,
            (81.0, 85.0, 89.9, 90.0),
            phase_old,
            phase_new,
        ),
        "key_signal_stats": key_signal_stats(
            old,
            new,
            [
                f"P(B_JM{jj}|XBVM{number})"
                for number in range(1, 5)
                for jj in (1, 2)
            ]
            + [
                f"I(L_M{jj}|XBVM{number})"
                for number in range(1, 5)
                for jj in (1, 2, 3)
            ]
            + ["V(QBIN)", "I(LIN|XBQ1)", "P(BJ1|XBQ1)", "P(BJ2|XBQ1)", "I(BJ2|XBQ1)"],
            WINDOWS_PS["post_history_recovery"],
            phase_old,
            phase_new,
        ),
    }
    write1 = {
        "window_ps": list(WINDOWS_PS["write1"]),
        "by_signal": key_signal_stats(
            old,
            new,
            tuple(
                label
                for number in range(1, 5)
                for label in _bvm_labels(number)
                if label in BVM_INTERNAL
            ),
            WINDOWS_PS["write1"],
            phase_old,
            phase_new,
            include_waveforms=True,
        ),
        "same_write1_input_source_semantics": bool(deck["physics_protocol_differences"]["write1_semantics_equal_at_95ps"]),
    }
    pre_read1_labels = OrderedDict(
        (
            ("bvm_internal", selected_groups["bvm_internal"]),
            ("sl", selected_groups["sl"]),
            ("bvmout", selected_groups["bvmout"]),
            ("qb_input", selected_groups["qb_input"]),
            ("qb_internal", selected_groups["qb_internal"]),
        )
    )
    pre_state_vectors: dict[str, object] = {}
    for number in range(1, 5):
        pre_state_vectors[f"BVM{number}"] = state_vector_pair(old, new, phase_old, phase_new, 109.9, number)
    pre_network = network_state_pair(old, new, phase_old, phase_new, 109.9)
    s1 = read_csv(S1_RAW)
    if s1.duplicate_columns:
        raise RuntimeError("isolated S1 reference unexpectedly contains duplicate headers")
    phase_s1: dict[str, tuple[float, ...]] = {
        signal: continuous_unwrap(s1.column(signal))
        for signal in s1.headers
        if signal.startswith("P")
    }
    s1_index, s1_actual = exact_index(s1, 109.9)
    s1_state = state_vector(s1, phase_s1, s1_index, 1)
    reference_comparison: dict[str, object] = {}
    for name in pre_state_vectors["BVM1"]["old"]:
        old_value = pre_state_vectors["BVM1"]["old"][name]
        new_value = pre_state_vectors["BVM1"]["new"][name]
        reference_comparison[name] = {
            "old": old_value,
            "new": new_value,
            "isolated_s1_reference": s1_state.get(name),
            "old_minus_s1": None if s1_state.get(name) is None else old_value - s1_state[name],
            "new_minus_s1": None if s1_state.get(name) is None else new_value - s1_state[name],
        }
    pre_read1 = {
        "window_ps": list(WINDOWS_PS["pre_read1"]),
        "last_pre_read1_sample_ps": 109.9,
        "by_group": group_window_comparisons(
            old, new, pre_read1_labels, WINDOWS_PS["pre_read1"], phase_old, phase_new
        ),
        "state_vectors": pre_state_vectors,
        "network_state": pre_network,
        "isolated_s1_reference": {
            "raw_sha256": raw_hash_before["s1"],
            "sample_ps": s1_actual,
            "state_vector_bvm1": s1_state,
            "role": "auxiliary_only_different_protocol_not_universal_threshold",
        },
        "reference_comparison_bvm1": reference_comparison,
    }
    read1_labels = OrderedDict(
        (
            ("sl", selected_groups["sl"]),
            ("bvmout", selected_groups["bvmout"]),
            ("qb_input", selected_groups["qb_input"]),
            ("qb_internal", selected_groups["qb_internal"]),
        )
    )
    read1 = {
        "window_ps": list(WINDOWS_PS["read1"]),
        "control_parity": read1_control_parity(old, new, phase_old, phase_new),
        "input_and_qb_comparisons": group_window_comparisons(
            old, new, read1_labels, WINDOWS_PS["read1"], phase_old, phase_new
        ),
        "qbin_lin_stats": key_signal_stats(
            old, new, ["V(QBIN)", "I(LIN|XBQ1)"], WINDOWS_PS["read1"], phase_old, phase_new
        ),
        "first_exact_from_read1_start": {
            signal: first_unequal(old, new, signal, 110.0, phase_old, phase_new)
            for signal in ("V(QBIN)", "I(LIN|XBQ1)", "P(BJ2|XBQ1)")
        },
        "first_descriptive_robust_from_read1_start": {
            signal: first_robust(old, new, signal, 110.0, phase_old, phase_new)
            for signal in ("V(QBIN)", "I(LIN|XBQ1)", "P(BJ2|XBQ1)")
        },
        "checkpoint_values": checkpoint_diff(
            old,
            new,
            ["V(QBIN)", "I(LIN|XBQ1)", "P(BJ2|XBQ1)", "V(BJ2|XBQ1)", "I(BJ2|XBQ1)"],
            (110.0, 111.0, 112.0, 114.0, 115.0, 120.0, 120.9),
            phase_old,
            phase_new,
        ),
    }
    bj2 = phase_trajectory_metrics(old, new, phase_old, phase_new)
    retrap = {
        "OLD": retrap_indicator(old, phase_old),
        "NEW": retrap_indicator(new, phase_new),
    }
    jtl = jtl_stage_crossings(old, new, phase_old, phase_new)
    common_probe_key_labels = list(common)
    manifest = write_plot_inputs(old, new, phase_old, phase_new, common)
    raw_hash_after = {"old": sha256(OLD_RAW), "new": sha256(NEW_RAW), "s1": sha256(S1_RAW)}
    if raw_hash_after != raw_hash_before:
        raise RuntimeError("raw hash changed during read-only analysis")
    metrics: dict[str, object] = {
        "schema": "history-audit-metrics-v1",
        "task": "OLD-1111 vs NEW-1111 HISTORY-DIFFERENCE CAUSAL AUDIT",
        "mode": "ANALYSIS_ONLY_NO_NEW_SIMULATION",
        "head_before_task": HEAD_BEFORE_TASK,
        "head_at_analysis": git_value("rev-parse", "HEAD"),
        "simulation_invoked": False,
        "difference_convention": "NEW_minus_OLD",
        "inputs": {
            "old": {"deck": str(OLD_DECK.relative_to(REPO)), "raw": str(OLD_RAW.relative_to(REPO)), "deck_sha256": sha256(OLD_DECK), "raw_sha256": raw_hash_before["old"]},
            "new": {"deck": str(NEW_DECK.relative_to(REPO)), "raw": str(NEW_RAW.relative_to(REPO)), "deck_sha256": sha256(NEW_DECK), "raw_sha256": raw_hash_before["new"]},
            "isolated_s1_reference": {"raw": str(S1_RAW.relative_to(REPO)), "raw_sha256": raw_hash_before["s1"]},
        },
        "raw_hashes_before": raw_hash_before,
        "raw_hashes_after": raw_hash_after,
        "raw_unchanged": raw_hash_after == raw_hash_before,
        "time_grid": {
            "old_sample_count": old.sample_count,
            "new_sample_count": new.sample_count,
            "old_header_count_including_time": len(old_header),
            "new_header_count_including_time": len(new_header),
            "common_probe_count": len(common),
            "old_only_probe_count": len(set(old_header) - set(new_header)),
            "new_only_probe_count": len(set(new_header) - set(old_header)),
            "exact_time_tokens_and_values": old_time_tokens == new_time_tokens and old.time == new.time,
            "time_start_ps": ps(old.time[0]),
            "time_end_ps": ps(old.time[-1]),
            "dt_ps": ps(old.time[1] - old.time[0]),
            "interpolation_used": False,
        },
        "common_probe_order_old": common_probe_key_labels,
        "missing_expected_group_probes": missing_groups,
        "deck_diff": deck,
        "pre70_parity": pre70,
        "first_divergence": first_divergence,
        "window_comparisons": {
            "history_intervention": history_comparisons,
            "post_history_recovery": recovery["key_signal_stats"],
            "write1": {"bvm_internal": {"by_signal": write1["by_signal"]}},
            "pre_read1": pre_read1["by_group"],
            "read1": read1["input_and_qb_comparisons"],
        },
        "recovery": recovery,
        "write1": write1,
        "pre_read1": pre_read1,
        "read1": read1,
        "bj2_trajectory": bj2,
        "retrap": retrap,
        "jtl_downstream": jtl,
        "plot_manifest_names": [item["name"] for item in manifest],
        "analysis_boundary": {
            "phase_crossings_are_trajectory_markers_not_sfq_counts": True,
            "no_convergence_claim": True,
            "no_4_or_5_correctness_claim": True,
            "canonical_bvm_not_tested": True,
            "future_causal_ab": "PROPOSED_NOT_AUTHORIZED",
        },
        "human_gate": {
            "state": "AWAITING_USER_REVIEW",
            "analysis_completed": True,
            "user_reviewed": False,
            "next_physical_experiment_authorized": False,
            "automatic_next_experiment": False,
            "next_action": "STOP",
        },
    }
    metrics["analysis_tools"] = {
        "script": str(Path(__file__).relative_to(REPO)),
        "script_sha256": sha256(Path(__file__)),
        "independent_check.py_sha256": sha256(EXP / "analysis/independent_check.py")
        if (EXP / "analysis/independent_check.py").is_file()
        else None,
        "render_plots.py_sha256": sha256(EXP / "analysis/render_plots.py")
        if (EXP / "analysis/render_plots.py").is_file()
        else None,
        "scripts/josim-plot2.py_sha256": sha256(REPO / "scripts/josim-plot2.py"),
        "scripts/bvmtools/raw.py_sha256": sha256(REPO / "scripts/bvmtools/raw.py"),
        "scripts/bvmtools/phase.py_sha256": sha256(REPO / "scripts/bvmtools/phase.py"),
        "scripts/bvmtools/waveform.py_sha256": sha256(REPO / "scripts/bvmtools/waveform.py"),
        "scripts/bvmtools/metrics.py_sha256": sha256(REPO / "scripts/bvmtools/metrics.py"),
    }
    (EXP / "analysis" / "history_audit_metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (EXP / "analysis" / "deck_diff_summary.json").write_text(
        json.dumps(deck, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (EXP / "analysis" / "plot_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    provenance = {
        "schema": "history-audit-provenance-v1",
        "head_before_task": HEAD_BEFORE_TASK,
        "head_at_analysis": metrics["head_at_analysis"],
        "simulation_invoked": False,
        "raw_unchanged": True,
        "raw_hashes_before": raw_hash_before,
        "raw_hashes_after": raw_hash_after,
        "input_deck_hashes": {"old": sha256(OLD_DECK), "new": sha256(NEW_DECK)},
        "analysis_script_sha256": sha256(Path(__file__)),
        "independent_check_sha256": sha256(EXP / "analysis/independent_check.py")
        if (EXP / "analysis/independent_check.py").is_file()
        else None,
        "render_script_sha256": sha256(EXP / "analysis/render_plots.py")
        if (EXP / "analysis/render_plots.py").is_file()
        else None,
        "plotter_sha256": sha256(REPO / "scripts/josim-plot2.py"),
        "solver": {
            "path": "build/josim-cli",
            "sha256": "48655cb31d6297ba571a3003c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2",
            "version": "v2.7.2837d13 compiled May 30 2026 at 20:37:57 (copied from run metadata; not invoked this task)",
        },
        "time_grid": metrics["time_grid"],
        "comparison": {"common_probe_only": True, "interpolation": False, "difference": "NEW_minus_OLD"},
    }
    (EXP / "analysis" / "provenance.json").write_text(
        json.dumps(provenance, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    write_report(metrics)
    print(f"analysis complete: common_probes={len(common)} old_new_samples={old.sample_count}")
    print(f"raw_unchanged={raw_hash_after == raw_hash_before} simulation_invoked=false")
    print(f"metrics={EXP / 'analysis/history_audit_metrics.json'}")
    print(f"report={EXP / 'analysis/OLD_VS_NEW_1111_HISTORY_CAUSAL_AUDIT.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
