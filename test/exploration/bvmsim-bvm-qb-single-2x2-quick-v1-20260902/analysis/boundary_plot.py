#!/usr/bin/env python3
"""Generate the three focused Boundary plots from immutable A001 raw CSVs."""

from __future__ import annotations

import argparse
import hashlib
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
sys.path.insert(0, str(EXP / "analysis"))

from bvmtools.raw import read_csv  # noqa: E402
from plot import display_label, projected_csv  # noqa: E402


CONDITIONS = {
    "S0-R": EXP / "runs/A001/S0-R/raw.csv",
    "S1-R": EXP / "runs/A001/S1-R/raw.csv",
    "S0-J": EXP / "runs/A001/S0-J/raw.csv",
    "S1-J": EXP / "runs/A001/S1-J/raw.csv",
}


def selections(conditions: list[str], labels: list[str]) -> list[tuple[str, str, str]]:
    return [
        (display_label(condition, label), condition, label)
        for condition in conditions
        for label in labels
    ]


def boundary_selections() -> dict[str, tuple[str, list[tuple[str, str, str]]]]:
    b0 = selections(
        ["S0-J", "S1-J"],
        [
            "V(SL1)",
            "I(L_SL|XBVM1)",
            "V(BVMOUT)",
            "I(BVMOUT)",
            "P(BVMOUT)",
        ],
    ) + selections(["S0-R", "S1-R", "S0-J", "S1-J"], ["V(QBIN)"])
    b2 = selections(
        ["S0-J", "S1-J", "S1-R"],
        ["P(BJ2|XBQ1)", "V(BJ2|XBQ1)"],
    ) + selections(["S0-J", "S1-J"], ["V(QBIN)"])
    transport_phase = selections(["S0-J", "S1-J"], ["P(BJ2|XBQ1)"]) + selections(
        ["S0-J", "S1-J"], [f"P(B02|XJTL1_{stage})" for stage in range(1, 7)]
    )
    transport_voltage = selections(["S1-J"], ["V(BJ2|XBQ1)", "V(QBOUT)"]) + selections(
        ["S1-J"], [f"V(B02|XJTL1_{stage})" for stage in range(1, 7)]
    )
    return {
        "BOUNDARY_B0_QBIN.html": (
            "Boundary B0 — BVM sensing / SL transmission to QBin",
            b0,
        ),
        "BOUNDARY_B2_BJ2.html": (
            "Boundary B2 — READ-local QB BJ2 phase/voltage and load comparison",
            b2,
        ),
        "BOUNDARY_B3_TRANSPORT.html": (
            "Boundary B3 — BJ2 to JTL1..JTL6 output-facing B02 transport",
            transport_phase + transport_voltage,
        ),
    }


def render_page(
    output_name: str,
    title: str,
    selections_for_page: list[tuple[str, str, str]],
    traces: dict[str, object],
    temporary: Path,
    manifest: dict[str, object],
) -> None:
    output = EXP / "plots" / output_name
    projection, labels = projected_csv(output, traces, selections_for_page, temporary)
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
        raise RuntimeError(f"josim-plot2 failed for {output_name}:\n{completed.stdout}\n{completed.stderr}")
    manifest["pages"].append(
        {
            "output": str(output.relative_to(REPO)),
            "selected_labels": labels,
            "source_raw": sorted(str(path.relative_to(REPO)) for path in CONDITIONS.values()),
            "interpolation": "none",
            "renderer_command": [str(item) for item in command],
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
        "renderer_sha256": hashlib.sha256(PLOTTER.read_bytes()).hexdigest(),
        "raw_sha256": {
            condition: hashlib.sha256(path.read_bytes()).hexdigest()
            for condition, path in CONDITIONS.items()
        },
        "generation_command": [
            "python3",
            str((EXP / "analysis/boundary_plot.py").relative_to(REPO)),
            "--timestamp",
            timestamp,
        ],
        "pages": [],
        "description": "Boundary plots are descriptive projections; immutable A001 raw CSVs remain the evidence authority.",
    }
    with tempfile.TemporaryDirectory(prefix="bvmsim_boundary_plots_") as temporary_name:
        temporary = Path(temporary_name)
        for output_name, (title, page_selections) in boundary_selections().items():
            render_page(output_name, title, page_selections, traces, temporary, manifest)

    manifest_path = EXP / "analysis/boundary_plot_manifest.yaml"
    lines = [
        f"generated_at: {manifest['generated_at']}",
        f"profile: {manifest['profile']}",
        f"layout: {manifest['layout']}",
        f"color: {manifest['color']}",
        f"phase_option: {manifest['phase_option']}",
        f"renderer: {manifest['renderer']}",
        f"renderer_sha256: {manifest['renderer_sha256']}",
        f"generation_command: {json.dumps(manifest['generation_command'], ensure_ascii=False)}",
        "interpolation: none",
        "pages:",
    ]
    for page in manifest["pages"]:
        lines.append(f"  - output: {page['output']}")
        lines.append(f"    renderer_command: {json.dumps(page['renderer_command'], ensure_ascii=False)}")
        lines.append(f"    selected_labels: {json.dumps(page['selected_labels'], ensure_ascii=False)}")
        lines.append(f"    source_raw: {json.dumps(page['source_raw'])}")
    lines.append("raw_sha256:")
    for condition, digest in manifest["raw_sha256"].items():
        lines.append(f"  {condition}: {digest}")
    manifest_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"generated {len(manifest['pages'])} Boundary focused HTML pages")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
