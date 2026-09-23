#!/usr/bin/env python3
"""Create per-run pages that show registered excitation beside measured output plots."""

from __future__ import annotations

import hashlib
import html
import json
import os
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def href_from(page_dir: Path, target: Path) -> str:
    return Path(os.path.relpath(target, page_dir)).as_posix()


def combined_html(phase: str, run_id: str, output_path: Path, stimulus: list[dict[str, Any]]) -> str:
    cards = []
    for entry in stimulus:
        target = ROOT / entry["output"]
        label = entry.get("label", entry.get("origin", "registered stimulus"))
        signals = ", ".join(entry.get("signals", []))
        cards.append(
            "<section class='card stimulus-card'>"
            f"<header><h2>{html.escape(label)}</h2><p>{html.escape(signals)}</p></header>"
            f"<iframe loading='eager' title='{html.escape(label)} {html.escape(run_id)}' src='{html.escape(href_from(output_path.parent, target))}'></iframe>"
            f"<p class='open'><a target='_blank' rel='noopener' href='{html.escape(href_from(output_path.parent, target))}'>Open stimulus plot</a></p>"
            "</section>"
        )
    result_link = href_from(output_path.parent, output_path.parent / "review.html")
    result_card = (
        "<section class='card result-card'>"
        "<header><h2>Experiment output</h2><p>Direct run visualization from raw.csv</p></header>"
        f"<iframe loading='eager' title='Experiment output {html.escape(run_id)}' src='{html.escape(result_link)}'></iframe>"
        f"<p class='open'><a target='_blank' rel='noopener' href='{html.escape(result_link)}'>Open output plot</a></p>"
        "</section>"
    )
    return """<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Combined stimulus and output</title>
<style>
:root{color-scheme:dark;font-family:system-ui,sans-serif;background:#111827;color:#e5e7eb}
body{margin:0;padding:18px}h1{margin:.15em 0}.sub{color:#bac6d7;margin:.2em 0 1em}
.layout{display:grid;grid-template-columns:minmax(0,1.35fr) minmax(360px,1fr);gap:14px;align-items:stretch}
.result-card{grid-row:1 / span 3}.card{background:#1f2937;border:1px solid #374151;border-radius:10px;padding:10px;min-width:0}
header h2{font-size:1rem;margin:.15em 0}.card p{font-size:.83rem;color:#cbd5e1;margin:.15em 0 .5em}
iframe{display:block;width:100%;height:290px;border:0;background:#fff;border-radius:6px}.result-card iframe{height:calc(100% - 54px);min-height:890px}
.open{margin:.35em 0 0!important}.open a{color:#93c5fd}.note{color:#cbd5e1;font-size:.9rem;margin:12px 0}
@media(max-width:900px){.layout{grid-template-columns:1fr}.result-card{grid-row:auto}.result-card iframe{height:620px;min-height:0}.stimulus-card iframe{height:360px}}
</style></head><body>
""" + f"<h1>{html.escape(run_id)}</h1><p class='sub'>Phase: {html.escape(phase)} · One page shows the experiment output beside its registered excitation.</p>" + (
        "<p class='note'>BVM excitation traces are direct raw.csv source-current tracks. MERGE INA/INB traces are the registered PWL source definition because those source voltages were not probed into solver raw.</p>"
    ) + f"<main class='layout'>{result_card}{''.join(cards)}</main></body></html>\n"


def main() -> int:
    viz_qa = load(ROOT / "analysis" / "STIMULUS_VIZ_QA.json")
    runs: list[dict[str, Any]] = []
    errors: list[str] = []
    skipped: list[dict[str, str]] = []
    raw_hash_before: dict[str, str] = {}
    for run_qa in viz_qa.get("runs", []):
        phase, run_id = run_qa["run_id"].split("/", 1) if "/" in run_qa["run_id"] else ("", run_qa["run_id"])
        # Derive phase from registered stimulus path, not from the display run label.
        first = run_qa["entries"][0]["input"].split("/", 1)[0]
        if first.startswith("phase_"):
            phase = first
        run_dir = ROOT / first / "runs" / run_id
        result_path = run_dir / "result.json"
        raw = run_dir / "raw.csv"
        output = run_dir / "plots" / "review.html"
        if not raw.is_file() and not result_path.is_file():
            skipped.append({"phase": phase, "run_id": run_id, "reason": "preserved failed solver attempt; no raw output"})
            continue
        if not result_path.is_file() or not raw.is_file():
            errors.append(f"incomplete result/raw pair for {phase}/{run_id}")
            continue
        result = load(result_path)
        if result.get("artifact_status") != "VALID":
            continue
        if not output.is_file():
            errors.append(f"missing output plot: {phase}/{run_id}")
            continue
        entries = run_qa.get("entries", [])
        if not entries:
            errors.append(f"no registered stimulus plots: {phase}/{run_id}")
            continue
        raw_hash = sha256(raw)
        raw_hash_before[str(raw.relative_to(ROOT))] = raw_hash
        for entry in entries:
            if not (ROOT / entry["output"]).is_file():
                errors.append(f"missing stimulus plot: {entry['output']}")
        combined = run_dir / "plots" / "combined.html"
        combined.write_text(combined_html(phase, run_id, output, entries), encoding="utf-8")
        runs.append({"phase": phase, "run_id": run_id, "artifact_status": result.get("artifact_status"), "raw_path": str(raw.relative_to(ROOT)), "raw_sha256_before": raw_hash, "raw_sha256_after": sha256(raw), "output_plot": str(output.relative_to(ROOT)), "output_plot_sha256": sha256(output), "combined_page": str(combined.relative_to(ROOT)), "combined_page_sha256": sha256(combined), "stimulus_entries": entries, "raw_unchanged": raw_hash == sha256(raw)})
    index = ROOT / "plots" / "COMBINED_INDEX.html"
    index.parent.mkdir(parents=True, exist_ok=True)
    rows = ["<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>Combined experiment review index</title><style>body{font:16px system-ui,sans-serif;margin:24px;background:#111827;color:#e5e7eb}table{border-collapse:collapse;width:100%}td,th{border:1px solid #475569;padding:8px;text-align:left}a{color:#93c5fd}.phase{margin-top:24px}</style></head><body>", f"<h1>{html.escape(ROOT.name)} — combined stimulus and output</h1>", "<p>Each run page shows the excitation and corresponding output plot together. Source definitions and raw tracks are labeled separately.</p>"]
    phases = sorted({item["phase"] for item in runs})
    for phase in phases:
        rows.append(f"<h2 class='phase'>{html.escape(phase)}</h2><table><tr><th>Run</th><th>Stimulus views</th><th>Output</th></tr>")
        for item in runs:
            if item["phase"] != phase:
                continue
            rel = Path(item["combined_page"])
            href = Path("..").joinpath(rel).as_posix()
            names = ", ".join(entry.get("label", entry.get("origin", "stimulus")) for entry in item["stimulus_entries"])
            rows.append(f"<tr><td><a href='{html.escape(href)}'>{html.escape(item['run_id'])}</a></td><td>{html.escape(names)}</td><td>{html.escape(item['artifact_status'])}</td></tr>")
        rows.append("</table>")
    if skipped:
        rows.append("<h2>Preserved failed attempts</h2>" + "".join(f"<p>{html.escape(item['phase'])}/{html.escape(item['run_id'])}: {html.escape(item['reason'])}. Deck, stimulus and logs remain available in the run directory.</p>" for item in skipped))
    rows.append("</body></html>")
    index.write_text("\n".join(rows) + "\n", encoding="utf-8")
    stimulus_index = ROOT / "plots" / "STIMULUS_INDEX.html"
    if stimulus_index.is_file():
        old = stimulus_index.read_text(encoding="utf-8")
        callout = "<p style='padding:10px;background:#1d4ed8;color:white;border-radius:6px'><a style='color:white' href='COMBINED_INDEX.html'>Open combined pages: excitation and output together for each run</a></p>"
        if "Open combined pages: excitation and output together for each run" not in old:
            old = old.replace("</p>", "</p>" + callout, 1)
            stimulus_index.write_text(old, encoding="utf-8")
    qa = {"schema": "bvm-qb-50ghz-combined-viz-qa-v1", "status": "PASS" if runs and not errors and all(item["raw_unchanged"] for item in runs) else "FAIL", "combined_run_count": len(runs), "skipped_incomplete_attempts": skipped, "index": str(index.relative_to(ROOT)), "index_sha256": sha256(index), "stimulus_viz_qa_status": viz_qa.get("status"), "raw_hashes_unchanged": all(item["raw_unchanged"] for item in runs), "scientific_interpretation_performed": False, "errors": errors, "runs": runs}
    (ROOT / "analysis" / "COMBINED_VIZ_QA.json").write_text(json.dumps(qa, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (ROOT / "analysis" / "COMBINED_VIZ_MANIFEST.json").write_text(json.dumps({"schema": "bvm-qb-50ghz-combined-viz-manifest-v1", "index": qa["index"], "index_sha256": qa["index_sha256"], "runs": runs}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": qa["status"], "combined_run_count": qa["combined_run_count"], "errors": errors, "index": qa["index"]}, ensure_ascii=False, indent=2))
    return 0 if qa["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
