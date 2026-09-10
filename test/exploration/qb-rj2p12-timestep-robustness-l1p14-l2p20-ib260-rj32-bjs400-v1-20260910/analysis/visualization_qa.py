#!/usr/bin/env python3
"""Mechanical QA for timestep whole-run visualizations."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
REUSE_RUNS = ("ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_DT0100_0001", "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_DT0100_0011")
REGISTERED_NEW_RUNS = ("ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_DT0050_0001", "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_DT0050_0011", "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_DT0025_0001", "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_DT0025_0011")
STANDALONE_NAMES = ("SIGNAL_PATH.html", "QB_STATE.html", "JTL_CHAIN.html")
COMPARISON_NAMES = ("TIMESTEP_0001_COMPARE.html", "TIMESTEP_0011_COMPARE.html")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def main() -> int:
    execution = json.loads((EXP / "qa/execution_summary.json").read_text(encoding="utf-8"))
    active_new = tuple(execution.get("run_order", REGISTERED_NEW_RUNS))
    active = REUSE_RUNS + active_new
    manifest = json.loads((EXP / "visualization/manifest.json").read_text(encoding="utf-8"))
    failures: list[str] = []
    standalone = manifest.get("standalone_entries", [])
    comparisons = manifest.get("comparison_entries", [])
    if manifest.get("status") != "PASS" or len(standalone) != len(active) * 3 or len(comparisons) != 2:
        failures.append("manifest status/count mismatch")
    if manifest.get("whole_run_window_ps") != [0.0, 200.0] or manifest.get("focused_windows") != [] or manifest.get("renderer") != "scripts/josim-plot2.py" or manifest.get("phase_option") != "2pi":
        failures.append("visualization protocol/style mismatch")
    expected = {f"{EXP.relative_to(REPO).as_posix()}/plots/cases/{run_id}/{name}" for run_id in active for name in STANDALONE_NAMES} | {f"{EXP.relative_to(REPO).as_posix()}/plots/comparison/{name}" for name in COMPARISON_NAMES}
    actual = {entry.get("output_path") for entry in standalone + comparisons if isinstance(entry, dict)}
    if actual != expected:
        failures.append("visualization output paths mismatch")
    for entry in standalone + comparisons:
        if not isinstance(entry, dict):
            failures.append("non-mapping manifest entry")
            continue
        output = REPO / str(entry.get("output_path", ""))
        if not output.is_file() or sha256(output) != entry.get("output_sha256"):
            failures.append(f"output missing/stale: {output}")
        expected_style = ("scripts/josim-plot2.py", "sep_comb") if entry.get("stage") == "standalone" else ("analysis/timestep_analysis.py", "metric_index")
        if (entry.get("renderer"), entry.get("layout")) != expected_style or entry.get("color") != "dark" or entry.get("phase_option") != "2pi":
            failures.append(f"style/renderer mismatch: {output}")
        for index, source_name in enumerate(entry.get("source_raw_paths", [])):
            source = REPO / source_name
            if not source.is_file() or sha256(source) != entry.get("source_raw_sha256", [])[index]:
                failures.append(f"source hash mismatch: {source}")
        if entry.get("stage") == "standalone" and (entry.get("input_mode") != "RAW_DIRECT" or entry.get("source_raw_paths") != [entry.get("input_path")]):
            failures.append(f"standalone is not raw direct: {output}")
        if entry.get("stage") == "comparison" and (entry.get("input_mode") != "METRIC_COMPARISON_INDEX" or entry.get("input_path") != f"{EXP.relative_to(REPO).as_posix()}/qa/timestep_qa.json" or entry.get("temporary_input_deleted") is not True):
            failures.append(f"comparison metric index provenance mismatch: {output}")
    actual_html = {path.relative_to(EXP).as_posix() for path in (EXP / "plots").rglob("*.html")}
    expected_html = {path.removeprefix(EXP.relative_to(REPO).as_posix() + "/") for path in expected}
    if actual_html != expected_html or list((EXP / "plots").rglob("*.csv")):
        failures.append("extra/missing HTML or retained plot CSV")
    result = {"schema": "bjs400-rj2p12-timestep-visualization-qa-v1", "experiment_id": EXP.name, "created_at_local": now(), "status": "PASS" if not failures else "FAIL", "standalone_html_count": len(standalone), "comparison_html_count": len(comparisons), "logical_case_count": len(active), "new_physical_case_count": len(active_new), "reused_case_count": len(REUSE_RUNS), "whole_run_only": True, "standalone_raw_direct": True, "comparison_metric_index": True, "comparison_pointwise_waveform_subtraction": False, "comparison_temp_csv_retained": False, "physics_solve_count": 0, "scientific_analysis_performed": False, "failures": failures}
    (EXP / "qa/visualization_qa.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "standalone_html": len(standalone), "comparison_html": len(comparisons), "failures": failures[:20], "scientific_analysis_performed": False}, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
