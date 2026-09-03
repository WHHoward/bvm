#!/usr/bin/env python3
"""Render one compact SL-endpoint view for each probe-extension run."""

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
PLOT_ROOT = EXP / "plots/sl_endpoints"
MANIFEST = EXP / "analysis/plot_manifest_sl_endpoints_v1.json"
INDEX = PLOT_ROOT / "INDEX.html"
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
        raise RuntimeError(f"refusing to overwrite visualization artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def labels() -> list[str]:
    endpoint = list(flatten_probe_labels(historical_sensing_line_endpoint_probes()))
    terminal = [
        "P(BVMOUT)", "V(BVMOUT)", "I(BVMOUT)",
        "V(QBIN)", "V(QBOUT)", "I(LIN|XBQ1)",
    ]
    return endpoint + terminal


def render(state: str, selected: list[str]) -> dict[str, object]:
    raw = RAW_ROOT / state / "raw.csv"
    trace = read_csv(raw)
    missing = [label for label in selected if label not in trace.headers]
    if missing:
        raise RuntimeError(f"{raw}: missing labels {missing}")
    output = PLOT_ROOT / state / "BVMOUT_QB_INPUT_SL_ENDPOINTS.html"
    command = [
        sys.executable,
        str(RENDERER),
        str(raw),
        "-x", str(output),
        "-t", "sep_comb",
        "-c", "dark",
        "-j", "2pi",
        "-s", *selected,
        "-w", f"PHASE B {state} — BVMout/QB input-output + all BVM SL endpoints",
    ]
    output.parent.mkdir(parents=True, exist_ok=True)
    if not output.exists():
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
        "sha256": digest(output),
        "input": str(raw.relative_to(REPO)),
        "labels": selected,
        "command": command,
        "phase_unit_check": "PASS",
    }


def write_index(records: list[dict[str, object]]) -> None:
    links = []
    for record in records:
        state = str(record["state"])
        links.append(f'<li><a href="{state}/BVMOUT_QB_INPUT_SL_ENDPOINTS.html">{state} — BVMout/QB input-output + all BVM SL endpoints</a></li>')
    content = (
        "<!doctype html>\n<html><head><meta charset=\"utf-8\"><title>SL endpoint plots</title></head><body>\n"
        "<h1>PHASE B — all BVM SL endpoint plots</h1>\n<ul>\n"
        + "\n".join(links)
        + "\n</ul>\n<p>P(...) uses JoSIM rad/(2*pi), rendered as phase turns. These plots are descriptive and use probe-extension raw files.</p>\n</body></html>\n"
    )
    write_once(INDEX, content)


def main() -> int:
    selected = labels()
    before = {state: digest(RAW_ROOT / state / "raw.csv") for state in STATES}
    records = [render(state, selected) for state in STATES]
    after = {state: digest(RAW_ROOT / state / "raw.csv") for state in STATES}
    if before != after:
        raise RuntimeError("probe-extension raw hash changed during visualization")
    manifest = {
        "schema": "bvmsim-4bvm-sl-endpoint-plot-manifest-v1",
        "renderer": str(RENDERER.relative_to(REPO)),
        "renderer_sha256": digest(RENDERER),
        "plot_driver": str(Path(__file__).relative_to(REPO)),
        "plot_driver_sha256": digest(Path(__file__)),
        "layout": "sep_comb",
        "color": "dark",
        "phase_jump": "2pi",
        "raw_sha256_before": before,
        "raw_sha256_after": after,
        "raw_unchanged": before == after,
        "plots": records,
    }
    write_once(MANIFEST, json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    write_index(records)
    print(json.dumps({"plots": len(records), "raw_unchanged": before == after}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
