#!/usr/bin/env python3
"""Create classic josim-plot2 standalone views from immutable raw CSVs."""

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

from common import (PLOTTER, REPO, ROOT, cases, in_half_open_window,
                    raw_time_ps, read_json, run_dir, sha256, write_json)

PLOT_ROOT = ROOT / "plots"
ASSET = PLOT_ROOT / "assets" / "plotly.min.js"
WINDOWS = {"full": None, "final_read_110_121": (110.0, 121.0),
           "post_read_121_200": (121.0, 200.0),
           "read_response_110_200": (110.0, 200.0)}


def plot_sets(run_id: str) -> dict[str, list[str]]:
    return {
        "01_overview_whole_chain": [
            "I(I_WL1)", "I(I_SE1)", "V(BVM1_SL)", "V(QB1_OUT)", "V(CB1_OUT)",
            "V(ACC1_OUT)", "P(BJ1|XGAP1)", "I(I_WL2)", "I(I_SE2)",
            "V(BVM2_SL)", "V(QB2_OUT)", "V(CB2_OUT)", "I(L2|XACC2)",
            "V(GAP2_IN)", "P(BJ1|XGAP2)", "V(FINAL_OUT)", "V(R_TERM)"],
        "02_local_branch_1": [
            "I(I_WL1)", "I(I_SE1)", "P(B_JS1|XBVM1)", "P(BJ3|XBQ1)",
            "P(BJ2|XCB1)", "P(BJ1|XACC1)", "V(BVM1_SL)", "V(QB1_OUT)",
            "V(CB1_OUT)", "V(ACC1_OUT)"],
        "02_local_branch_2": [
            "I(I_WL2)", "I(I_SE2)",
            "P(B_JS1|XBVM2)", "P(BJ3|XBQ2)", "P(BJ2|XCB2)",
            "P(BJ1|XACC2)", "V(BVM2_SL)", "V(QB2_OUT)", "V(CB2_OUT)",
            "I(L2|XACC2)"],
        "03_gap2_merge_debug": [
            "P(BJ1|XACC2)", "P(BJ1|XGAP1)", "I(L2|XACC2)",
            "I(L2|XGAP1)", "V(GAP2_IN)", "P(BJ1|XGAP2)", "V(FINAL_OUT)"],
        "04_bvm_state": [
            "P(B_JM1|XBVM1)", "P(B_JM2|XBVM1)", "P(B_JS1|XBVM1)",
            "P(B_JS2|XBVM1)", "I(L_M1|XBVM1)", "I(L_M2|XBVM1)",
            "I(L_M3|XBVM1)", "I(L_PM|XBVM1)", "P(B_JM1|XBVM2)",
            "P(B_JM2|XBVM2)", "P(B_JS1|XBVM2)", "P(B_JS2|XBVM2)",
            "I(L_M1|XBVM2)", "I(L_M2|XBVM2)", "I(L_M3|XBVM2)",
            "I(L_PM|XBVM2)"],
    }


def headers_and_rows(raw: Path, signals: list[str], bounds: tuple[float, float] | None):
    with raw.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        fields = reader.fieldnames or []
        if len(fields) != len(set(fields)):
            raise ValueError(f"duplicate headers in {raw}")
        missing = sorted(set(signals) - set(fields))
        if missing:
            raise ValueError(f"required plot signals missing from {raw}: {missing}")
        selected = ["time", *signals]
        rows = []
        times_ps = []
        time_tokens = []
        for row in reader:
            token = row["time"]
            time_ps = raw_time_ps(token)
            if bounds is not None and not in_half_open_window(token, bounds):
                continue
            rows.append({key: row[key] for key in selected})
            times_ps.append(float(time_ps))
            time_tokens.append(token)
    if len(rows) < 2:
        raise ValueError(f"plot selection has fewer than two stored samples: {raw} {bounds}")
    return selected, rows, times_ps, time_tokens


def externalize(html_path: Path) -> None:
    source = html_path.read_text(encoding="utf-8")
    matches = list(re.finditer(r"<script(?P<attrs>[^>]*)>(?P<body>.*?)</script>", source,
                               flags=re.DOTALL | re.IGNORECASE))
    runtime = next((match for match in matches
                    if len(match.group("body")) > 1_000_000 and
                    ("plotly.js v" in match.group("body") or "var Plotly=" in match.group("body"))), None)
    if runtime is None:
        raise RuntimeError(f"embedded Plotly runtime not found in {html_path}")
    body = runtime.group("body")
    ASSET.parent.mkdir(parents=True, exist_ok=True)
    if ASSET.exists() and ASSET.read_text(encoding="utf-8") != body:
        raise RuntimeError("Plotly runtime changed during one experiment")
    if not ASSET.exists():
        ASSET.write_text(body, encoding="utf-8")
    ref = Path(os.path.relpath(ASSET, html_path.parent)).as_posix()
    compact = source[:runtime.start()] + f'<script src="{ref}"></script>' + source[runtime.end():]
    if any(token in compact for token in ("plotly.js v", "var Plotly=", "cdn.plot.ly")):
        raise RuntimeError(f"Plotly runtime was not externalized: {html_path}")
    html_path.write_text(compact, encoding="utf-8")


def render_one(run_id: str, raw: Path, raw_hash: str, category: str,
               signals: list[str], window: str, bounds: tuple[float, float] | None) -> dict[str, Any]:
    fields, rows, times_ps, time_tokens = headers_and_rows(raw, signals, bounds)
    run_plot_dir = PLOT_ROOT / run_id
    run_plot_dir.mkdir(parents=True, exist_ok=True)
    output = run_plot_dir / f"{category}__{window}.html"
    with tempfile.TemporaryDirectory(prefix=f"{run_id}_plot_") as temp:
        temp_dir = Path(temp)
        projected = temp_dir / "selected_stored_samples.csv"
        with projected.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        temporary_html = temp_dir / "josim_plot.html"
        command = [sys.executable, str(PLOTTER), str(projected), "-x", str(temporary_html),
                   "-t", "sep_comb", "-c", "dark", "-j", "2pi", "-w",
                   f"{run_id} — raw — {category} — {window} — stored time axis", "-s", *signals]
        completed = subprocess.run(command, cwd=REPO, capture_output=True, text=True, check=False)
        if completed.returncode != 0 or not temporary_html.is_file():
            raise RuntimeError(f"josim-plot2 failed ({category}/{window}): {completed.stderr[-1200:]}")
        output.write_text(temporary_html.read_text(encoding="utf-8"), encoding="utf-8")
    externalize(output)
    return {"path": output.relative_to(ROOT).as_posix(), "sha256": sha256(output),
            "run_id": run_id, "raw_path": raw.relative_to(ROOT).as_posix(),
            "raw_sha256": raw_hash, "signals": signals, "category": category,
            "window": window, "window_ps": list(bounds) if bounds else [0, 200],
            "window_semantics": "[start,end), selected existing raw timestamps only",
            "actual_first_sample_ps": times_ps[0], "actual_last_sample_ps": times_ps[-1],
            "actual_first_sample_s_token": time_tokens[0], "actual_last_sample_s_token": time_tokens[-1],
            "sample_count": len(rows), "interpolation": False, "resampling": False,
            "renderer": "scripts/josim-plot2.py", "renderer_arguments": command[1:],
            "plot_type": "sep_comb", "theme": "dark", "phase_display": "raw P radians; -j 2pi navigation only",
        "excitation_and_outputs_same_classic_plot": category.startswith("01_overview") or category.startswith("02_local"),
            "descriptive_only": True}


def review_page(run_id: str, plots: list[dict[str, Any]], metadata: dict[str, Any], output: Path) -> None:
    rows = []
    for plot in plots:
        rel = Path(plot["path"]).name
        rows.append(f"<li><a href='{html.escape(rel)}'>{html.escape(plot['category'])} / {html.escape(plot['window'])}</a> — {plot['sample_count']} stored samples</li>")
    raw_rel = os.path.relpath(run_dir(run_id) / "raw.csv", output.parent)
    text = """<!doctype html><html><head><meta charset='utf-8'><title>""" + html.escape(run_id) + """ review</title>
<style>body{font:16px Arial,sans-serif;background:#111;color:#eee;margin:28px;line-height:1.55}a{color:#8ecbff}code{color:#ffd580}</style></head><body>
<h1>""" + html.escape(run_id) + """ — descriptive raw review</h1>
<p>Interpretation: NOT PERFORMED. Each linked figure is rendered by the classic <code>josim-plot2.py</code> with <code>sep_comb / dark / -j 2pi</code>. Raw P is radians; turns are navigation only.</p>
<p>Mask <code>""" + html.escape(metadata["parameters"]["MASK"]) + """</code>; active BVMs <code>""" + html.escape(str(metadata["parameters"]["active_bvms"])) + """</code>; DT <code>0.01p</code>; STOP <code>200p</code>.</p>
<p><a href='""" + html.escape(raw_rel) + """'>immutable raw.csv</a> · <a href='stimulus.html'>stimulus + output navigation</a></p>
<h2>Classic grouped plots</h2><ul>""" + "\n".join(rows) + """</ul>
<p>Overview and local-branch figures place the registered excitation-current traces and circuit outputs in the same classic plot. Window views preserve only actual stored samples and do not interpolate or resample.</p>
</body></html>"""
    output.write_text(text, encoding="utf-8")


def stimulus_page(run_id: str, plots: list[dict[str, Any]], output: Path) -> None:
    links = [item for item in plots if item["category"].startswith("01_overview")]
    items = "\n".join(f"<li><a href='{html.escape(Path(x['path']).name)}'>{html.escape(x['window'])} — excitation + whole-chain outputs</a></li>" for x in links)
    output.write_text("<!doctype html><html><head><meta charset='utf-8'><title>" + html.escape(run_id) +
                      " stimulus and outputs</title><style>body{font:16px Arial;background:#111;color:#eee;margin:28px}a{color:#8ecbff}</style></head><body><h1>" +
                      html.escape(run_id) + " — excitation and outputs</h1><p>These are the classic josim-plot2 overview figures: source currents and chain outputs are in the same plot, not separate cards.</p><ul>" + items +
                      "</ul><p><a href='review.html'>Back to run review</a></p></body></html>", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Render per-run classic JoSIM visualization")
    parser.add_argument("--run", action="append", dest="run_ids")
    args = parser.parse_args()
    all_entries: list[dict[str, Any]] = []
    qa_cases = []
    selected = set(args.run_ids or [item["run_id"] for item in cases()])
    for item in cases():
        run_id = item["run_id"]
        if run_id not in selected:
            continue
        directory = run_dir(run_id)
        raw = directory / "raw.csv"
        raw_before = sha256(raw)
        metadata = read_json(directory / "metadata.json")
        if metadata.get("raw", {}).get("sha256") != raw_before:
            raise RuntimeError(f"raw SHA differs from metadata for {run_id}")
        entries = []
        for category, signals in plot_sets(run_id).items():
            for window, bounds in WINDOWS.items():
                entries.append(render_one(run_id, raw, raw_before, category, signals, window, bounds))
        if sha256(raw) != raw_before:
            raise RuntimeError(f"raw changed while plotting {run_id}")
        plot_dir = PLOT_ROOT / run_id
        review = plot_dir / "review.html"
        review_page(run_id, entries, metadata, review)
        stimulus_page(run_id, entries, plot_dir / "stimulus.html")
        all_entries.extend(entries)
        qa_cases.append({"run_id": run_id, "status": "PASS", "raw_sha256_before_after": raw_before,
                         "classic_plot_count": len(entries), "review_page": review.relative_to(ROOT).as_posix(),
                         "stimulus_page": (plot_dir / "stimulus.html").relative_to(ROOT).as_posix()})
    invalid = []
    for entry in all_entries:
        path = ROOT / entry["path"]
        content = path.read_text(encoding="utf-8", errors="replace")
        if any(token in content for token in ("plotly.js v", "var Plotly=", "cdn.plot.ly")):
            invalid.append(entry["path"])
        if "unknown" in content.lower():
            invalid.append(entry["path"] + ":unknown-axis-or-label")
        if entry["raw_sha256"] != sha256(ROOT / entry["raw_path"]):
            invalid.append(entry["path"] + ":raw-hash-mismatch")
    qa = {"schema": "bvm-bq-cb-gap-plot-qa-v1", "status": "PASS" if len(qa_cases) == len(selected) and not invalid else "FAIL",
          "cases": qa_cases, "plot_count": len(all_entries), "invalid_pages": invalid,
          "renderer": "scripts/josim-plot2.py", "style": "sep_comb/dark/-j 2pi",
          "excitation_and_output_combined": True, "windowed_views_use_actual_samples": True,
          "raw_unchanged": True, "scientific_interpretation_performed": False}
    write_json(ROOT / "analysis" / "plot_manifest.json", {"schema": "bvm-bq-cb-gap-plot-manifest-v1",
                "entries": all_entries, "plot_qa_path": "qa/plot_qa.json",
                "classic_review_pages": [record["review_page"] for record in qa_cases]})
    write_json(ROOT / "qa" / "plot_qa.json", qa)
    print(json.dumps(qa, ensure_ascii=False, indent=2))
    return 0 if qa["status"] == "PASS" else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
