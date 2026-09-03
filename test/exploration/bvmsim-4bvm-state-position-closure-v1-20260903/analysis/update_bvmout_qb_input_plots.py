#!/usr/bin/env python3
"""Update the six existing BVMOUT_QB_INPUT.html files in place."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
EXP = HERE.parent
RAW_ROOT = EXP / "runs_sl_endpoints"
PLOT_ROOT = EXP / "plots/runs"
MANIFEST = EXP / "analysis/plot_manifest_bvmout_qb_input_v2.json"
RENDERER = REPO / "scripts/josim-plot2.py"
STATES = ("0000", "1000", "0100", "0010", "0001", "1111")

sys.path.insert(0, str(REPO / "scripts"))
from bvmtools.probes import flatten_probe_labels  # noqa: E402
from bvmtools.raw import read_csv  # noqa: E402
from bvmtools.sl_probes import historical_sensing_line_endpoint_probes  # noqa: E402


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_once(path: Path, content: str) -> None:
    if path.exists():
        if path.read_text(encoding="utf-8") == content:
            return
        raise RuntimeError(f"refusing to overwrite update manifest: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def selected_labels() -> list[str]:
    return list(flatten_probe_labels(historical_sensing_line_endpoint_probes())) + [
        "P(BVMOUT)", "V(BVMOUT)", "I(BVMOUT)",
        "V(QBIN)", "V(QBOUT)", "I(LIN|XBQ1)",
    ]


def update_one(state: str, selected: list[str]) -> dict[str, object]:
    raw = RAW_ROOT / state / "raw.csv"
    output = PLOT_ROOT / state / "BVMOUT_QB_INPUT.html"
    trace = read_csv(raw)
    if trace.duplicate_columns:
        raise RuntimeError(f"{raw}: duplicate columns {trace.duplicate_columns}")
    missing = [label for label in selected if label not in trace.headers]
    if missing:
        raise RuntimeError(f"{raw}: missing labels {missing}")
    if not output.is_file():
        raise RuntimeError(f"expected existing run visualization not found: {output}")
    previous = digest(output)
    command = [
        sys.executable,
        str(RENDERER),
        str(raw),
        "-x", str(output),
        "-t", "sep_comb",
        "-c", "dark",
        "-j", "2pi",
        "-s", *selected,
        "-w", f"PHASE B {state} — BVMout/QB input-output + all BVM SL endpoint junctions",
    ]
    completed = subprocess.run(command, cwd=REPO, text=True, capture_output=True, check=False)
    if completed.returncode != 0:
        raise RuntimeError(
            f"plot2 failed for {output}: exit={completed.returncode}\n"
            f"stdout={completed.stdout}\nstderr={completed.stderr}"
        )
    html = output.read_text(encoding="utf-8", errors="replace")
    if "<html" not in html.lower():
        raise RuntimeError(f"not HTML: {output}")
    if re.search(r'"title":\{"text":"Unknown"', html):
        raise RuntimeError(f"Unknown axis label: {output}")
    if "Phase (turns)" not in html or "2pi" not in html:
        raise RuntimeError(f"phase unit label missing: {output}")
    return {
        "state": state,
        "path": str(output.relative_to(REPO)),
        "input": str(raw.relative_to(REPO)),
        "previous_sha256": previous,
        "sha256": digest(output),
        "labels": selected,
        "command": command,
        "phase_unit_check": "PASS",
    }


def main() -> int:
    selected = selected_labels()
    before = {state: digest(RAW_ROOT / state / "raw.csv") for state in STATES}
    records = [update_one(state, selected) for state in STATES]
    after = {state: digest(RAW_ROOT / state / "raw.csv") for state in STATES}
    if before != after:
        raise RuntimeError("raw hash changed during existing-plot update")
    manifest = {
        "schema": "bvmsim-4bvm-bvmout-qb-input-plot-update-v2",
        "purpose": "replace the six existing BVMOUT_QB_INPUT.html visualizations with added all-BVM SL endpoints",
        "renderer": str(RENDERER.relative_to(REPO)),
        "renderer_sha256": digest(RENDERER),
        "layout": "sep_comb",
        "color": "dark",
        "phase_jump": "2pi",
        "input_scope": "probe-extension raw only; no raw overwrite",
        "raw_sha256_before": before,
        "raw_sha256_after": after,
        "raw_unchanged": before == after,
        "plot_count": len(records),
        "plots": records,
    }
    write_once(MANIFEST, json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"plots_updated": len(records), "raw_unchanged": before == after}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
