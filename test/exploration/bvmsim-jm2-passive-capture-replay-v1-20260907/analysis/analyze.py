#!/usr/bin/env python3
"""Analyze the four immutable runs and create focused plot inputs.

This file reports waveform facts and bounded counterfactual comparisons.  It
does not classify SFQ events or make a physical mechanism claim.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import subprocess
import sys
from collections import OrderedDict
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from typing import Iterable


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
DIRECT_EXP = REPO / "test/exploration/bvmsim-jm2-single-vs-4bvm-shared-sl-v1-20260907"
RAW_CASES = OrderedDict(
    (
        ("SINGLE_PASSIVE", EXP / "runs/single_passive/raw.csv"),
        ("ARRAY_PASSIVE", EXP / "runs/array_passive/raw.csv"),
        ("REPLAY_SINGLE", EXP / "runs/replay_single/raw.csv"),
        ("REPLAY_ARRAY", EXP / "runs/replay_array/raw.csv"),
    )
)
SOURCE_SIGNAL = "I(B_JSL8)"
TAU = 2.0 * math.pi
PHI0 = 2.067833848e-15

sys.path.insert(0, str(REPO / "scripts"))
from bvmtools.kcl import kcl_window_metrics, linear_kcl_residual  # noqa: E402
from bvmtools.metrics import phase_area_window  # noqa: E402
from bvmtools.phase import continuous_unwrap, window_indices  # noqa: E402
from bvmtools.raw import RawTrace, read_csv  # noqa: E402
from bvmtools.waveform import trapezoid_integral, waveform_metrics, waveform_window_metrics  # noqa: E402


WINDOWS_PS = OrderedDict(
    (
        ("INITIAL_PRE_WRITE0", (0.0, 50.0)),
        ("WRITE0", (50.0, 61.0)),
        ("PRE_ZERO_READ", (61.0, 70.0)),
        ("ZERO_STATE_READ_CONTROL", (70.0, 81.0)),
        ("POST_ZERO_READ", (81.0, 90.0)),
        ("WRITE1", (90.0, 101.0)),
        ("PRE_FINAL_READ", (101.0, 110.0)),
        ("FINAL_READ", (110.0, 121.0)),
        ("TAIL", (121.0, 200.0)),
    )
)
WINDOWS_S = OrderedDict((name, (start * 1e-12, end * 1e-12)) for name, (start, end) in WINDOWS_PS.items())


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def now_local() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def write_once(path: Path, content: str) -> None:
    if path.exists():
        if path.read_text(encoding="utf-8") == content:
            return
        raise RuntimeError(f"refusing to overwrite existing artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def load_traces() -> dict[str, RawTrace]:
    return {name: read_csv(path) for name, path in RAW_CASES.items()}


def series(trace: RawTrace, label: str, kind: str) -> tuple[float, ...]:
    values = trace.column(label)
    if kind == "P":
        return continuous_unwrap(values)  # type: ignore[arg-type]
    return values  # type: ignore[return-value]


def exact_grid(left: RawTrace, right: RawTrace) -> bool:
    return len(left.time) == len(right.time) and all(a == b for a, b in zip(left.time, right.time))


def scale_for(kind: str) -> tuple[float, float, str, str]:
    if kind == "I":
        return 1e6, 1e18, "uA", "uA*ps"
    if kind == "V":
        return 1e3, 1e15, "mV", "mV*ps"
    if kind == "P":
        return 1.0, 1.0, "rad", "rad*s"
    raise ValueError(kind)


def select_window(times: tuple[float, ...], values: tuple[float, ...], window: tuple[float, float]) -> tuple[list[float], list[float]]:
    indices = window_indices(times, *window)
    if len(indices) < 2:
        raise RuntimeError(f"window has fewer than two samples: {window}")
    return [times[index] for index in indices], [values[index] for index in indices]


def summary(values: tuple[float, ...], times: tuple[float, ...], kind: str, window: tuple[float, float]) -> dict[str, object]:
    selected_t, selected_v = select_window(times, values, window)
    factor, area_factor, unit, area_unit = scale_for(kind)
    base = waveform_metrics(selected_t, selected_v)
    return {
        "raw_unit": {"I": "A", "V": "V", "P": "rad"}[kind],
        "display_unit": unit,
        "area_unit": area_unit,
        "window_ps": [window[0] * 1e12, window[1] * 1e12],
        "sample_count": int(base["sample_count"]),
        "minimum": float(base["minimum"]) * factor,
        "maximum": float(base["maximum"]) * factor,
        "mean": float(base["mean"]) * factor,
        "p2p": float(base["p2p"]) * factor,
        "rms": float(base["rms"]) * factor,
        "max_abs": float(base["max_abs"]) * factor,
        "p95_abs": float(sorted(abs(value) for value in selected_v)[int(math.ceil(0.95 * len(selected_v))) - 1]) * factor,
        "endpoint": float(selected_v[-1]) * factor,
        "endpoint_change": float(selected_v[-1] - selected_v[0]) * factor,
        "signed_integral": float(base["signed_time_integral"]) * area_factor,
        "positive_area": float(base["positive_area"]) * area_factor,
        "negative_area": float(base["negative_area"]) * area_factor,
        "zero_crossing_count_activity_only": int(base["zero_crossing_count"]),
        "window_first_sample_ps": selected_t[0] * 1e12,
        "window_last_sample_ps": selected_t[-1] * 1e12,
    }


def delta_summary(
    left_trace: RawTrace,
    right_trace: RawTrace,
    left_label: str,
    right_label: str,
    kind: str,
    window: tuple[float, float],
    convention: str,
) -> dict[str, object]:
    if not exact_grid(left_trace, right_trace):
        raise RuntimeError(f"exact grid mismatch for {left_label} vs {right_label}")
    left = series(left_trace, left_label, kind)
    right = series(right_trace, right_label, kind)
    delta = tuple(r - l for l, r in zip(left, right))
    selected_t, selected_d = select_window(left_trace.time, delta, window)
    factor, area_factor, unit, area_unit = scale_for(kind)
    base = waveform_metrics(selected_t, selected_d)
    sorted_abs = sorted(abs(value) for value in selected_d)
    result: dict[str, object] = {
        "left_label": left_label,
        "right_label": right_label,
        "difference_convention": convention,
        "raw_unit": {"I": "A", "V": "V", "P": "rad"}[kind],
        "display_unit": unit,
        "area_unit": area_unit,
        "window_ps": [window[0] * 1e12, window[1] * 1e12],
        "sample_count": len(selected_d),
        "max_abs_delta": max(abs(value) for value in selected_d) * factor,
        "RMS_delta": math.sqrt(sum(value * value for value in selected_d) / len(selected_d)) * factor,
        "p95_abs_delta": sorted_abs[int(math.ceil(0.95 * len(sorted_abs))) - 1] * factor,
        "mean_delta": float(base["mean"]) * factor,
        "p2p_delta": float(base["p2p"]) * factor,
        "signed_integral_delta": float(base["signed_time_integral"]) * area_factor,
        "endpoint_delta": selected_d[-1] * factor,
        "window_first_sample_ps": selected_t[0] * 1e12,
        "window_last_sample_ps": selected_t[-1] * 1e12,
    }
    if kind == "P":
        result.update(
            {
                "phase_delta_rad_endpoint": selected_d[-1],
                "phase_delta_turns_endpoint": selected_d[-1] / TAU,
                "phase_p2p_turns": (max(selected_d) - min(selected_d)) / TAU,
                "phase_rule": "continuous_unwrap(raw radians) before subtraction; turns are rad/(2*pi)",
            }
        )
    return result


def signal_spec(identifier: str, left: str, right: str, kind: str, caption: str) -> dict[str, str]:
    return {"id": identifier, "left": left, "right": right, "kind": kind, "caption": caption}


PASSIVE_COMPARE = [
    signal_spec("JSL1_I", "I(B_JSL1)", "I(B_JSL1)", "I", "JSL1 current"),
    signal_spec("JSL8_I", "I(B_JSL8)", "I(B_JSL8)", "I", "JSL8 current"),
    signal_spec("BOUNDARY_V", "V(SL1)", "V(COMMON_SL)", "V", "SL / COMMON_SL boundary voltage"),
]
REPLAY_COMPARE = [
    signal_spec("QBIN_V", "V(QBIN)", "V(QBIN)", "V", "QBIN voltage"),
    signal_spec("QBOUT_V", "V(QBOUT)", "V(QBOUT)", "V", "QBOUT voltage"),
    signal_spec("REPLAY_I", "I(I_REPLAY)", "I(I_REPLAY)", "I", "replay source current"),
    signal_spec("LIN_I", "I(LIN|XBQ1)", "I(LIN|XBQ1)", "I", "QB LIN current"),
    signal_spec("BJ1_P", "P(BJ1|XBQ1)", "P(BJ1|XBQ1)", "P", "BJ1 phase"),
    signal_spec("BJ1_V", "V(BJ1|XBQ1)", "V(BJ1|XBQ1)", "V", "BJ1 voltage"),
    signal_spec("BJ2_P", "P(BJ2|XBQ1)", "P(BJ2|XBQ1)", "P", "BJ2 phase"),
    signal_spec("BJ2_V", "V(BJ2|XBQ1)", "V(BJ2|XBQ1)", "V", "BJ2 voltage"),
]
JTL_COMPARE = [
    signal_spec("JTL1_B01_P", "P(B01|XJTL1_1)", "P(B01|XJTL1_1)", "P", "JTL1 B01 phase"),
    signal_spec("JTL1_B01_V", "V(B01|XJTL1_1)", "V(B01|XJTL1_1)", "V", "JTL1 B01 voltage"),
    signal_spec("JTL1_B02_P", "P(B02|XJTL1_1)", "P(B02|XJTL1_1)", "P", "JTL1 B02 phase"),
    signal_spec("JTL1_B02_V", "V(B02|XJTL1_1)", "V(B02|XJTL1_1)", "V", "JTL1 B02 voltage"),
    signal_spec("JTL6_B01_P", "P(B01|XJTL1_6)", "P(B01|XJTL1_6)", "P", "JTL6 B01 phase"),
    signal_spec("JTL6_B01_V", "V(B01|XJTL1_6)", "V(B01|XJTL1_6)", "V", "JTL6 B01 voltage"),
    signal_spec("JTL6_B02_P", "P(B02|XJTL1_6)", "P(B02|XJTL1_6)", "P", "JTL6 B02 phase"),
    signal_spec("JTL6_B02_V", "V(B02|XJTL1_6)", "V(B02|XJTL1_6)", "V", "JTL6 B02 voltage"),
    signal_spec("JTL1_OUT_V", "V(JTL1_OUT)", "V(JTL1_OUT)", "V", "JTL1 output voltage"),
    signal_spec("JTL6_OUT_V", "V(JTL6_OUT)", "V(JTL6_OUT)", "V", "JTL6 output voltage"),
    signal_spec("R_TERM_I", "I(R_TERM)", "I(R_TERM)", "I", "10 ohm termination current"),
]


def required_passive_headers(instances: Iterable[int], boundary: str) -> list[str]:
    expected: list[str] = []
    for instance in instances:
        handle = f"XBVM{instance}"
        for jj in ("B_JM1", "B_JM2", "B_JS1", "B_JS2"):
            expected += [f"P({jj}|{handle})", f"V({jj}|{handle})", f"I({jj}|{handle})"]
        for branch in ("L_M1", "L_M2", "L_M3", "L_PM", "R_JM1", "L_S1", "L_S2", "R_S", "L_S3", "R_SE", "L_PSE", "L_PSL", "R_SL", "L_SL"):
            expected += [f"I({branch}|{handle})", f"V({branch}|{handle})"]
        expected += [f"I(I_WL{instance})", f"I(I_BL{instance})", f"I(I_SE{instance})"]
    expected.append(f"V({boundary})")
    for index in range(1, 9):
        expected += [f"P(B_JSL{index})", f"V(B_JSL{index})", f"I(B_JSL{index})"]
    return expected


def required_replay_headers() -> list[str]:
    expected = ["V(QBIN)", "V(QBOUT)", "I(I_REPLAY)"]
    for branch in ("LIN", "L1", "L2", "L3", "RJ1", "RJ2"):
        expected += [f"I({branch}|XBQ1)", f"V({branch}|XBQ1)"]
    # JoSIM emits the IB branch current for this model, but not always its
    # branch voltage.  Keep the requested probe as an explicit optional QA
    # item rather than invalidating an otherwise complete replay schema.
    expected.append("I(IB|XBQ1)")
    for jj in ("BJS", "BJ1", "BJ2"):
        expected += [f"P({jj}|XBQ1)", f"V({jj}|XBQ1)", f"I({jj}|XBQ1)"]
    for stage in range(1, 7):
        handle = f"XJTL1_{stage}"
        expected += [f"P(B01|{handle})", f"V(B01|{handle})", f"I(B01|{handle})", f"P(B02|{handle})", f"V(B02|{handle})", f"I(B02|{handle})", f"V(JTL{stage}_OUT)"]
    expected.append("I(R_TERM)")
    return expected


def artifact_qa(traces: dict[str, RawTrace]) -> dict[str, object]:
    required = {
        "SINGLE_PASSIVE": required_passive_headers((1,), "SL1"),
        "ARRAY_PASSIVE": required_passive_headers((1, 2, 3, 4), "COMMON_SL"),
        "REPLAY_SINGLE": required_replay_headers(),
        "REPLAY_ARRAY": required_replay_headers(),
    }
    optional = {name: ["V(IB|XBQ1)"] for name in ("REPLAY_SINGLE", "REPLAY_ARRAY")}
    cases: dict[str, object] = {}
    failures: list[str] = []
    for name, trace in traces.items():
        qa = trace.qa()
        missing = [label for label in required[name] if label not in trace.headers]
        missing_optional = [label for label in optional.get(name, []) if label not in trace.headers]
        if missing:
            failures.append(f"{name}: missing required {missing}")
        if qa["duplicate_columns"]:
            failures.append(f"{name}: duplicate columns {qa['duplicate_columns']}")
        cases[name] = {
            **qa,
            "path": str(RAW_CASES[name].resolve()),
            "raw_sha256": sha256(RAW_CASES[name]),
            "required_header_count": len(required[name]),
            "missing_required_headers": missing,
            "optional_missing_headers": missing_optional,
            "optional_probe_note": "V(IB|XBQ1) was requested but is not emitted by this JoSIM raw schema" if missing_optional else None,
            "metadata_path": str((EXP / "runs" / name.lower() / "metadata.json").resolve()),
        }
    return {
        "schema": "jm2-passive-capture-replay-artifact-qa-v1",
        "experiment_id": EXP.name,
        "created_at_local": now_local(),
        "status": "PASS" if not failures else "INVALID",
        "raw_immutable": True,
        "cases": cases,
        "failures": failures,
    }


def source_snapshot_fidelity(traces: dict[str, RawTrace]) -> dict[str, object]:
    records: dict[str, object] = {}
    failures: list[str] = []
    for passive, replay in (("SINGLE_PASSIVE", "REPLAY_SINGLE"), ("ARRAY_PASSIVE", "REPLAY_ARRAY")):
        raw_path = RAW_CASES[passive]
        snapshot_path = EXP / "data" / f"{passive.lower()}_JSL8_source.csv"
        with raw_path.open(newline="", encoding="utf-8") as handle:
            raw_rows = list(csv.DictReader(handle))
        with snapshot_path.open(newline="", encoding="utf-8") as handle:
            snapshot_rows = list(csv.DictReader(handle))
        raw_pairs = [(row["time"], row[SOURCE_SIGNAL]) for row in raw_rows]
        snap_pairs = [(row["time_s"], row["current_A"]) for row in snapshot_rows]
        exact_snapshot = raw_pairs == snap_pairs
        if not exact_snapshot:
            failures.append(f"{passive}: snapshot token pairs differ from raw")
        p_trace = traces[passive]
        r_trace = traces[replay]
        source = p_trace.column(SOURCE_SIGNAL)
        replay_source = r_trace.column("I(I_REPLAY)")
        replay_lin = r_trace.column("I(LIN|XBQ1)")
        grid = exact_grid(p_trace, r_trace)
        source_replay = tuple(replay_source[index] - source[index] for index in range(len(source))) if grid else ()
        source_lin = tuple(replay_lin[index] - source[index] for index in range(len(source))) if grid else ()
        orientation = tuple(replay_source[index] - replay_lin[index] for index in range(len(replay_source)))
        max_source_replay = max((abs(value) for value in source_replay), default=math.inf)
        max_source_lin = max((abs(value) for value in source_lin), default=math.inf)
        max_orientation = max((abs(value) for value in orientation), default=math.inf)
        if not (exact_snapshot and grid and max_source_replay == 0.0 and max_source_lin == 0.0 and max_orientation == 0.0):
            failures.append(f"{passive}: replay source/orientation fidelity failed")
        records[passive] = {
            "raw_path": raw_path.relative_to(REPO).as_posix(),
            "raw_sha256": sha256(raw_path),
            "snapshot_path": snapshot_path.relative_to(REPO).as_posix(),
            "snapshot_sha256": sha256(snapshot_path),
            "sample_count": len(raw_pairs),
            "exact_snapshot_token_pairs": exact_snapshot,
            "passive_replay_grid_exact": grid,
            "max_abs_source_minus_I_REPLAY_A": max_source_replay,
            "max_abs_source_minus_LIN_A": max_source_lin,
            "max_abs_I_REPLAY_minus_LIN_A": max_orientation,
            "orientation": "I_REPLAY 0 QBIN; positive injection matches JSL8 -> QBIN branch sense",
            "sign_change": False,
            "transformations": [],
            "replay_case": replay,
        }
    return {
        "schema": "jm2-passive-capture-replay-source-fidelity-v1",
        "status": "PASS" if not failures else "FAIL",
        "source_signal": SOURCE_SIGNAL,
        "records": records,
        "failures": failures,
    }


def build_comparison_metrics(traces: dict[str, RawTrace]) -> dict[str, object]:
    passive: dict[str, object] = {}
    for spec in PASSIVE_COMPARE:
        per_window: dict[str, object] = {}
        for name, window in WINDOWS_S.items():
            per_window[name] = delta_summary(
                traces["SINGLE_PASSIVE"], traces["ARRAY_PASSIVE"], spec["left"], spec["right"], spec["kind"], window,
                "ARRAY_PASSIVE - SINGLE_PASSIVE",
            )
        passive[spec["id"]] = {"caption": spec["caption"], "kind": spec["kind"], "windows": per_window}

    replay: dict[str, object] = {}
    for spec in REPLAY_COMPARE + JTL_COMPARE:
        per_window: dict[str, object] = {}
        for name, window in WINDOWS_S.items():
            per_window[name] = delta_summary(
                traces["REPLAY_SINGLE"], traces["REPLAY_ARRAY"], spec["left"], spec["right"], spec["kind"], window,
                "REPLAY_ARRAY - REPLAY_SINGLE",
            )
        replay[spec["id"]] = {"caption": spec["caption"], "kind": spec["kind"], "windows": per_window}

    array = traces["ARRAY_PASSIVE"]
    lsl = {f"BVM{i}": array.column(f"I(L_SL|XBVM{i})") for i in range(1, 5)}
    jsl1 = array.column("I(B_JSL1)")
    jsl8 = array.column("I(B_JSL8)")
    sum_lsl = tuple(sum(lsl[f"BVM{i}"][index] for i in range(1, 5)) for index in range(array.sample_count))
    balance_residual = linear_kcl_residual(
        {**lsl, "JSL1": jsl1},
        {"BVM1": 1.0, "BVM2": 1.0, "BVM3": 1.0, "BVM4": 1.0, "JSL1": -1.0},
    )
    balance: dict[str, object] = {
        "branch_orientation": {
            "BVM_LSL": "I(L_SL|XBVMi), netlist L_SL 12 -> SL",
            "JSL1": "I(B_JSL1), netlist COMMON_SL -> JSL_NODE1",
            "registered_kcl": "sum_i I(L_SL|XBVMi) - I(B_JSL1) = 0 at COMMON_SL",
        },
        "branches": {},
        "sum_lsl": {},
        "kcl_residual": {},
    }
    for name, values in lsl.items():
        balance["branches"][name] = {window: summary(values, array.time, "I", interval) for window, interval in WINDOWS_S.items()}
    balance["sum_lsl"] = {window: summary(sum_lsl, array.time, "I", interval) for window, interval in WINDOWS_S.items()}
    balance["jSL1"] = {window: summary(jsl1, array.time, "I", interval) for window, interval in WINDOWS_S.items()}
    balance["jSL8"] = {window: summary(jsl8, array.time, "I", interval) for window, interval in WINDOWS_S.items()}
    balance["kcl_residual"] = {
        window: kcl_window_metrics(array.time, balance_residual, interval, unit="A")
        for window, interval in WINDOWS_S.items()
    }

    case_ranges: dict[str, object] = {}
    for case, trace in traces.items():
        case_ranges[case] = {
            "source_or_receiver": "passive" if "PASSIVE" in case else "replay",
            "key_signals": {},
        }
        labels = [SOURCE_SIGNAL, "I(B_JSL1)", "V(SL1)"] if case == "SINGLE_PASSIVE" else []
        if case == "ARRAY_PASSIVE":
            labels = [SOURCE_SIGNAL, "I(B_JSL1)", "V(COMMON_SL)", "I(L_SL|XBVM1)", "I(L_SL|XBVM2)", "I(L_SL|XBVM3)", "I(L_SL|XBVM4)"]
        if "REPLAY" in case:
            labels = ["I(I_REPLAY)", "I(LIN|XBQ1)", "V(QBIN)", "P(BJ1|XBQ1)", "P(BJ2|XBQ1)", "P(B01|XJTL1_1)", "P(B01|XJTL1_6)", "I(R_TERM)"]
        kinds = {label: ("P" if label.startswith("P(") else "V" if label.startswith("V(") else "I") for label in labels}
        for label, kind in kinds.items():
            case_ranges[case]["key_signals"][label] = {window: summary(series(trace, label, kind), trace.time, kind, interval) for window, interval in WINDOWS_S.items()}

    return {
        "passive_source_comparison": passive,
        "replay_comparison": replay,
        "array_current_balance": balance,
        "case_key_signal_summaries": case_ranges,
    }


def replay_phase_area_metrics(traces: dict[str, RawTrace]) -> dict[str, object]:
    out: dict[str, object] = {}
    for case in ("REPLAY_SINGLE", "REPLAY_ARRAY"):
        trace = traces[case]
        out[case] = {}
        for jj in ("BJS", "BJ1", "BJ2"):
            phase = trace.column(f"P({jj}|XBQ1)")
            voltage = trace.column(f"V({jj}|XBQ1)")
            out[case][jj] = {
                window: phase_area_window(trace.time, phase, voltage, interval, include_segments=False)
                for window, interval in WINDOWS_S.items()
            }
    return {
        "method": "same-JJ P/V, same endpoint/direction, actual time grid; descriptive consistency only",
        "raw_phase_unit": "rad",
        "display_conversion": "continuous_unwrap(rad)/(2*pi)",
        "cases": out,
    }


def contextual_direct_comparison(traces: dict[str, RawTrace]) -> dict[str, object]:
    specs = [
        ("QBIN_V", "V(QBIN)", "V"),
        ("LIN_I", "I(LIN|XBQ1)", "I"),
        ("BJ1_P", "P(BJ1|XBQ1)", "P"),
        ("BJ2_P", "P(BJ2|XBQ1)", "P"),
        ("JTL1_B01_P", "P(B01|XJTL1_1)", "P"),
        ("JTL6_B01_P", "P(B01|XJTL1_6)", "P"),
        ("R_TERM_I", "I(R_TERM)", "I"),
    ]
    out: dict[str, object] = {
        "status": "CONTEXT_ONLY_NOT_A_NEW_RUN",
        "reference_experiment": DIRECT_EXP.relative_to(REPO).as_posix(),
        "reference_raw_hashes": {},
        "comparisons": {},
    }
    for role, direct_case, replay_case in (("SINGLE", "single", "REPLAY_SINGLE"), ("ARRAY", "array", "REPLAY_ARRAY")):
        direct_path = DIRECT_EXP / "runs" / direct_case / "raw.csv"
        direct = read_csv(direct_path)
        out["reference_raw_hashes"][role] = {"path": direct_path.relative_to(REPO).as_posix(), "sha256": sha256(direct_path)}
        group: dict[str, object] = {}
        if not exact_grid(direct, traces[replay_case]):
            group["status"] = "INCONCLUSIVE_NO_INTERPOLATION_GRID_MISMATCH"
        else:
            group["status"] = "DESCRIPTIVE_VALID"
            for identifier, label, kind in specs:
                group[identifier] = {
                    window: delta_summary(direct, traces[replay_case], label, label, kind, interval, f"{replay_case} - DIRECT_{role}")
                    for window, interval in WINDOWS_S.items()
                }
        out["comparisons"][role] = group
    return out


def write_csv(path: Path, times: tuple[float, ...], columns: list[tuple[str, tuple[float, ...]]]) -> dict[str, object]:
    if any(len(values) != len(times) for _, values in columns):
        raise RuntimeError(f"derived column length mismatch: {path}")
    buffer = StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(["time"] + [label for label, _ in columns])
    for index, time in enumerate(times):
        writer.writerow([f"{time:.17g}"] + [f"{values[index]:.17g}" for _, values in columns])
    content = buffer.getvalue()
    write_once(path, content)
    return {"path": path.relative_to(REPO).as_posix(), "sha256": sha256(path), "labels": [label for label, _ in columns], "sample_count": len(times)}


def p_label(base: str, role: str) -> str:
    return f"P({base}) | {role} [continuous rad]"


def iv_label(kind: str, base: str, role: str) -> str:
    unit = "A" if kind == "I" else "V"
    return f"{kind}({base}) | {role} [{unit}]"


def build_plot_inputs(traces: dict[str, RawTrace]) -> dict[str, object]:
    plot_dir = EXP / "plots/data"
    inputs: dict[str, object] = {}

    passive_columns: list[tuple[str, tuple[float, ...]]] = []
    for spec in PASSIVE_COMPARE:
        kind = spec["kind"]
        left_label = spec["left"]
        right_label = spec["right"]
        left_values = series(traces["SINGLE_PASSIVE"], left_label, kind)
        right_values = series(traces["ARRAY_PASSIVE"], right_label, kind)
        delta = tuple(r - l for l, r in zip(left_values, right_values))
        base = spec["caption"]
        if kind == "P":
            left_plot = p_label(base, "SINGLE_PASSIVE")
            right_plot = p_label(base, "ARRAY_PASSIVE")
            delta_plot = p_label(f"DELTA {base} = ARRAY_PASSIVE - SINGLE_PASSIVE", "DELTA")
        else:
            left_plot = iv_label(kind, base, "SINGLE_PASSIVE")
            right_plot = iv_label(kind, base, "ARRAY_PASSIVE")
            delta_plot = iv_label(kind, f"DELTA {base} = ARRAY_PASSIVE - SINGLE_PASSIVE", "DELTA")
        passive_columns += [(left_plot, left_values), (right_plot, right_values), (delta_plot, delta)]
    inputs["PASSIVE_SOURCE_COMPARE"] = write_csv(plot_dir / "PASSIVE_SOURCE_COMPARE.csv", traces["SINGLE_PASSIVE"].time, passive_columns)

    array = traces["ARRAY_PASSIVE"]
    lsl = [array.column(f"I(L_SL|XBVM{i})") for i in range(1, 5)]
    sum_lsl = tuple(sum(lsl[i][index] for i in range(4)) for index in range(array.sample_count))
    balance_columns = [(f"I(L_SL|XBVM{i}) | ARRAY_PASSIVE BVM{i} [A]", lsl[i - 1]) for i in range(1, 5)]
    balance_columns += [
        ("I(SUM_LSL = BVM1+BVM2+BVM3+BVM4) | ARRAY_PASSIVE [A]", sum_lsl),
        ("I(B_JSL1) | ARRAY_PASSIVE [A]", array.column("I(B_JSL1)")),
        ("I(B_JSL8) | ARRAY_PASSIVE [A]", array.column("I(B_JSL8)")),
    ]
    inputs["ARRAY_CURRENT_BALANCE"] = write_csv(plot_dir / "ARRAY_CURRENT_BALANCE.csv", array.time, balance_columns)

    replay_columns: list[tuple[str, tuple[float, ...]]] = []
    for spec in REPLAY_COMPARE:
        kind = spec["kind"]
        left_values = series(traces["REPLAY_SINGLE"], spec["left"], kind)
        right_values = series(traces["REPLAY_ARRAY"], spec["right"], kind)
        delta = tuple(r - l for l, r in zip(left_values, right_values))
        caption = spec["caption"]
        if kind == "P":
            left_plot = p_label(caption, "REPLAY_SINGLE")
            right_plot = p_label(caption, "REPLAY_ARRAY")
            delta_plot = p_label(f"DELTA {caption} = REPLAY_ARRAY - REPLAY_SINGLE", "DELTA")
        else:
            left_plot = iv_label(kind, caption, "REPLAY_SINGLE")
            right_plot = iv_label(kind, caption, "REPLAY_ARRAY")
            delta_plot = iv_label(kind, f"DELTA {caption} = REPLAY_ARRAY - REPLAY_SINGLE", "DELTA")
        replay_columns += [(left_plot, left_values), (right_plot, right_values), (delta_plot, delta)]
    inputs["QB_REPLAY_COMPARE"] = write_csv(plot_dir / "QB_REPLAY_COMPARE.csv", traces["REPLAY_SINGLE"].time, replay_columns)

    jtl_columns: list[tuple[str, tuple[float, ...]]] = []
    for spec in JTL_COMPARE:
        kind = spec["kind"]
        left_values = series(traces["REPLAY_SINGLE"], spec["left"], kind)
        right_values = series(traces["REPLAY_ARRAY"], spec["right"], kind)
        delta = tuple(r - l for l, r in zip(left_values, right_values))
        caption = spec["caption"]
        if kind == "P":
            left_plot = p_label(caption, "REPLAY_SINGLE")
            right_plot = p_label(caption, "REPLAY_ARRAY")
            delta_plot = p_label(f"DELTA {caption} = REPLAY_ARRAY - REPLAY_SINGLE", "DELTA")
        else:
            left_plot = iv_label(kind, caption, "REPLAY_SINGLE")
            right_plot = iv_label(kind, caption, "REPLAY_ARRAY")
            delta_plot = iv_label(kind, f"DELTA {caption} = REPLAY_ARRAY - REPLAY_SINGLE", "DELTA")
        jtl_columns += [(left_plot, left_values), (right_plot, right_values), (delta_plot, delta)]
    inputs["JTL_REPLAY_COMPARE"] = write_csv(plot_dir / "JTL_REPLAY_COMPARE.csv", traces["REPLAY_SINGLE"].time, jtl_columns)

    # The target overlay/delta plus all three quiet-cell control histories make
    # the registered WRITE/READ protocol visible in one focused page.
    control_columns: list[tuple[str, tuple[float, ...]]] = []
    for name in ("WL", "BL", "SE"):
        single = traces["SINGLE_PASSIVE"].column(f"I(I_{name}1)")
        target = traces["ARRAY_PASSIVE"].column(f"I(I_{name}1)")
        delta = tuple(r - l for l, r in zip(single, target))
        control_columns += [
            (f"I(I_{name}1) | SINGLE_PASSIVE target [A]", single),
            (f"I(I_{name}1) | ARRAY_PASSIVE BVM1 target [A]", target),
            (f"I(DELTA_{name}1 = ARRAY_BVM1 - SINGLE) [A]", delta),
        ]
    for instance in (2, 3, 4):
        for name in ("WL", "BL", "SE"):
            control_columns.append((f"I(I_{name}{instance}) | ARRAY_PASSIVE BVM{instance} quiet/control [A]", traces["ARRAY_PASSIVE"].column(f"I(I_{name}{instance})")))
    inputs["READ_WRITE_CONTROLS"] = write_csv(plot_dir / "READ_WRITE_CONTROLS.csv", traces["SINGLE_PASSIVE"].time, control_columns)
    return inputs


def numerical_qa(traces: dict[str, RawTrace]) -> dict[str, object]:
    reference = traces["SINGLE_PASSIVE"]
    grid = {name: exact_grid(reference, trace) for name, trace in traces.items()}
    return {
        "schema": "jm2-passive-capture-replay-numerical-qa-v1",
        "created_at_local": now_local(),
        "status": "PASS" if all(grid.values()) else "FAIL",
        "time_grids_exact_to_SINGLE_PASSIVE": grid,
        "sample_counts": {name: trace.sample_count for name, trace in traces.items()},
        "time_start_ps": {name: trace.time[0] * 1e12 for name, trace in traces.items()},
        "time_end_ps": {name: trace.time[-1] * 1e12 for name, trace in traces.items()},
        "integral_grid": "actual stored time values; trapezoid only",
        "window_semantics": "registered half-open windows",
        "phase_unwrap": "full trace continuous_unwrap before window selection or subtraction",
        "interpolation_used": False,
        "event_alignment_used": False,
        "convergence": "UNKNOWN; no timestep sweep registered or run",
        "sensitivity": "UNKNOWN; no parameter sweep registered or run",
    }


def provenance(traces: dict[str, RawTrace], plot_inputs: dict[str, object]) -> dict[str, object]:
    version = subprocess.check_output([str(REPO / "build/josim-cli"), "--version"], cwd=REPO, text=True).strip()
    source_manifest_path = EXP / "source/source_manifest.json"
    replay_manifest_path = EXP / "analysis/replay_source_manifest.json"
    files = {
        "bvm_variant": REPO / "test/exploration/bvmsim-jm2-connected-single-ab-v1-20260903/variants/bvm_jm2_connected.cir",
        "canonical_bvm_not_used": REPO / "circuits/bvm/bvm_cell.cir",
        "jjmit": REPO / "circuits/models/jjmit.cir",
        "qb": REPO / "BVMSim/BQ.cir",
        "jtl": REPO / "BVMSim/library_josim/jtl2.cir",
        "solver": REPO / "build/josim-cli",
    }
    sources = {name: {"path": path.relative_to(REPO).as_posix(), "sha256": sha256(path), "bytes": path.stat().st_size} for name, path in files.items()}
    decks = {}
    for case in RAW_CASES:
        deck = EXP / "runs" / case.lower() / "deck.cir"
        decks[case] = {"path": deck.relative_to(REPO).as_posix(), "sha256": sha256(deck), "bytes": deck.stat().st_size}
    raw = {name: {"path": path.relative_to(REPO).as_posix(), "sha256": sha256(path), "bytes": path.stat().st_size} for name, path in RAW_CASES.items()}
    return {
        "schema": "jm2-passive-capture-replay-provenance-v1",
        "experiment_id": EXP.name,
        "created_at_local": now_local(),
        "head_at_setup": "510cb59ebaa237268980133435aa2ff32468c935",
        "head_at_analysis": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip(),
        "solver": {"path": "build/josim-cli", "sha256": sha256(REPO / "build/josim-cli"), "version": version},
        "sources": sources,
        "source_manifest": {"path": source_manifest_path.relative_to(REPO).as_posix(), "sha256": sha256(source_manifest_path)},
        "replay_source_manifest": {"path": replay_manifest_path.relative_to(REPO).as_posix(), "sha256": sha256(replay_manifest_path)},
        "decks": decks,
        "raw": raw,
        "contextual_direct_reference": {
            "experiment": DIRECT_EXP.relative_to(REPO).as_posix(),
            "single_raw_sha256": sha256(DIRECT_EXP / "runs/single/raw.csv"),
            "array_raw_sha256": sha256(DIRECT_EXP / "runs/array/raw.csv"),
            "rerun": False,
        },
        "analysis_scripts": {name: {"path": f"{EXP.relative_to(REPO).as_posix()}/analysis/{name}.py", "sha256": sha256(EXP / "analysis" / f"{name}.py")} for name in ("analyze", "preflight", "run_passive", "build_replay", "replay_preflight", "run_replay")},
        "plotter": {"path": "scripts/josim-plot2.py", "sha256": sha256(REPO / "scripts/josim-plot2.py"), "options": "sep_comb dark -j 2pi"},
        "plot_inputs": plot_inputs,
        "phase_rule": "raw P radians -> continuous_unwrap -> display rad/(2*pi) turns; never SFQ count",
        "raw_unchanged_during_analysis": True,
    }


def main() -> int:
    before_hashes = {name: sha256(path) for name, path in RAW_CASES.items()}
    traces = load_traces()
    qa = artifact_qa(traces)
    fidelity = source_snapshot_fidelity(traces)
    if qa["status"] != "PASS" or fidelity["status"] != "PASS":
        raise RuntimeError(f"artifact/source QA failed: {qa['failures']} {fidelity['failures']}")
    metric_groups = build_comparison_metrics(traces)
    phase_area = replay_phase_area_metrics(traces)
    direct_context = contextual_direct_comparison(traces)
    plot_inputs = build_plot_inputs(traces)
    after_hashes = {name: sha256(path) for name, path in RAW_CASES.items()}
    unchanged = before_hashes == after_hashes
    if not unchanged:
        raise RuntimeError("raw hash changed during analysis")
    numerical = numerical_qa(traces)
    metrics = {
        "schema": "jm2-passive-capture-replay-metrics-v1",
        "experiment_id": EXP.name,
        "created_at_local": now_local(),
        "status": "DESCRIPTIVE_VALID",
        "comparison_conventions": {
            "passive": "ARRAY_PASSIVE - SINGLE_PASSIVE",
            "replay": "REPLAY_ARRAY - REPLAY_SINGLE",
            "direct_context": "REPLAY_CASE - DIRECT_CONTEXT_CASE",
        },
        "windows_ps": {name: list(interval) for name, interval in WINDOWS_PS.items()},
        "time_grid": numerical,
        "source_fidelity": fidelity,
        **metric_groups,
        "replay_phase_area": phase_area,
        "contextual_direct_comparison": direct_context,
        "raw_hashes_before_analysis": before_hashes,
        "raw_hashes_after_analysis": after_hashes,
        "raw_unchanged_before_after_analysis": unchanged,
        "event_count_statement": "No SFQ event count is computed or claimed; phase/area/threshold activity are descriptive only.",
    }
    write_once(EXP / "analysis/artifact_qa.json", json.dumps(qa, indent=2, ensure_ascii=False) + "\n")
    write_once(EXP / "analysis/source_fidelity.json", json.dumps(fidelity, indent=2, ensure_ascii=False) + "\n")
    write_once(EXP / "analysis/numerical_qa.json", json.dumps(numerical, indent=2, ensure_ascii=False) + "\n")
    write_once(EXP / "analysis/metrics.json", json.dumps(metrics, indent=2, ensure_ascii=False) + "\n")
    write_once(EXP / "analysis/provenance.json", json.dumps(provenance(traces, plot_inputs), indent=2, ensure_ascii=False) + "\n")
    write_once(EXP / "analysis/plot_inputs.json", json.dumps(plot_inputs, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"status": "PASS", "metrics": "analysis/metrics.json", "plots": list(plot_inputs), "raw_unchanged": unchanged}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
