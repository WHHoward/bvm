#!/usr/bin/env python3
"""BVM R-loop bridge-current timing replay experiment.

This is an ideal current-forcing counterfactual.  It clones the canonical BVM
body once per array instance, removes that clone's R_S and L_S3 elements, and
inserts an instance-specific PWL current source from local node 6 to node 10.
The canonical QB/JTL/terminal forward path remains loaded and unchanged.

The runner executes the exact two-case gate first.  The four delayed cases are
materialized and solved only if the registered mechanical fidelity screen
passes.  Scientific interpretation is deliberately kept separate from
mechanical raw arithmetic and remains review-gated unless the caller supplies
SCIENTIFIC_REVIEW_AUTHORIZED.
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
import bvm_qb_tline_feedback_dephasing as tline_helpers  # noqa: E402
import bvm_qb_tline_z0_rescue_gate as z0_helpers  # noqa: E402

replay_base = tline_helpers.replay_base

EXP = REPO / "test" / "exploration" / "bvm-rloop-bridge-timing-replay-v1-20260916"
REFERENCE_ROOT = REPO / "test" / "exploration" / "bvm-qb-threshold-ordering-boundary-search-v1-20260911" / "references" / "canonical_baseline"
SOURCE_INPUTS = REPO / "test" / "exploration" / "bvm-qb-threshold-ordering-boundary-search-v1-20260911" / "inputs"
SOLVER = REPO / "build" / "josim-cli"
PLOTTER = REPO / "scripts" / "josim-plot2.py"
CANONICAL = {mask: REFERENCE_ROOT / mask / "raw.csv" for mask in ("0011", "0111")}
CANONICAL_DECKS = {mask: REFERENCE_ROOT / mask / "deck.cir" for mask in ("0011", "0111")}

CONTEXT_EXPERIMENTS = {
    "boundary_timing_result": REPO / "test" / "exploration" / "bvm-qb-boundary-timing-replay-v1-20260916" / "result.json",
    "boundary_timing_provenance": REPO / "test" / "exploration" / "bvm-qb-boundary-timing-replay-v1-20260916" / "provenance.json",
    "ls3_result": REPO / "test" / "exploration" / "bvm-qb-rloop-ls3-causality-v1-20260916" / "result.json",
    "ls3_provenance": REPO / "test" / "exploration" / "bvm-qb-rloop-ls3-causality-v1-20260916" / "provenance.json",
    "tline_z0_result": REPO / "test" / "exploration" / "bvm-qb-tline-z0-rescue-gate-v1-20260916" / "result.json",
    "tline_z0_provenance": REPO / "test" / "exploration" / "bvm-qb-tline-z0-rescue-gate-v1-20260916" / "provenance.json",
}

EXPECTED_HEAD = "3523c8c6edfaeb2b880302cf2281857134501774"
PHI0 = 2.067833848e-15
TAU = 2.0 * math.pi
TD0 = 0.0
DELAYS_PS = (0.3, 0.6)
DELAY_SHIFTS = {0.3: 3, 0.6: 6}
T0_PS = 110.0
FOCUS_WINDOW = (110.0, 121.0)
REARM_WINDOW = (121.0, 130.0)
CONTROL_WINDOW = (70.0, 110.0)
FULL_WINDOW = (0.0, 200.0)
WINDOWS_PS = (FULL_WINDOW, CONTROL_WINDOW, FOCUS_WINDOW, REARM_WINDOW, (121.0, 200.0))
MASKS = ("0011", "0111")
EXACT_CASES = ("EXACT_0011", "EXACT_0111")
DELAY_CASES = ("DELAY0P3_0011", "DELAY0P3_0111", "DELAY0P6_0011", "DELAY0P6_0111")
ALL_CASES = EXACT_CASES + DELAY_CASES
FINAL_MARKER = "EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW"
CONTRACT_SENTENCE = "This experiment is governed by docs/EXPERIMENT_CONTRACT.md."
RESULT_LIMIT_BYTES = 500 * 1024
DRIVE_FOLDER_ID = "1--nlY7Nq5ArVPydJNrnQf-EGmwN-undh"
REARM_DWELL_SAMPLES = 3

# These are registered mechanical fidelity-screen tolerances, not physical
# acceptance tolerances and not a 1e-9 V requirement.  The raw errors are
# always retained in provenance even when a screen passes.
EXACT_TIMING_TOL_PS = 0.2
EXACT_PHASE_P2P_TOL_TURNS = 0.25
EXACT_NORMALIZED_WAVEFORM_RMS_TOL = 0.50

SOURCE_HASHES = {
    SOLVER: "48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2",
    REPO / "src" / "Output.cpp": None,
    REPO / "test" / "comp" / "tx.cir": "c0a5e75f3ccf04f9635187eea1672b3b377bde7c4e9589b5324b188fd53c7488",
    REPO / "circuits" / "qb" / "bq_parameterized_v1.cir": "f676ba1ecb9b2607631a5cfc2f99b7d67e09b9e821457015fba375b8a39f13b0",
    SOURCE_INPUTS / "jjmit.cir": "19862d1fd1f1f44dfa1523848d7d3b5e2594a6c5da8fdd80144b449e5312a336",
    SOURCE_INPUTS / "bvm_jm2_connected.cir": "0093a45cc3910448b484d8bd004c6df8c22358bacc8b3ed5e23912dcab805d54",
    SOURCE_INPUTS / "BQ_parameterized_bjs400_rj2.cir": "43468c49eb56090e586428a8ca26d17d8bbf107fbd9e535bbac7a72ed1200d42",
    SOURCE_INPUTS / "jtl2.cir": "ffd31f8eda2a86ca0133342be1ce678831b7237a53911eda046d2bff8454855a",
}
EXPECTED_CANONICAL_RAW_HASHES = {
    "0011": "3da7b754c990316ff8e5981692afa958d8056a61020a1912548bf6f2b7e0249c",
    "0111": "1ca15a938b23d4ed08eb964713f91476256c4caf0677d1bfd3dc43020271ec75",
}

JUNCTIONS = ("B_JM1", "B_JM2", "B_JS1", "B_JS2")
BVM_BRANCHES = ("L_M1", "L_M2", "L_M3", "L_PM", "L_S1", "L_S2", "L_S3", "R_S", "R_SE", "L_PSE", "L_PSL", "R_SL", "L_SL")
RLOOP_BRANCHES = ("L_S1", "L_S2", "L_M3", "L_SL")
JTL_STAGES = range(1, 7)
KNOWN_NONFATAL_WARNING_LINES = {
    "Unknown device/node IB|XBQ1",
    "Cannot store results for this device/node.",
}


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
    return tline_helpers.load_raw(path)


def time_indices(trace: Any, start_ps: float, end_ps: float) -> list[int]:
    return [index for index, value in enumerate(trace.time) if start_ps <= value * 1.0e12 < end_ps]


def actual_integral(times: Iterable[float], values: Iterable[float]) -> float:
    time_list = list(times)
    value_list = list(values)
    return sum(0.5 * (value_list[index] + value_list[index + 1]) * (time_list[index + 1] - time_list[index]) for index in range(len(value_list) - 1))


def unwrap(values: Iterable[float]) -> list[float]:
    return tline_helpers.unwrap(values)


def phase_navigation(trace: Any, signal: str) -> dict[str, Any]:
    return z0_helpers.phase_navigation(trace, signal)


def phase_area(trace: Any, phase_signal: str, voltage_signal: str) -> dict[str, Any]:
    return z0_helpers.phase_area_crosscheck(trace, phase_signal, voltage_signal)


def waveform_stats(trace: Any, signal: str, window: tuple[float, float]) -> dict[str, Any]:
    return z0_helpers.waveform_stats(trace, signal, window)


def compact_waveform(item: dict[str, Any]) -> dict[str, Any]:
    keys = ("signal", "unit", "minimum", "maximum", "p2p", "mean", "rms", "peak_abs", "peak_value", "time_of_peak_abs_ps", "signed_area", "absolute_area", "positive_area", "negative_area", "positive_sample_fraction", "negative_sample_fraction", "zero_crossing_count", "half_abs_peak_width")
    return {key: item.get(key) for key in keys}


def sign_metrics(trace: Any, signal: str, window: tuple[float, float]) -> dict[str, Any]:
    return z0_helpers.sign_metrics(trace, signal, window, REARM_DWELL_SAMPLES)


def voltage_integrals(trace: Any, signals: Iterable[str], window: tuple[float, float]) -> dict[str, Any]:
    return z0_helpers.voltage_integrals(trace, signals, window)


def vector_stats(trace: Any, signal: str, values: list[float], window: tuple[float, float]) -> dict[str, Any]:
    indices = time_indices(trace, *window)
    selected = [values[index] for index in indices]
    times = [trace.time[index] for index in indices]
    if len(selected) < 2:
        return {"status": "UNKNOWN", "signal": signal, "window_ps": list(window)}
    peak_position = max(range(len(selected)), key=lambda position: abs(selected[position]))
    return {
        "status": "DERIVED",
        "signal": signal,
        "window_ps": list(window),
        "sample_count": len(selected),
        "unit": "V",
        "minimum": min(selected),
        "maximum": max(selected),
        "p2p": max(selected) - min(selected),
        "mean": sum(selected) / len(selected),
        "rms": math.sqrt(sum(value * value for value in selected) / len(selected)),
        "peak_abs": abs(selected[peak_position]),
        "peak_value": selected[peak_position],
        "time_of_peak_abs_ps": times[peak_position] * 1.0e12,
        "signed_area": actual_integral(times, selected),
        "absolute_area": actual_integral(times, [abs(value) for value in selected]),
        "positive_area": actual_integral(times, [max(value, 0.0) for value in selected]),
        "negative_area": actual_integral(times, [min(value, 0.0) for value in selected]),
        "positive_sample_fraction": sum(value > 0.0 for value in selected) / len(selected),
        "negative_sample_fraction": sum(value < 0.0 for value in selected) / len(selected),
        "zero_crossing_count": tline_helpers.zero_crossing_count(selected),
        "actual_grid_trapezoid": True,
    }


def source_tokens(path: Path) -> tuple[list[str], dict[str, list[str]], dict[str, list[float]]]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.reader(stream)
        header = next(reader)
        if header.count("time") != 1:
            raise RuntimeError(f"time header is ambiguous: {path}")
        rows = [row for row in reader if row and any(cell.strip() for cell in row)]
    time_index = header.index("time")
    times = [row[time_index].strip() for row in rows]
    strings: dict[str, list[str]] = {name: [row[index].strip() for row in rows] for index, name in enumerate(header) if name != "time"}
    values: dict[str, list[float]] = {name: [float(token) for token in tokens] for name, tokens in strings.items()}
    return times, strings, values


def time_token_ps(token: str) -> str:
    time_ps = float(token) * 1.0e12
    return "0" if abs(time_ps) < 1.0e-30 else f"{time_ps:.17g}p"


def current_token(value: float) -> str:
    return f"{value:.17g}"


def make_bridge_values(values: dict[str, list[float]], times: list[str], delay_ps: float) -> dict[str, list[float]]:
    bridge = {f"XBVM{index}": [values[f"I(R_S|XBVM{index})"][row] + values[f"I(L_S3|XBVM{index})"][row] for row in range(len(times))] for index in range(1, 5)}
    if delay_ps == 0.0:
        return bridge
    shift = DELAY_SHIFTS[delay_ps]
    start = next(index for index, token in enumerate(times) if abs(float(token) * 1.0e12 - T0_PS) < 1.0e-9)
    delayed: dict[str, list[float]] = {}
    for instance, source in bridge.items():
        output: list[float] = []
        for index, token in enumerate(times):
            if index < start:
                output.append(source[index])
            elif index < start + shift:
                output.append(source[start])
            else:
                output.append(source[index - shift])
        delayed[instance] = output
    return delayed


def source_csv(path: Path, times: list[str], bridge: dict[str, list[float]], canonical_bridge: dict[str, list[float]], delay_ps: float) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["time_s", "time_ps", *[f"I_BRIDGE_{instance}_A" for instance in bridge]])
        for row, token in enumerate(times):
            writer.writerow([token, f"{float(token) * 1.0e12:.17g}", *[current_token(bridge[instance][row]) for instance in bridge]])
    start = next(index for index, token in enumerate(times) if abs(float(token) * 1.0e12 - T0_PS) < 1.0e-9)
    shift = DELAY_SHIFTS.get(delay_ps, 0)
    pre_equal = all(bridge[instance][index] == canonical_bridge[instance][index] for instance in bridge for index, token in enumerate(times) if float(token) * 1.0e12 < T0_PS)
    hold_equal = all(bridge[instance][index] == canonical_bridge[instance][start] for instance in bridge for index in range(start, min(start + shift, len(times))))
    post_equal = all(bridge[instance][index] == canonical_bridge[instance][index - shift] for instance in bridge for index in range(start + shift, len(times))) if shift else True
    return {
        "path": rel(path),
        "sha256": sha256(path),
        "bytes": path.stat().st_size,
        "point_count": len(times),
        "authority_grid": "canonical stored time tokens",
        "delay_ps": delay_ps,
        "stored_sample_shift": shift,
        "start_sample_index": start,
        "start_time_ps": float(times[start]) * 1.0e12,
        "pre_110_nonanticipation": pre_equal,
        "hold_rule_check": hold_equal,
        "post_shift_rule_check": post_equal,
        "interpolation": False,
        "resampling": False,
        "amplitude_scaling": False,
        "sign_change": False,
        "canonical_bridge_source": "I(R_S)+I(L_S3), positive node6->node10",
    }


def bridge_direction_audit(trace: Any, mask: str) -> dict[str, Any]:
    records: dict[str, Any] = {}
    all_pass = True
    for index in range(1, 5):
        def col(signal: str) -> list[float]:
            base = signal[:-1] if signal.endswith(")") else signal
            return [float(value) for value in trace.column(f"{base}|XBVM{index})")]
        rs = col("I(R_S)")
        ls3 = col("I(L_S3)")
        vrs = col("V(R_S)")
        vls3 = col("V(L_S3)")
        js1 = col("I(B_JS1)")
        lpse = col("I(L_PSE)")
        js2 = col("I(B_JS2)")
        lpsl = col("I(L_PSL)")
        bridge = [a + b for a, b in zip(rs, ls3)]
        resistor_residual = [v - 3.0 * i for v, i in zip(vrs, rs)]
        voltage_residual = [a - b for a, b in zip(vrs, vls3)]
        node6_residual = [b - a - c - d for b, a, c, d in zip(bridge, js1, lpse, [0.0] * len(bridge))]
        # At node 6 the signed current balance is bridge - I(B_JS1) - I(L_PSE).
        node10_residual = [b + a - c for b, a, c in zip(bridge, js2, lpsl)]
        representative_v = max(max(abs(value) for value in vrs), 1.0e-12)
        representative_i = max(max(abs(value) for value in bridge), 1.0e-12)
        resistor_max = max(abs(value) for value in resistor_residual)
        voltage_max = max(abs(value) for value in voltage_residual)
        node6_max = max(abs(value) for value in node6_residual)
        node10_max = max(abs(value) for value in node10_residual)
        sign_agreement = sum((i == 0.0 or v == 0.0 or i * v > 0.0) for i, v in zip(rs, vrs)) / len(rs)
        passed = bool(resistor_max <= max(representative_v * 1.0e-7, 1.0e-9) and voltage_max <= max(representative_v * 1.0e-9, 1.0e-12) and node6_max <= max(representative_i * 1.0e-6, 1.0e-10) and node10_max <= max(representative_i * 1.0e-6, 1.0e-10) and sign_agreement > 0.99)
        all_pass = all_pass and passed
        records[f"XBVM{index}"] = {
            "status": "PASS" if passed else "FAIL",
            "branch_endpoints": {"R_S": "6 -> 10", "L_S3": "6 -> 10"},
            "positive_direction": "node6 -> node10",
            "bridge_current_definition": "I(R_S) + I(L_S3)",
            "resistor_law_max_abs_V": resistor_max,
            "parallel_voltage_max_abs_V": voltage_max,
            "node6_kcl_max_abs_A": node6_max,
            "node10_kcl_max_abs_A": node10_max,
            "R_S_voltage_current_sign_agreement": sign_agreement,
            "bridge_current_min_A": min(bridge),
            "bridge_current_max_A": max(bridge),
            "KCL_equations": {"node6": "I(R_S)+I(L_S3)-I(B_JS1)-I(L_PSE)=0", "node10": "I(R_S)+I(L_S3)+I(B_JS2)-I(L_PSL)=0"},
            "mask_context": mask,
        }
    return {"status": "PASS" if all_pass else "FAIL", "source_orientation": "positive = node6 -> node10", "instances": records, "all_instances_pass": all_pass}


def clone_bvm_subckt(instance: int, payload: str) -> str:
    original = (SOURCE_INPUTS / "bvm_jm2_connected.cir").read_text(encoding="utf-8")
    lines = original.splitlines()
    start = next(index for index, line in enumerate(lines) if line.strip().lower() == ".subckt bvm wl bl se sl")
    end = next(index for index in range(start + 1, len(lines)) if lines[index].strip().lower() == ".ends bvm")
    body = lines[start:end + 1]
    output: list[str] = [f"* BVM_REPLAY_{instance}: canonical BVM body; only R_S/L_S3 are replaced by an ideal current replay."]
    rs_count = 0
    ls3_count = 0
    for line in body:
        stripped = line.strip()
        if stripped.lower() == ".subckt bvm wl bl se sl":
            output.append(f".subckt BVM_REPLAY_{instance} WL BL SE SL")
        elif re.fullmatch(r"R_S\s+6\s+10\s+3\.0", stripped, flags=re.IGNORECASE):
            output.append(f"I_BRIDGE_REPLAY 6 10 {payload}")
            rs_count += 1
        elif re.fullmatch(r"L_S3\s+6\s+10\s+0\.5P", stripped, flags=re.IGNORECASE):
            ls3_count += 1
        elif stripped.lower() == ".ends bvm":
            output.append(f".ends BVM_REPLAY_{instance}")
        else:
            output.append(line)
    if rs_count != 1 or ls3_count != 1:
        raise RuntimeError(f"BVM clone replacement count for {instance}: R_S={rs_count}, L_S3={ls3_count}")
    return "\n".join(output) + "\n"


def include_path(path: Path, deck_dir: Path) -> str:
    return Path(os.path.relpath(path, deck_dir)).as_posix()


def transformed_deck(mask: str, case_id: str, bridge_payloads: dict[str, str], deck_dir: Path) -> str:
    original = CANONICAL_DECKS[mask].read_text(encoding="utf-8")
    include_targets = {
        "../../inputs/jjmit.cir": SOURCE_INPUTS / "jjmit.cir",
        "../../inputs/BQ_parameterized_bjs400_rj2.cir": SOURCE_INPUTS / "BQ_parameterized_bjs400_rj2.cir",
        "../../inputs/jtl2.cir": SOURCE_INPUTS / "jtl2.cir",
    }
    output: list[str] = []
    clones_inserted = False
    instance_count = 0
    bridge_probe_replacements = 0
    bridge_probe_skips = 0
    for line in original.splitlines():
        stripped = line.strip()
        if stripped.startswith(".include "):
            include_name = stripped.split(None, 1)[1]
            if "bvm_jm2_connected.cir" in include_name:
                continue
            if include_name not in include_targets:
                raise RuntimeError(f"unexpected canonical include: {include_name}")
            output.append(f".include {include_path(include_targets[include_name], deck_dir)}")
            continue
        instance_match = re.fullmatch(r"XBVM([1-4]) WL\1 BL\1 SE\1 COMMON_SL BVM", stripped)
        if instance_match:
            if not clones_inserted:
                for index in range(1, 5):
                    output.append(clone_bvm_subckt(index, bridge_payloads[f"XBVM{index}"]))
                clones_inserted = True
            instance = int(instance_match.group(1))
            output.append(f"XBVM{instance} WL{instance} BL{instance} SE{instance} COMMON_SL BVM_REPLAY_{instance}")
            instance_count += 1
            continue
        if stripped.startswith(".print ") and "I(R_S|XBVM" in stripped:
            instance = int(re.search(r"XBVM([1-4])", stripped).group(1))
            output.append(f".print I(I_BRIDGE_REPLAY|XBVM{instance}) V(6|XBVM{instance}) V(10|XBVM{instance})")
            bridge_probe_replacements += 1
            continue
        if stripped.startswith(".print ") and "I(L_S3|XBVM" in stripped:
            bridge_probe_skips += 1
            continue
        output.append(line)
    if not clones_inserted or instance_count != 4 or bridge_probe_replacements != 4 or bridge_probe_skips != 4:
        raise RuntimeError(f"deck transform counts: clones={clones_inserted}, instances={instance_count}, bridge_probe={bridge_probe_replacements}, skips={bridge_probe_skips}")
    text = "\n".join(output) + "\n"
    if ".tran 0.1p 200p" not in text or "XBQ1 QBIN QBOUT BQ" not in text or "R_TERM JTL6_OUT 0 10" not in text:
        raise RuntimeError("canonical QB/JTL/terminal closure missing from transformed deck")
    if "R_S     6       10      3.0" in text or "L_S3    6       10      0.5P" in text:
        raise RuntimeError("active canonical bridge element remained in transformed deck")
    return text


def raw_expected_headers(canonical_trace: Any) -> set[str]:
    headers = set(canonical_trace.headers)
    for index in range(1, 5):
        for element in ("R_S", "L_S3"):
            headers.discard(f"I({element}|XBVM{index})")
            headers.discard(f"V({element}|XBVM{index})")
        headers.update((f"I(I_BRIDGE_REPLAY|XBVM{index})", f"V(6|XBVM{index})", f"V(10|XBVM{index})"))
    return headers


def source_inventory() -> list[dict[str, Any]]:
    records = [
        record_file("runner", SCRIPT, "bridge-current replay generator, gate arithmetic, QA, visualization, and packager"),
        record_file("global_jjmit_model", SOURCE_INPUTS / "jjmit.cir", "canonical global JJ model"),
        record_file("canonical_bvm_template", SOURCE_INPUTS / "bvm_jm2_connected.cir", "immutable BVM clone template"),
        record_file("canonical_qb_include", SOURCE_INPUTS / "BQ_parameterized_bjs400_rj2.cir", "canonical QB include"),
        record_file("canonical_jtl_include", SOURCE_INPUTS / "jtl2.cir", "canonical six-stage JTL include"),
        record_file("canonical_qb_hash_guard", REPO / "circuits" / "qb" / "bq_parameterized_v1.cir", "public QB hash guard"),
        record_file("josim_solver", SOLVER, "recorded physical solver"),
        record_file("plotter", PLOTTER, "standard descriptive renderer"),
        record_file("shared_tline_helpers", REPO / "scripts" / "bvm_qb_tline_feedback_dephasing.py", "read-only raw/phase/waveform/plot helper"),
        record_file("shared_z0_metrics_helpers", REPO / "scripts" / "bvm_qb_tline_z0_rescue_gate.py", "read-only QB/JTL/re-arm metrics helper"),
        record_file("shared_replay_helpers", REPO / "scripts" / "bvm_qb_boundary_timing_replay.py", "read-only raw/grid helper dependency"),
        record_file("tx_syntax_fixture", REPO / "test" / "comp" / "tx.cir", "TLINE context fixture; no new TLINE solve"),
    ]
    for mask in MASKS:
        records.extend([
            record_file(f"canonical_{mask}_raw", CANONICAL[mask], "read-only canonical closed-loop raw"),
            record_file(f"canonical_{mask}_deck", CANONICAL_DECKS[mask], "read-only canonical closed-loop deck"),
        ])
    for name, path in CONTEXT_EXPERIMENTS.items():
        records.append(record_file(name, path, "read-only accepted previous experiment context"))
    return records


def assert_sources(source_records: Iterable[dict[str, Any]] | None = None) -> None:
    if git_head() != EXPECTED_HEAD:
        raise RuntimeError(f"HEAD changed: {git_head()} != {EXPECTED_HEAD}")
    if remote_head() != EXPECTED_HEAD:
        raise RuntimeError(f"bvm/master changed: {remote_head()} != {EXPECTED_HEAD}")
    for path, expected in SOURCE_HASHES.items():
        if expected is None:
            continue
        if not path.is_file() or sha256(path) != expected:
            raise RuntimeError(f"registered source changed or missing: {path}")
    for mask, expected in EXPECTED_CANONICAL_RAW_HASHES.items():
        if sha256(CANONICAL[mask]) != expected:
            raise RuntimeError(f"canonical raw changed: {CANONICAL[mask]}")
    if source_records:
        for item in source_records:
            path = REPO / item["path"]
            if sha256(path) != item["sha256"]:
                raise RuntimeError(f"source closure changed: {path}")


def case_info(case_id: str) -> dict[str, Any]:
    if case_id.startswith("EXACT_"):
        return {"case_id": case_id, "mask": case_id.split("_", 1)[1], "delay_ps": 0.0, "shift": 0, "stage": "EXACT"}
    match = re.fullmatch(r"DELAY0P(3|6)_(0011|0111)", case_id)
    if not match:
        raise RuntimeError(f"unknown case: {case_id}")
    delay = 0.3 if match.group(1) == "3" else 0.6
    return {"case_id": case_id, "mask": match.group(2), "delay_ps": delay, "shift": DELAY_SHIFTS[delay], "stage": "DELAY"}


def case_dir(case_id: str) -> Path:
    return EXP / "runs" / case_id


def make_source_and_deck(case_id: str, source_times: list[str], source_values: dict[str, list[float]], canonical_bridge: dict[str, list[float]]) -> tuple[dict[str, Any], dict[str, Any]]:
    info = case_info(case_id)
    bridge = make_bridge_values(source_values, source_times, info["delay_ps"])
    source_path = EXP / "inputs" / "replay_sources" / f"{case_id}_bridge_current.csv"
    source_record = source_csv(source_path, source_times, bridge, canonical_bridge, info["delay_ps"])
    payloads = {instance: "PWL(" + " ".join(item for row, token in enumerate(source_times) for item in (time_token_ps(token), current_token(bridge[instance][row]))) + ")" for instance in bridge}
    deck_path = case_dir(case_id) / "deck.cir"
    deck_path.parent.mkdir(parents=True, exist_ok=True)
    deck_path.write_text(transformed_deck(info["mask"], case_id, payloads, deck_path.parent), encoding="utf-8")
    deck_record = {
        "run_id": case_id,
        "case_id": case_id,
        "mask": info["mask"],
        "stage": info["stage"],
        "delay_ps": info["delay_ps"],
        "stored_sample_shift": info["shift"],
        "source": source_record,
        "path": rel(deck_path),
        "sha256": sha256(deck_path),
        "bytes": deck_path.stat().st_size,
        "payload_sha256": {instance: sha256_text(payloads[instance]) for instance in payloads},
        "payload_bytes": {instance: len(payloads[instance].encode("utf-8")) for instance in payloads},
        "topology_transform": "canonical BVM body cloned per instance; active R_S/L_S3 removed; I_BRIDGE_REPLAY 6 10 PWL inserted; QB/JTL/terminal retained",
    }
    return source_record, deck_record


def append_yaml_registration(records: dict[str, Any], section: str) -> None:
    path = EXP / "experiment.yaml"
    text = path.read_text(encoding="utf-8").rstrip()
    lines = ["", f"{section}:"]
    for key, item in records.items():
        lines.extend([
            f"  - run_id: {key}",
            f"    path: {item['path']}",
            f"    sha256: {item['sha256']}",
            f"    bytes: {item['bytes']}",
            f"    mask: \"{item['mask']}\"",
            f"    delay_ps: {item['delay_ps']}",
            f"    stored_sample_shift: {item['stored_sample_shift']}",
            f"    source_csv: {item['source']['path']}",
            f"    source_csv_sha256: {item['source']['sha256']}",
        ])
    path.write_text(text + "\n" + "\n".join(lines) + "\n", encoding="utf-8")


def prepare() -> None:
    if EXP.exists():
        existing = {item.name for item in EXP.iterdir()}
        if existing - {"PREFLIGHT.md", "experiment.yaml"}:
            raise RuntimeError(f"refusing to overwrite non-empty experiment directory: {EXP}")
        if not {"PREFLIGHT.md", "experiment.yaml"}.issubset(existing):
            raise RuntimeError(f"experiment directory is incomplete: {EXP}")
    if CONTRACT_SENTENCE not in (EXP / "PREFLIGHT.md").read_text(encoding="utf-8"):
        raise RuntimeError("PREFLIGHT.md is missing the contract sentence")
    assert_sources()
    canonical_traces = {mask: load_raw(CANONICAL[mask]) for mask in MASKS}
    direction_audit = {mask: bridge_direction_audit(canonical_traces[mask], mask) for mask in MASKS}
    if not all(item["status"] == "PASS" for item in direction_audit.values()):
        raise RuntimeError(f"bridge direction/KCL preflight failed: {direction_audit}")
    EXP.mkdir(parents=True, exist_ok=True)
    (EXP / "runs").mkdir()
    (EXP / "plots").mkdir()
    (EXP / "analysis").mkdir()
    source_records = source_inventory()
    registered_decks: dict[str, Any] = {}
    source_records_by_mask: dict[str, Any] = {}
    for mask in MASKS:
        times, _, values = source_tokens(CANONICAL[mask])
        canonical_bridge = {f"XBVM{index}": [values[f"I(R_S|XBVM{index})"][row] + values[f"I(L_S3|XBVM{index})"][row] for row in range(len(times))] for index in range(1, 5)}
        source_record, deck_record = make_source_and_deck(f"EXACT_{mask}", times, values, canonical_bridge)
        registered_decks[f"EXACT_{mask}"] = deck_record
        source_records_by_mask[mask] = {"times": times, "values": values, "canonical_bridge": canonical_bridge, "source_record": source_record}
    append_yaml_registration(registered_decks, "exact_deck_registration")
    write_json(EXP / "analysis" / "SOURCE_MANIFEST.json", {"schema": "bvm-rloop-bridge-timing-source-manifest-v1", "experiment_id": EXP.name, "generated_at": now(), "source_closure": source_records, "canonical_raw_hashes": EXPECTED_CANONICAL_RAW_HASHES, "context_experiments": {name: rel(path) for name, path in CONTEXT_EXPERIMENTS.items()}, "direction_audit": direction_audit})
    transformation_registry = {
        "schema": "bvm-rloop-bridge-timing-transformation-registry-v1",
        "experiment_id": EXP.name,
        "generated_at": now(),
        "raw_mutation": False,
        "operations": [
            {"name": "bridge_current_definition", "input": "I(R_S|XBVMn)+I(L_S3|XBVMn)", "direction": "positive node6 -> node10", "same_instance_only": True, "interpolation": False},
            {"name": "exact_bridge_replay", "delay_ps": 0.0, "stored_sample_shift": 0, "rule": "canonical bridge current at each exact stored sample"},
            {"name": "delayed_bridge_replay", "delay_ps": [0.3, 0.6], "stored_sample_shift": [3, 6], "rule": "pre-110 identical, hold at canonical 110 ps, then exact index shift", "interpolation": False, "resampling": False, "amplitude_scaling": False, "sign_change": False},
            {"name": "phase_navigation", "rule": "independent continuous unwrap(raw radians)/(2*pi); navigation only; not SFQ count"},
            {"name": "same_jj_phase_area", "rule": "same JJ, direct same-endpoint voltage, same window, actual-grid trapezoid / Phi0"},
        ],
    }
    write_json(EXP / "analysis" / "TRANSFORMATION_REGISTRY.json", transformation_registry)
    provenance = {
        "schema": "bvm-rloop-bridge-timing-replay-provenance-v1",
        "experiment_id": EXP.name,
        "created_at": now(),
        "registration_head": EXPECTED_HEAD,
        "remote_bvm_master_at_registration": EXPECTED_HEAD,
        "contract_sentence": CONTRACT_SENTENCE,
        "scientific_review_authorized": False,
        "mechanical_analysis_performed": False,
        "bounded_experiment_interpretation_performed": False,
        "independent_scientific_review_performed": False,
        "scientific_interpretation_performed": False,
        "solver": replay_base.solver_context(),
        "source_closure": source_records,
        "canonical_reference_raw_hashes": EXPECTED_CANONICAL_RAW_HASHES,
        "direction_audit": direction_audit,
        "frozen": {
            "question": "Can timing-only replay of the canonical R_S//L_S3 bridge current preserve N2=2 while suppressing N3 retrigger/runaway?",
            "topology": "canonical BVM array -> COMMON_SL -> JSL1..8 -> canonical QB -> JTL1..6 -> 10 ohm terminal",
            "intervention": "only per-instance replacement of R_S 6 10 3.0 and L_S3 6 10 0.5P by I_BRIDGE_REPLAY 6 10 PWL",
            "TD_ps": 0.0,
            "time_step_ps": 0.1,
            "stop_time_ps": 200.0,
            "windows_ps": [list(window) for window in WINDOWS_PS],
            "window_semantics": "half-open actual stored timestamps",
            "no_QB_change": True,
            "no_JSL_change": True,
            "no_JTL_change": True,
            "no_terminal_change": True,
            "no_stimulus_change": True,
            "no_timestep_sweep": True,
            "no_sentinel": True,
            "no_extra_delay": True,
        },
        "authorized_matrix": {
            "exact": [{"case_id": case_id, "mask": case_info(case_id)["mask"], "delay_ps": 0.0, "stored_sample_shift": 0} for case_id in EXACT_CASES],
            "delayed": [{"case_id": case_id, "mask": case_info(case_id)["mask"], "delay_ps": case_info(case_id)["delay_ps"], "stored_sample_shift": case_info(case_id)["shift"], "exact_gate_required": True} for case_id in DELAY_CASES],
            "max_physical_solves": 6,
            "delayed_solve_gate": "mechanical exact fidelity PASS only",
            "forbidden": ["1.0 ps", "1.2 ps", "other delay", "transformer", "sentinel", "LS3 sweep", "QB sweep", "timestep sweep"],
        },
        "registered_decks": registered_decks,
        "runs": {},
        "run_order": [],
        "execution": {"authorized_physical_solve_count": 6, "actual_physical_solve_count": 0, "solver_invocation_count": 0, "exact_count": 0, "delayed_count": 0},
        "probe_policy": {"raw_expected_headers_by_mask": {mask: sorted(raw_expected_headers(canonical_traces[mask])) for mask in MASKS}, "bridge_current": "I(I_BRIDGE_REPLAY|XBVMn)", "bridge_voltage_equivalent": "V(6|XBVMn)-V(10|XBVMn)", "canonical_bridge_voltage": "V(R_S|XBVMn) = V(L_S3|XBVMn)"},
        "fidelity_screen": {"timing_tolerance_ps": EXACT_TIMING_TOL_PS, "phase_p2p_tolerance_turns": EXACT_PHASE_P2P_TOL_TURNS, "normalized_waveform_rms_tolerance": EXACT_NORMALIZED_WAVEFORM_RMS_TOL, "waveform_errors_reported": True, "bridge_voltage_mismatch_reported_but_not_silent": True},
        "analysis": {"status": "PENDING"},
        "qa": {"status": "PENDING"},
        "visualization": {"status": "PENDING"},
        "package": {"status": "PENDING", "drive_file_id": None, "drive_url": None},
        "stop": {"final_marker": None, "automatic_follow_up": False},
    }
    write_json(EXP / "provenance.json", provenance)
    result = {
        "schema": "bvm-rloop-bridge-timing-replay-result-v1",
        "experiment_id": EXP.name,
        "generated_at": now(),
        "status": "PREFLIGHT_PASS_EXACT_PENDING",
        "artifact_status": "PENDING",
        "scientific_review_authorized": False,
        "mechanical_analysis_performed": False,
        "bounded_experiment_interpretation_performed": False,
        "independent_scientific_review_performed": False,
        "scientific_interpretation_performed": False,
        "execution": provenance["execution"],
        "cases": {case_id: {"status": "REGISTERED_NOT_RUN" if case_id in DELAY_CASES else "AUTHORIZED_NOT_RUN"} for case_id in ALL_CASES},
        "fidelity": {"status": "PENDING"},
        "mechanical_comparison": {"status": "PENDING"},
        "classification": {"status": "SCIENTIFIC_REVIEW_REQUIRED", "assigned": None, "candidate_categories": ["FEEDBACK_PATH_TIMING_SELECTIVITY_SUPPORTED", "BRIDGE_TIMING_NONSELECTIVE", "BRIDGE_CURRENT_TIMING_INSUFFICIENT", "BRIDGE_CURRENT_REPLAY_FIXTURE_INVALID"]},
        "unknown": ["scientific interpretation", "mechanism strength", "physical current-source equivalence", "physical delay implementation", "SFQ event identity/count", "timestep/solver convergence"],
        "stop": {"final_marker": None, "automatic_follow_up": False},
    }
    write_json(EXP / "result.json", result)
    (EXP / "RESULT.md").write_text("# BVM R-loop bridge timing replay\n\nPreflight passed. Only EXACT_0011 and EXACT_0111 are materialized; delayed cases remain gated on mechanical exact fidelity.\n", encoding="utf-8")
    print(json.dumps({"status": "PREFLIGHT_PASS", "experiment": rel(EXP), "head": EXPECTED_HEAD, "exact_cases": list(EXACT_CASES), "delayed_cases_registered_but_not_materialized": list(DELAY_CASES), "direction_audit": direction_audit}, ensure_ascii=False, indent=2))


def warning_lines(log: Path) -> list[str]:
    if not log.is_file():
        return ["missing_log"]
    return [line.strip() for line in log.read_text(errors="replace").splitlines() if any(token in line for token in ("Missing model:", "Unknown device/node", "Cannot store results", "Error", "error"))]


def execute_cases(case_ids: Iterable[str]) -> None:
    provenance = read_json(EXP / "provenance.json")
    for case_id in case_ids:
        if case_id not in provenance["registered_decks"]:
            raise RuntimeError(f"case is not materialized/registered: {case_id}")
        item = provenance["registered_decks"][case_id]
        deck = REPO / item["path"]
        directory = deck.parent
        raw = directory / "raw.csv"
        log = directory / "run.log"
        metadata = directory / "metadata.json"
        if raw.exists() or log.exists() or metadata.exists():
            raise RuntimeError(f"refusing overwrite/retry: {case_id}")
        if sha256(deck) != item["sha256"]:
            raise RuntimeError(f"registered deck changed: {case_id}")
        command = [str(SOLVER), "-a", "1", "-o", str(raw), str(deck)]
        started = now()
        with log.open("x", encoding="utf-8") as stream:
            stream.write(f"experiment={EXP.name}\nrun_id={case_id}\nstarted_at={started}\ncommand={' '.join(command)}\n")
            stream.flush()
            completed = subprocess.run(command, cwd=REPO, stdout=stream, stderr=subprocess.STDOUT, check=False)
            finished = now()
            stream.write(f"finished_at={finished}\nexit_code={completed.returncode}\n")
        run_record: dict[str, Any] = {
            "run_id": case_id,
            "case_id": case_id,
            "mask": item["mask"],
            "stage": item["stage"],
            "delay_ps": item["delay_ps"],
            "stored_sample_shift": item["stored_sample_shift"],
            "command": command,
            "deck": {"path": rel(deck), "sha256": sha256(deck), "bytes": deck.stat().st_size},
            "log": {"path": rel(log), "sha256": sha256(log), "bytes": log.stat().st_size},
            "solver": replay_base.solver_context(),
            "started_at": started,
            "finished_at": finished,
            "physical_solve_this_experiment": True,
            "raw_immutable": True,
            "mechanical_analysis_performed": False,
            "bounded_experiment_interpretation_performed": False,
            "independent_scientific_review_performed": False,
        }
        if completed.returncode != 0 or not raw.is_file() or raw.stat().st_size == 0:
            run_record["execution_status"] = "SOLVER_FAIL"
            run_record["raw"] = {"path": rel(raw), "exists": raw.is_file(), "sha256": sha256(raw) if raw.is_file() else None, "bytes": raw.stat().st_size if raw.is_file() else None}
            provenance["runs"][case_id] = run_record
            provenance["run_order"].append(case_id)
            provenance["execution"]["actual_physical_solve_count"] = len(provenance["run_order"])
            provenance["execution"]["solver_invocation_count"] = len(provenance["run_order"])
            provenance["execution"]["exact_count"] = sum(1 for key in provenance["run_order"] if key.startswith("EXACT_"))
            provenance["execution"]["delayed_count"] = sum(1 for key in provenance["run_order"] if key.startswith("DELAY"))
            provenance["execution_status"] = "SOLVER_FAILURE_STOP"
            write_json(EXP / "provenance.json", provenance)
            raise RuntimeError(f"solver failed for {case_id}; preserved and stopped")
        try:
            trace = load_raw(raw)
            missing = sorted(set(provenance["probe_policy"]["raw_expected_headers_by_mask"][item["mask"]]) - set(trace.headers))
            run_record["raw"] = {"path": rel(raw), "sha256": sha256(raw), "bytes": raw.stat().st_size, "sample_count": trace.sample_count, "time_start_ps": trace.time[0] * 1.0e12, "time_end_ps": trace.time[-1] * 1.0e12, "grid": replay_base.finite_grid_qa(trace), "missing_required_probes": missing}
            run_record["solver_warning_lines"] = warning_lines(log)
            run_record["execution_status"] = "RUN_PASS" if not missing else "RUN_PASS_MISSING_PROBES"
        except Exception as exc:
            run_record["execution_status"] = "RAW_PARSE_FAILURE"
            run_record["raw_parse_error"] = str(exc)
            run_record["raw"] = {"path": rel(raw), "sha256": sha256(raw), "bytes": raw.stat().st_size}
            provenance["runs"][case_id] = run_record
            provenance["run_order"].append(case_id)
            provenance["execution"]["actual_physical_solve_count"] = len(provenance["run_order"])
            provenance["execution"]["solver_invocation_count"] = len(provenance["run_order"])
            provenance["execution_status"] = "RAW_FAILURE_STOP"
            write_json(EXP / "provenance.json", provenance)
            raise RuntimeError(f"raw parse failed for {case_id}; preserved and stopped") from exc
        run_record["metadata"] = {"path": rel(metadata), "source_csv": item["source"], "deck_sha256": sha256(deck), "raw_sha256": sha256(raw), "log_sha256": sha256(log), "execution_status": run_record["execution_status"]}
        write_json(metadata, run_record["metadata"])
        provenance["runs"][case_id] = run_record
        provenance["run_order"].append(case_id)
        provenance["execution"]["actual_physical_solve_count"] = len(provenance["run_order"])
        provenance["execution"]["solver_invocation_count"] = len(provenance["run_order"])
        provenance["execution"]["exact_count"] = sum(1 for key in provenance["run_order"] if key.startswith("EXACT_"))
        provenance["execution"]["delayed_count"] = sum(1 for key in provenance["run_order"] if key.startswith("DELAY"))
        write_json(EXP / "provenance.json", provenance)
        if missing:
            provenance["execution_status"] = "RAW_PROBE_FAILURE_STOP"
            write_json(EXP / "provenance.json", provenance)
            raise RuntimeError(f"required probes missing for {case_id}: {missing}")
    provenance["execution_status"] = "EXACT_RUNS_COMPLETE" if all(key.startswith("EXACT_") for key in provenance["run_order"]) else "ALL_AUTHORIZED_RUNS_COMPLETE"
    write_json(EXP / "provenance.json", provenance)
    result = read_json(EXP / "result.json")
    result["status"] = "EXACT_RUNS_COMPLETE_ANALYSIS_PENDING" if provenance["execution"]["delayed_count"] == 0 else "ALL_AUTHORIZED_RUNS_COMPLETE_ANALYSIS_PENDING"
    result["artifact_status"] = "VALID"
    result["execution"] = provenance["execution"]
    for key in provenance["run_order"]:
        result["cases"][key] = {"status": provenance["runs"][key]["execution_status"], "raw_path": provenance["runs"][key]["raw"]["path"], "raw_sha256": provenance["runs"][key]["raw"]["sha256"]}
    write_json(EXP / "result.json", result)
    print(json.dumps({"status": "RUN_PASS", "run_order": provenance["run_order"], "actual_physical_solve_count": provenance["execution"]["actual_physical_solve_count"]}, ensure_ascii=False, indent=2))


def analyze_bridge(trace: Any, mask: str, canonical: bool) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for index in range(1, 5):
        instance = f"XBVM{index}"
        if canonical:
            current = [a + b for a, b in zip(trace.column(f"I(R_S|{instance})"), trace.column(f"I(L_S3|{instance})"))]
            voltage = list(trace.column(f"V(R_S|{instance})"))
            source_signal = "I(R_S)+I(L_S3)"
            voltage_signal = "V(R_S)=V(L_S3)"
        else:
            current = list(trace.column(f"I(I_BRIDGE_REPLAY|{instance})"))
            voltage = [a - b for a, b in zip(trace.column(f"V(6|{instance})"), trace.column(f"V(10|{instance})"))]
            source_signal = f"I(I_BRIDGE_REPLAY|{instance})"
            voltage_signal = f"V(6|{instance})-V(10|{instance})"
        output[instance] = {
            "current_signal": source_signal,
            "voltage_signal": voltage_signal,
            "direction": "node6 -> node10",
            "current_focus": vector_stats(trace, source_signal, current, FOCUS_WINDOW) | {"unit": "A"},
            "current_rearm": vector_stats(trace, source_signal, current, REARM_WINDOW) | {"unit": "A"},
            "voltage_focus": vector_stats(trace, voltage_signal, voltage, FOCUS_WINDOW),
            "voltage_rearm": vector_stats(trace, voltage_signal, voltage, REARM_WINDOW),
            "current_rearm_signs": sign_metrics_from_values(trace, source_signal, current, REARM_WINDOW),
        }
    return {"status": "DERIVED", "source_orientation": "positive node6 -> node10", "instances": output, "canonical_direct_branch_voltage": canonical}


def sign_metrics_from_values(trace: Any, signal: str, values: list[float], window: tuple[float, float]) -> dict[str, Any]:
    indices = time_indices(trace, *window)
    selected = [values[index] for index in indices]
    times = [trace.time[index] for index in indices]
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
            if sustained is None and len(selected[position:position + REARM_DWELL_SAMPLES]) == REARM_DWELL_SAMPLES and all(item > 0.0 for item in selected[position:position + REARM_DWELL_SAMPLES]):
                sustained = times[position] * 1.0e12
        if previous == 1 and sign == -1 and first_pos_neg is None:
            first_pos_neg = times[position] * 1.0e12
        previous = sign
    positive_dwell = sum((times[index + 1] - times[index]) * 1.0e12 for index in range(len(times) - 1) if selected[index] > 0.0)
    negative_dwell = sum((times[index + 1] - times[index]) * 1.0e12 for index in range(len(times) - 1) if selected[index] < 0.0)
    return {"status": "DERIVED", "signal": signal, "window_ps": list(window), "sample_count": len(selected), "minimum": min(selected), "maximum": max(selected), "zero_sign_crossings": tline_helpers.zero_crossing_count(selected), "first_negative_to_positive_crossing_ps": first_neg_pos, "first_sustained_negative_to_positive_crossing_ps": sustained, "first_positive_to_negative_crossing_ps": first_pos_neg, "positive_dwell_ps": positive_dwell, "negative_dwell_ps": negative_dwell, "actual_grid": True}


def bvm_metrics(trace: Any, mask: str, canonical: bool) -> dict[str, Any]:
    cells: dict[str, Any] = {}
    for index in range(1, 5):
        instance = f"XBVM{index}"
        phase_nav = {f"P({element}|{instance})": phase_navigation(trace, f"P({element}|{instance})") for element in JUNCTIONS}
        phase_area_records = {f"P({element}|{instance})": phase_area(trace, f"P({element}|{instance})", f"V({element}|{instance})") for element in ("B_JS1", "B_JS2")}
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
        cells[instance] = {"phase_navigation": phase_nav, "phase_area": phase_area_records, "focus_waveforms": focus, "rearm_waveforms": rearm, "rloop_focus": {signal: focus[signal] for element in RLOOP_BRANCHES for kind in ("I", "V") for signal in (f"{kind}({element}|{instance})",) if signal in focus}}
    return {"active_bvm_instances": [f"XBVM{index}" for index in range(1, 5)], "cells": cells, "bridge": analyze_bridge(trace, mask, canonical)}


def run_metrics(case_id: str, trace: Any, canonical: bool = False) -> dict[str, Any]:
    info = case_info(case_id) if not canonical else {"mask": case_id.split("_", 1)[1], "delay_ps": None, "shift": None}
    mask = info["mask"]
    qb = z0_helpers.qb_metrics(trace)
    source_signals = ("I(B_JSL8)", "I(LIN|XBQ1)")
    source = {
        "focus": {signal: compact_waveform(waveform_stats(trace, signal, FOCUS_WINDOW)) for signal in source_signals if signal in trace.headers},
        "rearm": {signal: compact_waveform(waveform_stats(trace, signal, REARM_WINDOW)) for signal in source_signals if signal in trace.headers},
        "rearm_signs": {signal: sign_metrics(trace, signal, REARM_WINDOW) for signal in source_signals if signal in trace.headers},
        "rearm_signed_areas": {signal: waveform_stats(trace, signal, REARM_WINDOW).get("signed_area") for signal in source_signals if signal in trace.headers},
    }
    jsl = z0_helpers.jsl_metrics(trace)
    jtl = z0_helpers.jtl_metrics(trace)
    bvm = bvm_metrics(trace, mask, canonical)
    return {
        "run_id": case_id,
        "mask": mask,
        "delay_ps": info["delay_ps"],
        "stored_sample_shift": info["shift"],
        "canonical_reference": canonical,
        "raw_path": rel(trace.path),
        "raw_sha256": sha256(trace.path),
        "grid": replay_base.finite_grid_qa(trace),
        "qb": qb,
        "bvm": bvm,
        "jsl": jsl,
        "jtl": jtl,
        "source": source,
        "focus_waveforms": {signal: compact_waveform(waveform_stats(trace, signal, FOCUS_WINDOW)) for signal in ("V(COMMON_SL)", "V(QBIN)", "V(QBOUT)", "V(JTL6_OUT)", "I(R_TERM)") if signal in trace.headers},
        "rearm_waveforms": {signal: compact_waveform(waveform_stats(trace, signal, REARM_WINDOW)) for signal in ("V(COMMON_SL)", "V(QBIN)", "V(QBOUT)", "V(JTL6_OUT)", "I(R_TERM)") if signal in trace.headers},
        "phase_semantics": "P raw radians; continuous unwrap then rad/(2*pi) navigation only",
        "area_semantics": "same JJ/endpoints/direction/window; actual-grid trapezoid; not an SFQ count",
        "terminal_role": "downstream corroboration only, not the sole oracle",
        "scientific_interpretation_performed": False,
    }


def normalized_signal_delta(reference: Any, candidate: Any, signal: str, window: tuple[float, float]) -> dict[str, Any]:
    indices = time_indices(reference, *window)
    if signal not in reference.headers or signal not in candidate.headers:
        return {"status": "UNKNOWN", "signal": signal, "window_ps": list(window)}
    left = list(reference.column(signal))
    right = list(candidate.column(signal))
    if signal.startswith("P("):
        left_u = unwrap(left)
        right_u = unwrap(right)
        delta = [(right_u[index] - left_u[index]) / TAU for index in indices]
        return {"status": "DERIVED", "signal": signal, "window_ps": list(window), "unit": "turns", "raw_unit": "radians", "max_abs_delta_turns": max(abs(value) for value in delta), "rms_delta_turns": math.sqrt(sum(value * value for value in delta) / len(delta)), "endpoint_delta_turns": delta[-1], "independent_unwrap_before_subtract": True}
    delta = [right[index] - left[index] for index in indices]
    scale = max(max(left[index] for index in indices) - min(left[index] for index in indices), max(abs(left[index]) for index in indices), 1.0e-30)
    rms = math.sqrt(sum(value * value for value in delta) / len(delta))
    return {"status": "DERIVED", "signal": signal, "window_ps": list(window), "unit": "A" if signal.startswith("I(") else "V", "max_abs_delta": max(abs(value) for value in delta), "rms_delta": rms, "normalized_rms": rms / scale, "reference_scale": scale, "time_of_max_abs_delta_ps": reference.time[indices[max(range(len(indices)), key=lambda position: abs(delta[position]))]] * 1.0e12, "actual_grid": True}


def key_trajectory_deltas(reference: Any, candidate: Any, mask: str) -> dict[str, Any]:
    signals = ["I(B_JSL8)", "V(COMMON_SL)", "V(QBIN)", "I(LIN|XBQ1)", "I(L1|XBQ1)", "I(L2|XBQ1)", "V(QBOUT)", "V(JTL6_OUT)", "I(R_TERM)"]
    for index in range(1, 5):
        for element in ("B_JS1", "B_JS2", "B_JM1", "B_JM2"):
            signals.extend(f"{kind}({element}|XBVM{index})" for kind in ("P", "V", "I"))
    return {"focus_110_121": {signal: normalized_signal_delta(reference, candidate, signal, FOCUS_WINDOW) for signal in signals if signal in reference.headers and signal in candidate.headers}, "full_0_200": {signal: normalized_signal_delta(reference, candidate, signal, FULL_WINDOW) for signal in signals if signal in reference.headers and signal in candidate.headers}}


def exact_fidelity(canonical_metrics: dict[str, Any], exact_metrics: dict[str, Any], canonical_trace: Any, exact_trace: Any, mask: str) -> dict[str, Any]:
    canonical_oracle = canonical_metrics["qb"]["ordered_navigation_oracle"]
    exact_oracle = exact_metrics["qb"]["ordered_navigation_oracle"]
    canonical_count = canonical_oracle["ordered_navigation_candidate_count"]
    exact_count = exact_oracle["ordered_navigation_candidate_count"]
    timing: dict[str, Any] = {}
    timing_deltas: list[float] = []
    for name in ("BJ1", "BJ2"):
        canonical_time = canonical_oracle["navigation"][name]["positive_threshold_navigation_times_ps"].get("0.5")
        exact_time = exact_oracle["navigation"][name]["positive_threshold_navigation_times_ps"].get("0.5")
        delta = exact_time - canonical_time if canonical_time is not None and exact_time is not None else None
        if delta is not None:
            timing_deltas.append(abs(delta))
        timing[name] = {"canonical_ps": canonical_time, "exact_ps": exact_time, "delta_ps": delta}
    phase_records: dict[str, Any] = {}
    phase_deltas: list[float] = []
    for index in range(1, 5):
        instance = f"XBVM{index}"
        if mask == "0011" or mask == "0111":
            for element in ("B_JS1", "B_JS2"):
                signal = f"P({element}|{instance})"
                c = canonical_metrics["bvm"]["cells"][instance]["phase_navigation"].get(signal)
                e = exact_metrics["bvm"]["cells"][instance]["phase_navigation"].get(signal)
                if c and e:
                    delta = abs(e["focus_110_121_p2p_turns"] - c["focus_110_121_p2p_turns"])
                    phase_deltas.append(delta)
                    phase_records[signal] = {"canonical_focus_p2p_turns": c["focus_110_121_p2p_turns"], "exact_focus_p2p_turns": e["focus_110_121_p2p_turns"], "absolute_delta_turns": delta, "canonical_endpoint_delta_turns": c["focus_110_121_endpoint_delta_turns"], "exact_endpoint_delta_turns": e["focus_110_121_endpoint_delta_turns"]}
    key_deltas = key_trajectory_deltas(canonical_trace, exact_trace, mask)
    major_signals = ("I(B_JSL8)", "V(COMMON_SL)", "V(QBIN)", "I(LIN|XBQ1)", "I(L1|XBQ1)", "I(L2|XBQ1)", "V(QBOUT)", "V(JTL6_OUT)", "I(R_TERM)")
    normalized_values = [key_deltas["focus_110_121"][signal].get("normalized_rms") for signal in major_signals if key_deltas["focus_110_121"].get(signal, {}).get("normalized_rms") is not None]
    bridge_voltage: dict[str, Any] = {}
    bridge_voltage_deltas: list[float] = []
    for index in range(1, 5):
        instance = f"XBVM{index}"
        canonical_v = list(canonical_trace.column(f"V(R_S|{instance})"))
        exact_v = [a - b for a, b in zip(exact_trace.column(f"V(6|{instance})"), exact_trace.column(f"V(10|{instance})"))]
        indices = time_indices(canonical_trace, *FOCUS_WINDOW)
        delta = [exact_v[i] - canonical_v[i] for i in indices]
        scale = max(max(abs(canonical_v[i]) for i in indices), 1.0e-12)
        rms = math.sqrt(sum(value * value for value in delta) / len(delta))
        bridge_voltage_deltas.append(rms / scale)
        bridge_voltage[instance] = {"canonical_signal": f"V(R_S|{instance})", "exact_signal": f"V(6|{instance})-V(10|{instance})", "focus_max_abs_delta_V": max(abs(value) for value in delta), "focus_rms_delta_V": rms, "focus_normalized_rms": rms / scale, "canonical_voltage_focus": canonical_metrics["bvm"]["bridge"]["instances"][instance]["voltage_focus"], "exact_voltage_focus": exact_metrics["bvm"]["bridge"]["instances"][instance]["voltage_focus"], "severe_mismatch_screen": rms / scale > EXACT_NORMALIZED_WAVEFORM_RMS_TOL}
    current_replay: dict[str, Any] = {}
    current_errors: list[float] = []
    # The source CSV contains the exact imposed current; compare its values to
    # JoSIM's printed branch current on the actual stored grid.
    source_info = read_json(EXP / "provenance.json")["registered_decks"][exact_metrics["run_id"]]["source"]
    source_path = REPO / source_info["path"]
    with source_path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    for index in range(1, 5):
        signal = f"I(I_BRIDGE_REPLAY|XBVM{index})"
        imposed = [float(row[f"I_BRIDGE_XBVM{index}_A"]) for row in rows]
        actual = list(exact_trace.column(signal))
        errors = [actual[row] - imposed[row] for row in range(len(actual))]
        max_error = max(abs(value) for value in errors)
        current_errors.append(max_error)
        current_replay[f"XBVM{index}"] = {"signal": signal, "max_abs_current_error_A": max_error, "rms_current_error_A": math.sqrt(sum(value * value for value in errors) / len(errors)), "source_csv": source_info["path"]}
    criteria = {
        "grid_equal": tuple(canonical_trace.time) == tuple(exact_trace.time),
        "candidate_count_equal": exact_count == canonical_count and ((mask == "0011" and canonical_count == 2) or (mask == "0111" and canonical_count == 4)),
        "first_BJ_timing_within_registered_tolerance": bool(timing_deltas) and max(timing_deltas) <= EXACT_TIMING_TOL_PS,
        "JS_phase_p2p_within_registered_tolerance": bool(phase_deltas) and max(phase_deltas) <= EXACT_PHASE_P2P_TOL_TURNS,
        "major_waveform_normalized_rms_within_registered_tolerance": bool(normalized_values) and max(normalized_values) <= EXACT_NORMALIZED_WAVEFORM_RMS_TOL,
        "required_main_trajectory_metrics_present": all(signal in key_deltas["focus_110_121"] for signal in major_signals),
    }
    passed = all(criteria.values())
    return {"status": "PASS" if passed else "FAIL", "mask": mask, "canonical_ordered_candidate_count": canonical_count, "exact_ordered_candidate_count": exact_count, "criteria": criteria, "registered_tolerances": {"timing_ps": EXACT_TIMING_TOL_PS, "phase_p2p_turns": EXACT_PHASE_P2P_TOL_TURNS, "normalized_waveform_rms": EXACT_NORMALIZED_WAVEFORM_RMS_TOL}, "QB_timing": timing, "phase_p2p": phase_records, "key_trajectory_deltas": key_deltas, "bridge_voltage_comparison": bridge_voltage, "maximum_bridge_voltage_normalized_rms": max(bridge_voltage_deltas), "bridge_current_injection_fidelity": current_replay, "maximum_replay_current_error_A": max(current_errors), "same_JJ_phase_area_exact": exact_metrics["bvm"]["cells"], "same_JJ_phase_area_canonical": canonical_metrics["bvm"]["cells"], "fidelity_interpretation": "mechanical gate only; no physical-equivalence or current-sufficiency claim"}


def delayed_mechanical_comparison(analyses: dict[str, Any], canonical: dict[str, Any], exact: dict[str, Any]) -> dict[str, Any]:
    n2: dict[str, Any] = {}
    n3: dict[str, Any] = {}
    for key, item in analyses.items():
        target = n2 if item["mask"] == "0011" else n3
        oracle = item["qb"]["ordered_navigation_oracle"]
        target[key] = {
            "delay_ps": item.get("delay_ps"),
            "ordered_candidate_count": oracle["ordered_navigation_candidate_count"],
            "first_BJ1_plus_0p5_ps": oracle["navigation"]["BJ1"]["positive_threshold_navigation_times_ps"].get("0.5"),
            "first_BJ2_plus_0p5_ps": oracle["navigation"]["BJ2"]["positive_threshold_navigation_times_ps"].get("0.5"),
            "second_BJ1_plus_1p5_ps": oracle["navigation"]["BJ1"]["positive_threshold_navigation_times_ps"].get("1.5"),
            "second_BJ2_plus_1p5_ps": oracle["navigation"]["BJ2"]["positive_threshold_navigation_times_ps"].get("1.5"),
            "L1_rearm": item["qb"]["rearm_signs"].get("I(L1|XBQ1)"),
            "L2_rearm": item["qb"]["rearm_signs"].get("I(L2|XBQ1)"),
            "source_BJSL8_rearm": item["source"]["rearm_signs"].get("I(B_JSL8)"),
            "source_LIN_rearm": item["source"]["rearm_signs"].get("I(LIN|XBQ1)"),
            "JS1_JS2_focus_p2p_by_cell": {instance: {element: item["bvm"]["cells"][instance]["phase_navigation"].get(f"P({element}|{instance})", {}).get("focus_110_121_p2p_turns") for element in ("B_JS1", "B_JS2")} for instance in item["bvm"]["cells"]},
            "phase_area_residuals_turns": {signal: value.get("phase_minus_area_turns") for cell in item["bvm"]["cells"].values() for signal, value in cell["phase_area"].items()},
        }
    n2_counts = {key: item["ordered_candidate_count"] for key, item in n2.items()}
    n3_p2p = {key: item["JS1_JS2_focus_p2p_by_cell"].get("XBVM2") for key, item in n3.items()}
    return {"status": "DERIVED", "N2": n2, "N3": n3, "N2_all_delays_preserve_two": all(item["ordered_candidate_count"] >= 2 for key, item in n2.items() if key.startswith("DELAY")), "N3_directional_p2p_records": n3_p2p, "N2_ordered_candidate_counts": n2_counts, "scientific_category_assignment": "REVIEW_REQUIRED", "not_an_SFQ_count": True}


def independent_recalculation(paths: dict[str, Path], masks: dict[str, str]) -> dict[str, Any]:
    output: dict[str, Any] = {"status": "PASS", "method": "fresh csv.DictReader, independent unwrap and actual-grid trapezoid", "grid": {}, "ordered_navigation_candidate_count": {}, "phase_area": {}}
    for label, path in paths.items():
        with path.open(newline="", encoding="utf-8-sig") as stream:
            reader = csv.DictReader(stream)
            rows = list(reader)
            headers = reader.fieldnames or []
        times = [float(row["time"]) for row in rows]
        output["grid"][label] = len(times) == 1999 and times[0] == 0.0 and times[-1] == 1.999e-10 and all(right > left for left, right in zip(times, times[1:]))
        names = ["P(BJ1|XBQ1)", "P(BJ2|XBQ1)", *[f"P(B01|XJTL1_{stage})" for stage in JTL_STAGES]]
        if all(name in headers for name in names):
            unwrapped = {name: unwrap([float(row[name]) for row in rows]) for name in names}
            base = next(index for index, time in enumerate(times) if time * 1.0e12 >= 101.0)
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
            active = 3 if mask == "0011" else 2
            phase_area_records = {}
            focus = [index for index, time in enumerate(times) if 110.0 <= time * 1.0e12 < 121.0]
            for element in ("B_JS1", "B_JS2"):
                p_name = f"P({element}|XBVM{active})"
                v_name = f"V({element}|XBVM{active})"
                if p_name not in headers or v_name not in headers:
                    continue
                phase = unwrap([float(row[p_name]) for row in rows])
                phase_delta = (phase[focus[-1]] - phase[focus[0]]) / TAU
                voltage = [float(row[v_name]) for row in rows]
                area = actual_integral([times[index] for index in focus], [voltage[index] for index in focus]) / PHI0
                phase_area_records[element] = {"phase_delta_turns": phase_delta, "voltage_area_over_Phi0_turns": area, "residual_turns": phase_delta - area}
            output["phase_area"][label] = phase_area_records
    output["all_grids_valid"] = all(output["grid"].values())
    return output


def compact_result_run(item: dict[str, Any]) -> dict[str, Any]:
    oracle = item["qb"]["ordered_navigation_oracle"]
    return {"run_id": item["run_id"], "mask": item["mask"], "delay_ps": item.get("delay_ps"), "ordered_candidate_count": oracle["ordered_navigation_candidate_count"], "first_BJ1_plus_0p5_ps": oracle["navigation"]["BJ1"]["positive_threshold_navigation_times_ps"].get("0.5"), "first_BJ2_plus_0p5_ps": oracle["navigation"]["BJ2"]["positive_threshold_navigation_times_ps"].get("0.5"), "second_BJ1_plus_1p5_ps": oracle["navigation"]["BJ1"]["positive_threshold_navigation_times_ps"].get("1.5"), "second_BJ2_plus_1p5_ps": oracle["navigation"]["BJ2"]["positive_threshold_navigation_times_ps"].get("1.5"), "L1_rearm": item["qb"]["rearm_signs"].get("I(L1|XBQ1)"), "L2_rearm": item["qb"]["rearm_signs"].get("I(L2|XBQ1)"), "source_BJSL8_rearm": item["source"]["rearm_signs"].get("I(B_JSL8)"), "source_LIN_rearm": item["source"]["rearm_signs"].get("I(LIN|XBQ1)"), "raw_path": item["raw_path"], "raw_sha256": item["raw_sha256"]}


def compact_fidelity_result(item: dict[str, Any]) -> dict[str, Any]:
    major_signals = ("I(B_JSL8)", "V(COMMON_SL)", "V(QBIN)", "I(LIN|XBQ1)", "I(L1|XBQ1)", "I(L2|XBQ1)", "V(QBOUT)", "V(JTL6_OUT)", "I(R_TERM)")
    focus = item.get("key_trajectory_deltas", {}).get("focus_110_121", {})
    return {
        "status": item.get("status"),
        "mask": item.get("mask"),
        "canonical_ordered_candidate_count": item.get("canonical_ordered_candidate_count"),
        "exact_ordered_candidate_count": item.get("exact_ordered_candidate_count"),
        "criteria": item.get("criteria"),
        "registered_tolerances": item.get("registered_tolerances"),
        "QB_timing": item.get("QB_timing"),
        "phase_p2p": item.get("phase_p2p"),
        "major_waveform_focus_normalized_rms": {signal: focus.get(signal, {}).get("normalized_rms") for signal in major_signals},
        "bridge_voltage_focus": {instance: {key: value for key, value in item.get("bridge_voltage_comparison", {}).get(instance, {}).items() if key in ("focus_max_abs_delta_V", "focus_rms_delta_V", "focus_normalized_rms", "severe_mismatch_screen")} for instance in ("XBVM1", "XBVM2", "XBVM3", "XBVM4")},
        "maximum_replay_current_error_A": item.get("maximum_replay_current_error_A"),
        "fidelity_interpretation": item.get("fidelity_interpretation"),
    }


def analyze() -> None:
    provenance = read_json(EXP / "provenance.json")
    keys = list(provenance.get("run_order", []))
    if keys[:2] != list(EXACT_CASES) or len(keys) not in (2, 6):
        raise RuntimeError(f"analysis requires exactly two exact runs or all six authorized runs: {keys}")
    if len(keys) == 6 and keys != list(ALL_CASES):
        raise RuntimeError(f"unexpected authorized run order: {keys}")
    # The first analysis attempt found a missing helper export.  This is a
    # post-solve tooling repair only: verify pinned physics sources first,
    # then seal the revised analyzer dependency without touching raw files.
    assert_sources()
    current_runner = record_file("runner", SCRIPT, "bridge-current replay generator, gate arithmetic, QA, visualization, and packager")
    if not any(item.get("name") == "shared_z0_metrics_helpers" for item in provenance.get("source_closure", [])):
        provenance["source_closure"].append(record_file("shared_z0_metrics_helpers", REPO / "scripts" / "bvm_qb_tline_z0_rescue_gate.py", "read-only QB/JTL/re-arm metrics helper"))
    registered_runner = next((item for item in provenance["source_closure"] if item.get("name") == "runner"), None)
    if registered_runner is not None and registered_runner.get("sha256") != current_runner["sha256"]:
        provenance["postsolve_tooling_revision"] = {"path": rel(SCRIPT), "old_sha256": registered_runner.get("sha256"), "new_sha256": current_runner["sha256"], "reason": "repair missing QB/JTL helper import after analysis attempt; no deck/raw/solver/runs changed", "physical_rerun": False, "raw_mutated": False}
        registered_runner.update({"sha256": current_runner["sha256"], "bytes": current_runner["bytes"]})
    for item in provenance["source_closure"]:
        source_path = REPO / item["path"]
        if not source_path.is_file() or sha256(source_path) != item["sha256"]:
            raise RuntimeError(f"source closure changed before analysis: {source_path}")
    write_json(EXP / "analysis" / "SOURCE_MANIFEST.json", {"schema": "bvm-rloop-bridge-timing-source-manifest-v1", "experiment_id": EXP.name, "generated_at": now(), "source_closure": provenance["source_closure"], "canonical_raw_hashes": EXPECTED_CANONICAL_RAW_HASHES, "context_experiments": {name: rel(path) for name, path in CONTEXT_EXPERIMENTS.items()}, "direction_audit": provenance["direction_audit"], "postsolve_tooling_revision": provenance.get("postsolve_tooling_revision")})
    canonical_traces = {mask: load_raw(CANONICAL[mask]) for mask in MASKS}
    previous_hashes_before = {path: sha256(REPO / path) for path in [item["path"] for item in provenance["source_closure"] if item["name"].startswith("canonical_") or item["name"] in CONTEXT_EXPERIMENTS]}
    traces: dict[str, Any] = {}
    metrics: dict[str, Any] = {}
    raw_before: dict[str, str] = {}
    for key in keys:
        record = provenance["runs"][key]
        path = REPO / record["raw"]["path"]
        trace = load_raw(path)
        expected = set(provenance["probe_policy"]["raw_expected_headers_by_mask"][record["mask"]])
        missing = sorted(expected - set(trace.headers))
        if missing:
            raise RuntimeError(f"required raw probes missing during analysis: {key}: {missing}")
        if tuple(trace.time) != tuple(canonical_traces[record["mask"]].time):
            raise RuntimeError(f"stored grid mismatch: {key}")
        traces[key] = trace
        raw_before[key] = sha256(path)
        metrics[key] = run_metrics(key, trace, canonical=False)
    canonical_metrics = {mask: run_metrics(f"CANONICAL_{mask}", canonical_traces[mask], canonical=True) for mask in MASKS}
    exact_fidelity_records = {mask: exact_fidelity(canonical_metrics[mask], metrics[f"EXACT_{mask}"], canonical_traces[mask], traces[f"EXACT_{mask}"], mask) for mask in MASKS}
    exact_pass = all(record["status"] == "PASS" for record in exact_fidelity_records.values())
    delayed_comparison = delayed_mechanical_comparison(metrics, canonical_metrics["0011"], metrics["EXACT_0011"]) if len(keys) == 6 else None
    paths = {f"CANONICAL_{mask}": CANONICAL[mask] for mask in MASKS}
    masks = {f"CANONICAL_{mask}": mask for mask in MASKS}
    for key in keys:
        paths[key] = REPO / provenance["runs"][key]["raw"]["path"]
        masks[key] = provenance["runs"][key]["mask"]
    independent = independent_recalculation(paths, masks)
    raw_after = {key: sha256(REPO / provenance["runs"][key]["raw"]["path"]) for key in keys}
    previous_hashes_after = {path: sha256(REPO / path) for path in previous_hashes_before}
    if raw_before != raw_after or previous_hashes_before != previous_hashes_after:
        raise RuntimeError("raw or read-only references changed during analysis")
    provenance["mechanical_analysis_performed"] = True
    provenance["bounded_experiment_interpretation_performed"] = False
    provenance["independent_scientific_review_performed"] = False
    provenance["scientific_interpretation_performed"] = False
    provenance["raw_hash_before_analysis"] = raw_before
    provenance["raw_hash_after_analysis"] = raw_after
    provenance["reference_hashes_before_analysis"] = previous_hashes_before
    provenance["reference_hashes_after_analysis"] = previous_hashes_after
    provenance["analysis"] = {
        "status": "COMPLETE",
        "generated_at": now(),
        "mechanical_analysis_performed": True,
        "bounded_experiment_interpretation_performed": False,
        "independent_scientific_review_performed": False,
        "current_runs": metrics,
        "canonical_references": canonical_metrics,
        "exact_fidelity": exact_fidelity_records,
        "delayed_mechanical_comparison": delayed_comparison,
        "independent_numerical_recalculation": independent,
        "same_grid": True,
        "interpolation": False,
        "scientific_classification": "NOT_ASSIGNED_SCIENTIFIC_REVIEW_REQUIRED",
    }
    if not exact_pass:
        provenance["outcome"] = {"status": "FAIL", "classification": "BRIDGE_CURRENT_REPLAY_FIXTURE_INVALID", "interpretation_layer": "mechanical exact-fidelity fixture gate", "reason": "At least one EXACT case failed the preregistered raw chronology/trajectory fidelity screen; delayed cases must not run.", "delayed_cases_authorized": False}
        provenance["execution_status"] = "EXACT_FIDELITY_FAIL_STOP"
        provenance["stop"] = {"final_marker": FINAL_MARKER, "automatic_follow_up": False, "delayed_cases_run": 0, "sentinel_follow_up": False}
    elif len(keys) == 2:
        provenance["outcome"] = {"status": "EXACT_GATE_PASS", "classification": "DELAYED_CASES_AUTHORIZED", "interpretation_layer": "mechanical exact-fidelity gate", "reason": "Both exact cases passed the preregistered mechanical screen; the four registered delayed solves may now be materialized.", "delayed_cases_authorized": True}
        provenance["execution_status"] = "EXACT_FIDELITY_PASS_DELAYED_PENDING"
        provenance["stop"] = {"final_marker": None, "automatic_follow_up": False}
    else:
        provenance["outcome"] = {"status": "SCIENTIFIC_REVIEW_REQUIRED", "classification": "NOT_ASSIGNED", "interpretation_layer": "mechanical registered comparison complete", "reason": "Exact gate passed and all four delayed cases completed; Outcome A/B/C assignment is reserved for explicit scientific review.", "delayed_cases_authorized": True}
        provenance["execution_status"] = "ANALYSIS_COMPLETE"
        provenance["stop"] = {"final_marker": FINAL_MARKER, "automatic_follow_up": False, "delayed_cases_run": 4, "sentinel_follow_up": False}
    for key in keys:
        provenance["runs"][key]["mechanical_analysis_performed"] = True
        provenance["runs"][key]["bounded_experiment_interpretation_performed"] = False
        provenance["runs"][key]["independent_scientific_review_performed"] = False
    write_json(EXP / "provenance.json", provenance)
    result = read_json(EXP / "result.json")
    result["generated_at"] = now()
    result["status"] = "EXACT_FIDELITY_FAIL_STOP" if not exact_pass else "EXACT_FIDELITY_PASS_DELAYED_PENDING" if len(keys) == 2 else "ANALYSIS_COMPLETE"
    result["artifact_status"] = "VALID"
    result["scientific_review_authorized"] = False
    result["mechanical_analysis_performed"] = True
    result["bounded_experiment_interpretation_performed"] = False
    result["independent_scientific_review_performed"] = False
    result["scientific_interpretation_performed"] = False
    result["execution"] = provenance["execution"]
    result["fidelity"] = {"status": "PASS" if exact_pass else "FAIL", "by_mask": {mask: compact_fidelity_result(item) for mask, item in exact_fidelity_records.items()}, "delayed_authorized": exact_pass}
    result["mechanical_comparison"] = delayed_comparison
    result["exact_runs"] = {key: compact_result_run(metrics[key]) for key in EXACT_CASES}
    if len(keys) == 6:
        result["delayed_runs"] = {key: compact_result_run(metrics[key]) for key in DELAY_CASES}
    result["independent_numerical_recalculation"] = independent
    result["classification"] = {"status": "SCIENTIFIC_REVIEW_REQUIRED", "assigned": None, "mechanical_gate": provenance["outcome"], "candidate_categories": result["classification"].get("candidate_categories", [])}
    result["stop"] = provenance["stop"]
    write_json(EXP / "result.json", result)
    write_review_files(provenance, result)
    (EXP / "RESULT.md").write_text(result_markdown(result), encoding="utf-8")
    print(json.dumps({"status": result["status"], "exact_fidelity": "PASS" if exact_pass else "FAIL", "delayed_cases_authorized": exact_pass, "actual_physical_solve_count": len(keys)}, ensure_ascii=False, indent=2))


def write_review_files(provenance: dict[str, Any], result: dict[str, Any]) -> None:
    fidelity = result.get("fidelity", {})
    independent = result.get("independent_numerical_recalculation", {})
    numerical = [
        "# Numerical review — mechanical only",
        "",
        "Scientific interpretation is not performed in this artifact.",
        "",
        f"- Exact fidelity status: `{fidelity.get('status')}`.",
        f"- Independent fresh-CSV grid check: `{independent.get('all_grids_valid')}`.",
        f"- Independent ordered-navigation counts: `{json.dumps(independent.get('ordered_navigation_candidate_count', {}), ensure_ascii=False)}`.",
        "- P(...) remains raw radians; turns use independent unwrap/(2*pi).",
        "- Phase-area checks use the same JJ, endpoints, direction, half-open window, and actual-grid trapezoid.",
        "- No timestep convergence or solver sensitivity was authorized: UNKNOWN.",
    ]
    adversarial = [
        "# Adversarial review probes — mechanical only",
        "",
        f"- No-op/wrong-branch probe: canonical direction audit status `{provenance.get('direction_audit', {}).get('0011', {}).get('status')}` / `{provenance.get('direction_audit', {}).get('0111', {}).get('status')}`; replay source direction is registered as 6 -> 10.",
        "- Coupling probe: four BVM instances have separate PWL source columns and separate cloned subcircuits; no common replay waveform is used.",
        "- Weak-oracle probe: ordered navigation uses internal BJ1, BJ2, JTL1..6; terminal is corroboration only.",
        f"- Stale-artifact probe: current raw before/after equal `{provenance.get('raw_hash_before_analysis') == provenance.get('raw_hash_after_analysis')}` and read-only reference hashes equal `{provenance.get('reference_hashes_before_analysis') == provenance.get('reference_hashes_after_analysis')}`.",
        "- Boundary probe: exact stored-grid delay shifts, 110-ps hold, half-open windows; no interpolation or resampling.",
        "- Overclaim guard: no current-is-fundamental claim, no physical delay implementation claim, no SFQ count, no root-cause claim, and no Outcome A/B/C assignment.",
    ]
    (EXP / "analysis" / "NUMERICAL_REVIEW.md").write_text("\n".join(numerical) + "\n", encoding="utf-8")
    (EXP / "analysis" / "ADVERSARIAL_REVIEW.md").write_text("\n".join(adversarial) + "\n", encoding="utf-8")


def materialize_delayed() -> None:
    provenance = read_json(EXP / "provenance.json")
    if provenance.get("outcome", {}).get("classification") != "DELAYED_CASES_AUTHORIZED":
        raise RuntimeError("delayed cases require EXACT fidelity PASS")
    if any(case_id in provenance.get("registered_decks", {}) for case_id in DELAY_CASES):
        raise RuntimeError("delayed cases already materialized")
    canonical_data: dict[str, Any] = {}
    delayed_records: dict[str, Any] = {}
    for mask in MASKS:
        times, _, values = source_tokens(CANONICAL[mask])
        bridge = {f"XBVM{index}": [values[f"I(R_S|XBVM{index})"][row] + values[f"I(L_S3|XBVM{index})"][row] for row in range(len(times))] for index in range(1, 5)}
        canonical_data[mask] = (times, values, bridge)
    for delay in DELAYS_PS:
        for mask in MASKS:
            case_id = f"DELAY0P{int(delay * 10)}_{mask}"
            times, values, bridge = canonical_data[mask]
            _, record = make_source_and_deck(case_id, times, values, bridge)
            delayed_records[case_id] = record
    append_yaml_registration(delayed_records, "delayed_deck_registration")
    provenance["registered_decks"].update(delayed_records)
    provenance["delayed_materialization"] = {"status": "PASS", "cases": DELAY_CASES, "materialized_at": now(), "no_other_delay_points": True}
    write_json(EXP / "provenance.json", provenance)
    print(json.dumps({"status": "DELAYED_CASES_MATERIALIZED", "cases": list(DELAY_CASES)}, ensure_ascii=False, indent=2))


def result_markdown(result: dict[str, Any]) -> str:
    classification = result.get("classification", {})
    lines = [
        f"# BVM R-loop bridge timing replay ({EXP.name})",
        "",
        f"- Status: `{result.get('status')}`",
        f"- Artifact status: `{result.get('artifact_status')}`",
        f"- Scientific interpretation: `NOT_PERFORMED`; independent scientific review: `NOT_PERFORMED`.",
        f"- Mechanical gate/outcome: `{result.get('fidelity', {}).get('status')}` / `{result.get('classification', {}).get('mechanical_gate', {}).get('classification', 'pending')}`.",
        f"- HEAD: `{EXPECTED_HEAD}`; topology is canonical BVM -> COMMON_SL -> JSL1..8 -> canonical QB -> JTL1..6 -> terminal.",
        "- Intervention: per-instance ideal bridge-current forcing from node 6 to node 10; this is a counterfactual replay, not a physical device design.",
        "",
        "## Registered solves",
        "",
        "| run | mask | delay (ps) | ordered QB/JTL candidates | BJ1 +0.5 (ps) | BJ2 +0.5 (ps) | BJ1 +1.5 (ps) | BJ2 +1.5 (ps) |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for key in list(EXACT_CASES) + list(DELAY_CASES):
        item = result.get("exact_runs", {}).get(key) or result.get("delayed_runs", {}).get(key)
        if not item:
            continue
        lines.append(f"| `{key}` | {item.get('mask')} | {format_number(item.get('delay_ps'))} | {format_number(item.get('ordered_candidate_count'))} | {format_number(item.get('first_BJ1_plus_0p5_ps'))} | {format_number(item.get('first_BJ2_plus_0p5_ps'))} | {format_number(item.get('second_BJ1_plus_1p5_ps'))} | {format_number(item.get('second_BJ2_plus_1p5_ps'))} |")
    lines += [
        "",
        "## Exact replay fidelity",
        "",
        "The exact screen uses the pre-registered mechanical thresholds (timing 0.2 ps, JS1/JS2 focus p2p 0.25 turns, key-waveform normalized RMS 0.50). Actual errors, bridge differential voltage, source injection error, JM1/JM2, QB, JSL, JTL, terminal, and same-JJ phase/area data remain in `provenance.json`.",
        "",
        "P(...) raw values are radians. Displayed turns are only independent continuous-unwrapped rad/(2*pi) navigation values, never SFQ counts. Terminal traces are corroboration only.",
        "",
        "## Bridge sign and voltage evidence",
        "",
        "Canonical bridge current is `I(R_S)+I(L_S3)` with positive direction node6 -> node10. Canonical `V(R_S)=V(L_S3)` and node6/node10 KCL were checked before deck generation. Replay bridge voltage is derived as `V(6)-V(10)` and is not silently treated as equal to canonical branch voltage.",
        "",
        "## Scientific boundary",
        "",
        "The artifact does not assign `FEEDBACK_PATH_TIMING_SELECTIVITY_SUPPORTED`, `BRIDGE_TIMING_NONSELECTIVE`, or `BRIDGE_CURRENT_TIMING_INSUFFICIENT`. Those require explicit scientific review. This replay does not prove current is the unique sufficient state variable, a physical delay implementation, or a physical R_S/L_S3 equivalent.",
        "",
        "Previous QBIN-boundary replay, static LS3 intervention, and TLINE Z0 rescue results are referenced by hash in `provenance.json`; they are not modified or repackaged here.",
        "",
        "- Standalone and comparison descriptive plots: `plots/`.",
        "- Mechanical QA/reviews/transformation/source manifests: `analysis/`.",
        "- Per-run deck/raw/metadata/log: `runs/`.",
        "- PWL source data: `inputs/replay_sources/`.",
        "- Raw evidence ZIP: Drive-only; delivery identity is outside the ZIP in `delivery_manifest.json`.",
        "",
        f"Stop marker: {result.get('stop', {}).get('final_marker') or 'delayed cases pending exact gate'}",
        "",
    ]
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
    failures: list[str] = []
    checks: dict[str, Any] = {}
    expected_keys = list(EXACT_CASES) if len(keys) == 2 else list(ALL_CASES)
    for key in keys:
        record = provenance["runs"][key]
        deck = REPO / record["deck"]["path"]
        raw = REPO / record["raw"]["path"]
        log = REPO / record["log"]["path"]
        metadata = REPO / record["metadata"]["path"]
        text_value = deck.read_text(encoding="utf-8") if deck.is_file() else ""
        expected = set(provenance["probe_policy"]["raw_expected_headers_by_mask"][record["mask"]])
        warnings = warning_lines(log)
        known_warnings = [line for line in warnings if line in KNOWN_NONFATAL_WARNING_LINES]
        unexpected_warnings = [line for line in warnings if line not in KNOWN_NONFATAL_WARNING_LINES]
        try:
            trace = load_raw(raw)
            missing = sorted(expected - set(trace.headers))
            grid = replay_base.finite_grid_qa(trace)
        except Exception as exc:
            trace = None
            missing = [f"raw_parse_error:{exc}"]
            grid = {"status": "INVALID"}
        source = provenance["registered_decks"][key]["source"]
        source_path = REPO / source["path"]
        deck_ok = bool(text_value.count("B_JSL8 JSL_NODE7 QBIN jjmit area=5.0") == 1 and text_value.count("I_BRIDGE_REPLAY 6 10 PWL(") == 4 and "XBQ1 QBIN QBOUT BQ" in text_value and "R_TERM JTL6_OUT 0 10" in text_value and ".tran 0.1p 200p" in text_value and "R_S     6       10      3.0" not in text_value and "L_S3    6       10      0.5P" not in text_value and not any(token in text_value for token in ("V_REPLAY", "T_BVM_QB", "SENTINEL", "TRANSFORMER", "LC_LADDER")))
        passed = bool(record.get("execution_status") == "RUN_PASS" and deck_ok and sha256(deck) == record["deck"]["sha256"] and sha256(raw) == record["raw"]["sha256"] and source_path.is_file() and sha256(source_path) == source["sha256"] and metadata.is_file() and trace is not None and not missing and not trace.duplicate_columns and grid.get("sample_count") == 1999 and grid.get("time_start_ps") == 0.0 and grid.get("time_end_ps") == 199.9 and grid.get("strictly_increasing_time") is True and not unexpected_warnings)
        if not passed:
            failures.append(key)
        checks[key] = {"status": "PASS" if passed else "ARTIFACT_INVALID", "deck": {"path": rel(deck), "sha256": sha256(deck) if deck.is_file() else None, "registered_sha256": record["deck"]["sha256"], "topology_probe": deck_ok}, "raw": {"path": rel(raw), "sha256": sha256(raw) if raw.is_file() else None, "recorded_sha256": record["raw"]["sha256"], "missing_required_probes": missing, "grid": grid}, "metadata": {"path": rel(metadata), "exists": metadata.is_file()}, "solver_warning_lines": warnings, "known_nonfatal_solver_warnings": known_warnings, "unexpected_solver_warning_lines": unexpected_warnings}
    source_hashes_match = all(sha256(REPO / item["path"]) == item["sha256"] for item in provenance["source_closure"])
    references_match = provenance.get("reference_hashes_before_analysis") == provenance.get("reference_hashes_after_analysis") and all(sha256(REPO / path) == digest for path, digest in provenance.get("reference_hashes_after_analysis", {}).items())
    root_allowed = {"PREFLIGHT.md", "experiment.yaml", "RESULT.md", "result.json", "provenance.json", "delivery_manifest.json", "runs", "plots", "analysis", "inputs"}
    root_unexpected = sorted(path.name for path in EXP.iterdir() if path.name not in root_allowed)
    passed = bool(keys == expected_keys and not failures and source_hashes_match and references_match and provenance.get("raw_hash_before_analysis") == provenance.get("raw_hash_after_analysis") and provenance.get("execution", {}).get("actual_physical_solve_count") == len(keys) and provenance.get("execution", {}).get("actual_physical_solve_count") <= 6 and len(keys) in (2, 6) and not root_unexpected and (EXP / "analysis" / "TRANSFORMATION_REGISTRY.json").is_file() and (EXP / "result.json").stat().st_size <= RESULT_LIMIT_BYTES)
    qa = {"schema": "bvm-rloop-bridge-timing-mechanical-qa-v1", "experiment_id": EXP.name, "generated_at": now(), "status": "PASS" if passed else "FAIL", "artifact_status": "VALID" if passed else "ARTIFACT_INVALID", "head": git_head(), "remote_bvm_master": remote_head(), "run_order": keys, "expected_run_order": expected_keys, "source_hashes_match": source_hashes_match, "references_match": references_match, "raw_hash_before_after_equal": provenance.get("raw_hash_before_analysis") == provenance.get("raw_hash_after_analysis"), "max_physical_solves": 6, "actual_physical_solve_count": provenance.get("execution", {}).get("actual_physical_solve_count"), "no_unregistered_followup": keys in (list(EXACT_CASES), list(ALL_CASES)), "no_timestep_sweep": True, "no_sentinel": True, "root_unexpected_entries": root_unexpected, "runs": checks, "failures": failures, "mechanical_analysis_performed": True, "bounded_experiment_interpretation_performed": False, "independent_scientific_review_performed": False, "result_json_under_limit": (EXP / "result.json").stat().st_size <= RESULT_LIMIT_BYTES}
    write_json(EXP / "analysis" / "MECHANICAL_QA.json", qa)
    provenance["qa"] = qa
    write_json(EXP / "provenance.json", provenance)
    result["qa_summary"] = {"status": qa["status"], "artifact_status": qa["artifact_status"]}
    write_json(EXP / "result.json", result)
    (EXP / "RESULT.md").write_text(result_markdown(result), encoding="utf-8")
    if not passed:
        raise RuntimeError(f"mechanical QA failed: {failures}")
    print(json.dumps({"status": "PASS", "run_order": keys}, ensure_ascii=False, indent=2))


def plotter_html(input_path: Path, output_path: Path, subset: list[str], title: str) -> None:
    command = [sys.executable, str(PLOTTER), str(input_path), "-x", str(output_path), "-t", "sep_comb", "-c", "dark", "-j", "2pi", "-w", title, "-s", *subset]
    completed = subprocess.run(command, cwd=REPO, capture_output=True, text=True, check=False)
    if completed.returncode != 0 or not output_path.is_file() or output_path.stat().st_size == 0:
        raise RuntimeError(f"josim-plot2 failed for {output_path}: {completed.stderr[-1000:]}")


def externalize_plotly_runtime(temporary_html: Path, output_html: Path, asset_path: Path) -> None:
    html = temporary_html.read_text(encoding="utf-8")
    matches = list(re.finditer(r"<script(?P<attrs>[^>]*)>(?P<body>.*?)</script>", html, flags=re.DOTALL))
    runtime_match = next((match for match in matches if len(match.group("body")) > 1_000_000 and ("plotly.js v" in match.group("body") or "var Plotly=" in match.group("body"))), None)
    if runtime_match is None:
        raise RuntimeError(f"embedded Plotly runtime not found: {temporary_html}")
    runtime = runtime_match.group("body")
    asset_path.parent.mkdir(parents=True, exist_ok=True)
    if asset_path.exists() and asset_path.read_text(encoding="utf-8") != runtime:
        raise RuntimeError("Plotly runtime differs between pages")
    if not asset_path.exists():
        asset_path.write_text(runtime, encoding="utf-8")
    asset_ref = Path(os.path.relpath(asset_path, output_html.parent)).as_posix()
    compact = html[:runtime_match.start()] + f'<script src="{asset_ref}"></script>' + html[runtime_match.end():]
    if "plotly.js v" in compact or "var Plotly=" in compact or "cdn.plot.ly" in compact:
        raise RuntimeError(f"Plotly runtime not externalized: {output_html}")
    output_html.parent.mkdir(parents=True, exist_ok=True)
    output_html.write_text(compact, encoding="utf-8")


def render_external(input_path: Path, output_path: Path, signals: list[str], title: str, asset: Path) -> None:
    if output_path.exists():
        html = output_path.read_text(encoding="utf-8")
        ref = Path(os.path.relpath(asset, output_path.parent)).as_posix()
        if ref not in html or "plotly.js v" in html or "var Plotly=" in html or "cdn.plot.ly" in html:
            raise RuntimeError(f"invalid existing plot: {output_path}")
        return
    with tempfile.NamedTemporaryFile(prefix="bvm_bridge_plot_", suffix=".html", delete=False, dir="/tmp") as handle:
        temporary = Path(handle.name)
    try:
        plotter_html(input_path, temporary, signals, title)
        externalize_plotly_runtime(temporary, output_path, asset)
    finally:
        temporary.unlink(missing_ok=True)


def crop_csv(raw: Path, start_ps: float, end_ps: float) -> Path:
    with raw.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.reader(stream)
        header = next(reader)
        rows = [row for row in reader if row and start_ps <= float(row[0]) * 1.0e12 < end_ps]
    with tempfile.NamedTemporaryFile(prefix="bvm_bridge_focus_", suffix=".csv", delete=False, dir="/tmp", mode="w", newline="", encoding="utf-8") as handle:
        path = Path(handle.name)
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)
    return path


def comparison_csv(cases: list[tuple[str, Any]], signals: list[str], window: tuple[float, float] | None = None) -> Path:
    first_trace = cases[0][1]
    indices = list(range(first_trace.sample_count)) if window is None else time_indices(first_trace, *window)
    selected: list[tuple[str, list[float]]] = []
    labels: list[str] = []
    for case_id, trace in cases:
        for signal in signals:
            if signal in trace.headers:
                label = replay_base.prefixed_label(case_id, signal)
                labels.append(label)
                selected.append((label, list(trace.column(signal))))
    with tempfile.NamedTemporaryFile(prefix="bvm_bridge_compare_", suffix=".csv", delete=False, dir="/tmp", mode="w", newline="", encoding="utf-8") as handle:
        path = Path(handle.name)
        writer = csv.writer(handle)
        writer.writerow(["time", *labels])
        for index in indices:
            writer.writerow([f"{first_trace.time[index]:.17e}", *(f"{values[index]:.17e}" for _, values in selected)])
    return path


def bridge_voltage_comparison_csv(cases: list[tuple[str, Any]], window: tuple[float, float] | None = None) -> Path:
    first_trace = cases[0][1]
    indices = list(range(first_trace.sample_count)) if window is None else time_indices(first_trace, *window)
    series: list[tuple[str, list[float]]] = []
    for case_id, trace in cases:
        for index in range(1, 5):
            instance = f"XBVM{index}"
            if f"V(R_S|{instance})" in trace.headers:
                values = list(trace.column(f"V(R_S|{instance})"))
            else:
                values = [a - b for a, b in zip(trace.column(f"V(6|{instance})"), trace.column(f"V(10|{instance})"))]
            series.append((replay_base.prefixed_label(f"{case_id}_XBVM{index}", "V(BRIDGE_6_10)"), values))
    with tempfile.NamedTemporaryFile(prefix="bvm_bridge_voltage_compare_", suffix=".csv", delete=False, dir="/tmp", mode="w", newline="", encoding="utf-8") as handle:
        path = Path(handle.name)
        writer = csv.writer(handle)
        writer.writerow(["time", *[label for label, _ in series]])
        for index in indices:
            writer.writerow([f"{first_trace.time[index]:.17e}", *(f"{values[index]:.17e}" for _, values in series)])
    return path


def visualization() -> None:
    provenance = read_json(EXP / "provenance.json")
    if provenance.get("qa", {}).get("status") != "PASS":
        raise RuntimeError("mechanical QA must pass before visualization")
    asset = EXP / "plots" / "assets" / "plotly.min.js"
    entries: list[dict[str, Any]] = []
    full_specs = {
        "01_SIGNAL_TIMING": ["V(COMMON_SL)", "V(QBIN)", "I(B_JSL8)", "I(LIN|XBQ1)", "V(QBOUT)"],
        "02_BVM_STATE": [signal for index in range(1, 5) for element in ("B_JS1", "B_JS2", "B_JM1", "B_JM2") for signal in (f"P({element}|XBVM{index})", f"V({element}|XBVM{index})", f"I({element}|XBVM{index})")] + [signal for index in range(1, 5) for element in ("L_M3", "L_S1", "L_S2", "L_SL") for signal in (f"I({element}|XBVM{index})", f"V({element}|XBVM{index})")],
        "03_JSL_CHAIN": [signal for index in range(1, 9) for signal in (f"P(B_JSL{index})", f"V(B_JSL{index})", f"I(B_JSL{index})")],
        "04_QB_STATE": ["V(QBIN)", "I(LIN|XBQ1)", "V(LIN|XBQ1)", *[f"{kind}({element}|XBQ1)" for element in ("BJS", "BJ1", "BJ2") for kind in ("P", "V", "I")], *[f"{kind}({element}|XBQ1)" for element in ("L1", "L2", "L3", "RJ1", "RJ2") for kind in ("I", "V")], "V(QBOUT)"],
        "05_JTL_CHAIN": [signal for stage in JTL_STAGES for signal in (f"P(B01|XJTL1_{stage})", f"V(B01|XJTL1_{stage})", f"I(B01|XJTL1_{stage})", f"P(B02|XJTL1_{stage})", f"V(B02|XJTL1_{stage})", f"I(B02|XJTL1_{stage})", f"V(JTL{stage}_OUT)")] + ["I(R_TERM)"],
    }
    for key in provenance["run_order"]:
        record = provenance["runs"][key]
        raw = REPO / record["raw"]["path"]
        trace = load_raw(raw)
        run_dir_path = EXP / "plots" / key
        for page_name, requested in full_specs.items():
            selected = [signal for signal in requested if signal in trace.headers]
            output = run_dir_path / f"{page_name}.html"
            render_external(raw, output, selected, f"{key}: {page_name} full 0-200 ps; raw actual grid", asset)
            entries.append({"kind": "standalone", "run_id": key, "path": rel(output), "raw_path": rel(raw), "raw_sha256": sha256(raw), "sha256": sha256(output), "bytes": output.stat().st_size, "signals": selected, "window_ps": list(FULL_WINDOW), "focused": False, "renderer": rel(PLOTTER), "phase_display": "raw radians; rad/(2*pi) turns navigation only"})
        focus_csv = crop_csv(raw, *FOCUS_WINDOW)
        rearm_csv = crop_csv(raw, *REARM_WINDOW)
        try:
            for page_name, requested in full_specs.items():
                selected = [signal for signal in requested if signal in trace.headers]
                output = run_dir_path / f"{page_name}_focus_110_121.html"
                render_external(focus_csv, output, selected, f"{key}: {page_name} focus [110,121) ps; actual stored samples", asset)
                entries.append({"kind": "standalone", "run_id": key, "path": rel(output), "raw_path": rel(raw), "raw_sha256": sha256(raw), "sha256": sha256(output), "bytes": output.stat().st_size, "signals": selected, "window_ps": list(FOCUS_WINDOW), "focused": True, "derived_input": "actual-grid crop only; no interpolation", "renderer": rel(PLOTTER), "phase_display": "raw radians; rad/(2*pi) turns navigation only"})
            qb_rearm = ["V(QBIN)", "I(LIN|XBQ1)", "I(L1|XBQ1)", "I(L2|XBQ1)", "V(L1|XBQ1)", "V(L2|XBQ1)", "I(B_JSL8)", "V(COMMON_SL)"]
            selected = [signal for signal in qb_rearm if signal in trace.headers]
            output = run_dir_path / "04_QB_STATE_focus_121_130.html"
            render_external(rearm_csv, output, selected, f"{key}: 04_QB_STATE re-arm [121,130) ps; actual stored samples", asset)
            entries.append({"kind": "standalone", "run_id": key, "path": rel(output), "raw_path": rel(raw), "raw_sha256": sha256(raw), "sha256": sha256(output), "bytes": output.stat().st_size, "signals": selected, "window_ps": list(REARM_WINDOW), "focused": True, "derived_input": "actual-grid crop only; no interpolation", "renderer": rel(PLOTTER), "phase_display": "raw radians; rad/(2*pi) turns navigation only"})
        finally:
            focus_csv.unlink(missing_ok=True)
            rearm_csv.unlink(missing_ok=True)
    canonical_traces = {mask: load_raw(CANONICAL[mask]) for mask in MASKS}
    current_traces = {key: load_raw(REPO / provenance["runs"][key]["raw"]["path"]) for key in provenance["run_order"]}
    comparison_entries: list[dict[str, Any]] = []
    compare_specs = {
        "01_SIGNAL_TIMING": ["V(COMMON_SL)", "V(QBIN)", "I(B_JSL8)", "I(LIN|XBQ1)", "V(QBOUT)"],
        "02_BVM_STATE": [signal for index in range(1, 5) for element in ("B_JS1", "B_JS2", "B_JM1", "B_JM2") for signal in (f"P({element}|XBVM{index})", f"V({element}|XBVM{index})", f"I({element}|XBVM{index})")],
        "03_JSL_CHAIN": ["P(B_JSL8)", "V(B_JSL8)", "I(B_JSL8)", "V(COMMON_SL)"],
        "04_QB_STATE": ["V(QBIN)", "I(LIN|XBQ1)", "I(L1|XBQ1)", "I(L2|XBQ1)", "P(BJ1|XBQ1)", "P(BJ2|XBQ1)", "V(QBOUT)"],
        "05_JTL_CHAIN": [*[f"P(B01|XJTL1_{stage})" for stage in JTL_STAGES], *[f"V(JTL{stage}_OUT)" for stage in JTL_STAGES], "I(R_TERM)"],
    }
    for mask in MASKS:
        cases: list[tuple[str, Any]] = [(f"CANONICAL_{mask}", canonical_traces[mask])]
        for key in provenance["run_order"]:
            if provenance["runs"][key]["mask"] == mask:
                cases.append((key, current_traces[key]))
        for page_name, requested in compare_specs.items():
            selected = [signal for signal in requested if all(signal in trace.headers for _, trace in cases)]
            if not selected:
                continue
            for window, suffix in ((None, "full_0_200"), (FOCUS_WINDOW, "focus_110_121")) if page_name in ("01_SIGNAL_TIMING", "02_BVM_STATE", "04_QB_STATE") else ((None, "full_0_200"),):
                temporary = comparison_csv(cases, selected, window)
                output = EXP / "plots" / "comparisons" / f"{mask}_{page_name}_{suffix}.html"
                try:
                    render_external(temporary, output, [replay_base.prefixed_label(case, signal) for case, _ in cases for signal in selected], f"{mask}: canonical/exact/delayed — {page_name} {suffix}", asset)
                finally:
                    temporary.unlink(missing_ok=True)
                comparison_entries.append({"kind": "comparison", "mask": mask, "path": rel(output), "sha256": sha256(output), "bytes": output.stat().st_size, "cases": [case for case, _ in cases], "signals": selected, "window_ps": list(FOCUS_WINDOW if window else FULL_WINDOW), "focused": window is not None, "renderer": rel(PLOTTER), "phase_display": "independent case unwrap and rad/(2*pi) turns navigation"})
        voltage_temp = bridge_voltage_comparison_csv(cases, FOCUS_WINDOW)
        voltage_output = EXP / "plots" / "comparisons" / f"{mask}_BRIDGE_VOLTAGE_focus_110_121.html"
        try:
            voltage_signals = [replay_base.prefixed_label(f"{case}_XBVM{index}", "V(BRIDGE_6_10)") for case, _ in cases for index in range(1, 5)]
            render_external(voltage_temp, voltage_output, voltage_signals, f"{mask}: bridge differential voltage V(6)-V(10) vs canonical V(R_S), focus [110,121) ps", asset)
        finally:
            voltage_temp.unlink(missing_ok=True)
        comparison_entries.append({"kind": "derived_comparison", "mask": mask, "path": rel(voltage_output), "sha256": sha256(voltage_output), "bytes": voltage_output.stat().st_size, "cases": [case for case, _ in cases], "signals": voltage_signals, "window_ps": list(FOCUS_WINDOW), "focused": True, "derived_semantics": "canonical V(R_S) and replay V(6)-V(10); derived comparison, raw inputs preserved", "renderer": rel(PLOTTER), "phase_display": "voltage comparison; no phase conversion"})
    html_paths = sorted((EXP / "plots").rglob("*.html"))
    invalid = [rel(path) for path in html_paths if any(token in path.read_text(encoding="utf-8") for token in ("plotly.js v", "var Plotly=", "cdn.plot.ly"))]
    visualization = {"schema": "bvm-rloop-bridge-timing-visualization-v1", "status": "PASS" if html_paths and asset.is_file() and not invalid and entries and comparison_entries else "FAIL", "generated_at": now(), "renderer": rel(PLOTTER), "layout": "sep_comb", "color": "dark", "phase_option": "2pi", "semantic_structure": ["01_SIGNAL_TIMING", "02_BVM_STATE", "03_JSL_CHAIN", "04_QB_STATE", "05_JTL_CHAIN"], "entries": entries + comparison_entries, "standalone_count": len(entries), "comparison_count": len(comparison_entries), "focused_window_entries": sum(1 for item in entries if item.get("focused")), "asset": {"path": rel(asset), "sha256": sha256(asset) if asset.is_file() else None, "bytes": asset.stat().st_size if asset.is_file() else None}, "raw_hashes_rechecked": all(item["raw_sha256"] == sha256(REPO / item["raw_path"]) for item in entries), "invalid_runtime_pages": invalid, "visualization_is_descriptive_only": True}
    write_json(EXP / "analysis" / "VISUALIZATION_MANIFEST.json", visualization)
    write_json(EXP / "analysis" / "VISUALIZATION_QA.json", {"status": visualization["status"], "standalone_count": len(entries), "comparison_count": len(comparison_entries), "focused_window_entries": visualization["focused_window_entries"], "invalid_runtime_pages": invalid, "raw_hashes_rechecked": visualization["raw_hashes_rechecked"]})
    provenance["visualization"] = visualization
    write_json(EXP / "provenance.json", provenance)
    result = read_json(EXP / "result.json")
    result["visualization_summary"] = {"status": visualization["status"], "standalone_count": len(entries), "comparison_count": len(comparison_entries), "focused_window_entries": visualization["focused_window_entries"]}
    write_json(EXP / "result.json", result)
    (EXP / "RESULT.md").write_text(result_markdown(result), encoding="utf-8")
    if visualization["status"] != "PASS":
        raise RuntimeError(f"visualization QA failed: {invalid}")
    print(json.dumps({"status": "PASS", "standalone_count": len(entries), "comparison_count": len(comparison_entries)}, ensure_ascii=False, indent=2))


def write_evidence_manifests() -> None:
    records: list[dict[str, Any]] = []
    for path in sorted(EXP.rglob("*")):
        if not path.is_file() or path.name in {"delivery_manifest.json"} or path.suffix == ".tmp":
            continue
        records.append({"path": path.relative_to(EXP).as_posix(), "sha256": sha256(path), "bytes": path.stat().st_size})
    write_json(EXP / "analysis" / "RAW_ANALYSIS_HANDOFF_MANIFEST.json", {"schema": "bvm-rloop-bridge-timing-raw-analysis-handoff-v1", "experiment_id": EXP.name, "generated_at": now(), "raw_is_immutable_solver_output": True, "processed_crops_are_not_raw_substitutes": True, "files_excluding_delivery_manifest": records})
    lines = ["# Evidence manifest", "", "Evidence files are listed by repository-relative path, hash, and byte count. The Drive package identity is kept outside the ZIP to avoid self-reference.", "", "| path | SHA-256 | bytes |", "|---|---|---:|"]
    lines.extend(f"| `{item['path']}` | `{item['sha256']}` | {item['bytes']} |" for item in records)
    (EXP / "analysis" / "EVIDENCE_MANIFEST.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def package() -> None:
    provenance = read_json(EXP / "provenance.json")
    if provenance.get("qa", {}).get("status") != "PASS" or provenance.get("visualization", {}).get("status") != "PASS":
        raise RuntimeError("QA and visualization must pass before packaging")
    write_evidence_manifests()
    delivery_dir = Path("/mnt/d/BVM_Backages")
    delivery_dir.mkdir(parents=True, exist_ok=True)
    package_path = delivery_dir / f"{EXP.name}_raw_evidence.zip"
    version = "v1"
    if package_path.exists():
        version = "v2"
        package_path = delivery_dir / f"{EXP.name}_{version}_raw_evidence.zip"
    if package_path.exists():
        raise RuntimeError(f"refusing overwrite of existing package: {package_path}")
    result = read_json(EXP / "result.json")
    provenance["package"] = {"status": "PACKAGE_CONTENT_READY", "version": version, "internal_metadata_status": "ALL_AUTHORIZED_RUNS_COMPLETE_OR_EXACT_GATE_STOP", "delivery_manifest_path": "delivery_manifest.json", "drive_file_id": None, "drive_url": None}
    result["package_summary"] = {"status": "PACKAGE_CONTENT_READY", "version": version, "delivery_manifest_path": "delivery_manifest.json", "drive_file_id": None}
    write_json(EXP / "provenance.json", provenance)
    write_json(EXP / "result.json", result)
    (EXP / "RESULT.md").write_text(result_markdown(result), encoding="utf-8")
    files: list[tuple[Path, str]] = []
    for name in ("experiment.yaml", "PREFLIGHT.md", "RESULT.md", "result.json", "provenance.json"):
        files.append((EXP / name, name))
    for dirname in ("inputs", "runs", "plots", "analysis"):
        for path in sorted((EXP / dirname).rglob("*")):
            if path.is_file():
                files.append((path, path.relative_to(EXP).as_posix()))
    files.append((SCRIPT, "executor/bvm_qb_rloop_bridge_timing_replay.py"))
    records = [{"path": archive_name, "sha256": sha256(path), "bytes": path.stat().st_size} for path, archive_name in files]
    with zipfile.ZipFile(package_path, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path, archive_name in files:
            archive.write(path, archive_name)
    with zipfile.ZipFile(package_path, "r") as archive:
        reopened = {name: hashlib.sha256(archive.read(name)).hexdigest() for name in archive.namelist()}
    expected = {item["path"]: item["sha256"] for item in records}
    qa = {"status": "PASS" if expected == reopened else "FAIL", "package_version": version, "package_path": str(package_path), "package_sha256": sha256(package_path), "package_bytes": package_path.stat().st_size, "file_count": len(records), "expected_file_hashes_match_after_reopen": expected == reopened, "zip_files": records, "not_in_git": True, "contains_current_raw": all(any(item["path"] == provenance["runs"][key]["raw"]["path"] for item in records) for key in provenance["run_order"]), "contains_delivery_manifest": False, "delivery_manifest_outside_zip": True, "git_head_at_packaging": git_head(), "remote_head_at_packaging": remote_head()}
    manifest = {"schema": "bvm-rloop-bridge-timing-delivery-manifest-v1", "experiment_id": EXP.name, "created_at": now(), "status": "READY_FOR_DRIVE_UPLOAD" if qa["status"] == "PASS" else "PACKAGE_INVALID", "package_version": version, "package_path": str(package_path), "package_sha256": qa["package_sha256"], "package_bytes": qa["package_bytes"], "package_qa": qa, "drive_folder_id": DRIVE_FOLDER_ID, "drive_file_id": None, "drive_url": None, "delivery_id_is_outside_zip_to_avoid_self_reference": True}
    write_json(EXP / "delivery_manifest.json", manifest)
    provenance["package"] = {"status": manifest["status"], "version": version, "internal_metadata_status": "ALL_AUTHORIZED_RUNS_COMPLETE_OR_EXACT_GATE_STOP", "delivery_manifest_path": "delivery_manifest.json", "package_qa": qa, "drive_file_id": None, "drive_url": None}
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
        raise RuntimeError("local delivery package missing or changed")
    if drive_sha256 is not None and drive_sha256 != local_sha:
        raise RuntimeError("Drive SHA-256 mismatch")
    if drive_bytes is not None and int(drive_bytes) != int(manifest["package_bytes"]):
        raise RuntimeError("Drive byte-size mismatch")
    manifest["status"] = "UPLOADED"
    manifest["drive_file_id"] = file_id
    manifest["drive_url"] = url
    manifest["uploaded_at"] = now()
    manifest["drive_verified_local_sha256"] = local_sha
    manifest["drive_verified_local_bytes"] = package_path.stat().st_size
    write_json(manifest_path, manifest)
    provenance = read_json(EXP / "provenance.json")
    provenance["package"]["status"] = "UPLOADED"
    provenance["package"]["drive_file_id"] = file_id
    provenance["package"]["drive_url"] = url
    provenance["package"]["drive_uploaded_at"] = manifest["uploaded_at"]
    provenance["package"]["delivery_manifest_sha256"] = sha256(manifest_path)
    provenance["package"]["drive_sha256_verified"] = drive_sha256 == local_sha if drive_sha256 is not None else "metadata SHA not supplied by connector"
    write_json(EXP / "provenance.json", provenance)
    result = read_json(EXP / "result.json")
    result["package_summary"]["status"] = "UPLOADED"
    result["package_summary"]["drive_file_id"] = file_id
    result["package_summary"]["drive_url"] = url
    result["package_summary"]["drive_verified_local_sha256"] = local_sha
    write_json(EXP / "result.json", result)
    (EXP / "RESULT.md").write_text(result_markdown(result), encoding="utf-8")
    print(json.dumps({"status": "UPLOADED", "drive_file_id": file_id, "drive_url": url, "package_sha256": local_sha, "package_bytes": package_path.stat().st_size}, ensure_ascii=False, indent=2))


def all_actions() -> None:
    prepare()
    execute_cases(EXACT_CASES)
    analyze()
    result = read_json(EXP / "result.json")
    if result.get("fidelity", {}).get("status") == "PASS":
        materialize_delayed()
        execute_cases(DELAY_CASES)
        analyze()
    mechanical_qa()
    visualization()
    package()


def main() -> int:
    command = sys.argv[1] if len(sys.argv) > 1 else "all"
    actions = {
        "prepare": prepare,
        "run-exact": lambda: execute_cases(EXACT_CASES),
        "analyze": analyze,
        "materialize-delayed": materialize_delayed,
        "run-delayed": lambda: execute_cases(DELAY_CASES),
        "qa": mechanical_qa,
        "viz": visualization,
        "package": package,
        "record-drive": lambda: record_drive(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None, sys.argv[4] if len(sys.argv) > 4 else None, int(sys.argv[5]) if len(sys.argv) > 5 else None),
        "all": all_actions,
    }
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
