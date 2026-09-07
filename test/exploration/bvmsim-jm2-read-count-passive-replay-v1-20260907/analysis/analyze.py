#!/usr/bin/env python3
"""Analyze N1-N4 read-count passive/replay raw evidence without event counting."""

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


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
BASELINE = REPO / "test/exploration/bvmsim-jm2-passive-capture-replay-v1-20260907"
DIRECT_EXP = REPO / "test/exploration/bvmsim-jm2-single-vs-4bvm-shared-sl-v1-20260907"
HEAD_AT_SETUP = "217305580f1c9cec17839896730fbe9b1016c837"
TAU = 2.0 * math.pi
PHI0 = 2.067833848e-15
SOURCE_SIGNAL = "I(B_JSL8)"

RAW_CASES: OrderedDict[str, Path] = OrderedDict(
    [
        ("N1_PASSIVE", BASELINE / "runs/array_passive/raw.csv"),
        ("N2_PASSIVE", EXP / "runs/n2_passive/raw.csv"),
        ("N3_PASSIVE", EXP / "runs/n3_passive/raw.csv"),
        ("N4_PASSIVE", EXP / "runs/n4_passive/raw.csv"),
        ("N1_REPLAY", BASELINE / "runs/replay_array/raw.csv"),
        ("N2_REPLAY", EXP / "runs/n2_replay/raw.csv"),
        ("N3_REPLAY", EXP / "runs/n3_replay/raw.csv"),
        ("N4_REPLAY", EXP / "runs/n4_replay/raw.csv"),
    ]
)
PASSIVE_CASES = tuple(f"N{count}_PASSIVE" for count in (1, 2, 3, 4))
REPLAY_CASES = tuple(f"N{count}_REPLAY" for count in (1, 2, 3, 4))
NEW_CASES = tuple(name for name in RAW_CASES if name not in ("N1_PASSIVE", "N1_REPLAY"))

WINDOWS_PS: OrderedDict[str, tuple[float, float]] = OrderedDict(
    [
        ("INITIAL_PRE_WRITE0", (0.0, 50.0)),
        ("WRITE0", (50.0, 61.0)),
        ("PRE_ZERO_READ", (61.0, 70.0)),
        ("ZERO_STATE_READ_CONTROL", (70.0, 81.0)),
        ("POST_ZERO_READ", (81.0, 90.0)),
        ("WRITE1", (90.0, 101.0)),
        ("PRE_FINAL_READ", (101.0, 110.0)),
        ("FINAL_READ", (110.0, 121.0)),
        ("FINAL_READ_RESPONSE", (110.0, 200.0)),
        ("TAIL", (121.0, 200.0)),
    ]
)
WINDOWS_S = OrderedDict((name, (start * 1e-12, end * 1e-12)) for name, (start, end) in WINDOWS_PS.items())

sys.path.insert(0, str(REPO / "scripts"))
from bvmtools.kcl import kcl_window_metrics, linear_kcl_residual  # noqa: E402
from bvmtools.metrics import phase_area_window  # noqa: E402
from bvmtools.phase import continuous_unwrap, window_indices  # noqa: E402
from bvmtools.raw import RawTrace, read_csv  # noqa: E402
from bvmtools.waveform import percentile, trapezoid_integral, waveform_metrics  # noqa: E402


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


def exact_grid(left: RawTrace, right: RawTrace) -> bool:
    return len(left.time) == len(right.time) and all(a == b for a, b in zip(left.time, right.time))


def series(trace: RawTrace, label: str, kind: str) -> tuple[float, ...]:
    values = trace.column(label)
    if kind == "P":
        return continuous_unwrap(values)  # type: ignore[arg-type]
    return values  # type: ignore[return-value]


def select_window(times: tuple[float, ...], values: tuple[float, ...], window: tuple[float, float]) -> tuple[list[float], list[float]]:
    indices = window_indices(times, *window)
    if len(indices) < 2:
        raise RuntimeError(f"window has fewer than two samples: {window}")
    return [times[index] for index in indices], [values[index] for index in indices]


def scale_for(kind: str) -> tuple[float, float, str, str]:
    if kind == "I":
        return 1e6, 1e18, "uA", "uA*ps"
    if kind == "V":
        return 1e3, 1e15, "mV", "mV*ps"
    if kind == "P":
        return 1.0, 1.0, "rad", "rad*s"
    raise ValueError(kind)


def waveform_summary(values: tuple[float, ...], times: tuple[float, ...], kind: str, window: tuple[float, float]) -> dict[str, object]:
    selected_t, selected_v = select_window(times, values, window)
    value_factor, area_factor, display_unit, area_unit = scale_for(kind)
    base = waveform_metrics(selected_t, selected_v)
    return {
        "raw_unit": {"I": "A", "V": "V", "P": "rad"}[kind],
        "display_unit": display_unit,
        "area_unit": area_unit,
        "window_ps": [window[0] * 1e12, window[1] * 1e12],
        "sample_count": int(base["sample_count"]),
        "minimum": float(base["minimum"]) * value_factor,
        "maximum": float(base["maximum"]) * value_factor,
        "mean": float(base["mean"]) * value_factor,
        "rms": float(base["rms"]) * value_factor,
        "p2p": float(base["p2p"]) * value_factor,
        "max_abs": float(base["max_abs"]) * value_factor,
        "p95_abs": float(percentile([abs(value) for value in selected_v], 0.95)) * value_factor,
        "endpoint": float(selected_v[-1]) * value_factor,
        "endpoint_change": float(selected_v[-1] - selected_v[0]) * value_factor,
        "signed_integral": float(base["signed_time_integral"]) * area_factor,
        "positive_area": float(base["positive_area"]) * area_factor,
        "negative_area": float(base["negative_area"]) * area_factor,
        "zero_crossing_count_activity_only": int(base["zero_crossing_count"]),
        "peak_time_ps": float(base["peak_time"]) * 1e12,
        "minimum_time_ps": float(base["minimum_time"]) * 1e12,
        "window_first_sample_ps": selected_t[0] * 1e12,
        "window_last_sample_ps": selected_t[-1] * 1e12,
    }


def delta_summary(left_trace: RawTrace, right_trace: RawTrace, label: str, kind: str, window: tuple[float, float], convention: str) -> dict[str, object]:
    if not exact_grid(left_trace, right_trace):
        raise RuntimeError(f"exact grid mismatch for {label}")
    left = series(left_trace, label, kind)
    right = series(right_trace, label, kind)
    delta = tuple(r - l for l, r in zip(left, right))
    selected_t, selected_d = select_window(left_trace.time, delta, window)
    value_factor, area_factor, display_unit, area_unit = scale_for(kind)
    base = waveform_metrics(selected_t, selected_d)
    return {
        "label": label,
        "difference_convention": convention,
        "raw_unit": {"I": "A", "V": "V", "P": "rad"}[kind],
        "display_unit": display_unit,
        "area_unit": area_unit,
        "window_ps": [window[0] * 1e12, window[1] * 1e12],
        "sample_count": len(selected_d),
        "max_abs_delta": max(abs(value) for value in selected_d) * value_factor,
        "RMS_delta": math.sqrt(sum(value * value for value in selected_d) / len(selected_d)) * value_factor,
        "p95_abs_delta": float(percentile([abs(value) for value in selected_d], 0.95)) * value_factor,
        "mean_delta": float(base["mean"]) * value_factor,
        "p2p_delta": float(base["p2p"]) * value_factor,
        "signed_integral_delta": float(base["signed_time_integral"]) * area_factor,
        "positive_area_delta": float(base["positive_area"]) * area_factor,
        "negative_area_delta": float(base["negative_area"]) * area_factor,
        "endpoint_delta": selected_d[-1] * value_factor,
        "window_first_sample_ps": selected_t[0] * 1e12,
        "window_last_sample_ps": selected_t[-1] * 1e12,
        **({
            "phase_delta_rad_endpoint": selected_d[-1],
            "phase_delta_turns_endpoint": selected_d[-1] / TAU,
            "phase_p2p_turns": (max(selected_d) - min(selected_d)) / TAU,
            "phase_rule": "continuous_unwrap(raw radians) before subtraction; turns are rad/(2*pi)",
        } if kind == "P" else {}),
    }


def required_passive_headers() -> list[str]:
    expected: list[str] = []
    for instance in range(1, 5):
        handle = f"XBVM{instance}"
        for jj in ("B_JM1", "B_JM2", "B_JS1", "B_JS2"):
            expected += [f"P({jj}|{handle})", f"V({jj}|{handle})", f"I({jj}|{handle})"]
        for branch in ("L_M1", "L_M2", "L_M3", "L_PM", "R_JM1", "L_S1", "L_S2", "R_S", "L_S3", "R_SE", "L_PSE", "L_PSL", "R_SL", "L_SL"):
            expected += [f"I({branch}|{handle})", f"V({branch}|{handle})"]
    expected += [f"I(I_{name}{instance})" for instance in range(1, 5) for name in ("WL", "BL", "SE")]
    expected.append("V(COMMON_SL)")
    for index in range(1, 9):
        expected += [f"P(B_JSL{index})", f"V(B_JSL{index})", f"I(B_JSL{index})"]
    return expected


def required_replay_headers() -> list[str]:
    expected = ["V(QBIN)", "V(QBOUT)", "I(I_REPLAY)"]
    for branch in ("LIN", "L1", "L2", "L3", "RJ1", "RJ2"):
        expected += [f"I({branch}|XBQ1)", f"V({branch}|XBQ1)"]
    expected.append("I(IB|XBQ1)")
    for jj in ("BJS", "BJ1", "BJ2"):
        expected += [f"P({jj}|XBQ1)", f"V({jj}|XBQ1)", f"I({jj}|XBQ1)"]
    for stage in range(1, 7):
        handle = f"XJTL1_{stage}"
        expected += [f"P(B01|{handle})", f"V(B01|{handle})", f"I(B01|{handle})", f"P(B02|{handle})", f"V(B02|{handle})", f"I(B02|{handle})", f"V(JTL{stage}_OUT)"]
    expected.append("I(R_TERM)")
    return expected


def artifact_qa(traces: dict[str, RawTrace], source_manifest: dict[str, object]) -> dict[str, object]:
    required = {**{name: required_passive_headers() for name in PASSIVE_CASES}, **{name: required_replay_headers() for name in REPLAY_CASES}}
    cases: dict[str, object] = {}
    failures: list[str] = []
    for name, trace in traces.items():
        missing = [label for label in required[name] if label not in trace.headers]
        optional = ["V(IB|XBQ1)"] if "REPLAY" in name else []
        missing_optional = [label for label in optional if label not in trace.headers]
        if missing:
            failures.append(f"{name}: missing required headers {missing}")
        if trace.duplicate_columns:
            failures.append(f"{name}: duplicate columns {trace.duplicate_columns}")
        expected_hash = None
        if name in source_manifest.get("n1_reference", {}):
            expected_hash = source_manifest["n1_reference"][name]["sha256"]
        cases[name] = {
            **trace.qa(),
            "path": RAW_CASES[name].relative_to(REPO).as_posix(),
            "raw_sha256": sha256(RAW_CASES[name]),
            "expected_hash_if_reference": expected_hash,
            "reference_hash_match": expected_hash is None or expected_hash == sha256(RAW_CASES[name]),
            "required_header_count": len(required[name]),
            "missing_required_headers": missing,
            "optional_missing_headers": missing_optional,
            "optional_probe_note": "V(IB|XBQ1) requested but absent from emitted JoSIM schema" if missing_optional else None,
            "raw_role": "immutable_N1_reference" if name.startswith("N1_") else "new_run_raw",
        }
        if expected_hash is not None and expected_hash != sha256(RAW_CASES[name]):
            failures.append(f"{name}: immutable reference hash mismatch")
    return {
        "schema": "jm2-read-count-passive-replay-artifact-qa-v1",
        "experiment_id": EXP.name,
        "created_at_local": now_local(),
        "status": "PASS" if not failures else "INVALID",
        "raw_immutable": True,
        "cases": cases,
        "failures": failures,
    }


def csv_token_pairs(path: Path, time_key: str, value_key: str) -> list[tuple[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = csv.DictReader(handle)
        return [(row[time_key], row[value_key]) for row in rows]


def source_snapshot_fidelity(traces: dict[str, RawTrace], replay_manifest: dict[str, object]) -> dict[str, object]:
    records: dict[str, object] = {}
    failures: list[str] = []
    for count in (1, 2, 3, 4):
        passive = f"N{count}_PASSIVE"
        replay = f"N{count}_REPLAY"
        if count == 1:
            snapshot = BASELINE / "data/array_passive_JSL8_source.csv"
        else:
            snapshot = EXP / "data" / f"n{count}_passive_JSL8_source.csv"
        raw_pairs = csv_token_pairs(RAW_CASES[passive], "time", SOURCE_SIGNAL)
        snapshot_pairs = csv_token_pairs(snapshot, "time_s", "current_A")
        exact_snapshot = raw_pairs == snapshot_pairs
        source = traces[passive].column(SOURCE_SIGNAL)
        replay_source = traces[replay].column("I(I_REPLAY)")
        replay_lin = traces[replay].column("I(LIN|XBQ1)")
        grid = exact_grid(traces[passive], traces[replay])
        source_replay = tuple(replay_source[i] - source[i] for i in range(len(source))) if grid else ()
        source_lin = tuple(replay_lin[i] - source[i] for i in range(len(source))) if grid else ()
        replay_vs_lin = tuple(replay_source[i] - replay_lin[i] for i in range(len(replay_source))) if grid else ()
        max_sr = max((abs(value) for value in source_replay), default=math.inf)
        max_sl = max((abs(value) for value in source_lin), default=math.inf)
        max_rl = max((abs(value) for value in replay_vs_lin), default=math.inf)
        if not (exact_snapshot and grid and max_sr == 0.0 and max_sl == 0.0 and max_rl == 0.0):
            failures.append(f"{passive}: snapshot/replay/LIN exact fidelity failed")
        if passive in replay_manifest["sources"]:
            manifest_record = replay_manifest["sources"][passive]
        else:
            baseline_replay_manifest = json.loads((BASELINE / "analysis/replay_source_manifest.json").read_text(encoding="utf-8"))
            manifest_record = baseline_replay_manifest["sources"]["array_passive"]
        records[passive] = {
            "raw_path": RAW_CASES[passive].relative_to(REPO).as_posix(),
            "raw_sha256": sha256(RAW_CASES[passive]),
            "snapshot_path": snapshot.relative_to(REPO).as_posix(),
            "snapshot_sha256": sha256(snapshot),
            "sample_count": len(raw_pairs),
            "exact_snapshot_token_pairs": exact_snapshot,
            "passive_replay_grid_exact": grid,
            "max_abs_source_minus_I_REPLAY_A": max_sr,
            "max_abs_source_minus_LIN_A": max_sl,
            "max_abs_I_REPLAY_minus_LIN_A": max_rl,
            "orientation": "I_REPLAY 0 QBIN; positive injection matches JSL8 -> QBIN branch sense",
            "sign_change": False,
            "transformations": [],
            "replay_case": replay,
            "manifest_snapshot_sha256_match": manifest_record["snapshot"]["sha256"] == sha256(snapshot),
        }
    return {
        "schema": "jm2-read-count-passive-replay-source-fidelity-v1",
        "status": "PASS" if not failures else "FAIL",
        "source_signal": SOURCE_SIGNAL,
        "records": records,
        "failures": failures,
    }


def passive_metrics(traces: dict[str, RawTrace]) -> dict[str, object]:
    signals = OrderedDict([
        ("I(B_JSL1)", "I"),
        ("I(B_JSL8)", "I"),
        ("V(COMMON_SL)", "V"),
    ])
    out: dict[str, object] = {}
    for label, kind in signals.items():
        cases = {
            name: {window: waveform_summary(series(traces[name], label, kind), traces[name].time, kind, interval) for window, interval in WINDOWS_S.items()}
            for name in PASSIVE_CASES
        }
        deltas = {
            name: {window: delta_summary(traces["N1_PASSIVE"], traces[name], label, kind, interval, f"{name} - N1_PASSIVE") for window, interval in WINDOWS_S.items()}
            for name in PASSIVE_CASES[1:]
        }
        out[label] = {"kind": kind, "cases": cases, "deltas_vs_N1": deltas}
    return out


def balance_metrics(traces: dict[str, RawTrace]) -> dict[str, object]:
    out: dict[str, object] = {
        "branch_orientation": {
            "BVM_LSL": "I(L_SL|XBVMi), netlist L_SL 12 -> COMMON_SL",
            "JSL1": "I(B_JSL1), netlist COMMON_SL -> JSL_NODE1",
            "registered_kcl": "sum_i I(L_SL|XBVMi) - I(B_JSL1) = 0 at COMMON_SL",
        },
        "cases": {},
    }
    for name in PASSIVE_CASES:
        trace = traces[name]
        lsl = {f"BVM{i}": trace.column(f"I(L_SL|XBVM{i})") for i in range(1, 5)}
        jsl1 = trace.column("I(B_JSL1)")
        jsl8 = trace.column("I(B_JSL8)")
        sum_lsl = tuple(sum(lsl[f"BVM{i}"][index] for i in range(1, 5)) for index in range(trace.sample_count))
        residual = linear_kcl_residual({**lsl, "JSL1": jsl1}, {"BVM1": 1.0, "BVM2": 1.0, "BVM3": 1.0, "BVM4": 1.0, "JSL1": -1.0})
        item: dict[str, object] = {"branches": {}, "sum_lsl": {}, "jSL1": {}, "jSL8": {}, "kcl_residual": {}}
        for branch, values in lsl.items():
            item["branches"][branch] = {window: waveform_summary(values, trace.time, "I", interval) for window, interval in WINDOWS_S.items()}
        item["sum_lsl"] = {window: waveform_summary(sum_lsl, trace.time, "I", interval) for window, interval in WINDOWS_S.items()}
        item["jSL1"] = {window: waveform_summary(jsl1, trace.time, "I", interval) for window, interval in WINDOWS_S.items()}
        item["jSL8"] = {window: waveform_summary(jsl8, trace.time, "I", interval) for window, interval in WINDOWS_S.items()}
        item["kcl_residual"] = {window: kcl_window_metrics(trace.time, residual, interval, unit="A") for window, interval in WINDOWS_S.items()}
        out["cases"][name] = item
    return out


def replay_response_metrics(traces: dict[str, RawTrace]) -> dict[str, object]:
    specs = OrderedDict([
        ("I(I_REPLAY)", "I"),
        ("V(QBIN)", "V"),
        ("V(QBOUT)", "V"),
        ("P(BJ1|XBQ1)", "P"),
        ("P(BJ2|XBQ1)", "P"),
        ("P(B01|XJTL1_1)", "P"),
        ("P(B01|XJTL1_6)", "P"),
        ("I(R_TERM)", "I"),
    ])
    out: dict[str, object] = {}
    for label, kind in specs.items():
        out[label] = {
            "kind": kind,
            "cases": {
                name: {window: waveform_summary(series(traces[name], label, kind), traces[name].time, kind, interval) for window, interval in WINDOWS_S.items()}
                for name in REPLAY_CASES
            },
            "deltas_vs_N1": {
                name: {window: delta_summary(traces["N1_REPLAY"], traces[name], label, kind, interval, f"{name} - N1_REPLAY") for window, interval in WINDOWS_S.items()}
                for name in REPLAY_CASES[1:]
            },
        }
    return out


def phase_progression(trace: RawTrace, label: str, window: tuple[float, float]) -> dict[str, object]:
    values = continuous_unwrap(trace.column(label))
    indices = window_indices(trace.time, *window)
    if len(indices) < 2:
        raise RuntimeError(f"phase window has fewer than two samples: {label} {window}")
    selected = [values[index] for index in indices]
    return {
        "window_ps": [window[0] * 1e12, window[1] * 1e12],
        "phase_start_rad": selected[0],
        "phase_end_rad": selected[-1],
        "net_phase_displacement_rad": selected[-1] - selected[0],
        "net_phase_displacement_turns": (selected[-1] - selected[0]) / TAU,
        "phase_p2p_rad": max(selected) - min(selected),
        "phase_p2p_turns": (max(selected) - min(selected)) / TAU,
        "raw_unit": "rad",
        "display_conversion": "continuous_unwrap(raw radians)/(2*pi)",
        "sample_count": len(selected),
    }


def phase_area_metrics(traces: dict[str, RawTrace]) -> dict[str, object]:
    out: dict[str, object] = {"same_jj_contract": "same JJ P/V, same endpoint/direction, same actual time window; descriptive consistency only", "cases": {}}
    for name in REPLAY_CASES:
        trace = traces[name]
        out["cases"][name] = {}
        for jj in ("BJS", "BJ1", "BJ2"):
            phase = trace.column(f"P({jj}|XBQ1)")
            voltage = trace.column(f"V({jj}|XBQ1)")
            out["cases"][name][jj] = {
                window: phase_area_window(trace.time, phase, voltage, interval, include_segments=False)
                for window, interval in WINDOWS_S.items()
                if window in ("FINAL_READ", "FINAL_READ_RESPONSE", "TAIL")
            }
    return out


def terminal_metrics(traces: dict[str, RawTrace]) -> dict[str, object]:
    out: dict[str, object] = {"definition": "V_TERM = 10 ohm * I(R_TERM); area integrates V_TERM on actual stored time grid", "phi0_wb": PHI0, "cases": {}}
    for name in REPLAY_CASES:
        trace = traces[name]
        current = trace.column("I(R_TERM)")
        voltage = tuple(10.0 * value for value in current)
        item: dict[str, object] = {"V_TERM": {}, "I_R_TERM": {}, "windows": {}}
        for window_name in ("FINAL_READ", "FINAL_READ_RESPONSE", "TAIL"):
            interval = WINDOWS_S[window_name]
            selected_t, selected_i = select_window(trace.time, current, interval)
            selected_v = [10.0 * value for value in selected_i]
            raw_area = trapezoid_integral(selected_v, selected_t)
            item["I_R_TERM"][window_name] = waveform_summary(current, trace.time, "I", interval)
            item["V_TERM"][window_name] = waveform_summary(voltage, trace.time, "V", interval)
            item["windows"][window_name] = {
                "window_ps": [interval[0] * 1e12, interval[1] * 1e12],
                "sample_count": len(selected_t),
                "terminal_voltage_area_wb": raw_area,
                "terminal_voltage_area_over_phi0": raw_area / PHI0,
                "actual_grid_first_ps": selected_t[0] * 1e12,
                "actual_grid_last_ps": selected_t[-1] * 1e12,
                "formula": "trapezoid_integral(10 * I(R_TERM), actual time grid)",
            }
        out["cases"][name] = item
    return out


def event_audit(traces: dict[str, RawTrace], phase_area: dict[str, object], terminal: dict[str, object]) -> dict[str, object]:
    # No task-local numerical tolerance or convergence result freezes an event
    # classifier here. Record the joint observables, but deliberately do not
    # upgrade them into an SFQ/event disposition.
    out: dict[str, object] = {
        "status": "INCONCLUSIVE",
        "rule": "requires same-JJ phase progression, causal JTL propagation, termination pulse, and terminal area near integer Phi0; no single observable is a count",
        "cases": {},
    }
    for name in REPLAY_CASES:
        jtl6 = phase_progression(traces[name], "P(B01|XJTL1_6)", WINDOWS_S["FINAL_READ_RESPONSE"])
        area = terminal["cases"][name]["windows"]["FINAL_READ_RESPONSE"]
        term_current = terminal["cases"][name]["I_R_TERM"]["FINAL_READ_RESPONSE"]
        out["cases"][name] = {
            "disposition": "INCONCLUSIVE_NO_FROZEN_EVENT_CRITERION",
            "jtl6_progression": jtl6,
            "terminal_area": area,
            "terminal_activity": {
                "max_abs_current_uA": term_current["max_abs"],
                "positive_area_uA_ps": term_current["positive_area"],
            },
            "same_jj_phase_area_available": True,
            "causal_stage_by_stage_transport_verified": False,
            "termination_pulse_jointly_verified": False,
            "event_count": None,
            "reason": "descriptive phase/area/activity is retained; no event count or successful transmission claim is made",
        }
    return out


def read_count_summary(traces: dict[str, RawTrace], terminal: dict[str, object]) -> dict[str, object]:
    rows: dict[str, object] = {}
    for count in (1, 2, 3, 4):
        passive = traces[f"N{count}_PASSIVE"]
        replay = traces[f"N{count}_REPLAY"]
        source = passive.column(SOURCE_SIGNAL)
        source_t, source_v = select_window(passive.time, source, WINDOWS_S["FINAL_READ_RESPONSE"])
        source_base = waveform_metrics(source_t, source_v)
        bj2 = phase_progression(replay, "P(BJ2|XBQ1)", WINDOWS_S["FINAL_READ_RESPONSE"])
        jtl6 = phase_progression(replay, "P(B01|XJTL1_6)", WINDOWS_S["FINAL_READ_RESPONSE"])
        terminal_response = terminal["cases"][f"N{count}_REPLAY"]["windows"]["FINAL_READ_RESPONSE"]
        rows[str(count)] = {
            "read_count": count,
            "final_read_mask": f"{'1' * count}{'0' * (4 - count)}",
            "JSL8_peak_current_A": float(source_base["maximum"]),
            "JSL8_peak_current_uA": float(source_base["maximum"]) * 1e6,
            "JSL8_signed_area_A_s": float(source_base["signed_time_integral"]),
            "JSL8_signed_area_uA_ps": float(source_base["signed_time_integral"]) * 1e18,
            "JSL8_positive_area_A_s": float(source_base["positive_area"]),
            "JSL8_positive_area_uA_ps": float(source_base["positive_area"]) * 1e18,
            "BJ2_net_phase_displacement_rad": bj2["net_phase_displacement_rad"],
            "BJ2_net_phase_displacement_turns": bj2["net_phase_displacement_turns"],
            "JTL6_net_phase_displacement_rad": jtl6["net_phase_displacement_rad"],
            "JTL6_net_phase_displacement_turns": jtl6["net_phase_displacement_turns"],
            "terminal_A_TERM_over_Phi0": terminal_response["terminal_voltage_area_over_phi0"],
            "window": "FINAL_READ_RESPONSE [110 ps, 200 ps)",
        }
    return {
        "x": "read count N",
        "y_series_definitions": {
            "JSL8_peak_current": "positive maximum of I(B_JSL8), A/uA",
            "JSL8_signed_area": "trapezoid integral of I(B_JSL8), A*s/uA*ps",
            "JSL8_positive_area": "trapezoid integral of max(I(B_JSL8),0), A*s/uA*ps",
            "BJ2_net_phase_displacement": "continuous-unwrapped P(BJ2|XBQ1) endpoint displacement, rad and rad/(2*pi) turns",
            "JTL6_net_phase_displacement": "continuous-unwrapped P(B01|XJTL1_6) endpoint displacement, rad and rad/(2*pi) turns",
            "terminal_A_TERM_over_Phi0": "trapezoid integral of 10*I(R_TERM) divided by Phi0, dimensionless",
        },
        "rows": rows,
        "no_monotonicity_assumption": True,
    }


def contextual_direct_reference(traces: dict[str, RawTrace]) -> dict[str, object]:
    direct_array = DIRECT_EXP / "runs/array/raw.csv"
    direct_single = DIRECT_EXP / "runs/single/raw.csv"
    out: dict[str, object] = {
        "status": "CONTEXT_ONLY_NOT_A_NEW_RUN",
        "experiment": DIRECT_EXP.relative_to(REPO).as_posix(),
        "rerun": False,
        "raw_hashes": {
            "direct_single": {"path": direct_single.relative_to(REPO).as_posix(), "sha256": sha256(direct_single)},
            "direct_array": {"path": direct_array.relative_to(REPO).as_posix(), "sha256": sha256(direct_array)},
        },
        "comparison": {},
    }
    direct = read_csv(direct_array)
    replay = traces["N1_REPLAY"]
    labels = OrderedDict([
        ("V(QBIN)", "V"),
        ("I(LIN|XBQ1)", "I"),
        ("P(BJ1|XBQ1)", "P"),
        ("P(BJ2|XBQ1)", "P"),
        ("P(B01|XJTL1_1)", "P"),
        ("I(R_TERM)", "I"),
    ])
    if not exact_grid(direct, replay):
        out["comparison"]["status"] = "INCONCLUSIVE_GRID_MISMATCH_NO_INTERPOLATION"
    else:
        out["comparison"]["status"] = "DESCRIPTIVE_VALID"
        out["comparison"]["difference_convention"] = "N1_REPLAY - DIRECT_ARRAY"
        out["comparison"]["windows"] = {
            label: {window: delta_summary(direct, replay, label, kind, interval, "N1_REPLAY - DIRECT_ARRAY") for window, interval in WINDOWS_S.items()}
            for label, kind in labels.items()
        }
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


def plot_inputs(traces: dict[str, RawTrace], counts: dict[str, object]) -> dict[str, object]:
    plot_dir = EXP / "plots/data"
    reference = traces["N1_PASSIVE"]
    inputs: dict[str, object] = {}
    passive_columns: list[tuple[str, tuple[float, ...]]] = []
    for count in (1, 2, 3, 4):
        name = f"N{count}_PASSIVE"
        passive_columns.append((f"I(B_JSL8) | N{count}_PASSIVE [A]", traces[name].column(SOURCE_SIGNAL)))
    for count in (1, 2, 3, 4):
        name = f"N{count}_PASSIVE"
        passive_columns.append((f"V(COMMON_SL) | N{count}_PASSIVE [V]", traces[name].column("V(COMMON_SL)")))
    inputs["PASSIVE_SOURCE_N1_N4"] = write_csv(plot_dir / "PASSIVE_SOURCE_N1_N4.csv", reference.time, passive_columns)

    balance_columns: list[tuple[str, tuple[float, ...]]] = []
    for count in (1, 2, 3, 4):
        trace = traces[f"N{count}_PASSIVE"]
        lsl = [trace.column(f"I(L_SL|XBVM{i})") for i in range(1, 5)]
        total = tuple(sum(values[index] for values in lsl) for index in range(trace.sample_count))
        for index, values in enumerate(lsl, start=1):
            balance_columns.append((f"I(L_SL|XBVM{index}) | N{count}_PASSIVE BVM{index} [A]", values))
        balance_columns.extend([
            (f"I(SUM_LSL) | N{count}_PASSIVE [A]", total),
            (f"I(B_JSL1) | N{count}_PASSIVE [A]", trace.column("I(B_JSL1)")),
            (f"I(B_JSL8) | N{count}_PASSIVE [A]", trace.column("I(B_JSL8)")),
        ])
    inputs["ARRAY_LSL_BALANCE_N1_N4"] = write_csv(plot_dir / "ARRAY_LSL_BALANCE_N1_N4.csv", reference.time, balance_columns)

    qb_columns: list[tuple[str, tuple[float, ...]]] = []
    for count in (1, 2, 3, 4):
        trace = traces[f"N{count}_REPLAY"]
        qb_columns.extend([
            (f"V(QBIN) | N{count}_REPLAY [V]", trace.column("V(QBIN)")),
            (f"V(QBOUT) | N{count}_REPLAY [V]", trace.column("V(QBOUT)")),
            (f"P(BJ1|XBQ1) | N{count}_REPLAY [continuous rad]", continuous_unwrap(trace.column("P(BJ1|XBQ1)"))),
            (f"P(BJ2|XBQ1) | N{count}_REPLAY [continuous rad]", continuous_unwrap(trace.column("P(BJ2|XBQ1)"))),
        ])
    inputs["QB_REPLAY_N1_N4"] = write_csv(plot_dir / "QB_REPLAY_N1_N4.csv", traces["N1_REPLAY"].time, qb_columns)

    jtl_columns: list[tuple[str, tuple[float, ...]]] = []
    for count in (1, 2, 3, 4):
        trace = traces[f"N{count}_REPLAY"]
        jtl_columns.extend([
            (f"P(JTL1 B01) | N{count}_REPLAY [continuous rad]", continuous_unwrap(trace.column("P(B01|XJTL1_1)"))),
            (f"P(JTL6 B01) | N{count}_REPLAY [continuous rad]", continuous_unwrap(trace.column("P(B01|XJTL1_6)"))),
            (f"I(R_TERM) | N{count}_REPLAY [A]", trace.column("I(R_TERM)")),
        ])
    inputs["JTL_REPLAY_N1_N4"] = write_csv(plot_dir / "JTL_REPLAY_N1_N4.csv", traces["N1_REPLAY"].time, jtl_columns)

    summary_rows = counts["rows"]
    summary_columns: list[tuple[str, tuple[float, ...]]] = [
        ("I(JSL8 peak current) [A]", tuple(summary_rows[str(count)]["JSL8_peak_current_A"] for count in (1, 2, 3, 4))),
        ("I(JSL8 signed area) [A*s]", tuple(summary_rows[str(count)]["JSL8_signed_area_A_s"] for count in (1, 2, 3, 4))),
        ("I(JSL8 positive area) [A*s]", tuple(summary_rows[str(count)]["JSL8_positive_area_A_s"] for count in (1, 2, 3, 4))),
        ("P(BJ2 net phase displacement) [raw rad; shown turns]", tuple(summary_rows[str(count)]["BJ2_net_phase_displacement_rad"] for count in (1, 2, 3, 4))),
        ("P(JTL6 net phase displacement) [raw rad; shown turns]", tuple(summary_rows[str(count)]["JTL6_net_phase_displacement_rad"] for count in (1, 2, 3, 4))),
        ("V(terminal area / Phi0) [dimensionless]", tuple(summary_rows[str(count)]["terminal_A_TERM_over_Phi0"] for count in (1, 2, 3, 4))),
    ]
    inputs["READ_COUNT_SUMMARY"] = write_csv(plot_dir / "READ_COUNT_SUMMARY.csv", (1.0, 2.0, 3.0, 4.0), summary_columns)
    return inputs


def numerical_qa(traces: dict[str, RawTrace]) -> dict[str, object]:
    reference = traces["N1_PASSIVE"]
    grid = {name: exact_grid(reference, trace) for name, trace in traces.items()}
    return {
        "schema": "jm2-read-count-passive-replay-numerical-qa-v1",
        "created_at_local": now_local(),
        "status": "PASS" if all(grid.values()) else "FAIL",
        "time_grids_exact_to_N1_PASSIVE": grid,
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


def provenance(traces: dict[str, RawTrace], inputs: dict[str, object]) -> dict[str, object]:
    files = {
        "bvm_variant": REPO / "test/exploration/bvmsim-jm2-connected-single-ab-v1-20260903/variants/bvm_jm2_connected.cir",
        "canonical_bvm_not_used": REPO / "circuits/bvm/bvm_cell.cir",
        "jjmit": REPO / "circuits/models/jjmit.cir",
        "qb": REPO / "BVMSim/BQ.cir",
        "jtl": REPO / "BVMSim/library_josim/jtl2.cir",
        "solver": REPO / "build/josim-cli",
    }
    sources = {name: {"path": path.relative_to(REPO).as_posix(), "sha256": sha256(path), "bytes": path.stat().st_size} for name, path in files.items()}
    decks: dict[str, object] = {}
    for name in (*PASSIVE_CASES, *REPLAY_CASES):
        if name.startswith("N1_"):
            old_case = "array_passive" if name == "N1_PASSIVE" else "replay_array"
            path = BASELINE / "runs" / old_case / "deck.cir"
        else:
            path = EXP / "runs" / name.lower() / "deck.cir"
        decks[name] = {"path": path.relative_to(REPO).as_posix(), "sha256": sha256(path), "bytes": path.stat().st_size, "reference_or_new": "N1_REFERENCE" if name.startswith("N1_") else "NEW"}
    raw = {name: {"path": path.relative_to(REPO).as_posix(), "sha256": sha256(path), "bytes": path.stat().st_size, "reference_or_new": "N1_REFERENCE" if name.startswith("N1_") else "NEW"} for name, path in RAW_CASES.items()}
    version = subprocess.check_output([str(REPO / "build/josim-cli"), "--version"], cwd=REPO, text=True).strip()
    script_names = ("analyze", "preflight", "run_passive", "build_replay", "replay_preflight", "run_replay", "independent_check", "render_plots")
    return {
        "schema": "jm2-read-count-passive-replay-provenance-v1",
        "experiment_id": EXP.name,
        "created_at_local": now_local(),
        "head_at_setup": HEAD_AT_SETUP,
        "head_at_analysis": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip(),
        "solver": {"path": "build/josim-cli", "sha256": sha256(REPO / "build/josim-cli"), "version": version},
        "sources": sources,
        "source_manifest": {"path": "test/exploration/bvmsim-jm2-read-count-passive-replay-v1-20260907/source/source_manifest.json", "sha256": sha256(EXP / "source/source_manifest.json")},
        "replay_source_manifest": {"path": "test/exploration/bvmsim-jm2-read-count-passive-replay-v1-20260907/analysis/replay_source_manifest.json", "sha256": sha256(EXP / "analysis/replay_source_manifest.json")},
        "decks": decks,
        "raw": raw,
        "n1_reference_experiment": BASELINE.relative_to(REPO).as_posix(),
        "contextual_direct_reference": DIRECT_EXP.relative_to(REPO).as_posix(),
        "analysis_scripts": {name: {"path": f"{EXP.relative_to(REPO).as_posix()}/analysis/{name}.py", "sha256": sha256(EXP / "analysis" / f"{name}.py")} for name in script_names},
        "plotter": {"path": "scripts/josim-plot2.py", "sha256": sha256(REPO / "scripts/josim-plot2.py"), "options": "sep_comb dark -j 2pi"},
        "plot_inputs": inputs,
        "phase_rule": "raw P radians -> continuous_unwrap -> display rad/(2*pi) turns; never an SFQ count",
        "raw_unchanged_during_analysis": True,
    }


def main() -> int:
    source_manifest = json.loads((EXP / "source/source_manifest.json").read_text(encoding="utf-8"))
    replay_manifest = json.loads((EXP / "analysis/replay_source_manifest.json").read_text(encoding="utf-8"))
    before = {name: sha256(path) for name, path in RAW_CASES.items()}
    traces = load_traces()
    qa = artifact_qa(traces, source_manifest)
    if qa["status"] != "PASS":
        raise RuntimeError(f"artifact QA failed: {qa['failures']}")
    fidelity = source_snapshot_fidelity(traces, replay_manifest)
    if fidelity["status"] != "PASS":
        raise RuntimeError(f"source fidelity failed: {fidelity['failures']}")
    passive = passive_metrics(traces)
    balance = balance_metrics(traces)
    replay = replay_response_metrics(traces)
    phase_area = phase_area_metrics(traces)
    terminal = terminal_metrics(traces)
    events = event_audit(traces, phase_area, terminal)
    counts = read_count_summary(traces, terminal)
    direct = contextual_direct_reference(traces)
    inputs = plot_inputs(traces, counts)
    after = {name: sha256(path) for name, path in RAW_CASES.items()}
    if before != after:
        raise RuntimeError("raw hash changed during analysis")
    numerical = numerical_qa(traces)
    metrics = {
        "schema": "jm2-read-count-passive-replay-metrics-v1",
        "experiment_id": EXP.name,
        "created_at_local": now_local(),
        "status": "DESCRIPTIVE_VALID",
        "comparison_conventions": {"passive": "N2/N3/N4 - N1", "replay": "N2/N3/N4 - N1", "direct_context": "N1_REPLAY - DIRECT_ARRAY"},
        "windows_ps": {name: list(interval) for name, interval in WINDOWS_PS.items()},
        "time_grid": numerical,
        "source_fidelity": fidelity,
        "passive_source_comparison": passive,
        "array_lsl_balance": balance,
        "replay_response": replay,
        "replay_phase_area": phase_area,
        "terminal_metrics": terminal,
        "event_audit": events,
        "read_count_summary": counts,
        "contextual_direct_reference": direct,
        "raw_hashes_before_analysis": before,
        "raw_hashes_after_analysis": after,
        "raw_unchanged_before_after_analysis": before == after,
        "event_count_statement": "No SFQ event count is computed or claimed; phase/area/threshold activity are descriptive only.",
    }
    write_once(EXP / "analysis/artifact_qa.json", json.dumps(qa, indent=2, ensure_ascii=False) + "\n")
    write_once(EXP / "analysis/source_fidelity.json", json.dumps(fidelity, indent=2, ensure_ascii=False) + "\n")
    write_once(EXP / "analysis/numerical_qa.json", json.dumps(numerical, indent=2, ensure_ascii=False) + "\n")
    write_once(EXP / "analysis/metrics.json", json.dumps(metrics, indent=2, ensure_ascii=False) + "\n")
    write_once(EXP / "analysis/plot_inputs.json", json.dumps(inputs, indent=2, ensure_ascii=False) + "\n")
    write_once(EXP / "analysis/provenance.json", json.dumps(provenance(traces, inputs), indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"status": "PASS", "metrics": "analysis/metrics.json", "plot_inputs": list(inputs), "raw_unchanged": before == after}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
