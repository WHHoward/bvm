#!/usr/bin/env python3
"""Independent actual-grid arithmetic and artifact audit for the registered T1_C1 batch."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

SERIES = Path(__file__).resolve().parents[1]
RUNS_DIR = SERIES / "runs"
METRIC_SPEC = SERIES / "analysis" / "metric_spec.json"
T1_JJS = tuple(f"B_J{index}" for index in range(1, 12))
T1_WINDOWS = {
    "T1_PRE_CLOCK": (Decimal("110e-12"), Decimal("170e-12")),
    "T1_CLOCK_1": (Decimal("170e-12"), Decimal("220e-12")),
    "T1_CLOCK_2": (Decimal("220e-12"), Decimal("250e-12")),
}
OUTPUT_SIGNALS = (
    "V(T1_I)", "V(CLK)", "V(S)", "V(C)", "V(VOUT_C1)", "V(VOUT_C2)",
)
CURRENT_SIGNALS = (
    "I(V_T1_LINK)", "I(R_S)", "I(R_C)", "I(V_BIAS1)", "I(V_BIAS2)", "I(V_BIAS3)",
    "I(L1|XT1)", "I(L3|XT1)", "I(L11|XT1)", "I(L14|XT1)", "I(L17|XT1)",
)
RUN_IDS = tuple(f"A{19 + mask + (4 if mode == 'P' else 0):03d}_T1_C1_{mode}{mask}"
                for mode in ("Q", "P") for mask in range(4))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _unwrap_radians(values: list[float]) -> list[float]:
    if not values:
        return []
    result = [values[0]]
    for previous, current in zip(values, values[1:]):
        delta = current - previous
        while delta > math.pi:
            delta -= 2 * math.pi
        while delta < -math.pi:
            delta += 2 * math.pi
        result.append(result[-1] + delta)
    return result


def _area(values: list[Decimal], times: list[Decimal], indices: list[int]) -> Decimal:
    if len(indices) < 2:
        raise ValueError("registered window has fewer than two stored samples")
    return sum(((values[a] + values[b]) / Decimal(2)) * (times[b] - times[a])
                for a, b in zip(indices, indices[1:]))


def _read_selected_raw(raw: Path, required: set[str]) -> tuple[list[Decimal], dict[str, list[Decimal]], str]:
    before = sha256(raw)
    times: list[Decimal] = []
    columns: dict[str, list[Decimal]] = {name: [] for name in required}
    with raw.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.reader(stream)
        header = next(reader, None)
        if not header or header[0] != "time" or len(header) != len(set(header)):
            raise ValueError(f"invalid/duplicated raw header: {raw}")
        missing = sorted(required - set(header))
        if missing:
            raise ValueError(f"raw is missing registered audit signals: {missing}")
        positions = {name: header.index(name) for name in required}
        previous = None
        for row_number, row in enumerate(reader, start=2):
            if len(row) != len(header):
                raise ValueError(f"ragged CSV row {row_number}: {raw}")
            try:
                stamp = Decimal(row[0])
                sample = {name: Decimal(row[index]) for name, index in positions.items()}
            except (InvalidOperation, ValueError) as exc:
                raise ValueError(f"non-numeric raw token at {raw}:{row_number}") from exc
            if (not stamp.is_finite() or any(not value.is_finite() for value in sample.values())
                    or (previous is not None and stamp <= previous)):
                raise ValueError(f"non-finite/nonmonotonic raw sample at {raw}:{row_number}")
            previous = stamp
            times.append(stamp)
            for name, value in sample.items():
                columns[name].append(value)
    after = sha256(raw)
    if before != after:
        raise ValueError(f"raw changed during independent audit: {raw}")
    return times, columns, before


def audit_run(run_id: str, phase_tolerance: float, voltage_tolerance: float,
              area_tolerance: float) -> tuple[dict[str, Any], list[str]]:
    run_dir = RUNS_DIR / run_id
    raw = run_dir / "raw.csv"
    result = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
    provenance = json.loads((run_dir / "provenance.json").read_text(encoding="utf-8"))
    manifest = json.loads((run_dir / "probe_manifest.json").read_text(encoding="utf-8"))
    runner = json.loads((run_dir / "analysis" / "cell_metrics.json").read_text(encoding="utf-8"))
    mechanical = json.loads((run_dir / "analysis" / "mechanical_qa.json").read_text(encoding="utf-8"))
    required = {f"P({jj}|XT1)" for jj in T1_JJS} | {f"V({jj}|XT1)" for jj in T1_JJS}
    required |= set(OUTPUT_SIGNALS) | set(CURRENT_SIGNALS)
    if run_id.endswith(("P0", "P1", "P2", "P3")):
        required |= {"V(CLK_RAW)", "I(R_TRIG_CLK)"}
    else:
        required.add("I(R_CLK_QUIET)")
    times, columns, raw_hash = _read_selected_raw(raw, required)
    errors: list[str] = []
    if result.get("status") != "MECHANICAL_QA_PASS_AWAITING_USER_REVIEW" or result.get("artifact_status") != "VALID":
        errors.append("run result is not artifact-valid and awaiting review")
    if result.get("physical_solve_count") != 1:
        errors.append("run physical_solve_count is not exactly one")
    if result.get("raw_sha256") != raw_hash or provenance.get("raw", {}).get("sha256") != raw_hash:
        errors.append("raw SHA disagrees with result/provenance")
    if mechanical.get("raw_sha256_before") != raw_hash or mechanical.get("raw_sha256_after_plots") != raw_hash:
        errors.append("raw pre/post QA SHA mismatch")
    if manifest.get("profile") != "t1_focus" or manifest.get("signal_count") != len(manifest.get("signals", [])):
        errors.append("probe manifest profile/count is invalid")
    if len(times) != result.get("sample_count") or len(times) != mechanical.get("sample_count"):
        errors.append("independent raw row count disagrees with result/mechanical QA")
    if runner.get("raw_sha256") != raw_hash or runner.get("interpolation_or_resampling") is not False:
        errors.append("runner arithmetic does not identify this immutable raw grid")

    runner_junctions = {(item["junction"], item["window"]): item
                        for item in runner.get("t1_metrics", {}).get("junctions", [])}
    audited_junctions = []
    phase_area_max_abs_delta = 0.0
    for jj in T1_JJS:
        phase_signal, voltage_signal = f"P({jj}|XT1)", f"V({jj}|XT1)"
        phase = _unwrap_radians([float(value) for value in columns[phase_signal]])
        voltage = columns[voltage_signal]
        for window_name, (start, end) in T1_WINDOWS.items():
            indices = [i for i, stamp in enumerate(times) if start <= stamp < end]
            if len(indices) < 2:
                errors.append(f"{jj}/{window_name} has fewer than two stored samples")
                continue
            first, last = indices[0], indices[-1]
            delta_rad = phase[last] - phase[first]
            area = _area(voltage, times, indices)
            max_index = max(indices, key=lambda i: voltage[i])
            min_index = min(indices, key=lambda i: voltage[i])
            max_abs_index = max(indices, key=lambda i: abs(voltage[i]))
            audited = {
                "junction": jj, "window": window_name,
                "first_stored_time_seconds": str(times[first]),
                "last_stored_time_seconds": str(times[last]),
                "sample_count": len(indices), "phase_delta_rad": delta_rad,
                "phase_delta_rad_over_2pi_navigation": delta_rad / (2 * math.pi),
                "voltage_area_v_s_same_jj_same_rows": str(area),
                "voltage_area_phi0_arithmetic": float(area / Decimal("2.067833848e-15")),
                "phase_minus_area_turn_arithmetic": delta_rad / (2 * math.pi) -
                    float(area / Decimal("2.067833848e-15")),
                "voltage_min_v": str(min(voltage[i] for i in indices)),
                "voltage_max_v": str(voltage[max_index]),
                "time_of_voltage_max_seconds": str(times[max_index]),
                "time_of_voltage_min_seconds": str(times[min_index]),
                "time_of_max_abs_voltage_seconds": str(times[max_abs_index]),
                "interpolation_or_resampling": False,
            }
            audited_junctions.append(audited)
            expected = runner_junctions.get((jj, window_name))
            if expected is None:
                errors.append(f"runner is missing {jj}/{window_name} arithmetic")
                continue
            phase_error = abs(delta_rad - float(expected["phase_delta_rad"]))
            area_error = abs(float(area) - float(expected["voltage_area_v_s_same_jj_same_rows"]))
            phase_area_max_abs_delta = max(phase_area_max_abs_delta,
                                           abs(audited["phase_minus_area_turn_arithmetic"]))
            if phase_error > phase_tolerance:
                errors.append(f"{jj}/{window_name} phase cross-check exceeds tolerance: {phase_error}")
            if area_error > area_tolerance:
                errors.append(f"{jj}/{window_name} voltage-area cross-check exceeds tolerance: {area_error}")

    audited_outputs = []
    runner_outputs = {(item["signal"], item["window"]): item
                      for item in runner.get("t1_metrics", {}).get("outputs", [])}
    runner_outputs.update({(item["signal"], item["window"]): item
                           for item in runner.get("output_metrics", [])
                           if item.get("boundary") == "VOUT"})
    for signal in OUTPUT_SIGNALS + (("V(CLK_RAW)",) if "V(CLK_RAW)" in columns else ()):
        values = columns[signal]
        for window_name, (start, end) in T1_WINDOWS.items():
            indices = [i for i, stamp in enumerate(times) if start <= stamp < end]
            if len(indices) < 2:
                errors.append(f"{signal}/{window_name} has fewer than two stored samples")
                continue
            selected = [values[i] for i in indices]
            max_index = max(indices, key=lambda i: values[i])
            min_index = min(indices, key=lambda i: values[i])
            max_abs_index = max(indices, key=lambda i: abs(values[i]))
            area = _area(values, times, indices)
            audited = {
                "signal": signal, "window": window_name, "sample_count": len(indices),
                "min_v": str(min(selected)), "max_v": str(values[max_index]),
                "peak_to_peak_v": str(max(selected) - min(selected)),
                "time_of_positive_max_seconds": str(times[max_index]),
                "time_of_min_seconds": str(times[min_index]),
                "time_of_max_abs_seconds": str(times[max_abs_index]),
                "signed_area_v_s": str(area), "interpolation_or_resampling": False,
            }
            audited_outputs.append(audited)
            expected = runner_outputs.get((signal, window_name))
            if expected is None:
                errors.append(f"runner is missing {signal}/{window_name} output arithmetic")
                continue
            expected_peak_time = expected.get("time_of_positive_max_seconds",
                                              expected.get("time_of_max_v_s"))
            if str(expected_peak_time) != str(times[max_index]):
                errors.append(f"{signal}/{window_name} peak-time token mismatch")
            expected_area = expected.get("signed_area_v_s", expected.get("area_v_s"))
            if abs(float(area) - float(expected_area)) > area_tolerance:
                errors.append(f"{signal}/{window_name} output-area cross-check exceeds tolerance")
            expected_min = expected.get("min_v")
            expected_max = expected.get("max_v")
            expected_p2p = expected.get("peak_to_peak_v")
            if expected_min is not None and abs(float(min(selected)) - float(expected_min)) > voltage_tolerance:
                errors.append(f"{signal}/{window_name} minimum-voltage cross-check exceeds tolerance")
            if expected_max is not None and abs(float(max(selected)) - float(expected_max)) > voltage_tolerance:
                errors.append(f"{signal}/{window_name} maximum-voltage cross-check exceeds tolerance")
            if expected_p2p is not None and abs(float(max(selected) - min(selected)) - float(expected_p2p)) > voltage_tolerance:
                errors.append(f"{signal}/{window_name} peak-to-peak cross-check exceeds tolerance")

    return ({
        "run_id": run_id, "raw_path": str(raw.relative_to(SERIES)),
        "raw_sha256_before": raw_hash, "raw_sha256_after": sha256(raw),
        "raw_bytes": raw.stat().st_size, "sample_count": len(times),
        "time_start_seconds": str(times[0]), "time_end_seconds": str(times[-1]),
        "dt_min_seconds": str(min(b - a for a, b in zip(times, times[1:]))),
        "dt_max_seconds": str(max(b - a for a, b in zip(times, times[1:]))),
        "probe_count": manifest.get("signal_count"),
        "output_mode": result.get("output_mode"),
        "t1_clock_mode": result.get("t1_clock_mode"),
        "row_bits": result.get("row_bits"), "column_bits": result.get("column_bits"),
        "result_status": result.get("status"), "artifact_status": result.get("artifact_status"),
        "mechanical_qa_status": mechanical.get("status"),
        "static_qa_status": json.loads((run_dir / "analysis" / "static_qa.json").read_text()).get("status"),
        "stimulus_qa_status": result.get("stimulus_qa_status"),
        "provenance_qa_status": result.get("provenance_qa_status"),
        "plot_qa_status": result.get("plot_qa_status"),
        "deck_sha256": provenance.get("deck", {}).get("sha256"),
        "actual_deck_sha256": sha256(run_dir / "actual_deck.cir"),
        "probe_manifest_sha256": provenance.get("probe_manifest", {}).get("sha256"),
        "source_manifest_sha256": provenance.get("source_manifest", {}).get("sha256"),
        "source_hashes": {role: item.get("sha256") for role, item in provenance.get("sources", {}).items()},
        "solver": provenance.get("solver"), "executor_sha256": provenance.get("executor_sha256"),
        "parent_head": provenance.get("parent_head"),
        "phase_area_max_abs_residual_turn_arithmetic": phase_area_max_abs_delta,
        "t1_junctions": audited_junctions, "t1_outputs": audited_outputs,
        "errors": errors,
    }, errors)


def main() -> int:
    parser = argparse.ArgumentParser(description="Independently audit T1_C1 batch arithmetic from immutable raw CSVs")
    parser.add_argument("--drive-folder-id")
    parser.add_argument("--drive-folder-url")
    args = parser.parse_args()
    spec = json.loads(METRIC_SPEC.read_text(encoding="utf-8"))
    tolerances = spec["authorized_batch_20261008_t1_c1"]["independent_arithmetic_reproduction_tolerances"]
    phase_tolerance = float(tolerances["phase_abs_rad"])
    voltage_tolerance = float(tolerances["voltage_abs_v"])
    tolerance = float(tolerances["voltage_area_abs_v_s"])
    output_path = SERIES / "analysis" / "t1_batch_arithmetic.json"
    qa_path = SERIES / "analysis" / "t1_batch_arithmetic_qa.json"
    batch_manifest_path = SERIES / "analysis" / "t1_batch_manifest.json"
    if output_path.exists() or qa_path.exists() or batch_manifest_path.exists():
        raise FileExistsError("refusing to overwrite immutable T1 batch arithmetic artifacts")
    results = []
    errors = []
    for run_id in RUN_IDS:
        record, run_errors = audit_run(run_id, phase_tolerance, voltage_tolerance, tolerance)
        results.append(record)
        errors.extend(f"{run_id}: {message}" for message in run_errors)
    comparison_qa_path = SERIES / "analysis" / "t1_batch_comparison_qa.json"
    if not comparison_qa_path.is_file():
        errors.append("T1 paired/baseline comparison QA is missing")
        comparison_qa = None
    else:
        comparison_qa = json.loads(comparison_qa_path.read_text(encoding="utf-8"))
        if comparison_qa.get("status") != "PASS":
            errors.append("T1 paired/baseline comparison QA is not PASS")
    report = {
        "schema": "bvm-2x2-t1-batch-arithmetic-v1",
        "audit_script": str(Path(__file__).relative_to(SERIES)),
        "audit_script_sha256": sha256(Path(__file__)),
        "runs": results,
        "integration": "Decimal trapezoid over exact stored time tokens and actual raw rows",
        "phase_unit": "radians; rad/(2*pi) is navigation arithmetic, not event count",
        "interpolation_or_resampling": False,
        "scientific_interpretation_performed": False,
    }
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    manifest = {
        "schema": "bvm-2x2-t1-c1-batch-manifest-v1",
        "batch_id": "BVM2X2_T1_C1_20261008",
        "registered_parent_head": "7eb7983c8091a3933e871246754a47d199cabd67",
        "run_count_authorized": 8,
        "physical_solve_count": len(results),
        "execution_order": list(RUN_IDS),
        "status": "PASS" if not errors else "FAIL",
        "runs": [{key: value for key, value in record.items()
                  if key not in {"t1_junctions", "t1_outputs", "errors"}}
                 for record in results],
        "terminal_reference_runs": [
            "A013_SHARED_R00_C00", "A014_SHARED_R10_C10",
            "A015_SHARED_R01_C10", "A016_SHARED_R11_C10"],
        "comparison_map": {"Q0_P0": "A013_SHARED_R00_C00", "Q1_P1": "A014_SHARED_R10_C10",
                           "Q2_P2": "A015_SHARED_R01_C10", "Q3_P3": "A016_SHARED_R11_C10"},
        "comparison_manifest": "analysis/t1_batch_comparison_manifest.json",
        "comparison_qa": ("analysis/t1_batch_comparison_qa.json" if comparison_qa is not None else None),
        "arithmetic_report": str(output_path.relative_to(SERIES)),
        "audit_script": str(Path(__file__).relative_to(SERIES)),
        "audit_script_sha256": sha256(Path(__file__)),
        "drive_folder_id": args.drive_folder_id,
        "drive_folder_url": args.drive_folder_url,
        "scientific_interpretation_performed": False,
        "automatic_follow_up": False,
    }
    batch_manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                                   encoding="utf-8")
    qa = {
        "schema": "bvm-2x2-t1-batch-arithmetic-qa-v1",
        "status": "PASS" if not errors else "FAIL",
        "run_count": len(results), "physical_solve_count": len(results),
        "raws_immutable": all(item["raw_sha256_before"] == item["raw_sha256_after"] for item in results),
        "phase_delta_tolerance_rad": phase_tolerance,
        "voltage_tolerance_v": voltage_tolerance,
        "voltage_area_tolerance_v_s": tolerance,
        "errors": errors,
        "report_sha256": sha256(output_path),
        "batch_manifest_sha256": sha256(batch_manifest_path),
        "scientific_interpretation_performed": False,
    }
    qa_path.write_text(json.dumps(qa, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": qa["status"], "run_count": len(results),
                      "errors": errors, "report": str(output_path.relative_to(SERIES)),
                      "batch_manifest": str(batch_manifest_path.relative_to(SERIES)),
                      "qa": str(qa_path.relative_to(SERIES))}, ensure_ascii=False, indent=2))
    return 0 if qa["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
