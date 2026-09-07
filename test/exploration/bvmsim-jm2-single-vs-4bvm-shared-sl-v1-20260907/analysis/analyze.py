#!/usr/bin/env python3
"""Read the two immutable raw runs, perform QA/metrics, and build plot inputs.

This module never edits a raw CSV.  P traces are unwrapped in memory before
comparison and are written to derived plot CSVs in radians; the repository
plotter performs the single display conversion to phase turns.
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
from pathlib import Path
from typing import Iterable, Mapping


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
SINGLE_DIR = EXP / "runs/single"
ARRAY_DIR = EXP / "runs/array"
SINGLE_RAW = SINGLE_DIR / "raw.csv"
ARRAY_RAW = ARRAY_DIR / "raw.csv"
PREFLIGHT = EXP / "analysis/topology_preflight.json"
SOURCE_MANIFEST = EXP / "source/source_manifest.json"
SOLVER = REPO / "build/josim-cli"
VARIANT = REPO / "test/exploration/bvmsim-jm2-connected-single-ab-v1-20260903/variants/bvm_jm2_connected.cir"
JJMIT = REPO / "circuits/models/jjmit.cir"
BQ = REPO / "BVMSim/BQ.cir"
JTL = REPO / "BVMSim/library_josim/jtl2.cir"
CANONICAL_BVM = REPO / "circuits/bvm/bvm_cell.cir"
TAU = 2.0 * math.pi
PHI0 = 2.067833848e-15

sys.path.insert(0, str(REPO / "scripts"))
from bvmtools.kcl import kcl_window_metrics, linear_kcl_residual  # noqa: E402
from bvmtools.metrics import phase_area_window  # noqa: E402
from bvmtools.phase import continuous_unwrap, phase_window_metrics, window_indices  # noqa: E402
from bvmtools.raw import RawTrace, read_csv  # noqa: E402
from bvmtools.waveform import percentile, trapezoid_integral, waveform_metrics  # noqa: E402


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


def sig(identifier: str, caption: str, kind: str, single: str, array: str | None = None) -> dict[str, str]:
    return {"id": identifier, "caption": caption, "kind": kind, "single": single, "array": array or single}


SIGNALS: OrderedDict[str, list[dict[str, str]]] = OrderedDict(
    (
        (
            "CONTROL",
            [
                sig("WL", "WL control", "I", "I(I_WL1)"),
                sig("BL", "BL control", "I", "I(I_BL1)"),
                sig("SE", "SE control", "I", "I(I_SE1)"),
            ],
        ),
        (
            "BVM_STORAGE",
            [
                sig("JM1_P", "JM1 phase", "P", "P(B_JM1|XBVM1)"),
                sig("JM1_V", "JM1 voltage", "V", "V(B_JM1|XBVM1)"),
                sig("JM1_I", "JM1 current", "I", "I(B_JM1|XBVM1)"),
                sig("JM2_P", "JM2 phase", "P", "P(B_JM2|XBVM1)"),
                sig("JM2_V", "JM2 voltage", "V", "V(B_JM2|XBVM1)"),
                sig("JM2_I", "JM2 current", "I", "I(B_JM2|XBVM1)"),
                sig("LM1_I", "LM1 current", "I", "I(L_M1|XBVM1)"),
                sig("LM1_V", "LM1 voltage", "V", "V(L_M1|XBVM1)"),
                sig("LM2_I", "LM2 current", "I", "I(L_M2|XBVM1)"),
                sig("LM2_V", "LM2 voltage", "V", "V(L_M2|XBVM1)"),
                sig("LPM_I", "LPM current", "I", "I(L_PM|XBVM1)"),
                sig("LPM_V", "LPM voltage", "V", "V(L_PM|XBVM1)"),
                sig("RJM1_I", "RJM1 current", "I", "I(R_JM1|XBVM1)"),
                sig("RJM1_V", "RJM1 voltage", "V", "V(R_JM1|XBVM1)"),
            ],
        ),
        (
            "BVM_RLOOP",
            [
                sig("LM3_I", "LM3 current", "I", "I(L_M3|XBVM1)"),
                sig("LM3_V", "LM3 voltage", "V", "V(L_M3|XBVM1)"),
                sig("LS1_I", "LS1 current", "I", "I(L_S1|XBVM1)"),
                sig("LS1_V", "LS1 voltage", "V", "V(L_S1|XBVM1)"),
                sig("LS2_I", "LS2 current", "I", "I(L_S2|XBVM1)"),
                sig("LS2_V", "LS2 voltage", "V", "V(L_S2|XBVM1)"),
                sig("LS3_I", "LS3 current", "I", "I(L_S3|XBVM1)"),
                sig("LS3_V", "LS3 voltage", "V", "V(L_S3|XBVM1)"),
                sig("RS_I", "RS current", "I", "I(R_S|XBVM1)"),
                sig("RS_V", "RS voltage", "V", "V(R_S|XBVM1)"),
                sig("JS1_P", "JS1 phase", "P", "P(B_JS1|XBVM1)"),
                sig("JS1_V", "JS1 voltage", "V", "V(B_JS1|XBVM1)"),
                sig("JS1_I", "JS1 current", "I", "I(B_JS1|XBVM1)"),
                sig("JS2_P", "JS2 phase", "P", "P(B_JS2|XBVM1)"),
                sig("JS2_V", "JS2 voltage", "V", "V(B_JS2|XBVM1)"),
                sig("JS2_I", "JS2 current", "I", "I(B_JS2|XBVM1)"),
            ],
        ),
        (
            "BVM_OUTPUT",
            [
                sig("LPSL_I", "LPSL current", "I", "I(L_PSL|XBVM1)"),
                sig("LPSL_V", "LPSL voltage", "V", "V(L_PSL|XBVM1)"),
                sig("RSL_I", "RSL current", "I", "I(R_SL|XBVM1)"),
                sig("RSL_V", "RSL voltage", "V", "V(R_SL|XBVM1)"),
                sig("LSL_I", "LSL current", "I", "I(L_SL|XBVM1)"),
                sig("LSL_V", "LSL voltage", "V", "V(L_SL|XBVM1)"),
                sig("SL_BOUNDARY", "SL boundary", "V", "V(SL1)", "V(COMMON_SL)"),
            ],
        ),
        (
            "JSL_ENDPOINTS",
            [
                sig("JSL1_P", "JSL1 phase", "P", "P(B_JSL1)"),
                sig("JSL1_V", "JSL1 voltage", "V", "V(B_JSL1)"),
                sig("JSL1_I", "JSL1 current", "I", "I(B_JSL1)"),
                sig("JSL8_P", "JSL8 phase", "P", "P(B_JSL8)"),
                sig("JSL8_V", "JSL8 voltage", "V", "V(B_JSL8)"),
                sig("JSL8_I", "JSL8 current", "I", "I(B_JSL8)"),
            ],
        ),
        (
            "QB_INTERNAL",
            [
                sig("QBIN", "QBIN voltage", "V", "V(QBIN)"),
                sig("QBOUT", "QBOUT voltage", "V", "V(QBOUT)"),
                sig("LIN_I", "LIN current", "I", "I(LIN|XBQ1)"),
                sig("LIN_V", "LIN voltage", "V", "V(LIN|XBQ1)"),
                sig("L1_I", "L1 current", "I", "I(L1|XBQ1)"),
                sig("L1_V", "L1 voltage", "V", "V(L1|XBQ1)"),
                sig("L2_I", "L2 current", "I", "I(L2|XBQ1)"),
                sig("L2_V", "L2 voltage", "V", "V(L2|XBQ1)"),
                sig("L3_I", "L3 current", "I", "I(L3|XBQ1)"),
                sig("L3_V", "L3 voltage", "V", "V(L3|XBQ1)"),
                sig("RJ1_I", "RJ1 current", "I", "I(RJ1|XBQ1)"),
                sig("RJ1_V", "RJ1 voltage", "V", "V(RJ1|XBQ1)"),
                sig("RJ2_I", "RJ2 current", "I", "I(RJ2|XBQ1)"),
                sig("RJ2_V", "RJ2 voltage", "V", "V(RJ2|XBQ1)"),
                sig("IB_I", "IB current", "I", "I(IB|XBQ1)"),
                sig("BJS_P", "BJS phase", "P", "P(BJS|XBQ1)"),
                sig("BJS_V", "BJS voltage", "V", "V(BJS|XBQ1)"),
                sig("BJS_I", "BJS current", "I", "I(BJS|XBQ1)"),
                sig("BJ1_P", "BJ1 phase", "P", "P(BJ1|XBQ1)"),
                sig("BJ1_V", "BJ1 voltage", "V", "V(BJ1|XBQ1)"),
                sig("BJ1_I", "BJ1 current", "I", "I(BJ1|XBQ1)"),
                sig("BJ2_P", "BJ2 phase", "P", "P(BJ2|XBQ1)"),
                sig("BJ2_V", "BJ2 voltage", "V", "V(BJ2|XBQ1)"),
                sig("BJ2_I", "BJ2 current", "I", "I(BJ2|XBQ1)"),
            ],
        ),
        (
            "JTL_ENDPOINTS",
            [
                sig("JTL1_B01_P", "JTL1 B01 phase", "P", "P(B01|XJTL1_1)"),
                sig("JTL1_B01_V", "JTL1 B01 voltage", "V", "V(B01|XJTL1_1)"),
                sig("JTL1_B02_P", "JTL1 B02 phase", "P", "P(B02|XJTL1_1)"),
                sig("JTL1_B02_V", "JTL1 B02 voltage", "V", "V(B02|XJTL1_1)"),
                sig("JTL6_B01_P", "JTL6 B01 phase", "P", "P(B01|XJTL1_6)"),
                sig("JTL6_B01_V", "JTL6 B01 voltage", "V", "V(B01|XJTL1_6)"),
                sig("JTL6_B02_P", "JTL6 B02 phase", "P", "P(B02|XJTL1_6)"),
                sig("JTL6_B02_V", "JTL6 B02 voltage", "V", "V(B02|XJTL1_6)"),
                sig("JTL1_OUT", "JTL1 output node", "V", "V(JTL1_OUT)"),
                sig("JTL6_OUT", "JTL6 output node", "V", "V(JTL6_OUT)"),
                sig("R_TERM", "10 ohm termination current", "I", "I(R_TERM)"),
            ],
        ),
    )
)

ALL_JSL = [sig(f"JSL{i}_{kind}", f"JSL{i} {kind}", kind, f"{kind}(B_JSL{i})") for i in range(1, 9) for kind in ("P", "V", "I")]
STATE_SIGNALS = (
    sig("JM1_P", "JM1 phase", "P", "P(B_JM1|XBVM1)"),
    sig("JM2_P", "JM2 phase", "P", "P(B_JM2|XBVM1)"),
    sig("LM1_I", "LM1 current", "I", "I(L_M1|XBVM1)"),
    sig("LM2_I", "LM2 current", "I", "I(L_M2|XBVM1)"),
    sig("LM3_I", "LM3 current", "I", "I(L_M3|XBVM1)"),
    sig("LPM_I", "LPM current", "I", "I(L_PM|XBVM1)"),
)
QUIET_SIGNAL_TEMPLATES = (
    ("LSL_I", "LSL", "I", "I(L_SL|XBVM{instance})"),
    ("LS2_I", "LS2", "I", "I(L_S2|XBVM{instance})"),
    ("LS1_I", "LS1", "I", "I(L_S1|XBVM{instance})"),
    ("JM2_P", "JM2", "P", "P(B_JM2|XBVM{instance})"),
    ("JM1_P", "JM1", "P", "P(B_JM1|XBVM{instance})"),
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO.resolve()).as_posix()


def now_local() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def write_once(path: Path, content: str) -> None:
    if path.exists():
        if path.read_text(encoding="utf-8") == content:
            return
        raise RuntimeError(f"refusing to overwrite existing artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def load_trace(path: Path) -> RawTrace:
    return read_csv(path)


def values(trace: RawTrace, label: str, kind: str) -> tuple[float, ...]:
    raw = trace.column(label)
    if kind == "P":
        return continuous_unwrap(raw)  # type: ignore[arg-type]
    return raw  # type: ignore[return-value]


def raw_values(trace: RawTrace, label: str) -> tuple[float, ...]:
    return trace.column(label)  # type: ignore[return-value]


def scale_for(kind: str) -> tuple[float, float, str, str]:
    if kind == "I":
        return 1e6, 1e18, "uA", "uA*ps"
    if kind == "V":
        return 1e3, 1e15, "mV", "mV*ps"
    if kind == "P":
        return 1.0, 1.0, "rad", "rad*s"
    raise ValueError(kind)


def exact_grid(left: RawTrace, right: RawTrace) -> bool:
    return len(left.time) == len(right.time) and all(a == b for a, b in zip(left.time, right.time))


def selected(time_s: tuple[float, ...], data: tuple[float, ...], bounds: tuple[float, float]) -> tuple[list[float], list[float]]:
    indices = window_indices(time_s, *bounds)
    if len(indices) < 2:
        raise RuntimeError(f"window {bounds} has fewer than two samples")
    return [float(time_s[i]) for i in indices], [float(data[i]) for i in indices]


def summary(time_s: tuple[float, ...], data: tuple[float, ...], bounds: tuple[float, float], kind: str) -> dict[str, object]:
    t, y = selected(time_s, data, bounds)
    base = waveform_metrics(t, y)
    value_factor, area_factor, display_unit, area_unit = scale_for(kind)
    abs_values = [abs(value) for value in y]
    max_abs_index = max(range(len(y)), key=lambda i: abs(y[i]))
    return {
        "raw_unit": {"I": "A", "V": "V", "P": "rad"}[kind],
        "display_unit": display_unit,
        "area_unit": area_unit,
        "window_ps": [bounds[0] * 1e12, bounds[1] * 1e12],
        "sample_count": len(y),
        "minimum": float(base["minimum"]) * value_factor,
        "maximum": float(base["maximum"]) * value_factor,
        "mean": float(base["mean"]) * value_factor,
        "p2p": float(base["p2p"]) * value_factor,
        "rms": float(base["rms"]) * value_factor,
        "max_abs": max(abs_values) * value_factor,
        "p95_abs": percentile(abs_values, 0.95) * value_factor,
        "endpoint": y[-1] * value_factor,
        "endpoint_change": (y[-1] - y[0]) * value_factor,
        "signed_integral": trapezoid_integral(y, t) * area_factor,
        "signed_integral_raw": trapezoid_integral(y, t),
        "minimum_time_ps": float(base["minimum_time"]) * 1e12,
        "maximum_time_ps": float(base["peak_time"]) * 1e12,
        "max_abs_time_ps": t[max_abs_index] * 1e12,
    }


def delta_summary(time_s: tuple[float, ...], delta: tuple[float, ...], bounds: tuple[float, float], kind: str) -> dict[str, object]:
    base = summary(time_s, delta, bounds, kind)
    return {
        "unit": base["display_unit"],
        "raw_unit": base["raw_unit"],
        "area_unit": base["area_unit"],
        "window_ps": base["window_ps"],
        "sample_count": base["sample_count"],
        "max_abs_delta": base["max_abs"],
        "RMS_delta": base["rms"],
        "p95_abs_delta": base["p95_abs"],
        "mean_delta": base["mean"],
        "p2p": base["p2p"],
        "signed_integral_delta": base["signed_integral"],
        "signed_integral_delta_raw": base["signed_integral_raw"],
        "endpoint_delta": base["endpoint"],
        "endpoint_change_delta": base["endpoint_change"],
        "max_abs_time_ps": base["max_abs_time_ps"],
    }


def phase_area_for(trace: RawTrace, phase_label: str, bounds: tuple[float, float]) -> dict[str, object] | None:
    voltage_label = phase_label.replace("P(", "V(", 1)
    if voltage_label not in trace.headers:
        return None
    return phase_area_window(trace.time, raw_values(trace, phase_label), raw_values(trace, voltage_label), bounds, include_segments=False)


def signal_record(single: RawTrace, array: RawTrace, specification: Mapping[str, str]) -> tuple[tuple[float, ...], dict[str, object]]:
    kind = specification["kind"]
    single_values = values(single, specification["single"], kind)
    array_values = values(array, specification["array"], kind)
    delta = tuple(right - left for left, right in zip(single_values, array_values))
    record: dict[str, object] = {
        "id": specification["id"],
        "caption": specification["caption"],
        "kind": kind,
        "single_label": specification["single"],
        "array_target_label": specification["array"],
        "difference_convention": "ARRAY_TARGET_MINUS_SINGLE",
        "interpolation": "none",
        "phase_conversion": "continuous_unwrap(raw radians) for P; no conversion for I/V" if kind == "P" else None,
        "windows": {},
    }
    for window_name, bounds in WINDOWS_S.items():
        delta_metrics = delta_summary(single.time, delta, bounds, kind)
        delta_metrics["single"] = summary(single.time, single_values, bounds, kind)
        delta_metrics["array_target"] = summary(array.time, array_values, bounds, kind)
        if kind == "P":
            t, d = selected(single.time, delta, bounds)
            delta_metrics["continuous_phase_delta_endpoint_rad"] = d[-1]
            delta_metrics["continuous_phase_delta_change_rad"] = d[-1] - d[0]
            delta_metrics["continuous_phase_delta_endpoint_turns"] = d[-1] / TAU
            delta_metrics["phase_p2p_delta_turns"] = (max(d) - min(d)) / TAU
            single_area = phase_area_for(single, specification["single"], bounds)
            array_area = phase_area_for(array, specification["array"], bounds)
            voltage_label_single = specification["single"].replace("P(", "V(", 1)
            voltage_label_array = specification["array"].replace("P(", "V(", 1)
            if voltage_label_single in single.headers and voltage_label_array in array.headers:
                voltage_delta = tuple(
                    right - left
                    for left, right in zip(raw_values(single, voltage_label_single), raw_values(array, voltage_label_array))
                )
                vt, vy = selected(single.time, voltage_delta, bounds)
                delta_metrics["voltage_area_delta_wb"] = trapezoid_integral(vy, vt)
                delta_metrics["voltage_area_delta_over_phi0"] = trapezoid_integral(vy, vt) / PHI0
            delta_metrics["voltage_area_single_over_phi0"] = single_area["voltage_area_over_phi0"] if single_area else None
            delta_metrics["voltage_area_array_over_phi0"] = array_area["voltage_area_over_phi0"] if array_area else None
            delta_metrics["phase_area_consistency"] = {
                "single": {
                    "phase_delta_turns": single_area["phase_delta_turns"],
                    "voltage_area_turns": single_area["voltage_area_turns"],
                    "residual_turns": single_area["phase_area_residual_turns"],
                    "status": "DESCRIPTIVE_ONLY",
                } if single_area else None,
                "array_target": {
                    "phase_delta_turns": array_area["phase_delta_turns"],
                    "voltage_area_turns": array_area["voltage_area_turns"],
                    "residual_turns": array_area["phase_area_residual_turns"],
                    "status": "DESCRIPTIVE_ONLY",
                } if array_area else None,
                "note": "same-JJ P/V arithmetic; no event count or physical Gate",
            }
        record["windows"][window_name] = delta_metrics
    return delta, record


def expected_headers(kind: str) -> set[str]:
    instances = (1,) if kind == "single" else (1, 2, 3, 4)
    endpoint = "V(SL1)" if kind == "single" else "V(COMMON_SL)"
    required: set[str] = set()
    for i in instances:
        required.update({f"I(I_WL{i})", f"I(I_BL{i})", f"I(I_SE{i})"})
        h = f"XBVM{i}"
        for jj in ("B_JM1", "B_JM2", "B_JS1", "B_JS2"):
            required.update(f"{kind_}({jj}|{h})" for kind_ in ("P", "V", "I"))
        for branch in ("L_M1", "L_M2", "L_M3", "L_PM", "R_JM1", "L_S1", "L_S2", "R_S", "L_S3", "R_SE", "L_PSE", "L_PSL", "R_SL", "L_SL"):
            required.update({f"I({branch}|{h})", f"V({branch}|{h})"})
    required.add(endpoint)
    for i in range(1, 9):
        required.update({f"P(B_JSL{i})", f"V(B_JSL{i})", f"I(B_JSL{i})"})
    required.update({"V(QBIN)", "V(QBOUT)", "I(R_TERM)"})
    for branch in ("LIN", "L1", "L2", "L3", "RJ1", "RJ2"):
        required.update({f"I({branch}|XBQ1)", f"V({branch}|XBQ1)"})
    required.add("I(IB|XBQ1)")
    for jj in ("BJS", "BJ1", "BJ2"):
        required.update({f"P({jj}|XBQ1)", f"V({jj}|XBQ1)", f"I({jj}|XBQ1)"})
    for stage in range(1, 7):
        h = f"XJTL1_{stage}"
        required.update({f"P(B01|{h})", f"V(B01|{h})", f"I(B01|{h})", f"P(B02|{h})", f"V(B02|{h})", f"I(B02|{h})", f"V(JTL{stage}_OUT)"})
    return required


def artifact_qa(single: RawTrace, array: RawTrace) -> dict[str, object]:
    records: dict[str, object] = {}
    failures: list[str] = []
    for kind, trace, raw_path, run_dir in (("single", single, SINGLE_RAW, SINGLE_DIR), ("array", array, ARRAY_RAW, ARRAY_DIR)):
        metadata_path = run_dir / "metadata.json"
        metadata = json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path.is_file() else {}
        missing = sorted(expected_headers(kind) - set(trace.headers))
        if missing:
            failures.append(f"{kind}:missing_headers:{missing[:5]}")
        if trace.duplicate_columns:
            failures.append(f"{kind}:duplicate_columns:{trace.duplicate_columns}")
        if metadata.get("execution_status") != "RUN_PASS":
            failures.append(f"{kind}:execution_status:{metadata.get('execution_status')}")
        if metadata.get("artifacts", {}).get("raw", {}).get("sha256") != sha256(raw_path):
            failures.append(f"{kind}:metadata_raw_hash_mismatch")
        if metadata.get("artifacts", {}).get("deck", {}).get("sha256") != sha256(run_dir / "deck.cir"):
            failures.append(f"{kind}:metadata_deck_hash_mismatch")
        log_text = (run_dir / "run.log").read_text(encoding="utf-8", errors="replace") if (run_dir / "run.log").is_file() else ""
        if "v2.7.2837d13" not in log_text:
            failures.append(f"{kind}:solver_version_missing_from_log")
        if "error" in log_text.casefold() and "0 errors" not in log_text.casefold():
            failures.append(f"{kind}:solver_log_contains_error_token")
        qa = trace.qa()
        qa["raw_sha256"] = sha256(raw_path)
        qa["required_header_count"] = len(expected_headers(kind))
        qa["missing_headers"] = missing
        qa["extra_headers"] = sorted(set(trace.headers) - expected_headers(kind))
        qa["metadata_status"] = metadata.get("execution_status")
        records[kind] = qa
    grid_exact = exact_grid(single, array)
    if not grid_exact:
        failures.append("SINGLE_ARRAY:EXACT_GRID_FAIL")
    if single.time[0] != 0.0 or array.time[0] != 0.0:
        failures.append("time_start_not_zero")
    stop_coverage_ok = all(0.0 <= 200.0 - trace.time[-1] * 1e12 <= 0.100001 for trace in (single, array))
    if not stop_coverage_ok:
        failures.append("time_end_outside_registered_stop_interval")
    optional_probe = {
        "V(IB|XBQ1)": {
            "status": "NOT_SUPPORTED_BY_RAW_SCHEMA",
            "single_present": "V(IB|XBQ1)" in single.headers,
            "array_present": "V(IB|XBQ1)" in array.headers,
            "required_current_retained": "I(IB|XBQ1)" in single.headers and "I(IB|XBQ1)" in array.headers,
        }
    }
    return {
        "schema": "jm2-single-vs-4bvm-shared-sl-artifact-qa-v1",
        "created_at_local": now_local(),
        "status": "PASS" if not failures else "INVALID",
        "raw_immutable": True,
        "time_grid": {
            "single_sample_count": len(single.time),
            "array_sample_count": len(array.time),
            "exact_identity": grid_exact,
            "interpolation_used": False,
            "single_start_ps": single.time[0] * 1e12,
            "array_start_ps": array.time[0] * 1e12,
            "single_end_ps": single.time[-1] * 1e12,
            "array_end_ps": array.time[-1] * 1e12,
            "registered_stop_ps": 200.0,
            "stop_coverage_within_one_nominal_interval": stop_coverage_ok,
            "solver_output_convention": "last stored sample is 199.9 ps for .tran 0.1p 200p",
        },
        "runs": records,
        "optional_probe_support": optional_probe,
        "failures": failures,
    }


def control_equivalence(single: RawTrace, array: RawTrace) -> dict[str, object]:
    rows: dict[str, object] = {}
    failures: list[str] = []
    for name, single_label, array_label in (("WL", "I(I_WL1)", "I(I_WL1)"), ("BL", "I(I_BL1)", "I(I_BL1)"), ("SE", "I(I_SE1)", "I(I_SE1)")):
        left = raw_values(single, single_label)
        right = raw_values(array, array_label)
        deltas = tuple(b - a for a, b in zip(left, right))
        exact = all(a == b for a, b in zip(left, right))
        record = {
            "single_label": single_label,
            "array_target_label": array_label,
            "sample_count": len(deltas),
            "stored_grid_exact": exact_grid(single, array),
            "interpolation": "none",
            "pointwise_exact_zero": exact and all(value == 0.0 for value in deltas),
            "max_abs_delta_A": max(abs(value) for value in deltas),
            "RMS_delta_A": math.sqrt(sum(value * value for value in deltas) / len(deltas)),
            "nonzero_indices": [i for i, value in enumerate(deltas) if value != 0.0][:10],
        }
        rows[name] = record
        if not record["pointwise_exact_zero"]:
            failures.append(name)
    grid_exact = exact_grid(single, array)
    if not grid_exact:
        failures.append("EXACT_GRID_FAIL")
    return {
        "schema": "jm2-single-vs-4bvm-shared-sl-control-equivalence-v1",
        "created_at_local": now_local(),
        "status": "PASS" if not failures else "CONTROL_EQUIVALENCE_FAIL",
        "convention": "ARRAY_BVM1_minus_SINGLE",
        "requirements": {"pointwise_exact_zero": True, "same_stored_timestamps": True, "interpolation": "forbidden"},
        "signals": rows,
        "failures": failures,
    }


def state_summary(trace: RawTrace, instance: int, bounds: tuple[float, float]) -> dict[str, object]:
    output: dict[str, object] = {"window_ps": [bounds[0] * 1e12, bounds[1] * 1e12], "signals": {}}
    for specification in STATE_SIGNALS:
        label = specification["single"].replace("XBVM1", f"XBVM{instance}")
        data = values(trace, label, specification["kind"])
        record = summary(trace.time, data, bounds, specification["kind"])
        if specification["kind"] == "P":
            phase_record = phase_window_metrics(trace.time, raw_values(trace, label), bounds)
            voltage_label = label.replace("P(", "V(", 1)
            voltage = summary(trace.time, raw_values(trace, voltage_label), bounds, "V") if voltage_label in trace.headers else None
            record.update(
                {
                    "phase_endpoint_rad": phase_record["maximum_turns"] * TAU if False else data[window_indices(trace.time, *bounds)[-1]],
                    "phase_endpoint_turns": data[window_indices(trace.time, *bounds)[-1]] / TAU,
                    "phase_p2p_turns": phase_record["p2p_turns"],
                    "voltage_activity": {
                        "max_abs_mV": voltage["max_abs"] if voltage else None,
                        "rms_mV": voltage["rms"] if voltage else None,
                        "signed_integral_mV_ps": voltage["signed_integral"] if voltage else None,
                    },
                }
            )
        output["signals"][specification["id"]] = record
    return output


def state_checks(single: RawTrace, array: RawTrace) -> dict[str, object]:
    pre = WINDOWS_S["PRE_FINAL_READ"]
    zero = WINDOWS_S["ZERO_STATE_READ_CONTROL"]
    post_zero = WINDOWS_S["POST_ZERO_READ"]
    target = {
        "single": state_summary(single, 1, pre),
        "array_target_BVM1": state_summary(array, 1, pre),
    }
    quiet = {f"array_BVM{i}": state_summary(array, i, pre) for i in (2, 3, 4)}
    target_deltas: dict[str, object] = {}
    observed = False
    for specification in STATE_SIGNALS:
        s_data = values(single, specification["single"], specification["kind"])
        a_label = specification["single"].replace("XBVM1", "XBVM1")
        a_data = values(array, a_label, specification["kind"])
        delta = tuple(a - b for a, b in zip(a_data, s_data))
        metrics = delta_summary(single.time, delta, pre, specification["kind"])
        observed = observed or metrics["max_abs_delta"] != 0.0
        target_deltas[specification["id"]] = metrics
    zero_control = {
        "single": state_summary(single, 1, zero),
        "array_target_BVM1": state_summary(array, 1, zero),
        "array_BVM2": state_summary(array, 2, zero),
        "array_BVM3": state_summary(array, 3, zero),
        "array_BVM4": state_summary(array, 4, zero),
        "post_zero_single": state_summary(single, 1, post_zero),
        "post_zero_array_target_BVM1": state_summary(array, 1, post_zero),
    }
    return {
        "schema": "jm2-single-vs-4bvm-shared-sl-state-check-v1",
        "pre_final_window_ps": [pre[0] * 1e12, pre[1] * 1e12],
        "pre_final_target": target,
        "pre_final_quiet_cells": quiet,
        "pre_final_target_delta": target_deltas,
        "pre_final_flag": "PRE_FINAL_READ_STATE_DIFFERENCE_OBSERVED" if observed else "NO_NONZERO_PRE_FINAL_TARGET_DIFFERENCE",
        "flag_rule": "descriptive nonzero exact-grid difference only; no post hoc scientific tolerance or mechanism claim",
        "zero_state_read_control": zero_control,
        "zero_state_interpretation": "control waveform/state descriptors only; no SFQ naming",
    }


def kcl_checks(trace: RawTrace, instances: Iterable[int], include_shared: bool) -> dict[str, object]:
    records: dict[str, object] = {}
    for instance in instances:
        h = f"XBVM{instance}"
        equations = {
            "JM1_shunt": {f"I(B_JM1|{h})": 1.0, f"I(R_JM1|{h})": 1.0, f"I(L_M1|{h})": -1.0},
            "JS1_series": {f"I(L_S1|{h})": 1.0, f"I(B_JS1|{h})": -1.0},
            "JS2_series": {f"I(L_S2|{h})": 1.0, f"I(B_JS2|{h})": -1.0},
            "RLOOP_output": {f"I(R_S|{h})": 1.0, f"I(L_S3|{h})": 1.0, f"I(B_JS2|{h})": 1.0, f"I(L_PSL|{h})": -1.0},
            "SL_series_1": {f"I(L_PSL|{h})": 1.0, f"I(R_SL|{h})": -1.0},
            "SL_series_2": {f"I(R_SL|{h})": 1.0, f"I(L_SL|{h})": -1.0},
        }
        for name, coefficients in equations.items():
            residual = linear_kcl_residual({label: raw_values(trace, label) for label in coefficients}, coefficients)
            records[f"BVM{instance}_{name}"] = {
                "equation": coefficients,
                "window_metrics": {window: kcl_window_metrics(trace.time, residual, bounds, unit="A") for window, bounds in WINDOWS_S.items()},
            }
    if include_shared:
        branches = {f"LSL{instance}": raw_values(trace, f"I(L_SL|XBVM{instance})") for instance in instances}
        branches["JSL1"] = raw_values(trace, "I(B_JSL1)")
        coefficients = {name: 1.0 for name in branches if name != "JSL1"} | {"JSL1": -1.0}
        residual = linear_kcl_residual(branches, coefficients)
        records["SL_to_JSL1"] = {
            "equation": "sum(I(L_SL|XBVMi)) - I(B_JSL1)",
            "window_metrics": {window: kcl_window_metrics(trace.time, residual, bounds, unit="A") for window, bounds in WINDOWS_S.items()},
        }
    for i in range(2, 9):
        current = raw_values(trace, f"I(B_JSL{i})")
        reference = raw_values(trace, "I(B_JSL1)")
        residual = tuple(left - right for left, right in zip(current, reference))
        records[f"JSL{i}_series"] = {
            "equation": f"I(B_JSL{i}) - I(B_JSL1)",
            "window_metrics": {window: kcl_window_metrics(trace.time, residual, bounds, unit="A") for window, bounds in WINDOWS_S.items()},
        }
    return records


def plot_signal_label(specification: Mapping[str, str], role: str) -> str:
    kind = specification["kind"]
    if role == "single":
        return f"{kind}({specification['caption']}) | SINGLE [{kind == 'P' and 'continuous rad' or ('A' if kind == 'I' else 'V')}]"
    if role == "array":
        return f"{kind}({specification['caption']}) | ARRAY BVM1 [{kind == 'P' and 'continuous rad' or ('A' if kind == 'I' else 'V')}]"
    if role == "delta":
        return f"{kind}(DELTA {specification['caption']} = ARRAY BVM1 - SINGLE) [{kind == 'P' and 'continuous rad' or ('A' if kind == 'I' else 'V')}]"
    raise ValueError(role)


def standalone_label(specification: Mapping[str, str], role: str, instance: int | None = None) -> str:
    label = specification["single"] if role == "single" else specification["array"]
    suffix = "SINGLE" if role == "single" else "ARRAY BVM1"
    if instance is not None:
        label = label.replace("XBVM1", f"XBVM{instance}")
        suffix = f"ARRAY BVM{instance}"
    return f"{label} | {suffix} [{specification['kind'] == 'P' and 'continuous rad' or ('A' if specification['kind'] == 'I' else 'V')}]"


def write_derived_csv(path: Path, trace: RawTrace, specifications: Iterable[Mapping[str, str]], role: str, other: RawTrace | None = None) -> dict[str, object]:
    specifications = list(specifications)
    headers = ["time"]
    columns: list[tuple[str, tuple[float, ...]]] = []
    for specification in specifications:
        if role == "single":
            data = values(trace, specification["single"], specification["kind"])
            label = plot_signal_label(specification, "single")
            headers.append(label)
            columns.append((label, tuple(float(value) for value in data)))
        elif role == "array":
            data = values(trace, specification["array"], specification["kind"])
            label = plot_signal_label(specification, "array")
            headers.append(label)
            columns.append((label, tuple(float(value) for value in data)))
        else:
            if other is None:
                raise ValueError("comparison needs both traces")
            left = values(trace, specification["single"], specification["kind"])
            right = values(other, specification["array"], specification["kind"])
            delta = tuple(right_value - left_value for left_value, right_value in zip(left, right))
            for label, data in (
                (plot_signal_label(specification, "single"), left),
                (plot_signal_label(specification, "array"), right),
                (plot_signal_label(specification, "delta"), delta),
            ):
                headers.append(label)
                columns.append((label, tuple(float(value) for value in data)))
    rows = [headers]
    for index, timestamp in enumerate(trace.time):
        rows.append([repr(float(timestamp))] + [repr(data[index]) for _, data in columns])
    output = []
    for row in rows:
        output.append(",".join('"' + cell.replace('"', '""') + '"' if index else cell for index, cell in enumerate(row)))
    write_once(path, "\n".join(output) + "\n")
    return {"path": rel(path), "sha256": sha256(path), "labels": headers[1:], "role": role, "sample_count": len(trace.time)}


def quiet_specifications(instance: int) -> list[dict[str, str]]:
    return [sig(identifier.format(instance=instance), caption, kind, label.format(instance=instance)) for identifier, caption, kind, label in QUIET_SIGNAL_TEMPLATES]


def build_plot_inputs(single: RawTrace, array: RawTrace) -> dict[str, object]:
    entries: dict[str, object] = {"standalone": {"single": {}, "array": {}}, "comparison": {}}
    for group in ("CONTROL", "BVM_STORAGE", "BVM_RLOOP", "BVM_OUTPUT", "JSL_ENDPOINTS", "QB_INTERNAL", "JTL_ENDPOINTS"):
        single_path = EXP / "plots/derived/single" / f"{group}.csv"
        array_path = EXP / "plots/derived/array" / f"{group}.csv"
        entries["standalone"]["single"][group] = write_derived_csv(single_path, single, SIGNALS[group], "single")
        entries["standalone"]["array"][group] = write_derived_csv(array_path, array, SIGNALS[group], "array")
    entries["standalone"]["array"]["QUIET_BVMS"] = {}
    for instance in (2, 3, 4):
        path = EXP / "plots/derived/array" / f"QUIET_BVM{instance}.csv"
        entries["standalone"]["array"]["QUIET_BVMS"][str(instance)] = write_derived_csv(path, array, quiet_specifications(instance), "array")
    for group in ("CONTROL", "BVM_STORAGE", "BVM_RLOOP", "BVM_OUTPUT", "JSL_ENDPOINTS", "QB_INTERNAL", "JTL_ENDPOINTS"):
        path = EXP / "plots/comparison/data" / f"{group}_RAW_DELTA.csv"
        entries["comparison"][group] = write_derived_csv(path, single, SIGNALS[group], "comparison", other=array)
    return entries


def provenance(single: RawTrace, array: RawTrace) -> dict[str, object]:
    source_manifest = json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"))
    metadata = {kind: json.loads((EXP / "runs" / kind / "metadata.json").read_text(encoding="utf-8")) for kind in ("single", "array")}
    return {
        "schema": "jm2-single-vs-4bvm-shared-sl-provenance-v1",
        "experiment_id": EXP.name,
        "created_at_local": now_local(),
        "head_before_setup": source_manifest["head_before_setup"],
        "head_at_analysis": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip(),
        "solver": {
            "path": rel(SOLVER),
            "sha256": sha256(SOLVER),
            "version": subprocess.check_output([str(SOLVER), "--version"], cwd=REPO, text=True),
        },
        "sources": source_manifest["sources"],
        "canonical_bvm_used": False,
        "bvm_authority_statement": "historical JM2-connected variant only; canonical BVM is not an input",
        "decks": {kind: {"path": rel(EXP / "runs" / kind / "deck.cir"), "sha256": sha256(EXP / "runs" / kind / "deck.cir")} for kind in ("single", "array")},
        "raw": {kind: {"path": rel(EXP / "runs" / kind / "raw.csv"), "sha256": sha256(EXP / "runs" / kind / "raw.csv"), "bytes": (EXP / "runs" / kind / "raw.csv").stat().st_size} for kind in ("single", "array")},
        "logs": {kind: {"path": rel(EXP / "runs" / kind / "run.log"), "sha256": sha256(EXP / "runs" / kind / "run.log")} for kind in ("single", "array")},
        "run_metadata": metadata,
        "analysis_script": {"path": rel(Path(__file__)), "sha256": sha256(Path(__file__))},
        "plotter": {"path": rel(REPO / "scripts/josim-plot2.py"), "sha256": sha256(REPO / "scripts/josim-plot2.py")},
        "time_grid": {"sample_count": len(single.time), "exact_identity": exact_grid(single, array), "interpolation": "none"},
        "phase_rule": "raw JoSIM P radians -> continuous_unwrap -> display rad/(2*pi) turns; never SFQ count",
    }


def main() -> int:
    if not PREFLIGHT.is_file():
        raise RuntimeError("topology preflight is missing")
    preflight = json.loads(PREFLIGHT.read_text(encoding="utf-8"))
    if preflight.get("status") != "PASS":
        raise RuntimeError("topology preflight is not PASS")
    single = load_trace(SINGLE_RAW)
    array = load_trace(ARRAY_RAW)
    artifact = artifact_qa(single, array)
    control = control_equivalence(single, array)
    write_once(EXP / "analysis/artifact_qa.json", json.dumps(artifact, indent=2, ensure_ascii=False) + "\n")
    write_once(EXP / "analysis/control_equivalence.json", json.dumps(control, indent=2, ensure_ascii=False) + "\n")
    if artifact["status"] != "PASS":
        raise RuntimeError(f"artifact QA failed: {artifact['failures']}")
    if control["status"] != "PASS":
        raise RuntimeError(f"CONTROL_EQUIVALENCE_FAIL: {control['failures']}")
    signals_metrics: dict[str, object] = {}
    for group, specifications in SIGNALS.items():
        group_records: dict[str, object] = {}
        for specification in specifications:
            _, record = signal_record(single, array, specification)
            group_records[specification["id"]] = record
        signals_metrics[group] = group_records
    all_jsl_metrics: dict[str, object] = {}
    for specification in ALL_JSL:
        _, record = signal_record(single, array, specification)
        all_jsl_metrics[specification["id"]] = record
    metrics = {
        "schema": "jm2-single-vs-4bvm-shared-sl-metrics-v1",
        "created_at_local": now_local(),
        "status": "DESCRIPTIVE_VALID",
        "comparison_convention": "ARRAY_TARGET_MINUS_SINGLE",
        "window_semantics": "half-open intervals on actual stored timestamps",
        "time_grid": {"exact_identity": exact_grid(single, array), "interpolation": "none", "event_alignment": "none"},
        "registered_waveform_metrics": ["max_abs_delta", "RMS_delta", "p95_abs_delta", "mean_delta", "p2p", "signed_integral_delta", "endpoint_delta"],
        "registered_jj_metrics": ["continuous_phase_delta", "phase_p2p", "voltage_area", "phase_area_residual"],
        "phase_rule": "continuous_unwrap(raw radians); display turns are rad/(2*pi); phase values are not SFQ counts",
        "signals": signals_metrics,
        "all_jsl_raw_metrics": all_jsl_metrics,
        "state_checks": state_checks(single, array),
        "kcl": {
            "single": kcl_checks(single, (1,), include_shared=False),
            "array": kcl_checks(array, (1, 2, 3, 4), include_shared=True),
            "interpretation": "topology/numerical residual diagnostics; not a physical Gate",
        },
        "zero_state_control": "included under state_checks.zero_state_read_control",
        "no_sfq_event_count": True,
    }
    write_once(EXP / "analysis/metrics.json", json.dumps(metrics, indent=2, ensure_ascii=False) + "\n")
    plot_inputs = build_plot_inputs(single, array)
    write_once(EXP / "analysis/plot_inputs.json", json.dumps(plot_inputs, indent=2, ensure_ascii=False) + "\n")
    prov = provenance(single, array)
    write_once(EXP / "analysis/provenance.json", json.dumps(prov, indent=2, ensure_ascii=False) + "\n")
    numerical = {
        "schema": "jm2-single-vs-4bvm-shared-sl-numerical-qa-v1",
        "created_at_local": now_local(),
        "status": "PASS",
        "time_axis": artifact["time_grid"],
        "finite_values_and_monotonic_time": {kind: artifact["runs"][kind]["nan_inf_status"] == "PASS" and artifact["runs"][kind]["strictly_increasing_time"] for kind in ("single", "array")},
        "integral_grid": "actual stored time values; trapezoid only",
        "phase_unwrap": "full trace continuous_unwrap before window selection",
        "phase_area": "same JJ and same direction P/V arithmetic; residuals reported, not gated",
        "kcl_residuals": "recorded in metrics.json; descriptive topology QA",
        "convergence": "UNKNOWN; no timestep sweep registered or run",
        "sensitivity": "UNKNOWN; no parameter sweep registered or run",
    }
    write_once(EXP / "analysis/numerical_qa.json", json.dumps(numerical, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"status": "PASS", "artifact": artifact["status"], "control": control["status"], "samples": len(single.time), "plot_input_pages": 7}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
