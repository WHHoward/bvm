#!/usr/bin/env python3
"""Mechanical QA and registered arithmetic for the 12-run experiment.

This script reads raw evidence only.  It does not invoke JoSIM and does not
rank families or assign mechanism/physical conclusions.
"""

from __future__ import annotations

import hashlib
import json
import math
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import sys

REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
from bvmtools.phase import continuous_unwrap, window_indices  # noqa: E402
from bvmtools.raw import read_csv  # noqa: E402


NEW_RUNS = [
    ("L1_1P2", "L1", 12.0, 1.2, 250.0),
    ("L1_1P4", "L1", 12.0, 1.4, 250.0),
    ("L1_1P6", "L1", 12.0, 1.6, 250.0),
    ("L1_1P8", "L1", 12.0, 1.8, 250.0),
    ("IB_230", "IBias", 12.0, 2.0, 230.0),
    ("IB_240", "IBias", 12.0, 2.0, 240.0),
    ("IB_260", "IBias", 12.0, 2.0, 260.0),
    ("IB_270", "IBias", 12.0, 2.0, 270.0),
    ("RJ1_8", "RJ1", 8.0, 2.0, 250.0),
    ("RJ1_10", "RJ1", 10.0, 2.0, 250.0),
    ("RJ1_14", "RJ1", 14.0, 2.0, 250.0),
    ("RJ1_16", "RJ1", 16.0, 2.0, 250.0),
]
REUSED = ["L1_1P9", "NOMINAL", "L1_2P1", "RJ1_12P5", "RJ1_13"]
EXPECTED_PROBES = []
for instance in range(1, 5):
    header = f"XBVM{instance}"
    EXPECTED_PROBES.extend(
        f"{kind}({jj}|{header})"
        for jj in ("B_JM1", "B_JM2", "B_JS1", "B_JS2")
        for kind in ("P", "V", "I")
    )
    EXPECTED_PROBES.extend(
        f"{kind}({branch}|{header})"
        for branch in ("L_M1", "L_M2", "L_M3", "L_PM", "R_JM1", "L_S1", "L_S2", "R_S", "L_S3", "R_SE", "L_PSE", "L_PSL", "R_SL", "L_SL")
        for kind in ("I", "V")
    )
    EXPECTED_PROBES.extend((f"I(I_WL{instance})", f"I(I_BL{instance})", f"I(I_SE{instance})"))
EXPECTED_PROBES.append("V(COMMON_SL)")
for index in range(1, 9):
    EXPECTED_PROBES.extend((f"P(B_JSL{index})", f"V(B_JSL{index})", f"I(B_JSL{index})"))
EXPECTED_PROBES.extend(("V(QBIN)", "V(QBOUT)"))
for branch in ("LIN", "L1", "L2", "L3", "RJ1", "RJ2", "IB"):
    EXPECTED_PROBES.extend((f"I({branch}|XBQ1)", f"V({branch}|XBQ1)"))
for jj in ("BJS", "BJ1", "BJ2"):
    EXPECTED_PROBES.extend((f"P({jj}|XBQ1)", f"V({jj}|XBQ1)", f"I({jj}|XBQ1)"))
for stage in range(1, 7):
    header = f"XJTL1_{stage}"
    EXPECTED_PROBES.extend(
        (f"P(B01|{header})", f"V(B01|{header})", f"I(B01|{header})", f"P(B02|{header})", f"V(B02|{header})", f"I(B02|{header})", f"V(JTL{stage}_OUT)")
    )
EXPECTED_PROBES.append("I(R_TERM)")


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


def case_path(case_id: str) -> Path:
    if case_id in REUSED:
        return EXP / "references" / "reused" / case_id / "raw.csv"
    return EXP / "runs" / case_id / "raw.csv"


def deck_path(case_id: str) -> Path:
    if case_id in REUSED:
        return EXP / "references" / "reused" / case_id / "deck.cir"
    return EXP / "runs" / case_id / "deck.cir"


def trapezoid(time_s: tuple[float, ...], values: tuple[float, ...]) -> float:
    return sum((values[i] + values[i + 1]) * 0.5 * (time_s[i + 1] - time_s[i]) for i in range(len(values) - 1))


def waveform_stats(trace: Any, label: str) -> dict[str, Any]:
    values = tuple(float(value) for value in trace.column(label))
    time = trace.time
    rms = math.sqrt(sum(value * value for value in values) / len(values))
    max_index = max(range(len(values)), key=values.__getitem__)
    min_index = min(range(len(values)), key=values.__getitem__)
    return {
        "label": label,
        "first": values[0],
        "last": values[-1],
        "endpoint_delta": values[-1] - values[0],
        "min": min(values),
        "max": max(values),
        "max_abs": max(abs(value) for value in values),
        "p2p": max(values) - min(values),
        "rms": rms,
        "signed_area_actual_grid": trapezoid(time, values),
        "time_of_max_s": time[max_index],
        "time_of_min_s": time[min_index],
    }


def phase_descriptive(trace: Any, label: str) -> dict[str, Any]:
    values = continuous_unwrap(tuple(trace.column(label)))
    indices = window_indices(trace.time, 110e-12, 121e-12)
    if len(indices) < 2:
        return {"label": label, "status": "UNKNOWN", "reason": "fewer than two stored samples in FULL_READ"}
    reference = values[indices[0]]
    relative = [(values[index] - reference) / (2.0 * math.pi) for index in indices]
    peak_index = max(range(len(relative)), key=relative.__getitem__)
    return {
        "label": label,
        "status": "DERIVED",
        "raw_unit": "rad",
        "display_unit": "turns",
        "conversion": "continuous_unwrap(raw_rad)/(2*pi)",
        "reference_time_ps": trace.time[indices[0]] * 1e12,
        "relative_min_turns": min(relative),
        "relative_max_turns": max(relative),
        "relative_final_turns": relative[-1],
        "time_of_relative_max_ps": trace.time[indices[peak_index]] * 1e12,
        "not_an_event_count": True,
    }


def l1_bracket(trace: Any) -> dict[str, Any]:
    values = tuple(float(value) for value in trace.column("I(L1|XBQ1)"))
    negative = [index for index, value in enumerate(values) if value < 0.0]
    nonnegative = [index for index, value in enumerate(values) if value >= 0.0]
    if not negative or not nonnegative:
        return {"status": "UNKNOWN", "reason": "no negative/nonnegative stored samples"}
    last_negative = negative[-1]
    first_nonnegative = next((index for index in nonnegative if index > last_negative), None)
    if first_nonnegative is None:
        return {"status": "UNKNOWN", "reason": "no ordered negative-to-nonnegative bracket"}
    return {
        "status": "DERIVED",
        "rule": "stored-sample negative to nonnegative bracket; no interpolation",
        "last_negative_time_ps": trace.time[last_negative] * 1e12,
        "last_negative_current_uA": values[last_negative] * 1e6,
        "first_nonnegative_time_ps": trace.time[first_nonnegative] * 1e12,
        "first_nonnegative_current_uA": values[first_nonnegative] * 1e6,
    }


def mechanical_case(case_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    path = case_path(case_id)
    trace = read_csv(path)
    qa = trace.qa()
    missing = sorted(set(EXPECTED_PROBES) - set(trace.headers))
    grid_hash = hashlib.sha256("\n".join(f"{value:.17g}" for value in trace.time).encode()).hexdigest()
    record = {
        "case_id": case_id,
        "path": str(path),
        "sha256": sha256(path),
        "bytes": path.stat().st_size,
        "sample_count": trace.sample_count,
        "header_count": len(trace.headers),
        "time_start_ps": trace.time[0] * 1e12,
        "time_end_ps": trace.time[-1] * 1e12,
        "strictly_increasing_time": qa["strictly_increasing_time"],
        "finite_values": qa["nan_inf_status"] == "PASS",
        "duplicate_columns": trace.duplicate_columns,
        "stored_time_grid_sha256": grid_hash,
        "required_probe_presence": {"status": "PASS" if not missing else "UNKNOWN", "missing": missing},
        "raw_immutable": True,
    }
    if record["time_start_ps"] != 0.0 or record["time_end_ps"] != 199.9:
        record["time_range_status"] = "UNKNOWN"
    else:
        record["time_range_status"] = "PASS"
    arithmetic: dict[str, Any] = {
        "case_id": case_id,
        "scientific_interpretation_performed": False,
        "waveforms": {},
        "phase_descriptive": {},
        "l1_stored_sample_bracket": None,
        "kcl_residual": None,
        "qbin_port_work": {},
    }
    labels = [
        "I(L_SL|XBVM1)", "I(B_JSL1)", "I(B_JSL8)", "V(COMMON_SL)", "V(QBIN)", "V(QBOUT)",
        "I(L1|XBQ1)", "I(L2|XBQ1)", "I(IB|XBQ1)", "P(BJ1|XBQ1)", "V(BJ1|XBQ1)", "I(RJ1|XBQ1)",
        "P(BJ2|XBQ1)", "V(BJ2|XBQ1)", "I(BJ2|XBQ1)", "I(L3|XBQ1)",
    ]
    for label in labels:
        if label in trace.headers:
            arithmetic["waveforms"][label] = waveform_stats(trace, label)
    for label in ("P(BJ1|XBQ1)", "P(BJ2|XBQ1)"):
        if label in trace.headers:
            arithmetic["phase_descriptive"][label] = phase_descriptive(trace, label)
    if "I(L1|XBQ1)" in trace.headers:
        arithmetic["l1_stored_sample_bracket"] = l1_bracket(trace)
    if all(label in trace.headers for label in ("I(L2|XBQ1)", "I(IB|XBQ1)", "I(L1|XBQ1)")):
        l2 = trace.column("I(L2|XBQ1)")
        ib = trace.column("I(IB|XBQ1)")
        l1 = trace.column("I(L1|XBQ1)")
        residual = [l2[i] - ib[i] - l1[i] for i in range(len(l2))]
        arithmetic["kcl_residual"] = {
            "formula": "I(L2)-I(IB)-I(L1)",
            "max_abs_A": max(abs(value) for value in residual),
            "rms_A": math.sqrt(sum(value * value for value in residual) / len(residual)),
            "label": "DERIVED arithmetic diagnostic; no causal interpretation",
        }
    if all(label in trace.headers for label in ("V(QBIN)", "I(LIN|XBQ1)")):
        v = trace.column("V(QBIN|XBQ1)") if "V(QBIN|XBQ1)" in trace.headers else trace.column("V(QBIN)")
        i = trace.column("I(LIN|XBQ1)")
        for name, start, end in (("EARLY_TRIGGER", 110e-12, 116e-12), ("FULL_READ", 110e-12, 121e-12)):
            indices = window_indices(trace.time, start, end)
            arithmetic["qbin_port_work"][name] = {
                "formula": "integral(V(QBIN)*I(LIN)*dt)",
                "value": trapezoid(tuple(trace.time[index] for index in indices), tuple(v[index] * i[index] for index in indices)) if len(indices) >= 2 else None,
                "label": "DERIVED port-work diagnostic; no trigger threshold",
            }
    return record, arithmetic


def deck_diff() -> dict[str, Any]:
    nominal = (EXP / "inputs" / "nominal_deck_template.cir").read_text(encoding="utf-8").splitlines()
    nominal_params = {line.split("=", 1)[0]: line for line in nominal if line.startswith(".param ")}
    families: dict[str, Any] = {}
    failures: list[str] = []
    for run_id, family, rj1, l1, ibias in NEW_RUNS:
        lines = (EXP / "runs" / run_id / "deck.cir").read_text(encoding="utf-8").splitlines()
        params = {line.split("=", 1)[0]: line for line in lines if line.startswith(".param ")}
        changed = [key for key in sorted(set(nominal_params) | set(params)) if nominal_params.get(key) != params.get(key)]
        expected_key = {"L1": ".param L1_VALUE", "IBias": ".param IB_VALUE", "RJ1": ".param RJ1_VALUE"}[family]
        expected = [expected_key]
        pass_case = changed == expected and all(
            nominal[index] == lines[index]
            for index in range(len(nominal))
            if not nominal[index].startswith(".param ")
        )
        if not pass_case:
            failures.append(run_id)
        families[run_id] = {
            "family": family,
            "changed_parameter_lines": changed,
            "expected_changed_parameter_lines": expected,
            "status": "PASS" if pass_case else "FAIL",
        }
    return {
        "schema": "qb-l1-ibias-rj1-deck-diff-qa-v1",
        "status": "PASS" if not failures else "FAIL",
        "baseline": "inputs/nominal_deck_template.cir (same frozen non-parameter text)",
        "family_rule": "one registered parameter line changes; all other deck lines remain identical",
        "runs": families,
        "failures": failures,
    }


def main() -> int:
    current_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()
    preflight = json.loads((EXP / "analysis/preflight.json").read_text(encoding="utf-8"))
    preflight_head = preflight.get("head")
    if current_head != preflight_head:
        changed = set(subprocess.check_output(
            ["git", "diff", "--name-only", f"{preflight_head}..{current_head}"],
            cwd=REPO,
            text=True,
        ).splitlines())
        allowed_seal = {
            str(EXP.relative_to(REPO) / "PREFLIGHT.md"),
            str(EXP.relative_to(REPO) / "analysis/preflight.json"),
        }
        distance = int(subprocess.check_output(
            ["git", "rev-list", "--count", f"{preflight_head}..{current_head}"],
            cwd=REPO,
            text=True,
        ).strip())
        if not preflight.get("head_refresh") or distance != 1 or changed != allowed_seal:
            raise RuntimeError(f"HEAD changed after preflight outside seal: {current_head} != {preflight_head}")
    execution = json.loads((EXP / "qa/execution_summary.json").read_text(encoding="utf-8"))
    if execution.get("status") != "RUN_PASS" or execution.get("new_physical_solve_count") != 12:
        raise RuntimeError("execution summary is not an exact successful 12-run matrix")
    cases: dict[str, Any] = {}
    arithmetic: dict[str, Any] = {"schema": "qb-l1-ibias-rj1-registered-arithmetic-v1", "scientific_analysis_performed": False, "new": {}, "reused": {}}
    raw_failures: list[str] = []
    pre_hashes: dict[str, str] = {}
    for case_id, *_ in NEW_RUNS:
        record, derived = mechanical_case(case_id)
        cases[case_id] = record
        arithmetic["new"][case_id] = derived
        pre_hashes[case_id] = record["sha256"]
        if not record["strictly_increasing_time"] or not record["finite_values"] or record["duplicate_columns"] or record["time_range_status"] != "PASS":
            raw_failures.append(case_id)
    for case_id in REUSED:
        record, derived = mechanical_case(case_id)
        arithmetic["reused"][case_id] = derived
        pre_hashes[case_id] = record["sha256"]
        if not record["strictly_increasing_time"] or not record["finite_values"] or record["duplicate_columns"] or record["time_range_status"] != "PASS":
            raw_failures.append(case_id)
    post_hashes = {case_id: sha256(case_path(case_id)) for case_id in pre_hashes}
    raw_qa = {
        "schema": "qb-l1-ibias-rj1-raw-qa-v1",
        "status": "PASS" if not raw_failures and pre_hashes == post_hashes else "FAIL",
        "experiment_id": EXP.name,
        "created_at_local": now(),
        "head": current_head,
        "new_physical_solve_count": 12,
        "reused_physical_solve_count": 0,
        "cases": cases,
        "pre_analysis_sha256": pre_hashes,
        "post_analysis_sha256": post_hashes,
        "raw_unchanged_pre_to_post": pre_hashes == post_hashes,
        "artifact_validity": "VALID" if not raw_failures and pre_hashes == post_hashes else "INVALID",
        "overall_required_probe_status": "UNKNOWN" if any(case["required_probe_presence"]["status"] == "UNKNOWN" for case in cases.values()) else "PASS",
        "missing_probe_is_not_fabricated": True,
        "no_solver_invoked_by_qa": True,
        "scientific_analysis_performed": False,
        "failures": raw_failures,
    }
    deck_qa = deck_diff()
    source = json.loads((EXP / "SOURCE_MANIFEST.json").read_text(encoding="utf-8"))
    reuse = json.loads((EXP / "REUSED_REFERENCE_MANIFEST.json").read_text(encoding="utf-8"))
    provenance = {
        "schema": "qb-l1-ibias-rj1-provenance-v1",
        "experiment_id": EXP.name,
        "head_at_preflight": preflight.get("head"),
        "head_at_qa": current_head,
        "source_manifest": "SOURCE_MANIFEST.json",
        "reused_reference_manifest": "REUSED_REFERENCE_MANIFEST.json",
        "solver": source["sources"][-1],
        "new_cases": {case_id: {"deck": str(deck_path(case_id)), "raw": str(case_path(case_id)), "raw_sha256": pre_hashes[case_id]} for case_id, *_ in NEW_RUNS},
        "reused_cases": reuse["references"],
        "raw": {"new": {case_id: pre_hashes[case_id] for case_id, *_ in NEW_RUNS}, "reused": {case_id: pre_hashes[case_id] for case_id in REUSED}},
        "scientific_analysis_performed": False,
    }
    transformation = {
        "schema": "qb-l1-ibias-rj1-transformation-registry-v1",
        "raw_immutable": True,
        "transformations": [
            {"name": "exact_visual_window_slice", "operation": "half-open actual stored-row slices", "scope": "visualization only"},
            {"name": "phase_display", "operation": "independent continuous unwrap(raw_rad)/(2*pi)", "scope": "visualization only", "not_event_count": True},
            {"name": "arithmetic_diagnostics", "operation": "actual-grid extrema/area/KCL/port-work", "scope": "registered DERIVED arithmetic only"},
        ],
    }
    write_json(EXP / "qa/raw_qa.json", raw_qa)
    write_json(EXP / "qa/deck_diff_qa.json", deck_qa)
    write_json(EXP / "qa/provenance.json", provenance)
    write_json(EXP / "qa/transformation_registry.json", transformation)
    write_json(EXP / "qa/registered_arithmetic.json", arithmetic)
    print(json.dumps({"status": "PASS" if raw_qa["artifact_validity"] == "VALID" and deck_qa["status"] == "PASS" else "FAIL", "raw_failures": raw_failures, "deck_failures": deck_qa["failures"], "scientific_analysis_performed": False}, ensure_ascii=False, indent=2))
    return 0 if raw_qa["artifact_validity"] == "VALID" and deck_qa["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
