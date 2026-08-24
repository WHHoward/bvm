#!/usr/bin/env python3
"""Evidence-first analysis for the physical BVM -> JSL12 -> frozen QB run."""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[2]
PHI0 = 2.067833848e-15
TWO_PI = 2.0 * math.pi
ACTIVE = (94.0, 130.0)
POST = (140.0, 170.0)
PRE = (80.0, 94.0)
CLEAN_BAND = (0.95, 1.15)


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
            duplicate = 2
            while f"{key}__dup{duplicate}" in data:
                duplicate += 1
            key = f"{key}__dup{duplicate}"
        data[key] = np.asarray([float(row[idx]) for row in rows], dtype=float)
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
        area_consistent = bool(
            abs(delta) >= 1.0
            and delta * area_phi0 > 0
            and abs(residual) <= max(0.05, 0.10 * abs(delta))
        )
        segments.append({
            "start_ps": float(time[selected[0]]),
            "end_ps": float(time[selected[-1]]),
            "delta_turns": delta,
            "area_phi0": area_phi0,
            "residual_turns": residual,
            "complete_candidate": bool(abs(delta) >= 1.0),
            "area_consistent": area_consistent,
            "qualifying_event": area_consistent,
            "complete_event_units": int(math.floor(abs(delta))) if area_consistent else 0,
        })
    return segments


def phase_record(data: dict[str, np.ndarray], prefix: str, role: str) -> dict[str, Any]:
    time = data["__time_ps"]
    phase = np.unwrap(col(data, f"P({prefix}|XBQ)" if prefix in {"BJs", "BJL1", "BJL2"} else f"P({prefix})"))
    voltage = col(data, f"V({prefix}|XBQ)" if prefix in {"BJs", "BJL1", "BJL2"} else f"V({prefix})")
    current = col(data, f"I({prefix}|XBQ)" if prefix in {"BJs", "BJL1", "BJL2"} else f"I({prefix})")
    active = monotonic_segments(time, phase, voltage, ACTIVE)
    post = monotonic_segments(time, phase, voltage, POST)
    qualifying = [segment for segment in active if segment["qualifying_event"]]
    largest = max(active, key=lambda item: abs(item["delta_turns"])) if active else None
    forward = max((item for item in active if item["delta_turns"] > 0), key=lambda item: item["delta_turns"], default=None)
    backward = min((item for item in active if item["delta_turns"] < 0), key=lambda item: item["delta_turns"], default=None)
    pre_values = phase[mask(time, PRE)]
    post_values = phase[mask(time, POST)]
    return {
        "role": role,
        "phase_activity_p2p_turns": float(np.ptp(phase[mask(time, ACTIVE)]) / TWO_PI),
        "phase_pre_mean_turns": float(np.mean(pre_values) / TWO_PI) if pre_values.size else None,
        "phase_post_mean_turns": float(np.mean(post_values) / TWO_PI) if post_values.size else None,
        "phase_post_p2p_turns": float(np.ptp(post_values) / TWO_PI) if post_values.size else None,
        "segments": active,
        "post_segments": post,
        "largest_segment": largest,
        "largest_forward_segment": forward,
        "largest_backward_segment": backward,
        "qualifying_event_count": len(qualifying),
        "activity_complete_event_units": sum(item["complete_event_units"] for item in active),
        "post_complete_event_units": sum(item["complete_event_units"] for item in post),
        "current_activity_uA": {
            "min": float(np.min(current[mask(time, ACTIVE)]) * 1e6),
            "max": float(np.max(current[mask(time, ACTIVE)]) * 1e6),
        },
    }


def classify_bjl2(record: dict[str, Any]) -> str:
    if record["post_complete_event_units"] > 0:
        return "FREE_RUNNING_OR_POST_EVENT"
    if record["qualifying_event_count"] > 1:
        return "MULTI_EVENT"
    if record["qualifying_event_count"] == 1:
        delta = abs(record["largest_segment"]["delta_turns"])
        return "CLEAN_ONE_SFQ_CANDIDATE" if CLEAN_BAND[0] <= delta <= CLEAN_BAND[1] else "OVERDRIVEN_ONE_PLUS_RESIDUAL"
    return "SUBTHRESHOLD"


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


def jsl_record(data: dict[str, np.ndarray]) -> dict[str, Any]:
    time = data["__time_ps"]
    currents = [col(data, f"I(B_LD{idx})") for idx in range(1, 13)]
    reference = currents[0]
    diffs = np.vstack([current - reference for current in currents[1:]])
    record: dict[str, Any] = {
        "series_current_max_deviation_uA": float(np.max(np.abs(diffs)) * 1e6),
        "first_current_uA": {"min": float(np.min(reference) * 1e6), "max": float(np.max(reference) * 1e6)},
        "last_current_uA": {"min": float(np.min(currents[-1]) * 1e6), "max": float(np.max(currents[-1]) * 1e6)},
        "junctions": {},
    }
    for idx, current in enumerate(currents, 1):
        phase = np.unwrap(col(data, f"P(B_LD{idx})"))
        voltage = col(data, f"V(B_LD{idx})")
        segments = monotonic_segments(time, phase, voltage, ACTIVE)
        record["junctions"][f"B_LD{idx}"] = {
            "activity_p2p_turns": float(np.ptp(phase[mask(time, ACTIVE)]) / TWO_PI),
            "largest_segment": max(segments, key=lambda item: abs(item["delta_turns"])) if segments else None,
            "complete_event_units": sum(item["complete_event_units"] for item in segments),
        }
    return record


def source_record(data: dict[str, np.ndarray]) -> dict[str, Any]:
    time = data["__time_ps"]
    record: dict[str, Any] = {}
    for name in ("V(SL1)", "V(N6|XBVM1)", "I(L_SL|XBVM1)", "I(L_PSL|XBVM1)"):
        values = col(data, name)
        active = values[mask(time, ACTIVE)]
        post = values[mask(time, POST)]
        record[name] = {
            "activity_min": float(np.min(active)),
            "activity_max": float(np.max(active)),
            "activity_p2p": float(np.ptp(active)),
            "post_p2p": float(np.ptp(post)),
            "post_mean": float(np.mean(post)),
        }
    for name in ("P(B_JM1|XBVM1)", "P(B_JM2|XBVM1)", "P(B_JS1|XBVM1)", "P(B_JS2|XBVM1)"):
        phase = np.unwrap(col(data, name))
        active = phase[mask(time, ACTIVE)]
        post = phase[mask(time, POST)]
        record[name] = {
            "activity_p2p_turns": float(np.ptp(active) / TWO_PI),
            "post_p2p_turns": float(np.ptp(post) / TWO_PI),
            "post_mean_turns": float(np.mean(post) / TWO_PI),
        }
    return record


def analyze_case(path: Path, width: int, role: str) -> dict[str, Any]:
    data = load_csv(path)
    result: dict[str, Any] = {
        "path": str(path),
        "width_ps": width,
        "role": role,
        "time_end_ps": float(data["__time_ps"][-1]),
        "source": source_record(data),
        "jsl": jsl_record(data),
        "qb": {},
        "kcl_residual_uA": kcl_residuals(data),
    }
    for name in ("BJs", "BJL1", "BJL2"):
        result["qb"][name] = phase_record(data, name, role)
    result["bjl2_classification"] = classify_bjl2(result["qb"]["BJL2"])
    result["qb_branch"] = {}
    for name in ("V(IN)", "V(OUT)", "I(LIN|XBQ)", "I(L0|XBQ)", "I(L1|XBQ)", "I(L2|XBQ)", "I(RB|XBQ)", "I(RJ1|XBQ)", "I(RJ2|XBQ)", "I(R_LOAD)", "I(I_IBIAS)"):
        values = col(data, name)
        active = values[mask(data["__time_ps"], ACTIVE)]
        result["qb_branch"][name] = {"activity_min": float(np.min(active)), "activity_max": float(np.max(active))}
    return result


def analyze_qb_only(path: Path, width: int, role: str) -> dict[str, Any]:
    data = load_csv(path)
    result: dict[str, Any] = {"path": str(path), "width_ps": width, "role": role, "qb": {}}
    for name in ("BJs", "BJL1", "BJL2"):
        result["qb"][name] = phase_record(data, name, role)
    result["bjl2_classification"] = classify_bjl2(result["qb"]["BJL2"])
    return result


def analyze_source_only(path: Path, width: int, role: str) -> dict[str, Any]:
    data = load_csv(path)
    return {
        "path": str(path),
        "width_ps": width,
        "role": role,
        "source": source_record(data),
        "jsl": jsl_record(data),
    }


def compare_case(physical: dict[str, Any], ideal: dict[str, Any], source_only: dict[str, Any]) -> dict[str, Any]:
    comparison: dict[str, Any] = {
        "physical_classification": physical["bjl2_classification"],
        "ideal_classification": ideal.get("bjl2_classification"),
        "physical_vs_ideal_bjl2_largest_turn": (physical["qb"]["BJL2"]["largest_segment"] or {}).get("delta_turns"),
        "ideal_bjl2_largest_turn": (ideal.get("qb", {}).get("BJL2", {}).get("largest_segment") or {}).get("delta_turns"),
        "physical_vs_ideal_bjl2_area_phi0": (physical["qb"]["BJL2"]["largest_segment"] or {}).get("area_phi0"),
        "ideal_bjl2_area_phi0": (ideal.get("qb", {}).get("BJL2", {}).get("largest_segment") or {}).get("area_phi0"),
        "source_only": source_only.get("source", {}),
        "physical_source": physical.get("source", {}),
    }
    for signal in ("I(L_SL|XBVM1)", "V(SL1)"):
        if signal in source_only.get("source", {}) and signal in physical.get("source", {}):
            comparison[f"{signal}_activity_p2p_ratio"] = physical["source"][signal]["activity_p2p"] / max(abs(source_only["source"][signal]["activity_p2p"]), 1e-30)
    return comparison


def path_for(kind: str, width: int, role: str) -> Path:
    if kind == "physical":
        return ROOT / "raw" / str(width) / role / "run-01.csv"
    if kind == "ideal":
        return REPO / "test/exploration/bvm-read-semantics-audit-and-jsl-width-bracket-v1-20260824/raw/replay" / f"{width}ps" / role / "run-01.csv"
    if kind == "source":
        return REPO / "test/exploration/bvm-read-semantics-audit-and-jsl-width-bracket-v1-20260824/raw" / f"{width}ps" / role.replace("_", "-") / "run-01.csv"
    raise ValueError(kind)


def write_summary(width: int, cases: dict[str, dict[str, Any]]) -> None:
    fields = ["role", "bjl2_classification", "bjl2_activity_p2p_turns", "bjl2_largest_turns", "bjl2_area_phi0", "bjs_activity_p2p_turns", "bjl1_activity_p2p_turns"]
    with (ROOT / "analysis" / f"{width}ps-summary.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for role, item in cases.items():
            bjl2 = item["qb"]["BJL2"]
            bjs = item["qb"]["BJs"]
            bjl1 = item["qb"]["BJL1"]
            segment = bjl2["largest_segment"] or {}
            writer.writerow({
                "role": role,
                "bjl2_classification": item["bjl2_classification"],
                "bjl2_activity_p2p_turns": bjl2["phase_activity_p2p_turns"],
                "bjl2_largest_turns": segment.get("delta_turns", 0.0),
                "bjl2_area_phi0": segment.get("area_phi0", 0.0),
                "bjs_activity_p2p_turns": bjs["phase_activity_p2p_turns"],
                "bjl1_activity_p2p_turns": bjl1["phase_activity_p2p_turns"],
            })


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--width", type=int, choices=(13, 14), required=True)
    args = parser.parse_args()
    roles = ("logical1_read", "logical0_read", "logical1_no_read_control", "logical0_no_read_control")
    cases: dict[str, dict[str, Any]] = {}
    comparisons: dict[str, Any] = {}
    for role in roles:
        physical_path = path_for("physical", args.width, role)
        if not physical_path.exists():
            raise SystemExit(f"missing physical raw: {physical_path}")
        physical = analyze_case(physical_path, args.width, role)
        cases[role] = physical
        ideal_path = path_for("ideal", args.width, role)
        source_role = role.replace("_", "-")
        source_path = path_for("source", args.width, role) if role.endswith("_read") else REPO / "test/exploration/paper-sl-l0-20260824/raw" / ("logical1-read0-control" if role.startswith("logical1") else "logical0-read0-control") / "run-01.csv"
        ideal = analyze_qb_only(ideal_path, args.width, role) if ideal_path.exists() else {"missing": True}
        source = analyze_source_only(source_path, args.width, role) if source_path.exists() else {"missing": True}
        comparisons[role] = compare_case(physical, ideal, source)
    result = {"width_ps": args.width, "cases": cases, "comparisons": comparisons, "clean_band_turns": CLEAN_BAND, "windows_ps": {"pre": PRE, "activity": ACTIVE, "post": POST}}
    output = ROOT / "analysis" / f"physical-{args.width}ps-metrics.json"
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_summary(args.width, cases)
    print(json.dumps({"width_ps": args.width, "classifications": {role: item["bjl2_classification"] for role, item in cases.items()}}, indent=2))


if __name__ == "__main__":
    main()
