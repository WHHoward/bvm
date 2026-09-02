#!/usr/bin/env python3
"""Existing-raw-only operating-point decomposition for the scaled QB.

This script intentionally never invokes JoSIM.  It reads the registered G/I0/P0
raw traces, independently re-derives the QB KCL residuals and fixed-window
signatures, and uses Q45/Q68 only as scalar historical supporting references.
The generated HTML is delegated to the repository's canonical josim-plot2.py
renderer; the plot is descriptive and is not a physical Gate.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Sequence

import yaml

REPO = Path(__file__).resolve().parents[4]
ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "analysis"
PLOTS = ROOT / "plots"
CONFIG_PATH = ROOT / "experiment.yaml"
PLOTTER = REPO / "scripts" / "josim-plot2.py"
sys.path.insert(0, str(REPO / "scripts"))

from bvmtools.compare import compare_windowed_series, exact_time_grid_identity  # noqa: E402
from bvmtools.phase import TAU, continuous_unwrap, window_indices  # noqa: E402
from bvmtools.provenance import file_snapshot, git_snapshot, sha256_file  # noqa: E402
from bvmtools.raw import RawTrace, read_csv  # noqa: E402
from bvmtools.sfq import StrictLocalEventSpec, strict_event_summary  # noqa: E402
from bvmtools.waveform import trapezoid_integral  # noqa: E402


WINDOWS_PS = {
    "W2_pre_read_idle": (80.0, 90.0),
    "W3_read": (95.0, 110.0),
    "W4_post_read_observation": (110.0, 130.0),
    "node4_strict_activity": (95.0, 115.0),
    "node4_strict_post": (115.0, 130.0),
    "node4_strict_tail": (125.0, 130.0),
}
KCL_ABS_TOL_UA = 0.001
CURRENT_FLOOR_UA = 1.0
CURRENT_RELATIVE = 0.10
PHASE_THRESHOLD_TURNS = 0.05
PARTITION_THRESHOLD = 0.10
PARTITION_DENOMINATOR_FLOOR_UA = 5.0
TIE_RESOLUTION_PS = 0.0125

QB_CURRENT_SIGNALS = [
    "I(LIN|XBQ)",
    "I(BJS|XBQ)",
    "I(BJL1|XBQ)",
    "I(RJ1|XBQ)",
    "I(L1|XBQ)",
    "I(RB|XBQ)",
    "I(L2|XBQ)",
    "I(BJL2|XBQ)",
    "I(RJ2|XBQ)",
    "I(L0|XBQ)",
    "I(R_LOAD)",
    "I(I_IBIAS)",
]
QB_PHASE_SIGNALS = ["P(BJS|XBQ)", "P(BJL1|XBQ)", "P(BJL2|XBQ)"]
QB_VOLTAGE_SIGNALS = ["V(BJS|XBQ)", "V(BJL1|XBQ)", "V(BJL2|XBQ)"]
SOURCE_SIGNALS = [
    "I(B_LD1)",
    "I(B_LD12)",
    "I(L_SL|XBVM1)",
    "V(SL1)",
    "P(B_JS1|XBVM1)",
    "P(B_JS2|XBVM1)",
    "P(B_JM2|XBVM1)",
]
Q_SIGNALS = [
    "I(Lin|XBQ)",
    "I(BJS|XBQ)",
    "I(BJL1|XBQ)",
    "I(RJ1|XBQ)",
    "I(L1|XBQ)",
    "I(RB|XBQ)",
    "I(L2|XBQ)",
    "I(BJL2|XBQ)",
    "I(RJ2|XBQ)",
    "I(L0|XBQ)",
]
Q_PHASE_SIGNALS = ["P(BJS|XBQ)", "P(BJL1|XBQ)", "P(BJL2|XBQ)"]
Q_VOLTAGE_SIGNALS = ["V(BJS|XBQ)", "V(BJL1|XBQ)", "V(BJL2|XBQ)"]


def fail(message: str) -> None:
    raise RuntimeError(message)


def generated_at() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO.resolve()).as_posix()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_config() -> dict[str, Any]:
    value = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("id") != "QB_NODE2_OPERATING_POINT_DECOMPOSITION_V1":
        fail("unexpected experiment.yaml")
    if value.get("mode") != "EXISTING_RAW_ONLY" or value.get("no_new_josim") is not True:
        fail("analysis boundary is not existing-raw-only")
    return value


def resolve(path_text: str) -> Path:
    path = Path(path_text)
    if not path.is_absolute():
        path = REPO / path
    if not path.is_file():
        fail(f"registered file is missing: {path}")
    return path.resolve()


def header_sha256(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.sha256(handle.readline().rstrip(b"\r\n")).hexdigest()


def registered_hash(path: Path, *, q0_root: Path | None = None) -> dict[str, Any]:
    actual = sha256_file(path)
    sidecar = Path(str(path) + ".sha256")
    sources: list[tuple[Path, str]] = []
    if sidecar.is_file():
        sources.append((sidecar, sidecar.read_text(encoding="utf-8")))
    if q0_root is not None:
        sums = q0_root / "analysis" / "SHA256SUMS.txt"
        if sums.is_file():
            sources.append((sums, sums.read_text(encoding="utf-8")))
    matches: list[dict[str, str]] = []
    q0_relative = None
    if q0_root is not None:
        try:
            q0_relative = path.resolve().relative_to(q0_root.resolve()).as_posix()
        except ValueError:
            q0_relative = None
    for source, text in sources:
        for line in text.splitlines():
            fields = line.split()
            if len(fields) < 2:
                continue
            candidate = fields[-1].lstrip("./")
            try:
                candidate_abs = (source.parent / candidate).resolve()
            except OSError:
                continue
            exact_q0_match = (
                q0_relative is not None
                and source.name == "SHA256SUMS.txt"
                and candidate == q0_relative
            )
            if candidate_abs == path.resolve() or exact_q0_match:
                matches.append({"source": rel(source), "declared_sha256": fields[0]})
    result: dict[str, Any] = {
        "sha256": actual,
        "bytes": path.stat().st_size,
        "header_sha256": header_sha256(path),
        "registered_hash_matches": matches,
        "registered_hash_verified": bool(matches) and all(item["declared_sha256"].casefold() == actual.casefold() for item in matches),
    }
    if sidecar.is_file():
        result["sidecar"] = rel(sidecar)
    return result


def raw_record(path: Path, trace: RawTrace, *, q0_root: Path | None = None) -> dict[str, Any]:
    qa = trace.qa()
    record = registered_hash(path, q0_root=q0_root)
    record.update({
        "path": rel(path),
        "sample_count": trace.sample_count,
        "time_start_ps": trace.time[0] * 1.0e12,
        "time_end_ps": trace.time[-1] * 1.0e12,
        "dt_min_ps": min(trace.dt) * 1.0e12 if trace.dt else None,
        "dt_max_ps": max(trace.dt) * 1.0e12 if trace.dt else None,
        "qa": qa,
    })
    return record


def load_traces(config: dict[str, Any]) -> tuple[dict[str, RawTrace], dict[str, Path], dict[str, Any]]:
    paths = {
        key: resolve(value["raw"])
        for key, value in config["primary_cases"].items()
    }
    q0_root = REPO / "test/exploration/qb-q0-standalone-current-quantized-event-20260824"
    paths.update({key: resolve(value["raw"]) for key, value in config["supporting_cases"].items()})
    traces = {key: read_csv(path) for key, path in paths.items()}
    for key, trace in traces.items():
        if trace.qa().get("status") != "VALID":
            fail(f"raw QA failed: {key}")
        if key in {"G", "I0", "P0"} and not trace.duplicate_columns and key != "I0":
            fail(f"expected source duplicate columns not found: {key}")
    if not exact_time_grid_identity(traces["G"].time, traces["I0"].time):
        fail("G and I0 time grids differ")
    if not exact_time_grid_identity(traces["G"].time, traces["P0"].time):
        fail("G and P0 time grids differ")
    records = {
        key: raw_record(path, traces[key], q0_root=q0_root if key in {"Q45", "Q68"} else None)
        for key, path in paths.items()
    }
    return traces, paths, records


def occurrence_for(signal: str) -> int | None:
    if signal in {"I(B_LD1)", "I(B_LD12)"}:
        return 0
    return None


def selected(trace: RawTrace, signal: str) -> tuple[float, ...]:
    try:
        result = trace.column(signal, occurrence=occurrence_for(signal))
    except (KeyError, IndexError, ValueError) as exc:
        fail(f"cannot select exact signal {signal}: {exc}")
    if not isinstance(result, tuple) or (result and isinstance(result[0], tuple)):
        fail(f"bad selected signal {signal}")
    return tuple(float(value) for value in result)


def indices(trace: RawTrace, window_ps: Sequence[float]) -> tuple[int, ...]:
    return window_indices(trace.time, float(window_ps[0]) * 1.0e-12, float(window_ps[1]) * 1.0e-12)


def percentile(values: Sequence[float], fraction: float) -> float:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return float("nan")
    rank = (len(ordered) - 1) * fraction
    low = math.floor(rank)
    high = math.ceil(rank)
    if low == high:
        return ordered[low]
    return ordered[low] + (ordered[high] - ordered[low]) * (rank - low)


def zero_crossings(values: Sequence[float]) -> int:
    previous = 0
    count = 0
    for value in values:
        sign = 1 if value > 0.0 else -1 if value < 0.0 else 0
        if sign == 0:
            continue
        if previous and sign != previous:
            count += 1
        previous = sign
    return count


def current_stats(trace: RawTrace, signal: str, window_ps: Sequence[float], *, q_case: bool = False) -> dict[str, Any]:
    label = signal if not q_case else signal.replace("Lin", "LIN")
    values = selected(trace, signal)
    ii = indices(trace, window_ps)
    times = [trace.time[index] for index in ii]
    amps = [values[index] for index in ii]
    if len(amps) < 2:
        fail(f"too few samples for current window: {signal} {window_ps}")
    display = [value * 1.0e6 for value in amps]
    peak = max(range(len(display)), key=display.__getitem__)
    minimum = min(range(len(display)), key=display.__getitem__)
    signed = trapezoid_integral(amps, times) * 1.0e18
    positive = trapezoid_integral([max(value, 0.0) for value in amps], times) * 1.0e18
    negative = trapezoid_integral([min(value, 0.0) for value in amps], times) * 1.0e18
    result = {
        "signal": label,
        "window_ps": [float(window_ps[0]), float(window_ps[1])],
        "sample_count": len(display),
        "mean_uA": sum(display) / len(display),
        "median_uA": percentile(display, 0.5),
        "rms_uA": math.sqrt(sum(value * value for value in display) / len(display)),
        "minimum_uA": min(display),
        "maximum_uA": max(display),
        "max_abs_uA": max(abs(value) for value in display),
        "p2p_uA": max(display) - min(display),
        "signed_integral_uA_ps": signed,
        "positive_area_uA_ps": positive,
        "negative_area_uA_ps": negative,
        "zero_crossing_count": zero_crossings(display),
        "positive_occupancy": sum(value > 0.0 for value in display) / len(display),
        "negative_occupancy": sum(value < 0.0 for value in display) / len(display),
        "zero_occupancy": sum(value == 0.0 for value in display) / len(display),
        "maximum_time_ps": trace.time[ii[peak]] * 1.0e12,
        "minimum_time_ps": trace.time[ii[minimum]] * 1.0e12,
        "first_sample_ps": trace.time[ii[0]] * 1.0e12,
        "last_sample_ps": trace.time[ii[-1]] * 1.0e12,
    }
    return result


def phase_stats(trace: RawTrace, signal: str, window_ps: Sequence[float]) -> dict[str, Any]:
    raw = selected(trace, signal)
    unwrapped = continuous_unwrap(raw)
    ii = indices(trace, window_ps)
    values = [unwrapped[index] / TAU for index in ii]
    if len(values) < 2:
        fail(f"too few samples for phase window: {signal} {window_ps}")
    return {
        "signal": signal,
        "window_ps": [float(window_ps[0]), float(window_ps[1])],
        "sample_count": len(values),
        "mean_turns": sum(values) / len(values),
        "median_turns": percentile(values, 0.5),
        "rms_turns": math.sqrt(sum(value * value for value in values) / len(values)),
        "minimum_turns": min(values),
        "maximum_turns": max(values),
        "p2p_turns": max(values) - min(values),
        "endpoint_delta_turns": values[-1] - values[0],
        "first_sample_ps": trace.time[ii[0]] * 1.0e12,
        "last_sample_ps": trace.time[ii[-1]] * 1.0e12,
    }


def voltage_stats(trace: RawTrace, signal: str, window_ps: Sequence[float]) -> dict[str, Any]:
    values = selected(trace, signal)
    ii = indices(trace, window_ps)
    vals = [values[index] * 1.0e3 for index in ii]
    return {
        "signal": signal,
        "window_ps": [float(window_ps[0]), float(window_ps[1])],
        "sample_count": len(vals),
        "mean_mV": sum(vals) / len(vals),
        "rms_mV": math.sqrt(sum(value * value for value in vals) / len(vals)),
        "minimum_mV": min(vals),
        "maximum_mV": max(vals),
        "p2p_mV": max(vals) - min(vals),
    }


def exact_compare(trace_a: RawTrace, trace_b: RawTrace, signal_a: str, signal_b: str, window_ps: Sequence[float], *, unit: str) -> dict[str, Any]:
    if not exact_time_grid_identity(trace_a.time, trace_b.time):
        fail(f"exact comparison requested on different time grids: {signal_a}/{signal_b}")
    if unit == "uA":
        scale = 1.0e6
    elif unit == "turns":
        scale = 1.0 / TAU
    else:
        scale = 1.0
    values_a = selected(trace_a, signal_a)
    values_b = selected(trace_b, signal_b)
    if unit == "turns":
        values_a = continuous_unwrap(values_a)
        values_b = continuous_unwrap(values_b)
    return compare_windowed_series(
        trace_a.time,
        values_a,
        trace_b.time,
        values_b,
        (float(window_ps[0]) * 1.0e-12, float(window_ps[1]) * 1.0e-12),
        value_scale=scale,
        unit=unit,
        include_correlation=True,
    )


def kcl_metrics(trace: RawTrace, window_ps: Sequence[float], *, q_case: bool = False) -> dict[str, Any]:
    suffix = "" if not q_case else "_q"
    names = {
        "lin": "I(LIN|XBQ)" if not q_case else "I(Lin|XBQ)",
        "bjs": "I(BJS|XBQ)",
        "bjl1": "I(BJL1|XBQ)",
        "rj1": "I(RJ1|XBQ)",
        "l1": "I(L1|XBQ)",
        "rb": "I(RB|XBQ)",
        "l2": "I(L2|XBQ)",
        "bjl2": "I(BJL2|XBQ)",
        "rj2": "I(RJ2|XBQ)",
        "l0": "I(L0|XBQ)",
    }
    arrays = {key: selected(trace, signal) for key, signal in names.items()}
    ii = indices(trace, window_ps)
    residuals = {
        "input_node": [arrays["lin"][index] - arrays["bjs"][index] for index in ii],
        "node2": [arrays["bjs"][index] - arrays["bjl1"][index] - arrays["rj1"][index] - arrays["l1"][index] for index in ii],
        "node3": [arrays["l1"][index] + arrays["rb"][index] - arrays["l2"][index] for index in ii],
        "node4": [arrays["l2"][index] - arrays["bjl2"][index] - arrays["rj2"][index] - arrays["l0"][index] for index in ii],
    }
    result: dict[str, Any] = {
        "window_ps": [float(window_ps[0]), float(window_ps[1])],
        "sample_count": len(ii),
        "absolute_tolerance_uA": KCL_ABS_TOL_UA,
        "equations": {
            "input_node": "I(LIN) - I(BJS)",
            "node2": "I(BJS) - I(BJL1) - I(RJ1) - I(L1)",
            "node3": "I(L1) + I(RB) - I(L2)",
            "node4": "I(L2) - I(BJL2) - I(RJ2) - I(L0)",
        },
        "residuals": {},
    }
    all_pass = True
    for key, values in residuals.items():
        scaled = [value * 1.0e6 for value in values]
        record = {
            "max_abs_uA": max(abs(value) for value in scaled),
            "p95_abs_uA": percentile([abs(value) for value in scaled], 0.95),
            "rms_uA": math.sqrt(sum(value * value for value in scaled) / len(scaled)),
        }
        record["pass"] = record["max_abs_uA"] <= KCL_ABS_TOL_UA
        all_pass = all_pass and bool(record["pass"])
        result["residuals"][key] = record
    result["status"] = "KCL_CONSISTENT" if all_pass else "MECHANISM_ANALYSIS_INVALID"
    return result


def case_window_metrics(trace: RawTrace) -> dict[str, Any]:
    result: dict[str, Any] = {"currents": {}, "phases": {}, "voltages": {}}
    for window_name, window in WINDOWS_PS.items():
        result["currents"][window_name] = {signal: current_stats(trace, signal, window) for signal in QB_CURRENT_SIGNALS}
        result["phases"][window_name] = {signal: phase_stats(trace, signal, window) for signal in QB_PHASE_SIGNALS}
        result["voltages"][window_name] = {signal: voltage_stats(trace, signal, window) for signal in QB_VOLTAGE_SIGNALS}
    return result


def source_metrics(trace: RawTrace) -> dict[str, Any]:
    result: dict[str, Any] = {"currents": {}, "phases": {}, "voltages": {}}
    for window_name, window in WINDOWS_PS.items():
        result["currents"][window_name] = {
            signal: current_stats(trace, signal, window)
            for signal in ("I(B_LD1)", "I(B_LD12)", "I(L_SL|XBVM1)")
        }
        result["phases"][window_name] = {
            signal: phase_stats(trace, signal, window)
            for signal in ("P(B_JS1|XBVM1)", "P(B_JS2|XBVM1)", "P(B_JM2|XBVM1)")
        }
        result["voltages"][window_name] = {"V(SL1)": voltage_stats(trace, "V(SL1)", window)}
    return result


def resistor_proxy(trace: RawTrace, signal: str, resistance_ohm: float, window_ps: Sequence[float]) -> dict[str, Any]:
    values = selected(trace, signal)
    ii = indices(trace, window_ps)
    times = [trace.time[index] for index in ii]
    powers = [resistance_ohm * values[index] ** 2 for index in ii]
    return {
        "resistor_ohm": resistance_ohm,
        "mean_power_W": sum(powers) / len(powers),
        "rms_power_W": math.sqrt(sum(value * value for value in powers) / len(powers)),
        "energy_fJ": trapezoid_integral(powers, times) * 1.0e15,
        "interpretation": "resistor dissipation proxy only; not total QB power",
    }


def operating_point(trace: RawTrace) -> dict[str, Any]:
    w2 = WINDOWS_PS["W2_pre_read_idle"]
    currents = {signal: current_stats(trace, signal, w2) for signal in QB_CURRENT_SIGNALS}
    phases = {signal: phase_stats(trace, signal, w2) for signal in QB_PHASE_SIGNALS}
    bjs = currents["I(BJS|XBQ)"]["mean_uA"]
    partition: dict[str, Any] = {"denominator_signal": "I(BJS|XBQ)", "denominator_mean_uA": bjs}
    if abs(bjs) < PARTITION_DENOMINATOR_FLOOR_UA:
        partition.update({"status": "NOT_DEFINED_NEAR_ZERO_DENOMINATOR", "fractions": None})
    else:
        partition.update({
            "status": "VALID",
            "fractions": {
                "BJL1": currents["I(BJL1|XBQ)"]["mean_uA"] / bjs,
                "RJ1": currents["I(RJ1|XBQ)"]["mean_uA"] / bjs,
                "L1": currents["I(L1|XBQ)"]["mean_uA"] / bjs,
            },
        })
    l1 = currents["I(L1|XBQ)"]["mean_uA"]
    rb = currents["I(RB|XBQ)"]["mean_uA"]
    l2 = currents["I(L2|XBQ)"]["mean_uA"]
    if abs(l2) < PARTITION_DENOMINATOR_FLOOR_UA:
        bias = {"status": "NOT_DEFINED_NEAR_ZERO_DENOMINATOR", "fractions": None}
    else:
        bias = {
            "status": "VALID",
            "fractions_of_L2": {"L1": l1 / l2, "RB": rb / l2},
            "signed_sum": (l1 + rb) / l2,
            "relationship": "L1_opposes_RB" if l1 * rb < 0.0 else "L1_constructive_with_RB",
        }
    return {"currents": currents, "phases": phases, "node2_partition": partition, "node3_bias_composition": bias}


def node2_signature(trace: RawTrace) -> dict[str, Any]:
    w3 = WINDOWS_PS["W3_read"]
    currents = {signal: current_stats(trace, signal, w3) for signal in ["I(BJS|XBQ)", "I(BJL1|XBQ)", "I(RJ1|XBQ)", "I(L1|XBQ)"]}
    phases = {signal: phase_stats(trace, signal, w3) for signal in QB_PHASE_SIGNALS}
    return {
        "BJs_drive": {
            "current": currents["I(BJS|XBQ)"],
            "phase": phases["P(BJS|XBQ)"],
            "interpretation": "local BJs current/phase activity; phase turns are not SFQ counts",
        },
        "BJL1_branch": {"current": currents["I(BJL1|XBQ)"], "phase": phases["P(BJL1|XBQ)"]},
        "RJ1_branch": {
            "current": currents["I(RJ1|XBQ)"],
            "dissipation_proxy": resistor_proxy(trace, "I(RJ1|XBQ)", 33.0, w3),
        },
        "L1_branch": {
            "current": currents["I(L1|XBQ)"],
            "phase": phases["P(BJL1|XBQ)"],
            "sign_summary": {
                "positive_occupancy": currents["I(L1|XBQ)"]["positive_occupancy"],
                "negative_occupancy": currents["I(L1|XBQ)"]["negative_occupancy"],
                "zero_crossing_count": currents["I(L1|XBQ)"]["zero_crossing_count"],
            },
        },
    }


def node3_analysis(trace_i0: RawTrace, trace_p0: RawTrace) -> dict[str, Any]:
    w2 = WINDOWS_PS["W2_pre_read_idle"]
    w3 = WINDOWS_PS["W3_read"]
    cases: dict[str, Any] = {}
    for key, trace in (("I0", trace_i0), ("P0", trace_p0)):
        w2c = {signal: current_stats(trace, signal, w2) for signal in ["I(L1|XBQ)", "I(RB|XBQ)", "I(L2|XBQ)"]}
        w3c = {signal: current_stats(trace, signal, w3) for signal in ["I(L1|XBQ)", "I(RB|XBQ)", "I(L2|XBQ)"]}
        cases[key] = {
            "W2": w2c,
            "W3": w3c,
            "bias_relationship": "L1_opposes_RB" if w2c["I(L1|XBQ)"]["mean_uA"] * w2c["I(RB|XBQ)"]["mean_uA"] < 0 else "L1_constructive_with_RB",
            "RB_near_35uA": abs(w2c["I(RB|XBQ)"]["mean_uA"] - 35.0) <= 0.1,
        }
    differences = {
        signal: exact_compare(trace_i0, trace_p0, signal, signal, w3, unit="uA")
        for signal in ["I(L1|XBQ)", "I(RB|XBQ)", "I(L2|XBQ)"]
    }
    return {"cases": cases, "I0_vs_P0_exact_grid_W3": differences}


def strict_result(trace: RawTrace, raw_hash: str, case_key: str, metric_hash: str) -> dict[str, Any]:
    spec = StrictLocalEventSpec.from_mapping({
        "id": "qb-node2-operating-point-decomposition-bjl2-v1",
        "scope": "task-local",
        "status": "FROZEN",
        "mapping_status": "VERIFIED_FROM_BQ_SUBCIRCUIT_AND_DIRECT_COLUMNS",
        "phase_column": "P(BJL2|XBQ)",
        "voltage_column": "V(BJL2|XBQ)",
        "branch_endpoints": "BJL2 4 -> 0; direct JoSIM branch voltage",
        "voltage_to_phase_sign": 1,
        "reporting_direction": 1,
        "run_id": f"QB_NODE2_OPERATING_POINT_DECOMPOSITION_V1/{case_key}",
        "window_id": "W3-read-95-110ps-activity-95-115ps-post-115-130ps-tail-125-130ps",
        "raw_sha256": raw_hash,
        "metric_spec": {
            "path": "docs/research/METRIC_SPEC_V2.md",
            "version": "2.0.0",
            "sha256": metric_hash,
        },
        "compatibility_profile": "STRICT_EVENT_ANCHOR_COMPATIBILITY_V1",
        "tolerance": {
            "id": "qb-node2-operating-point-decomposition-bjl2-v1",
            "scope": "task-local",
            "status": "FROZEN",
            "evidence": "test/exploration/qb-node2-operating-point-decomposition-v1-20260902/experiment.yaml",
            "phase_area_residual_abs_floor_turns": 0.05,
            "phase_area_residual_relative": 0.10,
            "complete_min_turns": 1.0,
            "clean_upper_turns": 1.15,
            "post_range_max_turns": 1.0,
            "post_tail_p2p_max_turns": 0.25,
        },
    })
    return strict_event_summary(
        trace.time,
        selected(trace, "P(BJL2|XBQ)"),
        selected(trace, "V(BJL2|XBQ)"),
        activity_window_s=(95.0e-12, 115.0e-12),
        post_window_s=(115.0e-12, 130.0e-12),
        post_tail_window_s=(125.0e-12, 130.0e-12),
        spec=spec,
        actual_raw_sha256=raw_hash,
        actual_metric_spec_sha256=metric_hash,
    )


def compact_q_current(stats: dict[str, Any]) -> dict[str, Any]:
    return {key: stats[key] for key in (
        "mean_uA", "rms_uA", "minimum_uA", "maximum_uA", "p2p_uA",
        "signed_integral_uA_ps", "positive_area_uA_ps", "negative_area_uA_ps",
        "positive_occupancy", "negative_occupancy", "zero_crossing_count",
    )}


def q_reference_case(trace: RawTrace, path: Path, input_uA: float, raw_hash: str, metric_hash: str) -> dict[str, Any]:
    pulses: list[dict[str, Any]] = []
    for start in (10.0, 60.0, 110.0, 160.0, 210.0, 260.0):
        activity = (start, start + 25.0)
        post = (start + 25.0, min(start + 49.0, 300.0))
        currents = {
            signal: compact_q_current(current_stats(trace, signal, activity, q_case=True))
            for signal in ["I(BJS|XBQ)", "I(BJL1|XBQ)", "I(L1|XBQ)", "I(RB|XBQ)", "I(L2|XBQ)", "I(BJL2|XBQ)"]
        }
        phases = {signal: phase_stats(trace, signal, activity) for signal in Q_PHASE_SIGNALS}
        strict = strict_event_summary(
            trace.time,
            selected(trace, "P(BJL2|XBQ)"),
            selected(trace, "V(BJL2|XBQ)"),
            activity_window_s=(activity[0] * 1.0e-12, activity[1] * 1.0e-12),
            post_window_s=(post[0] * 1.0e-12, post[1] * 1.0e-12),
            post_tail_window_s=(max(post[0], post[1] - 5.0) * 1.0e-12, post[1] * 1.0e-12),
            spec=StrictLocalEventSpec.from_mapping({
                "id": "q0-historical-supporting-raw-arithmetic",
                "scope": "task-local",
                "status": "UNFROZEN",
                "mapping_status": "HISTORICAL_Q0_MAPPING",
                "phase_column": "P(BJL2|XBQ)",
                "voltage_column": "V(BJL2|XBQ)",
                "branch_endpoints": "BJL2 4 -> 0; inherited scaled QB snapshot",
                "voltage_to_phase_sign": 1,
                "reporting_direction": 1,
                "run_id": f"QB_NODE2_OPERATING_POINT_DECOMPOSITION_V1/{path.stem}/{start:g}ps",
                "window_id": f"q0-pulse-{start:g}ps",
                "raw_sha256": raw_hash,
                "metric_spec": {"path": "docs/research/METRIC_SPEC_V2.md", "version": "2.0.0", "sha256": metric_hash},
                "tolerance": {
                    "id": "q0-historical-unfrozen",
                    "scope": "task-local",
                    "status": "UNFROZEN",
                    "evidence": "test/exploration/qb-q0-standalone-current-quantized-event-20260824/manifest.yaml",
                    "phase_area_residual_abs_floor_turns": 0.05,
                    "phase_area_residual_relative": 0.10,
                    "complete_min_turns": 1.0,
                    "clean_upper_turns": 1.15,
                    "post_range_max_turns": 1.0,
                    "post_tail_p2p_max_turns": 0.25,
                },
            }),
            actual_raw_sha256=raw_hash,
            actual_metric_spec_sha256=metric_hash,
        )
        largest = strict.get("largest_monotonic_segment") or {}
        pulses.append({
            "start_ps": start,
            "currents": currents,
            "phases": {
                signal: {key: value["endpoint_delta_turns"] for key in ("endpoint_delta_turns", "p2p_turns", "mean_turns") if key in value}
                for signal, value in phases.items()
            },
            "bjl2_largest_segment_raw_arithmetic": {
                key: largest.get(key)
                for key in ("start_time_ps", "end_time_ps", "phase_reported_turns", "area_reported_turns", "phase_area_residual_turns")
            },
            "bjl2_unfrozen_classification": strict.get("compatibility_classification"),
            "post_phase_range_turns": (strict.get("post_boundedness") or {}).get("post_phase_range_turns"),
        })
    representative = next(item for item in pulses if item["start_ps"] == 110.0)
    return {
        "input_uA": input_uA,
        "raw": rel(path),
        "raw_sha256": raw_hash,
        "authority": "HISTORICAL_SUPPORTING_REFERENCE",
        "time_step_ps": 0.1,
        "stop_ps": 300.0,
        "pulse_starts_ps": [item["start_ps"] for item in pulses],
        "pulses": pulses,
        "representative_pulse_110ps": representative,
        "no_pointwise_comparison_to_G_I0_P0": True,
        "interpretation": "scalar local reference only; no universal threshold and no mechanism authority",
    }


def precentered(trace: RawTrace, signal: str, *, phase: bool = False, denominator_signal: str | None = None) -> tuple[list[int], list[float], float | None]:
    full = continuous_unwrap(selected(trace, signal)) if phase else selected(trace, signal)
    scale = 1.0 / TAU if phase else 1.0e6
    full_values = [value * scale for value in full]
    pre_idx = indices(trace, WINDOWS_PS["W2_pre_read_idle"])
    pre_median = percentile([full_values[index] for index in pre_idx], 0.5)
    analysis_idx = indices(trace, (95.0, 130.0))
    if denominator_signal is None:
        return analysis_idx, [full_values[index] - pre_median for index in analysis_idx], pre_median
    denominator = [selected(trace, denominator_signal)[index] * 1.0e6 for index in analysis_idx]
    output: list[float] = []
    for value, denom in zip(full_values, denominator):
        output.append(value / denom if abs(denom) >= PARTITION_DENOMINATOR_FLOOR_UA else float("nan"))
    pre_den = [selected(trace, denominator_signal)[index] * 1.0e6 for index in pre_idx]
    valid_pre = [value for value in pre_den if abs(value) >= PARTITION_DENOMINATOR_FLOOR_UA]
    baseline = percentile(valid_pre, 0.5) if valid_pre else None
    if baseline is not None:
        output = [value - baseline if math.isfinite(value) else float("nan") for value in output]
    return analysis_idx, output, baseline


def divergence_feature(trace_i0: RawTrace, trace_p0: RawTrace, signal_i0: str, signal_p0: str, *, kind: str, denominator: str | None = None) -> dict[str, Any]:
    idx_i, values_i, pre_i = precentered(trace_i0, signal_i0, phase=kind == "phase", denominator_signal=denominator)
    idx_p, values_p, pre_p = precentered(trace_p0, signal_p0, phase=kind == "phase", denominator_signal=denominator)
    if idx_i != idx_p:
        fail("divergence features do not share exact indices")
    finite_diffs = [abs(a - b) for a, b in zip(values_i, values_p) if math.isfinite(a) and math.isfinite(b)]
    if not finite_diffs:
        return {
            "signal_i0": signal_i0,
            "signal_p0": signal_p0,
            "kind": kind,
            "pre_median_i0": pre_i,
            "pre_median_p0": pre_p,
            "threshold": None,
            "first_time_ps": None,
            "status": "NO_VALID_DENOMINATOR",
        }
    if kind == "current":
        threshold = max(CURRENT_FLOOR_UA, CURRENT_RELATIVE * max(finite_diffs))
    elif kind == "phase":
        threshold = PHASE_THRESHOLD_TURNS
    else:
        threshold = PARTITION_THRESHOLD
    first: int | None = None
    for offset, (value_i, value_p) in enumerate(zip(values_i, values_p)):
        if math.isfinite(value_i) and math.isfinite(value_p) and abs(value_i - value_p) > threshold:
            first = offset
            break
    record = {
        "signal_i0": signal_i0,
        "signal_p0": signal_p0,
        "kind": kind,
        "pre_median_i0": pre_i,
        "pre_median_p0": pre_p,
        "scale_max_abs_precentered_difference": max(finite_diffs),
        "threshold": threshold,
        "first_time_ps": None if first is None else trace_i0.time[idx_i[first]] * 1.0e12,
        "status": "CROSSED" if first is not None else "NO_CROSSING",
    }
    if first is not None:
        record["first_sample_index"] = idx_i[first]
        record["first_difference"] = abs(values_i[first] - values_p[first])
    return record


def first_divergence(trace_i0: RawTrace, trace_p0: RawTrace) -> dict[str, Any]:
    features = {
        "L0_input_source": [divergence_feature(trace_i0, trace_p0, "I(LIN|XBQ)", "I(LIN|XBQ)", kind="current")],
        "L1_BJs": [
            divergence_feature(trace_i0, trace_p0, "I(BJS|XBQ)", "I(BJS|XBQ)", kind="current"),
            divergence_feature(trace_i0, trace_p0, "P(BJS|XBQ)", "P(BJS|XBQ)", kind="phase"),
        ],
        "L2_node2": [
            divergence_feature(trace_i0, trace_p0, "I(BJL1|XBQ)", "I(BJL1|XBQ)", kind="current"),
            divergence_feature(trace_i0, trace_p0, "I(RJ1|XBQ)", "I(RJ1|XBQ)", kind="current"),
            divergence_feature(trace_i0, trace_p0, "I(L1|XBQ)", "I(L1|XBQ)", kind="current"),
            divergence_feature(trace_i0, trace_p0, "I(BJL1|XBQ)", "I(BJL1|XBQ)", kind="partition", denominator="I(BJS|XBQ)"),
            divergence_feature(trace_i0, trace_p0, "I(L1|XBQ)", "I(L1|XBQ)", kind="partition", denominator="I(BJS|XBQ)"),
        ],
        "L3_node3": [
            divergence_feature(trace_i0, trace_p0, "I(L1|XBQ)", "I(L1|XBQ)", kind="current"),
            divergence_feature(trace_i0, trace_p0, "I(RB|XBQ)", "I(RB|XBQ)", kind="current"),
            divergence_feature(trace_i0, trace_p0, "I(L2|XBQ)", "I(L2|XBQ)", kind="current"),
            divergence_feature(trace_i0, trace_p0, "I(L1|XBQ)", "I(L1|XBQ)", kind="partition", denominator="I(L2|XBQ)"),
        ],
        "L4_node4_output": [
            divergence_feature(trace_i0, trace_p0, "I(L2|XBQ)", "I(L2|XBQ)", kind="current"),
            divergence_feature(trace_i0, trace_p0, "I(BJL2|XBQ)", "I(BJL2|XBQ)", kind="current"),
            divergence_feature(trace_i0, trace_p0, "I(RJ2|XBQ)", "I(RJ2|XBQ)", kind="current"),
            divergence_feature(trace_i0, trace_p0, "I(L0|XBQ)", "I(L0|XBQ)", kind="current"),
            divergence_feature(trace_i0, trace_p0, "P(BJL2|XBQ)", "P(BJL2|XBQ)", kind="phase"),
        ],
    }
    layer_times: dict[str, float | None] = {}
    for layer, records in features.items():
        times = [item["first_time_ps"] for item in records if item.get("first_time_ps") is not None]
        layer_times[layer] = min(times) if times else None
    present = sorted((time, layer) for layer, time in layer_times.items() if time is not None)
    groups: list[dict[str, Any]] = []
    for time, layer in present:
        if not groups or time - groups[-1]["first_time_ps"] > TIE_RESOLUTION_PS:
            groups.append({"first_time_ps": time, "layers": [layer]})
        else:
            groups[-1]["layers"].append(layer)
    first_group = groups[0] if groups else None
    return {
        "comparison": "I0 versus P0 exact_grid",
        "precentered": True,
        "analysis_window_ps": [95.0, 130.0],
        "thresholds": {
            "current_abs_floor_uA": CURRENT_FLOOR_UA,
            "current_relative_to_feature_scale": CURRENT_RELATIVE,
            "phase_abs_turns": PHASE_THRESHOLD_TURNS,
            "partition_abs_fraction": PARTITION_THRESHOLD,
            "partition_denominator_floor_uA": PARTITION_DENOMINATOR_FLOOR_UA,
            "tie_resolution_ps": TIE_RESOLUTION_PS,
        },
        "features": features,
        "layer_first_time_ps": layer_times,
        "ordered_tie_groups": groups,
        "first_group": first_group,
    }


def mechanism_classification(metrics: dict[str, Any]) -> dict[str, Any]:
    if metrics["kcl_status"] != "KCL_CONSISTENT":
        return {"classification": "ANALYSIS_INVALID", "mechanism_disposition": "EXPLORATORY", "reason": "KCL residual check failed; stop physical interpretation"}
    i0 = metrics["cases"]["I0"]
    p0 = metrics["cases"]["P0"]
    i0_sig = i0["node2_signature"]
    p0_sig = p0["node2_signature"]
    p0_bjs_active = (
        p0_sig["BJs_drive"]["phase"]["p2p_turns"] >= 1.0
        and p0_sig["BJs_drive"]["current"]["p2p_uA"] >= 5.0
    )
    node2 = metrics["I0_vs_P0_W3"]
    critical_node2 = (
        node2["I(BJL1|XBQ)"]["rms_difference"] > CURRENT_FLOOR_UA
        and node2["I(L1|XBQ)"]["rms_difference"] > CURRENT_FLOOR_UA
        and node2["P(BJL1|XBQ)"]["rms_difference"] > PHASE_THRESHOLD_TURNS
    )
    rb_stable = node2["I(RB|XBQ)"]["rms_difference"] <= CURRENT_FLOOR_UA
    strict_i0 = metrics["strict_local"]["I0"]["compatibility_classification"]
    strict_p0 = metrics["strict_local"]["P0"]["compatibility_classification"]
    downstream_follows = strict_i0 == "CLEAN_ONE_SFQ_CANDIDATE" and strict_p0 == "SUBTHRESHOLD"
    first_group = metrics["first_divergence"].get("first_group") or {}
    first_layers = set(first_group.get("layers", []))
    if p0_bjs_active and critical_node2 and rb_stable and downstream_follows:
        if {"L0_input_source", "L1_BJs", "L2_node2"}.issubset(first_layers):
            classification = "COUPLED_INPUT_BJS_NODE2"
            reason = "BJs is locally active, node2 branch separation and downstream separation are observed, RB remains stable, and L0/L1/L2 first crossings are tied at declared resolution."
        elif "L2_node2" in first_layers and "L1_BJs" not in first_layers:
            classification = "NODE2_REDISTRIBUTION_SUPPORTED"
            reason = "BJs is locally active and the first resolved separation is in the node2 partition while RB remains stable."
        else:
            classification = "NODE2_REDISTRIBUTION_SUPPORTED"
            reason = "BJs is locally active, critical node2 separation and downstream separation are present, and RB remains stable; onset ordering is not sufficient for a narrower claim."
    elif not p0_bjs_active and metrics["q_reference"]["Q45"]["representative_pulse_110ps"]["phases"]["P(BJL2|XBQ)"]["endpoint_delta_turns"] < 1.0:
        classification = "INPUT_BJS_LIMITATION_SUPPORTED"
        reason = "Physical P0 BJs activity is not clear under the preregistered descriptive activity rule and the lower scalar reference is also subthreshold; this remains exploratory."
    else:
        classification = "NO_CLEAR_DISCRIMINATION"
        reason = "Existing raw supports activity and differences but not a sufficiently separated mechanism classification under the preregistered rules."
    return {
        "classification": classification,
        "mechanism_disposition": "EXPLORATORY",
        "reason": reason,
        "H2_eligibility": {
            "BJs_clearly_active": p0_bjs_active,
            "critical_node2_separation": critical_node2,
            "RB_stable": rb_stable,
            "downstream_follows": downstream_follows,
        },
        "strict_local_labels_used": {"I0": strict_i0, "P0": strict_p0},
        "not_unique_root_cause": True,
    }


def q0_provenance(config: dict[str, Any], paths: dict[str, Path], records: dict[str, Any]) -> dict[str, Any]:
    q0_root = REPO / "test/exploration/qb-q0-standalone-current-quantized-event-20260824"
    manifest_path = q0_root / "manifest.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        fail("Q0 manifest is not a mapping")
    checks = {
        "scaled_bias_uA": manifest.get("scaled_fixture", {}).get("bias_uA") == 35.0,
        "scaled_inputs_include_45_and_68p4": all(value in manifest.get("scaled_fixture", {}).get("input_uA", []) for value in (45.0, 68.4)),
        "periodic_stimulus_registered": manifest.get("stimulus", {}).get("expression") == "pulse(0 IIN 10p 1p 1p 5p 50p)",
        "time_step_registered": manifest.get("time_step_ps") == 0.1,
        "stop_time_registered": manifest.get("stop_time_ps") == 300.0,
        "scaled_cell_hash_matches_q0_snapshot": sha256_file(q0_root / "inputs/bq_cell.cir") == "5ee4e8f054a9a49aea7e48493b20ef3d794db01b2902f15a439b0ea31f2276a2",
        "jj_model_hash_matches_q0_snapshot": sha256_file(q0_root / "inputs/jjmit.cir") == "19862d1fd1f1f44dfa1523848d7d3b5e2594a6c5da8fdd80144b449e5312a336",
    }
    if not all(checks.values()):
        fail(f"Q0 provenance checks failed: {checks}")
    deck_texts = {key: resolve(config["supporting_cases"][key]["deck"]).read_text(encoding="utf-8") for key in ("Q45", "Q68")}
    checks["Q45_deck_input_semantics"] = "I_IN 0 IN pulse(0 45u" in deck_texts["Q45"] and "I_IBIAS 0 IBIAS" in deck_texts["Q45"]
    checks["Q68_deck_input_semantics"] = "I_IN 0 IN pulse(0 68.4u" in deck_texts["Q68"] and "I_IBIAS 0 IBIAS" in deck_texts["Q68"]
    checks["Q45_Q68_load_semantics"] = all(
        "R_LOAD OUT 0 10" in deck_text
        for deck_text in (deck_texts["Q45"], deck_texts["Q68"])
    )
    checks["Q45_raw_hash_registered"] = records["Q45"]["registered_hash_verified"]
    checks["Q68_raw_hash_registered"] = records["Q68"]["registered_hash_verified"]
    if not all(checks.values()):
        fail(f"Q0 provenance checks failed: {checks}")
    return {
        "manifest": file_snapshot(manifest_path, relative_to=REPO),
        "manifest_checks": checks,
        "raw_hash_source": rel(q0_root / "analysis/SHA256SUMS.txt"),
        "raw_records": {key: records[key] for key in ("Q45", "Q68")},
        "fixture_inputs": {
            "Q45_deck": file_snapshot(resolve(config["supporting_cases"]["Q45"]["deck"]), relative_to=REPO),
            "Q68_deck": file_snapshot(resolve(config["supporting_cases"]["Q68"]["deck"]), relative_to=REPO),
            "bq_cell_snapshot": file_snapshot(q0_root / "inputs/bq_cell.cir", relative_to=REPO),
            "jjmit_snapshot": file_snapshot(q0_root / "inputs/jjmit.cir", relative_to=REPO),
        },
        "authority": "HISTORICAL_SUPPORTING_REFERENCE",
        "reason": "Q0 manifest and raw hashes are verified, but the fixture is periodic, 0.1 ps, standalone, and its local event rule is UNFROZEN.",
    }


def semantic_netlist_hash(path: Path) -> str:
    lines: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        text = raw.strip()
        if not text or text.startswith("*"):
            continue
        lines.append(re.sub(r"\s+", " ", text).casefold())
    return hashlib.sha256(("\n".join(lines) + "\n").encode("utf-8")).hexdigest()


def topology_check(path: Path) -> dict[str, Any]:
    expected = {
        "Lin": ("IN", "1"),
        "L0": ("4", "OUT"),
        "L1": ("2", "3"),
        "L2": ("3", "4"),
        "BJs": ("1", "2"),
        "BJL1": ("2", "0"),
        "RJ1": ("2", "0"),
        "BJL2": ("4", "0"),
        "RJ2": ("4", "0"),
        "RB": ("IB", "3"),
    }
    found: dict[str, list[str]] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        text = raw.strip()
        if not text or text.startswith("*") or text.startswith("."):
            continue
        fields = text.split()
        if len(fields) >= 3 and fields[0] in expected:
            found[fields[0]] = fields[1:3]
    result = {name: found.get(name) == list(nodes) for name, nodes in expected.items()}
    return {
        "path": rel(path),
        "semantic_sha256": semantic_netlist_hash(path),
        "branches": found,
        "expected_orientation": {name: list(nodes) for name, nodes in expected.items()},
        "all_expected_orientation_verified": all(result.values()),
        "per_branch": result,
    }


def write_plot(trace_i0: RawTrace, trace_p0: RawTrace, paths: dict[str, Path]) -> dict[str, Any]:
    signals = [
        ("I(BJS|XBQ)", "I(I0|BJS)", "I0"),
        ("I(BJS|XBQ)", "I(P0|BJS)", "P0"),
        ("P(BJS|XBQ)", "P(I0|BJS)", "I0"),
        ("P(BJS|XBQ)", "P(P0|BJS)", "P0"),
        ("I(BJL1|XBQ)", "I(I0|BJL1)", "I0"),
        ("I(BJL1|XBQ)", "I(P0|BJL1)", "P0"),
        ("I(L1|XBQ)", "I(I0|L1)", "I0"),
        ("I(L1|XBQ)", "I(P0|L1)", "P0"),
        ("I(RB|XBQ)", "I(I0|RB)", "I0"),
        ("I(RB|XBQ)", "I(P0|RB)", "P0"),
        ("I(L2|XBQ)", "I(I0|L2)", "I0"),
        ("I(L2|XBQ)", "I(P0|L2)", "P0"),
        ("P(BJL1|XBQ)", "P(I0|BJL1)", "I0"),
        ("P(BJL1|XBQ)", "P(P0|BJL1)", "P0"),
        ("P(BJL2|XBQ)", "P(I0|BJL2)", "I0"),
        ("P(BJL2|XBQ)", "P(P0|BJL2)", "P0"),
    ]
    output = ANALYSIS / "plot_input.csv"
    output.parent.mkdir(parents=True, exist_ok=True)
    raw_i0 = {signal: selected(trace_i0, signal) for signal, _name, _case in signals}
    raw_p0 = {signal: selected(trace_p0, signal) for signal, _name, _case in signals}
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["time"] + [name for _signal, name, _case in signals])
        for index, time in enumerate(trace_i0.time):
            row = [time]
            for signal, _name, case in signals:
                row.append((raw_i0 if case == "I0" else raw_p0)[signal][index])
            writer.writerow(row)
    columns = [name for _signal, name, _case in signals]
    output_html = PLOTS / "RESULT_OVERVIEW.html"
    command = [
        sys.executable, str(PLOTTER), str(output),
        "-t", "sep_comb", "-c", "dark", "-j", "2pi",
        "-s", *columns, "-x", str(output_html),
        "-w", "QB node2 operating-point decomposition — I0 vs P0 key signals",
    ]
    subprocess.run(command, cwd=REPO, check=True)
    metadata = {
        "schema_version": "CLASSIC_JOSIM_PLOT_V1",
        "generated_at": generated_at(),
        "experiment_id": rel(ROOT),
        "plot_path": rel(output_html),
        "generated_from": "scripts/josim-plot2.py",
        "plot_type": "sep_comb",
        "command_profile": "-t sep_comb -c dark -j 2pi",
        "style": "CLASSIC_LOCKED",
        "mode": "compact",
        "color": "dark",
        "phase_display": "continuous phase phi/2pi (turns); not an SFQ counter",
        "source_paths": {"I0": rel(paths["I0"]), "P0": rel(paths["P0"])},
        "derived_input": rel(output),
        "raw_input_only_for_derived_data": True,
        "columns": columns,
        "signal_count": len(columns),
        "group_count": 8,
        "full_time_grid_exact": True,
        "key_signal_groups": [
            "I(BJS|XBQ)", "P(BJS|XBQ)", "I(BJL1|XBQ)", "I(L1|XBQ)",
            "I(RB|XBQ)", "I(L2|XBQ)", "P(BJL1|XBQ)", "P(BJL2|XBQ)",
        ],
        "scientific_authority": "raw evidence and analysis report; visualization is descriptive and is not event/Gate authority",
    }
    write_json(PLOTS / "RESULT_OVERVIEW.metadata.json", metadata)
    return metadata


def build_provenance(config: dict[str, Any], paths: dict[str, Path], records: dict[str, Any], q0: dict[str, Any], topo: dict[str, Any]) -> dict[str, Any]:
    metric_path = REPO / "docs/research/METRIC_SPEC_V2.md"
    current_bq = REPO / "circuits/qb/bq_cell.cir"
    parent_bq = REPO / "test/exploration/bvm-load-qb-matrix-v1-20260901/inputs/bq_cell.cir"
    current_jj = REPO / "circuits/models/jjmit.cir"
    parent_jj = REPO / "test/exploration/bvm-load-qb-matrix-v1-20260901/inputs/jjmit.cir"
    current_bvm = REPO / "circuits/bvm/bvm_cell.cir"
    parent_bvm = REPO / "test/exploration/bvm-load-qb-matrix-v1-20260901/inputs/bvm_cell.cir"
    return {
        "task_id": config["id"],
        "generated_at": generated_at(),
        "repository": git_snapshot(REPO),
        "no_new_josim": True,
        "no_circuit_change": True,
        "no_parameter_change": True,
        "no_historical_raw_rewrite": True,
        "primary_raw": {key: records[key] for key in ("G", "I0", "P0")},
        "primary_decks": {key: file_snapshot(resolve(config["primary_cases"][key]["deck"]), relative_to=REPO) for key in ("G", "I0", "P0")},
        "supporting_q45_q68": q0,
        "qb_topology": {
            "parent_snapshot": file_snapshot(parent_bq, relative_to=REPO),
            "current_canonical": file_snapshot(current_bq, relative_to=REPO),
            "semantic_hash_parent": semantic_netlist_hash(parent_bq),
            "semantic_hash_current": semantic_netlist_hash(current_bq),
            "topology_orientation": topo,
            "parameters": config["qb_topology"]["parameters"],
            "input_load": "R_LOAD OUT 0 10 ohm; IBIAS=35 uA",
        },
        "models": {
            "jjmit_parent_snapshot": file_snapshot(parent_jj, relative_to=REPO),
            "jjmit_current_canonical": file_snapshot(current_jj, relative_to=REPO),
            "bvm_parent_snapshot": file_snapshot(parent_bvm, relative_to=REPO),
            "bvm_current_canonical": file_snapshot(current_bvm, relative_to=REPO),
        },
        "metric_spec": file_snapshot(metric_path, relative_to=REPO),
        "analysis_script": file_snapshot(ANALYSIS / "analyze_node2.py", relative_to=REPO),
        "config": file_snapshot(CONFIG_PATH, relative_to=REPO),
        "signal_occurrences": {
            "I(B_LD1)": 0,
            "I(B_LD12)": 0,
            "all_other_registered_signals": "unique exact occurrence; case-sensitive labels retained",
        },
        "branch_orientation": config["qb_topology"]["branch_orientation_from_netlist"],
        "kcl_equations": config["qb_topology"]["kcl"],
        "windows_ps": config["windows_ps"],
        "strict_local_anchor": config["strict_local_anchor"],
        "first_divergence": config["first_divergence"],
        "historical_boundary": {
            "old_audit": "test/exploration/qb-ideal-physical-internal-trajectory-audit-v1-20260825",
            "old_audit_use": "historical motivation only; not authoritative because of D12 RUN_INPUT_HASH_MISMATCH and replay-source semantic limitation",
        },
        "raw_provenance_statement": "All primary conclusions use existing raw CSVs; Q45/Q68 are scalar historical support only; raw files are not copied or rewritten.",
    }


def main() -> None:
    config = load_config()
    traces, paths, records = load_traces(config)
    metric_hash = sha256_file(REPO / "docs/research/METRIC_SPEC_V2.md")
    kcl_by_case: dict[str, Any] = {}
    case_metrics: dict[str, Any] = {}
    for key in ("I0", "P0"):
        kcl_by_case[key] = {name: kcl_metrics(traces[key], window, q_case=False) for name, window in WINDOWS_PS.items() if name in {"W2_pre_read_idle", "W3_read", "W4_post_read_observation"}}
        case_metrics[key] = {
            "raw": records[key],
            "windows": case_window_metrics(traces[key]),
            "operating_point": operating_point(traces[key]),
            "node2_signature": node2_signature(traces[key]),
            "node4": {
                "W3": {signal: current_stats(traces[key], signal, WINDOWS_PS["W3_read"]) for signal in ["I(L2|XBQ)", "I(BJL2|XBQ)", "I(RJ2|XBQ)", "I(L0|XBQ)"]},
                "W4": {signal: current_stats(traces[key], signal, WINDOWS_PS["W4_post_read_observation"]) for signal in ["I(L2|XBQ)", "I(BJL2|XBQ)", "I(RJ2|XBQ)", "I(L0|XBQ)"]},
                "strict_activity": {signal: (phase_stats(traces[key], signal, WINDOWS_PS["node4_strict_activity"]) if signal.startswith("P(") else voltage_stats(traces[key], signal, WINDOWS_PS["node4_strict_activity"]) if signal.startswith("V(") else current_stats(traces[key], signal, WINDOWS_PS["node4_strict_activity"])) for signal in ["I(L2|XBQ)", "I(BJL2|XBQ)", "I(RJ2|XBQ)", "I(L0|XBQ)", "P(BJL2|XBQ)", "V(BJL2|XBQ)"]},
                "strict_post": {signal: (phase_stats(traces[key], signal, WINDOWS_PS["node4_strict_post"]) if signal.startswith("P(") else voltage_stats(traces[key], signal, WINDOWS_PS["node4_strict_post"]) if signal.startswith("V(") else current_stats(traces[key], signal, WINDOWS_PS["node4_strict_post"])) for signal in ["I(L2|XBQ)", "I(BJL2|XBQ)", "I(RJ2|XBQ)", "I(L0|XBQ)", "P(BJL2|XBQ)", "V(BJL2|XBQ)"]},
                "strict_tail": {"P(BJL2|XBQ)": phase_stats(traces[key], "P(BJL2|XBQ)", WINDOWS_PS["node4_strict_tail"])},
            },
        }
    kcl_status = "KCL_CONSISTENT" if all(
        record["status"] == "KCL_CONSISTENT"
        for case in kcl_by_case.values()
        for record in case.values()
    ) else "MECHANISM_ANALYSIS_INVALID"
    replay_closure = {
        "full_grid": exact_compare(traces["G"], traces["I0"], "I(B_LD1)", "I(I_REPLAY)", (0.0, 170.0), unit="A"),
        "W3": exact_compare(traces["G"], traces["I0"], "I(B_LD1)", "I(I_REPLAY)", WINDOWS_PS["W3_read"], unit="A"),
    }
    source_comparison = {
        signal: exact_compare(traces["G"], traces["P0"], signal, signal, WINDOWS_PS["W3_read"], unit="A" if signal.startswith("I(") else "raw")
        for signal in ["I(B_LD1)", "I(B_LD12)", "I(L_SL|XBVM1)"]
    }
    source_comparison["V(SL1)"] = exact_compare(traces["G"], traces["P0"], "V(SL1)", "V(SL1)", WINDOWS_PS["W3_read"], unit="raw")
    node3 = node3_analysis(traces["I0"], traces["P0"])
    strict_local = {key: strict_result(traces[key], records[key]["sha256"], key, metric_hash) for key in ("I0", "P0")}
    anchor = strict_local["I0"].get("largest_monotonic_segment") or {}
    if strict_local["I0"]["compatibility_classification"] != "CLEAN_ONE_SFQ_CANDIDATE":
        fail("I0 strict anchor classification changed")
    if abs(float(anchor.get("phase_reported_turns", float("nan"))) - 1.0160289228944646) > 1.0e-12:
        fail("I0 strict anchor phase regression")
    if abs(float(anchor.get("area_reported_turns", float("nan"))) - 1.0160368344325381) > 1.0e-12:
        fail("I0 strict anchor area regression")
    if abs(float(anchor.get("start_time_ps", float("nan"))) - 103.0375) > 1.0e-9 or abs(float(anchor.get("end_time_ps", float("nan"))) - 110.175) > 1.0e-9:
        fail("I0 strict anchor segment regression")
    q0 = q0_provenance(config, paths, records)
    q_reference = {
        "Q45": q_reference_case(traces["Q45"], paths["Q45"], 45.0, records["Q45"]["sha256"], metric_hash),
        "Q68": q_reference_case(traces["Q68"], paths["Q68"], 68.4, records["Q68"]["sha256"], metric_hash),
    }
    topology = topology_check(resolve(config["qb_topology"]["source"]))
    first = first_divergence(traces["I0"], traces["P0"])
    i0_vs_p0 = {
        signal: exact_compare(traces["I0"], traces["P0"], signal, signal, WINDOWS_PS["W3_read"], unit="uA" if signal.startswith("I(") else "turns")
        for signal in ["I(BJS|XBQ)", "P(BJS|XBQ)", "I(BJL1|XBQ)", "I(RJ1|XBQ)", "I(L1|XBQ)", "I(RB|XBQ)", "I(L2|XBQ)", "I(BJL2|XBQ)", "I(RJ2|XBQ)", "I(L0|XBQ)", "P(BJL1|XBQ)", "P(BJL2|XBQ)"]
    }
    metrics: dict[str, Any] = {
        "schema_version": "QB_NODE2_OPERATING_POINT_DECOMPOSITION_V1",
        "generated_at": generated_at(),
        "analysis_only": True,
        "no_new_josim": True,
        "no_circuit_change": True,
        "no_parameter_change": True,
        "kcl_status": kcl_status,
        "kcl": kcl_by_case,
        "cases": case_metrics,
        "source": {"G": source_metrics(traces["G"]), "G_vs_P0_W3": source_comparison},
        "replay_closure_G_to_I0": replay_closure,
        "node3": node3,
        "strict_local": strict_local,
        "I0_vs_P0_W3": i0_vs_p0,
        "first_divergence": first,
        "q_reference": q_reference,
        "q_reference_provenance": q0,
        "topology": topology,
    }
    metrics["mechanism"] = mechanism_classification(metrics)
    write_json(ANALYSIS / "metrics.json", metrics)
    write_json(ANALYSIS / "provenance.json", build_provenance(config, paths, records, q0, topology))
    plot_metadata = write_plot(traces["I0"], traces["P0"], paths)
    write_json(ANALYSIS / "plot_metadata.json", plot_metadata)
    print(json.dumps({
        "status": "PASS" if kcl_status == "KCL_CONSISTENT" else "MECHANISM_ANALYSIS_INVALID",
        "kcl_status": kcl_status,
        "mechanism": metrics["mechanism"],
        "strict_I0": strict_local["I0"]["compatibility_classification"],
        "strict_P0": strict_local["P0"]["compatibility_classification"],
        "plot": rel(PLOTS / "RESULT_OVERVIEW.html"),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
