#!/usr/bin/env python3
"""Regenerate the physical BVM->12xJSL->QB visualization package.

This is a documentation-only renderer.  It never invokes JoSIM and never
changes raw CSVs, decks, analysis JSON, or scientific verdicts.  The plot
specifications below deliberately use exact CSV column names and the
registered physical-case paths.  Phase is displayed as the continuous raw
JoSIM P(...) trajectory divided by 2*pi; it is not an SFQ counter.

The renderer is kept separate from the generic alignment builder because this
exploration needs a richer source->JSL->QB current audit than the historical
three-panel plots.  It follows the josim-exploration-visualization and
josim-viz conventions: explicit provenance, declared phase semantics,
time in ps, voltage in uV, current in uA, and no event claim from a peak.
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
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
EXP = "test/exploration/physical-bvm-jsl12-qb-sfq-closure-v1-20260824"
EXP_ROOT = ROOT / EXP
TWO_PI = 2.0 * 3.141592653589793
ACTIVE = (94.0, 130.0)
POST = (140.0, 170.0)

ROLE_LABELS = {
    "logical1_read": "logical1 + canonical READ",
    "logical0_read": "logical0 + canonical READ",
    "logical1_no_read_control": "logical1 + READ=0 control",
    "logical0_no_read_control": "logical0 + READ=0 control",
}

ROLE_COLORS = {
    "logical1_read": "#b23a48",
    "logical0_read": "#3973ac",
    "logical1_no_read_control": "#d18b35",
    "logical0_no_read_control": "#687786",
}

ROLE_DASH = {
    "logical1_read": "solid",
    "logical0_read": "solid",
    "logical1_no_read_control": "dash",
    "logical0_no_read_control": "dash",
}


def case_path(width: int, role: str) -> str:
    return f"{EXP}/raw/{width}/{role}/run-01.csv"


def ideal_path(width: int, role: str) -> str:
    return (
        "test/exploration/bvm-read-semantics-audit-and-jsl-width-bracket-v1-20260824/"
        f"raw/replay/{width}ps/{role}/run-01.csv"
    )


def source_path(width: int, role: str) -> str:
    return (
        "test/exploration/bvm-read-semantics-audit-and-jsl-width-bracket-v1-20260824/"
        f"raw/{width}ps/{role.replace('_', '-')}/run-01.csv"
    )


def load_csv(path: Path) -> pd.DataFrame:
    """Read an existing JoSIM CSV and normalize only column quoting."""
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        header = next(
            (i for i, line in enumerate(handle)
             if line.lstrip().startswith(("time,", "time "))),
            None,
        )
    if header is None:
        raise ValueError(f"no JoSIM CSV header in {path}")
    frame = pd.read_csv(path, skiprows=header)
    frame.columns = [str(column).strip('"') for column in frame.columns]
    return frame


_CACHE: dict[str, pd.DataFrame] = {}


def frame(path: str) -> pd.DataFrame:
    if path not in _CACHE:
        full = ROOT / path
        if not full.exists():
            raise FileNotFoundError(full)
        _CACHE[path] = load_csv(full)
    return _CACHE[path]


def phase_column(prefix: str) -> str:
    if prefix in {"BJs", "BJL1", "BJL2"}:
        # JoSIM's Q0 deck uses the canonical uppercase BJS header, while the
        # human-facing label remains BJs to match the paper notation.
        csv_prefix = "BJS" if prefix == "BJs" else prefix
        return f"P({csv_prefix}|XBQ)"
    return f"P({prefix})"


def source_series(label: str, path: str, column: str, kind: str = "value",
                  *, role: str | None = None, color: str | None = None,
                  dash: str | None = None) -> dict[str, Any]:
    return {
        "label": label,
        "path": path,
        "column": column,
        "kind": kind,
        "role": role,
        "color": color,
        "dash": dash,
    }


def physical_series(width: int, role: str, column: str, kind: str = "value",
                    *, label: str | None = None) -> dict[str, Any]:
    return source_series(
        label or f"{width} ps · {ROLE_LABELS[role]}",
        case_path(width, role), column, kind,
        role=role, color=ROLE_COLORS[role], dash=ROLE_DASH[role],
    )


def _panel(title: str, series: list[dict[str, Any]], unit: str,
           phase_semantics: str | None = None, *, window: bool = True) -> dict[str, Any]:
    return {
        "title": title,
        "series": series,
        "unit": unit,
        "phase_semantics": phase_semantics,
        "window": window,
    }


def all_cases(width: int) -> list[tuple[int, str]]:
    return [(width, role) for role in ROLE_LABELS]


def phase_panel(width: int, prefix: str, *, roles: list[str] | None = None,
                label_prefix: str | None = None) -> dict[str, Any]:
    roles = roles or list(ROLE_LABELS)
    return _panel(
        f"{prefix} continuous phase",
        [physical_series(width, role, phase_column(prefix), "phase",
                         label=(f"{label_prefix} · " if label_prefix else "") + ROLE_LABELS[role])
         for role in roles],
        "连续相位 φ/2π（turn）",
        "continuous_absolute",
    )


def value_panel(width: int, title: str, column: str, unit: str,
                *, roles: list[str] | None = None) -> dict[str, Any]:
    roles = roles or list(ROLE_LABELS)
    return _panel(
        title,
        [physical_series(width, role, column, "value") for role in roles],
        unit,
    )


def metrics_note(width: int) -> str:
    metrics_path = EXP_ROOT / "analysis" / f"physical-{width}ps-metrics.json"
    data = json.loads(metrics_path.read_text(encoding="utf-8"))
    rows = []
    for role, record in data["cases"].items():
        bjl2 = record["qb"]["BJL2"]
        segment = bjl2.get("largest_segment") or {}
        rows.append(
            "<tr>"
            f"<td>{html.escape(ROLE_LABELS.get(role, role))}</td>"
            f"<td>{bjl2.get('phase_activity_p2p_turns', 0):.6g}</td>"
            f"<td>{segment.get('delta_turns', 0.0):.6g}</td>"
            f"<td>{segment.get('area_phi0', 0.0):.6g}</td>"
            f"<td>{html.escape(record.get('bjl2_classification', ''))}</td>"
            "</tr>"
        )
    return (
        "<section class='evidence-table'><h3>正式分析锚点（非由图单独判定）</h3>"
        "<p>事件判据来自同一 JJ、同一 monotonic segment 的连续相位与直接电压面积；"
        "phase activity 或电压峰值本身不等于 event。</p>"
        "<table><thead><tr><th>工况</th><th>BJL2 activity p2p (turn)</th>"
        "<th>最大 monotonic Δφ/2π</th><th>同段面积 (Φ0)</th><th>formal classification</th>"
        f"</tr></thead><tbody>{''.join(rows)}</tbody></table></section>"
    )


def specs() -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []

    # One readable page per real required case.  This prevents the four
    # matched cases from disappearing behind a comparison-only plot.
    for width in (13, 14):
        for role in ROLE_LABELS:
            specs.append({
                "id": f"physical-{width}ps-{role}-case",
                "title": f"Physical BVM→12×JSL→scaled QB · {width} ps · {ROLE_LABELS[role]}",
                "output": f"{EXP}/plots/cases/{width}ps-{role}.html",
                "role": "ZERO_CONTROL" if "no_read_control" in role else ("NEGATIVE_CONTROL" if role == "logical0_read" else "RESULT"),
                "cases": [f"{width}/{role}"],
                "notes": "单工况 evidence view；输入、BVM source/readout、12×JSL、QB 三颗 JJ 和主要 routing current 同页展示。",
                "panels": [
                    _panel("SL readout current", [physical_series(width, role, "I(L_SL|XBVM1)")], "current (µA)"),
                    _panel("SL and N6 voltage", [
                        physical_series(width, role, "V(SL1)"),
                        physical_series(width, role, "V(N6|XBVM1)"),
                    ], "voltage (µV)"),
                    _panel("BVM storage/read continuous phase", [
                        physical_series(width, role, "P(B_JM1|XBVM1)", "phase", label="JM1"),
                        physical_series(width, role, "P(B_JM2|XBVM1)", "phase", label="JM2"),
                        physical_series(width, role, "P(B_JS1|XBVM1)", "phase", label="JS1"),
                        physical_series(width, role, "P(B_JS2|XBVM1)", "phase", label="JS2"),
                    ], "连续相位 φ/2π（turn）", "continuous_absolute"),
                    _panel("12×JSL series current (first / middle / last)", [
                        physical_series(width, role, "I(B_LD1)"),
                        physical_series(width, role, "I(B_LD6)"),
                        physical_series(width, role, "I(B_LD12)"),
                    ], "current (µA)"),
                    _panel("QB phase ladder", [
                        physical_series(width, role, phase_column(prefix), "phase", label=prefix)
                        for prefix in ("BJs", "BJL1", "BJL2")
                    ], "连续相位 φ/2π（turn）", "continuous_absolute"),
                    _panel("QB routing currents", [
                        physical_series(width, role, column)
                        for column in ("I(BJS|XBQ)", "I(L1|XBQ)", "I(BJL1|XBQ)", "I(L2|XBQ)", "I(BJL2|XBQ)", "I(L0|XBQ)", "I(RB|XBQ)", "I(RJ1|XBQ)", "I(RJ2|XBQ)")
                    ], "current (µA)"),
                    _panel("BJL2 direct voltage and output", [
                        physical_series(width, role, "V(BJL2|XBQ)"),
                        physical_series(width, role, "V(OUT)"),
                    ], "voltage (µV)"),
                ],
                "metrics_width": width,
            })

        roles = list(ROLE_LABELS)
        specs.append({
            "id": f"physical-{width}ps-matched-cases",
            "title": f"Physical BVM→12×JSL→scaled QB · {width} ps · four matched cases",
            "output": f"{EXP}/plots/{width}ps-matched-cases.html",
            "role": "COMPARISON",
            "cases": [f"{width}/{role}" for role in roles],
            "notes": "同一 width 的 logical1/read1、logical0/read、两个 READ=0 controls；颜色表示 case role，虚线表示 control。",
            "panels": [
                value_panel(width, "SL readout current", "I(L_SL|XBVM1)", "current (µA)"),
                value_panel(width, "SL voltage", "V(SL1)", "voltage (µV)"),
                value_panel(width, "N6 voltage", "V(N6|XBVM1)", "voltage (µV)"),
                phase_panel(width, "BJs"),
                phase_panel(width, "BJL1"),
                phase_panel(width, "BJL2"),
                _panel("QB routing current partition", [
                    physical_series(width, role, column)
                    for column in ("I(L1|XBQ)", "I(L2|XBQ)", "I(L0|XBQ)", "I(BJL2|XBQ)")
                    for role in roles
                ], "current (µA)"),
                value_panel(width, "BJL2 direct voltage", "V(BJL2|XBQ)", "voltage (µV)"),
            ],
            "metrics_width": width,
        })

    # Cross-width view: the physical 13/14 ps result, all controls included.
    cross_cases = [(width, role) for width in (13, 14) for role in ROLE_LABELS]
    specs.append({
        "id": "physical-width-comparison",
        "title": "Physical BVM→12×JSL→scaled QB · 13 ps versus 14 ps",
        "output": f"{EXP}/plots/physical-width-comparison.html",
        "role": "COMPARISON",
        "cases": [f"{width}/{role}" for width, role in cross_cases],
        "notes": "跨 width 对照，保留 read1/read0/control 角色；13/14 ps 都没有 physical BJL2 complete event。",
        "panels": [
            _panel("SL readout current", [physical_series(w, r, "I(L_SL|XBVM1)", label=f"{w} ps · {ROLE_LABELS[r]}") for w, r in cross_cases], "current (µA)"),
            _panel("BJs continuous phase", [physical_series(w, r, phase_column("BJs"), "phase", label=f"{w} ps · {ROLE_LABELS[r]}") for w, r in cross_cases], "连续相位 φ/2π（turn）", "continuous_absolute"),
            _panel("BJL1 continuous phase", [physical_series(w, r, "P(BJL1|XBQ)", "phase", label=f"{w} ps · {ROLE_LABELS[r]}") for w, r in cross_cases], "连续相位 φ/2π（turn）", "continuous_absolute"),
            _panel("BJL2 continuous phase", [physical_series(w, r, "P(BJL2|XBQ)", "phase", label=f"{w} ps · {ROLE_LABELS[r]}") for w, r in cross_cases], "连续相位 φ/2π（turn）", "continuous_absolute"),
            _panel("BJL2 current", [physical_series(w, r, "I(BJL2|XBQ)", label=f"{w} ps · {ROLE_LABELS[r]}") for w, r in cross_cases], "current (µA)"),
        ],
    })

    # Source/storage guard is deliberately a separate result view so the
    # SL current cannot be missed in a QB-only plot.
    specs.append({
        "id": "physical-source-and-storage-guards",
        "title": "Physical BVM→12×JSL→scaled QB · SL current and BVM source/storage guards",
        "output": f"{EXP}/plots/physical-source-and-storage-guards.html",
        "role": "COMPARISON",
        "cases": [f"{w}/{r}" for w, r in cross_cases],
        "notes": "source/readout guard view；SL branch current 是直接结果信号，不是由 V(SL) 外观推断。JM/JS phase 仅作 source/storage guard 观察。",
        "panels": [
            _panel("SL readout current I(L_SL)", [physical_series(w, r, "I(L_SL|XBVM1)", label=f"{w} ps · {ROLE_LABELS[r]}") for w, r in cross_cases], "current (µA)"),
            _panel("SL voltage V(SL1)", [physical_series(w, r, "V(SL1)", label=f"{w} ps · {ROLE_LABELS[r]}") for w, r in cross_cases], "voltage (µV)"),
            _panel("N6 voltage", [physical_series(w, r, "V(N6|XBVM1)", label=f"{w} ps · {ROLE_LABELS[r]}") for w, r in cross_cases], "voltage (µV)"),
            _panel("JM1 / JM2 continuous phase", [
                physical_series(w, r, column, "phase", label=f"{w} ps · {ROLE_LABELS[r]} · {name}")
                for name, column in (("JM1", "P(B_JM1|XBVM1)"), ("JM2", "P(B_JM2|XBVM1)"))
                for w, r in cross_cases
            ], "连续相位 φ/2π（turn）", "continuous_absolute"),
            _panel("JS1 / JS2 continuous phase", [
                physical_series(w, r, column, "phase", label=f"{w} ps · {ROLE_LABELS[r]} · {name}")
                for name, column in (("JS1", "P(B_JS1|XBVM1)"), ("JS2", "P(B_JS2|XBVM1)"))
                for w, r in cross_cases
            ], "连续相位 φ/2π（turn）", "continuous_absolute"),
        ],
    })

    # Every JSL current is shown explicitly for the read cases.  The per-case
    # pages show first/middle/last; this page shows all 12 traces.
    jsl_cases = [(width, role) for width in (13, 14) for role in ROLE_LABELS]
    jsl_panels = [
        _panel(
            f"{width} ps · {ROLE_LABELS[role]} · all 12 JSL currents",
            [physical_series(width, role, f"I(B_LD{idx})", label=f"JSL{idx}") for idx in range(1, 13)],
            "current (µA)",
        )
        for width, role in jsl_cases
    ]
    specs.append({
        "id": "physical-jsl12-current-consistency",
        "title": "Physical BVM→12×JSL→scaled QB · all 12 JSL currents",
        "output": f"{EXP}/plots/physical-jsl12-current-consistency.html",
        "role": "RESULT",
        "cases": [f"{w}/{r}" for w, r in jsl_cases],
        "notes": "所有 12 个 JSL current 直接叠图；series consistency 的数值上限仍以正式 analysis JSON/REPORT 为准。",
        "panels": [
            *jsl_panels,
            _panel("First / middle / last JSL current", [
                physical_series(w, r, column, label=f"{w} ps · {ROLE_LABELS[r]} · {name}")
                for w, r in jsl_cases
                for name, column in (("JSL1", "I(B_LD1)"), ("JSL6", "I(B_LD6)"), ("JSL12", "I(B_LD12)"))
            ], "current (µA)"),
        ],
    })

    # KCL/current-partition view: each row is a node equation from the formal
    # analysis, not an invented scalar impedance approximation.
    kcl_cases = [(13, "logical1_read"), (13, "logical0_read"), (14, "logical1_read"), (14, "logical0_read")]
    specs.append({
        "id": "physical-qb-routing-and-kcl",
        "title": "Physical BVM→12×JSL→scaled QB · QB routing currents and node KCL",
        "output": f"{EXP}/plots/physical-qb-routing-and-kcl.html",
        "role": "COMPARISON",
        "cases": [f"{w}/{r}" for w, r in kcl_cases],
        "notes": "node2/node3/node4 的 current partition；三组 KCL residual 数值见 formal analysis，图只展示真实支路波形。",
        "panels": [
            _panel("Node2: I(BJs), I(L1), I(BJL1), I(RJ1)", [
                physical_series(w, r, column, label=f"{w} ps · {ROLE_LABELS[r]} · {name}")
                for w, r in kcl_cases
                for name, column in (("BJs", "I(BJS|XBQ)"), ("L1", "I(L1|XBQ)"), ("BJL1", "I(BJL1|XBQ)"), ("RJ1", "I(RJ1|XBQ)"))
            ], "current (µA)"),
            _panel("Node3: I(L1), I(RB), I(L2)", [
                physical_series(w, r, column, label=f"{w} ps · {ROLE_LABELS[r]} · {name}")
                for w, r in kcl_cases
                for name, column in (("L1", "I(L1|XBQ)"), ("RB", "I(RB|XBQ)"), ("L2", "I(L2|XBQ)"))
            ], "current (µA)"),
            _panel("Node4: I(L2), I(L0), I(BJL2), I(RJ2)", [
                physical_series(w, r, column, label=f"{w} ps · {ROLE_LABELS[r]} · {name}")
                for w, r in kcl_cases
                for name, column in (("L2", "I(L2|XBQ)"), ("L0", "I(L0|XBQ)"), ("BJL2", "I(BJL2|XBQ)"), ("RJ2", "I(RJ2|XBQ)"))
            ], "current (µA)"),
        ],
    })

    # Keep the old index paths, but replace their sparse contents with the
    # richer evidence views so existing bookmarks no longer hide the current.
    for width in (13, 14):
        physical = {role: case_path(width, role) for role in ROLE_LABELS}
        ideal = {role: ideal_path(width, role) for role in ROLE_LABELS}
        specs.append({
            "id": f"physical-bvm-jsl12-qb-{width}ps-ideal-vs-physical",
            "title": f"Physical BVM→12×JSL→scaled QB · {width} ps ideal replay versus physical cascade",
            "output": f"{EXP}/plots/{width}ps-ideal-vs-physical-qb.html",
            "role": "COMPARISON",
            "cases": [f"{width}/{r}" for r in ROLE_LABELS],
            "notes": "physical raw 是本实验 primary；ideal replay 是 source-isolated reference，不能替代 physical cascade。",
            "panels": [
                _panel("BJs phase: ideal versus physical", [
                    source_series(f"{ROLE_LABELS[r]} · physical", physical[r], phase_column("BJs"), "phase", role=r, color=ROLE_COLORS[r], dash="solid") for r in ROLE_LABELS
                ] + [
                    source_series(f"{ROLE_LABELS[r]} · ideal", ideal[r], phase_column("BJs"), "phase", role=r, color=ROLE_COLORS[r], dash="dot") for r in ROLE_LABELS
                ], "连续相位 φ/2π（turn）", "continuous_absolute"),
                _panel("BJL1 phase: ideal versus physical", [
                    source_series(f"{ROLE_LABELS[r]} · physical", physical[r], "P(BJL1|XBQ)", "phase", role=r, color=ROLE_COLORS[r], dash="solid") for r in ROLE_LABELS
                ] + [
                    source_series(f"{ROLE_LABELS[r]} · ideal", ideal[r], "P(BJL1|XBQ)", "phase", role=r, color=ROLE_COLORS[r], dash="dot") for r in ROLE_LABELS
                ], "连续相位 φ/2π（turn）", "continuous_absolute"),
                _panel("BJL2 phase: ideal versus physical", [
                    source_series(f"{ROLE_LABELS[r]} · physical", physical[r], "P(BJL2|XBQ)", "phase", role=r, color=ROLE_COLORS[r], dash="solid") for r in ROLE_LABELS
                ] + [
                    source_series(f"{ROLE_LABELS[r]} · ideal", ideal[r], "P(BJL2|XBQ)", "phase", role=r, color=ROLE_COLORS[r], dash="dot") for r in ROLE_LABELS
                ], "连续相位 φ/2π（turn）", "continuous_absolute"),
                _panel("SL readout current: physical", [physical_series(width, r, "I(L_SL|XBVM1)") for r in ROLE_LABELS], "current (µA)"),
            ],
        })

        source_only = {role: source_path(width, role) for role in ("logical1_read", "logical0_read")}
        specs.append({
            "id": f"physical-bvm-jsl12-qb-{width}ps-source-before-after",
            "title": f"Physical BVM→12×JSL→scaled QB · {width} ps source before/after QB loading",
            "output": f"{EXP}/plots/{width}ps-source-before-vs-after-qb-loading.html",
            "role": "COMPARISON",
            "cases": [f"{width} source-only {r}" for r in source_only] + [f"{width} physical {r}" for r in source_only],
            "notes": "source-only 是已有 no-receiver reference；physical 是 12×JSL 末端接 QB 后的 measured source。重点看 I(L_SL)、V(SL1)、V(N6) 的 source/load-line 改变。",
            "panels": [
                _panel("SL readout current", [
                    source_series(f"{width} source-only · {ROLE_LABELS[r]}", source_only[r], "I(L_SL|XBVM1)", role=r, color="#3973ac" if r == "logical1_read" else "#7aa6d8") for r in source_only
                ] + [
                    physical_series(width, r, "I(L_SL|XBVM1)", label=f"{width} physical · {ROLE_LABELS[r]}") for r in source_only
                ], "current (µA)"),
                _panel("SL voltage", [
                    source_series(f"{width} source-only · {ROLE_LABELS[r]}", source_only[r], "V(SL1)", role=r, color="#3973ac" if r == "logical1_read" else "#7aa6d8") for r in source_only
                ] + [
                    physical_series(width, r, "V(SL1)", label=f"{width} physical · {ROLE_LABELS[r]}") for r in source_only
                ], "voltage (µV)"),
                _panel("N6 voltage", [
                    source_series(f"{width} source-only · {ROLE_LABELS[r]}", source_only[r], "V(N6|XBVM1)", role=r, color="#3973ac" if r == "logical1_read" else "#7aa6d8") for r in source_only
                ] + [
                    physical_series(width, r, "V(N6|XBVM1)", label=f"{width} physical · {ROLE_LABELS[r]}") for r in source_only
                ], "voltage (µV)"),
                _panel("BVM read/storage phase (physical)", [
                    physical_series(width, r, column, "phase", label=f"physical · {ROLE_LABELS[r]} · {name}")
                    for r in source_only
                    for name, column in (("JM1", "P(B_JM1|XBVM1)"), ("JM2", "P(B_JM2|XBVM1)"), ("JS1", "P(B_JS1|XBVM1)"), ("JS2", "P(B_JS2|XBVM1)"))
                ], "连续相位 φ/2π（turn）", "continuous_absolute"),
            ],
        })

    specs.append({
        "id": "physical-bvm-jsl12-qb-logical1-vs-logical0",
        "title": "Physical BVM→12×JSL→scaled QB · logical1 versus logical0",
        "output": f"{EXP}/plots/physical-logical1-vs-logical0.html",
        "role": "COMPARISON",
        "cases": [f"{w}/{r}" for w, r in [(13, "logical1_read"), (13, "logical0_read"), (14, "logical1_read"), (14, "logical0_read")]],
        "notes": "只比较 canonical READ 的 logical1/logical0；READ=0 controls 在 matched-case 页面和单工况页面单独保留。",
        "panels": [
            _panel("SL readout current", [physical_series(w, r, "I(L_SL|XBVM1)", label=f"{w} ps · {ROLE_LABELS[r]}") for w, r in [(13, "logical1_read"), (13, "logical0_read"), (14, "logical1_read"), (14, "logical0_read")]], "current (µA)"),
            _panel("BJs phase", [physical_series(w, r, phase_column("BJs"), "phase", label=f"{w} ps · {ROLE_LABELS[r]}") for w, r in [(13, "logical1_read"), (13, "logical0_read"), (14, "logical1_read"), (14, "logical0_read")]], "连续相位 φ/2π（turn）", "continuous_absolute"),
            _panel("BJL1 phase", [physical_series(w, r, "P(BJL1|XBQ)", "phase", label=f"{w} ps · {ROLE_LABELS[r]}") for w, r in [(13, "logical1_read"), (13, "logical0_read"), (14, "logical1_read"), (14, "logical0_read")]], "连续相位 φ/2π（turn）", "continuous_absolute"),
            _panel("BJL2 phase", [physical_series(w, r, "P(BJL2|XBQ)", "phase", label=f"{w} ps · {ROLE_LABELS[r]}") for w, r in [(13, "logical1_read"), (13, "logical0_read"), (14, "logical1_read"), (14, "logical0_read")]], "连续相位 φ/2π（turn）", "continuous_absolute"),
            _panel("BJL2 current", [physical_series(w, r, "I(BJL2|XBQ)", label=f"{w} ps · {ROLE_LABELS[r]}") for w, r in [(13, "logical1_read"), (13, "logical0_read"), (14, "logical1_read"), (14, "logical0_read")]], "current (µA)"),
        ],
    })

    # Replace the old sparse event page at the same path.  It now shows the
    # full BJs->BJL1->BJL2 ladder and the direct same-JJ voltage used by the
    # formal segment analysis.
    event_cases = [(13, "logical1_read"), (14, "logical1_read"), (13, "logical0_read"), (14, "logical0_read")]
    specs.append({
        "id": "physical-bvm-jsl12-qb-bjl2-event-evidence",
        "title": "Physical BVM→12×JSL→scaled QB · phase / same-JJ voltage-area evidence",
        "output": f"{EXP}/plots/bjl2-phase-area-evidence.html",
        "role": "RESULT",
        "cases": [f"{w}/{r}" for w, r in event_cases],
        "notes": "图中标出 registered active window 94–130 ps 与 post window 140–170 ps；same-segment voltage-area 和 event classification 以正式 analysis JSON/REPORT 为准。",
        "panels": [
            _panel("BJs continuous phase", [physical_series(w, r, phase_column("BJs"), "phase", label=f"{w} ps · {ROLE_LABELS[r]}") for w, r in event_cases], "连续相位 φ/2π（turn）", "continuous_absolute"),
            _panel("BJL1 continuous phase", [physical_series(w, r, "P(BJL1|XBQ)", "phase", label=f"{w} ps · {ROLE_LABELS[r]}") for w, r in event_cases], "连续相位 φ/2π（turn）", "continuous_absolute"),
            _panel("BJL2 continuous phase", [physical_series(w, r, "P(BJL2|XBQ)", "phase", label=f"{w} ps · {ROLE_LABELS[r]}") for w, r in event_cases], "连续相位 φ/2π（turn）", "continuous_absolute"),
            _panel("BJL2 same-JJ voltage", [physical_series(w, r, "V(BJL2|XBQ)", label=f"{w} ps · {ROLE_LABELS[r]}") for w, r in event_cases], "voltage (µV)"),
            _panel("BJL2 current", [physical_series(w, r, "I(BJL2|XBQ)", label=f"{w} ps · {ROLE_LABELS[r]}") for w, r in event_cases], "current (µA)"),
        ],
        "metrics_widths": (13, 14),
    })
    return specs


def add_window_shapes(fig: go.Figure, rows: int, enabled: bool) -> None:
    if not enabled:
        return
    for row in range(1, rows + 1):
        fig.add_vrect(x0=ACTIVE[0], x1=ACTIVE[1], fillcolor="#f5c16c", opacity=0.08,
                      line_width=0, row=row, col=1)
        fig.add_vrect(x0=POST[0], x1=POST[1], fillcolor="#93c5fd", opacity=0.06,
                      line_width=0, row=row, col=1)
        fig.add_vline(x=ACTIVE[0], line_dash="dot", line_color="#c47f00", line_width=0.8, row=row, col=1)
        fig.add_vline(x=ACTIVE[1], line_dash="dot", line_color="#c47f00", line_width=0.8, row=row, col=1)
        fig.add_vline(x=POST[0], line_dash="dash", line_color="#477db7", line_width=0.8, row=row, col=1)


def write_matplotlib_preview(spec: dict[str, Any], output: Path) -> None:
    """Write a compact static preview when Plotly/Kaleido has no browser backend."""
    fig, axes = plt.subplots(len(spec["panels"]), 1, figsize=(15, max(7, 2.5 * len(spec["panels"]))), sharex=True)
    if len(spec["panels"]) == 1:
        axes = [axes]
    for axis, panel in zip(axes, spec["panels"]):
        for item in panel["series"]:
            data = frame(item["path"])
            y = data[item["column"]].to_numpy(copy=True)
            if item["kind"] == "phase":
                y = y / TWO_PI
            elif panel["unit"] == "voltage (µV)":
                y = y * 1e6
            elif panel["unit"] == "current (µA)":
                y = y * 1e6
            axis.plot(data["time"] * 1e12, y, label=item["label"],
                      color=item.get("color"), linestyle="--" if item.get("dash") in {"dash", "dot"} else "-", linewidth=0.8)
        axis.axvspan(ACTIVE[0], ACTIVE[1], color="#f5c16c", alpha=0.10)
        axis.axvspan(POST[0], POST[1], color="#93c5fd", alpha=0.08)
        axis.axvline(ACTIVE[0], color="#c47f00", linestyle=":", linewidth=0.7)
        axis.axvline(ACTIVE[1], color="#c47f00", linestyle=":", linewidth=0.7)
        static_unit = "phase φ/2π (turn)" if "连续相位" in panel["unit"] else panel["unit"]
        axis.set_ylabel(static_unit, fontsize=8)
        axis.set_title(panel["title"], loc="left", fontsize=9)
        axis.grid(True, alpha=0.2)
        if len(panel["series"]) <= 18:
            axis.legend(loc="upper left", fontsize=6, ncol=3, frameon=False)
    axes[-1].set_xlabel("time (ps)")
    fig.suptitle(spec["title"], fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.98))
    fig.savefig(output, dpi=130)
    plt.close(fig)


def render(spec: dict[str, Any]) -> None:
    panels = spec["panels"]
    fig = make_subplots(
        rows=len(panels), cols=1, shared_xaxes=True,
        vertical_spacing=min(0.035, 0.16 / max(len(panels), 1)),
        subplot_titles=[panel["title"] for panel in panels],
    )
    semantics: set[str] = set()
    source_paths: set[str] = set()
    required_signals: set[str] = set()
    for row, panel in enumerate(panels, 1):
        for item in panel["series"]:
            path = item["path"]
            df = frame(path)
            column = item["column"]
            if column not in df.columns:
                raise KeyError(f"{column} not found in {path}")
            x = df["time"] * 1e12
            y = df[column].copy()
            if item["kind"] == "phase":
                y = y / TWO_PI
                semantics.add(panel["phase_semantics"] or "UNDECLARED")
            elif panel["unit"] == "voltage (µV)":
                y = y * 1e6
            elif panel["unit"] == "current (µA)":
                y = y * 1e6
            line: dict[str, Any] = {"width": 1.25}
            if item.get("color"):
                line["color"] = item["color"]
            if item.get("dash"):
                line["dash"] = item["dash"]
            fig.add_trace(go.Scatter(
                x=x, y=y, mode="lines", name=item["label"],
                legendgroup=item["label"], line=line,
                hovertemplate=f"{item['label']}<br>%{{x:.4g}} ps<br>%{{y:.6g}}<extra></extra>",
            ), row=row, col=1)
            source_paths.add(path)
            required_signals.add(column)
        fig.update_yaxes(title_text=panel["unit"], row=row, col=1)
    add_window_shapes(fig, len(panels), any(panel.get("window", True) for panel in panels))
    fig.update_xaxes(title_text="time (ps)", row=len(panels), col=1)
    fig.update_layout(
        title=spec["title"], template="plotly_white", hovermode="x unified",
        height=max(720, 250 * len(panels)),
        legend=dict(orientation="h", y=-0.07, font=dict(size=10)),
        margin=dict(l=100, r=30, t=115, b=135),
    )
    output = ROOT / spec["output"]
    output.parent.mkdir(parents=True, exist_ok=True)
    meta = {
        "experiment_id": EXP,
        "plot_id": spec["id"],
        "role": spec["role"],
        "cases": spec["cases"],
        "phase_semantics": sorted(semantics),
        "source_paths": sorted(source_paths),
        "required_signals": sorted(required_signals),
        "registered_windows_ps": {"active": list(ACTIVE), "post": list(POST)},
        "generated_from": "scripts/generate_physical_closure_visualizations.py; existing raw CSV only",
        "scientific_authority": "accepted analysis/report; visualization is not event authority",
    }
    note = (
        "<section class='provenance' style='font:14px system-ui,sans-serif;padding:14px;"
        "border:1px solid #ccd6e0;background:#f7f9fc;margin-bottom:12px'>"
        f"<b>Plot role:</b> {html.escape(spec['role'])} &nbsp; "
        f"<b>Experiment:</b> {html.escape(EXP)}<br>"
        f"{html.escape(spec['notes'])}<br>"
        "<b>窗口：</b> active 94–130 ps；post 140–170 ps。"
        " <b>phase 语义：</b>原始 JoSIM P(...) 连续轨迹 / 2π；未基线相减、未按脉冲归零；不等于 SFQ 计数。"
        "</section>"
    )
    if "metrics_width" in spec:
        note += metrics_note(spec["metrics_width"])
    elif "metrics_widths" in spec:
        note += "".join(metrics_note(width) for width in spec["metrics_widths"])
    fragment = fig.to_html(include_plotlyjs="cdn", full_html=False, config={"displaylogo": False, "responsive": True})
    head = (
        "<!doctype html><html lang='zh-CN'><head><meta charset='utf-8'>"
        f"<meta name='experiment-id' content='{html.escape(EXP)}'>"
        f"<meta name='plot-id' content='{html.escape(spec['id'])}'>"
        f"<meta name='plot-role' content='{html.escape(spec['role'])}'>"
        f"<meta name='phase-semantics' content='{html.escape(','.join(sorted(semantics)))}'>"
        f"<script type='application/json' id='alignment-metadata'>{json.dumps(meta, ensure_ascii=False)}</script>"
        f"<title>{html.escape(spec['title'])}</title>"
        "<style>body{max-width:1700px;margin:1rem auto;padding:0 1rem;background:#fff}"
        ".evidence-table{font:13px system-ui,sans-serif;margin:10px 0 14px;padding:10px;"
        "border:1px solid #d7dde5;background:#fbfcfe}.evidence-table table{border-collapse:collapse;"
        "width:100%}.evidence-table th,.evidence-table td{border:1px solid #d7dde5;padding:5px 7px;"
        "text-align:left}.evidence-table th{background:#eef2f7}</style></head>"
        f"<body>{note}{fragment}</body></html>"
    )
    output.write_text(head, encoding="utf-8")
    output.with_suffix(".metadata.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    # Static PNGs are convenience previews only; HTML remains the canonical
    # interactive visualization entry in the alignment manifest.
    if spec["id"] in {"physical-width-comparison", "physical-source-and-storage-guards", "physical-qb-routing-and-kcl", "physical-bvm-jsl12-qb-bjl2-event-evidence"}:
        try:
            fig.write_image(output.with_suffix(".png"), scale=1)
        except Exception as exc:  # pragma: no cover - optional kaleido path
            write_matplotlib_preview(spec, output.with_suffix(".png"))
            print(f"Plotly PNG backend unavailable; wrote matplotlib preview for {output}: {exc}")
    print(f"generated {output}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", action="append", help="render only this spec id; repeatable")
    args = parser.parse_args()
    wanted = set(args.id or [])
    for spec in specs():
        if wanted and spec["id"] not in wanted:
            continue
        render(spec)


if __name__ == "__main__":
    main()
