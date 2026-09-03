#!/usr/bin/env python3
"""Analyze the six-state historical BVMSim position-closure experiment.

CSV parsing, phase/area arithmetic, waveform summaries, strict local event
lists, stimulus checks, static deck QA, and KCL arithmetic come from the
shared ``bvmtools`` package.  This file owns only the experiment's windows,
state association, comparison rules, and bounded exploratory interpretation.
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
from typing import Any, Mapping, Sequence


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

from bvmtools.deckqa import deck_qa  # noqa: E402
from bvmtools.kcl import kcl_window_metrics, linear_kcl_residual  # noqa: E402
from bvmtools.metrics import (  # noqa: E402
    burst_total_metrics,
    peak_timing_metrics,
    phase_area_consistency,
    phase_area_window,
    waveform_window_summary,
)
from bvmtools.phase import continuous_unwrap, phase_window_metrics, window_indices  # noqa: E402
from bvmtools.probes import (  # noqa: E402
    flatten_probe_labels,
    historical_bvm_array_probes,
    historical_bvm_probes,
    historical_jtl_probes,
    original_bvmsim_qb_probes,
)
from bvmtools.provenance import sha256_file  # noqa: E402
from bvmtools.raw import RawTrace, read_csv  # noqa: E402
from bvmtools.sfq import StrictLocalEventSpec, strict_event_list  # noqa: E402
from bvmtools.stimulus import (  # noqa: E402
    compare_stimuli,
    validate_bvm_write_read_protocol,
    validate_expected_plateau,
)


HISTORICAL_FIXTURE = REPO / "BVMSim/test_bvm_mixed_0.cir"
HISTORICAL_BVM = REPO / "BVMSim/bvm_cell.cir"
HISTORICAL_QB = REPO / "BVMSim/BQ.cir"
HISTORICAL_JTL = REPO / "BVMSim/library_josim/jtl2.cir"
METRIC_SPEC = REPO / "docs/research/METRIC_SPEC_V2.md"
SOLVER = REPO / "build/josim-cli"
PHASE_A_PARITY = REPO / (
    "test/exploration/research-workflow-tooling-consolidation-v1-20260903/"
    "parity/parity.json"
)
RENDERER = REPO / "scripts/josim-plot2.py"

STATES = ("0000", "1000", "0100", "0010", "0001", "1111")
WEIGHT_ONE_STATES = ("1000", "0100", "0010", "0001")
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
WRITE0_PLATEAU_S = (51.0e-12, 60.0e-12)
READ0_PLATEAU_S = (71.0e-12, 80.0e-12)
WRITE1_PLATEAU_S = (91.0e-12, 100.0e-12)
READ1_PLATEAU_S = (111.0e-12, 120.0e-12)
READ1_S = WINDOWS_S["READ1"]
SCAN_S = (0.0, 200.0e-12)

PLATEAU_TOLERANCE_A = 1.0e-9
PHASE_AREA_ABS_FLOOR = 0.05
PHASE_AREA_RELATIVE = 0.10
STATE_LEVEL_SIGN_MIN_TURNS = 0.25
STATE_STABILITY_MAX_P2P_TURNS = 0.25
RETRAP_MAX_P2P_TURNS = 0.25
INPUT_DIFFERENCE_TOLERANCE_UA = 0.1
STRICT_TOLERANCE = {
    "phase_area_residual_abs_floor_turns": PHASE_AREA_ABS_FLOOR,
    "phase_area_residual_relative": PHASE_AREA_RELATIVE,
    "complete_min_turns": 1.0,
    "clean_upper_turns": 1.15,
    "post_range_max_turns": 1.0,
    "post_tail_p2p_max_turns": RETRAP_MAX_P2P_TURNS,
}


def sha256(path: Path) -> str:
    return sha256_file(path)


def write_once(path: Path, value: Any) -> None:
    content = json.dumps(value, indent=2, ensure_ascii=False) + "\n"
    if path.exists():
        if path.read_text(encoding="utf-8") == content:
            return
        raise RuntimeError(f"refusing to overwrite analysis artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def relative(path: Path) -> str:
    return str(path.relative_to(REPO))


def signal(trace: RawTrace, label: str) -> tuple[float, ...]:
    return trace.column(label)  # type: ignore[return-value]


def window(name: str) -> tuple[float, float]:
    return WINDOWS_S[name]


def grid_facts(trace: RawTrace) -> dict[str, object]:
    steps = trace.dt
    return {
        "sample_count": trace.sample_count,
        "start_ps": trace.time[0] * 1.0e12,
        "end_ps": trace.time[-1] * 1.0e12,
        "dt_min_ps": min(steps) * 1.0e12,
        "dt_max_ps": max(steps) * 1.0e12,
        "uniform": all(step == steps[0] for step in steps),
        "interpolation": "none",
        "duplicate_columns": trace.duplicate_columns,
    }


def phase_area_fact(
    trace: RawTrace,
    phase_label: str,
    voltage_label: str,
    bounds_s: tuple[float, float],
) -> dict[str, object]:
    result = phase_area_window(
        trace.time,
        signal(trace, phase_label),
        signal(trace, voltage_label),
        bounds_s,
        include_segments=False,
    )
    result["phase_area_consistency"] = phase_area_consistency(
        float(result["phase_delta_turns"]),
        float(result["voltage_area_over_phi0"]),
        absolute_tolerance_turns=PHASE_AREA_ABS_FLOOR,
        relative_tolerance=PHASE_AREA_RELATIVE,
        relative_scale_floor_turns=1.0,
    )
    result["phase_column"] = phase_label
    result["voltage_column"] = voltage_label
    return result


def level_fact(trace: RawTrace, phase_label: str, bounds_s: tuple[float, float]) -> dict[str, object]:
    phase = signal(trace, phase_label)
    fact = phase_window_metrics(trace.time, phase, bounds_s)
    unwrapped = continuous_unwrap(phase)
    indices = window_indices(trace.time, *bounds_s)
    fact.update(
        {
            "phase_column": phase_label,
            "first_turns": unwrapped[indices[0]] / (2.0 * math.pi),
            "last_turns": unwrapped[indices[-1]] / (2.0 * math.pi),
            "raw_phase_unit": "rad",
            "display_conversion": "continuous_unwrap(rad)/(2*pi)",
        }
    )
    return fact


def compact_burst(result: dict[str, object]) -> dict[str, object]:
    return {
        key: result[key]
        for key in (
            "window_s",
            "phase_delta_rad",
            "phase_delta_turns",
            "voltage_area_wb",
            "voltage_area_over_phi0",
            "voltage_area_turns",
            "phase_area_residual_turns",
            "phase_area_consistency",
            "phase_min_turns",
            "phase_max_turns",
            "phase_p2p_turns",
            "sample_count",
            "window_first_ps",
            "window_last_ps",
            "raw_phase_unit",
            "display_conversion",
            "branch_orientation",
        )
        if key in result
    }


def event_spec(
    raw_path: Path,
    run_id: str,
    window_id: str,
    phase_label: str,
    voltage_label: str,
) -> StrictLocalEventSpec:
    return StrictLocalEventSpec.from_mapping(
        {
            "id": "bvmsim-4bvm-position-closure-strict-event-v1",
            "scope": "task-local",
            "status": "POST_HOC_EXPLORATORY",
            "provenance_status": "POST_HOC_EXPLORATORY",
            "mapping_status": "DECLARED_DIRECT_SAME_JJ_PV",
            "phase_column": phase_label,
            "voltage_column": voltage_label,
            "branch_endpoints": f"direct JoSIM branch orientation: {phase_label}",
            "voltage_to_phase_sign": 1,
            "reporting_direction": 1,
            "run_id": run_id,
            "window_id": window_id,
            "raw_sha256": sha256(raw_path),
            "metric_spec": {
                "path": relative(METRIC_SPEC),
                "version": "2.0.0",
                "sha256": sha256(METRIC_SPEC),
            },
            "tolerance": {
                "id": "bvmsim-4bvm-position-closure-strict-v1",
                "scope": "task-local",
                "status": "POST_HOC_EXPLORATORY",
                "provenance_status": "POST_HOC_EXPLORATORY",
                "evidence": relative(EXP / "experiment.yaml"),
                **STRICT_TOLERANCE,
            },
            "compatibility_profile": "STRICT_EVENT_ANCHOR_COMPATIBILITY_V1",
        }
    )


def compact_event_item(item: Mapping[str, object]) -> dict[str, object]:
    retrap = item.get("retrap_or_bounded_interval")
    return {
        "ordinal": item["ordinal"],
        "start_time_ps": item["start_time_ps"],
        "end_time_ps": item["end_time_ps"],
        "duration_ps": item["duration_ps"],
        "direction": item["direction"],
        "phase_reported_turns": item["phase_reported_turns"],
        "area_reported_turns": item["area_reported_turns"],
        "phase_area_residual_turns": item["phase_area_residual_turns"],
        "complete_segment": item["complete_segment"],
        "clean_band": item["clean_band"],
        "onset_in_event_window": item["onset_in_event_window"],
        "clean_separated_event": item["clean_separated_event"],
        "continuous_multiturn_segment": item["continuous_multiturn_segment"],
        "retrap_or_bounded_interval": retrap,
    }


def event_fact(
    trace: RawTrace,
    raw_path: Path,
    run_id: str,
    window_name: str,
    phase_label: str,
    voltage_label: str,
) -> dict[str, object]:
    result = strict_event_list(
        trace.time,
        signal(trace, phase_label),
        signal(trace, voltage_label),
        event_window_s=window(window_name),
        scan_window_s=SCAN_S,
        retrap_max_p2p_turns=RETRAP_MAX_P2P_TURNS,
        spec=event_spec(raw_path, run_id, window_name, phase_label, voltage_label),
    )
    segments = result["segments"]
    relevant = [
        compact_event_item(item)
        for item in segments  # type: ignore[union-attr]
        if abs(float(item["phase_reported_turns"])) >= 0.2
        or bool(item["complete_segment"])
        or bool(item["clean_separated_event"])
    ]
    return {
        "event_window": window_name,
        "phase_column": phase_label,
        "voltage_column": voltage_label,
        "segment_count_scanned": len(segments),  # type: ignore[arg-type]
        "complete_segment_count": result["complete_segment_count"],
        "clean_separated_event_count": result["clean_separated_event_count"],
        "complete_event_onset_times_ps": result["complete_event_onset_times_ps"],
        "clean_event_onset_times_ps": result["clean_event_onset_times_ps"],
        "clean_event_directions": result["clean_event_directions"],
        "largest_segment_turns": result["largest_segment_turns"],
        "any_segment_spans_over_1_15_turns": result["any_segment_spans_over_1_15_turns"],
        "continuous_multi_turn_running": result["continuous_multi_turn_running"],
        "segments_abs_turns_ge_0_2": relevant,
        "claim_ceiling": result["claim_ceiling"],
        "strict_spec": result["spec"],
    }


def waveform_fact(trace: RawTrace, label: str, bounds_s: tuple[float, float], unit: str) -> dict[str, object]:
    return {
        "label": label,
        **waveform_window_summary(trace.time, signal(trace, label), bounds_s, unit=unit),
    }


def peak_fact(trace: RawTrace, label: str, bounds_s: tuple[float, float], unit: str) -> dict[str, object]:
    return {
        "label": label,
        **peak_timing_metrics(trace.time, signal(trace, label), bounds_s, unit=unit),
    }


def bvm_observables(trace: RawTrace, instance: int) -> dict[str, object]:
    probes = historical_bvm_probes(instance)
    junctions: dict[str, object] = OrderedDict()
    for name in ("JM1", "JM2", "JS1", "JS2"):
        branch = probes[name]  # type: ignore[index]
        phase_label = branch["phase"]  # type: ignore[index]
        voltage_label = branch["voltage"]  # type: ignore[index]
        current_label = branch["current"]  # type: ignore[index]
        junctions[name] = {
            "phase_area": OrderedDict(
                (
                    (window_name, phase_area_fact(trace, phase_label, voltage_label, bounds_s))
                    for window_name, bounds_s in WINDOWS_S.items()
                )
            ),
            "current": OrderedDict(
                (
                    (window_name, waveform_fact(trace, current_label, bounds_s, "A"))
                    for window_name, bounds_s in WINDOWS_S.items()
                )
            ),
        }
    inductors: dict[str, object] = OrderedDict()
    for name in ("L_M1", "L_M2", "L_M3", "L_PM", "L_PSL"):
        current_label = probes[name]["current"]  # type: ignore[index]
        inductors[name] = OrderedDict(
            (
                (window_name, waveform_fact(trace, current_label, bounds_s, "A"))
                for window_name, bounds_s in WINDOWS_S.items()
            )
        )
    sl = probes["SL"]  # type: ignore[index]
    return {
        "instance": instance,
        "junctions": junctions,
        "inductor_currents": inductors,
        "SL": {
            "voltage": OrderedDict(
                (
                    (window_name, waveform_fact(trace, sl["voltage"], bounds_s, "V"))
                    for window_name, bounds_s in WINDOWS_S.items()
                )
            ),
            "current": OrderedDict(
                (
                    (window_name, waveform_fact(trace, sl["current"], bounds_s, "A"))
                    for window_name, bounds_s in WINDOWS_S.items()
                )
            ),
        },
    }


def state_closure(trace: RawTrace, state: str) -> dict[str, object]:
    bits: list[dict[str, object]] = []
    observed_bits: list[str | None] = []
    for instance, commanded in enumerate(state, start=1):
        jm1 = historical_bvm_probes(instance)["JM1"]  # type: ignore[index]
        write = phase_area_fact(trace, jm1["phase"], jm1["voltage"], window("WRITE1"))  # type: ignore[index]
        level = level_fact(trace, jm1["phase"], window("PRE_READ1"))  # type: ignore[index]
        delta = float(write["phase_delta_turns"])
        level_mean = float(level["mean_turns"])
        area_ok = bool(write["phase_area_consistency"]["phase_area_consistent"])  # type: ignore[index]
        stable = float(level["p2p_turns"]) <= STATE_STABILITY_MAX_P2P_TURNS
        if level_mean >= STATE_LEVEL_SIGN_MIN_TURNS:
            observed = "1"
        elif level_mean <= -STATE_LEVEL_SIGN_MIN_TURNS:
            observed = "0"
        else:
            observed = None
        observed_bits.append(observed)
        if observed is None:
            status = "INCONCLUSIVE_SIGN"
        elif not area_ok:
            status = "PHASE_AREA_MISMATCH"
        elif not stable:
            status = "PRE_READ_NOT_STABLE"
        elif observed != commanded:
            status = "OBSERVED_SIGN_MISMATCH"
        else:
            status = "OBSERVED_STATE_MATCH"
        bits.append(
            {
                "bvm": f"BVM{instance}",
                "commanded_bit": commanded,
                "observed_bit_basis": observed,
                "pre_read_jm1_level_mean_turns": level_mean,
                "write1_jm1_phase_delta_turns": delta,
                "write1_jm1_voltage_area_turns": write["voltage_area_over_phi0"],
                "write1_jm1_phase_area_consistency": write["phase_area_consistency"],
                "pre_read_jm1_level": level,
                "pre_read_stable": stable,
                "status": status,
            }
        )
    observed_state = "".join(bit if bit is not None else "?" for bit in observed_bits)
    complete = all(bit is not None for bit in observed_bits)
    matches = complete and observed_state == state
    stable = all(bool(item["pre_read_stable"]) for item in bits)
    if matches and stable:
        status = "OBSERVED_STATE_MATCH_AND_CLOSED"
    elif complete and not matches:
        status = "OBSERVED_STATE_MISMATCH"
    else:
        status = "OBSERVED_STATE_INCONCLUSIVE"
    return {
        "basis": "task-local BVM JM1 PRE_READ1 continuous-unwrapped phase level sign plus p2p stability",
        "commanded_state": state,
        "observed_state_basis": observed_state,
        "state_basis_complete": complete,
        "commanded_state_matches_observed_basis": matches,
        "all_pre_read_stable": stable,
        "status": status,
        "bits": bits,
    }


def stimulus_checks(trace: RawTrace, state: str) -> dict[str, object]:
    initial: dict[str, object] = OrderedDict()
    read0: dict[str, object] = OrderedDict()
    protocol: dict[str, object] = OrderedDict()
    for instance, bit in enumerate(state, start=1):
        wl = f"I(I_WL{instance})"
        bl = f"I(I_BL{instance})"
        se = f"I(I_SE{instance})"
        initial[f"BVM{instance}"] = {
            "WL": validate_expected_plateau(
                trace.time, signal(trace, wl), WRITE0_PLATEAU_S, -100.0e-6,
                tolerance=PLATEAU_TOLERANCE_A, unit="A",
            ),
            "BL": validate_expected_plateau(
                trace.time, signal(trace, bl), WRITE0_PLATEAU_S, -100.0e-6,
                tolerance=PLATEAU_TOLERANCE_A, unit="A",
            ),
        }
        read0[f"BVM{instance}"] = {
            "WL": validate_expected_plateau(
                trace.time, signal(trace, wl), READ0_PLATEAU_S, 100.0e-6,
                tolerance=PLATEAU_TOLERANCE_A, unit="A",
            ),
            "SE": validate_expected_plateau(
                trace.time, signal(trace, se), READ0_PLATEAU_S, 100.0e-6,
                tolerance=PLATEAU_TOLERANCE_A, unit="A",
            ),
        }
        expected_bl = 100.0e-6 if bit == "1" else -100.0e-6
        protocol[f"BVM{instance}"] = validate_bvm_write_read_protocol(
            trace,
            trace.time,
            write_window_s=WRITE1_PLATEAU_S,
            read_window_s=READ1_PLATEAU_S,
            expected_write={wl: 100.0e-6, bl: expected_bl},
            expected_read={wl: 100.0e-6, se: 100.0e-6},
            tolerance=PLATEAU_TOLERANCE_A,
            unit="A",
        )
    return {
        "plateau_tolerance_uA": PLATEAU_TOLERANCE_A * 1.0e6,
        "initial_write": initial,
        "read0": read0,
        "write1_read1_protocol": protocol,
        "all_protocol_status": (
            "PROTOCOL_VALID"
            if all(item["status"] == "PROTOCOL_VALID" for item in protocol.values())
            else "PROTOCOL_MISMATCH"
        ),
    }


def terminal_observables(trace: RawTrace) -> dict[str, object]:
    probes = historical_bvm_array_probes(4)["TERMINAL"]  # type: ignore[index]
    result: dict[str, object] = OrderedDict()
    for name in ("B_LD4_01", "B_LD4_11", "BVMout"):
        branch = probes[name]  # type: ignore[index]
        result[name] = {
            "phase_area": OrderedDict(
                (
                    (window_name, phase_area_fact(trace, branch["phase"], branch["voltage"], bounds_s))  # type: ignore[index]
                    for window_name, bounds_s in WINDOWS_S.items()
                )
            ),
            "current": OrderedDict(
                (
                    (window_name, waveform_fact(trace, branch["current"], bounds_s, "A"))  # type: ignore[index]
                    for window_name, bounds_s in WINDOWS_S.items()
                )
            ),
        }
    return result


def qb_observables(trace: RawTrace, raw_path: Path, run_id: str) -> dict[str, object]:
    probes = original_bvmsim_qb_probes()
    burst: dict[str, object] = OrderedDict()
    events: dict[str, object] = OrderedDict()
    for name in ("BJs", "BJ1", "BJ2"):
        branch = probes[name]  # type: ignore[index]
        burst[name] = OrderedDict(
            (
                (
                    window_name,
                    compact_burst(
                        burst_total_metrics(
                            trace.time,
                            signal(trace, branch["phase"]),  # type: ignore[index]
                            signal(trace, branch["voltage"]),  # type: ignore[index]
                            bounds_s,
                            absolute_tolerance_turns=PHASE_AREA_ABS_FLOOR,
                            relative_tolerance=PHASE_AREA_RELATIVE,
                            relative_scale_floor_turns=1.0,
                        )
                    ),
                )
                for window_name, bounds_s in WINDOWS_S.items()
            )
        )
        events[name] = OrderedDict(
            (
                (
                    window_name,
                    event_fact(
                        trace,
                        raw_path,
                        run_id,
                        window_name,
                        branch["phase"],  # type: ignore[index]
                        branch["voltage"],  # type: ignore[index]
                    ),
                )
                for window_name in WINDOWS_PS
            )
        )
    return {
        "signals": {
            "QBIN": OrderedDict(
                (
                    (window_name, waveform_fact(trace, probes["QBIN"]["voltage"], bounds_s, "V"))  # type: ignore[index]
                    for window_name, bounds_s in WINDOWS_S.items()
                )
            ),
            "QBOUT": OrderedDict(
                (
                    (window_name, waveform_fact(trace, probes["QBOUT"]["voltage"], bounds_s, "V"))  # type: ignore[index]
                    for window_name, bounds_s in WINDOWS_S.items()
                )
            ),
            "Lin": OrderedDict(
                (
                    (window_name, waveform_fact(trace, probes["Lin"]["current"], bounds_s, "A"))  # type: ignore[index]
                    for window_name, bounds_s in WINDOWS_S.items()
                )
            ),
        },
        "burst_total": burst,
        "strict_local_events": events,
        "read1_peak_timing": {
            "Lin": peak_fact(trace, probes["Lin"]["current"], READ1_S, "A"),  # type: ignore[index]
            "QBIN": peak_fact(trace, probes["QBIN"]["voltage"], READ1_S, "V"),  # type: ignore[index]
            "QBOUT": peak_fact(trace, probes["QBOUT"]["voltage"], READ1_S, "V"),  # type: ignore[index]
        },
    }


def jtl_observables(trace: RawTrace, raw_path: Path, run_id: str) -> dict[str, object]:
    probes = historical_jtl_probes(6)
    result: dict[str, object] = OrderedDict()
    for stage in range(1, 7):
        stage_name = f"JTL{stage}"
        result[stage_name] = OrderedDict()
        for junction in ("B01", "B02"):
            branch = probes[stage_name][junction]  # type: ignore[index]
            burst = OrderedDict(
                (
                    (
                        window_name,
                        compact_burst(
                            burst_total_metrics(
                                trace.time,
                                signal(trace, branch["phase"]),  # type: ignore[index]
                                signal(trace, branch["voltage"]),  # type: ignore[index]
                                bounds_s,
                                absolute_tolerance_turns=PHASE_AREA_ABS_FLOOR,
                                relative_tolerance=PHASE_AREA_RELATIVE,
                                relative_scale_floor_turns=1.0,
                            )
                        ),
                    )
                    for window_name, bounds_s in WINDOWS_S.items()
                )
            )
            events = OrderedDict(
                (
                    (
                        window_name,
                        event_fact(
                            trace,
                            raw_path,
                            run_id,
                            window_name,
                            branch["phase"],  # type: ignore[index]
                            branch["voltage"],  # type: ignore[index]
                        ),
                    )
                    for window_name in WINDOWS_PS
                )
            )
            result[stage_name][junction] = {  # type: ignore[index]
                "burst_total": burst,
                "strict_local_events": events,
                "read1_peak_timing": peak_fact(trace, branch["voltage"], READ1_S, "V"),  # type: ignore[index]
            }
    return result


def qb_kcl(trace: RawTrace) -> dict[str, object]:
    branches = {
        "BJs": signal(trace, "I(BJS|XBQ1)"),
        "BJ1": signal(trace, "I(BJ1|XBQ1)"),
        "RJ1": signal(trace, "I(RJ1|XBQ1)"),
        "L1": signal(trace, "I(L1|XBQ1)"),
        "QB_BIAS": signal(trace, "I(IB|XBQ1)"),
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
                "node_bias_L1_IB_L2",
                ({"L1": 1.0, "QB_BIAS": 1.0, "L2": -1.0}, "I(L1)+I(IB)-I(L2)=0"),
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
            "node_bias": "L1 2->BIAS and IB 0->BIAS enter; L2 BIAS->4 leaves",
            "node_4": "L2 BIAS->4 enters; BJ2/RJ2 4->0 and L3 4->OUT leave",
        },
        "equations": OrderedDict(),
    }
    for name, (coefficients, equation) in equations.items():
        residual = linear_kcl_residual(
            {branch: branches[branch] for branch in coefficients}, coefficients
        )
        windows: dict[str, object] = OrderedDict()
        for window_name, bounds_s in WINDOWS_S.items():
            windows[window_name] = kcl_window_metrics(trace.time, residual, bounds_s)
        result["equations"][name] = {  # type: ignore[index]
            "equation": equation,
            "coefficients": coefficients,
            "windows": windows,
        }
    return result


def required_probe_labels() -> tuple[str, ...]:
    labels: list[str] = []
    for label in (
        *(f"I(I_{control}{number})" for number in range(1, 5) for control in ("WL", "BL", "SE")),
        *flatten_probe_labels(historical_bvm_array_probes(4)),
        *flatten_probe_labels(original_bvmsim_qb_probes()),
        *flatten_probe_labels(historical_jtl_probes(6)),
    ):
        if label not in labels:
            labels.append(label)
    return tuple(labels)


def artifact_facts(trace: RawTrace, deck: Path, log: Path) -> dict[str, object]:
    log_text = log.read_text(encoding="utf-8", errors="replace") if log.is_file() else ""
    required = required_probe_labels()
    qa = deck_qa(
        deck,
        log_text=log_text,
        expected_includes=("BVMSim/bvm_cell.cir", "BVMSim/BQ.cir", "BVMSim/library_josim/jtl2.cir"),
        expected_bvm_instances=4,
        expected_terminal_sensing_jj_count=12,
        expected_jtl_stages=6,
        expected_termination_ohm=10.0,
        expected_tran_timestep_ps=0.1,
        required_probes=required,
        raw_headers=trace.headers,
    )
    return {
        "status": "ARTIFACT_VALID" if qa["status"] == "ARTIFACT_VALID" else "ARTIFACT_INVALID",
        "raw": trace.qa(),
        "deck_qa": qa,
        "required_probe_count": len(required),
        "required_probe_labels": list(required),
    }


def compare_invariant_controls(traces: Mapping[str, RawTrace]) -> dict[str, object]:
    reference = traces["0000"]
    labels = tuple(
        f"I(I_{control}{number})"
        for number in range(1, 5)
        for control in ("WL", "SE")
    )
    mapping_ref = {label: signal(reference, label) for label in labels}
    comparisons: dict[str, object] = OrderedDict()
    for state in STATES:
        if state == "0000":
            continue
        current = traces[state]
        comparison = compare_stimuli(
            reference.time,
            mapping_ref,
            current.time,
            {label: signal(current, label) for label in labels},
            SCAN_S,
            unit="A",
        )
        if comparison.get("status") == "VALID":
            for item in comparison["signals"].values():  # type: ignore[index]
                item["max_abs_difference_uA"] = float(item["max_abs_difference"]) * 1.0e6
                item["rms_difference_uA"] = float(item["rms_difference"]) * 1.0e6
        comparisons[state] = comparison
    return {
        "reference_state": "0000",
        "signals": list(labels),
        "comparison_window_ps": [0.0, 200.0],
        "no_interpolation": True,
        "comparisons": comparisons,
    }


def position_summary(state_results: Mapping[str, Mapping[str, object]]) -> dict[str, object]:
    inputs: dict[str, object] = OrderedDict()
    for state in WEIGHT_ONE_STATES:
        result = state_results[state]
        inputs[state] = {
            "expected_weight": 1,
            "observed_state_basis": result["state_closure"]["observed_state_basis"],  # type: ignore[index]
            "state_closure_status": result["state_closure"]["status"],  # type: ignore[index]
            "BVMout_READ1_current": result["terminal"]["BVMout"]["current"]["READ1"],  # type: ignore[index]
            "Lin_READ1_current": result["qb"]["read1_peak_timing"]["Lin"],  # type: ignore[index]
            "QBIN_READ1_voltage": result["qb"]["read1_peak_timing"]["QBIN"],  # type: ignore[index]
            "QBOUT_READ1_voltage": result["qb"]["read1_peak_timing"]["QBOUT"],  # type: ignore[index]
            "BJ2_READ1_burst_total": result["qb"]["burst_total"]["BJ2"]["READ1"],  # type: ignore[index]
            "BJ2_READ1_strict": result["qb"]["strict_local_events"]["BJ2"]["READ1"],  # type: ignore[index]
            "JTL6_B02_READ1_strict": result["jtl"]["JTL6"]["B02"]["strict_local_events"]["READ1"],  # type: ignore[index]
        }
    lin_peaks = [
        float(inputs[state]["Lin_READ1_current"]["peak_abs_value"])  # type: ignore[index]
        for state in WEIGHT_ONE_STATES
    ]
    bvmout_peaks = [
        float(inputs[state]["BVMout_READ1_current"]["max_abs"])  # type: ignore[index]
        for state in WEIGHT_ONE_STATES
    ]
    # ``peak_timing_metrics(..., unit="A")`` and
    # ``waveform_window_summary(..., unit="A")`` already return display
    # values in uA.  Do not apply a second SI-to-display conversion here.
    lin_range_uA = max(lin_peaks) - min(lin_peaks)
    bvmout_range_uA = max(bvmout_peaks) - min(bvmout_peaks)
    return {
        "weight_one_states": list(WEIGHT_ONE_STATES),
        "per_state": inputs,
        "Lin_peak_abs_range_uA": lin_range_uA,
        "BVMout_peak_abs_range_uA": bvmout_range_uA,
        "input_difference_tolerance_uA": INPUT_DIFFERENCE_TOLERANCE_UA,
        "position_dependent_Lin_peak_observed": lin_range_uA > INPUT_DIFFERENCE_TOLERANCE_UA,
        "position_dependent_BVMout_peak_observed": bvmout_range_uA > INPUT_DIFFERENCE_TOLERANCE_UA,
        "interpretation_ceiling": "position-dependent input waveform observation only; not a mechanism claim",
    }


def count_relation(state_results: Mapping[str, Mapping[str, object]]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for state in STATES:
        result = state_results[state]
        qb = result["qb"]["strict_local_events"]["BJ2"]["READ1"]  # type: ignore[index]
        jtl6 = result["jtl"]["JTL6"]["B02"]["strict_local_events"]["READ1"]  # type: ignore[index]
        burst = result["qb"]["burst_total"]["BJ2"]["READ1"]  # type: ignore[index]
        rows.append(
            {
                "state": state,
                "expected_popcount_reference": state.count("1"),
                "observed_state_basis": result["state_closure"]["observed_state_basis"],  # type: ignore[index]
                "state_closure_status": result["state_closure"]["status"],  # type: ignore[index]
                "BJ2_cumulative_phase_turns": burst["phase_delta_turns"],
                "BJ2_cumulative_area_turns": burst["voltage_area_over_phi0"],
                "BJ2_strict_complete_segments": qb["complete_segment_count"],
                "BJ2_strict_clean_separated_events": qb["clean_separated_event_count"],
                "BJ2_continuous_multi_turn_running": qb["continuous_multi_turn_running"],
                "JTL6_B02_strict_complete_segments": jtl6["complete_segment_count"],
                "JTL6_B02_strict_clean_separated_events": jtl6["clean_separated_event_count"],
                "JTL6_B02_continuous_multi_turn_running": jtl6["continuous_multi_turn_running"],
                "count_basis_is_strict_local_not_phase_only": True,
            }
        )
    return rows


def exploratory_classification(
    state_results: Mapping[str, Mapping[str, object]],
    position: Mapping[str, object],
) -> dict[str, object]:
    artifact_ok = all(result["artifact"]["status"] == "ARTIFACT_VALID" for result in state_results.values())
    protocol_ok = all(result["stimulus"]["all_protocol_status"] == "PROTOCOL_VALID" for result in state_results.values())
    closure_ok = all(result["state_closure"]["status"] == "OBSERVED_STATE_MATCH_AND_CLOSED" for result in state_results.values())
    count_rows = count_relation(state_results)
    aggregate_count_match = all(
        row["BJ2_strict_clean_separated_events"] == row["expected_popcount_reference"]
        and row["JTL6_B02_strict_clean_separated_events"] == row["expected_popcount_reference"]
        for row in count_rows
    )
    if not artifact_ok:
        label = "ANALYSIS_INVALID"
    elif not protocol_ok:
        label = "CONTROL_PROTOCOL_MISMATCH"
    elif closure_ok and bool(position["position_dependent_Lin_peak_observed"]) and not aggregate_count_match:
        label = "STATE_CLOSED_POSITION_DEPENDENT_INPUT_WITH_COUNT_MISMATCH"
    elif closure_ok and bool(position["position_dependent_Lin_peak_observed"]):
        label = "STATE_CLOSED_POSITION_DEPENDENT_INPUT_OBSERVED"
    elif closure_ok and aggregate_count_match:
        label = "SIX_STATE_STATE_AND_TRANSPORT_CLOSURE_SUPPORTED"
    elif closure_ok:
        label = "STATE_CLOSURE_WITH_QB_COUNT_MISMATCH"
    else:
        label = "NO_CLEAR_STATE_CLOSURE"
    return {
        "primary_exploratory_classification": label,
        "artifact_ok": artifact_ok,
        "control_protocol_ok": protocol_ok,
        "all_six_observed_state_basis_match_and_closed": closure_ok,
        "aggregate_strict_count_matches_popcount": aggregate_count_match,
        "position_dependent_input_observed": bool(position["position_dependent_Lin_peak_observed"]),
        "count_mismatch_is_not_hidden_by_position_result": not aggregate_count_match,
        "no_gate_or_paper_claim": True,
        "classification_note": "The result is exploratory evidence for this historical fixture only; no mechanism or canonical-BVM claim is made.",
    }


def analyze() -> dict[str, object]:
    traces: dict[str, RawTrace] = OrderedDict()
    state_results: dict[str, object] = OrderedDict()
    for state in STATES:
        run_dir = EXP / "runs" / state
        deck = run_dir / "deck.cir"
        raw = run_dir / "raw.csv"
        log = run_dir / "run.log"
        metadata = run_dir / "metadata.json"
        if not all(path.is_file() for path in (deck, raw, log, metadata)):
            raise RuntimeError(f"missing run artifact for state {state}")
        trace = read_csv(raw)
        traces[state] = trace
        metadata_value = json.loads(metadata.read_text(encoding="utf-8"))
        actual_raw_hash = sha256(raw)
        if metadata_value.get("raw_sha256") != actual_raw_hash:
            raise RuntimeError(f"raw hash mismatch in metadata for {state}")
        if int(metadata_value.get("exit_code", 1)) != 0:
            raise RuntimeError(f"solver execution failed for {state}")
        state_results[state] = {
            "state": state,
            "expected_popcount_reference": state.count("1"),
            "raw": relative(raw),
            "raw_sha256": actual_raw_hash,
            "deck": relative(deck),
            "deck_sha256": sha256(deck),
            "run_log": relative(log),
            "run_log_sha256": sha256(log),
            "metadata": metadata_value,
            "grid": grid_facts(trace),
            "artifact": artifact_facts(trace, deck, log),
            "stimulus": stimulus_checks(trace, state),
            "state_closure": state_closure(trace, state),
            "bvm": OrderedDict((f"BVM{instance}", bvm_observables(trace, instance)) for instance in range(1, 5)),
            "terminal": terminal_observables(trace),
            "qb": qb_observables(trace, raw, state),
            "jtl": jtl_observables(trace, raw, state),
            "kcl": qb_kcl(trace),
        }

    position = position_summary(state_results)  # type: ignore[arg-type]
    controls = compare_invariant_controls(traces)
    classification = exploratory_classification(state_results, position)  # type: ignore[arg-type]
    return {
        "schema": "bvmsim-4bvm-six-state-position-closure-metrics-v1",
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "experiment": relative(EXP),
        "source_class": "HISTORICAL_BVMSIM",
        "phase_a_gate": {
            "path": relative(PHASE_A_PARITY),
            "status": json.loads(PHASE_A_PARITY.read_text(encoding="utf-8"))["status"],
            "simulation_invoked": json.loads(PHASE_A_PARITY.read_text(encoding="utf-8"))["simulation_invoked"],
        },
        "fixed_fixture": {
            "bvm": relative(HISTORICAL_BVM),
            "qb": relative(HISTORICAL_QB),
            "jtl": relative(HISTORICAL_JTL),
            "rj1_ohm": 12.0,
            "rj2_ohm": 4.0,
            "qb_bias_uA": 250.0,
            "jtl_stages": 6,
            "termination_ohm": 10.0,
            "tran": ".tran 0.1p 200p 45p",
            "canonical_bvm_replaced": False,
        },
        "windows_ps": {name: list(bounds) for name, bounds in WINDOWS_PS.items()},
        "strict_tolerance": STRICT_TOLERANCE,
        "state_discriminator": {
            "basis": "PRE_READ1 JM1 continuous-unwrapped phase level sign plus p2p stability",
            "phase_level_sign_min_turns": STATE_LEVEL_SIGN_MIN_TURNS,
            "pre_read_phase_p2p_max_turns": STATE_STABILITY_MAX_P2P_TURNS,
            "not_a_universal_storage_claim": True,
        },
        "states": state_results,
        "cross_state_invariant_control_comparison": controls,
        "weight_one_position_summary": position,
        "count_relation": count_relation(state_results),  # type: ignore[arg-type]
        "exploratory_classification": classification,
        "analysis_limits": [
            "P phase is raw radians; turns are continuous_unwrap(rad)/(2*pi).",
            "A whole-window phase displacement is not an SFQ count.",
            "Strict event lists are local same-junction evidence; JTL progression is reported as matching observables, not a Gate.",
            "The historical BVMSim BVM is not the canonical circuits/bvm/bvm_cell.cir authority.",
            "No timestep convergence, process margin, mechanism identity, or paper-level claim is established.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(EXP / "analysis/metrics.json"))
    args = parser.parse_args()
    metrics = analyze()
    write_once(Path(args.output), metrics)
    print(json.dumps({
        "status": metrics["exploratory_classification"]["primary_exploratory_classification"],  # type: ignore[index]
        "states": len(metrics["states"]),  # type: ignore[arg-type]
        "output": args.output,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
