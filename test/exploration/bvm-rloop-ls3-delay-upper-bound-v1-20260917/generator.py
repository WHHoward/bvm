#!/usr/bin/env python3
"""Execute and package the registered LS3 0.5-ps upper-bound experiment."""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
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
import bvm_qb_rloop_ls3_population_validation as common

branch = common.branch_helpers
SOURCE_INPUTS = REPO / "test" / "exploration" / "bvm-qb-threshold-ordering-boundary-search-v1-20260911" / "inputs"
REFERENCE_ROOT = REPO / "test" / "exploration" / "bvm-qb-threshold-ordering-boundary-search-v1-20260911" / "references" / "canonical_baseline"
PREVIOUS_WINDOW = REPO / "test" / "exploration" / "bvm-rloop-ls3-delay-window-v1-20260916"
PREVIOUS_BRANCH = REPO / "test" / "exploration" / "bvm-rloop-branch-timing-decomposition-v1-20260916"
CANONICAL = {mask: REFERENCE_ROOT / mask / "raw.csv" for mask in ("0011", "0111")}
CANONICAL_DECKS = {mask: REFERENCE_ROOT / mask / "deck.cir" for mask in ("0011", "0111")}
EXPECTED_HEAD = "1348140f17f0d9467dc42238eaa1e252e877e07a"
MASKS = ("0011", "0111")
FIXED = ("LS3_DELAY0P5_0011", "LS3_DELAY0P5_0111")
CONDITIONAL = ("LS3_DELAY0P6_0011", "LS3_DELAY0P6_0111")
DELAY_INFO = {"0P5": (0.5, 5), "0P6": (0.6, 6)}
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
multi_evidence_oracle = common.multi_evidence_oracle
load_oracle_module = common.load_oracle_module

def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")

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
    match = re.fullmatch(r"LS3_DELAY(0P5|0P6)_(0011|0111)", case_id)
    if not match:
        raise RuntimeError(f"invalid case id: {case_id}")
    point, mask = match.groups()
    delay, shift = DELAY_INFO[point]
    return {"case_id": case_id, "point": point, "mask": mask, "delay_ps": delay, "stored_sample_shift": shift}

def reference_paths() -> dict[str, Path]:
    return {
        "0P2_0011": PREVIOUS_WINDOW / "runs" / "LS3_DELAY0P2_0011" / "raw.csv",
        "0P2_0111": PREVIOUS_WINDOW / "runs" / "LS3_DELAY0P2_0111" / "raw.csv",
        "0P3_0011": PREVIOUS_BRANCH / "runs" / "LS3_DELAY0P3_0011" / "raw.csv",
        "0P3_0111": PREVIOUS_BRANCH / "runs" / "LS3_DELAY0P3_0111" / "raw.csv",
        "0P4_0011": PREVIOUS_WINDOW / "runs" / "LS3_DELAY0P4_0011" / "raw.csv",
        "0P4_0111": PREVIOUS_WINDOW / "runs" / "LS3_DELAY0P4_0111" / "raw.csv",
    }

def delay_values(values: list[float], times: list[str], shift: int) -> list[float]:
    start = next(i for i, token in enumerate(times) if abs(float(token) * 1e12 - 110.0) < 1e-9)
    result: list[float] = []
    for index in range(len(times)):
        if index < start:
            result.append(values[index])
        elif index < start + shift:
            result.append(values[start])
        else:
            result.append(values[index - shift])
    return result

def write_source(path: Path, mask: str, delay: float, shift: int) -> dict[str, Any]:
    times, strings, values = branch.source_tokens(CANONICAL[mask])
    columns = {f"XBVM{index}": f"I(L_S3|XBVM{index})" for index in range(1, 5)}
    replay = {instance: delay_values(values[column], times, shift) for instance, column in columns.items()}
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["time_s", "time_ps", *[f"I_CANONICAL_LS3_{x}_A" for x in columns], *[f"I_LS3_REPLAY_{x}_A" for x in columns]])
        for row, token in enumerate(times):
            writer.writerow([token, f"{float(token) * 1e12:.17g}", *[branch.current_token(values[columns[x]][row]) for x in columns], *[branch.current_token(replay[x][row]) for x in columns]])
    start = next(i for i, token in enumerate(times) if abs(float(token) * 1e12 - 110.0) < 1e-9)
    return {"path": rel(path), "sha256": sha256(path), "bytes": path.stat().st_size, "authority_raw": rel(CANONICAL[mask]), "authority_raw_sha256": sha256(CANONICAL[mask]), "authority_columns": list(columns.values()), "source_column_sha256": {x: sha256_text("\n".join(strings[column]) + "\n") for x, column in columns.items()}, "point_count": len(times), "start_sample_index": start, "start_time_ps": float(times[start]) * 1e12, "delay_ps": delay, "stored_sample_shift": shift, "pre_110_nonanticipation": all(replay[x][i] == values[columns[x]][i] for x in columns for i, token in enumerate(times) if float(token) * 1e12 < 110.0), "hold_rule_check": all(replay[x][i] == values[columns[x]][start] for x in columns for i in range(start, start + shift)), "post_shift_rule_check": all(replay[x][i] == values[columns[x]][i - shift] for x in columns for i in range(start + shift, len(times))), "interpolation": False, "resampling": False, "amplitude_scaling": False, "sign_change": False, "positive_direction": "node6 -> node10"}

def make_deck(case_id: str) -> dict[str, Any]:
    item = case_info(case_id)
    times, _, values = branch.source_tokens(CANONICAL[item["mask"]])
    replay = {f"XBVM{i}": delay_values(values[f"I(L_S3|XBVM{i})"], times, item["stored_sample_shift"]) for i in range(1, 5)}
    source_path = EXP / "inputs" / "replay_sources" / f"{case_id}_branch_current.csv"
    source = write_source(source_path, item["mask"], item["delay_ps"], item["stored_sample_shift"])
    payloads = {instance: "PWL(" + " ".join(token for row, time_token in enumerate(times) for token in (branch.time_token_ps(time_token), branch.current_token(replay[instance][row]))) + ")" for instance in replay}
    deck = EXP / "runs" / case_id / "deck.cir"
    deck.parent.mkdir(parents=True, exist_ok=True)
    deck.write_text(branch.transformed_deck(item["mask"], "LS3", case_id, payloads, deck.parent), encoding="utf-8")
    return {**item, "path": rel(deck), "sha256": sha256(deck), "bytes": deck.stat().st_size, "source": source, "payload_sha256": {key: sha256_text(payloads[key]) for key in payloads}, "topology": "validated LS3-only replay; canonical QB/JSL/JTL/terminal unchanged"}


def source_inventory() -> list[dict[str, Any]]:
    records = [
        record_file("runner", Path(__file__), "upper-bound generator/analyzer/plotter/packager"),
        record_file("run_sh", EXP / "run.sh", "user-facing runner"),
        record_file("jjmit", SOURCE_INPUTS / "jjmit.cir", "canonical JJ model"),
        record_file("bvm", SOURCE_INPUTS / "bvm_jm2_connected.cir", "canonical BVM template"),
        record_file("qb", SOURCE_INPUTS / "BQ_parameterized_bjs400_rj2.cir", "canonical QB include"),
        record_file("jtl", SOURCE_INPUTS / "jtl2.cir", "canonical JTL include"),
        record_file("solver", REPO / "build" / "josim-cli", "recorded JoSIM solver"),
        record_file("plotter", REPO / "scripts" / "josim-plot2.py", "standard renderer"),
        record_file("branch_helper", REPO / "scripts" / "bvm_qb_rloop_branch_timing_decomposition.py", "validated LS3 topology/metrics"),
        record_file("population_helper", REPO / "scripts" / "bvm_qb_rloop_ls3_population_validation.py", "read-only oracle helper"),
        record_file("oracle", REPO / "test" / "exploration" / "bvm-population-scaling-rj2p12-l1p14-l2p20-ib260-rj32-bjs400-v1-20260910" / "analysis" / "population_oracle.py", "historical multi-evidence oracle"),
        record_file("previous_branch_result", PREVIOUS_BRANCH / "result.json", "read-only 0.3 context"),
        record_file("previous_window_result", PREVIOUS_WINDOW / "result.json", "read-only 0.2/0.4 context"),
    ]
    for mask in MASKS:
        records.extend([record_file(f"canonical_{mask}_raw", CANONICAL[mask], "read-only canonical raw"), record_file(f"canonical_{mask}_deck", CANONICAL_DECKS[mask], "read-only canonical deck")])
    for key, path in reference_paths().items():
        records.append(record_file(f"reference_{key}", path, "read-only delay reference; not copied"))
    return records


def prepare(args: argparse.Namespace) -> None:
    if git_head() != EXPECTED_HEAD or remote_head() != EXPECTED_HEAD:
        raise RuntimeError("HEAD/remote does not match frozen parent")
    if tuple(args.masks) != MASKS or tuple(args.delays) != ("0.5",):
        raise RuntimeError("registered run.sh parameters must be masks 0011/0111 and delay 0.5")
    existing_artifacts = [path for path in EXP.iterdir() if path.name not in {"run.sh", "generator.py", "__pycache__"}] if EXP.exists() else []
    if existing_artifacts:
        if not args.force:
            raise RuntimeError(f"experiment exists; use --force for timestamped backup: {EXP}")
        backup = EXP.with_name(f"{EXP.name}.attempt-{datetime.now().strftime('%Y%m%dT%H%M%S')}")
        shutil.move(str(EXP), str(backup))
    EXP.mkdir(parents=True, exist_ok=True)
    for directory in ("runs", "analysis", "plots", "inputs/replay_sources"):
        (EXP / directory).mkdir(parents=True, exist_ok=True)
    canonical = {mask: load_raw(path) for mask, path in CANONICAL.items()}
    direction = {mask: branch.branch_direction_audit(trace, mask) for mask, trace in canonical.items()}
    if any(item["status"] != "PASS" for item in direction.values()):
        raise RuntimeError(f"canonical branch audit failed: {direction}")
    records = {case_id: make_deck(case_id) for case_id in FIXED}
    (EXP / "PREFLIGHT.md").write_text(f"""# LS3 ideal timing upper bound — {EXP.name}

{CONTRACT}

- Parent HEAD: {EXPECTED_HEAD}; remote bvm/master: {EXPECTED_HEAD}.
- Study phase: EXPLORATORY; role: Experimental Operator + Evidence Packager.
- Initial fixed cases are LS3_DELAY0P5_0011 and LS3_DELAY0P5_0111. The 0.6-ps pair is conditional on the fixed mechanical gate.
- Validated LS3-only topology: physical R_S retained, physical L_S3 replaced by a same-instance ideal I(L_S3) replay; canonical QB/JSL/JTL/terminal unchanged.
- t0=110 ps; 0.5 ps is 5 stored samples and conditional 0.6 ps is 6 stored samples. The hold interval and later index shift use the actual stored grid.
- No interpolation, smoothing, resampling, scaling, polarity change, N1/N4, other delay, sentinel or timestep sweep.

## Authorized matrix

1. LS3_DELAY0P5_0011
2. LS3_DELAY0P5_0111
3. Conditional only if fixed N2=2, N3=3, and N2 second response/re-arm remains present: LS3_DELAY0P6_0011 and LS3_DELAY0P6_0111

Maximum new physical solves: 4. Navigation/phase turns are diagnostics, not literal SFQ counts.

## Runner

    chmod +x run.sh
    ./run.sh --dry-run
    ./run.sh

Edit only the USER-EDITABLE PARAMETERS block. Default raw overwrite is refused; --force creates a timestamped sibling backup.

Canonical branch direction/KCL audit: {json.dumps({mask: item["status"] for mask, item in direction.items()})}.
Final state: {FINAL}; scientific interpretation is not performed.
""", encoding="utf-8")
    (EXP / "README.md").write_text(f"""# {EXP.name}

Run ./run.sh --dry-run to inspect the registered parent, cases and exact JoSIM command without solving. The default runs the 0.5-ps pair, then adds 0.6 ps only when the preregistered N2/N3 mechanical condition passes. Raw evidence is immutable and phase turns are navigation diagnostics, not SFQ counts.
""", encoding="utf-8")
    (EXP / "experiment.yaml").write_text("\n".join([
        "schema_version: bvm-rloop-ls3-delay-upper-bound-v1",
        f"id: {EXP.name}",
        "study_phase: EXPLORATORY",
        "role: Experimental Operator + Evidence Packager",
        "status: PREFLIGHT_PASS",
        f"registration_head: {EXPECTED_HEAD}",
        f"remote_bvm_master_at_registration: {EXPECTED_HEAD}",
        f"contract_sentence: {CONTRACT}",
        "scientific_review_authorized: false",
        "authorized_matrix:",
        "  fixed: [LS3_DELAY0P5_0011, LS3_DELAY0P5_0111]",
        "  conditional: [LS3_DELAY0P6_0011, LS3_DELAY0P6_0111]",
        "  maximum_new_physical_solves: 4",
        "frozen:",
        "  t0_ps: 110.0",
        "  dt_ps: 0.1",
        "  fixed_delay_ps: 0.5",
        "  conditional_delay_ps: 0.6",
        "  fixed_shift_samples: 5",
        "  conditional_shift_samples: 6",
        "  stop_time_ps: 200.0",
        "  no_interpolation: true",
        "  no_scaling: true",
        "",
        "fixed_deck_registration:",
    ] + [f"  - run_id: {key}\n    path: {item['path']}\n    sha256: {item['sha256']}\n    source_csv: {item['source']['path']}\n    source_csv_sha256: {item['source']['sha256']}" for key, item in records.items()] + [
        "",
        "reference_policy: accepted 0.2/0.3/0.4 raw referenced by hash only",
        "scientific_classification: NOT_ASSIGNED_SCIENTIFIC_REVIEW_REQUIRED",
        "",
    ]), encoding="utf-8")
    closure = source_inventory()
    provenance = {"schema": "bvm-rloop-ls3-delay-upper-bound-provenance-v1", "experiment_id": EXP.name, "created_at": now(), "registration_head": EXPECTED_HEAD, "remote_bvm_master_at_registration": EXPECTED_HEAD, "contract_sentence": CONTRACT, "scientific_review_authorized": False, "mechanical_analysis_performed": False, "bounded_experiment_interpretation_performed": False, "independent_scientific_review_performed": False, "scientific_interpretation_performed": False, "solver": branch.replay_base.solver_context(), "source_closure": closure, "canonical_raw_hashes": {mask: sha256(path) for mask, path in CANONICAL.items()}, "previous_reference_hashes": {rel(path): sha256(path) for path in [*reference_paths().values(), PREVIOUS_BRANCH / "result.json", PREVIOUS_WINDOW / "result.json"]}, "branch_direction_audit": direction, "frozen": {"topology": "canonical BVM -> COMMON_SL -> JSL1..8 -> canonical QB -> JTL1..6 -> terminal", "intervention": "same-instance ideal I(L_S3) replay; physical R_S", "t0_ps": 110.0, "delays_ps": [0.5, 0.6], "stored_shifts": [5, 6], "dt_ps": 0.1, "stop_ps": 200.0, "windows_ps": [list(FULL), list(FOCUS), list(REARM)], "no_interpolation": True, "no_resampling": True, "no_amplitude_scaling": True}, "authorized_matrix": {"fixed": list(FIXED), "conditional": list(CONDITIONAL), "maximum_physical_solves": 4, "conditional_gate": "fixed N2=2/N3=3 and N2 second response/re-arm present", "no_other_solve": True}, "registered_decks": records, "runs": {}, "run_order": [], "execution": {"authorized_physical_solve_count": 4, "actual_physical_solve_count": 0, "solver_invocation_count": 0, "run_order": []}, "conditional_0p6": {"status": "PENDING"}, "analysis": {"status": "PENDING"}, "qa": {"status": "PENDING"}, "visualization": {"status": "PENDING"}, "package": {"status": "PENDING"}, "stop": {"final_marker": None, "automatic_follow_up": False}}
    write_json(EXP / "provenance.json", provenance)
    write_json(EXP / "result.json", {"schema": "bvm-rloop-ls3-delay-upper-bound-result-v1", "experiment_id": EXP.name, "generated_at": now(), "status": "PREFLIGHT_PASS", "artifact_status": "PENDING", "scientific_review_authorized": False, "mechanical_analysis_performed": False, "bounded_experiment_interpretation_performed": False, "independent_scientific_review_performed": False, "scientific_interpretation_performed": False, "execution": provenance["execution"], "cases": {key: {"status": "AUTHORIZED_NOT_RUN"} for key in [*FIXED, *CONDITIONAL]}, "timing_window": {"status": "PENDING"}, "classification": {"status": "SCIENTIFIC_REVIEW_REQUIRED", "assigned": None, "candidate_label": None}, "stop": {"final_marker": None, "automatic_follow_up": False}})


def dry_run(args: argparse.Namespace) -> None:
    print(f"experiment={EXP.name}")
    print(f"parent_sha={EXPECTED_HEAD}")
    print(f"masks={' '.join(args.masks)}")
    for case_id in [f"LS3_DELAY0P5_{mask}" for mask in args.masks] + [f"LS3_DELAY0P6_{mask}" for mask in args.masks]:
        item = case_info(case_id)
        print(f"case_id={case_id} delay_ps={item['delay_ps']} shift_samples={item['stored_sample_shift']} deck={EXP/'runs'/case_id/'deck.cir'} raw={EXP/'runs'/case_id/'raw.csv'}")
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
        raise RuntimeError(f"case not registered/executable: {case_id}")
    order = [*FIXED, *CONDITIONAL]
    expected = [key for key in order[:order.index(case_id)] if key in provenance["run_order"]]
    if provenance["run_order"] != expected:
        raise RuntimeError(f"wrong run order before {case_id}: {provenance['run_order']}")
    deck = REPO / provenance["registered_decks"][case_id]["path"]
    raw, log, stdout_path, stderr_path, metadata = [deck.parent / name for name in ("raw.csv", "run.log", "stdout.txt", "stderr.txt", "metadata.json")]
    if any(path.exists() for path in (raw, log, stdout_path, stderr_path, metadata)):
        raise RuntimeError(f"refusing overwrite/retry: {case_id}")
    command = [args.josim_bin, "-a", "1", "-o", str(raw), str(deck)]
    started = now()
    clock = time.monotonic()
    completed = subprocess.run(command, cwd=REPO, capture_output=True, text=True, check=False)
    runtime = time.monotonic() - clock
    finished = now()
    stdout_path.write_text(completed.stdout, encoding="utf-8")
    stderr_path.write_text(completed.stderr, encoding="utf-8")
    log.write_text(f"experiment={EXP.name}\nrun_id={case_id}\nparent_commit={EXPECTED_HEAD}\nstarted_at={started}\nfinished_at={finished}\nruntime_seconds={runtime:.6f}\ncommand={' '.join(command)}\nexit_code={completed.returncode}\nstdout_path={rel(stdout_path)}\nstderr_path={rel(stderr_path)}\n", encoding="utf-8")
    item = case_info(case_id)
    record = {"run_id": case_id, **item, "parent_commit": EXPECTED_HEAD, "command": command, "runtime_seconds": runtime, "started_at": started, "finished_at": finished, "deck": {"path": rel(deck), "sha256": sha256(deck), "bytes": deck.stat().st_size}, "stdout": {"path": rel(stdout_path), "sha256": sha256(stdout_path), "bytes": stdout_path.stat().st_size}, "stderr": {"path": rel(stderr_path), "sha256": sha256(stderr_path), "bytes": stderr_path.stat().st_size}, "log": {"path": rel(log), "sha256": sha256(log), "bytes": log.stat().st_size}, "solver": {**branch.replay_base.solver_context(), "binary_sha256": sha256(Path(args.josim_bin))}, "physical_solve_this_experiment": True, "raw_immutable": True, "mechanical_analysis_performed": False, "scientific_interpretation_performed": False}
    if completed.returncode != 0 or not raw.is_file() or raw.stat().st_size == 0:
        record["execution_status"] = "SOLVER_FAIL"
        record["raw"] = {"path": rel(raw), "exists": raw.is_file(), "sha256": sha256(raw) if raw.is_file() else None, "bytes": raw.stat().st_size if raw.is_file() else None}
        provenance["runs"][case_id] = record
        provenance["run_order"].append(case_id)
        provenance["execution"]["actual_physical_solve_count"] = len(provenance["run_order"])
        provenance["execution"]["solver_invocation_count"] = len(provenance["run_order"])
        write_json(EXP / "provenance.json", provenance)
        raise RuntimeError(f"solver failed: {case_id}")
    trace = load_raw(raw)
    missing = sorted(branch.expected_headers(load_raw(CANONICAL[item["mask"]]), "LS3") - set(trace.headers))
    record["raw"] = {"path": rel(raw), "sha256": sha256(raw), "bytes": raw.stat().st_size, "sample_count": trace.sample_count, "time_start_ps": trace.time[0] * 1e12, "time_end_ps": trace.time[-1] * 1e12, "grid": branch.replay_base.finite_grid_qa(trace), "missing_required_probes": missing}
    record["solver_warning_lines"] = warning_lines(log)
    record["execution_status"] = "RUN_PASS" if not missing else "RUN_PASS_MISSING_PROBES"
    record["metadata"] = {"path": rel(metadata), "deck_sha256": sha256(deck), "raw_sha256": sha256(raw), "log_sha256": sha256(log), "stdout_sha256": sha256(stdout_path), "stderr_sha256": sha256(stderr_path)}
    write_json(metadata, record["metadata"])
    provenance["runs"][case_id] = record
    provenance["run_order"].append(case_id)
    provenance["execution"]["actual_physical_solve_count"] = len(provenance["run_order"])
    provenance["execution"]["solver_invocation_count"] = len(provenance["run_order"])
    provenance["execution"]["run_order"] = provenance["run_order"]
    write_json(EXP / "provenance.json", provenance)
    if missing:
        raise RuntimeError(f"missing probes: {case_id} {missing}")


def trace_metrics(label: str, mask: str, trace: Any, delay: float | None, oracle_module: Any) -> dict[str, Any]:
    metrics = branch.run_metrics(label, mask, trace, family=None if delay is None else "LS3", canonical=delay is None, delay_ps=delay)
    metrics["multi_evidence_oracle"] = multi_evidence_oracle(trace, mask, oracle_module)
    metrics["active_bvm_indices"] = [index for index, bit in enumerate(mask, 1) if bit == "1"]
    metrics["phase_area_cross_checks_active"] = {f"P({element}|XBVM{index})": branch.phase_area(trace, f"P({element}|XBVM{index})", f"V({element}|XBVM{index})") for index in metrics["active_bvm_indices"] for element in ("B_JS1", "B_JS2")}
    return metrics


def compare_traces(canonical: Any, candidate: Any, mask: str, canonical_metrics: dict[str, Any], candidate_metrics: dict[str, Any]) -> dict[str, Any]:
    signals = ["I(B_JSL8)", "V(COMMON_SL)", "V(QBIN)", "I(LIN|XBQ1)", "I(L1|XBQ1)", "I(L2|XBQ1)", "V(QBOUT)", "V(JTL6_OUT)", "I(R_TERM)", *[f"P(B01|XJTL1_{stage})" for stage in JTL_STAGES], *[f"V(JTL{stage}_OUT)" for stage in JTL_STAGES]]
    for index in candidate_metrics["active_bvm_indices"]:
        signals.extend([f"{kind}({element}|XBVM{index})" for element in ("B_JS1", "B_JS2") for kind in ("P", "V", "I")])
    return {"signal_deltas": {signal: {"focus": branch.normalized_delta(canonical, candidate, signal, FOCUS), "full": branch.normalized_delta(canonical, candidate, signal, FULL)} for signal in signals}, "timing_drift": common.timing_drift(canonical_metrics["multi_evidence_oracle"], candidate_metrics["multi_evidence_oracle"]), "active_phase_p2p": common.phase_p2p_deltas(canonical, candidate, mask), "actual_grid": True, "interpolation": False}


def analyze(args: argparse.Namespace) -> None:
    provenance = read_json(EXP / "provenance.json")
    registered_runner = next(item for item in provenance["source_closure"] if item["name"] == "runner")
    current_runner = record_file("runner", Path(__file__), registered_runner["role"])
    if registered_runner["sha256"] != current_runner["sha256"]:
        provenance["postsolve_tooling_revision"] = {"path": rel(Path(__file__)), "old_sha256": registered_runner["sha256"], "new_sha256": current_runner["sha256"], "reason": "analysis-only runner repair", "physical_rerun": False, "raw_mutated": False}
        registered_runner.update({"sha256": current_runner["sha256"], "bytes": current_runner["bytes"]})
    oracle_module = load_oracle_module()
    run_order = provenance["run_order"]
    canonical_traces = {mask: load_raw(CANONICAL[mask]) for mask in MASKS}
    canonical_metrics = {mask: trace_metrics(f"CANONICAL_{mask}", mask, canonical_traces[mask], None, oracle_module) for mask in MASKS}
    traces = {case_id: load_raw(REPO / provenance["runs"][case_id]["raw"]["path"]) for case_id in run_order}
    metrics = {case_id: trace_metrics(case_id, case_info(case_id)["mask"], traces[case_id], case_info(case_id)["delay_ps"], oracle_module) for case_id in run_order}
    validations = {case_id: {"case_id": case_id, "mask": case_info(case_id)["mask"], "delay_ps": case_info(case_id)["delay_ps"], "oracle": metrics[case_id]["multi_evidence_oracle"], "comparison": compare_traces(canonical_traces[case_info(case_id)["mask"]], traces[case_id], case_info(case_id)["mask"], canonical_metrics[case_info(case_id)["mask"]], metrics[case_id]), "L1_rearm": metrics[case_id]["qb"]["rearm_signs"].get("I(L1|XBQ1)"), "JSL8_rearm": metrics[case_id]["source"]["rearm_signs"].get("I(B_JSL8)"), "bridge": metrics[case_id]["bridge"], "active_phase_area": metrics[case_id]["phase_area_cross_checks_active"]} for case_id in run_order}
    gate = {"status": "PENDING"}
    if all(key in validations for key in FIXED):
        n2 = validations["LS3_DELAY0P5_0011"]["oracle"]
        n3 = validations["LS3_DELAY0P5_0111"]["oracle"]
        second = bool(n2["ordered_phase_chains"][1]["complete_ordered_phase_chain"])
        rearm = validations["LS3_DELAY0P5_0011"]["L1_rearm"]
        allowed = n2["ordered_phase_chain_count"] == 2 and n3["ordered_phase_chain_count"] == 3 and second and rearm.get("status") == "DERIVED"
        gate = {"status": "PASS" if allowed else "FAIL", "N2_ordered_phase_chain_count": n2["ordered_phase_chain_count"], "N3_ordered_phase_chain_count": n3["ordered_phase_chain_count"], "N2_second_response_present": second, "N2_rearm_present": rearm.get("status") == "DERIVED", "conditional_0p6_allowed": allowed, "scientific_interpretation_performed": False}
    refs = {}
    for key, path in reference_paths().items():
        trace = load_raw(path)
        mask = key.rsplit("_", 1)[1]
        oracle = multi_evidence_oracle(trace, mask, oracle_module)
        refs[key] = {"raw_path": rel(path), "raw_sha256": sha256(path), "mask": mask, "oracle": oracle, "read_only_context": True}
    table = {
        "0.2": {"N2": refs["0P2_0011"]["oracle"]["ordered_phase_chain_count"], "N3": refs["0P2_0111"]["oracle"]["ordered_phase_chain_count"]},
        "0.3": {"N2": refs["0P3_0011"]["oracle"]["ordered_phase_chain_count"], "N3": refs["0P3_0111"]["oracle"]["ordered_phase_chain_count"]},
        "0.4": {"N2": refs["0P4_0011"]["oracle"]["ordered_phase_chain_count"], "N3": refs["0P4_0111"]["oracle"]["ordered_phase_chain_count"]},
        "0.5": {"N2": validations.get("LS3_DELAY0P5_0011", {}).get("oracle", {}).get("ordered_phase_chain_count"), "N3": validations.get("LS3_DELAY0P5_0111", {}).get("oracle", {}).get("ordered_phase_chain_count")},
        "0.6": {"N2": validations.get("LS3_DELAY0P6_0011", {}).get("oracle", {}).get("ordered_phase_chain_count"), "N3": validations.get("LS3_DELAY0P6_0111", {}).get("oracle", {}).get("ordered_phase_chain_count")},
    }
    raw_before = {key: sha256(REPO / provenance["runs"][key]["raw"]["path"]) for key in run_order}
    ref_names = ("canonical_", "previous_", "reference_")
    ref_before = {item["path"]: sha256(REPO / item["path"]) for item in provenance["source_closure"] if item["name"].startswith(ref_names)}
    analysis = {"schema": "bvm-rloop-ls3-delay-upper-bound-mechanical-analysis-v1", "experiment_id": EXP.name, "generated_at": now(), "new_cases": metrics, "validations": validations, "read_only_timing_window_references": refs, "conditional_gate": gate, "timing_window_table": table, "raw_hash_before_analysis": raw_before, "reference_hashes_before_analysis": ref_before, "actual_grid": True, "interpolation": False, "resampling": False, "scientific_interpretation_performed": False}
    write_json(EXP / "analysis" / "mechanical_analysis.json", analysis)
    raw_after = {key: sha256(REPO / provenance["runs"][key]["raw"]["path"]) for key in run_order}
    ref_after = {item["path"]: sha256(REPO / item["path"]) for item in provenance["source_closure"] if item["name"].startswith(ref_names)}
    if raw_before != raw_after or ref_before != ref_after:
        raise RuntimeError("raw/reference mutation detected")
    provenance["conditional_0p6"] = {"status": "AUTHORIZED" if gate.get("status") == "PASS" else "NOT_AUTHORIZED", **gate}
    provenance.update({"mechanical_analysis_performed": True, "bounded_experiment_interpretation_performed": False, "independent_scientific_review_performed": False, "scientific_interpretation_performed": False, "raw_hash_before_analysis": raw_before, "raw_hash_after_analysis": raw_after, "reference_hashes_before_analysis": ref_before, "reference_hashes_after_analysis": ref_after, "analysis": {"status": "COMPLETE", "path": rel(EXP / "analysis" / "mechanical_analysis.json")}, "execution_status": "ANALYSIS_COMPLETE"})
    for key in run_order:
        provenance["runs"][key].update({"mechanical_analysis_performed": True, "bounded_experiment_interpretation_performed": False, "independent_scientific_review_performed": False, "scientific_interpretation_performed": False})
    write_json(EXP / "provenance.json", provenance)
    result = read_json(EXP / "result.json")
    result.update({"generated_at": now(), "status": "ANALYSIS_COMPLETE_AWAITING_SCIENTIFIC_REVIEW", "artifact_status": "VALID", "mechanical_analysis_performed": True, "bounded_experiment_interpretation_performed": False, "independent_scientific_review_performed": False, "scientific_interpretation_performed": False, "execution": provenance["execution"], "conditional_gate": gate, "conditional_0p6": {"status": "AUTHORIZED" if gate.get("status") == "PASS" else "NOT_AUTHORIZED", "cases": list(CONDITIONAL) if gate.get("status") == "PASS" else []}, "classification": {"status": "SCIENTIFIC_REVIEW_REQUIRED", "assigned": None}, "stop": {"final_marker": FINAL, "automatic_follow_up": False}})
    result["cases"] = {key: {"run_id": key, "mask": case_info(key)["mask"], "delay_ps": case_info(key)["delay_ps"], "ordered_phase_chain_count": validations[key]["oracle"]["ordered_phase_chain_count"], "old_strict_complete_response_count": validations[key]["oracle"]["old_strict_complete_response_count"], "jtl6_cluster_count": validations[key]["oracle"]["jtl6_cluster_count"], "terminal_pulse_count": validations[key]["oracle"]["terminal_pulse_count"], "terminal_total_area_over_phi0": validations[key]["oracle"]["terminal_total_area_over_phi0"], "descriptive_candidate_label": validations[key]["oracle"]["descriptive_candidate_label"], "BJ1_landmarks_ps": [common.phase_time(validations[key]["oracle"], "BJ1", i) for i in range(1, 5)], "BJ2_landmarks_ps": [common.phase_time(validations[key]["oracle"], "BJ2", i) for i in range(1, 5)], "timing_drift_max_ps": validations[key]["comparison"]["timing_drift"]["max_abs_delta_ps"], "L1_rearm": validations[key]["L1_rearm"], "JSL8_rearm": validations[key]["JSL8_rearm"], "active_phase_area": validations[key]["active_phase_area"], "raw_path": provenance["runs"][key]["raw"]["path"], "raw_sha256": provenance["runs"][key]["raw"]["sha256"]} for key in run_order}
    result["timing_window"] = {"table": table, "candidate_label": "LS3_DELAY0P5_MECHANICAL_GATE_PASS" if gate.get("status") == "PASS" else "LS3_DELAY0P5_N2_OR_N3_GATE_FAIL", "classification": "NOT_ASSIGNED_SCIENTIFIC_REVIEW_REQUIRED"}
    write_json(EXP / "result.json", result)
    write_result_markdown(result)
    write_json(EXP / "analysis" / "SOURCE_MANIFEST.json", {"schema": "bvm-rloop-ls3-delay-upper-bound-source-manifest-v1", "source_closure": provenance["source_closure"], "canonical_hashes": provenance["canonical_raw_hashes"], "previous_reference_hashes": provenance["previous_reference_hashes"]})
    write_json(EXP / "analysis" / "TRANSFORMATION_REGISTRY.json", {"schema": "bvm-rloop-ls3-delay-upper-bound-transformation-registry-v1", "raw_mutation": False, "operations": [{"name": "delay0p5", "stored_shift": 5, "hold_at_110": True}, {"name": "delay0p6", "stored_shift": 6, "hold_at_110": True}, {"name": "phase_display", "rule": "raw radians to independent unwrap/(2*pi) navigation only"}, {"name": "integration", "rule": "actual stored time trapezoid"}]})


def write_result_markdown(result: dict[str, Any]) -> None:
    table = result["timing_window"]["table"]
    lines = [f"# LS3 ideal timing upper bound ({EXP.name})", "", f"- Status: {result['status']}", "- Artifact status: VALID", "- Scientific interpretation: NOT_PERFORMED; final classification: SCIENTIFIC_REVIEW_REQUIRED.", f"- Parent: {EXPECTED_HEAD}; fixed 0.5-ps pair, with 0.6 ps only after the registered mechanical gate.", "", "| delay | N2 count | N3 count | N2 second response | N3 fourth chain |", "|---:|---:|---:|---|---|"]
    for delay, row in table.items():
        lines.append(f"| {delay} ps | {row['N2'] if row['N2'] is not None else '—'} | {row['N3'] if row['N3'] is not None else '—'} | {'preserved' if row['N2'] is not None and row['N2'] >= 2 else '—'} | {'present' if row['N3'] is not None and row['N3'] >= 4 else 'absent' if row['N3'] is not None else 'pending'} |")
    lines.extend(["", f"- Mechanical candidate gate: {result['timing_window']['candidate_label']}.", "- No continuous boundary is inferred between discrete delays.", "", "| run | first BJ1/BJ2 (ps) | second BJ1/BJ2 (ps) | chains | JTL6 clusters | terminal area / Phi0 | max timing drift (ps) |", "|---|---|---|---:|---:|---:|---:|"])
    for key, item in result["cases"].items():
        lines.append(f"| {key} | {fmt(item['BJ1_landmarks_ps'][0])}/{fmt(item['BJ2_landmarks_ps'][0])} | {fmt(item['BJ1_landmarks_ps'][1])}/{fmt(item['BJ2_landmarks_ps'][1])} | {item['ordered_phase_chain_count']} | {item['jtl6_cluster_count']} | {fmt(item['terminal_total_area_over_phi0'])} | {fmt(item['timing_drift_max_ps'])} |")
    lines.extend(["", "N2/N3 chains, first missing stage, active JS1/JS2 phase-area checks, L1 re-arm, JSL8, bridge current/voltage and ideal-source power/energy are in analysis/mechanical_analysis.json. Phase turns are navigation diagnostics, not literal SFQ counts.", "", f"Stop marker: {FINAL}.", ""])
    (EXP / "RESULT.md").write_text("\n".join(lines), encoding="utf-8")
    (EXP / "analysis" / "NUMERICAL_REVIEW.md").write_text("\n".join(["# Numerical review — mechanical only", "", "- 0.5/0.6 ps use exact stored shifts of 5/6 samples and a 110-ps hold.", "- Integrations and comparisons use actual stored timestamps; no interpolation/resampling.", "- P(...) is raw radians; turns are independent unwrap/(2*pi) navigation only.", "- No timestep/solver sensitivity or physical delay-equivalence claim was tested."]) + "\n", encoding="utf-8")
    (EXP / "analysis" / "ADVERSARIAL_REVIEW.md").write_text("\n".join(["# Adversarial review probes — mechanical only", "", "- Canonical and prior timing-window hashes are checked; prior raw is not copied.", "- Conditional 0.6 ps is materialized only after the fixed 0.5-ps mechanical gate.", "- Per-instance LS3 replay preserves node6-to-node10 sign; no common waveform is used.", "- No scientific winner, mechanism, physical delay or SFQ-count claim is assigned."]) + "\n", encoding="utf-8")


def materialize_conditional() -> None:
    provenance = read_json(EXP / "provenance.json")
    if provenance.get("conditional_0p6", {}).get("status") not in {"AUTHORIZED", "PASS"}:
        raise RuntimeError("0.6 ps not authorized")
    records = {key: make_deck(key) for key in CONDITIONAL}
    provenance["registered_decks"].update(records)
    provenance["conditional_materialization"] = {"status": "PASS", "cases": list(records), "materialized_at": now()}
    write_json(EXP / "provenance.json", provenance)
    path = EXP / "experiment.yaml"
    text = path.read_text(encoding="utf-8").rstrip()
    block = ["", "conditional_0p6_deck_registration:"]
    for key, item in records.items():
        block.extend([f"  - run_id: {key}", f"    path: {item['path']}", f"    sha256: {item['sha256']}", f"    source_csv: {item['source']['path']}", f"    source_csv_sha256: {item['source']['sha256']}"])
    path.write_text(text + "\n" + "\n".join(block) + "\n", encoding="utf-8")


def mechanical_qa() -> None:
    provenance = read_json(EXP / "provenance.json")
    failures = []
    for key in provenance["run_order"]:
        record = provenance["runs"][key]
        paths = [REPO / record[name]["path"] for name in ("deck", "raw", "log", "stdout", "stderr", "metadata")]
        deck, raw, log, stdout, stderr, metadata = paths
        trace = load_raw(raw)
        text = deck.read_text(encoding="utf-8")
        grid = branch.replay_base.finite_grid_qa(trace)
        warnings = warning_lines(log)
        topology = text.count("I_LS3_REPLAY 6 10 PWL(") == 4 and text.count("R_S     6       10      3.0") == 4 and "XBQ1 QBIN QBOUT BQ" in text and "R_TERM JTL6_OUT 0 10" in text and ".tran 0.1p 200p" in text
        ok = record["execution_status"] == "RUN_PASS" and all(path.is_file() for path in paths) and topology and grid["status"] == "VALID" and grid["sample_count"] == 1999 and not record["raw"]["missing_required_probes"] and not trace.duplicate_columns and not [line for line in warnings if line not in KNOWN_WARNINGS] and sha256(raw) == record["raw"]["sha256"]
        if not ok:
            failures.append(key)
    source_ok = all(sha256(REPO / item["path"]) == item["sha256"] for item in provenance["source_closure"])
    count = len(provenance["run_order"])
    ok = not failures and count in (2, 4) and provenance["execution"]["actual_physical_solve_count"] == count and source_ok and provenance.get("raw_hash_before_analysis") == provenance.get("raw_hash_after_analysis") and provenance.get("reference_hashes_before_analysis") == provenance.get("reference_hashes_after_analysis")
    qa = {"schema": "bvm-rloop-ls3-delay-upper-bound-mechanical-qa-v1", "status": "PASS" if ok else "FAIL", "artifact_status": "VALID" if ok else "ARTIFACT_INVALID", "run_order": provenance["run_order"], "actual_physical_solve_count": count, "max_physical_solves": 4, "source_hashes_match": source_ok, "raw_hash_before_after_equal": provenance.get("raw_hash_before_analysis") == provenance.get("raw_hash_after_analysis"), "reference_hash_before_after_equal": provenance.get("reference_hashes_before_analysis") == provenance.get("reference_hashes_after_analysis"), "contains_all_new_run_raw": None, "contains_reference_raw_copies": False, "contains_delivery_manifest": False, "failures": failures, "mechanical_analysis_performed": True, "scientific_interpretation_performed": False}
    write_json(EXP / "analysis" / "MECHANICAL_QA.json", qa)
    provenance["qa"] = qa
    write_json(EXP / "provenance.json", provenance)
    result = read_json(EXP / "result.json")
    result["qa_summary"] = {"status": qa["status"], "artifact_status": qa["artifact_status"]}
    write_json(EXP / "result.json", result)
    if not ok:
        raise RuntimeError(f"mechanical QA failed: {failures}")


def fmt(value: Any) -> str:
    if value is None:
        return "—"
    try:
        return f"{float(value):.8g}"
    except (TypeError, ValueError):
        return str(value)


def visualization() -> None:
    provenance = read_json(EXP / "provenance.json")
    asset = EXP / "plots" / "assets" / "plotly.min.js"
    entries = []
    specs = {"01_SIGNAL_TIMING": ["V(COMMON_SL)", "I(B_JSL8)", "V(QBIN)", "I(LIN|XBQ1)", "V(QBOUT)"], "02_BVM_STATE": [signal for i in range(1,5) for element in ("B_JS1","B_JS2","B_JM1","B_JM2") for signal in (f"P({element}|XBVM{i})",f"V({element}|XBVM{i})",f"I({element}|XBVM{i})")], "03_JSL_CHAIN": [signal for i in range(1,9) for signal in (f"P(B_JSL{i})",f"V(B_JSL{i})",f"I(B_JSL{i})")], "04_QB_STATE": ["V(QBIN)","I(LIN|XBQ1)","P(BJ1|XBQ1)","V(BJ1|XBQ1)","P(BJ2|XBQ1)","V(BJ2|XBQ1)","I(L1|XBQ1)","I(L2|XBQ1)","V(QBOUT)"], "05_JTL_CHAIN": [signal for i in JTL_STAGES for signal in (f"P(B01|XJTL1_{i})",f"V(B01|XJTL1_{i})",f"V(JTL{i}_OUT)")] + ["I(R_TERM)"]}
    for key in provenance["run_order"]:
        raw = REPO / provenance["runs"][key]["raw"]["path"]
        trace = load_raw(raw)
        for page, requested in specs.items():
            selected = [signal for signal in requested if signal in trace.headers]
            full = EXP / "plots" / key / f"{page}_full_0_200.html"
            branch.render_plot(raw, full, selected, f"{key}: {page}; full 0-200 ps; actual stored grid", asset)
            entries.append({"kind": "standalone", "run_id": key, "path": rel(full), "raw_path": rel(raw), "raw_sha256": sha256(raw), "sha256": sha256(full), "signals": selected, "window_ps": list(FULL), "focused": False})
            crop = branch.total_helpers.crop_csv(raw, *FOCUS)
            try:
                focused = EXP / "plots" / key / f"{page}_focus_110_121.html"
                branch.render_plot(crop, focused, selected, f"{key}: {page}; focus [110,121) ps; actual stored samples", asset)
                entries.append({"kind": "standalone", "run_id": key, "path": rel(focused), "raw_path": rel(raw), "raw_sha256": sha256(raw), "sha256": sha256(focused), "signals": selected, "window_ps": list(FOCUS), "focused": True})
            finally:
                crop.unlink(missing_ok=True)
    for mask in MASKS:
        cases = [(f"CANONICAL_{mask}", load_raw(CANONICAL[mask]))]
        for key, path in reference_paths().items():
            if key.endswith("_" + mask):
                cases.append(("REF_" + key, load_raw(path)))
        for key in provenance["run_order"]:
            if case_info(key)["mask"] == mask:
                cases.append((key, load_raw(REPO / provenance["runs"][key]["raw"]["path"])))
        for page, requested in (("01_SIGNAL_TIMING", specs["01_SIGNAL_TIMING"]), ("03_JSL_CHAIN", specs["03_JSL_CHAIN"]), ("04_QB_STATE", specs["04_QB_STATE"]), ("05_JTL_CHAIN", specs["05_JTL_CHAIN"])):
            selected = [signal for signal in requested if all(signal in trace.headers for _, trace in cases)]
            if not selected:
                continue
            temporary = branch.total_helpers.comparison_csv(cases, selected, FOCUS)
            output = EXP / "plots" / "comparisons" / f"{mask}_{page}_focus_110_121.html"
            try:
                labels = [branch.replay_base.prefixed_label(case, signal) for case, _ in cases for signal in selected]
                branch.render_plot(temporary, output, labels, f"{mask}: LS3 upper-bound comparison {page}; focus [110,121) ps", asset)
            finally:
                temporary.unlink(missing_ok=True)
            entries.append({"kind": "comparison", "mask": mask, "path": rel(output), "sha256": sha256(output), "signals": selected, "cases": [case for case, _ in cases], "window_ps": list(FOCUS), "focused": True})
    html = sorted((EXP / "plots").rglob("*.html"))
    invalid = [rel(path) for path in html if any(token in path.read_text(encoding="utf-8") for token in ("plotly.js v", "var Plotly=", "cdn.plot.ly", "Unknown"))]
    record = {"schema": "bvm-rloop-ls3-delay-upper-bound-visualization-v1", "status": "PASS" if entries and asset.is_file() and not invalid else "FAIL", "renderer": rel(REPO / "scripts" / "josim-plot2.py"), "layout": "sep_comb", "color": "dark", "phase_option": "2pi", "entries": entries, "standalone_count": sum(item["kind"] == "standalone" for item in entries), "comparison_count": sum(item["kind"] == "comparison" for item in entries), "focused_window_entries": sum(item.get("focused", False) for item in entries), "asset": {"path": rel(asset), "sha256": sha256(asset) if asset.is_file() else None}, "invalid_runtime_pages": invalid, "raw_hashes_rechecked": all(item["raw_sha256"] == sha256(REPO / item["raw_path"]) for item in entries if item["kind"] == "standalone"), "descriptive_only": True}
    write_json(EXP / "analysis" / "VISUALIZATION_MANIFEST.json", record)
    write_json(EXP / "analysis" / "VISUALIZATION_QA.json", {key: record[key] for key in ("status", "standalone_count", "comparison_count", "focused_window_entries", "invalid_runtime_pages", "raw_hashes_rechecked")})
    provenance["visualization"] = record
    write_json(EXP / "provenance.json", provenance)
    result = read_json(EXP / "result.json")
    result["visualization_summary"] = {key: record[key] for key in ("status", "standalone_count", "comparison_count", "focused_window_entries")}
    write_json(EXP / "result.json", result)
    if record["status"] != "PASS":
        raise RuntimeError(f"visualization failed: {invalid}")


def write_evidence_manifest() -> None:
    records = [{"path": path.relative_to(EXP).as_posix(), "sha256": sha256(path), "bytes": path.stat().st_size} for path in sorted(EXP.rglob("*")) if path.is_file() and path.name != "delivery_manifest.json" and path.suffix != ".tmp"]
    write_json(EXP / "analysis" / "RAW_ANALYSIS_HANDOFF_MANIFEST.json", {"schema": "bvm-rloop-ls3-delay-upper-bound-raw-analysis-handoff-v1", "experiment_id": EXP.name, "raw_is_immutable_solver_output": True, "files_excluding_delivery_manifest": records})
    (EXP / "analysis" / "EVIDENCE_MANIFEST.md").write_text("\n".join(["# Evidence manifest", "", "| path | SHA-256 | bytes |", "|---|---|---:|"] + [f"| {item['path']} | {item['sha256']} | {item['bytes']} |" for item in records]) + "\n", encoding="utf-8")


def package() -> None:
    provenance = read_json(EXP / "provenance.json")
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
    files = [(EXP / name, name) for name in ("PREFLIGHT.md", "README.md", "experiment.yaml", "RESULT.md", "result.json", "provenance.json")]
    for dirname in ("inputs", "runs", "analysis", "plots"):
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
    qa = {"status": "PASS" if expected == reopened and all(member in reopened for member in raw_members) else "FAIL", "package_version": version, "package_path": str(package_path), "package_sha256": sha256(package_path), "package_bytes": package_path.stat().st_size, "file_count": len(records), "expected_file_hashes_match_after_reopen": expected == reopened, "zip_files": records, "contains_all_new_run_raw": all(member in reopened for member in raw_members), "new_run_raw_members": raw_members, "contains_reference_raw_copies": False, "contains_delivery_manifest": False, "delivery_manifest_outside_zip": True, "not_in_git": True, "git_head_at_packaging": git_head(), "remote_head_at_packaging": remote_head()}
    manifest = {"schema": "bvm-rloop-ls3-delay-upper-bound-delivery-manifest-v1", "experiment_id": EXP.name, "status": "READY_FOR_DRIVE_UPLOAD" if qa["status"] == "PASS" else "PACKAGE_INVALID", "package_version": version, "package_path": str(package_path), "package_sha256": qa["package_sha256"], "package_bytes": qa["package_bytes"], "package_qa": qa, "drive_folder_id": DRIVE_FOLDER_ID, "drive_file_id": None, "drive_url": None}
    write_json(EXP / "delivery_manifest.json", manifest)
    write_json(EXP / "analysis" / "PACKAGE_QA.json", qa)
    provenance["package"] = {"status": manifest["status"], "package_qa": qa, "delivery_manifest_path": "delivery_manifest.json", "drive_file_id": None, "drive_url": None}
    write_json(EXP / "provenance.json", provenance)
    result = read_json(EXP / "result.json")
    result["package_summary"] = {"status": manifest["status"], "package_version": version, "package_sha256": qa["package_sha256"], "package_bytes": qa["package_bytes"], "file_count": qa["file_count"], "delivery_manifest_path": "delivery_manifest.json", "drive_file_id": None}
    write_json(EXP / "result.json", result)
    if qa["status"] != "PASS":
        raise RuntimeError("package QA failed")
    print(json.dumps({"status": "PASS", "package_path": str(package_path), "sha256": qa["package_sha256"], "bytes": qa["package_bytes"], "files": qa["file_count"]}, ensure_ascii=False, indent=2))


def record_drive(file_id: str, url: str, size: int) -> None:
    manifest_path = EXP / "delivery_manifest.json"
    manifest = read_json(manifest_path)
    path = Path(manifest["package_path"])
    if sha256(path) != manifest["package_sha256"] or int(size) != manifest["package_bytes"]:
        raise RuntimeError("package verification failed")
    manifest.update({"status": "UPLOADED", "drive_file_id": file_id, "drive_url": url, "uploaded_at": now(), "drive_verified_local_sha256": manifest["package_sha256"], "drive_verified_local_bytes": manifest["package_bytes"], "remote_sha256_from_connector": None})
    write_json(manifest_path, manifest)
    provenance = read_json(EXP / "provenance.json")
    provenance["package"].update({"status": "UPLOADED", "drive_file_id": file_id, "drive_url": url, "drive_uploaded_at": manifest["uploaded_at"], "delivery_manifest_sha256": sha256(manifest_path), "drive_sha256_verified": "metadata SHA not supplied by connector"})
    write_json(EXP / "provenance.json", provenance)
    result = read_json(EXP / "result.json")
    result["package_summary"].update({"status": "UPLOADED", "drive_file_id": file_id, "drive_url": url})
    write_json(EXP / "result.json", result)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--josim-bin", default=str(REPO / "build" / "josim-cli"))
    parser.add_argument("--dt", default="0.1p")
    parser.add_argument("--stop-time", default="200p")
    parser.add_argument("--masks", nargs="+", default=list(MASKS))
    parser.add_argument("--delays", nargs="+", default=["0.5"])
    parser.add_argument("--only")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-analysis", action="store_true")
    parser.add_argument("--no-plots", action="store_true")
    parser.add_argument("command", nargs="?", default="all", choices=("all", "continue-conditional", "record-drive"))
    parser.add_argument("drive_id", nargs="?")
    parser.add_argument("drive_url", nargs="?")
    parser.add_argument("drive_size", nargs="?", type=int)
    args = parser.parse_args()
    if args.command == "record-drive":
        record_drive(args.drive_id, args.drive_url, args.drive_size)
        return 0
    if args.command == "continue-conditional":
        provenance = read_json(EXP / "provenance.json")
        if provenance.get("conditional_0p6", {}).get("status") not in {"AUTHORIZED", "PASS"}:
            raise RuntimeError("0.6 ps is not mechanically authorized")
        if provenance["run_order"] != list(FIXED):
            raise RuntimeError(f"conditional continuation requires completed fixed pair: {provenance['run_order']}")
        materialize_conditional()
        for key in CONDITIONAL:
            execute_case(key, args)
        analyze(args)
        mechanical_qa()
        visualization()
        package()
        return 0
    if args.dry_run:
        dry_run(args)
        return 0
    prepare(args)
    selected = [mask for mask in args.masks if args.only is None or mask == args.only]
    for key in [f"LS3_DELAY0P5_{mask}" for mask in selected]:
        execute_case(key, args)
    analyze(args)
    provenance = read_json(EXP / "provenance.json")
    if len(selected) == 2 and provenance.get("conditional_0p6", {}).get("status") == "AUTHORIZED":
        materialize_conditional()
        for key in CONDITIONAL:
            execute_case(key, args)
        analyze(args)
    mechanical_qa()
    if args.no_plots:
        raise RuntimeError("visualization is required for this experiment")
    visualization()
    package()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
