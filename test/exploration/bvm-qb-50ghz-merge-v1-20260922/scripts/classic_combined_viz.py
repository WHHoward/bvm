#!/usr/bin/env python3
"""Render excitation and response together using classic josim-plot2 from each raw CSV."""

from __future__ import annotations

import csv
import hashlib
import html
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPO = next(path for path in (ROOT, *ROOT.parents) if (path / ".git").exists())
PLOTTER = REPO / "scripts" / "josim-plot2.py"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def headers(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8", newline="") as stream:
        return [item.strip().strip('"') for item in next(csv.reader(stream))]


def render(raw: Path, output: Path, title: str, signals: list[str], run_id: str, kind: str) -> dict[str, Any]:
    raw_header = headers(raw)
    missing = [signal for signal in signals if signal not in raw_header]
    if missing:
        raise RuntimeError(f"{run_id}/{kind}: missing raw columns: {missing}")
    if not 3 <= len(signals) <= 5:
        raise RuntimeError(f"{run_id}/{kind}: expected 3-5 selected traces, got {len(signals)}")
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [sys.executable, str(PLOTTER), str(raw), "-x", str(output), "-t", "sep_comb", "-c", "dark", "-j", "2pi", "-w", title, "-s", *signals]
    completed = subprocess.run(command, cwd=REPO, capture_output=True, text=True, check=False)
    if completed.returncode != 0 or not output.is_file() or output.stat().st_size == 0:
        raise RuntimeError(f"josim-plot2 failed for {run_id}/{kind}: {completed.stderr[-1200:]}")
    html_text = output.read_text(encoding="utf-8", errors="replace")
    if '"title":{"text":"Unknown"}' in html_text:
        raise RuntimeError(f"Unknown axis title in {output}")
    metadata = {
        "schema": "bvm-qb-50ghz-classic-combined-plot-v1",
        "run_id": run_id,
        "plot_kind": kind,
        "renderer": "scripts/josim-plot2.py",
        "layout": "sep_comb",
        "color": "dark",
        "phase_option": "2pi",
        "input_mode": "RAW_DIRECT",
        "input_raw_path": str(raw.relative_to(ROOT)),
        "input_raw_sha256": sha256(raw),
        "output_path": str(output.relative_to(ROOT)),
        "output_sha256": sha256(output),
        "selected_raw_columns": signals,
        "command": command,
        "scientific_interpretation_performed": False,
    }
    output.with_suffix(".metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return metadata


def plots_for_run(run_dir: Path, phase: str, run_id: str, raw_hash: str) -> list[dict[str, Any]]:
    raw = run_dir / "raw.csv"
    available = set(headers(raw))
    out_dir = run_dir / "plots" / "classic_combined"
    if phase == "phase_c_merge_collision":
        signals = ["V(SFQ_A)", "V(SFQ_B)", "V(SFQ_Q)", "V(SFQ_OUT)", "V(R_TERM)"]
        plot = render(raw, out_dir / "MERGE_inputs_and_output.html", f"{run_id} | MERGE inputs + JTL/terminal outputs | raw", signals, run_id, "MERGE_INPUTS_AND_OUTPUT")
        plots = [plot]
    else:
        config = load(run_dir / "config_snapshot.json")
        size = int(config["parameters"]["ARRAY_SIZE"])
        output_signals = ["V(QBOUT)", "V(R_TERM)"]
        plots = []
        for group in ("WL", "BL", "SE"):
            excitation = [f"I(I_{group}{index})" for index in range(1, size + 1)]
            excitation = [signal for signal in excitation if signal in available]
            signals = excitation + output_signals
            plots.append(render(raw, out_dir / f"{group}_excitation_with_output.html", f"{run_id} | {group} excitation + QBOUT/terminal | raw", signals, run_id, f"{group}_EXCITATION_WITH_OUTPUT"))
    if sha256(raw) != raw_hash:
        raise RuntimeError(f"raw changed while plotting: {raw}")
    return plots


def main() -> int:
    stimulus_qa = load(ROOT / "analysis" / "STIMULUS_VIZ_QA.json")
    runs: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    errors: list[str] = []
    for stimulus_run in stimulus_qa.get("runs", []):
        if not stimulus_run.get("entries"):
            continue
        first_input = stimulus_run["entries"][0]["input"]
        phase = first_input.split("/", 1)[0]
        run_id = stimulus_run["run_id"]
        run_dir = ROOT / phase / "runs" / run_id
        raw = run_dir / "raw.csv"
        result_path = run_dir / "result.json"
        if not raw.is_file() and not result_path.is_file():
            skipped.append({"phase": phase, "run_id": run_id, "reason": "preserved failed solver attempt; no output raw"})
            continue
        if not raw.is_file() or not result_path.is_file():
            errors.append(f"incomplete raw/result pair: {phase}/{run_id}")
            continue
        if load(result_path).get("artifact_status") != "VALID":
            skipped.append({"phase": phase, "run_id": run_id, "reason": "artifact status not VALID"})
            continue
        before = sha256(raw)
        try:
            plots = plots_for_run(run_dir, phase, run_id, before)
        except (RuntimeError, KeyError, ValueError) as exc:
            errors.append(str(exc))
            continue
        runs.append({"phase": phase, "run_id": run_id, "raw_path": str(raw.relative_to(ROOT)), "raw_sha256_before": before, "raw_sha256_after": sha256(raw), "raw_unchanged": before == sha256(raw), "plots": plots})

    index = ROOT / "plots" / "COMBINED_INDEX.html"
    rows = [
        "<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>",
        "<title>Classic combined josim-plot index</title><style>body{font:16px system-ui,sans-serif;margin:24px;background:#111827;color:#e5e7eb}table{border-collapse:collapse;width:100%}td,th{border:1px solid #475569;padding:8px;text-align:left}a{color:#93c5fd}code{white-space:nowrap}</style></head><body>",
        f"<h1>{html.escape(ROOT.name)} — classic excitation + output plots</h1>",
        "<p>Each link opens a single classic <code>josim-plot2.py -t sep_comb</code> plot generated directly from that run's raw.csv. Candidate runs have WL/BL/SE excitation plots, each including QBOUT and terminal voltage. MERGE runs have input-pin and downstream output voltages in one plot.</p>",
    ]
    for phase in sorted({item["phase"] for item in runs}):
        rows.append(f"<h2>{html.escape(phase)}</h2><table><tr><th>Run</th><th>Single-figure plots</th></tr>")
        for item in runs:
            if item["phase"] != phase:
                continue
            links = []
            for plot in item["plots"]:
                href = Path(os.path.relpath(ROOT / plot["output_path"], index.parent)).as_posix()
                links.append(f"<a href='{html.escape(href)}'>{html.escape(plot['plot_kind'])}</a>")
            rows.append(f"<tr><td><code>{html.escape(item['run_id'])}</code></td><td>{' · '.join(links)}</td></tr>")
        rows.append("</table>")
    if skipped:
        rows.append("<h2>Preserved attempts without output plots</h2><ul>" + "".join(f"<li>{html.escape(item['phase'])}/{html.escape(item['run_id'])}: {html.escape(item['reason'])}</li>" for item in skipped) + "</ul>")
    rows.append("</body></html>")
    index.write_text("\n".join(rows) + "\n", encoding="utf-8")
    qa = {"schema": "bvm-qb-50ghz-classic-combined-viz-qa-v1", "status": "PASS" if runs and not errors and all(item["raw_unchanged"] for item in runs) else "FAIL", "combined_run_count": len(runs), "classic_plot_count": sum(len(item["plots"]) for item in runs), "skipped_attempts": skipped, "index": str(index.relative_to(ROOT)), "index_sha256": sha256(index), "renderer": "scripts/josim-plot2.py", "layout": "sep_comb", "raw_hashes_unchanged": all(item["raw_unchanged"] for item in runs), "scientific_interpretation_performed": False, "errors": errors, "runs": runs}
    (ROOT / "analysis" / "CLASSIC_COMBINED_VIZ_QA.json").write_text(json.dumps(qa, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (ROOT / "analysis" / "CLASSIC_COMBINED_VIZ_MANIFEST.json").write_text(json.dumps({"schema": "bvm-qb-50ghz-classic-combined-viz-manifest-v1", "index": qa["index"], "index_sha256": qa["index_sha256"], "renderer": qa["renderer"], "layout": qa["layout"], "runs": runs}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": qa["status"], "combined_run_count": qa["combined_run_count"], "classic_plot_count": qa["classic_plot_count"], "errors": errors, "index": qa["index"]}, ensure_ascii=False, indent=2))
    return 0 if qa["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
