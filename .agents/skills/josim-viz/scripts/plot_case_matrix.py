#!/usr/bin/env python3
"""Render a declared multi-case CSV matrix as a standalone Plotly HTML."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest", type=Path)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    spec = json.loads(args.manifest.read_text(encoding="utf-8"))
    panels = spec["panels"]
    fig = make_subplots(
        rows=len(panels), cols=1, shared_xaxes=True,
        vertical_spacing=min(0.08, 0.22 / max(len(panels), 1)),
        subplot_titles=[p["title"] for p in panels],
    )
    for row, panel in enumerate(panels, 1):
        for series in panel["series"]:
            csv_path = (args.manifest.parent / series["csv"]).resolve()
            df = pd.read_csv(csv_path)
            column = series.get("column", panel.get("column"))
            if not column:
                raise SystemExit(f"series {series.get('label', '<unnamed>')} has no CSV column")
            if column not in df.columns:
                raise SystemExit(f"missing column {column!r} in {csv_path}")
            x = df.iloc[:, 0] * float(panel.get("x_scale", 1.0))
            y = df[column]
            if panel.get("phase_turns"):
                y = y / (2.0 * 3.141592653589793)
            if panel.get("y_scale", 1.0) != 1.0:
                y = y * float(panel["y_scale"])
            fig.add_trace(go.Scatter(
                x=x, y=y, mode="lines", name=series["label"],
                legendgroup=series.get("group", series["label"]),
                line=series.get("line", {}),
                hovertemplate=f"{series['label']}<br>%{{x:.3g}}<br>%{{y:.6g}}<extra></extra>",
            ), row=row, col=1)
        fig.update_yaxes(title_text=panel.get("y_label", ""), row=row, col=1)
    fig.update_xaxes(title_text=spec.get("x_label", "time"), row=len(panels), col=1)
    fig.update_layout(
        title=spec.get("title", "Exploration case matrix"), template="plotly_dark",
        height=max(520, 280 * len(panels)), hovermode="x unified",
        legend=dict(orientation="h", y=-0.08), margin=dict(l=76, r=28, t=80, b=100),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(args.output, include_plotlyjs="cdn", config={"displaylogo": False})


if __name__ == "__main__":
    main()
