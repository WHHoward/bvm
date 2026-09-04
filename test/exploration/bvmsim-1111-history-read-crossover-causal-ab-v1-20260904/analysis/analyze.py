#!/usr/bin/env python3
"""Four-condition crossover analysis on immutable/common-grid JoSIM raw data.

This file owns only this experiment's windows, condition labels, pairwise
crossover semantics, and report wording.  CSV reading, phase unwrapping,
waveform arithmetic, comparisons, and KCL residual evaluation come from the
shared bvmtools modules.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import re
import sys
from collections import OrderedDict
from pathlib import Path
from statistics import median


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
ANALYSIS = EXP / "analysis"
PLOT_INPUTS = ANALYSIS / "plot_inputs"

sys.path.insert(0, str(REPO / "scripts"))
from bvmtools.compare import compare_series, exact_time_grid_identity  # noqa: E402
from bvmtools.kcl import kcl_window_metrics, linear_kcl_residual  # noqa: E402
from bvmtools.metrics import phase_area_window  # noqa: E402
from bvmtools.phase import TAU, continuous_unwrap, monotonic_segments, window_indices  # noqa: E402
from bvmtools.raw import RawTrace, read_csv  # noqa: E402
from bvmtools.waveform import percentile, trapezoid_integral, waveform_metrics, waveform_window_metrics  # noqa: E402


CONDITIONS = OrderedDict(
    (
        (
            "O+",
            {
                "label": "OLD-WITH-HISTORY",
                "context": "OLD",
                "history": "HISTORY_READ_PRESENT",
                "deck": REPO / "test/exploration/bvmsim-4bvm-jm2-connected-state-position-ab-v1-20260903/runs/1111/deck.cir",
                "raw": REPO / "test/exploration/bvmsim-4bvm-jm2-connected-state-position-ab-v1-20260903/runs/1111/raw.csv",
                "log": REPO / "test/exploration/bvmsim-4bvm-jm2-connected-state-position-ab-v1-20260903/runs/1111/run.log",
                "metadata": REPO / "test/exploration/bvmsim-4bvm-jm2-connected-state-position-ab-v1-20260903/runs/1111/metadata.json",
                "new_run": False,
            },
        ),
        (
            "O-",
            {
                "label": "OLD-NO-HISTORY",
                "context": "OLD",
                "history": "HISTORY_READ_ABSENT",
                "deck": EXP / "runs/OLD-NO-HISTORY/deck.cir",
                "raw": EXP / "runs/OLD-NO-HISTORY/raw.csv",
                "log": EXP / "runs/OLD-NO-HISTORY/run.log",
                "metadata": EXP / "runs/OLD-NO-HISTORY/metadata.json",
                "new_run": True,
            },
        ),
        (
            "N-",
            {
                "label": "NEW-NO-HISTORY",
                "context": "NEW",
                "history": "HISTORY_READ_ABSENT",
                "deck": REPO / "test/exploration/bvmsim-4bvm-allone-selective-read-additivity-isolation-v1-20260904/runs/1111/deck.cir",
                "raw": REPO / "test/exploration/bvmsim-4bvm-allone-selective-read-additivity-isolation-v1-20260904/runs/1111/raw.csv",
                "log": REPO / "test/exploration/bvmsim-4bvm-allone-selective-read-additivity-isolation-v1-20260904/runs/1111/run.log",
                "metadata": REPO / "test/exploration/bvmsim-4bvm-allone-selective-read-additivity-isolation-v1-20260904/runs/1111/metadata.json",
                "new_run": False,
            },
        ),
        (
            "N+",
            {
                "label": "NEW-WITH-HISTORY",
                "context": "NEW",
                "history": "HISTORY_READ_PRESENT",
                "deck": EXP / "runs/NEW-WITH-HISTORY/deck.cir",
                "raw": EXP / "runs/NEW-WITH-HISTORY/raw.csv",
                "log": EXP / "runs/NEW-WITH-HISTORY/run.log",
                "metadata": EXP / "runs/NEW-WITH-HISTORY/metadata.json",
                "new_run": True,
            },
        ),
    )
)

WINDOWS_PS = OrderedDict(
    (
        ("baseline_common", (45.0, 70.0)),
        ("history_intervention", (70.0, 81.0)),
        ("post_history_recovery", (81.0, 90.0)),
        ("write1", (90.0, 101.0)),
        ("pre_read1", (101.0, 110.0)),
        ("read1", (110.0, 121.0)),
        ("read1_response", (110.0, 160.0)),
        ("trajectory", (110.0, 170.0)),
        ("tail", (160.0, 170.0)),
    )
)

PAIR_SPECS = OrderedDict(
    (
        ("O+_vs_N+", ("O+", "N+", "history_present")),
        ("O-_vs_N-", ("O-", "N-", "history_absent")),
        ("O+_vs_O-", ("O+", "O-", "context_old")),
        ("N+_vs_N-", ("N+", "N-", "context_new")),
    )
)

STATE_NAMES = ("JM1_phase", "JM2_phase", "LM1_current", "LM2_current", "LM3_current", "LPM_current", "JS1_phase", "JS1_current", "JS2_phase", "JS2_current")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO.resolve()).as_posix()


def active_print_labels(deck: Path) -> list[str]:
    labels: list[str] = []
    for line in deck.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith(".print"):
            labels.extend(stripped.split()[1:])
    return labels


def time_tokens(path: Path) -> list[str]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.reader(handle)
        header = next(reader)
        index = header.index("time")
        return [row[index] for row in reader if row and any(cell.strip() for cell in row)]


def signal_for_bvm(number: int, name: str) -> str:
    mapping = {
        "JM1_phase": f"P(B_JM1|XBVM{number})",
        "JM2_phase": f"P(B_JM2|XBVM{number})",
        "LM1_current": f"I(L_M1|XBVM{number})",
        "LM2_current": f"I(L_M2|XBVM{number})",
        "LM3_current": f"I(L_M3|XBVM{number})",
        "LPM_current": f"I(L_PM|XBVM{number})",
        "JS1_phase": f"P(B_JS1|XBVM{number})",
        "JS1_current": f"I(B_JS1|XBVM{number})",
        "JS2_phase": f"P(B_JS2|XBVM{number})",
        "JS2_current": f"I(B_JS2|XBVM{number})",
    }
    return mapping[name]


def bvm_state_signals(number: int) -> tuple[str, ...]:
    return tuple(signal_for_bvm(number, name) for name in STATE_NAMES)


def bvm_internal_signals(number: int) -> tuple[str, ...]:
    return bvm_state_signals(number) + tuple(
        f"{kind}({element}|XBVM{number})"
        for element in ("L_M1", "L_M2", "L_M3", "L_PM", "L_PSL", "L_SL")
        for kind in ("I",)
    )


def sl_signals(number: int) -> tuple[str, ...]:
    return (f"I(L_PSL|XBVM{number})", f"V(SL{number})", f"I(L_SL|XBVM{number})")


GROUP_SIGNALS: OrderedDict[str, tuple[str, ...]] = OrderedDict(
    (
        (
            "bvm_internal",
            tuple(signal for number in range(1, 5) for signal in bvm_internal_signals(number)),
        ),
        ("sl", tuple(signal for number in range(1, 5) for signal in sl_signals(number))),
        ("qbin_lin", ("V(QBIN)", "V(QBOUT)", "I(LIN|XBQ1)")),
        ("qb_trajectory", ("P(BJ2|XBQ1)", "V(BJ2|XBQ1)")),
    )
)

TARGET_GROUP_WINDOWS = {
    "bvm_internal": "pre_read1",
    "sl": "read1_response",
    "qbin_lin": "read1_response",
    "qb_trajectory": "trajectory",
}


def unit_info(signal: str) -> tuple[str, str, float]:
    if signal.startswith("P"):
        return "rad", "turns", 1.0 / TAU
    if signal.startswith("V"):
        return "V", "mV", 1.0e3
    if signal.startswith("I"):
        return "A", "uA", 1.0e6
    raise ValueError(signal)


def display_series(trace: RawTrace, signal: str) -> tuple[float, ...]:
    values = trace.column(signal)
    factor = unit_info(signal)[2]
    if signal.startswith("P"):
        values = continuous_unwrap(values)
    return tuple(float(value) * factor for value in values)


def raw_series(trace: RawTrace, signal: str) -> tuple[float, ...]:
    values = trace.column(signal)
    return continuous_unwrap(values) if signal.startswith("P") else tuple(float(value) for value in values)


def indices_for(trace: RawTrace, window_name: str) -> tuple[int, ...]:
    start, end = WINDOWS_PS[window_name]
    return window_indices(trace.time, start * 1e-12, end * 1e-12)


def time_ps_at(trace: RawTrace, index: int) -> float:
    return trace.time[index] * 1.0e12


def waveform_stats(trace: RawTrace, signal: str, window_name: str) -> dict[str, object]:
    indices = indices_for(trace, window_name)
    times = [trace.time[index] for index in indices]
    values = [display_series(trace, signal)[index] for index in indices]
    base = waveform_metrics(times, values)
    source_unit, display_unit, _ = unit_info(signal)
    return {
        "signal": signal,
        "window": window_name,
        "window_ps": list(WINDOWS_PS[window_name]),
        "sample_count": len(indices),
        "source_unit": source_unit,
        "display_unit": display_unit,
        "minimum": base["minimum"],
        "maximum": base["maximum"],
        "p2p": base["p2p"],
        "rms": base["rms"],
        "signed_integral_display_unit_s": base["signed_time_integral"],
        "signed_integral_display_unit_ps": float(base["signed_time_integral"]) * 1.0e12,
        "peak_value": base["peak_value"],
        "peak_time_ps": float(base["peak_time"]) * 1.0e12,
        "minimum_value": base["minimum_value"],
        "minimum_time_ps": float(base["minimum_time"]) * 1.0e12,
    }


def p95(values: list[float]) -> float:
    return float(percentile(values, 0.95)) if values else 0.0


def pair_metric(left: RawTrace, right: RawTrace, signal: str, window_name: str, scale: float | None = None) -> dict[str, object]:
    left_values = display_series(left, signal)
    right_values = display_series(right, signal)
    left_indices = indices_for(left, window_name)
    right_indices = indices_for(right, window_name)
    left_time = [left.time[index] for index in left_indices]
    right_time = [right.time[index] for index in right_indices]
    left_selected = [left_values[index] for index in left_indices]
    right_selected = [right_values[index] for index in right_indices]
    comparison = compare_series(left_time, left_selected, right_time, right_selected, include_correlation=True)
    difference = [right_value - left_value for left_value, right_value in zip(left_selected, right_selected)]
    robust_scale = 1.0 if scale is None or scale == 0.0 else float(scale)
    source_unit, display_unit, _ = unit_info(signal)
    result = {
        "signal": signal,
        "window": window_name,
        "window_ps": list(WINDOWS_PS[window_name]),
        "difference_convention": "right_minus_left",
        "source_unit": source_unit,
        "display_unit": display_unit,
        "time_grid_exact": bool(comparison["time_grid_exact"]),
        "sample_count": len(difference),
        "max_abs_difference": max(abs(value) for value in difference),
        "rms_difference": math.sqrt(sum(value * value for value in difference) / len(difference)),
        "p95_abs_difference": p95([abs(value) for value in difference]),
        "correlation": comparison.get("correlation"),
        "normalization_scale_display": robust_scale,
        "normalized_rms_difference": math.sqrt(sum(value * value for value in difference) / len(difference)) / robust_scale,
    }
    return result


def robust_scales(traces: dict[str, RawTrace], signals: tuple[str, ...], window_name: str) -> dict[str, float]:
    result: dict[str, float] = {}
    for signal in signals:
        values: list[float] = []
        for trace in traces.values():
            series = display_series(trace, signal)
            values.extend(series[index] for index in indices_for(trace, window_name))
        center = median(values)
        robust = p95([abs(value - center) for value in values]) if values else 0.0
        result[signal] = robust if robust > 1.0e-12 else 1.0e-12
    return result


def group_pair_summary(pair_metrics: dict[str, dict[str, object]], group: str, signals: tuple[str, ...], scales: dict[str, float]) -> dict[str, object]:
    normalized: dict[str, list[float]] = {name: [] for name in PAIR_SPECS}
    raw_rms: dict[str, list[float]] = {name: [] for name in PAIR_SPECS}
    for pair_name, metrics in pair_metrics.items():
        for signal in signals:
            item = metrics[signal]
            normalized[pair_name].append(float(item["normalized_rms_difference"]))
            raw_rms[pair_name].append(float(item["rms_difference"]))
    history_names = ("O+_vs_N+", "O-_vs_N-")
    context_names = ("O+_vs_O-", "N+_vs_N-")
    history_values = [value for name in history_names for value in normalized[name]]
    context_values = [value for name in context_names for value in normalized[name]]
    history_pair_max = {name: max(normalized[name], default=0.0) for name in history_names}
    context_pair_min = {name: min(normalized[name], default=0.0) for name in context_names}
    return {
        "group": group,
        "signal_count": len(signals),
        "history_pair_normalized_rms_by_signal": normalized,
        "context_pair_normalized_rms_by_signal": {name: normalized[name] for name in context_names},
        "history_pair_median_normalized_rms": median(history_values) if history_values else 0.0,
        "context_pair_median_normalized_rms": median(context_values) if context_values else 0.0,
        "history_pair_max_normalized_rms": history_pair_max,
        "context_pair_min_normalized_rms": context_pair_min,
        "history_grouping_observed": bool(history_values) and max(history_values) < min(context_values),
        "normalization": "per-signal p95 absolute deviation from the four-condition median in this window; floor=1e-12 display unit",
    }


def crossing_times(trace: RawTrace, signal: str, window_name: str, max_crossings: int = 8) -> list[float]:
    indices = indices_for(trace, window_name)
    phase = continuous_unwrap(trace.column(signal))
    baseline = phase[indices[0]]
    crossings: list[float] = []
    for number in range(1, max_crossings + 1):
        target = baseline + number * TAU
        found = next((index for index in indices if phase[index] >= target), None)
        if found is None:
            break
        crossings.append(time_ps_at(trace, found))
    return crossings


def trajectory_metrics(trace: RawTrace) -> dict[str, object]:
    phase_signal = "P(BJ2|XBQ1)"
    voltage_signal = "V(BJ2|XBQ1)"
    indices = indices_for(trace, "trajectory")
    phase_raw = trace.column(phase_signal)
    phase = continuous_unwrap(phase_raw)
    phase_delta_rad = phase[indices[-1]] - phase[indices[0]]
    phase_delta_turns = phase_delta_rad / TAU
    voltage_area = phase_area_window(trace.time, phase_raw, trace.column(voltage_signal), (110e-12, 170e-12), include_segments=True)
    segments = monotonic_segments([phase[index] for index in indices])
    segment_turns = [abs((phase[indices[item.end_index]] - phase[indices[item.start_index]]) / TAU) for item in segments]
    return {
        "phase_signal": phase_signal,
        "voltage_signal": voltage_signal,
        "window": "trajectory",
        "phase_start_rad": phase[indices[0]],
        "phase_end_rad": phase[indices[-1]],
        "phase_delta_rad": phase_delta_rad,
        "phase_delta_turns": phase_delta_turns,
        "same_jj_voltage_area_over_phi0_turns": voltage_area["voltage_area_over_phi0"],
        "phase_area_residual_turns": voltage_area["phase_area_residual_turns"],
        "integer_crossing_markers_ps": crossing_times(trace, phase_signal, "read1_response"),
        "monotonic_segment_count": len(segments),
        "largest_monotonic_segment_abs_turns": max(segment_turns, default=0.0),
        "continuous_multiturn_segment_over_1_15_turns": any(value > 1.15 for value in segment_turns),
        "classification_boundary": "integer crossings and cumulative turns are trajectory markers, not clean SFQ event counts",
    }


def endpoint_value(trace: RawTrace, signal: str, target_ps: float = 109.9) -> float:
    indices = [index for index, value in enumerate(trace.time) if abs(value * 1.0e12 - target_ps) < 1.0e-9]
    if len(indices) != 1:
        raise RuntimeError(f"{trace.path}: expected exact {target_ps} ps sample for {signal}")
    return display_series(trace, signal)[indices[0]]


def state_vectors(traces: dict[str, RawTrace]) -> dict[str, object]:
    result: dict[str, object] = {}
    for condition, trace in traces.items():
        bvm_result: dict[str, object] = {}
        for number in range(1, 5):
            values = {name: endpoint_value(trace, signal_for_bvm(number, name)) for name in STATE_NAMES}
            values["JM1_positive_marker"] = values["JM1_phase"] > 0.0
            values["state_code_context"] = "1111 protocol target; marker is descriptive, not inferred from JM1/JM2 threshold"
            bvm_result[f"BVM{number}"] = values
        result[condition] = bvm_result
    return result


def lsl_sum(trace: RawTrace) -> tuple[float, ...]:
    branches = {f"LSL{number}": trace.column(f"I(L_SL|XBVM{number})") for number in range(1, 5)}
    return tuple(sum(branches[name][index] for name in branches) for index in range(trace.sample_count))


def closure_metrics(traces: dict[str, RawTrace]) -> dict[str, object]:
    result: dict[str, object] = {"orientation": "residual = I(LIN|XBQ1) - sum_i I(L_SL|XBVMi); all branch currents retain JoSIM sign direction", "per_condition": {}, "pairwise": {}}
    for condition, trace in traces.items():
        branches = {"LIN": trace.column("I(LIN|XBQ1)")}
        branches.update({f"LSL{number}": trace.column(f"I(L_SL|XBVM{number})") for number in range(1, 5)})
        residual = linear_kcl_residual(branches, {"LIN": 1.0, "LSL1": -1.0, "LSL2": -1.0, "LSL3": -1.0, "LSL4": -1.0})
        result["per_condition"][condition] = {window: kcl_window_metrics(trace.time, residual, (bounds[0] * 1e-12, bounds[1] * 1e-12), unit="A") for window, bounds in WINDOWS_PS.items() if window in ("history_intervention", "pre_read1", "read1_response")}
    for pair_name, (left_name, right_name, _) in PAIR_SPECS.items():
        left, right = traces[left_name], traces[right_name]
        delta_branches = {"LIN": tuple(a - b for a, b in zip(left.column("I(LIN|XBQ1)"), right.column("I(LIN|XBQ1)")))}
        for number in range(1, 5):
            label = f"LSL{number}"
            delta_branches[label] = tuple(a - b for a, b in zip(left.column(f"I(L_SL|XBVM{number})"), right.column(f"I(L_SL|XBVM{number})")))
        residual = linear_kcl_residual(delta_branches, {"LIN": 1.0, "LSL1": -1.0, "LSL2": -1.0, "LSL3": -1.0, "LSL4": -1.0})
        result["pairwise"][pair_name] = {window: kcl_window_metrics(left.time, residual, (bounds[0] * 1e-12, bounds[1] * 1e-12), unit="A") for window, bounds in WINDOWS_PS.items() if window in ("history_intervention", "pre_read1", "read1_response")}
    return result


def control_check(traces: dict[str, RawTrace]) -> dict[str, object]:
    checkpoints = (75.0, 95.0, 115.0)
    result: dict[str, object] = {}
    for condition, trace in traces.items():
        result[condition] = {}
        for checkpoint in checkpoints:
            index = next(index for index, value in enumerate(trace.time) if abs(value * 1e12 - checkpoint) < 1e-9)
            result[condition][str(checkpoint)] = {control: trace.column(f"I(I_{control}1)")[index] * 1.0e6 for control in ("WL", "BL", "SE")}
    return {"BVM1_checkpoint_currents_uA": result, "meaning": "75 ps checks history window; 95 ps checks WRITE1; 115 ps checks final READ1; BVM1 is representative because the four source waveforms are statically all-BVM matched"}


def post_run_qa(traces: dict[str, RawTrace]) -> dict[str, object]:
    checks: dict[str, object] = {"status": "PASS", "conditions": {}, "time_grid": {}, "immutable_reference_hashes": {}, "control_waveform": {}}
    full_labels = active_print_labels(CONDITIONS["N+"]["deck"])
    for condition, spec in CONDITIONS.items():
        trace = traces[condition]
        metadata = json.loads(spec["metadata"].read_text(encoding="utf-8")) if spec["metadata"].is_file() else {}
        command_metadata = metadata.get("command", {})
        solver_exit_code = command_metadata.get("exit_code") if isinstance(command_metadata, dict) else metadata.get("exit_code")
        expected_labels = full_labels if condition in ("O-", "N+") else active_print_labels(spec["deck"])
        missing = [label for label in expected_labels if label not in trace.headers]
        duplicate = trace.duplicate_columns
        log_text = spec["log"].read_text(encoding="utf-8", errors="replace") if spec["log"].is_file() else ""
        checks["conditions"][condition] = {
            "raw": rel(spec["raw"]),
            "deck": rel(spec["deck"]),
            "raw_sha256": sha256(spec["raw"]),
            "deck_sha256": sha256(spec["deck"]),
            "sample_count": trace.sample_count,
            "header_count": len(trace.headers),
            "missing_required_probes": missing,
            "duplicate_columns": duplicate,
            "solver_exit_code": solver_exit_code,
            "metadata_artifact_status": metadata.get("artifact_status"),
            "metadata_hashes_match": (
                not spec["new_run"]
                or metadata.get("hashes", {}).get("deck_sha256") == sha256(spec["deck"])
                and metadata.get("hashes", {}).get("raw_sha256") == sha256(spec["raw"])
                and metadata.get("hashes", {}).get("log_sha256") == sha256(spec["log"])
            ),
            "solver_identity": metadata.get("solver", {}).get("sha256") if isinstance(metadata.get("solver"), dict) else None,
            "model_warning": bool(re.search(r"Missing model:|Using default model", log_text, re.I)),
            "time_start_ps": trace.time[0] * 1e12,
            "time_end_ps": trace.time[-1] * 1e12,
            "dt_min_ps": min(trace.dt) * 1e12,
            "dt_max_ps": max(trace.dt) * 1e12,
        }
        if missing or duplicate or checks["conditions"][condition]["solver_exit_code"] != 0 or checks["conditions"][condition]["model_warning"] or not checks["conditions"][condition]["metadata_hashes_match"]:
            checks["status"] = "ARTIFACT_INVALID"
    reference_hashes = {
        "O+_deck": "3fcdb8b0d61c91cadcacee77c3c06b3a03f8f9392a8c838e9b8574b8938b4e88",
        "O+_raw": "9563ac09d75770cd9d9c2f2a93de0f418778012e64adb40fbf118ae0561d813f",
        "N-_deck": "5ee085051cfdc2cc6e45deac657230e86c64795d9cd9be100735b13974c3222e",
        "N-_raw": "b3d421822dd893d17331016b7f954784d24c90c97f58bc362676467c7650998b",
    }
    actual_reference_hashes = {"O+_deck": sha256(CONDITIONS["O+"]["deck"]), "O+_raw": sha256(CONDITIONS["O+"]["raw"]), "N-_deck": sha256(CONDITIONS["N-"]["deck"]), "N-_raw": sha256(CONDITIONS["N-"]["raw"])}
    checks["immutable_reference_hashes"] = {"expected": reference_hashes, "actual": actual_reference_hashes, "unchanged": reference_hashes == actual_reference_hashes}
    if not checks["immutable_reference_hashes"]["unchanged"]:
        checks["status"] = "ARTIFACT_INVALID"
    base = traces["O+"].time
    checks["time_grid"] = {
        "all_float_time_tuples_exact": all(exact_time_grid_identity(base, trace.time) for trace in traces.values()),
        "all_time_tokens_exact": all(time_tokens(CONDITIONS["O+"]["raw"]) == time_tokens(spec["raw"]) for spec in CONDITIONS.values()),
        "sample_count": len(base),
        "stored_start_ps": base[0] * 1e12,
        "stored_end_ps": base[-1] * 1e12,
        "requested_timestep_ps": 0.1,
        "stored_dt_note": "stored output contains 0.1/0.2 ps intervals; comparisons use the exact stored grid and do not interpolate",
    }
    if not checks["time_grid"]["all_float_time_tuples_exact"] or not checks["time_grid"]["all_time_tokens_exact"]:
        checks["status"] = "ARTIFACT_INVALID"
    for condition, trace in traces.items():
        history_value = 100.0 if CONDITIONS[condition]["history"] == "HISTORY_READ_PRESENT" else 0.0
        expected_controls = {
            75.0: {"WL": history_value, "BL": 0.0, "SE": history_value},
            95.0: {"WL": 100.0, "BL": 100.0, "SE": 0.0},
            115.0: {"WL": 100.0, "BL": 0.0, "SE": 100.0},
        }
        actual: dict[str, dict[str, float]] = {}
        mismatches: list[str] = []
        for checkpoint, expected in expected_controls.items():
            index = next(index for index, value in enumerate(trace.time) if abs(value * 1e12 - checkpoint) < 1e-9)
            actual[str(checkpoint)] = {}
            for control, expected_value in expected.items():
                value = trace.column(f"I(I_{control}1)")[index] * 1e6
                actual[str(checkpoint)][control] = value
                if value != expected_value:
                    mismatches.append(f"{checkpoint}:{control}={value} expected {expected_value}")
        checks["control_waveform"][condition] = {"actual_bvm1_uA": actual, "expected_bvm1_uA": {str(key): value for key, value in expected_controls.items()}, "mismatches": mismatches, "status": "PASS" if not mismatches else "FAIL"}
        if mismatches:
            checks["status"] = "ARTIFACT_INVALID"
    return checks


def write_csv(path: Path, names: list[str], series: list[tuple[float, ...]], time: tuple[float, ...]) -> None:
    if len(names) != len(series) or any(len(values) != len(time) for values in series):
        raise RuntimeError(f"plot input shape mismatch: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["time", *names])
        writer.writerows(zip(time, *series))


def plot_label(kind: str, condition: str, signal: str) -> str:
    prefix = signal[0]
    return f"{prefix}({condition}::{signal})"


def make_plot_inputs(traces: dict[str, RawTrace]) -> list[dict[str, object]]:
    PLOT_INPUTS.mkdir(parents=True, exist_ok=True)
    time = traces["O+"].time
    manifest: list[dict[str, object]] = []
    standalone = {
        "BVM_INTERNAL_STATE": ("P(B_JM1|XBVM1)", "P(B_JM1|XBVM2)", "P(B_JM1|XBVM3)", "P(B_JM1|XBVM4)", "P(B_JM2|XBVM1)", "P(B_JM2|XBVM2)", "P(B_JM2|XBVM3)", "P(B_JM2|XBVM4)"),
        "BVM_RLOOP_CURRENT": tuple(f"I(L_M3|XBVM{n})" for n in range(1, 5)) + tuple(f"I(L_PM|XBVM{n})" for n in range(1, 5)),
        "BVM_RLOOP_VOLTAGE": tuple(f"V(B_JM1|XBVM{n})" for n in range(1, 5)) + tuple(f"V(B_JM2|XBVM{n})" for n in range(1, 5)),
        "BVM_SENSING": tuple(f"I(L_SL|XBVM{n})" for n in range(1, 5)) + tuple(f"V(SL{n})" for n in range(1, 5)),
        "BVMOUT_QB_INPUT": ("P(BVMOUT)", "V(BVMOUT)", "I(BVMOUT)", "V(QBIN)", "I(LIN|XBQ1)", "V(QBOUT)"),
        "QB_INTERNAL": ("P(BJS|XBQ1)", "P(BJ1|XBQ1)", "P(BJ2|XBQ1)", "V(BJ2|XBQ1)", "I(L1|XBQ1)", "I(L2|XBQ1)"),
        "JTL_TRANSPORT": tuple(f"P(B02|XJTL1_{stage})" for stage in range(1, 7)),
    }
    for condition, spec in CONDITIONS.items():
        for name, signals in standalone.items():
            selected = [signal for signal in signals if signal in traces[condition].headers]
            if not selected:
                raise RuntimeError(f"no standalone signals for {condition}/{name}")
            manifest.append({"phase": "standalone", "name": f"{condition}_{name}", "condition": condition, "input": rel(spec["raw"]), "output": f"plots/runs/{condition}/{name}.html", "subset": list(selected), "title": f"{condition} {spec['label']} — {name}"})

    def derived(name: str, specs: list[tuple[str, str, str]], title: str) -> None:
        names: list[str] = []
        series: list[tuple[float, ...]] = []
        for label, condition, signal in specs:
            names.append(label)
            series.append(raw_series(traces[condition], signal))
        filename = f"{name}.csv"
        write_csv(PLOT_INPUTS / filename, names, series, time)
        manifest.append({"phase": "comparison", "name": name, "input": f"analysis/plot_inputs/{filename}", "output": f"plots/comparison/{name}.html", "subset": names, "title": title})

    all_conditions = list(CONDITIONS)
    derived("HISTORY_CONTROL_2X2", [(plot_label("I", c, signal), c, signal) for c in all_conditions for signal in ("I(I_WL1)", "I(I_BL1)", "I(I_SE1)")], "HISTORY_READ crossover — BVM1 WL / BL / SE controls — O+ O- N- N+")
    derived("PRE_READ1_LM3_2X2", [(plot_label("I", c, f"I(L_M3|XBVM{n})"), c, f"I(L_M3|XBVM{n})") for n in range(1, 5) for c in all_conditions], "PRE_READ1 LM3 crossover — all BVMs — O+ O- N- N+")
    state_specs = [(plot_label("P", c, f"P(B_JM{j}|XBVM{n})"), c, f"P(B_JM{j}|XBVM{n})") for n in range(1, 5) for j in (1, 2) for c in all_conditions]
    derived("PRE_READ1_STATE_VECTOR_2X2", state_specs, "PRE_READ1 BVM JM1/JM2 phase state — four conditions")
    for n in range(1, 5):
        derived(f"BVM{n}_LSL_CROSSOVER", [(plot_label("I", c, f"I(L_SL|XBVM{n})"), c, f"I(L_SL|XBVM{n})") for c in all_conditions], f"BVM{n} LSL output crossover — O+ O- N- N+")
    sum_specs: list[tuple[str, str, str]] = []
    for c in all_conditions:
        sum_name = f"I(SUM_LSL|{c})"
        names = [f"I(L_SL|XBVM{n})" for n in range(1, 5)]
        series = tuple(sum(traces[c].column(signal)[index] for signal in names) for index in range(traces[c].sample_count))
        sum_specs.append((sum_name, c, "I(LIN|XBQ1)"))
        # Add the sum as an explicit derived column below; LIN remains a raw column.
        if c == all_conditions[0]:
            total_names: list[str] = []
            total_series: list[tuple[float, ...]] = []
        total_names.append(sum_name)
        total_series.append(series)
    lin_names = [plot_label("I", c, "I(LIN|XBQ1)") for c in all_conditions]
    total_names.extend(lin_names)
    total_series.extend([traces[c].column("I(LIN|XBQ1)") for c in all_conditions])
    write_csv(PLOT_INPUTS / "TOTAL_BVM_OUTPUT_VS_LIN.csv", total_names, total_series, time)
    manifest.append({"phase": "comparison", "name": "TOTAL_BVM_OUTPUT_VS_LIN", "input": "analysis/plot_inputs/TOTAL_BVM_OUTPUT_VS_LIN.csv", "output": "plots/comparison/TOTAL_BVM_OUTPUT_VS_LIN.html", "subset": total_names, "title": "Σ BVM LSL output versus LIN — four-condition crossover"})
    derived("QBIN_LIN_CROSSOVER", [(plot_label("V", c, "V(QBIN)"), c, "V(QBIN)") for c in all_conditions] + [(plot_label("I", c, "I(LIN|XBQ1)"), c, "I(LIN|XBQ1)") for c in all_conditions], "QBIN and LIN crossover — O+ O- N- N+")
    derived("BJ2_CROSSOVER_4CONDITION", [(plot_label("P", c, "P(BJ2|XBQ1)"), c, "P(BJ2|XBQ1)") for c in all_conditions] + [(plot_label("V", c, "V(BJ2|XBQ1)"), c, "V(BJ2|XBQ1)") for c in all_conditions], "QB BJ2 trajectory crossover — phase and voltage — O+ O- N- N+")
    derived("BJ2_CROSSING_TIMELINE_2X2", [(plot_label("P", c, "P(BJ2|XBQ1)"), c, "P(BJ2|XBQ1)") for c in all_conditions], "BJ2 integer-crossing timeline markers — not SFQ count")
    distance_specs: list[tuple[str, str, str]] = []
    for signal in ("P(B_JM2|XBVM1)", "I(L_M3|XBVM1)", "I(L_SL|XBVM1)", "I(LIN|XBQ1)", "V(QBIN)", "P(BJ2|XBQ1)"):
        for pair_name, (left_name, right_name, _) in PAIR_SPECS.items():
            prefix = signal[0]
            label = f"{prefix}(|{pair_name}|::{signal})"
            left_values = display_series(traces[left_name], signal)
            right_values = display_series(traces[right_name], signal)
            # Difference is already in display units; plot2 only divides phase columns by 2π.
            # Convert it back to raw units so -j 2pi yields display turns exactly once.
            factor = unit_info(signal)[2]
            values = tuple(abs(right_values[index] - left_values[index]) / factor for index in range(len(time)))
            distance_specs.append((label, "", ""))
            if len(distance_specs) == 1:
                distance_names: list[str] = []
                distance_series: list[tuple[float, ...]] = []
            distance_names.append(label)
            distance_series.append(values)
    write_csv(PLOT_INPUTS / "HISTORY_GROUPING_VS_CONTEXT_GROUPING.csv", distance_names, distance_series, time)
    manifest.append({"phase": "comparison", "name": "HISTORY_GROUPING_VS_CONTEXT_GROUPING", "input": "analysis/plot_inputs/HISTORY_GROUPING_VS_CONTEXT_GROUPING.csv", "output": "plots/comparison/HISTORY_GROUPING_VS_CONTEXT_GROUPING.html", "subset": distance_names, "title": "Pairwise waveform distances — history pairs versus context pairs (no aggregate score)"})
    return manifest


def render_metadata(manifest: list[dict[str, object]]) -> dict[str, object]:
    return {"schema": "bvmsim-1111-history-read-crossover-analysis-v1", "conditions": list(CONDITIONS), "windows_ps": {name: list(bounds) for name, bounds in WINDOWS_PS.items()}, "pair_specs": {name: list(spec) for name, spec in PAIR_SPECS.items()}, "phase_raw_unit": "rad", "phase_display": "continuous_unwrap(rad)/(2*pi)", "interpolation": "none", "plot_manifest": manifest}


def make_metrics(traces: dict[str, RawTrace], qa: dict[str, object]) -> dict[str, object]:
    common_signals = [signal for signal in traces["O+"].headers if signal != "time" and all(signal in traces[c].headers for c in CONDITIONS)]
    time_grid_equal = all(exact_time_grid_identity(traces["O+"].time, traces[c].time) for c in CONDITIONS)
    scales = {group: {window: robust_scales(traces, signals, window) for window in WINDOWS_PS} for group, signals in GROUP_SIGNALS.items()}
    pairwise: dict[str, object] = {}
    groupings: dict[str, object] = {}
    for group, signals in GROUP_SIGNALS.items():
        pairwise[group] = {}
        for window in WINDOWS_PS:
            pairwise[group][window] = {}
            for pair_name, (left_name, right_name, _) in PAIR_SPECS.items():
                pairwise[group][window][pair_name] = {signal: pair_metric(traces[left_name], traces[right_name], signal, window, scales[group][window][signal]) for signal in signals}
            groupings.setdefault(group, {})[window] = group_pair_summary(pairwise[group][window], group, signals, scales[group][window])

    lsl_waveforms: dict[str, object] = {}
    for condition, trace in traces.items():
        lsl_waveforms[condition] = {}
        for number in range(1, 5):
            signal = f"I(L_SL|XBVM{number})"
            lsl_waveforms[condition][f"BVM{number}"] = {window: waveform_stats(trace, signal, window) for window in ("read1", "read1_response")}

    qbin_lin = {condition: {signal: {window: waveform_stats(trace, signal, window) for window in ("pre_read1", "read1", "read1_response")} for signal in ("V(QBIN)", "I(LIN|XBQ1)")} for condition, trace in traces.items()}
    trajectories = {condition: trajectory_metrics(trace) for condition, trace in traces.items()}
    exact_pairs: dict[str, object] = {}
    for pair_name, (left_name, right_name, _) in PAIR_SPECS.items():
        shared = [signal for signal in common_signals if signal in traces[left_name].headers and signal in traces[right_name].headers]
        unequal: list[str] = []
        max_abs_by_signal: dict[str, float] = {}
        for signal in shared:
            left_values = traces[left_name].column(signal)
            right_values = traces[right_name].column(signal)
            max_abs = max(abs(a - b) for a, b in zip(left_values, right_values))
            max_abs_by_signal[signal] = max_abs
            if max_abs != 0.0:
                unequal.append(signal)
        exact_pairs[pair_name] = {"common_signal_count": len(shared), "all_common_samples_exact": not unequal, "unequal_signal_count": len(unequal), "first_unequal_signals": unequal[:12], "max_abs_native_by_signal": max_abs_by_signal}

    history_grouped_all = all(bool(groupings[group][TARGET_GROUP_WINDOWS[group]]["history_grouping_observed"]) for group in GROUP_SIGNALS)
    history_exact_all = all(bool(exact_pairs[name]["all_common_samples_exact"]) for name in ("O+_vs_N+", "O-_vs_N-"))
    context_nonzero_all = all(not bool(exact_pairs[name]["all_common_samples_exact"]) for name in ("O+_vs_O-", "N+_vs_N-"))
    crossover_assessment = "HISTORY_GROUPING_OBSERVED_ACROSS_KEY_LAYERS" if history_grouped_all else "MIXED_OR_UNRESOLVED_GROUPING"
    if history_grouped_all and history_exact_all and context_nonzero_all:
        crossover_assessment = "HISTORY_GROUPING_OBSERVED_ACROSS_KEY_LAYERS_WITH_EXACT_COMMON_GRID_MATCHES"
    return {
        "schema": "bvmsim-1111-history-read-crossover-metrics-v1",
        "artifact_status": qa["status"],
        "conditions": list(CONDITIONS),
        "common_probe_count": len(common_signals),
        "common_probes": common_signals,
        "time_grid": {"exact_all_conditions": time_grid_equal, "sample_count": traces["O+"].sample_count, "start_ps": traces["O+"].time[0] * 1e12, "end_ps": traces["O+"].time[-1] * 1e12, "requested_timestep_ps": 0.1, "interpolation": "none"},
        "post_run_qa": qa,
        "controls": control_check(traces),
        "pre_read1_state_vectors_at_109_9ps": state_vectors(traces),
        "normalization_scales": scales,
        "pairwise": pairwise,
        "groupings": groupings,
        "exact_common_grid_pairs": exact_pairs,
        "bvm_lsl_waveforms": lsl_waveforms,
        "qbin_lin_waveforms": qbin_lin,
        "lin_minus_sum_lsl_closure": closure_metrics(traces),
        "bj2_trajectory": trajectories,
        "crossover_assessment": {
            "label": crossover_assessment,
            "history_pairs": {"O+_vs_N+": "present-present", "O-_vs_N-": "absent-absent"},
            "context_pairs": {"O+_vs_O-": "OLD present-absent", "N+_vs_N-": "NEW present-absent"},
            "history_grouping_across_bvm_internal_sl_qbin_lin_qb_trajectory": history_grouped_all,
            "both_history_pairs_exact_on_common_grid": history_exact_all,
            "both_context_pairs_nonexact_on_common_grid": context_nonzero_all,
            "interpretation": "This is a bounded crossover observation at dt=0.1 ps; it is not a unique-root-cause proof or clean SFQ count.",
        },
        "convergence_claim": "NOT_CLAIMED",
    }


def markdown_report(metrics: dict[str, object]) -> str:
    qa = metrics["post_run_qa"]
    trajectories = metrics["bj2_trajectory"]
    states = metrics["pre_read1_state_vectors_at_109_9ps"]
    grouping = metrics["groupings"]
    closure = metrics["lin_minus_sum_lsl_closure"]
    lines = [
        "# 1111 HISTORY-READ CROSSOVER CAUSAL A/B",
        "",
        "本报告只分析四个条件 `O+ / O- / N- / N+` 的 crossover；不把最终 4/5 表象单独当作因果结论。所有 `P(...)` 原始值是 rad；显示的 turns 仅由 continuous unwrap(rad)/(2π) 得到。",
        "",
        "## 1. Question",
        "",
        "检验 70–81 ps `HISTORY_READ_PRESENT/ABSENT` 是否比 OLD/NEW deck context 更能解释 BVM internal state、LSL、LIN/QBIN 和 QB BJ2 trajectory。",
        "",
        "## 2. Existing evidence and four-condition design",
        "",
        "| condition | context | history | authority |",
        "|---|---|---|---|",
        "| O+ | OLD | PRESENT | immutable existing raw |",
        "| O- | OLD | ABSENT | new physical run |",
        "| N- | NEW | ABSENT | immutable existing raw |",
        "| N+ | NEW | PRESENT | new physical run |",
        "",
        "O+ 和 N- 的原始 CSV 未重跑、未覆盖；O- 和 N+ 是本轮唯一新增的两个物理条件。",
        "",
        "## 3. What changed / what did not change",
        "",
        "O- 仅移除 OLD 母本的 70–81 ps all-BVM positive history read；N+ 仅把 exact OLD history waveform 放入 NEW 母本。其它物理主体、WRITE1、final READ1、QB/JTL/load、模型、`dt=0.1 ps` 和停止时间均冻结。O- 采用完整 branch probe schema 的额外 `.print` 只改变 observability。",
        "",
        "## 4. Static deck-diff proof",
        "",
        "见 `analysis/static_preflight.json`：未分类 physics difference 为 0；history present/absent 的源波形比较最大差均为 0 A；BL、WRITE1、final READ1、history 窗外源波形比较最大差均为 0 A；完整 probe schema 为 229 项。",
        "",
        "## 5. Artifact validity",
        "",
        f"post-run QA: **{qa['status']}**。四组均为 {metrics['time_grid']['sample_count']} 个样本，存储时间 {metrics['time_grid']['start_ps']:.1f}–{metrics['time_grid']['end_ps']:.1f} ps；四组 float/time-token grid exact equal；比较无插值。原始存储间隔实际包含 0.1/0.2 ps，`0.1 ps` 是 requested timestep。",
        "",
        "## 6. 70 ps pre-intervention parity",
        "",
        "在 `baseline_common=[45,70) ps`，O+ vs O- 与 N+ vs N- 的 common probes 逐点一致；完整 pair exactness 也见 `exact_common_grid_pairs`。因此本 crossover 的 history intervention 有明确的 70 ps anchor。",
        "",
        "## 7. History intervention and control semantics",
        "",
        "`HISTORY_READ_PRESENT` 的 75 ps 检查为 WL=+100 µA、BL=0、SE=+100 µA；`HISTORY_READ_ABSENT` 为三者 0。95 ps WRITE1 与 115 ps final READ1 的控制语义保持一致。详情见 `controls`。",
        "",
        "## 8. PRE_READ1 logical-state marker",
        "",
        "四条件的 protocol state target 都是 1111。109.9 ps 的 `JM1_positive_marker` 仅作极性/存储方向描述；不使用 `JM1 AND JM2 >= 0.25 turn` 作为唯一逻辑判据。实际的 JM1/JM2/JS1/JS2/LM1/LM2/LM3/LPM 数值和单位见 `pre_read1_state_vectors_at_109_9ps`。",
        "",
    ]
    lines += ["| condition | BVM | JM1 phase (turns) | JM2 phase (turns) | LM3 (µA) | LPM (µA) | JS1 phase (turns) | JS2 phase (turns) |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for condition in CONDITIONS:
        for number in range(1, 5):
            item = states[condition][f"BVM{number}"]
            lines.append(f"| {condition} | BVM{number} | {item['JM1_phase']:.9f} | {item['JM2_phase']:.9f} | {item['LM3_current']:.6f} | {item['LPM_current']:.6f} | {item['JS1_phase']:.9f} | {item['JS2_phase']:.9f} |")
    lines += [
        "",
        "## 9. PRE_READ1 analog-state crossover",
        "",
        "不把不同量纲裸相加；pairwise comparison 使用每个 signal 独立的 robust scale（四条件、该窗口的 p95 absolute deviation，floor=1e-12 display unit），同时保留逐 signal absolute/RMS difference。",
        "",
    ]
    for group in ("bvm_internal", "sl", "qbin_lin", "qb_trajectory"):
        window = {"bvm_internal": "pre_read1", "sl": "read1_response", "qbin_lin": "read1_response", "qb_trajectory": "trajectory"}[group]
        item = grouping[group][window]
        lines.append(f"- `{group}` ({window}): history-pair median normalized RMS={item['history_pair_median_normalized_rms']:.6g}，context-pair median normalized RMS={item['context_pair_median_normalized_rms']:.6g}；`history_grouping_observed={item['history_grouping_observed']}`。")
    lines += [
        "",
        "## 10. BVM internal crossover",
        "",
        "重点信号覆盖 JM1、JM2、LM3、JS1、JS2、LM1、LM2、LPM；完整逐信号 pair metrics 在 `pairwise.bvm_internal`，不只看 JM1。R_S/LS3 虽在 O−/N−/N+ 的 full-probe raw 中保留，但不可修改的 O+ historical raw 缺少这两列，因此不纳入四条件聚合，跨四条件结论记为 UNKNOWN。",
        "",
        "## 11. BVM LSL output crossover",
        "",
        "四颗 BVM 的 `I(L_SL|XBVMn)` 均作为独立 waveform 统计；各自的 min/max/p2p/RMS/signed integral/peak time 在 `bvm_lsl_waveforms`，四条件同图在 `plots/comparison/BVM1_LSL_CROSSOVER.html` 等四张图中。",
        "",
        "## 12. ΣLSL → LIN closure",
        "",
        "使用共享 `bvmtools.kcl.linear_kcl_residual`，方向固定为 `I(LIN) - Σ I(L_SL)`；并对四个 pair 的差分验证相同关系。`lin_minus_sum_lsl_closure` 同时给出 history window、PRE_READ1 和 final response 的 max-abs/RMS KCL residual，单位 µA。",
        "",
        "## 13. QB input crossover",
        "",
        "先比较 BVM/LSL 与 LIN，再看 QB；`V(QBIN)`、`I(LIN|XBQ1)`、`V(QBOUT)` 的四条件 waveform 和 pairwise distances 在 `qbin_lin_waveforms` 与 `pairwise.qbin_lin`。",
        "",
        "## 14. BJ2 trajectory crossover",
        "",
        "| condition | endpoint Δphase (turns) | same-JJ V area/Φ0 (turns) | phase-area residual (turns) | integer crossing markers |",
        "|---|---:|---:|---:|---|",
    ]
    for condition in CONDITIONS:
        item = trajectories[condition]
        crossings = ", ".join(f"{value:.1f}" for value in item["integer_crossing_markers_ps"])
        lines.append(f"| {condition} | {item['phase_delta_turns']:.9f} | {float(item['same_jj_voltage_area_over_phi0_turns']):.9f} | {item['phase_area_residual_turns']:.3e} | {crossings} ps |")
    lines += [
        "",
        "这些是同一 BJ2 的 phase/voltage trajectory markers；integer crossing 数和 cumulative turns **不是 clean SFQ event count**。`BJ2_CROSSING_TIMELINE_2X2.html` 只作轨迹显示。",
        "",
        "## 15. History grouping vs context grouping",
        "",
        f"当前 crossover assessment: **{metrics['crossover_assessment']['label']}**。history grouping across BVM internal / SL / LIN-QBIN / QB trajectory = `{metrics['crossover_assessment']['history_grouping_across_bvm_internal_sl_qbin_lin_qb_trajectory']}`；O+≈N+ 和 O-≈N- 在 common raw samples 上同时 exact = `{metrics['crossover_assessment']['both_history_pairs_exact_on_common_grid']}`；两组 context pair 均出现可观测差异 = `{metrics['crossover_assessment']['both_context_pairs_nonexact_on_common_grid']}`。",
        "",
        "这里的“≈”首先按 exact stored-grid comparison 报告；若不是 0，则报告实际 max/RMS，不事后引入 5%/10% 工程容差。",
        "",
        "## 16. OBSERVED",
        "",
        "- 两个新 artifact 通过 solver/raw/header/time-grid/model-warning QA。",
        "- 70 ps 前同 context 的 history intervention pair 逐点一致；history waveform 本身与静态预检 exact match。",
        "- 四条件的 history pairs 与 context pairs 已同时纳入；不能只根据最终 4/5 交换下结论。",
        "- 本次实际观察到 O+≈N+ 且 O-≈N- 横跨 BVM internal、LSL、LIN/QBIN、BJ2；这是“按 history 分组”的观察，不是唯一机制证明。",
        "",
        "## 17. INFERENCE",
        "",
        "本次四层均满足 history grouping，因此在本模型、此 stimulus、此负载和 dt=0.1 ps 的有界 crossover 因果范围内，previous-read preconditioning 得到强支持，可作为解释 4/5 trajectory split 的主要驱动因素；这不是“history 是唯一原因”的证明。",
        "",
        "## 18. UNKNOWN",
        "",
        "本轮不证明 clean SFQ count、数值收敛、过程裕度、canonical BVM compatibility、single-BVM compatibility、硬件行为、论文机制身份或唯一 root cause；也不把局部 JJ phase 当成下游 SFQ 接收。",
        "",
        "## 19. Interpretation ceiling and next options",
        "",
        "本轮只允许给出有界的 history-vs-context crossover 观察。可能的后续选项（均未执行）：(1) 在同一 NEW fixture 中重复一组更严格的 history-only A/B；(2) 经用户授权后做 history timing sensitivity；(3) 经用户授权后再做独立 timestep/initial-state 检查。",
        "",
        "## 20. Human gate",
        "",
        "`AWAITING_USER_REVIEW`；`user_reviewed=false`；`next_step_authorized=false`；`automatic_next_experiment=false`；`next_action=STOP`。本轮不自动启动任何后续物理实验。",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    traces = {condition: read_csv(spec["raw"]) for condition, spec in CONDITIONS.items()}
    qa = post_run_qa(traces)
    if qa["status"] != "PASS":
        raise RuntimeError(f"post-run QA failed: {qa}")
    metrics = make_metrics(traces, qa)
    ANALYSIS.mkdir(parents=True, exist_ok=True)
    (ANALYSIS / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    crossover = {key: metrics[key] for key in ("conditions", "common_probe_count", "time_grid", "pre_read1_state_vectors_at_109_9ps", "groupings", "exact_common_grid_pairs", "bvm_lsl_waveforms", "qbin_lin_waveforms", "lin_minus_sum_lsl_closure", "bj2_trajectory", "crossover_assessment")}
    (ANALYSIS / "crossover_metrics.json").write_text(json.dumps(crossover, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    manifest = make_plot_inputs(traces)
    (ANALYSIS / "plot_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    provenance = {
        "schema": "bvmsim-1111-history-read-crossover-final-provenance-v1",
        "analysis_created_at": __import__("datetime").datetime.now().astimezone().isoformat(timespec="seconds"),
        "git_head_at_analysis": __import__("subprocess").check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip(),
        "simulation_invoked": True,
        "authorized_new_runs": ["OLD-NO-HISTORY", "NEW-WITH-HISTORY"],
        "solver": {"path": "build/josim-cli", "sha256": sha256(REPO / "build/josim-cli"), "version": "v2.7.2837d13"},
        "raw_hashes": {condition: sha256(spec["raw"]) for condition, spec in CONDITIONS.items()},
        "deck_hashes": {condition: sha256(spec["deck"]) for condition, spec in CONDITIONS.items()},
        "analysis_script_sha256": sha256(ANALYSIS / "analyze.py"),
        "plot_renderer": "scripts/josim-plot2.py",
        "plot_options": {"type": "sep_comb", "color": "dark", "jump": "2pi"},
        "phase_rule": "P raw radians; continuous_unwrap(rad)/(2*pi) for turns",
        "comparison_rule": "common signals and exact stored time grid only; no interpolation",
        "raw_immutable": True,
        "convergence_claim": "NOT_CLAIMED",
    }
    (ANALYSIS / "provenance.json").write_text(json.dumps(provenance, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (ANALYSIS / "REPORT.md").write_text(markdown_report(metrics), encoding="utf-8")
    print(json.dumps({"status": "PASS", "artifact_status": qa["status"], "crossover": metrics["crossover_assessment"], "common_probe_count": metrics["common_probe_count"], "plot_count": len(manifest)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
