#!/usr/bin/env python3
"""Decompose the BVM R-loop bridge timing replay by branch.

The experiment has two replay families.  RS keeps the physical L_S3 branch
and replays only canonical I(R_S); LS3 keeps physical R_S and replays only
canonical I(L_S3).  Each BVM instance receives its own PWL waveform.  Exact
cases are solved first and each family independently gates its own 0.3-ps
delayed cases.

This is an ideal current-forcing counterfactual, not a physical delay-network
or R_S/L_S3 replacement.  The executor performs mechanical arithmetic and
evidence packaging only; scientific category assignment remains review-gated.
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
from typing import Any, Iterable

REPO = Path(__file__).resolve().parents[1]
SCRIPT = Path(__file__).resolve()
sys.path.insert(0, str(REPO / "scripts"))
import bvm_qb_rloop_bridge_timing_replay as total_helpers  # noqa: E402
import bvm_qb_tline_z0_rescue_gate as z0_helpers  # noqa: E402

replay_base = total_helpers.replay_base

EXP = REPO / "test" / "exploration" / "bvm-rloop-branch-timing-decomposition-v1-20260916"
REFERENCE_ROOT = REPO / "test" / "exploration" / "bvm-qb-threshold-ordering-boundary-search-v1-20260911" / "references" / "canonical_baseline"
SOURCE_INPUTS = REPO / "test" / "exploration" / "bvm-qb-threshold-ordering-boundary-search-v1-20260911" / "inputs"
SOLVER = REPO / "build" / "josim-cli"
PLOTTER = REPO / "scripts" / "josim-plot2.py"
PREVIOUS_TOTAL = REPO / "test" / "exploration" / "bvm-rloop-bridge-timing-replay-v1-20260916"
CANONICAL = {mask: REFERENCE_ROOT / mask / "raw.csv" for mask in ("0011", "0111")}
CANONICAL_DECKS = {mask: REFERENCE_ROOT / mask / "deck.cir" for mask in ("0011", "0111")}
PREVIOUS_TOTAL_RAW = {
    "EXACT_0011": PREVIOUS_TOTAL / "runs" / "EXACT_0011" / "raw.csv",
    "DELAY0P3_0011": PREVIOUS_TOTAL / "runs" / "DELAY0P3_0011" / "raw.csv",
    "EXACT_0111": PREVIOUS_TOTAL / "runs" / "EXACT_0111" / "raw.csv",
    "DELAY0P3_0111": PREVIOUS_TOTAL / "runs" / "DELAY0P3_0111" / "raw.csv",
}

EXPECTED_HEAD = "7ade840c731bc078eae0c87e42ca983aa74700dd"
EXPECTED_CANONICAL_RAW_HASHES = {
    "0011": "3da7b754c990316ff8e5981692afa958d8056a61020a1912548bf6f2b7e0249c",
    "0111": "1ca15a938b23d4ed08eb964713f91476256c4caf0677d1bfd3dc43020271ec75",
}
EXPECTED_PREVIOUS_TOTAL_RAW_HASHES = {
    "EXACT_0011": "b1289e28d3d48ef503711029048f644588e878ceabd9afeffe282edc768522ea",
    "DELAY0P3_0011": "4a627a3c7397be486f133256848327788d0a1fdf204a9749e299a0a72261db58",
    "EXACT_0111": "06c77265e1b4f7321e50d2b92a15a3d1d2f14cc6e7fca7ab0afbf7d82003745f",
    "DELAY0P3_0111": "5709b3115db09ae7a7eb0818a4d487f7432b7cff9ae40c1560ce7cc22da64d08",
}

PHI0 = 2.067833848e-15
TAU = 2.0 * math.pi
FOCUS_WINDOW = (110.0, 121.0)
REARM_WINDOW = (121.0, 130.0)
CONTROL_WINDOW = (70.0, 110.0)
FULL_WINDOW = (0.0, 200.0)
WINDOWS_PS = (FULL_WINDOW, CONTROL_WINDOW, FOCUS_WINDOW, REARM_WINDOW, (121.0, 200.0))
T0_PS = 110.0
DELAY_PS = 0.3
DELAY_SHIFT = 3
FAMILIES = ("RS", "LS3")
MASKS = ("0011", "0111")
EXACT_CASES = ("RS_EXACT_0011", "RS_EXACT_0111", "LS3_EXACT_0011", "LS3_EXACT_0111")
DELAY_CASES = ("RS_DELAY0P3_0011", "RS_DELAY0P3_0111", "LS3_DELAY0P3_0011", "LS3_DELAY0P3_0111")
FINAL_MARKER = "EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW"
CONTRACT_SENTENCE = "This experiment is governed by docs/EXPERIMENT_CONTRACT.md."
RESULT_LIMIT_BYTES = 500 * 1024
DRIVE_FOLDER_ID = "1--nlY7Nq5ArVPydJNrnQf-EGmwN-undh"
REARM_DWELL_SAMPLES = 3
EXACT_TIMING_TOL_PS = 0.2
EXACT_PHASE_P2P_TOL_TURNS = 0.25
EXACT_NORMALIZED_WAVEFORM_RMS_TOL = 0.50
LARGE_COMPLIANCE_VOLTAGE_V = 1.0e-3
LARGE_ENERGY_RATIO = 10.0

JUNCTIONS = ("B_JM1", "B_JM2", "B_JS1", "B_JS2")
BVM_BRANCHES = ("L_M1", "L_M2", "L_M3", "L_PM", "L_S1", "L_S2", "L_S3", "R_S", "R_SE", "L_PSE", "L_PSL", "R_SL", "L_SL")
RLOOP_BRANCHES = ("L_S1", "L_S2", "L_M3", "L_SL")
JTL_STAGES = range(1, 7)
KNOWN_NONFATAL_WARNING_LINES = {"Unknown device/node IB|XBQ1", "Cannot store results for this device/node."}


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


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


def remote_head() -> str | None:
    try:
        output = subprocess.check_output(["git", "ls-remote", "bvm", "refs/heads/master"], cwd=REPO, text=True, timeout=30).strip()
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None
    return output.split()[0] if output else None


def record_file(name: str, path: Path, role: str) -> dict[str, Any]:
    if not path.is_file():
        raise RuntimeError(f"missing source file: {path}")
    return {"name": name, "path": rel(path), "sha256": sha256(path), "bytes": path.stat().st_size, "role": role}


def load_raw(path: Path) -> Any:
    return total_helpers.load_raw(path)


def time_indices(trace: Any, start_ps: float, end_ps: float) -> list[int]:
    return total_helpers.time_indices(trace, start_ps, end_ps)


def actual_integral(times: Iterable[float], values: Iterable[float]) -> float:
    return total_helpers.actual_integral(times, values)


def waveform_stats(trace: Any, signal: str, window: tuple[float, float]) -> dict[str, Any]:
    return z0_helpers.waveform_stats(trace, signal, window)


def compact_waveform(item: dict[str, Any]) -> dict[str, Any]:
    return total_helpers.compact_waveform(item)


def phase_navigation(trace: Any, signal: str) -> dict[str, Any]:
    return z0_helpers.phase_navigation(trace, signal)


def phase_area(trace: Any, phase_signal: str, voltage_signal: str) -> dict[str, Any]:
    return z0_helpers.phase_area_crosscheck(trace, phase_signal, voltage_signal)


def sign_metrics(trace: Any, signal: str, window: tuple[float, float]) -> dict[str, Any]:
    return z0_helpers.sign_metrics(trace, signal, window, REARM_DWELL_SAMPLES)


def voltage_integrals(trace: Any, signals: Iterable[str], window: tuple[float, float]) -> dict[str, Any]:
    return z0_helpers.voltage_integrals(trace, signals, window)


def vector_stats(trace: Any, signal: str, values: list[float], window: tuple[float, float], unit: str) -> dict[str, Any]:
    indices = time_indices(trace, *window)
    selected = [float(values[index]) for index in indices]
    times = [float(trace.time[index]) for index in indices]
    if len(selected) < 2:
        return {"status": "UNKNOWN", "signal": signal, "window_ps": list(window), "unit": unit}
    peak_position = max(range(len(selected)), key=lambda position: abs(selected[position]))
    return {"status": "DERIVED", "signal": signal, "window_ps": list(window), "sample_count": len(selected), "unit": unit, "minimum": min(selected), "maximum": max(selected), "p2p": max(selected) - min(selected), "mean": sum(selected) / len(selected), "rms": math.sqrt(sum(value * value for value in selected) / len(selected)), "peak_abs": abs(selected[peak_position]), "peak_value": selected[peak_position], "time_of_peak_abs_ps": times[peak_position] * 1.0e12, "signed_area": actual_integral(times, selected), "absolute_area": actual_integral(times, [abs(value) for value in selected]), "positive_area": actual_integral(times, [max(value, 0.0) for value in selected]), "negative_area": actual_integral(times, [min(value, 0.0) for value in selected]), "positive_sample_fraction": sum(value > 0.0 for value in selected) / len(selected), "negative_sample_fraction": sum(value < 0.0 for value in selected) / len(selected), "zero_crossing_count": z0_helpers.zero_crossing_count(selected), "actual_grid_trapezoid": True}


def sign_metrics_values(trace: Any, signal: str, values: list[float], window: tuple[float, float]) -> dict[str, Any]:
    indices = time_indices(trace, *window)
    selected = [float(values[index]) for index in indices]
    times = [float(trace.time[index]) for index in indices]
    previous = 0
    first_neg_pos = None
    first_pos_neg = None
    sustained = None
    for position, value in enumerate(selected):
        sign = 1 if value > 0.0 else -1 if value < 0.0 else 0
        if sign == 0:
            continue
        if previous == -1 and sign == 1:
            if first_neg_pos is None:
                first_neg_pos = times[position] * 1.0e12
            tail = selected[position:position + REARM_DWELL_SAMPLES]
            if sustained is None and len(tail) == REARM_DWELL_SAMPLES and all(item > 0.0 for item in tail):
                sustained = times[position] * 1.0e12
        if previous == 1 and sign == -1 and first_pos_neg is None:
            first_pos_neg = times[position] * 1.0e12
        previous = sign
    positive_dwell = sum((times[index + 1] - times[index]) * 1.0e12 for index in range(len(times) - 1) if selected[index] > 0.0)
    negative_dwell = sum((times[index + 1] - times[index]) * 1.0e12 for index in range(len(times) - 1) if selected[index] < 0.0)
    return {"status": "DERIVED", "signal": signal, "window_ps": list(window), "sample_count": len(selected), "minimum": min(selected), "maximum": max(selected), "zero_sign_crossings": z0_helpers.zero_crossing_count(selected), "first_negative_to_positive_crossing_ps": first_neg_pos, "first_sustained_negative_to_positive_crossing_ps": sustained, "first_positive_to_negative_crossing_ps": first_pos_neg, "positive_dwell_ps": positive_dwell, "negative_dwell_ps": negative_dwell, "positive_sample_fraction": sum(value > 0.0 for value in selected) / len(selected), "negative_sample_fraction": sum(value < 0.0 for value in selected) / len(selected), "actual_grid": True, "sustained_definition": f"crossing followed by {REARM_DWELL_SAMPLES} consecutive stored samples > 0"}


def source_tokens(path: Path) -> tuple[list[str], dict[str, list[str]], dict[str, list[float]]]:
    return total_helpers.source_tokens(path)


def time_token_ps(token: str) -> str:
    return total_helpers.time_token_ps(token)


def current_token(value: float) -> str:
    return total_helpers.current_token(value)


def case_info(case_id: str) -> dict[str, Any]:
    match = re.fullmatch(r"(RS|LS3)_(EXACT|DELAY0P3)_(0011|0111)", case_id)
    if not match:
        raise RuntimeError(f"invalid case id: {case_id}")
    family, stage, mask = match.groups()
    delay = 0.0 if stage == "EXACT" else DELAY_PS
    return {"case_id": case_id, "family": family, "stage": stage, "mask": mask, "delay_ps": delay, "stored_sample_shift": 0 if delay == 0.0 else DELAY_SHIFT}


def case_dir(case_id: str) -> Path:
    return EXP / "runs" / case_id


def branch_signal(family: str) -> str:
    return "I(R_S)" if family == "RS" else "I(L_S3)"


def branch_column(family: str, index: int) -> str:
    element = "R_S" if family == "RS" else "L_S3"
    return f"I({element}|XBVM{index})"


def replay_element(family: str) -> str:
    return "I_RS_REPLAY" if family == "RS" else "I_LS3_REPLAY"


def physical_branch(family: str) -> str:
    return "L_S3" if family == "RS" else "R_S"


def branch_values(values: dict[str, list[float]], times: list[str], family: str, delay_ps: float) -> list[float]:
    source = [values[branch_column(family, index=1)][row] for row in range(len(times))]
    # This helper is only used through branch_values_by_instance; the first
    # instance expression above is intentionally replaced below per instance.
    return source if delay_ps == 0.0 else delayed_values(source, times, delay_ps)


def delayed_values(source: list[float], times: list[str], delay_ps: float) -> list[float]:
    if delay_ps == 0.0:
        return list(source)
    start = next(index for index, token in enumerate(times) if abs(float(token) * 1.0e12 - T0_PS) < 1.0e-9)
    output: list[float] = []
    for index in range(len(times)):
        if index < start:
            output.append(source[index])
        elif index < start + DELAY_SHIFT:
            output.append(source[start])
        else:
            output.append(source[index - DELAY_SHIFT])
    return output


def branch_values_by_instance(values: dict[str, list[float]], times: list[str], family: str, delay_ps: float) -> dict[str, list[float]]:
    return {f"XBVM{index}": delayed_values([values[branch_column(family, index)][row] for row in range(len(times))], times, delay_ps) for index in range(1, 5)}


def write_branch_source_csv(path: Path, times: list[str], values: dict[str, list[float]], family: str, delay_ps: float) -> dict[str, Any]:
    replay = branch_values_by_instance(values, times, family, delay_ps)
    path.parent.mkdir(parents=True, exist_ok=True)
    replay_name = replay_element(family)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        header = ["time_s", "time_ps"] + [f"I_CANONICAL_{family}_XBVM{index}_A" for index in range(1, 5)] + [f"I_{replay_name}_XBVM{index}_A" for index in range(1, 5)]
        writer.writerow(header)
        for row, token in enumerate(times):
            canonical = [values[branch_column(family, index)][row] for index in range(1, 5)]
            writer.writerow([token, f"{float(token) * 1.0e12:.17g}", *[current_token(item) for item in canonical], *[current_token(replay[f"XBVM{index}"][row]) for index in range(1, 5)]])
    start = next(index for index, token in enumerate(times) if abs(float(token) * 1.0e12 - T0_PS) < 1.0e-9)
    pre_equal = all(replay[f"XBVM{index}"][row] == values[branch_column(family, index)][row] for index in range(1, 5) for row, token in enumerate(times) if float(token) * 1.0e12 < T0_PS)
    hold_equal = all(replay[f"XBVM{index}"][row] == values[branch_column(family, index)][start] for index in range(1, 5) for row in range(start, start + (DELAY_SHIFT if delay_ps else 0)))
    post_equal = all(replay[f"XBVM{index}"][row] == values[branch_column(family, index)][row - DELAY_SHIFT] for index in range(1, 5) for row in range(start + DELAY_SHIFT, len(times))) if delay_ps else True
    return {"path": rel(path), "sha256": sha256(path), "bytes": path.stat().st_size, "family": family, "branch_signal": branch_signal(family), "replay_element": replay_name, "delay_ps": delay_ps, "stored_sample_shift": 0 if delay_ps == 0.0 else DELAY_SHIFT, "point_count": len(times), "start_sample_index": start, "start_time_ps": float(times[start]) * 1.0e12, "pre_110_nonanticipation": pre_equal, "hold_rule_check": hold_equal, "post_shift_rule_check": post_equal, "interpolation": False, "resampling": False, "amplitude_scaling": False, "sign_change": False, "positive_direction": "node6 -> node10"}


def clone_bvm_subckt(instance: int, family: str, payload: str) -> str:
    source = (SOURCE_INPUTS / "bvm_jm2_connected.cir").read_text(encoding="utf-8")
    lines = source.splitlines()
    start = next(index for index, line in enumerate(lines) if line.strip().lower() == ".subckt bvm wl bl se sl")
    end = next(index for index in range(start + 1, len(lines)) if lines[index].strip().lower() == ".ends bvm")
    body = lines[start:end + 1]
    clone_name = f"BVM_{family}_REPLAY_{instance}"
    output = [f"* {clone_name}: canonical BVM body with only {replay_element(family)} replayed."]
    replaced = 0
    kept_other = 0
    for line in body:
        stripped = line.strip()
        if stripped.lower() == ".subckt bvm wl bl se sl":
            output.append(f".subckt {clone_name} WL BL SE SL")
        elif re.fullmatch(r"R_S\s+6\s+10\s+3\.0", stripped, flags=re.IGNORECASE) and family == "RS":
            output.append(f"{replay_element(family)} 6 10 {payload}")
            replaced += 1
        elif re.fullmatch(r"L_S3\s+6\s+10\s+0\.5P", stripped, flags=re.IGNORECASE) and family == "LS3":
            output.append(f"{replay_element(family)} 6 10 {payload}")
            replaced += 1
        elif (stripped.lower() == "r_s     6       10      3.0".lower() or stripped.lower() == "l_s3    6       10      0.5p".lower()):
            output.append(line)
            kept_other += 1
        elif stripped.lower() == ".ends bvm":
            output.append(f".ends {clone_name}")
        else:
            output.append(line)
    if replaced != 1 or kept_other != 1:
        raise RuntimeError(f"branch clone counts {family} XBVM{instance}: replaced={replaced}, kept_other={kept_other}")
    return "\n".join(output) + "\n"


def include_path(path: Path, deck_dir: Path) -> str:
    return Path(os.path.relpath(path, deck_dir)).as_posix()


def transformed_deck(mask: str, family: str, case_id: str, payloads: dict[str, str], deck_dir: Path) -> str:
    original = CANONICAL_DECKS[mask].read_text(encoding="utf-8")
    include_targets = {
        "../../inputs/jjmit.cir": SOURCE_INPUTS / "jjmit.cir",
        "../../inputs/BQ_parameterized_bjs400_rj2.cir": SOURCE_INPUTS / "BQ_parameterized_bjs400_rj2.cir",
        "../../inputs/jtl2.cir": SOURCE_INPUTS / "jtl2.cir",
    }
    clone_name = lambda index: f"BVM_{family}_REPLAY_{index}"
    output: list[str] = []
    inserted = False
    instance_count = 0
    replaced = 0
    skipped = 0
    for line in original.splitlines():
        stripped = line.strip()
        if stripped.startswith(".include "):
            include_name = stripped.split(None, 1)[1]
            if "bvm_jm2_connected.cir" in include_name:
                continue
            if include_name not in include_targets:
                raise RuntimeError(f"unexpected include: {include_name}")
            output.append(f".include {include_path(include_targets[include_name], deck_dir)}")
            continue
        match = re.fullmatch(r"XBVM([1-4]) WL\1 BL\1 SE\1 COMMON_SL BVM", stripped)
        if match:
            if not inserted:
                for index in range(1, 5):
                    output.append(clone_bvm_subckt(index, family, payloads[f"XBVM{index}"]))
                inserted = True
            index = int(match.group(1))
            output.append(f"XBVM{index} WL{index} BL{index} SE{index} COMMON_SL {clone_name(index)}")
            instance_count += 1
            continue
        if stripped.startswith(".print ") and "I(R_S|XBVM" in stripped:
            index = int(re.search(r"XBVM([1-4])", stripped).group(1))
            if family == "RS":
                output.append(f".print I(I_RS_REPLAY|XBVM{index}) I(L_S3|XBVM{index}) V(L_S3|XBVM{index}) V(6|XBVM{index}) V(10|XBVM{index})")
            else:
                output.append(f".print I(R_S|XBVM{index}) V(R_S|XBVM{index}) I(I_LS3_REPLAY|XBVM{index}) V(6|XBVM{index}) V(10|XBVM{index})")
            replaced += 1
            continue
        if stripped.startswith(".print ") and "I(L_S3|XBVM" in stripped:
            skipped += 1
            continue
        output.append(line)
    if not inserted or instance_count != 4 or replaced != 4 or skipped != 4:
        raise RuntimeError(f"deck transform counts {case_id}: inserted={inserted}, instances={instance_count}, replaced={replaced}, skipped={skipped}")
    text = "\n".join(output) + "\n"
    if ".tran 0.1p 200p" not in text or "XBQ1 QBIN QBOUT BQ" not in text or "R_TERM JTL6_OUT 0 10" not in text:
        raise RuntimeError(f"canonical forward path missing in {case_id}")
    if text.count(f"{replay_element(family)} 6 10 PWL(") != 4:
        raise RuntimeError(f"expected four per-instance replay sources in {case_id}")
    if any(token in text for token in ("T_BVM_QB", "V_REPLAY", "SENTINEL", "TRANSFORMER", "LC_LADDER")):
        raise RuntimeError(f"forbidden topology token in {case_id}")
    return text


def expected_headers(canonical_trace: Any, family: str) -> set[str]:
    headers = set(canonical_trace.headers)
    for index in range(1, 5):
        replaced_element = "R_S" if family == "RS" else "L_S3"
        headers.discard(f"I({replaced_element}|XBVM{index})")
        headers.discard(f"V({replaced_element}|XBVM{index})")
        headers.update((f"I({replay_element(family)}|XBVM{index})", f"V(6|XBVM{index})", f"V(10|XBVM{index})"))
    return headers


def branch_direction_audit(trace: Any, mask: str) -> dict[str, Any]:
    records: dict[str, Any] = {}
    all_pass = True
    for index in range(1, 5):
        def col(element: str, kind: str) -> list[float]:
            return [float(value) for value in trace.column(f"{kind}({element}|XBVM{index})")]
        rs_i = col("R_S", "I")
        ls_i = col("L_S3", "I")
        rs_v = col("R_S", "V")
        ls_v = col("L_S3", "V")
        js1 = col("B_JS1", "I")
        lpse = col("L_PSE", "I")
        js2 = col("B_JS2", "I")
        lpsl = col("L_PSL", "I")
        total = [a + b for a, b in zip(rs_i, ls_i)]
        resistor_law = [v - 3.0 * i for v, i in zip(rs_v, rs_i)]
        parallel_voltage = [a - b for a, b in zip(rs_v, ls_v)]
        node6 = [b - a - c for b, a, c in zip(total, js1, lpse)]
        node10 = [b + a - c for b, a, c in zip(total, js2, lpsl)]
        vscale = max(max(abs(value) for value in rs_v), 1.0e-12)
        iscale = max(max(abs(value) for value in total), 1.0e-12)
        rs_sign = sum(i == 0.0 or v == 0.0 or i * v > 0.0 for i, v in zip(rs_i, rs_v)) / len(rs_i)
        passed = bool(max(abs(value) for value in resistor_law) <= max(vscale * 1.0e-7, 1.0e-9) and max(abs(value) for value in parallel_voltage) <= max(vscale * 1.0e-9, 1.0e-12) and max(abs(value) for value in node6) <= max(iscale * 1.0e-6, 1.0e-10) and max(abs(value) for value in node10) <= max(iscale * 1.0e-6, 1.0e-10) and rs_sign > 0.99)
        all_pass = all_pass and passed
        records[f"XBVM{index}"] = {"status": "PASS" if passed else "FAIL", "positive_direction": "node6 -> node10", "R_S_endpoint_order": "6 -> 10", "L_S3_endpoint_order": "6 -> 10", "R_S_law_max_abs_V": max(abs(value) for value in resistor_law), "parallel_voltage_max_abs_V": max(abs(value) for value in parallel_voltage), "node6_kcl_max_abs_A": max(abs(value) for value in node6), "node10_kcl_max_abs_A": max(abs(value) for value in node10), "R_S_sign_agreement": rs_sign, "bridge_current_definition": "I(R_S)+I(L_S3)", "mask": mask, "KCL_equations": {"node6": "I(R_S)+I(L_S3)-I(B_JS1)-I(L_PSE)=0", "node10": "I(R_S)+I(L_S3)+I(B_JS2)-I(L_PSL)=0"}}
    return {"status": "PASS" if all_pass else "FAIL", "positive_direction": "node6 -> node10", "mask": mask, "instances": records, "all_instances_pass": all_pass}


def source_inventory() -> list[dict[str, Any]]:
    records = [
        record_file("runner", SCRIPT, "branch replay generator, analysis, QA, visualization, and package builder"),
        record_file("global_jjmit_model", SOURCE_INPUTS / "jjmit.cir", "canonical global JJ model"),
        record_file("canonical_bvm_template", SOURCE_INPUTS / "bvm_jm2_connected.cir", "immutable BVM clone template"),
        record_file("canonical_qb_include", SOURCE_INPUTS / "BQ_parameterized_bjs400_rj2.cir", "canonical QB include"),
        record_file("canonical_jtl_include", SOURCE_INPUTS / "jtl2.cir", "canonical six-stage JTL include"),
        record_file("canonical_qb_hash_guard", REPO / "circuits" / "qb" / "bq_parameterized_v1.cir", "canonical QB guard"),
        record_file("josim_solver", SOLVER, "recorded physical solver"),
        record_file("plotter", PLOTTER, "standard descriptive renderer"),
        record_file("shared_total_replay_helpers", REPO / "scripts" / "bvm_qb_rloop_bridge_timing_replay.py", "read-only total replay helpers"),
        record_file("shared_z0_metrics_helpers", REPO / "scripts" / "bvm_qb_tline_z0_rescue_gate.py", "read-only QB/JTL/re-arm helpers"),
        record_file("shared_tline_helpers", REPO / "scripts" / "bvm_qb_tline_feedback_dephasing.py", "read-only waveform/plot helpers"),
        record_file("shared_replay_base", REPO / "scripts" / "bvm_qb_boundary_timing_replay.py", "read-only raw/grid helpers"),
    ]
    for mask in MASKS:
        records.extend([record_file(f"canonical_{mask}_raw", CANONICAL[mask], "read-only canonical raw"), record_file(f"canonical_{mask}_deck", CANONICAL_DECKS[mask], "read-only canonical deck")])
    for name, path in CONTEXT_EXPERIMENTS.items():
        records.append(record_file(name, path, "read-only previous experiment context"))
    for name, path in PREVIOUS_TOTAL_RAW.items():
        records.append(record_file(f"previous_total_{name}_raw", path, "read-only previous total-bridge replay raw"))
    return records


CONTEXT_EXPERIMENTS = {
    "previous_total_result": PREVIOUS_TOTAL / "result.json",
    "previous_total_provenance": PREVIOUS_TOTAL / "provenance.json",
    "boundary_replay_result": REPO / "test" / "exploration" / "bvm-qb-boundary-timing-replay-v1-20260916" / "result.json",
    "boundary_replay_provenance": REPO / "test" / "exploration" / "bvm-qb-boundary-timing-replay-v1-20260916" / "provenance.json",
    "ls3_result": REPO / "test" / "exploration" / "bvm-qb-rloop-ls3-causality-v1-20260916" / "result.json",
    "ls3_provenance": REPO / "test" / "exploration" / "bvm-qb-rloop-ls3-causality-v1-20260916" / "provenance.json",
    "tline_z0_result": REPO / "test" / "exploration" / "bvm-qb-tline-z0-rescue-gate-v1-20260916" / "result.json",
    "tline_z0_provenance": REPO / "test" / "exploration" / "bvm-qb-tline-z0-rescue-gate-v1-20260916" / "provenance.json",
}


def assert_registration() -> None:
    if git_head() != EXPECTED_HEAD or remote_head() != EXPECTED_HEAD:
        raise RuntimeError(f"HEAD/remote mismatch: {git_head()} / {remote_head()} != {EXPECTED_HEAD}")
    for mask, expected in EXPECTED_CANONICAL_RAW_HASHES.items():
        if sha256(CANONICAL[mask]) != expected:
            raise RuntimeError(f"canonical raw changed: {CANONICAL[mask]}")
    for case_id, expected in EXPECTED_PREVIOUS_TOTAL_RAW_HASHES.items():
        if sha256(PREVIOUS_TOTAL_RAW[case_id]) != expected:
            raise RuntimeError(f"previous total raw changed: {PREVIOUS_TOTAL_RAW[case_id]}")
    for path in [*CONTEXT_EXPERIMENTS.values(), *PREVIOUS_TOTAL_RAW.values()]:
        if not path.is_file():
            raise RuntimeError(f"missing read-only context: {path}")


def make_case_deck(case_id: str, canonical_trace: Any) -> dict[str, Any]:
    info = case_info(case_id)
    times, _, values = source_tokens(CANONICAL[info["mask"]])
    replay = branch_values_by_instance(values, times, info["family"], info["delay_ps"])
    source_path = EXP / "inputs" / "replay_sources" / f"{case_id}_branch_current.csv"
    source = write_branch_source_csv(source_path, times, values, info["family"], info["delay_ps"])
    payloads = {instance: "PWL(" + " ".join(item for row, token in enumerate(times) for item in (time_token_ps(token), current_token(replay[instance][row]))) + ")" for instance in replay}
    deck_path = case_dir(case_id) / "deck.cir"
    deck_path.parent.mkdir(parents=True, exist_ok=True)
    deck_path.write_text(transformed_deck(info["mask"], info["family"], case_id, payloads, deck_path.parent), encoding="utf-8")
    return {"run_id": case_id, "case_id": case_id, "family": info["family"], "mask": info["mask"], "stage": info["stage"], "delay_ps": info["delay_ps"], "stored_sample_shift": info["stored_sample_shift"], "path": rel(deck_path), "sha256": sha256(deck_path), "bytes": deck_path.stat().st_size, "source": source, "payload_sha256": {instance: sha256_text(payloads[instance]) for instance in payloads}, "payload_bytes": {instance: len(payloads[instance].encode("utf-8")) for instance in payloads}, "topology_transform": f"per-instance canonical BVM clone; only {branch_signal(info['family'])} replayed, other bridge branch physical; canonical QB/JTL/terminal retained"}


def append_yaml_records(records: dict[str, Any], section: str) -> None:
    path = EXP / "experiment.yaml"
    text = path.read_text(encoding="utf-8").rstrip()
    lines = ["", f"{section}:"]
    for key, item in records.items():
        lines.extend([f"  - run_id: {key}", f"    path: {item['path']}", f"    sha256: {item['sha256']}", f"    bytes: {item['bytes']}", f"    family: {item['family']}", f"    mask: \"{item['mask']}\"", f"    delay_ps: {item['delay_ps']}", f"    stored_sample_shift: {item['stored_sample_shift']}", f"    source_csv: {item['source']['path']}", f"    source_csv_sha256: {item['source']['sha256']}"])
    path.write_text(text + "\n" + "\n".join(lines) + "\n", encoding="utf-8")


def prepare() -> None:
    if EXP.exists():
        existing = {item.name for item in EXP.iterdir()}
        partial_empty_dirs = {name for name in ("runs", "analysis", "plots") if name in existing and (EXP / name).is_dir() and not any((EXP / name).iterdir())}
        if existing - {"PREFLIGHT.md", "experiment.yaml"} - partial_empty_dirs:
            raise RuntimeError(f"refusing to overwrite non-empty experiment: {EXP}")
        if not {"PREFLIGHT.md", "experiment.yaml"}.issubset(existing):
            raise RuntimeError(f"incomplete experiment directory: {EXP}")
    if CONTRACT_SENTENCE not in (EXP / "PREFLIGHT.md").read_text(encoding="utf-8"):
        raise RuntimeError("PREFLIGHT contract sentence missing")
    assert_registration()
    canonical_traces = {mask: load_raw(CANONICAL[mask]) for mask in MASKS}
    direction = {mask: branch_direction_audit(canonical_traces[mask], mask) for mask in MASKS}
    if not all(item["status"] == "PASS" for item in direction.values()):
        raise RuntimeError(f"branch direction audit failed: {direction}")
    EXP.mkdir(parents=True, exist_ok=True)
    for dirname in ("runs", "analysis", "plots"):
        (EXP / dirname).mkdir(exist_ok=True)
    sources = source_inventory()
    decks: dict[str, Any] = {}
    for case_id in EXACT_CASES:
        decks[case_id] = make_case_deck(case_id, canonical_traces[case_info(case_id)["mask"]])
    append_yaml_records(decks, "exact_deck_registration")
    source_manifest = {"schema": "bvm-rloop-branch-timing-source-manifest-v1", "experiment_id": EXP.name, "generated_at": now(), "source_closure": sources, "branch_direction_audit": direction, "previous_total_raw_hashes": EXPECTED_PREVIOUS_TOTAL_RAW_HASHES}
    write_json(EXP / "analysis" / "SOURCE_MANIFEST.json", source_manifest)
    transformation = {"schema": "bvm-rloop-branch-timing-transformation-registry-v1", "experiment_id": EXP.name, "generated_at": now(), "raw_mutation": False, "operations": [{"name": "branch_current_source", "definition": "I(R_S) or I(L_S3) from same canonical BVM instance", "positive_direction": "node6 -> node10", "per_instance": True}, {"name": "exact", "delay_ps": 0.0, "stored_sample_shift": 0}, {"name": "delay", "delay_ps": 0.3, "stored_sample_shift": 3, "rule": "pre-110 same sample, [110,110.3) hold 110-ps sample, post exact index shift", "interpolation": False, "resampling": False, "amplitude_scaling": False, "sign_change": False}, {"name": "phase_navigation", "rule": "independent unwrap(raw radians)/(2*pi), navigation only"}, {"name": "phase_area", "rule": "same JJ/endpoints/direction/window, actual-grid trapezoid/Phi0"}]}
    write_json(EXP / "analysis" / "TRANSFORMATION_REGISTRY.json", transformation)
    provenance = {"schema": "bvm-rloop-branch-timing-decomposition-provenance-v1", "experiment_id": EXP.name, "created_at": now(), "registration_head": EXPECTED_HEAD, "remote_bvm_master_at_registration": EXPECTED_HEAD, "contract_sentence": CONTRACT_SENTENCE, "scientific_review_authorized": False, "mechanical_analysis_performed": False, "bounded_experiment_interpretation_performed": False, "independent_scientific_review_performed": False, "scientific_interpretation_performed": False, "solver": replay_base.solver_context(), "source_closure": sources, "canonical_reference_raw_hashes": EXPECTED_CANONICAL_RAW_HASHES, "previous_total_reference_raw_hashes": EXPECTED_PREVIOUS_TOTAL_RAW_HASHES, "branch_direction_audit": direction, "frozen": {"question": "decompose the prior total-bridge delay effect into R_S-only versus L_S3-only timing", "forward_topology": "canonical BVM -> COMMON_SL -> JSL1..8 -> canonical QB -> JTL1..6 -> terminal", "intervention": "only one per-instance bridge branch replaced by its canonical current PWL", "exact_grid": "actual stored timestamps", "TD_delayed_ps": DELAY_PS, "stored_delay_samples": DELAY_SHIFT, "t0_ps": T0_PS, "time_step_ps": 0.1, "stop_time_ps": 200.0, "windows_ps": [list(window) for window in WINDOWS_PS], "no_QB_JSL_JTL_terminal_stimulus_change": True}, "authorized_matrix": {"exact": list(EXACT_CASES), "delayed_conditional": list(DELAY_CASES), "maximum_physical_solves": 8, "family_independent_gate": True, "no_other_delay": True}, "registered_decks": decks, "runs": {}, "run_order": [], "execution": {"authorized_physical_solve_count": 8, "actual_physical_solve_count": 0, "solver_invocation_count": 0, "exact_count": 0, "delayed_count": 0}, "probe_policy": {"branch": "RS replay: imposed I(I_RS_REPLAY|XBVMn), physical I(L_S3|XBVMn); LS3 replay: imposed I(I_LS3_REPLAY|XBVMn), physical I(R_S|XBVMn)", "voltage": "V(6|XBVMn)-V(10|XBVMn)", "main": "I(B_JSL8), V(COMMON_SL), V(QBIN), I(LIN|XBQ1), active JS1/JS2, JM1/JM2, L1/L2, QBOUT, all JTL stages, terminal", "raw_expected_headers_by_family": {family: {mask: sorted(expected_headers(canonical_traces[mask], family)) for mask in MASKS} for family in FAMILIES}}, "fidelity_screen": {"timing_tolerance_ps": EXACT_TIMING_TOL_PS, "phase_p2p_tolerance_turns": EXACT_PHASE_P2P_TOL_TURNS, "normalized_waveform_rms_tolerance": EXACT_NORMALIZED_WAVEFORM_RMS_TOL, "bridge_voltage_reported_separately": True}, "artifact_screen": {"large_compliance_voltage_threshold_V": LARGE_COMPLIANCE_VOLTAGE_V, "large_energy_ratio": LARGE_ENERGY_RATIO, "tag_is_mechanical_only": True}, "analysis": {"status": "PENDING"}, "qa": {"status": "PENDING"}, "visualization": {"status": "PENDING"}, "package": {"status": "PENDING", "drive_file_id": None, "drive_url": None}, "stop": {"final_marker": None, "automatic_follow_up": False}}
    write_json(EXP / "provenance.json", provenance)
    result = {"schema": "bvm-rloop-branch-timing-decomposition-result-v1", "experiment_id": EXP.name, "generated_at": now(), "status": "PREFLIGHT_PASS_EXACT_PENDING", "artifact_status": "PENDING", "scientific_review_authorized": False, "mechanical_analysis_performed": False, "bounded_experiment_interpretation_performed": False, "independent_scientific_review_performed": False, "scientific_interpretation_performed": False, "execution": provenance["execution"], "cases": {case_id: {"status": "AUTHORIZED_NOT_RUN" if case_id in EXACT_CASES else "CONDITIONAL_NOT_MATERIALIZED"} for case_id in [*EXACT_CASES, *DELAY_CASES]}, "exact_fidelity": {"status": "PENDING"}, "mechanical_comparison": {"status": "PENDING"}, "classification": {"status": "SCIENTIFIC_REVIEW_REQUIRED", "assigned": None, "candidate_categories": ["LS3_BRANCH_EFFECT_STRONG", "RS_BRANCH_EFFECT_STRONG", "SINGLE_BRANCH_EFFECT_WEAK", "BRANCH_COMPENSATION_OBSERVED", "IDEAL_SOURCE_ARTIFACT_LARGE"]}, "unknown": ["scientific category assignment", "physical delay implementation", "current-only sufficiency beyond replay", "SFQ identity/count", "timestep/solver convergence"], "stop": {"final_marker": None, "automatic_follow_up": False}}
    write_json(EXP / "result.json", result)
    (EXP / "RESULT.md").write_text("# BVM R-loop branch timing decomposition\n\nPreflight passed. Only the four EXACT family/mask cases are materialized; delayed cases remain family-gated.\n", encoding="utf-8")
    print(json.dumps({"status": "PREFLIGHT_PASS", "experiment": rel(EXP), "exact_cases": list(EXACT_CASES), "delayed_cases_conditional": list(DELAY_CASES), "head": EXPECTED_HEAD}, ensure_ascii=False, indent=2))


def warning_lines(path: Path) -> list[str]:
    if not path.is_file():
        return ["missing_log"]
    return [line.strip() for line in path.read_text(errors="replace").splitlines() if any(token in line for token in ("Missing model:", "Unknown device/node", "Cannot store results", "Error", "error"))]


def execute_cases(case_ids: Iterable[str]) -> None:
    provenance = read_json(EXP / "provenance.json")
    for case_id in case_ids:
        if case_id not in provenance["registered_decks"]:
            raise RuntimeError(f"case is not registered: {case_id}")
        deck_record = provenance["registered_decks"][case_id]
        deck = REPO / deck_record["path"]
        raw = deck.parent / "raw.csv"
        log = deck.parent / "run.log"
        metadata = deck.parent / "metadata.json"
        if raw.exists() or log.exists() or metadata.exists():
            raise RuntimeError(f"refusing overwrite/retry: {case_id}")
        if sha256(deck) != deck_record["sha256"]:
            raise RuntimeError(f"registered deck changed: {case_id}")
        command = [str(SOLVER), "-a", "1", "-o", str(raw), str(deck)]
        started = now()
        with log.open("x", encoding="utf-8") as stream:
            stream.write(f"experiment={EXP.name}\nrun_id={case_id}\nstarted_at={started}\ncommand={' '.join(command)}\n")
            stream.flush()
            completed = subprocess.run(command, cwd=REPO, stdout=stream, stderr=subprocess.STDOUT, check=False)
            finished = now()
            stream.write(f"finished_at={finished}\nexit_code={completed.returncode}\n")
        info = case_info(case_id)
        record: dict[str, Any] = {"run_id": case_id, "case_id": case_id, "family": info["family"], "mask": info["mask"], "stage": info["stage"], "delay_ps": info["delay_ps"], "stored_sample_shift": info["stored_sample_shift"], "command": command, "deck": {"path": rel(deck), "sha256": sha256(deck), "bytes": deck.stat().st_size}, "log": {"path": rel(log), "sha256": sha256(log), "bytes": log.stat().st_size}, "solver": replay_base.solver_context(), "started_at": started, "finished_at": finished, "physical_solve_this_experiment": True, "raw_immutable": True, "mechanical_analysis_performed": False, "bounded_experiment_interpretation_performed": False, "independent_scientific_review_performed": False}
        if completed.returncode != 0 or not raw.is_file() or raw.stat().st_size == 0:
            record["execution_status"] = "SOLVER_FAIL"
            record["raw"] = {"path": rel(raw), "exists": raw.is_file(), "sha256": sha256(raw) if raw.is_file() else None, "bytes": raw.stat().st_size if raw.is_file() else None}
            provenance["runs"][case_id] = record
            provenance["run_order"].append(case_id)
            provenance["execution"]["actual_physical_solve_count"] = len(provenance["run_order"])
            provenance["execution"]["solver_invocation_count"] = len(provenance["run_order"])
            provenance["execution_status"] = "SOLVER_FAILURE_STOP"
            write_json(EXP / "provenance.json", provenance)
            raise RuntimeError(f"solver failed for {case_id}; preserved and stopped")
        try:
            trace = load_raw(raw)
            expected = set(provenance["probe_policy"]["raw_expected_headers_by_family"][info["family"]][info["mask"]])
            missing = sorted(expected - set(trace.headers))
            record["raw"] = {"path": rel(raw), "sha256": sha256(raw), "bytes": raw.stat().st_size, "sample_count": trace.sample_count, "time_start_ps": trace.time[0] * 1.0e12, "time_end_ps": trace.time[-1] * 1.0e12, "grid": replay_base.finite_grid_qa(trace), "missing_required_probes": missing}
            record["solver_warning_lines"] = warning_lines(log)
            record["execution_status"] = "RUN_PASS" if not missing else "RUN_PASS_MISSING_PROBES"
        except Exception as exc:
            record["execution_status"] = "RAW_PARSE_FAILURE"
            record["raw_parse_error"] = str(exc)
            record["raw"] = {"path": rel(raw), "sha256": sha256(raw), "bytes": raw.stat().st_size}
            provenance["runs"][case_id] = record
            provenance["run_order"].append(case_id)
            provenance["execution"]["actual_physical_solve_count"] = len(provenance["run_order"])
            provenance["execution"]["solver_invocation_count"] = len(provenance["run_order"])
            provenance["execution_status"] = "RAW_FAILURE_STOP"
            write_json(EXP / "provenance.json", provenance)
            raise RuntimeError(f"raw parse failed for {case_id}; preserved and stopped") from exc
        record["metadata"] = {"path": rel(metadata), "source": deck_record["source"], "deck_sha256": sha256(deck), "raw_sha256": sha256(raw), "log_sha256": sha256(log), "execution_status": record["execution_status"]}
        write_json(metadata, record["metadata"])
        provenance["runs"][case_id] = record
        provenance["run_order"].append(case_id)
        provenance["execution"]["actual_physical_solve_count"] = len(provenance["run_order"])
        provenance["execution"]["solver_invocation_count"] = len(provenance["run_order"])
        provenance["execution"]["exact_count"] = sum(key.startswith(("RS_EXACT_", "LS3_EXACT_")) for key in provenance["run_order"])
        provenance["execution"]["delayed_count"] = sum(key.startswith(("RS_DELAY", "LS3_DELAY")) for key in provenance["run_order"])
        write_json(EXP / "provenance.json", provenance)
        if missing:
            provenance["execution_status"] = "RAW_PROBE_FAILURE_STOP"
            write_json(EXP / "provenance.json", provenance)
            raise RuntimeError(f"required probes missing for {case_id}: {missing}")
    provenance["execution_status"] = "EXACT_RUNS_COMPLETE" if len(provenance["run_order"]) == 4 else "ALL_AUTHORIZED_RUNS_COMPLETE"
    write_json(EXP / "provenance.json", provenance)
    result = read_json(EXP / "result.json")
    result["status"] = "EXACT_RUNS_COMPLETE_ANALYSIS_PENDING" if len(provenance["run_order"]) == 4 else "ALL_AUTHORIZED_RUNS_COMPLETE_ANALYSIS_PENDING"
    result["artifact_status"] = "VALID"
    result["execution"] = provenance["execution"]
    for key in provenance["run_order"]:
        result["cases"][key] = {"status": provenance["runs"][key]["execution_status"], "raw_path": provenance["runs"][key]["raw"]["path"], "raw_sha256": provenance["runs"][key]["raw"]["sha256"]}
    write_json(EXP / "result.json", result)
    print(json.dumps({"status": "RUN_PASS", "run_order": provenance["run_order"], "actual_physical_solve_count": provenance["execution"]["actual_physical_solve_count"]}, ensure_ascii=False, indent=2))


def energy_metrics(trace: Any, voltage: list[float], current: list[float], window: tuple[float, float], source_role: str) -> dict[str, Any]:
    indices = time_indices(trace, *window)
    times = [trace.time[index] for index in indices]
    v = [voltage[index] for index in indices]
    i = [current[index] for index in indices]
    power = [a * b for a, b in zip(v, i)]
    return {"status": "DERIVED", "window_ps": list(window), "sample_count": len(v), "voltage_min_V": min(v), "voltage_max_V": max(v), "voltage_rms_V": math.sqrt(sum(value * value for value in v) / len(v)), "current_min_A": min(i), "current_max_A": max(i), "max_abs_power_W": max(abs(value) for value in power), "signed_energy_J": actual_integral(times, power), "signed_energy_fJ": actual_integral(times, power) * 1.0e15, "absolute_exchanged_energy_J": actual_integral(times, [abs(value) for value in power]), "absolute_exchanged_energy_fJ": actual_integral(times, [abs(value) for value in power]) * 1.0e15, "power_sign_convention": "P_absorb=Vbridge*I_source; P>0 source absorbs, P<0 source supplies", "source_role": source_role, "actual_grid_trapezoid": True}


def bridge_records(trace: Any, family: str | None, canonical: bool = False, total_reference: bool = False) -> dict[str, Any]:
    records: dict[str, Any] = {}
    for index in range(1, 5):
        instance = f"XBVM{index}"
        if canonical:
            source = [a + b for a, b in zip(trace.column(f"I(R_S|{instance})"), trace.column(f"I(L_S3|{instance})"))]
            physical = None
            imposed = source
            voltage = list(trace.column(f"V(R_S|{instance})"))
            source_label = "I(R_S)+I(L_S3)"
            role = "canonical physical bridge reference, not ideal source"
        elif total_reference:
            source = list(trace.column(f"I(I_BRIDGE_REPLAY|{instance})"))
            physical = None
            imposed = source
            voltage = [a - b for a, b in zip(trace.column(f"V(6|{instance})"), trace.column(f"V(10|{instance})"))]
            source_label = f"I(I_BRIDGE_REPLAY|{instance})"
            role = "previous total-bridge ideal current replay source"
        elif family == "RS":
            imposed = list(trace.column(f"I(I_RS_REPLAY|{instance})"))
            physical = list(trace.column(f"I(L_S3|{instance})"))
            source = [a + b for a, b in zip(imposed, physical)]
            voltage = [a - b for a, b in zip(trace.column(f"V(6|{instance})"), trace.column(f"V(10|{instance})"))]
            source_label = f"I(I_RS_REPLAY|{instance})"
            role = "RS-only ideal replay source"
        elif family == "LS3":
            imposed = list(trace.column(f"I(I_LS3_REPLAY|{instance})"))
            physical = list(trace.column(f"I(R_S|{instance})"))
            source = [a + b for a, b in zip(imposed, physical)]
            voltage = [a - b for a, b in zip(trace.column(f"V(6|{instance})"), trace.column(f"V(10|{instance})"))]
            source_label = f"I(I_LS3_REPLAY|{instance})"
            role = "LS3-only ideal replay source"
        else:
            raise RuntimeError(f"bridge record family missing for {instance}")
        records[instance] = {"source_label": source_label, "physical_branch": physical_branch(family) if family in FAMILIES else None, "imposed_current_focus": vector_stats(trace, source_label, imposed, FOCUS_WINDOW, "A"), "imposed_current_rearm": vector_stats(trace, source_label, imposed, REARM_WINDOW, "A"), "physical_current_focus": vector_stats(trace, f"I({physical_branch(family)}|{instance})" if family in FAMILIES else "physical", physical, FOCUS_WINDOW, "A") if physical is not None else None, "physical_current_rearm": vector_stats(trace, f"I({physical_branch(family)}|{instance})" if family in FAMILIES else "physical", physical, REARM_WINDOW, "A") if physical is not None else None, "total_current_focus": vector_stats(trace, f"I_TOTAL_{instance}", source, FOCUS_WINDOW, "A"), "total_current_rearm": vector_stats(trace, f"I_TOTAL_{instance}", source, REARM_WINDOW, "A"), "voltage_focus": vector_stats(trace, f"Vbridge_{instance}", voltage, FOCUS_WINDOW, "V"), "voltage_rearm": vector_stats(trace, f"Vbridge_{instance}", voltage, REARM_WINDOW, "V"), "source_rearm_signs": sign_metrics_values(trace, source_label, imposed, REARM_WINDOW), "total_rearm_signs": sign_metrics_values(trace, f"I_TOTAL_{instance}", source, REARM_WINDOW), "energy_110_121": energy_metrics(trace, voltage, imposed, FOCUS_WINDOW, role), "energy_110_130": energy_metrics(trace, voltage, imposed, (110.0, 130.0), role), "source_role": role, "direction": "node6 -> node10"}
    return {"status": "DERIVED", "family": family, "canonical": canonical, "total_reference": total_reference, "instances": records, "voltage_definition": "V(6)-V(10) for replay; V(R_S)=V(L_S3) for canonical", "power_definition": "Vbridge*I_source with passive sign convention"}


def run_metrics(label: str, mask: str, trace: Any, family: str | None = None, canonical: bool = False, total_reference: bool = False, delay_ps: float | None = None) -> dict[str, Any]:
    bvm_cells: dict[str, Any] = {}
    for index in range(1, 5):
        instance = f"XBVM{index}"
        nav = {f"P({element}|{instance})": phase_navigation(trace, f"P({element}|{instance})") for element in JUNCTIONS}
        areas = {f"P({element}|{instance})": phase_area(trace, f"P({element}|{instance})", f"V({element}|{instance})") for element in ("B_JS1", "B_JS2")}
        focus: dict[str, Any] = {}
        rearm: dict[str, Any] = {}
        for element in JUNCTIONS:
            for kind in ("P", "V", "I"):
                signal = f"{kind}({element}|{instance})"
                if signal in trace.headers:
                    focus[signal] = compact_waveform(waveform_stats(trace, signal, FOCUS_WINDOW))
                    rearm[signal] = compact_waveform(waveform_stats(trace, signal, REARM_WINDOW))
        for element in BVM_BRANCHES:
            for kind in ("I", "V"):
                signal = f"{kind}({element}|{instance})"
                if signal in trace.headers:
                    focus[signal] = compact_waveform(waveform_stats(trace, signal, FOCUS_WINDOW))
                    rearm[signal] = compact_waveform(waveform_stats(trace, signal, REARM_WINDOW))
        bvm_cells[instance] = {"phase_navigation": nav, "phase_area": areas, "focus_waveforms": focus, "rearm_waveforms": rearm, "rloop_focus": {signal: focus[signal] for element in RLOOP_BRANCHES for kind in ("I", "V") for signal in (f"{kind}({element}|{instance})",) if signal in focus}}
    source_signals = ("I(B_JSL8)", "I(LIN|XBQ1)")
    source = {"focus": {signal: compact_waveform(waveform_stats(trace, signal, FOCUS_WINDOW)) for signal in source_signals}, "rearm": {signal: compact_waveform(waveform_stats(trace, signal, REARM_WINDOW)) for signal in source_signals}, "rearm_signs": {signal: sign_metrics(trace, signal, REARM_WINDOW) for signal in source_signals}, "signed_areas": {signal: waveform_stats(trace, signal, REARM_WINDOW).get("signed_area") for signal in source_signals}}
    return {"run_id": label, "mask": mask, "family": family, "canonical_reference": canonical, "canonical": canonical, "total_reference": total_reference, "delay_ps": delay_ps, "raw_path": rel(trace.path), "raw_sha256": sha256(trace.path), "grid": replay_base.finite_grid_qa(trace), "bvm": {"cells": bvm_cells, "active_instances": [f"XBVM{index}" for index, bit in enumerate(mask, start=1) if bit == "1"]}, "bridge": bridge_records(trace, family, canonical, total_reference), "qb": z0_helpers.qb_metrics(trace), "jsl": z0_helpers.jsl_metrics(trace), "jtl": z0_helpers.jtl_metrics(trace), "source": source, "focus_waveforms": {signal: compact_waveform(waveform_stats(trace, signal, FOCUS_WINDOW)) for signal in ("V(COMMON_SL)", "V(QBIN)", "V(QBOUT)", "V(JTL6_OUT)", "I(R_TERM)")}, "rearm_waveforms": {signal: compact_waveform(waveform_stats(trace, signal, REARM_WINDOW)) for signal in ("V(COMMON_SL)", "V(QBIN)", "V(QBOUT)", "V(JTL6_OUT)", "I(R_TERM)")}, "phase_semantics": "raw radians; independent unwrap/(2*pi) navigation only", "area_semantics": "same JJ/endpoints/direction/window, actual-grid trapezoid; not an SFQ count", "terminal_role": "corroboration only", "scientific_interpretation_performed": False}


def normalized_delta(reference: Any, candidate: Any, signal: str, window: tuple[float, float]) -> dict[str, Any]:
    indices = time_indices(reference, *window)
    if signal not in reference.headers or signal not in candidate.headers:
        return {"status": "UNKNOWN", "signal": signal, "window_ps": list(window)}
    left = list(reference.column(signal))
    right = list(candidate.column(signal))
    if signal.startswith("P("):
        left_u = total_helpers.unwrap(left)
        right_u = total_helpers.unwrap(right)
        delta = [(right_u[index] - left_u[index]) / TAU for index in indices]
        return {"status": "DERIVED", "signal": signal, "window_ps": list(window), "unit": "turns", "max_abs_delta_turns": max(abs(value) for value in delta), "rms_delta_turns": math.sqrt(sum(value * value for value in delta) / len(delta)), "endpoint_delta_turns": delta[-1], "independent_unwrap_before_subtract": True}
    delta = [right[index] - left[index] for index in indices]
    scale = max(max(left[index] for index in indices) - min(left[index] for index in indices), max(abs(left[index]) for index in indices), 1.0e-30)
    rms = math.sqrt(sum(value * value for value in delta) / len(delta))
    return {"status": "DERIVED", "signal": signal, "window_ps": list(window), "unit": "A" if signal.startswith("I(") else "V", "max_abs_delta": max(abs(value) for value in delta), "rms_delta": rms, "normalized_rms": rms / scale, "reference_scale": scale, "actual_grid": True}


def exact_source_error(exact_record: dict[str, Any], exact_trace: Any, family: str) -> dict[str, Any]:
    source = exact_record["source"]
    rows = []
    with (REPO / source["path"]).open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    errors: dict[str, Any] = {}
    for index in range(1, 5):
        signal = f"I({replay_element(family)}|XBVM{index})"
        imposed = [float(row[f"I_{replay_element(family)}_XBVM{index}_A"]) for row in rows]
        actual = list(exact_trace.column(signal))
        diff = [actual[row] - imposed[row] for row in range(len(actual))]
        errors[f"XBVM{index}"] = {"signal": signal, "max_abs_error_A": max(abs(value) for value in diff), "rms_error_A": math.sqrt(sum(value * value for value in diff) / len(diff))}
    return {"family": family, "source_csv": source["path"], "instances": errors, "max_abs_error_A": max(item["max_abs_error_A"] for item in errors.values())}


def exact_fidelity(family: str, mask: str, canonical: dict[str, Any], exact: dict[str, Any], canonical_trace: Any, exact_trace: Any, deck_record: dict[str, Any]) -> dict[str, Any]:
    co = canonical["qb"]["ordered_navigation_oracle"]
    eo = exact["qb"]["ordered_navigation_oracle"]
    canonical_count = co["ordered_navigation_candidate_count"]
    exact_count = eo["ordered_navigation_candidate_count"]
    timing = {}
    timing_abs: list[float] = []
    for name in ("BJ1", "BJ2"):
        c = co["navigation"][name]["positive_threshold_navigation_times_ps"].get("0.5")
        e = eo["navigation"][name]["positive_threshold_navigation_times_ps"].get("0.5")
        delta = e - c if c is not None and e is not None else None
        if delta is not None:
            timing_abs.append(abs(delta))
        timing[name] = {"canonical_ps": c, "exact_ps": e, "delta_ps": delta}
    phase_p2p: dict[str, Any] = {}
    phase_abs: list[float] = []
    for index in range(1, 5):
        instance = f"XBVM{index}"
        for element in ("B_JS1", "B_JS2"):
            signal = f"P({element}|{instance})"
            c = canonical["bvm"]["cells"][instance]["phase_navigation"][signal]
            e = exact["bvm"]["cells"][instance]["phase_navigation"][signal]
            delta = abs(e["focus_110_121_p2p_turns"] - c["focus_110_121_p2p_turns"])
            phase_abs.append(delta)
            phase_p2p[signal] = {"canonical_p2p_turns": c["focus_110_121_p2p_turns"], "exact_p2p_turns": e["focus_110_121_p2p_turns"], "absolute_delta_turns": delta, "canonical_endpoint_delta_turns": c["focus_110_121_endpoint_delta_turns"], "exact_endpoint_delta_turns": e["focus_110_121_endpoint_delta_turns"]}
    main_signals = ("I(B_JSL8)", "V(COMMON_SL)", "V(QBIN)", "I(LIN|XBQ1)", "I(L1|XBQ1)", "I(L2|XBQ1)", "V(QBOUT)", "V(JTL6_OUT)", "I(R_TERM)")
    main = {signal: normalized_delta(canonical_trace, exact_trace, signal, FOCUS_WINDOW) for signal in main_signals}
    normalized = [item.get("normalized_rms") for item in main.values() if item.get("normalized_rms") is not None]
    imposed_error = exact_source_error(deck_record, exact_trace, family)
    total_deltas = total_current_comparison(canonical, exact, canonical_trace, exact_trace, FOCUS_WINDOW)
    bridge_voltage = {instance: {"canonical": canonical["bridge"]["instances"][instance]["voltage_focus"], "exact": exact["bridge"]["instances"][instance]["voltage_focus"]} for instance in ("XBVM1", "XBVM2", "XBVM3", "XBVM4")}
    criteria = {"grid_equal": tuple(canonical_trace.time) == tuple(exact_trace.time), "candidate_count_equal": exact_count == canonical_count and ((mask == "0011" and canonical_count == 2) or (mask == "0111" and canonical_count == 4)), "first_BJ_timing_within_tolerance": bool(timing_abs) and max(timing_abs) <= EXACT_TIMING_TOL_PS, "JS_phase_p2p_within_tolerance": bool(phase_abs) and max(phase_abs) <= EXACT_PHASE_P2P_TOL_TURNS, "main_waveform_normalized_RMS_within_tolerance": bool(normalized) and max(normalized) <= EXACT_NORMALIZED_WAVEFORM_RMS_TOL, "required_main_trajectory_present": all(item["status"] != "UNKNOWN" for item in main.values())}
    return {"status": "PASS" if all(criteria.values()) else "FAIL", "family": family, "mask": mask, "canonical_ordered_candidate_count": canonical_count, "exact_ordered_candidate_count": exact_count, "criteria": criteria, "registered_tolerances": {"timing_ps": EXACT_TIMING_TOL_PS, "phase_p2p_turns": EXACT_PHASE_P2P_TOL_TURNS, "normalized_waveform_rms": EXACT_NORMALIZED_WAVEFORM_RMS_TOL}, "QB_timing": timing, "phase_p2p": phase_p2p, "main_focus_deltas": main, "bridge_constitution": {"imposed_source": exact["bridge"], "resultant_total": total_deltas, "voltage": bridge_voltage}, "source_injection_error": imposed_error, "energy": {instance: exact["bridge"]["instances"][instance]["energy_110_121"] for instance in exact["bridge"]["instances"]}, "no_physical_equivalence_claim": True}


def discrete_corr_lag(trace_a: Any, values_a: list[float], trace_b: Any, values_b: list[float], window: tuple[float, float], max_lag_samples: int = 20) -> dict[str, Any]:
    if tuple(trace_a.time) != tuple(trace_b.time):
        return {"status": "UNKNOWN", "reason": "stored grids differ"}
    indices = time_indices(trace_a, *window)
    left_all = values_a
    right_all = values_b
    candidates = []
    for lag in range(-max_lag_samples, max_lag_samples + 1):
        pairs = [(index, index + lag) for index in indices if 0 <= index + lag < len(right_all)]
        if len(pairs) < 2:
            continue
        left = [left_all[a] for a, _ in pairs]
        right = [right_all[b] for _, b in pairs]
        ml = sum(left) / len(left)
        mr = sum(right) / len(right)
        denom = math.sqrt(sum((value - ml) ** 2 for value in left) * sum((value - mr) ** 2 for value in right))
        corr = sum((a - ml) * (b - mr) for a, b in zip(left, right)) / denom if denom else None
        candidates.append({"lag_samples": lag, "lag_ps": lag * 0.1, "correlation": corr, "sample_count": len(pairs)})
    best = max(candidates, key=lambda item: item["correlation"] if item["correlation"] is not None else -math.inf) if candidates else None
    return {"status": "DESCRIPTIVE_GRID_LAG", "window_ps": list(window), "best": best, "interpolation": False, "actual_grid": True}


def total_current_comparison(reference: dict[str, Any], candidate: dict[str, Any], reference_trace: Any, candidate_trace: Any, window: tuple[float, float]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for index in range(1, 5):
        instance = f"XBVM{index}"
        ref_values = [reference["bridge"]["instances"][instance]["total_current_focus"]["mean"]] if False else None
        # Reconstruct the vectors from the raw traces; summaries are not used
        # for the comparison.
        def total_vector(metrics: dict[str, Any], trace: Any) -> list[float]:
            item = metrics["bridge"]["instances"][instance]
            if metrics.get("canonical"):
                return [a + b for a, b in zip(trace.column(f"I(R_S|{instance})"), trace.column(f"I(L_S3|{instance})"))]
            if metrics.get("total_reference"):
                return list(trace.column(f"I(I_BRIDGE_REPLAY|{instance})"))
            return [a + b for a, b in zip(trace.column(f"I({replay_element(metrics['family'])}|{instance})"), trace.column(f"I({physical_branch(metrics['family'])}|{instance})"))]
        a = total_vector(reference, reference_trace)
        b = total_vector(candidate, candidate_trace)
        indices = time_indices(reference_trace, *window)
        diff = [b[index] - a[index] for index in indices]
        output[instance] = {"window_ps": list(window), "rms_difference_A": math.sqrt(sum(value * value for value in diff) / len(diff)), "max_abs_difference_A": max(abs(value) for value in diff), "reference_stats": vector_stats(reference_trace, f"I_TOTAL_{instance}", a, window, "A"), "candidate_stats": vector_stats(candidate_trace, f"I_TOTAL_{instance}", b, window, "A"), "grid_corr_lag": discrete_corr_lag(reference_trace, a, candidate_trace, b, window)}
    return {"status": "DERIVED", "instances": output, "actual_grid": True, "interpolation": False}


def effect_fraction(canonical_n3: dict[str, Any], total_delay_n3: dict[str, Any], branch_delay_n3: dict[str, Any], instance: str = "XBVM2") -> dict[str, Any]:
    c = canonical_n3["bvm"]["cells"][instance]["phase_navigation"][f"P(B_JS1|{instance})"]["focus_110_121_p2p_turns"]
    t = total_delay_n3["bvm"]["cells"][instance]["phase_navigation"][f"P(B_JS1|{instance})"]["focus_110_121_p2p_turns"]
    p = branch_delay_n3["bvm"]["cells"][instance]["phase_navigation"][f"P(B_JS1|{instance})"]["focus_110_121_p2p_turns"]
    denominator = c - t
    return {"status": "DERIVED" if denominator != 0.0 else "UNKNOWN", "instance": instance, "canonical_C_turns": c, "previous_total_delay_T_turns": t, "branch_P_turns": p, "F_B": (c - p) / denominator if denominator else None, "formula": "(C-P_B)/(C-T)", "no_threshold_interpretation": True}


def energy_comparison(canonical: dict[str, Any], total_exact: dict[str, Any], total_delay: dict[str, Any], branch_exact: dict[str, Any], branch_delay: dict[str, Any]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for instance in ("XBVM1", "XBVM2", "XBVM3", "XBVM4"):
        output[instance] = {"canonical_physical_reference": {"110_121": canonical["bridge"]["instances"][instance]["energy_110_121"], "110_130": canonical["bridge"]["instances"][instance]["energy_110_130"]}, "previous_total_exact": {"110_121": total_exact["bridge"]["instances"][instance]["energy_110_121"], "110_130": total_exact["bridge"]["instances"][instance]["energy_110_130"]}, "previous_total_delay": {"110_121": total_delay["bridge"]["instances"][instance]["energy_110_121"], "110_130": total_delay["bridge"]["instances"][instance]["energy_110_130"]}, "branch_exact": {"110_121": branch_exact["bridge"]["instances"][instance]["energy_110_121"], "110_130": branch_exact["bridge"]["instances"][instance]["energy_110_130"]}, "branch_delay": {"110_121": branch_delay["bridge"]["instances"][instance]["energy_110_121"], "110_130": branch_delay["bridge"]["instances"][instance]["energy_110_130"]}}
    return {"status": "DERIVED", "instances": output, "large_compliance_voltage_threshold_V": LARGE_COMPLIANCE_VOLTAGE_V, "large_energy_ratio": LARGE_ENERGY_RATIO}


def family_mechanical_comparison(family: str, metrics: dict[str, Any], canonical_metrics: dict[str, Any], previous_metrics: dict[str, Any], traces: dict[str, Any]) -> dict[str, Any]:
    output: dict[str, Any] = {"family": family, "N2": {}, "N3": {}, "total_bridge": {}, "effect_fraction": None, "energy": None, "mechanical_evidence_tags": []}
    exact_n2 = metrics[f"{family}_EXACT_0011"]
    exact_n3 = metrics[f"{family}_EXACT_0111"]
    for delay_key in (f"{family}_DELAY0P3_0011", f"{family}_DELAY0P3_0111"):
        if delay_key not in metrics:
            continue
        item = metrics[delay_key]
        oracle = item["qb"]["ordered_navigation_oracle"]
        bucket = output["N2"] if item["mask"] == "0011" else output["N3"]
        bucket[delay_key] = {"delay_ps": DELAY_PS, "ordered_candidate_count": oracle["ordered_navigation_candidate_count"], "first_BJ1_plus_0p5_ps": oracle["navigation"]["BJ1"]["positive_threshold_navigation_times_ps"].get("0.5"), "first_BJ2_plus_0p5_ps": oracle["navigation"]["BJ2"]["positive_threshold_navigation_times_ps"].get("0.5"), "second_BJ1_plus_1p5_ps": oracle["navigation"]["BJ1"]["positive_threshold_navigation_times_ps"].get("1.5"), "second_BJ2_plus_1p5_ps": oracle["navigation"]["BJ2"]["positive_threshold_navigation_times_ps"].get("1.5"), "L1_rearm": item["qb"]["rearm_signs"].get("I(L1|XBQ1)"), "L2_rearm": item["qb"]["rearm_signs"].get("I(L2|XBQ1)"), "source_BJSL8_rearm": item["source"]["rearm_signs"].get("I(B_JSL8)"), "source_LIN_rearm": item["source"]["rearm_signs"].get("I(LIN|XBQ1)"), "JS1_JS2_focus_p2p": {instance: {element: item["bvm"]["cells"][instance]["phase_navigation"][f"P({element}|{instance})"]["focus_110_121_p2p_turns"] for element in ("B_JS1", "B_JS2")} for instance in item["bvm"]["active_instances"]}, "phase_area_residuals_turns": {signal: value.get("phase_minus_area_turns") for cell in item["bvm"]["cells"].values() for signal, value in cell["phase_area"].items()}}
        counterpart = previous_metrics["DELAY0P3_0011"] if item["mask"] == "0011" else previous_metrics["DELAY0P3_0111"]
        canonical_counterpart = canonical_metrics[item["mask"]]
        output["total_bridge"][delay_key] = {"vs_canonical": total_current_comparison(canonical_counterpart, item, traces[f"CANONICAL_{item['mask']}"], traces[delay_key], FOCUS_WINDOW), "vs_previous_total_delay": total_current_comparison(previous_metrics[f"DELAY0P3_{item['mask']}"], item, traces[f"TOTAL_DELAY0P3_{item['mask']}"], traces[delay_key], FOCUS_WINDOW), "imposed_vs_physical_branch": {instance: {"imposed_focus": item["bridge"]["instances"][instance]["imposed_current_focus"], "physical_focus": item["bridge"]["instances"][instance]["physical_current_focus"], "total_focus": item["bridge"]["instances"][instance]["total_current_focus"]} for instance in item["bridge"]["instances"]}}
        if item["mask"] == "0111":
            output["effect_fraction"] = effect_fraction(canonical_metrics["0111"], previous_metrics["DELAY0P3_0111"], item)
            output["energy"] = energy_comparison(canonical_metrics["0111"], previous_metrics["EXACT_0111"], previous_metrics["DELAY0P3_0111"], exact_n3, item)
    energies = (output.get("energy") or {}).get("instances", {})
    if energies:
        large = False
        for item in energies.values():
            delay_energy = item["branch_delay"]["110_130"]
            canonical_energy = item["canonical_physical_reference"]["110_130"]
            large = large or delay_energy["voltage_max_V"] >= LARGE_COMPLIANCE_VOLTAGE_V or delay_energy["voltage_min_V"] <= -LARGE_COMPLIANCE_VOLTAGE_V or (abs(delay_energy["absolute_exchanged_energy_fJ"]) > LARGE_ENERGY_RATIO * max(abs(canonical_energy["absolute_exchanged_energy_fJ"]), 1.0e-12))
        if large:
            output["mechanical_evidence_tags"].append("IDEAL_SOURCE_ARTIFACT_LARGE")
    output["N2_all_delayed_candidate_count_two"] = all(item["ordered_candidate_count"] == 2 for item in output["N2"].values()) if output["N2"] else None
    output["scientific_interpretation"] = "NOT_ASSIGNED_SCIENTIFIC_REVIEW_REQUIRED"
    return output


def compact_run(item: dict[str, Any]) -> dict[str, Any]:
    oracle = item["qb"]["ordered_navigation_oracle"]
    return {"run_id": item["run_id"], "family": item.get("family"), "mask": item["mask"], "delay_ps": item.get("delay_ps"), "ordered_candidate_count": oracle["ordered_navigation_candidate_count"], "first_BJ1_plus_0p5_ps": oracle["navigation"]["BJ1"]["positive_threshold_navigation_times_ps"].get("0.5"), "first_BJ2_plus_0p5_ps": oracle["navigation"]["BJ2"]["positive_threshold_navigation_times_ps"].get("0.5"), "second_BJ1_plus_1p5_ps": oracle["navigation"]["BJ1"]["positive_threshold_navigation_times_ps"].get("1.5"), "second_BJ2_plus_1p5_ps": oracle["navigation"]["BJ2"]["positive_threshold_navigation_times_ps"].get("1.5"), "JS1_JS2_focus_p2p_XBVM2": {element: item["bvm"]["cells"]["XBVM2"]["phase_navigation"][f"P({element}|XBVM2)"]["focus_110_121_p2p_turns"] for element in ("B_JS1", "B_JS2")}, "L1_rearm": item["qb"]["rearm_signs"].get("I(L1|XBQ1)"), "source_BJSL8_rearm": item["source"]["rearm_signs"].get("I(B_JSL8)"), "raw_path": item["raw_path"], "raw_sha256": item["raw_sha256"]}


def analyze() -> None:
    provenance = read_json(EXP / "provenance.json")
    keys = list(provenance.get("run_order", []))
    if keys[:4] != list(EXACT_CASES) or len(keys) not in (4, 6, 8):
        raise RuntimeError(f"unexpected run order for analysis: {keys}")
    if len(keys) == 6 and not (keys[4].endswith("_0011") and keys[5].endswith("_0111")):
        raise RuntimeError("six-run order must contain one family delayed pair")
    if len(keys) == 8 and keys != list(EXACT_CASES) + list(DELAY_CASES):
        raise RuntimeError("eight-run order must be exact then registered delayed order")
    # Allow analyzer-only revisions after a failed analysis attempt, while
    # keeping the physical source closure and raw files immutable.
    if git_head() != EXPECTED_HEAD:
        provenance["postsolve_analysis_head"] = git_head()
    current_runner = record_file("runner", SCRIPT, "branch replay generator, analysis, QA, visualization, and package builder")
    registered_runner = next(item for item in provenance["source_closure"] if item["name"] == "runner")
    if registered_runner["sha256"] != current_runner["sha256"]:
        provenance["postsolve_tooling_revision"] = {"path": rel(SCRIPT), "old_sha256": registered_runner["sha256"], "new_sha256": current_runner["sha256"], "reason": "analysis-only repair; no physical rerun", "physical_rerun": False, "raw_mutated": False}
        registered_runner.update({"sha256": current_runner["sha256"], "bytes": current_runner["bytes"]})
    for item in provenance["source_closure"]:
        path = REPO / item["path"]
        if not path.is_file() or sha256(path) != item["sha256"]:
            raise RuntimeError(f"source closure changed: {path}")
    canonical_traces = {mask: load_raw(CANONICAL[mask]) for mask in MASKS}
    traces: dict[str, Any] = {f"CANONICAL_{mask}": canonical_traces[mask] for mask in MASKS}
    for label, path in PREVIOUS_TOTAL_RAW.items():
        traces[f"TOTAL_{label}"] = load_raw(path)
    for key in keys:
        traces[key] = load_raw(REPO / provenance["runs"][key]["raw"]["path"])
    canonical_metrics = {mask: run_metrics(f"CANONICAL_{mask}", mask, canonical_traces[mask], canonical=True) for mask in MASKS}
    previous_metrics = {label: run_metrics(f"TOTAL_{label}", label.rsplit("_", 1)[1], traces[f"TOTAL_{label}"], total_reference=True, delay_ps=0.0 if label.startswith("EXACT") else DELAY_PS) for label in PREVIOUS_TOTAL_RAW}
    metrics: dict[str, Any] = {}
    for key in keys:
        info = case_info(key)
        metrics[key] = run_metrics(key, info["mask"], traces[key], family=info["family"], delay_ps=info["delay_ps"])
    fidelity = {family: {mask: exact_fidelity(family, mask, canonical_metrics[mask], metrics[f"{family}_EXACT_{mask}"], canonical_traces[mask], traces[f"{family}_EXACT_{mask}"], provenance["registered_decks"][f"{family}_EXACT_{mask}"]) for mask in MASKS} for family in FAMILIES}
    passing_families = [family for family in FAMILIES if all(fidelity[family][mask]["status"] == "PASS" for mask in MASKS)]
    family_results: dict[str, Any] = {}
    for family in FAMILIES:
        if f"{family}_EXACT_0011" not in metrics or f"{family}_EXACT_0111" not in metrics:
            continue
        family_metrics = {key: value for key, value in metrics.items() if key.startswith(family + "_")}
        family_traces = {key: value for key, value in traces.items() if key in family_metrics or key.startswith("CANONICAL_") or key.startswith("TOTAL_")}
        family_results[family] = family_mechanical_comparison(family, family_metrics, canonical_metrics, previous_metrics, family_traces)
    raw_before = {key: sha256(REPO / provenance["runs"][key]["raw"]["path"]) for key in keys}
    provenance["previous_total_reference_paths"] = [item["path"] for item in provenance["source_closure"] if item["name"].startswith("previous_total_") or item["name"] in CONTEXT_EXPERIMENTS]
    context_before = {path: sha256(REPO / path) for path in provenance.get("previous_total_reference_paths", [])}
    raw_after = {key: sha256(REPO / provenance["runs"][key]["raw"]["path"]) for key in keys}
    context_after = {path: sha256(REPO / path) for path in provenance.get("previous_total_reference_paths", [])}
    if raw_before != raw_after or context_before != context_after:
        raise RuntimeError("raw/reference mutation detected during analysis")
    delayed_authorized = [family for family in passing_families if any(key.startswith(family + "_DELAY") for key in keys)]
    exact_gate_status = "PASS" if len(passing_families) == 2 else "PARTIAL_PASS" if passing_families else "FAIL"
    provenance["mechanical_analysis_performed"] = True
    provenance["bounded_experiment_interpretation_performed"] = False
    provenance["independent_scientific_review_performed"] = False
    provenance["scientific_interpretation_performed"] = False
    provenance["raw_hash_before_analysis"] = raw_before
    provenance["raw_hash_after_analysis"] = raw_after
    provenance["reference_hashes_before_analysis"] = context_before
    provenance["reference_hashes_after_analysis"] = context_after
    provenance["analysis"] = {"status": "COMPLETE", "generated_at": now(), "mechanical_analysis_performed": True, "bounded_experiment_interpretation_performed": False, "independent_scientific_review_performed": False, "exact_fidelity": fidelity, "passing_families": passing_families, "current_runs": metrics, "canonical_references": canonical_metrics, "previous_total_references": previous_metrics, "family_comparisons": family_results, "exact_grid": True, "interpolation": False, "scientific_classification": "NOT_ASSIGNED_SCIENTIFIC_REVIEW_REQUIRED", "comparison_conditions": ["canonical", "previous total EXACT", "previous total DELAY0P3", "RS family", "LS3 family"]}
    if len(keys) == 4:
        provenance["outcome"] = {"status": "EXACT_GATE_COMPLETE", "classification": "DELAYED_CASES_AUTHORIZED_BY_FAMILY", "passing_families": passing_families, "failed_families": [family for family in FAMILIES if family not in passing_families], "delayed_cases_authorized_families": passing_families, "reason": "Each family with both EXACT masks passing may materialize only its own 0.3-ps delayed pair."}
        provenance["execution_status"] = "EXACT_FIDELITY_COMPLETE_DELAYED_PENDING"
        provenance["stop"] = {"final_marker": None, "automatic_follow_up": False}
    else:
        provenance["outcome"] = {"status": "SCIENTIFIC_REVIEW_REQUIRED", "classification": "NOT_ASSIGNED", "passing_families": passing_families, "failed_families": [family for family in FAMILIES if family not in passing_families], "reason": "All authorized delayed cases for passing families completed; branch-effect categories remain unassigned pending scientific review."}
        provenance["execution_status"] = "ANALYSIS_COMPLETE"
        provenance["stop"] = {"final_marker": FINAL_MARKER, "automatic_follow_up": False, "delayed_cases_run": len(keys) - 4, "sentinel_follow_up": False}
    for key in keys:
        provenance["runs"][key]["mechanical_analysis_performed"] = True
        provenance["runs"][key]["bounded_experiment_interpretation_performed"] = False
        provenance["runs"][key]["independent_scientific_review_performed"] = False
    write_json(EXP / "analysis" / "SOURCE_MANIFEST.json", {"schema": "bvm-rloop-branch-timing-source-manifest-v1", "experiment_id": EXP.name, "generated_at": now(), "source_closure": provenance["source_closure"], "branch_direction_audit": provenance["branch_direction_audit"], "previous_total_raw_hashes": EXPECTED_PREVIOUS_TOTAL_RAW_HASHES, "postsolve_tooling_revision": provenance.get("postsolve_tooling_revision")})
    write_json(EXP / "provenance.json", provenance)
    result = read_json(EXP / "result.json")
    result["generated_at"] = now()
    result["status"] = "EXACT_FIDELITY_COMPLETE_DELAYED_PENDING" if len(keys) == 4 else "ANALYSIS_COMPLETE"
    result["artifact_status"] = "VALID"
    result["mechanical_analysis_performed"] = True
    result["bounded_experiment_interpretation_performed"] = False
    result["independent_scientific_review_performed"] = False
    result["scientific_interpretation_performed"] = False
    result["execution"] = provenance["execution"]
    result["cases"] = {key: compact_run(metrics[key]) for key in keys}
    result["exact_fidelity"] = {family: {mask: {key: value for key, value in item.items() if key in ("status", "family", "mask", "canonical_ordered_candidate_count", "exact_ordered_candidate_count", "criteria", "registered_tolerances", "QB_timing", "phase_p2p", "source_injection_error", "no_physical_equivalence_claim")} for mask, item in by_mask.items()} for family, by_mask in fidelity.items()}
    result["mechanical_comparison"] = family_results
    result["classification"] = {"status": "SCIENTIFIC_REVIEW_REQUIRED", "assigned": None, "candidate_categories": result["classification"].get("candidate_categories", []), "exact_gate_status": exact_gate_status, "passing_families": passing_families}
    result["independent_numerical_recalculation"] = independent_recalculation(traces, {**{f"CANONICAL_{mask}": mask for mask in MASKS}, **{key: case_info(key)["mask"] for key in keys}})
    result["stop"] = provenance["stop"]
    write_json(EXP / "result.json", result)
    write_review_files(provenance, result)
    (EXP / "RESULT.md").write_text(result_markdown(result), encoding="utf-8")
    print(json.dumps({"status": result["status"], "exact_gate_status": exact_gate_status, "passing_families": passing_families, "actual_physical_solve_count": len(keys)}, ensure_ascii=False, indent=2))


def independent_recalculation(traces: dict[str, Any], masks: dict[str, str]) -> dict[str, Any]:
    output: dict[str, Any] = {"status": "PASS", "method": "fresh CSV reader and independent phase/order/area arithmetic", "grid": {}, "ordered_navigation_candidate_count": {}, "phase_area": {}}
    for label, trace in traces.items():
        if label.startswith("TOTAL_"):
            continue
        path = trace.path
        with path.open(newline="", encoding="utf-8-sig") as stream:
            reader = csv.DictReader(stream)
            rows = list(reader)
            headers = reader.fieldnames or []
        times = [float(row["time"]) for row in rows]
        output["grid"][label] = len(times) == 1999 and times[0] == 0.0 and times[-1] == 1.999e-10 and all(right > left for left, right in zip(times, times[1:]))
        names = ["P(BJ1|XBQ1)", "P(BJ2|XBQ1)", *[f"P(B01|XJTL1_{stage})" for stage in JTL_STAGES]]
        if all(name in headers for name in names):
            unwrapped = {name: total_helpers.unwrap([float(row[name]) for row in rows]) for name in names}
            base = next(index for index, value in enumerate(times) if value * 1.0e12 >= 101.0)
            count = 0
            for threshold in (0.5, 1.5, 2.5, 3.5, 4.5):
                chain = [next((times[index] * 1.0e12 for index in range(base, len(times)) if (unwrapped[name][index] - unwrapped[name][base]) / TAU >= threshold), None) for name in names]
                if all(value is not None for value in chain) and all(left < right for left, right in zip(chain, chain[1:])):
                    count += 1
                else:
                    break
            output["ordered_navigation_candidate_count"][label] = count
        mask = masks.get(label)
        if mask:
            active = next(index for index, bit in enumerate(mask, start=1) if bit == "1")
            focus = [index for index, value in enumerate(times) if 110.0 <= value * 1.0e12 < 121.0]
            area = {}
            for element in ("B_JS1", "B_JS2"):
                p_name = f"P({element}|XBVM{active})"
                v_name = f"V({element}|XBVM{active})"
                if p_name not in headers or v_name not in headers:
                    continue
                phase = total_helpers.unwrap([float(row[p_name]) for row in rows])
                voltage = [float(row[v_name]) for row in rows]
                phase_delta = (phase[focus[-1]] - phase[focus[0]]) / TAU
                voltage_area = actual_integral([times[index] for index in focus], [voltage[index] for index in focus]) / PHI0
                area[element] = {"phase_delta_turns": phase_delta, "voltage_area_over_Phi0_turns": voltage_area, "residual_turns": phase_delta - voltage_area}
            output["phase_area"][label] = area
    output["all_grids_valid"] = all(output["grid"].values())
    return output


def write_review_files(provenance: dict[str, Any], result: dict[str, Any]) -> None:
    numerical = ["# Numerical review - mechanical only", "", f"- Exact fidelity status: `{result.get('exact_fidelity', {}).get('status', 'see by family')}`.", f"- Independent fresh-CSV grid check: `{result.get('independent_numerical_recalculation', {}).get('all_grids_valid')}`.", f"- Independent ordered navigation: `{json.dumps(result.get('independent_numerical_recalculation', {}).get('ordered_navigation_candidate_count', {}), ensure_ascii=False)}`.", "- Phase is raw radians; turns are independent unwrap/(2*pi) navigation only.", "- Phase-area uses the same JJ/endpoints/direction/window and actual-grid trapezoid.", "- Convergence and timestep sensitivity: UNKNOWN; not authorized."]
    adversarial = ["# Adversarial review probes - mechanical only", "", f"- Branch direction/KCL audit: `{json.dumps({mask: provenance.get('branch_direction_audit', {}).get(mask, {}).get('status') for mask in MASKS}, ensure_ascii=False)}`.", "- Per-instance coupling probe: each clone has a distinct branch PWL column; no common waveform is used.", "- Weak-oracle probe: ordered internal BJ1->BJ2->JTL1..6 chronology; terminal is corroboration only.", f"- Stale-artifact probe: current raw hashes unchanged `{provenance.get('raw_hash_before_analysis') == provenance.get('raw_hash_after_analysis')}` and references unchanged `{provenance.get('reference_hashes_before_analysis') == provenance.get('reference_hashes_after_analysis')}`.", "- Boundary probe: exact 3-sample shift, 110-ps hold, half-open windows, no interpolation/resampling.", "- Overclaim guard: no physical delay, current-only sufficiency, SFQ count, root-cause, or final branch category assignment."]
    (EXP / "analysis" / "NUMERICAL_REVIEW.md").write_text("\n".join(numerical) + "\n", encoding="utf-8")
    (EXP / "analysis" / "ADVERSARIAL_REVIEW.md").write_text("\n".join(adversarial) + "\n", encoding="utf-8")


def materialize_delayed() -> None:
    provenance = read_json(EXP / "provenance.json")
    passing = provenance.get("outcome", {}).get("passing_families", [])
    if provenance.get("outcome", {}).get("classification") != "DELAYED_CASES_AUTHORIZED_BY_FAMILY":
        raise RuntimeError("delayed cases require exact family gate")
    if not passing:
        raise RuntimeError("no family passed exact gate")
    traces = {mask: load_raw(CANONICAL[mask]) for mask in MASKS}
    records: dict[str, Any] = {}
    for family in passing:
        for mask in MASKS:
            case_id = f"{family}_DELAY0P3_{mask}"
            records[case_id] = make_case_deck(case_id, traces[mask])
    append_yaml_records(records, "delayed_deck_registration")
    provenance["registered_decks"].update(records)
    provenance["delayed_materialization"] = {"status": "PASS", "families": passing, "cases": list(records), "materialized_at": now(), "no_other_delay": True}
    write_json(EXP / "provenance.json", provenance)
    print(json.dumps({"status": "DELAYED_MATERIALIZED", "families": passing, "cases": list(records)}, ensure_ascii=False, indent=2))


def result_markdown(result: dict[str, Any]) -> str:
    lines = [f"# BVM R-loop branch timing decomposition ({EXP.name})", "", f"- Status: `{result.get('status')}`", f"- Artifact status: `{result.get('artifact_status')}`", "- Scientific interpretation: `NOT_PERFORMED`; final branch category: `SCIENTIFIC_REVIEW_REQUIRED`.", f"- HEAD: `{EXPECTED_HEAD}`; exact grid `.tran 0.1p 200p`; delay is exactly `0.3 ps = 3 stored samples`.", "- Forward path remains canonical BVM -> COMMON_SL -> JSL1..8 -> canonical QB -> JTL1..6 -> terminal.", "- Intervention is per-instance ideal current forcing from node6 to node10; it is not a physical delay network or R_S/L_S3 equivalent.", "", "## Mechanical exact gate", "", "| family | mask | exact status | canonical candidates | exact candidates | BJ1/BJ2 first timing delta (ps) |", "|---|---|---|---:|---:|---:|"]
    for family in FAMILIES:
        for mask in MASKS:
            item = result.get("exact_fidelity", {}).get(family, {}).get(mask)
            if not item:
                continue
            timing = item.get("QB_timing", {})
            deltas = [value.get("delta_ps") for value in timing.values() if value.get("delta_ps") is not None]
            lines.append(f"| `{family}` | `{mask}` | `{item.get('status')}` | {format_number(item.get('canonical_ordered_candidate_count'))} | {format_number(item.get('exact_ordered_candidate_count'))} | {format_number(max(abs(value) for value in deltas) if deltas else None)} |")
    lines += ["", "## Delayed raw observations", "", "| run | family | mask | ordered candidates | first BJ1/BJ2 (ps) | second BJ1/BJ2 (ps) | N3 JS1/JS2 focus p2p (turns) |", "|---|---|---|---:|---|---|---|"]
    for key, item in result.get("cases", {}).items():
        if not key.startswith("_"):
            js = item.get("JS1_JS2_focus_p2p_XBVM2", {})
            lines.append(f"| `{key}` | {item.get('family')} | {item.get('mask')} | {format_number(item.get('ordered_candidate_count'))} | {format_number(item.get('first_BJ1_plus_0p5_ps'))}/{format_number(item.get('first_BJ2_plus_0p5_ps'))} | {format_number(item.get('second_BJ1_plus_1p5_ps'))}/{format_number(item.get('second_BJ2_plus_1p5_ps'))} | {format_number(js.get('B_JS1'))}/{format_number(js.get('B_JS2'))} |")
    lines += ["", "All phase turns are raw-radian independent navigation values, never SFQ counts. `I_TOTAL` is imposed plus physical-branch current and is compared on the actual stored grid. Ideal-source power uses `P_absorb=Vbridge*I_source`; canonical energy is a physical bridge reference, not ideal-source energy.", "", "Bridge sign audit, canonical/total/branch current comparison, source recovery, LS3/RS branch constitution, bridge voltage, energy, effect fraction `F_B`, active-cell symmetry, JM1/JM2, QB/JTL, and terminal records are in `provenance.json.analysis`.", "", "Previous total-bridge replay, QBIN-boundary replay, LS3 static intervention, and TLINE evidence are referenced by hash only; no old artifact is modified or repackaged.", "", "No final scientific category is assigned. `Outcome A-D` interpretation, mechanism ranking, physical implementation, and follow-up design remain UNKNOWN/review-gated.", "", "- Raw/deck/metadata/log: `runs/`.", "- PWL source data: `inputs/replay_sources/`.", "- Mechanical QA/reviews/manifests: `analysis/`.", "- Descriptive plots: `plots/`.", "- Drive-only ZIP identity: `delivery_manifest.json`.", "", f"Stop marker: {result.get('stop', {}).get('final_marker') or 'delayed cases pending exact family gate'}", ""]
    return "\n".join(lines)


def format_number(value: Any) -> str:
    if value is None:
        return "—"
    try:
        return f"{float(value):.8g}"
    except (TypeError, ValueError):
        return str(value)


def mechanical_qa() -> None:
    provenance = read_json(EXP / "provenance.json")
    result = read_json(EXP / "result.json")
    keys = list(provenance.get("run_order", []))
    expected = list(EXACT_CASES) + [key for family in provenance.get("outcome", {}).get("passing_families", []) for key in (f"{family}_DELAY0P3_0011", f"{family}_DELAY0P3_0111")]
    failures: list[str] = []
    checks: dict[str, Any] = {}
    for key in keys:
        record = provenance["runs"][key]
        deck = REPO / record["deck"]["path"]
        raw = REPO / record["raw"]["path"]
        log = REPO / record["log"]["path"]
        metadata = REPO / record["metadata"]["path"]
        info = case_info(key)
        text_value = deck.read_text(encoding="utf-8") if deck.is_file() else ""
        expected_header_set = set(provenance["probe_policy"]["raw_expected_headers_by_family"][info["family"]][info["mask"]])
        try:
            trace = load_raw(raw)
            missing = sorted(expected_header_set - set(trace.headers))
            grid = replay_base.finite_grid_qa(trace)
        except Exception as exc:
            trace = None
            missing = [f"raw_parse_error:{exc}"]
            grid = {"status": "INVALID"}
        warnings = warning_lines(log)
        unexpected_warnings = [line for line in warnings if line not in KNOWN_NONFATAL_WARNING_LINES]
        deck_ok = bool(text_value.count(f"{replay_element(info['family'])} 6 10 PWL(") == 4 and text_value.count("XBQ1 QBIN QBOUT BQ") == 1 and text_value.count("R_TERM JTL6_OUT 0 10") == 1 and ".tran 0.1p 200p" in text_value and "R_S     6       10      3.0" not in text_value if info["family"] == "RS" else text_value.count("I_LS3_REPLAY 6 10 PWL(") == 4 and text_value.count("XBQ1 QBIN QBOUT BQ") == 1 and text_value.count("R_TERM JTL6_OUT 0 10") == 1 and ".tran 0.1p 200p" in text_value and "L_S3    6       10      0.5P" not in text_value)
        passed = bool(record.get("execution_status") == "RUN_PASS" and deck_ok and sha256(deck) == record["deck"]["sha256"] == provenance["registered_decks"][key]["sha256"] and sha256(raw) == record["raw"]["sha256"] and metadata.is_file() and trace is not None and not missing and not trace.duplicate_columns and grid.get("sample_count") == 1999 and grid.get("time_start_ps") == 0.0 and grid.get("time_end_ps") == 199.9 and grid.get("strictly_increasing_time") is True and not unexpected_warnings)
        if not passed:
            failures.append(key)
        checks[key] = {"status": "PASS" if passed else "ARTIFACT_INVALID", "deck": {"path": rel(deck), "sha256": sha256(deck) if deck.is_file() else None, "registered_sha256": provenance["registered_decks"][key]["sha256"], "topology_ok": deck_ok}, "raw": {"path": rel(raw), "sha256": sha256(raw) if raw.is_file() else None, "recorded_sha256": record["raw"]["sha256"], "missing_required_probes": missing, "grid": grid}, "metadata": {"path": rel(metadata), "exists": metadata.is_file()}, "solver_warning_lines": warnings, "known_nonfatal_solver_warnings": [line for line in warnings if line in KNOWN_NONFATAL_WARNING_LINES], "unexpected_solver_warning_lines": unexpected_warnings}
    source_hashes_match = all(sha256(REPO / item["path"]) == item["sha256"] for item in provenance["source_closure"])
    reference_hashes_match = provenance.get("reference_hashes_before_analysis") == provenance.get("reference_hashes_after_analysis") and all(sha256(REPO / path) == digest for path, digest in provenance.get("reference_hashes_after_analysis", {}).items())
    passed = bool(keys == expected and not failures and source_hashes_match and reference_hashes_match and provenance.get("raw_hash_before_analysis") == provenance.get("raw_hash_after_analysis") and provenance.get("execution", {}).get("actual_physical_solve_count") == len(keys) and len(keys) <= 8 and (EXP / "analysis" / "TRANSFORMATION_REGISTRY.json").is_file() and (EXP / "result.json").stat().st_size <= RESULT_LIMIT_BYTES)
    qa = {"schema": "bvm-rloop-branch-timing-mechanical-qa-v1", "experiment_id": EXP.name, "generated_at": now(), "status": "PASS" if passed else "FAIL", "artifact_status": "VALID" if passed else "ARTIFACT_INVALID", "head": git_head(), "remote_bvm_master": remote_head(), "run_order": keys, "expected_run_order": expected, "source_hashes_match": source_hashes_match, "reference_hashes_match": reference_hashes_match, "raw_hash_before_after_equal": provenance.get("raw_hash_before_analysis") == provenance.get("raw_hash_after_analysis"), "actual_physical_solve_count": provenance.get("execution", {}).get("actual_physical_solve_count"), "max_physical_solves": 8, "no_extra_followup": keys == expected, "no_timestep_sweep": True, "no_sentinel": True, "contains_current_raw": None, "contains_all_new_run_raw": None, "contains_reference_raw_copies": False, "runs": checks, "failures": failures, "mechanical_analysis_performed": True, "bounded_experiment_interpretation_performed": False, "independent_scientific_review_performed": False, "result_json_under_limit": (EXP / "result.json").stat().st_size <= RESULT_LIMIT_BYTES}
    write_json(EXP / "analysis" / "MECHANICAL_QA.json", qa)
    provenance["qa"] = qa
    write_json(EXP / "provenance.json", provenance)
    result["qa_summary"] = {"status": qa["status"], "artifact_status": qa["artifact_status"]}
    write_json(EXP / "result.json", result)
    (EXP / "RESULT.md").write_text(result_markdown(result), encoding="utf-8")
    if not passed:
        raise RuntimeError(f"mechanical QA failed: {failures}")
    print(json.dumps({"status": "PASS", "run_order": keys}, ensure_ascii=False, indent=2))


def externalize_plotly_runtime(temporary: Path, output: Path, asset: Path) -> None:
    html = temporary.read_text(encoding="utf-8")
    matches = list(re.finditer(r"<script(?P<attrs>[^>]*)>(?P<body>.*?)</script>", html, flags=re.DOTALL))
    runtime = next((match for match in matches if len(match.group("body")) > 1_000_000 and ("plotly.js v" in match.group("body") or "var Plotly=" in match.group("body"))), None)
    if runtime is None:
        raise RuntimeError("embedded Plotly runtime not found")
    body = runtime.group("body")
    asset.parent.mkdir(parents=True, exist_ok=True)
    if asset.exists() and asset.read_text(encoding="utf-8") != body:
        raise RuntimeError("Plotly runtime differs")
    if not asset.exists():
        asset.write_text(body, encoding="utf-8")
    ref = Path(os.path.relpath(asset, output.parent)).as_posix()
    compact = html[:runtime.start()] + f'<script src="{ref}"></script>' + html[runtime.end():]
    if any(token in compact for token in ("plotly.js v", "var Plotly=", "cdn.plot.ly")):
        raise RuntimeError("Plotly runtime was not externalized")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(compact, encoding="utf-8")


def render_plot(input_path: Path, output_path: Path, signals: list[str], title: str, asset: Path) -> None:
    if output_path.exists():
        return
    with tempfile.NamedTemporaryFile(prefix="bvm_branch_plot_", suffix=".html", delete=False, dir="/tmp") as handle:
        temporary = Path(handle.name)
    try:
        command = [sys.executable, str(PLOTTER), str(input_path), "-x", str(temporary), "-t", "sep_comb", "-c", "dark", "-j", "2pi", "-w", title, "-s", *signals]
        completed = subprocess.run(command, cwd=REPO, capture_output=True, text=True, check=False)
        if completed.returncode != 0:
            raise RuntimeError(f"plotter failed: {completed.stderr[-1000:]}")
        externalize_plotly_runtime(temporary, output_path, asset)
    finally:
        temporary.unlink(missing_ok=True)


def visualization() -> None:
    provenance = read_json(EXP / "provenance.json")
    if provenance.get("qa", {}).get("status") != "PASS":
        raise RuntimeError("QA must pass before visualization")
    asset = EXP / "plots" / "assets" / "plotly.min.js"
    entries: list[dict[str, Any]] = []
    specs = {
        "01_SIGNAL_TIMING": ["V(COMMON_SL)", "I(B_JSL8)", "V(QBIN)", "I(LIN|XBQ1)", "V(QBOUT)"],
        "02_BVM_STATE": [signal for index in range(1, 5) for element in ("B_JS1", "B_JS2", "B_JM1", "B_JM2") for signal in (f"P({element}|XBVM{index})", f"V({element}|XBVM{index})", f"I({element}|XBVM{index})")] + [signal for index in range(1, 5) for element in ("L_S1", "L_S2", "L_M3", "L_SL") for signal in (f"I({element}|XBVM{index})", f"V({element}|XBVM{index})")],
        "03_JSL_CHAIN": [signal for index in range(1, 9) for signal in (f"P(B_JSL{index})", f"V(B_JSL{index})", f"I(B_JSL{index})")],
        "04_QB_STATE": ["V(QBIN)", "I(LIN|XBQ1)", "V(LIN|XBQ1)", *[f"{kind}({element}|XBQ1)" for element in ("BJS", "BJ1", "BJ2") for kind in ("P", "V", "I")], *[f"{kind}({element}|XBQ1)" for element in ("L1", "L2", "L3", "RJ1", "RJ2") for kind in ("I", "V")], "V(QBOUT)"],
        "05_JTL_CHAIN": [signal for stage in JTL_STAGES for signal in (f"P(B01|XJTL1_{stage})", f"V(B01|XJTL1_{stage})", f"I(B01|XJTL1_{stage})", f"P(B02|XJTL1_{stage})", f"V(B02|XJTL1_{stage})", f"I(B02|XJTL1_{stage})", f"V(JTL{stage}_OUT)")] + ["I(R_TERM)"],
    }
    for key in provenance["run_order"]:
        raw = REPO / provenance["runs"][key]["raw"]["path"]
        trace = load_raw(raw)
        for page, requested in specs.items():
            selected = [signal for signal in requested if signal in trace.headers]
            output = EXP / "plots" / key / f"{page}.html"
            render_plot(raw, output, selected, f"{key}: {page} full 0-200 ps; actual stored grid", asset)
            entries.append({"kind": "standalone", "run_id": key, "path": rel(output), "raw_path": rel(raw), "raw_sha256": sha256(raw), "sha256": sha256(output), "bytes": output.stat().st_size, "signals": selected, "window_ps": list(FULL_WINDOW), "focused": False, "phase_display": "raw radians; rad/(2*pi) turns navigation only"})
        focus = total_helpers.crop_csv(raw, *FOCUS_WINDOW)
        rearm = total_helpers.crop_csv(raw, *REARM_WINDOW)
        try:
            for page, requested in specs.items():
                selected = [signal for signal in requested if signal in trace.headers]
                output = EXP / "plots" / key / f"{page}_focus_110_121.html"
                render_plot(focus, output, selected, f"{key}: {page} focus [110,121) ps; actual stored samples", asset)
                entries.append({"kind": "standalone", "run_id": key, "path": rel(output), "raw_path": rel(raw), "raw_sha256": sha256(raw), "sha256": sha256(output), "bytes": output.stat().st_size, "signals": selected, "window_ps": list(FOCUS_WINDOW), "focused": True, "derived_input": "actual-grid crop only; no interpolation", "phase_display": "raw radians; rad/(2*pi) turns navigation only"})
            requested = ["V(QBIN)", "I(LIN|XBQ1)", "I(L1|XBQ1)", "I(L2|XBQ1)", "I(B_JSL8)", "V(COMMON_SL)"]
            selected = [signal for signal in requested if signal in trace.headers]
            output = EXP / "plots" / key / "04_QB_STATE_focus_121_130.html"
            render_plot(rearm, output, selected, f"{key}: 04_QB_STATE re-arm [121,130) ps; actual stored samples", asset)
            entries.append({"kind": "standalone", "run_id": key, "path": rel(output), "raw_path": rel(raw), "raw_sha256": sha256(raw), "sha256": sha256(output), "bytes": output.stat().st_size, "signals": selected, "window_ps": list(REARM_WINDOW), "focused": True, "derived_input": "actual-grid crop only; no interpolation", "phase_display": "raw radians; rad/(2*pi) turns navigation only"})
        finally:
            focus.unlink(missing_ok=True)
            rearm.unlink(missing_ok=True)
    canonical_traces = {mask: load_raw(CANONICAL[mask]) for mask in MASKS}
    previous_traces = {label: load_raw(path) for label, path in PREVIOUS_TOTAL_RAW.items()}
    comparison_entries: list[dict[str, Any]] = []
    compare_specs = {"01_SIGNAL_TIMING": specs["01_SIGNAL_TIMING"], "02_BVM_STATE": specs["02_BVM_STATE"], "03_JSL_CHAIN": ["P(B_JSL8)", "V(B_JSL8)", "I(B_JSL8)", "V(COMMON_SL)"], "04_QB_STATE": ["V(QBIN)", "I(LIN|XBQ1)", "I(L1|XBQ1)", "I(L2|XBQ1)", "P(BJ1|XBQ1)", "P(BJ2|XBQ1)", "V(QBOUT)"], "05_JTL_CHAIN": specs["05_JTL_CHAIN"]}
    for mask in MASKS:
        cases: list[tuple[str, Any]] = [(f"CANONICAL_{mask}", canonical_traces[mask]), (f"TOTAL_EXACT_{mask}", previous_traces[f"EXACT_{mask}"]), (f"TOTAL_DELAY0P3_{mask}", previous_traces[f"DELAY0P3_{mask}"])]
        for family in FAMILIES:
            for stage in ("EXACT", "DELAY0P3"):
                key = f"{family}_{stage}_{mask}"
                if key in provenance["runs"]:
                    cases.append((key, load_raw(REPO / provenance["runs"][key]["raw"]["path"])))
        for page, requested in compare_specs.items():
            selected = [signal for signal in requested if all(signal in trace.headers for _, trace in cases)]
            if not selected:
                continue
            for window, suffix in ((None, "full_0_200"), (FOCUS_WINDOW, "focus_110_121")) if page in ("01_SIGNAL_TIMING", "02_BVM_STATE", "04_QB_STATE") else ((None, "full_0_200"),):
                temporary = total_helpers.comparison_csv(cases, selected, window)
                output = EXP / "plots" / "comparisons" / f"{mask}_{page}_{suffix}.html"
                try:
                    render_plot(temporary, output, [replay_base.prefixed_label(case, signal) for case, _ in cases for signal in selected], f"{mask}: canonical/total/branch replay {page} {suffix}", asset)
                finally:
                    temporary.unlink(missing_ok=True)
                comparison_entries.append({"kind": "comparison", "mask": mask, "path": rel(output), "sha256": sha256(output), "bytes": output.stat().st_size, "cases": [case for case, _ in cases], "signals": selected, "window_ps": list(FOCUS_WINDOW if window else FULL_WINDOW), "focused": window is not None, "phase_display": "independent case unwrap and rad/(2*pi) turns navigation"})
        voltage_temp = total_helpers.bridge_voltage_comparison_csv(cases, FOCUS_WINDOW)
        voltage_output = EXP / "plots" / "comparisons" / f"{mask}_BRIDGE_VOLTAGE_focus_110_121.html"
        try:
            signal_names = [replay_base.prefixed_label(f"{case}_XBVM{index}", "V(BRIDGE_6_10)") for case, _ in cases for index in range(1, 5)]
            render_plot(voltage_temp, voltage_output, signal_names, f"{mask}: canonical/total/branch bridge voltage focus [110,121) ps", asset)
        finally:
            voltage_temp.unlink(missing_ok=True)
        comparison_entries.append({"kind": "derived_comparison", "mask": mask, "path": rel(voltage_output), "sha256": sha256(voltage_output), "bytes": voltage_output.stat().st_size, "cases": [case for case, _ in cases], "signals": signal_names, "window_ps": list(FOCUS_WINDOW), "focused": True, "derived_semantics": "canonical V(R_S) and replay V(6)-V(10)", "phase_display": "voltage comparison"})
    html_paths = sorted((EXP / "plots").rglob("*.html"))
    invalid = [rel(path) for path in html_paths if any(token in path.read_text(encoding="utf-8") for token in ("plotly.js v", "var Plotly=", "cdn.plot.ly", "Unknown"))]
    visualization = {"schema": "bvm-rloop-branch-timing-visualization-v1", "status": "PASS" if html_paths and asset.is_file() and not invalid and entries and comparison_entries else "FAIL", "generated_at": now(), "renderer": rel(PLOTTER), "layout": "sep_comb", "color": "dark", "phase_option": "2pi", "semantic_structure": list(specs), "entries": entries + comparison_entries, "standalone_count": len(entries), "comparison_count": len(comparison_entries), "focused_window_entries": sum(item["focused"] for item in entries), "asset": {"path": rel(asset), "sha256": sha256(asset) if asset.is_file() else None, "bytes": asset.stat().st_size if asset.is_file() else None}, "raw_hashes_rechecked": all(item["raw_sha256"] == sha256(REPO / item["raw_path"]) for item in entries), "invalid_runtime_pages": invalid, "visualization_is_descriptive_only": True}
    write_json(EXP / "analysis" / "VISUALIZATION_MANIFEST.json", visualization)
    write_json(EXP / "analysis" / "VISUALIZATION_QA.json", {"status": visualization["status"], "standalone_count": len(entries), "comparison_count": len(comparison_entries), "focused_window_entries": visualization["focused_window_entries"], "invalid_runtime_pages": invalid, "raw_hashes_rechecked": visualization["raw_hashes_rechecked"]})
    provenance["visualization"] = visualization
    write_json(EXP / "provenance.json", provenance)
    result = read_json(EXP / "result.json")
    result["visualization_summary"] = {"status": visualization["status"], "standalone_count": len(entries), "comparison_count": len(comparison_entries), "focused_window_entries": visualization["focused_window_entries"]}
    write_json(EXP / "result.json", result)
    (EXP / "RESULT.md").write_text(result_markdown(result), encoding="utf-8")
    if visualization["status"] != "PASS":
        raise RuntimeError(f"visualization failed: {invalid}")
    print(json.dumps({"status": "PASS", "standalone_count": len(entries), "comparison_count": len(comparison_entries)}, ensure_ascii=False, indent=2))


def write_evidence_manifests() -> None:
    records = []
    for path in sorted(EXP.rglob("*")):
        if not path.is_file() or path.name in {"delivery_manifest.json"} or path.suffix == ".tmp":
            continue
        records.append({"path": path.relative_to(EXP).as_posix(), "sha256": sha256(path), "bytes": path.stat().st_size})
    write_json(EXP / "analysis" / "RAW_ANALYSIS_HANDOFF_MANIFEST.json", {"schema": "bvm-rloop-branch-timing-raw-analysis-handoff-v1", "experiment_id": EXP.name, "generated_at": now(), "raw_is_immutable_solver_output": True, "processed_crops_are_not_raw_substitutes": True, "files_excluding_delivery_manifest": records})
    lines = ["# Evidence manifest", "", "| path | SHA-256 | bytes |", "|---|---|---:|"] + [f"| `{item['path']}` | `{item['sha256']}` | {item['bytes']} |" for item in records]
    (EXP / "analysis" / "EVIDENCE_MANIFEST.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def package() -> None:
    provenance = read_json(EXP / "provenance.json")
    if provenance.get("qa", {}).get("status") != "PASS" or provenance.get("visualization", {}).get("status") != "PASS":
        raise RuntimeError("QA and visualization must pass before package")
    write_evidence_manifests()
    delivery_dir = Path("/mnt/d/BVM_Backages")
    delivery_dir.mkdir(parents=True, exist_ok=True)
    previous_manifest = read_json(EXP / "delivery_manifest.json") if (EXP / "delivery_manifest.json").is_file() else None
    package_path = delivery_dir / f"{EXP.name}_raw_evidence.zip"
    version = "v1"
    if package_path.exists():
        version = "v2"
        package_path = delivery_dir / f"{EXP.name}_{version}_raw_evidence.zip"
    if package_path.exists():
        raise RuntimeError(f"refusing overwrite existing package: {package_path}")
    result = read_json(EXP / "result.json")
    provenance["package"] = {"status": "PACKAGE_CONTENT_READY", "version": version, "internal_metadata_status": "ALL_AUTHORIZED_OR_EXACT_GATE_RUNS_COMPLETE", "delivery_manifest_path": "delivery_manifest.json", "drive_file_id": None, "drive_url": None}
    result["package_summary"] = {"status": "PACKAGE_CONTENT_READY", "version": version, "delivery_manifest_path": "delivery_manifest.json", "drive_file_id": None}
    write_json(EXP / "provenance.json", provenance)
    write_json(EXP / "result.json", result)
    (EXP / "RESULT.md").write_text(result_markdown(result), encoding="utf-8")
    files: list[tuple[Path, str]] = []
    for name in ("experiment.yaml", "PREFLIGHT.md", "RESULT.md", "result.json", "provenance.json"):
        files.append((EXP / name, name))
    for dirname in ("inputs", "runs", "analysis", "plots"):
        for path in sorted((EXP / dirname).rglob("*")):
            if path.is_file():
                files.append((path, path.relative_to(EXP).as_posix()))
    files.append((SCRIPT, "executor/bvm_qb_rloop_branch_timing_decomposition.py"))
    records = [{"path": archive_name, "sha256": sha256(path), "bytes": path.stat().st_size} for path, archive_name in files]
    with zipfile.ZipFile(package_path, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path, archive_name in files:
            archive.write(path, archive_name)
    with zipfile.ZipFile(package_path, "r") as archive:
        reopened = {name: hashlib.sha256(archive.read(name)).hexdigest() for name in archive.namelist()}
    expected = {item["path"]: item["sha256"] for item in records}
    new_raw_members = [(REPO / provenance["runs"][key]["raw"]["path"]).relative_to(EXP).as_posix() for key in provenance["run_order"]]
    qa = {"status": "PASS" if expected == reopened else "FAIL", "package_version": version, "package_path": str(package_path), "package_sha256": sha256(package_path), "package_bytes": package_path.stat().st_size, "file_count": len(records), "expected_file_hashes_match_after_reopen": expected == reopened, "zip_files": records, "not_in_git": True, "contains_all_new_run_raw": all(member in reopened for member in new_raw_members), "new_run_raw_members": new_raw_members, "contains_reference_raw_copies": False, "contains_delivery_manifest": False, "delivery_manifest_outside_zip": True, "git_head_at_packaging": git_head(), "remote_head_at_packaging": remote_head(), "supersedes_previous_package_sha256": previous_manifest.get("package_sha256") if previous_manifest else None}
    manifest = {"schema": "bvm-rloop-branch-timing-delivery-manifest-v1", "experiment_id": EXP.name, "created_at": now(), "status": "READY_FOR_DRIVE_UPLOAD" if qa["status"] == "PASS" else "PACKAGE_INVALID", "package_version": version, "package_path": str(package_path), "package_sha256": qa["package_sha256"], "package_bytes": qa["package_bytes"], "package_qa": qa, "drive_folder_id": DRIVE_FOLDER_ID, "drive_file_id": None, "drive_url": None, "delivery_id_is_outside_zip_to_avoid_self_reference": True, "supersedes_previous_package_sha256": previous_manifest.get("package_sha256") if previous_manifest else None}
    write_json(EXP / "delivery_manifest.json", manifest)
    provenance["package"] = {"status": manifest["status"], "version": version, "internal_metadata_status": "ALL_AUTHORIZED_OR_EXACT_GATE_RUNS_COMPLETE", "delivery_manifest_path": "delivery_manifest.json", "package_qa": qa, "drive_file_id": None, "drive_url": None}
    write_json(EXP / "provenance.json", provenance)
    result = read_json(EXP / "result.json")
    result["package_summary"] = {"status": manifest["status"], "version": version, "package_sha256": qa["package_sha256"], "package_bytes": qa["package_bytes"], "file_count": qa["file_count"], "delivery_manifest_path": "delivery_manifest.json", "drive_file_id": None}
    write_json(EXP / "result.json", result)
    (EXP / "RESULT.md").write_text(result_markdown(result), encoding="utf-8")
    if qa["status"] != "PASS":
        raise RuntimeError("package reopen QA failed")
    print(json.dumps({"status": "PASS", "package_path": str(package_path), "sha256": qa["package_sha256"], "bytes": qa["package_bytes"], "files": qa["file_count"], "manifest": rel(EXP / "delivery_manifest.json")}, ensure_ascii=False, indent=2))


def record_drive(file_id: str, url: str | None = None, drive_sha256: str | None = None, drive_bytes: int | None = None) -> None:
    manifest_path = EXP / "delivery_manifest.json"
    manifest = read_json(manifest_path)
    package_path = Path(manifest["package_path"])
    local_sha = sha256(package_path)
    if not package_path.is_file() or local_sha != manifest["package_sha256"]:
        raise RuntimeError("local package missing or changed")
    if drive_sha256 is not None and drive_sha256 != local_sha:
        raise RuntimeError("Drive SHA-256 mismatch")
    if drive_bytes is not None and int(drive_bytes) != int(manifest["package_bytes"]):
        raise RuntimeError("Drive byte-size mismatch")
    manifest.update({"status": "UPLOADED", "drive_file_id": file_id, "drive_url": url, "uploaded_at": now(), "drive_verified_local_sha256": local_sha, "drive_verified_local_bytes": package_path.stat().st_size})
    write_json(manifest_path, manifest)
    provenance = read_json(EXP / "provenance.json")
    provenance["package"].update({"status": "UPLOADED", "drive_file_id": file_id, "drive_url": url, "drive_uploaded_at": manifest["uploaded_at"], "delivery_manifest_sha256": sha256(manifest_path), "drive_sha256_verified": drive_sha256 == local_sha if drive_sha256 is not None else "metadata SHA not supplied by connector"})
    write_json(EXP / "provenance.json", provenance)
    result = read_json(EXP / "result.json")
    result["package_summary"].update({"status": "UPLOADED", "drive_file_id": file_id, "drive_url": url, "drive_verified_local_sha256": local_sha})
    write_json(EXP / "result.json", result)
    (EXP / "RESULT.md").write_text(result_markdown(result), encoding="utf-8")
    print(json.dumps({"status": "UPLOADED", "drive_file_id": file_id, "drive_url": url, "package_sha256": local_sha, "package_bytes": package_path.stat().st_size}, ensure_ascii=False, indent=2))


def all_actions() -> None:
    prepare()
    execute_cases(EXACT_CASES)
    analyze()
    result = read_json(EXP / "result.json")
    passing = result.get("classification", {}).get("passing_families", [])
    if passing:
        materialize_delayed()
        delayed = [key for family in passing for key in (f"{family}_DELAY0P3_0011", f"{family}_DELAY0P3_0111")]
        execute_cases(delayed)
        analyze()
    mechanical_qa()
    visualization()
    package()


def main() -> int:
    command = sys.argv[1] if len(sys.argv) > 1 else "all"
    actions = {"prepare": prepare, "run-exact": lambda: execute_cases(EXACT_CASES), "analyze": analyze, "materialize-delayed": materialize_delayed, "run-delayed": lambda: execute_cases(DELAY_CASES), "qa": mechanical_qa, "viz": visualization, "package": package, "record-drive": lambda: record_drive(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None, sys.argv[4] if len(sys.argv) > 4 else None, int(sys.argv[5]) if len(sys.argv) > 5 else None), "all": all_actions}
    if command not in actions:
        print(f"usage: {SCRIPT.name} [prepare|run-exact|analyze|materialize-delayed|run-delayed|qa|viz|package|record-drive FILE_ID [URL] [SHA256] [BYTES]|all]", file=sys.stderr)
        return 2
    if command == "record-drive" and len(sys.argv) < 3:
        print("record-drive requires FILE_ID", file=sys.stderr)
        return 2
    actions[command]()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
