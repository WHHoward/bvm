#!/usr/bin/env python3
"""BVM -> QB boundary timing replay, EXACT_N3-gated exploration.

The replay is deliberately an ideal voltage-forcing counterfactual.  It is
not a circuit-equivalent reconstruction of the canonical QB boundary and it
does not preserve the original source impedance or source/load back-action.

This runner registers all three requested cases but materializes and solves
EXACT_N3 only.  Delayed cases stay review-gated because the current execution
does not carry SCIENTIFIC_REVIEW_AUTHORIZED and no numerical fidelity gate was
frozen by the user.
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
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

SCRIPT = Path(__file__).resolve()
REPO = SCRIPT.parents[1]
EXP = REPO / "test" / "exploration" / "bvm-qb-boundary-timing-replay-v1-20260916"

SOLVER = REPO / "build" / "josim-cli"
PLOTTER = REPO / "scripts" / "josim-plot2.py"
MODEL = REPO / "circuits" / "models" / "jjmit.cir"
QB = REPO / "circuits" / "qb" / "bq_parameterized_v1.cir"
BVM = (
    REPO
    / "test"
    / "exploration"
    / "bvm-population-scaling-rj2p12-l1p14-l2p20-ib260-rj32-bjs400-v1-20260910"
    / "inputs"
    / "bvm_jm2_connected.cir"
)
PASSIVE_DECK = (
    REPO
    / "test"
    / "exploration"
    / "bvm-population-passive-source-replay-rj2p12-l1p14-l2p20-ib260-rj32-bjs400-v1-20260911"
    / "runs"
    / "PASSIVE_N3_0111"
    / "deck.cir"
)
CANONICAL_ROOT = (
    REPO
    / "test"
    / "exploration"
    / "bvm-qb-threshold-ordering-boundary-search-v1-20260911"
    / "references"
    / "canonical_baseline"
    / "0111"
)
CANONICAL_RAW = CANONICAL_ROOT / "raw.csv"
CANONICAL_DECK = CANONICAL_ROOT / "deck.cir"

EXPECTED_HEAD = "4bc14ebf04c0ccf1c415bcc37def65631f67cbee"
EXPECTED_HASHES = {
    MODEL: "19862d1fd1f1f44dfa1523848d7d3b5e2594a6c5da8fdd80144b449e5312a336",
    QB: "f676ba1ecb9b2607631a5cfc2f99b7d67e09b9e821457015fba375b8a39f13b0",
    BVM: "0093a45cc3910448b484d8bd004c6df8c22358bacc8b3ed5e23912dcab805d54",
    SOLVER: "48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2",
}
EXPECTED_CANONICAL_RAW_SHA256 = "1ca15a938b23d4ed08eb964713f91476256c4caf0677d1bfd3dc43020271ec75"

PHI0 = 2.067833848e-15
TAU = 2.0 * math.pi
WINDOWS_PS = ((0.0, 200.0), (101.0, 110.0), (110.0, 121.0), (121.0, 200.0))
FOCUS_WINDOW = (110.0, 121.0)
PHASE_NAVIGATION_THRESHOLDS = (-0.5, -1.5, -2.5, -3.5, -4.5, -5.5, -6.5, -7.5)
DIV_PHASE_THRESHOLD_TURNS = 0.10
DIV_CURRENT_THRESHOLD_A = 5.0e-6
DIV_VOLTAGE_THRESHOLD_V = 50.0e-6
RESULT_LIMIT_BYTES = 500 * 1024
CONTRACT_SENTENCE = "This experiment is governed by docs/EXPERIMENT_CONTRACT.md."
FINAL_MARKER = "EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW"

BVM_JUNCTIONS = ("B_JM1", "B_JM2", "B_JS1", "B_JS2")
BVM_BRANCHES = (
    "L_M1",
    "L_M2",
    "L_M3",
    "L_PM",
    "L_S1",
    "L_S2",
    "L_S3",
    "R_S",
    "L_PSL",
    "R_SL",
    "L_SL",
)
JSL_COUNT = 8


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
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
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
    return {
        "path": rel(SOLVER),
        "sha256": sha256(SOLVER),
        "version": subprocess.check_output(
            [str(SOLVER), "--version"], cwd=REPO, text=True
        ).strip(),
    }


def record_file(name: str, path: Path, role: str) -> dict[str, Any]:
    if not path.is_file():
        raise RuntimeError(f"missing source file: {path}")
    return {
        "name": name,
        "path": rel(path),
        "sha256": sha256(path),
        "bytes": path.stat().st_size,
        "role": role,
    }


def assert_registered_sources() -> None:
    if git_head() != EXPECTED_HEAD:
        raise RuntimeError(
            f"current HEAD is {git_head()}, expected {EXPECTED_HEAD}; stop before prepare"
        )
    if remote_head() != EXPECTED_HEAD:
        raise RuntimeError(
            f"bvm/master is {remote_head()}, expected {EXPECTED_HEAD}; stop before prepare"
        )
    for path, expected in EXPECTED_HASHES.items():
        if not path.is_file() or sha256(path) != expected:
            raise RuntimeError(f"registered source changed or is missing: {path}")
    if sha256(CANONICAL_RAW) != EXPECTED_CANONICAL_RAW_SHA256:
        raise RuntimeError(f"canonical replay authority changed: {CANONICAL_RAW}")


def import_tools() -> tuple[Any, Any]:
    sys.path.insert(0, str(REPO / "scripts"))
    from bvmtools.phase import continuous_unwrap
    from bvmtools.raw import read_csv

    return read_csv, continuous_unwrap


def load_raw(path: Path) -> Any:
    read_csv, _ = import_tools()
    trace = read_csv(path)
    if trace.duplicate_columns:
        raise RuntimeError(f"duplicate columns in raw CSV: {path}: {trace.duplicate_columns}")
    return trace


def time_indices(trace: Any, start_ps: float, end_ps: float) -> list[int]:
    return [
        index
        for index, value in enumerate(trace.time)
        if start_ps <= value * 1.0e12 < end_ps
    ]


def actual_integral(times: Iterable[float], values: Iterable[float]) -> float:
    time_list = list(times)
    value_list = list(values)
    return sum(
        0.5 * (value_list[index] + value_list[index + 1])
        * (time_list[index + 1] - time_list[index])
        for index in range(len(value_list) - 1)
    )


def finite_grid_qa(trace: Any) -> dict[str, Any]:
    deltas = [
        (right - left) * 1.0e12
        for left, right in zip(trace.time, trace.time[1:])
    ]
    distinct_dt: dict[str, int] = {}
    for delta in deltas:
        key = f"{delta:.12g}"
        distinct_dt[key] = distinct_dt.get(key, 0) + 1
    return {
        "status": "VALID",
        "sample_count": trace.sample_count,
        "header_count": len(trace.headers),
        "time_start_ps": trace.time[0] * 1.0e12,
        "time_end_ps": trace.time[-1] * 1.0e12,
        "strictly_increasing_time": all(
            right > left for left, right in zip(trace.time, trace.time[1:])
        ),
        "finite_values": True,
        "dt_ps_min": min(deltas),
        "dt_ps_max": max(deltas),
        "dt_ps_counts": distinct_dt,
        "duplicate_columns": trace.duplicate_columns,
    }


def read_source_tokens(path: Path) -> tuple[list[str], list[str]]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.reader(stream)
        header = next(reader)
        if header.count("time") != 1 or header.count("V(QBIN)") != 1:
            raise RuntimeError("replay authority must contain unique time and V(QBIN) columns")
        time_index = header.index("time")
        voltage_index = header.index("V(QBIN)")
        times: list[str] = []
        voltages: list[str] = []
        for row in reader:
            if not row or not any(cell.strip() for cell in row):
                continue
            times.append(row[time_index].strip())
            voltages.append(row[voltage_index].strip())
    if len(times) != len(voltages) or len(times) < 2:
        raise RuntimeError("invalid replay authority token lengths")
    return times, voltages


def time_token_ps(token: str) -> str:
    time_ps = float(token) * 1.0e12
    if abs(time_ps) < 1.0e-30:
        return "0"
    return f"{time_ps:.17g}p"


def exact_pwl_payload(time_tokens: list[str], voltage_tokens: list[str]) -> str:
    pairs: list[str] = []
    for time_token, voltage_token in zip(time_tokens, voltage_tokens):
        pairs.extend((time_token_ps(time_token), voltage_token))
    return "PWL(" + " ".join(pairs) + ")"


def stimulus_lines() -> list[str]:
    lines = [
        line.strip()
        for line in PASSIVE_DECK.read_text(encoding="utf-8").splitlines()
        if re.match(r"^I_(?:WL|BL|SE)[1-4][ \t]", line.strip())
    ]
    if len(lines) != 12:
        raise RuntimeError(f"expected 12 passive stimulus lines, found {len(lines)}")
    return lines


def include_path(path: Path, deck_dir: Path) -> str:
    return Path(os.path.relpath(path, deck_dir)).as_posix()


def probe_lines() -> list[str]:
    lines: list[str] = []
    for index in range(1, 5):
        lines.append(f".print I(I_WL{index}) I(I_BL{index}) I(I_SE{index})")
        for element in BVM_JUNCTIONS:
            lines.append(
                f".print P({element}|XBVM{index}) V({element}|XBVM{index}) I({element}|XBVM{index})"
            )
        for element in BVM_BRANCHES:
            lines.append(f".print I({element}|XBVM{index}) V({element}|XBVM{index})")
    lines.append(".print V(COMMON_SL)")
    for index in range(1, JSL_COUNT + 1):
        lines.append(f".print P(B_JSL{index}) V(B_JSL{index}) I(B_JSL{index})")
    lines.extend((".print V(QBIN)", ".print I(V_REPLAY)"))
    return lines


def expected_headers() -> set[str]:
    required: set[str] = set()
    for index in range(1, 5):
        required.update(f"I(I_{kind}{index})" for kind in ("WL", "BL", "SE"))
        for element in BVM_JUNCTIONS:
            required.update(
                f"{kind}({element}|XBVM{index})" for kind in ("P", "V", "I")
            )
        for element in BVM_BRANCHES:
            required.update(f"{kind}({element}|XBVM{index})" for kind in ("I", "V"))
    required.add("V(COMMON_SL)")
    for index in range(1, JSL_COUNT + 1):
        required.update(
            f"{kind}(B_JSL{index})" for kind in ("P", "V", "I")
        )
    required.update(("V(QBIN)", "I(V_REPLAY)"))
    return required


def deck_text(deck_dir: Path, replay_payload: str) -> str:
    lines = [
        "* BVM -> QB boundary timing replay; only EXACT_N3 is materialized in this execution.",
        "* Causal replay / ideal voltage forcing; not a circuit-equivalent reconstruction.",
        "* P(...) is raw phase in radians; rad/(2*pi) is navigation only.",
        f".include {include_path(MODEL, deck_dir)}",
        f".include {include_path(BVM, deck_dir)}",
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
        f"V_REPLAY QBIN 0 {replay_payload}",
        "",
        *stimulus_lines(),
        "",
        ".tran 0.1p 200p",
        "",
        *probe_lines(),
        ".end",
        "",
    ]
    return "\n".join(lines)


def registered_yaml(
    registration_head: str,
    remote: str | None,
    source_records: list[dict[str, Any]],
    deck_record: dict[str, Any],
    replay_record: dict[str, Any],
) -> str:
    source_lines = "\n".join(
        f"  - {item['name']}: {item['path']}; sha256={item['sha256']}"
        for item in source_records
    )
    return textwrap.dedent(
        f"""
        schema_version: bvm-qb-boundary-timing-replay-v1
        id: {EXP.name}
        study_phase: EXPLORATORY
        role: Experimental Operator + Evidence Packager
        status: REGISTERED_EXACT_ONLY
        contract_sentence: {CONTRACT_SENTENCE}
        registration_head: {registration_head}
        remote_bvm_master_at_registration: {remote}
        scientific_review_authorized: false
        scientific_interpretation_performed: false

        question:
          primary: "Does N3 runaway timing depend on QB receiver-boundary feedback alignment with a BVM R-loop re-trigger state?"
          scope: "Causal replay only; not a physical-equivalent source/load replacement."
          interpretation_ceiling: "Execution, raw fidelity, registered arithmetic, and descriptive visual evidence only. Mechanism labels remain unassigned."

        source_fixture:
          source_history: "2026-09-11 passive N3 PASSIVE_N3_0111 BVM + COMMON_SL + 8xJSL topology"
          bvm_source: {rel(BVM)}
          bvm_source_role: "immutable BVM source; not modified"
          jsl8_change: "B_JSL8 JSL_NODE7 0 ... -> B_JSL8 JSL_NODE7 QBIN jjmit area=5.0"
          removed: "QB, JTL1..6, terminal"
          added: "V_REPLAY QBIN 0 PWL(...)"
          amplitude_change: false
          LS3_change: false
          RS_change: false
          canonical_bvm_or_qb_modified: false

        replay_authority:
          raw_path: {rel(CANONICAL_RAW)}
          raw_sha256: {sha256(CANONICAL_RAW)}
          allowed_column: "V(QBIN) only"
          stored_grid: "exact stored canonical timestamps; no interpolation, resampling, or time shift"
          sample_count: {replay_record['point_count']}
          time_start_ps: 0.0
          time_end_ps: 199.9
          source_token_sha256: {replay_record['source_token_sha256']}

        cases:
          - case_id: EXACT_N3
            status: MATERIALIZED_AND_AUTHORIZED
            rule: "0 <= t <= 200 ps: canonical V(QBIN,t) at each stored sample"
            delay_ps: 0.0
            stored_sample_shift: 0
          - case_id: DELAY_0P6
            status: REGISTERED_REVIEW_GATED_NOT_RUN
            rule: "t < 110 ps same; 110 <= t < 110.6 ps hold V(QBIN,110 ps); t >= 110.6 ps use canonical V(QBIN,t-0.6 ps)"
            delay_ps: 0.6
            stored_sample_shift: 6
            interpolation: false
          - case_id: DELAY_1P2
            status: REGISTERED_REVIEW_GATED_NOT_RUN
            rule: "t < 110 ps same; 110 <= t < 111.2 ps hold V(QBIN,110 ps); t >= 111.2 ps use canonical V(QBIN,t-1.2 ps)"
            delay_ps: 1.2
            stored_sample_shift: 12
            interpolation: false

        frozen:
          mask: "0111"
          active_bvm_instances: [XBVM2, XBVM3, XBVM4]
          bit_order: "b3b2b1b0 = BVM1/BVM2/BVM3/BVM4"
          BVM_count: 4
          JSL_count: 8
          JSL_area: 5.0
          stimulus: "passive N3 0111 source history; 100uA, 1ps edges, fixed 0-200ps history"
          tran: ".tran 0.1p 200p"
          analysis_windows_ps: [[0, 200], [101, 110], [110, 121], [121, 200]]
          window_semantics: "half-open; actual stored timestamps"
          fidelity_focus_window_ps: [110, 121]

        registered_deck:
          path: {deck_record['path']}
          sha256: {deck_record['sha256']}
          bytes: {deck_record['bytes']}
          expected_raw: runs/EXACT_N3/raw.csv

        source_closure:
        {source_lines}

        probes:
          fidelity: "P/V/I JS1, JS2, all active BVM; I/V LS1, LS2, LS3, RS, LM3, LSL; JM1/JM2; V(COMMON_SL); P/V/I JSL1..8; V(QBIN); I(V_REPLAY)."
          direction: "B_JSL8 is JSL_NODE7 -> QBIN; R_S and L_S3 use canonical local BVM branch orientation 6 -> 10."
          raw_phase: "P(JJ) is radians; continuous unwrap(rad)/(2*pi) is navigation only."
          voltage_area: "same JJ, same endpoints, same direction, actual stored grid, Phi0={PHI0}; not an SFQ count"

        registered_arithmetic:
          phase_navigation_thresholds_turns: {list(PHASE_NAVIGATION_THRESHOLDS)}
          divergence_thresholds: {{phase_turns: {DIV_PHASE_THRESHOLD_TURNS}, current_A: {DIV_CURRENT_THRESHOLD_A}, voltage_V: {DIV_VOLTAGE_THRESHOLD_V}}}
          cross_check: "JS1 and JS2 phase delta versus same-JJ voltage-time area in [110,121) ps"
          scientific_gate: "No numerical fidelity tolerance was supplied; do not automatically approve delayed cases."

        output_layout:
          root_files_only: [experiment.yaml, RESULT.md, result.json, provenance.json, runs, plots]
          forbidden_dirs: [screening, references, handoff, qa, analysis, inputs, data]
          run_files_only: [deck.cir, raw.csv, run.log]
          raw_zip: "Drive only; no ZIP in repository"
          no_png_svg: true

        stop:
          delayed_cases_without_scientific_review: false
          sentinel_follow_up: false
          read_extension: false
          final_state: {FINAL_MARKER}
        """
    ).lstrip()


def initial_result() -> dict[str, Any]:
    return {
        "schema": "bvm-qb-boundary-timing-replay-result-v1",
        "experiment_id": EXP.name,
        "generated_at": now(),
        "status": "PREFLIGHT_PASS_EXACT_ONLY",
        "artifact_status": "PENDING",
        "scientific_interpretation_performed": False,
        "execution": {
            "authorized_physical_solve_count": 1,
            "actual_physical_solve_count": 0,
            "authorized_run_order": ["EXACT_N3"],
            "registered_but_not_run": ["DELAY_0P6", "DELAY_1P2"],
        },
        "cases": {
            "EXACT_N3": {"status": "AUTHORIZED_NOT_RUN"},
            "DELAY_0P6": {"status": "REVIEW_GATED_NOT_RUN"},
            "DELAY_1P2": {"status": "REVIEW_GATED_NOT_RUN"},
        },
        "fidelity": {"status": "PENDING"},
        "review_questions": [
            "canonical / EXACT extra JS1 timing near 114.8 ps",
            "+0.6 ps and +1.2 ps movement or disappearance of extra JS1",
            "extra JS2 correspondence",
            "JS1 / JS2 read p2p trajectory comparison",
            "JSL/source current regeneration after first handoff",
            "JM1/JM2 later-follower ordering",
        ],
        "unknown": [
            "whether replay fidelity is scientifically sufficient",
            "mechanism or root cause",
            "physical equivalence of ideal voltage replay",
            "SFQ event identity or count",
            "timestep/solver convergence",
            "delayed-case outcome",
        ],
        "stop": {
            "final_marker": None,
            "automatic_follow_up": False,
        },
    }


def prepare() -> None:
    assert_registered_sources()
    if EXP.exists() and any(EXP.iterdir()):
        raise RuntimeError(f"experiment directory is not empty: {EXP}")
    EXP.mkdir(parents=True, exist_ok=True)
    run_dir = EXP / "runs" / "EXACT_N3"
    run_dir.mkdir(parents=True, exist_ok=True)
    (EXP / "plots").mkdir(parents=True, exist_ok=True)

    source_times, source_voltages = read_source_tokens(CANONICAL_RAW)
    canonical = load_raw(CANONICAL_RAW)
    if canonical.sample_count != 1999:
        raise RuntimeError(f"unexpected canonical sample count: {canonical.sample_count}")
    if canonical.time[0] != 0.0 or canonical.time[-1] != 1.999e-10:
        raise RuntimeError("unexpected canonical time range")
    replay_payload = exact_pwl_payload(source_times, source_voltages)
    deck = run_dir / "deck.cir"
    deck.write_text(deck_text(run_dir, replay_payload), encoding="utf-8")

    replay_record = {
        "authority_raw_path": rel(CANONICAL_RAW),
        "authority_raw_sha256": sha256(CANONICAL_RAW),
        "allowed_column": "V(QBIN)",
        "point_count": len(source_times),
        "source_token_sha256": sha256_text("\n".join(f"{t},{v}" for t, v in zip(source_times, source_voltages))),
        "pwl_payload_sha256": sha256_text(replay_payload),
        "pwl_payload_bytes": len(replay_payload.encode("utf-8")),
        "interpolation": False,
        "resampling": False,
        "time_shift": False,
    }
    deck_record = {
        "path": rel(deck),
        "sha256": sha256(deck),
        "bytes": deck.stat().st_size,
    }
    source_records = [
        record_file("runner", SCRIPT, "registered replay runner and mechanical arithmetic"),
        record_file("global_jjmit_model", MODEL, "global model closure"),
        record_file("canonical_qb", QB, "canonical QB hash guard only; QB is removed from replay deck"),
        record_file("canonical_bvm", BVM, "immutable BVM source closure"),
        record_file("passive_n3_fixture_deck", PASSIVE_DECK, "9/11 topology/stimulus fixture source"),
        record_file("canonical_n3_deck", CANONICAL_DECK, "9/10 closed N3 reference deck; raw replay authority remains V(QBIN) only"),
        record_file("josim_solver", SOLVER, "recorded physical solver"),
        record_file("plotter", PLOTTER, "standard JoSIM descriptive renderer"),
        record_file("shared_raw_reader", REPO / "scripts" / "bvmtools" / "raw.py", "duplicate-aware actual-grid reader"),
        record_file("shared_phase_tools", REPO / "scripts" / "bvmtools" / "phase.py", "continuous phase unwrap"),
        record_file("shared_waveform_tools", REPO / "scripts" / "bvmtools" / "waveform.py", "actual-grid arithmetic reference"),
    ]
    exp_yaml = registered_yaml(
        EXPECTED_HEAD, remote_head(), source_records, deck_record, replay_record
    )
    (EXP / "experiment.yaml").write_text(exp_yaml, encoding="utf-8")
    write_json(EXP / "result.json", initial_result())

    provenance = {
        "schema": "bvm-qb-boundary-timing-replay-provenance-v1",
        "experiment_id": EXP.name,
        "created_at": now(),
        "registration_head": EXPECTED_HEAD,
        "remote_bvm_master_at_registration": remote_head(),
        "contract_sentence": CONTRACT_SENTENCE,
        "scientific_review_authorized": False,
        "scientific_interpretation_performed": False,
        "runner": record_file("runner", SCRIPT, "registered runner"),
        "solver": solver_context(),
        "sources": source_records,
        "source_fixture": {
            "passive_fixture_deck": record_file("passive_fixture_deck", PASSIVE_DECK, "fixture topology and stimulus"),
            "canonical_bvm": record_file("canonical_bvm", BVM, "immutable included BVM"),
            "canonical_qb_hash_guard": record_file("canonical_qb", QB, "hash guard; not included in replay deck"),
            "qb_loaded": False,
            "jtl_loaded": False,
            "terminal_loaded": False,
        },
        "replay_authority": {
            "raw": record_file("canonical_n3_raw", CANONICAL_RAW, "read-only V(QBIN) replay authority"),
            "deck": record_file("canonical_n3_deck", CANONICAL_DECK, "read-only context; not replay source"),
            "allowed_column": "V(QBIN)",
            "other_columns_used_for_forcing": [],
            "actual_grid": finite_grid_qa(canonical),
            "pwl": replay_record,
        },
        "registered_cases": {
            "EXACT_N3": {
                "status": "AUTHORIZED_NOT_RUN",
                "delay_ps": 0.0,
                "stored_sample_shift": 0,
                "rule": "identity V(QBIN) replay at exact stored source samples",
            },
            "DELAY_0P6": {
                "status": "REVIEW_GATED_NOT_RUN",
                "delay_ps": 0.6,
                "stored_sample_shift": 6,
                "hold_interval_ps": [110.0, 110.6],
                "rule": "index-shifted canonical samples; no interpolation",
            },
            "DELAY_1P2": {
                "status": "REVIEW_GATED_NOT_RUN",
                "delay_ps": 1.2,
                "stored_sample_shift": 12,
                "hold_interval_ps": [110.0, 111.2],
                "rule": "index-shifted canonical samples; no interpolation",
            },
        },
        "registered_decks": {"EXACT_N3": deck_record},
        "run_order": [],
        "runs": {},
        "analysis_windows_ps": [list(window) for window in WINDOWS_PS],
        "focus_window_ps": list(FOCUS_WINDOW),
        "transformations": [
            {
                "name": "exact_voltage_replay",
                "input": f"{rel(CANONICAL_RAW)}:V(QBIN)",
                "output": "V_REPLAY PWL in runs/EXACT_N3/deck.cir",
                "operation": "identity values on source stored time grid",
                "interpolation": False,
                "resampling": False,
                "time_shift": False,
                "source_point_count": len(source_times),
                "payload_sha256": replay_record["pwl_payload_sha256"],
            },
            {
                "name": "phase_navigation_display",
                "input": "P(JJ) raw radians",
                "output": "continuous_unwrap(rad)/(2*pi) turns",
                "scientific_semantics": "navigation only; not SFQ count or fluxoid count",
            },
            {
                "name": "voltage_area_crosscheck",
                "input": "same JJ P/V, same endpoints/direction, [110,121) ps",
                "operation": "actual-grid trapezoid integral / Phi0",
                "scientific_semantics": "cross-check only; not an SFQ count",
            },
        ],
        "preflight": {
            "status": "PASS",
            "head_verified": EXPECTED_HEAD,
            "remote_verified": remote_head(),
            "canonical_source_hashes_verified": True,
            "canonical_source_mutation": False,
            "parameter_sweep": False,
            "sentinel_follow_up": False,
            "read_extension": False,
            "delayed_cases_materialized": False,
        },
        "qa": {"status": "PENDING"},
        "visualization": {"status": "PENDING"},
        "package": {"status": "PENDING", "drive_file_id": None, "drive_url": None},
        "stop": {"final_marker": None, "automatic_follow_up": False},
    }
    write_json(EXP / "provenance.json", provenance)
    (EXP / "RESULT.md").write_text(
        "# BVM -> QB boundary timing replay\n\n"
        "Preflight registered. Only EXACT_N3 is authorized for the first solve; delayed cases remain review-gated.\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": "PREFLIGHT_PASS",
        "experiment": rel(EXP),
        "head": EXPECTED_HEAD,
        "exact_deck": rel(deck),
        "pwl_point_count": len(source_times),
        "pwl_payload_sha256": replay_record["pwl_payload_sha256"],
    }, ensure_ascii=False, indent=2))


def execute() -> None:
    provenance = read_json(EXP / "provenance.json")
    if provenance.get("preflight", {}).get("status") != "PASS":
        raise RuntimeError("execution requires PASS preflight")
    if git_head() != provenance["registration_head"]:
        raise RuntimeError("HEAD changed after registration; do not execute")
    for item in provenance["sources"]:
        path = REPO / item["path"]
        if sha256(path) != item["sha256"]:
            raise RuntimeError(f"registered source changed after preflight: {path}")
    if provenance.get("run_order"):
        raise RuntimeError("EXACT_N3 execution has already been recorded; refusing overwrite/retry")

    run_dir = EXP / "runs" / "EXACT_N3"
    deck = run_dir / "deck.cir"
    raw = run_dir / "raw.csv"
    log = run_dir / "run.log"
    if raw.exists() or log.exists():
        raise RuntimeError("refusing overwrite/retry of existing EXACT_N3 artifacts")
    registered_deck = provenance["registered_decks"]["EXACT_N3"]
    if sha256(deck) != registered_deck["sha256"]:
        raise RuntimeError("registered EXACT_N3 deck changed before solve")

    command = [str(SOLVER), "-a", "1", "-o", str(raw), str(deck)]
    started = now()
    with log.open("x", encoding="utf-8") as stream:
        stream.write(
            f"experiment={EXP.name}\nrun_id=EXACT_N3\nstarted_at={started}\n"
            f"command={' '.join(command)}\n"
        )
        stream.flush()
        completed = subprocess.run(
            command,
            cwd=REPO,
            stdout=stream,
            stderr=subprocess.STDOUT,
            check=False,
        )
        finished = now()
        stream.write(f"finished_at={finished}\nexit_code={completed.returncode}\n")

    record: dict[str, Any] = {
        "run_id": "EXACT_N3",
        "case_id": "EXACT_N3",
        "deck": {"path": rel(deck), "sha256": sha256(deck), "bytes": deck.stat().st_size},
        "log": {"path": rel(log), "sha256": sha256(log), "bytes": log.stat().st_size},
        "command": command,
        "solver": solver_context(),
        "started_at": started,
        "finished_at": finished,
        "raw_immutable": True,
        "scientific_interpretation_performed": False,
        "physical_solve_this_experiment": True,
    }
    if completed.returncode != 0 or not raw.is_file() or raw.stat().st_size == 0:
        record["execution_status"] = "SOLVER_FAIL"
        record["raw"] = {
            "path": rel(raw),
            "exists": raw.is_file(),
            "sha256": sha256(raw) if raw.is_file() else None,
            "bytes": raw.stat().st_size if raw.is_file() else None,
        }
        provenance["runs"]["EXACT_N3"] = record
        provenance["run_order"] = ["EXACT_N3"]
        provenance["execution_status"] = "SOLVER_FAILURE_STOP"
        provenance["actual_physical_solve_count"] = 1
        write_json(EXP / "provenance.json", provenance)
        result = read_json(EXP / "result.json")
        result["status"] = "ARTIFACT_INVALID"
        result["artifact_status"] = "INVALID"
        result["execution"]["actual_physical_solve_count"] = 1
        result["cases"]["EXACT_N3"] = {"status": "SOLVER_FAIL"}
        write_json(EXP / "result.json", result)
        raise RuntimeError("EXACT_N3 solver failed; failure preserved and no retry authorized")

    try:
        trace = load_raw(raw)
        missing = sorted(expected_headers() - set(trace.headers))
        record["raw"] = {
            "path": rel(raw),
            "sha256": sha256(raw),
            "bytes": raw.stat().st_size,
            "sample_count": trace.sample_count,
            "time_start_ps": trace.time[0] * 1.0e12,
            "time_end_ps": trace.time[-1] * 1.0e12,
            "grid": finite_grid_qa(trace),
        }
        record["missing_required_probes"] = missing
        record["execution_status"] = "RUN_PASS" if not missing else "RUN_PASS_MISSING_PROBES"
    except Exception as exc:
        record["execution_status"] = "RAW_PARSE_FAILURE"
        record["raw_parse_error"] = str(exc)
        record["raw"] = {
            "path": rel(raw),
            "sha256": sha256(raw),
            "bytes": raw.stat().st_size,
        }
        provenance["runs"]["EXACT_N3"] = record
        provenance["run_order"] = ["EXACT_N3"]
        provenance["execution_status"] = "RAW_FAILURE_STOP"
        provenance["actual_physical_solve_count"] = 1
        write_json(EXP / "provenance.json", provenance)
        raise RuntimeError("EXACT_N3 raw parsing failed; failure preserved") from exc

    provenance["runs"]["EXACT_N3"] = record
    provenance["run_order"] = ["EXACT_N3"]
    provenance["actual_physical_solve_count"] = 1
    provenance["execution_status"] = "RUN_COMPLETE" if not missing else "RAW_PROBE_FAILURE_STOP"
    write_json(EXP / "provenance.json", provenance)
    result = read_json(EXP / "result.json")
    result["status"] = "EXACT_N3_RUN_COMPLETE" if not missing else "ARTIFACT_INVALID"
    result["artifact_status"] = "VALID" if not missing else "INVALID"
    result["execution"]["actual_physical_solve_count"] = 1
    result["cases"]["EXACT_N3"] = {
        "status": "RUN_PASS" if not missing else "RUN_PASS_MISSING_PROBES",
        "raw_path": rel(raw),
        "raw_sha256": sha256(raw),
        "missing_required_probes": missing,
    }
    write_json(EXP / "result.json", result)
    if missing:
        raise RuntimeError(f"required probe failure; delayed cases remain stopped: {missing}")
    print(json.dumps({
        "status": "RUN_PASS",
        "run_id": "EXACT_N3",
        "raw": rel(raw),
        "raw_sha256": sha256(raw),
        "sample_count": trace.sample_count,
    }, ensure_ascii=False, indent=2))


def phase_navigation(trace: Any, signal: str) -> dict[str, Any]:
    _, continuous_unwrap = import_tools()
    raw = trace.column(signal)
    unwrapped = continuous_unwrap(raw)
    base_index = next(index for index, value in enumerate(trace.time) if value * 1.0e12 >= 101.0)
    relative = [
        (unwrapped[index] - unwrapped[base_index]) / TAU
        for index in range(base_index, len(unwrapped))
    ]
    focus = time_indices(trace, *FOCUS_WINDOW)
    focus_relative = [
        (unwrapped[index] - unwrapped[focus[0]]) / TAU for index in focus
    ]
    crossings = {
        f"{threshold:g}": next(
            (
                trace.time[index] * 1.0e12
                for index in range(base_index, len(unwrapped))
                if (unwrapped[index] - unwrapped[base_index]) / TAU <= threshold
            ),
            None,
        )
        for threshold in PHASE_NAVIGATION_THRESHOLDS
    }
    return {
        "signal": signal,
        "raw_unit": "radians",
        "display_unit": "turns",
        "display_rule": "continuous_unwrap(rad)/(2*pi); navigation only",
        "baseline_time_ps": trace.time[base_index] * 1.0e12,
        "negative_threshold_navigation_times_ps": crossings,
        "relative_max_turns": max(relative),
        "relative_min_turns": min(relative),
        "relative_final_turns": relative[-1],
        "relative_p2p_turns": max(relative) - min(relative),
        "focus_110_121_endpoint_delta_turns": focus_relative[-1],
        "focus_110_121_p2p_turns": max(focus_relative) - min(focus_relative),
        "focus_110_121_min_turns": min(focus_relative),
        "focus_110_121_max_turns": max(focus_relative),
        "semantic_role": "PHASE_NAVIGATION_ONLY; not an SFQ count",
    }


def waveform_stats(trace: Any, signal: str, start_ps: float, end_ps: float) -> dict[str, Any]:
    indices = time_indices(trace, start_ps, end_ps)
    values = trace.column(signal)
    selected_times = [trace.time[index] for index in indices]
    selected_values = [values[index] for index in indices]
    if len(indices) < 2:
        return {"status": "UNKNOWN", "signal": signal, "window_ps": [start_ps, end_ps]}
    signed_area = actual_integral(selected_times, selected_values)
    peak_index = max(range(len(indices)), key=lambda position: abs(selected_values[position]))
    return {
        "status": "DERIVED",
        "signal": signal,
        "window_ps": [start_ps, end_ps],
        "sample_count": len(indices),
        "unit": "A" if signal.startswith("I(") else "V",
        "minimum": min(selected_values),
        "maximum": max(selected_values),
        "p2p": max(selected_values) - min(selected_values),
        "mean": sum(selected_values) / len(selected_values),
        "rms": math.sqrt(sum(value * value for value in selected_values) / len(selected_values)),
        "peak_abs": abs(selected_values[peak_index]),
        "time_of_peak_abs_ps": selected_times[peak_index] * 1.0e12,
        "signed_area": signed_area,
        "absolute_area": actual_integral(selected_times, [abs(value) for value in selected_values]),
    }


def phase_area_crosscheck(trace: Any, phase_signal: str, voltage_signal: str) -> dict[str, Any]:
    _, continuous_unwrap = import_tools()
    indices = time_indices(trace, *FOCUS_WINDOW)
    times = [trace.time[index] for index in indices]
    voltage = [trace.column(voltage_signal)[index] for index in indices]
    phase = [trace.column(phase_signal)[index] for index in indices]
    unwrapped = continuous_unwrap(phase)
    phase_delta_turns = (unwrapped[-1] - unwrapped[0]) / TAU
    voltage_area_turns = actual_integral(times, voltage) / PHI0
    return {
        "status": "DERIVED",
        "phase_signal": phase_signal,
        "voltage_signal": voltage_signal,
        "raw_phase_unit": "radians",
        "window_ps": list(FOCUS_WINDOW),
        "sample_count": len(indices),
        "phase_delta_turns": phase_delta_turns,
        "voltage_time_area_Wb": actual_integral(times, voltage),
        "voltage_area_over_Phi0_turns": voltage_area_turns,
        "phase_minus_area_turns": phase_delta_turns - voltage_area_turns,
        "phi0_Wb": PHI0,
        "actual_grid_trapezoid": True,
        "same_jj_same_endpoints_same_direction": True,
        "semantic_role": "phase/area cross-check; not an SFQ count",
    }


def delta_stats(
    canonical: Any,
    exact: Any,
    signal: str,
    indices: list[int],
) -> dict[str, Any]:
    canonical_values = canonical.column(signal)
    exact_values = exact.column(signal)
    deltas = [exact_values[index] - canonical_values[index] for index in indices]
    abs_deltas = [abs(value) for value in deltas]
    peak = max(range(len(indices)), key=lambda position: abs_deltas[position])
    result: dict[str, Any] = {
        "signal": signal,
        "window_grid": "canonical/exact same stored timestamps",
        "sample_count": len(indices),
        "unit": "A" if signal.startswith("I(") else "V" if signal.startswith("V(") else "raw_phase_rad",
        "max_abs_delta": max(abs_deltas),
        "rms_delta": math.sqrt(sum(value * value for value in deltas) / len(deltas)),
        "mean_delta": sum(deltas) / len(deltas),
        "time_of_max_abs_delta_ps": exact.time[indices[peak]] * 1.0e12,
        "canonical_min": min(canonical_values[index] for index in indices),
        "canonical_max": max(canonical_values[index] for index in indices),
        "exact_min": min(exact_values[index] for index in indices),
        "exact_max": max(exact_values[index] for index in indices),
    }
    if signal.startswith("P("):
        _, continuous_unwrap = import_tools()
        canonical_unwrapped = continuous_unwrap(canonical_values)
        exact_unwrapped = continuous_unwrap(exact_values)
        phase_deltas_turns = [
            (exact_unwrapped[index] - canonical_unwrapped[index]) / TAU
            for index in indices
        ]
        result["phase_delta_rule"] = "independent continuous unwrap then subtract; rad/(2*pi)"
        result["max_abs_delta_turns"] = max(abs(value) for value in phase_deltas_turns)
        result["rms_delta_turns"] = math.sqrt(
            sum(value * value for value in phase_deltas_turns) / len(phase_deltas_turns)
        )
        result["endpoint_delta_turns"] = phase_deltas_turns[-1]
        result["p2p_delta_turns"] = max(phase_deltas_turns) - min(phase_deltas_turns)
    return result


def fidelity_signal_list() -> list[str]:
    signals: list[str] = []
    for index in range(1, 5):
        signals.extend(f"I(I_{kind}{index})" for kind in ("WL", "BL", "SE"))
        for element in BVM_JUNCTIONS:
            signals.extend(
                f"{kind}({element}|XBVM{index})" for kind in ("P", "V", "I")
            )
        for element in BVM_BRANCHES:
            signals.extend(f"{kind}({element}|XBVM{index})" for kind in ("I", "V"))
    signals.append("V(COMMON_SL)")
    for index in range(1, JSL_COUNT + 1):
        signals.extend(f"{kind}(B_JSL{index})" for kind in ("P", "V", "I"))
    signals.append("V(QBIN)")
    return signals


def analyze() -> None:
    provenance = read_json(EXP / "provenance.json")
    if provenance.get("actual_physical_solve_count") != 1:
        raise RuntimeError("analysis requires exactly one completed EXACT_N3 solve")
    canonical = load_raw(CANONICAL_RAW)
    exact_path = EXP / "runs" / "EXACT_N3" / "raw.csv"
    exact = load_raw(exact_path)
    required = expected_headers()
    missing = sorted(required - set(exact.headers))
    if missing:
        raise RuntimeError(f"EXACT_N3 raw is missing required probes: {missing}")

    before = sha256(exact_path)
    grid_match = tuple(canonical.time) == tuple(exact.time)
    fidelity: dict[str, Any] = {
        "status": "SCIENTIFIC_REVIEW_REQUIRED",
        "candidate_gate_state": "NOT_AUTOMATICALLY_DECIDED",
        "delayed_cases_authorized": False,
        "delayed_cases_not_run": ["DELAY_0P6", "DELAY_1P2"],
        "reason": "No numerical fidelity tolerance and no SCIENTIFIC_REVIEW_AUTHORIZED token were supplied.",
        "canonical_raw": {
            "path": rel(CANONICAL_RAW),
            "sha256": sha256(CANONICAL_RAW),
            "grid": finite_grid_qa(canonical),
        },
        "exact_raw": {
            "path": rel(exact_path),
            "sha256": before,
            "grid": finite_grid_qa(exact),
        },
        "actual_stored_grid_match": grid_match,
        "interpolation_used": False,
        "focus_window_ps": list(FOCUS_WINDOW),
        "full_window_ps": [0.0, 200.0],
        "input_boundary": {
            "source_pwl_points": provenance["replay_authority"]["pwl"]["point_count"],
            "source_values_are_exact_stored_tokens": True,
            "output_v_qbin_stats": {},
        },
        "signal_deltas": {},
        "phase_navigation": {"canonical": {}, "exact": {}},
        "same_jj_phase_area_crosscheck": {"canonical": {}, "exact": {}},
        "canonical_only_boundary_feedback": {
            "status": "OBSERVED_REFERENCE_ONLY",
            "signals": ["I(L1|XBQ1)", "V(L1|XBQ1)", "I(BJ1|XBQ1)", "I(BJ2|XBQ1)"],
            "exact_replay_status": "NOT_APPLICABLE_QB_REMOVED",
        },
    }
    if grid_match:
        full_indices = list(range(exact.sample_count))
        focus_indices = time_indices(exact, *FOCUS_WINDOW)
        fidelity["input_boundary"]["output_v_qbin_stats"] = {
            "full_0_200_ps": waveform_stats(exact, "V(QBIN)", 0.0, 200.0),
            "focus_110_121_ps": waveform_stats(exact, "V(QBIN)", *FOCUS_WINDOW),
        }
        for signal in fidelity_signal_list():
            fidelity["signal_deltas"][signal] = {
                "full_0_200_ps": delta_stats(canonical, exact, signal, full_indices),
                "focus_110_121_ps": delta_stats(canonical, exact, signal, focus_indices),
            }
    else:
        fidelity["status"] = "GRID_MISMATCH_STOP"
        fidelity["candidate_gate_state"] = "STOP_NO_INTERPOLATION"
        fidelity["reason"] = "Canonical and EXACT raw stored grids differ; no interpolation or resampling was permitted."

    for index in range(1, 5):
        for element in ("B_JS1", "B_JS2"):
            signal = f"P({element}|XBVM{index})"
            fidelity["phase_navigation"]["canonical"][signal] = phase_navigation(canonical, signal)
            fidelity["phase_navigation"]["exact"][signal] = phase_navigation(exact, signal)
            phase_area_phase = f"P({element}|XBVM{index})"
            phase_area_voltage = f"V({element}|XBVM{index})"
            fidelity["same_jj_phase_area_crosscheck"]["canonical"][signal] = phase_area_crosscheck(
                canonical, phase_area_phase, phase_area_voltage
            )
            fidelity["same_jj_phase_area_crosscheck"]["exact"][signal] = phase_area_crosscheck(
                exact, phase_area_phase, phase_area_voltage
            )

    fidelity["replay_source_current"] = {
        "signal": "I(V_REPLAY)",
        "full_0_200_ps": waveform_stats(exact, "I(V_REPLAY)", 0.0, 200.0),
        "focus_110_121_ps": waveform_stats(exact, "I(V_REPLAY)", *FOCUS_WINDOW),
        "semantic_role": "ideal replay source branch current; not canonical source current",
    }
    fidelity["jtl_source_regeneration"] = {
        "status": "NOT_APPLICABLE_TO_REPLAY_FIXTURE",
        "reason": "Replay fixture has no QB/JTL; upstream JSL and I(V_REPLAY) are retained for review.",
    }

    after = sha256(exact_path)
    if before != after:
        raise RuntimeError("EXACT_N3 raw changed during analysis")
    provenance["raw_hash_before_analysis"] = {"EXACT_N3": before}
    provenance["raw_hash_after_analysis"] = {"EXACT_N3": after}
    provenance["analysis"] = {
        "generated_at": now(),
        "scientific_interpretation_performed": False,
        "registered_arithmetic_only": True,
        "actual_grid_comparison": grid_match,
        "raw_hashes_equal_before_after": True,
        "fidelity": fidelity,
    }
    provenance["stop"] = {
        "final_marker": FINAL_MARKER,
        "automatic_follow_up": False,
        "delayed_cases_run": False,
        "stop_reason": "EXACT_ONLY_REVIEW_GATED" if grid_match else "BOUNDARY_VOLTAGE_REPLAY_NOT_SUFFICIENT",
    }
    write_json(EXP / "provenance.json", provenance)

    result = read_json(EXP / "result.json")
    result.update(
        {
            "generated_at": now(),
            "status": "EXACT_ONLY_COMPLETE_REVIEW_GATED" if grid_match else "BOUNDARY_VOLTAGE_REPLAY_NOT_SUFFICIENT",
            "artifact_status": "VALID",
            "execution": {
                "authorized_physical_solve_count": 1,
                "actual_physical_solve_count": 1,
                "authorized_run_order": ["EXACT_N3"],
                "registered_but_not_run": ["DELAY_0P6", "DELAY_1P2"],
            },
            "fidelity": fidelity,
            "cases": {
                "EXACT_N3": {
                    "status": "RUN_PASS",
                    "raw_path": "runs/EXACT_N3/raw.csv",
                    "raw_sha256": after,
                },
                "DELAY_0P6": {"status": "REVIEW_GATED_NOT_RUN"},
                "DELAY_1P2": {"status": "REVIEW_GATED_NOT_RUN"},
            },
            "stop": {
                "final_marker": FINAL_MARKER,
                "automatic_follow_up": False,
                "delayed_cases_run": False,
            },
        }
    )
    write_json(EXP / "result.json", result)
    (EXP / "RESULT.md").write_text(result_markdown(result), encoding="utf-8")
    print(json.dumps({
        "status": result["status"],
        "grid_match": grid_match,
        "delayed_cases_run": False,
        "raw_hash_unchanged": True,
    }, ensure_ascii=False, indent=2))


def result_markdown(result: dict[str, Any]) -> str:
    fidelity = result.get("fidelity", {})
    nav = fidelity.get("phase_navigation", {})
    cross = fidelity.get("same_jj_phase_area_crosscheck", {})
    lines = [
        f"# BVM -> QB boundary timing replay ({EXP.name})",
        "",
        f"- Status: {result.get('status')}",
        f"- Final state: {FINAL_MARKER}",
        "- Scientific interpretation: NOT_PERFORMED; this is an evidence handoff for review.",
        "- Physical solves: EXACT_N3 = 1; DELAY_0P6 = 0; DELAY_1P2 = 0.",
        "- Fixture: 4 BVM -> COMMON_SL -> 8 JSL -> QBIN ideal voltage replay; QB/JTL/terminal removed.",
        "- Replay authority: canonical no-shunt N3 `0111` raw `V(QBIN)` only; exact stored samples, no interpolation.",
        "",
        "## Registered observations and arithmetic",
        "",
        "The following are raw observations or registered arithmetic. They do not assign a mechanism, SFQ count, or physical equivalence.",
        "",
        f"- Stored-grid equality: `{fidelity.get('actual_stored_grid_match')}`.",
        f"- Replay source points: `{fidelity.get('input_boundary', {}).get('source_pwl_points')}`.",
        f"- `V(QBIN)` source/output consistency is recorded in `result.json` under `fidelity.input_boundary`.",
        "",
        "### Phase navigation landmarks",
        "",
        "`P(...)` raw values are radians. The displayed turns below use independent continuous unwrap and rad/(2*pi), for navigation only; they are not SFQ counts.",
        "",
        "| signal | source -0.5 turn crossing (ps) | EXACT -0.5 turn crossing (ps) | source [110,121) p2p (turns) | EXACT [110,121) p2p (turns) |",
        "|---|---:|---:|---:|---:|",
    ]
    for index in (2, 3, 4):
        for element in ("B_JS1", "B_JS2"):
            signal = f"P({element}|XBVM{index})"
            source = nav.get("canonical", {}).get(signal, {})
            exact = nav.get("exact", {}).get(signal, {})
            source_time = source.get("negative_threshold_navigation_times_ps", {}).get("-0.5")
            exact_time = exact.get("negative_threshold_navigation_times_ps", {}).get("-0.5")
            lines.append(
                f"| `{signal}` | {format_number(source_time)} | {format_number(exact_time)} | "
                f"{format_number(source.get('focus_110_121_p2p_turns'))} | {format_number(exact.get('focus_110_121_p2p_turns'))} |"
            )
    lines += [
        "",
        "### Same-JJ JS1/JS2 phase-area cross-check",
        "",
        "The voltage area uses the actual stored timestamps and the same JJ/endpoints/direction as the phase trace. The residual is a numerical cross-check, not an event count.",
        "",
        "| signal | source phase delta (turns) | source V-area/Phi0 (turns) | EXACT phase delta (turns) | EXACT V-area/Phi0 (turns) |",
        "|---|---:|---:|---:|---:|",
    ]
    for index in (2, 3, 4):
        for element in ("B_JS1", "B_JS2"):
            signal = f"P({element}|XBVM{index})"
            source = cross.get("canonical", {}).get(signal, {})
            exact = cross.get("exact", {}).get(signal, {})
            lines.append(
                f"| `{signal}` | {format_number(source.get('phase_delta_turns'))} | {format_number(source.get('voltage_area_over_Phi0_turns'))} | "
                f"{format_number(exact.get('phase_delta_turns'))} | {format_number(exact.get('voltage_area_over_Phi0_turns'))} |"
            )
    lines += [
        "",
        "## Review questions retained",
        "",
        "The requested extra-JS1/JS2 timing, read p2p contraction, JSL/source regeneration, and JM1/JM2 follower questions remain explicitly review-gated. The raw navigation and full signal deltas are in `result.json`; the delayed cases were not run.",
        "",
        "- Canonical QB-only feedback traces (`L1`, `BJ1`, `BJ2`) are reference-only; they are not present in the replay fixture.",
        "- `I(V_REPLAY)` is the ideal forcing-source branch current and is not a canonical source-current substitute.",
        "- Convergence, SFQ event identity/count, mechanism, and physical equivalence are `UNKNOWN`.",
        "",
        "## Evidence paths",
        "",
        "- Run raw/deck/log: `runs/EXACT_N3/`.",
        "- Standalone full-window plots: `plots/EXACT_N3/`.",
        "- Canonical-vs-EXACT comparison plots: `plots/comparisons/`.",
        "- Machine evidence: `provenance.json` and `result.json`.",
        "- Raw evidence ZIP: Drive only; no ZIP is stored in this repository.",
        "",
        f"Stop marker: {FINAL_MARKER}",
        "",
    ]
    return "\n".join(lines)


def format_number(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, bool):
        return str(value)
    try:
        return f"{float(value):.8g}"
    except (TypeError, ValueError):
        return str(value)


def mechanical_qa() -> None:
    provenance = read_json(EXP / "provenance.json")
    result = read_json(EXP / "result.json")
    failures: list[str] = []
    checks: dict[str, Any] = {}
    run_dir = EXP / "runs" / "EXACT_N3"
    deck = run_dir / "deck.cir"
    raw = run_dir / "raw.csv"
    log = run_dir / "run.log"
    deck_text_value = deck.read_text(encoding="utf-8") if deck.is_file() else ""
    forbidden = [
        token
        for token in ("XBQ", "bq_parameterized", "jtl", "R_TERM", "I(R_TERM)")
        if token.casefold() in deck_text_value.casefold()
    ]
    unexpected_run_files = (
        sorted(path.name for path in run_dir.iterdir() if path.name not in {"deck.cir", "raw.csv", "run.log"})
        if run_dir.is_dir()
        else ["missing_run_directory"]
    )
    unexpected_case_dirs = sorted(
        path.name for path in (EXP / "runs").iterdir() if path.is_dir() and path.name != "EXACT_N3"
    ) if (EXP / "runs").is_dir() else ["missing_runs"]
    warning_lines = [
        line.strip()
        for line in log.read_text(errors="replace").splitlines()
        if any(token in line for token in ("Missing model:", "Unknown device/node", "Cannot store results"))
    ] if log.is_file() else ["missing_run_log"]
    try:
        trace = load_raw(raw)
        missing = sorted(expected_headers() - set(trace.headers))
        raw_qa = finite_grid_qa(trace)
    except Exception as exc:
        trace = None
        missing = [f"raw_parse_error:{exc}"]
        raw_qa = {"status": "INVALID"}
    recorded_hash = provenance.get("runs", {}).get("EXACT_N3", {}).get("raw", {}).get("sha256")
    raw_hash_match = raw.is_file() and sha256(raw) == recorded_hash
    source_hashes_match = all(
        sha256(REPO / item["path"]) == item["sha256"] for item in provenance.get("sources", [])
    )
    deck_ok = (
        deck.is_file()
        and deck_text_value.count("B_JSL8 JSL_NODE7 QBIN jjmit area=5.0") == 1
        and deck_text_value.count("V_REPLAY QBIN 0 PWL(") == 1
        and ".tran 0.1p 200p" in deck_text_value
        and not forbidden
        and "B_JSL8 JSL_NODE7 0" not in deck_text_value
    )
    root_names = {"experiment.yaml", "RESULT.md", "result.json", "provenance.json", "runs", "plots"}
    root_unexpected = sorted(path.name for path in EXP.iterdir() if path.name not in root_names)
    pass_status = bool(
        provenance.get("registration_head") == EXPECTED_HEAD
        and git_head() == EXPECTED_HEAD
        and source_hashes_match
        and deck_ok
        and not unexpected_run_files
        and not unexpected_case_dirs
        and not root_unexpected
        and not warning_lines
        and trace is not None
        and not missing
        and not trace.duplicate_columns
        and raw_hash_match
        and raw_qa.get("sample_count") == 1999
        and raw_qa.get("time_start_ps") == 0.0
        and raw_qa.get("time_end_ps") == 199.9
        and raw_qa.get("strictly_increasing_time") is True
        and provenance.get("actual_physical_solve_count") == 1
        and provenance.get("run_order") == ["EXACT_N3"]
        and not (EXP / "runs" / "DELAY_0P6").exists()
        and not (EXP / "runs" / "DELAY_1P2").exists()
    )
    if not pass_status:
        failures.append("EXACT_N3")
    qa = {
        "schema": "bvm-qb-boundary-timing-replay-mechanical-qa-v1",
        "experiment_id": EXP.name,
        "generated_at": now(),
        "status": "PASS" if pass_status else "FAIL",
        "artifact_status": "VALID" if pass_status else "ARTIFACT_INVALID",
        "head": git_head(),
        "required_registration_head": EXPECTED_HEAD,
        "remote_bvm_master": remote_head(),
        "source_hashes_match": source_hashes_match,
        "authorized_physical_solve_count": 1,
        "actual_physical_solve_count": provenance.get("actual_physical_solve_count"),
        "delayed_cases_run": False,
        "no_sentinel_follow_up": True,
        "no_canonical_bvm_or_qb_mutation": source_hashes_match,
        "no_raw_copy": True,
        "no_interpolation": provenance.get("replay_authority", {}).get("pwl", {}).get("interpolation") is False,
        "raw_hash_before_after_analysis_equal": provenance.get("raw_hash_before_analysis") == provenance.get("raw_hash_after_analysis"),
        "root_unexpected_entries": root_unexpected,
        "run_inventory": {
            "unexpected_run_files": unexpected_run_files,
            "unexpected_case_directories": unexpected_case_dirs,
            "required_files_present": all(path.is_file() for path in (deck, raw, log)),
        },
        "deck": {
            "path": rel(deck),
            "sha256": sha256(deck) if deck.is_file() else None,
            "registered_sha256": provenance.get("registered_decks", {}).get("EXACT_N3", {}).get("sha256"),
            "hash_match": deck.is_file() and sha256(deck) == provenance.get("registered_decks", {}).get("EXACT_N3", {}).get("sha256"),
            "exact_bjsl8_connection": "B_JSL8 JSL_NODE7 QBIN jjmit area=5.0" in deck_text_value,
            "exact_replay_source": "V_REPLAY QBIN 0 PWL(" in deck_text_value,
            "forbidden_removed_topology_tokens": forbidden,
        },
        "raw": {
            "path": rel(raw),
            "sha256": sha256(raw) if raw.is_file() else None,
            "recorded_sha256": recorded_hash,
            "hash_match": raw_hash_match,
            "missing_required_probes": missing,
            "duplicate_columns": trace.duplicate_columns if trace is not None else {},
            "grid": raw_qa,
        },
        "solver_warning_lines": warning_lines,
        "result_json_bytes": (EXP / "result.json").stat().st_size,
        "result_json_under_limit": (EXP / "result.json").stat().st_size <= RESULT_LIMIT_BYTES,
        "scientific_interpretation_performed": False,
        "failures": failures,
    }
    if qa["result_json_under_limit"] is False:
        qa["status"] = "FAIL"
        qa["artifact_status"] = "ARTIFACT_INVALID"
    provenance["qa"] = qa
    write_json(EXP / "provenance.json", provenance)
    result["qa_summary"] = {
        "status": qa["status"],
        "artifact_status": qa["artifact_status"],
        "raw_hash_match": raw_hash_match,
        "result_json_under_limit": qa["result_json_under_limit"],
    }
    write_json(EXP / "result.json", result)
    (EXP / "RESULT.md").write_text(result_markdown(result), encoding="utf-8")
    if qa["status"] != "PASS":
        raise RuntimeError(f"mechanical QA failed; artifact is INVALID: {failures}")
    print(json.dumps({"status": "PASS", "actual_physical_solve_count": 1}, ensure_ascii=False, indent=2))


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
    completed = subprocess.run(command, cwd=REPO, capture_output=True, text=True, check=False)
    if completed.returncode != 0 or not output_path.is_file() or output_path.stat().st_size == 0:
        raise RuntimeError(f"josim-plot2 failed for {output_path}: {completed.stderr[-1000:]}")


def externalize_plotly_runtime(temporary_html: Path, output_html: Path, asset_path: Path) -> None:
    html = temporary_html.read_text(encoding="utf-8")
    matches = list(re.finditer(r"<script(?P<attrs>[^>]*)>(?P<body>.*?)</script>", html, flags=re.DOTALL))
    runtime_match = next(
        (
            match
            for match in matches
            if len(match.group("body")) > 1_000_000
            and ("plotly.js v" in match.group("body") or "var Plotly=" in match.group("body"))
        ),
        None,
    )
    if runtime_match is None:
        raise RuntimeError(f"embedded Plotly runtime not found: {temporary_html}")
    runtime = runtime_match.group("body")
    asset_path.parent.mkdir(parents=True, exist_ok=True)
    if asset_path.exists():
        if asset_path.read_text(encoding="utf-8") != runtime:
            raise RuntimeError("Plotly runtime differs between visualization pages")
    else:
        asset_path.write_text(runtime, encoding="utf-8")
    asset_ref = Path(os.path.relpath(asset_path, output_html.parent)).as_posix()
    compact = html[: runtime_match.start()] + f'<script src="{asset_ref}"></script>' + html[runtime_match.end() :]
    if "plotly.js v" in compact or "var Plotly=" in compact or "cdn.plot.ly" in compact:
        raise RuntimeError(f"Plotly runtime was not externalized: {output_html}")
    output_html.parent.mkdir(parents=True, exist_ok=True)
    output_html.write_text(compact, encoding="utf-8")


def render_external_page(input_path: Path, output_path: Path, subset: list[str], title: str, asset_path: Path) -> None:
    if output_path.exists():
        raise RuntimeError(f"refusing overwrite of visualization: {output_path}")
    with tempfile.NamedTemporaryFile(prefix="bvm_boundary_replay_", suffix=".html", delete=False, dir="/tmp") as handle:
        temporary = Path(handle.name)
    try:
        plotter_html(input_path, temporary, subset, title)
        externalize_plotly_runtime(temporary, output_path, asset_path)
    finally:
        temporary.unlink(missing_ok=True)


def prefixed_label(case: str, signal: str) -> str:
    return f"{signal[0]}({case}|{signal[2:-1]})"


def comparison_csv(canonical: Any, exact: Any, signals: list[str]) -> tuple[Path, list[str]]:
    if tuple(canonical.time) != tuple(exact.time):
        raise RuntimeError("comparison raw grids do not match; no interpolation permitted")
    selected: list[tuple[str, list[float]]] = []
    labels: list[str] = []
    for case, trace in (("CANONICAL", canonical), ("EXACT", exact)):
        for signal in signals:
            if signal in trace.headers:
                label = prefixed_label(case, signal)
                labels.append(label)
                selected.append((label, list(trace.column(signal))))
    with tempfile.NamedTemporaryFile(prefix="bvm_boundary_compare_", suffix=".csv", delete=False, dir="/tmp") as handle:
        temporary = Path(handle.name)
    with temporary.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["time", *labels])
        for index, timestamp in enumerate(canonical.time):
            writer.writerow([f"{timestamp:.17e}", *(f"{values[index]:.17e}" for _, values in selected)])
    return temporary, labels


def visualization() -> None:
    provenance = read_json(EXP / "provenance.json")
    if provenance.get("qa", {}).get("status") != "PASS":
        raise RuntimeError("mechanical QA must pass before visualization")
    raw = EXP / "runs" / "EXACT_N3" / "raw.csv"
    exact = load_raw(raw)
    canonical = load_raw(CANONICAL_RAW)
    available = set(exact.headers)
    all_bvm_js = [
        f"{kind}({element}|XBVM{index})"
        for index in range(1, 5)
        for element in BVM_JUNCTIONS
        for kind in ("P", "V", "I")
    ]
    all_rloop = [
        f"{kind}({element}|XBVM{index})"
        for index in range(1, 5)
        for element in BVM_BRANCHES
        for kind in ("I", "V")
    ]
    all_source = [f"I(I_{kind}{index})" for index in range(1, 5) for kind in ("WL", "BL", "SE")]
    all_jsl = [
        f"{kind}(B_JSL{index})"
        for index in range(1, JSL_COUNT + 1)
        for kind in ("P", "V", "I")
    ]
    specs = {
        "01_signal_timing": (
            all_source + [
                "V(COMMON_SL)",
                "P(B_JS1|XBVM2)",
                "V(B_JS1|XBVM2)",
                "I(B_JS1|XBVM2)",
                "P(B_JS2|XBVM2)",
                "V(B_JS2|XBVM2)",
                "I(B_JS2|XBVM2)",
                "V(QBIN)",
                "I(V_REPLAY)",
            ],
            "EXACT_N3 signal timing: stimulus -> BVM JS -> COMMON_SL -> QBIN replay",
        ),
        "02_bvm_state": (all_bvm_js, "EXACT_N3 BVM JM1/JM2/JS1/JS2 raw P/V/I; phase displayed as turns navigation"),
        "03_bvm_rloop": (all_rloop, "EXACT_N3 BVM storage/R-loop branch I/V; canonical branch directions"),
        "04_jsl_boundary": (["V(COMMON_SL)", *all_jsl, "V(QBIN)", "I(V_REPLAY)"], "EXACT_N3 COMMON_SL -> JSL1..8 -> QBIN ideal replay boundary"),
        "05_phase_area_review": ([
            signal
            for index in (2, 3, 4)
            for element in ("B_JS1", "B_JS2")
            for signal in (
                f"P({element}|XBVM{index})",
                f"V({element}|XBVM{index})",
                f"I({element}|XBVM{index})",
            )
        ] + ["V(QBIN)", "I(V_REPLAY)"], "EXACT_N3 active-BVM JS1/JS2 phase and voltage-area navigation"),
    }
    asset = EXP / "plots" / "assets" / "plotly.min.js"
    entries: list[dict[str, Any]] = []
    for page_name, (signals, note) in specs.items():
        selected = [signal for signal in signals if signal in available]
        missing = sorted(set(signals) - set(selected))
        if missing:
            raise RuntimeError(f"missing visualization probes for {page_name}: {missing}")
        output = EXP / "plots" / "EXACT_N3" / f"{page_name}.html"
        render_external_page(raw, output, selected, note, asset)
        entries.append({
            "kind": "standalone",
            "case_id": "EXACT_N3",
            "path": rel(output),
            "raw_path": rel(raw),
            "raw_sha256": sha256(raw),
            "sha256": sha256(output),
            "bytes": output.stat().st_size,
            "signals": selected,
            "window_ps": [0.0, 200.0],
            "focused_windows": [],
            "renderer": rel(PLOTTER),
            "layout": "sep_comb",
            "color": "dark",
            "phase_display": "rad/(2*pi) turns navigation",
            "note": note,
        })

    comparison_specs = {
        "exact_vs_canonical_upstream": [
            "V(COMMON_SL)",
            "V(QBIN)",
            *[
                signal
                for index in range(1, 5)
                for element in ("B_JS1", "B_JS2")
                for signal in (
                    f"P({element}|XBVM{index})",
                    f"V({element}|XBVM{index})",
                    f"I({element}|XBVM{index})",
                )
            ],
            *all_jsl,
        ],
        "exact_vs_canonical_rloop": [
            *[
                f"{kind}({element}|XBVM{index})"
                for index in range(1, 5)
                for element in ("L_M3", "L_S3", "R_S", "L_SL")
                for kind in ("I", "V")
            ],
            *[
                f"P({element}|XBVM{index})"
                for index in range(1, 5)
                for element in ("B_JM1", "B_JM2")
            ],
        ],
    }
    comparison_entries: list[dict[str, Any]] = []
    if tuple(canonical.time) == tuple(exact.time):
        for page_name, signals in comparison_specs.items():
            selected = [signal for signal in signals if signal in canonical.headers and signal in exact.headers]
            temporary, labels = comparison_csv(canonical, exact, selected)
            output = EXP / "plots" / "comparisons" / f"{page_name}.html"
            try:
                render_external_page(
                    temporary,
                    output,
                    labels,
                    f"CANONICAL vs EXACT_N3: {page_name} (full 0-200 ps)",
                    asset,
                )
            finally:
                temporary.unlink(missing_ok=True)
            comparison_entries.append({
                "kind": "comparison",
                "cases": ["CANONICAL", "EXACT_N3"],
                "path": rel(output),
                "sha256": sha256(output),
                "bytes": output.stat().st_size,
                "signals": selected,
                "labels": labels,
                "window_ps": [0.0, 200.0],
                "focused_windows": [],
                "renderer": rel(PLOTTER),
                "layout": "sep_comb",
                "color": "dark",
                "phase_display": "independent case phase display as rad/(2*pi) turns navigation",
            })
    else:
        provenance.setdefault("visualization", {})["comparison_status"] = "NOT_RENDERED_GRID_MISMATCH"

    plots = sorted(path for path in (EXP / "plots").rglob("*") if path.is_file())
    html_paths = [path for path in plots if path.suffix.lower() == ".html"]
    if not html_paths or not asset.is_file():
        raise RuntimeError("visualization output is incomplete")
    if any(
        "plotly.js v" in path.read_text(encoding="utf-8")
        or "var Plotly=" in path.read_text(encoding="utf-8")
        or "cdn.plot.ly" in path.read_text(encoding="utf-8")
        for path in html_paths
    ):
        raise RuntimeError("embedded or CDN Plotly runtime remains")
    visualization = {
        "status": "PASS",
        "generated_at": now(),
        "renderer": rel(PLOTTER),
        "layout": "sep_comb",
        "color": "dark",
        "phase_option": "2pi",
        "window_ps": [0.0, 200.0],
        "focused_windows": [],
        "entries": entries + comparison_entries,
        "standalone_count": len(entries),
        "comparison_count": len(comparison_entries),
        "asset": {"path": rel(asset), "sha256": sha256(asset), "bytes": asset.stat().st_size},
        "raw_hashes_rechecked": all(item["raw_sha256"] == sha256(raw) for item in entries),
        "scientific_interpretation_performed": False,
        "no_png_svg": all(path.suffix.lower() not in {".png", ".svg"} for path in plots),
    }
    provenance["visualization"] = visualization
    write_json(EXP / "provenance.json", provenance)
    result = read_json(EXP / "result.json")
    result["visualization_summary"] = {
        "status": "PASS",
        "standalone_count": len(entries),
        "comparison_count": len(comparison_entries),
        "full_window_only": True,
        "asset": rel(asset),
    }
    write_json(EXP / "result.json", result)
    (EXP / "RESULT.md").write_text(result_markdown(result), encoding="utf-8")
    print(json.dumps({
        "status": "PASS",
        "standalone_count": len(entries),
        "comparison_count": len(comparison_entries),
        "asset": rel(asset),
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
        raise RuntimeError(f"refusing overwrite of immutable package: {package_path}")
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
    files.append((SCRIPT, "executor/bvm_qb_boundary_timing_replay.py"))
    records = [
        {"path": archive_name, "sha256": sha256(path), "bytes": path.stat().st_size}
        for path, archive_name in files
    ]
    with zipfile.ZipFile(package_path, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
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
        "contains_canonical_raw_copy": False,
        "contains_delayed_run": any(record["path"].startswith("runs/DELAY_") for record in records),
        "qa_outside_zip": True,
        "git_head_at_packaging": git_head(),
        "remote_head_at_packaging": remote_head(),
    }
    provenance["package"] = {
        "status": "READY_FOR_DRIVE_UPLOAD" if package_qa["status"] == "PASS" else "PACKAGE_INVALID",
        "qa": package_qa,
        "delivery_path": str(package_path),
        "drive_file_id": None,
        "drive_url": None,
    }
    write_json(EXP / "provenance.json", provenance)
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
        raise RuntimeError("package reopen QA failed; do not commit package metadata")
    print(json.dumps({
        "status": "PASS",
        "package_path": str(package_path),
        "sha256": package_qa["package_sha256"],
        "bytes": package_qa["package_bytes"],
        "files": package_qa["file_count"],
        "not_in_git": True,
    }, ensure_ascii=False, indent=2))


def record_drive(file_id: str, url: str | None = None) -> None:
    provenance = read_json(EXP / "provenance.json")
    package_info = provenance.get("package", {})
    package_qa = package_info.get("qa", {})
    package_path = Path(package_info.get("delivery_path", ""))
    if not package_path.is_file():
        raise RuntimeError("delivery ZIP is missing")
    if sha256(package_path) != package_qa.get("package_sha256"):
        raise RuntimeError("delivery ZIP changed before Drive record")
    package_info.update({
        "status": "UPLOADED",
        "drive_file_id": file_id,
        "drive_url": url,
        "drive_uploaded_at": now(),
    })
    provenance["package"] = package_info
    write_json(EXP / "provenance.json", provenance)
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
    actions = {
        "prepare": prepare,
        "run": execute,
        "analyze": analyze,
        "qa": mechanical_qa,
        "viz": visualization,
        "package": package,
        "record-drive": lambda: record_drive(
            sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None
        ),
    }
    if command == "all":
        for action in (prepare, execute, analyze, mechanical_qa, visualization):
            action()
        return 0
    if command not in actions:
        print(
            f"usage: {SCRIPT.name} [prepare|run|analyze|qa|viz|package|record-drive FILE_ID [URL]|all]",
            file=sys.stderr,
        )
        return 2
    if command == "record-drive" and len(sys.argv) < 3:
        print("record-drive requires FILE_ID", file=sys.stderr)
        return 2
    actions[command]()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
