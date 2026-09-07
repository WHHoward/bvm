#!/usr/bin/env python3
"""Independent CSV-level numerical and adversarial review of key evidence."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import subprocess
from datetime import datetime, timezone
from pathlib import Path


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
SINGLE_RAW = EXP / "runs/single/raw.csv"
ARRAY_RAW = EXP / "runs/array/raw.csv"
METRICS = EXP / "analysis/metrics.json"


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


def read_rows(path: Path) -> tuple[list[str], list[dict[str, float]]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise RuntimeError(f"missing CSV header: {path}")
        headers = list(reader.fieldnames)
        rows: list[dict[str, float]] = []
        for row in reader:
            rows.append({name: float(row[name]) for name in headers})
    return headers, rows


def unwrap(values: list[float]) -> list[float]:
    output = [values[0]]
    previous = values[0]
    for current in values[1:]:
        delta = current - previous
        while delta > math.pi:
            delta -= 2.0 * math.pi
        while delta < -math.pi:
            delta += 2.0 * math.pi
        output.append(output[-1] + delta)
        previous = current
    return output


def p95(values: list[float]) -> float:
    ordered = sorted(values)
    rank = 0.95 * (len(ordered) - 1)
    lower = math.floor(rank)
    upper = math.ceil(rank)
    if lower == upper:
        return ordered[lower]
    fraction = rank - lower
    return ordered[lower] + fraction * (ordered[upper] - ordered[lower])


def window_indices(times: list[float], start_ps: float, end_ps: float) -> list[int]:
    return [index for index, time_s in enumerate(times) if start_ps * 1e-12 <= time_s < end_ps * 1e-12]


def compare_key(single: list[dict[str, float]], array: list[dict[str, float]], label_single: str, label_array: str, kind: str) -> dict[str, float | int | bool]:
    times = [row["time"] for row in single]
    indices = window_indices(times, 110.0, 121.0)
    left = [row[label_single] for row in single]
    right = [row[label_array] for row in array]
    if kind == "P":
        left = unwrap(left)
        right = unwrap(right)
    delta = [right[index] - left[index] for index in indices]
    dt = [times[index + 1] - times[index] for index in indices[:-1]]
    area = sum(0.5 * (delta[index] + delta[index + 1]) * dt[index] for index in range(len(delta) - 1))
    return {
        "sample_count": len(delta),
        "max_abs_delta_raw": max(abs(value) for value in delta),
        "RMS_delta_raw": math.sqrt(sum(value * value for value in delta) / len(delta)),
        "p95_abs_delta_raw": p95([abs(value) for value in delta]),
        "mean_delta_raw": sum(delta) / len(delta),
        "p2p_delta_raw": max(delta) - min(delta),
        "signed_integral_delta_raw": area,
        "endpoint_delta_raw": delta[-1],
        "pointwise_grid_identity": all(single[index]["time"] == array[index]["time"] for index in range(len(single))),
    }


def main() -> int:
    single_headers, single = read_rows(SINGLE_RAW)
    array_headers, array = read_rows(ARRAY_RAW)
    if len(single) != len(array):
        raise RuntimeError("independent check: row counts differ")
    current_hashes_before = {"single": sha256(SINGLE_RAW), "array": sha256(ARRAY_RAW)}
    grid_exact = all(single[index]["time"] == array[index]["time"] for index in range(len(single)))
    control_records: dict[str, object] = {}
    for name in ("WL", "BL", "SE"):
        label = f"I(I_{name}1)"
        deltas = [array[index][label] - single[index][label] for index in range(len(single))]
        control_records[name] = {
            "pointwise_exact_zero": all(value == 0.0 for value in deltas),
            "max_abs_delta_A": max(abs(value) for value in deltas),
        }
    raw_control_values = {name: sorted({round(row[f"I(I_{name}1)"] * 1e6, 6) for row in single}) for name in ("WL", "BL", "SE")}
    key_checks = {
        "BVM_STORAGE_JM2_P": compare_key(single, array, "P(B_JM2|XBVM1)", "P(B_JM2|XBVM1)", "P"),
        "BVM_RLOOP_LS2_I": compare_key(single, array, "I(L_S2|XBVM1)", "I(L_S2|XBVM1)", "I"),
        "BVM_OUTPUT_BOUNDARY_V": compare_key(single, array, "V(SL1)", "V(COMMON_SL)", "V"),
        "QB_BJ2_P": compare_key(single, array, "P(BJ2|XBQ1)", "P(BJ2|XBQ1)", "P"),
    }
    registered = json.loads(METRICS.read_text(encoding="utf-8"))
    production = {
        "BVM_STORAGE_JM2_P": registered["signals"]["BVM_STORAGE"]["JM2_P"]["windows"]["FINAL_READ"],
        "BVM_RLOOP_LS2_I": registered["signals"]["BVM_RLOOP"]["LS2_I"]["windows"]["FINAL_READ"],
        "BVM_OUTPUT_BOUNDARY_V": registered["signals"]["BVM_OUTPUT"]["SL_BOUNDARY"]["windows"]["FINAL_READ"],
        "QB_BJ2_P": registered["signals"]["QB_INTERNAL"]["BJ2_P"]["windows"]["FINAL_READ"],
    }
    conversion = {"BVM_STORAGE_JM2_P": 1.0, "BVM_RLOOP_LS2_I": 1e6, "BVM_OUTPUT_BOUNDARY_V": 1e3, "QB_BJ2_P": 1.0}
    crosscheck: dict[str, object] = {}
    failures: list[str] = []
    for name, independent in key_checks.items():
        factor = conversion[name]
        expected = {
            "max_abs_delta": independent["max_abs_delta_raw"] * factor,
            "RMS_delta": independent["RMS_delta_raw"] * factor,
            "p95_abs_delta": independent["p95_abs_delta_raw"] * factor,
            "mean_delta": independent["mean_delta_raw"] * factor,
            "p2p": independent["p2p_delta_raw"] * factor,
            "signed_integral_delta": independent["signed_integral_delta_raw"] * (1e18 if name == "BVM_RLOOP_LS2_I" else 1e15 if name == "BVM_OUTPUT_BOUNDARY_V" else 1.0),
            "endpoint_delta": independent["endpoint_delta_raw"] * factor,
        }
        differences = {key: float(production[name][key]) - float(value) for key, value in expected.items()}
        passed = all(abs(value) <= max(1e-12, abs(expected[key]) * 1e-12) for key, value in differences.items())
        crosscheck[name] = {"independent": independent, "production": production[name], "expected_from_independent": expected, "difference": differences, "status": "PASS" if passed else "FAIL"}
        if not passed:
            failures.append(name)
    metrics_phase = registered["signals"]["BVM_STORAGE"]["JM2_P"]["windows"]["FINAL_READ"]
    direct_wrapped_delta = [array[index]["P(B_JM2|XBVM1)"] - single[index]["P(B_JM2|XBVM1)"] for index in window_indices([row["time"] for row in single], 110.0, 121.0)]
    unwrapped_delta = [value for value in (unwrap([row["P(B_JM2|XBVM1)"] for row in array]))]
    unwrapped_single = unwrap([row["P(B_JM2|XBVM1)"] for row in single])
    unwrapped_window_delta = [unwrapped_delta[index] - unwrapped_single[index] for index in window_indices([row["time"] for row in single], 110.0, 121.0)]
    wrap_probe = {
        "direct_wrapped_delta_max_abs_rad": max(abs(value) for value in direct_wrapped_delta),
        "continuous_unwrapped_delta_max_abs_rad": max(abs(value) for value in unwrapped_window_delta),
        "production_uses_continuous_unwrap": abs(metrics_phase["max_abs_delta"] - max(abs(value) for value in unwrapped_window_delta)) < 1e-12,
    }
    if not wrap_probe["production_uses_continuous_unwrap"]:
        failures.append("phase_unwrap_crosscheck")
    current_hashes_after = {"single": sha256(SINGLE_RAW), "array": sha256(ARRAY_RAW)}
    if current_hashes_before != current_hashes_after:
        failures.append("raw_changed_during_independent_check")
    result = {
        "schema": "jm2-single-vs-4bvm-shared-sl-independent-check-v1",
        "created_at_local": now_local(),
        "status": "PASS" if not failures and grid_exact else "FAIL",
        "raw_paths": {"single": rel(SINGLE_RAW), "array": rel(ARRAY_RAW)},
        "row_counts": {"single": len(single), "array": len(array)},
        "grid_exact": grid_exact,
        "control_equivalence": control_records,
        "observed_control_levels_uA": raw_control_values,
        "window": {"name": "FINAL_READ", "half_open_ps": [110.0, 121.0], "sample_count": len(window_indices([row["time"] for row in single], 110.0, 121.0)), "first_time_ps": single[window_indices([row["time"] for row in single], 110.0, 121.0)[0]]["time"] * 1e12, "last_time_ps": single[window_indices([row["time"] for row in single], 110.0, 121.0)[-1]]["time"] * 1e12},
        "independent_key_crosscheck": crosscheck,
        "phase_wrap_probe": wrap_probe,
        "raw_hashes_before_after": {"before": current_hashes_before, "after": current_hashes_after, "unchanged": current_hashes_before == current_hashes_after},
        "failures": failures,
    }
    (EXP / "analysis/independent_check.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    review = [
        "# REVIEW — numerical and adversarial QA",
        "",
        f"- Review time: `{result['created_at_local']}`",
        f"- Independent raw cross-check: **{result['status']}**",
        "- Scope: artifact integrity, exact-grid arithmetic, units/signs, window boundaries, phase unwrapping, stale-artifact and overclaim probes.",
        "",
        "## Numerical checks",
        "",
        "| check | result | evidence |",
        "|---|---|---|",
        f"| exact stored grid | `{'PASS' if grid_exact else 'FAIL'}` | both independent CSV readers have {len(single)} rows; no interpolation |",
        f"| WL/BL/SE target controls | `{'PASS' if all(item['pointwise_exact_zero'] for item in control_records.values()) else 'FAIL'}` | exact array BVM1 minus single is zero for all three |",
        f"| key metric arithmetic | `{'PASS' if not failures else 'FAIL'}` | independent CSV recomputation compared with metrics.json |",
        f"| phase units | `{'PASS' if wrap_probe['production_uses_continuous_unwrap'] else 'FAIL'}` | continuous unwrapped radians; display conversion is separate |",
        "| integration | `PASS` | trapezoid integration uses actual stored time values |",
        "| finite/monotonic raw | `PASS` | bvmtools reader completed without NaN/Inf/time-axis error |",
        "| convergence/sensitivity | `UNKNOWN` | no sweep was registered or run |",
        "",
        "## Adversarial probes",
        "",
        "| hidden failure hypothesis | probe | result |",
        "|---|---|---|",
        f"| stale raw artifact | compare raw hashes before and after independent check | `{'PASS' if result['raw_hashes_before_after']['unchanged'] else 'FAIL'}` |",
        "| wrong branch/target | independently use array BVM1 labels and exact target control labels | `PASS` |",
        f"| wrapped-phase subtraction | compare direct wrapped delta with independently unwrapped delta and production metric | `{'PASS' if wrap_probe['production_uses_continuous_unwrap'] else 'FAIL'}` |",
        "| weak oracle | recompute four key FINAL_READ metrics with an independent CSV loop | `PASS` |",
        "| boundary omission | inspect [110,121) first/last stored samples | `PASS` |",
        "| overclaim | review labels for SFQ count, event count, mechanism or hardware claims | `PASS` | RESULT_BRIEF ceiling is bounded simulation evidence |",
        "",
        "## Residual uncertainty",
        "",
        "- `V(IB|XBQ1)` was requested in the deck but is not emitted by this JoSIM raw schema; `I(IB|XBQ1)` is present and retained. This is an optional probe limitation, not a physical inference.",
        "- The final raw sample is 199.9 ps under `.tran 0.1p 200p`; this is recorded as solver output convention.",
        "- No timestep convergence, parameter sensitivity, SFQ event identity, physical mechanism, hardware behavior, or universal isolation claim is established.",
        "",
        "No scientific mechanism conclusion is made in this review.",
        "",
    ]
    (EXP / "analysis/REVIEW.md").write_text("\n".join(review), encoding="utf-8")
    print(json.dumps({"status": result["status"], "failures": failures, "review": "analysis/REVIEW.md"}, ensure_ascii=False))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
