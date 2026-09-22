#!/usr/bin/env python3
"""Analyze one generated Uxxx case using its stimulus-derived windows."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

SERIES = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERIES / "scripts"))
import analyze as engine  # noqa: E402


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def configure_windows(manifest: dict) -> None:
    windows = {name: (float(bounds[0]), float(bounds[1])) for name, bounds in manifest["windows"].items()}
    engine.WINDOWS = windows
    engine.STATE_WINDOWS = tuple(name for name in ("write0_50_61", "zero_read_control_70_81", "write1_90_101", "settle_101_110", "final_read_110_121", "recovery_121_130", "tail_150_200") if name in windows)
    engine.R_WINDOW = "final_read_110_121"
    engine.R_RECOVERY = "recovery_121_130"


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze one generated USER_CASE case")
    parser.add_argument("--case-root", required=True)
    args = parser.parse_args()
    case_root = Path(args.case_root).resolve()
    manifest = json.loads((case_root / "case_manifest.json").read_text(encoding="utf-8"))
    configure_windows(manifest)
    result = engine.analyze_case(case_root)
    analysis_dir = case_root / "analysis"
    qa_dir = case_root / "qa"
    analysis_dir.mkdir(exist_ok=True)
    qa_dir.mkdir(exist_ok=True)
    write_json(analysis_dir / "case_metrics.json", {"schema": "bvm-rloop-user-case-metrics-v1", "case": result, "windows": manifest["windows"], "scientific_interpretation_performed": False})
    engine.write_window_csv(result["window_rows"], analysis_dir / "per_signal_window_metrics.csv")
    population_rows = [{"mask": item["mask"], "run_id": item["run_id"], **item["metrics"]} for item in result["population"]]
    engine.write_window_csv(population_rows, analysis_dir / "population_metrics.csv")
    qa_rows = [{"run_id": row["run_id"], **row} for row in result["qa"]]
    raw_qa = {"schema": "bvm-rloop-user-case-raw-qa-v1", "status": "PASS" if all(row["status"] == "PASS" for row in qa_rows) else "FAIL", "run_count": len(qa_rows), "rows": qa_rows, "raw_immutable": True}
    write_json(qa_dir / "raw_qa.json", raw_qa)
    manifest_out = {"schema": "bvm-rloop-user-case-analysis-manifest-v1", "case_id": manifest["case_id"], "array_size": manifest.get("array_size", manifest["parameters"].get("ARRAY_SIZE", 4)), "windows": manifest["windows"], "raw_qa": str((qa_dir / "raw_qa.json").relative_to(SERIES)).replace("\\", "/"), "case_metrics": str((analysis_dir / "case_metrics.json").relative_to(SERIES)).replace("\\", "/"), "window_metrics": str((analysis_dir / "per_signal_window_metrics.csv").relative_to(SERIES)).replace("\\", "/"), "population_metrics": str((analysis_dir / "population_metrics.csv").relative_to(SERIES)).replace("\\", "/"), "scientific_interpretation_performed": False, "automatic_follow_up": False}
    write_json(analysis_dir / "analysis_manifest.json", manifest_out)
    status = "ANALYSIS_COMPLETE_AWAITING_SCIENTIFIC_REVIEW" if raw_qa["status"] == "PASS" else "ARTIFACT_INVALID"
    write_json(case_root / "result.json", {"schema": "bvm-rloop-user-case-result-v1", "case_id": manifest["case_id"], "array_size": manifest.get("array_size", manifest["parameters"].get("ARRAY_SIZE", 4)), "status": status, "artifact_status": "VALID" if raw_qa["status"] == "PASS" else "INVALID", "physical_solve_count": manifest["physical_solve_count"], "scientific_interpretation_performed": False, "automatic_follow_up": False})
    print(json.dumps({"status": raw_qa["status"], "case_id": manifest["case_id"], "physical_solve_count": manifest["physical_solve_count"], "scientific_interpretation": "NOT_PERFORMED"}, ensure_ascii=False, indent=2))
    return 0 if raw_qa["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
