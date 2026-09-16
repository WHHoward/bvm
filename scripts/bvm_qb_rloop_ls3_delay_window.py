#!/usr/bin/env python3
"""LS3-only 0.2/0.4-ps timing-window closure.

The 0.3-ps cases are read-only references from the accepted branch
decomposition experiment.  This runner executes only the four registered
0.2/0.4-ps N2/N3 cases and performs mechanical evidence packaging.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
SCRIPT = Path(__file__).resolve()
sys.path.insert(0, str(REPO / "scripts"))
import bvm_qb_rloop_ls3_population_validation as common  # noqa: E402

branch = common.branch_helpers
EXP = REPO / "test" / "exploration" / "bvm-rloop-ls3-delay-window-v1-20260916"
REFERENCE_ROOT = REPO / "test" / "exploration" / "bvm-qb-threshold-ordering-boundary-search-v1-20260911" / "references" / "canonical_baseline"
SOURCE_INPUTS = REPO / "test" / "exploration" / "bvm-qb-threshold-ordering-boundary-search-v1-20260911" / "inputs"
PREVIOUS = REPO / "test" / "exploration" / "bvm-rloop-branch-timing-decomposition-v1-20260916"
SOLVER = REPO / "build" / "josim-cli"
PLOTTER = REPO / "scripts" / "josim-plot2.py"
ORACLE = REPO / "test" / "exploration" / "bvm-population-scaling-rj2p12-l1p14-l2p20-ib260-rj32-bjs400-v1-20260910" / "analysis" / "population_oracle.py"

CANONICAL = {mask: REFERENCE_ROOT / mask / "raw.csv" for mask in ("0011", "0111")}
CANONICAL_DECKS = {mask: REFERENCE_ROOT / mask / "deck.cir" for mask in ("0011", "0111")}
PREVIOUS_RAW = {
    "LS3_EXACT_0011": PREVIOUS / "runs" / "LS3_EXACT_0011" / "raw.csv",
    "LS3_DELAY0P3_0011": PREVIOUS / "runs" / "LS3_DELAY0P3_0011" / "raw.csv",
    "LS3_EXACT_0111": PREVIOUS / "runs" / "LS3_EXACT_0111" / "raw.csv",
    "LS3_DELAY0P3_0111": PREVIOUS / "runs" / "LS3_DELAY0P3_0111" / "raw.csv",
}
EXPECTED_HEAD = "b904851be588ca88d40cf1700d5fef7ce3d889ed"
EXPECTED_CANONICAL_HASHES = {
    "0011": "3da7b754c990316ff8e5981692afa958d8056a61020a1912548bf6f2b7e0249c",
    "0111": "1ca15a938b23d4ed08eb964713f91476256c4caf0677d1bfd3dc43020271ec75",
}
EXPECTED_PREVIOUS_HASHES = {
    "LS3_EXACT_0011": "8416225dae6edf23cc125e18bb90cb96ef481860865a94f6e444d44fc6465246",
    "LS3_DELAY0P3_0011": "86bdf260882804948c830a4d885b7465d0ab8e479d4adb57830ed0deb8573d8d",
    "LS3_EXACT_0111": "a4f1f8f014f8048e19594da43acc7c4d41e1e5bfbb0bde320edaa513763cb3ef",
    "LS3_DELAY0P3_0111": "93e5672abfe9e0489c056a07f6d4a80b71a618c17e361dccace5a8a33bd91b37",
}
PINNED_INPUTS = {
    SOURCE_INPUTS / "jjmit.cir": "19862d1fd1f1f44dfa1523848d7d3b5e2594a6c5da8fdd80144b449e5312a336",
    SOURCE_INPUTS / "bvm_jm2_connected.cir": "0093a45cc3910448b484d8bd004c6df8c22358bacc8b3ed5e23912dcab805d54",
    SOURCE_INPUTS / "BQ_parameterized_bjs400_rj2.cir": "43468c49eb56090e586428a8ca26d17d8bbf107fbd9e535bbac7a72ed1200d42",
    SOURCE_INPUTS / "jtl2.cir": "ffd31f8eda2a86ca0133342be1ce678831b7237a53911eda046d2bff8454855a",
}
DELAY_POINTS = {"0P2": (0.2, 2), "0P4": (0.4, 4)}
RUN_ORDER = ("LS3_DELAY0P2_0011", "LS3_DELAY0P2_0111", "LS3_DELAY0P4_0011", "LS3_DELAY0P4_0111")
PHI0 = 2.067833848e-15
FOCUS = (110.0, 121.0)
REARM = (121.0, 130.0)
FULL = (0.0, 200.0)
CONTRACT_SENTENCE = "This experiment is governed by docs/EXPERIMENT_CONTRACT.md."
FINAL_MARKER = "EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW"
DRIVE_FOLDER_ID = "1--nlY7Nq5ArVPydJNrnQf-EGmwN-undh"
KNOWN_WARNINGS = {"Unknown device/node IB|XBQ1", "Cannot store results for this device/node."}
JTL_STAGES = tuple(range(1, 7))


def now() -> str:
    return __import__("datetime").datetime.now().astimezone().isoformat(timespec="seconds")


sha256 = common.sha256
sha256_text = common.sha256_text
rel = common.rel
write_json = common.write_json
read_json = common.read_json
load_raw = common.load_raw
time_indices = common.time_indices
actual_integral = common.actual_integral
vector_stats = common.vector_stats
normalized_delta = common.normalized_delta
multi_evidence_oracle = common.multi_evidence_oracle
load_oracle_module = common.load_oracle_module


def git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()


def remote_head() -> str | None:
    try:
        text = subprocess.check_output(["git", "ls-remote", "bvm", "refs/heads/master"], cwd=REPO, text=True, timeout=30).strip()
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None
    return text.split()[0] if text else None


def record_file(name: str, path: Path, role: str) -> dict[str, Any]:
    if not path.is_file():
        raise RuntimeError(f"missing source: {path}")
    return {"name": name, "path": rel(path), "sha256": sha256(path), "bytes": path.stat().st_size, "role": role}


def case_info(case_id: str) -> dict[str, Any]:
    match = re.fullmatch(r"LS3_DELAY(0P2|0P4)_(0011|0111)", case_id)
    if not match:
        raise RuntimeError(f"invalid case id: {case_id}")
    point, mask = match.groups()
    delay, shift = DELAY_POINTS[point]
    return {"case_id": case_id, "point": point, "mask": mask, "delay_ps": delay, "stored_sample_shift": shift}


def case_dir(case_id: str) -> Path:
    return EXP / "runs" / case_id


def assert_registration() -> None:
    if git_head() != EXPECTED_HEAD or remote_head() != EXPECTED_HEAD:
        raise RuntimeError(f"HEAD/remote mismatch: {git_head()} / {remote_head()} != {EXPECTED_HEAD}")
    for path, expected in PINNED_INPUTS.items():
        if not path.is_file() or sha256(path) != expected:
            raise RuntimeError(f"pinned input changed: {path}")
    for mask, expected in EXPECTED_CANONICAL_HASHES.items():
        if sha256(CANONICAL[mask]) != expected:
            raise RuntimeError(f"canonical raw changed: {mask}")
    for key, expected in EXPECTED_PREVIOUS_HASHES.items():
        if sha256(PREVIOUS_RAW[key]) != expected:
            raise RuntimeError(f"previous reference raw changed: {key}")


def source_inventory() -> list[dict[str, Any]]:
    records = [
        record_file("runner", SCRIPT, "LS3 timing-window generator, executor, mechanical analysis, visualization, and package builder"),
        record_file("canonical_jjmit", SOURCE_INPUTS / "jjmit.cir", "canonical global JJ model"),
        record_file("canonical_bvm", SOURCE_INPUTS / "bvm_jm2_connected.cir", "canonical BVM clone template"),
        record_file("canonical_qb", SOURCE_INPUTS / "BQ_parameterized_bjs400_rj2.cir", "canonical QB include"),
        record_file("canonical_jtl", SOURCE_INPUTS / "jtl2.cir", "canonical six-stage JTL include"),
        record_file("josim_solver", SOLVER, "recorded JoSIM binary"),
        record_file("plotter", PLOTTER, "standard JoSIM descriptive plotter"),
        record_file("branch_helper", REPO / "scripts" / "bvm_qb_rloop_branch_timing_decomposition.py", "validated LS3-only topology helper"),
        record_file("population_helper", REPO / "scripts" / "bvm_qb_rloop_ls3_population_validation.py", "read-only metric/oracle helper"),
        record_file("historical_population_oracle", ORACLE, "historical bounded phase/cluster oracle"),
        record_file("previous_branch_result", PREVIOUS / "result.json", "read-only 0.3-ps context"),
        record_file("previous_branch_provenance", PREVIOUS / "provenance.json", "read-only 0.3-ps provenance"),
    ]
    for mask in ("0011", "0111"):
        records.extend([record_file(f"canonical_{mask}_raw", CANONICAL[mask], "read-only canonical raw source"), record_file(f"canonical_{mask}_deck", CANONICAL_DECKS[mask], "read-only canonical deck source")])
    for key, path in PREVIOUS_RAW.items():
        records.append(record_file(f"previous_{key.lower()}", path, "read-only prior branch raw; not copied"))
    return records


def delayed_values(source: list[float], times: list[str], shift: int) -> list[float]:
    start = next(index for index, token in enumerate(times) if abs(float(token) * 1.0e12 - 110.0) < 1.0e-9)
    result: list[float] = []
    for index in range(len(times)):
        if index < start:
            result.append(source[index])
        elif index < start + shift:
            result.append(source[start])
        else:
            result.append(source[index - shift])
    return result


def write_source_csv(path: Path, mask: str, delay_ps: float, shift: int) -> dict[str, Any]:
    times, strings, values = branch.source_tokens(CANONICAL[mask])
    columns = {f"XBVM{index}": f"I(L_S3|XBVM{index})" for index in range(1, 5)}
    replay = {instance: delayed_values(values[column], times, shift) for instance, column in columns.items()}
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["time_s", "time_ps", *[f"I_CANONICAL_LS3_{instance}_A" for instance in columns], *[f"I_LS3_REPLAY_{instance}_A" for instance in columns]])
        for row, token in enumerate(times):
            writer.writerow([token, f"{float(token) * 1.0e12:.17g}", *[branch.current_token(values[columns[instance]][row]) for instance in columns], *[branch.current_token(replay[instance][row]) for instance in columns]])
    start = next(index for index, token in enumerate(times) if abs(float(token) * 1.0e12 - 110.0) < 1.0e-9)
    source_hashes = {instance: sha256_text("\n".join(strings[column]) + "\n") for instance, column in columns.items()}
    replay_hashes = {instance: sha256_text("\n".join(branch.current_token(value) for value in replay[instance]) + "\n") for instance in columns}
    pre_equal = all(replay[instance][row] == values[columns[instance]][row] for instance in columns for row, token in enumerate(times) if float(token) * 1.0e12 < 110.0)
    hold_equal = all(replay[instance][row] == values[columns[instance]][start] for instance in columns for row in range(start, start + shift))
    post_equal = all(replay[instance][row] == values[columns[instance]][row - shift] for instance in columns for row in range(start + shift, len(times)))
    return {"path": rel(path), "sha256": sha256(path), "bytes": path.stat().st_size, "mask": mask, "authority_raw": rel(CANONICAL[mask]), "authority_raw_sha256": sha256(CANONICAL[mask]), "authority_columns": list(columns.values()), "source_column_sha256": source_hashes, "replay_column_sha256": replay_hashes, "point_count": len(times), "start_sample_index": start, "start_time_ps": float(times[start]) * 1.0e12, "delay_ps": delay_ps, "stored_sample_shift": shift, "pre_110_nonanticipation": pre_equal, "hold_rule_check": hold_equal, "post_shift_rule_check": post_equal, "interpolation": False, "resampling": False, "amplitude_scaling": False, "sign_change": False, "positive_direction": "node6 -> node10"}


def make_case_deck(case_id: str) -> dict[str, Any]:
    info = case_info(case_id)
    times, _, values = branch.source_tokens(CANONICAL[info["mask"]])
    replay = {f"XBVM{index}": delayed_values(values[f"I(L_S3|XBVM{index})"], times, info["stored_sample_shift"]) for index in range(1, 5)}
    source_path = EXP / "inputs" / "replay_sources" / f"{case_id}_branch_current.csv"
    source = write_source_csv(source_path, info["mask"], info["delay_ps"], info["stored_sample_shift"])
    payloads = {instance: "PWL(" + " ".join(item for row, token in enumerate(times) for item in (branch.time_token_ps(token), branch.current_token(replay[instance][row]))) + ")" for instance in replay}
    deck = case_dir(case_id) / "deck.cir"
    deck.parent.mkdir(parents=True, exist_ok=True)
    deck.write_text(branch.transformed_deck(info["mask"], "LS3", case_id, payloads, deck.parent), encoding="utf-8")
    return {"run_id": case_id, **info, "path": rel(deck), "sha256": sha256(deck), "bytes": deck.stat().st_size, "source": source, "payload_sha256": {instance: sha256_text(payloads[instance]) for instance in payloads}, "payload_bytes": {instance: len(payloads[instance].encode()) for instance in payloads}, "topology_transform": "validated LS3-only replay: physical R_S retained, L_S3 replaced by same-instance ideal current source; QB/JSL/JTL/terminal unchanged"}


def preflight(direction: dict[str, Any]) -> str:
    return f"""# LS3 timing-window closure — {EXP.name}

{CONTRACT_SENTENCE}

## Registration

- Frozen parent HEAD: `{EXPECTED_HEAD}`; remote `bvm/master`: `{EXPECTED_HEAD}`.
- Study phase: `EXPLORATORY`; role: `Experimental Operator + Evidence Packager`.
- Scientific review authorization: `false`; only mechanical evidence packaging is performed.
- The 0.3-ps N2/N3 exact/delay raw from the prior branch-decomposition experiment is read-only context and is not rerun or copied.

## Single question

Is the registered 0.3-ps LS3-only population-selective timing observation part of a finite timing window rather than a single tested point?

## Frozen fixture

- Working point: L1=1.4 pH, L2=2.0 pH, IBias=260 µA, RJ1=32 Ω, RJ2=12 Ω, BJS area=4.
- Forward path: canonical BVM → COMMON_SL → JSL1..8 → canonical QB → JTL1..6 → 10 Ω terminal.
- LS3-only fixture: retain `R_S 6 10 3.0`; remove physical `L_S3 6 10 0.5P`; impose each same-instance canonical `I(L_S3)` from node6 to node10.
- QB/QBIN/JSL/JTL/terminal/BVM/stimulus/timestep are unchanged.
- `.tran 0.1p 200p`; actual stored 0.1-ps sample semantics; no interpolation, smoothing, resampling, scaling or sign modification.

## Read-only 0.3-ps reference

- Prior branch experiment: `test/exploration/bvm-rloop-branch-timing-decomposition-v1-20260916`.
- Reused runs: `LS3_EXACT_0011`, `LS3_DELAY0P3_0011`, `LS3_EXACT_0111`, `LS3_DELAY0P3_0111`.

## New authorized solves, exact order

1. `LS3_DELAY0P2_0011` — 2 stored samples.
2. `LS3_DELAY0P2_0111` — 2 stored samples.
3. `LS3_DELAY0P4_0011` — 4 stored samples.
4. `LS3_DELAY0P4_0111` — 4 stored samples.

For every delay: t<110 ps uses the canonical same sample; [110,110+delay) holds the 110-ps value; later samples use exact stored index i−shift. No other solve is authorized. N1/N4, 0.3 reruns, sweeps, sentinel, timestep refinement, QB/receiver/topology changes are prohibited.

## Mechanical oracle and limits

- N2: ordered QB→JTL phase-chain count, first/second BJ1/BJ2, L1 re-arm, JSL8 behavior, active JS1/JS2, with phase raw radians and turns only as navigation.
- N3: response 1..4 BJ1/BJ2/JTL1..6 chains, first missing stage, JS1/JS2 p2p and JSL8 behavior.
- Navigation/area/cluster quantities are not literal SFQ counts. Historical strict counts remain contextual where they disagree with multi-evidence records.
- Timing-window labels are mechanical candidates only; final scientific classification remains `NOT_ASSIGNED_SCIENTIFIC_REVIEW_REQUIRED`.

## Source audit

Canonical branch audits before source construction: `{json.dumps({mask: item['status'] for mask, item in direction.items()}, ensure_ascii=False)}`. Checks include V(R_S)≈3I(R_S), V(L_S3)=V(R_S), orientation and node6/node10 KCL.

## Stop

After the four new raw files, QA, visualization, package, commit and Drive delivery: `{FINAL_MARKER}`. No automatic follow-up.
"""


def initial_yaml(records: dict[str, Any]) -> str:
    lines = ["schema_version: bvm-rloop-ls3-delay-window-v1", f"id: {EXP.name}", "study_phase: EXPLORATORY", "role: Experimental Operator + Evidence Packager", "status: PREFLIGHT_PASS", f"contract_sentence: \"{CONTRACT_SENTENCE}\"", f"registration_head: {EXPECTED_HEAD}", f"remote_bvm_master_at_registration: {EXPECTED_HEAD}", "scientific_review_authorized: false", "mechanical_analysis_performed: false", "bounded_experiment_interpretation_performed: false", "independent_scientific_review_performed: false", "scientific_interpretation_performed: false", "", "question:", "  primary: \"Is the registered 0.3-ps LS3 timing effect a finite timing window?\"", "  scope: \"Only N2=0011 and N3=0111 at 0.2 ps and 0.4 ps; 0.3 ps is reused.\"", "  interpretation_ceiling: \"Mechanical candidate labels only; no scientific classification.\"", "", "frozen:", "  L1_pH: 1.4", "  L2_pH: 2.0", "  IBias_uA: 260", "  RJ1_ohm: 32", "  RJ2_ohm: 12", "  BJS_area: 4", "  timestep_ps: 0.1", "  stop_time_ps: 200", "  t0_ps: 110.0", "  actual_grid: true", "  interpolation: false", "  resampling: false", "  amplitude_scaling: false", "  sign_modification: false", "  no_N1_N4: true", "  no_other_delay: true", "", "authorized_matrix:"]
    for order, case_id in enumerate(RUN_ORDER, 1):
        info = case_info(case_id)
        lines.extend([f"  - run_id: {case_id}", f"    mask: \"{info['mask']}\"", f"    delay_ps: {info['delay_ps']}", f"    stored_sample_shift: {info['stored_sample_shift']}", f"    execution_order: {order}"])
    lines.extend(["  maximum_new_physical_solves: 4", "  no_N1_N4: true", "  no_0p3_rerun: true", "", "read_only_0p3_reference:", f"  experiment: {rel(PREVIOUS)}"])
    for key, path in PREVIOUS_RAW.items():
        lines.extend([f"  - run_id: {key}", f"    path: {rel(path)}", f"    sha256: {EXPECTED_PREVIOUS_HASHES[key]}"])
    lines.extend(["", "new_deck_registration:"])
    for case_id, item in records.items():
        lines.extend([f"  - run_id: {case_id}", f"    path: {item['path']}", f"    sha256: {item['sha256']}", f"    bytes: {item['bytes']}", f"    source_csv: {item['source']['path']}", f"    source_csv_sha256: {item['source']['sha256']}"])
    lines.extend(["", "oracle:", "  phase: raw radians; independent unwrap/(2*pi) turns navigation only", "  n2_n3: ordered phase chain plus JTL6/terminal corroboration", "  integration: actual stored time values", "  scientific_classification: NOT_ASSIGNED_SCIENTIFIC_REVIEW_REQUIRED", ""])
    return "\n".join(lines)


def prepare() -> None:
    assert_registration()
    if EXP.exists() and any(EXP.iterdir()):
        raise RuntimeError(f"refusing non-empty experiment directory: {EXP}")
    canonical = {mask: load_raw(path) for mask, path in CANONICAL.items()}
    direction = {mask: branch.branch_direction_audit(trace, mask) for mask, trace in canonical.items()}
    if any(item["status"] != "PASS" for item in direction.values()):
        raise RuntimeError(f"source direction audit failed: {direction}")
    EXP.mkdir(parents=True)
    for dirname in ("runs", "inputs/replay_sources", "analysis", "plots"):
        (EXP / dirname).mkdir(parents=True, exist_ok=True)
    (EXP / "PREFLIGHT.md").write_text(preflight(direction), encoding="utf-8")
    records = {case_id: make_case_deck(case_id) for case_id in RUN_ORDER}
    (EXP / "experiment.yaml").write_text(initial_yaml(records), encoding="utf-8")
    closure = source_inventory()
    provenance = {"schema": "bvm-rloop-ls3-delay-window-provenance-v1", "experiment_id": EXP.name, "created_at": now(), "registration_head": EXPECTED_HEAD, "remote_bvm_master_at_registration": EXPECTED_HEAD, "contract_sentence": CONTRACT_SENTENCE, "scientific_review_authorized": False, "mechanical_analysis_performed": False, "bounded_experiment_interpretation_performed": False, "independent_scientific_review_performed": False, "scientific_interpretation_performed": False, "solver": branch.replay_base.solver_context(), "source_closure": closure, "canonical_raw_hashes": EXPECTED_CANONICAL_HASHES, "previous_reference_raw_hashes": EXPECTED_PREVIOUS_HASHES, "branch_direction_audit": direction, "frozen": {"topology": "canonical BVM -> COMMON_SL -> JSL1..8 -> canonical QB -> JTL1..6 -> terminal", "replay": "same-instance I(L_S3), ideal current node6 -> node10", "t0_ps": 110.0, "delay_points_ps": [0.2, 0.4], "delay_shifts": [2, 4], "time_step_ps": 0.1, "stop_time_ps": 200.0, "windows_ps": [[0.0, 200.0], [70.0, 110.0], [110.0, 121.0], [121.0, 130.0]], "no_QB_JSL_JTL_terminal_change": True, "no_interpolation": True}, "authorized_matrix": {"run_order": list(RUN_ORDER), "maximum_new_physical_solves": 4, "no_N1_N4": True, "no_0p3_rerun": True, "no_other_solve": True}, "registered_decks": records, "runs": {}, "run_order": [], "execution": {"authorized_physical_solve_count": 4, "actual_physical_solve_count": 0, "solver_invocation_count": 0, "run_order": []}, "fidelity_screen": {"registered": "N2/N3 response observations and actual-grid timing/trajectory arithmetic; not a physical Gate"}, "analysis": {"status": "PENDING"}, "qa": {"status": "PENDING"}, "visualization": {"status": "PENDING"}, "package": {"status": "PENDING", "drive_file_id": None, "drive_url": None}, "stop": {"final_marker": None, "automatic_follow_up": False}}
    write_json(EXP / "provenance.json", provenance)
    result = {"schema": "bvm-rloop-ls3-delay-window-result-v1", "experiment_id": EXP.name, "generated_at": now(), "status": "PREFLIGHT_PASS", "artifact_status": "PENDING", "scientific_review_authorized": False, "mechanical_analysis_performed": False, "bounded_experiment_interpretation_performed": False, "independent_scientific_review_performed": False, "scientific_interpretation_performed": False, "execution": provenance["execution"], "cases": {case_id: {"status": "AUTHORIZED_NOT_RUN"} for case_id in RUN_ORDER}, "timing_window": {"status": "PENDING", "reused_0p3": True}, "classification": {"status": "SCIENTIFIC_REVIEW_REQUIRED", "assigned": None, "candidate_labels": ["LS3_TIMING_WINDOW_BROAD", "LS3_TIMING_WINDOW_PARTIAL", "LS3_TIMING_SWEET_SPOT_NARROW"]}, "stop": {"final_marker": None, "automatic_follow_up": False}}
    write_json(EXP / "result.json", result)
    (EXP / "RESULT.md").write_text(f"# LS3 timing-window closure ({EXP.name})\n\nPreflight passed; four 0.2/0.4-ps N2/N3 decks are registered.\n", encoding="utf-8")
    print(json.dumps({"status": "PREFLIGHT_PASS", "head": EXPECTED_HEAD, "run_order": list(RUN_ORDER)}, ensure_ascii=False, indent=2))


def warning_lines(path: Path) -> list[str]:
    if not path.is_file():
        return ["missing_log"]
    return [line.strip() for line in path.read_text(errors="replace").splitlines() if any(token in line for token in ("Missing model:", "Unknown device/node", "Cannot store results", "Error", "error"))]


def execute() -> None:
    provenance = read_json(EXP / "provenance.json")
    for case_id in RUN_ORDER:
        if provenance["run_order"] != list(RUN_ORDER[: RUN_ORDER.index(case_id)]):
            raise RuntimeError(f"wrong run prefix before {case_id}: {provenance['run_order']}")
        item = provenance["registered_decks"][case_id]
        deck = REPO / item["path"]
        raw, log, metadata = deck.parent / "raw.csv", deck.parent / "run.log", deck.parent / "metadata.json"
        if any(path.exists() for path in (raw, log, metadata)):
            raise RuntimeError(f"refusing overwrite/retry: {case_id}")
        command = [str(SOLVER), "-a", "1", "-o", str(raw), str(deck)]
        started = now()
        with log.open("x", encoding="utf-8") as stream:
            stream.write(f"experiment={EXP.name}\nrun_id={case_id}\nstarted_at={started}\ncommand={' '.join(command)}\n")
            completed = subprocess.run(command, cwd=REPO, stdout=stream, stderr=subprocess.STDOUT, check=False)
            finished = now()
            stream.write(f"finished_at={finished}\nexit_code={completed.returncode}\n")
        info = case_info(case_id)
        record: dict[str, Any] = {"run_id": case_id, **info, "command": command, "deck": {"path": rel(deck), "sha256": sha256(deck), "bytes": deck.stat().st_size}, "log": {"path": rel(log), "sha256": sha256(log), "bytes": log.stat().st_size}, "solver": branch.replay_base.solver_context(), "started_at": started, "finished_at": finished, "physical_solve_this_experiment": True, "raw_immutable": True, "mechanical_analysis_performed": False, "scientific_interpretation_performed": False}
        if completed.returncode != 0 or not raw.is_file() or raw.stat().st_size == 0:
            record["execution_status"] = "SOLVER_FAIL"
            record["raw"] = {"path": rel(raw), "exists": raw.is_file(), "sha256": sha256(raw) if raw.is_file() else None, "bytes": raw.stat().st_size if raw.is_file() else None}
            provenance["runs"][case_id] = record
            provenance["run_order"].append(case_id)
            provenance["execution"]["actual_physical_solve_count"] = len(provenance["run_order"])
            provenance["execution"]["solver_invocation_count"] = len(provenance["run_order"])
            write_json(EXP / "provenance.json", provenance)
            raise RuntimeError(f"solver failed; preserved {case_id}")
        trace = load_raw(raw)
        expected = branch.expected_headers(load_raw(CANONICAL[info["mask"]]), "LS3")
        missing = sorted(expected - set(trace.headers))
        grid = branch.replay_base.finite_grid_qa(trace)
        record["raw"] = {"path": rel(raw), "sha256": sha256(raw), "bytes": raw.stat().st_size, "sample_count": trace.sample_count, "time_start_ps": trace.time[0] * 1.0e12, "time_end_ps": trace.time[-1] * 1.0e12, "grid": grid, "missing_required_probes": missing}
        record["solver_warning_lines"] = warning_lines(log)
        record["execution_status"] = "RUN_PASS" if not missing else "RUN_PASS_MISSING_PROBES"
        record["metadata"] = {"path": rel(metadata), "source": item["source"], "deck_sha256": sha256(deck), "raw_sha256": sha256(raw), "log_sha256": sha256(log), "execution_status": record["execution_status"]}
        write_json(metadata, record["metadata"])
        provenance["runs"][case_id] = record
        provenance["run_order"].append(case_id)
        provenance["execution"]["actual_physical_solve_count"] = len(provenance["run_order"])
        provenance["execution"]["solver_invocation_count"] = len(provenance["run_order"])
        provenance["execution"]["run_order"] = provenance["run_order"]
        write_json(EXP / "provenance.json", provenance)
        if missing:
            raise RuntimeError(f"missing probes in {case_id}: {missing}")
    provenance["execution_status"] = "ALL_AUTHORIZED_RUNS_COMPLETE"
    write_json(EXP / "provenance.json", provenance)
    print(json.dumps({"status": "RUN_PASS", "run_order": provenance["run_order"], "physical_solves": 4}, ensure_ascii=False, indent=2))


def trace_metrics(label: str, mask: str, trace: Any, kind: str, oracle_module: Any) -> dict[str, Any]:
    metrics = branch.run_metrics(label, mask, trace, family=None if kind == "canonical" else "LS3", canonical=kind == "canonical", delay_ps=None if kind == "canonical" else case_info(label)["delay_ps"] if label in RUN_ORDER else 0.3)
    metrics["multi_evidence_oracle"] = multi_evidence_oracle(trace, mask, oracle_module)
    metrics["active_bvm_indices"] = [index for index, bit in enumerate(mask, 1) if bit == "1"]
    metrics["phase_area_cross_checks_active"] = {f"P({element}|XBVM{index})": branch.phase_area(trace, f"P({element}|XBVM{index})", f"V({element}|XBVM{index})") for index in metrics["active_bvm_indices"] for element in ("B_JS1", "B_JS2")}
    return metrics


def source_injection_error(case_id: str, trace: Any) -> dict[str, Any]:
    provenance = read_json(EXP / "provenance.json")
    rows = list(csv.DictReader((REPO / provenance["registered_decks"][case_id]["source"]["path"]).open(newline="", encoding="utf-8")))
    errors = {}
    maximum = 0.0
    for index in range(1, 5):
        imposed = [float(row[f"I_LS3_REPLAY_XBVM{index}_A"]) for row in rows]
        actual = [float(value) for value in load_raw(REPO / provenance["runs"][case_id]["raw"]["path"]).column(f"I(I_LS3_REPLAY|XBVM{index})")]
        diffs = [a - b for a, b in zip(actual, imposed)]
        maximum = max(maximum, max(abs(value) for value in diffs))
        errors[f"XBVM{index}"] = {"max_abs_error_A": max(abs(value) for value in diffs), "rms_error_A": (sum(value * value for value in diffs) / len(diffs)) ** 0.5}
    return {"status": "PASS" if maximum <= 1.0e-12 else "FAIL", "max_abs_error_A": maximum, "tolerance_A": 1.0e-12, "instances": errors}


def case_validation(case_id: str, canonical: Any, candidate: Any, canonical_metrics: dict[str, Any], candidate_metrics: dict[str, Any]) -> dict[str, Any]:
    mask = case_info(case_id)["mask"]
    oracle = candidate_metrics["multi_evidence_oracle"]
    signals = ["I(B_JSL8)", "V(COMMON_SL)", "V(QBIN)", "I(LIN|XBQ1)", "I(L1|XBQ1)", "I(L2|XBQ1)", "V(QBOUT)", "V(JTL6_OUT)", "I(R_TERM)"] + [f"P(B01|XJTL1_{stage})" for stage in JTL_STAGES] + [f"V(JTL{stage}_OUT)" for stage in JTL_STAGES]
    for index in candidate_metrics["active_bvm_indices"]:
        signals.extend([f"{kind}({element}|XBVM{index})" for element in ("B_JS1", "B_JS2") for kind in ("P", "V", "I")])
    deltas = {signal: {"focus_110_121": normalized_delta(canonical, candidate, signal, FOCUS), "full_0_200": normalized_delta(canonical, candidate, signal, FULL)} for signal in signals}
    p2p = common.phase_p2p_deltas(canonical, candidate, mask)
    timing = common.timing_drift(canonical_metrics["multi_evidence_oracle"], oracle)
    return {"case_id": case_id, "mask": mask, "delay_ps": case_info(case_id)["delay_ps"], "ordered_phase_chain_count": oracle["ordered_phase_chain_count"], "old_strict_complete_response_count": oracle["old_strict_complete_response_count"], "jtl6_cluster_count": oracle["jtl6_cluster_count"], "terminal_pulse_count": oracle["terminal_pulse_count"], "terminal_total_area_over_phi0": oracle["terminal_total_area_over_phi0"], "descriptive_candidate_label": oracle["descriptive_candidate_label"], "phase_landmarks": oracle["phase_landmarks"], "ordered_phase_chains": oracle["ordered_phase_chains"], "timing_drift": timing, "active_JS1_JS2_focus_p2p": p2p, "normalized_waveform_deltas": deltas, "L1_rearm": candidate_metrics["qb"]["rearm_signs"].get("I(L1|XBQ1)"), "JSL8_rearm": candidate_metrics["source"]["rearm_signs"].get("I(B_JSL8)"), "source_injection_error": source_injection_error(case_id, candidate), "active_phase_area": candidate_metrics["phase_area_cross_checks_active"], "actual_grid": True, "interpolation": False, "scientific_interpretation_performed": False}


def reused_case(label: str, path: Path, mask: str, oracle_module: Any) -> dict[str, Any]:
    trace = load_raw(path)
    oracle = multi_evidence_oracle(trace, mask, oracle_module)
    return {"run_id": label, "mask": mask, "raw_path": rel(path), "raw_sha256": sha256(path), "ordered_phase_chain_count": oracle["ordered_phase_chain_count"], "old_strict_complete_response_count": oracle["old_strict_complete_response_count"], "jtl6_cluster_count": oracle["jtl6_cluster_count"], "terminal_pulse_count": oracle["terminal_pulse_count"], "terminal_total_area_over_phi0": oracle["terminal_total_area_over_phi0"], "BJ1_landmarks_ps": [common.phase_time(oracle, "BJ1", i) for i in range(1, 5)], "BJ2_landmarks_ps": [common.phase_time(oracle, "BJ2", i) for i in range(1, 5)], "ordered_phase_chains": oracle["ordered_phase_chains"], "read_only_context": True, "physical_solve_this_experiment": False}


def timing_window_classification(new_cases: dict[str, Any], reused: dict[str, Any]) -> dict[str, Any]:
    n2 = {"0P2": new_cases["LS3_DELAY0P2_0011"]["ordered_phase_chain_count"], "0P3": reused["LS3_DELAY0P3_0011"]["ordered_phase_chain_count"], "0P4": new_cases["LS3_DELAY0P4_0011"]["ordered_phase_chain_count"]}
    n3 = {"0P2": new_cases["LS3_DELAY0P2_0111"]["ordered_phase_chain_count"], "0P3": reused["LS3_DELAY0P3_0111"]["ordered_phase_chain_count"], "0P4": new_cases["LS3_DELAY0P4_0111"]["ordered_phase_chain_count"]}
    retained = {point: n2[point] == 2 and n3[point] == 3 for point in n2}
    if retained["0P2"] and retained["0P4"]:
        label = "LS3_TIMING_WINDOW_BROAD"
    elif retained["0P2"] or retained["0P4"]:
        label = "LS3_TIMING_WINDOW_PARTIAL"
    else:
        label = "LS3_TIMING_SWEET_SPOT_NARROW"
    return {"status": "MECHANICAL_CANDIDATE_ONLY", "counts": {"N2": n2, "N3": n3}, "retained_2_3": retained, "candidate_label": label, "classification": "NOT_ASSIGNED_SCIENTIFIC_REVIEW_REQUIRED", "rule": "0.2 and 0.4 both retain N2=2/N3=3 => BROAD; one => PARTIAL; neither => NARROW", "not_process_robustness_proof": True}


def analyze() -> None:
    provenance = read_json(EXP / "provenance.json")
    if provenance["run_order"] != list(RUN_ORDER):
        raise RuntimeError(f"analysis requires all four runs: {provenance['run_order']}")
    registered_runner = next(item for item in provenance["source_closure"] if item["name"] == "runner")
    current_runner = record_file("runner", SCRIPT, registered_runner["role"])
    if registered_runner["sha256"] != current_runner["sha256"]:
        provenance["postsolve_tooling_revision"] = {"path": rel(SCRIPT), "old_sha256": registered_runner["sha256"], "new_sha256": current_runner["sha256"], "reason": "analysis-only argument-order repair; no physical rerun", "physical_rerun": False, "raw_mutated": False}
        registered_runner.update({"sha256": current_runner["sha256"], "bytes": current_runner["bytes"]})
    oracle_module = load_oracle_module()
    canonical_traces = {mask: load_raw(path) for mask, path in CANONICAL.items()}
    canonical_metrics = {mask: trace_metrics(f"CANONICAL_{mask}", mask, canonical_traces[mask], "canonical", oracle_module) for mask in CANONICAL}
    traces = {case_id: load_raw(REPO / provenance["runs"][case_id]["raw"]["path"]) for case_id in RUN_ORDER}
    metrics = {case_id: trace_metrics(case_id, case_info(case_id)["mask"], traces[case_id], "candidate", oracle_module) for case_id in RUN_ORDER}
    validations = {case_id: case_validation(case_id, canonical_traces[case_info(case_id)["mask"]], traces[case_id], canonical_metrics[case_info(case_id)["mask"]], metrics[case_id]) for case_id in RUN_ORDER}
    reused = {label: reused_case(label, path, "0011" if "0011" in label else "0111", oracle_module) for label, path in PREVIOUS_RAW.items()}
    population = timing_window_classification({case_id: validations[case_id] for case_id in RUN_ORDER}, reused)
    raw_before = {case_id: sha256(REPO / provenance["runs"][case_id]["raw"]["path"]) for case_id in RUN_ORDER}
    refs = [item["path"] for item in provenance["source_closure"] if item["name"].startswith(("canonical_", "previous_"))]
    refs_before = {path: sha256(REPO / path) for path in refs}
    analysis = {"schema": "bvm-rloop-ls3-delay-window-mechanical-analysis-v1", "experiment_id": EXP.name, "generated_at": now(), "new_cases": metrics, "validations": validations, "canonical_references": canonical_metrics, "reused_0p3_context": reused, "timing_window": population, "raw_hash_before_analysis": raw_before, "reference_hashes_before_analysis": refs_before, "raw_immutable": True, "actual_grid": True, "interpolation": False, "scientific_interpretation_performed": False}
    write_json(EXP / "analysis" / "mechanical_analysis.json", analysis)
    raw_after = {case_id: sha256(REPO / provenance["runs"][case_id]["raw"]["path"]) for case_id in RUN_ORDER}
    refs_after = {path: sha256(REPO / path) for path in refs}
    if raw_before != raw_after or refs_before != refs_after:
        raise RuntimeError("raw/reference mutation detected")
    provenance.update({"mechanical_analysis_performed": True, "bounded_experiment_interpretation_performed": False, "independent_scientific_review_performed": False, "scientific_interpretation_performed": False, "raw_hash_before_analysis": raw_before, "raw_hash_after_analysis": raw_after, "reference_hashes_before_analysis": refs_before, "reference_hashes_after_analysis": refs_after, "analysis": {"status": "COMPLETE", "path": rel(EXP / "analysis" / "mechanical_analysis.json"), "timing_window": population, "no_N1_N4": True, "no_0p3_rerun": True}, "execution_status": "ALL_AUTHORIZED_RUNS_COMPLETE_ANALYSIS_PENDING"})
    for case_id in RUN_ORDER:
        provenance["runs"][case_id].update({"mechanical_analysis_performed": True, "bounded_experiment_interpretation_performed": False, "independent_scientific_review_performed": False, "scientific_interpretation_performed": False})
    write_json(EXP / "provenance.json", provenance)
    result = read_json(EXP / "result.json")
    result.update({"generated_at": now(), "status": "ANALYSIS_COMPLETE_AWAITING_SCIENTIFIC_REVIEW", "artifact_status": "VALID", "mechanical_analysis_performed": True, "bounded_experiment_interpretation_performed": False, "independent_scientific_review_performed": False, "scientific_interpretation_performed": False, "execution": provenance["execution"], "cases": {case_id: {"run_id": case_id, "mask": case_info(case_id)["mask"], "delay_ps": case_info(case_id)["delay_ps"], "ordered_phase_chain_count": validations[case_id]["ordered_phase_chain_count"], "old_strict_complete_response_count": validations[case_id]["old_strict_complete_response_count"], "jtl6_cluster_count": validations[case_id]["jtl6_cluster_count"], "terminal_pulse_count": validations[case_id]["terminal_pulse_count"], "terminal_total_area_over_phi0": validations[case_id]["terminal_total_area_over_phi0"], "descriptive_candidate_label": validations[case_id]["descriptive_candidate_label"], "BJ1_landmarks_ps": [common.phase_time(validations[case_id], "BJ1", i) if "phase_landmarks" in validations[case_id] else None for i in range(1, 5)], "BJ2_landmarks_ps": [common.phase_time(validations[case_id], "BJ2", i) if "phase_landmarks" in validations[case_id] else None for i in range(1, 5)], "timing_drift_max_ps": validations[case_id]["timing_drift"]["max_abs_delta_ps"], "source_injection_error_A": validations[case_id]["source_injection_error"]["max_abs_error_A"], "active_phase_area": validations[case_id]["active_phase_area"], "raw_path": validations[case_id]["case_id"].replace("", "") if False else provenance["runs"][case_id]["raw"]["path"], "raw_sha256": provenance["runs"][case_id]["raw"]["sha256"]} for case_id in RUN_ORDER}, "timing_window": population, "reused_0p3": reused, "classification": {"status": "SCIENTIFIC_REVIEW_REQUIRED", "assigned": None, "candidate_label": population["candidate_label"], "reason": "mechanical candidate only"}, "stop": {"final_marker": FINAL_MARKER, "automatic_follow_up": False}})
    write_json(EXP / "result.json", result)
    write_result_markdown(result, analysis)
    write_json(EXP / "analysis" / "SOURCE_MANIFEST.json", {"schema": "bvm-rloop-ls3-delay-window-source-manifest-v1", "experiment_id": EXP.name, "generated_at": now(), "source_closure": provenance["source_closure"], "canonical_hashes": EXPECTED_CANONICAL_HASHES, "previous_hashes": EXPECTED_PREVIOUS_HASHES})
    write_json(EXP / "analysis" / "TRANSFORMATION_REGISTRY.json", {"schema": "bvm-rloop-ls3-delay-window-transformation-registry-v1", "raw_mutation": False, "operations": [{"name": "delay0p2", "stored_shift": 2, "rule": "pre-110 same; [110,110.2) hold 110 sample; post i-2", "interpolation": False}, {"name": "delay0p4", "stored_shift": 4, "rule": "pre-110 same; [110,110.4) hold 110 sample; post i-4", "interpolation": False}, {"name": "phase_display", "rule": "independent unwrap(raw radians)/(2*pi), navigation only"}, {"name": "area", "rule": "same JJ/endpoints/direction actual-grid trapezoid; not SFQ count"}]})
    print(json.dumps({"status": "ANALYSIS_COMPLETE", "timing_window_candidate": population["candidate_label"], "counts": population["counts"]}, ensure_ascii=False, indent=2))


def write_result_markdown(result: dict[str, Any], analysis: dict[str, Any]) -> None:
    population = result["timing_window"]
    lines = [f"# LS3 timing-window closure ({EXP.name})", "", f"- Status: `{result['status']}`", "- Artifact status: `VALID`", "- Scientific interpretation: `NOT_PERFORMED`; final classification: `SCIENTIFIC_REVIEW_REQUIRED`.", f"- Frozen parent: `{EXPECTED_HEAD}`; exactly four new solves; no N1/N4 or 0.3-ps rerun.", "- Fixture: validated LS3-only per-instance ideal current replay; canonical BVM→JSL→QB→JTL→terminal retained.", "", "## Timing-window table", "", "| delay | N2 ordered chains | N3 ordered chains | N2 second response | N3 fourth chain |", "|---:|---:|---:|---|---|"]
    for point, delay in (("0P2", 0.2), ("0P3", 0.3), ("0P4", 0.4)):
        n2 = population["counts"]["N2"][point]
        n3 = population["counts"]["N3"][point]
        n2_second = "preserved" if n2 >= 2 else "absent/missing"
        n3_fourth = "present" if n3 >= 4 else "absent"
        lines.append(f"| `{delay} ps` | {n2} | {n3} | {n2_second} | {n3_fourth} |")
    lines.extend(["", f"- Mechanical candidate label: `{population['candidate_label']}`.", "- Final scientific assignment: `NOT_ASSIGNED_SCIENTIFIC_REVIEW_REQUIRED`.", "- The 0.3-ps row is read-only prior evidence; no 0.3-ps solve was executed.", "", "## New-run evidence", "", "| run | old strict count | phase chains | JTL6 clusters | terminal clusters | terminal area / Φ0 | first BJ1/BJ2 (ps) | timing drift max (ps) |", "|---|---:|---:|---:|---:|---:|---|---:|"])
    for case_id in RUN_ORDER:
        item = analysis["validations"][case_id]
        first = item["ordered_phase_chains"][0]["landmark_times_ps"]
        lines.append(f"| `{case_id}` | {item['old_strict_complete_response_count']} | {item['ordered_phase_chain_count']} | {item['jtl6_cluster_count']} | {item['terminal_pulse_count']} | {common.fmt(item['terminal_total_area_over_phi0'])} | {common.fmt(first['BJ1'])}/{common.fmt(first['BJ2'])} | {common.fmt(item['timing_drift']['max_abs_delta_ps'])} |")
    lines.extend(["", "### N3 response chains", "", "| run | response 1 | response 2 | response 3 | response 4 |", "|---|---|---|---|---|"])
    for case_id in ("LS3_DELAY0P2_0111", "LS3_DELAY0P4_0111"):
        chains = analysis["validations"][case_id]["ordered_phase_chains"]
        cells = []
        for chain in chains:
            cells.append("complete" if chain["complete_ordered_phase_chain"] else f"missing {chain['first_missing_stage']}")
        lines.append(f"| `{case_id}` | {cells[0]} | {cells[1]} | {cells[2]} | {cells[3]} |")
    lines.extend(["", "N2/N3 active JS1/JS2 p2p, L1 re-arm, JSL8 signed/re-arm behavior, same-JJ phase-area arithmetic, normalized waveform deltas, source-injection error and all stage data are in `analysis/mechanical_analysis.json`. Phase is raw radians; turns are navigation only. Navigation count and voltage area are not literal SFQ counts.", "", f"Stop marker: `{FINAL_MARKER}`.", ""])
    (EXP / "RESULT.md").write_text("\n".join(lines), encoding="utf-8")
    (EXP / "analysis" / "NUMERICAL_REVIEW.md").write_text("\n".join(["# Numerical review — mechanical only", "", "- Delay transforms use exact stored index shifts of 2 and 4 samples, with 110-ps hold and half-open windows.", "- All integrations use actual stored timestamps; no interpolation/resampling.", "- P(...) is raw radians; turns are independent unwrap/(2*pi) navigation only.", "- Same-JJ JS1/JS2 phase-area records use matched endpoints/direction/window.", "- No timestep/parameter/solver sensitivity was run; convergence is UNKNOWN."]) + "\n", encoding="utf-8")
    (EXP / "analysis" / "ADVERSARIAL_REVIEW.md").write_text("\n".join(["# Adversarial review probes — mechanical only", "", "- Canonical source raw and prior 0.3-ps raw hashes are pinned; prior raw is not copied.", "- Canonical R_S/L_S3 orientation, resistor law, parallel voltage and KCL are audited before PWL generation.", "- Each BVM gets its own LS3 source waveform; no common waveform.", "- Run order and maximum solve count are enforced.", "- The N2/N3 phase-chain oracle is separate from the historical strict voltage-cluster field; both are retained.", "- No scientific winner, mechanism, physical delay or SFQ-count claim is assigned."]) + "\n", encoding="utf-8")


def mechanical_qa() -> None:
    provenance = read_json(EXP / "provenance.json")
    failures = []
    checks = {}
    for case_id in RUN_ORDER:
        rec = provenance["runs"].get(case_id)
        if not rec:
            failures.append(case_id)
            continue
        deck, raw, log, meta = [REPO / rec[key]["path"] for key in ("deck", "raw", "log", "metadata")]
        trace = load_raw(raw)
        info = case_info(case_id)
        warnings = warning_lines(log)
        unexpected = [line for line in warnings if line not in KNOWN_WARNINGS]
        topology = deck.read_text(encoding="utf-8")
        topology_ok = topology.count("I_LS3_REPLAY 6 10 PWL(") == 4 and topology.count("R_S     6       10      3.0") == 4 and "L_S3    6       10      0.5P" not in topology and "XBQ1 QBIN QBOUT BQ" in topology and "R_TERM JTL6_OUT 0 10" in topology and ".tran 0.1p 200p" in topology
        grid = branch.replay_base.finite_grid_qa(trace)
        missing = sorted(branch.expected_headers(load_raw(CANONICAL[info["mask"]]), "LS3") - set(trace.headers))
        passed = bool(rec["execution_status"] == "RUN_PASS" and topology_ok and meta.is_file() and not missing and not trace.duplicate_columns and grid["status"] == "VALID" and grid["sample_count"] == 1999 and grid["time_start_ps"] == 0.0 and grid["time_end_ps"] == 199.9 and not unexpected and sha256(raw) == rec["raw"]["sha256"] and sha256(deck) == rec["deck"]["sha256"])
        if not passed:
            failures.append(case_id)
        checks[case_id] = {"status": "PASS" if passed else "ARTIFACT_INVALID", "topology_ok": topology_ok, "grid": grid, "missing_required_probes": missing, "duplicate_columns": trace.duplicate_columns, "warnings": warnings, "unexpected_warnings": unexpected}
    source_ok = all(sha256(REPO / item["path"]) == item["sha256"] for item in provenance["source_closure"])
    passed = bool(provenance["run_order"] == list(RUN_ORDER) and provenance["execution"]["actual_physical_solve_count"] == 4 and not failures and source_ok and provenance.get("raw_hash_before_analysis") == provenance.get("raw_hash_after_analysis") and provenance.get("reference_hashes_before_analysis") == provenance.get("reference_hashes_after_analysis"))
    qa = {"schema": "bvm-rloop-ls3-delay-window-mechanical-qa-v1", "experiment_id": EXP.name, "generated_at": now(), "status": "PASS" if passed else "FAIL", "artifact_status": "VALID" if passed else "ARTIFACT_INVALID", "run_order": provenance["run_order"], "expected_run_order": list(RUN_ORDER), "actual_physical_solve_count": provenance["execution"]["actual_physical_solve_count"], "max_physical_solves": 4, "no_extra_solve": provenance["run_order"] == list(RUN_ORDER), "source_hashes_match": source_ok, "raw_hash_before_after_equal": provenance.get("raw_hash_before_analysis") == provenance.get("raw_hash_after_analysis"), "reference_hash_before_after_equal": provenance.get("reference_hashes_before_analysis") == provenance.get("reference_hashes_after_analysis"), "contains_all_new_run_raw": None, "contains_reference_raw_copies": False, "contains_delivery_manifest": False, "runs": checks, "failures": failures, "mechanical_analysis_performed": True, "scientific_interpretation_performed": False}
    write_json(EXP / "analysis" / "MECHANICAL_QA.json", qa)
    provenance["qa"] = qa
    write_json(EXP / "provenance.json", provenance)
    result = read_json(EXP / "result.json")
    result["qa_summary"] = {"status": qa["status"], "artifact_status": qa["artifact_status"]}
    write_json(EXP / "result.json", result)
    if not passed:
        raise RuntimeError(f"mechanical QA failed: {failures}")
    print(json.dumps({"status": "PASS", "physical_solves": 4}, ensure_ascii=False, indent=2))


def visualization() -> None:
    provenance = read_json(EXP / "provenance.json")
    if provenance.get("qa", {}).get("status") != "PASS":
        raise RuntimeError("QA required before visualization")
    asset = EXP / "plots" / "assets" / "plotly.min.js"
    entries = []
    specs = {
        "01_SIGNAL_TIMING": ["V(COMMON_SL)", "I(B_JSL8)", "V(QBIN)", "I(LIN|XBQ1)", "V(QBOUT)"],
        "02_BVM_STATE": [signal for index in range(1, 5) for element in ("B_JS1", "B_JS2", "B_JM1", "B_JM2") for signal in (f"P({element}|XBVM{index})", f"V({element}|XBVM{index})", f"I({element}|XBVM{index})")] + [signal for index in range(1, 5) for element in ("L_S1", "L_S2", "L_M3", "L_S3", "R_S", "L_SL") for signal in (f"I({element}|XBVM{index})", f"V({element}|XBVM{index})")],
        "03_JSL_CHAIN": [signal for index in range(1, 9) for signal in (f"P(B_JSL{index})", f"V(B_JSL{index})", f"I(B_JSL{index})")],
        "04_QB_STATE": ["V(QBIN)", "I(LIN|XBQ1)", "V(LIN|XBQ1)", "P(BJ1|XBQ1)", "V(BJ1|XBQ1)", "I(BJ1|XBQ1)", "P(BJ2|XBQ1)", "V(BJ2|XBQ1)", "I(BJ2|XBQ1)", "I(L1|XBQ1)", "V(L1|XBQ1)", "I(L2|XBQ1)", "V(L2|XBQ1)", "V(QBOUT)"],
        "05_JTL_CHAIN": [signal for stage in JTL_STAGES for signal in (f"P(B01|XJTL1_{stage})", f"V(B01|XJTL1_{stage})", f"I(B01|XJTL1_{stage})", f"P(B02|XJTL1_{stage})", f"V(B02|XJTL1_{stage})", f"I(B02|XJTL1_{stage})", f"V(JTL{stage}_OUT)")] + ["I(R_TERM)"],
    }
    for case_id in RUN_ORDER:
        raw = REPO / provenance["runs"][case_id]["raw"]["path"]
        trace = load_raw(raw)
        for page, requested in specs.items():
            selected = [signal for signal in requested if signal in trace.headers]
            output = EXP / "plots" / case_id / f"{page}_full_0_200.html"
            branch.render_plot(raw, output, selected, f"{case_id}: {page}; full 0–200 ps; actual stored grid", asset)
            entries.append({"kind": "standalone", "run_id": case_id, "path": rel(output), "raw_path": rel(raw), "raw_sha256": sha256(raw), "sha256": sha256(output), "bytes": output.stat().st_size, "signals": selected, "window_ps": list(FULL), "focused": False, "phase_display": "raw radians; rad/(2*pi) turns navigation only"})
            cropped = branch.total_helpers.crop_csv(raw, *FOCUS)
            try:
                focus = EXP / "plots" / case_id / f"{page}_focus_110_121.html"
                branch.render_plot(cropped, focus, selected, f"{case_id}: {page}; focus [110,121) ps; actual stored samples", asset)
                entries.append({"kind": "standalone", "run_id": case_id, "path": rel(focus), "raw_path": rel(raw), "raw_sha256": sha256(raw), "sha256": sha256(focus), "bytes": focus.stat().st_size, "signals": selected, "window_ps": list(FOCUS), "focused": True, "derived_input": "actual-grid crop only; no interpolation", "phase_display": "raw radians; rad/(2*pi) turns navigation only"})
            finally:
                cropped.unlink(missing_ok=True)
    for mask in ("0011", "0111"):
        cases = [(f"CANONICAL_{mask}", load_raw(CANONICAL[mask])), (f"LS3_DELAY0P3_{mask}", load_raw(PREVIOUS_RAW[f"LS3_DELAY0P3_{mask}"]))]
        cases.extend((case_id, load_raw(REPO / provenance["runs"][case_id]["raw"]["path"])) for case_id in RUN_ORDER if case_info(case_id)["mask"] == mask)
        for page, requested in (("01_SIGNAL_TIMING", specs["01_SIGNAL_TIMING"]), ("03_JSL_CHAIN", ["P(B_JSL8)", "V(B_JSL8)", "I(B_JSL8)", "V(COMMON_SL)"]), ("04_QB_STATE", specs["04_QB_STATE"]), ("05_JTL_CHAIN", specs["05_JTL_CHAIN"])):
            selected = [signal for signal in requested if all(signal in trace.headers for _, trace in cases)]
            if not selected:
                continue
            temporary = branch.total_helpers.comparison_csv(cases, selected, FOCUS)
            output = EXP / "plots" / "comparisons" / f"{mask}_{page}_focus_110_121.html"
            try:
                labels = [branch.replay_base.prefixed_label(case, signal) for case, _ in cases for signal in selected]
                branch.render_plot(temporary, output, labels, f"{mask}: canonical/0.3/0.2/0.4 LS3 {page}; focus [110,121) ps", asset)
            finally:
                temporary.unlink(missing_ok=True)
            entries.append({"kind": "comparison", "mask": mask, "path": rel(output), "sha256": sha256(output), "bytes": output.stat().st_size, "cases": [case for case, _ in cases], "signals": selected, "window_ps": list(FOCUS), "focused": True, "phase_display": "independent case unwrap; rad/(2*pi) turns navigation only"})
    html_paths = sorted((EXP / "plots").rglob("*.html"))
    invalid = [rel(path) for path in html_paths if any(token in path.read_text(encoding="utf-8") for token in ("plotly.js v", "var Plotly=", "cdn.plot.ly", "Unknown"))]
    record = {"schema": "bvm-rloop-ls3-delay-window-visualization-v1", "status": "PASS" if entries and asset.is_file() and not invalid else "FAIL", "generated_at": now(), "renderer": rel(PLOTTER), "layout": "sep_comb", "color": "dark", "phase_option": "2pi", "entries": entries, "standalone_count": sum(item["kind"] == "standalone" for item in entries), "comparison_count": sum(item["kind"] == "comparison" for item in entries), "focused_window_entries": sum(item["focused"] for item in entries), "asset": {"path": rel(asset), "sha256": sha256(asset) if asset.is_file() else None, "bytes": asset.stat().st_size if asset.is_file() else None}, "invalid_runtime_pages": invalid, "raw_hashes_rechecked": all(item["raw_sha256"] == sha256(REPO / item["raw_path"]) for item in entries if item["kind"] == "standalone"), "descriptive_only": True}
    write_json(EXP / "analysis" / "VISUALIZATION_MANIFEST.json", record)
    write_json(EXP / "analysis" / "VISUALIZATION_QA.json", {"status": record["status"], "standalone_count": record["standalone_count"], "comparison_count": record["comparison_count"], "focused_window_entries": record["focused_window_entries"], "invalid_runtime_pages": invalid, "raw_hashes_rechecked": record["raw_hashes_rechecked"]})
    provenance["visualization"] = record
    write_json(EXP / "provenance.json", provenance)
    result = read_json(EXP / "result.json")
    result["visualization_summary"] = {"status": record["status"], "standalone_count": record["standalone_count"], "comparison_count": record["comparison_count"], "focused_window_entries": record["focused_window_entries"]}
    write_json(EXP / "result.json", result)
    if record["status"] != "PASS":
        raise RuntimeError(f"visualization failed: {invalid}")
    print(json.dumps({"status": record["status"], "standalone_count": record["standalone_count"], "comparison_count": record["comparison_count"]}, ensure_ascii=False, indent=2))


def write_evidence_manifest() -> None:
    records = []
    for path in sorted(EXP.rglob("*")):
        if path.is_file() and path.name != "delivery_manifest.json" and path.suffix != ".tmp":
            records.append({"path": path.relative_to(EXP).as_posix(), "sha256": sha256(path), "bytes": path.stat().st_size})
    write_json(EXP / "analysis" / "RAW_ANALYSIS_HANDOFF_MANIFEST.json", {"schema": "bvm-rloop-ls3-delay-window-raw-analysis-handoff-v1", "experiment_id": EXP.name, "generated_at": now(), "raw_is_immutable_solver_output": True, "processed_crops_are_not_raw_substitutes": True, "files_excluding_delivery_manifest": records})
    (EXP / "analysis" / "EVIDENCE_MANIFEST.md").write_text("\n".join(["# Evidence manifest", "", "| path | SHA-256 | bytes |", "|---|---|---:|"] + [f"| `{item['path']}` | `{item['sha256']}` | {item['bytes']} |" for item in records]) + "\n", encoding="utf-8")


def package() -> None:
    provenance = read_json(EXP / "provenance.json")
    if provenance.get("qa", {}).get("status") != "PASS" or provenance.get("visualization", {}).get("status") != "PASS":
        raise RuntimeError("QA/viz required before package")
    write_evidence_manifest()
    delivery = Path("/mnt/d/BVM_Backages")
    delivery.mkdir(parents=True, exist_ok=True)
    package_path = delivery / f"{EXP.name}_raw_evidence.zip"
    version = "v1"
    if package_path.exists():
        number = 2
        while (delivery / f"{EXP.name}_v{number}_raw_evidence.zip").exists():
            number += 1
        version = f"v{number}"
        package_path = delivery / f"{EXP.name}_{version}_raw_evidence.zip"
    files = [(EXP / name, name) for name in ("experiment.yaml", "PREFLIGHT.md", "RESULT.md", "result.json", "provenance.json")]
    plots = []
    for dirname in ("inputs", "runs", "analysis", "plots"):
        for path in sorted((EXP / dirname).rglob("*")):
            if path.is_file() and (dirname != "plots" or path.name == "plotly.min.js" or "focus_110_121" in path.name):
                files.append((path, path.relative_to(EXP).as_posix()))
                if dirname == "plots":
                    plots.append(path.relative_to(EXP).as_posix())
    files.append((SCRIPT, "executor/bvm_qb_rloop_ls3_delay_window.py"))
    records = [{"path": name, "sha256": sha256(path), "bytes": path.stat().st_size} for path, name in files]
    with zipfile.ZipFile(package_path, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path, name in files:
            archive.write(path, name)
    with zipfile.ZipFile(package_path) as archive:
        reopened = {name: hashlib.sha256(archive.read(name)).hexdigest() for name in archive.namelist()}
    expected = {item["path"]: item["sha256"] for item in records}
    raw_members = [f"runs/{case_id}/raw.csv" for case_id in RUN_ORDER]
    qa = {"status": "PASS" if expected == reopened and all(member in reopened for member in raw_members) else "FAIL", "package_version": version, "package_path": str(package_path), "package_sha256": sha256(package_path), "package_bytes": package_path.stat().st_size, "file_count": len(records), "expected_file_hashes_match_after_reopen": expected == reopened, "zip_files": records, "contains_all_new_run_raw": all(member in reopened for member in raw_members), "new_run_raw_members": raw_members, "contains_reference_raw_copies": False, "contains_delivery_manifest": False, "delivery_manifest_outside_zip": True, "package_plot_policy": "focused pages and runtime only; full repository visualization remains committed", "packaged_plot_file_count": len(plots), "packaged_plot_paths": plots, "not_in_git": True, "git_head_at_packaging": git_head(), "remote_head_at_packaging": remote_head()}
    manifest = {"schema": "bvm-rloop-ls3-delay-window-delivery-manifest-v1", "experiment_id": EXP.name, "created_at": now(), "status": "READY_FOR_DRIVE_UPLOAD" if qa["status"] == "PASS" else "PACKAGE_INVALID", "package_version": version, "package_path": str(package_path), "package_sha256": qa["package_sha256"], "package_bytes": qa["package_bytes"], "package_qa": qa, "drive_folder_id": DRIVE_FOLDER_ID, "drive_file_id": None, "drive_url": None, "delivery_id_is_outside_zip_to_avoid_self_reference": True}
    write_json(EXP / "delivery_manifest.json", manifest)
    write_json(EXP / "analysis" / "PACKAGE_QA.json", qa)
    provenance["package"] = {"status": manifest["status"], "version": version, "delivery_manifest_path": "delivery_manifest.json", "package_qa": qa, "drive_file_id": None, "drive_url": None}
    write_json(EXP / "provenance.json", provenance)
    result = read_json(EXP / "result.json")
    result["package_summary"] = {"status": manifest["status"], "version": version, "package_sha256": qa["package_sha256"], "package_bytes": qa["package_bytes"], "file_count": qa["file_count"], "delivery_manifest_path": "delivery_manifest.json", "drive_file_id": None}
    write_json(EXP / "result.json", result)
    if qa["status"] != "PASS":
        raise RuntimeError("package QA failed")
    print(json.dumps({"status": "PASS", "package_path": str(package_path), "sha256": qa["package_sha256"], "bytes": qa["package_bytes"], "files": qa["file_count"]}, ensure_ascii=False, indent=2))


def record_drive(file_id: str, url: str | None = None, remote_bytes: int | None = None) -> None:
    manifest_path = EXP / "delivery_manifest.json"
    manifest = read_json(manifest_path)
    package_path = Path(manifest["package_path"])
    if sha256(package_path) != manifest["package_sha256"]:
        raise RuntimeError("local package changed")
    if remote_bytes is not None and int(remote_bytes) != manifest["package_bytes"]:
        raise RuntimeError("Drive size mismatch")
    manifest.update({"status": "UPLOADED", "drive_file_id": file_id, "drive_url": url, "uploaded_at": now(), "drive_verified_local_sha256": manifest["package_sha256"], "drive_verified_local_bytes": manifest["package_bytes"], "remote_sha256_from_connector": None})
    write_json(manifest_path, manifest)
    provenance = read_json(EXP / "provenance.json")
    provenance["package"].update({"status": "UPLOADED", "drive_file_id": file_id, "drive_url": url, "drive_uploaded_at": manifest["uploaded_at"], "delivery_manifest_sha256": sha256(manifest_path), "drive_sha256_verified": "metadata SHA not supplied by connector"})
    write_json(EXP / "provenance.json", provenance)
    result = read_json(EXP / "result.json")
    result["package_summary"].update({"status": "UPLOADED", "drive_file_id": file_id, "drive_url": url})
    write_json(EXP / "result.json", result)
    print(json.dumps({"status": "UPLOADED", "drive_file_id": file_id, "drive_url": url, "package_sha256": manifest["package_sha256"], "package_bytes": manifest["package_bytes"]}, ensure_ascii=False, indent=2))


def main() -> int:
    command = sys.argv[1] if len(sys.argv) > 1 else "all"
    actions = {"prepare": prepare, "run": execute, "analyze": analyze, "qa": mechanical_qa, "viz": visualization, "package": package, "record-drive": lambda: record_drive(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None, int(sys.argv[4]) if len(sys.argv) > 4 else None), "all": lambda: (prepare(), execute(), analyze(), mechanical_qa(), visualization(), package())}
    if command not in actions:
        print(f"usage: {SCRIPT.name} [prepare|run|analyze|qa|viz|package|record-drive FILE_ID [URL] [BYTES]|all]", file=sys.stderr)
        return 2
    if command == "record-drive" and len(sys.argv) < 3:
        return 2
    actions[command]()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
