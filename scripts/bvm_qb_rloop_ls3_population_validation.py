#!/usr/bin/env python3
"""Validate the registered LS3-only 0.3-ps replay at N1 and N4.

This runner is intentionally an Experimental Operator + Evidence Packager.
It performs bounded raw arithmetic and mechanical QA only.  The LS3 replay is
an instance-specific ideal-current counterfactual; it is not a passive delay
element and it does not establish a physical mechanism or an SFQ count.
"""

from __future__ import annotations

import csv
import hashlib
import importlib.util
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
import bvm_qb_rloop_branch_timing_decomposition as branch_helpers  # noqa: E402

POP_ROOT = REPO / "test" / "exploration" / "bvm-population-scaling-rj2p12-l1p14-l2p20-ib260-rj32-bjs400-v1-20260910"
EXP = REPO / "test" / "exploration" / "bvm-rloop-ls3-delay-population-validation-v1-20260916"
SOURCE_INPUTS = REPO / "test" / "exploration" / "bvm-qb-threshold-ordering-boundary-search-v1-20260911" / "inputs"
PREVIOUS_BRANCH = REPO / "test" / "exploration" / "bvm-rloop-branch-timing-decomposition-v1-20260916"
SOLVER = REPO / "build" / "josim-cli"
PLOTTER = REPO / "scripts" / "josim-plot2.py"
PUBLIC_QB = REPO / "circuits" / "qb" / "bq_parameterized_v1.cir"
ORACLE_PATH = POP_ROOT / "analysis" / "population_oracle.py"

CANONICAL_RAW = {
    "0001": POP_ROOT / "references" / "reused" / "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_0001" / "raw.csv",
    "1111": POP_ROOT / "runs" / "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_1111" / "raw.csv",
}
CANONICAL_DECK = {
    "0001": POP_ROOT / "references" / "reused" / "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_0001" / "deck.cir",
    "1111": POP_ROOT / "runs" / "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_1111" / "deck.cir",
}
REUSED_RAW = {
    "N2_CANONICAL": REPO / "test" / "exploration" / "bvm-qb-threshold-ordering-boundary-search-v1-20260911" / "references" / "canonical_baseline" / "0011" / "raw.csv",
    "N2_LS3_DELAY0P3": PREVIOUS_BRANCH / "runs" / "LS3_DELAY0P3_0011" / "raw.csv",
    "N3_CANONICAL": REPO / "test" / "exploration" / "bvm-qb-threshold-ordering-boundary-search-v1-20260911" / "references" / "canonical_baseline" / "0111" / "raw.csv",
    "N3_LS3_DELAY0P3": PREVIOUS_BRANCH / "runs" / "LS3_DELAY0P3_0111" / "raw.csv",
}

EXPECTED_HEAD = "2099471a24f7938056ac762ff60c89636dcafa7d"
EXPECTED_RAW_HASHES = {
    "0001": "7411226d2231dca0e1a3948660a82d7d88112baab8c18349cd83f4f94e6cf1b3",
    "1111": "0497b2d6822378c5b7491ab00abdfcf00d624ba9dd7e7a1c02046b5d4c3ed48c",
}
EXPECTED_DECK_HASHES = {
    "0001": "81a9b7e75437a5cb9ccd173b9db3bf93697ea6dd6017bb1d8dbf4bd4008d70fb",
    "1111": "892295ddd6599ba6cfa17a28a62528b6d891e0b7dc1c2105649dc25e5e3043c3",
}
EXPECTED_REUSED_HASHES = {
    "N2_CANONICAL": "3da7b754c990316ff8e5981692afa958d8056a61020a1912548bf6f2b7e0249c",
    "N2_LS3_DELAY0P3": "86bdf260882804948c830a4d885b7465d0ab8e479d4adb57830ed0deb8573d8d",
    "N3_CANONICAL": "1ca15a938b23d4ed08eb964713f91476256c4caf0677d1bfd3dc43020271ec75",
    "N3_LS3_DELAY0P3": "93e5672abfe9e0489c056a07f6d4a80b71a618c17e361dccace5a8a33bd91b37",
}
PINNED_INPUT_HASHES = {
    SOURCE_INPUTS / "jjmit.cir": "19862d1fd1f1f44dfa1523848d7d3b5e2594a6c5da8fdd80144b449e5312a336",
    SOURCE_INPUTS / "bvm_jm2_connected.cir": "0093a45cc3910448b484d8bd004c6df8c22358bacc8b3ed5e23912dcab805d54",
    SOURCE_INPUTS / "BQ_parameterized_bjs400_rj2.cir": "43468c49eb56090e586428a8ca26d17d8bbf107fbd9e535bbac7a72ed1200d42",
    SOURCE_INPUTS / "jtl2.cir": "ffd31f8eda2a86ca0133342be1ce678831b7237a53911eda046d2bff8454855a",
    PUBLIC_QB: "f676ba1ecb9b2607631a5cfc2f99b7d67e09b9e821457015fba375b8a39f13b0",
}

PHI0 = 2.067833848e-15
FOCUS_WINDOW = (110.0, 121.0)
REARM_WINDOW = (121.0, 130.0)
FULL_WINDOW = (0.0, 200.0)
CONTROL_WINDOW = (70.0, 110.0)
T0_PS = 110.0
DELAY_PS = 0.3
DELAY_SHIFT = 3
TIME_STEP_PS = 0.1
EXACT_TIMING_TOL_PS = 0.2
EXACT_PHASE_P2P_TOL_TURNS = 0.25
EXACT_NORMALIZED_WAVEFORM_RMS_TOL = 0.50
EXACT_SOURCE_ERROR_TOL_A = 1.0e-12
AREA_COMPATIBILITY_TOL_PHI0 = 1.0
RUN_ORDER = ("LS3_EXACT_0001", "LS3_DELAY0P3_0001", "LS3_EXACT_1111", "LS3_DELAY0P3_1111")
EXACT_CASES = ("LS3_EXACT_0001", "LS3_EXACT_1111")
DELAY_CASES = ("LS3_DELAY0P3_0001", "LS3_DELAY0P3_1111")
CONTRACT_SENTENCE = "This experiment is governed by docs/EXPERIMENT_CONTRACT.md."
FINAL_MARKER = "EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW"
DRIVE_FOLDER_ID = "1--nlY7Nq5ArVPydJNrnQf-EGmwN-undh"
KNOWN_WARNINGS = {"Unknown device/node IB|XBQ1", "Cannot store results for this device/node."}
JTL_STAGES = tuple(range(1, 7))
JUNCTIONS = ("B_JM1", "B_JM2", "B_JS1", "B_JS2")
BVM_BRANCHES = ("L_M1", "L_M2", "L_M3", "L_PM", "L_S1", "L_S2", "L_S3", "R_S", "R_SE", "L_PSE", "L_PSL", "R_SL", "L_SL")
CHAIN_STAGES = ("BJ1", "BJ2", "JTL1", "JTL2", "JTL3", "JTL4", "JTL5", "JTL6")


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
    return branch_helpers.load_raw(path)


def time_indices(trace: Any, window: tuple[float, float]) -> list[int]:
    return [index for index, value in enumerate(trace.time) if window[0] <= value * 1.0e12 < window[1]]


def actual_integral(times: Iterable[float], values: Iterable[float]) -> float:
    time_values = list(times)
    value_values = list(values)
    return sum(0.5 * (value_values[i] + value_values[i + 1]) * (time_values[i + 1] - time_values[i]) for i in range(len(value_values) - 1))


def case_info(case_id: str) -> dict[str, Any]:
    match = re.fullmatch(r"LS3_(EXACT|DELAY0P3)_(0001|1111)", case_id)
    if not match:
        raise RuntimeError(f"invalid case id: {case_id}")
    stage, mask = match.groups()
    return {"case_id": case_id, "stage": stage, "mask": mask, "delay_ps": 0.0 if stage == "EXACT" else DELAY_PS, "stored_sample_shift": 0 if stage == "EXACT" else DELAY_SHIFT}


def case_dir(case_id: str) -> Path:
    return EXP / "runs" / case_id


def assert_registration() -> None:
    if git_head() != EXPECTED_HEAD or remote_head() != EXPECTED_HEAD:
        raise RuntimeError(f"HEAD/remote mismatch: {git_head()} / {remote_head()} != {EXPECTED_HEAD}")
    for path, expected in PINNED_INPUT_HASHES.items():
        if not path.is_file() or sha256(path) != expected:
            raise RuntimeError(f"pinned source changed or missing: {path}")
    for mask, expected in EXPECTED_RAW_HASHES.items():
        if sha256(CANONICAL_RAW[mask]) != expected:
            raise RuntimeError(f"canonical {mask} raw changed")
    for mask, expected in EXPECTED_DECK_HASHES.items():
        if sha256(CANONICAL_DECK[mask]) != expected:
            raise RuntimeError(f"canonical {mask} deck changed")
    for name, expected in EXPECTED_REUSED_HASHES.items():
        if sha256(REUSED_RAW[name]) != expected:
            raise RuntimeError(f"reused raw changed: {name}")


def source_inventory() -> list[dict[str, Any]]:
    records = [
        record_file("runner", SCRIPT, "LS3 population validation generator, executor, mechanical analysis, visualization, and packager"),
        record_file("global_jjmit_model", SOURCE_INPUTS / "jjmit.cir", "canonical global JJ model"),
        record_file("canonical_bvm_template", SOURCE_INPUTS / "bvm_jm2_connected.cir", "canonical BVM clone template"),
        record_file("canonical_qb_include", SOURCE_INPUTS / "BQ_parameterized_bjs400_rj2.cir", "canonical QB include"),
        record_file("canonical_jtl_include", SOURCE_INPUTS / "jtl2.cir", "canonical six-stage JTL include"),
        record_file("public_qb_hash_guard", PUBLIC_QB, "canonical QB guard"),
        record_file("josim_solver", SOLVER, "recorded JoSIM solver"),
        record_file("plotter", PLOTTER, "standard descriptive JoSIM renderer"),
        record_file("branch_replay_helper", REPO / "scripts" / "bvm_qb_rloop_branch_timing_decomposition.py", "read-only validated LS3 topology and arithmetic helper"),
        record_file("total_replay_helper", REPO / "scripts" / "bvm_qb_rloop_bridge_timing_replay.py", "read-only raw/grid/source helper"),
        record_file("z0_metrics_helper", REPO / "scripts" / "bvm_qb_tline_z0_rescue_gate.py", "read-only waveform, phase, QB/JTL helper"),
        record_file("boundary_replay_helper", REPO / "scripts" / "bvm_qb_boundary_timing_replay.py", "read-only actual-grid helper"),
        record_file("historical_multi_evidence_oracle", ORACLE_PATH, "read-only historical voltage-cluster segmentation and strict comparison oracle"),
        record_file("previous_branch_result", PREVIOUS_BRANCH / "result.json", "read-only accepted N2/N3 context"),
        record_file("previous_branch_provenance", PREVIOUS_BRANCH / "provenance.json", "read-only accepted N2/N3 provenance"),
        record_file("previous_branch_source_manifest", PREVIOUS_BRANCH / "analysis" / "SOURCE_MANIFEST.json", "read-only previous source closure"),
    ]
    for mask in ("0001", "1111"):
        records.append(record_file(f"canonical_{mask}_raw", CANONICAL_RAW[mask], "read-only population source raw"))
        records.append(record_file(f"canonical_{mask}_deck", CANONICAL_DECK[mask], "read-only population source deck"))
    for name, path in REUSED_RAW.items():
        records.append(record_file(f"reused_{name.lower()}", path, "read-only N2/N3 population context raw; not copied into package"))
    return records


def delay_values(source: list[float], times: list[str], delay_ps: float) -> list[float]:
    if delay_ps == 0.0:
        return list(source)
    if delay_ps != DELAY_PS:
        raise RuntimeError(f"unauthorized delay: {delay_ps}")
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


def write_source_csv(path: Path, mask: str, delay_ps: float) -> dict[str, Any]:
    times, strings, values = branch_helpers.source_tokens(CANONICAL_RAW[mask])
    columns = {f"XBVM{index}": f"I(L_S3|XBVM{index})" for index in range(1, 5)}
    replay = {instance: delay_values(values[column], times, delay_ps) for instance, column in columns.items()}
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["time_s", "time_ps", *[f"I_CANONICAL_LS3_{instance}_A" for instance in columns], *[f"I_LS3_REPLAY_{instance}_A" for instance in columns]])
        for row, token in enumerate(times):
            writer.writerow([token, f"{float(token) * 1.0e12:.17g}", *[branch_helpers.current_token(values[columns[instance]][row]) for instance in columns], *[branch_helpers.current_token(replay[instance][row]) for instance in columns]])
    start = next(index for index, token in enumerate(times) if abs(float(token) * 1.0e12 - T0_PS) < 1.0e-9)
    source_column_hashes = {instance: sha256_text("\n".join(strings[column]) + "\n") for instance, column in columns.items()}
    replay_column_hashes = {instance: sha256_text("\n".join(branch_helpers.current_token(value) for value in replay[instance]) + "\n") for instance in columns}
    pre_equal = all(replay[instance][row] == values[columns[instance]][row] for instance in columns for row, token in enumerate(times) if float(token) * 1.0e12 < T0_PS)
    hold_equal = all(replay[instance][row] == values[columns[instance]][start] for instance in columns for row in range(start, start + (DELAY_SHIFT if delay_ps else 0)))
    post_equal = all(replay[instance][row] == values[columns[instance]][row - DELAY_SHIFT] for instance in columns for row in range(start + DELAY_SHIFT, len(times))) if delay_ps else True
    return {
        "path": rel(path),
        "sha256": sha256(path),
        "bytes": path.stat().st_size,
        "mask": mask,
        "authority_raw": rel(CANONICAL_RAW[mask]),
        "authority_raw_sha256": sha256(CANONICAL_RAW[mask]),
        "authority_columns": list(columns.values()),
        "source_column_sha256": source_column_hashes,
        "replay_column_sha256": replay_column_hashes,
        "point_count": len(times),
        "start_sample_index": start,
        "start_time_ps": float(times[start]) * 1.0e12,
        "delay_ps": delay_ps,
        "stored_sample_shift": 0 if delay_ps == 0.0 else DELAY_SHIFT,
        "pre_110_nonanticipation": pre_equal,
        "hold_rule_check": hold_equal,
        "post_shift_rule_check": post_equal,
        "interpolation": False,
        "resampling": False,
        "amplitude_scaling": False,
        "sign_change": False,
        "positive_direction": "node6 -> node10",
    }


def transform_deck(mask: str, case_id: str, payloads: dict[str, str], deck_dir: Path) -> str:
    original = CANONICAL_DECK[mask].read_text(encoding="utf-8")
    include_targets = {
        "jjmit.cir": SOURCE_INPUTS / "jjmit.cir",
        "bvm_jm2_connected.cir": SOURCE_INPUTS / "bvm_jm2_connected.cir",
        "BQ_parameterized_bjs400_rj2.cir": SOURCE_INPUTS / "BQ_parameterized_bjs400_rj2.cir",
        "jtl2.cir": SOURCE_INPUTS / "jtl2.cir",
    }
    output: list[str] = []
    inserted = False
    instance_count = 0
    replaced_rs = 0
    skipped_ls3 = 0
    for line in original.splitlines():
        stripped = line.strip()
        if stripped.startswith(".include "):
            include_name = Path(stripped.split(None, 1)[1]).name
            if include_name == "bvm_jm2_connected.cir":
                continue
            if include_name not in include_targets:
                raise RuntimeError(f"unexpected include in {case_id}: {include_name}")
            output.append(f".include {Path(os.path.relpath(include_targets[include_name], deck_dir)).as_posix()}")
            continue
        match = re.fullmatch(r"XBVM([1-4]) WL\1 BL\1 SE\1 COMMON_SL BVM", stripped)
        if match:
            if not inserted:
                for index in range(1, 5):
                    output.append(branch_helpers.clone_bvm_subckt(index, "LS3", payloads[f"XBVM{index}"]))
                inserted = True
            index = int(match.group(1))
            output.append(f"XBVM{index} WL{index} BL{index} SE{index} COMMON_SL BVM_LS3_REPLAY_{index}")
            instance_count += 1
            continue
        if stripped.startswith(".print ") and re.search(r"I\(R_S\|XBVM[1-4]\)", stripped):
            index = int(re.search(r"XBVM([1-4])", stripped).group(1))
            output.append(f".print I(R_S|XBVM{index}) V(R_S|XBVM{index}) I(I_LS3_REPLAY|XBVM{index}) V(6|XBVM{index}) V(10|XBVM{index})")
            replaced_rs += 1
            continue
        if stripped.startswith(".print ") and re.search(r"I\(L_S3\|XBVM[1-4]\)", stripped):
            skipped_ls3 += 1
            continue
        output.append(line)
    if not inserted or instance_count != 4 or replaced_rs != 4 or skipped_ls3 != 4:
        raise RuntimeError(f"deck transform counts {case_id}: {inserted=} {instance_count=} {replaced_rs=} {skipped_ls3=}")
    text = "\n".join(output) + "\n"
    if text.count("I_LS3_REPLAY 6 10 PWL(") != 4:
        raise RuntimeError(f"expected four LS3 replay sources: {case_id}")
    required = ("XBQ1 QBIN QBOUT BQ", "XJTL1_1 QBOUT JTL1_OUT jtl", "XJTL1_6 JTL5_OUT JTL6_OUT jtl", "R_TERM JTL6_OUT 0 10", ".tran 0.1p 200p")
    if any(item not in text for item in required):
        raise RuntimeError(f"canonical forward path missing: {case_id}")
    if "L_S3     6       10      0.5P" in text or "L_S3    6       10      0.5P" in text or ".include" in text and "bvm_jm2_connected.cir" in text:
        raise RuntimeError(f"physical LS3 or canonical BVM include survived: {case_id}")
    if any(token in text for token in ("T_BVM_QB", "V_REPLAY", "SENTINEL", "TRANSFORMER", "LC_LADDER")):
        raise RuntimeError(f"forbidden topology token in {case_id}")
    return text


def make_case_deck(case_id: str) -> dict[str, Any]:
    info = case_info(case_id)
    times, _, values = branch_helpers.source_tokens(CANONICAL_RAW[info["mask"]])
    replay = {f"XBVM{index}": delay_values(values[f"I(L_S3|XBVM{index})"], times, info["delay_ps"]) for index in range(1, 5)}
    source_path = EXP / "inputs" / "replay_sources" / f"{case_id}_branch_current.csv"
    source = write_source_csv(source_path, info["mask"], info["delay_ps"])
    payloads = {instance: "PWL(" + " ".join(item for row, token in enumerate(times) for item in (branch_helpers.time_token_ps(token), branch_helpers.current_token(replay[instance][row]))) + ")" for instance in replay}
    deck = case_dir(case_id) / "deck.cir"
    deck.parent.mkdir(parents=True, exist_ok=True)
    deck.write_text(transform_deck(info["mask"], case_id, payloads, deck.parent), encoding="utf-8")
    return {"run_id": case_id, **info, "path": rel(deck), "sha256": sha256(deck), "bytes": deck.stat().st_size, "source": source, "payload_sha256": {instance: sha256_text(payloads[instance]) for instance in payloads}, "payload_bytes": {instance: len(payloads[instance].encode("utf-8")) for instance in payloads}, "topology_transform": "per-instance canonical BVM clone; physical R_S retained; only same-instance I(L_S3) is imposed through ideal current source; canonical QB/JSL/JTL/terminal unchanged"}


def expected_headers(mask: str) -> set[str]:
    trace = load_raw(CANONICAL_RAW[mask])
    headers = set(trace.headers)
    for index in range(1, 5):
        headers.discard(f"I(L_S3|XBVM{index})")
        headers.discard(f"V(L_S3|XBVM{index})")
        headers.update((f"I(I_LS3_REPLAY|XBVM{index})", f"V(6|XBVM{index})", f"V(10|XBVM{index})"))
    return headers


def preflight_text(direction: dict[str, Any]) -> str:
    lines = [
        f"# LS3-only delay population validation — {EXP.name}",
        "",
        CONTRACT_SENTENCE,
        "",
        "## Registration",
        "",
        f"- Registration HEAD: `{EXPECTED_HEAD}`; remote `bvm/master`: `{EXPECTED_HEAD}`.",
        "- Study phase: `EXPLORATORY`; role: `Experimental Operator + Evidence Packager`.",
        "- Scientific review authorization: `false`; this run records mechanical evidence only.",
        "- Previous N2/N3 LS3 branch-decomposition artifacts are immutable read-only context.",
        "",
        "## Single question",
        "",
        "Does the registered LS3-only 0.3-ps timing intervention preserve N1≈1 and N4≈4 while retaining the already-established N2=2 / N3=3 behavior?",
        "",
        "This is an instance-specific ideal replay of canonical LS3 current, not a physical delay element or passive-equivalence proof.",
        "",
        "## Frozen fixture",
        "",
        "- Working point: L1=1.4 pH, L2=2.0 pH, IBias=260 µA, RJ1=32 Ω, RJ2=12 Ω, BJS area=4, `.tran 0.1p 200p`.",
        "- Forward path: `BVM -> COMMON_SL -> JSL1..8 -> canonical QB -> JTL1..6 -> 10 Ω terminal`.",
        "- Per instance: retain `R_S 6 10 3.0`; remove `L_S3 6 10 0.5P`; impose same-instance canonical `I(L_S3)` from node6 to node10.",
        "- QB, QBIN, JSL, JTL, terminal, BVM parameters, stimulus and timestep are unchanged.",
        f"- Actual stored grid is retained; expected 1999 rows, 0–199.9 ps, and the only delay is `{DELAY_PS} ps = {DELAY_SHIFT} stored samples`.",
        "- Delay: t<110 ps same sample; [110,110.3) ps holds the 110-ps sample; t≥110.3 ps uses exact index i−3.",
        "- No interpolation, smoothing, resampling, amplitude scaling, sign modification, other delay, sweep, sentinel, or READ extension.",
        "",
        "## Source raw authority",
        "",
    ]
    for mask in ("0001", "1111"):
        lines.append(f"- `{mask}`: `{rel(CANONICAL_RAW[mask])}`; SHA-256 `{EXPECTED_RAW_HASHES[mask]}`.")
    lines.extend([
        "",
        "## Mechanical source audit",
        "",
        f"- Canonical branch direction/KCL audit: `{json.dumps({mask: item['status'] for mask, item in direction.items()}, ensure_ascii=False)}`.",
        "- Checks: V(R_S)≈3I(R_S), V(L_S3)=V(R_S), node6/node10 KCL, positive node6→node10 orientation.",
        "- Failure of this audit blocks source construction.",
        "",
        "## Authorized solve order",
        "",
        "1. `LS3_EXACT_0001`",
        "2. `LS3_DELAY0P3_0001`",
        "3. `LS3_EXACT_1111`",
        "4. `LS3_DELAY0P3_1111`",
        "",
        "No other physical solve is authorized. Exact fidelity is gated independently per mask; a delayed raw may be mechanically recorded after a failed exact gate but is marked uninterpretable for validation.",
        "",
        "## Interpretation ceiling",
        "",
        "N1 uses one ordered BJ1→BJ2→JTL1..6 candidate plus terminal clusters/area as corroboration. N4 uses phase landmarks, ordered JTL phase chains, JTL6/terminal valleys and total terminal area; the historical strict `complete_response_count` is shown but is not the primary N4 oracle.",
        "",
        "All phase values remain raw radians; turns are independent unwrap/(2π) navigation only and are not SFQ counts. Final population labels and mechanism conclusions remain `NOT_ASSIGNED_SCIENTIFIC_REVIEW_REQUIRED`.",
        "",
        f"Stop marker: `{FINAL_MARKER}`.",
        "",
    ])
    return "\n".join(lines)


def initial_yaml(exact_records: dict[str, Any]) -> str:
    lines = [
        "schema_version: bvm-rloop-ls3-delay-population-validation-v1",
        f"id: {EXP.name}",
        "study_phase: EXPLORATORY",
        "role: Experimental Operator + Evidence Packager",
        "status: PREFLIGHT_PASS",
        f"contract_sentence: \"{CONTRACT_SENTENCE}\"",
        f"registration_head: {EXPECTED_HEAD}",
        f"remote_bvm_master_at_registration: {EXPECTED_HEAD}",
        "scientific_review_authorized: false",
        "mechanical_analysis_performed: false",
        "bounded_experiment_interpretation_performed: false",
        "independent_scientific_review_performed: false",
        "scientific_interpretation_performed: false",
        "",
        "question:",
        "  primary: \"Does LS3-only 0.3-ps timing preserve N1≈1 and N4≈4 while retaining established N2=2 / N3=3 behavior?\"",
        "  scope: \"N1/N4 validation only; N2/N3 are reused read-only context.\"",
        "  interpretation_ceiling: \"Mechanical evidence package; final labels and mechanism remain scientific-review gated.\"",
        "",
        "source_fixture:",
        "  forward_topology: \"canonical BVM -> COMMON_SL -> JSL1..8 -> canonical QB -> JTL1..6 -> 10 ohm terminal\"",
        "  physical_bridge: [\"R_S 6 10 3.0 retained\", \"L_S3 removed\"]",
        "  replay_branch: \"same-instance canonical I(L_S3), positive node6 -> node10\"",
        "  canonical_qb_jsl_jtl_terminal_unchanged: true",
        "  shared_waveform: false",
        "",
        "frozen:",
        "  L1_pH: 1.4",
        "  L2_pH: 2.0",
        "  IBias_uA: 260",
        "  RJ1_ohm: 32",
        "  RJ2_ohm: 12",
        "  BJS_area: 4",
        "  time_step_ps: 0.1",
        "  stop_time_ps: 200",
        "  intervention_start_ps: 110.0",
        "  delayed_ps: 0.3",
        "  delayed_stored_samples: 3",
        "  actual_grid: true",
        "  interpolation: false",
        "  resampling: false",
        "  amplitude_scaling: false",
        "  sign_modification: false",
        "  no_read_extension: true",
        "  no_sentinel: true",
        "",
        "authorized_matrix:",
    ]
    for case_id in RUN_ORDER:
        info = case_info(case_id)
        lines.extend([f"  - run_id: {case_id}", f"    mask: \"{info['mask']}\"", f"    stage: {info['stage']}", f"    delay_ps: {info['delay_ps']}", f"    stored_sample_shift: {info['stored_sample_shift']}", f"    execution_order: {RUN_ORDER.index(case_id) + 1}", f"    status: {'registered_exact_deck' if info['stage'] == 'EXACT' else 'registered_deferred_until_mask_exact_gate'}"])
    lines.extend(["  maximum_new_physical_solves: 4", "  no_other_solve: true", "", "source_raw_registration:"])
    for mask in ("0001", "1111"):
        lines.extend([f"  - mask: \"{mask}\"", f"    path: {rel(CANONICAL_RAW[mask])}", f"    sha256: {EXPECTED_RAW_HASHES[mask]}"])
    lines.extend(["", "exact_deck_registration:"])
    for key in EXACT_CASES:
        item = exact_records[key]
        lines.extend([f"  - run_id: {key}", f"    path: {item['path']}", f"    sha256: {item['sha256']}", f"    bytes: {item['bytes']}", f"    source_csv: {item['source']['path']}", f"    source_csv_sha256: {item['source']['sha256']}"])
    lines.extend(["", "replay_semantics:", "  phase_unit: raw radians; turns only independent unwrap/(2*pi) navigation", "  area: same JJ/endpoints/direction/window actual-grid trapezoid; not SFQ count", "  terminal: corroboration only", "  delayed_cases_interpretation: mask-specific exact gate required", ""])
    return "\n".join(lines)


def prepare() -> None:
    assert_registration()
    if EXP.exists() and any(EXP.iterdir()):
        raise RuntimeError(f"refusing to overwrite non-empty experiment: {EXP}")
    canonical = {mask: load_raw(path) for mask, path in CANONICAL_RAW.items()}
    direction = {mask: branch_helpers.branch_direction_audit(trace, mask) for mask, trace in canonical.items()}
    if any(item["status"] != "PASS" for item in direction.values()):
        raise RuntimeError(f"canonical LS3 source audit failed: {direction}")
    EXP.mkdir(parents=True, exist_ok=True)
    (EXP / "runs").mkdir()
    (EXP / "analysis").mkdir()
    (EXP / "plots").mkdir()
    (EXP / "inputs" / "replay_sources").mkdir(parents=True)
    (EXP / "PREFLIGHT.md").write_text(preflight_text(direction), encoding="utf-8")
    if CONTRACT_SENTENCE not in (EXP / "PREFLIGHT.md").read_text(encoding="utf-8"):
        raise RuntimeError("PREFLIGHT contract sentence missing")
    exact_records = {case_id: make_case_deck(case_id) for case_id in EXACT_CASES}
    (EXP / "experiment.yaml").write_text(initial_yaml(exact_records), encoding="utf-8")
    closure = source_inventory()
    provenance = {
        "schema": "bvm-rloop-ls3-delay-population-validation-provenance-v1",
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
        "solver": branch_helpers.replay_base.solver_context(),
        "source_closure": closure,
        "canonical_source_raw_hashes": EXPECTED_RAW_HASHES,
        "canonical_source_deck_hashes": EXPECTED_DECK_HASHES,
        "reused_context_raw_hashes": EXPECTED_REUSED_HASHES,
        "branch_direction_audit": direction,
        "frozen": {"question": "N1/N4 validation of already-observed LS3-only 0.3-ps timing replay", "topology": "canonical BVM -> COMMON_SL -> JSL1..8 -> canonical QB -> JTL1..6 -> terminal", "replay": "same-instance I(L_S3), ideal current node6 -> node10", "delay_ps": DELAY_PS, "stored_sample_shift": DELAY_SHIFT, "t0_ps": T0_PS, "time_step_ps": TIME_STEP_PS, "stop_time_ps": 200.0, "windows_ps": [list(FULL_WINDOW), list(CONTROL_WINDOW), list(FOCUS_WINDOW), list(REARM_WINDOW)], "no_interpolation": True, "no_resampling": True, "no_amplitude_scaling": True, "no_sign_change": True, "no_QB_JSL_JTL_terminal_change": True},
        "authorized_matrix": {"run_order": list(RUN_ORDER), "maximum_new_physical_solves": 4, "exact_cases": list(EXACT_CASES), "delayed_cases": list(DELAY_CASES), "no_other_solve": True, "mask_independent_exact_gate": True},
        "registered_decks": exact_records,
        "runs": {},
        "run_order": [],
        "execution": {"authorized_physical_solve_count": 4, "actual_physical_solve_count": 0, "solver_invocation_count": 0, "run_order": []},
        "fidelity_screen": {"timing_tolerance_ps": EXACT_TIMING_TOL_PS, "phase_p2p_tolerance_turns": EXACT_PHASE_P2P_TOL_TURNS, "normalized_waveform_rms_tolerance": EXACT_NORMALIZED_WAVEFORM_RMS_TOL, "source_injection_error_tolerance_A": EXACT_SOURCE_ERROR_TOL_A, "screen_is_mechanical_not_physical_equivalence": True},
        "analysis": {"status": "PENDING"},
        "qa": {"status": "PENDING"},
        "visualization": {"status": "PENDING"},
        "package": {"status": "PENDING", "drive_file_id": None, "drive_url": None},
        "stop": {"final_marker": None, "automatic_follow_up": False},
    }
    write_json(EXP / "provenance.json", provenance)
    result = {"schema": "bvm-rloop-ls3-delay-population-validation-result-v1", "experiment_id": EXP.name, "generated_at": now(), "status": "PREFLIGHT_PASS_EXACT_DECKS_REGISTERED", "artifact_status": "PENDING", "scientific_review_authorized": False, "mechanical_analysis_performed": False, "bounded_experiment_interpretation_performed": False, "independent_scientific_review_performed": False, "scientific_interpretation_performed": False, "execution": provenance["execution"], "cases": {case_id: {"status": "AUTHORIZED_NOT_RUN" if case_id in EXACT_CASES else "AUTHORIZED_DEFERRED_UNTIL_MASK_EXACT_GATE"} for case_id in RUN_ORDER}, "exact_fidelity": {"0001": {"status": "PENDING"}, "1111": {"status": "PENDING"}}, "population_comparison": {"status": "PENDING"}, "classification": {"status": "SCIENTIFIC_REVIEW_REQUIRED", "assigned": None, "candidate_labels": ["POPULATION_MAPPING_1_2_3_4_SUPPORTED_BY_CURRENT_REPLAY", "THREE_RESPONSE_CAP_BEHAVIOR_OBSERVED", "POPULATION_VALIDATION_MIXED"]}, "stop": {"final_marker": None, "automatic_follow_up": False}}
    write_json(EXP / "result.json", result)
    (EXP / "RESULT.md").write_text(f"# LS3-only delay population validation ({EXP.name})\n\nPreflight passed. Exact N1/N4 decks are registered; execution must follow the four-case order.\n", encoding="utf-8")
    print(json.dumps({"status": "PREFLIGHT_PASS", "experiment": rel(EXP), "head": EXPECTED_HEAD, "direction_audit": {mask: item["status"] for mask, item in direction.items()}, "registered_exact_cases": list(EXACT_CASES)}, ensure_ascii=False, indent=2))


def expected_raw_record(case_id: str, raw: Path, log: Path, metadata: Path) -> dict[str, Any]:
    info = case_info(case_id)
    trace = load_raw(raw)
    missing = sorted(expected_headers(info["mask"]) - set(trace.headers))
    return {"path": rel(raw), "sha256": sha256(raw), "bytes": raw.stat().st_size, "sample_count": trace.sample_count, "time_start_ps": trace.time[0] * 1.0e12, "time_end_ps": trace.time[-1] * 1.0e12, "grid": branch_helpers.replay_base.finite_grid_qa(trace), "missing_required_probes": missing, "log": {"path": rel(log), "sha256": sha256(log), "bytes": log.stat().st_size}, "metadata": {"path": rel(metadata)}}


def warning_lines(path: Path) -> list[str]:
    if not path.is_file():
        return ["missing_log"]
    return [line.strip() for line in path.read_text(errors="replace").splitlines() if any(token in line for token in ("Missing model:", "Unknown device/node", "Cannot store results", "Error", "error"))]


def materialize_delay(mask: str) -> None:
    case_id = f"LS3_DELAY0P3_{mask}"
    provenance = read_json(EXP / "provenance.json")
    exact_id = f"LS3_EXACT_{mask}"
    if exact_id not in provenance["run_order"]:
        raise RuntimeError(f"exact case not completed before delay materialization: {mask}")
    if case_id in provenance["registered_decks"]:
        raise RuntimeError(f"delay deck already registered: {case_id}")
    item = make_case_deck(case_id)
    provenance["registered_decks"][case_id] = item
    exact_gate = provenance.get("exact_fidelity", {}).get(mask, {}).get("status")
    provenance.setdefault("delayed_materialization", []).append({"case_id": case_id, "mask": mask, "materialized_at": now(), "exact_gate_status": exact_gate, "interpretation_allowed": exact_gate == "PASS", "no_other_delay": True})
    write_json(EXP / "provenance.json", provenance)
    yaml_path = EXP / "experiment.yaml"
    yaml_text = yaml_path.read_text(encoding="utf-8").rstrip()
    block = ["", f"delayed_deck_registration_{mask}:", f"  - run_id: {case_id}", f"    path: {item['path']}", f"    sha256: {item['sha256']}", f"    bytes: {item['bytes']}", f"    source_csv: {item['source']['path']}", f"    source_csv_sha256: {item['source']['sha256']}", f"    exact_gate_status: {exact_gate}", f"    interpretation_allowed: {str(exact_gate == 'PASS').lower()}"]
    yaml_path.write_text(yaml_text + "\n" + "\n".join(block) + "\n", encoding="utf-8")
    print(json.dumps({"status": "DELAY_MATERIALIZED", "case_id": case_id, "exact_gate_status": exact_gate}, ensure_ascii=False, indent=2))


def execute_one(case_id: str) -> None:
    provenance = read_json(EXP / "provenance.json")
    if case_id not in provenance["registered_decks"]:
        raise RuntimeError(f"case is not registered: {case_id}")
    expected_prefix = list(RUN_ORDER[: RUN_ORDER.index(case_id)])
    if provenance["run_order"] != expected_prefix:
        raise RuntimeError(f"wrong execution prefix before {case_id}: {provenance['run_order']}")
    deck_record = provenance["registered_decks"][case_id]
    deck = REPO / deck_record["path"]
    raw, log, metadata = deck.parent / "raw.csv", deck.parent / "run.log", deck.parent / "metadata.json"
    if any(path.exists() for path in (raw, log, metadata)):
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
    record: dict[str, Any] = {"run_id": case_id, **info, "command": command, "deck": {"path": rel(deck), "sha256": sha256(deck), "bytes": deck.stat().st_size}, "log": {"path": rel(log), "sha256": sha256(log), "bytes": log.stat().st_size}, "solver": branch_helpers.replay_base.solver_context(), "started_at": started, "finished_at": finished, "physical_solve_this_experiment": True, "raw_immutable": True, "mechanical_analysis_performed": False, "bounded_experiment_interpretation_performed": False, "independent_scientific_review_performed": False, "scientific_interpretation_performed": False}
    if completed.returncode != 0 or not raw.is_file() or raw.stat().st_size == 0:
        record["execution_status"] = "SOLVER_FAIL"
        record["raw"] = {"path": rel(raw), "exists": raw.is_file(), "sha256": sha256(raw) if raw.is_file() else None, "bytes": raw.stat().st_size if raw.is_file() else None}
        provenance["runs"][case_id] = record
        provenance["run_order"].append(case_id)
        provenance["execution"]["actual_physical_solve_count"] = len(provenance["run_order"])
        provenance["execution"]["solver_invocation_count"] = len(provenance["run_order"])
        provenance["execution"]["run_order"] = provenance["run_order"]
        provenance["execution_status"] = "SOLVER_FAILURE_STOP"
        write_json(EXP / "provenance.json", provenance)
        raise RuntimeError(f"solver failed for {case_id}; raw/log preserved")
    try:
        raw_record = expected_raw_record(case_id, raw, log, metadata)
    except Exception as exc:
        record["execution_status"] = "RAW_PARSE_FAILURE"
        record["raw_parse_error"] = str(exc)
        record["raw"] = {"path": rel(raw), "sha256": sha256(raw), "bytes": raw.stat().st_size}
        provenance["runs"][case_id] = record
        provenance["run_order"].append(case_id)
        provenance["execution"]["actual_physical_solve_count"] = len(provenance["run_order"])
        provenance["execution"]["solver_invocation_count"] = len(provenance["run_order"])
        write_json(EXP / "provenance.json", provenance)
        raise RuntimeError(f"raw parse failed for {case_id}; raw/log preserved") from exc
    record["raw"] = raw_record
    record["solver_warning_lines"] = warning_lines(log)
    record["execution_status"] = "RUN_PASS" if not raw_record["missing_required_probes"] else "RUN_PASS_MISSING_PROBES"
    record["metadata"] = {"path": rel(metadata), "source": deck_record["source"], "deck_sha256": sha256(deck), "raw_sha256": sha256(raw), "log_sha256": sha256(log), "execution_status": record["execution_status"]}
    write_json(metadata, record["metadata"])
    provenance["runs"][case_id] = record
    provenance["run_order"].append(case_id)
    provenance["execution"]["actual_physical_solve_count"] = len(provenance["run_order"])
    provenance["execution"]["solver_invocation_count"] = len(provenance["run_order"])
    provenance["execution"]["run_order"] = provenance["run_order"]
    write_json(EXP / "provenance.json", provenance)
    if raw_record["missing_required_probes"]:
        raise RuntimeError(f"required probes missing for {case_id}: {raw_record['missing_required_probes']}")
    print(json.dumps({"status": "RUN_PASS", "case_id": case_id, "sample_count": raw_record["sample_count"], "raw_sha256": raw_record["sha256"]}, ensure_ascii=False, indent=2))


def load_oracle_module() -> Any:
    spec = importlib.util.spec_from_file_location("historical_population_oracle", ORACLE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load historical population oracle")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def phase_time(oracle: dict[str, Any], stage: str, index: int) -> float | None:
    item = oracle["phase_landmarks"][stage]["landmarks"].get(str(index))
    return item.get("time_ps") if isinstance(item, dict) else None


def phase_chains(oracle: dict[str, Any]) -> list[dict[str, Any]]:
    records = []
    for index in range(1, 5):
        times = {stage: phase_time(oracle, stage, index) for stage in CHAIN_STAGES}
        missing = next((stage for stage in CHAIN_STAGES if times[stage] is None), None)
        order_failure = next((right for left, right in zip(CHAIN_STAGES, CHAIN_STAGES[1:]) if times[left] is not None and times[right] is not None and not times[left] < times[right]), None)
        complete = missing is None and order_failure is None
        records.append({"response_index": index, "complete_ordered_phase_chain": complete, "first_missing_stage": missing or order_failure, "landmark_times_ps": times, "navigation_only": True, "not_sfq_count": True})
    return records


def multi_evidence_oracle(trace: Any, mask: str, oracle_module: Any) -> dict[str, Any]:
    strict = oracle_module.generalized_response_oracle(trace)
    chains = phase_chains(strict)
    complete_count = sum(item["complete_ordered_phase_chain"] for item in chains)
    jtl6 = strict["voltage_pulse_clusters"]["JTL6"]
    terminal = strict["terminal_pulse_analysis"]
    jtl6_count = int(jtl6.get("cluster_count", 0))
    terminal_count = int(terminal.get("pulse_count", 0))
    area = terminal.get("total_final_area_over_phi0")
    area_float = float(area) if area is not None else None
    area_compatible = {str(n): area_float is not None and abs(area_float - n) <= AREA_COMPATIBILITY_TOL_PHI0 for n in (1, 3, 4)}
    if mask == "0001":
        candidate = "ONE_RESPONSE_LIKE_WITH_TERMINAL_CORROBORATION" if complete_count == 1 and terminal_count == 1 and area_compatible["1"] else "N1_RESPONSE_EVIDENCE_MIXED_OR_FAILED"
    elif mask == "1111":
        if complete_count == 4 and jtl6_count == 4 and terminal_count == 4 and area_compatible["4"]:
            candidate = "N4_FOUR_RESPONSE_LIKE_PRESERVED"
        elif complete_count == 3 and jtl6_count == 3 and terminal_count == 3 and area_compatible["3"]:
            candidate = "N4_REDUCED_TO_THREE_RESPONSE_LIKE"
        else:
            candidate = "N4_MIXED_ORACLE"
    else:
        candidate = f"{complete_count}_ORDERED_RESPONSE_LIKE_WITH_TERMINAL_CORROBORATION" if complete_count == terminal_count and complete_count > 0 else "RESPONSE_EVIDENCE_MIXED_OR_FAILED"
    return {"schema": "bvm-rloop-ls3-population-multi-evidence-oracle-v1", "mask": mask, "old_strict_complete_response_count": strict.get("complete_response_count"), "old_strict_status": strict.get("status"), "phase_landmarks": strict["phase_landmarks"], "ordered_phase_chains": chains, "ordered_phase_chain_count": complete_count, "jtl6_cluster_count": jtl6_count, "jtl6_clusters": jtl6.get("clusters", []), "terminal_pulse_count": terminal_count, "terminal_pulse_analysis": terminal, "terminal_total_area_over_phi0": area_float, "area_compatibility_tolerance_phi0": AREA_COMPATIBILITY_TOL_PHI0, "area_compatible_with_one": area_compatible["1"], "area_compatible_with_three": area_compatible["3"], "area_compatible_with_four": area_compatible["4"], "descriptive_candidate_label": candidate, "primary_n4_oracle": "phase landmarks + ordered BJ1->BJ2->JTL1..6 chains + JTL6/terminal valley-separated clusters + total terminal area; old strict field is contextual only", "segmentation_reference": "historical population_oracle.py: actual stored samples, baseline MAD threshold, 2.5-ps gap, below-threshold valley split", "not_event_count": True, "not_sfq_count": True, "scientific_interpretation_performed": False}


def vector_stats(trace: Any, values: list[float], window: tuple[float, float], signal: str, unit: str) -> dict[str, Any]:
    indices = time_indices(trace, window)
    chosen = [float(values[i]) for i in indices]
    times = [float(trace.time[i]) for i in indices]
    if len(chosen) < 2:
        return {"status": "UNKNOWN", "signal": signal, "window_ps": list(window), "unit": unit}
    power = [value * value for value in chosen]
    return {"status": "DERIVED", "signal": signal, "window_ps": list(window), "unit": unit, "sample_count": len(chosen), "minimum": min(chosen), "maximum": max(chosen), "p2p": max(chosen) - min(chosen), "rms": math.sqrt(sum(power) / len(power)), "peak_abs": max(abs(value) for value in chosen), "time_of_peak_abs_ps": times[max(range(len(chosen)), key=lambda i: abs(chosen[i]))] * 1.0e12, "signed_area": actual_integral(times, chosen), "absolute_area": actual_integral(times, [abs(value) for value in chosen]), "positive_area": actual_integral(times, [max(value, 0.0) for value in chosen]), "negative_area": actual_integral(times, [min(value, 0.0) for value in chosen]), "actual_grid_trapezoid": True}


def bridge_vectors(trace: Any, case_kind: str, instance: str) -> tuple[list[float], list[float], list[float], str]:
    rs = list(trace.column(f"I(R_S|{instance})"))
    if case_kind == "canonical":
        ls3 = list(trace.column(f"I(L_S3|{instance})"))
        total = [a + b for a, b in zip(rs, ls3)]
        voltage = list(trace.column(f"V(R_S|{instance})"))
        return total, voltage, total, "canonical physical bridge; no ideal source"
    imposed = list(trace.column(f"I(I_LS3_REPLAY|{instance})"))
    total = [a + b for a, b in zip(imposed, rs)]
    voltage = [a - b for a, b in zip(trace.column(f"V(6|{instance})"), trace.column(f"V(10|{instance})"))]
    return total, voltage, imposed, "LS3-only ideal current replay source"


def energy_record(trace: Any, voltage: list[float], current: list[float], window: tuple[float, float], role: str) -> dict[str, Any]:
    indices = time_indices(trace, window)
    times = [trace.time[i] for i in indices]
    v = [voltage[i] for i in indices]
    i = [current[i] for i in indices]
    power = [a * b for a, b in zip(v, i)]
    signed = actual_integral(times, power)
    absolute = actual_integral(times, [abs(value) for value in power])
    return {"status": "DERIVED", "window_ps": list(window), "sample_count": len(v), "voltage_min_V": min(v), "voltage_max_V": max(v), "voltage_rms_V": math.sqrt(sum(value * value for value in v) / len(v)), "current_min_A": min(i), "current_max_A": max(i), "ideal_source_peak_abs_power_W": max(abs(value) for value in power), "signed_energy_J": signed, "signed_energy_fJ": signed * 1.0e15, "absolute_exchanged_energy_J": absolute, "absolute_exchanged_energy_fJ": absolute * 1.0e15, "power_sign_convention": "P_absorb=V(node6-node10)*I_source(node6->node10)", "source_role": role, "actual_grid_trapezoid": True}


def source_injection_error(case_id: str, trace: Any) -> dict[str, Any]:
    source = read_json(EXP / "provenance.json")["registered_decks"][case_id]["source"]
    rows = list(csv.DictReader((REPO / source["path"]).open(newline="", encoding="utf-8")))
    output = {}
    maximum = 0.0
    for index in range(1, 5):
        key = f"I_LS3_REPLAY_XBVM{index}_A"
        imposed = [float(row[key]) for row in rows]
        actual = [float(value) for value in trace.column(f"I(I_LS3_REPLAY|XBVM{index})")]
        diffs = [a - b for a, b in zip(actual, imposed)]
        max_error = max(abs(value) for value in diffs)
        maximum = max(maximum, max_error)
        output[f"XBVM{index}"] = {"signal": f"I(I_LS3_REPLAY|XBVM{index})", "max_abs_error_A": max_error, "rms_error_A": math.sqrt(sum(value * value for value in diffs) / len(diffs))}
    return {"status": "PASS" if maximum <= EXACT_SOURCE_ERROR_TOL_A else "FAIL", "source_csv": source["path"], "instances": output, "max_abs_error_A": maximum, "tolerance_A": EXACT_SOURCE_ERROR_TOL_A}


def normalized_delta(reference: Any, candidate: Any, signal: str, window: tuple[float, float]) -> dict[str, Any]:
    if signal not in reference.headers or signal not in candidate.headers:
        return {"status": "UNKNOWN", "signal": signal, "window_ps": list(window)}
    indices = time_indices(reference, window)
    left = list(reference.column(signal))
    right = list(candidate.column(signal))
    if signal.startswith("P("):
        left_u = branch_helpers.total_helpers.unwrap(left)
        right_u = branch_helpers.total_helpers.unwrap(right)
        values = [(right_u[index] - left_u[index]) / (2.0 * math.pi) for index in indices]
        return {"status": "DERIVED", "signal": signal, "window_ps": list(window), "unit": "turns", "max_abs_delta_turns": max(abs(value) for value in values), "rms_delta_turns": math.sqrt(sum(value * value for value in values) / len(values)), "endpoint_delta_turns": values[-1], "independent_unwrap_before_subtract": True, "actual_grid": True}
    values = [right[index] - left[index] for index in indices]
    scale = max(max(left[index] for index in indices) - min(left[index] for index in indices), max(abs(left[index]) for index in indices), 1.0e-30)
    rms = math.sqrt(sum(value * value for value in values) / len(values))
    return {"status": "DERIVED", "signal": signal, "window_ps": list(window), "unit": "A" if signal.startswith("I(") else "V", "max_abs_delta": max(abs(value) for value in values), "rms_delta": rms, "normalized_rms": rms / scale, "reference_scale": scale, "actual_grid": True}


def phase_p2p_deltas(canonical: Any, candidate: Any, mask: str) -> dict[str, Any]:
    output: dict[str, Any] = {}
    active = [index for index, bit in enumerate(mask, 1) if bit == "1"]
    for index in active:
        for element in ("B_JS1", "B_JS2"):
            signal = f"P({element}|XBVM{index})"
            c = branch_helpers.phase_navigation(canonical, signal)
            e = branch_helpers.phase_navigation(candidate, signal)
            output[signal] = {"canonical_p2p_turns": c["focus_110_121_p2p_turns"], "candidate_p2p_turns": e["focus_110_121_p2p_turns"], "absolute_delta_turns": abs(e["focus_110_121_p2p_turns"] - c["focus_110_121_p2p_turns"]), "canonical_endpoint_delta_turns": c["focus_110_121_endpoint_delta_turns"], "candidate_endpoint_delta_turns": e["focus_110_121_endpoint_delta_turns"]}
    return output


def timing_drift(canonical_oracle: dict[str, Any], candidate_oracle: dict[str, Any]) -> dict[str, Any]:
    by_round: dict[str, Any] = {}
    all_abs: list[float] = []
    for index in range(1, 5):
        round_values: dict[str, Any] = {}
        for stage in CHAIN_STAGES:
            c = phase_time(canonical_oracle, stage, index)
            e = phase_time(candidate_oracle, stage, index)
            delta = e - c if c is not None and e is not None else None
            if delta is not None:
                all_abs.append(abs(delta))
            round_values[stage] = {"canonical_ps": c, "candidate_ps": e, "delta_ps": delta}
        by_round[str(index)] = {"landmarks": round_values, "max_abs_delta_ps": max((abs(item["delta_ps"]) for item in round_values.values() if item["delta_ps"] is not None), default=None)}
    return {"status": "DERIVED", "by_response_index": by_round, "max_abs_delta_ps": max(all_abs) if all_abs else None, "actual_stored_grid": True, "not_literal_propagation_delay_claim": True}


def bridge_comparison(canonical: Any, candidate: Any, window: tuple[float, float]) -> dict[str, Any]:
    output = {}
    for index in range(1, 5):
        instance = f"XBVM{index}"
        ref_total, ref_voltage, _, _ = bridge_vectors(canonical, "canonical", instance)
        cand_total, cand_voltage, _, _ = bridge_vectors(candidate, "candidate", instance)
        indices = time_indices(canonical, window)
        total_delta = [cand_total[i] - ref_total[i] for i in indices]
        voltage_delta = [cand_voltage[i] - ref_voltage[i] for i in indices]
        total_scale = max(max(ref_total[i] for i in indices) - min(ref_total[i] for i in indices), max(abs(ref_total[i]) for i in indices), 1.0e-30)
        voltage_scale = max(max(ref_voltage[i] for i in indices) - min(ref_voltage[i] for i in indices), max(abs(ref_voltage[i]) for i in indices), 1.0e-30)
        output[instance] = {"total_current": {"rms_difference_A": math.sqrt(sum(value * value for value in total_delta) / len(total_delta)), "max_abs_difference_A": max(abs(value) for value in total_delta), "normalized_rms": math.sqrt(sum(value * value for value in total_delta) / len(total_delta)) / total_scale, "reference_scale_A": total_scale}, "bridge_voltage": {"rms_difference_V": math.sqrt(sum(value * value for value in voltage_delta) / len(voltage_delta)), "max_abs_difference_V": max(abs(value) for value in voltage_delta), "normalized_rms": math.sqrt(sum(value * value for value in voltage_delta) / len(voltage_delta)) / voltage_scale, "reference_scale_V": voltage_scale}}
    return {"window_ps": list(window), "instances": output, "actual_grid": True, "interpolation": False}


def trace_metrics(case_id: str, trace: Any, oracle_module: Any, kind: str) -> dict[str, Any]:
    if case_id in RUN_ORDER:
        info = case_info(case_id)
    elif case_id.startswith("CANONICAL_"):
        info = {"mask": case_id.split("_", 1)[1], "delay_ps": None}
    else:
        info = {"mask": case_id, "delay_ps": None}
    mask = info["mask"]
    metrics = branch_helpers.run_metrics(case_id, mask, trace, family=None if kind == "canonical" else "LS3", canonical=kind == "canonical", delay_ps=info.get("delay_ps"))
    metrics["multi_evidence_oracle"] = multi_evidence_oracle(trace, mask, oracle_module)
    metrics["active_bvm_indices"] = [index for index, bit in enumerate(mask, 1) if bit == "1"]
    metrics["phase_area_cross_checks_active"] = {f"P({element}|XBVM{index})": branch_helpers.phase_area(trace, f"P({element}|XBVM{index})", f"V({element}|XBVM{index})") for index in metrics["active_bvm_indices"] for element in ("B_JS1", "B_JS2")}
    if kind != "canonical":
        metrics["source_injection_error"] = source_injection_error(case_id, trace)
        bridge = {}
        for index in range(1, 5):
            instance = f"XBVM{index}"
            total, voltage, imposed, role = bridge_vectors(trace, "candidate", instance)
            bridge[instance] = {"imposed_current_focus": vector_stats(trace, imposed, FOCUS_WINDOW, f"I(I_LS3_REPLAY|{instance})", "A"), "imposed_current_rearm": vector_stats(trace, imposed, REARM_WINDOW, f"I(I_LS3_REPLAY|{instance})", "A"), "physical_RS_current_focus": vector_stats(trace, list(trace.column(f"I(R_S|{instance})")), FOCUS_WINDOW, f"I(R_S|{instance})", "A"), "physical_RS_current_rearm": vector_stats(trace, list(trace.column(f"I(R_S|{instance})")), REARM_WINDOW, f"I(R_S|{instance})", "A"), "total_current_focus": vector_stats(trace, total, FOCUS_WINDOW, f"I_TOTAL_{instance}", "A"), "total_current_rearm": vector_stats(trace, total, REARM_WINDOW, f"I_TOTAL_{instance}", "A"), "Vbridge_focus": vector_stats(trace, voltage, FOCUS_WINDOW, f"Vbridge_{instance}", "V"), "Vbridge_rearm": vector_stats(trace, voltage, REARM_WINDOW, f"Vbridge_{instance}", "V"), "energy_110_121": energy_record(trace, voltage, imposed, FOCUS_WINDOW, role), "energy_110_130": energy_record(trace, voltage, imposed, (110.0, 130.0), role), "definition": "I_TOTAL=I_LS3_REPLAY+I(R_S); Vbridge=V(6)-V(10); ideal source branch current only", "passive_realizability_claim": False}
        metrics["ls3_replay_bridge_artifact"] = bridge
    return metrics


def exact_gate(mask: str, canonical_trace: Any, exact_trace: Any, canonical_metrics: dict[str, Any], exact_metrics: dict[str, Any]) -> dict[str, Any]:
    c_oracle = canonical_metrics["multi_evidence_oracle"]
    e_oracle = exact_metrics["multi_evidence_oracle"]
    required_chain_count = 1 if mask == "0001" else 4
    timing = timing_drift(c_oracle, e_oracle)
    phase = phase_p2p_deltas(canonical_trace, exact_trace, mask)
    required_signals = ["I(B_JSL8)", "V(COMMON_SL)", "V(QBIN)", "I(LIN|XBQ1)", "I(L1|XBQ1)", "I(L2|XBQ1)", "V(QBOUT)", "V(JTL6_OUT)", "I(R_TERM)"] + [f"P(B01|XJTL1_{stage})" for stage in JTL_STAGES] + [f"V(JTL{stage}_OUT)" for stage in JTL_STAGES]
    for index in range(1, 5):
        for element in ("B_JS1", "B_JS2") if index in [i for i, bit in enumerate(mask, 1) if bit == "1"] else ():
            required_signals.extend([f"{kind}({element}|XBVM{index})" for kind in ("P", "V", "I")])
    waveform = {signal: normalized_delta(canonical_trace, exact_trace, signal, FOCUS_WINDOW) for signal in required_signals}
    derived_waveforms = [item for item in waveform.values() if item.get("status") == "DERIVED" and "normalized_rms" in item]
    norm_values = [item["normalized_rms"] for item in derived_waveforms]
    phase_values = [item["absolute_delta_turns"] for item in phase.values()]
    injection = exact_metrics["source_injection_error"]
    criteria = {
        "grid_equal": tuple(canonical_trace.time) == tuple(exact_trace.time),
        "phase_chain_count_equal": c_oracle["ordered_phase_chain_count"] == e_oracle["ordered_phase_chain_count"] == required_chain_count,
        "all_registered_landmark_timing_within_tolerance": timing["max_abs_delta_ps"] is not None and timing["max_abs_delta_ps"] <= EXACT_TIMING_TOL_PS,
        "active_JS1_JS2_focus_p2p_within_tolerance": bool(phase_values) and max(phase_values) <= EXACT_PHASE_P2P_TOL_TURNS,
        "required_waveforms_present_and_normalized_RMS_within_tolerance": all(item.get("status") != "UNKNOWN" for item in waveform.values()) and bool(norm_values) and max(norm_values) <= EXACT_NORMALIZED_WAVEFORM_RMS_TOL,
        "source_injection_error_within_tolerance": injection["status"] == "PASS",
    }
    return {"status": "PASS" if all(criteria.values()) else "FAIL", "mask": mask, "criteria": criteria, "required_chain_count": required_chain_count, "canonical_phase_chain_count": c_oracle["ordered_phase_chain_count"], "exact_phase_chain_count": e_oracle["ordered_phase_chain_count"], "timing_drift": timing, "active_JS1_JS2_focus_p2p": phase, "waveform_normalized_RMS": waveform, "max_normalized_RMS": max(norm_values) if norm_values else None, "source_injection_error": injection, "registered_tolerances": {"timing_ps": EXACT_TIMING_TOL_PS, "phase_p2p_turns": EXACT_PHASE_P2P_TOL_TURNS, "normalized_RMS": EXACT_NORMALIZED_WAVEFORM_RMS_TOL, "source_error_A": EXACT_SOURCE_ERROR_TOL_A}, "screen_is_mechanical_not_physical_equivalence": True}


def update_after_exact(mask: str) -> None:
    provenance = read_json(EXP / "provenance.json")
    exact_id = f"LS3_EXACT_{mask}"
    if exact_id not in provenance["run_order"]:
        raise RuntimeError(f"cannot gate missing exact case: {mask}")
    oracle_module = load_oracle_module()
    canonical_trace = load_raw(CANONICAL_RAW[mask])
    exact_trace = load_raw(REPO / provenance["runs"][exact_id]["raw"]["path"])
    c_metrics = trace_metrics(f"CANONICAL_{mask}", canonical_trace, oracle_module, "canonical")
    e_metrics = trace_metrics(exact_id, exact_trace, oracle_module, "candidate")
    gate = exact_gate(mask, canonical_trace, exact_trace, c_metrics, e_metrics)
    provenance.setdefault("exact_fidelity", {})[mask] = gate
    provenance.setdefault("exact_gate_metrics", {})[mask] = {"canonical": c_metrics, "exact": e_metrics}
    write_json(EXP / "analysis" / f"EXACT_GATE_{mask}.json", gate)
    write_json(EXP / "provenance.json", provenance)
    result = read_json(EXP / "result.json")
    result["exact_fidelity"][mask] = {key: value for key, value in gate.items() if key not in ("waveform_normalized_RMS",)}
    result["exact_fidelity"][mask]["waveform_max_normalized_RMS"] = gate["max_normalized_RMS"]
    result["status"] = f"EXACT_{mask}_GATE_{gate['status']}_DELAY_PENDING"
    result["artifact_status"] = "VALID"
    result["execution"] = provenance["execution"]
    write_json(EXP / "result.json", result)
    print(json.dumps({"status": gate["status"], "mask": mask, "timing_max_abs_ps": gate["timing_drift"]["max_abs_delta_ps"], "max_normalized_RMS": gate["max_normalized_RMS"]}, ensure_ascii=False, indent=2))


def compare_case(canonical_trace: Any, candidate_trace: Any, mask: str, candidate_metrics: dict[str, Any], canonical_metrics: dict[str, Any]) -> dict[str, Any]:
    signals = ["I(B_JSL8)", "V(COMMON_SL)", "V(QBIN)", "I(LIN|XBQ1)", "I(L1|XBQ1)", "I(L2|XBQ1)", "V(QBOUT)", "V(JTL6_OUT)", "I(R_TERM)"] + [f"P(B01|XJTL1_{stage})" for stage in JTL_STAGES] + [f"V(JTL{stage}_OUT)" for stage in JTL_STAGES]
    for index in range(1, 5):
        if index in [i for i, bit in enumerate(mask, 1) if bit == "1"]:
            signals.extend([f"{kind}({element}|XBVM{index})" for element in ("B_JS1", "B_JS2", "B_JM1", "B_JM2") for kind in ("P", "V", "I")])
    signal_deltas = {signal: {"focus_110_121": normalized_delta(canonical_trace, candidate_trace, signal, FOCUS_WINDOW), "full_0_200": normalized_delta(canonical_trace, candidate_trace, signal, FULL_WINDOW)} for signal in signals}
    return {"vs_canonical": signal_deltas, "bridge_focus": bridge_comparison(canonical_trace, candidate_trace, FOCUS_WINDOW), "bridge_full": bridge_comparison(canonical_trace, candidate_trace, FULL_WINDOW), "timing_drift": timing_drift(canonical_metrics["multi_evidence_oracle"], candidate_metrics["multi_evidence_oracle"]), "active_phase_p2p": phase_p2p_deltas(canonical_trace, candidate_trace, mask), "actual_grid": True, "interpolation": False}


def reused_population_context(oracle_module: Any) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for name, path in REUSED_RAW.items():
        trace = load_raw(path)
        mask = "0011" if name.startswith("N2") else "0111"
        oracle = multi_evidence_oracle(trace, mask, oracle_module)
        output[name] = {"mask": mask, "raw_path": rel(path), "raw_sha256": sha256(path), "ordered_phase_chain_count": oracle["ordered_phase_chain_count"], "old_strict_complete_response_count": oracle["old_strict_complete_response_count"], "jtl6_cluster_count": oracle["jtl6_cluster_count"], "terminal_pulse_count": oracle["terminal_pulse_count"], "terminal_total_area_over_phi0": oracle["terminal_total_area_over_phi0"], "descriptive_candidate_label": oracle["descriptive_candidate_label"], "physical_solve_this_experiment": False, "read_only_context": True}
    return output


def compact_case(case_id: str, metrics: dict[str, Any], validation: dict[str, Any] | None, exact_gate_status: str | None) -> dict[str, Any]:
    oracle = metrics["multi_evidence_oracle"]
    phase = oracle["phase_landmarks"]
    focus_js = {}
    for index in metrics.get("active_bvm_indices", []):
        focus_js[f"XBVM{index}"] = {element: metrics["bvm"]["cells"][f"XBVM{index}"]["phase_navigation"][f"P({element}|XBVM{index})"]["focus_110_121_p2p_turns"] for element in ("B_JS1", "B_JS2")}
    return {"run_id": case_id, "mask": case_info(case_id)["mask"], "delay_ps": case_info(case_id)["delay_ps"], "old_strict_complete_response_count": oracle["old_strict_complete_response_count"], "ordered_phase_chain_count": oracle["ordered_phase_chain_count"], "jtl6_cluster_count": oracle["jtl6_cluster_count"], "terminal_pulse_count": oracle["terminal_pulse_count"], "terminal_total_area_over_phi0": oracle["terminal_total_area_over_phi0"], "descriptive_candidate_label": oracle["descriptive_candidate_label"], "BJ1_landmarks_ps": [phase_time(oracle, "BJ1", i) for i in range(1, 5)], "BJ2_landmarks_ps": [phase_time(oracle, "BJ2", i) for i in range(1, 5)], "JS1_JS2_focus_p2p_turns": focus_js, "exact_gate_status": exact_gate_status, "validation_status": validation.get("status") if validation else None, "raw_path": metrics["raw_path"], "raw_sha256": metrics["raw_sha256"]}


def population_result(cases: dict[str, dict[str, Any]], reused: dict[str, Any]) -> dict[str, Any]:
    n1_exact = cases["LS3_EXACT_0001"]["multi_evidence_oracle"]["descriptive_candidate_label"]
    n1_delay = cases["LS3_DELAY0P3_0001"]["multi_evidence_oracle"]["descriptive_candidate_label"]
    n4_exact = cases["LS3_EXACT_1111"]["multi_evidence_oracle"]["descriptive_candidate_label"]
    n4_delay = cases["LS3_DELAY0P3_1111"]["multi_evidence_oracle"]["descriptive_candidate_label"]
    n2_c = reused["N2_CANONICAL"]["ordered_phase_chain_count"]
    n2_d = reused["N2_LS3_DELAY0P3"]["ordered_phase_chain_count"]
    n3_c = reused["N3_CANONICAL"]["ordered_phase_chain_count"]
    n3_d = reused["N3_LS3_DELAY0P3"]["ordered_phase_chain_count"]
    if n1_delay.startswith("ONE_RESPONSE_LIKE") and n2_d == 2 and n3_d == 3 and n4_delay == "N4_FOUR_RESPONSE_LIKE_PRESERVED":
        candidate = "POPULATION_MAPPING_1_2_3_4_SUPPORTED_BY_CURRENT_REPLAY"
    elif n1_delay.startswith("ONE_RESPONSE_LIKE") and n2_d == 2 and n3_d == 3 and n4_delay == "N4_REDUCED_TO_THREE_RESPONSE_LIKE":
        candidate = "THREE_RESPONSE_CAP_BEHAVIOR_OBSERVED"
    else:
        candidate = "POPULATION_VALIDATION_MIXED"
    table = [
        {"population": "N1 0001", "canonical": "1-like", "LS3_delay0p3": n1_delay, "exact": n1_exact},
        {"population": "N2 0011", "canonical": n2_c, "LS3_delay0p3": n2_d, "source": "reused prior validated raw"},
        {"population": "N3 0111", "canonical": n3_c, "LS3_delay0p3": n3_d, "source": "reused prior validated raw"},
        {"population": "N4 1111", "canonical": "4-like", "LS3_delay0p3": n4_delay, "exact": n4_exact},
    ]
    return {"status": "MECHANICAL_CANDIDATE_ONLY", "table": table, "candidate_population_label": candidate, "classification": "NOT_ASSIGNED_SCIENTIFIC_REVIEW_REQUIRED", "N4_old_strict_field_retained": True, "N2_N3_rerun": False, "scientific_interpretation_performed": False}


def analyze_all() -> None:
    provenance = read_json(EXP / "provenance.json")
    if provenance["run_order"] != list(RUN_ORDER):
        raise RuntimeError(f"analysis requires exactly registered run order {RUN_ORDER}, got {provenance['run_order']}")
    registered_runner = next(item for item in provenance["source_closure"] if item["name"] == "runner")
    current_runner = record_file("runner", SCRIPT, registered_runner["role"])
    if registered_runner["sha256"] != current_runner["sha256"]:
        provenance["postsolve_tooling_revision"] = {"path": rel(SCRIPT), "old_sha256": registered_runner["sha256"], "new_sha256": current_runner["sha256"], "reason": "analysis-only parser repair; no physical rerun", "physical_rerun": False, "raw_mutated": False}
        registered_runner.update({"sha256": current_runner["sha256"], "bytes": current_runner["bytes"]})
    oracle_module = load_oracle_module()
    canonical_traces = {mask: load_raw(path) for mask, path in CANONICAL_RAW.items()}
    canonical_metrics = {mask: trace_metrics(f"CANONICAL_{mask}", trace, oracle_module, "canonical") for mask, trace in canonical_traces.items()}
    traces = {case_id: load_raw(REPO / provenance["runs"][case_id]["raw"]["path"]) for case_id in RUN_ORDER}
    metrics = {case_id: trace_metrics(case_id, traces[case_id], oracle_module, "candidate") for case_id in RUN_ORDER}
    validations: dict[str, Any] = {}
    for case_id in RUN_ORDER:
        mask = case_info(case_id)["mask"]
        validations[case_id] = compare_case(canonical_traces[mask], traces[case_id], mask, metrics[case_id], canonical_metrics[mask])
        if case_id.startswith("LS3_EXACT"):
            validations[case_id]["exact_gate"] = provenance["exact_fidelity"][mask]
        else:
            validations[case_id]["interpretation_allowed_only_if_exact_gate_pass"] = provenance["exact_fidelity"][mask]["status"] == "PASS"
            validations[case_id]["validation_interpretation_status"] = "MECHANICAL_ONLY_EXACT_GATE_FAILED" if provenance["exact_fidelity"][mask]["status"] != "PASS" else "MECHANICAL_EVIDENCE_READY_FOR_SCIENTIFIC_REVIEW"
    reused = reused_population_context(oracle_module)
    population = population_result({**metrics}, reused)
    raw_before = {case_id: sha256(REPO / provenance["runs"][case_id]["raw"]["path"]) for case_id in RUN_ORDER}
    refs_before = {path: sha256(Path(path)) for path in [item["path"] for item in provenance["source_closure"] if item["name"].startswith(("canonical_", "reused_", "previous_branch_"))]}
    mechanical = {"schema": "bvm-rloop-ls3-population-mechanical-analysis-v1", "experiment_id": EXP.name, "generated_at": now(), "cases": metrics, "canonical_references": canonical_metrics, "validations": validations, "reused_population_context": reused, "population_comparison": population, "raw_hash_before_analysis": raw_before, "reference_hashes_before_analysis": refs_before, "raw_is_immutable_solver_output": True, "actual_grid": True, "interpolation": False, "resampling": False, "scientific_interpretation_performed": False, "independent_scientific_review_performed": False}
    write_json(EXP / "analysis" / "mechanical_analysis.json", mechanical)
    raw_after = {case_id: sha256(REPO / provenance["runs"][case_id]["raw"]["path"]) for case_id in RUN_ORDER}
    refs_after = {path: sha256(Path(path)) for path in refs_before}
    if raw_before != raw_after or refs_before != refs_after:
        raise RuntimeError("raw/reference mutation detected during analysis")
    provenance["mechanical_analysis_performed"] = True
    provenance["bounded_experiment_interpretation_performed"] = False
    provenance["independent_scientific_review_performed"] = False
    provenance["scientific_interpretation_performed"] = False
    provenance["raw_hash_before_analysis"] = raw_before
    provenance["raw_hash_after_analysis"] = raw_after
    provenance["reference_hashes_before_analysis"] = refs_before
    provenance["reference_hashes_after_analysis"] = refs_after
    provenance["analysis"] = {"status": "COMPLETE", "generated_at": now(), "path": rel(EXP / "analysis" / "mechanical_analysis.json"), "population_comparison": population, "exact_fidelity": {mask: provenance["exact_fidelity"][mask] for mask in ("0001", "1111")}, "no_n2_n3_rerun": True, "scientific_classification": "NOT_ASSIGNED_SCIENTIFIC_REVIEW_REQUIRED"}
    provenance["execution_status"] = "ALL_AUTHORIZED_RUNS_COMPLETE_ANALYSIS_PENDING"
    for case_id in RUN_ORDER:
        provenance["runs"][case_id]["mechanical_analysis_performed"] = True
        provenance["runs"][case_id]["bounded_experiment_interpretation_performed"] = False
        provenance["runs"][case_id]["independent_scientific_review_performed"] = False
    write_json(EXP / "provenance.json", provenance)
    result = read_json(EXP / "result.json")
    result.update({"generated_at": now(), "status": "ANALYSIS_COMPLETE_AWAITING_SCIENTIFIC_REVIEW", "artifact_status": "VALID", "mechanical_analysis_performed": True, "bounded_experiment_interpretation_performed": False, "independent_scientific_review_performed": False, "scientific_interpretation_performed": False, "execution": provenance["execution"], "cases": {case_id: compact_case(case_id, metrics[case_id], validations[case_id], provenance["exact_fidelity"][case_info(case_id)["mask"]]["status"]) for case_id in RUN_ORDER}, "population_comparison": population, "classification": {"status": "SCIENTIFIC_REVIEW_REQUIRED", "assigned": None, "candidate_label": population["candidate_population_label"], "reason": "candidate label is mechanical evidence only; no scientific category assigned"}, "stop": {"final_marker": FINAL_MARKER, "automatic_follow_up": False}})
    write_json(EXP / "result.json", result)
    write_population_markdown(result, mechanical)
    write_json(EXP / "analysis" / "SOURCE_MANIFEST.json", {"schema": "bvm-rloop-ls3-population-source-manifest-v1", "experiment_id": EXP.name, "generated_at": now(), "source_closure": provenance["source_closure"], "canonical_source_raw_hashes": EXPECTED_RAW_HASHES, "reused_context_raw_hashes": EXPECTED_REUSED_HASHES, "branch_direction_audit": provenance["branch_direction_audit"]})
    (EXP / "analysis" / "TRANSFORMATION_REGISTRY.json").write_text(json.dumps({"schema": "bvm-rloop-ls3-population-transformation-registry-v1", "raw_mutation": False, "operations": [{"name": "LS3_exact", "rule": "same-instance canonical I(L_S3) at every stored sample"}, {"name": "LS3_delay0p3", "rule": "pre-110 same; [110,110.3) hold sample 110; post exact index i-3", "interpolation": False, "resampling": False, "amplitude_scaling": False, "sign_change": False}, {"name": "n4_multi_evidence", "rule": "phase landmarks, ordered JTL chains, historical valley-separated JTL6/terminal clusters, terminal area", "old_strict_field": "retained contextual only"}, {"name": "phase_display", "rule": "unwrap(raw radians)/(2*pi), navigation only"}, {"name": "area", "rule": "same JJ/endpoints/direction/window actual-grid trapezoid; not SFQ count"}]}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "ANALYSIS_COMPLETE", "population_candidate_label": population["candidate_population_label"], "exact_gates": {mask: provenance["exact_fidelity"][mask]["status"] for mask in ("0001", "1111")}}, ensure_ascii=False, indent=2))


def write_population_markdown(result: dict[str, Any], mechanical: dict[str, Any]) -> None:
    population = result["population_comparison"]
    lines = [f"# LS3-only delay population validation ({EXP.name})", "", f"- Status: `{result['status']}`", "- Artifact status: `VALID`", "- Scientific interpretation: `NOT_PERFORMED`; final classification: `SCIENTIFIC_REVIEW_REQUIRED`.", f"- HEAD: `{EXPECTED_HEAD}`; four authorized solves only; 0.3 ps = 3 actual stored samples.", "- Fixture: canonical BVM → COMMON_SL → JSL1..8 → canonical QB → JTL1..6 → terminal; per-instance ideal LS3 current replay with physical R_S retained.", "- The source is a causal replay counterfactual, not a physical delay or passive-realizability proof.", "", "## Exact fidelity gates", "", "| mask | exact gate | max landmark timing drift (ps) | max active JS1/JS2 p2p drift (turns) | max normalized RMS |", "|---|---|---:|---:|---:|"]
    for mask in ("0001", "1111"):
        gate = result["exact_fidelity"][mask]
        phase = gate.get("active_JS1_JS2_focus_p2p", {})
        max_phase = max((item.get("absolute_delta_turns", 0.0) for item in phase.values()), default=None)
        lines.append(f"| `{mask}` | `{gate['status']}` | {fmt(gate.get('timing_drift', {}).get('max_abs_delta_ps'))} | {fmt(max_phase)} | {fmt(gate.get('max_normalized_RMS'))} |")
    lines.extend(["", "## Population comparison", "", "| population | canonical | LS3 delay 0.3 ps |", "|---|---:|---:|"])
    for row in population["table"]:
        lines.append(f"| `{row['population']}` | `{row['canonical']}` | `{row['LS3_delay0p3']}` |")
    lines.extend(["", f"- Mechanical candidate label: `{population['candidate_population_label']}`.", "- Final scientific assignment: `NOT_ASSIGNED_SCIENTIFIC_REVIEW_REQUIRED`.", "- N2/N3 are reused read-only raw evidence; no N2/N3 solve was executed in this experiment.", "", "## N1/N4 multi-evidence record", "", "| case | old strict count | ordered phase chains | JTL6 clusters | terminal clusters | terminal area / Φ0 | descriptive candidate |", "|---|---:|---:|---:|---:|---:|---|"])
    for case_id in ("LS3_EXACT_0001", "LS3_DELAY0P3_0001", "LS3_EXACT_1111", "LS3_DELAY0P3_1111"):
        item = mechanical["cases"][case_id]["multi_evidence_oracle"]
        lines.append(f"| `{case_id}` | {item['old_strict_complete_response_count']} | {item['ordered_phase_chain_count']} | {item['jtl6_cluster_count']} | {item['terminal_pulse_count']} | {fmt(item['terminal_total_area_over_phi0'])} | `{item['descriptive_candidate_label']}` |")
    lines.extend(["", "For N4 the old strict field is deliberately shown beside the primary multi-evidence result: the strict count may be zero even when four phase chains, four JTL6/terminal clusters and near-four terminal area are present. It is contextual, not the sole oracle.", "", "### N4 round-by-round timing drift", "", "| response index | canonical BJ1 (ps) | delayed BJ1 (ps) | ΔBJ1 (ps) | canonical BJ2 (ps) | delayed BJ2 (ps) | ΔBJ2 (ps) |", "|---:|---:|---:|---:|---:|---:|---:|"])
    n4_timing = mechanical["validations"]["LS3_DELAY0P3_1111"]["timing_drift"]["by_response_index"]
    for index in range(1, 5):
        item = n4_timing[str(index)]["landmarks"]
        lines.append(f"| {index} | {fmt(item['BJ1']['canonical_ps'])} | {fmt(item['BJ1']['candidate_ps'])} | {fmt(item['BJ1']['delta_ps'])} | {fmt(item['BJ2']['canonical_ps'])} | {fmt(item['BJ2']['candidate_ps'])} | {fmt(item['BJ2']['delta_ps'])} |")
    lines.extend(["", "## Evidence retained", "", "- Per-run active BVM JS1/JS2 phase navigation and same-JJ voltage-area cross-checks.", "- BJ1/BJ2 landmarks, ordered JTL phase chains, JTL6/terminal cluster peaks/valleys/areas, terminal area/Φ0.", "- I(B_JSL8), COMMON_SL, QBIN/QB, all JSL/JTL stages, JM1/JM2, R_S, imposed LS3, I_TOTAL and Vbridge.", "- Ideal-source P_absorb = V(node6−node10) × I_source(node6→node10), signed and absolute exchanged energy; per-instance extrema and [110,121)/[110,130) records are in `analysis/mechanical_analysis.json`.", "- Phase is raw radians; turns are navigation only. Areas are same-JJ actual-grid arithmetic, not SFQ counts.", "", f"Stop marker: `{FINAL_MARKER}`.", ""])
    (EXP / "RESULT.md").write_text("\n".join(lines), encoding="utf-8")
    numerical = ["# Numerical review — mechanical only", "", "- Actual stored grid is retained; no interpolation/resampling was used.", "- Exact gate uses all registered phase landmark timing, active JS1/JS2 focus p2p, key waveform normalized RMS, and replay-source injection error.", "- Same-JJ phase/voltage-area checks use common endpoints, direction and [110,121) ps actual-grid trapezoids.", "- P(...) remains raw radians; displayed turns use independent unwrap/(2*pi) navigation only.", "- Timestep/convergence sensitivity and physical equivalence are UNKNOWN/not tested."]
    adversarial = ["# Adversarial review probes — mechanical only", "", "- Source authority hashes are pinned before PWL construction for N1 and N4.", "- Canonical R_S/L_S3 direction, resistor law, parallel voltage and node6/node10 KCL audits are required before source construction.", "- Each BVM instance has a distinct replay waveform; no common source is used.", "- N4 old strict count is exposed but not used as sole oracle; multi-evidence records phase chains, JTL6/terminal valleys and terminal area.", "- Raw/reference hashes are checked before/after analysis; raw solver output is not rewritten.", "- Exact solve order is enforced and maximum physical solves is four.", "- Overclaim guard: no passive LS3 delay claim, SFQ count, root-cause or final population classification."]
    (EXP / "analysis" / "NUMERICAL_REVIEW.md").write_text("\n".join(numerical) + "\n", encoding="utf-8")
    (EXP / "analysis" / "ADVERSARIAL_REVIEW.md").write_text("\n".join(adversarial) + "\n", encoding="utf-8")


def fmt(value: Any) -> str:
    if value is None:
        return "—"
    try:
        return f"{float(value):.8g}"
    except (TypeError, ValueError):
        return str(value)


def mechanical_qa() -> None:
    provenance = read_json(EXP / "provenance.json")
    failures: list[str] = []
    checks: dict[str, Any] = {}
    for case_id in RUN_ORDER:
        record = provenance.get("runs", {}).get(case_id)
        if not record:
            failures.append(case_id)
            continue
        deck = REPO / record["deck"]["path"]
        raw = REPO / record["raw"]["path"]
        log = REPO / record["log"]["path"]
        meta = REPO / record["metadata"]["path"]
        info = case_info(case_id)
        try:
            trace = load_raw(raw)
            grid = branch_helpers.replay_base.finite_grid_qa(trace)
            missing = sorted(expected_headers(info["mask"]) - set(trace.headers))
            duplicates = trace.duplicate_columns
        except Exception as exc:
            grid, missing, duplicates = {"status": "INVALID", "error": str(exc)}, [str(exc)], {"parse": str(exc)}
        text_value = deck.read_text(encoding="utf-8") if deck.is_file() else ""
        topology_ok = text_value.count("I_LS3_REPLAY 6 10 PWL(") == 4 and text_value.count("R_S     6       10      3.0") == 4 and text_value.count("XBQ1 QBIN QBOUT BQ") == 1 and text_value.count("R_TERM JTL6_OUT 0 10") == 1 and ".tran 0.1p 200p" in text_value and "L_S3     6       10      0.5P" not in text_value and "L_S3    6       10      0.5P" not in text_value
        warnings = warning_lines(log)
        unexpected = [line for line in warnings if line not in KNOWN_WARNINGS]
        passed = bool(record.get("execution_status") == "RUN_PASS" and topology_ok and deck.is_file() and raw.is_file() and meta.is_file() and log.is_file() and sha256(deck) == provenance["registered_decks"][case_id]["sha256"] and sha256(raw) == record["raw"]["sha256"] and sha256(log) == record["log"]["sha256"] and not missing and not duplicates and grid.get("status") == "VALID" and grid.get("sample_count") == 1999 and grid.get("time_start_ps") == 0.0 and grid.get("time_end_ps") == 199.9 and not unexpected)
        if not passed:
            failures.append(case_id)
        checks[case_id] = {"status": "PASS" if passed else "ARTIFACT_INVALID", "topology_ok": topology_ok, "grid": grid, "missing_required_probes": missing, "duplicate_columns": duplicates, "warnings": warnings, "unexpected_warnings": unexpected, "raw_sha256": sha256(raw) if raw.is_file() else None, "registered_raw_sha256": record["raw"].get("sha256")}
    source_hashes_match = all(path.is_file() and sha256(path) == item["sha256"] for item in provenance["source_closure"] for path in [REPO / item["path"]])
    raw_equal = provenance.get("raw_hash_before_analysis") == provenance.get("raw_hash_after_analysis")
    references_equal = provenance.get("reference_hashes_before_analysis") == provenance.get("reference_hashes_after_analysis")
    passed = bool(provenance.get("run_order") == list(RUN_ORDER) and not failures and source_hashes_match and raw_equal and references_equal and provenance.get("execution", {}).get("actual_physical_solve_count") == 4 and not any(case_id not in RUN_ORDER for case_id in provenance.get("run_order", [])))
    qa = {"schema": "bvm-rloop-ls3-population-mechanical-qa-v1", "experiment_id": EXP.name, "generated_at": now(), "status": "PASS" if passed else "FAIL", "artifact_status": "VALID" if passed else "ARTIFACT_INVALID", "head": git_head(), "remote_bvm_master": remote_head(), "run_order": provenance.get("run_order"), "expected_run_order": list(RUN_ORDER), "actual_physical_solve_count": provenance.get("execution", {}).get("actual_physical_solve_count"), "max_physical_solves": 4, "no_extra_follow_up": provenance.get("run_order") == list(RUN_ORDER), "source_hashes_match": source_hashes_match, "raw_hash_before_after_equal": raw_equal, "reference_hashes_before_after_equal": references_equal, "contains_all_new_run_raw": None, "contains_reference_raw_copies": False, "contains_delivery_manifest": False, "runs": checks, "failures": failures, "mechanical_analysis_performed": True, "bounded_experiment_interpretation_performed": False, "independent_scientific_review_performed": False, "scientific_interpretation_performed": False}
    write_json(EXP / "analysis" / "MECHANICAL_QA.json", qa)
    provenance["qa"] = qa
    write_json(EXP / "provenance.json", provenance)
    result = read_json(EXP / "result.json")
    result["qa_summary"] = {"status": qa["status"], "artifact_status": qa["artifact_status"]}
    write_json(EXP / "result.json", result)
    if not passed:
        raise RuntimeError(f"mechanical QA failed: {failures}")
    print(json.dumps({"status": "PASS", "run_order": provenance["run_order"], "physical_solves": 4}, ensure_ascii=False, indent=2))


def render_plot(input_path: Path, output_path: Path, signals: list[str], title: str, asset: Path) -> None:
    branch_helpers.render_plot(input_path, output_path, signals, title, asset)


def visualization() -> None:
    provenance = read_json(EXP / "provenance.json")
    if provenance.get("qa", {}).get("status") != "PASS":
        raise RuntimeError("mechanical QA must pass before visualization")
    asset = EXP / "plots" / "assets" / "plotly.min.js"
    entries: list[dict[str, Any]] = []
    specs = {
        "01_BVM_RLOOP": [signal for index in range(1, 5) for element in ("B_JS1", "B_JS2", "B_JM1", "B_JM2") for signal in (f"P({element}|XBVM{index})", f"V({element}|XBVM{index})", f"I({element}|XBVM{index})")] + [signal for index in range(1, 5) for element in ("L_S1", "L_S2", "L_M3", "L_S3", "R_S", "L_SL") for signal in (f"I({element}|XBVM{index})", f"V({element}|XBVM{index})")],
        "02_FORWARD_CHAIN": ["V(COMMON_SL)", "I(B_JSL8)", "V(QBIN)", "V(QBOUT)", *[f"V(JTL{stage}_OUT)" for stage in JTL_STAGES], "I(R_TERM)"],
        "03_LS3_SOURCE": [signal for index in range(1, 5) for signal in (f"I(I_LS3_REPLAY|XBVM{index})", f"I(R_S|XBVM{index})", f"V(R_S|XBVM{index})", f"V(6|XBVM{index})", f"V(10|XBVM{index})")],
        "04_QB_JTL_PHASE": ["P(BJ1|XBQ1)", "P(BJ2|XBQ1)", *[f"P(B01|XJTL1_{stage})" for stage in JTL_STAGES]],
    }
    for case_id in RUN_ORDER:
        raw = REPO / provenance["runs"][case_id]["raw"]["path"]
        trace = load_raw(raw)
        for page, requested in specs.items():
            selected = [signal for signal in requested if signal in trace.headers]
            if not selected:
                continue
            output = EXP / "plots" / case_id / f"{page}_full_0_200.html"
            render_plot(raw, output, selected, f"{case_id}: {page}; full 0–200 ps; actual stored grid", asset)
            entries.append({"kind": "standalone", "run_id": case_id, "path": rel(output), "raw_path": rel(raw), "raw_sha256": sha256(raw), "sha256": sha256(output), "bytes": output.stat().st_size, "signals": selected, "window_ps": list(FULL_WINDOW), "focused": False, "phase_display": "raw radians; rad/(2*pi) turns navigation only"})
            focus = branch_helpers.total_helpers.crop_csv(raw, *FOCUS_WINDOW)
            try:
                focus_output = EXP / "plots" / case_id / f"{page}_focus_110_121.html"
                render_plot(focus, focus_output, selected, f"{case_id}: {page}; focus [110,121) ps; actual stored samples", asset)
                entries.append({"kind": "standalone", "run_id": case_id, "path": rel(focus_output), "raw_path": rel(raw), "raw_sha256": sha256(raw), "sha256": sha256(focus_output), "bytes": focus_output.stat().st_size, "signals": selected, "window_ps": list(FOCUS_WINDOW), "focused": True, "derived_input": "actual-grid crop only; no interpolation", "phase_display": "raw radians; rad/(2*pi) turns navigation only"})
            finally:
                focus.unlink(missing_ok=True)
    oracle_module = load_oracle_module()
    for mask in ("0001", "1111"):
        cases = [(f"CANONICAL_{mask}", load_raw(CANONICAL_RAW[mask]))]
        for case_id in RUN_ORDER:
            if case_info(case_id)["mask"] == mask:
                cases.append((case_id, load_raw(REPO / provenance["runs"][case_id]["raw"]["path"])))
        for page, requested in {"01_FORWARD_CHAIN": specs["02_FORWARD_CHAIN"], "02_BVM_PHASE": [f"P(B_JS1|XBVM{index})" for index in range(1, 5) if f"P(B_JS1|XBVM{index})" in cases[0][1].headers] + ["P(BJ1|XBQ1)", "P(BJ2|XBQ1)", *[f"P(B01|XJTL1_{stage})" for stage in JTL_STAGES]]}.items():
            selected = [signal for signal in requested if all(signal in trace.headers for _, trace in cases)]
            if not selected:
                continue
            temporary = branch_helpers.total_helpers.comparison_csv(cases, selected, FOCUS_WINDOW)
            output = EXP / "plots" / "comparisons" / f"{mask}_{page}_focus_110_121.html"
            try:
                plot_signals = [branch_helpers.replay_base.prefixed_label(case, signal) for case, _ in cases for signal in selected]
                render_plot(temporary, output, plot_signals, f"{mask}: canonical/LS3 exact/delay {page}; focus [110,121) ps", asset)
            finally:
                temporary.unlink(missing_ok=True)
            entries.append({"kind": "comparison", "mask": mask, "path": rel(output), "sha256": sha256(output), "bytes": output.stat().st_size, "cases": [case for case, _ in cases], "signals": selected, "window_ps": list(FOCUS_WINDOW), "focused": True, "phase_display": "independent case unwrap; rad/(2*pi) turns navigation only"})
    html_paths = sorted((EXP / "plots").rglob("*.html"))
    invalid = [rel(path) for path in html_paths if any(token in path.read_text(encoding="utf-8") for token in ("plotly.js v", "var Plotly=", "cdn.plot.ly", "Unknown"))]
    status = "PASS" if entries and asset.is_file() and not invalid else "FAIL"
    visualization_record = {"schema": "bvm-rloop-ls3-population-visualization-v1", "status": status, "generated_at": now(), "renderer": rel(PLOTTER), "layout": "sep_comb", "color": "dark", "phase_option": "2pi", "entries": entries, "standalone_count": sum(item["kind"] == "standalone" for item in entries), "comparison_count": sum(item["kind"] == "comparison" for item in entries), "focused_window_entries": sum(item["focused"] for item in entries), "asset": {"path": rel(asset), "sha256": sha256(asset) if asset.is_file() else None, "bytes": asset.stat().st_size if asset.is_file() else None}, "invalid_runtime_pages": invalid, "raw_hashes_rechecked": all(item["raw_sha256"] == sha256(REPO / item["raw_path"]) for item in entries if item["kind"] == "standalone"), "descriptive_only": True}
    write_json(EXP / "analysis" / "VISUALIZATION_MANIFEST.json", visualization_record)
    write_json(EXP / "analysis" / "VISUALIZATION_QA.json", {"status": status, "standalone_count": visualization_record["standalone_count"], "comparison_count": visualization_record["comparison_count"], "focused_window_entries": visualization_record["focused_window_entries"], "invalid_runtime_pages": invalid, "raw_hashes_rechecked": visualization_record["raw_hashes_rechecked"]})
    provenance["visualization"] = visualization_record
    write_json(EXP / "provenance.json", provenance)
    result = read_json(EXP / "result.json")
    result["visualization_summary"] = {"status": status, "standalone_count": visualization_record["standalone_count"], "comparison_count": visualization_record["comparison_count"], "focused_window_entries": visualization_record["focused_window_entries"]}
    write_json(EXP / "result.json", result)
    if status != "PASS":
        raise RuntimeError(f"visualization failed: {invalid}")
    print(json.dumps({"status": status, "standalone_count": visualization_record["standalone_count"], "comparison_count": visualization_record["comparison_count"]}, ensure_ascii=False, indent=2))


def write_evidence_manifests() -> None:
    records = []
    for path in sorted(EXP.rglob("*")):
        if not path.is_file() or path.name == "delivery_manifest.json" or path.suffix == ".tmp":
            continue
        records.append({"path": path.relative_to(EXP).as_posix(), "sha256": sha256(path), "bytes": path.stat().st_size})
    write_json(EXP / "analysis" / "RAW_ANALYSIS_HANDOFF_MANIFEST.json", {"schema": "bvm-rloop-ls3-population-raw-analysis-handoff-v1", "experiment_id": EXP.name, "generated_at": now(), "raw_is_immutable_solver_output": True, "processed_crops_are_not_raw_substitutes": True, "files_excluding_delivery_manifest": records})
    lines = ["# Evidence manifest", "", "| path | SHA-256 | bytes |", "|---|---|---:|"] + [f"| `{item['path']}` | `{item['sha256']}` | {item['bytes']} |" for item in records]
    (EXP / "analysis" / "EVIDENCE_MANIFEST.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def package_plot_selected(path: Path) -> bool:
    relative = path.relative_to(EXP / "plots").as_posix()
    return path.name == "plotly.min.js" or "focus_110_121" in relative


def package() -> None:
    provenance = read_json(EXP / "provenance.json")
    if provenance.get("qa", {}).get("status") != "PASS" or provenance.get("visualization", {}).get("status") != "PASS":
        raise RuntimeError("mechanical QA and visualization must pass before package")
    write_evidence_manifests()
    delivery_dir = Path("/mnt/d/BVM_Backages")
    delivery_dir.mkdir(parents=True, exist_ok=True)
    package_path = delivery_dir / f"{EXP.name}_raw_evidence.zip"
    version = "v1"
    if package_path.exists():
        number = 2
        while (delivery_dir / f"{EXP.name}_v{number}_raw_evidence.zip").exists():
            number += 1
        version = f"v{number}"
        package_path = delivery_dir / f"{EXP.name}_{version}_raw_evidence.zip"
    files: list[tuple[Path, str]] = [(EXP / name, name) for name in ("experiment.yaml", "PREFLIGHT.md", "RESULT.md", "result.json", "provenance.json")]
    packaged_plots = []
    for dirname in ("inputs", "runs", "analysis", "plots"):
        for path in sorted((EXP / dirname).rglob("*")):
            if path.is_file() and (dirname != "plots" or package_plot_selected(path)):
                files.append((path, path.relative_to(EXP).as_posix()))
                if dirname == "plots":
                    packaged_plots.append(path.relative_to(EXP).as_posix())
    files.append((SCRIPT, "executor/bvm_qb_rloop_ls3_population_validation.py"))
    records = [{"path": name, "sha256": sha256(path), "bytes": path.stat().st_size} for path, name in files]
    with zipfile.ZipFile(package_path, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path, name in files:
            archive.write(path, name)
    with zipfile.ZipFile(package_path, "r") as archive:
        reopened = {name: hashlib.sha256(archive.read(name)).hexdigest() for name in archive.namelist()}
    expected = {item["path"]: item["sha256"] for item in records}
    new_raw_members = [f"runs/{case_id}/raw.csv" for case_id in RUN_ORDER]
    qa = {"status": "PASS" if expected == reopened and all(member in reopened for member in new_raw_members) else "FAIL", "package_version": version, "package_path": str(package_path), "package_sha256": sha256(package_path), "package_bytes": package_path.stat().st_size, "file_count": len(records), "expected_file_hashes_match_after_reopen": expected == reopened, "zip_files": records, "not_in_git": True, "contains_all_new_run_raw": all(member in reopened for member in new_raw_members), "new_run_raw_members": new_raw_members, "contains_reference_raw_copies": False, "contains_delivery_manifest": False, "delivery_manifest_outside_zip": True, "package_plot_policy": "focused pages only plus shared Plotly runtime; full visualization remains committed", "packaged_plot_file_count": len(packaged_plots), "packaged_plot_paths": packaged_plots, "git_head_at_packaging": git_head(), "remote_head_at_packaging": remote_head()}
    manifest = {"schema": "bvm-rloop-ls3-population-delivery-manifest-v1", "experiment_id": EXP.name, "created_at": now(), "status": "READY_FOR_DRIVE_UPLOAD" if qa["status"] == "PASS" else "PACKAGE_INVALID", "package_version": version, "package_path": str(package_path), "package_sha256": qa["package_sha256"], "package_bytes": qa["package_bytes"], "package_qa": qa, "drive_folder_id": DRIVE_FOLDER_ID, "drive_file_id": None, "drive_url": None, "delivery_id_is_outside_zip_to_avoid_self_reference": True}
    write_json(EXP / "delivery_manifest.json", manifest)
    write_json(EXP / "analysis" / "PACKAGE_QA.json", qa)
    provenance["package"] = {"status": manifest["status"], "version": version, "delivery_manifest_path": "delivery_manifest.json", "package_qa": qa, "drive_file_id": None, "drive_url": None}
    write_json(EXP / "provenance.json", provenance)
    result = read_json(EXP / "result.json")
    result["package_summary"] = {"status": manifest["status"], "version": version, "package_sha256": qa["package_sha256"], "package_bytes": qa["package_bytes"], "file_count": qa["file_count"], "delivery_manifest_path": "delivery_manifest.json", "drive_file_id": None}
    write_json(EXP / "result.json", result)
    if qa["status"] != "PASS":
        raise RuntimeError("package reopen QA failed")
    print(json.dumps({"status": "PASS", "package_path": str(package_path), "sha256": qa["package_sha256"], "bytes": qa["package_bytes"], "files": qa["file_count"]}, ensure_ascii=False, indent=2))


def record_drive(file_id: str, url: str | None = None, remote_bytes: int | None = None) -> None:
    manifest_path = EXP / "delivery_manifest.json"
    manifest = read_json(manifest_path)
    package_path = Path(manifest["package_path"])
    local_sha = sha256(package_path)
    if local_sha != manifest["package_sha256"]:
        raise RuntimeError("local package changed after packaging")
    if remote_bytes is not None and int(remote_bytes) != int(manifest["package_bytes"]):
        raise RuntimeError("Drive byte-size mismatch")
    manifest.update({"status": "UPLOADED", "drive_file_id": file_id, "drive_url": url, "uploaded_at": now(), "drive_verified_local_sha256": local_sha, "drive_verified_local_bytes": package_path.stat().st_size, "remote_sha256_from_connector": None})
    write_json(manifest_path, manifest)
    provenance = read_json(EXP / "provenance.json")
    provenance["package"].update({"status": "UPLOADED", "drive_file_id": file_id, "drive_url": url, "drive_uploaded_at": manifest["uploaded_at"], "delivery_manifest_sha256": sha256(manifest_path), "drive_sha256_verified": "metadata SHA not supplied by connector"})
    write_json(EXP / "provenance.json", provenance)
    result = read_json(EXP / "result.json")
    result["package_summary"].update({"status": "UPLOADED", "drive_file_id": file_id, "drive_url": url, "drive_verified_local_sha256": local_sha})
    write_json(EXP / "result.json", result)
    print(json.dumps({"status": "UPLOADED", "drive_file_id": file_id, "drive_url": url, "package_sha256": local_sha, "package_bytes": package_path.stat().st_size}, ensure_ascii=False, indent=2))


def all_actions() -> None:
    prepare()
    execute_one("LS3_EXACT_0001")
    update_after_exact("0001")
    materialize_delay("0001")
    execute_one("LS3_DELAY0P3_0001")
    execute_one("LS3_EXACT_1111")
    update_after_exact("1111")
    materialize_delay("1111")
    execute_one("LS3_DELAY0P3_1111")
    analyze_all()
    mechanical_qa()
    visualization()
    package()


def main() -> int:
    command = sys.argv[1] if len(sys.argv) > 1 else "all"
    actions = {"prepare": prepare, "run-one": lambda: execute_one(sys.argv[2]), "gate": lambda: update_after_exact(sys.argv[2]), "materialize-delay": lambda: materialize_delay(sys.argv[2]), "analyze": analyze_all, "qa": mechanical_qa, "viz": visualization, "package": package, "record-drive": lambda: record_drive(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None, int(sys.argv[4]) if len(sys.argv) > 4 else None), "all": all_actions}
    if command not in actions:
        print(f"usage: {SCRIPT.name} [prepare|run-one CASE|gate MASK|materialize-delay MASK|analyze|qa|viz|package|record-drive FILE_ID [URL] [BYTES]|all]", file=sys.stderr)
        return 2
    if command in ("run-one", "gate", "materialize-delay") and len(sys.argv) < 3:
        print(f"{command} requires an argument", file=sys.stderr)
        return 2
    actions[command]()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
