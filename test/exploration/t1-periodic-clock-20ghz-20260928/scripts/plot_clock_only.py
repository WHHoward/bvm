#!/usr/bin/env python3
"""Render classic josim-plot2 pages from the immutable CLK-only raw CSV."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

EXPERIMENT = Path(__file__).resolve().parents[1]
REPO = Path(__file__).resolve().parents[4]
SERIES = REPO / "test/exploration/bvm-qb-cb-array-topology-v1-20260924"
PLOTTER = REPO / "scripts/josim-plot2.py"
ASSET = SERIES / "plots/assets/plotly.min.js"
sys.path.insert(0, str(REPO / "scripts"))
from bvmtools.raw import read_csv  # noqa: E402
from clock_metrics import exact_stored_times  # noqa: E402
from config import parse_quantity  # noqa: E402


def digest(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_plotter():
    spec = importlib.util.spec_from_file_location("josim_plot2_clock_only", PLOTTER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import classic plotter: {PLOTTER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def render(run_dir: str | Path) -> dict[str, object]:
    root = Path(run_dir).resolve()
    raw = root / "raw.csv"
    if not raw.is_file() or not ASSET.is_file():
        raise RuntimeError("raw.csv or shared Plotly asset is missing")
    before = digest(raw)
    trace = read_csv(raw)
    if trace.duplicate_columns:
        raise RuntimeError(f"duplicate raw columns: {trace.duplicate_columns}")
    manifest = json.loads((root / "probe_manifest.json").read_text(encoding="utf-8"))
    labels = [str(item["label"]) for item in manifest["signals"]]
    if len(labels) != len(set(labels)):
        raise RuntimeError("probe manifest has duplicate signal labels")
    missing = [label for label in labels if label not in trace.headers]
    if missing:
        raise RuntimeError(f"probe manifest labels missing from raw: {missing}")

    config = json.loads((root / "USER_CASE.snapshot.json").read_text(encoding="utf-8"))
    clock_start = parse_quantity(config["T1_CLK_START"], label="T1_CLK_START")
    period = parse_quantity(config["T1_CLK_PERIOD"], label="T1_CLK_PERIOD")
    cycle_windows = [(clock_start + index * period,
                      clock_start + (index + 1) * period) for index in range(4)]
    cycle_labels = [
        "V(CLK_RAW)", "V(CLK)", "I(R_TRIG_CLK)", "V(S)", "V(C)",
        *(f"{quantity}({jj}|XT1)" for jj in ("B_J2", "B_J3", "B_J7", "B_J9", "B_J11")
          for quantity in ("P", "V")),
    ]
    pages: list[dict[str, object]] = [
        {"file": "01_CLK_AND_KEY_JJS.html", "title": "CLK input, outputs, and registered JJ state",
         "signals": cycle_labels, "window_s": None},
    ]
    for index, (start, end) in enumerate(cycle_windows, start=1):
        pages.append({
            "file": f"cycles/CLK_CYCLE_{index:02d}.html",
            "title": f"CLK cycle {index}: {float(start) * 1e12:g} ps",
            "signals": cycle_labels,
            "window_s": [float(start), float(end)],
            "_window_exact": (start, end),
            "window_rule": "[start,end); actual stored rows only",
        })

    import pandas as pd
    frame = pd.read_csv(raw)
    exact_times = exact_stored_times(raw)
    if len(exact_times) != len(frame):
        raise RuntimeError("exact stored-time row count disagrees with plotted raw rows")
    plotter = load_plotter()
    output = root / "plots"
    output.mkdir(parents=True, exist_ok=True)
    rendered = []
    for page in pages:
        selected = page["signals"]
        if not isinstance(selected, list) or not selected:
            raise RuntimeError(f"empty plot signal set: {page['file']}")
        window = page.get("window_s")
        current = frame
        if window is not None:
            lo, hi = page["_window_exact"]
            rows = [index for index, stamp in enumerate(exact_times) if lo <= stamp < hi]
            current = frame.iloc[rows].copy()
            if len(current) < 2:
                raise RuntimeError(f"fewer than two actual raw rows in plot window {window}")
        target = output / str(page["file"])
        target.parent.mkdir(parents=True, exist_ok=True)
        asset_reference = os.path.relpath(ASSET, target.parent).replace(os.sep, "/")
        args = SimpleNamespace(subset=selected, jump="2pi")
        figure = plotter.seperate_combined_layout(current, args)
        figure.update_layout(title=f"{root.name} — {page['title']}", title_font_size=22,
                             template="plotly_dark")
        figure.write_html(target, include_plotlyjs=asset_reference, full_html=True,
                          auto_open=False)
        text = target.read_text(encoding="utf-8")
        if (asset_reference not in text
                or (target.parent / asset_reference).resolve() != ASSET.resolve()):
            raise RuntimeError(f"shared Plotly asset reference missing in {target}")
        rendered.append({
            "path": target.relative_to(root).as_posix(), "sha256": digest(target),
            "status": "PASS", "trace_count": len(selected),
            "sample_count": len(current), "window_s": window,
        })

    after = digest(raw)
    qa = {
        "schema": "t1-clock-only-plot-qa-v1",
        "status": "PASS" if before == after and len(rendered) == 5 else "FAIL",
        "raw_sha256_before": before, "raw_sha256_after": after,
        "raw_immutable": before == after,
        "plotter_path": PLOTTER.relative_to(REPO).as_posix(),
        "plotter_sha256": digest(PLOTTER),
        "shared_plotly_asset_path": ASSET.relative_to(REPO).as_posix(),
        "shared_plotly_asset_sha256": digest(ASSET),
        "layout": "josim-plot2.py sep_comb dark -j 2pi",
        "phase_display": "raw P(...) radians; display turns = rad/(2*pi)",
        "interpolation_or_resampling": False,
        "full_run_pages": 1, "registered_cycle_pages": 4,
        "page_count": len(rendered), "pages": rendered,
        "scientific_interpretation_performed": False,
    }
    (root / "analysis").mkdir(parents=True, exist_ok=True)
    manifest_pages = [
        {key: value for key, value in page.items() if not key.startswith("_")}
        for page in pages
    ]
    (root / "analysis/plot_manifest.json").write_text(
        json.dumps({"schema": "t1-clock-only-plot-manifest-v1", "raw_sha256": before,
                    "pages": manifest_pages, "plotter_sha256": qa["plotter_sha256"],
                    "plotly_asset_sha256": qa["shared_plotly_asset_sha256"],
                    "scientific_interpretation_performed": False},
                   ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (root / "analysis/plot_qa.json").write_text(
        json.dumps(qa, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return qa


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: plot_clock_only.py <run-dir>", file=sys.stderr)
        return 2
    try:
        qa = render(sys.argv[1])
        print(json.dumps(qa, ensure_ascii=False, indent=2))
        return 0 if qa["status"] == "PASS" else 2
    except Exception as exc:
        print(f"PLOT_QA_FAIL: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
