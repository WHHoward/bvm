#!/usr/bin/env python3
"""Record descriptive replay pulse/propagation observations without counting events."""

from __future__ import annotations

import csv
import hashlib
import json
import math
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
BASELINE = REPO / "test/exploration/bvmsim-jm2-passive-capture-replay-v1-20260907"
PHI0 = Decimal("2.067833848e-15")
TAU = Decimal("6.2831853071795864769252867665590057683943387987502")
RAW = {"N1_REPLAY": BASELINE / "runs/replay_array/raw.csv", **{f"N{n}_REPLAY": EXP / "runs" / f"n{n}_replay/raw.csv" for n in (2, 3, 4)}}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def now_local() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def write_once(path: Path, content: str) -> None:
    if path.exists():
        if path.read_text(encoding="utf-8") == content:
            return
        raise RuntimeError(f"refusing to overwrite existing artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def load(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def response(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return [row for row in rows if 110 <= float(row["time"]) * 1e12 < 200]


def local_positive_peaks(rows: list[dict[str, str]], label: str, threshold: float = 5e-6, merge_ps: float = 1.0) -> list[dict[str, float]]:
    candidates: list[tuple[float, float]] = []
    values = [float(row[label]) for row in rows]
    times = [float(row["time"]) * 1e12 for row in rows]
    for index in range(1, len(rows) - 1):
        if values[index] > threshold and values[index] > values[index - 1] and values[index] >= values[index + 1]:
            candidates.append((times[index], values[index]))
    merged: list[tuple[float, float]] = []
    for candidate in candidates:
        if not merged or candidate[0] - merged[-1][0] > merge_ps:
            merged.append(candidate)
        elif candidate[1] > merged[-1][1]:
            merged[-1] = candidate
    return [{"time_ps": time, "current_uA": current * 1e6} for time, current in merged]


def phase_delta(rows: list[dict[str, str]], label: str) -> tuple[float, float]:
    raw = [float(row[label]) for row in rows]
    if not raw:
        raise RuntimeError(label)
    unwrapped = [raw[0]]
    for previous, current in zip(raw, raw[1:]):
        delta = current - previous
        while delta > math.pi:
            delta -= 2 * math.pi
        while delta < -math.pi:
            delta += 2 * math.pi
        unwrapped.append(unwrapped[-1] + delta)
    delta = unwrapped[-1] - unwrapped[0]
    return delta, delta / (2 * math.pi)


def area_phi0(rows: list[dict[str, str]], current_label: str, multiplier_ohm: Decimal = Decimal("10")) -> float:
    area = Decimal("0")
    for left, right in zip(rows, rows[1:]):
        dt = Decimal(right["time"]) - Decimal(left["time"])
        area += (Decimal(left[current_label]) + Decimal(right[current_label])) * dt / Decimal("2") * multiplier_ohm
    return float(area / PHI0)


def stage_peak_times(rows: list[dict[str, str]]) -> dict[str, float]:
    result: dict[str, float] = {}
    for stage in range(1, 7):
        label = f"V(B01|XJTL1_{stage})"
        chosen = max(rows, key=lambda row: abs(float(row[label])))
        result[str(stage)] = float(chosen["time"]) * 1e12
    return result


def main() -> int:
    records: dict[str, object] = {}
    failures: list[str] = []
    raw_hashes = {name: sha256(path) for name, path in RAW.items()}
    for name, path in RAW.items():
        rows = response(load(path))
        peaks = local_positive_peaks(rows, "I(R_TERM)")
        jtl6_rad, jtl6_turns = phase_delta(rows, "P(B01|XJTL1_6)")
        bj2_rad, bj2_turns = phase_delta(rows, "P(BJ2|XBQ1)")
        times = stage_peak_times(rows)
        monotonic_stages = all(times[str(i)] <= times[str(i + 1)] for i in range(1, 6))
        term_area = area_phi0(rows, "I(R_TERM)")
        if name == "N1_REPLAY":
            shape = "one-pulse-like terminal response (descriptive only)"
        elif name in ("N2_REPLAY", "N3_REPLAY"):
            shape = "multiple-pulse-like terminal response with separated peak-like maxima (descriptive only)"
        else:
            shape = "other: terminal response remains near a three-response trajectory despite N=4 input; saturation-like/partial interpretation unresolved"
        records[name] = {
            "raw_sha256": raw_hashes[name],
            "window": "FINAL_READ_RESPONSE [110 ps, 200 ps)",
            "terminal_peak_probe": {
                "threshold_uA": 5.0,
                "merge_separation_ps": 1.0,
                "peak_like_maxima": peaks,
                "note": "local-maxima activity probe for shape description; not an SFQ/event count",
            },
            "jtl_stage_voltage_peak_time_ps": times,
            "stage_peak_time_sequence_monotonic": monotonic_stages,
            "jtl6_net_phase_displacement_rad": jtl6_rad,
            "jtl6_net_phase_displacement_turns": jtl6_turns,
            "bj2_net_phase_displacement_rad": bj2_rad,
            "bj2_net_phase_displacement_turns": bj2_turns,
            "terminal_area_over_phi0": term_area,
            "shape_classification": shape,
            "transmitted_sfq_assessment": {
                "disposition": "INCONCLUSIVE",
                "same_jj_phase_area_observation_available": True,
                "causal_stage_timing_observation_available": monotonic_stages,
                "terminal_peak_observation_available": bool(peaks),
                "discrete_phase_slip_progression_verified": False,
                "reason": "the exploration has no frozen discrete-segmentation tolerance or convergence result; joint observables remain descriptive and are not promoted to an event count",
            },
        }
    record = {
        "schema": "jm2-read-count-replay-event-observation-v1",
        "experiment_id": EXP.name,
        "created_at_local": now_local(),
        "status": "PASS" if not failures else "FAIL",
        "raw_immutable": True,
        "raw_hashes_before": raw_hashes,
        "raw_hashes_after": {name: sha256(path) for name, path in RAW.items()},
        "records": records,
        "limitations": [
            "Peak-like terminal maxima use a declared 5 uA descriptive activity probe and are not event counts.",
            "Net phase displacement is continuous unwrapped rad/(2*pi) and is not an SFQ count.",
            "No timestep convergence or parameter sensitivity run was performed.",
        ],
        "failures": failures,
    }
    if record["raw_hashes_before"] != record["raw_hashes_after"]:
        record["status"] = "FAIL"
        record["failures"].append("raw hash changed during event observation")
    write_once(EXP / "analysis/event_observation.json", json.dumps(record, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"status": record["status"], "record": "analysis/event_observation.json", "failures": record["failures"]}, ensure_ascii=False))
    return 0 if record["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
