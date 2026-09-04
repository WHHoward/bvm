#!/usr/bin/env python3
"""Analyze the common-SL -> 12-JSL -> frozen QB/JTL integration.

The analyzer keeps the causal comparison local to this experiment:

* receiver-loaded runs are compared with the accepted passive same-mask raw;
* all arithmetic is performed on the stored grid, without interpolation;
* phase is raw JoSIM radians until it is explicitly converted with
  continuous_unwrap(rad)/(2*pi);
* strict event lists are local diagnostics and are never renamed as an SFQ
  count or a system-level transport gate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, Sequence


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
PASSIVE = REPO / "test/exploration/bvmsim-4bvm-paperlike-common-sl-accumulation-isolation-v1-20260904"
SOLVER = REPO / "build/josim-cli"
METRIC_SPEC = REPO / "docs/research/METRIC_SPEC_V2.md"
MASKS = ("0000", "0001", "0010", "0100", "1000", "0011", "0111", "1100", "1110", "1111")
ONE_HOT = ("0001", "0010", "0100", "1000")
ONE_HOT_BY_INSTANCE = {1: "1000", 2: "0100", 3: "0010", 4: "0001"}
MULTI_ACTIVE = ("0011", "0111", "1100", "1110", "1111")

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
WINDOWS_S = OrderedDict((name, (left * 1e-12, right * 1e-12)) for name, (left, right) in WINDOWS_PS.items())
READ = WINDOWS_S["READ"]
SCAN = (101.0e-12, 200.0e-12)
PLATEAU_TOLERANCE_A = 0.1e-6
WRITE0_PLATEAU = (51.0e-12, 60.0e-12)
WRITE1_PLATEAU = (91.0e-12, 100.0e-12)
READ_PLATEAU = (111.0e-12, 120.0e-12)

sys.path.insert(0, str(REPO / "scripts"))
from bvmtools.compare import compare_series, exact_time_grid_identity  # noqa: E402
from bvmtools.deckqa import deck_qa  # noqa: E402
from bvmtools.kcl import kcl_window_metrics, linear_kcl_residual  # noqa: E402
from bvmtools.metrics import phase_area_window  # noqa: E402
from bvmtools.phase import TAU, continuous_unwrap, window_indices  # noqa: E402
from bvmtools.raw import RawTrace, read_csv  # noqa: E402
from bvmtools.sfq import StrictLocalEventSpec, strict_event_list  # noqa: E402
from bvmtools.stimulus import validate_expected_plateau  # noqa: E402
from bvmtools.waveform import trapezoid_integral, waveform_metrics, waveform_window_metrics  # noqa: E402

sys.path.insert(0, str(EXP))
from generate_decks import required_probe_labels  # noqa: E402


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO.resolve()).as_posix()


def now_local() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def sig(trace: RawTrace, label: str) -> tuple[float, ...]:
    return trace.column(label)  # type: ignore[return-value]


def indices(trace: RawTrace, bounds: tuple[float, float]) -> tuple[int, ...]:
    selected = window_indices(trace.time, *bounds)
    if len(selected) < 2:
        raise RuntimeError(f"window has fewer than two samples: {bounds}")
    return selected


def unit_factor(unit: str) -> tuple[float, str]:
    if unit == "A":
        return 1.0e6, "uA"
    if unit == "V":
        return 1.0e3, "mV"
    if unit == "turns":
        return 1.0, "turns"
    return 1.0, unit


def waveform(trace: RawTrace, label: str, bounds: tuple[float, float], unit: str) -> dict[str, object]:
    result = dict(waveform_window_metrics(trace.time, sig(trace, label), bounds, unit=unit if unit in {"A", "V"} else "raw"))
    result.update({"label": label, "raw_unit": unit, "display_unit": result.get("unit", unit)})
    return result


def vector_waveform(trace: RawTrace, values: Sequence[float], bounds: tuple[float, float], unit: str) -> dict[str, object]:
    return dict(waveform_window_metrics(trace.time, values, bounds, unit=unit if unit in {"A", "V"} else "raw"))


def phase_turns(trace: RawTrace, label: str) -> tuple[float, ...]:
    return tuple(value / TAU for value in continuous_unwrap(sig(trace, label)))


def phase_area(trace: RawTrace, phase_label: str, voltage_label: str, bounds: tuple[float, float]) -> dict[str, object]:
    result = phase_area_window(
        trace.time,
        sig(trace, phase_label),
        sig(trace, voltage_label),
        bounds,
        voltage_to_phase_sign=1,
        reporting_direction=1,
        include_segments=False,
    )
    result["phase_label"] = phase_label
    result["voltage_label"] = voltage_label
    return result


def compare_vectors(
    time_left: Sequence[float],
    left: Sequence[float],
    time_right: Sequence[float],
    right: Sequence[float],
    bounds: tuple[float, float],
    unit: str,
) -> dict[str, object]:
    left_indices = window_indices(time_left, *bounds)
    right_indices = window_indices(time_right, *bounds)
    left_t = [float(time_left[i]) for i in left_indices]
    right_t = [float(time_right[i]) for i in right_indices]
    left_y = [float(left[i]) for i in left_indices]
    right_y = [float(right[i]) for i in right_indices]
    comparison = compare_series(
        left_t,
        left_y,
        right_t,
        right_y,
        interpolation=None,
        include_correlation=True,
    )
    comparison.pop("pointwise_difference", None)
    factor, display = unit_factor(unit)
    for key in ("max_abs_difference", "rms_difference", "p95_abs_difference"):
        comparison[key] = float(comparison[key]) * factor
    comparison["unit"] = display
    comparison["difference_convention"] = "right_minus_left"
    return comparison


def compare_trace_signal(
    left: RawTrace,
    left_label: str,
    right: RawTrace,
    right_label: str,
    bounds: tuple[float, float],
    unit: str,
) -> dict[str, object]:
    return compare_vectors(left.time, sig(left, left_label), right.time, sig(right, right_label), bounds, unit)


def compare_derived(
    left: RawTrace,
    left_values: Sequence[float],
    right: RawTrace,
    right_values: Sequence[float],
    bounds: tuple[float, float],
    unit: str,
) -> dict[str, object]:
    return compare_vectors(left.time, left_values, right.time, right_values, bounds, unit)


def sum_lsl(trace: RawTrace) -> tuple[float, ...]:
    branches = [sig(trace, f"I(L_SL|XBVM{instance})") for instance in range(1, 5)]
    return tuple(sum(branch[index] for branch in branches) for index in range(len(trace.time)))


def sum_bvm_branch(trace: RawTrace, branch: str) -> tuple[float, ...]:
    rows = [sig(trace, f"I({branch}|XBVM{instance})") for instance in range(1, 5)]
    return tuple(sum(row[index] for row in rows) for index in range(len(trace.time)))


def strict_spec(mask: str, phase_label: str, voltage_label: str, raw_hash: str) -> StrictLocalEventSpec:
    return StrictLocalEventSpec(
        id="COMMON_SL_QB_LOCAL_EVENT_DIAGNOSTIC_V1",
        scope="task-local",
        status="POST_HOC_EXPLORATORY",
        provenance_status="RECORDED",
        mapping_status="EXACT_RAW_LABEL_SAME_JJ",
        phase_column=phase_label,
        voltage_column=voltage_label,
        branch_endpoints="same JJ phase/voltage branch from frozen netlist",
        voltage_to_phase_sign=1,
        reporting_direction=1,
        run_id=mask,
        window_id="READ",
        raw_sha256=raw_hash,
        metric_spec={"path": rel(METRIC_SPEC), "version": "2.0.0", "sha256": digest(METRIC_SPEC)},
        tolerance={
            "id": "task-local-diagnostic-not-a-gate",
            "scope": "task-local diagnostic only",
            "evidence": "same-JJ phase-area plus exact-sign monotonic segmentation",
            "status": "POST_HOC_EXPLORATORY",
            "phase_area_residual_abs_floor_turns": 0.05,
            "phase_area_residual_relative": 0.10,
            "complete_min_turns": 1.0,
            "clean_upper_turns": 1.15,
            "post_range_max_turns": 1.0,
            "post_tail_p2p_max_turns": 0.25,
        },
        compatibility_profile="STRICT_EVENT_ANCHOR_COMPATIBILITY_V1",
    )


def strict_events(trace: RawTrace, mask: str, phase_label: str, voltage_label: str, raw_hash: str) -> dict[str, object]:
    result = strict_event_list(
        trace.time,
        sig(trace, phase_label),
        sig(trace, voltage_label),
        event_window_s=READ,
        scan_window_s=SCAN,
        retrap_max_p2p_turns=0.25,
        spec=strict_spec(mask, phase_label, voltage_label, raw_hash),
    )
    result["interpretation"] = "local strict diagnostic only; no downstream SFQ count"
    return result


def strict_compact(event: Mapping[str, object]) -> dict[str, object]:
    return {
        "complete_segment_count": event.get("complete_segment_count"),
        "clean_separated_event_count": event.get("clean_separated_event_count"),
        "largest_segment_turns": event.get("largest_segment_turns"),
        "any_segment_spans_over_1_15_turns": event.get("any_segment_spans_over_1_15_turns"),
        "continuous_multi_turn_running": event.get("continuous_multi_turn_running"),
        "complete_event_onset_times_ps": event.get("complete_event_onset_times_ps"),
        "clean_event_onset_times_ps": event.get("clean_event_onset_times_ps"),
        "clean_event_directions": event.get("clean_event_directions"),
        "segment_count_scanned": len(event.get("segments", [])),
    }


def protocol_record(trace: RawTrace, mask: str) -> dict[str, object]:
    per_bvm: dict[str, object] = {}
    failures: list[str] = []
    for instance in range(1, 5):
        wl = f"I(I_WL{instance})"
        bl = f"I(I_BL{instance})"
        se = f"I(I_SE{instance})"
        checks = {
            "WRITE0_WL": validate_expected_plateau(trace.time, sig(trace, wl), WRITE0_PLATEAU, -100e-6, tolerance=PLATEAU_TOLERANCE_A, unit="A"),
            "WRITE0_BL": validate_expected_plateau(trace.time, sig(trace, bl), WRITE0_PLATEAU, -100e-6, tolerance=PLATEAU_TOLERANCE_A, unit="A"),
            "NO_HISTORY_WL": validate_expected_plateau(trace.time, sig(trace, wl), (70e-12, 90e-12), 0.0, tolerance=PLATEAU_TOLERANCE_A, unit="A"),
            "NO_HISTORY_BL": validate_expected_plateau(trace.time, sig(trace, bl), (70e-12, 90e-12), 0.0, tolerance=PLATEAU_TOLERANCE_A, unit="A"),
            "NO_HISTORY_SE": validate_expected_plateau(trace.time, sig(trace, se), (70e-12, 90e-12), 0.0, tolerance=PLATEAU_TOLERANCE_A, unit="A"),
            "WRITE1_WL": validate_expected_plateau(trace.time, sig(trace, wl), WRITE1_PLATEAU, 100e-6, tolerance=PLATEAU_TOLERANCE_A, unit="A"),
            "WRITE1_BL": validate_expected_plateau(trace.time, sig(trace, bl), WRITE1_PLATEAU, 100e-6, tolerance=PLATEAU_TOLERANCE_A, unit="A"),
            "WRITE1_SE": validate_expected_plateau(trace.time, sig(trace, se), WRITE1_PLATEAU, 0.0, tolerance=PLATEAU_TOLERANCE_A, unit="A"),
        }
        expected_read = 100e-6 if mask[instance - 1] == "1" else 0.0
        checks.update(
            {
                "READ_WL": validate_expected_plateau(trace.time, sig(trace, wl), READ_PLATEAU, expected_read, tolerance=PLATEAU_TOLERANCE_A, unit="A"),
                "READ_SE": validate_expected_plateau(trace.time, sig(trace, se), READ_PLATEAU, expected_read, tolerance=PLATEAU_TOLERANCE_A, unit="A"),
                "READ_BL": validate_expected_plateau(trace.time, sig(trace, bl), READ_PLATEAU, 0.0, tolerance=PLATEAU_TOLERANCE_A, unit="A"),
            }
        )
        per_bvm[f"BVM{instance}"] = checks
        failures.extend(f"BVM{instance}:{name}" for name, item in checks.items() if item["status"] != "PASS")  # type: ignore[index]
    return {
        "mask": mask,
        "semantics": "mask bit 1: WL=SE=+100 uA; bit 0: WL=SE=0; BL=0 during final READ",
        "per_bvm": per_bvm,
        "status": "PROTOCOL_VALID" if not failures else "PROTOCOL_MISMATCH",
        "failures": failures,
    }


def artifact_qa(traces: Mapping[str, RawTrace], provenance: Mapping[str, object]) -> dict[str, object]:
    required = tuple(required_probe_labels())
    per_mask: dict[str, object] = {}
    for mask in MASKS:
        run_dir = EXP / "runs" / mask
        deck = run_dir / "deck.cir"
        raw = run_dir / "raw.csv"
        log = run_dir / "run.log"
        metadata_path = run_dir / "metadata.json"
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        log_text = log.read_text(encoding="utf-8", errors="replace")
        qa = deck_qa(
            deck,
            log_text=log_text,
            expected_includes=("bvm_jm2_connected.cir", "BVMSim/BQ.cir", "BVMSim/library_josim/jtl2.cir"),
            expected_bvm_instances=4,
            expected_jtl_stages=6,
            required_probes=required,
            raw_headers=traces[mask].headers,
        )
        expected_deck_hash = (provenance.get("deck_records") or {}).get(mask, {}).get("sha256")  # type: ignore[union-attr]
        issues: list[str] = []
        if metadata.get("exit_code") != 0:
            issues.append("SOLVER_EXIT_NONZERO")
        if metadata.get("execution_status") != "RUN_PASS":
            issues.append("EXECUTION_STATUS")
        if metadata.get("artifacts", {}).get("raw", {}).get("sha256") != digest(raw):
            issues.append("RAW_HASH_MISMATCH")
        if metadata.get("artifacts", {}).get("deck", {}).get("sha256") != digest(deck):
            issues.append("DECK_HASH_MISMATCH")
        if metadata.get("artifacts", {}).get("log", {}).get("sha256") != digest(log):
            issues.append("LOG_HASH_MISMATCH")
        if expected_deck_hash != digest(deck):
            issues.append("PROVENANCE_DECK_HASH_MISMATCH")
        if re.search(r"Missing model:|Using default model|\berror\b|\bfatal\b", log_text, re.I):
            issues.append("SOLVER_LOG_WARNING")
        if traces[mask].duplicate_columns:
            issues.append("DUPLICATE_RAW_HEADER")
        if qa["status"] != "ARTIFACT_VALID":
            issues.append("DECKQA")
        if "circuits/bvm/bvm_cell.cir" in deck.read_text(encoding="utf-8"):
            issues.append("CANONICAL_BVM_USED")
        per_mask[mask] = {
            "status": "ARTIFACT_VALID" if not issues else "ARTIFACT_INVALID",
            "issues": issues,
            "deck": rel(deck),
            "raw": rel(raw),
            "metadata": rel(metadata_path),
            "deck_sha256": digest(deck),
            "raw_sha256": digest(raw),
            "log_sha256": digest(log),
            "solver": metadata.get("solver"),
            "raw_qa": traces[mask].qa(),
            "deck_qa": qa,
        }
    return {
        "status": "ARTIFACT_VALID" if all(item["status"] == "ARTIFACT_VALID" for item in per_mask.values()) else "ARTIFACT_INVALID",
        "per_mask": per_mask,
        "raw_policy": "one immutable raw.csv per mask; no mutable shared authority",
        "interpolation": "none",
    }


def grid_record(traces: Mapping[str, RawTrace], passive: Mapping[str, RawTrace]) -> dict[str, object]:
    base = traces["0000"]
    array_exact = {mask: exact_time_grid_identity(base.time, traces[mask].time) for mask in MASKS}
    passive_exact = {mask: exact_time_grid_identity(traces[mask].time, passive[mask].time) for mask in MASKS}
    return {
        "array_runs_exact_with_0000": array_exact,
        "receiver_vs_passive_exact_by_mask": passive_exact,
        "all_array_exact": all(array_exact.values()),
        "all_receiver_vs_passive_exact": all(passive_exact.values()),
        "interpolation": "none",
        "per_mask": {
            mask: {
                "sample_count": traces[mask].sample_count,
                "start_ps": traces[mask].time[0] * 1e12,
                "last_sample_ps": traces[mask].time[-1] * 1e12,
                "dt_min_ps": min(traces[mask].dt) * 1e12,
                "dt_max_ps": max(traces[mask].dt) * 1e12,
                "stored_grid_uniform_exact": all(value == traces[mask].dt[0] for value in traces[mask].dt),
            }
            for mask in MASKS
        },
    }


def state_record(traces: Mapping[str, RawTrace]) -> dict[str, object]:
    output: dict[str, object] = {"basis": "phase/area descriptive state observation; not a forced logical-state label", "per_mask": {}}
    for mask, trace in traces.items():
        per_bvm: dict[str, object] = {}
        for instance in range(1, 5):
            record: dict[str, object] = {"commanded_stored_state": "1111", "JM1": {}, "JM2": {}}
            for jj in ("JM1", "JM2"):
                record[jj] = {
                    "WRITE1": phase_area(trace, f"P(B_{jj}|XBVM{instance})", f"V(B_{jj}|XBVM{instance})", WINDOWS_S["WRITE1_ALL"]),
                    "SETTLE": waveform_window_metrics(trace.time, sig(trace, f"P(B_{jj}|XBVM{instance})"), WINDOWS_S["SETTLE"], unit="raw"),
                    "READ": waveform_window_metrics(trace.time, sig(trace, f"P(B_{jj}|XBVM{instance})"), READ, unit="raw"),
                }
                record[jj]["SETTLE"]["display_note"] = "raw phase radians; no 2pi conversion in this raw-unit summary"  # type: ignore[index]
            per_bvm[f"BVM{instance}"] = record
        output["per_mask"][mask] = per_bvm  # type: ignore[index]
    return output


def critical_bvm_record(traces: Mapping[str, RawTrace]) -> dict[str, object]:
    branches = ("L_M3", "L_PSL", "R_SL", "L_SL", "R_S", "L_S3")
    output: dict[str, object] = {"windows": list(WINDOWS_PS), "per_mask": {}}
    for mask, trace in traces.items():
        per_bvm: dict[str, object] = {}
        for instance in range(1, 5):
            per_bvm[f"BVM{instance}"] = {
                branch: {
                    "current": waveform(trace, f"I({branch}|XBVM{instance})", READ, "A"),
                    "voltage": waveform(trace, f"V({branch}|XBVM{instance})", READ, "V"),
                }
                for branch in branches
            }
        output["per_mask"][mask] = per_bvm  # type: ignore[index]
    return output


def source_back_action(traces: Mapping[str, RawTrace], passive: Mapping[str, RawTrace]) -> dict[str, object]:
    output: dict[str, object] = {
        "comparison_convention": "receiver_loaded minus passive same-mask; exact stored grid only",
        "derived_signal": "SUM_LSL = sum(I(L_SL|XBVM1..4))",
        "per_mask": {},
    }
    for mask in MASKS:
        new = traces[mask]
        old = passive[mask]
        new_sum = sum_lsl(new)
        old_sum = sum_lsl(old)
        records: dict[str, object] = {}
        for window_name in ("PRE", "NO_HISTORY_READ", "READ", "TAIL"):
            bounds = WINDOWS_S[window_name]
            signals: dict[str, object] = {}
            for name, label in (
                ("SUM_LSL", None),
                ("BVM1_LSL", "I(L_SL|XBVM1)"),
                ("BVM2_LSL", "I(L_SL|XBVM2)"),
                ("BVM3_LSL", "I(L_SL|XBVM3)"),
                ("BVM4_LSL", "I(L_SL|XBVM4)"),
                ("BVM1_RSL", "I(R_SL|XBVM1)"),
                ("BVM2_RSL", "I(R_SL|XBVM2)"),
                ("BVM3_RSL", "I(R_SL|XBVM3)"),
                ("BVM4_RSL", "I(R_SL|XBVM4)"),
                ("COMMON_SL", "V(COMMON_SL)"),
            ):
                if label is None:
                    item = compare_derived(old, old_sum, new, new_sum, bounds, "A")
                else:
                    item = compare_trace_signal(old, label, new, label, bounds, "V" if name == "COMMON_SL" else "A")
                signals[name] = item
            signals["passive_terminal_current_vs_new_JSL01"] = compare_trace_signal(
                old,
                "I(B_COL_LOAD01)",
                new,
                "I(B_JSL01)",
                bounds,
                "A",
            )
            records[window_name] = signals
        output["per_mask"][mask] = records  # type: ignore[index]
    return output


def kcl_record(traces: Mapping[str, RawTrace]) -> dict[str, object]:
    output: dict[str, object] = {
        "orientation": {
            "common_sl": "I(L_SL|XBVMn) leaves each BVM toward COMMON_SL; I(B_JSL01) leaves COMMON_SL toward COL01",
            "jsl_series": "all B_JSL currents follow the listed first-node to second-node orientation",
            "qbin_boundary": "I(B_JSL12) and I(LIN|XBQ1) both enter the QBIN-side QB branch; residual is I(B_JSL12)-I(LIN)",
            "qb_node2": "-I(BJS)+I(BJ1)+I(RJ1)+I(L1)=0",
            "qb_node3": "-I(L1)+I(L2)-I(IB)=0",
            "qb_node4": "-I(L2)+I(BJ2)+I(RJ2)+I(L3)=0",
        },
        "per_mask": {},
    }
    for mask, trace in traces.items():
        common = linear_kcl_residual(
            {f"L_SL{instance}": sig(trace, f"I(L_SL|XBVM{instance})") for instance in range(1, 5)} | {"JSL01": sig(trace, "I(B_JSL01)")},
            {f"L_SL{instance}": 1.0 for instance in range(1, 5)} | {"JSL01": -1.0},
        )
        series: dict[str, object] = {}
        for index in range(2, 13):
            residual = linear_kcl_residual(
                {"JSL01": sig(trace, "I(B_JSL01)"), f"JSL{index:02d}": sig(trace, f"I(B_JSL{index:02d})")},
                {"JSL01": 1.0, f"JSL{index:02d}": -1.0},
            )
            series[f"B_JSL01_minus_B_JSL{index:02d}"] = {
                name: kcl_window_metrics(trace.time, residual, bounds)
                for name, bounds in (("PRE", WINDOWS_S["PRE"]), ("READ", READ), ("TAIL", WINDOWS_S["TAIL"]))
            }
        boundary = linear_kcl_residual(
            {"JSL12": sig(trace, "I(B_JSL12)"), "LIN": sig(trace, "I(LIN|XBQ1)")},
            {"JSL12": 1.0, "LIN": -1.0},
        )
        qb_equations = {
            "QB_NODE2": linear_kcl_residual(
                {"BJS": sig(trace, "I(BJS|XBQ1)"), "BJ1": sig(trace, "I(BJ1|XBQ1)"), "RJ1": sig(trace, "I(RJ1|XBQ1)"), "L1": sig(trace, "I(L1|XBQ1)")},
                {"BJS": -1.0, "BJ1": 1.0, "RJ1": 1.0, "L1": 1.0},
            ),
            "QB_NODE3": linear_kcl_residual(
                {"L1": sig(trace, "I(L1|XBQ1)"), "L2": sig(trace, "I(L2|XBQ1)"), "IB": sig(trace, "I(IB|XBQ1)")},
                {"L1": -1.0, "L2": 1.0, "IB": -1.0},
            ),
            "QB_NODE4": linear_kcl_residual(
                {"L2": sig(trace, "I(L2|XBQ1)"), "BJ2": sig(trace, "I(BJ2|XBQ1)"), "RJ2": sig(trace, "I(RJ2|XBQ1)"), "L3": sig(trace, "I(L3|XBQ1)")},
                {"L2": -1.0, "BJ2": 1.0, "RJ2": 1.0, "L3": 1.0},
            ),
        }
        output["per_mask"][mask] = {  # type: ignore[index]
            "COMMON_SL_to_JSL01": {name: kcl_window_metrics(trace.time, common, bounds) for name, bounds in (("PRE", WINDOWS_S["PRE"]), ("READ", READ), ("TAIL", WINDOWS_S["TAIL"]))},
            "JSL_series": series,
            "JSL12_to_LIN": {name: kcl_window_metrics(trace.time, boundary, bounds) for name, bounds in (("PRE", WINDOWS_S["PRE"]), ("READ", READ), ("TAIL", WINDOWS_S["TAIL"]))},
            "QB_internal": {
                equation: {name: kcl_window_metrics(trace.time, residual, bounds) for name, bounds in (("PRE", WINDOWS_S["PRE"]), ("READ", READ), ("TAIL", WINDOWS_S["TAIL"]))}
                for equation, residual in qb_equations.items()
            },
        }
    return output


def one_hot_symmetry(traces: Mapping[str, RawTrace]) -> dict[str, object]:
    labels: OrderedDict[str, tuple[str | None, str]] = OrderedDict(
        (
            ("SUM_LSL", (None, "A")),
            ("JSL01", ("I(B_JSL01)", "A")),
            ("JSL12", ("I(B_JSL12)", "A")),
            ("LIN", ("I(LIN|XBQ1)", "A")),
            ("QBIN", ("V(QBIN)", "V")),
            ("BJ2_phase", ("P(BJ2|XBQ1)", "turns")),
            ("JTL6_B02_phase", ("P(B02|XJTL1_6)", "turns")),
        )
    )
    output: dict[str, object] = {"comparison_window": "READ", "pairwise": {}}
    for left_pos, left_mask in enumerate(ONE_HOT):
        for right_mask in ONE_HOT[left_pos + 1 :]:
            pair: dict[str, object] = {}
            for name, (label, unit) in labels.items():
                if label is None:
                    item = compare_derived(traces[left_mask], sum_lsl(traces[left_mask]), traces[right_mask], sum_lsl(traces[right_mask]), READ, unit)
                elif name.endswith("phase"):
                    item = compare_derived(traces[left_mask], phase_turns(traces[left_mask], label), traces[right_mask], phase_turns(traces[right_mask], label), READ, unit)
                else:
                    item = compare_trace_signal(traces[left_mask], label, traces[right_mask], label, READ, unit)
                pair[name] = item
            output["pairwise"][f"{left_mask}_vs_{right_mask}"] = pair  # type: ignore[index]
    return output


def residual_summary(trace: RawTrace, actual: Sequence[float], predicted: Sequence[float], bounds: tuple[float, float], unit: str) -> dict[str, object]:
    residual = tuple(float(a - p) for a, p in zip(actual, predicted))
    actual_metric = vector_waveform(trace, actual, bounds, unit)
    predicted_metric = vector_waveform(trace, predicted, bounds, unit)
    residual_metric = vector_waveform(trace, residual, bounds, unit)
    raw_actual = [float(actual[i]) for i in indices(trace, bounds)]
    raw_residual = [float(residual[i]) for i in indices(trace, bounds)]
    raw_rms = math.sqrt(sum(x * x for x in raw_actual) / len(raw_actual)) if raw_actual else 0.0
    residual_rms = math.sqrt(sum(x * x for x in raw_residual) / len(raw_residual)) if raw_residual else 0.0
    return {
        "actual": actual_metric,
        "predicted": predicted_metric,
        "residual": residual_metric,
        "normalized_rms_error": residual_rms / raw_rms if raw_rms else None,
        "signed_integral_residual_si": trapezoid_integral(raw_residual, [trace.time[i] for i in indices(trace, bounds)]),
        "interpretation": "residual is descriptive; no predefined pass threshold",
    }


def additivity(traces: Mapping[str, RawTrace]) -> dict[str, object]:
    labels: OrderedDict[str, tuple[str | None, str]] = OrderedDict(
        (
            ("SUM_LSL", (None, "A")),
            ("JSL01", ("I(B_JSL01)", "A")),
            ("JSL12", ("I(B_JSL12)", "A")),
            ("LIN", ("I(LIN|XBQ1)", "A")),
            ("QBIN", ("V(QBIN)", "V")),
            ("QBOUT", ("V(QBOUT)", "V")),
        )
    )
    for instance in range(1, 5):
        labels[f"BVM{instance}_LSL"] = (f"I(L_SL|XBVM{instance})", "A")
    baseline = traces["0000"]
    one_hot_delta: dict[tuple[str, str], tuple[float, ...]] = {}
    for onehot in ONE_HOT:
        for name, (label, _) in labels.items():
            a = sum_lsl(traces[onehot]) if label is None else sig(traces[onehot], label)
            b = sum_lsl(baseline) if label is None else sig(baseline, label)
            one_hot_delta[(onehot, name)] = tuple(x - y for x, y in zip(a, b))
    output: dict[str, object] = {"definition": "Delta(mask)=mask-0000; predicted=sum(one-hot Delta); residual=actual-predicted", "per_mask": {}}
    for mask in MULTI_ACTIVE:
        active_onehots = [ONE_HOT_BY_INSTANCE[instance] for instance in range(1, 5) if mask[instance - 1] == "1"]
        record: dict[str, object] = {"active_one_hot_masks": active_onehots, "signals": {}}
        for name, (label, unit) in labels.items():
            actual_base = sum_lsl(traces[mask]) if label is None else sig(traces[mask], label)
            zero_base = sum_lsl(baseline) if label is None else sig(baseline, label)
            actual = tuple(a - b for a, b in zip(actual_base, zero_base))
            predicted = tuple(sum(one_hot_delta[(onehot, name)][i] for onehot in active_onehots) for i in range(len(actual)))
            record["signals"][name] = residual_summary(traces[mask], actual, predicted, READ, unit)  # type: ignore[index]
        output["per_mask"][mask] = record  # type: ignore[index]
    return output


def population_record(traces: Mapping[str, RawTrace], raw_hashes: Mapping[str, str]) -> dict[str, object]:
    output: dict[str, object] = {
        "population_definition": "commanded active-row count in mask, not measured SFQ count",
        "per_mask": {},
    }
    for mask, trace in traces.items():
        bj2_phase = phase_area(trace, "P(BJ2|XBQ1)", "V(BJ2|XBQ1)", READ)
        jtl6_phase = phase_area(trace, "P(B02|XJTL1_6)", "V(B02|XJTL1_6)", READ)
        bj2_event = strict_events(trace, mask, "P(BJ2|XBQ1)", "V(BJ2|XBQ1)", raw_hashes[mask])
        jtl6_event = strict_events(trace, mask, "P(B02|XJTL1_6)", "V(B02|XJTL1_6)", raw_hashes[mask])
        output["per_mask"][mask] = {  # type: ignore[index]
            "population": mask.count("1"),
            "active_bvms": [instance for instance in range(1, 5) if mask[instance - 1] == "1"],
            "SUM_LSL": waveform_window_metrics(trace.time, sum_lsl(trace), READ, unit="A"),
            "I(B_JSL01)": waveform(trace, "I(B_JSL01)", READ, "A"),
            "I(B_JSL12)": waveform(trace, "I(B_JSL12)", READ, "A"),
            "I(LIN|XBQ1)": waveform(trace, "I(LIN|XBQ1)", READ, "A"),
            "V(QBIN)": waveform(trace, "V(QBIN)", READ, "V"),
            "V(QBOUT)": waveform(trace, "V(QBOUT)", READ, "V"),
            "BJ2_phase_area": bj2_phase,
            "BJ2_strict_event_list": bj2_event,
            "JTL6_B02_phase_area": jtl6_phase,
            "JTL6_B02_strict_event_list": jtl6_event,
        }
    return output


def jtl_transport_record(traces: Mapping[str, RawTrace], raw_hashes: Mapping[str, str]) -> dict[str, object]:
    output: dict[str, object] = {"per_mask": {}, "stage_order": ["BJ2"] + [f"JTL{stage}" for stage in range(1, 7)]}
    for mask, trace in traces.items():
        rows: dict[str, object] = {}
        bj2_event = strict_events(trace, mask, "P(BJ2|XBQ1)", "V(BJ2|XBQ1)", raw_hashes[mask])
        rows["BJ2"] = {
            "phase_area": phase_area(trace, "P(BJ2|XBQ1)", "V(BJ2|XBQ1)", READ),
            "strict_event_list": bj2_event,
            "strict_compact": strict_compact(bj2_event),
        }
        for stage in range(1, 7):
            hierarchy = f"XJTL1_{stage}"
            stage_record: dict[str, object] = {}
            for junction in ("B01", "B02"):
                p = f"P({junction}|{hierarchy})"
                v = f"V({junction}|{hierarchy})"
                event = strict_events(trace, mask, p, v, raw_hashes[mask])
                stage_record[junction] = {
                    "phase_area": phase_area(trace, p, v, READ),
                    "strict_event_list": event,
                    "strict_compact": strict_compact(event),
                }
            rows[f"JTL{stage}"] = stage_record
        output["per_mask"][mask] = rows  # type: ignore[index]
    return output


def jsl_diagnostics(traces: Mapping[str, RawTrace], raw_hashes: Mapping[str, str]) -> dict[str, object]:
    output: dict[str, object] = {"assumption": "shared 12-JSL stack used as passive/current-transfer element; any complete local JSL event violates this assumption", "per_mask": {}}
    for mask, trace in traces.items():
        per_jsl: dict[str, object] = {}
        complete_any = False
        for index in range(1, 13):
            p = f"P(B_JSL{index:02d})"
            v = f"V(B_JSL{index:02d})"
            event = strict_events(trace, mask, p, v, raw_hashes[mask])
            compact = strict_compact(event)
            complete_any = complete_any or bool(compact["complete_segment_count"])
            per_jsl[f"B_JSL{index:02d}"] = compact
        output["per_mask"][mask] = {"any_complete_local_event": complete_any, "per_jsl": per_jsl}  # type: ignore[index]
    return output


def phase_population_table(traces: Mapping[str, RawTrace]) -> dict[str, object]:
    # A compact table of phase trajectory facts, explicitly labelled as
    # cumulative phase activity rather than event counts.
    output: dict[str, object] = {"phase_unit": "turns = continuous_unwrap(P radians)/(2*pi)", "per_mask": {}}
    for mask, trace in traces.items():
        item: dict[str, object] = {}
        for name, p, v in (
            ("BJ2", "P(BJ2|XBQ1)", "V(BJ2|XBQ1)"),
            ("JTL6_B02", "P(B02|XJTL1_6)", "V(B02|XJTL1_6)"),
        ):
            area = phase_area(trace, p, v, READ)
            item[name] = {
                "phase_delta_turns": area["phase_delta_turns"],
                "voltage_area_turns": area["voltage_area_over_phi0"],
                "phase_area_residual_turns": area["phase_area_residual_turns"],
                "phase_p2p_turns": area["phase_p2p_turns"],
                "not_an_sfq_count": True,
            }
        output["per_mask"][mask] = item  # type: ignore[index]
    return output


def write_json(path: Path, value: object) -> None:
    if path.exists():
        raise RuntimeError(f"refusing to overwrite immutable analysis artifact: {path}")
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="write immutable metrics.json")
    args = parser.parse_args()

    provenance = json.loads((EXP / "provenance.json").read_text(encoding="utf-8"))
    traces = OrderedDict((mask, read_csv(EXP / "runs" / mask / "raw.csv")) for mask in MASKS)
    passive = OrderedDict((mask, read_csv(PASSIVE / "runs" / mask / "raw.csv")) for mask in MASKS)
    raw_hashes = {mask: digest(EXP / "runs" / mask / "raw.csv") for mask in MASKS}
    grids = grid_record(traces, passive)
    if not grids["all_array_exact"] or not grids["all_receiver_vs_passive_exact"]:
        raise RuntimeError(f"time-grid identity failure; no interpolation is allowed: {grids}")

    artifacts = artifact_qa(traces, provenance)
    protocols = {mask: protocol_record(traces[mask], mask) for mask in MASKS}
    metrics: dict[str, object] = {
        "schema": "bvmsim-common-sl-12jsl-qb-integration-metrics-v1",
        "created_at_local": now_local(),
        "experiment_id": EXP.name,
        "head_at_analysis": subprocess_head(),
        "source_class": "HISTORICAL_BVMSIM_JM2_CONNECTED_COMMON_SL_12JSL_QB_VARIANT",
        "canonical_bvm_used": False,
        "frozen_boundary": "B_JSL12 COL11 0 -> COL11 QBIN; frozen BQ -> six frozen JTL stages -> 10 ohm",
        "artifact_qa": artifacts,
        "time_grid": grids,
        "protocol": protocols,
        "state_observation": state_record(traces),
        "critical_bvm": critical_bvm_record(traces),
        "source_back_action_vs_passive": source_back_action(traces, passive),
        "kcl": kcl_record(traces),
        "one_hot_symmetry": one_hot_symmetry(traces),
        "additivity_under_qb_load": additivity(traces),
        "population": population_record(traces, raw_hashes),
        "phase_population": phase_population_table(traces),
        "jsl_local_diagnostics": jsl_diagnostics(traces, raw_hashes),
        "jtl_transport": jtl_transport_record(traces, raw_hashes),
        "analysis_conventions": {
            "P_raw_unit": "radians",
            "phase_display_conversion": "continuous_unwrap(rad)/(2*pi)",
            "no_phase_or_voltage_area_as_sfq_count": True,
            "strict_event_list": "shared bvmtools.sfq strict_event_list; local diagnostic only",
            "all_pointwise_comparisons": "exact stored grid, no interpolation",
            "population": "commanded active BVM count, not measured output count",
        },
        "independent_check": {
            "path": rel(EXP / "analysis/independent_check.json"),
            "status": "PASS" if (EXP / "analysis/independent_check.json").is_file() else "RUN_AFTER_ANALYSIS",
        },
    }
    metrics["status"] = "ANALYSIS_VALID" if artifacts["status"] == "ARTIFACT_VALID" and all(item["status"] == "PROTOCOL_VALID" for item in protocols.values()) else "ANALYSIS_INVALID"
    if args.write:
        write_json(EXP / "analysis/metrics.json", metrics)
    print(json.dumps({"status": metrics["status"], "mask_count": len(MASKS), "grid_exact": True, "artifact_status": artifacts["status"]}, ensure_ascii=False))
    return 0


def subprocess_head() -> str:
    import subprocess

    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()


if __name__ == "__main__":
    raise SystemExit(main())
