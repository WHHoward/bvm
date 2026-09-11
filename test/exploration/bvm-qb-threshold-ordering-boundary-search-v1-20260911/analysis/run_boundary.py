#!/usr/bin/env python3
"""Execute the two registered threshold-ordering midpoint pairs."""

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
MATRIX = EXP / "boundary/BOUNDARY_MATRIX.json"
PREFLIGHT = EXP / "analysis/preflight.json"
STATE = EXP / "boundary/boundary_state.json"
RESULT_DIR = EXP / "boundary/results"
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
    allowed = {f"{prefix}/PREFLIGHT.md", f"{prefix}/SOURCE_MANIFEST.json", f"{prefix}/analysis/preflight.json", f"{prefix}/boundary/BOUNDARY_MATRIX.json", f"{prefix}/boundary/BOUNDARY_TABLE.md"}
    distance = int(subprocess.check_output(["git", "rev-list", "--count", f"{sealed}..{current}"], cwd=REPO, text=True).strip())
    valid = distance == 1 and changed in (allowed, allowed - {f"{prefix}/boundary/BOUNDARY_TABLE.md"})
    return {"status": "PASS" if valid else "FAIL", "head": current, "relation": "PREFLIGHT_SEAL_COMMIT" if valid else "UNEXPECTED", "changed_paths": sorted(changed), "commit_distance": distance}


def load_gate() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    preflight = json.loads(PREFLIGHT.read_text(encoding="utf-8"))
    matrix = json.loads(MATRIX.read_text(encoding="utf-8"))
    if preflight.get("status") != "PASS" or matrix.get("logical_midpoint_count") != 2 or matrix.get("logical_case_count") != 4:
        raise RuntimeError("boundary preflight or matrix is not PASS")
    if preflight.get("physical_solve_count_before_preflight") != 0:
        raise RuntimeError("boundary preflight has nonzero prior solve count")
    if sha256(MATRIX) != preflight.get("matrix_sha256") or sha256(EXP / "SOURCE_MANIFEST.json") != preflight.get("source_manifest_sha256"):
        raise RuntimeError("boundary matrix/source manifest hash mismatch")
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


def run_case(point: dict[str, Any], mask: str) -> dict[str, Any]:
    run_id = f"BOUNDARY_{point['point_id']}_{mask}"
    run_dir = EXP / "runs" / run_id
    deck_source = REPO / point["cases"][mask]["path"]
    if run_dir.exists():
        required = [run_dir / name for name in ("deck.cir", "raw.csv", "metadata.json", "run.log")]
        if not all(path.is_file() for path in required):
            raise RuntimeError(f"partial run exists; refusing overwrite: {run_dir}")
        metadata = json.loads((run_dir / "metadata.json").read_text(encoding="utf-8"))
        if metadata.get("point_id") != point["point_id"] or metadata.get("mask") != mask or metadata.get("execution_status") != "RUN_PASS":
            raise RuntimeError(f"existing run mismatch: {run_dir}")
        return {"run_id": run_id, "mask": mask, "source_kind": "NEW_PHYSICAL_SOLVE_ALREADY_COMPLETE", "physical_solve_this_experiment": True, "raw_path": rel(run_dir / "raw.csv"), "deck_path": rel(run_dir / "deck.cir"), "metadata_path": rel(run_dir / "metadata.json"), "log_path": rel(run_dir / "run.log"), "raw_sha256": sha256(run_dir / "raw.csv"), "deck_sha256": sha256(run_dir / "deck.cir"), "raw_bytes": (run_dir / "raw.csv").stat().st_size, "raw_summary": raw_summary(run_dir / "raw.csv")}
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
    metadata = {"schema": "bvm-qb-threshold-ordering-boundary-run-metadata-v1", "experiment_id": EXP.name, "run_id": run_id, "point_id": point["point_id"], "changes": point["changes"], "mask": mask, "topology": "BVM1..4 -> COMMON_SL -> 8-JJ JSL -> QB -> six-stage JTL -> R_TERM", "stimulus": {"amplitude_uA": 100.0, "tran": ".tran 0.1p 200p", "history": "IDLE/WRITE0/ZERO_STATE_READ_CONTROL/IDLE/WRITE1/SETTLE/FINAL_READ/TAIL"}, "started_at_local": started, "finished_at_local": finished, "git_head_before_run": head(), "command": command, "solver": {"path": rel(SOLVER), "sha256": sha256(SOLVER), "version": subprocess.check_output([str(SOLVER), "--version"], cwd=REPO, text=True)}, "deck_source": {"path": rel(deck_source), "sha256": sha256(deck_source)}, "artifacts": {"deck": {"path": rel(deck), "sha256": sha256(deck), "bytes": deck.stat().st_size}, "raw": {"path": rel(raw), "exists": raw_exists, "sha256": sha256(raw) if raw_exists else None, "bytes": raw.stat().st_size if raw_exists else None}, "log": {"path": rel(log), "sha256": sha256(log), "bytes": log.stat().st_size}}, "exit_code": completed.returncode, "execution_status": "RUN_PASS" if completed.returncode == 0 and raw_exists else "RUN_FAIL", "physical_solve_this_experiment": True, "raw_immutable": True, "parameter_tuning": False, "scientific_analysis_performed": False, "raw_summary": raw_summary(raw)}
    with metadata_path.open("x", encoding="utf-8") as stream:
        json.dump(metadata, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    if metadata["execution_status"] != "RUN_PASS":
        raise RuntimeError(f"solver failed without retry: {run_id}")
    return {"run_id": run_id, "mask": mask, "source_kind": "NEW_PHYSICAL_SOLVE", "physical_solve_this_experiment": True, "raw_path": rel(raw), "deck_path": rel(deck), "metadata_path": rel(metadata_path), "log_path": rel(log), "raw_sha256": sha256(raw), "deck_sha256": sha256(deck), "raw_bytes": raw.stat().st_size, "raw_summary": raw_summary(raw)}


def analyse(point: dict[str, Any], cases: dict[str, Any]) -> dict[str, Any]:
    output = RESULT_DIR / f"{point['point_id']}.json"
    expected_hashes = {mask: cases[mask]["raw_sha256"] for mask in MASKS}
    if not output.is_file():
        command = [sys.executable, str(EXP / "analysis/threshold_analysis.py"), "--point-id", point["point_id"], "--changes", json.dumps(point["changes"], separators=(",", ":")), "--n2", str(REPO / cases["0011"]["raw_path"]), "--n3", str(REPO / cases["0111"]["raw_path"])]
        completed = subprocess.run(command, cwd=REPO, check=False)
        if completed.returncode != 0 or not output.is_file():
            raise RuntimeError(f"threshold analysis failed: {point['point_id']}")
    result = json.loads(output.read_text(encoding="utf-8"))
    actual = {"0011": result.get("n2", {}).get("raw_sha256"), "0111": result.get("n3", {}).get("raw_sha256")}
    if actual != expected_hashes:
        raise RuntimeError(f"threshold result/raw binding failed: {point['point_id']}")
    return result


def state_template(preflight: dict[str, Any], relation: dict[str, Any]) -> dict[str, Any]:
    return {"schema": "bvm-qb-threshold-ordering-boundary-state-v1", "experiment_id": EXP.name, "created_at_local": now(), "updated_at_local": now(), "status": "RUNNING", "final_marker": None, "preflight_head": preflight["head_at_preflight"], "execution_head": relation["head"], "logical_midpoint_count": 2, "logical_case_count": 4, "maximum_new_physical_solve_count": 4, "points": {}, "run_order": [], "early_stop_point": None, "outcome": None}


def save_state(state: dict[str, Any]) -> None:
    state["updated_at_local"] = now()
    write_json(STATE, state)


def write_tables(state: dict[str, Any], matrix: dict[str, Any]) -> None:
    rows = []
    for point in matrix["points"]:
        record = state.get("points", {}).get(point["point_id"])
        row = {"axis": "L2" if "L2_pH" in point["changes"] else "IBias", "point_id": point["point_id"], "changes": point["changes"], "execution_status": "NOT_RUN", "control_status": None, "N2_classification": None, "N3_classification": None, "N2_count": None, "N3_count": None, "threshold_ordering_outcome": None, "N2_BJ1_1_ps": None, "N2_BJ2_1_ps": None, "N2_BJ1_2_ps": None, "N2_BJ2_2_ps": None, "N2_JTL6_2_ps": None, "N2_terminal_2_ps": None, "N3_BJ1_3_ps": None, "N3_BJ2_3_ps": None, "N3_BJ1_4_ps": None, "N3_BJ2_4_ps": None, "N3_JTL6_4_ps": None, "N3_terminal_4_ps": None, "N3_max_BJ1_turns": None, "N3_final_BJ1_turns": None, "N3_max_BJ2_turns": None, "N3_final_BJ2_turns": None, "post_third_peak_I_L1_A": None, "integral_118_121_V_s": None, "integral_121_124_V_s": None, "integral_124_128_V_s": None, "source_110_121_A_s": None, "source_121_124_A_s": None, "notes": []}
        if record and record.get("status") == "COMPLETE":
            result = json.loads((RESULT_DIR / f"{point['point_id']}.json").read_text(encoding="utf-8"))
            n2, n3 = result["n2"], result["n3"]
            n2e, n3e = n2["evidence"], n3["evidence"]
            n2c, n3c = n2["classification"], n3["classification"]
            n2p = n2e["terminal"].get("matched_candidate_pulses", n2e["terminal"].get("pulses", []))
            n3p = n3e["terminal"].get("matched_candidate_pulses", n3e["terminal"].get("pulses", []))
            def tm(evidence: dict[str, Any], track: str, ordinal: int) -> float | None:
                return evidence["phase_navigation"][track]["threshold_navigation_times_ps"].get(f"{({1: 0.5, 2: 1.5, 3: 2.5, 4: 3.5}[ordinal]):g}")
            row.update({"execution_status": "COMPLETE", "control_status": "CLEAN" if n2c["control_status"] == n3c["control_status"] == "CLEAN" else "CONTROL_CONTAMINATED", "N2_classification": n2c["classification"], "N3_classification": n3c["classification"], "N2_count": n2e["complete_response_candidate_count"], "N3_count": n3e["complete_response_candidate_count"], "threshold_ordering_outcome": result.get("threshold_ordering", {}).get("outcome"), "N2_BJ1_1_ps": tm(n2e, "BJ1", 1), "N2_BJ2_1_ps": tm(n2e, "BJ2", 1), "N2_BJ1_2_ps": tm(n2e, "BJ1", 2), "N2_BJ2_2_ps": tm(n2e, "BJ2", 2), "N2_JTL6_2_ps": tm(n2e, "JTL6", 2), "N2_terminal_2_ps": n2p[1]["peak_time_ps"] if len(n2p) >= 2 else None, "N3_BJ1_3_ps": tm(n3e, "BJ1", 3), "N3_BJ2_3_ps": tm(n3e, "BJ2", 3), "N3_BJ1_4_ps": tm(n3e, "BJ1", 4), "N3_BJ2_4_ps": tm(n3e, "BJ2", 4), "N3_JTL6_4_ps": tm(n3e, "JTL6", 4), "N3_terminal_4_ps": n3p[3]["peak_time_ps"] if len(n3p) >= 4 else None, "N3_max_BJ1_turns": n3e["internal_reset"]["BJ1_max_relative_turns"], "N3_final_BJ1_turns": n3e["internal_reset"]["BJ1_final_relative_turns"], "N3_max_BJ2_turns": n3e["internal_reset"]["BJ2_max_relative_turns"], "N3_final_BJ2_turns": n3e["internal_reset"]["BJ2_final_relative_turns"], "post_third_peak_I_L1_A": n3e["internal_reset"]["peak_I_L1_A"], "integral_118_121_V_s": n3e["internal_reset"]["integral_118_121_V_s"], "integral_121_124_V_s": n3e["internal_reset"]["integral_121_124_V_s"], "integral_124_128_V_s": n3e["internal_reset"]["integral_124_128_V_s"], "source_110_121_A_s": n3e["source_feedback"]["I_B_JSL8"]["110_121"]["signed_area_A_s"], "source_121_124_A_s": n3e["source_feedback"]["I_B_JSL8"]["121_124"]["signed_area_A_s"], "notes": result.get("notes", []) + result.get("threshold_ordering", {}).get("outcome", "")})
        rows.append(row)
    write_json(EXP / "boundary/BOUNDARY_RESULTS.json", {"schema": "bvm-qb-threshold-ordering-boundary-results-v1", "experiment_id": EXP.name, "updated_at_local": now(), "rows": rows, "not_sfq_count": True, "phase_semantics": "raw radians; rad/(2*pi) navigation only", "control_semantics": "complete downstream propagation in 70-110 ps history windows only"})
    lines = ["# QB threshold-ordering boundary results", "", "| axis | point | changes | control | N2 | N3 | midpoint outcome | N2 BJ1_2 ps | N3 BJ1_3 ps | N3 BJ1_4 ps | N3 JTL6_4 ps | N3 terminal_4 ps | source 110-121 A_s | source 121-124 A_s |", "|---|---|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|"]
    for row in rows:
        lines.append("| {axis} | {point_id} | {changes} | {history_control_status} | {N2_classification} ({N2_count}) | {N3_classification} ({N3_count}) | {threshold_ordering_outcome} | {N2_BJ1_2_ps} | {N3_BJ1_3_ps} | {N3_BJ1_4_ps} | {N3_JTL6_4_ps} | {N3_terminal_4_ps} | {source_110_121_A_s} | {source_121_124_A_s} |".format(axis=row["axis"], point_id=row["point_id"], changes=row["changes"], history_control_status=row["history_control_status"] or "", N2_classification=row["N2_classification"] or "", N2_count=row["N2_count"] if row["N2_count"] is not None else "", N3_classification=row["N3_classification"] or "", N3_count=row["N3_count"] if row["N3_count"] is not None else "", threshold_ordering_outcome=row["threshold_ordering_outcome"] or "", N2_BJ1_2_ps=row["N2_BJ1_2_ps"] or "", N3_BJ1_3_ps=row["N3_BJ1_3_ps"] or "", N3_BJ1_4_ps=row["N3_BJ1_4_ps"] or "", N3_JTL6_4_ps=row["N3_JTL6_4_ps"] or "", N3_terminal_4_ps=row["N3_terminal_4_ps"] or "", source_110_121_A_s=row["source_110_121_A_s"] or "", source_121_124_A_s=row["source_121_124_A_s"] or ""))
    lines.extend(["", "Endpoint results are bounded context only. No exact continuous threshold is inferred from three points. P values are raw radians; displayed turns are navigation, not SFQ counts.", ""])
    (EXP / "boundary/BOUNDARY_RESULTS.md").write_text("\n".join(lines), encoding="utf-8")


def write_execution(state: dict[str, Any]) -> None:
    runs = list(state.get("run_order", []))
    complete = sum(value.get("status") == "COMPLETE" for value in state.get("points", {}).values())
    record = {"schema": "bvm-qb-threshold-ordering-boundary-execution-v1", "experiment_id": EXP.name, "created_at_local": now(), "status": "PASS", "logical_midpoint_count": 2, "logical_case_count": 4, "actual_started_midpoint_count": complete, "actual_new_physical_solve_count": len(runs), "reused_endpoint_reference_count": 10, "validation_new_physical_solve_count": 0, "unauthorized_extra_solve_count": 0, "run_order": runs, "early_stop_point": state.get("early_stop_point"), "outcome": state.get("outcome"), "maximum_new_physical_solve_count": 4, "no_retry_performed": True, "no_replay": True, "no_passive_capture": True, "no_source_scaling": True, "no_n1_n4": True, "no_timestep_change": True, "raw_files_modified": 0, "scientific_analysis_performed": False}
    write_json(SUMMARY, record)


def main() -> int:
    preflight, matrix, relation = load_gate()
    state = json.loads(STATE.read_text(encoding="utf-8")) if STATE.is_file() else state_template(preflight, relation)
    if state.get("final_marker"):
        write_execution(state)
        return 0
    save_state(state)
    for point in matrix["points"]:
        pid = point["point_id"]
        if state.get("points", {}).get(pid, {}).get("status") == "COMPLETE":
            result = json.loads((RESULT_DIR / f"{pid}.json").read_text(encoding="utf-8"))
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
            state["points"][pid] = {"point_id": pid, "changes": point["changes"], "status": "COMPLETE", "candidate_class": result.get("candidate_class"), "threshold_ordering": result.get("threshold_ordering"), "cases": cases, "result_path": rel(RESULT_DIR / f"{pid}.json")}
            save_state(state)
        write_tables(state, matrix)
        if result.get("threshold_ordering", {}).get("outcome") == "DIRECT_2_TO_3_THRESHOLD_WINDOW_FOUND":
            state["early_stop_point"] = pid
            state["outcome"] = "DIRECT_2_TO_3_THRESHOLD_WINDOW_FOUND"
            state["status"] = "DIRECT_2_TO_3_THRESHOLD_WINDOW_FOUND"
            save_state(state)
            write_tables(state, matrix)
            state["final_marker"] = "EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW"
            save_state(state)
            write_execution(state)
            print(json.dumps({"status": state["status"], "final_marker": state["final_marker"], "new_physical_solves": len(state["run_order"])}, ensure_ascii=False, indent=2))
            return 0
    state["outcome"] = "NO_DIRECT_2_TO_3_TWO_PARAMETER_COMBINATION" if not any(json.loads(path.read_text(encoding="utf-8")).get("threshold_ordering", {}).get("outcome") == "DIRECT_2_TO_3_THRESHOLD_WINDOW_FOUND" for path in RESULT_DIR.glob("*.json")) else state.get("outcome")
    state["status"] = state["outcome"]
    state["final_marker"] = "EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW"
    save_state(state)
    write_tables(state, matrix)
    write_execution(state)
    print(json.dumps({"status": state["status"], "final_marker": state["final_marker"], "new_physical_solves": len(state["run_order"])}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
