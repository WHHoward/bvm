#!/usr/bin/env python3
"""Create standalone grouped pages and an exhaustive per-signal atlas.

Grouped pages are rendered with the repository's josim-plot2.py. The atlas
uses one shared local Plotly runtime and tiny deterministic per-signal pages so
that every raw column/window can be inspected without embedding the runtime
thousands of times. No cross-run comparison is produced.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import csv
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

SERIES = Path(__file__).resolve().parents[1]
REPO = next((path for path in (SERIES, *SERIES.parents) if (path / ".git").exists()), SERIES)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyze import load_case, phase_signal, signal_class, unwrap, write_json  # noqa: E402
from build_cases import CASE_ORDER, FAMILIES, MASKS  # noqa: E402

WINDOWS = (("whole_0_200", 0.0, 200.0), ("prehistory_50_110", 50.0, 110.0), ("zero_read_control_70_81", 70.0, 81.0), ("final_read_downstream_110_150", 110.0, 150.0))
GROUPS = ("stimulus_history", "BVM1", "BVM2", "BVM3", "BVM4", "COMMON_SL_JSL", "QB", "JTL_TERMINAL")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def repo_rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return value


def runtime_from_html(path: Path, asset: Path) -> None:
    html = path.read_text(encoding="utf-8")
    matches = list(re.finditer(r"<script(?P<attrs>[^>]*)>(?P<body>.*?)</script>", html, flags=re.DOTALL | re.IGNORECASE))
    runtime = next((match for match in matches if len(match.group("body")) > 1_000_000 and ("plotly.js v" in match.group("body") or "var Plotly=" in match.group("body"))), None)
    if runtime is None:
        raise RuntimeError(f"embedded Plotly runtime not found in {path}")
    body = runtime.group("body")
    asset.parent.mkdir(parents=True, exist_ok=True)
    if asset.exists() and asset.read_text(encoding="utf-8") != body:
        raise RuntimeError("josim-plot2 Plotly runtime changed within one series")
    if not asset.exists():
        asset.write_text(body, encoding="utf-8")


def externalize(path: Path, asset: Path) -> None:
    html = path.read_text(encoding="utf-8")
    matches = list(re.finditer(r"<script(?P<attrs>[^>]*)>(?P<body>.*?)</script>", html, flags=re.DOTALL | re.IGNORECASE))
    runtime = next((match for match in matches if len(match.group("body")) > 1_000_000 and ("plotly.js v" in match.group("body") or "var Plotly=" in match.group("body"))), None)
    if runtime is None:
        raise RuntimeError(f"embedded Plotly runtime not found in {path}")
    body = runtime.group("body")
    asset.parent.mkdir(parents=True, exist_ok=True)
    if asset.exists() and asset.read_text(encoding="utf-8") != body:
        raise RuntimeError("inconsistent Plotly runtime")
    if not asset.exists():
        asset.write_text(body, encoding="utf-8")
    reference = Path(os.path.relpath(asset, path.parent)).as_posix()
    compact = html[: runtime.start()] + f'<script src="{reference}"></script>' + html[runtime.end() :]
    if any(token in compact for token in ("plotly.js v", "var Plotly=", "cdn.plot.ly")):
        raise RuntimeError(f"Plotly runtime was not externalized: {path}")
    path.write_text(compact, encoding="utf-8")


def plotter_path() -> Path:
    path = REPO / "scripts" / "josim-plot2.py"
    if not path.is_file():
        raise RuntimeError(f"missing standard renderer: {path}")
    return path


def render_group(raw: Path, output: Path, signals: list[str], title: str, asset: Path) -> dict[str, Any]:
    if not signals:
        raise RuntimeError(f"empty grouped signal selection: {title}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(prefix="bvm_baseline_plot_", suffix=".html", delete=False, dir="/tmp") as handle:
        temporary = Path(handle.name)
    command = [sys.executable, str(plotter_path()), str(raw), "-x", str(temporary), "-t", "sep_comb", "-c", "dark", "-j", "2pi", "-w", title, "-s", *signals]
    try:
        completed = subprocess.run(command, cwd=REPO, capture_output=True, text=True, check=False)
        if completed.returncode != 0:
            raise RuntimeError(f"josim-plot2 failed for {title}: {completed.stderr[-1000:]}")
        output.write_text(temporary.read_text(encoding="utf-8"), encoding="utf-8")
        externalize(output, asset)
    finally:
        temporary.unlink(missing_ok=True)
    return {"output": repo_rel(output), "sha256": sha256(output), "raw_path": repo_rel(raw), "raw_sha256": sha256(raw), "signals": signals, "renderer": repo_rel(plotter_path()), "renderer_arguments": command, "time_unit": "ps", "phase_display": "-j 2pi navigation; raw P(...) remains radians", "descriptive_only": True}


def grouped_signals(headers: list[str], group: str) -> dict[str, list[str]]:
    if group == "stimulus_history":
        selected = [name for name in headers if name.startswith(("I(I_WL", "I(I_BL", "I(I_SE", "I(I_REPLAY"))]
    elif group.startswith("BVM"):
        instance = "XBVM" + group[-1]
        selected = [name for name in headers if f"|{instance})" in name]
    elif group == "COMMON_SL_JSL":
        selected = [name for name in headers if name == "V(COMMON_SL)" or "B_JSL" in name]
    elif group == "QB":
        selected = [name for name in headers if name in {"V(QBIN)", "V(QBOUT)"} or "|XBQ1)" in name]
    elif group == "JTL_TERMINAL":
        selected = [name for name in headers if "|XJTL1_" in name or name.startswith("V(JTL") or "R_TERM" in name]
    else:
        raise RuntimeError(f"unknown group: {group}")
    result = {"phase": [name for name in selected if name.startswith("P(")], "voltage": [name for name in selected if name.startswith("V(")], "current": [name for name in selected if name.startswith("I(")], "other": [name for name in selected if not name.startswith(("P(", "V(", "I("))]}
    return {kind: values for kind, values in result.items() if values}


def js_quote(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def atlas_data(case: dict[str, Any], run_id: str, output: Path) -> dict[str, Any]:
    signals: dict[str, list[float]] = {}
    phase_unwrapped: dict[str, list[float]] = {}
    for signal in case["headers"]:
        if signal == "time":
            continue
        values = [float(row[case["headers"].index(signal)]) for row in case["rows"]]
        signals[signal] = values
        if phase_signal(signal):
            phase_unwrapped[signal] = unwrap(values)
    data = {"run_id": run_id, "raw_path": repo_rel(case["path"]), "raw_sha256": case["raw_sha256"], "time_ps": case["times_ps"], "signals": signals, "phase_unwrapped": phase_unwrapped, "phase_semantics": "raw radians; unwrapped radians and rad/(2*pi) navigation only; not formal SFQ counts"}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("window.JOSIM_ATLAS_DATA = " + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";\n", encoding="utf-8")
    return {"path": repo_rel(output), "sha256": sha256(output), "bytes": output.stat().st_size, "run_id": run_id, "raw_path": repo_rel(case["path"]), "raw_sha256": case["raw_sha256"], "signal_count": len(signals), "phase_signal_count": len(phase_unwrapped), "raw_direct": True}


def atlas_page(run_id: str, case: dict[str, Any], signal: str, slug: str, window_name: str, start: float, end: float, data_file: Path, asset: Path, output: Path) -> dict[str, Any]:
    runtime = Path(os.path.relpath(asset, output.parent)).as_posix()
    data_ref = Path(os.path.relpath(data_file, output.parent)).as_posix()
    phase = phase_signal(signal)
    phase_js = """
const raw = data.signals[signal];
const unwrapped = data.phase_unwrapped[signal];
const turns = unwrapped.map(v => v / (2 * Math.PI));
const variants = [
  ["Raw phase [rad]", raw, "Phase [rad]"],
  ["Unwrapped phase [rad]", unwrapped, "Phase [rad]"],
  ["Unwrapped phase [turns]", turns, "Phase [turns]"],
];
for (const [title, values, ytitle] of variants) {
  const div = document.createElement("div");
  div.className = "plot";
  document.getElementById("plots").appendChild(div);
  const x = [], y = [];
  for (let i = 0; i < data.time_ps.length; i++) {
    if (data.time_ps[i] >= start && data.time_ps[i] < end) { x.push(data.time_ps[i]); y.push(values[i]); }
  }
  Plotly.newPlot(div, [{x, y, mode: "lines", name: signal}], {
    title: title + " — " + signal,
    paper_bgcolor: "#111111", plot_bgcolor: "#111111", font: {color: "#eeeeee"},
    xaxis: {title: "Time [ps]", gridcolor: "#444444"},
    yaxis: {title: ytitle, gridcolor: "#444444"},
    margin: {l: 80, r: 30, t: 70, b: 60}, showlegend: true,
  }, {responsive: true, displaylogo: false});
}
"""
    scalar_js = """
const values = data.signals[signal];
const x = [], y = [];
for (let i = 0; i < data.time_ps.length; i++) {
  if (data.time_ps[i] >= start && data.time_ps[i] < end) { x.push(data.time_ps[i]); y.push(values[i]); }
}
Plotly.newPlot("plots", [{x, y, mode: "lines", name: signal}], {
  title: signal + " — " + runId + " — " + windowName,
  paper_bgcolor: "#111111", plot_bgcolor: "#111111", font: {color: "#eeeeee"},
  xaxis: {title: "Time [ps]", gridcolor: "#444444"},
  yaxis: {title: unitLabel, gridcolor: "#444444"},
  margin: {l: 80, r: 30, t: 70, b: 60}, showlegend: true,
}, {responsive: true, displaylogo: false});
"""
    _, _, quantity, unit = signal_class(signal)
    body = phase_js if phase else scalar_js
    html = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>{run_id} — {signal} — {window_name}</title>
<style>body{{background:#111;color:#eee;font-family:Arial,sans-serif;margin:0;padding:16px}}.plot{{width:100%;height:360px;margin-bottom:18px}}</style></head>
<body><h1>{run_id}</h1><p>Exact signal: <code>{signal}</code><br>Window: [{start:g}, {end:g}) ps<br>Raw: {repo_rel(case['path'])}<br>Phase turns are navigation only; not formal SFQ counts.</p><div id="plots"></div>
<script src="{runtime}"></script><script src="{data_ref}"></script><script>
const data = window.JOSIM_ATLAS_DATA; const runId = {js_quote(run_id)}; const signal = {js_quote(signal)}; const windowName = {js_quote(window_name)}; const start = {start!r}; const end = {end!r}; const unitLabel = {js_quote(unit)};
{body}
</script></body></html>
"""
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding="utf-8")
    return {"kind": "atlas", "run_id": run_id, "signal": signal, "slug": slug, "window": window_name, "window_ps": [start, end], "path": repo_rel(output), "sha256": sha256(output), "raw_path": repo_rel(case["path"]), "raw_sha256": case["raw_sha256"], "phase_views": ["raw radians", "unwrapped radians", "rad/(2*pi) navigation turns"] if phase else [], "descriptive_only": True}


def write_atlas_index(run_id: str, entries: list[dict[str, Any]], output: Path) -> None:
    links = []
    for item in entries:
        target = SERIES / item["path"]
        relative = Path(os.path.relpath(target, output.parent)).as_posix()
        links.append(f"<li><code>{item['signal']}</code>: <a href=\"{relative}\">{item['window']}</a></li>")
    html = "<!doctype html><html><head><meta charset='utf-8'><title>" + run_id + " atlas</title></head><body><h1>" + run_id + " all-signal atlas</h1><p>Standalone raw-direct pages; phase turns are navigation only, not formal SFQ counts.</p><ul>" + "\n".join(links) + "</ul></body></html>\n"
    output.write_text(html, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Render standalone exhaustive baseline visualizations")
    parser.add_argument("--series-dir", default=str(SERIES))
    parser.add_argument("attempt")
    args = parser.parse_args()
    if Path(args.series_dir).resolve() != SERIES.resolve():
        raise RuntimeError("series-local plotter must run from its own series")
    attempt = SERIES / "runs" / args.attempt
    provenance = read_json(SERIES / "provenance.json")
    run_ids = list(provenance.get("run_order", []))
    if len(run_ids) != 15:
        raise RuntimeError(f"exhaustive baseline plot requires 15 completed runs, got {len(run_ids)}")
    visualization = SERIES / "visualization"
    asset = visualization / "assets" / "plotly.min.js"
    cases = {run_id: load_case(attempt / "cases" / run_id / "raw.csv") for run_id in run_ids}
    first_case = next(iter(cases.values()))
    first_signal = next(signal for signal in first_case["headers"] if signal != "time")
    with tempfile.NamedTemporaryFile(prefix="bvm_runtime_", suffix=".html", delete=False, dir="/tmp") as handle:
        runtime_temp = Path(handle.name)
    try:
        command = [sys.executable, str(plotter_path()), str(first_case["path"]), "-x", str(runtime_temp), "-t", "sep_comb", "-c", "dark", "-j", "2pi", "-w", "runtime extraction", "-s", first_signal]
        completed = subprocess.run(command, cwd=REPO, capture_output=True, text=True, check=False)
        if completed.returncode != 0:
            raise RuntimeError(f"renderer runtime extraction failed: {completed.stderr[-1000:]}")
        runtime_from_html(runtime_temp, asset)
    finally:
        runtime_temp.unlink(missing_ok=True)
    group_jobs: list[tuple[Path, Path, list[str], str]] = []
    grouped_entries: list[dict[str, Any]] = []
    for run_id, case in cases.items():
        groups_dir = visualization / run_id / "groups"
        for group in GROUPS:
            quantities = grouped_signals(case["headers"], group)
            for quantity, signals in quantities.items():
                output = groups_dir / f"{group}_{quantity}.html"
                group_jobs.append((case["path"], output, signals, f"{run_id} — {group} — {quantity}"))
    workers = min(8, max(1, os.cpu_count() or 1))
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(render_group, raw, output, signals, title, asset) for raw, output, signals, title in group_jobs]
        for future in futures:
            grouped_entries.append(future.result())
    atlas_entries: list[dict[str, Any]] = []
    data_entries: list[dict[str, Any]] = []
    for run_id, case in cases.items():
        data_file = visualization / "data" / f"{run_id}.data.js"
        data_entries.append(atlas_data(case, run_id, data_file))
        run_entries: list[dict[str, Any]] = []
        for signal in case["headers"]:
            if signal == "time":
                continue
            slug = hashlib.sha256(signal.encode("utf-8")).hexdigest()[:16]
            for window_name, start, end in WINDOWS:
                output = visualization / run_id / "atlas" / slug / f"{window_name}.html"
                run_entries.append(atlas_page(run_id, case, signal, slug, window_name, start, end, data_file, asset, output))
        atlas_entries.extend(run_entries)
        write_atlas_index(run_id, run_entries, visualization / run_id / "atlas" / "index.html")
    index_lines = ["# Exhaustive baseline visualization index", "", "Standalone only; no cross-run comparison plots are generated.", "", "- Plotter: `scripts/josim-plot2.py`; grouped pages use `sep_comb`, `dark`, `-j 2pi`.", "- Atlas pages are raw-direct with four actual-grid windows; phase pages show raw radians, unwrapped radians, and rad/(2*pi) navigation turns.", ""]
    for run_id in run_ids:
        run_group_entries = [item for item in grouped_entries if item["raw_path"].endswith(f"/{run_id}/raw.csv")]
        groups_index = visualization / run_id / "groups" / "index.html"
        groups_index.parent.mkdir(parents=True, exist_ok=True)
        group_links = []
        for item in run_group_entries:
            group_links.append(f"<li><a href=\"{Path(item['output']).name}\">{Path(item['output']).stem}</a></li>")
        groups_index.write_text("<!doctype html><html><head><meta charset='utf-8'><title>" + run_id + " grouped views</title></head><body><h1>" + run_id + " grouped views</h1><ul>" + "".join(group_links) + "</ul></body></html>\n", encoding="utf-8")
        index_lines.append(f"## {run_id}")
        index_lines.append("")
        index_lines.append(f"- [grouped views]({run_id}/groups/index.html)")
        index_lines.append(f"- [all-signal atlas]({run_id}/atlas/index.html)")
        index_lines.append("")
    (visualization / "index.md").parent.mkdir(parents=True, exist_ok=True)
    (visualization / "index.md").write_text("\n".join(index_lines), encoding="utf-8")
    html_paths = list(visualization.rglob("*.html"))
    invalid_runtime_pages = [repo_rel(path) for path in html_paths if any(token in path.read_text(encoding="utf-8", errors="replace") for token in ("plotly.js v", "var Plotly=", "cdn.plot.ly"))]
    plot_manifest = {"schema": "bvm-qb-current-baseline-exhaustive-visualization-manifest-v1", "experiment_id": SERIES.name, "attempt": args.attempt, "generated_at": __import__("datetime").datetime.now().astimezone().isoformat(timespec="seconds"), "renderer": repo_rel(plotter_path()), "renderer_defaults": {"layout": "sep_comb", "color": "dark", "phase_option": "2pi", "time_unit": "ps"}, "no_cross_run_comparison": True, "grouped_entries": grouped_entries, "data_entries": data_entries, "atlas_entries": atlas_entries, "standalone_count": len(grouped_entries) + len(atlas_entries), "atlas_signal_window_count": len(atlas_entries), "phase_semantics": "raw radians plus independent unwrap and rad/(2*pi) navigation only; not formal SFQ counts", "raw_hashes_rechecked": all(item["raw_sha256"] == sha256(cases[item["run_id"]]["path"]) for item in atlas_entries), "invalid_runtime_pages": invalid_runtime_pages, "descriptive_only": True}
    write_json(visualization / "plot_manifest.json", plot_manifest)
    write_json(visualization / "plot_qa.json", {"status": "PASS" if plot_manifest["raw_hashes_rechecked"] and plot_manifest["standalone_count"] > 0 and asset.is_file() and not invalid_runtime_pages else "FAIL", "no_cross_run_comparison": True, "standalone_count": plot_manifest["standalone_count"], "atlas_signal_window_count": plot_manifest["atlas_signal_window_count"], "plotly_runtime_sha256": sha256(asset) if asset.is_file() else None, "raw_hashes_rechecked": plot_manifest["raw_hashes_rechecked"], "invalid_embedded_runtime_pages": invalid_runtime_pages})
    provenance["visualization"] = {"status": "PASS", "manifest": repo_rel(visualization / "plot_manifest.json"), "plot_qa": repo_rel(visualization / "plot_qa.json"), "no_cross_run_comparison": True, "standalone_count": plot_manifest["standalone_count"]}
    write_json(SERIES / "provenance.json", provenance)
    result = read_json(SERIES / "result.json")
    result["visualization"] = provenance["visualization"]
    write_json(SERIES / "result.json", result)
    print(json.dumps({"status": "PASS", "attempt": args.attempt, "grouped_pages": len(grouped_entries), "atlas_pages": len(atlas_entries), "signals_per_run": {run_id: len([name for name in case["headers"] if name != "time"]) for run_id, case in cases.items()}}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
