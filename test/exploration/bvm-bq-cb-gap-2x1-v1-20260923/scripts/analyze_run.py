#!/usr/bin/env python3
"""Registered-grid arithmetic and artifact QA for one immutable raw CSV."""

from __future__ import annotations

import csv
import json
import math
import statistics
from pathlib import Path
from typing import Any

from common import MATRIX, PHI0, probe_signals, read_json, run_dir, sha256, write_json

JJ_PAIRS = [
    ("BQ1_BJ3", "P(BJ3|XBQ1)", "V(BJ3|XBQ1)"),
    ("BQ2_BJ3", "P(BJ3|XBQ2)", "V(BJ3|XBQ2)"),
    ("CB1_BJ2", "P(BJ2|XCB1)", "V(BJ2|XCB1)"),
    ("CB2_BJ2", "P(BJ2|XCB2)", "V(BJ2|XCB2)"),
    ("ACC1_BJ1", "P(BJ1|XACC1)", "V(BJ1|XACC1)"),
    ("ACC2_BJ1", "P(BJ1|XACC2)", "V(BJ1|XACC2)"),
    ("GAP1_BJ1", "P(BJ1|XGAP1)", "V(BJ1|XGAP1)"),
    ("GAP2_BJ1", "P(BJ1|XGAP2)", "V(BJ1|XGAP2)"),
]
EXTREMA_SIGNALS = [pair[2] for pair in JJ_PAIRS] + ["V(FINAL_OUT)", "V(R_TERM)"]
WINDOWS = read_json(MATRIX)["windows_ps"]


def unwrap(values: list[float]) -> list[float]:
    if not values:
        return []
    result = [values[0]]
    offset = 0.0
    previous = values[0]
    for value in values[1:]:
        delta = value - previous
        while delta > math.pi:
            offset -= 2.0 * math.pi
            delta -= 2.0 * math.pi
        while delta < -math.pi:
            offset += 2.0 * math.pi
            delta += 2.0 * math.pi
        result.append(value + offset)
        previous = value
    return result


def integrate(times_s: list[float], values: list[float]) -> float:
    return sum((t1 - t0) * (v0 + v1) * 0.5
               for t0, t1, v0, v1 in zip(times_s, times_s[1:], values, values[1:]))


def window_indices(times_ps: list[float], bounds: list[float]) -> list[int]:
    start, end = bounds
    return [i for i, time_ps in enumerate(times_ps) if start <= time_ps < end]


def load_selected_raw(raw: Path) -> tuple[list[str], list[float], dict[str, list[float]], dict[str, Any]]:
    before = sha256(raw)
    selected = {signal for signal in probe_signals()
                if signal.startswith("P(") or signal.startswith("V(")}
    with raw.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        headers = reader.fieldnames or []
        if not headers or len(headers) != len(set(headers)):
            raise ValueError("raw CSV has empty or duplicate headers")
        missing = sorted(set(probe_signals()) - set(headers))
        if missing:
            raise ValueError(f"required raw probes absent: {missing[:12]}")
        times_s: list[float] = []
        values = {signal: [] for signal in selected}
        finite_values = True
        for line_no, row in enumerate(reader, start=2):
            try:
                t = float(row["time"])
                if not math.isfinite(t):
                    raise ValueError("non-finite time")
                times_s.append(t)
                for header in headers:
                    value = float(row[header])
                    if not math.isfinite(value):
                        finite_values = False
                        raise ValueError(f"non-finite {header}")
                    if header in values:
                        values[header].append(value)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"invalid raw value at line {line_no}: {exc}") from exc
    times_ps = [t * 1e12 for t in times_s]
    if len(times_ps) < 2 or any(right <= left for left, right in zip(times_ps, times_ps[1:])):
        raise ValueError("raw time grid must have at least two strictly increasing samples")
    steps = [right - left for left, right in zip(times_ps, times_ps[1:])]
    median_dt = statistics.median(steps)
    irregular = sum(abs(dt - median_dt) > max(1e-10, median_dt * 1e-6) for dt in steps)
    qa = {"schema": "bvm-bq-cb-gap-raw-qa-v1", "status": "PASS",
          "raw_sha256_before": before, "raw_sha256_after": None,
          "sample_count": len(times_ps), "column_count": len(headers),
          "requested_probe_count": len(probe_signals()), "missing_required_probes": [],
          "finite_values": finite_values, "strictly_increasing_time": True,
          "time_start_ps": times_ps[0], "time_end_ps": times_ps[-1],
          "median_dt_ps": median_dt, "irregular_step_count": irregular,
          "stored_grid_only": True, "raw_immutable": True}
    return headers, times_s, values, qa


def stage_window_metrics(times_s: list[float], values: dict[str, list[float]]) -> list[dict[str, Any]]:
    times_ps = [time_s * 1e12 for time_s in times_s]
    phase_cache = {phase: unwrap(series) for phase, series in values.items() if phase.startswith("P(")}
    rows = []
    for stage, phase_signal, voltage_signal in JJ_PAIRS:
        for window, bounds in WINDOWS.items():
            indices = window_indices(times_ps, bounds)
            if len(indices) < 2:
                rows.append({"stage": stage, "phase_signal": phase_signal,
                             "voltage_signal": voltage_signal, "window": window,
                             "registered_window_ps": bounds, "status": "UNKNOWN_TOO_FEW_SAMPLES",
                             "sample_count": len(indices)})
                continue
            first, last = indices[0], indices[-1]
            phase = phase_cache[phase_signal]
            delta_rad = phase[last] - phase[first]
            area = integrate([times_s[i] for i in indices],
                             [values[voltage_signal][i] for i in indices])
            rows.append({"stage": stage, "phase_signal": phase_signal,
                         "voltage_signal": voltage_signal, "window": window,
                         "registered_window_ps": bounds, "window_semantics": "[start,end)",
                         "sample_count": len(indices), "actual_first_sample_ps": times_ps[first],
                         "actual_last_sample_ps": times_ps[last], "status": "RECORDED",
                         "delta_phase_rad": delta_rad,
                         "phase_delta_turns_navigation": delta_rad / (2.0 * math.pi),
                         "voltage_area_v_s": area, "voltage_area_phi0": area / PHI0,
                         "residual_turns_navigation": delta_rad / (2.0 * math.pi) - area / PHI0,
                         "integration_grid": "actual stored timestamps; no interpolation"})
    return rows


def terminal_area_metrics(times_s: list[float], values: dict[str, list[float]]) -> list[dict[str, Any]]:
    times_ps = [time_s * 1e12 for time_s in times_s]
    signal = "V(R_TERM)"
    result = []
    for window in ("final_read", "post_read", "read_response"):
        bounds = WINDOWS[window]
        indices = window_indices(times_ps, bounds)
        if len(indices) < 2:
            result.append({"signal": signal, "window": window, "status": "UNKNOWN_TOO_FEW_SAMPLES"})
            continue
        area = integrate([times_s[i] for i in indices], [values[signal][i] for i in indices])
        result.append({"signal": signal, "window": window, "registered_window_ps": bounds,
                       "window_semantics": "[start,end)", "sample_count": len(indices),
                       "actual_first_sample_ps": times_ps[indices[0]],
                       "actual_last_sample_ps": times_ps[indices[-1]],
                       "signed_area_v_s": area, "signed_area_phi0": area / PHI0,
                       "status": "RECORDED", "integration_grid": "actual stored timestamps; no interpolation"})
    return result


def bvm_state_windows(times_s: list[float], values: dict[str, list[float]]) -> list[dict[str, Any]]:
    times_ps = [time_s * 1e12 for time_s in times_s]
    records = []
    for bvm in (1, 2):
        for jj in ("B_JM1", "B_JM2", "B_JS1", "B_JS2"):
            signal = f"P({jj}|XBVM{bvm})"
            unwrapped = unwrap(values[signal])
            summaries = {}
            for name in ("pre_read", "bvm_state_post"):
                bounds = WINDOWS[name]
                indices = window_indices(times_ps, bounds)
                summaries[name] = {"registered_window_ps": bounds, "sample_count": len(indices),
                                   "median_phase_rad_unwrapped": statistics.median(unwrapped[i] for i in indices) if indices else None}
            pre = summaries["pre_read"]["median_phase_rad_unwrapped"]
            post = summaries["bvm_state_post"]["median_phase_rad_unwrapped"]
            records.append({"bvm": bvm, "junction": jj, "phase_signal": signal,
                            "windows": summaries,
                            "post_minus_pre_turns_navigation": (post - pre) / (2 * math.pi) if pre is not None and post is not None else None,
                            "classification": "DESCRIPTIVE_PHASE_STATE_ONLY"})
    return records


def voltage_extrema(times_s: list[float], values: dict[str, list[float]]) -> list[dict[str, Any]]:
    times_ps = [time_s * 1e12 for time_s in times_s]
    indices = window_indices(times_ps, WINDOWS["read_response"])
    output = []
    for signal in (pair[2] for pair in JJ_PAIRS):
        selected = max(indices, key=lambda index: abs(values[signal][index]))
        output.append({"signal": signal, "time_ps": times_ps[selected],
                       "voltage_v": values[signal][selected],
                       "semantics": "maximum-absolute stored voltage sample; navigation only, not an event"})
    for signal in ("V(FINAL_OUT)", "V(R_TERM)"):
        selected = max(indices, key=lambda index: abs(values[signal][index]))
        output.append({"signal": signal, "time_ps": times_ps[selected],
                       "voltage_v": values[signal][selected],
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
    _headers, times_s, values, raw_qa = load_selected_raw(raw)
    stage_metrics = stage_window_metrics(times_s, values)
    terminal_metrics = terminal_area_metrics(times_s, values)
    state_metrics = bvm_state_windows(times_s, values)
    extrema = voltage_extrema(times_s, values)
    analysis_dir = directory / "analysis"
    analysis_dir.mkdir(exist_ok=True)
    write_json(analysis_dir / "raw_qa.json", raw_qa)
    write_json(analysis_dir / "metrics.json", {
        "schema": "bvm-bq-cb-gap-mechanical-metrics-v1",
        "run_id": run_id, "mask": metadata["parameters"]["MASK"],
        "registered_windows_ps": WINDOWS, "jj_phase_area_metrics": stage_metrics,
        "terminal_area_metrics": terminal_metrics, "bvm_state_observations": state_metrics,
        "voltage_extrema_navigation_only": extrema,
        "semantics": {"phase_raw_unit": "radians", "turns": "delta_phase_rad/(2*pi), navigation only",
                      "phase_area_crosscheck": "same JJ, same endpoints/window, actual stored grid",
                      "terminal_area": "signed integral divided by Phi0; no event count inferred",
                      "classification": "not performed"},
        "scientific_interpretation_performed": False,
    })
    write_csv(analysis_dir / "stage_metrics.csv",
              ["stage", "window", "phase_signal", "voltage_signal", "status",
               "registered_window_ps", "sample_count", "actual_first_sample_ps", "actual_last_sample_ps",
               "delta_phase_rad", "phase_delta_turns_navigation", "voltage_area_v_s",
               "voltage_area_phi0", "residual_turns_navigation"], stage_metrics)
    write_csv(analysis_dir / "terminal_metrics.csv",
              ["signal", "window", "status", "registered_window_ps", "sample_count",
               "actual_first_sample_ps", "actual_last_sample_ps", "signed_area_v_s", "signed_area_phi0"],
              terminal_metrics)
    write_csv(analysis_dir / "voltage_extrema.csv",
              ["signal", "time_ps", "voltage_v", "semantics"], extrema)
    after = sha256(raw)
    raw_qa["raw_sha256_after"] = after
    raw_qa["raw_unchanged"] = before == after
    raw_qa["status"] = "PASS" if before == after and raw_qa["finite_values"] and raw_qa["strictly_increasing_time"] else "FAIL"
    write_json(analysis_dir / "raw_qa.json", raw_qa)
    qa = {"schema": "bvm-bq-cb-gap-analysis-qa-v1", "run_id": run_id,
          "status": raw_qa["status"], "raw_sha256_before_after": {"before": before, "after": after},
          "required_probe_count": len(probe_signals()), "same_jj_phase_area_windows": True,
          "actual_grid_integration": True, "interpolation_or_resampling": False,
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
