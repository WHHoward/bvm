#!/usr/bin/env python3
"""Independent raw-only arithmetic cross-check for the four-condition result.

This script deliberately does not read metrics.json or REPORT.md.  It uses
the shared raw/phase/waveform primitives, but recomputes the crossover
anchors, BJ2 phase/area facts, and LIN-minus-sum(LSL) closure directly from
the four raw CSVs.
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
from bvmtools.compare import exact_time_grid_identity  # noqa: E402
from bvmtools.kcl import linear_kcl_residual  # noqa: E402
from bvmtools.phase import TAU, continuous_unwrap  # noqa: E402
from bvmtools.raw import read_csv  # noqa: E402
from bvmtools.waveform import trapezoid_integral  # noqa: E402
from bvmtools.sfq import PHI0  # noqa: E402


RAW = {
    "O+": REPO / "test/exploration/bvmsim-4bvm-jm2-connected-state-position-ab-v1-20260903/runs/1111/raw.csv",
    "O-": EXP / "runs/OLD-NO-HISTORY/raw.csv",
    "N-": REPO / "test/exploration/bvmsim-4bvm-allone-selective-read-additivity-isolation-v1-20260904/runs/1111/raw.csv",
    "N+": EXP / "runs/NEW-WITH-HISTORY/raw.csv",
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def indices(trace, start_ps: float, end_ps: float) -> list[int]:
    return [index for index, value in enumerate(trace.time) if start_ps <= value * 1e12 < end_ps]


def rms(values: list[float]) -> float:
    return math.sqrt(sum(value * value for value in values) / len(values))


def phase_area(trace, start_ps: float, end_ps: float) -> float:
    selected = indices(trace, start_ps, end_ps)
    area = trapezoid_integral([trace.column("V(BJ2|XBQ1)")[index] for index in selected], [trace.time[index] for index in selected])
    return area / PHI0


def crossing_times(trace, start_ps: float, end_ps: float) -> list[float]:
    selected = indices(trace, start_ps, end_ps)
    phase = continuous_unwrap(trace.column("P(BJ2|XBQ1)"))
    baseline = phase[selected[0]]
    result: list[float] = []
    for number in range(1, 8):
        target = baseline + number * TAU
        found = next((index for index in selected if phase[index] >= target), None)
        if found is None:
            break
        result.append(trace.time[found] * 1e12)
    return result


def main() -> int:
    traces = {name: read_csv(path) for name, path in RAW.items()}
    base = traces["O+"].time
    if not all(exact_time_grid_identity(base, trace.time) for trace in traces.values()):
        raise AssertionError("time grids are not exactly identical")
    common = [name for name in traces["O+"].headers if name != "time" and all(name in traces[c].headers for c in traces)]
    pre = indices(traces["O+"], 45.0, 70.0)
    pre_parity = {}
    for left_name, right_name in (("O+", "O-"), ("N+", "N-")):
        unequal = [signal for signal in common if any(traces[left_name].column(signal)[i] != traces[right_name].column(signal)[i] for i in pre)]
        pre_parity[f"{left_name}_vs_{right_name}"] = {"common_probe_count": len(common), "sample_count": len(pre), "all_exact": not unequal, "unequal_signals": unequal[:10]}
    exact_pairs = {}
    for left_name, right_name in (("O+", "N+"), ("O-", "N-")):
        unequal = [signal for signal in common if any(a != b for a, b in zip(traces[left_name].column(signal), traces[right_name].column(signal)))]
        exact_pairs[f"{left_name}_vs_{right_name}"] = {"all_common_samples_exact": not unequal, "unequal_signals": unequal[:10]}
    context_nonzero = {}
    for left_name, right_name in (("O+", "O-"), ("N+", "N-")):
        differences = [abs(a - b) for signal in common for a, b in zip(traces[left_name].column(signal), traces[right_name].column(signal))]
        context_nonzero[f"{left_name}_vs_{right_name}"] = {"max_abs_native": max(differences), "nonzero_sample_count": sum(value != 0.0 for value in differences)}
    trajectory = {}
    for condition, trace in traces.items():
        selected = indices(trace, 110.0, 170.0)
        phase = continuous_unwrap(trace.column("P(BJ2|XBQ1)"))
        trajectory[condition] = {"endpoint_delta_turns": (phase[selected[-1]] - phase[selected[0]]) / TAU, "voltage_area_over_phi0_turns": phase_area(trace, 110.0, 170.0), "crossing_markers_ps": crossing_times(trace, 110.0, 170.0)}
    closure = {}
    for condition, trace in traces.items():
        branches = {"LIN": trace.column("I(LIN|XBQ1)")}
        branches.update({f"LSL{number}": trace.column(f"I(L_SL|XBVM{number})") for number in range(1, 5)})
        residual = linear_kcl_residual(branches, {"LIN": 1.0, "LSL1": -1.0, "LSL2": -1.0, "LSL3": -1.0, "LSL4": -1.0})
        selected = indices(trace, 110.0, 160.0)
        values = [residual[index] for index in selected]
        closure[condition] = {"max_abs_uA": max(abs(value) for value in values) * 1e6, "rms_uA": rms(values) * 1e6, "signed_integral_uA_ps": trapezoid_integral(values, [trace.time[index] for index in selected]) * 1e18}
    result = {
        "schema": "bvmsim-1111-history-read-crossover-independent-check-v1",
        "status": "PASS" if all(item["all_exact"] for item in pre_parity.values()) and all(item["all_common_samples_exact"] for item in exact_pairs.values()) and all(item["nonzero_sample_count"] > 0 for item in context_nonzero.values()) else "FAIL",
        "common_probe_count": len(common),
        "pre_70_parity": pre_parity,
        "history_pairs_exact": exact_pairs,
        "context_pairs_nonzero": context_nonzero,
        "bj2_trajectory": trajectory,
        "lin_minus_sum_lsl_read1_response": closure,
        "raw_sha256": {condition: digest(path) for condition, path in RAW.items()},
        "interpretation_boundary": "independent arithmetic supports crossover facts only; no clean SFQ count or unique mechanism claim",
    }
    (EXP / "analysis/independent_check.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
