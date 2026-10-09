#!/usr/bin/env python3
"""Independent raw reread of selected A025/A026 arithmetic (no solver)."""

from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any

SERIES = Path(__file__).resolve().parents[1]
TASK = SERIES / "analysis" / "cb-carry-buffer-d1-20261009"
RUNS = SERIES / "runs"
PHI0 = 2.067833848e-15
WINDOWS = {"ARRAY_FINAL_READ": (110.0, 121.0), "PRE_CLOCK": (121.0, 200.0),
           "CLOCK_EDGE": (200.0, 205.0), "POST_CLOCK": (205.0, 300.0),
           "TOTAL": (0.0, 300.0)}
RUN_IDS = ("A025_CARRY_CB_D1_ALL_CLOCK", "A026_CARRY_CB_D1_PAPER_CLOCK")
CHECK_SIGNALS = (
    "V(C_D0)", "I(V_CBU_A_D1)", "I(V_CARRY_IN_D1)", "I(V_CBU_B_D1)",
    "P(BJ1|XCB_CARRY_D1)", "P(BJ2|XCB_CARRY_D1)",
    "P(B_J11|XT1_D0)", "P(B_J11|XT1_D1)",
)
REQUIRED_SIGNALS = set(CHECK_SIGNALS) | {
    f"V({signal[2:]}" for signal in CHECK_SIGNALS if signal.startswith("P(")}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_columns(path: Path, required: set[str]) -> tuple[list[float], dict[str, list[float]]]:
    times, columns = [], {name: [] for name in required}
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.reader(stream)
        header = next(reader)
        if not header or header[0] != "time" or len(header) != len(set(header)):
            raise RuntimeError(f"invalid raw header: {path}")
        missing = required - set(header)
        if missing:
            raise RuntimeError(f"raw probes missing: {sorted(missing)}")
        indexes = {label: header.index(label) for label in required}
        previous = -math.inf
        for row in reader:
            time = float(row[0])
            if not math.isfinite(time) or time <= previous:
                raise RuntimeError(f"raw time is not strictly increasing: {path}")
            previous = time
            times.append(time)
            for label in required:
                value = float(row[indexes[label]])
                if not math.isfinite(value):
                    raise RuntimeError(f"non-finite raw value {label}: {path}")
                columns[label].append(value)
    return times, columns


def trapz(times: list[float], values: list[float], indices: list[int]) -> float:
    total = 0.0
    for left, right in zip(indices, indices[1:]):
        total += 0.5 * (values[left] + values[right]) * (times[right] - times[left])
    return total


def unwrap(values: list[float]) -> list[float]:
    output = [values[0]]
    for before, after in zip(values, values[1:]):
        delta = after - before
        while delta > math.pi:
            delta -= 2 * math.pi
        while delta < -math.pi:
            delta += 2 * math.pi
        output.append(output[-1] + delta)
    return output


def close(a: float, b: float) -> bool:
    return math.isclose(a, b, rel_tol=2e-12, abs_tol=1e-24)


def main() -> int:
    waveform_rows = list(csv.DictReader((TASK / "CB_CARRY_BUFFER_METRICS.csv").open(encoding="utf-8", newline="")))
    phase_rows = list(csv.DictReader((TASK / "SAME_JJ_PHASE_AREA.csv").open(encoding="utf-8", newline="")))
    waveform_index = {(row["run_id"], row["signal"], row["window"]): row for row in waveform_rows}
    phase_index = {(row["run_id"], row["phase_signal"], row["window"]): row for row in phase_rows}
    checks, raw_hashes = [], {}
    for run_id in RUN_IDS:
        raw = RUNS / run_id / "raw.csv"
        before = sha(raw)
        times, columns = read_columns(raw, REQUIRED_SIGNALS)
        unwrapped = {signal: unwrap(columns[signal]) for signal in CHECK_SIGNALS if signal.startswith("P(")}
        for window, (start_ps, end_ps) in WINDOWS.items():
            indices = [i for i, time in enumerate(times) if start_ps <= time*1e12 < end_ps]
            if len(indices) < 2:
                raise RuntimeError(f"too few actual samples for {run_id}/{window}")
            for signal in CHECK_SIGNALS:
                if signal.startswith("P("):
                    p_record = phase_index[(run_id, signal, window)]
                    voltage_signal = f"V({signal[2:]}"
                    voltage_area = trapz(times, columns[voltage_signal], indices)
                    delta = unwrapped[signal][indices[-1]] - unwrapped[signal][indices[0]]
                    actuals = {
                        "phase_delta_rad": delta,
                        "phase_delta_over_2pi_navigation": delta/(2*math.pi),
                        "same_jj_same_rows_v_area": voltage_area,
                        "v_area_over_phi0_arithmetic": voltage_area/PHI0,
                        "phase_minus_area_turns_arithmetic": delta/(2*math.pi)-voltage_area/PHI0,
                    }
                    for key, actual in actuals.items():
                        recorded = float(p_record[key])
                        if not close(actual, recorded):
                            raise RuntimeError(f"independent phase-area mismatch {run_id}/{signal}/{window}/{key}: {actual} != {recorded}")
                        checks.append({"run_id": run_id, "signal": signal, "window": window,
                                       "metric": key, "independent": actual, "recorded": recorded,
                                       "absolute_error": abs(actual-recorded)})
                elif signal.startswith("V("):
                    record = waveform_index[(run_id, signal, window)]
                    values = columns[signal]
                    area = trapz(times, values, indices)
                    actuals = {"signed_area_v_s": area, "area_phi0_arithmetic": area/PHI0,
                               "min_v": min(values[i] for i in indices),
                               "max_v": max(values[i] for i in indices)}
                    for key, actual in actuals.items():
                        recorded = float(record[key])
                        if not close(actual, recorded):
                            raise RuntimeError(f"independent waveform mismatch {run_id}/{signal}/{window}/{key}: {actual} != {recorded}")
                        checks.append({"run_id": run_id, "signal": signal, "window": window,
                                       "metric": key, "independent": actual, "recorded": recorded,
                                       "absolute_error": abs(actual-recorded)})
                else:
                    record = waveform_index[(run_id, signal, window)]
                    charge = trapz(times, columns[signal], indices)
                    actuals = {"signed_charge_c": charge,
                               "min_a": min(columns[signal][i] for i in indices),
                               "max_a": max(columns[signal][i] for i in indices)}
                    for key, actual in actuals.items():
                        recorded = float(record[key])
                        if not close(actual, recorded):
                            raise RuntimeError(f"independent current mismatch {run_id}/{signal}/{window}/{key}: {actual} != {recorded}")
                        checks.append({"run_id": run_id, "signal": signal, "window": window,
                                       "metric": key, "independent": actual, "recorded": recorded,
                                       "absolute_error": abs(actual-recorded)})
        after = sha(raw)
        if before != after:
            raise RuntimeError(f"raw hash changed during independent reread: {run_id}")
        raw_hashes[run_id] = {"sha256_before": before, "sha256_after": after,
                              "sample_count": len(times), "time_start_s": times[0], "time_end_s": times[-1]}

    result = {"schema": "bvm-4x4-cb-carry-buffer-d1-independent-numeric-recheck-v1",
              "status": "PASS", "solver_invoked": False, "raw_modified": False,
              "raw_by_run": raw_hashes, "check_count": len(checks),
              "maximum_absolute_recomputation_error": max(row["absolute_error"] for row in checks),
              "checks": checks,
              "method": "independent CSV reader; actual timestamp trapezoid; half-open windows; independent raw-phase unwrap",
              "scientific_interpretation_performed": False}
    target = TASK / "NUMERICAL_RECHECK.json"
    if target.exists():
        raise FileExistsError(f"refusing to overwrite independent numeric check: {target}")
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    analysis_path = TASK / "BATCH_ANALYSIS.json"
    analysis = json.loads(analysis_path.read_text(encoding="utf-8"))
    if "independent_numeric_recheck" in analysis:
        raise RuntimeError("BATCH_ANALYSIS already records an independent recheck")
    analysis["independent_numeric_recheck"] = {
        "path": target.relative_to(SERIES).as_posix(), "sha256": sha(target),
        "status": result["status"], "check_count": result["check_count"],
        "maximum_absolute_recomputation_error": result["maximum_absolute_recomputation_error"]}
    analysis_path.write_text(json.dumps(analysis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "check_count": result["check_count"],
                      "maximum_absolute_recomputation_error": result["maximum_absolute_recomputation_error"],
                      "raw_sha256_by_run": {key: value["sha256_before"] for key, value in raw_hashes.items()},
                      "scientific_interpretation_performed": False}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
