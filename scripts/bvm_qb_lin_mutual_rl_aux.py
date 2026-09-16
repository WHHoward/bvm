#!/usr/bin/env python3
"""Minimal passive mutual-RL auxiliary feasibility experiment.

The auxiliary loop is inserted inside an experimental QB clone so the
canonical galvanic JSL8 -> QBIN -> Lin -> BJs path remains intact.  K=0 is a
registered fixture/no-op gate.  Only if it passes are the three positive K
levels materialized.  This module records mechanical evidence only; labels
are candidates pending scientific review.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import re
import subprocess
import zipfile
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
SCRIPT = Path(__file__).resolve()
import sys
sys.path.insert(0, str(REPO / "scripts"))
import bvm_qb_rloop_ls3_population_validation as common  # noqa: E402

branch = common.branch_helpers
EXP = REPO / "test" / "exploration" / "bvm-qb-lin-mutual-rl-aux-v1-20260916"
REFERENCE_ROOT = REPO / "test" / "exploration" / "bvm-qb-threshold-ordering-boundary-search-v1-20260911" / "references" / "canonical_baseline"
SOURCE_INPUTS = REPO / "test" / "exploration" / "bvm-qb-threshold-ordering-boundary-search-v1-20260911" / "inputs"
POP_ROOT = REPO / "test" / "exploration" / "bvm-population-scaling-rj2p12-l1p14-l2p20-ib260-rj32-bjs400-v1-20260910"
SOLVER = REPO / "build" / "josim-cli"
PLOTTER = REPO / "scripts" / "josim-plot2.py"
ORACLE_PATH = POP_ROOT / "analysis" / "population_oracle.py"
CANONICAL = {mask: REFERENCE_ROOT / mask / "raw.csv" for mask in ("0011", "0111")}
CANONICAL.update({"0001": POP_ROOT / "references" / "reused" / "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_0001" / "raw.csv", "1111": POP_ROOT / "runs" / "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_1111" / "raw.csv"})
CANONICAL_DECK = {mask: REFERENCE_ROOT / mask / "deck.cir" for mask in ("0011", "0111")}
CANONICAL_DECK.update({"0001": POP_ROOT / "references" / "reused" / "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_0001" / "deck.cir", "1111": POP_ROOT / "runs" / "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_1111" / "deck.cir"})
EXPECTED_HEAD = "b904851be588ca88d40cf1700d5fef7ce3d889ed"
EXPECTED_CANONICAL_HASHES = {"0011": "3da7b754c990316ff8e5981692afa958d8056a61020a1912548bf6f2b7e0249c", "0111": "1ca15a938b23d4ed08eb964713f91476256c4caf0677d1bfd3dc43020271ec75", "0001": "7411226d2231dca0e1a3948660a82d7d88112baab8c18349cd83f4f94e6cf1b3", "1111": "0497b2d6822378c5b7491ab00abdfcf00d624ba9dd7e7a1c02046b5d4c3ed48c"}
PINNED_INPUTS = {SOURCE_INPUTS / "jjmit.cir": "19862d1fd1f1f44dfa1523848d7d3b5e2594a6c5da8fdd80144b449e5312a336", SOURCE_INPUTS / "bvm_jm2_connected.cir": "0093a45cc3910448b484d8bd004c6df8c22358bacc8b3ed5e23912dcab805d54", SOURCE_INPUTS / "BQ_parameterized_bjs400_rj2.cir": "43468c49eb56090e586428a8ca26d17d8bbf107fbd9e535bbac7a72ed1200d42", SOURCE_INPUTS / "jtl2.cir": "ffd31f8eda2a86ca0133342be1ce678831b7237a53911eda046d2bff8454855a"}
K_POINTS = {"K000": 0.0, "K010": 0.10, "K020": 0.20, "K030": 0.30}
FIXED_ORDER = ("K000_0011", "K000_0111", "K010_0011", "K010_0111", "K020_0011", "K020_0111", "K030_0011", "K030_0111")
K0_ORDER = FIXED_ORDER[:2]
CONDITIONAL_MASKS = ("0001", "1111")
PHI0 = 2.067833848e-15
FOCUS = (110.0, 121.0)
REARM = (121.0, 130.0)
FULL = (0.0, 200.0)
T0_PS = 110.0
LAUX_PH = 10.0
RAUX_OHM = 20.0
LIN_PH = 1.5
CONTRACT_SENTENCE = "This experiment is governed by docs/EXPERIMENT_CONTRACT.md."
FINAL_MARKER = "EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW"
DRIVE_FOLDER_ID = "1--nlY7Nq5ArVPydJNrnQf-EGmwN-undh"
KNOWN_WARNINGS = {"Unknown device/node IB|XBQ1", "Cannot store results for this device/node."}
JTL_STAGES = tuple(range(1, 7))

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


def now() -> str:
    from datetime import datetime
    return datetime.now().astimezone().isoformat(timespec="seconds")


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
        raise RuntimeError(f"missing source: {path}")
    return {"name": name, "path": rel(path), "sha256": sha256(path), "bytes": path.stat().st_size, "role": role}


def expected_headers(mask: str) -> set[str]:
    headers = set(load_raw(CANONICAL[mask]).headers)
    headers.update({"I(L_AUX|XBQ1)", "V(L_AUX|XBQ1)", "I(R_AUX|XBQ1)", "V(R_AUX|XBQ1)", "V(AUX|XBQ1)"})
    return headers


def case_info(case_id: str) -> dict[str, Any]:
    match = re.fullmatch(r"(K000|K010|K020|K030)_(0001|0011|0111|1111)", case_id)
    if not match:
        raise RuntimeError(f"invalid case id: {case_id}")
    point, mask = match.groups()
    return {"case_id": case_id, "K_point": point, "K_value": K_POINTS[point], "mask": mask, "M_pH": K_POINTS[point] * math.sqrt(LIN_PH * LAUX_PH), "conditional_population_validation": mask in CONDITIONAL_MASKS}


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


def static_k_audit() -> dict[str, Any]:
    fixture = REPO / "test" / "comp" / "mutual.cir"
    text = fixture.read_text(encoding="utf-8")
    syntax_lines = [line.strip() for line in text.splitlines() if line.strip().startswith("K ")]
    if not syntax_lines or not all(re.fullmatch(r"K\s+\S+\s+\S+\s+[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", line) for line in syntax_lines):
        raise RuntimeError("JoSIM K syntax fixture audit failed")
    values = {}
    for point, k in K_POINTS.items():
        m = k * math.sqrt(LIN_PH * LAUX_PH)
        determinant = LIN_PH * LAUX_PH - m * m
        eigen_discriminant = math.sqrt((LIN_PH - LAUX_PH) ** 2 + 4.0 * m * m)
        eigen_min = 0.5 * (LIN_PH + LAUX_PH - eigen_discriminant)
        eigen_max = 0.5 * (LIN_PH + LAUX_PH + eigen_discriminant)
        values[point] = {"K": k, "M_pH": m, "determinant_pH2": determinant, "eigenvalues_pH": [eigen_min, eigen_max], "matrix_positive_definite": eigen_min > 0.0}
    return {"status": "PASS" if all(item["matrix_positive_definite"] for item in values.values()) else "FAIL", "syntax_fixture": rel(fixture), "syntax_examples": syntax_lines, "matrix": values, "K_scope": "K=0,0.1,0.2,0.3 only; no negative polarity sweep"}


def source_inventory() -> list[dict[str, Any]]:
    records = [record_file("runner", SCRIPT, "mutual-RL generator, executor, mechanical analysis, visualization and package builder"), record_file("global_jjmit", SOURCE_INPUTS / "jjmit.cir", "canonical global JJ model"), record_file("canonical_bvm", SOURCE_INPUTS / "bvm_jm2_connected.cir", "canonical BVM include"), record_file("canonical_qb", SOURCE_INPUTS / "BQ_parameterized_bjs400_rj2.cir", "canonical QB source for clone"), record_file("canonical_jtl", SOURCE_INPUTS / "jtl2.cir", "canonical six-stage JTL"), record_file("josim_solver", SOLVER, "recorded solver"), record_file("plotter", PLOTTER, "standard descriptive renderer"), record_file("branch_helper", REPO / "scripts" / "bvm_qb_rloop_branch_timing_decomposition.py", "read-only BVM/R-loop metrics and replay topology helper"), record_file("population_helper", REPO / "scripts" / "bvm_qb_rloop_ls3_population_validation.py", "read-only multi-evidence helper"), record_file("population_oracle", ORACLE_PATH, "read-only historical cluster segmentation oracle"), record_file("mutual_syntax_fixture", REPO / "test" / "comp" / "mutual.cir", "read-only JoSIM K syntax fixture")]
    for mask in ("0011", "0111", "0001", "1111"):
        records.extend([record_file(f"canonical_{mask}_raw", CANONICAL[mask], "read-only canonical population raw"), record_file(f"canonical_{mask}_deck", CANONICAL_DECK[mask], "read-only canonical deck")])
    return records


def clone_qb(k_point: str) -> str:
    source = (SOURCE_INPUTS / "BQ_parameterized_bjs400_rj2.cir").read_text(encoding="utf-8")
    lines = source.splitlines()
    start = next(index for index, line in enumerate(lines) if line.strip().lower() == ".subckt bq in out")
    end = next(index for index in range(start + 1, len(lines)) if lines[index].strip().lower() == ".ends bq")
    name = f"BQ_MUTUAL_{k_point}"
    output = [f"* {name}: canonical BQ clone plus grounded passive mutual-RL auxiliary.", f".subckt {name} IN OUT"]
    inserted = False
    for line in lines[start + 1:end]:
        output.append(line)
        if line.strip().lower().startswith("lin ") and not inserted:
            output.extend(["L_AUX AUX 0 10P", "R_AUX 0 AUX 20", f"K_AUX Lin L_AUX {K_POINTS[k_point]:.17g}"])
            inserted = True
    if not inserted:
        raise RuntimeError("Lin anchor missing in BQ clone")
    output.extend([f".ends {name}", ""])
    return "\n".join(output)


def transform_deck(mask: str, k_point: str, case_id: str, deck_dir: Path) -> str:
    original = CANONICAL_DECK[mask].read_text(encoding="utf-8")
    include_targets = {"jjmit.cir": SOURCE_INPUTS / "jjmit.cir", "bvm_jm2_connected.cir": SOURCE_INPUTS / "bvm_jm2_connected.cir", "BQ_parameterized_bjs400_rj2.cir": SOURCE_INPUTS / "BQ_parameterized_bjs400_rj2.cir", "jtl2.cir": SOURCE_INPUTS / "jtl2.cir"}
    output: list[str] = []
    inserted = False
    bq_replaced = 0
    aux_probe_replaced = 0
    for line in original.splitlines():
        stripped = line.strip()
        if stripped.startswith(".include "):
            basename = Path(stripped.split(None, 1)[1]).name
            if basename == "BQ_parameterized_bjs400_rj2.cir":
                continue
            if basename not in include_targets:
                raise RuntimeError(f"unexpected include {basename} in {case_id}")
            target = include_targets[basename]
            output.append(f".include {Path(os.path.relpath(target, deck_dir)).as_posix()}")
            continue
        if re.fullmatch(r"XBQ1 QBIN QBOUT BQ", stripped):
            if not inserted:
                output.append(clone_qb(k_point))
                inserted = True
            output.append(f"XBQ1 QBIN QBOUT BQ_MUTUAL_{k_point}")
            bq_replaced += 1
            continue
        if stripped.startswith(".print ") and "V(QBIN)" in stripped and "V(QBOUT)" in stripped:
            output.append(stripped + " I(L_AUX|XBQ1) V(L_AUX|XBQ1) I(R_AUX|XBQ1) V(R_AUX|XBQ1) V(AUX|XBQ1)")
            aux_probe_replaced += 1
            continue
        output.append(line)
    if not inserted or bq_replaced != 1 or aux_probe_replaced != 1:
        raise RuntimeError(f"QB transform count failed for {case_id}: {inserted=} {bq_replaced=} {aux_probe_replaced=}")
    text = "\n".join(output) + "\n"
    for token in ("XBQ1 QBIN QBOUT BQ_MUTUAL_", "L_AUX AUX 0 10P", "R_AUX 0 AUX 20", "K_AUX Lin L_AUX", "XJTL1_1 QBOUT JTL1_OUT jtl", "XJTL1_6 JTL5_OUT JTL6_OUT jtl", "R_TERM JTL6_OUT 0 10", ".tran 0.1p 200p"):
        if token not in text:
            raise RuntimeError(f"required topology token missing in {case_id}: {token}")
    if text.count("L_AUX AUX 0 10P") != 1 or text.count("R_AUX 0 AUX 20") != 1 or text.count("K_AUX Lin L_AUX") != 1:
        raise RuntimeError(f"auxiliary count failed in {case_id}")
    if any(token in text for token in ("T_BVM_QB", "TRANSFORMER", "LC_LADDER", "PTL", "V_REPLAY", "SENTINEL")):
        raise RuntimeError(f"forbidden topology token in {case_id}")
    return text


def make_deck(case_id: str) -> dict[str, Any]:
    info = case_info(case_id)
    deck = case_dir(case_id) / "deck.cir"
    deck.parent.mkdir(parents=True, exist_ok=True)
    deck.write_text(transform_deck(info["mask"], info["K_point"], case_id, deck.parent), encoding="utf-8")
    return {**info, "path": rel(deck), "sha256": sha256(deck), "bytes": deck.stat().st_size, "topology": "canonical BVM -> COMMON_SL -> JSL1..8 -> QBIN -> experimental QB clone with canonical Lin plus grounded L_AUX/R_AUX/K_AUX -> QBOUT -> JTL1..6 -> terminal", "auxiliary": {"L_AUX_pH": LAUX_PH, "R_AUX_ohm": RAUX_OHM, "K": info["K_value"], "M_pH": info["M_pH"], "inside_experimental_qb_clone": True}}


def preflight_text(k_audit: dict[str, Any]) -> str:
    return f"""# Minimal Lin-coupled mutual-RL auxiliary feasibility — {EXP.name}

{CONTRACT_SENTENCE}

## Registration

- Frozen parent HEAD: `{EXPECTED_HEAD}`; remote `bvm/master`: `{EXPECTED_HEAD}`.
- Study phase: `EXPLORATORY`; role: `Experimental Operator + Evidence Packager`.
- Scientific review authorization: `false`; mechanical evidence only.
- Experiment B is independent of the LS3 timing-window experiment and does not read its results.

## Single question

Can a minimal passive mutual-RL auxiliary coupled to canonical QB `Lin=1.5 pH` reshape receiver back-action while retaining the canonical galvanic `JSL8 -> QBIN -> Lin -> BJs -> QB core` path?

## Frozen topology

- The canonical QB is not edited. Each deck uses an experimental QB clone with the original `Lin IN 1 1.5p`, BJs, BJ1/BJ2, L1/L2/L3, RJ1/RJ2 and bias unchanged.
- Added inside the clone only: `L_AUX AUX 0 10P`, `R_AUX 0 AUX 20`, `K_AUX Lin L_AUX K`.
- No added JJ, bias, capacitor, PTL, isolated receiver, transformer, or broken QBIN/Lin galvanic path.
- Full forward path remains BVM -> COMMON_SL -> JSL1..8 -> QBIN -> Lin -> BJs -> QB core -> QBOUT -> JTL1..6 -> terminal.
- `L_AUX/R_AUX = 0.5 ps` and 300 GHz impedance notes are engineering scales only.

## K registration

- Fixed `L_AUX=10 pH`, `R_AUX=20 Ω`; only positive K varies: `0.00`, `0.10`, `0.20`, `0.30`.
- `M=K*sqrt(1.5*10) pH`; matrix audit: `{json.dumps(k_audit['matrix'], ensure_ascii=False)}`.
- JoSIM K syntax fixture audit: `{k_audit['status']}`; no negative-polarity sweep.

## Authorized solve protocol

- Stage B0: `K000_0011`, `K000_0111` no-op gate first.
- Only if B0 passes: `K010/K020/K030` × `0011/0111` (six further fixed cases).
- Only if a tested K has the registered mechanical candidate `N2=2` and `N3=3`, choose the smallest such K and add exactly `<K>_0001`, `<K>_1111`.
- Absolute maximum is 10 new solves. No other K, L_AUX, R_AUX, polarity, timestep or topology case.

## Registered probes and evidence

- Full BVM/JSL/QB/JTL probes; active JS1/JS2, JM1/JM2, L_SL, JSL8, COMMON_SL, Lin, QBIN, BJ1/BJ2, L1/L2, all JTL stages and terminal.
- Auxiliary `I/V(L_AUX)`, `I/V(R_AUX)`, `V(AUX)`, Lin, QBIN, BVM source and JSL8.
- `[110,121)` and `[121,130)` actual-grid auxiliary current/voltage extrema/RMS and R_AUX dissipation `∫I(R_AUX)^2 R_AUX dt`.
- P(...) is raw radians; turns are independent unwrap/(2π) navigation only, never SFQ counts.

## Unknowns and stop

K=0 is a fixture/no-op gate, not a physical success gate. Mutual reciprocity, passive-realizability beyond the exact linear RL model, solver convergence and any mechanism remain UNKNOWN. After packaging and commit, stop at `{FINAL_MARKER}` with no automatic follow-up.
"""


def initial_yaml(k_audit: dict[str, Any], k0_records: dict[str, Any]) -> str:
    lines = ["schema_version: bvm-qb-lin-mutual-rl-aux-v1", f"id: {EXP.name}", "study_phase: EXPLORATORY", "role: Experimental Operator + Evidence Packager", "status: PREFLIGHT_PASS_K0_ONLY", f"contract_sentence: \"{CONTRACT_SENTENCE}\"", f"registration_head: {EXPECTED_HEAD}", f"remote_bvm_master_at_registration: {EXPECTED_HEAD}", "scientific_review_authorized: false", "mechanical_analysis_performed: false", "bounded_experiment_interpretation_performed: false", "independent_scientific_review_performed: false", "scientific_interpretation_performed: false", "", "question:", "  primary: \"Can a minimal passive Lin-coupled mutual-RL auxiliary reshape N3 while preserving N2?\"", "  scope: \"K=0/.1/.2/.3 at fixed Laux/Raux, then one smallest-K conditional N1/N4 pair only if mechanical 2/3 appears.\"", "  interpretation_ceiling: \"Mechanical candidate labels only; no physical solution or winner assignment.\"", "", "frozen:", "  Lin_pH: 1.5", "  Laux_pH: 10", "  Raux_ohm: 20", "  K_points: [0.0, 0.1, 0.2, 0.3]", "  positive_K_only: true", "  timestep_ps: 0.1", "  stop_time_ps: 200", "  actual_grid: true", "  interpolation: false", "  no_QB_parameter_change: true", "  no_new_JJ: true", "  no_capacitor: true", "  no_PTL: true", "", "authorized_matrix:"]
    for order, case_id in enumerate(FIXED_ORDER, 1):
        info = case_info(case_id)
        lines.extend([f"  - run_id: {case_id}", f"    K: {info['K_value']}", f"    M_pH: {info['M_pH']}", f"    mask: \"{info['mask']}\"", f"    execution_order: {order}", "    status: K0_gate_or_conditional_after_K0"])
    lines.extend(["  maximum_fixed_solves: 8", "  conditional_N1_N4_max_solves: 2", "  absolute_max_new_physical_solves: 10", "", "K_matrix_audit:", f"  status: {k_audit['status']}", f"  syntax_fixture: {k_audit['syntax_fixture']}", "  positive_definite_for_registered_points: true", "", "K0_deck_registration:"])
    for case_id, item in k0_records.items():
        lines.extend([f"  - run_id: {case_id}", f"    path: {item['path']}", f"    sha256: {item['sha256']}", f"    bytes: {item['bytes']}" ])
    lines.extend(["", "conditional_rule:", "  selection: smallest positive K with mechanical N2=2 and N3=3 candidate", "  added_masks: [0001, 1111]", "  no_subjective_waveform_ranking: true", "  scientific_assignment: NOT_ASSIGNED_SCIENTIFIC_REVIEW_REQUIRED", ""])
    return "\n".join(lines)


def prepare() -> None:
    assert_registration()
    k_audit = static_k_audit()
    if k_audit["status"] != "PASS":
        raise RuntimeError("K matrix audit failed")
    if EXP.exists() and any(EXP.iterdir()):
        raise RuntimeError(f"refusing non-empty experiment directory: {EXP}")
    EXP.mkdir(parents=True)
    for dirname in ("runs", "analysis", "plots"):
        (EXP / dirname).mkdir(parents=True, exist_ok=True)
    k0_records = {case_id: make_deck(case_id) for case_id in K0_ORDER}
    (EXP / "PREFLIGHT.md").write_text(preflight_text(k_audit), encoding="utf-8")
    (EXP / "experiment.yaml").write_text(initial_yaml(k_audit, k0_records), encoding="utf-8")
    closure = source_inventory()
    provenance = {"schema": "bvm-qb-lin-mutual-rl-aux-provenance-v1", "experiment_id": EXP.name, "created_at": now(), "registration_head": EXPECTED_HEAD, "remote_bvm_master_at_registration": EXPECTED_HEAD, "contract_sentence": CONTRACT_SENTENCE, "scientific_review_authorized": False, "mechanical_analysis_performed": False, "bounded_experiment_interpretation_performed": False, "independent_scientific_review_performed": False, "scientific_interpretation_performed": False, "solver": branch.replay_base.solver_context(), "source_closure": closure, "canonical_raw_hashes": EXPECTED_CANONICAL_HASHES, "K_matrix_audit": k_audit, "frozen": {"forward_path": "BVM -> COMMON_SL -> JSL1..8 -> QBIN -> canonical Lin -> BJs -> QB core -> QBOUT -> JTL1..6 -> terminal", "auxiliary": "L_AUX AUX 0 10P; R_AUX 0 AUX 20; K_AUX Lin L_AUX K inside experimental QB clone", "L_AUX_pH": LAUX_PH, "R_AUX_ohm": RAUX_OHM, "Lin_pH": LIN_PH, "K_points": K_POINTS, "windows_ps": [list(FULL), list(FOCUS), list(REARM)], "timestep_ps": 0.1, "stop_time_ps": 200.0, "no_negative_K": True, "no_QB_parameter_change": True}, "authorized_matrix": {"fixed_order": list(FIXED_ORDER), "K0_gate_order": list(K0_ORDER), "conditional_masks": list(CONDITIONAL_MASKS), "maximum_fixed_physical_solves": 8, "conditional_max": 2, "absolute_max": 10, "no_other_solve": True}, "registered_decks": k0_records, "runs": {}, "run_order": [], "execution": {"authorized_fixed_solve_count": 8, "conditional_authorized_max": 2, "absolute_authorized_max": 10, "actual_physical_solve_count": 0, "solver_invocation_count": 0, "run_order": []}, "K0_gate": {"status": "PENDING"}, "fixed_analysis": {"status": "PENDING"}, "conditional_selection": {"status": "PENDING"}, "analysis": {"status": "PENDING"}, "qa": {"status": "PENDING"}, "visualization": {"status": "PENDING"}, "package": {"status": "PENDING", "drive_file_id": None, "drive_url": None}, "stop": {"final_marker": None, "automatic_follow_up": False}}
    write_json(EXP / "provenance.json", provenance)
    result = {"schema": "bvm-qb-lin-mutual-rl-aux-result-v1", "experiment_id": EXP.name, "generated_at": now(), "status": "PREFLIGHT_PASS_K0_ONLY", "artifact_status": "PENDING", "scientific_review_authorized": False, "mechanical_analysis_performed": False, "bounded_experiment_interpretation_performed": False, "independent_scientific_review_performed": False, "scientific_interpretation_performed": False, "execution": provenance["execution"], "cases": {case_id: {"status": "AUTHORIZED_NOT_RUN" if case_id in K0_ORDER else "CONDITIONAL_NOT_MATERIALIZED"} for case_id in FIXED_ORDER}, "K_matrix": k_audit, "K0_gate": {"status": "PENDING"}, "fixed_points": {}, "conditional_population_validation": {"status": "NOT_AUTHORIZED"}, "classification": {"status": "SCIENTIFIC_REVIEW_REQUIRED", "assigned": None, "candidate_labels": ["MUTUAL_SELECTIVE_2_3", "MUTUAL_NONSELECTIVE", "MUTUAL_TOO_WEAK", "MUTUAL_DESTABILIZING", "MUTUAL_AUX_FIXTURE_INVALID", "MUTUAL_AUX_POPULATION_MAPPING_1_2_3_4_SUPPORTED"]}, "stop": {"final_marker": None, "automatic_follow_up": False}}
    write_json(EXP / "result.json", result)
    (EXP / "RESULT.md").write_text(f"# Minimal Lin-coupled mutual-RL auxiliary ({EXP.name})\n\nPreflight passed. K=0 no-op gate is registered first; K>0 decks remain unmaterialized until that gate passes.\n", encoding="utf-8")
    print(json.dumps({"status": "PREFLIGHT_PASS", "K_audit": k_audit["status"], "K0_order": list(K0_ORDER), "fixed_order": list(FIXED_ORDER)}, ensure_ascii=False, indent=2))


def warning_lines(path: Path) -> list[str]:
    if not path.is_file():
        return ["missing_log"]
    return [line.strip() for line in path.read_text(errors="replace").splitlines() if any(token in line for token in ("Missing model:", "Unknown device/node", "Cannot store results", "Error", "error"))]


def execute_cases(case_ids: list[str]) -> None:
    provenance = read_json(EXP / "provenance.json")
    for case_id in case_ids:
        if provenance["run_order"] != [*provenance["run_order"]]:
            raise RuntimeError("internal order state malformed")
        item = provenance["registered_decks"].get(case_id)
        if item is None:
            raise RuntimeError(f"case is not registered: {case_id}")
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
        expected = expected_headers(info["mask"])
        missing = sorted(expected - set(trace.headers))
        grid = branch.replay_base.finite_grid_qa(trace)
        record["raw"] = {"path": rel(raw), "sha256": sha256(raw), "bytes": raw.stat().st_size, "sample_count": trace.sample_count, "time_start_ps": trace.time[0] * 1.0e12, "time_end_ps": trace.time[-1] * 1.0e12, "grid": grid, "missing_required_probes": missing}
        record["solver_warning_lines"] = warning_lines(log)
        record["execution_status"] = "RUN_PASS" if not missing else "RUN_PASS_MISSING_PROBES"
        record["metadata"] = {"path": rel(metadata), "source": item.get("source", {"K": case_info(case_id)["K_value"], "M_pH": case_info(case_id)["M_pH"]}), "deck_sha256": sha256(deck), "raw_sha256": sha256(raw), "log_sha256": sha256(log), "execution_status": record["execution_status"]}
        write_json(metadata, record["metadata"])
        provenance["runs"][case_id] = record
        provenance["run_order"].append(case_id)
        provenance["execution"]["actual_physical_solve_count"] = len(provenance["run_order"])
        provenance["execution"]["solver_invocation_count"] = len(provenance["run_order"])
        provenance["execution"]["run_order"] = provenance["run_order"]
        write_json(EXP / "provenance.json", provenance)
        if missing:
            raise RuntimeError(f"missing probes in {case_id}: {missing}")
    write_json(EXP / "provenance.json", provenance)
    print(json.dumps({"status": "RUN_PASS", "run_order": provenance["run_order"], "physical_solves": provenance["execution"]["actual_physical_solve_count"]}, ensure_ascii=False, indent=2))


def aux_observables(trace: Any) -> dict[str, Any]:
    def stats(signal: str, window: tuple[float, float]) -> dict[str, Any]:
        return branch.waveform_stats(trace, signal, window) if signal in trace.headers else {"status": "UNKNOWN", "signal": signal, "window_ps": list(window)}
    aux_signals = ("I(L_AUX|XBQ1)", "V(L_AUX|XBQ1)", "I(R_AUX|XBQ1)", "V(R_AUX|XBQ1)", "V(AUX|XBQ1)")
    output = {"focus": {signal: stats(signal, FOCUS) for signal in aux_signals}, "rearm": {signal: stats(signal, REARM) for signal in aux_signals}}
    if any(signal not in trace.headers for signal in aux_signals):
        output.update({"status": "UNKNOWN", "missing": [signal for signal in aux_signals if signal not in trace.headers], "R_AUX_dissipation": {}, "passive_loop_model_only": False})
        return output
    dissipation = {}
    for window in (FOCUS, REARM):
        indices = time_indices(trace, window)
        times = [trace.time[index] for index in indices]
        current = [float(trace.column("I(R_AUX|XBQ1)")[index]) for index in indices]
        voltage = [float(trace.column("V(R_AUX|XBQ1)")[index]) for index in indices]
        signed_vi = actual_integral(times, [v * i for v, i in zip(voltage, current)])
        i2r = actual_integral(times, [i * i * RAUX_OHM for i in current])
        dissipation[str(window)] = {"window_ps": list(window), "signed_VI_energy_J": signed_vi, "signed_VI_energy_fJ": signed_vi * 1.0e15, "I2R_energy_J": i2r, "I2R_energy_fJ": i2r * 1.0e15, "passivity_nonnegative": i2r >= -1.0e-30, "actual_grid": True, "R_AUX_ohm": RAUX_OHM}
    output["R_AUX_dissipation"] = dissipation
    output["passive_loop_model_only"] = True
    output["no_directional_isolation_claim"] = True
    return output


def trace_metrics(label: str, mask: str, trace: Any, oracle_module: Any) -> dict[str, Any]:
    metrics = branch.run_metrics(label, mask, trace, family=None, canonical=True, delay_ps=0.0)
    if label.startswith("CANONICAL_"):
        metrics.update({"case_id": label, "K_point": "CANONICAL", "K_value": None, "mask": mask, "M_pH": None})
    else:
        metrics.update(case_info(label))
    metrics["multi_evidence_oracle"] = multi_evidence_oracle(trace, mask, oracle_module)
    metrics["auxiliary_observables"] = aux_observables(trace)
    metrics["active_bvm_indices"] = [index for index, bit in enumerate(mask, 1) if bit == "1"]
    metrics["phase_area_cross_checks_active"] = {f"P({element}|XBVM{index})": branch.phase_area(trace, f"P({element}|XBVM{index})", f"V({element}|XBVM{index})") for index in metrics["active_bvm_indices"] for element in ("B_JS1", "B_JS2")}
    return metrics


def compare_metrics(canonical_trace: Any, candidate_trace: Any, mask: str, canonical_metrics: dict[str, Any], candidate_metrics: dict[str, Any]) -> dict[str, Any]:
    signals = ["I(B_JSL8)", "V(COMMON_SL)", "V(QBIN)", "I(LIN|XBQ1)", "I(L1|XBQ1)", "I(L2|XBQ1)", "V(QBOUT)", "V(JTL6_OUT)", "I(R_TERM)", *[f"P(B01|XJTL1_{stage})" for stage in JTL_STAGES], *[f"V(JTL{stage}_OUT)" for stage in JTL_STAGES], "I(L_AUX|XBQ1)", "V(L_AUX|XBQ1)", "I(R_AUX|XBQ1)", "V(R_AUX|XBQ1)", "V(AUX|XBQ1)"]
    for index in candidate_metrics["active_bvm_indices"]:
        signals.extend([f"{kind}({element}|XBVM{index})" for element in ("B_JS1", "B_JS2", "B_JM1", "B_JM2") for kind in ("P", "V", "I")])
    deltas = {signal: {"focus_110_121": normalized_delta(canonical_trace, candidate_trace, signal, FOCUS), "full_0_200": normalized_delta(canonical_trace, candidate_trace, signal, FULL)} for signal in signals}
    return {"signal_deltas": deltas, "timing_drift": common.timing_drift(canonical_metrics["multi_evidence_oracle"], candidate_metrics["multi_evidence_oracle"]), "active_phase_p2p": common.phase_p2p_deltas(canonical_trace, candidate_trace, mask), "auxiliary_vs_canonical": {signal: normalized_delta(canonical_trace, candidate_trace, signal, FOCUS) for signal in ("I(LIN|XBQ1)", "V(QBIN)", "I(B_JSL8)", "V(COMMON_SL)")}, "actual_grid": True, "interpolation": False}


def k0_gate(canonical_n2: dict[str, Any], k0_n2: dict[str, Any], canonical_n3: dict[str, Any], k0_n3: dict[str, Any], canonical_n2_trace: Any, k0_n2_trace: Any, canonical_n3_trace: Any, k0_n3_trace: Any) -> dict[str, Any]:
    c2 = canonical_n2["multi_evidence_oracle"]
    k2 = k0_n2["multi_evidence_oracle"]
    c3 = canonical_n3["multi_evidence_oracle"]
    k3 = k0_n3["multi_evidence_oracle"]
    comparison_n2 = compare_metrics(canonical_n2_trace, k0_n2_trace, "0011", canonical_n2, k0_n2)
    comparison_n3 = compare_metrics(canonical_n3_trace, k0_n3_trace, "0111", canonical_n3, k0_n3)
    norm = [item["focus_110_121"].get("normalized_rms") for comparison in (comparison_n2, comparison_n3) for item in comparison["signal_deltas"].values() if item["focus_110_121"].get("status") == "DERIVED" and "normalized_rms" in item["focus_110_121"]]
    aux = k0_n2["auxiliary_observables"]
    aux_currents = [aux[window]["I(L_AUX|XBQ1)"].get("peak_abs", math.inf) for window in ("focus", "rearm")]
    aux_currents += [aux[window]["I(R_AUX|XBQ1)"].get("peak_abs", math.inf) for window in ("focus", "rearm")]
    criteria = {"grid_equal_N2": tuple(canonical_n2_trace.time) == tuple(k0_n2_trace.time), "grid_equal_N3": tuple(canonical_n3_trace.time) == tuple(k0_n3_trace.time), "N2_phase_chain_count_2": c2["ordered_phase_chain_count"] == 2 and k2["ordered_phase_chain_count"] == 2, "N3_phase_chain_count_4": c3["ordered_phase_chain_count"] == 4 and k3["ordered_phase_chain_count"] == 4, "first_landmark_timing_N2_within_0p2ps": comparison_n2["timing_drift"]["max_abs_delta_ps"] is not None and comparison_n2["timing_drift"]["max_abs_delta_ps"] <= 0.2, "first_landmark_timing_N3_within_0p2ps": comparison_n3["timing_drift"]["max_abs_delta_ps"] is not None and comparison_n3["timing_drift"]["max_abs_delta_ps"] <= 0.2, "key_waveforms_tight": bool(norm) and max(norm) <= 1.0e-3, "auxiliary_quiet_at_K0": bool(aux_currents) and max(aux_currents) <= 1.0e-9, "required_auxiliary_probes_present": all(aux[window][signal].get("status") == "DERIVED" for window in ("focus", "rearm") for signal in ("I(L_AUX|XBQ1)", "V(L_AUX|XBQ1)", "I(R_AUX|XBQ1)", "V(R_AUX|XBQ1)", "V(AUX|XBQ1)"))}
    return {"status": "PASS" if all(criteria.values()) else "FAIL", "criteria": criteria, "comparison_N2": comparison_n2, "comparison_N3": comparison_n3, "max_key_normalized_RMS": max(norm) if norm else None, "auxiliary_peak_abs_currents_A": aux_currents, "registered_tolerances": {"timing_ps": 0.2, "key_normalized_RMS": 1.0e-3, "auxiliary_quiet_A": 1.0e-9}, "scientific_interpretation_performed": False}


def multi_evidence_oracle_count(metrics: dict[str, Any], mask: str) -> int:
    return metrics["multi_evidence_oracle"]["ordered_phase_chain_count"]


def classify_fixed(metrics: dict[str, Any]) -> dict[str, Any]:
    oracle = metrics["multi_evidence_oracle"]
    n2 = oracle["ordered_phase_chain_count"] == 2 and oracle["terminal_pulse_count"] == 2
    n3 = oracle["ordered_phase_chain_count"] == 3
    gross = oracle["ordered_phase_chain_count"] > 4 or oracle["terminal_pulse_count"] > 4 or oracle["old_strict_status"] == "AMBIGUOUS_CLUSTER_COUNT"
    if gross:
        label = "MUTUAL_DESTABILIZING"
    elif n2 and n3:
        label = "MUTUAL_SELECTIVE_2_3"
    elif n3 and not n2:
        label = "MUTUAL_NONSELECTIVE"
    elif n2 and oracle["ordered_phase_chain_count"] == 4:
        label = "MUTUAL_TOO_WEAK"
    else:
        label = "MUTUAL_UNCLASSIFIED_OR_MIXED"
    return {"K_point": metrics["K_point"], "K_value": metrics["K_value"], "M_pH": metrics["M_pH"], "mask": metrics["mask"], "ordered_phase_chain_count": oracle["ordered_phase_chain_count"], "old_strict_complete_response_count": oracle["old_strict_complete_response_count"], "terminal_pulse_count": oracle["terminal_pulse_count"], "terminal_total_area_over_phi0": oracle["terminal_total_area_over_phi0"], "N2_normal_mechanical": n2 if metrics["mask"] == "0011" else None, "N3_target_mechanical": n3 if metrics["mask"] == "0111" else None, "no_gross_activity_heuristic": not gross, "mechanical_candidate_label": label, "classification_not_scientific": True}


def update_k0_gate() -> None:
    provenance = read_json(EXP / "provenance.json")
    oracle_module = load_oracle_module()
    canonical_n2_trace = load_raw(CANONICAL["0011"])
    k0_n2_trace = load_raw(REPO / provenance["runs"]["K000_0011"]["raw"]["path"])
    canonical_n3_trace = load_raw(CANONICAL["0111"])
    k0_n3_trace = load_raw(REPO / provenance["runs"]["K000_0111"]["raw"]["path"])
    canonical_n2 = trace_metrics("CANONICAL_0011", "0011", canonical_n2_trace, oracle_module)
    k0_n2 = trace_metrics("K000_0011", "0011", k0_n2_trace, oracle_module)
    canonical_n3 = trace_metrics("CANONICAL_0111", "0111", canonical_n3_trace, oracle_module)
    k0_n3 = trace_metrics("K000_0111", "0111", k0_n3_trace, oracle_module)
    gate = k0_gate(canonical_n2, k0_n2, canonical_n3, k0_n3, canonical_n2_trace, k0_n2_trace, canonical_n3_trace, k0_n3_trace)
    provenance["K0_gate"] = gate
    write_json(EXP / "analysis" / "K0_GATE.json", gate)
    write_json(EXP / "provenance.json", provenance)
    result = read_json(EXP / "result.json")
    result["K0_gate"] = {key: value for key, value in gate.items() if key != "comparison"}
    result["status"] = "K0_GATE_PASS_MAIN_MATERIALIZATION_AUTHORIZED" if gate["status"] == "PASS" else "K0_GATE_FAIL_STOP"
    result["artifact_status"] = "VALID"
    result["execution"] = provenance["execution"]
    write_json(EXP / "result.json", result)
    print(json.dumps({"status": gate["status"], "criteria": gate["criteria"]}, ensure_ascii=False, indent=2))


def materialize_main() -> None:
    provenance = read_json(EXP / "provenance.json")
    if provenance.get("K0_gate", {}).get("status") != "PASS":
        raise RuntimeError("K0 gate did not pass")
    records = {case_id: make_deck(case_id) for case_id in FIXED_ORDER[2:]}
    provenance["registered_decks"].update(records)
    provenance["main_materialization"] = {"status": "PASS", "cases": list(records), "materialized_at": now(), "no_negative_K": True}
    write_json(EXP / "provenance.json", provenance)
    print(json.dumps({"status": "MAIN_MATERIALIZED", "cases": list(records)}, ensure_ascii=False, indent=2))


def materialize_conditional(selected: str) -> None:
    provenance = read_json(EXP / "provenance.json")
    if selected not in K_POINTS or selected == "K000":
        raise RuntimeError(f"invalid conditional K: {selected}")
    if provenance.get("conditional_selection", {}).get("selected_K") != selected:
        raise RuntimeError("conditional selection is not registered")
    records = {f"{selected}_{mask}": make_deck(f"{selected}_{mask}") for mask in CONDITIONAL_MASKS}
    provenance["registered_decks"].update(records)
    provenance["conditional_materialization"] = {"status": "PASS", "selected_K": selected, "cases": list(records), "materialized_at": now(), "selection_rule": "smallest positive K with mechanical N2=2 and N3=3"}
    write_json(EXP / "provenance.json", provenance)
    yaml = EXP / "experiment.yaml"
    text = yaml.read_text(encoding="utf-8").rstrip()
    block = ["", "conditional_N1_N4_deck_registration:", f"  selected_K: {selected}"]
    for case_id in records:
        block.extend([f"  - run_id: {case_id}", f"    path: {records[case_id]['path']}", f"    sha256: {records[case_id]['sha256']}", f"    bytes: {records[case_id]['bytes']}"])
    yaml.write_text(text + "\n" + "\n".join(block) + "\n", encoding="utf-8")
    print(json.dumps({"status": "CONDITIONAL_MATERIALIZED", "selected_K": selected, "cases": list(records)}, ensure_ascii=False, indent=2))


def analyze() -> None:
    provenance = read_json(EXP / "provenance.json")
    registered_runner = next(item for item in provenance["source_closure"] if item["name"] == "runner")
    current_runner = record_file("runner", SCRIPT, registered_runner["role"])
    if registered_runner["sha256"] != current_runner["sha256"]:
        provenance["postsolve_tooling_revision"] = {"path": rel(SCRIPT), "old_sha256": registered_runner["sha256"], "new_sha256": current_runner["sha256"], "reason": "analysis-only canonical-label repair; no physical rerun", "physical_rerun": False, "raw_mutated": False}
        registered_runner.update({"sha256": current_runner["sha256"], "bytes": current_runner["bytes"]})
    oracle_module = load_oracle_module()
    run_order = provenance["run_order"]
    traces = {case_id: load_raw(REPO / provenance["runs"][case_id]["raw"]["path"]) for case_id in run_order}
    canonical_traces = {mask: load_raw(CANONICAL[mask]) for mask in ("0011", "0111", "0001", "1111")}
    canonical_metrics = {mask: trace_metrics(f"CANONICAL_{mask}", mask, trace, oracle_module) for mask, trace in canonical_traces.items()}
    metrics = {case_id: trace_metrics(case_id, case_info(case_id)["mask"], traces[case_id], oracle_module) for case_id in run_order}
    fixed = {case_id: classify_fixed(item) for case_id, item in metrics.items() if case_id in FIXED_ORDER}
    fixed_by_K: dict[str, Any] = {}
    for case_id, item in fixed.items():
        fixed_by_K.setdefault(item["K_point"], {})[item["mask"]] = item
    for point, pair in fixed_by_K.items():
        if point == "K000":
            pair["pair_mechanical_candidate_label"] = "MUTUAL_AUX_FIXTURE_K0_PASS" if provenance.get("K0_gate", {}).get("status") == "PASS" else "MUTUAL_AUX_FIXTURE_INVALID"
        else:
            n2 = pair.get("0011", {}).get("ordered_phase_chain_count") == 2 and pair.get("0011", {}).get("N2_normal_mechanical") is True
            n3 = pair.get("0111", {}).get("ordered_phase_chain_count") == 3 and pair.get("0111", {}).get("N3_target_mechanical") is True
            gross = any(pair.get(mask, {}).get("no_gross_activity_heuristic") is False for mask in ("0011", "0111"))
            if gross:
                pair_label = "MUTUAL_DESTABILIZING"
            elif n2 and n3:
                pair_label = "MUTUAL_SELECTIVE_2_3"
            elif n3 and not n2:
                pair_label = "MUTUAL_NONSELECTIVE"
            elif n2 and pair.get("0111", {}).get("ordered_phase_chain_count") == 4:
                pair_label = "MUTUAL_TOO_WEAK"
            else:
                pair_label = "MUTUAL_UNCLASSIFIED_OR_MIXED"
            pair["pair_mechanical_candidate_label"] = pair_label
    selection_candidates = []
    for point in ("K010", "K020", "K030"):
        pair = fixed_by_K.get(point, {})
        if pair.get("pair_mechanical_candidate_label") == "MUTUAL_SELECTIVE_2_3":
            selection_candidates.append(point)
    selected = min(selection_candidates, key=lambda point: K_POINTS[point]) if selection_candidates else None
    provenance["fixed_analysis"] = {"status": "COMPLETE", "by_K": fixed_by_K, "selection_candidates": selection_candidates}
    provenance["conditional_selection"] = {"status": "AUTHORIZED" if selected else "NOT_AUTHORIZED", "selected_K": selected, "selection_candidates": selection_candidates, "rule": "smallest positive K satisfying mechanical N2=2 and N3=3; no subjective waveform ranking", "no_scientific_winner": True}
    validations = {}
    for case_id, item in metrics.items():
        mask = case_info(case_id)["mask"]
        validations[case_id] = {"vs_canonical": compare_metrics(canonical_traces[mask], traces[case_id], mask, canonical_metrics[mask], item), "fixed_candidate": fixed.get(case_id), "auxiliary_observables": item["auxiliary_observables"]}
    conditional_metrics = {case_id: item for case_id, item in metrics.items() if case_id not in fixed}
    conditional_validation = {}
    for case_id, item in conditional_metrics.items():
        mask = case_info(case_id)["mask"]
        conditional_validation[case_id] = {"vs_canonical": compare_metrics(canonical_traces[mask], traces[case_id], mask, canonical_metrics[mask], item), "multi_evidence": item["multi_evidence_oracle"]}
    raw_before = {case_id: sha256(REPO / provenance["runs"][case_id]["raw"]["path"]) for case_id in run_order}
    refs = [item["path"] for item in provenance["source_closure"] if item["name"].startswith("canonical_")]
    refs_before = {path: sha256(REPO / path) for path in refs}
    analysis = {"schema": "bvm-qb-lin-mutual-rl-aux-mechanical-analysis-v1", "experiment_id": EXP.name, "generated_at": now(), "runs": metrics, "fixed_classifications": fixed, "fixed_by_K": fixed_by_K, "validations": validations, "conditional_validation": conditional_validation, "conditional_selection": provenance["conditional_selection"], "canonical_references": canonical_metrics, "K_matrix_audit": provenance["K_matrix_audit"], "raw_hash_before_analysis": raw_before, "reference_hashes_before_analysis": refs_before, "actual_grid": True, "interpolation": False, "scientific_interpretation_performed": False, "independent_scientific_review_performed": False}
    write_json(EXP / "analysis" / "mechanical_analysis.json", analysis)
    raw_after = {case_id: sha256(REPO / provenance["runs"][case_id]["raw"]["path"]) for case_id in run_order}
    refs_after = {path: sha256(REPO / path) for path in refs}
    if raw_before != raw_after or refs_before != refs_after:
        raise RuntimeError("raw/reference mutation detected")
    provenance.update({"mechanical_analysis_performed": True, "bounded_experiment_interpretation_performed": False, "independent_scientific_review_performed": False, "scientific_interpretation_performed": False, "raw_hash_before_analysis": raw_before, "raw_hash_after_analysis": raw_after, "reference_hashes_before_analysis": refs_before, "reference_hashes_after_analysis": refs_after, "analysis": {"status": "COMPLETE", "path": rel(EXP / "analysis" / "mechanical_analysis.json"), "fixed_case_count": len(fixed), "conditional_case_count": len(conditional_metrics), "no_negative_K": True, "no_other_solve": True}, "execution_status": "ALL_AUTHORIZED_RUNS_COMPLETE_ANALYSIS_PENDING"})
    for case_id in run_order:
        provenance["runs"][case_id].update({"mechanical_analysis_performed": True, "bounded_experiment_interpretation_performed": False, "independent_scientific_review_performed": False, "scientific_interpretation_performed": False})
    write_json(EXP / "provenance.json", provenance)
    result = read_json(EXP / "result.json")
    compact = {}
    for case_id, item in metrics.items():
        q = item["multi_evidence_oracle"]
        compact[case_id] = {"run_id": case_id, "K_point": case_info(case_id)["K_point"], "K": case_info(case_id)["K_value"], "M_pH": case_info(case_id)["M_pH"], "mask": case_info(case_id)["mask"], "ordered_phase_chain_count": q["ordered_phase_chain_count"], "old_strict_complete_response_count": q["old_strict_complete_response_count"], "jtl6_cluster_count": q["jtl6_cluster_count"], "terminal_pulse_count": q["terminal_pulse_count"], "terminal_total_area_over_phi0": q["terminal_total_area_over_phi0"], "BJ1_landmarks_ps": [common.phase_time(q, "BJ1", i) for i in range(1, 5)], "BJ2_landmarks_ps": [common.phase_time(q, "BJ2", i) for i in range(1, 5)], "mechanical_candidate_label": fixed.get(case_id, {}).get("mechanical_candidate_label"), "conditional_population_candidate": q.get("descriptive_candidate_label") if case_info(case_id)["mask"] in CONDITIONAL_MASKS else None, "raw_path": provenance["runs"][case_id]["raw"]["path"], "raw_sha256": provenance["runs"][case_id]["raw"]["sha256"]}
    result.update({"generated_at": now(), "status": "ANALYSIS_COMPLETE_AWAITING_SCIENTIFIC_REVIEW", "artifact_status": "VALID", "mechanical_analysis_performed": True, "bounded_experiment_interpretation_performed": False, "independent_scientific_review_performed": False, "scientific_interpretation_performed": False, "execution": provenance["execution"], "cases": compact, "fixed_points": fixed_by_K, "conditional_population_validation": {"status": "COMPLETE" if conditional_metrics else "NOT_RUN", "selected_K": selected, "cases": conditional_validation}, "classification": {"status": "SCIENTIFIC_REVIEW_REQUIRED", "assigned": None, "fixed_candidate_labels": fixed, "conditional_selection": provenance["conditional_selection"], "reason": "mechanical candidates only"}, "stop": {"final_marker": FINAL_MARKER, "automatic_follow_up": False}})
    write_json(EXP / "result.json", result)
    write_result_markdown(result, analysis)
    write_json(EXP / "analysis" / "SOURCE_MANIFEST.json", {"schema": "bvm-qb-lin-mutual-rl-aux-source-manifest-v1", "experiment_id": EXP.name, "generated_at": now(), "source_closure": provenance["source_closure"], "canonical_raw_hashes": EXPECTED_CANONICAL_HASHES, "K_matrix_audit": provenance["K_matrix_audit"]})
    write_json(EXP / "analysis" / "TRANSFORMATION_REGISTRY.json", {"schema": "bvm-qb-lin-mutual-rl-aux-transformation-registry-v1", "raw_mutation": False, "operations": [{"name": "experimental_qb_clone", "rule": "canonical BQ cloned; only grounded L_AUX/R_AUX/K_AUX added inside clone; canonical QB source untouched"}, {"name": "K_values", "values": K_POINTS, "M_formula": "K*sqrt(1.5*10) pH", "positive_K_only": True}, {"name": "aux_energy", "rule": "actual-grid integral of I(R_AUX)^2*20 and V(R_AUX)*I(R_AUX)"}, {"name": "phase_display", "rule": "unwrap(raw radians)/(2*pi), navigation only"}, {"name": "area", "rule": "same JJ/endpoints/direction actual-grid trapezoid; not SFQ count"}]})
    print(json.dumps({"status": "ANALYSIS_COMPLETE", "fixed_points": fixed_by_K, "selected_K": selected, "conditional_cases": list(conditional_metrics)}, ensure_ascii=False, indent=2))


def write_result_markdown(result: dict[str, Any], analysis: dict[str, Any]) -> None:
    lines = [f"# Minimal Lin-coupled mutual-RL auxiliary ({EXP.name})", "", f"- Status: `{result['status']}`", "- Artifact status: `VALID`", "- Scientific interpretation: `NOT_PERFORMED`; final assignment: `SCIENTIFIC_REVIEW_REQUIRED`.", f"- Frozen parent `{EXPECTED_HEAD}`; K=0/.1/.2/.3 only; positive K only; no negative K sweep.", "- Canonical galvanic path remains JSL8 → QBIN → Lin → BJs → QB core; auxiliary is inside an experimental QB clone.", "", "## K matrix", "", "| K point | K | M (pH) | 0011 ordered chains | 0111 ordered chains | 0011 candidate | 0111 candidate |", "|---|---:|---:|---:|---:|---|---|"]
    for point in ("K000", "K010", "K020", "K030"):
        pair = analysis["fixed_by_K"].get(point, {})
        n2, n3 = pair.get("0011", {}), pair.get("0111", {})
        pair_label = pair.get("pair_mechanical_candidate_label", "—")
        lines.append(f"| `{point}` | {K_POINTS[point]:.2f} | {K_POINTS[point] * math.sqrt(LIN_PH * LAUX_PH):.8g} | {n2.get('ordered_phase_chain_count', '—')} | {n3.get('ordered_phase_chain_count', '—')} | `{pair_label}` | `{pair_label}` |")
    lines.extend(["", "K=0 no-op gate status: `" + str(result.get("K0_gate", {}).get("status")) + "`.", "", "## Conditional population validation", "", f"- Selected K by preregistered smallest-positive mechanical rule: `{result.get('conditional_population_validation', {}).get('selected_K')}`.", "- Conditional N1/N4 solves are added only when fixed K evidence has N2=2 and N3=3 mechanically; no subjective waveform ranking is used.", ""])
    for case_id, item in result.get("conditional_population_validation", {}).get("cases", {}).items():
        q = item["multi_evidence"]
        lines.append(f"- `{case_id}`: ordered chains={q['ordered_phase_chain_count']}, JTL6 clusters={q['jtl6_cluster_count']}, terminal clusters={q['terminal_pulse_count']}, terminal area={common.fmt(q['terminal_total_area_over_phi0'])} Φ0; candidate `{q['descriptive_candidate_label']}`.")
    lines.extend(["", "## Auxiliary measurements", "", "Per-K auxiliary I/V, R_AUX signed V·I energy, I²R dissipation, Lin/QBIN/BVM/JSL8 deltas, and all internal/downstream records are in `analysis/mechanical_analysis.json`.", "The R_AUX nonnegative dissipation check is a numerical property of this finite passive model, not a claim of directional isolation or hardware realizability.", "", "Phase is raw radians; turns are navigation only. Navigation/area/cluster quantities are not literal SFQ counts.", "", f"Stop marker: `{FINAL_MARKER}`.", ""])
    (EXP / "RESULT.md").write_text("\n".join(lines), encoding="utf-8")
    (EXP / "analysis" / "NUMERICAL_REVIEW.md").write_text("\n".join(["# Numerical review — mechanical only", "", "- K matrix is recomputed as M=K*sqrt(1.5*10) pH; positive-definiteness is checked for all registered K.", "- K=0 fixture uses a grounded L/R loop and no new JJ/bias; its no-op gate is separate from physical success.", "- Auxiliary energies and deltas use actual stored timestamps; no interpolation/resampling.", "- P(...) remains raw radians; turns use independent unwrap/(2*pi) navigation only.", "- No timestep/solver/process sensitivity or physical delay-equivalence claim is made."]) + "\n", encoding="utf-8")
    (EXP / "analysis" / "ADVERSARIAL_REVIEW.md").write_text("\n".join(["# Adversarial review probes — mechanical only", "", "- Canonical QB source file is hash-pinned and not edited; the auxiliary is only in the experimental clone.", "- Galvanic QBIN/Lin path, canonical JSL/JTL/terminal and BVM are retained in every deck.", "- K syntax and 2x2 inductance matrix validity are audited before K0 execution.", "- K0 must pass before K>0 decks are materialized; only preregistered smallest-K conditional N1/N4 can follow.", "- Positive K only; no polarity sweep, component sweep, timestep sweep, sentinel or isolated receiver.", "- Candidate labels are mechanical evidence only; no winner, mechanism or physical solution assignment."]) + "\n", encoding="utf-8")


def mechanical_qa() -> None:
    provenance = read_json(EXP / "provenance.json")
    failures = []
    checks = {}
    run_order = provenance["run_order"]
    if run_order[:2] != list(K0_ORDER):
        failures.append("K0_order")
    if any(case_id not in provenance["registered_decks"] for case_id in run_order):
        failures.append("unregistered_run")
    for case_id in run_order:
        rec = provenance["runs"][case_id]
        deck, raw, log, meta = [REPO / rec[key]["path"] for key in ("deck", "raw", "log", "metadata")]
        trace = load_raw(raw)
        text = deck.read_text(encoding="utf-8")
        grid = branch.replay_base.finite_grid_qa(trace)
        info = case_info(case_id)
        expected = expected_headers(info["mask"])
        missing = sorted(expected - set(trace.headers))
        warnings = warning_lines(log)
        unexpected = [line for line in warnings if line not in KNOWN_WARNINGS]
        topology_ok = text.count("L_AUX AUX 0 10P") == 1 and text.count("R_AUX 0 AUX 20") == 1 and text.count("K_AUX Lin L_AUX") == 1 and text.count("XBQ1 QBIN QBOUT BQ_MUTUAL_") == 1 and "XJTL1_1 QBOUT JTL1_OUT jtl" in text and "XJTL1_6 JTL5_OUT JTL6_OUT jtl" in text and "R_TERM JTL6_OUT 0 10" in text and ".tran 0.1p 200p" in text
        passed = bool(rec["execution_status"] == "RUN_PASS" and topology_ok and meta.is_file() and not missing and not trace.duplicate_columns and grid["status"] == "VALID" and grid["sample_count"] == 1999 and grid["time_start_ps"] == 0.0 and grid["time_end_ps"] == 199.9 and not unexpected and sha256(raw) == rec["raw"]["sha256"] and sha256(deck) == rec["deck"]["sha256"])
        if not passed:
            failures.append(case_id)
        checks[case_id] = {"status": "PASS" if passed else "ARTIFACT_INVALID", "topology_ok": topology_ok, "grid": grid, "missing_required_probes": missing, "warnings": warnings, "unexpected_warnings": unexpected}
    source_ok = all(sha256(REPO / item["path"]) == item["sha256"] for item in provenance["source_closure"])
    count = len(run_order)
    passed = bool(not failures and source_ok and count in (2, 8, 10) and count <= 10 and provenance["execution"]["actual_physical_solve_count"] == count and provenance.get("raw_hash_before_analysis") == provenance.get("raw_hash_after_analysis") and provenance.get("reference_hashes_before_analysis") == provenance.get("reference_hashes_after_analysis"))
    qa = {"schema": "bvm-qb-lin-mutual-rl-aux-mechanical-qa-v1", "experiment_id": EXP.name, "generated_at": now(), "status": "PASS" if passed else "FAIL", "artifact_status": "VALID" if passed else "ARTIFACT_INVALID", "run_order": run_order, "actual_physical_solve_count": count, "allowed_counts": [2, 8, 10], "max_physical_solves": 10, "K0_gate_status": provenance.get("K0_gate", {}).get("status"), "source_hashes_match": source_ok, "raw_hash_before_after_equal": provenance.get("raw_hash_before_analysis") == provenance.get("raw_hash_after_analysis"), "reference_hash_before_after_equal": provenance.get("reference_hashes_before_analysis") == provenance.get("reference_hashes_after_analysis"), "contains_all_new_run_raw": None, "contains_reference_raw_copies": False, "contains_delivery_manifest": False, "runs": checks, "failures": failures, "mechanical_analysis_performed": True, "bounded_experiment_interpretation_performed": False, "independent_scientific_review_performed": False, "scientific_interpretation_performed": False}
    write_json(EXP / "analysis" / "MECHANICAL_QA.json", qa)
    provenance["qa"] = qa
    write_json(EXP / "provenance.json", provenance)
    result = read_json(EXP / "result.json")
    result["qa_summary"] = {"status": qa["status"], "artifact_status": qa["artifact_status"]}
    write_json(EXP / "result.json", result)
    if not passed:
        raise RuntimeError(f"mechanical QA failed: {failures}")
    print(json.dumps({"status": "PASS", "physical_solves": count, "run_order": run_order}, ensure_ascii=False, indent=2))


def visualization() -> None:
    provenance = read_json(EXP / "provenance.json")
    if provenance.get("qa", {}).get("status") != "PASS":
        raise RuntimeError("QA required before viz")
    asset = EXP / "plots" / "assets" / "plotly.min.js"
    entries = []
    specs = {"01_SIGNAL_TIMING": ["V(COMMON_SL)", "I(B_JSL8)", "V(QBIN)", "I(LIN|XBQ1)", "V(QBOUT)"], "02_BVM_STATE": [signal for index in range(1, 5) for element in ("B_JS1", "B_JS2", "B_JM1", "B_JM2") for signal in (f"P({element}|XBVM{index})", f"V({element}|XBVM{index})", f"I({element}|XBVM{index})")], "03_JSL_CHAIN": [signal for index in range(1, 9) for signal in (f"P(B_JSL{index})", f"V(B_JSL{index})", f"I(B_JSL{index})")], "04_QB_STATE": ["V(QBIN)", "I(LIN|XBQ1)", "V(LIN|XBQ1)", "I(L_AUX|XBQ1)", "V(L_AUX|XBQ1)", "I(R_AUX|XBQ1)", "V(R_AUX|XBQ1)", "V(AUX|XBQ1)", "P(BJ1|XBQ1)", "V(BJ1|XBQ1)", "I(BJ1|XBQ1)", "P(BJ2|XBQ1)", "V(BJ2|XBQ1)", "I(BJ2|XBQ1)", "I(L1|XBQ1)", "V(L1|XBQ1)", "I(L2|XBQ1)", "V(L2|XBQ1)", "V(QBOUT)"], "05_JTL_CHAIN": [signal for stage in JTL_STAGES for signal in (f"P(B01|XJTL1_{stage})", f"V(B01|XJTL1_{stage})", f"I(B01|XJTL1_{stage})", f"P(B02|XJTL1_{stage})", f"V(B02|XJTL1_{stage})", f"I(B02|XJTL1_{stage})", f"V(JTL{stage}_OUT)")] + ["I(R_TERM)"]}
    for case_id in provenance["run_order"]:
        raw = REPO / provenance["runs"][case_id]["raw"]["path"]
        trace = load_raw(raw)
        for page, requested in specs.items():
            selected = [signal for signal in requested if signal in trace.headers]
            output = EXP / "plots" / case_id / f"{page}_full_0_200.html"
            branch.render_plot(raw, output, selected, f"{case_id}: {page}; full 0–200 ps; actual stored grid", asset)
            entries.append({"kind": "standalone", "run_id": case_id, "path": rel(output), "raw_path": rel(raw), "raw_sha256": sha256(raw), "sha256": sha256(output), "bytes": output.stat().st_size, "signals": selected, "window_ps": list(FULL), "focused": False, "phase_display": "raw radians; rad/(2*pi) turns navigation only"})
            crop = branch.total_helpers.crop_csv(raw, *FOCUS)
            try:
                focus = EXP / "plots" / case_id / f"{page}_focus_110_121.html"
                branch.render_plot(crop, focus, selected, f"{case_id}: {page}; focus [110,121) ps; actual stored samples", asset)
                entries.append({"kind": "standalone", "run_id": case_id, "path": rel(focus), "raw_path": rel(raw), "raw_sha256": sha256(raw), "sha256": sha256(focus), "bytes": focus.stat().st_size, "signals": selected, "window_ps": list(FOCUS), "focused": True, "derived_input": "actual-grid crop only; no interpolation", "phase_display": "raw radians; rad/(2*pi) turns navigation only"})
            finally:
                crop.unlink(missing_ok=True)
    for mask in ("0011", "0111"):
        cases = [(f"CANONICAL_{mask}", load_raw(CANONICAL[mask]))]
        cases.extend((case_id, load_raw(REPO / provenance["runs"][case_id]["raw"]["path"])) for case_id in provenance["run_order"] if case_info(case_id)["mask"] == mask)
        for page, requested in (("01_SIGNAL_TIMING", specs["01_SIGNAL_TIMING"]), ("03_JSL_CHAIN", specs["03_JSL_CHAIN"]), ("04_QB_STATE", specs["04_QB_STATE"]), ("05_JTL_CHAIN", specs["05_JTL_CHAIN"])):
            selected = [signal for signal in requested if all(signal in trace.headers for _, trace in cases)]
            if not selected:
                continue
            temp = branch.total_helpers.comparison_csv(cases, selected, FOCUS)
            output = EXP / "plots" / "comparisons" / f"{mask}_{page}_focus_110_121.html"
            try:
                labels = [branch.replay_base.prefixed_label(case, signal) for case, _ in cases for signal in selected]
                branch.render_plot(temp, output, labels, f"{mask}: canonical/mutual K comparison {page}; focus [110,121) ps", asset)
            finally:
                temp.unlink(missing_ok=True)
            entries.append({"kind": "comparison", "mask": mask, "path": rel(output), "sha256": sha256(output), "bytes": output.stat().st_size, "cases": [case for case, _ in cases], "signals": selected, "window_ps": list(FOCUS), "focused": True, "phase_display": "independent case unwrap; rad/(2*pi) turns navigation only"})
    html = sorted((EXP / "plots").rglob("*.html"))
    invalid = [rel(path) for path in html if any(token in path.read_text(encoding="utf-8") for token in ("plotly.js v", "var Plotly=", "cdn.plot.ly", "Unknown"))]
    record = {"schema": "bvm-qb-lin-mutual-rl-aux-visualization-v1", "status": "PASS" if entries and asset.is_file() and not invalid else "FAIL", "generated_at": now(), "renderer": rel(PLOTTER), "layout": "sep_comb", "color": "dark", "phase_option": "2pi", "entries": entries, "standalone_count": sum(item["kind"] == "standalone" for item in entries), "comparison_count": sum(item["kind"] == "comparison" for item in entries), "focused_window_entries": sum(item["focused"] for item in entries), "asset": {"path": rel(asset), "sha256": sha256(asset) if asset.is_file() else None, "bytes": asset.stat().st_size if asset.is_file() else None}, "invalid_runtime_pages": invalid, "raw_hashes_rechecked": all(item["raw_sha256"] == sha256(REPO / item["raw_path"]) for item in entries if item["kind"] == "standalone"), "descriptive_only": True}
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
    write_json(EXP / "analysis" / "RAW_ANALYSIS_HANDOFF_MANIFEST.json", {"schema": "bvm-qb-lin-mutual-rl-aux-raw-analysis-handoff-v1", "experiment_id": EXP.name, "generated_at": now(), "raw_is_immutable_solver_output": True, "processed_crops_are_not_raw_substitutes": True, "files_excluding_delivery_manifest": records})
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
        n = 2
        while (delivery / f"{EXP.name}_v{n}_raw_evidence.zip").exists():
            n += 1
        version = f"v{n}"
        package_path = delivery / f"{EXP.name}_{version}_raw_evidence.zip"
    files = [(EXP / name, name) for name in ("experiment.yaml", "PREFLIGHT.md", "RESULT.md", "result.json", "provenance.json")]
    plots = []
    for dirname in ("runs", "analysis", "plots"):
        for path in sorted((EXP / dirname).rglob("*")):
            if path.is_file() and (dirname != "plots" or path.name == "plotly.min.js" or "focus_110_121" in path.name):
                files.append((path, path.relative_to(EXP).as_posix()))
                if dirname == "plots":
                    plots.append(path.relative_to(EXP).as_posix())
    files.append((SCRIPT, "executor/bvm_qb_lin_mutual_rl_aux.py"))
    records = [{"path": name, "sha256": sha256(path), "bytes": path.stat().st_size} for path, name in files]
    with zipfile.ZipFile(package_path, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path, name in files:
            archive.write(path, name)
    with zipfile.ZipFile(package_path) as archive:
        reopened = {name: hashlib.sha256(archive.read(name)).hexdigest() for name in archive.namelist()}
    expected = {item["path"]: item["sha256"] for item in records}
    raw_members = [f"runs/{case_id}/raw.csv" for case_id in provenance["run_order"]]
    qa = {"status": "PASS" if expected == reopened and all(member in reopened for member in raw_members) else "FAIL", "package_version": version, "package_path": str(package_path), "package_sha256": sha256(package_path), "package_bytes": package_path.stat().st_size, "file_count": len(records), "expected_file_hashes_match_after_reopen": expected == reopened, "zip_files": records, "contains_all_new_run_raw": all(member in reopened for member in raw_members), "new_run_raw_members": raw_members, "contains_reference_raw_copies": False, "contains_delivery_manifest": False, "delivery_manifest_outside_zip": True, "packaged_plot_file_count": len(plots), "packaged_plot_paths": plots, "package_plot_policy": "focused pages/runtime only; full visualization remains committed", "not_in_git": True, "git_head_at_packaging": git_head(), "remote_head_at_packaging": remote_head()}
    manifest = {"schema": "bvm-qb-lin-mutual-rl-aux-delivery-manifest-v1", "experiment_id": EXP.name, "created_at": now(), "status": "READY_FOR_DRIVE_UPLOAD" if qa["status"] == "PASS" else "PACKAGE_INVALID", "package_version": version, "package_path": str(package_path), "package_sha256": qa["package_sha256"], "package_bytes": qa["package_bytes"], "package_qa": qa, "drive_folder_id": DRIVE_FOLDER_ID, "drive_file_id": None, "drive_url": None, "delivery_id_is_outside_zip_to_avoid_self_reference": True}
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
    path = EXP / "delivery_manifest.json"
    manifest = read_json(path)
    package_path = Path(manifest["package_path"])
    if sha256(package_path) != manifest["package_sha256"]:
        raise RuntimeError("local package changed")
    if remote_bytes is not None and int(remote_bytes) != manifest["package_bytes"]:
        raise RuntimeError("Drive size mismatch")
    manifest.update({"status": "UPLOADED", "drive_file_id": file_id, "drive_url": url, "uploaded_at": now(), "drive_verified_local_sha256": manifest["package_sha256"], "drive_verified_local_bytes": manifest["package_bytes"], "remote_sha256_from_connector": None})
    write_json(path, manifest)
    provenance = read_json(EXP / "provenance.json")
    provenance["package"].update({"status": "UPLOADED", "drive_file_id": file_id, "drive_url": url, "drive_uploaded_at": manifest["uploaded_at"], "delivery_manifest_sha256": sha256(path), "drive_sha256_verified": "metadata SHA not supplied by connector"})
    write_json(EXP / "provenance.json", provenance)
    result = read_json(EXP / "result.json")
    result["package_summary"].update({"status": "UPLOADED", "drive_file_id": file_id, "drive_url": url})
    write_json(EXP / "result.json", result)
    print(json.dumps({"status": "UPLOADED", "drive_file_id": file_id, "drive_url": url, "package_sha256": manifest["package_sha256"], "package_bytes": manifest["package_bytes"]}, ensure_ascii=False, indent=2))


def all_actions() -> None:
    prepare()
    execute_cases(list(K0_ORDER))
    update_k0_gate()
    provenance = read_json(EXP / "provenance.json")
    if provenance["K0_gate"]["status"] != "PASS":
        analyze()
        mechanical_qa()
        visualization()
        package()
        return
    materialize_main()
    execute_cases(list(FIXED_ORDER[2:]))
    analyze()
    provenance = read_json(EXP / "provenance.json")
    selected = provenance.get("conditional_selection", {}).get("selected_K")
    if selected:
        materialize_conditional(selected)
        execute_cases([f"{selected}_0001", f"{selected}_1111"])
        analyze()
    mechanical_qa()
    visualization()
    package()


def main() -> int:
    command = sys.argv[1] if len(sys.argv) > 1 else "all"
    actions = {"prepare": prepare, "run-k0": lambda: execute_cases(list(K0_ORDER)), "gate-k0": update_k0_gate, "materialize-main": materialize_main, "run-main": lambda: execute_cases(list(FIXED_ORDER[2:])), "analyze": analyze, "qa": mechanical_qa, "viz": visualization, "package": package, "record-drive": lambda: record_drive(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None, int(sys.argv[4]) if len(sys.argv) > 4 else None), "all": all_actions}
    if command not in actions:
        print(f"usage: {SCRIPT.name} [prepare|run-k0|gate-k0|materialize-main|run-main|analyze|qa|viz|package|record-drive FILE_ID [URL] [BYTES]|all]", file=sys.stderr)
        return 2
    if command == "record-drive" and len(sys.argv) < 3:
        return 2
    actions[command]()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
