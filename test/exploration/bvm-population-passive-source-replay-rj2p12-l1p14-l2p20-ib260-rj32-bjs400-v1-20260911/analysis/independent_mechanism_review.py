#!/usr/bin/env python3
"""Independent stdlib-only review of topology, fidelity, hashes and raw navigation."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import re
import subprocess
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
PASSIVE = ("PASSIVE_N2_0011", "PASSIVE_N3_0111", "PASSIVE_N4_1111")
REPLAY = ("REPLAY_N2_0011_RJ2P12", "REPLAY_N3_0111_RJ2P12", "REPLAY_N4_1111_RJ2P12")
REFERENCES = ("ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_0011", "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_0111", "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_1111")
SOLVER_SHA256 = "48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2"
PAIR_RE = re.compile(r"([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)[pP]\s+([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)")
PHASE_THRESHOLD = 0.5
ACTIVITY_THRESHOLD = 1.0e-5


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def active_lines(path: Path) -> list[str]:
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip() and not line.lstrip().startswith(("*", ".", "+"))]


def read_raw(path: Path, required: tuple[str, ...]) -> tuple[list[float], dict[str, list[float]]]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.reader(stream)
        header = next(reader)
        if len(header) != len(set(header)):
            raise RuntimeError(f"duplicate raw header: {path}")
        pos = {name: index for index, name in enumerate(header)}
        if "time" not in pos or any(name not in pos for name in required):
            raise RuntimeError(f"required raw label missing: {path}")
        times: list[float] = []
        values = {name: [] for name in required}
        for row in reader:
            if len(row) != len(header):
                raise RuntimeError(f"raw row width mismatch: {path}")
            times.append(float(row[pos["time"]]) * 1.0e12)
            for name in required:
                values[name].append(float(row[pos[name]]))
    if len(times) != 1999 or times[0] != 0.0 or times[-1] != 199.9:
        raise RuntimeError(f"raw grid mismatch: {path}")
    if any(right <= left for left, right in zip(times, times[1:])):
        raise RuntimeError(f"raw grid not increasing: {path}")
    return times, values


def snapshot_pairs(path: Path) -> list[tuple[Decimal, Decimal]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return [(Decimal(row["time_s"]), Decimal(row["current_A"])) for row in csv.DictReader(stream)]


def deck_pairs(path: Path) -> list[tuple[Decimal, Decimal]]:
    text = path.read_text(encoding="utf-8")
    start = text.index("pwl(") + 4
    end = text.index(")", start)
    return [(Decimal(t) * Decimal("1e-12"), Decimal(i)) for t, i in PAIR_RE.findall(text[start:end])]


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


def first_activity(times: list[float], values: list[float]) -> float | None:
    return next((time for time, value in zip(times, values) if 110.0 <= time < 200.0 and abs(value) >= ACTIVITY_THRESHOLD), None)


def phase_landmark(times: list[float], values: list[float]) -> float | None:
    continuous = unwrap(values)
    base = next(index for index, time in enumerate(times) if time >= 110.0)
    baseline = continuous[base]
    return next((times[index] for index in range(base, len(times)) if (continuous[index] - baseline) / (2.0 * math.pi) >= PHASE_THRESHOLD), None)


def main() -> int:
    failures: list[str] = []
    checked: dict[str, Any] = {"passive_topology": {}, "replay_fidelity": {}, "raw_hashes": {}, "response_navigation": {}, "references": {}}
    for run in PASSIVE:
        path = EXP / "runs" / run / "deck.cir"
        lines = active_lines(path)
        local_failures: list[str] = []
        if sum(line.endswith("BVM") for line in lines) != 4 or sum(line.startswith("B_JSL") for line in lines) != 8:
            local_failures.append("BVM/JSL count mismatch")
        if "B_JSL8 JSL_NODE7 0 jjmit area=5.0" not in lines:
            local_failures.append("passive JSL8 orientation/endpoint mismatch")
        if any(token in line.casefold() for line in lines for token in ("bq", "jtl", "r_term", "qbin", "qbout")):
            local_failures.append("passive QB/JTL leakage")
        checked["passive_topology"][run] = {"status": "PASS" if not local_failures else "FAIL", "failures": local_failures, "deck_sha256": sha256(path)}
        failures.extend(f"{run}: {failure}" for failure in local_failures)
    for run in REPLAY:
        path = EXP / "runs" / run / "deck.cir"
        lines = active_lines(path)
        source_case = {"REPLAY_N2_0011_RJ2P12": "PASSIVE_N2_0011", "REPLAY_N3_0111_RJ2P12": "PASSIVE_N3_0111", "REPLAY_N4_1111_RJ2P12": "PASSIVE_N4_1111"}[run]
        snapshot = EXP / "data" / f"{source_case}_JSL8_source.csv"
        expected = snapshot_pairs(snapshot)
        actual = deck_pairs(path)
        local_failures: list[str] = []
        if actual != expected:
            local_failures.append("exact Decimal PWL pairs differ")
        if sum(line == "XBQ1 QBIN QBOUT BQ" for line in lines) != 1 or sum(line.startswith("XJTL1_") and line.endswith(" jtl") for line in lines) != 6:
            local_failures.append("receiver topology count mismatch")
        if any("BVM" in line or "B_JSL" in line for line in lines):
            local_failures.append("replay contains BVM/JSL")
        if "I_REPLAY 0 QBIN pwl(" not in path.read_text(encoding="utf-8"):
            local_failures.append("replay orientation line missing")
        source_times, source_values = read_raw(EXP / "runs" / source_case / "raw.csv", ("I(B_JSL8)",))
        replay_times, replay_values = read_raw(EXP / "runs" / run / "raw.csv", ("I(I_REPLAY)", "P(BJ1|XBQ1)", "P(BJ2|XBQ1)", "V(QBOUT)", "V(JTL1_OUT)", "V(JTL2_OUT)", "V(JTL3_OUT)", "V(JTL4_OUT)", "V(JTL5_OUT)", "V(JTL6_OUT)", "I(R_TERM)"))
        source_current = source_values["I(B_JSL8)"]
        replay_current = replay_values["I(I_REPLAY)"]
        current_error = max(abs(left - right) for left, right in zip(source_current, replay_current))
        if source_times != replay_times or current_error != 0.0:
            local_failures.append(f"raw I_REPLAY differs from source: max_error={current_error}")
        navigation = {label: first_activity(replay_times, replay_values[label]) for label in ("V(QBOUT)",) + tuple(f"V(JTL{stage}_OUT)" for stage in range(1, 7)) + ("I(R_TERM)",)}
        phase = {label: phase_landmark(replay_times, replay_values[label]) for label in ("P(BJ1|XBQ1)", "P(BJ2|XBQ1)")}
        checked["replay_fidelity"][run] = {"status": "PASS" if not local_failures else "FAIL", "failures": local_failures, "deck_sha256": sha256(path), "pwl_pair_count": len(actual), "source_case": source_case, "raw_replay_current_max_abs_error_A": current_error, "no_transformations": True}
        checked["response_navigation"][run] = {"phase_plus_0.5_turn_landmark_ps": phase, "first_activity_support_ps": navigation, "activity_threshold_native": ACTIVITY_THRESHOLD, "semantic_role": "navigation only; not an event count"}
        failures.extend(f"{run}: {failure}" for failure in local_failures)
    for run in REFERENCES:
        directory = EXP / "references/closed_loop_rj2p12" / run
        local_failures: list[str] = []
        metadata = json.loads((directory / "metadata.json").read_text(encoding="utf-8"))
        for name in ("deck.cir", "raw.csv", "metadata.json", "run.log"):
            path = directory / name
            recorded = metadata.get("artifacts", {}).get(name.removesuffix(".json").removesuffix(".csv").removesuffix(".cir").removesuffix(".log"), {})
            if not path.is_file():
                local_failures.append(f"missing {name}")
            if name == "raw.csv":
                read_raw(path, ("I(B_JSL8)", "P(BJ1|XBQ1)", "P(BJ2|XBQ1)", "V(QBOUT)", "V(JTL1_OUT)", "V(JTL2_OUT)", "V(JTL3_OUT)", "V(JTL4_OUT)", "V(JTL5_OUT)", "V(JTL6_OUT)", "I(R_TERM)"))
                if metadata.get("artifacts", {}).get("raw", {}).get("sha256") != sha256(path):
                    local_failures.append("reference raw hash changed")
            if name == "deck.cir" and "XBQ1 QBIN QBOUT BQ" not in active_lines(path):
                local_failures.append("reference is not closed-loop QB deck")
        checked["references"][run] = {"status": "PASS" if not local_failures else "FAIL", "immutable": True, "raw_sha256": sha256(directory / "raw.csv"), "deck_sha256": sha256(directory / "deck.cir"), "failures": local_failures}
        failures.extend(f"{run}: {failure}" for failure in local_failures)
    execution = json.loads((EXP / "qa/execution_summary_combined.json").read_text(encoding="utf-8"))
    expected_runs = sorted(PASSIVE + REPLAY)
    actual_runs = sorted(path.name for path in (EXP / "runs").iterdir() if path.is_dir())
    if execution.get("total_solver_solve_invocations") != 6 or execution.get("exact_total_physical_solve_count") != 6 or execution.get("unauthorized_extra_solves") != 0 or actual_runs != expected_runs:
        failures.append("execution count/run directory audit mismatch")
    if sha256(REPO / "build/josim-cli") != SOLVER_SHA256:
        failures.append("solver hash changed")
    raw_qa = json.loads((EXP / "qa/raw_qa.json").read_text(encoding="utf-8"))
    for run, record in raw_qa.get("runs", {}).items():
        path = REPO / record["path"]
        if path.is_file() and sha256(path) != record.get("sha256"):
            failures.append(f"QA raw hash changed: {run}")
        checked["raw_hashes"][run] = {"qa_sha256": record.get("sha256"), "current_sha256": sha256(path) if path.is_file() else None, "unchanged": path.is_file() and sha256(path) == record.get("sha256")}
    record = {"schema": "bvm-population-passive-source-replay-independent-review-v1", "experiment_id": EXP.name, "created_at_local": now(), "status": "PASS" if not failures else "FAIL", "independent_from_primary_analyzer": True, "solver_sha256": SOLVER_SHA256, "exact_new_physical_solve_count": 6, "unauthorized_extra_solves": 0, "raw_immutable": True, "scientific_analysis_performed": False, "response_progression": checked["response_navigation"], "checks": checked, "failures": failures}
    output = EXP / "qa/independent_review.json"
    output.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": record["status"], "independent_from_primary_analyzer": True, "new_physical_solves": 6, "failure_count": len(failures), "scientific_analysis_performed": False}, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
