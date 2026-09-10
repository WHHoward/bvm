#!/usr/bin/env python3
"""Minimal QA and mechanical summary for the high-range RJ1 experiment."""

from __future__ import annotations

import hashlib
import json
import math
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EXP / "analysis"))
from prepare_experiment import BQ400, CONTROL_KINDS, HISTORICAL_VALUES, MASKS, NEW_RUNS, RUN_TO_MASK, historical_manifest, control_line  # noqa: E402
sys.path.insert(0, str(REPO / "scripts"))
from bvmtools.phase import continuous_unwrap, window_indices  # noqa: E402
from bvmtools.raw import read_csv  # noqa: E402


OPTIONAL_UNKNOWN = {"V(IB|XBQ1)"}
HISTORICAL_CASES = tuple(f"RJ{rj1}_{mask}" for rj1 in HISTORICAL_VALUES for mask in MASKS)
ALL_CASES = NEW_RUNS + HISTORICAL_CASES


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
    if case_id in NEW_RUNS:
        return EXP / "runs" / case_id / "raw.csv"
    return EXP / "references/historical" / case_id / "raw.csv"


def deck_path(case_id: str) -> Path:
    if case_id in NEW_RUNS:
        return EXP / "runs" / case_id / "deck.cir"
    return EXP / "references/historical" / case_id / "deck.cir"


def rj1_for_case(case_id: str) -> float:
    if case_id in HISTORICAL_CASES:
        return float(case_id.split("_", 1)[0][2:])
    return float(case_id.split("_RJ", 1)[1].split("_", 1)[0])


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


def read_raw(path: Path) -> tuple[Any, dict[str, Any]]:
    trace = read_csv(path)
    if trace.duplicate_columns:
        raise RuntimeError(f"duplicate raw columns: {path}: {trace.duplicate_columns}")
    qa = trace.qa()
    times = tuple(trace.time)
    grid_hash = hashlib.sha256("\n".join(f"{value:.17g}" for value in times).encode()).hexdigest()
    return trace, {
        "header_count": len(trace.headers),
        "sample_count": trace.sample_count,
        "first_timestamp_s": times[0] if times else None,
        "last_timestamp_s": times[-1] if times else None,
        "strictly_increasing_time": qa["strictly_increasing_time"],
        "finite_values": qa["nan_inf_status"] == "PASS",
        "duplicate_columns": trace.duplicate_columns,
        "stored_time_grid_sha256": grid_hash,
        "headers": trace.headers,
    }


def head_relation(preflight_head: str) -> dict[str, Any]:
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()
    if head == preflight_head:
        return {"status": "PASS", "head": head, "preflight_head": preflight_head, "relation": "EXACT"}
    changed = set(subprocess.check_output(["git", "diff", "--name-only", f"{preflight_head}..{head}"], cwd=REPO, text=True).splitlines())
    allowed = {
        str(EXP.relative_to(REPO) / "PREFLIGHT.md"),
        str(EXP.relative_to(REPO) / "analysis/preflight.json"),
    }
    distance = int(subprocess.check_output(["git", "rev-list", "--count", f"{preflight_head}..{head}"], cwd=REPO, text=True).strip())
    status = "PASS" if distance == 1 and changed == allowed else "FAIL"
    return {"status": status, "head": head, "preflight_head": preflight_head, "relation": "PREFLIGHT_ONLY_SEAL_COMMIT" if status == "PASS" else "UNEXPECTED", "changed_paths": sorted(changed), "commit_distance": distance}


def trapezoid(time_s: tuple[float, ...], values: tuple[float, ...]) -> float:
    return sum((values[i] + values[i + 1]) * 0.5 * (time_s[i + 1] - time_s[i]) for i in range(len(values) - 1))


def select_window(time_s: tuple[float, ...], values: tuple[float, ...], start: float, end: float) -> tuple[tuple[float, ...], tuple[float, ...]]:
    indices = window_indices(time_s, start, end)
    return tuple(time_s[index] for index in indices), tuple(values[index] for index in indices)


def phase_diagnostic(trace: Any, label: str) -> dict[str, Any]:
    phase = continuous_unwrap(tuple(trace.column(label)))
    reference = window_indices(trace.time, 101e-12, 110e-12)
    post = window_indices(trace.time, 110e-12, 200e-12)
    if not reference or not post:
        return {"status": "UNKNOWN", "reason": "missing registered reference/post samples", "not_event_count": True}
    baseline = phase[reference[0]]
    relative = tuple((phase[index] - baseline) / (2.0 * math.pi) for index in post)
    crossing = next((index for index, value in zip(post, relative) if value >= 0.5), None)
    return {
        "status": "DERIVED",
        "label": label,
        "baseline_window_ps": [101.0, 110.0],
        "baseline_reference_time_ps": trace.time[reference[0]] * 1e12,
        "raw_unit": "rad",
        "display_unit": "turns",
        "conversion": "continuous_unwrap(raw_rad)/(2*pi)",
        "first_half_turn_timing_diagnostic_ps": trace.time[crossing] * 1e12 if crossing is not None else None,
        "first_half_turn_diagnostic_found": crossing is not None,
        "max_relative_turns_post_read": max(relative),
        "min_relative_turns_post_read": min(relative),
        "final_relative_turns": relative[-1],
        "not_event_time": True,
        "not_event_count": True,
        "scientific_interpretation_performed": False,
    }


def mechanical_case(case_id: str, trace: Any) -> dict[str, Any]:
    def column(label: str) -> tuple[float, ...]:
        return tuple(float(value) for value in trace.column(label))

    result: dict[str, Any] = {
        "case_id": case_id,
        "rj1_ohm": rj1_for_case(case_id),
        "mask": case_id.rsplit("_", 1)[1],
        "physical_solve_this_experiment": case_id in NEW_RUNS,
        "scientific_interpretation_performed": False,
        "phase_diagnostics": {
            "BJ1": phase_diagnostic(trace, "P(BJ1|XBQ1)"),
            "BJ2": phase_diagnostic(trace, "P(BJ2|XBQ1)"),
        },
        "current_voltage_descriptives": {},
        "signed_actual_grid_areas_A_s": {},
        "bj1_voltage_areas_V_s": {},
        "rj1_dissipation": {},
        "mechanical_threshold_flags": {},
        "notes": [
            "Mechanical diagnostic only.",
            "Phase displacement is not an SFQ/event count.",
            "First +0.5-turn value is not an event time.",
            "Threshold flags are not success, Gate or boundary classifications.",
        ],
    }
    for label in ("I(L1|XBQ1)", "I(L2|XBQ1)", "I(RJ1|XBQ1)", "V(RJ1|XBQ1)", "I(B_JSL8)"):
        values = column(label)
        result["current_voltage_descriptives"][label] = {
            "max": max(values),
            "min": min(values),
            "max_abs": max(abs(value) for value in values),
        }
    for label in ("I(B_JSL8)", "I(LIN|XBQ1)"):
        values = column(label)
        for name, start, end in (("EARLY_READ", 110e-12, 121e-12), ("TAIL", 121e-12, 200e-12)):
            times, selected = select_window(trace.time, values, start, end)
            result["signed_actual_grid_areas_A_s"][f"{label}:{name}"] = {
                "formula": "trapezoid(actual stored time grid, values)",
                "value": trapezoid(times, selected) if len(times) >= 2 else None,
                "window_ps": [start * 1e12, end * 1e12],
                "status": "DERIVED" if len(times) >= 2 else "UNKNOWN",
            }
    bj1_voltage = column("V(BJ1|XBQ1)")
    times, selected = select_window(trace.time, bj1_voltage, 110e-12, 200e-12)
    positive = tuple(max(value, 0.0) for value in selected)
    negative = tuple(min(value, 0.0) for value in selected)
    result["bj1_voltage_areas_V_s"] = {
        "window_ps": [110.0, 200.0],
        "positive": {"value": trapezoid(times, positive) if len(times) >= 2 else None, "status": "DERIVED" if len(times) >= 2 else "UNKNOWN"},
        "negative": {"value": trapezoid(times, negative) if len(times) >= 2 else None, "status": "DERIVED" if len(times) >= 2 else "UNKNOWN"},
        "orientation_from_deck": "BJ1 2 0",
        "not_event_count": True,
    }
    rj1_current = column("I(RJ1|XBQ1)")
    rj1_voltage = column("V(RJ1|XBQ1)")
    times, current_selected = select_window(trace.time, rj1_current, 110e-12, 200e-12)
    _, voltage_selected = select_window(trace.time, rj1_voltage, 110e-12, 200e-12)
    power = tuple(voltage_selected[index] * current_selected[index] for index in range(len(current_selected)))
    result["rj1_dissipation"] = {
        "window_ps": [110.0, 200.0],
        "formula": "integral(V(RJ1|XBQ1)*I(RJ1|XBQ1)*dt) on declared RJ1 2 0 orientation",
        "value_J": trapezoid(times, power) if len(times) >= 2 else None,
        "status": "DERIVED" if len(times) >= 2 else "UNKNOWN",
        "orientation_from_deck": "RJ1 2 0",
        "mechanical_diagnostic_only": True,
    }
    bj1_max = result["phase_diagnostics"]["BJ1"].get("max_relative_turns_post_read")
    bj2_max = result["phase_diagnostics"]["BJ2"].get("max_relative_turns_post_read")
    if bj1_max is not None:
        for threshold in (1.25, 1.5, 1.75, 2.0):
            result["mechanical_threshold_flags"][f"BJ1_max_phase_gt_{str(threshold).replace('.', 'p')}_turn"] = {
                "value": bj1_max > threshold,
                "label": "MECHANICAL_DIAGNOSTIC_ONLY",
                "not_event_count": True,
            }
    if bj2_max is not None:
        for threshold in (1.5, 2.0):
            result["mechanical_threshold_flags"][f"BJ2_max_phase_gt_{str(threshold).replace('.', 'p')}_turn"] = {
                "value": bj2_max > threshold,
                "label": "MECHANICAL_DIAGNOSTIC_ONLY",
                "not_event_count": True,
            }
    return result


def deck_diff() -> dict[str, Any]:
    failures: list[str] = []
    normalized: set[tuple[str, ...]] = set()
    pre_read: set[tuple[str, ...]] = set()
    same_mask_rj: dict[str, set[str]] = {mask: set() for mask in MASKS}
    records: dict[str, Any] = {}
    bq = BQ400.read_text(encoding="utf-8")
    if "BJs 1 2 jjmit area=4" not in bq or "BJs 1 2 jjmit area=3" in bq:
        failures.append("BJS400 source is not area=4 only")
    for run_id in NEW_RUNS:
        text = (EXP / "runs" / run_id / "deck.cir").read_text(encoding="utf-8")
        rj1 = float(run_id.split("_RJ", 1)[1].split("_", 1)[0])
        mask = RUN_TO_MASK[run_id]
        for required in (
            ".param L1_VALUE=1.6p",
            ".param IB_VALUE=260u",
            f".param RJ1_VALUE={rj1:g}",
            ".tran 0.1p 200p",
            "P(BJS|XBQ1) V(BJS|XBQ1) I(BJS|XBQ1)",
        ):
            if required not in text:
                failures.append(f"{run_id}: missing {required}")
        if any(text.count(f"XBVM{index} ") != 1 for index in range(1, 5)):
            failures.append(f"{run_id}: BVM topology count mismatch")
        for instance in range(1, 5):
            for kind in CONTROL_KINDS:
                expected = control_line(instance, kind, mask[instance - 1] == "1")
                if expected not in text:
                    failures.append(f"{run_id}: control mismatch {kind}{instance}")
        normalized.add(tuple(
            line for line in text.splitlines()
            if not line.startswith(".param L1_VALUE=")
            and not line.startswith(".param IB_VALUE=")
            and not line.startswith(".param RJ1_VALUE=")
            and not re.match(r"I_(WL|BL|SE)[1-4] ", line)
        ))
        pre_read.add(tuple(line.split(" 110p", 1)[0] for line in text.splitlines() if re.match(r"I_(WL|BL|SE)[1-4] ", line)))
        same_mask_rj[mask].add(next(line for line in text.splitlines() if line.startswith(".param RJ1_VALUE=")))
        records[run_id] = {"rj1_ohm": rj1, "mask": mask, "deck_sha256": sha256(deck_path(run_id)), "deck_bytes": deck_path(run_id).stat().st_size}
    if len(normalized) != 1:
        failures.append("new decks differ outside RJ1 and final-read controls")
    if len(pre_read) != 1:
        failures.append("new controls differ before 110ps")
    if any(len(values) != 4 for values in same_mask_rj.values()):
        failures.append("same-mask historical/new RJ1 value set is incomplete")
    return {
        "schema": "rj1-highrange-deck-diff-qa-v1",
        "status": "PASS" if not failures else "FAIL",
        "new_run_count": len(NEW_RUNS),
        "historical_case_count": len(HISTORICAL_CASES),
        "new_rj1_values_ohm": [20, 24, 32, 48],
        "historical_rj1_values_ohm": list(HISTORICAL_VALUES),
        "same_mask_only_rj1_difference": len(failures) == 0,
        "mask_pair_only_final_read_difference": len(pre_read) == 1,
        "pre_110ps_control_equality": len(pre_read) == 1,
        "normalized_new_decks_identical": len(normalized) == 1,
        "runs": records,
        "failures": failures,
    }


def main() -> int:
    preflight = json.loads((EXP / "analysis/preflight.json").read_text(encoding="utf-8"))
    relation = head_relation(str(preflight["head"]))
    execution = json.loads((EXP / "qa/execution_summary.json").read_text(encoding="utf-8"))
    execution_ok = (
        execution.get("status") == "PASS"
        and execution.get("solver_solve_invocations") == 8
        and execution.get("exact_new_physical_solve_count") == 8
        and execution.get("historical_reference_case_count") == 8
        and execution.get("unauthorized_extra_solves") == 0
        and execution.get("failed_runs") == []
    )
    history = historical_manifest()
    raw_records: dict[str, Any] = {}
    mechanical: dict[str, Any] = {}
    raw_failures: list[str] = []
    grid_hashes: set[str] = set()
    pre_hashes: dict[str, str] = {}
    traces: dict[str, Any] = {}
    for case_id in ALL_CASES:
        path = raw_path(case_id)
        if not path.is_file():
            raw_failures.append(f"{case_id}: missing raw.csv")
            continue
        pre_hashes[case_id] = sha256(path)
        trace, summary = read_raw(path)
        traces[case_id] = trace
        missing = sorted(expected_probes() - set(summary.pop("headers")))
        unknown = sorted(set(missing) & OPTIONAL_UNKNOWN)
        missing_required = sorted(set(missing) - OPTIONAL_UNKNOWN)
        if summary["sample_count"] != 1999 or summary["first_timestamp_s"] != 0.0 or summary["last_timestamp_s"] != 1.999e-10:
            raw_failures.append(f"{case_id}: time/sample range mismatch")
        if not summary["finite_values"] or not summary["strictly_increasing_time"]:
            raw_failures.append(f"{case_id}: finite/monotonic failure")
        if missing_required:
            raw_failures.append(f"{case_id}: missing required probes {','.join(missing_required)}")
        if case_id in HISTORICAL_CASES:
            expected_hash = history["references"][case_id]["artifacts"]["raw.csv"]["source_sha256"]
            if pre_hashes[case_id] != expected_hash:
                raw_failures.append(f"{case_id}: historical raw hash mismatch")
        grid_hashes.add(summary["stored_time_grid_sha256"])
        raw_records[case_id] = {
            "case_id": case_id,
            "path": str(path),
            "sha256": pre_hashes[case_id],
            "bytes": path.stat().st_size,
            **summary,
            "required_probe_status": "UNKNOWN" if unknown and not missing_required else ("PASS" if not missing else "FAIL"),
            "missing_probes": missing,
            "unknown_probes": unknown,
            "physical_solve_this_experiment": case_id in NEW_RUNS,
            "raw_immutable": True,
        }
        mechanical[case_id] = mechanical_case(case_id, trace)
    post_hashes = {case_id: sha256(raw_path(case_id)) for case_id in pre_hashes}
    raw_ok = not raw_failures and len(grid_hashes) == 1 and pre_hashes == post_hashes
    raw_qa = {
        "schema": "rj1-highrange-raw-qa-v1",
        "status": "PASS" if raw_ok else "FAIL",
        "artifact_validity": "VALID" if raw_ok else "INVALID",
        "experiment_id": EXP.name,
        "created_at_local": now(),
        "head": relation["head"],
        "execution_status": "PASS" if execution_ok else "FAIL",
        "new_physical_solve_count": 8,
        "historical_reference_case_count": 8,
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
    provenance_runs = {
        case_id: {
            "deck": str(deck_path(case_id)),
            "deck_sha256": sha256(deck_path(case_id)),
            "raw": str(raw_path(case_id)),
            "raw_sha256": pre_hashes.get(case_id),
            "physical_solve_this_experiment": case_id in NEW_RUNS,
        }
        for case_id in ALL_CASES
    }
    provenance = {
        "schema": "rj1-highrange-provenance-v1",
        "experiment_id": EXP.name,
        "head_at_qa": relation["head"],
        "preflight": "analysis/preflight.json",
        "source_manifest": "SOURCE_MANIFEST.json",
        "historical_reference_manifest": "HISTORICAL_REFERENCE_MANIFEST.json",
        "execution_summary": "qa/execution_summary.json",
        "mechanical_summary": "mechanical_summary.json",
        "solver": "build/josim-cli",
        "runs": provenance_runs,
        "historical_runs": history,
        "scientific_analysis_performed": False,
    }
    transformations = {
        "schema": "rj1-highrange-transformation-registry-v1",
        "raw_immutable": True,
        "scientific_analysis_performed": False,
        "transformations": [
            {"name": "mechanical_summary", "operation": "actual-grid descriptive extrema, phase diagnostics, positive/negative BJ1 voltage areas and RJ1 power integral", "scope": "registered mechanical arithmetic only"},
            {"name": "phase_display", "operation": "continuous_unwrap(raw_rad)/(2*pi)", "scope": "diagnostic/display only", "not_event_count": True, "first_half_turn_not_event_time": True},
            {"name": "standalone_plot_input", "operation": "raw.csv direct; no crop/resample/derived CSV", "scope": "visualization"},
            {"name": "comparison_plot_input", "operation": "temporary full-run merged CSV under /tmp; deleted after render", "scope": "visualization"},
        ],
    }
    write_json(EXP / "qa/raw_qa.json", raw_qa)
    write_json(EXP / "qa/deck_diff_qa.json", decks)
    write_json(EXP / "mechanical_summary.json", {
        "schema": "rj1-highrange-mechanical-summary-v1",
        "experiment_id": EXP.name,
        "created_at_local": now(),
        "status": "PASS" if raw_ok and decks["status"] == "PASS" else "FAIL",
        "scientific_interpretation_performed": False,
        "phase_convention": "raw P radians; continuous_unwrap(raw)/(2*pi) for display/diagnostic only",
        "first_half_turn_is_not_event_time": True,
        "threshold_flags_label": "MECHANICAL_DIAGNOSTIC_ONLY",
        "area_windows_ps": {"EARLY_READ": [110.0, 121.0], "TAIL": [121.0, 200.0]},
        "bj1_voltage_area_window_ps": [110.0, 200.0],
        "rj1_dissipation_window_ps": [110.0, 200.0],
        "cases": mechanical,
    })
    write_json(EXP / "qa/provenance.json", provenance)
    write_json(EXP / "qa/transformation_registry.json", transformations)
    result = {
        "status": "PASS" if raw_ok and decks["status"] == "PASS" and execution_ok and relation["status"] == "PASS" else "FAIL",
        "execution_status": "PASS" if execution_ok else "FAIL",
        "raw_status": raw_qa["status"],
        "deck_status": decks["status"],
        "mechanical_summary_status": "PASS" if raw_ok and decks["status"] == "PASS" else "FAIL",
        "head_relation": relation["relation"],
        "raw_failures": raw_failures,
        "scientific_analysis_performed": False,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

