"""Registered exact-grid arithmetic for the one-run T1 clock-only fixture."""

from __future__ import annotations

import hashlib
import csv
import json
import math
import statistics
from pathlib import Path
from typing import Any
from decimal import Decimal

import sys
REPO = Path(__file__).resolve().parents[4]
PLATFORM = Path(__file__).resolve().parents[2] / "bvm-qb-cb-array-topology-v1-20260924"
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(PLATFORM / "scripts"))

from config import parse_quantity, validate_t1_clock  # noqa: E402
from bvmtools.raw import RawTrace, read_csv  # noqa: E402


PHI0_VS = 2.067833848e-15
TARGET_JUNCTIONS = ("B_J2", "B_J3", "B_J7", "B_J9", "B_J11")
CLOCK_SIGNALS = ("V(CLK_RAW)", "V(CLK)")
OUTPUT_SIGNALS = ("V(S)", "V(C)")


def sha256(path: str | Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _unwrap(values: tuple[float, ...]) -> list[float]:
    if not values:
        return []
    result = [values[0]]
    two_pi = 2.0 * math.pi
    for value in values[1:]:
        delta = value - values[len(result) - 1]
        while delta > math.pi:
            delta -= two_pi
        while delta < -math.pi:
            delta += two_pi
        result.append(result[-1] + delta)
    return result


def exact_stored_times(path: str | Path) -> tuple[Decimal, ...]:
    """Read exact decimal timestamps from JoSIM's first CSV column."""
    result: list[Decimal] = []
    with Path(path).open("r", encoding="utf-8", newline="") as stream:
        next(stream, None)  # header
        for line_number, line in enumerate(stream, start=2):
            token = line.partition(",")[0].strip().strip('"')
            try:
                value = Decimal(token)
            except Exception as exc:
                raise ValueError(f"invalid raw time token at line {line_number}: {token!r}") from exc
            if not value.is_finite():
                raise ValueError(f"non-finite raw time token at line {line_number}: {token!r}")
            result.append(value)
    return tuple(result)


def _indices(times: tuple[Decimal, ...], start: Decimal, end: Decimal) -> list[int]:
    return [index for index, value in enumerate(times) if start <= value < end]


def _integral(times: tuple[float, ...], values: tuple[float, ...], indices: list[int]) -> float:
    if len(indices) < 2:
        raise ValueError("registered window has fewer than two stored samples")
    return sum(
        (values[left] + values[right]) * 0.5 * (times[right] - times[left])
        for left, right in zip(indices, indices[1:])
    )


def _range(values: tuple[float, ...], indices: list[int]) -> dict[str, float]:
    selected = [values[index] for index in indices]
    return {"min": min(selected), "max": max(selected), "first": selected[0],
            "last": selected[-1], "peak_to_peak": max(selected) - min(selected),
            "max_abs": max(abs(value) for value in selected)}


def _range_with_time(times: tuple[float, ...], values: tuple[float, ...],
                     indices: list[int]) -> dict[str, float]:
    result = _range(values, indices)
    peak_index = max(indices, key=lambda index: values[index])
    result["peak_time_s"] = times[peak_index]
    return result


def _arrival(times: tuple[float, ...], values: tuple[float, ...], indices: list[int],
             baseline: float) -> dict[str, Any]:
    peak_index = max(indices, key=lambda index: values[index])
    peak = values[peak_index]
    if peak <= baseline:
        return {"status": "NOT_REACHED", "baseline_v": baseline, "peak_v": peak,
                "peak_time_s": times[peak_index], "threshold_fraction": 0.5,
                "threshold_v": None, "stored_crossing_bracket_s": None}
    threshold = baseline + 0.5 * (peak - baseline)
    crossing = next((index for index in indices if values[index] >= threshold), None)
    if crossing is None:
        return {"status": "NOT_REACHED", "baseline_v": baseline, "peak_v": peak,
                "peak_time_s": times[peak_index], "threshold_fraction": 0.5,
                "threshold_v": threshold, "stored_crossing_bracket_s": None}
    prior = max(0, crossing - 1)
    return {"status": "MEASURED_NAVIGATION_MARKER", "baseline_v": baseline,
            "peak_v": peak, "peak_time_s": times[peak_index],
            "threshold_fraction": 0.5, "threshold_v": threshold,
            "stored_crossing_bracket_s": [times[prior], times[crossing]],
            "interpolation_or_resampling": False}


def analyze_trace(trace: RawTrace, values: dict[str, str]) -> dict[str, Any]:
    stop = parse_quantity(values["STOP"], label="STOP")
    clock = validate_t1_clock(values, stop)
    exact_times = exact_stored_times(trace.path)
    if len(exact_times) != len(trace.time):
        raise ValueError("exact stored-time row count disagrees with parsed raw trace")
    start = clock["start_s"]
    period = clock["period_s"]
    pulse_duration = clock["rise_s"] + clock["width_s"] + clock["fall_s"]
    preclock_start = start - Decimal("20e-12")
    preclock_end = start
    cycle_starts = [start + index * period for index in range(4)]
    required = {"V(CLK_RAW)", "V(CLK)", "I(R_TRIG_CLK)", "V(S)", "V(C)"}
    required.update(f"{q}({jj}|XT1)" for jj in TARGET_JUNCTIONS for q in ("P", "V"))
    missing = sorted(required - set(trace.headers))
    if missing:
        raise ValueError(f"raw is missing registered clock-only probes: {missing}")
    if trace.duplicate_columns:
        raise ValueError(f"raw contains duplicate labels: {trace.duplicate_columns}")

    times = trace.time
    phase = {jj: _unwrap(trace.column(f"P({jj}|XT1)")) for jj in TARGET_JUNCTIONS}
    columns = {label: trace.column(label) for label in required}
    pre_indices = _indices(exact_times, preclock_start, preclock_end)
    if len(pre_indices) < 2:
        raise ValueError("pre-clock window [150,170) ps has fewer than two stored samples")
    preclock = {
        "window_s": [float(preclock_start), float(preclock_end)], "boundary_rule": "[start,end)",
        "sample_count": len(pre_indices), "first_sample_s": times[pre_indices[0]],
        "last_sample_s": times[pre_indices[-1]],
        "signals": {label: _range(columns[label], pre_indices)
                    for label in (*CLOCK_SIGNALS, *OUTPUT_SIGNALS)},
        "junction_phase": {
            jj: {"first_rad": phase[jj][pre_indices[0]],
                 "last_rad": phase[jj][pre_indices[-1]],
                 "delta_rad": phase[jj][pre_indices[-1]] - phase[jj][pre_indices[0]],
                 "min_rad": min(phase[jj][i] for i in pre_indices),
                 "max_rad": max(phase[jj][i] for i in pre_indices)}
            for jj in TARGET_JUNCTIONS
        },
        "junction_voltage": {
            jj: _range(columns[f"V({jj}|XT1)"], pre_indices)
            for jj in TARGET_JUNCTIONS
        },
    }

    cycles: list[dict[str, Any]] = []
    for index, cycle_start in enumerate(cycle_starts, start=1):
        cycle_end = cycle_start + period
        selected = _indices(exact_times, cycle_start, cycle_end)
        if len(selected) < 2:
            raise ValueError(f"cycle {index} has fewer than two stored samples")
        prior_start = cycle_start - Decimal("20e-12")
        prior_end = cycle_start
        prior_indices = _indices(exact_times, prior_start, prior_end)
        clk_base = statistics.median(columns["V(CLK)"][i] for i in prior_indices)
        raw_base = statistics.median(columns["V(CLK_RAW)"][i] for i in prior_indices)
        clock = {
            "source_node": {"signal": "V(CLK_RAW)",
                            **_range_with_time(times, columns["V(CLK_RAW)"], selected)},
            "t1_input": {"signal": "V(CLK)",
                         **_range_with_time(times, columns["V(CLK)"], selected)},
            "source_arrival": _arrival(times, columns["V(CLK_RAW)"], selected, raw_base),
            "input_arrival": _arrival(times, columns["V(CLK)"], selected, clk_base),
            "series_current": {"signal": "I(R_TRIG_CLK)",
                               **_range_with_time(times, columns["I(R_TRIG_CLK)"], selected)},
        }
        junction_metrics: dict[str, Any] = {}
        for jj in TARGET_JUNCTIONS:
            phase_values = phase[jj]
            voltage = columns[f"V({jj}|XT1)"]
            phase_delta = phase_values[selected[-1]] - phase_values[selected[0]]
            area = _integral(times, voltage, selected)
            turns = phase_delta / (2.0 * math.pi)
            area_phi0 = area / PHI0_VS
            junction_metrics[jj] = {
                "phase_signal": f"P({jj}|XT1)", "voltage_signal": f"V({jj}|XT1)",
                "sample_count": len(selected),
                "first_sample_s": times[selected[0]], "last_sample_s": times[selected[-1]],
                "phase_delta_rad": phase_delta, "phase_delta_turns_rad_over_2pi": turns,
                "voltage_area_v_s_same_stored_rows": area,
                "voltage_area_phi0_arithmetic": area_phi0,
                "phase_minus_area_turns_arithmetic": turns - area_phi0,
                "phase_unwrapped_once_over_full_trace": True,
                "interpolation_or_resampling": False,
            }
        outputs = {}
        for label in OUTPUT_SIGNALS:
            values_for_signal = columns[label]
            outputs[label] = {
                **_range(values_for_signal, selected),
                "voltage_area_v_s": _integral(times, values_for_signal, selected),
                "sample_count": len(selected),
                "first_sample_s": times[selected[0]],
                "last_sample_s": times[selected[-1]],
            }
        tail_start = cycle_start + pulse_duration
        tail_indices = _indices(exact_times, tail_start, cycle_end)
        if len(tail_indices) < 2:
            raise ValueError(f"cycle {index} inter-pulse tail has fewer than two stored samples")
        tail = {
            "window_s": [float(tail_start), float(cycle_end)], "boundary_rule": "[start,end)",
            "sample_count": len(tail_indices),
            "signals": {label: _range(columns[label], tail_indices)
                        for label in (*CLOCK_SIGNALS, *OUTPUT_SIGNALS)},
            "junction_phase_delta_rad": {
                jj: phase[jj][tail_indices[-1]] - phase[jj][tail_indices[0]]
                for jj in TARGET_JUNCTIONS
            },
        }
        cycles.append({
            "cycle_index": index, "scheduled_start_s": float(cycle_start),
            "scheduled_end_s": float(cycle_end), "boundary_rule": "[start,end)",
            "sample_count": len(selected),
            "first_sample_s": times[selected[0]], "last_sample_s": times[selected[-1]],
            "clock": clock, "outputs": outputs, "junctions": junction_metrics,
            "inter_pulse_tail": tail,
        })

    dt = trace.dt
    return {
        "schema": "t1-periodic-clock-cycle-metrics-v1",
        "status": "DERIVED_ARITHMETIC_ONLY",
        "experiment_id": "t1-periodic-clock-20ghz-20260928",
        "clock_parameters": {key: values[key] for key in (
            "T1_CLK_MODE", "T1_CLK_START", "T1_CLK_PERIOD", "T1_CLK_AMPLITUDE",
            "T1_CLK_RISE", "T1_CLK_WIDTH", "T1_CLK_FALL", "T1_CLK_R_SERIES",
        )},
        "phi0_v_s_for_arithmetic": PHI0_VS,
        "sample_count": trace.sample_count,
        "time_range_s": [times[0], times[-1]],
        "dt_min_s": min(dt) if dt else None, "dt_max_s": max(dt) if dt else None,
        "uniform_time_grid": trace.qa()["uniform_time_grid"],
        "raw_sha256": sha256(trace.path),
        "preclock_static_state": preclock,
        "cycle_window_definition": "four successive half-open periods [start+k*period,start+(k+1)*period)",
        "arrival_marker_definition": (
            "first stored sample at or above baseline + 0.5*(cycle peak-baseline); "
            "baseline is median of immediately preceding quiet window; bracket only, no interpolation"
        ),
        "integration_method": "trapezoid over actual stored time rows selected by the registered half-open window",
        "raw_phase_units": "radians",
        "phase_turns_definition": "independent full-trace unwrap then delta/(2*pi); not an SFQ count",
        "interpolation_or_resampling": False,
        "scientific_interpretation_performed": False,
        "cycles": cycles,
    }


def analyze_file(raw_path: str | Path, values: dict[str, str]) -> dict[str, Any]:
    trace = read_csv(raw_path)
    return analyze_trace(trace, values)


def write_analysis(run_dir: str | Path) -> dict[str, Any]:
    root = Path(run_dir).resolve()
    raw = root / "raw.csv"
    config_path = root / "USER_CASE.snapshot.json"
    raw_before = sha256(raw)
    values = json.loads(config_path.read_text(encoding="utf-8"))
    trace = read_csv(raw)
    metrics = analyze_trace(trace, values)
    raw_after = sha256(raw)
    if raw_before != raw_after:
        raise RuntimeError("raw changed during clock metrics analysis")
    analysis = root / "analysis"
    analysis.mkdir(parents=True, exist_ok=True)
    qa = {
        "schema": "t1-clock-only-raw-qa-v1", **trace.qa(),
        "sha256": raw_before, "sha256_after_analysis": raw_after,
        "raw_immutable": raw_before == raw_after,
        "required_signal_count": len(trace.headers) - 1,
        "probe_profile": "debug", "status": "PASS",
        "scientific_interpretation_performed": False,
    }
    metrics["raw_sha256"] = raw_before
    (analysis / "raw_qa.json").write_text(
        json.dumps(qa, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (analysis / "clock_cycle_metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    transformations = {
        "schema": "t1-clock-only-transformation-registry-v1",
        "raw_sha256": raw_before,
        "raw_modified": False,
        "interpolation": False, "resampling": False, "smoothing": False,
        "scaling": False, "time_shift": False, "sign_correction": False,
        "operations": [
            {"operation": "full-trace phase unwrap", "signals": [
                f"P({jj}|XT1)" for jj in TARGET_JUNCTIONS],
             "purpose": "same-window endpoint phase arithmetic only"},
            {"operation": "half-open stored-row selection using exact decimal raw-time tokens",
             "windows": [
                metrics["preclock_static_state"]["window_s"],
                *[[cycle["scheduled_start_s"], cycle["scheduled_end_s"]]
                  for cycle in metrics["cycles"]]]},
            {"operation": "trapezoid integration", "time_source": "raw.csv time column",
             "signal_pairs": [
                 {"phase": f"P({jj}|XT1)", "voltage": f"V({jj}|XT1)"}
                 for jj in TARGET_JUNCTIONS] + [
                 {"voltage": signal} for signal in OUTPUT_SIGNALS]},
            {"operation": "plot window row selection using exact decimal raw-time tokens",
             "raw_rows_interpolated": False},
        ],
        "scientific_interpretation_performed": False,
    }
    (analysis / "transformation_registry.json").write_text(
        json.dumps(transformations, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")
    rows: list[dict[str, Any]] = []
    for cycle in metrics["cycles"]:
        clock = cycle["clock"]
        for label in ("V(CLK_RAW)", "V(CLK)", "I(R_TRIG_CLK)"):
            measurement = clock["source_node"] if label == "V(CLK_RAW)" else (
                clock["t1_input"] if label == "V(CLK)" else clock["series_current"]
            )
            arrival = (clock["source_arrival"] if label == "V(CLK_RAW)"
                       else clock["input_arrival"] if label == "V(CLK)" else {})
            bracket = arrival.get("stored_crossing_bracket_s")
            rows.append({
                "cycle_index": cycle["cycle_index"], "signal_kind": "clock", "signal": label,
                "window_start_s": cycle["scheduled_start_s"],
                "window_end_s": cycle["scheduled_end_s"],
                "first_sample_s": cycle["first_sample_s"], "last_sample_s": cycle["last_sample_s"],
                "sample_count": cycle["sample_count"],
                "value_min": measurement.get("min"), "value_max": measurement.get("max"),
                "peak_to_peak": measurement.get("peak_to_peak"),
                "peak_time_s": measurement.get("peak_time_s"),
                "baseline_v": arrival.get("baseline_v"),
                "arrival_threshold_v": arrival.get("threshold_v"),
                "arrival_bracket_start_s": bracket[0] if bracket else None,
                "arrival_bracket_end_s": bracket[1] if bracket else None,
            })
        for label, measurement in cycle["outputs"].items():
            rows.append({
                "cycle_index": cycle["cycle_index"], "signal_kind": "output", "signal": label,
                "window_start_s": cycle["scheduled_start_s"],
                "window_end_s": cycle["scheduled_end_s"],
                "first_sample_s": cycle["first_sample_s"], "last_sample_s": cycle["last_sample_s"],
                "sample_count": cycle["sample_count"],
                "value_min": measurement["min"], "value_max": measurement["max"],
                "peak_to_peak": measurement["peak_to_peak"],
                "voltage_area_v_s": measurement["voltage_area_v_s"],
            })
        for jj, measurement in cycle["junctions"].items():
            rows.append({
                "cycle_index": cycle["cycle_index"], "signal_kind": "junction", "signal": jj,
                "window_start_s": cycle["scheduled_start_s"],
                "window_end_s": cycle["scheduled_end_s"],
                "first_sample_s": measurement["first_sample_s"],
                "last_sample_s": measurement["last_sample_s"],
                "sample_count": measurement["sample_count"],
                "phase_delta_rad": measurement["phase_delta_rad"],
                "phase_delta_turns_rad_over_2pi": measurement["phase_delta_turns_rad_over_2pi"],
                "voltage_area_v_s": measurement["voltage_area_v_s_same_stored_rows"],
                "voltage_area_phi0_arithmetic": measurement["voltage_area_phi0_arithmetic"],
                "phase_minus_area_turns_arithmetic": measurement["phase_minus_area_turns_arithmetic"],
            })
    columns = [
        "cycle_index", "signal_kind", "signal", "window_start_s", "window_end_s",
        "first_sample_s", "last_sample_s", "sample_count", "value_min", "value_max",
        "peak_to_peak", "peak_time_s", "baseline_v", "arrival_threshold_v",
        "arrival_bracket_start_s", "arrival_bracket_end_s", "phase_delta_rad",
        "phase_delta_turns_rad_over_2pi", "voltage_area_v_s", "voltage_area_phi0_arithmetic",
        "phase_minus_area_turns_arithmetic",
    ]
    with (analysis / "clock_cycle_metrics.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return {"raw_sha256": raw_before, "raw_qa": qa, "metrics": metrics}


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Recompute exact-grid CLK-only metrics from one immutable raw")
    parser.add_argument("run_dir")
    args = parser.parse_args()
    try:
        result = write_analysis(args.run_dir)
        print(json.dumps({"status": "PASS", "raw_sha256": result["raw_sha256"],
                          "sample_count": result["raw_qa"]["sample_count"],
                          "cycle_count": len(result["metrics"]["cycles"]),
                          "scientific_interpretation_performed": False}, indent=2))
        return 0
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
