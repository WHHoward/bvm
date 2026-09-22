#!/usr/bin/env python3
"""Execute the registered B019 control-only gate and QB_IB sweep.

This driver deliberately keeps the control-only fixture separate from the
normal USER_CASE runner.  It creates exact stored-grid control-only evidence,
gates the authorized B019 sweep on the registered C0/C1 pattern, and stops at
mechanical/raw evidence.  It never interprets a terminal candidate as an SFQ
count or assigns a scientific operating-window verdict.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any

SERIES = Path(__file__).resolve().parents[1]
REPO = next(path for path in (SERIES, *SERIES.parents) if (path / ".git").exists())
sys.path.insert(0, str(SERIES / "scripts"))

import analyze as engine  # noqa: E402
import run_candidate as legacy  # noqa: E402
import try_candidate as platform  # noqa: E402
from render_review import render_group  # noqa: E402

USER_CONFIG = SERIES / "USER_CASE.env"
REFERENCE_CONFIG = SERIES / "config" / "canonical_reference.env"
PLAN = SERIES / "batches" / "B019_QB_IB_downward" / "B019_PLAN.json"
BATCH_ROOT = SERIES / "batches" / "B019_QB_IB_downward"
CONTROL_WINDOW = (70.0, 120.0)
CONTROL_MASK = "0000"
CONTROL_DT = "0.1p"
CONTROL_STOP = "120p"
CONTROL_CASES = (
    ("C0", "0.90", "32", "260u"),
    ("C1", "0.75", "32", "260u"),
)
IB_VALUES = ("220u", "230u", "240u", "250u", "260u")
QB_BASE = {
    "QB_LIN": "1.5p",
    "QB_BJS_AREA": "4.0",
    "QB_L1": "1.4p",
    "QB_L2": "2.0p",
    "QB_RJ1": "32",
    "QB_BJ2_AREA": "2.0",
    "QB_RJ2": "12",
    "QB_L3": "1.3p",
}
BVM_BASE = {
    "JM1_AREA": "1.2",
    "JM2_AREA": "1.4",
    "RJM1": "8",
    "RJM2": "OPEN",
    "LM1": "12.5p",
    "LM2": "24.5p",
    "LM3": "8.5p",
    "LPM": "0.5p",
    "JS1_AREA": "0.52",
    "JS2_AREA": "0.74",
    "RSH_JS1": "12",
    "RSH_JS2": "20",
    "LS1": "0.5p",
    "LS2": "0.5p",
    "LS3": "0.5p",
    "RS": "3.0",
    "LPSL": "0.5p",
    "RSL": "12.0",
    "LSL": "0.4p",
    "RBL": "20.0",
    "LPBL": "0.5p",
    "RWL": "20.0",
    "LPWL": "0.5p",
    "RSE": "20.0",
    "LPSE": "0.5p",
}
REQUIRED_CONTROL_HEADERS = (
    "P(BJ1|XBQ1)", "V(BJ1|XBQ1)", "I(BJ1|XBQ1)",
    "P(BJ2|XBQ1)", "V(BJ2|XBQ1)", "I(BJ2|XBQ1)",
    "I(L1|XBQ1)", "V(L1|XBQ1)", "I(R_TERM)", "V(R_TERM)",
    "V(QBIN)", "V(QBOUT)", "V(JTL6_OUT)", "V(COMMON_SL)",
)


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
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def repo_rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def load_raw(path: Path) -> tuple[list[str], list[list[float]]]:
    with path.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.reader(stream)
        headers = next(reader)
        rows = [[float(value) for value in row] for row in reader if row]
    return headers, rows


def value_equal(left: str, right: str) -> bool:
    if left.strip().upper() == right.strip().upper() == "OPEN":
        return True
    try:
        return abs(platform.parse_number(left, "compare") - platform.parse_number(right, "compare")) <= 1e-18 * max(1.0, abs(platform.parse_number(right, "compare")))
    except RuntimeError:
        return left.strip() == right.strip()


def check_user_baseline(values: dict[str, str]) -> None:
    for key, expected in {**BVM_BASE, **QB_BASE, "QB_BJ1_AREA": "0.75", "QB_IB": "260u", "MODE": "closed"}.items():
        actual = values.get(key)
        if actual is None or not value_equal(actual, expected):
            raise RuntimeError(f"USER_CASE baseline mismatch for {key}: expected {expected}, got {actual}")


def control_params(label: str, area: str, rj1: str, ib: str) -> tuple[dict[str, Any], dict[str, str]]:
    values = platform.load_env(USER_CONFIG)
    check_user_baseline(values)
    values.update({
        "NAME": f"B019_CONTROL_ONLY_{label}",
        "MODE": "closed",
        "MASKS": CONTROL_MASK,
        "QB_BJ1_AREA": area,
        "QB_RJ1": rj1,
        "QB_IB": ib,
        "SWEEP_ENABLED": "no",
        "SWEEP_KEY": "NONE",
        "SWEEP_VALUES": "",
        "SWEEP_REUSE_EXISTING": "yes",
    })
    validated = platform.validate(values, platform.load_env(REFERENCE_CONFIG))
    validated["STOP"] = CONTROL_STOP
    validated["RECOVERY_END"] = CONTROL_STOP
    validated["TAIL_START"] = "81p"
    validated["MASKS"] = [CONTROL_MASK]
    validated["CASE_ID"] = ""
    validated["windows"] = {
        "idle_0_50": [0.0, 50.0],
        "write0_50_61": [50.0, 61.0],
        "settle0_61_70": [61.0, 70.0],
        "control_70_81": [70.0, 81.0],
        "tail_81_120": [81.0, 120.0],
        "control_observation_70_120": [70.0, 120.0],
        "whole_0_120": [0.0, 120.0],
    }
    validated["time_ps"] = {"DT": 0.1, "STOP": 120.0, "CONTROL_START": 70.0, "CONTROL_END": 81.0}
    validated["control_only"] = True
    validated["control_only_label"] = label
    validated["config_changes"] = platform.change_rows(values, platform.load_env(REFERENCE_CONFIG))
    return validated, values


def control_stimulus() -> str:
    lines = [
        "* CONTROL_ONLY fixture; mask=0000; BVM1..BVM4 sources are identical external control paths.",
        "* IDLE [0,50); WRITE0 [50,61); settle [61,70); CONTROL [70,81); zero [81,120).",
        "* No WRITE1 and no FINAL READ. All times are exact registered PWL points.",
    ]
    for index in range(1, 5):
        for signal in ("WL", "BL", "SE"):
            write0 = -100.0 if signal in {"WL", "BL"} else 0.0
            control = 100.0 if signal in {"WL", "SE"} else 0.0
            points = [(0, 0), (50, 0), (51, write0), (60, write0), (61, 0), (70, 0), (71, control), (80, control), (81, 0), (120, 0)]
            values: list[str] = []
            for time_ps, current_ua in points:
                values.extend(("0" if time_ps == 0 else f"{time_ps:g}p", "0" if current_ua == 0 else f"{current_ua:+g}u"))
            lines.append(f"I_{signal}{index} 0 {signal}{index} pwl(" + " ".join(values) + ")")
    return "\n".join(lines) + "\n"


def config_snapshot(values: dict[str, str], case_id: str) -> str:
    lines = [f"# B019 CONTROL_ONLY snapshot; case={case_id}", "FIXTURE_MODE=CONTROL_ONLY", "CONTROL_ONLY_MASK=0000"]
    for key in sorted(values):
        lines.append(f"{key}={values[key]}")
    return "\n".join(lines) + "\n"


def source_manifest(case_root: Path, params: dict[str, Any], sources: dict[str, Path], parent: dict[str, Any], values: dict[str, str]) -> dict[str, Any]:
    records = []
    for role, path in sources.items():
        records.append({"role": role, "path": repo_rel(path), "sha256": sha256(path), "bytes": path.stat().st_size})
    for role, path in (
        ("TOP_CLOSED", SERIES / "circuits" / "closed_top.cir"),
        ("QB_TUNABLE_TEMPLATE", SERIES / "circuits" / "bq_tunable.cir"),
        ("BVM_TUNABLE_TEMPLATE", SERIES / "circuits" / "bvm_tunable.cir"),
        ("USER_CASE", USER_CONFIG),
        ("REFERENCE_CONFIG", REFERENCE_CONFIG),
    ):
        records.append({"role": role, "path": repo_rel(path), "sha256": sha256(path), "bytes": path.stat().st_size})
    by_role = {item["role"]: item for item in records}
    return {
        "schema": "bvm-rloop-control-only-source-manifest-v1",
        "created_at": now(),
        "parent": parent,
        "contract_sentence": "This experiment is governed by docs/EXPERIMENT_CONTRACT.md.",
        "fixture_mode": "CONTROL_ONLY",
        "case_parameters": params,
        "config_values": values,
        "sources": records,
        "bvm_rendered_snapshot": by_role.get("BVM"),
        "qb_rendered_snapshot": by_role.get("QB"),
        "jj_model_snapshot": by_role.get("JJ_MODEL"),
        "jtl_snapshot": by_role.get("JTL"),
        "canonical_bvm_source": {"path": repo_rel(platform.CANONICAL_BVM), "sha256": sha256(platform.CANONICAL_BVM)},
        "raw_not_copied_from_history": True,
    }


def terminal_candidates(times: list[float], values: list[float]) -> dict[str, Any]:
    candidates = [(times[index], values[index]) for index in range(1, len(values) - 1) if values[index] >= 50e-6 and values[index] >= values[index - 1] and values[index] >= values[index + 1]]
    selected: list[tuple[float, float]] = []
    for candidate in candidates:
        if not selected or candidate[0] - selected[-1][0] >= 2.5:
            selected.append(candidate)
        elif candidate[1] > selected[-1][1]:
            selected[-1] = candidate
    return {
        "count": len(selected),
        "candidates": [{"peak_ps": time_ps, "peak_A": peak} for time_ps, peak in selected],
        "first_peak_ps": selected[0][0] if selected else None,
        "max_peak_A": max((peak for _, peak in selected), default=None),
        "threshold_A": 50e-6,
        "minimum_separation_ps": 2.5,
        "label": "terminal_candidate",
    }


def window_values(headers: list[str], rows: list[list[float]], signal: str, start: float, end: float) -> tuple[list[float], list[float]]:
    if signal not in headers:
        return [], []
    column = headers.index(signal)
    selected = [(row[0] * 1e12, row[column]) for row in rows if start <= row[0] * 1e12 < end]
    return [item[0] for item in selected], [item[1] for item in selected]


def phase_metric(headers: list[str], rows: list[list[float]], prefix: str) -> dict[str, Any]:
    times, values = window_values(headers, rows, f"P({prefix}|XBQ1)", *CONTROL_WINDOW)
    unwrapped = engine.unwrap(values)
    relative = [(value - unwrapped[0]) / (2.0 * 3.141592653589793) for value in unwrapped] if unwrapped else []
    crossings = {"0.5": next((times[index] for index, value in enumerate(relative) if value >= 0.5), None), "1.5": next((times[index] for index, value in enumerate(relative) if value >= 1.5), None)}
    voltage_times, voltage_values = window_values(headers, rows, f"V({prefix}|XBQ1)", *CONTROL_WINDOW)
    return {
        "phase_raw_rad": {"start": values[0] if values else None, "end": values[-1] if values else None},
        "forward_max_turn": max(relative, default=None),
        "forward_min_turn": min(relative, default=None),
        "forward_p2p_turn": (max(relative) - min(relative)) if relative else None,
        "net_turn": relative[-1] if relative else None,
        "t_plus_0p5_ps": crossings["0.5"],
        "t_plus_1p5_ps": crossings["1.5"],
        "voltage_area_turn": engine.trapezoid(voltage_times, voltage_values) / engine.PHI0,
        "same_jj_voltage_area_crosscheck": True,
    }


def control_metrics(raw_path: Path) -> dict[str, Any]:
    headers, rows = load_raw(raw_path)
    times, l1_values = window_values(headers, rows, "I(L1|XBQ1)", *CONTROL_WINDOW)
    term_times, term_values = window_values(headers, rows, "I(R_TERM)", *CONTROL_WINDOW)
    bj1 = phase_metric(headers, rows, "BJ1")
    bj2 = phase_metric(headers, rows, "BJ2")
    metrics = {
        "schema": "bvm-rloop-control-only-metrics-v1",
        "case": raw_path.parents[2].name,
        "raw": {"path": repo_rel(raw_path), "sha256_before": sha256(raw_path)},
        "window": {"start_ps": 70.0, "end_ps": 120.0, "half_open": True, "actual_stored_samples": len(times)},
        "CONTROL_BJ1_forward_max_turn": bj1["forward_max_turn"],
        "CONTROL_BJ1_t_plus_0p5_ps": bj1["t_plus_0p5_ps"],
        "CONTROL_BJ1_t_plus_1p5_ps": bj1["t_plus_1p5_ps"],
        "CONTROL_BJ1_same_jj_voltage_area_turn": bj1["voltage_area_turn"],
        "CONTROL_BJ2_forward_max_turn": bj2["forward_max_turn"],
        "CONTROL_BJ2_t_plus_0p5_ps": bj2["t_plus_0p5_ps"],
        "CONTROL_BJ2_t_plus_1p5_ps": bj2["t_plus_1p5_ps"],
        "CONTROL_BJ2_same_jj_voltage_area_turn": bj2["voltage_area_turn"],
        "CONTROL_L1_I_min": min(l1_values) if l1_values else None,
        "CONTROL_L1_I_max": max(l1_values) if l1_values else None,
        "CONTROL_L1_zero_cross_up_ps": next((time for left, right, time in zip(l1_values, l1_values[1:], times[1:]) if left <= 0 < right), None),
        "CONTROL_terminal_candidate_count": terminal_candidates(term_times, term_values)["count"],
        "CONTROL_terminal_first_peak_ps": terminal_candidates(term_times, term_values)["first_peak_ps"],
        "CONTROL_terminal_max_peak_A": terminal_candidates(term_times, term_values)["max_peak_A"],
        "terminal_locator": terminal_candidates(term_times, term_values),
        "phase_convention": "P(...) raw radians; displayed forward values are independently unwrapped rad/(2*pi) navigation turns, not SFQ counts.",
        "scientific_interpretation_performed": False,
    }
    metrics["raw"]["sha256_after_metric_read"] = sha256(raw_path)
    return metrics


def visualization(case_root: Path, run_dir: Path, metrics: dict[str, Any]) -> dict[str, Any]:
    raw = run_dir / "raw.csv"
    headers, rows = load_raw(raw)
    plot_dir = SERIES / "plots" / case_root.name / "control_only"
    plot_dir.mkdir(parents=True, exist_ok=True)
    asset = SERIES / "plots" / "assets" / "plotly.min.js"
    signals = [
        "V(COMMON_SL)", "V(QBIN)", "V(QBOUT)", "P(BJ1|XBQ1)", "V(BJ1|XBQ1)", "I(BJ1|XBQ1)",
        "P(BJ2|XBQ1)", "V(BJ2|XBQ1)", "I(BJ2|XBQ1)", "I(L1|XBQ1)", "V(L1|XBQ1)",
        "V(JTL6_OUT)", "I(R_TERM)", "V(R_TERM)",
    ]
    signals = [signal for signal in signals if signal in headers]
    full = render_group(raw, plot_dir / "whole_0_120.html", signals, f"{case_root.name} — CONTROL_ONLY — whole 0–120 ps", asset)
    focus_raw = case_root / "analysis" / "visualization_source_70_120.csv"
    with focus_raw.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(headers)
        writer.writerows(row for row in rows if 70.0 <= row[0] * 1e12 < 120.0)
    focus = render_group(focus_raw, plot_dir / "focus_70_120.html", signals, f"{case_root.name} — CONTROL_ONLY — focused 70–120 ps", asset)
    entries = [item for item in (full, focus) if item]
    manifest = {
        "schema": "bvm-rloop-control-only-visualization-v1",
        "case_id": case_root.name,
        "entries": entries,
        "focus_transformation": "exact stored raw rows with 70 ps <= time < 120 ps; no interpolation, smoothing, or resampling",
        "source_raw_sha256": sha256(raw),
        "descriptive_only": True,
    }
    write_json(case_root / "analysis" / "control_only_visualization.json", manifest)
    qa = {
        "schema": "bvm-rloop-control-only-plot-qa-v1",
        "status": "PASS" if entries and all(item["raw_sha256"] == sha256(REPO / item["raw_path"]) for item in entries) else "FAIL",
        "entry_count": len(entries),
        "raw_hashes_rechecked": all(item["raw_sha256"] == sha256(REPO / item["raw_path"]) for item in entries),
        "descriptive_only": True,
        "phase_display": "raw P(...) radians; -j 2pi is navigation only",
    }
    write_json(case_root / "qa" / "control_only_plot_qa.json", qa)
    page = plot_dir / "review.html"
    links = " ".join(f"<li><a href='{html.escape(path.name)}'>{html.escape(path.stem)}</a></li>" for path in (plot_dir / "whole_0_120.html", plot_dir / "focus_70_120.html"))
    page.write_text(
        "<!doctype html><html><head><meta charset='utf-8'><title>" + html.escape(case_root.name) + "</title></head><body>"
        + f"<h1>{html.escape(case_root.name)} — CONTROL_ONLY</h1><p>Descriptive visualization only. P(...) raw radians; rad/(2*pi) is navigation, not SFQ count.</p>"
        + "<h2>Plots</h2><ul>" + links + "</ul>"
        + f"<p><a href='../../../runs/{html.escape(case_root.name)}/raw.csv'>case raw directory</a> · <a href='../../../runs/{html.escape(case_root.name)}/analysis/control_only_metrics.json'>metrics</a></p></body></html>\n",
        encoding="utf-8",
    )
    return {"manifest": repo_rel(case_root / "analysis" / "control_only_visualization.json"), "qa": qa, "review": repo_rel(page)}


def solve_control_case(label: str, area: str, rj1: str, ib: str) -> dict[str, Any]:
    params, values = control_params(label, area, rj1, ib)
    case_id = f"{platform.next_case_id()}_B019_CONTROL_ONLY_{label}"
    params["CASE_ID"] = case_id
    case_root = SERIES / "runs" / case_id
    if case_root.exists():
        raise RuntimeError(f"refusing to overwrite control case {case_root}")
    parent = legacy.git_snapshot()
    case_root.mkdir(parents=True, exist_ok=False)
    (case_root / "config_snapshot.env").write_text(config_snapshot(values, case_id), encoding="utf-8")
    (case_root / "stimulus_snapshot.env").write_text(control_stimulus(), encoding="utf-8")
    sources = platform.render_case_sources(case_root, params)
    write_json(case_root / "source_manifest.json", source_manifest(case_root, params, sources, parent, values))
    run_id = "CONTROL_ONLY_N0_0000"
    run_dir = case_root / "cases" / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    stimulus = run_dir / "stimulus.inc"
    stimulus.write_text(control_stimulus(), encoding="utf-8")
    deck = run_dir / "actual_deck.cir"
    deck_text = legacy.render_deck("closed", params, sources, stimulus, run_dir)
    deck.write_text(deck_text, encoding="utf-8")
    (run_dir / "deck.cir").write_text(deck_text, encoding="utf-8")
    raw = run_dir / "raw.csv"
    command = [str(REPO / "build" / "josim-cli"), "-a", "1", "-o", str(raw), str(deck)]
    started = now(); clock = time.monotonic()
    completed = subprocess.run(command, cwd=run_dir, capture_output=True, text=True, check=False)
    runtime = time.monotonic() - clock; finished = now()
    (run_dir / "stdout.txt").write_text(completed.stdout, encoding="utf-8")
    (run_dir / "stderr.txt").write_text(completed.stderr, encoding="utf-8")
    (run_dir / "run.log").write_text("\n".join((f"experiment={SERIES.name}", f"run_id={run_id}", f"fixture=CONTROL_ONLY", f"started_at={started}", f"finished_at={finished}", f"runtime_seconds={runtime:.6f}", f"command={shlex.join(command)}", f"exit_code={completed.returncode}", "")), encoding="utf-8")
    if completed.returncode != 0 or not raw.is_file() or raw.stat().st_size == 0:
        write_json(run_dir / "metadata.json", {"run_id": run_id, "execution_status": "SOLVER_FAIL", "command": command, "stderr_tail": completed.stderr[-4000:]})
        raise RuntimeError(f"JoSIM failed for {case_id}; artifacts preserved at {run_dir}")
    headers = legacy.read_header(raw)
    signal_manifest = legacy.write_signal_manifest(run_dir, "closed", params, headers)
    metadata = {
        "run_id": run_id, "mode": "closed", "mask": CONTROL_MASK, "fixture_mode": "CONTROL_ONLY",
        "parameters": params, "windows": params["windows"], "command": command, "started_at": started, "finished_at": finished,
        "runtime_seconds": runtime, "execution_status": "RUN_PASS",
        "solver": {"path": repo_rel(REPO / "build" / "josim-cli"), "sha256": sha256(REPO / "build" / "josim-cli"), "version": subprocess.check_output([str(REPO / "build" / "josim-cli"), "--version"], text=True).strip()},
        "deck": {"path": repo_rel(deck), "sha256": sha256(deck), "bytes": deck.stat().st_size},
        "stimulus": {"path": repo_rel(stimulus), "sha256": sha256(stimulus), "bytes": stimulus.stat().st_size},
        "raw": {"path": repo_rel(raw), "sha256": sha256(raw), "bytes": raw.stat().st_size, "headers": len(headers)},
        "signal_manifest": signal_manifest,
    }
    write_json(run_dir / "metadata.json", metadata)
    metrics = control_metrics(raw)
    write_json(case_root / "analysis" / "control_only_metrics.json", metrics)
    qa = engine.raw_qa(metadata, raw, *load_raw(raw))
    missing = [signal for signal in REQUIRED_CONTROL_HEADERS if signal not in headers]
    qa["required_control_headers_missing"] = missing
    qa["status"] = "PASS" if qa["status"] == "PASS" and not missing else "FAIL"
    write_json(case_root / "qa" / "raw_qa.json", {"schema": "bvm-rloop-control-only-raw-qa-v1", "status": qa["status"], "run_count": 1, "rows": [qa], "raw_immutable": True})
    viz = visualization(case_root, run_dir, metrics)
    expected = {
        "C0": {"terminal_count": 0, "bj1_t0p5": None, "bj2_t0p5": None},
        "C1": {"terminal_count": 1, "bj1_t0p5": "present", "bj2_t0p5": "present"},
    }[label]
    actual = {"terminal_count": metrics["CONTROL_terminal_candidate_count"], "bj1_t0p5": "present" if metrics["CONTROL_BJ1_t_plus_0p5_ps"] is not None else None, "bj2_t0p5": "present" if metrics["CONTROL_BJ2_t_plus_0p5_ps"] is not None else None}
    pattern_match = actual == expected
    validation = {"label": label, "case_id": case_id, "expected_pattern": expected, "actual_pattern": actual, "pattern_match": pattern_match, "reported_first_peak_ps": metrics["CONTROL_terminal_first_peak_ps"], "reported_max_peak_A": metrics["CONTROL_terminal_max_peak_A"], "no_invented_numeric_threshold": True}
    write_json(case_root / "analysis" / "control_only_validation.json", validation)
    summary = [f"# {case_id} CONTROL_ONLY", "", "Mechanical/raw evidence only; no scientific interpretation performed.", "", f"- Fixture: `CONTROL_ONLY`, mask `{CONTROL_MASK}`, STOP `120p`, DT `0.1p`.", f"- QB: `QB_BJ1_AREA={area}`, `QB_RJ1={rj1}`, `QB_IB={ib}`.", f"- Raw QA: `{qa['status']}`; required probes missing: `{missing}`.", f"- Registered pattern match: `{pattern_match}`.", "", "| metric | value |", "|---|---:|", f"| BJ1 forward max [turns, navigation] | {metrics['CONTROL_BJ1_forward_max_turn']} |", f"| BJ1 +0.5 time [ps] | {metrics['CONTROL_BJ1_t_plus_0p5_ps']} |", f"| BJ2 forward max [turns, navigation] | {metrics['CONTROL_BJ2_forward_max_turn']} |", f"| BJ2 +0.5 time [ps] | {metrics['CONTROL_BJ2_t_plus_0p5_ps']} |", f"| L1 min [A] | {metrics['CONTROL_L1_I_min']} |", f"| L1 max [A] | {metrics['CONTROL_L1_I_max']} |", f"| L1 zero-up [ps] | {metrics['CONTROL_L1_zero_cross_up_ps']} |", f"| terminal candidates | {metrics['CONTROL_terminal_candidate_count']} |", f"| terminal first peak [ps] | {metrics['CONTROL_terminal_first_peak_ps']} |", f"| terminal max peak [A] | {metrics['CONTROL_terminal_max_peak_A']} |", "", f"- Visualization: [{viz['review']}](/home/howard/JoSIM/{viz['review']}).", "- `terminal_candidate` is a mechanical positive-current locator, not an SFQ count.", ""]
    (case_root / "REVIEW_SUMMARY.md").write_text("\n".join(summary), encoding="utf-8")
    case_manifest = {"schema": "bvm-rloop-control-only-case-v1", "case_id": case_id, "fixture_mode": "CONTROL_ONLY", "parameters": params, "parent": parent, "source_manifest": {"path": repo_rel(case_root / "source_manifest.json"), "sha256": sha256(case_root / "source_manifest.json")}, "run_order": [run_id], "physical_solve_count": 1, "automatic_follow_up": False, "scientific_interpretation_performed": False}
    write_json(case_root / "case_manifest.json", case_manifest)
    result = {"schema": "bvm-rloop-control-only-result-v1", "case_id": case_id, "status": "CONTROL_ONLY_CASE_COMPLETE", "artifact_status": qa["status"], "physical_solve_count": 1, "pattern_match": pattern_match, "scientific_interpretation_performed": False}
    write_json(case_root / "result.json", result)
    return {"label": label, "case_id": case_id, "raw_path": repo_rel(raw), "raw_sha256": sha256(raw), "metrics": metrics, "qa": qa, "validation": validation, "visualization": viz}


def update_series_provenance(control_records: list[dict[str, Any]]) -> None:
    path = SERIES / "provenance.json"
    if not path.is_file():
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    data.setdefault("control_only_cases", {})
    for record in control_records:
        data["control_only_cases"][record["case_id"]] = record
    data["scientific_interpretation_performed"] = False
    data["automatic_follow_up"] = False
    write_json(path, data)


def run_b019_sweep() -> tuple[int, Path | None, str, str]:
    values = platform.load_env(USER_CONFIG)
    check_user_baseline(values)
    values.update({
        "NAME": "B019_QB_IB_downward",
        "MODE": "closed",
        "MASKS": "0000,0001,0011",
        "QB_BJ1_AREA": "0.75",
        "QB_RJ1": "32",
        "QB_IB": "260u",
        "SWEEP_ENABLED": "yes",
        "SWEEP_KEY": "QB_IB",
        "SWEEP_VALUES": ",".join(IB_VALUES),
        "SWEEP_REUSE_EXISTING": "yes",
    })
    validated = platform.validate({**values, "SWEEP_ENABLED": "no", "SWEEP_KEY": "NONE", "SWEEP_VALUES": ""}, platform.load_env(REFERENCE_CONFIG))
    if validated["MODE"] != "closed" or validated["MASKS"] != ["0000", "0001", "0011"]:
        raise RuntimeError("B019 static validation failed for mode/masks")
    BATCH_ROOT.mkdir(parents=True, exist_ok=True)
    (BATCH_ROOT / "B019_CONFIG_SNAPSHOT.env").write_text("# B019 sweep config snapshot\n" + "\n".join(f"{key}={values[key]}" for key in sorted(values)) + "\n", encoding="utf-8")
    with tempfile.NamedTemporaryFile(prefix="b019_", suffix=".env", dir="/tmp", mode="w", encoding="utf-8", delete=False) as handle:
        config_path = Path(handle.name)
        handle.write("\n".join(f"{key}={value}" for key, value in values.items()) + "\n")
    try:
        preview = subprocess.run([sys.executable, str(SERIES / "scripts" / "try_candidate.py"), "--config", str(config_path), "--dry-run"], cwd=REPO, capture_output=True, text=True, check=False)
        (BATCH_ROOT / "B019_DRY_RUN.txt").write_text(preview.stdout + "\n--- STDERR ---\n" + preview.stderr, encoding="utf-8")
        if preview.returncode != 0:
            raise RuntimeError(f"B019 dry-run failed before physical solve: {preview.stderr[-2000:]}")
        completed = subprocess.run([sys.executable, str(SERIES / "scripts" / "try_candidate.py"), "--config", str(config_path)], cwd=REPO, capture_output=True, text=True, check=False)
        (BATCH_ROOT / "B019_RUNNER.stdout").write_text(completed.stdout, encoding="utf-8")
        (BATCH_ROOT / "B019_RUNNER.stderr").write_text(completed.stderr, encoding="utf-8")
        # The platform allocates the next Bxxx name from every existing
        # batches/Bxxx_* directory.  B019's preflight directory therefore
        # cannot itself be the auto-created batch directory.  Locate the
        # actual generated manifest by registered sweep identity instead of
        # assuming its display name.
        candidates: list[Path] = []
        for candidate in (SERIES / "batches").iterdir():
            manifest_path = candidate / "BATCH_MANIFEST.json"
            if not manifest_path.is_file():
                continue
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            if manifest.get("sweep_key") == "QB_IB" and manifest.get("values") == list(IB_VALUES) and manifest.get("requested_masks") == ["0000", "0001", "0011"]:
                candidates.append(candidate)
        batch_root = max(candidates, key=lambda path: path.stat().st_mtime) if candidates else None
        return completed.returncode, batch_root, completed.stdout, completed.stderr
    finally:
        config_path.unlink(missing_ok=True)


def build_b019_report(batch_root: Path, controls: list[dict[str, Any]]) -> None:
    summary_path = batch_root / "BATCH_SUMMARY.csv"
    rows = list(csv.DictReader(summary_path.open(encoding="utf-8", newline="")))
    fields = ["IB", "ROLE", "MASK", "RUN_ID", "source_type", "raw_qa_status", "terminal_candidate_count", "terminal_first_peak_ps", "terminal_max_peak_A", "L1_I_max", "L1_zero_cross_up_ps", "BJ1_forward_max_turn", "BJ1_t_plus_0p5_ps", "BJ2_forward_max_turn", "BJ2_t_plus_0p5_ps", "CONTROL_BJ1_forward_max_turn", "CONTROL_BJ1_t_plus_0p5_ps", "CONTROL_BJ2_forward_max_turn", "CONTROL_BJ2_t_plus_0p5_ps", "CONTROL_L1_I_min", "CONTROL_L1_I_max", "CONTROL_L1_zero_cross_up_ps", "normal_protocol_control_terminal_candidate_count", "control_only_fixture_status", "control_only_case"]
    output: list[dict[str, Any]] = []
    by_value_mask = {(row.get("SWEEP_VALUE_RAW", ""), row.get("MASK", "")): row for row in rows}
    controls_by_ib = {"260u": next((item for item in controls if item["label"] == "C1"), None)}
    for value in IB_VALUES:
        for mask, role in (("0000", "N0"), ("0001", "N1"), ("0011", "N2")):
            row = by_value_mask.get((value, mask), {})
            output.append({"IB": value, "ROLE": role, "MASK": mask, "RUN_ID": row.get("RUN_ID"), "source_type": row.get("source_type"), "raw_qa_status": row.get("raw_qa_status"), "terminal_candidate_count": row.get("terminal_candidate_count"), "terminal_first_peak_ps": row.get("terminal_first_peak_ps"), "terminal_max_peak_A": row.get("terminal_max_peak_A"), "L1_I_max": row.get("QB_L1_I_max"), "L1_zero_cross_up_ps": row.get("QB_L1_zero_cross_up_ps"), "BJ1_forward_max_turn": row.get("BJ1_forward_max_turn"), "BJ1_t_plus_0p5_ps": row.get("BJ1_t_plus_0p5_ps"), "BJ2_forward_max_turn": row.get("BJ2_forward_max_turn"), "BJ2_t_plus_0p5_ps": row.get("BJ2_t_plus_0p5_ps"), "BJ1_forward_max_turn": row.get("BJ1_forward_max_turn"), "BJ1_t_plus_0p5_ps": row.get("BJ1_t_plus_0p5_ps"), "BJ2_forward_max_turn": row.get("BJ2_forward_max_turn"), "BJ2_t_plus_0p5_ps": row.get("BJ2_t_plus_0p5_ps"), "CONTROL_BJ1_forward_max_turn": row.get("CONTROL_BJ1_forward_max_turn"), "CONTROL_BJ1_t_plus_0p5_ps": row.get("CONTROL_BJ1_t_plus_0p5_ps"), "CONTROL_BJ2_forward_max_turn": row.get("CONTROL_BJ2_forward_max_turn"), "CONTROL_BJ2_t_plus_0p5_ps": row.get("CONTROL_BJ2_t_plus_0p5_ps"), "CONTROL_L1_I_min": row.get("CONTROL_L1_I_min"), "CONTROL_L1_I_max": row.get("CONTROL_L1_I_max"), "CONTROL_L1_zero_cross_up_ps": "", "normal_protocol_control_terminal_candidate_count": row.get("control_terminal_candidate_count"), "control_only_fixture_status": "C1_REFERENCE_ONLY" if value == "260u" else "NOT_RUN_IN_AUTHORIZED_MATRIX", "control_only_case": controls_by_ib["260u"]["case_id"] if value == "260u" and controls_by_ib["260u"] else ""})
        normal = by_value_mask.get((value, "0000"), {})
        output.append({"IB": value, "ROLE": "CONTROL", "MASK": "CONTROL_ONLY", "RUN_ID": "", "source_type": "CONTROL_ONLY_C1_REFERENCE" if value == "260u" else "NOT_RUN", "raw_qa_status": controls_by_ib["260u"]["qa"]["status"] if value == "260u" and controls_by_ib["260u"] else "NOT_RUN", "terminal_candidate_count": controls_by_ib["260u"]["metrics"]["CONTROL_terminal_candidate_count"] if value == "260u" and controls_by_ib["260u"] else "", "terminal_first_peak_ps": controls_by_ib["260u"]["metrics"]["CONTROL_terminal_first_peak_ps"] if value == "260u" and controls_by_ib["260u"] else "", "terminal_max_peak_A": controls_by_ib["260u"]["metrics"]["CONTROL_terminal_max_peak_A"] if value == "260u" and controls_by_ib["260u"] else "", "L1_I_max": controls_by_ib["260u"]["metrics"]["CONTROL_L1_I_max"] if value == "260u" and controls_by_ib["260u"] else "", "L1_zero_cross_up_ps": controls_by_ib["260u"]["metrics"]["CONTROL_L1_zero_cross_up_ps"] if value == "260u" and controls_by_ib["260u"] else "", "BJ1_forward_max_turn": controls_by_ib["260u"]["metrics"]["CONTROL_BJ1_forward_max_turn"] if value == "260u" and controls_by_ib["260u"] else "", "BJ1_t_plus_0p5_ps": controls_by_ib["260u"]["metrics"]["CONTROL_BJ1_t_plus_0p5_ps"] if value == "260u" and controls_by_ib["260u"] else "", "BJ2_forward_max_turn": controls_by_ib["260u"]["metrics"]["CONTROL_BJ2_forward_max_turn"] if value == "260u" and controls_by_ib["260u"] else "", "BJ2_t_plus_0p5_ps": controls_by_ib["260u"]["metrics"]["CONTROL_BJ2_t_plus_0p5_ps"] if value == "260u" and controls_by_ib["260u"] else "", "CONTROL_BJ1_forward_max_turn": controls_by_ib["260u"]["metrics"]["CONTROL_BJ1_forward_max_turn"] if value == "260u" and controls_by_ib["260u"] else "", "CONTROL_BJ1_t_plus_0p5_ps": controls_by_ib["260u"]["metrics"]["CONTROL_BJ1_t_plus_0p5_ps"] if value == "260u" and controls_by_ib["260u"] else "", "CONTROL_BJ2_forward_max_turn": controls_by_ib["260u"]["metrics"]["CONTROL_BJ2_forward_max_turn"] if value == "260u" and controls_by_ib["260u"] else "", "CONTROL_L1_I_min": controls_by_ib["260u"]["metrics"]["CONTROL_L1_I_min"] if value == "260u" and controls_by_ib["260u"] else "", "CONTROL_L1_I_max": controls_by_ib["260u"]["metrics"]["CONTROL_L1_I_max"] if value == "260u" and controls_by_ib["260u"] else "", "CONTROL_L1_zero_cross_up_ps": controls_by_ib["260u"]["metrics"]["CONTROL_L1_zero_cross_up_ps"] if value == "260u" and controls_by_ib["260u"] else "", "normal_protocol_control_terminal_candidate_count": normal.get("control_terminal_candidate_count", ""), "control_only_fixture_status": "C1_REFERENCE_ONLY" if value == "260u" else "NOT_RUN_IN_AUTHORIZED_MATRIX", "control_only_case": controls_by_ib["260u"]["case_id"] if value == "260u" and controls_by_ib["260u"] else ""})
    with (batch_root / "B019_METRICS.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader(); writer.writerows(output)
    qa = json.loads((batch_root / "BATCH_QA.json").read_text(encoding="utf-8"))
    execution = {"schema": "bvm-rloop-b019-execution-v1", "batch_id": batch_root.name, "control_only": controls, "batch_qa": qa, "physical_solve_count_normal_sweep": qa.get("new_physical_solve_count"), "reused_point_count": qa.get("reused_parameter_points"), "logical_run_count": qa.get("logical_run_count"), "scientific_interpretation_performed": False, "automatic_follow_up": False}
    write_json(batch_root / "B019_EXECUTION_MANIFEST.json", execution)
    lines = ["# B019 QB_IB downward — mechanical evidence review", "", "No scientific interpretation performed. `terminal_candidate` is a positive-current locator, not an SFQ count. P(...) values are raw radians; turn columns are independently unwrapped navigation metrics.", "", "## Authorized matrix", "", "- Normal closed sweep: `QB_IB=220u,230u,240u,250u,260u`; masks `0000,0001,0011`.", "- Logical runs: 15; new physical solves and strict reuse are recorded in `BATCH_QA.json`.", "- Control-only: only C0/C1 at `QB_IB=260u` were authorized before this sweep. Other IB control-only fixtures were not run.", "", "## C0/C1 gate", ""]
    for item in controls:
        m = item["metrics"]
        v = item["validation"]
        lines.append(f"- `{item['label']}` `{item['case_id']}`: raw QA `{item['qa']['status']}`, registered pattern match `{v['pattern_match']}`, terminal candidates `{m['CONTROL_terminal_candidate_count']}`, first peak `{m['CONTROL_terminal_first_peak_ps']} ps`, peak `{m['CONTROL_terminal_max_peak_A']} A`.")
    lines.extend(["", "## Per-IB rows", "", "See `B019_METRICS.csv`. CONTROL rows for 220–250u are explicitly `NOT_RUN_IN_AUTHORIZED_MATRIX`; normal-protocol control-window metrics are retained separately and are not treated as isolated CONTROL evidence.", "", "## Evidence status", "", "- Mechanical/raw evidence only.", "- No operating-window, mechanism, causal, or Gate conclusion is assigned.", "- No follow-up sweep was started.", ""])
    (batch_root / "B019_REVIEW.md").write_text("\n".join(lines), encoding="utf-8")


def dry_run() -> int:
    values = platform.load_env(USER_CONFIG)
    check_user_baseline(values)
    print("B019 PREVIEW")
    print("parent_head=8fcd69f1ead0861dc5c1e7c32659a21cc3a369df")
    print("control_only=C0(0.90,32,260u), C1(0.75,32,260u), mask=0000, stop=120p")
    print("sweep=QB_IB: " + ",".join(IB_VALUES))
    print("masks=0000,0001,0011; logical_runs=15; no solve executed")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.dry_run:
        return dry_run()
    if subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip() != "8fcd69f1ead0861dc5c1e7c32659a21cc3a369df":
        raise RuntimeError("registered B019 parent HEAD changed; stop before physical solve")
    BATCH_ROOT.mkdir(parents=True, exist_ok=True)
    controls: list[dict[str, Any]] = []
    for label, area, rj1, ib in CONTROL_CASES:
        print(f"RUN {label}: CONTROL_ONLY area={area} RJ1={rj1} IB={ib}", flush=True)
        controls.append(solve_control_case(label, area, rj1, ib))
        write_json(BATCH_ROOT / f"{label}_CONTROL_ONLY_RESULT.json", controls[-1])
    update_series_provenance(controls)
    gate = {item["label"]: item["validation"]["pattern_match"] and item["qa"]["status"] == "PASS" for item in controls}
    write_json(BATCH_ROOT / "CONTROL_ONLY_GATE.json", {"schema": "bvm-rloop-b019-control-gate-v1", "status": "PASS" if all(gate.values()) else "STOP", "cases": gate, "scientific_interpretation_performed": False})
    if not all(gate.values()):
        print(json.dumps({"status": "STOP_CONTROL_ONLY_GATE", "gate": gate}, ensure_ascii=False, indent=2))
        return 2
    print("CONTROL_ONLY_GATE PASS; running registered B019 normal sweep", flush=True)
    code, batch_root, stdout, stderr = run_b019_sweep()
    if batch_root is None:
        raise RuntimeError(f"B019 sweep did not create a complete batch; exit={code}; stderr={stderr[-2000:]}")
    if code != 0:
        print(json.dumps({"status": "B019_RUNNER_FAIL", "batch": repo_rel(batch_root), "exit_code": code}, ensure_ascii=False, indent=2))
        return code
    build_b019_report(batch_root, controls)
    print(json.dumps({"status": "B019_MECHANICAL_EVIDENCE_COMPLETE", "batch": repo_rel(batch_root), "control_cases": [item["case_id"] for item in controls], "scientific_interpretation_performed": False, "automatic_follow_up": False}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
