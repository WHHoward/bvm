#!/usr/bin/env python3
"""Small independent arithmetic/raw-integrity check for the causal audit.

This checker does not consume ``metrics.json``.  It rereads the source raw
files, verifies exact grids and recomputes a few core comparisons directly.
It is a mechanical cross-check, not a second scientific event detector.
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "scripts"))
from bvmtools.compare import exact_time_grid_identity  # noqa: E402
from bvmtools.raw import read_csv  # noqa: E402
from bvmtools.phase import continuous_unwrap, window_indices  # noqa: E402


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
OUTPUT = EXP / "analysis/independent_check.json"
ARRAY_EXP = REPO / "test/exploration/bvmsim-4bvm-common-sl-12jsl-qb-integration-v1-20260904"
PASSIVE_EXP = REPO / "test/exploration/bvmsim-4bvm-paperlike-common-sl-accumulation-isolation-v1-20260904"
SINGLE_RAW = REPO / "test/exploration/bvmsim-jm2-connected-single-rloop-observability-v1-20260904/runs/S1-J-RLOOP/raw.csv"
MASKS = ("0000", "0001", "0010", "0100", "1000", "0011", "0111", "1100", "1110", "1111")
READ = (110e-12, 170e-12)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO.resolve()).as_posix()


def now_local() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def max_abs(values: list[float] | tuple[float, ...]) -> float:
    return max(abs(value) for value in values)


def read_sources() -> tuple[object, dict[str, object], dict[str, object]]:
    single = read_csv(SINGLE_RAW)
    array = {mask: read_csv(ARRAY_EXP / "runs" / mask / "raw.csv") for mask in MASKS}
    passive = {mask: read_csv(PASSIVE_EXP / "runs" / mask / "raw.csv") for mask in MASKS}
    return single, array, passive


def main() -> int:
    if OUTPUT.exists():
        raise SystemExit(f"refusing to overwrite independent check: {OUTPUT}")
    single, arrays, passive = read_sources()
    source_paths = [SINGLE_RAW]
    source_paths.extend(ARRAY_EXP / "runs" / mask / "raw.csv" for mask in MASKS)
    source_paths.extend(PASSIVE_EXP / "runs" / mask / "raw.csv" for mask in MASKS)
    duplicate_columns = {rel(path): read_csv(path).duplicate_columns for path in source_paths}
    array_grid = all(exact_time_grid_identity(arrays["0000"].time, arrays[mask].time) for mask in MASKS)
    passive_grid = all(exact_time_grid_identity(passive["0000"].time, passive[mask].time) for mask in MASKS)
    receiver_passive_grid = exact_time_grid_identity(arrays["0000"].time, passive["0000"].time)
    overlap_grid = tuple(arrays["0000"].time)
    read_indices = window_indices(overlap_grid, *READ)
    def read_values(trace: object, label: str) -> tuple[float, ...]:
        return trace.column(label)  # type: ignore[union-attr,return-value]
    def phase_values(trace: object, label: str) -> tuple[float, ...]:
        return continuous_unwrap(read_values(trace, label))
    def delta(left: object, right: object, label: str, phase: bool = False) -> tuple[float, ...]:
        left_values = phase_values(left, label) if phase else read_values(left, label)
        right_values = phase_values(right, label) if phase else read_values(right, label)
        return tuple(
            float(right_values[index]) - float(left_values[index])
            for index in read_indices
        )
    # COMMON_SL KCL is recomputed from the four BVM LSL branches and JSL01.
    g3 = arrays["1000"]
    branch_sum = tuple(
        sum(float(read_values(g3, f"I(L_SL|XBVM{instance})")[index]) for instance in range(1, 5))
        - float(read_values(g3, "I(B_JSL01)")[index])
        for index in read_indices
    )
    forward_active = delta(arrays["0001"], arrays["0011"], "I(L_SL|XBVM4)")
    passive_active = delta(passive["0001"], passive["0011"], "I(L_SL|XBVM4)")
    qb_phase = delta(arrays["0001"], arrays["0011"], "P(B_JS2|XBVM4)", phase=True)
    passive_phase = delta(passive["0001"], passive["0011"], "P(B_JS2|XBVM4)", phase=True)
    recomputed_nonzero = {
        "forward_active_victim_LSL_delta": max_abs(forward_active) > 0.0,
        "forward_active_victim_JS2_phase_delta_QB": max_abs(qb_phase) > 0.0,
        "forward_active_victim_JS2_phase_delta_passive": max_abs(passive_phase) > 0.0,
    }
    result = {
        "schema": "bvmsim-single-to-array-causal-audit-independent-check-v1",
        "created_at_local": now_local(),
        "source_raw_sha256": {rel(path): sha256(path) for path in source_paths},
        "duplicate_columns": duplicate_columns,
        "grid_checks": {
            "array_exact_across_masks": array_grid,
            "passive_exact_across_masks": passive_grid,
            "receiver_passive_exact": receiver_passive_grid,
            "read_sample_count": len(read_indices),
        },
        "recomputed_core": {
            "G3_COMMON_SL_KCL_READ_max_abs_A": max_abs(branch_sum),
            "forward_active_victim_LSL_delta_READ_max_abs_A": max_abs(forward_active),
            "forward_active_victim_JS2_phase_delta_READ_max_abs_rad": max_abs(qb_phase),
            "forward_active_victim_JS2_phase_delta_passive_READ_max_abs_rad": max_abs(passive_phase),
            "forward_active_victim_LSL_delta_QB_minus_passive_max_abs_A": max_abs(tuple(a - b for a, b in zip(forward_active, passive_active))),
            "phase_conversion_note": "JS2 values are continuous-unwrapped raw radians; no SFQ count is inferred",
            "nonzero_expected_checks": recomputed_nonzero,
        },
        "status": "PASS" if array_grid and passive_grid and receiver_passive_grid and not any(duplicate_columns.values()) and all(recomputed_nonzero.values()) else "FAIL",
    }
    OUTPUT.write_text(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "read_samples": len(read_indices)}, ensure_ascii=False))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
