#!/usr/bin/env python3
"""Analyze the four delta4 replay runs without assigning SFQ event counts."""

from __future__ import annotations

import json
import math
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from scripts.bvmtools.metrics import phase_area_consistency, phase_area_window
from scripts.bvmtools.phase import window_indices
from scripts.bvmtools.raw import RawTrace, read_csv
from scripts.bvmtools.waveform import waveform_window_metrics

from common import (
    CONTROL_RAWS,
    DOWNSTREAM_ZOOM_PS,
    EXPECTED_HASHES,
    EXP,
    FINAL_READ_RESPONSE_PS,
    FOURTH_INTERNAL_SEARCH_PS,
    HEAD,
    QB_INTERNAL_CRITICAL_PS,
    RUNS,
    SOURCE_RAWS,
    SOURCE_SNAPSHOTS,
    TAIL_COMPLETENESS_PS,
    current_head,
    json_text,
    sha256,
    write_once,
)


ALL_CASES = ("N3_REPLAY", "N4_REPLAY") + RUNS
RAW_PATHS = {
    "N3_REPLAY": CONTROL_RAWS["N3_REPLAY"],
    "N4_REPLAY": CONTROL_RAWS["N4_REPLAY"],
    **{run_id: EXP / "runs" / run_id / "raw.csv" for run_id in RUNS},
}
EXECUTION_PATH = EXP / "analysis/execution_summary.json"
REGISTRY_PATH = EXP / "analysis/transformation_registry.json"
PRE_SOLVE_GATE_PATH = EXP / "analysis/pre_solve_gate.json"

QB_LABELS = (
    "I(I_REPLAY)",
    "V(QBIN)",
    "I(LIN|XBQ1)",
    "V(LIN|XBQ1)",
    "P(BJS|XBQ1)",
    "V(BJS|XBQ1)",
    "I(BJS|XBQ1)",
    "I(L1|XBQ1)",
    "V(L1|XBQ1)",
    "P(BJ1|XBQ1)",
    "V(BJ1|XBQ1)",
    "I(BJ1|XBQ1)",
    "I(RJ1|XBQ1)",
    "V(RJ1|XBQ1)",
    "I(L2|XBQ1)",
    "V(L2|XBQ1)",
    "I(IB|XBQ1)",
    "P(BJ2|XBQ1)",
    "V(BJ2|XBQ1)",
    "I(BJ2|XBQ1)",
    "I(RJ2|XBQ1)",
    "V(RJ2|XBQ1)",
    "I(L3|XBQ1)",
    "V(L3|XBQ1)",
    "V(QBOUT)",
)
JTL_LABELS = tuple(
    label
    for stage in range(1, 7)
    for label in (
        f"P(B01|XJTL1_{stage})",
        f"V(B01|XJTL1_{stage})",
        f"I(B01|XJTL1_{stage})",
        f"P(B02|XJTL1_{stage})",
        f"V(B02|XJTL1_{stage})",
        f"I(B02|XJTL1_{stage})",
        f"V(JTL{stage}_OUT)",
    )
) + ("I(R_TERM)",)
REQUIRED_LABELS = QB_LABELS + JTL_LABELS

INTERNAL_THRESHOLDS_V = {
    "QBIN": 0.25e-3,
    "BJS": 0.10e-3,
    "BJ1": 0.30e-3,
    "BJ2": 0.50e-3,
    "QBOUT": 0.45e-3,
}
DOWNSTREAM_THRESHOLDS = {
    "QBOUT": 0.45e-3,
    **{f"JTL{stage}_OUT": 0.50e-3 for stage in range(1, 7)},
    "R_TERM": 5.0e-6,
}
THIRD_QBOUT_PS = {"N3_REPLAY": 125.9, "N4_REPLAY": 121.9}
PHASE_AREA_LABELS = {
    "BJS": ("P(BJS|XBQ1)", "V(BJS|XBQ1)"),
    "BJ1": ("P(BJ1|XBQ1)", "V(BJ1|XBQ1)"),
    "BJ2": ("P(BJ2|XBQ1)", "V(BJ2|XBQ1)"),
    "JTL1_B01": ("P(B01|XJTL1_1)", "V(B01|XJTL1_1)"),
    "JTL6_B01": ("P(B01|XJTL1_6)", "V(B01|XJTL1_6)"),
}


def ps_window(bounds: tuple[float, float]) -> tuple[float, float]:
    return bounds[0] * 1.0e-12, bounds[1] * 1.0e-12


def finite_grid_qa(trace: RawTrace) -> dict[str, object]:
    qa = trace.qa()
    dt_ps = [value * 1.0e12 for value in trace.dt]
    return {
        "status": "PASS",
        "sample_count": trace.sample_count,
        "time_start_ps": trace.time[0] * 1.0e12,
        "time_end_ps": trace.time[-1] * 1.0e12,
        "dt_min_ps": min(dt_ps),
        "dt_max_ps": max(dt_ps),
        "irregular_interval_count": sum(value > 0.1000000001 for value in dt_ps),
        "strictly_increasing": qa["strictly_increasing_time"],
        "nan_inf_status": qa["nan_inf_status"],
        "duplicate_columns": qa["duplicate_columns"],
        "header_count": len(trace.headers),
    }


def window_stats(trace: RawTrace, label: str, bounds: tuple[float, float], unit: str) -> dict[str, object]:
    return waveform_window_metrics(trace.time, trace.column(label), ps_window(bounds), unit=unit)


def activity_clusters(
    trace: RawTrace,
    label: str,
    threshold: float,
    bounds: tuple[float, float],
    *,
    minimum_samples: int = 2,
) -> list[dict[str, object]]:
    indices = list(window_indices(trace.time, *ps_window(bounds)))
    values = trace.column(label)
    clusters: list[dict[str, object]] = []
    active: list[int] = []
    for index in indices + [None]:
        qualifies = index is not None and abs(values[index]) > threshold
        if qualifies:
            active.append(index)
            continue
        if len(active) >= minimum_samples:
            peak_index = max(active, key=lambda item: abs(values[item]))
            clusters.append(
                {
                    "start_ps": trace.time[active[0]] * 1.0e12,
                    "end_ps": trace.time[active[-1]] * 1.0e12,
                    "sample_count": len(active),
                    "sampled_span_ps": (trace.time[active[-1]] - trace.time[active[0]]) * 1.0e12,
                    "peak_abs": abs(values[peak_index]),
                    "peak_abs_display": abs(values[peak_index]) * (1.0e3 if label.startswith("V(") else 1.0e6),
                    "peak_signed_display": values[peak_index] * (1.0e3 if label.startswith("V(") else 1.0e6),
                    "peak_time_ps": trace.time[peak_index] * 1.0e12,
                    "threshold": threshold,
                    "threshold_semantics": "absolute activity samples/clusters only; not event count",
                }
            )
        active = []
    return clusters


def post_reference_candidates(
    clusters: list[dict[str, object]], reference_ps: float, guard_ps: float
) -> dict[str, object]:
    start_ps = reference_ps + guard_ps
    post = [item for item in clusters if float(item["start_ps"]) >= start_ps]
    overlap = [
        item
        for item in clusters
        if float(item["start_ps"]) < start_ps <= float(item["end_ps"])
    ]
    return {
        "reference_ps": reference_ps,
        "guard_ps": guard_ps,
        "search_start_ps": start_ps,
        "separable_activity_candidates": post,
        "overlapping_reference_activity": overlap,
        "status": (
            "OBSERVED_BOUNDED_CANDIDATE_ACTIVITY"
            if post
            else "ACTIVITY_OVERLAPS_REFERENCE_OR_NOT_OBSERVED"
        ),
    }


def ordered_internal_candidate(
    candidates: dict[str, dict[str, object]],
) -> dict[str, object]:
    required = ("QBIN", "BJ1", "BJ2", "QBOUT")
    first: dict[str, float] = {}
    missing = []
    for name in required:
        items = candidates[name]["separable_activity_candidates"]
        if not items:
            missing.append(name)
        else:
            first[name] = float(items[0]["start_ps"])
    order = [first[name] for name in required if name in first]
    strictly_ordered = len(order) == len(required) and all(
        left < right for left, right in zip(order, order[1:])
    )
    return {
        "required_progression": list(required),
        "first_candidate_start_ps": first,
        "missing_required_stages": missing,
        "strictly_increasing_activity_order": strictly_ordered,
        "status": (
            "BOUNDED_INTERNAL_PROGRESSION_CANDIDATE"
            if strictly_ordered
            else "NOT_ESTABLISHED"
        ),
        "interpretation": "descriptive internal activity order; not an SFQ event count",
    }


def downstream_chain(
    trace: RawTrace,
    candidate_start_ps: float | None,
    candidate_end_ps: float | None,
    bounds: tuple[float, float],
) -> dict[str, object]:
    if candidate_start_ps is None or candidate_end_ps is None:
        return {
            "status": "NOT_ESTABLISHED",
            "reason": "no separable BJ2 candidate supplied",
            "stages": {},
            "strictly_increasing": False,
        }
    stage_names = ("QBOUT",) + tuple(f"JTL{stage}_OUT" for stage in range(1, 7)) + ("R_TERM",)
    stage_records: dict[str, object] = {}
    first_times: list[float] = []
    for name in stage_names:
        label = "V(QBOUT)" if name == "QBOUT" else "V(" + name + ")" if name.startswith("JTL") else "I(R_TERM)"
        threshold = DOWNSTREAM_THRESHOLDS[name]
        clusters = activity_clusters(trace, label, threshold, bounds)
        following = [item for item in clusters if float(item["start_ps"]) >= candidate_end_ps]
        if following:
            item = following[0]
            stage_records[name] = {"status": "OBSERVED_ACTIVITY_AFTER_BJ2", "cluster": item}
            first_times.append(float(item["start_ps"]))
        else:
            stage_records[name] = {
                "status": "NOT_OBSERVED_AFTER_BJ2",
                "all_clusters_in_window": clusters,
            }
    ordered = len(first_times) == len(stage_names) and all(
        left < right for left, right in zip(first_times, first_times[1:])
    )
    return {
        "status": "ORDERED_DOWNSTREAM_ACTIVITY_CANDIDATE" if ordered else "NOT_ESTABLISHED",
        "stages": stage_records,
        "first_stage_times_ps": dict(
            (name, stage_records[name]["cluster"]["start_ps"])
            for name in stage_names
            if name in stage_records and "cluster" in stage_records[name]
        ),
        "strictly_increasing": ordered,
        "interpretation": "QBOUT-to-termination activity ordering only; not SFQ transmission certification",
    }


def phase_area_facts(trace: RawTrace) -> dict[str, object]:
    output: dict[str, object] = {}
    bounds = ps_window((float(QB_INTERNAL_CRITICAL_PS[0]), float(QB_INTERNAL_CRITICAL_PS[1])))
    for name, (phase_label, voltage_label) in PHASE_AREA_LABELS.items():
        result = phase_area_window(
            trace.time,
            trace.column(phase_label),
            trace.column(voltage_label),
            bounds,
            voltage_to_phase_sign=1,
            reporting_direction=1,
            include_segments=False,
        )
        result["phase_area_consistency"] = phase_area_consistency(
            float(result["phase_delta_turns"]),
            float(result["voltage_area_over_phi0"]),
            absolute_tolerance_turns=0.15,
            relative_tolerance=0.15,
        )
        result["same_jj"] = {
            "phase_label": phase_label,
            "voltage_label": voltage_label,
            "voltage_to_phase_sign": 1,
            "reporting_direction": 1,
        }
        output[name] = result
    return {
        "window_ps": [float(QB_INTERNAL_CRITICAL_PS[0]), float(QB_INTERNAL_CRITICAL_PS[1])],
        "raw_phase_unit": "rad",
        "display_conversion": "continuous_unwrap(rad)/(2*pi)",
        "facts": output,
        "interpretation": "same-JJ fixed-window arithmetic; not an SFQ event count",
    }


def third_reference(case: str) -> float:
    return THIRD_QBOUT_PS["N3_REPLAY" if case == "N3_REPLAY" else "N4_REPLAY"]


def analyze_case(case: str, trace: RawTrace) -> dict[str, object]:
    source_metrics = {
        "I_REPLAY_final_response": window_stats(
            trace,
            "I(I_REPLAY)",
            (float(FINAL_READ_RESPONSE_PS[0]), float(FINAL_READ_RESPONSE_PS[1])),
            "A",
        ),
        "I_REPLAY_tail": window_stats(
            trace,
            "I(I_REPLAY)",
            (float(TAIL_COMPLETENESS_PS[0]), float(TAIL_COMPLETENESS_PS[1])),
            "A",
        ),
    }
    internal_bounds = (
        float(FOURTH_INTERNAL_SEARCH_PS[0]),
        float(FOURTH_INTERNAL_SEARCH_PS[1]),
    )
    internal_clusters: dict[str, list[dict[str, object]]] = {}
    for name, threshold in INTERNAL_THRESHOLDS_V.items():
        label = "V(" + name + ")" if name in {"QBIN", "QBOUT"} else f"V({name}|XBQ1)"
        internal_clusters[name] = activity_clusters(trace, label, threshold, internal_bounds)
    reference_ps = third_reference(case)
    candidates = {
        name: post_reference_candidates(items, reference_ps, 0.5)
        for name, items in internal_clusters.items()
    }
    internal_progression = ordered_internal_candidate(candidates)
    bj2_items = candidates["BJ2"]["separable_activity_candidates"]
    if bj2_items:
        candidate_start = float(bj2_items[0]["start_ps"])
        candidate_end = float(bj2_items[0]["end_ps"])
    else:
        candidate_start = candidate_end = None
    downstream = downstream_chain(
        trace,
        candidate_start,
        candidate_end,
        (float(DOWNSTREAM_ZOOM_PS[0]), float(DOWNSTREAM_ZOOM_PS[1])),
    )
    activity = {
        "internal_fixed_window": {
            "window_ps": list(internal_bounds),
            "thresholds": {name: threshold for name, threshold in INTERNAL_THRESHOLDS_V.items()},
            "clusters": internal_clusters,
        },
        "downstream_fixed_window": {
            "window_ps": [float(DOWNSTREAM_ZOOM_PS[0]), float(DOWNSTREAM_ZOOM_PS[1])],
            "thresholds": DOWNSTREAM_THRESHOLDS,
        },
        "post_third_internal_candidates": candidates,
        "internal_progression": internal_progression,
        "downstream_chain": downstream,
        "reference_semantics": {
            "third_QBOUT_reference_ps": reference_ps,
            "JTL_and_terminal_are_downstream_only": True,
        },
    }
    return {
        "case": case,
        "role": "immutable control" if case in CONTROL_RAWS else "new authorized intervention",
        "raw_path": RAW_PATHS[case].relative_to(EXP.parent.parent.parent).as_posix(),
        "raw_sha256": sha256(RAW_PATHS[case]),
        "grid_qa": finite_grid_qa(trace),
        "source_metrics": source_metrics,
        "activity": activity,
        "phase_area": phase_area_facts(trace),
        "phase_and_area_are_not_SFQ_count": True,
    }


def family_assessment(metrics: dict[str, dict[str, object]], family: tuple[str, str]) -> dict[str, object]:
    records = [metrics[name] for name in family]
    complete = [
        bool(
            record["activity"]["internal_progression"]["status"]
            == "BOUNDED_INTERNAL_PROGRESSION_CANDIDATE"
            and record["activity"]["downstream_chain"]["status"]
            == "ORDERED_DOWNSTREAM_ACTIVITY_CANDIDATE"
        )
        for record in records
    ]
    bj2 = [
        bool(record["activity"]["post_third_internal_candidates"]["BJ2"]["separable_activity_candidates"])
        for record in records
    ]
    return {
        "runs": list(family),
        "both_have_separable_BJ2_activity": all(bj2),
        "both_have_bounded_complete_progression_candidate": all(complete),
        "per_run": {
            name: {
                "separable_BJ2_activity": bj2[index],
                "bounded_complete_progression_candidate": complete[index],
            }
            for index, name in enumerate(family)
        },
        "interpretation": (
            "family support requires both runs to show the registered complete progression evidence; "
            "partial BJ2 activity alone is insufficient"
        ),
    }


def raw_hash_qa(metadata: dict[str, object]) -> dict[str, object]:
    result: dict[str, object] = {}
    for case, path in RAW_PATHS.items():
        before = sha256(path)
        execution_hash = (
            metadata["cases"][case]["artifacts"]["raw"]["sha256"]
            if case in metadata["cases"]
            else EXPECTED_HASHES[f"{case}_raw"]
        )
        result[case] = {
            "path": path.relative_to(EXP.parent.parent.parent).as_posix(),
            "hash_at_execution_record": execution_hash,
            "hash_before_analysis": before,
            "expected_control_hash": EXPECTED_HASHES.get(f"{case}_raw"),
            "matches_execution_record": before == execution_hash,
            "matches_expected_control": (
                before == EXPECTED_HASHES[f"{case}_raw"] if case in CONTROL_RAWS else None
            ),
        }
    return result


def main() -> int:
    if current_head() != HEAD:
        raise RuntimeError("HEAD changed after pre-solve gate")
    execution = json.loads(EXECUTION_PATH.read_text(encoding="utf-8"))
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    pre_solve = json.loads(PRE_SOLVE_GATE_PATH.read_text(encoding="utf-8"))
    if execution.get("status") != "PASS" or execution.get("physical_run_count") != 4:
        raise RuntimeError("execution summary is not the authorized four-run PASS")
    if pre_solve.get("status") != "PASS":
        raise RuntimeError("pre-solve gate is not PASS")
    if list(registry.get("authorized_runs", {})) != list(RUNS):
        raise RuntimeError("registry does not contain exactly the four authorized runs")
    before_hashes = raw_hash_qa(execution)
    traces = {case: read_csv(path) for case, path in RAW_PATHS.items()}
    failures: list[str] = []
    for case, trace in traces.items():
        missing = [label for label in REQUIRED_LABELS if label not in trace.headers]
        if missing:
            failures.append(f"{case}: missing required probes {missing}")
        if trace.duplicate_columns:
            failures.append(f"{case}: duplicate columns {trace.duplicate_columns}")
        if trace.qa()["nan_inf_status"] != "PASS":
            failures.append(f"{case}: non-finite raw data")
        if case in RUNS and trace.sample_count != 2059:
            failures.append(f"{case}: unexpected extended sample count {trace.sample_count}")
    metrics = {case: analyze_case(case, trace) for case, trace in traces.items()}
    after_hashes = raw_hash_qa(execution)
    for case in ALL_CASES:
        if before_hashes[case]["hash_before_analysis"] != after_hashes[case]["hash_before_analysis"]:
            failures.append(f"{case}: raw hash changed during analysis")
    for case, item in after_hashes.items():
        if not item["matches_execution_record"]:
            failures.append(f"{case}: current raw hash differs from execution metadata")
        if case in CONTROL_RAWS and not item["matches_expected_control"]:
            failures.append(f"{case}: immutable control hash mismatch")
    assessment = {
        "delay_family": family_assessment(
            metrics,
            ("DELTA4_DELAY_3PS", "DELTA4_DELAY_6PS"),
        ),
        "gain_family": family_assessment(
            metrics,
            ("DELTA4_GAIN_1P25", "DELTA4_GAIN_1P50"),
        ),
    }
    delay_complete = assessment["delay_family"]["both_have_bounded_complete_progression_candidate"]
    gain_complete = assessment["gain_family"]["both_have_bounded_complete_progression_candidate"]
    if delay_complete and not gain_complete:
        classification = "DELAY_ONLY_BOUNDED_SUPPORT"
    elif gain_complete and not delay_complete:
        classification = "GAIN_ONLY_BOUNDED_SUPPORT"
    elif delay_complete and gain_complete:
        classification = "BOTH_MIXED_SENSITIVITY"
    else:
        classification = "MIXED_OR_UNRESOLVED"
    result = {
        "schema": "jm2-delta4-replay-sensitivity-analysis-v1",
        "experiment_id": EXP.name,
        "head": current_head(),
        "status": "PASS" if not failures else "ARTIFACT_INVALID",
        "execution": {
            "physical_run_count": execution["physical_run_count"],
            "authorized_runs": list(RUNS),
            "controls": ["N3_REPLAY", "N4_REPLAY"],
            "controls_rerun": False,
        },
        "raw_hash_qa_before_and_after": {
            "before": before_hashes,
            "after": after_hashes,
            "all_unchanged": not any(
                before_hashes[case]["hash_before_analysis"] != after_hashes[case]["hash_before_analysis"]
                for case in ALL_CASES
            ),
        },
        "fixed_windows_ps": {
            "FINAL_READ_RESPONSE": [float(FINAL_READ_RESPONSE_PS[0]), float(FINAL_READ_RESPONSE_PS[1])],
            "QB_INTERNAL_CRITICAL": [float(QB_INTERNAL_CRITICAL_PS[0]), float(QB_INTERNAL_CRITICAL_PS[1])],
            "FOURTH_INTERNAL_SEARCH": [float(FOURTH_INTERNAL_SEARCH_PS[0]), float(FOURTH_INTERNAL_SEARCH_PS[1])],
            "DOWNSTREAM_ZOOM": [float(DOWNSTREAM_ZOOM_PS[0]), float(DOWNSTREAM_ZOOM_PS[1])],
            "TAIL_COMPLETENESS": [float(TAIL_COMPLETENESS_PS[0]), float(TAIL_COMPLETENESS_PS[1])],
            "semantics": "half-open [start,end)",
        },
        "cases": metrics,
        "family_assessment": assessment,
        "classification": {
            "bounded_result": classification,
            "meaning": "fixed four-intervention replay comparison only",
            "no_root_cause": True,
            "no_SFQ_count": True,
            "convergence": "UNKNOWN",
        },
        "interpretation_labels": ["OBSERVED", "DERIVED", "BOUNDED_RESULT", "UNKNOWN"],
        "unknowns": [
            "whether a different intervention would complete the partial progression",
            "unique separation of recovery, internal regeneration and effective stimulus",
            "timestep convergence and solver/parameter sensitivity",
            "hardware behavior or universal mechanism",
        ],
        "failures": failures,
    }
    write_once(EXP / "analysis/metrics.json", json_text(result))
    print(
        json.dumps(
            {
                "status": result["status"],
                "classification": classification,
                "raw_unchanged": result["raw_hash_qa_before_and_after"]["all_unchanged"],
                "failures": failures,
            },
            ensure_ascii=False,
        )
    )
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
