#!/usr/bin/env python3
"""Render the read-count metric summary with a categorical read-count x-axis."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from plotly.subplots import make_subplots
import plotly.graph_objects as go


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    with args.input.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    x = [int(float(row["time"])) for row in rows]
    names = list(rows[0]) if rows else []
    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.12,
        subplot_titles=(
            "JSL8 amplitude",
            "JSL8 area",
            "Receiver phase and terminal area",
        ),
    )
    def values(name: str, factor: float = 1.0) -> list[float]:
        return [float(row[name]) * factor for row in rows]

    fig.add_trace(go.Scatter(x=x, y=values("I(JSL8 peak current) [A]"), mode="lines+markers", name="I(JSL8 peak current) [A]"), row=1, col=1)
    fig.update_yaxes(title_text="Current peak (A)", row=1, col=1)
    fig.add_trace(go.Scatter(x=x, y=values("I(JSL8 signed area) [A*s]"), mode="lines+markers", name="I(JSL8 signed area) [A*s]"), row=2, col=1)
    fig.add_trace(go.Scatter(x=x, y=values("I(JSL8 positive area) [A*s]"), mode="lines+markers", name="I(JSL8 positive area) [A*s]"), row=2, col=1)
    fig.update_yaxes(title_text="Area (A*s)", row=2, col=1)
    fig.add_trace(go.Scatter(x=x, y=values("P(BJ2 net phase displacement) [raw rad; shown turns]", 1 / (2 * 3.141592653589793)), mode="lines+markers", name="P(BJ2 net phase displacement) [raw rad; shown turns]"), row=3, col=1)
    fig.add_trace(go.Scatter(x=x, y=values("P(JTL6 net phase displacement) [raw rad; shown turns]", 1 / (2 * 3.141592653589793)), mode="lines+markers", name="P(JTL6 net phase displacement) [raw rad; shown turns]"), row=3, col=1)
    fig.add_trace(go.Scatter(x=x, y=values("V(terminal area / Phi0) [dimensionless]"), mode="lines+markers", name="V(terminal area / Phi0) [dimensionless]"), row=3, col=1)
    fig.update_yaxes(title_text="Phase (turns) [rad/2pi] / A_TERM/Phi0", row=3, col=1)
    fig.update_xaxes(
        tickmode="array",
        tickvals=[1, 2, 3, 4],
        ticktext=["1", "2", "3", "4"],
        title_text="Number of simultaneously read stored-1 BVMs",
        row=3,
        col=1,
    )
    fig.update_layout(
        title="Read-count summary N=1..4 | descriptive source/receiver metrics",
        template="plotly_dark",
        title_font_size=26,
        hovermode="x unified",
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
