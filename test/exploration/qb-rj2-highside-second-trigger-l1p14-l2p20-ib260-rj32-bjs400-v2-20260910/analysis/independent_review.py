#!/usr/bin/env python3
"""Independent stdlib-only numerical and adversarial review of the RJ2 evidence.

This reviewer intentionally does not import the experiment QA implementation or
the shared raw parser.  It reads the immutable CSV artifacts directly and
recomputes the registered window counts, phase navigation anchors, differential
voltage areas, and required L1-zero proxy.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
REGISTERED_NEW_RUNS = (
    "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_0001",
    "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_0011",
    "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P14_0001",
    "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P14_0011",
    "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P16_0001",
    "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P16_0011",
)
NEW_RUNS = REGISTERED_NEW_RUNS
REUSE_RUNS = ("ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P10_0001", "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P10_0011")
ALL_RUNS = REUSE_RUNS + NEW_RUNS
RJ2_BY_RUN = {run_id: float(re.search(r"RJ2P(\d+)", run_id).group(1)) for run_id in NEW_RUNS}
RJ2_BY_RUN.update({run_id: 10.0 for run_id in REUSE_RUNS})
MASK_BY_RUN = {run_id: run_id.rsplit("_", 1)[1] for run_id in ALL_RUNS}
RAW_LABELS = ("P(BJ1|XBQ1)", "P(BJ2|XBQ1)", "V(BJ1|XBQ1)", "V(BJ2|XBQ1)", "I(L1|XBQ1)", "I(L2|XBQ1)")
PI2 = 2.0 * math.pi


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def raw_path(run_id: str) -> Path:
    root = EXP / ("runs" if run_id in NEW_RUNS else "references/reused")
    return root / run_id / "raw.csv"


def deck_path(run_id: str) -> Path:
    root = EXP / ("runs" if run_id in NEW_RUNS else "references/reused")
    return root / run_id / "deck.cir"


def metadata_path(run_id: str) -> Path:
    root = EXP / ("runs" if run_id in NEW_RUNS else "references/reused")
    return root / run_id / "metadata.json"


def read_raw(path: Path) -> tuple[list[str], list[float], dict[str, list[float]]]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.reader(stream)
        header = next(reader)
        if len(header) != len(set(header)):
            raise ValueError(f"duplicate header: {path}")
        rows = list(reader)
    columns = {name: [] for name in header}
    for row in rows:
        if len(row) != len(header):
            raise ValueError(f"row width mismatch: {path}")
        for name, value in zip(header, row):
            number = float(value)
            if not math.isfinite(number):
                raise ValueError(f"nonfinite value: {path}")
            columns[name].append(number)
    return header, columns["time"], columns


def indexes(times: list[float], start: float, end: float) -> list[int]:
    return [index for index, value in enumerate(times) if start <= value < end]


def trapezoid(times: list[float], values: list[float]) -> float:
    return sum((values[index] + values[index + 1]) * 0.5 * (times[index + 1] - times[index]) for index in range(len(values) - 1))


def integrate(times: list[float], values: list[float], start: float, end: float) -> float | None:
    selected = indexes(times, start, end)
    if len(selected) < 2:
        return None
    return trapezoid([times[index] for index in selected], [values[index] for index in selected])


def unwrap(values: list[float]) -> list[float]:
    if not values:
        return []
    output = [values[0]]
    previous = values[0]
    for current in values[1:]:
        delta = current - previous
        while delta > math.pi:
            delta -= PI2
        while delta < -math.pi:
            delta += PI2
        output.append(output[-1] + delta)
        previous = current
    return output


def phase_anchor(times: list[float], values: list[float], threshold: float) -> int | None:
    baseline = indexes(times, 101e-12, 110e-12)
    origin = indexes(times, 110e-12, 200e-12)
    if not baseline or not origin:
        return None
    continuous = unwrap(values)
    reference = continuous[baseline[0]]
    return next((index for index in origin if (continuous[index] - reference) / PI2 >= threshold), None)


def phase_anchor_from(times: list[float], values: list[float], *, reference_index: int, start_index: int, threshold: float, end_time_s: float = 200e-12) -> int | None:
    continuous = unwrap(values)
    reference = continuous[reference_index]
    return next((index for index in range(start_index, len(times)) if times[index] < end_time_s and (continuous[index] - reference) / PI2 >= threshold), None)


def positive_segments(times: list[float], l1: list[float], anchor: int) -> list[dict[str, Any]]:
    groups: list[list[int]] = []
    for index in range(anchor, len(times)):
        if times[index] >= 200e-12:
            break
        if l1[index] > 0.0:
            if not groups or index != groups[-1][-1] + 1:
                groups.append([index])
            else:
                groups[-1].append(index)
    return [{
        "start_time_ps": times[group[0]] * 1e12,
        "end_time_ps": times[group[-1]] * 1e12,
        "positive_dwell_duration_ps": (times[group[-1]] - times[group[0]]) * 1e12,
        "peak_time_ps": times[max(group, key=lambda index: l1[index])] * 1e12,
        "peak_A": max(l1[index] for index in group),
    } for group in groups]


def ordered_jtl_candidate(times: list[float], columns: dict[str, list[float]], *, reference_index: int, start_index: int, threshold: float, end_time_s: float = 200e-12) -> tuple[bool, dict[str, float | None]]:
    markers: dict[str, float | None] = {}
    for stage in range(1, 7):
        index = phase_anchor_from(times, columns[f"P(B01|XJTL1_{stage})"], reference_index=reference_index, start_index=start_index, threshold=threshold, end_time_s=end_time_s)
        markers[f"JTL{stage}"] = times[index] * 1e12 if index is not None else None
    ordered = all(value is not None for value in markers.values()) and all(markers[f"JTL{stage}"] < markers[f"JTL{stage + 1}"] for stage in range(1, 6))
    return ordered, markers


def multi_evidence_candidate(times: list[float], columns: dict[str, list[float]], *, baseline_window: tuple[float, float], origin_window: tuple[float, float], reference_index: int | None = None, start_index: int | None = None) -> dict[str, Any]:
    baseline = indexes(times, *baseline_window)
    origin = indexes(times, *origin_window)
    if not baseline or not origin:
        return {"status": "UNKNOWN", "checks": {}}
    reference = baseline[0] if reference_index is None else reference_index
    start = origin[0] if start_index is None else start_index
    bj1 = phase_anchor_from(times, columns["P(BJ1|XBQ1)"], reference_index=reference, start_index=start, threshold=0.5, end_time_s=origin_window[1])
    bj2 = phase_anchor_from(times, columns["P(BJ2|XBQ1)"], reference_index=reference, start_index=start, threshold=0.9, end_time_s=origin_window[1])
    ordered, markers = ordered_jtl_candidate(times, columns, reference_index=reference, start_index=start, threshold=0.5, end_time_s=origin_window[1])
    post = indexes(times, times[start], 200e-12)
    checks = {
        "BJ1_progression_candidate": bj1 is not None,
        "BJ2_progression_candidate": bj2 is not None,
        "QBOUT_direct_signal": any(abs(columns["V(QBOUT)"][index]) > 0.0 for index in post),
        "ordered_JTL1_to_JTL6_candidate": ordered,
        "terminal_direct_area": integrate(times, columns["V(JTL6_OUT)"], times[start], 200e-12) is not None,
    }
    return {
        "status": "BOUNDED_RESULT" if all(checks.values()) else "NO_COMPLETE_MULTI_EVIDENCE_CANDIDATE",
        "checks": checks,
        "BJ1_marker_time_ps": times[bj1] * 1e12 if bj1 is not None else None,
        "BJ2_marker_time_ps": times[bj2] * 1e12 if bj2 is not None else None,
        "ordered_JTL_marker_times_ps": markers,
        "terminal_area_V_s": integrate(times, columns["V(JTL6_OUT)"], times[start], 200e-12),
        "not_event_count": True,
        "not_sfq_count": True,
    }


def diff_values(columns: dict[str, list[float]], indices: list[int]) -> list[float]:
    bj1 = columns["V(BJ1|XBQ1)"]
    bj2 = columns["V(BJ2|XBQ1)"]
    return [bj1[index] - bj2[index] for index in indices]


def diff_integral(times: list[float], columns: dict[str, list[float]], start: float, end: float) -> float | None:
    selected = indexes(times, start, end)
    if len(selected) < 2:
        return None
    return trapezoid([times[index] for index in selected], diff_values(columns, selected))


def cumulative_diff(times: list[float], columns: dict[str, list[float]], start: float, end: float) -> float | None:
    return diff_integral(times, columns, start, end)


def close(left: Any, right: Any, *, rel: float = 1e-11, absolute: float = 1e-24) -> bool:
    if left is None or right is None:
        return left is right
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return math.isclose(float(left), float(right), rel_tol=rel, abs_tol=absolute)
    return left == right


def compare(failures: list[str], label: str, actual: Any, expected: Any) -> None:
    if not close(actual, expected):
        failures.append(f"{label}: independent={actual!r}, recorded={expected!r}")


def main() -> int:
    failures: list[str] = []
    probes: dict[str, Any] = {}
    traces: dict[str, tuple[list[str], list[float], dict[str, list[float]]]] = {}
    raw_hashes: dict[str, str] = {}
    deck_hashes: dict[str, str] = {}
    recrossing_records: dict[str, dict[str, Any]] = {}
    positive_records: dict[str, list[dict[str, Any]]] = {}
    control_records: dict[str, dict[str, Any]] = {}
    first_response_records: dict[str, dict[str, Any]] = {}
    second_response_records: dict[str, dict[str, Any]] = {}
    execution = json.loads((EXP / "qa/execution_summary.json").read_text(encoding="utf-8"))
    global NEW_RUNS, ALL_RUNS, RJ2_BY_RUN, MASK_BY_RUN
    NEW_RUNS = tuple(execution.get("run_order", ()))
    if not NEW_RUNS or any(run_id not in REGISTERED_NEW_RUNS for run_id in NEW_RUNS):
        raise RuntimeError("execution summary does not contain a non-empty registered RJ2 prefix")
    if NEW_RUNS != tuple(run_id for run_id in REGISTERED_NEW_RUNS if run_id in NEW_RUNS):
        raise RuntimeError("execution run order is not a registered ascending RJ2 prefix")
    ALL_RUNS = REUSE_RUNS + NEW_RUNS
    RJ2_BY_RUN = {run_id: float(re.search(r"RJ2P(\d+)", run_id).group(1)) for run_id in REGISTERED_NEW_RUNS}
    RJ2_BY_RUN.update({run_id: 10.0 for run_id in REUSE_RUNS})
    MASK_BY_RUN = {run_id: run_id.rsplit("_", 1)[1] for run_id in ALL_RUNS}

    for run_id in ALL_RUNS:
        raw = raw_path(run_id)
        deck = deck_path(run_id)
        if not raw.is_file() or not deck.is_file():
            failures.append(f"missing raw/deck: {run_id}")
            continue
        try:
            header, times, columns = read_raw(raw)
        except Exception as exc:
            failures.append(f"raw parse failure {run_id}: {exc}")
            continue
        missing = [label for label in RAW_LABELS if label not in columns]
        if missing:
            failures.append(f"missing independent review probes {run_id}: {missing}")
        if len(times) != 1999 or not times or times[0] != 0.0 or times[-1] != 1.999e-10:
            failures.append(f"time extent mismatch: {run_id}")
        if any(right <= left for left, right in zip(times, times[1:])):
            failures.append(f"time is not strictly increasing: {run_id}")
        traces[run_id] = (header, times, columns)
        raw_hashes[run_id] = sha256(raw)
        deck_hashes[run_id] = sha256(deck)

    if len(traces) != len(ALL_RUNS):
        failures.append(f"expected {len(ALL_RUNS)} readable raw files after the registered stop, found {len(traces)}")
    if len(set(raw_hashes.values())) != len(raw_hashes):
        failures.append("raw hashes are not unique across the observed logical cases")
    if len(set(deck_hashes.values())) != len(deck_hashes):
        failures.append("deck hashes are not unique across the observed logical cases")

    window_counts: dict[str, set[int]] = {"CONTROL_ORIGIN_[70,110)": set(), "FINAL_ORIGIN_[110,200)": set(), "PRE_SWITCH_[110,114.5)": set()}
    recorded = json.loads((EXP / "mechanical_summary.json").read_text(encoding="utf-8"))
    raw_qa = json.loads((EXP / "qa/raw_qa.json").read_text(encoding="utf-8"))
    preflight = json.loads((EXP / "analysis/preflight.json").read_text(encoding="utf-8"))
    reuse_manifest = json.loads((EXP / "REUSED_REFERENCE_MANIFEST.json").read_text(encoding="utf-8"))
    if raw_qa.get("status") != "PASS" or recorded.get("status") != "PASS":
        failures.append("registered raw/mechanical QA is not PASS")
    if execution.get("status") != "PASS" or execution.get("solver_solve_invocations") != len(NEW_RUNS) or execution.get("unauthorized_extra_solves") != 0:
        failures.append("execution summary is not an exact registered-stop/0-extra PASS")

    case_records = recorded.get("cases", {})
    raw_records = raw_qa.get("cases", {})
    phase_records: dict[str, dict[str, int | None]] = {}
    for run_id, (_header, times, columns) in traces.items():
        window_counts["CONTROL_ORIGIN_[70,110)"].add(len(indexes(times, 70e-12, 110e-12)))
        window_counts["FINAL_ORIGIN_[110,200)"].add(len(indexes(times, 110e-12, 200e-12)))
        window_counts["PRE_SWITCH_[110,114.5)"].add(len(indexes(times, 110e-12, 114.5e-12)))
        if "V(IB|XBQ1)" not in _header:
            pass
        else:
            failures.append(f"optional V(IB|XBQ1) unexpectedly present: {run_id}")
        bj1_index = phase_anchor(times, columns["P(BJ1|XBQ1)"], 0.5)
        bj2_index = phase_anchor(times, columns["P(BJ2|XBQ1)"], 0.9)
        phase_records[run_id] = {"bj1": bj1_index, "bj2": bj2_index}
        case = case_records.get(run_id, {})
        final = case.get("FINAL_ORIGIN", {}).get("phase_diagnostics", {})
        bj1 = final.get("BJ1", {})
        bj2 = final.get("BJ2", {})
        compare(failures, f"{run_id} BJ1 anchor index", bj1_index, bj1.get("first_half_turn_sample_index"))
        compare(failures, f"{run_id} BJ2 anchor index", bj2_index, bj2.get("first_0p9_turn_sample_index"))
        compare(failures, f"{run_id} RJ2 value", RJ2_BY_RUN[run_id], case.get("RJ2_ohm"))
        compare(failures, f"{run_id} L2 fixed value", 2.0, case.get("L2_pH"))
        compare(failures, f"{run_id} raw hash in mechanical summary", raw_hashes[run_id], case.get("raw_provenance", {}).get("sha256"))
        compare(failures, f"{run_id} raw hash in raw QA", raw_hashes[run_id], raw_records.get(run_id, {}).get("sha256"))
        transition_times = []
        if bj2_index is not None:
            l1 = columns["I(L1|XBQ1)"]
            transition_times = [times[index] * 1e12 for index in range(bj2_index + 1, len(times)) if l1[index - 1] < 0.0 < l1[index]]
        recrossing_records[run_id] = {"anchor_index": bj2_index, "negative_to_positive_times_ps": transition_times, "observed": bool(transition_times)}
        recorded_observation = case.get("POST_FIRST_BJ2_REARM", {}).get("recrossing_observation")
        expected_observation = "OBSERVED_L1_RECROSSING" if transition_times else "NO_OBSERVED_L1_RECROSSING"
        compare(failures, f"{run_id} strict L1 recrossing label", expected_observation, recorded_observation)

        control_candidate = multi_evidence_candidate(
            times,
            columns,
            baseline_window=(61e-12, 70e-12),
            origin_window=(70e-12, 110e-12),
        )
        final_candidate = multi_evidence_candidate(
            times,
            columns,
            baseline_window=(101e-12, 110e-12),
            origin_window=(110e-12, 200e-12),
        )
        control_records[run_id] = control_candidate
        first_response_records[run_id] = final_candidate
        recorded_control = case.get("CONTROL_HARD_GUARDRAIL", {})
        recorded_first = case.get(f"FIRST_RESPONSE_{MASK_BY_RUN[run_id]}", {})
        recorded_control_status = "BOUNDED_RESULT" if recorded_control.get("status") == "UNSUITABLE_WORKING_POINT" else "CLEAN"
        independent_control_status = "BOUNDED_RESULT" if control_candidate.get("status") == "BOUNDED_RESULT" else "CLEAN"
        compare(failures, f"{run_id} control response status", independent_control_status, recorded_control_status)
        compare(failures, f"{run_id} first response status", final_candidate.get("status"), recorded_first.get("status"))

        if bj2_index is not None:
            anchor_time = times[bj2_index]
            diff_record = case.get("DIFFERENTIAL_VOLTAGE_IMPULSE", {})
            for name, start, end in (
                ("A_DIFF_cumulative_landmarks.from_110_to_121", 110e-12, 121e-12),
                ("A_DIFF_cumulative_landmarks.from_110_to_140", 110e-12, 140e-12),
                ("A_DIFF_cumulative_landmarks.from_110_to_200", 110e-12, 200e-12),
            ):
                key = name.rsplit(".", 1)[1]
                compare(failures, f"{run_id} {name}", cumulative_diff(times, columns, start, end), diff_record.get("A_DIFF_cumulative_landmarks", {}).get(key, {}).get("value_V_s"))
            compare(failures, f"{run_id} differential after BJ2 anchor", cumulative_diff(times, columns, anchor_time, 140e-12), diff_record.get("A_DIFF_cumulative_after_BJ2_anchor_to_140", {}).get("value_V_s"))
            l1_anchor = columns["I(L1|XBQ1)"][bj2_index]
            required = -3.4e-12 * l1_anchor if l1_anchor < 0.0 else None
            compare(failures, f"{run_id} required L1-zero proxy", required, diff_record.get("A_REQUIRED_TO_L1_ZERO", {}).get("value_V_s"))
            post = case.get("POST_FIRST_BJ2_REARM", {})
            post_indices = [index for index, value in enumerate(times) if anchor_time <= value < 200e-12]
            compare(failures, f"{run_id} post L1 minimum", min(columns["I(L1|XBQ1)"][index] for index in post_indices), post.get("L1_post_anchor_min"))
            compare(failures, f"{run_id} post L2 maximum", max(columns["I(L2|XBQ1)"][index] for index in post_indices), post.get("L2_post_anchor_max_A"))
            positive = positive_segments(times, columns["I(L1|XBQ1)"], bj2_index)
            positive_records[run_id] = positive
            second_analysis = case.get("SECOND_TRIGGER_ANALYSIS", {})
            compare(failures, f"{run_id} positive segment count", len(positive), second_analysis.get("positive_segment_count"))
            first_record = second_analysis.get("first_successful_regeneration_reference") or {}
            strongest_record = second_analysis.get("strongest_second_positive_excursion") or {}
            if positive:
                compare(failures, f"{run_id} first positive L1 peak", positive[0]["peak_A"], first_record.get("L1_peak_A"))
            strongest = max(positive[1:], key=lambda item: item["peak_A"]) if len(positive) > 1 else None
            if strongest is not None:
                compare(failures, f"{run_id} strongest second L1 peak", strongest["peak_A"], strongest_record.get("L1_peak_A"))
            second_start = None
            if strongest is not None:
                second_start = next((index for index, value in enumerate(times) if math.isclose(value * 1e12, strongest["start_time_ps"], rel_tol=0.0, abs_tol=1e-9)), None)
            independent_second = multi_evidence_candidate(
                times,
                columns,
                baseline_window=(101e-12, 110e-12),
                origin_window=(110e-12, 200e-12),
                reference_index=second_start if second_start is not None else bj2_index,
                start_index=second_start if second_start is not None else bj2_index,
            )
            second_response_records[run_id] = independent_second
            independent_second_status = "BOUNDED_RESULT" if independent_second.get("status") == "BOUNDED_RESULT" else "NO_SECOND_COMPLETE_MULTI_EVIDENCE_CANDIDATE"
            compare(failures, f"{run_id} second response status", independent_second_status, (second_analysis.get("second_complete_multi_evidence_candidate") or {}).get("status"))

    expected_window_counts = {
        "CONTROL_ORIGIN_[70,110)": 400,
        "FINAL_ORIGIN_[110,200)": 900,
        "PRE_SWITCH_[110,114.5)": 45,
    }
    for name, expected in expected_window_counts.items():
        if window_counts[name] != {expected}:
            failures.append(f"window count boundary mismatch {name}: {sorted(window_counts[name])}")

    for run_id in NEW_RUNS:
        metadata = metadata_path(run_id)
        if not metadata.is_file():
            failures.append(f"missing new metadata: {run_id}")
            continue
        value = json.loads(metadata.read_text(encoding="utf-8"))
        if value.get("execution_status") != "RUN_PASS" or value.get("physical_solve_this_experiment") is not True:
            failures.append(f"new metadata execution flag mismatch: {run_id}")
        compare(failures, f"{run_id} metadata RJ2", RJ2_BY_RUN[run_id], value.get("rj2_ohm"))
        compare(failures, f"{run_id} metadata mask", MASK_BY_RUN[run_id], value.get("mask"))
        compare(failures, f"{run_id} metadata raw hash", raw_hashes[run_id], value.get("artifacts", {}).get("raw", {}).get("sha256"))
        compare(failures, f"{run_id} metadata deck hash", deck_hashes[run_id], value.get("artifacts", {}).get("deck", {}).get("sha256"))
        deck_text = deck_path(run_id).read_text(encoding="utf-8")
        if f".param RJ2_VALUE={RJ2_BY_RUN[run_id]:g}" not in deck_text:
            failures.append(f"RJ2 deck parameter mismatch: {run_id}")
        if ".param L2_VALUE" in deck_text:
            failures.append(f"unexpected L2 parameter perturbation: {run_id}")

    for run_id in REUSE_RUNS:
        manifest_entry = reuse_manifest.get("references", {}).get(run_id, {})
        compare(failures, f"{run_id} reuse raw hash", raw_hashes[run_id], manifest_entry.get("artifacts", {}).get("raw.csv", {}).get("source_sha256"))
        compare(failures, f"{run_id} reuse deck hash", deck_hashes[run_id], manifest_entry.get("artifacts", {}).get("deck.cir", {}).get("source_sha256"))

    observed_recrossing_cases = [run_id for run_id in ALL_RUNS if recrossing_records.get(run_id, {}).get("observed")]
    compare(failures, "mechanical summary observed recrossing cases", observed_recrossing_cases, recorded.get("observed_l1_recrossing_cases"))
    if len(NEW_RUNS) < len(REGISTERED_NEW_RUNS):
        if not isinstance(execution.get("early_stop_reason"), str) or not execution.get("early_stop_reason", "").startswith("STAGE_"):
            failures.append(f"registered staged-stop reason is missing: {execution.get('early_stop_reason')!r}")
        if not execution.get("registered_unrun_values"):
            failures.append("staged stop does not preserve registered unrun values")

    # Adversarial probes: non-no-op parameterization, correct branch routing,
    # independent oracle agreement, boundary discipline, stale-artifact shield,
    # and explicit overclaim ceiling.
    probes.update({
        "no_op_parameterization": len(set(deck_hashes.values())) == len(deck_hashes) and {RJ2_BY_RUN[run_id] for run_id in NEW_RUNS}.issubset({12.0, 14.0, 16.0}),
        "wrong_branch_guard": all(case_records.get(run_id, {}).get("RJ2_ohm") == RJ2_BY_RUN[run_id] for run_id in ALL_RUNS),
        "weak_oracle_differential": not any("independent=" in failure for failure in failures),
        "boundary_windows": all(window_counts[name] == {expected} for name, expected in expected_window_counts.items()),
        "stale_artifact_guard": raw_qa.get("pre_analysis_sha256") == raw_qa.get("post_analysis_sha256") and all(raw_hashes.get(run_id) == raw_records.get(run_id, {}).get("sha256") for run_id in ALL_RUNS),
        "overclaim_ceiling": recorded.get("scientific_interpretation_performed") is False and raw_qa.get("scientific_analysis_performed") is False,
        "strict_recrossing_recomputed": observed_recrossing_cases == recorded.get("observed_l1_recrossing_cases"),
        "control_first_second_candidates_recomputed": all(run_id in control_records and run_id in first_response_records for run_id in ALL_RUNS) and all(run_id in second_response_records for run_id in positive_records),
        "stage_decision_artifacts_present": bool(execution.get("stage_decisions")) and all((EXP / "qa/stages" / f"stage{item.get('stage')}_decision.json").is_file() for item in execution.get("stage_decisions", [])),
    })
    for name, value in probes.items():
        if value is not True:
            failures.append(f"adversarial probe failed: {name}")

    result = {
        "schema": "bjs400-rj2-highside-second-trigger-independent-review-v2",
        "experiment_id": EXP.name,
        "created_at_local": now(),
        "status": "PASS" if not failures else "FAIL",
        "review_type": "stdlib-only numerical cross-check plus bounded adversarial probes",
        "cases_checked": len(traces),
        "registered_new_case_count": len(REGISTERED_NEW_RUNS),
        "unrun_preserved_case_ids": [run_id for run_id in REGISTERED_NEW_RUNS if run_id not in NEW_RUNS],
        "raw_hash_count": len(set(raw_hashes.values())),
        "raw_hashes_unique": len(set(raw_hashes.values())) == len(raw_hashes),
        "optional_unknown": "V(IB|XBQ1)",
        "optional_unknown_absent_in_all_cases": all("V(IB|XBQ1)" not in header for header, _times, _columns in traces.values()),
        "window_counts": {name: sorted(values) for name, values in window_counts.items()},
        "phase_anchor_recomputed": phase_records,
        "recrossing_recomputed": recrossing_records,
        "positive_excursions_recomputed": positive_records,
        "control_candidates_recomputed": control_records,
        "first_response_candidates_recomputed": first_response_records,
        "second_response_candidates_recomputed": second_response_records,
        "stage_decisions_checked": execution.get("stage_decisions", []),
        "adversarial_probes": probes,
        "execution_head": execution.get("head"),
        "preflight_head": preflight.get("head"),
        "metadata_hash_checks": True,
        "raw_immutable_check": raw_qa.get("pre_analysis_sha256") == raw_qa.get("post_analysis_sha256"),
        "scientific_interpretation_performed": False,
        "failures": failures,
        "residual_uncertainty": [
            "No timestep convergence or scientific mechanism interpretation was performed.",
            "Phase thresholds remain stored-sample navigation diagnostics, not event or SFQ counts.",
            "Optional V(IB|XBQ1) remains UNKNOWN because the solver did not emit it.",
        ],
    }
    qa_path = EXP / "qa/independent_review.json"
    qa_path.parent.mkdir(parents=True, exist_ok=True)
    qa_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    review = EXP / "analysis/REVIEW.md"
    review.write_text(
        "\n".join([
            "# Independent numerical and adversarial review",
            "",
            "Review status: `" + result["status"] + "`.",
            "",
            "This review used a stdlib-only CSV reader and an independently implemented phase unwrap and trapezoid calculation; it did not import the experiment QA pipeline.",
            "",
            f"- Logical cases checked after the registered stop: {len(traces)}; unique raw hashes: {len(set(raw_hashes.values()))}.",
            f"- Window cardinalities: CONTROL_ORIGIN={sorted(window_counts['CONTROL_ORIGIN_[70,110)'])}, FINAL_ORIGIN={sorted(window_counts['FINAL_ORIGIN_[110,200)'])}, PRE_SWITCH={sorted(window_counts['PRE_SWITCH_[110,114.5)'])}.",
            "- Optional `V(IB|XBQ1)` is absent in all cases and remains `UNKNOWN`.",
            "- Differential voltage cumulative landmarks, post-BJ2 anchor arithmetic, required L1-zero proxy, strict L1 re-crossing and early-stop reason, raw hashes and new-run metadata hashes were independently checked.",
            "",
            "Adversarial probes covered no-op parameterization, wrong-branch routing, weak-oracle disagreement, half-open window boundaries, stale raw artifacts and the scientific overclaim ceiling.",
            "",
            "Residual uncertainty: no timestep convergence or scientific mechanism interpretation was performed; phase navigation thresholds remain mechanical diagnostics, not event/SFQ counts.",
            "",
        ]),
        encoding="utf-8",
    )
    print(json.dumps({"status": result["status"], "cases_checked": len(traces), "raw_hashes_unique": result["raw_hashes_unique"], "window_counts": result["window_counts"], "failures": failures[:20], "scientific_analysis_performed": False}, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
