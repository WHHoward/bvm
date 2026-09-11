#!/usr/bin/env python3
"""Execute the preregistered full closed-loop QB screening prefix.

This runner is deliberately sequential.  It never retries a solver failure,
never overwrites a run directory, and stops at the first raw-supported S
candidate long enough to run the separately registered full-population
validation gate.
"""

from __future__ import annotations

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
MATRIX_PATH = EXP / "screening/SCREENING_MATRIX.json"
PREFLIGHT_PATH = EXP / "analysis/preflight.json"
STATE_PATH = EXP / "screening/screening_state.json"
TABLE_JSON = EXP / "screening/SCREENING_TABLE.json"
TABLE_MD = EXP / "screening/SCREENING_TABLE.md"
EXECUTION_SUMMARY = EXP / "qa/execution_summary.json"
MASKS = ("0011", "0111")
REUSE_CASES = {
    ("RJ2_ohm", 10.0, "0011"): EXP / "references/reused_rj2p10/ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P10_0011",
    ("RJ2_ohm", 10.0, "0111"): EXP / "references/reused_rj2p10/ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P10_0111",
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


def json_write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


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
    return {
        "header_count": len(header),
        "sample_count": count,
        "first_timestamp": first[0],
        "last_timestamp": last[0],
    }


def current_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()


def head_relation(preflight_head: str) -> dict[str, Any]:
    head = current_head()
    if head == preflight_head:
        return {"status": "PASS", "head": head, "relation": "EXACT", "changed_paths": [], "commit_distance": 0}
    changed = set(subprocess.check_output(["git", "diff", "--name-only", f"{preflight_head}..{head}"], cwd=REPO, text=True).splitlines())
    prefix = EXP.relative_to(REPO).as_posix()
    allowed = {
        f"{prefix}/PREFLIGHT.md",
        f"{prefix}/analysis/preflight.json",
        f"{prefix}/SOURCE_MANIFEST.json",
        f"{prefix}/screening/SCREENING_MATRIX.json",
        f"{prefix}/screening/SCREENING_MATRIX.md",
    }
    distance = int(subprocess.check_output(["git", "rev-list", "--count", f"{preflight_head}..{head}"], cwd=REPO, text=True).strip())
    valid = distance == 1 and changed == allowed
    return {
        "status": "PASS" if valid else "FAIL",
        "head": head,
        "relation": "PREFLIGHT_SEAL_COMMIT" if valid else "UNEXPECTED",
        "changed_paths": sorted(changed),
        "commit_distance": distance,
    }


def load_gate() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    preflight = json.loads(PREFLIGHT_PATH.read_text(encoding="utf-8"))
    matrix = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
    if preflight.get("status") != "PASS":
        raise RuntimeError("screening preflight is not PASS")
    if preflight.get("physical_solve_count_before_preflight") != 0:
        raise RuntimeError("preflight records a nonzero prior solve count")
    if preflight.get("logical_screening_point_count") != 37 or preflight.get("logical_screening_case_count") != 74:
        raise RuntimeError("screening matrix count changed")
    if matrix.get("logical_point_count") != 37 or matrix.get("logical_case_count") != 74:
        raise RuntimeError("screening matrix JSON count changed")
    if sha256(MATRIX_PATH) != preflight.get("matrix_sha256"):
        raise RuntimeError("screening matrix SHA does not match preflight")
    if sha256(EXP / "SOURCE_MANIFEST.json") != preflight.get("source_manifest_sha256"):
        raise RuntimeError("source manifest SHA does not match preflight")
    relation = head_relation(str(preflight["head_at_preflight"]))
    if relation["status"] != "PASS":
        raise RuntimeError(f"HEAD/preflight relation is not allowed: {relation}")
    if not SOLVER.is_file() or sha256(SOLVER) != SOLVER_SHA256:
        raise RuntimeError("canonical solver identity changed")
    if not (EXP / "PREFLIGHT.md").is_file():
        raise RuntimeError("PREFLIGHT.md is missing")
    return preflight, matrix, relation


def matrix_point(matrix: dict[str, Any], point_id: str) -> dict[str, Any]:
    for point in matrix["points"]:
        if point["point_id"] == point_id:
            return point
    raise KeyError(point_id)


def point_key(point: dict[str, Any]) -> tuple[str, float]:
    return str(point["parameter"]), float(point["value"])


def reuse_root(point: dict[str, Any], mask: str) -> Path | None:
    return REUSE_CASES.get((str(point["parameter"]), float(point["value"]), mask))


def verify_complete_run(run_dir: Path) -> dict[str, Any]:
    required = [run_dir / name for name in ("deck.cir", "raw.csv", "metadata.json", "run.log")]
    if not all(path.is_file() for path in required):
        raise RuntimeError(f"partial run directory exists; refusing to resume or overwrite: {run_dir}")
    metadata = json.loads((run_dir / "metadata.json").read_text(encoding="utf-8"))
    if metadata.get("execution_status") != "RUN_PASS" or metadata.get("exit_code") != 0:
        raise RuntimeError(f"existing run is not a successful immutable run: {run_dir}")
    if metadata.get("artifacts", {}).get("raw", {}).get("sha256") != sha256(run_dir / "raw.csv"):
        raise RuntimeError(f"existing run metadata/raw hash mismatch: {run_dir}")
    return metadata


def reuse_case(point: dict[str, Any], mask: str, root: Path) -> dict[str, Any]:
    if not root.is_dir():
        raise RuntimeError(f"registered reuse reference is missing: {root}")
    metadata = json.loads((root / "metadata.json").read_text(encoding="utf-8"))
    raw = root / "raw.csv"
    deck = root / "deck.cir"
    log = root / "run.log"
    for path in (raw, deck, log):
        if not path.is_file():
            raise RuntimeError(f"registered reuse artifact is missing: {path}")
    if metadata.get("mask") != mask or metadata.get("working_point", {}).get("RJ2_ohm") != float(point["value"]):
        raise RuntimeError(f"reuse metadata does not match point/mask: {root}")
    return {
        "run_id": root.name,
        "mask": mask,
        "source_kind": "EXACT_IMMUTABLE_REUSE",
        "physical_solve_this_experiment": False,
        "raw_path": rel(raw),
        "deck_path": rel(deck),
        "metadata_path": rel(root / "metadata.json"),
        "log_path": rel(log),
        "raw_sha256": sha256(raw),
        "deck_sha256": sha256(deck),
        "raw_bytes": raw.stat().st_size,
        "raw_summary": raw_summary(raw),
        "origin_experiment": metadata.get("experiment_id"),
        "origin_run_id": metadata.get("run_id", root.name),
    }


def physical_case(point: dict[str, Any], mask: str, deck_source: Path, *, run_prefix: str = "SCREEN") -> dict[str, Any]:
    run_id = f"{run_prefix}_{point['point_id']}_{mask}"
    run_dir = EXP / "runs" / run_id
    deck = run_dir / "deck.cir"
    raw = run_dir / "raw.csv"
    log = run_dir / "run.log"
    metadata_path = run_dir / "metadata.json"
    if run_dir.exists():
        metadata = verify_complete_run(run_dir)
        if metadata.get("point_id") != point["point_id"] or metadata.get("mask") != mask:
            raise RuntimeError(f"existing run identity mismatch: {run_dir}")
        return {
            "run_id": run_id,
            "mask": mask,
            "source_kind": "NEW_PHYSICAL_SOLVE_ALREADY_COMPLETE",
            "physical_solve_this_experiment": True,
            "raw_path": rel(raw),
            "deck_path": rel(deck),
            "metadata_path": rel(metadata_path),
            "log_path": rel(log),
            "raw_sha256": sha256(raw),
            "deck_sha256": sha256(deck),
            "raw_bytes": raw.stat().st_size,
            "raw_summary": raw_summary(raw),
            "execution_status": metadata.get("execution_status"),
        }
    run_dir.mkdir(parents=True)
    shutil.copy2(deck_source, deck)
    started = now()
    command = [str(SOLVER), "-a", "1", "-o", str(raw), str(deck)]
    with log.open("x", encoding="utf-8") as stream:
        completed = subprocess.run(command, cwd=REPO, stdout=stream, stderr=subprocess.STDOUT, check=False)
    finished = now()
    raw_exists = raw.is_file()
    record: dict[str, Any] = {
        "schema": "bvm-full-closed-loop-qb-screening-run-metadata-v1",
        "experiment_id": EXP.name,
        "run_id": run_id,
        "point_id": point["point_id"],
        "parameter": point["parameter"],
        "value": point["value"],
        "mask": mask,
        "topology": "BVM1..4 -> COMMON_SL -> 8-JJ JSL -> QB -> six-stage JTL -> R_TERM",
        "working_point": {"parameter_changed": point["parameter"], "tested_value": point["value"], "baseline": json.loads((EXP / "screening/SCREENING_MATRIX.json").read_text(encoding="utf-8"))["baseline"]},
        "started_at_local": started,
        "finished_at_local": finished,
        "git_head_before_run": current_head(),
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
        json.dump(record, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    if record["execution_status"] != "RUN_PASS":
        raise RuntimeError(f"solver failed without retry: {run_id}, exit_code={completed.returncode}, raw={raw_exists}")
    return {
        "run_id": run_id,
        "mask": mask,
        "source_kind": "NEW_PHYSICAL_SOLVE",
        "physical_solve_this_experiment": True,
        "raw_path": rel(raw),
        "deck_path": rel(deck),
        "metadata_path": rel(metadata_path),
        "log_path": rel(log),
        "raw_sha256": sha256(raw),
        "deck_sha256": sha256(deck),
        "raw_bytes": raw.stat().st_size,
        "raw_summary": raw_summary(raw),
        "execution_status": record["execution_status"],
    }


def result_path(point_id: str) -> Path:
    return EXP / "screening/results" / f"{point_id}.json"


def analyse_point(point: dict[str, Any], cases: dict[str, Any]) -> dict[str, Any]:
    output = result_path(point["point_id"])
    expected_paths = {mask: cases[mask]["raw_path"] for mask in MASKS}
    if output.is_file():
        result = json.loads(output.read_text(encoding="utf-8"))
        actual_paths = {"0011": result.get("n2", {}).get("raw_path"), "0111": result.get("n3", {}).get("raw_path")}
        actual_hashes = {"0011": result.get("n2", {}).get("raw_sha256"), "0111": result.get("n3", {}).get("raw_sha256")}
        expected_hashes = {mask: cases[mask]["raw_sha256"] for mask in MASKS}
        if actual_paths != expected_paths or actual_hashes != expected_hashes:
            raise RuntimeError(f"existing analysis result does not bind to current raw cases: {output}")
        return result
    command = [sys.executable, str(EXP / "analysis/screening_analysis.py"), "--point-id", point["point_id"], "--parameter", str(point["parameter"]), "--value", str(point["value"]), "--n2", str(REPO / expected_paths["0011"]), "--n3", str(REPO / expected_paths["0111"])]
    completed = subprocess.run(command, cwd=REPO, check=False)
    if completed.returncode != 0 or not output.is_file():
        raise RuntimeError(f"raw analysis failed for {point['point_id']}; no solver retry is permitted")
    result = json.loads(output.read_text(encoding="utf-8"))
    if result.get("n2", {}).get("raw_sha256") != expected_hashes["0011"] or result.get("n3", {}).get("raw_sha256") != expected_hashes["0111"]:
        raise RuntimeError(f"analysis output hash binding failed: {output}")
    return result


def state_template(preflight: dict[str, Any], matrix: dict[str, Any], relation: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "bvm-full-closed-loop-qb-screening-state-v1",
        "experiment_id": EXP.name,
        "created_at_local": now(),
        "updated_at_local": now(),
        "status": "RUNNING",
        "final_marker": None,
        "preflight_head": preflight["head_at_preflight"],
        "execution_head": relation["head"],
        "logical_point_count": matrix["logical_point_count"],
        "logical_case_count": matrix["logical_case_count"],
        "maximum_new_screening_solve_count": preflight["maximum_new_screening_solve_count"],
        "maximum_total_new_solve_count_including_validation": preflight["maximum_total_new_solve_count_including_validation"],
        "points": {},
        "run_order": [],
        "failed_runs": [],
        "candidate_point_id": None,
        "validation": None,
        "early_stop": None,
    }


def load_state(preflight: dict[str, Any], matrix: dict[str, Any], relation: dict[str, Any]) -> dict[str, Any]:
    if not STATE_PATH.is_file():
        return state_template(preflight, matrix, relation)
    state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    if state.get("preflight_head") != preflight.get("head_at_preflight"):
        raise RuntimeError("screening state belongs to a different preflight seal")
    return state


def save_state(state: dict[str, Any]) -> None:
    state["updated_at_local"] = now()
    json_write(STATE_PATH, state)


def metric_time(evidence: dict[str, Any], track: str, ordinal: int) -> float | None:
    threshold = f"{({1: 0.5, 2: 1.5, 3: 2.5, 4: 3.5}[ordinal]):g}"
    return evidence.get("phase_navigation", {}).get(track, {}).get("threshold_navigation_times_ps", {}).get(threshold)


def case_table_fields(result: dict[str, Any], branch: str) -> dict[str, Any]:
    case = result[branch]
    evidence = case["evidence"]
    terminal = evidence.get("terminal", {})
    pulses = terminal.get("matched_candidate_pulses", terminal.get("pulses", []))
    reset = evidence.get("internal_reset", {})
    return {
        "classification": case.get("classification", {}).get("classification"),
        "complete_response_count": evidence.get("complete_response_candidate_count"),
        "control_status": evidence.get("control", {}).get("status"),
        "BJ1_2_ps": metric_time(evidence, "BJ1", 2),
        "BJ2_2_ps": metric_time(evidence, "BJ2", 2),
        "terminal_2_ps": pulses[1].get("peak_time_ps") if len(pulses) >= 2 else None,
        "BJ1_3_ps": metric_time(evidence, "BJ1", 3),
        "BJ2_3_ps": metric_time(evidence, "BJ2", 3),
        "BJ1_4_ps": metric_time(evidence, "BJ1", 4),
        "BJ2_4_ps": metric_time(evidence, "BJ2", 4),
        "JTL6_4_ps": metric_time(evidence, "JTL6", 4),
        "terminal_4_ps": pulses[3].get("peak_time_ps") if len(pulses) >= 4 else None,
        "max_BJ1_relative_turns": evidence.get("phase_navigation", {}).get("BJ1", {}).get("max_relative_turns"),
        "final_BJ1_relative_turns": evidence.get("phase_navigation", {}).get("BJ1", {}).get("final_relative_turns"),
        "max_BJ2_relative_turns": evidence.get("phase_navigation", {}).get("BJ2", {}).get("max_relative_turns"),
        "final_BJ2_relative_turns": evidence.get("phase_navigation", {}).get("BJ2", {}).get("final_relative_turns"),
        "post_third_peak_I_L1_A": reset.get("peak_I_L1_A"),
        "integral_121_126_V_s": reset.get("integral_121_126_V_s"),
    }


def write_screening_table(state: dict[str, Any], matrix: dict[str, Any]) -> None:
    rows: list[dict[str, Any]] = []
    for point in matrix["points"]:
        pid = point["point_id"]
        record = state.get("points", {}).get(pid)
        row: dict[str, Any] = {"parameter": point["parameter"], "tested_value": point["value"], "point_id": pid, "execution_status": "NOT_RUN", "candidate_class": None, "notes": []}
        if record and record.get("status") == "COMPLETE":
            result = json.loads(result_path(pid).read_text(encoding="utf-8"))
            n2, n3 = case_table_fields(result, "n2"), case_table_fields(result, "n3")
            row.update({
                "execution_status": "COMPLETE",
                "candidate_class": result.get("candidate_class"),
                "candidate_label": result.get("candidate_label"),
                "control_status": "CLEAN" if n2["control_status"] == n3["control_status"] == "CLEAN" else "CONTROL_CONTAMINATED",
                "N2_classification": n2["classification"],
                "N3_classification": n3["classification"],
                "N2_complete_response_count": n2["complete_response_count"],
                "N3_complete_response_count": n3["complete_response_count"],
                "N2_BJ1_2_ps": n2["BJ1_2_ps"],
                "N2_BJ2_2_ps": n2["BJ2_2_ps"],
                "N2_terminal_2_ps": n2["terminal_2_ps"],
                "N3_BJ1_3_ps": n3["BJ1_3_ps"],
                "N3_BJ2_3_ps": n3["BJ2_3_ps"],
                "N3_BJ1_4_ps": n3["BJ1_4_ps"],
                "N3_BJ2_4_ps": n3["BJ2_4_ps"],
                "N3_JTL6_4_ps": n3["JTL6_4_ps"],
                "N3_terminal_4_ps": n3["terminal_4_ps"],
                "N3_max_BJ1_relative_turns": n3["max_BJ1_relative_turns"],
                "N3_final_BJ1_relative_turns": n3["final_BJ1_relative_turns"],
                "N3_max_BJ2_relative_turns": n3["max_BJ2_relative_turns"],
                "N3_final_BJ2_relative_turns": n3["final_BJ2_relative_turns"],
                "N3_post_third_peak_I_L1_A": n3["post_third_peak_I_L1_A"],
                "N3_integral_121_126_V_s": n3["integral_121_126_V_s"],
                "notes": result.get("notes", []) + n3.get("classification", {}).get("notes", []),
                "case_paths": {mask: record.get("cases", {}).get(mask, {}).get("raw_path") for mask in MASKS},
            })
        rows.append(row)
    table = {
        "schema": "bvm-full-closed-loop-qb-screening-table-v1",
        "experiment_id": EXP.name,
        "updated_at_local": now(),
        "logical_point_count": len(rows),
        "rows": rows,
        "not_sfq_count": True,
        "phase_semantics": "raw radians; threshold navigation after continuous unwrap and division by 2*pi; not an SFQ count",
    }
    json_write(TABLE_JSON, table)
    columns = ["parameter", "tested_value", "point_id", "execution_status", "control_status", "N2_classification", "N3_classification", "N2_complete_response_count", "N3_complete_response_count", "N2_BJ1_2_ps", "N2_BJ2_2_ps", "N2_terminal_2_ps", "N3_BJ1_3_ps", "N3_BJ2_3_ps", "N3_BJ1_4_ps", "N3_BJ2_4_ps", "N3_JTL6_4_ps", "N3_terminal_4_ps", "N3_max_BJ1_relative_turns", "N3_final_BJ1_relative_turns", "N3_max_BJ2_relative_turns", "N3_final_BJ2_relative_turns", "N3_post_third_peak_I_L1_A", "N3_integral_121_126_V_s", "candidate_class", "notes"]
    lines = ["# Full closed-loop QB screening table", "", "Rows are one-factor points in registered priority order. Empty fields mean the point was not run because of early stop or is not yet complete. Phase values are navigation diagnostics, not SFQ counts.", "", "| " + " | ".join(columns) + " |", "|" + "---|" * len(columns)]
    for row in rows:
        values = []
        for column in columns:
            value = row.get(column)
            if isinstance(value, list):
                value = "; ".join(str(item) for item in value)
            values.append("" if value is None else str(value).replace("|", "\\|"))
        lines.append("| " + " | ".join(values) + " |")
    lines.extend(["", f"Completed logical points: `{sum(row['execution_status'] == 'COMPLETE' for row in rows)}` / `{len(rows)}`.", f"Completed logical cases: `{sum(2 for row in rows if row['execution_status'] == 'COMPLETE')}`; exact reuse cases are counted logically but not as new physical solves.", ""])
    TABLE_MD.write_text("\n".join(lines), encoding="utf-8")


def write_execution_summary(state: dict[str, Any], *, status: str) -> None:
    physical_runs = []
    reused_cases = []
    failed = list(state.get("failed_runs", []))
    logical_points = 0
    for point in state.get("points", {}).values():
        if point.get("status") == "COMPLETE":
            logical_points += 1
        for case in point.get("cases", {}).values():
            if case.get("physical_solve_this_experiment"):
                if case.get("run_id") not in physical_runs:
                    physical_runs.append(case["run_id"])
            elif case.get("source_kind") == "EXACT_IMMUTABLE_REUSE":
                reused_cases.append(f"{point['point_id']}/{case['mask']}")
    validation = state.get("validation") or {}
    validation_runs = validation.get("new_run_ids", []) if isinstance(validation, dict) else []
    for run_id in validation_runs:
        if run_id not in physical_runs:
            physical_runs.append(run_id)
    record = {
        "schema": "bvm-full-closed-loop-qb-screening-execution-v1",
        "experiment_id": EXP.name,
        "created_at_local": now(),
        "status": status,
        "preflight_head": state.get("preflight_head"),
        "execution_head": state.get("execution_head"),
        "logical_screening_point_count": 37,
        "logical_screening_case_count": 74,
        "logical_screening_points_completed": logical_points,
        "logical_screening_cases_completed": logical_points * 2,
        "exact_new_physical_solve_count": len(physical_runs),
        "reused_physical_case_count": len(reused_cases),
        "reused_cases": reused_cases,
        "solver_solve_invocations": len(physical_runs),
        "validation_new_physical_solve_count": len(validation_runs),
        "run_order": physical_runs,
        "failed_runs": failed,
        "unauthorized_extra_solves": 0,
        "maximum_new_screening_solve_count": 72,
        "maximum_total_new_solve_count_including_validation": 74,
        "early_stop": state.get("early_stop"),
        "candidate_point_id": state.get("candidate_point_id"),
        "raw_files_modified": 0,
        "scientific_analysis_performed": False,
        "scientific_review_performed": False,
        "no_retry_performed": True,
        "no_replay": True,
        "no_passive_capture": True,
        "no_timestep_sweep": True,
    }
    json_write(EXECUTION_SUMMARY, record)


def read_validation_summary() -> dict[str, Any] | None:
    path = EXP / "screening/validation_summary.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def run_candidate_validation(state: dict[str, Any], point: dict[str, Any]) -> dict[str, Any]:
    candidate_file = EXP / "screening/CANDIDATE_FOUND.json"
    if not candidate_file.is_file():
        json_write(candidate_file, {"schema": "bvm-full-closed-loop-qb-screening-candidate-v1", "experiment_id": EXP.name, "created_at_local": now(), "point_id": point["point_id"], "parameter": point["parameter"], "value": point["value"], "screening_result": rel(result_path(point["point_id"])), "action": "stop broad screening and run only 0001/1111 validation"})
    summary = read_validation_summary()
    if summary is None:
        completed = subprocess.run([sys.executable, str(EXP / "analysis/run_candidate_validation.py")], cwd=REPO, check=False)
        if completed.returncode not in (0, 1):
            raise RuntimeError("candidate validation execution failed; no retry is permitted")
        summary = read_validation_summary()
        if summary is None:
            raise RuntimeError("candidate validation returned without validation_summary.json")
    state["candidate_point_id"] = point["point_id"]
    state["validation"] = summary
    return summary


def finalize(state: dict[str, Any], matrix: dict[str, Any], *, status: str, reason: str) -> int:
    state["status"] = status
    state["final_marker"] = "EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW"
    state["early_stop"] = reason
    save_state(state)
    write_screening_table(state, matrix)
    write_execution_summary(state, status="PASS")
    print(json.dumps({"status": status, "final_marker": state["final_marker"], "reason": reason, "new_physical_solves": json.loads(EXECUTION_SUMMARY.read_text(encoding="utf-8"))["exact_new_physical_solve_count"]}, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    preflight, matrix, relation = load_gate()
    state = load_state(preflight, matrix, relation)
    if state.get("final_marker"):
        write_execution_summary(state, status="PASS")
        print(json.dumps({"status": state.get("status"), "final_marker": state.get("final_marker"), "resumed": True}, ensure_ascii=False, indent=2))
        return 0
    save_state(state)
    points = matrix["points"]
    for point in points:
        pid = point["point_id"]
        existing = state.get("points", {}).get(pid)
        if existing and existing.get("status") == "COMPLETE":
            result = json.loads(result_path(pid).read_text(encoding="utf-8"))
        else:
            cases: dict[str, Any] = {}
            for mask in MASKS:
                reuse = reuse_root(point, mask)
                if reuse is not None:
                    case = reuse_case(point, mask, reuse)
                else:
                    deck = EXP / "screening/decks" / pid / f"{mask}.cir"
                    if not deck.is_file():
                        raise RuntimeError(f"registered screening deck is missing: {deck}")
                    case = physical_case(point, mask, deck)
                    state["run_order"].append(case["run_id"])
                cases[mask] = case
                state.setdefault("points", {}).setdefault(pid, {"point_id": pid, "parameter": point["parameter"], "value": point["value"], "status": "PARTIAL", "cases": {}})["cases"][mask] = case
                save_state(state)
            result = analyse_point(point, cases)
            state["points"][pid] = {"point_id": pid, "parameter": point["parameter"], "value": point["value"], "status": "COMPLETE", "candidate_class": result.get("candidate_class"), "candidate_label": result.get("candidate_label"), "cases": cases, "result_path": rel(result_path(pid))}
            save_state(state)
        write_screening_table(state, matrix)
        if result.get("candidate_class") == "S":
            summary = run_candidate_validation(state, point)
            if summary.get("classification") == "FULL_POPULATION_1_2_3_4_CANDIDATE":
                return finalize(state, matrix, status="FULL_POPULATION_1_2_3_4_CANDIDATE", reason="DIRECT_2_TO_3_CANDIDATE validated at full population")
            state["early_stop"] = "screening S point validation failed; broad screening resumed"
            save_state(state)
    completed_results = [json.loads(result_path(point["point_id"]).read_text(encoding="utf-8")) for point in points if result_path(point["point_id"]).is_file()]
    promising = [result for result in completed_results if result.get("candidate_class") == "A"]
    if promising:
        selected = [f"{item['point_id']}={item['value']}" for item in promising[:2]]
        reason = "NO_DIRECT_2_TO_3_POINT / PROMISING_DIRECTIONS_IDENTIFIED; top A directions: " + ", ".join(selected)
        return finalize(state, matrix, status="NO_DIRECT_2_TO_3_POINT", reason=reason)
    return finalize(state, matrix, status="NO_SELECTIVE_RECEIVER_PARAMETER_DIRECTION_FOUND", reason="NO_SELECTIVE_RECEIVER_PARAMETER_DIRECTION_FOUND")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"SCREENING BLOCKED: {exc}", file=sys.stderr)
        raise
