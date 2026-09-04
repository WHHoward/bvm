#!/usr/bin/env python3
"""Analyze the ten all-one/selective-read array runs.

The experiment-local code owns the windows, mask semantics and interpretation.
Raw parsing, phase unwrapping, waveform arithmetic, KCL combinations, strict
local event diagnostics and pointwise comparisons are delegated to bvmtools.
No phase displacement or voltage area is promoted to an SFQ count here.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, Sequence


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
SOLVER = REPO / "build/josim-cli"
SINGLE = REPO / "test/exploration/bvmsim-jm2-connected-single-rloop-observability-v1-20260904/runs/S1-J-RLOOP/raw.csv"
METRIC_SPEC = REPO / "docs/research/METRIC_SPEC_V2.md"
MASKS = ("0000", "0001", "0010", "0100", "1000", "0011", "0111", "1100", "1110", "1111")
ONE_HOT = ("0001", "0010", "0100", "1000")
ONE_HOT_BY_INSTANCE = {1: "1000", 2: "0100", 3: "0010", 4: "0001"}
FORWARD = ("1100", "1110", "1111")
REVERSE = ("0011", "0111", "1111")

WINDOWS_PS = OrderedDict(
    (
        ("PRE", (45.0, 50.0)),
        ("WRITE0", (50.0, 70.0)),
        ("PRE_ALL_ONE_WRITE", (70.0, 90.0)),
        ("WRITE1_ALL", (90.0, 101.0)),
        ("SETTLE_1111", (101.0, 110.0)),
        ("READ", (110.0, 170.0)),
        ("TAIL", (170.0, 200.0)),
    )
)
WINDOWS_S = OrderedDict((name, (left * 1e-12, right * 1e-12)) for name, (left, right) in WINDOWS_PS.items())
RESET_PLATEAU = (51.0e-12, 60.0e-12)
WRITE1_PLATEAU = (91.0e-12, 100.0e-12)
READ_PLATEAU = (111.0e-12, 120.0e-12)
READ_WINDOW = WINDOWS_S["READ"]
SCAN_WINDOW = (101.0e-12, 200.0e-12)
PLATEAU_TOLERANCE_A = 0.1e-6

sys.path.insert(0, str(REPO / "scripts"))
from bvmtools.compare import compare_series, exact_time_grid_identity  # noqa: E402
from bvmtools.deckqa import deck_qa  # noqa: E402
from bvmtools.kcl import kcl_window_metrics, linear_kcl_residual  # noqa: E402
from bvmtools.metrics import phase_area_window, peak_timing_metrics  # noqa: E402
from bvmtools.phase import TAU, continuous_unwrap, phase_window_metrics, window_indices  # noqa: E402
from bvmtools.raw import RawTrace, read_csv  # noqa: E402
from bvmtools.sfq import StrictLocalEventSpec, strict_event_list  # noqa: E402
from bvmtools.stimulus import validate_expected_plateau  # noqa: E402
from bvmtools.waveform import trapezoid_integral, waveform_metrics, waveform_window_metrics  # noqa: E402

sys.path.insert(0, str(EXP))
from generate_decks import required_probe_labels  # noqa: E402


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO.resolve()).as_posix()


def sig(trace: RawTrace, label: str) -> tuple[float, ...]:
    return trace.column(label)  # type: ignore[return-value]


def bvm_label(instance: int, prefix: str, kind: str = "I") -> str:
    return f"{kind}({prefix}|XBVM{instance})"


CURRENT_BRANCHES = OrderedDict(
    (
        ("JM1", "L_M1"),
        ("JM2", "L_M2"),
        ("LM3", "L_M3"),
        ("LPM", "L_PM"),
        ("RJM1", "R_JM1"),
        ("LS1", "L_S1"),
        ("LS2", "L_S2"),
        ("RS", "R_S"),
        ("LS3", "L_S3"),
        ("RSE", "R_SE"),
        ("LPSE", "L_PSE"),
        ("LPSL", "L_PSL"),
        ("RSL", "R_SL"),
        ("LSL", "L_SL"),
    )
)
VOLTAGE_BRANCHES = OrderedDict(
    (
        ("RJM1", "R_JM1"),
        ("LS1", "L_S1"),
        ("JS1", "B_JS1"),
        ("LS2", "L_S2"),
        ("JS2", "B_JS2"),
        ("RS", "R_S"),
        ("LS3", "L_S3"),
        ("RSE", "R_SE"),
        ("LPSE", "L_PSE"),
        ("LPSL", "L_PSL"),
        ("RSL", "R_SL"),
        ("LSL", "L_SL"),
    )
)
JJ_NAMES = ("JM1", "JM2", "JS1", "JS2")


def selected_indices(times: Sequence[float], bounds: tuple[float, float]) -> tuple[int, ...]:
    indices = window_indices(times, *bounds)
    if len(indices) < 2:
        raise RuntimeError(f"window has fewer than two samples: {bounds}")
    return indices


def metric(trace: RawTrace, label: str, bounds: tuple[float, float], unit: str) -> dict[str, object]:
    values = sig(trace, label)
    result = dict(waveform_window_metrics(trace.time, values, bounds, unit=unit))
    result["label"] = label
    result["raw_unit"] = "A" if unit == "A" else "V" if unit == "V" else "raw"
    result["peak_timing"] = dict(peak_timing_metrics(trace.time, values, bounds, unit=unit))
    return result


def phase_metric(trace: RawTrace, phase_label: str, voltage_label: str, bounds: tuple[float, float]) -> dict[str, object]:
    result = phase_area_window(
        trace.time,
        sig(trace, phase_label),
        sig(trace, voltage_label),
        bounds,
        voltage_to_phase_sign=1,
        reporting_direction=1,
        include_segments=False,
    )
    result["phase_label"] = phase_label
    result["voltage_label"] = voltage_label
    return result


def phase_turn_values(trace: RawTrace, label: str) -> tuple[float, ...]:
    return tuple(value / TAU for value in continuous_unwrap(sig(trace, label)))


def phase_delta_values(trace: RawTrace, baseline: RawTrace, label: str) -> tuple[float, ...]:
    left = phase_turn_values(trace, label)
    right = phase_turn_values(baseline, label)
    if trace.time != baseline.time:
        raise RuntimeError(f"phase delta grid mismatch for {label}")
    return tuple(a - b for a, b in zip(left, right))


def series_stats(times: Sequence[float], values: Sequence[float], bounds: tuple[float, float], unit: str) -> dict[str, object]:
    indices = selected_indices(times, bounds)
    t = [float(times[index]) for index in indices]
    y = [float(values[index]) for index in indices]
    # The shared waveform helper remains the arithmetic authority.  A raw
    # unit is used for already-normalized phase differences in turns.
    result = dict(waveform_window_metrics(t, y, (t[0], math.nextafter(t[-1], math.inf)), unit=unit))
    result["sample_count"] = len(y)
    result["window_first_s"] = t[0]
    result["window_last_sample_s"] = t[-1]
    result["peak_abs_value"] = max(abs(value) for value in y)
    peak_abs = max(range(len(y)), key=lambda index: abs(y[index]))
    result["peak_abs_time_s"] = t[peak_abs]
    return result


def compact_compare(time_a: Sequence[float], values_a: Sequence[float], time_b: Sequence[float], values_b: Sequence[float], *, unit: str, scale: float = 1.0) -> dict[str, object]:
    comparison = compare_series(
        time_a,
        values_a,
        time_b,
        values_b,
        interpolation=None,
        include_correlation=True,
    )
    comparison.pop("pointwise_difference", None)
    for key in ("max_abs_difference", "rms_difference", "p95_abs_difference"):
        comparison[key] = float(comparison[key]) * scale
    comparison["unit"] = unit
    comparison["difference_convention"] = "right_minus_left"
    return comparison


def relative_series(trace: RawTrace, label: str, bounds: tuple[float, float], *, phase: bool = False) -> tuple[tuple[float, ...], tuple[float, ...]]:
    indices = selected_indices(trace.time, bounds)
    first = indices[0]
    times = tuple(float(trace.time[index] - trace.time[first]) for index in indices)
    if phase:
        values_all = phase_turn_values(trace, label)
        values = tuple(float(values_all[index] - values_all[first]) for index in indices)
    else:
        values_all = sig(trace, label)
        values = tuple(float(values_all[index]) for index in indices)
    return times, values


def grid_record(trace: RawTrace) -> dict[str, object]:
    return {
        "sample_count": trace.sample_count,
        "start_ps": trace.time[0] * 1e12,
        "last_sample_ps": trace.time[-1] * 1e12,
        "dt_min_ps": min(trace.dt) * 1e12,
        "dt_max_ps": max(trace.dt) * 1e12,
        "uniform_exact": all(value == trace.dt[0] for value in trace.dt),
        "interpolation": "none",
    }


def protocol_record(trace: RawTrace) -> dict[str, object]:
    result: dict[str, object] = {"per_bvm": {}, "status": "PROTOCOL_VALID"}
    for instance in range(1, 5):
        wl, bl, se = (f"I(I_{name}{instance})" for name in ("WL", "BL", "SE"))
        reset = {
            wl: validate_expected_plateau(trace.time, sig(trace, wl), RESET_PLATEAU, -100e-6, tolerance=PLATEAU_TOLERANCE_A, unit="A"),
            bl: validate_expected_plateau(trace.time, sig(trace, bl), RESET_PLATEAU, -100e-6, tolerance=PLATEAU_TOLERANCE_A, unit="A"),
        }
        write1 = {
            wl: validate_expected_plateau(trace.time, sig(trace, wl), WRITE1_PLATEAU, 100e-6, tolerance=PLATEAU_TOLERANCE_A, unit="A"),
            bl: validate_expected_plateau(trace.time, sig(trace, bl), WRITE1_PLATEAU, 100e-6, tolerance=PLATEAU_TOLERANCE_A, unit="A"),
        }
        read_common_zero = {
            se: validate_expected_plateau(trace.time, sig(trace, se), READ_PLATEAU, 0.0, tolerance=PLATEAU_TOLERANCE_A, unit="A"),
            bl: validate_expected_plateau(trace.time, sig(trace, bl), READ_PLATEAU, 0.0, tolerance=PLATEAU_TOLERANCE_A, unit="A"),
        }
        # The actual selective-read WL/SE values are checked below from the
        # mask; this records the common BL=0 and inactive-source checks.
        noop = {
            name: metric(trace, label, (70e-12, 90e-12), "A")
            for name, label in (("WL", wl), ("BL", bl), ("SE", se))
        }
        result["per_bvm"][f"BVM{instance}"] = {  # type: ignore[index]
            "reset": reset,
            "write1": write1,
            "read_common_zero_check": read_common_zero,
            "noop_70_90": noop,
        }
    # Rewrite the intentionally mask-independent placeholder read check as a
    # zero check; the caller supplies active/inactive expected WL/SE values.
    result["status"] = "PROTOCOL_VALID" if all(
        all(item["status"] == "PASS" for item in result["per_bvm"][f"BVM{n}"]["reset"].values())  # type: ignore[index]
        and all(item["status"] == "PASS" for item in result["per_bvm"][f"BVM{n}"]["write1"].values())  # type: ignore[index]
        for n in range(1, 5)
    ) else "PROTOCOL_MISMATCH"
    return result


def selective_protocol_record(trace: RawTrace, mask: str) -> dict[str, object]:
    result = protocol_record(trace)
    for instance in range(1, 5):
        per = result["per_bvm"][f"BVM{instance}"]  # type: ignore[index]
        active = mask[instance - 1] == "1"
        wl = f"I(I_WL{instance})"
        bl = f"I(I_BL{instance})"
        se = f"I(I_SE{instance})"
        expected = 100e-6 if active else 0.0
        per["read"] = {  # type: ignore[index]
            wl: validate_expected_plateau(trace.time, sig(trace, wl), READ_PLATEAU, expected, tolerance=PLATEAU_TOLERANCE_A, unit="A"),
            se: validate_expected_plateau(trace.time, sig(trace, se), READ_PLATEAU, expected, tolerance=PLATEAU_TOLERANCE_A, unit="A"),
            bl: validate_expected_plateau(trace.time, sig(trace, bl), READ_PLATEAU, 0.0, tolerance=PLATEAU_TOLERANCE_A, unit="A"),
        }
    result["status"] = "PROTOCOL_VALID" if all(
        all(item["status"] == "PASS" for item in result["per_bvm"][f"BVM{n}"]["read"].values())  # type: ignore[index]
        for n in range(1, 5)
    ) and result["status"] == "PROTOCOL_VALID" else "PROTOCOL_MISMATCH"
    result["mask"] = mask
    result["semantics"] = "mask=1: WL+SE=+100 uA; mask=0: WL=SE=0; BL=0 for every READ"
    return result


def artifact_records(traces: Mapping[str, RawTrace]) -> dict[str, object]:
    required = tuple(required_probe_labels())
    per: dict[str, object] = {}
    for mask in MASKS:
        run_dir = EXP / "runs" / mask
        deck = run_dir / "deck.cir"
        raw = run_dir / "raw.csv"
        log = run_dir / "run.log"
        metadata_path = run_dir / "metadata.json"
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        trace = traces[mask]
        log_text = log.read_text(encoding="utf-8", errors="replace")
        qa = deck_qa(
            deck,
            log_text=log_text,
            expected_includes=("bvm_jm2_connected.cir", "BVMSim/BQ.cir", "BVMSim/library_josim/jtl2.cir"),
            expected_bvm_instances=4,
            expected_terminal_sensing_jj_count=12,
            expected_jtl_stages=6,
            expected_termination_ohm=10.0,
            expected_tran_timestep_ps=0.1,
            required_probes=required,
            raw_headers=trace.headers,
        )
        issues: list[str] = []
        if metadata.get("command", {}).get("exit_code") != 0:
            issues.append("SOLVER_EXIT_NONZERO")
        if metadata.get("artifact_status") != "EXECUTION_COMPLETE":
            issues.append("EXECUTION_INCOMPLETE")
        if metadata.get("hashes", {}).get("raw_sha256") != digest(raw):
            issues.append("RAW_HASH_MISMATCH")
        if metadata.get("hashes", {}).get("deck_sha256") != digest(deck):
            issues.append("DECK_HASH_MISMATCH")
        if metadata.get("hashes", {}).get("log_sha256") != digest(log):
            issues.append("LOG_HASH_MISMATCH")
        if metadata.get("model_warning_detected") or re.search(r"Missing model:|Using default model", log_text, re.I):
            issues.append("MODEL_WARNING")
        if trace.duplicate_columns:
            issues.append("DUPLICATE_RAW_HEADER")
        if qa["status"] != "ARTIFACT_VALID":
            issues.append("DECK_OR_RAW_QA")
        if "circuits/bvm/bvm_cell.cir" in deck.read_text(encoding="utf-8"):
            issues.append("CANONICAL_BVM_USED")
        per[mask] = {
            "status": "ARTIFACT_VALID" if not issues else "ARTIFACT_INVALID",
            "issues": issues,
            "deck": rel(deck),
            "raw": rel(raw),
            "metadata": rel(metadata_path),
            "deck_sha256": digest(deck),
            "raw_sha256": digest(raw),
            "log_sha256": digest(log),
            "raw_qa": trace.qa(),
            "deck_qa": qa,
        }
    return {
        "status": "ARTIFACT_VALID" if all(item["status"] == "ARTIFACT_VALID" for item in per.values()) else "ARTIFACT_INVALID",
        "per_mask": per,
        "raw_policy": "one immutable raw.csv per mask; no shared mutable authority",
        "source_authority": "historical BVMSim JM2-connected variant; canonical BVM excluded",
    }


def state_closure(traces: Mapping[str, RawTrace]) -> dict[str, object]:
    output: dict[str, object] = {"per_mask": {}, "criterion": "descriptive only; abs WRITE1 phase displacement >=0.25 turns and SETTLE->TAIL mean shift within observed p2p"}
    for mask in MASKS:
        trace = traces[mask]
        per_bvm: dict[str, object] = {}
        for instance in range(1, 5):
            jj: dict[str, object] = {}
            for junction in ("JM1", "JM2"):
                p = bvm_label(instance, f"B_{junction}", "P")
                v = bvm_label(instance, f"B_{junction}", "V")
                write = phase_metric(trace, p, v, (90e-12, 101e-12))
                settle = phase_window_metrics(trace.time, sig(trace, p), WINDOWS_S["SETTLE_1111"])
                tail = phase_window_metrics(trace.time, sig(trace, p), WINDOWS_S["TAIL"])
                shift = float(tail["mean_turns"]) - float(settle["mean_turns"])
                noise = max(float(settle["p2p_turns"]), float(tail["p2p_turns"]))
                stable = abs(shift) <= noise + 1e-15
                write_delta = float(write["phase_delta_turns"])
                jj[junction] = {
                    "write1_phase_area": write,
                    "settle_phase": settle,
                    "tail_phase": tail,
                    "settle_to_tail_mean_shift_turns": shift,
                    "observed_noise_bound_turns": noise,
                    "retention_stable_descriptive": stable,
                    "write1_abs_delta_turns": abs(write_delta),
                    "write1_activity_marker": abs(write_delta) >= 0.25,
                }
            eligible = all(
                bool(jj[junction]["retention_stable_descriptive"])
                and bool(jj[junction]["write1_activity_marker"])
                for junction in ("JM1", "JM2")
            )
            per_bvm[f"BVM{instance}"] = {
                "commanded_stored_state": "1111",
                "JM1_JM2": jj,
                "stored_1111_observed_descriptive": eligible,
                "warning": "not a forced state label; this is a task-local phase/area observation",
            }
        output["per_mask"][mask] = per_bvm  # type: ignore[index]
    output["all_four_observed_for_every_mask"] = all(
        record["stored_1111_observed_descriptive"]  # type: ignore[index]
        for per_mask in output["per_mask"].values()  # type: ignore[union-attr]
        for record in per_mask.values()
    )
    return output


def inactive_signal_specs(instance: int) -> OrderedDict[str, tuple[str, str]]:
    return OrderedDict(
        (
            ("RSL", (bvm_label(instance, "R_SL"), "A")),
            ("LSL", (bvm_label(instance, "L_SL"), "A")),
            ("RS", (bvm_label(instance, "R_S"), "A")),
            ("LS3", (bvm_label(instance, "L_S3"), "A")),
            ("LM3", (bvm_label(instance, "L_M3"), "A")),
            ("LM1", (bvm_label(instance, "L_M1"), "A")),
            ("LM2", (bvm_label(instance, "L_M2"), "A")),
            ("LPM", (bvm_label(instance, "L_PM"), "A")),
            ("JS1", (bvm_label(instance, "B_JS1", "P"), "turns")),
            ("JS2", (bvm_label(instance, "B_JS2", "P"), "turns")),
            ("JM1", (bvm_label(instance, "B_JM1", "P"), "turns")),
            ("JM2", (bvm_label(instance, "B_JM2", "P"), "turns")),
        )
    )


def inactive_isolation(traces: Mapping[str, RawTrace]) -> dict[str, object]:
    output: dict[str, object] = {"baseline": "same-position 0000 stored-1111 no-read run", "per_one_hot": {}}
    baseline = traces["0000"]
    for mask in ONE_HOT:
        one = traces[mask]
        active = next(index for index, bit in enumerate(mask, start=1) if bit == "1")
        victims: dict[str, object] = {}
        for victim in range(1, 5):
            if victim == active:
                continue
            signals: dict[str, object] = {}
            for name, (label, unit) in inactive_signal_specs(victim).items():
                if unit == "turns":
                    values = phase_delta_values(one, baseline, label)
                    base_values = phase_turn_values(baseline, label)
                    one_values = phase_turn_values(one, label)
                    delta_label_unit = "turns"
                    scale = 1.0
                else:
                    if one.time != baseline.time:
                        raise RuntimeError(f"inactive delta grid mismatch: {mask}/{victim}/{label}")
                    one_values = sig(one, label)
                    base_values = sig(baseline, label)
                    values = tuple(a - b for a, b in zip(one_values, base_values))
                    delta_label_unit = "uA"
                    scale = 1e6
                signals[name] = {
                    "label": label,
                    "unit": delta_label_unit,
                    "baseline": metric(baseline, label, READ_WINDOW, "A" if unit == "A" else "raw"),
                    "one_hot": metric(one, label, READ_WINDOW, "A" if unit == "A" else "raw"),
                    "delta": series_stats(one.time, values, READ_WINDOW, "A" if unit == "A" else "raw"),
                    "delta_max_abs_display": series_stats(one.time, values, READ_WINDOW, "A" if unit == "A" else "raw")["max_abs"],
                }
            victims[f"BVM{victim}"] = {"commanded_read_bit": 0, "signals": signals}
        output["per_one_hot"][mask] = {  # type: ignore[index]
            "active_bvm": f"BVM{active}",
            "inactive_victims": victims,
            "interpretation": "READ-associated difference against same-position 0000; not a unique causal decomposition",
        }
    return output


def active_vs_single(traces: Mapping[str, RawTrace]) -> dict[str, object]:
    if not SINGLE.is_file():
        return {"status": "MISSING_SINGLE_REFERENCE", "path": rel(SINGLE)}
    single = read_csv(SINGLE)
    specs = OrderedDict(
        (
            ("LM3", ("I(L_M3|XBVM{n})", "I(L_M3|XBVM1)", "uA", 1e6, False)),
            ("JS1", ("P(B_JS1|XBVM{n})", "P(B_JS1|XBVM1)", "turns", 1.0, True)),
            ("JS2", ("P(B_JS2|XBVM{n})", "P(B_JS2|XBVM1)", "turns", 1.0, True)),
            ("RS", ("I(R_S|XBVM{n})", "I(R_S|XBVM1)", "uA", 1e6, False)),
            ("LS3", ("I(L_S3|XBVM{n})", "I(L_S3|XBVM1)", "uA", 1e6, False)),
            ("RSL", ("I(R_SL|XBVM{n})", "I(R_SL|XBVM1)", "uA", 1e6, False)),
            ("LSL", ("I(L_SL|XBVM{n})", "I(L_SL|XBVM1)", "uA", 1e6, False)),
            ("VSL", ("V(SL{n})", "V(SL1)", "mV", 1e3, False)),
            ("LIN", ("I(LIN|XBQ1)", "I(LIN|XBQ1)", "uA", 1e6, False)),
            ("QBIN", ("V(QBIN)", "V(QBIN)", "mV", 1e3, False)),
        )
    )
    result: dict[str, object] = {
        "status": "VALID",
        "array_read_window_ps": [110.0, 170.0],
        "single_reference_read_window_ps": [70.0, 130.0],
        "alignment": "relative onset, exact sample index, no interpolation",
        "history_limitation": "single S1 is an isolated historical reference with a different absolute stimulus schedule; comparison is waveform-shape/scale context, not identical protocol equivalence",
        "per_one_hot": {},
    }
    for mask in ONE_HOT:
        array = traces[mask]
        active = next(index for index, bit in enumerate(mask, start=1) if bit == "1")
        entries: dict[str, object] = {}
        for name, (array_pattern, single_label, unit, scale, phase) in specs.items():
            array_label = array_pattern.format(n=active)
            ta, va = relative_series(array, array_label, READ_WINDOW, phase=phase)
            ts, vs = relative_series(single, single_label, (70e-12, 130e-12), phase=phase)
            if len(ta) != len(ts):
                entries[name] = {"status": "SAMPLE_COUNT_MISMATCH", "array_samples": len(ta), "single_samples": len(ts)}
            else:
                array_dt = tuple(ta[index + 1] - ta[index] for index in range(len(ta) - 1))
                single_dt = tuple(ts[index + 1] - ts[index] for index in range(len(ts) - 1))
                max_dt_difference = max(
                    (abs(left - right) for left, right in zip(array_dt, single_dt)),
                    default=0.0,
                )
                # Pair equal sample indices.  The comparison is deliberately
                # performed on a synthetic sample-index axis: this is not
                # interpolation, and it avoids treating binary floating-point
                # offset representation as a physical grid change.
                index_axis = tuple(float(index) for index in range(len(ta)))
                entries[name] = {
                    "array_label": array_label,
                    "single_label": single_label,
                    "phase_centered": phase,
                    "alignment": "same relative READ sample index; no interpolation",
                    "array_samples": len(ta),
                    "single_samples": len(ts),
                    "max_abs_dt_difference_s": max_dt_difference,
                    "exact_relative_time_grid": exact_time_grid_identity(ta, ts),
                    "comparison": compact_compare(index_axis, va, index_axis, vs, unit=unit, scale=scale),
                }
        result["per_one_hot"][mask] = {"active_bvm": f"BVM{active}", "signals": entries}  # type: ignore[index]
    return result


def one_hot_position(traces: Mapping[str, RawTrace]) -> dict[str, object]:
    baseline = traces["0000"]
    result: dict[str, object] = {"per_one_hot": {}, "signals": ("V(QBIN)", "I(LIN|XBQ1)", "active RSL", "active LSL", "active V(SL)")}
    for mask in ONE_HOT:
        active = next(index for index, bit in enumerate(mask, start=1) if bit == "1")
        array = traces[mask]
        items: dict[str, object] = {}
        for name, label, unit in (
            ("QBIN", "V(QBIN)", "V"),
            ("LIN", "I(LIN|XBQ1)", "A"),
            ("RSL", bvm_label(active, "R_SL"), "A"),
            ("LSL", bvm_label(active, "L_SL"), "A"),
            ("VSL", f"V(SL{active})", "V"),
        ):
            items[name] = {
                "label": label,
                "raw_one_hot": metric(array, label, READ_WINDOW, unit),
                "delta_vs_0000": {
                    "unit": "uA" if unit == "A" else "mV",
                    "stats": series_stats(
                        array.time,
                        tuple(a - b for a, b in zip(sig(array, label), sig(baseline, label))),
                        READ_WINDOW,
                        unit,
                    ),
                },
            }
        result["per_one_hot"][mask] = {"active_bvm": f"BVM{active}", "signals": items}  # type: ignore[index]
    return result


def superposition_summary(time: Sequence[float], actual: Sequence[float], predicted: Sequence[float], bounds: tuple[float, float], unit: str) -> dict[str, object]:
    indices = selected_indices(time, bounds)
    t = [float(time[index]) for index in indices]
    a = [float(actual[index]) for index in indices]
    p = [float(predicted[index]) for index in indices]
    residual = [x - y for x, y in zip(a, p)]
    display_scale = 1e6 if unit == "A" else 1e3 if unit == "V" else 1.0
    area_scale = 1e18 if unit == "A" else 1e15 if unit == "V" else 1.0
    comparison = compact_compare(t, p, t, a, unit=("uA" if unit == "A" else "mV" if unit == "V" else unit), scale=display_scale)
    actual_rms = math.sqrt(sum(x * x for x in a) / len(a))
    residual_rms = math.sqrt(sum(x * x for x in residual) / len(residual))
    ai = max(range(len(a)), key=lambda i: abs(a[i]))
    pi = max(range(len(p)), key=lambda i: abs(p[i]))
    residual_stats = dict(waveform_window_metrics(t, residual, (t[0], math.nextafter(t[-1], math.inf)), unit=unit))
    return {
        "difference_convention": "actual_delta_minus_one_hot_predicted_delta",
        "unit": "uA" if unit == "A" else "mV" if unit == "V" else unit,
        "actual_delta": dict(waveform_window_metrics(t, a, (t[0], math.nextafter(t[-1], math.inf)), unit=unit)),
        "predicted_delta": dict(waveform_window_metrics(t, p, (t[0], math.nextafter(t[-1], math.inf)), unit=unit)),
        "residual": residual_stats,
        "comparison_actual_vs_predicted": comparison,
        "signed_integral_residual_display": trapezoid_integral(residual, t) * area_scale,
        "signed_integral_unit": "uA*ps" if unit == "A" else "mV*ps" if unit == "V" else "raw*s",
        "peak_time_actual_ps": t[ai] * 1e12,
        "peak_time_predicted_ps": t[pi] * 1e12,
        "peak_time_difference_ps": (t[ai] - t[pi]) * 1e12,
        "normalized_rms_error": residual_rms / actual_rms if actual_rms else None,
        "correlation": comparison.get("correlation"),
        "sample_count": len(t),
        "interpolation": "none",
    }


def additivity(traces: Mapping[str, RawTrace]) -> dict[str, object]:
    baseline = traces["0000"]
    specs: list[tuple[str, str, str]] = [
        ("QB_LIN", "I(LIN|XBQ1)", "A"),
        ("QB_QBIN", "V(QBIN)", "V"),
        ("BVM1_RSL", bvm_label(1, "R_SL"), "A"),
        ("BVM2_RSL", bvm_label(2, "R_SL"), "A"),
        ("BVM3_RSL", bvm_label(3, "R_SL"), "A"),
        ("BVM4_RSL", bvm_label(4, "R_SL"), "A"),
        ("BVM1_LSL", bvm_label(1, "L_SL"), "A"),
        ("BVM2_LSL", bvm_label(2, "L_SL"), "A"),
        ("BVM3_LSL", bvm_label(3, "L_SL"), "A"),
        ("BVM4_LSL", bvm_label(4, "L_SL"), "A"),
        ("BVM1_VSL", "V(SL1)", "V"),
        ("BVM2_VSL", "V(SL2)", "V"),
        ("BVM3_VSL", "V(SL3)", "V"),
        ("BVM4_VSL", "V(SL4)", "V"),
    ]
    result: dict[str, object] = {"formula": "Delta_X(mask)=X(mask)-X(0000); predicted=sum(Delta_X(one-hot)); residual=actual-predicted", "forward": {}, "reverse": {}}
    delta_by_label_mask: dict[tuple[str, str], tuple[float, ...]] = {}
    for mask in ONE_HOT:
        trace = traces[mask]
        for _, label, _ in specs:
            delta_by_label_mask[(mask, label)] = tuple(a - b for a, b in zip(sig(trace, label), sig(baseline, label)))

    for direction, masks in (("forward", FORWARD), ("reverse", REVERSE)):
        for mask in masks:
            trace = traces[mask]
            active_onehots = [ONE_HOT_BY_INSTANCE[index] for index, bit in enumerate(mask, start=1) if bit == "1"]
            entries: dict[str, object] = {}
            for name, label, unit in specs:
                actual = tuple(a - b for a, b in zip(sig(trace, label), sig(baseline, label)))
                predicted = tuple(
                    sum(delta_by_label_mask[(onehot, label)][i] for onehot in active_onehots)
                    for i in range(len(actual))
                )
                entries[name] = {
                    "label": label,
                    "active_one_hot_masks": active_onehots,
                    "summary": superposition_summary(trace.time, actual, predicted, READ_WINDOW, unit),
                }
            result[direction][mask] = entries  # type: ignore[index]
    return result


def kcl_record(traces: Mapping[str, RawTrace]) -> dict[str, object]:
    equations = OrderedDict(
        (
            ("JM1_shunt", (("B_JM1", 1.0), ("R_JM1", 1.0), ("L_M1", -1.0))),
            ("SE_RLOOP", (("B_JS1", 1.0), ("L_PSE", 1.0), ("R_S", -1.0), ("L_S3", -1.0))),
            ("RLOOP_OUTPUT", (("R_S", 1.0), ("L_S3", 1.0), ("B_JS2", 1.0), ("L_PSL", -1.0))),
            ("SL_SERIES_1", (("L_PSL", 1.0), ("R_SL", -1.0))),
            ("SL_SERIES_2", (("R_SL", 1.0), ("L_SL", -1.0))),
        )
    )
    result: dict[str, object] = {
        "orientation": "positive current is from first netlist node to second",
        "equations": {name: " + ".join(f"{sign:+g} I({branch})" for branch, sign in terms) for name, terms in equations.items()},
        "per_mask": {},
    }
    for mask in MASKS:
        trace = traces[mask]
        per_bvm: dict[str, object] = {}
        for instance in range(1, 5):
            branch_values = {
                branch: sig(trace, bvm_label(instance, branch))
                for branch in {branch for terms in equations.values() for branch, _ in terms}
            }
            per_equation: dict[str, object] = {}
            for name, terms in equations.items():
                coefficients = {bvm_label(instance, branch): sign for branch, sign in terms}
                residual = linear_kcl_residual(
                    {bvm_label(instance, branch): branch_values[branch] for branch, _ in terms},
                    coefficients,
                )
                per_equation[name] = {
                    "coefficients": coefficients,
                    "READ": kcl_window_metrics(trace.time, residual, READ_WINDOW, unit="A"),
                    "SETTLE_1111": kcl_window_metrics(trace.time, residual, WINDOWS_S["SETTLE_1111"], unit="A"),
                }
            per_bvm[f"BVM{instance}"] = per_equation
        result["per_mask"][mask] = per_bvm  # type: ignore[index]
    return result


def rsl_record(traces: Mapping[str, RawTrace]) -> dict[str, object]:
    result: dict[str, object] = {"per_one_hot": {}, "power_definition": "P_RSL(t)=V(R_SL|XBVMn)*I(R_SL|XBVMn); E=integral(P_RSL dt); descriptive only"}
    for mask in ONE_HOT:
        trace = traces[mask]
        per_bvm: dict[str, object] = {}
        for instance in range(1, 5):
            current = sig(trace, bvm_label(instance, "R_SL"))
            voltage = sig(trace, bvm_label(instance, "R_SL", "V"))
            indices = selected_indices(trace.time, READ_WINDOW)
            t = [trace.time[i] for i in indices]
            i_values = [current[i] for i in indices]
            v_values = [voltage[i] for i in indices]
            power = [i * v for i, v in zip(i_values, v_values)]
            p_metrics = waveform_metrics(t, power)
            per_bvm[f"BVM{instance}"] = {
                "current": metric(trace, bvm_label(instance, "R_SL"), READ_WINDOW, "A"),
                "voltage": metric(trace, bvm_label(instance, "R_SL", "V"), READ_WINDOW, "V"),
                "power_W": {
                    "mean": p_metrics["mean"],
                    "minimum": p_metrics["minimum"],
                    "maximum": p_metrics["maximum"],
                    "max_abs": p_metrics["max_abs"],
                    "signed_integral_Ws": trapezoid_integral(power, t),
                    "energy_pJ_signed": trapezoid_integral(power, t) * 1e12,
                },
            }
        result["per_one_hot"][mask] = per_bvm  # type: ignore[index]
    return result


def rs_ls3_record(traces: Mapping[str, RawTrace]) -> dict[str, object]:
    result: dict[str, object] = {"per_one_hot": {}, "fraction_definition": "I(RS)/(I(RS)+I(LS3)) only where |sum|>1 uA; descriptive ratio"}
    for mask in ONE_HOT:
        trace = traces[mask]
        per_bvm: dict[str, object] = {}
        for instance in range(1, 5):
            irs = sig(trace, bvm_label(instance, "R_S"))
            ils3 = sig(trace, bvm_label(instance, "L_S3"))
            vrs = sig(trace, bvm_label(instance, "R_S", "V"))
            vls3 = sig(trace, bvm_label(instance, "L_S3", "V"))
            indices = selected_indices(trace.time, READ_WINDOW)
            fractions = []
            for index in indices:
                total = irs[index] + ils3[index]
                if abs(total) > 1e-6:
                    fractions.append(irs[index] / total)
            per_bvm[f"BVM{instance}"] = {
                "RS_current": metric(trace, bvm_label(instance, "R_S"), READ_WINDOW, "A"),
                "LS3_current": metric(trace, bvm_label(instance, "L_S3"), READ_WINDOW, "A"),
                "RS_voltage": metric(trace, bvm_label(instance, "R_S", "V"), READ_WINDOW, "V"),
                "LS3_voltage": metric(trace, bvm_label(instance, "L_S3", "V"), READ_WINDOW, "V"),
                "current_sum": series_stats(trace.time, tuple(a + b for a, b in zip(irs, ils3)), READ_WINDOW, "A"),
                "RS_fraction": {
                    "sample_count_above_1uA": len(fractions),
                    "minimum": min(fractions) if fractions else None,
                    "maximum": max(fractions) if fractions else None,
                    "mean": sum(fractions) / len(fractions) if fractions else None,
                },
            }
        result["per_one_hot"][mask] = per_bvm  # type: ignore[index]
    return result


def strict_spec(mask: str, phase_label: str, voltage_label: str, raw_hash: str) -> StrictLocalEventSpec:
    return StrictLocalEventSpec(
        id="ALL_ONE_SELECTIVE_READ_LOCAL_EVENT_DIAGNOSTIC_V1",
        scope="task-local",
        status="POST_HOC_EXPLORATORY",
        provenance_status="RECORDED",
        mapping_status="EXACT_RAW_LABEL_SAME_JJ",
        phase_column=phase_label,
        voltage_column=voltage_label,
        branch_endpoints="same JJ phase/voltage branch",
        voltage_to_phase_sign=1,
        reporting_direction=1,
        run_id=mask,
        window_id="READ",
        raw_sha256=raw_hash,
        metric_spec={"path": rel(METRIC_SPEC), "version": "2.0.0", "sha256": digest(METRIC_SPEC)},
        tolerance={
            "id": "task-local-diagnostic",
            "scope": "task-local diagnostic only",
            "evidence": "same JJ phase-area plus segmentation",
            "status": "POST_HOC_EXPLORATORY",
            "phase_area_residual_abs_floor_turns": 0.05,
            "phase_area_residual_relative": 0.10,
            "complete_min_turns": 1.0,
            "clean_upper_turns": 1.15,
            "post_range_max_turns": 1.0,
            "post_tail_p2p_max_turns": 0.25,
        },
        compatibility_profile="STRICT_EVENT_ANCHOR_COMPATIBILITY_V1",
    )


def strict_compact(trace: RawTrace, mask: str, phase_label: str, voltage_label: str, raw_hash: str) -> dict[str, object]:
    try:
        result = strict_event_list(
            trace.time,
            sig(trace, phase_label),
            sig(trace, voltage_label),
            event_window_s=READ_WINDOW,
            scan_window_s=SCAN_WINDOW,
            retrap_max_p2p_turns=0.25,
            spec=strict_spec(mask, phase_label, voltage_label, raw_hash),
        )
        return {
            "status": "DIAGNOSTIC_VALID",
            "mode": result["mode"],
            "complete_segment_count": result["complete_segment_count"],
            "clean_separated_event_count": result["clean_separated_event_count"],
            "largest_segment_turns": result["largest_segment_turns"],
            "any_segment_spans_over_1_15_turns": result["any_segment_spans_over_1_15_turns"],
            "continuous_multi_turn_running": result["continuous_multi_turn_running"],
            "complete_event_onset_times_ps": result["complete_event_onset_times_ps"],
            "clean_event_onset_times_ps": result["clean_event_onset_times_ps"],
            "clean_event_directions": result["clean_event_directions"],
            "claim_ceiling": "local junction diagnostic only; not a downstream transport count",
        }
    except Exception as exc:
        return {"status": "DIAGNOSTIC_ERROR", "error": str(exc), "claim_ceiling": "no event interpretation"}


def qb_jtl_secondary(traces: Mapping[str, RawTrace]) -> dict[str, object]:
    result: dict[str, object] = {"per_mask": {}, "warning": "phase/area and strict lists are secondary local diagnostics; not SFQ counts"}
    for mask in MASKS:
        trace = traces[mask]
        raw_hash = digest(EXP / "runs" / mask / "raw.csv")
        bj2 = phase_metric(trace, "P(BJ2|XBQ1)", "V(BJ2|XBQ1)", READ_WINDOW)
        jtl6 = phase_metric(trace, "P(B02|XJTL1_6)", "V(B02|XJTL1_6)", READ_WINDOW)
        result["per_mask"][mask] = {  # type: ignore[index]
            "QB_BJ2_same_jj_phase_area": bj2,
            "QB_BJ2_strict_local_diagnostic": strict_compact(trace, mask, "P(BJ2|XBQ1)", "V(BJ2|XBQ1)", raw_hash),
            "JTL6_B02_same_jj_phase_area": jtl6,
            "JTL6_B02_strict_local_diagnostic": strict_compact(trace, mask, "P(B02|XJTL1_6)", "V(B02|XJTL1_6)", raw_hash),
            "QB_input_output": {
                "I(LIN|XBQ1)": metric(trace, "I(LIN|XBQ1)", READ_WINDOW, "A"),
                "V(QBIN)": metric(trace, "V(QBIN)", READ_WINDOW, "V"),
                "V(QBOUT)": metric(trace, "V(QBOUT)", READ_WINDOW, "V"),
            },
        }
    return result


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def fmt(value: object, digits: int = 5) -> str:
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "是" if value else "否"
    if isinstance(value, (int, float)):
        return f"{float(value):.{digits}g}"
    return str(value)


def report(metrics: Mapping[str, object]) -> str:
    artifacts = metrics["artifact_qa"]
    closure = metrics["state_closure"]
    lines = [
        "# ALL-ONE SELECTIVE-READ / ADDITIVITY / ISOLATION Quick",
        "",
        "## 首要问题",
        "",
        "本轮优先检查四颗 historical JM2-connected BVM 是否在共享 RSL/SL 上表现为相对独立的 unit-current 源：",
        "(1) active BVM 与 isolated single reference；(2) inactive BVM 与同位置 0000；(3) multi-active 实际响应与 one-hot 叠加预测。最终 QB/JTL 只作次级诊断。",
        "",
        "## 边界与协议",
        "",
        "每个 mask 独立运行；四颗 BVM 均先执行 WRITE0，再执行统一 WL+BL=+100 uA 的 all-one WRITE1，之后只在 READ 的 WL+SE 上施加 mask。mask 位序为 `b3b2b1b0 -> BVM1/BVM2/BVM3/BVM4`。70--90 ps 是全零 no-op，不是 READ。使用 historical BVMSim JM2-connected BVM、原始 BVMSim QB、六级 JTL、0.1 ps 步长；canonical BVM 未使用。",
        "",
        f"Artifact QA：`{artifacts['status']}`；state closure 是描述性检查，四颗在所有 mask 的 task-local stored-1111 观察为 `{closure['all_four_observed_for_every_mask']}`。这两个字段都不等于物理功能 PASS。",
        "",
        "## 1. Active BVM vs isolated single reference",
        "",
        "array READ `[110,170)` ps 与 previous single S1 `[70,130)` ps 按 READ onset 的相对采样索引对齐，不插值。single 的绝对 stimulus schedule 不同，因此这里只能作 branch waveform/scale context，不能称为同协议等价。详细数值在 `metrics.json` 的 `active_vs_single`。",
        "",
        "| one-hot | active BVM | LIN max abs (array vs single diff) | QBIN max abs diff | RSL max abs diff | LSL max abs diff |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for mask in ONE_HOT:
        active = next(index for index, bit in enumerate(mask, start=1) if bit == "1")
        item = metrics["active_vs_single"]["per_one_hot"][mask]["signals"]  # type: ignore[index]
        def md(name: str) -> object:
            value = item[name]
            return value.get("comparison", {}).get("max_abs_difference") if isinstance(value, dict) else None
        lines.append(f"| {mask} | BVM{active} | {fmt(md('LIN'))} uA | {fmt(md('QBIN'))} mV | {fmt(md('RSL'))} uA | {fmt(md('LSL'))} uA |")

    lines.extend([
        "",
        "## 2. Inactive BVM vs 0000",
        "",
        "以下是 one-hot active READ 下每个 inactive victim 的 `mask - 0000`。它回答的是 stored-1111、commanded-0 BVM 是否仍离开 0000；不是把 victim 响应归因给单一耦合路径。",
        "",
        "| active mask | inactive victim | Delta RSL max abs (uA) | Delta LSL max abs (uA) | Delta RS max abs (uA) | Delta LS3 max abs (uA) | Delta JS1 max abs (turns) | Delta JS2 max abs (turns) |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ])
    for mask in ONE_HOT:
        victims = metrics["inactive_isolation"]["per_one_hot"][mask]["inactive_victims"]  # type: ignore[index]
        for victim, record in victims.items():
            signals = record["signals"]
            vals = [signals[name]["delta_max_abs_display"] for name in ("RSL", "LSL", "RS", "LS3", "JS1", "JS2")]
            lines.append(f"| {mask} | {victim} | {fmt(vals[0])} | {fmt(vals[1])} | {fmt(vals[2])} | {fmt(vals[3])} | {fmt(vals[4])} | {fmt(vals[5])} |")

    lines.extend([
        "",
        "## 3. Multi-active actual vs one-hot superposition",
        "",
        "`Delta_X(mask)=X(mask)-X(0000)`；`Delta_X_pred=sum(Delta_X(one-hot))`；残差为 actual-predicted。没有预设 5%/10% 合格阈值，保留 max abs、RMS、signed integral、peak-time difference、normalized RMS 和 correlation。",
        "",
        "| direction | mask | LIN residual max abs (uA) | LIN normalized RMS | max per-BVM LSL residual (uA) | QBIN residual max abs (mV) | QBIN normalized RMS |",
        "|---|---|---:|---:|---:|---:|---:|",
    ])
    for direction in ("forward", "reverse"):
        for mask in (FORWARD if direction == "forward" else REVERSE):
            entry = metrics["additivity"][direction][mask]  # type: ignore[index]
            lin = entry["QB_LIN"]["summary"]
            qbin = entry["QB_QBIN"]["summary"]
            lsl_max = max(entry[f"BVM{instance}_LSL"]["summary"]["residual"]["max_abs"] for instance in range(1, 5))
            lines.append(f"| {direction} | {mask} | {fmt(lin['residual']['max_abs'])} | {fmt(lin['normalized_rms_error'])} | {fmt(lsl_max)} | {fmt(qbin['residual']['max_abs'])} | {fmt(qbin['normalized_rms_error'])} |")

    lines.extend([
        "",
        "## 4. 有界结论（仅限本 fixture）",
        "",
        "基于上述三组优先证据，本轮不支持把四颗 BVM 描述为在当前共享 RSL/SL fixture 中提供相对独立、可近似线性叠加的 unit-current 源。",
        "",
        "- **Observed:** one-hot active 响应随位置明显变化；array one-hot 与 isolated single 的 branch waveform 不能视为同协议等价。",
        "- **Observed:** 每个 one-hot run 中，三个 commanded-0、但先前经过 all-one WRITE1 的 victim 都相对 0000 出现非零 RSL/LSL；差异还出现在 RS、LS3、LM3 以及 JM1/JM2 phase probes。",
        "- **Observed:** multi-active 实际波形与 one-hot superposition 的 LIN、每路 LSL 和 QBIN 残差达到事件/波形尺度；因此当前数据不支持 near-linear accumulation。",
        "- **Caveat:** task-local 的 all-one stored-1111 closure 没有被四颗 BVM 全部确认：JM1 WRITE1 约为 2 turns，但 JM2 约为 0.124 turns，低于本轮描述性 0.25-turn marker。因而不能把所有 victim 的小响应简单表述为完整存储态下的隔离失败，也不能据此否定所有可能的其他协议。",
        "- **Inference:** 在本固定历史模型、固定偏置、固定步长和固定拓扑下，证据更接近 `cross-coupling/back-action + position-dependent response + non-additive accumulation`；耦合的具体物理路径仍是 Unknown。",
        "",
        "## 5. RSL / RS||LS3 / KCL",
        "",
        "RSL 的 `V*I` 和积分能量、RS/LS3 的支路电流分配以及五组 BVM KCL 只用于验证方向、层级和 current partition；它们不是独立性 gate。完整结果见 `metrics.json`。",
        "",
        "## 6. QB/JTL 次级诊断",
        "",
        "BJ2 与 JTL6 B02 保存同 JJ phase/voltage-area 与 shared strict event-list 诊断。phase turns、whole-window voltage area 和 local segment 数均不直接等于 SFQ received count。",
        "",
        "| mask | BJ2 READ phase delta (turns) | BJ2 strict clean events (diagnostic) | JTL6 B02 phase delta (turns) | JTL6 B02 strict clean events (diagnostic) |",
        "|---|---:|---:|---:|---:|",
    ])
    for mask in MASKS:
        item = metrics["qb_jtl_secondary"]["per_mask"][mask]  # type: ignore[index]
        lines.append(
            f"| {mask} | {fmt(item['QB_BJ2_same_jj_phase_area']['phase_delta_turns'])} | {fmt(item['QB_BJ2_strict_local_diagnostic'].get('clean_separated_event_count'))} | {fmt(item['JTL6_B02_same_jj_phase_area']['phase_delta_turns'])} | {fmt(item['JTL6_B02_strict_local_diagnostic'].get('clean_separated_event_count'))} |"
        )

    lines.extend([
        "",
        "## 7. 证据分层",
        "",
        "**Observed:** raw 中的四路控制、四个 hierarchical BVM 的直接 branch P/V/I、BVMout、QB 和六级 JTL 探针；10 个 mask 各有独立 deck/raw/log/metadata。",
        "",
        "**Derived:** 同一 raw 网格上的 one-hot-vs-0000 差分、one-hot 叠加预测、残差统计、RSL 功率/能量、RS||LS3 分配和 KCL residual。P 原始单位是 rad；只有明确转换后的字段才是 continuous phase turns。",
        "",
        "**Inference:** 若 inactive victim 的 Delta RSL/LSL/RS/LS3/JS 或 storage probe 显著非零，则说明当前 fixture 中存在 READ-associated cross-coupling；若 multi-active residual 相对 one-hot 叠加不小，则不能把共享 SL 解释为近似线性累加。active-vs-single 只能作为 bounded contextual comparison。",
        "",
        "**Unknown:** 本轮不能证明论文机制、普适 RSL isolation、unit current 的工艺独立性、canonical BVM 兼容性、硬件行为或系统 QB 逻辑正确性；也没有做参数、bias、timestep、T1 或完整 16-state matrix。",
        "",
        "## 8. 文件与 gate",
        "",
        "主数据：`analysis/metrics.json`；独立复算：`analysis/independent_check.json`；图索引：`plots/RESULT_OVERVIEW.html`。本轮结束后 gate 必须保持 `AWAITING_USER_REVIEW`、`user_reviewed: false`、`next_step_authorized: false`，不自动启动后续实验。",
        "",
        "当前 primary classification 不由 QB 输出数量决定，而由上述三组 array evidence 是否支持相对独立/近似 additivity 决定；在人工审阅前不升级为 PASS/FAIL 或论文结论。",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    traces = OrderedDict((mask, read_csv(EXP / "runs" / mask / "raw.csv")) for mask in MASKS)
    grid_identity = {
        mask: exact_time_grid_identity(traces["0000"].time, traces[mask].time)
        for mask in MASKS
    }
    if not all(grid_identity.values()):
        raise RuntimeError(f"array time-grid mismatch: {grid_identity}")
    artifacts = artifact_records(traces)
    protocols = {mask: selective_protocol_record(traces[mask], mask) for mask in MASKS}
    metrics: dict[str, object] = {
        "schema": "bvmsim-4bvm-allone-selective-read-additivity-isolation-metrics-v1",
        "created_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "experiment_id": EXP.name,
        "source_class": "HISTORICAL_BVMSIM_JM2_CONNECTED_VARIANT",
        "canonical_bvm_used": False,
        "artifact_qa": artifacts,
        "time_grid": {"all_array_runs_exact_identity_with_0000": all(grid_identity.values()), "per_mask": {mask: grid_record(traces[mask]) for mask in MASKS}, "interpolation": "none"},
        "protocol": protocols,
        "state_closure": state_closure(traces),
        "one_hot_position": one_hot_position(traces),
        "active_vs_single": active_vs_single(traces),
        "inactive_isolation": inactive_isolation(traces),
        "additivity": additivity(traces),
        "rsl": rsl_record(traces),
        "rs_ls3": rs_ls3_record(traces),
        "kcl": kcl_record(traces),
        "qb_jtl_secondary": qb_jtl_secondary(traces),
        "interpretation": {
            "phase_raw_unit": "rad",
            "phase_display_conversion": "continuous_unwrap(rad)/(2*pi)",
            "phase_turns_not_sfq_count": True,
            "strict_event_list_role": "secondary local diagnostic only",
            "primary_science_order": ["active_vs_isolated_single", "inactive_vs_0000", "multi_active_vs_one_hot_superposition"],
        },
        "independent_check": {"path": rel(EXP / "analysis/independent_check.json"), "status": "RUN_AFTER_MAIN_ANALYSIS"},
    }
    metrics["status"] = "ANALYSIS_VALID" if artifacts["status"] == "ARTIFACT_VALID" and all(item["status"] == "PROTOCOL_VALID" for item in protocols.values()) else "ANALYSIS_INVALID"
    if args.write:
        write_json(EXP / "analysis/metrics.json", metrics)
        (EXP / "analysis/REPORT.md").write_text(report(metrics), encoding="utf-8")
    print(json.dumps({"status": metrics["status"], "masks": len(MASKS), "grid_identity": all(grid_identity.values())}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
