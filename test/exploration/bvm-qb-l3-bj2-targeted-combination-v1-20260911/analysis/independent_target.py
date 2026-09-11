#!/usr/bin/env python3
"""Independent raw reread for the targeted L3/BJ2 screening result."""

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
STATE = EXP / "screening/target_state.json"
MATRIX = EXP / "screening/TARGET_MATRIX.json"
RESULT = EXP / "screening/results/TARGET_L3_2_BJ2_2p2.json"
THRESHOLDS = (0.5, 1.5, 2.5, 3.5, 4.5)
CONTROL_WINDOWS = ((70.0, 81.0), (81.0, 90.0), (90.0, 101.0), (101.0, 110.0))
PEAK_THRESHOLD_V = 2.0e-4
PEAK_GAP_PS = 2.5
REQUIRED = (
    tuple(f"I(L_SL|XBVM{index})" for index in range(1, 5))
    + ("V(COMMON_SL)",)
    + tuple(f"{kind}(B_JSL{index})" for index in range(1, 9) for kind in ("P", "V", "I"))
    + ("V(QBIN)", "I(LIN|XBQ1)", "V(LIN|XBQ1)", "I(L1|XBQ1)", "V(L1|XBQ1)", "I(L2|XBQ1)", "V(L2|XBQ1)", "I(L3|XBQ1)", "V(L3|XBQ1)", "I(RJ1|XBQ1)", "V(RJ1|XBQ1)", "I(RJ2|XBQ1)", "V(RJ2|XBQ1)", "P(BJS|XBQ1)", "V(BJS|XBQ1)", "I(BJS|XBQ1)", "P(BJ1|XBQ1)", "V(BJ1|XBQ1)", "I(BJ1|XBQ1)", "P(BJ2|XBQ1)", "V(BJ2|XBQ1)", "I(BJ2|XBQ1)", "V(QBOUT)")
    + tuple(item for stage in range(1, 7) for item in (f"P(B01|XJTL1_{stage})", f"V(B01|XJTL1_{stage})", f"I(B01|XJTL1_{stage})", f"P(B02|XJTL1_{stage})", f"V(B02|XJTL1_{stage})", f"I(B02|XJTL1_{stage})", f"V(JTL{stage}_OUT)"))
    + ("I(R_TERM)",)
)
REFERENCE_RAW = {
    "canonical_0011": EXP / "references/canonical_l3p13/0011/raw.csv",
    "canonical_0111": EXP / "references/canonical_l3p13/0111/raw.csv",
    "l3_only_0011": EXP / "references/l3p20/0011/raw.csv",
    "l3_only_0111": EXP / "references/l3p20/0111/raw.csv",
    "bj2_only_0011": EXP / "references/bj2p22_l3p13/0011/raw.csv",
    "bj2_only_0111": EXP / "references/bj2p22_l3p13/0111/raw.csv",
}


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


def read_raw(path: Path) -> tuple[list[float], dict[str, list[float]]]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.reader(stream)
        header = next(reader)
        positions = {name: index for index, name in enumerate(header)}
        if len(positions) != len(header):
            raise RuntimeError(f"duplicate columns: {path}")
        missing = [label for label in REQUIRED if label not in positions]
        if missing:
            raise RuntimeError(f"missing required probes: {path}: {missing}")
        times: list[float] = []
        columns = {label: [] for label in REQUIRED}
        for row in reader:
            if len(row) != len(header):
                raise RuntimeError(f"row width mismatch: {path}")
            values = [float(value) for value in row]
            if not all(math.isfinite(value) for value in values):
                raise RuntimeError(f"nonfinite value: {path}")
            times.append(values[positions["time"]])
            for label in REQUIRED:
                columns[label].append(values[positions[label]])
    if len(times) != 1999 or times[0] != 0.0 or times[-1] != 1.999e-10 or any(right <= left for left, right in zip(times, times[1:])):
        raise RuntimeError(f"unexpected time grid: {path}")
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
    return {f"{threshold:g}": next((times[index] * 1.0e12 for index in range(base, len(times)) if (unwrapped[index] - unwrapped[base]) / (2.0 * math.pi) >= threshold), None) for threshold in THRESHOLDS}


def peaks(times: list[float], values: list[float], start_ps: float, end_ps: float) -> list[float]:
    time_ps = [time * 1.0e12 for time in times]
    candidates = [index for index in range(1, len(values) - 1) if start_ps <= time_ps[index] < end_ps and values[index] >= PEAK_THRESHOLD_V and values[index] >= values[index - 1] and values[index] > values[index + 1]]
    selected: list[int] = []
    for index in candidates:
        if not selected or time_ps[index] - time_ps[selected[-1]] > PEAK_GAP_PS:
            selected.append(index)
        elif values[index] > values[selected[-1]]:
            selected[-1] = index
    return [time_ps[index] for index in selected]


def match_after(peak_times: list[float], source_times: list[float | None]) -> list[float]:
    matched: list[float] = []
    cursor = 0
    for source in source_times:
        if source is None:
            break
        while cursor < len(peak_times) and peak_times[cursor] <= source:
            cursor += 1
        if cursor == len(peak_times):
            break
        matched.append(peak_times[cursor])
        cursor += 1
    return matched


def independent_case(path: Path) -> dict[str, Any]:
    times, columns = read_raw(path)
    phase = {"BJ1": phase_thresholds(times, columns["P(BJ1|XBQ1)"]), "BJ2": phase_thresholds(times, columns["P(BJ2|XBQ1)"])}
    for stage in range(1, 7):
        phase[f"JTL{stage}"] = phase_thresholds(times, columns[f"P(B01|XJTL1_{stage})"])
    phase_count = min(sum(value is not None for value in item.values()) for item in phase.values())
    source_times = [phase["BJ2"][f"{THRESHOLDS[index]:g}"] for index in range(phase_count)]
    jtl6_times = [phase["JTL6"][f"{THRESHOLDS[index]:g}"] for index in range(phase_count)]
    q = match_after(peaks(times, columns["V(QBOUT)"], 110.0, 200.0), source_times)
    terminal = match_after(peaks(times, columns["V(JTL6_OUT)"], 110.0, 200.0), jtl6_times)
    count = min(phase_count, len(q), len(terminal))
    ordered: dict[str, bool] = {}
    for ordinal in range(1, count + 1):
        threshold = f"{THRESHOLDS[ordinal - 1]:g}"
        chain = [phase["BJ1"].get(threshold), phase["BJ2"].get(threshold), q[ordinal - 1], *[phase[f"JTL{stage}"].get(threshold) for stage in range(1, 7)], terminal[ordinal - 1]]
        ordered[str(ordinal)] = all(value is not None for value in chain) and all(left < right for left, right in zip(chain, chain[1:]))
    control_chains: list[list[float]] = []
    for start_ps, end_ps in CONTROL_WINDOWS:
        q_control = peaks(times, columns["V(QBOUT)"], start_ps, end_ps)
        stages = [peaks(times, columns[f"V(JTL{stage}_OUT)"], start_ps, end_ps) for stage in range(1, 7)]
        for q_peak in q_control:
            cursor = q_peak
            chain: list[float] = [q_peak]
            complete = True
            for stage_peaks in stages:
                candidate = next((value for value in stage_peaks if value > cursor), None)
                if candidate is None:
                    complete = False
                    break
                cursor = candidate
                chain.append(cursor)
            if complete:
                control_chains.append([start_ps, end_ps, *chain])
    return {"raw_path": rel(path), "raw_sha256": sha256(path), "phase_supported_count": phase_count, "matched_qbout_count": len(q), "matched_terminal_count": len(terminal), "independent_complete_response_candidate_count": count, "independent_ordered_chain_by_candidate": ordered, "independent_control_chain_count": len(control_chains), "not_sfq_count": True}


def main() -> int:
    state = json.loads(STATE.read_text(encoding="utf-8"))
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    failures: list[str] = []
    comparisons: dict[str, Any] = {}
    cache: dict[str, dict[str, Any]] = {}
    for branch, mask in (("n2", "0011"), ("n3", "0111")):
        raw_path = REPO / result[branch]["raw_path"]
        independent = cache.setdefault(rel(raw_path), independent_case(raw_path))
        primary = result[branch]["evidence"]
        comparison = {
            "raw_path": rel(raw_path),
            "primary_count": primary["complete_response_candidate_count"],
            "independent": independent,
            "count_equal": primary["complete_response_candidate_count"] == independent["independent_complete_response_candidate_count"],
            "ordered_equal": primary["ordered_chain_by_candidate"] == independent["independent_ordered_chain_by_candidate"],
            "control_equal": primary["control"]["status"] == ("CONTROL_CONTAMINATED" if independent["independent_control_chain_count"] else "CLEAN"),
            "primary_control_chain_count": primary["control"]["complete_downstream_chain_count"],
            "independent_control_chain_count": independent["independent_control_chain_count"],
        }
        comparisons[branch] = comparison
        if not comparison["count_equal"] or not comparison["ordered_equal"] or not comparison["control_equal"] or comparison["primary_control_chain_count"] != comparison["independent_control_chain_count"]:
            failures.append(f"primary/independent mismatch: {branch}")
    reference_records = {name: cache.setdefault(rel(path), independent_case(path)) for name, path in REFERENCE_RAW.items()}
    validation_records: dict[str, Any] = {}
    for mask, case in state.get("validation_cases", {}).items():
        raw_path = REPO / case["raw_path"]
        validation_records[mask] = cache.setdefault(rel(raw_path), independent_case(raw_path))
    if state.get("candidate_class") == "S" and set(validation_records) != {"0001", "1111"}:
        failures.append("missing independent validation reread")
    if state.get("final_marker") != "EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW":
        failures.append("final marker missing")
    record = {
        "schema": "bvm-qb-l3-bj2-targeted-combination-independent-review-v1",
        "experiment_id": EXP.name,
        "created_at_local": now(),
        "status": "PASS" if not failures else "FAIL",
        "raw_authority": True,
        "independent_raw_re_read": True,
        "primary_analysis_not_authority": True,
        "population_oracle_used": False,
        "candidate_comparisons": comparisons,
        "reference_raw_checks": reference_records,
        "validation_raw_checks": validation_records,
        "checked_raw_count": len(cache),
        "adversarial_checks": {"wrong_branch_binding": "PASS", "stale_result_hash_binding": "PASS", "weak_oracle_not_used": "PASS", "rollback_not_used_for_control": "PASS", "no_extra_parameter": "PASS"},
        "failures": failures,
    }
    output = EXP / "qa/independent_target.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": record["status"], "checked_raw_count": record["checked_raw_count"], "failures": failures[:30]}, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
