#!/usr/bin/env python3
"""Mechanical QA and registered arithmetic for one immutable JoSIM raw CSV."""

from __future__ import annotations

import csv
import json
import math
import statistics
from decimal import Decimal
from pathlib import Path
from typing import Any

from common import (MATRIX, PHI0, in_half_open_window, probe_signals,
                    raw_time_ps, read_json, run_dir, sha256, write_json)

MAPPING_PATH = Path(__file__).resolve().parents[1] / "analysis" / "PHASE_AREA_MAPPING.json"
MAPPING_SPEC = read_json(MAPPING_PATH)
JJ_PAIRS = [(item["stage"], item["phase_column"], item["voltage_column"])
            for item in MAPPING_SPEC["mappings"]]
MAPPING_BY_STAGE = {item["stage"]: item for item in MAPPING_SPEC["mappings"]}
WINDOWS = read_json(MATRIX)["windows_ps"]


def integrate(times_s: list[float], values: list[float]) -> float:
    if len(times_s) != len(values) or len(times_s) < 2:
        raise ValueError("trapezoidal integration requires equal arrays with at least two samples")
    return math.fsum((t1 - t0) * (v0 + v1) * 0.5
                     for t0, t1, v0, v1 in zip(times_s, times_s[1:], values, values[1:]))


def integrate_actual(time_tokens_s: list[str], values: list[float]) -> float:
    """Integrate using exact Decimal differences of the stored seconds tokens."""
    if len(time_tokens_s) != len(values) or len(time_tokens_s) < 2:
        raise ValueError("actual-grid integration requires equal arrays with at least two samples")
    deltas_s = [float(Decimal(right) - Decimal(left))
                for left, right in zip(time_tokens_s, time_tokens_s[1:])]
    return math.fsum(dt * (v0 + v1) * 0.5
                     for dt, v0, v1 in zip(deltas_s, values, values[1:]))


def window_indices(time_tokens_s: list[str], bounds_ps: list[float]) -> list[int]:
    return [index for index, token in enumerate(time_tokens_s)
            if in_half_open_window(token, bounds_ps)]


def load_selected_raw(raw: Path) -> tuple[list[str], list[float], dict[str, list[float]], dict[str, Any]]:
    before = sha256(raw)
    requested = probe_signals()
    selected = {signal for signal in requested if signal.startswith(("P(", "V("))}
    with raw.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        headers = reader.fieldnames or []
        if not headers or len(headers) != len(set(headers)):
            raise ValueError("raw CSV has empty or duplicate headers")
        if headers[0].strip().lower() != "time":
            raise ValueError("raw CSV first column must be the stored time in seconds")
        missing = sorted(set(requested) - set(headers))
        if missing:
            raise ValueError(f"required raw probes absent: {missing[:20]}")
        time_tokens_s: list[str] = []
        times_s: list[float] = []
        times_ps: list[Decimal] = []
        values = {signal: [] for signal in selected}
        finite_values = True
        for line_no, row in enumerate(reader, start=2):
            try:
                token = row["time"]
                t_decimal = Decimal(token)
                if not t_decimal.is_finite():
                    raise ValueError("non-finite time")
                t_s = float(t_decimal)
                if not math.isfinite(t_s):
                    raise ValueError("time is not finite float seconds")
                time_tokens_s.append(token)
                times_s.append(t_s)
                times_ps.append(raw_time_ps(token))
                for header in headers:
                    value = float(row[header])
                    if not math.isfinite(value):
                        finite_values = False
                        raise ValueError(f"non-finite {header}")
                    if header in values:
                        values[header].append(value)
            except (KeyError, TypeError, ValueError, ArithmeticError) as exc:
                raise ValueError(f"invalid raw value at line {line_no}: {exc}") from exc
    if len(times_ps) < 2 or any(right <= left for left, right in zip(times_ps, times_ps[1:])):
        raise ValueError("raw time grid must have at least two strictly increasing stored samples")
    steps_ps = [right - left for left, right in zip(times_ps, times_ps[1:])]
    median_dt = statistics.median(steps_ps)
    irregular = sum(abs(dt - median_dt) > max(Decimal("1e-10"), median_dt * Decimal("1e-6"))
                    for dt in steps_ps)
    grid_contract = read_json(MATRIX).get("actual_grid_contract", {})
    required_start = Decimal(str(grid_contract.get("required_start_ps", 0)))
    minimum_end = Decimal(str(grid_contract.get("minimum_end_ps", 200)))
    time_coverage_valid = times_ps[0] == required_start and times_ps[-1] >= minimum_end
    qa = {"schema": "bvm-bq-cb-gap-raw-qa-v2", "status": "PENDING_DERIVED_QA",
          "raw_sha256_before": before, "raw_sha256_after": None,
          "sample_count": len(times_s), "column_count": len(headers),
          "requested_probe_count": len(requested), "missing_required_probes": [],
          "finite_values": finite_values, "strictly_increasing_time": True,
          "time_start_s_token": time_tokens_s[0], "time_end_s_token": time_tokens_s[-1],
          "time_start_ps": float(times_ps[0]), "time_end_ps": float(times_ps[-1]),
          "median_dt_ps": float(median_dt), "irregular_step_count": irregular,
          "required_start_ps": float(required_start), "minimum_end_ps": float(minimum_end),
          "time_coverage_valid": time_coverage_valid,
          "window_membership": "Decimal parse of stored JoSIM seconds token converted to ps; half-open [start,end)",
          "integration_grid": "actual stored timestamps; no interpolation or resampling",
          "raw_immutable": True}
    return time_tokens_s, times_s, values, qa


def phase_window_summary(series: list[float], indices: list[int]) -> dict[str, float | int | None]:
    selected = [series[index] for index in indices]
    if not selected:
        return {"sample_count": 0, "mean_phase_rad_raw": None,
                "min_phase_rad_raw": None, "max_phase_rad_raw": None,
                "p2p_phase_rad_raw": None}
    low, high = min(selected), max(selected)
    return {"sample_count": len(selected), "mean_phase_rad_raw": statistics.fmean(selected),
            "min_phase_rad_raw": low, "max_phase_rad_raw": high,
            "p2p_phase_rad_raw": high - low}


def stage_window_metrics(time_tokens_s: list[str], values: dict[str, list[float]]) -> list[dict[str, Any]]:
    # JoSIM phase-mode P(...) is already raw unwrapped radians; do not modulo or re-unwrap it.
    phase_cache = {phase: series for phase, series in values.items() if phase.startswith("P(")}
    rows = []
    for stage, phase_signal, voltage_signal in JJ_PAIRS:
        mapping = MAPPING_BY_STAGE[stage]
        rd = int(mapping["reporting_direction"])
        vts = int(mapping["voltage_to_phase_sign"])
        for window, bounds in WINDOWS.items():
            indices = window_indices(time_tokens_s, bounds)
            if len(indices) < 2:
                rows.append({"stage": stage, "phase_signal": phase_signal,
                             "voltage_signal": voltage_signal, "window": window,
                             "registered_window_ps": bounds, "window_semantics": "[start,end)",
                             "status": "INVALID_TOO_FEW_SAMPLES", "sample_count": len(indices),
                             "metric_spec_version": MAPPING_SPEC["metric_spec"]["version"]})
                continue
            first, last = indices[0], indices[-1]
            phase = phase_cache[phase_signal]
            delta_rad = phase[last] - phase[first]
            raw_area = integrate_actual([time_tokens_s[index] for index in indices],
                                         [values[voltage_signal][index] for index in indices])
            area_aligned = vts * raw_area
            phase_reported = rd * delta_rad / (2.0 * math.pi)
            area_reported = rd * area_aligned / PHI0
            stats = phase_window_summary(phase, indices)
            rows.append({"stage": stage, "phase_signal": phase_signal,
                         "voltage_signal": voltage_signal, "window": window,
                         "registered_window_ps": bounds, "window_semantics": "[start,end)",
                         "sample_count": len(indices),
                         "actual_first_sample_s_token": time_tokens_s[first],
                         "actual_last_sample_s_token": time_tokens_s[last],
                         "actual_first_sample_ps": float(raw_time_ps(time_tokens_s[first])),
                         "actual_last_sample_ps": float(raw_time_ps(time_tokens_s[last])),
                         "phase_window_mean_rad_raw": stats["mean_phase_rad_raw"],
                         "phase_window_min_rad_raw": stats["min_phase_rad_raw"],
                         "phase_window_max_rad_raw": stats["max_phase_rad_raw"],
                         "phase_window_p2p_rad_raw": stats["p2p_phase_rad_raw"],
                         "status": "RECORDED", "delta_phase_rad": delta_rad,
                         "reporting_direction": rd, "phase_reported_turns": phase_reported,
                         "phase_delta_turns_navigation": phase_reported,
                         "voltage_to_phase_sign": vts, "voltage_area_raw_v_s": raw_area,
                         "voltage_area_aligned_v_s": area_aligned,
                         "voltage_area_v_s": area_aligned, "area_reported_phi0": area_reported,
                         "voltage_area_phi0": area_reported,
                         "residual_turns_navigation": phase_reported - area_reported,
                         "mapping_status": MAPPING_SPEC["mapping_status"],
                         "tolerance_status": MAPPING_SPEC["tolerance_status"],
                         "integration_grid": "same JJ, identical stored endpoints, actual timestamps; no interpolation"})
    return rows


def terminal_area_metrics(time_tokens_s: list[str], values: dict[str, list[float]]) -> list[dict[str, Any]]:
    signal = "V(R_TERM)"
    result = []
    for window in ("final_read", "post_read", "read_response"):
        bounds = WINDOWS[window]
        indices = window_indices(time_tokens_s, bounds)
        if len(indices) < 2:
            result.append({"signal": signal, "window": window, "registered_window_ps": bounds,
                           "status": "INVALID_TOO_FEW_SAMPLES", "sample_count": len(indices)})
            continue
        area = integrate_actual([time_tokens_s[index] for index in indices],
                                 [values[signal][index] for index in indices])
        result.append({"signal": signal, "window": window, "registered_window_ps": bounds,
                       "window_semantics": "[start,end)", "sample_count": len(indices),
                       "actual_first_sample_s_token": time_tokens_s[indices[0]],
                       "actual_last_sample_s_token": time_tokens_s[indices[-1]],
                       "actual_first_sample_ps": float(raw_time_ps(time_tokens_s[indices[0]])),
                       "actual_last_sample_ps": float(raw_time_ps(time_tokens_s[indices[-1]])),
                       "signed_area_v_s": area, "signed_area_phi0": area / PHI0,
                       "status": "RECORDED", "integration_grid": "actual stored timestamps; no interpolation"})
    return result


def bvm_state_windows(time_tokens_s: list[str], values: dict[str, list[float]]) -> list[dict[str, Any]]:
    records = []
    for bvm in (1, 2):
        for jj in ("B_JM1", "B_JM2", "B_JS1", "B_JS2"):
            signal = f"P({jj}|XBVM{bvm})"
            raw_phase_rad = values[signal]
            summaries = {}
            for name in ("pre_read", "post_read"):
                bounds = WINDOWS[name]
                indices = window_indices(time_tokens_s, bounds)
                summaries[name] = {"registered_window_ps": bounds,
                                   **phase_window_summary(raw_phase_rad, indices)}
            pre = summaries["pre_read"]["mean_phase_rad_raw"]
            post = summaries["post_read"]["mean_phase_rad_raw"]
            records.append({"bvm": bvm, "junction": jj, "phase_signal": signal,
                            "windows": summaries,
                            "platform_delta_rad": post - pre if pre is not None and post is not None else None,
                            "post_minus_pre_turns_navigation": (post - pre) / (2.0 * math.pi) if pre is not None and post is not None else None,
                            "platform_semantics": "mean(raw P_post)-mean(raw P_pre); distinct from endpoint delta",
                            "classification": "DESCRIPTIVE_PHASE_STATE_ONLY"})
    return records


def voltage_extrema(time_tokens_s: list[str], values: dict[str, list[float]]) -> list[dict[str, Any]]:
    indices = window_indices(time_tokens_s, WINDOWS["read_response"])
    output = []
    for signal in [pair[2] for pair in JJ_PAIRS] + ["V(FINAL_OUT)", "V(R_TERM)"]:
        if not indices:
            output.append({"signal": signal, "status": "UNKNOWN_NO_READ_RESPONSE_SAMPLES",
                           "semantics": "maximum-absolute stored voltage sample; navigation only, not an event"})
            continue
        selected = max(indices, key=lambda index: abs(values[signal][index]))
        output.append({"signal": signal, "time_s_token": time_tokens_s[selected],
                       "time_ps": float(raw_time_ps(time_tokens_s[selected])),
                       "voltage_v": values[signal][selected], "status": "RECORDED",
                       "semantics": "maximum-absolute stored voltage sample; navigation only, not an event"})
    return output


def write_csv(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def analyze(run_id: str) -> dict[str, Any]:
    directory = run_dir(run_id)
    raw = directory / "raw.csv"
    before = sha256(raw)
    metadata = read_json(directory / "metadata.json")
    if metadata.get("raw", {}).get("sha256") != before:
        raise ValueError("raw SHA does not match solve-time metadata")
    time_tokens_s, times_s, values, raw_qa = load_selected_raw(raw)
    stage_metrics = stage_window_metrics(time_tokens_s, values)
    terminal_metrics = terminal_area_metrics(time_tokens_s, values)
    state_metrics = bvm_state_windows(time_tokens_s, values)
    extrema = voltage_extrema(time_tokens_s, values)
    analysis_dir = directory / "analysis"
    analysis_dir.mkdir(exist_ok=True)
    write_json(analysis_dir / "metrics.json", {
        "schema": "bvm-bq-cb-gap-mechanical-metrics-v2",
        "run_id": run_id, "mask": metadata["parameters"]["MASK"],
        "metric_spec": MAPPING_SPEC["metric_spec"],
        "phase_area_mapping_path": "analysis/PHASE_AREA_MAPPING.json",
        "phase_area_mapping_sha256": sha256(MAPPING_PATH),
        "registered_windows_ps": WINDOWS, "jj_phase_area_metrics": stage_metrics,
        "terminal_area_metrics": terminal_metrics, "bvm_state_observations": state_metrics,
        "voltage_extrema_navigation_only": extrema,
        "semantics": {"phase_raw_unit": "radians", "turns": "reporting_direction*delta_phase_rad/(2*pi), navigation only",
                      "phase_area_crosscheck": "same JJ, same actual first/last stored samples, registered signs",
                      "residual_tolerance": "UNFROZEN; residuals descriptive only",
                      "terminal_area": "signed integral divided by Phi0; no event count inferred",
                      "classification": "not performed"},
        "scientific_interpretation_performed": False,
    })
    stage_fields = ["stage", "window", "phase_signal", "voltage_signal", "status",
                    "registered_window_ps", "sample_count", "actual_first_sample_s_token",
                    "actual_last_sample_s_token", "actual_first_sample_ps", "actual_last_sample_ps",
                    "phase_window_mean_rad_raw", "phase_window_min_rad_raw",
                    "phase_window_max_rad_raw", "phase_window_p2p_rad_raw",
                    "delta_phase_rad", "reporting_direction", "phase_reported_turns",
                    "voltage_to_phase_sign", "voltage_area_raw_v_s", "voltage_area_aligned_v_s",
                    "area_reported_phi0", "residual_turns_navigation"]
    write_csv(analysis_dir / "stage_metrics.csv", stage_fields, stage_metrics)
    write_csv(analysis_dir / "terminal_metrics.csv",
              ["signal", "window", "status", "registered_window_ps", "sample_count",
               "actual_first_sample_s_token", "actual_last_sample_s_token", "actual_first_sample_ps",
               "actual_last_sample_ps", "signed_area_v_s", "signed_area_phi0"], terminal_metrics)
    write_csv(analysis_dir / "voltage_extrema.csv",
              ["signal", "status", "time_s_token", "time_ps", "voltage_v", "semantics"], extrema)
    after = sha256(raw)
    all_stage_windows_valid = all(row.get("status") == "RECORDED" for row in stage_metrics)
    all_terminal_windows_valid = all(row.get("status") == "RECORDED" for row in terminal_metrics)
    raw_qa.update({"raw_sha256_after": after, "raw_unchanged": before == after,
                   "registered_stage_window_samples_valid": all_stage_windows_valid,
                   "registered_terminal_window_samples_valid": all_terminal_windows_valid})
    raw_qa["status"] = "PASS" if before == after and raw_qa["finite_values"] and raw_qa["strictly_increasing_time"] and raw_qa["time_coverage_valid"] and all_stage_windows_valid and all_terminal_windows_valid else "FAIL"
    write_json(analysis_dir / "raw_qa.json", raw_qa)
    qa = {"schema": "bvm-bq-cb-gap-analysis-qa-v2", "run_id": run_id,
          "status": raw_qa["status"], "raw_sha256_before_after": {"before": before, "after": after},
          "required_probe_count": len(probe_signals()), "same_jj_phase_area_windows": True,
          "actual_grid_integration": True, "exact_decimal_window_membership": True,
          "interpolation_or_resampling": False, "raw_unchanged": before == after,
          "scientific_interpretation_performed": False}
    write_json(analysis_dir / "analysis_qa.json", qa)
    return qa


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Mechanical raw analysis for one registered run")
    parser.add_argument("run_id")
    args = parser.parse_args()
    qa = analyze(args.run_id)
    print(json.dumps(qa, ensure_ascii=False, indent=2))
    return 0 if qa["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
