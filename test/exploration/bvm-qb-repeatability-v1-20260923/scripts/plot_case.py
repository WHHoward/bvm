#!/usr/bin/env python3
"""Classic JoSIM plot2 figures and compact one-shot-style run pages."""

from __future__ import annotations

import argparse
import csv
import html
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from common import PLOTTER, ROOT, REPO, read_json, repo_rel, resolve_run_dir, sha256, write_json


def raw_header(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8", newline="") as stream:
        return next(csv.reader(stream))


def externalize_plotly(html_path: Path, asset_path: Path) -> None:
    source = html_path.read_text(encoding="utf-8")
    scripts = list(re.finditer(r"<script(?P<attrs>[^>]*)>(?P<body>.*?)</script>", source,
                               flags=re.DOTALL | re.IGNORECASE))
    runtime = next((item for item in scripts
                    if len(item.group("body")) > 1_000_000 and
                    ("plotly.js v" in item.group("body") or "var Plotly=" in item.group("body"))), None)
    if runtime is None:
        raise ValueError(f"embedded Plotly runtime not found in {html_path}")
    body = runtime.group("body")
    asset_path.parent.mkdir(parents=True, exist_ok=True)
    if asset_path.exists() and asset_path.read_text(encoding="utf-8") != body:
        raise ValueError("Plotly runtime changed within this experiment; preserve old pages and investigate")
    if not asset_path.exists():
        asset_path.write_text(body, encoding="utf-8")
    relative_asset = Path(os.path.relpath(asset_path, html_path.parent)).as_posix()
    compact = source[:runtime.start()] + f'<script src="{relative_asset}"></script>' + source[runtime.end():]
    if any(token in compact for token in ("plotly.js v", "var Plotly=", "cdn.plot.ly")):
        raise ValueError(f"Plotly externalization failed for {html_path}")
    html_path.write_text(compact, encoding="utf-8")


def write_grid_subset(raw: Path, output: Path, signals: list[str], window: list[float],
                      source_sha: str, run_id: str) -> dict[str, Any]:
    start, end = window
    output.parent.mkdir(parents=True, exist_ok=True)
    rows_kept: list[dict[str, str]] = []
    headers: list[str] = []
    with raw.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        headers = reader.fieldnames or []
        selected = ["time", *signals]
        missing = [signal for signal in selected if signal not in headers]
        if missing:
            raise ValueError(f"focused plot requests absent raw columns: {missing}")
        for row in reader:
            time_ps = float(row["time"]) * 1e12
            if start <= time_ps < end:
                rows_kept.append({key: row[key] for key in selected})
    if len(rows_kept) < 2:
        raise ValueError(f"focused raw-grid subset has fewer than two samples in [{start:g},{end:g}) ps")
    with output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["time", *signals])
        writer.writeheader()
        writer.writerows(rows_kept)
    actual_start = float(rows_kept[0]["time"]) * 1e12
    actual_end = float(rows_kept[-1]["time"]) * 1e12
    sidecar = {
        "schema": "bvm-qb-repeatability-plot-grid-subset-v1",
        "run_id": run_id, "source_raw_path": repo_rel(raw), "source_raw_sha256": source_sha,
        "derived_input_path": repo_rel(output), "derived_input_sha256": sha256(output),
        "registered_window_ps": [start, end], "window_semantics": "[start,end)",
        "actual_first_sample_ps": actual_start, "actual_last_sample_ps": actual_end,
        "sample_count": len(rows_kept), "selected_raw_signals": signals,
        "transformation": "project selected direct raw columns and retain only actual stored rows in a half-open time window",
        "interpolation": False, "resampling": False, "smoothing": False,
    }
    sidecar_path = output.with_suffix(output.suffix + ".metadata.json")
    write_json(sidecar_path, sidecar)
    return sidecar


def render_classic(raw_input: Path, output: Path, signals: list[str], title: str,
                   asset: Path, source_raw: Path, source_raw_sha: str,
                   subset_metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    if not 2 <= len(signals) <= 5:
        raise ValueError(f"classic grouped plots require 2–5 exact signals, got {len(signals)} for {title}")
    columns = raw_header(raw_input)
    if len(columns) != len(set(columns)):
        raise ValueError(f"duplicate raw column label in plot input {raw_input}")
    missing = [signal for signal in signals if signal not in columns]
    if missing:
        raise ValueError(f"plot requests absent exact signal labels: {missing}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="bvm_repeat_plot_") as tmp:
        temp_html = Path(tmp) / "plot.html"
        command = [sys.executable, str(PLOTTER), str(raw_input), "-x", str(temp_html),
                   "-t", "sep_comb", "-c", "dark", "-j", "2pi", "-w", title,
                   "-s", *signals]
        completed = subprocess.run(command, cwd=REPO, capture_output=True, text=True, check=False)
        if completed.returncode != 0 or not temp_html.is_file():
            raise RuntimeError(f"josim-plot2 failed for {title}: {completed.stderr[-1500:]}")
        output.write_text(temp_html.read_text(encoding="utf-8"), encoding="utf-8")
    externalize_plotly(output, asset)
    record = {
        "title": title, "path": repo_rel(output), "sha256": sha256(output),
        "raw_path": repo_rel(source_raw), "raw_sha256": source_raw_sha,
        "plot_input_path": repo_rel(raw_input), "plot_input_sha256": sha256(raw_input),
        "signals": signals, "renderer": repo_rel(PLOTTER),
        "renderer_arguments": ["-t", "sep_comb", "-c", "dark", "-j", "2pi"],
        "phase_display": "raw P(...) is radians; -j 2pi displays navigation turns only",
        "descriptive_only": True,
    }
    if subset_metadata:
        record["stored_grid_subset"] = subset_metadata
    return record


def groups_for_run(headers: list[str], params: dict[str, Any], cycles: list[dict[str, Any]]) -> dict[str, list[tuple[str, list[str], list[float] | None]]]:
    size = int(params["ARRAY_SIZE"])
    groups: dict[str, list[tuple[str, list[str], list[float] | None]]] = {
        "01_SIGNAL_TIMING": [], "02_BVM_STATE": [], "03_JSL_CHAIN": [],
        "04_QB_STATE": [], "05_JTL_CHAIN": [],
    }

    def add(section: str, stem: str, signals: list[str], window: list[float] | None = None) -> None:
        actual = [signal for signal in signals if signal in headers]
        if len(actual) < 2:
            return
        if len(actual) > 5:
            raise ValueError(f"plot group {stem} exceeds the 2–5 signal classic layout contract")
        groups[section].append((stem, actual, window))

    # Whole-run inputs and source/output overlays, one BVM per focused view.
    for index in range(1, size + 1):
        add("01_SIGNAL_TIMING", f"input_to_output_BVM{index}",
            [f"I(I_{signal}{index})" for signal in ("WL", "BL", "SE")] + ["V(QBOUT)", "V(R_TERM)"])
    active_indices = [i for i, bit in enumerate(str(params["MASK"]), start=1) if bit == "1"]
    for cycle in cycles:
        cycle_id = int(cycle["cycle_index"])
        win = cycle["cycle_window_ps"]
        if active_indices:
            add("01_SIGNAL_TIMING", f"read_cycle_{cycle_id:02d}_stimulus_output",
                [f"I(I_SE{i})" for i in active_indices] + ["V(QBOUT)", "V(R_TERM)"], win)
        else:
            add("01_SIGNAL_TIMING", f"read_cycle_{cycle_id:02d}_zero_mask_output",
                ["V(QBIN)", "V(QBOUT)", "V(R_TERM)"], win)

    # BVM internal states, grouped per cell in the same compact style as the reference platform.
    for index in range(1, size + 1):
        add("02_BVM_STATE", f"BVM{index}_storage_state",
            [f"P(B_JM1|XBVM{index})", f"P(B_JM2|XBVM{index})",
             f"I(L_M1|XBVM{index})", f"I(L_M2|XBVM{index})", f"I(L_M3|XBVM{index})"])
        add("02_BVM_STATE", f"BVM{index}_rloop_state",
            [f"P(B_JS1|XBVM{index})", f"P(B_JS2|XBVM{index})",
             f"I(L_S1|XBVM{index})", f"I(L_S2|XBVM{index})", f"I(L_S3|XBVM{index})"])
        add("02_BVM_STATE", f"BVM{index}_output_boundary",
            [f"I(L_PSL|XBVM{index})", f"I(R_SL|XBVM{index})", f"I(L_SL|XBVM{index})"])

    # All eight JSL stages are represented, with explicit input and output boundaries.
    for prefix in ("P", "I"):
        for start, end in ((1, 4), (5, 8)):
            labels = [f"{prefix}(B_JSL{i})" for i in range(start, end + 1)]
            add("03_JSL_CHAIN", f"JSL_{prefix}_{start}_{end}", labels)
    add("03_JSL_CHAIN", "COMMON_SL_to_QBIN_boundaries", ["V(COMMON_SL)", "V(QBIN)", "I(B_JSL1)", "I(B_JSL8)"])

    # QB interface and internal currents/states.
    add("04_QB_STATE", "QB_junction_phase", [f"P({jj}|XBQ1)" for jj in ("BJS", "BJ1", "BJ2")])
    add("04_QB_STATE", "QB_inductor_currents", [f"I({name}|XBQ1)" for name in ("LIN", "L1", "L2", "L3")])
    add("04_QB_STATE", "QB_input_output_boundaries", ["V(QBIN)", "V(QBOUT)", "V(R_TERM)"])

    # Compact phase-through-chain views cover all six cells and both junctions.
    for junction in ("B01", "B02"):
        for start, end in ((1, 3), (4, 6)):
            add("05_JTL_CHAIN", f"JTL_{junction}_phase_{start}_{end}",
                [f"P({junction}|XJTL1_{stage})" for stage in range(start, end + 1)])
    add("05_JTL_CHAIN", "JTL_outputs_and_terminal",
        ["V(QBOUT)", "V(JTL1_OUT)", "V(JTL3_OUT)", "V(JTL6_OUT)", "V(R_TERM)"])
    return groups


def q(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.6g}"
    return html.escape(str(value))


def render_pages(run_dir: Path, metadata: dict[str, Any], plot_entries: list[dict[str, Any]]) -> None:
    params = metadata["parameters"]
    snapshot = read_json(run_dir / "stimulus_snapshot.json")
    result_path = run_dir / "result.json"
    result = read_json(result_path) if result_path.is_file() else {}
    def links(section: str) -> str:
        entries = [item for item in plot_entries if item["section"] == section]
        return "<ul>" + "".join(
            f"<li><a href='{html.escape(os.path.relpath(REPO / item['path'], run_dir / 'plots'))}'>{html.escape(item['title'])}</a>"
            f" — {html.escape(', '.join(item['signals']))}</li>" for item in entries) + "</ul>"

    style = "body{font-family:Arial,sans-serif;background:#111;color:#eee;margin:24px;line-height:1.45}a{color:#8ecbff}table{border-collapse:collapse;width:100%;margin:12px 0 26px}th,td{border:1px solid #555;padding:6px 8px;text-align:left;font-size:13px}th{background:#262626}section{margin:28px 0;padding:14px;border:1px solid #444;border-radius:6px}code{color:#ffd580}small{color:#aaa}"
    rows = "".join(f"<tr><th>{html.escape(key)}</th><td><code>{q(value)}</code></td></tr>"
                    for key, value in params.items()
                    if key in {"TEST_MODE", "CANDIDATE", "ARRAY_SIZE", "MASK", "BIT_ORDER", "DT", "STOP", "STOP_PS", "READ_COUNT", "READ_PERIOD_PS", "STATE_SEQUENCE"})
    schedule_rows = "".join(f"<tr><td>{item['ordinal']}</td><td>{q(item.get('state'))}</td><td>{q(item['read_start_ps'])}</td><td>{q(item['read_end_ps'])}</td></tr>"
                             for item in snapshot["read_schedule"])
    body = ["<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>",
            f"<title>{html.escape(run_dir.name)} review</title><style>{style}</style></head><body>",
            f"<h1>{html.escape(run_dir.name)}</h1>",
            "<p>Compact descriptive run review. Raw phase is radians; turns are navigation only. No scientific interpretation is performed.</p>",
            f"<p>Artifact status: <b>{html.escape(str(result.get('artifact_status','PENDING')))}</b></p>",
            "<h2>Resolved run configuration</h2><table>" + rows + "</table>",
            "<h2>Registered read schedule</h2><table><tr><th>cycle</th><th>state/mask</th><th>READ start ps</th><th>READ end ps</th></tr>" + schedule_rows + "</table>",
            "<section><h2>01_SIGNAL_TIMING</h2><p>Whole-run excitation/output views and non-overlapping raw-grid READ-cycle views.</p>" + links("01_SIGNAL_TIMING") + "</section>",
            "<section><h2>02_BVM_STATE</h2><p>Per-BVM storage, R-loop and output-boundary grouped raw plots.</p>" + links("02_BVM_STATE") + "</section>",
            "<section><h2>03_JSL_CHAIN</h2><p>Input boundary → all eight JSL stages → QBIN boundary.</p>" + links("03_JSL_CHAIN") + "</section>",
            "<section><h2>04_QB_STATE</h2><p>QB input boundary, internal JJ/inductor branches and output boundary.</p>" + links("04_QB_STATE") + "</section>",
            "<section><h2>05_JTL_CHAIN</h2><p>Every JTL stage is probed; grouped plots are descriptive only.</p>" + links("05_JTL_CHAIN") + "</section>",
            "<section><h2>Cycle, candidate and recovery data</h2><ul>",
            "<li><a href='../analysis/cycle_metrics.csv'>cycle_metrics.csv</a> / <a href='../analysis/cycle_metrics.json'>cycle_metrics.json</a></li>",
            "<li><a href='../analysis/state_windows.csv'>PRE / READ / POST / NEXT_PRE state windows</a></li>",
            "<li><a href='../analysis/event_assignment.csv'>candidate assignment table</a> / <a href='../analysis/event_assignment.json'>candidate assignment JSON</a></li>",
            "<li><a href='../analysis/jtl_chain_assignment.csv'>ordered JTL1…JTL6 candidate-path table</a></li>",
            "<li><a href='../analysis/recovery_trace.csv'>component-level recovery trace</a> / <a href='../analysis/recovery_metrics.json'>recovery metrics</a></li>",
            "<li><a href='../analysis/analysis_qa.json'>analysis QA</a> · <a href='../analysis/plot_qa.json'>plot QA</a></li></ul></section>",
            "<h2>Immutable run evidence</h2><ul>",
            "<li><a href='../raw.csv'>raw.csv</a> · <a href='../actual_deck.cir'>actual_deck.cir</a> · <a href='../stimulus.inc'>stimulus.inc</a></li>",
            "<li><a href='../config_snapshot.env'>config_snapshot.env</a> · <a href='../stimulus_snapshot.json'>stimulus_snapshot.json</a> · <a href='../source_manifest.json'>source_manifest.json</a></li>",
            "</ul><small>Renderer: scripts/josim-plot2.py, sep_comb/dark/-j 2pi. The plotted raw P(...) unit is radians; conversion to turns is navigation only.</small>",
            "</body></html>"]
    if (run_dir / "analysis" / "ANALYSIS_RECOVERY.md").is_file():
        body.insert(-1, "<section><h2>Analysis recovery</h2><p>This immutable raw was reanalyzed without another solver run. "
                          "The prior failed analysis record is preserved under <a href='../analysis/attempts/ANALYSIS_ATTEMPT1/'>analysis/attempts/ANALYSIS_ATTEMPT1/</a>.</p></section>")
    review = run_dir / "plots" / "review.html"
    review.write_text("\n".join(body), encoding="utf-8")

    stimulus_entries = [item for item in plot_entries if item["section"] == "01_SIGNAL_TIMING"]
    stim_body = ["<!doctype html><html><head><meta charset='utf-8'>",
                 f"<title>{html.escape(run_dir.name)} stimulus</title><style>{style}</style></head><body>",
                 f"<h1>{html.escape(run_dir.name)} — stimulus and output</h1>",
                 "<p>Each input/output figure uses excitation currents and QB/JTL terminal voltages from the same run raw.csv.</p><ul>"]
    for item in stimulus_entries:
        rel = os.path.relpath(REPO / item["path"], run_dir / "plots")
        stim_body.append(f"<li><a href='{html.escape(rel)}'>{html.escape(item['title'])}</a> — {html.escape(', '.join(item['signals']))}</li>")
    stim_body.extend(["</ul><p><a href='review.html'>Back to run review</a></p></body></html>"])
    (run_dir / "plots" / "stimulus.html").write_text("\n".join(stim_body), encoding="utf-8")


def render_run(run_dir: Path) -> dict[str, Any]:
    resolved_run_dir = resolve_run_dir(run_dir.name)
    if run_dir.resolve() != resolved_run_dir:
        raise ValueError("plot path must resolve to one direct child under this experiment's runs/")
    run_dir = resolved_run_dir
    raw = run_dir / "raw.csv"
    raw_before = sha256(raw)
    metadata = read_json(run_dir / "metadata.json")
    stimulus_snapshot = read_json(run_dir / "stimulus_snapshot.json")
    params = metadata["parameters"]
    headers = raw_header(raw)
    if len(headers) != len(set(headers)):
        raise ValueError("raw file has duplicate labels; classic plot selection refuses implicit columns")
    groups = groups_for_run(headers, params, stimulus_snapshot["registered_windows"])
    plot_root = run_dir / "plots"
    asset = ROOT / "plots" / "assets" / "plotly.min.js"
    entries: list[dict[str, Any]] = []
    for section, group_rows in groups.items():
        for stem, signals, window in group_rows:
            title = f"{run_dir.name} — {section} — {stem}"
            if window is None:
                plot_input = raw
                subset = None
            else:
                plot_input = plot_root / "plot_inputs" / f"{stem}.csv"
                subset = write_grid_subset(raw, plot_input, signals, window, raw_before, run_dir.name)
            output = plot_root / "groups" / f"{stem}.html"
            record = render_classic(plot_input, output, signals, title, asset, raw, raw_before, subset)
            record["section"] = section
            record["stem"] = stem
            entries.append(record)
    if sha256(raw) != raw_before:
        raise ValueError("raw hash changed while plotting")
    manifest = {"schema": "bvm-qb-repeatability-plot-manifest-v1", "run_id": run_dir.name,
                "renderer": repo_rel(PLOTTER), "layout": "CLASSIC_LOCKED sep_comb dark phase rad/(2pi) turns navigation",
                "raw_path": repo_rel(raw), "raw_sha256": raw_before,
                "entries": entries, "review_page": repo_rel(plot_root / "review.html"),
                "stimulus_page": repo_rel(plot_root / "stimulus.html"),
                "no_cards_or_iframes": True, "scientific_interpretation_performed": False}
    render_pages(run_dir, metadata, entries)
    manifest["review_page_sha256"] = sha256(plot_root / "review.html")
    manifest["stimulus_page_sha256"] = sha256(plot_root / "stimulus.html")
    write_json(plot_root / "plot_manifest.json", manifest)
    invalid_pages = []
    invalid_entries = []
    raw_columns = set(headers)
    for entry in entries:
        page = REPO / entry["path"]
        page_text = page.read_text(encoding="utf-8", errors="replace")
        if any(token in page_text for token in ("Unknown", "cdn.plot.ly", "plotly.js v", "var Plotly=")):
            invalid_pages.append(entry["path"])
        if not (2 <= len(entry["signals"]) <= 5) or any(signal not in raw_columns for signal in entry["signals"]):
            invalid_entries.append(entry["path"])
        subset = entry.get("stored_grid_subset")
        if subset:
            derived = REPO / subset["derived_input_path"]
            if (not derived.is_file() or sha256(derived) != subset["derived_input_sha256"] or
                    subset["source_raw_sha256"] != raw_before or
                    subset["interpolation"] or subset["resampling"] or subset["smoothing"]):
                invalid_entries.append(entry["path"])
    review_path = plot_root / "review.html"
    stimulus_path = plot_root / "stimulus.html"
    review_text = review_path.read_text(encoding="utf-8") if review_path.is_file() else ""
    stimulus_text = stimulus_path.read_text(encoding="utf-8") if stimulus_path.is_file() else ""
    required_sections = ("01_SIGNAL_TIMING", "02_BVM_STATE", "03_JSL_CHAIN", "04_QB_STATE", "05_JTL_CHAIN")
    missing_sections = [section for section in required_sections if section not in review_text]
    stimulus_entries = [item for item in entries if item["section"] == "01_SIGNAL_TIMING" and
                        item["stem"].startswith("input_to_output_BVM")]
    combined_signal_coverage = {}
    for index in range(1, int(params["ARRAY_SIZE"]) + 1):
        stem = f"input_to_output_BVM{index}"
        entry = next((item for item in stimulus_entries if item["stem"] == stem), None)
        expected = [f"I(I_WL{index})", f"I(I_BL{index})", f"I(I_SE{index})", "V(QBOUT)", "V(R_TERM)"]
        combined_signal_coverage[stem] = {
            "expected_signals": expected,
            "present_signals": [signal for signal in expected if entry and signal in entry["signals"]],
            "same_classic_plot": bool(entry and all(signal in entry["signals"] for signal in expected)),
            "renderer": entry.get("renderer") if entry else None,
            "renderer_arguments": entry.get("renderer_arguments") if entry else None,
        }
    combined_plots_pass = (len(stimulus_entries) == int(params["ARRAY_SIZE"]) and
                           all(item["same_classic_plot"] and
                               item["renderer_arguments"] == ["-t", "sep_comb", "-c", "dark", "-j", "2pi"]
                               for item in combined_signal_coverage.values()))
    page_links_present = ("input/output figure" in stimulus_text and
                          all(section in review_text for section in required_sections) and
                          all(item["title"] in stimulus_text for item in stimulus_entries))
    no_custom_visual_shell = "<iframe" not in review_text.lower() and "<svg" not in review_text.lower()
    qa = {"schema": "bvm-qb-repeatability-plot-qa-v1",
          "status": "PASS" if entries and not invalid_pages and not invalid_entries and not missing_sections and page_links_present and combined_plots_pass and no_custom_visual_shell and sha256(raw) == raw_before else "FAIL",
          "run_id": run_dir.name, "plot_count": len(entries), "raw_sha256": raw_before,
          "raw_hash_unchanged": sha256(raw) == raw_before,
          "renderer": repo_rel(PLOTTER), "layout": "sep_comb/dark/-j 2pi",
          "invalid_pages": invalid_pages, "invalid_plot_entries": invalid_entries,
          "missing_semantic_sections": missing_sections, "review_page_exists": review_path.is_file(),
          "stimulus_page_exists": stimulus_path.is_file(), "input_output_combined_page": page_links_present,
          "combined_excitation_and_output_plot_count": len(stimulus_entries),
          "combined_excitation_output_signal_coverage": combined_signal_coverage,
          "all_excitation_and_output_signals_share_classic_plot": combined_plots_pass,
          "review_page_sha256": manifest["review_page_sha256"],
          "stimulus_page_sha256": manifest["stimulus_page_sha256"],
          "plot_manifest_sha256": sha256(plot_root / "plot_manifest.json"),
          "separate_review_and_stimulus_pages": True,
          "no_custom_svg_or_iframe_visual_shell": no_custom_visual_shell,
          "classic_figures_only_no_cards_or_iframes": True,
          "phase_turns_are_navigation_only": True, "descriptive_only": True}
    write_json(plot_root / "plot_qa.json", qa)
    return qa


def main() -> int:
    parser = argparse.ArgumentParser(description="Render one run with classic josim-plot2 grouped pages")
    parser.add_argument("run_id")
    args = parser.parse_args()
    qa = render_run(resolve_run_dir(args.run_id))
    print(json.dumps(qa, ensure_ascii=False, indent=2))
    return 0 if qa["status"] == "PASS" else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, ValueError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
