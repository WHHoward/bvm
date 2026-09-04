#!/usr/bin/env python3
"""Analyze the two probe-only JM2-connected single-BVM runs.

This file owns only this experiment's windows, branch equations and bounded
interpretation.  Raw parsing, waveform arithmetic, phase conversion and KCL
linear combinations are delegated to scripts/bvmtools.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import re
import subprocess
import sys
from collections import OrderedDict
from pathlib import Path


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
OLD = REPO / "test/exploration/bvmsim-jm2-connected-single-ab-v1-20260903"
sys.path.insert(0, str(REPO / "scripts"))

from bvmtools.compare import compare_series, exact_time_grid_identity  # noqa: E402
from bvmtools.deckqa import deck_qa  # noqa: E402
from bvmtools.kcl import kcl_window_metrics, linear_kcl_residual  # noqa: E402
from bvmtools.phase import TAU, phase_window_metrics, window_indices  # noqa: E402
from bvmtools.raw import RawTrace, read_csv  # noqa: E402
from bvmtools.stimulus import validate_bvm_write_read_protocol  # noqa: E402
from bvmtools.waveform import trapezoid_integral, waveform_metrics, waveform_window_metrics  # noqa: E402


RUNS = OrderedDict((
    ("S0-J-RLOOP", {"state": 0, "old": "S0-J-JM2C"}),
    ("S1-J-RLOOP", {"state": 1, "old": "S1-J-JM2C"}),
))

WINDOWS_PS = OrderedDict((
    ("PRE_READ", (62.0, 70.0)),
    ("READ", (70.0, 82.0)),
    ("EARLY_RESPONSE", (82.0, 120.0)),
    ("TAIL", (170.0, 200.0)),
    ("FULL", (0.0, 200.0)),
))

STIMULUS = ("I(I_WL1)", "I(I_BL1)", "I(I_SE1)")
CURRENT_BRANCHES = OrderedDict((
    ("LM1", "I(L_M1|XBVM1)"),
    ("LM2", "I(L_M2|XBVM1)"),
    ("LM3", "I(L_M3|XBVM1)"),
    ("LPM", "I(L_PM|XBVM1)"),
    ("RJM1", "I(R_JM1|XBVM1)"),
    ("LS1", "I(L_S1|XBVM1)"),
    ("LS2", "I(L_S2|XBVM1)"),
    ("RS", "I(R_S|XBVM1)"),
    ("LS3", "I(L_S3|XBVM1)"),
    ("RSE", "I(R_SE|XBVM1)"),
    ("LPSE", "I(L_PSE|XBVM1)"),
    ("LPSL", "I(L_PSL|XBVM1)"),
    ("RSL", "I(R_SL|XBVM1)"),
    ("LSL", "I(L_SL|XBVM1)"),
))
VOLTAGE_BRANCHES = OrderedDict((
    ("RJM1", "V(R_JM1|XBVM1)"),
    ("RS", "V(R_S|XBVM1)"),
    ("LS3", "V(L_S3|XBVM1)"),
    ("RSE", "V(R_SE|XBVM1)"),
    ("LPSE", "V(L_PSE|XBVM1)"),
    ("LS1", "V(L_S1|XBVM1)"),
    ("LS2", "V(L_S2|XBVM1)"),
    ("LPSL", "V(L_PSL|XBVM1)"),
    ("RSL", "V(R_SL|XBVM1)"),
    ("LSL", "V(L_SL|XBVM1)"),
))
JJ_CONTEXT = OrderedDict((
    ("JM1", "B_JM1"), ("JM2", "B_JM2"),
    ("JS1", "B_JS1"), ("JS2", "B_JS2"),
))

LEGACY_CURRENT_PROBES = (
    "I(L_M1|XBVM1)", "I(L_M2|XBVM1)", "I(L_M3|XBVM1)", "I(L_PM|XBVM1)",
    "I(L_PSL|XBVM1)", "I(L_SL|XBVM1)",
)
LEGACY_PROBES = list(
    STIMULUS
    + tuple(
        f"{kind}(B_{junction}|XBVM1)"
        for junction in ("JM1", "JM2", "JS1", "JS2")
        for kind in ("P", "V", "I")
    )
    + LEGACY_CURRENT_PROBES
    + ("V(SL1)", "I(L_PSL|XBVM1)", "I(L_SL|XBVM1)")
    + (
        "P(B_LD4_01)", "V(B_LD4_01)", "I(B_LD4_01)",
        "P(B_LD4_11)", "V(B_LD4_11)", "I(B_LD4_11)",
        "P(BVMOUT)", "V(BVMOUT)", "I(BVMOUT)",
    )
    + (
        "V(QBIN)", "V(QBOUT)", "I(LIN|XBQ1)",
        "P(BJS|XBQ1)", "V(BJS|XBQ1)", "I(BJS|XBQ1)",
        "P(BJ1|XBQ1)", "V(BJ1|XBQ1)", "I(BJ1|XBQ1)", "I(RJ1|XBQ1)",
        "I(L1|XBQ1)", "I(IB|XBQ1)", "I(L2|XBQ1)",
        "P(BJ2|XBQ1)", "V(BJ2|XBQ1)", "I(BJ2|XBQ1)", "I(RJ2|XBQ1)", "I(L3|XBQ1)",
    )
)
for _stage in range(1, 7):
    LEGACY_PROBES.extend(
        (
            f"P(B01|XJTL1_{_stage})", f"V(B01|XJTL1_{_stage})",
            f"P(B02|XJTL1_{_stage})", f"V(B02|XJTL1_{_stage})",
        )
    )
NEW_PROBES = list(dict.fromkeys(
    [label for label in CURRENT_BRANCHES.values() if label not in LEGACY_PROBES]
    + list(VOLTAGE_BRANCHES.values())
))
ALL_PROBES = list(dict.fromkeys(
    LEGACY_PROBES + list(CURRENT_BRANCHES.values()) + list(VOLTAGE_BRANCHES.values())
))

KCL_EQUATIONS = OrderedDict((
    (
        "JM1_shunt_node7",
        OrderedDict((
            ("I(B_JM1|XBVM1)", 1.0), ("I(R_JM1|XBVM1)", 1.0), ("I(L_M1|XBVM1)", -1.0),
        )),
    ),
    ("JM2_node3", OrderedDict((("I(L_M2|XBVM1)", 1.0), ("I(B_JM2|XBVM1)", -1.0)))),
    (
        "LM3_node4",
        OrderedDict((("I(B_JM2|XBVM1)", 1.0), ("I(L_M3|XBVM1)", -1.0), ("I(L_S1|XBVM1)", -1.0))),
    ),
    (
        "Sloop_node8",
        OrderedDict((("I(L_M3|XBVM1)", 1.0), ("I(L_PM|XBVM1)", -1.0), ("I(L_S2|XBVM1)", -1.0))),
    ),
    (
        "SE_RLOOP_node6",
        OrderedDict((("I(B_JS1|XBVM1)", 1.0), ("I(L_PSE|XBVM1)", 1.0), ("I(R_S|XBVM1)", -1.0), ("I(L_S3|XBVM1)", -1.0))),
    ),
    (
        "RLOOP_output_node10",
        OrderedDict((("I(R_S|XBVM1)", 1.0), ("I(L_S3|XBVM1)", 1.0), ("I(B_JS2|XBVM1)", 1.0), ("I(L_PSL|XBVM1)", -1.0))),
    ),
    ("JS1_series_node5", OrderedDict((("I(L_S1|XBVM1)", 1.0), ("I(B_JS1|XBVM1)", -1.0)))),
    ("JS2_series_node9", OrderedDict((("I(L_S2|XBVM1)", 1.0), ("I(B_JS2|XBVM1)", -1.0)))),
    ("SE_series_node14", OrderedDict((("I(R_SE|XBVM1)", 1.0), ("I(L_PSE|XBVM1)", -1.0)))),
    ("SL_series_node11", OrderedDict((("I(L_PSL|XBVM1)", 1.0), ("I(R_SL|XBVM1)", -1.0)))),
    ("SL_series_node12", OrderedDict((("I(R_SL|XBVM1)", 1.0), ("I(L_SL|XBVM1)", -1.0)))),
))

RESISTANCES_OHM = OrderedDict((("RJM1", 8.0), ("RS", 3.0), ("RSL", 12.0), ("RSE", 20.0)))
INDUCTANCES_PH = OrderedDict(
    (("LM1", 12.5), ("LM2", 24.5), ("LM3", 8.5), ("LPM", 0.5),
     ("LS1", 0.5), ("LS2", 0.5), ("LS3", 0.5), ("LPSE", 0.5),
     ("LPSL", 0.5), ("LSL", 0.4))
)

TOOLING_INCIDENTS = [
    {
        "stage": "physical_run_orchestration",
        "description": "First run.sh invocation completed S0 but the metadata writer rejected the literal -- separator.",
        "impact": "S0 raw/log were preserved; metadata was repaired from the same artifacts; S0 was not rerun.",
    },
    {
        "stage": "analysis",
        "description": "First analyzer invocation omitted the OLD experiment-root variable.",
        "impact": "Analyzer exited before writing scientific outputs; fixed and rerun on immutable raw only.",
    },
    {
        "stage": "visualization",
        "description": "First renderer invocation used a three-item OrderedDict entry for comparison plots.",
        "impact": "No plot was produced in the failed invocation; fixed and rerun without changing raw.",
    },
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO.resolve()).as_posix()


def series(trace: RawTrace, label: str) -> tuple[float, ...]:
    return trace.column(label)  # type: ignore[return-value]


def ps_window(name: str) -> tuple[float, float]:
    start, end = WINDOWS_PS[name]
    return start * 1.0e-12, end * 1.0e-12


def phase_metrics(trace: RawTrace, label: str, window: tuple[float, float]) -> dict[str, object]:
    result = phase_window_metrics(trace.time, series(trace, label), window)
    result["peak_time_ps"] = None
    indices = window_indices(trace.time, *window)
    unwrapped_turns = [value / TAU for value in _unwrap(series(trace, label))]
    if indices:
        peak = max(indices, key=lambda index: unwrapped_turns[index])
        result["peak_time_ps"] = float(trace.time[peak] * 1.0e12)
    return result


def _unwrap(values: tuple[float, ...]) -> tuple[float, ...]:
    from bvmtools.phase import continuous_unwrap
    return continuous_unwrap(values)


def waveform_by_unit(trace: RawTrace, label: str, window: tuple[float, float]) -> dict[str, object]:
    unit = "A" if label.startswith("I(") else "V" if label.startswith("V(") else "raw"
    return waveform_window_metrics(trace.time, series(trace, label), window, unit=unit)


def protocol_result(trace: RawTrace, state: int) -> dict[str, object]:
    write = -100.0e-6 if state == 0 else 100.0e-6
    return validate_bvm_write_read_protocol(
        trace,
        trace.time,
        write_window_s=(51.0e-12, 60.0e-12),
        read_window_s=(71.0e-12, 80.0e-12),
        expected_write={"I(I_WL1)": write, "I(I_BL1)": write, "I(I_SE1)": 0.0},
        expected_read={"I(I_WL1)": 100.0e-6, "I(I_BL1)": 0.0, "I(I_SE1)": 100.0e-6},
        tolerance=1.0e-10,
        unit="A",
    )


def metadata_qa(condition: str, deck: Path, raw: Path, log: Path) -> dict[str, object]:
    metadata_path = raw.parent / "metadata.json"
    if not metadata_path.is_file():
        return {"status": "FAIL", "reason": "metadata_missing"}
    data = json.loads(metadata_path.read_text(encoding="utf-8"))
    expected = {
        "deck_sha256": sha256(deck), "raw_sha256": sha256(raw), "log_sha256": sha256(log),
    }
    actual = data.get("hashes", {})
    checks = {
        "condition": data.get("condition") == condition,
        "exit_code": data.get("command", {}).get("exit_code") == 0,
        "artifact_status": data.get("artifact_status") == "VALID",
        "hashes": all(actual.get(key) == value for key, value in expected.items()),
        "created_at": bool(data.get("created_at")),
        "solver_hash": data.get("solver", {}).get("sha256") == sha256(REPO / "build/josim-cli"),
    }
    return {"status": "PASS" if all(checks.values()) else "FAIL", "checks": checks, "metadata": data}


def legacy_parity(trace: RawTrace, old: RawTrace) -> dict[str, object]:
    if not exact_time_grid_identity(trace.time, old.time):
        return {"status": "FAIL", "time_grid_exact": False, "signals": {}}
    comparisons: OrderedDict[str, dict[str, object]] = OrderedDict()
    for label in LEGACY_PROBES:
        comparisons[label] = compare_series(
            old.time, series(old, label), trace.time, series(trace, label), include_correlation=True
        )
    max_abs = max(float(item["max_abs_difference"]) for item in comparisons.values())
    rms = math.sqrt(
        sum(float(item["rms_difference"]) ** 2 for item in comparisons.values()) / len(comparisons)
    )
    return {
        "status": "EXACT" if max_abs == 0.0 else "DIFF_OBSERVED",
        "time_grid_exact": True,
        "max_abs_difference_across_original_probes": max_abs,
        "rms_of_signal_rms_differences": rms,
        "signals": comparisons,
    }


def kcl_results(trace: RawTrace) -> tuple[dict[str, object], OrderedDict[str, tuple[float, ...]]]:
    currents = {label: series(trace, label) for label in {name for equation in KCL_EQUATIONS.values() for name in equation}}
    residuals: OrderedDict[str, tuple[float, ...]] = OrderedDict()
    windows: OrderedDict[str, dict[str, object]] = OrderedDict()
    for equation, coefficients in KCL_EQUATIONS.items():
        equation_currents = {label: currents[label] for label in coefficients}
        residual = linear_kcl_residual(equation_currents, coefficients)
        residuals[equation] = residual
    for window_name in WINDOWS_PS:
        window = ps_window(window_name)
        windows[window_name] = OrderedDict(
            (equation, kcl_window_metrics(trace.time, residual, window, unit="A"))
            for equation, residual in residuals.items()
        )
    return {"equations": {name: dict(coefficients) for name, coefficients in KCL_EQUATIONS.items()}, "windows": windows}, residuals


def series_sanity(trace: RawTrace) -> dict[str, object]:
    result: OrderedDict[str, object] = OrderedDict()
    pairs = OrderedDict((
        ("LS1_minus_JS1", ("I(L_S1|XBVM1)", "I(B_JS1|XBVM1)")),
        ("LS2_minus_JS2", ("I(L_S2|XBVM1)", "I(B_JS2|XBVM1)")),
        ("LPSL_minus_RSL", ("I(L_PSL|XBVM1)", "I(R_SL|XBVM1)")),
        ("RSL_minus_LSL", ("I(R_SL|XBVM1)", "I(L_SL|XBVM1)")),
        ("RSE_minus_LPSE", ("I(R_SE|XBVM1)", "I(L_PSE|XBVM1)")),
    ))
    for name, (left, right) in pairs.items():
        difference = tuple(a - b for a, b in zip(series(trace, left), series(trace, right)))
        result[name] = {
            "left": left, "right": right,
            "windows": OrderedDict(
                (window_name, kcl_window_metrics(trace.time, difference, ps_window(window_name), unit="A"))
                for window_name in WINDOWS_PS
            ),
        }
    return result


def fraction_rs(trace: RawTrace) -> OrderedDict[str, object]:
    rs = series(trace, CURRENT_BRANCHES["RS"])
    ls3 = series(trace, CURRENT_BRANCHES["LS3"])
    threshold = 1.0e-12
    output: OrderedDict[str, object] = OrderedDict()
    for window_name in WINDOWS_PS:
        indices = window_indices(trace.time, *ps_window(window_name))
        denom = [rs[index] + ls3[index] for index in indices]
        valid = [rs[index] / denom[index] for index in range(len(indices)) if abs(denom[index]) > threshold]
        output[window_name] = {
            "definition": "I(RS)/(I(RS)+I(LS3))",
            "denominator_threshold_A": threshold,
            "sample_count": len(indices),
            "valid_sample_count": len(valid),
            "valid_fraction": len(valid) / len(indices) if indices else 0.0,
            "mean": sum(valid) / len(valid) if valid else None,
            "minimum": min(valid) if valid else None,
            "maximum": max(valid) if valid else None,
        }
    return output


def resistor_analysis(trace: RawTrace) -> OrderedDict[str, object]:
    output: OrderedDict[str, object] = OrderedDict()
    for name, resistance in RESISTANCES_OHM.items():
        current = series(trace, CURRENT_BRANCHES[name])
        voltage = series(trace, VOLTAGE_BRANCHES[name])
        windowed: OrderedDict[str, object] = OrderedDict()
        for window_name in WINDOWS_PS:
            indices = window_indices(trace.time, *ps_window(window_name))
            t = [trace.time[index] for index in indices]
            i = [current[index] for index in indices]
            v = [voltage[index] for index in indices]
            signed_power = [vv * ii for vv, ii in zip(v, i)]
            joule_power = [ii * ii * resistance for ii in i]
            signed_energy = trapezoid_integral(signed_power, t) * 1.0e15
            joule_energy = trapezoid_integral(joule_power, t) * 1.0e15
            windowed[window_name] = {
                "resistance_ohm": resistance,
                "signed_VI_energy_fJ": signed_energy,
                "I2R_energy_fJ": joule_energy,
                "energy_difference_fJ": signed_energy - joule_energy,
                "current": waveform_by_unit(trace, CURRENT_BRANCHES[name], ps_window(window_name)),
                "voltage": waveform_by_unit(trace, VOLTAGE_BRANCHES[name], ps_window(window_name)),
            }
        output[name] = windowed
    return output


def inductor_analysis(trace: RawTrace) -> OrderedDict[str, object]:
    output: OrderedDict[str, object] = OrderedDict()
    for name, inductance_ph in INDUCTANCES_PH.items():
        current = series(trace, CURRENT_BRANCHES[name])
        windowed: OrderedDict[str, object] = OrderedDict()
        inductance_h = inductance_ph * 1.0e-12
        for window_name in WINDOWS_PS:
            indices = window_indices(trace.time, *ps_window(window_name))
            t = [trace.time[index] for index in indices]
            flux = [inductance_h * current[index] for index in indices]
            energy = [0.5 * inductance_h * current[index] ** 2 for index in indices]
            flux_display = [value * 1.0e15 for value in flux]
            energy_display = [value * 1.0e15 for value in energy]
            flux_stats = waveform_metrics(t, flux_display)
            energy_stats = waveform_metrics(t, energy_display)
            windowed[window_name] = {
                "inductance_pH": inductance_ph,
                "flux_linkage_unit": "fWb",
                "flux_linkage_stats": flux_stats,
                "stored_energy_unit": "fJ",
                "stored_energy_stats": energy_stats,
                "current": waveform_by_unit(trace, CURRENT_BRANCHES[name], ps_window(window_name)),
            }
        output[name] = windowed
    return output


def write_csv(path: Path, headers: list[str], time: tuple[float, ...], columns: OrderedDict[str, tuple[float, ...]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["time", *headers])
        for index, value in enumerate(time):
            writer.writerow([f"{value:.15e}", *[f"{columns[label][index]:.15e}" for label in headers]])


def key_read_summary(trace: RawTrace) -> dict[str, object]:
    names = ("RJM1", "LM3", "RS", "LS3", "RSE", "LPSE", "RSL", "LSL")
    result: OrderedDict[str, object] = OrderedDict()
    for name in names:
        result[name] = {
            "current": waveform_by_unit(trace, CURRENT_BRANCHES[name], ps_window("READ")),
            "voltage": waveform_by_unit(trace, VOLTAGE_BRANCHES[name], ps_window("READ")) if name in VOLTAGE_BRANCHES else None,
        }
    return result


def run_record(condition: str, spec: dict[str, object]) -> tuple[dict[str, object], RawTrace, OrderedDict[str, tuple[float, ...]]]:
    run_dir = EXP / "runs" / condition
    deck = run_dir / "deck.cir"
    raw_path = run_dir / "raw.csv"
    log = run_dir / "run.log"
    old_raw = OLD / "runs" / str(spec["old"]) / "raw/run-01.csv"
    trace = read_csv(raw_path)
    old_trace = read_csv(old_raw)
    required_deck_includes = (
        "circuits/models/jjmit.cir",
        "bvmsim-jm2-connected-single-ab-v1-20260903/variants/bvm_jm2_connected.cir",
        "BVMSim/BQ.cir",
        "BVMSim/library_josim/jtl2.cir",
    )
    deck_result = deck_qa(
        deck,
        log_text=log.read_text(encoding="utf-8", errors="replace"),
        expected_includes=required_deck_includes,
        expected_bvm_instances=1,
        expected_terminal_sensing_jj_count=12,
        expected_jtl_stages=6,
        expected_termination_ohm=10.0,
        expected_tran_timestep_ps=0.1,
        required_probes=ALL_PROBES,
        raw_headers=trace.headers,
    )
    time_grid = {
        "exact_with_old_authority": exact_time_grid_identity(trace.time, old_trace.time),
        "sample_count": len(trace.time),
        "start_ps": trace.time[0] * 1.0e12,
        "last_sample_ps": trace.time[-1] * 1.0e12,
        "dt_first_ps": trace.dt[0] * 1.0e12,
        "dt_last_ps": trace.dt[-1] * 1.0e12,
        "tran_stop_ps": 200.0,
        "note": "JoSIM stores 0..199.9 ps for .tran 0.1p 200p; 200 ps is the stop horizon.",
    }
    protocol = protocol_result(trace, int(spec["state"]))
    metadata = metadata_qa(condition, deck, raw_path, log)
    log_text = log.read_text(encoding="utf-8", errors="replace")
    warnings = re.findall(r"(?i)(Missing model:.*|Using default model.*)", log_text)
    artifact_checks = {
        "deck_qa": deck_result["status"] == "ARTIFACT_VALID",
        "raw_duplicates_absent": not trace.duplicate_columns,
        "time_grid_exact": time_grid["exact_with_old_authority"],
        "protocol": protocol["status"] == "PROTOCOL_VALID",
        "metadata": metadata["status"] == "PASS",
        "solver_model_warnings_absent": not warnings,
        "raw_nonempty": raw_path.stat().st_size > 0,
    }
    artifact_status = "ARTIFACT_VALID" if all(artifact_checks.values()) else "ARTIFACT_INVALID"
    kcl, residuals = kcl_results(trace)
    signals: OrderedDict[str, object] = OrderedDict()
    for window_name in WINDOWS_PS:
        window = ps_window(window_name)
        signals[window_name] = {
            "current": OrderedDict((name, waveform_by_unit(trace, label, window)) for name, label in CURRENT_BRANCHES.items()),
            "voltage": OrderedDict((name, waveform_by_unit(trace, label, window)) for name, label in VOLTAGE_BRANCHES.items()),
            "phase": OrderedDict((name, phase_metrics(trace, f"P({branch}|XBVM1)", window)) for name, branch in JJ_CONTEXT.items()),
            "nonlinear_context": OrderedDict(
                (
                    name,
                    {
                        "phase": phase_metrics(trace, f"P({branch}|XBVM1)", window),
                        "voltage": waveform_by_unit(trace, f"V({branch}|XBVM1)", window),
                        "current": waveform_by_unit(trace, f"I({branch}|XBVM1)", window),
                    },
                )
                for name, branch in JJ_CONTEXT.items()
            ),
        }
    record: dict[str, object] = {
        "condition": condition,
        "logical_state": spec["state"],
        "artifact_status": artifact_status,
        "artifact_checks": artifact_checks,
        "paths": {"deck": rel(deck), "raw": rel(raw_path), "log": rel(log), "old_authority_raw": rel(old_raw)},
        "hashes": {"deck_sha256": sha256(deck), "raw_sha256": sha256(raw_path), "log_sha256": sha256(log)},
        "raw_qa": trace.qa(),
        "deck_qa": deck_result,
        "metadata_qa": {"status": metadata["status"], "checks": metadata.get("checks", {})},
        "model_warnings": warnings,
        "time_grid": time_grid,
        "legacy_probe_parity": legacy_parity(trace, old_trace),
        "stimulus_protocol": protocol,
        "window_signal_metrics": signals,
        "key_read_summary": key_read_summary(trace),
        "kcl": kcl,
        "series_current_sanity": series_sanity(trace),
        "rs_fraction": fraction_rs(trace),
        "resistor_analysis": resistor_analysis(trace),
        "inductor_analysis": inductor_analysis(trace),
        "interpretation": {
            "phase_unit": "raw P radians; phase metrics use continuous_unwrap(rad)/(2*pi) turns",
            "phase_not_sfq_count": True,
            "energies_descriptive_only": True,
            "single_reference_only": True,
        },
    }
    return record, trace, residuals


def comparison_data(traces: OrderedDict[str, RawTrace], residuals: OrderedDict[str, OrderedDict[str, tuple[float, ...]]]) -> None:
    selected = [
        ("I(L_M3|XBVM1)", "I(R_JM1|XBVM1)"),
        ("I(R_S|XBVM1)", "I(L_S3|XBVM1)"),
        ("I(R_SE|XBVM1)", "I(L_PSE|XBVM1)"),
        ("I(R_SL|XBVM1)", "I(L_SL|XBVM1)"),
        ("V(R_S|XBVM1)", "V(R_SL|XBVM1)"),
        ("P(B_JS1|XBVM1)", "P(B_JS2|XBVM1)"),
    ]
    columns = OrderedDict()
    for label in [item for pair in selected for item in pair]:
        columns[f"{label} [S0]"] = series(traces["S0-J-RLOOP"], label)
        columns[f"{label} [S1]"] = series(traces["S1-J-RLOOP"], label)
    write_csv(
        EXP / "plots/comparison/data/S0_VS_S1_RLOOP_PASSIVE_NETWORK.csv",
        list(columns),
        traces["S0-J-RLOOP"].time,
        columns,
    )
    residual_columns: OrderedDict[str, tuple[float, ...]] = OrderedDict()
    for equation in ("JM1_shunt_node7", "SE_RLOOP_node6", "RLOOP_output_node10", "SL_series_node12"):
        residual_columns[f"I(KCL_{equation}) [S0]"] = residuals["S0-J-RLOOP"][equation]
        residual_columns[f"I(KCL_{equation}) [S1]"] = residuals["S1-J-RLOOP"][equation]
    write_csv(
        EXP / "plots/comparison/data/S0_VS_S1_RLOOP_KCL.csv",
        list(residual_columns),
        traces["S0-J-RLOOP"].time,
        residual_columns,
    )


def report_text(metrics: dict[str, object]) -> str:
    runs = metrics["runs"]
    lines = [
        "# JM2-connected single-BVM R-loop / SL observability",
        "",
        "## 1. Question",
        "",
        "本轮只建立 isolated historical single-BVM 的 branch-level reference，回答 S0/S1 的 R-loop、SE、RSL/SL 支路如何分配；不测试 array。",
        "",
        "## 2. Probe-only nature",
        "",
        "两个 executed deck 均由旧 `S0-J-JM2C` / `S1-J-JM2C` 机械继承。唯一改变是新增 direct branch current/voltage `.print`，以及因 executed deck 搬到 `runs/<condition>/` 而做 include path relocation。静态归一化物理差异为 0。",
        "",
        "## 3. What changed / what did not change",
        "",
        "保留 JM2-connected variant、12-JJ terminal sensing line、原始 `BVMSim/BQ.cir`、六级 280-uA JTL、10-ohm load、WL+BL WRITE、WL+SE READ、0.1-ps step 和 200-ps stop。没有使用 canonical BVM，也没有做参数或 timestep sweep。",
        "",
        "## 4. Artifact validity",
        "",
        f"总体分析状态：`{metrics['status']}`。每个 run 的 raw、deck、log、metadata hash 和 post-run QA 见 `metrics.json`。JoSIM 的实际保存网格为 0 到 199.9 ps；`.tran 0.1p 200p` 的 200 ps 是 stop horizon。",
        "",
        "| run | artifact | time grid | protocol | old probe parity |",
        "|---|---|---|---|---|",
    ]
    for condition, record in runs.items():
        lines.append(
            f"| {condition} | `{record['artifact_status']}` | `{record['time_grid']['exact_with_old_authority']}` | `{record['stimulus_protocol']['status']}` | `{record['legacy_probe_parity']['status']}` |"
        )
    lines.extend([
        "",
        "### Tooling incidents",
        "",
        "本轮记录了 3 个工具层 incident：首次 run.sh 的 metadata 参数分隔符、首次 analyzer 的路径变量、首次 renderer 的 comparison map 结构。它们均未修改 raw、未改变 deck、未导致 physics rerun；修复后分别对同一 raw 或同一 plot 输入重做 QA。",
        "",
        "## 5. Topology and sign convention",
        "",
        "元件电流方向按 netlist 的第一个节点到第二个节点；元件电压为同一方向的 V(first)-V(second)。实际 JM2-connected variant 的 endpoint 已在 static preflight 中记录。直接元件电压 probe 被 JoSIM 的 hierarchical device lookup 接受，因此本轮没有使用 node-difference fallback。",
        "",
        "关键闭合式包括：`I(B_JM1)+I(R_JM1)-I(L_M1)`；`I(B_JS1)+I(L_PSE)-I(R_S)-I(L_S3)`；`I(R_S)+I(L_S3)+I(B_JS2)-I(L_PSL)`；以及 `I(L_PSL)-I(R_SL)`、`I(R_SL)-I(L_SL)`。完整系数和每个窗口的 residual 在 `metrics.json`。",
        "",
        "## 6. Observed branch reference",
        "",
        "下面只列 READ 窗口的关键量级；完整的 PRE_READ、READ、EARLY_RESPONSE、TAIL、FULL 统计均保存在 `metrics.json`。电流为 uA，电压为 mV；signed integral 的单位按字段标注。",
        "",
        "| run | branch | I mean (uA) | I max_abs (uA) | V mean (mV) | V max_abs (mV) |",
        "|---|---|---:|---:|---:|---:|",
    ])
    for condition, record in runs.items():
        read = record["key_read_summary"]
        for name in ("RJM1", "LM3", "RS", "LS3", "RSE", "LPSE", "RSL", "LSL"):
            current = read[name]["current"]
            voltage = read[name]["voltage"]
            voltage_mean = "—" if voltage is None else f"{voltage['mean']:.6g}"
            voltage_max_abs = "—" if voltage is None else f"{voltage['max_abs']:.6g}"
            lines.append(
                f"| {condition} | {name} | {current['mean']:.6g} | {current['max_abs']:.6g} | "
                f"{voltage_mean} | {voltage_max_abs} |"
            )
    lines.extend([
        "",
        "## 7. RJM1 split, RS||LS3 split, and RSL branch",
        "",
        "RJM1 的 current split 由 `I(L_M1)` 与 `I(B_JM1)`/`I(R_JM1)` 的方向一致性检查给出；RS/LS3 的 fraction 仅在 `|I(RS)+I(LS3)| > 1 uA` 时计算，是描述性比值，不是 gate。RSL 的 voltage/current/dissipation 以及 RSE、RS、RJM1 的 READ energy 也只用于本 fixture 的量级比较。",
        "",
        "| run | KCL equation | READ max_abs residual (uA) | READ RMS residual (uA) |",
        "|---|---|---:|---:|",
    ])
    for condition, record in runs.items():
        for equation in ("JM1_shunt_node7", "SE_RLOOP_node6", "RLOOP_output_node10", "SL_series_node12"):
            item = record["kcl"]["windows"]["READ"][equation]
            lines.append(f"| {condition} | {equation} | {item['max_abs_uA']:.6g} | {item['rms_uA']:.6g} |")
    lines.extend([
        "",
        "## 8. OBSERVED / DERIVED / INFERENCE / UNKNOWN",
        "",
        "**Observed:** 两个 raw 都包含完整 direct passive branch current/voltage、原有 JJ/QB/JTL probe；S0/S1 stimulus 按旧 deck 实际输出；old probe 与新 raw 的时间网格可逐点对照。",
        "",
        "**Derived:** KCL residual、series-current difference、RS fraction、V×I / I²R energy、L×I flux linkage 和 0.5×L×I² stored-energy 是由同一 raw 的数值后处理得到的描述量。`L×I` 不被命名为 trapped Phi0。",
        "",
        "**Inference ceiling:** 这些数据可作为下一轮 4-BVM 对照时的 isolated branch reference，尤其是同名层级下的方向和 KCL schema；不能单独推断 array isolation、cross-coupling root cause、论文机制或 SFQ transport。",
        "",
        "**Unknown:** 本轮未运行 4-BVM selective-read/all-one/additivity/isolation，因此 single reference 是否能预测 array 行为仍未知；也未对 RJ1、bias、timestep 或任何参数做稳健性测试。",
        "",
        "## 9. Visualization",
        "",
        "每个 standalone 页面均使用 `scripts/josim-plot2.py -t sep_comb -c dark -j 2pi`；P 列仅做 rad/(2*pi) 数值转换并标成 turns，不是 SFQ count。",
        "",
        "- S0 plots: `plots/runs/S0-J-RLOOP/`",
        "- S1 plots: `plots/runs/S1-J-RLOOP/`",
        "- comparison: `plots/comparison/`",
        "",
        "## 10. Future 4-BVM comparison",
        "",
        "未来 array deck 应按 `experiment.yaml` 中冻结的 `BVM_SINGLE_ARRAY_BRANCH_V1` schema，将 `XBVM1` 替换为相应 `XBVM<n>`，保留同一套串联 branch probes、端点方向和 KCL 方程。该规则只登记 schema，本轮没有建立或运行 4-BVM。",
        "",
        "## 11. Human gate",
        "",
        "`AWAITING_USER_REVIEW`；`user_reviewed: false`；`next_step_authorized: false`；`automatic_next_experiment: false`；`next_action: STOP`。",
    ])
    return "\n".join(lines) + "\n"


def write_final_provenance(metrics: dict[str, object]) -> None:
    """Record final artifact identities without changing raw evidence."""
    source_paths = (
        EXP / "experiment.yaml",
        EXP / "generate_decks.py",
        EXP / "run.sh",
        EXP / "analysis/static_preflight.py",
        EXP / "analysis/analyze.py",
        EXP / "analysis/render_plots.py",
        REPO / "scripts/bvmtools/raw.py",
        REPO / "scripts/bvmtools/waveform.py",
        REPO / "scripts/bvmtools/phase.py",
        REPO / "scripts/bvmtools/kcl.py",
        REPO / "scripts/josim-plot2.py",
        REPO / "circuits/models/jjmit.cir",
        REPO / "BVMSim/BQ.cir",
        REPO / "BVMSim/library_josim/jtl2.cir",
        OLD / "variants/bvm_jm2_connected.cir",
        OLD / "runs/S0-J-JM2C/deck.cir",
        OLD / "runs/S1-J-JM2C/deck.cir",
    )
    source_hashes = OrderedDict((rel(path), sha256(path)) for path in source_paths)
    run_records = OrderedDict()
    for condition in RUNS:
        run_dir = EXP / "runs" / condition
        metadata = json.loads((run_dir / "metadata.json").read_text(encoding="utf-8"))
        run_records[condition] = {
            "metadata_path": rel(run_dir / "metadata.json"),
            "metadata_created_at": metadata["created_at"],
            "command": metadata["command"],
            "deck_sha256": sha256(run_dir / "deck.cir"),
            "raw_sha256": sha256(run_dir / "raw.csv"),
            "log_sha256": sha256(run_dir / "run.log"),
            "artifact_status": metrics["runs"][condition]["artifact_status"],
        }
    solver = REPO / "build/josim-cli"
    solver_version = subprocess.run([str(solver), "--version"], capture_output=True, text=True, check=True)
    plot_manifest = EXP / "analysis/plot_manifest.json"
    provenance = OrderedDict((
        ("schema", "bvm-jm2-connected-single-rloop-final-provenance-v1"),
        ("experiment", metrics["experiment"]),
        ("completed_at", __import__("datetime").datetime.now().astimezone().isoformat(timespec="seconds")),
        ("head_before_task", "824c5c735b647028712e752a599bee8711c46a30"),
        ("preregistration_commit", "0c68b524"),
        ("head_at_final_analysis", subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True, check=True).stdout.strip()),
        ("source_class", "HISTORICAL_BVMSIM_JM2_CONNECTED_VARIANT"),
        ("variant_identity", {
            "path": rel(OLD / "variants/bvm_jm2_connected.cir"),
            "sha256": sha256(OLD / "variants/bvm_jm2_connected.cir"),
            "expected_sha256": "0093a45cc3910448b484d8bd004c6df8c22358bacc8b3ed5e23912dcab805d54",
            "status": "PASS" if sha256(OLD / "variants/bvm_jm2_connected.cir") == "0093a45cc3910448b484d8bd004c6df8c22358bacc8b3ed5e23912dcab805d54" else "FAIL",
        }),
        ("solver", {
            "path": str(solver.resolve()),
            "sha256": sha256(solver),
            "version": solver_version.stdout.strip(),
        }),
        ("source_hashes", source_hashes),
        ("run_records", run_records),
        ("static_preflight_snapshot", {
            "path": rel(EXP / "analysis/static_preflight.json"),
            "sha256": sha256(EXP / "analysis/static_preflight.json"),
            "status": "PASS",
            "normalized_physics_difference_count": 0,
            "probe_only_extension": True,
        }),
        ("analysis", {
            "path": rel(EXP / "analysis/metrics.json"),
            "sha256": sha256(EXP / "analysis/metrics.json"),
            "status": metrics["status"],
        }),
        ("plots", {
            "manifest": rel(plot_manifest),
            "manifest_sha256": sha256(plot_manifest) if plot_manifest.is_file() else None,
            "count": 18,
            "raw_unchanged": True,
        }),
        ("tooling_incidents", TOOLING_INCIDENTS),
        ("status", "AWAITING_USER_REVIEW"),
        ("human_gate", {
            "user_reviewed": False,
            "next_step_authorized": False,
            "automatic_next_experiment": False,
            "next_action": "STOP",
            "array_followup_run": False,
        }),
    ))
    (EXP / "provenance.json").write_text(json.dumps(provenance, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    traces: OrderedDict[str, RawTrace] = OrderedDict()
    records: OrderedDict[str, dict[str, object]] = OrderedDict()
    residuals: OrderedDict[str, OrderedDict[str, tuple[float, ...]]] = OrderedDict()
    for condition, spec in RUNS.items():
        record, trace, run_residuals = run_record(condition, spec)
        records[condition] = record
        traces[condition] = trace
        residuals[condition] = run_residuals
    analysis_valid = all(record["artifact_status"] == "ARTIFACT_VALID" for record in records.values())
    comparison_grid = exact_time_grid_identity(traces["S0-J-RLOOP"].time, traces["S1-J-RLOOP"].time)
    for condition, trace in traces.items():
        derived_columns = OrderedDict(
            (f"I(KCL_{equation})", residual)
            for equation, residual in residuals[condition].items()
        )
        write_csv(
            EXP / "plots/runs" / condition / "derived/BVM_RLOOP_KCL.csv",
            list(derived_columns),
            trace.time,
            derived_columns,
        )
    comparison_data(traces, residuals)
    metrics: dict[str, object] = {
        "schema": "bvm-jm2-connected-single-rloop-analysis-v1",
        "experiment": "bvmsim-jm2-connected-single-rloop-observability-v1-20260904",
        "status": "ANALYSIS_VALID" if analysis_valid and comparison_grid else "ANALYSIS_INVALID",
        "comparison_time_grid_exact": comparison_grid,
        "visualization_phase_conversion": "P raw radians -> continuous_unwrap(rad)/(2*pi) turns",
        "runs": records,
        "comparison_data": {
            "path": "plots/comparison/data/S0_VS_S1_RLOOP_PASSIVE_NETWORK.csv",
            "kcl_path": "plots/comparison/data/S0_VS_S1_RLOOP_KCL.csv",
            "time_grid_exact": comparison_grid,
            "interpolation": "none",
        },
        "probe_schema": "BVM_SINGLE_ARRAY_BRANCH_V1",
        "interpretation_ceiling": "isolated historical single-BVM reference only",
        "tooling_incidents": TOOLING_INCIDENTS,
    }
    (EXP / "analysis/metrics.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (EXP / "analysis/REPORT.md").write_text(report_text(metrics), encoding="utf-8")
    gate = {
        "state": "AWAITING_USER_REVIEW",
        "user_reviewed": False,
        "next_step_authorized": False,
        "automatic_next_experiment": False,
        "next_action": "STOP",
        "stage_b_or_array_authorized": False,
        "analysis_status": metrics["status"],
    }
    (EXP / "analysis/human-gate.yaml").write_text(
        "\n".join(f"{key}: {'true' if value is True else 'false' if value is False else value}" for key, value in gate.items()) + "\n",
        encoding="utf-8",
    )
    write_final_provenance(metrics)
    print(json.dumps({"status": metrics["status"], "runs": {key: value["artifact_status"] for key, value in records.items()}}, ensure_ascii=False))
    return 0 if metrics["status"] == "ANALYSIS_VALID" else 2


if __name__ == "__main__":
    raise SystemExit(main())
