#!/usr/bin/env python3
"""Independent read-only arithmetic audit for the authorized A/B/C raw files."""

from __future__ import annotations

import csv
import hashlib
import json
import math
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

SERIES = Path(__file__).resolve().parents[1]
RUNS = SERIES / "runs"
PHI0_VS = Decimal("2.067833848e-15")
CELL_JJS = ("B_JM1", "B_JM2", "B_JS1", "B_JS2")
QB_JJS = ("BJ1", "BJ2", "BJ3")
SJTL_JJS = ("BJ1",)
CB_JJS = ("BJ1", "BJ2")

RUN_SPECS = {
    "A009_SHARED_R10_C11": {
        "role": "A009 orientation reference; no new solve",
        "response_windows": {"A009_FIRST_READ_RESPONSE": ("110e-12", "170e-12")},
        "branch_windows": {"A009_FINAL_READ": ("110e-12", "121e-12")},
    },
    "A010_SHARED_R11_C10": {
        "role": "A same-column dual read",
        "response_windows": {
            "FIRST_READ_RESPONSE": ("110e-12", "170e-12"),
            "SECOND_READ_RESPONSE": ("170e-12", "250e-12"),
        },
        "branch_windows": {
            "FINAL_READ": ("110e-12", "121e-12"),
            "SECOND_READ": ("170e-12", "181e-12"),
        },
    },
    "A011_SHARED_R11_C11": {
        "role": "B four-cell read",
        "response_windows": {"READ_RESPONSE": ("110e-12", "250e-12")},
        "branch_windows": {"FINAL_READ": ("110e-12", "121e-12")},
    },
    "A012_SHARED_R11_C11": {
        "role": "C mixed-store sequential write then four-cell read",
        "response_windows": {"READ_RESPONSE": ("170e-12", "300e-12")},
        "branch_windows": {
            "WRITE0": ("50e-12", "61e-12"),
            "WRITE1_TARGET_1": ("90e-12", "101e-12"),
            "WRITE1_TARGET_2": ("120e-12", "131e-12"),
            "FINAL_READ": ("170e-12", "181e-12"),
        },
    },
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _trace_labels() -> tuple[list[str], list[str], list[str]]:
    branches = [f"I({element}|XBVM_{cell})"
                for cell in ("R1C1", "R1C2", "R2C1", "R2C2")
                for element in ("R_WL", "R_BL", "R_SE")]
    outputs = [f"V({node}_{cell})" for cell in ("R1C1", "R1C2", "R2C1", "R2C2")
               for node in ("SL", "QBOUT", "SJTL_OUT", "VOUT")]
    junctions = []
    for cell in ("R1C1", "R1C2", "R2C1", "R2C2"):
        for role, instance, elements in (
                ("BVM", f"XBVM_{cell}", CELL_JJS),
                ("QB", f"XBQ_{cell}", QB_JJS),
                ("SJTL", f"XSJTL_{cell}", SJTL_JJS),
                ("CB", f"XCB_{cell}", CB_JJS)):
            for element in elements:
                junctions.extend((f"P({element}|{instance})", f"V({element}|{instance})"))
    return branches, outputs, junctions


def _read_selected_raw(run_id: str, labels: list[str]
                       ) -> tuple[list[Decimal], dict[str, list[Decimal]], dict[str, Any]]:
    run = RUNS / run_id
    raw = run / "raw.csv"
    result = json.loads((run / "result.json").read_text(encoding="utf-8"))
    manifest = json.loads((SERIES / "experiment_manifest.json").read_text(encoding="utf-8"))
    entry = next((item for item in manifest["runs"] if item.get("run_id") == run_id), None)
    before = sha256(raw)
    if result.get("artifact_status") != "VALID" or result.get("raw_sha256") != before:
        raise ValueError(f"run result/raw SHA mismatch or invalid artifact: {run_id}")
    for qa_name in ("raw_qa.json", "mechanical_qa.json", "provenance_qa.json",
                    "plot_qa.json", "stimulus_qa.json", "static_qa.json"):
        qa = json.loads((run / "analysis" / qa_name).read_text(encoding="utf-8"))
        if qa.get("status") != "PASS":
            raise ValueError(f"{run_id} has non-PASS {qa_name}: {qa.get('status')}")
    if entry is None or entry.get("raw_sha256") != before:
        raise ValueError(f"experiment_manifest/raw SHA mismatch: {run_id}")
    traces = {label: [] for label in labels}
    times: list[Decimal] = []
    with raw.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.reader(stream)
        header = next(reader, None)
        if not header or header[0] != "time" or len(header) != len(set(header)):
            raise ValueError(f"missing time column or duplicate labels in {raw}")
        missing = sorted(set(labels) - set(header))
        if missing:
            raise ValueError(f"required probes missing from {run_id}: {missing}")
        indexes = {label: header.index(label) for label in labels}
        previous: Decimal | None = None
        for row_no, row in enumerate(reader, start=2):
            if not row:
                continue
            try:
                stamp = Decimal(row[0])
                values = {label: Decimal(row[index]) for label, index in indexes.items()}
            except (InvalidOperation, IndexError) as exc:
                raise ValueError(f"invalid raw number at {raw}:{row_no}") from exc
            if (not stamp.is_finite() or any(not value.is_finite() for value in values.values())
                    or (previous is not None and stamp <= previous)):
                raise ValueError(f"nonfinite/nonmonotonic raw row at {raw}:{row_no}")
            previous = stamp
            times.append(stamp)
            for label, value in values.items():
                traces[label].append(value)
    after = sha256(raw)
    if before != after:
        raise ValueError(f"raw changed during independent audit: {run_id}")
    if len(times) != result.get("sample_count"):
        raise ValueError(f"sample-count mismatch for {run_id}")
    return times, traces, {"run_id": run_id, "raw_path": f"runs/{run_id}/raw.csv",
                           "raw_sha256_before": before, "raw_sha256_after": after,
                           "raw_immutable": before == after, "sample_count": len(times),
                           "actual_time_start_s": str(times[0]),
                           "actual_time_end_s": str(times[-1]),
                           "dt_min_s": str(min(b-a for a,b in zip(times,times[1:]))),
                           "dt_max_s": str(max(b-a for a,b in zip(times,times[1:])))}


def _indices(times: list[Decimal], bounds: tuple[str, str]) -> list[int]:
    start, end = map(Decimal, bounds)
    return [i for i, stamp in enumerate(times) if start <= stamp < end]


def _integral(times: list[Decimal], values: list[Decimal], indexes: list[int]) -> Decimal:
    if len(indexes) < 2:
        raise ValueError("registered arithmetic window has fewer than two stored rows")
    return sum(((values[left] + values[right]) * Decimal("0.5") *
                (times[right] - times[left]) for left, right in zip(indexes, indexes[1:])),
               Decimal(0))


def _unwrap_radians(values: list[Decimal]) -> list[float]:
    if not values:
        return []
    result = [float(values[0])]
    for before, after in zip(values, values[1:]):
        delta = float(after - before)
        while delta > math.pi:
            delta -= 2 * math.pi
        while delta < -math.pi:
            delta += 2 * math.pi
        result.append(result[-1] + delta)
    return result


def _boundaries() -> list[tuple[str, str, str]]:
    return [(role, f"{node}_{cell}", cell)
            for cell in ("R1C1", "R1C2", "R2C1", "R2C2")
            for role, node in (("BVM_SL", "SL"), ("QB_OUT", "QBOUT"),
                               ("SJTL_OUT", "SJTL_OUT"), ("VOUT", "VOUT"))]


def audit_run(run_id: str, spec: dict[str, Any], branches: list[str],
              output_labels: list[str], junction_labels: list[str]) -> dict[str, Any]:
    labels = list(dict.fromkeys(branches + output_labels + junction_labels))
    times, traces, integrity = _read_selected_raw(run_id, labels)
    branch_records = []
    for stage, raw_bounds in spec["branch_windows"].items():
        indexes = _indices(times, raw_bounds)
        start, end = map(Decimal, raw_bounds)
        for cell in ("R1C1", "R1C2", "R2C1", "R2C2"):
            for element, branch in (("R_WL", "WL"), ("R_BL", "BL"), ("R_SE", "SE")):
                signal = f"I({element}|XBVM_{cell})"
                values = traces[signal]
                selected = [values[i] for i in indexes]
                branch_records.append({
                    "cell": cell, "branch": branch, "signal": signal, "window": stage,
                    "window_s": [str(start), str(end)], "boundary_rule": "[start,end)",
                    "sample_count": len(indexes), "min_a": str(min(selected)),
                    "max_a": str(max(selected)), "max_abs_a": str(max(abs(v) for v in selected)),
                    "charge_c_actual_grid": str(_integral(times, values, indexes)),
                })

    output_records = []
    junction_records = []
    for window, raw_bounds in spec["response_windows"].items():
        indexes = _indices(times, raw_bounds)
        start, end = map(Decimal, raw_bounds)
        if len(indexes) < 2:
            raise ValueError(f"{run_id}/{window} contains fewer than two stored rows")
        for role, node, cell in _boundaries():
            signal = f"V({node})"
            values = traces[signal]
            max_i = max(indexes, key=lambda i: values[i])
            min_i = min(indexes, key=lambda i: values[i])
            maxabs_i = max(indexes, key=lambda i: abs(values[i]))
            selected = [values[i] for i in indexes]
            output_records.append({
                "cell": cell, "boundary": role, "signal": signal, "window": window,
                "window_s": [str(start), str(end)], "boundary_rule": "[start,end)",
                "sample_count": len(indexes), "min_v": str(min(selected)),
                "max_v": str(max(selected)), "peak_to_peak_v": str(max(selected)-min(selected)),
                "signed_voltage_area_v_s_actual_grid": str(_integral(times, values, indexes)),
                "time_of_max_v_s": str(times[max_i]), "time_of_min_v_s": str(times[min_i]),
                "time_of_max_abs_v_s": str(times[maxabs_i]),
            })

        for cell in ("R1C1", "R1C2", "R2C1", "R2C2"):
            groups = (("BVM", f"XBVM_{cell}", CELL_JJS),
                      ("QB", f"XBQ_{cell}", QB_JJS),
                      ("sJTL", f"XSJTL_{cell}", SJTL_JJS),
                      ("CB", f"XCB_{cell}", CB_JJS))
            for role, instance, elements in groups:
                for element in elements:
                    phase_signal, voltage_signal = f"P({element}|{instance})", f"V({element}|{instance})"
                    phase_all = _unwrap_radians(traces[phase_signal])
                    phase_delta = phase_all[indexes[-1]] - phase_all[indexes[0]]
                    voltage_area = _integral(times, traces[voltage_signal], indexes)
                    phase_turns = phase_delta / (2 * math.pi)
                    area_turns = float(voltage_area / PHI0_VS)
                    junction_records.append({
                        "cell": cell, "role": role, "instance": instance,
                        "junction": element, "phase_signal": phase_signal,
                        "voltage_signal": voltage_signal, "window": window,
                        "window_s": [str(start), str(end)], "boundary_rule": "[start,end)",
                        "first_stored_time_s": str(times[indexes[0]]),
                        "last_stored_time_s": str(times[indexes[-1]]),
                        "sample_count": len(indexes), "phase_delta_rad": phase_delta,
                        "phase_delta_turns_navigation": phase_turns,
                        "voltage_area_v_s_actual_grid": str(voltage_area),
                        "voltage_area_over_phi0_arithmetic": area_turns,
                        "phase_minus_area_turns_arithmetic": phase_turns-area_turns,
                    })

    return {
        **integrity, "role": spec["role"], "branch_current_arithmetic": branch_records,
        "output_arithmetic": output_records, "same_jj_phase_voltage_arithmetic": junction_records,
        "integration_grid": "raw CSV actual time tokens; Decimal trapezoid",
        "phase_units": "raw radians; turns only delta/(2*pi) navigation arithmetic",
        "event_or_sfq_count": "NOT_PERFORMED; no registered classifier/threshold",
        "scientific_interpretation_performed": False,
    }


def main() -> int:
    target = SERIES / "analysis" / "independent_batch_arithmetic_v2.json"
    if target.exists():
        raise FileExistsError(f"refusing to overwrite arithmetic audit: {target}")
    branches, outputs, junctions = _trace_labels()
    runs = {run_id: audit_run(run_id, spec, branches, outputs, junctions)
            for run_id, spec in RUN_SPECS.items()}
    result = {
        "schema": "bvm-2x2-independent-batch-arithmetic-v2",
        "supersedes": "independent_batch_arithmetic.json; v1 output rows lacked an explicit cell field",
        "source_script_sha256": sha256(Path(__file__)),
        "metric_spec_sha256": sha256(SERIES / "analysis" / "metric_spec.json"),
        "phi0_vs": str(PHI0_VS), "runs": runs,
        "independent_crosscheck": "Decimal actual-grid output and same-JJ voltage integration; phase independently unwrapped from raw radians",
        "event_or_sfq_count": "NOT_PERFORMED",
        "scientific_interpretation_performed": False,
    }
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "ARITHMETIC_AUDIT_COMPLETE", "output": str(target.relative_to(SERIES)),
                      "sha256": sha256(target),
                      "run_raw_sha256": {run_id: item["raw_sha256_before"]
                                         for run_id, item in runs.items()},
                      "output_metric_rows": {run_id: len(item["output_arithmetic"])
                                             for run_id, item in runs.items()},
                      "junction_metric_rows": {run_id: len(item["same_jj_phase_voltage_arithmetic"])
                                               for run_id, item in runs.items()},
                      "scientific_interpretation_performed": False}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
