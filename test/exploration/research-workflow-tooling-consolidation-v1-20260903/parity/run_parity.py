#!/usr/bin/env python3
"""Run Phase A golden parity using immutable existing raw files only.

This script never invokes JoSIM.  It re-derives selected measurements through
the shared bvmtools API and compares them with the already recorded old
analysis results.  It is deliberately not a scientific verdict engine.
"""

from __future__ import annotations

import json
import math
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

from bvmtools.deckqa import deck_qa  # noqa: E402
from bvmtools.kcl import kcl_window_metrics, linear_kcl_residual  # noqa: E402
from bvmtools.metrics import (  # noqa: E402
    burst_total_metrics,
    peak_timing_metrics,
    phase_area_window,
    waveform_window_summary,
)
from bvmtools.phase import window_indices  # noqa: E402
from bvmtools.probes import (  # noqa: E402
    flatten_probe_labels,
    historical_bvm_probes,
    historical_jtl_probes,
    original_bvmsim_qb_probes,
)
from bvmtools.provenance import sha256_file  # noqa: E402
from bvmtools.raw import RawTrace, read_csv  # noqa: E402
from bvmtools.sfq import StrictLocalEventSpec, strict_event_list  # noqa: E402
from bvmtools.stimulus import validate_bvm_write_read_protocol  # noqa: E402


SINGLE_ROOT = REPO / "test/exploration/bvmsim-single-corrected-baseline-v1-20260903"
FOUR_ROOT = REPO / "test/exploration/bvmsim-bvm-qb-jtl-operational-baseline-v1-20260903"
SINGLE_METRICS = json.loads(
    (SINGLE_ROOT / "analysis/metrics.json").read_text(encoding="utf-8")
)
FOUR_METRICS = json.loads(
    (FOUR_ROOT / "analysis/metrics.json").read_text(encoding="utf-8")
)

TURNS_ABS = 1.0e-12
TURNS_REL = 1.0e-12
WAVEFORM_ABS = 1.0e-9
WAVEFORM_REL = 1.0e-12
PHASE_AREA_ABS = 0.05
PHASE_AREA_REL = 0.10
STRICT_RETRAP_P2P = 0.25


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO.resolve()).as_posix()


def json_write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def window(start_ps: float, end_ps: float) -> tuple[float, float]:
    return start_ps * 1.0e-12, end_ps * 1.0e-12


def scalar_check(
    checks: list[dict[str, object]],
    name: str,
    observed: float,
    expected: float,
    *,
    abs_tolerance: float,
    relative_tolerance: float,
) -> None:
    observed_value = float(observed)
    expected_value = float(expected)
    difference = observed_value - expected_value
    allowed = float(abs_tolerance) + float(relative_tolerance) * abs(expected_value)
    checks.append(
        {
            "name": name,
            "kind": "numeric",
            "observed": observed_value,
            "expected": expected_value,
            "difference": difference,
            "allowed_abs_error": allowed,
            "pass": abs(difference) <= allowed,
        }
    )


def exact_check(
    checks: list[dict[str, object]], name: str, observed: object, expected: object
) -> None:
    checks.append(
        {
            "name": name,
            "kind": "exact",
            "observed": observed,
            "expected": expected,
            "pass": observed == expected,
        }
    )


def old_four_record(state: str) -> dict[str, Any]:
    return next(item for item in FOUR_METRICS["results"]["four"] if item["state"] == state)


def strict_spec(raw_path: Path, phase: str, voltage: str, run_id: str) -> StrictLocalEventSpec:
    return StrictLocalEventSpec.from_mapping(
        {
            "id": "phase-a-parity-strict-local-v1",
            "scope": "task-local",
            "status": "POST_HOC_EXPLORATORY",
            "provenance_status": "RAW_HASHED_REPRODUCTION_ONLY",
            "mapping_status": "DECLARED_DIRECT_SAME_JJ_PV",
            "phase_column": phase,
            "voltage_column": voltage,
            "branch_endpoints": "direct JoSIM same-JJ P/V mapping",
            "voltage_to_phase_sign": 1,
            "reporting_direction": 1,
            "run_id": run_id,
            "window_id": "READ1",
            "raw_sha256": sha256_file(raw_path),
            "metric_spec": {
                "path": "docs/research/METRIC_SPEC_V2.md",
                "version": "2.0.0",
                "sha256": sha256_file(REPO / "docs/research/METRIC_SPEC_V2.md"),
            },
            "tolerance": {
                "id": "phase-a-parity-task-local-v1",
                "scope": "task-local",
                "status": "POST_HOC_EXPLORATORY",
                "evidence": rel(EXP / "PHASE_A_REPORT.md"),
                "phase_area_residual_abs_floor_turns": PHASE_AREA_ABS,
                "phase_area_residual_relative": PHASE_AREA_REL,
                "complete_min_turns": 1.0,
                "clean_upper_turns": 1.15,
                "post_range_max_turns": 1.0,
                "post_tail_p2p_max_turns": STRICT_RETRAP_P2P,
            },
            "compatibility_profile": "STRICT_EVENT_ANCHOR_COMPATIBILITY_V1",
        }
    )


def add_phase_area_parity(
    checks: list[dict[str, object]],
    name: str,
    observed: Mapping[str, object],
    expected: Mapping[str, object],
) -> None:
    for field in (
        "phase_delta_rad",
        "phase_delta_turns",
        "voltage_area_wb",
        "voltage_area_over_phi0",
        "voltage_area_turns",
        "phase_area_residual_turns",
    ):
        if field in observed and field in expected:
            scalar_check(
                checks,
                f"{name}.{field}",
                float(observed[field]),
                float(expected[field]),
                abs_tolerance=TURNS_ABS if "turns" in field else 1.0e-15,
                relative_tolerance=TURNS_REL,
            )


def add_waveform_parity(
    checks: list[dict[str, object]],
    name: str,
    observed: Mapping[str, object],
    expected: Mapping[str, object],
) -> None:
    for field in (
        "minimum",
        "maximum",
        "p2p",
        "mean",
        "median",
        "rms",
        "max_abs",
        "peak_value",
        "peak_time_s",
        "minimum_value",
        "minimum_time_s",
        "signed_time_integral",
        "positive_area",
        "negative_area",
    ):
        if field in observed and field in expected:
            scalar_check(
                checks,
                f"{name}.{field}",
                float(observed[field]),
                float(expected[field]),
                abs_tolerance=WAVEFORM_ABS,
                relative_tolerance=WAVEFORM_REL,
            )


def available_bvm_labels(trace: RawTrace, instance: int = 1) -> tuple[str, ...]:
    labels = flatten_probe_labels(historical_bvm_probes(instance))
    return tuple(label for label in labels if label in trace.headers)


def evaluate_single(
    checks: list[dict[str, object]], case: str, raw_path: Path, deck_path: Path
) -> dict[str, object]:
    trace = read_csv(raw_path)
    old = SINGLE_METRICS["conditions"][case]
    event_window = window(70.0, 170.0)
    phase = "P(BJ2|XBQ1)"
    voltage = "V(BJ2|XBQ1)"
    current = "I(LIN|XBQ1)"
    shared = phase_area_window(trace.time, trace.column(phase), trace.column(voltage), event_window)
    old_area = old["response"]["qb"]["BJ2"]["phase_area"]["RESPONSE"]
    add_phase_area_parity(checks, f"{case}.qb_bj2_response", shared, old_area)
    consistency = burst_total_metrics(
        trace.time,
        trace.column(phase),
        trace.column(voltage),
        event_window,
        absolute_tolerance_turns=PHASE_AREA_ABS,
        relative_tolerance=PHASE_AREA_REL,
        relative_scale_floor_turns=1.0,
    )["phase_area_consistency"]
    old_expected_consistency = abs(float(old_area["phase_area_residual_turns"])) <= max(
        PHASE_AREA_ABS,
        PHASE_AREA_REL
        * max(
            abs(float(old_area["phase_delta_turns"])),
            abs(float(old_area["voltage_area_turns"])),
            1.0,
        ),
    )
    exact_check(
        checks,
        f"{case}.qb_bj2_phase_area_consistent",
        consistency["phase_area_consistent"],
        old_expected_consistency,
    )
    shared_waveform = waveform_window_summary(
        trace.time, trace.column(current), event_window, unit="A"
    )
    old_waveform = old["response"]["lin_current"]["windows"]["RESPONSE"]
    add_waveform_parity(checks, f"{case}.lin_response", shared_waveform, old_waveform)
    shared_peak = peak_timing_metrics(
        trace.time, trace.column(current), event_window, unit="A"
    )
    scalar_check(
        checks,
        f"{case}.lin_peak_abs_value",
        float(shared_peak["peak_abs_value"]),
        float(old_waveform["max_abs"]),
        abs_tolerance=WAVEFORM_ABS,
        relative_tolerance=WAVEFORM_REL,
    )
    old_segment = old_area["segment_diagnostic"]
    shared_segment = shared["segment_diagnostic"]
    for field in (
        "segment_count",
        "largest_abs_segment_turns",
        "continuous_multiturn_running_descriptive",
    ):
        exact_check(
            checks,
            f"{case}.segment_diagnostic.{field}",
            shared_segment[field],
            old_segment[field],
        )

    expected_write = {
        "I(I_WL1)": -100.0e-6
        if int(old["logical_state"]) == 0
        else 100.0e-6,
        "I(I_BL1)": -100.0e-6
        if int(old["logical_state"]) == 0
        else 100.0e-6,
        "I(I_SE1)": 0.0,
    }
    expected_read = {
        "I(I_WL1)": 100.0e-6,
        "I(I_BL1)": 0.0,
        "I(I_SE1)": 100.0e-6,
    }
    stimulus = validate_bvm_write_read_protocol(
        trace,
        trace.time,
        write_window_s=window(51.0, 60.0),
        read_window_s=window(71.0, 80.0),
        expected_write=expected_write,
        expected_read=expected_read,
        tolerance=1.0e-12,
    )
    old_stimulus = old["artifact"]["stimulus_check"]
    exact_check(checks, f"{case}.stimulus.status", stimulus["status"], "PROTOCOL_VALID")
    exact_check(
        checks,
        f"{case}.stimulus.write_semantics",
        all(item["status"] == "PASS" for item in stimulus["write"].values()),
        old_stimulus["write_equals_WL_plus_BL"],
    )
    exact_check(
        checks,
        f"{case}.stimulus.read_semantics",
        all(item["status"] == "PASS" for item in stimulus["read"].values()),
        old_stimulus["read_equals_WL_plus_SE_and_BL_zero"],
    )
    for key, old_item in old_stimulus["plateau_checks"].items():
        section, label = key.split("_", 1)
        actual = stimulus[section][label]
        scalar_check(
            checks,
            f"{case}.stimulus.{key}.max_abs_error_uA",
            float(actual["max_abs_error_display"]),
            float(old_item["max_abs_error_uA"]),
            abs_tolerance=WAVEFORM_ABS,
            relative_tolerance=0.0,
        )

    required = (
        available_bvm_labels(trace)
        + flatten_probe_labels(original_bvmsim_qb_probes())
        + flatten_probe_labels(historical_jtl_probes(6))
    )
    log_path = deck_path.parent / "logs/run-01.log"
    qa = deck_qa(
        deck_path,
        log_text=log_path.read_text(encoding="utf-8"),
        expected_includes=(
            "BVMSim/bvm_cell.cir",
            "BVMSim/BQ.cir",
            "BVMSim/library_josim/jtl2.cir",
        ),
        expected_bvm_instances=1,
        expected_terminal_sensing_jj_count=12,
        expected_jtl_stages=6,
        expected_termination_ohm=10.0,
        expected_tran_timestep_ps=0.1,
        required_probes=required,
        raw_headers=trace.headers,
    )
    exact_check(checks, f"{case}.deckqa.status", qa["status"], "ARTIFACT_VALID")
    exact_check(checks, f"{case}.deckqa.raw_missing", qa["raw_missing_probes"], [])
    return {
        "case": case,
        "raw": rel(raw_path),
        "raw_sha256": sha256_file(raw_path),
        "deck": rel(deck_path),
        "deck_sha256": sha256_file(deck_path),
        "shared_burst_total": {
            "phase_delta_turns": shared["phase_delta_turns"],
            "voltage_area_turns": shared["voltage_area_turns"],
            "phase_area_consistent": consistency["phase_area_consistent"],
        },
        "shared_stimulus_status": stimulus["status"],
        "deckqa": qa,
    }


def evaluate_four(checks: list[dict[str, object]]) -> dict[str, object]:
    state = "1111"
    raw_path = FOUR_ROOT / "runs/four/1111/raw/run-01.csv"
    deck_path = FOUR_ROOT / "runs/four/1111/deck.cir"
    trace = read_csv(raw_path)
    old = old_four_record(state)
    event_window = window(110.0, 170.0)
    phase = "P(BJ2|XBQ1)"
    voltage = "V(BJ2|XBQ1)"
    shared = burst_total_metrics(
        trace.time,
        trace.column(phase),
        trace.column(voltage),
        event_window,
        absolute_tolerance_turns=PHASE_AREA_ABS,
        relative_tolerance=PHASE_AREA_REL,
        relative_scale_floor_turns=1.0,
    )
    old_qb = old["qb"]["READ1"]
    for field in ("phase_delta_turns", "voltage_area_over_phi0"):
        scalar_check(
            checks,
            f"four_{state}.qb.{field}",
            float(shared["phase_delta_turns" if field == "phase_delta_turns" else "voltage_area_over_phi0"]),
            float(old_qb[field]),
            abs_tolerance=TURNS_ABS,
            relative_tolerance=TURNS_REL,
        )
    old_bvmout = old["bvmout_READ1_phase_area"]
    shared_bvmout = phase_area_window(
        trace.time,
        trace.column("P(BVMOUT)"),
        trace.column("V(BVMOUT)"),
        event_window,
    )
    add_phase_area_parity(checks, f"four_{state}.bvmout", shared_bvmout, old_bvmout)
    shared_input = waveform_window_summary(
        trace.time,
        trace.column("I(LIN|XBQ1)"),
        event_window,
        unit="A",
    )
    old_input = old["input_descriptor_READ1"]
    for field, old_field in (
        ("minimum", "min_uA"),
        ("maximum", "max_uA"),
        ("p2p", "p2p_uA"),
        ("mean", "mean_uA"),
        ("rms", "rms_uA"),
        ("max_abs", "peak_abs_uA"),
    ):
        scalar_check(
            checks,
            f"four_{state}.lin.{field}",
            float(shared_input[field]),
            float(old_input[old_field]),
            abs_tolerance=WAVEFORM_ABS,
            relative_tolerance=WAVEFORM_REL,
        )
    scalar_check(
        checks,
        f"four_{state}.lin.signed_integral",
        float(shared_input["signed_time_integral"]),
        float(old_input["integral_pC"]) * 1.0e6,
        abs_tolerance=WAVEFORM_ABS,
        relative_tolerance=WAVEFORM_REL,
    )

    spec = strict_spec(raw_path, phase, voltage, "F4_1111_R12_T100")
    scan = (trace.time[0], trace.time[-1] + trace.dt[-1])
    strict = strict_event_list(
        trace.time,
        trace.column(phase),
        trace.column(voltage),
        event_window_s=event_window,
        scan_window_s=scan,
        retrap_max_p2p_turns=STRICT_RETRAP_P2P,
        spec=spec,
    )
    old_strict = old_qb["strict_local"]
    for field in (
        "complete_segment_count",
        "clean_separated_event_count",
        "complete_event_onset_times_ps",
        "clean_event_onset_times_ps",
        "continuous_multi_turn_running",
    ):
        exact_check(checks, f"four_{state}.qb.strict.{field}", strict[field], old_strict[field])
    jtl_phase = "P(B02|XJTL1_6)"
    jtl_voltage = "V(B02|XJTL1_6)"
    jtl = burst_total_metrics(
        trace.time,
        trace.column(jtl_phase),
        trace.column(jtl_voltage),
        event_window,
        absolute_tolerance_turns=PHASE_AREA_ABS,
        relative_tolerance=PHASE_AREA_REL,
        relative_scale_floor_turns=1.0,
    )
    old_jtl = old["jtl"]["JTL6"]["B02"]
    for field in ("phase_delta_turns", "voltage_area_over_phi0"):
        scalar_check(
            checks,
            f"four_{state}.jtl6.{field}",
            float(jtl["phase_delta_turns" if field == "phase_delta_turns" else "voltage_area_over_phi0"]),
            float(old_jtl[field]),
            abs_tolerance=TURNS_ABS,
            relative_tolerance=TURNS_REL,
        )

    expected_write = {}
    expected_read = {}
    for index in range(1, 5):
        expected_write[f"I(I_WL{index})"] = -100.0e-6
        expected_write[f"I(I_BL{index})"] = -100.0e-6
        expected_write[f"I(I_SE{index})"] = 0.0
        expected_read[f"I(I_WL{index})"] = 100.0e-6
        expected_read[f"I(I_BL{index})"] = 0.0
        expected_read[f"I(I_SE{index})"] = 100.0e-6
    stimulus = validate_bvm_write_read_protocol(
        trace,
        trace.time,
        write_window_s=window(51.0, 60.0),
        read_window_s=window(111.0, 120.0),
        expected_write=expected_write,
        expected_read=expected_read,
        tolerance=1.0e-12,
    )
    exact_check(checks, f"four_{state}.stimulus.status", stimulus["status"], "PROTOCOL_VALID")

    required = (
        available_bvm_labels(trace)
        + flatten_probe_labels(original_bvmsim_qb_probes())
        + flatten_probe_labels(historical_jtl_probes(6))
    )
    log_path = deck_path.parent / "logs/run-01.log"
    qa = deck_qa(
        deck_path,
        log_text=log_path.read_text(encoding="utf-8"),
        expected_includes=(
            "BVMSim/bvm_cell.cir",
            "BVMSim/BQ.cir",
            "BVMSim/library_josim/jtl2.cir",
        ),
        expected_bvm_instances=4,
        expected_terminal_sensing_jj_count=12,
        expected_jtl_stages=6,
        expected_termination_ohm=10.0,
        expected_tran_timestep_ps=0.1,
        required_probes=required,
        raw_headers=trace.headers,
    )
    exact_check(checks, f"four_{state}.deckqa.status", qa["status"], "ARTIFACT_VALID")
    exact_check(checks, f"four_{state}.deckqa.raw_missing", qa["raw_missing_probes"], [])

    # Existing four-BVM analysis includes KCL residuals. Recompute one full
    # equation through the already shared KCL helper as a regression anchor.
    kcl_branches = {
        "I_BJs": trace.column("I(BJS|XBQ1)"),
        "I_BJ1": trace.column("I(BJ1|XBQ1)"),
        "I_RJ1": trace.column("I(RJ1|XBQ1)"),
        "I_L1": trace.column("I(L1|XBQ1)"),
    }
    residual = linear_kcl_residual(
        kcl_branches,
        {"I_BJs": -1.0, "I_BJ1": 1.0, "I_RJ1": 1.0, "I_L1": 1.0},
    )
    shared_kcl = kcl_window_metrics(trace.time, residual, event_window, unit="A")
    old_kcl = old["kcl_READ1"]["QB_node2"]["metrics"]
    scalar_check(
        checks,
        f"four_{state}.kcl.node1.max_abs_uA",
        float(shared_kcl["max_abs_uA"]),
        float(old_kcl["max_abs_uA"]),
        abs_tolerance=WAVEFORM_ABS,
        relative_tolerance=WAVEFORM_REL,
    )
    return {
        "case": f"four_{state}",
        "raw": rel(raw_path),
        "raw_sha256": sha256_file(raw_path),
        "deck": rel(deck_path),
        "deck_sha256": sha256_file(deck_path),
        "shared_qb": {
            "phase_delta_turns": shared["phase_delta_turns"],
            "voltage_area_turns": shared["voltage_area_turns"],
            "phase_area_consistent": shared["phase_area_consistency"]["phase_area_consistent"],
        },
        "shared_jtl6": {
            "phase_delta_turns": jtl["phase_delta_turns"],
            "voltage_area_turns": jtl["voltage_area_turns"],
        },
        "shared_stimulus_status": stimulus["status"],
        "deckqa": qa,
    }


def main() -> int:
    checks: list[dict[str, object]] = []
    cases: list[dict[str, object]] = []
    for case in ("S0-J-CORRECTED-RERUN", "S1-J-CORRECTED-RERUN"):
        cases.append(
            evaluate_single(
                checks,
                case,
                SINGLE_ROOT / f"runs/{case}/raw/run-01.csv",
                SINGLE_ROOT / f"runs/{case}/deck.cir",
            )
        )
    cases.append(evaluate_four(checks))
    failed = [item for item in checks if not bool(item["pass"])]
    result = {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "phase": "A",
        "simulation_invoked": False,
        "status": "INFRA_REGRESSION_PASS" if not failed else "INFRA_REGRESSION_FAIL",
        "tolerances": {
            "turns_abs": TURNS_ABS,
            "turns_rel": TURNS_REL,
            "waveform_display_abs": WAVEFORM_ABS,
            "waveform_display_rel": WAVEFORM_REL,
        },
        "checks": checks,
        "failed_checks": failed,
        "cases": cases,
        "source_metrics": {
            "single": rel(SINGLE_ROOT / "analysis/metrics.json"),
            "single_sha256": sha256_file(SINGLE_ROOT / "analysis/metrics.json"),
            "four": rel(FOUR_ROOT / "analysis/metrics.json"),
            "four_sha256": sha256_file(FOUR_ROOT / "analysis/metrics.json"),
        },
        "raw_policy": "existing raw read only; no rewrite or new JoSIM run",
    }
    json_write(EXP / "parity/parity.json", result)
    report_lines = [
        "# PHASE A — shared tooling golden parity",
        "",
        f"- Status: `{result['status']}`",
        "- Simulation invoked: `false`",
        "- Golden inputs: corrected single-BVM S0-J/S1-J and historical 4-BVM 1111",
        f"- Checks: `{len(checks)}` total, `{len(failed)}` failed",
        "",
        "本报告只记录 measurement implementation parity；不产生新的物理 verdict。",
        "旧实验 raw、deck、metrics、plots、reports 和 analysis outputs 未被修改。",
        "",
    ]
    if failed:
        report_lines.extend(
            [
                "## Failed checks",
                "",
                *[f"- `{item['name']}`: observed={item.get('observed')!r}, expected={item.get('expected')!r}" for item in failed],
                "",
                "PHASE B blocked by parity failure.",
            ]
        )
    else:
        report_lines.extend(
            [
                "## Passed scope",
                "",
                "- same-JJ phase/area arithmetic and explicit consistency",
                "- waveform window and peak timing summaries",
                "- strict event-list anchor fields for historical 1111",
                "- caller-declared WL+BL WRITE / WL+SE READ plateau validation",
                "- hierarchical probe coverage and static deck/header QA",
                "- shared KCL residual arithmetic anchor",
                "",
                "结论：`INFRA_REGRESSION_PASS`，现在才允许进入 PHASE B。",
            ]
        )
    (EXP / "PHASE_A_REPORT.md").write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "checks": len(checks), "failed": len(failed)}))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
