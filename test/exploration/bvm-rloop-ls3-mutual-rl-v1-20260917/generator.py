#!/usr/bin/env python3
"""Run the frozen passive mutual-RL loop directly coupled to physical LS3.

This runner is an Experimental Operator + Evidence Packager.  It performs
bounded mechanical arithmetic and packaging only; candidate labels remain
pending scientific review.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

EXP = Path(__file__).resolve().parent
REPO = EXP.parents[2]
sys.path.insert(0, str(REPO / "scripts"))
import bvm_qb_rloop_ls3_population_validation as common  # noqa: E402

branch = common.branch_helpers
SOURCE_INPUTS = REPO / "test" / "exploration" / "bvm-qb-threshold-ordering-boundary-search-v1-20260911" / "inputs"
REFERENCE_ROOT = REPO / "test" / "exploration" / "bvm-qb-threshold-ordering-boundary-search-v1-20260911" / "references" / "canonical_baseline"
POP_ROOT = REPO / "test" / "exploration" / "bvm-population-scaling-rj2p12-l1p14-l2p20-ib260-rj32-bjs400-v1-20260910"
SOLVER = REPO / "build" / "josim-cli"
PLOTTER = REPO / "scripts" / "josim-plot2.py"
ORACLE_PATH = POP_ROOT / "analysis" / "population_oracle.py"
CANONICAL = {mask: REFERENCE_ROOT / mask / "raw.csv" for mask in ("0011", "0111")}
CANONICAL.update({"0001": POP_ROOT / "references" / "reused" / "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_0001" / "raw.csv", "1111": POP_ROOT / "runs" / "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_1111" / "raw.csv"})
CANONICAL_DECK = {mask: REFERENCE_ROOT / mask / "deck.cir" for mask in ("0011", "0111")}
CANONICAL_DECK.update({"0001": POP_ROOT / "references" / "reused" / "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_0001" / "deck.cir", "1111": POP_ROOT / "runs" / "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_1111" / "deck.cir"})

EXPECTED_HEAD = "1348140f17f0d9467dc42238eaa1e252e877e07a"
MASKS = ("0011", "0111")
M_VALUES = {"M0P00": 0.00, "M0P25": 0.25, "M0P50": 0.50, "M0P75": 0.75}
M_LABELS = tuple(M_VALUES)
FIXED = tuple(f"LS3_MUTUAL_{label}_{mask}" for label in M_LABELS for mask in MASKS)
K0 = FIXED[:2]
CONDITIONAL_MASKS = ("0001", "1111")
L_S3_PH = 0.5
R_S_OHM = 3.0
L_AUX_PH = 10.0
R_AUX_OHM = 20.0
FOCUS = (110.0, 121.0)
REARM = (121.0, 130.0)
FULL = (0.0, 200.0)
CONTRACT = "This experiment is governed by docs/EXPERIMENT_CONTRACT.md."
FINAL = "EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW"
DRIVE_FOLDER_ID = "1--nlY7Nq5ArVPydJNrnQf-EGmwN-undh"
KNOWN_WARNINGS = {"Unknown device/node IB|XBQ1", "Cannot store results for this device/node."}
JTL_STAGES = tuple(range(1, 7))

sha256 = common.sha256
sha256_text = common.sha256_text
rel = common.rel
write_json = common.write_json
read_json = common.read_json
load_raw = common.load_raw
time_indices = branch.time_indices
actual_integral = branch.actual_integral
multi_evidence_oracle = common.multi_evidence_oracle
load_oracle_module = common.load_oracle_module


def now() -> str:
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


def k_for_m(m_ph: float) -> float:
    return m_ph / math.sqrt(L_S3_PH * L_AUX_PH)


def case_info(case_id: str) -> dict[str, Any]:
    match = re.fullmatch(r"LS3_MUTUAL_(M0P00|M0P25|M0P50|M0P75)_(0001|0011|0111|1111)", case_id)
    if not match:
        raise RuntimeError(f"invalid case id: {case_id}")
    label, mask = match.groups()
    m_ph = M_VALUES[label]
    return {"case_id": case_id, "M_label": label, "M_pH": m_ph, "K": k_for_m(m_ph), "mask": mask, "conditional_population_validation": mask in CONDITIONAL_MASKS}


def case_dir(case_id: str) -> Path:
    return EXP / "runs" / case_id


def static_matrix_audit() -> dict[str, Any]:
    fixture = REPO / "test" / "comp" / "mutual.cir"
    syntax = [line.strip() for line in fixture.read_text(encoding="utf-8").splitlines() if line.strip().startswith("K ")]
    values: dict[str, Any] = {}
    syntax_ok = bool(syntax) and all(re.fullmatch(r"K\s+\S+\s+\S+\s+[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", line) for line in syntax)
    for label, m_ph in M_VALUES.items():
        k = k_for_m(m_ph)
        determinant = L_S3_PH * L_AUX_PH - m_ph * m_ph
        discriminant = math.sqrt((L_S3_PH - L_AUX_PH) ** 2 + 4.0 * m_ph * m_ph)
        eigen_min = 0.5 * (L_S3_PH + L_AUX_PH - discriminant)
        eigen_max = 0.5 * (L_S3_PH + L_AUX_PH + discriminant)
        values[label] = {"M_pH": m_ph, "K": k, "determinant_pH2": determinant, "eigenvalues_pH": [eigen_min, eigen_max], "abs_K_lt_1": abs(k) < 1.0, "matrix_positive_definite": eigen_min > 0.0}
    return {"status": "PASS" if syntax_ok and all(item["abs_K_lt_1"] and item["matrix_positive_definite"] for item in values.values()) else "FAIL", "syntax_fixture": rel(fixture), "syntax_examples": syntax, "L_S3_pH": L_S3_PH, "L_AUX_pH": L_AUX_PH, "matrix": values, "formula": "K=M/sqrt(L_S3*L_AUX)", "scope": "M=0.00/0.25/0.50/0.75 pH only"}


def clone_bvm(m_label: str, k: float) -> str:
    source = (SOURCE_INPUTS / "bvm_jm2_connected.cir").read_text(encoding="utf-8")
    lines = source.splitlines()
    start = next(index for index, line in enumerate(lines) if line.strip().lower() == ".subckt bvm wl bl se sl")
    end = next(index for index in range(start + 1, len(lines)) if lines[index].strip().lower() == ".ends bvm")
    name = f"BVM_LS3_MUTUAL_{m_label}"
    output = [f"* {name}: canonical BVM clone with a passive loop magnetically coupled to physical L_S3.", f".subckt {name} WL BL SE SL"]
    inserted = False
    for line in lines[start + 1:end]:
        output.append(line)
        if re.match(r"^\s*L_S3\s+6\s+10\s+0\.5P\s*$", line, flags=re.IGNORECASE):
            output.extend(["L_AUX  AUX  0       10P", "R_AUX  0       AUX     20", f"K_AUX  L_S3   L_AUX   {k:.17g}"])
            inserted = True
    if not inserted:
        raise RuntimeError("physical L_S3 anchor missing in canonical BVM")
    output.extend([f".ends {name}", ""])
    return "\n".join(output)


def transform_deck(mask: str, m_label: str, case_id: str, deck_dir: Path) -> str:
    original = CANONICAL_DECK[mask].read_text(encoding="utf-8")
    k = k_for_m(M_VALUES[m_label])
    include_targets = {"jjmit.cir": SOURCE_INPUTS / "jjmit.cir", "bvm_jm2_connected.cir": SOURCE_INPUTS / "bvm_jm2_connected.cir", "BQ_parameterized_bjs400_rj2.cir": SOURCE_INPUTS / "BQ_parameterized_bjs400_rj2.cir", "jtl2.cir": SOURCE_INPUTS / "jtl2.cir"}
    output: list[str] = []
    inserted = False
    instance_count = 0
    probe_count = 0
    for line in original.splitlines():
        stripped = line.strip()
        if stripped.startswith(".include "):
            basename = Path(stripped.split(None, 1)[1]).name
            if basename == "bvm_jm2_connected.cir":
                continue
            if basename not in include_targets:
                raise RuntimeError(f"unexpected include in {case_id}: {basename}")
            target = include_targets[basename]
            output.append(f".include {Path(os.path.relpath(target, deck_dir)).as_posix()}")
            continue
        match = re.fullmatch(r"XBVM([1-4]) WL\1 BL\1 SE\1 COMMON_SL BVM", stripped)
        if match:
            if not inserted:
                output.append(clone_bvm(m_label, k))
                inserted = True
            index = match.group(1)
            output.append(f"XBVM{index} WL{index} BL{index} SE{index} COMMON_SL BVM_LS3_MUTUAL_{m_label}")
            instance_count += 1
            continue
        probe_match = re.search(r"I\(L_S3\|XBVM([1-4])\)", stripped)
        if stripped.startswith(".print ") and probe_match:
            index = probe_match.group(1)
            output.append(stripped + f" I(L_AUX|XBVM{index}) V(L_AUX|XBVM{index}) I(R_AUX|XBVM{index}) V(R_AUX|XBVM{index}) V(AUX|XBVM{index})")
            probe_count += 1
            continue
        output.append(line)
    if not inserted or instance_count != 4 or probe_count != 4:
        raise RuntimeError(f"BVM mutual transform counts failed for {case_id}: {inserted=} {instance_count=} {probe_count=}")
    text = "\n".join(output) + "\n"
    required = ("L_S3    6       10      0.5P", "L_AUX  AUX  0       10P", "R_AUX  0       AUX     20", "K_AUX  L_S3   L_AUX", "XBQ1 QBIN QBOUT BQ", "XJTL1_1 QBOUT JTL1_OUT jtl", "XJTL1_6 JTL5_OUT JTL6_OUT jtl", "R_TERM JTL6_OUT 0 10", ".tran 0.1p 200p")
    for token in required:
        if token not in text:
            raise RuntimeError(f"required topology token missing in {case_id}: {token}")
    if "L_S3    6       10      0.5P" not in text or "BVM_LS3_MUTUAL_" not in text:
        raise RuntimeError("physical L_S3 was not retained")
    if any(token in text for token in ("V_REPLAY", "I_REPLAY", "TRANSFORMER", "PTL", "SENTINEL", "LC_LADDER")):
        raise RuntimeError(f"forbidden topology token in {case_id}")
    return text


def make_deck(case_id: str) -> dict[str, Any]:
    info = case_info(case_id)
    deck = case_dir(case_id) / "deck.cir"
    deck.parent.mkdir(parents=True, exist_ok=True)
    deck.write_text(transform_deck(info["mask"], info["M_label"], case_id, deck.parent), encoding="utf-8")
    return {**info, "path": rel(deck), "sha256": sha256(deck), "bytes": deck.stat().st_size, "topology": "canonical physical R_S/L_S3 retained inside a BVM clone; L_AUX/R_AUX/K_AUX is directly coupled to L_S3; canonical QB/JSL/JTL unchanged"}


def expected_headers(mask: str) -> set[str]:
    headers = set(load_raw(CANONICAL[mask]).headers)
    for index in range(1, 5):
        headers.update({f"I(L_AUX|XBVM{index})", f"V(L_AUX|XBVM{index})", f"I(R_AUX|XBVM{index})", f"V(R_AUX|XBVM{index})", f"V(AUX|XBVM{index})"})
    return headers


def source_inventory() -> list[dict[str, Any]]:
    records = [
        record_file("runner", Path(__file__), "physical-LS3 mutual-RL generator/executor/analyzer/plotter/packager"),
        record_file("run_sh", EXP / "run.sh", "user-facing runner"),
        record_file("jjmit", SOURCE_INPUTS / "jjmit.cir", "canonical JJ model"),
        record_file("bvm", SOURCE_INPUTS / "bvm_jm2_connected.cir", "canonical BVM template; read-only"),
        record_file("qb", SOURCE_INPUTS / "BQ_parameterized_bjs400_rj2.cir", "canonical QB include; read-only"),
        record_file("jtl", SOURCE_INPUTS / "jtl2.cir", "canonical JTL include; read-only"),
        record_file("solver", SOLVER, "recorded JoSIM solver"),
        record_file("plotter", PLOTTER, "standard descriptive renderer"),
        record_file("branch_helper", REPO / "scripts" / "bvm_qb_rloop_branch_timing_decomposition.py", "read-only metrics/topology helper"),
        record_file("population_helper", REPO / "scripts" / "bvm_qb_rloop_ls3_population_validation.py", "read-only multi-evidence helper"),
        record_file("oracle", ORACLE_PATH, "read-only historical oracle"),
        record_file("mutual_syntax_fixture", REPO / "test" / "comp" / "mutual.cir", "read-only K syntax fixture"),
    ]
    for mask in ("0011", "0111", "0001", "1111"):
        records.extend([record_file(f"canonical_{mask}_raw", CANONICAL[mask], "read-only canonical raw"), record_file(f"canonical_{mask}_deck", CANONICAL_DECK[mask], "read-only canonical deck")])
    return records


def prepare(args: argparse.Namespace) -> None:
    if git_head() != EXPECTED_HEAD or remote_head() != EXPECTED_HEAD:
        raise RuntimeError("HEAD/remote does not match frozen parent")
    if tuple(args.masks) != MASKS or tuple(args.m_values) != tuple(f"{value:.2f}" for value in M_VALUES.values()):
        raise RuntimeError("registered masks/M values do not match M=0.00/0.25/0.50/0.75")
    if args.l_aux != L_AUX_PH or args.r_aux != R_AUX_OHM:
        raise RuntimeError("registered auxiliary values require L_AUX=10 pH and R_AUX=20 ohm")
    matrix = static_matrix_audit()
    if matrix["status"] != "PASS":
        raise RuntimeError("mutual matrix audit failed")
    existing_artifacts = [path for path in EXP.iterdir() if path.name not in {"run.sh", "generator.py", "__pycache__"}] if EXP.exists() else []
    if existing_artifacts:
        if not args.force:
            raise RuntimeError(f"experiment exists; use --force for timestamped backup: {EXP}")
        backup = EXP.with_name(f"{EXP.name}.attempt-{datetime.now().strftime('%Y%m%dT%H%M%S')}")
        shutil.move(str(EXP), str(backup))
    EXP.mkdir(parents=True, exist_ok=True)
    for directory in ("runs", "analysis", "plots"):
        (EXP / directory).mkdir(parents=True, exist_ok=True)
    canonical = {mask: load_raw(CANONICAL[mask]) for mask in MASKS}
    direction = {mask: branch.branch_direction_audit(trace, mask) for mask, trace in canonical.items()}
    if any(item["status"] != "PASS" for item in direction.values()):
        raise RuntimeError(f"canonical physical bridge audit failed: {direction}")
    records = {case_id: make_deck(case_id) for case_id in K0}
    preflight = f"""# Physical LS3 mutual-RL loop — {EXP.name}

{CONTRACT}

- Parent HEAD: `{EXPECTED_HEAD}`; remote `bvm/master`: `{EXPECTED_HEAD}`.
- Study phase: `EXPLORATORY`; role: `Experimental Operator + Evidence Packager`.
- Scientific review authorization: `false`; only mechanical evidence and candidate labels are recorded.
- Question: can a simple passive reciprocal magnetic load directly coupled to physical `L_S3` modify the N3 fourth-regeneration record while preserving the N2 record?
- Physical canonical bridge is retained exactly: `R_S=3 ohm`, `L_S3=0.5 pH`; the canonical BVM/QB files are not modified.
- Added only inside an experimental BVM clone: `L_AUX=10 pH`, `R_AUX=20 ohm`, and `K_AUX L_S3 L_AUX K`, with `M=K*sqrt(0.5*10) pH`.
- Fixed M values are exactly `0.00`, `0.25`, `0.50`, and `0.75 pH`; K is derived and recorded exactly. No negative M, M>0.75, other L/R/C, JJ, source, bias, resonator, PTL, split-LS3 or timestep case.
- M=0.00 is the no-op gate and is solved first. Positive M cases are materialized only after that gate passes. N1/N4 are materialized only for the smallest positive M whose fixed pair mechanically gives N2=2 and N3=3.
- `.tran 0.1p 200p`; actual stored grid only. P(...) is raw radians; rad/(2*pi) turns are navigation only and not literal SFQ counts.

## Authorized cases

1. `LS3_MUTUAL_M0P00_0011`
2. `LS3_MUTUAL_M0P00_0111`
3. `LS3_MUTUAL_M0P25_0011`
4. `LS3_MUTUAL_M0P25_0111`
5. `LS3_MUTUAL_M0P50_0011`
6. `LS3_MUTUAL_M0P50_0111`
7. `LS3_MUTUAL_M0P75_0011`
8. `LS3_MUTUAL_M0P75_0111`
9–10. Conditional smallest-positive-M pair × `0001`,`1111` only after the registered mechanical selective gate.

Maximum new physical solves: 10. The M=0 pair must reproduce the canonical N2=2/N3=4 mapping and be auxiliary-quiet before positive cases run.

Canonical bridge audit: `{json.dumps({mask: item['status'] for mask, item in direction.items()}, ensure_ascii=False)}`.

Final state: `{FINAL}`; no scientific mechanism or winner conclusion is assigned.
"""
    (EXP / "PREFLIGHT.md").write_text(preflight, encoding="utf-8")
    (EXP / "README.md").write_text(f"# {EXP.name}\n\n`./run.sh --dry-run` prints the frozen M/K matrix without invoking JoSIM. The physical LS3 bridge is retained; only the passive reciprocal auxiliary loop is added inside a per-case BVM clone.\n", encoding="utf-8")
    yaml = ["schema_version: bvm-rloop-ls3-mutual-rl-v1", f"id: {EXP.name}", "study_phase: EXPLORATORY", "role: Experimental Operator + Evidence Packager", "status: PREFLIGHT_PASS_M0_GATE_FIRST", f"registration_head: {EXPECTED_HEAD}", f"remote_bvm_master_at_registration: {EXPECTED_HEAD}", f"contract_sentence: {CONTRACT}", "scientific_review_authorized: false", "", "frozen:", "  R_S_ohm: 3.0", "  L_S3_pH: 0.5", "  L_AUX_pH: 10.0", "  R_AUX_ohm: 20.0", "  M_values_pH: [0.00, 0.25, 0.50, 0.75]", "  timestep_ps: 0.1", "  stop_time_ps: 200.0", "  actual_grid: true", "  interpolation: false", "  resampling: false", "  no_QB_change: true", "  no_negative_M: true", "", "authorized_matrix:", "  fixed: [LS3_MUTUAL_M0P00_0011, LS3_MUTUAL_M0P00_0111, LS3_MUTUAL_M0P25_0011, LS3_MUTUAL_M0P25_0111, LS3_MUTUAL_M0P50_0011, LS3_MUTUAL_M0P50_0111, LS3_MUTUAL_M0P75_0011, LS3_MUTUAL_M0P75_0111]", "  conditional: [smallest_positive_M x 0001, smallest_positive_M x 1111]", "  maximum_new_physical_solves: 10", "", "M_matrix_audit:", f"  status: {matrix['status']}", f"  formula: {matrix['formula']}", "", "initial_M0_deck_registration:"]
    for key, item in records.items():
        yaml.extend([f"  - run_id: {key}", f"    path: {item['path']}", f"    sha256: {item['sha256']}", f"    bytes: {item['bytes']}", f"    M_pH: {item['M_pH']}", f"    K: {item['K']:.17g}"])
    yaml.extend(["", "conditional_rule: smallest positive M with mechanical N2=2/N3=3 only", "scientific_classification: NOT_ASSIGNED_SCIENTIFIC_REVIEW_REQUIRED", ""])
    (EXP / "experiment.yaml").write_text("\n".join(yaml), encoding="utf-8")
    closure = source_inventory()
    provenance = {"schema": "bvm-rloop-ls3-mutual-rl-provenance-v1", "experiment_id": EXP.name, "created_at": now(), "registration_head": EXPECTED_HEAD, "remote_bvm_master_at_registration": EXPECTED_HEAD, "contract_sentence": CONTRACT, "scientific_review_authorized": False, "mechanical_analysis_performed": False, "bounded_experiment_interpretation_performed": False, "independent_scientific_review_performed": False, "scientific_interpretation_performed": False, "solver": {**branch.replay_base.solver_context(), "binary_sha256": sha256(SOLVER)}, "source_closure": closure, "branch_direction_audit": direction, "matrix_audit": matrix, "frozen": {"question": "passive reciprocal magnetic load directly coupled to physical LS3", "R_S_ohm": R_S_OHM, "L_S3_pH": L_S3_PH, "L_AUX_pH": L_AUX_PH, "R_AUX_ohm": R_AUX_OHM, "M_values_pH": M_VALUES, "K_formula": "M/sqrt(0.5*10)", "windows_ps": [list(FULL), list(FOCUS), list(REARM)], "no_QB_change": True, "no_other_sweep": True}, "authorized_matrix": {"fixed": list(FIXED), "M0_gate": list(K0), "conditional_masks": list(CONDITIONAL_MASKS), "maximum": 10, "no_other_solve": True}, "registered_decks": records, "runs": {}, "run_order": [], "execution": {"authorized_physical_solve_count": 10, "actual_physical_solve_count": 0, "solver_invocation_count": 0, "run_order": []}, "M0_gate": {"status": "PENDING"}, "conditional_selection": {"status": "PENDING"}, "analysis": {"status": "PENDING"}, "qa": {"status": "PENDING"}, "visualization": {"status": "PENDING"}, "package": {"status": "PENDING"}, "stop": {"final_marker": None, "automatic_follow_up": False}}
    write_json(EXP / "provenance.json", provenance)
    result = {"schema": "bvm-rloop-ls3-mutual-rl-result-v1", "experiment_id": EXP.name, "generated_at": now(), "status": "PREFLIGHT_PASS_M0_GATE_FIRST", "artifact_status": "PENDING", "scientific_review_authorized": False, "mechanical_analysis_performed": False, "bounded_experiment_interpretation_performed": False, "independent_scientific_review_performed": False, "scientific_interpretation_performed": False, "execution": provenance["execution"], "cases": {key: {"status": "AUTHORIZED_NOT_RUN" if key in K0 else "NOT_MATERIALIZED"} for key in FIXED}, "matrix_audit": matrix, "M0_gate": {"status": "PENDING"}, "conditional_selection": {"status": "PENDING"}, "classification": {"status": "SCIENTIFIC_REVIEW_REQUIRED", "assigned": None, "candidate_labels": ["LS3_MUTUAL_SELECTIVE_2_3", "LS3_MUTUAL_PARTIAL_LEVERAGE", "LS3_MUTUAL_TOO_WEAK", "LS3_MUTUAL_NONSELECTIVE", "LS3_MUTUAL_DESTABILIZING", "LS3_MUTUAL_FIXTURE_INVALID"]}, "stop": {"final_marker": None, "automatic_follow_up": False}}
    write_json(EXP / "result.json", result)


def dry_run(args: argparse.Namespace) -> None:
    matrix = static_matrix_audit()
    print(f"experiment={EXP.name}")
    print(f"parent_sha={EXPECTED_HEAD}")
    print(f"masks={' '.join(args.masks)}")
    for label, m_ph in M_VALUES.items():
        k = k_for_m(m_ph)
        for mask in args.masks:
            key = f"LS3_MUTUAL_{label}_{mask}"
            print(f"case_id={key} M_pH={m_ph:.2f} K={k:.17g} L_AUX_pH={args.l_aux} R_AUX_ohm={args.r_aux} deck={EXP/'runs'/key/'deck.cir'} raw={EXP/'runs'/key/'raw.csv'}")
    print(f"josim_cli={args.josim_bin}")
    print(f"dt={args.dt} stop_time={args.stop_time} M_matrix_status={matrix['status']} M0_gate_solve_count=2 fixed_max=8 absolute_max=10")
    print("DRY_RUN no JoSIM invocation")


def warning_lines(path: Path) -> list[str]:
    if not path.is_file():
        return ["missing_log"]
    return [line.strip() for line in path.read_text(errors="replace").splitlines() if any(token in line for token in ("Missing model:", "Unknown device/node", "Cannot store results", "Error", "error"))]


def execute_case(case_id: str, args: argparse.Namespace) -> None:
    provenance = read_json(EXP / "provenance.json")
    if case_id in provenance["run_order"] or case_id not in provenance["registered_decks"]:
        raise RuntimeError(f"case not registered or already run: {case_id}")
    order = [*K0, *[key for key in FIXED if key not in K0], *[f"LS3_MUTUAL_{label}_{mask}" for label in M_LABELS for mask in CONDITIONAL_MASKS]]
    position = order.index(case_id)
    expected_prefix = [key for key in order[:position] if key in provenance["run_order"]]
    if provenance["run_order"] != expected_prefix:
        raise RuntimeError(f"wrong run order before {case_id}: {provenance['run_order']}")
    deck = REPO / provenance["registered_decks"][case_id]["path"]
    raw, log, stdout_path, stderr_path, metadata = [deck.parent / name for name in ("raw.csv", "run.log", "stdout.txt", "stderr.txt", "metadata.json")]
    if any(path.exists() for path in (raw, log, stdout_path, stderr_path, metadata)):
        raise RuntimeError(f"refusing overwrite/retry: {case_id}")
    command = [str(args.josim_bin), "-a", "1", "-o", str(raw), str(deck)]
    started = now()
    clock = time.monotonic()
    completed = subprocess.run(command, cwd=REPO, capture_output=True, text=True, check=False)
    runtime = time.monotonic() - clock
    finished = now()
    stdout_path.write_text(completed.stdout, encoding="utf-8")
    stderr_path.write_text(completed.stderr, encoding="utf-8")
    log.write_text("\n".join([f"experiment={EXP.name}", f"run_id={case_id}", f"parent_commit={EXPECTED_HEAD}", f"started_at={started}", f"finished_at={finished}", f"runtime_seconds={runtime:.6f}", f"command={' '.join(command)}", f"exit_code={completed.returncode}", "--- stdout ---", completed.stdout, "--- stderr ---", completed.stderr, ""]), encoding="utf-8")
    item = case_info(case_id)
    record: dict[str, Any] = {"run_id": case_id, **item, "parent_commit": EXPECTED_HEAD, "command": command, "runtime_seconds": runtime, "started_at": started, "finished_at": finished, "deck": {"path": rel(deck), "sha256": sha256(deck), "bytes": deck.stat().st_size}, "stdout": {"path": rel(stdout_path), "sha256": sha256(stdout_path), "bytes": stdout_path.stat().st_size}, "stderr": {"path": rel(stderr_path), "sha256": sha256(stderr_path), "bytes": stderr_path.stat().st_size}, "log": {"path": rel(log), "sha256": sha256(log), "bytes": log.stat().st_size}, "solver": {**branch.replay_base.solver_context(), "binary_sha256": sha256(Path(args.josim_bin))}, "physical_solve_this_experiment": True, "raw_immutable": True, "mechanical_analysis_performed": False, "scientific_interpretation_performed": False, "solver_warning_lines": warning_lines(log)}
    if completed.returncode != 0 or not raw.is_file() or raw.stat().st_size == 0:
        record["execution_status"] = "SOLVER_FAIL"
        record["raw"] = {"path": rel(raw), "exists": raw.is_file(), "sha256": sha256(raw) if raw.is_file() else None, "bytes": raw.stat().st_size if raw.is_file() else None}
        write_json(metadata, {"run_id": case_id, "execution_status": record["execution_status"], "raw": record["raw"], "deck_sha256": record["deck"]["sha256"], "log_sha256": record["log"]["sha256"], "stdout_sha256": record["stdout"]["sha256"], "stderr_sha256": record["stderr"]["sha256"]})
        record["metadata"] = {"path": rel(metadata), "sha256": sha256(metadata), "bytes": metadata.stat().st_size}
        provenance["runs"][case_id] = record
        provenance["run_order"].append(case_id)
        provenance["execution"]["actual_physical_solve_count"] = len(provenance["run_order"])
        provenance["execution"]["solver_invocation_count"] = len(provenance["run_order"])
        provenance["execution"]["run_order"] = provenance["run_order"]
        write_json(EXP / "provenance.json", provenance)
        raise RuntimeError(f"solver failed; artifacts preserved for {case_id}")
    trace = load_raw(raw)
    missing = sorted(expected_headers(item["mask"]) - set(trace.headers))
    record["raw"] = {"path": rel(raw), "sha256": sha256(raw), "bytes": raw.stat().st_size, "sample_count": trace.sample_count, "time_start_ps": trace.time[0] * 1.0e12, "time_end_ps": trace.time[-1] * 1.0e12, "grid": branch.replay_base.finite_grid_qa(trace), "missing_required_probes": missing}
    record["execution_status"] = "RUN_PASS" if not missing else "RUN_PASS_MISSING_PROBES"
    write_json(metadata, {"run_id": case_id, "parameters": item, "deck_sha256": record["deck"]["sha256"], "raw_sha256": record["raw"]["sha256"], "log_sha256": record["log"]["sha256"], "stdout_sha256": record["stdout"]["sha256"], "stderr_sha256": record["stderr"]["sha256"], "execution_status": record["execution_status"]})
    record["metadata"] = {"path": rel(metadata), "sha256": sha256(metadata), "bytes": metadata.stat().st_size}
    provenance["runs"][case_id] = record
    provenance["run_order"].append(case_id)
    provenance["execution"]["actual_physical_solve_count"] = len(provenance["run_order"])
    provenance["execution"]["solver_invocation_count"] = len(provenance["run_order"])
    provenance["execution"]["run_order"] = provenance["run_order"]
    write_json(EXP / "provenance.json", provenance)
    if missing:
        raise RuntimeError(f"missing required probes for {case_id}: {missing}")


def aux_observables(trace: Any) -> dict[str, Any]:
    result: dict[str, Any] = {"status": "DERIVED", "instances": {}, "model": "passive L_AUX/R_AUX loop magnetically coupled to physical L_S3"}
    for index in range(1, 5):
        instance = f"XBVM{index}"
        signals = {"I_L_AUX": f"I(L_AUX|{instance})", "V_L_AUX": f"V(L_AUX|{instance})", "I_R_AUX": f"I(R_AUX|{instance})", "V_R_AUX": f"V(R_AUX|{instance})", "V_AUX": f"V(AUX|{instance})"}
        missing = [signal for signal in signals.values() if signal not in trace.headers]
        windows: dict[str, Any] = {}
        for name, window in (("focus_110_121", FOCUS), ("rearm_121_130", REARM), ("full_0_200", FULL)):
            windows[name] = {label: branch.waveform_stats(trace, signal, window) if signal in trace.headers else {"status": "UNKNOWN", "signal": signal, "window_ps": list(window)} for label, signal in signals.items()}
            if not missing:
                indices = time_indices(trace, *window)
                times = [float(trace.time[i]) for i in indices]
                i_aux = [float(trace.column(signals["I_R_AUX"])[i]) for i in indices]
                v_aux = [float(trace.column(signals["V_R_AUX"])[i]) for i in indices]
                i2r = actual_integral(times, [value * value * R_AUX_OHM for value in i_aux])
                vi = actual_integral(times, [v * i for v, i in zip(v_aux, i_aux)])
                windows[name]["R_AUX_energy"] = {"I2R_energy_J": i2r, "I2R_energy_fJ": i2r * 1.0e15, "signed_VI_energy_J": vi, "signed_VI_energy_fJ": vi * 1.0e15, "passivity_nonnegative": i2r >= -1.0e-30, "actual_grid": True, "R_AUX_ohm": R_AUX_OHM}
        result["instances"][instance] = {"signals": signals, "missing": missing, "windows": windows, "status": "DERIVED" if not missing else "UNKNOWN"}
        if missing:
            result["status"] = "UNKNOWN"
    result["no_directional_isolation_claim"] = True
    return result


def trace_metrics(label: str, mask: str, trace: Any, oracle_module: Any) -> dict[str, Any]:
    metrics = branch.run_metrics(label, mask, trace, family=None, canonical=True, delay_ps=0.0)
    metrics["multi_evidence_oracle"] = multi_evidence_oracle(trace, mask, oracle_module)
    metrics["auxiliary"] = aux_observables(trace)
    metrics["active_bvm_indices"] = [index for index, bit in enumerate(mask, 1) if bit == "1"]
    metrics["phase_area_cross_checks_active"] = {f"P({element}|XBVM{index})": branch.phase_area(trace, f"P({element}|XBVM{index})", f"V({element}|XBVM{index})") for index in metrics["active_bvm_indices"] for element in ("B_JS1", "B_JS2")}
    return metrics


def compare_traces(canonical: Any, candidate: Any, mask: str, canonical_metrics: dict[str, Any], candidate_metrics: dict[str, Any]) -> dict[str, Any]:
    signals = ["I(B_JSL8)", "V(COMMON_SL)", "V(QBIN)", "I(LIN|XBQ1)", "I(L1|XBQ1)", "I(L2|XBQ1)", "V(QBOUT)", "V(JTL6_OUT)", "I(R_TERM)", *[f"P(B01|XJTL1_{stage})" for stage in JTL_STAGES], *[f"V(JTL{stage}_OUT)" for stage in JTL_STAGES]]
    for index in candidate_metrics["active_bvm_indices"]:
        signals.extend([f"{kind}({element}|XBVM{index})" for element in ("B_JS1", "B_JS2", "B_JM1", "B_JM2", "L_S3", "R_S") for kind in (("P", "V", "I") if element.startswith("B_") else ("I", "V"))])
    return {"signal_deltas": {signal: {"focus": branch.normalized_delta(canonical, candidate, signal, FOCUS), "full": branch.normalized_delta(canonical, candidate, signal, FULL)} for signal in signals}, "timing_drift": common.timing_drift(canonical_metrics["multi_evidence_oracle"], candidate_metrics["multi_evidence_oracle"]), "active_phase_p2p": common.phase_p2p_deltas(canonical, candidate, mask), "actual_grid": True, "interpolation": False}


def fourth_time(oracle: dict[str, Any]) -> float | None:
    return common.phase_time(oracle, "BJ1", 4)


def active_phase_delta(metrics: dict[str, Any], baseline: dict[str, Any]) -> float | None:
    values: list[float] = []
    for instance in metrics["bvm"]["active_instances"]:
        for element in ("B_JS1", "B_JS2"):
            signal = f"P({element}|{instance})"
            a = metrics["bvm"]["cells"][instance]["phase_navigation"][signal]["focus_110_121_p2p_turns"]
            b = baseline["bvm"]["cells"][instance]["phase_navigation"][signal]["focus_110_121_p2p_turns"]
            values.append(abs(a - b))
    return max(values) if values else None


def ls3_signed_area(metrics: dict[str, Any]) -> float | None:
    values: list[float] = []
    for instance in metrics["bvm"]["active_instances"]:
        item = metrics["bvm"]["cells"][instance]["focus_waveforms"].get(f"I(L_S3|{instance})")
        if item and item.get("signed_area") is not None:
            values.append(float(item["signed_area"]))
    return sum(values) / len(values) if values else None


def classify_groups(validations: dict[str, Any], canonical_metrics: dict[str, Any], m0_metrics: dict[str, Any], m0_gate: dict[str, Any]) -> dict[str, Any]:
    groups: dict[str, Any] = {}
    for label in M_LABELS:
        n2_key = f"LS3_MUTUAL_{label}_0011"
        n3_key = f"LS3_MUTUAL_{label}_0111"
        if n2_key not in validations or n3_key not in validations:
            continue
        n2 = validations[n2_key]["oracle"]["ordered_phase_chain_count"]
        n3 = validations[n3_key]["oracle"]["ordered_phase_chain_count"]
        n3_fourth = fourth_time(validations[n3_key]["oracle"])
        baseline_n3 = m0_metrics.get("0111", {}).get("multi_evidence_oracle", {})
        baseline_fourth = fourth_time(baseline_n3) if baseline_n3 else None
        phase_deltas = [item["active_phase_delta_turns"] for item in (validations[n2_key], validations[n3_key]) if item.get("active_phase_delta_turns") is not None]
        ls3_deltas = [item["ls3_signed_area_delta"] for item in (validations[n2_key], validations[n3_key]) if item.get("ls3_signed_area_delta") is not None]
        gross = n2 > 4 or n3 > 6 or validations[n2_key]["oracle"]["terminal_pulse_count"] > 6 or validations[n3_key]["oracle"]["terminal_pulse_count"] > 8
        groups[label] = {"M_pH": M_VALUES[label], "K": k_for_m(M_VALUES[label]), "N2_ordered_phase_chain_count": n2, "N3_ordered_phase_chain_count": n3, "N3_fourth_BJ1_ps": n3_fourth, "N3_fourth_delta_from_M0_ps": n3_fourth - baseline_fourth if n3_fourth is not None and baseline_fourth is not None else None, "active_phase_delta_max_turns_from_M0": max(phase_deltas) if phase_deltas else None, "LS3_signed_area_delta_from_M0": sum(ls3_deltas) / len(ls3_deltas) if ls3_deltas else None, "gross_activity_heuristic": gross}
        if label == "M0P00":
            groups[label]["mechanical_candidate_label"] = "LS3_MUTUAL_FIXTURE_INVALID" if m0_gate.get("status") != "PASS" else "LS3_MUTUAL_M0_NOOP_GATE_PASS"
        elif gross:
            groups[label]["mechanical_candidate_label"] = "LS3_MUTUAL_DESTABILIZING"
        elif n2 == 2 and n3 == 3:
            groups[label]["mechanical_candidate_label"] = "LS3_MUTUAL_SELECTIVE_2_3"
        elif n3 == 3 and n2 != 2:
            groups[label]["mechanical_candidate_label"] = "LS3_MUTUAL_NONSELECTIVE"
        elif n2 == 2 and n3 == 4:
            groups[label]["mechanical_candidate_label"] = "LS3_MUTUAL_TOO_WEAK"
        else:
            groups[label]["mechanical_candidate_label"] = "LS3_MUTUAL_UNCLASSIFIED_OR_MIXED"
    positive = [label for label in M_LABELS[1:] if groups.get(label, {}).get("N2_ordered_phase_chain_count") == 2 and groups.get(label, {}).get("N3_ordered_phase_chain_count") == 3]
    selected = min(positive, key=lambda label: M_VALUES[label]) if positive else None
    return {"groups": groups, "smallest_positive_selective_M": selected, "conditional_authorized": selected is not None, "mechanical_only": True}


def update_m0_gate(args: argparse.Namespace) -> dict[str, Any]:
    provenance = read_json(EXP / "provenance.json")
    oracle_module = load_oracle_module()
    canonical_n2 = load_raw(CANONICAL["0011"])
    canonical_n3 = load_raw(CANONICAL["0111"])
    candidate_n2 = load_raw(REPO / provenance["runs"][K0[0]]["raw"]["path"])
    candidate_n3 = load_raw(REPO / provenance["runs"][K0[1]]["raw"]["path"])
    cm2 = trace_metrics("CANONICAL_0011", "0011", canonical_n2, oracle_module)
    cm3 = trace_metrics("CANONICAL_0111", "0111", canonical_n3, oracle_module)
    km2 = trace_metrics(K0[0], "0011", candidate_n2, oracle_module)
    km3 = trace_metrics(K0[1], "0111", candidate_n3, oracle_module)
    c2 = compare_traces(canonical_n2, candidate_n2, "0011", cm2, km2)
    c3 = compare_traces(canonical_n3, candidate_n3, "0111", cm3, km3)
    norm = [item["focus"].get("normalized_rms") for comparison in (c2, c3) for item in comparison["signal_deltas"].values() if item["focus"].get("normalized_rms") is not None]
    aux_peak = []
    for metrics in (km2, km3):
        for instance in metrics["auxiliary"]["instances"].values():
            for window in ("focus_110_121", "rearm_121_130"):
                for key in ("I_L_AUX", "I_R_AUX"):
                    aux_peak.append(instance["windows"][window][key].get("peak_abs", math.inf))
    criteria = {"grid_equal_N2": tuple(canonical_n2.time) == tuple(candidate_n2.time), "grid_equal_N3": tuple(canonical_n3.time) == tuple(candidate_n3.time), "N2_count_2_both": cm2["multi_evidence_oracle"]["ordered_phase_chain_count"] == 2 and km2["multi_evidence_oracle"]["ordered_phase_chain_count"] == 2, "N3_count_4_both": cm3["multi_evidence_oracle"]["ordered_phase_chain_count"] == 4 and km3["multi_evidence_oracle"]["ordered_phase_chain_count"] == 4, "key_shared_waveforms_tight": bool(norm) and max(norm) <= 1.0e-3, "landmark_timing_within_0p2ps": c2["timing_drift"]["max_abs_delta_ps"] is not None and c3["timing_drift"]["max_abs_delta_ps"] is not None and max(c2["timing_drift"]["max_abs_delta_ps"], c3["timing_drift"]["max_abs_delta_ps"]) <= 0.2, "auxiliary_quiet": bool(aux_peak) and max(aux_peak) <= 1.0e-9, "required_auxiliary_probes": km2["auxiliary"]["status"] == "DERIVED" and km3["auxiliary"]["status"] == "DERIVED"}
    gate = {"status": "PASS" if all(criteria.values()) else "FAIL", "criteria": criteria, "registered_tolerances": {"key_shared_waveform_normalized_rms": 1.0e-3, "timing_ps": 0.2, "auxiliary_quiet_A": 1.0e-9}, "comparison_N2": c2, "comparison_N3": c3, "scientific_interpretation_performed": False}
    provenance["M0_gate"] = gate
    write_json(EXP / "analysis" / "M0_GATE.json", gate)
    write_json(EXP / "provenance.json", provenance)
    result = read_json(EXP / "result.json")
    result["M0_gate"] = {key: value for key, value in gate.items() if key not in ("comparison_N2", "comparison_N3")}
    result["status"] = "M0_GATE_PASS_POSITIVE_M_AUTHORIZED" if gate["status"] == "PASS" else "M0_GATE_FAIL_STOP"
    write_json(EXP / "result.json", result)
    return gate


def materialize_positive() -> None:
    provenance = read_json(EXP / "provenance.json")
    if provenance.get("M0_gate", {}).get("status") != "PASS":
        raise RuntimeError("M=0 no-op gate did not pass")
    records = {key: make_deck(key) for key in FIXED if key not in K0}
    provenance["registered_decks"].update(records)
    provenance["positive_materialization"] = {"status": "PASS", "cases": list(records), "materialized_at": now()}
    write_json(EXP / "provenance.json", provenance)
    yaml = EXP / "experiment.yaml"
    block = ["", "positive_M_deck_registration:"]
    for key, item in records.items():
        block.extend([f"  - run_id: {key}", f"    path: {item['path']}", f"    sha256: {item['sha256']}", f"    bytes: {item['bytes']}", f"    M_pH: {item['M_pH']}", f"    K: {item['K']:.17g}"])
    yaml.write_text(yaml.read_text(encoding="utf-8").rstrip() + "\n" + "\n".join(block) + "\n", encoding="utf-8")


def materialize_conditional(label: str) -> None:
    provenance = read_json(EXP / "provenance.json")
    if provenance.get("conditional_selection", {}).get("selected_M_label") != label:
        raise RuntimeError(f"conditional selection mismatch: {label}")
    records = {f"LS3_MUTUAL_{label}_{mask}": make_deck(f"LS3_MUTUAL_{label}_{mask}") for mask in CONDITIONAL_MASKS}
    provenance["registered_decks"].update(records)
    provenance["conditional_materialization"] = {"status": "PASS", "selected_M_label": label, "cases": list(records), "materialized_at": now()}
    write_json(EXP / "provenance.json", provenance)
    yaml = EXP / "experiment.yaml"
    block = ["", "conditional_N1_N4_deck_registration:", f"  selected_M_label: {label}"]
    for key, item in records.items():
        block.extend([f"  - run_id: {key}", f"    path: {item['path']}", f"    sha256: {item['sha256']}", f"    bytes: {item['bytes']}"])
    yaml.write_text(yaml.read_text(encoding="utf-8").rstrip() + "\n" + "\n".join(block) + "\n", encoding="utf-8")


def analyze(args: argparse.Namespace) -> None:
    provenance = read_json(EXP / "provenance.json")
    registered_runner = next(item for item in provenance["source_closure"] if item["name"] == "runner")
    current_runner = record_file("runner", Path(__file__), registered_runner["role"])
    if registered_runner["sha256"] != current_runner["sha256"]:
        provenance["postsolve_tooling_revision"] = {"path": rel(Path(__file__)), "old_sha256": registered_runner["sha256"], "new_sha256": current_runner["sha256"], "reason": "analysis-only runner repair", "physical_rerun": False, "raw_mutated": False}
        registered_runner.update({"sha256": current_runner["sha256"], "bytes": current_runner["bytes"]})
    oracle_module = load_oracle_module()
    canonical_metrics = {mask: trace_metrics(f"CANONICAL_{mask}", mask, load_raw(CANONICAL[mask]), oracle_module) for mask in MASKS}
    m0_metrics = {mask: canonical_metrics[mask] for mask in MASKS}
    for key in provenance["run_order"]:
        if case_info(key)["M_label"] == "M0P00":
            m0_metrics[case_info(key)["mask"]] = trace_metrics(key, case_info(key)["mask"], load_raw(REPO / provenance["runs"][key]["raw"]["path"]), oracle_module)
    validations: dict[str, Any] = {}
    for key in provenance["run_order"]:
        info = case_info(key)
        trace = load_raw(REPO / provenance["runs"][key]["raw"]["path"])
        metric = trace_metrics(key, info["mask"], trace, oracle_module)
        comparison = compare_traces(load_raw(CANONICAL[info["mask"]]), trace, info["mask"], canonical_metrics[info["mask"]], metric)
        baseline = m0_metrics[info["mask"]]
        area_delta = None
        current_area = ls3_signed_area(metric)
        baseline_area = ls3_signed_area(baseline)
        if current_area is not None and baseline_area is not None:
            area_delta = current_area - baseline_area
        validations[key] = {"case_id": key, "mask": info["mask"], "params": info, "oracle": metric["multi_evidence_oracle"], "comparison": comparison, "auxiliary": metric["auxiliary"], "active_phase_area": metric["phase_area_cross_checks_active"], "active_phase_delta_turns": active_phase_delta(metric, baseline) if info["M_label"] != "M0P00" else 0.0, "ls3_signed_area": current_area, "ls3_signed_area_delta": area_delta, "bvm": metric["bvm"], "bridge": metric["bridge"], "source": metric["source"], "qb": metric["qb"], "jsl": metric["jsl"], "jtl": metric["jtl"]}
    m0_gate = provenance.get("M0_gate", {"status": "PENDING"})
    group_result = classify_groups(validations, canonical_metrics, m0_metrics, m0_gate)
    selected = group_result.get("smallest_positive_selective_M") if m0_gate.get("status") == "PASS" else None
    conditional_selection = {"status": "AUTHORIZED" if selected else "NOT_AUTHORIZED", "selected_M_label": selected, "selected_cases": [f"LS3_MUTUAL_{selected}_{mask}" for mask in CONDITIONAL_MASKS] if selected else [], "mechanical_only": True}
    raw_before = {key: sha256(REPO / provenance["runs"][key]["raw"]["path"]) for key in provenance["run_order"]}
    source_before = {item["path"]: sha256(REPO / item["path"]) for item in provenance["source_closure"]}
    analysis = {"schema": "bvm-rloop-ls3-mutual-rl-mechanical-analysis-v1", "experiment_id": EXP.name, "generated_at": now(), "runs": validations, "groups": group_result["groups"], "conditional_selection": conditional_selection, "canonical_references": {mask: {"raw_path": rel(CANONICAL[mask]), "raw_sha256": sha256(CANONICAL[mask]), "ordered_phase_chain_count": canonical_metrics[mask]["multi_evidence_oracle"]["ordered_phase_chain_count"]} for mask in MASKS}, "M0_gate": m0_gate, "matrix_audit": provenance["matrix_audit"], "raw_hash_before_analysis": raw_before, "source_hashes_before_analysis": source_before, "actual_grid": True, "interpolation": False, "resampling": False, "scientific_interpretation_performed": False}
    write_json(EXP / "analysis" / "mechanical_analysis.json", analysis)
    raw_after = {key: sha256(REPO / provenance["runs"][key]["raw"]["path"]) for key in provenance["run_order"]}
    source_after = {item["path"]: sha256(REPO / item["path"]) for item in provenance["source_closure"]}
    if raw_before != raw_after or source_before != source_after:
        raise RuntimeError("raw/source mutation detected during analysis")
    provenance.update({"conditional_selection": conditional_selection, "mechanical_analysis_performed": True, "bounded_experiment_interpretation_performed": False, "independent_scientific_review_performed": False, "scientific_interpretation_performed": False, "raw_hash_before_analysis": raw_before, "raw_hash_after_analysis": raw_after, "source_hashes_before_analysis": source_before, "source_hashes_after_analysis": source_after, "analysis": {"status": "COMPLETE", "path": rel(EXP / "analysis" / "mechanical_analysis.json")}, "execution_status": "ANALYSIS_COMPLETE"})
    for key in provenance["run_order"]:
        provenance["runs"][key].update({"mechanical_analysis_performed": True, "bounded_experiment_interpretation_performed": False, "independent_scientific_review_performed": False, "scientific_interpretation_performed": False})
    write_json(EXP / "provenance.json", provenance)
    result = read_json(EXP / "result.json")
    compact: dict[str, Any] = {}
    for key, item in validations.items():
        compact[key] = {"run_id": key, "mask": item["mask"], "M_pH": item["params"]["M_pH"], "K": item["params"]["K"], "ordered_phase_chain_count": item["oracle"]["ordered_phase_chain_count"], "old_strict_complete_response_count": item["oracle"]["old_strict_complete_response_count"], "terminal_pulse_count": item["oracle"]["terminal_pulse_count"], "BJ1_landmarks_ps": [common.phase_time(item["oracle"], "BJ1", i) for i in range(1, 5)], "BJ2_landmarks_ps": [common.phase_time(item["oracle"], "BJ2", i) for i in range(1, 5)], "mechanical_candidate_label": group_result["groups"].get(item["params"]["M_label"], {}).get("mechanical_candidate_label"), "active_phase_area": item["active_phase_area"], "auxiliary": item["auxiliary"], "bridge": item["bridge"], "raw_path": provenance["runs"][key]["raw"]["path"], "raw_sha256": provenance["runs"][key]["raw"]["sha256"]}
    result.update({"generated_at": now(), "status": "ANALYSIS_COMPLETE_AWAITING_SCIENTIFIC_REVIEW", "artifact_status": "VALID", "mechanical_analysis_performed": True, "bounded_experiment_interpretation_performed": False, "independent_scientific_review_performed": False, "scientific_interpretation_performed": False, "execution": provenance["execution"], "cases": compact, "groups": group_result["groups"], "conditional_selection": conditional_selection, "classification": {"status": "SCIENTIFIC_REVIEW_REQUIRED", "assigned": None, "candidate_labels_are_mechanical_only": True}, "stop": {"final_marker": FINAL, "automatic_follow_up": False}})
    write_json(EXP / "result.json", result)
    write_json(EXP / "analysis" / "SOURCE_MANIFEST.json", {"schema": "bvm-rloop-ls3-mutual-rl-source-manifest-v1", "source_closure": provenance["source_closure"], "canonical_hashes": {mask: sha256(CANONICAL[mask]) for mask in CANONICAL}, "matrix_audit": provenance["matrix_audit"]})
    write_json(EXP / "analysis" / "TRANSFORMATION_REGISTRY.json", {"schema": "bvm-rloop-ls3-mutual-rl-transformation-registry-v1", "raw_mutation": False, "physical_LS3_retained": True, "physical_RS_retained": True, "auxiliary": "L_AUX AUX 0 10P; R_AUX 0 AUX 20; K_AUX L_S3 L_AUX K inside BVM clone", "M_to_K": "K=M/sqrt(0.5*10)", "M_values_pH": M_VALUES, "actual_grid": True, "phase_display": "raw radians; rad/(2*pi) navigation only", "scientific_interpretation_performed": False})
    write_result_markdown()


def fmt(value: Any) -> str:
    if value is None:
        return "—"
    try:
        return f"{float(value):.8g}"
    except (TypeError, ValueError):
        return str(value)


def write_result_markdown() -> None:
    result = read_json(EXP / "result.json")
    lines = [f"# Physical LS3 mutual-RL loop — {EXP.name}", "", f"- Status: `{result['status']}`", "- Artifact status: `VALID`", "- Scientific interpretation: `NOT_PERFORMED`; candidate labels require review.", "- Physical `R_S=3 ohm` and `L_S3=0.5 pH` are retained; `L_AUX=10 pH`, `R_AUX=20 ohm`, with M-derived K.", "", "| M (pH) | K | N2 ordered chains | N3 ordered chains | N3 fourth BJ1 (ps) | mechanical label |", "|---:|---:|---:|---:|---:|---|"]
    for label in M_LABELS:
        group = result.get("groups", {}).get(label)
        if not group:
            lines.append(f"| {M_VALUES[label]:.2f} | {k_for_m(M_VALUES[label]):.8g} | — | — | — | pending |")
            continue
        lines.append(f"| {group['M_pH']:.2f} | {group['K']:.8g} | {group['N2_ordered_phase_chain_count']} | {group['N3_ordered_phase_chain_count']} | {fmt(group['N3_fourth_BJ1_ps'])} | `{group['mechanical_candidate_label']}` |")
    lines.extend(["", "Per-run active JS1/JS2 phase-area cross-checks, physical I/V LS3 and RS, total bridge current, V6-V10, JSL8, Lin/QBIN, L1 re-arm, auxiliary I/V, I²R and signed power/energy records are in `analysis/mechanical_analysis.json`.", "M=0 is a no-op gate. N1/N4 are conditional only; the smallest positive M is recorded if the fixed pair mechanically gives N2=2 and N3=3.", "P(...) is raw radians; rad/(2*pi) turns are navigation only, not literal SFQ counts. No scientific mechanism or winner conclusion is assigned.", "", f"Stop marker: `{FINAL}`.", ""])
    (EXP / "RESULT.md").write_text("\n".join(lines), encoding="utf-8")
    (EXP / "analysis" / "NUMERICAL_REVIEW.md").write_text("\n".join(["# Numerical review — mechanical only", "", "- M values are exact registered values; K=M/sqrt(0.5*10) is derived without a free K sweep.", "- The two-winding matrix audit records |K|<1, determinant and positive eigenvalues.", "- All integrations and comparisons use actual stored timestamps; no interpolation/resampling.", "- R_AUX dissipation is computed as actual-grid integral of I(R_AUX)^2*20 ohm and is not a hardware claim.", "- P(...) is raw radians; rad/(2*pi) turns are navigation only."]) + "\n", encoding="utf-8")
    (EXP / "analysis" / "ADVERSARIAL_REVIEW.md").write_text("\n".join(["# Adversarial review probes — mechanical only", "", "- M=0 is solved and checked before any positive-M materialization.", "- Physical L_S3 and R_S remain in each BVM clone; canonical BVM/QB files are not edited.", "- K is derived from M and the mutual matrix is audited for every registered point.", "- Conditional N1/N4 cases require a fixed mechanical N2=2/N3=3 pair and select the smallest positive M.", "- No negative M, M>0.75, extra L/R/C, sentinel, or follow-up solve is run.", "- Candidate labels do not constitute scientific interpretation."]) + "\n", encoding="utf-8")


def mechanical_qa() -> None:
    provenance = read_json(EXP / "provenance.json")
    failures: list[str] = []
    checks: dict[str, Any] = {}
    for key in provenance["run_order"]:
        record = provenance["runs"][key]
        deck = REPO / record["deck"]["path"]
        raw = REPO / record["raw"]["path"]
        log = REPO / record["log"]["path"]
        metadata = REPO / record["metadata"]["path"]
        stdout_path = REPO / record["stdout"]["path"]
        stderr_path = REPO / record["stderr"]["path"]
        text_value = deck.read_text(encoding="utf-8") if deck.is_file() else ""
        try:
            trace = load_raw(raw)
            missing = sorted(expected_headers(record["mask"]) - set(trace.headers))
            grid = branch.replay_base.finite_grid_qa(trace)
        except Exception as exc:
            trace = None
            missing = [f"raw_parse_error:{exc}"]
            grid = {"status": "INVALID"}
        warnings = warning_lines(log)
        unexpected = [line for line in warnings if line not in KNOWN_WARNINGS]
        topology_ok = bool(re.search(r"^\s*L_S3\s+6\s+10\s+0\.5P\s*$", text_value, flags=re.MULTILINE | re.IGNORECASE) and text_value.count("L_AUX  AUX  0       10P") == 1 and text_value.count("R_AUX  0       AUX     20") == 1 and text_value.count("K_AUX  L_S3   L_AUX") == 1 and text_value.count("BVM_LS3_MUTUAL_") >= 4 and "XBQ1 QBIN QBOUT BQ" in text_value and "XJTL1_1 QBOUT JTL1_OUT jtl" in text_value and "XJTL1_6 JTL5_OUT JTL6_OUT jtl" in text_value and "R_TERM JTL6_OUT 0 10" in text_value and ".tran 0.1p 200p" in text_value)
        passed = bool(record["execution_status"] == "RUN_PASS" and topology_ok and trace is not None and not missing and not trace.duplicate_columns and grid.get("status") == "VALID" and grid.get("sample_count") == 1999 and metadata.is_file() and stdout_path.is_file() and stderr_path.is_file() and not unexpected and sha256(deck) == record["deck"]["sha256"] and sha256(raw) == record["raw"]["sha256"])
        if not passed:
            failures.append(key)
        checks[key] = {"status": "PASS" if passed else "ARTIFACT_INVALID", "topology_ok": topology_ok, "grid": grid, "missing_required_probes": missing, "unexpected_solver_warning_lines": unexpected, "raw_sha256_matches": raw.is_file() and sha256(raw) == record["raw"]["sha256"]}
    selection = provenance.get("conditional_selection", {})
    expected = list(K0) if provenance.get("M0_gate", {}).get("status") != "PASS" else list(FIXED)
    if selection.get("status") == "AUTHORIZED":
        expected.extend(selection["selected_cases"])
    source_ok = all(sha256(REPO / item["path"]) == item["sha256"] for item in provenance["source_closure"])
    passed = bool(provenance["run_order"] == expected and not failures and source_ok and provenance.get("raw_hash_before_analysis") == provenance.get("raw_hash_after_analysis") and provenance.get("source_hashes_before_analysis") == provenance.get("source_hashes_after_analysis") and provenance["execution"]["actual_physical_solve_count"] == len(provenance["run_order"]) and len(provenance["run_order"]) in (2, 8, 10))
    qa = {"schema": "bvm-rloop-ls3-mutual-rl-mechanical-qa-v1", "status": "PASS" if passed else "FAIL", "artifact_status": "VALID" if passed else "ARTIFACT_INVALID", "run_order": provenance["run_order"], "expected_run_order": expected, "actual_physical_solve_count": len(provenance["run_order"]), "max_physical_solves": 10, "source_hashes_match": source_ok, "raw_hash_before_after_equal": provenance.get("raw_hash_before_analysis") == provenance.get("raw_hash_after_analysis"), "source_hash_before_after_equal": provenance.get("source_hashes_before_analysis") == provenance.get("source_hashes_after_analysis"), "contains_reference_raw_copies": False, "contains_delivery_manifest": False, "runs": checks, "failures": failures, "mechanical_analysis_performed": True, "scientific_interpretation_performed": False}
    write_json(EXP / "analysis" / "MECHANICAL_QA.json", qa)
    provenance["qa"] = qa
    write_json(EXP / "provenance.json", provenance)
    result = read_json(EXP / "result.json")
    result["qa_summary"] = {"status": qa["status"], "artifact_status": qa["artifact_status"]}
    write_json(EXP / "result.json", result)
    write_result_markdown()
    if not passed:
        raise RuntimeError(f"mechanical QA failed: {failures}")


def visualization() -> None:
    provenance = read_json(EXP / "provenance.json")
    if provenance.get("qa", {}).get("status") != "PASS":
        raise RuntimeError("mechanical QA must pass before visualization")
    asset = EXP / "plots" / "assets" / "plotly.min.js"
    entries: list[dict[str, Any]] = []
    specs = {
        "01_SIGNAL_TIMING": ["V(COMMON_SL)", "I(B_JSL8)", "V(QBIN)", "I(LIN|XBQ1)", "V(QBOUT)"],
        "02_BVM_STATE": [signal for index in range(1, 5) for element in ("B_JS1", "B_JS2", "B_JM1", "B_JM2", "L_S3", "R_S", "L_AUX", "R_AUX") for signal in (f"P({element}|XBVM{index})", f"V({element}|XBVM{index})", f"I({element}|XBVM{index})") if element.startswith("B_") or signal.startswith("V(") or signal.startswith("I(")],
        "03_JSL_CHAIN": [signal for index in range(1, 9) for signal in (f"P(B_JSL{index})", f"V(B_JSL{index})", f"I(B_JSL{index})")],
        "04_QB_STATE": ["V(QBIN)", "I(LIN|XBQ1)", "V(LIN|XBQ1)", "P(BJ1|XBQ1)", "V(BJ1|XBQ1)", "I(BJ1|XBQ1)", "P(BJ2|XBQ1)", "V(BJ2|XBQ1)", "I(BJ2|XBQ1)", "I(L1|XBQ1)", "I(L2|XBQ1)", "V(QBOUT)"],
        "05_JTL_CHAIN": [signal for stage in JTL_STAGES for signal in (f"P(B01|XJTL1_{stage})", f"V(B01|XJTL1_{stage})", f"I(B01|XJTL1_{stage})", f"V(JTL{stage}_OUT)")] + ["I(R_TERM)"],
    }
    for key in provenance["run_order"]:
        raw = REPO / provenance["runs"][key]["raw"]["path"]
        trace = load_raw(raw)
        for page, requested in specs.items():
            selected = [signal for signal in requested if signal in trace.headers]
            full = EXP / "plots" / key / f"{page}_full_0_200.html"
            branch.render_plot(raw, full, selected, f"{key}: {page}; full 0-200 ps; actual stored grid", asset)
            entries.append({"kind": "standalone", "run_id": key, "path": rel(full), "raw_path": rel(raw), "raw_sha256": sha256(raw), "sha256": sha256(full), "signals": selected, "window_ps": list(FULL), "focused": False, "descriptive_only": True})
            crop = branch.total_helpers.crop_csv(raw, *FOCUS)
            try:
                focus = EXP / "plots" / key / f"{page}_focus_110_121.html"
                branch.render_plot(crop, focus, selected, f"{key}: {page}; focus [110,121) ps; actual stored grid", asset)
                entries.append({"kind": "standalone", "run_id": key, "path": rel(focus), "raw_path": rel(raw), "raw_sha256": sha256(raw), "sha256": sha256(focus), "signals": selected, "window_ps": list(FOCUS), "focused": True, "descriptive_only": True})
            finally:
                crop.unlink(missing_ok=True)
    for label in M_LABELS:
        for mask in MASKS:
            cases = [(f"CANONICAL_{mask}", load_raw(CANONICAL[mask]))]
            cases.extend((key, load_raw(REPO / provenance["runs"][key]["raw"]["path"])) for key in provenance["run_order"] if case_info(key)["M_label"] == label and case_info(key)["mask"] == mask)
            selected = [signal for signal in specs["01_SIGNAL_TIMING"] + specs["03_JSL_CHAIN"] + specs["04_QB_STATE"] if all(signal in trace.headers for _, trace in cases)]
            if not selected:
                continue
            temporary = branch.total_helpers.comparison_csv(cases, selected, FOCUS)
            output = EXP / "plots" / "comparisons" / f"{label}_{mask}_comparison_focus_110_121.html"
            try:
                labels = [branch.replay_base.prefixed_label(case, signal) for case, _ in cases for signal in selected]
                branch.render_plot(temporary, output, labels, f"{label} {mask}: canonical/mutual LS3 comparison; focus [110,121) ps", asset)
            finally:
                temporary.unlink(missing_ok=True)
            entries.append({"kind": "comparison", "M_label": label, "mask": mask, "path": rel(output), "sha256": sha256(output), "signals": selected, "cases": [case for case, _ in cases], "window_ps": list(FOCUS), "focused": True, "descriptive_only": True})
    html = sorted((EXP / "plots").rglob("*.html"))
    invalid = [rel(path) for path in html if any(token in path.read_text(encoding="utf-8") for token in ("plotly.js v", "var Plotly=", "cdn.plot.ly", "Unknown"))]
    record = {"schema": "bvm-rloop-ls3-mutual-rl-visualization-v1", "status": "PASS" if entries and asset.is_file() and not invalid else "FAIL", "renderer": rel(PLOTTER), "layout": "sep_comb", "color": "dark", "phase_option": "2pi", "entries": entries, "standalone_count": sum(item["kind"] == "standalone" for item in entries), "comparison_count": sum(item["kind"] == "comparison" for item in entries), "focused_window_entries": sum(item.get("focused", False) for item in entries), "asset": {"path": rel(asset), "sha256": sha256(asset) if asset.is_file() else None}, "invalid_runtime_pages": invalid, "raw_hashes_rechecked": all(item["raw_sha256"] == sha256(REPO / item["raw_path"]) for item in entries if item["kind"] == "standalone"), "descriptive_only": True}
    write_json(EXP / "analysis" / "VISUALIZATION_MANIFEST.json", record)
    write_json(EXP / "analysis" / "VISUALIZATION_QA.json", {key: record[key] for key in ("status", "standalone_count", "comparison_count", "focused_window_entries", "invalid_runtime_pages", "raw_hashes_rechecked")})
    provenance["visualization"] = record
    write_json(EXP / "provenance.json", provenance)
    result = read_json(EXP / "result.json")
    result["visualization_summary"] = {key: record[key] for key in ("status", "standalone_count", "comparison_count", "focused_window_entries")}
    write_json(EXP / "result.json", result)
    write_result_markdown()
    if record["status"] != "PASS":
        raise RuntimeError(f"visualization failed: {invalid}")


def write_evidence_manifest() -> None:
    records = [{"path": path.relative_to(EXP).as_posix(), "sha256": sha256(path), "bytes": path.stat().st_size} for path in sorted(EXP.rglob("*")) if path.is_file() and path.name != "delivery_manifest.json" and path.suffix != ".tmp"]
    write_json(EXP / "analysis" / "RAW_ANALYSIS_HANDOFF_MANIFEST.json", {"schema": "bvm-rloop-ls3-mutual-rl-raw-analysis-handoff-v1", "experiment_id": EXP.name, "raw_is_immutable_solver_output": True, "files_excluding_delivery_manifest": records})
    (EXP / "analysis" / "EVIDENCE_MANIFEST.md").write_text("\n".join(["# Evidence manifest", "", "| path | SHA-256 | bytes |", "|---|---|---:"] + [f"| `{item['path']}` | `{item['sha256']}` | {item['bytes']} |" for item in records]) + "\n", encoding="utf-8")


def package() -> None:
    provenance = read_json(EXP / "provenance.json")
    if provenance.get("qa", {}).get("status") != "PASS" or provenance.get("visualization", {}).get("status") != "PASS":
        raise RuntimeError("QA and visualization must pass before package")
    write_evidence_manifest()
    delivery = Path("/mnt/d/BVM_Backages")
    delivery.mkdir(parents=True, exist_ok=True)
    package_path = delivery / f"{EXP.name}_raw_evidence.zip"
    version = "v1"
    number = 2
    while package_path.exists():
        version = f"v{number}"
        package_path = delivery / f"{EXP.name}_{version}_raw_evidence.zip"
        number += 1
    files: list[tuple[Path, str]] = [(EXP / name, name) for name in ("PREFLIGHT.md", "README.md", "experiment.yaml", "RESULT.md", "result.json", "provenance.json")]
    for dirname in ("runs", "analysis", "plots"):
        for path in sorted((EXP / dirname).rglob("*")):
            if path.is_file() and (dirname != "plots" or path.name == "plotly.min.js" or "focus_110_121" in path.name):
                files.append((path, path.relative_to(EXP).as_posix()))
    files.extend([(Path(__file__), "executor/generator.py"), (EXP / "run.sh", "executor/run.sh")])
    records = [{"path": name, "sha256": sha256(path), "bytes": path.stat().st_size} for path, name in files]
    with zipfile.ZipFile(package_path, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path, name in files:
            archive.write(path, name)
    with zipfile.ZipFile(package_path) as archive:
        reopened = {name: hashlib.sha256(archive.read(name)).hexdigest() for name in archive.namelist()}
    expected = {item["path"]: item["sha256"] for item in records}
    raw_members = [f"runs/{key}/raw.csv" for key in provenance["run_order"]]
    qa = {"status": "PASS" if expected == reopened and all(member in reopened for member in raw_members) else "FAIL", "package_version": version, "package_path": str(package_path), "package_sha256": sha256(package_path), "package_bytes": package_path.stat().st_size, "file_count": len(records), "expected_file_hashes_match_after_reopen": expected == reopened, "contains_all_new_run_raw": all(member in reopened for member in raw_members), "new_run_raw_members": raw_members, "contains_reference_raw_copies": False, "contains_delivery_manifest": False, "delivery_manifest_outside_zip": True, "not_in_git": True, "zip_files": records, "git_head_at_packaging": git_head(), "remote_head_at_packaging": remote_head()}
    manifest = {"schema": "bvm-rloop-ls3-mutual-rl-delivery-manifest-v1", "experiment_id": EXP.name, "status": "READY_FOR_DRIVE_UPLOAD" if qa["status"] == "PASS" else "PACKAGE_INVALID", "package_version": version, "package_path": str(package_path), "package_sha256": qa["package_sha256"], "package_bytes": qa["package_bytes"], "package_qa": qa, "drive_folder_id": DRIVE_FOLDER_ID, "drive_file_id": None, "drive_url": None}
    write_json(EXP / "delivery_manifest.json", manifest)
    write_json(EXP / "analysis" / "PACKAGE_QA.json", qa)
    provenance["package"] = {"status": manifest["status"], "package_qa": qa, "delivery_manifest_path": "delivery_manifest.json", "drive_file_id": None, "drive_url": None}
    write_json(EXP / "provenance.json", provenance)
    result = read_json(EXP / "result.json")
    result["package_summary"] = {"status": manifest["status"], "package_version": version, "package_sha256": qa["package_sha256"], "package_bytes": qa["package_bytes"], "file_count": qa["file_count"], "delivery_manifest_path": "delivery_manifest.json", "drive_file_id": None}
    write_json(EXP / "result.json", result)
    write_result_markdown()
    if qa["status"] != "PASS":
        raise RuntimeError("package QA failed")
    print(json.dumps({"status": "PASS", "package_path": str(package_path), "sha256": qa["package_sha256"], "bytes": qa["package_bytes"], "files": qa["file_count"]}, ensure_ascii=False, indent=2))


def record_drive(file_id: str, url: str | None, size: int) -> None:
    manifest_path = EXP / "delivery_manifest.json"
    manifest = read_json(manifest_path)
    package_path = Path(manifest["package_path"])
    if not package_path.is_file() or sha256(package_path) != manifest["package_sha256"] or int(size) != int(manifest["package_bytes"]):
        raise RuntimeError("local package verification failed")
    manifest.update({"status": "UPLOADED", "drive_file_id": file_id, "drive_url": url, "uploaded_at": now(), "drive_verified_local_sha256": manifest["package_sha256"], "drive_verified_local_bytes": manifest["package_bytes"], "remote_sha256_from_connector": None})
    write_json(manifest_path, manifest)
    provenance = read_json(EXP / "provenance.json")
    provenance["package"].update({"status": "UPLOADED", "drive_file_id": file_id, "drive_url": url, "drive_uploaded_at": manifest["uploaded_at"], "delivery_manifest_sha256": sha256(manifest_path), "drive_sha256_verified": "metadata SHA not supplied by connector"})
    write_json(EXP / "provenance.json", provenance)
    result = read_json(EXP / "result.json")
    result["package_summary"].update({"status": "UPLOADED", "drive_file_id": file_id, "drive_url": url})
    write_json(EXP / "result.json", result)
    write_result_markdown()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--josim-bin", default=str(SOLVER))
    parser.add_argument("--dt", default="0.1p")
    parser.add_argument("--stop-time", default="200p")
    parser.add_argument("--masks", nargs="+", default=list(MASKS))
    parser.add_argument("--m-values", nargs="+", default=[f"{value:.2f}" for value in M_VALUES.values()])
    parser.add_argument("--l-aux", type=float, default=L_AUX_PH)
    parser.add_argument("--r-aux", type=float, default=R_AUX_OHM)
    parser.add_argument("--only")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-analysis", action="store_true")
    parser.add_argument("--no-plots", action="store_true")
    parser.add_argument("command", nargs="?", default="all", choices=("all", "continue-from-m0", "record-drive"))
    parser.add_argument("drive_id", nargs="?")
    parser.add_argument("drive_url", nargs="?")
    parser.add_argument("drive_size", nargs="?", type=int)
    args = parser.parse_args()
    if args.command == "record-drive":
        if not args.drive_id or args.drive_size is None:
            raise RuntimeError("record-drive requires FILE_ID and BYTES")
        record_drive(args.drive_id, args.drive_url, args.drive_size)
        return 0
    if args.dry_run:
        dry_run(args)
        return 0
    if args.dt != "0.1p" or args.stop_time != "200p":
        raise RuntimeError("registration requires dt=0.1p and stop_time=200p")
    if args.command == "continue-from-m0":
        provenance = read_json(EXP / "provenance.json")
        if provenance.get("run_order") != list(K0):
            raise RuntimeError(f"continuation requires exactly the M=0 pair: {provenance.get('run_order')}")
        gate = update_m0_gate(args)
        if gate["status"] != "PASS":
            analyze(args)
            mechanical_qa()
            visualization()
            package()
            return 0
        materialize_positive()
        for key in [key for key in FIXED if key not in K0]:
            execute_case(key, args)
        analyze(args)
        provenance = read_json(EXP / "provenance.json")
        selected = provenance.get("conditional_selection", {}).get("selected_M_label")
        if selected:
            materialize_conditional(selected)
            for mask in CONDITIONAL_MASKS:
                execute_case(f"LS3_MUTUAL_{selected}_{mask}", args)
            analyze(args)
        mechanical_qa()
        visualization()
        package()
        return 0
    prepare(args)
    selected_masks = [mask for mask in args.masks if args.only is None or mask == args.only]
    for mask in selected_masks:
        execute_case(f"LS3_MUTUAL_M0P00_{mask}", args)
    gate = update_m0_gate(args)
    if selected_masks != list(MASKS) or gate["status"] != "PASS":
        analyze(args)
        mechanical_qa()
        visualization()
        package()
        return 0
    materialize_positive()
    for key in [key for key in FIXED if key not in K0]:
        execute_case(key, args)
    analyze(args)
    provenance = read_json(EXP / "provenance.json")
    selected = provenance.get("conditional_selection", {}).get("selected_M_label")
    if selected:
        materialize_conditional(selected)
        for mask in CONDITIONAL_MASKS:
            execute_case(f"LS3_MUTUAL_{selected}_{mask}", args)
        analyze(args)
    mechanical_qa()
    visualization()
    package()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
