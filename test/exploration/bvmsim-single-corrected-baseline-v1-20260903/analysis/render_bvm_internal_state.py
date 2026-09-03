#!/usr/bin/env python3
"""Render the complete BVM internal-state view for every corrected run."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from collections import OrderedDict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "scripts"))
from bvmtools.raw import read_csv  # noqa: E402


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
PLOTTER = REPO / "scripts/josim-plot2.py"
CONDITIONS = OrderedDict(
    (
        ("S0-R-CORRECTED", EXP / "runs/S0-R-CORRECTED/raw/run-01.csv"),
        ("S1-R-CORRECTED", EXP / "runs/S1-R-CORRECTED/raw/run-01.csv"),
        ("S0-J-CORRECTED", EXP / "runs/S0-J-CORRECTED/raw/run-01.csv"),
        ("S1-J-CORRECTED", EXP / "runs/S1-J-CORRECTED/raw/run-01.csv"),
        ("S0-J-CORRECTED-RERUN", EXP / "runs/S0-J-CORRECTED-RERUN/raw/run-01.csv"),
        ("S1-J-CORRECTED-RERUN", EXP / "runs/S1-J-CORRECTED-RERUN/raw/run-01.csv"),
    )
)
JUNCTIONS = ("JM1", "JM2", "JS1", "JS2")
KINDS = ("P", "V", "I")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def labels() -> list[str]:
    internal = [
        f"{kind}(B_{junction}|XBVM1)"
        for junction in JUNCTIONS
        for kind in KINDS
    ]
    sensing_line = ["V(SL1)", "I(L_PSL|XBVM1)", "I(L_SL|XBVM1)"]
    endpoints = [
        f"{kind}(B_{junction})"
        for junction in ("LD4_01", "LD4_11")
        for kind in KINDS
    ] + [f"{kind}(BVMOUT)" for kind in KINDS]
    return internal + sensing_line + endpoints


def verify_input(path: Path, selected: list[str]) -> dict[str, object]:
    trace = read_csv(path)
    if trace.duplicate_columns:
        raise RuntimeError(f"duplicate raw columns require explicit selection: {path}: {trace.duplicate_columns}")
    missing = [name for name in selected if name not in trace.headers]
    if missing:
        raise RuntimeError(f"{path}: missing labels: {missing}")
    return {
        "raw_sha256": sha256(path),
        "sample_count": trace.sample_count,
        "time_start": trace.time[0],
        "time_end": trace.time[-1],
        "header_count": len(trace.headers),
        "duplicate_columns": trace.duplicate_columns,
    }


def render(condition: str, source: Path, output: Path, selected: list[str], info: dict[str, object]) -> dict[str, object]:
    command = [
        sys.executable,
        str(PLOTTER),
        str(source),
        "-x",
        str(output),
        "-t",
        "sep_comb",
        "-c",
        "dark",
        "-j",
        "2pi",
        "-s",
        *selected,
        "-w",
        f"{condition} — complete BVM internal JJ state and SL boundary",
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
        "condition": condition,
        "path": str(output.relative_to(REPO)),
        "input": str(source.relative_to(REPO)),
        "input_sha256": info["raw_sha256"],
        "output_sha256": sha256(output),
        "title": f"{condition} — complete BVM internal JJ state and SL boundary",
        "labels": selected,
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
    selected = labels()
    inputs: dict[str, dict[str, object]] = {}
    plots: list[dict[str, object]] = []
    for condition, source in CONDITIONS.items():
        inputs[condition] = verify_input(source, selected)
        output = EXP / "plots" / "runs" / condition / "BVM_INTERNAL_STATE.html"
        plots.append(render(condition, source, output, selected, inputs[condition]))

    after = {condition: verify_input(source, selected) for condition, source in CONDITIONS.items()}
    before_hashes = {condition: info["raw_sha256"] for condition, info in inputs.items()}
    after_hashes = {condition: info["raw_sha256"] for condition, info in after.items()}
    if before_hashes != after_hashes:
        raise RuntimeError("raw hash changed during visualization")

    manifest = {
        "schema": "bvmsim-single-corrected-complete-bvm-internal-state-plot-manifest-v1",
        "purpose": "Add one complete BVM internal-state plot to every run",
        "renderer": str(PLOTTER.relative_to(REPO)),
        "renderer_sha256": sha256(PLOTTER),
        "plot_generator": str(Path(__file__).relative_to(REPO)),
        "plot_generator_sha256": sha256(Path(__file__)),
        "layout": "sep_comb",
        "color": "dark",
        "phase_jump": "2pi",
        "source_raw_policy": "existing raw reused; no simulation rerun; raw immutable",
        "included_junctions": {
            "bvm_internal": [f"{kind}(B_{junction}|XBVM1)" for junction in JUNCTIONS for kind in KINDS],
            "sensing_line_endpoints_available_in_raw": [
                f"{kind}(B_{junction})"
                for junction in ("LD4_01", "LD4_11")
                for kind in KINDS
            ] + [f"{kind}(BVMOUT)" for kind in KINDS],
        },
        "inputs_before": inputs,
        "inputs_after": after,
        "raw_unchanged": True,
        "plots": plots,
    }
    manifest_path = EXP / "analysis" / "bvm_internal_state_plot_manifest_v1.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"plots": len(plots), "runs": len(CONDITIONS), "raw_unchanged": True}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
