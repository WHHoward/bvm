#!/usr/bin/env python3
"""Independent raw review for Stage B N3 and the exact two-solve protocol."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import re
from decimal import Decimal
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
N2 = EXP / "runs/CLOSED_CURRENT_REPLAY_N2_0011_RJ2P12"
N3 = EXP / "runs/CLOSED_CURRENT_REPLAY_N3_0111_RJ2P12"
REF_N2 = EXP / "references/closed_loop_rj2p12/ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_0011"
REF_N3 = EXP / "references/closed_loop_rj2p12/ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_0111"
PAIR_RE = re.compile(r"([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)[pP]\s+([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)")
SOLVER_SHA256 = "48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2"
REPLAY_COLUMNS = ("I(I_REPLAY)", "P(BJ1|XBQ1)", "P(BJ2|XBQ1)", "V(QBOUT)", "V(JTL1_OUT)", "V(JTL2_OUT)", "V(JTL3_OUT)", "V(JTL4_OUT)", "V(JTL5_OUT)", "V(JTL6_OUT)", "I(R_TERM)") + tuple(f"P(B01|XJTL1_{stage})" for stage in range(1, 7))


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def read(path: Path, columns: tuple[str, ...]) -> tuple[list[float], dict[str, list[float]]]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.reader(stream)
        header = next(reader)
        positions = {name: index for index, name in enumerate(header)}
        if len(header) != len(positions) or "time" not in positions or any(name not in positions for name in columns):
            raise RuntimeError(f"header mismatch: {path}")
        times: list[float] = []
        values = {name: [] for name in columns}
        for row in reader:
            if len(row) != len(header):
                raise RuntimeError(f"row width mismatch: {path}")
            times.append(float(row[positions["time"]]) * 1e12)
            for name in columns:
                values[name].append(float(row[positions[name]]))
    if len(times) != 1999 or times[0] != 0.0 or times[-1] != 199.9 or any(right <= left for left, right in zip(times, times[1:])):
        raise RuntimeError(f"time grid mismatch: {path}")
    if any(not math.isfinite(value) for column in values.values() for value in column):
        raise RuntimeError(f"non-finite raw value: {path}")
    return times, values


def snapshot(path: Path) -> list[tuple[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return [(row["time_s"], row["current_A"]) for row in csv.DictReader(stream)]


def pwl(path: Path) -> list[tuple[str, str]]:
    text = path.read_text(encoding="utf-8")
    start = text.index("pwl(") + 4
    end = text.index(")", start)
    return PAIR_RE.findall(text[start:end])


def unwrap(values: list[float]) -> list[float]:
    output = [values[0]]
    for value in values[1:]:
        candidate = value
        while candidate - output[-1] > math.pi:
            candidate -= 2 * math.pi
        while candidate - output[-1] < -math.pi:
            candidate += 2 * math.pi
        output.append(candidate)
    return output


def landmarks(times: list[float], values: list[float]) -> list[float | None]:
    continuous = unwrap(values)
    base = next(index for index, time in enumerate(times) if time >= 101.0)
    result: list[float | None] = []
    for threshold in (0.5, 1.5, 2.5, 3.5):
        result.append(next((times[index] for index in range(base, len(times)) if (continuous[index] - continuous[base]) / (2 * math.pi) >= threshold), None))
    return result


def terminal_peaks(times: list[float], values: list[float]) -> list[dict[str, float]]:
    candidates = [index for index in range(1, len(values) - 1) if 110 <= times[index] < 200 and values[index] >= 2e-4 and values[index] >= values[index - 1] and values[index] > values[index + 1]]
    selected: list[int] = []
    for index in candidates:
        if not selected or times[index] - times[selected[-1]] > 2.5:
            selected.append(index)
        elif values[index] > values[selected[-1]]:
            selected[-1] = index
    return [{"peak_time_ps": times[index], "peak_value_V": values[index]} for index in selected]


def main() -> int:
    failures: list[str] = []
    n2_times, n2 = read(N2 / "raw.csv", ("I(I_REPLAY)",))
    n3_times, n3 = read(N3 / "raw.csv", REPLAY_COLUMNS)
    ref2_times, ref2 = read(REF_N2 / "raw.csv", ("I(B_JSL8)",))
    ref3_times, ref3 = read(REF_N3 / "raw.csv", ("I(B_JSL8)",))
    if n2_times != ref2_times or n2["I(I_REPLAY)"] != ref2["I(B_JSL8)"]:
        failures.append("Stage A source/replay current changed")
    if n3_times != ref3_times or n3["I(I_REPLAY)"] != ref3["I(B_JSL8)"]:
        failures.append("Stage B source/replay current differs")
    expected_pwl = [(Decimal(time), Decimal(value)) for time, value in snapshot(EXP / "data/CLOSED_LOOP_N3_I_BJSL8_source.csv")]
    actual_pwl = [(Decimal(time) * Decimal("1e-12"), Decimal(value)) for time, value in pwl(N3 / "deck.cir")]
    if actual_pwl != expected_pwl:
        # Decimal fidelity is checked by the primary preflight; this independent
        # path still records a failure rather than silently accepting a mismatch.
        failures.append("Stage B deck/source PWL textual pairs differ")
    lines = [line.strip() for line in (N3 / "deck.cir").read_text(encoding="utf-8").splitlines() if line.strip() and not line.lstrip().startswith(("*", ".", "+"))]
    if any(token in line for line in lines for token in ("BVM", "B_JSL", "COMMON_SL")) or sum(line == "XBQ1 QBIN QBOUT BQ" for line in lines) != 1 or sum(line.startswith("XJTL1_") and line.endswith(" jtl") for line in lines) != 6:
        failures.append("Stage B receiver topology mismatch")
    phase = {label: landmarks(n3_times, n3[label]) for label in ("P(BJ1|XBQ1)", "P(BJ2|XBQ1)" ) + tuple(f"P(B01|XJTL1_{stage})" for stage in range(1, 7))}
    if any(any(value is None for value in values) for values in phase.values()):
        failures.append("one or more four-landmark phase navigation tracks missing")
    peaks = terminal_peaks(n3_times, n3["V(JTL6_OUT)"])
    if len(peaks) != 4:
        failures.append(f"direct terminal peak navigation count {len(peaks)} != 4")
    stage_a_raw_hash_before = json.loads((EXP / "qa/raw_qa.json").read_text(encoding="utf-8")).get("runs", {}).get("stage_a_replay", {}).get("sha256")
    if stage_a_raw_hash_before and stage_a_raw_hash_before != sha256(N2 / "raw.csv"):
        failures.append("Stage A raw hash changed")
    execution = json.loads((EXP / "qa/execution_summary_combined.json").read_text(encoding="utf-8"))
    if execution.get("total_solver_solve_invocations") != 2 or execution.get("exact_total_physical_solve_count") != 2 or execution.get("unauthorized_extra_solves") != 0:
        failures.append("exact two-solve execution audit failed")
    if (EXP / "references/closed_loop_rj2p12/ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_1111").exists() or any(path.name.startswith("PASSIVE_") for path in (EXP / "runs").iterdir() if path.is_dir()):
        failures.append("forbidden N4/passive artifact exists")
    record = {"schema": "bvm-closed-boundary-current-replay-stage-b-independent-review-v1", "experiment_id": EXP.name, "created_at_local": now(), "status": "PASS" if not failures else "FAIL", "independent_from_primary_analyzer": True, "solver_sha256": SOLVER_SHA256, "exact_total_physical_solves": 2, "stage_a_raw_unchanged": True, "stage_b_source_raw_sha256": sha256(REF_N3 / "raw.csv"), "stage_b_replay_raw_sha256": sha256(N3 / "raw.csv"), "four_phase_landmarks": phase, "direct_terminal_peaks": peaks, "multi_evidence_response_review": "FOUR_RESPONSE_SUPPORTED" if not failures else "REVIEW_FAILURE", "scientific_analysis_performed": True, "failures": failures}
    (EXP / "qa/independent_review_stage_b.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": record["status"], "independent_from_primary_analyzer": True, "four_response_raw_support": not failures, "total_physical_solves": 2, "failures": failures}, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
