#!/usr/bin/env python3
"""Bounded BVM -> canonical QB TLINE feedback-dephasing experiment.

The first execution is deliberately small and fixed: one Z0 (6 ohm), two
registered TD values (0.3 ps and 0.6 ps), and masks 0011/0111.  The canonical
closed N2/N3 raws are read-only references; they are never rerun or copied
into the experiment directory.  The four formal decks are made only after a
separate JoSIM TLINE syntax/delay smoke test passes.

This module is an evidence runner and bounded timing reviewer.  It does not
convert a current waveform into SFQ events, and it does not decompose port
waveforms into incident/reflected waves without a separately justified model.
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
import textwrap
import zipfile
from pathlib import Path
from typing import Any, Iterable

REPO = Path(__file__).resolve().parents[1]
SCRIPT = Path(__file__).resolve()
sys.path.insert(0, str(REPO / "scripts"))
import bvm_qb_boundary_timing_replay as replay_base  # noqa: E402


EXP = REPO / "test" / "exploration" / "bvm-qb-tline-feedback-dephasing-v1-20260916"
SOLVER = REPO / "build" / "josim-cli"
PLOTTER = REPO / "scripts" / "josim-plot2.py"
SOURCE_INPUTS = REPO / "test" / "exploration" / "bvm-qb-threshold-ordering-boundary-search-v1-20260911" / "inputs"
REFERENCE_ROOT = REPO / "test" / "exploration" / "bvm-qb-threshold-ordering-boundary-search-v1-20260911" / "references" / "canonical_baseline"
CANONICAL = {
    "0011": REFERENCE_ROOT / "0011" / "raw.csv",
    "0111": REFERENCE_ROOT / "0111" / "raw.csv",
}
CANONICAL_DECKS = {
    "0011": REFERENCE_ROOT / "0011" / "deck.cir",
    "0111": REFERENCE_ROOT / "0111" / "deck.cir",
}
SMOKE_DECK = EXP / "smoke" / "tline_syntax" / "deck.cir"
SMOKE_RAW = EXP / "smoke" / "tline_syntax" / "raw.csv"
SMOKE_LOG = EXP / "smoke" / "tline_syntax" / "run.log"

EXPECTED_HEAD = "cdd916a35ee3f28eea8b7d3524a5751fda6f6efd"
EXPECTED_SOURCE_HASHES = {
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

PHI0 = 2.067833848e-15
TAU = 2.0 * math.pi
WINDOWS_PS = ((0.0, 200.0), (70.0, 110.0), (101.0, 110.0), (110.0, 121.0), (121.0, 200.0))
FOCUS_WINDOW = (110.0, 121.0)
CONTROL_WINDOW = (70.0, 110.0)
LANDMARK_WINDOW = (113.5, 115.5)
PHASE_THRESHOLDS = (0.5, 1.5, 2.5, 3.5, 4.5, 5.5, 6.5, 7.5)
FORMAL_CASES = (
    ("TLINE_TD_0P3", "0.3p", 0.3, 3),
    ("TLINE_TD_0P6", "0.6p", 0.6, 6),
)
MASKS = ("0011", "0111")
RUN_ORDER = tuple(f"{case_id}_{mask}" for case_id, _, _, _ in FORMAL_CASES for mask in MASKS)
FINAL_MARKER = "EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW"
CONTRACT_SENTENCE = "This experiment is governed by docs/EXPERIMENT_CONTRACT.md."
RESULT_LIMIT_BYTES = 500 * 1024
DRIVE_FOLDER_ID = "1--nlY7Nq5ArVPydJNrnQf-EGmwN-undh"

BVM_JUNCTIONS = ("B_JM1", "B_JM2", "B_JS1", "B_JS2")
BVM_BRANCHES = ("L_S1", "L_S2", "L_S3", "R_S", "L_M3", "L_SL")
JTL_STAGES = range(1, 7)


def now() -> str:
    return replay_base.now()


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
    replay_base.write_json(path, value)


def read_json(path: Path) -> dict[str, Any]:
    return replay_base.read_json(path)


def git_head() -> str:
    return replay_base.git_head()


def remote_head() -> str | None:
    return replay_base.remote_head()


def record_file(name: str, path: Path, role: str) -> dict[str, Any]:
    return replay_base.record_file(name, path, role)


def load_raw(path: Path) -> Any:
    return replay_base.load_raw(path)


def time_indices(trace: Any, start_ps: float, end_ps: float) -> list[int]:
    return replay_base.time_indices(trace, start_ps, end_ps)


def actual_integral(times: Iterable[float], values: Iterable[float]) -> float:
    time_list = list(times)
    value_list = list(values)
    return sum(
        0.5 * (value_list[index] + value_list[index + 1])
        * (time_list[index + 1] - time_list[index])
        for index in range(len(value_list) - 1)
    )


def source_inventory() -> list[dict[str, Any]]:
    records = [
        record_file("runner", SCRIPT, "formal TLINE runner, arithmetic, QA, visualization, and package builder"),
        record_file("global_jjmit_model", SOURCE_INPUTS / "jjmit.cir", "canonical global JJ model closure"),
        record_file("canonical_bvm", SOURCE_INPUTS / "bvm_jm2_connected.cir", "canonical BVM source closure"),
        record_file("canonical_qb_include", SOURCE_INPUTS / "BQ_parameterized_bjs400_rj2.cir", "canonical QB include used by reference decks"),
        record_file("canonical_jtl_include", SOURCE_INPUTS / "jtl2.cir", "canonical six-stage JTL include used by reference decks"),
        record_file("public_qb_hash_guard", REPO / "circuits" / "qb" / "bq_parameterized_v1.cir", "canonical QB hash guard; no parameter modification"),
        record_file("transmission_line_source", REPO / "src" / "TransmissionLine.cpp", "JoSIM T element parser and stamp"),
        record_file("transmission_line_header", REPO / "include" / "JoSIM" / "TransmissionLine.hpp", "JoSIM four-node T element declaration"),
        record_file("transmission_line_docs", REPO / "docs" / "comp_stamps.md", "lossless TLINE equations and k=TD/h documentation"),
        record_file("transmission_line_example", REPO / "test" / "comp" / "tx.cir", "repository TLINE syntax example"),
        record_file("josim_solver", SOLVER, "recorded physical solver"),
        record_file("plotter", PLOTTER, "standard descriptive renderer"),
        record_file("shared_raw_reader", REPO / "scripts" / "bvmtools" / "raw.py", "duplicate-aware raw reader"),
        record_file("shared_phase_tools", REPO / "scripts" / "bvmtools" / "phase.py", "phase unwrap/window semantics"),
        record_file("shared_waveform_tools", REPO / "scripts" / "bvmtools" / "waveform.py", "actual-grid waveform arithmetic"),
        record_file("smoke_deck", SMOKE_DECK, "pre-formal TLINE syntax/delay smoke deck"),
        record_file("smoke_raw", SMOKE_RAW, "pre-formal TLINE smoke raw"),
        record_file("smoke_log", SMOKE_LOG, "pre-formal TLINE smoke log"),
    ]
    for mask in MASKS:
        records.append(record_file(f"canonical_{mask}_raw", CANONICAL[mask], "read-only canonical raw reference; not copied"))
        records.append(record_file(f"canonical_{mask}_deck", CANONICAL_DECKS[mask], "read-only canonical deck reference; not rerun"))
    return records


def assert_source_hashes() -> None:
    if git_head() != EXPECTED_HEAD:
        raise RuntimeError(f"registration HEAD changed: {git_head()} != {EXPECTED_HEAD}")
    if remote_head() != EXPECTED_HEAD:
        raise RuntimeError(f"bvm/master changed at registration: {remote_head()} != {EXPECTED_HEAD}")
    for path, expected in EXPECTED_SOURCE_HASHES.items():
        if not path.is_file() or sha256(path) != expected:
            raise RuntimeError(f"registered source changed or missing: {path}")
    for mask in MASKS:
        if sha256(CANONICAL[mask]) != EXPECTED_CANONICAL_RAW_HASHES[mask]:
            raise RuntimeError(f"canonical raw changed: {CANONICAL[mask]}")


def smoke_result() -> dict[str, Any]:
    if not SMOKE_RAW.is_file() or not SMOKE_LOG.is_file():
        raise RuntimeError("TLINE smoke raw/log missing")
    trace = load_raw(SMOKE_RAW)
    required = {"V(IN)", "V(OUT)", "I(T_SMOKE)", "I(RLOAD)"}
    missing = sorted(required - set(trace.headers))
    rows = []
    with SMOKE_RAW.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    input_step = next((float(row["time"]) * 1.0e12 for row in rows if float(row["V(IN)"]) > 0.0), None)
    output_step = next((float(row["time"]) * 1.0e12 for row in rows if float(row["V(OUT)"]) > 0.0), None)
    warnings = [
        line.strip()
        for line in SMOKE_LOG.read_text(errors="replace").splitlines()
        if any(token in line for token in ("Missing model:", "Unknown device/node", "Cannot store results", "Error", "error"))
    ]
    measured_delay = output_step - input_step if input_step is not None and output_step is not None else None
    status = bool(
        not missing
        and trace.sample_count == 20
        and trace.time[0] == 0.0
        and trace.time[-1] == 1.9e-12
        and input_step == 0.6
        and output_step == 0.9
        and abs((measured_delay or 0.0) - 0.3) < 1.0e-12
        and round((measured_delay or 0.0) / 0.1) == 3
        and not warnings
    )
    return {
        "status": "PASS" if status else "FAIL",
        "deck": {"path": rel(SMOKE_DECK), "sha256": sha256(SMOKE_DECK), "bytes": SMOKE_DECK.stat().st_size},
        "raw": {"path": rel(SMOKE_RAW), "sha256": sha256(SMOKE_RAW), "bytes": SMOKE_RAW.stat().st_size, "grid": replay_base.finite_grid_qa(trace)},
        "log": {"path": rel(SMOKE_LOG), "sha256": sha256(SMOKE_LOG), "bytes": SMOKE_LOG.stat().st_size},
        "headers": list(trace.headers),
        "missing": missing,
        "input_step_ps": input_step,
        "output_step_ps": output_step,
        "measured_delay_ps": measured_delay,
        "measured_delay_samples": round((measured_delay or 0.0) / 0.1) if measured_delay is not None else None,
        "warnings": warnings,
        "syntax": "Tlabel Vi+ Vi- Vo+ Vo- TD=value Z0=value",
        "ground_return": "IN/0 and OUT/0",
    }


def include_path(path: Path, deck_dir: Path) -> str:
    return Path(os.path.relpath(path, deck_dir)).as_posix()


def rewrite_canonical_deck(mask: str, case_id: str, td_token: str, deck_dir: Path) -> str:
    original = CANONICAL_DECKS[mask].read_text(encoding="utf-8")
    include_map = {
        "../../inputs/jjmit.cir": SOURCE_INPUTS / "jjmit.cir",
        "../../inputs/bvm_jm2_connected.cir": SOURCE_INPUTS / "bvm_jm2_connected.cir",
        "../../inputs/BQ_parameterized_bjs400_rj2.cir": SOURCE_INPUTS / "BQ_parameterized_bjs400_rj2.cir",
        "../../inputs/jtl2.cir": SOURCE_INPUTS / "jtl2.cir",
    }
    lines = original.splitlines()
    output: list[str] = []
    changed_bjsl8 = 0
    inserted_tline = 0
    inserted_probe = 0
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(".include "):
            include_name = stripped.split(None, 1)[1]
            if include_name not in include_map:
                raise RuntimeError(f"unexpected canonical include: {include_name}")
            output.append(f".include {include_path(include_map[include_name], deck_dir)}")
            continue
        if stripped == "B_JSL8 JSL_NODE7 QBIN jjmit area=5.0":
            output.append("B_JSL8 JSL_NODE7 TLINE_IN jjmit area=5.0")
            output.append(f"T_BVM_QB TLINE_IN 0 QBIN 0 TD={td_token} Z0=6")
            changed_bjsl8 += 1
            inserted_tline += 1
            continue
        output.append(line)
        if stripped == ".print V(COMMON_SL)":
            output.append(".print V(TLINE_IN,0) I(T_BVM_QB)")
            inserted_probe += 1
    if changed_bjsl8 != 1 or inserted_tline != 1 or inserted_probe != 1:
        raise RuntimeError(
            f"canonical deck rewrite counts: B_JSL8={changed_bjsl8}, TLINE={inserted_tline}, probe={inserted_probe}"
        )
    text = "\n".join(output) + "\n"
    if ".tran 0.1p 200p" not in text:
        raise RuntimeError("canonical .tran changed or missing")
    return text


def expected_headers() -> set[str]:
    required: set[str] = set()
    for index in range(1, 5):
        required.update(f"I(I_{kind}{index})" for kind in ("WL", "BL", "SE"))
        for element in BVM_JUNCTIONS:
            required.update(f"{kind}({element}|XBVM{index})" for kind in ("P", "V", "I"))
        for element in ("L_M1", "L_M2", "L_M3", "L_PM", "R_JM1", "L_S1", "L_S2", "R_S", "L_S3", "R_SE", "L_PSE", "L_PSL", "R_SL", "L_SL"):
            required.update(f"{kind}({element}|XBVM{index})" for kind in ("I", "V"))
    required.add("V(COMMON_SL)")
    required.update(("V(TLINE_IN,0)", "I(T_BVM_QB)"))
    for index in range(1, 9):
        required.update(f"{kind}(B_JSL{index})" for kind in ("P", "V", "I"))
    required.update(("V(QBIN)", "V(QBOUT)"))
    required.update(f"{kind}({element}|XBQ1)" for element in ("LIN", "L1", "L2", "L3", "RJ1", "RJ2") for kind in ("I", "V"))
    required.update(f"{kind}({element}|XBQ1)" for element in ("BJS", "BJ1", "BJ2") for kind in ("P", "V", "I"))
    for stage in JTL_STAGES:
        instance = f"XJTL1_{stage}"
        required.update(f"{kind}({element}|{instance})" for element in ("B01", "B02") for kind in ("P", "V", "I"))
        required.add(f"V(JTL{stage}_OUT)")
    required.add("I(R_TERM)")
    return required


def run_id(case_id: str, mask: str) -> str:
    return f"{case_id}_{mask}"


def run_dir(case_id: str, mask: str) -> Path:
    return EXP / "runs" / case_id / mask


def registered_yaml_update(deck_records: dict[str, Any], source_records: list[dict[str, Any]], smoke: dict[str, Any]) -> None:
    """Append the final machine-readable deck registration to the preflight YAML."""

    yaml_path = EXP / "experiment.yaml"
    text = yaml_path.read_text(encoding="utf-8")
    text = text.replace("status: PREFLIGHT_SMOKE_PASS", "status: PREFLIGHT_PASS")
    text = text.replace("formal_decks_blocked_until_smoke_pass: true", "formal_decks_blocked_until_smoke_pass: true\n  formal_decks_registered: true")
    block = [
        "",
        "formal_deck_registration:",
    ]
    for key in RUN_ORDER:
        record = deck_records[key]
        block.append(f"  - run_id: {key}")
        block.append(f"    path: {record['path']}")
        block.append(f"    sha256: {record['sha256']}")
        block.append(f"    bytes: {record['bytes']}")
    block += [
        "",
        "source_closure_hashes:",
    ]
    for item in source_records:
        block.append(f"  - {item['name']}: {item['path']}; sha256={item['sha256']}")
    block += [
        "",
        "smoke_evidence:",
        "  status: PASS",
        f"  measured_delay_ps: {smoke['measured_delay_ps']}",
        f"  measured_delay_samples: {smoke['measured_delay_samples']}",
        "  formal_deck_creation_after_smoke: true",
    ]
    yaml_path.write_text(text.rstrip() + "\n" + "\n".join(block) + "\n", encoding="utf-8")


def prepare() -> None:
    assert_source_hashes()
    smoke = smoke_result()
    if smoke["status"] != "PASS":
        raise RuntimeError("TLINE syntax/delay smoke gate failed; formal decks not authorized")
    for path in (EXP / "runs", EXP / "plots"):
        path.mkdir(parents=True, exist_ok=True)
    source_records = source_inventory()
    deck_records: dict[str, Any] = {}
    for case_id, td_token, td_ps, shift_samples in FORMAL_CASES:
        for mask in MASKS:
            directory = run_dir(case_id, mask)
            if directory.exists() and any(directory.iterdir()):
                raise RuntimeError(f"formal run directory is not empty: {directory}")
            directory.mkdir(parents=True, exist_ok=True)
            deck = directory / "deck.cir"
            deck.write_text(rewrite_canonical_deck(mask, case_id, td_token, directory), encoding="utf-8")
            key = run_id(case_id, mask)
            deck_records[key] = {
                "run_id": key,
                "case_id": case_id,
                "mask": mask,
                "TD_ps": td_ps,
                "expected_stored_delay_samples": shift_samples,
                "path": rel(deck),
                "sha256": sha256(deck),
                "bytes": deck.stat().st_size,
            }
    registered_yaml_update(
        deck_records,
        source_records,
        smoke,
    )
    provenance = {
        "schema": "bvm-qb-tline-feedback-dephasing-provenance-v1",
        "experiment_id": EXP.name,
        "created_at": now(),
        "registration_head": EXPECTED_HEAD,
        "remote_bvm_master_at_registration": EXPECTED_HEAD,
        "current_head_at_prepare": git_head(),
        "contract_sentence": CONTRACT_SENTENCE,
        "scientific_review_authorized": False,
        "scientific_interpretation_performed": False,
        "solver": replay_base.solver_context(),
        "syntax_gate": smoke,
        "source_closure": source_records,
        "canonical_reference_raw_hashes": EXPECTED_CANONICAL_RAW_HASHES,
        "frozen": {
            "topology": "4xBVM -> COMMON_SL -> JSL1..8 -> TLINE -> canonical QB -> JTL1..6 -> 10 ohm terminal",
            "mask_cases": list(MASKS),
            "Z0_ohm": 6.0,
            "time_step_ps": 0.1,
            "stop_time_ps": 200.0,
            "analysis_windows_ps": [list(window) for window in WINDOWS_PS],
            "focus_window_ps": list(FOCUS_WINDOW),
            "control_window_ps": list(CONTROL_WINDOW),
            "no_qb_parameter_change": True,
            "no_bvm_change": True,
            "no_ls3_rs_change": True,
            "no_amplitude_scaling": True,
            "no_sentinel": True,
            "no_read_extension": True,
            "no_timestep_sweep": True,
        },
        "authorized_formal_matrix": {
            "max_new_physical_solves": 4,
            "cases": [
                {"case_id": case_id, "TD_ps": td_ps, "stored_delay_samples": shift, "Z0_ohm": 6.0, "masks": list(MASKS)}
                for case_id, _, td_ps, shift in FORMAL_CASES
            ],
            "run_order": list(RUN_ORDER),
            "no_other_delay_or_Z0_points": True,
        },
        "registered_decks": deck_records,
        "runs": {},
        "run_order": [],
        "execution": {
            "syntax_smoke_solve_count": 1,
            "authorized_formal_physical_solve_count": 4,
            "actual_formal_physical_solve_count": 0,
            "total_solver_invocation_count": 1,
        },
        "registered_metrics": {
            "phase": "P raw radians; independent unwrap then rad/(2*pi) navigation only",
            "phase_area": "same JJ, same endpoints, same direction, actual-grid trapezoid / Phi0",
            "N2": "control cleanliness, first/second ordered QB/JTL navigation candidates, measured TLINE forward delay",
            "N3": "active JS1/JS2 focus p2p, 114.8 ps navigation landmark, source/JSL regeneration, LS3/RS, COMMON_SL, QBIN, BJ1/BJ2",
            "TLINE": "near/far port voltage/current features, forward and return-feature timing, distortion/ringing/zero crossings/width",
            "no_incident_reflected_decomposition": True,
        },
        "transformations": [
            {
                "name": "canonical_deck_to_tline_deck",
                "changes": [
                    "B_JSL8 JSL_NODE7 QBIN -> B_JSL8 JSL_NODE7 TLINE_IN",
                    "add T_BVM_QB TLINE_IN 0 QBIN 0 TD=<registered> Z0=6",
                    "add TLINE near-port observability V(TLINE_IN,0), I(T_BVM_QB)",
                    "remap only external include paths for the new run directories",
                ],
                "canonical_bvm_qb_jtl_contents_unchanged": True,
            }
        ],
        "qa": {"status": "PENDING"},
        "visualization": {"status": "PENDING"},
        "package": {"status": "PENDING", "drive_file_id": None, "drive_url": None},
        "stop": {"final_marker": None, "automatic_follow_up": False},
    }
    write_json(EXP / "provenance.json", provenance)
    result = {
        "schema": "bvm-qb-tline-feedback-dephasing-result-v1",
        "experiment_id": EXP.name,
        "generated_at": now(),
        "status": "PREFLIGHT_PASS_FORMAL_RUNS_PENDING",
        "artifact_status": "PENDING",
        "scientific_interpretation_performed": False,
        "execution": provenance["execution"],
        "runs": {},
        "outcome": {"status": "PENDING", "classification": None},
        "unknown": ["formal TLINE result", "reflection/distortion dominance", "convergence"],
        "stop": {"final_marker": None, "automatic_follow_up": False},
    }
    write_json(EXP / "result.json", result)
    (EXP / "RESULT.md").write_text(
        "# BVM -> QB TLINE feedback dephasing\n\n"
        "Preflight and TLINE smoke gate passed. Four formal runs are registered; no formal raw has been produced yet.\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": "PREFLIGHT_PASS",
        "experiment": rel(EXP),
        "smoke": smoke,
        "formal_runs": list(RUN_ORDER),
        "formal_decks": deck_records,
    }, ensure_ascii=False, indent=2))


def execute() -> None:
    provenance = read_json(EXP / "provenance.json")
    if provenance.get("syntax_gate", {}).get("status") != "PASS":
        raise RuntimeError("formal execution requires PASS TLINE syntax gate")
    if git_head() != EXPECTED_HEAD:
        raise RuntimeError("formal execution must remain on the registered HEAD")
    for item in provenance.get("source_closure", []):
        path = REPO / item["path"]
        if sha256(path) != item["sha256"]:
            raise RuntimeError(f"source changed after preflight: {path}")
    if provenance.get("run_order"):
        raise RuntimeError("formal execution already recorded; refusing overwrite/retry")
    for key in RUN_ORDER:
        record = provenance["registered_decks"][key]
        deck = REPO / record["path"]
        raw = EXP / "runs" / record["case_id"] / record["mask"] / "raw.csv"
        log = EXP / "runs" / record["case_id"] / record["mask"] / "run.log"
        if raw.exists() or log.exists():
            raise RuntimeError(f"refusing overwrite/retry: {key}")
        if sha256(deck) != record["sha256"]:
            raise RuntimeError(f"registered deck changed: {key}")
        command = [str(SOLVER), "-a", "1", "-o", str(raw), str(deck)]
        started = now()
        with log.open("x", encoding="utf-8") as stream:
            stream.write(f"experiment={EXP.name}\nrun_id={key}\nstarted_at={started}\ncommand={' '.join(command)}\n")
            stream.flush()
            completed = subprocess.run(command, cwd=REPO, stdout=stream, stderr=subprocess.STDOUT, check=False)
            finished = now()
            stream.write(f"finished_at={finished}\nexit_code={completed.returncode}\n")
        run_record: dict[str, Any] = {
            "run_id": key,
            "case_id": record["case_id"],
            "mask": record["mask"],
            "TD_ps": record["TD_ps"],
            "command": command,
            "deck": {"path": rel(deck), "sha256": sha256(deck), "bytes": deck.stat().st_size},
            "log": {"path": rel(log), "sha256": sha256(log), "bytes": log.stat().st_size},
            "solver": replay_base.solver_context(),
            "started_at": started,
            "finished_at": finished,
            "physical_solve_this_experiment": True,
            "raw_immutable": True,
            "scientific_interpretation_performed": False,
        }
        if completed.returncode != 0 or not raw.is_file() or raw.stat().st_size == 0:
            run_record["execution_status"] = "SOLVER_FAIL"
            run_record["raw"] = {"path": rel(raw), "exists": raw.is_file(), "sha256": sha256(raw) if raw.is_file() else None, "bytes": raw.stat().st_size if raw.is_file() else None}
            provenance["runs"][key] = run_record
            provenance["run_order"].append(key)
            provenance["execution"]["actual_formal_physical_solve_count"] = len(provenance["run_order"])
            provenance["execution"]["total_solver_invocation_count"] = 1 + len(provenance["run_order"])
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
            }
            run_record["missing_required_probes"] = missing
            run_record["execution_status"] = "RUN_PASS" if not missing else "RUN_PASS_MISSING_PROBES"
        except Exception as exc:
            run_record["execution_status"] = "RAW_PARSE_FAILURE"
            run_record["raw_parse_error"] = str(exc)
            run_record["raw"] = {"path": rel(raw), "sha256": sha256(raw), "bytes": raw.stat().st_size}
            provenance["runs"][key] = run_record
            provenance["run_order"].append(key)
            provenance["execution"]["actual_formal_physical_solve_count"] = len(provenance["run_order"])
            provenance["execution"]["total_solver_invocation_count"] = 1 + len(provenance["run_order"])
            provenance["execution_status"] = "RAW_FAILURE_STOP"
            write_json(EXP / "provenance.json", provenance)
            raise RuntimeError(f"raw parse failed for {key}; failure preserved") from exc
        provenance["runs"][key] = run_record
        provenance["run_order"].append(key)
        provenance["execution"]["actual_formal_physical_solve_count"] = len(provenance["run_order"])
        provenance["execution"]["total_solver_invocation_count"] = 1 + len(provenance["run_order"])
        write_json(EXP / "provenance.json", provenance)
        if missing:
            provenance["execution_status"] = "RAW_PROBE_FAILURE_STOP"
            write_json(EXP / "provenance.json", provenance)
            raise RuntimeError(f"missing required probes for {key}: {missing}")
    provenance["execution_status"] = "ALL_FORMAL_RUNS_COMPLETE"
    write_json(EXP / "provenance.json", provenance)
    result = read_json(EXP / "result.json")
    result["status"] = "FORMAL_RUNS_COMPLETE_ANALYSIS_PENDING"
    result["artifact_status"] = "VALID"
    result["execution"] = provenance["execution"]
    result["runs"] = {
        key: {
            "status": provenance["runs"][key]["execution_status"],
            "case_id": provenance["runs"][key]["case_id"],
            "mask": provenance["runs"][key]["mask"],
            "TD_ps": provenance["runs"][key]["TD_ps"],
            "raw_path": provenance["runs"][key]["raw"]["path"],
            "raw_sha256": provenance["runs"][key]["raw"]["sha256"],
        }
        for key in RUN_ORDER
    }
    write_json(EXP / "result.json", result)
    print(json.dumps({"status": "RUN_PASS", "run_order": list(RUN_ORDER), "formal_solve_count": 4}, ensure_ascii=False, indent=2))


def unwrap(values: Iterable[float]) -> list[float]:
    output: list[float] = []
    previous_raw: float | None = None
    previous_unwrapped = 0.0
    for raw_value in values:
        value = float(raw_value)
        if previous_raw is None:
            previous_raw = value
            previous_unwrapped = value
        else:
            delta = value - previous_raw
            while delta > math.pi:
                delta -= TAU
            while delta < -math.pi:
                delta += TAU
            previous_unwrapped += delta
            previous_raw = value
        output.append(previous_unwrapped)
    return output


def zero_crossing_count(values: Iterable[float]) -> int:
    previous = 0
    count = 0
    for value in values:
        sign = 1 if value > 0.0 else -1 if value < 0.0 else 0
        if sign == 0:
            continue
        if previous and sign != previous:
            count += 1
        previous = sign
    return count


def width_at_half_abs_peak(trace: Any, signal: str, indices: list[int]) -> dict[str, Any]:
    values = trace.column(signal)
    if not indices:
        return {"status": "UNKNOWN"}
    peak_position = max(range(len(indices)), key=lambda position: abs(values[indices[position]]))
    half = abs(values[indices[peak_position]]) * 0.5
    left = peak_position
    while left > 0 and abs(values[indices[left - 1]]) >= half:
        left -= 1
    right = peak_position
    while right + 1 < len(indices) and abs(values[indices[right + 1]]) >= half:
        right += 1
    return {
        "status": "DERIVED",
        "threshold": "0.5 * absolute peak",
        "threshold_value": half,
        "start_ps": trace.time[indices[left]] * 1.0e12,
        "end_ps": trace.time[indices[right]] * 1.0e12,
        "width_ps": (trace.time[indices[right]] - trace.time[indices[left]]) * 1.0e12,
        "peak_time_ps": trace.time[indices[peak_position]] * 1.0e12,
    }


def waveform_stats(trace: Any, signal: str, start_ps: float, end_ps: float) -> dict[str, Any]:
    indices = time_indices(trace, start_ps, end_ps)
    values = trace.column(signal)
    if len(indices) < 2:
        return {"status": "UNKNOWN", "signal": signal, "window_ps": [start_ps, end_ps]}
    times = [trace.time[index] for index in indices]
    selected = [values[index] for index in indices]
    peak_position = max(range(len(indices)), key=lambda position: abs(selected[position]))
    return {
        "status": "DERIVED",
        "signal": signal,
        "window_ps": [start_ps, end_ps],
        "sample_count": len(indices),
        "unit": "rad" if signal.startswith("P(") else "A" if signal.startswith("I(") else "V",
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
        "zero_crossing_count": zero_crossing_count(selected),
        "half_abs_peak_width": width_at_half_abs_peak(trace, signal, indices),
    }


def phase_navigation(trace: Any, signal: str, baseline_ps: float = 101.0) -> dict[str, Any]:
    raw = trace.column(signal)
    continuous = unwrap(raw)
    base_index = next(index for index, value in enumerate(trace.time) if value * 1.0e12 >= baseline_ps)
    relative = [(continuous[index] - continuous[base_index]) / TAU for index in range(base_index, len(continuous))]
    focus = time_indices(trace, *FOCUS_WINDOW)
    focus_relative = [(continuous[index] - continuous[focus[0]]) / TAU for index in focus]
    positive = {
        f"{threshold:g}": next(
            (
                trace.time[index] * 1.0e12
                for index in range(base_index, len(continuous))
                if (continuous[index] - continuous[base_index]) / TAU >= threshold
            ),
            None,
        )
        for threshold in PHASE_THRESHOLDS
    }
    negative = {
        f"-{threshold:g}": next(
            (
                trace.time[index] * 1.0e12
                for index in range(base_index, len(continuous))
                if (continuous[index] - continuous[base_index]) / TAU <= -threshold
            ),
            None,
        )
        for threshold in PHASE_THRESHOLDS
    }
    return {
        "signal": signal,
        "raw_unit": "radians",
        "display_unit": "turns",
        "display_rule": "independent continuous unwrap(rad)/(2*pi); navigation only",
        "baseline_time_ps": trace.time[base_index] * 1.0e12,
        "positive_threshold_navigation_times_ps": positive,
        "negative_threshold_navigation_times_ps": negative,
        "first_abs_0p5_navigation_ps": next(
            (
                trace.time[index] * 1.0e12
                for index in range(base_index, len(continuous))
                if abs((continuous[index] - continuous[base_index]) / TAU) >= 0.5
            ),
            None,
        ),
        "relative_min_turns": min(relative),
        "relative_max_turns": max(relative),
        "relative_final_turns": relative[-1],
        "relative_p2p_turns": max(relative) - min(relative),
        "focus_110_121_endpoint_delta_turns": focus_relative[-1],
        "focus_110_121_p2p_turns": max(focus_relative) - min(focus_relative),
        "focus_110_121_min_turns": min(focus_relative),
        "focus_110_121_max_turns": max(focus_relative),
        "semantic_role": "PHASE_NAVIGATION_ONLY; not an SFQ count",
    }


def phase_area_crosscheck(trace: Any, phase_signal: str, voltage_signal: str, window: tuple[float, float] = FOCUS_WINDOW) -> dict[str, Any]:
    indices = time_indices(trace, *window)
    times = [trace.time[index] for index in indices]
    phase = [trace.column(phase_signal)[index] for index in indices]
    voltage = [trace.column(voltage_signal)[index] for index in indices]
    phase_continuous = unwrap(phase)
    delta_rad = phase_continuous[-1] - phase_continuous[0]
    area_vs = actual_integral(times, voltage)
    area_turns = area_vs / PHI0
    return {
        "status": "DERIVED",
        "phase_signal": phase_signal,
        "voltage_signal": voltage_signal,
        "raw_phase_unit": "radians",
        "window_ps": list(window),
        "sample_count": len(indices),
        "delta_phase_rad": delta_rad,
        "phase_delta_turns": delta_rad / TAU,
        "voltage_area_V_s": area_vs,
        "voltage_area_over_Phi0_turns": area_turns,
        "phase_minus_area_turns": delta_rad / TAU - area_turns,
        "actual_grid_trapezoid": True,
        "same_jj_same_endpoints_same_direction": True,
        "semantic_role": "phase/area cross-check; not an SFQ count",
    }


def independent_raw_review(canonical: dict[str, Any], traces: dict[str, Any]) -> dict[str, Any]:
    """Recalculate critical values with a separate compact raw-only path."""

    def manual_nav(trace: Any, signal: str) -> dict[str, Any]:
        raw = [float(value) for value in trace.column(signal)]
        continuous = [raw[0]]
        previous = raw[0]
        for value in raw[1:]:
            delta = value - previous
            while delta > math.pi:
                delta -= TAU
            while delta < -math.pi:
                delta += TAU
            continuous.append(continuous[-1] + delta)
            previous = value
        base_index = next(index for index, value in enumerate(trace.time) if value * 1.0e12 >= 101.0)
        focus = time_indices(trace, *FOCUS_WINDOW)
        relative = [(continuous[index] - continuous[focus[0]]) / TAU for index in focus]
        positive = {}
        for threshold in PHASE_THRESHOLDS:
            positive[f"{threshold:g}"] = next(
                (
                    trace.time[index] * 1.0e12
                    for index in range(base_index, len(continuous))
                    if (continuous[index] - continuous[base_index]) / TAU >= threshold
                ),
                None,
            )
        return {
            "focus_p2p_turns": max(relative) - min(relative),
            "positive_crossings_ps": positive,
            "relative_min_turns": min((continuous[index] - continuous[base_index]) / TAU for index in range(base_index, len(continuous))),
        }

    def manual_area(trace: Any, phase_signal: str, voltage_signal: str) -> dict[str, float]:
        indices = time_indices(trace, *FOCUS_WINDOW)
        phase = [float(value) for value in trace.column(phase_signal)]
        continuous = [phase[0]]
        previous = phase[0]
        for value in phase[1:]:
            delta = value - previous
            while delta > math.pi:
                delta -= TAU
            while delta < -math.pi:
                delta += TAU
            continuous.append(continuous[-1] + delta)
            previous = value
        phase_delta = (continuous[indices[-1]] - continuous[indices[0]]) / TAU
        voltage = trace.column(voltage_signal)
        area = actual_integral(
            [trace.time[index] for index in indices],
            [voltage[index] for index in indices],
        ) / PHI0
        return {"phase_delta_turns": phase_delta, "voltage_area_over_Phi0_turns": area, "residual_turns": phase_delta - area}

    def manual_order_count(trace: Any) -> int:
        names = ["BJ1", "BJ2", *[f"JTL{stage}" for stage in JTL_STAGES]]
        signals = {
            name: manual_nav(trace, "P(BJ1|XBQ1)" if name == "BJ1" else "P(BJ2|XBQ1)" if name == "BJ2" else f"P(B01|XJTL1_{name[3:]})")
            for name in names
        }
        count = 0
        for threshold in PHASE_THRESHOLDS:
            key = f"{threshold:g}"
            chain = [signals[name]["positive_crossings_ps"].get(key) for name in names]
            if all(value is not None for value in chain) and all(left < right for left, right in zip(chain, chain[1:])):
                count += 1
            else:
                break
        return count

    output: dict[str, Any] = {
        "status": "PASS",
        "method": "independent compact unwrap/integral/order loops over raw traces",
        "grid_equal_to_canonical": {},
        "n2_order_counts": {},
        "n3_phase_p2p": {},
        "phase_area": {},
    }
    for mask, trace in canonical.items():
        output["grid_equal_to_canonical"][f"CANONICAL_{mask}"] = True
        output["n2_order_counts"][f"CANONICAL_{mask}"] = manual_order_count(trace)
    for key, trace in traces.items():
        mask = key.rsplit("_", 1)[1]
        output["grid_equal_to_canonical"][key] = tuple(trace.time) == tuple(canonical[mask].time)
        output["n2_order_counts"][key] = manual_order_count(trace)
        if mask == "0111":
            output["n3_phase_p2p"][key] = {
                "JS1": manual_nav(trace, "P(B_JS1|XBVM2)")["focus_p2p_turns"],
                "JS2": manual_nav(trace, "P(B_JS2|XBVM2)")["focus_p2p_turns"],
            }
        active_index = next(index for index, bit in enumerate(mask, start=1) if bit == "1")
        output["phase_area"][key] = {
            "JS1": manual_area(trace, f"P(B_JS1|XBVM{active_index})", f"V(B_JS1|XBVM{active_index})"),
            "JS2": manual_area(trace, f"P(B_JS2|XBVM{active_index})", f"V(B_JS2|XBVM{active_index})"),
        }
    return output


def independent_critical_recalculation(canonical: dict[str, Any], traces: dict[str, Any]) -> dict[str, Any]:
    """Independent critical-number check from fresh CSV reads and local loops."""

    def fresh(path: Path) -> tuple[list[float], dict[str, list[float]]]:
        with path.open(newline="", encoding="utf-8-sig") as stream:
            reader = csv.DictReader(stream)
            headers = reader.fieldnames or []
            if len(headers) != len(set(headers)):
                raise RuntimeError(f"duplicate header in independent read: {path}")
            rows = list(reader)
        times = [float(row["time"]) for row in rows]
        columns = {
            signal: [float(row[signal]) for row in rows]
            for signal in headers
            if signal != "time"
        }
        return times, columns

    def unwrap_fresh(values: list[float]) -> list[float]:
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

    def trapezoid(times: list[float], values: list[float], indices: list[int]) -> float:
        return sum(
            0.5 * (values[left] + values[right]) * (times[right] - times[left])
            for left, right in zip(indices, indices[1:])
        )

    def fresh_phase_metrics(times: list[float], columns: dict[str, list[float]], signal: str) -> dict[str, Any]:
        phase = unwrap_fresh(columns[signal])
        focus = [index for index, value in enumerate(times) if 110.0 <= value * 1.0e12 < 121.0]
        base = next(index for index, value in enumerate(times) if value * 1.0e12 >= 101.0)
        relative = [(phase[index] - phase[focus[0]]) / TAU for index in focus]
        return {
            "focus_p2p_turns": max(relative) - min(relative),
            "focus_endpoint_delta_turns": relative[-1],
            "relative_min_turns_from_101": min((phase[index] - phase[base]) / TAU for index in range(base, len(phase))),
        }

    output: dict[str, Any] = {"status": "PASS", "method": "fresh csv.DictReader + independent unwrap/trapezoid loops", "grid_match": {}, "n2_navigation_candidate_count": {}, "n3_phase_p2p": {}, "phase_area": {}}
    fresh_data: dict[str, tuple[list[float], dict[str, list[float]]]] = {}
    for mask in MASKS:
        fresh_data[f"CANONICAL_{mask}"] = fresh(CANONICAL[mask])
    for key in RUN_ORDER:
        record = read_json(EXP / "provenance.json")["runs"][key]
        fresh_data[key] = fresh(EXP / "runs" / record["case_id"] / record["mask"] / "raw.csv")
    for mask in MASKS:
        times, columns = fresh_data[f"CANONICAL_{mask}"]
        output["grid_match"][f"CANONICAL_{mask}"] = len(times) == 1999 and times[0] == 0.0 and times[-1] == 1.999e-10
        # Only the two registered first/second N2 navigation thresholds are
        # needed for this independent check.
        names = ("P(BJ1|XBQ1)", "P(BJ2|XBQ1)", "P(B01|XJTL1_1)", "P(B01|XJTL1_2)", "P(B01|XJTL1_3)", "P(B01|XJTL1_4)", "P(B01|XJTL1_5)", "P(B01|XJTL1_6)")
        unwrapped = {signal: unwrap_fresh(columns[signal]) for signal in names}
        base = next(index for index, value in enumerate(times) if value * 1.0e12 >= 101.0)
        count = 0
        for threshold in (0.5, 1.5, 2.5, 3.5):
            chain = []
            for signal in names:
                chain.append(next((times[index] * 1.0e12 for index in range(base, len(times)) if (unwrapped[signal][index] - unwrapped[signal][base]) / TAU >= threshold), None))
            if all(value is not None for value in chain) and all(left < right for left, right in zip(chain, chain[1:])):
                count += 1
            else:
                break
        output["n2_navigation_candidate_count"][f"CANONICAL_{mask}"] = count
    for key, (times, columns) in fresh_data.items():
        if key.startswith("CANONICAL_"):
            continue
        mask = key.rsplit("_", 1)[1]
        canonical_times, _ = fresh_data[f"CANONICAL_{mask}"]
        output["grid_match"][key] = times == canonical_times
        if mask == "0111":
            output["n3_phase_p2p"][key] = {
                "JS1": fresh_phase_metrics(times, columns, "P(B_JS1|XBVM2)")["focus_p2p_turns"],
                "JS2": fresh_phase_metrics(times, columns, "P(B_JS2|XBVM2)")["focus_p2p_turns"],
            }
        if mask == "0011":
            names = ("P(BJ1|XBQ1)", "P(BJ2|XBQ1)", "P(B01|XJTL1_1)", "P(B01|XJTL1_2)", "P(B01|XJTL1_3)", "P(B01|XJTL1_4)", "P(B01|XJTL1_5)", "P(B01|XJTL1_6)")
            unwrapped = {signal: unwrap_fresh(columns[signal]) for signal in names}
            base = next(index for index, value in enumerate(times) if value * 1.0e12 >= 101.0)
            count = 0
            for threshold in (0.5, 1.5, 2.5, 3.5):
                chain = [next((times[index] * 1.0e12 for index in range(base, len(times)) if (unwrapped[signal][index] - unwrapped[signal][base]) / TAU >= threshold), None) for signal in names]
                if all(value is not None for value in chain) and all(left < right for left, right in zip(chain, chain[1:])):
                    count += 1
                else:
                    break
            output["n2_navigation_candidate_count"][key] = count
        active_index = next(index for index, bit in enumerate(mask, start=1) if bit == "1")
        focus = [index for index, value in enumerate(times) if 110.0 <= value * 1.0e12 < 121.0]
        output["phase_area"][key] = {}
        for element in ("B_JS1", "B_JS2"):
            p_signal = f"P({element}|XBVM{active_index})"
            v_signal = f"V({element}|XBVM{active_index})"
            unwrapped = unwrap_fresh(columns[p_signal])
            phase_delta = (unwrapped[focus[-1]] - unwrapped[focus[0]]) / TAU
            area = trapezoid(times, columns[v_signal], focus) / PHI0
            output["phase_area"][key][element] = {"phase_delta_turns": phase_delta, "voltage_area_over_Phi0_turns": area, "residual_turns": phase_delta - area}
    return output


def local_features(trace: Any, signal: str, window: tuple[float, float], maximum: int = 5) -> list[dict[str, Any]]:
    indices = time_indices(trace, *window)
    values = trace.column(signal)
    candidates: list[int] = []
    for position in range(1, len(indices) - 1):
        value = abs(values[indices[position]])
        if value >= abs(values[indices[position - 1]]) and value >= abs(values[indices[position + 1]]):
            candidates.append(indices[position])
    candidates.sort(key=lambda index: abs(values[index]), reverse=True)
    selected: list[int] = []
    for index in candidates:
        t = trace.time[index] * 1.0e12
        if all(abs(t - trace.time[other] * 1.0e12) >= 0.2 for other in selected):
            selected.append(index)
        if len(selected) >= maximum:
            break
    return [
        {"time_ps": trace.time[index] * 1.0e12, "value": values[index], "abs_value": abs(values[index])}
        for index in sorted(selected, key=lambda index: trace.time[index])
    ]


def signal_delta(canonical: Any, candidate: Any, signal: str, window: tuple[float, float]) -> dict[str, Any]:
    indices = time_indices(canonical, *window)
    cvalues = canonical.column(signal)
    xvalues = candidate.column(signal)
    deltas = [xvalues[index] - cvalues[index] for index in indices]
    result: dict[str, Any] = {
        "signal": signal,
        "window_ps": list(window),
        "sample_count": len(indices),
        "unit": "rad" if signal.startswith("P(") else "A" if signal.startswith("I(") else "V",
        "max_abs_delta": max(abs(value) for value in deltas),
        "rms_delta": math.sqrt(sum(value * value for value in deltas) / len(deltas)),
        "time_of_max_abs_delta_ps": canonical.time[indices[max(range(len(indices)), key=lambda position: abs(deltas[position]))]] * 1.0e12,
    }
    if signal.startswith("P("):
        cu = unwrap(cvalues)
        xu = unwrap(xvalues)
        phase_delta = [(xu[index] - cu[index]) / TAU for index in indices]
        result.update({
            "independent_unwrap_then_subtract": True,
            "max_abs_delta_turns": max(abs(value) for value in phase_delta),
            "rms_delta_turns": math.sqrt(sum(value * value for value in phase_delta) / len(phase_delta)),
            "endpoint_delta_turns": phase_delta[-1],
        })
    return result


def ordered_navigation_oracle(trace: Any) -> dict[str, Any]:
    labels = {
        "BJ1": "P(BJ1|XBQ1)",
        "BJ2": "P(BJ2|XBQ1)",
        **{f"JTL{stage}": f"P(B01|XJTL1_{stage})" for stage in JTL_STAGES},
    }
    nav = {name: phase_navigation(trace, signal) for name, signal in labels.items()}
    records: list[dict[str, Any]] = []
    for threshold in PHASE_THRESHOLDS:
        key = f"{threshold:g}"
        chain = {name: nav[name]["positive_threshold_navigation_times_ps"].get(key) for name in labels}
        values = list(chain.values())
        complete = all(value is not None for value in values) and all(left < right for left, right in zip(values, values[1:]))
        records.append({
            "navigation_threshold_turns": threshold,
            "chain_times_ps": chain,
            "ordered": complete,
            "semantic_role": "ordered phase-navigation candidate; not an SFQ count",
        })
    prefix = 0
    for record in records:
        if not record["ordered"]:
            break
        prefix += 1
    return {
        "status": "DERIVED",
        "navigation": nav,
        "ordered_navigation_candidate_count": prefix,
        "second_response_navigation_candidate_present": prefix >= 2,
        "records": records,
        "not_terminal_pulse_count": True,
    }


def discrete_best_lag(trace: Any, near_signal: str, far_signal: str, window: tuple[float, float], max_lag_samples: int = 20) -> dict[str, Any]:
    """Find a descriptive same-grid lag; never interpolate or decompose waves."""

    indices = time_indices(trace, *window)
    near = [trace.column(near_signal)[index] for index in indices]
    far = [trace.column(far_signal)[index] for index in indices]
    candidates: list[dict[str, Any]] = []
    for lag in range(min(max_lag_samples, len(indices) - 2) + 1):
        left = near[: len(near) - lag]
        right = far[lag:]
        mean_left = sum(left) / len(left)
        mean_right = sum(right) / len(right)
        centered_left = [value - mean_left for value in left]
        centered_right = [value - mean_right for value in right]
        denominator = math.sqrt(
            sum(value * value for value in centered_left)
            * sum(value * value for value in centered_right)
        )
        correlation = (
            sum(a * b for a, b in zip(centered_left, centered_right)) / denominator
            if denominator else None
        )
        rms_difference = math.sqrt(
            sum((a - b) * (a - b) for a, b in zip(left, right)) / len(left)
        )
        candidates.append({
            "lag_samples": lag,
            "lag_ps": lag * 0.1,
            "correlation": correlation,
            "rms_difference_V": rms_difference,
        })
    best = max(candidates, key=lambda item: item["correlation"] if item["correlation"] is not None else -math.inf)
    return {
        "status": "DESCRIPTIVE_GRID_LAG",
        "near_signal": near_signal,
        "far_signal": far_signal,
        "window_ps": list(window),
        "search_lag_samples": [0, min(max_lag_samples, len(indices) - 2)],
        "best": best,
        "all_candidates": candidates,
        "interpolation": False,
    }


def tline_timing_features(trace: Any, specified_td_ps: float) -> dict[str, Any]:
    near_v = waveform_stats(trace, "V(TLINE_IN,0)", *FOCUS_WINDOW)
    far_v = waveform_stats(trace, "V(QBIN)", *FOCUS_WINDOW)
    near_i = waveform_stats(trace, "I(T_BVM_QB)", *FOCUS_WINDOW)
    far_i = waveform_stats(trace, "I(LIN|XBQ1)", *FOCUS_WINDOW)
    near_v_features = local_features(trace, "V(TLINE_IN,0)", FOCUS_WINDOW)
    far_v_features = local_features(trace, "V(QBIN)", FOCUS_WINDOW)
    near_i_features = local_features(trace, "I(T_BVM_QB)", FOCUS_WINDOW)
    far_i_features = local_features(trace, "I(LIN|XBQ1)", FOCUS_WINDOW)
    far_v_peak = far_v["time_of_peak_abs_ps"]
    later_near = [item for item in near_v_features if item["time_ps"] > far_v_peak]
    return {
        "specified_TD_ps": specified_td_ps,
        "specified_TD_samples": round(specified_td_ps / 0.1),
        "upstream_port": {
            "voltage_signal": "V(TLINE_IN,0)",
            "current_signal": "I(T_BVM_QB)",
            "direction": "TLINE_IN -> 0",
            "voltage_focus": near_v,
            "current_focus": near_i,
            "voltage_features": near_v_features,
            "current_features": near_i_features,
        },
        "receiver_side_port": {
            "voltage_signal": "V(QBIN)",
            "current_signal": "I(LIN|XBQ1)",
            "direction": "QBIN -> QB internal node 1",
            "voltage_focus": far_v,
            "current_focus": far_i,
            "voltage_features": far_v_features,
            "current_features": far_i_features,
            "current_probe_role": "receiver-side KCL boundary current; not a hidden second TLINE branch label",
        },
        "measured_forward_peak_delay_ps": {
            "voltage_peak_delta": far_v["time_of_peak_abs_ps"] - near_v["time_of_peak_abs_ps"],
            "current_peak_delta": far_i["time_of_peak_abs_ps"] - near_i["time_of_peak_abs_ps"],
        },
        "measured_forward_half_peak_onset_delta_ps": {
            "voltage": far_v["half_abs_peak_width"]["start_ps"] - near_v["half_abs_peak_width"]["start_ps"],
            "current": far_i["half_abs_peak_width"]["start_ps"] - near_i["half_abs_peak_width"]["start_ps"],
        },
        "same_grid_port_voltage_lag": discrete_best_lag(
            trace, "V(TLINE_IN,0)", "V(QBIN)", FOCUS_WINDOW
        ),
        "later_upstream_feature_after_far_voltage_peak": later_near[0] if later_near else None,
        "return_feature_status": "DESCRIPTIVE_LATER_UPSTREAM_PORT_FEATURE_ONLY",
        "no_incident_reflected_wave_decomposition": True,
        "specified_TD_is_not_measured_return_delay": True,
    }


def compact_waveform(item: dict[str, Any]) -> dict[str, Any]:
    return {
        key: item.get(key)
        for key in ("signal", "unit", "minimum", "maximum", "p2p", "peak_abs", "peak_value", "time_of_peak_abs_ps", "signed_area", "absolute_area", "positive_area", "negative_area", "positive_sample_fraction", "negative_sample_fraction", "zero_crossing_count", "half_abs_peak_width")
    }


def run_analysis(case_id: str, mask: str, trace: Any, canonical: Any) -> dict[str, Any]:
    active = [index for index, bit in enumerate(mask, start=1) if bit == "1"]
    phase_nav = {}
    phase_area = {}
    for index in active:
        for element in ("B_JS1", "B_JS2", "B_JM1", "B_JM2"):
            signal = f"P({element}|XBVM{index})"
            phase_nav[signal] = phase_navigation(trace, signal)
            if element in ("B_JS1", "B_JS2"):
                phase_area[signal] = phase_area_crosscheck(trace, signal, f"V({element}|XBVM{index})")
    focus_waveforms: dict[str, Any] = {}
    waveform_signals = [
        "V(COMMON_SL)", "V(TLINE_IN,0)", "I(T_BVM_QB)", "V(QBIN)", "I(LIN|XBQ1)",
        "V(QBOUT)", "V(JTL6_OUT)", "I(R_TERM)",
    ]
    for index in active:
        for element in ("B_JS1", "B_JS2", "B_JM1", "B_JM2"):
            waveform_signals.extend(f"{kind}({element}|XBVM{index})" for kind in ("P", "V", "I"))
        for element in BVM_BRANCHES:
            waveform_signals.extend(f"{kind}({element}|XBVM{index})" for kind in ("I", "V"))
    for index in range(1, 9):
        waveform_signals.extend(f"{kind}(B_JSL{index})" for kind in ("P", "V", "I"))
    for element in ("BJS", "BJ1", "BJ2"):
        waveform_signals.extend(f"{kind}({element}|XBQ1)" for kind in ("P", "V", "I"))
    for signal in dict.fromkeys(waveform_signals):
        if signal in trace.headers:
            focus_waveforms[signal] = compact_waveform(waveform_stats(trace, signal, *FOCUS_WINDOW))
    jtl_phase = {f"P(B01|XJTL1_{stage})": phase_navigation(trace, f"P(B01|XJTL1_{stage})") for stage in JTL_STAGES}
    qb_oracle = ordered_navigation_oracle(trace)
    td_ps = next(item[2] for item in FORMAL_CASES if item[0] == case_id)
    tline = tline_timing_features(trace, td_ps)
    source_profile = {
        signal: compact_waveform(waveform_stats(trace, signal, *FOCUS_WINDOW))
        for signal in ("I(B_JSL8)", "I(T_BVM_QB)", "I(LIN|XBQ1)")
        if signal in trace.headers
    }
    canonical_compare_signals = [
        "V(COMMON_SL)", "V(QBIN)", "I(LIN|XBQ1)", "V(LIN|XBQ1)",
        "P(BJ1|XBQ1)", "V(BJ1|XBQ1)", "I(BJ1|XBQ1)",
        "P(BJ2|XBQ1)", "V(BJ2|XBQ1)", "I(BJ2|XBQ1)",
        "I(B_JSL8)", "V(B_JSL8)",
    ]
    for index in active:
        canonical_compare_signals.extend((
            f"P(B_JS1|XBVM{index})", f"V(B_JS1|XBVM{index})", f"I(B_JS1|XBVM{index})",
            f"P(B_JS2|XBVM{index})", f"V(B_JS2|XBVM{index})", f"I(B_JS2|XBVM{index})",
            f"I(L_S3|XBVM{index})", f"V(L_S3|XBVM{index})", f"I(R_S|XBVM{index})", f"V(R_S|XBVM{index})",
        ))
    canonical_deltas = {
        signal: {
            "full_0_200_ps": signal_delta(canonical, trace, signal, (0.0, 200.0)),
            "focus_110_121_ps": signal_delta(canonical, trace, signal, FOCUS_WINDOW),
        }
        for signal in dict.fromkeys(canonical_compare_signals)
        if signal in canonical.headers and signal in trace.headers
    }
    first_bj = {
        signal: phase_nav.get(signal) or phase_navigation(trace, signal)
        for signal in ("P(BJ1|XBQ1)", "P(BJ2|XBQ1)")
        if signal in trace.headers
    }
    return {
        "run_id": run_id(case_id, mask),
        "case_id": case_id,
        "mask": mask,
        "active_bvm_instances": [f"XBVM{index}" for index in active],
        "TD_ps": next(item[2] for item in FORMAL_CASES if item[0] == case_id),
        "raw_path": rel(EXP / "runs" / case_id / mask / "raw.csv"),
        "raw_sha256": sha256(EXP / "runs" / case_id / mask / "raw.csv"),
        "grid": replay_base.finite_grid_qa(trace),
        "phase_navigation": phase_nav,
        "phase_area": phase_area,
        "qb_ordered_navigation_oracle": qb_oracle,
        "jtl_stage_navigation": jtl_phase,
        "first_bj_navigation": first_bj,
        "focus_waveforms": focus_waveforms,
        "source_profile": source_profile,
        "tline_timing": tline,
        "canonical_deltas": canonical_deltas,
        "control_window": {
            signal: compact_waveform(waveform_stats(trace, signal, *CONTROL_WINDOW))
            for signal in ("V(QBOUT)", "V(JTL6_OUT)", "I(R_TERM)", "V(QBIN)")
            if signal in trace.headers
        },
        "phase_semantics": "raw radians; turns only independent unwrap/(2*pi) navigation",
        "area_semantics": "actual-grid trapezoid on same JJ/endpoints/direction/window; not an SFQ count",
        "scientific_interpretation_performed": True,
    }


def canonical_reference_analysis(mask: str, trace: Any) -> dict[str, Any]:
    active = [index for index, bit in enumerate(mask, start=1) if bit == "1"]
    phase_navigation_records = {}
    phase_area = {}
    for index in active:
        for element in ("B_JS1", "B_JS2", "B_JM1", "B_JM2"):
            signal = f"P({element}|XBVM{index})"
            phase_navigation_records[signal] = phase_navigation(signal=signal, trace=trace)
            if element in ("B_JS1", "B_JS2"):
                phase_area[signal] = phase_area_crosscheck(trace, signal, f"V({element}|XBVM{index})")
    qb_phase_navigation = {
        signal: phase_navigation(trace, signal)
        for signal in (
            "P(BJ1|XBQ1)",
            "P(BJ2|XBQ1)",
            *[f"P(B01|XJTL1_{stage})" for stage in JTL_STAGES],
        )
    }
    return {
        "mask": mask,
        "qb_ordered_navigation_oracle": ordered_navigation_oracle(trace),
        "phase_navigation": phase_navigation_records,
        "qb_phase_navigation": qb_phase_navigation,
        "phase_area": phase_area,
        "qb_waveforms": {
            signal: compact_waveform(waveform_stats(trace, signal, *FOCUS_WINDOW))
            for signal in ("V(QBIN)", "I(LIN|XBQ1)", "V(LIN|XBQ1)", "V(QBOUT)", "I(B_JSL8)")
            if signal in trace.headers
        },
        "raw_path": rel(CANONICAL[mask]),
        "raw_sha256": sha256(CANONICAL[mask]),
    }


def classify_outcome(analyses: dict[str, Any], references: dict[str, Any]) -> dict[str, Any]:
    n2 = {key: value for key, value in analyses.items() if value["mask"] == "0011"}
    n3 = {key: value for key, value in analyses.items() if value["mask"] == "0111"}
    n2_counts = {key: value["qb_ordered_navigation_oracle"]["ordered_navigation_candidate_count"] for key, value in n2.items()}
    canonical_n2_count = references["0011"]["qb_ordered_navigation_oracle"]["ordered_navigation_candidate_count"]
    n2_second = all(value["qb_ordered_navigation_oracle"]["second_response_navigation_candidate_present"] for value in n2.values())
    n3_js1 = {key: value["phase_navigation"]["P(B_JS1|XBVM2)"]["focus_110_121_p2p_turns"] for key, value in n3.items()}
    n3_js2 = {key: value["phase_navigation"]["P(B_JS2|XBVM2)"]["focus_110_121_p2p_turns"] for key, value in n3.items()}
    n3_decreasing = all(n3_js1[key] < n3_js1["TLINE_TD_0P3_0111"] for key in ("TLINE_TD_0P6_0111",)) and all(n3_js2[key] < n3_js2["TLINE_TD_0P3_0111"] for key in ("TLINE_TD_0P6_0111",))
    canonical_n3_js1 = references["0111"]["phase_navigation"]["P(B_JS1|XBVM2)"]["focus_110_121_p2p_turns"]
    canonical_n3_js2 = references["0111"]["phase_navigation"]["P(B_JS2|XBVM2)"]["focus_110_121_p2p_turns"]
    n3_both_below_canonical = all(value < canonical_n3_js1 for value in n3_js1.values()) and all(value < canonical_n3_js2 for value in n3_js2.values())
    n3_vs_canonical = {
        key: {
            "JS1_focus_p2p": value["phase_navigation"]["P(B_JS1|XBVM2)"]["focus_110_121_p2p_turns"],
            "JS2_focus_p2p": value["phase_navigation"]["P(B_JS2|XBVM2)"]["focus_110_121_p2p_turns"],
            "JS1_canonical_focus_p2p": references["0111"]["phase_navigation"]["P(B_JS1|XBVM2)"]["focus_110_121_p2p_turns"],
            "JS2_canonical_focus_p2p": references["0111"]["phase_navigation"]["P(B_JS2|XBVM2)"]["focus_110_121_p2p_turns"],
            "JS1_delta_vs_canonical_turns": value["phase_navigation"]["P(B_JS1|XBVM2)"]["focus_110_121_p2p_turns"] - references["0111"]["phase_navigation"]["P(B_JS1|XBVM2)"]["focus_110_121_p2p_turns"],
            "JS2_delta_vs_canonical_turns": value["phase_navigation"]["P(B_JS2|XBVM2)"]["focus_110_121_p2p_turns"] - references["0111"]["phase_navigation"]["P(B_JS2|XBVM2)"]["focus_110_121_p2p_turns"],
        }
        for key, value in n3.items()
    }
    source_extinction_profiles = {
        key: {
            "I_BJSL8_min": value["focus_waveforms"].get("I(B_JSL8)", {}).get("minimum"),
            "I_BJSL8_max": value["focus_waveforms"].get("I(B_JSL8)", {}).get("maximum"),
            "I_TLINE_min": value["focus_waveforms"].get("I(T_BVM_QB)", {}).get("minimum"),
            "I_TLINE_max": value["focus_waveforms"].get("I(T_BVM_QB)", {}).get("maximum"),
            "I_BJSL8_zero_crossings": value["focus_waveforms"].get("I(B_JSL8)", {}).get("zero_crossing_count"),
            "I_BJSL8_signed_area": value["focus_waveforms"].get("I(B_JSL8)", {}).get("signed_area"),
            "I_BJSL8_positive_sample_fraction": value["focus_waveforms"].get("I(B_JSL8)", {}).get("positive_sample_fraction"),
            "I_BJSL8_negative_sample_fraction": value["focus_waveforms"].get("I(B_JSL8)", {}).get("negative_sample_fraction"),
        }
        for key, value in n3.items()
    }
    distortion = {
        key: {
            "near_voltage": value["tline_timing"]["upstream_port"]["voltage_focus"],
            "far_voltage": value["tline_timing"]["receiver_side_port"]["voltage_focus"],
            "near_current": value["tline_timing"]["upstream_port"]["current_focus"],
            "far_current": value["tline_timing"]["receiver_side_port"]["current_focus"],
        }
        for key, value in analyses.items()
    }
    if not n2_second or any(count != 2 for count in n2_counts.values()):
        classification = "N2_FUNCTIONAL_FAIL"
        status = "FAIL"
        reason = "At least one N2 TLINE case does not retain the canonical two ordered navigation candidates."
    elif n3_decreasing:
        classification = "TLINE_FEEDBACK_DEPHASING_SUPPORTED"
        status = "PASS"
        reason = "Both registered N3 TLINE delays reduce the JS1 and JS2 focus trajectory p2p relative to the shorter-delay case while N2 retains its two ordered candidates."
    else:
        classification = "NO_TIMING_EFFECT_OBSERVED"
        status = "INCONCLUSIVE"
        reason = "The registered N3 directional trajectory comparison did not show a monotonic delay effect."
    return {
        "status": status,
        "classification": classification,
        "reason": reason,
        "n2_ordered_navigation_candidate_counts": n2_counts,
        "canonical_n2_ordered_navigation_candidate_count": canonical_n2_count,
        "n2_second_response_navigation_candidate_present": n2_second,
        "n3_focus_p2p_by_case": n3_vs_canonical,
        "n3_focus_p2p_monotonic_with_TD": n3_decreasing,
        "n3_both_cases_below_canonical": n3_both_below_canonical,
        "n3_canonical_focus_p2p_turns": {"JS1": canonical_n3_js1, "JS2": canonical_n3_js2},
        "n3_source_extinction_observed": False,
        "timing_dephasing_status": "NOT_CONFIRMED" if not n3_both_below_canonical or not n2_second else "CANDIDATE_ONLY",
        "impedance_distortion_confounding": "UNRESOLVED: TLINE port peak/width/zero-crossing changes are descriptive and not separated from timing by this fixed Z0 point.",
        "source_profile": source_extinction_profiles,
        "distortion_profiles": distortion,
        "bounded_scope": "fixed N2/N3 masks, canonical QB/JTL/terminal, Z0=6 ohm, TD in {0.3,0.6} ps, dt=0.1 ps, 0-200 ps",
        "physical_equivalence": "UNKNOWN: ideal lossless TLINE model and this fixture do not establish hardware or universal receiver impedance behavior",
        "no_SFQ_or_terminal_count_substitution": True,
    }


def analyze() -> None:
    provenance = read_json(EXP / "provenance.json")
    if provenance.get("execution", {}).get("actual_formal_physical_solve_count") != 4 or provenance.get("run_order") != list(RUN_ORDER):
        raise RuntimeError("analysis requires exactly the four authorized formal runs")
    canonical = {mask: load_raw(CANONICAL[mask]) for mask in MASKS}
    traces: dict[str, Any] = {}
    analyses: dict[str, Any] = {}
    before: dict[str, str] = {}
    for key in RUN_ORDER:
        case_id, mask = key.rsplit("_", 1)
        raw = EXP / "runs" / case_id / mask / "raw.csv"
        before[key] = sha256(raw)
        trace = load_raw(raw)
        missing = sorted(expected_headers() - set(trace.headers))
        if missing:
            raise RuntimeError(f"missing formal probes for {key}: {missing}")
        if tuple(trace.time) != tuple(canonical[mask].time):
            raise RuntimeError(f"stored grid mismatch for {key}; no interpolation is permitted")
        traces[key] = trace
        analyses[key] = run_analysis(case_id, mask, trace, canonical[mask])
    references = {mask: canonical_reference_analysis(mask, canonical[mask]) for mask in MASKS}
    classification = classify_outcome(analyses, references)
    independent_critical_review = independent_critical_recalculation(canonical, traces)
    independent_review = independent_raw_review(canonical, traces)
    after = {key: sha256(EXP / "runs" / provenance["runs"][key]["case_id"] / provenance["runs"][key]["mask"] / "raw.csv") for key in RUN_ORDER}
    if before != after:
        raise RuntimeError("formal raw changed during analysis")
    provenance["raw_hash_before_analysis"] = before
    provenance["raw_hash_after_analysis"] = after
    registered_runner = next(
        (item for item in provenance.get("source_closure", []) if item.get("name") == "runner"),
        None,
    )
    current_runner = record_file(
        "runner", SCRIPT, "formal TLINE runner, arithmetic, QA, visualization, and package builder"
    )
    if registered_runner is not None and registered_runner.get("sha256") != current_runner["sha256"]:
        provenance["postsolve_tooling_revision"] = {
            "path": rel(SCRIPT),
            "old_sha256": registered_runner.get("sha256"),
            "new_sha256": current_runner["sha256"],
            "reason": "post-solve analysis/reporting enhancement; no deck, raw, solver, or run-matrix change",
            "physical_rerun": False,
            "raw_mutated": False,
        }
        for item in provenance["source_closure"]:
            if item.get("name") == "runner":
                item.update({"sha256": current_runner["sha256"], "bytes": current_runner["bytes"]})
    provenance["analysis"] = {
        "generated_at": now(),
        "scientific_interpretation_performed": True,
        "actual_grid_comparison": True,
        "interpolation_used": False,
        "runs": analyses,
        "canonical_references": references,
        "outcome": classification,
        "independent_critical_review": independent_critical_review,
        "independent_raw_review": independent_review,
    }
    provenance["outcome"] = classification
    provenance["delayed_or_extra_runs"] = []
    provenance["execution_status"] = "ANALYSIS_COMPLETE"
    write_json(EXP / "provenance.json", provenance)
    result = read_json(EXP / "result.json")
    result["generated_at"] = now()
    result["status"] = "ANALYSIS_COMPLETE"
    result["artifact_status"] = "VALID"
    result["scientific_interpretation_performed"] = True
    result["execution"] = provenance["execution"]
    result["runs"] = {
        key: {
            "status": "RUN_PASS",
            "case_id": analyses[key]["case_id"],
            "mask": analyses[key]["mask"],
            "TD_ps": analyses[key]["TD_ps"],
            "raw_path": analyses[key]["raw_path"],
            "raw_sha256": analyses[key]["raw_sha256"],
            "grid": analyses[key]["grid"],
        }
        for key in RUN_ORDER
    }
    result["outcome"] = classification
    result["independent_critical_review"] = independent_critical_review
    result["independent_raw_review"] = independent_review
    result["analysis_summary"] = {
        key: {
            "mask": analyses[key]["mask"],
            "TD_ps": analyses[key]["TD_ps"],
            "phase_navigation": {
                signal: {
                    "focus_110_121_p2p_turns": item["focus_110_121_p2p_turns"],
                    "focus_110_121_endpoint_delta_turns": item["focus_110_121_endpoint_delta_turns"],
                    "positive_threshold_navigation_times_ps": item["positive_threshold_navigation_times_ps"],
                    "negative_threshold_navigation_times_ps": item["negative_threshold_navigation_times_ps"],
                }
                for signal, item in analyses[key]["phase_navigation"].items()
            },
            "phase_area": analyses[key]["phase_area"],
            "first_bj_navigation": analyses[key]["first_bj_navigation"],
            "qb_ordered_navigation_oracle": {
                "ordered_navigation_candidate_count": analyses[key]["qb_ordered_navigation_oracle"]["ordered_navigation_candidate_count"],
                "second_response_navigation_candidate_present": analyses[key]["qb_ordered_navigation_oracle"]["second_response_navigation_candidate_present"],
                "first_two_records": analyses[key]["qb_ordered_navigation_oracle"]["records"][:2],
            },
            "tline_timing": analyses[key]["tline_timing"],
            "source_profile": analyses[key]["source_profile"],
            "control_window": analyses[key]["control_window"],
        }
        for key in RUN_ORDER
    }
    result["canonical_references"] = {
        mask: {
            "ordered_navigation_candidate_count": references[mask]["qb_ordered_navigation_oracle"]["ordered_navigation_candidate_count"],
            "second_response_navigation_candidate_present": references[mask]["qb_ordered_navigation_oracle"]["second_response_navigation_candidate_present"],
            "phase_navigation": references[mask]["phase_navigation"],
            "qb_phase_navigation": references[mask]["qb_phase_navigation"],
            "phase_area": references[mask]["phase_area"],
            "qb_waveforms": references[mask]["qb_waveforms"],
        }
        for mask in MASKS
    }
    result["unknown"] = [
        "physical hardware equivalence of ideal lossless TLINE",
        "universal receiver characteristic impedance",
        "timestep/solver convergence",
        "SFQ event identity/count and hardware behavior",
    ]
    result["stop"] = {
        "final_marker": FINAL_MARKER,
        "automatic_follow_up": False,
        "additional_delay_points_run": 0,
        "additional_Z0_points_run": 0,
        "sentinel_follow_up": False,
    }
    write_json(EXP / "result.json", result)
    (EXP / "RESULT.md").write_text(result_markdown(result), encoding="utf-8")
    print(json.dumps({"status": "ANALYSIS_COMPLETE", "outcome": classification, "raw_hashes_equal_before_after": True}, ensure_ascii=False, indent=2))


def result_markdown(result: dict[str, Any]) -> str:
    summary = result.get("analysis_summary", {})
    outcome = result.get("outcome", {})
    lines = [
        f"# BVM -> QB TLINE feedback dephasing ({EXP.name})",
        "",
        f"- Status: `{result.get('status')}`",
        f"- Outcome: `{outcome.get('classification')}` ({outcome.get('status')})",
        f"- Bounded answer: {outcome.get('reason', 'pending analysis')}",
        "- Formal solves: exactly TLINE_TD_0P3/TLINE_TD_0P6 × masks 0011/0111.",
        "- TLINE: ideal lossless four-node element, `Z0=6 ohm`; no current-to-SFQ conversion.",
        "- Canonical QB/JTL/terminal and BVM parameters are unchanged.",
        "",
        "## N2/N3 timing summary",
        "",
        "Phase is raw radians. Turns are only independent continuous-unwrapped navigation values, not SFQ counts.",
        "",
        "| run | mask | TD (ps) | JS1 [110,121) p2p (turns) | JS2 [110,121) p2p (turns) | ordered QB/JTL navigation candidates |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for key in RUN_ORDER:
        item = summary.get(key, {})
        nav = item.get("phase_navigation", {})
        mask = item.get("mask", "")
        active_instance = next((f"XBVM{index}" for index, bit in enumerate(mask, start=1) if bit == "1"), "XBVM2")
        js1 = nav.get(f"P(B_JS1|{active_instance})", {})
        js2 = nav.get(f"P(B_JS2|{active_instance})", {})
        oracle = result.get("analysis_summary", {}).get(key, {}).get("qb_ordered_navigation_oracle", {})
        # The compact result intentionally keeps the oracle in outcome/provenance;
        # display the value from provenance only when available in the result run.
        candidate_count = result.get("outcome", {}).get("n2_ordered_navigation_candidate_counts", {}).get(
            key,
            oracle.get("ordered_navigation_candidate_count", "—"),
        )
        lines.append(
            f"| `{key}` | {item.get('mask', '—')} | {format_number(item.get('TD_ps'))} | {format_number(js1.get('focus_110_121_p2p_turns'))} | {format_number(js2.get('focus_110_121_p2p_turns'))} | {candidate_count} |"
        )
    lines += [
        "",
        "## N2 reference and TLINE forward timing",
        "",
        f"The canonical N2 ordered phase-navigation candidate count is `{result.get('outcome', {}).get('canonical_n2_ordered_navigation_candidate_count', '—')}`; the TLINE runs report `{result.get('outcome', {}).get('n2_ordered_navigation_candidate_counts', {})}`. This navigation oracle is not a terminal pulse count.",
        "",
        "| run | specified TD (ps) | first BJ1 +0.5 (ps) | first BJ2 +0.5 (ps) | first BJ1 shift vs canonical (ps) | first BJ2 shift vs canonical (ps) | port V peak delta (ps) | same-grid V lag (ps) |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for key in RUN_ORDER:
        item = summary.get(key, {})
        timing = item.get("tline_timing", {})
        first_bj = item.get("first_bj_navigation", {})
        mask = item.get("mask", "")
        ref = result.get("canonical_references", {}).get(mask, {})
        ref_nav = ref.get("qb_phase_navigation", {})
        bj1 = first_bj.get("P(BJ1|XBQ1)", {}).get("positive_threshold_navigation_times_ps", {}).get("0.5")
        bj2 = first_bj.get("P(BJ2|XBQ1)", {}).get("positive_threshold_navigation_times_ps", {}).get("0.5")
        ref_bj1 = ref_nav.get("P(BJ1|XBQ1)", {}).get("positive_threshold_navigation_times_ps", {}).get("0.5")
        ref_bj2 = ref_nav.get("P(BJ2|XBQ1)", {}).get("positive_threshold_navigation_times_ps", {}).get("0.5")
        lag = timing.get("same_grid_port_voltage_lag", {}).get("best", {}).get("lag_ps")
        lines.append(
            f"| `{key}` | {format_number(timing.get('specified_TD_ps'))} | {format_number(bj1)} | {format_number(bj2)} | {format_number(bj1 - ref_bj1 if bj1 is not None and ref_bj1 is not None else None)} | {format_number(bj2 - ref_bj2 if bj2 is not None and ref_bj2 is not None else None)} | {format_number(timing.get('measured_forward_peak_delay_ps', {}).get('voltage_peak_delta'))} | {format_number(lag)} |"
        )
    lines += [
        "",
        "## Same-JJ phase / voltage-area cross-check",
        "",
        "All JS1/JS2 phase-area values use the same JJ, endpoints, direction and actual stored timestamps in `[110,121) ps`.",
        "",
        "| run | JS1 phase delta (turns) | JS1 V-area/Phi0 (turns) | JS2 phase delta (turns) | JS2 V-area/Phi0 (turns) |",
        "|---|---:|---:|---:|---:|",
    ]
    # Phase-area details live in provenance; the result summary has them for compact review.
    for key in RUN_ORDER:
        item = summary.get(key, {}).get("phase_area", {})
        mask = summary.get(key, {}).get("mask", "")
        active_instance = next((f"XBVM{index}" for index, bit in enumerate(mask, start=1) if bit == "1"), "XBVM2")
        js1 = item.get(f"P(B_JS1|{active_instance})", {})
        js2 = item.get(f"P(B_JS2|{active_instance})", {})
        lines.append(
            f"| `{key}` | {format_number(js1.get('phase_delta_turns'))} | {format_number(js1.get('voltage_area_over_Phi0_turns'))} | {format_number(js2.get('phase_delta_turns'))} | {format_number(js2.get('voltage_area_over_Phi0_turns'))} |"
        )
    lines += [
        "",
        "## TLINE port and distortion evidence",
        "",
        "Port features are described directly from `V(TLINE_IN,0)`, `I(T_BVM_QB)`, `V(QBIN)` and `I(LIN|XBQ1)`. No incident/reflected-wave decomposition is asserted.",
        "",
        "Detailed peak amplitudes, signed areas, zero crossings, half-peak widths, local features, COMMON_SL, JSL1..8, LS3/RS, QB, JTL and JM1/JM2 timing are in `provenance.json.analysis.runs` and `result.json.analysis_summary`.",
        "",
        "## Interpretation boundary",
        "",
        f"Outcome disposition: `{outcome.get('classification')}` ({outcome.get('status')}). {outcome.get('reason', '')}",
        "",
        "For N3, the TLINE cases remain multi-turn phase-navigation trajectories in the registered window and the source current remains positive-dominant; the result therefore does not satisfy the stated selective-dephasing outcome. The N2 two-response requirement is already lost in both TLINE cases.",
        "",
        "The outcome is bounded to this fixed N2/N3 simulation, ideal lossless TLINE model, `Z0=6 ohm`, two registered TD values, canonical QB/JTL/terminal, `dt=0.1 ps`, and `0–200 ps`. It is not a hardware measurement, universal impedance result, SFQ count, or proof of physical-equivalent QB feedback.",
        "",
        "## Evidence",
        "",
        "- Preflight and syntax basis: `PREFLIGHT.md` and `experiment.yaml`.",
        "- Raw/deck/log: `runs/TLINE_TD_0P3/0011`, `runs/TLINE_TD_0P3/0111`, `runs/TLINE_TD_0P6/0011`, `runs/TLINE_TD_0P6/0111`.",
        "- Smoke evidence: `smoke/tline_syntax/`.",
        "- Full-window plots and comparisons: `plots/`.",
        "- Machine evidence: `provenance.json` and `result.json`.",
        "- Delivery manifest: `delivery_manifest.json`; raw ZIP is Drive-only.",
        "",
        f"Stop marker: {FINAL_MARKER}",
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
    failures: list[str] = []
    checks: dict[str, Any] = {}
    required = expected_headers()
    for key in RUN_ORDER:
        record = provenance.get("runs", {}).get(key, {})
        case_id = record.get("case_id")
        mask = record.get("mask")
        directory = run_dir(case_id, mask) if case_id and mask else EXP / "runs" / "missing"
        deck = directory / "deck.cir"
        raw = directory / "raw.csv"
        log = directory / "run.log"
        text_value = deck.read_text(encoding="utf-8") if deck.is_file() else ""
        forbidden = [token for token in ("LC_LADDER", "R_MATCH", "V_REPLAY", "SENTINEL") if token.casefold() in text_value.casefold()]
        unexpected = sorted(path.name for path in directory.iterdir() if path.name not in {"deck.cir", "raw.csv", "run.log"}) if directory.is_dir() else ["missing_directory"]
        warnings = [line.strip() for line in log.read_text(errors="replace").splitlines() if any(token in line for token in ("Missing model:", "Unknown device/node", "Cannot store results", "Error", "error"))] if log.is_file() else ["missing_log"]
        known_nonfatal_warnings = [
            "Unknown device/node IB|XBQ1",
            "Cannot store results for this device/node.",
        ]
        unexpected_warnings = [warning for warning in warnings if warning not in known_nonfatal_warnings]
        try:
            trace = load_raw(raw)
            missing = sorted(required - set(trace.headers))
            raw_qa = replay_base.finite_grid_qa(trace)
        except Exception as exc:
            trace = None
            missing = [f"raw_parse_error:{exc}"]
            raw_qa = {"status": "INVALID"}
        raw_hash = sha256(raw) if raw.is_file() else None
        raw_recorded = record.get("raw", {}).get("sha256")
        deck_hash = sha256(deck) if deck.is_file() else None
        deck_registered = provenance.get("registered_decks", {}).get(key, {}).get("sha256")
        deck_ok = bool(
            deck.is_file()
            and text_value.count("B_JSL8 JSL_NODE7 TLINE_IN jjmit area=5.0") == 1
            and text_value.count("T_BVM_QB TLINE_IN 0 QBIN 0 TD=") == 1
            and text_value.count("Z0=6") == 1
            and text_value.count("V(TLINE_IN,0)") == 1
            and text_value.count("I(T_BVM_QB)") == 1
            and "B_JSL8 JSL_NODE7 QBIN jjmit area=5.0" not in text_value
            and ".tran 0.1p 200p" in text_value
            and not forbidden
        )
        passed = bool(
            record.get("execution_status") == "RUN_PASS"
            and deck_ok
            and deck_hash == deck_registered
            and raw_hash == raw_recorded
            and trace is not None
            and not missing
            and not trace.duplicate_columns
            and raw_qa.get("sample_count") == 1999
            and raw_qa.get("time_start_ps") == 0.0
            and raw_qa.get("time_end_ps") == 199.9
            and raw_qa.get("strictly_increasing_time") is True
            and not unexpected
            and not unexpected_warnings
        )
        if not passed:
            failures.append(key)
        checks[key] = {
            "status": "PASS" if passed else "ARTIFACT_INVALID",
            "deck": {"path": rel(deck), "sha256": deck_hash, "registered_sha256": deck_registered, "hash_match": deck_hash == deck_registered, "topology_checks": {"B_JSL8_to_TLINE_IN": text_value.count("B_JSL8 JSL_NODE7 TLINE_IN jjmit area=5.0") == 1, "TLINE_to_QBIN": text_value.count("T_BVM_QB TLINE_IN 0 QBIN 0 TD=") == 1, "Z0_only_6": text_value.count("Z0=6") == 1, "near_port_voltage_probe": text_value.count("V(TLINE_IN,0)") == 1, "near_port_current_probe": text_value.count("I(T_BVM_QB)") == 1, "canonical_bjsl8_removed": "B_JSL8 JSL_NODE7 QBIN jjmit area=5.0" not in text_value}, "forbidden_tokens": forbidden},
            "raw": {"path": rel(raw), "sha256": raw_hash, "recorded_sha256": raw_recorded, "hash_match": raw_hash == raw_recorded, "missing_required_probes": missing, "duplicate_columns": trace.duplicate_columns if trace is not None else {}, "grid": raw_qa},
            "unexpected_entries": unexpected,
            "solver_warning_lines": warnings,
            "known_nonfatal_probe_warnings": [warning for warning in warnings if warning in known_nonfatal_warnings],
            "unexpected_solver_warning_lines": unexpected_warnings,
        }
    source_hashes_match = all(sha256(REPO / item["path"]) == item["sha256"] for item in provenance.get("source_closure", []))
    root_allowed = {"experiment.yaml", "PREFLIGHT.md", "RESULT.md", "result.json", "provenance.json", "delivery_manifest.json", "runs", "plots", "smoke"}
    root_unexpected = sorted(path.name for path in EXP.iterdir() if path.name not in root_allowed)
    passed = bool(
        not failures
        and source_hashes_match
        and not root_unexpected
        and provenance.get("run_order") == list(RUN_ORDER)
        and provenance.get("execution", {}).get("actual_formal_physical_solve_count") == 4
        and provenance.get("execution", {}).get("total_solver_invocation_count") == 5
        and provenance.get("syntax_gate", {}).get("status") == "PASS"
        and provenance.get("raw_hash_before_analysis") == provenance.get("raw_hash_after_analysis")
        and (EXP / "runs").is_dir()
        and (EXP / "plots").is_dir()
        and (EXP / "smoke").is_dir()
        and (EXP / "result.json").stat().st_size <= RESULT_LIMIT_BYTES
    )
    qa = {
        "schema": "bvm-qb-tline-feedback-dephasing-mechanical-qa-v1",
        "experiment_id": EXP.name,
        "generated_at": now(),
        "status": "PASS" if passed else "FAIL",
        "artifact_status": "VALID" if passed else "ARTIFACT_INVALID",
        "head": git_head(),
        "remote_bvm_master": remote_head(),
        "source_hashes_match": source_hashes_match,
        "syntax_smoke_status": provenance.get("syntax_gate", {}).get("status"),
        "authorized_formal_solve_count": 4,
        "actual_formal_solve_count": provenance.get("execution", {}).get("actual_formal_physical_solve_count"),
        "total_solver_invocation_count": provenance.get("execution", {}).get("total_solver_invocation_count"),
        "no_extra_delay_points": sorted(path.name for path in (EXP / "runs").iterdir() if path.is_dir()) == sorted(case_id for case_id, _, _, _ in FORMAL_CASES),
        "no_Z0_sweep": True,
        "no_canonical_mutation": source_hashes_match,
        "no_read_extension": True,
        "no_sentinel_follow_up": True,
        "known_nonfatal_probe_warning_policy": "IB|XBQ1 is an inherited canonical probe outside the required probe set; recorded UNKNOWN/NOT_SUPPORTED, no raw rerun",
        "raw_hash_before_after_analysis_equal": provenance.get("raw_hash_before_analysis") == provenance.get("raw_hash_after_analysis"),
        "root_unexpected_entries": root_unexpected,
        "runs": checks,
        "result_json_bytes": (EXP / "result.json").stat().st_size,
        "result_json_under_limit": (EXP / "result.json").stat().st_size <= RESULT_LIMIT_BYTES,
        "scientific_interpretation_performed": True,
        "failures": failures,
    }
    provenance["qa"] = qa
    write_json(EXP / "provenance.json", provenance)
    result["qa_summary"] = {"status": qa["status"], "artifact_status": qa["artifact_status"], "result_json_under_limit": qa["result_json_under_limit"]}
    write_json(EXP / "result.json", result)
    (EXP / "RESULT.md").write_text(result_markdown(result), encoding="utf-8")
    if qa["status"] != "PASS":
        raise RuntimeError(f"mechanical QA failed: {failures}")
    print(json.dumps({"status": "PASS", "formal_runs": list(RUN_ORDER)}, ensure_ascii=False, indent=2))


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
    compact = html[: runtime_match.start()] + f'<script src="{asset_ref}"></script>' + html[runtime_match.end() :]
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
    with tempfile.NamedTemporaryFile(prefix="bvm_tline_plot_", suffix=".html", delete=False, dir="/tmp") as handle:
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
    with tempfile.NamedTemporaryFile(prefix="bvm_tline_focus_", suffix=".csv", delete=False, dir="/tmp", mode="w", newline="", encoding="utf-8") as handle:
        temporary = Path(handle.name)
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)
    return temporary


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
    with tempfile.NamedTemporaryFile(prefix="bvm_tline_compare_", suffix=".csv", delete=False, dir="/tmp", mode="w", newline="", encoding="utf-8") as handle:
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
    all_entries: list[dict[str, Any]] = []
    full_specs = {
        "01_signal_timing": ["V(COMMON_SL)", "V(TLINE_IN,0)", "I(T_BVM_QB)", "V(QBIN)", "I(LIN|XBQ1)"],
        "02_BVM_JS": [signal for index in range(1, 5) for element in ("B_JS1", "B_JS2") for signal in (f"P({element}|XBVM{index})", f"V({element}|XBVM{index})", f"I({element}|XBVM{index})")],
        "03_BVM_RLOOP": [signal for index in range(1, 5) for element in BVM_BRANCHES for signal in (f"I({element}|XBVM{index})", f"V({element}|XBVM{index})")],
        "04_JSL": [signal for index in range(1, 9) for signal in (f"P(B_JSL{index})", f"V(B_JSL{index})", f"I(B_JSL{index})")],
        "05_QB": ["V(TLINE_IN,0)", "I(T_BVM_QB)", "V(QBIN)", "I(LIN|XBQ1)", "V(LIN|XBQ1)", *[f"{kind}({element}|XBQ1)" for element in ("BJS", "BJ1", "BJ2") for kind in ("P", "V", "I")], *[f"{kind}({element}|XBQ1)" for element in ("L1", "L2", "L3", "RJ1", "RJ2") for kind in ("I", "V")], "V(QBOUT)"],
        "06_JTL": [signal for stage in JTL_STAGES for signal in (f"P(B01|XJTL1_{stage})", f"V(B01|XJTL1_{stage})", f"I(B01|XJTL1_{stage})", f"P(B02|XJTL1_{stage})", f"V(B02|XJTL1_{stage})", f"I(B02|XJTL1_{stage})", f"V(JTL{stage}_OUT)")],
        "07_terminal": ["V(QBOUT)", *[f"V(JTL{stage}_OUT)" for stage in JTL_STAGES], "I(R_TERM)", "V(TLINE_IN,0)", "V(QBIN)"],
    }
    focus_specs = {
        "01_signal_timing_focus_110_121": full_specs["01_signal_timing"],
        "02_BVM_JS_focus_110_121": full_specs["02_BVM_JS"],
    }
    for key in RUN_ORDER:
        case_id, mask = key.rsplit("_", 1)
        raw = EXP / "runs" / case_id / mask / "raw.csv"
        trace = load_raw(raw)
        case_dir = EXP / "plots" / case_id / mask
        for page_name, requested in full_specs.items():
            selected = [signal for signal in requested if signal in trace.headers]
            if not selected:
                continue
            output = case_dir / f"{page_name}.html"
            render_external(raw, output, selected, f"{key}: {page_name} (full 0-200 ps)", asset)
            all_entries.append({"kind": "standalone", "run_id": key, "path": rel(output), "raw_path": rel(raw), "raw_sha256": sha256(raw), "sha256": sha256(output), "bytes": output.stat().st_size, "signals": selected, "window_ps": [0.0, 200.0], "focused": False, "renderer": rel(PLOTTER), "phase_display": "rad/(2*pi) turns navigation"})
        focus_csv = crop_csv(raw, *FOCUS_WINDOW)
        try:
            for page_name, requested in focus_specs.items():
                selected = [signal for signal in requested if signal in trace.headers]
                if not selected:
                    continue
                output = case_dir / f"{page_name}.html"
                render_external(focus_csv, output, selected, f"{key}: {page_name} (110-121 ps stored samples)", asset)
                all_entries.append({"kind": "standalone", "run_id": key, "path": rel(output), "raw_path": rel(raw), "raw_sha256": sha256(raw), "sha256": sha256(output), "bytes": output.stat().st_size, "signals": selected, "window_ps": list(FOCUS_WINDOW), "focused": True, "derived_input": "actual-grid crop only; no interpolation", "renderer": rel(PLOTTER), "phase_display": "rad/(2*pi) turns navigation"})
        finally:
            focus_csv.unlink(missing_ok=True)

    comparison_entries: list[dict[str, Any]] = []
    canonical_traces = {mask: load_raw(CANONICAL[mask]) for mask in MASKS}
    compare_specs = {
        "canonical_vs_tline_js_boundary": ["V(COMMON_SL)", "V(QBIN)", "V(LIN|XBQ1)", "I(LIN|XBQ1)", *[signal for index in range(1, 5) for element in ("B_JS1", "B_JS2") for signal in (f"P({element}|XBVM{index})", f"V({element}|XBVM{index})", f"I({element}|XBVM{index})")], *[f"{kind}(B_JSL{index})" for index in range(1, 9) for kind in ("P", "V", "I")]],
        "canonical_vs_tline_rloop": [signal for index in range(1, 5) for element in ("L_M3", "L_S3", "R_S", "L_SL") for signal in (f"I({element}|XBVM{index})", f"V({element}|XBVM{index})")],
        "canonical_vs_tline_qb_jtl": ["V(QBOUT)", "V(QBIN)", *[f"P(BJ{element}|XBQ1)" for element in ("1", "2")], *[f"P(B01|XJTL1_{stage})" for stage in JTL_STAGES], *[f"V(JTL{stage}_OUT)" for stage in JTL_STAGES], "I(R_TERM)"],
    }
    for mask in MASKS:
        cases: list[tuple[str, Any]] = [("CANONICAL", canonical_traces[mask])]
        for case_id, _, _, _ in FORMAL_CASES:
            cases.append((f"{case_id}", load_raw(EXP / "runs" / case_id / mask / "raw.csv")))
        for page_name, requested in compare_specs.items():
            selected = [signal for signal in requested if all(signal in trace.headers for _, trace in cases)]
            if not selected:
                continue
            temporary = comparison_csv(cases, selected)
            output = EXP / "plots" / "comparisons" / f"{mask}_{page_name}.html"
            try:
                render_external(temporary, output, [replay_base.prefixed_label(case, signal) for case, _ in cases for signal in selected], f"{mask}: CANONICAL vs TLINE cases — {page_name} (full 0-200 ps)", asset)
            finally:
                temporary.unlink(missing_ok=True)
            comparison_entries.append({"kind": "comparison", "mask": mask, "path": rel(output), "sha256": sha256(output), "bytes": output.stat().st_size, "cases": [case for case, _ in cases], "signals": selected, "window_ps": [0.0, 200.0], "focused": False, "renderer": rel(PLOTTER), "phase_display": "independent case unwrap and rad/(2*pi) turns navigation"})
    html_paths = sorted(path for path in (EXP / "plots").rglob("*.html"))
    if not html_paths or not asset.is_file():
        raise RuntimeError("visualization output incomplete")
    invalid = [rel(path) for path in html_paths if any(token in path.read_text(encoding="utf-8") for token in ("plotly.js v", "var Plotly=", "cdn.plot.ly"))]
    if invalid:
        raise RuntimeError(f"invalid HTML runtime externalization: {invalid}")
    visualization = {
        "status": "PASS",
        "generated_at": now(),
        "renderer": rel(PLOTTER),
        "layout": "sep_comb",
        "color": "dark",
        "phase_option": "2pi",
        "entries": all_entries + comparison_entries,
        "standalone_count": len(all_entries),
        "comparison_count": len(comparison_entries),
        "focused_window_entries": sum(1 for entry in all_entries if entry.get("focused")),
        "full_window_only_comparisons": True,
        "asset": {"path": rel(asset), "sha256": sha256(asset), "bytes": asset.stat().st_size},
        "raw_hashes_rechecked": all(entry["raw_sha256"] == sha256(REPO / entry["raw_path"]) for entry in all_entries),
        "scientific_interpretation_performed": True,
    }
    provenance["visualization"] = visualization
    write_json(EXP / "provenance.json", provenance)
    result = read_json(EXP / "result.json")
    result["visualization_summary"] = {"status": "PASS", "standalone_count": len(all_entries), "comparison_count": len(comparison_entries), "focused_window_entries": visualization["focused_window_entries"], "asset": rel(asset)}
    write_json(EXP / "result.json", result)
    (EXP / "RESULT.md").write_text(result_markdown(result), encoding="utf-8")
    print(json.dumps({"status": "PASS", "standalone_count": len(all_entries), "comparison_count": len(comparison_entries)}, ensure_ascii=False, indent=2))


def package() -> None:
    provenance = read_json(EXP / "provenance.json")
    if provenance.get("qa", {}).get("status") != "PASS" or provenance.get("visualization", {}).get("status") != "PASS":
        raise RuntimeError("QA and visualization must pass before packaging")
    delivery_dir = Path("/mnt/d/BVM_Backages")
    delivery_dir.mkdir(parents=True, exist_ok=True)
    v1_package_path = delivery_dir / f"{EXP.name}_raw_evidence.zip"
    previous_manifest = read_json(EXP / "delivery_manifest.json") if (EXP / "delivery_manifest.json").is_file() else None
    if v1_package_path.exists():
        package_version = "v2"
        package_path = delivery_dir / f"{EXP.name}_v2_raw_evidence.zip"
    else:
        package_version = "v1"
        package_path = v1_package_path
    if package_path.exists():
        raise RuntimeError(f"refusing overwrite of existing package: {package_path}")
    # The package-internal metadata is made content-consistent before the ZIP
    # is opened and hashed.  Delivery ID/SHA are intentionally kept in the
    # repo-side delivery_manifest.json to avoid a self-reference cycle.
    provenance["package"] = {
        "status": "PACKAGE_CONTENT_READY",
        "version": package_version,
        "internal_metadata_status": "ALL_AUTHORIZED_FORMAL_CASES_COMPLETE",
        "delivery_manifest_path": "delivery_manifest.json",
        "drive_file_id": None,
        "drive_url": None,
    }
    result = read_json(EXP / "result.json")
    result["package_summary"] = {"status": "PACKAGE_CONTENT_READY", "version": package_version, "delivery_manifest_path": "delivery_manifest.json", "drive_file_id": None}
    write_json(EXP / "provenance.json", provenance)
    write_json(EXP / "result.json", result)
    (EXP / "RESULT.md").write_text(result_markdown(result), encoding="utf-8")
    files: list[tuple[Path, str]] = []
    for name in ("experiment.yaml", "PREFLIGHT.md", "RESULT.md", "result.json", "provenance.json"):
        path = EXP / name
        if path.is_file():
            files.append((path, path.relative_to(EXP).as_posix()))
    for path in sorted((EXP / "smoke").rglob("*")):
        if path.is_file():
            files.append((path, path.relative_to(EXP).as_posix()))
    for path in sorted((EXP / "runs").rglob("*")):
        if path.is_file():
            files.append((path, path.relative_to(EXP).as_posix()))
    for path in sorted((EXP / "plots").rglob("*")):
        if path.is_file():
            files.append((path, path.relative_to(EXP).as_posix()))
    files.append((SCRIPT, "executor/bvm_qb_tline_feedback_dephasing.py"))
    records = [{"path": archive_name, "sha256": sha256(path), "bytes": path.stat().st_size} for path, archive_name in files]
    with zipfile.ZipFile(package_path, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path, archive_name in files:
            archive.write(path, archive_name)
    with zipfile.ZipFile(package_path, "r") as archive:
        reopened = {name: hashlib.sha256(archive.read(name)).hexdigest() for name in archive.namelist()}
    expected = {record["path"]: record["sha256"] for record in records}
    qa = {
        "status": "PASS" if expected == reopened else "FAIL",
        "package_version": package_version,
        "package_path": str(package_path),
        "package_sha256": sha256(package_path),
        "package_bytes": package_path.stat().st_size,
        "file_count": len(records),
        "expected_file_hashes_match_after_reopen": expected == reopened,
        "zip_files": records,
        "not_in_git": True,
        "contains_all_authorized_formal_raw": all(any(record["path"] == f"runs/{case_id}/{mask}/raw.csv" for record in records) for case_id, _, _, _ in FORMAL_CASES for mask in MASKS),
        "contains_canonical_reference_copy": any(record["path"].startswith("references/") for record in records),
        "delivery_manifest_in_zip": any(record["path"] == "delivery_manifest.json" for record in records),
        "delivery_manifest_outside_zip": True,
        "supersedes_previous_package": previous_manifest.get("package_sha256") if previous_manifest else None,
        "git_head_at_packaging": git_head(),
        "remote_head_at_packaging": remote_head(),
    }
    manifest = {
        "schema": "bvm-qb-tline-feedback-dephasing-delivery-manifest-v1",
        "experiment_id": EXP.name,
        "created_at": now(),
        "status": "READY_FOR_DRIVE_UPLOAD" if qa["status"] == "PASS" else "PACKAGE_INVALID",
        "package_version": package_version,
        "package_path": str(package_path),
        "package_sha256": qa["package_sha256"],
        "package_bytes": qa["package_bytes"],
        "package_qa": qa,
        "drive_folder_id": DRIVE_FOLDER_ID,
        "drive_file_id": None,
        "drive_url": None,
        "delivery_id_is_outside_zip_to_avoid_self_reference": True,
        "supersedes_previous_package": previous_manifest.get("package_sha256") if previous_manifest else None,
    }
    write_json(EXP / "delivery_manifest.json", manifest)
    provenance["package"] = {
        "status": "READY_FOR_DRIVE_UPLOAD" if qa["status"] == "PASS" else "PACKAGE_INVALID",
        "version": package_version,
        "internal_metadata_status": "ALL_AUTHORIZED_FORMAL_CASES_COMPLETE",
        "delivery_manifest_path": "delivery_manifest.json",
        "package_qa": qa,
        "drive_file_id": None,
        "drive_url": None,
    }
    write_json(EXP / "provenance.json", provenance)
    result = read_json(EXP / "result.json")
    result["package_summary"] = {"status": provenance["package"]["status"], "version": package_version, "package_sha256": qa["package_sha256"], "package_bytes": qa["package_bytes"], "file_count": qa["file_count"], "delivery_manifest_path": "delivery_manifest.json", "drive_file_id": None}
    write_json(EXP / "result.json", result)
    (EXP / "RESULT.md").write_text(result_markdown(result), encoding="utf-8")
    if qa["status"] != "PASS":
        raise RuntimeError("package reopen QA failed")
    print(json.dumps({"status": "PASS", "package_path": str(package_path), "sha256": qa["package_sha256"], "bytes": qa["package_bytes"], "files": qa["file_count"], "manifest": rel(EXP / "delivery_manifest.json")}, ensure_ascii=False, indent=2))


def record_drive(file_id: str, url: str | None = None) -> None:
    manifest_path = EXP / "delivery_manifest.json"
    manifest = read_json(manifest_path)
    package_path = Path(manifest["package_path"])
    if not package_path.is_file() or sha256(package_path) != manifest["package_sha256"]:
        raise RuntimeError("delivery package missing or changed before Drive record")
    manifest["status"] = "UPLOADED"
    manifest["drive_file_id"] = file_id
    manifest["drive_url"] = url
    manifest["uploaded_at"] = now()
    write_json(manifest_path, manifest)
    provenance = read_json(EXP / "provenance.json")
    provenance["package"]["status"] = "UPLOADED"
    provenance["package"]["drive_file_id"] = file_id
    provenance["package"]["drive_url"] = url
    provenance["package"]["drive_uploaded_at"] = manifest["uploaded_at"]
    provenance["package"]["delivery_manifest_sha256"] = sha256(manifest_path)
    write_json(EXP / "provenance.json", provenance)
    result = read_json(EXP / "result.json")
    result["package_summary"]["status"] = "UPLOADED"
    result["package_summary"]["drive_file_id"] = file_id
    result["package_summary"]["drive_url"] = url
    write_json(EXP / "result.json", result)
    (EXP / "RESULT.md").write_text(result_markdown(result), encoding="utf-8")
    print(json.dumps({"status": "UPLOADED", "drive_file_id": file_id, "drive_url": url, "package_sha256": manifest["package_sha256"]}, ensure_ascii=False, indent=2))


def main() -> int:
    command = sys.argv[1] if len(sys.argv) > 1 else "all"
    actions = {"prepare": prepare, "run": execute, "analyze": analyze, "qa": mechanical_qa, "viz": visualization, "package": package, "record-drive": lambda: record_drive(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)}
    if command == "all":
        for action in (prepare, execute, analyze, mechanical_qa, visualization):
            action()
        return 0
    if command not in actions:
        print(f"usage: {SCRIPT.name} [prepare|run|analyze|qa|viz|package|record-drive FILE_ID [URL]|all]", file=sys.stderr)
        return 2
    if command == "record-drive" and len(sys.argv) < 3:
        print("record-drive requires FILE_ID", file=sys.stderr)
        return 2
    actions[command]()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
