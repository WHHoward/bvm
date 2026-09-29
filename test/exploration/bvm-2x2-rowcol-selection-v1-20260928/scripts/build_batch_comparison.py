#!/usr/bin/env python3
"""Build exact-grid, classic-plot comparisons for the registered A/B/C batch."""

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
    """Return only common actual timestamps in [start,end); never interpolate."""
    start, end = window
    if end <= start or len(series) < 2:
        raise ValueError("comparison needs at least two series and a positive half-open window")
    selected = {
        case: {stamp: values for stamp, values in rows.items() if start <= stamp < end}
        for case, rows in series.items()
    }
    common = set.intersection(*(set(rows) for rows in selected.values()))
    if len(common) < 2:
        raise ValueError("fewer than two exact common stored timestamps in comparison window")
    times = sorted(common)
    return times, selected


def _read_run(run_id: str, signals: list[str], window: tuple[Decimal, Decimal]
              ) -> tuple[dict[Decimal, tuple[str, ...]], dict[str, Any]]:
    raw = RUNS / run_id / "raw.csv"
    if not raw.is_file():
        raise FileNotFoundError(f"registered comparison raw is missing: {raw}")
    before = sha256(raw)
    rows: dict[Decimal, tuple[str, ...]] = {}
    with raw.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.reader(stream)
        header = next(reader, None)
        if not header or header[0] != "time" or len(header) != len(set(header)):
            raise ValueError(f"raw header is missing/duplicated: {raw}")
        missing = sorted(set(signals) - set(header))
        if missing:
            raise ValueError(f"raw {run_id} is missing comparison probes: {missing}")
        indexes = [header.index(signal) for signal in signals]
        previous: Decimal | None = None
        for row_no, row in enumerate(reader, start=2):
            if not row:
                continue
            try:
                stamp = Decimal(row[0])
                values = tuple(row[index] for index in indexes)
                numeric = tuple(Decimal(value) for value in values)
            except (InvalidOperation, IndexError) as exc:
                raise ValueError(f"bad time/value in {raw}:{row_no}") from exc
            if (not stamp.is_finite() or any(not value.is_finite() for value in numeric)
                    or (previous is not None and stamp <= previous)):
                raise ValueError(f"non-finite or nonmonotonic stored grid in {raw}:{row_no}")
            previous = stamp
            rows[stamp] = values
    after = sha256(raw)
    if before != after:
        raise ValueError(f"raw changed while comparison was being built: {raw}")
    selected_count = sum(window[0] <= stamp < window[1] for stamp in rows)
    return rows, {"run_id": run_id, "raw_path": str(raw.relative_to(SERIES)),
                  "raw_sha256_before": before, "raw_sha256_after": after,
                  "raw_immutable": before == after, "samples_in_window": selected_count,
                  "source_sample_count": len(rows), "signals": signals}


def _plotter_module() -> Any:
    spec = importlib.util.spec_from_file_location("josim_plot2_batch_compare", PLOTTER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import classic plotter: {PLOTTER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _build_one(spec: dict[str, Any], plotter: Any) -> dict[str, Any]:
    window = (Decimal(spec["window_s"][0]), Decimal(spec["window_s"][1]))
    rows_by_case: dict[str, dict[Decimal, tuple[str, ...]]] = {}
    inputs = []
    for run_id, signals in spec["cases"].items():
        rows, record = _read_run(run_id, signals, window)
        rows_by_case[run_id] = rows
        inputs.append(record)
    times, selected = align_exact_rows(rows_by_case, window)
    columns = []
    for run_id, signals in spec["cases"].items():
        columns.extend((f"{signal} [{run_id}]", index)
                       for index, signal in enumerate(signals))

    stem = spec["stem"]
    csv_path = OUT / f"{stem}.csv"
    html_path = OUT / f"{stem}.html"
    if csv_path.exists() or html_path.exists():
        raise FileExistsError(f"refusing to overwrite comparison artifact for {stem}")
    OUT.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["time", *[name for name, _index in columns]])
        for stamp in times:
            values = []
            for run_id, _signals in spec["cases"].items():
                values.extend(selected[run_id][stamp])
            writer.writerow([str(stamp), *values])

    import pandas as pd

    frame = pd.read_csv(csv_path)
    plot_subset = [name for name, _index in columns]
    figure = plotter.seperate_combined_layout(
        frame, SimpleNamespace(subset=plot_subset, jump="2pi"))
    figure.update_layout(title=spec["title"], title_font_size=22, template="plotly_dark")
    asset_ref = Path(os.path.relpath(PLOTLY_ASSET, html_path.parent)).as_posix()
    figure.write_html(html_path, include_plotlyjs=asset_ref, full_html=True, auto_open=False)
    if asset_ref not in html_path.read_text(encoding="utf-8"):
        raise ValueError(f"classic comparison page omitted shared plotly asset: {html_path}")

    raw_hashes_stable = all(item["raw_immutable"] for item in inputs)
    return {
        "stem": stem, "title": spec["title"], "window_s": [str(window[0]), str(window[1])],
        "boundary_rule": "[start,end)", "alignment": "exact common stored timestamps only",
        "interpolation_or_resampling": False, "common_sample_count": len(times),
        "first_common_time_s": str(times[0]), "last_common_time_s": str(times[-1]),
        "inputs": inputs, "derived_csv": str(csv_path.relative_to(SERIES)),
        "derived_csv_sha256": sha256(csv_path), "classic_html": str(html_path.relative_to(SERIES)),
        "classic_html_sha256": sha256(html_path), "plotter_sha256": sha256(PLOTTER),
        "plotly_asset_sha256": sha256(PLOTLY_ASSET),
        "raw_immutable": raw_hashes_stable, "status": "PASS" if raw_hashes_stable else "FAIL",
        "scientific_interpretation_performed": False,
    }


def main() -> int:
    specs = [
        {
            "stem": "A009_vs_A010_first_read_response",
            "title": "A009 same-row vs A010 same-column — first response [110,170) ps",
            "window_s": ["110e-12", "170e-12"],
            "cases": {
                "A009_SHARED_R10_C11": ["V(VOUT_R1C1)", "V(VOUT_R1C2)"],
                "A010_SHARED_R11_C10": ["V(VOUT_R1C1)", "V(VOUT_R2C1)"],
            },
        },
        {
            "stem": "A010_A011_A012_full_read_outputs",
            "title": "A010/A011/A012 four independent VOUT traces — common raw rows [0,250) ps",
            "window_s": ["0", "250e-12"],
            "cases": {
                run_id: [f"V(VOUT_{cell})" for cell in ("R1C1", "R1C2", "R2C1", "R2C2")]
                for run_id in ("A010_SHARED_R11_C10", "A011_SHARED_R11_C11",
                               "A012_SHARED_R11_C11")
            },
        },
    ]
    if not PLOTLY_ASSET.is_file():
        raise FileNotFoundError(f"shared classic-plot asset missing: {PLOTLY_ASSET}")
    plotter = _plotter_module()
    comparisons = [_build_one(spec, plotter) for spec in specs]
    manifest_path = SERIES / "analysis" / "batch_comparison_manifest.json"
    qa_path = SERIES / "analysis" / "batch_comparison_qa.json"
    for path in (manifest_path, qa_path):
        if path.exists():
            raise FileExistsError(f"refusing to overwrite batch comparison record: {path}")
    manifest = {
        "schema": "bvm-2x2-batch-comparison-v1",
        "parent_head": subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=REPO, check=True,
            capture_output=True, text=True).stdout.strip(),
        "comparisons": comparisons,
        "scientific_interpretation_performed": False,
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                             encoding="utf-8")
    qa = {"schema": "bvm-2x2-batch-comparison-qa-v1",
          "status": "PASS" if all(item["status"] == "PASS" for item in comparisons) else "FAIL",
          "comparison_count": len(comparisons), "raws_immutable": True,
          "interpolation_or_resampling": False,
          "manifest_sha256": sha256(manifest_path),
          "scientific_interpretation_performed": False}
    qa_path.write_text(json.dumps(qa, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": qa["status"], "comparisons": comparisons,
                      "manifest": str(manifest_path.relative_to(SERIES)),
                      "qa": str(qa_path.relative_to(SERIES))}, ensure_ascii=False, indent=2))
    return 0 if qa["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
