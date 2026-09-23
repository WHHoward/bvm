#!/usr/bin/env python3
"""Execute only the frozen four-case physical matrix, with immutable run folders."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from common import (MATRIX, REPO, ROOT, SOLVER, SOURCE_PATHS,
                    SOURCE_SNAPSHOT_NAMES, cases, current_head, git_status,
                    read_json, render_deck, repo_rel, sha256, solver_identity,
                    source_records, stimulus_text, write_json)

PREFLIGHT_QA = ROOT / "analysis" / "PREFLIGHT_QA.json"
PREFLIGHT_MD = ROOT / "PREFLIGHT.md"
EXECUTION = ROOT / "analysis" / "EXECUTION.json"
ANALYZER = Path(__file__).with_name("analyze_run.py")
INDEPENDENT_VERIFIER = Path(__file__).with_name("independent_verify.py")


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def verify_live_source_lock(source_lock: dict[str, Any]) -> None:
    for role, frozen in source_lock.get("source_hashes", {}).items():
        path = REPO / frozen.get("path", "")
        if not path.is_file() or sha256(path) != frozen.get("sha256"):
            raise RuntimeError(f"frozen source/input changed after preflight: {role}")


def run_one(item: dict[str, Any], preflight: dict[str, Any], source_lock: dict[str, Any], execution: dict[str, Any]) -> dict[str, Any]:
    run_id = item["run_id"]
    directory = ROOT / "runs" / run_id
    if directory.exists():
        raise RuntimeError(f"append-only run directory already exists; refusing overwrite: {directory}")
    if current_head() != preflight.get("head"):
        raise RuntimeError("HEAD changed after machine preflight; no solve started for this run")
    verify_live_source_lock(source_lock)
    (directory / "snapshot" / "sources").mkdir(parents=True)
    run_source_records = []
    for source in source_records():
        original = REPO / source["path"]
        snapshot = directory / "snapshot" / "sources" / source["snapshot_name"]
        shutil.copyfile(original, snapshot)
        actual_hash = sha256(snapshot)
        if actual_hash != source["sha256"]:
            raise RuntimeError(f"source changed while snapshotting: {source['role']}")
        run_source_records.append({**source, "snapshot_path": repo_rel(snapshot),
                                   "snapshot_sha256": actual_hash,
                                   "bytes": snapshot.stat().st_size})

    stimulus = directory / "stimulus.inc"
    stimulus.write_text(stimulus_text(item["mask"]), encoding="utf-8")
    deck_text = render_deck("stimulus.inc")
    actual_deck = directory / "actual_deck.cir"
    actual_deck.write_text(deck_text, encoding="utf-8")
    shutil.copyfile(actual_deck, directory / "deck.cir")
    if actual_deck.read_bytes() != (directory / "deck.cir").read_bytes():
        raise RuntimeError("deck.cir and actual_deck.cir differ")

    metadata = {
        "schema": "bvm-bq-cb-gap-run-metadata-v2", "run_id": run_id,
        "experiment_id": read_json(MATRIX)["experiment_id"],
        "parameters": {"MASK": item["mask"], "population": item["population"],
                       "active_bvms": item["active_bvms"], "DT": preflight["cases"][0]["dt"],
                       "STOP": preflight["cases"][0]["stop"], "save_start": "0p",
                       "R_TERM_OHM": 2},
        "purpose": item["purpose"], "git": {"head": current_head(),
                    "status_porcelain_at_solve_start": git_status()},
        "solver": solver_identity(), "stimulus": {"path": "stimulus.inc",
                    "sha256": sha256(stimulus)},
        "deck": {"path": "actual_deck.cir", "sha256": sha256(actual_deck)},
        "source_manifest": "source_manifest.json", "created_at": now(),
        "metric_spec": read_json(MATRIX)["metric_spec"],
        "raw": {"path": "raw.csv", "sha256": None},
        "scientific_interpretation_performed": False,
    }
    write_json(directory / "metadata.json", metadata)
    source_manifest = {
        "schema": "bvm-bq-cb-gap-source-manifest-v2", "run_id": run_id,
        "registered_source_lock_sha256": preflight.get("source_lock_sha256"),
        "sources": run_source_records,
        "referenced_frozen_inputs": {
            role: source_lock["source_hashes"][role]
            for role in ("MODEL_REFERENCE", "METRIC_SPEC", "METRIC_SPEC_COPY", "V1_INCIDENT_COPY")
        },
        "rendered_deck": {"path": "actual_deck.cir", "sha256": sha256(actual_deck)},
        "stimulus": {"path": "stimulus.inc", "sha256": sha256(stimulus)},
        "jjmit_model": {"reference_path": "bvm_0923/test_bvm.cir",
                        "reference_sha256": read_json(ROOT / "analysis" / "SOURCE_LOCK.json")["source_hashes"]["MODEL_REFERENCE"]["sha256"],
                        "actual_deck_line": next(line.strip() for line in deck_text.splitlines()
                                                  if line.strip().lower().startswith(".model jjmit")),
                        "source_lock_role": "MODEL_REFERENCE"},
        "scientific_interpretation_performed": False,
    }
    write_json(directory / "source_manifest.json", source_manifest)

    raw = directory / "raw.csv"
    command = [str(SOLVER), "--output", str(raw), str(directory / "actual_deck.cir")]
    started = now()
    record: dict[str, Any] = {"run_id": run_id, "command": command,
                              "cwd": repo_rel(directory), "started_at": started,
                              "head": current_head(), "solver": solver_identity(),
                              "deck_sha256": sha256(actual_deck),
                              "stimulus_sha256": sha256(stimulus),
                              "solve_started": True, "status": "RUNNING"}
    execution["physical_solve_count_started"] += 1
    execution["runs"].append(record)
    write_json(EXECUTION, execution)
    completed = subprocess.run(command, cwd=directory, capture_output=True, text=True, check=False)
    (directory / "stdout.txt").write_text(completed.stdout, encoding="utf-8")
    (directory / "stderr.txt").write_text(completed.stderr, encoding="utf-8")
    (directory / "run.log").write_text("=== STDOUT ===\n" + completed.stdout +
                                       "\n=== STDERR ===\n" + completed.stderr, encoding="utf-8")
    record.update({"completed_at": now(), "returncode": completed.returncode,
                   "stdout_sha256": sha256(directory / "stdout.txt"),
                   "stderr_sha256": sha256(directory / "stderr.txt"),
                   "run_log_sha256": sha256(directory / "run.log"),
                   "raw_exists": raw.is_file(), "status": "SOLVER_PASS" if completed.returncode == 0 and raw.is_file() else "SOLVER_FAIL"})
    if raw.is_file():
        record["raw"] = {"sha256": sha256(raw), "bytes": raw.stat().st_size}
        metadata["raw"] = {"path": "raw.csv", "sha256": record["raw"]["sha256"],
                           "bytes": record["raw"]["bytes"]}
        write_json(directory / "metadata.json", metadata)
    write_json(directory / "solve_receipt.json", record)
    write_json(EXECUTION, execution)
    if completed.returncode != 0 or not raw.is_file() or raw.stat().st_size == 0:
        record["status"] = "TOOL_OR_ARTIFACT_FAILURE_STOP"
        write_json(directory / "solve_receipt.json", record)
        raise RuntimeError(f"JoSIM failed for {run_id}; preserving deck/raw/logs and stopping without retry")

    analyzed = subprocess.run([sys.executable, str(ANALYZER), run_id], cwd=REPO,
                              capture_output=True, text=True, check=False)
    record["mechanical_qa_returncode"] = analyzed.returncode
    record["mechanical_qa_stdout"] = analyzed.stdout
    record["mechanical_qa_stderr"] = analyzed.stderr
    record["status"] = "RAW_QA_PASS" if analyzed.returncode == 0 else "RAW_QA_FAIL_STOP"
    write_json(directory / "solve_receipt.json", record)
    execution["runs"][-1] = record
    write_json(EXECUTION, execution)
    if analyzed.returncode != 0:
        raise RuntimeError(f"raw/mechanical QA failed for {run_id}; no additional solve will be started")
    independent = subprocess.run([sys.executable, str(INDEPENDENT_VERIFIER), run_id], cwd=REPO,
                                  capture_output=True, text=True, check=False)
    record["independent_qa_returncode"] = independent.returncode
    record["independent_qa_stdout"] = independent.stdout
    record["independent_qa_stderr"] = independent.stderr
    record["status"] = "INDEPENDENT_RAW_QA_PASS" if independent.returncode == 0 else "INDEPENDENT_RAW_QA_FAIL_STOP"
    write_json(directory / "solve_receipt.json", record)
    execution["runs"][-1] = record
    write_json(EXECUTION, execution)
    if independent.returncode != 0:
        raise RuntimeError(f"independent raw arithmetic QA failed for {run_id}; no additional solve will be started")
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description="Run exactly N0_00, N1_01, N1_10, N2_11")
    parser.add_argument("--plan", action="store_true", help="print the exact plan without solving")
    args = parser.parse_args()
    experiment_text = (ROOT / "experiment.yaml").read_text(encoding="utf-8")
    if "execution_status: ABORTED_PENDING_USER_DIRECTION" in experiment_text:
        raise RuntimeError("this experiment directory is incident-aborted and cannot launch physical solves")
    matrix = read_json(MATRIX)
    if [item["run_id"] for item in cases()] != ["N0_00", "N1_01", "N1_10", "N2_11"]:
        raise RuntimeError("registered run matrix identity/order changed")
    plan = {"authorized_cases": cases(), "authorized_solve_count": 4,
            "dt": matrix["dt"], "stop": matrix["stop"], "physical_solve_executed": False}
    if args.plan:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return 0
    if not PREFLIGHT_QA.is_file():
        raise RuntimeError("analysis/PREFLIGHT_QA.json missing; run preflight --write")
    preflight = read_json(PREFLIGHT_QA)
    if preflight.get("status") != "PASS" or not preflight.get("no_solve_executed"):
        raise RuntimeError("machine preflight is not a no-solve PASS")
    if preflight.get("head") != current_head():
        raise RuntimeError("HEAD differs from the preflight execution HEAD")
    if preflight.get("source_lock_sha256") != sha256(ROOT / "analysis" / "SOURCE_LOCK.json"):
        raise RuntimeError("source lock changed after preflight")
    if sha256(MATRIX) != preflight.get("matrix_sha256"):
        raise RuntimeError("matrix changed after preflight")
    if EXECUTION.exists():
        raise RuntimeError("execution record already exists; refusing to rerun or overwrite")
    if (ROOT / "runs").exists() and any((ROOT / "runs").iterdir()):
        raise RuntimeError("run directory is not empty; refusing append-only collision")
    execution = {"schema": "bvm-bq-cb-gap-execution-v2", "experiment_id": matrix["experiment_id"],
                 "preflight_sha256": sha256(PREFLIGHT_QA), "preflight_md_sha256": sha256(PREFLIGHT_MD),
                 "head": current_head(), "authorized_solve_count": 4,
                 "physical_solve_count_started": 0, "status": "RUNNING",
                 "scientific_interpretation_performed": False, "runs": []}
    write_json(EXECUTION, execution)
    for item in cases():
        print(f"RUN {item['run_id']} mask={item['mask']} active={item['active_bvms']}", flush=True)
        source_lock = read_json(ROOT / "analysis" / "SOURCE_LOCK.json")
        run_one(item, preflight, source_lock, execution)
    execution["status"] = "ALL_FOUR_SOLVES_RAW_AND_INDEPENDENT_QA_PASS"
    execution["completed_at"] = now()
    write_json(EXECUTION, execution)
    print(json.dumps({"status": execution["status"],
                      "physical_solve_count": execution["physical_solve_count_started"],
                      "runs": [item["run_id"] for item in execution["runs"]],
                      "scientific_interpretation_performed": False}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
