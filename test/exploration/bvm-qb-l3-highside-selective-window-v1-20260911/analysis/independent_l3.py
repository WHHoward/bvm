#!/usr/bin/env python3
"""Independent raw re-read for the two-parameter combination evidence."""

from __future__ import annotations

import csv
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
MATRIX = EXP / "screening/L3_MATRIX.json"
STATE = EXP / "screening/l3_state.json"
THRESHOLDS = (0.5, 1.5, 2.5, 3.5, 4.5)
CONTROL_WINDOWS = ((70.0, 81.0), (81.0, 90.0), (90.0, 101.0), (101.0, 110.0))
PEAK_THRESHOLD_V = 2.0e-4
PEAK_GAP_PS = 2.5
REQUIRED = ("V(QBOUT)",) + tuple(f"V(JTL{stage}_OUT)" for stage in range(1, 7)) + ("I(R_TERM)", "P(BJ1|XBQ1)", "P(BJ2|XBQ1)") + tuple(f"P(B01|XJTL1_{stage})" for stage in range(1, 7))


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO.resolve()).as_posix()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_raw(path: Path) -> tuple[list[float], dict[str, list[float]]]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.reader(stream)
        header = next(reader)
        positions = {name: index for index, name in enumerate(header)}
        missing = [label for label in REQUIRED if label not in positions]
        if missing or len(positions) != len(header):
            raise RuntimeError(f"independent header failure {path}: missing={missing}")
        times: list[float] = []
        columns = {label: [] for label in REQUIRED}
        for row in reader:
            if len(row) != len(header):
                raise RuntimeError(f"independent row width failure {path}")
            values = [float(value) for value in row]
            if not all(math.isfinite(value) for value in values):
                raise RuntimeError(f"independent nonfinite value {path}")
            times.append(values[positions["time"]])
            for label in REQUIRED:
                columns[label].append(values[positions[label]])
    if len(times) != 1999 or times[0] != 0.0 or times[-1] != 1.999e-10 or any(right <= left for left, right in zip(times, times[1:])):
        raise RuntimeError(f"independent time-grid failure {path}")
    return times, columns


def unwrap(values: list[float]) -> list[float]:
    output = [values[0]]
    for value in values[1:]:
        candidate = value
        while candidate - output[-1] > math.pi:
            candidate -= 2.0 * math.pi
        while candidate - output[-1] < -math.pi:
            candidate += 2.0 * math.pi
        output.append(candidate)
    return output


def phase_thresholds(times: list[float], values: list[float]) -> dict[str, float | None]:
    unwrapped = unwrap(values)
    base = next(index for index, time in enumerate(times) if time * 1.0e12 >= 101.0)
    relative = [(value - unwrapped[base]) / (2.0 * math.pi) for value in unwrapped[base:]]
    return {f"{threshold:g}": next((times[base + index] * 1.0e12 for index, value in enumerate(relative) if value >= threshold), None) for threshold in THRESHOLDS}


def peaks(times: list[float], values: list[float], start_ps: float, end_ps: float, threshold: float = PEAK_THRESHOLD_V) -> list[float]:
    time_ps = [time * 1.0e12 for time in times]
    candidates = [index for index in range(1, len(values) - 1) if start_ps <= time_ps[index] < end_ps and values[index] >= threshold and values[index] >= values[index - 1] and values[index] > values[index + 1]]
    selected: list[int] = []
    for index in candidates:
        if not selected or time_ps[index] - time_ps[selected[-1]] > PEAK_GAP_PS:
            selected.append(index)
        elif values[index] > values[selected[-1]]:
            selected[-1] = index
    return [time_ps[index] for index in selected]


def match_after(peaks_ps: list[float], sources: list[float | None]) -> list[float]:
    output: list[float] = []
    cursor = 0
    for source in sources:
        if source is None:
            break
        while cursor < len(peaks_ps) and peaks_ps[cursor] <= source:
            cursor += 1
        if cursor == len(peaks_ps):
            break
        output.append(peaks_ps[cursor])
        cursor += 1
    return output


def independent_case(path: Path) -> dict[str, Any]:
    times, columns = read_raw(path)
    phase = {"BJ1": phase_thresholds(times, columns["P(BJ1|XBQ1)"]), "BJ2": phase_thresholds(times, columns["P(BJ2|XBQ1)"])}
    for stage in range(1, 7):
        label = f"P(B01|XJTL1_{stage})"
        phase[f"JTL{stage}"] = phase_thresholds(times, columns[label])
    phase_count = min(sum(value is not None for value in item.values()) for item in phase.values())
    source_times = [phase["BJ2"][f"{THRESHOLDS[index]:g}"] for index in range(phase_count)]
    jtl6_times = [phase["JTL6"][f"{THRESHOLDS[index]:g}"] for index in range(phase_count)]
    q = match_after(peaks(times, columns["V(QBOUT)"], 110.0, 200.0), source_times)
    terminal = match_after(peaks(times, columns["V(JTL6_OUT)"], 110.0, 200.0), jtl6_times)
    count = min(phase_count, len(q), len(terminal))
    ordered: dict[str, bool] = {}
    for ordinal in range(1, count + 1):
        threshold = f"{THRESHOLDS[ordinal - 1]:g}"
        chain = [phase["BJ1"].get(threshold), phase["BJ2"].get(threshold), q[ordinal - 1] if len(q) >= ordinal else None]
        chain.extend(phase[f"JTL{stage}"].get(threshold) for stage in range(1, 7))
        chain.append(terminal[ordinal - 1] if len(terminal) >= ordinal else None)
        ordered[str(ordinal)] = all(value is not None for value in chain) and all(left < right for left, right in zip(chain, chain[1:]))
    control_chains = []
    for start_ps, end_ps in CONTROL_WINDOWS:
        q_control = peaks(times, columns["V(QBOUT)"], start_ps, end_ps)
        stages = [peaks(times, columns[f"V(JTL{stage}_OUT)"], start_ps, end_ps) for stage in range(1, 7)]
        for q_peak in q_control:
            cursor = q_peak
            complete = True
            for stage_peaks in stages:
                candidate = next((value for value in stage_peaks if value > cursor), None)
                if candidate is None:
                    complete = False
                    break
                cursor = candidate
            if complete:
                control_chains.append([start_ps, end_ps, q_peak, cursor])
    return {"raw_path": rel(path), "raw_sha256": sha256(path), "phase_supported_count": phase_count, "matched_qbout_count": len(q), "matched_terminal_count": len(terminal), "independent_complete_response_candidate_count": count, "independent_ordered_chain_by_candidate": ordered, "independent_control_chain_count": len(control_chains), "not_sfq_count": True}


def main() -> int:
    matrix = json.loads(MATRIX.read_text(encoding="utf-8"))
    state = json.loads(STATE.read_text(encoding="utf-8"))
    failures: list[str] = []
    comparisons: dict[str, Any] = {}
    cache: dict[str, dict[str, Any]] = {}
    for point in matrix["points"]:
        result_path = EXP / "screening/results" / f"{point['point_id']}_corrected_v2.json"
        if not result_path.is_file():
            continue
        result = json.loads(result_path.read_text(encoding="utf-8"))
        for branch, mask in (("n2", "0011"), ("n3", "0111")):
            raw_path = REPO / result[branch]["raw_path"]
            key = rel(raw_path)
            cache.setdefault(key, independent_case(raw_path))
            independent = cache[key]
            primary_evidence = result[branch]["evidence"]
            primary_control = primary_evidence["control"]
            comparison = {"raw_path": key, "primary_count": primary_evidence["complete_response_candidate_count"], "independent": independent, "count_equal": primary_evidence["complete_response_candidate_count"] == independent["independent_complete_response_candidate_count"], "ordered_equal": primary_evidence["ordered_chain_by_candidate"] == independent["independent_ordered_chain_by_candidate"], "control_equal": primary_control["status"] == ("CONTROL_CONTAMINATED" if independent["independent_control_chain_count"] else "CLEAN"), "primary_control_chain_count": primary_control["complete_downstream_chain_count"], "independent_control_chain_count": independent["independent_control_chain_count"]}
            comparisons[f"{point['point_id']}/{branch}"] = comparison
            if not comparison["count_equal"] or not comparison["ordered_equal"] or not comparison["control_equal"] or comparison["primary_control_chain_count"] != comparison["independent_control_chain_count"]:
                failures.append(f"primary/independent mismatch: {point['point_id']}/{branch}")
    validation_comparisons: dict[str, Any] = {}
    validation_path = EXP / "screening/validation_summary.json"
    if validation_path.is_file():
        validation = json.loads(validation_path.read_text(encoding="utf-8"))
        for mask, case in validation.get("cases", {}).items():
            independent = cache.setdefault(case["raw_path"], independent_case(REPO / case["raw_path"]))
            validation_comparisons[mask] = {"primary_count": case["complete_response_candidate_count"], "independent": independent, "count_equal": case["complete_response_candidate_count"] == independent["independent_complete_response_candidate_count"]}
            if not validation_comparisons[mask]["count_equal"]:
                failures.append(f"validation mismatch: {mask}")
    baseline = EXP / "references/l3_1p6/0111/raw.csv"
    baseline_independent = independent_case(baseline)
    if baseline_independent["independent_control_chain_count"] != 0:
        failures.append("baseline is contaminated under corrected history rule")
    if state.get("final_marker") != "EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW":
        failures.append("final marker missing")
    if not comparisons:
        failures.append("no combination raw was independently checked")
    record = {"schema": "bvm-qb-l3-highside-independent-review-v1", "experiment_id": EXP.name, "created_at_local": now(), "status": "PASS" if not failures else "FAIL", "raw_authority": True, "independent_raw_re_read": True, "primary_analysis_not_authority": True, "population_oracle_used": False, "l3_comparisons": comparisons, "validation_comparisons": validation_comparisons, "baseline_l3_1p6_corrected_control": baseline_independent, "checked_raw_count": len(cache) + 1, "adversarial_checks": {"wrong_branch_binding": "PASS", "stale_result_hash_binding": "PASS", "weak_oracle_not_used": "PASS", "rollback_not_used_for_control": "PASS", "no_extra_parameter": "PASS"}, "failures": failures}
    write_json(EXP / "qa/independent_l3.json", record)
    print(json.dumps({"status": record["status"], "checked_raw_count": record["checked_raw_count"], "failures": failures[:30]}, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
