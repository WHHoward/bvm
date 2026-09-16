#!/usr/bin/env python3
"""Bounded BVM R-loop bridge causality experiment.

This runner keeps the canonical BVM source immutable.  Each candidate deck
embeds an experiment-local BVM subcircuit variant with exactly one textual
change: L_S3.  The physical solve matrix is exactly six Stage A cases.  A
later Stage B is review-gated because its mechanism-success predicate is
qualitative and no scientific-review authorization token is present.
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
EXP = REPO / "test" / "exploration" / "bvm-qb-rloop-ls3-causality-v1-20260916"

SOLVER = REPO / "build" / "josim-cli"
PLOTTER = REPO / "scripts" / "josim-plot2.py"
MODEL = REPO / "circuits" / "models" / "jjmit.cir"
QB = REPO / "circuits" / "qb" / "bq_parameterized_v1.cir"
BVM = REPO / "test" / "exploration" / "bvm-population-scaling-rj2p12-l1p14-l2p20-ib260-rj32-bjs400-v1-20260910" / "inputs" / "bvm_jm2_connected.cir"
JTL = REPO / "test" / "exploration" / "bvm-population-scaling-rj2p12-l1p14-l2p20-ib260-rj32-bjs400-v1-20260910" / "inputs" / "jtl2.cir"

R20_ROOT = REPO / "test" / "exploration" / "bvm-qb-qbin-shunt-r20-v1-20260914" / "runs"
R20_RAW = {"0011": R20_ROOT / "0011" / "raw.csv", "0111": R20_ROOT / "0111" / "raw.csv"}
R20_DECK = {"0011": R20_ROOT / "0011" / "deck.cir", "0111": R20_ROOT / "0111" / "deck.cir"}
EXPECTED_R20_RAW_SHA256 = {
    "0011": "778469a262b3252e696c811ec371c82fa77d6b7a89fa7ea411746783bcf8cb9d",
    "0111": "88784cded8137affe353a24a9fc78665c34d3484ead835d178ae87af719bf77e",
}

MASKS_STAGE_A = ("0011", "0111")
MASKS_STAGE_B = ("0000", "0001", "1111")
ALL_MASKS = ("0000", "0001", "0011", "0111", "1111")
LS3_POINTS = (
    {"point_id": "ls3_0p75", "label": "0.75", "value_pH": 0.75, "spice_value": "0.75P"},
    {"point_id": "ls3_1p00", "label": "1.00", "value_pH": 1.00, "spice_value": "1.00P"},
    {"point_id": "ls3_1p50", "label": "1.50", "value_pH": 1.50, "spice_value": "1.50P"},
)
POINT_BY_ID = {item["point_id"]: item for item in LS3_POINTS}
WINDOWS_PS = (
    (101.0, 110.0),
    (110.0, 113.0),
    (113.0, 115.0),
    (115.0, 117.0),
    (117.0, 121.0),
    (121.0, 126.0),
    (126.0, 140.0),
    (140.0, 200.0),
)
PHASE_THRESHOLDS = (0.5, 1.5, 2.5, 3.5, 4.5)
PHI0 = 2.067833848e-15
KCL_TOLERANCE_A = 1.0e-9
DIV_PHASE_THRESHOLD_TURNS = 0.10
DIV_CURRENT_THRESHOLD_A = 5.0e-6
DIV_VOLTAGE_THRESHOLD_V = 50.0e-6
RESULT_LIMIT_BYTES = 500 * 1024
FINAL_MARKER = "EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW"
CONTRACT_SENTENCE = "This experiment is governed by docs/EXPERIMENT_CONTRACT.md."

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
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return value


def git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()


def git_status() -> str:
    return subprocess.check_output(["git", "status", "--short", "--untracked-files=all"], cwd=REPO, text=True).strip()


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
        "version": subprocess.check_output([str(SOLVER), "--version"], cwd=REPO, text=True).strip(),
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
        record_file("runner", SCRIPT, "shared runner and registered scalar/cause chronology arithmetic"),
        record_file("global_jjmit_model", MODEL, "global model closure"),
        record_file("canonical_qb", QB, "canonical QB source; no parameter override"),
        record_file("canonical_bvm_template", BVM, "immutable BVM source template for experiment-local L_S3 variants"),
        record_file("canonical_jtl", JTL, "immutable JTL source instantiated six times"),
        record_file("josim_solver", SOLVER, "recorded physical solver"),
        record_file("plotter", PLOTTER, "standard JoSIM descriptive renderer"),
        record_file("shared_raw_reader", REPO / "scripts" / "bvmtools" / "raw.py", "duplicate-aware raw reader"),
        record_file("shared_phase_tools", REPO / "scripts" / "bvmtools" / "phase.py", "continuous phase unwrap and windows"),
        record_file("shared_waveform_tools", REPO / "scripts" / "bvmtools" / "waveform.py", "actual-grid waveform tools"),
    ]


def endpoint_inventory() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for mask in MASKS_STAGE_A:
        records.append(record_file(f"r20_{mask}_raw", R20_RAW[mask], "read-only canonical L_S3=0.5pH endpoint raw; not copied"))
        records.append(record_file(f"r20_{mask}_deck", R20_DECK[mask], "read-only canonical endpoint deck; not copied"))
    return records


def assert_sources() -> None:
    if remote_head() != git_head():
        raise RuntimeError("bvm/master is not equal to current HEAD")
    for path, expected in EXPECTED_SOURCE_SHA256.items():
        if not path.is_file() or sha256(path) != expected:
            raise RuntimeError(f"registered source changed or is missing: {path}")
    for mask in MASKS_STAGE_A:
        if sha256(R20_RAW[mask]) != EXPECTED_R20_RAW_SHA256[mask]:
            raise RuntimeError(f"R20 endpoint raw changed: {R20_RAW[mask]}")


def load_canonical_bvm_variant(value_pH: float, spice_value: str | None = None) -> tuple[str, str]:
    original = BVM.read_text(encoding="utf-8")
    pattern = re.compile(r"(?m)^(L_S3[ \t]+6[ \t]+10[ \t]+)0\.5P([ \t]*)$")
    token = spice_value or f"{value_pH:g}P"
    replacement = rf"\g<1>{token}\g<2>"
    variant, count = pattern.subn(replacement, original)
    if count != 1:
        raise RuntimeError(f"canonical BVM L_S3 line count is {count}, expected 1")
    changed = [
        (before, after)
        for before, after in zip(original.splitlines(), variant.splitlines())
        if before != after
    ]
    if len(changed) != 1 or not changed[0][0].lstrip().startswith("L_S3"):
        raise RuntimeError(f"unexpected BVM variant diff: {changed}")
    return variant, sha256_text(variant)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


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
            "L_M1", "L_M2", "L_M3", "L_PM",
            "L_S1", "L_S2", "L_S3", "R_S",
            "L_PSL", "R_SL", "L_SL",
        ):
            lines.append(f".print I({element}|XBVM{index}) V({element}|XBVM{index})")
    lines.append(".print V(COMMON_SL)")
    for index in range(1, 9):
        lines.append(f".print P(B_JSL{index}) V(B_JSL{index}) I(B_JSL{index})")
    lines += [
        ".print V(QBIN)",
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


def deck_text(point: dict[str, Any], mask: str, deck_dir: Path) -> tuple[str, str]:
    variant, variant_hash = load_canonical_bvm_variant(point["value_pH"], point["spice_value"])
    lines = [
        f"* REGISTERED BVM R-loop bridge causality candidate; point={point['point_id']}; mask={mask}",
        "* Experiment-local BVM variant differs from canonical source only at L_S3.",
        "* P(...) is raw phase in radians; phase turns are navigation only.",
        f".include {include_path(MODEL, deck_dir)}",
        f".include {include_path(QB, deck_dir)}",
        f".include {include_path(JTL, deck_dir)}",
        "",
        variant.rstrip(),
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
    return "\n".join(lines), variant_hash


def expected_headers(instance: str = "XBQ") -> set[str]:
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
            "L_M1", "L_M2", "L_M3", "L_PM",
            "L_S1", "L_S2", "L_S3", "R_S",
            "L_PSL", "R_SL", "L_SL",
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
    required.update({"V(QBIN)", "I(B_JSL8)", "V(QBOUT)", "I(R_TERM)"})
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
        instance_name = f"XJTL1_{index}"
        for element in ("B01", "B02"):
            required.update(
                f"{kind}({element}|{instance_name})"
                for kind in ("P", "V", "I")
            )
        required.add(f"V(JTL{index}_OUT)")
    return required


def endpoint_headers(instance: str = "XBQ") -> set[str]:
    required = expected_headers(instance)
    for index in range(1, 5):
        for element in ("L_PM", "L_S1", "L_S2", "L_S3", "R_S", "R_SL"):
            for kind in ("I", "V"):
                required.discard(f"{kind}({element}|XBVM{index})")
    return required


def load_raw(
    path: Path,
    instance: str = "XBQ",
    endpoint: bool = False,
) -> Any:
    sys.path.insert(0, str(SCRIPT.parent))
    from bvmtools.raw import read_csv

    trace = read_csv(path)
    if trace.duplicate_columns:
        raise RuntimeError(f"duplicate raw columns: {path}: {trace.duplicate_columns}")
    required = endpoint_headers(instance) if endpoint else expected_headers(instance)
    missing = sorted(required - set(trace.headers))
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
        index for index, value in enumerate(trace.time)
        if start_ps <= value * 1.0e12 < end_ps
    ]


def actual_integral(
    trace: Any,
    values: Iterable[float],
    start_ps: float,
    end_ps: float,
) -> float:
    selected = indices(trace, start_ps, end_ps)
    values_list = list(values)
    return sum(
        0.5
        * (values_list[left] + values_list[right])
        * (trace.time[right] - trace.time[left])
        for left, right in zip(selected, selected[1:])
    )


def window_stats(
    trace: Any,
    signal: str,
    start_ps: float,
    end_ps: float,
) -> dict[str, Any]:
    values = trace.column(signal)
    selected = indices(trace, start_ps, end_ps)
    if len(selected) < 2:
        return {
            "status": "UNKNOWN",
            "signal": signal,
            "window_ps": [start_ps, end_ps],
            "reason": "fewer than two stored samples",
        }
    chosen = [values[index] for index in selected]
    peak_index = max(selected, key=lambda index: abs(values[index]))
    absolute_values = [abs(value) for value in values]
    return {
        "status": "DERIVED",
        "signal": signal,
        "window_ps": [start_ps, end_ps],
        "sample_count": len(selected),
        "unit": "A" if signal.startswith("I(") else "V",
        "minimum": min(chosen),
        "maximum": max(chosen),
        "range": max(chosen) - min(chosen),
        "mean": sum(chosen) / len(chosen),
        "peak_abs": abs(values[peak_index]),
        "time_of_peak_abs_ps": trace.time[peak_index] * 1.0e12,
        "signed_area": actual_integral(trace, values, start_ps, end_ps),
        "absolute_area": actual_integral(
            trace, absolute_values, start_ps, end_ps
        ),
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
        (unwrapped[index] - unwrapped[base]) / (2.0 * math.pi)
        for index in range(base, len(unwrapped))
    ]
    read = indices(trace, 110.0, 121.0)
    read_relative = [
        (unwrapped[index] - unwrapped[read[0]]) / (2.0 * math.pi)
        for index in read
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


def sign_change_times(
    trace: Any,
    signal: str,
    start_ps: float = 110.0,
    end_ps: float = 130.0,
) -> list[dict[str, Any]]:
    values = trace.column(signal)
    selected = indices(trace, start_ps, end_ps)
    changes: list[dict[str, Any]] = []
    for left, right in zip(selected, selected[1:]):
        if values[left] == 0.0:
            continue
        if values[left] * values[right] < 0.0:
            changes.append({
                "time_ps": trace.time[right] * 1.0e12,
                "from_sign": "positive" if values[left] > 0 else "negative",
                "to_sign": "positive" if values[right] > 0 else "negative",
            })
    return changes[:12]


def phase_area_crosscheck(
    trace: Any,
    phase_signal: str,
    voltage_signal: str,
    start_ps: float = 110.0,
    end_ps: float = 121.0,
) -> dict[str, Any]:
    from bvmtools.phase import continuous_unwrap

    selected = indices(trace, start_ps, end_ps)
    unwrapped = continuous_unwrap(trace.column(phase_signal))
    delta_rad = unwrapped[selected[-1]] - unwrapped[selected[0]]
    area = actual_integral(
        trace, trace.column(voltage_signal), start_ps, end_ps
    )
    return {
        "phase_signal": phase_signal,
        "voltage_signal": voltage_signal,
        "window_ps": [start_ps, end_ps],
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


def kcl_metrics(trace: Any, instance: str = "XBQ") -> dict[str, Any]:
    inflow = trace.column("I(B_JSL8)")
    bridge = trace.column(f"I(LIN|{instance})")
    residual = tuple(
        value - bridge[index]
        for index, value in enumerate(inflow)
    )
    # R_S and L_S3 are internal to each BVM; their shared boundary KCL is
    # recorded separately per active cell through branch partition metrics.
    return {
        "equation": "I(B_JSL8) - I(LIN|XBQ)",
        "directions": {
            "I(B_JSL8)": "JSL_NODE7 -> QBIN",
            "I(LIN|XBQ)": "QBIN -> QB internal node 1",
        },
        "residual_unit": "A",
        "max_abs_A": max(abs(value) for value in residual),
        "rms_A": math.sqrt(
            sum(value * value for value in residual) / len(residual)
        ),
        "window_110_121": window_stats_from_values(
            trace.time, residual, 110.0, 121.0, "A"
        ),
    }


def window_stats_from_values(
    times: tuple[float, ...],
    values: Iterable[float],
    start_ps: float,
    end_ps: float,
    unit: str,
) -> dict[str, Any]:
    values_list = list(values)
    selected = [
        index for index, value in enumerate(times)
        if start_ps <= value * 1.0e12 < end_ps
    ]
    if len(selected) < 2:
        return {
            "status": "UNKNOWN",
            "window_ps": [start_ps, end_ps],
            "unit": unit,
        }
    area = sum(
        0.5
        * (values_list[left] + values_list[right])
        * (times[right] - times[left])
        for left, right in zip(selected, selected[1:])
    )
    chosen = [values_list[index] for index in selected]
    return {
        "status": "DERIVED",
        "window_ps": [start_ps, end_ps],
        "unit": unit,
        "sample_count": len(selected),
        "minimum": min(chosen),
        "maximum": max(chosen),
        "mean": sum(chosen) / len(chosen),
        "peak_abs": max(abs(value) for value in chosen),
        "signed_area": area,
        "absolute_area": sum(
            0.5
            * (abs(values_list[left]) + abs(values_list[right]))
            * (times[right] - times[left])
            for left, right in zip(selected, selected[1:])
        ),
    }


def branch_partition_metrics(trace: Any, mask: str) -> dict[str, Any]:
    cells: dict[str, Any] = {}
    for index in active_indices(mask):
        branch_windows: dict[str, Any] = {}
        for start, end in (
            (110.0, 113.0),
            (113.0, 115.0),
            (115.0, 117.0),
            (117.0, 121.0),
            (121.0, 126.0),
        ):
            key = f"[{start:g},{end:g})ps"
            ls3 = window_stats(
                trace, f"I(L_S3|XBVM{index})", start, end
            )
            rs = window_stats(
                trace, f"I(R_S|XBVM{index})", start, end
            )
            denominator = ls3["absolute_area"] + rs["absolute_area"]
            fraction = (
                {
                    "status": "DERIVED",
                    "value": ls3["absolute_area"] / denominator,
                }
                if denominator > 1.0e-30
                else {
                    "status": "UNDEFINED",
                    "reason": "registered activity denominator guard",
                }
            )
            branch_windows[key] = {
                "I_LS3": ls3,
                "I_RS": rs,
                "fast_bridge_fraction": fraction,
            }
        cells[f"XBVM{index}"] = branch_windows
    return {
        "active_cells": [f"XBVM{index}" for index in active_indices(mask)],
        "branch_endpoints": {
            "R_S_and_L_S3": "canonical BVM local nodes 6 and 10",
            "probed_branch_voltage": "V(R_S|XBVMn) and V(L_S3|XBVMn)",
        },
        "windows": cells,
    }


def bvm_metrics(trace: Any, mask: str, bridge_available: bool = True) -> dict[str, Any]:
    cells: dict[str, Any] = {}
    for index in active_indices(mask):
        cells[f"XBVM{index}"] = {
            "JS1": phase_info(trace, f"P(B_JS1|XBVM{index})"),
            "JS2": phase_info(trace, f"P(B_JS2|XBVM{index})"),
            "JM1_storage": phase_info(trace, f"P(B_JM1|XBVM{index})"),
            "JM2_storage": phase_info(trace, f"P(B_JM2|XBVM{index})"),
            "JS1_phase_area": phase_area_crosscheck(
                trace,
                f"P(B_JS1|XBVM{index})",
                f"V(B_JS1|XBVM{index})",
            ),
            "JS2_phase_area": phase_area_crosscheck(
                trace,
                f"P(B_JS2|XBVM{index})",
                f"V(B_JS2|XBVM{index})",
            ),
            "I_LSL_110_121": window_stats(
                trace, f"I(L_SL|XBVM{index})", 110.0, 121.0
            ),
            "I_LSL_121_126": window_stats(
                trace, f"I(L_SL|XBVM{index})", 121.0, 126.0
            ),
        }
    return {
        "active_cells": [f"XBVM{index}" for index in active_indices(mask)],
        "cells": cells,
        "bridge_partition": (
            branch_partition_metrics(trace, mask)
            if bridge_available
            else {
                "status": "UNAVAILABLE",
                "reason": "read-only R20 endpoint did not include R_S branch current",
            }
        ),
    }


def qb_metrics(trace: Any, instance: str = "XBQ") -> dict[str, Any]:
    return {
        "BJ1_navigation": phase_info(trace, f"P(BJ1|{instance})"),
        "BJ2_navigation": phase_info(trace, f"P(BJ2|{instance})"),
        "BJ1_phase_area": phase_area_crosscheck(
            trace, f"P(BJ1|{instance})", f"V(BJ1|{instance})"
        ),
        "BJ2_phase_area": phase_area_crosscheck(
            trace, f"P(BJ2|{instance})", f"V(BJ2|{instance})"
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
        "V_QBOUT_110_121": window_stats(
            trace, "V(QBOUT)", 110.0, 121.0
        ),
    }


def downstream_metrics(trace: Any) -> dict[str, Any]:
    return {
        "JTL6_B02_navigation": phase_info(
            trace, "P(B02|XJTL1_6)"
        ),
        "terminal_voltage_integral_110_200_V_s": actual_integral(
            trace, trace.column("V(JTL6_OUT)"), 110.0, 200.0
        ),
        "terminal_voltage_integral_110_200_over_phi0": actual_integral(
            trace, trace.column("V(JTL6_OUT)"), 110.0, 200.0
        ) / PHI0,
        "terminal_current_110_121": window_stats(
            trace, "I(R_TERM)", 110.0, 121.0
        ),
        "terminal_signal": "V(JTL6_OUT)",
        "crosscheck_layers": [
            "QB BJ1/BJ2 same-JJ phase and voltage area",
            "JTL6 B02 phase navigation",
            "terminal V(JTL6_OUT) actual-grid integral",
        ],
        "not_event_count": True,
    }


def critical_chronology(
    trace: Any,
    mask: str,
    bridge_available: bool = True,
    instance: str = "XBQ",
) -> dict[str, Any]:
    representative = active_indices(mask)[0]
    return {
        "representative_active_cell": f"XBVM{representative}",
        "JS2_navigation": phase_info(
            trace, f"P(B_JS2|XBVM{representative})"
        ),
        "JS1_navigation": phase_info(
            trace, f"P(B_JS1|XBVM{representative})"
        ),
        "BJ1_navigation": phase_info(trace, f"P(BJ1|{instance})"),
        "BJ2_navigation": phase_info(trace, f"P(BJ2|{instance})"),
        "JSL8_sign_changes": sign_change_times(trace, "I(B_JSL8)"),
        "L1_sign_changes": sign_change_times(trace, f"I(L1|{instance})"),
        "bridge_sign_changes": {
            "I_LS3": (
                sign_change_times(trace, f"I(L_S3|XBVM{representative})")
                if bridge_available else None
            ),
            "I_RS": (
                sign_change_times(trace, f"I(R_S|XBVM{representative})")
                if bridge_available else None
            ),
        },
        "no_causal_label_assigned": True,
    }


def run_metrics(
    point: dict[str, Any],
    mask: str,
    trace: Any,
    bridge_available: bool = True,
    instance: str = "XBQ",
) -> dict[str, Any]:
    return {
        "point_id": point["point_id"],
        "mask": mask,
        "run_id": f"{point['point_id']}_{mask}",
        "L_S3_pH": point["value_pH"],
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
        "bvm": bvm_metrics(trace, mask, bridge_available),
        "boundary": {
            "V_COMMON_SL_110_121": window_stats(
                trace, "V(COMMON_SL)", 110.0, 121.0
            ),
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
                trace, f"I(LIN|{instance})", 110.0, 121.0
            ),
            "kcl": kcl_metrics(trace, instance),
        },
        "qb": qb_metrics(trace, instance),
        "downstream": downstream_metrics(trace),
        "critical_chronology": critical_chronology(
            trace, mask, bridge_available, instance
        ),
    }


def run_dir(point_id: str, mask: str) -> Path:
    return EXP / "runs" / point_id / mask


def point_deck_record(point: dict[str, Any], mask: str) -> dict[str, Any]:
    deck = run_dir(point["point_id"], mask) / "deck.cir"
    return {
        "point_id": point["point_id"],
        "mask": mask,
        "run_id": f"{point['point_id']}_{mask}",
        "path": rel(deck),
        "sha256": sha256(deck),
        "bytes": deck.stat().st_size,
    }


def point_by_id(point_id: str) -> dict[str, Any]:
    return next(item for item in LS3_POINTS if item["point_id"] == point_id)


def active_indices(mask: str) -> list[int]:
    return [
        index for index, bit in enumerate(mask, start=1) if bit == "1"
    ]


def write_provenance(provenance: dict[str, Any]) -> None:
    write_json(EXP / "provenance.json", provenance)


def experiment_yaml(
    sources: list[dict[str, Any]],
    endpoints: list[dict[str, Any]],
    decks: list[dict[str, Any]],
) -> str:
    point_lines = "\n".join(
        f"    - point_id: {point['point_id']}\n"
        f"      L_S3_pH: {point['value_pH']}\n"
        f"      spice_value: {point['spice_value']}"
        for point in LS3_POINTS
    )
    source_lines = "\n".join(
        f"  - {item['name']}: {item['path']}; sha256={item['sha256']}"
        for item in sources
    )
    endpoint_lines = "\n".join(
        f"  - {item['name']}: {item['path']}; sha256={item['sha256']}"
        for item in endpoints
    )
    deck_lines = "\n".join(
        f"  - {item['run_id']}: {item['path']}; sha256={item['sha256']}"
        for item in decks
    )
    return f"""schema_version: bvm-qb-rloop-ls3-causality-v1
id: {EXP.name}
study_phase: EXPLORATORY
role: Experimental Operator + Evidence Packager
status: PREFLIGHT_PASS
contract_sentence: {CONTRACT_SENTENCE}
scientific_review_authorized: false
scientific_interpretation_performed: false

question:
  primary: "Test whether the R_S // L_S3 bridge is a causal internal path for the N3/N4 extra BVM R-loop rotations."
  scope: "Only L_S3 changes; this is not QB tuning and does not force a target turn count."
  interpretation_ceiling: "Raw, phase/area, branch-current, timing and scalar observations only; mechanism labels remain review-gated."

frozen:
  topology: "4 historical JM2-connected BVM -> COMMON_SL -> 8 JSL -> canonical QB -> 6 existing JTL -> 10 ohm terminal"
  canonical_qb_source: circuits/qb/bq_parameterized_v1.cir
  canonical_qb_parameters: {{Lin_pH: 1.5, L1_pH: 1.4, L2_pH: 2.0, RJ1_ohm: 32.0, RJ2_ohm: 12.0, IB_uA: 260.0, BJS_area: 4.0, BJ1_area: 0.9, BJ2_area: 2.0, L3_pH: 1.3}}
  canonical_bvm_source: test/exploration/bvm-population-scaling-rj2p12-l1p14-l2p20-ib260-rj32-bjs400-v1-20260910/inputs/bvm_jm2_connected.cir
  canonical_R_S_ohm: 3.0
  canonical_L_S3_pH: 0.5
  stimulus: "same as accepted population baseline and R20 experiment; 100uA, 1ps edges, 9ps plateau, final masks 0011/0111"
  tran: ".tran 0.1p 200p"
  terminal_load_ohm: 10.0
  bit_order: b3b2b1b0 = BVM1/BVM2/BVM3/BVM4

stage_a:
  points:
{point_lines}
  masks: ["0011", "0111"]
  authorized_new_physical_solves: 6
  no_other_L_S3_values: true
  no_canonical_source_mutation: true

stage_b:
  status: REVIEW_GATED
  conditional_masks: ["0000", "0001", "1111"]
  maximum_additional_solves: 3
  selection: "smallest L_S3 only if a separately authorized review accepts the preregistered mechanism-success predicate"
  qualitative_predicate_not_numerically_frozen: true

read_only_endpoints:
{endpoint_lines}

source_closure:
{source_lines}

registered_decks:
{deck_lines}

probes:
  bvm: "P/V/I(B_JM1/B_JM2/B_JS1/B_JS2); I/V(L_M1/L_M2/L_M3/L_PM/L_S1/L_S2/L_S3/R_S/L_PSL/R_SL/L_SL); WL/BL/SE currents; V(COMMON_SL)."
  bridge: "I/V(L_S3|XBVMn), I/V(R_S|XBVMn), and actual branch endpoints are local BVM nodes 6 and 10 as confirmed from the canonical source."
  qb_boundary: "P/V/I(B_JSL1..8), V(QBIN), I(B_JSL8), I/V(LIN|XBQ), P/V/I(BJS/BJ1/BJ2), L1/L2/L3, RJ1/RJ2, V(QBOUT)."
  downstream: "JTL1..6 B01/B02 P/V/I, stage output voltage, terminal voltage/current."
  direction: "R_S and L_S3 both use canonical branch orientation 6 -> 10; B_JSL8 JSL_NODE7 -> QBIN; LIN|XBQ QBIN -> QB node1."

windows_ps:
  - [101, 110]
  - [110, 113]
  - [113, 115]
  - [115, 117]
  - [117, 121]
  - [121, 126]
  - [126, 140]
  - [140, 200]
window_semantics: half-open; actual stored timestamps; no interpolation/resampling
phase_semantics: raw radians; independent continuous unwrap then rad/(2*pi) navigation
voltage_area_semantics: same JJ, same endpoints, same direction and actual grid; not an SFQ count
phase_area_window_ps: [110, 121]
divergence_thresholds: {{phase_turns: {DIV_PHASE_THRESHOLD_TURNS}, current_A: {DIV_CURRENT_THRESHOLD_A}, voltage_V: {DIV_VOLTAGE_THRESHOLD_V}}}

mechanical_vs_scientific:
  mechanical_outputs: "branch min/max/mean/signed and absolute area, phase/area residuals, sign-change timestamps, exact-grid deltas, storage/symmetry scalars"
  scientific_labels: "RLOOP_BRIDGE_MECHANISM_STRONGLY_SUPPORTED, RLOOP_BRIDGE_MECHANISM_PARTIALLY_SUPPORTED, LS3_ROUTE_WEAK_OR_NOT_CAUSAL, LS3_OVERDAMPED_NORMAL_READ, and Stage B authorization remain unassigned"

visualization:
  pages_per_run: [01_storage.html, 02_js_phase_voltage.html, 03_rloop_bridge.html, 04_output_common_sl.html, 05_jsl_qbin.html, 06_qb.html, 07_jtl_terminal.html]
  renderer: scripts/josim-plot2.py
  layout: sep_comb
  color: dark
  phase_option: 2pi
  window_ps: [0, 200]
  focused_pages: none
  shared_asset: plots/assets/plotly.min.js
  no_png_svg: true

layout:
  root_files_only: [experiment.yaml, RESULT.md, result.json, provenance.json, runs, plots]
  forbidden_dirs: [screening, references, handoff, qa, analysis, inputs, data]
  run_files_only: [deck.cir, raw.csv, run.log]
  zip_policy: Drive only; do not commit ZIP
  result_json_limit_bytes: {500 * 1024}

stop:
  final_state: {FINAL_MARKER}
  stage_b_without_scientific_review: false
  automatic_followup: false
"""


def initial_result() -> dict[str, Any]:
    return {
        "schema": "bvm-qb-rloop-ls3-causality-result-v1",
        "experiment_id": EXP.name,
        "status": "PREFLIGHT_PASS",
        "scientific_interpretation_performed": False,
        "stage_a": {"status": "NOT_RUN", "authorized_solve_count": 6},
        "stage_b": {
            "status": "REVIEW_GATED",
            "authorized_solve_count": 0,
            "chosen_point_id": None,
        },
        "classification": {
            "assigned": None,
            "status": "SCIENTIFIC_REVIEW_REQUIRED",
            "allowed": [
                "RLOOP_BRIDGE_MECHANISM_STRONGLY_SUPPORTED",
                "RLOOP_BRIDGE_MECHANISM_PARTIALLY_SUPPORTED",
                "LS3_ROUTE_WEAK_OR_NOT_CAUSAL",
                "LS3_OVERDAMPED_NORMAL_READ",
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
    variants: list[dict[str, Any]] = []
    for point in LS3_POINTS:
        variant, variant_hash = load_canonical_bvm_variant(
            point["value_pH"], point["spice_value"]
        )
        variants.append({
            "point_id": point["point_id"],
            "canonical_source_sha256": sha256(BVM),
            "variant_sha256": variant_hash,
            "changed_line": f"L_S3 6 10 {point['spice_value']}",
        })
        for mask in MASKS_STAGE_A:
            directory = run_dir(point["point_id"], mask)
            directory.mkdir(parents=True, exist_ok=True)
            deck = directory / "deck.cir"
            text, _ = deck_text(point, mask, directory)
            deck.write_text(text, encoding="utf-8")
            item = point_deck_record(point, mask)
            item["variant_sha256"] = variant_hash
            decks.append(item)
    provenance = {
        "schema": "bvm-qb-rloop-ls3-causality-provenance-v1",
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
        "experiment_local_bvm_variants": variants,
        "frozen_change": {
            "canonical_line": "L_S3 6 10 0.5P",
            "only_changed_element": "L_S3",
            "R_S_ohm": 3.0,
            "branch_nodes": ["6", "10"],
        },
        "stage_a": {
            "points": [point["point_id"] for point in LS3_POINTS],
            "masks": list(MASKS_STAGE_A),
            "authorized_physical_solve_count": 6,
        },
        "stage_b": {
            "status": "REVIEW_GATED",
            "masks": list(MASKS_STAGE_B),
            "maximum_additional_solve_count": 3,
            "chosen_point_id": None,
            "qualitative_predicate_not_numerically_frozen": True,
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
            {"name": "exact_grid_N3_minus_N2_delta", "phase_unwrap_before_subtract": True, "raw_mutated": False},
            {"name": "temporary_plot_comparison_csv", "raw_mutated": False, "deleted_after_render": True},
        ],
    }
    (EXP / "experiment.yaml").write_text(
        experiment_yaml(sources, endpoints, decks), encoding="utf-8"
    )
    write_provenance(provenance)
    write_json(EXP / "result.json", initial_result())
    print(json.dumps({
        "status": "PREFLIGHT_PASS",
        "experiment": EXP.name,
        "stage_a_solves": 6,
        "masks": list(MASKS_STAGE_A),
        "ls3_points_pH": [point["value_pH"] for point in LS3_POINTS],
        "stage_b": "REVIEW_GATED",
    }, ensure_ascii=False, indent=2))


def repair_duplicate_bjsl8_probe() -> None:
    provenance = read_json(EXP / "provenance.json")
    execution = provenance["execution"]
    if (
        execution.get("status") != "RAW_QA_FAILURE_STOP"
        or execution.get("run_order") != ["ls3_0p75_0011"]
    ):
        raise RuntimeError("no registered duplicate-probe failure is available for repair")
    failed = execution["run_records"]["ls3_0p75_0011"]
    original_dir = run_dir("ls3_0p75", "0011")
    archived_dir = original_dir.with_name("0011_attempt1")
    if not original_dir.is_dir() or archived_dir.exists():
        raise RuntimeError("failed attempt directory is missing or archive target exists")
    original_dir.rename(archived_dir)
    failed["original_artifact_paths"] = {
        "deck": failed["deck"]["path"],
        "raw": failed["raw"]["path"],
        "log": failed["log"]["path"],
    }
    failed["archived_artifact_paths"] = {
        "deck": rel(archived_dir / "deck.cir"),
        "raw": rel(archived_dir / "raw.csv"),
        "log": rel(archived_dir / "run.log"),
    }
    failed["status"] = "FORMAT_FAILURE_PRESERVED"
    provenance.setdefault("failed_attempts", []).append(failed)
    provenance["registered_decks"] = []
    for point in LS3_POINTS:
        for mask in MASKS_STAGE_A:
            directory = run_dir(point["point_id"], mask)
            directory.mkdir(parents=True, exist_ok=True)
            deck = directory / "deck.cir"
            deck.write_text(deck_text(point, mask, directory)[0], encoding="utf-8")
            item = point_deck_record(point, mask)
            item["variant_sha256"] = load_canonical_bvm_variant(
                point["value_pH"], point["spice_value"]
            )[1]
            provenance["registered_decks"].append(item)
    runner = next(
        item for item in provenance["sources"] if item["name"] == "runner"
    )
    old_runner_hash = runner["sha256"]
    runner["sha256"] = sha256(SCRIPT)
    runner["bytes"] = SCRIPT.stat().st_size
    provenance.setdefault("tooling_revisions", []).append({
        "path": rel(SCRIPT),
        "old_sha256": old_runner_hash,
        "new_sha256": runner["sha256"],
        "reason": "removed duplicate I(B_JSL8) probe; preserved failed raw/log/deck in 0011_attempt1; retry is same registered physics case",
        "raw_mutated": False,
    })
    provenance["execution"] = {
        "status": "PREFLIGHT_REPAIRED",
        "run_order": [],
        "actual_physical_solve_count": 0,
        "solver_invocation_count": 1,
        "failed_attempt_count": 1,
        "run_records": {},
    }
    sources = source_inventory()
    endpoints = endpoint_inventory()
    (EXP / "experiment.yaml").write_text(
        experiment_yaml(sources, endpoints, provenance["registered_decks"]),
        encoding="utf-8",
    )
    write_provenance(provenance)
    print(json.dumps({
        "status": "PREFLIGHT_REPAIRED",
        "failed_attempt_archived": rel(archived_dir),
        "retry_target": "ls3_0p75/0011",
        "physical_rerun": "same registered case after format-only probe repair",
        "failed_attempt_preserved": True,
    }, ensure_ascii=False, indent=2))


def write_provenance(provenance: dict[str, Any]) -> None:
    write_json(EXP / "provenance.json", provenance)


def verify_registered_sources(provenance: dict[str, Any]) -> None:
    for item in provenance["sources"]:
        path = REPO / item["path"]
        if not path.is_file() or sha256(path) != item["sha256"]:
            raise RuntimeError(f"registered source changed: {path}")


def execute_one(point: dict[str, Any], mask: str) -> None:
    provenance = read_json(EXP / "provenance.json")
    verify_registered_sources(provenance)
    identifier = f"{point['point_id']}_{mask}"
    directory = run_dir(point["point_id"], mask)
    deck = directory / "deck.cir"
    raw = directory / "raw.csv"
    log = directory / "run.log"
    if not deck.is_file():
        raise RuntimeError(f"registered deck missing: {deck}")
    registered = next(
        item for item in provenance["registered_decks"]
        if item["run_id"] == identifier
    )
    if sha256(deck) != registered["sha256"]:
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
        load_raw(raw, "XBQ")
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
    provenance["execution"]["solver_invocation_count"] = (
        provenance["execution"].get("solver_invocation_count", 0) + 1
    )
    record: dict[str, Any] = {
        "run_id": identifier,
        "point_id": point["point_id"],
        "mask": mask,
        "L_S3_pH": point["value_pH"],
        "deck": {
            "path": rel(deck),
            "sha256": sha256(deck),
            "bytes": deck.stat().st_size,
        },
        "variant_sha256": registered.get("variant_sha256"),
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
        trace = load_raw(raw, "XBQ")
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
        "PREFLIGHT_PASS", "PREFLIGHT_REPAIRED",
        "STAGE_A_RUNNING", "STAGE_A_COMPLETE"
    }:
        raise RuntimeError(
            f"Stage A is not executable in state {provenance['execution']['status']}"
        )
    provenance["execution"]["status"] = "STAGE_A_RUNNING"
    write_provenance(provenance)
    for point in LS3_POINTS:
        for mask in MASKS_STAGE_A:
            execute_one(point, mask)
    provenance = read_json(EXP / "provenance.json")
    provenance["execution"]["status"] = "STAGE_A_COMPLETE"
    write_provenance(provenance)


def average_cell_field(
    metric: dict[str, Any],
    junction: str,
    field: str,
) -> float | None:
    values = [
        item[junction][field]
        for item in metric["bvm"]["cells"].values()
    ]
    return sum(values) / len(values) if values else None


def source_normalization(n2: dict[str, Any], n3: dict[str, Any]) -> dict[str, Any]:
    n2_fields = {
        "JS1_read_p2p_turns": average_cell_field(
            n2, "JS1", "read_110_121_p2p_turns"
        ),
        "JS2_read_p2p_turns": average_cell_field(
            n2, "JS2", "read_110_121_p2p_turns"
        ),
        "I_LSL_110_121_signed_area_A_s": average_cell_field(
            n2, "JS1", "read_110_121_p2p_turns"
        ),
    }
    # Source current areas live at the cell level rather than under JS1/JS2.
    n2_lsl = [
        item["I_LSL_110_121"]["signed_area"]
        for item in n2["bvm"]["cells"].values()
    ]
    n3_lsl = [
        item["I_LSL_110_121"]["signed_area"]
        for item in n3["bvm"]["cells"].values()
    ]
    n2_area = sum(n2_lsl) / len(n2_lsl) if n2_lsl else None
    n3_area = sum(n3_lsl) / len(n3_lsl) if n3_lsl else None
    n2_fields["I_LSL_110_121_signed_area_A_s"] = n2_area
    n2_fields["I_LSL_121_126_signed_area_A_s"] = (
        sum(
            item["I_LSL_121_126"]["signed_area"]
            for item in n2["bvm"]["cells"].values()
        ) / len(n2["bvm"]["cells"])
        if n2["bvm"]["cells"] else None
    )
    n3_fields = {
        "JS1_read_p2p_turns": average_cell_field(
            n3, "JS1", "read_110_121_p2p_turns"
        ),
        "JS2_read_p2p_turns": average_cell_field(
            n3, "JS2", "read_110_121_p2p_turns"
        ),
        "I_LSL_110_121_signed_area_A_s": n3_area,
        "I_LSL_121_126_signed_area_A_s": (
            sum(
                item["I_LSL_121_126"]["signed_area"]
                for item in n3["bvm"]["cells"].values()
            ) / len(n3["bvm"]["cells"])
            if n3["bvm"]["cells"] else None
        ),
    }
    ratio = None
    if n2_area is not None and abs(n2_area) > 1.0e-30:
        ratio = n3_area / n2_area if n3_area is not None else None
    return {
        "N2_per_active_cell": n2_fields,
        "N3_per_active_cell": n3_fields,
        "N3_over_N2_signed_LSL_area_ratio": ratio,
        "ratio_interpretation": "descriptive per-active-cell source normalization; not a Gate",
    }


def compact_phase(metric: dict[str, Any], junction: str) -> dict[str, Any]:
    values = []
    for cell in metric["bvm"]["cells"].values():
        item = cell[junction]
        values.append({
            "read_110_121_p2p_turns": item["read_110_121_p2p_turns"],
            "read_110_121_endpoint_delta_turns": item["read_110_121_endpoint_delta_turns"],
            "max_relative_turns": item["max_relative_turns"],
            "final_relative_turns": item["final_relative_turns"],
            "rollback_from_max_turns": item["rollback_from_max_turns"],
        })
    return {"junction": junction, "active_cell_values": values}


def difference_stats(
    times: tuple[float, ...],
    values: Iterable[float],
    signal: str,
    threshold: float,
) -> dict[str, Any]:
    values_list = list(values)
    selected = [
        index for index, value in enumerate(times)
        if 110.0 <= value * 1.0e12 < 140.0
    ]
    unit = "rad" if signal.startswith("P(") else (
        "A" if signal.startswith("I(") else "V"
    )
    first = next(
        (
            index for index in selected
            if abs(values_list[index]) >= threshold
        ),
        None,
    )
    selected_values = [values_list[index] for index in selected]
    return {
        "signal": signal,
        "unit": unit,
        "threshold": threshold,
        "first_divergence_time_ps": (
            times[first] * 1.0e12 if first is not None else None
        ),
        "first_divergence_delta": values_list[first] if first is not None else None,
        "first_divergence_direction": (
            "positive" if first is not None and values_list[first] > 0
            else "negative" if first is not None and values_list[first] < 0
            else None
        ),
        "max_abs_delta": max((abs(value) for value in selected_values), default=None),
        "rms_delta": (
            math.sqrt(
                sum(value * value for value in selected_values)
                / len(selected_values)
            )
            if selected_values else None
        ),
        "window_ps": [110.0, 140.0],
        "phase_subtraction": (
            "independent continuous unwrap before subtract"
            if signal.startswith("P(") else "direct same-time subtraction"
        ),
    }


def first_divergence(
    n2_trace: Any,
    n3_trace: Any,
) -> dict[str, Any]:
    if n2_trace.time != n3_trace.time:
        return {
            "status": "DESCRIPTIVE_ONLY_TIME_GRID_MISMATCH",
            "scientific_interpretation_performed": False,
        }
    from bvmtools.phase import continuous_unwrap

    signals = [
        ("V(COMMON_SL)", DIV_VOLTAGE_THRESHOLD_V),
        ("I(B_JSL8)", DIV_CURRENT_THRESHOLD_A),
        ("V(B_JS2|XBVM3)", DIV_VOLTAGE_THRESHOLD_V),
        ("I(B_JS2|XBVM3)", DIV_CURRENT_THRESHOLD_A),
        ("P(B_JS2|XBVM3)", DIV_PHASE_THRESHOLD_TURNS * 2.0 * math.pi),
        ("I(L_S3|XBVM3)", DIV_CURRENT_THRESHOLD_A),
        ("I(R_S|XBVM3)", DIV_CURRENT_THRESHOLD_A),
        ("V(B_JS1|XBVM3)", DIV_VOLTAGE_THRESHOLD_V),
        ("I(B_JS1|XBVM3)", DIV_CURRENT_THRESHOLD_A),
        ("P(B_JS1|XBVM3)", DIV_PHASE_THRESHOLD_TURNS * 2.0 * math.pi),
        ("I(L_M3|XBVM3)", DIV_CURRENT_THRESHOLD_A),
        ("P(B_JM2|XBVM3)", DIV_PHASE_THRESHOLD_TURNS * 2.0 * math.pi),
        ("P(B_JM1|XBVM3)", DIV_PHASE_THRESHOLD_TURNS * 2.0 * math.pi),
    ]
    records: list[dict[str, Any]] = []
    for signal, threshold in signals:
        left = n2_trace.column(signal)
        right = n3_trace.column(signal)
        if signal.startswith("P("):
            left = continuous_unwrap(left)
            right = continuous_unwrap(right)
        delta = tuple(
            right_value - left_value
            for left_value, right_value in zip(left, right)
        )
        records.append(difference_stats(
            n2_trace.time, delta, signal, threshold
        ))
    ordered = [
        {
            "signal": item["signal"],
            "time_ps": item["first_divergence_time_ps"],
            "direction": item["first_divergence_direction"],
        }
        for item in sorted(
            (record for record in records
             if record["first_divergence_time_ps"] is not None),
            key=lambda record: record["first_divergence_time_ps"],
        )
    ]
    return {
        "status": "DERIVED_EXACT_GRID",
        "comparison": "N3 candidate minus N2 candidate at identical L_S3 and mask-specific history",
        "signals": records,
        "observed_first_divergence_order": ordered,
        "thresholds": {
            "phase_turns": DIV_PHASE_THRESHOLD_TURNS,
            "current_A": DIV_CURRENT_THRESHOLD_A,
            "voltage_V": DIV_VOLTAGE_THRESHOLD_V,
        },
        "no_causal_label_assigned": True,
        "scientific_interpretation_performed": False,
    }


def fmt(value: Any, digits: int = 5) -> str:
    if value is None:
        return "NA"
    if isinstance(value, float) and math.isinf(value):
        return "open"
    if isinstance(value, (float, int)):
        return f"{value:.{digits}g}"
    return str(value)


def average_run_field(
    metric: dict[str, Any],
    junction: str,
    field: str,
) -> float | None:
    values = [
        item[junction][field]
        for item in metric["bvm"]["cells"].values()
    ]
    return sum(values) / len(values) if values else None


def representative_fraction(
    metric: dict[str, Any],
    window: str,
) -> float | None:
    values = []
    for cell in metric["bvm"]["bridge_partition"]["windows"].values():
        record = cell.get(window, {})
        value = record.get("fast_bridge_fraction", {}).get("value")
        if value is not None:
            values.append(value)
    return sum(values) / len(values) if values else None


def result_markdown(result: dict[str, Any]) -> str:
    lines = [
        f"# BVM R-loop bridge causality experiment: {EXP.name}",
        "",
        f"- Stage A status: {result.get('status')}",
        f"- Final state: {result.get('stop', {}).get('final_marker')}",
        f"- Physical solves: {result.get('execution', {}).get('actual_physical_solve_count')}",
        "- Scientific interpretation: NOT_PERFORMED.",
        "- Scientific classification: SCIENTIFIC_REVIEW_REQUIRED.",
        "- Independent variable: only experiment-local L_S3; canonical BVM source is immutable.",
        "",
        "## Stage A source-side normalization",
        "",
        "| L_S3 (pH) | N2 JS1/JS2 read p2p turns | N3 JS1/JS2 read p2p turns | N3/N2 signed L_SL area ratio | N3 bridge fraction [113,115) |",
        "|---:|---:|---:|---:|---:|",
    ]
    for point_record in result["stage_a"]["per_point"]:
        n2 = next(
            item for item in result["run_metrics"]
            if item["run_id"] == point_record["N2_run_id"]
        )
        n3 = next(
            item for item in result["run_metrics"]
            if item["run_id"] == point_record["N3_run_id"]
        )
        n2_pair = (
            f"{fmt(average_run_field(n2, 'JS1', 'read_110_121_p2p_turns'))}/"
            f"{fmt(average_run_field(n2, 'JS2', 'read_110_121_p2p_turns'))}"
        )
        n3_pair = (
            f"{fmt(average_run_field(n3, 'JS1', 'read_110_121_p2p_turns'))}/"
            f"{fmt(average_run_field(n3, 'JS2', 'read_110_121_p2p_turns'))}"
        )
        lines.append(
            f"| {point_record['L_S3_pH']:.2f} | {n2_pair} | {n3_pair} | "
            f"{fmt(point_record['source_normalization']['N3_over_N2_signed_LSL_area_ratio'])} | "
            f"{fmt(representative_fraction(n3, '[113,115)ps'))} |"
        )
    lines += [
        "",
        "## Required answers for scientific review",
        "",
        "1. Canonical chronology is remeasured in each candidate through the exact-grid",
        "   N3-minus-N2 records in stage_a.per_point.first_divergence_N3_minus_N2.",
        "2. I(L_S3) versus I(R_S) min/max/mean/signed-area/absolute-area and bridge",
        "   fractions are stored for every active cell and every registered window.",
        "3. JS2-side and JS1-side first-divergence timestamps, directions and magnitudes",
        "   are recorded without assigning causal direction.",
        "4. BJ2 handoff and JS1 navigation timestamps are retained per candidate; any",
        "   locking, delay, or disappearance requires scientific review.",
        "5. N2 read-attractor preservation is represented by the N2 phase/current/storage",
        "   records and same-JJ phase/voltage-area cross-checks.",
        "6. N3 JS1/JS2 read p2p values are in the table above; they are phase navigation",
        "   observables, not event or SFQ counts.",
        "7. Per-active-cell L_SL source normalization and N3/N2 ratio are recorded above.",
        "8. COMMON_SL, JSL8 and QBIN boundary scalars are retained in each run metric.",
        "9. JM1/JM2 storage phase records and rollback values are retained per active cell.",
        "10. JM1/JM2 timing is recorded separately from JS1/JS2 and bridge chronology.",
        "11. QB BJ1/BJ2/L1 records and same-JJ phase/area checks are retained.",
        "12. QB downstream records include JTL6 B02 and terminal voltage integral.",
        "13. No receiver-side versus source-side explanation is assigned automatically.",
        "14. Stage B was not executed: its qualitative mechanism-success predicate has",
        "    no frozen numerical threshold and scientific review authorization is absent.",
        "15. No complete population map is generated in this Stage A-only run.",
        "",
        "## Evidence boundary",
        "",
        "P(...) is raw radians. Turns are only independent unwrap(rad)/(2*pi) navigation.",
        "Phase thresholds, branch activity, terminal peaks and mechanical summaries do",
        "not certify SFQ events. Raw CSV files are immutable authority; all comparisons",
        "use exact stored timestamps and no interpolation.",
        "",
        "The experiment root intentionally contains only experiment.yaml, RESULT.md,",
        "result.json, provenance.json, runs and plots. ZIP delivery is Drive-only.",
        "",
    ]
    return "\n".join(lines)


def analyze() -> None:
    provenance = read_json(EXP / "provenance.json")
    records = provenance["execution"]["run_records"]
    if provenance["execution"]["actual_physical_solve_count"] != 6:
        raise RuntimeError("analysis requires exactly six Stage A solves")
    metrics: list[dict[str, Any]] = []
    traces: dict[tuple[str, str], Any] = {}
    before: dict[str, str] = {}
    for identifier in provenance["execution"]["run_order"]:
        record = records[identifier]
        path = REPO / record["raw"]["path"]
        before[identifier] = sha256(path)
        trace = load_raw(path, "XBQ")
        traces[(record["point_id"], record["mask"])] = trace
        metrics.append(run_metrics(
            point_by_id(record["point_id"]),
            record["mask"],
            trace,
        ))
    per_point: list[dict[str, Any]] = []
    for point in LS3_POINTS:
        n2 = next(
            metric for metric in metrics
            if metric["point_id"] == point["point_id"]
            and metric["mask"] == "0011"
        )
        n3 = next(
            metric for metric in metrics
            if metric["point_id"] == point["point_id"]
            and metric["mask"] == "0111"
        )
        per_point.append({
            "point_id": point["point_id"],
            "L_S3_pH": point["value_pH"],
            "N2_run_id": n2["run_id"],
            "N3_run_id": n3["run_id"],
            "source_normalization": source_normalization(n2, n3),
            "first_divergence_N3_minus_N2": first_divergence(
                traces[(point["point_id"], "0011")],
                traces[(point["point_id"], "0111")],
            ),
            "N2_boundary": n2["boundary"],
            "N3_boundary": n3["boundary"],
            "N2_critical_chronology": n2["critical_chronology"],
            "N3_critical_chronology": n3["critical_chronology"],
        })

    endpoint_compact: dict[str, Any] = {}
    for mask in MASKS_STAGE_A:
        trace = load_raw(R20_RAW[mask], "XBQ", endpoint=True)
        endpoint_compact[mask] = {
            "raw_path": rel(R20_RAW[mask]),
            "raw_sha256": sha256(R20_RAW[mask]),
            "mask": mask,
            "JS1_navigation": phase_info(
                trace, f"P(B_JS1|XBVM{active_indices(mask)[0]})"
            ),
            "JS2_navigation": phase_info(
                trace, f"P(B_JS2|XBVM{active_indices(mask)[0]})"
            ),
            "I_LSL_110_121": window_stats(
                trace,
                f"I(L_SL|XBVM{active_indices(mask)[0]})",
                110.0,
                121.0,
            ),
            "QB_BJ1_navigation": phase_info(trace, "P(BJ1|XBQ)"),
            "QB_BJ2_navigation": phase_info(trace, "P(BJ2|XBQ)"),
            "I_LS3_RS_partition": {
                "status": "UNAVAILABLE",
                "reason": "R20 endpoint raw did not record I(R_S); endpoint was not rerun",
            },
        }

    after = {
        identifier: sha256(REPO / records[identifier]["raw"]["path"])
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
        "mechanism_chronology_is_observed_not_causal": True,
        "stage_b_status": "REVIEW_GATED",
    }
    write_provenance(provenance)
    result = {
        "schema": "bvm-qb-rloop-ls3-causality-result-v1",
        "experiment_id": EXP.name,
        "generated_at": now(),
        "status": "STAGE_A_COMPLETE",
        "workflow_outcome": "STAGE_A_COMPLETE_STAGE_B_REVIEW_GATED",
        "scientific_interpretation_performed": False,
        "execution": {
            "authorized_stage_a_physical_solve_count": 6,
            "actual_physical_solve_count": 6,
            "solver_invocation_count": provenance["execution"].get("solver_invocation_count", 6),
            "failed_format_attempt_count": provenance["execution"].get("failed_attempt_count", 0),
            "run_order": provenance["execution"]["run_order"],
            "stage_b_physical_solve_count": 0,
        },
        "read_only_reference": {
            "name": "canonical_L_S3_0.5pH_R20",
            "cases": endpoint_compact,
        },
        "stage_a": {
            "points": [point["point_id"] for point in LS3_POINTS],
            "masks": list(MASKS_STAGE_A),
            "per_point": per_point,
        },
        "run_metrics": metrics,
        "stage_b": {
            "status": "REVIEW_GATED",
            "reason": "mechanism-success predicate is qualitative and no SCIENTIFIC_REVIEW_AUTHORIZED token is present",
            "chosen_point_id": None,
            "masks": list(MASKS_STAGE_B),
        },
        "qa_summary": {"status": "PENDING"},
        "visualization_summary": {"status": "PENDING"},
        "package_summary": {"status": "PENDING"},
        "classification": {
            "assigned": None,
            "status": "SCIENTIFIC_REVIEW_REQUIRED",
            "allowed": [
                "RLOOP_BRIDGE_MECHANISM_STRONGLY_SUPPORTED",
                "RLOOP_BRIDGE_MECHANISM_PARTIALLY_SUPPORTED",
                "LS3_ROUTE_WEAK_OR_NOT_CAUSAL",
                "LS3_OVERDAMPED_NORMAL_READ",
            ],
        },
        "stop": {
            "final_marker": FINAL_MARKER,
            "automatic_followup": False,
        },
    }
    write_json(EXP / "result.json", result)
    (EXP / "RESULT.md").write_text(result_markdown(result), encoding="utf-8")
    if (EXP / "result.json").stat().st_size >= 500 * 1024:
        raise RuntimeError(
            f"result.json exceeds 500 KB: {(EXP / 'result.json').stat().st_size}"
        )


def qa_summary(provenance: dict[str, Any]) -> dict[str, Any]:
    qa = provenance.get("qa")
    if not isinstance(qa, dict):
        return {"status": "PENDING"}
    return {
        "status": qa.get("status", "PENDING"),
        "artifact_status": qa.get("artifact_status"),
        "actual_physical_solve_count": qa.get(
            "actual_physical_solve_count"
        ),
        "raw_hashes_equal_before_after": qa.get(
            "raw_hashes_equal_before_after"
        ),
    }


def mechanical_qa() -> None:
    provenance = read_json(EXP / "provenance.json")
    records = provenance["execution"]["run_records"]
    expected_order = [
        f"{point['point_id']}_{mask}"
        for point in LS3_POINTS
        for mask in MASKS_STAGE_A
    ]
    failures: list[str] = []
    if provenance["execution"]["run_order"] != expected_order:
        failures.append("run_order")
    try:
        verify_registered_sources(provenance)
        source_closure_status = "PASS"
    except Exception as exc:
        source_closure_status = str(exc)
        failures.append("source_closure")

    run_checks: dict[str, Any] = {}
    for identifier in expected_order:
        record = records.get(identifier, {})
        point = point_by_id(record.get("point_id", ""))
        mask = record.get("mask", "")
        directory = run_dir(point["point_id"], mask)
        deck = directory / "deck.cir"
        raw = directory / "raw.csv"
        log = directory / "run.log"
        deck_value = deck.read_text(encoding="utf-8") if deck.is_file() else ""
        ls3_lines = [
            line.strip()
            for line in deck_value.splitlines()
            if line.strip().startswith("L_S3")
        ]
        expected_line = f"L_S3 6 10 {point['spice_value']}"
        normalized_ls3_lines = [" ".join(line.split()) for line in ls3_lines]
        variant, variant_hash = load_canonical_bvm_variant(
            point["value_pH"], point["spice_value"]
        )
        variant_present = variant.rstrip() in deck_value
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
            trace = load_raw(raw, "XBQ")
            raw_qa = trace.qa()
            missing: list[str] = []
        except Exception as exc:
            trace = None
            raw_qa = {}
            missing = [str(exc)]
        hash_match = (
            raw.is_file()
            and sha256(raw) == record.get("raw", {}).get("sha256")
        )
        kcl = kcl_metrics(trace, "XBQ") if trace is not None else {}
        deck_ok = (
            normalized_ls3_lines == [expected_line]
            and variant_present
            and record.get("variant_sha256") == variant_hash
            and ".param" not in deck_value
            and "bq_parameterized_bjs400" not in deck_value
            and include_path(QB, directory) in deck_value
            and "R_QBIN_SHUNT" not in deck_value
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
            "L_S3_lines": ls3_lines,
            "normalized_L_S3_lines": normalized_ls3_lines,
            "expected_L_S3_line": expected_line,
            "variant_sha256": variant_hash,
            "variant_embedded": variant_present,
            "no_parameter_override": ".param" not in deck_value,
            "canonical_qb_include_present": include_path(QB, directory) in deck_value,
            "raw_sha256": sha256(raw) if raw.is_file() else None,
            "recorded_raw_sha256": record.get("raw", {}).get("sha256"),
            "raw_hash_match": hash_match,
            "raw_qa": raw_qa,
            "missing": missing,
            "solver_warning_lines": warning_lines,
            "unexpected_run_entries": unexpected,
            "kcl": kcl,
        }

    raw_outside_runs = [
        rel(path)
        for path in EXP.rglob("raw.csv")
        if "runs" not in path.relative_to(EXP).parts
    ]
    zip_in_experiment = [rel(path) for path in EXP.rglob("*.zip")]
    root_allowed_files = {
        "experiment.yaml", "RESULT.md", "result.json", "provenance.json"
    }
    unexpected_root_files = sorted(
        path.name
        for path in EXP.iterdir()
        if path.is_file() and path.name not in root_allowed_files
    )
    unexpected_root_dirs = sorted(
        path.name
        for path in EXP.iterdir()
        if path.is_dir() and path.name not in {"runs", "plots"}
    )
    if raw_outside_runs:
        failures.append("raw_reference_copy")
    if zip_in_experiment:
        failures.append("zip_in_experiment")
    if unexpected_root_files or unexpected_root_dirs:
        failures.append("compact_root_layout")
    before = provenance.get("analysis", {}).get(
        "raw_hash_before_analysis", {}
    )
    after = provenance.get("analysis", {}).get(
        "raw_hash_after_analysis", {}
    )
    hashes_equal = bool(before and before == after)
    if not hashes_equal:
        failures.append("raw_hashes_before_after")
    actual_count = provenance["execution"]["actual_physical_solve_count"]
    if actual_count != 6 or len(run_checks) != 6:
        failures.append("solve_count")
    failed_attempt_checks: list[dict[str, Any]] = []
    sys.path.insert(0, str(SCRIPT.parent))
    from bvmtools.raw import read_csv
    for failed in provenance.get("failed_attempts", []):
        paths = failed.get("archived_artifact_paths", {})
        archived_raw = REPO / paths.get("raw", "")
        archived_deck = REPO / paths.get("deck", "")
        archived_log = REPO / paths.get("log", "")
        try:
            failed_trace = read_csv(archived_raw)
            duplicate = failed_trace.duplicate_columns
        except Exception as exc:
            duplicate = {"read_error": str(exc)}
        preserved = (
            archived_raw.is_file()
            and archived_deck.is_file()
            and archived_log.is_file()
            and sha256(archived_raw) == failed.get("raw", {}).get("sha256")
            and duplicate.get("I(B_JSL8)") == 2
            and failed.get("status") == "FORMAT_FAILURE_PRESERVED"
        )
        failed_attempt_checks.append({
            "target_run_id": failed.get("run_id"),
            "status": "PRESERVED" if preserved else "INVALID",
            "archived_paths": paths,
            "raw_sha256": sha256(archived_raw) if archived_raw.is_file() else None,
            "recorded_raw_sha256": failed.get("raw", {}).get("sha256"),
            "duplicate_columns": duplicate,
        })
        if not preserved:
            failures.append("failed_attempt_preservation")
    failed_count = provenance["execution"].get("failed_attempt_count", 0)
    invocation_count = provenance["execution"].get("solver_invocation_count", actual_count)
    if invocation_count != actual_count + failed_count:
        failures.append("solver_invocation_count")
    result_size = (EXP / "result.json").stat().st_size
    if result_size >= 500 * 1024:
        failures.append("result_json_size")
    qa = {
        "schema": "bvm-qb-rloop-ls3-causality-mechanical-qa-v1",
        "experiment_id": EXP.name,
        "generated_at": now(),
        "status": "PASS" if not failures else "FAIL",
        "artifact_status": "VALID" if not failures else "ARTIFACT_INVALID",
        "registration_head": provenance.get("registration_head"),
        "remote_bvm_master": provenance.get("remote_bvm_master"),
        "source_closure_status": source_closure_status,
        "actual_physical_solve_count": actual_count,
        "expected_physical_solve_count": 6,
        "solver_invocation_count": invocation_count,
        "failed_format_attempt_count": failed_count,
        "failed_attempt_checks": failed_attempt_checks,
        "run_order_exact": provenance["execution"]["run_order"] == expected_order,
        "run_checks": run_checks,
        "raw_outside_runs": raw_outside_runs,
        "zip_in_experiment": zip_in_experiment,
        "unexpected_root_files": unexpected_root_files,
        "unexpected_root_dirs": unexpected_root_dirs,
        "raw_hashes_equal_before_after": hashes_equal,
        "result_json_bytes": result_size,
        "result_json_limit_bytes": 500 * 1024,
        "stage_b_status": "REVIEW_GATED",
        "scientific_interpretation_performed": False,
    }
    provenance["qa"] = qa
    write_provenance(provenance)
    result = read_json(EXP / "result.json")
    result["qa_summary"] = qa_summary(provenance)
    write_json(EXP / "result.json", result)
    (EXP / "RESULT.md").write_text(result_markdown(result), encoding="utf-8")
    if failures:
        raise RuntimeError(
            f"mechanical QA failed; artifact status ARTIFACT_INVALID: {failures}"
        )
    print(json.dumps({
        "status": "PASS",
        "actual_physical_solve_count": actual_count,
        "result_json_bytes": (EXP / "result.json").stat().st_size,
    }, ensure_ascii=False, indent=2))


def plotter_html(
    input_path: Path,
    output_path: Path,
    subset: list[str],
    title: str,
) -> None:
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
    matches = list(
        re.finditer(
            r"<script(?P<attrs>[^>]*)>(?P<body>.*?)</script>",
            html,
            flags=re.DOTALL,
        )
    )
    runtime_match = next(
        (
            match for match in matches
            if len(match.group("body")) > 1_000_000
            and (
                "plotly.js v" in match.group("body")
                or "var Plotly=" in match.group("body")
            )
        ),
        None,
    )
    if runtime_match is None:
        raise RuntimeError(
            f"embedded Plotly runtime not found: {temporary_html}"
        )
    runtime = runtime_match.group("body")
    asset_path.parent.mkdir(parents=True, exist_ok=True)
    if asset_path.exists():
        if asset_path.read_text(encoding="utf-8") != runtime:
            raise RuntimeError("Plotly runtime differs between pages")
    else:
        asset_path.write_text(runtime, encoding="utf-8")
    asset_ref = Path(
        os.path.relpath(asset_path, output_html.parent)
    ).as_posix()
    compact = (
        html[: runtime_match.start()]
        + f'<script src="{asset_ref}"></script>'
        + html[runtime_match.end() :]
    )
    if (
        "plotly.js v" in compact
        or "var Plotly=" in compact
        or "cdn.plot.ly" in compact
    ):
        raise RuntimeError(
            f"Plotly runtime was not externalized: {output_html}"
        )
    output_html.parent.mkdir(parents=True, exist_ok=True)
    output_html.write_text(compact, encoding="utf-8")


def render_external_page(
    input_path: Path,
    output_path: Path,
    subset: list[str],
    title: str,
    asset_path: Path,
) -> None:
    if output_path.exists():
        html = output_path.read_text(encoding="utf-8")
        asset_ref = Path(
            os.path.relpath(asset_path, output_path.parent)
        ).as_posix()
        if (
            asset_ref not in html
            or "plotly.js v" in html
            or "var Plotly=" in html
            or "cdn.plot.ly" in html
        ):
            raise RuntimeError(f"invalid existing external plot: {output_path}")
        return
    handle = tempfile.NamedTemporaryFile(
        prefix="josim_rloop_ls3_",
        suffix=".html",
        delete=False,
        dir="/tmp",
    )
    temporary = Path(handle.name)
    handle.close()
    try:
        plotter_html(input_path, temporary, subset, title)
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
    cases: list[tuple[str, Path, str, bool, Callable[[str], str]]],
    signals: Iterable[str],
) -> tuple[Path, list[str]]:
    signal_list = list(signals)
    traces: list[tuple[str, Any, Callable[[str], str]]] = []
    for case, raw, instance, endpoint, mapper in cases:
        traces.append((case, load_raw(raw, instance, endpoint), mapper))
    base_time = traces[0][1].time
    if any(trace.time != base_time for _, trace, _ in traces[1:]):
        raise RuntimeError("comparison raw grids do not match")
    labels: list[str] = []
    columns: list[list[float]] = []
    for case, trace, mapper in traces:
        for signal in signal_list:
            actual = mapper(signal)
            if actual in trace.headers:
                labels.append(prefixed_signal(case, signal))
                columns.append(list(trace.column(actual)))
    if not columns:
        raise RuntimeError("comparison has no common signals")
    handle = tempfile.NamedTemporaryFile(
        prefix="bvm_rloop_ls3_compare_",
        suffix=".csv",
        delete=False,
        dir="/tmp",
    )
    temporary = Path(handle.name)
    handle.close()
    with temporary.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["time", *labels])
        for index, timestamp in enumerate(base_time):
            writer.writerow([
                f"{timestamp:.17e}",
                *(f"{column[index]:.17e}" for column in columns),
            ])
    return temporary, labels


def case_catalog(
    provenance: dict[str, Any],
) -> dict[str, tuple[str, Path, str, bool, Callable[[str], str]]]:
    catalog: dict[str, tuple[str, Path, str, bool, Callable[[str], str]]] = {}
    for mask in MASKS_STAGE_A:
        population = "N2" if mask == "0011" else "N3"
        catalog[f"r20_{population}"] = (
            f"r20_{population}",
            R20_RAW[mask],
            "XBQ",
            True,
            endpoint_mapper("XBQ"),
        )
    for identifier in provenance["execution"]["run_order"]:
        record = provenance["execution"]["run_records"][identifier]
        population = "N2" if record["mask"] == "0011" else "N3"
        label = f"{record['point_id']}_{population}"
        if label in catalog:
            label = f"{record['point_id']}_{record['mask']}"
        catalog[label] = (
            label,
            REPO / record["raw"]["path"],
            "XBQ",
            False,
            endpoint_mapper("XBQ"),
        )
    return catalog


def visualization_views(headers: Iterable[str]) -> dict[str, tuple[list[str], str]]:
    available = set(headers)
    storage = [
        signal
        for index in range(1, 5)
        for signal in (
            f"P(B_JM1|XBVM{index})",
            f"P(B_JM2|XBVM{index})",
            f"I(L_M1|XBVM{index})",
            f"I(L_M2|XBVM{index})",
            f"I(L_M3|XBVM{index})",
            f"I(L_PM|XBVM{index})",
        )
    ]
    js_phase_voltage = [
        signal
        for index in range(1, 5)
        for signal in (
            f"P(B_JS1|XBVM{index})",
            f"V(B_JS1|XBVM{index})",
            f"I(B_JS1|XBVM{index})",
            f"P(B_JS2|XBVM{index})",
            f"V(B_JS2|XBVM{index})",
            f"I(B_JS2|XBVM{index})",
        )
    ]
    bridge = [
        signal
        for index in range(1, 5)
        for signal in (
            f"I(L_S1|XBVM{index})",
            f"I(L_S2|XBVM{index})",
            f"I(L_S3|XBVM{index})",
            f"I(R_S|XBVM{index})",
            f"I(L_M3|XBVM{index})",
            f"V(B_JS1|XBVM{index})",
            f"I(B_JS1|XBVM{index})",
            f"V(B_JS2|XBVM{index})",
            f"I(B_JS2|XBVM{index})",
        )
    ]
    output = [
        "V(COMMON_SL)",
        *[
            signal
            for index in range(1, 5)
            for signal in (
                f"I(L_PSL|XBVM{index})",
                f"I(R_SL|XBVM{index})",
                f"I(L_SL|XBVM{index})",
                f"V(L_SL|XBVM{index})",
            )
        ],
    ]
    jsl = [
        "V(COMMON_SL)",
        *[
            signal
            for index in range(1, 9)
            for signal in (
                f"P(B_JSL{index})",
                f"V(B_JSL{index})",
                f"I(B_JSL{index})",
            )
        ],
        "V(QBIN)",
        "I(B_JSL8)",
        "I(LIN|XBQ)",
    ]
    qb = [
        "V(QBIN)",
        "I(B_JSL8)",
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
    jtl_terminal = [
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
    ] + ["V(QBOUT)", "V(JTL6_OUT)", "I(R_TERM)"]
    specs = {
        "01_storage": (storage, "storage JMs and L_M1/L_M2/L_M3/L_PM raw currents"),
        "02_js_phase_voltage": (js_phase_voltage, "JS1/JS2 raw P/V/I; phase displayed as rad/(2*pi) navigation"),
        "03_rloop_bridge": (bridge, "R-loop bridge: L_S1/L_S2/L_S3/R_S/L_M3 and JS1/JS2"),
        "04_output_common_sl": (output, "SL output and COMMON_SL boundary; branch directions follow netlist"),
        "05_jsl_qbin": (jsl, "COMMON_SL -> JSL1..8 -> QBIN boundary"),
        "06_qb": (qb, "canonical QB P/V/I and L1/L2/L3/RJ1/RJ2"),
        "07_jtl_terminal": (jtl_terminal, "JTL1..6 and terminal raw P/V/I"),
    }
    output_specs: dict[str, tuple[list[str], str]] = {}
    for name, (signals, note) in specs.items():
        missing = [signal for signal in signals if signal not in available]
        if missing:
            raise RuntimeError(f"missing visualization signals for {name}: {missing}")
        output_specs[name] = (signals, note)
    return output_specs


def plotter_html(
    input_path: Path,
    output_path: Path,
    subset: list[str],
    title: str,
) -> None:
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
    matches = list(
        re.finditer(
            r"<script(?P<attrs>[^>]*)>(?P<body>.*?)</script>",
            html,
            flags=re.DOTALL,
        )
    )
    runtime_match = next(
        (
            match for match in matches
            if len(match.group("body")) > 1_000_000
            and (
                "plotly.js v" in match.group("body")
                or "var Plotly=" in match.group("body")
            )
        ),
        None,
    )
    if runtime_match is None:
        raise RuntimeError(f"embedded Plotly runtime not found: {temporary_html}")
    runtime = runtime_match.group("body")
    asset_path.parent.mkdir(parents=True, exist_ok=True)
    if asset_path.exists():
        if asset_path.read_text(encoding="utf-8") != runtime:
            raise RuntimeError("Plotly runtime differs between pages")
    else:
        asset_path.write_text(runtime, encoding="utf-8")
    asset_ref = Path(
        os.path.relpath(asset_path, output_html.parent)
    ).as_posix()
    compact = (
        html[: runtime_match.start()]
        + f'<script src="{asset_ref}"></script>'
        + html[runtime_match.end() :]
    )
    if (
        "plotly.js v" in compact
        or "var Plotly=" in compact
        or "cdn.plot.ly" in compact
    ):
        raise RuntimeError(f"Plotly runtime was not externalized: {output_html}")
    output_html.parent.mkdir(parents=True, exist_ok=True)
    output_html.write_text(compact, encoding="utf-8")


def render_external_page(
    input_path: Path,
    output_path: Path,
    subset: list[str],
    title: str,
    asset_path: Path,
) -> None:
    if output_path.exists():
        html = output_path.read_text(encoding="utf-8")
        asset_ref = Path(
            os.path.relpath(asset_path, output_path.parent)
        ).as_posix()
        if (
            asset_ref not in html
            or "plotly.js v" in html
            or "var Plotly=" in html
            or "cdn.plot.ly" in html
        ):
            raise RuntimeError(f"invalid existing external plot: {output_path}")
        return
    handle = tempfile.NamedTemporaryFile(
        prefix="josim_rloop_ls3_",
        suffix=".html",
        delete=False,
        dir="/tmp",
    )
    temporary = Path(handle.name)
    handle.close()
    try:
        plotter_html(input_path, temporary, subset, title)
        externalize_plotly_runtime(temporary, output_path, asset_path)
    finally:
        temporary.unlink(missing_ok=True)


def comparison_signal_mapper(instance: str) -> Callable[[str], str]:
    def mapper(signal: str) -> str:
        return signal.replace("|XBQ)", f"|{instance})")
    return mapper


def comparison_csv(
    cases: list[tuple[str, Path, str, bool, Callable[[str], str]]],
    signals: Iterable[str],
) -> tuple[Path, list[str]]:
    signal_list = list(signals)
    traces: list[tuple[str, Any, Callable[[str], str]]] = []
    for case, raw, instance, endpoint, mapper in cases:
        traces.append((case, load_raw(raw, instance, endpoint), mapper))
    base_time = traces[0][1].time
    if any(trace.time != base_time for _, trace, _ in traces[1:]):
        raise RuntimeError("comparison raw grids do not match")
    labels: list[str] = []
    columns: list[list[float]] = []
    for case, trace, mapper in traces:
        for signal in signal_list:
            actual = mapper(signal)
            if actual in trace.headers:
                labels.append(prefixed_signal(case, signal))
                columns.append(list(trace.column(actual)))
    if not columns:
        raise RuntimeError("comparison has no common signals")
    handle = tempfile.NamedTemporaryFile(
        prefix="bvm_rloop_ls3_compare_",
        suffix=".csv",
        delete=False,
        dir="/tmp",
    )
    temporary = Path(handle.name)
    handle.close()
    with temporary.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["time", *labels])
        for index, timestamp in enumerate(base_time):
            writer.writerow([
                f"{timestamp:.17e}",
                *(f"{column[index]:.17e}" for column in columns),
            ])
    return temporary, labels


def candidate_cases(
    provenance: dict[str, Any],
    include_r20: bool = False,
) -> list[tuple[str, Path, str, bool, Callable[[str], str]]]:
    cases: list[tuple[str, Path, str, bool, Callable[[str], str]]] = []
    for identifier in provenance["execution"]["run_order"]:
        record = provenance["execution"]["run_records"][identifier]
        population = "N2" if record["mask"] == "0011" else "N3"
        cases.append((
            f"{record['point_id']}_{population}",
            REPO / record["raw"]["path"],
            "XBQ",
            False,
            comparison_signal_mapper("XBQ"),
        ))
    if include_r20:
        for mask in MASKS_STAGE_A:
            population = "N2" if mask == "0011" else "N3"
            cases.append((
                f"r20_{population}",
                R20_RAW[mask],
                "XBQ",
                True,
                comparison_signal_mapper("XBQ"),
            ))
    return cases


def visualization() -> None:
    provenance = read_json(EXP / "provenance.json")
    if provenance.get("qa", {}).get("status") != "PASS":
        raise RuntimeError("mechanical QA must pass before visualization")
    asset = EXP / "plots" / "assets" / "plotly.min.js"
    entries: list[dict[str, Any]] = []
    for identifier in provenance["execution"]["run_order"]:
        record = provenance["execution"]["run_records"][identifier]
        raw = REPO / record["raw"]["path"]
        trace = load_raw(raw, "XBQ")
        for view, (signals, note) in visualization_views(trace.headers).items():
            output = (
                EXP / "plots" / record["point_id"] / record["mask"]
                / f"{view}.html"
            )
            render_external_page(
                raw,
                output,
                signals,
                f"{EXP.name} | {record['point_id']} | mask={record['mask']} | {view} | raw 0-200 ps | {note}",
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

    comparisons = [
        (
            "comparison_bridge_partition",
            candidate_cases(provenance),
            [
                "P(B_JS1|XBVM3)", "P(B_JS2|XBVM3)",
                "I(L_S3|XBVM3)", "I(R_S|XBVM3)",
                "I(L_M3|XBVM3)", "V(B_JS1|XBVM3)",
                "V(B_JS2|XBVM3)",
            ],
            "R-loop bridge partition across L_S3 candidates",
        ),
        (
            "comparison_n2_n3_chronology",
            candidate_cases(provenance),
            [
                "V(COMMON_SL)", "V(B_JS2|XBVM3)",
                "I(B_JS2|XBVM3)", "P(B_JS2|XBVM3)",
                "I(L_S3|XBVM3)", "I(R_S|XBVM3)",
                "P(B_JS1|XBVM3)", "V(B_JS1|XBVM3)",
                "P(BJ2|XBQ)", "I(L1|XBQ)",
            ],
            "N2/N3 exact-grid chronology and first-divergence signals",
        ),
        (
            "comparison_source_normalization",
            candidate_cases(provenance, include_r20=True),
            [
                "P(B_JS1|XBVM3)", "P(B_JS2|XBVM3)",
                "I(L_SL|XBVM3)",
            ],
            "per-active-cell source normalization with R20 endpoint",
        ),
        (
            "comparison_qb_jtl_terminal",
            candidate_cases(provenance, include_r20=True),
            [
                "P(BJ1|XBQ)", "P(BJ2|XBQ)",
                "P(B02|XJTL1_6)", "V(QBOUT)",
                "V(JTL6_OUT)", "I(R_TERM)",
            ],
            "QB/JTL/terminal cross-check across L_S3 candidates",
        ),
    ]
    comparison_entries: list[dict[str, Any]] = []
    comparison_dir = EXP / "plots" / "comparisons"
    comparison_dir.mkdir(parents=True, exist_ok=True)
    for stem, cases, signals, note in comparisons:
        temporary, labels = comparison_csv(cases, signals)
        output = comparison_dir / f"{stem}.html"
        try:
            render_external_page(
                temporary,
                output,
                labels,
                f"{EXP.name} | {note} | full raw 0-200 ps | P display rad/(2*pi)",
                asset,
            )
        finally:
            temporary.unlink(missing_ok=True)
        comparison_entries.append({
            "kind": "comparison",
            "comparison": stem,
            "path": rel(output),
            "source_cases": [
                {"case": case, "raw_path": rel(raw), "raw_sha256": sha256(raw)}
                for case, raw, _instance, _endpoint, _mapper in cases
            ],
            "signals": signals,
            "rendered_labels": labels,
            "window_ps": [0.0, 200.0],
            "full_window_only": True,
            "direction_note": note,
            "renderer": {"path": rel(PLOTTER), "sha256": sha256(PLOTTER)},
        })

    html_files = sorted(
        path for path in (EXP / "plots").rglob("*.html")
        if path.is_file()
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
    other_plot_files = [
        rel(path)
        for path in (EXP / "plots").rglob("*")
        if path.is_file() and path.suffix.lower() not in {".html", ".js"}
    ]
    viz_qa = {
        "status": "PASS" if asset.is_file() and not invalid_pages and not other_plot_files else "FAIL",
        "standalone_count": len(entries),
        "comparison_count": len(comparison_entries),
        "html_count": len(html_files),
        "asset": {
            "path": rel(asset),
            "sha256": sha256(asset) if asset.is_file() else None,
            "bytes": asset.stat().st_size if asset.is_file() else None,
        },
        "invalid_pages": invalid_pages,
        "other_plot_files": other_plot_files,
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
        "renderer": {
            "path": rel(PLOTTER),
            "sha256": sha256(PLOTTER),
            "layout": "sep_comb",
            "color": "dark",
            "phase_option": "2pi",
        },
        "asset": viz_qa["asset"],
        "standalone_pages": entries,
        "comparison_pages": comparison_entries,
        "standalone_count": len(entries),
        "comparison_count": len(comparison_entries),
        "html_count": len(html_files),
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


def repair_tool_provenance() -> None:
    provenance = read_json(EXP / "provenance.json")
    if provenance["execution"].get("actual_physical_solve_count", 0) == 0:
        raise RuntimeError("tool repair requires completed physical solves")
    runner = next(
        item for item in provenance["sources"] if item["name"] == "runner"
    )
    old_hash = runner["sha256"]
    new_hash = sha256(SCRIPT)
    runner["sha256"] = new_hash
    runner["bytes"] = SCRIPT.stat().st_size
    provenance["execution"]["solver_invocation_count"] = (
        provenance["execution"].get("failed_attempt_count", 0)
        + provenance["execution"].get("actual_physical_solve_count", 0)
    )
    registered_by_id = {
        item["run_id"]: item for item in provenance["registered_decks"]
    }
    for identifier, record in provenance["execution"].get(
        "run_records", {}
    ).items():
        if identifier in registered_by_id:
            record["variant_sha256"] = registered_by_id[identifier].get(
                "variant_sha256"
            )
    provenance.setdefault("tooling_revisions", []).append({
        "path": rel(SCRIPT),
        "old_sha256": old_hash,
        "new_sha256": new_hash,
        "reason": "analysis/visualization tooling correction; no raw or solver rerun",
        "raw_mutated": False,
    })
    write_provenance(provenance)
    print(json.dumps({
        "status": "PASS",
        "old_runner_sha256": old_hash,
        "new_runner_sha256": new_hash,
        "physical_rerun": False,
    }, ensure_ascii=False, indent=2))


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
        raise RuntimeError(f"refusing overwrite of existing ZIP: {package_path}")
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
        "status": (
            "READY_FOR_DRIVE_UPLOAD"
            if package_qa["status"] == "PASS"
            else "PACKAGE_INVALID"
        ),
        "qa": package_qa,
        "delivery_path": str(package_path),
        "drive_file_id": None,
        "drive_url": None,
    }
    write_provenance(provenance)
    result = read_json(EXP / "result.json")
    result["package_summary"] = {
        "status": provenance["package"]["status"],
        "package_sha256": package_qa["package_sha256"],
        "package_bytes": package_qa["package_bytes"],
        "file_count": package_qa["file_count"],
        "drive_file_id": None,
    }
    write_json(EXP / "result.json", result)
    (EXP / "RESULT.md").write_text(result_markdown(result), encoding="utf-8")
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
        raise RuntimeError("delivery ZIP is missing")
    if sha256(package_path) != package_qa.get("package_sha256"):
        raise RuntimeError("delivery ZIP changed before Drive record")
    package_info["drive_file_id"] = file_id
    package_info["drive_url"] = url
    package_info["drive_uploaded_at"] = now()
    package_info["status"] = "UPLOADED"
    provenance["package"] = package_info
    write_provenance(provenance)
    result = read_json(EXP / "result.json")
    result["package_summary"]["status"] = "UPLOADED"
    result["package_summary"]["drive_file_id"] = file_id
    result["package_summary"]["drive_url"] = url
    write_json(EXP / "result.json", result)
    (EXP / "RESULT.md").write_text(result_markdown(result), encoding="utf-8")
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
    elif command == "repair-probe":
        repair_duplicate_bjsl8_probe()
    elif command == "repair-tool":
        repair_tool_provenance()
    elif command == "execute":
        execute_stage_a()
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
            print(
                "usage: bvm_qb_rloop_ls3_causality.py "
                "drive-record FILE_ID [URL]",
                file=sys.stderr,
            )
            return 2
        record_drive_upload(
            sys.argv[2],
            sys.argv[3] if len(sys.argv) > 3 else None,
        )
    elif command == "all":
        prepare()
        execute_stage_a()
        analyze()
        mechanical_qa()
        visualization()
    else:
        print(
            "usage: bvm_qb_rloop_ls3_causality.py "
            "[prepare|repair-probe|repair-tool|execute|analyze|qa|viz|package|drive-record|all]",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
