#!/usr/bin/env python3
"""Mechanical, stored-grid analysis for one immutable run."""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import sys
from pathlib import Path
from typing import Any

from common import (KNOWN_UNSUPPORTED_RAW_SIGNALS, ROOT, legacy, read_json,
                    resolve_run_dir, sha256, write_json)

PHI0 = 2.067833848e-15


def load_raw(path: Path) -> tuple[list[str], list[dict[str, float]]]:
    with path.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        headers = reader.fieldnames or []
        if not headers or len(headers) != len(set(headers)):
            raise ValueError("raw CSV has an empty or duplicate header")
        rows: list[dict[str, float]] = []
        for line_number, item in enumerate(reader, start=2):
            row: dict[str, float] = {}
            for key in headers:
                value = item.get(key)
                if value is None or value == "":
                    raise ValueError(f"empty raw cell at line {line_number}, column {key}")
                number = float(value)
                if not math.isfinite(number):
                    raise ValueError(f"non-finite raw value at line {line_number}, column {key}")
                row[key] = number
            rows.append(row)
    return headers, rows


def unwrap(values: list[float]) -> list[float]:
    if not values:
        return []
    result = [values[0]]
    offset = 0.0
    previous = values[0]
    for value in values[1:]:
        difference = value - previous
        while difference > math.pi:
            offset -= 2.0 * math.pi
            difference -= 2.0 * math.pi
        while difference < -math.pi:
            offset += 2.0 * math.pi
            difference += 2.0 * math.pi
        result.append(value + offset)
        previous = value
    return result


def signal_definitions(params: dict[str, Any]) -> dict[str, dict[str, str]]:
    definitions: dict[str, dict[str, str]] = {}

    def put(signal: str, group: str, quantity: str, unit: str) -> None:
        definitions[signal] = {"group": group, "quantity": quantity, "unit": unit}

    for index in range(1, int(params["ARRAY_SIZE"]) + 1):
        for jj in ("B_JM1", "B_JM2"):
            for prefix, unit, quantity in (("P", "rad", "phase"), ("V", "V", "voltage"), ("I", "A", "current")):
                put(f"{prefix}({jj}|XBVM{index})", "storage", quantity, unit)
        for branch in ("L_M1", "L_M2", "L_M3", "L_PM"):
            for prefix, unit, quantity in (("I", "A", "current"), ("V", "V", "voltage")):
                put(f"{prefix}({branch}|XBVM{index})", "storage", quantity, unit)
        for jj in ("B_JS1", "B_JS2"):
            for prefix, unit, quantity in (("P", "rad", "phase"), ("V", "V", "voltage"), ("I", "A", "current")):
                put(f"{prefix}({jj}|XBVM{index})", "boundary", quantity, unit)
        for branch in ("L_S1", "L_S2", "L_S3", "R_S", "L_PSL", "R_SL", "L_SL"):
            for prefix, unit, quantity in (("I", "A", "current"), ("V", "V", "voltage")):
                put(f"{prefix}({branch}|XBVM{index})", "boundary", quantity, unit)
    put("V(COMMON_SL)", "boundary", "voltage", "V")
    for index in range(1, 9):
        for prefix, unit, quantity in (("P", "rad", "phase"), ("V", "V", "voltage"), ("I", "A", "current")):
            put(f"{prefix}(B_JSL{index})", "boundary", quantity, unit)
    put("V(QBIN)", "boundary", "voltage", "V")
    for jj in ("BJS", "BJ1", "BJ2"):
        for prefix, unit, quantity in (("P", "rad", "phase"), ("V", "V", "voltage"), ("I", "A", "current")):
            put(f"{prefix}({jj}|XBQ1)", "qb", quantity, unit)
    for branch in ("LIN", "L1", "L2", "L3", "RJ1", "RJ2", "IB"):
        for prefix, unit, quantity in (("I", "A", "current"), ("V", "V", "voltage")):
            put(f"{prefix}({branch}|XBQ1)", "qb", quantity, unit)
    put("V(QBOUT)", "qb", "voltage", "V")
    for stage in range(1, 7):
        for jj in ("B01", "B02"):
            for prefix, unit, quantity in (("P", "rad", "phase"), ("V", "V", "voltage"), ("I", "A", "current")):
                put(f"{prefix}({jj}|XJTL1_{stage})", "jtl", quantity, unit)
        put(f"V(JTL{stage}_OUT)", "jtl", "voltage", "V")
    put("I(R_TERM)", "jtl", "current", "A")
    put("V(R_TERM)", "jtl", "voltage", "V")
    return definitions


def integrate(times_s: list[float], values: list[float]) -> float:
    return sum((t1 - t0) * (v0 + v1) * 0.5
               for t0, t1, v0, v1 in zip(times_s, times_s[1:], values, values[1:]))


def indices_in(times_ps: list[float], window: list[float]) -> list[int]:
    start, end = window
    return [i for i, time_ps in enumerate(times_ps) if start <= time_ps < end]


def window_summary(name: str, bounds: list[float], indices: list[int], times_ps: list[float],
                   rows: list[dict[str, float]], unwrapped: dict[str, list[float]],
                   definitions: dict[str, dict[str, str]], baseline: dict[str, float] | None) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    result: dict[str, Any] = {"name": name, "registered_window_ps": bounds,
                              "semantics": "half-open; actual stored samples only",
                              "sample_count": len(indices),
                              "actual_first_sample_ps": times_ps[indices[0]] if indices else None,
                              "actual_last_sample_ps": times_ps[indices[-1]] if indices else None,
                              "signals": {}}
    rows_out: list[dict[str, Any]] = []
    for signal, info in definitions.items():
        available = indices
        if not available:
            value = None
        else:
            series = unwrapped[signal] if info["quantity"] == "phase" else [row[signal] for row in rows]
            value = statistics.median(series[i] for i in available)
        delta = value - baseline[signal] if value is not None and baseline and signal in baseline else None
        result["signals"][signal] = {"component_group": info["group"], "quantity": info["quantity"],
                                     "unit": info["unit"], "median": value,
                                     "delta_from_PRE1": delta}
        rows_out.append({"window": name, "window_start_ps": bounds[0], "window_end_ps": bounds[1],
                         "actual_first_sample_ps": result["actual_first_sample_ps"],
                         "actual_last_sample_ps": result["actual_last_sample_ps"],
                         "sample_count": len(indices), "signal": signal,
                         "component_group": info["group"], "quantity": info["quantity"],
                         "unit": info["unit"], "median": value, "delta_from_PRE1": delta})
    return result, rows_out


def phase_area_crosscheck(headers: list[str], rows: list[dict[str, float]], times_ps: list[float],
                          unwrapped: dict[str, list[float]], phase_signal: str,
                          voltage_signal: str, window: list[float]) -> dict[str, Any]:
    idx = indices_in(times_ps, window)
    if phase_signal not in headers or voltage_signal not in headers or len(idx) < 2:
        return {"status": "UNKNOWN", "phase_signal": phase_signal, "voltage_signal": voltage_signal,
                "registered_window_ps": window, "sample_count": len(idx)}
    t0, t1 = idx[0], idx[-1]
    delta_rad = unwrapped[phase_signal][t1] - unwrapped[phase_signal][t0]
    voltage_area = integrate([rows[i]["time"] for i in idx], [rows[i][voltage_signal] for i in idx])
    return {"status": "RECORDED", "phase_signal": phase_signal, "voltage_signal": voltage_signal,
            "registered_window_ps": window, "actual_first_sample_ps": times_ps[t0],
            "actual_last_sample_ps": times_ps[t1], "sample_count": len(idx),
            "delta_phase_rad": delta_rad,
            "phase_delta_turns_navigation": delta_rad / (2.0 * math.pi),
            "voltage_area_v_s": voltage_area, "voltage_area_phi0": voltage_area / PHI0,
            "phase_area_residual_turns_navigation": delta_rad / (2.0 * math.pi) - voltage_area / PHI0,
            "integration_grid": "actual stored rows; no interpolation"}


def candidate_clusters(times_ps: list[float], rows: list[dict[str, float]], signal: str,
                       threshold_v: float, merge_gap_ps: float, candidate_prefix: str) -> list[dict[str, Any]]:
    clusters: list[list[tuple[int, float, float]]] = []
    active: list[tuple[int, float, float]] = []
    last_above_ps: float | None = None
    for index, row in enumerate(rows):
        time_ps = times_ps[index]
        voltage = row[signal]
        if voltage >= threshold_v:
            if active and last_above_ps is not None and time_ps - last_above_ps > merge_gap_ps:
                clusters.append(active)
                active = []
            active.append((index, time_ps, voltage))
            last_above_ps = time_ps
        elif active and last_above_ps is not None and time_ps - last_above_ps > merge_gap_ps:
            clusters.append(active)
            active = []
            last_above_ps = None
    if active:
        clusters.append(active)
    result: list[dict[str, Any]] = []
    for ordinal, cluster in enumerate(clusters, start=1):
        peak = max(cluster, key=lambda item: item[2])
        result.append({"candidate_id": f"{candidate_prefix}{ordinal:04d}",
                       "start_ps": cluster[0][1], "end_ps": cluster[-1][1],
                       "peak_time_ps": peak[1], "peak_voltage_v": peak[2],
                       "sample_count_above_threshold": len(cluster),
                       "threshold_v": threshold_v, "merge_gap_ps": merge_gap_ps,
                       "candidate_only_not_event_count": True})
    return result


def cycle_for_time(time_ps: float, cycles: list[dict[str, Any]]) -> int | None:
    for cycle in cycles:
        start, end = cycle["cycle_window_ps"]
        if start <= time_ps < end:
            return int(cycle["cycle_index"])
    return None


def assign_candidates(upstream_all: list[dict[str, Any]], terminal: list[dict[str, Any]],
                      cycles: list[dict[str, Any]], latency_min: float, latency_max: float) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    upstream = []
    for item in upstream_all:
        cycle = cycle_for_time(item["peak_time_ps"], cycles)
        if cycle is not None:
            upstream.append({**item, "read_cycle_index": cycle})
    possible: dict[str, list[dict[str, Any]]] = {}
    reverse: dict[str, list[str]] = {item["candidate_id"]: [] for item in terminal}
    for source in upstream:
        matches = [target for target in terminal
                   if latency_min <= target["peak_time_ps"] - source["peak_time_ps"] <= latency_max]
        possible[source["candidate_id"]] = matches
        for target in matches:
            reverse[target["candidate_id"]].append(source["candidate_id"])

    rows: list[dict[str, Any]] = []
    assigned_pairs: list[tuple[float, float, str, str]] = []
    for source in upstream:
        matches = possible[source["candidate_id"]]
        common = {"upstream_candidate_id": source["candidate_id"],
                  "upstream_event_time_ps": source["peak_time_ps"],
                  "upstream_candidate_start_ps": source["start_ps"],
                  "upstream_candidate_end_ps": source["end_ps"],
                  "read_cycle_index": source["read_cycle_index"],
                  "possible_terminal_candidate_ids": [m["candidate_id"] for m in matches]}
        if not matches:
            rows.append({**common, "terminal_candidate_id": None, "terminal_event_time_ps": None,
                         "terminal_observed_cycle_index": None,
                         "latency_ps": None, "assignment_status": "NO_TERMINAL_CANDIDATE_IN_SEARCH_WINDOW"})
        elif len(matches) > 1:
            rows.append({**common, "terminal_candidate_id": None, "terminal_event_time_ps": None,
                         "terminal_observed_cycle_indices": [cycle_for_time(m["peak_time_ps"], cycles) for m in matches],
                         "terminal_observed_cycle_index": None,
                         "latency_ps": None, "assignment_status": "AMBIGUOUS_MULTIPLE_TERMINAL_CANDIDATES"})
        elif len(reverse[matches[0]["candidate_id"]]) > 1:
            rows.append({**common, "terminal_candidate_id": None, "terminal_event_time_ps": None,
                         "terminal_observed_cycle_index": cycle_for_time(matches[0]["peak_time_ps"], cycles),
                         "latency_ps": None, "assignment_status": "AMBIGUOUS_SHARED_TERMINAL_CANDIDATE"})
        else:
            target = matches[0]
            assigned_pairs.append((source["peak_time_ps"], target["peak_time_ps"],
                                   source["candidate_id"], target["candidate_id"]))
            rows.append({**common, "terminal_candidate_id": target["candidate_id"],
                         "terminal_event_time_ps": target["peak_time_ps"],
                         "terminal_observed_cycle_index": cycle_for_time(target["peak_time_ps"], cycles),
                         "latency_ps": target["peak_time_ps"] - source["peak_time_ps"],
                         "assignment_status": "ASSIGNED_PENDING_MONOTONICITY"})

    # Any crossing between individually unique links invalidates both links.
    by_source_time = sorted(assigned_pairs)
    bad_sources: set[str] = set()
    for left, right in zip(by_source_time, by_source_time[1:]):
        if right[1] <= left[1]:
            bad_sources.update((left[2], right[2]))
    for row in rows:
        if row["upstream_candidate_id"] in bad_sources:
            row.update({"terminal_candidate_id": None, "terminal_event_time_ps": None,
                        "latency_ps": None, "assignment_status": "AMBIGUOUS_MONOTONIC_ORDER"})
        elif row["assignment_status"] == "ASSIGNED_PENDING_MONOTONICITY":
            row["assignment_status"] = "ASSIGNED_UNIQUE_MONOTONIC"

    assigned_targets = {row["terminal_candidate_id"]: row["upstream_candidate_id"]
                        for row in rows if row["assignment_status"] == "ASSIGNED_UNIQUE_MONOTONIC"}
    terminal_rows = []
    for item in terminal:
        sources = reverse[item["candidate_id"]]
        terminal_rows.append({**item,
                              "terminal_observed_cycle_index": cycle_for_time(item["peak_time_ps"], cycles),
                              "possible_upstream_candidate_ids": sources,
                              "assigned_upstream_candidate_id": assigned_targets.get(item["candidate_id"]),
                              "assignment_status": "ASSIGNED_UNIQUE_MONOTONIC" if item["candidate_id"] in assigned_targets
                              else "AMBIGUOUS_POSSIBLE_MATCH" if sources else "UNMATCHED_NO_UPSTREAM_CANDIDATE"})
    assigned_order = [row for row in rows if row["assignment_status"] == "ASSIGNED_UNIQUE_MONOTONIC"]
    assigned_order.sort(key=lambda row: row["upstream_event_time_ps"])
    monotonic = all(a["terminal_event_time_ps"] < b["terminal_event_time_ps"]
                    for a, b in zip(assigned_order, assigned_order[1:]))
    unique_terminal_ids = len(assigned_targets) == len(set(assigned_targets))
    qa = {"status": "PASS" if monotonic and unique_terminal_ids else "FAIL",
          "assigned_pair_count": len(assigned_order), "assigned_terminal_ids_unique": unique_terminal_ids,
          "assigned_pairs_monotonic": monotonic, "ambiguous_upstream_candidate_count": sum(
              row["assignment_status"].startswith("AMBIGUOUS") for row in rows),
          "candidate_only_not_event_or_sfq_count": True,
          "latency_search_window_ps": [latency_min, latency_max]}
    return rows, terminal_rows, qa


def assign_jtl_candidate_paths(assignments: list[dict[str, Any]],
                               jtl_candidates: dict[str, list[dict[str, Any]]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Describe a strict 12-junction candidate chain between BJ2 and terminal."""
    nodes = [(stage, junction) for stage in range(1, 7) for junction in ("B01", "B02")]
    paths: list[dict[str, Any]] = []
    for upstream in assignments:
        row: dict[str, Any] = {
            "upstream_candidate_id": upstream["upstream_candidate_id"],
            "upstream_event_time_ps": upstream["upstream_event_time_ps"],
            "upstream_read_cycle_index": upstream["read_cycle_index"],
            "terminal_candidate_id": upstream.get("terminal_candidate_id"),
            "terminal_event_time_ps": upstream.get("terminal_event_time_ps"),
            "terminal_observed_cycle_index": upstream.get("terminal_observed_cycle_index"),
            "terminal_assignment_status": upstream["assignment_status"],
            "jtl_path_status": "UPSTREAM_TERMINAL_AMBIGUOUS",
        }
        for stage, junction in nodes:
            node = f"JTL{stage}_{junction}"
            row[f"{node}_candidate_id"] = None
            row[f"{node}_candidate_time_ps"] = None
        if upstream["assignment_status"] != "ASSIGNED_UNIQUE_MONOTONIC":
            paths.append(row)
            continue
        cursor = float(upstream["upstream_event_time_ps"])
        terminal_time = float(upstream["terminal_event_time_ps"])
        status = "UNIQUE_MONOTONIC_CANDIDATE_PATH"
        for stage, junction in nodes:
            node = f"JTL{stage}_{junction}"
            candidates = [item for item in jtl_candidates[node]
                          if cursor < float(item["peak_time_ps"]) < terminal_time]
            if not candidates:
                status = f"INCOMPLETE_NO_{node}_CANDIDATE"
                break
            if len(candidates) > 1:
                status = f"AMBIGUOUS_MULTIPLE_{node}_CANDIDATES"
                break
            selected = candidates[0]
            row[f"{node}_candidate_id"] = selected["candidate_id"]
            row[f"{node}_candidate_time_ps"] = selected["peak_time_ps"]
            cursor = float(selected["peak_time_ps"])
        row["jtl_path_status"] = status
        paths.append(row)

    candidate_users: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for path in paths:
        if path["jtl_path_status"] != "UNIQUE_MONOTONIC_CANDIDATE_PATH":
            continue
        for stage, junction in nodes:
            node = f"JTL{stage}_{junction}"
            candidate_users.setdefault((node, path[f"{node}_candidate_id"]), []).append(path)
    for (node, _candidate_id), users in candidate_users.items():
        if len(users) > 1:
            for path in users:
                path["jtl_path_status"] = f"AMBIGUOUS_SHARED_{node}_CANDIDATE"

    accepted = [path for path in paths if path["jtl_path_status"] == "UNIQUE_MONOTONIC_CANDIDATE_PATH"]
    accepted_keys = [(f"JTL{stage}_{junction}", path[f"JTL{stage}_{junction}_candidate_id"])
                     for path in accepted for stage, junction in nodes]
    no_reuse = len(accepted_keys) == len(set(accepted_keys))
    strict_order = all(
        float(path[f"JTL{left_stage}_{left_junction}_candidate_time_ps"]) <
        float(path[f"JTL{right_stage}_{right_junction}_candidate_time_ps"])
        for path in accepted
        for (left_stage, left_junction), (right_stage, right_junction) in zip(nodes, nodes[1:]))
    invariant_status = "PASS" if no_reuse and strict_order else "FAIL"
    path_status = "COMPLETE_PATHS_OBSERVED" if accepted else "NO_COMPLETE_PATH_OBSERVED"
    qa = {"status": path_status, "invariant_status": invariant_status,
          "complete_unique_path_count": len(accepted),
          "ambiguous_or_incomplete_path_count": len(paths) - len(accepted),
          "accepted_paths_use_unique_jtl_node_candidates": no_reuse,
          "accepted_paths_are_strictly_monotonic": strict_order,
          "ambiguous_or_incomplete_paths_retained": True,
          "phase_or_voltage_candidates_are_not_sfq_counts": True}
    return paths, qa


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def analyze_run(run_dir: Path) -> dict[str, Any]:
    resolved_run_dir = resolve_run_dir(run_dir.name)
    if run_dir.resolve() != resolved_run_dir:
        raise ValueError("analysis path must resolve to one direct child under this experiment's runs/")
    run_dir = resolved_run_dir
    raw = run_dir / "raw.csv"
    before_sha = sha256(raw)
    metadata = read_json(run_dir / "metadata.json")
    solve_raw_sha = metadata.get("raw", {}).get("sha256")
    if not solve_raw_sha or before_sha != solve_raw_sha:
        raise ValueError(f"raw SHA-256 differs from solve-time metadata; refuse analysis: expected={solve_raw_sha}, actual={before_sha}")
    snapshot = read_json(run_dir / "stimulus_snapshot.json")
    params = metadata["parameters"]
    headers, rows = load_raw(raw)
    times_ps = [row["time"] * 1e12 for row in rows]
    if len(rows) < 2 or any(b <= a for a, b in zip(times_ps, times_ps[1:])):
        raise ValueError("raw time grid must contain at least two strictly increasing stored samples")
    if any(not math.isfinite(t) for t in times_ps):
        raise ValueError("raw time column contains non-finite values")
    dt_ps = [b - a for a, b in zip(times_ps, times_ps[1:])]
    median_dt = statistics.median(dt_ps)
    irregular_count = sum(abs(step - median_dt) > max(1e-9, abs(median_dt) * 1e-6) for step in dt_ps)
    actual_stop_ps = float(params["STOP_PS"])
    if times_ps[-1] > actual_stop_ps + median_dt or times_ps[-1] < actual_stop_ps - 2 * median_dt:
        raise ValueError(f"actual raw range ends at {times_ps[-1]:g} ps, outside planned STOP={actual_stop_ps:g} ps")

    requested = legacy.requested_signals("closed", params)
    requested_names = list(dict.fromkeys(item[0] for item in requested))
    unsupported = {signal: info for signal, info in KNOWN_UNSUPPORTED_RAW_SIGNALS.items()
                   if signal in requested_names and signal not in headers}
    missing = [signal for signal in requested_names if signal not in headers and signal not in unsupported]
    if missing:
        raise ValueError(f"required probe columns absent from raw: {missing[:12]}")
    signal_descriptions = {signal: {"component_group": subsystem, "physical_quantity": quantity}
                           for signal, subsystem, quantity in requested}
    signal_manifest_rows = []
    for signal in requested_names:
        status = "PRESENT" if signal in headers else "UNKNOWN"
        signal_manifest_rows.append({"raw_column": signal,
                                     **signal_descriptions.get(signal, {}),
                                     "status": status,
                                     "reason": unsupported.get(signal, {}).get("reason", "")})
    stderr_path = run_dir / "stderr.txt"
    stderr_text = stderr_path.read_text(encoding="utf-8", errors="replace") if stderr_path.is_file() else ""
    warning_lines = [line.strip() for line in stderr_text.splitlines()
                     if any(token in line for token in ("Unknown device/node", "Cannot store results for this device/node.",
                                                        "Ignoring this store request."))]
    expected_warning_lines = {line for item in KNOWN_UNSUPPORTED_RAW_SIGNALS.values()
                              for line in item["expected_warning_lines"]}
    unexpected_warning_lines = [line for line in warning_lines if line not in expected_warning_lines]
    expected_unknown_nodes = [signal[2:-1] for signal in unsupported]
    if any(not any(node in line for node in expected_unknown_nodes) for line in warning_lines if "Unknown device/node" in line):
        unexpected_warning_lines.extend(line for line in warning_lines
                                        if "Unknown device/node" in line and line not in unexpected_warning_lines)
    solver_warning_qa = {
        "schema": "bvm-qb-repeatability-solver-warning-qa-v1",
        "status": "PASS" if not unexpected_warning_lines else "FAIL",
        "stderr_path": str(stderr_path),
        "stderr_sha256": sha256(stderr_path) if stderr_path.is_file() else None,
        "observed_probe_warning_lines": warning_lines,
        "known_unsupported_raw_columns": sorted(unsupported),
        "unsupported_columns_are_explicit_unknown": True,
        "unexpected_warning_lines": sorted(set(unexpected_warning_lines)),
        "scientific_interpretation_performed": False,
    }

    definitions = signal_definitions(params)
    definitions = {key: val for key, val in definitions.items() if key in headers}
    phase_columns = [key for key, info in definitions.items() if info["quantity"] == "phase"]
    unwrapped = {key: unwrap([row[key] for row in rows]) for key in phase_columns}
    cycles = snapshot["registered_windows"]
    if not cycles:
        raise ValueError("stimulus snapshot has no registered READ cycle windows")
    phase_checks: list[dict[str, Any]] = []
    cycle_results: list[dict[str, Any]] = []
    state_rows: list[dict[str, Any]] = []
    first_pre_indices = indices_in(times_ps, cycles[0]["pre_window_ps"])
    if not first_pre_indices:
        raise ValueError("PRE_1 has no stored samples")
    baseline: dict[str, float] = {}
    for signal, info in definitions.items():
        values = unwrapped[signal] if info["quantity"] == "phase" else [row[signal] for row in rows]
        baseline[signal] = statistics.median(values[index] for index in first_pre_indices)

    for cycle in cycles:
        cycle_index = int(cycle["cycle_index"])
        bounds = cycle["cycle_window_ps"]
        cycle_idx = indices_in(times_ps, bounds)
        if len(cycle_idx) < 2:
            raise ValueError(f"cycle {cycle_index} has fewer than two actual stored samples")
        cycle_record: dict[str, Any] = {"cycle_index": cycle_index,
                                        "read_start_ps": cycle["read_start_ps"],
                                        "read_end_ps": cycle["read_end_ps"],
                                        "upstream_cycle_window_ps": bounds,
                                        "upstream_cycle_window_semantics": cycle["cycle_window_semantics"],
                                        "cycle_sample_count": len(cycle_idx),
                                        "actual_first_sample_ps": times_ps[cycle_idx[0]],
                                        "actual_last_sample_ps": times_ps[cycle_idx[-1]],
                                        "phase_area_crosschecks": {}}
        for junction in ("BJ1", "BJ2"):
            p_signal = f"P({junction}|XBQ1)"
            v_signal = f"V({junction}|XBQ1)"
            check = phase_area_crosscheck(headers, rows, times_ps, unwrapped,
                                          p_signal, v_signal, bounds)
            cycle_record["phase_area_crosschecks"][junction] = check
        cycle_results.append(cycle_record)

        for window_name, window_bounds, virtual in (
            ("PRE", cycle["pre_window_ps"], False),
            ("READ", cycle["read_window_ps"], False),
            ("POST", cycle["post_window_ps"], False),
            ("NEXT_PRE", cycle["next_pre_window_ps"], cycle["next_pre_is_virtual"]),
        ):
            indices = indices_in(times_ps, window_bounds)
            if not indices:
                raise ValueError(f"{window_name}_{cycle_index} has no actual stored samples")
            summary, csv_rows = window_summary(f"{window_name}_{cycle_index}", window_bounds,
                                               indices, times_ps, rows, unwrapped,
                                               definitions, baseline)
            summary["read_cycle_index"] = cycle_index
            summary["virtual_next_read_anchor"] = bool(virtual)
            cycle_record.setdefault("state_windows", {})[window_name] = summary
            for row in csv_rows:
                row["read_cycle_index"] = cycle_index
                row["virtual_next_read_anchor"] = bool(virtual)
            state_rows.extend(csv_rows)

    # Navigation-only upstream and terminal candidates; no event/SFQ classification.
    upstream = candidate_clusters(times_ps, rows, "V(BJ2|XBQ1)",
                                  float(params["BJ2_CANDIDATE_THRESHOLD_UV"]) * 1e-6,
                                  float(params["BJ2_CANDIDATE_GAP_PS"]), "BJ2C")
    terminal = candidate_clusters(times_ps, rows, "V(R_TERM)",
                                  float(params["TERMINAL_CANDIDATE_THRESHOLD_UV"]) * 1e-6,
                                  float(params["TERMINAL_CANDIDATE_GAP_PS"]), "TERMC")
    assignments, terminal_rows, assignment_qa = assign_candidates(
        upstream, terminal, cycles, float(params["LATENCY_MIN_PS"]), float(params["LATENCY_MAX_PS"]))
    jtl_candidates: dict[str, list[dict[str, Any]]] = {}
    for stage in range(1, 7):
        for junction in ("B01", "B02"):
            node = f"JTL{stage}_{junction}"
            jtl_candidates[node] = candidate_clusters(
                times_ps, rows, f"V({junction}|XJTL1_{stage})",
                float(params["TERMINAL_CANDIDATE_THRESHOLD_UV"]) * 1e-6,
                float(params["TERMINAL_CANDIDATE_GAP_PS"]), f"{node}C")
    jtl_paths, jtl_path_qa = assign_jtl_candidate_paths(assignments, jtl_candidates)

    # Recovery deltas use the PRE_1 median. Keep units separate in every vector norm.
    recovery_start = float(cycles[0]["read_end_ps"])
    trace_indices = [i for i, time_ps in enumerate(times_ps) if recovery_start <= time_ps <= actual_stop_ps]
    component_columns: list[str] = []
    component_rows: list[dict[str, Any]] = []
    distance_keys: list[tuple[str, str, list[str]]] = []
    for group in ("storage", "boundary", "qb", "jtl"):
        for quantity, unit, suffix in (("phase", "rad", "phase_rad"),
                                       ("current", "A", "current_A"),
                                       ("voltage", "V", "voltage_V")):
            signals = [key for key, info in definitions.items()
                       if info["group"] == group and info["quantity"] == quantity]
            if signals:
                distance_keys.append((group, suffix, signals))
                component_columns.extend([f"delta__{key}" for key in signals])
    trace_fieldnames = ["time_ps"] + component_columns + [f"D_{group}_{suffix}_L2" for group, suffix, _ in distance_keys]
    for i in trace_indices:
        entry: dict[str, Any] = {"time_ps": times_ps[i]}
        for signal, info in definitions.items():
            if signal not in baseline:
                continue
            series = unwrapped[signal] if info["quantity"] == "phase" else None
            value = series[i] if series is not None else rows[i][signal]
            entry[f"delta__{signal}"] = value - baseline[signal]
        for group, suffix, signals in distance_keys:
            deltas = [entry[f"delta__{signal}"] for signal in signals]
            entry[f"D_{group}_{suffix}_L2"] = math.sqrt(sum(value * value for value in deltas))
        component_rows.append(entry)

    terminal_ids = [row["terminal_candidate_id"] for row in assignments
                    if row["assignment_status"] == "ASSIGNED_UNIQUE_MONOTONIC"]
    assignment_qa["assigned_terminal_candidates_never_reused"] = len(terminal_ids) == len(set(terminal_ids))
    assignment_qa["status"] = "PASS" if assignment_qa["status"] == "PASS" and assignment_qa["assigned_terminal_candidates_never_reused"] else "FAIL"

    analysis_dir = run_dir / "analysis"
    analysis_dir.mkdir(exist_ok=True)
    signal_manifest_path = analysis_dir / "signal_manifest.csv"
    write_csv(signal_manifest_path,
              ["raw_column", "component_group", "physical_quantity", "status", "reason"],
              signal_manifest_rows)
    write_json(analysis_dir / "solver_warning_qa.json", solver_warning_qa)

    raw_qa = {
        "schema": "bvm-qb-repeatability-raw-qa-v1", "status": "PASS",
        "raw_sha256": before_sha, "sample_count": len(rows), "column_count": len(headers),
        "time_start_ps": times_ps[0], "time_end_ps": times_ps[-1],
        "planned_stop_ps": actual_stop_ps, "median_dt_ps": median_dt,
        "irregular_step_count": irregular_count, "finite_values": True,
        "strictly_increasing_time": True, "requested_probe_count": len(requested_names),
        "required_probe_count": len(requested_names) - len(unsupported),
        "missing_required_probes": [],
        "known_unsupported_probe_columns": sorted(unsupported),
        "raw_immutable": True,
    }
    analysis_qa = {"schema": "bvm-qb-repeatability-analysis-qa-v1",
                   "status": "PASS" if assignment_qa["status"] == "PASS" and jtl_path_qa["invariant_status"] == "PASS" and solver_warning_qa["status"] == "PASS" and len(cycle_results) == len(cycles) else "FAIL",
                   "raw_sha256_before_after": {"before": before_sha, "after": sha256(raw)},
                   "raw_unchanged": before_sha == sha256(raw),
                   "cycles_nonoverlapping": all(cycles[i]["cycle_window_ps"][1] <= cycles[i + 1]["cycle_window_ps"][0]
                                                 for i in range(len(cycles) - 1)),
                   "phase_area_same_jj_same_window_actual_grid": True,
                   "interpolation_or_resampling": False,
                   "candidate_assignment": assignment_qa,
                   "jtl_candidate_path_qa": jtl_path_qa,
                   "solver_warning_qa": solver_warning_qa["status"],
                   "unsupported_probe_columns_recorded_unknown": sorted(unsupported),
                   "signal_manifest_sha256": sha256(analysis_dir / "signal_manifest.csv"),
                   "scientific_interpretation_performed": False,
                   "phase_turns_are_navigation_only": True}
    if not analysis_qa["raw_unchanged"]:
        analysis_qa["status"] = "FAIL"

    write_json(analysis_dir / "raw_qa.json", raw_qa)
    write_json(analysis_dir / "cycle_metrics.json", {
        "schema": "bvm-qb-repeatability-cycle-metrics-v1", "run_id": run_dir.name,
        "cycles": cycle_results, "phase_area_semantics": "same JJ, same half-open cycle window, actual stored grid; no interpolation",
        "phase_turns_are_navigation_only": True,
    })
    write_csv(analysis_dir / "cycle_metrics.csv",
              ["cycle_index", "read_start_ps", "read_end_ps", "upstream_cycle_start_ps",
               "upstream_cycle_end_ps", "cycle_sample_count", "actual_first_sample_ps", "actual_last_sample_ps",
               "BJ1_delta_phase_rad", "BJ1_phase_delta_turns_navigation", "BJ1_voltage_area_phi0",
               "BJ2_delta_phase_rad", "BJ2_phase_delta_turns_navigation", "BJ2_voltage_area_phi0"],
              [{"cycle_index": c["cycle_index"], "read_start_ps": c["read_start_ps"],
                "read_end_ps": c["read_end_ps"], "upstream_cycle_start_ps": c["upstream_cycle_window_ps"][0],
                "upstream_cycle_end_ps": c["upstream_cycle_window_ps"][1],
                "cycle_sample_count": c["cycle_sample_count"],
                "actual_first_sample_ps": c["actual_first_sample_ps"], "actual_last_sample_ps": c["actual_last_sample_ps"],
                **{f"{jj}_{key}": c["phase_area_crosschecks"][jj].get(source_key)
                   for jj in ("BJ1", "BJ2")
                   for key, source_key in (("delta_phase_rad", "delta_phase_rad"),
                                           ("phase_delta_turns_navigation", "phase_delta_turns_navigation"),
                                           ("voltage_area_phi0", "voltage_area_phi0"))}}
               for c in cycle_results])
    write_csv(analysis_dir / "state_windows.csv",
              ["read_cycle_index", "window", "window_start_ps", "window_end_ps", "actual_first_sample_ps",
               "actual_last_sample_ps", "sample_count", "signal", "component_group", "quantity", "unit",
               "median", "delta_from_PRE1", "virtual_next_read_anchor"], state_rows)
    write_json(analysis_dir / "event_assignment.json", {
        "schema": "bvm-qb-repeatability-candidate-assignment-v1",
        "upstream_signal": "V(BJ2|XBQ1)", "terminal_signal": "V(R_TERM)",
        "assignment_semantics": "search terminal candidates globally by registered forward latency; a terminal candidate may occur in a later READ cycle than its upstream candidate, and both cycle indices are recorded",
        "candidate_thresholds_and_gap_from_config": {
            "bj2_threshold_uv": params["BJ2_CANDIDATE_THRESHOLD_UV"],
            "bj2_gap_ps": params["BJ2_CANDIDATE_GAP_PS"],
            "terminal_threshold_uv": params["TERMINAL_CANDIDATE_THRESHOLD_UV"],
            "terminal_gap_ps": params["TERMINAL_CANDIDATE_GAP_PS"],
            "latency_search_window_ps": [params["LATENCY_MIN_PS"], params["LATENCY_MAX_PS"]]},
        "upstream_candidate_count_navigation_only": len(upstream),
        "terminal_candidate_count_navigation_only": len(terminal),
        "assignments": assignments, "terminal_candidates": terminal_rows,
        "jtl_stage_candidate_records": jtl_candidates,
        "jtl_candidate_counts_navigation_only": {node: len(items) for node, items in jtl_candidates.items()},
        "jtl_candidate_paths": jtl_paths, "jtl_path_qa": jtl_path_qa,
        "qa": assignment_qa,
        "scientific_interpretation_performed": False,
        "candidate_or_assignment_is_not_sfq_count": True,
    })
    write_csv(analysis_dir / "event_assignment.csv",
              ["upstream_candidate_id", "upstream_event_time_ps", "upstream_candidate_start_ps",
               "upstream_candidate_end_ps", "read_cycle_index", "possible_terminal_candidate_ids",
               "terminal_observed_cycle_index", "terminal_observed_cycle_indices",
               "terminal_candidate_id", "terminal_event_time_ps", "latency_ps", "assignment_status"],
              [{**item,
                "possible_terminal_candidate_ids": ";".join(item["possible_terminal_candidate_ids"]),
                "terminal_observed_cycle_indices": ";".join(str(x) for x in item.get("terminal_observed_cycle_indices", []))}
               for item in assignments])
    write_csv(analysis_dir / "terminal_candidates.csv",
              ["candidate_id", "start_ps", "end_ps", "peak_time_ps", "peak_voltage_v",
               "sample_count_above_threshold", "threshold_v", "merge_gap_ps", "terminal_observed_cycle_index",
               "possible_upstream_candidate_ids", "assigned_upstream_candidate_id", "assignment_status"],
              [{**item, "possible_upstream_candidate_ids": ";".join(item["possible_upstream_candidate_ids"])}
               for item in terminal_rows])
    jtl_path_fields = ["upstream_candidate_id", "upstream_event_time_ps", "upstream_read_cycle_index",
                       "terminal_candidate_id", "terminal_event_time_ps", "terminal_observed_cycle_index",
                       "terminal_assignment_status", "jtl_path_status"]
    for stage in range(1, 7):
        for junction in ("B01", "B02"):
            node = f"JTL{stage}_{junction}"
            jtl_path_fields.extend((f"{node}_candidate_id", f"{node}_candidate_time_ps"))
    write_csv(analysis_dir / "jtl_chain_assignment.csv", jtl_path_fields, jtl_paths)
    recovery_metrics = {
        "schema": "bvm-qb-repeatability-recovery-metrics-v1", "run_id": run_dir.name,
        "reference": "median values in PRE_1; phase values independently unwrapped; raw phase preserved",
        "trace_start_ps": recovery_start, "trace_end_ps": times_ps[trace_indices[-1]] if trace_indices else None,
        "trace_row_count": len(component_rows), "trace_uses_actual_stored_grid": True,
        "distance_definition": "separate Euclidean norms within homogeneous signal units; no cross-unit norm and no recovery threshold",
        "component_signal_count": len(definitions),
        "last_trace_distances": component_rows[-1] if component_rows else None,
        "recovered_boolean": None, "scientific_interpretation_performed": False,
    }
    write_json(analysis_dir / "recovery_metrics.json", recovery_metrics)
    write_csv(analysis_dir / "recovery_trace.csv", trace_fieldnames, component_rows)
    write_json(analysis_dir / "analysis_qa.json", analysis_qa)
    if sha256(raw) != before_sha:
        raise ValueError("raw SHA-256 changed during analysis")
    return analysis_qa


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze one saved run without running JoSIM")
    parser.add_argument("run_id", help="directory name under runs/")
    args = parser.parse_args()
    qa = analyze_run(resolve_run_dir(args.run_id))
    print(json.dumps(qa, ensure_ascii=False, indent=2))
    return 0 if qa["status"] == "PASS" else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
