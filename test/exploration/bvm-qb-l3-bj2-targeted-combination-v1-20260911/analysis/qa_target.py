#!/usr/bin/env python3
"""Mechanical QA for the targeted L3/BJ2 full closed-loop experiment."""

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
MATRIX = EXP / "screening/TARGET_MATRIX.json"
STATE = EXP / "screening/target_state.json"
SOLVER = REPO / "build/josim-cli"
SOLVER_SHA256 = "48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2"
POINT_ID = "TARGET_L3_2_BJ2_2p2"
SCREENING_MASKS = ("0011", "0111")
VALIDATION_MASKS = ("0001", "1111")
ALL_MASKS = SCREENING_MASKS + VALIDATION_MASKS
BASELINE = {"Lin_pH": 1.5, "L1_pH": 1.4, "L2_pH": 2.0, "RJ1_ohm": 32.0, "RJ2_ohm": 12.0, "IBias_uA": 260.0, "BJS_area": 4.0, "BJ1_area": 0.9, "BJ2_area": 2.0, "L3_pH": 1.3}
REQUIRED = (
    tuple(f"I(L_SL|XBVM{index})" for index in range(1, 5))
    + ("V(COMMON_SL)",)
    + tuple(f"{kind}(B_JSL{index})" for index in range(1, 9) for kind in ("P", "V", "I"))
    + ("V(QBIN)", "I(LIN|XBQ1)", "V(LIN|XBQ1)", "I(L1|XBQ1)", "V(L1|XBQ1)", "I(L2|XBQ1)", "V(L2|XBQ1)", "I(L3|XBQ1)", "V(L3|XBQ1)", "I(RJ1|XBQ1)", "V(RJ1|XBQ1)", "I(RJ2|XBQ1)", "V(RJ2|XBQ1)", "P(BJS|XBQ1)", "V(BJS|XBQ1)", "I(BJS|XBQ1)", "P(BJ1|XBQ1)", "V(BJ1|XBQ1)", "I(BJ1|XBQ1)", "P(BJ2|XBQ1)", "V(BJ2|XBQ1)", "I(BJ2|XBQ1)", "V(QBOUT)")
    + tuple(item for stage in range(1, 7) for item in (f"P(B01|XJTL1_{stage})", f"V(B01|XJTL1_{stage})", f"I(B01|XJTL1_{stage})", f"P(B02|XJTL1_{stage})", f"V(B02|XJTL1_{stage})", f"I(B02|XJTL1_{stage})", f"V(JTL{stage}_OUT)"))
    + ("I(R_TERM)",)
)
ORIGINS = {
    "canonical_l3p13/0011": REPO / "test/exploration/bvm-qb-l3-highside-selective-window-v1-20260911/references/canonical_l3p13/0011",
    "canonical_l3p13/0111": REPO / "test/exploration/bvm-qb-l3-highside-selective-window-v1-20260911/references/canonical_l3p13/0111",
    "l3p20/0011": REPO / "test/exploration/bvm-qb-l3-highside-selective-window-v1-20260911/runs/L3_H2_L3_2_0011",
    "l3p20/0111": REPO / "test/exploration/bvm-qb-l3-highside-selective-window-v1-20260911/runs/L3_H2_L3_2_0111",
    "bj2p22_l3p13/0011": REPO / "test/exploration/bvm-full-closed-loop-qb-parameter-screening-v1-20260911/runs/SCREEN_BJ2_area_2p2_0011",
    "bj2p22_l3p13/0111": REPO / "test/exploration/bvm-full-closed-loop-qb-parameter-screening-v1-20260911/runs/SCREEN_BJ2_area_2p2_0111",
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
                    failures.append("nonfinite raw value")
                times.append(values[positions["time"]])
    except (OSError, StopIteration, ValueError, KeyError) as exc:
        failures.append(f"raw read failure: {exc}")
    grid = len(times) == 1999 and bool(times) and times[0] == 0.0 and times[-1] == 1.999e-10 and all(right > left for left, right in zip(times, times[1:]))
    if not grid:
        failures.append("time grid is not 1999 samples 0..199.9 ps")
    actual = sha256(path) if path.is_file() else None
    recorded = None
    if metadata is not None:
        if metadata.is_file():
            try:
                recorded = json.loads(metadata.read_text(encoding="utf-8")).get("artifacts", {}).get("raw", {}).get("sha256")
                if recorded != actual:
                    failures.append("metadata/raw SHA mismatch")
            except (OSError, json.JSONDecodeError) as exc:
                failures.append(f"metadata read failure: {exc}")
        else:
            failures.append("metadata missing")
    origin_sha = None
    if origin is not None:
        if not origin.is_file() or actual != sha256(origin):
            failures.append("reference is not byte-identical to origin")
        if origin.is_file():
            origin_sha = sha256(origin)
    return {"status": "PASS" if not failures else "FAIL", "path": rel(path), "sha256": actual, "bytes": path.stat().st_size if path.is_file() else None, "header_count": len(header), "sample_count": len(times), "time_range_s": [times[0], times[-1]] if times else None, "actual_grid": grid, "metadata_raw_sha256": recorded, "origin_sha256": origin_sha, "failures": failures}


def active_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip() and not line.lstrip().startswith(("*", ".", "+"))]


def structural_signature(path: Path) -> tuple[str, ...]:
    lines = []
    for line in path.read_text(encoding="utf-8").splitlines():
        value = line.strip()
        if not value or value.startswith(("*", ".param", "I_WL", "I_BL", "I_SE")) or "bq_variants/" in value or "BQ_parameterized_bjs400_rj2.cir" in value:
            continue
        lines.append(value)
    return tuple(lines)


def deck_check(path: Path, point: dict[str, Any], mask: str) -> dict[str, Any]:
    failures: list[str] = []
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    lines = active_lines(text)
    if sum(line.endswith("BVM") for line in lines) != 4 or sum(line.startswith("B_JSL") for line in lines) != 8:
        failures.append("BVM/JSL topology count mismatch")
    if sum(line == "XBQ1 QBIN QBOUT BQ" for line in lines) != 1 or sum(line.startswith("XJTL1_") and line.endswith(" jtl") for line in lines) != 6:
        failures.append("QB/JTL topology count mismatch")
    if sum(line == "R_TERM JTL6_OUT 0 10" for line in lines) != 1:
        failures.append("terminal mismatch")
    required_includes = (".include ../../inputs/jjmit.cir", ".include ../../inputs/bvm_jm2_connected.cir", ".include ../../inputs/jtl2.cir", ".tran 0.1p 200p")
    failures.extend(f"missing {item}" for item in required_includes if item not in text)
    if "I_REPLAY" in text or "PASSIVE" in text.upper() or "replay" in text.lower():
        failures.append("forbidden replay/passive token")
    if path.is_file() and structural_signature(path) != structural_signature(EXP / "references/canonical_l3p13/0011/deck.cir"):
        failures.append("full topology/protocol structural signature differs")
    for expected in (".param L1_VALUE=1.4p", ".param IB_VALUE=260u", ".param RJ1_VALUE=32", ".param RJ2_VALUE=12"):
        if expected not in text:
            failures.append(f"missing frozen active parameter: {expected}")
    variant = EXP / "inputs/bq_variants/TARGET_L3_2_BJ2_2p2_L3_pH2_BJ2_area2p2.cir"
    variant_text = variant.read_text(encoding="utf-8") if variant.is_file() else ""
    if "BJ2 4 0 jjmit area=2.2" not in variant_text or "L3 4 OUT 2p" not in variant_text:
        failures.append("target variant values not bound")
    return {"status": "PASS" if not failures else "FAIL", "path": rel(path), "sha256": sha256(path) if path.is_file() else None, "bytes": path.stat().st_size if path.is_file() else None, "point_id": point["point_id"], "mask": mask, "changes": point["changes"], "failures": failures}


def main() -> int:
    matrix = json.loads(MATRIX.read_text(encoding="utf-8"))
    state = json.loads(STATE.read_text(encoding="utf-8"))
    failures: list[str] = []
    reference_records: dict[str, Any] = {}
    for key, origin_dir in ORIGINS.items():
        local_dir = EXP / "references" / key
        record: dict[str, Any] = {}
        for name in ("raw.csv", "deck.cir", "metadata.json", "run.log"):
            local, origin = local_dir / name, origin_dir / name
            if name == "raw.csv":
                record[name] = raw_check(local, local_dir / "metadata.json", origin)
                failures.extend(f"{key}: {item}" for item in record[name]["failures"])
            else:
                same = local.is_file() and origin.is_file() and sha256(local) == sha256(origin)
                record[name] = {"status": "PASS" if same else "FAIL", "path": rel(local), "sha256": sha256(local) if local.is_file() else None, "bytes": local.stat().st_size if local.is_file() else None, "origin_sha256": sha256(origin) if origin.is_file() else None}
                if not same:
                    failures.append(f"reference mismatch: {key}/{name}")
        reference_records[key] = record

    point = matrix["points"][0]
    decks: dict[str, Any] = {}
    for mask in ALL_MASKS:
        path = REPO / point["cases"][mask]["path"]
        record = deck_check(path, point, mask)
        decks[mask] = record
        failures.extend(f"deck {mask}: {item}" for item in record["failures"])

    run_dirs = sorted(path for path in (EXP / "runs").iterdir() if path.is_dir())
    runs: dict[str, Any] = {}
    for run_dir in run_dirs:
        if run_dir.name not in {f"{POINT_ID}_{mask}" for mask in ALL_MASKS}:
            failures.append(f"unauthorized run directory: {run_dir.name}")
        record = raw_check(run_dir / "raw.csv", run_dir / "metadata.json")
        runs[run_dir.name] = record
        failures.extend(f"{run_dir.name}: {item}" for item in record["failures"])
        if not all((run_dir / name).is_file() for name in ("deck.cir", "raw.csv", "metadata.json", "run.log")):
            failures.append(f"incomplete run: {run_dir.name}")

    result_path = EXP / "screening/results/TARGET_L3_2_BJ2_2p2_v2.json"
    results: dict[str, Any] = {}
    if result_path.is_file():
        result = json.loads(result_path.read_text(encoding="utf-8"))
        results[POINT_ID] = {"path": rel(result_path), "sha256": sha256(result_path), "candidate_class": result.get("candidate_class"), "candidate_label": result.get("candidate_label"), "analysis_version": result.get("analysis_version"), "supersedes_result": result.get("supersedes_result")}
        for branch, mask in (("n2", "0011"), ("n3", "0111")):
            case = state.get("screening_cases", {}).get(mask)
            if case is None or result.get(branch, {}).get("raw_path") != case.get("raw_path") or result.get(branch, {}).get("raw_sha256") != case.get("raw_sha256"):
                failures.append(f"result/raw binding mismatch: {branch}/{mask}")
            control = result.get(branch, {}).get("evidence", {}).get("control", {})
            if control.get("rollback_excluded_from_control") is not True or not control.get("criterion"):
                failures.append(f"corrected control missing: {branch}/{mask}")
            if "BJ1_max_minus_final_turns" in json.dumps(control, ensure_ascii=False):
                failures.append(f"old rollback control criterion present: {branch}/{mask}")
        for reference_name, reference in result.get("references", {}).items():
            for mask, path in reference.get("raw_paths", {}).items():
                if not (REPO / path).is_file() or reference.get("raw_sha256", {}).get(mask) != sha256(REPO / path):
                    failures.append(f"stale reference binding: {reference_name}/{mask}")
    else:
        failures.append("target result missing")

    execution = json.loads((EXP / "qa/execution_summary.json").read_text(encoding="utf-8")) if (EXP / "qa/execution_summary.json").is_file() else {}
    if state.get("final_marker") != "EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW":
        failures.append("final marker missing")
    if execution.get("status") != "PASS" or execution.get("actual_new_physical_solve_count") != len(run_dirs) or execution.get("unauthorized_extra_solve_count") != 0 or execution.get("no_retry_performed") is not True:
        failures.append("execution summary mismatch")
    if len(run_dirs) > 4 or len(run_dirs) < 2 or execution.get("screening_new_physical_solve_count") != 2:
        failures.append("solve budget or screening count mismatch")
    if state.get("candidate_class") == "S":
        if set(state.get("validation_cases", {})) != set(VALIDATION_MASKS) or execution.get("validation_new_physical_solve_count") != 2:
            failures.append("clean 2/3 did not receive both conditional validation solves")
    elif execution.get("validation_new_physical_solve_count") != 0 or state.get("validation_cases"):
        failures.append("conditional validation was run without clean 2/3")

    raw_status = "PASS" if runs and all(item["status"] == "PASS" for item in runs.values()) and all(item["raw.csv"]["status"] == "PASS" for item in reference_records.values()) else "FAIL"
    deck_status = "PASS" if all(item["status"] == "PASS" for item in decks.values()) else "FAIL"
    write_json(EXP / "qa/raw_qa.json", {"schema": "bvm-qb-l3-bj2-targeted-combination-raw-qa-v1", "experiment_id": EXP.name, "created_at_local": now(), "status": raw_status, "artifact_validity": "VALID" if raw_status == "PASS" else "ARTIFACT_INVALID", "required_probe_count": len(REQUIRED), "references": reference_records, "runs": runs, "raw_files_modified": 0, "failures": failures})
    write_json(EXP / "qa/deck_diff_qa.json", {"schema": "bvm-qb-l3-bj2-targeted-combination-deck-qa-v1", "experiment_id": EXP.name, "created_at_local": now(), "status": deck_status, "decks": decks, "target_only_changes": {"L3_pH": 2.0, "BJ2_area": 2.2}, "failures": failures})
    write_json(EXP / "qa/provenance.json", {"schema": "bvm-qb-l3-bj2-targeted-combination-provenance-v1", "experiment_id": EXP.name, "created_at_local": now(), "repository_head_at_qa": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip(), "preflight": {"path": rel(EXP / "analysis/preflight.json"), "sha256": sha256(EXP / "analysis/preflight.json")}, "source_manifest": {"path": rel(EXP / "SOURCE_MANIFEST.json"), "sha256": sha256(EXP / "SOURCE_MANIFEST.json")}, "matrix": {"path": rel(MATRIX), "sha256": sha256(MATRIX)}, "solver": {"path": rel(SOLVER), "sha256": sha256(SOLVER), "version": subprocess.check_output([str(SOLVER), "--version"], cwd=REPO, text=True)}, "runs": {name: {"raw_sha256": item.get("sha256"), "bytes": item.get("bytes")} for name, item in runs.items()}, "references": {key: {"raw_sha256": value["raw.csv"].get("sha256"), "bytes": value["raw.csv"].get("bytes")} for key, value in reference_records.items()}, "results": results, "reference_roles": {"canonical": "L3=1.3 BJ2=2.0", "l3_only": "L3=2.0 BJ2=2.0", "bj2_only": "L3=1.3 BJ2=2.2"}, "raw_authority": True, "no_extra_parameter": True, "no_timestep_change": True})
    write_json(EXP / "qa/transformation_registry.json", {"schema": "bvm-qb-l3-bj2-targeted-combination-transformation-registry-v1", "experiment_id": EXP.name, "created_at_local": now(), "raw_immutable": True, "phase": "independent continuous unwrap of raw radians then rad/(2*pi) navigation only", "integration": "actual-grid trapezoid without interpolation", "control": "complete QBOUT->JTL1..6 chain only in registered 70-110 ps windows; FINAL/Tail rollback excluded", "source_feedback": "actual-grid I(B_JSL8) signed areas", "visualization": "raw-direct standalone and temporary exact-grid focused comparison deleted after render", "forbidden": ["replay", "passive capture", "source modification", "source scaling", "extra scan", "third parameter", "timestep change", "positional validation"], "scientific_review_status": "AWAITING_SCIENTIFIC_REVIEW"})
    mechanical = "PASS" if not failures and raw_status == "PASS" and deck_status == "PASS" else "FAIL"
    write_json(EXP / "mechanical_summary.json", {"schema": "bvm-qb-l3-bj2-targeted-combination-mechanical-summary-v1", "experiment_id": EXP.name, "created_at_local": now(), "status": mechanical, "raw_qa_status": raw_status, "deck_qa_status": deck_status, "execution_status": execution.get("status"), "scientific_interpretation_performed": False, "scientific_review_status": "AWAITING_SCIENTIFIC_REVIEW", "raw_files_modified": 0, "failures": failures})
    print(json.dumps({"status": mechanical, "raw_status": raw_status, "deck_status": deck_status, "run_count": len(run_dirs), "reference_count": len(reference_records), "failures": failures[:40]}, ensure_ascii=False, indent=2))
    return 0 if mechanical == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
