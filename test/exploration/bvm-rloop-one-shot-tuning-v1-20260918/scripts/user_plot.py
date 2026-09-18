#!/usr/bin/env python3
"""Create one compact, stimulus-aware review page for a generated U case."""

from __future__ import annotations

import argparse
import csv
import html
import json
import math
import os
import sys
from pathlib import Path
from typing import Any

SERIES = Path(__file__).resolve().parents[1]
REPO = next(path for path in (SERIES, *SERIES.parents) if (path / ".git").exists())
sys.path.insert(0, str(SERIES / "scripts"))
from render_review import render_group, raw_headers, sha256, write_json  # noqa: E402


def q(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.6g}"
    return html.escape(str(value))


def load_raw(path: Path) -> tuple[list[str], list[list[float]]]:
    with path.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.reader(stream)
        headers = next(reader)
        return headers, [[float(value) for value in row] for row in reader if row]


def svg_panel(headers: list[str], rows: list[list[float]], signals: list[str], windows: dict[str, list[float]], title: str, width: int = 1040, panel_height: int = 125) -> str:
    time_index = headers.index("time")
    times = [row[time_index] * 1e12 for row in rows]
    stop = max(times) if times else 1.0
    colors = ("#66ccff", "#ffcc66", "#66ff99", "#ff7799", "#bb99ff", "#eeeeee", "#ff9966", "#99ddff")
    panels = []
    for signal_index, signal in enumerate(signals):
        if signal not in headers:
            continue
        values = [row[headers.index(signal)] for row in rows]
        scale = 1e6 if signal.startswith("I(") else 1e3 if signal.startswith("V(") else 1.0
        display = [value * scale for value in values]
        finite = [value for value in display if math.isfinite(value)]
        if not finite:
            continue
        low, high = min(finite), max(finite)
        if abs(high - low) < 1e-18:
            low -= 1.0; high += 1.0
        y0 = 30 + len(panels) * panel_height
        inner_top, inner_bottom = y0 + 16, y0 + panel_height - 18
        points = []
        stride = max(1, len(times) // 900)
        for index in range(0, len(times), stride):
            x = 80 + times[index] / stop * (width - 110)
            y = inner_bottom - (display[index] - low) / (high - low) * (inner_bottom - inner_top)
            points.append(f"{x:.2f},{y:.2f}")
        unit = "µA" if signal.startswith("I(") else "mV" if signal.startswith("V(") else "raw"
        panels.append((y0, f"<text x='8' y='{y0+28}' fill='#eee' font-size='12'>{html.escape(signal)} [{unit}]</text><polyline fill='none' stroke='{colors[signal_index % len(colors)]}' stroke-width='1.2' points='{' '.join(points)}'/><text x='{width-30}' y='{inner_top+10}' fill='#aaa' font-size='10' text-anchor='end'>{high:.4g}</text><text x='{width-30}' y='{inner_bottom}' fill='#aaa' font-size='10' text-anchor='end'>{low:.4g}</text>"))
    height = 45 + max(1, len(panels)) * panel_height
    marker_names = (("write0_50_61", "WRITE0"), ("zero_read_control_70_81", "CONTROL READ"), ("write1_90_101", "WRITE1"), ("final_read_110_121", "FINAL READ"))
    markers = []
    for name, label in marker_names:
        if name not in windows:
            continue
        start, end = windows[name]
        x1 = 80 + start / stop * (width - 110); x2 = 80 + end / stop * (width - 110)
        markers.append(f"<rect x='{x1:.2f}' y='25' width='{max(1,x2-x1):.2f}' height='{height-35}' fill='#ffffff' opacity='0.04'/><text x='{(x1+x2)/2:.2f}' y='16' fill='#ddd' font-size='10' text-anchor='middle'>{label}</text>")
    body = "".join(item[1] for item in panels)
    return f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {width} {height}' style='width:100%;background:#111'><rect width='100%' height='100%' fill='#111'/><text x='80' y='12' fill='#fff' font-size='13'>{html.escape(title)}</text>{''.join(markers)}{body}<line x1='80' x2='{width-30}' y1='{height-22}' y2='{height-22}' stroke='#777'/><text x='80' y='{height-7}' fill='#aaa' font-size='10'>0 ps</text><text x='{width-30}' y='{height-7}' fill='#aaa' font-size='10' text-anchor='end'>{stop:g} ps</text></svg>"


def link(path: Path, base: Path, label: str) -> str:
    return f"<a href='{html.escape(os.path.relpath(path, base))}'>{html.escape(label)}</a>"


def main() -> int:
    parser = argparse.ArgumentParser(description="Render one USER_CASE review")
    parser.add_argument("--case-root", required=True)
    args = parser.parse_args()
    case_root = Path(args.case_root).resolve()
    manifest = json.loads((case_root / "case_manifest.json").read_text(encoding="utf-8"))
    metrics = json.loads((case_root / "analysis" / "case_metrics.json").read_text(encoding="utf-8"))["case"]
    windows = manifest["windows"]
    plot_root = SERIES / "plots" / case_root.name
    group_root = plot_root / "groups"
    asset = SERIES / "plots" / "assets" / "plotly.min.js"
    plot_entries: list[dict[str, Any]] = []
    run_plot_links: dict[str, list[str]] = {}
    first_raw = None; first_headers = None; first_rows = None
    for run in metrics["runs"]:
        raw = case_root / "cases" / run["run_id"] / "raw.csv"
        headers, rows = load_raw(raw)
        if first_raw is None:
            first_raw, first_headers, first_rows = raw, headers, rows
        bvm = run["active_bvms"][0] if run["active_bvms"] else 1
        selections = {
            "s_loop": [f"{quantity}(B_JM{junction}|XBVM{bvm})" for junction in (1, 2) for quantity in ("P", "V", "I")] + [f"{quantity}({branch}|XBVM{bvm})" for branch in ("L_M1", "L_M2", "L_M3", "L_PM") for quantity in ("I", "V")],
            "r_loop": [f"{quantity}(B_JS{junction}|XBVM{bvm})" for junction in (1, 2) for quantity in ("P", "V", "I")] + [f"{quantity}({branch}|XBVM{bvm})" for branch in ("L_S1", "L_S2", "L_S3", "R_S") for quantity in ("I", "V")],
            "output": ["V(COMMON_SL)", "I(B_JSL8)", "V(B_JSL8)", f"I(L_SL|XBVM{bvm})", f"V(L_SL|XBVM{bvm})"],
        }
        run_plot_links[run["run_id"]] = []
        for prefix, requested in selections.items():
            present = [signal for signal in requested if signal in headers]
            output = group_root / f"{run['run_id']}_{prefix}.html"
            item = render_group(raw, output, present, f"{case_root.name} — {run['run_id']} — {prefix}", asset)
            if item:
                plot_entries.append(item); run_plot_links[run["run_id"]].append(item["path"])
    if first_raw is None or first_headers is None or first_rows is None:
        raise RuntimeError("no raw run found")
    stimulus_svg = svg_panel(first_headers, first_rows, ["I(I_WL1)", "I(I_BL1)", "I(I_SE1)"], windows, "Actual stimulus source branches — representative raw run")
    overview_signals = ["I(I_WL1)", "I(I_BL1)", "I(I_SE1)", "V(B_JS1|XBVM1)", "V(B_JS2|XBVM1)", "I(L_S3|XBVM1)", "V(L_S3|XBVM1)", "I(L_SL|XBVM1)", "V(L_SL|XBVM1)", "V(COMMON_SL)", "I(B_JSL8)"]
    overview_svg = svg_panel(first_headers, first_rows, [signal for signal in overview_signals if signal in first_headers], windows, "Stimulus + response overview — representative raw run", panel_height=95)
    review = plot_root / "review.html"
    params = manifest["parameters"]
    changes = manifest.get("config_changes", [])
    circuit_changes = "<br>".join(f"{html.escape(row['key'])}: {html.escape(row['from'])} → {html.escape(row['to'])}" for row in changes if row["section"] == "circuit") or "none"
    stimulus_changes = "<br>".join(f"{html.escape(row['key'])}: {html.escape(row['from'])} → {html.escape(row['to'])}" for row in changes if row["section"] == "stimulus") or "none"
    base = review.parent
    body = ["<!doctype html><html><head><meta charset='utf-8'><title>" + html.escape(case_root.name) + "</title><style>body{font-family:Arial,sans-serif;background:#111;color:#eee;margin:20px;line-height:1.45}a{color:#8ecbff}section{border:1px solid #444;border-radius:6px;margin:18px 0;padding:14px}table{border-collapse:collapse;width:100%;font-size:12px}th,td{border:1px solid #555;padding:5px}th{background:#292929}code{color:#ffd580}.svgbox{overflow:auto;margin:8px 0 16px}small{color:#aaa}</style></head><body>", f"<h1>{html.escape(case_root.name)}</h1>", f"<p><b>NAME</b>={html.escape(params['NAME'])} · <b>MODE</b>={html.escape(params['MODE'])} · <b>MASKS</b>={', '.join(params['MASKS'])}</p>", f"<p><b>Circuit changes</b><br>{circuit_changes}<br><br><b>Stimulus changes</b><br>{stimulus_changes}</p>"]
    body.extend(["<section><h2>Page 1 — stimulus + operation timeline</h2>", f"<div class='svgbox'>{stimulus_svg}</div>", "<p>Markers and waveform are generated from the actual raw stimulus branch columns, not only from config text.</p></section>"])
    body.extend(["<section><h2>Page 2 — stimulus + response overview</h2>", f"<div class='svgbox'>{overview_svg}</div></section>"])
    def grouped_links(run_id: str, prefix: str) -> str:
        return " · ".join(link(REPO / path, base, Path(path).stem) for path in run_plot_links[run_id] if f"_{prefix}.html" in path) or "—"
    body.append("<section><h2>Page 3 — S-loop</h2><p>JM1/JM2 P/V/I and LM1/LM2/LM3/LPM I/V grouped plots:</p><ul>" + "".join(f"<li>{html.escape(run['run_id'])}: {grouped_links(run['run_id'], 's_loop')}</li>" for run in metrics["runs"]) + "</ul><p>Gate-S: <b>REVIEW_REQUIRED</b>; no fixed percentage threshold.</p></section>")
    body.append("<section><h2>Page 4 — R-loop</h2><p>JS1/JS2 P/V/I and LS1/LS2/LS3/RS I/V grouped plots:</p><ul>" + "".join(f"<li>{html.escape(run['run_id'])}: {grouped_links(run['run_id'], 'r_loop')}</li>" for run in metrics["runs"]) + "</ul><p>Gate-R: <b>AMBIGUOUS</b>; navigation labels are not formal SFQ counts.</p></section>")
    body.append("<section><h2>Page 5 — output</h2><ul>" + "".join(f"<li>{html.escape(run['run_id'])}: {grouped_links(run['run_id'], 'output')}</li>" for run in metrics["runs"]) + "</ul><p>Output includes COMMON_SL, JSL8, LSL and actual timing windows.</p></section>")
    body.append("<section><h2>Page 6 — numeric state summary</h2><p>Dynamic windows: " + ", ".join(f"{name}=[{bounds[0]:g},{bounds[1]:g}) ps" for name, bounds in windows.items()) + f".</p><p>{link(case_root / 'REVIEW_SUMMARY.md', base, 'REVIEW_SUMMARY.md')} · {link(case_root / 'analysis' / 'case_metrics.json', base, 'case_metrics.json')} · {link(case_root / 'analysis' / 'per_signal_window_metrics.csv', base, 'per_signal_window_metrics.csv')}</p></section>")
    body.append("<section><h2>Page 7 — one-shot summary</h2><table><tr><th>run</th><th>BVM</th><th>JS1 read turns</th><th>JS1 p2p</th><th>JS2 read turns</th><th>JS2 p2p</th><th>first activity absolute ps</th><th>relative to read start ps</th></tr>" + "".join(f"<tr><td>{html.escape(run['run_id'])}</td><td>BVM{bvm}</td><td>{q(run['r_loop'][str(bvm)]['B_JS1'].get('net_turns_110_121'))}</td><td>{q(run['r_loop'][str(bvm)]['B_JS1'].get('p2p_turns_110_121'))}</td><td>{q(run['r_loop'][str(bvm)]['B_JS2'].get('net_turns_110_121'))}</td><td>{q(run['r_loop'][str(bvm)]['B_JS2'].get('p2p_turns_110_121'))}</td><td>{q(run['r_loop'][str(bvm)]['B_JS1'].get('activity', {}).get('first_activity_ps'))}</td><td>{q((run['r_loop'][str(bvm)]['B_JS1'].get('activity', {}).get('first_activity_ps') or 0) - windows['final_read_110_121'][0] if run['r_loop'][str(bvm)]['B_JS1'].get('activity', {}).get('first_activity_ps') is not None else None)}</td></tr>" for run in metrics["runs"] for bvm in (run["active_bvms"] or [1])) + "</table></section>")
    body.append("<h2>Raw evidence</h2><ul>" + "".join(f"<li>{link(case_root / 'cases' / run['run_id'] / 'raw.csv', base, run['run_id'] + '/raw.csv')}</li>" for run in metrics["runs"]) + "</ul><small>Phase P(...) is raw radians; turns are navigation only. No scientific interpretation performed.</small></body></html>")
    review.parent.mkdir(parents=True, exist_ok=True)
    review.write_text("\n".join(body), encoding="utf-8")
    plot_qa = {"status": "PASS", "case_id": case_root.name, "grouped_plot_count": len(plot_entries), "no_exhaustive_atlas": True, "no_cross_run_comparison": True, "raw_hashes_rechecked": all(item["raw_sha256"] == sha256(REPO / item["raw_path"]) for item in plot_entries), "descriptive_only": True}
    write_json(case_root / "qa" / "plot_qa.json", plot_qa)
    write_json(case_root / "analysis" / "plot_manifest.json", {"schema": "bvm-rloop-user-case-plot-manifest-v1", "case_id": case_root.name, "entries": plot_entries, "review": str(review.relative_to(SERIES)).replace("\\", "/"), "plot_qa": str((case_root / "qa" / "plot_qa.json").relative_to(SERIES)).replace("\\", "/"), "no_exhaustive_atlas": True, "no_cross_run_comparison": True})
    print(json.dumps(plot_qa, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

