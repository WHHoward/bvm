#!/usr/bin/env python3
"""Independent read-only recomputation of registered same-JJ phase/area arithmetic."""

from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any

SERIES = Path(__file__).resolve().parents[1]
REPO = SERIES.parents[2]
TASK = SERIES / "analysis" / "cb-direct-d1-20261009"
PHI0 = 2.067833848e-15
WINDOWS_PS = {
    "ARRAY_FINAL_READ": (110.0, 121.0),
    "PRE_CLOCK": (121.0, 200.0),
    "CLOCK_EDGE": (200.0, 205.0),
    "POST_CLOCK": (205.0, 300.0),
    "TOTAL": (0.0, 300.0),
}
RUN_IDS = ("A023_CB_DIRECT_D1_ALL_CLOCK", "A024_CB_DIRECT_D1_PAPER_CLOCK")
JUNCTIONS = (
    "P(BJ1|XCBU_D1)", "P(BJ2|XCBU_D1)", "P(B_J11|XT1_D0)",
    "P(B_J1|XT1_D1)", "P(B_J9|XT1_D1)", "P(B_J10|XT1_D1)",
    "P(B_J11|XT1_D1)", "P(BJ1|XCB_D1_L2)",
)


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def unwrap_rad(values: list[float]) -> list[float]:
    if not values:
        return []
    result = [values[0]]
    for previous, current in zip(values, values[1:]):
        delta = current - previous
        while delta > math.pi:
            delta -= 2 * math.pi
        while delta < -math.pi:
            delta += 2 * math.pi
        result.append(result[-1] + delta)
    return result


def integrate_actual_grid(times: list[float], values: list[float], indexes: list[int]) -> float:
    return sum((values[left] + values[right]) * 0.5 * (times[right] - times[left])
               for left, right in zip(indexes, indexes[1:]))


def main() -> int:
    output = TASK / "NUMERICAL_RECHECK.json"
    if output.exists():
        raise FileExistsError(f"refusing to overwrite numerical recheck: {output}")
    run_results: list[dict[str, Any]] = []
    max_phase_residual_turns = 0.0
    max_raw_vs_metrics_phase_error_rad = 0.0
    max_raw_vs_metrics_area_error_v_s = 0.0
    check_count = 0

    for run_id in RUN_IDS:
        run_dir = SERIES / "runs" / run_id
        raw = run_dir / "raw.csv"
        metrics_path = run_dir / "metrics.json"
        raw_sha_before = sha(raw)
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
        wanted = {label for phase in JUNCTIONS for label in (phase, "V(" + phase[2:])}
        times: list[float] = []
        columns = {label: [] for label in wanted}
        with raw.open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            header = reader.fieldnames or []
            if not header or header[0] != "time" or len(header) != len(set(header)):
                raise ValueError(f"{run_id}: invalid raw header")
            missing = wanted - set(header)
            if missing:
                raise ValueError(f"{run_id}: missing required direct JJ probes {sorted(missing)}")
            previous_time = -math.inf
            for line_no, row in enumerate(reader, start=2):
                time_s = float(row["time"])
                values = {label: float(row[label]) for label in wanted}
                if not math.isfinite(time_s) or time_s <= previous_time or any(
                        not math.isfinite(value) for value in values.values()):
                    raise ValueError(f"{run_id}: non-finite or non-monotone raw at line {line_no}")
                previous_time = time_s
                times.append(time_s)
                for label, value in values.items():
                    columns[label].append(value)
        if len(times) != 29999:
            raise ValueError(f"{run_id}: unexpected sample count {len(times)}")
        dt = [right-left for left, right in zip(times, times[1:])]
        window_indexes = {
            name: [i for i, time_s in enumerate(times)
                   if start_ps * 1e-12 <= time_s < end_ps * 1e-12]
            for name, (start_ps, end_ps) in WINDOWS_PS.items()
        }
        metric_index = {(item["phase_signal"], item["window"]): item
                        for item in metrics.get("same_jj_phase_voltage", [])}
        records = []
        for phase_signal in JUNCTIONS:
            voltage_signal = "V(" + phase_signal[2:]
            phase = unwrap_rad(columns[phase_signal])
            volts = columns[voltage_signal]
            for window, indexes in window_indexes.items():
                if len(indexes) < 2:
                    raise ValueError(f"{run_id}: too few rows in {window}")
                first, last = indexes[0], indexes[-1]
                phase_delta = phase[last] - phase[first]
                area = integrate_actual_grid(times, volts, indexes)
                record = metric_index[(phase_signal, window)]
                phase_error = abs(phase_delta - record["phase_delta_rad"])
                area_error = abs(area - record["voltage_area_v_s_same_jj_same_rows"])
                residual = phase_delta / (2 * math.pi) - area / PHI0
                max_phase_residual_turns = max(max_phase_residual_turns, abs(residual))
                max_raw_vs_metrics_phase_error_rad = max(max_raw_vs_metrics_phase_error_rad, phase_error)
                max_raw_vs_metrics_area_error_v_s = max(max_raw_vs_metrics_area_error_v_s, area_error)
                check_count += 1
                records.append({"phase_signal": phase_signal, "voltage_signal": voltage_signal,
                                "window": window, "sample_count": len(indexes),
                                "phase_delta_rad": phase_delta,
                                "phase_delta_rad_over_2pi_navigation": phase_delta / (2 * math.pi),
                                "voltage_area_v_s_same_jj_same_rows": area,
                                "voltage_area_phi0_arithmetic": area / PHI0,
                                "phase_minus_area_turn_residual": residual,
                                "raw_vs_metrics_phase_abs_error_rad": phase_error,
                                "raw_vs_metrics_area_abs_error_v_s": area_error})
        raw_sha_after = sha(raw)
        if raw_sha_after != raw_sha_before:
            raise RuntimeError(f"{run_id}: raw SHA changed during read-only recomputation")
        run_results.append({"run_id": run_id, "raw_sha256_before": raw_sha_before,
                            "raw_sha256_after": raw_sha_after, "metrics_sha256": sha(metrics_path),
                            "sample_count": len(times), "time_range_ps": [times[0]*1e12, times[-1]*1e12],
                            "dt_min_ps": min(dt)*1e12, "dt_max_ps": max(dt)*1e12,
                            "same_jj_window_check_count": len(records), "records": records})

    payload = {"schema": "bvm-4x4-cb-direct-d1-numerical-recheck-v1",
               "status": "PASS_RAW_RECOMPUTATION_MATCHES_METRICS",
               "analysis_script_path": Path(__file__).resolve().relative_to(REPO).as_posix(),
               "analysis_script_sha256": sha(Path(__file__).resolve()),
               "method": "Independent standard-library CSV read; radians unwrapped locally; trapezoid over actual timestamps and half-open windows.",
               "windows_ps_half_open": WINDOWS_PS,
               "phase_unit": "radians",
               "turns_semantics": "delta/(2*pi) navigation only; not SFQ/event count",
               "physical_solve_count": 0,
               "raw_modified": False,
               "comparison_rule": "No cross-run interpolation/resampling performed by this recheck.",
               "same_jj_window_checks": check_count,
               "max_raw_vs_metrics_phase_abs_error_rad": max_raw_vs_metrics_phase_error_rad,
               "max_raw_vs_metrics_area_abs_error_v_s": max_raw_vs_metrics_area_error_v_s,
               "max_same_jj_phase_area_residual_turns": max_phase_residual_turns,
               "runs": run_results,
               "scientific_interpretation_performed": False,
               "automatic_follow_up": False}
    with output.open("x", encoding="utf-8") as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(json.dumps({"status": payload["status"], "same_jj_window_checks": check_count,
                      "max_raw_vs_metrics_phase_abs_error_rad": max_raw_vs_metrics_phase_error_rad,
                      "max_raw_vs_metrics_area_abs_error_v_s": max_raw_vs_metrics_area_error_v_s,
                      "max_same_jj_phase_area_residual_turns": max_phase_residual_turns,
                      "raw_sha256_unchanged": all(item["raw_sha256_before"] == item["raw_sha256_after"]
                                                   for item in run_results),
                      "physical_solve_count": 0}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
