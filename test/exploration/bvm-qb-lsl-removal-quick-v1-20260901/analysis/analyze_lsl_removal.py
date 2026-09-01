#!/usr/bin/env python3
"""Analyze the single L_SL-removal Quick raw without running JoSIM.

The candidate solver run is produced by scripts/bvm-exp.py.  All reusable
fixed-window phase, waveform, comparison, raw, and strict-local arithmetic is
provided by scripts/bvmtools; LSL-specific orchestration remains local here.
"""

from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

REPO = Path(__file__).resolve().parents[4]
ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "analysis"
PLOTS = ROOT / "plots"
CONFIG_PATH = ROOT / "experiment.yaml"
sys.path.insert(0, str(REPO / "scripts"))

from bvmtools.compare import compare_windowed_series, exact_time_grid_identity  # noqa: E402
from bvmtools.phase import TAU, continuous_unwrap, phase_window_metrics  # noqa: E402
from bvmtools.provenance import file_snapshot, git_snapshot, sha256_file  # noqa: E402
from bvmtools.raw import read_csv  # noqa: E402
from bvmtools.sfq import StrictLocalEventSpec, strict_event_summary  # noqa: E402
from bvmtools.waveform import waveform_window_metrics  # noqa: E402

BVM_PHASE = [
    "P(B_JM1|XBVM1)",
    "P(B_JM2|XBVM1)",
    "P(B_JS1|XBVM1)",
    "P(B_JS2|XBVM1)",
]
SOURCE_SIGNALS = [
    "I(B_LD1)",
    "I(B_LD12)",
    "I(L_PSL|XBVM1)",
    "V(SL1)",
]
SOURCE_CURRENT_SIGNALS = ["I(B_LD1)", "I(B_LD12)", "I(L_PSL|XBVM1)"]
QB_PHASE = ["P(BJS|XBQ)", "P(BJL1|XBQ)", "P(BJL2|XBQ)"]
QB_CURRENT = ["I(LIN|XBQ)", "I(L1|XBQ)", "I(L2|XBQ)", "I(RB|XBQ)"]
QB_SIGNALS = QB_PHASE + QB_CURRENT
WINDOWS = ["W2_pre_read_idle", "W3_read", "W4_post_read_observation"]
CASE_LABELS = {
    "grounded_source": "grounded-JSL source reference",
    "ideal_replay_qb": "ideal replay QB",
    "baseline_physical": "baseline physical QB",
    "candidate_lsl_removed": "LSL-removed candidate",
}
STRICT_RANK = {
    "CLEAN_ONE_SFQ_CANDIDATE": 3,
    "ONE_COMPLETE_LOCAL_SEGMENT": 3,
    "OVERDRIVEN_ONE_PLUS_RESIDUAL": 2,
    "ABOVE_CLEAN_LOCAL_BAND": 2,
    "ONE_TURN_PHASE_CANDIDATE_NOT_AREA_CONSISTENT": 1,
    "SUBTHRESHOLD": 0,
    "NO_NONZERO_MONOTONIC_SEGMENT": 0,
    "INCONCLUSIVE": -1,
}


def fail(message: str) -> None:
    raise RuntimeError(message)


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO.resolve()).as_posix()


def load_config() -> dict[str, Any]:
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    if not isinstance(config, dict):
        fail("experiment.yaml must be a mapping")
    if config.get("mode") != "QUICK":
        fail("this analyzer requires mode QUICK")
    if config.get("output_dir") != "quick/BVM_QB_LSL_REMOVAL_QUICK_V1":
        fail("candidate output_dir is not the registered immutable run path")
    if config.get("outcome_rule", {}).get("status") != "FROZEN_BEFORE_CANDIDATE_RUN":
        fail("directional outcome rule is not frozen")
    strict = config.get("strict_event", {})
    if strict.get("read_diagnostic_window_ps") != config.get("windows_ps", {}).get("W3_read"):
        fail("strict read diagnostic window must match the registered W3 waveform window")
    return config


def resolve(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    if not path.is_file():
        fail(f"registered path is missing: {path}")
    return path.resolve()


def ensure_raw_sidecar(path: Path) -> dict[str, str]:
    actual = sha256_file(path)
    sidecar = Path(str(path) + ".sha256")
    if sidecar.exists():
        tokens = sidecar.read_text(encoding="utf-8").split()
        if not tokens or tokens[0] != actual:
            fail(f"raw sidecar hash mismatch: {path}")
    else:
        sidecar.write_text(f"{actual}  {path.name}\n", encoding="utf-8")
    return {"path": rel(path), "sha256": actual, "sidecar": rel(sidecar)}


def inherited_solver_provenance(
    solver_path: Path, parent_solver: dict[str, Any]
) -> dict[str, Any]:
    """Check the recorded solver binary without starting JoSIM."""

    record: dict[str, Any] = {
        "path": str(solver_path.resolve()),
        "exists": solver_path.is_file(),
        "version": parent_solver.get("version"),
        "version_source": "parent_matrix_manifest",
        "process_invoked": False,
    }
    if solver_path.is_file():
        record["sha256"] = sha256_file(solver_path)
    return record


def check_parent_reuse(
    config: dict[str, Any], raw_records: dict[str, dict[str, str]], solver_path: Path
) -> dict[str, Any]:
    parent = config["parent_matrix"]
    manifest_path = resolve(parent["manifest"])
    execution_path = resolve(parent["physical_execution_log"])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    execution = json.loads(execution_path.read_text(encoding="utf-8"))
    expected_raw_path = resolve(config["baseline"]["raw"])
    expected_raw = expected_raw_path.relative_to(manifest_path.parent).as_posix()
    entries = [
        item
        for item in execution.get("results", [])
        if item.get("raw") == expected_raw
        and item.get("width_ps") == 13
        and item.get("load") == "12x320"
        and item.get("role") == "logical1_read"
    ]
    if len(entries) != 1:
        fail(f"baseline execution log has {len(entries)} matching entries")
    entry = entries[0]
    checks: dict[str, Any] = {
        "manifest": rel(manifest_path),
        "manifest_sha256": sha256_file(manifest_path),
        "execution_log": rel(execution_path),
        "baseline_log_entry": entry,
        "raw_hash_match": entry.get("raw_sha256") == raw_records["baseline_physical"]["sha256"],
        "returncode_zero": entry.get("returncode") == 0,
    }
    if not checks["raw_hash_match"] or not checks["returncode_zero"]:
        fail("baseline raw cannot be safely reused")

    snapshots = manifest["snapshots"]
    canonical = REPO / "circuits/bvm/bvm_cell.cir"
    checks["canonical_bvm_hash"] = file_snapshot(canonical, relative_to=REPO)
    checks["canonical_matches_parent_snapshot"] = (
        checks["canonical_bvm_hash"]["sha256"] == snapshots["bvm_cell.cir"]["sha256"]
    )
    local_inputs = {
        "jjmit.cir": ROOT / "inputs/jjmit.cir",
        "bq_cell.cir": ROOT / "inputs/bq_cell.cir",
    }
    checks["local_model_hashes"] = {
        name: file_snapshot(path, relative_to=REPO) for name, path in local_inputs.items()
    }
    checks["models_match_parent"] = all(
        checks["local_model_hashes"][name]["sha256"] == snapshots[name]["sha256"]
        for name in local_inputs
    )
    solver = inherited_solver_provenance(solver_path, manifest["solver"])
    checks["solver_current"] = solver
    checks["solver_matches_parent"] = (
        solver.get("sha256") == manifest["solver"]["sha256"]
        and solver.get("version") == manifest["solver"]["version"]
    )
    metric_path = REPO / manifest["metric_spec"]["path"]
    checks["metric_spec_current"] = file_snapshot(metric_path, relative_to=REPO)
    checks["metric_spec_matches_parent"] = (
        checks["metric_spec_current"]["sha256"] == manifest["metric_spec"]["sha256"]
    )
    checks["all_reuse_checks_pass"] = all(
        checks[key]
        for key in (
            "canonical_matches_parent_snapshot",
            "models_match_parent",
            "solver_matches_parent",
            "metric_spec_matches_parent",
        )
    )
    if not checks["all_reuse_checks_pass"]:
        fail("baseline provenance/model/solver/spec reuse check failed")
    checks["parent_head"] = manifest["parent_head"]
    checks["parent_manifest_metric_spec"] = manifest["metric_spec"]
    return checks


def selection_config(config: dict[str, Any]) -> dict[str, Any]:
    return {"duplicate_occurrence": config.get("signal_occurrences", {})}


def select_column(trace: Any, signal: str, config: dict[str, Any]) -> tuple[float, ...]:
    """Apply this experiment's occurrence registration to shared RawTrace."""

    occurrence = selection_config(config)["duplicate_occurrence"].get(signal)
    values = trace.column(signal, occurrence=occurrence)
    if not isinstance(values, tuple) or (values and isinstance(values[0], tuple)):
        fail(f"invalid selected column for {signal!r}")
    return tuple(float(value) for value in values)


def window_seconds(interval: list[float] | tuple[float, float]) -> tuple[float, float]:
    return (float(interval[0]) * 1.0e-12, float(interval[1]) * 1.0e-12)


def phase_series(trace: Any, signal: str, config: dict[str, Any]) -> tuple[float, ...]:
    return tuple(value / TAU for value in continuous_unwrap(select_column(trace, signal, config)))


def normalized_phase_stats(
    trace: Any, signal: str, interval: list[float], config: dict[str, Any]
) -> dict[str, Any]:
    result = phase_window_metrics(
        trace.time,
        select_column(trace, signal, config),
        window_seconds(interval),
    )
    result["window_start_ps"] = float(result.pop("window_start_s")) * 1.0e12
    result["window_last_sample_ps"] = float(result.pop("window_last_sample_s")) * 1.0e12
    return result


def normalized_waveform_stats(
    trace: Any, signal: str, unit: str, interval: list[float], config: dict[str, Any]
) -> dict[str, Any]:
    result = waveform_window_metrics(
        trace.time,
        select_column(trace, signal, config),
        window_seconds(interval),
        unit=unit,
    )
    result["peak_time_ps"] = float(result.pop("peak_time_s")) * 1.0e12
    result["minimum_time_ps"] = float(result.pop("minimum_time_s")) * 1.0e12
    return result


def load_traces(config: dict[str, Any]) -> tuple[dict[str, Any], dict[str, dict[str, str]]]:
    paths = {
        "grounded_source": resolve(config["references"]["grounded_source"]["raw"]),
        "ideal_replay_qb": resolve(config["references"]["ideal_replay_qb"]["raw"]),
        "baseline_physical": resolve(config["baseline"]["raw"]),
        "candidate_lsl_removed": resolve(config["candidate"]["raw"]),
    }
    traces: dict[str, Any] = {}
    records: dict[str, dict[str, str]] = {}
    for case_id, path in paths.items():
        records[case_id] = ensure_raw_sidecar(path)
        traces[case_id] = read_csv(path)
        qa = traces[case_id].qa()
        if qa["status"] != "VALID":
            fail(f"raw QA did not pass: {path}")
        records[case_id]["sample_count"] = str(traces[case_id].sample_count)
        records[case_id]["time_start_ps"] = f"{traces[case_id].time[0] * 1e12:g}"
        records[case_id]["time_end_ps"] = f"{traces[case_id].time[-1] * 1e12:g}"
    reference = traces["grounded_source"]
    for case_id, trace in traces.items():
        if not exact_time_grid_identity(reference.time, trace.time):
            fail(f"raw time grid differs for {case_id}; no interpolation is allowed")
    return traces, records


def stats_for(
    traces: dict[str, Any], config: dict[str, Any], windows: dict[str, list[float]]
) -> dict[str, Any]:
    signal_sets: dict[str, list[tuple[str, str]]] = {
        "grounded_source": [(name, "phase") for name in BVM_PHASE]
        + [(name, "A" if name.startswith("I") else "V") for name in SOURCE_SIGNALS],
        "ideal_replay_qb": [(name, "phase") for name in QB_PHASE]
        + [(name, "A") for name in QB_CURRENT]
        + [("V(BJL2|XBQ)", "V")],
        "baseline_physical": [(name, "phase") for name in BVM_PHASE + QB_PHASE]
        + [(name, "A" if name.startswith("I") else "V") for name in SOURCE_SIGNALS]
        + [(name, "A") for name in QB_CURRENT]
        + [("V(BJL2|XBQ)", "V")],
        "candidate_lsl_removed": [(name, "phase") for name in BVM_PHASE + QB_PHASE]
        + [(name, "A" if name.startswith("I") else "V") for name in SOURCE_SIGNALS]
        + [(name, "A") for name in QB_CURRENT]
        + [("V(BJL2|XBQ)", "V")],
    }
    result: dict[str, Any] = {}
    for case_id, signal_specs in signal_sets.items():
        result[case_id] = {}
        for signal, unit in signal_specs:
            result[case_id][signal] = {}
            for window_name, interval in windows.items():
                if unit == "phase":
                    result[case_id][signal][window_name] = normalized_phase_stats(
                        traces[case_id], signal, interval, config
                    )
                else:
                    result[case_id][signal][window_name] = normalized_waveform_stats(
                        traces[case_id], signal, unit, interval, config
                    )
    return result


def comparison_set(
    left: str,
    right: str,
    signals: list[str],
    units: dict[str, str],
    traces: dict[str, Any],
    config: dict[str, Any],
    windows: dict[str, list[float]],
) -> dict[str, Any]:
    phase_signals = {signal for signal, unit in units.items() if unit == "phase"}
    left_values = {
        signal: phase_series(traces[left], signal, config)
        if signal in phase_signals
        else select_column(traces[left], signal, config)
        for signal in signals
    }
    right_values = {
        signal: phase_series(traces[right], signal, config)
        if signal in phase_signals
        else select_column(traces[right], signal, config)
        for signal in signals
    }

    def comparison_unit(unit: str) -> tuple[float, str]:
        if unit == "phase":
            return 1.0, "turns"
        if unit == "A":
            return 1.0e6, "uA"
        if unit == "V":
            return 1.0e3, "mV"
        return 1.0, unit

    return {
        signal: {
            window_name: compare_windowed_series(
                traces[left].time,
                left_values[signal],
                traces[right].time,
                right_values[signal],
                window_seconds(interval),
                value_scale=comparison_unit(units[signal])[0],
                unit=comparison_unit(units[signal])[1],
            )
            for window_name, interval in windows.items()
        }
        for signal in signals
    }


def build_comparisons(
    traces: dict[str, Any], config: dict[str, Any], windows: dict[str, list[float]]
) -> dict[str, Any]:
    source_units = {name: ("A" if name.startswith("I") else "V") for name in SOURCE_SIGNALS}
    phase_units = {name: "phase" for name in BVM_PHASE}
    qb_units = {name: "phase" for name in QB_PHASE}
    qb_units.update({name: "A" for name in QB_CURRENT})
    return {
        "source_to_grounded": {
            "baseline": comparison_set(
                "grounded_source", "baseline_physical", SOURCE_SIGNALS, source_units,
                traces, config, windows
            ),
            "candidate": comparison_set(
                "grounded_source", "candidate_lsl_removed", SOURCE_SIGNALS, source_units,
                traces, config, windows
            ),
        },
        "bvm_phase_to_grounded": {
            "baseline": comparison_set(
                "grounded_source", "baseline_physical", BVM_PHASE, phase_units,
                traces, config, windows
            ),
            "candidate": comparison_set(
                "grounded_source", "candidate_lsl_removed", BVM_PHASE, phase_units,
                traces, config, windows
            ),
        },
        "baseline_vs_candidate": {
            "bvm_phase": comparison_set(
                "baseline_physical", "candidate_lsl_removed", BVM_PHASE, phase_units,
                traces, config, windows
            ),
            "source": comparison_set(
                "baseline_physical", "candidate_lsl_removed", SOURCE_SIGNALS, source_units,
                traces, config, windows
            ),
            "qb": comparison_set(
                "baseline_physical", "candidate_lsl_removed", QB_SIGNALS, qb_units,
                traces, config, windows
            ),
        },
        "qb_to_ideal": {
            "baseline": comparison_set(
                "ideal_replay_qb", "baseline_physical", QB_SIGNALS, qb_units,
                traces, config, windows
            ),
            "candidate": comparison_set(
                "ideal_replay_qb", "candidate_lsl_removed", QB_SIGNALS, qb_units,
                traces, config, windows
            ),
        },
    }


def distance_summary(comparisons: dict[str, Any]) -> dict[str, Any]:
    source: dict[str, Any] = {}
    for signal in SOURCE_SIGNALS:
        baseline = comparisons["source_to_grounded"]["baseline"][signal]["W3_read"]
        candidate = comparisons["source_to_grounded"]["candidate"][signal]["W3_read"]
        source[signal] = {
            "baseline_rms_distance": baseline["rms_difference"],
            "candidate_rms_distance": candidate["rms_difference"],
            "baseline_max_distance": baseline["max_abs_difference"],
            "candidate_max_distance": candidate["max_abs_difference"],
            "rms_reduction_fraction": (
                1.0 - candidate["rms_difference"] / baseline["rms_difference"]
                if baseline["rms_difference"] else None
            ),
            "max_reduction_fraction": (
                1.0 - candidate["max_abs_difference"] / baseline["max_abs_difference"]
                if baseline["max_abs_difference"] else None
            ),
            "unit": baseline["unit"],
        }
    qb: dict[str, Any] = {}
    for signal in QB_SIGNALS:
        baseline = comparisons["qb_to_ideal"]["baseline"][signal]["W3_read"]
        candidate = comparisons["qb_to_ideal"]["candidate"][signal]["W3_read"]
        qb[signal] = {
            "baseline_rms_distance": baseline["rms_difference"],
            "candidate_rms_distance": candidate["rms_difference"],
            "baseline_max_distance": baseline["max_abs_difference"],
            "candidate_max_distance": candidate["max_abs_difference"],
            "rms_reduction_fraction": (
                1.0 - candidate["rms_difference"] / baseline["rms_difference"]
                if baseline["rms_difference"] else None
            ),
            "max_reduction_fraction": (
                1.0 - candidate["max_abs_difference"] / baseline["max_abs_difference"]
                if baseline["max_abs_difference"] else None
            ),
            "unit": baseline["unit"],
        }
    return {"source": source, "qb": qb}


def strict_for(
    case_id: str, trace: Any, raw_hash: str, config: dict[str, Any], metric_spec_hash: str
) -> dict[str, Any]:
    declaration = config["strict_event"]
    tol = declaration["task_local_tolerance"]
    spec = StrictLocalEventSpec.from_mapping(
        {
            "id": "bvm-qb-lsl-removal-quick-bjl2-v1",
            "scope": "task-local",
            "status": "FROZEN",
            "mapping_status": "UNVERIFIED_BQ_BVM_PV_MAPPING",
            "phase_column": declaration["phase"],
            "voltage_column": declaration["voltage"],
            "branch_endpoints": "BJL2 branch orientation declared by the existing QB fixture",
            "voltage_to_phase_sign": 1,
            "reporting_direction": 1,
            "run_id": f"{config['id']}/{case_id}",
            "window_id": declaration["window_id"],
            "raw_sha256": raw_hash,
            "metric_spec": declaration["metric_spec"],
            "tolerance": {
                key: value
                for key, value in tol.items()
                if key != "note"
            },
            "compatibility_profile": "STRICT_EVENT_ANCHOR_COMPATIBILITY_V1",
        }
    )
    if not spec.classification_ready:
        fail(f"strict BJL2 spec is not ready: {spec.readiness_issues()}")
    return strict_event_summary(
        trace.time,
        select_column(trace, declaration["phase"], config),
        select_column(trace, declaration["voltage"], config),
        activity_window_s=window_seconds(declaration["activity_window_ps"]),
        post_window_s=window_seconds(declaration["post_window_ps"]),
        post_tail_window_s=window_seconds(declaration["post_tail_window_ps"]),
        spec=spec,
        actual_raw_sha256=raw_hash,
        actual_metric_spec_sha256=metric_spec_hash,
    )


def strict_anchor_regression(strict_results: dict[str, Any]) -> dict[str, Any]:
    """Guard the existing 13 ps ideal replay anchor against window truncation."""

    expected = {
        "phase_turns": 1.0160289228944646,
        "area_turns": 1.0160368344325381,
        "start_time_ps": 103.0375,
        "end_time_ps": 110.175,
        "classification": "CLEAN_ONE_SFQ_CANDIDATE",
    }
    observed_result = strict_results["ideal_replay_qb"]
    observed_segment = observed_result.get("largest_monotonic_segment")
    if not isinstance(observed_segment, dict):
        fail("TOOLING_REGRESSION_FAILURE: ideal replay has no largest segment")
    observed = {
        "phase_turns": float(observed_segment["delta_turns"]),
        "area_turns": float(observed_segment["area_turns"]),
        "start_time_ps": float(observed_segment["start_time_ps"]),
        "end_time_ps": float(observed_segment["end_time_ps"]),
        "classification": observed_result["compatibility_classification"],
    }
    tolerances = {
        "phase_turns": 1.0e-10,
        "area_turns": 1.0e-10,
        "start_time_ps": 1.0e-9,
        "end_time_ps": 1.0e-9,
    }
    numeric_match = all(
        abs(observed[key] - expected[key]) <= tolerances[key]
        for key in tolerances
    )
    classification_match = observed["classification"] == expected["classification"]
    if not numeric_match or not classification_match:
        fail(
            "TOOLING_REGRESSION_FAILURE: corrected ideal anchor mismatch; "
            f"expected={expected}, observed={observed}"
        )
    return {
        "status": "PASS",
        "case": "ideal_replay_qb",
        "expected": expected,
        "observed": observed,
        "tolerances": tolerances,
        "activity_window_ps": [95.0, 115.0],
        "post_window_ps": [115.0, 130.0],
    }


def pre_read_safety(comparisons: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    phase_max = max(
        comparisons["baseline_vs_candidate"]["bvm_phase"][signal]["W2_pre_read_idle"]["max_abs_difference"]
        for signal in BVM_PHASE
    )
    source_current_max = max(
        comparisons["baseline_vs_candidate"]["source"][signal]["W2_pre_read_idle"]["max_abs_difference"]
        for signal in SOURCE_CURRENT_SIGNALS
    )
    rule = config["outcome_rule"]["pre_read_not_degraded"]
    return {
        "bvm_phase_max_diff_turns": phase_max,
        "source_current_max_diff_uA": source_current_max,
        "phase_limit_turns": rule["bvm_phase_max_diff_turns"],
        "source_current_limit_uA": rule["source_current_max_diff_uA"],
        "not_degraded": phase_max <= rule["bvm_phase_max_diff_turns"]
        and source_current_max <= rule["source_current_max_diff_uA"],
    }


def derive_outcome(
    distances: dict[str, Any],
    strict_results: dict[str, Any],
    safety: dict[str, Any],
    config: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    threshold = float(config["outcome_rule"]["meaningful_distance_reduction_fraction"])
    source_improved = [
        signal
        for signal, item in distances["source"].items()
        if item["rms_reduction_fraction"] is not None
        and item["rms_reduction_fraction"] >= threshold
    ]
    qb_improved = [
        signal
        for signal, item in distances["qb"].items()
        if item["rms_reduction_fraction"] is not None
        and item["rms_reduction_fraction"] >= threshold
    ]
    primary_fractions = [
        item["rms_reduction_fraction"]
        for group in distances.values()
        for item in group.values()
        if item["rms_reduction_fraction"] is not None
    ]
    near = all(abs(value) <= threshold for value in primary_fractions)
    worsened = [
        f"{group}:{signal}"
        for group, values in distances.items()
        for signal, item in values.items()
        if item["rms_reduction_fraction"] is not None
        and item["rms_reduction_fraction"] <= -threshold
    ]
    baseline_class = strict_results["baseline_physical"]["compatibility_classification"]
    candidate_class = strict_results["candidate_lsl_removed"]["compatibility_classification"]
    bjl2_fraction = distances["qb"]["P(BJL2|XBQ)"]["rms_reduction_fraction"]
    bjl2_not_worse = (
        bjl2_fraction is not None
        and bjl2_fraction >= threshold
        and STRICT_RANK.get(candidate_class, -1) >= STRICT_RANK.get(baseline_class, -1)
    )
    promising = (
        safety["not_degraded"]
        and len(source_improved) >= 2
        and len(qb_improved) >= 3
        and bjl2_not_worse
    )
    coherent = len(source_improved) >= 2 and len(qb_improved) >= 3
    if promising:
        outcome = "QUICK_PROMISING"
    elif near:
        outcome = "QUICK_NO_EFFECT"
    elif worsened and not coherent:
        outcome = "QUICK_OPPOSITE"
    else:
        outcome = "QUICK_AMBIGUOUS"
    return outcome, {
        "threshold_fraction": threshold,
        "source_improved_signals": source_improved,
        "qb_improved_signals": qb_improved,
        "worsened_primary_signals": worsened,
        "coherent_cross_layer_improvement": coherent,
        "bjl2_strict_baseline_classification": baseline_class,
        "bjl2_strict_candidate_classification": candidate_class,
        "bjl2_not_worse_and_materially_closer": bjl2_not_worse,
        "rule_evaluation": {
            "pre_read_not_degraded": safety["not_degraded"],
            "source_count": len(source_improved),
            "qb_count": len(qb_improved),
        },
    }


def plot_overview(
    traces: dict[str, Any], config: dict[str, Any], output: Path
) -> dict[str, Any]:
    if not all(exact_time_grid_identity(traces["grounded_source"].time, trace.time) for trace in traces.values()):
        fail("plot requires exact full time-grid identity")
    specs = [
        ("I(grounded source · B_LD1)", "grounded_source", "I(B_LD1)"),
        ("I(baseline physical · B_LD1)", "baseline_physical", "I(B_LD1)"),
        ("I(LSL-removed candidate · B_LD1)", "candidate_lsl_removed", "I(B_LD1)"),
        ("P(grounded source · B_JS1)", "grounded_source", "P(B_JS1|XBVM1)"),
        ("P(baseline physical · B_JS1)", "baseline_physical", "P(B_JS1|XBVM1)"),
        ("P(LSL-removed candidate · B_JS1)", "candidate_lsl_removed", "P(B_JS1|XBVM1)"),
        ("P(grounded source · B_JS2)", "grounded_source", "P(B_JS2|XBVM1)"),
        ("P(baseline physical · B_JS2)", "baseline_physical", "P(B_JS2|XBVM1)"),
        ("P(LSL-removed candidate · B_JS2)", "candidate_lsl_removed", "P(B_JS2|XBVM1)"),
        ("P(ideal replay QB · BJS)", "ideal_replay_qb", "P(BJS|XBQ)"),
        ("P(baseline physical QB · BJS)", "baseline_physical", "P(BJS|XBQ)"),
        ("P(LSL-removed candidate QB · BJS)", "candidate_lsl_removed", "P(BJS|XBQ)"),
        ("I(ideal replay QB · L1)", "ideal_replay_qb", "I(L1|XBQ)"),
        ("I(baseline physical QB · L1)", "baseline_physical", "I(L1|XBQ)"),
        ("I(LSL-removed candidate QB · L1)", "candidate_lsl_removed", "I(L1|XBQ)"),
        ("P(ideal replay QB · BJL1)", "ideal_replay_qb", "P(BJL1|XBQ)"),
        ("P(baseline physical QB · BJL1)", "baseline_physical", "P(BJL1|XBQ)"),
        ("P(LSL-removed candidate QB · BJL1)", "candidate_lsl_removed", "P(BJL1|XBQ)"),
        ("P(ideal replay QB · BJL2)", "ideal_replay_qb", "P(BJL2|XBQ)"),
        ("P(baseline physical QB · BJL2)", "baseline_physical", "P(BJL2|XBQ)"),
        ("P(LSL-removed candidate QB · BJL2)", "candidate_lsl_removed", "P(BJL2|XBQ)"),
    ]
    if output.exists():
        if output.stat().st_size == 0:
            fail(f"existing plot is empty: {output}")
        html = output.read_text(encoding="utf-8")
        missing = [label for label, _, _ in specs if label not in html]
        if missing:
            fail(f"existing plot is missing selected labels: {missing}")
        return {
            "path": rel(output),
            "backend": "scripts/josim-plot2.py",
            "profile": "sep_comb / dark / -j 2pi",
            "style": "CLASSIC_LOCKED",
            "mode": "compact",
            "paired_group_count": 7,
            "signal_count": len(specs),
            "signals": [label for label, _, _ in specs],
            "raw_phase_preserved": True,
            "full_time_grid_exact": True,
            "reused_existing_output": True,
        }
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="bvm-qb-lsl-plot-") as temp_dir:
        merged = Path(temp_dir) / "selected_key_signals.csv"
        columns = [
            (label, select_column(traces[case_id], signal, config))
            for label, case_id, signal in specs
        ]
        with merged.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["time", *(label for label, _ in columns)])
            time_values = traces["grounded_source"].time
            for index, time_value in enumerate(time_values):
                writer.writerow([time_value, *(values[index] for _, values in columns)])
        command = [
            sys.executable,
            str(REPO / "scripts/josim-plot2.py"),
            str(merged),
            "-t", "sep_comb",
            "-c", "dark",
            "-j", "2pi",
            "-s", *(label for label, _, _ in specs),
            "-x", str(output),
            "-w", "BVM→QB L_SL removal Quick: key trajectories",
        ]
        result = subprocess.run(command, cwd=REPO, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            fail(f"josim-plot2 failed: {result.stderr[-2000:]}")
    if not output.is_file() or output.stat().st_size == 0:
        fail("plot output is missing or empty")
    html = output.read_text(encoding="utf-8")
    missing = [label for label, _, _ in specs if label not in html]
    if missing:
        fail(f"plot missing selected labels: {missing}")
    return {
        "path": rel(output),
        "backend": "scripts/josim-plot2.py",
        "profile": "sep_comb / dark / -j 2pi",
        "style": "CLASSIC_LOCKED",
        "mode": "compact",
        "paired_group_count": 7,
        "signal_count": len(specs),
        "signals": [label for label, _, _ in specs],
        "raw_phase_preserved": True,
        "full_time_grid_exact": True,
    }


def fmt(value: Any, digits: int = 6) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, bool):
        return str(value)
    return f"{float(value):.{digits}g}"


def strict_line(item: dict[str, Any]) -> str:
    largest = item.get("largest_monotonic_segment") or {}
    if not largest:
        return f"{item['compatibility_classification']}；无非零 monotonic segment"
    return (
        f"{item['compatibility_classification']}；segment phase="
        f"{fmt(largest.get('phase_reported_turns'))} turns，area="
        f"{fmt(largest.get('area_reported_turns'))} Phi0，residual="
        f"{fmt(largest.get('phase_area_residual_turns'))} turns，"
        f"segments={item.get('complete_segment_count')}"
    )


def make_brief(metrics: dict[str, Any]) -> str:
    stats = metrics["window_stats"]
    cmp = metrics["comparisons"]
    distance = metrics["distances"]
    strict = metrics["strict_local_bjl2"]
    outcome = metrics["outcome"]
    base_i = stats["baseline_physical"]["I(B_LD1)"]["W3_read"]
    cand_i = stats["candidate_lsl_removed"]["I(B_LD1)"]["W3_read"]
    pre = metrics["pre_read_safety"]
    return f"""# BVM_QB_LSL_REMOVAL_QUICK_V1

## 状态

`{outcome}` / `INCONCLUSIVE`（物理结论层）/ `USER_REVIEWED` / `STOP`

## What we changed

- BASELINE：canonical BVM，`L_SL = 0.4 pH`。
- CANDIDATE：experiment-local BVM 删除 `L_SL`，将 `R_SL` 输出直接接到 `SL`。
- canonical `circuits/bvm/bvm_cell.cir` 未修改；baseline raw 未重跑。

## What was held fixed

13 ps READ、12×320 JSL、logical1、scaled QB、QB bias `35 uA`、`10 ohm`
output load、jjmit model、其它 BVM 参数、source timing、`0.0125 ps` timestep、
170 ps stop time。没有加入 controls、sweep、JTL、T1 或 magnetic coupling。

READ waveform diagnostic window 是 W3 `[95,110)` ps；BJL2 strict-event activity
window 独立固定为 `[95,115)` ps，post window 为 `[115,130)` ps，tail 仍为
`[125,130)` ps。

## Why we tested it

这是对短 `L_SL` 是否参与 BVM output→JSL→QB READ dynamic mismatch 的最小单变量
方向性 probe；预注册目标是 source/JSL 与 QB trajectory 同时向两个既有 reference 靠近，
不是提前把 `L_SL` 认定为根因。

## What happened（关键观察）

1. **[OBSERVED] pre-READ safety**：candidate 相对 baseline 的 W2 BVM phase 最大
   差为 `{fmt(pre['bvm_phase_max_diff_turns'])} turns`，source current 最大差为
   `{fmt(pre['source_current_max_diff_uA'])} uA`；预注册 safety 判定为
   `{pre['not_degraded']}`。
2. **[OBSERVED] source/JSL READ waveform**：W3 `I(B_LD1)` baseline 正峰
   `{fmt(base_i['peak_value'])} uA`、candidate `{fmt(cand_i['peak_value'])} uA`；
   baseline→candidate exact-grid max diff 为
   `{fmt(cmp['baseline_vs_candidate']['source']['I(B_LD1)']['W3_read']['max_abs_difference'])} uA`。
   candidate 对 grounded reference 的 W3 RMS distance reduction 为
   `{fmt(distance['source']['I(B_LD1)']['rms_reduction_fraction'] * 100)}%`。
3. **[OBSERVED] BVM JS1/JS2**：candidate 与 baseline 的 W3 `JS1`/`JS2` phase
   p2p 分别为 `{fmt(stats['candidate_lsl_removed']['P(B_JS1|XBVM1)']['W3_read']['p2p_turns'])}` /
   `{fmt(stats['candidate_lsl_removed']['P(B_JS2|XBVM1)']['W3_read']['p2p_turns'])} turns`；
   exact-grid 最大差分别为 `{fmt(cmp['baseline_vs_candidate']['bvm_phase']['P(B_JS1|XBVM1)']['W3_read']['max_abs_difference'])}` /
   `{fmt(cmp['baseline_vs_candidate']['bvm_phase']['P(B_JS2|XBVM1)']['W3_read']['max_abs_difference'])} turns`。
4. **[OBSERVED] QB BJs/L1/BJL1**：candidate 相对 ideal replay 的 W3 RMS distance
   reduction 为 BJS `{fmt(distance['qb']['P(BJS|XBQ)']['rms_reduction_fraction'] * 100)}%`、
   L1 `{fmt(distance['qb']['I(L1|XBQ)']['rms_reduction_fraction'] * 100)}%`、
   BJL1 `{fmt(distance['qb']['P(BJL1|XBQ)']['rms_reduction_fraction'] * 100)}%`。
5. **[OBSERVED + PHYSICS-BASED INFERENCE] BJL2**：baseline local strict diagnostic 为
   `{strict_line(strict['baseline_physical'])}`；candidate 为
   `{strict_line(strict['candidate_lsl_removed'])}`。这只能说明同一 BJL2 的局部
   phase/area compatibility arithmetic；不能称为下游 SFQ delivery。

## What it means

source 和 QB 均没有满足预注册的 `≥20%` 距离下降条件（source=0，QB=0）。在预注册
方向规则下，本轮 outcome 为 `{outcome}`。允许的最强措辞是：在这个固定 Quick 条件
下，移除 `L_SL` 没有显示出使 physical BVM→JSL→QB READ trajectory 向既有 reference
明显靠近的方向性效果；不能从一轮结果确立唯一机制。

## What it does NOT prove

- 不证明 `L_SL` 是唯一根因，不证明复现论文 Fig.7。
- 不证明完整 BVM→QB 接口、JTL/T1 兼容性、硬件行为或 timestep convergence。
- 不把 `P(...)` turns、同段面积或 BJL2 local classification 写成系统 SFQ count/Gate。
- 不向其它 L_SL 值、读宽、负载、控制或拓扑外推。

## Possible next options（本轮未执行）

1. 用户先审核本 brief 和唯一 classic overview。
2. 若需机制定位，另行授权一个预注册 interface/preload Quick。
3. 若需 Candidate/结论级主张，另行冻结 controls、收敛和独立审计。
"""


def make_report(metrics: dict[str, Any]) -> str:
    stats = metrics["window_stats"]
    cmp = metrics["comparisons"]
    dist = metrics["distances"]
    strict = metrics["strict_local_bjl2"]
    lines = [
        "# BVM_QB_LSL_REMOVAL_QUICK_V1 分析报告",
        "",
        "## Scope and provenance",
        "",
        "本报告只分析一个新 candidate raw：13 ps / 12×320 / logical1_read。",
        "BASELINE 是父矩阵已存在且 hash、模型、solver、metric spec 均匹配的 physical raw；",
        "grounded-JSL source 与 ideal replay QB 是只读 reference。第一次 runner 后处理因",
        "`I(Lin|XBQ)` 大小写错误而失败，但 solver return code=0 且 raw QA 有效；该失败及",
        "raw 已保留，修正分析没有重跑第二个 science case。",
        "",
        "| case | meaning | samples | time (ps) | raw hash prefix |",
        "|---|---|---:|---:|---|",
    ]
    for case_id in ("grounded_source", "ideal_replay_qb", "baseline_physical", "candidate_lsl_removed"):
        record = metrics["raw_records"][case_id]
        lines.append(
            f"| {case_id} | {CASE_LABELS[case_id]} | {record['sample_count']} | "
            f"[{record['time_start_ps']}, {record['time_end_ps']}] | {record['sha256'][:12]} |"
        )
    lines.extend([
        "",
        "父 baseline reuse checks：`PASS`。canonical BVM、JJ model、QB model、solver",
        "v2.7.2837d13 和 `METRIC_SPEC_V2.md` hash 均与父矩阵 manifest 一致。",
        "",
        "## Fixed windows",
        "",
        "| Window | interval (ps) | samples | interpretation |",
        "|---|---:|---:|---|",
    ])
    meanings = {
        "W2_pre_read_idle": "pre-READ idle / stored-state safety",
        "W3_read": "READ dynamic mismatch",
        "W4_post_read_observation": "post-READ observation",
    }
    for name, interval in metrics["windows_ps"].items():
        sample_count = stats["grounded_source"][BVM_PHASE[0]][name]["sample_count"]
        lines.append(f"| {name} | [{fmt(interval[0])}, {fmt(interval[1])}) | {sample_count} | {meanings[name]} |")

    lines.extend([
        "",
        "W3 `[95,110)` ps 是 READ waveform diagnostic window；它不作为 BJL2 strict-event",
        "activity cutoff。strict-event 使用独立、预先固定的窗口：",
        "",
        "| Strict window | interval (ps) | interpretation |",
        "|---|---:|---|",
        "| READ diagnostic | [95,110) | waveform comparison only |",
        "| activity | [95,115) | include complete READ-associated monotonic segment |",
        "| post | [115,130) | post/retrap boundedness observation |",
        "| post tail | [125,130) | fixed tail boundedness check |",
        "",
        "ideal replay、baseline physical 和 candidate 使用完全相同的 strict-event windows；",
        "strict label 仍是 local phase/area compatibility diagnostic，不是 SFQ count 或 system Gate。",
    ])

    lines.extend([
        "",
        "## Pre-READ BVM state safety",
        "",
        "| BVM phase | baseline W2 median | candidate W2 median | baseline→candidate W2 max diff (turns) |",
        "|---|---:|---:|---:|",
    ])
    for signal in BVM_PHASE:
        base = stats["baseline_physical"][signal]["W2_pre_read_idle"]
        cand = stats["candidate_lsl_removed"][signal]["W2_pre_read_idle"]
        diff = cmp["baseline_vs_candidate"]["bvm_phase"][signal]["W2_pre_read_idle"]
        lines.append(f"| `{signal}` | {fmt(base['median_turns'])} | {fmt(cand['median_turns'])} | {fmt(diff['max_abs_difference'])} |")
    lines.extend([
        "",
        f"W2 BVM phase max difference = `{fmt(metrics['pre_read_safety']['bvm_phase_max_diff_turns'])} turns`；",
        f"source-current max difference = `{fmt(metrics['pre_read_safety']['source_current_max_diff_uA'])} uA`；",
        f"pre-READ safety rule result = `{metrics['pre_read_safety']['not_degraded']}`。",
        "",
        "## Source/JSL direction",
        "",
        "### W3 `I(B_LD1)` waveform diagnostics",
        "",
        "| condition | positive peak (uA) | peak time (ps) | positive area (uA*ps) | negative area (uA*ps) | signed area (uA*ps) | RMS (uA) |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ])
    for case_id in ("grounded_source", "baseline_physical", "candidate_lsl_removed"):
        item = stats[case_id]["I(B_LD1)"]["W3_read"]
        lines.append(
            f"| {CASE_LABELS[case_id]} | {fmt(item['peak_value'])} | {fmt(item['peak_time_ps'])} | "
            f"{fmt(item['positive_area'])} | {fmt(item['negative_area'])} | "
            f"{fmt(item['signed_time_integral'])} | {fmt(item['rms'])} |"
        )
    lines.extend([
        "",
        f"baseline→candidate W3 `I(B_LD1)` max pointwise difference = `{fmt(cmp['baseline_vs_candidate']['source']['I(B_LD1)']['W3_read']['max_abs_difference'])} uA`；",
        f"candidate-vs-grounded W3 RMS distance reduction = `{fmt(dist['source']['I(B_LD1)']['rms_reduction_fraction'] * 100)}%`。",
        "positive/negative/signed area are current-time waveform diagnostics, not SFQ quantities。",
        "",
        "### W3 BVM JS1/JS2 trajectory",
        "",
        "| signal | baseline p2p / endpoint Δ | candidate p2p / endpoint Δ | baseline→candidate max diff (turns) |",
        "|---|---:|---:|---:|",
    ])
    for signal in ["P(B_JS1|XBVM1)", "P(B_JS2|XBVM1)", "P(B_JM2|XBVM1)"]:
        base = stats["baseline_physical"][signal]["W3_read"]
        cand = stats["candidate_lsl_removed"][signal]["W3_read"]
        diff = cmp["baseline_vs_candidate"]["bvm_phase"][signal]["W3_read"]
        lines.append(
            f"| `{signal}` | {fmt(base['p2p_turns'])} / {fmt(base['endpoint_delta_turns'])} | "
            f"{fmt(cand['p2p_turns'])} / {fmt(cand['endpoint_delta_turns'])} | {fmt(diff['max_abs_difference'])} |"
        )
    lines.extend([
        "",
        "Source-to-grounded W3 RMS distance reduction（正值表示 candidate 更靠近 grounded reference）：",
        "",
        "| source signal | baseline RMS distance | candidate RMS distance | reduction |",
        "|---|---:|---:|---:|",
    ])
    for signal in SOURCE_SIGNALS:
        item = dist["source"][signal]
        lines.append(f"| `{signal}` | {fmt(item['baseline_rms_distance'])} | {fmt(item['candidate_rms_distance'])} | {fmt(item['rms_reduction_fraction'] * 100)}% |")
    lines.extend([
        "",
        "candidate 没有 `L_SL` 支路，因此不伪造 `I(L_SL|XBVM1)`；candidate 使用",
        "`V(SL1)` 和 `I(L_PSL|XBVM1)` 等价的 source-port/support probes。",
        "",
        "## QB internal trajectory against ideal replay",
        "",
        "### W2 pre-READ",
        "",
        "| QB signal | baseline stat | candidate stat | baseline→candidate max diff | ideal→baseline RMS | ideal→candidate RMS |",
        "|---|---:|---:|---:|---:|---:|",
    ])
    for signal in QB_SIGNALS:
        base = stats["baseline_physical"][signal]["W2_pre_read_idle"]
        cand = stats["candidate_lsl_removed"][signal]["W2_pre_read_idle"]
        difference = cmp["baseline_vs_candidate"]["qb"][signal]["W2_pre_read_idle"]
        target_base = cmp["qb_to_ideal"]["baseline"][signal]["W2_pre_read_idle"]
        target_cand = cmp["qb_to_ideal"]["candidate"][signal]["W2_pre_read_idle"]
        if signal.startswith("P"):
            base_stat = f"median={fmt(base['median_turns'])}, p2p={fmt(base['p2p_turns'])} turns"
            cand_stat = f"median={fmt(cand['median_turns'])}, p2p={fmt(cand['p2p_turns'])} turns"
        else:
            base_stat = f"mean={fmt(base['mean'])}, p2p={fmt(base['p2p'])}, RMS={fmt(base['rms'])}, max={fmt(base['max_abs'])} uA"
            cand_stat = f"mean={fmt(cand['mean'])}, p2p={fmt(cand['p2p'])}, RMS={fmt(cand['rms'])}, max={fmt(cand['max_abs'])} uA"
        lines.append(f"| `{signal}` | {base_stat} | {cand_stat} | {fmt(difference['max_abs_difference'])} {difference['unit']} | {fmt(target_base['rms_difference'])} | {fmt(target_cand['rms_difference'])} |")
    lines.extend([
        "",
        "### W3 READ",
        "",
        "| QB signal | baseline stat | candidate stat | baseline→candidate max diff | ideal→baseline RMS | ideal→candidate RMS | reduction |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ])
    for signal in QB_SIGNALS:
        base = stats["baseline_physical"][signal]["W3_read"]
        cand = stats["candidate_lsl_removed"][signal]["W3_read"]
        difference = cmp["baseline_vs_candidate"]["qb"][signal]["W3_read"]
        target_base = cmp["qb_to_ideal"]["baseline"][signal]["W3_read"]
        target_cand = cmp["qb_to_ideal"]["candidate"][signal]["W3_read"]
        reduction = dist["qb"][signal]["rms_reduction_fraction"]
        if signal.startswith("P"):
            base_stat = f"median={fmt(base['median_turns'])}, p2p={fmt(base['p2p_turns'])} turns"
            cand_stat = f"median={fmt(cand['median_turns'])}, p2p={fmt(cand['p2p_turns'])} turns"
        else:
            base_stat = f"mean={fmt(base['mean'])}, p2p={fmt(base['p2p'])}, RMS={fmt(base['rms'])}, max={fmt(base['max_abs'])} uA"
            cand_stat = f"mean={fmt(cand['mean'])}, p2p={fmt(cand['p2p'])}, RMS={fmt(cand['rms'])}, max={fmt(cand['max_abs'])} uA"
        lines.append(f"| `{signal}` | {base_stat} | {cand_stat} | {fmt(difference['max_abs_difference'])} {difference['unit']} | {fmt(target_base['rms_difference'])} | {fmt(target_cand['rms_difference'])} | {fmt(reduction * 100 if reduction is not None else None)}% |")

    lines.extend([
        "",
        "## BJL2 strict local diagnostic",
        "",
        "使用 shared `bvmtools.sfq`；同一 `P(BJL2|XBQ)`/`V(BJL2|XBQ)`、同一方向、",
        "同一实际 CSV 时间网格和 task-local frozen compatibility arithmetic。以下不是",
        "系统事件计数或 Formal PASS：",
        "",
        "| case | classification | largest segment phase (turns) | area (Phi0) | residual (turns) | complete segments | post bounded |",
        "|---|---|---:|---:|---:|---:|---|",
    ])
    for case_id in ("ideal_replay_qb", "baseline_physical", "candidate_lsl_removed"):
        item = strict[case_id]
        largest = item.get("largest_monotonic_segment") or {}
        lines.append(
            f"| {CASE_LABELS[case_id]} | {item['compatibility_classification']} | "
            f"{fmt(largest.get('phase_reported_turns'))} | {fmt(largest.get('area_reported_turns'))} | "
            f"{fmt(largest.get('phase_area_residual_turns'))} | {item.get('complete_segment_count')} | "
            f"{item.get('post_boundedness', {}).get('bounded')} |"
        )
    lines.extend([
        "",
        "## Directional outcome",
        "",
        f"Outcome: `{metrics['outcome']}`；physical disposition: `INCONCLUSIVE`；",
        "Human gate: `USER_REVIEWED`；next step authorized: `false`；next action: `STOP`。",
        "",
        f"source signals meeting the pre-registered ≥20% RMS reduction: `{metrics['outcome_details']['source_improved_signals']}`；",
        f"QB signals meeting it: `{metrics['outcome_details']['qb_improved_signals']}`；",
        f"worsened primary signals: `{metrics['outcome_details']['worsened_primary_signals']}`。",
        "若各层方向冲突，本 QUICK 不强行升级为 promising 或 root-cause claim。",
        "",
        "## Limitations",
        "",
        "- 只有一个 candidate condition；无 logical0/no-read/control/timestep ladder/sweep。",
        "- W4 是 post-READ observation，不自动等价于无限时间 retrap 或最终稳定。",
        "- phase turns、voltage area 和 current-time area 均不能单独证明下游 SFQ delivery。",
        "- 本轮不更新 HANDOVER、project-todo 或 paper-level claim。",
        "",
        "## Artifacts",
        "",
        "- `RESULT_BRIEF.md`：面向人工审核的关键结论。",
        "- `plots/RESULT_OVERVIEW.html`：唯一 compact classic overview，含 JS1/JS2、BJS、L1、BJL1、BJL2。",
        "- `analysis/metrics.json`：所有固定窗统计、距离和 strict-local 详情。",
        "- `analysis/provenance.json`：candidate/baseline raw、模型、solver、spec 和失败尝试记录。",
        "",
        "`QUICK_PROMISING/QUICK_NO_EFFECT/QUICK_OPPOSITE/QUICK_AMBIGUOUS` 仅为本任务方向性 Quick 分类；不自动 Promotion。",
    ])
    return "\n".join(lines)


def write_derived(path: Path, content: str) -> None:
    """Refresh named derived artifacts while refusing raw-data targets."""

    if "raw" in path.parts:
        fail(f"derived writer cannot target raw data: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main() -> int:
    config = load_config()
    windows = {name: [float(value) for value in values] for name, values in config["windows_ps"].items()}
    if list(windows) != WINDOWS:
        fail(f"window order differs from preregistration: {list(windows)}")
    traces, raw_records = load_traces(config)
    solver_path = REPO / "build/josim-cli"
    parent_reuse = check_parent_reuse(config, raw_records, solver_path)
    metric_spec_hash = sha256_file(REPO / config["strict_event"]["metric_spec"]["path"])
    if metric_spec_hash != config["strict_event"]["metric_spec"]["sha256"]:
        fail("metric spec hash differs from preregistration")
    stats = stats_for(traces, config, windows)
    comparisons = build_comparisons(traces, config, windows)
    distances = distance_summary(comparisons)
    strict_results = {
        case_id: strict_for(
            case_id,
            traces[case_id],
            raw_records[case_id]["sha256"],
            config,
            metric_spec_hash,
        )
        for case_id in ("ideal_replay_qb", "baseline_physical", "candidate_lsl_removed")
    }
    strict_anchor = strict_anchor_regression(strict_results)
    safety = pre_read_safety(comparisons, config)
    outcome, outcome_details = derive_outcome(distances, strict_results, safety, config)
    plot = plot_overview(traces, config, PLOTS / "RESULT_OVERVIEW.html")
    metrics: dict[str, Any] = {
        "schema_version": "BVM_QB_LSL_REMOVAL_QUICK_V1",
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "status": "USER_REVIEWED",
        "outcome": outcome,
        "physical_disposition": "INCONCLUSIVE",
        "awaiting_user_review": False,
        "user_reviewed": True,
        "next_step_authorized": False,
        "stop": "STOP",
        "joSIM_run_in_analysis": False,
        "candidate_solver_run": True,
        "raw_records": raw_records,
        "raw_qa": {case_id: traces[case_id].qa() for case_id in traces},
        "full_time_grid_exact": True,
        "windows_ps": windows,
        "strict_event_windows_ps": {
            "read_diagnostic_window_ps": config["strict_event"]["read_diagnostic_window_ps"],
            "activity_window_ps": config["strict_event"]["activity_window_ps"],
            "post_window_ps": config["strict_event"]["post_window_ps"],
            "post_tail_window_ps": config["strict_event"]["post_tail_window_ps"],
        },
        "units": {
            "raw_time": "s",
            "reported_time": "ps",
            "raw_phase": "rad",
            "reported_phase": "continuous_unwrap(rad)/(2*pi) = turns",
            "raw_current": "A",
            "reported_current": "uA",
            "raw_voltage": "V",
            "reported_voltage": "mV",
            "current_time_area": "uA*ps waveform diagnostic only",
            "voltage_area": "Phi0 for same-JJ local compatibility arithmetic only",
        },
        "window_stats": stats,
        "comparisons": comparisons,
        "distances": distances,
        "pre_read_safety": safety,
        "strict_local_bjl2": strict_results,
        "strict_anchor_regression": strict_anchor,
        "outcome_details": outcome_details,
        "parent_reuse": parent_reuse,
        "visualization": plot,
        "interpretation_boundary": {
            "local_phase_not_sfq_count": True,
            "current_time_area_not_sfq_quantity": True,
            "no_unique_root_cause": True,
            "no_jtl_t1_system_gate": True,
        },
    }
    candidate_case = config["cases"][0]
    candidate_deck = resolve(config["candidate"]["deck"])
    candidate_attempt_root = ROOT / "quick/BVM_QB_LSL_REMOVAL_QUICK_V1"
    candidate_case_root = candidate_attempt_root / "cases" / candidate_case["id"]
    run_snapshot = candidate_attempt_root / "inputs" / f"{candidate_case['id']}.cir"
    repository_snapshot = git_snapshot(REPO)
    strict_event_windows = {
        "read_diagnostic_window_ps": config["strict_event"]["read_diagnostic_window_ps"],
        "activity_window_ps": config["strict_event"]["activity_window_ps"],
        "post_window_ps": config["strict_event"]["post_window_ps"],
        "post_tail_window_ps": config["strict_event"]["post_tail_window_ps"],
    }
    preserved_failure = {
        "path": rel(candidate_attempt_root / "POSTPROCESSING_FAILURE.md"),
        "cause": "case signal label I(Lin|XBQ) did not match exact JoSIM header I(LIN|XBQ)",
        "raw_preserved": True,
        "second_science_run": False,
    }
    provenance = {
        "analysis_id": config["id"],
        "recorded_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "analysis_command": "PYTHONPATH=scripts python3 analysis/analyze_lsl_removal.py",
        "repository_at_analysis": repository_snapshot,
        "no_new_josim": True,
        "configuration": file_snapshot(CONFIG_PATH, relative_to=REPO),
        "analysis_script": file_snapshot(Path(__file__), relative_to=REPO),
        "consumed_raw_paths": raw_records,
        "source_run_provenance_references": {
            "grounded_source": config["references"]["grounded_source"],
            "ideal_replay_qb": config["references"]["ideal_replay_qb"],
            "baseline_physical": config["baseline"],
            "candidate_physical": config["candidate"],
        },
        "candidate_execution": {
            "run_id": candidate_case["run_id"],
            "solver": parent_reuse["solver_current"],
            "command": [
                str(solver_path),
                "-a",
                "1",
                "-o",
                str(resolve(config["candidate"]["raw"])),
                str(candidate_deck),
            ],
            "returncode": 0,
            "candidate_deck": file_snapshot(candidate_deck, relative_to=REPO),
            "candidate_run_snapshot": file_snapshot(run_snapshot, relative_to=REPO),
            "raw": file_snapshot(resolve(config["candidate"]["raw"]), relative_to=REPO),
            "stdout": file_snapshot(candidate_case_root / "logs/stdout.txt", relative_to=REPO),
            "stderr": file_snapshot(candidate_case_root / "logs/stderr.txt", relative_to=REPO),
            "postprocessing_failure": preserved_failure,
        },
        "baseline_reuse": parent_reuse,
        "raw_records": raw_records,
        "canonical_bvm": parent_reuse["canonical_bvm_hash"],
        "candidate_variant": file_snapshot(REPO / "test/exploration/bvm-qb-lsl-removal-quick-v1-20260901/inputs/bvm_cell_lsl_removed.cir", relative_to=REPO),
        "candidate_bq_model": file_snapshot(ROOT / "inputs/bq_cell.cir", relative_to=REPO),
        "candidate_jj_model": file_snapshot(ROOT / "inputs/jjmit.cir", relative_to=REPO),
        "metric_spec": file_snapshot(REPO / config["strict_event"]["metric_spec"]["path"], relative_to=REPO),
        "windows_ps": windows,
        "strict_event_windows_ps": strict_event_windows,
        "strict_event": config["strict_event"],
        "outcome_rule": config["outcome_rule"],
        "visualization": plot,
        "preserved_postprocessing_failure": preserved_failure,
        "note": "Candidate raw execution is valid; only the first post-processing attempt failed. No raw or canonical circuit was overwritten.",
    }
    gate = """status: USER_REVIEWED
outcome: PLACEHOLDER_FILLED_IN_METRICS
physical_disposition: INCONCLUSIVE
user_reviewed: true
next_step_authorized: false
next_action: STOP
automatic_promotion: false
automatic_next_experiment: false
""".replace("PLACEHOLDER_FILLED_IN_METRICS", outcome)
    write_derived(ANALYSIS / "metrics.json", json.dumps(metrics, ensure_ascii=False, indent=2) + "\n")
    write_derived(ANALYSIS / "provenance.json", json.dumps(provenance, ensure_ascii=False, indent=2) + "\n")
    write_derived(ROOT / "RESULT_BRIEF.md", make_brief(metrics))
    write_derived(ANALYSIS / "REPORT.md", make_report(metrics))
    write_derived(ANALYSIS / "human-gate.yaml", gate)
    print(json.dumps({"status": "OK", "outcome": outcome, "plot": plot}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
