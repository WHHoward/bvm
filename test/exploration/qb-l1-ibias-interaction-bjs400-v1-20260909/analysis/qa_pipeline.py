#!/usr/bin/env python3
"""Minimal raw/deck QA for the BJS400 L1 x IBias interaction experiment."""

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
from prepare_experiment import BQ400, CONTROL_KINDS, MASKS, NEW_RUNS, REUSE_RUNS, RUN_TO_CORNER, RUN_TO_MASK, WORKING_POINTS, control_line  # noqa: E402


OPTIONAL_UNKNOWN = {"V(IB|XBQ1)"}
ALL_CASES = NEW_RUNS + REUSE_RUNS


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


def raw_path(case_id: str) -> Path:
    return EXP / ("runs" if case_id in NEW_RUNS else "references/reused") / case_id / "raw.csv"


def deck_path(case_id: str) -> Path:
    return EXP / ("runs" if case_id in NEW_RUNS else "references/reused") / case_id / "deck.cir"


def expected_probes() -> list[str]:
    probes: list[str] = []
    for instance in range(1, 5):
        probes.extend(f"I(I_{kind}{instance})" for kind in CONTROL_KINDS)
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


def read_raw(path: Path) -> dict[str, Any]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.reader(stream)
        header = next(reader)
        rows: list[list[str]] = []
        times: list[float] = []
        finite = True
        width_ok = True
        monotonic = True
        previous: float | None = None
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
            finite = finite and all(math.isfinite(value) for value in values)
            current = values[0]
            monotonic = monotonic and (previous is None or current > previous)
            previous = current
            times.append(current)
    grid_hash = hashlib.sha256("\n".join(f"{value:.17g}" for value in times).encode()).hexdigest()
    return {
        "header_count": len(header),
        "sample_count": len(rows),
        "first_timestamp_s": times[0] if times else None,
        "last_timestamp_s": times[-1] if times else None,
        "finite_values": finite,
        "row_widths_valid": width_ok,
        "strictly_increasing_time": monotonic,
        "stored_time_grid_sha256": grid_hash,
        "headers": header,
    }


def head_relation(preflight_head: str) -> dict[str, Any]:
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()
    if head == preflight_head:
        return {"status": "PASS", "head": head, "preflight_head": preflight_head, "relation": "EXACT"}
    changed = set(subprocess.check_output(["git", "diff", "--name-only", f"{preflight_head}..{head}"], cwd=REPO, text=True).splitlines())
    allowed = {
        str(EXP.relative_to(REPO) / "PREFLIGHT.md"),
        str(EXP.relative_to(REPO) / "analysis/preflight.json"),
    }
    distance = int(subprocess.check_output(["git", "rev-list", "--count", f"{preflight_head}..{head}"], cwd=REPO, text=True).strip())
    status = "PASS" if distance == 1 and changed == allowed else "FAIL"
    return {"status": status, "head": head, "preflight_head": preflight_head, "relation": "PREFLIGHT_ONLY_SEAL_COMMIT" if status == "PASS" else "UNEXPECTED", "changed_paths": sorted(changed), "commit_distance": distance}


def normalized_deck(text: str) -> tuple[str, ...]:
    output = []
    for line in text.splitlines():
        if line.startswith(".param L1_VALUE=") or line.startswith(".param IB_VALUE=") or line.startswith(".param RJ1_VALUE="):
            continue
        if re.match(r"I_(WL|BL|SE)[1-4] ", line):
            continue
        output.append(line)
    return tuple(output)


def deck_diff() -> dict[str, Any]:
    failures: list[str] = []
    normalized: set[tuple[str, ...]] = set()
    records: dict[str, Any] = {}
    bq = BQ400.read_text(encoding="utf-8")
    if "BJs 1 2 jjmit area=4" not in bq or "BJs 1 2 jjmit area=3" in bq:
        failures.append("BJS400 source is not exactly area=4")
    for run_id in NEW_RUNS:
        text = deck_path(run_id).read_text(encoding="utf-8")
        corner = WORKING_POINTS[RUN_TO_CORNER[run_id]]
        mask = RUN_TO_MASK[run_id]
        for required in (
            f".param L1_VALUE={corner['L1_pH']:g}p",
            f".param IB_VALUE={corner['IBias_uA']:g}u",
            ".param RJ1_VALUE=12",
            ".tran 0.1p 200p",
            "P(BJS|XBQ1) V(BJS|XBQ1) I(BJS|XBQ1)",
        ):
            if required not in text:
                failures.append(f"{run_id}: missing {required}")
        if any(text.count(f"XBVM{index} ") != 1 for index in range(1, 5)):
            failures.append(f"{run_id}: BVM topology count mismatch")
        for instance in range(1, 5):
            for kind in CONTROL_KINDS:
                expected = control_line(instance, kind, mask[instance - 1] == "1")
                if expected not in text:
                    failures.append(f"{run_id}: control mismatch {kind}{instance}")
        normalized.add(normalized_deck(text))
        records[run_id] = {
            "corner": RUN_TO_CORNER[run_id],
            "mask": mask,
            "parameters": corner,
            "deck_sha256": sha256(deck_path(run_id)),
            "deck_bytes": deck_path(run_id).stat().st_size,
        }
    pre_read_signatures = set()
    for run_id in NEW_RUNS:
        lines = deck_path(run_id).read_text(encoding="utf-8").splitlines()
        pre_read_signatures.add(tuple(line.split(" 110p", 1)[0] for line in lines if re.match(r"I_(WL|BL|SE)[1-4] ", line)))
    if len(pre_read_signatures) != 1:
        failures.append("new ARRAY controls differ before 110ps")
    return {
        "schema": "bjs400-l1-ibias-interaction-deck-diff-qa-v1",
        "status": "PASS" if not failures and len(normalized) == 1 else "FAIL",
        "exact_new_run_count": len(NEW_RUNS),
        "reused_case_count": len(REUSE_RUNS),
        "normalized_new_decks_identical": len(normalized) == 1,
        "pre_110ps_control_equality": len(pre_read_signatures) == 1,
        "bjs400_source_delta": {"status": "PASS" if not failures else "FAIL", "active_line": "BJs 1 2 jjmit area=4"},
        "runs": records,
        "failures": failures,
    }


def main() -> int:
    preflight = json.loads((EXP / "analysis/preflight.json").read_text(encoding="utf-8"))
    relation = head_relation(str(preflight["head"]))
    execution = json.loads((EXP / "qa/execution_summary.json").read_text(encoding="utf-8"))
    execution_ok = (
        execution.get("status") == "PASS"
        and execution.get("solver_solve_invocations") == 6
        and execution.get("exact_new_physical_solve_count") == 6
        and execution.get("reused_physical_case_count") == 2
        and execution.get("unauthorized_extra_solves") == 0
        and execution.get("failed_runs") == []
    )
    raw_records: dict[str, Any] = {}
    raw_failures: list[str] = []
    grid_hashes: set[str] = set()
    pre_hashes: dict[str, str] = {}
    reuse_manifest = json.loads((EXP / "REUSED_REFERENCE_MANIFEST.json").read_text(encoding="utf-8"))
    for case_id in ALL_CASES:
        path = raw_path(case_id)
        if not path.is_file():
            raw_failures.append(case_id + ": missing raw.csv")
            continue
        pre_hashes[case_id] = sha256(path)
        summary = read_raw(path)
        missing = sorted(set(expected_probes()) - set(summary.pop("headers")))
        unknown = sorted(set(missing) & OPTIONAL_UNKNOWN)
        missing_required = sorted(set(missing) - OPTIONAL_UNKNOWN)
        if summary["sample_count"] != 1999 or summary["first_timestamp_s"] != 0.0 or summary["last_timestamp_s"] != 1.999e-10:
            raw_failures.append(case_id + ": time/sample range mismatch")
        if not summary["finite_values"] or not summary["row_widths_valid"] or not summary["strictly_increasing_time"]:
            raw_failures.append(case_id + ": finite/width/monotonicity failure")
        if missing_required:
            raw_failures.append(case_id + ": missing required probes " + ",".join(missing_required))
        if case_id in REUSE_RUNS:
            expected_hash = reuse_manifest["references"][case_id]["artifacts"]["raw.csv"]["source_sha256"]
            if pre_hashes[case_id] != expected_hash:
                raw_failures.append(case_id + ": reused raw does not match source hash")
        grid_hashes.add(summary["stored_time_grid_sha256"])
        raw_records[case_id] = {
            "case_id": case_id,
            "path": str(path),
            "sha256": pre_hashes[case_id],
            "bytes": path.stat().st_size,
            **summary,
            "required_probe_status": "UNKNOWN" if unknown and not missing_required else ("PASS" if not missing else "FAIL"),
            "missing_probes": missing,
            "unknown_probes": unknown,
            "physical_solve_this_experiment": case_id in NEW_RUNS,
            "raw_immutable": True,
        }
    post_hashes = {case_id: sha256(raw_path(case_id)) for case_id in pre_hashes}
    raw_ok = not raw_failures and len(grid_hashes) == 1 and pre_hashes == post_hashes
    raw_qa = {
        "schema": "bjs400-l1-ibias-interaction-raw-qa-v1",
        "status": "PASS" if raw_ok else "FAIL",
        "artifact_validity": "VALID" if raw_ok else "INVALID",
        "experiment_id": EXP.name,
        "created_at_local": now(),
        "head": relation["head"],
        "execution_status": "PASS" if execution_ok else "FAIL",
        "new_physical_solve_count": 6,
        "reused_physical_case_count": 2,
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
    decks = deck_diff()
    provenance = {
        "schema": "bjs400-l1-ibias-interaction-provenance-v1",
        "experiment_id": EXP.name,
        "head_at_qa": relation["head"],
        "preflight": "analysis/preflight.json",
        "source_manifest": "SOURCE_MANIFEST.json",
        "reuse_manifest": "REUSED_REFERENCE_MANIFEST.json",
        "execution_summary": "qa/execution_summary.json",
        "solver": "build/josim-cli",
        "new_runs": {
            run_id: {
                "deck": str(deck_path(run_id)),
                "deck_sha256": sha256(deck_path(run_id)),
                "raw": str(raw_path(run_id)),
                "raw_sha256": pre_hashes.get(run_id),
                "metadata": str(EXP / "runs" / run_id / "metadata.json"),
                "run_log": str(EXP / "runs" / run_id / "run.log"),
            }
            for run_id in NEW_RUNS
        },
        "runs": {
            run_id: {
                "deck": str(deck_path(run_id)),
                "deck_sha256": sha256(deck_path(run_id)),
                "raw": str(raw_path(run_id)),
                "raw_sha256": pre_hashes.get(run_id),
                "metadata": str(EXP / "runs" / run_id / "metadata.json"),
                "run_log": str(EXP / "runs" / run_id / "run.log"),
                "physical_solve_this_experiment": True,
            }
            for run_id in NEW_RUNS
        },
        "reused_runs": reuse_manifest,
        "scientific_analysis_performed": False,
    }
    transformations = {
        "schema": "bjs400-l1-ibias-interaction-transformation-registry-v1",
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
