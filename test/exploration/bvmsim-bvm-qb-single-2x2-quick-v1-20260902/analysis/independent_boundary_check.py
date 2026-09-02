#!/usr/bin/env python3
"""Independently recompute the principal A001 phase/area quantities.

This check deliberately does not import the Boundary reassessment module.  It
uses the shared raw reader, phase unwrapping, and actual-grid integration to
recompute the already-recorded event intervals.  It never invokes JoSIM and
never writes a raw CSV.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
import sys


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

from bvmtools.phase import TAU, continuous_unwrap, window_indices  # noqa: E402
from bvmtools.raw import read_csv  # noqa: E402
from bvmtools.waveform import trapezoid_integral  # noqa: E402


PHI0 = 2.067833848e-15
EXPECTED_RAW_SHA256 = {
    "S0-R": "a8e8183d864b8170bf29074644b467d1b00613f3848b7e25f0f4b1059237d1f3",
    "S1-R": "ac622d6c343b3edf18b656620c1df4a9263b37d117e6d48f65cc2a3399a1d904",
    "S0-J": "8844cd26ee3f5d4058ea5f7fde34f995b8c5d09a1b5f4ab9aebed3d9ca7cbeeb",
    "S1-J": "95042595e9c8ba9c82af1f7f9e8bd6130214405d8c8804ab4912d92bedae8b21",
}
CONDITIONS = {
    condition: EXP / f"runs/A001/{condition}/raw.csv"
    for condition in EXPECTED_RAW_SHA256
}


def record_targets(metrics: dict[str, object]) -> list[dict[str, object]]:
    b2 = metrics["B2"]  # type: ignore[index]
    b3 = metrics["B3"]  # type: ignore[index]
    targets: list[dict[str, object]] = []
    b2_principal = b2["S1-J"]["local_response"]["principal"]  # type: ignore[index]
    targets.append(
        {
            "name": "B2 S1-J BJ2",
            "condition": "S1-J",
            "phase_label": "P(BJ2|XBQ1)",
            "voltage_label": "V(BJ2|XBQ1)",
            "principal": b2_principal,
        }
    )
    for stage in b3["S1-J_stages"]:  # type: ignore[index]
        targets.append(
            {
                "name": f"B3 S1-J {stage['stage']} B02",
                "condition": "S1-J",
                "phase_label": stage["local_response"]["phase_label"],
                "voltage_label": stage["local_response"]["voltage_label"],
                "principal": stage["local_response"]["principal"],
            }
        )
    return targets


def exact_grid(left: tuple[float, ...], right: tuple[float, ...]) -> bool:
    return left == right


def recompute_target(target: dict[str, object], metrics: dict[str, object]) -> dict[str, object]:
    condition = str(target["condition"])
    trace = read_csv(CONDITIONS[condition])
    phase_label = str(target["phase_label"])
    voltage_label = str(target["voltage_label"])
    principal = target["principal"]
    if not isinstance(principal, dict):
        raise ValueError(f"missing principal interval for {target['name']}")
    start = int(principal["measure_start_index"])
    end = int(principal["measure_end_index"])
    if not (0 <= start < end < trace.sample_count):
        raise ValueError(f"invalid interval for {target['name']}: {start}..{end}")

    phase = continuous_unwrap(trace.column(phase_label))
    phase_delta_rad = phase[end] - phase[start]
    phase_turns = phase_delta_rad / TAU
    times = trace.time[start : end + 1]
    voltage = trace.column(voltage_label)[start : end + 1]
    voltage_area_wb = trapezoid_integral(voltage, times)
    voltage_area_turns = voltage_area_wb / PHI0
    expected_phase = float(principal["phase_delta_turns"])
    expected_area = float(principal["voltage_area_turns"])
    expected_residual = float(principal["signed_phase_area_residual_turns"])
    row = {
        "name": target["name"],
        "condition": condition,
        "phase_label": phase_label,
        "voltage_label": voltage_label,
        "measure_start_index": start,
        "measure_end_index": end,
        "measure_start_ps": trace.time[start] * 1.0e12,
        "measure_end_ps": trace.time[end] * 1.0e12,
        "recomputed_phase_delta_rad": phase_delta_rad,
        "recomputed_phase_delta_turns": phase_turns,
        "recomputed_voltage_area_wb": voltage_area_wb,
        "recomputed_voltage_area_turns": voltage_area_turns,
        "recomputed_signed_residual_turns": phase_turns - voltage_area_turns,
        "metric_phase_abs_error_turns": abs(phase_turns - expected_phase),
        "metric_area_abs_error_turns": abs(voltage_area_turns - expected_area),
        "metric_residual_abs_error_turns": abs((phase_turns - voltage_area_turns) - expected_residual),
        "metric_source": "analysis/boundary_metrics.json principal interval; arithmetic independently recomputed",
    }
    for key in ("metric_phase_abs_error_turns", "metric_area_abs_error_turns", "metric_residual_abs_error_turns"):
        if float(row[key]) > 1.0e-12:
            raise AssertionError(f"{target['name']} mismatch in {key}: {row[key]}")
    return row


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--timestamp", default=None)
    args = parser.parse_args()
    timestamp = args.timestamp or datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    metrics_path = EXP / "analysis/boundary_metrics.json"
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    traces = {condition: read_csv(path) for condition, path in CONDITIONS.items()}
    raw_hashes = {
        condition: hashlib.sha256(path.read_bytes()).hexdigest()
        for condition, path in CONDITIONS.items()
    }
    base_time = traces["S0-R"].time
    grid_identity = all(exact_grid(base_time, trace.time) for trace in traces.values())
    if not grid_identity:
        raise AssertionError("A001 time grids are not exactly identical")
    if raw_hashes != EXPECTED_RAW_SHA256:
        raise AssertionError(f"A001 raw hash mismatch: {raw_hashes}")

    rows = [recompute_target(target, metrics) for target in record_targets(metrics)]
    output = {
        "schema_version": "INDEPENDENT_BOUNDARY_CHECK_V1",
        "generated_at": timestamp,
        "analysis_mode": "analysis-only; no JoSIM invocation; no raw rewrite",
        "raw_hashes": raw_hashes,
        "all_four_time_grids_exactly_identical": grid_identity,
        "target_count": len(rows),
        "targets": rows,
        "max_phase_abs_error_turns": max(row["metric_phase_abs_error_turns"] for row in rows),
        "max_area_abs_error_turns": max(row["metric_area_abs_error_turns"] for row in rows),
        "max_residual_abs_error_turns": max(row["metric_residual_abs_error_turns"] for row in rows),
        "status": "PASS",
    }
    output_path = EXP / "analysis/independent_boundary_check.json"
    output_path.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {output_path.relative_to(REPO)}")
    print(
        "status=PASS "
        f"targets={len(rows)} "
        f"max_phase_error={output['max_phase_abs_error_turns']:.3e} turns "
        f"max_area_error={output['max_area_abs_error_turns']:.3e} turns"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
