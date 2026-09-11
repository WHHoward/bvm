#!/usr/bin/env python3
"""Execute the registered two-parameter combination sequence."""

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
MATRIX = EXP / "screening/COMBINATION_MATRIX.json"
PREFLIGHT = EXP / "analysis/preflight.json"
STATE = EXP / "screening/combination_state.json"
TABLE_JSON = EXP / "screening/COMBINATION_TABLE.json"
TABLE_MD = EXP / "screening/COMBINATION_TABLE.md"
EXECUTION = EXP / "qa/execution_summary.json"
MASKS = ("0011", "0111")


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


def current_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()


def head_relation(sealed_head: str) -> dict[str, Any]:
    head = current_head()
    if head == sealed_head:
        return {"status": "PASS", "head": head, "relation": "EXACT", "changed_paths": [], "commit_distance": 0}
    changed = set(subprocess.check_output(["git", "diff", "--name-only", f"{sealed_head}..{head}"], cwd=REPO, text=True).splitlines())
    prefix = EXP.relative_to(REPO).as_posix()
    allowed = {f"{prefix}/PREFLIGHT.md", f"{prefix}/analysis/preflight.json", f"{prefix}/SOURCE_MANIFEST.json", f"{prefix}/screening/COMBINATION_MATRIX.json", f"{prefix}/screening/COMBINATION_MATRIX.md"}
    valid = int(subprocess.check_output(["git", "rev-list", "--count", f"{sealed_head}..{head}"], cwd=REPO, text=True).strip()) == 1 and changed in (allowed, allowed - {f"{prefix}/screening/COMBINATION_MATRIX.md"})
    return {"status": "PASS" if valid else "FAIL", "head": head, "relation": "PREFLIGHT_SEAL_COMMIT" if valid else "UNEXPECTED", "changed_paths": sorted(changed), "commit_distance": int(subprocess.check_output(["git", "rev-list", "--count", f"{sealed_head}..{head}"], cwd=REPO, text=True).strip())}


def load_gate() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    preflight = json.loads(PREFLIGHT.read_text(encoding="utf-8"))
    matrix = json.loads(MATRIX.read_text(encoding="utf-8"))
    if preflight.get("status") != "PASS" or matrix.get("logical_combination_point_count") != 9 or matrix.get("logical_combination_case_count") != 18:
        raise RuntimeError("combination preflight or matrix is not PASS")
    if preflight.get("physical_solve_count_before_preflight") != 0:
        raise RuntimeError("preflight has nonzero prior solve count")
    if sha256(MATRIX) != preflight.get("matrix_sha256") or sha256(EXP / "SOURCE_MANIFEST.json") != preflight.get("source_manifest_sha256"):
        raise RuntimeError("matrix/source manifest is not bound to preflight")
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


def verify_existing(run_dir: Path, point_id: str, mask: str) -> dict[str, Any]:
    required = [run_dir / name for name in ("deck.cir", "raw.csv", "metadata.json", "run.log")]
    if not all(path.is_file() for path in required):
        raise RuntimeError(f"partial combination run exists; refusing overwrite: {run_dir}")
    metadata = json.loads((run_dir / "metadata.json").read_text(encoding="utf-8"))
    if metadata.get("point_id") != point_id or metadata.get("mask") != mask or metadata.get("execution_status") != "RUN_PASS":
        raise RuntimeError(f"existing combination run identity/status mismatch: {run_dir}")
    if metadata.get("artifacts", {}).get("raw", {}).get("sha256") != sha256(run_dir / "raw.csv"):
        raise RuntimeError(f"existing combination raw hash mismatch: {run_dir}")
    return {"run_id": run_dir.name, "mask": mask, "source_kind": "NEW_PHYSICAL_SOLVE_ALREADY_COMPLETE", "physical_solve_this_experiment": True, "raw_path": rel(run_dir / "raw.csv"), "deck_path": rel(run_dir / "deck.cir"), "metadata_path": rel(run_dir / "metadata.json"), "log_path": rel(run_dir / "run.log"), "raw_sha256": sha256(run_dir / "raw.csv"), "deck_sha256": sha256(run_dir / "deck.cir"), "raw_bytes": (run_dir / "raw.csv").stat().st_size, "raw_summary": raw_summary(run_dir / "raw.csv")}


def run_physical(point: dict[str, Any], mask: str, deck_source: Path, prefix: str = "COMB") -> dict[str, Any]:
    run_id = f"{prefix}_{point['point_id']}_{mask}"
    run_dir = EXP / "runs" / run_id
    if run_dir.exists():
        return verify_existing(run_dir, point["point_id"], mask)
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
    record = {
        "schema": "bvm-qb-two-parameter-combination-run-metadata-v1", "experiment_id": EXP.name, "run_id": run_id,
        "point_id": point["point_id"], "changes": point["changes"], "mask": mask,
        "topology": "BVM1..4 -> COMMON_SL -> 8-JJ JSL -> QB -> six-stage JTL -> R_TERM",
        "stimulus": {"amplitude_uA": 100.0, "tran": ".tran 0.1p 200p", "history": "0-50 IDLE; 50-61 WRITE0; 61-70 IDLE; 70-81 CONTROL; 81-90 IDLE; 90-101 WRITE1; 101-110 SETTLE; 110-121 FINAL READ; 121-200 TAIL"},
        "started_at_local": started, "finished_at_local": finished, "git_head_before_run": current_head(), "command": command,
        "solver": {"path": rel(SOLVER), "sha256": sha256(SOLVER), "version": subprocess.check_output([str(SOLVER), "--version"], cwd=REPO, text=True)},
        "deck_source": {"path": rel(deck_source), "sha256": sha256(deck_source)},
        "artifacts": {"deck": {"path": rel(deck), "sha256": sha256(deck), "bytes": deck.stat().st_size}, "raw": {"path": rel(raw), "exists": raw_exists, "sha256": sha256(raw) if raw_exists else None, "bytes": raw.stat().st_size if raw_exists else None}, "log": {"path": rel(log), "sha256": sha256(log), "bytes": log.stat().st_size}},
        "exit_code": completed.returncode, "execution_status": "RUN_PASS" if completed.returncode == 0 and raw_exists else "RUN_FAIL",
        "physical_solve_this_experiment": True, "raw_immutable": True, "parameter_tuning": False, "scientific_analysis_performed": False, "raw_summary": raw_summary(raw),
    }
    with metadata_path.open("x", encoding="utf-8") as stream:
        json.dump(record, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    if record["execution_status"] != "RUN_PASS":
        raise RuntimeError(f"solver failed without retry: {run_id}")
    return {"run_id": run_id, "mask": mask, "source_kind": "NEW_PHYSICAL_SOLVE", "physical_solve_this_experiment": True, "raw_path": rel(raw), "deck_path": rel(deck), "metadata_path": rel(metadata_path), "log_path": rel(log), "raw_sha256": sha256(raw), "deck_sha256": sha256(deck), "raw_bytes": raw.stat().st_size, "raw_summary": raw_summary(raw)}


def state_template(preflight: dict[str, Any], relation: dict[str, Any]) -> dict[str, Any]:
    return {"schema": "bvm-qb-two-parameter-combination-state-v1", "experiment_id": EXP.name, "created_at_local": now(), "updated_at_local": now(), "status": "RUNNING", "final_marker": None, "preflight_head": preflight["head_at_preflight"], "execution_head": relation["head"], "logical_combination_point_count": 9, "logical_combination_case_count": 18, "maximum_new_screening_solve_count": 18, "maximum_total_new_solve_count_including_validation": 20, "points": {}, "run_order": [], "failed_runs": [], "candidate_point_id": None, "validation": None, "early_stop_point": None, "near_direct_candidates": [], "strongest_near_direct_candidate": None}


def load_state(preflight: dict[str, Any], relation: dict[str, Any]) -> dict[str, Any]:
    if not STATE.is_file():
        return state_template(preflight, relation)
    state = json.loads(STATE.read_text(encoding="utf-8"))
    if state.get("preflight_head") != preflight["head_at_preflight"]:
        raise RuntimeError("combination state belongs to a different preflight")
    return state


def save_state(state: dict[str, Any]) -> None:
    state["updated_at_local"] = now()
    write_json(STATE, state)


def time_at(evidence: dict[str, Any], track: str, ordinal: int) -> float | None:
    threshold = f"{({1: 0.5, 2: 1.5, 3: 2.5, 4: 3.5}[ordinal]):g}"
    return evidence.get("phase_navigation", {}).get(track, {}).get("threshold_navigation_times_ps", {}).get(threshold)


def case_fields(result: dict[str, Any], branch: str) -> dict[str, Any]:
    case = result[branch]
    evidence = case["evidence"]
    pulses = evidence.get("terminal", {}).get("matched_candidate_pulses", evidence.get("terminal", {}).get("pulses", []))
    reset = evidence.get("internal_reset", {})
    source = evidence.get("source_feedback", {}).get("I_B_JSL8", {})
    return {"classification": case["classification"].get("classification"), "control_status": case["classification"].get("control_status"), "complete_response_count": evidence.get("complete_response_candidate_count"), "BJ1_2_ps": time_at(evidence, "BJ1", 2), "BJ2_2_ps": time_at(evidence, "BJ2", 2), "JTL6_2_ps": time_at(evidence, "JTL6", 2), "terminal_2_ps": pulses[1].get("peak_time_ps") if len(pulses) >= 2 else None, "BJ1_3_ps": time_at(evidence, "BJ1", 3), "BJ2_3_ps": time_at(evidence, "BJ2", 3), "BJ1_4_ps": time_at(evidence, "BJ1", 4), "BJ2_4_ps": time_at(evidence, "BJ2", 4), "JTL6_4_ps": time_at(evidence, "JTL6", 4), "terminal_4_ps": pulses[3].get("peak_time_ps") if len(pulses) >= 4 else None, "N3_max_BJ1_turns": reset.get("BJ1_max_relative_turns"), "N3_final_BJ1_turns": reset.get("BJ1_final_relative_turns"), "N3_max_BJ2_turns": reset.get("BJ2_max_relative_turns"), "N3_final_BJ2_turns": reset.get("BJ2_final_relative_turns"), "post_third_peak_I_L1_A": reset.get("peak_I_L1_A"), "integral_118_121_V_s": reset.get("integral_118_121_V_s"), "integral_121_124_V_s": reset.get("integral_121_124_V_s"), "integral_124_128_V_s": reset.get("integral_124_128_V_s"), "source_110_121_A_s": source.get("110_121", {}).get("signed_area_A_s"), "source_121_124_A_s": source.get("121_124", {}).get("signed_area_A_s")}


def write_table(state: dict[str, Any], matrix: dict[str, Any]) -> None:
    rows: list[dict[str, Any]] = []
    for point in matrix["points"]:
        pid = point["point_id"]
        row: dict[str, Any] = {"combination_id": pid, "changes": point["changes"], "execution_status": "NOT_RUN", "history_control_status": None, "N2_classification": None, "N3_classification": None, "candidate_class": None, "notes": []}
        record = state.get("points", {}).get(pid)
        if record and record.get("status") == "COMPLETE":
            result = json.loads((EXP / "screening/results" / f"{pid}.json").read_text(encoding="utf-8"))
            n2, n3 = case_fields(result, "n2"), case_fields(result, "n3")
            row.update({"execution_status": "COMPLETE", "history_control_status": "CLEAN" if n2["control_status"] == n3["control_status"] == "CLEAN" else "CONTROL_CONTAMINATED", "N2_classification": n2["classification"], "N3_classification": n3["classification"], "candidate_class": result.get("candidate_class"), "N2_response_count": n2["complete_response_count"], "N3_response_count": n3["complete_response_count"], "N2_BJ1_2_ps": n2["BJ1_2_ps"], "N2_BJ2_2_ps": n2["BJ2_2_ps"], "N2_JTL6_2_ps": n2["JTL6_2_ps"], "N2_terminal_2_ps": n2["terminal_2_ps"], "N3_BJ1_3_ps": n3["BJ1_3_ps"], "N3_BJ2_3_ps": n3["BJ2_3_ps"], "N3_BJ1_4_ps": n3["BJ1_4_ps"], "N3_BJ2_4_ps": n3["BJ2_4_ps"], "N3_JTL6_4_ps": n3["JTL6_4_ps"], "N3_terminal_4_ps": n3["terminal_4_ps"], "N3_max_BJ1_turns": n3["N3_max_BJ1_turns"], "N3_final_BJ1_turns": n3["N3_final_BJ1_turns"], "N3_max_BJ2_turns": n3["N3_max_BJ2_turns"], "N3_final_BJ2_turns": n3["N3_final_BJ2_turns"], "post_third_peak_I_L1_A": n3["post_third_peak_I_L1_A"], "integral_118_121_V_s": n3["integral_118_121_V_s"], "integral_121_124_V_s": n3["integral_121_124_V_s"], "integral_124_128_V_s": n3["integral_124_128_V_s"], "source_110_121_A_s": n3["source_110_121_A_s"], "source_121_124_A_s": n3["source_121_124_A_s"], "notes": result.get("notes", []) + result.get("n3", {}).get("classification", {}).get("fourth_diagnostics", {}).get("notes", [])})
        rows.append(row)
    write_json(TABLE_JSON, {"schema": "bvm-qb-two-parameter-combination-table-v1", "experiment_id": EXP.name, "updated_at_local": now(), "logical_point_count": 9, "rows": rows, "phase_semantics": "raw radians; threshold navigation rad/(2*pi), not SFQ count", "control_semantics": "complete downstream chain only in registered history windows"})
    columns = ["combination_id", "changes", "execution_status", "history_control_status", "N2_classification", "N3_classification", "N2_response_count", "N3_response_count", "N2_BJ1_2_ps", "N2_BJ2_2_ps", "N2_JTL6_2_ps", "N2_terminal_2_ps", "N3_BJ1_3_ps", "N3_BJ2_3_ps", "N3_BJ1_4_ps", "N3_BJ2_4_ps", "N3_JTL6_4_ps", "N3_terminal_4_ps", "N3_max_BJ1_turns", "N3_final_BJ1_turns", "N3_max_BJ2_turns", "N3_final_BJ2_turns", "post_third_peak_I_L1_A", "integral_118_121_V_s", "integral_121_124_V_s", "integral_124_128_V_s", "source_110_121_A_s", "source_121_124_A_s", "candidate_class", "notes"]
    lines = ["# Two-parameter full closed-loop combination table", "", "Rows follow the registered execution order. Phase/area/peak values are diagnostics, not SFQ counts.", "", "| " + " | ".join(columns) + " |", "|" + "---|" * len(columns)]
    for row in rows:
        values = []
        for column in columns:
            value = row.get(column)
            if isinstance(value, dict):
                value = ", ".join(f"{key}={val:g}" for key, val in value.items())
            if isinstance(value, list):
                value = "; ".join(str(item) for item in value)
            values.append("" if value is None else str(value).replace("|", "\\|"))
        lines.append("| " + " | ".join(values) + " |")
    lines.extend(["", f"Completed logical points: {sum(row['execution_status'] == 'COMPLETE' for row in rows)} / 9.", ""])
    TABLE_MD.write_text("\n".join(lines), encoding="utf-8")


def write_execution_summary(state: dict[str, Any], status: str) -> None:
    run_ids: list[str] = []
    for point in state.get("points", {}).values():
        for case in point.get("cases", {}).values():
            if case.get("physical_solve_this_experiment") and case.get("run_id") not in run_ids:
                run_ids.append(case["run_id"])
    validation = state.get("validation") or {}
    for run_id in validation.get("new_run_ids", []) if isinstance(validation, dict) else []:
        if run_id not in run_ids:
            run_ids.append(run_id)
    complete_points = sum(record.get("status") == "COMPLETE" for record in state.get("points", {}).values())
    record = {"schema": "bvm-qb-two-parameter-combination-execution-v1", "experiment_id": EXP.name, "created_at_local": now(), "status": status, "preflight_head": state.get("preflight_head"), "execution_head": state.get("execution_head"), "logical_combination_point_count": 9, "logical_combination_case_count": 18, "actual_started_combination_point_count": complete_points, "actual_screening_physical_solve_count": sum(1 for run_id in run_ids if run_id.startswith("COMB_")), "validation_new_physical_solve_count": len(validation.get("new_run_ids", [])) if isinstance(validation, dict) else 0, "exact_new_physical_solve_count": len(run_ids), "reused_raw_count": 2, "unauthorized_extra_solve_count": 0, "unauthorized_extra_solves": 0, "run_order": run_ids, "early_stop_point": state.get("early_stop_point"), "near_direct_candidates": state.get("near_direct_candidates", []), "strongest_near_direct_candidate": state.get("strongest_near_direct_candidate"), "maximum_screening_solve_count": 18, "maximum_total_new_solve_count_including_validation": 20, "no_retry_performed": True, "no_replay": True, "no_passive_capture": True, "no_source_scaling": True, "no_read_extension": True, "no_jtl_parameter_change": True, "no_timestep_change": True, "raw_files_modified": 0, "scientific_analysis_performed": False, "scientific_review_performed": False}
    write_json(EXECUTION, record)


def finalize(state: dict[str, Any], matrix: dict[str, Any], status: str, reason: str) -> int:
    state["status"] = status
    state["final_marker"] = "EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW"
    state["early_stop_point"] = reason
    save_state(state)
    write_table(state, matrix)
    write_execution_summary(state, "PASS")
    print(json.dumps({"status": status, "final_marker": state["final_marker"], "reason": reason, "new_physical_solves": json.loads(EXECUTION.read_text(encoding="utf-8"))["exact_new_physical_solve_count"]}, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    preflight, matrix, relation = load_gate()
    state = load_state(preflight, relation)
    if state.get("final_marker"):
        write_execution_summary(state, "PASS")
        print(json.dumps({"status": state["status"], "final_marker": state["final_marker"], "resumed": True}, ensure_ascii=False, indent=2))
        return 0
    save_state(state)
    for point in matrix["points"]:
        pid = point["point_id"]
        record = state.get("points", {}).get(pid)
        if record and record.get("status") == "COMPLETE":
            result = json.loads((EXP / "screening/results" / f"{pid}.json").read_text(encoding="utf-8"))
        else:
            cases: dict[str, Any] = {}
            for mask in MASKS:
                deck = EXP / "screening/decks" / pid / f"{mask}.cir"
                if not deck.is_file():
                    raise RuntimeError(f"registered combination deck missing: {deck}")
                case = run_physical(point, mask, deck)
                cases[mask] = case
                state.setdefault("points", {}).setdefault(pid, {"point_id": pid, "changes": point["changes"], "status": "PARTIAL", "cases": {}})["cases"][mask] = case
                if case["run_id"] not in state["run_order"]:
                    state["run_order"].append(case["run_id"])
                save_state(state)
            changes_json = json.dumps(point["changes"], separators=(",", ":"))
            result_path = EXP / "screening/results" / f"{pid}.json"
            if not result_path.is_file():
                command = [sys.executable, str(EXP / "analysis/combination_analysis.py"), "--point-id", pid, "--changes", changes_json, "--n2", str(REPO / cases["0011"]["raw_path"]), "--n3", str(REPO / cases["0111"]["raw_path"])]
                completed = subprocess.run(command, cwd=REPO, check=False)
                if completed.returncode != 0 or not result_path.is_file():
                    raise RuntimeError(f"combination raw analysis failed: {pid}")
            result = json.loads(result_path.read_text(encoding="utf-8"))
            expected = {mask: cases[mask]["raw_sha256"] for mask in MASKS}
            actual = {"0011": result.get("n2", {}).get("raw_sha256"), "0111": result.get("n3", {}).get("raw_sha256")}
            if expected != actual:
                raise RuntimeError(f"combination result/raw hash binding failed: {pid}")
            state["points"][pid] = {"point_id": pid, "changes": point["changes"], "status": "COMPLETE", "candidate_class": result.get("candidate_class"), "cases": cases, "result_path": rel(result_path)}
            save_state(state)
        write_table(state, matrix)
        if result.get("candidate_class") == "S":
            candidate_path = EXP / "screening/CANDIDATE_FOUND.json"
            if not candidate_path.is_file():
                write_json(candidate_path, {"schema": "bvm-qb-two-parameter-combination-candidate-v1", "experiment_id": EXP.name, "created_at_local": now(), "point_id": pid, "changes": point["changes"], "screening_result": rel(EXP / "screening/results" / f"{pid}.json"), "action": "stop unstarted combinations and validate only 0001/1111"})
            state["candidate_point_id"] = pid
            save_state(state)
            completed = subprocess.run([sys.executable, str(EXP / "analysis/run_candidate_validation.py")], cwd=REPO, check=False)
            summary_path = EXP / "screening/validation_summary.json"
            if completed.returncode not in (0, 1) or not summary_path.is_file():
                raise RuntimeError("candidate validation execution failed without retry")
            state["validation"] = json.loads(summary_path.read_text(encoding="utf-8"))
            if state["validation"].get("classification") == "FULL_POPULATION_1_2_3_4_CANDIDATE":
                return finalize(state, matrix, "FULL_POPULATION_1_2_3_4_CANDIDATE", "DIRECT_2_TO_3_COMBINATION_CANDIDATE validated; CHAIN_CLOSURE_CANDIDATE_FOUND")
            return finalize(state, matrix, "DIRECT_2_TO_3_FOUND / FULL_POPULATION_VALIDATION_FAILED", "direct 2/3 found but full population validation failed; stop for scientific review")
    results = [json.loads((EXP / "screening/results" / f"{point['point_id']}.json").read_text(encoding="utf-8")) for point in matrix["points"] if (EXP / "screening/results" / f"{point['point_id']}.json").is_file()]
    near_direct = [result["point_id"] for result in results if result.get("candidate_class") == "A"]
    state["near_direct_candidates"] = near_direct
    state["strongest_near_direct_candidate"] = near_direct[0] if near_direct else None
    reason = "NO_DIRECT_2_TO_3_TWO_PARAMETER_COMBINATION"
    if near_direct:
        reason += "; near-direct candidates in registered order: " + ", ".join(near_direct)
    return finalize(state, matrix, "NO_DIRECT_2_TO_3_TWO_PARAMETER_COMBINATION", reason)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"COMBINATION BLOCKED: {exc}", file=sys.stderr)
        raise
