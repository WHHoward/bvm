#!/usr/bin/env python3
"""Independent Stage A check; no import of the primary analyzer."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import re
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
REF = EXP / "references/closed_loop_rj2p12/ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_0011"
RUN = EXP / "runs/CLOSED_CURRENT_REPLAY_N2_0011_RJ2P12"
PAIR_RE = re.compile(r"([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)[pP]\s+([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)")


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
        pos = {name: index for index, name in enumerate(header)}
        if len(header) != len(pos) or "time" not in pos or any(name not in pos for name in columns):
            raise RuntimeError(f"header/probe mismatch: {path}")
        times: list[float] = []
        values = {name: [] for name in columns}
        for row in reader:
            if len(row) != len(header):
                raise RuntimeError(f"width mismatch: {path}")
            times.append(float(row[pos["time"]]) * 1e12)
            for name in columns:
                values[name].append(float(row[pos[name]]))
    if len(times) != 1999 or times[0] != 0.0 or times[-1] != 199.9 or any(right <= left for left, right in zip(times, times[1:])):
        raise RuntimeError(f"time grid mismatch: {path}")
    if any(not math.isfinite(value) for column in values.values() for value in column):
        raise RuntimeError(f"non-finite probe: {path}")
    return times, values


def source_pairs(path: Path) -> list[tuple[Decimal, Decimal]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return [(Decimal(row["time_s"]), Decimal(row["current_A"])) for row in csv.DictReader(stream)]


def deck_pairs(path: Path) -> list[tuple[Decimal, Decimal]]:
    text = path.read_text(encoding="utf-8")
    start = text.index("pwl(") + 4
    end = text.index(")", start)
    return [(Decimal(t) * Decimal("1e-12"), Decimal(value)) for t, value in PAIR_RE.findall(text[start:end])]


def unwrap(values: list[float]) -> list[float]:
    result = [values[0]]
    two_pi = 2 * math.pi
    for value in values[1:]:
        candidate = value
        while candidate - result[-1] > math.pi:
            candidate -= two_pi
        while candidate - result[-1] < -math.pi:
            candidate += two_pi
        result.append(candidate)
    return result


def first_activity(times: list[float], values: list[float]) -> float | None:
    return next((time for time, value in zip(times, values) if 110 <= time < 200 and abs(value) >= 1e-5), None)


def main() -> int:
    failures: list[str] = []
    source_times, source_values = read(REF / "raw.csv", ("I(B_JSL8)",))
    replay_columns = ("I(I_REPLAY)", "P(BJ1|XBQ1)", "P(BJ2|XBQ1)", "V(QBOUT)") + tuple(f"V(JTL{stage}_OUT)" for stage in range(1, 7)) + ("I(R_TERM)",)
    replay_times, replay_values = read(RUN / "raw.csv", replay_columns)
    expected = source_pairs(EXP / "data/CLOSED_LOOP_N2_I_BJSL8_source.csv")
    actual = deck_pairs(RUN / "deck.cir")
    if expected != actual:
        failures.append("PWL Decimal pairs differ from source snapshot")
    if source_times != replay_times or source_values["I(B_JSL8)"] != replay_values["I(I_REPLAY)"]:
        failures.append("replay raw current differs from source current")
    lines = [line.strip() for line in (RUN / "deck.cir").read_text(encoding="utf-8").splitlines() if line.strip() and not line.lstrip().startswith(("*", ".", "+"))]
    if any(token in line for line in lines for token in ("BVM", "B_JSL", "COMMON_SL")):
        failures.append("replay netlist contains source topology")
    if sum(line == "XBQ1 QBIN QBOUT BQ" for line in lines) != 1 or sum(line.startswith("XJTL1_") and line.endswith(" jtl") for line in lines) != 6:
        failures.append("receiver topology mismatch")
    navigation = {label: first_activity(replay_times, replay_values[label]) for label in ("V(QBOUT)",) + tuple(f"V(JTL{stage}_OUT)" for stage in range(1, 7)) + ("I(R_TERM)",)}
    phases = {}
    for label in ("P(BJ1|XBQ1)", "P(BJ2|XBQ1)"):
        continuous = unwrap(replay_values[label])
        base = next(index for index, time in enumerate(replay_times) if time >= 101.0)
        baseline = continuous[base]
        phases[label] = {"baseline_ps": replay_times[base], "plus_0.5_turn_ps": next((replay_times[index] for index in range(base, len(replay_times)) if (continuous[index] - baseline) / (2 * math.pi) >= 0.5), None), "semantic_role": "PHASE_NAVIGATION_ONLY"}
    metadata = json.loads((RUN / "metadata.json").read_text(encoding="utf-8"))
    if metadata.get("solver", {}).get("sha256") != "48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2" or metadata.get("artifacts", {}).get("raw", {}).get("sha256") != sha256(RUN / "raw.csv"):
        failures.append("solver/raw metadata hash mismatch")
    execution = json.loads((EXP / "qa/execution_summary.json").read_text(encoding="utf-8"))
    if execution.get("solver_solve_invocations") != 1 or execution.get("stage_b_started") is not False:
        failures.append("execution is not one-solve Stage A only")
    if (EXP / "references/closed_loop_rj2p12").joinpath("ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_0111").exists():
        failures.append("N3 source was copied before Stage A review")
    record = {"schema": "bvm-closed-boundary-current-replay-stage-a-independent-review-v1", "experiment_id": EXP.name, "created_at_local": now(), "status": "PASS" if not failures else "FAIL", "independent_from_primary_analyzer": True, "source_raw_sha256": sha256(REF / "raw.csv"), "replay_raw_sha256": sha256(RUN / "raw.csv"), "pwl_pair_count": len(actual), "exact_timestamp_value_fidelity": expected == actual, "raw_current_exact": source_values["I(B_JSL8)"] == replay_values["I(I_REPLAY)"], "receiver_topology_checked": True, "response_navigation": {"first_activity_support_ps": navigation, "phase": phases, "semantic_role": "navigation only; no response count"}, "stage_b_started": False, "scientific_analysis_performed": False, "failures": failures}
    (EXP / "qa/independent_review.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": record["status"], "independent_from_primary_analyzer": True, "stage_b_started": False, "scientific_analysis_performed": False, "failures": failures}, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
