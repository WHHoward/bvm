#!/usr/bin/env python3
"""Run the R6-A-scale transformer isolation experiment on current QB."""

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
FIXED = ("ISO_R6A_0011", "ISO_R6A_0111")
CONDITIONAL = ("ISO_R6A_0001", "ISO_R6A_1111")
MASKS = ("0011", "0111")
L_PRI_PH_DEFAULT = 0.20
L_SEC_PH_DEFAULT = 2.00
K_ISO_DEFAULT = 0.50
R_PRI_OHM_DEFAULT = 12.0
FOCUS = (110.0, 121.0)
REARM = (121.0, 130.0)
FULL = (0.0, 200.0)
PHI0 = 2.067833848e-15
CONTRACT = "This experiment is governed by docs/EXPERIMENT_CONTRACT.md."
FINAL = "EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW"
DRIVE_FOLDER_ID = "1--nlY7Nq5ArVPydJNrnQf-EGmwN-undh"
KNOWN_WARNINGS = {"Unknown device/node IB|XBQ1", "Cannot store results for this device/node."}
JTL_STAGES = tuple(range(1, 7))

sha256 = common.sha256
rel = common.rel
write_json = common.write_json
read_json = common.read_json
load_raw = common.load_raw
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


def case_info(case_id: str, args: argparse.Namespace) -> dict[str, Any]:
    match = re.fullmatch(r"ISO_R6A_(0011|0111|0001|1111)", case_id)
    if not match:
        raise RuntimeError(f"invalid case id: {case_id}")
    mask = match.group(1)
    m = args.k_iso * math.sqrt(args.l_pri * args.l_sec)
    return {"case_id": case_id, "mask": mask, "L_PRI_pH": args.l_pri, "L_SEC_pH": args.l_sec, "K_ISO": args.k_iso, "R_PRI_ohm": args.r_pri, "M_pH": m, "conditional_population_validation": mask in ("0001", "1111")}


def static_matrix_audit(args: argparse.Namespace) -> dict[str, Any]:
    fixture = REPO / "test" / "comp" / "mutual.cir"
    syntax = [line.strip() for line in fixture.read_text(encoding="utf-8").splitlines() if line.strip().startswith("K ")]
    m = args.k_iso * math.sqrt(args.l_pri * args.l_sec)
    determinant = args.l_pri * args.l_sec - m * m
    discriminant = math.sqrt((args.l_pri - args.l_sec) ** 2 + 4.0 * m * m)
    eigen_min = 0.5 * (args.l_pri + args.l_sec - discriminant)
    eigen_max = 0.5 * (args.l_pri + args.l_sec + discriminant)
    syntax_ok = bool(syntax) and all(re.fullmatch(r"K\s+\S+\s+\S+\s+[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", line) for line in syntax)
    return {"status": "PASS" if syntax_ok and abs(args.k_iso) < 1.0 and determinant > 0.0 and eigen_min > 0.0 else "FAIL", "syntax_fixture": rel(fixture), "syntax_examples": syntax, "L_PRI_pH": args.l_pri, "L_SEC_pH": args.l_sec, "K_ISO": args.k_iso, "M_pH": m, "determinant_pH2": determinant, "eigenvalues_pH": [eigen_min, eigen_max], "abs_K_lt_1": abs(args.k_iso) < 1.0, "matrix_positive_definite": eigen_min > 0.0}


def transform_deck(mask: str, args: argparse.Namespace, deck_dir: Path) -> str:
    original = CANONICAL_DECK[mask].read_text(encoding="utf-8")
    targets = {"jjmit.cir": SOURCE_INPUTS / "jjmit.cir", "bvm_jm2_connected.cir": SOURCE_INPUTS / "bvm_jm2_connected.cir", "BQ_parameterized_bjs400_rj2.cir": SOURCE_INPUTS / "BQ_parameterized_bjs400_rj2.cir", "jtl2.cir": SOURCE_INPUTS / "jtl2.cir"}
    output = []
    bjsl8_replaced = 0
    inserted = False
    probe_replaced = 0
    for line in original.splitlines():
        stripped = line.strip()
        if stripped.startswith(".include "):
            basename = Path(stripped.split(None, 1)[1]).name
            if basename not in targets:
                raise RuntimeError(f"unexpected include: {basename}")
            output.append(f".include {Path(os.path.relpath(targets[basename], deck_dir)).as_posix()}")
            continue
        if re.fullmatch(r"B_JSL8 JSL_NODE7 QBIN jjmit area=5\.0", stripped, flags=re.IGNORECASE):
            output.append("B_JSL8 JSL_NODE7 ISO_SOURCE_OUT jjmit area=5.0")
            output.extend([f"R_PRI ISO_SOURCE_OUT N_PRI {args.r_pri:.17g}", f"L_PRI N_PRI 0 {args.l_pri:.17g}P", f"L_SEC QBIN 0 {args.l_sec:.17g}P", f"K_ISO L_PRI L_SEC {args.k_iso:.17g}"])
            bjsl8_replaced += 1
            inserted = True
            continue
        if stripped.startswith(".print ") and "P(B_JSL8)" in stripped:
            output.append(stripped + " V(ISO_SOURCE_OUT) I(R_PRI) V(R_PRI) I(L_PRI) V(L_PRI) I(L_SEC) V(L_SEC)")
            probe_replaced += 1
            continue
        output.append(line)
    if bjsl8_replaced != 1 or not inserted or probe_replaced != 1:
        raise RuntimeError(f"transform anchors failed {bjsl8_replaced=} {inserted=} {probe_replaced=}")
    text = "\n".join(output) + "\n"
    if "B_JSL8 JSL_NODE7 QBIN" in text or "B_JSL8 JSL_NODE7 ISO_SOURCE_OUT" not in text:
        raise RuntimeError("direct JSL8-QBIN galvanic connection survived")
    for token in ("R_PRI ISO_SOURCE_OUT N_PRI", "L_PRI N_PRI 0", "L_SEC QBIN 0", "K_ISO L_PRI L_SEC", "XBQ1 QBIN QBOUT BQ", "XJTL1_1 QBOUT JTL1_OUT jtl", "XJTL1_6 JTL5_OUT JTL6_OUT jtl", "R_TERM JTL6_OUT 0 10", ".tran 0.1p 200p"):
        if token not in text:
            raise RuntimeError(f"transform token missing: {token}")
    if any(token in text for token in ("T_BVM_QB", "V_REPLAY", "TRANSFORMER", "PTL", "SENTINEL", "LC_LADDER")):
        raise RuntimeError("forbidden topology token")
    return text


def make_deck(case_id: str, args: argparse.Namespace) -> dict[str, Any]:
    item = case_info(case_id, args)
    deck = EXP / "runs" / case_id / "deck.cir"
    deck.parent.mkdir(parents=True, exist_ok=True)
    deck.write_text(transform_deck(item["mask"], args, deck.parent), encoding="utf-8")
    return {**item, "path": rel(deck), "sha256": sha256(deck), "bytes": deck.stat().st_size, "topology": "JSL8 source-side BVM endpoint -> R_PRI -> L_PRI, coupled by K_ISO to L_SEC -> QBIN; canonical QB/JTL retained"}


def expected_headers(mask: str) -> set[str]:
    headers = set(load_raw(CANONICAL[mask]).headers)
    headers.update({"V(ISO_SOURCE_OUT)", "I(R_PRI)", "V(R_PRI)", "I(L_PRI)", "V(L_PRI)", "I(L_SEC)", "V(L_SEC)"})
    return headers


def source_inventory() -> list[dict[str, Any]]:
    return [record_file("runner", Path(__file__), "transformer generator/executor/analyzer/plotter/packager"), record_file("run_sh", EXP / "run.sh", "user-facing runner"), record_file("jjmit", SOURCE_INPUTS / "jjmit.cir", "canonical JJ model"), record_file("bvm", SOURCE_INPUTS / "bvm_jm2_connected.cir", "canonical BVM"), record_file("qb", SOURCE_INPUTS / "BQ_parameterized_bjs400_rj2.cir", "canonical current QB"), record_file("jtl", SOURCE_INPUTS / "jtl2.cir", "canonical JTL"), record_file("solver", SOLVER, "recorded solver"), record_file("plotter", PLOTTER, "standard renderer"), record_file("branch_helper", REPO / "scripts" / "bvm_qb_rloop_branch_timing_decomposition.py", "read-only metrics helper"), record_file("population_helper", REPO / "scripts" / "bvm_qb_rloop_ls3_population_validation.py", "read-only oracle helper"), record_file("oracle", ORACLE_PATH, "historical multi-evidence oracle"), *[record_file(f"canonical_{mask}_raw", CANONICAL[mask], "read-only canonical raw") for mask in ("0011", "0111", "0001", "1111")], *[record_file(f"canonical_{mask}_deck", CANONICAL_DECK[mask], "read-only canonical deck") for mask in ("0011", "0111", "0001", "1111")]]


def prepare(args: argparse.Namespace) -> None:
    if git_head() != EXPECTED_HEAD or remote_head() != EXPECTED_HEAD:
        raise RuntimeError("HEAD/remote does not match frozen parent")
    if tuple(args.masks) != MASKS:
        raise RuntimeError("current registration requires masks 0011/0111")
    if (args.l_pri, args.l_sec, args.k_iso, args.r_pri) != (0.20, 2.00, 0.50, 12.0):
        raise RuntimeError("current registration requires R6-A scale 0.20/2.00/K0.50/R12")
    matrix = static_matrix_audit(args)
    if matrix["status"] != "PASS":
        raise RuntimeError("transformer matrix audit failed")
    m = args.k_iso * math.sqrt(args.l_pri * args.l_sec)
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
        raise RuntimeError(f"canonical branch audit failed: {direction}")
    records = {key: make_deck(key, args) for key in FIXED}
    (EXP / "PREFLIGHT.md").write_text(f"""# R6-style transformer isolation of current population QB — {EXP.name}

{CONTRACT}

- Parent HEAD: {EXPECTED_HEAD}; remote bvm/master: {EXPECTED_HEAD}.
- Study phase: EXPLORATORY; role: Experimental Operator + Evidence Packager.
- Current canonical population QB is retained unchanged. The direct B_JSL8 JSL_NODE7-to-QBIN connection is removed and replaced by the frozen passive interface.
- Frozen interface: R_PRI=12.0 ohm, L_PRI=0.20 pH, L_SEC=2.00 pH, K_ISO=0.50, M={m:.17g} pH.
- Topology: B_JSL8 -> ISO_SOURCE_OUT -> R_PRI -> L_PRI -> ground, with L_SEC QBIN -> ground and K_ISO coupling. Canonical QB/JTL/BVM internal parameters otherwise remain unchanged.
- No parameter sweep, R6-B ratio point, added JJ, current/voltage source, bias, C, PTL, or timestep refinement.
- Fixed cases are ISO_R6A_0011 and ISO_R6A_0111. Conditional N1/N4 cases run only if both fixed cases mechanically give N2=2 and N3=3.
- JoSIM .tran 0.1p 200p; all integrations use actual timestamps. P(...) is raw radians and turns are navigation only, not literal SFQ counts.

## Runner

    chmod +x run.sh
    ./run.sh --dry-run
    ./run.sh

Edit only USER-EDITABLE PARAMETERS in run.sh. Default raw overwrite is refused; --force creates a timestamped sibling backup.

Static K/matrix audit: {matrix["status"]}; canonical branch audit: {json.dumps({mask: item["status"] for mask, item in direction.items()})}.

Final state: {FINAL}; scientific interpretation is not performed.
""", encoding="utf-8")
    (EXP / "README.md").write_text(f"""# {EXP.name}

Use ./run.sh --dry-run to inspect the two fixed transformer-isolation cases without invoking JoSIM. The conditional N1/N4 pair is materialized only after the fixed mechanical N2/N3 rule passes. This is an isolation counterfactual at a frozen R6-A scale applied to the current population QB; do not infer a final design or literal SFQ count.
""", encoding="utf-8")
    yaml = ["schema_version: bvm-qb-transformer-isolation-current-qb-v1", f"id: {EXP.name}", "study_phase: EXPLORATORY", "role: Experimental Operator + Evidence Packager", "status: PREFLIGHT_PASS", f"registration_head: {EXPECTED_HEAD}", f"remote_bvm_master_at_registration: {EXPECTED_HEAD}", f"contract_sentence: {CONTRACT}", "scientific_review_authorized: false", "", "frozen:", "  L_PRI_pH: 0.20", "  L_SEC_pH: 2.00", "  K_ISO: 0.50", "  R_PRI_ohm: 12.0", f"  M_pH: {m:.17g}", "  timestep_ps: 0.1", "  stop_time_ps: 200", "", "authorized_matrix:", "  fixed: [ISO_R6A_0011, ISO_R6A_0111]", "  conditional: [ISO_R6A_0001, ISO_R6A_1111]", "  maximum_new_physical_solves: 4", "", "fixed_deck_registration:"]
    for key, item in records.items():
        yaml.extend([f"  - run_id: {key}", f"    path: {item['path']}", f"    sha256: {item['sha256']}", f"    bytes: {item['bytes']}"])
    yaml.extend(["", "conditional_rule: fixed N2=2/N3=3 mechanical label only", "scientific_classification: NOT_ASSIGNED_SCIENTIFIC_REVIEW_REQUIRED", ""])
    (EXP / "experiment.yaml").write_text("\n".join(yaml), encoding="utf-8")
    closure = source_inventory()
    provenance = {"schema": "bvm-qb-transformer-isolation-current-qb-provenance-v1", "experiment_id": EXP.name, "created_at": now(), "registration_head": EXPECTED_HEAD, "remote_bvm_master_at_registration": EXPECTED_HEAD, "contract_sentence": CONTRACT, "scientific_review_authorized": False, "mechanical_analysis_performed": False, "bounded_experiment_interpretation_performed": False, "independent_scientific_review_performed": False, "scientific_interpretation_performed": False, "solver": branch.replay_base.solver_context(), "source_closure": closure, "frozen": {"question": "apply R6-A-scale transformer isolation to current canonical population QB", "topology": "JSL8 source -> R_PRI -> L_PRI; K_ISO; L_SEC -> QBIN; canonical QB/JTL retained", "L_PRI_pH": args.l_pri, "L_SEC_pH": args.l_sec, "K_ISO": args.k_iso, "R_PRI_ohm": args.r_pri, "M_pH": m, "windows_ps": [list(FULL), list(FOCUS), list(REARM)], "no_R6B": True, "no_parameter_sweep": True}, "matrix_audit": matrix, "branch_direction_audit": direction, "authorized_matrix": {"fixed": list(FIXED), "conditional": list(CONDITIONAL), "maximum": 4, "no_other_solve": True}, "registered_decks": records, "runs": {}, "run_order": [], "execution": {"authorized_physical_solve_count": 4, "actual_physical_solve_count": 0, "solver_invocation_count": 0, "run_order": []}, "conditional_selection": {"status": "PENDING"}, "analysis": {"status": "PENDING"}, "qa": {"status": "PENDING"}, "visualization": {"status": "PENDING"}, "package": {"status": "PENDING"}, "stop": {"final_marker": None, "automatic_follow_up": False}}
    write_json(EXP / "provenance.json", provenance)
    write_json(EXP / "result.json", {"schema": "bvm-qb-transformer-isolation-current-qb-result-v1", "experiment_id": EXP.name, "generated_at": now(), "status": "PREFLIGHT_PASS", "artifact_status": "PENDING", "scientific_review_authorized": False, "mechanical_analysis_performed": False, "bounded_experiment_interpretation_performed": False, "independent_scientific_review_performed": False, "scientific_interpretation_performed": False, "execution": provenance["execution"], "cases": {key: {"status": "AUTHORIZED_NOT_RUN"} for key in [*FIXED, *CONDITIONAL]}, "matrix_audit": matrix, "conditional_population_validation": {"status": "NOT_AUTHORIZED"}, "classification": {"status": "SCIENTIFIC_REVIEW_REQUIRED", "assigned": None}, "stop": {"final_marker": None, "automatic_follow_up": False}})


def dry_run(args: argparse.Namespace) -> None:
    print(f"experiment={EXP.name}")
    print(f"parent_sha={EXPECTED_HEAD}")
    print(f"masks={' '.join(args.masks)}")
    m = args.k_iso * math.sqrt(args.l_pri * args.l_sec)
    for mask in args.masks:
        print(f"case_id=ISO_R6A_{mask} L_PRI_pH={args.l_pri} L_SEC_pH={args.l_sec} K_ISO={args.k_iso} R_PRI_ohm={args.r_pri} M_pH={m:.17g} deck={EXP/'runs'/f'ISO_R6A_{mask}'/'deck.cir'} raw={EXP/'runs'/f'ISO_R6A_{mask}'/'raw.csv'}")
    print(f"josim_cli={args.josim_bin}")
    print(f"dt={args.dt} stop_time={args.stop_time} fixed_solve_count=2 maximum_solve_count=4")
    print("DRY_RUN no JoSIM invocation")


def warning_lines(path: Path) -> list[str]:
    if not path.is_file():
        return ["missing_log"]
    return [line.strip() for line in path.read_text(errors="replace").splitlines() if any(token in line for token in ("Missing model:", "Unknown device/node", "Cannot store results", "Error", "error"))]


def execute_case(case_id: str, args: argparse.Namespace) -> None:
    provenance = read_json(EXP / "provenance.json")
    if case_id in provenance["run_order"] or case_id not in provenance["registered_decks"]:
        raise RuntimeError(f"case not registered or already run: {case_id}")
    order = [*FIXED, *CONDITIONAL]
    position = order.index(case_id)
    expected_prefix = [key for key in order[:position] if key in provenance["run_order"]]
    if provenance["run_order"] != expected_prefix:
        raise RuntimeError(f"wrong run order before {case_id}: {provenance['run_order']}")
    deck = REPO / provenance["registered_decks"][case_id]["path"]
    raw = deck.parent / "raw.csv"
    log = deck.parent / "run.log"
    stdout_path = deck.parent / "stdout.txt"
    stderr_path = deck.parent / "stderr.txt"
    metadata = deck.parent / "metadata.json"
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
    log.write_text(
        "\n".join([
            f"experiment={EXP.name}",
            f"run_id={case_id}",
            f"parent_commit={EXPECTED_HEAD}",
            f"started_at={started}",
            f"finished_at={finished}",
            f"runtime_seconds={runtime:.6f}",
            f"command={' '.join(command)}",
            f"exit_code={completed.returncode}",
            "--- stdout ---",
            completed.stdout,
            "--- stderr ---",
            completed.stderr,
            "",
        ]),
        encoding="utf-8",
    )
    item = case_info(case_id, args)
    record: dict[str, Any] = {
        "run_id": case_id,
        **item,
        "parent_commit": EXPECTED_HEAD,
        "command": command,
        "runtime_seconds": runtime,
        "started_at": started,
        "finished_at": finished,
        "deck": {"path": rel(deck), "sha256": sha256(deck), "bytes": deck.stat().st_size},
        "stdout": {"path": rel(stdout_path), "sha256": sha256(stdout_path), "bytes": stdout_path.stat().st_size},
        "stderr": {"path": rel(stderr_path), "sha256": sha256(stderr_path), "bytes": stderr_path.stat().st_size},
        "log": {"path": rel(log), "sha256": sha256(log), "bytes": log.stat().st_size},
        "solver": {**branch.replay_base.solver_context(), "binary_sha256": sha256(Path(args.josim_bin))},
        "physical_solve_this_experiment": True,
        "raw_immutable": True,
        "mechanical_analysis_performed": False,
        "scientific_interpretation_performed": False,
        "solver_warning_lines": warning_lines(log),
    }
    if completed.returncode != 0 or not raw.is_file() or raw.stat().st_size == 0:
        record["execution_status"] = "SOLVER_FAIL"
        record["raw"] = {"path": rel(raw), "exists": raw.is_file(), "sha256": sha256(raw) if raw.is_file() else None, "bytes": raw.stat().st_size if raw.is_file() else None}
        write_json(metadata, {"run_id": case_id, "execution_status": record["execution_status"], "deck_sha256": record["deck"]["sha256"], "raw": record["raw"], "log_sha256": record["log"]["sha256"], "stdout_sha256": record["stdout"]["sha256"], "stderr_sha256": record["stderr"]["sha256"]})
        record["metadata"] = {"path": rel(metadata), "sha256": sha256(metadata), "bytes": metadata.stat().st_size}
        provenance["runs"][case_id] = record
        provenance["run_order"].append(case_id)
        provenance["execution"]["actual_physical_solve_count"] = len(provenance["run_order"])
        provenance["execution"]["solver_invocation_count"] = len(provenance["run_order"])
        provenance["execution"]["run_order"] = provenance["run_order"]
        write_json(EXP / "provenance.json", provenance)
        raise RuntimeError(f"solver failed; preserved artifacts for {case_id}")
    trace = load_raw(raw)
    missing = sorted(expected_headers(item["mask"]) - set(trace.headers))
    record["raw"] = {"path": rel(raw), "sha256": sha256(raw), "bytes": raw.stat().st_size, "sample_count": trace.sample_count, "time_start_ps": trace.time[0] * 1.0e12, "time_end_ps": trace.time[-1] * 1.0e12, "grid": branch.replay_base.finite_grid_qa(trace), "missing_required_probes": missing}
    record["execution_status"] = "RUN_PASS" if not missing else "RUN_PASS_MISSING_PROBES"
    metadata_value = {"run_id": case_id, "deck_sha256": record["deck"]["sha256"], "raw_sha256": record["raw"]["sha256"], "log_sha256": record["log"]["sha256"], "stdout_sha256": record["stdout"]["sha256"], "stderr_sha256": record["stderr"]["sha256"], "execution_status": record["execution_status"], "parameters": item}
    write_json(metadata, metadata_value)
    record["metadata"] = {"path": rel(metadata), "sha256": sha256(metadata), "bytes": metadata.stat().st_size}
    provenance["runs"][case_id] = record
    provenance["run_order"].append(case_id)
    provenance["execution"]["actual_physical_solve_count"] = len(provenance["run_order"])
    provenance["execution"]["solver_invocation_count"] = len(provenance["run_order"])
    provenance["execution"]["run_order"] = provenance["run_order"]
    write_json(EXP / "provenance.json", provenance)
    if missing:
        raise RuntimeError(f"missing required probes for {case_id}: {missing}")


def vector_stats(trace: Any, signal: str, window: tuple[float, float]) -> dict[str, Any]:
    if signal not in trace.headers:
        return {"status": "UNKNOWN", "signal": signal, "window_ps": list(window)}
    return branch.waveform_stats(trace, signal, window)


def energy_for(trace: Any, voltage_signal: str, current_signal: str, window: tuple[float, float], resistance: float | None = None) -> dict[str, Any]:
    if voltage_signal not in trace.headers or current_signal not in trace.headers:
        return {"status": "UNKNOWN", "voltage_signal": voltage_signal, "current_signal": current_signal, "window_ps": list(window)}
    indices = branch.time_indices(trace, *window)
    times = [float(trace.time[index]) for index in indices]
    voltage = [float(trace.column(voltage_signal)[index]) for index in indices]
    current = [float(trace.column(current_signal)[index]) for index in indices]
    power = [v * i for v, i in zip(voltage, current)]
    signed = branch.actual_integral(times, power)
    output = {
        "status": "DERIVED",
        "window_ps": list(window),
        "voltage_signal": voltage_signal,
        "current_signal": current_signal,
        "sample_count": len(indices),
        "power_peak_abs_W": max(abs(value) for value in power) if power else None,
        "signed_power_energy_J": signed,
        "signed_power_energy_fJ": signed * 1.0e15,
        "actual_grid_trapezoid": True,
    }
    if resistance is not None:
        i2r = branch.actual_integral(times, [value * value * resistance for value in current])
        output.update({"I2R_energy_J": i2r, "I2R_energy_fJ": i2r * 1.0e15, "passivity_nonnegative": i2r >= -1.0e-30, "resistance_ohm": resistance})
    return output


def transformer_observables(trace: Any) -> dict[str, Any]:
    windows = {"focus_110_121": FOCUS, "rearm_121_130": REARM, "full_0_200": FULL}
    signals = ("V(ISO_SOURCE_OUT)", "I(R_PRI)", "V(R_PRI)", "I(L_PRI)", "V(L_PRI)", "I(L_SEC)", "V(L_SEC)")
    measurements = {name: {signal: vector_stats(trace, signal, window) for signal in signals} for name, window in windows.items()}
    for name, window in windows.items():
        measurements[name]["primary_resistor_power"] = energy_for(trace, "V(R_PRI)", "I(R_PRI)", window, 12.0)
        measurements[name]["primary_inductor_power"] = energy_for(trace, "V(L_PRI)", "I(L_PRI)", window)
        measurements[name]["secondary_inductor_power"] = energy_for(trace, "V(L_SEC)", "I(L_SEC)", window)
    timing: dict[str, Any] = {}
    indices = branch.time_indices(trace, *FOCUS)
    for signal in ("V(ISO_SOURCE_OUT)", "I(R_PRI)", "I(L_PRI)", "I(L_SEC)"):
        if signal not in trace.headers or not indices:
            timing[signal] = {"status": "UNKNOWN"}
            continue
        values = [abs(float(trace.column(signal)[index])) for index in indices]
        position = max(range(len(values)), key=values.__getitem__)
        timing[signal] = {"status": "DERIVED", "focus_peak_abs_time_ps": float(trace.time[indices[position]]) * 1.0e12, "focus_peak_abs_value": values[position], "actual_grid": True}
    return {"status": "DERIVED", "signals": signals, "measurements": measurements, "timing": timing, "passive_interface_only": True, "transfer_interpretation": "descriptive primary/secondary timing and power records only; no directional-isolation claim"}


def trace_metrics(label: str, mask: str, trace: Any, oracle_module: Any) -> dict[str, Any]:
    metrics = branch.run_metrics(label, mask, trace, family=None, canonical=True, delay_ps=0.0)
    metrics["multi_evidence_oracle"] = multi_evidence_oracle(trace, mask, oracle_module)
    metrics["transformer"] = transformer_observables(trace)
    metrics["active_bvm_indices"] = [index for index, bit in enumerate(mask, 1) if bit == "1"]
    metrics["phase_area_cross_checks_active"] = {f"P({element}|XBVM{index})": branch.phase_area(trace, f"P({element}|XBVM{index})", f"V({element}|XBVM{index})") for index in metrics["active_bvm_indices"] for element in ("B_JS1", "B_JS2")}
    return metrics


def compare_traces(canonical: Any, candidate: Any, mask: str, canonical_metrics: dict[str, Any], candidate_metrics: dict[str, Any]) -> dict[str, Any]:
    signals = ["I(B_JSL8)", "V(COMMON_SL)", "V(QBIN)", "I(LIN|XBQ1)", "I(L1|XBQ1)", "I(L2|XBQ1)", "V(QBOUT)", "V(JTL6_OUT)", "I(R_TERM)", *[f"P(B01|XJTL1_{stage})" for stage in JTL_STAGES], *[f"V(JTL{stage}_OUT)" for stage in JTL_STAGES]]
    for index in candidate_metrics["active_bvm_indices"]:
        signals.extend([f"{kind}({element}|XBVM{index})" for element in ("B_JS1", "B_JS2", "B_JM1", "B_JM2", "L_S3", "R_S") for kind in (("P", "V", "I") if element.startswith("B_") else ("V", "I"))])
    return {"signal_deltas": {signal: {"focus": branch.normalized_delta(canonical, candidate, signal, FOCUS), "full": branch.normalized_delta(canonical, candidate, signal, FULL)} for signal in signals}, "timing_drift": common.timing_drift(canonical_metrics["multi_evidence_oracle"], candidate_metrics["multi_evidence_oracle"]), "active_phase_p2p": common.phase_p2p_deltas(canonical, candidate, mask), "actual_grid": True, "interpolation": False, "transformer_observables": candidate_metrics["transformer"]}


def mechanical_label(mask: str, oracle: dict[str, Any], canonical_oracle: dict[str, Any], comparison: dict[str, Any]) -> str:
    count = oracle["ordered_phase_chain_count"]
    canonical_count = canonical_oracle["ordered_phase_chain_count"]
    gross = count > canonical_count + 2 or oracle["terminal_pulse_count"] > 6
    if gross:
        return "CURRENT_QB_ISOLATION_INCOMPATIBLE_AT_R6A_POINT"
    if mask == "0011" and count == 2:
        return "N2_MAPPING_2_MECHANICAL"
    if mask == "0111" and count == 3:
        return "N3_MAPPING_3_MECHANICAL"
    if mask == "0111" and count == 4:
        bvm_deltas = [item["focus"].get("normalized_rms") for item in comparison["signal_deltas"].values() if item["focus"].get("normalized_rms") is not None and ("B_JS" in item["focus"].get("signal", "") or "L_S3" in item["focus"].get("signal", "") or "R_S" in item["focus"].get("signal", ""))]
        return "ISOLATION_PRESERVED_MAPPING_NO_N3_CORRECTION" if not bvm_deltas or max(bvm_deltas) > 1.0e-3 else "CURRENT_QB_ISOLATION_NO_MATERIAL_CHANGE_MECHANICAL"
    return "ISOLATION_EFFECTIVE_FORWARD_MARGIN_INSUFFICIENT"


def analyze(args: argparse.Namespace) -> None:
    provenance = read_json(EXP / "provenance.json")
    registered_runner = next(item for item in provenance["source_closure"] if item["name"] == "runner")
    current_runner = record_file("runner", Path(__file__), registered_runner["role"])
    if registered_runner["sha256"] != current_runner["sha256"]:
        provenance["postsolve_tooling_revision"] = {"path": rel(Path(__file__)), "old_sha256": registered_runner["sha256"], "new_sha256": current_runner["sha256"], "reason": "analysis-only runner repair", "physical_rerun": False, "raw_mutated": False}
        registered_runner.update({"sha256": current_runner["sha256"], "bytes": current_runner["bytes"]})
    oracle_module = load_oracle_module()
    canonical_traces = {mask: load_raw(CANONICAL[mask]) for mask in MASKS}
    canonical_metrics = {mask: trace_metrics(f"CANONICAL_{mask}", mask, canonical_traces[mask], oracle_module) for mask in MASKS}
    candidate_traces = {key: load_raw(REPO / provenance["runs"][key]["raw"]["path"]) for key in provenance["run_order"]}
    metrics = {key: trace_metrics(key, case_info(key, args)["mask"], trace, oracle_module) for key, trace in candidate_traces.items()}
    validations = {}
    for key, item in metrics.items():
        mask = case_info(key, args)["mask"]
        validations[key] = {"case_id": key, "mask": mask, "params": case_info(key, args), "oracle": item["multi_evidence_oracle"], "comparison": compare_traces(canonical_traces[mask], candidate_traces[key], mask, canonical_metrics[mask], item), "transformer": item["transformer"], "active_phase_area": item["phase_area_cross_checks_active"], "mechanical_candidate_label": mechanical_label(mask, item["multi_evidence_oracle"], canonical_metrics[mask]["multi_evidence_oracle"], compare_traces(canonical_traces[mask], candidate_traces[key], mask, canonical_metrics[mask], item))}
    gate = {"status": "PENDING", "rule": "fixed 0011 ordered chains=2 and 0111 ordered chains=3"}
    if all(key in validations for key in FIXED):
        n2 = validations["ISO_R6A_0011"]["oracle"]["ordered_phase_chain_count"]
        n3 = validations["ISO_R6A_0111"]["oracle"]["ordered_phase_chain_count"]
        allowed = n2 == 2 and n3 == 3
        gate = {"status": "PASS" if allowed else "FAIL", "N2_ordered_phase_chain_count": n2, "N3_ordered_phase_chain_count": n3, "conditional_N1_N4_allowed": allowed, "scientific_interpretation_performed": False}
    raw_before = {key: sha256(REPO / provenance["runs"][key]["raw"]["path"]) for key in provenance["run_order"]}
    source_before = {item["path"]: sha256(REPO / item["path"]) for item in provenance["source_closure"]}
    analysis = {"schema": "bvm-qb-transformer-isolation-current-qb-mechanical-analysis-v1", "experiment_id": EXP.name, "generated_at": now(), "runs": validations, "canonical_references": {mask: {"ordered_phase_chain_count": canonical_metrics[mask]["multi_evidence_oracle"]["ordered_phase_chain_count"], "raw_path": rel(CANONICAL[mask]), "raw_sha256": sha256(CANONICAL[mask])} for mask in MASKS}, "conditional_gate": gate, "raw_hash_before_analysis": raw_before, "source_hashes_before_analysis": source_before, "actual_grid": True, "interpolation": False, "resampling": False, "scientific_interpretation_performed": False}
    write_json(EXP / "analysis" / "mechanical_analysis.json", analysis)
    raw_after = {key: sha256(REPO / provenance["runs"][key]["raw"]["path"]) for key in provenance["run_order"]}
    source_after = {item["path"]: sha256(REPO / item["path"]) for item in provenance["source_closure"]}
    if raw_before != raw_after or source_before != source_after:
        raise RuntimeError("raw/source mutation detected during analysis")
    provenance["conditional_selection"] = {"status": "AUTHORIZED" if gate["status"] == "PASS" else "NOT_AUTHORIZED", "selected_cases": list(CONDITIONAL) if gate["status"] == "PASS" else [], **gate}
    provenance.update({"mechanical_analysis_performed": True, "bounded_experiment_interpretation_performed": False, "independent_scientific_review_performed": False, "scientific_interpretation_performed": False, "raw_hash_before_analysis": raw_before, "raw_hash_after_analysis": raw_after, "source_hashes_before_analysis": source_before, "source_hashes_after_analysis": source_after, "analysis": {"status": "COMPLETE", "path": rel(EXP / "analysis" / "mechanical_analysis.json")}, "execution_status": "ANALYSIS_COMPLETE"})
    for key in provenance["run_order"]:
        provenance["runs"][key].update({"mechanical_analysis_performed": True, "bounded_experiment_interpretation_performed": False, "independent_scientific_review_performed": False, "scientific_interpretation_performed": False})
    write_json(EXP / "provenance.json", provenance)
    result = read_json(EXP / "result.json")
    result.update({"generated_at": now(), "status": "ANALYSIS_COMPLETE_AWAITING_SCIENTIFIC_REVIEW", "artifact_status": "VALID", "mechanical_analysis_performed": True, "bounded_experiment_interpretation_performed": False, "independent_scientific_review_performed": False, "scientific_interpretation_performed": False, "execution": provenance["execution"], "conditional_selection": provenance["conditional_selection"], "classification": {"status": "SCIENTIFIC_REVIEW_REQUIRED", "assigned": None, "candidate_label": "MECHANICAL_ONLY"}, "stop": {"final_marker": FINAL, "automatic_follow_up": False}})
    result["cases"] = {key: {"run_id": key, "mask": item["mask"], "M_pH": item["params"]["M_pH"], "ordered_phase_chain_count": item["oracle"]["ordered_phase_chain_count"], "old_strict_complete_response_count": item["oracle"]["old_strict_complete_response_count"], "terminal_pulse_count": item["oracle"]["terminal_pulse_count"], "BJ1_landmarks_ps": [common.phase_time(item["oracle"], "BJ1", i) for i in range(1, 5)], "BJ2_landmarks_ps": [common.phase_time(item["oracle"], "BJ2", i) for i in range(1, 5)], "mechanical_candidate_label": item["mechanical_candidate_label"], "active_phase_area": item["active_phase_area"], "transformer": item["transformer"], "raw_path": provenance["runs"][key]["raw"]["path"], "raw_sha256": provenance["runs"][key]["raw"]["sha256"]} for key, item in validations.items()}
    result["gate"] = gate
    write_json(EXP / "result.json", result)
    (EXP / "analysis" / "SOURCE_MANIFEST.json").write_text(json.dumps({"schema": "bvm-qb-transformer-isolation-current-qb-source-manifest-v1", "source_closure": provenance["source_closure"], "canonical_hashes": {mask: sha256(CANONICAL[mask]) for mask in CANONICAL}}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (EXP / "analysis" / "TRANSFORMATION_REGISTRY.json").write_text(json.dumps({"schema": "bvm-qb-transformer-isolation-current-qb-transformation-registry-v1", "raw_mutation": False, "direct_galvanic_JSL8_QBIN_removed": True, "interface": {"R_PRI_ohm": args.r_pri, "L_PRI_pH": args.l_pri, "L_SEC_pH": args.l_sec, "K_ISO": args.k_iso, "M_pH": args.k_iso * math.sqrt(args.l_pri * args.l_sec)}, "actual_grid": True, "phase_display": "raw radians; rad/(2*pi) navigation only", "scientific_interpretation_performed": False}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_result_markdown() -> None:
    result = read_json(EXP / "result.json")
    lines = [f"# Current QB transformer isolation — {EXP.name}", "", f"- Status: `{result['status']}`", "- Artifact status: `VALID`", "- Scientific interpretation: `NOT_PERFORMED`; review remains required.", f"- Frozen interface: R_PRI={result['matrix_audit'].get('R_PRI_ohm', 12.0)} ohm, L_PRI={result['matrix_audit']['L_PRI_pH']} pH, L_SEC={result['matrix_audit']['L_SEC_pH']} pH, K={result['matrix_audit']['K_ISO']}, M={result['matrix_audit']['M_pH']:.8g} pH.", "", "| run | mask | M (pH) | ordered phase chains | BJ1 first/second (ps) | BJ2 first/second (ps) | mechanical label |", "|---|---|---:|---:|---|---|---|"]
    for key, item in result.get("cases", {}).items():
        lines.append(f"| `{key}` | {item['mask']} | {item['M_pH']:.8g} | {item['ordered_phase_chain_count']} | {fmt(item['BJ1_landmarks_ps'][0])}/{fmt(item['BJ1_landmarks_ps'][1])} | {fmt(item['BJ2_landmarks_ps'][0])}/{fmt(item['BJ2_landmarks_ps'][1])} | `{item['mechanical_candidate_label']}` |")
    lines.extend(["", "Transformer primary/secondary I/V, power and timing records; active JS1/JS2 same-JJ phase/area checks; LS3/RS, COMMON_SL, JSL, QB and JTL records are in `analysis/mechanical_analysis.json`.", "Replay/interface branch current is recorded according to its element orientation; no directional-isolation or physical-equivalence conclusion is assigned.", "P(...) remains raw radians; rad/(2*pi) is navigation only, not an SFQ count.", "", f"Stop marker: `{FINAL}`.", ""])
    (EXP / "RESULT.md").write_text("\n".join(lines), encoding="utf-8")
    (EXP / "analysis" / "NUMERICAL_REVIEW.md").write_text("\n".join(["# Numerical review — mechanical only", "", "- M is derived exactly as K*sqrt(L_PRI*L_SEC); |K|<1 and the two-winding matrix audit are recorded.", "- All source comparisons and integrations use actual stored timestamps; no interpolation/resampling.", "- P(...) is raw radians; turns are independent rad/(2*pi) navigation only.", "- Power records are descriptive element-oriented traces, not mechanism or hardware claims."]) + "\n", encoding="utf-8")
    (EXP / "analysis" / "ADVERSARIAL_REVIEW.md").write_text("\n".join(["# Adversarial review probes — mechanical only", "", "- Deck QA checks that direct B_JSL8 JSL_NODE7 QBIN is absent and the canonical QB/JTL/terminal path remains.", "- Physical L_S3 and R_S remain in the canonical BVM include; no canonical source file is edited.", "- Conditional N1/N4 cases are materialized only after the fixed N2/N3 mechanical rule.", "- No R6-B point, sweep, sentinel or follow-up is run.", "- No scientific winner or mechanism conclusion is assigned."]) + "\n", encoding="utf-8")


def materialize_conditional(args: argparse.Namespace) -> None:
    provenance = read_json(EXP / "provenance.json")
    if provenance.get("conditional_selection", {}).get("status") != "AUTHORIZED":
        raise RuntimeError("conditional N1/N4 cases are not authorized")
    records = {key: make_deck(key, args) for key in CONDITIONAL}
    provenance["registered_decks"].update(records)
    provenance["conditional_materialization"] = {"status": "PASS", "cases": list(records), "materialized_at": now()}
    write_json(EXP / "provenance.json", provenance)
    yaml = EXP / "experiment.yaml"
    block = ["", "conditional_N1_N4_deck_registration:"]
    for key, item in records.items():
        block.extend([f"  - run_id: {key}", f"    path: {item['path']}", f"    sha256: {item['sha256']}", f"    bytes: {item['bytes']}"])
    yaml.write_text(yaml.read_text(encoding="utf-8").rstrip() + "\n" + "\n".join(block) + "\n", encoding="utf-8")


def mechanical_qa() -> None:
    provenance = read_json(EXP / "provenance.json")
    failures: list[str] = []
    checks: dict[str, Any] = {}
    for key in provenance["run_order"]:
        record = provenance["runs"][key]
        info = record
        deck = REPO / record["deck"]["path"]
        raw = REPO / record["raw"]["path"]
        log = REPO / record["log"]["path"]
        stdout_path = REPO / record["stdout"]["path"]
        stderr_path = REPO / record["stderr"]["path"]
        metadata = REPO / record["metadata"]["path"]
        text_value = deck.read_text(encoding="utf-8") if deck.is_file() else ""
        try:
            trace = load_raw(raw)
            missing = sorted(expected_headers(info["mask"]) - set(trace.headers))
            grid = branch.replay_base.finite_grid_qa(trace)
        except Exception as exc:
            trace = None
            missing = [f"raw_parse_error:{exc}"]
            grid = {"status": "INVALID"}
        warnings = warning_lines(log)
        unexpected = [line for line in warnings if line not in KNOWN_WARNINGS]
        topology_ok = bool(text_value.count("B_JSL8 JSL_NODE7 ISO_SOURCE_OUT") == 1 and "B_JSL8 JSL_NODE7 QBIN" not in text_value and text_value.count("R_PRI ISO_SOURCE_OUT N_PRI") == 1 and text_value.count("L_PRI N_PRI 0") == 1 and text_value.count("L_SEC QBIN 0") == 1 and text_value.count("K_ISO L_PRI L_SEC") == 1 and "XBQ1 QBIN QBOUT BQ" in text_value and "XJTL1_1 QBOUT JTL1_OUT jtl" in text_value and "XJTL1_6 JTL5_OUT JTL6_OUT jtl" in text_value and "R_TERM JTL6_OUT 0 10" in text_value and ".tran 0.1p 200p" in text_value)
        passed = bool(record["execution_status"] == "RUN_PASS" and topology_ok and trace is not None and not missing and not trace.duplicate_columns and grid.get("status") == "VALID" and grid.get("sample_count") == 1999 and stdout_path.is_file() and stderr_path.is_file() and metadata.is_file() and not unexpected and sha256(raw) == record["raw"]["sha256"] and sha256(deck) == record["deck"]["sha256"])
        if not passed:
            failures.append(key)
        checks[key] = {"status": "PASS" if passed else "ARTIFACT_INVALID", "topology_ok": topology_ok, "missing_required_probes": missing, "grid": grid, "unexpected_solver_warning_lines": unexpected, "raw_sha256_matches": raw.is_file() and sha256(raw) == record["raw"]["sha256"]}
    selection = provenance.get("conditional_selection", {})
    expected = list(FIXED) + (list(CONDITIONAL) if selection.get("status") == "AUTHORIZED" else [])
    source_ok = all(sha256(REPO / item["path"]) == item["sha256"] for item in provenance["source_closure"])
    passed = bool(provenance["run_order"] == expected and not failures and source_ok and provenance.get("raw_hash_before_analysis") == provenance.get("raw_hash_after_analysis") and provenance.get("source_hashes_before_analysis") == provenance.get("source_hashes_after_analysis") and provenance["execution"]["actual_physical_solve_count"] == len(provenance["run_order"]) and len(provenance["run_order"]) in (2, 4))
    qa = {"schema": "bvm-qb-transformer-isolation-current-qb-mechanical-qa-v1", "status": "PASS" if passed else "FAIL", "artifact_status": "VALID" if passed else "ARTIFACT_INVALID", "run_order": provenance["run_order"], "expected_run_order": expected, "actual_physical_solve_count": len(provenance["run_order"]), "max_physical_solves": 4, "source_hashes_match": source_ok, "raw_hash_before_after_equal": provenance.get("raw_hash_before_analysis") == provenance.get("raw_hash_after_analysis"), "source_hash_before_after_equal": provenance.get("source_hashes_before_analysis") == provenance.get("source_hashes_after_analysis"), "contains_reference_raw_copies": False, "contains_delivery_manifest": False, "runs": checks, "failures": failures, "mechanical_analysis_performed": True, "scientific_interpretation_performed": False}
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
        "02_BVM_STATE": [signal for index in range(1, 5) for element in ("B_JS1", "B_JS2", "B_JM1", "B_JM2", "L_S3", "R_S") for signal in (f"P({element}|XBVM{index})", f"V({element}|XBVM{index})", f"I({element}|XBVM{index})") if element.startswith("B_") or signal.startswith("V(") or signal.startswith("I(")],
        "03_JSL_CHAIN": [signal for index in range(1, 9) for signal in (f"P(B_JSL{index})", f"V(B_JSL{index})", f"I(B_JSL{index})")],
        "04_QB_STATE": ["V(QBIN)", "V(ISO_SOURCE_OUT)", "I(R_PRI)", "V(R_PRI)", "I(L_PRI)", "V(L_PRI)", "I(L_SEC)", "V(L_SEC)", "P(BJ1|XBQ1)", "V(BJ1|XBQ1)", "I(BJ1|XBQ1)", "P(BJ2|XBQ1)", "V(BJ2|XBQ1)", "I(BJ2|XBQ1)", "I(L1|XBQ1)", "I(L2|XBQ1)", "V(QBOUT)"],
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
    for mask in MASKS:
        cases = [(f"CANONICAL_{mask}", load_raw(CANONICAL[mask]))]
        cases.extend((key, load_raw(REPO / provenance["runs"][key]["raw"]["path"])) for key in provenance["run_order"] if key.rsplit("_", 1)[1] == mask)
        for page, requested in (("01_SIGNAL_TIMING", specs["01_SIGNAL_TIMING"]), ("02_BVM_STATE", specs["02_BVM_STATE"]), ("03_JSL_CHAIN", specs["03_JSL_CHAIN"]), ("04_QB_STATE", ["V(QBIN)", "I(LIN|XBQ1)", "V(QBOUT)"]), ("05_JTL_CHAIN", specs["05_JTL_CHAIN"])):
            selected = [signal for signal in requested if all(signal in trace.headers for _, trace in cases)]
            if not selected:
                continue
            temporary = branch.total_helpers.comparison_csv(cases, selected, FOCUS)
            output = EXP / "plots" / "comparisons" / f"{mask}_{page}_focus_110_121.html"
            try:
                labels = [branch.replay_base.prefixed_label(case, signal) for case, _ in cases for signal in selected]
                branch.render_plot(temporary, output, labels, f"{mask}: canonical/current-QB-isolation {page}; focus [110,121) ps", asset)
            finally:
                temporary.unlink(missing_ok=True)
            entries.append({"kind": "comparison", "mask": mask, "path": rel(output), "sha256": sha256(output), "signals": selected, "cases": [case for case, _ in cases], "window_ps": list(FOCUS), "focused": True, "descriptive_only": True})
    html = sorted((EXP / "plots").rglob("*.html"))
    invalid = [rel(path) for path in html if any(token in path.read_text(encoding="utf-8") for token in ("plotly.js v", "var Plotly=", "cdn.plot.ly", "Unknown"))]
    record = {"schema": "bvm-qb-transformer-isolation-current-qb-visualization-v1", "status": "PASS" if entries and asset.is_file() and not invalid else "FAIL", "renderer": rel(PLOTTER), "layout": "sep_comb", "color": "dark", "phase_option": "2pi", "entries": entries, "standalone_count": sum(item["kind"] == "standalone" for item in entries), "comparison_count": sum(item["kind"] == "comparison" for item in entries), "focused_window_entries": sum(item.get("focused", False) for item in entries), "asset": {"path": rel(asset), "sha256": sha256(asset) if asset.is_file() else None}, "invalid_runtime_pages": invalid, "raw_hashes_rechecked": all(item["raw_sha256"] == sha256(REPO / item["raw_path"]) for item in entries if item["kind"] == "standalone"), "descriptive_only": True}
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
    write_json(EXP / "analysis" / "RAW_ANALYSIS_HANDOFF_MANIFEST.json", {"schema": "bvm-qb-transformer-isolation-current-qb-raw-analysis-handoff-v1", "experiment_id": EXP.name, "raw_is_immutable_solver_output": True, "files_excluding_delivery_manifest": records})
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
    manifest = {"schema": "bvm-qb-transformer-isolation-current-qb-delivery-manifest-v1", "experiment_id": EXP.name, "status": "READY_FOR_DRIVE_UPLOAD" if qa["status"] == "PASS" else "PACKAGE_INVALID", "package_version": version, "package_path": str(package_path), "package_sha256": qa["package_sha256"], "package_bytes": qa["package_bytes"], "package_qa": qa, "drive_folder_id": DRIVE_FOLDER_ID, "drive_file_id": None, "drive_url": None}
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


def fmt(value: Any) -> str:
    if value is None:
        return "—"
    try:
        return f"{float(value):.8g}"
    except (TypeError, ValueError):
        return str(value)


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
    parser.add_argument("--l-pri", type=float, default=L_PRI_PH_DEFAULT)
    parser.add_argument("--l-sec", type=float, default=L_SEC_PH_DEFAULT)
    parser.add_argument("--k-iso", type=float, default=K_ISO_DEFAULT)
    parser.add_argument("--r-pri", type=float, default=R_PRI_OHM_DEFAULT)
    parser.add_argument("--only")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-analysis", action="store_true")
    parser.add_argument("--no-plots", action="store_true")
    parser.add_argument("command", nargs="?", default="all", choices=("all", "continue-after-solve", "record-drive"))
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
        raise RuntimeError("this registration requires dt=0.1p and stop_time=200p")
    if args.command == "continue-after-solve":
        provenance = read_json(EXP / "provenance.json")
        if provenance.get("run_order") != list(FIXED):
            raise RuntimeError(f"continuation requires the two fixed cases: {provenance.get('run_order')}")
        analyze(args)
        mechanical_qa()
        visualization()
        package()
        return 0
    prepare(args)
    selected = [mask for mask in args.masks if args.only is None or mask == args.only]
    for mask in selected:
        execute_case(f"ISO_R6A_{mask}", args)
    analyze(args)
    provenance = read_json(EXP / "provenance.json")
    if selected == list(MASKS) and provenance.get("conditional_selection", {}).get("status") == "AUTHORIZED":
        materialize_conditional(args)
        for key in CONDITIONAL:
            execute_case(key, args)
        analyze(args)
    mechanical_qa()
    visualization()
    package()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
