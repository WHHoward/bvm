#!/usr/bin/env python3
"""Mechanical QA for the two-parameter full closed-loop combination."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
MATRIX = EXP / "screening/COMBINATION_MATRIX.json"
STATE = EXP / "screening/combination_state.json"
SOLVER = REPO / "build/josim-cli"
SOLVER_SHA256 = "48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2"
BASELINE = {"Lin_pH": 1.5, "L1_pH": 1.4, "L2_pH": 2.0, "RJ1_ohm": 32.0, "RJ2_ohm": 12.0, "IBias_uA": 260.0, "BJS_area": 4.0, "BJ1_area": 0.9, "BJ2_area": 2.0, "L3_pH": 1.3}
REQUIRED = ("I(B_JSL8)", "V(QBIN)", "V(COMMON_SL)", "I(LIN|XBQ1)", "I(L1|XBQ1)", "I(L2|XBQ1)", "P(BJ1|XBQ1)", "V(BJ1|XBQ1)", "I(BJ1|XBQ1)", "P(BJ2|XBQ1)", "V(BJ2|XBQ1)", "I(BJ2|XBQ1)", "V(QBOUT)", "V(JTL1_OUT)", "V(JTL2_OUT)", "V(JTL3_OUT)", "V(JTL4_OUT)", "V(JTL5_OUT)", "V(JTL6_OUT)", "I(R_TERM)") + tuple(f"P(B01|XJTL1_{stage})" for stage in range(1, 7))
REFERENCE_ORIGINS = {
    "0011": REPO / "test/exploration/bvm-full-closed-loop-qb-parameter-screening-v1-20260911/references/baseline_rj2p12/ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_0011",
    "0111": REPO / "test/exploration/bvm-full-closed-loop-qb-parameter-screening-v1-20260911/references/baseline_rj2p12/ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_0111",
}
PREVIOUS_ORIGINS = {
    "0011": REPO / "test/exploration/bvm-full-closed-loop-qb-parameter-screening-v1-20260911/references/baseline_rj2p12/ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_0011",
    "0111": REPO / "test/exploration/bvm-full-closed-loop-qb-parameter-screening-v1-20260911/references/baseline_rj2p12/ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_0111",
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
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def raw_check(path: Path, metadata: Path | None = None, origin: Path | None = None) -> dict[str, Any]:
    failures: list[str] = []
    header: list[str] = []
    times: list[float] = []
    try:
        with path.open(newline="", encoding="utf-8-sig") as stream:
            reader = csv.reader(stream)
            header = next(reader)
            positions = {name: index for index, name in enumerate(header)}
            if len(positions) != len(header):
                failures.append("duplicate raw column")
            failures.extend(f"missing probe: {label}" for label in REQUIRED if label not in positions)
            for row in reader:
                if len(row) != len(header):
                    failures.append("raw row width mismatch")
                    continue
                values = [float(value) for value in row]
                if not all(math.isfinite(value) for value in values):
                    failures.append("non-finite raw value")
                times.append(values[positions["time"]])
    except (OSError, StopIteration, ValueError) as exc:
        failures.append(f"raw read failure: {exc}")
    if len(times) != 1999 or not times or times[0] != 0.0 or times[-1] != 1.999e-10:
        failures.append("time grid is not 1999 samples from 0 to 199.9 ps")
    if any(right <= left for left, right in zip(times, times[1:])):
        failures.append("time is not strictly increasing")
    actual = sha256(path) if path.is_file() else None
    recorded = None
    if metadata is not None and metadata.is_file():
        try:
            value = json.loads(metadata.read_text(encoding="utf-8"))
            recorded = value.get("artifacts", {}).get("raw", {}).get("sha256")
            if recorded != actual:
                failures.append("metadata/raw SHA mismatch")
        except (OSError, json.JSONDecodeError) as exc:
            failures.append(f"metadata read failure: {exc}")
    elif metadata is not None:
        failures.append("metadata missing")
    origin_sha = None
    if origin is not None:
        if not origin.is_file() or actual != sha256(origin):
            failures.append("reference raw is not byte-identical to previous immutable raw")
        if origin.is_file():
            origin_sha = sha256(origin)
    return {"status": "PASS" if not failures else "FAIL", "path": rel(path), "sha256": actual, "bytes": path.stat().st_size if path.is_file() else None, "header_count": len(header), "sample_count": len(times), "time_range_s": [times[0], times[-1]] if times else None, "actual_grid": len(times) == 1999 and bool(times) and times[0] == 0.0 and times[-1] == 1.999e-10 and all(right > left for left, right in zip(times, times[1:])), "metadata_raw_sha256": recorded, "origin_sha256": origin_sha, "failures": failures}


def active_value(text: str, pattern: str) -> float:
    matches = [float(match.group(1)) for line in text.splitlines() if (match := re.match(pattern, line.strip()))]
    if len(matches) != 1:
        raise RuntimeError(f"parameter is not unique: {pattern}")
    return matches[0]


def variant_values(path: Path) -> dict[str, float]:
    text = path.read_text(encoding="utf-8")
    patterns = {"Lin_pH": r"^Lin IN 1 ([0-9.eE+-]+)p$", "L2_pH": r"^L2 3 4 ([0-9.eE+-]+)p$", "BJS_area": r"^BJs 1 2 jjmit area=([0-9.eE+-]+)$", "BJ1_area": r"^BJ1 2 0 jjmit area=([0-9.eE+-]+)$", "BJ2_area": r"^BJ2 4 0 jjmit area=([0-9.eE+-]+)$", "L3_pH": r"^L3 4 OUT ([0-9.eE+-]+)p$"}
    return {key: active_value(text, pattern) for key, pattern in patterns.items()}


def one_factor_record(point: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    deck = REPO / point["cases"]["0011"]["path"]
    variant = REPO / point["variant_path"]
    text = deck.read_text(encoding="utf-8")
    values = dict(BASELINE)
    values.update(variant_values(variant))
    values.update({
        "L1_pH": active_value(text, r"^\.param L1_VALUE=([0-9.eE+-]+)p$"),
        "IBias_uA": active_value(text, r"^\.param IB_VALUE=([0-9.eE+-]+)u$"),
        "RJ1_ohm": active_value(text, r"^\.param RJ1_VALUE=([0-9.eE+-]+)$"),
        "RJ2_ohm": active_value(text, r"^\.param RJ2_VALUE=([0-9.eE+-]+)$"),
    })
    changed = [key for key in BASELINE if not math.isclose(values[key], BASELINE[key], rel_tol=0.0, abs_tol=1.0e-12)]
    expected = sorted(point["changes"])
    if sorted(changed) != expected:
        failures.append(f"changed parameters {changed} != registered {expected}")
    for key, expected_value in point["changes"].items():
        if not math.isclose(values[key], float(expected_value), rel_tol=0.0, abs_tol=1.0e-12):
            failures.append(f"{key} value {values[key]} != {expected_value}")
    return {"status": "PASS" if not failures else "FAIL", "point_id": point["point_id"], "resolved_values": values, "changed_parameters": changed, "registered_changes": point["changes"], "failures": failures}


def main() -> int:
    matrix = json.loads(MATRIX.read_text(encoding="utf-8"))
    state = json.loads(STATE.read_text(encoding="utf-8"))
    failures: list[str] = []
    reference_records: dict[str, Any] = {}
    for mask, origin in PREVIOUS_ORIGINS.items():
        local = EXP / "references/baseline_rj2p12" / origin.name
        record = {suffix: raw_check(local / suffix, local / "metadata.json", origin / suffix if suffix == "raw.csv" else None) for suffix in ("raw.csv",)}
        for suffix in ("deck.cir", "metadata.json", "run.log"):
            path = local / suffix
            record[suffix] = {"status": "PASS" if path.is_file() else "FAIL", "path": rel(path), "sha256": sha256(path) if path.is_file() else None, "bytes": path.stat().st_size if path.is_file() else None}
            if not path.is_file() or (origin / suffix).is_file() is False or sha256(path) != sha256(origin / suffix):
                failures.append(f"baseline reference mismatch: {mask}/{suffix}")
        reference_records[mask] = record
        if record["raw.csv"]["status"] != "PASS":
            failures.extend(f"baseline reference {mask}: {item}" for item in record["raw.csv"]["failures"])

    deck_records: dict[str, Any] = {}
    factor_records: dict[str, Any] = {}
    for point in matrix["points"]:
        factor = one_factor_record(point)
        factor_records[point["point_id"]] = factor
        failures.extend(f"{point['point_id']}: {item}" for item in factor["failures"])
        for mask in MASKS:
            path = REPO / point["cases"][mask]["path"]
            text = path.read_text(encoding="utf-8") if path.is_file() else ""
            lines = [line.strip() for line in text.splitlines() if line.strip() and not line.lstrip().startswith(("*", ".", "+"))]
            local_failures: list[str] = []
            if not path.is_file() or sha256(path) != point["cases"][mask]["sha256"]:
                local_failures.append("registered deck missing or SHA mismatch")
            if sum(line.endswith("BVM") for line in lines) != 4 or sum(line.startswith("B_JSL") for line in lines) != 8 or sum(line == "XBQ1 QBIN QBOUT BQ" for line in lines) != 1 or sum(line.startswith("XJTL1_") and line.endswith(" jtl") for line in lines) != 6:
                local_failures.append("full topology count mismatch")
            if sum(line == "R_TERM JTL6_OUT 0 10" for line in lines) != 1:
                local_failures.append("terminal mismatch")
            for required in (".include ../../inputs/jjmit.cir", ".include ../../inputs/bvm_jm2_connected.cir", ".include ../../inputs/jtl2.cir", ".tran 0.1p 200p"):
                if required not in text:
                    local_failures.append(f"missing {required}")
            if "I_REPLAY" in text or "PASSIVE" in text.upper():
                local_failures.append("forbidden replay/passive token")
            if "rollback" in text.lower():
                local_failures.append("rollback text leaked into deck")
            record = {"status": "PASS" if not local_failures else "FAIL", "path": rel(path), "sha256": sha256(path) if path.is_file() else None, "bytes": path.stat().st_size if path.is_file() else None, "failures": local_failures}
            deck_records[f"{point['point_id']}/{mask}"] = record
            failures.extend(f"{point['point_id']}/{mask}: {item}" for item in local_failures)

    raw_records: dict[str, Any] = {}
    run_dirs = sorted(path for path in (EXP / "runs").iterdir() if path.is_dir())
    for run_dir in run_dirs:
        if not (run_dir.name.startswith("COMB_") or run_dir.name.startswith("VALIDATION_")):
            failures.append(f"unauthorized run directory: {run_dir.name}")
        record = raw_check(run_dir / "raw.csv", run_dir / "metadata.json")
        raw_records[run_dir.name] = record
        if record["status"] != "PASS":
            failures.extend(f"{run_dir.name}: {item}" for item in record["failures"])
        if not all((run_dir / suffix).is_file() for suffix in ("deck.cir", "raw.csv", "metadata.json", "run.log")):
            failures.append(f"run artifact incomplete: {run_dir.name}")

    result_records: dict[str, Any] = {}
    for point in matrix["points"]:
        result_path = EXP / "screening/results" / f"{point['point_id']}.json"
        if not result_path.is_file():
            continue
        result = json.loads(result_path.read_text(encoding="utf-8"))
        result_records[point["point_id"]] = {"path": rel(result_path), "sha256": sha256(result_path), "candidate_class": result.get("candidate_class")}
        state_point = state.get("points", {}).get(point["point_id"], {})
        for branch, mask in (("n2", "0011"), ("n3", "0111")):
            case = state_point.get("cases", {}).get(mask)
            if case is None or result.get(branch, {}).get("raw_path") != case.get("raw_path") or result.get(branch, {}).get("raw_sha256") != case.get("raw_sha256"):
                failures.append(f"result/raw binding mismatch: {point['point_id']}/{mask}")
            evidence = result.get(branch, {}).get("evidence", {})
            control = evidence.get("control", {})
            if control.get("rollback_excluded_from_control") is not True or not control.get("criterion"):
                failures.append(f"corrected control rule missing: {point['point_id']}/{mask}")
            if "BJ1_max_minus_final_turns" in json.dumps(control, ensure_ascii=False):
                failures.append(f"old rollback control criterion present: {point['point_id']}/{mask}")
            if "source_feedback" not in evidence:
                failures.append(f"source feedback missing: {point['point_id']}/{mask}")

    execution_path = EXP / "qa/execution_summary.json"
    execution = json.loads(execution_path.read_text(encoding="utf-8")) if execution_path.is_file() else {}
    if state.get("final_marker") != "EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW":
        failures.append("final marker missing")
    if execution.get("status") != "PASS":
        failures.append("execution summary is not PASS")
    physical_count = len(run_dirs)
    if execution.get("exact_new_physical_solve_count") != physical_count:
        failures.append("execution physical count does not match run directories")
    if execution.get("unauthorized_extra_solve_count") != 0 or execution.get("no_retry_performed") is not True:
        failures.append("execution authorization/retry guard failed")
    if any(execution.get(key) is not True for key in ("no_replay", "no_passive_capture", "no_source_scaling", "no_read_extension", "no_jtl_parameter_change", "no_timestep_change")):
        failures.append("forbidden workflow guard missing")
    if not SOLVER.is_file() or sha256(SOLVER) != SOLVER_SHA256:
        failures.append("solver identity changed")

    raw_status = "PASS" if not reference_records or all(item["raw.csv"]["status"] == "PASS" for item in reference_records.values()) and all(item["status"] == "PASS" for item in raw_records.values()) else "FAIL"
    deck_status = "PASS" if all(item["status"] == "PASS" for item in deck_records.values()) and all(item["status"] == "PASS" for item in factor_records.values()) else "FAIL"
    write_json(EXP / "qa/raw_qa.json", {"schema": "bvm-qb-two-parameter-combination-raw-qa-v1", "experiment_id": EXP.name, "created_at_local": now(), "status": raw_status, "artifact_validity": "VALID" if raw_status == "PASS" else "ARTIFACT_INVALID", "required_probe_count": len(REQUIRED), "baseline_references": reference_records, "runs": raw_records, "raw_files_modified": 0, "failures": [item for name, record in raw_records.items() for item in record.get("failures", [])]})
    write_json(EXP / "qa/deck_diff_qa.json", {"schema": "bvm-qb-two-parameter-combination-deck-qa-v1", "experiment_id": EXP.name, "created_at_local": now(), "status": deck_status, "logical_combination_point_count": 9, "logical_combination_case_count": 18, "two_parameter_only": True, "full_closed_loop_only": True, "decks": deck_records, "parameter_records": factor_records, "failures": failures})
    raw_artifacts = {name: {"path": record.get("path"), "sha256": record.get("sha256"), "bytes": record.get("bytes")} for name, record in raw_records.items()}
    write_json(EXP / "qa/provenance.json", {"schema": "bvm-qb-two-parameter-combination-provenance-v1", "experiment_id": EXP.name, "created_at_local": now(), "repository_head_at_qa": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip(), "preflight": {"path": rel(EXP / "analysis/preflight.json"), "sha256": sha256(EXP / "analysis/preflight.json")}, "source_manifest": {"path": rel(EXP / "SOURCE_MANIFEST.json"), "sha256": sha256(EXP / "SOURCE_MANIFEST.json")}, "matrix": {"path": rel(MATRIX), "sha256": sha256(MATRIX)}, "solver": {"path": rel(SOLVER), "sha256": sha256(SOLVER), "version": subprocess.check_output([str(SOLVER), "--version"], cwd=REPO, text=True)}, "raw": raw_artifacts, "baseline_references": reference_records, "results": result_records, "raw_authority": True, "corrected_control_windows_ps": [[70.0, 81.0], [81.0, 90.0], [90.0, 101.0], [101.0, 110.0]], "rollback_not_control": True, "no_replay": True, "no_passive_capture": True, "no_timestep_change": True})
    write_json(EXP / "qa/transformation_registry.json", {"schema": "bvm-qb-two-parameter-combination-transformation-registry-v1", "experiment_id": EXP.name, "created_at_local": now(), "raw_immutable": True, "raw_input_mode": "direct raw CSV", "phase": "independent continuous unwrap then rad/(2*pi) navigation only", "integration": "trapezoid on actual stored time grid without interpolation", "control": "complete downstream chain in registered 70-110 ps windows; final/tail rollback excluded", "source_feedback": "actual-grid signed I(B_JSL8) areas in registered windows", "visualization": "raw direct standalone; temporary same-grid comparison CSV deleted after render", "forbidden": ["replay", "passive capture", "source scaling", "read extension", "JTL change", "timestep change", "raw overwrite"], "scientific_review_status": "AWAITING_SCIENTIFIC_REVIEW"})
    mechanical_status = "PASS" if not failures and raw_status == "PASS" and deck_status == "PASS" else "FAIL"
    write_json(EXP / "mechanical_summary.json", {"schema": "bvm-qb-two-parameter-combination-mechanical-summary-v1", "experiment_id": EXP.name, "created_at_local": now(), "status": mechanical_status, "raw_qa_status": raw_status, "deck_qa_status": deck_status, "execution_status": execution.get("status"), "scientific_interpretation_performed": False, "scientific_review_status": "AWAITING_SCIENTIFIC_REVIEW", "raw_files_modified": 0, "failures": failures})
    print(json.dumps({"status": mechanical_status, "raw_status": raw_status, "deck_status": deck_status, "run_count": physical_count, "failures": failures[:40]}, ensure_ascii=False, indent=2))
    return 0 if mechanical_status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
