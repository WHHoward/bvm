#!/usr/bin/env python3
"""Mechanical QA for the new experiment's V2.1 presentation artifacts."""

from __future__ import annotations

import csv
import hashlib
import json
import sys
import subprocess
from datetime import datetime, timezone
from pathlib import Path


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
CATEGORIES = {"01_SIGNAL_TIMING", "02_BVM_STATE", "03_JSL_CHAIN", "04_QB_STATE", "05_JTL_CHAIN"}
STANDALONE_COUNTS = {"01_SIGNAL_TIMING": 3, "02_BVM_STATE": 3, "03_JSL_CHAIN": 3, "04_QB_STATE": 4, "05_JTL_CHAIN": 2}
COMPARISON_WINDOWS = {
    category: set(windows)
    for category, windows in {
        "01_SIGNAL_TIMING": ("OVERVIEW_0_200ps", "SYSTEM_CRITICAL_101_135ps", "FINAL_READ_110_121ps"),
        "02_BVM_STATE": ("OVERVIEW_0_200ps", "SYSTEM_CRITICAL_101_135ps", "FINAL_READ_110_121ps"),
        "03_JSL_CHAIN": ("OVERVIEW_0_200ps", "SYSTEM_CRITICAL_101_135ps", "FINAL_READ_110_121ps"),
        "04_QB_STATE": ("OVERVIEW_0_200ps", "SYSTEM_CRITICAL_101_135ps", "FINAL_READ_110_121ps", "QB_110_130ps"),
        "05_JTL_CHAIN": ("OVERVIEW_0_200ps", "SYSTEM_CRITICAL_101_135ps", "FINAL_READ_110_121ps", "QB_JTL_110_130ps"),
    }.items()
}
FAMILIES = {
    "L1": ["L1_1P2", "L1_1P4", "L1_1P6", "L1_1P8", "L1_1P9", "L1_NOMINAL", "L1_2P1"],
    "IBIAS": ["IB_230", "IB_240", "IB_NOMINAL", "IB_260", "IB_270"],
    "RJ1": ["RJ1_8", "RJ1_10", "RJ1_NOMINAL", "RJ1_12P5", "RJ1_13", "RJ1_14", "RJ1_16"],
}
NEW_RUNS = {run_id for family in FAMILIES.values() for run_id in family if run_id.startswith(("L1_1P", "IB_", "RJ1_8", "RJ1_10", "RJ1_14", "RJ1_16"))}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def read_rows(path: Path) -> tuple[list[str], list[list[str]]]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.reader(stream)
        return next(reader), list(reader)


def check_entry(entry: dict[str, object], failures: list[str]) -> None:
    input_csv = Path(str(entry["input_csv"]))
    output = Path(str(entry["output_path"]))
    if not input_csv.is_file() or not output.is_file():
        failures.append(f"missing visualization artifact: {input_csv} / {output}")
        return
    if sha256(input_csv) != entry.get("input_sha256"):
        failures.append(f"input hash changed: {input_csv}")
    if sha256(output) != entry.get("output_sha256"):
        failures.append(f"output hash changed: {output}")
    if any(label.startswith("P(") for label in entry.get("signal_order_actual", [])) and "independently unwrapped" not in str(entry.get("transformation")):
        failures.append(f"phase transformation declaration missing: {output}")
    window = entry.get("window_ps")
    if not isinstance(window, list) or len(window) != 2:
        failures.append(f"window missing: {output}")
        return
    start, end = float(window[0]), float(window[1])
    header, rows = read_rows(input_csv)
    times = [float(row[0]) * 1e12 for row in rows]
    if not rows or min(times) < start or max(times) >= end or any(right <= left for left, right in zip(times, times[1:])):
        failures.append(f"window/grid invalid: {input_csv}")
    source_raw = Path(str(entry.get("source_raw_paths", [""])[0]))
    if not source_raw.is_file():
        failures.append(f"source raw missing: {source_raw}")
    else:
        if sha256(source_raw) != entry.get("source_raw_sha256", [None])[0]:
            failures.append(f"source raw hash changed: {source_raw}")
        _, source_rows = read_rows(source_raw)
        expected_times = [row[0] for row in source_rows if start <= float(row[0]) * 1e12 < end]
        if [row[0] for row in rows] != expected_times:
            failures.append(f"visualization is not exact stored-row slice: {input_csv}")


def run(mode: str) -> int:
    failures: list[str] = []
    standalone = mode == "standalone"
    manifest_path = EXP / "visualization" / ("manifest_standalone.json" if standalone else "manifest.json")
    qa_path = EXP / "visualization" / ("visualization_qa_standalone.json" if standalone else "visualization_qa.json")
    if not manifest_path.is_file():
        failures.append(f"missing manifest: {manifest_path}")
        manifest: dict[str, object] = {}
    else:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entries = list(manifest.get("standalone_entries", []))
    if not standalone:
        entries += list(manifest.get("comparison_entries", []))
    if {entry.get("category") for entry in entries} != CATEGORIES:
        failures.append("semantic category set is incomplete")
    for entry in entries:
        check_entry(entry, failures)
    standalone_entries = list(manifest.get("standalone_entries", []))
    for run_id in {item for family in FAMILIES.values() for item in family}:
        run_entries = [entry for entry in standalone_entries if entry.get("run_ids") == [run_id]]
        if len(run_entries) != 15:
            failures.append(f"standalone entry count for {run_id}: {len(run_entries)} != 15")
        for category, count in STANDALONE_COUNTS.items():
            category_entries = [entry for entry in run_entries if entry.get("category") == category]
            if len(category_entries) != count:
                failures.append(f"standalone {run_id}/{category} count {len(category_entries)} != {count}")
            if "OVERVIEW_0_200ps" not in {entry.get("window_name") for entry in category_entries}:
                failures.append(f"missing 0-200ps overview: {run_id}/{category}")
    if not standalone:
        comparison = list(manifest.get("comparison_entries", []))
        for family, run_ids in FAMILIES.items():
            family_entries = [entry for entry in comparison if entry.get("run_ids") == run_ids]
            if len(family_entries) != 17:
                failures.append(f"comparison {family} count {len(family_entries)} != 17")
            for category, required in COMPARISON_WINDOWS.items():
                got = {entry.get("window_name") for entry in family_entries if entry.get("category") == category}
                if got != required:
                    failures.append(f"comparison {family}/{category} windows mismatch")
                standalone_order = next((entry.get("signal_order_requested") for entry in standalone_entries if entry.get("category") == category), None)
                if any(entry.get("signal_order_requested") != standalone_order for entry in family_entries if entry.get("category") == category):
                    failures.append(f"comparison {family}/{category} signal ordering mismatch")
    qa = {
        "schema": "qb-l1-ibias-rj1-v2-1-visualization-qa-v1",
        "experiment_id": EXP.name,
        "version": "V2.1",
        "stage": mode,
        "status": "PASS" if not failures else "FAIL",
        "entry_count": len(entries),
        "standalone_entry_count": len(standalone_entries),
        "comparison_entry_count": len(manifest.get("comparison_entries", [])),
        "semantic_completeness_gates": {
            "A_input_boundary_declared": {"status": "PASS" if set(manifest.get("semantic_completeness", {})) == CATEGORIES else "FAIL", "categories_checked": sorted(CATEGORIES)},
            "B_output_boundary_declared": {"status": "PASS" if set(manifest.get("semantic_completeness", {})) == CATEGORIES else "FAIL", "categories_checked": sorted(CATEGORIES)},
            "C_standalone_overview_0_200ps": {"status": "PASS" if not any("overview" in failure for failure in failures) else "FAIL", "categories_checked": sorted(CATEGORIES)},
        },
        "raw_files_modified": 0,
        "physics_solve_count": 0,
        "scientific_analysis_performed": False,
        "extra_mechanism_plots_generated": False,
        "failures": failures,
        "created_at_local": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
    }
    qa_path.parent.mkdir(parents=True, exist_ok=True)
    qa_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": qa["status"], "stage": mode, "entry_count": len(entries), "failures": failures[:20]}, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) == 2 else "final"
    if mode not in {"standalone", "final"}:
        raise SystemExit("usage: visualization_qa.py [standalone|final]")
    return run(mode)


if __name__ == "__main__":
    raise SystemExit(main())
