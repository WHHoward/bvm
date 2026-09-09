#!/usr/bin/env python3
"""Render registered standalone, zoom, family and mechanism visualizations.

Standalone pages are rendered first. Comparison rendering refuses to start
until standalone visualization QA has passed. All derived inputs are exact
stored-row slices or registered samplewise arithmetic; raw CSVs are never
changed.
"""

from __future__ import annotations

import base64
import csv
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
PLOT2 = REPO / "scripts/josim-plot2.py"
sys.path.insert(0, str(REPO / "scripts"))
from bvmtools.phase import continuous_unwrap  # noqa: E402
from bvmtools.raw import read_csv  # noqa: E402


RUNS = {
    "NOMINAL": ("nominal", 12.0, 2.0),
    "L1_DOWN": ("l1_down", 12.0, 1.9),
    "L1_UP": ("l1_up", 12.0, 2.1),
    "RJ1_UP_05": ("rj1_up_05", 12.5, 2.0),
    "RJ1_UP_10": ("rj1_up_10", 13.0, 2.0),
}
WINDOWS_PS = {"110_116ps": (110.0, 116.0), "110_121ps": (110.0, 121.0)}


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def write_once(path: Path, content: str | bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        old = path.read_bytes()
        new = content if isinstance(content, bytes) else content.encode()
        if old == new:
            return
        raise RuntimeError(f"refusing to overwrite visualization artifact: {path}")
    if isinstance(content, bytes):
        path.write_bytes(content)
    else:
        path.write_text(content, encoding="utf-8")


def raw_path(run_id: str) -> Path:
    return EXP / "runs" / RUNS[run_id][0] / "raw.csv"


def read_rows(path: Path) -> tuple[list[str], list[list[str]]]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.reader(stream)
        return next(reader), list(reader)


def projection_csv(run_id: str, labels: list[str], destination: Path, *, window: tuple[float, float] | None = None, derived_quiet: bool = False) -> tuple[list[str], str]:
    source = raw_path(run_id)
    header, rows = read_rows(source)
    positions = {name: index for index, name in enumerate(header)}
    selected = ["time"] + [label for label in labels if label in positions and label != "time"]
    missing = [label for label in labels if label not in positions]
    out_rows: list[list[str]] = []
    quiet_labels = [f"I(L_SL|XBVM{i})" for i in range(2, 5)]
    needed_quiet = all(label in positions for label in quiet_labels)
    for row in rows:
        time_ps = float(row[0]) * 1e12
        if window is not None and not (window[0] <= time_ps < window[1]):
            continue
        out = [row[positions[label]] for label in selected]
        if derived_quiet and needed_quiet:
            out.append(f"{sum(float(row[positions[label]]) for label in quiet_labels):.17g}")
        out_rows.append(out)
    if derived_quiet and needed_quiet:
        selected.append("I_quiet_total")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(selected)
        writer.writerows(out_rows)
    return missing, selected


def plot2(destination: Path, input_path: Path, labels: list[str], title: str) -> dict[str, object]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    available_header, _ = read_rows(input_path)
    available = set(available_header)
    selected = [label for label in labels if label in available]
    missing = [label for label in labels if label not in available]
    if not selected:
        raise RuntimeError(f"no requested labels available for {destination}")
    command = [
        sys.executable,
        str(PLOT2),
        str(input_path),
        "-x",
        str(destination),
        "-t",
        "sep_comb",
        "-c",
        "dark",
        "-j",
        "2pi",
        "-w",
        title,
        "-s",
        *selected,
    ]
    subprocess.run(command, cwd=REPO, check=True)
    return {"command": command, "selected": selected, "missing": missing}


def manifest_entry(*, stage: str, kind: str, run_ids: list[str], input_path: Path, output_path: Path, command: list[str] | str, signals: list[str], window: list[float] | None, units: dict[str, str], transformation: str, source_paths: list[Path]) -> dict[str, object]:
    return {
        "stage": stage,
        "kind": kind,
        "run_ids": run_ids,
        "input_path": str(input_path),
        "input_sha256": digest(input_path),
        "output_path": str(output_path),
        "output_sha256": digest(output_path),
        "command": command,
        "signal_list": signals,
        "window_ps": window,
        "units": units,
        "phase_convention": "P(...) raw radians; display uses independent continuous unwrap then rad/(2*pi) turns where applicable",
        "transformation_registry": transformation,
        "source_raw_paths": [str(path) for path in source_paths],
        "source_raw_sha256": [digest(path) for path in source_paths],
    }


def standalone() -> int:
    entries: list[dict[str, object]] = []
    source_labels = [
        "I(L_SL|XBVM1)", "I(L_SL|XBVM2)", "I(L_SL|XBVM3)", "I(L_SL|XBVM4)",
        "I(B_JSL1)", "I(B_JSL8)", "V(COMMON_SL)", "V(QBIN)",
    ]
    trigger_labels = [
        "P(BJ1|XBQ1)", "V(BJ1|XBQ1)", "I(RJ1|XBQ1)", "I(L1|XBQ1)",
        "P(BJS|XBQ1)", "V(BJS|XBQ1)", "I(BJS|XBQ1)", "I(LIN|XBQ1)",
    ]
    regeneration_labels = [
        "I(L1|XBQ1)", "I(L2|XBQ1)", "P(BJ2|XBQ1)", "V(BJ2|XBQ1)",
        "I(BJ2|XBQ1)", "I(RJ2|XBQ1)", "I(L3|XBQ1)", "V(QBOUT)",
    ]
    downstream_labels = []
    for stage in range(1, 7):
        downstream_labels.extend(
            [f"P(B01|XJTL1_{stage})", f"V(B01|XJTL1_{stage})", f"I(B01|XJTL1_{stage})", f"P(B02|XJTL1_{stage})", f"V(B02|XJTL1_{stage})", f"I(B02|XJTL1_{stage})", f"V(JTL{stage}_OUT)"]
        )
    downstream_labels.append("I(R_TERM)")
    for run_id in RUNS:
        raw = raw_path(run_id)
        run_dir = EXP / "plots/standalone" / RUNS[run_id][0]
        source_csv = run_dir / "source_interface_data.csv"
        missing, selected = projection_csv(run_id, source_labels, source_csv, derived_quiet=True)
        output = run_dir / "A_SOURCE_INTERFACE.html"
        result = plot2(output, source_csv, selected, f"{run_id} source/interface; current A, voltage V; raw/derived tracks")
        entries.append(manifest_entry(stage="standalone", kind="source_interface", run_ids=[run_id], input_path=source_csv, output_path=output, command=result["command"], signals=result["selected"], window=None, units={"current": "A", "voltage": "V", "time": "s"}, transformation="I_quiet_total samplewise sum; no interpolation/resampling/smoothing; raw phase not included", source_paths=[raw]))
        result = plot2(run_dir / "B_QB_TRIGGER.html", raw, trigger_labels, f"{run_id} QB trigger block; P raw rad and -j 2pi display turns")
        entries.append(manifest_entry(stage="standalone", kind="qb_trigger", run_ids=[run_id], input_path=raw, output_path=run_dir / "B_QB_TRIGGER.html", command=result["command"], signals=result["selected"], window=None, units={"current": "A", "voltage": "V", "phase": "rad; display turns"}, transformation="none", source_paths=[raw]))
        result = plot2(run_dir / "C_REGENERATION.html", raw, regeneration_labels, f"{run_id} QB regeneration; raw tracks")
        entries.append(manifest_entry(stage="standalone", kind="regeneration", run_ids=[run_id], input_path=raw, output_path=run_dir / "C_REGENERATION.html", command=result["command"], signals=result["selected"], window=None, units={"current": "A", "voltage": "V", "phase": "rad; display turns"}, transformation="none", source_paths=[raw]))
        result = plot2(run_dir / "D_DOWNSTREAM.html", raw, downstream_labels, f"{run_id} all six JTL stages and termination; raw tracks")
        entries.append(manifest_entry(stage="standalone", kind="downstream", run_ids=[run_id], input_path=raw, output_path=run_dir / "D_DOWNSTREAM.html", command=result["command"], signals=result["selected"], window=None, units={"current": "A", "voltage": "V", "phase": "rad; display turns"}, transformation="none", source_paths=[raw]))

        zoom_labels = [
            "I(L_SL|XBVM1)", "I(L_SL|XBVM2)", "I(L_SL|XBVM3)", "I(L_SL|XBVM4)",
            "V(COMMON_SL)", "I(B_JSL1)", "I(B_JSL8)", "V(QBIN)",
            "P(BJ1|XBQ1)", "V(BJ1|XBQ1)", "I(RJ1|XBQ1)", "I(L1|XBQ1)", "I(L2|XBQ1)",
            "P(BJ2|XBQ1)", "V(BJ2|XBQ1)", "I(BJ2|XBQ1)", "I(RJ2|XBQ1)", "I(L3|XBQ1)", "V(QBOUT)",
        ]
        for window_name, window in WINDOWS_PS.items():
            data = EXP / "plots/zoom/data" / RUNS[run_id][0] / f"{window_name}.csv"
            missing, selected = projection_csv(run_id, zoom_labels, data, window=window)
            output = EXP / "plots/zoom" / RUNS[run_id][0] / f"{window_name}.html"
            result = plot2(output, data, selected, f"{run_id} critical window [{window[0]},{window[1]}) ps; raw tracks")
            entries.append(manifest_entry(stage="standalone", kind="critical_zoom", run_ids=[run_id], input_path=data, output_path=output, command=result["command"], signals=result["selected"], window=list(window), units={"current": "A", "voltage": "V", "phase": "rad; display turns"}, transformation="exact stored-row half-open window slice only; no interpolation/resampling/smoothing", source_paths=[raw]))
    record = {
        "schema": "qb-rj1-l1-local-sensitivity-standalone-visualization-v1",
        "experiment_id": EXP.name,
        "created_at_local": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "renderer": str(PLOT2),
        "options": "sep_comb dark -j 2pi",
        "entries": entries,
        "status": "PASS",
    }
    (EXP / "analysis/standalone_visualization_manifest.json").write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "stage": "standalone", "entry_count": len(entries)}, ensure_ascii=False))
    return 0


def load_traces() -> dict[str, object]:
    return {run_id: read_csv(raw_path(run_id)) for run_id in RUNS}


def series(trace, label: str) -> tuple[float, ...]:
    return tuple(float(value) for value in trace.column(label))


def x_window(trace, start_ps: float, end_ps: float) -> tuple[list[float], tuple[int, ...]]:
    indices = tuple(index for index, value in enumerate(trace.time) if start_ps * 1e-12 <= value < end_ps * 1e-12)
    return [trace.time[index] * 1e12 for index in indices], indices


def html_for_image(path: Path, title: str) -> None:
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    html = f"<!doctype html><meta charset='utf-8'><title>{title}</title><h1>{title}</h1><img style='max-width:100%' src='data:image/png;base64,{encoded}'>\n"
    # Comparison/mechanism HTML is a regenerated presentation artifact; raw
    # and deck files remain immutable and are never overwritten.
    path.with_suffix(".html").write_text(html, encoding="utf-8")


def family_plot(traces: dict[str, object], run_ids: list[str], family: str, output: Path) -> list[str]:
    specs = [
        ("I(B_JSL8)", "I(B_JSL8)", 1e6, "uA", False),
        ("V(COMMON_SL)", "V(COMMON_SL)", 1e3, "mV", False),
        ("V(QBIN)", "V(QBIN)", 1e3, "mV", False),
        ("BJ1 phase progression", "P(BJ1|XBQ1)", 1.0, "turns from 110 ps", True),
        ("V(BJ1)", "V(BJ1|XBQ1)", 1e3, "mV", False),
        ("I(RJ1)", "I(RJ1|XBQ1)", 1e6, "uA", False),
        ("I(L1)", "I(L1|XBQ1)", 1e6, "uA", False),
        ("I(L2)", "I(L2|XBQ1)", 1e6, "uA", False),
        ("BJ2 phase progression", "P(BJ2|XBQ1)", 1.0, "turns from 110 ps", True),
        ("V(QBOUT)", "V(QBOUT)", 1e3, "mV", False),
        ("terminal response", "V(JTL6_OUT)", 1e3, "mV", False),
    ]
    fig, axes = plt.subplots(4, 3, figsize=(17, 15), sharex=True)
    axes = axes.ravel()
    for axis, (title, label, scale, unit, is_phase) in zip(axes, specs):
        for run_id in run_ids:
            trace = traces[run_id]
            times, indices = x_window(trace, 0.0, 200.0)
            data = series(trace, label)
            if is_phase:
                unwrapped = continuous_unwrap(data)
                ref = min(range(len(trace.time)), key=lambda index: abs(trace.time[index] - 110e-12))
                y = [(unwrapped[index] - unwrapped[ref]) / (2.0 * 3.141592653589793) for index in indices]
            else:
                y = [data[index] * scale for index in indices]
            rj1 = RUNS[run_id][1]
            l1 = RUNS[run_id][2]
            axis.plot(times, y, linewidth=0.9, label=f"{run_id} (RJ1={rj1:g}, L1={l1:g})")
        axis.set_title(title)
        axis.set_ylabel(unit)
        axis.grid(alpha=0.25)
    for axis in axes[len(specs):]:
        axis.axis("off")
    axes[-1].set_xlabel("time (ps)")
    axes[-2].set_xlabel("time (ps)")
    axes[-3].set_xlabel("time (ps)")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", bbox_to_anchor=(0.5, 0.935), ncol=3, fontsize=8)
    fig.suptitle(f"{family} parameter family comparison; exact raw time grid; no smoothing/resampling", y=0.995)
    fig.tight_layout(rect=(0, 0, 1, 0.885))
    fig.savefig(output, dpi=150)
    plt.close(fig)
    return [spec[1] for spec in specs]


def phase_plane(traces: dict[str, object], run_ids: list[str], family: str, output: Path) -> list[str]:
    fig, axis = plt.subplots(figsize=(9, 6))
    for run_id in run_ids:
        trace = traces[run_id]
        phase = continuous_unwrap(series(trace, "P(BJ1|XBQ1)"))
        voltage = series(trace, "V(BJ1|XBQ1)")
        ref = min(range(len(trace.time)), key=lambda index: abs(trace.time[index] - 110e-12))
        x = [(phase[index] - phase[ref]) / (2.0 * 3.141592653589793) for index in range(len(phase)) if 110e-12 <= trace.time[index] < 200e-12]
        y = [voltage[index] * 1e3 for index in range(len(phase)) if 110e-12 <= trace.time[index] < 200e-12]
        axis.plot(x, y, linewidth=1.0, label=run_id)
    axis.set_xlabel("BJ1 relative phase progression from 110 ps (turns = rad/(2*pi))")
    axis.set_ylabel("V(BJ1|XBQ1) (mV)")
    axis.set_title(f"BJ1 phase-plane — {family} family; each case independently unwrapped")
    axis.grid(alpha=0.25)
    axis.legend()
    fig.tight_layout()
    fig.savefig(output, dpi=160)
    plt.close(fig)
    return ["P(BJ1|XBQ1)", "V(BJ1|XBQ1)"]


def source_decomposition(traces: dict[str, object], output: Path) -> list[str]:
    fig, axes = plt.subplots(4, 1, figsize=(12, 13), sharex=True)
    labels = [
        ("active I(L_SL|XBVM1)", "I(L_SL|XBVM1)", False),
        ("quiet total I_LSL2+I_LSL3+I_LSL4", "I_quiet_total", True),
        ("I(B_JSL1)", "I(B_JSL1)", False),
        ("I(B_JSL8)", "I(B_JSL8)", False),
    ]
    for axis, (title, label, quiet) in zip(axes, labels):
        for run_id, trace in traces.items():
            times, indices = x_window(trace, 110.0, 116.0)
            if quiet:
                values = tuple(sum(series(trace, f"I(L_SL|XBVM{i})")[index] for i in range(2, 5)) for index in range(trace.sample_count))
            else:
                values = series(trace, label)
            axis.plot(times, [values[index] * 1e6 for index in indices], linewidth=1.0, label=run_id)
        axis.set_title(title)
        axis.set_ylabel("uA")
        axis.grid(alpha=0.25)
    axes[-1].set_xlabel("time (ps), exact [110,116) stored-row zoom")
    axes[0].legend(ncol=3, fontsize=8)
    fig.suptitle("ARRAY source decomposition during early trigger; derived quiet total only", y=0.995)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    fig.savefig(output, dpi=160)
    plt.close(fig)
    return ["I(L_SL|XBVM1)", "I_quiet_total=sum(I(L_SL|XBVM2..4))", "I(B_JSL1)", "I(B_JSL8)"]


def comparison() -> int:
    qa_path = EXP / "analysis/visualization_qa_standalone.json"
    if not qa_path.is_file() or json.loads(qa_path.read_text(encoding="utf-8")).get("status") != "PASS":
        raise RuntimeError("standalone visualization QA must PASS before comparison rendering")
    traces = load_traces()
    entries: list[dict[str, object]] = []
    families = {"L1": ["L1_DOWN", "NOMINAL", "L1_UP"], "RJ1": ["NOMINAL", "RJ1_UP_05", "RJ1_UP_10"]}
    for family, run_ids in families.items():
        output = EXP / f"plots/compare_{family.lower()}" / f"{family}_FAMILY.png"
        signals = family_plot(traces, run_ids, family, output)
        html_path = output.with_suffix(".html")
        html_for_image(output, f"{family} parameter family comparison")
        entries.append(manifest_entry(stage="comparison", kind=f"{family.lower()}_family", run_ids=run_ids, input_path=raw_path(run_ids[0]), output_path=output, command="analysis/render_plots.py comparison; matplotlib exact-grid overlay", signals=signals, window=[0.0, 200.0], units={"current": "uA", "voltage": "mV", "phase": "independently unwrapped turns"}, transformation="independent phase unwrap for display; no interpolation/resampling/smoothing", source_paths=[raw_path(run_id) for run_id in run_ids]))
        entries.append(manifest_entry(stage="comparison", kind=f"{family.lower()}_family_html", run_ids=run_ids, input_path=raw_path(run_ids[0]), output_path=html_path, command="analysis/render_plots.py comparison; embedded PNG", signals=signals, window=[0.0, 200.0], units={"current": "uA", "voltage": "mV", "phase": "independently unwrapped turns"}, transformation="independent phase unwrap for display; no interpolation/resampling/smoothing", source_paths=[raw_path(run_id) for run_id in run_ids]))
        plane = EXP / "plots/mechanism" / f"BJ1_PHASE_PLANE_{family}.png"
        signals = phase_plane(traces, run_ids, family, plane)
        plane_html = plane.with_suffix(".html")
        html_for_image(plane, f"BJ1 phase-plane {family} family")
        entries.append(manifest_entry(stage="mechanism", kind=f"bj1_phase_plane_{family.lower()}", run_ids=run_ids, input_path=raw_path(run_ids[0]), output_path=plane, command="analysis/render_plots.py comparison; matplotlib phase-plane", signals=signals, window=[110.0, 200.0], units={"x": "turns=rad/(2*pi)", "y": "mV"}, transformation="independent continuous phase unwrap per case; no smoothing/resampling", source_paths=[raw_path(run_id) for run_id in run_ids]))
        entries.append(manifest_entry(stage="mechanism", kind=f"bj1_phase_plane_{family.lower()}_html", run_ids=run_ids, input_path=raw_path(run_ids[0]), output_path=plane_html, command="analysis/render_plots.py comparison; embedded PNG", signals=signals, window=[110.0, 200.0], units={"x": "turns=rad/(2*pi)", "y": "mV"}, transformation="independent continuous phase unwrap per case; no smoothing/resampling", source_paths=[raw_path(run_id) for run_id in run_ids]))
    source_output = EXP / "plots/mechanism/ARRAY_SOURCE_DECOMPOSITION_110_116ps.png"
    signals = source_decomposition(traces, source_output)
    source_html = source_output.with_suffix(".html")
    html_for_image(source_output, "ARRAY source decomposition 110-116 ps")
    entries.append(manifest_entry(stage="mechanism", kind="array_source_decomposition", run_ids=list(RUNS), input_path=raw_path("NOMINAL"), output_path=source_output, command="analysis/render_plots.py comparison; matplotlib source decomposition", signals=signals, window=[110.0, 116.0], units={"current": "uA"}, transformation="I_quiet_total samplewise sum; independent phase not used; no smoothing/resampling", source_paths=[raw_path(run_id) for run_id in RUNS]))
    entries.append(manifest_entry(stage="mechanism", kind="array_source_decomposition_html", run_ids=list(RUNS), input_path=raw_path("NOMINAL"), output_path=source_html, command="analysis/render_plots.py comparison; embedded PNG", signals=signals, window=[110.0, 116.0], units={"current": "uA"}, transformation="I_quiet_total samplewise sum; independent phase not used; no smoothing/resampling", source_paths=[raw_path(run_id) for run_id in RUNS]))

    standalone_manifest = json.loads((EXP / "analysis/standalone_visualization_manifest.json").read_text(encoding="utf-8"))
    final = {
        "schema": "qb-rj1-l1-local-sensitivity-visualization-manifest-v1",
        "experiment_id": EXP.name,
        "created_at_local": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "renderer_default": str(PLOT2),
        "standalone_options": "sep_comb dark -j 2pi",
        "standalone_entries": standalone_manifest["entries"],
        "comparison_entries": entries,
        "status": "PASS",
    }
    (EXP / "analysis/visualization_manifest.json").write_text(json.dumps(final, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "stage": "comparison", "comparison_entry_count": len(entries), "total_entry_count": len(final["standalone_entries"]) + len(entries)}, ensure_ascii=False))
    return 0


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in {"standalone", "comparison"}:
        raise SystemExit("usage: render_plots.py {standalone|comparison}")
    return standalone() if sys.argv[1] == "standalone" else comparison()


if __name__ == "__main__":
    raise SystemExit(main())
