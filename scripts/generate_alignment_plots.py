#!/usr/bin/env python3
"""Generate documentation-only comparison plots from existing CSV artifacts.

This module deliberately has no JoSIM invocation and no scientific decision
logic.  Every series is declared with an exact CSV path and exact column.  The
generated HTML carries machine-readable provenance so the alignment verifier
can distinguish result, control, and source/reference plots.
"""
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


ROOT = Path(__file__).resolve().parents[1]
TWO_PI = 2.0 * 3.141592653589793


def _series(label: str, path: str, column: str, *, role: str = "RESULT",
            phase: bool = False, color: str | None = None) -> dict[str, Any]:
    return {
        "label": label,
        "path": path,
        "column": column,
        "role": role,
        "phase": phase,
        **({"color": color} if color else {}),
    }


def _panel(title: str, series: list[dict[str, Any]], *, unit: str,
           phase_semantics: str | None = None) -> dict[str, Any]:
    return {
        "title": title,
        "series": series,
        "unit": unit,
        "phase_semantics": phase_semantics,
    }


def _q2_case(bias: str, case: str, column: str) -> str:
    return f"test/exploration/paper-sl-q2-20260824/raw/{bias}/{case}.csv"


def _factor_case(experiment: str, raw_subdir: str, case: str) -> str:
    return f"test/exploration/{experiment}/raw/{raw_subdir}/{case}.csv"


def _r13_case(condition: str, case: str) -> str:
    return ("test/exploration/bvm-sfq-receiver-r13a-temporal-conditioning-20260823/"
            f"raw/{condition}/{case}/run-01.csv")


def _q0_case(case: str) -> str:
    return ("test/exploration/qb-q0-standalone-current-quantized-event-20260824/"
            f"raw/scaled/{case}.csv")


def _read_existing_csv(path: Path) -> pd.DataFrame:
    """Read a committed JoSIM CSV, including files with a text preamble."""
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        header = next(
            (
                i
                for i, line in enumerate(handle)
                if line.lstrip().startswith(("time,", "time "))
            ),
            None,
        )
    if header is None:
        raise ValueError(f"no JoSIM CSV header in {path}")
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        header_line = ""
        for index, line in enumerate(handle):
            if index == header:
                header_line = line
                break
    if "," in header_line:
        frame = pd.read_csv(path, skiprows=header)
    else:
        frame = pd.read_csv(path, skiprows=header, sep=r"\s+", engine="python")
    # JoSIM's whitespace formatter preserves quotes around signal names.
    # Normalize only the parsed labels; numerical data are untouched.
    frame.columns = [str(column).strip('"') for column in frame.columns]
    return frame


def specs() -> list[dict[str, Any]]:
    """Return the bounded, named comparisons requested by the alignment task."""
    q1_root = "test/exploration/paper-sl-q1-20260824/raw/"
    q1_cases = {
        "q0 positive control": "test/exploration/qb-q0-standalone-current-quantized-event-20260824/raw/scaled/iin-68p4u.csv",
        "read1": q1_root + "paper-j1-logical1-read.csv",
        "read0": q1_root + "paper-j0-logical0-read.csv",
        "l1_read0": q1_root + "paper-j1-logical1-read0-control.csv",
        "l0_read0": q1_root + "paper-j0-logical0-read0-control.csv",
    }
    q2_cases = {
        "37.5/read1": _q2_case("37p5u", "paper-j1-logical1-read", ""),
        "37.5/read0": _q2_case("37p5u", "paper-j0-logical0-read", ""),
        "40/read1": _q2_case("40u", "paper-j1-logical1-read", ""),
        "40/read0": _q2_case("40u", "paper-j0-logical0-read", ""),
    }
    # _q2_case accepts a stem; the empty fourth argument above is intentionally
    # not used.  Keep the actual paths explicit to make provenance review easy.
    q2_cases = {
        "37.5/read1": "test/exploration/paper-sl-q2-20260824/raw/37p5u/paper-j1-logical1-read.csv",
        "37.5/read0": "test/exploration/paper-sl-q2-20260824/raw/37p5u/paper-j0-logical0-read.csv",
        "40/read1": "test/exploration/paper-sl-q2-20260824/raw/40u/paper-j1-logical1-read.csv",
        "40/read0": "test/exploration/paper-sl-q2-20260824/raw/40u/paper-j0-logical0-read.csv",
    }

    factor = {
        "Q2 (3.91,3.91)": _factor_case("paper-sl-q2-20260824", "40u", "paper-j1-logical1-read"),
        "Q3 (4.50,3.91)": _factor_case("paper-sl-q3-l1-routing-closure-20260824", "l1-4p5", "paper-j1-logical1-read"),
        "Q4 (3.91,4.50)": _factor_case("paper-sl-q4-l1-l2-placement-20260824", "q4-l1-3p91-l2-4p50", "paper-j1-logical1-read"),
        "Q5 (4.50,4.50)": _factor_case("paper-sl-q5-l1-l2-factorial-20260824", "q5-l1-4p50-l2-4p50", "paper-j1-logical1-read"),
    }

    specs: list[dict[str, Any]] = []
    specs.append({
        "id": "paper-sl-q2-bias-comparison",
        "title": "PAPER-SL-Q2 · 37.5 µA versus 40 µA",
        "output": "test/exploration/paper-sl-q2-20260824/plots/bias-37p5-vs-40-comparison.html",
        "experiment_id": "paper-sl-q2-20260824",
        "role": "COMPARISON",
        "cases": list(q2_cases),
        "notes": "冻结 paper-JSL replay 下的 central-bias 对比；图只展示已有 raw。",
        "panels": [
            _panel("BJL1 continuous phase", [
                _series(k, v, "P(BJL1|XBQ)", phase=True) for k, v in q2_cases.items()
            ], unit="连续相位 φ/2π（turn）", phase_semantics="continuous_absolute"),
            _panel("BJL2 continuous phase", [
                _series(k, v, "P(BJL2|XBQ)", phase=True) for k, v in q2_cases.items()
            ], unit="连续相位 φ/2π（turn）", phase_semantics="continuous_absolute"),
            _panel("BJL2 current", [
                _series(k, v, "I(BJL2|XBQ)") for k, v in q2_cases.items()
            ], unit="current (µA)"),
        ],
    })
    specs.append({
        "id": "paper-sl-q1-qb-replay-comparison",
        "title": "PAPER-SL-Q1 · paper-JSL replay into frozen scaled QB",
        "output": "test/exploration/paper-sl-q1-20260824/plots/qb-replay/comparison.html",
        "experiment_id": "paper-sl-q1-20260824",
        "role": "COMPARISON",
        "cases": list(q1_cases),
        "notes": "核心是 frozen QB response；paper-JSL source waveform 另列为 SOURCE_REFERENCE。",
        "panels": [
            _panel("BJs continuous phase", [
                _series(k, v, "P(BJS|XBQ)", phase=True) for k, v in q1_cases.items()
            ], unit="连续相位 φ/2π（turn）", phase_semantics="continuous_absolute"),
            _panel("BJL1 continuous phase", [
                _series(k, v, "P(BJL1|XBQ)", phase=True) for k, v in q1_cases.items()
            ], unit="连续相位 φ/2π（turn）", phase_semantics="continuous_absolute"),
            _panel("BJL2 continuous phase", [
                _series(k, v, "P(BJL2|XBQ)", phase=True) for k, v in q1_cases.items()
            ], unit="连续相位 φ/2π（turn）", phase_semantics="continuous_absolute"),
        ],
    })
    specs.append({
        "id": "paper-sl-q2-q3-q4-q5-factorial",
        "title": "PAPER-SL-Q2/Q3/Q4/Q5 · L1/L2 2×2 factorial comparison",
        "output": "test/exploration/paper-sl-q5-l1-l2-factorial-20260824/plots/q2-q3-q4-q5-factorial-comparison.html",
        "experiment_id": "paper-sl-q5-l1-l2-factorial-20260824",
        "role": "COMPARISON",
        "cases": list(factor),
        "notes": "四个已接受 factorial points；Q2 来自 40 µA reference，Q3/Q4/Q5 为对应 sibling fixtures。",
        "panels": [
            _panel("BJL1 continuous phase", [
                _series(k, v, "P(BJL1|XBQ)", phase=True) for k, v in factor.items()
            ], unit="连续相位 φ/2π（turn）", phase_semantics="continuous_absolute"),
            _panel("BJL2 continuous phase", [
                _series(k, v, "P(BJL2|XBQ)", phase=True) for k, v in factor.items()
            ], unit="连续相位 φ/2π（turn）", phase_semantics="continuous_absolute"),
            _panel("routing currents", [
                _series(k, v, "I(L1|XBQ)") for k, v in factor.items()
            ] + [
                _series(k, v, "I(L2|XBQ)") for k, v in factor.items()
            ], unit="current (µA)"),
        ],
    })

    boundary = {
        "Q0 + 10Ω (accepted)": _q0_case("iin-68p4u"),
        "Q0 OPEN": "test/exploration/qb-load-boundary-matrix-20260824/raw-v2/A-q0-open/scaled-iin-68p4u.csv",
        "Q0 JTL-only": "test/exploration/qb-load-boundary-matrix-20260824/raw-v2/B-q0-jtl-only/scaled-iin-68p4u.csv",
        "Q0 10Ω || JTL": "test/exploration/qb-load-boundary-matrix-20260824/raw-v2/C-q0-10ohm-parallel-jtl/scaled-iin-68p4u.csv",
    }
    specs.append({
        "id": "qb-load-boundary-q0-comparison",
        "title": "QB load boundary · same Q0 source, four output boundaries",
        "output": "test/exploration/qb-load-boundary-matrix-20260824/plots/q0-complete-boundary-comparison.html",
        "experiment_id": "qb-load-boundary-matrix-20260824",
        "role": "COMPARISON",
        "cases": list(boundary),
        "notes": "Q0+10Ω 作为 accepted comparator；Q5 OPEN/JTL 保留为独立 secondary comparison。",
        "panels": [
            _panel("BJL2 continuous phase", [
                _series(k, v, "P(BJL2|XBQ)", phase=True) for k, v in boundary.items()
            ], unit="连续相位 φ/2π（turn）", phase_semantics="continuous_absolute"),
            _panel("QB output voltage", [
                _series(k, v, "V(OUT)") for k, v in boundary.items()
            ], unit="voltage (µV)"),
        ],
    })

    r13_conditions = {
        "raw replay": "raw-replay",
        "C1 rectify": "c1-rectify",
        "C2 hold20": "c2-hold20",
        "C3 rectify+hold20": "c3-rectify-hold20",
    }
    for label, condition in r13_conditions.items():
        cases = {
            "read1": _r13_case(condition, "read1"),
            "read0": _r13_case(condition, "read0"),
            "logical1 READ=0": _r13_case(condition, "logical1-read0-control"),
            "logical0 READ=0": _r13_case(condition, "logical0-read0-control"),
        }
        specs.append({
            "id": f"r13-{condition}-comparison",
            "title": f"R13-A · {label}",
            "output": f"test/exploration/bvm-sfq-receiver-r13a-temporal-conditioning-20260823/plots/{condition}/comparison.html",
            "experiment_id": "bvm-sfq-receiver-r13a-temporal-conditioning-20260823",
            "role": "COMPARISON",
            "cases": [f"{condition}/{k}" for k in cases],
            "notes": "理想 waveform transformation 的 bounded replay；不等同于 physical conditioner。",
            "panels": [
                _panel("B3 continuous phase", [
                    _series(k, v, "P(B3|XREPLAY)", phase=True) for k, v in cases.items()
                ], unit="连续相位 φ/2π（turn）", phase_semantics="continuous_absolute"),
                _panel("B3 voltage", [
                    _series(k, v, "V(B3|XREPLAY)") for k, v in cases.items()
                ], unit="voltage (µV)"),
            ],
        })
    aggregate_cases = {
        label: _r13_case(condition, "read1") for label, condition in r13_conditions.items()
    }
    specs.append({
        "id": "r13-raw-vs-c1-vs-c2-vs-c3",
        "title": "R13-A · raw / C1 / C2 / C3 read1 comparison",
        "output": "test/exploration/bvm-sfq-receiver-r13a-temporal-conditioning-20260823/plots/raw-vs-c1-vs-c2-vs-c3.html",
        "experiment_id": "bvm-sfq-receiver-r13a-temporal-conditioning-20260823",
        "role": "COMPARISON",
        "cases": list(aggregate_cases),
        "notes": "四种 bounded input transformation 的 read1 对照。",
        "panels": [
            _panel("B3 continuous phase", [
                _series(k, v, "P(B3|XREPLAY)", phase=True) for k, v in aggregate_cases.items()
            ], unit="连续相位 φ/2π（turn）", phase_semantics="continuous_absolute"),
            _panel("B3 voltage", [
                _series(k, v, "V(B3|XREPLAY)") for k, v in aggregate_cases.items()
            ], unit="voltage (µV)"),
        ],
    })

    q5 = "test/exploration/paper-sl-q5-l1-l2-factorial-20260824/raw/q5-l1-4p50-l2-4p50/paper-j1-logical1-read.csv"
    q6 = "test/exploration/paper-sl-q6-qb-jtl-compatibility-20260824/raw/q6-q5-to-two-cell-jtl/paper-j1-logical1-read.csv"
    specs.append({
        "id": "paper-sl-q6-q5-standalone-vs-coupled",
        "title": "PAPER-SL-Q6 · Q5 standalone versus QB→JTL coupled",
        "output": "test/exploration/paper-sl-q6-qb-jtl-compatibility-20260824/plots/q5-standalone-vs-q6-coupled.html",
        "experiment_id": "paper-sl-q6-qb-jtl-compatibility-20260824",
        "role": "COMPARISON",
        "cases": ["Q5 standalone", "Q6 coupled"],
        "notes": "Q5 standalone raw 来自 accepted Q5 fixture；Q6 为同一源与 two-cell JTL 的耦合结果。",
        "panels": [
            _panel("BJL1 continuous phase", [
                _series("Q5 standalone", q5, "P(BJL1|XBQ)", phase=True),
                _series("Q6 coupled", q6, "P(BJL1|XBQ)", phase=True),
            ], unit="连续相位 φ/2π（turn）", phase_semantics="continuous_absolute"),
            _panel("BJL2 continuous phase", [
                _series("Q5 standalone", q5, "P(BJL2|XBQ)", phase=True),
                _series("Q6 coupled", q6, "P(BJL2|XBQ)", phase=True),
            ], unit="连续相位 φ/2π（turn）", phase_semantics="continuous_absolute"),
            _panel("QB output voltage", [
                _series("Q5 standalone", q5, "V(OUT)"),
                _series("Q6 coupled", q6, "V(OUT)"),
            ], unit="voltage (µV)"),
        ],
    })
    return specs


def render(spec: dict[str, Any]) -> None:
    fig = make_subplots(
        rows=len(spec["panels"]), cols=1, shared_xaxes=True,
        vertical_spacing=min(0.06, 0.20 / max(len(spec["panels"]), 1)),
        subplot_titles=[p["title"] for p in spec["panels"]],
    )
    semantics: set[str] = set()
    source_paths: list[str] = []
    for row, panel in enumerate(spec["panels"], 1):
        for series in panel["series"]:
            path = ROOT / series["path"]
            if not path.exists():
                raise FileNotFoundError(path)
            df = _read_existing_csv(path)
            if series["column"] not in df.columns:
                raise KeyError(f"{series['column']} not found in {path}")
            x = df["time"] * 1e12
            y = df[series["column"]]
            if series.get("phase"):
                y = y / TWO_PI
                semantics.add(panel["phase_semantics"] or "UNDECLARED")
            if panel["unit"] == "voltage (µV)":
                y = y * 1e6
            elif panel["unit"] == "current (µA)":
                y = y * 1e6
            line = {"width": 1.4}
            if series.get("color"):
                line["color"] = series["color"]
            fig.add_trace(go.Scatter(
                x=x, y=y, mode="lines", name=series["label"],
                legendgroup=series["label"], line=line,
                hovertemplate=f"{series['label']}<br>%{{x:.4g}} ps<br>%{{y:.6g}}<extra></extra>",
            ), row=row, col=1)
            source_paths.append(series["path"])
        fig.update_yaxes(title_text=panel["unit"], row=row, col=1)
    fig.update_xaxes(title_text="time (ps)", row=len(spec["panels"]), col=1)
    fig.update_layout(
        title=spec["title"], template="plotly_white", hovermode="x unified",
        height=max(620, 290 * len(spec["panels"])),
        legend=dict(orientation="h", y=-0.08), margin=dict(l=90, r=30, t=100, b=120),
    )
    output = ROOT / spec["output"]
    output.parent.mkdir(parents=True, exist_ok=True)
    fragment = fig.to_html(include_plotlyjs="cdn", full_html=False, config={"displaylogo": False})
    note = (
        "<section class='provenance' style='font:14px sans-serif; padding:12px; "
        "border:1px solid #ccd; background:#f7f9fc'>"
        f"<b>Plot role:</b> {html.escape(spec['role'])} &nbsp; "
        f"<b>Experiment:</b> {html.escape(spec['experiment_id'])}<br>"
        f"{html.escape(spec['notes'])}<br>"
        "连续相位 φ/2π（turn）为原始 JoSIM P(...) 连续轨迹；未做基线相减、未按脉冲归零；不等于 SFQ 计数。"
        "</section>"
    )
    meta = {
        "experiment_id": spec["experiment_id"],
        "plot_id": spec["id"],
        "role": spec["role"],
        "cases": spec["cases"],
        "phase_semantics": sorted(semantics) if semantics else [],
        "source_paths": sorted(set(source_paths)),
        "generated_from": "scripts/generate_alignment_plots.py; existing raw CSV only",
    }
    head = (
        "<!doctype html><html lang='zh-CN'><head><meta charset='utf-8'>"
        f"<meta name='experiment-id' content='{html.escape(spec['experiment_id'])}'>"
        f"<meta name='plot-id' content='{html.escape(spec['id'])}'>"
        f"<meta name='plot-role' content='{html.escape(spec['role'])}'>"
        f"<meta name='phase-semantics' content='{html.escape(','.join(sorted(semantics)))}'>"
        f"<script type='application/json' id='alignment-metadata'>{json.dumps(meta, ensure_ascii=False)}</script>"
        f"<title>{html.escape(spec['title'])}</title></head><body>{note}{fragment}</body></html>"
    )
    output.write_text(head, encoding="utf-8")
    output.with_suffix(".metadata.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"generated {output}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", action="append", help="render only this spec id; repeatable")
    args = ap.parse_args()
    wanted = set(args.id or [])
    for spec in specs():
        if wanted and spec["id"] not in wanted:
            continue
        render(spec)


if __name__ == "__main__":
    main()
