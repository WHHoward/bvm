#!/usr/bin/env python3
"""Build the registered READ-semantics and JSL-width result views.

This is a documentation-only renderer.  It consumes existing CSV/JSON
artifacts and delegates multi-case plotting to the repository visualization
skill's plot_case_matrix.py.
"""
from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[2]
PLOTTER = REPO / ".agents/skills/josim-exploration-visualization/scripts/plot_case_matrix.py"
PLOT_DIR = ROOT / "plots"
SPEC_DIR = ROOT / "analysis/plot_specs"
PHASE_NOTE = (
    "连续相位 φ/2π（turn）：原始 JoSIM P(t)/(2π) 连续轨迹；"
    "未做基线相减、未按脉冲归零；不等于 SFQ 计数。"
)


def repo_rel(path: Path) -> str:
    return path.relative_to(REPO).as_posix()


def write_spec(name: str, spec: dict[str, Any]) -> Path:
    SPEC_DIR.mkdir(parents=True, exist_ok=True)
    path = SPEC_DIR / f"{name}.json"
    path.write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def render_matrix(name: str, spec: dict[str, Any], *, phase: bool = False,
                  notes: str = "", roles: dict[str, str] | None = None) -> Path:
    spec_path = write_spec(name, spec)
    output = PLOT_DIR / f"{name}.html"
    subprocess.run([sys.executable, str(PLOTTER), str(spec_path), "--output", str(output)], check=True)
    metadata = {
        "title": spec.get("title", name),
        "source_paths": sorted({
            series["csv"]
            for panel in spec.get("panels", [])
            for series in panel.get("series", [])
        }),
        "phase_semantics": "continuous_absolute" if phase else None,
        "case_roles": roles or {},
        "notes": notes,
        "renderer": "josim-exploration-visualization/plot_case_matrix.py",
    }
    (output.with_suffix(".metadata.json")).write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return output


def source_paths(width: int, role: str) -> Path:
    if width == 12 and role == "logical1_read":
        return REPO / "test/exploration/bvm-jsl-read-width-to-qb-sfq-v1-20260824/raw/phase-b/12jsl-12ps/logical1-read/run-01.csv"
    if width == 12 and role == "logical0_read":
        return ROOT / "raw/12ps-canonical/logical0-read/run-01.csv"
    return ROOT / f"raw/{width}ps/{role.replace('_read', '-read')}/run-01.csv"


def replay_path(width: int, role: str) -> Path:
    return ROOT / "raw/replay" / f"{width}ps/{role}/run-01.csv"


def series_for(cases: list[tuple[str, Path, str]], column: str,
               *, line_dash_by: str | None = None) -> list[dict[str, Any]]:
    out = []
    for label, path, role in cases:
        item: dict[str, Any] = {
            "label": label,
            "csv": os.path.relpath(path, SPEC_DIR).replace("\\", "/"),
            "column": column,
            "group": role,
        }
        if line_dash_by == "role":
            item["line"] = {"dash": "dash" if "logical0" in role else "solid"}
        out.append(item)
    return out


def build_read_semantics_table() -> None:
    manifest = yaml.safe_load((REPO / "docs/BVM_READ_SEMANTICS_MANIFEST.yaml").read_text(encoding="utf-8"))
    rows = []
    for case in manifest.get("cases", []):
        rows.append(
            "<tr>"
            f"<td>{case.get('case_id','')}</td>"
            f"<td>{case.get('role','')}</td>"
            f"<td>{case.get('fixture','')}</td>"
            f"<td>{case.get('classification','')}</td>"
            f"<td>{case.get('protocol_status','')}</td>"
            f"<td>{case.get('lineage_status','')}</td>"
            "</tr>"
        )
    html = """<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>BVM READ semantics audit</title>
<style>body{font-family:system-ui,sans-serif;background:#111827;color:#e5e7eb;margin:2rem}h1{font-size:1.5rem}p{max-width:1100px;line-height:1.6}table{border-collapse:collapse;width:100%;font-size:.82rem}th,td{border:1px solid #374151;padding:.45rem;text-align:left;vertical-align:top}th{background:#1f2937;position:sticky;top:0}tr:nth-child(even){background:#172033}.ok{color:#86efac}</style>
</head><body><h1>BVM READ semantics audit</h1>
<p><span class="ok">Formal roles:</span> logical1_read = positive stored state + canonical positive WL/SE READ；logical0_read = negative stored state + exactly the same canonical positive READ；logical1/0_no_read_control = READ disabled. WL-only negative initialization is a diagnostic, not canonical logical0.</p>
<p>本表是 provenance audit，不是 event 计数。旧 PAPER-SL logical0 lineage 保留用于追溯，但不得作为 canonical read0 结果。</p>
<table><thead><tr><th>case</th><th>role</th><th>fixture</th><th>classification</th><th>protocol</th><th>lineage</th></tr></thead><tbody>
""" + "\n".join(rows) + """</tbody></table></body></html>
"""
    output = PLOT_DIR / "read-semantics-audit.html"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding="utf-8")
    (output.with_suffix(".metadata.json")).write_text(json.dumps({
        "title": "BVM READ semantics audit",
        "source_paths": ["docs/BVM_READ_SEMANTICS_MANIFEST.yaml", "docs/BVM_READ_SEMANTICS_AUDIT.md"],
        "phase_semantics": None,
        "case_roles": {"canonical": "RESULT", "legacy": "HISTORICAL_REFERENCE"},
        "notes": "Formal case-role and protocol provenance table.",
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_source_plot() -> None:
    widths = [12, 13, 14, 15]
    cases: list[tuple[str, Path, str]] = []
    for width in widths:
        for role in ("logical1_read", "logical0_read"):
            path = source_paths(width, role)
            if not path.exists():
                raise FileNotFoundError(path)
            label = f"{width} ps · {'read1' if 'logical1' in role else 'read0'}"
            cases.append((label, path, role))
    roles = {label: ("RESULT" if "read1" in label else "NEGATIVE_CONTROL") for label, _, _ in cases}
    panels = [
        {"title": "JSL source current I(B_LD1)", "column": "I(B_LD1)", "y_scale": 1e6, "y_label": "I(B_LD1) (µA)", "x_scale": 1e12, "series": series_for(cases, "I(B_LD1)", line_dash_by="role")},
        {"title": "canonical BVM SL-side current I(L_SL)", "column": "I(L_SL|XBVM1)", "y_scale": 1e6, "y_label": "I(L_SL) (µA)", "x_scale": 1e12, "series": series_for(cases, "I(L_SL|XBVM1)", line_dash_by="role")},
        {"title": "canonical BVM SL voltage V(SL1)", "column": "V(SL1)", "y_scale": 1e6, "y_label": "V(SL1) (µV)", "x_scale": 1e12, "series": series_for(cases, "V(SL1)", line_dash_by="role")},
    ]
    render_matrix(
        "source-width-comparison", {
            "title": "Canonical 12/13/14/15 ps JSL source: read1 vs canonical read0",
            "x_label": "time (ps)", "panels": panels,
        }, notes="read1/read0 are canonical positive WL+SE READ cases after the semantics correction; phase not plotted here.", roles=roles)


def build_qb_plot() -> None:
    widths = [12, 13, 14, 15]
    cases: list[tuple[str, Path, str]] = []
    for width in widths:
        for role in ("logical1_read", "logical0_read"):
            path = replay_path(width, role)
            if not path.exists():
                raise FileNotFoundError(path)
            cases.append((f"{width} ps · {'read1' if 'logical1' in role else 'read0'}", path, role))
    roles = {label: ("RESULT" if "read1" in label else "NEGATIVE_CONTROL") for label, _, _ in cases}
    panels = [
        {"title": "BJL2 continuous phase φ/2π", "column": "P(BJL2|XBQ)", "phase_turns": True, "y_label": "连续相位 φ/2π (turn)", "x_scale": 1e12, "series": series_for(cases, "P(BJL2|XBQ)", line_dash_by="role")},
        {"title": "BJL1 continuous phase φ/2π", "column": "P(BJL1|XBQ)", "phase_turns": True, "y_label": "连续相位 φ/2π (turn)", "x_scale": 1e12, "series": series_for(cases, "P(BJL1|XBQ)", line_dash_by="role")},
        {"title": "BJL2 voltage", "column": "V(BJL2|XBQ)", "y_scale": 1e6, "y_label": "V(BJL2) (µV)", "x_scale": 1e12, "series": series_for(cases, "V(BJL2|XBQ)", line_dash_by="role")},
        {"title": "BJL2 current", "column": "I(BJL2|XBQ)", "y_scale": 1e6, "y_label": "I(BJL2) (µA)", "x_scale": 1e12, "series": series_for(cases, "I(BJL2|XBQ)", line_dash_by="role")},
    ]
    render_matrix(
        "qb-replay-width-comparison", {
            "title": "Frozen scaled QB replay: 12/13/14/15 ps canonical read1 vs read0",
            "x_label": "time (ps)", "panels": panels,
        }, phase=True, notes=PHASE_NOTE + " 同一 BJL2 segment 的 direct voltage area 见 REPORT.md。", roles=roles)


def build_margin_plot() -> None:
    metrics = json.loads((ROOT / "analysis/metrics.json").read_text(encoding="utf-8"))
    csv_path = ROOT / "analysis/width-margin-summary.csv"
    fields = [
        "width_ps", "read1_bjl2_activity_p2p_turns", "read0_bjl2_activity_p2p_turns",
        "read1_bjl2_largest_segment_turns", "read0_bjl2_largest_segment_turns",
        "read1_bjl2_area_phi0", "read0_bjl2_area_phi0",
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for width in (12, 13, 14, 15):
            qb = metrics["widths"][str(width)]["qb"]
            row: dict[str, Any] = {"width_ps": width}
            for role, prefix in (("logical1_read", "read1"), ("logical0_read", "read0")):
                bjl2 = qb[role]["junctions"]["BJL2"]
                segment = bjl2["largest_segment"] or {}
                row[f"{prefix}_bjl2_activity_p2p_turns"] = bjl2["phase_activity_p2p_turns"]
                row[f"{prefix}_bjl2_largest_segment_turns"] = segment.get("delta_turns", 0.0)
                row[f"{prefix}_bjl2_area_phi0"] = segment.get("area_phi0", 0.0)
            writer.writerow(row)
    rel_csv = os.path.relpath(csv_path, SPEC_DIR).replace("\\", "/")
    panels = [
        {"title": "BJL2 activity range", "column": "read1_bjl2_activity_p2p_turns", "y_label": "read1 / read0 activity (turn)", "series": [{"label": "read1", "csv": rel_csv, "column": "read1_bjl2_activity_p2p_turns"}, {"label": "read0", "csv": rel_csv, "column": "read0_bjl2_activity_p2p_turns", "line": {"dash": "dash"}}]},
        {"title": "BJL2 largest monotonic segment", "column": "read1_bjl2_largest_segment_turns", "y_label": "largest segment (turn)", "series": [{"label": "read1", "csv": rel_csv, "column": "read1_bjl2_largest_segment_turns"}, {"label": "read0", "csv": rel_csv, "column": "read0_bjl2_largest_segment_turns", "line": {"dash": "dash"}}]},
        {"title": "same-segment voltage area", "column": "read1_bjl2_area_phi0", "y_label": "∫Vdt/Φ0 (turn-equivalent)", "series": [{"label": "read1", "csv": rel_csv, "column": "read1_bjl2_area_phi0"}, {"label": "read0", "csv": rel_csv, "column": "read0_bjl2_area_phi0", "line": {"dash": "dash"}}]},
    ]
    render_matrix(
        "bjl2-margin-vs-width", {
            "title": "BJL2 margin vs canonical JSL plateau width",
            "x_label": "JSL plateau width (ps)", "panels": panels,
        }, phase=True, notes=PHASE_NOTE + " 图中 segment/area 是 analysis-derived diagnostics，不是仅凭曲线形状的 event count。", roles={"read1": "RESULT", "read0": "NEGATIVE_CONTROL"})


def main() -> None:
    PLOT_DIR.mkdir(parents=True, exist_ok=True)
    build_read_semantics_table()
    build_source_plot()
    build_qb_plot()
    build_margin_plot()
    print("built READ semantics and width-bracket visualizations")


if __name__ == "__main__":
    main()
