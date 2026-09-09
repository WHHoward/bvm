#!/usr/bin/env python3
"""Compute only the preregistered raw-derived metrics for the five runs.

No event detector, SFQ counter, interpolation, resampling or raw mutation is
used here. Phase is unwrapped independently per run and remains explicitly
identified as raw radians before the derived rad/(2*pi) display quantity.
"""

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
from bvmtools.raw import RawTrace, read_csv  # noqa: E402


PHI0 = 2.067833848e-15
TAU = 2.0 * math.pi
RUNS = {
    "NOMINAL": ("nominal", 12.0, 2.0, "matched baseline"),
    "L1_DOWN": ("l1_down", 12.0, 1.9, "L1 decrease"),
    "L1_UP": ("l1_up", 12.0, 2.1, "opposite-direction L1 control"),
    "RJ1_UP_05": ("rj1_up_05", 12.5, 2.0, "small RJ1 increase"),
    "RJ1_UP_10": ("rj1_up_10", 13.0, 2.0, "larger RJ1 increase"),
}
WINDOWS_PS = {
    "PRE_FINAL": (101.0, 110.0),
    "EARLY_TRIGGER": (110.0, 116.0),
    "FULL_READ": (110.0, 121.0),
    "TAIL": (121.0, 200.0),
    "FULL_FINAL": (110.0, 200.0),
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def write_once(path: Path, content: str) -> None:
    if path.exists():
        if path.read_text(encoding="utf-8") == content:
            return
        raise RuntimeError(f"refusing to overwrite analysis artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def values(trace: RawTrace, label: str) -> tuple[float, ...] | None:
    if label not in trace.headers:
        return None
    try:
        return tuple(float(value) for value in trace.column(label))  # type: ignore[arg-type]
    except (KeyError, ValueError):
        return None


def idx_for(trace: RawTrace, window_name: str) -> tuple[int, ...]:
    start_ps, end_ps = WINDOWS_PS[window_name]
    return window_indices(trace.time, start_ps * 1e-12, end_ps * 1e-12)


def integrate(time_s: tuple[float, ...], series: tuple[float, ...], indices: tuple[int, ...]) -> float:
    return sum(
        0.5 * (series[left] + series[right]) * (time_s[right] - time_s[left])
        for left, right in zip(indices, indices[1:])
    )


def unknown(label: str, unit: str, window_name: str) -> dict[str, object]:
    return {"status": "UNKNOWN", "signal": label, "unit": unit, "window": window_name, "reason": "requested column is not present in this raw"}


def waveform_stats(trace: RawTrace, label: str, unit: str, window_name: str, series: tuple[float, ...] | None = None) -> dict[str, object]:
    data = values(trace, label) if series is None else series
    if data is None:
        return unknown(label, unit, window_name)
    indices = idx_for(trace, window_name)
    if len(indices) < 2:
        return {"status": "UNKNOWN", "signal": label, "unit": unit, "window": window_name, "reason": "window has fewer than two stored samples"}
    selected = [data[index] for index in indices]
    times = [trace.time[index] for index in indices]
    max_value = max(selected)
    min_value = min(selected)
    max_index = selected.index(max_value)
    min_index = selected.index(min_value)
    signed = integrate(trace.time, data, indices)
    positive = integrate(trace.time, tuple(max(value, 0.0) for value in data), indices)
    negative = integrate(trace.time, tuple(min(value, 0.0) for value in data), indices)
    return {
        "status": "DERIVED",
        "signal": label,
        "unit": unit,
        "window": window_name,
        "window_ps": list(WINDOWS_PS[window_name]),
        "sample_count": len(indices),
        "first": selected[0],
        "last": selected[-1],
        "endpoint_delta": selected[-1] - selected[0],
        "max": max_value,
        "min": min_value,
        "max_abs": max(abs(value) for value in selected),
        "RMS": math.sqrt(sum(value * value for value in selected) / len(selected)),
        "p2p": max_value - min_value,
        "time_of_max_ps": times[max_index] * 1e12,
        "time_of_min_ps": times[min_index] * 1e12,
        "signed_area": signed,
        "positive_area": positive,
        "negative_area": negative,
        "area_unit": f"{unit}*s",
        "integration": "trapezoid on actual stored time grid; half-open window",
    }


def phase_area(trace: RawTrace, phase_label: str, voltage_label: str, window_name: str) -> dict[str, object]:
    phase = values(trace, phase_label)
    voltage = values(trace, voltage_label)
    if phase is None or voltage is None:
        return {"status": "UNKNOWN", "phase_signal": phase_label, "voltage_signal": voltage_label, "window": window_name, "reason": "same-JJ P/V column missing"}
    indices = idx_for(trace, window_name)
    unwrapped = continuous_unwrap(phase)
    raw_delta = unwrapped[indices[-1]] - unwrapped[indices[0]]
    area = integrate(trace.time, voltage, indices) / PHI0
    return {
        "status": "DERIVED",
        "phase_signal": phase_label,
        "voltage_signal": voltage_label,
        "phase_unit": "rad",
        "display_unit": "turns",
        "window": window_name,
        "window_ps": list(WINDOWS_PS[window_name]),
        "phase_delta_rad": raw_delta,
        "phase_delta_turns": raw_delta / TAU,
        "voltage_area_turns": area,
        "phase_area_residual_turns": raw_delta / TAU - area,
        "same_jj_same_direction": True,
        "phase_method": "independent continuous_unwrap(raw radians) then divide by 2*pi",
        "voltage_area_method": "actual-time trapezoid integral divided by Phi0",
        "not_an_sfq_count": True,
    }


def relative_phase(trace: RawTrace, phase_label: str) -> dict[str, object]:
    phase = values(trace, phase_label)
    if phase is None:
        return {"status": "UNKNOWN", "signal": phase_label, "reason": "phase column missing"}
    unwrapped = continuous_unwrap(phase)
    reference_target = 110.0e-12
    reference_index = min(range(len(trace.time)), key=lambda index: abs(trace.time[index] - reference_target))
    relative = tuple((value - unwrapped[reference_index]) / TAU for value in unwrapped)
    exact_reference = trace.time[reference_index] == reference_target
    result: dict[str, object] = {
        "status": "DERIVED" if exact_reference else "UNKNOWN",
        "signal": phase_label,
        "raw_unit": "rad",
        "display_unit": "turns",
        "reference_target_ps": 110.0,
        "reference_time_ps": trace.time[reference_index] * 1e12,
        "reference_exact": exact_reference,
        "reference_phase_raw_rad": phase[reference_index],
        "phase_conversion": "continuous_unwrap(raw_rad)/(2*pi)",
        "windows": {},
        "not_an_sfq_count": True,
    }
    for window_name in WINDOWS_PS:
        indices = idx_for(trace, window_name)
        selected = [relative[index] for index in indices]
        maximum = max(selected)
        maximum_positive = max((value for value in selected if value > 0.0), default=0.0)
        maximum_index = selected.index(maximum)
        result["windows"][window_name] = {
            "first": selected[0],
            "last": selected[-1],
            "final_relative_progression_turns": selected[-1],
            "maximum_relative_progression_turns": maximum,
            "max_positive_relative_progression_turns": maximum_positive,
            "minimum_relative_progression_turns": min(selected),
            "p2p_relative_progression_turns": max(selected) - min(selected),
            "time_of_max_progression_ps": trace.time[indices[maximum_index]] * 1e12,
            "sample_count": len(indices),
        }
    pre_indices = idx_for(trace, "PRE_FINAL")
    pre_index = pre_indices[-1]
    result["phase_at_PRE_FINAL_last"] = {
        "time_ps": trace.time[pre_index] * 1e12,
        "raw_phase_rad": phase[pre_index],
        "unwrapped_phase_rad": unwrapped[pre_index],
        "unwrapped_phase_turns": unwrapped[pre_index] / TAU,
    }
    return result


def positive_voltage_duration(trace: RawTrace, voltage_label: str, window_name: str) -> dict[str, object]:
    voltage = values(trace, voltage_label)
    if voltage is None:
        return unknown(voltage_label, "V", window_name)
    indices = idx_for(trace, window_name)
    positive_intervals = sum(
        trace.time[right] - trace.time[left]
        for left, right in zip(indices, indices[1:])
        if voltage[left] > 0.0 and voltage[right] > 0.0
    )
    return {
        "status": "DERIVED",
        "signal": voltage_label,
        "window": window_name,
        "rule": "V>0 at both endpoints of each actual stored interval; no threshold and no event count",
        "positive_sample_count": sum(voltage[index] > 0.0 for index in indices),
        "positive_interval_duration_s": positive_intervals,
        "positive_interval_duration_ps": positive_intervals * 1e12,
    }


def l1_metrics(trace: RawTrace) -> dict[str, object]:
    label = "I(L1|XBQ1)"
    data = values(trace, label)
    if data is None:
        return {"status": "UNKNOWN", "signal": label, "reason": "column missing"}
    target = 110.0e-12
    ref_index = min(range(len(trace.time)), key=lambda index: abs(trace.time[index] - target))
    full_indices = idx_for(trace, "FULL_FINAL")
    brackets = []
    for left, right in zip(full_indices, full_indices[1:]):
        if data[left] < 0.0 <= data[right]:
            brackets.append({
                "last_negative": {"time_ps": trace.time[left] * 1e12, "current_A": data[left], "current_uA": data[left] * 1e6},
                "first_nonnegative": {"time_ps": trace.time[right] * 1e12, "current_A": data[right], "current_uA": data[right] * 1e6},
                "statement": "crossing is bracketed between these two stored samples; no sub-sample crossing time",
            })
    return {
        "status": "DERIVED",
        "signal": label,
        "value_at_or_nearest_110ps": {"target_time_ps": 110.0, "actual_time_ps": trace.time[ref_index] * 1e12, "exact": trace.time[ref_index] == target, "current_A": data[ref_index], "current_uA": data[ref_index] * 1e6},
        "windows": {name: waveform_stats(trace, label, "A", name) for name in WINDOWS_PS},
        "sign_change_negative_to_nonnegative": bool(brackets),
        "sign_change_brackets": brackets,
        "no_interpolation": True,
    }


def source_metrics(trace: RawTrace) -> dict[str, object]:
    lsl = [values(trace, f"I(L_SL|XBVM{instance})") for instance in range(1, 5)]
    if any(series is None for series in lsl):
        quiet = None
        active = None
    else:
        active = lsl[0]
        quiet = tuple(sum(series[index] for series in lsl[1:]) for index in range(len(lsl[0])))  # type: ignore[index]
    series: dict[str, object] = {
        "I(LSL|XBVM1)": {name: waveform_stats(trace, "I(L_SL|XBVM1)", "A", name) for name in WINDOWS_PS},
        "I_quiet_total": {name: waveform_stats(trace, "I_quiet_total", "A", name, quiet) if quiet is not None else unknown("I_quiet_total", "A", name) for name in WINDOWS_PS},
        "I(B_JSL1)": {name: waveform_stats(trace, "I(B_JSL1)", "A", name) for name in WINDOWS_PS},
        "I(B_JSL8)": {name: waveform_stats(trace, "I(B_JSL8)", "A", name) for name in WINDOWS_PS},
        "V(COMMON_SL)": {name: waveform_stats(trace, "V(COMMON_SL)", "V", name) for name in WINDOWS_PS},
        "V(QBIN)": {name: waveform_stats(trace, "V(QBIN)", "V", name) for name in WINDOWS_PS},
    }
    if active is not None:
        series["I(LSL|XBVM1)"]["derived_source_label"] = "I(L_SL|XBVM1)"
    if quiet is not None:
        series["I_quiet_total"]["formula"] = "samplewise I(L_SL|XBVM2)+I(L_SL|XBVM3)+I(L_SL|XBVM4) from immutable raw"
    return {"series": series, "source_sum_formula": "I_quiet_total=sum(I(L_SL|XBVM2..4))", "no_interpolation": True}


def port_work(trace: RawTrace) -> dict[str, object]:
    voltage = values(trace, "V(QBIN)")
    current = values(trace, "I(LIN|XBQ1)")
    if voltage is None or current is None:
        return {name: unknown("V(QBIN)*I(LIN|XBQ1)", "J", name) for name in ("EARLY_TRIGGER", "FULL_READ")}
    product = tuple(voltage[index] * current[index] for index in range(len(voltage)))
    result = {}
    for name in ("EARLY_TRIGGER", "FULL_READ"):
        indices = idx_for(trace, name)
        result[name] = {
            "status": "DERIVED",
            "formula": "integral(V(QBIN)*I(LIN|XBQ1)*dt)",
            "unit": "J",
            "value_J": integrate(trace.time, product, indices),
            "window_ps": list(WINDOWS_PS[name]),
            "actual_grid": True,
            "label": "DERIVED port-work diagnostic; not a universal trigger-energy threshold",
        }
    return result


def regeneration_metrics(trace: RawTrace) -> dict[str, object]:
    l2 = values(trace, "I(L2|XBQ1)")
    ib = values(trace, "I(IB|XBQ1)")
    l1 = values(trace, "I(L1|XBQ1)")
    if l2 is None or ib is None or l1 is None:
        kcl = None
    else:
        kcl = tuple(l2[index] - ib[index] - l1[index] for index in range(len(l2)))
    result: dict[str, object] = {
        "KCL_residual": {name: waveform_stats(trace, "I(L2)-I(IB)-I(L1)", "A", name, kcl) if kcl is not None else unknown("I(L2)-I(IB)-I(L1)", "A", name) for name in WINDOWS_PS},
        "KCL_formula": "I(L2)-I(IB)-I(L1)",
        "I(L2)": {name: waveform_stats(trace, "I(L2|XBQ1)", "A", name) for name in WINDOWS_PS},
        "BJ2_phase": relative_phase(trace, "P(BJ2|XBQ1)"),
        "BJ2_voltage": {name: waveform_stats(trace, "V(BJ2|XBQ1)", "V", name) for name in WINDOWS_PS},
        "I(BJ2)": {name: waveform_stats(trace, "I(BJ2|XBQ1)", "A", name) for name in WINDOWS_PS},
        "I(RJ2)": {name: waveform_stats(trace, "I(RJ2|XBQ1)", "A", name) for name in WINDOWS_PS},
        "I(L3)": {name: waveform_stats(trace, "I(L3|XBQ1)", "A", name) for name in WINDOWS_PS},
        "V(QBOUT)": {name: waveform_stats(trace, "V(QBOUT)", "V", name) for name in WINDOWS_PS},
        "same_jj_phase_area_BJ2": {name: phase_area(trace, "P(BJ2|XBQ1)", "V(BJ2|XBQ1)", name) for name in ("FULL_READ", "FULL_FINAL")},
    }
    return result


def descriptive_peak_order(trace: RawTrace) -> dict[str, object]:
    labels = {
        "BJ1_voltage": ("V(BJ1|XBQ1)", "V"),
        "L1_current": ("I(L1|XBQ1)", "A"),
        "L2_current": ("I(L2|XBQ1)", "A"),
        "BJ2_voltage": ("V(BJ2|XBQ1)", "V"),
        "QBOUT_voltage": ("V(QBOUT)", "V"),
    }
    for stage in range(1, 7):
        labels[f"JTL{stage}_OUT_voltage"] = (f"V(JTL{stage}_OUT)", "V")
    result: dict[str, object] = {
        "status": "DERIVED",
        "rule": "time_of_max of raw signal in registered window; descriptive peak diagnostic, not event onset or causal ordering",
        "windows": {},
    }
    for window_name in ("EARLY_TRIGGER", "FULL_READ", "FULL_FINAL"):
        result["windows"][window_name] = {}
        for name, (label, unit) in labels.items():
            stats = waveform_stats(trace, label, unit, window_name)
            if stats.get("status") == "DERIVED":
                result["windows"][window_name][name] = {"time_of_max_ps": stats["time_of_max_ps"], "max": stats["max"], "unit": unit}
            else:
                result["windows"][window_name][name] = stats
    result["causal_order_classification"] = "UNKNOWN; no threshold/onset criterion is registered"
    return result


def downstream_metrics(trace: RawTrace) -> dict[str, object]:
    stages: dict[str, object] = {}
    for stage in range(1, 7):
        h = f"XJTL1_{stage}"
        stage_record: dict[str, object] = {"output_voltage": {name: waveform_stats(trace, f"V(JTL{stage}_OUT)", "V", name) for name in WINDOWS_PS}}
        for jj in ("B01", "B02"):
            p = f"P({jj}|{h})"
            v = f"V({jj}|{h})"
            i = f"I({jj}|{h})"
            stage_record[jj] = {
                "phase_raw_rad": {name: waveform_stats(trace, p, "rad", name) for name in WINDOWS_PS},
                "voltage": {name: waveform_stats(trace, v, "V", name) for name in WINDOWS_PS},
                "current": {name: waveform_stats(trace, i, "A", name) for name in WINDOWS_PS},
                "same_jj_phase_area": {name: phase_area(trace, p, v, name) for name in ("FULL_READ", "FULL_FINAL")},
            }
        stages[f"JTL{stage}"] = stage_record
    terminal = {
        "V(JTL6_OUT)": {name: waveform_stats(trace, "V(JTL6_OUT)", "V", name) for name in WINDOWS_PS},
        "I(R_TERM)": {name: waveform_stats(trace, "I(R_TERM)", "A", name) for name in WINDOWS_PS},
        "terminal_voltage_area": {name: waveform_stats(trace, "V(JTL6_OUT)", "V", name) for name in ("FULL_READ", "FULL_FINAL")},
        "terminal_area_note": "node/termination diagnostic; not a same-JJ SFQ certification",
    }
    return {"stages": stages, "terminal": terminal, "classification": "INCONCLUSIVE/UNKNOWN without frozen SFQ acceptance tolerance and timestep convergence", "no_event_count": True}


def main() -> int:
    raw_qa_path = EXP / "analysis/raw_qa.json"
    if not raw_qa_path.is_file():
        raise RuntimeError("raw QA must run before analysis")
    raw_qa = json.loads(raw_qa_path.read_text(encoding="utf-8"))
    if raw_qa.get("artifact_validity") != "VALID":
        raise RuntimeError("raw artifact is not VALID")
    traces = {run_id: read_csv(EXP / "runs" / directory / "raw.csv") for run_id, (directory, _, _, _) in RUNS.items()}
    metrics: dict[str, object] = {
        "schema": "qb-rj1-l1-local-sensitivity-metrics-v1",
        "experiment_id": EXP.name,
        "created_at_local": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "phase_policy": "P(...) raw radians; independent continuous_unwrap per run; display/relative turns=rad/(2*pi); never SFQ count",
        "window_policy": {name: {"start_ps": bounds[0], "end_ps": bounds[1], "half_open": True} for name, bounds in WINDOWS_PS.items()},
        "integration_policy": "actual stored time grid trapezoid; no fixed-dt assumption",
        "runs": {},
        "historical_nominal_reference": {
            "path": str(EXP / "inputs/historical_array_reference_raw.csv"),
            "sha256": sha256(EXP / "inputs/historical_array_reference_raw.csv"),
            "role": "reproducibility cross-check only; does not replace new NOMINAL",
        },
        "event_count": "NOT_COMPUTED",
        "optimization": "NOT_PERFORMED",
    }
    for run_id, (directory, rj1, l1, purpose) in RUNS.items():
        trace = traces[run_id]
        metrics["runs"][run_id] = {
            "run_directory": f"runs/{directory}",
            "parameters": {"RJ1_ohm": rj1, "L1_pH": l1},
            "purpose": purpose,
            "raw_sha256": sha256(EXP / "runs" / directory / "raw.csv"),
            "source_interface": source_metrics(trace),
            "qbin_port_work": port_work(trace),
            "BJ1": {
                "relative_phase": relative_phase(trace, "P(BJ1|XBQ1)"),
                "voltage": {name: waveform_stats(trace, "V(BJ1|XBQ1)", "V", name) for name in WINDOWS_PS},
                "positive_voltage_duration": {name: positive_voltage_duration(trace, "V(BJ1|XBQ1)", name) for name in ("EARLY_TRIGGER", "FULL_READ", "FULL_FINAL")},
                "I(RJ1)": {name: waveform_stats(trace, "I(RJ1|XBQ1)", "A", name) for name in WINDOWS_PS},
                "same_jj_phase_area": {name: phase_area(trace, "P(BJ1|XBQ1)", "V(BJ1|XBQ1)", name) for name in ("FULL_READ", "FULL_FINAL")},
            },
            "L1": l1_metrics(trace),
            "regeneration": regeneration_metrics(trace),
            "descriptive_peak_order": descriptive_peak_order(trace),
            "downstream": downstream_metrics(trace),
        }

    # Exact-grid comparison is a registered prerequisite for pointwise family plots.
    reference_time = traces["NOMINAL"].time
    metrics["exact_time_grid"] = {
        run_id: {"same_as_nominal": trace.time == reference_time, "sample_count": trace.sample_count, "time_start_s": trace.time[0], "time_end_s": trace.time[-1]}
        for run_id, trace in traces.items()
    }
    metrics["status"] = "PASS" if all(item["same_as_nominal"] for item in metrics["exact_time_grid"].values()) else "INCONCLUSIVE"
    write_once(EXP / "analysis/metrics.json", json.dumps(metrics, indent=2, ensure_ascii=False, allow_nan=False) + "\n")

    transformations = {
        "schema": "qb-rj1-l1-local-sensitivity-transformation-registry-v1",
        "experiment_id": EXP.name,
        "raw_mutation": False,
        "interpolation": False,
        "resampling": False,
        "smoothing": False,
        "time_alignment": False,
        "registered_derived_operations": [
            "I_quiet_total is samplewise sum of raw I(L_SL|XBVM2..4)",
            "KCL residual is I(L2)-I(IB)-I(L1)",
            "phase display/progression independently continuous_unwraps raw radians then divides by 2*pi",
            "waveform areas and W_QBIN use actual-time trapezoid integration",
            "zoom CSVs, when generated, are exact stored-row half-open window slices only",
        ],
        "event_detection": "none",
        "event_count": "none",
    }
    write_once(EXP / "analysis/transformation_registry.json", json.dumps(transformations, indent=2, ensure_ascii=False) + "\n")

    execution = json.loads((EXP / "analysis/execution_summary.json").read_text(encoding="utf-8"))
    provenance = {
        "schema": "qb-rj1-l1-local-sensitivity-analysis-provenance-v1",
        "experiment_id": EXP.name,
        "created_at_local": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "head_at_analysis": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip(),
        "preflight_path": "analysis/preflight.json",
        "preflight_sha256": sha256(EXP / "analysis/preflight.json"),
        "deck_diff_qa_path": "analysis/deck_diff_qa.json",
        "deck_diff_qa_sha256": sha256(EXP / "analysis/deck_diff_qa.json"),
        "execution_summary_path": "analysis/execution_summary.json",
        "execution_summary_sha256": sha256(EXP / "analysis/execution_summary.json"),
        "raw_qa_path": "analysis/raw_qa.json",
        "raw_qa_sha256": sha256(raw_qa_path),
        "raw_hashes_pre_analysis": raw_qa["pre_analysis_sha256"],
        "raw_hashes_at_analysis": {run_id: sha256(EXP / "runs" / directory / "raw.csv") for run_id, (directory, _, _, _) in RUNS.items()},
        "raw_unchanged_through_analysis": raw_qa["pre_analysis_sha256"] == {run_id: sha256(EXP / "runs" / directory / "raw.csv") for run_id, (directory, _, _, _) in RUNS.items()},
        "execution_summary_status": execution.get("status"),
        "solver_solve_invocations": execution.get("solver_solve_invocations"),
        "solver": {"path": str(REPO / "build/josim-cli"), "sha256": "48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2"},
        "fixture": {
            "experiment": "test/exploration/bvmsim-jm2-single-vs-4bvm-shared-sl-v1-20260907",
            "array_deck_sha256": "85227538d48d69251f4276b94b28adfc83cd25f95aa6609fa9eb2375c873f1cf",
            "array_raw_sha256": "8543abc6d7a7d276c0bfa3159a4d3d37d569200e5fa30082466e66df8ab24dc2",
        },
        "source_identity": {
            "bvm_variant": {"path": "test/exploration/bvmsim-jm2-connected-single-ab-v1-20260903/variants/bvm_jm2_connected.cir", "sha256": "0093a45cc3910448b484d8bd004c6df8c22358bacc8b3ed5e23912dcab805d54"},
            "jjmit": {"path": "circuits/models/jjmit.cir", "sha256": "19862d1fd1f1f44dfa1523848d7d3b5e2594a6c5da8fdd80144b449e5312a336"},
            "bq_source": {"path": "BVMSim/BQ.cir", "sha256": "f3dcbf5f9bb3898faf5194b5f7c4771df3fa1ed16150496de4b52cb6f7256dfd"},
            "jtl": {"path": "BVMSim/library_josim/jtl2.cir", "sha256": "ffd31f8eda2a86ca0133342be1ce678831b7237a53911eda046d2bff8454855a"},
            "bq_parameterized": {"path": "inputs/BQ_parameterized.cir", "sha256": "ff67dbbe42feb6a33d4573fdfd84e4657d1d0fd241f9b497e231b23a936afe10"},
        },
        "interpretation_ceiling": "fixed historical simulation only; no mechanism, hardware, SFQ count, optimization or convergence claim",
    }
    write_once(EXP / "analysis/provenance.json", json.dumps(provenance, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"status": metrics["status"], "run_count": len(RUNS), "event_count": "NOT_COMPUTED", "metrics": "analysis/metrics.json"}, ensure_ascii=False))
    return 0 if metrics["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
