#!/usr/bin/env python3
"""Analyze the 13 ps JSL8 physical closure and its 12x320 reference.

This is an evidence script, not the legacy ``sfq_metrics.py`` Gate.  It keeps
phase activity, same-segment phase/area evidence, source guards, JSL guards,
QB partition, and the final Exploration disposition separate.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[2]
REFERENCE = REPO / "test/exploration/physical-bvm-jsl12-qb-sfq-closure-v1-20260824"
PHI0 = 2.067833848e-15
TWO_PI = 2.0 * math.pi
PRE = (80.0, 94.0)
ACTIVE = (94.0, 130.0)
POST = (140.0, 170.0)
CLEAN_BAND = (0.95, 1.15)
ROLES = ("logical1_read", "logical0_read", "logical1_no_read_control", "logical0_no_read_control")
SOURCE_SIGNALS = ("V(SL1)", "V(N6|XBVM1)", "I(L_SL|XBVM1)", "I(L_PSL|XBVM1)")
QB_PHASES = ("BJs", "BJL1", "BJL2")
QB_BRANCHES = ("V(IN)", "V(OUT)", "I(Lin|XBQ)", "I(L0|XBQ)", "I(L1|XBQ)", "I(L2|XBQ)", "I(RB|XBQ)", "I(RJ1|XBQ)", "I(RJ2|XBQ)", "I(R_LOAD)", "I(I_IBIAS)")


def norm(name: str) -> str:
    return name.strip().strip('"').replace(" ", "").lower()


def load_csv(path: Path) -> dict[str, np.ndarray]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        header = next(reader)
        rows = [row for row in reader if row]
    data: dict[str, np.ndarray] = {}
    for idx, name in enumerate(header):
        key = name.strip().strip('"')
        if key in data:
            suffix = 2
            while f"{key}__dup{suffix}" in data:
                suffix += 1
            key = f"{key}__dup{suffix}"
        data[key] = np.asarray([float(row[idx]) for row in rows], dtype=float)
    if "time" not in data:
        raise ValueError(f"missing time column: {path}")
    time = data["time"] * 1e12
    if time.size < 2 or not np.all(np.diff(time) > 0):
        raise ValueError(f"invalid time axis: {path}")
    if not all(np.all(np.isfinite(values)) for values in data.values()):
        raise ValueError(f"NaN/Inf in {path}")
    data["__time_ps"] = time
    return data


def col(data: dict[str, np.ndarray], wanted: str) -> np.ndarray:
    target = norm(wanted)
    for name, values in data.items():
        if norm(name) == target:
            return values
    raise KeyError(f"missing {wanted!r}; available={list(data)}")


def mask(time: np.ndarray, bounds: tuple[float, float]) -> np.ndarray:
    return (time >= bounds[0]) & (time < bounds[1])


def integrate(time_ps: np.ndarray, voltage: np.ndarray) -> float:
    integral = np.trapezoid(voltage, time_ps * 1e-12) if hasattr(np, "trapezoid") else np.trapz(voltage, time_ps * 1e-12)
    return float(integral / PHI0)


def monotonic_segments(time: np.ndarray, phase: np.ndarray, voltage: np.ndarray, bounds: tuple[float, float]) -> list[dict[str, Any]]:
    indices = np.flatnonzero(mask(time, bounds))
    if indices.size < 2:
        return []
    local = phase[indices]
    signs = np.sign(np.diff(local))
    nonzero = np.flatnonzero(signs != 0)
    if nonzero.size == 0:
        return []
    starts = [0]
    previous = signs[nonzero[0]]
    for position in nonzero[1:]:
        current = signs[position]
        if current != previous:
            starts.append(int(position))
            previous = current
    starts.append(len(indices) - 1)
    segments: list[dict[str, Any]] = []
    for left, right in zip(starts[:-1], starts[1:]):
        selected = indices[left:right + 1]
        if selected.size < 2:
            continue
        delta = float((phase[selected[-1]] - phase[selected[0]]) / TWO_PI)
        area_phi0 = integrate(time[selected], voltage[selected])
        residual = float(area_phi0 - delta)
        complete = abs(delta) >= 1.0
        area_consistent = bool(
            complete
            and delta * area_phi0 > 0
            and abs(residual) <= max(0.05, 0.10 * abs(delta))
        )
        segments.append({
            "start_ps": float(time[selected[0]]),
            "end_ps": float(time[selected[-1]]),
            "delta_turns": delta,
            "area_phi0": area_phi0,
            "residual_turns": residual,
            "complete_phase_candidate": complete,
            "area_consistent": area_consistent,
            "qualifying_event": area_consistent,
        })
    return segments


def p2p(values: np.ndarray) -> float:
    return float(np.ptp(values))


def stats(data: dict[str, np.ndarray], name: str) -> dict[str, float]:
    time = data["__time_ps"]
    values = col(data, name)
    active = values[mask(time, ACTIVE)]
    post = values[mask(time, POST)]
    return {
        "active_min": float(np.min(active)),
        "active_max": float(np.max(active)),
        "active_p2p": p2p(active),
        "post_min": float(np.min(post)),
        "post_max": float(np.max(post)),
        "post_p2p": p2p(post),
        "post_mean": float(np.mean(post)),
    }


def phase_record(data: dict[str, np.ndarray], prefix: str, role: str, *, qb: bool) -> dict[str, Any]:
    time = data["__time_ps"]
    scope = "|XBQ" if qb else ""
    phase = np.unwrap(col(data, f"P({prefix}{scope})"))
    voltage = col(data, f"V({prefix}{scope})")
    current = col(data, f"I({prefix}{scope})")
    active_segments = monotonic_segments(time, phase, voltage, ACTIVE)
    post_segments = monotonic_segments(time, phase, voltage, POST)
    qualifying = [segment for segment in active_segments if segment["qualifying_event"]]
    largest = max(active_segments, key=lambda item: abs(item["delta_turns"])) if active_segments else None
    pre_values = phase[mask(time, PRE)]
    post_values = phase[mask(time, POST)]
    active_values = phase[mask(time, ACTIVE)]
    return {
        "role": role,
        "phase_activity_p2p_turns": p2p(active_values) / TWO_PI,
        "phase_pre_mean_turns": float(np.mean(pre_values) / TWO_PI) if pre_values.size else None,
        "phase_post_mean_turns": float(np.mean(post_values) / TWO_PI) if post_values.size else None,
        "phase_post_p2p_turns": p2p(post_values) / TWO_PI if post_values.size else None,
        "segments": active_segments,
        "post_segments": post_segments,
        "largest_segment": largest,
        "qualifying_event_count": len(qualifying),
        "post_qualifying_event_count": sum(1 for segment in post_segments if segment["qualifying_event"]),
        "current_activity_uA": {
            "min": float(np.min(current[mask(time, ACTIVE)]) * 1e6),
            "max": float(np.max(current[mask(time, ACTIVE)]) * 1e6),
        },
    }


def classify_bjl2(record: dict[str, Any]) -> str:
    if record["post_qualifying_event_count"] > 0:
        return "FREE_RUNNING_OR_POST_EVENT"
    if record["qualifying_event_count"] > 1:
        return "MULTI_EVENT"
    if record["qualifying_event_count"] == 1:
        delta = abs(record["largest_segment"]["delta_turns"])
        return "CLEAN_ONE_SFQ_CANDIDATE" if CLEAN_BAND[0] <= delta <= CLEAN_BAND[1] else "OVERDRIVEN_ONE_PLUS_RESIDUAL"
    return "SUBTHRESHOLD"


def source_record(data: dict[str, np.ndarray]) -> dict[str, Any]:
    record = {name: stats(data, name) for name in SOURCE_SIGNALS}
    time = data["__time_ps"]
    for name in ("P(B_JM1|XBVM1)", "P(B_JM2|XBVM1)", "P(B_JS1|XBVM1)", "P(B_JS2|XBVM1)"):
        phase = np.unwrap(col(data, name))
        record[name] = {
            "active_p2p_turns": p2p(phase[mask(time, ACTIVE)]) / TWO_PI,
            "post_p2p_turns": p2p(phase[mask(time, POST)]) / TWO_PI,
            "post_mean_turns": float(np.mean(phase[mask(time, POST)]) / TWO_PI),
        }
    return record


def jsl_record(data: dict[str, np.ndarray], count: int) -> dict[str, Any]:
    time = data["__time_ps"]
    currents = [col(data, f"I(B_LD{idx})") for idx in range(1, count + 1)]
    reference = currents[0]
    deviations = np.vstack([current - reference for current in currents[1:]])
    junctions: dict[str, Any] = {}
    complete_junctions: list[str] = []
    for idx, current in enumerate(currents, 1):
        name = f"B_LD{idx}"
        phase = np.unwrap(col(data, f"P({name})"))
        voltage = col(data, f"V({name})")
        active_segments = monotonic_segments(time, phase, voltage, ACTIVE)
        post_segments = monotonic_segments(time, phase, voltage, POST)
        qualifying = [segment for segment in active_segments + post_segments if segment["qualifying_event"]]
        if qualifying:
            complete_junctions.append(name)
        junctions[name] = {
            "activity_p2p_turns": p2p(phase[mask(time, ACTIVE)]) / TWO_PI,
            "post_p2p_turns": p2p(phase[mask(time, POST)]) / TWO_PI,
            "largest_segment": max(active_segments, key=lambda item: abs(item["delta_turns"])) if active_segments else None,
            "qualifying_event_count": len(qualifying),
            "current_active_uA": {"min": float(np.min(current[mask(time, ACTIVE)]) * 1e6), "max": float(np.max(current[mask(time, ACTIVE)]) * 1e6)},
        }
    return {
        "count": count,
        "series_current_max_deviation_uA": float(np.max(np.abs(deviations)) * 1e6),
        "first_current_active_uA": {"min": float(np.min(reference[mask(time, ACTIVE)]) * 1e6), "max": float(np.max(reference[mask(time, ACTIVE)]) * 1e6)},
        "last_current_active_uA": {"min": float(np.min(currents[-1][mask(time, ACTIVE)]) * 1e6), "max": float(np.max(currents[-1][mask(time, ACTIVE)]) * 1e6)},
        "junctions": junctions,
        "complete_event_junctions": complete_junctions,
        "non_switching_guard": "PASS" if not complete_junctions else "PAPER_JSL_NONSWITCHING_ASSUMPTION_VIOLATED",
    }


def kcl_residuals(data: dict[str, np.ndarray]) -> dict[str, float]:
    bjs = col(data, "I(BJs|XBQ)")
    bjl1 = col(data, "I(BJL1|XBQ)")
    rj1 = col(data, "I(RJ1|XBQ)")
    l1 = col(data, "I(L1|XBQ)")
    rb = col(data, "I(RB|XBQ)")
    l2 = col(data, "I(L2|XBQ)")
    bjl2 = col(data, "I(BJL2|XBQ)")
    rj2 = col(data, "I(RJ2|XBQ)")
    l0 = col(data, "I(L0|XBQ)")
    equations = {
        "node2": bjs - l1 - bjl1 - rj1,
        "node3": l1 + rb - l2,
        "node4": l2 - l0 - bjl2 - rj2,
    }
    return {name: float(np.max(np.abs(value)) * 1e6) for name, value in equations.items()}


def analyze_case(path: Path, role: str, jsl_count: int) -> dict[str, Any]:
    data = load_csv(path)
    result: dict[str, Any] = {
        "path": str(path.relative_to(REPO)),
        "role": role,
        "time_end_ps": float(data["__time_ps"][-1]),
        "source": source_record(data),
        "jsl": jsl_record(data, jsl_count),
        "qb": {},
        "qb_branch": {name: stats(data, name) for name in QB_BRANCHES},
        "qb_kcl_residual_uA": kcl_residuals(data),
    }
    for name in QB_PHASES:
        result["qb"][name] = phase_record(data, name, role, qb=True)
    result["bjl2_classification"] = classify_bjl2(result["qb"]["BJL2"])
    result["port_trajectory"] = {
        "time_window_ps": [float(data["__time_ps"][0]), float(data["__time_ps"][-1])],
        "V(IN)": stats(data, "V(IN)"),
        "I(Lin|XBQ)": stats(data, "I(Lin|XBQ)"),
        "interpretation": "time-parametrized V(IN)-I(Lin) trajectory; not a static impedance fit",
    }
    return result


def raw_path(root: Path, role: str) -> Path:
    return root / "raw/13" / role / "run-01.csv"


def largest_abs(record: dict[str, Any]) -> float:
    segment = record.get("largest_segment") or {}
    return abs(float(segment.get("delta_turns", 0.0)))


def phase_summary(record: dict[str, Any]) -> dict[str, Any]:
    segment = record.get("largest_segment") or {}
    return {
        "phase_activity_p2p_turns": record.get("phase_activity_p2p_turns"),
        "largest_delta_turns": segment.get("delta_turns"),
        "largest_area_phi0": segment.get("area_phi0"),
        "largest_residual_turns": segment.get("residual_turns"),
        "qualifying_event_count": record.get("qualifying_event_count"),
        "post_qualifying_event_count": record.get("post_qualifying_event_count"),
    }


def compare_case(reference: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    source: dict[str, Any] = {}
    for name in SOURCE_SIGNALS:
        old = reference["source"][name]
        new = current["source"][name]
        source[name] = {
            "12x320": old,
            "8x500": new,
            "active_p2p_delta": new["active_p2p"] - old["active_p2p"],
            "active_p2p_ratio_abs": new["active_p2p"] / max(abs(old["active_p2p"]), 1e-30),
            "post_p2p_delta": new["post_p2p"] - old["post_p2p"],
        }
    qb = {
        name: {
            "12x320": phase_summary(reference["qb"][name]),
            "8x500": phase_summary(current["qb"][name]),
            "largest_abs_delta_turns": largest_abs(current["qb"][name]) - largest_abs(reference["qb"][name]),
        }
        for name in QB_PHASES
    }
    branches = {
        name: {
            "12x320": reference["qb_branch"][name],
            "8x500": current["qb_branch"][name],
            "active_p2p_delta": current["qb_branch"][name]["active_p2p"] - reference["qb_branch"][name]["active_p2p"],
        }
        for name in ("V(IN)", "I(Lin|XBQ)", "I(L1|XBQ)", "I(L2|XBQ)", "I(L0|XBQ)", "I(RB|XBQ)", "I(RJ1|XBQ)", "I(RJ2|XBQ)")
    }
    jsl = {
        "12x320_count": reference["jsl"]["count"],
        "8x500_count": current["jsl"]["count"],
        "12x320_series_current_max_deviation_uA": reference["jsl"]["series_current_max_deviation_uA"],
        "8x500_series_current_max_deviation_uA": current["jsl"]["series_current_max_deviation_uA"],
        "12x320_complete_event_junctions": reference["jsl"]["complete_event_junctions"],
        "8x500_complete_event_junctions": current["jsl"]["complete_event_junctions"],
        "junctions": {},
    }
    for idx in range(1, 9):
        name = f"B_LD{idx}"
        jsl["junctions"][name] = {
            "12x320": reference["jsl"]["junctions"].get(name),
            "8x500": current["jsl"]["junctions"][name],
        }
    return {
        "reference_case": reference["path"],
        "current_case": current["path"],
        "source_loadline": source,
        "qb_transfer": qb,
        "qb_branch_partition": branches,
        "jsl_current_phase": jsl,
        "kcl": {"12x320": reference["qb_kcl_residual_uA"], "8x500": current["qb_kcl_residual_uA"]},
    }


def decision(cases: dict[str, dict[str, Any]], references: dict[str, dict[str, Any]]) -> dict[str, Any]:
    primary = cases["logical1_read"]
    controls = [cases[role] for role in ("logical0_read", "logical1_no_read_control", "logical0_no_read_control")]
    jsl_ok = all(case["jsl"]["non_switching_guard"] == "PASS" for case in cases.values())
    control_ok = all(case["bjl2_classification"] not in {"CLEAN_ONE_SFQ_CANDIDATE", "OVERDRIVEN_ONE_PLUS_RESIDUAL", "MULTI_EVENT", "FREE_RUNNING_OR_POST_EVENT"} for case in controls)
    candidate = primary["bjl2_classification"] == "CLEAN_ONE_SFQ_CANDIDATE" and control_ok and jsl_ok
    reference_primary = references["logical1_read"]
    margin = {
        name: {
            "12x320_abs_largest_turns": largest_abs(reference_primary["qb"][name]),
            "8x500_abs_largest_turns": largest_abs(primary["qb"][name]),
            "delta_abs_turns": largest_abs(primary["qb"][name]) - largest_abs(reference_primary["qb"][name]),
        }
        for name in ("BJs", "BJL1", "BJL2")
    }
    # The registered ``margin`` branch is about downstream QB transfer.  A
    # larger BJs excursion alone is explicitly not enough to call JSL8 an
    # improvement, because local upstream activity is not downstream delivery.
    visible_margin_improvement = any(margin[name]["delta_abs_turns"] > 0.0 for name in ("BJL1", "BJL2"))
    if not jsl_ok:
        verdict = "PAPER_JSL_NONSWITCHING_ASSUMPTION_VIOLATED"
    elif candidate:
        verdict = "PAPER_JSL8_500_PHYSICAL_ONE_SFQ_CANDIDATE"
    elif visible_margin_improvement:
        verdict = "PAPER_JSL8_IMPROVES_PHYSICAL_MARGIN"
    else:
        verdict = "JSL_SIZING_NOT_SUFFICIENT"
    bjs_multi = largest_abs(primary["qb"]["BJs"]) >= 1.0
    downstream_subthreshold = primary["qb"]["BJL1"]["qualifying_event_count"] == 0 and primary["qb"]["BJL2"]["qualifying_event_count"] == 0
    mechanism = "QB internal load-line mismatch" if bjs_multi and downstream_subthreshold else "bounded physical interface result; mechanism not isolated"
    return {
        "verdict": verdict,
        "candidate_conditions": {"logical1_clean_one_sfq": primary["bjl2_classification"], "controls_bounded": control_ok, "all_8_jsl_non_switching": jsl_ok},
        "margin": margin,
        "visible_margin_improvement_by_registered_comparison": visible_margin_improvement,
        "mechanism_boundary": mechanism,
        "bvm_storage_guard": "BOUNDED_OBSERVED_ONLY",
        "next_action": "NONE_THIS_TURN",
        "authorized_if_candidate": "dt=0.00625 ps then rewrite/read review; not run automatically",
        "authorized_if_margin_only": "14 ps backup may be proposed; not run automatically",
    }


def write_summary(cases: dict[str, dict[str, Any]]) -> None:
    fields = ["role", "bjl2_classification", "bjs_activity_p2p_turns", "bjs_largest_turns", "bjl1_activity_p2p_turns", "bjl1_largest_turns", "bjl2_activity_p2p_turns", "bjl2_largest_turns", "bjl2_area_phi0", "jsl_guard", "jsl_current_max_deviation_uA"]
    with (ROOT / "analysis/13ps-summary.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for role, item in cases.items():
            row: dict[str, Any] = {"role": role, "bjl2_classification": item["bjl2_classification"], "jsl_guard": item["jsl"]["non_switching_guard"], "jsl_current_max_deviation_uA": item["jsl"]["series_current_max_deviation_uA"]}
            for name, prefix in (("BJs", "bjs"), ("BJL1", "bjl1"), ("BJL2", "bjl2")):
                record = item["qb"][name]
                row[f"{prefix}_activity_p2p_turns"] = record["phase_activity_p2p_turns"]
                row[f"{prefix}_largest_turns"] = (record["largest_segment"] or {}).get("delta_turns", 0.0)
            row["bjl2_area_phi0"] = (item["qb"]["BJL2"]["largest_segment"] or {}).get("area_phi0", 0.0)
            writer.writerow(row)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def finalize_manifest(cases: dict[str, dict[str, Any]], comparisons: dict[str, Any], disposition: dict[str, Any]) -> None:
    path = ROOT / "manifest.yaml"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != "BVM_JSL8_500_PHYSICAL_QB_RECHECK_V1":
        raise SystemExit("unexpected experiment manifest schema")
    raw_hashes: dict[str, str] = {}
    for role in ROLES:
        raw = raw_path(ROOT, role)
        raw_hashes[f"13/{role}/run-01.csv"] = sha256(raw)
    manifest["execution"] = {
        "status": "COMPLETE",
        "recorded_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "case_count": 4,
        "roles": list(ROLES),
        "command": "build/josim-cli -a 1 -o raw/13/<role>/run-01.csv inputs/13/<role>.cir",
        "raw_sha256": raw_hashes,
        "no_14ps_run": True,
    }
    manifest["analysis"] = {
        "status": "COMPLETE",
        "script": "analysis/analyze_physical.py",
        "metrics": ["continuous_unwrapped_phase", "same_jj_same_segment_voltage_area", "post_retrap", "source_guard", "jsl8_non_switching_guard", "qb_node2_node3_node4_kcl", "12x320_vs_8x500_loadline"],
        "phase_semantics": "continuous_absolute",
        "verdict": disposition["verdict"],
        "comparison": "analysis/comparison-12x320-vs-8x500.json",
    }
    manifest["reference_raw_sha256"] = {f"13/{role}/run-01.csv": sha256(raw_path(REFERENCE, role)) for role in ROLES}
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_hashes() -> None:
    paths = [ROOT / "manifest.yaml", ROOT / "PREREGISTRATION.md", ROOT / "REPORT.md", ROOT / "SUMMARY.md"]
    paths += [ROOT / "analysis" / name for name in ("build_fixture.py", "analyze_physical.py", "physical-13ps-metrics.json", "comparison-12x320-vs-8x500.json", "13ps-summary.csv")]
    paths += sorted((ROOT / "plots").glob("*.metadata.json"))
    paths += [ROOT / "topology/publication/BVM_JSL8_SCALED_QB_PHYSICAL/schematic.svg", ROOT / "topology/publication/BVM_JSL8_SCALED_QB_PHYSICAL/schematic-annotated.svg"]
    paths += [ROOT / "inputs" / name for name in ("jjmit.cir", "bvm_cell.cir", "bq_cell.cir")]
    paths += sorted((ROOT / "inputs/13").glob("*.cir"))
    paths += sorted((ROOT / "raw/13").glob("*/*.csv"))
    with (ROOT / "analysis/sha256sums.txt").open("w", encoding="utf-8") as handle:
        for path in paths:
            if path.exists():
                handle.write(f"{sha256(path)}  {path.relative_to(ROOT).as_posix()}\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-finalize", action="store_true", help="only calculate metrics; do not update manifest")
    args = parser.parse_args()
    current: dict[str, dict[str, Any]] = {}
    reference: dict[str, dict[str, Any]] = {}
    for role in ROLES:
        current_path = raw_path(ROOT, role)
        reference_path = raw_path(REFERENCE, role)
        if not current_path.exists() or not reference_path.exists():
            raise SystemExit(f"missing current/reference raw for {role}")
        current[role] = analyze_case(current_path, role, 8)
        reference[role] = analyze_case(reference_path, role, 12)
    comparisons = {role: compare_case(reference[role], current[role]) for role in ROLES}
    disposition = decision(current, reference)
    result = {
        "experiment": "BVM_JSL8_500_PHYSICAL_QB_RECHECK_V1",
        "reference_experiment": REFERENCE.relative_to(REPO).as_posix(),
        "windows_ps": {"pre": PRE, "active": ACTIVE, "post": POST},
        "clean_band_turns": CLEAN_BAND,
        "cases": current,
        "decision": disposition,
    }
    (ROOT / "analysis/physical-13ps-metrics.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (ROOT / "analysis/comparison-12x320-vs-8x500.json").write_text(json.dumps({"cases": comparisons, "decision": disposition}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_summary(current)
    if not args.no_finalize:
        finalize_manifest(current, comparisons, disposition)
        write_hashes()
    print(json.dumps({"verdict": disposition["verdict"], "classifications": {role: item["bjl2_classification"] for role, item in current.items()}, "jsl_guards": {role: item["jsl"]["non_switching_guard"] for role, item in current.items()}}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
