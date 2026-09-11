#!/usr/bin/env python3
"""Verify the registered raw-direct and temporary-comparison visualizations."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
PLOTTER = "scripts/josim-plot2.py"
PASSIVE = ("PASSIVE_N2_0011", "PASSIVE_N3_0111", "PASSIVE_N4_1111")
REPLAY = ("REPLAY_N2_0011_RJ2P12", "REPLAY_N3_0111_RJ2P12", "REPLAY_N4_1111_RJ2P12")
RUNS = PASSIVE + REPLAY
STANDALONE_NAMES = {run: ("01_SIGNAL_TIMING.html", "02_BVM_STATE.html", "03_JSL_CHAIN.html") if run in PASSIVE else ("01_SIGNAL_TIMING.html", "04_QB_STATE.html", "05_JTL_CHAIN.html", "06_TERMINAL.html") for run in RUNS}
COMPARISON_NAMES = ("PASSIVE_SOURCE_N2_N4.html", "QB_REPLAY_N2_N4.html", "JTL_REPLAY_N2_N4.html", "TERMINAL_REPLAY_N2_N4.html", "CLOSED_VS_REPLAY_N2.html", "CLOSED_VS_REPLAY_N3.html", "CLOSED_VS_REPLAY_N4.html")


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def check_entry(entry: dict[str, Any], failures: list[str]) -> None:
    output = REPO / entry["output_path"]
    if not output.is_file():
        failures.append(f"missing plot: {entry['output_path']}")
        return
    if sha256(output) != entry.get("output_sha256"):
        failures.append(f"plot hash mismatch: {entry['output_path']}")
    if entry.get("renderer") != PLOTTER or entry.get("layout") != "sep_comb" or entry.get("color") != "dark" or entry.get("phase_option") != "2pi":
        failures.append(f"plot style mismatch: {entry['output_path']}")
    if entry.get("window_ps") != [0.0, 200.0] or entry.get("window_semantics") != "whole-run raw timestamps; no focused window":
        failures.append(f"plot window mismatch: {entry['output_path']}")
    source_hashes = entry.get("source_raw_sha256", [])
    for index, raw_path in enumerate(entry.get("source_raw_paths", [])):
        source = REPO / raw_path
        if not source.is_file():
            failures.append(f"missing plot source: {raw_path}")
        elif index >= len(source_hashes) or sha256(source) != source_hashes[index]:
            failures.append(f"plot source hash mismatch: {raw_path}")
    command = entry.get("command", [])
    if not isinstance(command, list) or "-t" not in command or command[command.index("-t") + 1] != "sep_comb" or "-c" not in command or command[command.index("-c") + 1] != "dark" or "-j" not in command or command[command.index("-j") + 1] != "2pi":
        failures.append(f"plot command style mismatch: {entry['output_path']}")
    if entry.get("stage") == "standalone":
        if entry.get("input_mode") != "RAW_DIRECT" or entry.get("input_path") != entry.get("input_raw") or entry.get("source_raw_paths") != [entry.get("input_raw")]:
            failures.append(f"standalone is not raw-direct: {entry['output_path']}")
        if entry.get("temporary_input_sha256") is not None:
            failures.append(f"standalone has temporary input: {entry['output_path']}")
    elif entry.get("stage") == "comparison":
        temp = Path(str(entry.get("input_path", "")))
        if not str(temp).startswith("/tmp/bvm-mechanism-comparison-") or temp.exists():
            failures.append(f"comparison temporary CSV retained: {entry['output_path']}")
        if entry.get("input_mode") != "TEMPORARY_MERGED_COMPARISON" or entry.get("temporary_input_sha256") is None:
            failures.append(f"comparison provenance incomplete: {entry['output_path']}")
    else:
        failures.append(f"unknown visualization stage: {entry.get('stage')}")


def main() -> int:
    manifest_path = EXP / "visualization/manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    failures: list[str] = []
    standalone = manifest.get("standalone_entries", [])
    comparisons = manifest.get("comparison_entries", [])
    if manifest.get("status") != "PASS":
        failures.append("manifest status is not PASS")
    if manifest.get("renderer") != PLOTTER or manifest.get("layout") != "sep_comb" or manifest.get("color") != "dark" or manifest.get("phase_option") != "2pi":
        failures.append("manifest style is not frozen")
    if manifest.get("whole_run_window_ps") != [0.0, 200.0] or manifest.get("focused_windows") != []:
        failures.append("manifest is not whole-run only")
    if len(standalone) != 21 or len(comparisons) != 7:
        failures.append(f"entry count mismatch: {len(standalone)} standalone, {len(comparisons)} comparisons")
    for entry in standalone + comparisons:
        if isinstance(entry, dict):
            check_entry(entry, failures)
        else:
            failures.append("non-mapping visualization entry")
    prefix = EXP.relative_to(REPO).as_posix()
    expected_standalone = {f"{prefix}/visualization/plots/runs/{run}/{name}" for run, names in STANDALONE_NAMES.items() for name in names}
    expected_comparison = {f"{prefix}/visualization/plots/comparison/{name}" for name in COMPARISON_NAMES}
    if {entry.get("output_path") for entry in standalone} != expected_standalone:
        failures.append("standalone output set mismatch")
    if {entry.get("output_path") for entry in comparisons} != expected_comparison:
        failures.append("comparison output set mismatch")
    actual_html = {path.relative_to(EXP).as_posix() for path in (EXP / "visualization/plots").rglob("*.html")}
    expected_html = {path.removeprefix(prefix + "/") for path in expected_standalone | expected_comparison}
    if actual_html != expected_html:
        failures.append("visualization plot directory has extra/missing HTML")
    if list((EXP / "visualization/plots").rglob("*.csv")):
        failures.append("temporary comparison CSV found under visualization/plots")
    qa = {"schema": "bvm-population-passive-source-replay-visualization-qa-v1", "experiment_id": EXP.name, "created_at_local": now(), "status": "PASS" if not failures else "FAIL", "standalone_html_count": len(standalone), "comparison_html_count": len(comparisons), "whole_run_only": True, "focused_window_plots": False, "standalone_raw_direct": True, "comparison_temp_csv_retained": False, "raw_files_modified": 0, "physics_solve_count": 0, "scientific_analysis_performed": False, "failures": failures}
    output = EXP / "qa/visualization_qa.json"
    output.write_text(json.dumps(qa, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": qa["status"], "standalone_html": len(standalone), "comparison_html": len(comparisons), "failure_count": len(failures), "scientific_analysis_performed": False}, ensure_ascii=False, indent=2))
    return 0 if qa["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
