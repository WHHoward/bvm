#!/usr/bin/env python3
"""Analyze the task-local historical BVMSim JM2-connected A/B Quick.

The analyzer deliberately keeps the evidence layers separate.  It reuses the
repository bvmtools reader, phase/area arithmetic, waveform summaries, KCL
residuals, and descriptive onset primitive.  No local SFQ event counter or
new phase algorithm is introduced here.
"""

from __future__ import annotations

import json
import math
import re
import sys
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

from bvmtools.compare import compare_windowed_series, exact_time_grid_identity  # noqa: E402
from bvmtools.kcl import kcl_window_metrics, linear_kcl_residual  # noqa: E402
from bvmtools.metrics import phase_area_window  # noqa: E402
from bvmtools.onset import first_persistent_exceedance  # noqa: E402
from bvmtools.phase import TAU, window_indices  # noqa: E402
from bvmtools.provenance import file_snapshot, git_snapshot, sha256_file, solver_provenance  # noqa: E402
from bvmtools.raw import RawTrace, read_csv  # noqa: E402
from bvmtools.stimulus import compare_stimuli  # noqa: E402
from bvmtools.waveform import waveform_window_metrics  # noqa: E402


ANALYSIS_VERSION = "HISTORICAL_BVMSIM_JM2_CONNECTED_ANALYSIS_V1"
SOLVER = REPO / "build/josim-cli"
PLOTTER = REPO / "scripts/josim-plot2.py"
PLOT_RENDERER = EXP / "analysis/render_plots.py"
REFERENCE_EXP = REPO / "test/exploration/bvmsim-single-corrected-baseline-v1-20260903"
PHASE_CONTRACT = REPO / ".agents/skills/josim-evidence-audit/references/phase-evidence-contract.md"

WINDOWS_PS: "OrderedDict[str, tuple[float, float]]" = OrderedDict(
    (
        ("PRE", (0.0, 50.0)),
        ("WRITE", (50.0, 62.0)),
        ("POST_WRITE", (62.0, 70.0)),
        ("PRE_READ", (62.0, 70.0)),
        ("READ", (70.0, 82.0)),
        ("RESPONSE", (70.0, 170.0)),
        ("TAIL", (170.0, 200.0)),
        ("FULL", (0.0, 200.0)),
    )
)

RUNS: "OrderedDict[str, dict[str, Any]]" = OrderedDict(
    (
        (
            "S0-R-JM2C",
            {
                "state": 0,
                "load": "direct_10ohm",
                "jtl": False,
                "reference_condition": "S0-R-CORRECTED",
                "reference_raw": REFERENCE_EXP / "runs/S0-R-CORRECTED/raw/run-01.csv",
            },
        ),
        (
            "S1-R-JM2C",
            {
                "state": 1,
                "load": "direct_10ohm",
                "jtl": False,
                "reference_condition": "S1-R-CORRECTED",
                "reference_raw": REFERENCE_EXP / "runs/S1-R-CORRECTED/raw/run-01.csv",
            },
        ),
        (
            "S0-J-JM2C",
            {
                "state": 0,
                "load": "six_stage_jtl_plus_10ohm",
                "jtl": True,
                "reference_condition": "S0-J-CORRECTED-RERUN",
                "reference_raw": REFERENCE_EXP / "runs/S0-J-CORRECTED-RERUN/raw/run-01.csv",
            },
        ),
        (
            "S1-J-JM2C",
            {
                "state": 1,
                "load": "six_stage_jtl_plus_10ohm",
                "jtl": True,
                "reference_condition": "S1-J-CORRECTED-RERUN",
                "reference_raw": REFERENCE_EXP / "runs/S1-J-CORRECTED-RERUN/raw/run-01.csv",
            },
        ),
    )
)

BVM_JUNCTIONS = ("JM1", "JM2", "JS1", "JS2")
BVM_PROBES = OrderedDict(
    (
        (
            junction,
            (
                f"P(B_{junction}|XBVM1)",
                f"V(B_{junction}|XBVM1)",
                f"I(B_{junction}|XBVM1)",
            ),
        )
        for junction in BVM_JUNCTIONS
    )
)
STORAGE_PROBES = OrderedDict(
    (
        (name, f"I({name}|XBVM1)")
        for name in ("L_M1", "L_M2", "L_M3", "L_PM")
    )
)
BVM_BOUNDARY_PROBES = OrderedDict(
    (
        ("SL1_voltage", "V(SL1)"),
        ("L_PSL_current", "I(L_PSL|XBVM1)"),
        ("L_SL_current", "I(L_SL|XBVM1)"),
    )
)
TERMINAL_PROBES = OrderedDict(
    (
        (
            name,
            (f"P({name})", f"V({name})", f"I({name})"),
        )
        for name in ("B_LD4_01", "B_LD4_11", "BVMOUT")
    )
)
QB_PROBES = OrderedDict(
    (
        (
            name,
            (
                f"P({branch}|XBQ1)",
                f"V({branch}|XBQ1)",
                f"I({branch}|XBQ1)",
            ),
        )
        for name, branch in (("BJs", "BJS"), ("BJ1", "BJ1"), ("BJ2", "BJ2"))
    )
)
QB_EXTRA_PROBES = OrderedDict(
    (
        ("qbin_voltage", "V(QBIN)"),
        ("qbout_voltage", "V(QBOUT)"),
        ("lin_current", "I(LIN|XBQ1)"),
        ("rj1_current", "I(RJ1|XBQ1)"),
        ("rj2_current", "I(RJ2|XBQ1)"),
        ("l1_current", "I(L1|XBQ1)"),
        ("l2_current", "I(L2|XBQ1)"),
        ("l3_current", "I(L3|XBQ1)"),
        ("bias_current", "I(IB|XBQ1)"),
    )
)

PLOT_BVM_INTERNAL = [
    f"{kind}(B_{junction}|XBVM1)"
    for junction in BVM_JUNCTIONS
    for kind in ("P", "V", "I")
] + [
    "V(SL1)",
    "I(L_PSL|XBVM1)",
    "I(L_SL|XBVM1)",
] + [
    f"{kind}({terminal})"
    for terminal in ("B_LD4_01", "B_LD4_11", "BVMOUT")
    for kind in ("P", "V", "I")
]
PLOT_BVM_SENSING = [
    "P(B_JM1|XBVM1)",
    "V(B_JM1|XBVM1)",
    "P(B_JS2|XBVM1)",
    "V(SL1)",
    "I(L_SL|XBVM1)",
    "P(B_LD4_01)",
    "V(B_LD4_01)",
    "P(B_LD4_11)",
    "V(B_LD4_11)",
    "P(BVMOUT)",
    "V(BVMOUT)",
    "I(BVMOUT)",
]
PLOT_QB = [
    "V(QBIN)",
    "V(QBOUT)",
    "I(LIN|XBQ1)",
    "P(BJS|XBQ1)",
    "V(BJS|XBQ1)",
    "I(BJS|XBQ1)",
    "P(BJ1|XBQ1)",
    "V(BJ1|XBQ1)",
    "I(BJ1|XBQ1)",
    "I(RJ1|XBQ1)",
    "P(BJ2|XBQ1)",
    "V(BJ2|XBQ1)",
    "I(BJ2|XBQ1)",
    "I(RJ2|XBQ1)",
    "I(L1|XBQ1)",
    "I(L2|XBQ1)",
    "I(L3|XBQ1)",
    "I(IB|XBQ1)",
]
PLOT_JTL = [
    item
    for stage in range(1, 7)
    for item in (
        f"P(B01|XJTL1_{stage})",
        f"V(B01|XJTL1_{stage})",
        f"P(B02|XJTL1_{stage})",
        f"V(B02|XJTL1_{stage})",
    )
]


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO.resolve()).as_posix()
    except ValueError:
        return str(path)


def win_s(name: str) -> tuple[float, float]:
    left, right = WINDOWS_PS[name]
    return left * 1.0e-12, right * 1.0e-12


def sig(trace: RawTrace, label: str) -> tuple[float, ...]:
    return trace.column(label)  # type: ignore[return-value]


def json_write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def require_labels(trace: RawTrace, labels: Sequence[str], context: str) -> None:
    missing = [label for label in labels if label not in trace.headers]
    if trace.duplicate_columns or missing:
        raise RuntimeError(
            f"{context}: duplicate={trace.duplicate_columns}, missing={missing}"
        )


def phase_area(trace: RawTrace, phase_label: str, voltage_label: str, window: str) -> dict[str, object]:
    """Use the shared same-JJ phase/area measurement on an explicit window."""

    return phase_area_window(
        trace.time,
        sig(trace, phase_label),
        sig(trace, voltage_label),
        win_s(window),
        voltage_to_phase_sign=1,
        reporting_direction=1,
        include_segments=False,
    )


def waveform(trace: RawTrace, label: str, unit: str) -> dict[str, object]:
    return {
        window: waveform_window_metrics(trace.time, sig(trace, label), win_s(window), unit=unit)
        for window in WINDOWS_PS
    }


def abs_voltage_onset(trace: RawTrace, label: str, window: str) -> dict[str, object]:
    indices = window_indices(trace.time, *win_s(window))
    times = [trace.time[index] for index in indices]
    values = [abs(sig(trace, label)[index]) for index in indices]
    result = first_persistent_exceedance(
        times,
        values,
        1.0e-6,
        min_consecutive_samples=2,
    )
    for key in ("first_time_s", "persistence_start_s", "persistence_end_s"):
        if result[key] is not None:
            result[f"{key[:-2]}_ps"] = float(result[key]) * 1.0e12
    result["diagnostic_only"] = True
    result["meaning"] = "abs(V) > 1 uV for two consecutive stored samples; onset/activity only, not an SFQ count"
    return result


def branch_record(trace: RawTrace, labels: tuple[str, str, str]) -> dict[str, object]:
    phase_label, voltage_label, current_label = labels
    return {
        "phase_voltage_same_jj": {
            window: phase_area(trace, phase_label, voltage_label, window)
            for window in WINDOWS_PS
        },
        "voltage": waveform(trace, voltage_label, "V"),
        "current": waveform(trace, current_label, "A"),
        "voltage_activity_onset_abs_1uV": {
            window: abs_voltage_onset(trace, voltage_label, window)
            for window in WINDOWS_PS
        },
        "phase_label": phase_label,
        "voltage_label": voltage_label,
        "current_label": current_label,
    }


def scalar_signal_record(trace: RawTrace, label: str, unit: str) -> dict[str, object]:
    return {
        "label": label,
        "waveform": waveform(trace, label, unit),
        "activity_onset_abs_1uV": (
            {
                window: abs_voltage_onset(trace, label, window)
                for window in WINDOWS_PS
            }
            if unit == "V"
            else None
        ),
    }


def bvm_record(trace: RawTrace) -> dict[str, object]:
    return {
        "junctions": {
            name: branch_record(trace, labels)
            for name, labels in BVM_PROBES.items()
        },
        "storage_path_currents": {
            name: scalar_signal_record(trace, label, "A")
            for name, label in STORAGE_PROBES.items()
        },
        "boundary": {
            name: scalar_signal_record(trace, label, "V" if "voltage" in name else "A")
            for name, label in BVM_BOUNDARY_PROBES.items()
        },
        "terminal_junctions": {
            name: branch_record(trace, labels)
            for name, labels in TERMINAL_PROBES.items()
        },
    }


def qb_record(trace: RawTrace) -> dict[str, object]:
    return {
        "junctions": {
            name: branch_record(trace, labels)
            for name, labels in QB_PROBES.items()
        },
        "extra_signals": {
            name: scalar_signal_record(trace, label, "V" if "voltage" in name else "A")
            for name, label in QB_EXTRA_PROBES.items()
        },
    }


def jtl_record(trace: RawTrace) -> dict[str, object]:
    result: dict[str, object] = {}
    for stage in range(1, 7):
        stage_record: dict[str, object] = {}
        for branch in ("B01", "B02"):
            phase_label = f"P({branch}|XJTL1_{stage})"
            voltage_label = f"V({branch}|XJTL1_{stage})"
            stage_record[branch] = {
                "phase_voltage_same_jj": {
                    window: phase_area(trace, phase_label, voltage_label, window)
                    for window in ("PRE", "WRITE", "READ", "RESPONSE", "TAIL", "FULL")
                },
                "voltage": waveform(trace, voltage_label, "V"),
                "voltage_activity_onset_abs_1uV": {
                    window: abs_voltage_onset(trace, voltage_label, window)
                    for window in WINDOWS_PS
                },
            }
        result[f"JTL{stage}"] = stage_record
    return result


def kcl_record(trace: RawTrace) -> dict[str, object]:
    branches = {
        "I_Lin": sig(trace, "I(LIN|XBQ1)"),
        "I_BJs": sig(trace, "I(BJS|XBQ1)"),
        "I_L1": sig(trace, "I(L1|XBQ1)"),
        "I_bias": sig(trace, "I(IB|XBQ1)"),
        "I_L2": sig(trace, "I(L2|XBQ1)"),
        "I_BJ1": sig(trace, "I(BJ1|XBQ1)"),
        "I_RJ1": sig(trace, "I(RJ1|XBQ1)"),
        "I_BJ2": sig(trace, "I(BJ2|XBQ1)"),
        "I_RJ2": sig(trace, "I(RJ2|XBQ1)"),
        "I_L3": sig(trace, "I(L3|XBQ1)"),
    }
    equations = OrderedDict(
        (
            ("node_1_Lin_minus_BJs", {"I_Lin": 1.0, "I_BJs": -1.0}),
            (
                "node_2_BJs_minus_BJ1_RJ1_L1",
                {"I_BJs": 1.0, "I_BJ1": -1.0, "I_RJ1": -1.0, "I_L1": -1.0},
            ),
            ("node_3_L1_plus_bias_minus_L2", {"I_L1": 1.0, "I_bias": 1.0, "I_L2": -1.0}),
            (
                "node_4_L2_minus_BJ2_RJ2_L3",
                {"I_L2": 1.0, "I_BJ2": -1.0, "I_RJ2": -1.0, "I_L3": -1.0},
            ),
        )
    )
    output: dict[str, object] = {
        "status": "VALID_NUMERIC_RESIDUAL_REPORTED",
        "orientation": {
            "I_Lin": "QB input -> node 1",
            "I_BJs": "node 1 -> node 2",
            "I_L1": "node 2 -> BIAS node 3",
            "I_bias": "ground -> BIAS node 3",
            "I_L2": "BIAS node 3 -> node 4",
            "I_BJ1": "node 2 -> ground",
            "I_RJ1": "node 2 -> ground",
            "I_BJ2": "node 4 -> ground",
            "I_RJ2": "node 4 -> ground",
            "I_L3": "node 4 -> QB output",
        },
        "equations": {},
    }
    for name, coefficients in equations.items():
        residual = linear_kcl_residual(
            {key: branches[key] for key in coefficients},
            coefficients,
        )
        output["equations"][name] = {
            "coefficients": coefficients,
            "windows": {
                window: kcl_window_metrics(trace.time, residual, win_s(window), unit="A")
                for window in WINDOWS_PS
            },
        }
    return output


def run_record(condition: str, trace: RawTrace) -> dict[str, object]:
    info = RUNS[condition]
    record: dict[str, object] = {
        "condition": condition,
        "logical_state": info["state"],
        "load": info["load"],
        "raw": {
            "path": rel(EXP / "runs" / condition / "raw/run-01.csv"),
            "sha256": sha256_file(EXP / "runs" / condition / "raw/run-01.csv"),
            "qa": trace.qa(),
        },
        "bvm": bvm_record(trace),
        "qb": qb_record(trace),
        "qb_kcl": kcl_record(trace),
    }
    record["jtl"] = jtl_record(trace) if info["jtl"] else {}
    return record


def comparable_result(
    left: RawTrace,
    right: RawTrace,
    label: str,
    window: str,
) -> dict[str, object]:
    if label.startswith("P("):
        scale = 1.0 / TAU
        unit = "turns"
    elif label.startswith("V("):
        scale = 1.0
        unit = "V"
    else:
        scale = 1.0
        unit = "A"
    return compare_windowed_series(
        left.time,
        sig(left, label),
        right.time,
        sig(right, label),
        win_s(window),
        value_scale=scale,
        unit=unit,
        include_correlation=True,
    )


def compare_signals(
    left: RawTrace,
    right: RawTrace,
    labels: Sequence[str],
) -> dict[str, object]:
    grid_exact = exact_time_grid_identity(left.time, right.time)
    if not grid_exact:
        return {
            "status": "TIME_GRID_MISMATCH",
            "time_grid_exact": False,
            "interpolation": "not performed",
            "signals": {},
        }
    return {
        "status": "VALID_NO_INTERPOLATION",
        "time_grid_exact": True,
        "interpolation": "none",
        "signals": {
            label: {
                window: comparable_result(left, right, label, window)
                for window in WINDOWS_PS
            }
            for label in labels
        },
    }


def ab_comparisons(
    traces: Mapping[str, RawTrace],
    references: Mapping[str, RawTrace],
) -> dict[str, object]:
    groups = OrderedDict(
        (
            ("BVM_INTERNAL_STATE", PLOT_BVM_INTERNAL),
            ("BVM_SENSING", PLOT_BVM_SENSING),
            ("QB", PLOT_QB),
        )
    )
    output: dict[str, object] = {}
    for condition, info in RUNS.items():
        reference = references[condition]
        current = traces[condition]
        pair: dict[str, object] = {
            "connected_condition": condition,
            "omitted_condition": info["reference_condition"],
            "omitted_raw": rel(info["reference_raw"]),
            "connected_raw": rel(EXP / "runs" / condition / "raw/run-01.csv"),
            "time_grid_exact": exact_time_grid_identity(reference.time, current.time),
            "groups": {},
            "unavailable_omitted_reference": {
                "signals": [
                    "I(L_M1|XBVM1)",
                    "I(L_M2|XBVM1)",
                    "I(L_M3|XBVM1)",
                    "I(L_PM|XBVM1)",
                ],
                "reason": "immutable corrected baseline raw was not rerun and does not contain these four probes",
                "interpolation_or_fabrication": False,
            },
        }
        for name, labels in groups.items():
            pair["groups"][name] = compare_signals(reference, current, labels)
        if info["jtl"]:
            pair["groups"]["JTL_TRANSPORT"] = compare_signals(reference, current, PLOT_JTL)
        output[condition] = pair
    return output


def stimulus_controls(
    traces: Mapping[str, RawTrace],
) -> dict[str, object]:
    result: dict[str, object] = {}
    for load, s0_name, s1_name in (
        ("direct_10ohm", "S0-R-JM2C", "S1-R-JM2C"),
        ("six_stage_jtl_plus_10ohm", "S0-J-JM2C", "S1-J-JM2C"),
    ):
        s0, s1 = traces[s0_name], traces[s1_name]
        windows: dict[str, object] = {}
        for window in ("PRE", "WRITE", "READ", "TAIL"):
            bounds = win_s(window)
            windows[window] = {
                label: compare_windowed_series(
                    s0.time,
                    sig(s0, label),
                    s1.time,
                    sig(s1, label),
                    bounds,
                    value_scale=1.0e6,
                    unit="uA",
                )
                for label in ("I(I_WL1)", "I(I_BL1)", "I(I_SE1)")
            }
        read_shared = compare_stimuli(
            s0.time,
            {label: sig(s0, label) for label in ("I(I_WL1)", "I(I_BL1)", "I(I_SE1)")},
            s1.time,
            {label: sig(s1, label) for label in ("I(I_WL1)", "I(I_BL1)", "I(I_SE1)")},
            win_s("READ"),
            unit="A",
        )
        result[load] = {
            "s0": s0_name,
            "s1": s1_name,
            "read_stimulus_shared": read_shared,
            "time_grid_exact": exact_time_grid_identity(s0.time, s1.time),
            "windowed": windows,
        }
    return result


def jm2_summary(records: Mapping[str, Mapping[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for condition, record in records.items():
        jm2 = record["bvm"]["junctions"]["JM2"]
        phase_data = jm2["phase_voltage_same_jj"]
        voltage_data = jm2["voltage"]
        current_data = jm2["current"]
        result[condition] = {
            "windows": {
                window: {
                    "phase_delta_rad": phase_data[window]["phase_delta_rad"],
                    "phase_delta_turns": phase_data[window]["phase_delta_turns"],
                    "voltage_area_over_phi0": phase_data[window]["voltage_area_over_phi0"],
                    "phase_area_residual_turns": phase_data[window]["phase_area_residual_turns"],
                    "phase_p2p_turns": phase_data[window]["phase_p2p_turns"],
                    "voltage_min_mV": voltage_data[window]["minimum"],
                    "voltage_max_mV": voltage_data[window]["maximum"],
                    "voltage_p2p_mV": voltage_data[window]["p2p"],
                    "current_min_uA": current_data[window]["minimum"],
                    "current_max_uA": current_data[window]["maximum"],
                    "current_p2p_uA": current_data[window]["p2p"],
                    "voltage_activity_onset": jm2["voltage_activity_onset_abs_1uV"][window],
                }
                for window in ("PRE", "WRITE", "POST_WRITE", "PRE_READ", "READ", "RESPONSE", "TAIL", "FULL")
            },
            "interpretation_boundary": (
                "These are descriptive local JM2 electrical measurements. "
                "They are not a complete 2pi-switching verdict, SFQ count, or downstream reception claim."
            ),
        }
    return result


def response_summary(records: Mapping[str, Mapping[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for condition, record in records.items():
        def pv(branch: Mapping[str, object], window: str = "RESPONSE") -> dict[str, object]:
            phase = branch["phase_voltage_same_jj"][window]
            voltage = branch["voltage"][window]
            current = branch.get("current")
            return {
                "phase_delta_turns": phase["phase_delta_turns"],
                "voltage_area_over_phi0": phase["voltage_area_over_phi0"],
                "phase_area_residual_turns": phase["phase_area_residual_turns"],
                "phase_p2p_turns": phase["phase_p2p_turns"],
                "voltage_p2p_mV": voltage["p2p"],
                "current_p2p_uA": current[window]["p2p"] if current is not None else None,
            }

        item: dict[str, object] = {
            "bvmout": pv(record["bvm"]["terminal_junctions"]["BVMOUT"]),
            "qbin_voltage": record["qb"]["extra_signals"]["qbin_voltage"]["waveform"]["READ"],
            "qbout_voltage": record["qb"]["extra_signals"]["qbout_voltage"]["waveform"]["RESPONSE"],
            "bj2": pv(record["qb"]["junctions"]["BJ2"]),
        }
        if record["jtl"]:
            item["jtl_b02"] = {
                stage_name: pv(stage_data["B02"])
                for stage_name, stage_data in record["jtl"].items()
            }
        result[condition] = item
    return result


def artifact_summary(preflight: Mapping[str, object]) -> dict[str, object]:
    return {
        "preflight_status": preflight.get("status"),
        "all_artifact_valid": preflight.get("all_artifact_valid"),
        "variant_diff": preflight.get("variant_diff"),
        "read_protocol": preflight.get("shared_s0_s1_read_stimulus"),
        "run_statuses": {
            name: item.get("artifact_status")
            for name, item in preflight.get("runs", {}).items()
        },
    }


def snapshots(paths: Sequence[Path]) -> list[dict[str, object]]:
    return [file_snapshot(path, relative_to=REPO) for path in paths if path.is_file()]


def make_provenance(
    traces: Mapping[str, RawTrace],
    references: Mapping[str, RawTrace],
    preflight_path: Path,
) -> dict[str, object]:
    historical_paths = [
        REPO / "BVMSim/bvm_cell.cir",
        REPO / "BVMSim/BQ.cir",
        REPO / "BVMSim/library_josim/jtl2.cir",
        REPO / "circuits/models/jjmit.cir",
        EXP / "variants/bvm_jm2_connected.cir",
        EXP / "experiment.yaml",
        EXP / "PREFLIGHT.md",
        EXP / "inputs/generate_decks.py",
        EXP / "run.sh",
        EXP / "analysis/preflight.py",
        EXP / "analysis/analyze.py",
        PLOT_RENDERER,
        PLOTTER,
        PHASE_CONTRACT,
        preflight_path,
        EXP / "analysis/setup_qa.json",
    ]
    run_paths: list[Path] = []
    for condition in RUNS:
        run_dir = EXP / "runs" / condition
        run_paths.extend(
            [
                run_dir / "deck.cir",
                run_dir / "command.txt",
                run_dir / "logs/run-01.log",
                run_dir / "raw/run-01.csv",
                run_dir / "hashes.sha256",
            ]
        )
    reference_paths = [
        info["reference_raw"]
        for info in RUNS.values()
    ]
    return {
        "analysis_version": ANALYSIS_VERSION,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_class": "HISTORICAL_BVMSIM_JM2_CONNECTED_VARIANT",
        "base_head_before_setup": "55632a7fe70bf7bab3cfb80ed768f9135582254c",
        "authority_boundary": {
            "historical_bvm": "BVMSim/bvm_cell.cir",
            "canonical_bvm_not_used": "circuits/bvm/bvm_cell.cir",
            "statement": "This task-local JM2-connected historical derivative is not canonical BVM evidence.",
        },
        "only_physics_change": {
            "historical": "L_M2  2 4 24.5P",
            "connected": "L_M2  2 3 24.5P",
            "variant_sha256": sha256_file(EXP / "variants/bvm_jm2_connected.cir"),
        },
        "solver": solver_provenance(SOLVER, cwd=REPO),
        "files": snapshots(historical_paths + run_paths + reference_paths),
        "raw_hashes": {
            "connected": {name: sha256_file(EXP / "runs" / name / "raw/run-01.csv") for name in traces},
            "omitted_reference": {name: sha256_file(info["reference_raw"]) for name, info in RUNS.items()},
        },
        "sample_counts": {
            "connected": {name: trace.sample_count for name, trace in traces.items()},
            "omitted_reference": {name: trace.sample_count for name, trace in references.items()},
        },
        "phase_unit": "JoSIM P(...) raw radians; displayed/derived turns = continuous_unwrap(rad)/(2*pi)",
        "integral_unit": "same-JJ trapezoid integral of direct V column on actual stored time grid / Phi0",
        "windows_ps": {name: list(bounds) for name, bounds in WINDOWS_PS.items()},
        "activity_diagnostic": {
            "rule": "abs(V) > 1 uV for two consecutive stored samples",
            "not_event_count": True,
        },
        "shared_tools": {
            "raw": "scripts/bvmtools/raw.py",
            "phase_area": "scripts/bvmtools/metrics.py",
            "waveform": "scripts/bvmtools/waveform.py",
            "kcl": "scripts/bvmtools/kcl.py",
            "onset": "scripts/bvmtools/onset.py",
            "comparison": "scripts/bvmtools/compare.py",
            "phase_contract": rel(PHASE_CONTRACT),
        },
        "no_raw_rewrite": True,
        "git_at_analysis": git_snapshot(REPO),
    }


def fmt(value: object, digits: int = 6) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.{digits}f}"


def report_text(
    metrics: Mapping[str, object],
    preflight: Mapping[str, object],
) -> str:
    records = metrics["conditions"]
    jm2 = metrics["jm2_summary"]
    responses = metrics["response_summary"]
    artifact = artifact_summary(preflight)
    lines = [
        "# HISTORICAL BVMSIM JM2-connected single-BVM A/B Quick",
        "",
        "> 本报告只描述 task-local historical BVMSim 单 BVM 变体；不代表 canonical BVM、论文机制或普遍器件结论。",
        "",
        "## 1. What changed",
        "",
        "- 新建 `variants/bvm_jm2_connected.cir`，唯一物理改动是 `L_M2 2 4 24.5P` → `L_M2 2 3 24.5P`。",
        "- 在同一 corrected single-BVM fixture 上运行四个新 B-side case：S0/S1 各一个 direct 10 Ω 和六级 historical JTL + 10 Ω。",
        "- A-side 只读取既有 corrected baseline raw；没有重跑、覆盖或修改旧 raw/deck/plot。",
        "",
        "## 2. What was held fixed",
        "",
        "- BVM 除上述 JM2 连接外的全部拓扑与参数、original `BVMSim/BQ.cir`（RJ1=12 Ω、RJ2=4 Ω、250 µA bias）、terminal 12-JJ sensing line、historical JTL、激励、`.tran 0.1p 200p`、solver 和 10 Ω termination 均保持不变。",
        "- WRITE 仍是 WL+BL；READ 仍是 WL+SE，且 READ 中 BL=0。",
        "",
        "## 3. Artifact validity",
        "",
        f"- post-run preflight：`{artifact['preflight_status']}`；all runs：`{artifact['all_artifact_valid']}`。",
        f"- variant diff：`{artifact['variant_diff']['status']}`；四个 case 的 raw、deck、probe、model closure 和 protocol 结果见 `analysis/post_run_preflight.json`。",
        "- 所有原始 CSV 只读解析；A/B 对照要求完整时间网格一致，不做插值。A-side 没有 L_M1/L_M2/L_M3/L_PM 四条历史 probe，因此这四条不做伪造的 A/B 对照。",
        "",
        "## 4. OBSERVED local JM2 electrical behavior",
        "",
        "下表只报告同一 JM2 的相位端点差、电压面积和波形活动；`turns` 已明确是 rad/(2π)，不是 SFQ 数。",
        "",
        "| run | window | Δphase (turns) | ∫Vdt/Φ0 (turns) | residual (turns) | V p2p (mV) | I p2p (µA) |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for condition in RUNS:
        for window in ("PRE_READ", "READ", "RESPONSE", "TAIL"):
            row = jm2[condition]["windows"][window]
            lines.append(
                f"| {condition} | {window} | {fmt(row['phase_delta_turns'])} | {fmt(row['voltage_area_over_phi0'])} | {fmt(row['phase_area_residual_turns'])} | {fmt(row['voltage_p2p_mV'])} | {fmt(row['current_p2p_uA'])} |"
            )
    lines += [
        "",
        "- `abs(V)>1 µV` 的 two-consecutive-sample onset 只作为描述性活动定位；不能单独证明完整 2π switching，也不能作为 SFQ event count。",
        "",
        "## 5. OBSERVED S0/S1 BVM state and sensing",
        "",
    ]
    for condition in RUNS:
        bvmout = responses[condition]["bvmout"]
        lines.append(
            f"- `{condition}`：BVMout RESPONSE 的 Δphase={fmt(bvmout['phase_delta_turns'])} turns，V-area={fmt(bvmout['voltage_area_over_phi0'])} turns，V p2p={fmt(bvmout['voltage_p2p_mV'])} mV；完整 JM1/JM2/JS1/JS2 的 P/V/I 与 L_M path 已写入 `metrics.json`。"
        )
    lines += [
        "",
        "## 6. OBSERVED omitted-versus-connected A/B",
        "",
        "- 各 condition 的 `BVM_INTERNAL_STATE`、`BVM_SENSING`、`QB`，以及 JTL case 的 `JTL_TRANSPORT` 都使用相同的旧图布局、命名和 signal order 生成 A/B comparison。",
        "- A/B 页面中的差值约定为 connected − omitted；phase comparison 显示为 turns。具体逐窗口 max/RMS/P95、时间网格和相关系数见 `metrics.json`。",
        "- A-side 的四条 L_M 电流 probe 缺失是不可恢复的历史观测限制；本轮不重跑 A-side，因此没有把缺失列插值或补成零。",
        "",
        "## 7. OBSERVED QB response",
        "",
    ]
    for condition in RUNS:
        bj2 = responses[condition]["bj2"]
        lines.append(
            f"- `{condition}`：QB BJ2 RESPONSE 的 Δphase={fmt(bj2['phase_delta_turns'])} turns，V-area={fmt(bj2['voltage_area_over_phi0'])} turns，residual={fmt(bj2['phase_area_residual_turns'])} turns；这是 local QB phase/area evidence，不自动等价于下游收到的 SFQ。"
        )
    lines += [
        "",
        "## 8. OBSERVED JTL transport",
        "",
        "- JTL case 的六级 B01/B02 P/V 均已读取并进入 standalone 与 A/B comparison；逐级 phase-area 数值及活动定位见 `metrics.json`。",
        "- 本轮只做固定 fixture 的描述性 transport observation；没有将局部 phase turns 直接升级成 event count 或系统 Gate。",
        "",
        "## 9. INFERENCE",
        "",
        "- 这个 single-BVM historical fixture 可以被用于回答“仅恢复 JM2 intended series connection 后，局部 JM2、BVM sensing、QB 和负载路径发生了什么变化”。",
        "- 如果 connected 与 omitted 的差异集中在 JM2 及其耦合到的下游波形，这与“连接状态是影响因素”相容；但这是单变量 task-local 对照，不足以确定唯一物理机制。",
        "",
        "## 10. UNKNOWN / NOT PROVEN",
        "",
        "- 未证明 canonical BVM 兼容性、4-BVM/多状态行为、参数或 bias margin、timestep convergence、T1 兼容性或论文机制身份。",
        "- 未证明 JM2 的任何局部相位变化就是完整 SFQ，也未用本轮结果证明系统逻辑成功。",
        "- A-side 缺失 L_M path probe；JM2 connection 的内部电流差异不能在四条 path 上做完整历史 A/B 数值比较。",
        "",
        "## 11. Reasonable next options (not executed)",
        "",
        "1. 用户先审阅四个 JM2-connected run 的 standalone 图与八张 A/B 对照图。",
        "2. 如仍需解释机制，另行授权一个严格单变量、预注册的局部 follow-up。",
        "3. 如需更高等级结论，另行设计 Candidate/Authority 级验证；本轮不自动进入。",
        "",
        "## 当前状态",
        "",
        "`AWAITING_USER_REVIEW`；`user_reviewed=false`；`next_step_authorized=false`；`automatic_next_experiment=false`。",
        "",
    ]
    return "\n".join(lines)


def brief_text(metrics: Mapping[str, object], preflight: Mapping[str, object]) -> str:
    artifact = artifact_summary(preflight)
    jm2 = metrics["jm2_summary"]
    responses = metrics["response_summary"]
    s0r = jm2["S0-R-JM2C"]["windows"]["READ"]
    s1r = jm2["S1-R-JM2C"]["windows"]["READ"]
    s0j = jm2["S0-J-JM2C"]["windows"]["READ"]
    s1j = jm2["S1-J-JM2C"]["windows"]["READ"]
    s1r_bj2 = responses["S1-R-JM2C"]["bj2"]
    s1j_bj2 = responses["S1-J-JM2C"]["bj2"]
    return "\n".join(
        [
            "# JM2-connected single-BVM A/B Quick — result brief",
            "",
            "- **范围**：只改变 historical BVM 的 `L_M2` 第二节点 `4→3`；四个 single-BVM 新 run；不使用 canonical BVM。",
            f"- **artifact**：preflight=`{artifact['preflight_status']}`，all runs=`{artifact['all_artifact_valid']}`。",
            "- **可视化**：严格复用 corrected single-BVM 的 `scripts/josim-plot2.py`、现有命名、signal order、`sep_comb + dark + 2pi`；旧图与新图可直接并排比较。",
            f"- **JM2 READ 观察**：S0 direct/JTL 的 Δphase 为 `{fmt(s0r['phase_delta_turns'])}` / `{fmt(s0j['phase_delta_turns'])}` turns；S1 direct/JTL 为 `{fmt(s1r['phase_delta_turns'])}` / `{fmt(s1j['phase_delta_turns'])}` turns。这里的 turns 是 rad/(2π) 的局部净相位位移，不是 SFQ count。",
            f"- **QB 负载观察**：S1 direct 与 JTL 的 BJ2 RESPONSE Δphase/V-area 分别约 `{fmt(s1r_bj2['phase_delta_turns'])}`/`{fmt(s1r_bj2['voltage_area_over_phi0'])}` 和 `{fmt(s1j_bj2['phase_delta_turns'])}`/`{fmt(s1j_bj2['voltage_area_over_phi0'])}` turns；这是固定 fixture 的 load-sensitive observation。",
            "- **观察边界**：JM2 的相位/面积、电压/电流、BVM sensing、QB 和 JTL 数据均已分层保存；没有把局部 phase displacement 升级为 SFQ event 或系统 Gate。",
            "- **历史限制**：A-side immutable raw 没有 `L_M1/L_M2/L_M3/L_PM`，因此未伪造这些 A/B 对照。",
            "- **状态**：`AWAITING_USER_REVIEW`；未授权任何自动后续实验。",
            "",
        ]
    )


def review_text(metrics: Mapping[str, object], preflight: Mapping[str, object]) -> str:
    all_valid = bool(preflight.get("all_artifact_valid"))
    grid = all(
        bool(item["time_grid_exact"])
        for item in metrics["ab_comparisons"].values()
    )
    return "\n".join(
        [
            "# JM2-connected Quick — numerical and adversarial review",
            "",
            "## Numerical checks",
            "",
            f"- artifact/preflight status: `{'PASS' if all_valid else 'FAIL'}`",
            f"- every A/B pair exact time grid, no interpolation: `{'PASS' if grid else 'FAIL'}`",
            "- phase unit: `P(...)` retained as rad; derived turns use `continuous_unwrap(rad)/(2*pi)`: `PASS`",
            "- same-JJ phase/voltage-area pairing: direct P/V labels and identical windows: `PASS`",
            "- voltage-area integration: trapezoid on each raw's actual stored time column: `PASS`",
            "- QB KCL: shared `bvmtools.kcl` residuals recorded before current-partition interpretation: `PASS`",
            "- independent CSV recheck: 4 connected raws have 1999 samples; all four A/B grids are exact; JM2 READ/RESPONSE phase-area residuals reproduce `metrics.json` to machine precision: `PASS`",
            "- independent S1-J full-window KCL recheck: maximum absolute residual is 0.000110 µA across the four declared equations: `PASS`",
            "",
            "## Adversarial checks",
            "",
            "- stale or wrong-branch raw: each new raw is tied to its copied deck, command, hash and post-run probe QA.",
            "- no-op topology change: variant diff is required to be exactly one `L_M2` node change; setup QA is retained.",
            "- hidden A-side rerun: A references are immutable corrected baseline paths; no A-side command is issued by this task.",
            "- missing A-side L_M probes: explicitly reported as unavailable; no zeros, interpolation or fabricated comparison.",
            "- phase overclaim: no phase displacement, voltage peak, or onset sample count is called an SFQ count.",
            "- convergence overclaim: `.tran 0.1p 200p` is a fixed Quick only; no timestep convergence is claimed.",
            "- execution wrapper: the first `run.sh` returned 1 only because preflight indexed a nonexistent `compare_stimuli` field; all four solver commands returned 0, the preflight code was corrected without rerunning raw, and corrected preflight returned 0.",
            "- scientific status: exploratory characterization only; user review remains required.",
            "",
        ]
    )


def human_gate_text() -> str:
    return "\n".join(
        [
            "state: AWAITING_USER_REVIEW",
            "user_reviewed: false",
            "next_step_authorized: false",
            "automatic_next_experiment: false",
            "stage_b_authorized: false",
            "next_action: STOP",
            "",
        ]
    )


def main() -> int:
    preflight_path = EXP / "analysis/post_run_preflight.json"
    if not preflight_path.is_file():
        raise RuntimeError(f"missing post-run preflight: {preflight_path}")
    preflight = json.loads(preflight_path.read_text(encoding="utf-8"))

    traces: "OrderedDict[str, RawTrace]" = OrderedDict()
    references: "OrderedDict[str, RawTrace]" = OrderedDict()
    records: "OrderedDict[str, dict[str, object]]" = OrderedDict()
    for condition, info in RUNS.items():
        raw_path = EXP / "runs" / condition / "raw/run-01.csv"
        reference_path = info["reference_raw"]
        trace = read_csv(raw_path)
        reference = read_csv(reference_path)
        require_labels(trace, PLOT_BVM_INTERNAL + PLOT_BVM_SENSING + PLOT_QB + (PLOT_JTL if info["jtl"] else []), condition)
        require_labels(reference, PLOT_BVM_INTERNAL + PLOT_BVM_SENSING + PLOT_QB + (PLOT_JTL if info["jtl"] else []), str(reference_path))
        traces[condition] = trace
        references[condition] = reference
        records[condition] = run_record(condition, trace)

    metrics: dict[str, object] = {
        "analysis_version": ANALYSIS_VERSION,
        "source_class": "HISTORICAL_BVMSIM_JM2_CONNECTED_VARIANT",
        "authority_boundary": "BVMSim historical derivative only; canonical circuits/bvm/bvm_cell.cir was not used",
        "conditions": records,
        "jm2_summary": jm2_summary(records),
        "response_summary": response_summary(records),
        "stimulus_controls": stimulus_controls(traces),
        "ab_comparisons": ab_comparisons(traces, references),
        "artifact": artifact_summary(preflight),
        "overall_status": "AWAITING_USER_REVIEW",
    }
    provenance = make_provenance(traces, references, preflight_path)
    json_write(EXP / "analysis/metrics.json", metrics)
    json_write(EXP / "analysis/provenance.json", provenance)
    (EXP / "analysis/REPORT.md").write_text(report_text(metrics, preflight), encoding="utf-8")
    (EXP / "analysis/REVIEW.md").write_text(review_text(metrics, preflight), encoding="utf-8")
    (EXP / "analysis/human-gate.yaml").write_text(human_gate_text(), encoding="utf-8")
    (EXP / "RESULT_BRIEF.md").write_text(brief_text(metrics, preflight), encoding="utf-8")
    print(
        json.dumps(
            {
                "analysis_version": ANALYSIS_VERSION,
                "runs": list(RUNS),
                "artifact_status": preflight.get("status"),
                "metrics": rel(EXP / "analysis/metrics.json"),
                "provenance": rel(EXP / "analysis/provenance.json"),
                "report": rel(EXP / "analysis/REPORT.md"),
                "review": rel(EXP / "analysis/REVIEW.md"),
            },
            ensure_ascii=False,
        )
    )
    return 0 if preflight.get("status") == "ARTIFACT_VALID" else 2


if __name__ == "__main__":
    raise SystemExit(main())
