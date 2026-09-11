#!/usr/bin/env python3
"""Mechanical QA for L3 high-side visualizations."""

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
STATE = EXP / "screening/l3_state.json"


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    state = json.loads(STATE.read_text(encoding="utf-8"))
    failures: list[str] = []
    standalone = manifest.get("standalone_entries", [])
    comparisons = manifest.get("comparison_entries", [])
    if not standalone:
        failures.append("no standalone entries")
    if not comparisons:
        failures.append("no focused L3 comparisons")
    if manifest.get("semantic_structure") != ["01_SIGNAL_TIMING", "02_BVM_STATE", "03_JSL_CHAIN", "04_QB_STATE", "05_JTL_CHAIN"]:
        failures.append("V2.1 semantic structure mismatch")
    run_ids = {path.name for path in (EXP / "runs").iterdir() if path.is_dir()}
    per_run = {run_id: 0 for run_id in run_ids}
    outputs: set[Path] = set()
    phase_pages = 0
    for entry in standalone:
        raw = EXP / entry["input_raw"]
        output = REPO / entry["output_path"]
        if not raw.is_file() or entry.get("input_raw_sha256") != sha256(raw):
            failures.append(f"stale raw: {entry.get('run_id')}")
        if not output.is_file() or entry.get("output_sha256") != sha256(output):
            failures.append(f"stale HTML: {entry.get('output_path')}")
        if output in outputs:
            failures.append(f"duplicate output: {entry.get('output_path')}")
        outputs.add(output)
        if entry.get("run_id") in per_run:
            per_run[entry["run_id"]] += 1
        html = output.read_text(encoding="utf-8", errors="replace") if output.is_file() else ""
        if re.search(r'"title"\s*:\s*\{\s*"text"\s*:\s*"Unknown"', html):
            failures.append(f"Unknown axis title: {entry.get('output_path')}")
        if any(label.startswith("P(") for label in entry.get("labels", [])):
            phase_pages += 1
            if "Phase (turns)" not in html or "rad\\u002f2pi" not in html:
                failures.append(f"phase conversion label missing: {entry.get('output_path')}")
    for run_id, count in per_run.items():
        if count == 0:
            failures.append(f"missing run standalone page: {run_id}")
    for entry in comparisons:
        output = REPO / entry["output_path"]
        if not output.is_file() or entry.get("output_sha256") != sha256(output):
            failures.append(f"stale comparison: {entry.get('output_path')}")
        if entry.get("window_ps") != [108.0, 150.0] or entry.get("temporary_input_deleted") is not True:
            failures.append(f"focused comparison policy mismatch: {entry.get('output_path')}")
        if output in outputs:
            failures.append(f"duplicate comparison output: {entry.get('output_path')}")
        outputs.add(output)
    temporary = list(Path("/tmp").glob("bvm-target-comparison-*.csv"))
    derived = list((EXP / "visualization").rglob("*.csv"))
    if temporary:
        failures.append("temporary L3 CSV remains")
    if derived:
        failures.append("derived visualization CSV remains")
    record: dict[str, Any] = {"schema": "bvm-qb-l3-bj2-targeted-combination-visualization-qa-v2.1", "experiment_id": EXP.name, "created_at_local": now(), "status": "PASS" if not failures else "FAIL", "standalone_html_count": len(standalone), "comparison_html_count": len(comparisons), "phase_page_count": phase_pages, "per_run_standalone_counts": per_run, "temporary_inputs_deleted": not temporary, "derived_csv_present": bool(derived), "raw_direct_standalone": True, "semantic_structure": manifest.get("semantic_structure"), "semantic_completeness_gates": {"raw_direct": "PASS" if not failures else "FAIL", "comparison_present": "PASS" if comparisons else "FAIL", "no_unknown_axis": "PASS" if not any("Unknown axis" in item for item in failures) else "FAIL"}, "failures": failures}
    output = EXP / "qa/visualization_qa.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": record["status"], "standalone_html_count": len(standalone), "comparison_html_count": len(comparisons), "failures": failures[:30]}, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
