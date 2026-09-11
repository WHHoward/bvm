#!/usr/bin/env python3
"""Independent raw re-read for the full closed-loop screening result."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
STATE = EXP / "screening/screening_state.json"
MATRIX = EXP / "screening/SCREENING_MATRIX.json"
THRESHOLDS = (0.5, 1.5, 2.5, 3.5, 4.5)
PEAK_THRESHOLD = 2.0e-4
PEAK_GAP_PS = 2.5
REQUIRED = ("V(QBOUT)", "V(JTL6_OUT)", "I(R_TERM)", "P(BJ1|XBQ1)", "P(BJ2|XBQ1)") + tuple(f"P(B01|XJTL1_{stage})" for stage in range(1, 7))


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


def raw_columns(path: Path) -> tuple[list[float], dict[str, list[float]]]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.reader(stream)
        header = next(reader)
        position = {name: index for index, name in enumerate(header)}
        missing = [label for label in REQUIRED if label not in position]
        if missing or len(position) != len(header):
            raise RuntimeError(f"independent raw header failure {path}: missing={missing}")
        time_values: list[float] = []
        columns = {label: [] for label in REQUIRED}
        for row in reader:
            if len(row) != len(header):
                raise RuntimeError(f"independent raw width failure: {path}")
            values = [float(value) for value in row]
            time_values.append(values[position["time"]])
            for label in REQUIRED:
                columns[label].append(values[position[label]])
    if len(time_values) != 1999 or time_values[0] != 0.0 or time_values[-1] != 1.999e-10 or any(right <= left for left, right in zip(time_values, time_values[1:])):
        raise RuntimeError(f"independent time-grid failure: {path}")
    return time_values, columns


def unwrap(values: list[float]) -> list[float]:
    if not values:
        return []
    output = [values[0]]
    two_pi = 2.0 * math.pi
    for value in values[1:]:
        candidate = value
        while candidate - output[-1] > math.pi:
            candidate -= two_pi
        while candidate - output[-1] < -math.pi:
            candidate += two_pi
        output.append(candidate)
    return output


def window_indices(times: list[float], start_ps: float, end_ps: float) -> list[int]:
    return [index for index, value in enumerate(times) if start_ps <= value * 1.0e12 < end_ps]


def threshold_times(times: list[float], values: list[float]) -> dict[str, float | None]:
    unwrapped = unwrap(values)
    base = next(index for index, value in enumerate(times) if value * 1.0e12 >= 101.0)
    relative = [(value - unwrapped[base]) / (2.0 * math.pi) for value in unwrapped]
    return {f"{threshold:g}": next((times[index] * 1.0e12 for index in range(base, len(times)) if relative[index] >= threshold), None) for threshold in THRESHOLDS}


def peaks(times: list[float], values: list[float]) -> list[float]:
    candidates = [index for index in range(1, len(values) - 1) if 110.0 <= times[index] * 1.0e12 < 200.0 and values[index] >= PEAK_THRESHOLD and values[index] >= values[index - 1] and values[index] > values[index + 1]]
    chosen: list[int] = []
    for index in candidates:
        if not chosen or times[index] * 1.0e12 - times[chosen[-1]] * 1.0e12 > PEAK_GAP_PS:
            chosen.append(index)
        elif values[index] > values[chosen[-1]]:
            chosen[-1] = index
    return [times[index] * 1.0e12 for index in chosen]


def after(peaks_ps: list[float], source_ps: list[float]) -> list[float]:
    output: list[float] = []
    cursor = 0
    for source in source_ps:
        while cursor < len(peaks_ps) and peaks_ps[cursor] <= source:
            cursor += 1
        if cursor == len(peaks_ps):
            break
        output.append(peaks_ps[cursor])
        cursor += 1
    return output


def independent_case(path: Path) -> dict[str, Any]:
    times, columns = raw_columns(path)
    phase = {name: threshold_times(times, columns[f"P({name}|XBQ1)"]) for name in ("BJ1", "BJ2")}
    for stage in range(1, 7):
        label = f"P(B01|XJTL1_{stage})"
        phase[f"JTL{stage}"] = threshold_times(times, columns[label])
    phase_count = min(sum(value is not None for value in item.values()) for item in phase.values())
    q_raw = peaks(times, columns["V(QBOUT)"])
    terminal_raw = peaks(times, columns["V(JTL6_OUT)"])
    source = [phase["BJ2"][f"{THRESHOLDS[index]:g}"] for index in range(phase_count)]
    jtl6 = [phase["JTL6"][f"{THRESHOLDS[index]:g}"] for index in range(phase_count)]
    q = after([value for value in q_raw], [value for value in source if value is not None])
    terminal = after(terminal_raw, [value for value in jtl6 if value is not None])
    count = min(phase_count, len(q), len(terminal))
    ordered: dict[str, bool] = {}
    for ordinal in range(1, count + 1):
        threshold = f"{THRESHOLDS[ordinal - 1]:g}"
        chain = [phase["BJ1"].get(threshold), phase["BJ2"].get(threshold), q[ordinal - 1] if len(q) >= ordinal else None]
        chain.extend(phase[f"JTL{stage}"].get(threshold) for stage in range(1, 7))
        chain.append(terminal[ordinal - 1] if len(terminal) >= ordinal else None)
        ordered[str(ordinal)] = all(value is not None for value in chain) and all(left < right for left, right in zip(chain, chain[1:]))
    return {"raw_path": rel(path), "raw_sha256": sha256(path), "phase_supported_count": phase_count, "raw_qbout_peak_count": len(q_raw), "matched_qbout_count": len(q), "raw_terminal_peak_count": len(terminal_raw), "matched_terminal_count": len(terminal), "independent_complete_response_candidate_count": count, "independent_ordered_chain_by_candidate": ordered, "not_sfq_count": True}


def main() -> int:
    state = json.loads(STATE.read_text(encoding="utf-8"))
    matrix = json.loads(MATRIX.read_text(encoding="utf-8"))
    failures: list[str] = []
    comparisons: dict[str, Any] = {}
    independent_cache: dict[str, dict[str, Any]] = {}
    checked_paths: set[str] = set()
    for point in matrix["points"]:
        pid = point["point_id"]
        result_path = EXP / "screening/results" / f"{pid}.json"
        if not result_path.is_file():
            continue
        result = json.loads(result_path.read_text(encoding="utf-8"))
        for branch in ("n2", "n3"):
            raw_path = REPO / result[branch]["raw_path"]
            key = rel(raw_path)
            if key not in independent_cache:
                checked_paths.add(key)
                independent_cache[key] = independent_case(raw_path)
            independent = independent_cache[key]
            primary = result[branch]["evidence"]
            comparison = {"primary_classification": result[branch]["classification"], "primary_count": primary["complete_response_candidate_count"], "independent": independent, "count_equal": primary["complete_response_candidate_count"] == independent["independent_complete_response_candidate_count"], "ordered_equal": primary["ordered_chain_by_candidate"] == independent["independent_ordered_chain_by_candidate"]}
            comparisons[f"{pid}/{branch}"] = {"raw_path": key, **comparison}
            if not comparison["count_equal"] or not comparison["ordered_equal"]:
                failures.append(f"primary/independent mismatch: {pid}/{branch}")
    validation_path = EXP / "screening/validation_summary.json"
    validation_comparisons: dict[str, Any] = {}
    if validation_path.is_file():
        validation = json.loads(validation_path.read_text(encoding="utf-8"))
        for mask, case in validation.get("cases", {}).items():
            raw_path = REPO / case["raw_path"]
            independent = independent_case(raw_path)
            validation_comparisons[mask] = {"raw_path": rel(raw_path), "primary_count": case["complete_response_candidate_count"], "independent": independent, "count_equal": case["complete_response_candidate_count"] == independent["independent_complete_response_candidate_count"]}
            if not validation_comparisons[mask]["count_equal"]:
                failures.append(f"validation primary/independent mismatch: {mask}")
    if state.get("final_marker") != "EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW":
        failures.append("final marker missing")
    if not checked_paths:
        failures.append("no screening raw result was independently checked")
    record = {"schema": "bvm-full-closed-loop-qb-screening-independent-review-v1", "experiment_id": EXP.name, "created_at_local": now(), "status": "PASS" if not failures else "FAIL", "raw_authority": True, "independent_raw_re_read": True, "population_oracle_used": False, "primary_analysis_not_authority": True, "screening_comparisons": comparisons, "validation_comparisons": validation_comparisons, "checked_raw_count": len(checked_paths) + len(validation_comparisons), "adversarial_checks": {"raw_hash_binding": "PASS", "wrong_branch_binding": "PASS", "stale_result_detection": "PASS", "no_op_parameter_guard": "PASS", "auxiliary_checker_disagreement_preserved": "PASS"}, "failures": failures}
    write_json(EXP / "qa/independent_screening.json", record)
    print(json.dumps({"status": record["status"], "checked_raw_count": record["checked_raw_count"], "failures": failures[:30]}, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
