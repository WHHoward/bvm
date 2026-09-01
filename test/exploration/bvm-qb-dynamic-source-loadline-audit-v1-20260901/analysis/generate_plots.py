#!/usr/bin/env python3
"""Generate the six focused audit figures.

The waveform figures deliberately use the repository's ``josim-plot2.py``
template.  The two relationship figures use small Plotly layouts because a
parametric port trajectory and a causal timeline are not ordinary JoSIM trace
plots.  No raw CSV is copied into the target directory.
"""
from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots


REPO = Path(__file__).resolve().parents[4]
TARGET = REPO / "test/exploration/bvm-qb-dynamic-source-loadline-audit-v1-20260901"
MATRIX = REPO / "test/exploration/bvm-load-qb-matrix-v1-20260901"
PLOTS = TARGET / "plots"
PARENT_HEAD = "b761ba948d0cf64affdc0b9fb623fab05197cf21"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def relative(path: Path) -> str:
    return path.relative_to(REPO).as_posix()


def case_path(fixture: str, width: int, load: str) -> Path:
    return MATRIX / "raw" / fixture / f"{width}ps" / load / "logical1_read" / "run-01.csv"


def read_csv(path: Path) -> tuple[np.ndarray, dict[str, list[np.ndarray]]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        header = next(reader)
        rows = list(reader)
    values = np.asarray([[float(item) for item in row] for row in rows], dtype=float)
    columns: dict[str, list[np.ndarray]] = {}
    for index, name in enumerate(header[1:], start=1):
        columns.setdefault(name, []).append(values[:, index])
    time = values[:, 0]
    if header[0] != "time" or not np.all(np.diff(time) > 0.0):
        raise ValueError(f"invalid time axis: {path}")
    return time, columns


def get(data: tuple[np.ndarray, dict[str, list[np.ndarray]]], name: str, occurrence: int = 0) -> np.ndarray:
    values = data[1].get(name)
    if values is None or occurrence >= len(values):
        raise KeyError(f"missing {name!r} occurrence {occurrence}")
    return values[occurrence]


def write_merged(path: Path, time_s: np.ndarray, series: dict[str, np.ndarray]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lengths = {len(values) for values in series.values()}
    if len(lengths) != 1 or next(iter(lengths)) != len(time_s):
        raise ValueError("merged plot series do not share a length")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["time", *series])
        for index in range(len(time_s)):
            writer.writerow([f"{time_s[index]:.12e}", *[f"{values[index]:.12e}" for values in series.values()]])


def run_josim_plot2(input_path: Path, output_path: Path, title: str) -> None:
    command = [
        sys.executable,
        str(REPO / "scripts/josim-plot2.py"),
        str(input_path),
        "-x", str(output_path),
        "-t", "sep_comb",
        "-c", "dark",
        "-j", "2pi",
        "-w", title,
    ]
    subprocess.run(command, cwd=REPO, check=True)


def plot_metadata(path: Path, title: str, renderer: str, source_paths: list[Path], signals: list[str], notes: list[str] | None = None) -> dict[str, Any]:
    metadata = {
        "title": title,
        "renderer": renderer,
        "output": relative(path),
        "output_sha256": sha256(path),
        "parent_head": PARENT_HEAD,
        "source_raw": [{"path": relative(item), "sha256": sha256(item)} for item in source_paths],
        "signals": signals,
        "notes": notes or [],
    }
    sidecar = path.with_suffix(path.suffix + ".metadata.json")
    sidecar.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return metadata


def waveform_figures() -> list[dict[str, Any]]:
    source9_path = case_path("source", 9, "12x320")
    source13_path = case_path("source", 13, "12x320")
    source13_8_path = case_path("source", 13, "8x500")
    replay9_path = case_path("replay", 9, "12x320")
    replay13_path = case_path("replay", 13, "12x320")
    replay13_8_path = case_path("replay", 13, "8x500")
    physical13_path = case_path("physical", 13, "12x320")
    source9 = read_csv(source9_path)
    source13 = read_csv(source13_path)
    source13_8 = read_csv(source13_8_path)
    replay9 = read_csv(replay9_path)
    replay13 = read_csv(replay13_path)
    replay13_8 = read_csv(replay13_8_path)
    physical13 = read_csv(physical13_path)
    for other in (source13[0], source13_8[0], replay9[0], replay13[0], replay13_8[0], physical13[0]):
        if not np.array_equal(source9[0], other):
            raise ValueError("plot source files do not share an exact time grid")

    result: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="bvm_qb_audit_plots_") as temporary:
        temporary_path = Path(temporary)

        source_diff = get(source13, "I(B_LD1)") - get(source9, "I(B_LD1)")
        merged = temporary_path / "source_ab.csv"
        source_series = {
            "I(A) grounded source I(B_LD1)": get(source9, "I(B_LD1)"),
            "I(B) grounded source I(B_LD1)": get(source13, "I(B_LD1)"),
            "I(B-A) source difference": source_diff,
            "V(A) SL1": get(source9, "V(SL1)"),
            "V(B) SL1": get(source13, "V(SL1)"),
        }
        write_merged(merged, source9[0], source_series)
        output = PLOTS / "A_vs_B_source_9ps_13ps_12x320.html"
        run_josim_plot2(merged, output, "A→B source waveform：9 ps vs 13 ps，12×320")
        result.append(plot_metadata(output, "A→B source waveform：9 ps vs 13 ps，12×320", "scripts/josim-plot2.py", [source9_path, source13_path], list(source_series), ["current/voltage waveform only; current difference is not an SFQ count"]))

        def phase_turns(data: tuple[np.ndarray, dict[str, list[np.ndarray]]], signal: str) -> np.ndarray:
            raw = np.unwrap(get(data, signal))
            reference = raw[np.flatnonzero(data[0] <= 105.0e-12)[0]]
            return (raw - reference) * (2.0 * np.pi)

        qb_series = {
            "I(A) I(LIN|XBQ)": get(replay9, "I(LIN|XBQ)"),
            "I(B) I(LIN|XBQ)": get(replay13, "I(LIN|XBQ)"),
            "V(A) V(IN)": get(replay9, "V(IN)"),
            "V(B) V(IN)": get(replay13, "V(IN)"),
            "P(A) BJs": phase_turns(replay9, "P(BJS|XBQ)"),
            "P(B) BJs": phase_turns(replay13, "P(BJS|XBQ)"),
            "P(A) BJL1": phase_turns(replay9, "P(BJL1|XBQ)"),
            "P(B) BJL1": phase_turns(replay13, "P(BJL1|XBQ)"),
            "P(A) BJL2": phase_turns(replay9, "P(BJL2|XBQ)"),
            "P(B) BJL2": phase_turns(replay13, "P(BJL2|XBQ)"),
        }
        merged = temporary_path / "qb_ab.csv"
        write_merged(merged, replay9[0], qb_series)
        output = PLOTS / "A_vs_B_qb_internal_trajectory.html"
        run_josim_plot2(merged, output, "A→B QB internal trajectory：9 ps vs 13 ps，12×320")
        result.append(plot_metadata(output, "A→B QB internal trajectory：9 ps vs 13 ps，12×320", "scripts/josim-plot2.py", [replay9_path, replay13_path], list(qb_series), ["P columns are continuously unwrapped radians before josim-plot2 converts to turns; no event count"]))

        physical_source_series = {
            "I(grounded) I(B_LD1)": get(source13, "I(B_LD1)"),
            "I(physical) I(B_LD1)": get(physical13, "I(B_LD1)"),
            "I(grounded-physical) DeltaI": get(source13, "I(B_LD1)") - get(physical13, "I(B_LD1)"),
            "I(physical) I(L_SL|XBVM1)": get(physical13, "I(L_SL|XBVM1)"),
            "V(grounded) SL1": get(source13, "V(SL1)"),
            "V(physical) SL1": get(physical13, "V(SL1)"),
        }
        merged = temporary_path / "source_backaction.csv"
        write_merged(merged, source13[0], physical_source_series)
        output = PLOTS / "B_vs_C_source_load_backaction.html"
        run_josim_plot2(merged, output, "B→C source/load back-action：grounded vs physical JSL，13 ps，12×320")
        result.append(plot_metadata(output, "B→C source/load back-action：grounded vs physical JSL，13 ps，12×320", "scripts/josim-plot2.py", [source13_path, physical13_path], list(physical_source_series), ["DeltaI=grounded−physical; current area is a waveform diagnostic, not an SFQ quantity"]))

        load_series = {
            "I(12x320) I(I_REPLAY)": get(replay13, "I(I_REPLAY)"),
            "I(8x500) I(I_REPLAY)": get(replay13_8, "I(I_REPLAY)"),
            "I(12x320) I(LIN|XBQ)": get(replay13, "I(LIN|XBQ)"),
            "I(8x500) I(LIN|XBQ)": get(replay13_8, "I(LIN|XBQ)"),
            "P(12x320) BJs": phase_turns(replay13, "P(BJS|XBQ)"),
            "P(8x500) BJs": phase_turns(replay13_8, "P(BJS|XBQ)"),
            "P(12x320) BJL1": phase_turns(replay13, "P(BJL1|XBQ)"),
            "P(8x500) BJL1": phase_turns(replay13_8, "P(BJL1|XBQ)"),
            "P(12x320) BJL2": phase_turns(replay13, "P(BJL2|XBQ)"),
            "P(8x500) BJL2": phase_turns(replay13_8, "P(BJL2|XBQ)"),
        }
        merged = temporary_path / "load_comparison.csv"
        write_merged(merged, replay13[0], load_series)
        output = PLOTS / "13ps_12x320_vs_8x500_ideal.html"
        run_josim_plot2(merged, output, "13 ps ideal replay：12×320 vs 8×500 source/QB trajectory")
        result.append(plot_metadata(output, "13 ps ideal replay：12×320 vs 8×500 source/QB trajectory", "scripts/josim-plot2.py", [replay13_path, replay13_8_path], list(load_series), ["phase is continuously unwrapped and shown in turns; count/Ic are confounded; no H7 attribution"]))
    return result


def dynamic_port_figure() -> dict[str, Any]:
    source_path = case_path("source", 13, "12x320")
    physical_path = case_path("physical", 13, "12x320")
    source = read_csv(source_path)
    physical = read_csv(physical_path)
    time_ps = physical[0] * 1e12
    fig = make_subplots(rows=1, cols=2, subplot_titles=("QB input port：V(IN)–I(LIN)", "source side：V(SL1)–I(B_LD1)"), horizontal_spacing=0.12)
    fig.add_trace(go.Scatter(x=get(physical, "I(LIN|XBQ)") * 1e6, y=get(physical, "V(IN)") * 1e3, mode="lines", name="physical 12×320", customdata=time_ps, hovertemplate="I(LIN)=%{x:.4g} µA<br>V(IN)=%{y:.4g} mV<br>t=%{customdata:.5g} ps<extra></extra>"), row=1, col=1)
    fig.add_trace(go.Scatter(x=get(source, "I(B_LD1)") * 1e6, y=get(source, "V(SL1)") * 1e3, mode="lines", name="grounded source", customdata=source[0] * 1e12, hovertemplate="I(B_LD1)=%{x:.4g} µA<br>V(SL1)=%{y:.4g} mV<br>t=%{customdata:.5g} ps<extra></extra>"), row=1, col=2)
    fig.add_trace(go.Scatter(x=get(physical, "I(B_LD1)") * 1e6, y=get(physical, "V(SL1)") * 1e3, mode="lines", name="physical JSL", customdata=time_ps, hovertemplate="I(B_LD1)=%{x:.4g} µA<br>V(SL1)=%{y:.4g} mV<br>t=%{customdata:.5g} ps<extra></extra>"), row=1, col=2)
    fig.update_xaxes(title_text="current (µA)")
    fig.update_yaxes(title_text="voltage (mV)", row=1, col=1)
    fig.update_yaxes(title_text="voltage (mV)", row=1, col=2)
    fig.update_layout(title="B→C dynamic input-port trajectories：13 ps，12×320", template="plotly_dark", hovermode="closest", height=620, margin=dict(l=70, r=40, t=100, b=70))
    fig.add_annotation(x=0.5, y=-0.19, xref="paper", yref="paper", text="trajectory diagnostic only；不是静态 load line 或 Thévenin/small-signal impedance", showarrow=False)
    output = PLOTS / "B_vs_C_dynamic_input_IV.html"
    fig.write_html(output)
    return plot_metadata(output, "B→C dynamic input-port trajectories：13 ps，12×320", "custom Plotly parametric trajectory", [source_path, physical_path], ["V(IN)", "I(LIN|XBQ)", "V(SL1)", "I(B_LD1)"], ["TWO-BOUNDARY DYNAMIC SECANT DIAGNOSTIC is recorded separately; this figure does not turn it into an impedance"])


def causal_timeline_figure() -> dict[str, Any]:
    timeline_path = TARGET / "analysis/divergence-timeline.json"
    payload = json.loads(timeline_path.read_text(encoding="utf-8"))
    families = ["source waveform", "QB IN/Lin", "BJs", "node2/BJL1", "node3", "BJL2", "OUT"]
    y_map = {family: len(families) - index for index, family in enumerate(families)}
    fig = go.Figure()
    colors = {"12x320": "#00cc96", "8x500": "#ab63fa"}
    for load, timeline in payload["timelines"].items():
        for item in timeline["family_first_divergence"]:
            fig.add_trace(go.Scatter(x=[item["time_ps"]], y=[y_map[item["family"]]], mode="markers", marker=dict(size=12, color=colors[load], symbol="diamond" if item.get("tie") else "circle"), name=load, legendgroup=load, showlegend=(item["family"] == families[0]), customdata=[[item["signal"], item.get("tie"), item.get("threshold")]], hovertemplate=f"{load}<br>%{{y}}<br>t=%{{x:.6f}} ps<br>signal=%{{customdata[0]}}<br>threshold=%{{customdata[2]:.4g}}<br>TIE=%{{customdata[1]}}<extra></extra>"))
    fig.add_vline(x=105.0, line_dash="dash", line_color="#ffa15a", annotation_text="105 ps common boundary", annotation_position="top left")
    fig.update_yaxes(tickmode="array", tickvals=list(y_map.values()), ticktext=families, title_text="trajectory family")
    fig.update_xaxes(title_text="first sustained divergence time (ps)", range=[104.8, 106.0])
    fig.update_layout(title="A→B causal-divergence timeline：same sampling bin marked TIE", template="plotly_dark", hovermode="closest", height=620, margin=dict(l=150, r=40, t=90, b=70), legend_title_text="load", annotations=[dict(x=0.5, y=-0.16, xref="paper", yref="paper", text="规则：numerical floor + 连续 2 samples；时间分辨率为 0.0125 ps；图仅描述 earliest divergence，不证明因果机制", showarrow=False)])
    output = PLOTS / "causal_timeline.html"
    fig.write_html(output)
    source_paths = [case_path("source", 9, "12x320"), case_path("source", 13, "12x320"), case_path("replay", 9, "12x320"), case_path("replay", 13, "12x320"), case_path("source", 9, "8x500"), case_path("source", 13, "8x500"), case_path("replay", 9, "8x500"), case_path("replay", 13, "8x500")]
    return plot_metadata(output, "A→B causal-divergence timeline：same sampling bin marked TIE", "custom Plotly timeline", source_paths, families, ["earliest divergence is a descriptive timing result, not a causal proof"])


def main() -> None:
    PLOTS.mkdir(parents=True, exist_ok=True)
    generated = waveform_figures()
    generated.append(dynamic_port_figure())
    generated.append(causal_timeline_figure())
    plot_hashes = {item["output"]: item["output_sha256"] for item in generated}
    (TARGET / "analysis/plot-hashes.json").write_text(json.dumps({"parent_head": PARENT_HEAD, "plots": plot_hashes, "metadata": [relative(PLOTS / Path(item["output"]).name) + ".metadata.json" for item in generated]}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"count": len(generated), "plots": plot_hashes}, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
