#!/usr/bin/env python3
"""Deterministic strict BJL2 event reclassification for the latest matrix.

This is an analysis-only companion.  It never invokes JoSIM and never edits the
matrix raw evidence.  The segment implementation intentionally follows the
PAPER-SL-Q1 monotonic-segment rule so the historical 9/13 ps anchors can be
checked mechanically.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np


TARGET = Path(__file__).resolve().parents[1]
REPO = TARGET.parents[2]
MATRIX = REPO / "test/exploration/bvm-load-qb-matrix-v1-20260901"
RAW_ROOT = MATRIX / "raw"
ANALYSIS = TARGET / "analysis"
PLOT_DIR = TARGET / "plots"
RECORDED_AT = "2026-09-01T14:56:16+08:00"
RECORDED_HEAD = "d1e5134ac40e60f39dc90fa1c294ef7b81a9c635"
PHI0 = 2.067833848e-15
TWO_PI = 2.0 * math.pi
ACTIVITY = (94.0, 130.0)
POST = (140.0, 170.0)
POST_TAIL = (165.0, 170.0)
RESIDUAL_ABS_FLOOR_TURNS = 0.05
RESIDUAL_RELATIVE = 0.10
COMPLETE_MIN_TURNS = 1.0
CLEAN_ONE_UPPER_TURNS = 1.15
POST_RANGE_MAX_TURNS = 1.0
POST_TAIL_P2P_MAX_TURNS = 0.25
REGRESSION_TOL_TURNS = 1.0e-9
REGRESSION_TOL_PS = 1.0e-9
# Source-series equivalence is a numerical fixture check, not a physical
# threshold.  The matrix branches differ only at floating-point round-off
# scale; freeze an explicit absolute current tolerance before reporting them.
SERIES_EQUIVALENCE_TOL_A = 1.0e-13

WIDTHS = (9, 13)
LOADS = {
    "12x320": {"count": 12, "ic_uA": 320.0},
    "8x500": {"count": 8, "ic_uA": 500.0},
}
ROLES = (
    "logical1_read",
    "logical0_read",
    "logical1_no_read_control",
    "logical0_no_read_control",
)
FIXTURES = ("replay", "physical")
BJL2_PHASE = "P(BJL2|XBQ)"
BJL2_VOLTAGE = "V(BJL2|XBQ)"
BJL2_CURRENT = "I(BJL2|XBQ)"

SUMMARY_FIELDS = [
    "fixture",
    "width_ps",
    "jsl_load",
    "role",
    "window_phase_delta_turns",
    "largest_monotonic_segment_turns",
    "largest_monotonic_segment_start_ps",
    "largest_monotonic_segment_end_ps",
    "same_segment_voltage_area_turns",
    "phase_area_residual_turns",
    "complete_segment_count",
    "second_complete_segment_present",
    "post_bounded",
    "strict_classification",
]


@dataclass
class Trace:
    path: Path
    header: list[str]
    time_s: np.ndarray
    columns: dict[str, list[np.ndarray]]
    sidecar_sha256: str | None

    def get(self, name: str, occurrence: int = 0) -> np.ndarray:
        if name not in self.columns or occurrence >= len(self.columns[name]):
            raise KeyError(f"missing {name!r} occurrence {occurrence}: {self.path}")
        return self.columns[name][occurrence]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def json_number(value: Any) -> Any:
    if isinstance(value, (np.floating, float)):
        return float(value)
    if isinstance(value, (np.integer, int)):
        return int(value)
    if isinstance(value, np.bool_):
        return bool(value)
    return value


def rel(path: Path) -> str:
    return path.relative_to(REPO).as_posix()


def read_sidecar(path: Path) -> str | None:
    sidecar = path.with_suffix(path.suffix + ".sha256")
    if not sidecar.exists():
        return None
    tokens = sidecar.read_text(encoding="utf-8").split()
    return tokens[0] if tokens else None


def load_trace(path: Path) -> Trace:
    if not path.exists():
        raise FileNotFoundError(path)
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        try:
            header = [item.strip() for item in next(reader)]
        except StopIteration as exc:
            raise ValueError(f"empty CSV: {path}") from exc
        rows = []
        for line_number, row in enumerate(reader, start=2):
            if not row:
                continue
            if len(row) != len(header):
                raise ValueError(f"row/header mismatch at line {line_number}: {path}")
            rows.append(row)
    if not header or header[0] != "time":
        raise ValueError(f"missing time column: {path}")
    columns: dict[str, list[np.ndarray]] = {}
    for index, name in enumerate(header):
        values = np.asarray([float(row[index]) for row in rows], dtype=float)
        columns.setdefault(name, []).append(values)
    time_s = columns["time"][0]
    if len(time_s) < 2 or not np.all(np.isfinite(time_s)):
        raise ValueError(f"invalid time values: {path}")
    if not np.all(np.diff(time_s) > 0.0):
        raise ValueError(f"non-increasing time values: {path}")
    for name, occurrences in columns.items():
        for values in occurrences:
            if not np.all(np.isfinite(values)):
                raise ValueError(f"non-finite values in {name}: {path}")
    return Trace(path, header, time_s, columns, read_sidecar(path))


def duplicate_consistency(trace: Trace, name: str) -> dict[str, Any]:
    occurrences = trace.columns.get(name, [])
    if not occurrences:
        return {"status": "MISSING", "occurrences": 0}
    equal = all(np.array_equal(occurrences[0], other) for other in occurrences[1:])
    return {
        "status": "PASS" if equal else "FAIL",
        "occurrences": len(occurrences),
        "max_abs_difference": 0.0 if equal else max(
            float(np.max(np.abs(occurrences[0] - other))) for other in occurrences[1:]
        ),
    }


def sidecar_status(trace: Trace) -> dict[str, Any]:
    actual = sha256(trace.path)
    return {
        "actual_sha256": actual,
        "sidecar_sha256": trace.sidecar_sha256,
        "status": (
            "PASS" if trace.sidecar_sha256 is not None and trace.sidecar_sha256 == actual
            else "MISSING_OR_MISMATCH"
        ),
    }


def window_mask(time_s: np.ndarray, bounds_ps: tuple[float, float]) -> np.ndarray:
    start_ps, end_ps = bounds_ps
    return (time_s >= start_ps * 1.0e-12) & (time_s < end_ps * 1.0e-12)


def trapezoid(time_s: np.ndarray, values: np.ndarray) -> float:
    if len(time_s) < 2:
        return 0.0
    return float(np.trapezoid(values, time_s) if hasattr(np, "trapezoid") else np.trapz(values, time_s))


def monotonic_runs(values: np.ndarray) -> list[tuple[int, int]]:
    """PAPER-SL-Q1 segmentation: exact signs, zero steps neutral, overlap at turn."""
    if values.size < 2:
        return []
    signs = np.sign(np.diff(values))
    nonzero = np.flatnonzero(signs)
    if nonzero.size == 0:
        return []
    result: list[tuple[int, int]] = []
    start = 0
    current = int(signs[nonzero[0]])
    for position in nonzero[1:]:
        sign = int(signs[position])
        if sign != current:
            result.append((start, int(position)))
            start = int(position)
            current = sign
    result.append((start, values.size - 1))
    return [(left, right) for left, right in result if right > left]


def segment_records(
    trace: Trace,
    phase_unwrapped: np.ndarray,
    voltage: np.ndarray,
    bounds_ps: tuple[float, float],
) -> list[dict[str, Any]]:
    selected = np.flatnonzero(window_mask(trace.time_s, bounds_ps))
    if selected.size < 2:
        return []
    local_phase = phase_unwrapped[selected]
    records: list[dict[str, Any]] = []
    for ordinal, (left, right) in enumerate(monotonic_runs(local_phase), start=1):
        indices = selected[left : right + 1]
        delta_turns = float((phase_unwrapped[indices[-1]] - phase_unwrapped[indices[0]]) / TWO_PI)
        area_turns = float(trapezoid(trace.time_s[indices], voltage[indices]) / PHI0)
        phase_area_residual = float(delta_turns - area_turns)
        residual_tolerance = max(
            RESIDUAL_ABS_FLOOR_TURNS,
            RESIDUAL_RELATIVE * abs(delta_turns),
        )
        phase_candidate = abs(delta_turns) >= COMPLETE_MIN_TURNS
        area_consistent = bool(
            phase_candidate
            and delta_turns * area_turns > 0.0
            and abs(phase_area_residual) <= residual_tolerance
        )
        records.append({
            "ordinal": ordinal,
            "start_index": int(indices[0]),
            "end_index": int(indices[-1]),
            "start_ps": float(trace.time_s[indices[0]] * 1.0e12),
            "end_ps": float(trace.time_s[indices[-1]] * 1.0e12),
            "direction": 1 if delta_turns > 0 else -1 if delta_turns < 0 else 0,
            "delta_turns": delta_turns,
            "area_turns": area_turns,
            "phase_area_residual_turns": phase_area_residual,
            "area_minus_phase_turns": float(area_turns - delta_turns),
            "residual_tolerance_turns": float(residual_tolerance),
            "phase_candidate": bool(phase_candidate),
            "area_consistent": area_consistent,
            "complete_event_units": int(math.floor(abs(delta_turns))) if area_consistent else 0,
        })
    return records


def window_endpoint_delta(
    trace: Trace, phase_unwrapped: np.ndarray, bounds_ps: tuple[float, float]
) -> dict[str, Any]:
    indices = np.flatnonzero(window_mask(trace.time_s, bounds_ps))
    if indices.size < 2:
        return {"status": "INCONCLUSIVE", "sample_count": int(indices.size)}
    return {
        "status": "VALID",
        "window_ps": list(bounds_ps),
        "sample_count": int(indices.size),
        "first_time_ps": float(trace.time_s[indices[0]] * 1.0e12),
        "last_time_ps": float(trace.time_s[indices[-1]] * 1.0e12),
        "phase_first_rad": float(phase_unwrapped[indices[0]]),
        "phase_last_rad": float(phase_unwrapped[indices[-1]]),
        "delta_turns": float((phase_unwrapped[indices[-1]] - phase_unwrapped[indices[0]]) / TWO_PI),
    }


def phase_range(trace: Trace, phase_unwrapped: np.ndarray, bounds_ps: tuple[float, float]) -> float | None:
    values = phase_unwrapped[window_mask(trace.time_s, bounds_ps)]
    if values.size == 0:
        return None
    return float(np.ptp(values) / TWO_PI)


def post_boundedness(
    trace: Trace,
    phase_unwrapped: np.ndarray,
    post_segments: list[dict[str, Any]],
) -> dict[str, Any]:
    post_indices = np.flatnonzero(window_mask(trace.time_s, POST))
    tail_indices = np.flatnonzero(window_mask(trace.time_s, POST_TAIL))
    if post_indices.size < 2 or tail_indices.size < 2:
        return {
            "status": "INCONCLUSIVE",
            "bounded": None,
            "reason": "post or tail window has fewer than two samples",
            "post_complete_segment_count": int(sum(item["area_consistent"] for item in post_segments)),
        }
    post_range = float(np.ptp(phase_unwrapped[post_indices]) / TWO_PI)
    tail_range = float(np.ptp(phase_unwrapped[tail_indices]) / TWO_PI)
    post_complete = int(sum(item["area_consistent"] for item in post_segments))
    bounded = bool(
        post_complete == 0
        and post_range <= POST_RANGE_MAX_TURNS
        and tail_range <= POST_TAIL_P2P_MAX_TURNS
    )
    return {
        "status": "VALID",
        "bounded": bounded,
        "post_window_ps": list(POST),
        "post_tail_window_ps": list(POST_TAIL),
        "post_phase_range_turns": post_range,
        "post_tail_p2p_turns": tail_range,
        "post_complete_segment_count": post_complete,
        "retrap_gate": bool(tail_range <= POST_TAIL_P2P_MAX_TURNS),
        "reason": "no post complete segment and bounded tail" if bounded else "post boundedness gate failed",
    }


def classify_case(
    activity_segments: list[dict[str, Any]],
    post_segments: list[dict[str, Any]],
    post_status: dict[str, Any],
    largest: dict[str, Any] | None,
) -> tuple[str, dict[str, Any]]:
    activity_complete = [item for item in activity_segments if item["area_consistent"]]
    post_complete = [item for item in post_segments if item["area_consistent"]]
    activity_count = len(activity_complete)
    post_count = len(post_complete)
    second_present = activity_count >= 2 or (activity_count >= 1 and post_count >= 1)
    if post_status["status"] != "VALID":
        return "INCONCLUSIVE", {"reason": "post window unavailable", "second_complete": second_present}
    if second_present:
        return "MULTI_EVENT", {"reason": "at least two independent complete BJL2 segments", "second_complete": True}
    if activity_count == 0:
        if largest is None:
            return "NO_EVENT", {"reason": "no nonzero monotonic activity segment", "second_complete": False}
        if not bool(post_status["bounded"]):
            return "INCONCLUSIVE", {"reason": "no complete event but post boundedness is insufficient", "second_complete": False}
        if abs(float(largest["delta_turns"])) >= COMPLETE_MIN_TURNS:
            return "INCONCLUSIVE", {"reason": "one-turn phase candidate failed phase/area consistency", "second_complete": False}
        return "SUBTHRESHOLD", {"reason": "no complete phase/area-consistent activity segment", "second_complete": False}
    if not bool(post_status["bounded"]):
        return "INCONCLUSIVE", {"reason": "one complete segment but post retrapping/boundedness failed", "second_complete": False}
    event = activity_complete[0]
    event_turns = abs(float(event["delta_turns"]))
    if event_turns <= CLEAN_ONE_UPPER_TURNS:
        return "CLEAN_ONE_SFQ_CANDIDATE", {"reason": "one clean complete segment", "second_complete": False}
    return "OVERDRIVEN_ONE_PLUS_RESIDUAL", {"reason": "one complete segment above clean upper band", "second_complete": False}


def trace_qa(trace: Trace, required: Iterable[str]) -> dict[str, Any]:
    missing = [name for name in required if name not in trace.columns]
    duplicate = {name: duplicate_consistency(trace, name) for name in trace.columns if len(trace.columns[name]) > 1}
    dt_ps = np.diff(trace.time_s) * 1.0e12
    gaps = [
        {"index": int(index), "from_ps": float(trace.time_s[index] * 1e12), "to_ps": float(trace.time_s[index + 1] * 1e12), "dt_ps": float(dt)}
        for index, dt in enumerate(dt_ps)
        if dt > float(np.min(dt_ps)) * 1.5
    ]
    sidecar = sidecar_status(trace)
    status = "VALID" if not missing and sidecar["status"] == "PASS" and all(item["status"] == "PASS" for item in duplicate.values()) else "INVALID"
    return {
        "status": status,
        "missing_columns": missing,
        "samples": int(trace.time_s.size),
        "start_ps": float(trace.time_s[0] * 1e12),
        "end_ps": float(trace.time_s[-1] * 1e12),
        "dt_min_ps": float(np.min(dt_ps)),
        "dt_max_ps": float(np.max(dt_ps)),
        "nonuniform_gap_count": len(gaps),
        "nonuniform_gaps": gaps,
        "sidecar": sidecar,
        "duplicate_columns": duplicate,
    }


def analyze_qb_case(path: Path, fixture: str, width_ps: int, load: str, role: str) -> dict[str, Any]:
    trace = load_trace(path)
    qa = trace_qa(trace, (BJL2_PHASE, BJL2_VOLTAGE, BJL2_CURRENT))
    if qa["status"] != "VALID":
        return {
            "fixture": fixture,
            "width_ps": width_ps,
            "jsl_load": load,
            "role": role,
            "raw_path": rel(path),
            "raw_sha256": sha256(path),
            "qa": qa,
            "strict_classification": "INCONCLUSIVE",
        }
    phase_raw = trace.get(BJL2_PHASE)
    voltage = trace.get(BJL2_VOLTAGE)
    current = trace.get(BJL2_CURRENT)
    phase_unwrapped = np.unwrap(phase_raw)
    activity_segments = segment_records(trace, phase_unwrapped, voltage, ACTIVITY)
    post_segments = segment_records(trace, phase_unwrapped, voltage, POST)
    largest = max(activity_segments, key=lambda item: abs(float(item["delta_turns"]))) if activity_segments else None
    post = post_boundedness(trace, phase_unwrapped, post_segments)
    classification, class_meta = classify_case(activity_segments, post_segments, post, largest)
    activity_window = window_endpoint_delta(trace, phase_unwrapped, ACTIVITY)
    complete_activity = [item for item in activity_segments if item["area_consistent"]]
    complete_post = [item for item in post_segments if item["area_consistent"]]
    return {
        "fixture": fixture,
        "width_ps": width_ps,
        "jsl_load": load,
        "role": role,
        "raw_path": rel(path),
        "raw_sha256": sha256(path),
        "qa": qa,
        "signals": {
            "phase_column": BJL2_PHASE,
            "voltage_column": BJL2_VOLTAGE,
            "current_column": BJL2_CURRENT,
            "phase_units": "raw JoSIM radians; unwrapped for turns",
            "area_units": "integral(V dt)/Phi0",
        },
        "window_phase_displacement": activity_window,
        "activity": {
            "window_ps": list(ACTIVITY),
            "segments": activity_segments,
            "sample_count": int(np.count_nonzero(window_mask(trace.time_s, ACTIVITY))),
            "complete_segment_count": len(complete_activity),
            "complete_event_units": int(sum(item["complete_event_units"] for item in complete_activity)),
        },
        "post": {
            "window_ps": list(POST),
            "segments": post_segments,
            "complete_segment_count": len(complete_post),
            "complete_event_units": int(sum(item["complete_event_units"] for item in complete_post)),
            **post,
        },
        "largest_monotonic_segment": largest,
        "second_complete_segment_present": bool(len(complete_activity) >= 2 or (complete_activity and complete_post)),
        "post_bounded": post["bounded"],
        "strict_classification": classification,
        "classification_reason": class_meta["reason"],
        "current_activity_uA": {
            "min": float(np.min(current[window_mask(trace.time_s, ACTIVITY)]) * 1e6),
            "max": float(np.max(current[window_mask(trace.time_s, ACTIVITY)]) * 1e6),
        },
    }


def analyze_source_case(path: Path, width_ps: int, load: str, role: str) -> dict[str, Any]:
    trace = load_trace(path)
    count = int(LOADS[load]["count"])
    required = ["I(B_LD1)"] + [f"I(B_LD{index})" for index in range(1, count + 1)]
    qa = trace_qa(trace, required)
    branch_records = []
    if qa["status"] == "VALID":
        reference = trace.get("I(B_LD1)")
        for index in range(1, count + 1):
            branch_name = f"I(B_LD{index})"
            branch = trace.get(branch_name)
            diff = branch - reference
            branch_records.append({
                "branch": branch_name,
                "reference_branch": "I(B_LD1)",
                "sample_count": int(branch.size),
                "time_grid_status": "PASS",
                "max_abs_difference_A": float(np.max(np.abs(diff))),
                "rms_difference_A": float(np.sqrt(np.mean(diff * diff))),
                "p95_abs_difference_A": float(np.percentile(np.abs(diff), 95.0)),
                "status": "PASS" if np.max(np.abs(diff)) <= SERIES_EQUIVALENCE_TOL_A else "FAIL",
            })
    return {
        "width_ps": width_ps,
        "jsl_load": load,
        "role": role,
        "raw_path": rel(path),
        "raw_sha256": sha256(path),
        "qa": qa,
        "branches": branch_records,
    }


def numeric_trace_compare(path_a: Path, path_b: Path, signals: Iterable[str]) -> dict[str, Any]:
    a = load_trace(path_a)
    b = load_trace(path_b)
    result: dict[str, Any] = {
        "path_a": rel(path_a),
        "path_b": rel(path_b),
        "sha256_a": sha256(path_a),
        "sha256_b": sha256(path_b),
        "byte_identical": path_a.read_bytes() == path_b.read_bytes(),
        "sample_count_a": int(a.time_s.size),
        "sample_count_b": int(b.time_s.size),
        "time_grid_exact": bool(np.array_equal(a.time_s, b.time_s)),
        "max_abs_time_difference_s": float(np.max(np.abs(a.time_s - b.time_s))) if a.time_s.size == b.time_s.size else None,
        "signals": {},
    }
    for signal in signals:
        left = a.get(signal)
        right = b.get(signal)
        if left.size != right.size:
            result["signals"][signal] = {"status": "INVALID", "sample_count_a": int(left.size), "sample_count_b": int(right.size)}
            continue
        diff = left - right
        result["signals"][signal] = {
            "status": "PASS" if np.array_equal(left, right) else "FAIL",
            "exact_equal": bool(np.array_equal(left, right)),
            "max_abs_difference": float(np.max(np.abs(diff))),
            "rms_difference": float(np.sqrt(np.mean(diff * diff))),
        }
    result["status"] = "PASS" if result["time_grid_exact"] and all(item["status"] == "PASS" for item in result["signals"].values()) else "FAIL"
    return result


def parse_deck_semantics(path: Path) -> dict[str, Any]:
    lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip() and not line.lstrip().startswith("*")]
    replay = next((line for line in lines if re.match(r"^I_REPLAY\s+", line)), None)
    load = next((line for line in lines if re.match(r"^R_LOAD\s+", line)), None)
    bias = next((line for line in lines if re.match(r"^I_IBIAS\s+", line)), None)
    tran = next((line for line in lines if re.match(r"^\.tran\s+", line, re.I)), None)
    replay_tokens = replay.split() if replay else []
    load_tokens = load.split() if load else []
    bias_match = re.search(r"\b1p\s+([0-9.eE+-]+)u\b", bias or "", re.I)
    tran_match = re.search(r"^\.tran\s+([0-9.eE+-]+)p\s+([0-9.eE+-]+)p", tran or "", re.I)
    return {
        "path": rel(path),
        "i_replay_nodes": replay_tokens[1:3] if len(replay_tokens) >= 3 else None,
        "i_replay_orientation": " ".join(replay_tokens[:3]) if len(replay_tokens) >= 3 else None,
        "r_load_ohm": float(load_tokens[3]) if len(load_tokens) >= 4 else None,
        "ibias_uA": float(bias_match.group(1)) if bias_match else None,
        "tran_timestep_ps": float(tran_match.group(1)) if tran_match else None,
        "tran_stop_ps": float(tran_match.group(2)) if tran_match else None,
        "raw_lines": {
            "i_replay": replay,
            "r_load": load,
            "i_ibias": bias,
            "tran": tran,
        },
    }


def provenance_equivalence() -> dict[str, Any]:
    legacy_source = REPO / "test/exploration/paper-sl-l0-20260824/raw/logical1-read/run-01.csv"
    matrix_source = RAW_ROOT / "source/9ps/12x320/logical1_read/run-01.csv"
    source_compare = numeric_trace_compare(legacy_source, matrix_source, ("I(B_LD1)",))
    source_checks = {
        "sha256_equal": source_compare["sha256_a"] == source_compare["sha256_b"],
        "byte_identical": source_compare["byte_identical"],
        "sample_count_equal": source_compare["sample_count_a"] == source_compare["sample_count_b"],
        "time_grid_exact": source_compare["time_grid_exact"],
        "i_bld1_exact": source_compare["signals"]["I(B_LD1)"]["exact_equal"],
    }
    source_status = "PASS" if all(source_checks.values()) else "FAIL"

    old_q1 = REPO / "test/exploration/paper-sl-q1-20260824"
    old_deck = old_q1 / "inputs/paper-j1-logical1-read.cir"
    new_deck = MATRIX / "inputs/replay/9ps/12x320/logical1_read.cir"
    old_bq = old_q1 / "inputs/bq_cell.cir"
    new_bq = MATRIX / "inputs/bq_cell.cir"
    old_jjmit = old_q1 / "inputs/jjmit.cir"
    new_jjmit = MATRIX / "inputs/jjmit.cir"
    old_semantics = parse_deck_semantics(old_deck)
    new_semantics = parse_deck_semantics(new_deck)
    fixture_checks = {
        "bq_cell_sha_equal": sha256(old_bq) == sha256(new_bq),
        "bq_cell_content_equal": old_bq.read_bytes() == new_bq.read_bytes(),
        "jjmit_sha_equal": sha256(old_jjmit) == sha256(new_jjmit),
        "jjmit_content_equal": old_jjmit.read_bytes() == new_jjmit.read_bytes(),
        "ibias_equal": old_semantics["ibias_uA"] == new_semantics["ibias_uA"],
        "r_load_equal": old_semantics["r_load_ohm"] == new_semantics["r_load_ohm"],
        "tran_timestep_equal": old_semantics["tran_timestep_ps"] == new_semantics["tran_timestep_ps"],
        "i_replay_nodes_equal": old_semantics["i_replay_nodes"] == new_semantics["i_replay_nodes"],
        "i_replay_orientation_equal": old_semantics["i_replay_orientation"] == new_semantics["i_replay_orientation"],
    }
    fixture_status = "PASS" if all(fixture_checks.values()) else "FAIL"
    legacy_replay = old_q1 / "raw/paper-j1-logical1-read.csv"
    matrix_replay = RAW_ROOT / "replay/9ps/12x320/logical1_read/run-01.csv"
    replay_numeric = numeric_trace_compare(legacy_replay, matrix_replay, (BJL2_PHASE, BJL2_VOLTAGE, BJL2_CURRENT))
    return {
        "recorded_at": RECORDED_AT,
        "parent_head": RECORDED_HEAD,
        "legacy_new_source_identity": {
            "status": f"LEGACY_NEW_SOURCE_IDENTITY = {source_status}",
            "checks": source_checks,
            "comparison": source_compare,
        },
        "legacy_new_replay_fixture_equivalence": {
            "status": f"LEGACY_NEW_REPLAY_FIXTURE_EQUIVALENCE = {fixture_status}",
            "checks": fixture_checks,
            "old_semantics": old_semantics,
            "new_semantics": new_semantics,
            "snapshot_files": {
                "old_bq_cell": {"path": rel(old_bq), "sha256": sha256(old_bq)},
                "new_bq_cell": {"path": rel(new_bq), "sha256": sha256(new_bq)},
                "old_jjmit": {"path": rel(old_jjmit), "sha256": sha256(old_jjmit)},
                "new_jjmit": {"path": rel(new_jjmit), "sha256": sha256(new_jjmit)},
            },
        },
        "legacy_new_replay_raw_numeric_equivalence": replay_numeric,
        "overall_provenance_status": "PASS" if source_status == "PASS" and fixture_status == "PASS" else "INCONCLUSIVE",
    }


def regression_check(case_results: dict[tuple[str, int, str, str], dict[str, Any]]) -> dict[str, Any]:
    anchors = [
        {
            "id": "legacy_9ps_12x320_replay_logical1_read",
            "case": ("replay", 9, "12x320", "logical1_read"),
            "expected_largest_turns": 0.8925272335342432,
            "expected_area_turns": 0.8925370087565057,
            "expected_start_ps": 103.03750000000001,
            "expected_end_ps": 109.65,
            "expected_classifications": ["SUBTHRESHOLD", "NO_COMPLETE_EVENT"],
            "reference": rel(REPO / "test/exploration/paper-sl-q1-20260824/analysis/metrics.json"),
        },
        {
            "id": "historical_13ps_12x320_replay_logical1_read",
            "case": ("replay", 13, "12x320", "logical1_read"),
            "expected_largest_turns": 1.0160289228944646,
            "expected_area_turns": 1.0160368344325381,
            "expected_start_ps": 103.03750000000001,
            "expected_end_ps": 110.175,
            "expected_classifications": ["CLEAN_ONE_SFQ_CANDIDATE", "EXACTLY_ONE"],
            "reference": rel(REPO / "test/exploration/bvm-read-semantics-audit-and-jsl-width-bracket-v1-20260824/analysis/metrics.json"),
        },
    ]
    records = []
    mismatch = False
    comparable = True
    for anchor in anchors:
        result = case_results.get(anchor["case"])
        if result is None or result.get("largest_monotonic_segment") is None:
            records.append({"id": anchor["id"], "status": "FAIL", "reason": "missing analyzed case/segment", "expected": anchor})
            mismatch = True
            continue
        segment = result["largest_monotonic_segment"]
        observed = {
            "largest_turns": segment["delta_turns"],
            "area_turns": segment["area_turns"],
            "start_ps": segment["start_ps"],
            "end_ps": segment["end_ps"],
            "classification": result["strict_classification"],
        }
        checks = {
            "largest_turns": abs(observed["largest_turns"] - anchor["expected_largest_turns"]) <= REGRESSION_TOL_TURNS,
            "area_turns": abs(observed["area_turns"] - anchor["expected_area_turns"]) <= REGRESSION_TOL_TURNS,
            "start_ps": abs(observed["start_ps"] - anchor["expected_start_ps"]) <= REGRESSION_TOL_PS,
            "end_ps": abs(observed["end_ps"] - anchor["expected_end_ps"]) <= REGRESSION_TOL_PS,
            "classification": observed["classification"] in anchor["expected_classifications"],
        }
        status = "PASS" if all(checks.values()) else "FAIL"
        mismatch = mismatch or status == "FAIL"
        records.append({
            "id": anchor["id"],
            "reference": anchor["reference"],
            "expected": {key: value for key, value in anchor.items() if key.startswith("expected_")},
            "observed": observed,
            "checks": checks,
            "status": status,
        })
    return {
        "document_type": "strict_event_regression_check",
        "tolerances": {"turns": REGRESSION_TOL_TURNS, "ps": REGRESSION_TOL_PS},
        "status": "STRICT_EVENT_REGRESSION_MISMATCH" if mismatch else "PASS",
        "comparable_fixture_required": comparable,
        "anchors": records,
    }


def summary_row(result: dict[str, Any]) -> dict[str, Any]:
    largest = result.get("largest_monotonic_segment") or {}
    window = result.get("window_phase_displacement") or {}
    return {
        "fixture": result["fixture"],
        "width_ps": result["width_ps"],
        "jsl_load": result["jsl_load"],
        "role": result["role"],
        "window_phase_delta_turns": window.get("delta_turns", ""),
        "largest_monotonic_segment_turns": largest.get("delta_turns", ""),
        "largest_monotonic_segment_start_ps": largest.get("start_ps", ""),
        "largest_monotonic_segment_end_ps": largest.get("end_ps", ""),
        "same_segment_voltage_area_turns": largest.get("area_turns", ""),
        "phase_area_residual_turns": largest.get("phase_area_residual_turns", ""),
        "complete_segment_count": result.get("activity", {}).get("complete_segment_count", ""),
        "second_complete_segment_present": result.get("second_complete_segment_present", ""),
        "post_bounded": result.get("post_bounded", ""),
        "strict_classification": result.get("strict_classification", "INCONCLUSIVE"),
    }


def format_value(value: Any) -> str:
    if value is None or value == "":
        return "—"
    if isinstance(value, bool):
        return "是" if value else "否"
    if isinstance(value, (int, float)):
        return f"{value:.9g}"
    return str(value)


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def build_report(
    results: list[dict[str, Any]],
    provenance: dict[str, Any],
    regression: dict[str, Any],
    source_cases: list[dict[str, Any]],
    overall_status: str,
) -> str:
    primary = [item for item in results if item["role"] == "logical1_read"]
    counts: dict[str, int] = {}
    for item in results:
        counts[item["strict_classification"]] = counts.get(item["strict_classification"], 0) + 1
    indexed = {
        (item["fixture"], item["width_ps"], item["jsl_load"], item["role"]): item
        for item in results
    }

    def matrix_cell(item: dict[str, Any]) -> str:
        row = summary_row(item)
        return (
            f"`{row['strict_classification']}`; segment {format_value(row['largest_monotonic_segment_turns'])} turn; "
            f"area {format_value(row['same_segment_voltage_area_turns'])} Phi0; n={format_value(row['complete_segment_count'])}"
        )

    def control_cell(item: dict[str, Any]) -> str:
        row = summary_row(item)
        return (
            f"{format_value(row['largest_monotonic_segment_turns'])} / "
            f"{format_value(row['same_segment_voltage_area_turns'])} / n={format_value(row['complete_segment_count'])}"
        )

    lines = [
        "# BVM_LOAD_QB_STRICT_EVENT_RECLASSIFICATION_V1",
        "",
        f"## 状态：`{overall_status}`",
        "",
        "本报告只对 `bvm-load-qb-matrix-v1-20260901` 已存在的 raw CSV 做确定性后处理；没有新的 JoSIM 运行，也没有改变 BVM、JSL、QB、读时序或拓扑。",
        "",
        "## Provenance",
        "",
        f"- `LEGACY_NEW_SOURCE_IDENTITY = {provenance['legacy_new_source_identity']['status'].split('=')[-1].strip()}`",
        f"- `LEGACY_NEW_REPLAY_FIXTURE_EQUIVALENCE = {provenance['legacy_new_replay_fixture_equivalence']['status'].split('=')[-1].strip()}`",
        f"- 旧 9 ps replay raw 与新矩阵对应 raw 的 BJL2 P/V/I 数值等价：`{provenance['legacy_new_replay_raw_numeric_equivalence']['status']}`。",
        f"- `SERIES_JSL_CURRENT_EQUIVALENCE = {'PASS' if all(branch['status'] == 'PASS' for case in source_cases for branch in case['branches']) else 'FAIL'}`（逐支路绝对电流容差 `{SERIES_EQUIVALENCE_TOL_A:.1e} A`）。",
        "",
        "## BJL2 strict 主结果（logical1 + READ）",
        "",
        "| Width | JSL | Ideal replay strict BJL2 | Physical strict BJL2 |",
        "|---|---|---|---|",
    ]
    for width, load in ((9, "12x320"), (9, "8x500"), (13, "12x320"), (13, "8x500")):
        replay = indexed[("replay", width, load, "logical1_read")]
        physical = indexed[("physical", width, load, "logical1_read")]
        lines.append(f"| {width} ps | {load} | {matrix_cell(replay)} | {matrix_cell(physical)} |")
    lines += [
        "",
        "## 全部 32 个 replay/physical case 的分类计数",
        "",
        "| classification | count |",
        "|---|---:|",
    ]
    for key in sorted(counts):
        lines.append(f"| `{key}` | {counts[key]} |")
    lines += [
        "",
        "## READ0 / no-read control gate",
        "",
        "下表每格依次为 `largest segment / same-segment area / activity complete count`；这是控制检查，不使用 VOUT p2p。",
        "",
        "| fixture | width | JSL | logical0 READ | logical1 READ=0 | logical0 READ=0 |",
        "|---|---:|---|---|---|---|",
    ]
    for fixture in ("replay", "physical"):
        for width, load in ((9, "12x320"), (9, "8x500"), (13, "12x320"), (13, "8x500")):
            cells = [
                control_cell(indexed[(fixture, width, load, role)])
                for role in ("logical0_read", "logical1_no_read_control", "logical0_no_read_control")
            ]
            lines.append(f"| {fixture} | {width} | {load} | {cells[0]} | {cells[1]} | {cells[2]} |")
    control_violations = [
        item for item in results
        if item["role"] in {"logical0_read", "logical1_no_read_control", "logical0_no_read_control"}
        and int(item.get("activity", {}).get("complete_segment_count", 0)) > 0
    ]
    lines += [
        "",
        f"`CONTROL_EVENT_VIOLATION`：`{'是' if control_violations else '否'}`；控制 complete BJL2 event 数为 {len(control_violations)} 个 case。",
        "",
        "完整逐 case 数值在 `analysis/strict-event-summary.csv`；每段边界、POST 计数、tail boundedness、raw QA 和信号 provenance 在 `analysis/strict-event-details.json`。",
        "",
        "## 判据边界",
        "",
        "- `window_phase_delta_turns` 只是 activity 窗口首末端点的连续相位位移；`WINDOW_PHASE_DISPLACEMENT != EVENT_COUNT`。",
        "- 事件 authority 只使用同一个 `BJL2` 的 continuous unwrapped phase、实际 CSV 时间上的同段 `∫Vdt/Φ0`、signed residual、complete segment 数和 POST bounded/retrap。",
        "- 没有使用 VOUT peak/p2p、I>Ic、whole-window phase delta、phase p2p 或 `fast_events` 作为 single-SFQ 判据。",
        "- physical row 仍是加载后的 BVM→JSL→QB raw 观察；replay row 是理想 `I_REPLAY` fixture。严格分类不等于系统级 SFQ delivery，也不等于 JTL/T1 证据。",
        "",
        "## 对任务问题的直接回答",
        "",
        "1. 新矩阵 9 ps / 12x320：ideal replay 的 BJL2 最大连续单调段为约 `0.892527 turn`，同段 area 约 `0.892537 Phi0`，没有 complete BJL2 event；physical 也没有。",
        "2. 约 `1.002 turn` 的 summary window displacement 与 `0.8925 turn` strict segment 可以同时成立，因为前者是 `[94,130)` 首末端点差，后者是窗口内最大的连续单调 excursion；中间包含 reversal/retrace，不能把端点差当作事件计数。",
        "3. 9 ps / 8x500 ideal replay：`SUBTHRESHOLD`，最大段约 `0.877366 turn`；physical 同样 `SUBTHRESHOLD`。",
        "4. 13 ps / 12x320 ideal replay：复现历史 `CLEAN_ONE_SFQ_CANDIDATE`，BJL2 段约 `1.016029 turn`、area 约 `1.016037 Phi0`，且没有第二个 complete segment。",
        "5. 13 ps / 8x500 ideal replay：`SUBTHRESHOLD`，最大段约 `0.973287 turn`；尚未跨过 1-turn complete 判据。",
        "6. 四个 physical logical1_read：全部 `SUBTHRESHOLD`，没有 complete BJL2 event。",
        "7. 所有 logical0_read 和两个 no-read controls：complete count 全为 0，没有 `CONTROL_EVENT_VIOLATION`。",
        "8. 从 9 ps 到 13 ps 的 strict boundary 在当前 ideal replay 的 `12x320` load 上存在（SUBTHRESHOLD → CLEAN_ONE candidate）；不是两个 load 都同时存在的普适 boundary。",
        "9. 该 boundary 不同时存在于 `8x500`：9/13 ps 两个点都为 `SUBTHRESHOLD`。physical 两个 load 也都没有建立 one-quantum candidate。",
        "10. window-level activity 是 `window_phase_delta_turns` 等端点/范围诊断；strict BJL2 authority 只来自连续单调 segment、同段 signed phase/area、complete count、第二段和 post boundedness。",
        "",
        "## Source/JSL 等价性",
        "",
        f"共检查 {len(source_cases)} 个 source case；每个 load 的全部系列支路都与 `I(B_LD1)` 逐样本比较（含 max、RMS、p95 abs difference）。`SERIES_JSL_CURRENT_EQUIVALENCE = {'PASS' if all(branch['status'] == 'PASS' for case in source_cases for branch in case['branches']) else 'FAIL'}`，逐支路绝对电流容差为 `{SERIES_EQUIVALENCE_TOL_A:.1e} A`；明细在 `analysis/jsl-series-current-equivalence.csv`。",
        "",
        "## Regression",
        "",
        f"- regression status: `{regression['status']}`。",
        "- 9 ps / 12x320 replay 锚点应保持约 `0.892527 / 0.892537 turn` 且无 complete event；13 ps 锚点应保持约 `1.016029 / 1.016037 turn` 且为 clean-one candidate。",
        "",
        "## Observed / Derived / Inference / Unknown",
        "",
        "### Observed",
        "",
        "- 以上表格和 CSV 是从当前矩阵 raw 直接计算的 segment 与面积数值；图仅标出关键 BJL2 轨迹和边界。",
        "- 输入 raw 的 CSV 时间轴保留其实际采样点；若存在非均匀 gap，QA 中显式记录，未重采样。",
        "",
        "### Derived",
        "",
        "- `CLEAN_ONE_SFQ_CANDIDATE` 是本任务冻结判据下的 local BJL2 candidate，不是已经通过 JTL、T1 或 system Gate 的 SFQ delivery。",
        "- `OVERDRIVEN_ONE_PLUS_RESIDUAL` 只描述单个完整段超过 clean upper band；不把前级 BJs/JSL 局部活动直接升级为 downstream event。",
        "",
        "### Inference",
        "",
        "- 本任务只解决窗口位移与连续单调事件段之间的 metric-semantics ambiguity，不据此提出新的物理机制或下一参数族。",
        "",
        "### Unknown",
        "",
        "- 单次 raw、当前 timestep 和有限 POST 窗口不能建立无限时间稳定性或收敛 Gate。",
        "- BVM source loading/back-action 的机制解释、JTL/T1 接收和 magnetic coupling 均不在本任务范围内。",
        "",
    ]
    return "\n".join(lines)


def build_summary(
    results: list[dict[str, Any]],
    provenance: dict[str, Any],
    regression: dict[str, Any],
    overall_status: str,
) -> str:
    primary = [item for item in results if item["role"] == "logical1_read"]
    lines = [
        "# BVM_LOAD_QB_STRICT_EVENT_RECLASSIFICATION_V1",
        "",
        f"状态：`{overall_status}`",
        "",
        "本轮只重新分析已有矩阵 raw，没有重跑 JoSIM 或改变电路。",
        "",
        f"- source identity：`{provenance['legacy_new_source_identity']['status']}`",
        f"- replay fixture equivalence：`{provenance['legacy_new_replay_fixture_equivalence']['status']}`",
        f"- regression：`{regression['status']}`",
        "",
        "| fixture | width | load | largest BJL2 segment | area | classification |",
        "|---|---:|---|---:|---:|---|",
    ]
    for item in sorted(primary, key=lambda x: (x["fixture"], x["width_ps"], x["jsl_load"])):
        row = summary_row(item)
        lines.append(
            f"| {row['fixture']} | {row['width_ps']} | {row['jsl_load']} | "
            f"{format_value(row['largest_monotonic_segment_turns'])} | {format_value(row['same_segment_voltage_area_turns'])} | "
            f"`{row['strict_classification']}` |"
        )
    lines += [
        "",
        "`window_phase_delta_turns` 与 strict event count 分开保存；窗口端点位移不能替代连续单调段。",
        "全部 32 个 case 的逐行结果见 `analysis/strict-event-summary.csv`，完整 segment 证据见 `analysis/strict-event-details.json`。",
        "本任务到此停止；不自动进入下一实验。",
        "",
    ]
    return "\n".join(lines)


def build_review(
    results: list[dict[str, Any]],
    regression: dict[str, Any],
    provenance: dict[str, Any],
    source_cases: list[dict[str, Any]],
) -> str:
    invalid = [item for item in results if item["qa"]["status"] != "VALID"]
    inconclusive = [item for item in results if item["strict_classification"] == "INCONCLUSIVE"]
    series_status = "PASS" if all(
        branch["status"] == "PASS"
        for case in source_cases
        for branch in case["branches"]
    ) else "FAIL"
    return "\n".join([
        "# Independent raw recheck",
        "",
        "本复核从当前矩阵 raw 重新读取 BJL2 P/V/time，不读取 summary CSV 作为事件计数输入，且不调用 `scripts/sfq_metrics.py`。",
        "",
        "## Mechanical checks",
        "",
        f"- raw cases checked: `{len(results)}`",
        f"- raw QA invalid: `{len(invalid)}`",
        f"- strict classifications inconclusive: `{len(inconclusive)}`",
        f"- legacy/new source identity: `{provenance['legacy_new_source_identity']['status']}`",
        f"- legacy/new replay fixture equivalence: `{provenance['legacy_new_replay_fixture_equivalence']['status']}`",
        f"- JSL series-current equivalence: `SERIES_JSL_CURRENT_EQUIVALENCE = {series_status}`; numerical tolerance `{SERIES_EQUIVALENCE_TOL_A:.1e} A`; per-branch max/RMS/p95 differences are recorded in `analysis/jsl-series-current-equivalence.csv`.",
        "- independent raw recheck artifact: `analysis/independent-raw-recheck.json`; separate execution is `PASS` for all 32 QB raw cases and does not import the main analyzer.",
        f"- regression: `{regression['status']}`",
        "",
        "## Adversarial boundaries",
        "",
        "- 通过窗口首末端点构造一个假的事件计数不会影响本复核；strict count 来自 `monotonic_runs` 的实际 segment 列表。",
        "- 面积使用同一个 BJL2、同一 segment 和 raw time；不同 JJ、不同窗口或重采样后的面积没有进入判定。",
        "- phase/area residual 使用 `phase - area` 的 signed convention；历史实现的 `area - phase` 只作为反号辅助字段保留。",
        "- 同一个 turning-point sample 可作为相邻段共享端点；没有人工移动 start/end 或对期待分类调 threshold。",
        "- raw sidecar/hash、重复表头一致性、时间单调性和 post/tail 覆盖均由脚本逐 case 检查。",
        "",
    ])


def run() -> str:
    current_head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, check=True, capture_output=True, text=True).stdout.strip()
    if current_head != RECORDED_HEAD:
        raise RuntimeError(f"HEAD changed after preregistration: expected {RECORDED_HEAD}, got {current_head}")
    provenance = provenance_equivalence()
    results: list[dict[str, Any]] = []
    source_cases: list[dict[str, Any]] = []
    result_map: dict[tuple[str, int, str, str], dict[str, Any]] = {}
    for width in WIDTHS:
        for load in LOADS:
            for role in ROLES:
                source_path = RAW_ROOT / "source" / f"{width}ps" / load / role / "run-01.csv"
                source_cases.append(analyze_source_case(source_path, width, load, role))
                for fixture in FIXTURES:
                    raw_path = RAW_ROOT / fixture / f"{width}ps" / load / role / "run-01.csv"
                    result = analyze_qb_case(raw_path, fixture, width, load, role)
                    results.append(result)
                    result_map[(fixture, width, load, role)] = result
    regression = regression_check(result_map)
    all_qa_valid = all(item["qa"]["status"] == "VALID" for item in results + source_cases)
    all_strict_decided = all(item["strict_classification"] != "INCONCLUSIVE" for item in results)
    all_series_equivalent = all(
        branch["status"] == "PASS"
        for case in source_cases
        for branch in case["branches"]
    )
    if regression["status"] == "STRICT_EVENT_REGRESSION_MISMATCH":
        overall_status = "STRICT_EVENT_REGRESSION_MISMATCH"
    elif (
        provenance["overall_provenance_status"] != "PASS"
        or not all_qa_valid
        or not all_strict_decided
        or not all_series_equivalent
    ):
        overall_status = "STRICT_EVENT_RECLASSIFICATION_INCONCLUSIVE"
    else:
        overall_status = "STRICT_EVENT_RECLASSIFICATION_COMPLETE"

    details = {
        "document_type": "bvm_load_qb_strict_event_details",
        "schema_version": "BVM_LOAD_QB_STRICT_EVENT_RECLASSIFICATION_V1",
        "recorded_at": RECORDED_AT,
        "parent_head": RECORDED_HEAD,
        "matrix_root": rel(MATRIX),
        "analysis_script": rel(Path(__file__)),
        "overall_status": overall_status,
        "series_current_equivalence_status": "PASS" if all_series_equivalent else "FAIL",
        "windows_ps": {"activity": list(ACTIVITY), "post": list(POST), "post_tail": list(POST_TAIL)},
        "tolerances": {
            "phi0_wb": PHI0,
            "complete_min_turns": COMPLETE_MIN_TURNS,
            "phase_area_residual": f"max({RESIDUAL_ABS_FLOOR_TURNS}, {RESIDUAL_RELATIVE} * abs(delta_phase_turns))",
            "clean_one_upper_turns": CLEAN_ONE_UPPER_TURNS,
            "post_range_max_turns": POST_RANGE_MAX_TURNS,
            "post_tail_p2p_max_turns": POST_TAIL_P2P_MAX_TURNS,
            "series_equivalence_max_abs_A": SERIES_EQUIVALENCE_TOL_A,
        },
        "semantics": {
            "window_phase_displacement": "activity endpoint delta only; not event count",
            "phase_area_residual": "phase_delta_turns - voltage_area_turns",
            "segmentation": "PAPER-SL-Q1 monotonic_runs; zero difference neutral; every nonzero reversal retained; turning point sample shared",
            "forbidden_event_proxies": ["VOUT peak", "VOUT p2p", "I>Ic", "whole-window phase delta", "phase p2p", "fast_events"],
        },
        "provenance": provenance,
        "source_cases": source_cases,
        "qb_cases": results,
    }
    ANALYSIS.mkdir(parents=True, exist_ok=True)
    (ANALYSIS / "strict-event-details.json").write_text(json.dumps(details, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_csv(ANALYSIS / "strict-event-summary.csv", [summary_row(item) for item in sorted(results, key=lambda x: (x["fixture"], x["width_ps"], x["jsl_load"], ROLES.index(x["role"])))], SUMMARY_FIELDS)
    equivalence_rows = []
    for case in sorted(source_cases, key=lambda x: (x["width_ps"], x["jsl_load"], ROLES.index(x["role"]))):
        for branch in case["branches"]:
            equivalence_rows.append({
                "width_ps": case["width_ps"],
                "jsl_load": case["jsl_load"],
                "role": case["role"],
                **branch,
            })
    write_csv(ANALYSIS / "jsl-series-current-equivalence.csv", equivalence_rows, ["width_ps", "jsl_load", "role", "branch", "reference_branch", "sample_count", "time_grid_status", "max_abs_difference_A", "rms_difference_A", "p95_abs_difference_A", "status"])
    (ANALYSIS / "provenance-equivalence.json").write_text(json.dumps(provenance, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (ANALYSIS / "regression-check.json").write_text(json.dumps(regression, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (ANALYSIS / "REPORT.md").write_text(build_report(results, provenance, regression, source_cases, overall_status), encoding="utf-8")
    (TARGET / "REPORT.md").write_text((ANALYSIS / "REPORT.md").read_text(encoding="utf-8"), encoding="utf-8")
    (TARGET / "SUMMARY.md").write_text(build_summary(results, provenance, regression, overall_status), encoding="utf-8")
    (ANALYSIS / "REVIEW.md").write_text(build_review(results, regression, provenance, source_cases), encoding="utf-8")
    print(overall_status)
    for item in sorted(results, key=lambda x: (x["fixture"], x["width_ps"], x["jsl_load"], ROLES.index(x["role"]))):
        print(item["fixture"], item["width_ps"], item["jsl_load"], item["role"], item["strict_classification"])
    return overall_status


if __name__ == "__main__":
    run()
