#!/usr/bin/env python3
"""Freeze the exact static render/probe contract for the authorized T1_C1 batch."""

from __future__ import annotations

import json
import hashlib
import re
from pathlib import Path

import run_platform as platform

SERIES = Path(__file__).resolve().parents[1]
OUT = SERIES / "analysis" / "t1_preflight_manifest.json"
FROZEN_INPUTS = (
    "scripts/run_platform.py",
    "scripts/audit_t1_batch.py",
    "scripts/build_t1_batch_comparison.py",
    "scripts/freeze_t1_batch_preflight.py",
    "tests/test_platform.py",
    "analysis/metric_spec.json",
    "experiment.yaml",
    "scripts/josim-plot2.py",
)
MATRIX = (
    ("T1_C1_Q0", "00", "00", "QUIET"),
    ("T1_C1_Q1", "10", "10", "QUIET"),
    ("T1_C1_Q2", "01", "10", "QUIET"),
    ("T1_C1_Q3", "11", "10", "QUIET"),
    ("T1_C1_P0", "00", "00", "PULSE"),
    ("T1_C1_P1", "10", "10", "PULSE"),
    ("T1_C1_P2", "01", "10", "PULSE"),
    ("T1_C1_P3", "11", "10", "PULSE"),
)


def main() -> int:
    if OUT.exists():
        raise FileExistsError(f"refusing to overwrite frozen preflight manifest: {OUT}")
    if max((int(match.group(1)) for path in platform.RUNS.glob("A[0-9][0-9][0-9]_*")
            if (match := re.match(r"A(\d{3})_", path.name))), default=0) != 18:
        raise RuntimeError("expected immutable history A001-A018 before T1_C1 batch")
    first_id = 19
    solver = platform._solver_info()
    frozen_inputs = {
        relative: platform.sha256(
            platform.REPO / relative if relative == "scripts/josim-plot2.py"
            else SERIES / relative
        )
        for relative in FROZEN_INPUTS
    }
    rows = []
    preview_run = platform.RUNS / "A000_T1_C1_PREFLIGHT"
    for offset, (preset, row_bits, col_bits, clock_mode) in enumerate(MATRIX):
        case, stimulus = platform.load_config(preset)
        rendered = platform.render(case, stimulus, preview_run)
        expected_id = f"A{first_id + offset:03d}_{preset}"
        expected_active = [
            cell for cell in ("R1C1", "R1C2", "R2C1", "R2C2")
            if row_bits[int(cell[1]) - 1] == "1" and col_bits[int(cell[3]) - 1] == "1"
        ]
        if (case["OUTPUT_MODE"] != "T1_C1" or case["OUTPUT_TOPOLOGY"] != "COLUMN_MERGE"
                or case["ROW_BITS"] != row_bits or case["COL_BITS"] != col_bits
                or case["T1_CLK_MODE"] != clock_mode
                or rendered["static_qa"]["status"] != "PASS"
                or rendered["topology"]["cell_selection"]["active_crosspoints"] != expected_active
                or len(platform.plot_page_plan(rendered["topology"], rendered["probes"])) != 4):
            raise RuntimeError(f"static preflight render mismatch for {preset}")
        rows.append({
            "preset": preset, "expected_run_id": expected_id,
            "row_bits": row_bits, "column_bits": col_bits,
            "active_crosspoints": expected_active, "clock_mode": clock_mode,
            "effective_user_case": case, "effective_stimulus": stimulus,
            "deck_sha256": hashlib.sha256(rendered["deck"].encode()).hexdigest(),
            "stimulus_inc_sha256": hashlib.sha256(
                rendered["stimulus_text"].encode()).hexdigest(),
            "source_sha256": {role: item["sha256"] for role, item in rendered["sources"].items()},
            "topology_manifest": rendered["topology"],
            "probe_manifest": rendered["probes"],
            "static_qa": rendered["static_qa"],
            "estimated_raw_bytes": platform.estimate_raw_bytes(
                rendered["probes"]["signal_count"]),
            "planned_physical_solve_count": 1,
        })
    manifest = {
        "schema": "bvm-2x2-t1-c1-preflight-v1",
        "batch_id": "BVM2X2_T1_C1_20261008",
        "parent_head": platform._git_head(),
        "solver": solver,
        "frozen_input_sha256": frozen_inputs,
        "authorized_physical_solve_count": 8,
        "static_render_solve_count": 0,
        "execution_order": [row["preset"] for row in rows],
        "expected_run_ids": [row["expected_run_id"] for row in rows],
        "conditions": rows,
        "time_step": "0.01p", "stop_time": "250p",
        "raw_estimate_method": "A018 raw-byte/probe ratio plus 15 percent width margin",
        "interpretation": "mechanical QA and arithmetic only; scientific interpretation not performed",
        "automatic_follow_up": False,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PREFLIGHT_MANIFEST_PASS", "manifest": str(OUT.relative_to(SERIES)),
                      "sha256": platform.sha256(OUT), "preset_count": len(rows),
                      "expected_run_ids": manifest["expected_run_ids"],
                      "probe_counts": {row["preset"]: row["probe_manifest"]["signal_count"]
                                       for row in rows},
                      "estimated_raw_bytes": {row["preset"]: row["estimated_raw_bytes"]
                                              for row in rows}}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
