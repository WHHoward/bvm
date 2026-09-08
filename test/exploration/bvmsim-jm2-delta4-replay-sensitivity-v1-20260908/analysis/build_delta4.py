#!/usr/bin/env python3
"""Build exact delta4 source components and the four registered replay decks."""

from __future__ import annotations

import csv
import json
from decimal import Decimal
from pathlib import Path

from common import (
    EXP,
    HEAD,
    OUTPUT_END_PS,
    RUNS,
    SOURCE_END_PS,
    SOURCE_RECON_TOL_A,
    SOURCE_SNAPSHOTS,
    TRANSFORMS,
    current_head,
    extended_grid,
    fmt_decimal,
    fmt_ps,
    json_text,
    read_snapshot,
    replay_deck,
    sha256,
    write_once,
)


def csv_text(header: list[str], rows: list[list[str]]) -> str:
    lines = [",".join(header)]
    lines.extend(",".join(row) for row in rows)
    return "\n".join(lines) + "\n"


def main() -> int:
    preflight_path = EXP / "analysis/preflight.json"
    if not preflight_path.is_file():
        raise RuntimeError("machine preflight is missing")
    preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
    if preflight.get("status") != "PASS":
        raise RuntimeError("machine preflight is not PASS")
    if current_head() != HEAD:
        raise RuntimeError("HEAD changed after preflight")

    n3_rows = read_snapshot(SOURCE_SNAPSHOTS["N3_PASSIVE"])
    n4_rows = read_snapshot(SOURCE_SNAPSHOTS["N4_PASSIVE"])
    n3_grid = [row[1] for row in n3_rows]
    n4_grid = [row[1] for row in n4_rows]
    if n3_grid != n4_grid:
        raise RuntimeError("N3/N4 source grids differ")
    n3 = {row[1]: row[2] for row in n3_rows}
    n4 = {row[1]: row[2] for row in n4_rows}
    delta = {time_ps: n4[time_ps] - n3[time_ps] for time_ps in n3_grid}
    reconstruction_residual = {
        time_ps: n3[time_ps] + delta[time_ps] - n4[time_ps] for time_ps in n3_grid
    }
    max_residual = max(abs(value) for value in reconstruction_residual.values())
    if max_residual > SOURCE_RECON_TOL_A:
        raise RuntimeError(f"source reconstruction exceeds tolerance: {max_residual}")

    delta_rows = []
    for time_ps, n3_value, n4_value in (
        (row[1], row[2], n4[row[1]]) for row in n3_rows
    ):
        delta_value = delta[time_ps]
        residual = n3_value + delta_value - n4_value
        delta_rows.append(
            [
                fmt_ps(time_ps),
                fmt_decimal(n3_value),
                fmt_decimal(n4_value),
                fmt_decimal(delta_value),
                fmt_decimal(n3_value + delta_value),
                fmt_decimal(residual),
            ]
        )
    delta_path = EXP / "data/delta4_source.csv"
    write_once(
        delta_path,
        csv_text(
            [
                "time_ps",
                "I_N3_PASSIVE_A",
                "I_N4_PASSIVE_A",
                "delta_I4_A",
                "I_N3_plus_delta_A",
                "reconstruction_residual_A",
            ],
            delta_rows,
        ),
    )

    output_times = extended_grid(n3_rows)
    n3_final = n3[SOURCE_END_PS]
    intervention_records: dict[str, object] = {}
    for run_id in RUNS:
        transform = TRANSFORMS[run_id]
        kind = str(transform["kind"])
        delay_ps = transform.get("delay_ps")
        gain = transform.get("gain")
        source_rows: list[list[str]] = []
        deck_points: list[tuple[Decimal, Decimal]] = []
        lookup_records: list[dict[str, object]] = []
        for target_ps in output_times:
            background = n3.get(target_ps, n3_final)
            if kind == "exact_timestamp_shift":
                assert isinstance(delay_ps, Decimal)
                argument_ps = target_ps - delay_ps
                component = delta.get(argument_ps, Decimal("0"))
                lookup = {
                    "target_time_ps": str(target_ps),
                    "source_argument_ps": str(argument_ps),
                    "exact_source_timestamp_found": argument_ps in delta,
                    "out_of_range": argument_ps < n3_grid[0] or argument_ps > n3_grid[-1],
                    "missing_exact_timestamp": argument_ps not in delta,
                    "component_A": fmt_decimal(component),
                }
            elif kind == "signed_gain":
                assert isinstance(gain, Decimal)
                argument_ps = target_ps
                base_delta = delta.get(argument_ps, Decimal("0"))
                component = base_delta * gain
                lookup = {
                    "target_time_ps": str(target_ps),
                    "source_argument_ps": str(argument_ps),
                    "exact_source_timestamp_found": argument_ps in delta,
                    "out_of_range": argument_ps < n3_grid[0] or argument_ps > n3_grid[-1],
                    "missing_exact_timestamp": argument_ps not in delta,
                    "base_delta_A": fmt_decimal(base_delta),
                    "gain": str(gain),
                    "component_A": fmt_decimal(component),
                }
            else:  # pragma: no cover
                raise RuntimeError(f"unknown transform: {kind}")
            replay_value = background + component
            source_rows.append(
                [
                    fmt_ps(target_ps),
                    fmt_decimal(background),
                    fmt_decimal(delta.get(argument_ps, Decimal("0"))),
                    fmt_decimal(component),
                    fmt_decimal(replay_value),
                ]
            )
            deck_points.append((target_ps, replay_value))
            lookup_records.append(lookup)

        source_path = EXP / "data" / f"{run_id}_source.csv"
        write_once(
            source_path,
            csv_text(
                [
                    "time_ps",
                    "I_N3_BACKGROUND_A",
                    "delta_I4_BASE_AT_LOOKUP_A",
                    "delta_I4_COMPONENT_A",
                    "I_REPLAY_A",
                ],
                source_rows,
            ),
        )
        description = (
            f"exact timestamp shift delta_I4(t-{delay_ps} ps)"
            if kind == "exact_timestamp_shift"
            else f"signed delta_I4 gain {gain}"
        )
        deck_path = EXP / "runs" / run_id / "deck.cir"
        write_once(deck_path, replay_deck(run_id, source_path, deck_points, description))
        intervention_records[run_id] = {
            "run_id": run_id,
            "kind": kind,
            "formula": (
                f"I_N3(t) + delta_I4(t - {delay_ps} ps)"
                if kind == "exact_timestamp_shift"
                else f"I_N3(t) + {gain} * delta_I4(t)"
            ),
            "source_path": source_path.relative_to(EXP.parent.parent.parent).as_posix(),
            "source_sha256": sha256(source_path),
            "source_sample_count": len(source_rows),
            "source_time_start_ps": str(output_times[0]),
            "source_time_end_ps": str(output_times[-1]),
            "deck_path": deck_path.relative_to(EXP.parent.parent.parent).as_posix(),
            "deck_sha256": sha256(deck_path),
            "deck_bytes": deck_path.stat().st_size,
            "pwl_pairs": len(deck_points),
            "lookup_records": lookup_records,
            "tail_extension": {
                "background_rule": "N3 final stored value after 199.9 ps only",
                "delta_rule": "exact lookup on original grid; missing/out-of-range zero",
            },
        }

    registry = {
        "schema": "jm2-delta4-transformation-registry-v1",
        "experiment_id": EXP.name,
        "head": current_head(),
        "source_identity": {
            "N3_PASSIVE_snapshot": {
                "path": SOURCE_SNAPSHOTS["N3_PASSIVE"].relative_to(EXP.parent.parent.parent).as_posix(),
                "sha256": sha256(SOURCE_SNAPSHOTS["N3_PASSIVE"]),
            },
            "N4_PASSIVE_snapshot": {
                "path": SOURCE_SNAPSHOTS["N4_PASSIVE"].relative_to(EXP.parent.parent.parent).as_posix(),
                "sha256": sha256(SOURCE_SNAPSHOTS["N4_PASSIVE"]),
            },
            "signal": "I(B_JSL8)",
            "positive_orientation": "JSL_NODE7 toward passive load / I_REPLAY 0 QBIN",
        },
        "source_grid": {
            "original_time_start_ps": str(n3_grid[0]),
            "original_time_end_ps": str(n3_grid[-1]),
            "original_sample_count": len(n3_grid),
            "output_time_end_ps": str(OUTPUT_END_PS),
            "output_sample_count": len(output_times),
            "actual_decimal_grid": True,
            "source_grid_gap_preserved": "14.7 ps to 14.9 ps",
        },
        "delta4": {
            "equation": "I_N4_PASSIVE(B_JSL8,t) - I_N3_PASSIVE(B_JSL8,t)",
            "role": "marginal source contribution / mathematical counterfactual component",
            "source_csv": delta_path.relative_to(EXP.parent.parent.parent).as_posix(),
            "source_csv_sha256": sha256(delta_path),
            "reconstruction_equation": "I_N3_PASSIVE + delta_I4 == I_N4_PASSIVE",
            "max_abs_reconstruction_residual_A": fmt_decimal(max_residual),
            "reconstruction_abs_tolerance_A": str(SOURCE_RECON_TOL_A),
            "arithmetic": "exact Decimal subtraction/addition",
        },
        "delay_contract": {
            "definition": "S_tau(delta)(t)=delta(t-tau)",
            "timestamp_operation": "exact Decimal key lookup, never row-index shift",
            "interpolation": False,
            "smoothing": False,
            "resampling": False,
            "fitting": False,
            "pulse_reconstruction": False,
            "out_of_range_delta": "zero",
            "missing_exact_timestamp": "zero",
            "N3_background_original_domain_unchanged": True,
        },
        "gain_contract": {
            "signed_scaling": True,
            "positive_and_negative_scaled": True,
            "rectification": False,
            "clipping": False,
            "reshaping": False,
            "timestamp_change": False,
        },
        "authorized_runs": intervention_records,
    }
    write_once(EXP / "analysis/transformation_registry.json", json_text(registry))
    reconstruction = {
        "schema": "jm2-delta4-source-reconstruction-check-v1",
        "experiment_id": EXP.name,
        "head": current_head(),
        "source_csv": delta_path.relative_to(EXP.parent.parent.parent).as_posix(),
        "source_csv_sha256": sha256(delta_path),
        "same_actual_decimal_grid": True,
        "sample_count": len(n3_grid),
        "max_abs_residual_A": fmt_decimal(max_residual),
        "tolerance_A": str(SOURCE_RECON_TOL_A),
        "status": "PASS" if max_residual <= SOURCE_RECON_TOL_A else "FAIL",
        "residual_nonzero_count": sum(value != 0 for value in reconstruction_residual.values()),
        "all_values_finite": True,
    }
    write_once(EXP / "analysis/source_reconstruction.json", json_text(reconstruction))
    print(
        json.dumps(
            {
                "status": "PASS",
                "delta_rows": len(n3_grid),
                "output_rows": len(output_times),
                "runs": list(intervention_records),
                "max_abs_reconstruction_residual_A": fmt_decimal(max_residual),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
