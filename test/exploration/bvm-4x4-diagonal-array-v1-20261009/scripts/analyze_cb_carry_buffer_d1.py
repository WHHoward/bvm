#!/usr/bin/env python3
"""Independent actual-grid mechanical arithmetic and classic paired plots."""

from __future__ import annotations

import csv
import hashlib
import html
import json
import math
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pandas as pd

import diagonal_platform as platform

SERIES = platform.SERIES
REPO = platform.REPO
RUNS = SERIES / "runs"
TASK = SERIES / "analysis" / "cb-carry-buffer-d1-20261009"
PLOTS = SERIES / "plots"
PHI0 = platform.PHI0
WINDOWS = {
    "ARRAY_FINAL_READ": (110.0, 121.0),
    "PRE_CLOCK": (121.0, 200.0),
    "CLOCK_EDGE": (200.0, 205.0),
    "POST_CLOCK": (205.0, 300.0),
    "TOTAL": (0.0, 300.0),
}
TRIPLETS = (
    ("ALL", "A021_CHAIN_ALL_GLOBAL_CLOCK", "A023_CB_DIRECT_D1_ALL_CLOCK",
     "A025_CARRY_CB_D1_ALL_CLOCK", "A021_A023_A025_COMMON.html"),
    ("PAPER", "A022_CHAIN_PAPER_GLOBAL_CLOCK", "A024_CB_DIRECT_D1_PAPER_CLOCK",
     "A026_CARRY_CB_D1_PAPER_CLOCK", "A022_A024_A026_COMMON.html"),
)
COMMON_SIGNALS = (
    "V(DOUT_D0)", "V(T1_I_D0)", "V(S_D0)", "V(C_D0)",
    "P(B_J1|XT1_D0)", "V(B_J1|XT1_D0)", "P(B_J9|XT1_D0)", "V(B_J9|XT1_D0)",
    "P(B_J10|XT1_D0)", "V(B_J10|XT1_D0)", "P(B_J11|XT1_D0)", "V(B_J11|XT1_D0)",
    "V(DOUT_D1)", "P(BJ1|XCB_D1_L2)", "V(BJ1|XCB_D1_L2)",
    "V(T1_I_D1)", "V(S_D1)", "V(C_D1)",
    "P(B_J1|XT1_D1)", "V(B_J1|XT1_D1)", "P(B_J9|XT1_D1)", "V(B_J9|XT1_D1)",
    "P(B_J10|XT1_D1)", "V(B_J10|XT1_D1)", "P(B_J11|XT1_D1)", "V(B_J11|XT1_D1)",
    "V(CLK_D1)", "V(DOUT_D2)", "V(T1_I_D2)", "V(S_D2)", "V(C_D2)", "V(CLK_D2)",
)
FOCUS_RUNS = tuple(dict.fromkeys(run_id for _name, *ids, _page in TRIPLETS for run_id in ids))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def jread(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_new(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def _trapz_actual(times_s: list[float], values: Any, indices: list[int]) -> float:
    total = 0.0
    for left, right in zip(indices, indices[1:]):
        total += 0.5 * (float(values[left]) + float(values[right])) * (times_s[right] - times_s[left])
    return total


def _unwrap_independent(values: Any) -> list[float]:
    if not values:
        return []
    output = [float(values[0])]
    two_pi = 2.0 * math.pi
    for previous_raw, current_raw in zip(values, values[1:]):
        delta = float(current_raw) - float(previous_raw)
        while delta > math.pi:
            delta -= two_pi
        while delta < -math.pi:
            delta += two_pi
        output.append(output[-1] + delta)
    return output


def _indices(times_s: list[float], name: str) -> list[int]:
    start_ps, end_ps = WINDOWS[name]
    return [index for index, value in enumerate(times_s)
            if start_ps <= value * 1e12 < end_ps]


def _run_identity(run_id: str) -> dict[str, Any]:
    run_dir = RUNS / run_id
    raw = run_dir / "raw.csv"
    result = jread(run_dir / "result.json")
    qa = jread(run_dir / "qa.json")
    raw_qa = jread(run_dir / "chain_qa.json")
    metrics = jread(run_dir / "metrics.json")
    probe = jread(run_dir / "probe_manifest.json")
    plot_qa = jread(run_dir / "plot_qa.json")
    digest = sha(raw)
    if (result.get("artifact_status") != "VALID" or result.get("physical_solve_count") != 1 or
            result.get("raw_sha256") != digest or qa.get("status") != "PASS" or
            qa.get("raw_sha256_before_analysis") != digest or qa.get("raw_sha256_after_analysis") != digest or
            raw_qa.get("status") != "PASS" or raw_qa.get("raw_sha256_after_analysis") != digest or
            metrics.get("raw_sha256") != digest or plot_qa.get("status") != "PASS" or
            plot_qa.get("raw_sha256_after") != digest or probe.get("profile") != "t1_chain_focus"):
        raise RuntimeError(f"artifact/QA/raw identity failure: {run_id}")
    for page in plot_qa.get("pages", []):
        path = SERIES / page["path"]
        if not path.is_file() or sha(path) != page.get("sha256"):
            raise RuntimeError(f"standalone plot SHA mismatch: {run_id}/{path.name}")
    return {"run_id": run_id, "run_dir": run_dir, "raw": raw, "raw_sha256": digest,
            "raw_bytes": raw.stat().st_size, "result": result, "qa": qa,
            "raw_qa": raw_qa, "metrics": metrics, "probe": probe, "plot_qa": plot_qa}


def _selected_signals(run: dict[str, Any], common: set[str] | None = None) -> list[str]:
    labels = [item["label"] for item in run["probe"]["signals"]]
    if common is not None:
        missing = sorted(common - set(labels))
        if missing:
            raise RuntimeError(f"common signal schema missing in {run['run_id']}: {missing}")
        return [signal for signal in labels if signal in common]
    selected = []
    for item in run["probe"]["signals"]:
        group = item.get("group", "")
        label = item["label"]
        if (group.startswith(("chain_input:D0", "chain_input:D1", "chain_t1:D0:",
                              "chain_t1:D1:", "chain_t1_jj:D0", "chain_t1_jj:D1",
                              "chain_cbu:D1", "chain_cbu_jj:D1", "chain_cbu_cb_direct:D1",
                              "chain_cbu_cb_carry_buffer:D1")) or label in
                {"V(T1_I_D2)", "V(S_D2)", "V(C_D2)", "V(CLK_D2)", "V(DOUT_D2)"}):
            selected.append(label)
    return list(dict.fromkeys(selected))


def _mechanical_metrics(run: dict[str, Any], signal_set: list[str]) -> tuple[list[dict], list[dict], dict]:
    raw_before = sha(run["raw"])
    times_s, columns, header = platform.read_raw(run["raw"], set(signal_set), exact_header=False)
    if raw_before != run["raw_sha256"] or len(times_s) != run["raw_qa"]["sample_count"]:
        raise RuntimeError(f"raw identity/sample-count changed: {run['run_id']}")
    if any(not math.isfinite(value) for value in times_s) or any(
            right <= left for left, right in zip(times_s, times_s[1:])):
        raise RuntimeError(f"non-finite or non-monotone actual raw time: {run['run_id']}")
    indexes = {name: _indices(times_s, name) for name in WINDOWS}
    for name, indices in indexes.items():
        if len(indices) < 2:
            raise RuntimeError(f"fewer than two actual samples in {name} for {run['run_id']}")

    waveforms, currents, junctions = [], [], []
    for signal in signal_set:
        values = columns[signal]
        for window, selected in indexes.items():
            selected_values = [float(values[i]) for i in selected]
            if signal.startswith("V("):
                high = max(selected, key=lambda i: values[i])
                low = min(selected, key=lambda i: values[i])
                area = _trapz_actual(times_s, values, selected)
                waveforms.append({"run_id": run["run_id"], "raw_sha256": raw_before,
                                  "signal": signal, "window": window, "unit": "V",
                                  "sample_count": len(selected), "min_v": values[low],
                                  "max_v": values[high], "p2p_v": values[high]-values[low],
                                  "time_of_min_ps": times_s[low]*1e12,
                                  "time_of_max_ps": times_s[high]*1e12,
                                  "signed_area_v_s": area, "area_phi0_arithmetic": area/PHI0,
                                  "integration": "actual stored timestamps; trapezoid; no interpolation"})
            elif signal.startswith("I("):
                charge = _trapz_actual(times_s, values, selected)
                currents.append({"run_id": run["run_id"], "raw_sha256": raw_before,
                                 "signal": signal, "window": window, "unit": "A",
                                 "sample_count": len(selected), "min_a": min(selected_values),
                                 "max_a": max(selected_values),
                                 "p2p_a": max(selected_values)-min(selected_values),
                                 "signed_charge_c": charge,
                                 "direction": next((item.get("direction") for item in run["probe"]["signals"]
                                                    if item["label"] == signal),
                                                   "JoSIM element-reference direction")})

    phase_labels = [signal for signal in signal_set if signal.startswith("P(")]
    for phase_signal in phase_labels:
        voltage_signal = f"V({phase_signal[2:]}"
        if voltage_signal not in columns:
            raise RuntimeError(f"same-JJ voltage probe absent for {phase_signal} in {run['run_id']}")
        unwrapped = _unwrap_independent(columns[phase_signal])
        voltage = columns[voltage_signal]
        for window, selected in indexes.items():
            first, last = selected[0], selected[-1]
            delta = unwrapped[last] - unwrapped[first]
            area = _trapz_actual(times_s, voltage, selected)
            junctions.append({"run_id": run["run_id"], "raw_sha256": raw_before,
                              "phase_signal": phase_signal, "voltage_signal": voltage_signal,
                              "window": window, "unit": "rad", "sample_count": len(selected),
                              "phase_delta_rad": delta,
                              "phase_delta_over_2pi_navigation": delta/(2.0*math.pi),
                              "same_jj_same_rows_v_area": area,
                              "v_area_over_phi0_arithmetic": area/PHI0,
                              "phase_minus_area_turns_arithmetic": delta/(2.0*math.pi)-area/PHI0,
                              "phase_raw_unit": "radians", "unwrapped_per_run": True,
                              "interpolation_or_resampling": False})
    raw_after = sha(run["raw"])
    qa = {"run_id": run["run_id"], "status": "PASS" if raw_after == raw_before else "FAIL",
          "raw_sha256_before": raw_before, "raw_sha256_after": raw_after,
          "sample_count": len(times_s), "header_count": len(header),
          "selected_signal_count": len(signal_set), "time_start_s": times_s[0],
          "time_end_s": times_s[-1],
          "dt_min_s": min(right-left for left, right in zip(times_s, times_s[1:])),
          "dt_max_s": max(right-left for left, right in zip(times_s, times_s[1:])),
          "time_monotone": True, "finite_values": True,
          "windows": {name: {"start_ps": WINDOWS[name][0], "end_ps": WINDOWS[name][1],
                             "boundary": "[start,end)", "sample_count": len(indices),
                             "first_stored_ps": times_s[indices[0]]*1e12,
                             "last_stored_ps": times_s[indices[-1]]*1e12}
                      for name, indices in indexes.items()},
          "integration": "actual stored timestamp rows; no interpolation/resampling"}
    if qa["status"] != "PASS":
        raise RuntimeError(f"raw changed during independent arithmetic: {run['run_id']}")
    return waveforms + currents, junctions, qa


def _classic_comparison_page(name: str, runs: list[dict[str, Any]], signals: list[str],
                             exact_grid: bool) -> dict[str, Any]:
    target = PLOTS / "comparison" / name
    if target.exists():
        raise FileExistsError(f"refusing to overwrite comparison page: {target}")
    plotter = platform._plotter_module()
    sections, records = [], []
    for run in runs:
        before = sha(run["raw"])
        times, columns, _header = platform.read_raw(run["raw"], set(signals))
        frame = pd.DataFrame({"time": times, **{signal: list(columns[signal]) for signal in signals}})
        fig = plotter.seperate_combined_layout(frame, SimpleNamespace(subset=signals, jump="2pi"))
        fig.update_layout(title=f"{run['run_id']} — common D0/D1/D2 boundaries",
                          template="plotly_dark", autosize=True, width=None)
        div = fig.to_html(full_html=False, include_plotlyjs=False,
                          config={"responsive": True})
        if "Plotly.newPlot" not in div or '"responsive": true' not in div or "staticPlot" in div:
            raise RuntimeError(f"classic interactive Plotly QA failed: {name}/{run['run_id']}")
        sections.append(f"<section><h2>{html.escape(run['run_id'])}</h2>"
                        f"<p>Raw SHA-256: <code>{run['raw_sha256']}</code>; samples: {len(times)}</p>{div}</section>")
        after = sha(run["raw"])
        if before != after:
            raise RuntimeError(f"raw changed during plot generation: {run['run_id']}")
        records.append({"run_id": run["run_id"], "raw_sha256_before": before,
                        "raw_sha256_after": after, "sample_count": len(times),
                        "signals": signals, "stored_grid_only": True})
    asset_ref = Path(os.path.relpath(platform.PLOTLY_ASSET, target.parent)).as_posix()
    document = ("<!doctype html><html><head><meta charset=\"utf-8\"><style>html,body,main{width:100%;margin:0;padding:0;}"
                "body{background:#111;color:#eee;overflow-x:hidden;}main{max-width:none;width:100%;}section{padding:8px 2%;}"
                f"</style><script src=\"{html.escape(asset_ref)}\"></script></head><body><main><h1>{html.escape(name)}</h1>"
                "<p>Classic josim-plot2 sep_comb/dark/-j 2pi; the same common signal schema is shown for each run on its native grid. "
                "No interpolation/resampling. Phase turns are rad/(2π) navigation arithmetic only, not event counts.</p>"
                f"<p>Exact stored grids identical: {str(exact_grid).lower()}.</p>" + "\n".join(sections) +
                "</main></body></html>\n")
    if document.count(asset_ref) != 1:
        raise RuntimeError(f"shared Plotly relative asset reference invalid: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(document, encoding="utf-8")
    if not target.is_file() or "Plotly.newPlot" not in document or '"responsive": true' not in document:
        raise RuntimeError(f"comparison HTML validation failed: {target}")
    return {"path": target.relative_to(SERIES).as_posix(), "sha256": sha(target),
            "status": "PASS", "renderer": "scripts/josim-plot2.py",
            "layout": "sep_comb/dark/-j 2pi", "shared_plotly_asset": asset_ref,
            "shared_plotly_asset_sha256": sha(platform.PLOTLY_ASSET),
            "signals": signals, "runs": records, "exact_stored_grids_identical": exact_grid,
            "interpolation_or_resampling": False}


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite mechanical table: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise RuntimeError(f"mechanical table is empty: {path}")
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def build(write: bool = True) -> dict[str, Any]:
    task_paths = (TASK / "BATCH_ANALYSIS.json", TASK / "CB_CARRY_BUFFER_METRICS.csv",
                  TASK / "SAME_JJ_PHASE_AREA.csv", TASK / "PAIRED_COMPARISON.csv",
                  TASK / "EVIDENCE_MANIFEST.md", TASK / "RESULT_BRIEF.md",
                  TASK / "RAW_ANALYSIS_HANDOFF_MANIFEST.json")
    if write and any(path.exists() for path in task_paths):
        raise RuntimeError("carry-buffer analysis artifact already exists; refusing overwrite")
    run_ids = list(FOCUS_RUNS)
    runs = {run_id: _run_identity(run_id) for run_id in run_ids}
    all_signals: dict[str, list[str]] = {}
    wave_rows, jj_rows, raw_qa_records = [], [], []
    for run_id, run in runs.items():
        signals = _selected_signals(run)
        all_signals[run_id] = signals
        waves, junctions, qa = _mechanical_metrics(run, signals)
        wave_rows.extend(waves)
        jj_rows.extend(junctions)
        raw_qa_records.append(qa)

    pair_rows, comparison_plots = [], []
    triplet_grids = {}
    for group, *items in TRIPLETS:
        baseline_id, direct_id, carry_id, page_name = items
        selected_runs = [runs[baseline_id], runs[direct_id], runs[carry_id]]
        common_set = set(COMMON_SIGNALS)
        grid_list = []
        for run in selected_runs:
            times, _columns, _header = platform.read_raw(run["raw"], common_set)
            grid_list.append(times)
        exact_grid = all(grid_list[0] == grid for grid in grid_list[1:])
        triplet_grids[group] = {"exact_stored_grids_identical": exact_grid,
                                "sample_count": [len(values) for values in grid_list]}
        # Pointwise metrics are never compared unless exact grids match.
        wave_index = {(row["run_id"], row["signal"], row["window"]): row for row in wave_rows}
        jj_index = {(row["run_id"], row["phase_signal"], row["window"]): row for row in jj_rows}
        current_index = {(row["run_id"], row["signal"], row["window"]): row for row in wave_rows
                         if row.get("unit") == "A"}
        for signal in COMMON_SIGNALS:
            metric_index = current_index if signal.startswith("I(") else wave_index if signal.startswith("V(") else jj_index
            for window in WINDOWS:
                records = [metric_index.get((run_id, signal, window)) for run_id in
                           (baseline_id, direct_id, carry_id)]
                if any(record is None for record in records):
                    raise RuntimeError(f"registered comparison arithmetic missing {signal}/{window}/{group}")
                row = {"comparison_group": group, "signal": signal, "window": window,
                       "unit": records[0]["unit"], "exact_grid_for_triplet": exact_grid,
                       "interpolation_or_resampling": False}
                for role, run_id, record in zip(("merge", "cb_direct", "carry_buffer"),
                                                (baseline_id, direct_id, carry_id), records, strict=True):
                    row[f"{role}_run_id"] = run_id
                    row[f"{role}_raw_sha256"] = record["raw_sha256"]
                    for key, value in record.items():
                        if key in {"run_id", "raw_sha256", "signal", "window", "unit", "direction"}:
                            continue
                        row[f"{role}_{key}"] = value
                pair_rows.append(row)
        comparison_plots.append(_classic_comparison_page(page_name, selected_runs,
                                                          list(COMMON_SIGNALS), exact_grid))

    if write:
        _write_csv(TASK / "CB_CARRY_BUFFER_METRICS.csv", wave_rows)
        _write_csv(TASK / "SAME_JJ_PHASE_AREA.csv", jj_rows)
        _write_csv(TASK / "PAIRED_COMPARISON.csv", pair_rows)
        raw_by_run = {run_id: {"path": runs[run_id]["raw"].relative_to(SERIES).as_posix(),
                               "sha256": runs[run_id]["raw_sha256"], "bytes": runs[run_id]["raw_bytes"],
                               "sample_count": runs[run_id]["raw_qa"]["sample_count"]}
                      for run_id in run_ids}
        batch_analysis = {"schema": "bvm-4x4-cb-carry-buffer-d1-analysis-v1", "status": "PASS",
                          "batch_id": "BVM4X4_CB_CARRY_BUFFER_D1_20261009",
                          "physical_solve_count": 2,
                          "new_run_ids": ["A025_CARRY_CB_D1_ALL_CLOCK", "A026_CARRY_CB_D1_PAPER_CLOCK"],
                          "raw_identity_and_qa": raw_qa_records,
                          "raw_sha256_by_run": {run_id: runs[run_id]["raw_sha256"] for run_id in run_ids},
                          "raw_bytes_by_run": {run_id: runs[run_id]["raw_bytes"] for run_id in run_ids},
                          "probe_signals_by_run": all_signals,
                          "triplet_grid_checks": triplet_grids,
                          "common_comparison_signals": list(COMMON_SIGNALS),
                          "registered_windows_ps": {name: list(bounds) for name, bounds in WINDOWS.items()},
                          "tables": {"waveforms_and_currents": (TASK / "CB_CARRY_BUFFER_METRICS.csv").relative_to(SERIES).as_posix(),
                                     "same_jj_phase_voltage": (TASK / "SAME_JJ_PHASE_AREA.csv").relative_to(SERIES).as_posix(),
                                     "paired_comparison": (TASK / "PAIRED_COMPARISON.csv").relative_to(SERIES).as_posix()},
                          "comparison_plots": comparison_plots,
                          "arithmetic": "actual stored timestamps, half-open windows, trapezoid integration; no resampling",
                          "phase": "raw radians; independent unwrap per run; delta/(2*pi) navigation only",
                          "event_classifier": None, "sfq_count_inference": "NOT_PERFORMED",
                          "scientific_interpretation_performed": False,
                          "timestep_convergence": "UNKNOWN_NOT_RUN",
                          "automatic_follow_up": False, "next_action": "STOP_AWAITING_USER_REVIEW"}
        write_new(TASK / "BATCH_ANALYSIS.json", batch_analysis)
        brief = ["# A025/A026 D1 carry-side CB_0928 — evidence handoff", "",
                 "- Artifact/mechanical status: `PASS`; physical solves: `2`; scientific interpretation: `NOT PERFORMED`.",
                 "- The registered matrix is A025 (1111/1111) and A026 (1101/1101), global single clock at 200 ps.",
                 "- The A021→A023→A025 and A022→A024→A026 tables contain only actual-grid descriptive metrics; they do not classify SFQ events or mechanism.",
                 "- `P(...)` is stored in radians. `delta/(2π)` and voltage-area/Φ0 are navigation/arithmetic columns, not event counts.",
                 "- Same-JJ phase/voltage arithmetic uses identical raw samples and half-open registered windows; interpolation/resampling was not used.",
                 "- Timestep convergence: `UNKNOWN`; no follow-up solve authorized.", "",
                 "| Run | Raw bytes | Raw SHA-256 | Sample count | Mechanical QA |",
                 "|---|---:|---|---:|---|"]
        for run_id in run_ids:
            r = runs[run_id]
            brief.append(f"| {run_id} | {r['raw_bytes']} | `{r['raw_sha256']}` | {r['raw_qa']['sample_count']} | PASS |")
        brief.extend(["", "Machine-readable arithmetic: `BATCH_ANALYSIS.json` and the CSV tables in this directory.",
                      "Standalone run HTML and the two classic common-signal triplet pages are under `plots/` and are not packaged.",
                      "No mechanism, isolation, SFQ-count, or multiplier-function conclusion is issued."])
        (TASK / "RESULT_BRIEF.md").write_text("\n".join(brief) + "\n", encoding="utf-8")
        evidence_lines = ["# Evidence manifest", "",
                          "This work unit follows `docs/EXPERIMENT_CONTRACT.md`. Raw CSVs are immutable.", "",
                          "| Run | Raw path | Raw SHA-256 | Bytes |", "|---|---|---|---:|"]
        for run_id in run_ids:
            r = runs[run_id]
            evidence_lines.append(f"| {run_id} | `{r['raw'].relative_to(SERIES).as_posix()}` | `{r['raw_sha256']}` | {r['raw_bytes']} |")
        evidence_lines.extend(["", "The A021/A022, A023/A024 and A025/A026 common-boundary comparisons use identical label schemas and native stored grids; see `BATCH_ANALYSIS.json`.",
                               "All HTML remains local and is excluded from ZIP archives.",
                               "Scientific interpretation: `NOT PERFORMED`; automatic follow-up: `NONE`."])
        (TASK / "EVIDENCE_MANIFEST.md").write_text("\n".join(evidence_lines) + "\n", encoding="utf-8")
        handoff = {"schema": "bvm-raw-analysis-handoff-v1", "analysis_id": "bvm-4x4-cb-carry-buffer-d1-20261009",
                   "analysis_scope": {"source_runs": run_ids, "read_only_raw": True,
                                      "solver_authorized": False, "circuit_or_parameter_changes": False,
                                      "windows_ps": {name: list(bounds) for name, bounds in WINDOWS.items()},
                                      "signals": all_signals},
                   "raw_by_run": raw_by_run, "transformations": [],
                   "visualization": {"renderer": "scripts/josim-plot2.py", "layout": "sep_comb/dark/-j 2pi",
                                     "html_local_only": True, "files": comparison_plots},
                   "scientific_interpretation_performed": False}
        write_new(TASK / "RAW_ANALYSIS_HANDOFF_MANIFEST.json", handoff)
        if sha(runs["A025_CARRY_CB_D1_ALL_CLOCK"]["raw"]) != runs["A025_CARRY_CB_D1_ALL_CLOCK"]["raw_sha256"] or \
                sha(runs["A026_CARRY_CB_D1_PAPER_CLOCK"]["raw"]) != runs["A026_CARRY_CB_D1_PAPER_CLOCK"]["raw_sha256"]:
            raise RuntimeError("new raw changed after arithmetic/visualization")
    return {"status": "PASS", "runs": run_ids, "physical_solve_count": 2,
            "raw_sha256_by_run": {run_id: runs[run_id]["raw_sha256"] for run_id in run_ids},
            "triplet_grid_checks": triplet_grids,
            "scientific_interpretation_performed": False}


def main() -> int:
    if sys.argv[1:] != ["--write"]:
        print("usage: analyze_cb_carry_buffer_d1.py --write", file=sys.stderr)
        return 2
    try:
        result = build(write=True)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(f"ANALYSIS_FAILURE_RAW_PRESERVED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
