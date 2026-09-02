#!/usr/bin/env python3
"""Semantic QA for the three Boundary HTML projections.

The check is read-only.  It verifies that the classic renderer kept the
P/V/I prefixes, assigned the expected axes, and numerically converted the B3
phase trace to turns.
"""

from __future__ import annotations

import base64
import json
from pathlib import Path
import sys

import numpy as np


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

from bvmtools.phase import TAU, continuous_unwrap  # noqa: E402
from bvmtools.raw import read_csv  # noqa: E402


EXPECTED_TITLES = {
    "BOUNDARY_B0_QBIN.html": ("Voltage (V)", "Phase (turns) [rad/2pi]", "Current (I)"),
    "BOUNDARY_B2_BJ2.html": ("Voltage (V)", "Phase (turns) [rad/2pi]"),
    "BOUNDARY_B3_TRANSPORT.html": ("Voltage (V)", "Phase (turns) [rad/2pi]"),
}


def plot_json(path: Path) -> tuple[list[dict[str, object]], dict[str, object]]:
    source = path.read_text(encoding="utf-8")
    marker = "Plotly.newPlot("
    marker_position = source.rfind(marker)
    if marker_position < 0:
        raise AssertionError(f"{path}: Plotly call not found")
    decoder = json.JSONDecoder()
    data_start = source.find("[", marker_position)
    data, after_data = decoder.raw_decode(source, data_start)
    layout_start = after_data
    while source[layout_start] in " \t\r\n,":
        layout_start += 1
    layout, _ = decoder.raw_decode(source, layout_start)
    return data, layout


def array_values(value: object) -> np.ndarray:
    if isinstance(value, list):
        return np.asarray(value, dtype=float)
    if isinstance(value, dict) and "bdata" in value:
        return np.frombuffer(base64.b64decode(value["bdata"]), dtype=np.dtype(value["dtype"]))
    raise AssertionError(f"unsupported Plotly array representation: {type(value)}")


def main() -> int:
    for filename, expected_titles in EXPECTED_TITLES.items():
        path = EXP / "plots" / filename
        data, layout = plot_json(path)
        titles = [
            layout[key].get("title", {}).get("text")
            for key in sorted(layout)
            if key.startswith("yaxis")
        ]
        names = [str(trace.get("name")) for trace in data]
        if not all(name and name[0] in "PVI" for name in names):
            raise AssertionError(f"{filename}: a trace lost its P/V/I prefix: {names}")
        if not all(title in titles for title in expected_titles):
            raise AssertionError(f"{filename}: unexpected y-axis titles: {titles}")
        if "Unknown" in titles:
            raise AssertionError(f"{filename}: Unknown is an axis title")
        print(f"{filename}: traces={len(names)} y_titles={titles}")

    b3_data, _ = plot_json(EXP / "plots/BOUNDARY_B3_TRANSPORT.html")
    phase_trace = next(
        trace for trace in b3_data if trace.get("name") == "P(BJ2|XBQ1) [S1-J]"
    )
    plotted = array_values(phase_trace["y"])
    raw = read_csv(EXP / "runs/A001/S1-J/raw.csv")
    expected = np.asarray(continuous_unwrap(raw.column("P(BJ2|XBQ1)")), dtype=float) / TAU
    if plotted.shape != expected.shape:
        raise AssertionError(f"B3 phase length mismatch: {plotted.shape} vs {expected.shape}")
    error = float(np.max(np.abs(plotted - expected)))
    if error > 1.0e-12:
        raise AssertionError(f"B3 phase conversion error is {error} turns")
    print(f"B3 S1-J BJ2 phase conversion max_abs_error={error:.3e} turns")
    print("HTML_SEMANTIC_QA=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
