#!/usr/bin/env python3
"""Evidence-first internal-trajectory audit for frozen QB references.

This script reads existing raw CSVs and existing netlist/provenance files only.
It never invokes JoSIM and never writes into any reference Exploration.  The
outputs are derived evidence; the registered raw files, netlists, and the r5
preregistration remain the authority.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np


TARGET = Path(__file__).resolve().parents[1]
REPO = TARGET.parents[2]
ANALYSIS = TARGET / "analysis"
PLOTS = TARGET / "plots"
PLOT_INPUTS = ANALYSIS / "plot_inputs"

PHI0 = 2.067833848e-15
TWO_PI = 2.0 * math.pi
PRE = (80.0, 94.0)
ACTIVE = (94.0, 130.0)
TRANSITION = (130.0, 140.0)
POST = (140.0, 170.0)
Q0_PULSE_STARTS = (10.0, 60.0, 110.0, 160.0, 210.0, 260.0)
DIVERGENCE_TIE_PS = 0.0125
ABS_TOL = 1.0e-12
REL_TOL = 1.0e-6
ROLES = ("logical1_read", "logical0_read", "logical1_no_read_control", "logical0_no_read_control")


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO.resolve()).as_posix()


def sha256(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class Table:
    def __init__(self, path: Path, header: list[str], rows: list[list[str]]):
        self.path = path
        self.header = header
        self.rows = rows
        self._columns = {
            index: np.asarray([float(row[index]) for row in rows], dtype=np.float64)
            for index in range(len(header))
        }
        if self.indices("time"):
            self.time_s = self.column("time")[0]
            self.time_ps = self.time_s * np.float64(1.0e12)
        elif self.indices("time_ps"):
            self.time_ps = self.column("time_ps")[0]
            self.time_s = self.time_ps * np.float64(1.0e-12)
        else:
            raise ValueError(f"missing time/time_ps column: {path}")
        if self.time_ps.size < 2 or not np.all(np.isfinite(self.time_ps)):
            raise ValueError(f"invalid time axis: {path}")
        if not np.all(np.diff(self.time_ps) > 0):
            raise ValueError(f"time is not strictly increasing: {path}")
        if not all(np.all(np.isfinite(values)) for values in self._columns.values()):
            raise ValueError(f"NaN/Inf in {path}")

    def indices(self, name: str) -> list[int]:
        target = normalize(name)
        return [index for index, header in enumerate(self.header) if normalize(header) == target]

    def column(self, name: str, occurrence: int = 0) -> tuple[np.ndarray, int]:
        indices = self.indices(name)
        if len(indices) <= occurrence:
            raise KeyError(f"missing {name!r} in {self.path}; header={self.header}")
        index = indices[occurrence]
        return self._columns[index], index

    def by_index(self, index: int) -> np.ndarray:
        return self._columns[index]


def normalize(name: str) -> str:
    return name.strip().strip('"').replace(" ", "").lower()


def load_table(path: Path) -> Table:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        header = next(reader)
        rows = [row for row in reader if row]
    if not rows:
        raise ValueError(f"empty CSV: {path}")
    if any(len(row) != len(header) for row in rows):
        raise ValueError(f"ragged CSV: {path}")
    return Table(path, header, rows)


def mask(time_ps: np.ndarray, bounds: tuple[float, float]) -> np.ndarray:
    return (time_ps >= bounds[0]) & (time_ps < bounds[1])


def integrate(time_ps: np.ndarray, values: np.ndarray) -> float:
    if time_ps.size < 2:
        return 0.0
    seconds = time_ps * 1.0e-12
    area = np.trapezoid(values, seconds) if hasattr(np, "trapezoid") else np.trapz(values, seconds)
    return float(area)


def mad(values: np.ndarray) -> float:
    median = float(np.median(values))
    return float(np.median(np.abs(values - median)))


def p2p(values: np.ndarray) -> float:
    return float(np.max(values) - np.min(values)) if values.size else 0.0


def longest_true(values: np.ndarray) -> int:
    longest = current = 0
    for value in values:
        if bool(value):
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return longest


def json_float(value: float | np.floating[Any]) -> float | None:
    number = float(value)
    return number if math.isfinite(number) else None


def stats(values: np.ndarray, time_ps: np.ndarray, bounds: tuple[float, float], baseline: float | None = None) -> dict[str, Any]:
    selected = mask(time_ps, bounds)
    data = values[selected]
    if data.size == 0:
        return {"n": 0}
    base = float(np.median(values[mask(time_ps, PRE)])) if baseline is None else float(baseline)
    return {
        "n": int(data.size),
        "min": json_float(np.min(data)),
        "max": json_float(np.max(data)),
        "median": json_float(np.median(data)),
        "mean": json_float(np.mean(data)),
        "p2p": json_float(p2p(data)),
        "signed_integral": json_float(integrate(time_ps[selected], data)),
        "dynamic_integral": json_float(integrate(time_ps[selected], data - base)),
        "baseline_median": json_float(base),
    }


def sign_runs(values: np.ndarray) -> list[tuple[int, int]]:
    if values.size < 2:
        return []
    signs = np.sign(np.diff(values))
    nonzero = np.flatnonzero(signs != 0)
    if nonzero.size == 0:
        return []
    runs: list[tuple[int, int]] = []
    start = 0
    current = int(signs[nonzero[0]])
    for position in nonzero[1:]:
        sign = int(signs[position])
        if sign != current:
            runs.append((start, int(position)))
            start = int(position)
            current = sign
    runs.append((start, values.size - 1))
    return [(left, right) for left, right in runs if right > left]


def phase_segments(table: Table, phase_name: str, voltage_name: str, bounds: tuple[float, float]) -> list[dict[str, Any]]:
    phase, _ = table.column(phase_name)
    voltage, _ = table.column(voltage_name)
    phase = np.unwrap(phase)
    selected = np.flatnonzero(mask(table.time_ps, bounds))
    if selected.size < 2:
        return []
    records: list[dict[str, Any]] = []
    for left, right in sign_runs(phase[selected]):
        indices = selected[left : right + 1]
        delta_turns = float((phase[indices[-1]] - phase[indices[0]]) / TWO_PI)
        area_turns = float(integrate(table.time_ps[indices], voltage[indices]) / PHI0)
        residual = float(area_turns - delta_turns)
        tolerance = max(0.05, 0.10 * abs(delta_turns))
        area_consistent = bool(
            abs(delta_turns) >= 1.0
            and abs(area_turns) > 1.0e-12
            and delta_turns * area_turns > 0
            and abs(residual) <= tolerance
        )
        records.append({
            "start_ps": json_float(table.time_ps[indices[0]]),
            "end_ps": json_float(table.time_ps[indices[-1]]),
            "delta_turns": json_float(delta_turns),
            "area_phi0": json_float(area_turns),
            "residual_turns": json_float(residual),
            "area_tolerance_turns": json_float(tolerance),
            "phase_candidate": bool(abs(delta_turns) >= 1.0),
            "area_consistent": area_consistent,
        })
    return records


def phase_record(table: Table, prefix: str, role: str) -> dict[str, Any]:
    phase_name = f"P({prefix}|XBQ)"
    voltage_name = f"V({prefix}|XBQ)"
    current_name = f"I({prefix}|XBQ)"
    phase, _ = table.column(phase_name)
    current, _ = table.column(current_name)
    phase = np.unwrap(phase)
    pre = phase[mask(table.time_ps, PRE)]
    active = phase[mask(table.time_ps, ACTIVE)]
    transition = phase[mask(table.time_ps, TRANSITION)]
    post = phase[mask(table.time_ps, POST)]
    active_segments = phase_segments(table, phase_name, voltage_name, ACTIVE)
    transition_segments = phase_segments(table, phase_name, voltage_name, TRANSITION)
    post_segments = phase_segments(table, phase_name, voltage_name, POST)
    all_active = active_segments + transition_segments
    qualifying = [item for item in all_active if item["area_consistent"]]
    return {
        "role": role,
        "phase_unit": "raw radians; reported relative turns are rad/(2pi)",
        "pre_median_rad": json_float(np.median(pre)),
        "pre_mad_rad": json_float(mad(pre)),
        "active_relative_p2p_turns": json_float(p2p(active - np.median(pre)) / TWO_PI),
        "transition_relative_p2p_turns": json_float(p2p(transition - np.median(pre)) / TWO_PI),
        "post_relative_p2p_turns": json_float(p2p(post - np.median(pre)) / TWO_PI),
        "active_segments": active_segments,
        "transition_segments": transition_segments,
        "post_segments": post_segments,
        "qualifying_phase_area_candidates": len(qualifying),
        "post_qualifying_candidates": sum(1 for item in post_segments if item["area_consistent"]),
        "largest_active_segment": max(all_active, key=lambda item: abs(float(item["delta_turns"]))) if all_active else None,
        "current_active_uA": {
            "min": json_float(np.min(current[mask(table.time_ps, ACTIVE)]) * 1.0e6),
            "max": json_float(np.max(current[mask(table.time_ps, ACTIVE)]) * 1.0e6),
        },
    }


def phase_or_current_features(table: Table, source_kind: str) -> dict[str, np.ndarray]:
    result: dict[str, np.ndarray] = {}
    source_name = "I(I_REPLAY)" if source_kind == "ideal" else ("I(B_LD12)" if source_kind == "d12" else "I(B_LD8)")
    result["input_source_current_A"] = table.column(source_name)[0]
    result["input_lin_current_A"] = table.column("I(LIN|XBQ)")[0]
    result["input_voltage_V"] = table.column("V(IN)")[0]
    for prefix in ("BJs", "BJL1", "BJL2"):
        phase = np.unwrap(table.column(f"P({prefix}|XBQ)")[0]) / TWO_PI
        result[f"phase_{prefix}_relative_turns"] = phase - float(np.median(phase[mask(table.time_ps, PRE)]))
        result[f"sin_{prefix}"] = np.sin(phase * TWO_PI)
        result[f"cos_{prefix}"] = np.cos(phase * TWO_PI)
        result[f"current_{prefix}_A"] = table.column(f"I({prefix}|XBQ)")[0]
        result[f"voltage_{prefix}_V"] = table.column(f"V({prefix}|XBQ)")[0]
    for name in ("I(L0|XBQ)", "I(L1|XBQ)", "I(L2|XBQ)", "I(RB|XBQ)", "I(RJ1|XBQ)", "I(RJ2|XBQ)"):
        result[f"branch_{name}"] = table.column(name)[0]
    result["output_voltage_V"] = table.column("V(OUT)")[0]
    return result


def kcl_terms(table: Table, source_kind: str) -> dict[str, tuple[np.ndarray, np.ndarray, list[np.ndarray]]]:
    features = phase_or_current_features(table, source_kind)
    return {
        "input": (
            features["input_source_current_A"],
            features["input_lin_current_A"],
            [features["input_source_current_A"], features["input_lin_current_A"]],
        ),
        "node2": (
            features["current_BJs_A"],
            features["branch_I(L1|XBQ)"] + features["current_BJL1_A"] + features["branch_I(RJ1|XBQ)"],
            [features["current_BJs_A"], features["branch_I(L1|XBQ)"], features["current_BJL1_A"], features["branch_I(RJ1|XBQ)"]],
        ),
        "node3": (
            features["branch_I(L1|XBQ)"] + features["branch_I(RB|XBQ)"],
            features["branch_I(L2|XBQ)"],
            [features["branch_I(L1|XBQ)"], features["branch_I(RB|XBQ)"], features["branch_I(L2|XBQ)"]],
        ),
        "node4": (
            features["branch_I(L2|XBQ)"],
            features["branch_I(L0|XBQ)"] + features["current_BJL2_A"] + features["branch_I(RJ2|XBQ)"],
            [features["branch_I(L2|XBQ)"], features["branch_I(L0|XBQ)"], features["current_BJL2_A"], features["branch_I(RJ2|XBQ)"]],
        ),
    }


def gate_metrics(left: np.ndarray, right: np.ndarray, time_ps: np.ndarray, bounds: tuple[float, float], bound_terms: list[np.ndarray] | None = None) -> dict[str, Any]:
    selected = mask(time_ps, bounds)
    a = left[selected]
    b = right[selected]
    residual = a - b
    if bound_terms is None:
        bound_terms = [left, right]
    bound = ABS_TOL + REL_TOL * sum(np.abs(term[selected]) for term in bound_terms)
    ratio = np.abs(residual) / bound
    return {
        "n": int(residual.size),
        "max_abs_A": json_float(np.max(np.abs(residual))),
        "p95_abs_A": json_float(np.percentile(np.abs(residual), 95)),
        "max_ratio": json_float(np.max(ratio)),
        "p95_ratio": json_float(np.percentile(ratio, 95)),
        "samples_over_bound": int(np.count_nonzero(ratio > 1.0)),
        "longest_consecutive_over_bound": int(longest_true(ratio > 1.0)),
        "passed": bool(np.max(ratio) <= 1.0 and np.percentile(ratio, 95) <= 1.0 and longest_true(ratio > 1.0) < 3),
    }


def orientation_and_kcl(table: Table, source_kind: str) -> dict[str, Any]:
    terms = kcl_terms(table, source_kind)
    output: dict[str, Any] = {"bound": {"abs_tol_A": ABS_TOL, "rel_tol": REL_TOL}, "windows": {}, "status": "ORIENTATION_KCL_PASS"}
    for window_name, bounds in (("PRE", PRE), ("ACTIVE", ACTIVE), ("TRANSITION", TRANSITION), ("POST", POST)):
        window: dict[str, Any] = {}
        for equation, (left, right, all_terms) in terms.items():
            expected = gate_metrics(left, right, table.time_ps, bounds, all_terms)
            window[equation] = {"expected": expected}
            if equation == "input":
                opposite = gate_metrics(left, -right, table.time_ps, bounds, [left, -right])
                window[equation]["opposite_sign"] = opposite
                if not expected["passed"] and opposite["passed"]:
                    output["status"] = "PORT_SIGN_ORIENTATION_ERROR"
                elif not expected["passed"]:
                    output["status"] = "ORIENTATION_KCL_INCONCLUSIVE"
            elif not expected["passed"] and output["status"] == "ORIENTATION_KCL_PASS":
                output["status"] = "ORIENTATION_KCL_INCONCLUSIVE"
        output["windows"][window_name] = window
    return output


def load_all_specs() -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    exp = REPO / "test/exploration"
    c13_root = exp / "bvm-read-semantics-audit-and-jsl-width-bracket-v1-20260824"
    d12_root = exp / "physical-bvm-jsl12-qb-sfq-closure-v1-20260824"
    e8_root = exp / "bvm-jsl8-500-physical-qb-recheck-v1-20260824"
    q0_root = exp / "qb-q0-standalone-current-quantized-event-20260824"
    source_root = exp / "paper-sl-l0-20260824"
    source_raw_root = c13_root / "raw/13ps"
    c13_sources = {
        "logical1_read": source_raw_root / "logical1-read/run-01.csv",
        "logical0_read": source_raw_root / "logical0-read/run-01.csv",
        "logical1_no_read_control": source_root / "raw/logical1-read0-control/run-01.csv",
        "logical0_no_read_control": source_root / "raw/logical0-read0-control/run-01.csv",
    }
    c13 = {
        role: {
            "raw": c13_root / f"raw/replay/13ps/{role}/run-01.csv",
            "source_raw": source,
            "snapshot": c13_root / f"reference/replay_sources/13ps-{role}.csv",
            "deck": c13_root / f"inputs/replay/13ps/{role}.cir",
        }
        for role, source in c13_sources.items()
    }
    d12 = {
        role: {"raw": d12_root / f"raw/13/{role}/run-01.csv", "deck": d12_root / f"inputs/13/{role}.cir"}
        for role in ROLES
    }
    e8 = {
        role: {"raw": e8_root / f"raw/13/{role}/run-01.csv", "deck": e8_root / f"inputs/13/{role}.cir"}
        for role in ROLES
    }
    q0 = {
        "45u": q0_root / "raw/scaled/iin-45u.csv",
        "68p4u": q0_root / "raw/scaled/iin-68p4u.csv",
    }
    return c13, d12, e8, q0


def file_record(path: Path, csv_quality: bool = False) -> dict[str, Any]:
    record: dict[str, Any] = {"path": rel(path), "exists": path.exists(), "bytes": path.stat().st_size if path.exists() else None, "sha256": sha256(path)}
    if not path.exists() or not csv_quality:
        return record
    raw = path.read_bytes()
    first_line = raw.splitlines(keepends=True)[0] if raw else b""
    record["header_sha256"] = hashlib.sha256(first_line).hexdigest()
    record["line_count"] = raw.count(b"\n")
    try:
        table = load_table(path)
        dt = np.diff(table.time_ps)
        record.update({
            "columns": len(table.header),
            "rows": len(table.rows),
            "header": table.header,
            "time_start_ps": json_float(table.time_ps[0]),
            "time_end_ps": json_float(table.time_ps[-1]),
            "dt_min_ps": json_float(np.min(dt)),
            "dt_max_ps": json_float(np.max(dt)),
            "finite": True,
            "strictly_increasing": True,
        })
    except Exception as exc:  # pragma: no cover - recorded as artifact evidence
        record.update({"finite": False, "strictly_increasing": False, "error": str(exc)})
    return record


def declared_sha(manifest: Path, key: str) -> str | None:
    if not manifest.exists():
        return None
    text = manifest.read_text(encoding="utf-8")
    quoted = re.escape(key)
    patterns = [
        rf'"{quoted}"\s*:\s*\{{.*?"sha256"\s*:\s*"([0-9a-f]{{64}})"',
        rf'"{quoted}"\s*:\s*"([0-9a-f]{{64}})"',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.S)
        if match:
            return match.group(1)
    return None


def source_chain(c13: dict[str, dict[str, Any]]) -> dict[str, Any]:
    output: dict[str, Any] = {
        "historical_selected_source_column": {"index": 14, "header": "I(B_LD1)", "selection": "header.index(\"I(B_LD1\")"},
        "direct_final_jsl_diagnostic_column": {"index": 51, "header": "I(B_LD12)"},
        "snapshot_schema": ["time_ps", "I_JSL_A"],
        "snapshot_has_voltage": False,
        "roles": {},
    }
    for role, spec in c13.items():
        source = load_table(spec["source_raw"])
        snapshot = load_table(spec["snapshot"])
        raw_time = source.time_s * np.float64(1.0e12)
        source_current = source.by_index(14)
        snapshot_time = snapshot.column("time_ps")[0]
        snapshot_current = snapshot.column("I_JSL_A")[0]
        same_time = bool(np.array_equal(raw_time, snapshot_time))
        same_current = bool(np.array_equal(source_current, snapshot_current))
        duplicate_14_18 = bool(np.array_equal(source.by_index(14), source.by_index(18)))
        duplicate_15_51 = bool(np.array_equal(source.by_index(15), source.by_index(51)))
        deck_text = spec["deck"].read_text(encoding="utf-8")
        match = re.search(r"I_REPLAY\s+0\s+IN\s+pwl\((.*?)\)", deck_text, re.S)
        deck_pairs: list[tuple[float, float]] = []
        if match:
            tokens = match.group(1).replace("+", " ").split()
            if len(tokens) % 2 == 0:
                for index in range(0, len(tokens), 2):
                    time_token = tokens[index]
                    deck_pairs.append((float(time_token[:-1]), float(tokens[index + 1])))
        deck_array = np.asarray(deck_pairs, dtype=np.float64)
        snapshot_array = np.column_stack((snapshot_time, snapshot_current))
        same_deck = bool(deck_array.shape == snapshot_array.shape and np.array_equal(deck_array, snapshot_array))
        output["roles"][role] = {
            "source_raw": rel(spec["source_raw"]),
            "source_sha256": sha256(spec["source_raw"]),
            "snapshot": rel(spec["snapshot"]),
            "snapshot_sha256": sha256(spec["snapshot"]),
            "deck": rel(spec["deck"]),
            "deck_sha256": sha256(spec["deck"]),
            "source_header_indices": {"I(B_LD1)": [14, 18], "I(B_LD12)": [15, 51]},
            "source_rows": len(source.rows),
            "snapshot_rows": len(snapshot.rows),
            "deck_pwl_rows": int(deck_array.shape[0]),
            "time_source_s_to_snapshot_ps_exact_float64": same_time,
            "selected_index14_to_snapshot_current_exact_float64": same_current,
            "snapshot_to_deck_pwl_exact_float64": same_deck,
            "duplicate_index14_18_exact_float64": duplicate_14_18,
            "duplicate_index15_51_exact_float64": duplicate_15_51,
            "status": "HISTORICAL_REPLAY_SOURCE_CHAIN_CLOSED" if all((same_time, same_current, same_deck, duplicate_14_18, duplicate_15_51)) else "INVALID",
            "final_jsl_source_semantics": "INCONCLUSIVE",
        }
    output["all_roles_closed"] = all(role["status"] == "HISTORICAL_REPLAY_SOURCE_CHAIN_CLOSED" for role in output["roles"].values())
    output["final_jsl_source_semantics"] = "INCONCLUSIVE"
    return output


def case_signal_map(source_kind: str) -> dict[str, str]:
    source_name = "I(I_REPLAY)" if source_kind == "ideal" else ("I(B_LD12)" if source_kind == "d12" else "I(B_LD8)")
    return {
        "source": source_name,
        "lin": "I(LIN|XBQ)",
        "vin": "V(IN)",
        "vout": "V(OUT)",
        "bjs_p": "P(BJs|XBQ)",
        "bjs_v": "V(BJs|XBQ)",
        "bjs_i": "I(BJs|XBQ)",
        "bjl1_p": "P(BJL1|XBQ)",
        "bjl1_v": "V(BJL1|XBQ)",
        "bjl1_i": "I(BJL1|XBQ)",
        "bjl2_p": "P(BJL2|XBQ)",
        "bjl2_v": "V(BJL2|XBQ)",
        "bjl2_i": "I(BJL2|XBQ)",
        "l0": "I(L0|XBQ)",
        "l1": "I(L1|XBQ)",
        "l2": "I(L2|XBQ)",
        "rb": "I(RB|XBQ)",
        "rj1": "I(RJ1|XBQ)",
        "rj2": "I(RJ2|XBQ)",
    }


def load_case_records(c13: dict[str, dict[str, Any]], d12: dict[str, dict[str, Any]], e8: dict[str, dict[str, Any]]) -> tuple[dict[str, Table], dict[str, str]]:
    tables: dict[str, Table] = {}
    kinds: dict[str, str] = {}
    for prefix, specs, kind in (("C13", c13, "ideal"), ("D12", d12, "d12"), ("E8", e8, "e8")):
        for role, spec in specs.items():
            key = f"{prefix}.{role}"
            tables[key] = load_table(spec["raw"])
            kinds[key] = kind
    return tables, kinds


def case_trajectory(key: str, table: Table, source_kind: str, role: str) -> dict[str, Any]:
    signal_map = case_signal_map(source_kind)
    phase = {name: phase_record(table, prefix, role) for name, prefix in (("BJs", "BJs"), ("BJL1", "BJL1"), ("BJL2", "BJL2"))}
    current_stats = {}
    for label, signal in (("source", signal_map["source"]), ("lin", signal_map["lin"]), ("bjs", signal_map["bjs_i"]), ("bjl1", signal_map["bjl1_i"]), ("bjl2", signal_map["bjl2_i"]), ("l0", signal_map["l0"]), ("l1", signal_map["l1"]), ("l2", signal_map["l2"]), ("rb", signal_map["rb"]), ("rj1", signal_map["rj1"]), ("rj2", signal_map["rj2"])):
        values = table.column(signal)[0]
        current_stats[label] = {window: stats(values, table.time_ps, bounds) for window, bounds in (("PRE", PRE), ("ACTIVE", ACTIVE), ("TRANSITION", TRANSITION), ("POST", POST))}
    return {
        "key": key,
        "role": role,
        "source_kind": source_kind,
        "path": rel(table.path),
        "rows": len(table.rows),
        "time_start_ps": json_float(table.time_ps[0]),
        "time_end_ps": json_float(table.time_ps[-1]),
        "dt_min_ps": json_float(np.min(np.diff(table.time_ps))),
        "dt_max_ps": json_float(np.max(np.diff(table.time_ps))),
        "orientation_kcl": orientation_and_kcl(table, source_kind),
        "phase": phase,
        "current_stats": current_stats,
    }


PRE_FEATURES = (
    "input_source_current_A", "input_lin_current_A", "input_voltage_V",
    "phase_BJs_relative_turns", "sin_BJs", "cos_BJs", "current_BJs_A", "voltage_BJs_V",
    "phase_BJL1_relative_turns", "sin_BJL1", "cos_BJL1", "current_BJL1_A", "voltage_BJL1_V",
    "phase_BJL2_relative_turns", "sin_BJL2", "cos_BJL2", "current_BJL2_A", "voltage_BJL2_V",
    "branch_I(L0|XBQ)", "branch_I(L1|XBQ)", "branch_I(L2|XBQ)", "branch_I(RB|XBQ)",
    "branch_I(RJ1|XBQ)", "branch_I(RJ2|XBQ)", "output_voltage_V",
)


def pre_feature_table(table: Table, source_kind: str) -> dict[str, np.ndarray]:
    return phase_or_current_features(table, source_kind)


def pre_compare(a: Table, a_kind: str, b: Table, b_kind: str, pair: str) -> dict[str, Any]:
    if not np.array_equal(a.time_ps, b.time_ps):
        return {"pair": pair, "status": "INCONCLUSIVE", "reason": "time grids differ; no interpolation allowed"}
    a_features = pre_feature_table(a, a_kind)
    b_features = pre_feature_table(b, b_kind)
    rows: list[dict[str, Any]] = []
    repartitioned = False
    inconclusive = False
    for feature in PRE_FEATURES:
        left = a_features[feature][mask(a.time_ps, PRE)]
        right = b_features[feature][mask(b.time_ps, PRE)]
        scale_a = max(1.4826 * mad(left), 1.0e-12 * max(1.0, float(np.max(np.abs(left)))))
        scale_b = max(1.4826 * mad(right), 1.0e-12 * max(1.0, float(np.max(np.abs(right)))))
        limit = 5.0 * math.sqrt(scale_a * scale_a + scale_b * scale_b)
        diff = np.abs(left - right)
        over = diff > limit
        row = {
            "pair": pair,
            "feature": feature,
            "unit": "turns" if "phase_" in feature else ("dimensionless" if feature.startswith(("sin_", "cos_")) else ("A" if "current" in feature or "branch_" in feature else "V")),
            "median_a": json_float(np.median(left)),
            "median_b": json_float(np.median(right)),
            "median_abs_difference": json_float(abs(float(np.median(left)) - float(np.median(right)))),
            "scale_a": json_float(scale_a),
            "scale_b": json_float(scale_b),
            "pair_limit": json_float(limit),
            "max_abs_difference": json_float(np.max(diff)),
            "samples_over_limit": int(np.count_nonzero(over)),
            "fraction_over_limit": json_float(np.mean(over)),
            "longest_consecutive_over_limit": int(longest_true(over)),
        }
        row["median_within_limit"] = bool(row["median_abs_difference"] <= row["pair_limit"])
        row["sustained_over_limit"] = bool(row["median_abs_difference"] > row["pair_limit"] and longest_true(over) >= 3)
        if row["sustained_over_limit"]:
            repartitioned = True
        elif not row["median_within_limit"]:
            inconclusive = True
        rows.append(row)
    status = "PRE_BIAS_REPARTITIONED" if repartitioned else ("INCONCLUSIVE" if inconclusive else "PRE_STATE_MATCHED")
    return {"pair": pair, "status": status, "features": rows}


DIV_FEATURES = (
    ("input_port", "source", "input_source_current_A"),
    ("input_port", "lin", "input_lin_current_A"),
    ("input_port", "vin", "input_voltage_V"),
    ("bjs_trajectory", "bjs_phase", "phase_BJs_relative_turns"),
    ("bjs_trajectory", "bjs_voltage", "voltage_BJs_V"),
    ("bjs_trajectory", "bjs_current", "current_BJs_A"),
    ("node2", "l1_current", "branch_I(L1|XBQ)"),
    ("node2", "bjl1_current", "current_BJL1_A"),
    ("node2", "rj1_current", "branch_I(RJ1|XBQ)"),
    ("node3", "rb_current", "branch_I(RB|XBQ)"),
    ("node3", "l2_current", "branch_I(L2|XBQ)"),
    ("node4", "l0_current", "branch_I(L0|XBQ)"),
    ("node4", "bjl2_current", "current_BJL2_A"),
    ("node4", "rj2_current", "branch_I(RJ2|XBQ)"),
    ("node4", "vout", "output_voltage_V"),
)


def first_run(masked: np.ndarray, minimum: int = 3) -> int | None:
    for index in range(0, masked.size - minimum + 1):
        if bool(np.all(masked[index : index + minimum])):
            return index
    return None


def divergence_pair(a: Table, a_kind: str, b: Table, b_kind: str, pair: str) -> dict[str, Any]:
    if not np.array_equal(a.time_ps, b.time_ps):
        return {"pair": pair, "status": "INCONCLUSIVE", "reason": "time grids differ; no interpolation allowed", "features": []}
    af = pre_feature_table(a, a_kind)
    bf = pre_feature_table(b, b_kind)
    rows: list[dict[str, Any]] = []
    for layer, feature, key in DIV_FEATURES:
        av = af[key]
        bv = bf[key]
        pre_a = av[mask(a.time_ps, PRE)]
        pre_b = bv[mask(b.time_ps, PRE)]
        med_a = float(np.median(pre_a))
        med_b = float(np.median(pre_b))
        scale_a = max(1.4826 * mad(pre_a), 1.0e-12 * max(1.0, float(np.max(np.abs(pre_a)))))
        scale_b = max(1.4826 * mad(pre_b), 1.0e-12 * max(1.0, float(np.max(np.abs(pre_b)))))
        threshold = 5.0 * math.sqrt(scale_a * scale_a + scale_b * scale_b)
        delta = np.abs((av - med_a) - (bv - med_b))
        pre_indices = np.flatnonzero(mask(a.time_ps, PRE))
        active_indices = np.flatnonzero(mask(a.time_ps, ACTIVE) | mask(a.time_ps, TRANSITION))
        pre_candidate = first_run(delta[pre_indices] > threshold)
        active_candidate = first_run(delta[active_indices] > threshold)
        pre_time = float(a.time_ps[pre_indices[pre_candidate]]) if pre_candidate is not None else None
        active_time = float(a.time_ps[active_indices[active_candidate]]) if active_candidate is not None else None
        first_time = pre_time if pre_time is not None else active_time
        first_scope = "PRE" if pre_time is not None else ("ACTIVE_OR_TRANSITION" if active_time is not None else None)
        rows.append({
            "pair": pair,
            "layer": layer,
            "feature": feature,
            "value_key": key,
            "unit": "turns" if "phase_" in key else ("A" if "current" in key or "branch_" in key else "V"),
            "scale_a": json_float(scale_a),
            "scale_b": json_float(scale_b),
            "threshold": json_float(threshold),
            "pre_median_a": json_float(med_a),
            "pre_median_b": json_float(med_b),
            "first_divergence_time_ps": json_float(first_time) if first_time is not None else None,
            "first_divergence_scope": first_scope,
            "sustained_samples": 3 if first_time is not None else 0,
        })
    valid = [row for row in rows if row["first_divergence_time_ps"] is not None]
    active_valid = [row for row in valid if row["first_divergence_scope"] == "ACTIVE_OR_TRANSITION"]
    earliest = min(active_valid, key=lambda row: float(row["first_divergence_time_ps"])) if active_valid else None
    layer_first: dict[str, dict[str, Any]] = {}
    for layer in ("input_port", "bjs_trajectory", "node2", "node3", "node4"):
        candidates = [row for row in active_valid if row["layer"] == layer]
        if candidates:
            layer_first[layer] = min(candidates, key=lambda row: float(row["first_divergence_time_ps"]))
    tie_layers = []
    if earliest is not None:
        earliest_time = float(earliest["first_divergence_time_ps"])
        tie_layers = [
            layer for layer, row in layer_first.items()
            if abs(float(row["first_divergence_time_ps"]) - earliest_time) <= DIVERGENCE_TIE_PS + 1.0e-12
        ]
    return {
        "pair": pair,
        "status": "DESCRIPTIVE_OR_PROVENANCE_INCONCLUSIVE" if pair.endswith("D12") else "ANALYZED",
        "features": rows,
        "earliest_active_or_transition": earliest,
        "layer_first": layer_first,
        "tie_tolerance_ps": DIVERGENCE_TIE_PS,
        "earliest_tie_layers": tie_layers,
        "earliest_layer_classification": "TIE" if len(tie_layers) > 1 else (tie_layers[0] if tie_layers else "NO_CREDIBLE_ACTIVE_DIVERGENCE"),
        "pre_divergence_present": any(row["first_divergence_scope"] == "PRE" for row in rows),
    }


def partition_rows(key: str, table: Table, source_kind: str, role: str) -> list[dict[str, Any]]:
    features = phase_or_current_features(table, source_kind)
    equations = kcl_terms(table, source_kind)
    signal_values = {
        "source": features["input_source_current_A"],
        "lin": features["input_lin_current_A"],
        "BJs": features["current_BJs_A"],
        "BJL1": features["current_BJL1_A"],
        "BJL2": features["current_BJL2_A"],
        "L0": features["branch_I(L0|XBQ)"],
        "L1": features["branch_I(L1|XBQ)"],
        "L2": features["branch_I(L2|XBQ)"],
        "RB": features["branch_I(RB|XBQ)"],
        "RJ1": features["branch_I(RJ1|XBQ)"],
        "RJ2": features["branch_I(RJ2|XBQ)"],
    }
    rows: list[dict[str, Any]] = []
    for window_name, bounds in (("PRE", PRE), ("ACTIVE", ACTIVE), ("TRANSITION", TRANSITION), ("POST", POST)):
        for signal, values in signal_values.items():
            record = stats(values, table.time_ps, bounds)
            rows.append({"case": key, "role": role, "window": window_name, "kind": "branch_current", "signal": signal, "unit": "A", **record})
        for equation, (left, right, all_terms) in equations.items():
            record = gate_metrics(left, right, table.time_ps, bounds, all_terms)
            rows.append({"case": key, "role": role, "window": window_name, "kind": "kcl_residual", "signal": equation, "unit": "A", **record})
    return rows


def q0_case(path: Path, label: str) -> dict[str, Any]:
    table = load_table(path)
    junctions: dict[str, list[dict[str, Any]]] = {"BJs": [], "BJL1": [], "BJL2": []}
    for start in Q0_PULSE_STARTS:
        windows = {
            "pre": (start - 10.0, start - 1.0),
            "activity": (start, start + 25.0),
            "post": (start + 25.0, min(start + 49.0, 300.0)),
        }
        for prefix in junctions:
            phase_name = f"P({prefix}|XBQ)"
            voltage_name = f"V({prefix}|XBQ)"
            current_name = f"I({prefix}|XBQ)"
            phase, _ = table.column(phase_name)
            current, _ = table.column(current_name)
            phase = np.unwrap(phase)
            active_records = phase_segments(table, phase_name, voltage_name, windows["activity"])
            post_records = phase_segments(table, phase_name, voltage_name, windows["post"])
            pre_values = phase[mask(table.time_ps, windows["pre"])]
            active_values = phase[mask(table.time_ps, windows["activity"])]
            post_values = phase[mask(table.time_ps, windows["post"])]
            junctions[prefix].append({
                "pulse_start_ps": start,
                "activity_window_ps": list(windows["activity"]),
                "pre_median_rad": json_float(np.median(pre_values)),
                "activity_relative_p2p_turns": json_float(p2p(active_values - np.median(pre_values)) / TWO_PI),
                "post_relative_p2p_turns": json_float(p2p(post_values - np.median(pre_values)) / TWO_PI),
                "active_segments": active_records,
                "post_segments": post_records,
                "current_activity_uA": {"min": json_float(np.min(current[mask(table.time_ps, windows["activity"])] ) * 1.0e6), "max": json_float(np.max(current[mask(table.time_ps, windows["activity"])] ) * 1.0e6)},
            })
    summary: dict[str, Any] = {"label": label, "path": rel(path), "dt_ps": json_float(np.min(np.diff(table.time_ps))), "junctions": junctions}
    for prefix, records in junctions.items():
        bjl2_candidates = [sum(1 for item in record["active_segments"] if item["area_consistent"]) for record in records]
        summary[prefix] = {
            "pulse_count": len(records),
            "candidate_counts": bjl2_candidates,
            "candidate_count_median": json_float(np.median(bjl2_candidates)),
            "activity_relative_p2p_turns_median": json_float(np.median([record["activity_relative_p2p_turns"] for record in records])),
            "activity_relative_p2p_turns_min": json_float(np.min([record["activity_relative_p2p_turns"] for record in records])),
            "activity_relative_p2p_turns_max": json_float(np.max([record["activity_relative_p2p_turns"] for record in records])),
        }
    bjl2_counts = summary["BJL2"]["candidate_counts"]
    if label == "45u" and all(count == 0 for count in bjl2_counts):
        summary["local_reference_classification"] = "TRAJECTORY_RESEMBLANCE_TO_SUBTHRESHOLD"
    elif label == "68p4u" and all(count == 1 for count in bjl2_counts):
        summary["local_reference_classification"] = "TRAJECTORY_RESEMBLANCE_TO_QUANTIZED"
    else:
        summary["local_reference_classification"] = "TRAJECTORY_RESEMBLANCE_MIXED_OR_INCONCLUSIVE"
    return summary


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, ensure_ascii=False, allow_nan=False)
        handle.write("\n")


def write_artifact_inventory(integrity: dict[str, Any], plot_records: list[dict[str, Any]], now: str) -> None:
    """Write a non-circular SHA-256 inventory for the complete audit bundle.

    ``artifact-inventory.json`` explicitly excludes itself.  All other paths
    are hashed from the same working tree that will be committed; the final
    checkpoint additionally verifies that every listed path is tracked and
    readable through ``git show HEAD:<path>``.
    """
    categories: dict[str, set[Path]] = {
        "raw_and_provenance": set(),
        "dependency_closure": set(),
        "analysis_and_reports": set(),
        "plots_and_metadata": set(),
        "validation": set(),
    }

    def add(category: str, path: Path) -> None:
        if path.resolve() != (ANALYSIS / "artifact-inventory.json").resolve():
            categories[category].add(path)

    for record in integrity.get("files", []):
        add("raw_and_provenance", REPO / record["path"])

    exp = REPO / "test/exploration"
    closure_roots = (
        exp / "qb-q0-standalone-current-quantized-event-20260824/inputs",
        exp / "bvm-read-semantics-audit-and-jsl-width-bracket-v1-20260824/inputs/replay/13ps",
        exp / "physical-bvm-jsl12-qb-sfq-closure-v1-20260824/inputs/13",
        exp / "bvm-jsl8-500-physical-qb-recheck-v1-20260824/inputs/13",
    )
    for root in closure_roots:
        if root.exists():
            for path in root.rglob("*"):
                if path.is_file():
                    add("dependency_closure", path)

    for path in (
        TARGET / "PREREGISTRATION.md",
        TARGET / "REPORT.md",
        TARGET / "REVIEW.md",
        TARGET / "SUMMARY.md",
        TARGET / "manifest.yaml",
        ANALYSIS / "analyze_trajectory.py",
        REPO / "scripts/josim-plot2.py",
        REPO / "scripts/build_visualization_alignment.py",
        REPO / "scripts/verify_visualization_alignment.py",
        REPO / "docs/VISUALIZATION_ALIGNMENT_MANIFEST.yaml",
        REPO / "docs/TOPOLOGY_ALIGNMENT_MANIFEST.yaml",
        REPO / "visualization-alignment-validation.json",
    ):
        add("analysis_and_reports" if path.is_relative_to(TARGET) else "validation", path)

    for path in ANALYSIS.glob("*.json"):
        add("analysis_and_reports", path)
    for path in ANALYSIS.glob("*.csv"):
        add("analysis_and_reports", path)
    for path in PLOT_INPUTS.glob("*.csv"):
        add("analysis_and_reports", path)
    for path in PLOTS.glob("*.html"):
        add("plots_and_metadata", path)
    for path in PLOTS.glob("*.metadata.json"):
        add("plots_and_metadata", path)

    inventory: dict[str, Any] = {
        "schema_version": "1.0",
        "inventory_id": "QB_IDEAL_PHYSICAL_INTERNAL_TRAJECTORY_AUDIT_V1_SHA256",
        "generated_at": now,
        "scope": "all registered raw/provenance inputs, dependency-closure decks/includes, analysis scripts, derived evidence, reports, key plots/metadata, and validation/index files used by this audit",
        "self_exempt": {
            "path": rel(ANALYSIS / "artifact-inventory.json"),
            "reason": "excluding the inventory file itself prevents a SHA-256 self-reference cycle",
        },
        "fresh_checkout_requirement": {
            "required": True,
            "checks": [
                "git ls-files --error-unmatch <path>",
                "git show HEAD:<path> is non-empty",
                "sha256(git show HEAD:<path>) == sha256 recorded below",
            ],
            "status": "REQUIRED_AFTER_COMMIT",
        },
        "categories": {},
    }
    for category, paths in categories.items():
        records = []
        for path in sorted(paths, key=lambda item: rel(item)):
            record = file_record(path, csv_quality=False)
            record["required_tracked"] = True
            records.append(record)
        inventory["categories"][category] = records
    inventory["file_count"] = sum(len(records) for records in inventory["categories"].values())
    inventory["all_present"] = all(record["exists"] for records in inventory["categories"].values() for record in records)
    write_json(ANALYSIS / "artifact-inventory.json", inventory)


def write_plot_input(name: str, series: list[tuple[str, np.ndarray, np.ndarray]], title: str, source_paths: list[str], phase_semantics: str) -> None:
    time_values = sorted({float(time) for _, times, _ in series for time in (times / 1.0e12)})
    index = {value: row for row, value in enumerate(time_values)}
    rows = [{"time": time} for time in time_values]
    headers = ["time"]
    for label, times_ps, values in series:
        headers.append(label)
        for time, value in zip(times_ps / 1.0e12, values):
            rows[index[float(time)]][label] = float(value)
    for row in rows:
        for header in headers[1:]:
            row.setdefault(header, "")
    write_csv(PLOT_INPUTS / f"{name}.csv", headers, rows)
    write_json(PLOTS / f"{name}.metadata.json", {
        "plot": name,
        "title": title,
        "input": rel(PLOT_INPUTS / f"{name}.csv"),
        "source_paths": source_paths,
        "phase_semantics": phase_semantics,
        "source_classification": "DERIVED_DIAGNOSTIC_ONLY",
        "renderer": "scripts/josim-plot2.py",
        "normalization": "-j 2pi only labels phase as continuous phase turns rad/2pi; no SFQ count",
    })


def prepare_plots(tables: dict[str, Table], q0_tables: dict[str, Table]) -> list[dict[str, Any]]:
    PLOTS.mkdir(parents=True, exist_ok=True)
    PLOT_INPUTS.mkdir(parents=True, exist_ok=True)
    selected = tables
    specs: list[tuple[str, str, list[tuple[str, str, str]], str]] = [
        ("pre-bias-state-comparison", "PRE operating-point comparison", [("P(C13 BJL2)", "C13.logical1_read", "P(BJL2|XBQ)"), ("P(D12 BJL2)", "D12.logical1_read", "P(BJL2|XBQ)"), ("P(E8 BJL2)", "E8.logical1_read", "P(BJL2|XBQ)"), ("I(C13 Lin)", "C13.logical1_read", "I(LIN|XBQ)"), ("I(D12 Lin)", "D12.logical1_read", "I(LIN|XBQ)"), ("I(E8 Lin)", "E8.logical1_read", "I(LIN|XBQ)")], "continuous phase rad/2pi plus current A"),
        ("input-port-orientation-kcl", "Input port source versus QB Lin", [("I(C13 source)", "C13.logical1_read", "I(I_REPLAY)"), ("I(C13 Lin)", "C13.logical1_read", "I(LIN|XBQ)"), ("I(D12 source)", "D12.logical1_read", "I(B_LD12)"), ("I(D12 Lin)", "D12.logical1_read", "I(LIN|XBQ)"), ("I(E8 source)", "E8.logical1_read", "I(B_LD8)"), ("I(E8 Lin)", "E8.logical1_read", "I(LIN|XBQ)"), ("V(C13 IN)", "C13.logical1_read", "V(IN)"), ("V(D12 IN)", "D12.logical1_read", "V(IN)"), ("V(E8 IN)", "E8.logical1_read", "V(IN)")], "input source current and Lin current are A; V(IN) is V"),
        ("node2-current-partition", "QB node2 current partition", [("I(C13 BJs)", "C13.logical1_read", "I(BJs|XBQ)"), ("I(C13 L1)", "C13.logical1_read", "I(L1|XBQ)"), ("I(C13 BJL1)", "C13.logical1_read", "I(BJL1|XBQ)"), ("I(E8 BJs)", "E8.logical1_read", "I(BJs|XBQ)"), ("I(E8 L1)", "E8.logical1_read", "I(L1|XBQ)"), ("I(E8 BJL1)", "E8.logical1_read", "I(BJL1|XBQ)")], "branch currents A; diagnostic KCL partition"),
        ("node3-current-partition", "QB node3 current partition", [("I(C13 L1)", "C13.logical1_read", "I(L1|XBQ)"), ("I(C13 RB)", "C13.logical1_read", "I(RB|XBQ)"), ("I(C13 L2)", "C13.logical1_read", "I(L2|XBQ)"), ("I(E8 L1)", "E8.logical1_read", "I(L1|XBQ)"), ("I(E8 RB)", "E8.logical1_read", "I(RB|XBQ)"), ("I(E8 L2)", "E8.logical1_read", "I(L2|XBQ)")], "branch currents A; diagnostic KCL partition"),
        ("node4-current-partition", "QB node4/output current partition", [("I(C13 L2)", "C13.logical1_read", "I(L2|XBQ)"), ("I(C13 L0)", "C13.logical1_read", "I(L0|XBQ)"), ("I(C13 BJL2)", "C13.logical1_read", "I(BJL2|XBQ)"), ("I(E8 L2)", "E8.logical1_read", "I(L2|XBQ)"), ("I(E8 L0)", "E8.logical1_read", "I(L0|XBQ)"), ("I(E8 BJL2)", "E8.logical1_read", "I(BJL2|XBQ)")], "branch currents A; diagnostic KCL partition"),
        ("bjs-vs-bjl1-phase-trajectory", "BJs versus BJL1 continuous phase trajectory", [("P(C13 BJs)", "C13.logical1_read", "P(BJs|XBQ)"), ("P(C13 BJL1)", "C13.logical1_read", "P(BJL1|XBQ)"), ("P(E8 BJs)", "E8.logical1_read", "P(BJs|XBQ)"), ("P(E8 BJL1)", "E8.logical1_read", "P(BJL1|XBQ)")], "continuous phase turns rad/2pi; not an event count"),
        ("bjl1-vs-bjl2-phase-trajectory", "BJL1 versus BJL2 continuous phase trajectory", [("P(C13 BJL1)", "C13.logical1_read", "P(BJL1|XBQ)"), ("P(C13 BJL2)", "C13.logical1_read", "P(BJL2|XBQ)"), ("P(E8 BJL1)", "E8.logical1_read", "P(BJL1|XBQ)"), ("P(E8 BJL2)", "E8.logical1_read", "P(BJL2|XBQ)")], "continuous phase turns rad/2pi; not an event count"),
        ("vin-vs-ilin-port-trajectory", "QB input voltage and Lin current", [("V(C13 IN)", "C13.logical1_read", "V(IN)"), ("V(E8 IN)", "E8.logical1_read", "V(IN)"), ("I(C13 Lin)", "C13.logical1_read", "I(LIN|XBQ)"), ("I(E8 Lin)", "E8.logical1_read", "I(LIN|XBQ)")], "V(IN) and I(Lin) retain native units in separate panels"),
        ("matched-controls", "Matched logical0 and READ=0 control BJL2 trajectories", [(f"P({label} BJL2)", f"{family}.{role}", "P(BJL2|XBQ)") for family, label in (("C13", "C13"), ("D12", "D12"), ("E8", "E8")) for role in ("logical0_read", "logical1_no_read_control", "logical0_no_read_control")], "continuous phase turns rad/2pi; matched controls only; not an event count"),
    ]
    for name, title, signal_specs, semantics in specs:
        series: list[tuple[str, np.ndarray, np.ndarray]] = []
        paths: list[str] = []
        for label, key, signal in signal_specs:
            table = selected[key]
            series.append((label, table.time_ps, table.column(signal)[0]))
            paths.append(rel(table.path))
        write_plot_input(name, series, title, paths, semantics)
    q0_series: list[tuple[str, np.ndarray, np.ndarray]] = []
    q0_paths: list[str] = []
    for label, key in (("P(Q0 45u BJL2)", "45u"), ("P(Q0 68p4u BJL2)", "68p4u")):
        table = q0_tables[key]
        q0_series.append((label, table.time_ps, table.column("P(BJL2|XBQ)")[0]))
        q0_paths.append(rel(table.path))
    for label, key in (("P(C13 ideal replay BJL2)", "C13.logical1_read"), ("P(E8 physical BJL2)", "E8.logical1_read")):
        table = tables[key]
        q0_series.append((label, table.time_ps, table.column("P(BJL2|XBQ)")[0]))
        q0_paths.append(rel(table.path))
    write_plot_input("standalone45-vs68p4-vs-physical-trajectory", q0_series, "Native-timestamp Q0 versus ideal/physical BJL2 trajectory", q0_paths, "continuous phase turns rad/2pi; Q0 dt=0.1 ps and 13 ps dt=0.0125 ps are not time-aligned or interpolated")
    return [{"name": name, "path": rel(PLOTS / f"{name}.html"), "metadata": rel(PLOTS / f"{name}.metadata.json")} for name, _, _, _ in specs] + [{"name": "standalone45-vs68p4-vs-physical-trajectory", "path": rel(PLOTS / "standalone45-vs68p4-vs-physical-trajectory.html"), "metadata": rel(PLOTS / "standalone45-vs68p4-vs-physical-trajectory.metadata.json")}]


def independent_recheck(tables: dict[str, Table], q0_tables: dict[str, Table], primary: dict[str, Any], pre_results: list[dict[str, Any]], div_results: dict[str, Any]) -> dict[str, Any]:
    """Re-read raw files and recompute a minimal subset through a separate path.

    This deliberately does not call the primary trajectory, KCL, PRE, or
    divergence helpers.  It is a weak-oracle probe against shared helper bugs,
    not a second scientific authority.
    """
    reread = {key: load_table(table.path) for key, table in tables.items()}

    def direct_features(table: Table, kind: str) -> dict[str, np.ndarray]:
        source_name = "I(I_REPLAY)" if kind == "ideal" else ("I(B_LD12)" if kind == "d12" else "I(B_LD8)")
        phase_bjs = np.unwrap(table.column("P(BJs|XBQ)")[0]) / TWO_PI
        phase_bjl1 = np.unwrap(table.column("P(BJL1|XBQ)")[0]) / TWO_PI
        phase_bjl2 = np.unwrap(table.column("P(BJL2|XBQ)")[0]) / TWO_PI
        return {
            "source": table.column(source_name)[0],
            "lin": table.column("I(LIN|XBQ)")[0],
            "vin": table.column("V(IN)")[0],
            "bjs_phase": phase_bjs - float(np.median(phase_bjs[mask(table.time_ps, PRE)])),
            "bjs_current": table.column("I(BJs|XBQ)")[0],
            "bjl1_current": table.column("I(BJL1|XBQ)")[0],
            "bjl2_phase": phase_bjl2 - float(np.median(phase_bjl2[mask(table.time_ps, PRE)])),
            "bjl2_current": table.column("I(BJL2|XBQ)")[0],
            "l0": table.column("I(L0|XBQ)")[0],
            "l1": table.column("I(L1|XBQ)")[0],
            "l2": table.column("I(L2|XBQ)")[0],
            "rb": table.column("I(RB|XBQ)")[0],
            "rj1": table.column("I(RJ1|XBQ)")[0],
            "rj2": table.column("I(RJ2|XBQ)")[0],
            "vout": table.column("V(OUT)")[0],
        }

    def direct_gate(left: np.ndarray, right: np.ndarray, terms: list[np.ndarray], time_ps: np.ndarray, bounds: tuple[float, float]) -> dict[str, Any]:
        selected = mask(time_ps, bounds)
        residual = left[selected] - right[selected]
        bound = ABS_TOL + REL_TOL * sum(np.abs(term[selected]) for term in terms)
        ratio = np.abs(residual) / bound
        over = ratio > 1.0
        return {
            "max_abs_A": json_float(np.max(np.abs(residual))),
            "p95_abs_A": json_float(np.percentile(np.abs(residual), 95)),
            "max_ratio": json_float(np.max(ratio)),
            "p95_ratio": json_float(np.percentile(ratio, 95)),
            "samples_over_bound": int(np.count_nonzero(over)),
            "longest_consecutive_over_bound": int(longest_true(over)),
            "passed": bool(np.max(ratio) <= 1.0 and np.percentile(ratio, 95) <= 1.0 and longest_true(over) < 3),
        }

    orientation: dict[str, Any] = {}
    for key in ("C13.logical1_read", "D12.logical1_read", "E8.logical1_read"):
        kind = "ideal" if key.startswith("C13") else ("d12" if key.startswith("D12") else "e8")
        table = reread[key]
        f = direct_features(table, kind)
        equations = {
            "input": (f["source"], f["lin"], [f["source"], f["lin"]]),
            "node2": (f["bjs_current"], f["l1"] + f["bjl1_current"] + f["rj1"], [f["bjs_current"], f["l1"], f["bjl1_current"], f["rj1"]]),
            "node3": (f["l1"] + f["rb"], f["l2"], [f["l1"], f["rb"], f["l2"]]),
            "node4": (f["l2"], f["l0"] + f["bjl2_current"] + f["rj2"], [f["l2"], f["l0"], f["bjl2_current"], f["rj2"]]),
        }
        orientation[key] = {}
        for window, bounds in (("PRE", PRE), ("ACTIVE", ACTIVE), ("TRANSITION", TRANSITION), ("POST", POST)):
            orientation[key][window] = {name: direct_gate(*equation, table.time_ps, bounds) for name, equation in equations.items()}

    def direct_phase_area(table: Table) -> dict[str, Any]:
        phase = np.unwrap(table.column("P(BJL2|XBQ)")[0])
        voltage = table.column("V(BJL2|XBQ)")[0]
        output: dict[str, Any] = {}
        for label, bounds in (("ACTIVE", ACTIVE), ("TRANSITION", TRANSITION), ("POST", POST)):
            indices = np.flatnonzero(mask(table.time_ps, bounds))
            segments: list[dict[str, Any]] = []
            if indices.size >= 2:
                local = phase[indices]
                signs = np.sign(np.diff(local))
                nz = np.flatnonzero(signs != 0)
                if nz.size:
                    start = 0
                    current = int(signs[nz[0]])
                    for position in nz[1:]:
                        sign = int(signs[position])
                        if sign != current:
                            selected = indices[start : int(position) + 1]
                            delta = float((phase[selected[-1]] - phase[selected[0]]) / TWO_PI)
                            area = float(integrate(table.time_ps[selected], voltage[selected]) / PHI0)
                            segments.append({"delta_turns": json_float(delta), "area_phi0": json_float(area), "residual_turns": json_float(area - delta)})
                            start = int(position)
                            current = sign
                    selected = indices[start:]
                    delta = float((phase[selected[-1]] - phase[selected[0]]) / TWO_PI)
                    area = float(integrate(table.time_ps[selected], voltage[selected]) / PHI0)
                    segments.append({"delta_turns": json_float(delta), "area_phi0": json_float(area), "residual_turns": json_float(area - delta)})
            output[label] = {"segments": segments, "largest": max(segments, key=lambda item: abs(float(item["delta_turns"]))) if segments else None}
        return output

    phase_area = {key: direct_phase_area(reread[key]) for key in ("C13.logical1_read", "D12.logical1_read", "E8.logical1_read")}
    pair_specs = (("D12", "d12"), ("E8", "e8"))
    pre_recomputed: list[dict[str, Any]] = []
    divergence_recomputed: dict[str, Any] = {}
    for suffix, kind in pair_specs:
        pair = f"C13.logical1_read vs {suffix}"
        left = reread["C13.logical1_read"]
        right = reread[f"{suffix}.logical1_read"]
        lf = direct_features(left, "ideal")
        rf = direct_features(right, kind)
        feature_rows: list[dict[str, Any]] = []
        first_active: list[float] = []
        for name in ("source", "lin", "vin", "bjs_phase", "bjs_current", "bjl1_current", "l1", "rb", "l2", "l0", "bjl2_current", "rj1", "rj2", "vout"):
            la = lf[name][mask(left.time_ps, PRE)]
            rb = rf[name][mask(right.time_ps, PRE)]
            scale_a = max(1.4826 * mad(la), 1.0e-12 * max(1.0, float(np.max(np.abs(la)))))
            scale_b = max(1.4826 * mad(rb), 1.0e-12 * max(1.0, float(np.max(np.abs(rb)))))
            limit = 5.0 * math.sqrt(scale_a * scale_a + scale_b * scale_b)
            pre_difference = abs(float(np.median(la)) - float(np.median(rb)))
            pre_recomputed.append({"pair": pair, "feature": name, "pair_limit": json_float(limit), "median_abs_difference": json_float(pre_difference), "within_limit": bool(pre_difference <= limit)})
            delta = np.abs((lf[name] - float(np.median(la))) - (rf[name] - float(np.median(rb))))
            active_indices = np.flatnonzero(mask(left.time_ps, ACTIVE) | mask(left.time_ps, TRANSITION))
            first = None
            for position in range(0, active_indices.size - 2):
                if np.all(delta[active_indices[position : position + 3]] > limit):
                    first = float(left.time_ps[active_indices[position]])
                    break
            feature_rows.append({"feature": name, "first_active_or_transition_ps": first})
            if first is not None:
                first_active.append(first)
        divergence_recomputed[pair] = {"features": feature_rows, "earliest_active_or_transition_ps": min(first_active) if first_active else None}

    primary_gate_match = True
    for key, windows in orientation.items():
        primary_windows = primary["cases"][key]["orientation_kcl"]["windows"]
        for window, equations in windows.items():
            for equation, value in equations.items():
                primary_value = primary_windows[window][equation]["expected"]
                primary_gate_match &= value["max_abs_A"] == primary_value["max_abs_A"] and value["max_ratio"] == primary_value["max_ratio"]
    return {
        "status": "PASS" if primary_gate_match else "INCONCLUSIVE",
        "reads_derived_outputs": False,
        "raw_paths": [rel(table.path) for table in reread.values()],
        "orientation_kcl_recheck": orientation,
        "bjl2_phase_area_recheck": phase_area,
        "pre_state_recheck": {"features": pre_recomputed, "source": "raw-only direct calculation"},
        "divergence_recheck": divergence_recomputed,
        "matches_primary_orientation_kcl_subset": primary_gate_match,
    }


def write_report(integrity: dict[str, Any], chain: dict[str, Any], primary: dict[str, Any], pre_results: list[dict[str, Any]], divergence: dict[str, Any], q0_results: dict[str, Any], independent: dict[str, Any], plot_records: list[dict[str, Any]], now: str) -> None:
    e8_div = divergence["C13.logical1_read vs E8"]
    earliest = e8_div.get("earliest_active_or_transition")
    tie_layers = e8_div.get("earliest_tie_layers", [])
    layer = e8_div.get("earliest_layer_classification", "NO_CREDIBLE_ACTIVE_DIVERGENCE")
    recommendation_by_layer = {
        "input_port": "source impedance/load-line family at the QB input interface",
        "bjs_trajectory": "BJs input-coupling/critical-current and Lin interface family",
        "node2": "BJL1/RJ1/L1 node2 partition family",
        "node3": "RB/L2 node3 partition family",
        "node4": "BJL2/RJ2/L0/output-load family",
        "NO_CREDIBLE_ACTIVE_DIVERGENCE": "No new parameter family is licensed; preserve the bounded observation and stop",
    }
    recommendation = (
        "coupled input-port/load-line plus BJs/node2 interface family; no unique first layer is established"
        if len(tie_layers) > 1
        else recommendation_by_layer.get(layer, "No new parameter family is licensed; preserve the bounded observation and stop")
    )
    layer_label = (
        "TIE: " + " + ".join(tie_layers)
        if len(tie_layers) > 1
        else layer
    )
    layer_result = e8_div.get("layer_first", {})
    layer_text = ", ".join(
        f"{name}={float(value['first_divergence_time_ps']):.6f}ps"
        for name, value in layer_result.items()
    ) if layer_result else "none"
    report_lines = [
        "# QB_IDEAL_PHYSICAL_INTERNAL_TRAJECTORY_AUDIT_V1",
        "",
        f"- analysis timestamp: `{now}`",
        f"- analysis HEAD: `{integrity['head']}`",
        "- solver execution: no new JoSIM run; frozen solver metadata is recorded only",
        "- final disposition: `MECHANISM_AUDIT_INCONCLUSIVE`",
        "",
        "## Artifact status",
        "",
        f"- C13 historical raw→snapshot→PWL chain: `{chain['all_roles_closed'] and 'HISTORICAL_REPLAY_SOURCE_CHAIN_CLOSED' or 'INVALID'}`; final-JSL source semantics: `INCONCLUSIVE`.",
        "- D12 12×320: raw files are complete for descriptive recheck, but the four registered input-deck hashes are `RUN_INPUT_HASH_MISMATCH`; it cannot support certified mechanism ranking.",
        "- E8 8×500: current tracked raw/input closure was rechecked descriptively; it cannot repair the C13 semantic boundary or D12 provenance defect.",
        f"- independent raw recheck: `{independent['status']}`.",
        "",
        "## Key results",
        "",
        "| pair / reference | status | key result |",
        "|---|---|---|",
    ]
    for pair in pre_results:
        report_lines.append(f"| PRE {pair['pair']} | `{pair['status']}` | raw PRE feature comparison; phase uses relative turns plus sin/cos |" )
    report_lines.append(f"| C13 ↔ D12 | `DESCRIPTIVE_RAW_OBSERVATION / PROVENANCE_INCONCLUSIVE` | first-divergence table retained but not certified |")
    if earliest:
        report_lines.append(f"| C13 ↔ E8 | `ANALYZED; total still INCONCLUSIVE` | representative earliest active/transition feature `{earliest['feature']}` at `{earliest['first_divergence_time_ps']:.6f} ps`, layer `{layer_label}`; no unique layer order within `{DIVERGENCE_TIE_PS:.4f} ps` |")
    else:
        report_lines.append("| C13 ↔ E8 | `ANALYZED; no active/transition first divergence` | no registered feature crossed the three-sample threshold in ACTIVE∪TRANSITION |")
    for label in ("45u", "68p4u"):
        result = q0_results[label]
        report_lines.append(f"| Q0 scaled {label} | `{result['local_reference_classification']}` | BJL2 local candidate counts `{result['BJL2']['candidate_counts']}` across six pulse windows |")
    report_lines += [
        "",
        "## Observed",
        "",
        "- All five reference families have finite, strictly increasing raw time axes and the registered 13 ps cases share the native 0.0125 ps output grid; Q0 remains 0.1 ps and is not aligned to the 13 ps files.",
        "- C13 snapshots contain only `time_ps,I_JSL_A`; exact replay closure uses the historical first `I(B_LD1)` occurrence at source-column index 14. The direct terminal `I(B_LD12)` index 51 is a separate diagnostic column.",
        "- Physical E8 and D12 expose the QB port and internal BJs→BJL1→BJL2 branch signals needed for partition analysis; local phase trajectories and voltage-area diagnostics are retained separately from event claims.",
        "",
        "## Derived",
        "",
        "- `orientation-audit.json` reports the pre-registered source-vs-Lin and node2/node3/node4 residuals with fixed `abs_tol=1e-12 A`, `rel_tol=1e-6`, max/p95 and three-consecutive-sample criteria.",
        "- `pre-bias-state.csv` reports the pre-registered feature-specific scale/limit comparison; a PRE mismatch is not relabeled as an ACTIVE root cause.",
        f"- For the C13↔E8 pair, the earliest active/transition classification is `{layer_label}`; layer-specific first samples are recorded in `divergence-timeline.csv`: `{layer_text}`. Layers within `{DIVERGENCE_TIE_PS:.4f} ps` are treated as tied, not causally ordered.",
        "- Q0 45 µA and 68.4 µA are six-pulse local references under their own windows; they do not establish a universal threshold or timestep convergence.",
        "",
        "## Inference",
        "",
        f"- The strongest bounded mechanism classification is `{layer_label}` / `{recommendation}` for the C13 auxiliary-probe replay versus E8 physical drive, subject to the provenance boundary. This is a temporal/feature-level inference, not a unique physical root-cause proof.",
        "- The E8 observation is conservatively described as `JSL8_LOADLINE_SHIFT_NO_DIRECTIONAL_RECOVERY`; the superseded directional wording `PAPER_JSL8_IMPROVES_PHYSICAL_MARGIN` is not used.",
        "- No local BJs multi-turn trajectory is called overdrive/failure, and no visualization or derivative sample is used as an event count.",
        "",
        "## Unknown / unresolved",
        "",
        "- C13 does not establish an ideal replay of the final physical JSL branch because its historical source selection is the auxiliary index-14 `I(B_LD1)` column. A new index-51 replay would be a different experiment and was not created.",
        "- The D12 run-input hash mismatch prevents an authority-level C13↔D12 mechanism ranking. The missing historical `control-provenance.yaml` also limits READ/selectivity claims.",
        "- One native timestep and these existing runs do not establish timestep convergence, parameter sensitivity, or a unique causal mechanism.",
        "",
        "## Next parameter family recommendation (not executed)",
        "",
        f"- first divergence classification: `{layer_label}`; recommended family: `{recommendation}`.",
        "- existing evidence: the first registered feature crossing occurs only after the fixed PRE subtraction and three-sample persistence rule; physical model: frozen BQ plus existing E8 BVM/JSL interface; target quantity: the layer's raw current/phase/voltage feature and its downstream partition.",
        "- falsifiable hypothesis: changing only the nominated family should move the nominated feature and its downstream signature while leaving the matched controls and upstream layers within their registered bounds.",
        "- controls: retain logical1 no-read, logical0 read, logical0 no-read, existing C13 historical replay, and no-magnetic-coupling boundary; do not change multiple families in one follow-up.",
        "- decision tree: if the nominated layer moves first and downstream signatures follow, retain it as a candidate mechanism; if an upstream layer moves first, reclassify the divergence; if controls move comparably or orientation/KCL fails, mark `INCONCLUSIVE` and stop.",
        "- stop rule: no sweep or parameter change is executed in this task; any future route, metric freeze, or paper claim requires renewed authorization and review.",
        "",
        "## Evidence files",
        "",
        "- `analysis/reference-integrity.json`",
        "- `analysis/orientation-audit.json`",
        "- `analysis/pre-bias-state.csv`",
        "- `analysis/divergence-timeline.csv`",
        "- `analysis/node-partition-summary.csv`",
        "- `analysis/trajectory-audit.json`",
        "- `analysis/independent-raw-recheck.json`",
        "- `analysis/artifact-inventory.json` (non-circular final SHA-256 inventory; the inventory file itself is explicitly self-exempt)",
        "- key diagnostic plots are listed in `manifest.yaml` and each has a sidecar metadata JSON; plots are not Gate authority.",
        "",
        "## Provenance and method",
        "",
        "The analysis script reads the five registered reference families and current tracked netlist/provenance files only. It does not call `scripts/sfq_metrics.py`, `scripts/run_exp.sh`, or `build/josim-cli` to generate a run.",
    ]
    (TARGET / "REPORT.md").write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    summary_lines = [
        "# QB ideal / physical internal trajectory audit — summary",
        "",
        "- Final: `MECHANISM_AUDIT_INCONCLUSIVE`.",
        f"- C13 source chain: `{chain['all_roles_closed'] and 'HISTORICAL_REPLAY_SOURCE_CHAIN_CLOSED' or 'INVALID'}` for historical index-14 `I(B_LD1)`; final-JSL semantics remain `INCONCLUSIVE`.",
        "- D12: descriptive raw only because registered input-deck hashes do not match current tracked decks.",
        f"- E8 C13↔physical first divergence classification: `{layer_label}`" + (f" at `{earliest['first_divergence_time_ps']:.6f} ps`; representative feature `{earliest['feature']}`; tied layers are recorded in `trajectory-audit.json`." if earliest else "."),
        "- Q0 scaled 45 µA / 68.4 µA remain bounded local reference points, not universal thresholds.",
        "- No new JoSIM run, no parameter sweep, no magnetic coupling, no JTL/T1; stop here.",
    ]
    (TARGET / "SUMMARY.md").write_text("\n".join(summary_lines) + "\n", encoding="utf-8")


def main() -> None:
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    c13, d12, e8, q0 = load_all_specs()
    all_tables, kinds = load_case_records(c13, d12, e8)
    q0_tables = {label: load_table(path) for label, path in q0.items()}
    chain = source_chain(c13)
    primary_cases = {key: case_trajectory(key, all_tables[key], kinds[key], key.split(".", 1)[1]) for key in all_tables}
    pre_results = [
        pre_compare(all_tables["C13.logical1_read"], "ideal", all_tables["D12.logical1_read"], "d12", "C13.logical1_read vs D12.logical1_read"),
        pre_compare(all_tables["C13.logical1_read"], "ideal", all_tables["E8.logical1_read"], "e8", "C13.logical1_read vs E8.logical1_read"),
    ]
    divergence = {
        "C13.logical1_read vs D12": divergence_pair(all_tables["C13.logical1_read"], "ideal", all_tables["D12.logical1_read"], "d12", "C13.logical1_read vs D12"),
        "C13.logical1_read vs E8": divergence_pair(all_tables["C13.logical1_read"], "ideal", all_tables["E8.logical1_read"], "e8", "C13.logical1_read vs E8"),
    }
    pre_rows = [row for result in pre_results for row in result.get("features", [])]
    write_csv(ANALYSIS / "pre-bias-state.csv", list(pre_rows[0].keys()) if pre_rows else ["pair", "feature", "status"], pre_rows)
    div_rows = [row for result in divergence.values() for row in result.get("features", [])]
    write_csv(ANALYSIS / "divergence-timeline.csv", list(div_rows[0].keys()) if div_rows else ["pair", "feature"], div_rows)
    partition = [row for key, table in all_tables.items() for row in partition_rows(key, table, kinds[key], key.split(".", 1)[1])]
    write_csv(ANALYSIS / "node-partition-summary.csv", list(partition[0].keys()), partition)
    q0_results = {label: q0_case(path, label) for label, path in q0.items()}
    integrity_paths: list[tuple[Path, bool]] = []
    for spec in c13.values():
        integrity_paths.extend([(spec["raw"], True), (spec["source_raw"], True), (spec["snapshot"], True), (spec["deck"], False)])
    for specs in (d12, e8):
        for spec in specs.values():
            integrity_paths.extend([(spec["raw"], True), (spec["deck"], False)])
    for path in q0.values():
        integrity_paths.append((path, True))
    extra_paths = [
        TARGET / "PREREGISTRATION.md",
        REPO / "docs/research/METRIC_SPEC_V2.md",
        REPO / "build/josim-cli",
        REPO / "scripts/josim-plot2.py",
        REPO / "test/exploration/bvm-read-semantics-audit-and-jsl-width-bracket-v1-20260824/manifest.yaml",
        REPO / "test/exploration/bvm-read-semantics-audit-and-jsl-width-bracket-v1-20260824/reference/source-manifest.json",
        REPO / "test/exploration/physical-bvm-jsl12-qb-sfq-closure-v1-20260824/manifest.yaml",
        REPO / "test/exploration/bvm-jsl8-500-physical-qb-recheck-v1-20260824/manifest.yaml",
        REPO / "test/exploration/qb-q0-standalone-current-quantized-event-20260824/manifest.yaml",
        REPO / "test/exploration/bvm-read-semantics-audit-and-jsl-width-bracket-v1-20260824/inputs/bq_cell.cir",
        REPO / "test/exploration/bvm-read-semantics-audit-and-jsl-width-bracket-v1-20260824/inputs/qb-jjmit.cir",
        REPO / "test/exploration/bvm-jsl8-500-physical-qb-recheck-v1-20260824/inputs/bq_cell.cir",
        REPO / "test/exploration/bvm-jsl8-500-physical-qb-recheck-v1-20260824/inputs/jjmit.cir",
        REPO / "test/exploration/bvm-jsl8-500-physical-qb-recheck-v1-20260824/inputs/bvm_cell.cir",
        REPO / "test/exploration/physical-bvm-jsl12-qb-sfq-closure-v1-20260824/inputs/bq_cell.cir",
        REPO / "test/exploration/physical-bvm-jsl12-qb-sfq-closure-v1-20260824/inputs/jjmit.cir",
        REPO / "test/exploration/physical-bvm-jsl12-qb-sfq-closure-v1-20260824/inputs/bvm_cell.cir",
        REPO / "test/exploration/qb-q0-standalone-current-quantized-event-20260824/manifest.yaml",
    ]
    integrity = {
        "analysis_timestamp": now,
        "head": subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True, check=True).stdout.strip(),
        "preregistration": rel(TARGET / "PREREGISTRATION.md"),
        "solver": {
            "path": rel(REPO / "build/josim-cli"),
            "sha256": sha256(REPO / "build/josim-cli"),
            "version_output": subprocess.run([str(REPO / "build/josim-cli"), "--version"], cwd=REPO, capture_output=True, text=True).stdout.strip(),
        },
        "fixed_rules": {"abs_tol_A": ABS_TOL, "rel_tol": REL_TOL, "windows_ps": {"PRE": PRE, "ACTIVE": ACTIVE, "TRANSITION": TRANSITION, "POST": POST}},
        "files": [],
        "d12_input_hash_disposition": "RUN_INPUT_HASH_MISMATCH (historical manifest declaration retained; no rewrite)",
        "c13_source_chain": chain,
        "artifact_inventory": rel(ANALYSIS / "artifact-inventory.json"),
    }
    d12_manifest = REPO / "test/exploration/physical-bvm-jsl12-qb-sfq-closure-v1-20260824/manifest.yaml"
    e8_manifest = REPO / "test/exploration/bvm-jsl8-500-physical-qb-recheck-v1-20260824/manifest.yaml"
    integrity["input_deck_hash_comparison"] = {}
    for family, specs, manifest_path in (("D12", d12, d12_manifest), ("E8", e8, e8_manifest)):
        for role, spec in specs.items():
            declared = declared_sha(manifest_path, f"13ps_{role}")
            actual = sha256(spec["deck"])
            integrity["input_deck_hash_comparison"][f"{family}.{role}"] = {
                "declared_manifest_sha256": declared,
                "current_deck_sha256": actual,
                "status": "MATCH" if declared and actual == declared else "RUN_INPUT_HASH_MISMATCH",
            }
    seen: set[str] = set()
    for path, csv_quality in integrity_paths + [(path, False) for path in extra_paths]:
        key = str(path.resolve())
        if key not in seen:
            integrity["files"].append(file_record(path, csv_quality))
            seen.add(key)
    write_json(ANALYSIS / "reference-integrity.json", integrity)
    trajectory = {
        "analysis_timestamp": now,
        "head": integrity["head"],
        "final_disposition": "MECHANISM_AUDIT_INCONCLUSIVE",
        "source_chain": chain,
        "cases": primary_cases,
        "pre_state": pre_results,
        "divergence": divergence,
        "q0": q0_results,
        "constraints": {"no_new_josim": True, "no_sweep": True, "no_magnetic_coupling": True, "no_jtl_t1": True},
    }
    write_json(ANALYSIS / "orientation-audit.json", {"head": integrity["head"], "cases": {key: value["orientation_kcl"] for key, value in primary_cases.items()}})
    write_json(ANALYSIS / "trajectory-audit.json", trajectory)
    plot_records = prepare_plots(all_tables, q0_tables)
    for record in plot_records:
        for path, csv_quality in (
            (PLOTS / Path(record["path"]).name, False),
            (PLOTS / Path(record["metadata"]).name, False),
            (PLOT_INPUTS / f"{record['name']}.csv", False),
        ):
            key = str(path.resolve())
            if key not in seen:
                integrity["files"].append(file_record(path, csv_quality))
                seen.add(key)
    write_json(ANALYSIS / "reference-integrity.json", integrity)
    independent = independent_recheck(all_tables, q0_tables, {"cases": primary_cases}, pre_results, divergence)
    write_json(ANALYSIS / "independent-raw-recheck.json", independent)
    manifest = {
        "experiment": "QB_IDEAL_PHYSICAL_INTERNAL_TRAJECTORY_AUDIT_V1",
        "date_directory": TARGET.name,
        "head": integrity["head"],
        "status": "MECHANISM_AUDIT_INCONCLUSIVE",
        "analysis_only": True,
        "solver": integrity["solver"],
        "raw_refs": {"Q0_45": rel(q0["45u"]), "Q0_68p4": rel(q0["68p4u"]), "C13": {role: rel(spec["raw"]) for role, spec in c13.items()}, "D12": {role: rel(spec["raw"]) for role, spec in d12.items()}, "E8": {role: rel(spec["raw"]) for role, spec in e8.items()}},
        "source_chain_status": "HISTORICAL_REPLAY_SOURCE_CHAIN_CLOSED" if chain["all_roles_closed"] else "INVALID",
        "c13_selected_source_column": {"index": 14, "header": "I(B_LD1)", "semantic": "auxiliary probe; not final I(B_LD12)"},
        "d12_disposition": "DESCRIPTIVE_RAW_OBSERVATION / RUN_INPUT_HASH_MISMATCH",
        "derived_evidence": [rel(ANALYSIS / name) for name in ("reference-integrity.json", "orientation-audit.json", "pre-bias-state.csv", "divergence-timeline.csv", "node-partition-summary.csv", "trajectory-audit.json", "independent-raw-recheck.json", "artifact-inventory.json")],
        "plots": plot_records,
        "plot_inputs": [rel(PLOT_INPUTS / f"{record['name']}.csv") for record in plot_records],
        "visualization_boundary": "key mechanism diagnostics only; HTML is not event/Gate authority",
    }
    write_json(TARGET / "manifest.yaml", manifest)
    write_report(integrity, chain, {"cases": primary_cases}, pre_results, divergence, q0_results, independent, plot_records, now)
    write_artifact_inventory(integrity, plot_records, now)
    print(json.dumps({"head": integrity["head"], "source_chain": chain["all_roles_closed"], "e8_earliest": divergence["C13.logical1_read vs E8"].get("earliest_active_or_transition"), "q0": {label: result["local_reference_classification"] for label, result in q0_results.items()}}, ensure_ascii=False))


if __name__ == "__main__":
    main()
