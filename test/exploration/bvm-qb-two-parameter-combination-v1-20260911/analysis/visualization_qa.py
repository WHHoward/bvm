#!/usr/bin/env python3
"""Mechanical QA for raw-direct combination visualizations."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
MANIFEST = EXP / "visualization/manifest.json"
STATE = EXP / "screening/combination_state.json"


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


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    state = json.loads(STATE.read_text(encoding="utf-8"))
    failures: list[str] = []
    standalone = manifest.get("standalone_entries", [])
    comparisons = manifest.get("comparison_entries", [])
    if not standalone:
        failures.append("no standalone visualization entries")
    if not comparisons:
        failures.append("no paired comparison visualization entries")
    run_ids = {path.name for path in (EXP / "runs").iterdir() if path.is_dir()}
    per_run = {run_id: 0 for run_id in run_ids}
    checked_outputs: set[Path] = set()
    phase_pages = 0
    for entry in standalone:
        raw = EXP / entry["input_raw"]
        output = REPO / entry["output_path"]
        if not raw.is_file() or entry.get("input_raw_sha256") != sha256(raw):
            failures.append(f"stale/missing raw input: {entry.get('run_id')}")
        if not output.is_file() or entry.get("output_sha256") != sha256(output):
            failures.append(f"stale/missing standalone output: {entry.get('output_path')}")
        if output in checked_outputs:
            failures.append(f"duplicate output: {entry.get('output_path')}")
        checked_outputs.add(output)
        if entry.get("window_ps") != [0.0, 200.0] or entry.get("input_mode") != "RAW_DIRECT":
            failures.append(f"standalone policy mismatch: {entry.get('output_path')}")
        if entry.get("run_id") in per_run:
            per_run[entry["run_id"]] += 1
        html = output.read_text(encoding="utf-8", errors="replace") if output.is_file() else ""
        if re.search(r'"title"\s*:\s*\{\s*"text"\s*:\s*"Unknown"', html):
            failures.append(f"Unknown axis title: {entry.get('output_path')}")
        if any(label.startswith("P(") for label in entry.get("labels", [])):
            phase_pages += 1
            if "Phase (turns)" not in html or "rad\\u002f2pi" not in html:
                failures.append(f"phase conversion label missing: {entry.get('output_path')}")
            if "rad/(2*pi)" not in entry.get("phase_convention", ""):
                failures.append(f"phase convention metadata missing: {entry.get('output_path')}")
    for run_id, count in per_run.items():
        if count == 0:
            failures.append(f"no standalone page for physical run: {run_id}")
    for entry in comparisons:
        output = REPO / entry["output_path"]
        if not output.is_file() or entry.get("output_sha256") != sha256(output):
            failures.append(f"stale/missing comparison output: {entry.get('output_path')}")
        if entry.get("temporary_input_deleted") is not True:
            failures.append(f"temporary comparison input not deleted: {entry.get('output_path')}")
        if entry.get("input_mode") != "TEMPORARY_EXACT_GRID_MERGE_DELETED_AFTER_RENDER":
            failures.append(f"comparison input policy mismatch: {entry.get('output_path')}")
        if output in checked_outputs:
            failures.append(f"duplicate output: {entry.get('output_path')}")
        checked_outputs.add(output)
    if list(Path("/tmp").glob("bvm-combination-*.csv")):
        failures.append("temporary comparison CSV remains")
    if list((EXP / "visualization").rglob("*.csv")):
        failures.append("derived visualization CSV remains")
    record = {"schema": "bvm-qb-two-parameter-combination-visualization-qa-v1", "experiment_id": EXP.name, "created_at_local": now(), "status": "PASS" if not failures else "FAIL", "standalone_html_count": len(standalone), "comparison_html_count": len(comparisons), "phase_page_count": phase_pages, "per_run_standalone_counts": per_run, "whole_run_standalone": all(entry.get("window_ps") == [0.0, 200.0] for entry in standalone), "focused_window": [108.0, 150.0], "raw_direct_standalone": True, "temporary_inputs_deleted": not list(Path("/tmp").glob("bvm-combination-*.csv")), "derived_csv_present": bool(list((EXP / "visualization").rglob("*.csv"))), "semantic_completeness_gates": {"raw_direct": "PASS" if not failures else "FAIL", "no_unknown_axis": "PASS" if not any("Unknown axis" in failure for failure in failures) else "FAIL", "comparison_present": "PASS" if comparisons else "FAIL"}, "failures": failures}
    path = EXP / "qa/visualization_qa.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": record["status"], "standalone_html_count": len(standalone), "comparison_html_count": len(comparisons), "failures": failures[:30]}, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
