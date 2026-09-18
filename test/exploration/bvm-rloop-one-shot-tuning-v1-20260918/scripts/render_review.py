#!/usr/bin/env python3
"""Render compact per-candidate review pages and a small set of grouped plots."""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

SERIES = Path(__file__).resolve().parents[1]
REPO = next(path for path in (SERIES, *SERIES.parents) if (path / ".git").exists())
PLOTTER = REPO / "scripts" / "josim-plot2.py"


def sha256(path: Path) -> str:
    import hashlib
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


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def externalize(path: Path, asset: Path) -> None:
    source = path.read_text(encoding="utf-8")
    matches = list(re.finditer(r"<script(?P<attrs>[^>]*)>(?P<body>.*?)</script>", source, flags=re.DOTALL | re.IGNORECASE))
    runtime = next((match for match in matches if len(match.group("body")) > 1_000_000 and ("plotly.js v" in match.group("body") or "var Plotly=" in match.group("body"))), None)
    if runtime is None:
        raise RuntimeError(f"embedded Plotly runtime not found in {path}")
    body = runtime.group("body")
    asset.parent.mkdir(parents=True, exist_ok=True)
    if asset.exists() and asset.read_text(encoding="utf-8") != body:
        raise RuntimeError("Plotly runtime changed within this experiment")
    if not asset.exists():
        asset.write_text(body, encoding="utf-8")
    reference = Path(os.path.relpath(asset, path.parent)).as_posix()
    compact = source[:runtime.start()] + f'<script src="{reference}"></script>' + source[runtime.end():]
    if any(token in compact for token in ("plotly.js v", "var Plotly=", "cdn.plot.ly")):
        raise RuntimeError(f"Plotly runtime was not externalized: {path}")
    path.write_text(compact, encoding="utf-8")


def render_group(raw: Path, output: Path, signals: list[str], title: str, asset: Path) -> dict[str, Any] | None:
    signals = [signal for signal in signals if signal]
    if not signals:
        return None
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(prefix="bvm_one_shot_plot_", suffix=".html", delete=False, dir="/tmp") as handle:
        temporary = Path(handle.name)
    command = [sys.executable, str(PLOTTER), str(raw), "-x", str(temporary), "-t", "sep_comb", "-c", "dark", "-j", "2pi", "-w", title, "-s", *signals]
    try:
        completed = subprocess.run(command, cwd=REPO, capture_output=True, text=True, check=False)
        if completed.returncode != 0:
            raise RuntimeError(f"josim-plot2 failed for {title}: {completed.stderr[-1000:]}")
        output.write_text(temporary.read_text(encoding="utf-8"), encoding="utf-8")
        externalize(output, asset)
    finally:
        temporary.unlink(missing_ok=True)
    return {"path": repo_rel(output), "sha256": sha256(output), "raw_path": repo_rel(raw), "raw_sha256": sha256(raw), "signals": signals, "renderer": repo_rel(PLOTTER), "renderer_arguments": command, "phase_display": "raw P(...) radians; -j 2pi is navigation only", "descriptive_only": True}


def raw_headers(path: Path) -> list[str]:
    import csv
    with path.open("r", encoding="utf-8", newline="") as stream:
        return next(csv.reader(stream))


def q(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.6g}"
    return html.escape(str(value))


def review_page(case_result: dict[str, Any], plots: list[dict[str, Any]], output: Path) -> None:
    params = case_result["parameters"]
    plot_by_title = {Path(item["path"]).stem: item for item in plots}
    run_rows = []
    for run in case_result["runs"]:
        active = run["active_bvms"]
        links = [f'<a href="{html.escape(Path(item["path"]).name)}">{html.escape(Path(item["path"]).stem)}</a>' for item in plots if f"/{run['run_id']}_" in item["path"]]
        run_rows.append((run, active, links))
    def plot_links(run_id: str, prefix: str) -> str:
        links = [f'<a href="{html.escape(os.path.relpath(REPO / item["path"], output.parent))}">{html.escape(Path(item["path"]).stem)}</a>' for item in plots if f"/{run_id}_{prefix}" in item["path"]]
        return " · ".join(links) if links else "—"
    body: list[str] = ["<!doctype html><html><head><meta charset='utf-8'><title>" + html.escape(case_result["case_id"]) + " review</title><style>body{font-family:Arial,sans-serif;background:#111;color:#eee;margin:24px;line-height:1.45}a{color:#8ecbff}table{border-collapse:collapse;width:100%;margin:12px 0 28px}th,td{border:1px solid #555;padding:6px 8px;text-align:left;font-size:13px}th{background:#262626}code{color:#ffd580}section{margin:28px 0;padding:14px;border:1px solid #444;border-radius:6px}small{color:#aaa}</style></head><body>", f"<h1>{html.escape(case_result['case_id'])}</h1>", "<p>Compact descriptive review page. Scientific interpretation is not performed; phase turns are navigation only, not formal SFQ counts.</p>", "<h2>Case</h2>", "<ul>", f"<li>Mode: <code>{html.escape(params['MODE'])}</code></li>", f"<li>JS1/JS2 area: <code>{html.escape(params['JS1_AREA'])}</code> / <code>{html.escape(params['JS2_AREA'])}</code></li>", f"<li>JS1/JS2 shunt: <code>{html.escape(params['RSH_JS1'])}</code> / <code>{html.escape(params['RSH_JS2'])}</code> ohm</li>", f"<li>LS1/LS2/LS3: <code>{html.escape(params['LS1'])}</code> / <code>{html.escape(params['LS2'])}</code> / <code>{html.escape(params['LS3'])}</code></li>", "</ul>"]
    body.extend(["<section><h2>Page 1 — stimulus + S-loop</h2><p>Windowed JM1/JM2 and LM1/LM2/LM3/LPM metrics are in <code>analysis/per_signal_window_metrics.csv</code>.</p>", "<table><tr><th>mask</th><th>representative active BVM</th><th>JM1 WRITE0 turns</th><th>JM1 control turns</th><th>JM1 WRITE1 turns</th><th>JM1 pre-read turns</th><th>grouped plots</th></tr>"])
    for run, active, _links in run_rows:
        bvm = active[0] if active else 1
        state = run["state"][str(bvm)]["B_JM1"]
        body.append(f"<tr><td>{html.escape(run['mask'])}</td><td>{'BVM' + str(bvm) if active else 'none (BVM1 diagnostic)'}</td><td>{q(state['write0_50_61'].get('phase_delta_turns'))}</td><td>{q(state['zero_read_control_70_81'].get('phase_delta_turns'))}</td><td>{q(state['write1_90_101'].get('phase_delta_turns'))}</td><td>{q(state['settle_101_110'].get('phase_delta_turns'))}</td><td>{plot_links(run['run_id'], 's_loop')}</td></tr>")
    body.extend(["</table><p>Gate-S: <b>REVIEW_REQUIRED</b>. No fixed percentage threshold or automatic functional-family decision is applied.</p></section>"])
    body.extend(["<section><h2>Page 2 — R-loop</h2><table><tr><th>mask</th><th>BVM</th><th>JS1 110→121 turns</th><th>JS1 p2p turns</th><th>JS2 110→121 turns</th><th>JS2 p2p turns</th><th>label</th><th>grouped plots</th></tr>"])
    for run, active, _links in run_rows:
        for bvm in active:
            js1 = run["r_loop"][str(bvm)]["B_JS1"]
            js2 = run["r_loop"][str(bvm)]["B_JS2"]
            body.append(f"<tr><td>{html.escape(run['mask'])}</td><td>BVM{bvm}</td><td>{q(js1.get('net_turns_110_121'))}</td><td>{q(js1.get('p2p_turns_110_121'))}</td><td>{q(js2.get('net_turns_110_121'))}</td><td>{q(js2.get('p2p_turns_110_121'))}</td><td>AMBIGUOUS</td><td>{plot_links(run['run_id'], 'r_loop')}</td></tr>")
    body.extend(["</table><p>Gate-R: <b>AMBIGUOUS</b>. Activity clusters and crossings are descriptive navigation metrics, not a formal classifier.</p></section>"])
    body.extend(["<section><h2>Page 3 — output</h2><table><tr><th>mask</th><th>peak positive I(B_JSL8) [A]</th><th>peak negative [A]</th><th>signed area [Phi0]</th><th>absolute area [Phi0]</th><th>zero crossings</th><th>grouped plots</th></tr>"])
    for run, _active, _links in run_rows:
        population = run["population"]
        body.append(f"<tr><td>{html.escape(run['mask'])}</td><td>{q(population.get('peak_positive_a'))}</td><td>{q(population.get('peak_negative_a'))}</td><td>{q(population.get('signed_area_phi0'))}</td><td>{q(population.get('absolute_area_phi0'))}</td><td>{q(population.get('zero_crossings'))}</td><td>{plot_links(run['run_id'], 'output')}</td></tr>")
    body.extend(["</table><p>Population monotonicity is reported numerically only; no strict 1:2:3:4 condition is imposed.</p></section>"])
    metrics_link = html.escape(os.path.relpath(SERIES / "analysis" / "case_metrics.json", output.parent))
    gate_link = html.escape(os.path.relpath(SERIES / "analysis" / "gate_s_comparison.json", output.parent))
    window_link = html.escape(os.path.relpath(SERIES / "analysis" / "per_signal_window_metrics.csv", output.parent))
    summary_link = html.escape(os.path.relpath(SERIES / "runs" / case_result["case_id"] / "REVIEW_SUMMARY.md", output.parent))
    body.extend([f"<section><h2>Page 4 — state summary</h2><p>Registered windows: WRITE0, zero-state control read, WRITE1, pre-final-read, recovery, and 150–200 ps tail. See the case summary and machine-readable metrics for JM2 and LM branch values.</p><p><a href='{metrics_link}'>case_metrics.json</a> · <a href='{gate_link}'>gate_s_comparison.json</a> · <a href='{window_link}'>per_signal_window_metrics.csv</a> · <a href='{summary_link}'>REVIEW_SUMMARY.md</a></p></section>"])
    body.extend(["<section><h2>Page 5 — one-shot summary</h2><p>JS1/JS2 first activity, possible subsequent activity, LS3 recovery, settling estimator, crossings, and same-JJ voltage-area cross-checks are retained in <code>case_metrics.json</code>. No event count or one-shot verdict is assigned.</p></section>", "<h2>Raw evidence</h2><ul>"])
    for run, _active, _links in run_rows:
        raw_path = SERIES / "runs" / case_result["case_id"] / "cases" / run["run_id"] / "raw.csv"
        body.append(f"<li><a href='{html.escape(os.path.relpath(raw_path, output.parent))}'>{html.escape(run['run_id'])}/raw.csv</a></li>")
    body.extend(["</ul><small>Renderer: scripts/josim-plot2.py, sep_comb/dark/-j 2pi. Raw P(...) is radians.</small></body></html>"])
    output.write_text("\n".join(body), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Render compact review pages")
    parser.add_argument("--case", action="append", dest="case_ids")
    args = parser.parse_args()
    metrics = read_json(SERIES / "analysis" / "case_metrics.json")
    selected = set(args.case_ids or [item["case_id"] for item in metrics["cases"]])
    previous_entries: dict[str, dict[str, Any]] = {}
    previous_manifest = SERIES / "analysis" / "plot_manifest.json"
    if previous_manifest.is_file():
        try:
            previous_entries = {item["path"]: item for item in read_json(previous_manifest).get("entries", [])}
        except (KeyError, TypeError, json.JSONDecodeError):
            previous_entries = {}
    all_entries: list[dict[str, Any]] = []
    for case_result in metrics["cases"]:
        case_id = case_result["case_id"]
        if case_id not in selected:
            continue
        case_plot_dir = SERIES / "plots" / case_id
        asset = SERIES / "plots" / "assets" / "plotly.min.js"
        case_plot_dir.mkdir(parents=True, exist_ok=True)
        entries: list[dict[str, Any]] = []
        for run in case_result["runs"]:
            raw = SERIES / "runs" / case_id / "cases" / run["run_id"] / "raw.csv"
            headers = raw_headers(raw)
            active = run["active_bvms"] or [1]
            bvm = active[0]
            selections = {
                "s_loop_junctions": [f"{quantity}(B_JM{junction}|XBVM{bvm})" for junction in (1, 2) for quantity in ("P", "V", "I")],
                "s_loop_branches": [f"{quantity}({branch}|XBVM{bvm})" for branch in ("L_M1", "L_M2", "L_M3", "L_PM") for quantity in ("I", "V")],
                "r_loop_junctions": [f"{quantity}(B_JS{junction}|XBVM{bvm})" for junction in (1, 2) for quantity in ("P", "V", "I")],
                "r_loop_branches": [f"{quantity}({branch}|XBVM{bvm})" for branch in ("L_S1", "L_S2", "L_S3", "R_S") for quantity in ("I", "V")],
                "output": ["V(COMMON_SL)", "P(B_JSL8)", "V(B_JSL8)", "I(B_JSL8)"],
            }
            for prefix, signals in selections.items():
                present = [signal for signal in signals if signal in headers]
                output = case_plot_dir / "groups" / f"{run['run_id']}_{prefix}.html"
                output_key = repo_rel(output)
                cached = previous_entries.get(output_key)
                item = cached if cached and output.is_file() and cached.get("raw_sha256") == sha256(raw) else render_group(raw, output, present, f"{case_id} — {run['run_id']} — {prefix}", asset)
                if item:
                    entries.append(item)
        review = case_plot_dir / "review.html"
        review_page(case_result, entries, review)
        all_entries.extend(entries)
    index = SERIES / "plots" / "index.md"
    lines = ["# BVM R-loop one-shot tuning review", "", "Compact review pages only; no exhaustive atlas is generated.", "", "Phase plots show raw radians and `rad/(2*pi)` navigation only; they are not formal SFQ counts.", ""]
    for case_result in metrics["cases"]:
        if case_result["case_id"] in selected:
            lines.extend([f"## {case_result['case_id']}", "", f"- [review.html]({case_result['case_id']}/review.html)", f"- [REVIEW_SUMMARY.md](../runs/{case_result['case_id']}/REVIEW_SUMMARY.md)", ""])
    index.write_text("\n".join(lines), encoding="utf-8")
    invalid = []
    for entry in all_entries:
        path = REPO / entry["path"]
        text = path.read_text(encoding="utf-8", errors="replace")
        if any(token in text for token in ("plotly.js v", "var Plotly=", "cdn.plot.ly")):
            invalid.append(entry["path"])
    plot_qa = {"status": "PASS" if all_entries and not invalid else "FAIL", "case_count": len(selected), "grouped_plot_count": len(all_entries), "no_exhaustive_atlas": True, "no_cross_run_comparison": True, "invalid_embedded_runtime_pages": invalid, "raw_hashes_rechecked": all(entry["raw_sha256"] == sha256(REPO / entry["raw_path"]) for entry in all_entries), "descriptive_only": True}
    write_json(SERIES / "qa" / "plot_qa.json", plot_qa)
    write_json(SERIES / "analysis" / "plot_manifest.json", {"schema": "bvm-rloop-one-shot-plot-manifest-v1", "entries": all_entries, "review_index": repo_rel(index), "plot_qa": repo_rel(SERIES / "qa" / "plot_qa.json"), "no_exhaustive_atlas": True, "no_cross_run_comparison": True})
    result_path = SERIES / "result.json"
    result = read_json(result_path) if result_path.is_file() else {}
    result.update({"visualization": {"status": plot_qa["status"], "manifest": repo_rel(SERIES / "analysis" / "plot_manifest.json"), "plot_qa": repo_rel(SERIES / "qa" / "plot_qa.json"), "no_exhaustive_atlas": True}, "scientific_interpretation_performed": False, "automatic_follow_up": False})
    write_json(result_path, result)
    print(json.dumps(plot_qa, ensure_ascii=False, indent=2))
    return 0 if plot_qa["status"] == "PASS" else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
