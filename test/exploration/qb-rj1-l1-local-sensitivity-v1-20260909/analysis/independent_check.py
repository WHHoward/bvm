#!/usr/bin/env python3
"""Independent raw-only arithmetic cross-check; does not import analyze.py."""

from __future__ import annotations

import hashlib
import json
import math
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
from bvmtools.phase import continuous_unwrap, window_indices  # noqa: E402
from bvmtools.raw import read_csv  # noqa: E402


PHI0 = 2.067833848e-15
TAU = 2.0 * math.pi
RUNS = {"NOMINAL": "nominal", "L1_DOWN": "l1_down", "L1_UP": "l1_up", "RJ1_UP_05": "rj1_up_05", "RJ1_UP_10": "rj1_up_10"}
WINDOWS = {"EARLY_TRIGGER": (110e-12, 116e-12), "FULL_READ": (110e-12, 121e-12), "FULL_FINAL": (110e-12, 200e-12)}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def vec(trace, label: str) -> tuple[float, ...]:
    return tuple(float(value) for value in trace.column(label))


def indices(trace, window: tuple[float, float]) -> tuple[int, ...]:
    return window_indices(trace.time, *window)


def trapz(time_s: tuple[float, ...], data: tuple[float, ...], ix: tuple[int, ...]) -> float:
    return sum(0.5 * (data[a] + data[b]) * (time_s[b] - time_s[a]) for a, b in zip(ix, ix[1:]))


def max_abs(data: tuple[float, ...]) -> float:
    return max((abs(value) for value in data), default=0.0)


def rms(data: tuple[float, ...]) -> float:
    return math.sqrt(sum(value * value for value in data) / len(data)) if data else 0.0


def main() -> int:
    traces = {run_id: read_csv(EXP / "runs" / directory / "raw.csv") for run_id, directory in RUNS.items()}
    nominal_time = traces["NOMINAL"].time
    result: dict[str, object] = {
        "schema": "qb-rj1-l1-local-sensitivity-independent-check-v1",
        "experiment_id": EXP.name,
        "created_at_local": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "does_not_import_primary_analyzer": True,
        "raw_hashes": {run_id: sha256(EXP / "runs" / directory / "raw.csv") for run_id, directory in RUNS.items()},
        "exact_time_grid": {run_id: trace.time == nominal_time for run_id, trace in traces.items()},
        "interpolation": "none",
        "checks": {},
    }
    for run_id, trace in traces.items():
        l1 = vec(trace, "I(L1|XBQ1)")
        l2 = vec(trace, "I(L2|XBQ1)")
        ib = vec(trace, "I(IB|XBQ1)")
        quiet = tuple(sum(vec(trace, f"I(L_SL|XBVM{i})")[j] for i in range(2, 5)) for j in range(trace.sample_count))
        kcl = tuple(l2[j] - ib[j] - l1[j] for j in range(trace.sample_count))
        phase = continuous_unwrap(vec(trace, "P(BJ1|XBQ1)"))
        ref = min(range(trace.sample_count), key=lambda j: abs(trace.time[j] - 110e-12))
        rel = tuple((value - phase[ref]) / TAU for value in phase)
        check: dict[str, object] = {
            "sample_count": trace.sample_count,
            "header_count": len(trace.headers),
            "time_start_ps": trace.time[0] * 1e12,
            "time_end_ps": trace.time[-1] * 1e12,
            "quiet_total_formula": "I(L_SL|XBVM2)+I(L_SL|XBVM3)+I(L_SL|XBVM4)",
            "quiet_total_full_final": {"min_uA": min(quiet[i] for i in indices(trace, WINDOWS["FULL_FINAL"])) * 1e6, "max_uA": max(quiet[i] for i in indices(trace, WINDOWS["FULL_FINAL"])) * 1e6},
            "kcl_L2_minus_IB_minus_L1_full_read": {"max_abs_uA": max_abs(tuple(kcl[i] for i in indices(trace, WINDOWS["FULL_READ"]))) * 1e6, "RMS_uA": rms(tuple(kcl[i] for i in indices(trace, WINDOWS["FULL_READ"]))) * 1e6},
            "bj1_relative_progression_full_read": {"max_turns": max(rel[i] for i in indices(trace, WINDOWS["FULL_READ"])), "min_turns": min(rel[i] for i in indices(trace, WINDOWS["FULL_READ"])), "final_turns": rel[indices(trace, WINDOWS["FULL_READ"])[-1]], "reference_time_ps": trace.time[ref] * 1e12},
            "l1_at_110ps_uA": l1[ref] * 1e6,
            "l1_negative_to_nonnegative_brackets": [
                {"last_negative_time_ps": trace.time[a] * 1e12, "last_negative_uA": l1[a] * 1e6, "first_nonnegative_time_ps": trace.time[b] * 1e12, "first_nonnegative_uA": l1[b] * 1e6}
                for a, b in zip(indices(trace, WINDOWS["FULL_FINAL"]), indices(trace, WINDOWS["FULL_FINAL"])[1:])
                if l1[a] < 0.0 <= l1[b]
            ],
            "qbin_work": {},
        }
        vq = vec(trace, "V(QBIN)")
        il = vec(trace, "I(LIN|XBQ1)")
        product = tuple(vq[j] * il[j] for j in range(trace.sample_count))
        for name, window in WINDOWS.items():
            check["qbin_work"][name] = trapz(trace.time, product, indices(trace, window))  # type: ignore[index]
        # Same-JJ BJ1 phase/voltage area cross-check on the registered FULL_READ window.
        vbj1 = vec(trace, "V(BJ1|XBQ1)")
        ix = indices(trace, WINDOWS["FULL_READ"])
        phase_delta = phase[ix[-1]] - phase[ix[0]]
        area_turns = trapz(trace.time, vbj1, ix) / PHI0
        check["bj1_same_jj_phase_area_full_read"] = {"phase_delta_rad": phase_delta, "phase_delta_turns": phase_delta / TAU, "voltage_area_turns": area_turns, "residual_turns": phase_delta / TAU - area_turns, "not_an_sfq_count": True}
        result["checks"][run_id] = check
    result["all_exact_time_grid"] = all(result["exact_time_grid"].values())
    result["status"] = "PASS" if result["all_exact_time_grid"] else "FAIL"
    target = EXP / "analysis/independent_check.json"
    if target.exists():
        raise RuntimeError(f"refusing to overwrite independent check: {target}")
    target.write_text(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "run_count": len(RUNS), "all_exact_time_grid": result["all_exact_time_grid"], "output": str(target)}, ensure_ascii=False))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
