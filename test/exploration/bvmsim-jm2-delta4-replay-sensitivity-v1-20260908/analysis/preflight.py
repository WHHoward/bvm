#!/usr/bin/env python3
"""Machine preflight for the four-condition delta4 replay experiment.

This script is read-only with respect to all existing evidence and never
invokes a JoSIM solve. It writes only new preflight/source-manifest records.
"""

from __future__ import annotations

import csv
import subprocess
from decimal import Decimal
from pathlib import Path

from common import (
    CONTROL_RAWS,
    EXPECTED_HASHES,
    EXP,
    HEAD,
    MODEL_PATHS,
    RUNS,
    SOURCE_RAWS,
    SOURCE_SNAPSHOTS,
    SOURCE_END_PS,
    SOURCE_START_PS,
    SOURCE_RECON_TOL_A,
    TAIL_WINDOW_PS,
    QUIET_ABS_LAST_UA_MAX,
    QUIET_MAX_STEP_UA_MAX,
    QUIET_P2P_UA_MAX,
    SOLVER,
    current_head,
    json_text,
    read_snapshot,
    sha256,
    tail_summary,
    write_once,
)


REQUIRED_CONTRACT_SENTENCE = "This experiment is governed by docs/EXPERIMENT_CONTRACT.md."
PREFLIGHT_MD = EXP / "PREFLIGHT.md"


def raw_source_rows(path: Path) -> list[tuple[str, Decimal, Decimal]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.reader(handle)
        header = next(reader)
        if header.count("time") != 1 or header.count("I(B_JSL8)") != 1:
            raise RuntimeError(f"source raw must contain unique time and I(B_JSL8): {path}")
        time_index = header.index("time")
        current_index = header.index("I(B_JSL8)")
        rows = [
            (
                row[time_index],
                Decimal(row[time_index]) * Decimal("1e12"),
                Decimal(row[current_index]),
            )
            for row in reader
            if row and any(cell.strip() for cell in row)
        ]
    if len(rows) < 2:
        raise RuntimeError(f"source raw has too few rows: {path}")
    if any(right[1] <= left[1] for left, right in zip(rows, rows[1:])):
        raise RuntimeError(f"source raw time is not strictly increasing: {path}")
    if any(not value.is_finite() for row in rows for value in row[1:]):
        raise RuntimeError(f"source raw has non-finite values: {path}")
    return rows


def source_pair_check(raw_path: Path, snapshot_path: Path) -> dict[str, object]:
    raw_rows = raw_source_rows(raw_path)
    snapshot_rows = read_snapshot(snapshot_path)
    mismatches: list[dict[str, object]] = []
    if len(raw_rows) != len(snapshot_rows):
        mismatches.append({"reason": "row_count", "raw": len(raw_rows), "snapshot": len(snapshot_rows)})
    for index, (raw, snapshot) in enumerate(zip(raw_rows, snapshot_rows)):
        if raw[1] != snapshot[1] or raw[2] != snapshot[2]:
            mismatches.append(
                {
                    "index": index,
                    "raw_time_ps": str(raw[1]),
                    "snapshot_time_ps": str(snapshot[1]),
                    "raw_current_A": str(raw[2]),
                    "snapshot_current_A": str(snapshot[2]),
                }
            )
            if len(mismatches) >= 5:
                break
    times = [row[1] for row in snapshot_rows]
    intervals = [right - left for left, right in zip(times, times[1:])]
    interval_text = sorted({format(value.normalize(), "f") for value in intervals})
    return {
        "raw": raw_path.relative_to(EXP.parent.parent.parent).as_posix(),
        "raw_sha256": sha256(raw_path),
        "snapshot": snapshot_path.relative_to(EXP.parent.parent.parent).as_posix(),
        "snapshot_sha256": sha256(snapshot_path),
        "raw_snapshot_exact_decimal_match": not mismatches,
        "mismatches": mismatches,
        "sample_count": len(snapshot_rows),
        "time_start_ps": str(times[0]),
        "time_end_ps": str(times[-1]),
        "dt_ps": interval_text,
        "tail": tail_summary(snapshot_rows),
    }


def control_check(name: str, path: Path) -> dict[str, object]:
    actual = sha256(path)
    return {
        "path": path.relative_to(EXP.parent.parent.parent).as_posix(),
        "expected_sha256": EXPECTED_HASHES[f"{name}_raw"],
        "actual_sha256": actual,
        "unchanged": actual == EXPECTED_HASHES[f"{name}_raw"],
        "rerun": False,
    }


def model_check(name: str, path: Path) -> dict[str, object]:
    actual = sha256(path)
    expected = EXPECTED_HASHES.get(name)
    return {
        "path": path.relative_to(REPO).as_posix(),
        "expected_sha256": expected,
        "actual_sha256": actual,
        "unchanged": expected is None or actual == expected,
        "bytes": path.stat().st_size,
    }


REPO = EXP.parents[2]


def main() -> int:
    failures: list[str] = []
    if REQUIRED_CONTRACT_SENTENCE not in PREFLIGHT_MD.read_text(encoding="utf-8"):
        failures.append("PREFLIGHT.md is missing the exact contract sentence")
    actual_head = current_head()
    if actual_head != HEAD:
        failures.append(f"HEAD mismatch: {actual_head}")
    tracked_status = subprocess.run(
        ["git", "diff", "--quiet"], cwd=REPO, check=False
    ).returncode == 0 and subprocess.run(
        ["git", "diff", "--cached", "--quiet"], cwd=REPO, check=False
    ).returncode == 0
    if not tracked_status:
        failures.append("tracked or staged worktree changes exist at preflight")

    source_checks: dict[str, object] = {}
    for name in ("N3_PASSIVE", "N4_PASSIVE"):
        try:
            item = source_pair_check(SOURCE_RAWS[name], SOURCE_SNAPSHOTS[name])
        except Exception as exc:
            failures.append(f"{name}: {exc}")
            continue
        source_checks[name] = item
        if item["raw_sha256"] != EXPECTED_HASHES[f"{name}_raw"]:
            failures.append(f"{name}: source raw hash mismatch")
        if item["snapshot_sha256"] != EXPECTED_HASHES[f"{name}_snapshot"]:
            failures.append(f"{name}: source snapshot hash mismatch")
        if not item["raw_snapshot_exact_decimal_match"]:
            failures.append(f"{name}: raw/snapshot Decimal values differ")
        if item["sample_count"] != 1999:
            failures.append(f"{name}: unexpected sample count")
        if Decimal(item["time_start_ps"]) != SOURCE_START_PS or Decimal(item["time_end_ps"]) != SOURCE_END_PS:
            failures.append(f"{name}: unexpected source time range")
        if item["dt_ps"] != ["0.1", "0.2"]:
            failures.append(f"{name}: unexpected actual source intervals {item['dt_ps']}")
        if item["tail"]["status"] != "PASS":
            failures.append(f"{name}: quiet-tail criterion failed")

    if set(source_checks) == {"N3_PASSIVE", "N4_PASSIVE"}:
        n3_rows = read_snapshot(SOURCE_SNAPSHOTS["N3_PASSIVE"])
        n4_rows = read_snapshot(SOURCE_SNAPSHOTS["N4_PASSIVE"])
        n3_grid = [row[1] for row in n3_rows]
        n4_grid = [row[1] for row in n4_rows]
        if n3_grid != n4_grid:
            failures.append("N3/N4 source Decimal timestamp grids differ")

    controls = {}
    for name, path in CONTROL_RAWS.items():
        item = control_check(name, path)
        controls[name] = item
        if not item["unchanged"]:
            failures.append(f"{name}: immutable control hash mismatch")

    models = {}
    for name, path in MODEL_PATHS.items():
        item = model_check(name, path)
        models[name] = item
        if not item["unchanged"]:
            failures.append(f"{name}: model hash mismatch")
    if not SOLVER.is_file():
        failures.append(f"solver missing: {SOLVER}")
        solver = None
    else:
        solver_version = subprocess.check_output([str(SOLVER), "--version"], cwd=REPO, text=True).strip()
        solver = {
            "path": SOLVER.relative_to(REPO).as_posix(),
            "sha256": sha256(SOLVER),
            "version": solver_version,
        }

    existing_new_artifacts = []
    for run_id in RUNS:
        run_dir = EXP / "runs" / run_id
        for filename in ("deck.cir", "raw.csv", "run.log", "metadata.json"):
            if (run_dir / filename).exists():
                existing_new_artifacts.append((run_id, filename))
    if existing_new_artifacts:
        failures.append(f"new run artifacts already exist: {existing_new_artifacts}")

    run_matrix = [
        {
            "id": "DELTA4_DELAY_3PS",
            "formula": "I_N3(t) + delta_I4(t - 3 ps)",
            "kind": "exact_timestamp_shift",
            "delay_ps": "3.0",
        },
        {
            "id": "DELTA4_DELAY_6PS",
            "formula": "I_N3(t) + delta_I4(t - 6 ps)",
            "kind": "exact_timestamp_shift",
            "delay_ps": "6.0",
        },
        {
            "id": "DELTA4_GAIN_1P25",
            "formula": "I_N3(t) + 1.25 * delta_I4(t)",
            "kind": "signed_gain",
            "gain": "1.25",
        },
        {
            "id": "DELTA4_GAIN_1P50",
            "formula": "I_N3(t) + 1.50 * delta_I4(t)",
            "kind": "signed_gain",
            "gain": "1.50",
        },
    ]
    record = {
        "schema": "jm2-delta4-replay-sensitivity-preflight-v1",
        "experiment_id": EXP.name,
        "created_at_local": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).astimezone().isoformat(timespec="seconds"),
        "status": "PASS" if not failures else "FAIL",
        "head_at_setup": HEAD,
        "head_at_preflight": actual_head,
        "tracked_worktree_clean_at_preflight": tracked_status,
        "contract_sentence_present": REQUIRED_CONTRACT_SENTENCE in PREFLIGHT_MD.read_text(encoding="utf-8"),
        "source_signal": "I(B_JSL8)",
        "source_checks": source_checks,
        "source_grid": {
            "sample_count": 1999,
            "time_start_ps": str(SOURCE_START_PS),
            "time_end_ps": str(SOURCE_END_PS),
            "dt_ps": ["0.1", "0.2"],
            "common_actual_decimal_grid_required": True,
        },
        "delta4": {
            "equation": "I_N4_PASSIVE(B_JSL8,t) - I_N3_PASSIVE(B_JSL8,t)",
            "role": "marginal source contribution / mathematical counterfactual component",
            "reconstruction": "I_N3_PASSIVE + delta_I4 == I_N4_PASSIVE",
            "reconstruction_abs_tolerance_A": str(SOURCE_RECON_TOL_A),
            "timestamp_arithmetic": "exact Decimal",
            "no_interpolation": True,
            "no_resampling": True,
            "no_waveform_reconstruction": True,
            "out_of_range_delta": "zero",
        },
        "tail_decision": {
            "window_ps": [str(item) for item in TAIL_WINDOW_PS],
            "abs_last_uA_max": str(QUIET_ABS_LAST_UA_MAX),
            "p2p_uA_max": str(QUIET_P2P_UA_MAX),
            "max_adjacent_step_uA_max": str(QUIET_MAX_STEP_UA_MAX),
            "output_grid_end_ps": "205.9",
            "tstop_ps": "206.0",
            "n3_background_extension": "hold final N3 stored value only after 199.9 ps",
            "primary_window_ps": ["110.0", "200.0"],
        },
        "controls": controls,
        "models": models,
        "solver": solver,
        "authorized_run_matrix": run_matrix,
        "receiver": {
            "qb": "BVMSim/BQ.cir",
            "jtl": "BVMSim/library_josim/jtl2.cir",
            "jjmit": "circuits/models/jjmit.cir",
            "jtl_stages": 6,
            "termination_ohm": 10.0,
            "parameters": "RJ1=12 ohm; RJ2=4 ohm; IB=250 uA; BJS area=3; BJ1 area=0.9; BJ2 area=2",
        },
        "probes": {
            "QB_full": "QBIN/input boundary, I(I_REPLAY), LIN, BJS, L1, BJ1, RJ1, L2, IB, BJ2, RJ2, L3, QBOUT; JJ P/V/I and inductor/resistor I/V where available",
            "JTL_full": "JTL1-JTL6 B01/B02 P/V/I and each stage output voltage; I(R_TERM)",
        },
        "windows_ps": {
            "FINAL_READ_RESPONSE": ["110.0", "200.0"],
            "QB_INTERNAL_CRITICAL": ["118.0", "140.0"],
            "FOURTH_INTERNAL_SEARCH": ["120.0", "140.0"],
            "DOWNSTREAM_ZOOM": ["118.0", "180.0"],
            "TAIL_COMPLETENESS": ["190.0", "206.0"],
            "semantics": "half-open [start,end)",
            "internal_priority": ["BJ1", "BJ2", "QBOUT"],
        },
        "thresholds": {
            "voltage_mV": {
                "QBIN": 0.25,
                "BJS": 0.10,
                "BJ1": 0.30,
                "BJ2": 0.50,
                "QBOUT": 0.45,
                "JTL_B01": 0.50,
            },
            "termination_uA": 5.0,
            "minimum_consecutive_samples": 2,
            "semantics": "activity samples/clusters only; never event counts",
        },
        "phase_area": {
            "raw_phase_unit": "rad",
            "conversion": "continuous_unwrap(rad)/(2*pi)",
            "same_jj_same_endpoints_same_direction_same_window": True,
            "absolute_tolerance_turns": 0.15,
            "relative_tolerance": 0.15,
            "SFQ_count_allowed": False,
        },
        "convergence": "UNKNOWN; no timestep convergence or sensitivity sweep authorized",
        "prohibited_followups": ["N5/N6", "QB/JTL tuning", "BJ1/BJ2/RJ1/RJ2/IB sweep", "timestep sweep", "physical BVM rerun", "additional condition", "T1"],
        "failures": failures,
    }
    write_once(EXP / "analysis/preflight.json", json_text(record))

    source_manifest = {
        "schema": "jm2-delta4-source-identity-manifest-v1",
        "experiment_id": EXP.name,
        "head": actual_head,
        "source_signal": "I(B_JSL8)",
        "N3_PASSIVE": source_checks.get("N3_PASSIVE"),
        "N4_PASSIVE": source_checks.get("N4_PASSIVE"),
        "controls": controls,
        "models": models,
        "solver": solver,
        "delta4_role": "marginal source contribution / mathematical counterfactual component; not independent SFQ or independent BVM source",
    }
    write_once(EXP / "source/source_manifest.json", json_text(source_manifest))
    print(__import__("json").dumps({"status": record["status"], "head": actual_head, "failures": failures}, ensure_ascii=False))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
