#!/usr/bin/env python3
"""Bounded N2 TLINE Z0 rescue-gate experiment.

The experiment keeps the previously accepted TLINE topology and TD=0.3 ps,
and registers only Z0=12 and Z0=24 for the N2 mask 0011.  A single N3 solve
is materialized only when one of those two N2 cases passes the preregistered
rescue gate.  The previous Z0=6 result and the canonical raws are read-only
references; they are never rerun, copied, or modified here.

This program distinguishes mechanical raw analysis, bounded registered-gate
interpretation, and independent scientific review.  It never converts phase
or current traces into SFQ counts and it does not decompose a TLINE waveform
into incident/reflected waves.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
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
import bvm_qb_tline_feedback_dephasing as prior  # noqa: E402

replay_base = prior.replay_base

EXP = REPO / "test" / "exploration" / "bvm-qb-tline-z0-rescue-gate-v1-20260916"
PREVIOUS_EXP = REPO / "test" / "exploration" / "bvm-qb-tline-feedback-dephasing-v1-20260916"
REFERENCE_ROOT = REPO / "test" / "exploration" / "bvm-qb-threshold-ordering-boundary-search-v1-20260911" / "references" / "canonical_baseline"
SOURCE_INPUTS = REPO / "test" / "exploration" / "bvm-qb-threshold-ordering-boundary-search-v1-20260911" / "inputs"
SOLVER = REPO / "build" / "josim-cli"
PLOTTER = REPO / "scripts" / "josim-plot2.py"

CANONICAL = {
    "0011": REFERENCE_ROOT / "0011" / "raw.csv",
    "0111": REFERENCE_ROOT / "0111" / "raw.csv",
}
CANONICAL_DECKS = {
    "0011": REFERENCE_ROOT / "0011" / "deck.cir",
    "0111": REFERENCE_ROOT / "0111" / "deck.cir",
}
PREVIOUS_TLINE_RAW = {
    "0011": PREVIOUS_EXP / "runs" / "TLINE_TD_0P3" / "0011" / "raw.csv",
    "0111": PREVIOUS_EXP / "runs" / "TLINE_TD_0P3" / "0111" / "raw.csv",
}
PREVIOUS_TLINE_DECK = {
    "0011": PREVIOUS_EXP / "runs" / "TLINE_TD_0P3" / "0011" / "deck.cir",
    "0111": PREVIOUS_EXP / "runs" / "TLINE_TD_0P3" / "0111" / "deck.cir",
}
PREVIOUS_TLINE_LOG = {
    "0011": PREVIOUS_EXP / "runs" / "TLINE_TD_0P3" / "0011" / "run.log",
    "0111": PREVIOUS_EXP / "runs" / "TLINE_TD_0P3" / "0111" / "run.log",
}
PREVIOUS_SMOKE = {
    "deck": PREVIOUS_EXP / "smoke" / "tline_syntax" / "deck.cir",
    "raw": PREVIOUS_EXP / "smoke" / "tline_syntax" / "raw.csv",
    "log": PREVIOUS_EXP / "smoke" / "tline_syntax" / "run.log",
}

EXPECTED_HEAD = "ad15dc5abd26d12b618451f9358211ef90b3fa80"
PHI0 = 2.067833848e-15
TAU = 2.0 * math.pi
FOCUS_WINDOW = (110.0, 121.0)
REARM_WINDOW = (121.0, 130.0)
CONTROL_WINDOW = (70.0, 110.0)
WINDOWS_PS = ((0.0, 200.0), (70.0, 110.0), (101.0, 110.0), (110.0, 121.0), (121.0, 130.0), (121.0, 200.0))
TD_PS = 0.3
TD_TOKEN = "0.3p"
STAGE1_Z0 = (12, 24)
STAGE1_MASK = "0011"
STAGE1_RUNS = ("Z0_12_0011", "Z0_24_0011")
FINAL_MARKER = "EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW"
CONTRACT_SENTENCE = "This experiment is governed by docs/EXPERIMENT_CONTRACT.md."
RESULT_LIMIT_BYTES = 500 * 1024
DRIVE_FOLDER_ID = "1--nlY7Nq5ArVPydJNrnQf-EGmwN-undh"
KNOWN_UNAVAILABLE_PROBES = ("I(IB|XBQ1)", "V(IB|XBQ1)")
KNOWN_NONFATAL_WARNING_LINES = (
    "Unknown device/node IB|XBQ1",
    "Cannot store results for this device/node.",
)
REARM_DWELL_SAMPLES = 3

PINNED_REPO_HASHES = {
    SOLVER: "48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2",
    REPO / "src" / "TransmissionLine.cpp": "a26adbd8c48dc384d33e625528a7bd4a18e111c7bf3415ab4077c117bb60a575",
    REPO / "include" / "JoSIM" / "TransmissionLine.hpp": "4e1c30b2736a76c83c8a6acbce41ee78cc0ac4bc4cceede9be2c80a9bdfe66d9",
    REPO / "docs" / "comp_stamps.md": "0e50119a3cac23bdf998ee0561afce48a0acf481a72a7e86ebe10ac09cc7904b",
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
EXPECTED_PREVIOUS_HASHES = {
    PREVIOUS_TLINE_DECK["0011"]: "befe685ba517dbebf73c7b12e7f9f11804a5985677a5235fab7e58e24e4ca117",
    PREVIOUS_TLINE_RAW["0011"]: "f799abc7db071b902d2ba1f0528fc38219c4542b1b662da18595b82900c0607b",
    PREVIOUS_TLINE_LOG["0011"]: "2a099acba96e5cc4af4c2eea2fab3390d8b4ccffb55f7d41ab17e16cb0fc5713",
    PREVIOUS_TLINE_DECK["0111"]: "48a3a4bc7253c88a1f192774808d7d16cf6404f6b4a699a8843374873f6c8640",
    PREVIOUS_TLINE_RAW["0111"]: "a2e170319be878039d43bc730cd462a54cd47f9832c9595c5bbc5590b6817143",
    PREVIOUS_TLINE_LOG["0111"]: "db0ea940478fa2bfdc0bb47a4e2e0aef2965395ccfbae50d750395912db6027f",
    PREVIOUS_SMOKE["deck"]: "d4b3080f86cad1fbf7bb011ec21c9003d99bf279bfb85f256c1c6a77a1c89493",
    PREVIOUS_SMOKE["raw"]: "ca6da2b9b408c389f8f448118dede1dfafbdabb58217554f14635f62085d7f21",
    PREVIOUS_SMOKE["log"]: "7d59f7de1f6f8f159c58d510a97b17c396539e39624d3f3b7bb7e4b1a3bfa8da",
}

JTL_STAGES = range(1, 7)
BVM_JUNCTIONS = ("B_JM1", "B_JM2", "B_JS1", "B_JS2")
BVM_BRANCHES = ("L_M1", "L_M2", "L_M3", "L_PM", "L_S1", "L_S2", "L_S3", "R_S", "L_PSL", "R_SL", "L_SL")
RLOOP_BRANCHES = ("L_S3", "R_S", "L_M3", "L_SL")


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
    return prior.load_raw(path)


def time_indices(trace: Any, start_ps: float, end_ps: float) -> list[int]:
    return [index for index, value in enumerate(trace.time) if start_ps <= value * 1.0e12 < end_ps]


def actual_integral(times: Iterable[float], values: Iterable[float]) -> float:
    time_list = list(times)
    value_list = list(values)
    return sum(0.5 * (value_list[index] + value_list[index + 1]) * (time_list[index + 1] - time_list[index]) for index in range(len(value_list) - 1))


def source_inventory() -> list[dict[str, Any]]:
    records = [
        record_file("runner", SCRIPT, "Z0 rescue runner, gate arithmetic, QA, visualization, and package builder"),
        record_file("global_jjmit_model", SOURCE_INPUTS / "jjmit.cir", "canonical global JJ model closure"),
        record_file("canonical_bvm", SOURCE_INPUTS / "bvm_jm2_connected.cir", "canonical BVM source closure"),
        record_file("canonical_qb_include", SOURCE_INPUTS / "BQ_parameterized_bjs400_rj2.cir", "canonical QB include closure"),
        record_file("canonical_jtl_include", SOURCE_INPUTS / "jtl2.cir", "canonical six-stage JTL closure"),
        record_file("public_qb_hash_guard", REPO / "circuits" / "qb" / "bq_parameterized_v1.cir", "canonical QB hash guard"),
        record_file("transmission_line_source", REPO / "src" / "TransmissionLine.cpp", "T element parser and stamp"),
        record_file("transmission_line_header", REPO / "include" / "JoSIM" / "TransmissionLine.hpp", "four-node T element declaration"),
        record_file("transmission_line_docs", REPO / "docs" / "comp_stamps.md", "lossless TLINE equations"),
        record_file("transmission_line_example", REPO / "test" / "comp" / "tx.cir", "TLINE syntax fixture"),
        record_file("josim_solver", SOLVER, "recorded physical solver"),
        record_file("plotter", PLOTTER, "standard descriptive renderer"),
        record_file("shared_raw_reader", REPO / "scripts" / "bvmtools" / "raw.py", "duplicate-aware raw reader"),
        record_file("shared_phase_tools", REPO / "scripts" / "bvmtools" / "phase.py", "phase unwrap and window helpers"),
        record_file("shared_waveform_tools", REPO / "scripts" / "bvmtools" / "waveform.py", "actual-grid waveform helpers"),
        record_file("previous_tline_experiment_result", PREVIOUS_EXP / "result.json", "read-only previous TLINE result context"),
        record_file("previous_tline_experiment_provenance", PREVIOUS_EXP / "provenance.json", "read-only previous TLINE provenance context"),
    ]
    for mask in ("0011", "0111"):
        records.append(record_file(f"canonical_{mask}_raw", CANONICAL[mask], "read-only canonical raw reference"))
        records.append(record_file(f"canonical_{mask}_deck", CANONICAL_DECKS[mask], "read-only canonical deck reference"))
        records.append(record_file(f"previous_tline_{mask}_deck", PREVIOUS_TLINE_DECK[mask], "read-only Z0=6 TD=0.3 topology reference"))
        records.append(record_file(f"previous_tline_{mask}_raw", PREVIOUS_TLINE_RAW[mask], "read-only Z0=6 TD=0.3 raw reference"))
        records.append(record_file(f"previous_tline_{mask}_log", PREVIOUS_TLINE_LOG[mask], "read-only Z0=6 TD=0.3 log reference"))
    records.extend([
        record_file("previous_tline_smoke_deck", PREVIOUS_SMOKE["deck"], "read-only syntax smoke deck"),
        record_file("previous_tline_smoke_raw", PREVIOUS_SMOKE["raw"], "read-only syntax smoke raw"),
        record_file("previous_tline_smoke_log", PREVIOUS_SMOKE["log"], "read-only syntax smoke log"),
    ])
    return records


def assert_registration() -> None:
    if git_head() != EXPECTED_HEAD:
        raise RuntimeError(f"current HEAD changed: {git_head()} != {EXPECTED_HEAD}")
    if remote_head() != EXPECTED_HEAD:
        raise RuntimeError(f"bvm/master changed: {remote_head()} != {EXPECTED_HEAD}")
    for path, expected in PINNED_REPO_HASHES.items():
        if not path.is_file() or sha256(path) != expected:
            raise RuntimeError(f"registered source changed or missing: {path}")
    for mask, expected in EXPECTED_CANONICAL_RAW_HASHES.items():
        if sha256(CANONICAL[mask]) != expected:
            raise RuntimeError(f"canonical raw changed: {CANONICAL[mask]}")
    for path, expected in EXPECTED_PREVIOUS_HASHES.items():
        if not path.is_file() or sha256(path) != expected:
            raise RuntimeError(f"previous evidence changed or missing: {path}")


def expected_headers() -> set[str]:
    return prior.expected_headers()


def run_id(z0: int, mask: str) -> str:
    return f"Z0_{z0}_{mask}"


def run_dir(z0: int, mask: str) -> Path:
    return EXP / "runs" / f"Z0_{z0}" / mask


def z0_from_key(key: str) -> int:
    return int(key.split("_", 2)[1])


def mask_from_key(key: str) -> str:
    return key.rsplit("_", 1)[1]


def current_run_order(provenance: dict[str, Any]) -> list[str]:
    return list(provenance.get("run_order", []))


def active_indices(mask: str) -> list[int]:
    return [index for index, bit in enumerate(mask, start=1) if bit == "1"]


def transform_prior_deck(mask: str, z0: int) -> str:
    original = PREVIOUS_TLINE_DECK[mask].read_text(encoding="utf-8")
    old_line = "T_BVM_QB TLINE_IN 0 QBIN 0 TD=0.3p Z0=6"
    new_line = f"T_BVM_QB TLINE_IN 0 QBIN 0 TD=0.3p Z0={z0}"
    if original.count(old_line) != 1 or original.count("Z0=6") != 1:
        raise RuntimeError(f"unexpected previous TLINE deck transform anchor for {mask}")
    transformed = original.replace(old_line, new_line)
    if transformed.count(new_line) != 1 or "Z0=6" in transformed:
        raise RuntimeError(f"Z0 transform failed for {mask}, Z0={z0}")
    if transformed.replace(new_line, old_line) != original:
        raise RuntimeError(f"transform changed more than the registered Z0 token for {mask}")
    return transformed


def deck_record(z0: int, mask: str, stage: int) -> dict[str, Any]:
    path = run_dir(z0, mask) / "deck.cir"
    key = run_id(z0, mask)
    return {
        "run_id": key,
        "stage": stage,
        "z0_ohm": z0,
        "TD_ps": TD_PS,
        "mask": mask,
        "path": rel(path),
        "sha256": sha256(path),
        "bytes": path.stat().st_size,
        "source_deck": rel(PREVIOUS_TLINE_DECK[mask]),
        "transform": "previous Z0=6, TD=0.3 deck with only T_BVM_QB Z0 token changed",
    }


def initial_yaml_append(records: dict[str, Any]) -> None:
    path = EXP / "experiment.yaml"
    text = path.read_text(encoding="utf-8").rstrip()
    block = ["", "stage1_deck_registration:"]
    for key in STAGE1_RUNS:
        item = records[key]
        block.extend([
            f"  - run_id: {key}",
            f"    path: {item['path']}",
            f"    sha256: {item['sha256']}",
            f"    bytes: {item['bytes']}",
            f"    Z0_ohm: {item['z0_ohm']}",
            "    TD_ps: 0.3",
            "    mask: 0011",
        ])
    path.write_text(text + "\n" + "\n".join(block) + "\n", encoding="utf-8")


def stage2_yaml_append(item: dict[str, Any]) -> None:
    path = EXP / "experiment.yaml"
    text = path.read_text(encoding="utf-8").rstrip()
    block = [
        "",
        "stage2_deck_registration:",
        f"  - run_id: {item['run_id']}",
        f"    path: {item['path']}",
        f"    sha256: {item['sha256']}",
        f"    bytes: {item['bytes']}",
        f"    Z0_ohm: {item['z0_ohm']}",
        "    TD_ps: 0.3",
        "    mask: 0111",
        "    authorization: stage1 N2_RESCUED gate only",
    ]
    path.write_text(text + "\n" + "\n".join(block) + "\n", encoding="utf-8")


def prepare() -> None:
    assert_registration()
    if EXP.exists():
        existing = {path.name for path in EXP.iterdir()}
        if existing - {"PREFLIGHT.md", "experiment.yaml"}:
            raise RuntimeError(f"refusing to overwrite non-empty experiment directory: {EXP}")
        if not {"PREFLIGHT.md", "experiment.yaml"}.issubset(existing):
            raise RuntimeError(f"experiment directory is incomplete and will not be repaired in place: {EXP}")
    EXP.mkdir(parents=True, exist_ok=True)
    if CONTRACT_SENTENCE not in (EXP / "PREFLIGHT.md").read_text(encoding="utf-8"):
        raise RuntimeError("PREFLIGHT.md is missing the experiment contract sentence")
    (EXP / "runs").mkdir()
    (EXP / "plots").mkdir()
    (EXP / "analysis").mkdir()
    source_records = source_inventory()
    registered: dict[str, Any] = {}
    for z0 in STAGE1_Z0:
        key = run_id(z0, STAGE1_MASK)
        directory = run_dir(z0, STAGE1_MASK)
        directory.mkdir(parents=True, exist_ok=True)
        deck = directory / "deck.cir"
        deck.write_text(transform_prior_deck(STAGE1_MASK, z0), encoding="utf-8")
        registered[key] = deck_record(z0, STAGE1_MASK, 1)
    initial_yaml_append(registered)
    provenance = {
        "schema": "bvm-qb-tline-z0-rescue-gate-provenance-v1",
        "experiment_id": EXP.name,
        "created_at": now(),
        "registration_head": EXPECTED_HEAD,
        "remote_bvm_master_at_registration": EXPECTED_HEAD,
        "current_head_at_prepare": git_head(),
        "contract_sentence": CONTRACT_SENTENCE,
        "scientific_review_authorized": False,
        "mechanical_analysis_performed": False,
        "bounded_experiment_interpretation_performed": False,
        "independent_scientific_review_performed": False,
        "scientific_interpretation_performed": False,
        "solver": replay_base.solver_context(),
        "source_closure": source_records,
        "canonical_reference_raw_hashes": EXPECTED_CANONICAL_RAW_HASHES,
        "previous_reference_hashes": {rel(path): digest for path, digest in EXPECTED_PREVIOUS_HASHES.items()},
        "frozen": {
            "topology": "4xBVM -> COMMON_SL -> JSL1..8 -> TLINE_IN -> ideal lossless TLINE -> QBIN -> canonical QB -> JTL1..6 -> 10 ohm terminal",
            "TD_ps": TD_PS,
            "Z0_engineering_diagnostic_values_ohm": [6, 12, 24],
            "Z0_interpretation": "engineering diagnostic values only; not matching values or measured characteristic impedance",
            "mask_stage1": STAGE1_MASK,
            "mask_stage2_conditional": "0111",
            "time_step_ps": 0.1,
            "stop_time_ps": 200.0,
            "stored_grid": "actual JoSIM CSV timestamps; expected 1999 samples from 0 to 199.9 ps",
            "analysis_windows_ps": [list(window) for window in WINDOWS_PS],
            "window_semantics": "half-open actual stored timestamps; no interpolation/resampling",
            "canonical_qb_unchanged": True,
            "canonical_bvm_unchanged": True,
            "canonical_jtl_terminal_unchanged": True,
            "no_amplitude_scaling": True,
            "no_matching_network": True,
            "no_transformer": True,
            "no_read_extension": True,
            "no_timestep_sweep": True,
            "no_sentinel": True,
        },
        "syntax_gate": {
            "status": "PASS",
            "authority": "previous experiment TLINE syntax/delay smoke; read-only reference",
            "syntax": "Tlabel Vi+ Vi- Vo+ Vo- TD=value Z0=value",
            "smoke_deck": rel(PREVIOUS_SMOKE["deck"]),
            "smoke_raw": rel(PREVIOUS_SMOKE["raw"]),
            "smoke_raw_sha256": EXPECTED_PREVIOUS_HASHES[PREVIOUS_SMOKE["raw"]],
            "measured_delay_ps": 0.3,
            "measured_delay_samples": 3,
            "no_new_smoke_solve": True,
        },
        "authorized_matrix": {
            "stage1_max_new_physical_solves": 2,
            "conditional_stage2_max_new_physical_solves": 1,
            "absolute_max_new_physical_solves": 3,
            "stage1": [{"run_id": run_id(z0, STAGE1_MASK), "Z0_ohm": z0, "TD_ps": TD_PS, "mask": STAGE1_MASK} for z0 in STAGE1_Z0],
            "conditional_stage2": "only one 0111 run at the single closest-to-canonical rescue Z0",
            "forbidden_additions": ["N3 unless rescue PASS", "0001", "1111", "TD=0.6 ps", "other Z0", "QB change", "matching", "transformer", "sentinel", "timestep sweep"],
        },
        "registered_decks": registered,
        "runs": {},
        "run_order": [],
        "execution": {"new_physical_solve_authorized": 3, "actual_new_physical_solve_count": 0, "solver_invocation_count": 0, "stage1_count": 0, "stage2_count": 0},
        "registered_metrics": {
            "qb_response": "BJ1/BJ2 +0.5 and +1.5 navigation, ordered BJ1->BJ2->JTL1..6 candidate count; terminal corroboration only",
            "rearm": "I(L1), I(L2), BJ1/BJ2, reset-voltage actual-grid integrals in [121,130) ps",
            "source_recovery": "I(B_JSL8), I(LIN|XBQ1), signed area, positive->negative crossing, negative dwell/min, COMMON_SL, QBIN",
            "bvm_rloop": "active JS1/JS2 [110,121) p2p and same-JJ phase/voltage-area; LS3, R_S, LM3, L_SL",
            "phase": "P raw radians; independent continuous unwrap then rad/(2*pi) navigation only",
            "integration": "same JJ/endpoints/direction/window; trapezoid on actual time grid",
            "tline": "near-port/far-side waveform features; no incident/reflected decomposition; TD is not measured return delay",
        },
        "probe_policy": {
            "required_headers": sorted(expected_headers()),
            "known_unavailable": list(KNOWN_UNAVAILABLE_PROBES),
            "known_unavailable_reason": "inherited I(IB|XBQ1)/V(IB|XBQ1) public print lookup is not resolved by JoSIM; no metric uses it",
            "tline_current": "I(T_BVM_QB) is exposed first-port branch current; I(LIN|XBQ1) is receiver-side QBIN KCL current",
        },
        "transformations": [{
            "name": "previous_tline_deck_Z0_only",
            "registered_change": "replace exactly T_BVM_QB ... TD=0.3p Z0=6 with TD=0.3p Z0=12 or Z0=24",
            "all_other_deck_lines_identical": True,
            "raw_transformations": [],
            "interpolation": False,
            "scaling": False,
            "time_shift": False,
        }],
        "analysis": {"status": "PENDING"},
        "qa": {"status": "PENDING"},
        "visualization": {"status": "PENDING"},
        "package": {"status": "PENDING", "drive_file_id": None, "drive_url": None},
        "stop": {"final_marker": None, "automatic_follow_up": False},
    }
    write_json(EXP / "provenance.json", provenance)
    result = {
        "schema": "bvm-qb-tline-z0-rescue-gate-result-v1",
        "experiment_id": EXP.name,
        "generated_at": now(),
        "status": "PREFLIGHT_PASS_STAGE1_PENDING",
        "artifact_status": "PENDING",
        "scientific_review_authorized": False,
        "mechanical_analysis_performed": False,
        "bounded_experiment_interpretation_performed": False,
        "independent_scientific_review_performed": False,
        "execution": provenance["execution"],
        "runs": {},
        "outcome": {"status": "PENDING", "classification": None},
        "unknown": ["whether Z0 change rescues N2", "whether any N3 trajectory is materially dephased", "timestep/solver convergence", "physical characteristic impedance", "SFQ event identity/count"],
        "stop": {"final_marker": None, "automatic_follow_up": False},
    }
    write_json(EXP / "result.json", result)
    (EXP / "RESULT.md").write_text("# BVM -> QB TLINE Z0 rescue gate\n\nPreflight passed. Stage 1 contains exactly two new N2 decks; no raw has been produced yet.\n", encoding="utf-8")
    print(json.dumps({"status": "PREFLIGHT_PASS", "experiment": rel(EXP), "stage1_runs": STAGE1_RUNS, "head": EXPECTED_HEAD}, ensure_ascii=False, indent=2))


def warning_lines(log: Path) -> list[str]:
    if not log.is_file():
        return ["missing_log"]
    return [line.strip() for line in log.read_text(errors="replace").splitlines() if any(token in line for token in ("Missing model:", "Unknown device/node", "Cannot store results", "Error", "error"))]


def run_one(key: str, stage: int) -> None:
    provenance = read_json(EXP / "provenance.json")
    record = provenance["registered_decks"].get(key)
    if not record:
        raise RuntimeError(f"run is not registered: {key}")
    deck = REPO / record["path"]
    run_path = deck.parent
    raw = run_path / "raw.csv"
    log = run_path / "run.log"
    if raw.exists() or log.exists():
        raise RuntimeError(f"refusing overwrite/retry of immutable run: {key}")
    if sha256(deck) != record["sha256"]:
        raise RuntimeError(f"registered deck changed: {key}")
    command = [str(SOLVER), "-a", "1", "-o", str(raw), str(deck)]
    started = now()
    with log.open("x", encoding="utf-8") as stream:
        stream.write(f"experiment={EXP.name}\nrun_id={key}\nstage={stage}\nstarted_at={started}\ncommand={' '.join(command)}\n")
        stream.flush()
        completed = subprocess.run(command, cwd=REPO, stdout=stream, stderr=subprocess.STDOUT, check=False)
        finished = now()
        stream.write(f"finished_at={finished}\nexit_code={completed.returncode}\n")
    run_record: dict[str, Any] = {
        "run_id": key,
        "stage": stage,
        "Z0_ohm": record["z0_ohm"],
        "TD_ps": TD_PS,
        "mask": record["mask"],
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
        provenance["runs"][key] = run_record
        provenance["run_order"].append(key)
        provenance["execution"]["actual_new_physical_solve_count"] = len(provenance["run_order"])
        provenance["execution"]["solver_invocation_count"] = len(provenance["run_order"])
        provenance["execution"][f"stage{stage}_count"] += 1
        provenance["execution_status"] = "SOLVER_FAILURE_STOP"
        write_json(EXP / "provenance.json", provenance)
        raise RuntimeError(f"solver failed for {key}; failure preserved and no retry authorized")
    try:
        trace = load_raw(raw)
        missing = sorted(expected_headers() - set(trace.headers))
        run_record["raw"] = {
            "path": rel(raw),
            "sha256": sha256(raw),
            "bytes": raw.stat().st_size,
            "sample_count": trace.sample_count,
            "time_start_ps": trace.time[0] * 1.0e12,
            "time_end_ps": trace.time[-1] * 1.0e12,
            "grid": replay_base.finite_grid_qa(trace),
            "missing_required_probes": missing,
            "known_unavailable_probes": [signal for signal in KNOWN_UNAVAILABLE_PROBES if signal not in trace.headers],
        }
        run_record["solver_warning_lines"] = warning_lines(log)
        run_record["known_nonfatal_probe_warnings"] = [line for line in run_record["solver_warning_lines"] if line in KNOWN_NONFATAL_WARNING_LINES]
        run_record["unexpected_solver_warning_lines"] = [line for line in run_record["solver_warning_lines"] if line not in KNOWN_NONFATAL_WARNING_LINES]
        run_record["missing_required_probes"] = missing
        run_record["execution_status"] = "RUN_PASS" if not missing else "RUN_PASS_MISSING_PROBES"
    except Exception as exc:
        run_record["execution_status"] = "RAW_PARSE_FAILURE"
        run_record["raw_parse_error"] = str(exc)
        run_record["raw"] = {"path": rel(raw), "sha256": sha256(raw), "bytes": raw.stat().st_size}
        provenance["runs"][key] = run_record
        provenance["run_order"].append(key)
        provenance["execution"]["actual_new_physical_solve_count"] = len(provenance["run_order"])
        provenance["execution"]["solver_invocation_count"] = len(provenance["run_order"])
        provenance["execution"][f"stage{stage}_count"] += 1
        provenance["execution_status"] = "RAW_FAILURE_STOP"
        write_json(EXP / "provenance.json", provenance)
        raise RuntimeError(f"raw parse failed for {key}; failure preserved") from exc
    provenance["runs"][key] = run_record
    provenance["run_order"].append(key)
    provenance["execution"]["actual_new_physical_solve_count"] = len(provenance["run_order"])
    provenance["execution"]["solver_invocation_count"] = len(provenance["run_order"])
    provenance["execution"][f"stage{stage}_count"] += 1
    write_json(EXP / "provenance.json", provenance)
    if missing:
        provenance["execution_status"] = "RAW_PROBE_FAILURE_STOP"
        write_json(EXP / "provenance.json", provenance)
        raise RuntimeError(f"missing required probes for {key}: {missing}")


def execute_stage1() -> None:
    provenance = read_json(EXP / "provenance.json")
    if current_run_order(provenance):
        raise RuntimeError("stage 1 execution already has recorded runs; refusing overwrite/retry")
    if git_head() != EXPECTED_HEAD or remote_head() != EXPECTED_HEAD:
        raise RuntimeError("HEAD/remote moved after registration")
    for item in provenance["source_closure"]:
        path = REPO / item["path"]
        if sha256(path) != item["sha256"]:
            raise RuntimeError(f"source closure changed before execution: {path}")
    for key in STAGE1_RUNS:
        run_one(key, 1)
    provenance = read_json(EXP / "provenance.json")
    provenance["execution_status"] = "STAGE1_RUNS_COMPLETE"
    write_json(EXP / "provenance.json", provenance)
    result = read_json(EXP / "result.json")
    result["status"] = "STAGE1_RUNS_COMPLETE_ANALYSIS_PENDING"
    result["artifact_status"] = "VALID"
    result["execution"] = provenance["execution"]
    result["runs"] = compact_run_records(provenance)
    write_json(EXP / "result.json", result)
    print(json.dumps({"status": "STAGE1_RUN_PASS", "run_order": STAGE1_RUNS}, ensure_ascii=False, indent=2))


def materialize_stage2(selected_z0: int) -> None:
    provenance = read_json(EXP / "provenance.json")
    if provenance.get("outcome", {}).get("classification") != "N2_RESCUED":
        raise RuntimeError("stage 2 materialization requires N2_RESCUED")
    if any(mask_from_key(key) == "0111" for key in current_run_order(provenance)):
        raise RuntimeError("stage 2 already materialized")
    if selected_z0 not in STAGE1_Z0:
        raise RuntimeError(f"selected Z0 is outside registered rescue points: {selected_z0}")
    key = run_id(selected_z0, "0111")
    directory = run_dir(selected_z0, "0111")
    directory.mkdir(parents=True, exist_ok=False)
    deck = directory / "deck.cir"
    deck.write_text(transform_prior_deck("0111", selected_z0), encoding="utf-8")
    record = deck_record(selected_z0, "0111", 2)
    provenance["registered_decks"][key] = record
    provenance["stage2_authorization"] = {
        "status": "AUTHORIZED_BY_STAGE1_RESCUE_GATE",
        "selected_Z0_ohm": selected_z0,
        "selection_rule": "single smallest normalized actual-grid recovery/re-arm distance to canonical N2",
        "authorized_run": key,
        "no_second_N3_Z0": True,
        "authorized_at": now(),
    }
    write_json(EXP / "provenance.json", provenance)
    stage2_yaml_append(record)
    print(json.dumps({"status": "STAGE2_DECK_REGISTERED", "run_id": key, "deck": record}, ensure_ascii=False, indent=2))


def execute_stage2() -> None:
    provenance = read_json(EXP / "provenance.json")
    key = provenance.get("stage2_authorization", {}).get("authorized_run")
    if not key or key not in provenance.get("registered_decks", {}):
        raise RuntimeError("stage 2 is not authorized/materialized")
    if current_run_order(provenance) != list(STAGE1_RUNS):
        raise RuntimeError("stage 2 requires exactly the two completed stage 1 runs")
    run_one(key, 2)
    provenance = read_json(EXP / "provenance.json")
    provenance["execution_status"] = "ALL_AUTHORIZED_RUNS_COMPLETE"
    write_json(EXP / "provenance.json", provenance)
    result = read_json(EXP / "result.json")
    result["status"] = "ALL_AUTHORIZED_RUNS_COMPLETE_ANALYSIS_PENDING"
    result["artifact_status"] = "VALID"
    result["execution"] = provenance["execution"]
    result["runs"] = compact_run_records(provenance)
    write_json(EXP / "result.json", result)
    print(json.dumps({"status": "STAGE2_RUN_PASS", "run_order": current_run_order(provenance)}, ensure_ascii=False, indent=2))


def unwrap(values: Iterable[float]) -> list[float]:
    return prior.unwrap(values)


def zero_crossing_count(values: Iterable[float]) -> int:
    return prior.zero_crossing_count(values)


def waveform_stats(trace: Any, signal: str, window: tuple[float, float]) -> dict[str, Any]:
    return prior.waveform_stats(trace, signal, *window)


def phase_navigation(trace: Any, signal: str) -> dict[str, Any]:
    return prior.phase_navigation(trace, signal)


def phase_area_crosscheck(trace: Any, phase_signal: str, voltage_signal: str) -> dict[str, Any]:
    return prior.phase_area_crosscheck(trace, phase_signal, voltage_signal, FOCUS_WINDOW)


def ordered_navigation_oracle(trace: Any) -> dict[str, Any]:
    return prior.ordered_navigation_oracle(trace)


def local_features(trace: Any, signal: str, window: tuple[float, float]) -> list[dict[str, Any]]:
    return prior.local_features(trace, signal, window)


def compact_waveform(item: dict[str, Any]) -> dict[str, Any]:
    keys = ("signal", "unit", "minimum", "maximum", "p2p", "peak_abs", "peak_value", "time_of_peak_abs_ps", "signed_area", "absolute_area", "positive_area", "negative_area", "positive_sample_fraction", "negative_sample_fraction", "zero_crossing_count", "half_abs_peak_width")
    return {key: item.get(key) for key in keys}


def signal_stats_if_present(trace: Any, signal: str, window: tuple[float, float]) -> dict[str, Any] | None:
    return compact_waveform(waveform_stats(trace, signal, window)) if signal in trace.headers else None


def sign_metrics(trace: Any, signal: str, window: tuple[float, float], dwell_samples: int = REARM_DWELL_SAMPLES) -> dict[str, Any]:
    if signal not in trace.headers:
        return {"status": "UNKNOWN", "signal": signal, "window_ps": list(window)}
    indices = time_indices(trace, *window)
    values = trace.column(signal)
    selected = [float(values[index]) for index in indices]
    times = [float(trace.time[index]) for index in indices]
    def first_transition(from_sign: int, to_sign: int) -> float | None:
        previous = 0
        for position, value in enumerate(selected):
            sign = 1 if value > 0.0 else -1 if value < 0.0 else 0
            if sign == 0:
                continue
            if previous == from_sign and sign == to_sign:
                return times[position] * 1.0e12
            previous = sign
        return None
    def sustained_negative_positive() -> float | None:
        previous = 0
        for position, value in enumerate(selected):
            sign = 1 if value > 0.0 else -1 if value < 0.0 else 0
            if sign == 0:
                continue
            if previous == -1 and sign == 1:
                tail = selected[position:position + dwell_samples]
                if len(tail) == dwell_samples and all(item > 0.0 for item in tail):
                    return times[position] * 1.0e12
            previous = sign
        return None
    positive_dwell = sum((times[index + 1] - times[index]) * 1.0e12 for index in range(len(times) - 1) if selected[index] > 0.0)
    negative_dwell = sum((times[index + 1] - times[index]) * 1.0e12 for index in range(len(times) - 1) if selected[index] < 0.0)
    return {
        "status": "DERIVED",
        "signal": signal,
        "window_ps": list(window),
        "sample_count": len(selected),
        "minimum": min(selected) if selected else None,
        "maximum": max(selected) if selected else None,
        "zero_sign_crossings": zero_crossing_count(selected),
        "first_negative_to_positive_crossing_ps": first_transition(-1, 1),
        "first_positive_to_negative_crossing_ps": first_transition(1, -1),
        "first_sustained_negative_to_positive_crossing_ps": sustained_negative_positive(),
        "positive_dwell_ps": positive_dwell,
        "negative_dwell_ps": negative_dwell,
        "positive_sample_fraction": sum(value > 0.0 for value in selected) / len(selected) if selected else None,
        "negative_sample_fraction": sum(value < 0.0 for value in selected) / len(selected) if selected else None,
        "actual_grid": True,
        "sustained_definition": f"crossing followed by {dwell_samples} consecutive stored samples > 0",
    }


def voltage_integrals(trace: Any, signals: Iterable[str], window: tuple[float, float]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for signal in signals:
        if signal not in trace.headers:
            output[signal] = {"status": "UNKNOWN", "signal": signal, "window_ps": list(window)}
            continue
        indices = time_indices(trace, *window)
        times = [trace.time[index] for index in indices]
        values = [trace.column(signal)[index] for index in indices]
        area = actual_integral(times, values)
        output[signal] = {
            "status": "DERIVED",
            "signal": signal,
            "window_ps": list(window),
            "sample_count": len(values),
            "signed_area_V_s": area,
            "signed_area_mV_ps": area * 1.0e15,
            "actual_grid_trapezoid": True,
            "not_an_SFQ_quantity": True,
        }
    return output


def port_features(trace: Any) -> dict[str, Any]:
    required = ("V(TLINE_IN,0)", "I(T_BVM_QB)", "V(QBIN)", "I(LIN|XBQ1)")
    if not all(signal in trace.headers for signal in required):
        return {"status": "UNKNOWN", "missing": [signal for signal in required if signal not in trace.headers], "specified_TD_is_not_measured_return_delay": True}
    result = prior.tline_timing_features(trace, TD_PS)
    result["specified_TD_is_not_measured_return_delay"] = True
    return result


def bvm_metrics(trace: Any, mask: str) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for index in active_indices(mask):
        instance = f"XBVM{index}"
        phase_nav = {}
        phase_area = {}
        for element in BVM_JUNCTIONS:
            p_signal = f"P({element}|{instance})"
            if p_signal not in trace.headers:
                continue
            phase_nav[p_signal] = phase_navigation(trace, p_signal)
            if element in ("B_JS1", "B_JS2") and f"V({element}|{instance})" in trace.headers:
                phase_area[p_signal] = phase_area_crosscheck(trace, p_signal, f"V({element}|{instance})")
        focus = {}
        rearm = {}
        for element in BVM_JUNCTIONS:
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
        output[instance] = {
            "phase_navigation": phase_nav,
            "phase_area": phase_area,
            "focus_waveforms": focus,
            "rearm_waveforms": rearm,
            "rloop_focus": {signal: focus[signal] for element in RLOOP_BRANCHES for kind in ("I", "V") for signal in (f"{kind}({element}|{instance})",) if signal in focus},
            "jm_follower_navigation": {signal: phase_nav[signal] for signal in phase_nav if any(element in signal for element in ("B_JM1", "B_JM2"))},
        }
    return output


def jsl_metrics(trace: Any) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for number in range(1, 9):
        output[f"B_JSL{number}"] = {
            "focus": {f"{kind}(B_JSL{number})": compact_waveform(waveform_stats(trace, f"{kind}(B_JSL{number})", FOCUS_WINDOW)) for kind in ("P", "V", "I") if f"{kind}(B_JSL{number})" in trace.headers},
            "rearm": {f"{kind}(B_JSL{number})": compact_waveform(waveform_stats(trace, f"{kind}(B_JSL{number})", REARM_WINDOW)) for kind in ("P", "V", "I") if f"{kind}(B_JSL{number})" in trace.headers},
        }
    return output


def qb_metrics(trace: Any) -> dict[str, Any]:
    signals = (
        "V(QBIN)", "V(QBOUT)", "I(LIN|XBQ1)", "V(LIN|XBQ1)",
        "I(L1|XBQ1)", "V(L1|XBQ1)", "I(L2|XBQ1)", "V(L2|XBQ1)",
        "I(L3|XBQ1)", "V(L3|XBQ1)", "I(RJ1|XBQ1)", "V(RJ1|XBQ1)",
        "I(RJ2|XBQ1)", "V(RJ2|XBQ1)",
        "P(BJS|XBQ1)", "V(BJS|XBQ1)", "I(BJS|XBQ1)",
        "P(BJ1|XBQ1)", "V(BJ1|XBQ1)", "I(BJ1|XBQ1)",
        "P(BJ2|XBQ1)", "V(BJ2|XBQ1)", "I(BJ2|XBQ1)",
    )
    return {
        "focus": {signal: compact_waveform(waveform_stats(trace, signal, FOCUS_WINDOW)) for signal in signals if signal in trace.headers},
        "rearm": {signal: compact_waveform(waveform_stats(trace, signal, REARM_WINDOW)) for signal in signals if signal in trace.headers},
        "rearm_signs": {signal: sign_metrics(trace, signal, REARM_WINDOW) for signal in ("I(L1|XBQ1)", "I(L2|XBQ1)")},
        "navigation": {signal: phase_navigation(trace, signal) for signal in ("P(BJ1|XBQ1)", "P(BJ2|XBQ1)") if signal in trace.headers},
        "reset_voltage_integrals": voltage_integrals(trace, ("V(L1|XBQ1)", "V(L2|XBQ1)", "V(L3|XBQ1)", "V(RJ1|XBQ1)", "V(RJ2|XBQ1)"), REARM_WINDOW),
        "ordered_navigation_oracle": ordered_navigation_oracle(trace),
    }


def jtl_metrics(trace: Any) -> dict[str, Any]:
    return {
        "navigation": {f"P(B01|XJTL1_{stage})": phase_navigation(trace, f"P(B01|XJTL1_{stage})") for stage in JTL_STAGES},
        "focus": {signal: compact_waveform(waveform_stats(trace, signal, FOCUS_WINDOW)) for stage in JTL_STAGES for signal in (f"P(B01|XJTL1_{stage})", f"V(B01|XJTL1_{stage})", f"I(B01|XJTL1_{stage})", f"P(B02|XJTL1_{stage})", f"V(B02|XJTL1_{stage})", f"I(B02|XJTL1_{stage})", f"V(JTL{stage}_OUT)") if signal in trace.headers},
        "terminal": {signal: compact_waveform(waveform_stats(trace, signal, FOCUS_WINDOW)) for signal in ("I(R_TERM)", "V(JTL6_OUT)") if signal in trace.headers},
    }


def source_recovery_metrics(trace: Any) -> dict[str, Any]:
    return {
        "focus": {signal: compact_waveform(waveform_stats(trace, signal, FOCUS_WINDOW)) for signal in ("I(B_JSL8)", "I(T_BVM_QB)", "I(LIN|XBQ1)", "V(COMMON_SL)", "V(QBIN)") if signal in trace.headers},
        "rearm": {signal: compact_waveform(waveform_stats(trace, signal, REARM_WINDOW)) for signal in ("I(B_JSL8)", "I(T_BVM_QB)", "I(LIN|XBQ1)", "V(COMMON_SL)", "V(QBIN)") if signal in trace.headers},
        "rearm_signs": {signal: sign_metrics(trace, signal, REARM_WINDOW) for signal in ("I(B_JSL8)", "I(T_BVM_QB)", "I(LIN|XBQ1)")},
        "rearm_integrals": voltage_integrals(trace, ("V(COMMON_SL)", "V(QBIN)"), REARM_WINDOW),
    }


def analyze_trace(label: str, mask: str, trace: Any, raw_path: Path, z0: int | None = None) -> dict[str, Any]:
    phase_area = {}
    for index in active_indices(mask):
        instance = f"XBVM{index}"
        for element in ("B_JS1", "B_JS2"):
            p_signal = f"P({element}|{instance})"
            v_signal = f"V({element}|{instance})"
            if p_signal in trace.headers and v_signal in trace.headers:
                phase_area[p_signal] = phase_area_crosscheck(trace, p_signal, v_signal)
    full_focus_signals = ("V(COMMON_SL)", "V(TLINE_IN,0)", "I(T_BVM_QB)", "V(QBIN)", "I(LIN|XBQ1)", "V(QBOUT)", "V(JTL6_OUT)", "I(R_TERM)")
    return {
        "run_id": label,
        "mask": mask,
        "Z0_ohm": z0,
        "TD_ps": TD_PS if z0 is not None else None,
        "raw_path": rel(raw_path),
        "raw_sha256": sha256(raw_path),
        "grid": replay_base.finite_grid_qa(trace),
        "phase_navigation": {f"P({element}|XBVM{index})": phase_navigation(trace, f"P({element}|XBVM{index})") for index in active_indices(mask) for element in BVM_JUNCTIONS if f"P({element}|XBVM{index})" in trace.headers},
        "phase_area": phase_area,
        "bvm": bvm_metrics(trace, mask),
        "jsl": jsl_metrics(trace),
        "qb": qb_metrics(trace),
        "jtl": jtl_metrics(trace),
        "source_recovery": source_recovery_metrics(trace),
        "port_features": port_features(trace),
        "focus_waveforms": {signal: compact_waveform(waveform_stats(trace, signal, FOCUS_WINDOW)) for signal in full_focus_signals if signal in trace.headers},
        "rearm_waveforms": {signal: compact_waveform(waveform_stats(trace, signal, REARM_WINDOW)) for signal in full_focus_signals if signal in trace.headers},
        "control_window": {signal: compact_waveform(waveform_stats(trace, signal, CONTROL_WINDOW)) for signal in ("V(QBIN)", "V(QBOUT)", "V(JTL6_OUT)", "I(R_TERM)") if signal in trace.headers},
        "phase_semantics": "raw radians; independent continuous unwrap/(2*pi) navigation only",
        "area_semantics": "same JJ, same endpoints, same direction, actual-grid trapezoid; not an SFQ count",
        "interpretation_status": "DERIVED raw metrics; no SFQ or mechanism claim",
    }


def normalized_distance(reference: Any, candidate: Any, signals: Iterable[str], window: tuple[float, float]) -> dict[str, Any]:
    per_signal: dict[str, Any] = {}
    scores: list[float] = []
    indices = time_indices(reference, *window)
    for signal in signals:
        if signal not in reference.headers or signal not in candidate.headers:
            per_signal[signal] = {"status": "UNKNOWN"}
            continue
        left = [float(reference.column(signal)[index]) for index in indices]
        right = [float(candidate.column(signal)[index]) for index in indices]
        scale = max(max(left) - min(left), max(abs(value) for value in left), 1.0e-30)
        rms = math.sqrt(sum((a - b) * (a - b) for a, b in zip(left, right)) / len(left))
        normalized = rms / scale
        per_signal[signal] = {"status": "DERIVED", "window_ps": list(window), "sample_count": len(left), "rms_raw": rms, "reference_scale_raw": scale, "normalized_rms": normalized, "actual_grid": True}
        scores.append(normalized)
    return {"status": "DERIVED" if scores else "UNKNOWN", "window_ps": list(window), "signals": per_signal, "mean_normalized_rms": sum(scores) / len(scores) if scores else None, "signal_count": len(scores), "selection_role": "closest-to-canonical recovery/re-arm trajectory"}


def gate_entry(candidate: dict[str, Any], canonical: dict[str, Any], previous: dict[str, Any], canonical_trace: Any, candidate_trace: Any) -> dict[str, Any]:
    oracle = candidate["qb"]["ordered_navigation_oracle"]
    canonical_oracle = canonical["qb"]["ordered_navigation_oracle"]
    canonical_count = canonical_oracle["ordered_navigation_candidate_count"]
    first_record = oracle["records"][0] if oracle["records"] else {"ordered": False}
    second_record = oracle["records"][1] if len(oracle["records"]) > 1 else {"ordered": False}
    l1 = candidate["qb"]["rearm_signs"].get("I(L1|XBQ1)", {})
    terminal = candidate["jtl"]["terminal"]
    terminal_present = bool(terminal.get("V(JTL6_OUT)"))
    source = candidate["source_recovery"]["rearm_signs"].get("I(B_JSL8)", {})
    gate = {
        "Z0_ohm": candidate["Z0_ohm"],
        "canonical_ordered_candidate_count": canonical_count,
        "ordered_candidate_count": oracle["ordered_navigation_candidate_count"],
        "first_response_intact": bool(first_record.get("ordered")),
        "second_response_recovered": bool(oracle["ordered_navigation_candidate_count"] >= canonical_count and second_record.get("ordered")),
        "first_bj1_plus_0p5_ps": oracle["navigation"]["BJ1"]["positive_threshold_navigation_times_ps"].get("0.5"),
        "first_bj2_plus_0p5_ps": oracle["navigation"]["BJ2"]["positive_threshold_navigation_times_ps"].get("0.5"),
        "second_bj1_plus_1p5_ps": oracle["navigation"]["BJ1"]["positive_threshold_navigation_times_ps"].get("1.5"),
        "second_bj2_plus_1p5_ps": oracle["navigation"]["BJ2"]["positive_threshold_navigation_times_ps"].get("1.5"),
        "rearm_l1_sustained_negative_to_positive_ps": l1.get("first_sustained_negative_to_positive_crossing_ps"),
        "rearm_l1_positive_dwell_ps": l1.get("positive_dwell_ps"),
        "rearm_l1_zero_sign_crossings": l1.get("zero_sign_crossings"),
        "source_bjsl8_positive_to_negative_ps": source.get("first_positive_to_negative_crossing_ps"),
        "source_bjsl8_negative_dwell_ps": source.get("negative_dwell_ps"),
        "terminal_corrob_signal_present": terminal_present,
        "not_terminal_only_oracle": True,
        "ringing_or_new_switching_screen": {
            "status": "PASS_DESCRIPTIVE_SCREEN" if bool(second_record.get("ordered")) and terminal_present and l1.get("first_sustained_negative_to_positive_crossing_ps") is not None else "FAIL_OR_UNKNOWN",
            "basis": "second response is required to be internally ordered BJ1->BJ2->JTL1..6 and accompanied by L1 re-arm; terminal is corroboration only",
            "not_a_switching_or_SFQ_certification": True,
        },
        "recovery_distance": normalized_distance(canonical_trace, candidate_trace, ("I(L1|XBQ1)", "I(L2|XBQ1)", "V(L1|XBQ1)", "V(L2|XBQ1)", "I(B_JSL8)", "I(LIN|XBQ1)", "V(COMMON_SL)", "V(QBIN)"), REARM_WINDOW),
    }
    gate["rescue_pass"] = bool(
        gate["first_response_intact"]
        and gate["second_response_recovered"]
        and gate["ordered_candidate_count"] == canonical_count
        and gate["rearm_l1_sustained_negative_to_positive_ps"] is not None
        and float(gate["rearm_l1_positive_dwell_ps"] or 0.0) > 0.0
        and gate["ringing_or_new_switching_screen"]["status"] == "PASS_DESCRIPTIVE_SCREEN"
    )
    gate["previous_Z0_6_ordered_candidate_count"] = previous["qb"]["ordered_navigation_oracle"]["ordered_navigation_candidate_count"]
    return gate


def independent_csv(path: Path) -> tuple[list[float], dict[str, list[float]]]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        headers = reader.fieldnames or []
        if len(headers) != len(set(headers)):
            raise RuntimeError(f"duplicate header in independent read: {path}")
        rows = list(reader)
    times = [float(row["time"]) for row in rows]
    columns = {signal: [float(row[signal]) for row in rows] for signal in headers if signal != "time"}
    return times, columns


def independent_unwrap(values: list[float]) -> list[float]:
    output = [values[0]]
    previous = values[0]
    for value in values[1:]:
        delta = value - previous
        while delta > math.pi:
            delta -= TAU
        while delta < -math.pi:
            delta += TAU
        output.append(output[-1] + delta)
        previous = value
    return output


def independent_navigation_count(times: list[float], columns: dict[str, list[float]]) -> int:
    names = ["P(BJ1|XBQ1)", "P(BJ2|XBQ1)", *[f"P(B01|XJTL1_{stage})" for stage in JTL_STAGES]]
    unwrapped = {name: independent_unwrap(columns[name]) for name in names}
    base = next(index for index, value in enumerate(times) if value * 1.0e12 >= 101.0)
    count = 0
    for threshold in (0.5, 1.5, 2.5, 3.5, 4.5):
        chain = [next((times[index] * 1.0e12 for index in range(base, len(times)) if (unwrapped[name][index] - unwrapped[name][base]) / TAU >= threshold), None) for name in names]
        if all(value is not None for value in chain) and all(left < right for left, right in zip(chain, chain[1:])):
            count += 1
        else:
            break
    return count


def independent_phase_area(times: list[float], columns: dict[str, list[float]], mask: str, element: str) -> dict[str, Any]:
    index = active_indices(mask)[0]
    p_signal = f"P({element}|XBVM{index})"
    v_signal = f"V({element}|XBVM{index})"
    phase = independent_unwrap(columns[p_signal])
    focus = [index for index, value in enumerate(times) if 110.0 <= value * 1.0e12 < 121.0]
    area = actual_integral([times[index] for index in focus], [columns[v_signal][index] for index in focus]) / PHI0
    phase_delta = (phase[focus[-1]] - phase[focus[0]]) / TAU
    return {"phase_delta_turns": phase_delta, "voltage_area_over_Phi0_turns": area, "residual_turns": phase_delta - area}


def independent_recalculation(paths: dict[str, Path], masks: dict[str, str]) -> dict[str, Any]:
    data = {label: independent_csv(path) for label, path in paths.items()}
    output: dict[str, Any] = {"status": "PASS", "method": "fresh csv.DictReader + independent unwrap/trapezoid/order loops", "grid_match": {}, "ordered_navigation_candidate_count": {}, "phase_area": {}}
    for label, (times, columns) in data.items():
        output["grid_match"][label] = len(times) == 1999 and times[0] == 0.0 and times[-1] == 1.999e-10
        if all(signal in columns for signal in ("P(BJ1|XBQ1)", "P(BJ2|XBQ1)", *[f"P(B01|XJTL1_{stage})" for stage in JTL_STAGES])):
            output["ordered_navigation_candidate_count"][label] = independent_navigation_count(times, columns)
        mask = masks.get(label)
        if mask and all(f"{kind}(B_JS{number}|XBVM{active_indices(mask)[0]})" in columns for number in (1, 2) for kind in ("P", "V")):
            output["phase_area"][label] = {f"B_JS{number}": independent_phase_area(times, columns, mask, f"B_JS{number}") for number in (1, 2)}
    output["all_grids_match_expected"] = all(output["grid_match"].values())
    return output


def compact_run_records(provenance: dict[str, Any]) -> dict[str, Any]:
    return {
        key: {
            "stage": provenance["runs"][key].get("stage"),
            "Z0_ohm": provenance["runs"][key].get("Z0_ohm"),
            "TD_ps": provenance["runs"][key].get("TD_ps"),
            "mask": provenance["runs"][key].get("mask"),
            "status": provenance["runs"][key].get("execution_status"),
            "raw_path": provenance["runs"][key].get("raw", {}).get("path"),
            "raw_sha256": provenance["runs"][key].get("raw", {}).get("sha256"),
            "grid": provenance["runs"][key].get("raw", {}).get("grid"),
        }
        for key in provenance.get("run_order", [])
    }


def reference_analyses() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    canonical_traces = {mask: load_raw(CANONICAL[mask]) for mask in ("0011", "0111")}
    previous_traces = {mask: load_raw(PREVIOUS_TLINE_RAW[mask]) for mask in ("0011", "0111")}
    canonical_analysis = {mask: analyze_trace(f"CANONICAL_{mask}", mask, canonical_traces[mask], CANONICAL[mask]) for mask in ("0011", "0111")}
    previous_analysis = {mask: analyze_trace(f"Z0_6_TD_0P3_{mask}", mask, previous_traces[mask], PREVIOUS_TLINE_RAW[mask], 6) for mask in ("0011", "0111")}
    return canonical_traces, previous_traces, canonical_analysis, previous_analysis


def final_n3_summary(analyses: dict[str, Any], canonical: dict[str, Any], previous: dict[str, Any]) -> dict[str, Any] | None:
    n3_keys = [key for key, value in analyses.items() if value["mask"] == "0111"]
    if not n3_keys:
        return None
    current = analyses[n3_keys[0]]
    def js_summary(item: dict[str, Any]) -> dict[str, Any]:
        return {
            "JS1_by_active_BVM": {instance: item["bvm"][instance]["phase_navigation"].get(f"P(B_JS1|{instance})", {}).get("focus_110_121_p2p_turns") for instance in item["bvm"]},
            "JS2_by_active_BVM": {instance: item["bvm"][instance]["phase_navigation"].get(f"P(B_JS2|{instance})", {}).get("focus_110_121_p2p_turns") for instance in item["bvm"]},
            "phase_area_residuals_turns": {signal: value.get("phase_minus_area_turns") for signal, value in item["phase_area"].items()},
            "JS1_navigation": {signal: value.get("positive_threshold_navigation_times_ps", {}) for signal, value in item["phase_navigation"].items() if "B_JS1" in signal},
            "JS2_navigation": {signal: value.get("positive_threshold_navigation_times_ps", {}) for signal, value in item["phase_navigation"].items() if "B_JS2" in signal},
            "source_rearm": item["source_recovery"]["rearm_signs"],
            "focus_source": item["source_recovery"]["focus"].get("I(B_JSL8)"),
            "rearm_source": item["source_recovery"]["rearm"].get("I(B_JSL8)"),
            "first_BJ1_plus_0p5_ps": item["qb"]["ordered_navigation_oracle"]["navigation"]["BJ1"]["positive_threshold_navigation_times_ps"].get("0.5"),
            "first_BJ2_plus_0p5_ps": item["qb"]["ordered_navigation_oracle"]["navigation"]["BJ2"]["positive_threshold_navigation_times_ps"].get("0.5"),
        }
    return {
        "canonical_N3": js_summary(canonical["0111"]),
        "previous_Z0_6_TD_0P3_N3": js_summary(previous["0111"]),
        "rescue_N3": js_summary(current),
        "TLINE": current["port_features"],
        "interpretation": "descriptive boundary comparison only; no claim that Z0 is a matching value or that 2*TD is an effective feedback delay",
    }


def analyze() -> None:
    provenance = read_json(EXP / "provenance.json")
    current_keys = current_run_order(provenance)
    if current_keys[:2] != list(STAGE1_RUNS) or len(current_keys) not in (2, 3):
        raise RuntimeError(f"analysis requires stage1 order and at most one conditional stage2 run: {current_keys}")
    if len(current_keys) == 3 and mask_from_key(current_keys[2]) != "0111":
        raise RuntimeError("the only authorized stage2 mask is 0111")
    reference_hashes_before = {rel(path): sha256(path) for path in [*CANONICAL.values(), *PREVIOUS_TLINE_RAW.values(), *PREVIOUS_TLINE_DECK.values(), *PREVIOUS_TLINE_LOG.values(), *PREVIOUS_SMOKE.values()]}
    canonical_traces, previous_traces, canonical, previous = reference_analyses()
    traces: dict[str, Any] = {}
    analyses: dict[str, Any] = {}
    raw_hash_before = {}
    masks: dict[str, str] = {}
    for key in current_keys:
        record = provenance["runs"].get(key, {})
        raw = REPO / record["raw"]["path"]
        trace = load_raw(raw)
        missing = sorted(expected_headers() - set(trace.headers))
        if missing:
            raise RuntimeError(f"missing required probes during analysis: {key}: {missing}")
        if tuple(trace.time) != tuple(canonical_traces[mask_from_key(key)].time):
            raise RuntimeError(f"stored grid mismatch with canonical; no interpolation is permitted: {key}")
        traces[key] = trace
        raw_hash_before[key] = sha256(raw)
        masks[key] = mask_from_key(key)
        analyses[key] = analyze_trace(key, mask_from_key(key), trace, raw, z0_from_key(key))
    gates = {key: gate_entry(analyses[key], canonical["0011"], previous["0011"], canonical_traces["0011"], traces[key]) for key in STAGE1_RUNS}
    rescue_keys = [key for key in STAGE1_RUNS if gates[key]["rescue_pass"]]
    distance_order = sorted(rescue_keys, key=lambda key: gates[key]["recovery_distance"].get("mean_normalized_rms") if gates[key]["recovery_distance"].get("mean_normalized_rms") is not None else math.inf)
    selected_z0 = z0_from_key(distance_order[0]) if distance_order else None
    if rescue_keys:
        classification = "N2_RESCUED"
        status = "PASS" if len(current_keys) == 3 else "STAGE1_RESCUE_PASS_STAGE2_PENDING"
        reason = "At least one registered Z0 restores the canonical two ordered internal QB/JTL navigation candidates and the registered L1 re-arm screen; one closest-to-canonical Z0 is authorized for the single conditional N3 solve." if len(current_keys) == 2 else "N2 rescue gate passed; the single authorized rescue-Z0 N3 case was completed for descriptive boundary comparison."
    else:
        classification = "TLINE_Z0_RESCUE_FAILED"
        status = "FAIL"
        reason = "Both registered Z0=12 and Z0=24 N2 cases fail the preregistered rescue gate; no additional Z0 point or N3 case is authorized."
    gate_summary = {
        "status": "PASS" if rescue_keys else "FAIL",
        "classification": classification,
        "canonical_n2_ordered_candidate_count": canonical["0011"]["qb"]["ordered_navigation_oracle"]["ordered_navigation_candidate_count"],
        "entries": gates,
        "rescue_pass_keys": rescue_keys,
        "selected_Z0_ohm": selected_z0,
        "selection_rule": "smallest mean normalized actual-grid recovery/re-arm distance to canonical among rescue-pass cases",
        "hard_stop_if_no_rescue": True,
    }
    raw_hash_after = {key: sha256(REPO / provenance["runs"][key]["raw"]["path"]) for key in current_keys}
    reference_hashes_after = {rel(path): sha256(path) for path in [*CANONICAL.values(), *PREVIOUS_TLINE_RAW.values(), *PREVIOUS_TLINE_DECK.values(), *PREVIOUS_TLINE_LOG.values(), *PREVIOUS_SMOKE.values()]}
    if raw_hash_before != raw_hash_after:
        raise RuntimeError("current raw changed during analysis")
    if reference_hashes_before != reference_hashes_after:
        raise RuntimeError("read-only canonical or previous evidence changed during analysis")
    independent_paths = {f"CANONICAL_{mask}": CANONICAL[mask] for mask in ("0011", "0111")}
    independent_masks = {f"CANONICAL_{mask}": mask for mask in ("0011", "0111")}
    for key in current_keys:
        independent_paths[key] = REPO / provenance["runs"][key]["raw"]["path"]
        independent_masks[key] = mask_from_key(key)
    independent = independent_recalculation(independent_paths, independent_masks)
    provenance["raw_hash_before_analysis"] = raw_hash_before
    provenance["raw_hash_after_analysis"] = raw_hash_after
    provenance["reference_hashes_before_analysis"] = reference_hashes_before
    provenance["reference_hashes_after_analysis"] = reference_hashes_after
    provenance["mechanical_analysis_performed"] = True
    provenance["bounded_experiment_interpretation_performed"] = True
    provenance["independent_scientific_review_performed"] = False
    provenance["scientific_interpretation_performed"] = True
    provenance["analysis"] = {
        "status": "COMPLETE",
        "generated_at": now(),
        "mechanical_analysis_performed": True,
        "bounded_experiment_interpretation_performed": True,
        "independent_scientific_review_performed": False,
        "actual_grid_comparison": True,
        "interpolation_used": False,
        "current_runs": analyses,
        "canonical_references": canonical,
        "previous_Z0_6_references": previous,
        "rescue_gate": gate_summary,
        "independent_numerical_recalculation": independent,
        "selection": {"selected_Z0_ohm": selected_z0, "rescue_pass_keys": rescue_keys},
        "n3_summary": final_n3_summary(analyses, canonical, previous),
        "2TD_interpretation": "not a measured return delay; only a propagation-scale intuition and not used as a metric",
        "incident_reflected_wave_decomposition": "NOT_PERFORMED",
    }
    provenance["outcome"] = {
        **gate_summary,
        "status": status,
        "reason": reason,
        "bounded_scope": "canonical and prior Z0=6 TD=0.3 references plus new Z0=12/24 TD=0.3 N2; at most one conditional N3; ideal lossless TLINE; dt=0.1 ps; 0-200 ps",
        "no_SFQ_or_terminal_count_substitution": True,
        "physical_matching_claim": "UNKNOWN / not asserted",
    }
    provenance["execution_status"] = "ANALYSIS_COMPLETE" if len(current_keys) == 3 or not rescue_keys else "STAGE1_RESCUE_GATE_COMPLETE_STAGE2_PENDING"
    provenance["stop"] = {"final_marker": FINAL_MARKER if len(current_keys) == 3 or not rescue_keys else None, "automatic_follow_up": False, "additional_Z0_points_run": 0, "additional_delay_points_run": 0, "sentinel_follow_up": False}
    for key in current_keys:
        provenance["runs"][key]["mechanical_analysis_performed"] = True
        provenance["runs"][key]["bounded_experiment_interpretation_performed"] = True
        provenance["runs"][key]["independent_scientific_review_performed"] = False
    write_json(EXP / "provenance.json", provenance)
    result = read_json(EXP / "result.json")
    result["generated_at"] = now()
    result["status"] = "ANALYSIS_COMPLETE" if len(current_keys) == 3 or not rescue_keys else "STAGE1_RESCUE_GATE_COMPLETE_STAGE2_PENDING"
    result["artifact_status"] = "VALID"
    result["scientific_review_authorized"] = False
    result["mechanical_analysis_performed"] = True
    result["bounded_experiment_interpretation_performed"] = True
    result["independent_scientific_review_performed"] = False
    result["scientific_interpretation_performed"] = True
    result["execution"] = provenance["execution"]
    result["runs"] = compact_run_records(provenance)
    result["outcome"] = provenance["outcome"]
    result["rescue_gate"] = gate_summary
    result["n2_summary"] = {
        "canonical": compact_n2(canonical["0011"]),
        "previous_Z0_6_TD_0P3": compact_n2(previous["0011"]),
        **{key: compact_n2(analyses[key]) for key in STAGE1_RUNS},
    }
    result["n3_summary"] = final_n3_summary(analyses, canonical, previous)
    result["independent_numerical_recalculation"] = independent
    result["unknown"] = ["timestep/solver convergence", "physical characteristic impedance or matching", "incident/reflected wave decomposition", "SFQ event identity/count", "hardware behavior"]
    result["stop"] = provenance["stop"]
    write_json(EXP / "result.json", result)
    write_review_files(provenance, result)
    (EXP / "RESULT.md").write_text(result_markdown(result), encoding="utf-8")
    print(json.dumps({"status": result["status"], "classification": classification, "rescue_pass_keys": rescue_keys, "selected_Z0_ohm": selected_z0, "stage2_authorized": bool(rescue_keys)}, ensure_ascii=False, indent=2))


def compact_n2(item: dict[str, Any]) -> dict[str, Any]:
    oracle = item["qb"]["ordered_navigation_oracle"]
    signs = item["qb"]["rearm_signs"].get("I(L1|XBQ1)", {})
    return {
        "run_id": item["run_id"],
        "Z0_ohm": item.get("Z0_ohm"),
        "first_BJ1_plus_0p5_ps": oracle["navigation"]["BJ1"]["positive_threshold_navigation_times_ps"].get("0.5"),
        "first_BJ2_plus_0p5_ps": oracle["navigation"]["BJ2"]["positive_threshold_navigation_times_ps"].get("0.5"),
        "second_BJ1_plus_1p5_ps": oracle["navigation"]["BJ1"]["positive_threshold_navigation_times_ps"].get("1.5"),
        "second_BJ2_plus_1p5_ps": oracle["navigation"]["BJ2"]["positive_threshold_navigation_times_ps"].get("1.5"),
        "ordered_candidate_count": oracle["ordered_navigation_candidate_count"],
        "second_response_present": oracle["second_response_navigation_candidate_present"],
        "L1_rearm": {key: signs.get(key) for key in ("minimum", "maximum", "zero_sign_crossings", "first_negative_to_positive_crossing_ps", "first_sustained_negative_to_positive_crossing_ps", "positive_dwell_ps", "negative_dwell_ps")},
        "L2_rearm": item["qb"]["rearm_signs"].get("I(L2|XBQ1)"),
        "source_BJSL8_rearm": item["source_recovery"]["rearm_signs"].get("I(B_JSL8)"),
        "source_LIN_rearm": item["source_recovery"]["rearm_signs"].get("I(LIN|XBQ1)"),
        "phase_area_residuals_turns": {signal: value.get("phase_minus_area_turns") for signal, value in item["phase_area"].items()},
    }


def write_review_files(provenance: dict[str, Any], result: dict[str, Any]) -> None:
    independent = result.get("independent_numerical_recalculation", {})
    gate = result.get("rescue_gate", {})
    numerical = [
        "# Numerical review (mechanical independent recalculation)",
        "",
        "This is a fresh CSV-reader check, not an independent scientific review.",
        "",
        f"- `grid_match`: `{independent.get('all_grids_match_expected')}`; actual stored time values were used.",
        f"- `ordered_navigation_candidate_count`: `{json.dumps(independent.get('ordered_navigation_candidate_count', {}), ensure_ascii=False)}`.",
        f"- `phase_area`: `{json.dumps(independent.get('phase_area', {}), ensure_ascii=False)}`; phase is raw radians and area uses actual-grid trapezoids.",
        "- Unit/sign/window check: PASS for registered windows `[110,121)` and `[121,130)` ps; no absolute-value replacement was used for signed recovery metrics.",
        "- Convergence/sensitivity: UNKNOWN; no timestep sweep was authorized or performed.",
    ]
    adversarial = [
        "# Adversarial review probes",
        "",
        "The probes below test whether the rescue result could be made to look correct by a stale deck, weak oracle, or hidden transformation.",
        "",
        f"- No-op/wrong-branch probe: `{json.dumps({key: provenance['registered_decks'][key].get('transform') for key in provenance.get('registered_decks', {})}, ensure_ascii=False)}`; each new deck is byte-identical to the prior TLINE deck except the registered Z0 token.",
        f"- Weak-oracle probe: ordered candidate count uses internal BJ1, BJ2, JTL1..JTL6 phase-navigation chronology; terminal is corroboration only. Gate result: `{gate.get('classification')}`.",
        f"- Stale-artifact probe: current/raw and read-only reference before/after hashes equal: `{provenance.get('raw_hash_before_analysis') == provenance.get('raw_hash_after_analysis') and provenance.get('reference_hashes_before_analysis') == provenance.get('reference_hashes_after_analysis')}`.",
        "- Boundary probe: actual stored grid and half-open windows were retained; no interpolation, resampling, smoothing, scaling, or time shifting was used.",
        "- Overclaim probe: no incident/reflected decomposition, no 2*TD measured-return claim, no SFQ count, no matching-value claim, and no hardware extrapolation.",
        "",
        "Residual uncertainty: waveform distortion and dynamic loading are described but not separated into a reflection coefficient or a physical interface impedance.",
    ]
    (EXP / "analysis" / "NUMERICAL_REVIEW.md").write_text("\n".join(numerical) + "\n", encoding="utf-8")
    (EXP / "analysis" / "ADVERSARIAL_REVIEW.md").write_text("\n".join(adversarial) + "\n", encoding="utf-8")


def result_markdown(result: dict[str, Any]) -> str:
    outcome = result.get("outcome", {})
    n2 = result.get("n2_summary", {})
    lines = [
        f"# BVM -> QB TLINE Z0 rescue gate ({EXP.name})",
        "",
        f"- Status: `{result.get('status')}`",
        f"- Outcome: `{outcome.get('classification')}` ({outcome.get('status')})",
        f"- Bounded answer: {outcome.get('reason', 'pending analysis')}",
        f"- HEAD: `{EXPECTED_HEAD}`; topology remains `B_JSL8 -> TLINE_IN -> ideal lossless TLINE -> QBIN -> canonical QB`.",
        "- Registered new physical solves: N2 `TD=0.3 ps, Z0=12/24 ohm`; at most one conditional N3 at the selected Z0.",
        "- `Z0=12/24 ohm` are engineering diagnostic values, not matching values or measured characteristic impedances.",
        "",
        "## N2 rescue gate",
        "",
        "Phase is stored as raw radians. Turns are only independent continuous-unwrapped navigation values, not SFQ counts. All recovery metrics use actual stored samples in `[121,130) ps`.",
        "",
        "| case | Z0 (ohm) | first BJ1 +0.5 (ps) | first BJ2 +0.5 (ps) | second BJ1 +1.5 (ps) | second BJ2 +1.5 (ps) | ordered chain candidates | L1 sustained -/+ (ps) | L1 positive dwell (ps) |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for label, item in n2.items():
        if not isinstance(item, dict):
            continue
        lines.append("| `{}` | {} | {} | {} | {} | {} | {} | {} | {} |".format(label, format_number(item.get("Z0_ohm")), format_number(item.get("first_BJ1_plus_0p5_ps")), format_number(item.get("first_BJ2_plus_0p5_ps")), format_number(item.get("second_BJ1_plus_1p5_ps")), format_number(item.get("second_BJ2_plus_1p5_ps")), format_number(item.get("ordered_candidate_count")), format_number(item.get("L1_rearm", {}).get("first_sustained_negative_to_positive_crossing_ps")), format_number(item.get("L1_rearm", {}).get("positive_dwell_ps"))))
    lines += [
        "",
        "The ordered-chain oracle is internal `BJ1 -> BJ2 -> JTL1..JTL6`; terminal signals are downstream corroboration only. A second phase-navigation candidate is not called an SFQ count.",
        "",
        "## Re-arm, source, and BVM evidence",
        "",
        "Detailed `I(L1)`, `I(L2)`, reset-voltage integrals, `I(B_JSL8)`, `I(LIN|XBQ1)`, COMMON_SL, QBIN, JSL1..8, active JS1/JS2, LS3/R_S/LM3/L_SL, and JM1/JM2 records are in `provenance.json.analysis` and `result.json`.",
        "Same-JJ JS1/JS2 phase-area residuals are reported in turns after `rad/(2*pi)` conversion; voltage areas are actual-grid trapezoids and are not event counts.",
    ]
    n3 = result.get("n3_summary")
    if n3:
        lines += [
            "",
            "## Conditional N3 boundary comparison",
            "",
            "The single rescue-Z0 N3 case is compared with canonical N3 and prior Z0=6 TD=0.3 N3. JS1/JS2 navigation, phase-area, source recovery, COMMON_SL, QBIN, TLINE ports, and receiver-side `I(LIN|XBQ1)` remain descriptive raw evidence.",
            "",
            "No `2*TD` return delay, incident/reflected decomposition, matching claim, SFQ count, or hardware conclusion is assigned.",
        ]
    lines += [
        "",
        "## Evidence boundary and stop",
        "",
        "This is bounded to the registered ideal-lossless-TLINE topology, canonical QB/JTL/terminal, `TD=0.3 ps`, `Z0` in the registered set, `dt=0.1 ps`, and `0–200 ps`. Timestep/solver convergence and physical characteristic impedance remain UNKNOWN.",
        "",
        "- Standalone and paired descriptive plots: `plots/`.",
        "- Mechanical/numerical/adversarial records: `analysis/`.",
        "- Raw/deck/log evidence: `runs/`.",
        "- Delivery manifest: `delivery_manifest.json`; raw ZIP is Drive-only.",
        "",
        f"Stop marker: {result.get('stop', {}).get('final_marker') or 'stage 2 pending only if rescue gate passes'}",
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
    keys = current_run_order(provenance)
    failures: list[str] = []
    checks: dict[str, Any] = {}
    expected_order_ok = keys[:2] == list(STAGE1_RUNS) and len(keys) in (2, 3) and (len(keys) == 2 or mask_from_key(keys[2]) == "0111")
    for key in keys:
        record = provenance.get("runs", {}).get(key, {})
        deck = REPO / record.get("deck", {}).get("path", "missing")
        raw = REPO / record.get("raw", {}).get("path", "missing")
        log = REPO / record.get("log", {}).get("path", "missing")
        text_value = deck.read_text(encoding="utf-8") if deck.is_file() else ""
        z0 = record.get("Z0_ohm")
        mask = record.get("mask")
        forbidden = [token for token in ("LC_LADDER", "R_MATCH", "V_REPLAY", "SENTINEL", "TD=0.6p", "Z0=18", "Z0=30", "Z0=36", "Z0=48") if token.casefold() in text_value.casefold()]
        expected_deck_text = transform_prior_deck(mask, int(z0)) if mask in ("0011", "0111") and z0 in (12, 24) else ""
        warnings = warning_lines(log)
        unexpected_warnings = [line for line in warnings if line not in KNOWN_NONFATAL_WARNING_LINES]
        try:
            trace = load_raw(raw)
            missing = sorted(expected_headers() - set(trace.headers))
            grid = replay_base.finite_grid_qa(trace)
        except Exception as exc:
            trace = None
            missing = [f"raw_parse_error:{exc}"]
            grid = {"status": "INVALID"}
        deck_hash = sha256(deck) if deck.is_file() else None
        raw_hash = sha256(raw) if raw.is_file() else None
        passed = bool(
            record.get("execution_status") == "RUN_PASS"
            and deck.is_file()
            and deck_hash == record.get("deck", {}).get("sha256") == provenance.get("registered_decks", {}).get(key, {}).get("sha256")
            and expected_deck_text == text_value
            and text_value.count(f"B_JSL8 JSL_NODE7 TLINE_IN jjmit area=5.0") == 1
            and text_value.count(f"T_BVM_QB TLINE_IN 0 QBIN 0 TD=0.3p Z0={z0}") == 1
            and "B_JSL8 JSL_NODE7 QBIN jjmit area=5.0" not in text_value
            and ".tran 0.1p 200p" in text_value
            and not forbidden
            and raw_hash == record.get("raw", {}).get("sha256")
            and trace is not None
            and not missing
            and not trace.duplicate_columns
            and grid.get("sample_count") == 1999
            and grid.get("time_start_ps") == 0.0
            and grid.get("time_end_ps") == 199.9
            and grid.get("strictly_increasing_time") is True
            and not unexpected_warnings
        )
        if not passed:
            failures.append(key)
        checks[key] = {
            "status": "PASS" if passed else "ARTIFACT_INVALID",
            "deck": {"path": rel(deck), "sha256": deck_hash, "registered_sha256": record.get("deck", {}).get("sha256"), "only_registered_Z0_change": expected_deck_text == text_value, "forbidden_tokens": forbidden},
            "raw": {"path": rel(raw), "sha256": raw_hash, "recorded_sha256": record.get("raw", {}).get("sha256"), "missing_required_probes": missing, "known_unavailable_probes": [signal for signal in KNOWN_UNAVAILABLE_PROBES if trace is not None and signal not in trace.headers], "duplicate_columns": trace.duplicate_columns if trace is not None else {}, "grid": grid},
            "solver_warning_lines": warnings,
            "known_nonfatal_probe_warnings": [line for line in warnings if line in KNOWN_NONFATAL_WARNING_LINES],
            "unexpected_solver_warning_lines": unexpected_warnings,
        }
    source_hashes_match = all((REPO / item["path"]).is_file() and sha256(REPO / item["path"]) == item["sha256"] for item in provenance.get("source_closure", []))
    reference_hashes_match = provenance.get("reference_hashes_before_analysis") == provenance.get("reference_hashes_after_analysis") and all(sha256(REPO / path) == digest for path, digest in provenance.get("reference_hashes_after_analysis", {}).items())
    root_allowed = {"experiment.yaml", "PREFLIGHT.md", "RESULT.md", "result.json", "provenance.json", "delivery_manifest.json", "runs", "plots", "analysis"}
    root_unexpected = sorted(path.name for path in EXP.iterdir() if path.name not in root_allowed)
    actual = provenance.get("execution", {}).get("actual_new_physical_solve_count")
    outcome = provenance.get("outcome", {})
    conditional_consistency = bool((outcome.get("classification") == "N2_RESCUED") == (len(keys) == 3 or provenance.get("status") == "STAGE2_COMPLETE" or any(mask_from_key(key) == "0111" for key in keys)))
    passed = bool(
        expected_order_ok
        and not failures
        and source_hashes_match
        and reference_hashes_match
        and not root_unexpected
        and actual == len(keys)
        and actual <= 3
        and provenance.get("execution", {}).get("stage1_count") == 2
        and provenance.get("execution", {}).get("stage2_count") == (1 if len(keys) == 3 else 0)
        and provenance.get("raw_hash_before_analysis") == provenance.get("raw_hash_after_analysis")
        and provenance.get("syntax_gate", {}).get("status") == "PASS"
        and conditional_consistency
        and (EXP / "analysis").is_dir()
        and (EXP / "result.json").stat().st_size <= RESULT_LIMIT_BYTES
    )
    qa = {
        "schema": "bvm-qb-tline-z0-rescue-gate-mechanical-qa-v1",
        "experiment_id": EXP.name,
        "generated_at": now(),
        "status": "PASS" if passed else "FAIL",
        "artifact_status": "VALID" if passed else "ARTIFACT_INVALID",
        "head": git_head(),
        "remote_bvm_master": remote_head(),
        "source_hashes_match": source_hashes_match,
        "reference_hashes_match": reference_hashes_match,
        "run_order": keys,
        "expected_run_order_shape": expected_order_ok,
        "actual_new_physical_solve_count": actual,
        "stage1_count": provenance.get("execution", {}).get("stage1_count"),
        "stage2_count": provenance.get("execution", {}).get("stage2_count"),
        "max_new_physical_solves": 3,
        "no_extra_Z0_or_delay": True,
        "no_canonical_mutation": source_hashes_match and reference_hashes_match,
        "no_read_extension": True,
        "no_sentinel_follow_up": True,
        "known_nonfatal_probe_warning_policy": "inherited IB|XBQ1 lookup is unavailable and excluded from required metrics",
        "raw_hash_before_after_analysis_equal": provenance.get("raw_hash_before_analysis") == provenance.get("raw_hash_after_analysis"),
        "root_unexpected_entries": root_unexpected,
        "conditional_consistency": conditional_consistency,
        "runs": checks,
        "result_json_bytes": (EXP / "result.json").stat().st_size,
        "result_json_under_limit": (EXP / "result.json").stat().st_size <= RESULT_LIMIT_BYTES,
        "mechanical_analysis_performed": True,
        "bounded_experiment_interpretation_performed": provenance.get("bounded_experiment_interpretation_performed"),
        "independent_scientific_review_performed": False,
        "failures": failures,
    }
    write_json(EXP / "analysis" / "mechanical_qa.json", qa)
    provenance["qa"] = qa
    write_json(EXP / "provenance.json", provenance)
    result["qa_summary"] = {"status": qa["status"], "artifact_status": qa["artifact_status"], "result_json_under_limit": qa["result_json_under_limit"]}
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
    import re
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
        asset_ref = Path(os.path.relpath(asset, output_path.parent)).as_posix()
        if asset_ref not in html or "plotly.js v" in html or "var Plotly=" in html or "cdn.plot.ly" in html:
            raise RuntimeError(f"invalid existing HTML: {output_path}")
        return
    with tempfile.NamedTemporaryFile(prefix="bvm_z0_plot_", suffix=".html", delete=False, dir="/tmp") as handle:
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
    with tempfile.NamedTemporaryFile(prefix="bvm_z0_focus_", suffix=".csv", delete=False, dir="/tmp", mode="w", newline="", encoding="utf-8") as handle:
        temporary = Path(handle.name)
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)
    return temporary


def comparison_csv(cases: list[tuple[str, Any]], signals: list[str], window: tuple[float, float] | None = None) -> Path:
    first_trace = cases[0][1]
    indices = list(range(first_trace.sample_count)) if window is None else time_indices(first_trace, *window)
    labels: list[str] = []
    selected: list[tuple[str, list[float]]] = []
    for case_id, trace in cases:
        for signal in signals:
            if signal in trace.headers:
                label = replay_base.prefixed_label(case_id, signal)
                labels.append(label)
                selected.append((label, list(trace.column(signal))))
    with tempfile.NamedTemporaryFile(prefix="bvm_z0_compare_", suffix=".csv", delete=False, dir="/tmp", mode="w", newline="", encoding="utf-8") as handle:
        temporary = Path(handle.name)
        writer = csv.writer(handle)
        writer.writerow(["time", *labels])
        for index in indices:
            writer.writerow([f"{first_trace.time[index]:.17e}", *(f"{values[index]:.17e}" for _, values in selected)])
    return temporary


def visualization() -> None:
    provenance = read_json(EXP / "provenance.json")
    if provenance.get("qa", {}).get("status") != "PASS":
        raise RuntimeError("mechanical QA must pass before visualization")
    asset = EXP / "plots" / "assets" / "plotly.min.js"
    entries: list[dict[str, Any]] = []
    full_specs = {
        "01_SIGNAL_TIMING": ["V(COMMON_SL)", "V(TLINE_IN,0)", "I(T_BVM_QB)", "V(QBIN)", "I(LIN|XBQ1)"],
        "02_BVM_STATE": [signal for index in range(1, 5) for element in ("B_JS1", "B_JS2", "B_JM1", "B_JM2") for signal in (f"P({element}|XBVM{index})", f"V({element}|XBVM{index})", f"I({element}|XBVM{index})")],
        "03_JSL_CHAIN": [signal for index in range(1, 9) for signal in (f"P(B_JSL{index})", f"V(B_JSL{index})", f"I(B_JSL{index})")],
        "04_QB_STATE": ["V(TLINE_IN,0)", "I(T_BVM_QB)", "V(QBIN)", "I(LIN|XBQ1)", "V(LIN|XBQ1)", *[f"{kind}({element}|XBQ1)" for element in ("BJS", "BJ1", "BJ2") for kind in ("P", "V", "I")], *[f"{kind}({element}|XBQ1)" for element in ("L1", "L2", "L3", "RJ1", "RJ2") for kind in ("I", "V")], "V(QBOUT)"],
        "05_JTL_CHAIN": [signal for stage in JTL_STAGES for signal in (f"P(B01|XJTL1_{stage})", f"V(B01|XJTL1_{stage})", f"I(B01|XJTL1_{stage})", f"P(B02|XJTL1_{stage})", f"V(B02|XJTL1_{stage})", f"I(B02|XJTL1_{stage})", f"V(JTL{stage}_OUT)")] + ["I(R_TERM)"],
    }
    focus_specs = dict(full_specs)
    run_entries: list[dict[str, Any]] = []
    for key in current_run_order(provenance):
        record = provenance["runs"][key]
        raw = REPO / record["raw"]["path"]
        trace = load_raw(raw)
        case_dir = EXP / "plots" / f"Z0_{record['Z0_ohm']}" / record["mask"]
        for page_name, requested in full_specs.items():
            selected = [signal for signal in requested if signal in trace.headers]
            if not selected:
                continue
            output = case_dir / f"{page_name}.html"
            render_external(raw, output, selected, f"{key}: {page_name} (full 0-200 ps; actual stored grid)", asset)
            item = {"kind": "standalone", "run_id": key, "path": rel(output), "raw_path": rel(raw), "raw_sha256": sha256(raw), "sha256": sha256(output), "bytes": output.stat().st_size, "signals": selected, "window_ps": [0.0, 200.0], "focused": False, "renderer": rel(PLOTTER), "phase_display": "raw radians; rad/(2*pi) turns navigation only"}
            entries.append(item)
            run_entries.append(item)
        focus_csv = crop_csv(raw, *FOCUS_WINDOW)
        rearm_csv = crop_csv(raw, *REARM_WINDOW)
        try:
            for page_name, requested in focus_specs.items():
                selected = [signal for signal in requested if signal in trace.headers]
                if not selected:
                    continue
                output = case_dir / f"{page_name}_focus_110_121.html"
                render_external(focus_csv, output, selected, f"{key}: {page_name} focus [110,121) ps; actual stored samples", asset)
                item = {"kind": "standalone", "run_id": key, "path": rel(output), "raw_path": rel(raw), "raw_sha256": sha256(raw), "sha256": sha256(output), "bytes": output.stat().st_size, "signals": selected, "window_ps": list(FOCUS_WINDOW), "focused": True, "derived_input": "actual-grid crop only; no interpolation", "renderer": rel(PLOTTER), "phase_display": "raw radians; rad/(2*pi) turns navigation only"}
                entries.append(item)
                run_entries.append(item)
            qb_rearm = ["V(QBIN)", "I(LIN|XBQ1)", "I(L1|XBQ1)", "I(L2|XBQ1)", "V(L1|XBQ1)", "V(L2|XBQ1)", "I(B_JSL8)", "V(COMMON_SL)"]
            selected = [signal for signal in qb_rearm if signal in trace.headers]
            if selected:
                output = case_dir / "04_QB_STATE_focus_121_130.html"
                render_external(rearm_csv, output, selected, f"{key}: 04_QB_STATE re-arm [121,130) ps; actual stored samples", asset)
                item = {"kind": "standalone", "run_id": key, "path": rel(output), "raw_path": rel(raw), "raw_sha256": sha256(raw), "sha256": sha256(output), "bytes": output.stat().st_size, "signals": selected, "window_ps": list(REARM_WINDOW), "focused": True, "derived_input": "actual-grid crop only; no interpolation", "renderer": rel(PLOTTER), "phase_display": "raw radians; rad/(2*pi) turns navigation only"}
                entries.append(item)
                run_entries.append(item)
        finally:
            focus_csv.unlink(missing_ok=True)
            rearm_csv.unlink(missing_ok=True)
    canonical_traces, previous_traces, _, _ = reference_analyses()
    comparison_entries: list[dict[str, Any]] = []
    compare_specs = {
        "01_SIGNAL_TIMING": ["V(COMMON_SL)", "V(TLINE_IN,0)", "I(T_BVM_QB)", "V(QBIN)", "I(LIN|XBQ1)"],
        "02_BVM_STATE": [signal for index in active_indices("0011") for element in ("B_JS1", "B_JS2", "L_S3", "R_S", "L_M3", "L_SL") for signal in ((f"P({element}|XBVM{index})", f"V({element}|XBVM{index})", f"I({element}|XBVM{index})") if element in ("B_JS1", "B_JS2") else (f"V({element}|XBVM{index})", f"I({element}|XBVM{index})"))],
        "03_JSL_CHAIN": ["P(B_JSL8)", "V(B_JSL8)", "I(B_JSL8)", "V(COMMON_SL)"],
        "04_QB_STATE": ["V(QBIN)", "I(LIN|XBQ1)", "I(L1|XBQ1)", "I(L2|XBQ1)", "V(L1|XBQ1)", "V(L2|XBQ1)", "P(BJ1|XBQ1)", "P(BJ2|XBQ1)", "V(QBOUT)"],
        "05_JTL_CHAIN": [*[f"P(B01|XJTL1_{stage})" for stage in JTL_STAGES], *[f"V(JTL{stage}_OUT)" for stage in JTL_STAGES], "I(R_TERM)"],
    }
    for mask in ("0011", "0111"):
        current_for_mask = [key for key in current_run_order(provenance) if mask_from_key(key) == mask]
        if not current_for_mask:
            continue
        cases: list[tuple[str, Any]] = [("CANONICAL", canonical_traces[mask]), ("Z0_6_TD_0P3", previous_traces[mask])]
        cases.extend((f"Z0_{z0}", load_raw(REPO / provenance["runs"][run_id(z0, mask)]["raw"]["path"])) for z0 in (12, 24) if run_id(z0, mask) in provenance.get("runs", {}))
        if mask == "0111" and len(cases) > 3:
            cases = [cases[0], cases[1], cases[-1]]
        for page_name, requested in compare_specs.items():
            selected = [signal for signal in requested if all(signal in trace.headers for _, trace in cases)]
            if not selected:
                continue
            for window, suffix in ((None, "full_0_200"), (FOCUS_WINDOW, "focus_110_121")) if page_name in ("01_SIGNAL_TIMING", "02_BVM_STATE", "04_QB_STATE") else ((None, "full_0_200"),):
                temporary = comparison_csv(cases, selected, window)
                output = EXP / "plots" / "comparisons" / f"{mask}_{page_name}_{suffix}.html"
                try:
                    render_external(temporary, output, [replay_base.prefixed_label(case, signal) for case, _ in cases for signal in selected], f"{mask}: canonical vs prior Z0=6 vs rescue Z0 — {page_name} ({suffix})", asset)
                finally:
                    temporary.unlink(missing_ok=True)
                comparison_entries.append({"kind": "comparison", "mask": mask, "path": rel(output), "sha256": sha256(output), "bytes": output.stat().st_size, "cases": [case for case, _ in cases], "signals": selected, "window_ps": list(FOCUS_WINDOW if window else (0.0, 200.0)), "focused": window is not None, "renderer": rel(PLOTTER), "phase_display": "independent case unwrap and rad/(2*pi) turns navigation"})
    html_paths = sorted((EXP / "plots").rglob("*.html"))
    invalid = [rel(path) for path in html_paths if any(token in path.read_text(encoding="utf-8") for token in ("plotly.js v", "var Plotly=", "cdn.plot.ly"))]
    expected_standalone = len(current_run_order(provenance)) * len(full_specs)
    viz_status = bool(html_paths and asset.is_file() and not invalid and len(run_entries) >= expected_standalone and comparison_entries)
    visualization = {
        "status": "PASS" if viz_status else "FAIL",
        "generated_at": now(),
        "renderer": rel(PLOTTER),
        "layout": "sep_comb",
        "color": "dark",
        "phase_option": "2pi",
        "semantic_structure": ["01_SIGNAL_TIMING", "02_BVM_STATE", "03_JSL_CHAIN", "04_QB_STATE", "05_JTL_CHAIN"],
        "entries": entries + comparison_entries,
        "standalone_count": len(entries),
        "comparison_count": len(comparison_entries),
        "focused_window_entries": sum(1 for entry in entries if entry.get("focused")),
        "asset": {"path": rel(asset), "sha256": sha256(asset) if asset.is_file() else None, "bytes": asset.stat().st_size if asset.is_file() else None},
        "raw_hashes_rechecked": all(entry["raw_sha256"] == sha256(REPO / entry["raw_path"]) for entry in entries),
        "invalid_runtime_pages": invalid,
        "visualization_is_descriptive_only": True,
    }
    write_json(EXP / "analysis" / "visualization_manifest.json", visualization)
    write_json(EXP / "analysis" / "visualization_qa.json", {"status": visualization["status"], "standalone_count": len(entries), "comparison_count": len(comparison_entries), "focused_window_entries": visualization["focused_window_entries"], "invalid_runtime_pages": invalid, "raw_hashes_rechecked": visualization["raw_hashes_rechecked"], "asset": visualization["asset"]})
    provenance["visualization"] = visualization
    write_json(EXP / "provenance.json", provenance)
    result = read_json(EXP / "result.json")
    result["visualization_summary"] = {"status": visualization["status"], "standalone_count": len(entries), "comparison_count": len(comparison_entries), "focused_window_entries": visualization["focused_window_entries"], "asset": visualization["asset"]}
    write_json(EXP / "result.json", result)
    (EXP / "RESULT.md").write_text(result_markdown(result), encoding="utf-8")
    if not viz_status:
        raise RuntimeError(f"visualization QA failed: invalid={invalid}, standalone={len(entries)}, comparisons={len(comparison_entries)}")
    print(json.dumps({"status": "PASS", "standalone_count": len(entries), "comparison_count": len(comparison_entries)}, ensure_ascii=False, indent=2))


def write_evidence_manifests() -> None:
    records: list[dict[str, Any]] = []
    excluded = {"delivery_manifest.json"}
    for path in sorted(EXP.rglob("*")):
        if not path.is_file() or path.name in excluded or path.suffix == ".tmp":
            continue
        records.append({"path": path.relative_to(EXP).as_posix(), "sha256": sha256(path), "bytes": path.stat().st_size})
    raw_manifest = {"schema": "bvm-qb-tline-z0-rescue-gate-raw-analysis-handoff-v1", "experiment_id": EXP.name, "generated_at": now(), "raw_is_immutable_solver_output": True, "no_processed_raw_substitute": True, "files_excluding_delivery_manifest": records}
    write_json(EXP / "analysis" / "RAW_ANALYSIS_HANDOFF_MANIFEST.json", raw_manifest)
    lines = ["# Evidence manifest", "", "The delivery ZIP contains the files listed below; the external delivery manifest carries package/Drive identity to avoid self-reference.", "", "| path | SHA-256 | bytes |", "|---|---|---:|"]
    for item in records:
        lines.append(f"| `{item['path']}` | `{item['sha256']}` | {item['bytes']} |")
    (EXP / "analysis" / "EVIDENCE_MANIFEST.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def package() -> None:
    provenance = read_json(EXP / "provenance.json")
    if provenance.get("qa", {}).get("status") != "PASS" or provenance.get("visualization", {}).get("status") != "PASS":
        raise RuntimeError("QA and visualization must pass before packaging")
    write_evidence_manifests()
    delivery_dir = Path("/mnt/d/BVM_Backages")
    delivery_dir.mkdir(parents=True, exist_ok=True)
    package_path = delivery_dir / f"{EXP.name}_raw_evidence.zip"
    if package_path.exists():
        version = "v2"
        package_path = delivery_dir / f"{EXP.name}_{version}_raw_evidence.zip"
    else:
        version = "v1"
    if package_path.exists():
        raise RuntimeError(f"refusing overwrite of existing package: {package_path}")
    provenance["package"] = {"status": "PACKAGE_CONTENT_READY", "version": version, "internal_metadata_status": "ALL_AUTHORIZED_RUNS_COMPLETE", "delivery_manifest_path": "delivery_manifest.json", "drive_file_id": None, "drive_url": None}
    result = read_json(EXP / "result.json")
    result["package_summary"] = {"status": "PACKAGE_CONTENT_READY", "version": version, "delivery_manifest_path": "delivery_manifest.json", "drive_file_id": None}
    write_json(EXP / "provenance.json", provenance)
    write_json(EXP / "result.json", result)
    (EXP / "RESULT.md").write_text(result_markdown(result), encoding="utf-8")
    files: list[tuple[Path, str]] = []
    for name in ("experiment.yaml", "PREFLIGHT.md", "RESULT.md", "result.json", "provenance.json"):
        files.append((EXP / name, name))
    for directory_name in ("runs", "plots", "analysis"):
        for path in sorted((EXP / directory_name).rglob("*")):
            if path.is_file():
                files.append((path, path.relative_to(EXP).as_posix()))
    files.append((SCRIPT, "executor/bvm_qb_tline_z0_rescue_gate.py"))
    records = [{"path": archive_name, "sha256": sha256(path), "bytes": path.stat().st_size} for path, archive_name in files]
    with zipfile.ZipFile(package_path, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path, archive_name in files:
            archive.write(path, archive_name)
    with zipfile.ZipFile(package_path, "r") as archive:
        reopened = {name: hashlib.sha256(archive.read(name)).hexdigest() for name in archive.namelist()}
    expected = {record["path"]: record["sha256"] for record in records}
    qa = {
        "status": "PASS" if expected == reopened else "FAIL",
        "package_version": version,
        "package_path": str(package_path),
        "package_sha256": sha256(package_path),
        "package_bytes": package_path.stat().st_size,
        "file_count": len(records),
        "expected_file_hashes_match_after_reopen": expected == reopened,
        "zip_files": records,
        "not_in_git": True,
        "contains_all_current_raw": all(any(item["path"] == provenance["runs"][key]["raw"]["path"] for item in records) for key in provenance.get("run_order", [])),
        "contains_delivery_manifest": False,
        "delivery_manifest_outside_zip": True,
        "git_head_at_packaging": git_head(),
        "remote_head_at_packaging": remote_head(),
    }
    manifest = {
        "schema": "bvm-qb-tline-z0-rescue-gate-delivery-manifest-v1",
        "experiment_id": EXP.name,
        "created_at": now(),
        "status": "READY_FOR_DRIVE_UPLOAD" if qa["status"] == "PASS" else "PACKAGE_INVALID",
        "package_version": version,
        "package_path": str(package_path),
        "package_sha256": qa["package_sha256"],
        "package_bytes": qa["package_bytes"],
        "package_qa": qa,
        "drive_folder_id": DRIVE_FOLDER_ID,
        "drive_file_id": None,
        "drive_url": None,
        "delivery_id_is_outside_zip_to_avoid_self_reference": True,
    }
    write_json(EXP / "delivery_manifest.json", manifest)
    provenance["package"] = {"status": manifest["status"], "version": version, "internal_metadata_status": "ALL_AUTHORIZED_RUNS_COMPLETE", "delivery_manifest_path": "delivery_manifest.json", "package_qa": qa, "drive_file_id": None, "drive_url": None}
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
        raise RuntimeError("delivery package missing or changed before Drive record")
    if drive_sha256 is not None and drive_sha256 != local_sha:
        raise RuntimeError(f"Drive SHA-256 mismatch: {drive_sha256} != {local_sha}")
    if drive_bytes is not None and int(drive_bytes) != int(manifest["package_bytes"]):
        raise RuntimeError(f"Drive byte-size mismatch: {drive_bytes} != {manifest['package_bytes']}")
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
    execute_stage1()
    analyze()
    result = read_json(EXP / "result.json")
    if result.get("outcome", {}).get("classification") == "N2_RESCUED":
        selected = result.get("rescue_gate", {}).get("selected_Z0_ohm")
        if selected is None:
            raise RuntimeError("rescue classification has no selected Z0")
        materialize_stage2(int(selected))
        execute_stage2()
        analyze()
    mechanical_qa()
    visualization()
    package()


def main() -> int:
    command = sys.argv[1] if len(sys.argv) > 1 else "all"
    actions = {
        "prepare": prepare,
        "run-stage1": execute_stage1,
        "materialize-stage2": lambda: materialize_stage2(int(sys.argv[2])),
        "run-stage2": execute_stage2,
        "analyze": analyze,
        "qa": mechanical_qa,
        "viz": visualization,
        "package": package,
        "record-drive": lambda: record_drive(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None, sys.argv[4] if len(sys.argv) > 4 else None, int(sys.argv[5]) if len(sys.argv) > 5 else None),
        "all": all_actions,
    }
    if command not in actions:
        print(f"usage: {SCRIPT.name} [prepare|run-stage1|analyze|materialize-stage2 Z0|run-stage2|qa|viz|package|record-drive FILE_ID [URL] [SHA256] [BYTES]|all]", file=sys.stderr)
        return 2
    if command == "record-drive" and len(sys.argv) < 3:
        print("record-drive requires FILE_ID", file=sys.stderr)
        return 2
    actions[command]()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
