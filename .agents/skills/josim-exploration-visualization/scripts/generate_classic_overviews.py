#!/usr/bin/env python3
"""Generate descriptive overview plots for Explorations lacking HTML plots.

This is a result-documentation helper only.  It reads existing raw CSV files,
uses exact headers, normalizes phase by 2π for display, and never counts an
event or reruns JoSIM.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


PHASE_PRIORITY = ["B_OUT", "B_TRIG", "BJL2", "BJL1", "BJs", "B3", "B2", "B1", "JTL"]
VOLTAGE_PRIORITY = ["B_OUT", "B_TRIG", "N_SEC", "OUT", "SL", "N6", "BJL2", "BJL1", "BJs"]
CURRENT_PRIORITY = ["L_SL", "L1", "L2", "L0", "L_SEC", "B_OUT", "BJL2", "BJL1", "BJs", "IN"]


def score_signal(column: str, priority: list[str]) -> tuple[int, str]:
    value = column.lower()
    for index, token in enumerate(priority):
        if token.lower() in value:
            return (len(priority) - index, column)
    return (0, column)


def case_label(path: Path, root: Path) -> str:
    rel = path.relative_to(root).as_posix()
    return rel.removesuffix("/run-01.csv").removesuffix(".csv")


def choose_cases(raw_root: Path) -> list[Path]:
    return [
        p for p in sorted(raw_root.rglob("*.csv"))
        if "/reference/" not in p.as_posix()
    ]


def collect_columns(cases: list[Path]) -> tuple[list[str], list[str], list[str]]:
    headers = {}
    for path in cases:
        df = pd.read_csv(path, nrows=1)
        headers[path] = list(df.columns)
    all_columns = sorted({c for values in headers.values() for c in values})
    phases = [c for c in all_columns if c.startswith("P(")]
    voltages = [c for c in all_columns if c.startswith("V(")]
    currents = [c for c in all_columns if c.startswith("I(")]
    phases = sorted(phases, key=lambda c: (-score_signal(c, PHASE_PRIORITY)[0], c))[:4]
    voltages = sorted(voltages, key=lambda c: (-score_signal(c, VOLTAGE_PRIORITY)[0], c))[:2]
    currents = sorted(currents, key=lambda c: (-score_signal(c, CURRENT_PRIORITY)[0], c))[:4]
    return phases, voltages, currents


def panel(fig, row: int, title: str, column: str, cases: list[Path], raw_root: Path,
          kind: str) -> None:
    for path in cases:
        if column not in pd.read_csv(path, nrows=0).columns:
            continue
        df = pd.read_csv(path, usecols=[df_col for df_col in ["time", column]])
        y = df[column]
        y_label = "raw"
        if kind == "phase":
            y = y / (2.0 * 3.141592653589793)
            y_label = "turns (rad / 2π)"
        elif kind == "voltage":
            y = y * 1e6
            y_label = "µV"
        elif kind == "current":
            y = y * 1e6
            y_label = "µA"
        fig.add_trace(
            go.Scatter(
                x=df["time"] * 1e12,
                y=y,
                mode="lines",
                name=case_label(path, raw_root),
                legendgroup=case_label(path, raw_root),
                line={"width": 1.15},
                hovertemplate=f"{case_label(path, raw_root)}<br>%{{x:.4g}} ps<br>%{{y:.6g}} {y_label}<extra></extra>",
            ),
            row=row,
            col=1,
        )
    fig.update_yaxes(title_text=f"{column}<br>{y_label}", row=row, col=1)
    fig.update_xaxes(title_text="time (ps)", row=row, col=1)


def generate(exploration: Path) -> bool:
    raw_root = exploration / "raw"
    plots = exploration / "plots"
    if not raw_root.exists():
        return False
    if plots.exists() and list(plots.rglob("*.html")):
        return False
    cases = choose_cases(raw_root)
    if not cases:
        return False
    phases, voltages, currents = collect_columns(cases)
    panels = [("phase", c) for c in phases] + [("voltage", c) for c in voltages] + [("current", c) for c in currents]
    if not panels:
        return False
    fig = make_subplots(
        rows=len(panels), cols=1, shared_xaxes=False,
        vertical_spacing=min(0.04, 0.18 / max(len(panels), 1)),
        subplot_titles=[f"{kind}: {column}" for kind, column in panels],
    )
    for row, (kind, column) in enumerate(panels, 1):
        panel(fig, row, f"{kind}: {column}", column, cases, raw_root, kind)
    fig.update_layout(
        title=f"{exploration.name} — raw-case overview",
        template="plotly_dark",
        height=max(650, 260 * len(panels)),
        hovermode="x",
        legend=dict(orientation="h", y=-0.03),
        margin=dict(l=100, r=30, t=90, b=130),
    )
    plots.mkdir(parents=True, exist_ok=True)
    output = plots / "overview.html"
    fig.write_html(output, include_plotlyjs="cdn", config={"displaylogo": False})
    lines = [
        f"# {exploration.name} overview",
        "",
        "此图由既有 raw CSV 生成，仅用于跨 case 阅读；没有重新运行 JoSIM，也不从图中判定 event/Gate。",
        "",
        "## cases",
        "",
        *[f"- `{case_label(p, raw_root)}`" for p in cases],
        "",
        "## exact displayed columns",
        "",
        *[f"- phase: `{c}` → rad/2π turns" for c in phases],
        *[f"- voltage: `{c}` → µV" for c in voltages],
        *[f"- current: `{c}` → µA" for c in currents],
        "",
        "正式 phase/area、event 和 scientific verdict 仍以对应 analysis/report 为准。",
    ]
    (plots / "overview-README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{exploration.name}: {len(cases)} cases, {len(panels)} panels -> {output}")
    return True


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path("test/exploration"))
    args = ap.parse_args()
    count = 0
    for exploration in sorted(p for p in args.root.iterdir() if p.is_dir()):
        count += int(generate(exploration))
    print(f"generated={count}")


if __name__ == "__main__":
    main()
