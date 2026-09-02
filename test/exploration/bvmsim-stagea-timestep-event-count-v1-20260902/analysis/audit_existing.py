#!/usr/bin/env python3
"""Audit existing BVMSim/Stage-A raw divergence without running JoSIM.

Only exact stored timestamp overlaps are compared.  The historical duplicate
V(O2) columns are selected by explicit occurrence and never collapsed.
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

from bvmtools.phase import continuous_unwrap  # noqa: E402
from bvmtools.raw import RawTrace, read_csv  # noqa: E402


HIST = REPO / "BVMSim/data_tran.csv"
M0 = REPO / "test/exploration/bvmsim-qb-strict-qualification-v1-20260902/raw/m0/run-01.csv"
S1 = REPO / "test/exploration/bvmsim-qb-strict-qualification-v1-20260902/raw/s1/run-01.csv"
WINDOW = (110.0, 170.0)
PHASE_THRESHOLD_TURNS = 0.05
VOLTAGE_FLOOR_V = 5.0e-6
VOLTAGE_RELATIVE = 0.10
PERSISTENCE = 3


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ps(value_s: float) -> float:
    return value_s * 1.0e12


def exact_overlap(a: RawTrace, b: RawTrace) -> list[tuple[int, int]]:
    b_indices = {value: index for index, value in enumerate(b.time)}
    return [(index, b_indices[value]) for index, value in enumerate(a.time) if value in b_indices]


def select(trace: RawTrace, name: str, occurrence: int | None = None) -> tuple[float, ...]:
    return trace.column(name, occurrence=occurrence)  # type: ignore[return-value]


def first_at_or_after(trace: RawTrace, left_ps: float) -> int:
    for index, value in enumerate(trace.time):
        if ps(value) >= left_ps:
            return index
    raise ValueError(f"no sample at or after {left_ps} ps in {trace.path}")


def runs(values: list[bool]) -> list[tuple[int, int]]:
    output: list[tuple[int, int]] = []
    start: int | None = None
    for index, value in enumerate(values + [False]):
        if value and start is None:
            start = index
        if not value and start is not None:
            output.append((start, index - 1))
            start = None
    return output


def pair_metrics(
    a: RawTrace,
    b: RawTrace,
    phase_name: str,
    voltage_name: str | None,
    *,
    phase_occurrence_a: int | None = None,
    phase_occurrence_b: int | None = None,
    voltage_occurrence_a: int | None = None,
    voltage_occurrence_b: int | None = None,
) -> dict[str, Any]:
    overlaps = [(ia, ib) for ia, ib in exact_overlap(a, b) if WINDOW[0] <= ps(a.time[ia]) < WINDOW[1]]
    if not overlaps:
        return {"status": "NO_EXACT_OVERLAP", "signal": phase_name}
    phase_a = select(a, phase_name, phase_occurrence_a)
    phase_b = select(b, phase_name, phase_occurrence_b)
    first_a = first_at_or_after(a, WINDOW[0])
    first_b = first_at_or_after(b, WINDOW[0])
    phase_base_a = phase_a[first_a]
    phase_base_b = phase_b[first_b]
    phase_diffs = [((phase_a[ia] - phase_base_a) - (phase_b[ib] - phase_base_b)) / (2.0 * math.pi) for ia, ib in overlaps]
    voltage_diffs: list[float] | None = None
    voltage_threshold: float | None = None
    if voltage_name is not None:
        voltage_a = select(a, voltage_name, voltage_occurrence_a)
        voltage_b = select(b, voltage_name, voltage_occurrence_b)
        voltage_diffs = [voltage_a[ia] - voltage_b[ib] for ia, ib in overlaps]
        peak = max(max(abs(voltage_a[ia]), abs(voltage_b[ib])) for ia, ib in overlaps)
        voltage_threshold = max(VOLTAGE_FLOOR_V, VOLTAGE_RELATIVE * peak)
    flags = []
    for index, phase_diff in enumerate(phase_diffs):
        phase_ok = abs(phase_diff) >= PHASE_THRESHOLD_TURNS
        voltage_ok = voltage_diffs is None or abs(voltage_diffs[index]) >= float(voltage_threshold)
        flags.append(phase_ok and voltage_ok)
    consecutive = runs(flags)
    first_run = next((item for item in consecutive if item[1] - item[0] + 1 >= PERSISTENCE), None)
    record: dict[str, Any] = {
        "status": "VALID",
        "signal": phase_name,
        "voltage_signal": voltage_name,
        "overlap_samples": len(overlaps),
        "window_ps": list(WINDOW),
        "phase_threshold_turns": PHASE_THRESHOLD_TURNS,
        "voltage_threshold_v": voltage_threshold,
        "persistence_common_samples": PERSISTENCE,
        "max_abs_phase_trajectory_difference_turns": max(map(abs, phase_diffs)),
        "first_common_time_ps": ps(a.time[overlaps[0][0]]),
        "first_meaningful_divergence_ps": ps(a.time[overlaps[first_run[0]][0]]) if first_run else None,
        "meaningful_divergence_end_ps": ps(a.time[overlaps[first_run[1]][0]]) if first_run else None,
        "meaningful_divergence_common_sample_span": (first_run[1] - first_run[0] + 1) if first_run else 0,
        "phase_difference_at_first_meaningful_turns": phase_diffs[first_run[0]] if first_run else None,
        "voltage_difference_at_first_meaningful_v": voltage_diffs[first_run[0]] if first_run and voltage_diffs is not None else None,
        "max_abs_voltage_difference_v": max(map(abs, voltage_diffs)) if voltage_diffs is not None else None,
        "meaningful": bool(first_run),
    }
    if first_run:
        record["first_meaningful_index_in_overlap"] = first_run[0]
    return record


def compare_pair(a_name: str, a: RawTrace, b_name: str, b: RawTrace) -> dict[str, Any]:
    signals: list[dict[str, Any]] = []
    definitions = [
        ("P(BJ1|XBQ1)", "V(QBOUT)", None, None, None, None),
        ("P(B01|XJTL1_1)", None, None, None, None, None),
    ]
    if a_name == "historical" and b_name == "stage_a_m0":
        definitions.append(("V(QBOUT)", "V(QBIN)", None, None, None, None))
        definitions.append(("V(O2)", None, 0, None, None, None))
        definitions.append(("V(O2)", None, 1, None, None, None))
    else:
        definitions.extend([
            ("P(BJ2|XBQ1)", "V(BJ2|XBQ1)", None, None, None, None),
            ("P(B01|XJTL1_1)", "V(B01|XJTL1_1)", None, None, None, None),
            ("P(B02|XJTL1_1)", "V(B02|XJTL1_1)", None, None, None, None),
        ])
    for phase, voltage, pa, pb, va, vb in definitions:
        if phase not in a.headers or phase not in b.headers:
            continue
        if voltage is not None and (voltage not in a.headers or voltage not in b.headers):
            voltage = None
        try:
            signals.append(pair_metrics(a, b, phase, voltage, phase_occurrence_a=pa, phase_occurrence_b=pb, voltage_occurrence_a=va, voltage_occurrence_b=vb))
        except Exception as exc:
            signals.append({"status": "ERROR", "signal": phase, "error": repr(exc)})
    meaningful = [item for item in signals if item.get("meaningful")]
    first = min(meaningful, key=lambda item: item["first_meaningful_divergence_ps"]) if meaningful else None
    return {
        "pair": f"{a_name} vs {b_name}",
        "a_path": str(a.path),
        "b_path": str(b.path),
        "a_sha256": sha256(a.path),
        "b_sha256": sha256(b.path),
        "a_qa": a.qa(),
        "b_qa": b.qa(),
        "signals": signals,
        "first_meaningful_divergence": first,
    }


def main() -> int:
    traces = {
        "historical": read_csv(HIST),
        "stage_a_m0": read_csv(M0),
        "stage_a_s1": read_csv(S1),
    }
    result = {
        "analysis": "existing_raw_exact_overlap_divergence_audit_v1",
        "new_josim_run": False,
        "raw_inputs": {name: {"path": str(trace.path), "sha256": sha256(trace.path)} for name, trace in traces.items()},
        "criteria": {
            "window_ps": list(WINDOW),
            "phase_threshold_turns": PHASE_THRESHOLD_TURNS,
            "voltage_floor_v": VOLTAGE_FLOOR_V,
            "voltage_relative_to_pair_peak": VOLTAGE_RELATIVE,
            "persistence_common_samples": PERSISTENCE,
            "matching": "exact float timestamps parsed from stored decimal tokens; no interpolation",
        },
        "pairs": [
            compare_pair("historical", traces["historical"], "stage_a_m0", traces["stage_a_m0"]),
            compare_pair("stage_a_m0", traces["stage_a_m0"], "stage_a_s1", traces["stage_a_s1"]),
        ],
    }
    out = EXP / "analysis/existing_raw_divergence.json"
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(out), "pairs": len(result["pairs"])}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
