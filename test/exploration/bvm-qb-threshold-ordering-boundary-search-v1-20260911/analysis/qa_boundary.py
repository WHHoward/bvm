#!/usr/bin/env python3
"""Mechanical QA for the two-point threshold-ordering boundary search."""

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
MATRIX = EXP / "boundary/BOUNDARY_MATRIX.json"
STATE = EXP / "boundary/boundary_state.json"
SOLVER = REPO / "build/josim-cli"
SOLVER_SHA256 = "48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2"
MASKS = ("0011", "0111")
REQUIRED = ("I(B_JSL8)", "V(QBIN)", "V(COMMON_SL)", "I(LIN|XBQ1)", "I(L1|XBQ1)", "I(L2|XBQ1)", "P(BJ1|XBQ1)", "V(BJ1|XBQ1)", "I(BJ1|XBQ1)", "P(BJ2|XBQ1)", "V(BJ2|XBQ1)", "I(BJ2|XBQ1)", "V(QBOUT)", "V(JTL1_OUT)", "V(JTL2_OUT)", "V(JTL3_OUT)", "V(JTL4_OUT)", "V(JTL5_OUT)", "V(JTL6_OUT)", "I(R_TERM)") + tuple(f"P(B01|XJTL1_{stage})" for stage in range(1, 7))
ORIGINS = {
    "canonical_baseline/0011": REPO / "test/exploration/bvm-full-closed-loop-qb-parameter-screening-v1-20260911/references/baseline_rj2p12/ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_0011",
    "canonical_baseline/0111": REPO / "test/exploration/bvm-full-closed-loop-qb-parameter-screening-v1-20260911/references/baseline_rj2p12/ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_0111",
    "endpoints/l2_low_l3p16/0011": REPO / "test/exploration/bvm-qb-two-parameter-combination-v1-20260911/runs/COMB_C01_0011",
    "endpoints/l2_low_l3p16/0111": REPO / "test/exploration/bvm-qb-two-parameter-combination-v1-20260911/runs/COMB_C01_0111",
    "endpoints/l2_high_l3p16/0011": REPO / "test/exploration/bvm-full-closed-loop-qb-parameter-screening-v1-20260911/runs/SCREEN_L3_pH_1p6_0011",
    "endpoints/l2_high_l3p16/0111": REPO / "test/exploration/bvm-full-closed-loop-qb-parameter-screening-v1-20260911/runs/SCREEN_L3_pH_1p6_0111",
    "endpoints/ib_low_l3p16/0011": REPO / "test/exploration/bvm-qb-two-parameter-combination-v1-20260911/runs/COMB_C07_0011",
    "endpoints/ib_low_l3p16/0111": REPO / "test/exploration/bvm-qb-two-parameter-combination-v1-20260911/runs/COMB_C07_0111",
    "endpoints/ib_high_l3p16/0011": REPO / "test/exploration/bvm-full-closed-loop-qb-parameter-screening-v1-20260911/runs/SCREEN_L3_pH_1p6_0011",
    "endpoints/ib_high_l3p16/0111": REPO / "test/exploration/bvm-full-closed-loop-qb-parameter-screening-v1-20260911/runs/SCREEN_L3_pH_1p6_0111",
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
                failures.append("duplicate raw columns")
            failures.extend(f"missing probe: {label}" for label in REQUIRED if label not in positions)
            for row in reader:
                if len(row) != len(header):
                    failures.append("row width mismatch")
                    continue
                values = [float(value) for value in row]
                if not all(math.isfinite(value) for value in values):
                    failures.append("nonfinite value")
                times.append(values[positions["time"]])
    except (OSError, StopIteration, ValueError) as exc:
        failures.append(f"raw read failure: {exc}")
    if len(times) != 1999 or not times or times[0] != 0.0 or times[-1] != 1.999e-10:
        failures.append("actual grid is not 1999 samples 0..199.9 ps")
    if any(right <= left for left, right in zip(times, times[1:])):
        failures.append("time not strictly increasing")
    actual = sha256(path) if path.is_file() else None
    recorded = None
    if metadata is not None and metadata.is_file():
        try:
            recorded = json.loads(metadata.read_text(encoding="utf-8")).get("artifacts", {}).get("raw", {}).get("sha256")
            if recorded != actual:
                failures.append("metadata/raw SHA mismatch")
        except (OSError, json.JSONDecodeError) as exc:
            failures.append(f"metadata read failure: {exc}")
    elif metadata is not None:
        failures.append("metadata missing")
    origin_sha = None
    if origin is not None:
        if not origin.is_file() or actual != sha256(origin):
            failures.append("reference is not byte-identical to origin")
        if origin.is_file():
            origin_sha = sha256(origin)
    return {"status": "PASS" if not failures else "FAIL", "path": rel(path), "sha256": actual, "bytes": path.stat().st_size if path.is_file() else None, "header_count": len(header), "sample_count": len(times), "time_range_s": [times[0], times[-1]] if times else None, "actual_grid": len(times) == 1999 and bool(times) and times[0] == 0.0 and times[-1] == 1.999e-10 and all(right > left for left, right in zip(times, times[1:])), "metadata_raw_sha256": recorded, "origin_sha256": origin_sha, "failures": failures}


def active_value(text: str, pattern: str) -> float:
    values = [float(match.group(1)) for line in text.splitlines() if (match := re.match(pattern, line.strip()))]
    if len(values) != 1:
        raise RuntimeError(f"nonunique parameter: {pattern}")
    return values[0]


def variant_values(path: Path) -> dict[str, float]:
    text = path.read_text(encoding="utf-8")
    patterns = {"Lin_pH": r"^Lin IN 1 ([0-9.eE+-]+)p$", "L2_pH": r"^L2 3 4 ([0-9.eE+-]+)p$", "BJS_area": r"^BJs 1 2 jjmit area=([0-9.eE+-]+)$", "BJ1_area": r"^BJ1 2 0 jjmit area=([0-9.eE+-]+)$", "BJ2_area": r"^BJ2 4 0 jjmit area=([0-9.eE+-]+)$", "L3_pH": r"^L3 4 OUT ([0-9.eE+-]+)p$"}
    return {key: active_value(text, pattern) for key, pattern in patterns.items()}


def factor_check(point: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    deck = REPO / point["cases"]["0011"]["path"]
    variant = REPO / point["variant_path"]
    text = deck.read_text(encoding="utf-8")
    values = dict(BASELINE)
    values.update(variant_values(variant))
    values.update({"L1_pH": active_value(text, r"^\.param L1_VALUE=([0-9.eE+-]+)p$"), "IBias_uA": active_value(text, r"^\.param IB_VALUE=([0-9.eE+-]+)u$"), "RJ1_ohm": active_value(text, r"^\.param RJ1_VALUE=([0-9.eE+-]+)$"), "RJ2_ohm": active_value(text, r"^\.param RJ2_VALUE=([0-9.eE+-]+)$")})
    changed = sorted(key for key in BASELINE if not math.isclose(values[key], BASELINE[key], rel_tol=0.0, abs_tol=1.0e-12))
    if changed != sorted(point["changes"]):
        failures.append(f"changed={changed}, expected={sorted(point['changes'])}")
    for key, expected in point["changes"].items():
        if not math.isclose(values[key], float(expected), rel_tol=0.0, abs_tol=1.0e-12):
            failures.append(f"{key}={values[key]} expected {expected}")
    return {"status": "PASS" if not failures else "FAIL", "point_id": point["point_id"], "resolved_values": values, "changed_parameters": changed, "failures": failures}


def main() -> int:
    matrix = json.loads(MATRIX.read_text(encoding="utf-8"))
    state = json.loads(STATE.read_text(encoding="utf-8"))
    failures: list[str] = []
    references: dict[str, Any] = {}
    for key, origin in ORIGINS.items():
        local = EXP / "references" / key
        record = {}
        for name in ("raw.csv", "deck.cir", "metadata.json", "run.log"):
            source = local / name
            origin_file = origin / name
            if name == "raw.csv":
                record[name] = raw_check(source, local / "metadata.json", origin_file)
            else:
                record[name] = {"status": "PASS" if source.is_file() else "FAIL", "path": rel(source), "sha256": sha256(source) if source.is_file() else None, "bytes": source.stat().st_size if source.is_file() else None}
                if not source.is_file() or not origin_file.is_file() or sha256(source) != sha256(origin_file):
                    failures.append(f"reference mismatch {key}/{name}")
        references[key] = record
        if record["raw.csv"]["status"] != "PASS":
            failures.extend(f"{key}: {item}" for item in record["raw.csv"]["failures"])

    decks: dict[str, Any] = {}
    factors: dict[str, Any] = {}
    for point in matrix["points"]:
        factor = factor_check(point)
        factors[point["point_id"]] = factor
        failures.extend(f"{point['point_id']}: {item}" for item in factor["failures"])
        for mask in MASKS:
            case = point["cases"][mask]
            path = REPO / case["path"]
            text = path.read_text(encoding="utf-8") if path.is_file() else ""
            lines = [line.strip() for line in text.splitlines() if line.strip() and not line.lstrip().startswith(("*", ".", "+"))]
            local_failures: list[str] = []
            if not path.is_file() or sha256(path) != case["sha256"]:
                local_failures.append("registered deck missing/SHA mismatch")
            if sum(line.endswith("BVM") for line in lines) != 4 or sum(line.startswith("B_JSL") for line in lines) != 8 or sum(line == "XBQ1 QBIN QBOUT BQ" for line in lines) != 1 or sum(line.startswith("XJTL1_") and line.endswith(" jtl") for line in lines) != 6:
                local_failures.append("full topology count mismatch")
            if sum(line == "R_TERM JTL6_OUT 0 10" for line in lines) != 1:
                local_failures.append("terminal mismatch")
            for token in (".include ../../inputs/jjmit.cir", ".include ../../inputs/bvm_jm2_connected.cir", ".include ../../inputs/jtl2.cir", ".tran 0.1p 200p"):
                if token not in text:
                    local_failures.append(f"missing {token}")
            if "I_REPLAY" in text or "PASSIVE" in text.upper():
                local_failures.append("forbidden replay/passive token")
            decks[f"{point['point_id']}/{mask}"] = {"status": "PASS" if not local_failures else "FAIL", "path": rel(path), "sha256": sha256(path) if path.is_file() else None, "bytes": path.stat().st_size if path.is_file() else None, "failures": local_failures}
            failures.extend(f"{point['point_id']}/{mask}: {item}" for item in local_failures)

    runs: dict[str, Any] = {}
    run_dirs = sorted(path for path in (EXP / "runs").iterdir() if path.is_dir())
    for run_dir in run_dirs:
        if not run_dir.name.startswith("BOUNDARY_"):
            failures.append(f"unauthorized run directory: {run_dir.name}")
        record = raw_check(run_dir / "raw.csv", run_dir / "metadata.json")
        runs[run_dir.name] = record
        if record["status"] != "PASS":
            failures.extend(f"{run_dir.name}: {item}" for item in record["failures"])
        if not all((run_dir / name).is_file() for name in ("deck.cir", "raw.csv", "metadata.json", "run.log")):
            failures.append(f"incomplete run artifact: {run_dir.name}")

    results: dict[str, Any] = {}
    for point in matrix["points"]:
        path = EXP / "boundary/results" / f"{point['point_id']}.json"
        if not path.is_file():
            failures.append(f"missing midpoint result: {point['point_id']}")
            continue
        result = json.loads(path.read_text(encoding="utf-8"))
        results[point["point_id"]] = {"path": rel(path), "sha256": sha256(path), "threshold_ordering": result.get("threshold_ordering")}
        state_point = state.get("points", {}).get(point["point_id"], {})
        for branch, mask in (("n2", "0011"), ("n3", "0111")):
            case = state_point.get("cases", {}).get(mask)
            if case is None or result.get(branch, {}).get("raw_path") != case.get("raw_path") or result.get(branch, {}).get("raw_sha256") != case.get("raw_sha256"):
                failures.append(f"result/raw binding mismatch: {point['point_id']}/{mask}")
            control = result.get(branch, {}).get("evidence", {}).get("control", {})
            if control.get("rollback_excluded_from_control") is not True or not control.get("criterion"):
                failures.append(f"corrected control missing: {point['point_id']}/{mask}")
            if "BJ1_max_minus_final_turns" in json.dumps(control, ensure_ascii=False):
                failures.append(f"old rollback control field present: {point['point_id']}/{mask}")
    execution_path = EXP / "qa/execution_summary.json"
    execution = json.loads(execution_path.read_text(encoding="utf-8")) if execution_path.is_file() else {}
    if state.get("final_marker") != "EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW":
        failures.append("final marker missing")
    if execution.get("status") != "PASS" or execution.get("actual_new_physical_solve_count") != len(run_dirs) or execution.get("unauthorized_extra_solve_count") != 0 or execution.get("no_retry_performed") is not True:
        failures.append("execution summary mismatch")
    if execution.get("validation_new_physical_solve_count") != 0 or execution.get("no_n1_n4") is not True or execution.get("no_timestep_change") is not True:
        failures.append("forbidden follow-up guard failed")
    if sha256(SOLVER) != SOLVER_SHA256:
        failures.append("solver hash changed")
    raw_status = "PASS" if all(record["status"] == "PASS" for record in runs.values()) and all(record["raw.csv"]["status"] == "PASS" for record in references.values()) else "FAIL"
    deck_status = "PASS" if all(record["status"] == "PASS" for record in decks.values()) and all(record["status"] == "PASS" for record in factors.values()) else "FAIL"
    write_json(EXP / "qa/raw_qa.json", {"schema": "bvm-qb-threshold-ordering-boundary-raw-qa-v1", "experiment_id": EXP.name, "created_at_local": now(), "status": raw_status, "artifact_validity": "VALID" if raw_status == "PASS" else "ARTIFACT_INVALID", "required_probe_count": len(REQUIRED), "references": references, "runs": runs, "raw_files_modified": 0, "failures": failures})
    write_json(EXP / "qa/deck_diff_qa.json", {"schema": "bvm-qb-threshold-ordering-boundary-deck-qa-v1", "experiment_id": EXP.name, "created_at_local": now(), "status": deck_status, "decks": decks, "parameter_records": factors, "logical_case_count": 4, "failures": failures})
    raw_artifacts = {name: {"path": item.get("path"), "sha256": item.get("sha256"), "bytes": item.get("bytes")} for name, item in runs.items()}
    write_json(EXP / "qa/provenance.json", {"schema": "bvm-qb-threshold-ordering-boundary-provenance-v1", "experiment_id": EXP.name, "created_at_local": now(), "repository_head_at_qa": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip(), "preflight": {"path": rel(EXP / "analysis/preflight.json"), "sha256": sha256(EXP / "analysis/preflight.json")}, "source_manifest": {"path": rel(EXP / "SOURCE_MANIFEST.json"), "sha256": sha256(EXP / "SOURCE_MANIFEST.json")}, "matrix": {"path": rel(MATRIX), "sha256": sha256(MATRIX)}, "solver": {"path": rel(SOLVER), "sha256": sha256(SOLVER), "version": subprocess.check_output([str(SOLVER), "--version"], cwd=REPO, text=True)}, "raw": raw_artifacts, "endpoint_references": references, "results": results, "raw_authority": True, "rollback_not_control": True, "no_n1_n4": True, "no_timestep_change": True})
    write_json(EXP / "qa/transformation_registry.json", {"schema": "bvm-qb-threshold-ordering-boundary-transformation-registry-v1", "experiment_id": EXP.name, "created_at_local": now(), "raw_immutable": True, "phase": "independent unwrap of raw radians then rad/(2*pi) navigation only", "integration": "actual stored grid trapezoid; no interpolation", "control": "complete QBOUT->JTL1..6 chain in registered 70-110 ps windows; FINAL/Tail rollback excluded", "source_feedback": "actual-grid signed I(B_JSL8) areas", "visualization": "raw-direct standalone and temporary exact-grid focused comparisons deleted after render", "forbidden": ["replay", "passive capture", "source scaling", "read extension", "N1/N4 before later authorization", "third parameter", "timestep change", "raw overwrite"], "scientific_review_status": "AWAITING_SCIENTIFIC_REVIEW"})
    mechanical = "PASS" if not failures and raw_status == "PASS" and deck_status == "PASS" else "FAIL"
    write_json(EXP / "mechanical_summary.json", {"schema": "bvm-qb-threshold-ordering-boundary-mechanical-summary-v1", "experiment_id": EXP.name, "created_at_local": now(), "status": mechanical, "raw_qa_status": raw_status, "deck_qa_status": deck_status, "execution_status": execution.get("status"), "scientific_interpretation_performed": False, "scientific_review_status": "AWAITING_SCIENTIFIC_REVIEW", "raw_files_modified": 0, "failures": failures})
    print(json.dumps({"status": mechanical, "raw_status": raw_status, "deck_status": deck_status, "run_count": len(run_dirs), "failures": failures[:40]}, ensure_ascii=False, indent=2))
    return 0 if mechanical == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
