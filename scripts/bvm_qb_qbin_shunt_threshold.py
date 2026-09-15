#!/usr/bin/env python3
"""Conductance-ladder experiment for the canonical QBIN linear shunt.

The experiment is intentionally narrow:

* Stage A has exactly six new resistance values and masks 0011/0111.
* Stage B is created only by a registered mechanical 2/3 response oracle.
* Existing open and R20 raw files are read-only endpoint references.
* Raw CSV files are never copied, rewritten, interpolated, or resampled.
* result.json contains scalar/navigation data only; waveform data stays in raw.

The runner is shared from scripts/ rather than copied into the experiment
directory. The experiment directory itself contains only the compact layout
registered in the user request.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Iterable

SCRIPT = Path(__file__).resolve()
REPO = SCRIPT.parents[1]
EXP = REPO / "test" / "exploration" / "bvm-qb-qbin-shunt-threshold-v1-20260915"

SOLVER = REPO / "build" / "josim-cli"
PLOTTER = REPO / "scripts" / "josim-plot2.py"
MODEL = REPO / "circuits" / "models" / "jjmit.cir"
QB = REPO / "circuits" / "qb" / "bq_parameterized_v1.cir"
BVM = REPO / "test" / "exploration" / "bvm-population-scaling-rj2p12-l1p14-l2p20-ib260-rj32-bjs400-v1-20260910" / "inputs" / "bvm_jm2_connected.cir"
JTL = REPO / "test" / "exploration" / "bvm-population-scaling-rj2p12-l1p14-l2p20-ib260-rj32-bjs400-v1-20260910" / "inputs" / "jtl2.cir"

OPEN_ROOT = REPO / "test" / "exploration" / "bvm-qb-threshold-ordering-boundary-search-v1-20260911" / "references" / "canonical_baseline"
R20_ROOT = REPO / "test" / "exploration" / "bvm-qb-qbin-shunt-r20-v1-20260914" / "runs"

MASKS_STAGE_A = ("0011", "0111")
MASKS_STAGE_B = ("0000", "0001", "1111")
ALL_MASKS = ("0000", "0001", "0011", "0111", "1111")
WINDOWS_PS = (
    (101.0, 110.0),
    (110.0, 113.0),
    (113.0, 117.0),
    (117.0, 121.0),
    (121.0, 126.0),
    (126.0, 130.0),
    (130.0, 140.0),
    (140.0, 200.0),
)
PHASE_THRESHOLDS = (0.5, 1.5, 2.5, 3.5, 4.5)
PHI0 = 2.067833848e-15
KCL_TOLERANCE_A = 1.0e-9
CONTROL_V_THRESHOLD = 2.0e-4
CONTROL_I_THRESHOLD = 2.0e-5
TERMINAL_PEAK_THRESHOLD = 2.0e-4
MIN_PEAK_GAP_PS = 2.5
RESULT_LIMIT_BYTES = 500 * 1024
FINAL_MARKER = "EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW"
CONTRACT_SENTENCE = "This experiment is governed by docs/EXPERIMENT_CONTRACT.md."

POINTS = (
    {"point_id": "r100", "label": "100", "resistance_ohm": 100.0, "conductance_S": 0.010, "g_over_g20": 0.20, "spice_value": "100"},
    {"point_id": "r66p667", "label": "66.667", "resistance_ohm": 66.6666667, "conductance_S": 0.015, "g_over_g20": 0.30, "spice_value": "66.6666667"},
    {"point_id": "r50", "label": "50", "resistance_ohm": 50.0, "conductance_S": 0.020, "g_over_g20": 0.40, "spice_value": "50"},
    {"point_id": "r40", "label": "40", "resistance_ohm": 40.0, "conductance_S": 0.025, "g_over_g20": 0.50, "spice_value": "40"},
    {"point_id": "r33p333", "label": "33.333", "resistance_ohm": 33.3333333, "conductance_S": 0.030, "g_over_g20": 0.60, "spice_value": "33.3333333"},
    {"point_id": "r25", "label": "25", "resistance_ohm": 25.0, "conductance_S": 0.040, "g_over_g20": 0.80, "spice_value": "25"},
)
POINT_BY_ID = {point["point_id"]: point for point in POINTS}

OPEN_RAW = {
    "0011": OPEN_ROOT / "0011" / "raw.csv",
    "0111": OPEN_ROOT / "0111" / "raw.csv",
}
R20_RAW = {
    "0011": R20_ROOT / "0011" / "raw.csv",
    "0111": R20_ROOT / "0111" / "raw.csv",
}
OPEN_DECK = {
    "0011": OPEN_ROOT / "0011" / "deck.cir",
    "0111": OPEN_ROOT / "0111" / "deck.cir",
}
R20_DECK = {
    "0011": R20_ROOT / "0011" / "deck.cir",
    "0111": R20_ROOT / "0111" / "deck.cir",
}
EXPECTED_OPEN_RAW_SHA256 = {
    "0011": "3da7b754c990316ff8e5981692afa958d8056a61020a1912548bf6f2b7e0249c",
    "0111": "1ca15a938b23d4ed08eb964713f91476256c4caf0677d1bfd3dc43020271ec75",
}
EXPECTED_R20_RAW_SHA256 = {
    "0011": "778469a262b3252e696c811ec371c82fa77d6b7a89fa7ea411746783bcf8cb9d",
    "0111": "88784cded8137affe353a24a9fc78665c34d3484ead835d178ae87af719bf77e",
}
EXPECTED_SOURCE_SHA256 = {
    MODEL: "19862d1fd1f1f44dfa1523848d7d3b5e2594a6c5da8fdd80144b449e5312a336",
    QB: "f676ba1ecb9b2607631a5cfc2f99b7d67e09b9e821457015fba375b8a39f13b0",
    BVM: "0093a45cc3910448b484d8bd004c6df8c22358bacc8b3ed5e23912dcab805d54",
    JTL: "ffd31f8eda2a86ca0133342be1ce678831b7237a53911eda046d2bff8454855a",
    SOLVER: "48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2",
}


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO.resolve()).as_posix()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return value


def git_head() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=REPO, text=True
    ).strip()


def git_status() -> str:
    return subprocess.check_output(
        ["git", "status", "--short", "--untracked-files=all"],
        cwd=REPO,
        text=True,
    ).strip()


def remote_head() -> str | None:
    try:
        output = subprocess.check_output(
            ["git", "ls-remote", "bvm", "refs/heads/master"],
            cwd=REPO,
            text=True,
            timeout=30,
        ).strip()
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None
    return output.split()[0] if output else None


def solver_context() -> dict[str, Any]:
    if not SOLVER.is_file():
        raise RuntimeError(f"missing solver: {SOLVER}")
    return {
        "path": rel(SOLVER),
        "sha256": sha256(SOLVER),
        "version": subprocess.check_output(
            [str(SOLVER), "--version"], cwd=REPO, text=True
        ).strip(),
    }


def record_file(name: str, path: Path, role: str) -> dict[str, Any]:
    if not path.is_file():
        raise RuntimeError(f"missing file: {path}")
    return {
        "name": name,
        "path": rel(path),
        "sha256": sha256(path),
        "bytes": path.stat().st_size,
        "role": role,
    }


def source_inventory() -> list[dict[str, Any]]:
    return [
        record_file("runner", SCRIPT, "shared experiment runner and registered mechanical oracle"),
        record_file("global_jjmit_model", MODEL, "global BVM/JSL model closure"),
        record_file("canonical_qb", QB, "canonical QB source; no parameter override"),
        record_file("bvm_jm2_connected", BVM, "latest frozen JM2-connected BVM source"),
        record_file("jtl2_source", JTL, "latest frozen JTL source instantiated six times"),
        record_file("josim_solver", SOLVER, "recorded physical solver"),
        record_file("plotter", PLOTTER, "standard JoSIM descriptive renderer"),
        record_file("shared_raw_reader", REPO / "scripts" / "bvmtools" / "raw.py", "duplicate-aware raw reader"),
        record_file("shared_phase_tools", REPO / "scripts" / "bvmtools" / "phase.py", "phase unwrap and window tools"),
        record_file("shared_waveform_tools", REPO / "scripts" / "bvmtools" / "waveform.py", "actual-grid waveform tools"),
    ]


def endpoint_inventory() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for mask in MASKS_STAGE_A:
        records.append(record_file(f"open_{mask}_raw", OPEN_RAW[mask], "read-only open endpoint raw; not copied"))
        records.append(record_file(f"open_{mask}_deck", OPEN_DECK[mask], "read-only open endpoint deck; not copied"))
        records.append(record_file(f"r20_{mask}_raw", R20_RAW[mask], "read-only R20 endpoint raw; not copied"))
        records.append(record_file(f"r20_{mask}_deck", R20_DECK[mask], "read-only R20 endpoint deck; not copied"))
    return records


def assert_sources() -> None:
    if remote_head() != git_head():
        raise RuntimeError("bvm/master is not equal to current HEAD")
    for path, expected in EXPECTED_SOURCE_SHA256.items():
        if not path.is_file() or sha256(path) != expected:
            raise RuntimeError(f"registered source changed or is missing: {path}")
    for mask in MASKS_STAGE_A:
        if sha256(OPEN_RAW[mask]) != EXPECTED_OPEN_RAW_SHA256[mask]:
            raise RuntimeError(f"open endpoint raw hash changed: {OPEN_RAW[mask]}")
        if sha256(R20_RAW[mask]) != EXPECTED_R20_RAW_SHA256[mask]:
            raise RuntimeError(f"R20 endpoint raw hash changed: {R20_RAW[mask]}")


def include_path(path: Path, deck_dir: Path) -> str:
    return Path(os.path.relpath(path, deck_dir)).as_posix()


def pwl(points: Iterable[tuple[float, float]]) -> str:
    tokens: list[str] = []
    for time_ps, current_uA in points:
        value = f"{current_uA:+g}u" if current_uA else "0"
        tokens.extend((f"{time_ps:g}p", value))
    return "pwl(" + " ".join(tokens) + ")"


def stimulus(mask: str, index: int, kind: str) -> list[tuple[float, float]]:
    active = mask[index - 1] == "1"
    if kind == "WL":
        final = 100.0 if active else 0.0
        return [
            (0, 0), (50, 0), (51, -100), (60, -100), (61, 0),
            (70, 0), (71, 100), (80, 100), (81, 0),
            (90, 0), (91, 100), (100, 100), (101, 0),
            (110, 0), (111, final), (120, final), (121, 0), (200, 0),
        ]
    if kind == "BL":
        return [
            (0, 0), (50, 0), (51, -100), (60, -100), (61, 0),
            (70, 0), (81, 0), (90, 0), (91, 100), (100, 100), (101, 0),
            (110, 0), (121, 0), (200, 0),
        ]
    if kind == "SE":
        final = 100.0 if active else 0.0
        return [
            (0, 0), (70, 0), (81, 0), (90, 0), (101, 0), (110, 0),
            (111, final), (120, final), (121, 0), (200, 0),
        ]
    raise ValueError(kind)


def probe_lines() -> list[str]:
    lines: list[str] = []
    for index in range(1, 5):
        lines.append(f".print I(I_WL{index}) I(I_BL{index}) I(I_SE{index})")
        for element in ("B_JM1", "B_JM2", "B_JS1", "B_JS2"):
            lines.append(
                f".print P({element}|XBVM{index}) V({element}|XBVM{index}) I({element}|XBVM{index})"
            )
        for element in (
            "L_M1", "L_M2", "L_M3", "L_S1",
            "L_S2", "L_S3", "L_PSL", "L_SL",
        ):
            lines.append(f".print I({element}|XBVM{index}) V({element}|XBVM{index})")
    lines.append(".print V(COMMON_SL)")
    for index in range(1, 9):
        lines.append(f".print P(B_JSL{index}) V(B_JSL{index}) I(B_JSL{index})")
    lines += [
        ".print V(QBIN)",
        ".print I(R_QBIN_SHUNT) V(R_QBIN_SHUNT)",
        ".print I(LIN|XBQ) V(LIN|XBQ)",
        ".print I(L1|XBQ) V(L1|XBQ)",
        ".print I(L2|XBQ) V(L2|XBQ)",
        ".print I(L3|XBQ) V(L3|XBQ)",
        ".print I(RJ1|XBQ) V(RJ1|XBQ)",
        ".print I(RJ2|XBQ) V(RJ2|XBQ)",
        ".print P(BJS|XBQ) V(BJS|XBQ) I(BJS|XBQ)",
        ".print P(BJ1|XBQ) V(BJ1|XBQ) I(BJ1|XBQ)",
        ".print P(BJ2|XBQ) V(BJ2|XBQ) I(BJ2|XBQ)",
        ".print V(QBOUT)",
    ]
    for index in range(1, 7):
        instance = f"XJTL1_{index}"
        lines.append(
            f".print P(B01|{instance}) V(B01|{instance}) I(B01|{instance}) "
            f"P(B02|{instance}) V(B02|{instance}) I(B02|{instance})"
        )
        lines.append(f".print V(JTL{index}_OUT)")
    lines.append(".print I(R_TERM)")
    return lines


def deck_text(point: dict[str, Any], mask: str, deck_dir: Path) -> str:
    lines = [
        f"* REGISTERED QBIN linear shunt conductance ladder; point={point['point_id']}; mask={mask}",
        "* This candidate changes exactly one line relative to the open baseline.",
        "* P(...) is raw phase in radians; phase turns are display/navigation only.",
        f".include {include_path(MODEL, deck_dir)}",
        f".include {include_path(QB, deck_dir)}",
        f".include {include_path(BVM, deck_dir)}",
        f".include {include_path(JTL, deck_dir)}",
        "",
        "XBVM1 WL1 BL1 SE1 COMMON_SL BVM",
        "XBVM2 WL2 BL2 SE2 COMMON_SL BVM",
        "XBVM3 WL3 BL3 SE3 COMMON_SL BVM",
        "XBVM4 WL4 BL4 SE4 COMMON_SL BVM",
        "",
        "B_JSL1 COMMON_SL JSL_NODE1 jjmit area=5.0",
        "B_JSL2 JSL_NODE1 JSL_NODE2 jjmit area=5.0",
        "B_JSL3 JSL_NODE2 JSL_NODE3 jjmit area=5.0",
        "B_JSL4 JSL_NODE3 JSL_NODE4 jjmit area=5.0",
        "B_JSL5 JSL_NODE4 JSL_NODE5 jjmit area=5.0",
        "B_JSL6 JSL_NODE5 JSL_NODE6 jjmit area=5.0",
        "B_JSL7 JSL_NODE6 JSL_NODE7 jjmit area=5.0",
        "B_JSL8 JSL_NODE7 QBIN jjmit area=5.0",
        "",
        "* Positive shunt direction is QBIN -> ground.",
        f"R_QBIN_SHUNT QBIN 0 {point['spice_value']}",
        "",
        "XBQ QBIN QBOUT BQ",
        "XJTL1_1 QBOUT JTL1_OUT jtl",
        "XJTL1_2 JTL1_OUT JTL2_OUT jtl",
        "XJTL1_3 JTL2_OUT JTL3_OUT jtl",
        "XJTL1_4 JTL3_OUT JTL4_OUT jtl",
        "XJTL1_5 JTL4_OUT JTL5_OUT jtl",
        "XJTL1_6 JTL5_OUT JTL6_OUT jtl",
        "R_TERM JTL6_OUT 0 10",
        "",
    ]
    for index in range(1, 5):
        for kind in ("WL", "BL", "SE"):
            lines.append(
                f"I_{kind}{index} 0 {kind}{index} "
                f"{pwl(stimulus(mask, index, kind))}"
            )
    lines += ["", ".tran 0.1p 200p", ""]
    lines += probe_lines()
    lines += [".end", ""]
    return "\n".join(lines)


def run_dir(point_id: str, mask: str) -> Path:
    return EXP / "runs" / point_id / mask


def run_id(point_id: str, mask: str) -> str:
    return f"{point_id}_{mask}"


def expected_headers(instance: str = "XBQ", include_shunt: bool = True) -> set[str]:
    required: set[str] = set()
    for index in range(1, 5):
        required.update(
            f"I(I_{kind}{index})" for kind in ("WL", "BL", "SE")
        )
        for element in ("B_JM1", "B_JM2", "B_JS1", "B_JS2"):
            required.update(
                f"{kind}({element}|XBVM{index})"
                for kind in ("P", "V", "I")
            )
        for element in (
            "L_M1", "L_M2", "L_M3", "L_S1",
            "L_S2", "L_S3", "L_PSL", "L_SL",
        ):
            required.update(
                f"{kind}({element}|XBVM{index})"
                for kind in ("I", "V")
            )
    required.add("V(COMMON_SL)")
    for index in range(1, 9):
        required.update(
            f"{kind}(B_JSL{index})" for kind in ("P", "V", "I")
        )
    required.add("V(QBIN)")
    required.add("V(QBOUT)")
    if include_shunt:
        required.update({"I(R_QBIN_SHUNT)", "V(R_QBIN_SHUNT)"})
    for element in ("LIN", "L1", "L2", "L3", "RJ1", "RJ2"):
        required.update(
            f"{kind}({element}|{instance})" for kind in ("I", "V")
        )
    for element in ("BJS", "BJ1", "BJ2"):
        required.update(
            f"{kind}({element}|{instance})"
            for kind in ("P", "V", "I")
        )
    for index in range(1, 7):
        jtl_instance = f"XJTL1_{index}"
        for element in ("B01", "B02"):
            required.update(
                f"{kind}({element}|{jtl_instance})"
                for kind in ("P", "V", "I")
            )
        required.add(f"V(JTL{index}_OUT)")
    required.add("I(R_TERM)")
    return required


def load_raw(path: Path, instance: str, include_shunt: bool) -> Any:
    sys.path.insert(0, str(SCRIPT.parent))
    from bvmtools.raw import read_csv

    trace = read_csv(path)
    if trace.duplicate_columns:
        raise RuntimeError(f"duplicate raw columns: {path}: {trace.duplicate_columns}")
    missing = sorted(expected_headers(instance, include_shunt) - set(trace.headers))
    if missing:
        raise RuntimeError(f"missing required probes in {path}: {missing}")
    if (
        trace.sample_count != 1999
        or trace.time[0] != 0.0
        or trace.time[-1] != 1.999e-10
        or any(right <= left for left, right in zip(trace.time, trace.time[1:]))
    ):
        raise RuntimeError(f"unexpected raw time grid: {path}")
    return trace


def indices(trace: Any, start_ps: float, end_ps: float) -> list[int]:
    return [
        index
        for index, value in enumerate(trace.time)
        if start_ps <= value * 1.0e12 < end_ps
    ]


def actual_integral(trace: Any, values: Iterable[float], start_ps: float, end_ps: float) -> float:
    selected = indices(trace, start_ps, end_ps)
    values_list = list(values)
    total = 0.0
    for left, right in zip(selected, selected[1:]):
        total += (
            0.5
            * (values_list[left] + values_list[right])
            * (trace.time[right] - trace.time[left])
        )
    return total


def window_stats(trace: Any, signal: str, start_ps: float, end_ps: float) -> dict[str, Any]:
    values = trace.column(signal)
    selected = indices(trace, start_ps, end_ps)
    if len(selected) < 2:
        return {
            "status": "UNKNOWN",
            "signal": signal,
            "window_ps": [start_ps, end_ps],
            "reason": "fewer than two actual samples",
        }
    selected_values = [values[index] for index in selected]
    peak_index = max(selected, key=lambda index: abs(values[index]))
    unit = "A" if signal.startswith("I(") else "V"
    area = actual_integral(trace, values, start_ps, end_ps)
    return {
        "status": "DERIVED",
        "signal": signal,
        "window_ps": [start_ps, end_ps],
        "sample_count": len(selected),
        "unit": unit,
        "first": values[selected[0]],
        "last": values[selected[-1]],
        "minimum": min(selected_values),
        "maximum": max(selected_values),
        "range": max(selected_values) - min(selected_values),
        "peak_abs": abs(values[peak_index]),
        "time_of_peak_abs_ps": trace.time[peak_index] * 1.0e12,
        "mean": sum(selected_values) / len(selected_values),
        "signed_time_integral": area,
    }


def phase_info(trace: Any, signal: str) -> dict[str, Any]:
    from bvmtools.phase import continuous_unwrap

    raw = trace.column(signal)
    unwrapped = continuous_unwrap(raw)
    base = next(
        index for index, value in enumerate(trace.time)
        if value * 1.0e12 >= 101.0
    )
    relative = [
        (value - unwrapped[base]) / (2.0 * math.pi)
        for value in unwrapped[base:]
    ]
    read_indices = indices(trace, 110.0, 121.0)
    read_relative = [
        (unwrapped[index] - unwrapped[read_indices[0]]) / (2.0 * math.pi)
        for index in read_indices
    ]
    threshold_times = {}
    for threshold in PHASE_THRESHOLDS:
        threshold_times[f"{threshold:g}"] = next(
            (
                trace.time[index] * 1.0e12
                for index in range(base, len(unwrapped))
                if (unwrapped[index] - unwrapped[base]) / (2.0 * math.pi)
                >= threshold
            ),
            None,
        )
    return {
        "signal": signal,
        "raw_unit": "radians",
        "baseline_time_ps": trace.time[base] * 1.0e12,
        "threshold_navigation_times_ps": threshold_times,
        "max_relative_turns": max(relative),
        "final_relative_turns": relative[-1],
        "p2p_relative_turns": max(relative) - min(relative),
        "rollback_from_max_turns": relative[-1] - max(relative),
        "read_110_121_endpoint_delta_turns": read_relative[-1],
        "read_110_121_p2p_turns": max(read_relative) - min(read_relative),
        "read_110_121_min_relative_turns": min(read_relative),
        "read_110_121_max_relative_turns": max(read_relative),
        "semantic_role": "PHASE_NAVIGATION_ONLY; not an SFQ count",
    }


def positive_peaks(
    trace: Any,
    signal: str,
    threshold: float = TERMINAL_PEAK_THRESHOLD,
    minimum_gap_ps: float = MIN_PEAK_GAP_PS,
) -> list[dict[str, Any]]:
    values = list(trace.column(signal))
    times = [value * 1.0e12 for value in trace.time]
    candidates = [
        index
        for index in range(1, len(values) - 1)
        if 110.0 <= times[index] < 200.0
        and values[index] >= threshold
        and values[index] >= values[index - 1]
        and values[index] > values[index + 1]
    ]
    selected: list[int] = []
    for index in candidates:
        if not selected or times[index] - times[selected[-1]] > minimum_gap_ps:
            selected.append(index)
        elif values[index] > values[selected[-1]]:
            selected[-1] = index
    return [
        {
            "peak_time_ps": times[index],
            "peak_value_V": values[index],
            "sample_index": index,
        }
        for index in selected
    ]


def terminal_lobes(trace: Any) -> dict[str, Any]:
    values = list(trace.column("V(JTL6_OUT)"))
    peaks = positive_peaks(trace, "V(JTL6_OUT)")
    if not peaks:
        return {
            "peak_navigation_count": 0,
            "lobes": [],
            "integral_110_200_V_s": actual_integral(
                trace, values, 110.0, 200.0
            ),
            "integral_110_200_over_phi0": actual_integral(
                trace, values, 110.0, 200.0
            ) / PHI0,
            "locator": {
                "threshold_V": TERMINAL_PEAK_THRESHOLD,
                "minimum_gap_ps": MIN_PEAK_GAP_PS,
            },
            "not_event_count": True,
        }
    peak_indices = [int(item["sample_index"]) for item in peaks]
    valleys = [
        min(range(left, right + 1), key=lambda index: values[index])
        for left, right in zip(peak_indices, peak_indices[1:])
    ]
    full_indices = indices(trace, 110.0, 200.0)
    bounds = [full_indices[0], *valleys, full_indices[-1]]
    lobes: list[dict[str, Any]] = []
    for ordinal, peak in enumerate(peaks):
        left, right = bounds[ordinal], bounds[ordinal + 1]
        area = 0.0
        for index in range(left, right):
            area += (
                0.5
                * (values[index] + values[index + 1])
                * (trace.time[index + 1] - trace.time[index])
            )
        lobes.append({
            "navigation_index": ordinal + 1,
            "peak_time_ps": peak["peak_time_ps"],
            "peak_value_V": peak["peak_value_V"],
            "left_boundary_ps": trace.time[left] * 1.0e12,
            "right_boundary_ps": trace.time[right] * 1.0e12,
            "signed_area_V_s": area,
            "area_over_phi0": area / PHI0,
        })
    total = actual_integral(trace, values, 110.0, 200.0)
    return {
        "peak_navigation_count": len(peaks),
        "lobes": lobes,
        "integral_110_200_V_s": total,
        "integral_110_200_over_phi0": total / PHI0,
        "locator": {
            "threshold_V": TERMINAL_PEAK_THRESHOLD,
            "minimum_gap_ps": MIN_PEAK_GAP_PS,
        },
        "not_event_count": True,
    }


def control_info(trace: Any, instance: str) -> dict[str, Any]:
    control_indices = indices(trace, 70.0, 110.0)
    jtl_values = trace.column("V(JTL6_OUT)")
    terminal_values = trace.column("I(R_TERM)")
    bj1 = phase_info(trace, f"P(BJ1|{instance})")
    bj2 = phase_info(trace, f"P(BJ2|{instance})")
    rollback_1 = abs(
        bj1["final_relative_turns"] - bj1["max_relative_turns"]
    )
    rollback_2 = abs(
        bj2["final_relative_turns"] - bj2["max_relative_turns"]
    )
    max_jtl = max(
        (abs(jtl_values[index]) for index in control_indices), default=0.0
    )
    max_terminal = max(
        (abs(terminal_values[index]) for index in control_indices),
        default=0.0,
    )
    contaminated = (
        max_jtl >= CONTROL_V_THRESHOLD
        or max_terminal >= CONTROL_I_THRESHOLD
        or rollback_1 > 0.5
        or rollback_2 > 0.5
    )
    return {
        "status": "CONTROL_CONTAMINATED" if contaminated else "CLEAN",
        "window_ps": [70.0, 110.0],
        "max_abs_JTL6_V": max_jtl,
        "max_abs_terminal_current_A": max_terminal,
        "BJ1_rollback_from_max_turns": rollback_1,
        "BJ2_rollback_from_max_turns": rollback_2,
        "thresholds": {
            "JTL6_V": CONTROL_V_THRESHOLD,
            "terminal_A": CONTROL_I_THRESHOLD,
            "rollback_turns": 0.5,
        },
        "guardrail_only": True,
    }


def response_oracle(trace: Any, instance: str) -> dict[str, Any]:
    phase_labels = {
        "BJ1": f"P(BJ1|{instance})",
        "BJ2": f"P(BJ2|{instance})",
    }
    phase_labels.update({
        f"JTL{stage}": f"P(B01|XJTL1_{stage})"
        for stage in range(1, 7)
    })
    phase = {name: phase_info(trace, label) for name, label in phase_labels.items()}
    supported = min(
        sum(value is not None for value in item["threshold_navigation_times_ps"].values())
        for item in phase.values()
    )
    qbout = positive_peaks(trace, "V(QBOUT)")
    terminal = positive_peaks(trace, "V(JTL6_OUT)")
    chain_records: list[dict[str, Any]] = []
    for ordinal in range(supported):
        threshold = PHASE_THRESHOLDS[ordinal]
        source_bj2 = phase["BJ2"]["threshold_navigation_times_ps"].get(
            f"{threshold:g}"
        )
        qbout_peak = next(
            (item for item in qbout if source_bj2 is not None and item["peak_time_ps"] > source_bj2),
            None,
        )
        phase_times = {
            name: item["threshold_navigation_times_ps"].get(f"{threshold:g}")
            for name, item in phase.items()
        }
        jtl6_time = phase_times["JTL6"]
        terminal_peak = next(
            (
                item for item in terminal
                if jtl6_time is not None and item["peak_time_ps"] > jtl6_time
            ),
            None,
        )
        chain = {
            "BJ1": phase_times["BJ1"],
            "BJ2": phase_times["BJ2"],
            "QBOUT": qbout_peak["peak_time_ps"] if qbout_peak else None,
            **{f"JTL{stage}": phase_times[f"JTL{stage}"] for stage in range(1, 7)},
            "terminal": terminal_peak["peak_time_ps"] if terminal_peak else None,
        }
        ordered_values = [value for value in chain.values()]
        complete = (
            all(value is not None for value in ordered_values)
            and all(
                left < right
                for left, right in zip(ordered_values, ordered_values[1:])
            )
        )
        chain_records.append({
            "navigation_index": ordinal + 1,
            "phase_threshold_turns": threshold,
            "navigation_times_ps": chain,
            "ordered_complete": complete,
        })
    prefix = 0
    for item in chain_records:
        if item["ordered_complete"]:
            prefix += 1
        else:
            break
    control = control_info(trace, instance)
    return {
        "phase_tracks": phase,
        "phase_supported_count": supported,
        "qbout_peak_navigation_count": len(qbout),
        "terminal_peak_navigation_count": len(terminal),
        "ordered_chain_candidates": chain_records,
        "complete_response_candidate_count": prefix,
        "second_response_present": bool(
            len(chain_records) >= 2
            and chain_records[1]["ordered_complete"]
        ),
        "fourth_response_present": bool(
            len(chain_records) >= 4
            and chain_records[3]["ordered_complete"]
        ),
        "control": control,
        "eligible_for_stage_b_2_3": bool(
            control["status"] == "CLEAN"
            and prefix == 2
        ),
        "not_sfq_count": True,
        "mechanical_oracle": (
            "phase navigation + QBOUT positive-lobe navigation + ordered "
            "JTL1..6 B01 navigation + terminal positive-lobe navigation; "
            "auxiliary only"
        ),
    }


def active_indices(mask: str) -> list[int]:
    return [
        index for index, bit in enumerate(mask, start=1) if bit == "1"
    ]


def spread(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"status": "UNKNOWN", "reason": "no active cells"}
    return {
        "status": "DERIVED",
        "minimum": min(values),
        "maximum": max(values),
        "max_minus_min": max(values) - min(values),
    }


def bvm_metrics(trace: Any, mask: str) -> dict[str, Any]:
    active = active_indices(mask)
    cells: dict[str, Any] = {}
    for index in active:
        cells[f"XBVM{index}"] = {
            "JS1": phase_info(trace, f"P(B_JS1|XBVM{index})"),
            "JS2": phase_info(trace, f"P(B_JS2|XBVM{index})"),
            "JM1_storage": phase_info(trace, f"P(B_JM1|XBVM{index})"),
            "JM2_storage": phase_info(trace, f"P(B_JM2|XBVM{index})"),
            "I_LSL_110_121": window_stats(
                trace, f"I(L_SL|XBVM{index})", 110.0, 121.0
            ),
            "I_LSL_121_126": window_stats(
                trace, f"I(L_SL|XBVM{index})", 121.0, 126.0
            ),
        }
    return {
        "active_cells": [f"XBVM{index}" for index in active],
        "cells": cells,
        "equivalent_active_cell_spread": {
            "JS1_max_relative_turns": spread(
                [cells[name]["JS1"]["max_relative_turns"] for name in cells]
            ),
            "JS2_max_relative_turns": spread(
                [cells[name]["JS2"]["max_relative_turns"] for name in cells]
            ),
            "JS1_final_relative_turns": spread(
                [cells[name]["JS1"]["final_relative_turns"] for name in cells]
            ),
            "JS2_final_relative_turns": spread(
                [cells[name]["JS2"]["final_relative_turns"] for name in cells]
            ),
            "I_LSL_110_121_peak_abs_A": spread(
                [
                    cells[name]["I_LSL_110_121"]["peak_abs"]
                    for name in cells
                ]
            ),
        },
    }


def phase_area_crosscheck(trace: Any, instance: str, element: str) -> dict[str, Any]:
    from bvmtools.phase import continuous_unwrap

    phase_signal = f"P({element}|{instance})"
    voltage_signal = f"V({element}|{instance})"
    selected = indices(trace, 110.0, 121.0)
    raw = trace.column(phase_signal)
    unwrapped = continuous_unwrap(raw)
    delta_rad = unwrapped[selected[-1]] - unwrapped[selected[0]]
    area = actual_integral(
        trace, trace.column(voltage_signal), 110.0, 121.0
    )
    return {
        "phase_signal": phase_signal,
        "voltage_signal": voltage_signal,
        "window_ps": [110.0, 121.0],
        "phase_delta_rad": delta_rad,
        "phase_delta_turns": delta_rad / (2.0 * math.pi),
        "voltage_area_V_s": area,
        "voltage_area_over_phi0": area / PHI0,
        "area_minus_phase_turns": (
            area / PHI0 - delta_rad / (2.0 * math.pi)
        ),
        "same_jj_same_direction": True,
        "not_an_sfq_count": True,
    }


def boundary_metrics(trace: Any, include_shunt: bool) -> dict[str, Any]:
    values = {
        "V_QBIN_113_117": window_stats(
            trace, "V(QBIN)", 113.0, 117.0
        ),
        "V_QBIN_117_121": window_stats(
            trace, "V(QBIN)", 117.0, 121.0
        ),
        "I_BJSL8_110_121": window_stats(
            trace, "I(B_JSL8)", 110.0, 121.0
        ),
        "I_LIN_110_121": window_stats(
            trace, "I(LIN|XBQ)" if "I(LIN|XBQ)" in trace.headers else "I(LIN|XBQ1)", 110.0, 121.0
        ),
    }
    if include_shunt:
        shunt_signal = "I(R_QBIN_SHUNT)"
        values["I_SHUNT_110_121"] = window_stats(
            trace, shunt_signal, 110.0, 121.0
        )
        for start, end in (
            (113.0, 117.0),
            (117.0, 121.0),
            (121.0, 126.0),
        ):
            key = f"{start:g}_{end:g}"
            denominator = actual_integral(
                trace, trace.column("I(B_JSL8)"), start, end
            )
            shunt_area = actual_integral(
                trace, trace.column(shunt_signal), start, end
            )
            lin_area = actual_integral(
                trace, trace.column("I(LIN|XBQ)"), start, end
            )
            if abs(denominator) <= 1.0e-30:
                fraction: dict[str, Any] = {
                    "status": "UNDEFINED",
                    "reason": "registered denominator guard",
                    "denominator_A_s": denominator,
                }
            else:
                fraction = {
                    "status": "DERIVED",
                    "denominator_A_s": denominator,
                    "shunt_area_A_s": shunt_area,
                    "lin_area_A_s": lin_area,
                    "shunt_fraction": shunt_area / denominator,
                }
            values[f"partition_{key}_ps"] = {
                "I_BJSL8_area_A_s": denominator,
                "I_R_QBIN_SHUNT_area_A_s": shunt_area,
                "I_LIN_area_A_s": lin_area,
                "shunt_fraction": fraction,
            }
    else:
        values["I_SHUNT_110_121"] = {
            "status": "NOT_APPLICABLE",
            "reason": "read-only open or R20 endpoint has no candidate shunt probe",
        }
    return {
        "direction_convention": {
            "I(B_JSL8)": "JSL_NODE7 -> QBIN",
            "I(R_QBIN_SHUNT)": "QBIN -> ground",
            "I(LIN|XBQ)": "QBIN -> QB internal node 1",
        },
        "values": values,
    }


def qb_metrics(trace: Any, instance: str) -> dict[str, Any]:
    return {
        "BJ1_navigation": phase_info(trace, f"P(BJ1|{instance})"),
        "BJ2_navigation": phase_info(trace, f"P(BJ2|{instance})"),
        "BJ1_phase_area_crosscheck": phase_area_crosscheck(
            trace, instance, "BJ1"
        ),
        "BJ2_phase_area_crosscheck": phase_area_crosscheck(
            trace, instance, "BJ2"
        ),
        "L1_windows": {
            f"[{start:g},{end:g})ps": window_stats(
                trace, f"I(L1|{instance})", start, end
            )
            for start, end in (
                (113.0, 117.0),
                (117.0, 121.0),
                (121.0, 126.0),
                (126.0, 130.0),
            )
        },
        "L2_windows": {
            f"[{start:g},{end:g})ps": window_stats(
                trace, f"I(L2|{instance})", start, end
            )
            for start, end in (
                (113.0, 117.0),
                (117.0, 121.0),
                (121.0, 126.0),
            )
        },
    }


def downstream_metrics(trace: Any) -> dict[str, Any]:
    return {
        "JTL6_B02_navigation": phase_info(
            trace, "P(B02|XJTL1_6)"
        ),
        "terminal_navigation": terminal_lobes(trace),
        "terminal_voltage_integral_110_200_over_phi0": terminal_lobes(
            trace
        )["integral_110_200_over_phi0"],
        "terminal_signal": "V(JTL6_OUT)",
        "crosscheck_layers": [
            "QB BJ1/BJ2 phase and same-JJ voltage area",
            "JTL6 B02 phase navigation",
            "terminal V(JTL6_OUT) actual-grid integral",
        ],
        "not_event_count": True,
    }


def run_metrics(
    point: dict[str, Any],
    mask: str,
    trace: Any,
    include_shunt: bool = True,
    instance: str = "XBQ",
) -> dict[str, Any]:
    return {
        "point_id": point["point_id"],
        "mask": mask,
        "run_id": run_id(point["point_id"], mask),
        "resistance_ohm": point["resistance_ohm"],
        "conductance_S": point["conductance_S"],
        "g_over_g20": point["g_over_g20"],
        "active_cells": [f"XBVM{index}" for index in active_indices(mask)],
        "raw": {
            "path": rel(trace.path),
            "sha256": sha256(trace.path),
            "bytes": trace.path.stat().st_size,
            "sample_count": trace.sample_count,
            "time_start_ps": trace.time[0] * 1.0e12,
            "time_end_ps": trace.time[-1] * 1.0e12,
            "header_count": len(trace.headers),
            "irregular_grid": trace.qa()["nonuniform_time_grid"],
        },
        "bvm": bvm_metrics(trace, mask),
        "boundary": boundary_metrics(trace, include_shunt),
        "qb": qb_metrics(trace, instance),
        "downstream": downstream_metrics(trace),
        "mechanical_response_oracle": response_oracle(
            trace, instance
        ),
    }


def point_by_id(point_id: str) -> dict[str, Any]:
    if point_id not in POINT_BY_ID:
        raise KeyError(point_id)
    return POINT_BY_ID[point_id]


def point_deck_record(point: dict[str, Any], mask: str) -> dict[str, Any]:
    deck = run_dir(point["point_id"], mask) / "deck.cir"
    return {
        "point_id": point["point_id"],
        "mask": mask,
        "run_id": run_id(point["point_id"], mask),
        "path": rel(deck),
        "sha256": sha256(deck),
        "bytes": deck.stat().st_size,
    }


def yaml_source_lines(items: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for item in items:
        lines.extend(
            [
                f"  - name: {item['name']}",
                f"    path: {json.dumps(item['path'], ensure_ascii=False)}",
                f"    sha256: {item['sha256']}",
                f"    bytes: {item['bytes']}",
                f"    role: {json.dumps(item['role'], ensure_ascii=False)}",
            ]
        )
    return "\n".join(lines)


def experiment_yaml(
    sources: list[dict[str, Any]],
    endpoints: list[dict[str, Any]],
    decks: list[dict[str, Any]],
) -> str:
    point_lines = "\n".join(
        f"    - point_id: {point['point_id']}\n"
        f"      R_shunt_ohm: {point['resistance_ohm']}\n"
        f"      conductance_S: {point['conductance_S']}\n"
        f"      G_over_G20: {point['g_over_g20']}\n"
        f"      spice_value: {point['spice_value']}"
        for point in POINTS
    )
    deck_lines = "\n".join(
        f"  - {item['run_id']}: {item['path']}; sha256={item['sha256']}"
        for item in decks
    )
    return f"""schema_version: bvm-qb-qbin-shunt-threshold-v1
id: {EXP.name}
study_phase: EXPLORATORY
role: Experimental Operator + Evidence Packager
status: PREFLIGHT_PASS
contract_sentence: {CONTRACT_SENTENCE}
scientific_review_authorized: false
scientific_interpretation_performed: false

question:
  primary: "Determine the threshold ordering of N2 second-response and N3 fourth-response navigation candidates as QBIN shunt conductance increases."
  scope: "One bounded conductance ladder; not QB parameter tuning, adaptive sweep, or T1 work."
  interpretation_ceiling: "Raw waveform and registered scalar/navigation evidence only. Scientific labels remain unassigned until review."

frozen_topology: "4 historical JM2-connected BVM -> COMMON_SL -> 8 JSL -> QBIN -> canonical BQ -> 6 existing JTL -> 10 ohm terminal"
canonical_qb_source: circuits/qb/bq_parameterized_v1.cir
canonical_qb_parameters: {{Lin_pH: 1.5, L1_pH: 1.4, L2_pH: 2.0, RJ1_ohm: 32.0, RJ2_ohm: 12.0, IB_uA: 260.0, BJS_area: 4.0, BJ1_area: 0.9, BJ2_area: 2.0, L3_pH: 1.3}}
frozen_solver: ".tran 0.1p 200p; stored time 0..199.9 ps"
frozen_protocol: "IDLE 0-50; WRITE0 50-61; zero-state read control 70-81; WRITE1 90-101; SETTLE 101-110; final read 110-121; TAIL 121-200 ps; amplitude 100uA; 1 ps edges; 9 ps plateau"
bit_order: b3b2b1b0 = BVM1/BVM2/BVM3/BVM4

stage_a:
  points:
{point_lines}
  masks: ["0011", "0111"]
  authorized_new_physical_solves: 12
  no_open_or_r20_resolve: true

stage_b:
  trigger: "At least one Stage A point with mechanical N2 exact two-response candidate and N3 exact three-response candidate, both control-clean."
  selection: "Choose maximum finite R_shunt among trigger points."
  masks: ["0000", "0001", "1111"]
  maximum_additional_solves: 3
  maximum_total_new_physical_solves: 15
  no_adaptive_sweep: true

read_only_endpoints:
{yaml_source_lines(endpoints)}

source_closure:
{yaml_source_lines(sources)}

registered_decks:
{deck_lines}

probes:
  bvm: "P/V/I(B_JM1/B_JM2/B_JS1/B_JS2), I/V(L_M1/L_M2/L_M3/L_S1/L_S2/L_S3/L_PSL/L_SL), and WL/BL/SE source currents for every BVM."
  boundary: "V(COMMON_SL), P/V/I(B_JSL7/B_JSL8), V(QBIN), I(B_JSL8), I(R_QBIN_SHUNT), I(LIN|XBQ)."
  qb: "P/V/I(BJS/BJ1/BJ2), I/V(L1/L2/L3), I/V(RJ1/RJ2), V(QBOUT)."
  downstream: "P/V/I(B01/B02) at JTL1..JTL6, stage output voltages, I(R_TERM)."
  direction: "B_JSL8 JSL_NODE7->QBIN; shunt QBIN->ground; LIN|XBQ QBIN->QB internal node1."

windows_ps:
  - [101, 110]
  - [110, 113]
  - [113, 117]
  - [117, 121]
  - [121, 126]
  - [126, 140]
  - [140, 200]
window_semantics: half-open; actual stored grid; no interpolation or resampling
phase_semantics: raw radians; independent continuous unwrap then divide by 2*pi for navigation only
voltage_area_semantics: actual-grid trapezoid on same JJ, endpoints, direction and window; not an SFQ count
kcl_equation: "I(B_JSL8) - I(R_QBIN_SHUNT) - I(LIN|XBQ)"
kcl_tolerance_A: {KCL_TOLERANCE_A}

mechanical_oracle:
  name: "complete_response_candidate"
  definition: "BJ1/BJ2 phase-navigation threshold -> QBOUT positive-lobe navigation -> ordered JTL1..JTL6 B01 thresholds -> terminal positive-lobe navigation"
  phase_thresholds_turns: [0.5, 1.5, 2.5, 3.5, 4.5]
  positive_lobe_threshold_V: {TERMINAL_PEAK_THRESHOLD}
  minimum_lobe_gap_ps: {MIN_PEAK_GAP_PS}
  control_window_ps: [70, 110]
  control_thresholds: "JTL6 voltage 0.2mV; terminal current 20uA; phase rollback 0.5 turns"
  auxiliary_only: true
  not_sfq_count: true

layout:
  root_files_only: [experiment.yaml, RESULT.md, result.json, provenance.json, runs, plots]
  forbidden_root_dirs: [screening, references, handoff, qa, analysis, inputs, data]
  run_files_only: [deck.cir, raw.csv, run.log]
  plot_policy: "HTML only; full 0-200 ps; shared local plots/assets/plotly.min.js; no focused pages; no duplicated runtime"
  result_json_limit_bytes: {RESULT_LIMIT_BYTES}

stop:
  no_2_3_window: LINEAR_SHUNT_WINDOW_NOT_FOUND
  after_stage_b: {FINAL_MARKER}
  no_automatic_followup: true
"""


def initial_result() -> dict[str, Any]:
    return {
        "schema": "bvm-qb-qbin-shunt-threshold-result-v1",
        "experiment_id": EXP.name,
        "status": "PREFLIGHT_PASS",
        "scientific_interpretation_performed": False,
        "stage_a": {"status": "NOT_RUN", "rows": [], "authorized_solve_count": 12},
        "stage_b": {"status": "NOT_AUTHORIZED", "authorized_solve_count": 0},
        "threshold_table": [],
        "classification": {
            "assigned": None,
            "status": "SCIENTIFIC_REVIEW_REQUIRED",
            "allowed": [
                "CLEAN_WINDOW_FOUND",
                "BAD_THRESHOLD_ORDERING",
                "NON_MONOTONIC_BOUNDARY",
                "NEW_PATHOLOGY",
            ],
        },
        "qa_summary": {"status": "PENDING"},
        "visualization_summary": {"status": "PENDING"},
        "package_summary": {"status": "PENDING"},
        "stop": {"final_marker": None, "automatic_followup": False},
    }


def prepare() -> None:
    if EXP.exists() and any(EXP.iterdir()):
        raise RuntimeError(f"experiment directory is not empty: {EXP}")
    assert_sources()
    EXP.mkdir(parents=True, exist_ok=True)
    sources = source_inventory()
    endpoints = endpoint_inventory()
    decks: list[dict[str, Any]] = []
    for point in POINTS:
        for mask in MASKS_STAGE_A:
            directory = run_dir(point["point_id"], mask)
            directory.mkdir(parents=True, exist_ok=True)
            deck = directory / "deck.cir"
            deck.write_text(deck_text(point, mask, directory), encoding="utf-8")
            decks.append(point_deck_record(point, mask))
    provenance = {
        "schema": "bvm-qb-qbin-shunt-threshold-provenance-v1",
        "experiment_id": EXP.name,
        "created_at": now(),
        "registration_head": git_head(),
        "remote_bvm_master": remote_head(),
        "worktree_status_at_registration": git_status(),
        "contract_sentence": CONTRACT_SENTENCE,
        "scientific_review_authorized": False,
        "scientific_interpretation_performed": False,
        "solver": solver_context(),
        "sources": sources,
        "read_only_endpoints": endpoints,
        "registered_decks": decks,
        "stage_a": {
            "points": [point["point_id"] for point in POINTS],
            "masks": list(MASKS_STAGE_A),
            "authorized_physical_solve_count": 12,
        },
        "stage_b": {
            "trigger_rule": "mechanical N2 exact two-response candidate and N3 exact three-response candidate, both control-clean",
            "masks": list(MASKS_STAGE_B),
            "authorized_physical_solve_count": 0,
            "chosen_point_id": None,
        },
        "execution": {
            "status": "PREFLIGHT_PASS",
            "run_order": [],
            "actual_physical_solve_count": 0,
            "run_records": {},
        },
        "analysis": {
            "raw_hash_before_analysis": {},
            "raw_hash_after_analysis": {},
            "raw_hashes_equal_before_after": None,
            "scientific_interpretation_performed": False,
        },
        "transformations": [
            {"name": "continuous_phase_unwrap", "raw_mutated": False},
            {"name": "phase_turn_navigation", "formula": "unwrap(raw_phase_rad)/(2*pi)", "raw_mutated": False, "not_sfq_count": True},
            {"name": "actual_grid_trapezoid", "interpolation": False, "raw_mutated": False},
            {"name": "temporary_plot_comparison_csv", "raw_mutated": False, "deleted_after_render": True},
        ],
    }
    (EXP / "experiment.yaml").write_text(
        experiment_yaml(sources, endpoints, decks), encoding="utf-8"
    )
    write_json(EXP / "provenance.json", provenance)
    write_json(EXP / "result.json", initial_result())
    print(json.dumps({
        "status": "PREFLIGHT_PASS",
        "experiment": EXP.name,
        "head": git_head(),
        "remote": remote_head(),
        "stage_a_points": [point["point_id"] for point in POINTS],
        "stage_a_solves": 12,
        "stage_b_max_additional_solves": 3,
    }, ensure_ascii=False, indent=2))


def write_provenance(provenance: dict[str, Any]) -> None:
    write_json(EXP / "provenance.json", provenance)


def repair_tool_provenance() -> None:
    provenance = read_json(EXP / "provenance.json")
    if provenance["execution"].get("actual_physical_solve_count", 0) == 0:
        raise RuntimeError("tool provenance repair is only for post-solve analysis tooling")
    runner = next(
        item for item in provenance["sources"] if item["name"] == "runner"
    )
    old_hash = runner["sha256"]
    new_hash = sha256(SCRIPT)
    runner["sha256"] = new_hash
    runner["bytes"] = SCRIPT.stat().st_size
    provenance.setdefault("tooling_revisions", []).append({
        "path": rel(SCRIPT),
        "old_sha256": old_hash,
        "new_sha256": new_hash,
        "reason": "analysis-only endpoint instance mapping repair after all physical solves; no raw or solver rerun",
        "raw_mutated": False,
    })
    write_provenance(provenance)
    print(json.dumps({
        "status": "PASS",
        "old_runner_sha256": old_hash,
        "new_runner_sha256": new_hash,
        "physical_rerun": False,
    }, ensure_ascii=False, indent=2))


def verify_registered_sources(provenance: dict[str, Any]) -> None:
    for item in provenance["sources"]:
        path = REPO / item["path"]
        if not path.is_file() or sha256(path) != item["sha256"]:
            raise RuntimeError(f"registered source changed: {path}")


def execute_one(point: dict[str, Any], mask: str) -> None:
    provenance = read_json(EXP / "provenance.json")
    verify_registered_sources(provenance)
    directory = run_dir(point["point_id"], mask)
    deck = directory / "deck.cir"
    raw = directory / "raw.csv"
    log = directory / "run.log"
    identifier = run_id(point["point_id"], mask)
    if not deck.is_file():
        raise RuntimeError(f"registered deck missing: {deck}")
    registered_deck = next(
        item for item in provenance["registered_decks"]
        if item["run_id"] == identifier
    )
    if sha256(deck) != registered_deck["sha256"]:
        raise RuntimeError(f"registered deck changed: {deck}")

    existing = provenance["execution"]["run_records"].get(identifier)
    if raw.exists() or log.exists():
        if (
            not existing
            or existing.get("execution_status") != "RUN_PASS"
            or not raw.is_file()
            or not log.is_file()
            or sha256(raw) != existing.get("raw", {}).get("sha256")
        ):
            raise RuntimeError(
                f"partial or failed artifacts exist; refusing retry: {directory}"
            )
        load_raw(raw, "XBQ", True)
        return

    command = [str(SOLVER), "-a", "1", "-o", str(raw), str(deck)]
    started = now()
    with log.open("x", encoding="utf-8") as stream:
        stream.write(
            f"experiment={EXP.name}\nrun_id={identifier}\n"
            f"started_at={started}\ncommand={' '.join(command)}\n"
        )
        stream.flush()
        completed = subprocess.run(
            command,
            cwd=REPO,
            stdout=stream,
            stderr=subprocess.STDOUT,
            check=False,
        )
        stream.write(f"finished_at={now()}\nexit_code={completed.returncode}\n")

    record: dict[str, Any] = {
        "run_id": identifier,
        "point_id": point["point_id"],
        "mask": mask,
        "resistance_ohm": point["resistance_ohm"],
        "conductance_S": point["conductance_S"],
        "g_over_g20": point["g_over_g20"],
        "deck": {
            "path": rel(deck),
            "sha256": sha256(deck),
            "bytes": deck.stat().st_size,
        },
        "log": {
            "path": rel(log),
            "sha256": sha256(log),
            "bytes": log.stat().st_size,
        },
        "command": command,
        "solver": solver_context(),
        "started_at": started,
        "finished_at": now(),
        "raw_immutable": True,
        "scientific_interpretation_performed": False,
    }
    if completed.returncode != 0 or not raw.is_file() or raw.stat().st_size == 0:
        record["execution_status"] = "SOLVER_FAIL"
        provenance["execution"]["run_records"][identifier] = record
        provenance["execution"]["run_order"].append(identifier)
        provenance["execution"]["actual_physical_solve_count"] = len(
            provenance["execution"]["run_order"]
        )
        provenance["execution"]["status"] = "SOLVER_FAILURE_STOP"
        write_provenance(provenance)
        raise RuntimeError(
            f"solver failed for {identifier}; raw/log preserved and no retry"
        )
    try:
        trace = load_raw(raw, "XBQ", True)
    except Exception as exc:
        record["execution_status"] = "RAW_QA_FAILURE"
        record["raw"] = {
            "path": rel(raw),
            "sha256": sha256(raw),
            "bytes": raw.stat().st_size,
        }
        record["error"] = str(exc)
        provenance["execution"]["run_records"][identifier] = record
        provenance["execution"]["run_order"].append(identifier)
        provenance["execution"]["actual_physical_solve_count"] = len(
            provenance["execution"]["run_order"]
        )
        provenance["execution"]["status"] = "RAW_QA_FAILURE_STOP"
        write_provenance(provenance)
        raise RuntimeError(
            f"raw QA failed for {identifier}; artifact preserved and no retry"
        ) from exc

    record["raw"] = {
        "path": rel(raw),
        "sha256": sha256(raw),
        "bytes": raw.stat().st_size,
        "sample_count": trace.sample_count,
        "time_start_ps": trace.time[0] * 1.0e12,
        "time_end_ps": trace.time[-1] * 1.0e12,
        "header_count": len(trace.headers),
    }
    record["execution_status"] = "RUN_PASS"
    provenance["execution"]["run_records"][identifier] = record
    provenance["execution"]["run_order"].append(identifier)
    provenance["execution"]["actual_physical_solve_count"] = len(
        provenance["execution"]["run_order"]
    )
    write_provenance(provenance)


def execute_stage_a() -> None:
    provenance = read_json(EXP / "provenance.json")
    if provenance["execution"]["status"] not in {
        "PREFLIGHT_PASS", "STAGE_A_RUNNING", "STAGE_A_COMPLETE"
    }:
        raise RuntimeError("Stage A is not executable in the current state")
    provenance["execution"]["status"] = "STAGE_A_RUNNING"
    write_provenance(provenance)
    for point in POINTS:
        for mask in MASKS_STAGE_A:
            execute_one(point, mask)
    provenance = read_json(EXP / "provenance.json")
    provenance["execution"]["status"] = "STAGE_A_COMPLETE"
    write_provenance(provenance)


def register_stage_b(point: dict[str, Any]) -> None:
    provenance = read_json(EXP / "provenance.json")
    if provenance["stage_b"]["chosen_point_id"] is not None:
        if provenance["stage_b"]["chosen_point_id"] != point["point_id"]:
            raise RuntimeError("Stage B chosen point cannot be changed")
        return
    new_decks: list[dict[str, Any]] = []
    for mask in MASKS_STAGE_B:
        directory = run_dir(point["point_id"], mask)
        directory.mkdir(parents=True, exist_ok=True)
        deck = directory / "deck.cir"
        deck.write_text(deck_text(point, mask, directory), encoding="utf-8")
        new_decks.append(point_deck_record(point, mask))
    provenance["registered_decks"].extend(new_decks)
    provenance["stage_b"]["chosen_point_id"] = point["point_id"]
    provenance["stage_b"]["authorized_physical_solve_count"] = 3
    provenance["stage_b"]["status"] = "AUTHORIZED"
    provenance["execution"]["status"] = "STAGE_B_AUTHORIZED"
    write_provenance(provenance)


def execute_stage_b() -> None:
    provenance = read_json(EXP / "provenance.json")
    chosen = provenance["stage_b"].get("chosen_point_id")
    if provenance["stage_b"].get("status") != "AUTHORIZED" or not chosen:
        raise RuntimeError("Stage B is not authorized")
    point = point_by_id(chosen)
    provenance["execution"]["status"] = "STAGE_B_RUNNING"
    write_provenance(provenance)
    for mask in MASKS_STAGE_B:
        execute_one(point, mask)
    provenance = read_json(EXP / "provenance.json")
    provenance["stage_b"]["status"] = "COMPLETE"
    provenance["execution"]["status"] = "STAGE_B_COMPLETE"
    write_provenance(provenance)


def endpoint_point(kind: str) -> dict[str, Any]:
    if kind == "open":
        return {
            "point_id": "open",
            "label": "open",
            "resistance_ohm": math.inf,
            "conductance_S": 0.0,
            "g_over_g20": 0.0,
            "spice_value": "open",
        }
    if kind == "r20":
        return {
            "point_id": "r20",
            "label": "20",
            "resistance_ohm": 20.0,
            "conductance_S": 0.05,
            "g_over_g20": 1.0,
            "spice_value": "20",
        }
    raise KeyError(kind)


def response_flag(oracle: dict[str, Any], field: str) -> str:
    if oracle["control"]["status"] != "CLEAN":
        return "CONTROL_CONTAMINATED"
    return "PRESENT" if oracle[field] else "ABSENT"


def phase_mean(metric: dict[str, Any], jj: str, field: str) -> float | None:
    values = [
        cell[jj][field]
        for cell in metric["bvm"]["cells"].values()
    ]
    return sum(values) / len(values) if values else None


def threshold_row(
    point: dict[str, Any],
    n2: dict[str, Any],
    n3: dict[str, Any],
    source_kind: str,
) -> dict[str, Any]:
    n2_oracle = n2["mechanical_response_oracle"]
    n3_oracle = n3["mechanical_response_oracle"]
    n2_control_clean = n2_oracle["control"]["status"] == "CLEAN"
    n3_control_clean = n3_oracle["control"]["status"] == "CLEAN"
    trigger = bool(
        n2_control_clean
        and n3_control_clean
        and n2_oracle["complete_response_candidate_count"] == 2
        and n2_oracle["second_response_present"]
        and n3_oracle["complete_response_candidate_count"] == 3
        and not n3_oracle["fourth_response_present"]
    )
    return {
        "point_id": point["point_id"],
        "Rsh_ohm": point["resistance_ohm"],
        "Rsh_label": point["label"],
        "G_S": point["conductance_S"],
        "G_over_G20": point["g_over_g20"],
        "source_kind": source_kind,
        "N2_response_candidate_count": n2_oracle["complete_response_candidate_count"],
        "N3_response_candidate_count": n3_oracle["complete_response_candidate_count"],
        "N2_second": response_flag(n2_oracle, "second_response_present"),
        "N3_fourth": response_flag(n3_oracle, "fourth_response_present"),
        "N2_JS1_read_110_121_p2p_turns_mean": phase_mean(n2, "JS1", "read_110_121_p2p_turns"),
        "N2_JS2_read_110_121_p2p_turns_mean": phase_mean(n2, "JS2", "read_110_121_p2p_turns"),
        "N3_JS1_read_110_121_p2p_turns_mean": phase_mean(n3, "JS1", "read_110_121_p2p_turns"),
        "N3_JS2_read_110_121_p2p_turns_mean": phase_mean(n3, "JS2", "read_110_121_p2p_turns"),
        "N2_control": n2_oracle["control"]["status"],
        "N3_control": n3_oracle["control"]["status"],
        "mechanical_2_3_trigger": trigger,
        "scientific_status": "SCIENTIFIC_REVIEW_REQUIRED",
        "not_sfq_count": True,
    }


def compact_endpoint_record(
    kind: str,
    point: dict[str, Any],
    mask: str,
    metric: dict[str, Any],
) -> dict[str, Any]:
    oracle = metric["mechanical_response_oracle"]
    return {
        "kind": kind,
        "mask": mask,
        "raw": metric["raw"],
        "response_candidate_count": oracle["complete_response_candidate_count"],
        "second_response": response_flag(oracle, "second_response_present"),
        "fourth_response": response_flag(oracle, "fourth_response_present"),
        "control": oracle["control"]["status"],
        "JS1_read_110_121_p2p_turns": phase_mean(metric, "JS1", "read_110_121_p2p_turns"),
        "JS2_read_110_121_p2p_turns": phase_mean(metric, "JS2", "read_110_121_p2p_turns"),
        "not_sfq_count": True,
    }


def threshold_summary(stage_a_rows: list[dict[str, Any]]) -> dict[str, Any]:
    n2_absent = next(
        (row for row in stage_a_rows if row["N2_second"] == "ABSENT"),
        None,
    )
    n3_absent = next(
        (row for row in stage_a_rows if row["N3_fourth"] == "ABSENT"),
        None,
    )
    n2_sequence = [
        row["N2_response_candidate_count"] for row in stage_a_rows
    ]
    n3_sequence = [
        row["N3_response_candidate_count"] for row in stage_a_rows
    ]
    return {
        "stage_a_conductance_order": [
            row["point_id"] for row in stage_a_rows
        ],
        "N2_second_first_absent": {
            "point_id": n2_absent["point_id"] if n2_absent else None,
            "G_over_G20": n2_absent["G_over_G20"] if n2_absent else None,
            "Rsh_ohm": n2_absent["Rsh_ohm"] if n2_absent else None,
        },
        "N3_fourth_first_absent": {
            "point_id": n3_absent["point_id"] if n3_absent else None,
            "G_over_G20": n3_absent["G_over_G20"] if n3_absent else None,
            "Rsh_ohm": n3_absent["Rsh_ohm"] if n3_absent else None,
        },
        "mechanical_2_3_points": [
            row["point_id"]
            for row in stage_a_rows
            if row["mechanical_2_3_trigger"]
        ],
        "N2_response_sequence": n2_sequence,
        "N3_response_sequence": n3_sequence,
        "N2_sequence_non_increasing": all(
            left >= right
            for left, right in zip(n2_sequence, n2_sequence[1:])
        ),
        "N3_sequence_non_increasing": all(
            left >= right
            for left, right in zip(n3_sequence, n3_sequence[1:])
        ),
        "scientific_status": "SCIENTIFIC_REVIEW_REQUIRED",
    }


def result_markdown(result: dict[str, Any]) -> str:
    rows = result.get("threshold_table", [])
    lines = [
        f"# QBIN linear-shunt threshold-window experiment: {EXP.name}",
        "",
        f"- Workflow status: {result.get('workflow_outcome', 'PENDING')}",
        f"- Final state: {result.get('stop', {}).get('final_marker') or 'STAGE_B_DECISION_PENDING'}",
        f"- Scientific interpretation: NOT_PERFORMED; classification: {result.get('classification', {}).get('status')}",
        f"- Physical solves: {result.get('execution', {}).get('actual_physical_solve_count', 0)}; Stage A authorized 12; Stage B maximum 3.",
        "- Independent variable: conductance of one resistor R_QBIN_SHUNT from QBIN to ground.",
        "",
        "## Threshold-result table",
        "",
        "The response columns below are auxiliary mechanical navigation candidates.",
        "They are not SFQ counts, event certification, or a physical verdict.",
        "",
        "| Rsh (ohm) | G/G20 | N2 response candidates | N3 response candidates | N2 2nd | N3 4th | N2 JS1/JS2 read p2p turns | N3 JS1/JS2 read p2p turns |",
        "|---:|---:|---:|---:|---|---|---:|---:|",
    ]
    for row in rows:
        resistance = "open" if math.isinf(row["Rsh_ohm"]) else row["Rsh_label"]
        n2_pair = f"{row['N2_JS1_read_110_121_p2p_turns_mean']:.4g}/{row['N2_JS2_read_110_121_p2p_turns_mean']:.4g}"
        n3_pair = f"{row['N3_JS1_read_110_121_p2p_turns_mean']:.4g}/{row['N3_JS2_read_110_121_p2p_turns_mean']:.4g}"
        lines.append(
            f"| {resistance} | {row['G_over_G20']:.2f} | "
            f"{row['N2_response_candidate_count']} | {row['N3_response_candidate_count']} | "
            f"{row['N2_second']} | {row['N3_fourth']} | {n2_pair} | {n3_pair} |"
        )
    lines += [
        "",
        "## Required review answers",
        "",
        f"1. Earliest N3 fourth-response disappearance in the registered Stage A order: {result['threshold_summary']['N3_fourth_first_absent']['point_id'] or 'none'}; scientific classification remains pending review.",
        f"2. Earliest N2 second-response disappearance in the registered Stage A order: {result['threshold_summary']['N2_second_first_absent']['point_id'] or 'none'}; scientific classification remains pending review.",
        f"3. Mechanical threshold ordering: N2 second first absent at G/G20={result['threshold_summary']['N2_second_first_absent']['G_over_G20']}; N3 fourth first absent at G/G20={result['threshold_summary']['N3_fourth_first_absent']['G_over_G20']}.",
        f"4. Mechanical 2/3 points: {result['threshold_summary']['mechanical_2_3_points'] or 'none'}; no post-hoc interpolation is performed.",
        "5. If a 2/3 trigger exists, Stage B uses only the maximum finite R point and",
        "   masks 0000, 0001, 1111; otherwise the workflow stops without extra solves.",
        "6. QBIN voltage, shunt fraction, L1 windows, BVM storage, symmetry, rollback,",
        "   and non-monotonicity scalars are in result.json and remain review questions.",
        "",
        "## Evidence boundary",
        "",
        "P(...) is raw phase in radians. Phase turns are independent unwrap(rad)/(2*pi)",
        "navigation values only; they are not SFQ counts. Terminal integrals and lobe",
        "navigation are descriptive cross-checks, not event-count authority.",
        "",
        "Open and R20 endpoints are referenced by path and SHA-256 only. No historical",
        "raw is copied into this experiment. No focused plots, ZIP in Git, or automatic",
        "post-Stage-B experiment is created.",
        "",
        f"Stop marker: {result.get('stop', {}).get('final_marker') or 'pending'}",
        "",
    ]
    return "\n".join(lines)


def analyze() -> None:
    provenance = read_json(EXP / "provenance.json")
    run_records = provenance["execution"]["run_records"]
    before: dict[str, str] = {}
    all_metrics: list[dict[str, Any]] = []
    metric_by_point_mask: dict[tuple[str, str], dict[str, Any]] = {}
    for identifier in provenance["execution"]["run_order"]:
        record = run_records[identifier]
        raw = REPO / record["raw"]["path"]
        before[identifier] = sha256(raw)
        metric = run_metrics(
            point_by_id(record["point_id"]),
            record["mask"],
            load_raw(raw, "XBQ", True),
            True,
        )
        all_metrics.append(metric)
        metric_by_point_mask[(record["point_id"], record["mask"])] = metric

    endpoint_metrics: dict[str, dict[str, dict[str, Any]]] = {}
    for kind, paths, hashes in (
        ("open", OPEN_RAW, EXPECTED_OPEN_RAW_SHA256),
        ("r20", R20_RAW, EXPECTED_R20_RAW_SHA256),
    ):
        endpoint_metrics[kind] = {}
        endpoint_instance = "XBQ1" if kind == "open" else "XBQ"
        for mask in MASKS_STAGE_A:
            trace = load_raw(paths[mask], endpoint_instance, False)
            endpoint_metrics[kind][mask] = run_metrics(
                endpoint_point(kind),
                mask,
                trace,
                False,
                endpoint_instance,
            )
            if sha256(paths[mask]) != hashes[mask]:
                raise RuntimeError(f"endpoint changed during analysis: {paths[mask]}")

    stage_a_rows: list[dict[str, Any]] = []
    for point in POINTS:
        n2 = metric_by_point_mask[(point["point_id"], "0011")]
        n3 = metric_by_point_mask[(point["point_id"], "0111")]
        stage_a_rows.append(
            threshold_row(point, n2, n3, "NEW_PHYSICAL_SOLVE_STAGE_A")
        )
    endpoint_rows = [
        threshold_row(
            endpoint_point(kind),
            endpoint_metrics[kind]["0011"],
            endpoint_metrics[kind]["0111"],
            "READ_ONLY_ENDPOINT_REFERENCE",
        )
        for kind in ("open", "r20")
    ]
    table_rows = [endpoint_rows[0], *stage_a_rows, endpoint_rows[1]]
    stage_a_trigger_points = [
        row["point_id"] for row in stage_a_rows
        if row["mechanical_2_3_trigger"]
    ]

    stage_b_status = provenance["stage_b"].get("status", "NOT_AUTHORIZED")
    chosen = provenance["stage_b"].get("chosen_point_id")
    stage_b_metrics = [
        metric for metric in all_metrics
        if chosen and metric["point_id"] == chosen
        and metric["mask"] in MASKS_STAGE_B
    ]
    after = {
        identifier: sha256(REPO / run_records[identifier]["raw"]["path"])
        for identifier in provenance["execution"]["run_order"]
    }
    if before != after:
        raise RuntimeError("raw changed during analysis")
    provenance["analysis"] = {
        "generated_at": now(),
        "raw_hash_before_analysis": before,
        "raw_hash_after_analysis": after,
        "raw_hashes_equal_before_after": True,
        "scientific_interpretation_performed": False,
        "mechanical_oracle_only": True,
    }
    write_provenance(provenance)

    if stage_b_status == "COMPLETE":
        workflow_outcome = "FOUND_2_3_WINDOW"
        final_marker: str | None = FINAL_MARKER
    elif stage_b_status == "NO_WINDOW":
        workflow_outcome = "LINEAR_SHUNT_WINDOW_NOT_FOUND"
        final_marker = FINAL_MARKER
    elif stage_b_status == "AUTHORIZED":
        workflow_outcome = "FOUND_2_3_WINDOW_STAGE_B_PENDING"
        final_marker = None
    else:
        workflow_outcome = "STAGE_A_COMPLETE_STAGE_B_DECISION_PENDING"
        final_marker = None

    result = {
        "schema": "bvm-qb-qbin-shunt-threshold-result-v1",
        "experiment_id": EXP.name,
        "generated_at": now(),
        "workflow_outcome": workflow_outcome,
        "scientific_interpretation_performed": False,
        "execution": {
            "authorized_stage_a_physical_solve_count": 12,
            "authorized_stage_b_maximum_physical_solve_count": 3,
            "actual_physical_solve_count": provenance["execution"]["actual_physical_solve_count"],
            "run_order": provenance["execution"]["run_order"],
            "stage_a_run_count": sum(
                record["point_id"] in POINT_BY_ID
                and record["mask"] in MASKS_STAGE_A
                for record in run_records.values()
            ),
            "stage_b_run_count": len(stage_b_metrics),
        },
        "frozen_configuration": {
            "topology": "4 historical JM2-connected BVM -> COMMON_SL -> 8 JSL -> QBIN -> canonical BQ -> 6 existing JTL -> 10 ohm terminal",
            "qb_parameters": {
                "Lin_pH": 1.5, "L1_pH": 1.4, "L2_pH": 2.0,
                "RJ1_ohm": 32.0, "RJ2_ohm": 12.0, "IB_uA": 260.0,
                "BJS_area": 4.0, "BJ1_area": 0.9, "BJ2_area": 2.0,
                "L3_pH": 1.3,
            },
            "tran": ".tran 0.1p 200p",
            "protocol": "same as R20 experiment; masks b3b2b1b0=BVM1/BVM2/BVM3/BVM4",
        },
        "read_only_endpoints": [
            compact_endpoint_record(
                kind,
                endpoint_point(kind),
                mask,
                endpoint_metrics[kind][mask],
            )
            for kind in ("open", "r20")
            for mask in MASKS_STAGE_A
        ],
        "stage_a": {
            "status": "COMPLETE",
            "points": stage_a_rows,
            "trigger_points": stage_a_trigger_points,
            "found_2_3_window": bool(stage_a_trigger_points),
        },
        "threshold_summary": threshold_summary(stage_a_rows),
        "stage_b": {
            "status": stage_b_status,
            "chosen_point_id": chosen,
            "masks": list(MASKS_STAGE_B) if chosen else [],
            "population_map": [
                metric["mechanical_response_oracle"]
                | {"point_id": metric["point_id"], "mask": metric["mask"]}
                for metric in stage_b_metrics
            ],
        },
        "run_metrics": all_metrics,
        "threshold_table": table_rows,
        "classification": {
            "assigned": None,
            "status": "SCIENTIFIC_REVIEW_REQUIRED",
            "allowed": [
                "CLEAN_WINDOW_FOUND",
                "BAD_THRESHOLD_ORDERING",
                "NON_MONOTONIC_BOUNDARY",
                "NEW_PATHOLOGY",
            ],
        },
        "qa_summary": result_qa_summary(provenance),
        "visualization_summary": {
            "status": provenance.get("visualization", {}).get("status", "PENDING"),
            "standalone_count": provenance.get("visualization", {}).get("standalone_count", len(provenance.get("visualization", {}).get("standalone_pages", []))),
            "comparison_count": provenance.get("visualization", {}).get("comparison_count", len(provenance.get("visualization", {}).get("comparison_pages", []))),
            "html_count": provenance.get("visualization", {}).get("html_count"),
            "shared_asset": provenance.get("visualization", {}).get("asset", {}).get("path"),
            "focused_pages": provenance.get("visualization", {}).get("focused_pages", []),
        },
        "package_summary": {
            "status": provenance.get("package", {}).get("status", "PENDING"),
            "package_sha256": provenance.get("package", {}).get("qa", {}).get("package_sha256"),
            "package_bytes": provenance.get("package", {}).get("qa", {}).get("package_bytes"),
        },
        "review_questions": [
            "N3 fourth response earliest conductance",
            "N2 second response earliest conductance",
            "threshold ordering",
            "2/3 window and maximum R if any",
            "chosen-R N3 JS1/JS2 navigation regime",
            "source runaway versus QB input partition",
            "V(QBIN) conductance trend",
            "N2 L1 re-arm trend",
            "BVM JM1/JM2 storage",
            "active-cell positional symmetry",
            "non-monotonic response",
            "Stage B full population map if triggered",
        ],
        "stop": {
            "final_marker": final_marker,
            "automatic_followup": False,
        },
    }
    write_json(EXP / "result.json", result)
    (EXP / "RESULT.md").write_text(result_markdown(result), encoding="utf-8")
    if (EXP / "result.json").stat().st_size >= RESULT_LIMIT_BYTES:
        raise RuntimeError(
            f"result.json exceeds registered size limit: {(EXP / 'result.json').stat().st_size}"
        )


def decide_stage_b() -> None:
    provenance = read_json(EXP / "provenance.json")
    if provenance["stage_b"].get("status") in {"NO_WINDOW", "COMPLETE"}:
        return
    result = read_json(EXP / "result.json")
    trigger_points = result["stage_a"].get("trigger_points", [])
    if not trigger_points:
        provenance["stage_b"]["status"] = "NO_WINDOW"
        provenance["stage_b"]["authorized_physical_solve_count"] = 0
        provenance["execution"]["status"] = "STAGE_A_COMPLETE_STOP"
        write_provenance(provenance)
        analyze()
        return
    chosen = max(
        (point_by_id(point_id) for point_id in trigger_points),
        key=lambda point: point["resistance_ohm"],
    )
    register_stage_b(chosen)
    analyze()


def execute() -> None:
    provenance = read_json(EXP / "provenance.json")
    if provenance["execution"]["status"] == "PREFLIGHT_PASS":
        execute_stage_a()
    elif provenance["execution"]["status"] not in {
        "STAGE_A_COMPLETE",
        "STAGE_B_AUTHORIZED",
        "STAGE_B_RUNNING",
        "STAGE_B_COMPLETE",
        "STAGE_A_COMPLETE_STOP",
    }:
        raise RuntimeError(
            f"execution is not resumable in state {provenance['execution']['status']}"
        )
    provenance = read_json(EXP / "provenance.json")
    if provenance["execution"]["status"] == "STAGE_A_COMPLETE":
        analyze()
        decide_stage_b()
    provenance = read_json(EXP / "provenance.json")
    if provenance["stage_b"].get("status") == "AUTHORIZED":
        execute_stage_b()
        analyze()


def result_qa_summary(provenance: dict[str, Any]) -> dict[str, Any]:
    qa = provenance.get("qa")
    if not isinstance(qa, dict):
        return {"status": "PENDING"}
    return {
        "status": qa.get("status", "PENDING"),
        "artifact_status": qa.get("artifact_status"),
        "raw_hashes_equal_before_after": qa.get(
            "raw_hashes_equal_before_after"
        ),
        "actual_physical_solve_count": qa.get(
            "actual_physical_solve_count"
        ),
    }


def kcl_check(trace: Any) -> dict[str, Any]:
    inflow = trace.column("I(B_JSL8)")
    shunt = trace.column("I(R_QBIN_SHUNT)")
    lin = trace.column("I(LIN|XBQ)")
    residual = tuple(
        a - b - c for a, b, c in zip(inflow, shunt, lin)
    )
    max_abs = max(abs(value) for value in residual)
    rms = math.sqrt(
        sum(value * value for value in residual) / len(residual)
    )
    windows = {}
    for start, end in ((110.0, 121.0), (113.0, 117.0), (117.0, 121.0), (121.0, 126.0)):
        selected = [
            residual[index] for index in indices(trace, start, end)
        ]
        windows[f"[{start:g},{end:g})ps"] = {
            "max_abs_A": max(abs(value) for value in selected),
            "rms_A": math.sqrt(
                sum(value * value for value in selected) / len(selected)
            ),
            "sample_count": len(selected),
        }
    return {
        "equation": "I(B_JSL8) - I(R_QBIN_SHUNT) - I(LIN|XBQ)",
        "directions": {
            "I(B_JSL8)": "JSL_NODE7 -> QBIN",
            "I(R_QBIN_SHUNT)": "QBIN -> ground",
            "I(LIN|XBQ)": "QBIN -> QB internal node 1",
        },
        "max_abs_A": max_abs,
        "rms_A": rms,
        "windows": windows,
        "tolerance_A": KCL_TOLERANCE_A,
    }


def mechanical_qa() -> None:
    provenance = read_json(EXP / "provenance.json")
    actual_records = provenance["execution"]["run_records"]
    expected_stage_a_order = [
        run_id(point["point_id"], mask)
        for point in POINTS
        for mask in MASKS_STAGE_A
    ]
    chosen = provenance["stage_b"].get("chosen_point_id")
    stage_b_status = provenance["stage_b"].get("status")
    expected_order = list(expected_stage_a_order)
    if stage_b_status == "COMPLETE" and chosen:
        expected_order.extend(
            [run_id(chosen, mask) for mask in MASKS_STAGE_B]
        )
    failures: list[str] = []
    run_checks: dict[str, Any] = {}
    if provenance["execution"]["run_order"] != expected_order:
        failures.append("run_order")
    source_failures = []
    try:
        verify_registered_sources(provenance)
    except Exception as exc:
        source_failures.append(str(exc))
        failures.append("source_closure")

    for identifier in provenance["execution"]["run_order"]:
        record = actual_records.get(identifier, {})
        point = point_by_id(record["point_id"])
        mask = record["mask"]
        directory = run_dir(point["point_id"], mask)
        deck = directory / "deck.cir"
        raw = directory / "raw.csv"
        log = directory / "run.log"
        deck_value = deck.read_text(encoding="utf-8") if deck.is_file() else ""
        shunt_lines = [
            line.strip()
            for line in deck_value.splitlines()
            if line.strip().startswith("R_QBIN_SHUNT")
        ]
        expected_shunt = f"R_QBIN_SHUNT QBIN 0 {point['spice_value']}"
        warning_lines = [
            line.strip()
            for line in log.read_text(errors="replace").splitlines()
            if any(
                token in line
                for token in (
                    "Missing model:",
                    "Using default model",
                    "Unknown device/node",
                    "Cannot store results",
                )
            )
        ] if log.is_file() else ["missing_log"]
        unexpected = (
            sorted(
                path.name
                for path in directory.iterdir()
                if path.name not in {"deck.cir", "raw.csv", "run.log"}
            )
            if directory.is_dir()
            else ["missing_run_dir"]
        )
        try:
            trace = load_raw(raw, "XBQ", True)
            raw_qa = trace.qa()
            missing = []
        except Exception as exc:
            trace = None
            raw_qa = {}
            missing = [str(exc)]
        recorded_hash = record.get("raw", {}).get("sha256")
        hash_match = raw.is_file() and sha256(raw) == recorded_hash
        kcl = kcl_check(trace) if trace is not None else {}
        deck_ok = (
            shunt_lines == [expected_shunt]
            and ".param" not in deck_value
            and "BQ_parameterized_bjs400" not in deck_value
            and include_path(QB, directory) in deck_value
        )
        clean = bool(
            deck_ok
            and not warning_lines
            and not unexpected
            and not missing
            and hash_match
            and trace is not None
            and raw_qa.get("sample_count") == 1999
            and raw_qa.get("strictly_increasing_time") is True
            and kcl.get("max_abs_A", math.inf) <= KCL_TOLERANCE_A
        )
        if not clean:
            failures.append(identifier)
        run_checks[identifier] = {
            "status": "PASS" if clean else "ARTIFACT_INVALID",
            "point_id": point["point_id"],
            "mask": mask,
            "deck_sha256": sha256(deck) if deck.is_file() else None,
            "shunt_lines": shunt_lines,
            "expected_shunt": expected_shunt,
            "no_parameter_override": ".param" not in deck_value,
            "canonical_qb_include_present": include_path(QB, directory) in deck_value,
            "raw_sha256": sha256(raw) if raw.is_file() else None,
            "recorded_raw_sha256": recorded_hash,
            "raw_hash_match": hash_match,
            "raw_qa": raw_qa,
            "missing": missing,
            "solver_warning_lines": warning_lines,
            "unexpected_run_entries": unexpected,
            "kcl": kcl,
        }

    all_raws = [
        path for path in EXP.rglob("raw.csv")
        if "runs" not in path.relative_to(EXP).parts
    ]
    zip_files = list(EXP.rglob("*.zip"))
    if all_raws:
        failures.append("raw_reference_copy")
    if zip_files:
        failures.append("zip_in_experiment_root")
    allowed_root_files = {
        "experiment.yaml", "RESULT.md", "result.json", "provenance.json"
    }
    root_unexpected = sorted(
        path.name for path in EXP.iterdir()
        if path.is_file() and path.name not in allowed_root_files
    )
    root_unexpected_dirs = sorted(
        path.name for path in EXP.iterdir()
        if path.is_dir() and path.name not in {"runs", "plots"}
    )
    if root_unexpected or root_unexpected_dirs:
        failures.append("compact_root_layout")
    actual_count = provenance["execution"]["actual_physical_solve_count"]
    expected_count = 12 + (3 if stage_b_status == "COMPLETE" else 0)
    if actual_count != expected_count or len(run_checks) != expected_count:
        failures.append("physical_solve_count")
    raw_before = provenance.get("analysis", {}).get(
        "raw_hash_before_analysis", {}
    )
    raw_after = provenance.get("analysis", {}).get(
        "raw_hash_after_analysis", {}
    )
    raw_hashes_equal = bool(raw_before and raw_before == raw_after)
    if not raw_hashes_equal:
        failures.append("analysis_raw_hashes")
    result_size = (EXP / "result.json").stat().st_size
    if result_size >= RESULT_LIMIT_BYTES:
        failures.append("result_json_size")

    qa = {
        "schema": "bvm-qb-qbin-shunt-threshold-mechanical-qa-v1",
        "experiment_id": EXP.name,
        "generated_at": now(),
        "status": "PASS" if not failures else "FAIL",
        "artifact_status": "VALID" if not failures else "ARTIFACT_INVALID",
        "registration_head": provenance.get("registration_head"),
        "remote_bvm_master": provenance.get("remote_bvm_master"),
        "actual_physical_solve_count": actual_count,
        "expected_physical_solve_count": expected_count,
        "stage_a_order_exact": provenance["execution"]["run_order"][:12] == expected_stage_a_order,
        "stage_b_status": stage_b_status,
        "stage_b_chosen_point_id": chosen,
        "source_failures": source_failures,
        "run_checks": run_checks,
        "raw_reference_copies": [rel(path) for path in all_raws],
        "zip_files_in_experiment": [rel(path) for path in zip_files],
        "compact_root_unexpected_files": root_unexpected,
        "compact_root_unexpected_dirs": root_unexpected_dirs,
        "raw_hashes_equal_before_after": raw_hashes_equal,
        "result_json_bytes": result_size,
        "result_json_limit_bytes": RESULT_LIMIT_BYTES,
        "scientific_interpretation_performed": False,
    }
    provenance["qa"] = qa
    write_provenance(provenance)
    result = read_json(EXP / "result.json")
    result["qa_summary"] = result_qa_summary(provenance)
    write_json(EXP / "result.json", result)
    (EXP / "RESULT.md").write_text(result_markdown(result), encoding="utf-8")
    if failures:
        raise RuntimeError(
            f"mechanical QA failed; artifact status ARTIFACT_INVALID: {failures}"
        )
    print(json.dumps({
        "status": "PASS",
        "actual_physical_solve_count": actual_count,
        "stage_b_status": stage_b_status,
        "result_json_bytes": (EXP / "result.json").stat().st_size,
    }, ensure_ascii=False, indent=2))


def plotter_html(input_path: Path, output_path: Path, subset: list[str], title: str) -> None:
    command = [
        sys.executable,
        str(PLOTTER),
        str(input_path),
        "-x",
        str(output_path),
        "-t",
        "sep_comb",
        "-c",
        "dark",
        "-j",
        "2pi",
        "-w",
        title,
        "-s",
        *subset,
    ]
    completed = subprocess.run(
        command, cwd=REPO, capture_output=True, text=True, check=False
    )
    if (
        completed.returncode != 0
        or not output_path.is_file()
        or output_path.stat().st_size == 0
    ):
        raise RuntimeError(
            f"josim-plot2 failed for {output_path}: {completed.stderr[-1000:]}"
        )


def externalize_plotly_runtime(
    temporary_html: Path,
    output_html: Path,
    asset_path: Path,
) -> None:
    html = temporary_html.read_text(encoding="utf-8")
    blocks = list(
        re.finditer(
            r"<script(?P<attrs>[^>]*)>(?P<body>.*?)</script>",
            html,
            flags=re.DOTALL,
        )
    )
    runtime = None
    for match in blocks:
        body = match.group("body")
        if len(body) > 1_000_000 and (
            "plotly.js v" in body or "var Plotly=" in body
        ):
            runtime = match
            break
    if runtime is None:
        raise RuntimeError(
            f"could not find embedded Plotly runtime in {temporary_html}"
        )
    runtime_body = runtime.group("body")
    asset_path.parent.mkdir(parents=True, exist_ok=True)
    if asset_path.exists():
        existing = asset_path.read_text(encoding="utf-8")
        if existing != runtime_body:
            raise RuntimeError("Plotly runtime differs between generated pages")
    else:
        asset_path.write_text(runtime_body, encoding="utf-8")
    relative_asset = Path(
        os.path.relpath(asset_path, output_html.parent)
    ).as_posix()
    replacement = f'<script src="{relative_asset}"></script>'
    compact_html = html[: runtime.start()] + replacement + html[runtime.end() :]
    if "plotly.js v" in compact_html or "var Plotly=" in compact_html:
        raise RuntimeError("embedded Plotly runtime was not fully externalized")
    if "cdn.plot.ly" in compact_html:
        raise RuntimeError("CDN Plotly reference remains after externalization")
    output_html.parent.mkdir(parents=True, exist_ok=True)
    output_html.write_text(compact_html, encoding="utf-8")


def render_external_page(
    input_path: Path,
    output_path: Path,
    subset: list[str],
    title: str,
    asset_path: Path,
) -> None:
    if output_path.exists():
        html = output_path.read_text(encoding="utf-8")
        relative_asset = Path(
            os.path.relpath(asset_path, output_path.parent)
        ).as_posix()
        if (
            relative_asset not in html
            or "plotly.js v" in html
            or "var Plotly=" in html
            or "cdn.plot.ly" in html
        ):
            raise RuntimeError(f"existing plot is not a valid external-runtime page: {output_path}")
        return
    handle = tempfile.NamedTemporaryFile(
        prefix="josim_qbin_threshold_",
        suffix=".html",
        delete=False,
        dir="/tmp",
    )
    temporary = Path(handle.name)
    handle.close()
    try:
        plotter_html( input_path, temporary, subset, title)
        externalize_plotly_runtime(temporary, output_path, asset_path)
    finally:
        temporary.unlink(missing_ok=True)


def prefixed_signal(case: str, signal: str) -> str:
    if len(signal) < 3 or signal[1] != "(" or not signal.endswith(")"):
        raise ValueError(signal)
    return f"{signal[0]}({case}|{signal[2:-1]})"


def endpoint_mapper(instance: str) -> Callable[[str], str]:
    def mapper(signal: str) -> str:
        return signal.replace("|XBQ)", f"|{instance})")
    return mapper


def comparison_csv(
    cases: list[tuple[str, Path, str, Callable[[str], str]]],
    signals: Iterable[str],
) -> tuple[Path, list[str]]:
    signal_list = list(signals)
    traces: list[tuple[str, Any, Callable[[str], str]]] = []
    for case, raw, _instance, mapper in cases:
        trace = load_raw(raw, _instance, False)
        traces.append((case, trace, mapper))
    base_time = traces[0][1].time
    if any(trace.time != base_time for _, trace, _ in traces[1:]):
        raise RuntimeError("comparison raw grids do not match")
    labels: list[str] = []
    columns: list[list[float]] = []
    for case, trace, mapper in traces:
        for signal in signal_list:
            mapped = mapper(signal)
            if mapped in trace.headers:
                labels.append(prefixed_signal(case, signal))
                columns.append(list(trace.column(mapped)))
    if not columns:
        raise RuntimeError("comparison has no common signals")
    handle = tempfile.NamedTemporaryFile(
        prefix="bvm_qbin_threshold_compare_",
        suffix=".csv",
        delete=False,
        dir="/tmp",
    )
    path = Path(handle.name)
    handle.close()
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["time", *labels])
        for index, timestamp in enumerate(base_time):
            writer.writerow([
                f"{timestamp:.17e}",
                *(f"{column[index]:.17e}" for column in columns),
            ])
    return path, labels


def case_catalog(
    provenance: dict[str, Any],
) -> dict[str, tuple[str, Path, str, Callable[[str], str]]]:
    catalog: dict[str, tuple[str, Path, str, Callable[[str], str]]] = {}
    for mask in MASKS_STAGE_A:
        catalog[f"open_N{2 if mask == '0011' else 3}"] = (
            f"open_N{2 if mask == '0011' else 3}",
            OPEN_RAW[mask],
            "XBQ1",
            endpoint_mapper("XBQ1"),
        )
        catalog[f"r20_N{2 if mask == '0011' else 3}"] = (
            f"r20_N{2 if mask == '0011' else 3}",
            R20_RAW[mask],
            "XBQ",
            endpoint_mapper("XBQ"),
        )
    for identifier in provenance["execution"]["run_order"]:
        record = provenance["execution"]["run_records"][identifier]
        label = (
            f"{record['point_id']}_N{2 if record['mask'] == '0011' else 3}"
            if record["mask"] in MASKS_STAGE_A
            else f"{record['point_id']}_{record['mask']}"
        )
        catalog[label] = (
            label,
            REPO / record["raw"]["path"],
            "XBQ",
            endpoint_mapper("XBQ"),
        )
    return catalog


def visualization() -> None:
    provenance = read_json(EXP / "provenance.json")
    if provenance.get("qa", {}).get("status") != "PASS":
        raise RuntimeError("mechanical QA must pass before visualization")
    asset = EXP / "plots" / "assets" / "plotly.min.js"
    sets = metric_signal_sets_for_viz()
    entries: list[dict[str, Any]] = []
    run_records = provenance["execution"]["run_records"]
    for identifier in provenance["execution"]["run_order"]:
        record = run_records[identifier]
        point_id = record["point_id"]
        mask = record["mask"]
        raw = REPO / record["raw"]["path"]
        trace = load_raw(raw, "XBQ", True)
        view_specs = visualization_views(trace.headers)
        for view, (signals, note) in view_specs.items():
            output = EXP / "plots" / point_id / mask / f"{view}.html"
            render_external_page(
                raw,
                output,
                signals,
                f"{EXP.name} | {point_id} | mask={mask} | {view} | raw 0-200 ps | {note}",
                asset,
            )
            entries.append({
                "kind": "standalone",
                "run_id": identifier,
                "path": rel(output),
                "raw_path": rel(raw),
                "raw_sha256": sha256(raw),
                "view": view,
                "signals": signals,
                "window_ps": [0.0, 200.0],
                "direction_note": note,
                "renderer": {"path": rel(PLOTTER), "sha256": sha256(PLOTTER)},
            })

    catalog = case_catalog(provenance)
    comparisons: list[tuple[str, list[tuple[str, Path, str, Callable[[str], str]]], list[str], str]] = []
    all_threshold_cases = list(catalog.values())
    comparisons.append((
        "comparison_threshold_boundary",
        all_threshold_cases,
        sets["boundary_compare"],
        "conductance threshold boundary: V(QBIN), I(B_JSL8), I(LIN|XBQ)",
    ))
    stage_a_cases = [
        value for key, value in catalog.items()
        if not key.startswith("open_") and not key.startswith("r20_")
        and any(key.startswith(point["point_id"] + "_") for point in POINTS)
    ]
    comparisons.append((
        "comparison_threshold_shunt",
        stage_a_cases,
        sets["shunt_compare"],
        "conductance threshold shunt partition: I(B_JSL8), I(R_QBIN_SHUNT), I(LIN|XBQ)",
    ))
    comparisons.append((
        "comparison_threshold_qb",
        all_threshold_cases,
        sets["qb_compare"],
        "conductance threshold QB navigation and L1",
    ))
    comparisons.append((
        "comparison_threshold_bvm",
        all_threshold_cases,
        sets["bvm_compare"],
        "conductance threshold BVM source navigation at common XBVM3",
    ))
    chosen = provenance["stage_b"].get("chosen_point_id")
    if chosen and provenance["stage_b"].get("status") == "COMPLETE":
        population_cases = [
            (
                f"{chosen}_{mask}",
                REPO / provenance["execution"]["run_records"][run_id(chosen, mask)]["raw"]["path"],
                "XBQ",
                endpoint_mapper("XBQ"),
            )
            for mask in ALL_MASKS
            if run_id(chosen, mask) in provenance["execution"]["run_records"]
        ]
        comparisons.append((
            f"comparison_{chosen}_population",
            population_cases,
            sets["population_compare"],
            f"chosen {chosen} population map: 0000/0001/0011/0111/1111",
        ))

    comparison_entries: list[dict[str, Any]] = []
    comparison_dir = EXP / "plots" / "comparisons"
    comparison_dir.mkdir(parents=True, exist_ok=True)
    for stem, cases, signals, note in comparisons:
        temp_csv, labels = comparison_csv(cases, signals)
        output = comparison_dir / f"{stem}.html"
        try:
            render_external_page(
                temp_csv,
                output,
                labels,
                f"{EXP.name} | {note} | full raw 0-200 ps | P display rad/(2*pi)",
                asset,
            )
        finally:
            temp_csv.unlink(missing_ok=True)
        comparison_entries.append({
            "kind": "comparison",
            "comparison": stem,
            "path": rel(output),
            "source_cases": [
                {"case": case, "raw_path": rel(raw), "raw_sha256": sha256(raw)}
                for case, raw, _instance, _mapper in cases
            ],
            "signals": signals,
            "rendered_labels": labels,
            "window_ps": [0.0, 200.0],
            "full_window_only": True,
            "direction_note": note,
            "renderer": {"path": rel(PLOTTER), "sha256": sha256(PLOTTER)},
        })

    html_files = sorted(
        path for path in (EXP / "plots").rglob("*")
        if path.is_file() and path.suffix.lower() == ".html"
    )
    invalid_pages = []
    for path in html_files:
        html = path.read_text(encoding="utf-8")
        asset_ref = Path(os.path.relpath(asset, path.parent)).as_posix()
        if (
            asset_ref not in html
            or "plotly.js v" in html
            or "var Plotly=" in html
            or "cdn.plot.ly" in html
        ):
            invalid_pages.append(rel(path))
    non_html_plot_files = [
        rel(path) for path in (EXP / "plots").rglob("*")
        if path.is_file() and path.suffix.lower() not in {".html", ".js"}
    ]
    viz_qa = {
        "status": "PASS" if asset.is_file() and not invalid_pages and not non_html_plot_files else "FAIL",
        "asset": {"path": rel(asset), "sha256": sha256(asset) if asset.is_file() else None, "bytes": asset.stat().st_size if asset.is_file() else None},
        "standalone_count": len(entries),
        "comparison_count": len(comparison_entries),
        "html_count": len(html_files),
        "invalid_pages": invalid_pages,
        "non_html_plot_files": non_html_plot_files,
        "full_window_only": True,
        "focused_pages": [],
        "no_png_svg_pdf": True,
        "shared_runtime": True,
        "raw_hashes_rechecked": all(
            item["raw_sha256"] == sha256(REPO / item["raw_path"])
            for item in entries
        ),
        "scientific_interpretation_performed": False,
    }
    provenance["visualization"] = {
        "status": viz_qa["status"],
        "renderer": {"path": rel(PLOTTER), "sha256": sha256(PLOTTER), "layout": "sep_comb", "color": "dark", "phase_option": "2pi"},
        "asset": viz_qa["asset"],
        "standalone_pages": entries,
        "comparison_pages": comparison_entries,
        "full_window_only": True,
        "focused_pages": [],
        "shared_runtime": True,
        "scientific_interpretation_performed": False,
    }
    provenance["visualization_qa"] = viz_qa
    write_provenance(provenance)
    result = read_json(EXP / "result.json")
    result["visualization_summary"] = {
        "status": viz_qa["status"],
        "standalone_count": len(entries),
        "comparison_count": len(comparison_entries),
        "html_count": len(html_files),
        "shared_asset": rel(asset),
        "focused_pages": [],
        "no_png_svg_pdf": True,
    }
    write_json(EXP / "result.json", result)
    (EXP / "RESULT.md").write_text(result_markdown(result), encoding="utf-8")
    if viz_qa["status"] != "PASS":
        raise RuntimeError("visualization QA failed")
    print(json.dumps({
        "status": "PASS",
        "standalone_html": len(entries),
        "comparison_html": len(comparison_entries),
        "shared_asset": rel(asset),
    }, ensure_ascii=False, indent=2))


def visualization_views(headers: Iterable[str]) -> dict[str, tuple[list[str], str]]:
    available = set(headers)
    bvm_phase = [
        f"P(B_{element}|XBVM{index})"
        for index in range(1, 5)
        for element in ("JM1", "JM2", "JS1", "JS2")
    ]
    bvm_currents = [
        f"I(I_{kind}{index})"
        for index in range(1, 5)
        for kind in ("WL", "BL", "SE")
    ] + [
        f"I({element}|XBVM{index})"
        for index in range(1, 5)
        for element in (
            "L_M1", "L_M2", "L_M3", "L_S1",
            "L_S2", "L_S3", "L_PSL", "L_SL",
        )
    ]
    common_jsl = ["V(COMMON_SL)"] + [
        signal
        for index in range(1, 9)
        for signal in (
            f"P(B_JSL{index})",
            f"V(B_JSL{index})",
            f"I(B_JSL{index})",
        )
    ]
    qbin = [
        "V(COMMON_SL)",
        "V(QBIN)",
        "I(B_JSL8)",
        "I(R_QBIN_SHUNT)",
        "I(LIN|XBQ)",
    ]
    qb = [
        "I(LIN|XBQ)", "V(LIN|XBQ)",
        "I(L1|XBQ)", "V(L1|XBQ)",
        "I(L2|XBQ)", "V(L2|XBQ)",
        "I(L3|XBQ)", "V(L3|XBQ)",
        "I(RJ1|XBQ)", "V(RJ1|XBQ)",
        "I(RJ2|XBQ)", "V(RJ2|XBQ)",
        "P(BJS|XBQ)", "V(BJS|XBQ)", "I(BJS|XBQ)",
        "P(BJ1|XBQ)", "V(BJ1|XBQ)", "I(BJ1|XBQ)",
        "P(BJ2|XBQ)", "V(BJ2|XBQ)", "I(BJ2|XBQ)",
        "V(QBOUT)",
    ]
    jtl = [
        signal
        for index in range(1, 7)
        for signal in (
            f"P(B01|XJTL1_{index})",
            f"V(B01|XJTL1_{index})",
            f"I(B01|XJTL1_{index})",
            f"P(B02|XJTL1_{index})",
            f"V(B02|XJTL1_{index})",
            f"I(B02|XJTL1_{index})",
            f"V(JTL{index}_OUT)",
        )
    ]
    terminal = ["V(QBOUT)", "V(JTL6_OUT)", "I(R_TERM)"]
    specs = {
        "01_bvm_phase": (bvm_phase, "BVM phase state; raw radians and rad/(2*pi) navigation"),
        "02_bvm_currents": (bvm_currents, "BVM source and branch currents; netlist directions"),
        "03_common_jsl": (common_jsl, "COMMON_SL -> JSL1..8 -> QBIN raw chain"),
        "04_qbin_boundary": (qbin, "B_JSL8 JSL_NODE7->QBIN; shunt QBIN->ground; LIN QBIN->QB node1"),
        "05_qb": (qb, "QB P/V/I and branch currents; phase navigation only"),
        "06_jtl": (jtl, "JTL1..6 B01/B02 P/V/I and stage outputs"),
        "07_terminal": (terminal, "QBOUT -> JTL6_OUT -> R_TERM; terminal current to ground"),
    }
    output: dict[str, tuple[list[str], str]] = {}
    for name, (signals, note) in specs.items():
        missing = [signal for signal in signals if signal not in available]
        if missing:
            raise RuntimeError(f"missing visualization signals for {name}: {missing}")
        output[name] = (signals, note)
    return output


def metric_signal_sets_for_viz() -> dict[str, list[str]]:
    return {
        "boundary_compare": [
            "V(QBIN)", "I(B_JSL8)", "I(LIN|XBQ)"
        ],
        "shunt_compare": [
            "I(B_JSL8)", "I(R_QBIN_SHUNT)", "I(LIN|XBQ)"
        ],
        "qb_compare": [
            "P(BJ1|XBQ)", "P(BJ2|XBQ)", "I(L1|XBQ)", "V(QBOUT)"
        ],
        "bvm_compare": [
            "P(B_JS1|XBVM3)", "P(B_JS2|XBVM3)", "I(L_SL|XBVM3)"
        ],
        "population_compare": [
            "P(BJ1|XBQ)", "P(BJ2|XBQ)", "V(JTL6_OUT)", "I(R_TERM)"
        ],
    }


def package() -> None:
    provenance = read_json(EXP / "provenance.json")
    if provenance.get("qa", {}).get("status") != "PASS":
        raise RuntimeError("mechanical QA must pass before packaging")
    if provenance.get("visualization", {}).get("status") != "PASS":
        raise RuntimeError("visualization QA must pass before packaging")
    delivery_dir = Path("/mnt/d/BVM_Backages")
    delivery_dir.mkdir(parents=True, exist_ok=True)
    package_path = delivery_dir / f"{EXP.name}_raw_evidence.zip"
    if package_path.exists():
        raise RuntimeError(f"refusing overwrite of existing delivery ZIP: {package_path}")

    files: list[tuple[Path, str]] = []
    for name in ("experiment.yaml", "RESULT.md", "result.json", "provenance.json"):
        path = EXP / name
        if not path.is_file():
            raise RuntimeError(f"missing package root file: {path}")
        files.append((path, path.relative_to(EXP).as_posix()))
    for path in sorted((EXP / "runs").rglob("*")):
        if path.is_file():
            files.append((path, path.relative_to(EXP).as_posix()))
    for path in sorted((EXP / "plots").rglob("*")):
        if path.is_file():
            files.append((path, path.relative_to(EXP).as_posix()))

    records = [
        {
            "path": archive_name,
            "sha256": sha256(path),
            "bytes": path.stat().st_size,
        }
        for path, archive_name in files
    ]
    with zipfile.ZipFile(
        package_path,
        "x",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=6,
    ) as archive:
        for path, archive_name in files:
            archive.write(path, archive_name)
    with zipfile.ZipFile(package_path, "r") as archive:
        reopened = {
            name: hashlib.sha256(archive.read(name)).hexdigest()
            for name in archive.namelist()
        }
    expected = {record["path"]: record["sha256"] for record in records}
    package_qa = {
        "status": "PASS" if expected == reopened else "FAIL",
        "package_path": str(package_path),
        "package_sha256": sha256(package_path),
        "package_bytes": package_path.stat().st_size,
        "file_count": len(records),
        "expected_file_hashes_match_after_reopen": expected == reopened,
        "zip_files": records,
        "not_in_git": True,
        "no_reference_raw_copy": True,
        "git_commit_at_package": git_head(),
        "remote_head_at_package": remote_head(),
    }
    provenance["package"] = {
        "status": "READY_FOR_DRIVE_UPLOAD" if package_qa["status"] == "PASS" else "PACKAGE_INVALID",
        "qa": package_qa,
        "delivery_path": str(package_path),
        "drive_file_id": None,
        "drive_url": None,
    }
    write_provenance(provenance)
    if package_qa["status"] != "PASS":
        raise RuntimeError("package reopen QA failed")
    print(json.dumps({
        "status": "PASS",
        "package_path": str(package_path),
        "sha256": package_qa["package_sha256"],
        "bytes": package_qa["package_bytes"],
        "files": package_qa["file_count"],
        "not_in_git": True,
    }, ensure_ascii=False, indent=2))


def record_drive_upload(file_id: str, url: str | None = None) -> None:
    provenance = read_json(EXP / "provenance.json")
    package_info = provenance.get("package", {})
    package_qa = package_info.get("qa", {})
    package_path = Path(package_info.get("delivery_path", ""))
    if not package_path.is_file():
        raise RuntimeError("delivery ZIP is missing; cannot record Drive upload")
    if sha256(package_path) != package_qa.get("package_sha256"):
        raise RuntimeError("delivery ZIP changed before Drive upload record")
    package_info["drive_file_id"] = file_id
    package_info["drive_url"] = url
    package_info["drive_uploaded_at"] = now()
    package_info["status"] = "UPLOADED"
    provenance["package"] = package_info
    write_provenance(provenance)
    print(json.dumps({
        "status": "UPLOADED",
        "drive_file_id": file_id,
        "drive_url": url,
        "package_sha256": package_qa.get("package_sha256"),
    }, ensure_ascii=False, indent=2))


def main() -> int:
    command = sys.argv[1] if len(sys.argv) > 1 else "all"
    if command == "prepare":
        prepare()
    elif command == "repair-tool":
        repair_tool_provenance()
    elif command == "execute":
        execute()
    elif command == "analyze":
        analyze()
    elif command == "qa":
        mechanical_qa()
    elif command == "viz":
        visualization()
    elif command == "package":
        package()
    elif command == "drive-record":
        if len(sys.argv) < 3:
            print("usage: bvm_qb_qbin_shunt_threshold.py drive-record FILE_ID [URL]", file=sys.stderr)
            return 2
        record_drive_upload(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
    elif command == "all":
        prepare()
        execute()
        mechanical_qa()
        visualization()
    else:
        print(
            "usage: bvm_qb_qbin_shunt_threshold.py "
            "[prepare|repair-tool|execute|analyze|qa|viz|package|drive-record|all]",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
