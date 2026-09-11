#!/usr/bin/env python3
"""Mechanical QA for selected-mask flat whole-run visualizations."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
PLOTTER = REPO / "scripts/josim-plot2.py"
RUN_IDS = ["ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P10_0111"]
STANDALONE_NAMES = ["SIGNAL_PATH.html", "BVM_STATE.html", "BVM_OUTPUT.html", "JSL_CHAIN.html", "QB_STATE.html", "JTL_CHAIN.html"]
COMPARISON_NAMES = ["RJ2P10_P11_P12_WEIGHT3.html", "RJ2P10_WEIGHT2_VS_WEIGHT3.html"]


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def check_entry(entry: dict[str, Any], failures: list[str]) -> None:
    output = REPO / entry["output_path"]
    if not output.is_file():
        failures.append(f"missing output: {entry['output_path']}")
        return
    if sha256(output) != entry.get("output_sha256"):
        failures.append(f"output hash mismatch: {entry['output_path']}")
    if entry.get("renderer") != str(PLOTTER.relative_to(REPO)):
        failures.append(f"renderer mismatch: {entry['output_path']}")
    if entry.get("layout") != "sep_comb" or entry.get("color") != "dark" or entry.get("phase_option") != "2pi":
        failures.append(f"plot style mismatch: {entry['output_path']}")
    if entry.get("window_ps") != [0.0, 200.0] or entry.get("window_semantics") != "whole-run raw timestamps; no focused window":
        failures.append(f"window mismatch: {entry['output_path']}")
    command = entry.get("command", [])
    if not isinstance(command, list) or str(PLOTTER) not in command or "-t" not in command or command[command.index("-t") + 1] != "sep_comb" or "-c" not in command or command[command.index("-c") + 1] != "dark" or "-j" not in command or command[command.index("-j") + 1] != "2pi":
        failures.append(f"plot command/style mismatch: {entry['output_path']}")
    source_paths = [REPO / path for path in entry.get("source_raw_paths", [])]
    source_hashes = entry.get("source_raw_sha256", [])
    for index, source in enumerate(source_paths):
        if not source.is_file():
            failures.append(f"missing source raw: {source}")
        elif index >= len(source_hashes) or sha256(source) != source_hashes[index]:
            failures.append(f"source raw hash mismatch: {source}")
    if entry.get("stage") == "standalone":
        if entry.get("input_mode") != "RAW_DIRECT" or entry.get("source_raw_paths") != [entry.get("input_path")]:
            failures.append(f"standalone is not raw-direct: {entry['output_path']}")
        if entry.get("temporary_input_sha256") is not None:
            failures.append(f"standalone has temporary input: {entry['output_path']}")
    elif entry.get("stage") == "comparison":
        input_path = Path(str(entry.get("input_path", "")))
        if not str(input_path).startswith("/tmp/bjs400-comparison-") or input_path.exists():
            failures.append(f"comparison temporary CSV was not deleted: {entry['output_path']}")
        if entry.get("input_mode") != "TEMPORARY_MERGED_COMPARISON":
            failures.append(f"comparison input mode mismatch: {entry['output_path']}")
        if not entry.get("comparison_cases") or entry.get("temporary_input_sha256") is None:
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
    if manifest.get("renderer") != "scripts/josim-plot2.py":
        failures.append("manifest renderer is not scripts/josim-plot2.py")
    if manifest.get("layout") != "sep_comb" or manifest.get("color") != "dark" or manifest.get("phase_option") != "2pi":
        failures.append("manifest plot style is not frozen")
    if manifest.get("whole_run_window_ps") != [0.0, 200.0] or manifest.get("focused_windows") != []:
        failures.append("manifest is not whole-run-only")
    if len(standalone) != 6 or len(comparisons) != 2:
        failures.append(f"entry count mismatch: standalone={len(standalone)} comparison={len(comparisons)}")
    for entry in standalone + comparisons:
        if isinstance(entry, dict):
            check_entry(entry, failures)
        else:
            failures.append("non-mapping visualization entry")
    experiment_prefix = EXP.relative_to(REPO).as_posix()
    expected_standalone = {
        f"{experiment_prefix}/plots/runs/{run_id}/{name}" for run_id in RUN_IDS for name in STANDALONE_NAMES
    }
    actual_standalone = {entry.get("output_path") for entry in standalone}
    if actual_standalone != expected_standalone:
        failures.append("standalone output paths are not exactly flat six-per-run")
    expected_comparison = {f"{experiment_prefix}/plots/comparison/{name}" for name in COMPARISON_NAMES}
    actual_comparison = {entry.get("output_path") for entry in comparisons}
    if actual_comparison != expected_comparison:
        failures.append("comparison output paths are not exactly the authorized 20")
    actual_html = {
        path.relative_to(EXP).as_posix()
        for path in (EXP / "plots").rglob("*.html")
    }
    expected_html = {path.removeprefix(experiment_prefix + "/") for path in expected_standalone | expected_comparison}
    if actual_html != expected_html:
        failures.append("plots contains extra/missing HTML artifacts")
    if list((EXP / "plots").rglob("*.csv")):
        failures.append("plot directory contains a duplicate CSV")
    if (EXP / "visualization/derived").exists():
        failures.append("standalone/comparison derived visualization directory exists")
    if any("window" in path.name.casefold() or "category" in path.parts for path in (EXP / "plots").rglob("*")):
        failures.append("focused/category plot artifact detected")
    qa = {
        "schema": "bjs400-rj2p10-weight3-flat-visualization-qa-v1",
        "experiment_id": EXP.name,
        "created_at_local": now(),
        "status": "PASS" if not failures else "FAIL",
        "standalone_html_count": len(standalone),
        "comparison_html_count": len(comparisons),
        "expected_standalone_html_per_run": 6,
        "expected_comparison_html": 2,
        "whole_run_only": True,
        "focused_window_plots": False,
        "standalone_raw_direct": True,
        "standalone_derived_csv": False,
        "comparison_temp_csv_retained": False,
        "flat_directory_structure": True,
        "renderer": "scripts/josim-plot2.py",
        "layout": "sep_comb",
        "color": "dark",
        "phase_option": "2pi",
        "raw_files_modified": 0,
        "physics_solve_count": 0,
        "scientific_analysis_performed": False,
        "failures": failures,
    }
    write_json(EXP / "qa/visualization_qa.json", qa)
    print(json.dumps({"status": qa["status"], "standalone_html": len(standalone), "comparison_html": len(comparisons), "failures": failures[:20], "scientific_analysis_performed": False}, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
