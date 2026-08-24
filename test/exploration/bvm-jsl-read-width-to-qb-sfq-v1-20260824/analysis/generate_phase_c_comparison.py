#!/usr/bin/env python3
"""Generate the registered 9 ps versus W*=12 ps frozen-QB replay comparison.

This is a descriptive visualization only.  Event status remains the formal
phase/area analysis in ``analysis/PHASE_C_REPORT.md``.
"""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots


ROOT = Path(__file__).resolve().parents[1]
Q1 = ROOT.parent / "paper-sl-q1-20260824"
OUT = ROOT / "plots/9ps-vs-Wstar-qb-replay-comparison.html"
META = ROOT / "plots/9ps-vs-Wstar-qb-replay-comparison.metadata.json"

JUNCTIONS = [
    ("BJs", "P(BJs|XBQ)", "V(BJs|XBQ)"),
    ("BJL1", "P(BJL1|XBQ)", "V(BJL1|XBQ)"),
    ("BJL2", "P(BJL2|XBQ)", "V(BJL2|XBQ)"),
]

CASES = [
    (
        "logical1 + READ",
        "paper-j1-logical1-read",
        "wstar12-logical1-read",
        "read1",
    ),
    (
        "logical0 + READ",
        "paper-j0-logical0-read",
        "wstar12-logical0-read",
        "read0",
    ),
    (
        "logical1 + READ=0",
        "paper-j1-logical1-read0-control",
        "wstar12-logical1-read0-control",
        "zero_control_logical1",
    ),
    (
        "logical0 + READ=0",
        "paper-j0-logical0-read0-control",
        "wstar12-logical0-read0-control",
        "zero_control_logical0",
    ),
]


def read_csv(path: Path) -> dict[str, np.ndarray]:
    with path.open(newline="") as handle:
        rows = list(csv.reader(handle))
    header = [item.strip() for item in rows[0]]
    values = np.asarray([[float(value) for value in row] for row in rows[1:] if row], dtype=float)
    data = {name: values[:, index] for index, name in enumerate(header)}
    data["time_ps"] = data["time"] * 1e12
    return data


def get(data: dict[str, np.ndarray], requested: str) -> np.ndarray:
    if requested in data:
        return data[requested]
    normalized = {key.replace(" ", "").lower(): key for key in data}
    key = normalized[requested.replace(" ", "").lower()]
    return data[key]


def add_trace(
    fig: go.Figure,
    data: dict[str, np.ndarray],
    signal: str,
    row: int,
    col: int,
    label: str,
    color: str,
    legend: bool,
    group: str,
) -> None:
    value = get(data, signal)
    if signal.startswith("P("):
        value = np.unwrap(value) / (2.0 * math.pi)
    fig.add_trace(
        go.Scatter(
            x=data["time_ps"],
            y=value,
            mode="lines",
            name=label,
            legendgroup=group,
            showlegend=legend,
            line={"color": color, "width": 1.4},
            hovertemplate=f"{label}<br>t=%{{x:.4f}} ps<br>%{{y:.6g}}<extra></extra>",
        ),
        row=row,
        col=col,
    )


def main() -> None:
    phase_a = ROOT / "raw/phase-c"
    # Q1 stores the accepted 9 ps comparator as flat CSV files.
    sources: dict[str, dict[str, Path]] = {}
    for _, q1_id, wstar_id, role in CASES:
        sources[role] = {
            "9ps": Q1 / "raw" / f"{q1_id}.csv",
            "wstar12": phase_a / wstar_id / "run-01.csv",
        }

    rows = [
        ("read1", "logical1 + READ · continuous phase φ/2π (turn)"),
        ("read0", "logical0 + READ · continuous phase φ/2π (turn)"),
        ("zero_control_logical1", "logical1 + READ=0 · continuous phase φ/2π (turn)"),
        ("zero_control_logical0", "logical0 + READ=0 · continuous phase φ/2π (turn)"),
        ("read1_voltage", "logical1 + READ · direct JJ voltage (V)"),
        ("read0_voltage", "logical0 + READ · direct JJ voltage (V)"),
        ("zero_control_logical1_voltage", "logical1 + READ=0 · direct JJ voltage (V)"),
        ("zero_control_logical0_voltage", "logical0 + READ=0 · direct JJ voltage (V)"),
    ]
    row_by_key = {key: index + 1 for index, (key, _) in enumerate(rows)}
    fig = make_subplots(
        rows=len(rows),
        cols=3,
        shared_xaxes=False,
        horizontal_spacing=0.045,
        vertical_spacing=0.024,
        column_titles=[name for name, _, _ in JUNCTIONS],
        row_titles=[title for _, title in rows],
    )
    colors = {"9ps": "#1f5a91", "wstar12": "#d47a21"}
    labels = {"9ps": "Q1 accepted 9 ps", "wstar12": "W*=12 ps"}

    for case_label, _, _, role in CASES:
        for version in ("9ps", "wstar12"):
            data = read_csv(sources[role][version])
            for column_index, (_, phase_signal, voltage_signal) in enumerate(JUNCTIONS, start=1):
                phase_row = row_by_key[role]
                voltage_row = row_by_key[f"{role}_voltage"]
                add_trace(
                    fig, data, phase_signal, phase_row, column_index,
                    f"{case_label} · {labels[version]}", colors[version],
                    legend=(column_index == 1 and phase_row == 1), group=version,
                )
                add_trace(
                    fig, data, voltage_signal, voltage_row, column_index,
                    f"{case_label} · {labels[version]}", colors[version],
                    legend=False, group=version,
                )

    fig.update_xaxes(title_text="time (ps)")
    for row_index in range(1, 5):
        fig.update_yaxes(title_text="turn", row=row_index, col=1)
    for row_index in range(5, 9):
        fig.update_yaxes(title_text="V", row=row_index, col=1)
    fig.update_layout(
        title=(
            "PAPER-SL-Q1 vs W*=12 ps · frozen scaled QB replay<br>"
            "<sup>continuous phase φ/2π (turn); direct voltage; not an SFQ event count</sup>"
        ),
        template="plotly_white",
        width=1500,
        height=2450,
        margin={"l": 190, "r": 30, "t": 100, "b": 60},
        hovermode="x unified",
        legend={"orientation": "h", "y": 1.015, "x": 0.25},
        font={"family": "Arial, sans-serif", "size": 11},
    )
    fig.add_annotation(
        text=(
            "Source: accepted PAPER-SL-Q1 9 ps raw versus this Exploration's W*=12 ps raw. "
            "Raw time grid, polarity and amplitudes are retained; no normalization, rectification, "
            "hold, smoothing or resampling. Formal event classification is in PHASE_C_REPORT.md."
        ),
        xref="paper", yref="paper", x=0, y=-0.025, showarrow=False,
        align="left", font={"size": 10, "color": "#555"},
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(OUT, include_plotlyjs="cdn", full_html=True, auto_open=False)
    metadata = {
        "experiment_id": "bvm-jsl-read-width-to-qb-sfq-v1-20260824",
        "plot_id": "9ps-vs-wstar-qb-replay-comparison",
        "role": "COMPARISON",
        "phase_semantics": ["continuous_absolute"],
        "description": "Accepted 9 ps PAPER-SL-Q1 replay compared with W*=12 ps replay into frozen scaled QB.",
        "cases": [role for _, _, _, role in CASES],
        "source_paths": [
            str(path.relative_to(ROOT.parents[2]))
            for role_sources in sources.values() for path in role_sources.values()
        ],
        "generated_from": "analysis/generate_phase_c_comparison.py; existing raw CSV only",
        "event_claim_boundary": "Visualization is descriptive; formal event claims require continuous phase, same-JJ same-segment voltage area, and post-state analysis in PHASE_C_REPORT.md.",
    }
    META.write_text(json.dumps(metadata, indent=2) + "\n")
    print(OUT)
    print(META)


if __name__ == "__main__":
    main()
