#!/usr/bin/env python3
"""Build the registered exact-grid T0-T5 column-output overlay."""

from __future__ import annotations

import csv
import hashlib
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
RUN_IDS = (
    "A013_SHARED_R00_C00",
    "A014_SHARED_R10_C10",
    "A015_SHARED_R01_C10",
    "A016_SHARED_R11_C10",
    "A017_SHARED_R10_C11",
    "A018_SHARED_R11_C11",
)
SIGNALS = ("V(VOUT_C1)", "V(VOUT_C2)")
WINDOW = (Decimal("0"), Decimal("250e-12"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def align_exact_rows(
    series: dict[str, dict[Decimal, tuple[str, ...]]],
    window: tuple[Decimal, Decimal],
) -> tuple[list[Decimal], dict[str, dict[Decimal, tuple[str, ...]]]]:
    """Select the exact timestamp intersection inside [start,end)."""
    start, end = window
    if end <= start or len(series) < 2:
        raise ValueError("comparison needs multiple series and a positive half-open window")
    selected = {
        name: {stamp: values for stamp, values in rows.items() if start <= stamp < end}
        for name, rows in series.items()
    }
    common = set.intersection(*(set(rows) for rows in selected.values()))
    if len(common) < 2:
        raise ValueError("fewer than two exact common stored timestamps in comparison window")
    return sorted(common), selected


def read_run(run_id: str) -> tuple[dict[Decimal, tuple[str, ...]], dict[str, Any]]:
    raw = RUNS / run_id / "raw.csv"
    if not raw.is_file():
        raise FileNotFoundError(f"registered run raw is missing: {raw}")
    before = sha256(raw)
    rows: dict[Decimal, tuple[str, ...]] = {}
    with raw.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.reader(stream)
        header = next(reader, None)
        if not header or header[0] != "time" or len(header) != len(set(header)):
            raise ValueError(f"raw header is missing/duplicated: {raw}")
        missing = sorted(set(SIGNALS) - set(header))
        if missing:
            raise ValueError(f"raw {run_id} is missing comparison probes: {missing}")
        indices = [header.index(signal) for signal in SIGNALS]
        previous: Decimal | None = None
        for row_no, row in enumerate(reader, start=2):
            if not row:
                continue
            try:
                stamp = Decimal(row[0])
                values = tuple(row[index] for index in indices)
                numeric = tuple(Decimal(value) for value in values)
            except (InvalidOperation, IndexError) as exc:
                raise ValueError(f"invalid raw time/value in {raw}:{row_no}") from exc
            if (not stamp.is_finite() or any(not value.is_finite() for value in numeric)
                    or (previous is not None and stamp <= previous)):
                raise ValueError(f"non-finite or nonmonotonic stored grid in {raw}:{row_no}")
            previous = stamp
            rows[stamp] = values
    after = sha256(raw)
    if before != after:
        raise ValueError(f"raw changed during comparison: {raw}")
    count = sum(WINDOW[0] <= stamp < WINDOW[1] for stamp in rows)
    return rows, {
        "run_id": run_id,
        "raw_path": str(raw.relative_to(SERIES)),
        "raw_sha256_before": before,
        "raw_sha256_after": after,
        "raw_immutable": before == after,
        "sample_count": len(rows),
        "window_sample_count": count,
        "signals": list(SIGNALS),
    }


def load_plotter() -> Any:
    spec = importlib.util.spec_from_file_location("josim_plot2_merge_compare", PLOTTER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import classic plotter: {PLOTTER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    records: dict[str, dict[Decimal, tuple[str, ...]]] = {}
    inputs = []
    for run_id in RUN_IDS:
        rows, record = read_run(run_id)
        records[run_id] = rows
        inputs.append(record)
    times, selected = align_exact_rows(records, WINDOW)
    labels = [f"{signal} [{run_id}]" for run_id in RUN_IDS for signal in SIGNALS]
    OUT.mkdir(parents=True, exist_ok=True)
    csv_path = OUT / "M_T0_T5_column_outputs_exact_grid.csv"
    html_path = OUT / "M_T0_T5_column_outputs_exact_grid.html"
    manifest_path = SERIES / "analysis" / "merge_batch_comparison_manifest.json"
    qa_path = SERIES / "analysis" / "merge_batch_comparison_qa.json"
    for path in (csv_path, html_path, manifest_path, qa_path):
        if path.exists():
            raise FileExistsError(f"refusing to overwrite comparison artifact: {path}")
    with csv_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["time", *labels])
        for stamp in times:
            values = [value for run_id in RUN_IDS for value in selected[run_id][stamp]]
            writer.writerow([str(stamp), *values])

    import pandas as pd

    frame = pd.read_csv(csv_path)
    plotter = load_plotter()
    figure = plotter.seperate_combined_layout(
        frame, SimpleNamespace(subset=labels, jump="2pi"))
    figure.update_layout(
        title="T0-T5 merged-column VOUT_C1/VOUT_C2 — exact common raw rows [0,250) ps",
        title_font_size=22,
        template="plotly_dark",
    )
    if not PLOTLY_ASSET.is_file():
        raise FileNotFoundError(f"shared classic plot asset missing: {PLOTLY_ASSET}")
    asset_ref = Path(os.path.relpath(PLOTLY_ASSET, html_path.parent)).as_posix()
    figure.write_html(html_path, include_plotlyjs=asset_ref, full_html=True, auto_open=False)
    if asset_ref not in html_path.read_text(encoding="utf-8"):
        raise ValueError("comparison page does not reference the established shared Plotly asset")

    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, check=True,
                          capture_output=True, text=True).stdout.strip()
    manifest = {
        "schema": "bvm-2x2-merge-batch-comparison-v1",
        "parent_head": head,
        "run_ids": list(RUN_IDS),
        "signals": list(SIGNALS),
        "window_seconds": [str(WINDOW[0]), str(WINDOW[1])],
        "boundary_rule": "[start,end)",
        "alignment": "exact common stored timestamps only",
        "interpolation_or_resampling": False,
        "common_sample_count": len(times),
        "first_common_time_seconds": str(times[0]),
        "last_common_time_seconds": str(times[-1]),
        "inputs": inputs,
        "derived_csv": str(csv_path.relative_to(SERIES)),
        "derived_csv_sha256": sha256(csv_path),
        "classic_html": str(html_path.relative_to(SERIES)),
        "classic_html_sha256": sha256(html_path),
        "plotter_sha256": sha256(PLOTTER),
        "plotly_asset_sha256": sha256(PLOTLY_ASSET),
        "scientific_interpretation_performed": False,
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                             encoding="utf-8")
    qa = {
        "schema": "bvm-2x2-merge-batch-comparison-qa-v1",
        "status": "PASS" if all(item["raw_immutable"] for item in inputs) else "FAIL",
        "comparison_count": 1,
        "raws_immutable": all(item["raw_immutable"] for item in inputs),
        "interpolation_or_resampling": False,
        "common_sample_count": len(times),
        "manifest_sha256": sha256(manifest_path),
        "scientific_interpretation_performed": False,
    }
    qa_path.write_text(json.dumps(qa, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": qa["status"], "run_ids": list(RUN_IDS),
                      "common_sample_count": len(times), "alignment": "exact timestamps only",
                      "interpolation_or_resampling": False,
                      "csv": str(csv_path.relative_to(SERIES)),
                      "html": str(html_path.relative_to(SERIES)),
                      "manifest": str(manifest_path.relative_to(SERIES)),
                      "qa": str(qa_path.relative_to(SERIES))}, ensure_ascii=False, indent=2))
    return 0 if qa["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
