#!/usr/bin/env python3
"""Verify that adding SL print probes preserves all parent raw waveforms."""

from __future__ import annotations

import json
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
EXP = HERE.parent
OLD_ROOT = EXP / "runs"
NEW_ROOT = EXP / "runs_sl_endpoints"
OUTPUT = EXP / "analysis/sl_endpoint_parity.json"
STATES = ("0000", "1000", "0100", "0010", "0001", "1111")

sys.path.insert(0, str(REPO / "scripts"))
from bvmtools.compare import compare_series, exact_time_grid_identity  # noqa: E402
from bvmtools.probes import flatten_probe_labels  # noqa: E402
from bvmtools.raw import read_csv  # noqa: E402
from bvmtools.sl_probes import historical_sensing_line_endpoint_probes  # noqa: E402


def write_once(path: Path, content: str) -> None:
    if path.exists():
        if path.read_text(encoding="utf-8") == content:
            return
        raise RuntimeError(f"refusing to overwrite parity artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main() -> int:
    expected_endpoints = list(flatten_probe_labels(historical_sensing_line_endpoint_probes()))
    results: dict[str, object] = {
        "schema": "bvmsim-4bvm-sl-endpoint-parity-v1",
        "comparison": "parent PHASE-B raw versus probe-extension raw",
        "interpolation": "none",
        "expected_endpoint_labels": expected_endpoints,
        "states": {},
    }
    failed = False
    for state in STATES:
        old = read_csv(OLD_ROOT / state / "raw.csv")
        new = read_csv(NEW_ROOT / state / "raw.csv")
        if old.duplicate_columns or new.duplicate_columns:
            raise RuntimeError(f"duplicate columns in state {state}: old={old.duplicate_columns}, new={new.duplicate_columns}")
        missing = [label for label in expected_endpoints if label not in new.headers]
        common = [label for label in old.headers if label != old.time_column and label in new.headers]
        series: dict[str, dict[str, object]] = {}
        for label in common:
            result = compare_series(old.time, old.column(label), new.time, new.column(label))
            result.pop("pointwise_difference", None)
            series[label] = result
        max_abs = max(float(item["max_abs_difference"]) for item in series.values()) if series else None
        rms_max = max(float(item["rms_difference"]) for item in series.values()) if series else None
        state_result = {
            "old_headers": len(old.headers),
            "new_headers": len(new.headers),
            "added_header_count": len(new.headers) - len(old.headers),
            "expected_endpoints_present": not missing,
            "missing_expected_endpoints": missing,
            "old_duplicate_columns": old.duplicate_columns,
            "new_duplicate_columns": new.duplicate_columns,
            "old_sample_count": old.sample_count,
            "new_sample_count": new.sample_count,
            "time_grid_exact": exact_time_grid_identity(old.time, new.time),
            "common_signal_count": len(common),
            "common_signal_max_abs_difference": max_abs,
            "common_signal_max_rms_difference": rms_max,
            "all_common_signals_numerically_identical": max_abs == 0.0 and rms_max == 0.0,
            "signals": series,
        }
        results["states"][state] = state_result  # type: ignore[index]
        if (
            missing
            or not state_result["time_grid_exact"]
            or not state_result["all_common_signals_numerically_identical"]
        ):
            failed = True
    results["status"] = "PROBE_EXTENSION_PARITY_PASS" if not failed else "PROBE_EXTENSION_PARITY_FAIL"
    write_once(OUTPUT, json.dumps(results, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"status": results["status"], "states": len(STATES), "output": str(OUTPUT)}))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
