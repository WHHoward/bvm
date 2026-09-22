#!/usr/bin/env python3
"""Registered BVM/QB repeated-read, rewrite/read, MERGE, and conditional integration runner."""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from statistics import median
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPO = next(path for path in (ROOT, *ROOT.parents) if (path / ".git").exists())
OLD_SERIES = REPO / "test" / "exploration" / "bvm-rloop-one-shot-tuning-v1-20260918"
OLD_SCRIPTS = OLD_SERIES / "scripts"
sys.path.insert(0, str(OLD_SCRIPTS))
spec = importlib.util.spec_from_file_location("legacy_platform", OLD_SCRIPTS / "run_candidate.py")
if spec is None or spec.loader is None:
    raise RuntimeError("cannot load existing BVM/QB runner")
legacy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(legacy)

PHI0 = 2.067833848e-15
SOLVER = REPO / "build" / "josim-cli"
PLOTTER = REPO / "scripts" / "josim-plot2.py"
MERGE_SOURCE = REPO / "circuits" / "standard" / "MERGE.cir"
CANDIDATE_JTL_SOURCE = REPO / "test" / "exploration" / "bvm-qb-l1-l3-bj2-targeted-closure-v1-20260914" / "inputs" / "jtl2.cir"
MERGE_JTL_SOURCE = REPO / "circuits" / "standard" / "JTL.cir"
JJ_SOURCE = REPO / "circuits" / "models" / "jjmit.cir"

BASE = {
    "NAME": "bvm_qb_50ghz_merge",
    "MODE": "closed",
    "JM1_AREA": "1.2", "JM2_AREA": "1.4", "RJM1": "8", "RJM2": "OPEN",
    "LM1": "12.5p", "LM2": "24.5p", "LM3": "8.5p", "LPM": "0.5p",
    "RSH_JS1": "OPEN", "RSH_JS2": "OPEN",
    "LS1": "0.5p", "LS2": "0.5p", "LS3": "0.5p", "RS": "3.0",
    "LPSL": "0.5p", "RSL": "12.0", "LSL": "0.4p",
    "RBL": "20.0", "LPBL": "0.5p", "RWL": "20.0", "LPWL": "0.5p",
    "RSE": "20.0", "LPSE": "0.5p",
    "QB_LIN": "1.5p", "QB_BJS_AREA": "4.0", "QB_L1": "1.4p", "QB_L2": "2.0p",
    "QB_RJ1": "32", "QB_BJ2_AREA": "2.0", "QB_RJ2": "12", "QB_L3": "1.3p", "QB_IB": "260u",
    "DT": "0.1p",
}
CANDIDATES = {
    "QB_1X1": {"ARRAY_SIZE": 1, "JS1_AREA": "0.90", "JS2_AREA": "0.90", "QB_BJ1_AREA": "1.0"},
    "QB_2X1": {"ARRAY_SIZE": 2, "JS1_AREA": "0.90", "JS2_AREA": "0.90", "QB_BJ1_AREA": "0.85"},
    "QB_3X1": {"ARRAY_SIZE": 3, "JS1_AREA": "0.86", "JS2_AREA": "0.86", "QB_BJ1_AREA": "0.85"},
}
READ_STARTS = (110.0, 130.0, 150.0, 170.0, 190.0)
READ_WIDTH = 11.0
RESPONSE_OFFSET = (15.0, 45.0)
TERMINAL_THRESHOLD_V = 0.1e-3
TERMINAL_GAP_PS = 0.5
PHASE_A_MASKS = {"QB_1X1": ("0", "1"), "QB_2X1": ("00", "01", "10", "11"), "QB_3X1": tuple(f"{i:03b}" for i in range(8))}
REWRITE_SEQUENCES = {"QB_1X1": ("0", "1", "0", "1"), "QB_2X1": ("00", "01", "11", "00", "01"), "QB_3X1": ("000", "001", "011", "111", "000")}
MERGE_DELTAS = (0.0, 0.5, -0.5, 1.0, -1.0, 2.0, -2.0, 3.0, -3.0, 4.0, -4.0, 6.0, -6.0)
INTEGRATION_MASKS = ("0000", "0001", "0100", "0011", "0101", "0111", "1101", "1111")


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def repo_rel(path: Path) -> str:
    return path.resolve().relative_to(REPO.resolve()).as_posix()


def git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()


def git_status() -> str:
    return subprocess.check_output(["git", "status", "--short", "--untracked-files=all"], cwd=REPO, text=True)


def source_record(role: str, path: Path) -> dict[str, Any]:
    return {"role": role, "path": repo_rel(path), "sha256": sha256(path), "bytes": path.stat().st_size}


def candidate_params(candidate: str, array_size: int | None = None) -> dict[str, Any]:
    if candidate not in CANDIDATES:
        raise RuntimeError(f"unknown candidate {candidate}")
    p = dict(BASE)
    p.update(CANDIDATES[candidate])
    if array_size is not None:
        p["ARRAY_SIZE"] = array_size
    p["BIT_ORDER"] = legacy.fan_in.bit_order(int(p["ARRAY_SIZE"]))
    p["MASKS"] = []
    p["STOP"] = "240p"
    return p


def fmt_time(ps: float) -> str:
    if abs(ps) < 1e-12:
        return "0"
    return f"{ps:g}p"


def fmt_current(ua: float) -> str:
    if abs(ua) < 1e-15:
        return "0"
    return f"{ua:+g}u"


def stage(points: list[tuple[float, float]], start: float, end: float, amp: float, ramp: float = 1.0) -> None:
    points.extend(((start, 0.0), (start + ramp, amp), (end - ramp, amp), (end, 0.0)))


def stimulus_line(signal: str, points: list[tuple[float, float]], stop: float) -> str:
    normalized: list[tuple[float, float]] = []
    for point in sorted(points + [(stop, 0.0)], key=lambda item: item[0]):
        if normalized and abs(normalized[-1][0] - point[0]) < 1e-12 and abs(normalized[-1][1] - point[1]) < 1e-18:
            continue
        normalized.append(point)
    values = " ".join(f"{fmt_time(t)} {fmt_current(i)}" for t, i in normalized)
    return f"I_{signal} 0 {signal} pwl({values})"


def repeated_stimulus(p: dict[str, Any], mask: str) -> tuple[str, list[float]]:
    size = int(p["ARRAY_SIZE"])
    stop = 240.0
    lines = [f"* Phase A repeated-read; candidate={p['CANDIDATE']}; mask={mask}; {p['BIT_ORDER']}", "* five reads at 20 ps cadence; no rewrite after WRITE1."]
    for index in range(1, size + 1):
        active = mask[index - 1] == "1"
        for signal in ("WL", "BL", "SE"):
            points: list[tuple[float, float]] = [(0.0, 0.0)]
            stage(points, 50.0, 61.0, -100.0 if signal in ("WL", "BL") else 0.0)
            stage(points, 70.0, 81.0, 100.0 if signal in ("WL", "SE") else 0.0)
            stage(points, 90.0, 101.0, 100.0 if signal in ("WL", "BL") else 0.0)
            for start in READ_STARTS:
                stage(points, start, start + READ_WIDTH, 100.0 if active and signal in ("WL", "SE") else 0.0)
            lines.append(stimulus_line(f"{signal}{index}", points, stop))
    return "\n".join(lines) + "\n", list(READ_STARTS)


def rewrite_stimulus(p: dict[str, Any], sequence: tuple[str, ...]) -> tuple[str, list[dict[str, Any]]]:
    size = int(p["ARRAY_SIZE"])
    stop = 430.0 if size > 1 else 360.0
    lines = [f"* Phase B rewrite/read; candidate={p['CANDIDATE']}; sequence={' -> '.join(sequence)}; {p['BIT_ORDER']}", "* Each state: reset WRITE0 all cells, WRITE1 target-one cells, then read target-one cells."]
    points_by_signal = {(index, signal): [(0.0, 0.0)] for index in range(1, size + 1) for signal in ("WL", "BL", "SE")}
    records: list[dict[str, Any]] = []
    base = 50.0
    for ordinal, state in enumerate(sequence, start=1):
        reset_start = base
        write1_start = base + 20.0
        read_start = base + 45.0
        for index in range(1, size + 1):
            one = state[index - 1] == "1"
            for signal in ("WL", "BL", "SE"):
                pts = points_by_signal[(index, signal)]
                stage(pts, reset_start, reset_start + 11.0, -100.0 if signal in ("WL", "BL") else 0.0)
                stage(pts, write1_start, write1_start + 11.0, 100.0 if one and signal in ("WL", "BL") else 0.0)
                stage(pts, read_start, read_start + READ_WIDTH, 100.0 if one and signal in ("WL", "SE") else 0.0)
        records.append({"ordinal": ordinal, "state": state, "population": state.count("1"), "read_start_ps": read_start, "read_end_ps": read_start + READ_WIDTH})
        base += 70.0
    for index in range(1, size + 1):
        for signal in ("WL", "BL", "SE"):
            lines.append(stimulus_line(f"{signal}{index}", points_by_signal[(index, signal)], stop))
    return "\n".join(lines) + "\n", records


def copy_sources(run_dir: Path, p: dict[str, Any], merge: bool = False) -> dict[str, Path]:
    source_dir = run_dir / "snapshot" / "sources"
    source_dir.mkdir(parents=True, exist_ok=False)
    sources: dict[str, Path] = {}
    for role, source in (("JJ_MODEL", JJ_SOURCE), ("JTL", CANDIDATE_JTL_SOURCE)):
        target = source_dir / source.name
        shutil.copy2(source, target)
        sources[role] = target
    bvm = source_dir / "bvm_tunable.cir"
    bvm.write_text(legacy.render_bvm(p), encoding="utf-8")
    sources["BVM"] = bvm
    if not merge:
        qb = source_dir / "bq_tunable.cir"
        qb.write_text(legacy.render_qb(p), encoding="utf-8")
        sources["QB"] = qb
    return sources


def write_source_manifest(run_dir: Path, sources: dict[str, Path], p: dict[str, Any], extra: dict[str, Any] | None = None) -> None:
    records = [source_record(role, path) for role, path in sources.items()]
    data = {"schema": "bvm-qb-50ghz-source-manifest-v1", "experiment": ROOT.name, "parent_head": git_head(), "solver_sha256": sha256(SOLVER), "parameters": p, "sources": records, "raw_not_copied_from_history": True}
    if extra:
        data.update(extra)
    write_json(run_dir / "source_manifest.json", data)


def single_deck(run_dir: Path, p: dict[str, Any], stimulus: Path, sources: dict[str, Path]) -> Path:
    text = legacy.render_deck("closed", p, sources, stimulus, run_dir)
    deck = run_dir / "actual_deck.cir"
    deck.write_text(text, encoding="utf-8")
    (run_dir / "deck.cir").write_text(text, encoding="utf-8")
    return deck


def run_solver(run_dir: Path, deck: Path, phase: str, run_id: str, expected: dict[str, Any]) -> Path:
    raw = run_dir / "raw.csv"
    command = [str(SOLVER), "-a", "1", "-o", str(raw), str(deck)]
    started = now(); clock = time.monotonic()
    completed = subprocess.run(command, cwd=run_dir, capture_output=True, text=True, check=False)
    runtime = time.monotonic() - clock; finished = now()
    (run_dir / "stdout.txt").write_text(completed.stdout, encoding="utf-8")
    (run_dir / "stderr.txt").write_text(completed.stderr, encoding="utf-8")
    (run_dir / "run.log").write_text("\n".join((f"experiment={ROOT.name}", f"phase={phase}", f"run_id={run_id}", f"started_at={started}", f"finished_at={finished}", f"runtime_seconds={runtime:.6f}", f"command={' '.join(command)}", f"exit_code={completed.returncode}", "")), encoding="utf-8")
    metadata = {"schema": "bvm-qb-50ghz-run-metadata-v1", "experiment": ROOT.name, "phase": phase, "run_id": run_id, "parameters": expected.get("parameters", {}), "expected": expected, "command": command, "started_at": started, "finished_at": finished, "runtime_seconds": runtime, "execution_status": "RUN_PASS" if completed.returncode == 0 and raw.is_file() and raw.stat().st_size else "RUN_FAIL", "solver": {"path": repo_rel(SOLVER), "sha256": sha256(SOLVER), "version": subprocess.check_output([str(SOLVER), "--version"], text=True).strip()}}
    if raw.is_file():
        metadata["raw"] = {"path": repo_rel(raw), "sha256": sha256(raw), "bytes": raw.stat().st_size}
    write_json(run_dir / "metadata.json", metadata)
    if completed.returncode != 0 or not raw.is_file() or raw.stat().st_size == 0:
        raise RuntimeError(f"JoSIM failed for {phase}/{run_id}; raw/deck/log preserved at {run_dir}")
    return raw


def load_raw(raw: Path) -> tuple[list[str], list[dict[str, float]]]:
    with raw.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        headers = reader.fieldnames or []
        rows = [{key: float(value) for key, value in row.items() if value not in (None, "")} for row in reader]
    return headers, rows


def raw_qa(raw: Path) -> dict[str, Any]:
    headers, rows = load_raw(raw)
    times = [row["time"] for row in rows if "time" in row]
    finite = all(math.isfinite(value) for row in rows for value in row.values())
    steps = [(b - a) * 1e12 for a, b in zip(times, times[1:])]
    monotonic = all(step > 0 for step in steps)
    nominal = median(steps) if steps else None
    irregular = sum(1 for step in steps if nominal is not None and abs(step - nominal) > 1e-6)
    result = {"schema": "bvm-qb-50ghz-raw-qa-v1", "status": "PASS" if finite and monotonic and bool(times) else "FAIL", "raw_sha256": sha256(raw), "sample_count": len(rows), "column_count": len(headers), "time_start_ps": times[0] * 1e12 if times else None, "time_end_ps": times[-1] * 1e12 if times else None, "nominal_dt_ps": nominal, "irregular_step_count": irregular, "finite": finite, "strictly_monotonic_time": monotonic, "raw_immutable": True}
    write_json(raw.parent / "qa" / "raw_qa.json", result)
    return result


def column(headers: list[str], wanted: str) -> str | None:
    return wanted if wanted in headers else None


def trapz(xs: list[float], ys: list[float]) -> float:
    return sum((b - a) * (ya + yb) * 0.5 for a, b, ya, yb in zip(xs, xs[1:], ys, ys[1:]))


def phase_area(headers: list[str], rows: list[dict[str, float]], phase_key: str, voltage_key: str, start_ps: float, end_ps: float) -> dict[str, Any]:
    if phase_key not in headers or voltage_key not in headers:
        return {"status": "UNKNOWN", "phase_key": phase_key, "voltage_key": voltage_key}
    subset = [(row["time"] * 1e12, row[phase_key], row[voltage_key]) for row in rows if start_ps <= row["time"] * 1e12 < end_ps]
    if len(subset) < 2:
        return {"status": "UNKNOWN", "phase_key": phase_key, "voltage_key": voltage_key, "sample_count": len(subset)}
    times = [item[0] for item in subset]
    phases = [item[1] for item in subset]
    volts = [item[2] for item in subset]
    return {"status": "RECORDED", "phase_key": phase_key, "voltage_key": voltage_key, "window_ps": [start_ps, end_ps], "delta_phase_rad": phases[-1] - phases[0], "delta_phase_turns_navigation": (phases[-1] - phases[0]) / (2.0 * math.pi), "voltage_area_phi0": trapz([t * 1e-12 for t in times], volts) / PHI0, "sample_count": len(subset)}


def response_clusters(headers: list[str], rows: list[dict[str, float]], voltage_key: str = "V(R_TERM)") -> list[dict[str, Any]]:
    if voltage_key not in headers:
        return []
    active: list[tuple[float, float]] = []
    clusters: list[list[tuple[float, float]]] = []
    previous_t: float | None = None
    for row in rows:
        t = row["time"] * 1e12
        v = row[voltage_key]
        if v >= TERMINAL_THRESHOLD_V:
            if active and previous_t is not None and t - previous_t > TERMINAL_GAP_PS:
                clusters.append(active); active = []
            active.append((t, v)); previous_t = t
        elif active:
            clusters.append(active); active = []; previous_t = None
    if active:
        clusters.append(active)
    result = []
    for points in clusters:
        result.append({"start_ps": points[0][0], "end_ps": points[-1][0], "peak_ps": max(points, key=lambda item: item[1])[0], "peak_v": max(item[1] for item in points), "sample_count": len(points)})
    return result


def clusters_in(clusters: list[dict[str, Any]], start_ps: float, end_ps: float) -> list[dict[str, Any]]:
    return [item for item in clusters if start_ps <= item["peak_ps"] < end_ps]


def state_vector(headers: list[str], rows: list[dict[str, float]], start_ps: float, end_ps: float, prefix: str = "XBVM1") -> dict[str, Any]:
    keys = [f"P(B_JM1|{prefix})", f"P(B_JM2|{prefix})", f"I(L_M1|{prefix})", f"I(L_M2|{prefix})", f"I(L_M3|{prefix})", f"I(L_PM|{prefix})"]
    subset = [row for row in rows if start_ps <= row["time"] * 1e12 < end_ps]
    values = {key: median([row[key] for row in subset]) if key in headers and subset else None for key in keys}
    return {"window_ps": [start_ps, end_ps], "values": values}


def plot_run(run_dir: Path, phase: str, kind: str) -> dict[str, Any]:
    raw = run_dir / "raw.csv"
    headers, _rows = load_raw(raw)
    if kind == "merge":
        wanted = ["V(SFQ_A)", "V(SFQ_B)", "V(SFQ_Q)", "V(SFQ_OUT)", "V(R_TERM)"]
    elif kind == "integration":
        wanted = ["V(QBOUT_A)", "V(QBOUT_B)", "V(MERGED)", "V(GLOBAL_OUT)", "V(R_TERM)"]
    else:
        wanted = ["V(R_TERM)", "P(BJ1|XBQ1)", "P(BJ2|XBQ1)", "I(L1|XBQ1)", "V(B_JSL8)"]
    selected = [item for item in wanted if item in headers]
    plot_dir = run_dir / "plots"
    plot_dir.mkdir(parents=True, exist_ok=True)
    html = plot_dir / "review.html"
    if selected:
        command = [sys.executable, str(PLOTTER), str(raw), "-x", str(html), "-t", "sep_comb", "-c", "dark", "-j", "2pi", "-w", f"{phase} {run_dir.name}", "-s", *selected]
        completed = subprocess.run(command, cwd=REPO, capture_output=True, text=True, check=False)
        status = "PASS" if completed.returncode == 0 and html.is_file() else "FAIL"
        (plot_dir / "plotter.stdout.txt").write_text(completed.stdout, encoding="utf-8")
        (plot_dir / "plotter.stderr.txt").write_text(completed.stderr, encoding="utf-8")
    else:
        html.write_text("<html><body><p>No registered plot signal was emitted.</p></body></html>\n", encoding="utf-8")
        status = "FAIL"
    qa = {"schema": "bvm-qb-50ghz-plot-qa-v1", "status": status, "phase": phase, "run_id": run_dir.name, "selected_signals": selected, "raw_sha256": sha256(raw), "descriptive_only": True, "phase_display": "P(...) raw radians; -j 2pi is navigation turns"}
    write_json(run_dir / "qa" / "plot_qa.json", qa)
    return qa


def finalize_run(run_dir: Path, phase: str, expected: dict[str, Any], kind: str = "candidate") -> dict[str, Any]:
    raw = run_dir / "raw.csv"
    qa = raw_qa(raw)
    headers, rows = load_raw(raw)
    clusters = response_clusters(headers, rows)
    metrics: dict[str, Any] = {"schema": "bvm-qb-50ghz-run-metrics-v1", "phase": phase, "run_id": run_dir.name, "expected": expected, "terminal_response_candidates": clusters, "terminal_candidate_count": len(clusters), "phase_area_cross_checks": {}}
    if kind == "candidate":
        reads = expected.get("read_starts_ps", [])
        metrics["cycle_metrics"] = []
        for start in reads:
            observed = clusters_in(clusters, start + RESPONSE_OFFSET[0], start + RESPONSE_OFFSET[1])
            metrics["cycle_metrics"].append({"read_start_ps": start, "read_end_ps": start + READ_WIDTH, "expected_population": expected.get("population", 0), "terminal_response_candidate_count": len(observed), "first_response_ps": observed[0]["peak_ps"] if observed else None, "last_response_ps": observed[-1]["peak_ps"] if observed else None, "burst_span_ps": (observed[-1]["peak_ps"] - observed[0]["peak_ps"]) if len(observed) > 1 else 0.0, "storage_state_after": state_vector(headers, rows, start + READ_WIDTH + 5.0, start + READ_WIDTH + 10.0)})
        for jj in ("BJ1", "BJ2"):
            metrics["phase_area_cross_checks"][jj] = [phase_area(headers, rows, f"P({jj}|XBQ1)", f"V({jj}|XBQ1)", start, start + READ_WIDTH) for start in reads]
        metrics["gate_candidate"] = all(item["terminal_response_candidate_count"] == item["expected_population"] for item in metrics["cycle_metrics"])
    elif kind == "rewrite":
        metrics["state_cycle_metrics"] = []
        for state in expected["sequence"]:
            read = state["read"]
            observed = clusters_in(clusters, read["start_ps"] + RESPONSE_OFFSET[0], read["start_ps"] + RESPONSE_OFFSET[1])
            metrics["state_cycle_metrics"].append({"state": state["mask"], "expected_population": state["population"], "read_start_ps": read["start_ps"], "terminal_response_candidate_count": len(observed), "first_response_ps": observed[0]["peak_ps"] if observed else None, "last_response_ps": observed[-1]["peak_ps"] if observed else None})
        metrics["gate_candidate"] = all(item["terminal_response_candidate_count"] == item["expected_population"] for item in metrics["state_cycle_metrics"])
        metrics["phase_area_cross_checks"]["BJ1"] = [phase_area(headers, rows, "P(BJ1|XBQ1)", "V(BJ1|XBQ1)", item["read"]["start_ps"], item["read"]["end_ps"]) for item in expected["sequence"]]
    elif kind == "merge":
        metrics["input_event_count"] = expected["input_event_count"]
        metrics["gate_candidate"] = len(clusters) == expected["input_event_count"]
    elif kind == "integration":
        metrics["expected_population"] = expected["population"]
        metrics["gate_candidate"] = len(clusters) == expected["population"]
        metrics["pair_a_population"] = expected["pair_a_population"]
        metrics["pair_b_population"] = expected["pair_b_population"]
    write_json(run_dir / "analysis" / "metrics.json", metrics)
    plot_kind = "merge" if kind == "merge" else "integration" if kind == "integration" else "candidate"
    plot = plot_run(run_dir, phase, plot_kind)
    result = {"schema": "bvm-qb-50ghz-run-result-v1", "phase": phase, "run_id": run_dir.name, "status": "ANALYSIS_COMPLETE_AWAITING_SCIENTIFIC_REVIEW" if qa["status"] == "PASS" and plot["status"] == "PASS" else "ARTIFACT_INVALID", "artifact_status": "VALID" if qa["status"] == "PASS" and plot["status"] == "PASS" else "INVALID", "physical_solve_count": 1, "scientific_interpretation_performed": False, "automatic_follow_up": False, "registered_mechanical_gate_candidate": metrics.get("gate_candidate"), "raw_sha256": qa["raw_sha256"], "plot_raw_sha256": plot["raw_sha256"]}
    write_json(run_dir / "result.json", result)
    return {"run_id": run_dir.name, "raw_qa": qa, "plot_qa": plot, "metrics": metrics, "result": result}


def prepare_run(phase_root: Path, run_id: str, p: dict[str, Any], stimulus_text_value: str, expected: dict[str, Any], kind: str = "candidate") -> dict[str, Any]:
    run_dir = phase_root / "runs" / run_id
    if run_dir.exists():
        attempt = 2
        while (phase_root / "runs" / f"{run_id}_attempt{attempt}").exists():
            attempt += 1
        run_id = f"{run_id}_attempt{attempt}"
        run_dir = phase_root / "runs" / run_id
    run_dir.mkdir(parents=True)
    (run_dir / "stimulus.inc").write_text(stimulus_text_value, encoding="utf-8")
    sources = copy_sources(run_dir, p)
    write_source_manifest(run_dir, sources, p, {"phase": phase_root.name, "run_id": run_id})
    deck = single_deck(run_dir, p, run_dir / "stimulus.inc", sources)
    write_json(run_dir / "config_snapshot.json", {"parameters": p, "expected": expected, "parent_head": git_head(), "phase": phase_root.name})
    run_solver(run_dir, deck, phase_root.name, run_id, {"parameters": p, **expected})
    return finalize_run(run_dir, phase_root.name, expected, kind)


def merge_cases() -> list[dict[str, Any]]:
    cases = [{"case": "A_only", "a": [40.0], "b": [], "input_event_count": 1}, {"case": "B_only", "a": [], "b": [40.0], "input_event_count": 1}]
    for delta in MERGE_DELTAS:
        cases.append({"case": f"collision_{delta:+g}ps".replace("+", "p").replace("-", "m"), "a": [40.0], "b": [40.0 + delta], "delta_ps": delta, "input_event_count": 2})
    cases.extend([{"case": "same_A_doublet_6ps", "a": [40.0, 46.0], "b": [], "input_event_count": 2}, {"case": "same_B_doublet_6ps", "a": [], "b": [40.0, 46.0], "input_event_count": 2}])
    for offset in (0.0, 3.0, 6.0):
        cases.append({"case": f"two_plus_one_{offset:g}ps".replace(".", "p"), "a": [40.0, 46.0], "b": [40.0 + offset], "input_event_count": 3})
    for skew in (0.0, 0.5, 1.0, 2.0, 3.0, 4.0):
        cases.append({"case": f"two_plus_two_skew_{skew:g}ps".replace(".", "p"), "a": [40.0, 46.0], "b": [40.0 + skew, 46.0 + skew], "skew_ps": skew, "input_event_count": 4})
    return cases


def merge_stimulus(case: dict[str, Any]) -> str:
    def source(name: str, pulses: list[float]) -> str:
        points: list[str] = ["0 0"]
        for t in pulses:
            points.extend((f"{fmt_time(t - 1.0)} 0", f"{fmt_time(t)} 0", f"{fmt_time(t + 1.0)} +1.5m", f"{fmt_time(t + 3.0)} +1.5m", f"{fmt_time(t + 4.0)} 0"))
        points.append("120p 0")
        return f"V_IN{name} IN{name} 0 pwl(" + " ".join(points) + ")"
    return "\n".join([f"* MERGE synthetic case {case['case']}", source("A", case["a"]), "R_INA INA N1 3", "L_INA N1 SFQ_A 0.5p", source("B", case["b"]), "R_INB INB N2 3", "L_INB N2 SFQ_B 0.5p", ""]) 


def merge_deck(run_dir: Path, stimulus: Path) -> Path:
    source_dir = run_dir / "snapshot" / "sources"
    source_dir.mkdir(parents=True, exist_ok=True)
    for source in (JJ_SOURCE, MERGE_JTL_SOURCE, MERGE_SOURCE):
        shutil.copy2(source, source_dir / source.name)
    text = "\n".join([
        ".include " + os.path.relpath(source_dir / JJ_SOURCE.name, run_dir),
        ".include " + os.path.relpath(source_dir / MERGE_SOURCE.name, run_dir),
        ".include " + os.path.relpath(source_dir / MERGE_JTL_SOURCE.name, run_dir),
        ".include " + os.path.relpath(stimulus, run_dir),
        "XMERGE SFQ_A SFQ_B SFQ_Q THmitll_MERGE",
        "XLOAD SFQ_Q SFQ_OUT THmitll_JTL",
        "R_TERM SFQ_OUT 0 1",
        ".tran 0.1p 120p",
        ".print V(SFQ_A) V(SFQ_B) V(SFQ_Q) V(SFQ_OUT) V(R_TERM)",
        ".print " + " ".join(f"P(B{i}|XMERGE)" for i in range(1, 8)),
        ".print " + " ".join(f"I(L{i}|XMERGE)" for i in range(1, 11)),
        ".print P(B1|XLOAD) P(B2|XLOAD)",
        ".end",
    ]) + "\n"
    deck = run_dir / "actual_deck.cir"
    deck.write_text(text, encoding="utf-8")
    (run_dir / "deck.cir").write_text(text, encoding="utf-8")
    return deck


def run_merge_case(phase_root: Path, case: dict[str, Any]) -> dict[str, Any]:
    run_id = case["case"]
    run_dir = phase_root / "runs" / run_id
    if run_dir.exists():
        raise RuntimeError(f"refusing to overwrite existing run: {run_dir}")
    run_dir.mkdir(parents=True)
    stimulus = run_dir / "stimulus.inc"
    stimulus.write_text(merge_stimulus(case), encoding="utf-8")
    sources = {"JJ_MODEL": run_dir / "snapshot" / "sources" / JJ_SOURCE.name, "JTL_STANDARD": run_dir / "snapshot" / "sources" / MERGE_JTL_SOURCE.name, "MERGE": run_dir / "snapshot" / "sources" / MERGE_SOURCE.name}
    deck = merge_deck(run_dir, stimulus)
    write_source_manifest(run_dir, sources, {"fixture": "standard MERGE", "merge_source_sha256": sha256(MERGE_SOURCE)}, {"phase": phase_root.name, "run_id": run_id, "case": case})
    run_solver(run_dir, deck, phase_root.name, run_id, {"case": case, "input_event_count": case["input_event_count"]})
    return finalize_run(run_dir, phase_root.name, {"case": case, "input_event_count": case["input_event_count"]}, "merge")


def integration_params() -> dict[str, Any]:
    p = candidate_params("QB_2X1", 4)
    p["CANDIDATE"] = "QB_2X1_BRANCH_A_AND_B"
    p["STOP"] = "240p"
    return p


def integration_stimulus(mask: str) -> str:
    p = integration_params()
    # Use the same one-shot write/control/read protocol as Phase A, with one final read.
    text, _ = repeated_stimulus(p, mask)
    return text.replace("five reads at 20 ps cadence; no rewrite after WRITE1.", "single registered integration read at 110-121 ps.")


def integration_deck(run_dir: Path, stimulus: Path, p: dict[str, Any]) -> Path:
    source_dir = run_dir / "snapshot" / "sources"
    source_dir.mkdir(parents=True, exist_ok=True)
    for source in (JJ_SOURCE, MERGE_JTL_SOURCE, MERGE_SOURCE):
        shutil.copy2(source, source_dir / source.name)
    bvm = source_dir / "bvm_tunable.cir"; bvm.write_text(legacy.render_bvm(p), encoding="utf-8")
    qb = legacy.render_qb(p)
    qb_a = qb.replace(".subckt BQ IN OUT", ".subckt BQ_A IN OUT", 1).replace(".ends BQ", ".ends BQ_A", 1)
    qb_b = qb.replace(".subckt BQ IN OUT", ".subckt BQ_B IN OUT", 1).replace(".ends BQ", ".ends BQ_B", 1)
    (source_dir / "bq_branch.cir").write_text(qb_a + "\n" + qb_b, encoding="utf-8")
    lines = [
        ".include " + os.path.relpath(source_dir / JJ_SOURCE.name, run_dir),
        ".include " + os.path.relpath(source_dir / JTL_SOURCE.name, run_dir),
        ".include " + os.path.relpath(source_dir / MERGE_SOURCE.name, run_dir),
        ".include " + os.path.relpath(bvm, run_dir),
        ".include " + os.path.relpath(source_dir / "bq_branch.cir", run_dir),
        ".include " + os.path.relpath(stimulus, run_dir),
    ]
    lines.extend(["XBVM1 WL1 BL1 SE1 COMMON_SL_A BVM", "XBVM2 WL2 BL2 SE2 COMMON_SL_A BVM", "XBVM3 WL3 BL3 SE3 COMMON_SL_B BVM", "XBVM4 WL4 BL4 SE4 COMMON_SL_B BVM"])
    for prefix, common, qbin in (("A", "COMMON_SL_A", "QBIN_A"), ("B", "COMMON_SL_B", "QBIN_B")):
        lines.extend([f"B_JSL_{prefix}1 {common} JSL_{prefix}1 jjmit area=5.0"] + [f"B_JSL_{prefix}{i} JSL_{prefix}{i-1} JSL_{prefix}{i} jjmit area=5.0" for i in range(2, 8)] + [f"B_JSL_{prefix}8 JSL_{prefix}7 {qbin} jjmit area=5.0", f"XQB_{prefix} {qbin} QBOUT_{prefix} BQ_{prefix}", f"XISO_{prefix} QBOUT_{prefix} ISO_{prefix} THmitll_JTL"])
    lines.extend(["XMERGE ISO_A ISO_B MERGED THmitll_MERGE", "XGLOBAL_JTL MERGED GLOBAL_OUT THmitll_JTL", "R_TERM GLOBAL_OUT 0 1", ".tran 0.1p 240p"])
    for index in range(1, 5):
        lines.append(".print " + " ".join(f"{q}({j}|XBVM{index})" for j in ("B_JM1", "B_JM2", "B_JS1", "B_JS2") for q in ("P", "V", "I")))
    lines.append(".print V(COMMON_SL_A) V(COMMON_SL_B)")
    for prefix in ("A", "B"):
        lines.append(".print " + " ".join(f"{q}(B_JSL_{prefix}{i})" for i in range(1, 9) for q in ("P", "V", "I")))
        lines.append(".print " + " ".join(f"{q}({j}|XQB_{prefix})" for j in ("BJS", "BJ1", "BJ2") for q in ("P", "V", "I")))
        lines.append(".print " + " ".join(f"{q}({j}|XISO_{prefix})" for j in ("B1", "B2") for q in ("P", "V", "I")))
    lines.append(".print " + " ".join(f"{q}(B{i}|XMERGE)" for i in range(1, 8) for q in ("P", "V", "I")))
    lines.append(".print P(B1|XGLOBAL_JTL) P(B2|XGLOBAL_JTL) V(GLOBAL_OUT) V(R_TERM)")
    lines.append(".end")
    deck = run_dir / "actual_deck.cir"
    deck.write_text("\n".join(lines) + "\n", encoding="utf-8")
    (run_dir / "deck.cir").write_text(deck.read_text(encoding="utf-8"), encoding="utf-8")
    return deck


def run_integration_case(phase_root: Path, mask: str) -> dict[str, Any]:
    run_id = f"mask_{mask}"
    run_dir = phase_root / "runs" / run_id
    if run_dir.exists():
        raise RuntimeError(f"refusing to overwrite existing run: {run_dir}")
    run_dir.mkdir(parents=True)
    p = integration_params(); p["MASK"] = mask
    (run_dir / "stimulus.inc").write_text(integration_stimulus(mask), encoding="utf-8")
    sources = {"JJ_MODEL": JJ_SOURCE, "JTL_STANDARD": MERGE_JTL_SOURCE, "MERGE": MERGE_SOURCE}
    deck = integration_deck(run_dir, run_dir / "stimulus.inc", p)
    write_source_manifest(run_dir, {key: (run_dir / "snapshot" / "sources" / path.name if key != "BVM" else run_dir / "snapshot" / "sources" / "bvm_tunable.cir") for key, path in sources.items()} | {"BVM": run_dir / "snapshot" / "sources" / "bvm_tunable.cir", "QB_A": run_dir / "snapshot" / "sources" / "bq_branch.cir", "QB_B": run_dir / "snapshot" / "sources" / "bq_branch.cir"}, p, {"phase": phase_root.name, "run_id": run_id, "mask": mask, "pair_mapping": "b3b2|b1b0"})
    expected = {"mask": mask, "population": mask.count("1"), "pair_a_population": mask[:2].count("1"), "pair_b_population": mask[2:].count("1"), "parameters": p}
    run_solver(run_dir, deck, phase_root.name, run_id, expected)
    return finalize_run(run_dir, phase_root.name, expected, "integration")


def write_phase_summary(phase_root: Path, results: list[dict[str, Any]], status: str, extra: dict[str, Any] | None = None) -> None:
    data = {"schema": "bvm-qb-50ghz-phase-summary-v1", "phase": phase_root.name, "status": status, "run_count": len(results), "physical_solve_count": len(results), "scientific_interpretation_performed": False, "automatic_follow_up": False, "runs": results}
    if extra:
        data.update(extra)
    write_json(phase_root / "analysis" / "phase_summary.json", data)
    lines = [f"# {phase_root.name}", "", "scientific interpretation = NOT PERFORMED", "", f"status = {status}", f"physical_solve_count = {len(results)}", ""]
    for result in results:
        lines.append(f"- {result['run_id']}: raw_qa={result['raw_qa']['status']}; plot_qa={result['plot_qa']['status']}; registered_mechanical_gate_candidate={result['metrics'].get('gate_candidate')}")
    (phase_root / "RESULT_BRIEF.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_phase_a() -> dict[str, Any]:
    root = ROOT / "phase_a_repeated_read"; results = []
    for candidate, masks in PHASE_A_MASKS.items():
        for mask in masks:
            p = candidate_params(candidate); p["CANDIDATE"] = candidate
            text, reads = repeated_stimulus(p, mask)
            expected = {"candidate": candidate, "mask": mask, "population": mask.count("1"), "read_starts_ps": reads, "parameters": p}
            results.append(prepare_run(root, f"{candidate}_{mask}", p, text, expected, "candidate"))
    status = "PASS" if all(item["result"]["artifact_status"] == "VALID" for item in results) else "ARTIFACT_INVALID"
    write_phase_summary(root, results, status, {"registered_read_cadence_ps": 20.0, "registered_response_offset_ps": list(RESPONSE_OFFSET)})
    return {"status": status, "results": results}


def run_phase_b() -> dict[str, Any]:
    root = ROOT / "phase_b_rewrite_read"; results = []
    for candidate, sequence in REWRITE_SEQUENCES.items():
        p = candidate_params(candidate); p["CANDIDATE"] = candidate
        text, records = rewrite_stimulus(p, sequence)
        expected = {"candidate": candidate, "sequence": [{"mask": item["state"], "population": item["population"], "read": {"start_ps": item["read_start_ps"], "end_ps": item["read_end_ps"]}} for item in records], "parameters": p}
        results.append(prepare_run(root, f"{candidate}_rewrite_sequence", p, text, expected, "rewrite"))
    status = "PASS" if all(item["result"]["artifact_status"] == "VALID" for item in results) else "ARTIFACT_INVALID"
    write_phase_summary(root, results, status)
    return {"status": status, "results": results}


def run_phase_c() -> dict[str, Any]:
    root = ROOT / "phase_c_merge_collision"; results = []
    static = {"merge_source_sha256": sha256(MERGE_SOURCE), "merge_source_has_non_ascii": any(ord(ch) > 127 for ch in MERGE_SOURCE.read_text(encoding="utf-8")), "merge_source_path": repo_rel(MERGE_SOURCE)}
    write_json(root / "analysis" / "merge_static_check.json", static)
    for case in merge_cases():
        run_dir = root / "runs" / case["case"]
        if run_dir.exists() and (run_dir / "raw.csv").is_file():
            results.append(finalize_run(run_dir, root.name, {"case": case, "input_event_count": case["input_event_count"]}, "merge"))
        else:
            results.append(run_merge_case(root, case))
    gate = {"schema": "bvm-qb-50ghz-merge-gate-v1", "status": "PASS" if all(item["result"]["artifact_status"] == "VALID" for item in results) and all(item["metrics"].get("gate_candidate") is True for item in results) else "FAIL", "required_case_count": len(results), "cases": [{"run_id": item["run_id"], "input_event_count": item["metrics"].get("input_event_count"), "terminal_response_candidate_count": item["metrics"].get("terminal_candidate_count"), "gate_candidate": item["metrics"].get("gate_candidate")} for item in results], "static_check": static, "scientific_interpretation_performed": False}
    write_json(root / "analysis" / "merge_gate.json", gate)
    status = "PASS" if gate["status"] == "PASS" and all(item["result"]["artifact_status"] == "VALID" for item in results) else "FAIL"
    write_phase_summary(root, results, status, {"merge_gate": gate})
    return {"status": status, "results": results, "gate": gate}


def run_phase_d() -> dict[str, Any]:
    root = ROOT / "phase_d_4bvm_merge_integration"; results = []
    for mask in INTEGRATION_MASKS:
        results.append(run_integration_case(root, mask))
    status = "PASS" if all(item["result"]["artifact_status"] == "VALID" for item in results) else "ARTIFACT_INVALID"
    write_phase_summary(root, results, status, {"pair_mapping": "b3b2|b1b0", "masks": list(INTEGRATION_MASKS)})
    return {"status": status, "results": results}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("A", "B", "C", "D", "all"), required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.dry_run:
        print(json.dumps({"experiment": ROOT.name, "parent_head": git_head(), "phase": args.phase, "phase_a_solves": sum(len(v) for v in PHASE_A_MASKS.values()), "phase_b_solves": len(REWRITE_SEQUENCES), "phase_c_solves": len(merge_cases()), "phase_d_solves_if_authorized": len(INTEGRATION_MASKS)}, indent=2))
        return 0
    if args.phase == "A":
        run_phase_a()
    elif args.phase == "B":
        run_phase_b()
    elif args.phase == "C":
        run_phase_c()
    elif args.phase == "D":
        gate = ROOT / "phase_c_merge_collision" / "analysis" / "merge_gate.json"
        if not gate.is_file() or json.loads(gate.read_text(encoding="utf-8")).get("status") != "PASS":
            raise SystemExit("STOP: direct MERGE mechanical gate is not PASS; Phase D is not authorized")
        run_phase_d()
    else:
        run_phase_a(); run_phase_b(); merge = run_phase_c()
        if merge["status"] == "PASS":
            run_phase_d()
        else:
            print("STOP: direct MERGE mechanical gate failed; Phase D not run")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
