#!/usr/bin/env python3
"""Verify the combined Stage A/Stage B visualization manifest."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
PREFIX = EXP.relative_to(REPO).as_posix()
N3_SOURCE = "CLOSED_LOOP_N3_REFERENCE"
N3_REPLAY = "CLOSED_CURRENT_REPLAY_N3_0111_RJ2P12"
NEW_STANDALONE = {N3_SOURCE: ("01_SIGNAL_TIMING.html", "02_BVM_STATE.html", "03_SOURCE_BOUNDARY.html", "04_QB_STATE.html", "05_JTL_CHAIN.html", "06_TERMINAL.html"), N3_REPLAY: ("01_SIGNAL_TIMING.html", "04_QB_STATE.html", "05_JTL_CHAIN.html", "06_TERMINAL.html")}
NEW_COMPARISONS = ("CLOSED_VS_CLOSED_CURRENT_REPLAY_N3.html", "CLOSED_CURRENT_REPLAY_N2_VS_N3.html")


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    manifest = json.loads((EXP / "visualization/manifest.json").read_text(encoding="utf-8"))
    failures: list[str] = []
    if manifest.get("status") != "PASS" or manifest.get("standalone_entry_count") != 20 or manifest.get("comparison_entry_count") != 3:
        failures.append("combined manifest status/count mismatch")
    if manifest.get("renderer") != "scripts/josim-plot2.py" or manifest.get("layout") != "sep_comb" or manifest.get("color") != "dark" or manifest.get("phase_option") != "2pi" or manifest.get("whole_run_window_ps") != [0.0, 200.0]:
        failures.append("plot style/window mismatch")
    if manifest.get("stage_b", {}).get("outcome") != "CLOSED_BOUNDARY_CURRENT_REPLAY_REPRODUCES_N3_FOUR_RESPONSE":
        failures.append("Stage B visualization outcome marker missing")
    for entry in manifest.get("standalone_entries", []) + manifest.get("comparison_entries", []):
        output = REPO / entry["output_path"]
        if not output.is_file():
            failures.append(f"missing output: {entry['output_path']}")
            continue
        if sha256(output) != entry.get("output_sha256"):
            failures.append(f"output hash mismatch: {entry['output_path']}")
        if entry.get("window_ps") != [0.0, 200.0] or entry.get("renderer") != "scripts/josim-plot2.py":
            failures.append(f"plot metadata mismatch: {entry['output_path']}")
        for index, raw in enumerate(entry.get("source_raw_paths", [])):
            path = REPO / raw
            hashes = entry.get("source_raw_sha256", [])
            if not path.is_file() or index >= len(hashes) or sha256(path) != hashes[index]:
                failures.append(f"source hash mismatch: {raw}")
        if entry.get("stage") == "comparison":
            temp = Path(str(entry.get("input_path", "")))
            if not (str(temp).startswith("/tmp/bvm-closed-replay-comparison-") or str(temp).startswith("/tmp/bvm-closed-replay-stage-b-")) or temp.exists():
                failures.append(f"comparison temp CSV retained: {entry['output_path']}")
    expected_new = {f"{PREFIX}/visualization/plots/runs/{run}/{name}" for run, names in NEW_STANDALONE.items() for name in names}
    actual_new = {entry.get("output_path") for entry in manifest.get("standalone_entries", []) if entry.get("run_id") in NEW_STANDALONE}
    if actual_new != expected_new:
        failures.append("Stage B standalone output set mismatch")
    expected_comparison = {f"{PREFIX}/visualization/plots/comparison/{name}" for name in NEW_COMPARISONS}
    actual_comparison = {entry.get("output_path") for entry in manifest.get("comparison_entries", []) if entry.get("name") in {name.removesuffix('.html') for name in NEW_COMPARISONS}}
    if actual_comparison != expected_comparison:
        failures.append("Stage B comparison output set mismatch")
    if any(path.suffix == ".csv" for path in (EXP / "visualization/plots").rglob("*")):
        failures.append("plot CSV retained")
    qa = {"schema": "bvm-closed-boundary-current-replay-combined-visualization-qa-v1", "experiment_id": EXP.name, "created_at_local": now(), "status": "PASS" if not failures else "FAIL", "standalone_html_count": manifest.get("standalone_entry_count"), "comparison_html_count": manifest.get("comparison_entry_count"), "stage_b_outcome": manifest.get("stage_b", {}).get("outcome"), "whole_run_only": True, "temporary_comparison_csv_retained": False, "physics_solve_count": 0, "scientific_analysis_performed": True, "failures": failures}
    (EXP / "qa/visualization_qa_stage_b.json").write_text(json.dumps(qa, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": qa["status"], "standalone_html": qa["standalone_html_count"], "comparison_html": qa["comparison_html_count"], "failure_count": len(failures)}, ensure_ascii=False, indent=2))
    return 0 if qa["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
