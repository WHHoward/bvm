#!/usr/bin/env python3
"""Raw, deck and registered mechanical QA for the full 24-case grid."""

from __future__ import annotations

import hashlib
import json
import math
import re
import subprocess
import sys
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EXP / "analysis"))
from prepare_experiment import (  # noqa: E402
    BQ400,
    CONTROL_KINDS,
    IBIAS_VALUES,
    L1_VALUES,
    MASKS,
    NEW_RUNS,
    NEW_RUN_PARAMETERS,
    REUSE_RUNS,
    REUSE_SPECS,
    RUN_TO_MASK,
    build_deck,
    control_line,
    normalized_deck,
    pre_read_controls,
)
sys.path.insert(0, str(REPO / "scripts"))
from bvmtools.phase import continuous_unwrap, window_indices  # noqa: E402
from bvmtools.raw import read_csv  # noqa: E402


OPTIONAL_UNKNOWN = {"V(IB|XBQ1)"}
GRID_CASES: OrderedDict[tuple[float, float], tuple[str, str]] = OrderedDict(
    (
        ((1.2, 250.0), ("ARRAY_L1P12_0001", "ARRAY_L1P12_0011")),
        ((1.2, 260.0), ("ARRAY_L1P12_IB260_0001", "ARRAY_L1P12_IB260_0011")),
        ((1.2, 270.0), ("ARRAY_L1P12_IB270_0001", "ARRAY_L1P12_IB270_0011")),
        ((1.4, 250.0), ("ARRAY_L1P14_0001", "ARRAY_L1P14_0011")),
        ((1.4, 260.0), ("ARRAY_L1P14_IB260_0001", "ARRAY_L1P14_IB260_0011")),
        ((1.4, 270.0), ("ARRAY_L1P14_IB270_0001", "ARRAY_L1P14_IB270_0011")),
        ((1.6, 250.0), ("ARRAY_L1P16_IB250_0001", "ARRAY_L1P16_IB250_0011")),
        ((1.6, 260.0), ("ARRAY_L1P16_IB260_0001", "ARRAY_L1P16_IB260_0011")),
        ((1.6, 270.0), ("ARRAY_L1P16_IB270_0001", "ARRAY_L1P16_IB270_0011")),
        ((2.0, 250.0), ("ARRAY_L1P20_IB250_0001", "ARRAY_L1P20_IB250_0011")),
        ((2.0, 260.0), ("ARRAY_IB260_0001", "ARRAY_IB260_0011")),
        ((2.0, 270.0), ("ARRAY_IB270_0001", "ARRAY_IB270_0011")),
    )
)
ALL_CASES = tuple(case_id for pair in GRID_CASES.values() for case_id in pair)
CASE_PARAMS: dict[str, dict[str, float]] = {
    **NEW_RUN_PARAMETERS,
    **{
        run_id: {"L1_pH": spec["L1_pH"], "IBias_uA": spec["IBias_uA"], "RJ1_ohm": 12.0}
        for run_id, spec in REUSE_SPECS.items()
    },
}

WINDOWS = OrderedDict(
    (
        ("EARLY_READ", (110e-12, 121e-12)),
        ("TAIL", (121e-12, 200e-12)),
    )
)
PRE_SWITCH_WINDOW = (110e-12, 114.5e-12)
PHASE_BASELINE_WINDOW = (101e-12, 110e-12)
PHASE_POST_READ_WINDOW = (110e-12, 200e-12)
RATIO_PEAK_TOLERANCE_A = 1e-12
RATIO_AREA_TOLERANCE_A_S = 1e-18
RATIO_CANCELLATION_FRACTION = 0.01


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def raw_path(case_id: str) -> Path:
    root = "runs" if case_id in NEW_RUNS else "references/reused"
    return EXP / root / case_id / "raw.csv"


def deck_path(case_id: str) -> Path:
    root = "runs" if case_id in NEW_RUNS else "references/reused"
    return EXP / root / case_id / "deck.cir"


def source_experiment(case_id: str) -> str:
    if case_id in NEW_RUNS:
        return str(EXP.relative_to(REPO))
    return str(REUSE_SPECS[case_id]["source"].relative_to(REPO))


def source_run(case_id: str) -> str:
    if case_id in NEW_RUNS:
        return f"runs/{case_id}"
    return f"runs/{REUSE_SPECS[case_id]['source_run']}"


def expected_probes() -> set[str]:
    probes: set[str] = set()
    for instance in range(1, 5):
        probes.update(f"I(I_{kind}{instance})" for kind in CONTROL_KINDS)
        header = f"XBVM{instance}"
        for jj in ("B_JM1", "B_JM2", "B_JS1", "B_JS2"):
            probes.update(f"{kind}({jj}|{header})" for kind in ("P", "V", "I"))
        for branch in ("L_M1", "L_M2", "L_M3", "L_PM", "R_JM1", "L_S1", "L_S2", "R_S", "L_S3", "R_SE", "L_PSE", "L_PSL", "R_SL", "L_SL"):
            probes.update(f"{kind}({branch}|{header})" for kind in ("I", "V"))
    probes.add("V(COMMON_SL)")
    for index in range(1, 9):
        probes.update((f"P(B_JSL{index})", f"V(B_JSL{index})", f"I(B_JSL{index})"))
    probes.update(("V(QBIN)", "V(QBOUT)", "I(LIN|XBQ1)", "V(LIN|XBQ1)"))
    for jj in ("BJS", "BJ1"):
        probes.update((f"P({jj}|XBQ1)", f"V({jj}|XBQ1)", f"I({jj}|XBQ1)"))
    for branch in ("RJ1", "L1"):
        probes.update((f"I({branch}|XBQ1)", f"V({branch}|XBQ1)"))
    probes.update(("I(IB|XBQ1)", "V(IB|XBQ1)", "I(L2|XBQ1)", "V(L2|XBQ1)"))
    probes.update(("P(BJ2|XBQ1)", "V(BJ2|XBQ1)", "I(BJ2|XBQ1)"))
    probes.update(("I(RJ2|XBQ1)", "V(RJ2|XBQ1)", "I(L3|XBQ1)", "V(L3|XBQ1)"))
    for stage in range(1, 7):
        header = f"XJTL1_{stage}"
        for jj in ("B01", "B02"):
            probes.update((f"P({jj}|{header})", f"V({jj}|{header})", f"I({jj}|{header})"))
        probes.add(f"V(JTL{stage}_OUT)")
    probes.add("I(R_TERM)")
    return probes


def head_relation(preflight_head: str) -> dict[str, Any]:
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()
    if head == preflight_head:
        return {"status": "PASS", "head": head, "preflight_head": preflight_head, "relation": "EXACT"}
    changed = set(subprocess.check_output(["git", "diff", "--name-only", f"{preflight_head}..{head}"], cwd=REPO, text=True).splitlines())
    allowed = {str(EXP.relative_to(REPO) / "PREFLIGHT.md"), str(EXP.relative_to(REPO) / "analysis/preflight.json")}
    distance = int(subprocess.check_output(["git", "rev-list", "--count", f"{preflight_head}..{head}"], cwd=REPO, text=True).strip())
    status = "PASS" if distance == 1 and changed == allowed else "FAIL"
    return {"status": status, "head": head, "preflight_head": preflight_head, "relation": "PREFLIGHT_ONLY_SEAL_COMMIT" if status == "PASS" else "UNEXPECTED", "changed_paths": sorted(changed), "commit_distance": distance}


def trapezoid(times: tuple[float, ...], values: tuple[float, ...]) -> float:
    return sum((values[index] + values[index + 1]) * 0.5 * (times[index + 1] - times[index]) for index in range(len(values) - 1))


def selected(trace: Any, label: str, window: tuple[float, float]) -> tuple[tuple[float, ...], tuple[float, ...]]:
    indexes = window_indices(trace.time, *window)
    values = tuple(float(value) for value in trace.column(label))
    return tuple(trace.time[index] for index in indexes), tuple(values[index] for index in indexes)


def area(trace: Any, label: str, window: tuple[float, float]) -> float | None:
    times, values = selected(trace, label, window)
    return trapezoid(times, values) if len(times) >= 2 else None


def extrema(trace: Any, label: str) -> dict[str, float]:
    values = tuple(float(value) for value in trace.column(label))
    return {"max": max(values), "min": min(values), "max_abs": max(abs(value) for value in values)}


def phase_diagnostic(trace: Any, label: str) -> dict[str, Any]:
    unwrapped = continuous_unwrap(tuple(trace.column(label)))
    baseline_indices = window_indices(trace.time, *PHASE_BASELINE_WINDOW)
    post_indices = window_indices(trace.time, *PHASE_POST_READ_WINDOW)
    if not baseline_indices or not post_indices:
        return {"status": "UNKNOWN", "reason": "registered phase window has no samples", "not_event_time": True, "not_event_count": True}
    baseline = unwrapped[baseline_indices[0]]
    relative = tuple((unwrapped[index] - baseline) / (2.0 * math.pi) for index in post_indices)
    half_index = next((index for index, value in zip(post_indices, relative) if value >= 0.5), None)
    return {
        "status": "DERIVED",
        "label": label,
        "raw_unit": "rad",
        "display_unit": "turns",
        "conversion": "continuous_unwrap(raw_rad)/(2*pi)",
        "baseline_window_ps": [101.0, 110.0],
        "post_read_window_ps": [110.0, 200.0],
        "baseline_reference_time_ps": trace.time[baseline_indices[0]] * 1e12,
        "first_half_turn_timing_diagnostic_ps": trace.time[half_index] * 1e12 if half_index is not None else None,
        "first_half_turn_diagnostic_found": half_index is not None,
        "max_continuous_relative_phase_turns": max(relative),
        "min_continuous_relative_phase_turns": min(relative),
        "final_continuous_relative_phase_turns": relative[-1],
        "not_event_time": True,
        "not_event_count": True,
        "scientific_interpretation_performed": False,
    }


def signed_component_areas(trace: Any, label: str, window: tuple[float, float]) -> dict[str, Any]:
    times, values = selected(trace, label, window)
    positive = tuple(max(value, 0.0) for value in values)
    negative = tuple(min(value, 0.0) for value in values)
    return {
        "positive_A_s": trapezoid(times, positive) if len(times) >= 2 else None,
        "negative_A_s": trapezoid(times, negative) if len(times) >= 2 else None,
        "window_ps": [window[0] * 1e12, window[1] * 1e12],
        "formula": "trapezoid(actual stored time grid, max(V,0) or min(V,0))",
        "status": "DERIVED" if len(times) >= 2 else "UNKNOWN",
    }


def mechanical_case(case_id: str, trace: Any) -> tuple[dict[str, Any], dict[str, float | None]]:
    params = CASE_PARAMS[case_id]
    phase = {"BJ1": phase_diagnostic(trace, "P(BJ1|XBQ1)"), "BJ2": phase_diagnostic(trace, "P(BJ2|XBQ1)")}
    current_descriptives = {
        label: extrema(trace, label)
        for label in ("I(L1|XBQ1)", "I(L2|XBQ1)", "I(RJ1|XBQ1)", "I(B_JSL8)", "I(LIN|XBQ1)", "V(QBIN)", "V(COMMON_SL)")
    }
    source_areas: dict[str, Any] = {}
    ratio_inputs: dict[str, float | None] = {}
    for label in ("I(B_JSL8)", "I(LIN|XBQ1)"):
        for window_name, window in WINDOWS.items():
            value = area(trace, label, window)
            source_areas[f"{label}:{window_name}"] = {
                "value_A_s": value,
                "window_ps": [window[0] * 1e12, window[1] * 1e12],
                "formula": "trapezoid(actual stored time grid, values)",
                "status": "DERIVED" if value is not None else "UNKNOWN",
            }
            if window_name == "EARLY_READ":
                ratio_inputs[f"{label}:EARLY_READ"] = value
        ratio_inputs[f"{label}:PRE_SWITCH_PROXY"] = area(trace, label, PRE_SWITCH_WINDOW)
    bj1_voltage = signed_component_areas(trace, "V(BJ1|XBQ1)", WINDOWS["EARLY_READ"])
    times, voltage = selected(trace, "V(RJ1|XBQ1)", WINDOWS["EARLY_READ"])
    current_times = window_indices(trace.time, *WINDOWS["EARLY_READ"])
    current = tuple(float(trace.column("I(RJ1|XBQ1)")[index]) for index in current_times)
    energy = trapezoid(times, tuple(v * i for v, i in zip(voltage, current))) if len(times) >= 2 else None
    result = {
        "case_id": case_id,
        "L1_pH": params["L1_pH"],
        "IBias_uA": params["IBias_uA"],
        "RJ1_ohm": 12.0,
        "mask": case_id.rsplit("_", 1)[1],
        "source_experiment": source_experiment(case_id),
        "source_run": source_run(case_id),
        "physical_solve_this_experiment": case_id in NEW_RUNS,
        "scientific_interpretation_performed": False,
        "phase_diagnostics": phase,
        "current_voltage_descriptives": current_descriptives,
        "signed_actual_grid_areas_A_s": source_areas,
        "BJ1_voltage_final_read_area": bj1_voltage,
        "RJ1_dissipated_energy_final_read": {
            "value_J": energy,
            "window_ps": [110.0, 121.0],
            "formula": "trapezoid(actual stored time grid, V(RJ1|XBQ1)*I(RJ1|XBQ1))",
            "orientation": "as emitted by the registered JoSIM branch labels; no sign correction",
            "status": "DERIVED" if energy is not None else "UNKNOWN",
        },
        "raw_provenance": {"path": str(raw_path(case_id).relative_to(REPO)), "sha256": sha256(raw_path(case_id))},
        "notes": [
            "Mechanical arithmetic only.",
            "First +0.5-turn value is a timing/navigation diagnostic, not an event time.",
            "Continuous phase displacement is not an SFQ count or fluxoid count.",
            "Signed areas and energy use the actual stored time grid and half-open windows.",
        ],
    }
    return result, ratio_inputs


def ratio_record(numerator: float | None, denominator: float | None, *, metric: str, unit: str, denominator_abs_area: float | None = None) -> dict[str, Any]:
    if numerator is None or denominator is None or not math.isfinite(numerator) or not math.isfinite(denominator):
        return {"status": "UNKNOWN", "ratio": None, "metric": metric, "unit": unit, "reason": "missing_or_nonfinite_operand"}
    if metric == "peak_abs_current":
        if abs(denominator) <= RATIO_PEAK_TOLERANCE_A:
            return {"status": "UNKNOWN", "ratio": None, "metric": metric, "unit": unit, "reason": "denominator_at_or_below_1e-12_A"}
    else:
        if abs(denominator) <= RATIO_AREA_TOLERANCE_A_S:
            return {"status": "UNKNOWN", "ratio": None, "metric": metric, "unit": unit, "reason": "denominator_at_or_below_1e-18_A_s"}
        if denominator_abs_area is not None and abs(denominator) < RATIO_CANCELLATION_FRACTION * denominator_abs_area:
            return {"status": "UNKNOWN", "ratio": None, "metric": metric, "unit": unit, "reason": "signed_area_is_cancellation_sensitive_below_1_percent_of_absolute_area"}
    return {"status": "DERIVED", "ratio": numerator / denominator, "metric": metric, "unit": unit, "numerator": numerator, "denominator": denominator}


def absolute_area(trace: Any, label: str, window: tuple[float, float]) -> float | None:
    times, values = selected(trace, label, window)
    return trapezoid(times, tuple(abs(value) for value in values)) if len(times) >= 2 else None


def grid_ratios(traces: dict[str, Any], inputs: dict[str, dict[str, float | None]]) -> dict[str, Any]:
    output: dict[str, Any] = OrderedDict()
    for (l1, ibias), (mask0001, mask0011) in GRID_CASES.items():
        output[f"L1P{int(round(l1 * 10)):02d}_IB{int(ibias)}"] = {
            "L1_pH": l1,
            "IBias_uA": ibias,
            "mask_0001_case_id": mask0001,
            "mask_0011_case_id": mask0011,
            "ratio_semantics": "0011 numerator / 0001 denominator; mechanical diagnostic only",
            "I(B_JSL8)_peak": ratio_record(
                max(abs(value) for value in traces[mask0011].column("I(B_JSL8)")),
                max(abs(value) for value in traces[mask0001].column("I(B_JSL8)")),
                metric="peak_abs_current", unit="A",
            ),
            "I(B_JSL8)_EARLY_READ_signed_area": ratio_record(
                inputs[mask0011]["I(B_JSL8):EARLY_READ"], inputs[mask0001]["I(B_JSL8):EARLY_READ"],
                metric="signed_area", unit="A_s", denominator_abs_area=absolute_area(traces[mask0001], "I(B_JSL8)", WINDOWS["EARLY_READ"]),
            ),
            "I(LIN)_EARLY_READ_signed_area": ratio_record(
                inputs[mask0011]["I(LIN|XBQ1):EARLY_READ"], inputs[mask0001]["I(LIN|XBQ1):EARLY_READ"],
                metric="signed_area", unit="A_s", denominator_abs_area=absolute_area(traces[mask0001], "I(LIN|XBQ1)", WINDOWS["EARLY_READ"]),
            ),
            "MECHANICAL_PRE_SWITCH_PROXY": {
                "window_ps": [110.0, 114.5],
                "I(B_JSL8)_signed_area_ratio": ratio_record(
                    inputs[mask0011]["I(B_JSL8):PRE_SWITCH_PROXY"], inputs[mask0001]["I(B_JSL8):PRE_SWITCH_PROXY"],
                    metric="signed_area", unit="A_s", denominator_abs_area=absolute_area(traces[mask0001], "I(B_JSL8)", PRE_SWITCH_WINDOW),
                ),
                "I(LIN)_signed_area_ratio": ratio_record(
                    inputs[mask0011]["I(LIN|XBQ1):PRE_SWITCH_PROXY"], inputs[mask0001]["I(LIN|XBQ1):PRE_SWITCH_PROXY"],
                    metric="signed_area", unit="A_s", denominator_abs_area=absolute_area(traces[mask0001], "I(LIN|XBQ1)", PRE_SWITCH_WINDOW),
                ),
                "label": "MECHANICAL_PRE_SWITCH_PROXY; not proof of linear population scaling",
            },
        }
    return output


def deck_diff() -> dict[str, Any]:
    failures: list[str] = []
    normalized: set[tuple[str, ...]] = set()
    pre_read: set[tuple[str, ...]] = set()
    pair_checks: dict[str, Any] = {}
    records: dict[str, Any] = {}
    bq = BQ400.read_text(encoding="utf-8")
    if "BJs 1 2 jjmit area=4" not in bq or "BJs 1 2 jjmit area=3" in bq:
        failures.append("BJS400 source is not exactly area=4")
    for run_id in NEW_RUNS:
        deck = deck_path(run_id)
        text = deck.read_text(encoding="utf-8")
        params = NEW_RUN_PARAMETERS[run_id]
        mask = RUN_TO_MASK[run_id]
        for required in (f".param L1_VALUE={params['L1_pH']:g}p", f".param IB_VALUE={params['IBias_uA']:g}u", ".param RJ1_VALUE=12", ".tran 0.1p 200p", "P(BJS|XBQ1) V(BJS|XBQ1) I(BJS|XBQ1)"):
            if required not in text:
                failures.append(f"{run_id}: missing {required}")
        if any(text.count(f"XBVM{index} ") != 1 for index in range(1, 5)):
            failures.append(f"{run_id}: BVM topology count mismatch")
        for instance in range(1, 5):
            for kind in CONTROL_KINDS:
                if control_line(instance, kind, mask[instance - 1] == "1") not in text:
                    failures.append(f"{run_id}: control mismatch {kind}{instance}")
        normalized.add(normalized_deck(text))
        pre_read.add(pre_read_controls(text))
        records[run_id] = {"parameters": params, "mask": mask, "deck_sha256": sha256(deck), "deck_bytes": deck.stat().st_size}
    if len(normalized) != 1:
        failures.append("new decks differ outside registered L1/IBias and final-read mask substitutions")
    if len(pre_read) != 1:
        failures.append("new controls differ before 110ps")
    for point, pair in GRID_CASES.items():
        if pair[0] in NEW_RUNS and pair[1] in NEW_RUNS:
            before = pre_read_controls(deck_path(pair[0]).read_text(encoding="utf-8"))
            after = pre_read_controls(deck_path(pair[1]).read_text(encoding="utf-8"))
            pair_checks[f"{point[0]}_{point[1]}"] = {"pre_110ps_equal": before == after, "mask_pair": pair}
            if before != after:
                failures.append(f"{pair}: mask pair differs before final read")
    historical_failures: list[str] = []
    for run_id, spec in REUSE_SPECS.items():
        source_text = deck_path(run_id).read_text(encoding="utf-8")
        expected_text = build_deck(spec["L1_pH"], spec["IBias_uA"], spec["mask"])
        if normalized_deck(source_text) != normalized_deck(expected_text) or pre_read_controls(source_text) != pre_read_controls(expected_text):
            historical_failures.append(run_id)
    if historical_failures:
        failures.append("historical deck comparability failed: " + ",".join(historical_failures))
    return {
        "schema": "bjs400-l1-ibias-full-grid-deck-diff-qa-v1",
        "status": "PASS" if not failures else "FAIL",
        "new_run_count": len(NEW_RUNS),
        "reused_case_count": len(REUSE_RUNS),
        "exact_logical_case_count": len(ALL_CASES),
        "registered_parameters_only": True,
        "mask_pair_only_final_read_difference": len(pre_read) == 1,
        "normalized_new_decks_identical": len(normalized) == 1,
        "historical_deck_comparability": "PASS" if not historical_failures else "FAIL",
        "bjs400_source": "PASS" if "BJs 1 2 jjmit area=4" in bq and "BJs 1 2 jjmit area=3" not in bq else "FAIL",
        "pair_checks": pair_checks,
        "runs": records,
        "failures": failures,
    }


def main() -> int:
    preflight = json.loads((EXP / "analysis/preflight.json").read_text(encoding="utf-8"))
    relation = head_relation(str(preflight["head"]))
    execution = json.loads((EXP / "qa/execution_summary.json").read_text(encoding="utf-8"))
    execution_ok = (
        execution.get("status") == "PASS"
        and execution.get("solver_solve_invocations") == 10
        and execution.get("exact_new_physical_solve_count") == 10
        and execution.get("reused_physical_case_count") == 14
        and execution.get("unauthorized_extra_solves") == 0
        and execution.get("failed_runs") == []
    )
    reuse_manifest = json.loads((EXP / "REUSED_REFERENCE_MANIFEST.json").read_text(encoding="utf-8"))
    raw_records: dict[str, Any] = {}
    raw_failures: list[str] = []
    grid_hashes: set[str] = set()
    pre_hashes: dict[str, str] = {}
    traces: dict[str, Any] = {}
    mechanical: dict[str, Any] = OrderedDict()
    ratio_inputs: dict[str, dict[str, float | None]] = {}
    required = expected_probes()
    for case_id in ALL_CASES:
        path = raw_path(case_id)
        if not path.is_file():
            raw_failures.append(f"{case_id}: missing raw.csv")
            continue
        try:
            trace = read_csv(path)
        except Exception as exc:  # artifact failure is recorded, not relabeled as physical failure
            raw_failures.append(f"{case_id}: raw reader failure: {exc}")
            continue
        pre_hashes[case_id] = sha256(path)
        traces[case_id] = trace
        qa = trace.qa()
        missing = sorted(required - set(trace.headers))
        unknown = sorted(set(missing) & OPTIONAL_UNKNOWN)
        missing_required = sorted(set(missing) - OPTIONAL_UNKNOWN)
        grid_hash = hashlib.sha256("\n".join(f"{value:.17g}" for value in trace.time).encode()).hexdigest()
        grid_hashes.add(grid_hash)
        if trace.sample_count != 1999 or trace.time[0] != 0.0 or trace.time[-1] != 1.999e-10:
            raw_failures.append(f"{case_id}: time/sample range mismatch")
        if qa["nan_inf_status"] != "PASS" or not qa["strictly_increasing_time"]:
            raw_failures.append(f"{case_id}: finite/monotonic failure")
        if missing_required:
            raw_failures.append(f"{case_id}: missing required probes {','.join(missing_required)}")
        if case_id in REUSE_RUNS and pre_hashes[case_id] != reuse_manifest["references"][case_id]["artifacts"]["raw.csv"]["source_sha256"]:
            raw_failures.append(f"{case_id}: reused raw hash mismatch")
        raw_records[case_id] = {
            "case_id": case_id,
            "path": str(path.relative_to(REPO)),
            "sha256": pre_hashes[case_id],
            "bytes": path.stat().st_size,
            "header_count": len(trace.headers),
            "sample_count": trace.sample_count,
            "first_timestamp_s": trace.time[0],
            "last_timestamp_s": trace.time[-1],
            "stored_time_grid_sha256": grid_hash,
            "dt_min_s": min(trace.dt),
            "dt_max_s": max(trace.dt),
            "strictly_increasing_time": qa["strictly_increasing_time"],
            "finite_values": qa["nan_inf_status"] == "PASS",
            "duplicate_columns": trace.duplicate_columns,
            "required_probe_status": "UNKNOWN" if unknown and not missing_required else ("PASS" if not missing else "FAIL"),
            "missing_probes": missing,
            "unknown_probes": unknown,
            "physical_solve_this_experiment": case_id in NEW_RUNS,
            "raw_immutable": True,
        }
        try:
            case_summary, inputs = mechanical_case(case_id, trace)
            mechanical[case_id] = case_summary
            ratio_inputs[case_id] = inputs
        except Exception as exc:
            raw_failures.append(f"{case_id}: mechanical arithmetic failure: {exc}")
    post_hashes = {case_id: sha256(raw_path(case_id)) for case_id in pre_hashes}
    raw_ok = not raw_failures and len(traces) == len(ALL_CASES) and len(grid_hashes) == 1 and pre_hashes == post_hashes
    raw_qa = {
        "schema": "bjs400-l1-ibias-full-grid-raw-qa-v1",
        "status": "PASS" if raw_ok else "FAIL",
        "artifact_validity": "VALID" if raw_ok else "INVALID",
        "experiment_id": EXP.name,
        "created_at_local": now(),
        "head": relation["head"],
        "execution_status": "PASS" if execution_ok else "FAIL",
        "new_physical_solve_count": len(NEW_RUNS),
        "reused_physical_case_count": len(REUSE_RUNS),
        "exact_logical_case_count": len(ALL_CASES),
        "unauthorized_extra_solves": 0,
        "cases": raw_records,
        "pre_analysis_sha256": pre_hashes,
        "post_analysis_sha256": post_hashes,
        "raw_unchanged_pre_to_post": pre_hashes == post_hashes,
        "common_time_grid": len(grid_hashes) == 1,
        "stored_grid_hashes": sorted(grid_hashes),
        "required_probe_missing_is_not_fabricated": True,
        "raw_files_modified": 0,
        "scientific_analysis_performed": False,
        "failures": raw_failures,
    }
    decks = deck_diff()
    ratios = grid_ratios(traces, ratio_inputs) if raw_ok else {}
    mechanical_status = "PASS" if raw_ok and decks["status"] == "PASS" and len(mechanical) == len(ALL_CASES) else "FAIL"
    mechanical_summary = {
        "schema": "bjs400-l1-ibias-full-grid-mechanical-summary-v1",
        "experiment_id": EXP.name,
        "created_at_local": now(),
        "status": mechanical_status,
        "scientific_interpretation_performed": False,
        "grid": {
            "L1_pH": list(L1_VALUES),
            "IBias_uA": list(IBIAS_VALUES),
            "masks": list(MASKS),
            "logical_case_count": len(ALL_CASES),
            "historical_reuse_count": len(REUSE_RUNS),
            "new_physical_solve_count": len(NEW_RUNS),
            "case_order": list(ALL_CASES),
            "point_case_order": {f"L1P{int(round(l1 * 10)):02d}_IB{int(ibias)}": list(pair) for (l1, ibias), pair in GRID_CASES.items()},
        },
        "phase_convention": "raw P radians; continuous_unwrap(raw)/(2*pi) for display/diagnostic only",
        "first_half_turn_is_not_event_time_or_event_count": True,
        "windows": {
            "phase_baseline_ps": [101.0, 110.0],
            "phase_post_read_ps": [110.0, 200.0],
            "EARLY_READ_ps": [110.0, 121.0],
            "TAIL_ps": [121.0, 200.0],
            "MECHANICAL_PRE_SWITCH_PROXY_ps": [110.0, 114.5],
            "semantics": "half-open; actual stored timestamps; no interpolation or resampling",
        },
        "ratio_policy": {
            "numerator_denominator": "0011 / 0001",
            "peak_abs_current_tolerance_A": RATIO_PEAK_TOLERANCE_A,
            "signed_area_tolerance_A_s": RATIO_AREA_TOLERANCE_A_S,
            "cancellation_fraction": RATIO_CANCELLATION_FRACTION,
            "ambiguous_ratio_status": "UNKNOWN",
        },
        "cases": mechanical,
        "ratio_diagnostics": ratios,
        "notes": [
            "All fields are MECHANICAL or DERIVED arithmetic, not scientific classifications.",
            "No cell is labeled PASS, FAIL, GOOD, BAD, OPTIMAL, under-driven, discriminating or over-driven.",
            "No phase displacement, voltage area, threshold or current sign is an SFQ count or event classifier.",
            "Scientific interpretation is NOT_PERFORMED.",
        ],
    }
    provenance = {
        "schema": "bjs400-l1-ibias-full-grid-provenance-v1",
        "experiment_id": EXP.name,
        "head_at_qa": relation["head"],
        "preflight": "analysis/preflight.json",
        "source_manifest": "SOURCE_MANIFEST.json",
        "reuse_manifest": "REUSED_REFERENCE_MANIFEST.json",
        "execution_summary": "qa/execution_summary.json",
        "mechanical_summary": "mechanical_summary.json",
        "solver": "build/josim-cli",
        "new_runs": {
            run_id: {
                "deck": str(deck_path(run_id).relative_to(REPO)),
                "deck_sha256": sha256(deck_path(run_id)),
                "raw": str(raw_path(run_id).relative_to(REPO)),
                "raw_sha256": pre_hashes.get(run_id),
                "metadata": str((EXP / "runs" / run_id / "metadata.json").relative_to(REPO)),
                "run_log": str((EXP / "runs" / run_id / "run.log").relative_to(REPO)),
                "physical_solve_this_experiment": True,
            }
            for run_id in NEW_RUNS
        },
        "reused_runs": {
            run_id: {
                "reference": str((EXP / "references/reused" / run_id).relative_to(REPO)),
                "source_experiment": source_experiment(run_id),
                "source_run": source_run(run_id),
                "raw_sha256": pre_hashes.get(run_id),
                "deck_sha256": sha256(deck_path(run_id)),
                "physical_solve_this_experiment": False,
            }
            for run_id in REUSE_RUNS
        },
        "all_24_logical_cases": list(ALL_CASES),
        "scientific_analysis_performed": False,
    }
    provenance["runs"] = {**provenance["new_runs"], **provenance["reused_runs"]}
    transformations = {
        "schema": "bjs400-l1-ibias-full-grid-transformation-registry-v1",
        "raw_immutable": True,
        "scientific_analysis_performed": False,
        "transformations": [
            {"name": "mechanical_summary", "operation": "actual-grid extrema, continuous phase diagnostic, signed components, energy and registered ratios", "scope": "mechanical arithmetic only"},
            {"name": "phase_display", "operation": "continuous_unwrap(raw_rad)/(2*pi)", "scope": "diagnostic/display only", "not_event_count": True},
            {"name": "area_integration", "operation": "trapezoid on actual stored time values; half-open registered windows", "scope": "mechanical arithmetic only", "interpolation": False},
            {"name": "standalone_plot_input", "operation": "raw.csv direct; no crop/resample/derived CSV", "scope": "visualization"},
            {"name": "comparison_plot_input", "operation": "temporary full-run merged CSV under /tmp only; deleted after render", "scope": "visualization"},
        ],
    }
    write_json(EXP / "qa/raw_qa.json", raw_qa)
    write_json(EXP / "qa/deck_diff_qa.json", decks)
    write_json(EXP / "mechanical_summary.json", mechanical_summary)
    write_json(EXP / "qa/provenance.json", provenance)
    write_json(EXP / "qa/transformation_registry.json", transformations)
    result = {
        "status": "PASS" if raw_ok and decks["status"] == "PASS" and execution_ok and relation["status"] == "PASS" and mechanical_status == "PASS" else "FAIL",
        "execution_status": "PASS" if execution_ok else "FAIL",
        "raw_status": raw_qa["status"],
        "deck_status": decks["status"],
        "mechanical_summary_status": mechanical_status,
        "head_relation": relation["relation"],
        "logical_case_count": len(ALL_CASES),
        "raw_failures": raw_failures,
        "scientific_analysis_performed": False,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
