#!/usr/bin/env python3
"""Per-run strict analysis for the RJ1 x timestep robustness experiment.

This module deliberately keeps four evidence layers separate:

* raw/grid/artifact QA;
* same-junction phase and voltage-area event arithmetic;
* local QB/JTL activity and transport ordering;
* cautious exploratory matrix/protection summaries.

It reuses the repository bvmtools reader, phase arithmetic, strict event list,
waveform integration, comparison helpers, KCL arithmetic, and provenance
helpers.  A net phase displacement is never used as an SFQ event count.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
import sys
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

from bvmtools.kcl import kcl_window_metrics, linear_kcl_residual  # noqa: E402
from bvmtools.phase import TAU, continuous_unwrap, phase_window_metrics, window_indices  # noqa: E402
from bvmtools.provenance import git_snapshot, sha256_file, solver_provenance  # noqa: E402
from bvmtools.raw import RawTrace, read_csv  # noqa: E402
from bvmtools.sfq import PHI0, StrictLocalEventSpec, strict_event_list  # noqa: E402
from bvmtools.waveform import trapezoid_integral, waveform_metrics, waveform_window_metrics  # noqa: E402


SOLVER = REPO / "build/josim-cli"
METRIC_SPEC = REPO / "docs/research/METRIC_SPEC_V2.md"
PLOTTER = REPO / "scripts/josim-plot2.py"
HISTORICAL_BQ = REPO / "BVMSim/BQ.cir"
HISTORICAL_RAW = REPO / "BVMSim/data_tran.csv"
CANONICAL_BVM = REPO / "circuits/bvm/bvm_cell.cir"
HISTORICAL_BVM = REPO / "BVMSim/bvm_cell.cir"
JTL_SOURCE = REPO / "BVMSim/library_josim/jtl2.cir"
SHARED_JJ = REPO / "circuits/models/jjmit.cir"
AUTH_QB = REPO / "circuits/qb/bq_cell_bvmsim_v1.cir"

WINDOWS_PS: "OrderedDict[str, tuple[float, float]]" = OrderedDict(
    (
        ("INITIAL_PRE", (0.0, 50.0)),
        ("WRITE0", (50.0, 70.0)),
        ("READ0", (70.0, 90.0)),
        ("WRITE1", (90.0, 110.0)),
        ("READ1_RESPONSE", (110.0, 170.0)),
        ("TAIL_RESET", (170.0, 200.0)),
    )
)
PROTECTION_READ_PS = (70.0, 82.0)
PROTECTION_POST_PS = (82.0, 200.0)
FULL_PS = (0.0, 200.0)

QB_JUNCTIONS = OrderedDict(
    (
        ("BJs", ("P(BJS|XBQ1)", "V(BJS|XBQ1)", "I(BJS|XBQ1)")),
        ("BJ1", ("P(BJ1|XBQ1)", "V(BJ1|XBQ1)", "I(BJ1|XBQ1)")),
        ("BJ2", ("P(BJ2|XBQ1)", "V(BJ2|XBQ1)", "I(BJ2|XBQ1)")),
    )
)
JTL_JUNCTIONS = OrderedDict(
    (
        (
            f"JTL{stage}",
            OrderedDict(
                (
                    (
                        junction,
                        (
                            f"P({junction}|XJTL1_{stage})",
                            f"V({junction}|XJTL1_{stage})",
                        ),
                    )
                    for junction in ("B01", "B02")
                )
            ),
        )
        for stage in range(1, 7)
    )
)

STRICT_TOLERANCE = {
    "phase_area_residual_abs_floor_turns": 0.05,
    "phase_area_residual_relative": 0.10,
    "complete_min_turns": 1.0,
    "clean_upper_turns": 1.15,
    "post_range_max_turns": 1.0,
    "post_tail_p2p_max_turns": 0.25,
}

# These are deliberately descriptive analysis aids.  They were not frozen as
# acceptance thresholds in experiment.yaml and must never be reported as
# preregistered gates.
DESCRIPTIVE_CANDIDATE_MIN_TURNS = 0.2
DESCRIPTIVE_ONE_PHI0_MIN_TURNS = 0.75
DESCRIPTIVE_ONE_PHI0_MAX_TURNS = 1.25
DESCRIPTIVE_ONE_PHI0_RESIDUAL_MAX_TURNS = 0.20


def sha256(path: Path) -> str:
    return sha256_file(path)


def rel(path: Path) -> str:
    return str(path.resolve().relative_to(REPO.resolve()))


def json_write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def ps(value_s: float) -> float:
    return float(value_s) * 1.0e12


def safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def signal(trace: RawTrace, label: str) -> tuple[float, ...]:
    return trace.column(label)  # type: ignore[return-value]


def window_s(bounds_ps: tuple[float, float]) -> tuple[float, float]:
    return bounds_ps[0] * 1.0e-12, bounds_ps[1] * 1.0e-12


def config_records() -> list[dict[str, Any]]:
    manifest = json.loads((EXP / "analysis/deck_manifest.json").read_text(encoding="utf-8"))
    records: list[dict[str, Any]] = []
    for record in manifest["decks"]:
        run_id = str(record["run_id"])
        if record["family"] == "four_bvm":
            effective_deck = EXP / "runs" / run_id / "attempt-03/deck.cir"
            effective_raw = EXP / "runs" / run_id / "attempt-03/raw/run-01.csv"
            attempt = "attempt-03"
            initial_deck = REPO / record["deck"]
            initial_raw = REPO / record["raw"]
        else:
            effective_deck = REPO / record["deck"]
            effective_raw = REPO / record["raw"]
            attempt = "run-01"
            initial_deck = effective_deck
            initial_raw = effective_raw
        records.append(
            {
                **record,
                "effective_deck": effective_deck,
                "effective_raw": effective_raw,
                "effective_attempt": attempt,
                "initial_deck": initial_deck,
                "initial_raw": initial_raw,
            }
        )
    return records


def required_labels() -> list[str]:
    labels = ["P(BVMOUT)", "V(BVMOUT)", "I(BVMOUT)", "V(QBIN)"]
    labels.extend(
        [
            "P(BJS|XBQ1)", "V(BJS|XBQ1)", "I(BJS|XBQ1)",
            "P(BJ1|XBQ1)", "V(BJ1|XBQ1)", "I(BJ1|XBQ1)",
            "P(BJ2|XBQ1)", "V(BJ2|XBQ1)", "I(BJ2|XBQ1)",
            "V(QBOUT)", "I(RJ1|XBQ1)", "I(RJ2|XBQ1)",
            "I(LIN|XBQ1)", "I(L1|XBQ1)", "I(L2|XBQ1)",
            "I(L3|XBQ1)", "I(I_QB_BIAS)",
        ]
    )
    for stage in range(1, 7):
        for junction in ("B01", "B02"):
            labels.extend((f"P({junction}|XJTL1_{stage})", f"V({junction}|XJTL1_{stage})"))
    return labels


def raw_qa(trace: RawTrace, record: dict[str, Any]) -> dict[str, Any]:
    expected_dt_s = float(record["timestep_ps"]) * 1.0e-12
    dts = [float(value) for value in trace.dt]
    actual_dt_s = statistics.median(dts)
    dt_error_s = max(abs(value - expected_dt_s) for value in dts)
    expected_start_ps = 45.0 if record["family"] == "four_bvm" else 0.0
    dt_ok = math.isclose(actual_dt_s, expected_dt_s, rel_tol=1.0e-9, abs_tol=1.0e-24)
    start_ok = math.isclose(ps(trace.time[0]), expected_start_ps, rel_tol=0.0, abs_tol=1.0e-9)
    stop_ok = trace.time[-1] < 200.0e-12
    return {
        "status": "VALID" if dt_ok and start_ok and stop_ok else "INVALID",
        "reader_qa": trace.qa(),
        "expected_timestep_ps": float(record["timestep_ps"]),
        "actual_timestep_ps_median": ps(actual_dt_s),
        "actual_timestep_ps_min": ps(min(dts)),
        "actual_timestep_ps_max": ps(max(dts)),
        "max_dt_error_s": dt_error_s,
        "time_start_ps": ps(trace.time[0]),
        "time_last_sample_ps": ps(trace.time[-1]),
        "expected_start_ps": expected_start_ps,
        "print_start_semantics": "45 ps four-BVM" if record["family"] == "four_bvm" else "0 ps single-BVM",
        "grid_checks": {
            "uniform_actual_grid": bool(max(dts) == min(dts)),
            "strictly_increasing": True,
            "timestep_matches_deck": dt_ok,
            "start_matches_fixture": start_ok,
            "stop_before_200_ps": stop_ok,
            "interpolation": "none",
        },
    }


def compact_retrap(value: Any) -> Any:
    if not isinstance(value, dict):
        return value
    keep = (
        "kind", "bounded", "start_time_ps", "end_time_ps", "duration_ps",
        "intermediate_segment_count", "intermediate_abs_turns_sum",
        "opposite_direction_retrap", "intermediate_complete_segment",
        "phase_p2p_turns", "next_event_index", "next_event_onset_ps",
        "tail_phase_p2p_turns",
    )
    return {key: value[key] for key in keep if key in value}


def compact_segment(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "ordinal": int(item["ordinal"]),
        "start_index": int(item["start_index"]),
        "end_index": int(item["end_index"]),
        "start_time_ps": float(item["start_time_ps"]),
        "end_time_ps": float(item["end_time_ps"]),
        "duration_ps": float(item["duration_ps"]),
        "direction": int(item["direction"]),
        "phase_delta_rad": float(item["phase_delta_rad"]),
        "phase_turns": float(item["phase_reported_turns"]),
        "voltage_area_wb": float(item["raw_area_wb"]),
        "voltage_area_turns": float(item["area_reported_turns"]),
        "signed_phase_area_residual_turns": float(item["phase_area_residual_turns"]),
        "complete_segment": bool(item["complete_segment"]),
        "clean_band": bool(item["clean_band"]),
        "clean_separated_event": bool(item["clean_separated_event"]),
        "continuous_multiturn_segment": bool(item["continuous_multiturn_segment"]),
        "onset_in_event_window": bool(item["onset_in_event_window"]),
        "event_index": item.get("event_index"),
        "event_window_event_index": item.get("event_window_event_index"),
        "retrap_or_bounded_interval": compact_retrap(item.get("retrap_or_bounded_interval")),
    }


def strict_spec(raw_path: Path, phase_name: str, voltage_name: str, run_id: str) -> StrictLocalEventSpec:
    return StrictLocalEventSpec.from_mapping(
        {
            "id": "bvm-qb-rj1-timestep-robustness-strict-event-v1",
            "scope": "task-local",
            "status": "FROZEN",
            "provenance_status": "PRE_REGISTERED_EXPLORATORY",
            "mapping_status": "DECLARED_DIRECT_SAME_JJ_PV",
            "phase_column": phase_name,
            "voltage_column": voltage_name,
            "branch_endpoints": f"JoSIM direct branch orientation for {phase_name} / {voltage_name}",
            "voltage_to_phase_sign": 1,
            "reporting_direction": 1,
            "run_id": run_id,
            "window_id": "full-trace-onset-association-0-50-70-90-110-170-200ps",
            "raw_sha256": sha256(raw_path),
            "metric_spec": {
                "path": rel(METRIC_SPEC),
                "version": "2.0.0",
                "sha256": sha256(METRIC_SPEC),
            },
            "tolerance": {
                "id": "bvm-qb-rj1-task-local-strict-event-v1",
                "scope": "task-local",
                "status": "FROZEN",
                "provenance_status": "PRE_REGISTERED_EXPLORATORY",
                "evidence": rel(EXP / "experiment.yaml"),
                **STRICT_TOLERANCE,
            },
            "compatibility_profile": "STRICT_EVENT_ANCHOR_COMPATIBILITY_V1",
        }
    )


def phase_window(trace: RawTrace, phase_name: str, bounds: tuple[float, float]) -> dict[str, Any]:
    return phase_window_metrics(trace.time, signal(trace, phase_name), window_s(bounds))


def waveform_window(trace: RawTrace, label: str, bounds: tuple[float, float], unit: str) -> dict[str, Any]:
    return waveform_window_metrics(trace.time, signal(trace, label), window_s(bounds), unit=unit)


def window_segments(event_list: dict[str, Any], bounds: tuple[float, float]) -> list[dict[str, Any]]:
    left, right = bounds
    return [
        item
        for item in event_list["segments"]
        if left <= float(item["start_time_ps"]) < right
    ]


def event_window_summary(
    trace: RawTrace,
    event_list: dict[str, Any],
    phase_name: str,
    voltage_name: str,
    bounds: tuple[float, float],
) -> dict[str, Any]:
    selected = window_segments(event_list, bounds)
    complete = [item for item in selected if bool(item["complete_segment"])]
    clean = [item for item in complete if bool(item["clean_separated_event"])]
    candidate = [
        item
        for item in selected
        if abs(float(item["phase_reported_turns"])) >= DESCRIPTIVE_CANDIDATE_MIN_TURNS
    ]
    return {
        "window_ps": list(bounds),
        "phase_window": phase_window(trace, phase_name, bounds),
        "voltage_window": waveform_window(trace, voltage_name, bounds, "V"),
        "complete_segment_count": len(complete),
        "clean_separated_event_count": len(clean),
        "complete_event_onset_times_ps": [float(item["start_time_ps"]) for item in complete],
        "clean_event_onset_times_ps": [float(item["start_time_ps"]) for item in clean],
        "clean_event_directions": [int(item["direction"]) for item in clean],
        "largest_segment_turns": max((abs(float(item["phase_reported_turns"])) for item in selected), default=0.0),
        "any_segment_spans_over_1_15_turns": any(bool(item["continuous_multiturn_segment"]) for item in selected),
        "continuous_multi_turn_running": any(bool(item["continuous_multiturn_segment"]) for item in selected),
        "descriptive_candidate_threshold": {
            "min_abs_phase_turns": DESCRIPTIVE_CANDIDATE_MIN_TURNS,
            "status": "POST_HOC_DESCRIPTIVE_NOT_PREREGISTERED",
        },
        "candidate_segments": [compact_segment(item) for item in candidate],
        "complete_segments": [compact_segment(item) for item in complete],
        "clean_separated_events": [compact_segment(item) for item in clean],
    }


def junction_analysis(
    trace: RawTrace,
    raw_path: Path,
    run_id: str,
    label: str,
    phase_name: str,
    voltage_name: str,
) -> dict[str, Any]:
    spec = strict_spec(raw_path, phase_name, voltage_name, run_id)
    events = strict_event_list(
        trace.time,
        signal(trace, phase_name),
        signal(trace, voltage_name),
        event_window_s=window_s(FULL_PS),
        scan_window_s=window_s(FULL_PS),
        retrap_max_p2p_turns=float(STRICT_TOLERANCE["post_tail_p2p_max_turns"]),
        spec=spec,
    )
    return {
        "label": label,
        "phase_column": phase_name,
        "voltage_column": voltage_name,
        "raw_units": {"phase": "rad", "voltage": "V"},
        "phase_turn_conversion": "continuous_unwrap(raw JoSIM radians) / (2*pi)",
        "strict_spec": spec.metadata(),
        "full_trace_event_summary": {
            "complete_segment_count": sum(bool(item["complete_segment"]) for item in events["segments"]),
            "clean_separated_event_count": sum(bool(item["clean_separated_event"]) for item in events["segments"]),
            "largest_segment_turns": float(events["largest_segment_turns"]),
            "any_segment_spans_over_1_15_turns": bool(events["any_segment_spans_over_1_15_turns"]),
            "continuous_multi_turn_running": bool(events["continuous_multi_turn_running"]),
        },
        "segments": [compact_segment(item) for item in events["segments"]],
        "windows": OrderedDict(
            (
                (name, event_window_summary(trace, events, phase_name, voltage_name, bounds))
                for name, bounds in WINDOWS_PS.items()
            )
        ),
    }


def current_kcl(trace: RawTrace) -> dict[str, Any]:
    branches = {
        "BJs": signal(trace, "I(BJS|XBQ1)"),
        "BJ1": signal(trace, "I(BJ1|XBQ1)"),
        "RJ1": signal(trace, "I(RJ1|XBQ1)"),
        "L1": signal(trace, "I(L1|XBQ1)"),
        "QB_BIAS": signal(trace, "I(I_QB_BIAS)"),
        "L2": signal(trace, "I(L2|XBQ1)"),
        "BJ2": signal(trace, "I(BJ2|XBQ1)"),
        "RJ2": signal(trace, "I(RJ2|XBQ1)"),
        "L3": signal(trace, "I(L3|XBQ1)"),
    }
    equations = OrderedDict(
        (
            (
                "node_2_BJs_BJ1_RJ1_L1",
                ({"BJs": 1.0, "BJ1": -1.0, "RJ1": -1.0, "L1": -1.0}, "I(BJs)-I(BJ1)-I(RJ1)-I(L1)=0"),
            ),
            (
                "node_bias_L1_source_L2",
                ({"L1": 1.0, "QB_BIAS": 1.0, "L2": -1.0}, "I(L1)+I(I_QB_BIAS)-I(L2)=0"),
            ),
            (
                "node_4_L2_BJ2_RJ2_L3",
                ({"L2": 1.0, "BJ2": -1.0, "RJ2": -1.0, "L3": -1.0}, "I(L2)-I(BJ2)-I(RJ2)-I(L3)=0"),
            ),
        )
    )
    result: dict[str, Any] = {
        "orientation": {
            "convention": "positive current is from the first listed deck node to the second",
            "node_2": "BJs 1->2 enters; BJ1/RJ1 2->0 and L1 2->BIAS leave",
            "node_bias": "L1 2->BIAS and I_QB_BIAS 0->BIAS enter; L2 BIAS->4 leaves",
            "node_4": "L2 BIAS->4 enters; BJ2/RJ2 4->0 and L3 4->OUT leave",
        },
        "equations": OrderedDict(),
    }
    for name, (coefficients, equation) in equations.items():
        residual = linear_kcl_residual(
            {branch: branches[branch] for branch in coefficients},
            coefficients,
        )
        result["equations"][name] = {
            "equation": equation,
            "coefficients": coefficients,
            "windows": OrderedDict(
                (
                    (
                        window_name,
                        kcl_window_metrics(trace.time, residual, window_s(bounds)),
                    )
                    for window_name, bounds in WINDOWS_PS.items()
                )
            ),
        }
    return result


def principal_event(junction: dict[str, Any], bounds: tuple[float, float]) -> dict[str, Any] | None:
    selected = window_segments(
        {"segments": junction["segments"]},
        bounds,
    )
    complete = [item for item in selected if bool(item["complete_segment"])]
    if not complete:
        return None
    return max(complete, key=lambda item: abs(float(item["phase_turns"])))


def settling_summary(trace: RawTrace, bj2: dict[str, Any]) -> dict[str, Any]:
    tail_bounds = WINDOWS_PS["TAIL_RESET"]
    tail_phase = phase_window(trace, bj2["phase_column"], tail_bounds)
    tail_voltage = waveform_window(trace, bj2["voltage_column"], tail_bounds, "V")
    tail_segments = window_segments({"segments": bj2["segments"]}, tail_bounds)
    tail_complete = [item for item in tail_segments if bool(item["complete_segment"])]
    duration_ps = float(tail_phase["window_last_sample_s"] - tail_phase["window_start_s"]) * 1.0e12
    drift_rate = (
        float(tail_phase["endpoint_delta_turns"]) / duration_ps
        if duration_ps > 0.0
        else None
    )
    return {
        "window_ps": list(tail_bounds),
        "post_event_mean_voltage_mV": float(tail_voltage["mean"]),
        "post_event_rms_voltage_mV": float(tail_voltage["rms"]),
        "post_event_max_abs_voltage_mV": float(tail_voltage["max_abs"]),
        "phase_plateau_p2p_turns": float(tail_phase["p2p_turns"]),
        "phase_endpoint_delta_turns": float(tail_phase["endpoint_delta_turns"]),
        "phase_drift_rate_turns_per_ps": drift_rate,
        "additional_complete_segments": len(tail_complete),
        "additional_complete_segment_onsets_ps": [float(item["start_time_ps"]) for item in tail_complete],
        "boundedness_observation": "descriptive; no single voltage threshold is used as a retrapping proof",
    }


def transport_summary(junctions: dict[str, Any]) -> dict[str, Any]:
    bj2 = junctions["BJ2"]
    source_window = bj2["windows"]["READ1_RESPONSE"]
    source_principal = principal_event(bj2, WINDOWS_PS["READ1_RESPONSE"])
    stages: OrderedDict[str, dict[str, Any]] = OrderedDict()
    source_onset = float(source_principal["start_time_ps"]) if source_principal else None
    source_direction = int(source_principal["direction"]) if source_principal else None
    stages["BJ2"] = {
        "role": "local QB output junction; not downstream reception by itself",
        "complete_segment_count": source_window["complete_segment_count"],
        "clean_separated_event_count": source_window["clean_separated_event_count"],
        "net_phase_turns": source_window["phase_window"]["endpoint_delta_turns"],
        "principal_event": source_principal,
        "continuous_multi_turn_running": source_window["continuous_multi_turn_running"],
        "onset_times_ps": source_window["complete_event_onset_times_ps"],
    }
    previous_onset: float | None = source_onset
    for stage in range(1, 7):
        label = f"JTL{stage}"
        b01 = junctions[label + ".B01"]
        b02 = junctions[label + ".B02"]
        b01_window = b01["windows"]["READ1_RESPONSE"]
        b02_window = b02["windows"]["READ1_RESPONSE"]
        b02_principal = principal_event(b02, WINDOWS_PS["READ1_RESPONSE"])
        b02_onset = float(b02_principal["start_time_ps"]) if b02_principal else None
        latency = b02_onset - source_onset if b02_onset is not None and source_onset is not None else None
        stages[label] = {
            "role": "JTL output-facing B02 is primary; B01 is auxiliary/internal",
            "B01_complete_segment_count": b01_window["complete_segment_count"],
            "B01_clean_separated_event_count": b01_window["clean_separated_event_count"],
            "B02_complete_segment_count": b02_window["complete_segment_count"],
            "B02_clean_separated_event_count": b02_window["clean_separated_event_count"],
            "B01_net_phase_turns": b01_window["phase_window"]["endpoint_delta_turns"],
            "B02_net_phase_turns": b02_window["phase_window"]["endpoint_delta_turns"],
            "B01_clean_onset_times_ps": b01_window["clean_event_onset_times_ps"],
            "B02_clean_onset_times_ps": b02_window["clean_event_onset_times_ps"],
            "B02_principal_event": b02_principal,
            "B02_latency_from_BJ2_principal_ps": latency,
            "B02_polarity": int(b02_principal["direction"]) if b02_principal else None,
            "B02_forward_after_BJ2": bool(b02_onset is not None and source_onset is not None and b02_onset > source_onset),
            "stage_order_comparable": bool(b02_principal is not None),
            "previous_stage_onset_ps": previous_onset,
            "stage_onset_increases_from_previous": bool(
                b02_onset is not None and previous_onset is not None and b02_onset > previous_onset
            ),
        }
        if b02_onset is not None:
            previous_onset = b02_onset
    stage_names = [f"JTL{stage}" for stage in range(1, 7)]
    b02_onsets = [stages[name]["B02_principal_event"]["start_time_ps"] for name in stage_names if stages[name]["B02_principal_event"]]
    return {
        "association_window": "READ1_RESPONSE 110-170 ps for four-BVM; per-run protection separately uses 70-82 ps",
        "stages": stages,
        "B02_principal_onset_order_ps": b02_onsets,
        "B02_principal_onset_strictly_increasing": bool(len(b02_onsets) >= 2 and all(a < b for a, b in zip(b02_onsets, b02_onsets[1:]))),
        "transport_identity_status": "NOT_ESTABLISHED_BY_LOCAL_SUMMARIES",
        "warning": "local B02 events are not automatically matched cross-junction identities; onset order and polarity are descriptive checks",
    }


def protection_summary(record: dict[str, Any], junctions: dict[str, Any]) -> dict[str, Any] | None:
    if record["family"] != "single_bvm_protection":
        return None
    state = str(record["state"])
    bj2 = junctions["BJ2"]
    read_segments = window_segments({"segments": bj2["segments"]}, PROTECTION_READ_PS)
    post_segments = window_segments({"segments": bj2["segments"]}, PROTECTION_POST_PS)
    read_complete = [item for item in read_segments if bool(item["complete_segment"])]
    post_complete = [item for item in post_segments if bool(item["complete_segment"])]
    stage_rows = []
    for stage in range(1, 7):
        b02 = junctions[f"JTL{stage}.B02"]
        read = window_segments({"segments": b02["segments"]}, PROTECTION_READ_PS)
        post = window_segments({"segments": b02["segments"]}, PROTECTION_POST_PS)
        complete = [item for item in read if bool(item["complete_segment"])]
        clean = [item for item in complete if bool(item["clean_separated_event"])]
        post_complete = [item for item in post if bool(item["complete_segment"])]
        post_clean = [item for item in post_complete if bool(item["clean_separated_event"])]
        principal = max(complete, key=lambda item: abs(float(item["phase_turns"])), default=None)
        candidates = [
            item
            for item in read
            if abs(float(item["phase_turns"])) >= DESCRIPTIVE_CANDIDATE_MIN_TURNS
        ]
        principal_candidate = max(candidates, key=lambda item: abs(float(item["phase_turns"])), default=None)
        stage_rows.append(
            {
                "stage": stage,
                "complete_count_read": len(complete),
                "clean_count_read": len(clean),
                "complete_count_post": len(post_complete),
                "clean_count_post": len(post_clean),
                "principal_candidate_phase_turns": float(principal_candidate["phase_turns"]) if principal_candidate else None,
                "principal_candidate_area_turns": float(principal_candidate["voltage_area_turns"]) if principal_candidate else None,
                "principal_candidate_onset_ps": float(principal_candidate["start_time_ps"]) if principal_candidate else None,
                "principal_candidate_direction": int(principal_candidate["direction"]) if principal_candidate else None,
                "principal_phase_turns": float(principal["phase_turns"]) if principal else None,
                "principal_area_turns": float(principal["voltage_area_turns"]) if principal else None,
                "principal_onset_ps": float(principal["start_time_ps"]) if principal else None,
                "principal_direction": int(principal["direction"]) if principal else None,
            }
        )
    bj2_principal = max(read_complete, key=lambda item: abs(float(item["phase_turns"])), default=None)
    false_trigger = bool(
        read_complete
        or post_complete
        or any(row["complete_count_read"] or row["complete_count_post"] for row in stage_rows)
    )
    source_approximately_one_phi0 = False
    all_stage_one = False
    same_polarity = False
    increasing = False
    if state == "S0":
        verdict = "S0_NO_STRICT_TRIGGER" if not false_trigger else "S0_FALSE_TRIGGER_OBSERVED"
    else:
        source_approximately_one_phi0 = bool(
            len(read_complete) == 1
            and bj2_principal
            and DESCRIPTIVE_ONE_PHI0_MIN_TURNS <= abs(float(bj2_principal["phase_turns"])) <= DESCRIPTIVE_ONE_PHI0_MAX_TURNS
            and DESCRIPTIVE_ONE_PHI0_MIN_TURNS <= abs(float(bj2_principal["voltage_area_turns"])) <= DESCRIPTIVE_ONE_PHI0_MAX_TURNS
            and abs(float(bj2_principal["signed_phase_area_residual_turns"])) <= DESCRIPTIVE_ONE_PHI0_RESIDUAL_MAX_TURNS
        )
        all_stage_one = all(row["clean_count_read"] == 1 for row in stage_rows)
        same_polarity = bool(
            bj2_principal
            and all(row["principal_direction"] == int(bj2_principal["direction"]) for row in stage_rows if row["principal_direction"] is not None)
        )
        increasing = bool(
            all(
                stage_rows[index]["principal_onset_ps"] is not None
                and stage_rows[index + 1]["principal_onset_ps"] is not None
                and stage_rows[index + 1]["principal_onset_ps"] > stage_rows[index]["principal_onset_ps"]
                for index in range(len(stage_rows) - 1)
            )
        )
        verdict = "S1_PROTECTED_CANDIDATE" if source_approximately_one_phi0 and all_stage_one and same_polarity and increasing else "S1_PROTECTION_INCONCLUSIVE"
    return {
        "state": state,
        "read_window_ps": list(PROTECTION_READ_PS),
        "post_window_ps": list(PROTECTION_POST_PS),
        "S0_false_trigger_or_extra": false_trigger if state == "S0" else None,
        "BJ2_read_complete_count": len(read_complete),
        "BJ2_post_complete_count": len(post_complete),
        "BJ2_principal_phase_turns": float(bj2_principal["phase_turns"]) if bj2_principal else None,
        "BJ2_principal_flux_turns": float(bj2_principal["voltage_area_turns"]) if bj2_principal else None,
        "BJ2_principal_phase_area_residual_turns": float(bj2_principal["signed_phase_area_residual_turns"]) if bj2_principal else None,
        "BJ2_principal_onset_ps": float(bj2_principal["start_time_ps"]) if bj2_principal else None,
        "BJ2_principal_direction": int(bj2_principal["direction"]) if bj2_principal else None,
        "jtl_B02_read": stage_rows,
        "criteria_observation": {
            "S1_source_same_event_approximately_one_phi0": source_approximately_one_phi0 if state == "S1" else None,
            "S1_source_approximately_one_phi0_threshold_status": (
                "POST_HOC_DESCRIPTIVE_NOT_PREREGISTERED" if state == "S1" else None
            ),
            "all_six_B02_one_clean_event": state == "S1" and all(row["clean_count_read"] == 1 for row in stage_rows),
            "same_polarity": state == "S1" and bool(bj2_principal) and same_polarity if state == "S1" else None,
            "strictly_increasing_onsets": state == "S1" and increasing if state == "S1" else None,
        },
        "descriptive_thresholds": {
            "candidate_min_abs_phase_turns": DESCRIPTIVE_CANDIDATE_MIN_TURNS,
            "one_phi0_phase_and_area_range_turns": [
                DESCRIPTIVE_ONE_PHI0_MIN_TURNS,
                DESCRIPTIVE_ONE_PHI0_MAX_TURNS,
            ],
            "one_phi0_phase_area_residual_max_turns": DESCRIPTIVE_ONE_PHI0_RESIDUAL_MAX_TURNS,
            "status": "POST_HOC_DESCRIPTIVE_NOT_PREREGISTERED",
        },
        "protection_verdict": verdict,
        "warning": "S0 is assessed for complete local/read/post activity; sub-unit voltage activity is not called an SFQ trigger; descriptive candidate and approximately-one-Phi0 bounds are not preregistered acceptance gates",
    }


def key_waveforms(trace: RawTrace) -> dict[str, Any]:
    result: dict[str, Any] = OrderedDict()
    for label, unit in (
        ("V(BVMOUT)", "V"), ("I(BVMOUT)", "A"), ("V(QBIN)", "V"),
        ("V(QBOUT)", "V"), ("I(RJ1|XBQ1)", "A"), ("I(RJ2|XBQ1)", "A"),
        ("I(LIN|XBQ1)", "A"), ("I(L1|XBQ1)", "A"),
        ("I(L2|XBQ1)", "A"), ("I(L3|XBQ1)", "A"),
    ):
        result[label] = OrderedDict(
            (
                (name, waveform_window(trace, label, bounds, unit))
                for name, bounds in WINDOWS_PS.items()
            )
        )
    return result


def four_summary(record: dict[str, Any], junctions: dict[str, Any], transport: dict[str, Any], settling: dict[str, Any]) -> dict[str, Any] | None:
    if record["family"] != "four_bvm":
        return None
    bj1 = junctions["BJ1"]["windows"]["READ1_RESPONSE"]
    bj2 = junctions["BJ2"]["windows"]["READ1_RESPONSE"]
    principal = principal_event(junctions["BJ2"], WINDOWS_PS["READ1_RESPONSE"])
    late = [
        item
        for item in window_segments({"segments": junctions["BJ2"]["segments"]}, WINDOWS_PS["READ1_RESPONSE"])
        if principal is not None and float(item["start_time_ps"]) > float(principal["end_time_ps"])
    ]
    if bj2["continuous_multi_turn_running"]:
        branch = "CONTINUOUS_MULTI_TURN_BRANCH"
    elif bj2["clean_separated_event_count"]:
        branch = "SEPARATED_LOCAL_EVENT_ACTIVITY"
    elif bj2["complete_segment_count"]:
        branch = "COMPLETE_LOCAL_ACTIVITY_NOT_CLEAN"
    else:
        branch = "NO_COMPLETE_BJ2_EVENT"
    return {
        "BJ1_READ1_net_turns": junctions["BJ1"]["windows"]["READ1_RESPONSE"]["phase_window"]["endpoint_delta_turns"],
        "BJ2_READ1_net_turns": bj2["phase_window"]["endpoint_delta_turns"],
        "BJ2_READ1_complete_segment_count": bj2["complete_segment_count"],
        "BJ2_READ1_clean_separated_event_count": bj2["clean_separated_event_count"],
        "BJ2_principal_event": principal,
        "BJ2_principal_flux_turns": float(principal["voltage_area_turns"]) if principal else None,
        "BJ2_principal_phase_step_turns": float(principal["phase_turns"]) if principal else None,
        "BJ2_principal_onset_ps": float(principal["start_time_ps"]) if principal else None,
        "BJ2_principal_end_ps": float(principal["end_time_ps"]) if principal else None,
        "BJ2_principal_continuous_running": bool(principal and principal["continuous_multiturn_segment"]),
        "late_candidate_count_after_principal": len([item for item in late if abs(float(item["phase_turns"])) >= 0.2]),
        "late_complete_count_after_principal": len([item for item in late if bool(item["complete_segment"])]),
        "late_complete_onsets_ps": [float(item["start_time_ps"]) for item in late if bool(item["complete_segment"])],
        "post_settling": settling,
        "JTL1_B02_READ1_net_turns": transport["stages"]["JTL1"]["B02_net_phase_turns"],
        "JTL6_B02_READ1_net_turns": transport["stages"]["JTL6"]["B02_net_phase_turns"],
        "JTL1_B02_complete_count": transport["stages"]["JTL1"]["B02_complete_segment_count"],
        "JTL6_B02_complete_count": transport["stages"]["JTL6"]["B02_complete_segment_count"],
        "branch_observation": branch,
        "BJ1_read_window_net_turns": bj1["phase_window"]["endpoint_delta_turns"],
        "warning": "four-BVM net phase trajectory and local/JTL event summaries remain separate; no four/five net-turn claim is an SFQ count",
    }


def run_result(record: dict[str, Any]) -> dict[str, Any]:
    raw_path = record["effective_raw"]
    deck_path = record["effective_deck"]
    result: dict[str, Any] = {
        "run_id": record["run_id"],
        "family": record["family"],
        "rj1_key": record["rj1_key"],
        "rj1_ohm": record["rj1_ohm"],
        "timestep_ps": record["timestep_ps"],
        "state": record["state"],
        "effective_attempt": record["effective_attempt"],
        "raw_path": rel(raw_path),
        "raw_sha256": sha256(raw_path),
        "deck_path": rel(deck_path),
        "deck_sha256": sha256(deck_path),
        "initial_deck_path": rel(record["initial_deck"]),
        "initial_deck_sha256": sha256(record["initial_deck"]),
        "raw_qa": None,
        "required_missing": [],
        "artifact_status": "INVALID",
    }
    trace = read_csv(raw_path)
    result["raw_qa"] = raw_qa(trace, record)
    headers = set(trace.headers)
    result["required_missing"] = [label for label in required_labels() if label not in headers]
    if result["required_missing"] or result["raw_qa"]["status"] != "VALID":
        result["warnings"] = ["required probe or actual timestep/grid QA failed; no physical interpretation generated"]
        return result

    junctions: dict[str, Any] = OrderedDict()
    for label, names in QB_JUNCTIONS.items():
        junctions[label] = junction_analysis(trace, raw_path, f"{record['run_id']}/{label}", label, names[0], names[1])
    for stage, cells in JTL_JUNCTIONS.items():
        for label, names in cells.items():
            junctions[f"{stage}.{label}"] = junction_analysis(
                trace, raw_path, f"{record['run_id']}/{stage}.{label}", f"{stage}.{label}", *names
            )
    transport = transport_summary(junctions)
    result.update(
        {
            "artifact_status": "VALID",
            "junctions": junctions,
            "transport": transport,
            "key_waveforms": key_waveforms(trace),
            "kcl": current_kcl(trace),
            "settling": settling_summary(trace, junctions["BJ2"]),
            "four_bvm_summary": four_summary(record, junctions, transport, settling_summary(trace, junctions["BJ2"])),
            "single_bvm_protection": protection_summary(record, junctions),
            "analysis_boundaries": {
                "observed": "raw/grid, phase/area segments, waveform and KCL arithmetic",
                "derived": "window-assigned complete/clean local segments and onset/latency summaries",
                "inference": "exploratory branch/protection labels only after comparison; not a Gate; descriptive candidate bounds are post-hoc",
                "unknown": "paper mechanism identity, canonical BVM compatibility, timestep convergence beyond tested pair",
            },
            "warnings": [
                "P(...) is raw JoSIM radians; turns are only continuous_unwrap(rad)/(2*pi)",
                "local JJ phase slip is not automatically downstream reception",
                "net phase trajectory is not an SFQ count",
                "no post-hoc parameter tuning was performed; strict-event tolerances are pre-registered in experiment.yaml, while candidate and approximately-one-Phi0 bounds are descriptive post-hoc analysis aids",
            ],
        }
    )
    return result


def fmt(value: Any, digits: int = 4) -> str:
    number = safe_float(value)
    return "n/a" if number is None else f"{number:.{digits}f}"


def result_markdown(result: dict[str, Any]) -> str:
    lines = [
        f"# {result['run_id']}",
        "",
        f"- family: `{result['family']}`; RJ1: `{result['rj1_ohm']} ohm`; timestep: `{result['timestep_ps']} ps`; state: `{result['state']}`",
        f"- effective raw: `{result['raw_path']}` (`{result['effective_attempt']}`)",
        f"- artifact status: **{result['artifact_status']}**",
        "",
    ]
    if result["artifact_status"] != "VALID":
        lines.extend(["## QA", "", f"- missing probes: `{', '.join(result['required_missing'])}`", "- no physical interpretation was generated.", ""])
        return "\n".join(lines)
    four = result.get("four_bvm_summary")
    protection = result.get("single_bvm_protection")
    bj2 = result["junctions"]["BJ2"]
    read1 = bj2["windows"]["READ1_RESPONSE"]
    lines.extend(
        [
            "## Observed / derived key data",
            "",
            f"- actual grid: `{fmt(result['raw_qa']['actual_timestep_ps_median'], 6)} ps`, saved `{fmt(result['raw_qa']['time_start_ps'], 3)}..{fmt(result['raw_qa']['time_last_sample_ps'], 3)} ps`, interpolation: none",
            f"- BJ2 READ1 net trajectory: `{fmt(read1['phase_window']['endpoint_delta_turns'], 6)} turn`; complete segments: `{read1['complete_segment_count']}`; clean separated events: `{read1['clean_separated_event_count']}`",
            f"- BJ2 continuous multi-turn status in READ1: `{read1['continuous_multi_turn_running']}`",
            f"- BJ2 settling tail: mean V `{fmt(result['settling']['post_event_mean_voltage_mV'], 6)} mV`, RMS V `{fmt(result['settling']['post_event_rms_voltage_mV'], 6)} mV`, phase p2p `{fmt(result['settling']['phase_plateau_p2p_turns'], 6)} turn`, tail complete segments `{result['settling']['additional_complete_segments']}`",
        ]
    )
    if four:
        principal = four["BJ2_principal_event"]
        lines.extend(
            [
                f"- four-BVM branch observation: `{four['branch_observation']}`; BJ1 net `{fmt(four['BJ1_READ1_net_turns'], 6)} turn`; BJ2 net `{fmt(four['BJ2_READ1_net_turns'], 6)} turn`",
                f"- BJ2 principal same-segment phase/area: phase `{fmt(four['BJ2_principal_phase_step_turns'], 6)} turn`, area `{fmt(four['BJ2_principal_flux_turns'], 6)} Phi0`, onset `{fmt(four['BJ2_principal_onset_ps'], 3)} ps`, continuous segment `{bool(principal and principal['continuous_multiturn_segment'])}`",
                f"- late complete segments after principal: `{four['late_complete_count_after_principal']}`; JTL1/JTL6 B02 READ1 net trajectories: `{fmt(four['JTL1_B02_READ1_net_turns'], 6)}` / `{fmt(four['JTL6_B02_READ1_net_turns'], 6)}` turn",
            ]
        )
    if protection:
        lines.extend(
            [
                "",
                "## Single-BVM protection",
                "",
                f"- protection verdict: `{protection['protection_verdict']}`; S0 false/extra trigger flag: `{protection['S0_false_trigger_or_extra']}`",
                f"- BJ2 principal phase/area: `{fmt(protection['BJ2_principal_phase_turns'], 6)} turn` / `{fmt(protection['BJ2_principal_flux_turns'], 6)} Phi0`; JTL B02 read complete counts: `{[row['complete_count_read'] for row in protection['jtl_B02_read']]}`",
            ]
        )
    lines.extend(
        [
            "",
            "## Interpretation boundary",
            "",
            "- **Observed:** values above are derived from the immutable raw using exact stored samples and same-JJ phase/area segments.",
            "- **Not claimed:** a net four/five-turn trajectory is not four/five SFQ events; local phase is not automatically transported reception; this run does not prove canonical BVM compatibility or convergence.",
            "",
        ]
    )
    return "\n".join(lines)


def compact_run_summary(result: dict[str, Any]) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "run_id": result["run_id"],
        "family": result["family"],
        "rj1_ohm": result["rj1_ohm"],
        "timestep_ps": result["timestep_ps"],
        "state": result["state"],
        "artifact_status": result["artifact_status"],
        "effective_attempt": result["effective_attempt"],
        "raw_path": result["raw_path"],
        "raw_sha256": result["raw_sha256"],
        "deck_path": result["deck_path"],
        "deck_sha256": result["deck_sha256"],
        "actual_timestep_ps": result["raw_qa"]["actual_timestep_ps_median"] if result["raw_qa"] else None,
    }
    if result["artifact_status"] != "VALID":
        return summary
    if result["family"] == "four_bvm":
        four = result["four_bvm_summary"]
        summary.update(
            {
                "BJ1_net_turns": four["BJ1_READ1_net_turns"],
                "BJ2_net_turns": four["BJ2_READ1_net_turns"],
                "BJ2_phase_step_turns": four["BJ2_principal_phase_step_turns"],
                "BJ2_flux_turns": four["BJ2_principal_flux_turns"],
                "BJ2_principal_onset_ps": four["BJ2_principal_onset_ps"],
                "BJ2_complete_count": four["BJ2_READ1_complete_segment_count"],
                "BJ2_clean_count": four["BJ2_READ1_clean_separated_event_count"],
                "BJ2_continuous_running": four["BJ2_principal_continuous_running"],
                "late_complete_count": four["late_complete_count_after_principal"],
                "JTL1_B02_net_turns": four["JTL1_B02_READ1_net_turns"],
                "JTL6_B02_net_turns": four["JTL6_B02_READ1_net_turns"],
                "JTL1_B02_complete_count": four["JTL1_B02_complete_count"],
                "JTL6_B02_complete_count": four["JTL6_B02_complete_count"],
                "branch_observation": four["branch_observation"],
            }
        )
    else:
        protection = result["single_bvm_protection"]
        summary.update(
            {
                "S0_false_trigger_or_extra": protection["S0_false_trigger_or_extra"],
                "BJ2_principal_phase_turns": protection["BJ2_principal_phase_turns"],
                "BJ2_principal_flux_turns": protection["BJ2_principal_flux_turns"],
                "JTL1_B02_phase_turns": protection["jtl_B02_read"][0]["principal_phase_turns"],
                "JTL1_B02_flux_turns": protection["jtl_B02_read"][0]["principal_area_turns"],
                "JTL6_B02_phase_turns": protection["jtl_B02_read"][5]["principal_phase_turns"],
                "JTL6_B02_flux_turns": protection["jtl_B02_read"][5]["principal_area_turns"],
                "protection_verdict": protection["protection_verdict"],
            }
        )
    return summary


def effective_manifest(records: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "raw_policy": "raw files immutable; four-BVM attempt-01 incomplete probes retained; attempt-03 is effective",
        "runs": [
            {
                "run_id": record["run_id"],
                "family": record["family"],
                "rj1_ohm": record["rj1_ohm"],
                "timestep_ps": record["timestep_ps"],
                "state": record["state"],
                "effective_attempt": record["effective_attempt"],
                "effective_deck": rel(record["effective_deck"]),
                "effective_raw": rel(record["effective_raw"]),
                "initial_deck": rel(record["initial_deck"]),
                "initial_raw": rel(record["initial_raw"]),
            }
            for record in records
        ],
    }


def provenance(records: list[dict[str, Any]], results: list[dict[str, Any]], timestamp: str) -> dict[str, Any]:
    source_paths = [
        HISTORICAL_BQ, HISTORICAL_BVM, JTL_SOURCE, HISTORICAL_RAW, CANONICAL_BVM,
        AUTH_QB, SHARED_JJ, METRIC_SPEC, PLOTTER,
        EXP / "inputs/generate_decks.py", EXP / "inputs/make_four_probe_complete_attempt2.py",
        EXP / "inputs/make_four_probe_complete_attempt3.py", EXP / "analysis/analyze.py",
    ]
    snapshots = {rel(path): {"sha256": sha256(path), "bytes": path.stat().st_size} for path in source_paths if path.exists()}
    run_records = []
    for record, result in zip(records, results):
        command_file = EXP / "runs" / record["run_id"] / record["effective_attempt"] / "logs/command-01.txt" if record["family"] == "four_bvm" else EXP / "runs" / record["run_id"] / "logs/command-01.txt"
        run_records.append(
            {
                "run_id": record["run_id"],
                "family": record["family"],
                "rj1_ohm": record["rj1_ohm"],
                "timestep_ps": record["timestep_ps"],
                "state": record["state"],
                "effective_attempt": record["effective_attempt"],
                "deck": result.get("deck_path"),
                "deck_sha256": result.get("deck_sha256"),
                "raw": result.get("raw_path"),
                "raw_sha256": result.get("raw_sha256"),
                "command_file": rel(command_file) if command_file.exists() else None,
                "command_file_sha256": sha256(command_file) if command_file.exists() else None,
                "exit_code_recorded": 0 if command_file.exists() and "exit_code: 0" in command_file.read_text(encoding="utf-8") else None,
            }
        )
    return {
        "generated_at": timestamp,
        "head_before_task": "751a276adb73214c34b5f39fcfab4fbff95d1060",
        "head_at_analysis": git_snapshot(REPO),
        "setup_commit": "d3c0fb2 experiment: freeze RJ1 timestep robustness matrix",
        "source_hashes": snapshots,
        "explicit_source_boundary": {
            "BVMSim_bvm_is_not_canonical": True,
            "BVMSim_R_JM1_ohm": 8,
            "canonical_R_JM1_ohm": 6,
            "canonical_bvm_used": False,
            "BVMSim_BQ_variants_used_as_formal_source": False,
        },
        "solver": solver_provenance(SOLVER, cwd=REPO),
        "experiment_local_variants": {
            rel(EXP / "inputs/qb-rj1-12.cir"): sha256(EXP / "inputs/qb-rj1-12.cir"),
            rel(EXP / "inputs/qb-rj1-11p5.cir"): sha256(EXP / "inputs/qb-rj1-11p5.cir"),
            rel(EXP / "inputs/qb-rj1-11.cir"): sha256(EXP / "inputs/qb-rj1-11.cir"),
        },
        "variant_diff_check": json.loads((EXP / "inputs/variant_diff_check.json").read_text(encoding="utf-8")),
        "run_records": run_records,
        "analysis_semantics": {
            "phase": "raw JoSIM radians; continuous unwrap then divide by 2*pi",
            "voltage_area": "same-JJ same-segment trapezoid integral(V dt)/Phi0",
            "event_helper": "scripts/bvmtools/sfq.py strict_event_list",
            "kcl_helper": "scripts/bvmtools/kcl.py",
            "interpolation": "none for run-local arithmetic and no raw rewrite",
            "descriptive_candidate_threshold": {
                "min_abs_phase_turns": DESCRIPTIVE_CANDIDATE_MIN_TURNS,
                "status": "POST_HOC_DESCRIPTIVE_NOT_PREREGISTERED",
            },
            "descriptive_one_phi0_thresholds": {
                "phase_and_area_range_turns": [
                    DESCRIPTIVE_ONE_PHI0_MIN_TURNS,
                    DESCRIPTIVE_ONE_PHI0_MAX_TURNS,
                ],
                "phase_area_residual_max_turns": DESCRIPTIVE_ONE_PHI0_RESIDUAL_MAX_TURNS,
                "status": "POST_HOC_DESCRIPTIVE_NOT_PREREGISTERED",
            },
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--timestamp", default=None)
    args = parser.parse_args()
    timestamp = args.timestamp or datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    records = config_records()
    results: list[dict[str, Any]] = []
    for record in records:
        result = run_result(record)
        results.append(result)
        run_analysis_dir = EXP / "runs" / record["run_id"] / "analysis"
        json_write(run_analysis_dir / "metrics.json", result)
        (run_analysis_dir / "RESULT.md").write_text(result_markdown(result), encoding="utf-8")

    summaries = [compact_run_summary(result) for result in results]
    global_metrics = {
        "experiment": "BVM_QB_RJ1_TIMESTEP_ROBUSTNESS_V1",
        "analysis_version": "rj1-robustness-per-run-v1",
        "generated_at": timestamp,
        "artifact_status": "VALID" if all(item["artifact_status"] == "VALID" for item in results) else "INVALID",
        "run_count": len(results),
        "four_bvm_count": sum(item["family"] == "four_bvm" for item in results),
        "single_bvm_protection_count": sum(item["family"] == "single_bvm_protection" for item in results),
        "run_summaries": summaries,
        "per_run_metrics": {
            result["run_id"]: rel(EXP / "runs" / result["run_id"] / "analysis/metrics.json")
            for result in results
        },
        "classification_boundary": "comparison and reviewer are required before final exploratory classifications",
    }
    json_write(EXP / "analysis/metrics.json", global_metrics)
    json_write(EXP / "analysis/effective_run_manifest.json", effective_manifest(records))
    json_write(EXP / "analysis/provenance.json", provenance(records, results, timestamp))
    review_path = EXP / "analysis/REVIEW.md"
    if not review_path.exists():
        review_path.write_text(
            "# REVIEW\n\n分析产物已生成；最终科学审阅待 Sol XHigh reviewer。\n\n"
            "本文件不把 solver exit 0、图形或 net turns 升级为 SFQ/Gate 结论。\n",
            encoding="utf-8",
        )
    (EXP / "analysis/human-gate.yaml").write_text(
        "state: AWAITING_USER_REVIEW\nuser_reviewed: false\nnext_step_authorized: false\nautomatic_next_experiment: false\nstage_b_authorized: false\nnext_action: STOP\n",
        encoding="utf-8",
    )
    print(json.dumps({"status": global_metrics["artifact_status"], "runs": len(results)}, ensure_ascii=False))
    return 0 if global_metrics["artifact_status"] == "VALID" else 2


if __name__ == "__main__":
    raise SystemExit(main())
