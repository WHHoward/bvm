#!/usr/bin/env python3
"""不读取 task-local metrics.json 的独立关键数值复核。

仍使用仓库共享 raw reader 和实际网格积分；本脚本只重新组织少量关键量，
不复制 CSV parser、phase unwrap 或 SFQ 算法。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
A_ROOT = REPO / "test/exploration/bvmsim-4bvm-state-position-closure-v1-20260903"
STATES = ("0000", "1000", "0100", "0010", "0001", "1111")
ONE_HOT = ("1000", "0100", "0010", "0001")
READ1 = (110.0e-12, 170.0e-12)

sys.path.insert(0, str(REPO / "scripts"))
from bvmtools.compare import exact_time_grid_identity  # noqa: E402
from bvmtools.metrics import phase_area_window  # noqa: E402
from bvmtools.raw import read_csv  # noqa: E402
from bvmtools.waveform import trapezoid_integral  # noqa: E402


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sig(trace, label: str):
    return trace.column(label)


def indices(trace, bounds):
    return [i for i, value in enumerate(trace.time) if bounds[0] <= value < bounds[1]]


def max_abs(values):
    return max((abs(float(value)) for value in values), default=0.0)


def abs_peak_time(trace, values, bounds):
    selected = indices(trace, bounds)
    if not selected:
        return None
    index = max(selected, key=lambda i: abs(float(values[i])))
    return trace.time[index] * 1.0e12


def signal_peak(trace, label: str, *, value_factor: float, area_factor: float) -> dict[str, float | None]:
    values = sig(trace, label)
    selected_indices = indices(trace, READ1)
    selected = [values[i] for i in selected_indices]
    return {
        "max_abs": max_abs(selected) * value_factor,
        "signed_integral": trapezoid_integral(
            selected,
            [trace.time[i] for i in selected_indices],
        ) * area_factor,
        "abs_peak_time_ps": abs_peak_time(trace, values, READ1),
    }


def delta_current(trace, baseline, label: str) -> dict[str, float | None]:
    values = sig(trace, label)
    base = sig(baseline, label)
    selected = indices(trace, READ1)
    delta = [float(values[i]) - float(base[i]) for i in selected]
    times = [trace.time[i] for i in selected]
    return {
        "minimum_uA": min(delta) * 1.0e6,
        "maximum_uA": max(delta) * 1.0e6,
        "max_abs_uA": max_abs(delta) * 1.0e6,
        "p2p_uA": (max(delta) - min(delta)) * 1.0e6,
        "rms_uA": math.sqrt(sum(value * value for value in delta) / len(delta)) * 1.0e6,
        "signed_integral_uA_ps": trapezoid_integral(delta, times) * 1.0e18,
        "abs_peak_time_ps": abs_peak_time(trace, [float(values[i]) - float(base[i]) for i in range(len(values))], READ1),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=EXP / "analysis/independent_check.json")
    args = parser.parse_args()
    connected = {state: read_csv(EXP / "runs" / state / "raw.csv") for state in STATES}
    omitted = {state: read_csv(A_ROOT / "runs_sl_endpoints" / state / "raw.csv") for state in STATES}
    for state in STATES:
        if not exact_time_grid_identity(connected[state].time, connected["0000"].time):
            raise RuntimeError(f"connected time grid mismatch: {state}")
        if not exact_time_grid_identity(omitted[state].time, omitted["0000"].time):
            raise RuntimeError(f"omitted time grid mismatch: {state}")
        if not exact_time_grid_identity(connected[state].time, omitted[state].time):
            raise RuntimeError(f"A/B time grid mismatch: {state}")

    position = {
        state: {
            "V(QBIN)_mV": signal_peak(connected[state], "V(QBIN)", value_factor=1.0e3, area_factor=1.0e15),
            "I(LIN|XBQ1)_uA": signal_peak(connected[state], "I(LIN|XBQ1)", value_factor=1.0e6, area_factor=1.0e18),
        }
        for state in ONE_HOT
    }
    cross: dict[str, object] = {}
    for state in ONE_HOT:
        cross[state] = {}
        for number, bit in enumerate(state, start=1):
            if bit == "1":
                continue
            label = f"I(L_SL|XBVM{number})"
            cross[state][f"BVM{number}"] = {
                "omitted": delta_current(omitted[state], omitted["0000"], label),
                "connected": delta_current(connected[state], connected["0000"], label),
            }

    phase_area = {}
    for state in STATES:
        trace = connected[state]
        phase_area[state] = {
            "BJ2_READ1": phase_area_window(
                trace.time,
                sig(trace, "P(BJ2|XBQ1)"),
                sig(trace, "V(BJ2|XBQ1)"),
                READ1,
                include_segments=False,
            ),
            "JTL6_B02_READ1": phase_area_window(
                trace.time,
                sig(trace, "P(B02|XJTL1_6)"),
                sig(trace, "V(B02|XJTL1_6)"),
                READ1,
                include_segments=False,
            ),
        }

    result = {
        "schema": "bvmsim-4bvm-jm2-connected-independent-check-v1",
        "source": "raw.csv only; metrics.json not read",
        "time_grid_exact_all": True,
        "raw_sha256": {
            "connected": {state: digest(EXP / "runs" / state / "raw.csv") for state in STATES},
            "omitted_endpoint": {state: digest(A_ROOT / "runs_sl_endpoints" / state / "raw.csv") for state in STATES},
        },
        "position": position,
        "zero_bvm_delta_current": cross,
        "same_jj_phase_area": phase_area,
        "assertions": {
            "six_connected_raw_loaded": len(connected) == 6,
            "four_one_hot_position_records": len(position) == 4,
            "zero_cell_records": sum(len(value) for value in cross.values()) == 8,
            "phase_area_records": len(phase_area) == 6,
        },
    }
    if not all(result["assertions"].values()):
        raise RuntimeError(f"independent assertions failed: {result['assertions']}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists():
        old = args.output.read_text(encoding="utf-8")
        new = json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
        if old != new:
            raise RuntimeError(f"refusing to overwrite independent check: {args.output}")
    else:
        args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "output": str(args.output.relative_to(REPO))}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
