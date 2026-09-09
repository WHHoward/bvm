#!/usr/bin/env python3
"""Minimal visualization QA for the interaction experiment."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
RUN_IDS = (
    "ARRAY_L1P20_IB250_0001",
    "ARRAY_L1P20_IB250_0011",
    "ARRAY_L1P16_IB250_0001",
    "ARRAY_L1P16_IB250_0011",
    "ARRAY_L1P16_IB260_0001",
    "ARRAY_L1P16_IB260_0011",
)
STANDALONE_NAMES = ("SIGNAL_PATH.html", "QB_STATE.html", "JTL_CHAIN.html")
COMPARISON_NAMES = ("0001_INTERACTION_COMPARE.html", "0011_INTERACTION_COMPARE.html")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def check_entry(entry: dict[str, Any], failures: list[str]) -> None:
    output = REPO / str(entry.get("output_path", ""))
    if not output.is_file():
        failures.append(f"missing output: {entry.get('output_path')}")
        return
    if sha256(output) != entry.get("output_sha256"):
        failures.append(f"output hash mismatch: {entry.get('output_path')}")
    for key, expected in (("renderer", "scripts/josim-plot2.py"), ("layout", "sep_comb"), ("color", "dark"), ("phase_option", "2pi")):
        if entry.get(key) != expected:
            failures.append(f"{key} mismatch: {entry.get('output_path')}")
    if entry.get("window_ps") != [0.0, 200.0] or entry.get("window_semantics") != "whole-run raw timestamps; no focused window":
        failures.append(f"window mismatch: {entry.get('output_path')}")
    command = entry.get("command", [])
    if not isinstance(command, list) or str(REPO / "scripts/josim-plot2.py") not in command:
        failures.append(f"renderer command mismatch: {entry.get('output_path')}")
    if entry.get("stage") == "standalone":
        if entry.get("input_mode") != "RAW_DIRECT":
            failures.append(f"standalone is not raw direct: {entry.get('output_path')}")
        if entry.get("source_raw_paths") != [entry.get("input_path")]:
            failures.append(f"standalone source/input mismatch: {entry.get('output_path')}")
        if entry.get("temporary_input_sha256") is not None:
            failures.append(f"standalone has temporary input: {entry.get('output_path')}")
    elif entry.get("stage") == "comparison":
        input_path = Path(str(entry.get("input_path", "")))
        if not str(input_path).startswith("/tmp/bjs400-interaction-") or input_path.exists():
            failures.append(f"comparison temporary input retained: {entry.get('output_path')}")
        if entry.get("input_mode") != "TEMPORARY_MERGED_COMPARISON" or entry.get("temporary_input_deleted") is not True:
            failures.append(f"comparison temporary provenance mismatch: {entry.get('output_path')}")
        if len(entry.get("comparison_cases", [])) != 4 or entry.get("temporary_input_sha256") is None:
            failures.append(f"comparison case provenance incomplete: {entry.get('output_path')}")
    else:
        failures.append(f"unknown visualization stage: {entry.get('stage')}")
    sources = entry.get("source_raw_paths", [])
    hashes = entry.get("source_raw_sha256", [])
    for index, source in enumerate(sources):
        path = REPO / source
        if not path.is_file():
            failures.append(f"missing source raw: {source}")
        elif index >= len(hashes) or sha256(path) != hashes[index]:
            failures.append(f"source raw hash mismatch: {source}")


def main() -> int:
    manifest = json.loads((EXP / "visualization/manifest.json").read_text(encoding="utf-8"))
    failures: list[str] = []
    standalone = manifest.get("standalone_entries", [])
    comparison = manifest.get("comparison_entries", [])
    if manifest.get("status") != "PASS":
        failures.append("manifest status is not PASS")
    if len(standalone) != 18 or len(comparison) != 2:
        failures.append(f"entry count mismatch: standalone={len(standalone)} comparison={len(comparison)}")
    if manifest.get("whole_run_window_ps") != [0.0, 200.0] or manifest.get("focused_windows") != []:
        failures.append("manifest is not whole-run only")
    if manifest.get("renderer") != "scripts/josim-plot2.py" or manifest.get("layout") != "sep_comb" or manifest.get("color") != "dark" or manifest.get("phase_option") != "2pi":
        failures.append("manifest style mismatch")
    for entry in standalone + comparison:
        if isinstance(entry, dict):
            check_entry(entry, failures)
        else:
            failures.append("non-mapping visualization entry")
    prefix = EXP.relative_to(REPO).as_posix()
    expected_standalone = {f"{prefix}/plots/runs/{run_id}/{name}" for run_id in RUN_IDS for name in STANDALONE_NAMES}
    expected_comparison = {f"{prefix}/plots/comparison/{name}" for name in COMPARISON_NAMES}
    if {entry.get("output_path") for entry in standalone} != expected_standalone:
        failures.append("standalone paths are not exactly 3 per new run")
    if {entry.get("output_path") for entry in comparison} != expected_comparison:
        failures.append("comparison paths are not exactly the two authorized files")
    actual_html = {path.relative_to(EXP).as_posix() for path in (EXP / "plots").rglob("*.html")}
    expected_html = {path.removeprefix(prefix + "/") for path in expected_standalone | expected_comparison}
    if actual_html != expected_html:
        failures.append("plots contains extra or missing HTML")
    if list((EXP / "plots").rglob("*.csv")):
        failures.append("plot directory contains duplicate CSV")
    if (EXP / "visualization/derived").exists():
        failures.append("derived visualization directory exists")
    for path in (EXP / "plots").rglob("*"):
        if "window" in path.name.casefold() or "category" in path.parts or "v2_1" in path.parts:
            failures.append(f"non-flat/focused plot artifact: {path}")
    qa = {
        "schema": "bjs400-l1-ibias-interaction-visualization-qa-v1",
        "experiment_id": EXP.name,
        "created_at_local": now(),
        "status": "PASS" if not failures else "FAIL",
        "standalone_html_count": len(standalone),
        "comparison_html_count": len(comparison),
        "expected_standalone_html_per_new_run": 3,
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
    print(json.dumps({"status": qa["status"], "standalone_html": len(standalone), "comparison_html": len(comparison), "failures": failures[:20], "scientific_analysis_performed": False}, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())

