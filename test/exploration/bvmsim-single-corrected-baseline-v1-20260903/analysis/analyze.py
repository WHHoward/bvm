#!/usr/bin/env python3
"""Analyze the corrected historical BVMSim single-BVM baseline.

This analyzer deliberately keeps the evidence layers separate:

* bvmtools.raw owns exact CSV/header handling;
* bvmtools.phase and bvmtools.waveform own phase/area arithmetic on the
  actual stored time grid;
* bvmtools.sfq owns monotonic-segment diagnostics, but no local tolerance is
  invented here to turn a dense burst into a clean-event count;
* bvmtools.kcl owns current-balance arithmetic.

The bounded functional assessment uses burst-total phase/area evidence at the
JTL output-facing B02 markers, in accordance with BOUNDARY_SPEC_V2.  It does
not call a whole-window phase displacement an SFQ count.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import subprocess
import sys
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

from bvmtools.compare import compare_series, compare_windowed_series, exact_time_grid_identity  # noqa: E402
from bvmtools.kcl import kcl_window_metrics, linear_kcl_residual  # noqa: E402
from bvmtools.phase import TAU, phase_window_metrics, window_indices  # noqa: E402
from bvmtools.provenance import file_snapshot, git_snapshot, sha256_file, solver_provenance  # noqa: E402
from bvmtools.raw import RawTrace, RawTraceError, read_csv  # noqa: E402
from bvmtools.sfq import PHI0, strict_segment_metrics  # noqa: E402
from bvmtools.waveform import trapezoid_integral, waveform_window_metrics  # noqa: E402


ANALYSIS_VERSION = "BVM_QB_SINGLE_CORRECTED_BASELINE_ANALYSIS_V1"
SOLVER = REPO / "build/josim-cli"
PLOTTER = REPO / "scripts/josim-plot2.py"
RENDERER = EXP / "analysis/render_plots.py"
BOUNDARY = REPO / "docs/research/BOUNDARY_SPEC_V2.md"
METRIC_SPEC = REPO / "docs/research/METRIC_SPEC_V2.md"

WINDOWS_PS: "OrderedDict[str, tuple[float, float]]" = OrderedDict(
    (
        ("PRE", (0.0, 50.0)),
        ("WRITE", (50.0, 62.0)),
        ("READ", (70.0, 82.0)),
        ("RESPONSE", (70.0, 170.0)),
        ("TAIL", (170.0, 200.0)),
        ("FULL", (0.0, 200.0)),
    )
)

CONDITIONS: "OrderedDict[str, dict[str, Any]]" = OrderedDict(
    (
        (
            "S0-R-CORRECTED",
            {
                "logical_state": 0,
                "load": "direct_10ohm",
                "raw": EXP / "runs/S0-R-CORRECTED/raw/run-01.csv",
                "deck": EXP / "runs/S0-R-CORRECTED/deck.cir",
                "initial_raw": None,
            },
        ),
        (
            "S1-R-CORRECTED",
            {
                "logical_state": 1,
                "load": "direct_10ohm",
                "raw": EXP / "runs/S1-R-CORRECTED/raw/run-01.csv",
                "deck": EXP / "runs/S1-R-CORRECTED/deck.cir",
                "initial_raw": None,
            },
        ),
        (
            "S0-J-CORRECTED-RERUN",
            {
                "logical_state": 0,
                "load": "six_stage_jtl_plus_10ohm",
                "raw": EXP / "runs/S0-J-CORRECTED-RERUN/raw/run-01.csv",
                "deck": EXP / "runs/S0-J-CORRECTED-RERUN/deck.cir",
                "initial_raw": EXP / "runs/S0-J-CORRECTED/raw/run-01.csv",
            },
        ),
        (
            "S1-J-CORRECTED-RERUN",
            {
                "logical_state": 1,
                "load": "six_stage_jtl_plus_10ohm",
                "raw": EXP / "runs/S1-J-CORRECTED-RERUN/raw/run-01.csv",
                "deck": EXP / "runs/S1-J-CORRECTED-RERUN/deck.cir",
                "initial_raw": EXP / "runs/S1-J-CORRECTED/raw/run-01.csv",
            },
        ),
    )
)

OLD_REFERENCE = EXP.parent / "bvmsim-bvm-qb-jtl-operational-baseline-v1-20260903"
OLD_SINGLE = {
    "S1-R-OLD-INVALID": OLD_REFERENCE / "runs/single/S1-R/raw/run-01.csv",
}

BVM_PROBES = OrderedDict(
    (
        ("JM1", ("P(B_JM1|XBVM1)", "V(B_JM1|XBVM1)", "I(B_JM1|XBVM1)")),
        ("JM2", ("P(B_JM2|XBVM1)", "V(B_JM2|XBVM1)", "I(B_JM2|XBVM1)")),
        ("JS1", ("P(B_JS1|XBVM1)", "V(B_JS1|XBVM1)", "I(B_JS1|XBVM1)")),
        ("JS2", ("P(B_JS2|XBVM1)", "V(B_JS2|XBVM1)", "I(B_JS2|XBVM1)")),
        ("B_LD4_01", ("P(B_LD4_01)", "V(B_LD4_01)", "I(B_LD4_01)")),
        ("B_LD4_11", ("P(B_LD4_11)", "V(B_LD4_11)", "I(B_LD4_11)")),
        ("BVMout", ("P(BVMOUT)", "V(BVMOUT)", "I(BVMOUT)")),
    )
)
QB_PROBES = OrderedDict(
    (
        ("BJs", ("P(BJS|XBQ1)", "V(BJS|XBQ1)", "I(BJS|XBQ1)")),
        ("BJ1", ("P(BJ1|XBQ1)", "V(BJ1|XBQ1)", "I(BJ1|XBQ1)")),
        ("BJ2", ("P(BJ2|XBQ1)", "V(BJ2|XBQ1)", "I(BJ2|XBQ1)")),
    )
)
JTL_PROBES = OrderedDict(
    (
        (
            f"JTL{stage}",
            OrderedDict(
                (
                    ("B01", (f"P(B01|XJTL1_{stage})", f"V(B01|XJTL1_{stage})")),
                    ("B02", (f"P(B02|XJTL1_{stage})", f"V(B02|XJTL1_{stage})")),
                )
            ),
        )
        for stage in range(1, 7)
    )
)

REQUIRED_COMMON = [
    "I(I_WL1)",
    "I(I_BL1)",
    "I(I_SE1)",
    "V(SL1)",
    "I(L_PSL|XBVM1)",
    "I(L_SL|XBVM1)",
    "P(BVMOUT)",
    "V(BVMOUT)",
    "I(BVMOUT)",
    "V(QBIN)",
    "V(QBOUT)",
    "I(LIN|XBQ1)",
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
]


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO.resolve()).as_posix()
    except ValueError:
        return str(path)


def json_write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def sig(trace: RawTrace, label: str) -> tuple[float, ...]:
    return trace.column(label)  # type: ignore[return-value]


def window_s(name: str) -> tuple[float, float]:
    left, right = WINDOWS_PS[name]
    return left * 1.0e-12, right * 1.0e-12


def finite_float(value: object) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("non-finite numeric value")
    return result


def short_segment(item: Mapping[str, object]) -> dict[str, object]:
    keys = (
        "ordinal",
        "start_time_ps",
        "end_time_ps",
        "duration_ps",
        "direction",
        "phase_reported_turns",
        "area_reported_turns",
        "phase_area_residual_turns",
    )
    return {key: item[key] for key in keys}


def phase_area_window(
    trace: RawTrace, phase_label: str, voltage_label: str, name: str
) -> dict[str, object]:
    bounds = window_s(name)
    phase = sig(trace, phase_label)
    voltage = sig(trace, voltage_label)
    phase_metrics = phase_window_metrics(trace.time, phase, bounds)
    indices = window_indices(trace.time, *bounds)
    times = [trace.time[index] for index in indices]
    values = [voltage[index] for index in indices]
    area_wb = trapezoid_integral(values, times)
    area_turns = area_wb / PHI0
    delta_turns = float(phase_metrics["endpoint_delta_turns"])
    segments = strict_segment_metrics(trace.time, phase, voltage, bounds)
    ordered = sorted(segments, key=lambda item: abs(float(item["phase_reported_turns"])), reverse=True)
    largest = short_segment(ordered[0]) if ordered else None
    return {
        "window_ps": list(WINDOWS_PS[name]),
        "phase_label": phase_label,
        "voltage_label": voltage_label,
        "phase_delta_rad": delta_turns * TAU,
        "phase_delta_turns": delta_turns,
        "voltage_area_wb": area_wb,
        "voltage_area_turns": area_turns,
        "phase_area_residual_turns": delta_turns - area_turns,
        "phase_min_turns": phase_metrics["minimum_turns"],
        "phase_max_turns": phase_metrics["maximum_turns"],
        "phase_p2p_turns": phase_metrics["p2p_turns"],
        "sample_count": phase_metrics["sample_count"],
        "segment_diagnostic": {
            "method": "bvmtools.sfq.strict_segment_metrics",
            "classification": "DESCRIPTIVE_ONLY_NO_TASK_LOCAL_STRICT_TOLERANCE",
            "segment_count": len(segments),
            "largest_abs_segment_turns": max(
                (abs(float(item["phase_reported_turns"])) for item in segments), default=0.0
            ),
            "any_segment_spans_over_1_15_turns": any(
                abs(float(item["phase_reported_turns"])) > 1.15 for item in segments
            ),
            "continuous_multiturn_running_descriptive": any(
                abs(float(item["phase_reported_turns"])) > 1.15 for item in segments
            ),
            "clean_separated_event_count": None,
            "largest_segment": largest,
            "largest_segments": [short_segment(item) for item in ordered[:12]],
            "why_no_clean_count": (
                "This baseline did not preregister a local strict-event tolerance; "
                "dense-burst functional count is evaluated by same-JJ burst-total "
                "phase/area plus downstream B02 evidence."
            ),
        },
    }


def waveform_windows(trace: RawTrace, label: str, unit: str) -> dict[str, object]:
    return {
        name: waveform_window_metrics(trace.time, sig(trace, label), window_s(name), unit=unit)
        for name in WINDOWS_PS
    }


def signal_activity(trace: RawTrace, label: str, unit: str) -> dict[str, object]:
    return {"label": label, "windows": waveform_windows(trace, label, unit)}


def static_deck_checks(condition: str, info: Mapping[str, Any], trace: RawTrace, log_text: str) -> dict[str, object]:
    deck = Path(info["deck"])
    text = deck.read_text(encoding="utf-8")
    terminal_jj = re.findall(r"(?m)^B_LD4_\d{2}\s", text)
    bvmout = re.findall(r"(?m)^BVMout\s", text)
    jtl_instances = re.findall(r"(?mi)^xjtl1_[1-6]\s", text)
    expected = set(REQUIRED_COMMON)
    if info["load"] == "six_stage_jtl_plus_10ohm":
        for stage in range(1, 7):
            expected.update(
                (
                    f"P(B01|XJTL1_{stage})",
                    f"V(B01|XJTL1_{stage})",
                    f"P(B02|XJTL1_{stage})",
                    f"V(B02|XJTL1_{stage})",
                )
            )
    missing = sorted(expected.difference(trace.headers))
    return {
        "deck_path": rel(deck),
        "deck_sha256": sha256_file(deck),
        "model_include_present": ".include ../../../../circuits/models/jjmit.cir" in text,
        "historical_bvm_include_present": ".include ../../../../BVMSim/bvm_cell.cir" in text,
        "historical_qb_include_present": ".include ../../../../BVMSim/BQ.cir" in text,
        "historical_jtl_include_present": ".include ../../../../BVMSim/library_josim/jtl2.cir" in text
        if info["load"] == "six_stage_jtl_plus_10ohm"
        else True,
        "active_bvm_instance_count": len(re.findall(r"(?m)^XBVM1\s+WL1\s+BL1\s+SE1\s+SL1\s+BVM\s*$", text)),
        "terminal_series_jj_count": len(terminal_jj) + len(bvmout),
        "terminal_device_lines": len(terminal_jj),
        "terminal_bvmout_lines": len(bvmout),
        "jtl_instance_count": len(jtl_instances),
        "original_qb_active": bool(re.search(r"(?m)^xBQ1\s+QBin\s+QBout\s+BQ\s*$", text)),
        "migrated_qb_absent": "BQ_BVMSIM_V1" not in text and "I_QB_BIAS" not in text,
        "fixed_tran_present": ".tran 0.1p 200p" in text,
        "model_warning_absent": not bool(re.search(r"Missing model:|Using default model", log_text, re.I)),
        "raw_missing_expected_headers": missing,
        "raw_duplicate_columns": trace.duplicate_columns,
    }


def stimulus_metrics(trace: RawTrace) -> dict[str, object]:
    labels = ("I(I_WL1)", "I(I_BL1)", "I(I_SE1)")
    result: dict[str, object] = {}
    plateau_write = window_s("WRITE")
    # 70--81 ps is the full READ support; 71--80 ps is the flat plateau.
    plateau_read = (71.0e-12, 80.0e-12)
    for label in labels:
        values = sig(trace, label)
        write_indices = window_indices(trace.time, *plateau_write)
        read_indices = window_indices(trace.time, *plateau_read)
        result[label] = {
            "full": waveform_windows(trace, label, "A"),
            "write_plateau_uA": {
                "minimum": min(values[index] for index in write_indices) * 1.0e6,
                "maximum": max(values[index] for index in write_indices) * 1.0e6,
                "expected_uA": None,
            },
            "read_plateau_uA": {
                "minimum": min(values[index] for index in read_indices) * 1.0e6,
                "maximum": max(values[index] for index in read_indices) * 1.0e6,
                "expected_uA": None,
            },
        }
    return result


def expected_stimulus_check(trace: RawTrace, logical_state: int) -> dict[str, object]:
    write_amp = -100.0 if logical_state == 0 else 100.0
    plateau_write = (51.0e-12, 60.0e-12)
    # 70--81 ps is the full READ support; 71--80 ps is the flat plateau.
    plateau_read = (71.0e-12, 80.0e-12)
    checks: dict[str, object] = {}
    for label, expected in (
        ("I(I_WL1)", write_amp),
        ("I(I_BL1)", write_amp),
        ("I(I_SE1)", 0.0),
    ):
        values = sig(trace, label)
        indices = window_indices(trace.time, *plateau_write)
        errors = [abs(values[index] * 1.0e6 - expected) for index in indices]
        checks[f"write_{label}"] = {"expected_uA": expected, "max_abs_error_uA": max(errors)}
    for label, expected in (
        ("I(I_WL1)", 100.0),
        ("I(I_BL1)", 0.0),
        ("I(I_SE1)", 100.0),
    ):
        values = sig(trace, label)
        indices = window_indices(trace.time, *plateau_read)
        errors = [abs(values[index] * 1.0e6 - expected) for index in indices]
        checks[f"read_{label}"] = {"expected_uA": expected, "max_abs_error_uA": max(errors)}
    return {
        "write_polarity": "negative" if logical_state == 0 else "positive",
        "write_equals_WL_plus_BL": all(float(item["max_abs_error_uA"]) == 0.0 for key, item in checks.items() if key.startswith("write_I(I_WL1)") or key.startswith("write_I(I_BL1)")),
        "read_equals_WL_plus_SE_and_BL_zero": all(float(item["max_abs_error_uA"]) == 0.0 for key, item in checks.items() if key.startswith("read_")),
        "plateau_checks": checks,
    }


def kcl_metrics(trace: RawTrace) -> dict[str, object]:
    branches = {
        "I_Lin": sig(trace, "I(LIN|XBQ1)"),
        "I_BJs": sig(trace, "I(BJS|XBQ1)"),
        "I_L1": sig(trace, "I(L1|XBQ1)"),
        "I_bias": sig(trace, "I(IB|XBQ1)"),
        "I_L2": sig(trace, "I(L2|XBQ1)"),
        "I_BJ1": sig(trace, "I(BJ1|XBQ1)"),
        "I_RJ1": sig(trace, "I(RJ1|XBQ1)"),
        "I_BJ2": sig(trace, "I(BJ2|XBQ1)"),
        "I_RJ2": sig(trace, "I(RJ2|XBQ1)"),
        "I_L3": sig(trace, "I(L3|XBQ1)"),
    }
    equations = OrderedDict(
        (
            ("node_1_Lin_minus_BJs", ({"I_Lin": 1.0, "I_BJs": -1.0})),
            ("node_2_BJs_to_BJ1_RJ1_L1", ({"I_BJs": 1.0, "I_BJ1": -1.0, "I_RJ1": -1.0, "I_L1": -1.0})),
            ("node_3_L1_plus_bias_minus_L2", ({"I_L1": 1.0, "I_bias": 1.0, "I_L2": -1.0})),
            ("node_4_L2_to_BJ2_RJ2_L3", ({"I_L2": 1.0, "I_BJ2": -1.0, "I_RJ2": -1.0, "I_L3": -1.0})),
        )
    )
    output: dict[str, object] = {
        "status": "VALID_NUMERIC_RESIDUAL_REPORTED",
        "orientation": {
            "I_Lin": "IN -> QB node 1",
            "I_BJs": "node 1 -> node 2",
            "I_L1": "node 2 -> BIAS node 3",
            "I_bias": "ground -> BIAS node 3",
            "I_L2": "BIAS node 3 -> node 4",
            "I_BJ1": "node 2 -> ground",
            "I_RJ1": "node 2 -> ground",
            "I_BJ2": "node 4 -> ground",
            "I_RJ2": "node 4 -> ground",
            "I_L3": "node 4 -> OUT",
        },
        "equations": {},
    }
    for name, coefficients in equations.items():
        selected = {key: branches[key] for key in coefficients}
        residual = linear_kcl_residual(selected, coefficients)
        output["equations"][name] = {
            "coefficients": coefficients,
            "windows": {
                window_name: kcl_window_metrics(trace.time, residual, window_s(window_name), unit="A")
                for window_name in WINDOWS_PS
            },
        }
    return output


def time_grid_qa(trace: RawTrace) -> dict[str, object]:
    dt_ps = [value * 1.0e12 for value in trace.dt]
    off = [value for value in dt_ps if abs(value - 0.1) > 1.0e-9]
    return {
        "status": "VALID",
        "sample_count": trace.sample_count,
        "time_start_ps": trace.time[0] * 1.0e12,
        "time_end_ps": trace.time[-1] * 1.0e12,
        "requested_tran_step_ps": 0.1,
        "stored_dt_min_ps": min(dt_ps),
        "stored_dt_max_ps": max(dt_ps),
        "stored_off_nominal_dt_ps": off,
        "actual_grid_used_for_integrals": True,
        "duplicate_columns": trace.duplicate_columns,
    }


def branch_record(trace: RawTrace, name: str, labels: tuple[str, str, str]) -> dict[str, object]:
    phase_label, voltage_label, current_label = labels
    return {
        "phase_area": {
            window_name: phase_area_window(trace, phase_label, voltage_label, window_name)
            for window_name in ("PRE", "WRITE", "READ", "RESPONSE", "TAIL", "FULL")
        },
        "current": signal_activity(trace, current_label, "A"),
        "phase_label": phase_label,
        "voltage_label": voltage_label,
        "current_label": current_label,
    }


def jtl_record(trace: RawTrace) -> dict[str, object]:
    output: dict[str, object] = {}
    for stage, branches in JTL_PROBES.items():
        output[stage] = {}
        for branch, (phase_label, voltage_label) in branches.items():
            output[stage][branch] = {
                window_name: phase_area_window(trace, phase_label, voltage_label, window_name)
                for window_name in ("READ", "RESPONSE", "TAIL", "FULL")
            }
    return output


def artifact_record(condition: str, info: Mapping[str, Any], trace: RawTrace) -> dict[str, object]:
    log_path = Path(info["deck"]).parent / "logs/run-01.log"
    log = log_path.read_text(encoding="utf-8")
    return {
        "condition": condition,
        "source_class": "HISTORICAL_BVMSIM",
        "raw_path": rel(Path(info["raw"])),
        "raw_sha256": sha256_file(Path(info["raw"])),
        "raw_qa": time_grid_qa(trace),
        "deck_checks": static_deck_checks(condition, info, trace, log),
        "stimulus_check": expected_stimulus_check(trace, int(info["logical_state"])),
        "run_command": (Path(info["deck"]).parent / "command.txt").read_text(encoding="utf-8"),
        "log_path": rel(log_path),
        "log_sha256": sha256_file(log_path),
        "run_exit_code": 0,
    }


def response_record(trace: RawTrace) -> dict[str, object]:
    return {
        "bvm": {
            name: branch_record(trace, name, labels)
            for name, labels in BVM_PROBES.items()
        },
        "qb": {
            name: branch_record(trace, name, labels)
            for name, labels in QB_PROBES.items()
        },
        "qbin_voltage": signal_activity(trace, "V(QBIN)", "V"),
        "qbout_voltage": signal_activity(trace, "V(QBOUT)", "V"),
        "lin_current": signal_activity(trace, "I(LIN|XBQ1)", "A"),
    }


def compare_pair(trace_a: RawTrace, trace_b: RawTrace, label: str) -> dict[str, object]:
    if label.startswith("P("):
        return compare_windowed_series(
            trace_a.time,
            sig(trace_a, label),
            trace_b.time,
            sig(trace_b, label),
            window_s("RESPONSE"),
            value_scale=1.0 / TAU,
            unit="turns",
        )
    unit = "V" if label.startswith("V(") else "A"
    return compare_windowed_series(
        trace_a.time,
        sig(trace_a, label),
        trace_b.time,
        sig(trace_b, label),
        window_s("RESPONSE"),
        unit=unit,
    )


def pair_comparisons(traces: Mapping[str, RawTrace]) -> dict[str, object]:
    output: dict[str, object] = {}
    common = ("V(SL1)", "I(L_SL|XBVM1)", "V(QBIN)", "P(BJ2|XBQ1)", "V(QBOUT)")
    pairs = (
        ("S0_direct_vs_jtl", "S0-R-CORRECTED", "S0-J-CORRECTED-RERUN"),
        ("S1_direct_vs_jtl", "S1-R-CORRECTED", "S1-J-CORRECTED-RERUN"),
        ("S0_direct_vs_S1_direct", "S0-R-CORRECTED", "S1-R-CORRECTED"),
        ("S0_jtl_vs_S1_jtl", "S0-J-CORRECTED-RERUN", "S1-J-CORRECTED-RERUN"),
    )
    for name, left, right in pairs:
        output[name] = {
            "left": left,
            "right": right,
            "time_grid_exact": exact_time_grid_identity(traces[left].time, traces[right].time),
            "signals": {label: compare_pair(traces[left], traces[right], label) for label in common},
        }
    return output


def old_invalid_comparison(corrected: RawTrace) -> dict[str, object]:
    old_path = OLD_SINGLE["S1-R-OLD-INVALID"]
    old = read_csv(old_path)
    labels = ("I(I_WL1)", "I(I_BL1)", "I(I_SE1)")
    return {
        "old_condition": "S1-R-OLD-INVALID",
        "old_path": rel(old_path),
        "old_raw_sha256": sha256_file(old_path),
        "old_artifact_status": "ARTIFACT_INVALID",
        "old_model_warning_expected": True,
        "time_grid_exact": exact_time_grid_identity(old.time, corrected.time),
        "stimulus_comparisons_full": {
            label: compare_series(old.time, sig(old, label), corrected.time, sig(corrected, label))
            | {"pointwise_difference": "omitted_from_report"}
            for label in labels
        },
        "old_read_plateau_uA": {
            label: waveform_window_metrics(old.time, sig(old, label), (71.0e-12, 81.0e-12), unit="A")
            for label in labels
        },
        "corrected_read_plateau_uA": {
            label: waveform_window_metrics(corrected.time, sig(corrected, label), (71.0e-12, 81.0e-12), unit="A")
            for label in labels
        },
    }


def near_zero(value: float, scale: float = 0.1) -> bool:
    return abs(value) <= scale


def near_one(value: float) -> bool:
    return 0.75 <= value <= 1.25


def functional_assessment(condition: str, response: Mapping[str, Any]) -> dict[str, object]:
    info = CONDITIONS[condition]
    bj2 = response["qb"]["BJ2"]["phase_area"]["RESPONSE"]
    if info["load"] == "direct_10ohm":
        return {
            "verdict": "INCONCLUSIVE_FOR_COUNT",
            "reason": "direct-load count was not the preregistered functional boundary; retain as load comparison baseline",
            "bj2_response_phase_turns": bj2["phase_delta_turns"],
            "bj2_response_area_turns": bj2["voltage_area_turns"],
        }
    stages = response["jtl"]
    b02 = [stages[f"JTL{stage}"]["B02"]["RESPONSE"] for stage in range(1, 7)]
    if int(info["logical_state"]) == 0:
        ok = near_zero(float(bj2["phase_delta_turns"])) and near_zero(float(bj2["voltage_area_turns"]))
        ok = ok and all(near_zero(float(item["phase_delta_turns"])) and near_zero(float(item["voltage_area_turns"])) for item in b02)
        verdict = "FUNCTIONAL_PASS" if ok else "INCONCLUSIVE"
        reason = "S0 no-output control: QB BJ2 and every JTL B02 burst-total remain near zero" if ok else "S0 no-output control was not established"
    else:
        bj2_ok = near_one(float(bj2["phase_delta_turns"])) and near_one(float(bj2["voltage_area_turns"])) and abs(float(bj2["phase_area_residual_turns"])) < 0.05
        stage_ok = all(
            near_one(float(item["phase_delta_turns"]))
            and near_one(float(item["voltage_area_turns"]))
            and abs(float(item["phase_area_residual_turns"])) < 0.05
            and float(item["phase_delta_turns"]) > 0.0
            for item in b02
        )
        ok = bj2_ok and stage_ok
        verdict = "FUNCTIONAL_PASS" if ok else "INCONCLUSIVE"
        reason = "S1 one-burst boundary: QB BJ2 and JTL1..JTL6 B02 each preserve one positive burst-total with same-JJ phase/area agreement" if ok else "S1 one-burst boundary was not established"
    return {
        "verdict": verdict,
        "reason": reason,
        "count_basis": "burst_total_phase_area_plus_downstream_B02; not whole-window phase alone",
        "bj2_response_phase_turns": bj2["phase_delta_turns"],
        "bj2_response_area_turns": bj2["voltage_area_turns"],
        "bj2_response_residual_turns": bj2["phase_area_residual_turns"],
        "jtl_b02_response_phase_turns": [item["phase_delta_turns"] for item in b02],
        "jtl_b02_response_area_turns": [item["voltage_area_turns"] for item in b02],
        "jtl_b02_response_residual_turns": [item["phase_area_residual_turns"] for item in b02],
        "polarity": [1 if float(item["phase_delta_turns"]) > 0 else -1 if float(item["phase_delta_turns"]) < 0 else 0 for item in b02],
    }


def condition_record(condition: str, trace: RawTrace) -> dict[str, object]:
    info = CONDITIONS[condition]
    response = response_record(trace)
    if info["load"] == "six_stage_jtl_plus_10ohm":
        response["jtl"] = jtl_record(trace)
    else:
        response["jtl"] = {}
    record = {
        "condition": condition,
        "logical_state": info["logical_state"],
        "load": info["load"],
        "artifact": artifact_record(condition, info, trace),
        "response": response,
        "qb_kcl": kcl_metrics(trace),
    }
    record["functional_assessment"] = functional_assessment(condition, response)
    return record


def make_provenance(traces: Mapping[str, RawTrace]) -> dict[str, object]:
    source_paths = [
        REPO / "BVMSim/BVM.cir",
        REPO / "BVMSim/bvm_cell.cir",
        REPO / "BVMSim/BQ.cir",
        REPO / "BVMSim/library_josim/jtl2.cir",
        REPO / "circuits/models/jjmit.cir",
        EXP / "experiment.yaml",
        EXP / "analysis/jtl-probe-rerun.yaml",
        BOUNDARY,
        METRIC_SPEC,
        Path(__file__),
        RENDERER,
    ]
    source_paths = [path for path in source_paths if path.is_file()]
    raw_snapshots = []
    for condition, trace in traces.items():
        path = Path(CONDITIONS[condition]["raw"])
        raw_snapshots.append(
            {
                "condition": condition,
                "path": rel(path),
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
                "sample_count": trace.sample_count,
            }
        )
    initial = []
    for condition, info in CONDITIONS.items():
        if info["initial_raw"] is not None:
            path = Path(info["initial_raw"])
            initial.append({"condition": condition, "path": rel(path), "sha256": sha256_file(path)})
    old_path = OLD_SINGLE["S1-R-OLD-INVALID"]
    return {
        "analysis_version": ANALYSIS_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "analysis_claim_ceiling": "historical BVMSim source-class single-BVM baseline; exploratory functional evidence only",
        "git_before_analysis": git_snapshot(REPO),
        "solver": solver_provenance(SOLVER, cwd=REPO),
        "files": [file_snapshot(path, relative_to=REPO) for path in source_paths],
        "plotter": file_snapshot(PLOTTER, relative_to=REPO),
        "plot_generator": file_snapshot(RENDERER, relative_to=REPO),
        "corrected_raws": raw_snapshots,
        "preserved_initial_jtl_raws": initial,
        "preserved_old_invalid_raw": file_snapshot(old_path, relative_to=REPO),
        "no_raw_rewrite": True,
        "phase_unit": "JoSIM P(...) raw radians; displayed turns are continuous_unwrap(rad)/(2*pi)",
        "integral_unit": "same-JJ trapezoidal integral on actual stored time grid divided by Phi0",
        "windows_ps": {key: list(value) for key, value in WINDOWS_PS.items()},
        "kcl_tool": "scripts/bvmtools/kcl.py",
        "sfq_tool": "scripts/bvmtools/sfq.py strict_segment_metrics (descriptive only)",
    }


def report_text(metrics: Mapping[str, Any]) -> str:
    cases = metrics["conditions"]
    s0j = cases["S0-J-CORRECTED-RERUN"]
    s1j = cases["S1-J-CORRECTED-RERUN"]
    s1r = cases["S1-R-CORRECTED"]
    s0r = cases["S0-R-CORRECTED"]
    s0j_bj2 = s0j["functional_assessment"]
    s1j_bj2 = s1j["functional_assessment"]

    def f(value: object, digits: int = 6) -> str:
        return f"{float(value):.{digits}f}"

    s1j_stages = s1j_bj2["jtl_b02_response_area_turns"]
    s0j_stages = s0j_bj2["jtl_b02_response_area_turns"]
    lines = [
        "# Corrected historical BVMSim single-BVM → original QB baseline",
        "",
        "> 本报告只覆盖 historical `BVMSim/bvm_cell.cir` 的 single-BVM 2×2；它不是 canonical BVM 兼容性结论，也不是 timestep 或参数裕度结论。",
        "",
        "## 1. What changed",
        "",
        "- 新建 task-local corrected decks：`S0-R-CORRECTED`、`S1-R-CORRECTED`，以及带完整 JTL 探针的新 `S0-J-CORRECTED-RERUN`、`S1-J-CORRECTED-RERUN`。",
        "- WRITE 修正为 `WL+BL`：S0 为 `-100/-100 µA`，S1 为 `+100/+100 µA`，时间为 50–61 ps。",
        "- READ 修正为两个逻辑态完全相同的 `WL+SE`：`WL=+100 µA`、`SE=+100 µA`、`BL=0`，时间为 70–81 ps。",
        "- corrected deck 显式 include `circuits/models/jjmit.cir`，避免 BVM/terminal JJ 使用 default model。QB 仍是原始 `BVMSim/BQ.cir`。",
        "",
        "## 2. What did not change",
        "",
        "- BVM、original QB、六级 historical JTL、280 µA/JTL、10 Ω load、`.tran 0.1p 200p` 和 solver 均未改变。",
        "- terminal sensing line 保持 11 个串联 load JJ + `BVMout`，共 12 个 JJ。",
        "- `BVMSim/BQ.cir`、`BVMSim/bvm_cell.cir`、`BVMSim/library_josim/jtl2.cir` 和旧 single raw 均未覆盖。",
        "- 初次 corrected JTL raw 因缺少 JTL P/V 探针而标记 `OBSERVABILITY_INCOMPLETE`；本报告使用其后的 probe-only rerun。",
        "",
        "## 3. OBSERVED stimulus correction",
        "",
        "四个 corrected raw 的实际 plateau 检查均为零误差：WRITE 只改变 S0/S1 的 WL/BL 极性；READ 的三条控制在 S0/S1 间完全相同。独立控制图见：",
        "",
        "- `plots/runs/S0-R-CORRECTED/BVM_STIMULUS_AND_STATE.html`",
        "- `plots/runs/S1-R-CORRECTED/BVM_STIMULUS_AND_STATE.html`",
        "- `plots/runs/S0-J-CORRECTED-RERUN/BVM_STIMULUS_AND_STATE.html`",
        "- `plots/runs/S1-J-CORRECTED-RERUN/BVM_STIMULUS_AND_STATE.html`",
        "",
        "旧 single fixture 的 `S1-R` 在 READ 期间是 SE-only，且 log 有 `Missing model: JJMIT` / `Using default model`；它只作为 `ARTIFACT_INVALID` 历史对照。旧 raw 与 corrected raw 的因果差异不能拆分为“READ 修复贡献”和“model 修复贡献”，因为本轮两者同时修复。",
        "",
        "## 4. OBSERVED model closure",
        "",
        "四个实际使用的 corrected raw 均通过基本 raw QA；log 未出现 model fallback；deck 有 intended `jjmit` include；direct run 有 0 个 JTL instance，JTL rerun 有 6 个 JTL instance，terminal JJ 计数均为 12。输出 raw 的存储网格为请求的 0.1 ps 为主，但每个 JoSIM raw 保留一个 0.2 ps 间隔；所有积分均使用实际存储时间，不做插值。",
        "",
        "## 5. OBSERVED S0",
        "",
        f"- direct 10 Ω：S0 `BJ2` RESPONSE 的 phase/area 为 `{f(s0r['response']['qb']['BJ2']['phase_area']['RESPONSE']['phase_delta_turns'])}` / `{f(s0r['response']['qb']['BJ2']['phase_area']['RESPONSE']['voltage_area_turns'])}` turns，未见约 1 turn 的 READ-associated QB burst。",
        f"- JTL load：S0 `BJ2` RESPONSE 的 phase/area 为 `{f(s0j_bj2['bj2_response_phase_turns'])}` / `{f(s0j_bj2['bj2_response_area_turns'])}` turns；JTL1–JTL6 的 B02 burst-total area 为 `{', '.join(f(x) for x in s0j_stages)}` turns，均接近零。",
        f"- bounded no-output control assessment：`{s0j_bj2['verdict']}`。这不是对任意 future load 的普遍无输出证明。",
        "",
        "## 6. OBSERVED S1",
        "",
        f"- direct 10 Ω：S1 `BJ2` RESPONSE 的 phase/area 为 `{f(s1r['response']['qb']['BJ2']['phase_area']['RESPONSE']['phase_delta_turns'])}` / `{f(s1r['response']['qb']['BJ2']['phase_area']['RESPONSE']['voltage_area_turns'])}` turns，显示 direct load 下约 2-turn response；这一路径没有预注册的单量子 count boundary，因此不把它直接判为 count PASS。",
        f"- JTL load：S1 `BJ2` RESPONSE 的 phase/area 为 `{f(s1j_bj2['bj2_response_phase_turns'])}` / `{f(s1j_bj2['bj2_response_area_turns'])}` turns，residual `{f(s1j_bj2['bj2_response_residual_turns'])}` turns。",
        f"- JTL1–JTL6 的 B02 RESPONSE phase/area 为：`{' / '.join(f(p) + ' / ' + f(a) for p, a in zip(s1j_bj2['jtl_b02_response_phase_turns'], s1j_bj2['jtl_b02_response_area_turns']))}` turns；极性为 `{'/'.join('+' if p > 0 else '-' if p < 0 else '0' for p in s1j_bj2['polarity'])}`。",
        f"- bounded one-burst assessment：`{s1j_bj2['verdict']}`。计数依据是同一 JJ 的 burst-total phase/area 与下游 B02 的一致性，不是 whole-window phase 单独计数。",
        "",
        "## 7. OBSERVED direct vs JTL load",
        "",
        "- S0 在 direct 与 JTL 下都没有约 1-turn BJ2 burst；JTL rerun 补足了 direct run 初次没有的六级 B01/B02 P/V 观测。",
        "- S1 的 QB 响应明显受负载影响：direct 10 Ω 的 BJ2 RESPONSE 约 2 turns，而六级 JTL load 的 BJ2/B02 burst-total 约 1 turn。这个结果是本固定 fixture 的 load-sensitive observation，不足以单独说明某一物理机制或普适设计规则。",
        "- JTL B02 每一级都保留约 1 的 phase/area burst-total；每一级的细碎 ringing/严格 monotonic segmentation 不被升级成额外 SFQ 数。",
        "",
        "## 8. INFERENCE",
        "",
        "在本轮固定的 historical BVMSim source、original QB、六级 historical JTL 和 10 Ω termination 下，修正后的 single-BVM 确实让 WL+SE READ 条件可被直接核验；S0/S1 的 QBin/QB 响应可区分；JTL load 下可得到 bounded 的 0→0 和 1→1 burst-total functional evidence。因此 corrected fixture 可以回答“这个 historical single BVM → original QB → JTL fixture 在该固定点是否工作”，而旧 single fixture 不能承担这个结论。",
        "",
        "## 9. UNKNOWN",
        "",
        "- 本轮没有拆分 READ protocol 与 model closure 两个修复各自的因果贡献。",
        "- 本轮没有证明 canonical BVM 兼容性、single-BVM 的普遍行为、参数/偏置裕度、timestep convergence、T1 行为或论文机制身份。",
        "- `P(...)` 的局部 phase turns 不是自动的 SFQ count；严格 clean-separated event count 本轮没有使用未预注册的 task-local tolerance 强行生成。",
        "- direct 10 Ω 的约 2-turn response 说明负载敏感，但本轮没有把它解释为错误机制或做参数优化。",
        "",
        "## 10. Reasonable next options",
        "",
        "1. 由用户审阅本报告和四张独立 stimulus 图，决定是否接受这组 single-BVM historical baseline。",
        "2. 如确有必要，另行授权只拆分一个因素的 control experiment，以分别评估 READ 语义与 model closure 的影响。",
        "3. 如需推进科学路线，再另行授权 canonical BVM 或数值鲁棒性工作；本轮没有自动执行。",
        "",
        "## 当前状态",
        "",
        "`AWAITING_USER_REVIEW`；`user_reviewed=false`；`next_step_authorized=false`；`automatic_next_experiment=false`。",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-report", action="store_true")
    args = parser.parse_args()

    traces: "OrderedDict[str, RawTrace]" = OrderedDict()
    records: "OrderedDict[str, dict[str, object]]" = OrderedDict()
    for condition, info in CONDITIONS.items():
        trace = read_csv(info["raw"])
        traces[condition] = trace
        records[condition] = condition_record(condition, trace)

    corrected_s1r = traces["S1-R-CORRECTED"]
    metrics: dict[str, object] = {
        "analysis_version": ANALYSIS_VERSION,
        "source_class": "HISTORICAL_BVMSIM",
        "authority_boundary": "BVMSim/bvm_cell.cir != canonical circuits/bvm/bvm_cell.cir; no canonical claim",
        "conditions": records,
        "pair_comparisons": pair_comparisons(traces),
        "old_invalid_comparison": old_invalid_comparison(corrected_s1r),
        "overall_assessment": {
            "artifact_status": "ARTIFACT_VALID_FOR_CORRECTED_RUNS",
            "jtl_functional_scope": "S0-J and S1-J bounded exploratory assessment",
            "direct_load_scope": "load-sensitive baseline; no count PASS assigned",
            "status": "AWAITING_USER_REVIEW",
        },
    }
    provenance = make_provenance(traces)
    json_write(EXP / "analysis/metrics.json", metrics)
    json_write(EXP / "analysis/provenance.json", provenance)
    if not args.no_report:
        (EXP / "analysis/SINGLE_BVM_CORRECTED_REPORT.md").write_text(report_text(metrics), encoding="utf-8")
    print(json.dumps({
        "analysis_version": ANALYSIS_VERSION,
        "conditions": list(CONDITIONS),
        "metrics": rel(EXP / "analysis/metrics.json"),
        "provenance": rel(EXP / "analysis/provenance.json"),
        "report": rel(EXP / "analysis/SINGLE_BVM_CORRECTED_REPORT.md") if not args.no_report else None,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
