#!/usr/bin/env python3
"""Mechanical QA for the bounded raw-direct visualization set."""

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
STATE = EXP / "screening/screening_state.json"


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
        failures.append("no standalone entries")
    if not comparisons:
        failures.append("comparison_required but no comparison entries")
    run_ids = {path.name for path in (EXP / "runs").iterdir() if path.is_dir()}
    entries_by_run: dict[str, int] = {run_id: 0 for run_id in run_ids}
    checked_outputs: set[Path] = set()
    phase_entries = 0
    for entry in standalone:
        raw = EXP / entry["input_raw"]
        output = REPO / entry["output_path"]
        if not raw.is_file() or entry.get("input_raw_sha256") != sha256(raw):
            failures.append(f"stale/missing standalone raw: {entry.get('run_id')}")
        if not output.is_file() or entry.get("output_sha256") != sha256(output):
            failures.append(f"stale/missing standalone HTML: {entry.get('output_path')}")
        if output in checked_outputs:
            failures.append(f"duplicate output path: {entry.get('output_path')}")
        checked_outputs.add(output)
        if entry.get("window_ps") != [0.0, 200.0] or entry.get("input_mode") != "RAW_DIRECT":
            failures.append(f"standalone window/input mode mismatch: {entry.get('run_id')}")
        if any(label.startswith("P(") for label in entry.get("labels", [])):
            phase_entries += 1
            if entry.get("phase_option") != "2pi":
                failures.append(f"phase option mismatch: {entry.get('output_path')}")
            if "rad/(2*pi)" not in entry.get("phase_convention", ""):
                failures.append(f"phase convention missing: {entry.get('output_path')}")
        run_id = entry.get("run_id")
        if run_id in entries_by_run:
            entries_by_run[run_id] += 1
        html = output.read_text(encoding="utf-8", errors="replace") if output.is_file() else ""
        if re.search(r'"title"\s*:\s*\{\s*"text"\s*:\s*"Unknown"', html):
            failures.append(f"Unknown axis/text in HTML: {entry.get('output_path')}")
        if "Phase (turns)" not in html or "rad\\u002f2pi" not in html:
            if any(label.startswith("P(") for label in entry.get("labels", [])):
                failures.append(f"phase axis conversion not visible in HTML: {entry.get('output_path')}")
    for run_id, count in entries_by_run.items():
        if count == 0:
            failures.append(f"no per-run visualization entry: {run_id}")
    for entry in comparisons:
        output = REPO / entry["output_path"]
        if not output.is_file() or entry.get("output_sha256") != sha256(output):
            failures.append(f"stale/missing comparison HTML: {entry.get('output_path')}")
        if entry.get("window_ps") != [108.0, 150.0] or entry.get("temporary_input_deleted") is not True:
            failures.append(f"focused comparison policy mismatch: {entry.get('output_path')}")
        if entry.get("input_mode") != "TEMPORARY_EXACT_GRID_MERGE_DELETED_AFTER_RENDER":
            failures.append(f"comparison input mode mismatch: {entry.get('output_path')}")
        if output in checked_outputs:
            failures.append(f"duplicate comparison output path: {entry.get('output_path')}")
        checked_outputs.add(output)
    temporary_files = list(Path("/tmp").glob("bvm-qb-screen-*.csv"))
    if temporary_files:
        failures.append("temporary comparison CSV remains: " + ", ".join(str(path) for path in temporary_files))
    derived_csv = [path for path in (EXP / "visualization").rglob("*.csv") if path.is_file()]
    if derived_csv:
        failures.append("derived visualization CSV remains: " + ", ".join(rel(path) for path in derived_csv))
    html_text = "".join((REPO / entry["output_path"]).read_text(encoding="utf-8", errors="replace") for entry in standalone if (REPO / entry["output_path"]).is_file())
    unknown_axis = re.search(r'"title"\s*:\s*\{\s*"text"\s*:\s*"Unknown"', html_text) is not None
    record: dict[str, Any] = {"schema": "bvm-full-closed-loop-qb-screening-visualization-qa-v1", "experiment_id": EXP.name, "created_at_local": now(), "status": "PASS" if not failures else "FAIL", "standalone_html_count": len(standalone), "comparison_html_count": len(comparisons), "phase_entry_count": phase_entries, "run_entry_counts": entries_by_run, "whole_run_plots_only": all(entry.get("window_ps") == [0.0, 200.0] for entry in standalone), "focused_comparison_window": [108.0, 150.0], "temporary_inputs_deleted": not temporary_files, "derived_csv_present": bool(derived_csv), "raw_direct_standalone": True, "semantic_completeness_gates": {"raw_direct": "PASS" if not failures else "FAIL", "phase_unit_label": "PASS" if phase_entries and not failures else "FAIL", "no_unknown_axis": "PASS" if not unknown_axis else "FAIL", "comparison_present": "PASS" if comparisons else "FAIL"}, "failures": failures}
    path = EXP / "qa/visualization_qa.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": record["status"], "standalone_html_count": len(standalone), "comparison_html_count": len(comparisons), "failures": failures[:30]}, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
