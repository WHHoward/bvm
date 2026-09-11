#!/usr/bin/env python3
"""Execute the registered L3 high-side sequence with an H1 early stop."""

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
MATRIX = EXP / "screening/L3_MATRIX.json"
PREFLIGHT = EXP / "analysis/preflight.json"
STATE = EXP / "screening/l3_state.json"
RESULT_DIR = EXP / "screening/results"
SUMMARY = EXP / "qa/execution_summary.json"
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


def head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()


def head_relation(sealed: str) -> dict[str, Any]:
    current = head()
    if current == sealed:
        return {"status": "PASS", "head": current, "relation": "EXACT", "changed_paths": [], "commit_distance": 0}
    changed = set(subprocess.check_output(["git", "diff", "--name-only", f"{sealed}..{current}"], cwd=REPO, text=True).splitlines())
    prefix = EXP.relative_to(REPO).as_posix()
    allowed = {f"{prefix}/PREFLIGHT.md", f"{prefix}/SOURCE_MANIFEST.json", f"{prefix}/analysis/preflight.json", f"{prefix}/screening/L3_MATRIX.json", f"{prefix}/screening/L3_TABLE.md"}
    distance = int(subprocess.check_output(["git", "rev-list", "--count", f"{sealed}..{current}"], cwd=REPO, text=True).strip())
    valid = distance == 1 and changed in (allowed, allowed - {f"{prefix}/screening/L3_TABLE.md"})
    return {"status": "PASS" if valid else "FAIL", "head": current, "relation": "PREFLIGHT_SEAL_COMMIT" if valid else "UNEXPECTED", "changed_paths": sorted(changed), "commit_distance": distance}


def load_gate() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    preflight = json.loads(PREFLIGHT.read_text(encoding="utf-8"))
    matrix = json.loads(MATRIX.read_text(encoding="utf-8"))
    if preflight.get("status") != "PASS" or matrix.get("logical_new_point_count") != 2 or matrix.get("logical_new_case_count") != 4:
        raise RuntimeError("L3 preflight/matrix is not PASS")
    if preflight.get("physical_solve_count_before_preflight") != 0:
        raise RuntimeError("L3 preflight records prior solves")
    if sha256(MATRIX) != preflight.get("matrix_sha256") or sha256(EXP / "SOURCE_MANIFEST.json") != preflight.get("source_manifest_sha256"):
        raise RuntimeError("L3 matrix/source hash mismatch")
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


def result_path(point_id: str) -> Path:
    return RESULT_DIR / f"{point_id}_corrected_v2.json"


def run_case(point: dict[str, Any], mask: str) -> dict[str, Any]:
    run_id = f"L3_{point['point_id']}_{mask}"
    run_dir = EXP / "runs" / run_id
    deck_source = REPO / point["cases"][mask]["path"]
    if run_dir.exists():
        required = [run_dir / name for name in ("deck.cir", "raw.csv", "metadata.json", "run.log")]
        if not all(path.is_file() for path in required):
            raise RuntimeError(f"partial run exists; refusing overwrite: {run_dir}")
        metadata = json.loads((run_dir / "metadata.json").read_text(encoding="utf-8"))
        if metadata.get("point_id") != point["point_id"] or metadata.get("mask") != mask or metadata.get("execution_status") != "RUN_PASS":
            raise RuntimeError(f"existing run identity/status mismatch: {run_dir}")
        return {"run_id": run_id, "mask": mask, "source_kind": "NEW_PHYSICAL_SOLVE_ALREADY_COMPLETE", "physical_solve_this_experiment": True, "raw_path": rel(run_dir / "raw.csv"), "deck_path": rel(run_dir / "deck.cir"), "metadata_path": rel(run_dir / "metadata.json"), "log_path": rel(run_dir / "run.log"), "raw_sha256": sha256(run_dir / "raw.csv"), "deck_sha256": sha256(run_dir / "deck.cir"), "raw_bytes": (run_dir / "raw.csv").stat().st_size, "raw_summary": raw_summary(run_dir / "raw.csv")}
    run_dir.mkdir(parents=True)
    deck, raw, log, metadata_path = run_dir / "deck.cir", run_dir / "raw.csv", run_dir / "run.log", run_dir / "metadata.json"
    shutil.copy2(deck_source, deck)
    command = [str(SOLVER), "-a", "1", "-o", str(raw), str(deck)]
    started = now()
    with log.open("x", encoding="utf-8") as stream:
        completed = subprocess.run(command, cwd=REPO, stdout=stream, stderr=subprocess.STDOUT, check=False)
    finished = now()
    raw_exists = raw.is_file()
    metadata = {"schema": "bvm-qb-l3-highside-run-metadata-v1", "experiment_id": EXP.name, "run_id": run_id, "point_id": point["point_id"], "changes": point["changes"], "mask": mask, "topology": "BVM1..4 -> COMMON_SL -> 8-JJ JSL -> QB -> six-stage JTL -> R_TERM", "stimulus": {"amplitude_uA": 100.0, "tran": ".tran 0.1p 200p", "history": "IDLE/WRITE0/ZERO_STATE_READ_CONTROL/IDLE/WRITE1/SETTLE/FINAL_READ/TAIL"}, "started_at_local": started, "finished_at_local": finished, "git_head_before_run": head(), "command": command, "solver": {"path": rel(SOLVER), "sha256": sha256(SOLVER), "version": subprocess.check_output([str(SOLVER), "--version"], cwd=REPO, text=True)}, "deck_source": {"path": rel(deck_source), "sha256": sha256(deck_source)}, "artifacts": {"deck": {"path": rel(deck), "sha256": sha256(deck), "bytes": deck.stat().st_size}, "raw": {"path": rel(raw), "exists": raw_exists, "sha256": sha256(raw) if raw_exists else None, "bytes": raw.stat().st_size if raw_exists else None}, "log": {"path": rel(log), "sha256": sha256(log), "bytes": log.stat().st_size}}, "exit_code": completed.returncode, "execution_status": "RUN_PASS" if completed.returncode == 0 and raw_exists else "RUN_FAIL", "physical_solve_this_experiment": True, "raw_immutable": True, "parameter_tuning": False, "scientific_analysis_performed": False, "raw_summary": raw_summary(raw)}
    with metadata_path.open("x", encoding="utf-8") as stream:
        json.dump(metadata, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    if metadata["execution_status"] != "RUN_PASS":
        raise RuntimeError(f"solver failed without retry: {run_id}")
    return {"run_id": run_id, "mask": mask, "source_kind": "NEW_PHYSICAL_SOLVE", "physical_solve_this_experiment": True, "raw_path": rel(raw), "deck_path": rel(deck), "metadata_path": rel(metadata_path), "log_path": rel(log), "raw_sha256": sha256(raw), "deck_sha256": sha256(deck), "raw_bytes": raw.stat().st_size, "raw_summary": raw_summary(raw)}


def analyse(point: dict[str, Any], cases: dict[str, Any]) -> dict[str, Any]:
    output = result_path(point["point_id"])
    if not output.is_file():
        command = [sys.executable, str(EXP / "analysis/l3_analysis.py"), "--point-id", point["point_id"], "--changes", json.dumps(point["changes"], separators=(",", ":")), "--n2", str(REPO / cases["0011"]["raw_path"]), "--n3", str(REPO / cases["0111"]["raw_path"])]
        completed = subprocess.run(command, cwd=REPO, check=False)
        if completed.returncode != 0 or not output.is_file():
            raise RuntimeError(f"L3 raw analysis failed: {point['point_id']}")
    result = json.loads(output.read_text(encoding="utf-8"))
    expected = {"0011": cases["0011"]["raw_sha256"], "0111": cases["0111"]["raw_sha256"]}
    actual = {"0011": result.get("n2", {}).get("raw_sha256"), "0111": result.get("n3", {}).get("raw_sha256")}
    if actual != expected:
        raise RuntimeError(f"L3 result/raw hash binding failed: {point['point_id']}")
    return result


def state_template(preflight: dict[str, Any], relation: dict[str, Any]) -> dict[str, Any]:
    return {"schema": "bvm-qb-l3-highside-state-v1", "experiment_id": EXP.name, "created_at_local": now(), "updated_at_local": now(), "status": "RUNNING", "final_marker": None, "preflight_head": preflight["head_at_preflight"], "execution_head": relation["head"], "logical_new_point_count": 2, "logical_new_case_count": 4, "maximum_new_screening_solve_count": 4, "points": {}, "run_order": [], "early_stop_point": None, "outcome": None, "validation": None}


def save_state(state: dict[str, Any]) -> None:
    state["updated_at_local"] = now()
    write_json(STATE, state)


def write_table(state: dict[str, Any], matrix: dict[str, Any]) -> None:
    rows: list[dict[str, Any]] = [{"L3_pH": 1.6, "point_id": "REFERENCE_L3_1p6", "execution_status": "IMMUTABLE_REFERENCE", "control_status": "CLEAN", "N2_count": 2, "N3_count": 4, "N2_BJ1_2_ps": None, "N3_BJ1_4_ps": None, "N3_BJ2_4_ps": None, "N3_JTL6_4_ps": None, "N3_terminal_4_ps": None, "candidate_class": "REFERENCE", "source_110_121_A_s": None, "source_121_124_A_s": None, "notes": ["L3=1.6 reference; reused immutable raw"]}]
    for point in matrix["points"]:
        record = state.get("points", {}).get(point["point_id"])
        row = {"L3_pH": point["changes"]["L3_pH"], "point_id": point["point_id"], "execution_status": "NOT_RUN", "control_status": None, "N2_count": None, "N3_count": None, "N2_BJ1_2_ps": None, "N3_BJ1_4_ps": None, "N3_BJ2_4_ps": None, "N3_JTL6_4_ps": None, "N3_terminal_4_ps": None, "candidate_class": None, "source_110_121_A_s": None, "source_121_124_A_s": None, "notes": []}
        if record and record.get("status") == "COMPLETE" and result_path(point["point_id"]).is_file():
            result = json.loads(result_path(point["point_id"]).read_text(encoding="utf-8"))
            n2, n3 = result["n2"], result["n3"]
            n2e, n3e = n2["evidence"], n3["evidence"]
            def tm(evidence: dict[str, Any], track: str, ordinal: int) -> float | None:
                return evidence["phase_navigation"][track]["threshold_navigation_times_ps"].get(f"{({1: 0.5, 2: 1.5, 3: 2.5, 4: 3.5}[ordinal]):g}")
            n3p = n3e["terminal"].get("matched_candidate_pulses", n3e["terminal"].get("pulses", []))
            row.update({"execution_status": "COMPLETE", "control_status": "CLEAN" if n2["classification"]["control_status"] == n3["classification"]["control_status"] == "CLEAN" else "CONTROL_CONTAMINATED", "N2_count": n2e["complete_response_candidate_count"], "N3_count": n3e["complete_response_candidate_count"], "N2_BJ1_2_ps": tm(n2e, "BJ1", 2), "N3_BJ1_4_ps": tm(n3e, "BJ1", 4), "N3_BJ2_4_ps": tm(n3e, "BJ2", 4), "N3_JTL6_4_ps": tm(n3e, "JTL6", 4), "N3_terminal_4_ps": n3p[3]["peak_time_ps"] if len(n3p) >= 4 else None, "candidate_class": result.get("candidate_class"), "source_110_121_A_s": n3e["source_feedback"]["I_B_JSL8"]["110_121"]["signed_area_A_s"], "source_121_124_A_s": n3e["source_feedback"]["I_B_JSL8"]["121_124"]["signed_area_A_s"], "notes": result.get("notes", []) + result.get("n3", {}).get("classification", {}).get("fourth_diagnostics", {}).get("notes", [])})
        rows.append(row)
    write_json(EXP / "screening/L3_RESULTS.json", {"schema": "bvm-qb-l3-highside-results-v1", "experiment_id": EXP.name, "updated_at_local": now(), "rows": rows, "phase_navigation_only": True, "not_sfq_count": True})
    lines = ["# L3 highside selective-window results", "", "| L3 pH | status | control | N2 | N3 | N2 BJ1_2 ps | N3 BJ1_4 ps | N3 BJ2_4 ps | N3 JTL6_4 ps | N3 terminal_4 ps | class | source 110-121 A_s | source 121-124 A_s |", "|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|"]
    for row in rows:
        lines.append("| {L3_pH} | {execution_status} | {control_status} | {N2_count} | {N3_count} | {N2_BJ1_2_ps} | {N3_BJ1_4_ps} | {N3_BJ2_4_ps} | {N3_JTL6_4_ps} | {N3_terminal_4_ps} | {candidate_class} | {source_110_121_A_s} | {source_121_124_A_s} |".format(**{key: "" if value is None else value for key, value in row.items()}))
    lines.extend(["", "L3=1.6 is immutable reference. No exact optimum or continuous boundary is inferred from the three tested values.", ""])
    (EXP / "screening/L3_RESULTS.md").write_text("\n".join(lines), encoding="utf-8")


def write_execution(state: dict[str, Any]) -> None:
    runs = list(state.get("run_order", []))
    complete = sum(value.get("status") == "COMPLETE" for value in state.get("points", {}).values())
    write_json(SUMMARY, {"schema": "bvm-qb-l3-highside-execution-v1", "experiment_id": EXP.name, "created_at_local": now(), "status": "PASS", "logical_new_point_count": 2, "logical_new_case_count": 4, "actual_started_point_count": complete, "actual_new_physical_solve_count": len(runs), "reference_l3_1p6_raw_count": 2, "validation_new_physical_solve_count": 0, "unauthorized_extra_solve_count": 0, "run_order": runs, "early_stop_point": state.get("early_stop_point"), "outcome": state.get("outcome"), "maximum_new_screening_solve_count": 4, "maximum_total_new_solve_count_if_later_validation_authorized": 6, "no_retry_performed": True, "no_replay": True, "no_passive_capture": True, "no_source_scaling": True, "no_jtl_parameter_change": True, "no_timestep_change": True, "no_n1_n4": True, "raw_files_modified": 0, "scientific_analysis_performed": False})


def finalize(state: dict[str, Any], matrix: dict[str, Any], outcome: str, reason: str) -> int:
    state["outcome"] = outcome
    state["status"] = outcome
    state["final_marker"] = "EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW"
    state["early_stop_point"] = reason
    save_state(state)
    write_table(state, matrix)
    write_execution(state)
    print(json.dumps({"status": outcome, "final_marker": state["final_marker"], "reason": reason, "new_physical_solves": len(state["run_order"])}, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    preflight, matrix, relation = load_gate()
    state = json.loads(STATE.read_text(encoding="utf-8")) if STATE.is_file() else state_template(preflight, relation)
    if state.get("final_marker") and all(result_path(point["point_id"]).is_file() for point in matrix["points"] if state.get("points", {}).get(point["point_id"], {}).get("status") == "COMPLETE"):
        write_table(state, matrix)
        write_execution(state)
        return 0
    save_state(state)
    for point in matrix["points"]:
        pid = point["point_id"]
        if state.get("points", {}).get(pid, {}).get("status") == "COMPLETE" and result_path(pid).is_file():
            result = json.loads(result_path(pid).read_text(encoding="utf-8"))
        else:
            cases: dict[str, Any] = {}
            for mask in MASKS:
                case = run_case(point, mask)
                cases[mask] = case
                state.setdefault("points", {}).setdefault(pid, {"point_id": pid, "changes": point["changes"], "status": "PARTIAL", "cases": {}})["cases"][mask] = case
                if case["run_id"] not in state["run_order"]:
                    state["run_order"].append(case["run_id"])
                save_state(state)
            result = analyse(point, cases)
            state["points"][pid] = {"point_id": pid, "changes": point["changes"], "status": "COMPLETE", "candidate_class": result.get("candidate_class"), "cases": cases, "result_path": rel(result_path(pid))}
            save_state(state)
        write_table(state, matrix)
        if result.get("candidate_class") == "S":
            return finalize(state, matrix, "DIRECT_2_TO_3_L3_CANDIDATE", f"{pid} clean 2/3 found; stop before unstarted L3 points and reserve validation for later authorization")
        if pid.startswith("H1"):
            continue
    results = [json.loads(result_path(point["point_id"]).read_text(encoding="utf-8")) for point in matrix["points"] if result_path(point["point_id"]).is_file()]
    classes = [result.get("candidate_class") for result in results]
    if "A" in classes:
        outcome = "L3_HIGHSIDE_SELECTIVE_EFFECT_OBSERVED"
    elif "C" in classes or "D" in classes:
        outcome = "L3_HIGHSIDE_UPPER_BOUNDARY_REACHED"
    else:
        outcome = "L3_HIGHSIDE_NO_SELECTIVE_WINDOW_IN_TESTED_RANGE"
    return finalize(state, matrix, outcome, "H1 and H2 completed; stop without extra L3 values")


if __name__ == "__main__":
    raise SystemExit(main())
