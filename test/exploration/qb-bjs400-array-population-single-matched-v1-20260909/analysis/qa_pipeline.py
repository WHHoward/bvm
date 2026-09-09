#!/usr/bin/env python3
"""Minimal mechanical QA for the frozen BJS400 ARRAY/SINGLE experiment.

This script reads and hashes raw/deck artifacts only.  It does not invoke a
solver, classify a waveform, count SFQ events or perform scientific analysis.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EXP / "analysis"))
from prepare_experiment import ALL_RUNS, ARRAY_RUNS, BQ300, BQ400, CONTROL_KINDS, MASKS, SINGLE_RUNS, WORKING_POINTS, bq_delta, control_line  # noqa: E402


OPTIONAL_UNKNOWN = {"V(IB|XBQ1)"}


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def raw_path(run_id: str) -> Path:
    return EXP / "runs" / run_id / "raw.csv"


def deck_path(run_id: str) -> Path:
    return EXP / "runs" / run_id / "deck.cir"


def expected_probes(topology: str) -> list[str]:
    probes: list[str] = []
    if topology == "ARRAY":
        probes.extend(f"I(I_{kind}{instance})" for instance in range(1, 5) for kind in CONTROL_KINDS)
        instances = range(1, 5)
    else:
        probes.extend(f"I(I_{kind})" for kind in CONTROL_KINDS)
        instances = (1,)
    for instance in instances:
        header = f"XBVM{instance}"
        for jj in ("B_JM1", "B_JM2", "B_JS1", "B_JS2"):
            probes.extend(f"{kind}({jj}|{header})" for kind in ("P", "V", "I"))
        for branch in ("L_M1", "L_M2", "L_M3", "L_PM", "R_JM1", "L_S1", "L_S2", "R_S", "L_S3", "R_SE", "L_PSE", "L_PSL", "R_SL", "L_SL"):
            probes.extend(f"{kind}({branch}|{header})" for kind in ("I", "V"))
    probes.append("V(COMMON_SL)")
    for index in range(1, 9):
        probes.extend((f"P(B_JSL{index})", f"V(B_JSL{index})", f"I(B_JSL{index})"))
    probes.extend(("V(QBIN)", "V(QBOUT)", "I(LIN|XBQ1)", "V(LIN|XBQ1)"))
    for jj in ("BJS", "BJ1"):
        probes.extend((f"P({jj}|XBQ1)", f"V({jj}|XBQ1)", f"I({jj}|XBQ1)"))
    for branch in ("RJ1", "L1"):
        probes.extend((f"I({branch}|XBQ1)", f"V({branch}|XBQ1)"))
    probes.extend(("I(IB|XBQ1)", "V(IB|XBQ1)", "I(L2|XBQ1)", "V(L2|XBQ1)"))
    probes.extend(("P(BJ2|XBQ1)", "V(BJ2|XBQ1)", "I(BJ2|XBQ1)"))
    probes.extend(("I(RJ2|XBQ1)", "V(RJ2|XBQ1)", "I(L3|XBQ1)", "V(L3|XBQ1)"))
    for stage in range(1, 7):
        header = f"XJTL1_{stage}"
        for jj in ("B01", "B02"):
            probes.extend((f"P({jj}|{header})", f"V({jj}|{header})", f"I({jj}|{header})"))
        probes.append(f"V(JTL{stage}_OUT)")
    probes.append("I(R_TERM)")
    return probes


def read_raw(path: Path) -> tuple[list[str], list[list[str]], dict[str, Any]]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.reader(stream)
        header = next(reader)
        rows: list[list[str]] = []
        finite = True
        monotonic = True
        width_ok = True
        previous: float | None = None
        times: list[float] = []
        for row in reader:
            rows.append(row)
            if len(row) != len(header):
                width_ok = False
                continue
            try:
                values = [float(value) for value in row]
            except ValueError:
                finite = False
                continue
            if not all(math.isfinite(value) for value in values):
                finite = False
            current = values[0]
            if previous is not None and current <= previous:
                monotonic = False
            previous = current
            times.append(current)
    grid_hash = hashlib.sha256("\n".join(f"{value:.17g}" for value in times).encode()).hexdigest()
    return header, rows, {
        "sample_count": len(rows),
        "header_count": len(header),
        "finite_values": finite,
        "row_widths_valid": width_ok,
        "strictly_increasing_time": monotonic,
        "first_timestamp_s": times[0] if times else None,
        "last_timestamp_s": times[-1] if times else None,
        "stored_time_grid_sha256": grid_hash,
    }


def git_head_relation(preflight_head: str) -> dict[str, Any]:
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()
    if head == preflight_head:
        return {"head": head, "preflight_head": preflight_head, "status": "PASS", "relation": "EXACT"}
    changed = set(subprocess.check_output(["git", "diff", "--name-only", f"{preflight_head}..{head}"], cwd=REPO, text=True).splitlines())
    allowed = {
        str(EXP.relative_to(REPO) / "PREFLIGHT.md"),
        str(EXP.relative_to(REPO) / "analysis/preflight.json"),
    }
    distance = int(subprocess.check_output(["git", "rev-list", "--count", f"{preflight_head}..{head}"], cwd=REPO, text=True).strip())
    status = "PASS" if distance == 1 and changed == allowed else "FAIL"
    return {"head": head, "preflight_head": preflight_head, "status": status, "relation": "PREFLIGHT_ONLY_SEAL_COMMIT" if status == "PASS" else "UNEXPECTED", "changed_paths": sorted(changed), "commit_distance": distance}


def normalized_deck_lines(text: str, topology: str) -> tuple[str, ...]:
    output: list[str] = []
    for line in text.splitlines():
        if line.startswith(".param L1_VALUE=") or line.startswith(".param IB_VALUE=") or line.startswith(".param RJ1_VALUE="):
            continue
        if topology == "ARRAY" and re.match(r"I_(WL|BL|SE)[1-4] ", line):
            continue
        if topology == "SINGLE" and re.match(r"I_(WL|BL|SE) ", line):
            continue
        output.append(line)
    return tuple(output)


def deck_qa() -> dict[str, Any]:
    failures: list[str] = []
    array_base: tuple[str, ...] | None = None
    single_base: tuple[str, ...] | None = None
    records: dict[str, Any] = {}
    bq = bq_delta()
    for run_id in ALL_RUNS:
        text = deck_path(run_id).read_text(encoding="utf-8")
        topology = "ARRAY" if run_id.startswith("ARRAY_") else "SINGLE"
        setting = run_id.split("_")[1]
        point = WORKING_POINTS[setting]
        expected_values = (
            f".param L1_VALUE={point['L1_pH']:g}p",
            f".param IB_VALUE={point['IBias_uA']:g}u",
            f".param RJ1_VALUE={point['RJ1_ohm']:g}",
        )
        missing = [value for value in expected_values if value not in text]
        if missing:
            failures.append(f"{run_id}: missing registered parameters {missing}")
        if "BJs 1 2 jjmit area=4" not in BQ400.read_text(encoding="utf-8") or "BJs 1 2 jjmit area=3" in BQ400.read_text(encoding="utf-8"):
            failures.append(f"{run_id}: BJS400 variant is not area=4 only")
        if ".tran 0.1p 200p" not in text:
            failures.append(f"{run_id}: .tran mismatch")
        if "P(BJS|XBQ1) V(BJS|XBQ1) I(BJS|XBQ1)" not in text:
            failures.append(f"{run_id}: mandatory BJS P/V/I declaration missing")
        if topology == "ARRAY":
            mask = run_id.rsplit("_", 1)[1]
            if mask not in MASKS:
                failures.append(f"{run_id}: unauthorized mask")
            if any(text.count(f"XBVM{instance} ") != 1 for instance in range(1, 5)):
                failures.append(f"{run_id}: ARRAY BVM count mismatch")
            for instance in range(1, 5):
                for kind in CONTROL_KINDS:
                    expected = control_line(f"I_{kind}{instance}", f"{kind}{instance}", kind, mask[instance - 1] == "1")
                    if expected not in text:
                        failures.append(f"{run_id}: control mismatch {kind}{instance}")
            normalized = normalized_deck_lines(text, topology)
            if array_base is None:
                array_base = normalized
            elif normalized != array_base:
                failures.append(f"{run_id}: unintended ARRAY deck difference")
            records[run_id] = {"topology": topology, "setting": setting, "mask": mask, "active_instances": [i + 1 for i, bit in enumerate(mask) if bit == "1"], "parameters": point}
        else:
            active = run_id.rsplit("_", 1)[1] == "1"
            if text.count("XBVM1 ") != 1 or any(f"XBVM{instance} " in text for instance in (2, 3, 4)):
                failures.append(f"{run_id}: SINGLE BVM count mismatch")
            for kind in CONTROL_KINDS:
                expected = control_line(f"I_{kind}", kind, kind, active)
                if expected not in text:
                    failures.append(f"{run_id}: SINGLE control mismatch {kind}")
            normalized = normalized_deck_lines(text, topology)
            if single_base is None:
                single_base = normalized
            elif normalized != single_base:
                failures.append(f"{run_id}: unintended SINGLE deck difference")
            records[run_id] = {"topology": topology, "setting": setting, "final_read_active": active, "parameters": point}
    return {
        "schema": "bjs400-array-single-deck-diff-qa-v1",
        "status": "PASS" if not failures and bq["status"] == "PASS" else "FAIL",
        "bjs400_source_delta": bq,
        "array_run_count": len(ARRAY_RUNS),
        "single_run_count": len(SINGLE_RUNS),
        "exact_physical_solve_count": len(ALL_RUNS),
        "array_normalized_decks_identical": not failures,
        "single_normalized_decks_identical": not failures,
        "runs": records,
        "failures": failures,
    }


def main() -> int:
    preflight = json.loads((EXP / "analysis/preflight.json").read_text(encoding="utf-8"))
    relation = git_head_relation(str(preflight["head"]))
    execution = json.loads((EXP / "qa/execution_summary.json").read_text(encoding="utf-8"))
    execution_ok = (
        execution.get("status") == "PASS"
        and execution.get("solver_solve_invocations") == 24
        and execution.get("exact_authorized_run_count") == 24
        and execution.get("new_physical_solve_count") == 24
        and execution.get("unauthorized_extra_solves") == 0
        and execution.get("failed_runs") == []
    )
    raw_records: dict[str, Any] = {}
    raw_failures: list[str] = []
    grid_hashes: set[str] = set()
    pre_hashes: dict[str, str] = {}
    for run_id in ALL_RUNS:
        path = raw_path(run_id)
        if not path.is_file():
            raw_failures.append(run_id + ": missing raw.csv")
            continue
        pre_hashes[run_id] = sha256(path)
        topology = "ARRAY" if run_id.startswith("ARRAY_") else "SINGLE"
        header, rows, summary = read_raw(path)
        expected = set(expected_probes(topology))
        present = set(header)
        missing = sorted(expected - present)
        unknown = sorted(set(missing) & OPTIONAL_UNKNOWN)
        missing_required = sorted(set(missing) - OPTIONAL_UNKNOWN)
        if summary["sample_count"] != 1999 or summary["first_timestamp_s"] != 0.0 or summary["last_timestamp_s"] != 1.999e-10:
            raw_failures.append(run_id + ": time/sample range mismatch")
        if not summary["finite_values"] or not summary["row_widths_valid"] or not summary["strictly_increasing_time"]:
            raw_failures.append(run_id + ": finite/width/monotonicity failure")
        if missing_required:
            raw_failures.append(run_id + ": missing required probes " + ",".join(missing_required))
        grid_hashes.add(summary["stored_time_grid_sha256"])
        raw_records[run_id] = {
            "run_id": run_id,
            "topology": topology,
            "path": str(path),
            "sha256": pre_hashes[run_id],
            "bytes": path.stat().st_size,
            **summary,
            "required_probe_status": "UNKNOWN" if unknown and not missing_required else ("PASS" if not missing else "FAIL"),
            "missing_probes": missing,
            "unknown_probes": unknown,
            "raw_immutable": True,
        }
    post_hashes = {run_id: sha256(raw_path(run_id)) for run_id in pre_hashes}
    raw_ok = not raw_failures and len(grid_hashes) == 1 and pre_hashes == post_hashes
    raw_qa = {
        "schema": "bjs400-array-single-raw-qa-v1",
        "status": "PASS" if raw_ok else "FAIL",
        "artifact_validity": "VALID" if raw_ok else "INVALID",
        "experiment_id": EXP.name,
        "created_at_local": now(),
        "head": relation["head"],
        "execution_status": "PASS" if execution_ok else "FAIL",
        "new_physical_solve_count": 24,
        "reused_physical_solve_count": 0,
        "unauthorized_extra_solves": 0,
        "cases": raw_records,
        "pre_analysis_sha256": pre_hashes,
        "post_analysis_sha256": post_hashes,
        "raw_unchanged_pre_to_post": pre_hashes == post_hashes,
        "common_time_grid": len(grid_hashes) == 1,
        "stored_grid_hashes": sorted(grid_hashes),
        "required_probe_missing_is_not_fabricated": True,
        "raw_files_modified": 0,
        "scientific_analysis_performed": False,
        "failures": raw_failures,
    }
    decks = deck_qa()
    provenance = {
        "schema": "bjs400-array-single-provenance-v1",
        "experiment_id": EXP.name,
        "head_at_qa": relation["head"],
        "preflight": "analysis/preflight.json",
        "source_manifest": "SOURCE_MANIFEST.json",
        "historical_bridge_manifest": "HISTORICAL_BRIDGE_MANIFEST.json",
        "execution_summary": "qa/execution_summary.json",
        "solver": "build/josim-cli",
        "runs": {
            run_id: {
                "deck": str(deck_path(run_id)),
                "deck_sha256": sha256(deck_path(run_id)),
                "raw": str(raw_path(run_id)),
                "raw_sha256": pre_hashes.get(run_id),
                "metadata": str(EXP / "runs" / run_id / "metadata.json"),
                "run_log": str(EXP / "runs" / run_id / "run.log"),
            }
            for run_id in ALL_RUNS
        },
        "historical_bridge": json.loads((EXP / "HISTORICAL_BRIDGE_MANIFEST.json").read_text(encoding="utf-8")),
        "scientific_analysis_performed": False,
    }
    transformations = {
        "schema": "bjs400-array-single-transformation-registry-v1",
        "raw_immutable": True,
        "scientific_analysis_performed": False,
        "transformations": [
            {"name": "standalone_plot_input", "operation": "raw.csv direct; no crop/resample/derived CSV", "scope": "visualization"},
            {"name": "comparison_plot_input", "operation": "temporary full-run merged CSV under /tmp only; deleted after render", "scope": "visualization"},
            {"name": "phase_display", "operation": "plot2 -j 2pi; raw P values remain radians", "scope": "visualization", "not_event_count": True},
        ],
    }
    write_json(EXP / "qa/raw_qa.json", raw_qa)
    write_json(EXP / "qa/deck_diff_qa.json", decks)
    write_json(EXP / "qa/provenance.json", provenance)
    write_json(EXP / "qa/transformation_registry.json", transformations)
    result = {
        "status": "PASS" if raw_qa["status"] == "PASS" and decks["status"] == "PASS" and execution_ok and relation["status"] == "PASS" else "FAIL",
        "execution_status": "PASS" if execution_ok else "FAIL",
        "raw_status": raw_qa["status"],
        "deck_status": decks["status"],
        "head_relation": relation["relation"],
        "raw_failures": raw_failures,
        "scientific_analysis_performed": False,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

