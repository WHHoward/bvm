#!/usr/bin/env python3
"""Generate compact classic plots from the four immutable A001 raw files."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
PLOTTER = REPO / "scripts/josim-plot2.py"
sys.path.insert(0, str(REPO / "scripts"))

from bvmtools.compare import exact_time_grid_identity  # noqa: E402
from bvmtools.raw import read_csv  # noqa: E402


CONDITIONS = {
    "S0-R": EXP / "runs/A001/S0-R/raw.csv",
    "S1-R": EXP / "runs/A001/S1-R/raw.csv",
    "S0-J": EXP / "runs/A001/S0-J/raw.csv",
    "S1-J": EXP / "runs/A001/S1-J/raw.csv",
}


def safe_column(trace, label):
    return trace.column(label)


def projected_csv(path: Path, traces: dict[str, object], selections: list[tuple[str, str, str]], temporary: Path) -> tuple[Path, list[str]]:
    """Write a unique-label projection without changing any raw evidence."""

    reference = next(iter(traces.values()))
    for trace in traces.values():
        if not exact_time_grid_identity(reference.time, trace.time):
            raise RuntimeError("plot projection requires exact shared time grids; no interpolation is allowed")
    labels = [display for display, _, _ in selections]
    if len(labels) != len(set(labels)):
        raise RuntimeError("plot projection has duplicate display labels")
    values = [(display, safe_column(traces[condition], source_label)) for display, condition, source_label in selections]
    projection = temporary / path.name.replace(".html", ".csv")
    with projection.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["time", *labels])
        for index, time_value in enumerate(reference.time):
            writer.writerow([f"{time_value:.17e}", *[f"{series[index]:.17e}" for _, series in values]])
    return projection, labels


def render(
    output_name: str,
    title: str,
    selections: list[tuple[str, str, str]],
    traces: dict[str, object],
    temporary: Path,
    manifest: dict[str, object],
) -> None:
    output = EXP / "plots" / output_name
    projection, labels = projected_csv(output, traces, selections, temporary)
    command = [
        sys.executable,
        str(PLOTTER),
        str(projection),
        "-x",
        str(output),
        "-t",
        "sep_comb",
        "-c",
        "dark",
        "-j",
        "2pi",
        "-w",
        title,
        "-s",
        *labels,
    ]
    completed = subprocess.run(command, cwd=REPO, check=False, capture_output=True, text=True)
    if completed.returncode != 0:
        raise RuntimeError(
            f"josim-plot2 failed for {output_name}:\n{completed.stdout}\n{completed.stderr}"
        )
    manifest["pages"].append(
        {
            "output": str(output.relative_to(REPO)),
            "renderer": str(PLOTTER.relative_to(REPO)),
            "renderer_command": [str(item) for item in command],
            "source_raw": sorted(str(path.relative_to(REPO)) for path in CONDITIONS.values()),
            "selected_display_labels": labels,
            "interpolation": "none",
        }
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--timestamp", default=None)
    args = parser.parse_args()
    timestamp = args.timestamp or datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    traces = {condition: read_csv(path) for condition, path in CONDITIONS.items()}
    (EXP / "plots").mkdir(parents=True, exist_ok=True)
    manifest: dict[str, object] = {
        "generated_at": timestamp,
        "profile": "CLASSIC_LOCKED",
        "layout": "sep_comb",
        "color": "dark",
        "phase_option": "2pi",
        "renderer": str(PLOTTER.relative_to(REPO)),
        "renderer_sha256": __import__("hashlib").sha256(PLOTTER.read_bytes()).hexdigest(),
        "raw_sha256": {
            condition: __import__("hashlib").sha256(path.read_bytes()).hexdigest()
            for condition, path in CONDITIONS.items()
        },
        "pages": [],
        "description": "Derived projections are temporary; raw CSVs remain the only waveform authority.",
    }
    with tempfile.TemporaryDirectory(prefix="bvmsim_bvm_qb_plots_") as temporary_name:
        temporary = Path(temporary_name)
        all_conditions = list(CONDITIONS)
        overview_selection = [
            (f"{condition}::V(BVMOUT)", condition, "V(BVMOUT)")
            for condition in all_conditions
        ] + [
            (f"{condition}::V(QBIN)", condition, "V(QBIN)")
            for condition in all_conditions
        ] + [
            (f"{condition}::P(BJ2|XBQ1)", condition, "P(BJ2|XBQ1)")
            for condition in all_conditions
        ] + [
            (f"{condition}::V(QBOUT)", condition, "V(QBOUT)")
            for condition in all_conditions
        ]
        render(
            "RESULT_OVERVIEW.html",
            "Single BVMSim BVM -> QB matched 2x2 Quick — overview",
            overview_selection,
            traces,
            temporary,
            manifest,
        )

        interface_selection = []
        for condition in all_conditions:
            for label in ("P(BVMOUT)", "V(BVMOUT)", "I(BVMOUT)", "V(QBIN)"):
                interface_selection.append((f"{condition}::{label}", condition, label))
        render(
            "RESULT_BVM_INTERFACE.html",
            "BVM sensing-line terminal and QB input — matched 2x2",
            interface_selection,
            traces,
            temporary,
            manifest,
        )

        qb_selection = []
        for condition in all_conditions:
            for label in (
                "P(BJS|XBQ1)",
                "P(BJ1|XBQ1)",
                "P(BJ2|XBQ1)",
                "V(BJS|XBQ1)",
                "V(BJ1|XBQ1)",
                "V(BJ2|XBQ1)",
            ):
                qb_selection.append((f"{condition}::{label}", condition, label))
        render(
            "RESULT_QB_INTERNAL.html",
            "QB internal phase and voltage — matched 2x2",
            qb_selection,
            traces,
            temporary,
            manifest,
        )

        jtl_conditions = ("S0-J", "S1-J")
        transport_voltage = []
        transport_phase = []
        for condition in jtl_conditions:
            transport_voltage.append((f"{condition}::V(BJ2|XBQ1)", condition, "V(BJ2|XBQ1)"))
            transport_phase.append((f"{condition}::P(BJ2|XBQ1)", condition, "P(BJ2|XBQ1)"))
            for stage in range(1, 7):
                label_v = f"V(B01|XJTL1_{stage})"
                label_p = f"P(B01|XJTL1_{stage})"
                transport_voltage.append((f"{condition}::{label_v}", condition, label_v))
                transport_phase.append((f"{condition}::{label_p}", condition, label_p))
        render(
            "RESULT_TRANSPORT_VOLTAGE.html",
            "QB BJ2 -> JTL1..JTL6 voltage transport — J conditions",
            transport_voltage,
            {key: traces[key] for key in jtl_conditions},
            temporary,
            manifest,
        )
        render(
            "RESULT_TRANSPORT_PHASE.html",
            "QB BJ2 -> JTL1..JTL6 phase transport (/2pi turns) — J conditions",
            transport_phase,
            {key: traces[key] for key in jtl_conditions},
            temporary,
            manifest,
        )

    manifest_path = EXP / "analysis/plot_manifest.yaml"
    lines = [
        f"generated_at: {manifest['generated_at']}",
        f"profile: {manifest['profile']}",
        f"layout: {manifest['layout']}",
        f"color: {manifest['color']}",
        f"phase_option: {manifest['phase_option']}",
        f"renderer: {manifest['renderer']}",
        f"renderer_sha256: {manifest['renderer_sha256']}",
        "interpolation: none",
        "pages:",
    ]
    for page in manifest["pages"]:
        lines.append(f"  - output: {page['output']}")
        lines.append(f"    renderer_command: {json.dumps(page['renderer_command'], ensure_ascii=False)}")
        lines.append(f"    selected_labels: {json.dumps(page['selected_display_labels'], ensure_ascii=False)}")
        lines.append(f"    source_raw: {json.dumps(page['source_raw'])}")
    lines.append("raw_sha256:")
    for condition, digest in manifest["raw_sha256"].items():
        lines.append(f"  {condition}: {digest}")
    manifest_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"generated {len(manifest['pages'])} focused classic HTML pages")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
