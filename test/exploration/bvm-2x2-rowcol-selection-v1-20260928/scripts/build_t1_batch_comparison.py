#!/usr/bin/env python3
"""Build exact-grid T1 clock-pair and terminal-reference views with josim-plot2."""

from __future__ import annotations

import csv
import hashlib
import html
import importlib.util
import json
import os
import subprocess
from decimal import Decimal, InvalidOperation
from pathlib import Path
from types import SimpleNamespace
from typing import Any

SERIES = Path(__file__).resolve().parents[1]
REPO = next(path for path in SERIES.parents if (path / ".git").exists())
RUNS = SERIES / "runs"
PLOTTER = REPO / "scripts" / "josim-plot2.py"
PLOTLY_ASSET = (REPO / "test/exploration/bvm-qb-cb-array-topology-v1-20260924"
                / "plots/assets/plotly.min.js")
OUT = SERIES / "plots" / "comparison"
MASKS = (
    {"mask": "0", "rows": "00", "columns": "00", "terminal": "A013_SHARED_R00_C00",
     "quiet": "A019_T1_C1_Q0", "pulse": "A023_T1_C1_P0"},
    {"mask": "1", "rows": "10", "columns": "10", "terminal": "A014_SHARED_R10_C10",
     "quiet": "A020_T1_C1_Q1", "pulse": "A024_T1_C1_P1"},
    {"mask": "2", "rows": "01", "columns": "10", "terminal": "A015_SHARED_R01_C10",
     "quiet": "A021_T1_C1_Q2", "pulse": "A025_T1_C1_P2"},
    {"mask": "3", "rows": "11", "columns": "10", "terminal": "A016_SHARED_R11_C10",
     "quiet": "A022_T1_C1_Q3", "pulse": "A026_T1_C1_P3"},
)
CLOCK_SIGNALS = (
    "V(CLK)", "V(T1_I)", "V(S)", "V(C)", "V(VOUT_C1)", "V(VOUT_C2)",
    "P(B_J2|XT1)", "P(B_J3|XT1)", "P(B_J7|XT1)", "P(B_J9|XT1)", "P(B_J11|XT1)",
)
BASELINE_SIGNALS = ("V(VOUT_C1)", "V(VOUT_C2)")
CLOCK_WINDOW = (Decimal("110e-12"), Decimal("250e-12"))
PRE_CLOCK_WINDOW = (Decimal("110e-12"), Decimal("170e-12"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def align_exact_rows(
    rows_by_run: dict[str, dict[Decimal, tuple[str, ...]]],
    window: tuple[Decimal, Decimal],
) -> tuple[list[Decimal], dict[str, dict[Decimal, tuple[str, ...]]]]:
    start, end = window
    if end <= start or len(rows_by_run) < 2:
        raise ValueError("comparison needs multiple runs and a positive [start,end) window")
    selected = {run: {t: values for t, values in rows.items() if start <= t < end}
                for run, rows in rows_by_run.items()}
    common = set.intersection(*(set(rows) for rows in selected.values()))
    if len(common) < 2:
        raise ValueError("fewer than two exact common stored timestamps")
    return sorted(common), selected


def read_run(run_id: str, signals: tuple[str, ...]) -> tuple[dict[Decimal, tuple[str, ...]], dict[str, Any]]:
    raw = RUNS / run_id / "raw.csv"
    if not raw.is_file():
        raise FileNotFoundError(f"missing registered raw: {raw}")
    before = sha256(raw)
    rows: dict[Decimal, tuple[str, ...]] = {}
    with raw.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.reader(stream)
        header = next(reader, None)
        if not header or header[0] != "time" or len(header) != len(set(header)):
            raise ValueError(f"invalid/duplicate raw header: {raw}")
        missing = sorted(set(signals) - set(header))
        if missing:
            raise ValueError(f"{run_id} missing comparison signals: {missing}")
        indexes = [header.index(signal) for signal in signals]
        previous = None
        for row_no, row in enumerate(reader, start=2):
            if not row:
                continue
            try:
                stamp = Decimal(row[0])
                values = tuple(row[index] for index in indexes)
                numbers = tuple(Decimal(value) for value in values)
            except (InvalidOperation, IndexError) as exc:
                raise ValueError(f"invalid token at {raw}:{row_no}") from exc
            if (not stamp.is_finite() or any(not value.is_finite() for value in numbers)
                    or (previous is not None and stamp <= previous)):
                raise ValueError(f"non-finite/nonmonotonic sample at {raw}:{row_no}")
            previous = stamp
            rows[stamp] = values
    after = sha256(raw)
    if before != after:
        raise ValueError(f"raw changed during comparison: {raw}")
    return rows, {
        "run_id": run_id, "raw_path": str(raw.relative_to(SERIES)),
        "raw_sha256_before": before, "raw_sha256_after": after,
        "raw_immutable": before == after, "source_sample_count": len(rows),
        "signals": list(signals),
    }


def load_plotter() -> Any:
    spec = importlib.util.spec_from_file_location("josim_plot2_t1_batch_compare", PLOTTER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import classic plotter: {PLOTTER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build_section(run_ids: tuple[str, ...], signals: tuple[str, ...],
                  window: tuple[Decimal, Decimal], title: str,
                  plotter: Any) -> tuple[str, dict[str, Any]]:
    rows_by_run = {}
    inputs = []
    for run_id in run_ids:
        rows, record = read_run(run_id, signals)
        rows_by_run[run_id] = rows
        inputs.append(record)
    times, aligned = align_exact_rows(rows_by_run, window)
    labels = [f"{signal} [{run_id}]" for run_id in run_ids for signal in signals]
    import pandas as pd

    data: dict[str, Any] = {"time": [float(t) for t in times]}
    for run_id in run_ids:
        for index, signal in enumerate(signals):
            label = f"{signal} [{run_id}]"
            data[label] = [float(aligned[run_id][t][index]) for t in times]
    frame = pd.DataFrame(data)
    figure = plotter.seperate_combined_layout(
        frame, SimpleNamespace(subset=labels, jump="2pi"))
    figure.update_layout(title=title, title_font_size=20, template="plotly_dark")
    section_html = figure.to_html(full_html=False, include_plotlyjs=False)
    record = {
        "title": title, "run_ids": list(run_ids), "signals_per_run": list(signals),
        "window_seconds": [str(window[0]), str(window[1])],
        "boundary_rule": "[start,end)", "alignment": "exact common stored timestamps only",
        "interpolation_or_resampling": False, "common_sample_count": len(times),
        "first_common_time_seconds": str(times[0]), "last_common_time_seconds": str(times[-1]),
        "inputs": inputs,
    }
    return section_html, record


def write_page(path: Path, title: str, sections: list[tuple[str, dict[str, Any]]]) -> dict[str, Any]:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite comparison page: {path}")
    asset_ref = Path(os.path.relpath(PLOTLY_ASSET, path.parent)).as_posix()
    parts = ["<!doctype html><html><head><meta charset=\"utf-8\">",
             f"<script src=\"{html.escape(asset_ref)}\"></script></head><body>",
             f"<h1>{html.escape(title)}</h1>",
             "<p>Classic josim-plot2 sep_comb/dark/-j 2pi; exact raw rows only; no interpolation.</p>"]
    for section_html, record in sections:
        parts.append(f"<section><h2>{html.escape(record['title'])}</h2>{section_html}</section>")
    parts.append("</body></html>\n")
    content = "\n".join(parts)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    if content.count(asset_ref) != 1 or content.count("Plotly.newPlot") != len(sections):
        raise ValueError(f"comparison HTML asset/figure count mismatch: {path}")
    return {"path": str(path.relative_to(SERIES)), "sha256": sha256(path),
            "shared_plotly_asset_count": 1, "section_count": len(sections), "status": "PASS"}


def main() -> int:
    for run in [case[key] for case in MASKS for key in ("terminal", "quiet", "pulse")]:
        if not (RUNS / run / "raw.csv").is_file():
            raise FileNotFoundError(f"T1 comparison is incomplete; missing raw for {run}")
    if not PLOTLY_ASSET.is_file():
        raise FileNotFoundError(f"shared classic Plotly asset missing: {PLOTLY_ASSET}")
    manifest_path = SERIES / "analysis" / "t1_batch_comparison_manifest.json"
    qa_path = SERIES / "analysis" / "t1_batch_comparison_qa.json"
    if manifest_path.exists() or qa_path.exists():
        raise FileExistsError("refusing to overwrite T1 comparison manifest/QA")
    plotter = load_plotter()
    clock_sections = []
    baseline_sections = []
    for item in MASKS:
        clock_title = (f"Mask {item['mask']} ({item['rows']}/{item['columns']}): "
                       "QUIET vs PULSE [110,250) ps")
        clock_html, clock_record = build_section(
            (item["quiet"], item["pulse"]), CLOCK_SIGNALS, CLOCK_WINDOW, clock_title, plotter)
        clock_sections.append((clock_html, clock_record))
        baseline_title = (f"Mask {item['mask']} ({item['rows']}/{item['columns']}): "
                          f"TERMINAL {item['terminal']} vs T1 QUIET/PULSE [110,170) ps")
        baseline_html, baseline_record = build_section(
            (item["terminal"], item["quiet"], item["pulse"]),
            BASELINE_SIGNALS, PRE_CLOCK_WINDOW, baseline_title, plotter)
        baseline_record["load_comparability"] = "NOT_MATCHED: terminal baseline has 2-ohm C1 load; T1_C1 uses T1 input"
        baseline_sections.append((baseline_html, baseline_record))
    OUT.mkdir(parents=True, exist_ok=True)
    clock_page = write_page(OUT / "T1_C1_quiet_vs_pulse_exact_grid.html",
                            "T1_C1 clock mode pairs — full registered response windows", clock_sections)
    baseline_page = write_page(OUT / "T1_C1_vs_A013_A016_terminal_frontend.html",
                               "T1_C1 vs terminal reference — pre-clock front-end output; load differs",
                               baseline_sections)
    comparisons = [
        {"id": "T1_C1_QUIET_VS_PULSE", "window_seconds": [str(CLOCK_WINDOW[0]), str(CLOCK_WINDOW[1])],
         "alignment": "exact common stored timestamps only", "interpolation_or_resampling": False,
         "sections": [record for _html, record in clock_sections], "page": clock_page},
        {"id": "A013_A016_TERMINAL_VS_T1_FRONTEND", "window_seconds": [str(PRE_CLOCK_WINDOW[0]), str(PRE_CLOCK_WINDOW[1])],
         "alignment": "exact common stored timestamps only", "interpolation_or_resampling": False,
         "load_comparability": "NOT_MATCHED: terminal C1 2-ohm vs T1 input",
         "sections": [record for _html, record in baseline_sections], "page": baseline_page},
    ]
    manifest = {
        "schema": "bvm-2x2-t1-batch-comparison-v1",
        "parent_head": subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=REPO, check=True,
            capture_output=True, text=True).stdout.strip(),
        "comparisons": comparisons, "plotter_path": str(PLOTTER.relative_to(REPO)),
        "plotter_sha256": sha256(PLOTTER),
        "plotly_asset_path": str(PLOTLY_ASSET.relative_to(REPO)),
        "plotly_asset_sha256": sha256(PLOTLY_ASSET),
        "scientific_interpretation_performed": False,
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                             encoding="utf-8")
    raw_hashes_stable = all(record["raw_immutable"]
                            for comparison in comparisons
                            for section in comparison["sections"]
                            for record in section["inputs"])
    qa = {
        "schema": "bvm-2x2-t1-batch-comparison-qa-v1",
        "status": "PASS" if raw_hashes_stable and all(comp["page"]["status"] == "PASS"
                                                       for comp in comparisons) else "FAIL",
        "raws_immutable": raw_hashes_stable, "interpolation_or_resampling": False,
        "comparison_count": len(comparisons), "page_count": 2,
        "manifest_sha256": sha256(manifest_path),
        "scientific_interpretation_performed": False,
    }
    qa_path.write_text(json.dumps(qa, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": qa["status"], "comparison_count": len(comparisons),
                      "pages": [clock_page, baseline_page],
                      "manifest": str(manifest_path.relative_to(SERIES)),
                      "qa": str(qa_path.relative_to(SERIES))}, ensure_ascii=False, indent=2))
    return 0 if qa["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
