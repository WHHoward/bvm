#!/usr/bin/env python3
"""Independent Decimal recomputation of registered arithmetic from one raw CSV."""

from __future__ import annotations

import csv
import json
import math
import sys
from decimal import Decimal, localcontext
from pathlib import Path
from typing import Any

from common import MATRIX, PHI0, read_json, run_dir, sha256, write_json

ROOT = Path(__file__).resolve().parents[1]
MAPPING = read_json(ROOT / "analysis" / "PHASE_AREA_MAPPING.json")
WINDOWS = read_json(MATRIX)["windows_ps"]
TOLERANCES = read_json(MATRIX)["mechanical_arithmetic_reproduction"]["tolerances"]


def dec_integral(time_seconds: list[Decimal], voltage: list[Decimal]) -> Decimal:
    if len(time_seconds) != len(voltage) or len(time_seconds) < 2:
        raise ValueError("independent integration requires equal arrays with at least two samples")
    return sum((t1 - t0) * (v0 + v1) / Decimal(2)
               for t0, t1, v0, v1 in zip(time_seconds, time_seconds[1:], voltage, voltage[1:]))


def selected_indices(time_tokens_s: list[str], bounds_ps: list[float]) -> list[int]:
    start, end = Decimal(str(bounds_ps[0])), Decimal(str(bounds_ps[1]))
    return [index for index, token in enumerate(time_tokens_s)
            if start <= Decimal(token) * Decimal("1e12") < end]


def compare_scalar(name: str, independently_computed: float, pipeline_value: Any,
                   tolerance: float) -> dict[str, Any]:
    actual = float(pipeline_value)
    difference = abs(independently_computed - actual)
    return {"quantity": name, "independent_value": independently_computed,
            "pipeline_value": actual, "absolute_difference": difference,
            "registered_implementation_tolerance": tolerance,
            "status": "PASS" if math.isfinite(difference) and difference <= tolerance else "FAIL"}


def verify(run_id: str) -> dict[str, Any]:
    directory = run_dir(run_id)
    raw = directory / "raw.csv"
    metrics_path = directory / "analysis" / "metrics.json"
    before = sha256(raw)
    metadata = read_json(directory / "metadata.json")
    if metadata.get("raw", {}).get("sha256") != before:
        raise ValueError("raw SHA differs from solve-time metadata")
    metrics = read_json(metrics_path)
    required = {"time"}
    for mapping in MAPPING["mappings"]:
        required.add(mapping["phase_column"])
        required.add(mapping["voltage_column"])
    required.add("V(R_TERM)")
    with raw.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        headers = reader.fieldnames or []
        if len(headers) != len(set(headers)):
            raise ValueError("duplicate raw CSV columns")
        folded_headers = [header.casefold() for header in headers]
        if len(folded_headers) != len(set(folded_headers)):
            raise ValueError("raw headers collide under JoSIM case normalization")
        actual_header = {header.casefold(): header for header in headers}
        missing = sorted(name for name in required if name != "time" and name.casefold() not in actual_header)
        if "time" not in actual_header:
            missing.append("time")
        if missing:
            raise ValueError(f"independent check missing required raw columns: {missing}")
        raw_header_aliases = {name: actual_header[name.casefold()] for name in required
                              if name != "time" and name != actual_header[name.casefold()]}
        time_tokens_s: list[str] = []
        selected = {name: [] for name in required if name != "time"}
        for line_no, row in enumerate(reader, start=2):
            token = row[actual_header["time"]]
            if not Decimal(token).is_finite():
                raise ValueError(f"non-finite time token at line {line_no}")
            time_tokens_s.append(token)
            for signal in selected:
                value = Decimal(row[actual_header[signal.casefold()]])
                if not value.is_finite():
                    raise ValueError(f"non-finite {signal} at line {line_no}")
                selected[signal].append(value)
    if len(time_tokens_s) < 2:
        raise ValueError("raw has fewer than two rows")
    metrics_by_key = {(row["stage"], row["window"]): row
                      for row in metrics["jj_phase_area_metrics"]}
    comparisons = []
    with localcontext() as context:
        context.prec = 50
        phi0 = Decimal(str(PHI0))
        for mapping in MAPPING["mappings"]:
            stage = mapping["stage"]
            phase = selected[mapping["phase_column"]]
            voltage = selected[mapping["voltage_column"]]
            rd = int(mapping["reporting_direction"])
            vts = int(mapping["voltage_to_phase_sign"])
            for window, bounds in WINDOWS.items():
                indices = selected_indices(time_tokens_s, bounds)
                pipeline = metrics_by_key.get((stage, window))
                if len(indices) < 2 or pipeline is None or pipeline.get("status") != "RECORDED":
                    comparisons.append({"stage": stage, "window": window, "status": "FAIL_MISSING_OR_INVALID_PIPELINE_ROW"})
                    continue
                first, last = indices[0], indices[-1]
                delta_rad = phase[last] - phase[first]
                area_raw = dec_integral([Decimal(time_tokens_s[i]) for i in indices],
                                        [voltage[i] for i in indices])
                phase_turns = rd * float(delta_rad) / (2.0 * math.pi)
                area_aligned = Decimal(vts) * area_raw
                area_turns = float(Decimal(rd) * area_aligned / phi0)
                tests = [
                    compare_scalar("delta_phase_rad", float(delta_rad), pipeline["delta_phase_rad"],
                                   TOLERANCES["phase_delta_rad_abs"]),
                    compare_scalar("phase_reported_turns", phase_turns, pipeline["phase_reported_turns"],
                                   TOLERANCES["phase_turns_abs"]),
                    compare_scalar("voltage_area_v_s", float(area_aligned), pipeline["voltage_area_v_s"],
                                   TOLERANCES["voltage_area_v_s_abs"]),
                    compare_scalar("area_reported_phi0", area_turns, pipeline["area_reported_phi0"],
                                   TOLERANCES["voltage_area_phi0_abs"]),
                ]
                comparisons.append({"stage": stage, "window": window,
                                    "actual_first_time_s_token": time_tokens_s[first],
                                    "actual_last_time_s_token": time_tokens_s[last],
                                    "sample_count": len(indices),
                                    "checks": tests,
                                    "status": "PASS" if all(item["status"] == "PASS" for item in tests) else "FAIL"})
        terminal_pipeline = {(row["window"]): row for row in metrics["terminal_area_metrics"]}
        for window in ("final_read", "post_read", "read_response"):
            indices = selected_indices(time_tokens_s, WINDOWS[window])
            pipeline = terminal_pipeline.get(window)
            if len(indices) < 2 or pipeline is None or pipeline.get("status") != "RECORDED":
                comparisons.append({"stage": "R_TERM", "window": window,
                                    "status": "FAIL_MISSING_OR_INVALID_PIPELINE_ROW"})
                continue
            area = dec_integral([Decimal(time_tokens_s[i]) for i in indices],
                                [selected["V(R_TERM)"][i] for i in indices])
            area_phi0 = float(area / phi0)
            check = compare_scalar("terminal_signed_area_phi0", area_phi0,
                                   pipeline["signed_area_phi0"],
                                   TOLERANCES["terminal_area_phi0_abs"])
            comparisons.append({"stage": "R_TERM", "window": window,
                                "sample_count": len(indices), "checks": [check],
                                "status": check["status"]})
    after = sha256(raw)
    if before != after:
        raise ValueError("raw changed during independent arithmetic verification")
    status = "PASS" if all(item["status"] == "PASS" for item in comparisons) else "FAIL"
    qa = {"schema": "bvm-bq-cb-independent-arithmetic-qa-v1", "run_id": run_id,
          "status": status, "raw_sha256_before_after": {"before": before, "after": after},
          "independent_method": "Decimal raw seconds, raw voltage and raw phase; no analyzer imports",
          "mechanical_reproduction_tolerances": TOLERANCES,
          "raw_header_aliases": raw_header_aliases,
          "these_tolerances_are_not_physical_or_acceptance_tolerances": True,
          "checks": comparisons, "interpolation": False, "resampling": False,
          "raw_unchanged": True, "scientific_interpretation_performed": False}
    write_json(directory / "analysis" / "independent_check.json", qa)
    return qa


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Independent raw arithmetic QA; no physical solve")
    parser.add_argument("run_id")
    args = parser.parse_args()
    qa = verify(args.run_id)
    print(json.dumps(qa, ensure_ascii=False, indent=2))
    return 0 if qa["status"] == "PASS" else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
