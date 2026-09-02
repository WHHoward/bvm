#!/usr/bin/env python3
"""Analyze Stage-A BVMSim QB migration and strict transport evidence.

This analyzer deliberately delegates CSV parsing, phase unwrapping, monotonic
segmentation, same-segment phase/area arithmetic, comparison, and KCL
arithmetic to ``bvmtools``.  Its local logic only associates the shared
segment records with the preregistered windows and reports the requested
multi-event classification.
"""

from __future__ import annotations

import hashlib
import json
import math
import subprocess
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Any, Iterable


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

from bvmtools.compare import compare_series, exact_time_grid_identity  # noqa: E402
from bvmtools.kcl import kcl_window_metrics, linear_kcl_residual  # noqa: E402
from bvmtools.phase import continuous_unwrap, phase_window_metrics, window_indices  # noqa: E402
from bvmtools.provenance import file_snapshot, git_snapshot, sha256_file, solver_provenance  # noqa: E402
from bvmtools.raw import RawTrace, read_csv  # noqa: E402
from bvmtools.sfq import StrictLocalEventSpec, strict_event_summary  # noqa: E402


HISTORICAL_RAW = REPO / "BVMSim/data_tran.csv"
M0_RAW = EXP / "raw/m0/run-01.csv"
S1_RAW = EXP / "raw/s1/run-01.csv"
METRIC_SPEC = REPO / "docs/research/METRIC_SPEC_V2.md"
SOLVER = REPO / "build/josim-cli"

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

MIGRATION_COLUMNS = (
    "I(BVMOUT)",
    "V(QBIN)",
    "V(QBOUT)",
    "V(O1)",
    "V(O3)",
    "V(O4)",
    "V(O5)",
    "V(O6)",
    "P(BJ1|XBQ1)",
    "P(B01|XJTL1_1)",
    "P(B01|XJTL1_2)",
)

QB_SIGNALS = OrderedDict(
    (
        ("BJs", ("P(BJS|XBQ1)", "V(BJS|XBQ1)")),
        ("BJ1", ("P(BJ1|XBQ1)", "V(BJ1|XBQ1)")),
        ("BJ2", ("P(BJ2|XBQ1)", "V(BJ2|XBQ1)")),
    )
)

JTL_SIGNALS = OrderedDict(
    (
        (f"JTL{stage}", OrderedDict(
            (
                ("B01", (f"P(B01|XJTL1_{stage})", f"V(B01|XJTL1_{stage})")),
                ("B02", (f"P(B02|XJTL1_{stage})", f"V(B02|XJTL1_{stage})")),
            )
        ))
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

M0_CEILINGS = {
    "phase": 1.0e-8,
    "voltage": 1.0e-12,
    "current": 1.0e-12,
}


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def signal(trace: RawTrace, name: str) -> tuple[float, ...]:
    """Select a signal exactly, with only case-preserving unique fallback."""

    try:
        return trace.column(name)  # type: ignore[return-value]
    except KeyError:
        matches = [header for header in trace.headers if header.casefold() == name.casefold()]
        if len(matches) != 1:
            raise
        return trace.column(matches[0])  # type: ignore[return-value]


def full_window(trace: RawTrace) -> tuple[float, float]:
    dt = trace.time[-1] - trace.time[-2]
    return trace.time[0], trace.time[-1] + max(dt, 1.0e-30)


def time_ps(value_s: float) -> float:
    return float(value_s) * 1.0e12


def window_for_onset(start_s: float) -> str:
    start_ps = time_ps(start_s)
    for label, (left, right) in WINDOWS_PS.items():
        if left <= start_ps < right:
            return label
    return "OUTSIDE_REGISTERED_WINDOWS"


def touched_windows(start_s: float, end_s: float) -> list[str]:
    start_ps = time_ps(start_s)
    end_ps = time_ps(end_s)
    touched: list[str] = []
    for label, (left, right) in WINDOWS_PS.items():
        if start_ps < right and end_ps >= left:
            touched.append(label)
    return touched


def strict_spec(raw_path: Path, phase_name: str, voltage_name: str, run_id: str) -> StrictLocalEventSpec:
    return StrictLocalEventSpec.from_mapping(
        {
            "id": "bvmsim-qb-stage-a-strict-local-event-v1",
            "scope": "task-local",
            "status": "FROZEN",
            "mapping_status": "DECLARED_DIRECT_SAME_JJ_PV",
            "phase_column": phase_name,
            "voltage_column": voltage_name,
            "branch_endpoints": f"JoSIM direct branch {phase_name} and {voltage_name}; deck element orientation",
            "voltage_to_phase_sign": 1,
            "reporting_direction": 1,
            "run_id": run_id,
            "window_id": "full-trace-segments-associated-by-onset-to-0-50-70-90-110-170-200ps",
            "raw_sha256": sha256_file(raw_path),
            "metric_spec": {
                "path": "docs/research/METRIC_SPEC_V2.md",
                "version": "2.0.0",
                "sha256": sha256_file(METRIC_SPEC),
            },
            "tolerance": {
                "id": "bvmsim-qb-stage-a-task-local-strict-event-v1",
                "scope": "task-local",
                "status": "FROZEN",
                "evidence": "test/exploration/bvmsim-qb-strict-qualification-v1-20260902/experiment.yaml",
                **STRICT_TOLERANCE,
            },
            "compatibility_profile": "STRICT_EVENT_ANCHOR_COMPATIBILITY_V1",
        }
    )


def _complete(record: dict[str, object]) -> bool:
    return record.get("area_consistent") is True and abs(float(record["phase_reported_turns"])) >= 1.0


def enrich_segments(
    trace: RawTrace,
    segments: Iterable[dict[str, object]],
) -> list[dict[str, object]]:
    """Add event-list classification to shared strict segment records.

    No new detector is used here.  ``strict_event_summary`` already supplies
    the ordered monotonic segments, phase/area residuals, and completeness.
    This function only checks whether adjacent shared segments provide a
    bounded opposite-direction retrap before the next complete segment.
    """

    base = [dict(item) for item in segments]
    complete_indices = [index for index, item in enumerate(base) if _complete(item)]
    # The phase sequence is supplied per signal by the caller through the
    # temporary private field below; this keeps the helper generic.
    phase_unwrapped = getattr(enrich_segments, "_phase_unwrapped", None)
    if phase_unwrapped is None:
        raise RuntimeError("enrich_segments requires its signal phase context")

    for index, item in enumerate(base):
        turns = float(item["phase_reported_turns"])
        item["complete_segment"] = _complete(item)
        item["clean_band"] = bool(_complete(item) and abs(turns) <= STRICT_TOLERANCE["clean_upper_turns"])
        item["onset_context"] = window_for_onset(float(item["start_time_s"]))
        item["windows_touched"] = touched_windows(float(item["start_time_s"]), float(item["end_time_s"]))
        item["crosses_registered_boundary"] = len(item["windows_touched"]) > 1
        item["retrap_or_bounded_interval"] = None
        item["clean_separated_event"] = False

    for ordinal, index in enumerate(complete_indices):
        current = base[index]
        next_index = complete_indices[ordinal + 1] if ordinal + 1 < len(complete_indices) else None
        if next_index is not None:
            between = base[index + 1 : next_index]
            intermediate_turns = sum(abs(float(item["phase_reported_turns"])) for item in between)
            opposite_retrap = any(
                int(item["direction"]) == -int(current["direction"])
                for item in between
            )
            bounded = bool(
                between
                and opposite_retrap
                and not any(bool(item.get("complete_segment")) for item in between)
                and intermediate_turns < STRICT_TOLERANCE["complete_min_turns"]
            )
            current["retrap_or_bounded_interval"] = {
                "kind": "INTER_EVENT_RETRAP",
                "bounded": bounded,
                "start_time_ps": float(between[0]["start_time_ps"]) if between else None,
                "end_time_ps": float(between[-1]["end_time_ps"]) if between else None,
                "duration_ps": (
                    float(between[-1]["end_time_ps"]) - float(between[0]["start_time_ps"])
                    if between
                    else 0.0
                ),
                "intermediate_segment_count": len(between),
                "intermediate_abs_turns_sum": intermediate_turns,
                "opposite_direction_retrap": opposite_retrap,
                "intermediate_complete_segment": any(bool(item.get("complete_segment")) for item in between),
            }
            current["clean_separated_event"] = bool(current["clean_band"] and bounded)
        else:
            end_index = int(current["end_index"])
            tail_values = [float(value) for value in phase_unwrapped[end_index:]]
            tail_p2p = (max(tail_values) - min(tail_values)) / (2.0 * math.pi) if len(tail_values) >= 2 else None
            bounded = tail_p2p is not None and tail_p2p <= STRICT_TOLERANCE["post_tail_p2p_max_turns"]
            current["retrap_or_bounded_interval"] = {
                "kind": "POST_EVENT_BOUNDED_TAIL",
                "bounded": bounded,
                "start_time_ps": float(current["end_time_ps"]),
                "end_time_ps": time_ps(trace.time[-1]),
                "duration_ps": time_ps(trace.time[-1] - trace.time[end_index]),
                "tail_phase_p2p_turns": tail_p2p,
            }
            current["clean_separated_event"] = bool(current["clean_band"] and bounded)

    for item in base:
        item["continuous_multiturn_segment"] = abs(float(item["phase_reported_turns"])) > STRICT_TOLERANCE["clean_upper_turns"]
    return base


def analyze_signal(trace: RawTrace, label: str, phase_name: str, voltage_name: str, run_id: str) -> dict[str, object]:
    phase = signal(trace, phase_name)
    voltage = signal(trace, voltage_name)
    spec = strict_spec(trace.path, phase_name, voltage_name, run_id)
    summary = strict_event_summary(
        trace.time,
        phase,
        voltage,
        activity_window_s=full_window(trace),
        spec=spec,
        actual_raw_sha256=sha256_file(trace.path),
        actual_metric_spec_sha256=sha256_file(METRIC_SPEC),
    )
    enrich_segments._phase_unwrapped = continuous_unwrap(phase)  # type: ignore[attr-defined]
    segments = enrich_segments(trace, summary["activity_segments"])  # type: ignore[arg-type]
    delattr(enrich_segments, "_phase_unwrapped")

    complete = [item for item in segments if bool(item["complete_segment"])]
    clean = [item for item in segments if bool(item["clean_separated_event"])]
    largest = max(segments, key=lambda item: abs(float(item["phase_reported_turns"]))) if segments else None
    association: dict[str, object] = OrderedDict()
    for window_label, (left_ps, right_ps) in WINDOWS_PS.items():
        left_s, right_s = left_ps * 1.0e-12, right_ps * 1.0e-12
        onset_segments = [
            item for item in segments if left_s <= float(item["start_time_s"]) < right_s
        ]
        onset_complete = [item for item in onset_segments if bool(item["complete_segment"])]
        onset_clean = [item for item in onset_segments if bool(item["clean_separated_event"])]
        try:
            phase_window = phase_window_metrics(trace.time, phase, (left_s, right_s))
        except ValueError as exc:
            phase_window = {"status": "INSUFFICIENT_SAMPLES", "reason": str(exc)}
        association[window_label] = {
            "window_ps": [left_ps, right_ps],
            "onset_complete_segment_count": len(onset_complete),
            "onset_clean_separated_event_count": len(onset_clean),
            "complete_onset_times_ps": [float(item["start_time_ps"]) for item in onset_complete],
            "clean_onset_times_ps": [float(item["start_time_ps"]) for item in onset_clean],
            "directions": [int(item["direction"]) for item in onset_clean],
            "crossing_segments": [
                {
                    "start_time_ps": float(item["start_time_ps"]),
                    "end_time_ps": float(item["end_time_ps"]),
                    "windows_touched": item["windows_touched"],
                    "direction": int(item["direction"]),
                    "phase_turns": float(item["phase_reported_turns"]),
                }
                for item in onset_segments
                if bool(item["crosses_registered_boundary"])
            ],
            "phase_window": phase_window,
        }

    return {
        "label": label,
        "phase_column": phase_name,
        "voltage_column": voltage_name,
        "spec": summary["spec"],
        "raw_sha256_match": summary["raw_sha256_match"],
        "metric_spec_sha256_match": summary["metric_spec_sha256_match"],
        "segment_count": len(segments),
        "complete_segment_count": len(complete),
        "clean_separated_event_count": len(clean),
        "complete_segment_onset_times_ps": [float(item["start_time_ps"]) for item in complete],
        "clean_event_onset_times_ps": [float(item["start_time_ps"]) for item in clean],
        "clean_event_directions": [int(item["direction"]) for item in clean],
        "largest_segment": largest,
        "largest_segment_turns": abs(float(largest["phase_reported_turns"])) if largest else 0.0,
        "any_segment_spans_over_1_15_turns": any(
            abs(float(item["phase_reported_turns"])) > STRICT_TOLERANCE["clean_upper_turns"]
            for item in segments
        ),
        "continuous_multi_turn_running": any(
            bool(item["continuous_multiturn_segment"]) and bool(item["complete_segment"])
            for item in segments
        ),
        "segments": segments,
        "association_windows": association,
        "shared_summary": {
            "activity_window_s": summary["activity_window_s"],
            "window_phase_displacement_turns": summary["window_phase_displacement_turns"],
            "compatibility_classification": summary["compatibility_classification"],
            "classification_reason": summary["classification_reason"],
        },
    }


def required_signal_check(trace: RawTrace) -> list[str]:
    required: list[str] = [
        "I(BVMOUT)", "V(QBIN)", "V(QBOUT)", "V(O1)", "V(O2)", "V(O3)", "V(O4)", "V(O5)", "V(O6)",
        "I(LIN|XBQ1)", "I(BJS|XBQ1)", "P(BJS|XBQ1)", "V(BJS|XBQ1)",
        "I(BJ1|XBQ1)", "P(BJ1|XBQ1)", "V(BJ1|XBQ1)", "I(RJ1|XBQ1)",
        "I(L1|XBQ1)", "I(I_QB_BIAS)", "I(L2|XBQ1)",
        "I(BJ2|XBQ1)", "P(BJ2|XBQ1)", "V(BJ2|XBQ1)", "I(RJ2|XBQ1)", "I(L3|XBQ1)",
    ]
    for cell in JTL_SIGNALS.values():
        for phase_name, voltage_name in cell.values():
            required.extend((phase_name, voltage_name))
    return [name for name in required if not any(header.casefold() == name.casefold() for header in trace.headers)]


def compare_migration(hist: RawTrace, migrated: RawTrace) -> dict[str, object]:
    grid_exact = exact_time_grid_identity(hist.time, migrated.time)
    result: dict[str, object] = {
        "status": "INVALID_TIME_GRID" if not grid_exact else "PENDING_VALUE_COMPARISON",
        "historical_raw": str(HISTORICAL_RAW.relative_to(REPO)),
        "migrated_raw": str(M0_RAW.relative_to(REPO)),
        "historical_sample_count": hist.sample_count,
        "migrated_sample_count": migrated.sample_count,
        "historical_time_start_ps": time_ps(hist.time[0]),
        "historical_time_end_ps": time_ps(hist.time[-1]),
        "migrated_time_start_ps": time_ps(migrated.time[0]),
        "migrated_time_end_ps": time_ps(migrated.time[-1]),
        "time_grid_exact": grid_exact,
        "interpolation_mode": "none",
        "historical_duplicate_columns": hist.duplicate_columns,
        "duplicate_column_policy": "V(O2) was not selected; bvmtools occurrence-preserving reader used",
        "signals": {},
    }
    if not grid_exact:
        return result
    all_ok = True
    for name in MIGRATION_COLUMNS:
        left = signal(hist, name)
        right = signal(migrated, name)
        comparison = compare_series(hist.time, left, migrated.time, right, interpolation=None)
        compact = {key: value for key, value in comparison.items() if key != "pointwise_difference"}
        kind = "phase" if name.startswith("P(") else "voltage" if name.startswith("V(") else "current"
        ceiling = M0_CEILINGS[kind]
        max_abs = float(compact["max_abs_difference"])
        within = max_abs <= ceiling
        all_ok = all_ok and within
        compact.update(
            {
                "signal_kind": kind,
                "numerical_ceiling": ceiling,
                "within_numerical_ceiling": within,
                "historical_first": float(left[0]),
                "migrated_first": float(right[0]),
                "historical_last": float(left[-1]),
                "migrated_last": float(right[-1]),
                "historical_peak_to_peak": max(left) - min(left),
                "migrated_peak_to_peak": max(right) - min(right),
            }
        )
        result["signals"][name] = compact  # type: ignore[index]
    result["status"] = "PASS" if all_ok else "FAIL"
    result["acceptance_note"] = (
        "PASS means exact grid and every selected shared signal is within the preregistered tight numerical ceiling; "
        "this is packaging equivalence, not a physical Gate."
    )
    return result


def analyze_kcl(trace: RawTrace) -> dict[str, object]:
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
            ("node_2_BJs_BJ1_RJ1_L1", ({"BJs": 1.0, "BJ1": -1.0, "RJ1": -1.0, "L1": -1.0}, "I(BJs)-I(BJ1)-I(RJ1)-I(L1)=0")),
            ("node_bias_L1_source_L2", ({"L1": 1.0, "QB_BIAS": 1.0, "L2": -1.0}, "I(L1)+I(I_QB_BIAS)-I(L2)=0")),
            ("node_4_L2_BJ2_RJ2_L3", ({"L2": 1.0, "BJ2": -1.0, "RJ2": -1.0, "L3": -1.0}, "I(L2)-I(BJ2)-I(RJ2)-I(L3)=0")),
        )
    )
    orientation = {
        "convention": "positive current is from the first listed deck node to the second",
        "node_2": "BJs 1→2 enters; BJ1 2→0, L1 2→BIAS leave",
        "node_bias": "L1 2→BIAS and I_QB_BIAS 0→BIAS enter; L2 BIAS→4 leaves",
        "node_4": "L2 BIAS→4 enters; BJ2/RJ2 4→0 and L3 4→OUT leave",
    }
    metrics: dict[str, object] = {"orientation": orientation, "equations": {}}
    for label, (coefficients, equation) in equations.items():
        equation_branches = {name: branches[name] for name in coefficients}
        residual = linear_kcl_residual(equation_branches, coefficients)
        windows: dict[str, object] = {}
        for window_label, (left_ps, right_ps) in WINDOWS_PS.items():
            try:
                windows[window_label] = kcl_window_metrics(
                    trace.time,
                    residual,
                    (left_ps * 1.0e-12, right_ps * 1.0e-12),
                )
            except ValueError as exc:
                windows[window_label] = {"status": "INSUFFICIENT_SAMPLES", "reason": str(exc)}
        metrics["equations"][label] = {  # type: ignore[index]
            "equation": equation,
            "coefficients": coefficients,
            "windows": windows,
        }
    return metrics


def events_for_window(record: dict[str, object], label: str, *, clean: bool) -> list[dict[str, object]]:
    return [
        item
        for item in record["segments"]  # type: ignore[union-attr]
        if item["onset_context"] == label and (bool(item["clean_separated_event"]) if clean else bool(item["complete_segment"]))
    ]


def transport_summary(signals: dict[str, dict[str, object]], window_label: str) -> dict[str, object]:
    stage_records: OrderedDict[str, dict[str, object]] = OrderedDict()
    bj2_events = events_for_window(signals["BJ2"], window_label, clean=True)
    stage_records["BJ2"] = {
        "junction": "BJ2",
        "clean_event_count": len(bj2_events),
        "complete_segment_count": len(events_for_window(signals["BJ2"], window_label, clean=False)),
        "polarity": sorted(set(int(item["direction"]) for item in bj2_events)),
        "onset_times_ps": [float(item["start_time_ps"]) for item in bj2_events],
        "continuous_running": bool(signals["BJ2"]["continuous_multi_turn_running"]),
    }
    previous = bj2_events
    for stage, cell in JTL_SIGNALS.items():
        b01 = signals[f"{stage}.B01"]
        b02 = signals[f"{stage}.B02"]
        e01 = events_for_window(b01, window_label, clean=True)
        e02 = events_for_window(b02, window_label, clean=True)
        count = min(len(e01), len(e02))
        onsets = [float(item["start_time_ps"]) for item in e01[:count]]
        latencies = (
            [float(b["start_time_ps"]) - float(a["start_time_ps"]) for a, b in zip(previous[:count], e01[:count])]
            if len(previous) >= count and count > 0
            else None
        )
        stage_records[stage] = {
            "junction": "B01/B02 cell minimum",
            "clean_event_count": count,
            "B01_clean_event_count": len(e01),
            "B02_clean_event_count": len(e02),
            "B01_complete_segment_count": len(events_for_window(b01, window_label, clean=False)),
            "B02_complete_segment_count": len(events_for_window(b02, window_label, clean=False)),
            "polarity": sorted(set(int(item["direction"]) for item in (e01[:count] + e02[:count]))),
            "onset_times_ps": onsets,
            "B01_onset_times_ps": [float(item["start_time_ps"]) for item in e01],
            "B02_onset_times_ps": [float(item["start_time_ps"]) for item in e02],
            "latency_from_previous_stage_ps": latencies,
            "discrete_identity_ordered": all(
                earlier <= later for earlier, later in zip(onsets, onsets[1:])
            ),
        }
        previous = e01
    return {"window": window_label, "stages": stage_records}


def all_signal_records(trace: RawTrace, run_id: str) -> dict[str, dict[str, object]]:
    records: dict[str, dict[str, object]] = {}
    for label, (phase_name, voltage_name) in QB_SIGNALS.items():
        records[label] = analyze_signal(trace, label, phase_name, voltage_name, f"{run_id}/{label}")
    for stage, cell in JTL_SIGNALS.items():
        for junction, (phase_name, voltage_name) in cell.items():
            records[f"{stage}.{junction}"] = analyze_signal(
                trace,
                f"{stage}.{junction}",
                phase_name,
                voltage_name,
                f"{run_id}/{stage}.{junction}",
            )
    return records


def scalar_phase_summary(record: dict[str, object], window_label: str) -> dict[str, object]:
    window = record["association_windows"][window_label]  # type: ignore[index]
    phase_window = window["phase_window"]  # type: ignore[index]
    return {
        "complete_segment_count": window["onset_complete_segment_count"],
        "clean_separated_event_count": window["onset_clean_separated_event_count"],
        "complete_onset_times_ps": window["complete_onset_times_ps"],
        "clean_onset_times_ps": window["clean_onset_times_ps"],
        "directions": window["directions"],
        "phase_window": phase_window,
    }


def classify(
    migration: dict[str, object],
    strict: dict[str, object],
    transport: dict[str, object],
) -> tuple[str, str]:
    if migration.get("status") != "PASS":
        return "MIGRATION_INVALID", "M0 migration equivalence did not pass; S1 science cannot be qualified"
    if strict.get("status") != "VALID":
        return "ANALYSIS_INVALID", "strict input/observable analysis is incomplete or invalid"
    bj2 = strict["signals"]["BJ2"]  # type: ignore[index]
    read1 = scalar_phase_summary(bj2, "READ1_RESPONSE")
    read0 = scalar_phase_summary(bj2, "READ0")
    stage_counts = [transport["stages"][stage]["clean_event_count"] for stage in ("BJ2", "JTL1", "JTL2", "JTL3", "JTL4", "JTL5", "JTL6")]  # type: ignore[index]
    read1_polarities = [
        polarity
        for stage in transport["stages"].values()  # type: ignore[union-attr]
        for polarity in stage["polarity"]  # type: ignore[index]
    ]
    extra_non_read1 = sum(
        int(strict["signals"][name]["association_windows"][window]["onset_complete_segment_count"])  # type: ignore[index]
        for name in ("BJ2", "JTL1.B01", "JTL2.B01", "JTL3.B01", "JTL4.B01", "JTL5.B01", "JTL6.B01")
        for window in ("INITIAL_PRE", "WRITE0", "READ0", "WRITE1", "TAIL_RESET")
    )
    if (
        read1["clean_separated_event_count"] == 4
        and stage_counts == [4, 4, 4, 4, 4, 4, 4]
        and read0["clean_separated_event_count"] == 0
        and all(polarity == 1 for polarity in read1_polarities)
        and extra_non_read1 == 0
    ):
        return "FOUR_SEPARATED_SFQ_TRANSPORT_SUPPORTED", "four read1 clean events and four-event cell-minimum transport at every stage"
    if bool(bj2["continuous_multi_turn_running"]):
        return "CONTINUOUS_MULTI_TURN_RUNNING_STATE", "at least one complete BJ2 segment exceeds the 1.15-turn clean band"
    if extra_non_read1 > 0 or read0["complete_segment_count"] > 0:
        return "SELECTIVITY_OR_OVERDRIVE_FAILURE", "complete output activity is present outside the intended READ1 association window"
    if read1["clean_separated_event_count"] > 0 and min(stage_counts[1:]) < read1["clean_separated_event_count"]:
        return "LOCAL_MULTI_SFQ_WITH_TRANSPORT_LOSS", "local clean BJ2 events are not preserved through all JTL stages"
    if read1["clean_separated_event_count"] > 1:
        return "OTHER_SEPARATED_MULTI_SFQ_TRANSPORT_SUPPORTED", "separated multi-event activity is present but does not meet the four-event strong label"
    if read1["complete_segment_count"] > 0:
        return "MULTI_PHASE_ACTIVITY_ONLY", "complete-looking phase segments lack the required clean separated interpretation"
    return "NO_CLEAR_STRICT_CLASSIFICATION", "no strong separated transport pattern was established"


def quick_label(classification: str) -> str:
    if classification == "FOUR_SEPARATED_SFQ_TRANSPORT_SUPPORTED":
        return "QUICK_PROMISING"
    if classification == "LOCAL_MULTI_SFQ_WITH_TRANSPORT_LOSS":
        return "QUICK_AMBIGUOUS"
    if classification in {"CONTINUOUS_MULTI_TURN_RUNNING_STATE", "SELECTIVITY_OR_OVERDRIVE_FAILURE"}:
        return "QUICK_OPPOSITE"
    if classification in {"MIGRATION_INVALID", "ANALYSIS_INVALID"}:
        return "QUICK_INVALID"
    return "QUICK_AMBIGUOUS"


def provenance(m0: RawTrace | None, s1: RawTrace | None) -> dict[str, object]:
    source_paths = [
        REPO / "BVMSim/BQ.cir",
        REPO / "BVMSim/bvm_cell.cir",
        REPO / "BVMSim/test_bvm_mixed_0.cir",
        REPO / "BVMSim/data_tran.csv",
        REPO / "BVMSim/library_josim/jtl2.cir",
        REPO / "BVMSim/run.sh",
        REPO / "BVMSim/josim-plot.py",
        REPO / "circuits/models/jjmit.cir",
        REPO / "circuits/bvm/bvm_cell.cir",
        REPO / "circuits/qb/bq_cell_bvmsim_v1.cir",
    ]
    artifact_paths = [
        EXP / "inputs/prepare_decks.py",
        EXP / "migrated/m0_bvmsim_qb.cir",
        EXP / "migrated/s1_bvmsim_qb.cir",
        REPO / "scripts/josim-plot2.py",
        REPO / "scripts/bvmtools/raw.py",
        REPO / "scripts/bvmtools/provenance.py",
        REPO / "scripts/bvmtools/phase.py",
        REPO / "scripts/bvmtools/sfq.py",
        REPO / "scripts/bvmtools/waveform.py",
        REPO / "scripts/bvmtools/compare.py",
        REPO / "scripts/bvmtools/kcl.py",
        METRIC_SPEC,
        Path(__file__),
        SOLVER,
    ]
    if m0 is not None:
        artifact_paths.append(m0.path)
    if s1 is not None:
        artifact_paths.append(s1.path)
    unique_paths: list[Path] = []
    seen: set[Path] = set()
    for path in source_paths + artifact_paths:
        if path.is_file() and path not in seen:
            unique_paths.append(path)
            seen.add(path)
    execution_head = None
    run_head_file = EXP / "logs/pre-run-head.txt"
    if run_head_file.is_file():
        execution_head = run_head_file.read_text(encoding="utf-8").strip()
    commands_file = EXP / "logs/commands.tsv"
    commands = commands_file.read_text(encoding="utf-8").splitlines() if commands_file.is_file() else []
    return {
        "task_id": "IMPORT_BVMSIM_QB_AND_STRICTLY_QUALIFY_V1",
        "stage": "A",
        "head_before_task": "22376a3f1a8c3cfd40a6f9afaf85da7b43e3c3f6",
        "execution_head_before_science_runs": execution_head,
        "git_snapshot_at_analysis": git_snapshot(REPO),
        "solver": solver_provenance(SOLVER, cwd=REPO),
        "source_files": [file_snapshot(path, relative_to=REPO) for path in source_paths if path.is_file()],
        "analysis_and_tool_files": [file_snapshot(path, relative_to=REPO) for path in unique_paths if path in artifact_paths],
        "commands_and_exit_records": commands,
        "raw_rewrite_policy": "historical BVMSim/data_tran.csv was not rewritten; M0 and S1 have separate raw paths",
        "bvm_authority_boundary": "BVMSim/bvm_cell.cir (R_JM1=8 ohm) is not canonical circuits/bvm/bvm_cell.cir (R_JM1=6 ohm)",
    }


def make_brief(result: dict[str, object]) -> str:
    migration = result["migration"]
    strict = result["strict"]
    classification = result["primary_classification"]
    quick = result["quick_label"]
    if strict.get("status") == "VALID":
        bj2 = strict["signals"]["BJ2"]  # type: ignore[index]
        read0 = scalar_phase_summary(bj2, "READ0")
        read1 = scalar_phase_summary(bj2, "READ1_RESPONSE")
        transport = result["transport_read1"]["stages"]  # type: ignore[index]
        transport_line = ", ".join(f"{stage}={item['clean_event_count']}" for stage, item in transport.items())
        kcl_note = "KCL 已计算并保存于 metrics.json。"
        observations = [
            f"M0 迁移等价性为 {migration['status']}；共享网格={migration.get('time_grid_exact')}，未插值。",
            f"S1 BJ2 READ0：complete segments={read0['complete_segment_count']}，clean separated={read0['clean_separated_event_count']}；READ1：complete segments={read1['complete_segment_count']}，clean separated={read1['clean_separated_event_count']}。",
            f"BJ2 READ1 端点相位位移={read1['phase_window'].get('endpoint_delta_turns')} turns；这是相位轨迹量，不单独等于 SFQ 数。",
            f"READ1 transport cell-minimum clean counts：{transport_line}。",
            f"主分类={classification}，Quick={quick}；额外/自发活动按窗口列在 metrics.json。",
            kcl_note,
        ]
    else:
        observations = [f"M0 迁移等价性为 {migration.get('status')}；S1 未进入科学运行。", "严格分析状态不完整，见 metrics.json。"]
    lines = [
        "# Stage A 结果摘要",
        "",
        "## 1. What changed",
        "",
        "仅将 BVMSim 活动 QB 封装迁移到 `circuits/qb/bq_cell_bvmsim_v1.cir`，子电路接口为 `BQ_BVMSIM_V1 IN OUT BIAS`；原 QB 内部 250-uA bias 以完全相同的 `I_QB_BIAS 0 QB_BIAS pwl(0 0 1p 250u)` 外置。",
        "",
        "## 2. What held fixed",
        "",
        "Stage A 保持 BVMSim 的 4-BVM、累积 sensing-line、BVMout、原始刺激、QB 元件值、六级原始 `BVMSim/library_josim/jtl2.cir`、10-ohm 终端负载和 200-ps 停止时间。BVMSim BVM 不是 canonical BVM authority：BVMSim 的 `R_JM1=8 Ω`，canonical `circuits/bvm/bvm_cell.cir` 为 `6 Ω`；本阶段没有替换它。",
        "",
        "## 3. Why tested",
        "",
        "区分真实分离、重捕获的多 SFQ 事件与一条连续多圈 running phase trajectory；全窗口约 4 turns 不会被自动报告为 4 个 SFQ。",
        "",
        "## 4. What happened",
        "",
    ]
    lines.extend(f"- {item}" for item in observations[:6])
    lines.extend(
        [
            "",
            "## 5. Physical meaning",
            "",
            f"在本 BVMSim exploratory fixture 和本阶段 strict task-local 口径下，当前主分类是 `{classification}`（Quick `{quick}`）。它只描述本次仿真的局部相位/同结电压面积与 JTL 逐级关系；它不把局部相位圈直接升级为闭环 fluxoid 或硬件 SFQ 计数。",
            "",
            "## 6. What it does NOT prove",
            "",
            "不证明 canonical BVM compatibility、single-BVM compatibility、一个 BVM contribution 对应一个 SFQ、timestep convergence、process margin、T1 compatibility、paper mechanism identity 或唯一 QB operating mechanism；也不是 Formal PASS。",
            "",
            "## 7. Current status",
            "",
            "`AWAITING_USER_REVIEW`。本阶段没有自动开始 Stage B，前序 replay Quick 的 human gate 也未被本授权改写。",
            "",
            "## 8. Possible next options (not executed)",
            "",
            "- 用户先审阅本阶段 raw、metrics、结果摘要和关键图。",
            "- 如确有必要，另行授权并预注册 `CANONICAL_BVM_TO_BVMSIM_QB_QUICK_V1`。",
            "- 另行审查 BVMSim QB 的局部工作点和机制；本阶段未做参数扫掠。",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    out_metrics = EXP / "analysis/metrics.json"
    out_provenance = EXP / "analysis/provenance.json"
    (EXP / "migration").mkdir(parents=True, exist_ok=True)
    (EXP / "strict").mkdir(parents=True, exist_ok=True)
    (EXP / "analysis").mkdir(parents=True, exist_ok=True)

    result: dict[str, object] = {
        "task_id": "IMPORT_BVMSIM_QB_AND_STRICTLY_QUALIFY_V1",
        "stage": "A",
        "artifact_status": "VALID",
        "analysis_status": "VALID",
        "raw_files": {},
    }
    try:
        hist = read_csv(HISTORICAL_RAW)
        m0 = read_csv(M0_RAW)
        result["raw_files"] = {
            "historical": hist.qa(),
            "m0": m0.qa(),
        }
        migration = compare_migration(hist, m0)
        result["migration"] = migration
        write_json(EXP / "migration/m0_comparison.json", migration)
    except Exception as exc:  # pragma: no cover - recorded as artifact invalidity
        result["artifact_status"] = "INVALID"
        result["analysis_status"] = "INVALID"
        result["migration"] = {"status": "ANALYSIS_INVALID", "error": repr(exc)}
        result["strict"] = {"status": "NOT_RUN"}
        result["primary_classification"] = "ANALYSIS_INVALID"
        result["quick_label"] = "QUICK_INVALID"
        result["provenance"] = provenance(None, None)
        write_json(out_metrics, result)
        write_json(out_provenance, result["provenance"])
        (EXP / "RESULT_BRIEF.md").write_text(make_brief(result), encoding="utf-8")
        return 1

    if migration["status"] != "PASS" or not S1_RAW.is_file():
        result["strict"] = {
            "status": "NOT_RUN",
            "reason": "S1 is conditional on M0 PASS and was not available at analysis time",
        }
        result["primary_classification"] = "MIGRATION_INVALID" if migration["status"] != "PASS" else "NO_CLEAR_STRICT_CLASSIFICATION"
        result["quick_label"] = quick_label(result["primary_classification"])
        result["provenance"] = provenance(m0, None)
        write_json(out_metrics, result)
        write_json(out_provenance, result["provenance"])
        (EXP / "RESULT_BRIEF.md").write_text(make_brief(result), encoding="utf-8")
        return 0 if migration["status"] == "PASS" else 1

    try:
        s1 = read_csv(S1_RAW)
        missing = required_signal_check(s1)
        if missing:
            raise RuntimeError(f"S1 is missing required observables: {missing}")
        result["raw_files"]["s1"] = s1.qa()  # type: ignore[index]
        records = all_signal_records(s1, "s1")
        strict: dict[str, object] = {
            "status": "VALID",
            "required_observables": "PASS",
            "phase_area_semantics": "shared bvmtools.sfq strict_event_summary; full-trace segments associated by onset",
            "signals": records,
            "kcl": analyze_kcl(s1),
            "read0": {
                "BJ2": scalar_phase_summary(records["BJ2"], "READ0"),
            },
        }
        strict["transport_read0"] = transport_summary(records, "READ0")
        result["strict"] = strict
        result["transport_read1"] = transport_summary(records, "READ1_RESPONSE")
        result["transport_read0"] = strict["transport_read0"]
        classification, reason = classify(migration, strict, result["transport_read1"])  # type: ignore[arg-type]
        result["primary_classification"] = classification
        result["classification_reason"] = reason
        result["quick_label"] = quick_label(classification)
        result["provenance"] = provenance(m0, s1)
        write_json(EXP / "strict/s1_strict.json", strict)
        write_json(out_metrics, result)
        write_json(out_provenance, result["provenance"])
        (EXP / "RESULT_BRIEF.md").write_text(make_brief(result), encoding="utf-8")
        return 0
    except Exception as exc:  # pragma: no cover - recorded as analysis invalidity
        result["analysis_status"] = "INVALID"
        result["strict"] = {"status": "INVALID", "error": repr(exc)}
        result["primary_classification"] = "ANALYSIS_INVALID"
        result["classification_reason"] = repr(exc)
        result["quick_label"] = "QUICK_INVALID"
        result["provenance"] = provenance(m0, None)
        write_json(out_metrics, result)
        write_json(out_provenance, result["provenance"])
        (EXP / "RESULT_BRIEF.md").write_text(make_brief(result), encoding="utf-8")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
