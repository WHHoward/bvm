#!/usr/bin/env python3
"""Analyze the independent BVMSim timestep/event-count convergence Quick.

The analyzer keeps three evidence layers separate:

* exact stored-grid/artifact checks;
* same-junction phase/area segment and reusable strict event-list arithmetic;
* cautious transport/source interpretation.

It never treats a whole-window phase displacement as an SFQ count.
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

from bvmtools.compare import compare_series  # noqa: E402
from bvmtools.kcl import kcl_window_metrics, linear_kcl_residual  # noqa: E402
from bvmtools.phase import continuous_unwrap, phase_window_metrics, window_indices  # noqa: E402
from bvmtools.raw import RawTrace, read_csv  # noqa: E402
from bvmtools.sfq import StrictLocalEventSpec, strict_event_list  # noqa: E402
from bvmtools.waveform import waveform_metrics  # noqa: E402


HISTORICAL_RAW = REPO / "BVMSim/data_tran.csv"
STAGE_A_M0_RAW = REPO / "test/exploration/bvmsim-qb-strict-qualification-v1-20260902/raw/m0/run-01.csv"
STAGE_A_S1_RAW = REPO / "test/exploration/bvmsim-qb-strict-qualification-v1-20260902/raw/s1/run-01.csv"
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

RUNS: "OrderedDict[str, Path]" = OrderedDict(
    (
        ("T100", EXP / "runs/T100/attempt-02/raw.csv"),
        ("T050", EXP / "runs/T050/attempt-01/raw.csv"),
        ("T025", EXP / "runs/T025/attempt-01/raw.csv"),
        ("T0125", EXP / "runs/T0125/attempt-01/raw.csv"),
        ("T100_FULL", EXP / "runs/T100_FULL/attempt-01/raw.csv"),
    )
)

NOMINAL_DT_PS = {"T100": 0.1, "T050": 0.05, "T025": 0.025, "T0125": 0.0125, "T100_FULL": 0.1}
DECKS = {
    "T100": EXP / "migrated/T100.cir",
    "T050": EXP / "migrated/T050.cir",
    "T025": EXP / "migrated/T025.cir",
    "T0125": EXP / "migrated/T0125.cir",
    "T100_FULL": EXP / "migrated/T100_FULL.cir",
}

QB_SIGNALS = OrderedDict(
    (
        ("BJs", ("P(BJS|XBQ1)", "V(BJS|XBQ1)")),
        ("BJ1", ("P(BJ1|XBQ1)", "V(BJ1|XBQ1)")),
        ("BJ2", ("P(BJ2|XBQ1)", "V(BJ2|XBQ1)")),
    )
)
JTL_SIGNALS = OrderedDict(
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

ALL_JUNCTIONS = OrderedDict()
ALL_JUNCTIONS.update(QB_SIGNALS)
for stage, cells in JTL_SIGNALS.items():
    for junction, names in cells.items():
        ALL_JUNCTIONS[f"{stage}.{junction}"] = names

STRICT_TOLERANCE = {
    "phase_area_residual_abs_floor_turns": 0.05,
    "phase_area_residual_relative": 0.10,
    "complete_min_turns": 1.0,
    "clean_upper_turns": 1.15,
    "post_range_max_turns": 1.0,
    "post_tail_p2p_max_turns": 0.25,
}
SCAN_WINDOW_S = (0.0, 200.0e-12)
READ1_WINDOW_S = (110.0e-12, 170.0e-12)
READ1_LABEL = "READ1_RESPONSE"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def json_write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def ps(value_s: float) -> float:
    return float(value_s) * 1.0e12


def signal(trace: RawTrace, name: str) -> tuple[float, ...]:
    try:
        return trace.column(name)  # type: ignore[return-value]
    except KeyError:
        candidates = [header for header in trace.headers if header.casefold() == name.casefold()]
        if len(candidates) != 1:
            raise
        return trace.column(candidates[0])  # type: ignore[return-value]


def strict_spec(raw_path: Path, phase_name: str, voltage_name: str, run_id: str) -> StrictLocalEventSpec:
    return StrictLocalEventSpec.from_mapping(
        {
            "id": "bvmsim-stagea-timestep-strict-event-v1",
            "scope": "task-local",
            "status": "FROZEN",
            "provenance_status": "POST_HOC_EXPLORATORY",
            "mapping_status": "DECLARED_DIRECT_SAME_JJ_PV",
            "phase_column": phase_name,
            "voltage_column": voltage_name,
            "branch_endpoints": f"JoSIM direct branch orientation for {phase_name} / {voltage_name}",
            "voltage_to_phase_sign": 1,
            "reporting_direction": 1,
            "run_id": run_id,
            "window_id": "full-scan-with-window-association-0-50-70-90-110-170-200ps",
            "raw_sha256": sha256(raw_path),
            "metric_spec": {
                "path": "docs/research/METRIC_SPEC_V2.md",
                "version": "2.0.0",
                "sha256": sha256(METRIC_SPEC),
            },
            "tolerance": {
                "id": "bvmsim-stagea-timestep-task-local-strict-event-v1",
                "scope": "task-local",
                "status": "FROZEN",
                "provenance_status": "POST_HOC_EXPLORATORY",
                "evidence": "test/exploration/bvmsim-stagea-timestep-event-count-v1-20260902/experiment.yaml",
                **STRICT_TOLERANCE,
            },
            "compatibility_profile": "STRICT_EVENT_ANCHOR_COMPATIBILITY_V1",
        }
    )


def phase_window(trace: RawTrace, phase: tuple[float, ...], bounds_ps: tuple[float, float]) -> dict[str, object]:
    try:
        return phase_window_metrics(
            trace.time,
            phase,
            (bounds_ps[0] * 1.0e-12, bounds_ps[1] * 1.0e-12),
        )
    except ValueError as exc:
        return {"status": "INSUFFICIENT_SAMPLES", "reason": str(exc), "window_ps": list(bounds_ps)}


def add_voltage_diagnostics(
    event_list: dict[str, object],
    trace: RawTrace,
    voltage: tuple[float, ...],
) -> None:
    """Attach descriptive voltage pulse data to shared segment records."""

    for item in event_list["segments"]:  # type: ignore[index]
        start = int(item["start_index"])
        end = int(item["end_index"])
        values = voltage[start : end + 1]
        metrics = waveform_metrics(trace.time[start : end + 1], values)
        item["voltage_min_v"] = float(metrics["minimum"])
        item["voltage_max_v"] = float(metrics["maximum"])
        item["voltage_peak_abs_v"] = float(metrics["max_abs"])
        item["voltage_peak_time_ps"] = ps(float(metrics["peak_time"]))
        item["voltage_signed_area_wb"] = float(item["raw_area_wb"])


def compact_event_list(event_list: dict[str, object]) -> dict[str, object]:
    """Keep one segment table; avoid serializing the same records three times."""

    keep = (
        "mode",
        "claim_ceiling",
        "event_window_s",
        "scan_window_s",
        "retrap_max_p2p_turns",
        "spec",
        "segments",
        "complete_segment_count",
        "clean_separated_event_count",
        "complete_event_onset_times_ps",
        "clean_event_onset_times_ps",
        "clean_event_directions",
        "largest_segment_turns",
        "any_segment_spans_over_1_15_turns",
        "continuous_multi_turn_running",
    )
    return {key: event_list[key] for key in keep}


def event_summary_for_window(
    trace: RawTrace,
    phase_name: str,
    voltage_name: str,
    raw_path: Path,
    run_id: str,
    label: str,
    bounds_ps: tuple[float, float],
) -> dict[str, object]:
    phase = signal(trace, phase_name)
    voltage = signal(trace, voltage_name)
    event_list = strict_event_list(
        trace.time,
        phase,
        voltage,
        event_window_s=(bounds_ps[0] * 1.0e-12, bounds_ps[1] * 1.0e-12),
        scan_window_s=SCAN_WINDOW_S,
        retrap_max_p2p_turns=STRICT_TOLERANCE["post_tail_p2p_max_turns"],
        spec=strict_spec(raw_path, phase_name, voltage_name, f"{run_id}/{label}"),
    )
    add_voltage_diagnostics(event_list, trace, voltage)
    event_list = compact_event_list(event_list)
    selected_phase = phase_window(trace, phase, bounds_ps)
    window_segments = [
        item
        for item in event_list["segments"]  # type: ignore[index]
        if bool(item["onset_in_event_window"])
    ]
    candidates = [
        {
            "segment_ordinal": int(item["ordinal"]),
            "start_time_ps": float(item["start_time_ps"]),
            "end_time_ps": float(item["end_time_ps"]),
            "direction": int(item["direction"]),
            "phase_turns": float(item["phase_reported_turns"]),
            "area_turns": float(item["area_reported_turns"]),
            "phase_area_residual_turns": float(item["phase_area_residual_turns"]),
            "complete_segment": bool(item["complete_segment"]),
            "clean_separated_event": bool(item["clean_separated_event"]),
            "voltage_peak_abs_v": float(item["voltage_peak_abs_v"]),
            "voltage_peak_time_ps": float(item["voltage_peak_time_ps"]),
        }
        for item in event_list["segments"]  # type: ignore[index]
        if bool(item["onset_in_event_window"]) and abs(float(item["phase_reported_turns"])) >= 0.2
    ]
    return {
        "window_ps": list(bounds_ps),
        "phase_window": selected_phase,
        "complete_segment_count": event_list["complete_segment_count"],
        "clean_separated_event_count": event_list["clean_separated_event_count"],
        "complete_event_onset_times_ps": event_list["complete_event_onset_times_ps"],
        "clean_event_onset_times_ps": event_list["clean_event_onset_times_ps"],
        "clean_event_directions": event_list["clean_event_directions"],
        "largest_segment_turns": max(
            (abs(float(item["phase_reported_turns"])) for item in window_segments),
            default=0.0,
        ),
        "any_segment_spans_over_1_15_turns": any(
            bool(item["continuous_multiturn_segment"]) for item in window_segments
        ),
        "continuous_multi_turn_running": any(
            bool(item["continuous_multiturn_segment"]) for item in window_segments
        ),
        "large_segment_candidates": candidates,
        "event_list": event_list,
    }


def analyze_signal(
    trace: RawTrace,
    raw_path: Path,
    run_id: str,
    label: str,
    phase_name: str,
    voltage_name: str,
) -> dict[str, object]:
    windows: dict[str, object] = OrderedDict()
    for window_label, bounds_ps in WINDOWS_PS.items():
        summary = event_summary_for_window(
            trace,
            phase_name,
            voltage_name,
            raw_path,
            run_id,
            window_label,
            bounds_ps,
        )
        # The full event list is identical in scan scope; retain the detailed
        # list only for READ1 to keep metrics.json focused.
        if window_label != READ1_LABEL:
            summary = {key: value for key, value in summary.items() if key != "event_list"}
        windows[window_label] = summary
    read1 = windows[READ1_LABEL]
    return {
        "label": label,
        "phase_column": phase_name,
        "voltage_column": voltage_name,
        "windows": windows,
        "read1_segments": read1["event_list"]["segments"],  # type: ignore[index]
        "raw_units": {"phase": "rad", "voltage": "V"},
        "phase_turn_conversion": "continuous_unwrap(rad)/(2*pi)",
        "event_claim_ceiling": "local same-junction only; not downstream transport",
    }


def required_missing(trace: RawTrace) -> list[str]:
    required: list[str] = [
        "I(BVMOUT)",
        "V(QBIN)",
        "V(QBOUT)",
        "I(BJS|XBQ1)",
        "P(BJS|XBQ1)",
        "V(BJS|XBQ1)",
        "I(BJ1|XBQ1)",
        "P(BJ1|XBQ1)",
        "V(BJ1|XBQ1)",
        "I(BJ2|XBQ1)",
        "P(BJ2|XBQ1)",
        "V(BJ2|XBQ1)",
    ]
    for _, pair in ALL_JUNCTIONS.items():
        required.extend(pair)
    return [name for name in required if not any(header.casefold() == name.casefold() for header in trace.headers)]


def kcl_metrics(trace: RawTrace) -> dict[str, object]:
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
    result: dict[str, object] = {
        "orientation": {
            "convention": "positive current is from first listed deck node to second",
            "node_2": "BJs 1->2 enters; BJ1 2->0, RJ1 2->0, L1 2->BIAS leave",
            "node_bias": "L1 2->BIAS and I_QB_BIAS 0->BIAS enter; L2 BIAS->4 leaves",
            "node_4": "L2 BIAS->4 enters; BJ2/RJ2 4->0 and L3 4->OUT leave",
        },
        "equations": OrderedDict(),
    }
    for label, (coefficients, equation) in equations.items():
        residual = linear_kcl_residual(
            {name: branches[name] for name in coefficients},
            coefficients,
        )
        windows: dict[str, object] = {}
        for window_label, bounds_ps in WINDOWS_PS.items():
            try:
                windows[window_label] = kcl_window_metrics(
                    trace.time,
                    residual,
                    (bounds_ps[0] * 1.0e-12, bounds_ps[1] * 1.0e-12),
                )
            except ValueError as exc:
                windows[window_label] = {"status": "INSUFFICIENT_SAMPLES", "reason": str(exc)}
        result["equations"][label] = {  # type: ignore[index]
            "equation": equation,
            "coefficients": coefficients,
            "windows": windows,
        }
    return result


def exact_overlap_values(
    a: RawTrace,
    b: RawTrace,
    values_a: tuple[float, ...],
    values_b: tuple[float, ...],
) -> tuple[list[float], list[float], int]:
    b_index = {time: index for index, time in enumerate(b.time)}
    pairs = [(index, b_index[time]) for index, time in enumerate(a.time) if time in b_index]
    return (
        [a.time[index] for index, _ in pairs],
        [values_a[index] for index, _ in pairs],
        [values_b[index] for _, index in pairs],
    )


def compare_exact_signal(
    a: RawTrace,
    b: RawTrace,
    name: str,
    *,
    occurrence_a: int | None = None,
    occurrence_b: int | None = None,
) -> dict[str, object]:
    values_a = a.column(name, occurrence=occurrence_a)  # type: ignore[assignment]
    values_b = b.column(name, occurrence=occurrence_b)  # type: ignore[assignment]
    common_time, aligned_a, aligned_b = exact_overlap_values(a, b, values_a, values_b)
    if not common_time:
        return {"status": "NO_EXACT_OVERLAP", "signal": name}
    comparison = compare_series(
        common_time,
        aligned_a,
        common_time,
        aligned_b,
        interpolation=None,
    )
    comparison.pop("pointwise_difference", None)
    comparison.update(
        {
            "signal": name,
            "occurrence_a": occurrence_a,
            "occurrence_b": occurrence_b,
            "overlap_time_start_ps": ps(common_time[0]),
            "overlap_time_end_ps": ps(common_time[-1]),
            "overlap_sample_count": len(common_time),
            "comparison": "exact stored timestamp overlap; no interpolation",
        }
    )
    return comparison


def reference_comparison() -> dict[str, object]:
    historical = read_csv(HISTORICAL_RAW)
    stage_m0 = read_csv(STAGE_A_M0_RAW)
    stage_s1 = read_csv(STAGE_A_S1_RAW)
    t100 = read_csv(RUNS["T100"])
    t025 = read_csv(RUNS["T025"])
    t100_full = read_csv(RUNS["T100_FULL"])

    migration_signals = [
        ("I(BVMOUT)", None, None),
        ("V(QBIN)", None, None),
        ("V(QBOUT)", None, None),
        ("V(O1)", None, None),
        ("V(O2)", 0, None),
        ("V(O2)", 1, None),
        ("P(BJ1|XBQ1)", None, None),
        ("P(B01|XJTL1_1)", None, None),
    ]
    historical_t100 = [
        compare_exact_signal(historical, t100, name, occurrence_a=occ_a, occurrence_b=occ_b)
        for name, occ_a, occ_b in migration_signals
    ]
    stage_m0_t100 = [
        compare_exact_signal(stage_m0, t100, name)
        for name in ("I(BVMOUT)", "V(QBIN)", "V(QBOUT)", "V(O1)", "V(O2)", "P(BJ1|XBQ1)", "P(B01|XJTL1_1)")
    ]
    stage_s1_t025 = [
        compare_exact_signal(stage_s1, t025, name)
        for name in ("I(BVMOUT)", "V(QBIN)", "V(QBOUT)", "V(O1)", "V(O2)", "P(BJ1|XBQ1)", "P(BJ2|XBQ1)", "P(B01|XJTL1_1)")
    ]
    t100_t100_full = [
        compare_exact_signal(t100, t100_full, name)
        for name in ("I(BVMOUT)", "V(QBIN)", "V(QBOUT)", "P(BJ1|XBQ1)", "P(BJ2|XBQ1)", "P(B01|XJTL1_1)")
    ]
    return {
        "historical_vs_new_T100": historical_t100,
        "stage_a_M0_vs_new_T100": stage_m0_t100,
        "stage_a_S1_vs_new_T025": stage_s1_t025,
        "new_T100_print_start_vs_T100_FULL": t100_t100_full,
        "historical_duplicate_policy": "V(O2) occurrence 0 and 1 compared explicitly; no pandas-style collapse",
    }


def transport_summary(signals: dict[str, dict[str, object]]) -> dict[str, object]:
    read1_bj2 = signals["BJ2"]["windows"][READ1_LABEL]
    stages: OrderedDict[str, dict[str, object]] = OrderedDict()
    stages["BJ2"] = {
        "junction": "BJ2",
        "local_clean_event_count": read1_bj2["clean_separated_event_count"],
        "complete_segment_count": read1_bj2["complete_segment_count"],
        "polarity": read1_bj2["clean_event_directions"],
        "onset_times_ps": read1_bj2["clean_event_onset_times_ps"],
        "net_turns": read1_bj2["phase_window"].get("endpoint_delta_turns"),
        "continuous_running": read1_bj2["continuous_multi_turn_running"],
        "transport_identity_status": "SOURCE_JUNCTION_ONLY",
    }
    previous_onsets = list(read1_bj2["clean_event_onset_times_ps"])
    for stage in JTL_SIGNALS:
        b01 = signals[f"{stage}.B01"]["windows"][READ1_LABEL]
        b02 = signals[f"{stage}.B02"]["windows"][READ1_LABEL]
        b01_count = int(b01["clean_separated_event_count"] or 0)
        b02_count = int(b02["clean_separated_event_count"] or 0)
        count = min(b01_count, b02_count)
        onsets = [float(value) for value in b01["clean_event_onset_times_ps"][:count]]
        previous_for_latency = previous_onsets[:count]
        latencies = (
            [onset - prior for prior, onset in zip(previous_for_latency, onsets)]
            if count and len(previous_for_latency) == count
            else None
        )
        stages[stage] = {
            "junction": "B01/B02 cell conservative minimum",
            "local_stage_summary_count": count,
            "local_stage_summary_definition": "min(B01_clean_event_count, B02_clean_event_count); no event identity matching",
            "transport_identity_status": "NO_EVENT_IDENTITY_MATCH",
            "B01_clean_event_count": b01_count,
            "B02_clean_event_count": b02_count,
            "B01_complete_segment_count": b01["complete_segment_count"],
            "B02_complete_segment_count": b02["complete_segment_count"],
            "polarity": sorted(set(int(value) for value in b01["clean_event_directions"][:count] + b02["clean_event_directions"][:count])),
            "onset_times_ps": onsets,
            "B01_onset_times_ps": b01["clean_event_onset_times_ps"],
            "B02_onset_times_ps": b02["clean_event_onset_times_ps"],
            "latency_from_previous_stage_ps": latencies,
            "net_turns_B01": b01["phase_window"].get("endpoint_delta_turns"),
            "net_turns_B02": b02["phase_window"].get("endpoint_delta_turns"),
            "discrete_identity_ordered": all(a <= b for a, b in zip(onsets, onsets[1:])),
        }
        previous_onsets = onsets
    return {
        "window": READ1_LABEL,
        "stages": stages,
        "transport_claim_status": "NOT_ESTABLISHED",
        "transport_count_warning": "stage counts are local B01/B02 summaries, not conserved identities",
    }


def candidate_ladder(record: dict[str, object]) -> list[dict[str, object]]:
    candidates = []
    for order, item in enumerate(
        [
            item
            for item in record["windows"][READ1_LABEL]["event_list"]["segments"]
            if bool(item["onset_in_event_window"]) and abs(float(item["phase_reported_turns"])) >= 0.5
        ],
        start=1,
    ):
        candidates.append(
            {
                "candidate_order": order,
                "start_time_ps": float(item["start_time_ps"]),
                "end_time_ps": float(item["end_time_ps"]),
                "direction": int(item["direction"]),
                "phase_turns": float(item["phase_reported_turns"]),
                "area_turns": float(item["area_reported_turns"]),
                "phase_area_residual_turns": float(item["phase_area_residual_turns"]),
                "complete_segment": bool(item["complete_segment"]),
                "clean_separated_event": bool(item["clean_separated_event"]),
                "event_index": item["event_index"],
                "event_window_event_index": item.get("event_window_event_index"),
            }
        )
    return candidates


def fifth_candidate_ladder(signals: dict[str, dict[str, object]]) -> dict[str, object]:
    order = ["BJ2"] + [f"JTL{stage}.B01" for stage in range(1, 7)] + [f"JTL{stage}.B02" for stage in range(1, 7)]
    ladder = {name: candidate_ladder(signals[name]) for name in order}
    return {
        "definition": "ladder is per-junction descriptive ordering of phase segments >=0.5 turns; it is not a cross-junction time order, event identity, causal origin, or event count",
        "ladder": ladder,
        "candidate_caveat": "candidate order is descriptive per junction only; a fifth segment is not evidence of a fifth clean BJ2 event or of causal propagation",
    }


def classify(signals: dict[str, dict[str, object]], transport: dict[str, object]) -> tuple[str, str]:
    bj2 = signals["BJ2"]
    read1 = bj2["windows"][READ1_LABEL]
    read0 = bj2["windows"]["READ0"]
    stage_counts = [
        int(
            transport["stages"][stage].get(
                "local_stage_summary_count",
                transport["stages"][stage].get("local_clean_event_count", 0),
            )
            or 0
        )
        for stage in ("BJ2", "JTL1", "JTL2", "JTL3", "JTL4", "JTL5", "JTL6")
    ]
    extra_complete = 0
    for name in ("BJ2",) + tuple(f"JTL{stage}.B01" for stage in range(1, 7)):
        for window_label in WINDOWS_PS:
            if window_label == READ1_LABEL:
                continue
            count = signals[name]["windows"][window_label]["complete_segment_count"]
            extra_complete += int(count or 0)
    if bool(read1["continuous_multi_turn_running"]):
        return "CONTINUOUS_MULTI_TURN_RUNNING_STATE", "BJ2 contains a finite approximately-four-turn continuous segment, followed by a sub-unit residual and later settling tail; strict retrap/bounded completion for the main segment is not asserted, this label does not mean unbounded free running, and net turns are not separated event count"
    if extra_complete > 0 or int(read0["complete_segment_count"] or 0) > 0:
        return "SELECTIVITY_OR_OVERDRIVE_FAILURE", "complete local output activity is present outside the intended READ1 association window"
    if int(read1["clean_separated_event_count"] or 0) > 0 and min(stage_counts[1:]) < int(read1["clean_separated_event_count"] or 0):
        return "LOCAL_MULTI_SFQ_WITH_TRANSPORT_LOSS", "local clean BJ2 events are not preserved through the full JTL chain"
    if int(read1["clean_separated_event_count"] or 0) > 1:
        return "OTHER_SEPARATED_MULTI_SFQ_TRANSPORT_SUPPORTED", "separated multi-event local activity exists without the four-event strong conditions"
    if int(read1["complete_segment_count"] or 0) > 0:
        return "MULTI_PHASE_ACTIVITY_ONLY", "complete-looking activity lacks a clean separated interpretation"
    return "NO_CLEAR_STRICT_CLASSIFICATION", "no strict event/transport classification established"


def quick_label(classification: str) -> str:
    if classification == "FOUR_SEPARATED_SFQ_TRANSPORT_SUPPORTED":
        return "QUICK_PROMISING"
    if classification in {"CONTINUOUS_MULTI_TURN_RUNNING_STATE", "SELECTIVITY_OR_OVERDRIVE_FAILURE"}:
        return "QUICK_OPPOSITE"
    if classification in {"MIGRATION_INVALID", "ANALYSIS_INVALID"}:
        return "QUICK_INVALID"
    return "QUICK_AMBIGUOUS"


def analyze_run(run_id: str, raw_path: Path) -> dict[str, object]:
    trace = read_csv(raw_path)
    missing = required_missing(trace)
    signals: dict[str, dict[str, object]] = {}
    if not missing:
        for label, (phase_name, voltage_name) in ALL_JUNCTIONS.items():
            signals[label] = analyze_signal(trace, raw_path, run_id, label, phase_name, voltage_name)
    transport = transport_summary(signals) if not missing else {"status": "MISSING_OBSERVABLES"}
    classification, reason = classify(signals, transport) if not missing else ("ANALYSIS_INVALID", "required raw observables are missing")
    return {
        "run_id": run_id,
        "raw_path": str(raw_path.relative_to(REPO)),
        "raw_sha256": sha256(raw_path),
        "deck_path": str(DECKS[run_id].relative_to(REPO)),
        "deck_sha256": sha256(DECKS[run_id]),
        "nominal_timestep_ps": NOMINAL_DT_PS[run_id],
        "raw_qa": trace.qa(),
        "required_missing": missing,
        "artifact_status": "VALID" if not missing else "INVALID",
        "signals": signals,
        "transport_read1": transport,
        "event5_candidate_ladder": fifth_candidate_ladder(signals) if not missing else {"status": "UNAVAILABLE"},
        "kcl": kcl_metrics(trace) if not missing else {"status": "UNAVAILABLE"},
        "classification": classification,
        "classification_reason": reason,
        "quick_label": quick_label(classification),
    }


def compact_matrix_row(run_id: str, result: dict[str, object]) -> dict[str, object]:
    signals = result["signals"]
    transport = result["transport_read1"]
    bj2 = signals["BJ2"]["windows"][READ1_LABEL]
    jtl1 = transport["stages"]["JTL1"]
    jtl6 = transport["stages"]["JTL6"]
    return {
        "run_id": run_id,
        "timestep_ps": NOMINAL_DT_PS[run_id],
        "BJ2_READ_net_turns": bj2["phase_window"].get("endpoint_delta_turns"),
        "BJ2_complete_segment_count": bj2["complete_segment_count"],
        "BJ2_quantized_event_count": bj2["clean_separated_event_count"],
        "BJ2_largest_segment_turns": bj2["largest_segment_turns"],
        "BJ2_continuous_running": bj2["continuous_multi_turn_running"],
        "JTL1_B01_net_turns": jtl1.get("net_turns_B01"),
        "JTL1_B01_clean_event_count": jtl1.get("B01_clean_event_count"),
        "JTL1_local_stage_summary_count": jtl1.get("local_stage_summary_count"),
        "JTL6_B01_clean_event_count": jtl6.get("B01_clean_event_count"),
        "JTL6_B02_clean_event_count": jtl6.get("B02_clean_event_count"),
        "JTL6_local_stage_summary_count": jtl6.get("local_stage_summary_count"),
        "classification": result["classification"],
    }


def max_abs(values: Iterable[dict[str, object]], key: str) -> float:
    numeric = [abs(float(item[key])) for item in values if item.get(key) is not None]
    return max(numeric, default=0.0)


def make_first_divergence_report(audit: dict[str, object], results: dict[str, object]) -> str:
    pair_hist = audit["pairs"][0]
    pair_s1 = audit["pairs"][1]
    lines = [
        "# FIRST_DIVERGENCE",
        "",
        "本文件是新 JoSIM run 之前完成的 existing-raw-only 分歧审计与新矩阵结果的衔接记录。",
        "没有对历史 raw 做重写，也没有用插值制造共同采样点。",
        "",
        "## 既有 raw 审计（Observed）",
        "",
        f"- `BVMSim/data_tran.csv` 与 Stage-A M0 在预注册的 110–170 ps 窗口共同信号上没有检测到有意义分歧；最大相位轨迹差为 {max_abs(pair_hist['signals'], 'max_abs_phase_trajectory_difference_turns'):.6g} turn。",
        f"- Stage-A M0 与 Stage-A S1 的首个满足预注册持续规则的分歧为 `{pair_s1['first_meaningful_divergence']['signal']}`，约 {float(pair_s1['first_meaningful_divergence']['first_meaningful_divergence_ps']):.4f} ps。",
        "- 同一对 raw 中，JTL1 B01 的 phase-only 阈值交叉约为 117.3 ps，而 BJ2 的 phase+voltage paired 阈值交叉约为 120.4 ps；两者判据不同，不能据此推出 JTL 先导致 BJ2，也不能反向推出 BJ2 先导致 JTL。",
        "",
        "## 新矩阵的首个可见分歧（Observed）",
        "",
        "下表只比较 exact stored timestamp overlap，并用 T100 作为历史分辨率参照；它不是事件计数判据。",
        "",
        "| run | 与 T100 的最早共同窗口分歧备注 |",
        "|---|---|",
    ]
    base = results["runs"]["T100"]
    for run_id in ("T050", "T025", "T0125", "T100_FULL"):
        current = results["runs"][run_id]
        phase = current["signals"]["JTL1.B01"]["windows"][READ1_LABEL]["phase_window"].get("endpoint_delta_turns")
        bj2 = current["signals"]["BJ2"]["windows"][READ1_LABEL]["phase_window"].get("endpoint_delta_turns")
        lines.append(f"| {run_id} | READ1 JTL1.B01 net={float(phase):.6f} turn，BJ2 net={float(bj2):.6f} turn；详见 `metrics.json` 的 exact reference comparison。 |")
    lines.extend(
        [
            "",
            "## Attribution boundary",
            "",
            "- **Observed:** 新 T100 raw 的历史共同信号与历史 raw 完全一致；T100_FULL 在 45 ps 之后也与 T100 一致；T025 raw 与 Stage-A S1 一致。",
            "- **Derived:** 这排除了“仅仅因为 print-start 选项不同”作为 4→5 净相位分支差异的充分解释；同时支持把 `.tran` 控制行视为这组新旧 fixture 的唯一物理/数值改变。",
            "- **Not yet a final scientific conclusion:** 是否足以称为 timestep-induced branch change，以及该 branch change 是否具有稳定的物理事件意义，必须结合 event list、同-JJ phase/area、KCL 和 reviewer 审阅；不能因为 net turns 接近 4/5 就预先下结论。",
        ]
    )
    return "\n".join(lines) + "\n"


def make_event_convergence_report(results: dict[str, object]) -> str:
    rows = results["matrix_summary"]
    lines = [
        "# EVENT_COUNT_CONVERGENCE",
        "",
        "本 Quick 的关键边界：`net turns` 不是 SFQ event count。event count 使用 shared `bvmtools.sfq.strict_event_list` 的同一 JJ、同一连续单调 segment、同 segment `∫Vdt/Phi0`、相位 delta、方向和 retrap/bounded interval。",
        "",
        "## 矩阵摘要",
        "",
        "| timestep | BJ2 READ net turns | BJ2 complete segments | BJ2 clean separated events | JTL1 B01 net turns | JTL1 B01 clean | JTL1 local stage min | JTL6 local stage min | classification |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row['timestep_ps']} ps | {float(row['BJ2_READ_net_turns']):.6f} | {row['BJ2_complete_segment_count']} | {row['BJ2_quantized_event_count']} | {float(row['JTL1_B01_net_turns']):.6f} | {row['JTL1_B01_clean_event_count']} | {row['JTL1_local_stage_summary_count']} | {row['JTL6_local_stage_summary_count']} | {row['classification']} |"
        )
    lines.extend(
        [
            "",
            "## 重点 Observed",
            "",
            "- T100 的 BJ2 READ1 主段约为 4 turns；T050/T025/T0125 的 BJ2 READ1 净位移约为 5 turns，但这些细网格 run 的 BJ2 仍是一个约 4-turn 的连续主段加一个不足 1 turn 的后续段，而不是五个 clean separated events。",
            "- 细网格 run 的 JTL6 B02 可以出现五个约单位量级的完整段；这不等于 BJ2 已经产生五个 clean events。表中的 JTL1/JTL6 数值只是 B01/B02 的本地 stage summary，不是经过 event identity matching 的 transported count。",
            "- T100_FULL 的 45 ps 之后轨迹用于检查 print-start；它与 T100 一致时，print-start 不是解释 4→5 的充分原因。",
            "",
            "## 4→5 的当前证据边界",
            "",
            "**Observed:** 净相位分支随 `.tran` 从 0.1 ps 变为 0.05/0.025/0.0125 ps 而改变，并在更细三个网格保持接近 5；历史/T100 保持接近 4。",
            "",
            "**Derived but not yet accepted:** 在 fixture、source waveform、bias、load、拓扑和 solver binary 均固定且 T100/T100_FULL/T025 对照成立的前提下，这与 timestep-conditioned numerical branch-change candidate 一致。T050/T025/T0125 在约 5-turn 轨迹上具有定性稳定性，但这不是 timestep convergence proof，也不能排除数值积分路径或非线性分支选择。它更不能被改写成“4→5 个 SFQ”，因为 BJ2 的多-turn 主段没有 retrap 分隔。",
            "",
            "**Sol XHigh review 后仍 Unknown:** 这种 branch change 是否应被解释为有物理意义的 operating branch，还是数值积分路径/吸引域切换；以及不同 junction 上的第五候选是否具有可配对的 event identity。",
            "",
            "## 必须回答的问题",
            "",
            "1. 历史 BVMSim JTL1 B01 是否约 4 turns：是，且 new T100 逐点复现；这只是净位移。",
            "2. Stage-A 0.025 ps 是否约 5 turns：是，new T025 与 Stage-A S1 一致；这只是净位移。",
            "3. T100 是否回到约 4 turns：是。",
            "4. 第五候选段的描述性顺序在哪里：见 `metrics.json:event5_candidate_ladder`；该表按 junction 和固定展示顺序列出候选，不表示起源、前驱或因果顺序，且不能称为第五 clean BJ2 event。",
            "5. JTL 是否生成第五个还是仅传播：当前各 junction 的本地 phase/area 候选没有完成 event identity matching，因此既不能声称已传播，也不能排除 JTL 内部本地生成或重整形。",
            "6. event count 是否收敛：净 turns 在细网格具有定性稳定性，但没有预注册的误差阶/停止带，也没有形成“四个/五个”BJ2 收敛结论；必须以各 junction 计数表为准。",
            "7. 应信任 4、5 还是 INCONCLUSIVE：净相位分支可报告为历史/T100≈4、细网格≈5；作为 clean SFQ event count 或机制结论，当前应保持 INCONCLUSIVE/受 reviewer 限制。",
        ]
    )
    return "\n".join(lines) + "\n"


def make_brief(results: dict[str, object], reference: dict[str, object], audit: dict[str, object]) -> str:
    rows = results["matrix_summary"]
    return "\n".join(
        [
            "# RESULT_BRIEF",
            "",
            "## 1. What changed",
            "",
            "在完全相同的 4-BVM → BVMSim QB → 六级 JTL fixture 上，新建 T100/T050/T025/T0125/T100_FULL 独立 raw；仅改变 `.tran` 控制行，历史 raw 保持不变。",
            "",
            "## 2. What held fixed",
            "",
            "BVMSim historical BVM、四路 accumulated sensing line、active BVMSim QB、250 µA QB bias、原始 BVMSim JTL、10 Ω load、source waveform、stop time、共享 `jjmit` 与 solver binary 均固定。canonical BVM 未使用。",
            "",
            "## 3. Why tested",
            "",
            "区分历史约 4-turn 与 Stage-A 约 5-turn 的数值分支差异，且检查净相位位移是否真的由分离、re-trapped 的局部事件组成。",
            "",
            "## 4. What happened（最多六点）",
            "",
            f"- 新 T100 raw hash 与历史 `BVMSim/data_tran.csv` 不同列布局但数值共同信号逐点一致；T100_FULL 在 45 ps 之后与 T100 一致。",
            f"- T100 BJ2 READ1 net turns={float(rows[0]['BJ2_READ_net_turns']):.6f}；细网格 T025={float(rows[2]['BJ2_READ_net_turns']):.6f}、T0125={float(rows[3]['BJ2_READ_net_turns']):.6f}。",
            "- BJ2 的约 4/5-turn 位移由连续多-turn segment 主导，不应写成四个/五个 clean SFQ。",
            "- 细网格下游 JTL6 B02 存在第五个约单位量级完整段，但上游 BJ2 与 JTL1 B01 的事件身份不满足四个 clean separated transport 条件；各级计数仅作本地 stage summary。",
            "- KCL 使用 shared `bvmtools.kcl` 验证；详细残差和每个 junction 的 phase/area/event list 在 `analysis/metrics.json`。",
            "- 首个既有 raw 分歧是不同阈值下的 crossing：JTL1 B01 phase-only 约 117.3 ps，BJ2 phase+voltage paired 约 120.4 ps；不能由此推断因果先后。",
            "",
            "## 5. Physical meaning",
            "",
            "Observed 结论是：该固定 exploratory fixture 对 timestep 很敏感，并出现约 4 与约 5 turns 的数值轨迹分支。Sol XHigh reviewer 的结论是对 timestep-conditioned numerical branch-change candidate 部分支持（中等偏强），但仍不等于 timestep convergence、离散 SFQ count，或已证明 JTL 生成/传输了第五个 SFQ。",
            "",
            "## 6. What it does NOT prove",
            "",
            "不证明 canonical BVM compatibility、single-BVM compatibility、一个 BVM contribution 对应一个 SFQ、timestep convergence、process margin、T1 compatibility、paper mechanism identity 或 unique QB operating mechanism。",
            "",
            "## 7. Current status",
            "",
            "Sol XHigh reviewer 已完成审查：4→5 归因为 timestep-conditioned numerical branch-change candidate 仅部分支持；在用户 review 前保持 `AWAITING_USER_REVIEW`，不启动后续实验。",
            "",
            "## 8. Possible next options（不执行）",
            "",
            "1. 由用户决定是否把 branch-change 候选升级为 Candidate 级复核。",
            "2. 在重新授权后单独设计 event identity/transport 的受控 follow-up。",
            "3. 在重新授权后再考虑 canonical BVM 路线；本 Quick 不执行。",
            "",
            "## Evidence files",
            "",
            "- `analysis/EVENT_COUNT_CONVERGENCE.md`",
            "- `analysis/FIRST_DIVERGENCE.md`",
            "- `analysis/metrics.json`",
            "- `plots/RESULT_TIMESTEP_BJ2.html`",
            "- `plots/RESULT_TIMESTEP_JTL1.html`",
            "- `plots/RESULT_EVENT5_CANDIDATE_ORDER.html`",
            "",
        ]
    )


def solver_version() -> str:
    completed = subprocess.run([str(SOLVER), "--version"], capture_output=True, text=True, check=False)
    return completed.stdout.strip() or completed.stderr.strip()


def main() -> int:
    traces = {run_id: read_csv(path) for run_id, path in RUNS.items()}
    results = {run_id: analyze_run(run_id, path) for run_id, path in RUNS.items()}
    result_bundle: dict[str, object] = {
        "analysis_id": "bvmsim-stagea-timestep-event-count-convergence-v1",
        "analysis_status": "VALID" if all(item["artifact_status"] == "VALID" for item in results.values()) else "INVALID",
        "raw_parser": "scripts/bvmtools/raw.py; duplicate-preserving exact occurrence selection",
        "phase_arithmetic": "scripts/bvmtools.phase continuous_unwrap; turns=rad/(2*pi)",
        "event_arithmetic": "scripts/bvmtools.sfq.strict_event_list; same-JJ segment phase/area plus retrap",
        "windows_ps": {label: list(bounds) for label, bounds in WINDOWS_PS.items()},
        "matrix_summary": [compact_matrix_row(run_id, results[run_id]) for run_id in RUNS],
        "runs": results,
        "reference_comparison": reference_comparison(),
    }
    audit_path = EXP / "analysis/existing_raw_divergence.json"
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    result_bundle["existing_raw_divergence_audit"] = audit
    for run_id, result in results.items():
        result["event5_candidate_ladder"] = fifth_candidate_ladder(result["signals"])

    metrics_path = EXP / "analysis/metrics.json"
    json_write(metrics_path, result_bundle)
    json_write(EXP / "analysis/provenance.json", {
        "analysis_id": result_bundle["analysis_id"],
        "generated_at_local": subprocess.run(["date", "--iso-8601=seconds"], capture_output=True, text=True, check=False).stdout.strip(),
        "git_head": subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True, check=False).stdout.strip(),
        "git_status_short": subprocess.run(["git", "status", "--short", "--untracked-files=all"], cwd=REPO, capture_output=True, text=True, check=False).stdout.splitlines(),
        "solver": {"path": str(SOLVER.relative_to(REPO)), "version": solver_version(), "sha256": sha256(SOLVER)},
        "source_hashes": {
            "BVMSim/BQ.cir": sha256(REPO / "BVMSim/BQ.cir"),
            "BVMSim/bvm_cell.cir": sha256(REPO / "BVMSim/bvm_cell.cir"),
            "BVMSim/test_bvm_mixed_0.cir": sha256(REPO / "BVMSim/test_bvm_mixed_0.cir"),
            "BVMSim/data_tran.csv": sha256(HISTORICAL_RAW),
            "BVMSim/library_josim/jtl2.cir": sha256(REPO / "BVMSim/library_josim/jtl2.cir"),
            "BVMSim/run.sh": sha256(REPO / "BVMSim/run.sh"),
            "BVMSim/josim-plot.py": sha256(REPO / "BVMSim/josim-plot.py"),
            "circuits/models/jjmit.cir": sha256(REPO / "circuits/models/jjmit.cir"),
            "circuits/qb/bq_cell_bvmsim_v1.cir": sha256(REPO / "circuits/qb/bq_cell_bvmsim_v1.cir"),
            "circuits/bvm/bvm_cell.cir": sha256(REPO / "circuits/bvm/bvm_cell.cir"),
        },
        "template": {"path": "test/exploration/bvmsim-qb-strict-qualification-v1-20260902/migrated/m0_bvmsim_qb.cir", "sha256": sha256(REPO / "test/exploration/bvmsim-qb-strict-qualification-v1-20260902/migrated/m0_bvmsim_qb.cir")},
        "decks": {run_id: {"path": str(DECKS[run_id].relative_to(REPO)), "sha256": sha256(DECKS[run_id])} for run_id in RUNS},
        "raws": {run_id: {"path": str(path.relative_to(REPO)), "sha256": sha256(path)} for run_id, path in RUNS.items()},
        "analysis_tools": {
            "analysis/analyze_convergence.py": sha256(Path(__file__)),
            "analysis/independent_recheck.py": sha256(EXP / "analysis/independent_recheck.py"),
            "analysis/render_plots.py": sha256(EXP / "analysis/render_plots.py"),
            "analysis/audit_existing.py": sha256(EXP / "analysis/audit_existing.py"),
            "inputs/generate_decks.py": sha256(EXP / "inputs/generate_decks.py"),
            "scripts/bvmtools/raw.py": sha256(REPO / "scripts/bvmtools/raw.py"),
            "scripts/bvmtools/phase.py": sha256(REPO / "scripts/bvmtools/phase.py"),
            "scripts/bvmtools/sfq.py": sha256(REPO / "scripts/bvmtools/sfq.py"),
            "scripts/bvmtools/waveform.py": sha256(REPO / "scripts/bvmtools/waveform.py"),
            "scripts/bvmtools/compare.py": sha256(REPO / "scripts/bvmtools/compare.py"),
            "scripts/bvmtools/kcl.py": sha256(REPO / "scripts/bvmtools/kcl.py"),
            "scripts/josim-plot2.py": sha256(REPO / "scripts/josim-plot2.py"),
            "docs/research/METRIC_SPEC_V2.md": sha256(METRIC_SPEC),
            "test/tools/test_bvmtools.py": sha256(REPO / "test/tools/test_bvmtools.py"),
            "test/tools/test_strict_event_list.py": sha256(REPO / "test/tools/test_strict_event_list.py"),
        },
        "no_raw_rewrite": True,
        "canonical_bvm_used": False,
        "known_bvm_difference": "BVMSim/bvm_cell.cir R_JM1=8 ohm; circuits/bvm/bvm_cell.cir R_JM1=6 ohm",
    })
    (EXP / "analysis/FIRST_DIVERGENCE.md").write_text(make_first_divergence_report(audit, result_bundle), encoding="utf-8")
    (EXP / "analysis/EVENT_COUNT_CONVERGENCE.md").write_text(make_event_convergence_report(result_bundle), encoding="utf-8")
    (EXP / "RESULT_BRIEF.md").write_text(make_brief(result_bundle, result_bundle["reference_comparison"], audit), encoding="utf-8")
    (EXP / "analysis/human-gate.yaml").write_text(
        "state: AWAITING_USER_REVIEW\nuser_reviewed: false\nnext_step_authorized: false\nautomatic_next_experiment: false\nstage_b_authorized: false\nnext_action: STOP\nreview_required: Sol_XHigh_josim_architect\nreview_focus: challenge_4_to_5_timestep_branch_attribution\n",
        encoding="utf-8",
    )
    print(json.dumps({"metrics": str(metrics_path), "runs": len(results), "analysis_status": result_bundle["analysis_status"]}, indent=2))
    return 0 if result_bundle["analysis_status"] == "VALID" else 2


if __name__ == "__main__":
    raise SystemExit(main())
