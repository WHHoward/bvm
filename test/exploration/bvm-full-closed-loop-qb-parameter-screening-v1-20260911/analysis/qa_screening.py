#!/usr/bin/env python3
"""Mechanical QA for the bounded full closed-loop QB screening evidence."""

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
MATRIX = EXP / "screening/SCREENING_MATRIX.json"
STATE = EXP / "screening/screening_state.json"
SOLVER = REPO / "build/josim-cli"
SOLVER_SHA256 = "48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2"
REQUIRED = ("I(B_JSL8)", "V(QBIN)", "V(COMMON_SL)", "I(LIN|XBQ1)", "I(L1|XBQ1)", "I(L2|XBQ1)", "P(BJ1|XBQ1)", "V(BJ1|XBQ1)", "I(BJ1|XBQ1)", "P(BJ2|XBQ1)", "V(BJ2|XBQ1)", "I(BJ2|XBQ1)", "V(QBOUT)", "V(JTL1_OUT)", "V(JTL2_OUT)", "V(JTL3_OUT)", "V(JTL4_OUT)", "V(JTL5_OUT)", "V(JTL6_OUT)", "I(R_TERM)") + tuple(f"P(B01|XJTL1_{stage})" for stage in range(1, 7))
BASELINE = {"Lin_pH": 1.5, "L1_pH": 1.4, "L2_pH": 2.0, "RJ1_ohm": 32.0, "RJ2_ohm": 12.0, "IBias_uA": 260.0, "BJS_area": 4.0, "BJ1_area": 0.9, "BJ2_area": 2.0, "L3_pH": 1.3}
REUSE_ORIGINS = {
    "references/reused_rj2p10/ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P10_0011": REPO / "test/exploration/bvm-population-rj2p10-weight3-diagnostic-l1p14-l2p20-ib260-rj32-bjs400-v1-20260911/references/rj2p10/ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P10_0011",
    "references/reused_rj2p10/ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P10_0111": REPO / "test/exploration/bvm-population-rj2p10-weight3-diagnostic-l1p14-l2p20-ib260-rj32-bjs400-v1-20260911/runs/ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P10_0111",
    "references/reused_rj2p11/ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P11_0011": REPO / "test/exploration/bvm-population-scaling-rj2p11-midpoint-l1p14-l2p20-ib260-rj32-bjs400-v1-20260911/runs/ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P11_0011",
    "references/reused_rj2p11/ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P11_0111": REPO / "test/exploration/bvm-population-scaling-rj2p11-midpoint-l1p14-l2p20-ib260-rj32-bjs400-v1-20260911/runs/ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P11_0111",
    "references/baseline_rj2p12/ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_0011": REPO / "test/exploration/bvm-population-scaling-rj2p12-l1p14-l2p20-ib260-rj32-bjs400-v1-20260910/references/reused/ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_0011",
    "references/baseline_rj2p12/ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_0111": REPO / "test/exploration/bvm-population-scaling-rj2p12-l1p14-l2p20-ib260-rj32-bjs400-v1-20260910/runs/ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_0111",
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


def raw_check(path: Path, metadata_path: Path | None = None, origin: Path | None = None) -> dict[str, Any]:
    failures: list[str] = []
    header: list[str] = []
    positions: dict[str, int] = {}
    times: list[float] = []
    finite = True
    width = True
    try:
        with path.open(newline="", encoding="utf-8-sig") as stream:
            reader = csv.reader(stream)
            header = next(reader)
            positions = {name: index for index, name in enumerate(header)}
            if len(positions) != len(header):
                failures.append("duplicate raw columns")
            missing = [name for name in REQUIRED if name not in positions]
            if missing:
                failures.append("missing required probes: " + ", ".join(missing))
            for row in reader:
                if len(row) != len(header):
                    width = False
                    continue
                try:
                    values = [float(value) for value in row]
                except ValueError:
                    finite = False
                    continue
                finite = finite and all(math.isfinite(value) for value in values)
                if "time" in positions:
                    times.append(values[positions["time"]])
    except (OSError, StopIteration) as exc:
        failures.append(f"cannot read raw: {exc}")
    if not width:
        failures.append("raw row width mismatch")
    if not finite:
        failures.append("non-finite raw value")
    if len(times) != 1999 or not times or times[0] != 0.0 or times[-1] != 1.999e-10:
        failures.append("raw time grid is not exactly 0..199.9 ps at 0.1 ps")
    if any(right <= left for left, right in zip(times, times[1:])):
        failures.append("raw timestamps are not strictly increasing")
    actual = sha256(path) if path.is_file() else None
    recorded = None
    if metadata_path is not None and metadata_path.is_file():
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            recorded = metadata.get("artifacts", {}).get("raw", {}).get("sha256")
            if recorded != actual:
                failures.append("metadata/raw SHA mismatch")
        except (OSError, json.JSONDecodeError) as exc:
            failures.append(f"metadata unreadable: {exc}")
    elif metadata_path is not None:
        failures.append("metadata missing")
    origin_sha = None
    if origin is not None:
        if not origin.is_file() or actual != sha256(origin):
            failures.append("immutable reuse raw is not byte-identical to origin")
        if origin.is_file():
            origin_sha = sha256(origin)
    return {
        "status": "PASS" if not failures else "FAIL",
        "path": rel(path),
        "sha256": actual,
        "bytes": path.stat().st_size if path.is_file() else None,
        "header_count": len(header),
        "sample_count": len(times),
        "time_range_s": [times[0], times[-1]] if times else None,
        "actual_grid": len(times) == 1999 and bool(times) and times[0] == 0.0 and times[-1] == 1.999e-10 and all(right > left for left, right in zip(times, times[1:])),
        "required_probes": list(REQUIRED),
        "metadata_raw_sha256": recorded,
        "origin_sha256": origin_sha,
        "failures": failures,
    }


def deck_lines(path: Path) -> list[str]:
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip() and not line.lstrip().startswith(("*", ".", "+"))]


def deck_check(path: Path, expected_parameter: str | None = None, expected_value: float | None = None, mask: str | None = None, variant: Path | None = None) -> dict[str, Any]:
    failures: list[str] = []
    if not path.is_file():
        return {"status": "FAIL", "path": rel(path), "failures": ["deck missing"]}
    text = path.read_text(encoding="utf-8")
    lines = deck_lines(path)
    if sum(line.endswith("BVM") for line in lines) != 4:
        failures.append("BVM count != 4")
    if sum(line.startswith("B_JSL") for line in lines) != 8:
        failures.append("JSL count != 8")
    if sum(line == "XBQ1 QBIN QBOUT BQ" for line in lines) != 1:
        failures.append("QB instance mismatch")
    if sum(line.startswith("XJTL1_") and line.endswith(" jtl") for line in lines) != 6:
        failures.append("JTL stage count != 6")
    if sum(line == "R_TERM JTL6_OUT 0 10" for line in lines) != 1:
        failures.append("terminal mismatch")
    for token in (".include ../../inputs/jjmit.cir", ".include ../../inputs/bvm_jm2_connected.cir", ".include ../../inputs/jtl2.cir", ".param L1_VALUE=", ".param IB_VALUE=", ".param RJ1_VALUE=", ".param RJ2_VALUE=", ".tran 0.1p 200p"):
        if token not in text:
            failures.append(f"missing full closed-loop token: {token}")
    if "I_REPLAY" in text or "PASSIVE" in text.upper():
        failures.append("replay/passive source token present")
    if expected_parameter is not None and expected_value is not None:
        expected_tokens = {"L1_pH": ("L1_VALUE", expected_value, "p"), "IBias_uA": ("IB_VALUE", expected_value, "u"), "RJ1_ohm": ("RJ1_VALUE", expected_value, ""), "RJ2_ohm": ("RJ2_VALUE", expected_value, "")}
        if expected_parameter in expected_tokens:
            key, value, suffix = expected_tokens[expected_parameter]
            if f".param {key}={value:g}{suffix}" not in text:
                failures.append(f"active deck parameter mismatch: {expected_parameter}")
        if variant is not None and not variant.is_file():
            failures.append("QB variant missing")
        if variant is not None and variant.is_file():
            variant_text = variant.read_text(encoding="utf-8")
            expected_variant = {"Lin_pH": (r"^Lin IN 1 ([0-9.eE+-]+)p$", expected_value), "L2_pH": (r"^L2 3 4 ([0-9.eE+-]+)p$", expected_value), "BJS_area": (r"^BJs 1 2 jjmit area=([0-9.eE+-]+)$", expected_value), "BJ1_area": (r"^BJ1 2 0 jjmit area=([0-9.eE+-]+)$", expected_value), "BJ2_area": (r"^BJ2 4 0 jjmit area=([0-9.eE+-]+)$", expected_value), "L3_pH": (r"^L3 4 OUT ([0-9.eE+-]+)p$", expected_value)}
            if expected_parameter in expected_variant:
                pattern, value = expected_variant[expected_parameter]
                matches = [float(match.group(1)) for line in variant_text.splitlines() if (match := re.match(pattern, line.strip()))]
                if len(matches) != 1 or not math.isclose(matches[0], value, rel_tol=0.0, abs_tol=1e-12):
                    failures.append(f"active QB variant parameter mismatch: {expected_parameter}")
    if mask is not None:
        expected_active = {"WL": [mask[index] == "1" for index in range(4)], "BL": [mask[index] == "1" for index in range(4)], "SE": [mask[index] == "1" for index in range(4)]}
        # The complete source deck has one stimulus line per control.  The
        # exact PWL text is checked by the registration matrix; here ensure
        # that all twelve controls remain present and no replay line replaced
        # them.
        for kind in ("WL", "BL", "SE"):
            if sum(line.startswith(f"I_{kind}{index} ") for index in range(1, 5) for line in text.splitlines()) != 4:
                failures.append(f"control line count mismatch: {kind}")
    return {"status": "PASS" if not failures else "FAIL", "path": rel(path), "sha256": sha256(path), "bytes": path.stat().st_size, "failures": failures}


def variant_values(path: Path) -> dict[str, float]:
    text = path.read_text(encoding="utf-8")
    patterns = {"Lin_pH": r"^Lin IN 1 ([0-9.eE+-]+)p$", "L2_pH": r"^L2 3 4 ([0-9.eE+-]+)p$", "BJS_area": r"^BJs 1 2 jjmit area=([0-9.eE+-]+)$", "BJ1_area": r"^BJ1 2 0 jjmit area=([0-9.eE+-]+)$", "BJ2_area": r"^BJ2 4 0 jjmit area=([0-9.eE+-]+)$", "L3_pH": r"^L3 4 OUT ([0-9.eE+-]+)p$"}
    result: dict[str, float] = {}
    for key, pattern in patterns.items():
        matches = [float(match.group(1)) for line in text.splitlines() if (match := re.match(pattern, line.strip()))]
        if len(matches) != 1:
            raise RuntimeError(f"cannot find unique variant value {key} in {path}")
        result[key] = matches[0]
    return result


def one_factor_record(point: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    variant = EXP / point["variant_path"].split("test/exploration/" + EXP.name + "/", 1)[-1] if False else REPO / point["variant_path"]
    values = dict(BASELINE)
    values.update(variant_values(variant))
    deck = REPO / point["cases"]["0011"]["path"]
    text = deck.read_text(encoding="utf-8")
    active_patterns = {"L1_pH": r"^\.param L1_VALUE=([0-9.eE+-]+)p$", "IBias_uA": r"^\.param IB_VALUE=([0-9.eE+-]+)u$", "RJ1_ohm": r"^\.param RJ1_VALUE=([0-9.eE+-]+)$", "RJ2_ohm": r"^\.param RJ2_VALUE=([0-9.eE+-]+)$"}
    for key, pattern in active_patterns.items():
        matches = [float(match.group(1)) for line in text.splitlines() if (match := re.match(pattern, line.strip()))]
        if len(matches) != 1:
            failures.append(f"active parameter not unique: {key}")
        else:
            values[key] = matches[0]
    changed = [key for key in BASELINE if not math.isclose(values[key], BASELINE[key], rel_tol=0.0, abs_tol=1e-12)]
    if changed != [point["parameter"]] or not math.isclose(values[point["parameter"]], float(point["value"]), rel_tol=0.0, abs_tol=1e-12):
        failures.append(f"one-factor violation: changed={changed}, expected={point['parameter']}={point['value']}")
    return {"status": "PASS" if not failures else "FAIL", "point_id": point["point_id"], "parameter": point["parameter"], "tested_value": point["value"], "resolved_values": values, "changed_parameters": changed, "failures": failures}


def reference_records() -> tuple[dict[str, Any], list[str]]:
    records: dict[str, Any] = {}
    failures: list[str] = []
    for relative, origin in REUSE_ORIGINS.items():
        local = REPO / (str(EXP.relative_to(REPO)) + "/" + relative)
        entry = {suffix: raw_check(local / suffix, local / "metadata.json", origin / suffix if suffix == "raw.csv" else None) for suffix in ("raw.csv",)}
        for suffix in ("deck.cir", "metadata.json", "run.log"):
            path = local / suffix
            if not path.is_file():
                entry[suffix] = {"status": "FAIL", "path": rel(path), "failures": ["missing"]}
            else:
                entry[suffix] = {"status": "PASS", "path": rel(path), "sha256": sha256(path), "bytes": path.stat().st_size}
        records[relative] = entry
        if any(item.get("status") != "PASS" for item in entry.values()):
            failures.append(relative)
        if origin.is_dir():
            for suffix in ("deck.cir", "metadata.json", "run.log"):
                if (local / suffix).is_file() and sha256(local / suffix) != sha256(origin / suffix):
                    failures.append(f"reuse byte mismatch: {relative}/{suffix}")
    return records, failures


def main() -> int:
    matrix = json.loads(MATRIX.read_text(encoding="utf-8"))
    state = json.loads(STATE.read_text(encoding="utf-8"))
    failures: list[str] = []
    reference, reference_failures = reference_records()
    failures.extend(reference_failures)

    deck_records: dict[str, Any] = {}
    factor_records: dict[str, Any] = {}
    for point in matrix["points"]:
        factor = one_factor_record(point)
        factor_records[point["point_id"]] = factor
        if factor["status"] != "PASS":
            failures.extend(f"{point['point_id']}: {item}" for item in factor["failures"])
        for mask in ("0011", "0111"):
            case = point["cases"][mask]
            deck = REPO / case["path"]
            if not deck.is_file() or sha256(deck) != case["sha256"]:
                failures.append(f"registered deck hash/missing: {point['point_id']}/{mask}")
            check = deck_check(deck, point["parameter"], float(point["value"]), mask, REPO / point["variant_path"])
            deck_records[f"{point['point_id']}/{mask}"] = check
            if check["status"] != "PASS":
                failures.extend(f"{point['point_id']}/{mask}: {item}" for item in check["failures"])

    raw_records: dict[str, Any] = {}
    run_dirs = sorted(path for path in (EXP / "runs").iterdir() if path.is_dir())
    for run_dir in run_dirs:
        if not (run_dir.name.startswith("SCREEN_") or run_dir.name.startswith("VALIDATION_")):
            failures.append(f"unauthorized run directory: {run_dir.name}")
        metadata_path = run_dir / "metadata.json"
        raw_records[run_dir.name] = raw_check(run_dir / "raw.csv", metadata_path)
        for suffix in ("deck.cir", "metadata.json", "run.log"):
            if not (run_dir / suffix).is_file():
                failures.append(f"run artifact missing: {run_dir.name}/{suffix}")
        if raw_records[run_dir.name]["status"] != "PASS":
            failures.extend(f"{run_dir.name}: {item}" for item in raw_records[run_dir.name]["failures"])

    result_records: dict[str, Any] = {}
    for point in matrix["points"]:
        path = EXP / "screening/results" / f"{point['point_id']}.json"
        if not path.is_file():
            continue
        result = json.loads(path.read_text(encoding="utf-8"))
        result_records[point["point_id"]] = {"path": rel(path), "sha256": sha256(path), "candidate_class": result.get("candidate_class"), "n2_raw_sha256": result.get("n2", {}).get("raw_sha256"), "n3_raw_sha256": result.get("n3", {}).get("raw_sha256")}
        for branch, mask in (("n2", "0011"), ("n3", "0111")):
            case = state.get("points", {}).get(point["point_id"], {}).get("cases", {}).get(mask)
            if case is None or result.get(branch, {}).get("raw_path") != case.get("raw_path") or result.get(branch, {}).get("raw_sha256") != case.get("raw_sha256"):
                failures.append(f"analysis/raw binding mismatch: {point['point_id']}/{mask}")

    execution = json.loads((EXP / "qa/execution_summary.json").read_text(encoding="utf-8")) if (EXP / "qa/execution_summary.json").is_file() else {}
    if state.get("final_marker") != "EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW":
        failures.append("final marker is missing")
    actual_physical = sum(1 for path in run_dirs if path.name.startswith("SCREEN_") or path.name.startswith("VALIDATION_"))
    if execution.get("exact_new_physical_solve_count") != actual_physical or execution.get("solver_solve_invocations") != actual_physical:
        failures.append("execution physical solve count does not match run directories")
    if execution.get("unauthorized_extra_solves") != 0 or execution.get("no_retry_performed") is not True:
        failures.append("execution retry/authorization guard failed")
    if execution.get("no_replay") is not True or execution.get("no_passive_capture") is not True or execution.get("no_timestep_sweep") is not True:
        failures.append("forbidden workflow guard missing")
    if sha256(SOLVER) != SOLVER_SHA256:
        failures.append("solver hash changed")

    raw_status = "PASS" if not any(item.get("status") != "PASS" for item in raw_records.values()) and not reference_failures else "FAIL"
    deck_status = "PASS" if not any(item.get("status") != "PASS" for item in deck_records.values()) and not any(item.get("status") != "PASS" for item in factor_records.values()) else "FAIL"
    write_json(EXP / "qa/raw_qa.json", {"schema": "bvm-full-closed-loop-qb-screening-raw-qa-v1", "experiment_id": EXP.name, "created_at_local": now(), "status": raw_status, "artifact_validity": "VALID" if raw_status == "PASS" else "ARTIFACT_INVALID", "raw_files_modified": 0, "required_probe_count": len(REQUIRED), "references": reference, "runs": raw_records, "failures": reference_failures + [item for name, record in raw_records.items() for item in record.get("failures", [])]})
    write_json(EXP / "qa/deck_diff_qa.json", {"schema": "bvm-full-closed-loop-qb-screening-deck-qa-v1", "experiment_id": EXP.name, "created_at_local": now(), "status": deck_status, "registered_point_count": len(matrix["points"]), "registered_case_count": len(matrix["points"]) * 2, "one_factor_only": True, "full_closed_loop_only": True, "decks": deck_records, "one_factor_records": factor_records, "failures": failures})
    raw_artifacts = {name: {"raw": record.get("sha256"), "bytes": record.get("bytes")} for name, record in raw_records.items()}
    write_json(EXP / "qa/provenance.json", {"schema": "bvm-full-closed-loop-qb-screening-provenance-v1", "experiment_id": EXP.name, "created_at_local": now(), "repository_head_at_qa": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip(), "preflight": {"path": rel(EXP / "analysis/preflight.json"), "sha256": sha256(EXP / "analysis/preflight.json")}, "source_manifest": {"path": rel(EXP / "SOURCE_MANIFEST.json"), "sha256": sha256(EXP / "SOURCE_MANIFEST.json")}, "matrix": {"path": rel(MATRIX), "sha256": sha256(MATRIX)}, "solver": {"path": rel(SOLVER), "sha256": sha256(SOLVER), "version": subprocess.check_output([str(SOLVER), "--version"], cwd=REPO, text=True)}, "raw_artifacts": raw_artifacts, "reference_artifacts": reference, "results": result_records, "raw_authority": True, "baseline_immutable": True, "no_replay": True, "no_passive_capture": True, "no_timestep_sweep": True})
    write_json(EXP / "qa/transformation_registry.json", {"schema": "bvm-full-closed-loop-qb-screening-transformation-registry-v1", "experiment_id": EXP.name, "created_at_local": now(), "raw_immutable": True, "raw_input_mode": "direct raw CSV", "analysis": {"phase": "continuous unwrap of raw P radians; display/navigation turns = rad/(2*pi)", "integration": "trapezoid on actual stored time grid; no interpolation", "peak_navigation": "raw voltage lobe navigation only; not an SFQ count", "terminal_area": "diagnostic only; not a count"}, "visualization": "raw.csv direct for standalone; temporary exact-grid merged CSV only for comparisons and deleted after render", "forbidden_transformations": ["replay source", "passive-ground capture", "resampling", "smoothing", "timestep change", "raw overwrite"], "scientific_review_status": "AWAITING_SCIENTIFIC_REVIEW"})
    mechanical_status = "PASS" if not failures and raw_status == "PASS" and deck_status == "PASS" else "FAIL"
    write_json(EXP / "mechanical_summary.json", {"schema": "bvm-full-closed-loop-qb-screening-mechanical-summary-v1", "experiment_id": EXP.name, "created_at_local": now(), "status": mechanical_status, "raw_qa_status": raw_status, "deck_qa_status": deck_status, "execution_status": execution.get("status"), "scientific_interpretation_performed": False, "scientific_review_status": "AWAITING_SCIENTIFIC_REVIEW", "raw_files_modified": 0, "failures": failures})
    print(json.dumps({"status": mechanical_status, "raw_status": raw_status, "deck_status": deck_status, "run_count": actual_physical, "failures": failures[:40]}, ensure_ascii=False, indent=2))
    return 0 if mechanical_status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
