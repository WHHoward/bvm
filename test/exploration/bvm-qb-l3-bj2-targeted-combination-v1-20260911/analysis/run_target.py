#!/usr/bin/env python3
"""Execute the registered BJ2/L3 screening pair and conditional validation."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
SOLVER = REPO / "build/josim-cli"
SOLVER_SHA256 = "48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2"
MATRIX = EXP / "screening/TARGET_MATRIX.json"
PREFLIGHT = EXP / "analysis/preflight.json"
STATE = EXP / "screening/target_state.json"
RESULT_PATH = EXP / "screening/results/TARGET_L3_2_BJ2_2p2_v2.json"
VALIDATION_PATH = EXP / "screening/validation_summary.json"
TABLE_JSON = EXP / "screening/TARGET_RESULTS.json"
TABLE_MD = EXP / "screening/TARGET_RESULTS.md"
SUMMARY = EXP / "qa/execution_summary.json"
POINT_ID = "TARGET_L3_2_BJ2_2p2"
SCREENING_MASKS = ("0011", "0111")
VALIDATION_MASKS = ("0001", "1111")
ALL_MASKS = ("0001", "0011", "0111", "1111")
OUTCOME_LABELS = {
    "S": "DIRECT_2_TO_3_L3_BJ2_CANDIDATE",
    "A": "N2_RESCUED_BUT_N3_FOURTH_REMAINS",
    "B": "N3_SUPPRESSED_BUT_N2_NOT_RESCUED",
    "C": "L3_BJ2_COMBINATION_UNFAVORABLE",
    "D": "N3_FOURTH_HANDOFF_BOUNDARY_CASE",
}


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


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


def head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()


def head_relation(sealed: str) -> dict[str, Any]:
    current = head()
    if current == sealed:
        return {"status": "PASS", "head": current, "relation": "EXACT", "changed_paths": [], "commit_distance": 0}
    changed = set(subprocess.check_output(["git", "diff", "--name-only", f"{sealed}..{current}"], cwd=REPO, text=True).splitlines())
    prefix = EXP.relative_to(REPO).as_posix()
    allowed = {
        f"{prefix}/PREFLIGHT.md",
        f"{prefix}/SOURCE_MANIFEST.json",
        f"{prefix}/analysis/preflight.json",
        f"{prefix}/screening/TARGET_MATRIX.json",
        f"{prefix}/screening/TARGET_TABLE.md",
    }
    distance = int(subprocess.check_output(["git", "rev-list", "--count", f"{sealed}..{current}"], cwd=REPO, text=True).strip())
    valid = distance == 1 and changed.issubset(allowed)
    return {"status": "PASS" if valid else "FAIL", "head": current, "relation": "PREFLIGHT_SEAL_COMMIT" if valid else "UNEXPECTED", "changed_paths": sorted(changed), "commit_distance": distance}


def load_gate() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    preflight = json.loads(PREFLIGHT.read_text(encoding="utf-8"))
    matrix = json.loads(MATRIX.read_text(encoding="utf-8"))
    if preflight.get("status") != "PASS" or matrix.get("logical_new_point_count") != 1 or matrix.get("logical_new_case_count") != 2:
        raise RuntimeError("target preflight/matrix is not PASS")
    if preflight.get("physical_solve_count_before_preflight") != 0:
        raise RuntimeError("target preflight records prior physical solves")
    if sha256(MATRIX) != preflight.get("matrix_sha256") or sha256(EXP / "SOURCE_MANIFEST.json") != preflight.get("source_manifest_sha256"):
        raise RuntimeError("target matrix/source hash mismatch")
    relation = head_relation(str(preflight["head_at_preflight"]))
    if relation["status"] != "PASS":
        raise RuntimeError(f"HEAD/preflight relation is not allowed: {relation}")
    if not SOLVER.is_file() or sha256(SOLVER) != SOLVER_SHA256:
        raise RuntimeError("canonical solver identity changed")
    return preflight, matrix, relation


def raw_summary(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.reader(stream)
        try:
            header = next(reader)
            first = next(reader)
        except StopIteration:
            return None
        last = first
        count = 1
        for row in reader:
            last = row
            count += 1
    return {"header_count": len(header), "sample_count": count, "first_timestamp": first[0], "last_timestamp": last[0]}


def state_template(preflight: dict[str, Any], relation: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "bvm-qb-l3-bj2-targeted-combination-state-v1",
        "experiment_id": EXP.name,
        "created_at_local": now(),
        "updated_at_local": now(),
        "status": "RUNNING",
        "final_marker": None,
        "preflight_head": preflight["head_at_preflight"],
        "execution_head": relation["head"],
        "point_id": POINT_ID,
        "screening_solve_count": 2,
        "maximum_total_solve_count": 4,
        "screening_cases": {},
        "validation_cases": {},
        "run_order": [],
        "candidate_class": None,
        "outcome": None,
        "validation": None,
    }


def save_state(state: dict[str, Any]) -> None:
    state["updated_at_local"] = now()
    write_json(STATE, state)


def run_case(point: dict[str, Any], mask: str, *, run_kind: str) -> dict[str, Any]:
    run_id = f"{POINT_ID}_{mask}"
    run_dir = EXP / "runs" / run_id
    deck_source = REPO / point["cases"][mask]["path"]
    if run_dir.exists():
        required = [run_dir / name for name in ("deck.cir", "raw.csv", "metadata.json", "run.log")]
        if not all(path.is_file() for path in required):
            raise RuntimeError(f"partial run exists; refusing overwrite: {run_dir}")
        metadata = json.loads((run_dir / "metadata.json").read_text(encoding="utf-8"))
        if metadata.get("run_id") != run_id or metadata.get("mask") != mask or metadata.get("run_kind") != run_kind or metadata.get("execution_status") != "RUN_PASS":
            raise RuntimeError(f"existing run identity/status mismatch: {run_dir}")
        return {"run_id": run_id, "mask": mask, "run_kind": run_kind, "source_kind": "EXISTING_COMPLETED_RUN", "physical_solve_this_experiment": True, "raw_path": rel(run_dir / "raw.csv"), "deck_path": rel(run_dir / "deck.cir"), "metadata_path": rel(run_dir / "metadata.json"), "log_path": rel(run_dir / "run.log"), "raw_sha256": sha256(run_dir / "raw.csv"), "deck_sha256": sha256(run_dir / "deck.cir"), "raw_bytes": (run_dir / "raw.csv").stat().st_size, "raw_summary": raw_summary(run_dir / "raw.csv")}
    run_dir.mkdir(parents=True)
    deck = run_dir / "deck.cir"
    raw = run_dir / "raw.csv"
    log = run_dir / "run.log"
    metadata_path = run_dir / "metadata.json"
    shutil.copy2(deck_source, deck)
    command = [str(SOLVER), "-a", "1", "-o", str(raw), str(deck)]
    started = now()
    with log.open("x", encoding="utf-8") as stream:
        completed = subprocess.run(command, cwd=REPO, stdout=stream, stderr=subprocess.STDOUT, check=False)
    finished = now()
    raw_exists = raw.is_file()
    metadata = {
        "schema": "bvm-qb-l3-bj2-targeted-combination-run-metadata-v1",
        "experiment_id": EXP.name,
        "run_id": run_id,
        "run_kind": run_kind,
        "point_id": point["point_id"],
        "changes": point["changes"],
        "mask": mask,
        "topology": "BVM1..4 -> COMMON_SL -> 8-JJ JSL -> QB -> six-stage JTL -> R_TERM",
        "stimulus": {"amplitude_uA": 100.0, "tran": ".tran 0.1p 200p", "history": "IDLE/WRITE0/ZERO_STATE_READ_CONTROL/IDLE/WRITE1/SETTLE/FINAL_READ/TAIL"},
        "started_at_local": started,
        "finished_at_local": finished,
        "git_head_before_run": head(),
        "command": command,
        "solver": {"path": rel(SOLVER), "sha256": sha256(SOLVER), "version": subprocess.check_output([str(SOLVER), "--version"], cwd=REPO, text=True)},
        "deck_source": {"path": rel(deck_source), "sha256": sha256(deck_source)},
        "artifacts": {
            "deck": {"path": rel(deck), "sha256": sha256(deck), "bytes": deck.stat().st_size},
            "raw": {"path": rel(raw), "exists": raw_exists, "sha256": sha256(raw) if raw_exists else None, "bytes": raw.stat().st_size if raw_exists else None},
            "log": {"path": rel(log), "sha256": sha256(log), "bytes": log.stat().st_size},
        },
        "exit_code": completed.returncode,
        "execution_status": "RUN_PASS" if completed.returncode == 0 and raw_exists else "RUN_FAIL",
        "physical_solve_this_experiment": True,
        "raw_immutable": True,
        "parameter_tuning": False,
        "scientific_analysis_performed": False,
        "raw_summary": raw_summary(raw),
    }
    with metadata_path.open("x", encoding="utf-8") as stream:
        json.dump(metadata, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    if metadata["execution_status"] != "RUN_PASS":
        raise RuntimeError(f"solver failed without retry: {run_id}")
    return {"run_id": run_id, "mask": mask, "run_kind": run_kind, "source_kind": "NEW_PHYSICAL_SOLVE", "physical_solve_this_experiment": True, "raw_path": rel(raw), "deck_path": rel(deck), "metadata_path": rel(metadata_path), "log_path": rel(log), "raw_sha256": sha256(raw), "deck_sha256": sha256(deck), "raw_bytes": raw.stat().st_size, "raw_summary": raw_summary(raw)}


def analyse(point: dict[str, Any], cases: dict[str, Any], *, force: bool = False) -> dict[str, Any]:
    if force or not RESULT_PATH.is_file():
        command = [sys.executable, str(EXP / "analysis/target_analysis.py"), "--point-id", point["point_id"], "--changes", json.dumps(point["changes"], separators=(",", ":")), "--n2", str(REPO / cases["0011"]["raw_path"]), "--n3", str(REPO / cases["0111"]["raw_path"])]
        completed = subprocess.run(command, cwd=REPO, check=False)
        if completed.returncode != 0 or not RESULT_PATH.is_file():
            raise RuntimeError(f"target raw analysis failed: {point['point_id']}")
    result = json.loads(RESULT_PATH.read_text(encoding="utf-8"))
    expected = {"0011": cases["0011"]["raw_sha256"], "0111": cases["0111"]["raw_sha256"]}
    actual = {mask: result["n2" if mask == "0011" else "n3"]["raw_sha256"] for mask in SCREENING_MASKS}
    if actual != expected:
        raise RuntimeError(f"target result/raw hash binding failed: {point['point_id']}")
    return result


def validation_summary(state: dict[str, Any]) -> dict[str, Any]:
    from target_analysis import case_evidence, load

    raw_paths = {
        "0001": REPO / state["validation_cases"]["0001"]["raw_path"],
        "0011": REPO / state["screening_cases"]["0011"]["raw_path"],
        "0111": REPO / state["screening_cases"]["0111"]["raw_path"],
        "1111": REPO / state["validation_cases"]["1111"]["raw_path"],
    }
    expected = {"0001": 1, "0011": 2, "0111": 3, "1111": 4}
    cases: dict[str, Any] = {}
    for mask in ALL_MASKS:
        evidence = case_evidence(load(raw_paths[mask]))
        cases[mask] = {
            "raw_path": rel(raw_paths[mask]),
            "raw_sha256": sha256(raw_paths[mask]),
            "expected_response_candidate_count": expected[mask],
            "observed_response_candidate_count": evidence["complete_response_candidate_count"],
            "ordered_chain_by_candidate": evidence["ordered_chain_by_candidate"],
            "control_status": evidence["control"]["status"],
            "control_complete_downstream_chain_count": evidence["control"]["complete_downstream_chain_count"],
            "phase_navigation_only": True,
            "not_sfq_count": True,
        }
    exact = all(item["observed_response_candidate_count"] == item["expected_response_candidate_count"] and item["control_status"] == "CLEAN" for item in cases.values())
    ordered = all(all(item["ordered_chain_by_candidate"].get(str(index), False) for index in range(1, item["expected_response_candidate_count"] + 1)) for item in cases.values())
    record = {"schema": "bvm-qb-l3-bj2-targeted-combination-validation-v1", "experiment_id": EXP.name, "created_at_local": now(), "status": "FULL_POPULATION_1_2_3_4_CANDIDATE" if exact and ordered else "VALIDATION_NOT_FULL_1_2_3_4", "cases": cases, "exact_candidate_counts": exact, "all_ordered_chains": ordered, "chain_closure_candidate": exact and ordered, "raw_authority": True, "scientific_review_performed": False, "not_sfq_count": True}
    write_json(VALIDATION_PATH, record)
    return record


def write_table(state: dict[str, Any], result: dict[str, Any] | None) -> None:
    row = {
        "point_id": POINT_ID,
        "L3_pH": 2.0,
        "BJ2_area": 2.2,
        "screening_status": "COMPLETE" if result else "NOT_RUN",
        "control_n2": result["n2"]["classification"]["control_status"] if result else None,
        "control_n3": result["n3"]["classification"]["control_status"] if result else None,
        "N2_candidate_count": result["n2"]["evidence"]["complete_response_candidate_count"] if result else None,
        "N3_candidate_count": result["n3"]["evidence"]["complete_response_candidate_count"] if result else None,
        "N2_classification": result["n2"]["classification"]["classification"] if result else None,
        "N3_classification": result["n3"]["classification"]["classification"] if result else None,
        "candidate_class": result.get("candidate_class") if result else None,
        "candidate_label": result.get("candidate_label") if result else None,
        "validation_status": state.get("validation", {}).get("status") if state.get("validation") else "NOT_RUN",
        "run_ids": state.get("run_order", []),
    }
    write_json(TABLE_JSON, {"schema": "bvm-qb-l3-bj2-targeted-combination-results-v1", "experiment_id": EXP.name, "updated_at_local": now(), "row": row, "references": {"canonical": "references/canonical_l3p13", "l3_only": "references/l3p20", "bj2_only": "references/bj2p22_l3p13"}, "phase_navigation_only": True, "not_sfq_count": True})
    lines = ["# BJ2/L3 targeted combination results", "", "| point | L3 pH | BJ2 area | control N2 | control N3 | N2 candidates | N3 candidates | N2 class | N3 class | result class | validation |", "|---|---:|---:|---|---|---:|---:|---|---|---|---|"]
    values = [row["point_id"], row["L3_pH"], row["BJ2_area"], row["control_n2"] or "", row["control_n3"] or "", row["N2_candidate_count"] if row["N2_candidate_count"] is not None else "", row["N3_candidate_count"] if row["N3_candidate_count"] is not None else "", row["N2_classification"] or "", row["N3_classification"] or "", row["candidate_label"] or "", row["validation_status"]]
    lines.append("| " + " | ".join(str(value) for value in values) + " |")
    lines.extend(["", "Three reference pairs are immutable raw context: canonical L3=1.3/BJ2=2.0, L3-only L3=2.0/BJ2=2.0, and BJ2-only L3=1.3/BJ2=2.2.", "", "P(...) is raw radians; any turns are phase navigation only and are not SFQ counts.", ""])
    TABLE_MD.write_text("\n".join(lines), encoding="utf-8")


def write_execution(state: dict[str, Any]) -> None:
    run_order = list(state.get("run_order", []))
    screening_count = len(state.get("screening_cases", {}))
    validation_count = len(state.get("validation_cases", {}))
    write_json(SUMMARY, {
        "schema": "bvm-qb-l3-bj2-targeted-combination-execution-v1",
        "experiment_id": EXP.name,
        "created_at_local": now(),
        "status": "PASS",
        "screening_new_physical_solve_count": screening_count,
        "validation_new_physical_solve_count": validation_count,
        "actual_new_physical_solve_count": len(run_order),
        "maximum_new_screening_solve_count": 2,
        "maximum_total_solve_count_if_clean_2_to_3": 4,
        "unauthorized_extra_solve_count": 0,
        "run_order": run_order,
        "outcome": state.get("outcome"),
        "conditional_validation_performed": validation_count > 0,
        "no_retry_performed": True,
        "no_replay": True,
        "no_passive_capture": True,
        "no_source_waveform_modification": True,
        "no_source_scaling": True,
        "no_jtl_change": True,
        "no_timestep_change": True,
        "no_extra_parameter": True,
        "raw_files_modified": 0,
        "scientific_analysis_performed": False,
    })


def finalize(state: dict[str, Any], result: dict[str, Any], outcome: str, reason: str) -> int:
    state["candidate_class"] = result.get("candidate_class")
    state["outcome"] = outcome
    state["status"] = outcome
    state["final_marker"] = "EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW"
    state["stop_reason"] = reason
    save_state(state)
    write_table(state, result)
    write_execution(state)
    print(json.dumps({"status": outcome, "final_marker": state["final_marker"], "candidate_class": result.get("candidate_class"), "new_physical_solves": len(state["run_order"]), "validation_new_physical_solves": len(state.get("validation_cases", {}))}, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reclassify-existing", action="store_true", help="recompute the result from completed immutable raw files without running the solver")
    args = parser.parse_args()
    preflight, matrix, relation = load_gate()
    point = matrix["points"][0]
    state = json.loads(STATE.read_text(encoding="utf-8")) if STATE.is_file() else state_template(preflight, relation)
    if not args.reclassify_existing and state.get("final_marker") and RESULT_PATH.is_file():
        write_table(state, json.loads(RESULT_PATH.read_text(encoding="utf-8")))
        write_execution(state)
        return 0
    if args.reclassify_existing:
        if set(state.get("screening_cases", {})) != set(SCREENING_MASKS):
            raise RuntimeError("cannot reclassify without both completed screening cases")
        result = analyse(point, state["screening_cases"], force=True)
        return finalize(state, result, OUTCOME_LABELS[result["candidate_class"]], "reclassified existing immutable screening raw after strict ordered-chain logic repair")
    save_state(state)
    screening_cases: dict[str, Any] = {}
    for mask in SCREENING_MASKS:
        case = run_case(point, mask, run_kind="SCREENING")
        screening_cases[mask] = case
        state["screening_cases"][mask] = case
        if case["run_id"] not in state["run_order"]:
            state["run_order"].append(case["run_id"])
        save_state(state)
    result = analyse(point, screening_cases)
    state["candidate_class"] = result.get("candidate_class")
    save_state(state)
    write_table(state, result)
    if result.get("candidate_class") == "S":
        for mask in VALIDATION_MASKS:
            case = run_case(point, mask, run_kind="CONDITIONAL_VALIDATION")
            state["validation_cases"][mask] = case
            if case["run_id"] not in state["run_order"]:
                state["run_order"].append(case["run_id"])
            save_state(state)
        validation = validation_summary(state)
        state["validation"] = validation
        if validation["chain_closure_candidate"]:
            state["secondary_outcome"] = "CHAIN_CLOSURE_CANDIDATE_FOUND"
            return finalize(state, result, "FULL_POPULATION_1_2_3_4_CANDIDATE", "clean 2/3 screening pair followed by registered 0001/1111 validation")
        return finalize(state, result, "DIRECT_2_TO_3_L3_BJ2_CANDIDATE", "clean 2/3 screening pair found; conditional validation completed without full 1/2/3/4 closure")
    return finalize(state, result, OUTCOME_LABELS[result["candidate_class"]], "screening pair completed; no conditional validation because clean 2/3 was not observed")


if __name__ == "__main__":
    raise SystemExit(main())
