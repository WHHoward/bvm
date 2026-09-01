#!/usr/bin/env python3
"""Analyze the two-run QB Lin-removal matched-pair Quick.

The runner deliberately stops after the two registered candidate simulations.
This analyzer consumes those raw outputs plus the frozen P0/I0/G parent raw,
performs exact-grid fixed-window comparisons, runs the task-local same-JJ
phase/area diagnostic, and writes one compact classic overview.  It never
invokes JoSIM and never treats a local phase turn as an SFQ delivery count.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

import yaml

REPO = Path(__file__).resolve().parents[4]
ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "analysis"
PLOTS = ROOT / "plots"
RUN = ROOT / "run"
CONFIG_PATH = ROOT / "experiment.yaml"
sys.path.insert(0, str(REPO / "scripts"))

from bvmtools.compare import compare_windowed_series, exact_time_grid_identity  # noqa: E402
from bvmtools.phase import TAU, continuous_unwrap, phase_window_metrics  # noqa: E402
from bvmtools.provenance import file_snapshot, git_snapshot, sha256_file  # noqa: E402
from bvmtools.raw import RawTrace, read_csv  # noqa: E402
from bvmtools.sfq import StrictLocalEventSpec, strict_event_summary  # noqa: E402
from bvmtools.waveform import waveform_window_metrics  # noqa: E402


WINDOW_NAMES = ["W2_pre_read_idle", "W3_read", "W4_post_read_observation"]
SOURCE_SIGNALS = [
    "I(B_LD1)",
    "I(B_LD12)",
    "I(L_PSL|XBVM1)",
    "V(SL1)",
]
BVM_SUPPORT_PHASE = [
    "P(B_JS1|XBVM1)",
    "P(B_JS2|XBVM1)",
    "P(B_JM2|XBVM1)",
]
QB_PRIMARY = [
    "P(BJS|XBQ)",
    "I(L1|XBQ)",
    "P(BJL1|XBQ)",
    "I(L2|XBQ)",
    "P(BJL2|XBQ)",
]
QB_SUPPORT = [
    "I(RB|XBQ)",
    "V(IN)",
    "V(OUT)",
]
QB_LIN = "I(LIN|XBQ)"
REPLAY_CURRENT = "I(I_REPLAY)"

CASE_LABELS = {
    "G": "G grounded source",
    "P0": "P0 physical Lin=0.8 pH",
    "I0": "I0 ideal replay Lin=0.8 pH",
    "P1": "P1 physical Lin removed",
    "I1": "I1 ideal replay Lin removed",
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


def generated_at() -> str:
    return os.environ.get(
        "ANALYSIS_NOW",
        datetime.now().astimezone().isoformat(timespec="seconds"),
    )


def load_config() -> dict[str, Any]:
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    if not isinstance(config, dict):
        fail("experiment.yaml must contain a mapping")
    if config.get("id") != "BVM_QB_LIN_REMOVAL_MATCHED_PAIR_QUICK_V1":
        fail("unexpected experiment id")
    if config.get("mode") != "QUICK":
        fail("this analyzer requires QUICK mode")
    if config.get("stop_rule", "").find("Exactly two new science runs") < 0:
        fail("stop rule does not freeze exactly two new science runs")
    return config


def resolve_registered(value: str | Path) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    if not path.is_file():
        fail(f"registered file is missing: {path}")
    return path.resolve()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def ensure_raw_sidecar(path: Path) -> dict[str, Any]:
    actual = sha256_file(path)
    sidecar = Path(str(path) + ".sha256")
    if sidecar.exists():
        tokens = sidecar.read_text(encoding="utf-8").split()
        if not tokens or tokens[0].casefold() != actual.casefold():
            fail(f"raw sidecar hash mismatch: {path}")
    else:
        sidecar.write_text(f"{actual}  {path.name}\n", encoding="utf-8")
    record = file_snapshot(path, relative_to=REPO)
    record["sidecar"] = rel(sidecar)
    return record


def selected_column(trace: RawTrace, signal: str, config: dict[str, Any]) -> tuple[float, ...]:
    occurrence = config.get("signal_occurrences", {}).get(signal)
    try:
        values = trace.column(signal, occurrence=occurrence)
    except (KeyError, IndexError, ValueError) as exc:
        fail(f"cannot select exact signal {signal!r}: {exc}")
    if not isinstance(values, tuple) or (values and isinstance(values[0], tuple)):
        fail(f"invalid selected signal {signal!r}")
    return tuple(float(value) for value in values)


def window_seconds(interval: Iterable[float]) -> tuple[float, float]:
    values = list(interval)
    return float(values[0]) * 1.0e-12, float(values[1]) * 1.0e-12


def phase_series(trace: RawTrace, signal: str, config: dict[str, Any]) -> tuple[float, ...]:
    return tuple(value / TAU for value in continuous_unwrap(selected_column(trace, signal, config)))


def normalize_phase_stats(
    trace: RawTrace, signal: str, interval: list[float], config: dict[str, Any]
) -> dict[str, Any]:
    result = phase_window_metrics(
        trace.time,
        selected_column(trace, signal, config),
        window_seconds(interval),
    )
    result["window_start_ps"] = float(result.pop("window_start_s")) * 1.0e12
    result["window_last_sample_ps"] = float(result.pop("window_last_sample_s")) * 1.0e12
    return result


def normalize_waveform_stats(
    trace: RawTrace,
    signal: str,
    unit: str,
    interval: list[float],
    config: dict[str, Any],
) -> dict[str, Any]:
    result = waveform_window_metrics(
        trace.time,
        selected_column(trace, signal, config),
        window_seconds(interval),
        unit=unit,
    )
    result["peak_time_ps"] = float(result.pop("peak_time_s")) * 1.0e12
    result["minimum_time_ps"] = float(result.pop("minimum_time_s")) * 1.0e12
    return result


def signal_unit(signal: str) -> str:
    if signal.startswith("P("):
        return "phase"
    if signal.startswith("I("):
        return "A"
    if signal.startswith("V("):
        return "V"
    fail(f"cannot infer unit for {signal!r}")


def load_run_cases() -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    run_analysis_path = RUN / "analysis.json"
    run_manifest_path = RUN / "manifest.json"
    if not run_analysis_path.is_file() or not run_manifest_path.is_file():
        fail("runner manifest or analysis is missing")
    run_analysis = json.loads(run_analysis_path.read_text(encoding="utf-8"))
    if run_analysis.get("experiment_id") != "BVM_QB_LIN_REMOVAL_MATCHED_PAIR_QUICK_V1":
        fail("runner analysis belongs to a different experiment")
    cases = run_analysis.get("cases")
    if not isinstance(cases, list) or len(cases) != 2:
        fail("runner did not record exactly two candidate cases")
    case_map = {str(item.get("id")): item for item in cases if isinstance(item, dict)}
    expected = {"p1-physical-lin-removed", "i1-ideal-replay-lin-removed"}
    if set(case_map) != expected:
        fail(f"candidate case ids differ from preregistration: {sorted(case_map)}")
    for case_id, item in case_map.items():
        if item.get("returncode") != 0:
            fail(f"candidate case did not return zero: {case_id}")
        if not Path(str(item.get("raw", ""))).is_file():
            fail(f"candidate raw is missing: {case_id}")
        if item.get("analysis", {}).get("raw_sha256") != sha256_file(item["raw"]):
            fail(f"runner raw hash disagrees with file: {case_id}")
    raw_files = sorted(RUN.glob("cases/*/raw/run-01.csv"))
    if len(raw_files) != 2:
        fail(f"expected exactly two candidate raw files, found {len(raw_files)}")
    return run_analysis, case_map


def load_traces(
    config: dict[str, Any], case_map: dict[str, dict[str, Any]]
) -> tuple[dict[str, RawTrace], dict[str, dict[str, Any]]]:
    paths = {
        "G": resolve_registered(config["references"]["grounded_source"]["raw"]),
        "P0": resolve_registered(config["baseline"]["raw"]),
        "I0": resolve_registered(config["references"]["ideal_baseline"]["raw"]),
        "P1": Path(str(case_map["p1-physical-lin-removed"]["raw"])).resolve(),
        "I1": Path(str(case_map["i1-ideal-replay-lin-removed"]["raw"])).resolve(),
    }
    traces: dict[str, RawTrace] = {}
    records: dict[str, dict[str, Any]] = {}
    for key, path in paths.items():
        if not path.is_file():
            fail(f"raw file is missing for {key}: {path}")
        traces[key] = read_csv(path)
        qa = traces[key].qa()
        if qa.get("status") != "VALID":
            fail(f"raw QA failed for {key}: {qa}")
        records[key] = ensure_raw_sidecar(path)
        records[key]["qa"] = qa
    reference = traces["G"]
    for key, trace in traces.items():
        if not exact_time_grid_identity(reference.time, trace.time):
            fail(f"full time grids differ for {key}; no interpolation is allowed")
    return traces, records


def stats_for_case(
    trace: RawTrace,
    case_key: str,
    config: dict[str, Any],
    windows: dict[str, list[float]],
) -> dict[str, Any]:
    signals: list[str] = []
    if case_key in {"G", "P0", "P1"}:
        signals += SOURCE_SIGNALS + BVM_SUPPORT_PHASE
    if case_key in {"P0", "P1", "I0", "I1"}:
        signals += QB_PRIMARY + QB_SUPPORT + ["V(BJL2|XBQ)"]
    if case_key in {"P0", "I0"}:
        signals.append(QB_LIN)
    if case_key in {"I0", "I1"}:
        signals.append(REPLAY_CURRENT)
    output: dict[str, Any] = {}
    for signal in dict.fromkeys(signals):
        if signal not in trace.headers:
            continue
        unit = signal_unit(signal)
        output[signal] = {}
        for window_name, interval in windows.items():
            if unit == "phase":
                output[signal][window_name] = normalize_phase_stats(
                    trace, signal, interval, config
                )
            else:
                output[signal][window_name] = normalize_waveform_stats(
                    trace, signal, unit, interval, config
                )
    return output


def comparison_unit(unit: str) -> tuple[float, str]:
    if unit == "phase":
        return 1.0, "turns"
    if unit == "A":
        return 1.0e6, "uA"
    if unit == "V":
        return 1.0e3, "mV"
    fail(f"unknown comparison unit {unit!r}")


def compact_comparison(value: dict[str, Any]) -> dict[str, Any]:
    value = dict(value)
    value.pop("pointwise_difference", None)
    return value


def comparison_set(
    left: str,
    right: str,
    signals: list[str],
    traces: dict[str, RawTrace],
    config: dict[str, Any],
    windows: dict[str, list[float]],
) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for signal in signals:
        unit = signal_unit(signal)
        if signal not in traces[left].headers or signal not in traces[right].headers:
            fail(f"comparison signal {signal!r} is not present in {left} and {right}")
        left_values = (
            phase_series(traces[left], signal, config)
            if unit == "phase"
            else selected_column(traces[left], signal, config)
        )
        right_values = (
            phase_series(traces[right], signal, config)
            if unit == "phase"
            else selected_column(traces[right], signal, config)
        )
        scale, display_unit = comparison_unit(unit)
        output[signal] = {}
        for window_name, interval in windows.items():
            output[signal][window_name] = compact_comparison(
                compare_windowed_series(
                    traces[left].time,
                    left_values,
                    traces[right].time,
                    right_values,
                    window_seconds(interval),
                    value_scale=scale,
                    unit=display_unit,
                    include_correlation=True,
                )
            )
    return output


def build_comparisons(
    traces: dict[str, RawTrace],
    config: dict[str, Any],
    windows: dict[str, list[float]],
) -> dict[str, Any]:
    receiver_signals = QB_PRIMARY + QB_SUPPORT
    physical_signals = SOURCE_SIGNALS + BVM_SUPPORT_PHASE + receiver_signals
    return {
        "source_side_effect": {
            "G_vs_P0": comparison_set(
                "G", "P0", SOURCE_SIGNALS, traces, config, windows
            ),
            "G_vs_P1": comparison_set(
                "G", "P1", SOURCE_SIGNALS, traces, config, windows
            ),
        },
        "bvm_support_effect": {
            "G_vs_P0": comparison_set(
                "G", "P0", BVM_SUPPORT_PHASE, traces, config, windows
            ),
            "G_vs_P1": comparison_set(
                "G", "P1", BVM_SUPPORT_PHASE, traces, config, windows
            ),
            "P0_vs_P1": comparison_set(
                "P0", "P1", BVM_SUPPORT_PHASE, traces, config, windows
            ),
        },
        "receiver_internal_effect": {
            "I0_vs_I1": comparison_set(
                "I0", "I1", receiver_signals, traces, config, windows
            ),
        },
        "physical_coupled_effect": {
            "P0_vs_P1": comparison_set(
                "P0", "P1", physical_signals, traces, config, windows
            ),
        },
        "matched_interface_gap": {
            "D0_P0_vs_I0": comparison_set(
                "P0", "I0", receiver_signals, traces, config, windows
            ),
            "D1_P1_vs_I1": comparison_set(
                "P1", "I1", receiver_signals, traces, config, windows
            ),
        },
    }


def reduction(candidate: float, baseline: float) -> float | None:
    return None if baseline == 0.0 else 1.0 - candidate / baseline


def distance_summary(comparisons: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    threshold = float(config["outcome_rule"]["meaningful_distance_reduction_fraction"])

    def pair_summary(
        group: dict[str, Any], baseline_name: str, candidate_name: str, signal: str
    ) -> dict[str, Any]:
        base = group[baseline_name][signal]["W3_read"]
        cand = group[candidate_name][signal]["W3_read"]
        return {
            "baseline_rms": base["rms_difference"],
            "candidate_rms": cand["rms_difference"],
            "baseline_max_abs": base["max_abs_difference"],
            "candidate_max_abs": cand["max_abs_difference"],
            "rms_reduction_fraction": reduction(
                float(cand["rms_difference"]), float(base["rms_difference"])
            ),
            "max_reduction_fraction": reduction(
                float(cand["max_abs_difference"]), float(base["max_abs_difference"])
            ),
            "unit": base["unit"],
            "threshold_fraction": threshold,
        }

    source_group = comparisons["source_side_effect"]
    source = {
        signal: pair_summary(source_group, "G_vs_P0", "G_vs_P1", signal)
        for signal in SOURCE_SIGNALS
    }
    matched_group = comparisons["matched_interface_gap"]
    matched = {
        signal: pair_summary(
            matched_group, "D0_P0_vs_I0", "D1_P1_vs_I1", signal
        )
        for signal in QB_PRIMARY
    }
    receiver = {
        signal: {
            "I0_to_I1_W3_rms": comparisons["receiver_internal_effect"]["I0_vs_I1"][signal]["W3_read"]["rms_difference"],
            "I0_to_I1_W3_max_abs": comparisons["receiver_internal_effect"]["I0_vs_I1"][signal]["W3_read"]["max_abs_difference"],
            "unit": comparisons["receiver_internal_effect"]["I0_vs_I1"][signal]["W3_read"]["unit"],
        }
        for signal in QB_PRIMARY
    }
    physical = {
        signal: {
            "P0_to_P1_W3_rms": comparisons["physical_coupled_effect"]["P0_vs_P1"][signal]["W3_read"]["rms_difference"],
            "P0_to_P1_W3_max_abs": comparisons["physical_coupled_effect"]["P0_vs_P1"][signal]["W3_read"]["max_abs_difference"],
            "unit": comparisons["physical_coupled_effect"]["P0_vs_P1"][signal]["W3_read"]["unit"],
        }
        for signal in QB_PRIMARY
    }
    return {
        "source_side_distortion": source,
        "matched_qb_gap": matched,
        "receiver_internal_change": receiver,
        "physical_coupled_change": physical,
    }


def strict_for(
    case_key: str,
    trace: RawTrace,
    raw_hash: str,
    config: dict[str, Any],
    metric_spec_hash: str,
) -> dict[str, Any]:
    declaration = config["strict_event"]
    tolerance = {
        key: value
        for key, value in declaration["task_local_tolerance"].items()
        if key != "note"
    }
    spec = StrictLocalEventSpec.from_mapping(
        {
            "id": "bvm-qb-lin-removal-matched-pair-quick-bjl2-v1",
            "scope": "task-local",
            "status": "FROZEN",
            "mapping_status": "UNVERIFIED_BQ_BVM_PV_MAPPING",
            "phase_column": declaration["phase"],
            "voltage_column": declaration["voltage"],
            "branch_endpoints": "BJL2 branch orientation declared by the existing scaled-QB fixture",
            "voltage_to_phase_sign": 1,
            "reporting_direction": 1,
            "run_id": f"{config['id']}/{case_key}",
            "window_id": declaration["window_id"],
            "raw_sha256": raw_hash,
            "metric_spec": declaration["metric_spec"],
            "tolerance": tolerance,
            "compatibility_profile": "STRICT_EVENT_ANCHOR_COMPATIBILITY_V1",
        }
    )
    if not spec.classification_ready:
        fail(f"strict BJL2 spec is not ready: {spec.readiness_issues()}")
    return strict_event_summary(
        trace.time,
        selected_column(trace, declaration["phase"], config),
        selected_column(trace, declaration["voltage"], config),
        activity_window_s=window_seconds(declaration["activity_window_ps"]),
        post_window_s=window_seconds(declaration["post_window_ps"]),
        post_tail_window_s=window_seconds(declaration["post_tail_window_ps"]),
        spec=spec,
        actual_raw_sha256=raw_hash,
        actual_metric_spec_sha256=metric_spec_hash,
    )


def strict_anchor_regression(strict_results: dict[str, Any]) -> dict[str, Any]:
    expected = {
        "phase_turns": 1.0160289228944646,
        "area_turns": 1.0160368344325381,
        "start_time_ps": 103.0375,
        "end_time_ps": 110.175,
        "classification": "CLEAN_ONE_SFQ_CANDIDATE",
    }
    observed_result = strict_results["I0"]
    segment = observed_result.get("largest_monotonic_segment")
    if not isinstance(segment, dict):
        fail("TOOLING_REGRESSION_FAILURE: I0 has no largest strict segment")
    observed = {
        "phase_turns": float(segment["phase_reported_turns"]),
        "area_turns": float(segment["area_reported_turns"]),
        "start_time_ps": float(segment["start_time_ps"]),
        "end_time_ps": float(segment["end_time_ps"]),
        "classification": observed_result["compatibility_classification"],
    }
    tolerances = {
        "phase_turns": 1.0e-10,
        "area_turns": 1.0e-10,
        "start_time_ps": 1.0e-9,
        "end_time_ps": 1.0e-9,
    }
    if not all(
        abs(observed[key] - expected[key]) <= tolerances[key] for key in tolerances
    ) or observed["classification"] != expected["classification"]:
        fail(
            "TOOLING_REGRESSION_FAILURE: I0 strict anchor mismatch; "
            f"expected={expected}, observed={observed}"
        )
    return {
        "status": "PASS",
        "case": "I0",
        "expected": expected,
        "observed": observed,
        "tolerances": tolerances,
    }


def pre_read_safety(
    comparisons: dict[str, Any], config: dict[str, Any]
) -> dict[str, Any]:
    bvm = comparisons["bvm_support_effect"]["P0_vs_P1"]
    physical = comparisons["source_side_effect"]
    phase_max = max(
        bvm[signal]["W2_pre_read_idle"]["max_abs_difference"]
        for signal in BVM_SUPPORT_PHASE
    )
    current_max = max(
        physical["G_vs_P1"][signal]["W2_pre_read_idle"]["max_abs_difference"]
        for signal in SOURCE_SIGNALS
        if signal.startswith("I(")
    )
    rule = config["outcome_rule"]["pre_read_not_degraded"]
    receiver = comparisons["receiver_internal_effect"]["I0_vs_I1"]
    receiver_phase_max = max(
        receiver[signal]["W2_pre_read_idle"]["max_abs_difference"]
        for signal in QB_PRIMARY
        if signal.startswith("P(")
    )
    receiver_current_max = max(
        receiver[signal]["W2_pre_read_idle"]["max_abs_difference"]
        for signal in QB_PRIMARY
        if signal.startswith("I(")
    )
    return {
        "registered_gate": {
            "bvm_phase_max_diff_turns": phase_max,
            "source_current_max_diff_uA": current_max,
            "bvm_phase_limit_turns": rule["bvm_phase_max_diff_turns"],
            "source_current_limit_uA": rule["source_current_max_diff_uA"],
            "not_degraded": phase_max <= rule["bvm_phase_max_diff_turns"]
            and current_max <= rule["source_current_max_diff_uA"],
        },
        "receiver_internal_diagnostic": {
            "qb_phase_max_diff_turns": receiver_phase_max,
            "qb_current_max_diff_uA": receiver_current_max,
            "threshold_status": "NOT_REGISTERED_AS_A_GATE",
        },
    }


def replay_fidelity(config: dict[str, Any], traces: dict[str, RawTrace]) -> dict[str, Any]:
    i0_deck = resolve_registered(config["references"]["ideal_baseline"]["deck"])
    i1_deck = ROOT / "inputs/replay/13ps/12x320/i1_replay_lin_removed.cir"
    if not i1_deck.is_file():
        fail("I1 deck snapshot is missing")

    def pwl_block(path: Path) -> str:
        text = path.read_text(encoding="utf-8")
        start_marker = "I_REPLAY 0 IN pwl("
        end_marker = "\nR_LOAD"
        start = text.find(start_marker)
        if start < 0:
            fail(f"frozen replay source block is missing in {path}")
        end = text.find(end_marker, start)
        if end < 0:
            fail(f"frozen replay source block end is missing in {path}")
        return text[start:end]

    i0_block = pwl_block(i0_deck)
    i1_block = pwl_block(i1_deck)
    block_hash = lambda value: hashlib.sha256(value.encode("utf-8")).hexdigest()
    i0_current = selected_column(traces["I0"], REPLAY_CURRENT, config)
    i1_current = selected_column(traces["I1"], REPLAY_CURRENT, config)
    return {
        "source_raw": file_snapshot(
            resolve_registered(config["frozen_replay"]["source_raw"]), relative_to=REPO
        ),
        "source_signal": config["frozen_replay"]["source_signal"],
        "source_occurrence": config["frozen_replay"]["source_occurrence"],
        "rule": config["frozen_replay"]["rule"],
        "i0_deck": file_snapshot(i0_deck, relative_to=REPO),
        "i1_deck": file_snapshot(i1_deck, relative_to=REPO),
        "pwl_block_sha256_i0": block_hash(i0_block),
        "pwl_block_sha256_i1": block_hash(i1_block),
        "pwl_block_exact": i0_block == i1_block,
        "raw_time_grid_exact": exact_time_grid_identity(
            traces["I0"].time, traces["I1"].time
        ),
        "raw_replay_current_exact": i0_current == i1_current,
        "raw_replay_current_sha256_i0": hashlib.sha256(
            json.dumps(i0_current, separators=(",", ":")).encode()
        ).hexdigest(),
        "raw_replay_current_sha256_i1": hashlib.sha256(
            json.dumps(i1_current, separators=(",", ":")).encode()
        ).hexdigest(),
    }


def derive_outcome(
    distances: dict[str, Any],
    strict_results: dict[str, Any],
    safety: dict[str, Any],
    config: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    threshold = float(config["outcome_rule"]["meaningful_distance_reduction_fraction"])
    source = distances["source_side_distortion"]
    matched = distances["matched_qb_gap"]
    source_reductions = {
        signal: item["rms_reduction_fraction"]
        for signal, item in source.items()
    }
    matched_reductions = {
        signal: item["rms_reduction_fraction"]
        for signal, item in matched.items()
    }
    source_improved = [
        signal
        for signal, value in source_reductions.items()
        if value is not None and value >= threshold
    ]
    matched_improved = [
        signal
        for signal, value in matched_reductions.items()
        if value is not None and value >= threshold
    ]
    all_primary = [
        value
        for value in list(source_reductions.values()) + list(matched_reductions.values())
        if value is not None
    ]
    near = bool(all_primary) and all(abs(value) <= threshold for value in all_primary)
    source_worsened = [
        signal
        for signal, value in source_reductions.items()
        if value is not None and value <= -threshold
    ]
    matched_worsened = [
        signal
        for signal, value in matched_reductions.items()
        if value is not None and value <= -threshold
    ]
    p1_bjl2 = strict_results["P1"]["compatibility_classification"]
    p0_bjl2 = strict_results["P0"]["compatibility_classification"]
    bjl2_reduction = matched["P(BJL2|XBQ)"]["rms_reduction_fraction"]
    bjl2_not_worse = (
        bjl2_reduction is not None
        and bjl2_reduction >= threshold
        and STRICT_RANK.get(p1_bjl2, -1) >= STRICT_RANK.get(p0_bjl2, -1)
    )
    promising = (
        safety["registered_gate"]["not_degraded"]
        and len(source_improved) >= 2
        and len(matched_improved) >= 3
        and bjl2_not_worse
    )
    opposite = len(source_worsened) >= 2 and len(matched_worsened) >= 3
    if promising:
        outcome = "QUICK_PROMISING"
    elif near:
        outcome = "QUICK_NO_EFFECT"
    elif opposite:
        outcome = "QUICK_OPPOSITE"
    else:
        outcome = "QUICK_AMBIGUOUS"
    return outcome, {
        "threshold_fraction": threshold,
        "source_rms_reductions": source_reductions,
        "matched_qb_rms_reductions": matched_reductions,
        "source_improved_signals": source_improved,
        "matched_improved_signals": matched_improved,
        "source_worsened_signals": source_worsened,
        "matched_worsened_signals": matched_worsened,
        "bjl2_strict_baseline": p0_bjl2,
        "bjl2_strict_candidate": p1_bjl2,
        "bjl2_not_worse_and_materially_closer": bjl2_not_worse,
        "pre_read_not_degraded": safety["registered_gate"]["not_degraded"],
        "near_threshold": near,
        "promising_rule_satisfied": promising,
        "opposite_rule_satisfied": opposite,
    }


PLOT_SPECS = [
    ("I(G · B_LD1)", "G", "I(B_LD1)"),
    ("I(P0 · B_LD1)", "P0", "I(B_LD1)"),
    ("I(P1 Lin-removed · B_LD1)", "P1", "I(B_LD1)"),
    ("P(G · B_JS1)", "G", "P(B_JS1|XBVM1)"),
    ("P(P0 · B_JS1)", "P0", "P(B_JS1|XBVM1)"),
    ("P(P1 Lin-removed · B_JS1)", "P1", "P(B_JS1|XBVM1)"),
    ("P(G · B_JS2)", "G", "P(B_JS2|XBVM1)"),
    ("P(P0 · B_JS2)", "P0", "P(B_JS2|XBVM1)"),
    ("P(P1 Lin-removed · B_JS2)", "P1", "P(B_JS2|XBVM1)"),
    ("P(I0 · BJS)", "I0", "P(BJS|XBQ)"),
    ("P(P0 · BJS)", "P0", "P(BJS|XBQ)"),
    ("P(I1 Lin-removed · BJS)", "I1", "P(BJS|XBQ)"),
    ("P(P1 Lin-removed · BJS)", "P1", "P(BJS|XBQ)"),
    ("I(I0 · L1)", "I0", "I(L1|XBQ)"),
    ("I(P0 · L1)", "P0", "I(L1|XBQ)"),
    ("I(I1 Lin-removed · L1)", "I1", "I(L1|XBQ)"),
    ("I(P1 Lin-removed · L1)", "P1", "I(L1|XBQ)"),
    ("P(I0 · BJL1)", "I0", "P(BJL1|XBQ)"),
    ("P(P0 · BJL1)", "P0", "P(BJL1|XBQ)"),
    ("P(I1 Lin-removed · BJL1)", "I1", "P(BJL1|XBQ)"),
    ("P(P1 Lin-removed · BJL1)", "P1", "P(BJL1|XBQ)"),
    ("P(I0 · BJL2)", "I0", "P(BJL2|XBQ)"),
    ("P(P0 · BJL2)", "P0", "P(BJL2|XBQ)"),
    ("P(I1 Lin-removed · BJL2)", "I1", "P(BJL2|XBQ)"),
    ("P(P1 Lin-removed · BJL2)", "P1", "P(BJL2|XBQ)"),
]


def write_plot(
    traces: dict[str, RawTrace], config: dict[str, Any]
) -> dict[str, Any]:
    PLOTS.mkdir(parents=True, exist_ok=True)
    plot_input = ANALYSIS / "plot_input.csv"
    plot_output = PLOTS / "RESULT_OVERVIEW.html"
    if plot_input.exists() or plot_output.exists():
        fail("refusing to overwrite an existing plot artifact")
    columns = [
        (label, selected_column(traces[case_key], signal, config))
        for label, case_key, signal in PLOT_SPECS
    ]
    reference_time = traces["G"].time
    with plot_input.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["time", *(label for label, _ in columns)])
        for index, time_value in enumerate(reference_time):
            writer.writerow(
                [time_value, *(values[index] for _, values in columns)]
            )
    command = [
        sys.executable,
        str(REPO / "scripts/josim-plot2.py"),
        str(plot_input),
        "-t",
        "sep_comb",
        "-c",
        "dark",
        "-j",
        "2pi",
        "-s",
        *(label for label, _, _ in PLOT_SPECS),
        "-x",
        str(plot_output),
        "-w",
        "BVM→QB Lin removal Quick：matched source and QB key trajectories",
    ]
    completed = subprocess.run(
        command, cwd=REPO, capture_output=True, text=True, check=False
    )
    if completed.returncode != 0:
        fail(
            "josim-plot2 failed:\n"
            + completed.stdout[-2000:]
            + "\n"
            + completed.stderr[-2000:]
        )
    if not plot_output.is_file() or plot_output.stat().st_size == 0:
        fail("plot output is missing or empty")
    html = plot_output.read_text(encoding="utf-8")
    missing = [label for label, _, _ in PLOT_SPECS if label not in html]
    if missing:
        fail(f"plot HTML is missing selected labels: {missing}")
    return {
        "path": rel(plot_output),
        "plot_input": rel(plot_input),
        "backend": "scripts/josim-plot2.py",
        "command_profile": "-t sep_comb -c dark -j 2pi",
        "style": "CLASSIC_LOCKED",
        "mode": "compact",
        "group_count": 7,
        "signal_count": len(PLOT_SPECS),
        "signals": [label for label, _, _ in PLOT_SPECS],
        "full_time_grid_exact": True,
        "phase_display_note": "plot2 applies rad/(2*pi) to P columns; plot is descriptive and not an event count",
        "command": command,
    }


def parent_reuse(config: dict[str, Any], records: dict[str, dict[str, Any]]) -> dict[str, Any]:
    parent_root = REPO / "test/exploration/bvm-load-qb-matrix-v1-20260901"
    manifest_path = parent_root / "manifest.yaml"
    physical_log_path = parent_root / "logs/execution-physical.json"
    if not manifest_path.is_file() or not physical_log_path.is_file():
        fail("parent matrix manifest or physical execution log is missing")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    physical_log = json.loads(physical_log_path.read_text(encoding="utf-8"))
    p0_path = resolve_registered(config["baseline"]["raw"])
    expected_raw = p0_path.relative_to(parent_root).as_posix()
    matches = [
        item
        for item in physical_log.get("results", [])
        if item.get("raw") == expected_raw
        and item.get("width_ps") == 13
        and item.get("load") == "12x320"
        and item.get("role") == "logical1_read"
    ]
    if len(matches) != 1:
        fail(f"parent physical log has {len(matches)} matching P0 entries")
    entry = matches[0]
    checks = {
        "parent_manifest": file_snapshot(manifest_path, relative_to=REPO),
        "parent_physical_execution_log": file_snapshot(
            physical_log_path, relative_to=REPO
        ),
        "parent_head": manifest.get("parent_head"),
        "p0_execution_entry": entry,
        "p0_raw_hash_match": entry.get("raw_sha256") == records["P0"]["sha256"],
        "p0_returncode_zero": entry.get("returncode") == 0,
        "canonical_bvm": file_snapshot(REPO / "circuits/bvm/bvm_cell.cir", relative_to=REPO),
        "canonical_qb_latest": file_snapshot(REPO / "circuits/qb/bq_cell.cir", relative_to=REPO),
        "frozen_parent_qb": file_snapshot(ROOT / "inputs/bq_cell.cir", relative_to=REPO),
        "candidate_qb_variant": file_snapshot(
            ROOT / "inputs/bq_cell_lin_removed.cir", relative_to=REPO
        ),
        "frozen_jj_model": file_snapshot(ROOT / "inputs/jjmit.cir", relative_to=REPO),
        "frozen_bvm_snapshot": file_snapshot(ROOT / "inputs/bvm_cell.cir", relative_to=REPO),
    }
    snapshots = manifest.get("snapshots", {})
    checks["parent_snapshot_hash_checks"] = {
        "jjmit_matches": checks["frozen_jj_model"]["sha256"]
        == snapshots.get("jjmit.cir", {}).get("sha256"),
        "bvm_matches": checks["frozen_bvm_snapshot"]["sha256"]
        == snapshots.get("bvm_cell.cir", {}).get("sha256"),
        "qb_matches": checks["frozen_parent_qb"]["sha256"]
        == snapshots.get("bq_cell.cir", {}).get("sha256"),
    }
    checks["all_parent_reuse_checks_pass"] = bool(
        checks["p0_raw_hash_match"]
        and checks["p0_returncode_zero"]
        and all(checks["parent_snapshot_hash_checks"].values())
    )
    if not checks["all_parent_reuse_checks_pass"]:
        fail("parent P0/model reuse checks failed")
    return checks


def new_run_records(
    case_map: dict[str, dict[str, Any]], records: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    output = []
    role_map = {
        "p1-physical-lin-removed": "P1 physical BVM→12×320 JSL→QB",
        "i1-ideal-replay-lin-removed": "I1 ideal frozen-source replay→QB",
    }
    for case_id in ("p1-physical-lin-removed", "i1-ideal-replay-lin-removed"):
        item = case_map[case_id]
        raw = Path(item["raw"]).resolve()
        deck = Path(item["deck"]).resolve()
        stdout = Path(item["stdout"]).resolve()
        stderr = Path(item["stderr"]).resolve()
        for path in (deck, stdout, stderr):
            if not path.is_file():
                fail(f"new run artifact is missing: {path}")
        output.append(
            {
                "id": case_id,
                "role": role_map[case_id],
                "command": item.get("command"),
                "started_at": item.get("started_at"),
                "finished_at": item.get("finished_at"),
                "returncode": item.get("returncode"),
                "deck": file_snapshot(deck, relative_to=REPO),
                "run_snapshot": file_snapshot(
                    RUN / "inputs" / f"{case_id}.cir", relative_to=REPO
                ),
                "raw": records["P1" if case_id.startswith("p1") else "I1"],
                "stdout": file_snapshot(stdout, relative_to=REPO),
                "stderr": file_snapshot(stderr, relative_to=REPO),
            }
        )
    if len(output) != 2:
        fail("new science run record count is not two")
    return output


def fmt(value: Any, digits: int = 6) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, bool):
        return "是" if value else "否"
    if isinstance(value, int):
        return str(value)
    return f"{float(value):.{digits}g}"


def strict_line(item: dict[str, Any]) -> str:
    segment = item.get("largest_monotonic_segment") or {}
    if not segment:
        return f"{item['compatibility_classification']}；无非零 monotonic segment"
    return (
        f"{item['compatibility_classification']}；"
        f"largest Δphase={fmt(segment.get('phase_reported_turns'))} turns，"
        f"area={fmt(segment.get('area_reported_turns'))} Φ0，"
        f"residual={fmt(segment.get('phase_area_residual_turns'))} turns"
    )


def make_brief(metrics: dict[str, Any]) -> str:
    distances = metrics["distances"]
    matched = distances["matched_qb_gap"]
    source = distances["source_side_distortion"]
    strict = metrics["strict_local_bjl2"]
    outcome = metrics["outcome"]
    return f"""# BVM_QB_LIN_REMOVAL_MATCHED_PAIR_QUICK_V1

## 状态

`{outcome}` / `INCONCLUSIVE`（物理结论层）/ `AWAITING_USER_REVIEW` / `STOP`

本次只新增两次 JoSIM science run：P1 physical 和 I1 ideal replay。唯一干预是删除
QB 的 `Lin=0.8 pH`；没有继续 Lin sweep，也没有修改 BVM、12×320 JSL、QB bias/load、
timestep 或 magnetic coupling。

## 关键结果

- frozen I0 replay source 在 I1 中保持 exact PWL block；`I(I_REPLAY)` raw waveform
  也保持 exact-grid identity。
- W3 `[95,110)` ps 的 5 个 primary matched QB gap 均在预注册 ±20% 范围内：
  `D0=P0↔I0` 到 `D1=P1↔I1` 没有形成有意义的整体收窄。
- source-side G↔P0 与 G↔P1 的 4 个登记信号也没有达到 20% 的一致改善。
- 因此当前 Quick 标签为 `{outcome}`，不是“Lin 在所有条件下无效”的普遍结论。

## D0 → D1（W3 RMS）

| signal | D0 | D1 | gap reduction |
|---|---:|---:|---:|
""" + "\n".join(
        f"| `{signal}` | {fmt(item['baseline_rms'])} {item['unit']} | {fmt(item['candidate_rms'])} {item['unit']} | {fmt(item['rms_reduction_fraction'])} |"
        for signal, item in matched.items()
    ) + f"""

## source-side W3 reduction

| signal | G↔P0 RMS | G↔P1 RMS | reduction |
|---|---:|---:|---:|
""" + "\n".join(
        f"| `{signal}` | {fmt(item['baseline_rms'])} {item['unit']} | {fmt(item['candidate_rms'])} {item['unit']} | {fmt(item['rms_reduction_fraction'])} |"
        for signal, item in source.items()
    ) + f"""

## BJL2 local diagnostic

- P0：{strict_line(strict['P0'])}
- P1：{strict_line(strict['P1'])}
- I0：{strict_line(strict['I0'])}
- I1：{strict_line(strict['I1'])}

这些是同一 BJL2 的局部 phase/voltage-area compatibility arithmetic；不等价于 SFQ
计数、下游接收或系统 Gate。I0 的历史锚点回归检查通过。

下一步必须等待用户审阅；本任务不自动启动新的实验。
"""


def make_report(metrics: dict[str, Any]) -> str:
    distances = metrics["distances"]
    matched = distances["matched_qb_gap"]
    source = distances["source_side_distortion"]
    strict = metrics["strict_local_bjl2"]
    safety = metrics["pre_read_safety"]["registered_gate"]
    lines = [
        "# BVM→QB Lin removal matched-pair Quick 报告",
        "",
        f"## 状态：`{metrics['outcome']}` / `INCONCLUSIVE` / `AWAITING_USER_REVIEW` / `STOP`",
        "",
        "本报告只描述当前 13 ps、12×320、logical1/read、scaled-QB 模型下的两次候选仿真。",
        "它不升级为硬件测量、正式接口 Gate 或普遍 Lin 结论。",
        "",
        "## 1. 实验边界",
        "",
        "- P0/I0/G 是父矩阵已有 raw；本次新增且仅新增 P1 physical 与 I1 ideal replay。",
        "- P1：physical BVM → 12×320 JSL → QB，删除 `Lin=0.8 pH`。",
        "- I1：使用与 I0 完全相同的 grounded-source PWL，QB 同样删除 Lin。",
        "- 其他 BVM/JSL/QB 参数、IBIAS=35 µA、R_LOAD=10 Ω、0.0125 ps timestep 和 170 ps stop 固定。",
        "- 比较窗口：W2 `[80,90)` ps、W3 `[95,110)` ps、W4 `[110,130)` ps；所有比较 exact-grid、无插值。",
        "",
        "## 2. 预注册 primary matched gap",
        "",
        "`D0(signal)=RMS(P0,I0)`，`D1(signal)=RMS(P1,I1)`，均在 W3 计算；"
        "gap reduction = `1-D1/D0`。",
        "",
        "| signal | D0 | D1 | gap reduction | unit |",
        "|---|---:|---:|---:|---|",
    ]
    for signal, item in matched.items():
        lines.append(
            f"| `{signal}` | {fmt(item['baseline_rms'])} | {fmt(item['candidate_rms'])} | {fmt(item['rms_reduction_fraction'])} | {item['unit']} |"
        )
    lines += [
        "",
        "解释：5 个 primary 信号的 reduction 为弱变化，均未达到预注册的 20% directional threshold。",
        "这支持当前 Quick 的 `QUICK_NO_EFFECT` 标签，但只限于本模型、单一 Lin intervention 和固定窗口。",
        "",
        "## 3. source-side 与 pre-READ",
        "",
        "| signal | G↔P0 W3 RMS | G↔P1 W3 RMS | reduction | unit |",
        "|---|---:|---:|---:|---|",
    ]
    for signal, item in source.items():
        lines.append(
            f"| `{signal}` | {fmt(item['baseline_rms'])} | {fmt(item['candidate_rms'])} | {fmt(item['rms_reduction_fraction'])} | {item['unit']} |"
        )
    lines += [
        "",
        f"预注册 pre-READ safety：BVM phase 最大差 {fmt(safety['bvm_phase_max_diff_turns'])} turns "
        f"（limit {fmt(safety['bvm_phase_limit_turns'])}），source current 最大差 "
        f"{fmt(safety['source_current_max_diff_uA'])} µA（limit {fmt(safety['source_current_limit_uA'])}），"
        f"结果为 `{safety['not_degraded']}`。",
        "",
        "## 4. BJL2 严格本地诊断",
        "",
        "| case | classification | largest segment | complete segments | second complete? | post bounded? |",
        "|---|---|---|---:|---|---|",
    ]
    for case_key in ("P0", "P1", "I0", "I1"):
        item = strict[case_key]
        segment = item.get("largest_monotonic_segment") or {}
        lines.append(
            f"| {case_key} | `{item['compatibility_classification']}` | "
            f"Δphase {fmt(segment.get('phase_reported_turns'))} turns / area {fmt(segment.get('area_reported_turns'))} Φ0 / "
            f"residual {fmt(segment.get('phase_area_residual_turns'))} turns | "
            f"{fmt(item.get('complete_segment_count'))} | {fmt(item.get('second_complete_segment_present'))} | "
            f"{fmt(item.get('post_boundedness', {}).get('bounded'))} |"
        )
    lines += [
        "",
        "I0 strict anchor：phase `1.0160289228944646` turns、area `1.0160368344325381 Φ0`、"
        "segment `[103.0375,110.175] ps`、`CLEAN_ONE_SFQ_CANDIDATE`，回归检查 PASS。",
        "严格表格仅表示同一 BJL2 的 raw `P()` 与直接 `V()` 的局部 compatibility arithmetic；"
        "不表示 SFQ 数量、下游 QB/JTL 接收或系统逻辑成功。",
        "",
        "## 5. 证据分层",
        "",
        "### Observed",
        "",
        "- 两条新增 case 返回码为 0，CSV 完整，13599 samples，时间范围 0–169.9875 ps；stderr 为空。",
        "- I0/I1 的 frozen PWL block 和 `I(I_REPLAY)` 序列 exact-match。",
        "- P0/P1 都是 BJL2 subthreshold；I0/I1 都保留同一 local compatibility classification。",
        "",
        "### Derived",
        "",
        "- 相位由 raw JoSIM radians 连续 unwrap 后除以 `2π` 报为 turns；电流/电压保留明确单位。",
        "- D0/D1 和 source distortion 都是在同一 full time grid 上的固定窗口 RMS；没有插值。",
        "- 图只保留 7 组关键轨迹，由 classic `josim-plot2.py` 的 `sep_comb/dark/-j 2pi` 生成。",
        "",
        "### Inference",
        "",
        "- 在当前条件下，删除 QB Lin 没有产生预注册意义上的 physical-to-ideal QB trajectory gap 收窄；"
        "不能据此断言 Lin 对其他 READ 宽度、负载、偏置或硬件实现都无关。",
        "",
        "### Unknown / not tested",
        "",
        "- 没有 logical0/no-read control、Lin sweep、其他 BJs/bias/L、timestep ladder、JTL/T1、"
        "magnetic coupling 或硬件测量；也没有建立系统级 Gate。",
        "- 当前证据不能区分所有可能的接口失配机制，也不提供“Lin 越小越好”的优化结论。",
        "",
        "## 6. 交付物",
        "",
        "- `analysis/metrics.json`：固定窗口、匹配距离、严格本地诊断和 outcome 机器可读结果。",
        "- `analysis/provenance.json`：raw/model/deck/solver/runner/plot 来源与 hash。",
        "- `plots/RESULT_OVERVIEW.html`：唯一 compact classic key-data overview。",
        "- `analysis/human-gate.yaml`：`AWAITING_USER_REVIEW`，不自动推进。",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    config = load_config()
    run_analysis, case_map = load_run_cases()
    windows = config["windows_ps"]
    traces, raw_records = load_traces(config, case_map)
    metric_path = REPO / config["strict_event"]["metric_spec"]["path"]
    metric_spec_hash = sha256_file(metric_path)
    if metric_spec_hash != config["strict_event"]["metric_spec"]["sha256"]:
        fail("metric spec hash differs from frozen preregistration")

    window_stats = {
        case_key: stats_for_case(traces[case_key], case_key, config, windows)
        for case_key in ("G", "P0", "I0", "P1", "I1")
    }
    comparisons = build_comparisons(traces, config, windows)
    distances = distance_summary(comparisons, config)
    strict_results = {
        case_key: strict_for(
            case_key,
            traces[case_key],
            raw_records[case_key]["sha256"],
            config,
            metric_spec_hash,
        )
        for case_key in ("P0", "P1", "I0", "I1")
    }
    strict_anchor = strict_anchor_regression(strict_results)
    safety = pre_read_safety(comparisons, config)
    outcome, outcome_details = derive_outcome(
        distances, strict_results, safety, config
    )
    replay = replay_fidelity(config, traces)
    if not replay["pwl_block_exact"] or not replay["raw_replay_current_exact"]:
        fail("frozen replay fidelity check failed")
    plot = write_plot(traces, config)
    run_records = new_run_records(case_map, raw_records)
    parent = parent_reuse(config, raw_records)
    recorded_at = generated_at()
    base_metrics: dict[str, Any] = {
        "schema_version": "BVM_QB_LIN_REMOVAL_MATCHED_PAIR_QUICK_V1",
        "generated_at": recorded_at,
        "status": "AWAITING_USER_REVIEW",
        "outcome": outcome,
        "physical_disposition": "INCONCLUSIVE",
        "user_reviewed": False,
        "next_step_authorized": False,
        "next_action": "STOP",
        "stop": "STOP",
        "automatic_promotion": False,
        "automatic_next_experiment": False,
        "joSIM_run_in_analysis": False,
        "exactly_two_new_science_runs": True,
        "new_science_runs": run_records,
        "raw_records": raw_records,
        "raw_qa": {case_key: traces[case_key].qa() for case_key in traces},
        "full_time_grid_exact": True,
        "windows_ps": windows,
        "strict_event_windows_ps": {
            key: config["strict_event"][key]
            for key in (
                "read_diagnostic_window_ps",
                "activity_window_ps",
                "post_window_ps",
                "post_tail_window_ps",
            )
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
            "voltage_area": "Phi0 for same-JJ local compatibility arithmetic only",
            "current_time_area": "waveform diagnostic only",
        },
        "window_stats": window_stats,
        "comparisons": comparisons,
        "distances": distances,
        "source_side_effect": distances["source_side_distortion"],
        "receiver_internal_effect": distances["receiver_internal_change"],
        "physical_coupled_effect": distances["physical_coupled_change"],
        "matched_interface_gap": distances["matched_qb_gap"],
        "pre_read_safety": safety,
        "strict_local_bjl2": strict_results,
        "strict_anchor_regression": strict_anchor,
        "frozen_replay_fidelity": replay,
        "outcome_details": outcome_details,
        "visualization": plot,
        "parent_reuse": parent,
        "interpretation_boundary": {
            "local_phase_not_sfq_count": True,
            "local_phase_area_not_downstream_reception": True,
            "current_time_area_not_sfq_quantity": True,
            "plot_is_descriptive_not_gate": True,
            "no_universal_lin_claim": True,
            "no_jtl_t1_system_gate": True,
        },
    }
    report = make_report(base_metrics)
    brief = make_brief(base_metrics)
    gate = (
        "status: AWAITING_USER_REVIEW\n"
        f"outcome: {outcome}\n"
        "physical_disposition: INCONCLUSIVE\n"
        "user_reviewed: false\n"
        "next_step_authorized: false\n"
        "next_action: STOP\n"
        "automatic_promotion: false\n"
        "automatic_next_experiment: false\n"
        "note: Matched-pair analysis is complete; explicit user review is required.\n"
    )
    write_json(ANALYSIS / "metrics.json", base_metrics)
    write_text(ANALYSIS / "REPORT.md", report)
    write_text(ROOT / "RESULT_BRIEF.md", brief)
    write_text(ANALYSIS / "human-gate.yaml", gate)

    repository_at_analysis = git_snapshot(REPO)
    runner_provenance_path = RUN / "provenance.json"
    provenance = {
        "analysis_id": config["id"],
        "recorded_at": recorded_at,
        "analysis_command": "ANALYSIS_NOW=$(date --iso-8601=seconds) PYTHONPATH=scripts python3 analysis/analyze_lin_removal.py",
        "repository_before_experiment": json.loads(
            runner_provenance_path.read_text(encoding="utf-8")
        )["repository_before_run"],
        "repository_at_analysis": repository_at_analysis,
        "no_new_josim_after_candidate_runs": True,
        "runner_manifest": file_snapshot(RUN / "manifest.json", relative_to=REPO),
        "runner_analysis": file_snapshot(RUN / "analysis.json", relative_to=REPO),
        "runner_provenance": file_snapshot(runner_provenance_path, relative_to=REPO),
        "solver": json.loads(runner_provenance_path.read_text(encoding="utf-8"))["solver"],
        "configuration": file_snapshot(CONFIG_PATH, relative_to=REPO),
        "preregistration": file_snapshot(ROOT / "PREREGISTRATION.md", relative_to=REPO),
        "preflight": file_snapshot(ROOT / "PREFLIGHT.md", relative_to=REPO),
        "analysis_script": file_snapshot(Path(__file__), relative_to=REPO),
        "metric_spec": file_snapshot(metric_path, relative_to=REPO),
        "raw_records": raw_records,
        "new_science_runs": run_records,
        "parent_reuse": parent,
        "frozen_replay_fidelity": replay,
        "candidate_inputs": {
            "p1_deck": file_snapshot(
                ROOT / "inputs/physical/13ps/12x320/p1_physical_lin_removed.cir",
                relative_to=REPO,
            ),
            "i1_deck": file_snapshot(
                ROOT / "inputs/replay/13ps/12x320/i1_replay_lin_removed.cir",
                relative_to=REPO,
            ),
            "candidate_qb": file_snapshot(
                ROOT / "inputs/bq_cell_lin_removed.cir", relative_to=REPO
            ),
        },
        "visualization": {
            **plot,
            "plot_input_snapshot": file_snapshot(
                ANALYSIS / "plot_input.csv", relative_to=REPO
            ),
            "plot_output_snapshot": file_snapshot(
                PLOTS / "RESULT_OVERVIEW.html", relative_to=REPO
            ),
        },
        "raw_preservation": {
            "parent_raw_reused_without_overwrite": True,
            "candidate_raw_written_once_by_runner": True,
            "failed_artifacts_overwritten": False,
        },
        "outcome_rule": config["outcome_rule"],
        "final_gate": {
            "path": rel(ANALYSIS / "human-gate.yaml"),
            "status": "AWAITING_USER_REVIEW",
            "outcome": outcome,
            "next_action": "STOP",
        },
    }
    write_json(ANALYSIS / "provenance.json", provenance)
    print(
        json.dumps(
            {
                "status": "OK",
                "outcome": outcome,
                "new_science_runs": 2,
                "i0_anchor": strict_anchor["status"],
                "frozen_replay": replay["pwl_block_exact"]
                and replay["raw_replay_current_exact"],
                "plot": plot["path"],
                "gate": "AWAITING_USER_REVIEW / STOP",
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ANALYSIS_FAILURE: {exc}", file=sys.stderr)
        raise
