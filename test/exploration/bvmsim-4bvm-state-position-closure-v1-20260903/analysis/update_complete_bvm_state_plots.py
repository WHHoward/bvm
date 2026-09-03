#!/usr/bin/env python3
"""Refresh the existing PHASE-B BVM state plots with every BVM-cell JJ probe."""

from __future__ import annotations

import csv
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "scripts"))
from bvmtools.raw import read_csv  # noqa: E402


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
PLOTTER = REPO / "scripts/josim-plot2.py"
STATES = ("0000", "1000", "0100", "0010", "0001", "1111")
JUNCTIONS = ("JM1", "JM2", "JS1", "JS2")
KINDS = ("P", "V", "I")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def raw_path(state: str) -> Path:
    return EXP / "runs" / state / "raw.csv"


def csv_header(path: Path) -> list[str]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return next(csv.reader(handle))


def bvm_jj_pvi_labels() -> list[str]:
    return [
        f"{kind}(B_{junction}|XBVM{number})"
        for number in range(1, 5)
        for junction in JUNCTIONS
        for kind in KINDS
    ]


def labels_for(view: str) -> list[str]:
    labels = bvm_jj_pvi_labels()
    if view == "BVM_STATE":
        labels += [
            *(f"V(SL{number})" for number in range(1, 5)),
            *(f"I(L_SL|XBVM{number})" for number in range(1, 5)),
        ]
    elif view != "BVM_INTERNAL_PVI":
        raise ValueError(f"unknown view: {view}")
    return labels


def verify_input(path: Path, labels: list[str]) -> dict[str, object]:
    trace = read_csv(path)
    if trace.duplicate_columns:
        raise RuntimeError(f"duplicate raw columns require explicit selection: {path}: {trace.duplicate_columns}")
    missing = [label for label in labels if label not in trace.headers]
    if missing:
        raise RuntimeError(f"{path}: missing labels: {missing}")
    return {
        "raw_sha256": sha256(path),
        "sample_count": trace.sample_count,
        "time_start": trace.time[0],
        "time_end": trace.time[-1],
        "header_count": len(csv_header(path)),
        "duplicate_columns": trace.duplicate_columns,
    }


def render(path: Path, output: Path, title: str, labels: list[str], input_info: dict[str, object]) -> dict[str, object]:
    previous_sha = sha256(output) if output.exists() else None
    command = [
        sys.executable,
        str(PLOTTER),
        str(path),
        "-x",
        str(output),
        "-t",
        "sep_comb",
        "-c",
        "dark",
        "-j",
        "2pi",
        "-s",
        *labels,
        "-w",
        title,
    ]
    output.parent.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(command, cwd=REPO, capture_output=True, text=True)
    if completed.returncode != 0:
        raise RuntimeError(
            f"josim-plot2 failed: exit={completed.returncode}\n"
            f"stdout={completed.stdout}\nstderr={completed.stderr}"
        )
    html = output.read_text(encoding="utf-8", errors="replace")
    if "<html" not in html.lower():
        raise RuntimeError(f"not an HTML plot: {output}")
    if re.search(r'"title":\{"text":"Unknown"\}', html):
        raise RuntimeError(f"plot contains an Unknown axis: {output}")
    if "Phase (turns)" not in html or "2pi" not in html:
        raise RuntimeError(f"phase unit QA failed: {output}")
    return {
        "path": str(output.relative_to(REPO)),
        "input": str(path.relative_to(REPO)),
        "input_sha256": input_info["raw_sha256"],
        "previous_output_sha256": previous_sha,
        "output_sha256": sha256(output),
        "title": title,
        "labels": labels,
        "command": command,
        "exit_code": completed.returncode,
        "qa": {
            "html": True,
            "unknown_axis_absent": True,
            "phase_display": "rad/(2pi) turns",
            "classic_renderer": True,
        },
    }


def main() -> int:
    views = ("BVM_STATE", "BVM_INTERNAL_PVI")
    labels = {view: labels_for(view) for view in views}
    raw_before: dict[str, dict[str, object]] = {}
    plots: list[dict[str, object]] = []
    for state in STATES:
        source = raw_path(state)
        raw_before[state] = verify_input(source, labels["BVM_STATE"])
        for view in views:
            title = (
                f"PHASE B {state} — {view}: all four BVM internal JJ P/V/I"
                if view == "BVM_INTERNAL_PVI"
                else f"PHASE B {state} — {view}: all four BVM internal JJ P/V/I plus SL telemetry"
            )
            output = EXP / "plots" / "runs" / state / f"{view}.html"
            plots.append(render(source, output, title, labels[view], raw_before[state]))

    raw_after = {state: verify_input(raw_path(state), labels["BVM_STATE"]) for state in STATES}
    if {state: info["raw_sha256"] for state, info in raw_before.items()} != {
        state: info["raw_sha256"] for state, info in raw_after.items()
    }:
        raise RuntimeError("raw hash changed during visualization")

    manifest = {
        "schema": "bvmsim-4bvm-complete-bvm-state-plot-manifest-v1",
        "purpose": "Update existing per-run BVM_STATE and BVM_INTERNAL_PVI views only",
        "renderer": str(PLOTTER.relative_to(REPO)),
        "renderer_sha256": sha256(PLOTTER),
        "plot_generator": str(Path(__file__).relative_to(REPO)),
        "plot_generator_sha256": sha256(Path(__file__)),
        "layout": "sep_comb",
        "color": "dark",
        "phase_jump": "2pi",
        "source_raw_policy": "existing raw.csv reused; no simulation rerun; raw immutable",
        "bvm_internal_junctions": [
            f"{kind}(B_{junction}|XBVM{number})"
            for number in range(1, 5)
            for junction in JUNCTIONS
            for kind in KINDS
        ],
        "raw_before": raw_before,
        "raw_after": raw_after,
        "raw_unchanged": True,
        "plots": plots,
    }
    manifest_path = EXP / "analysis" / "plot_manifest_bvm_state_complete_v1.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"plots": len(plots), "states": len(STATES), "raw_unchanged": True}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
