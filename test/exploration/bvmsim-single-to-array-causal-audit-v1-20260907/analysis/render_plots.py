#!/usr/bin/env python3
"""Render the task-local comparison CSVs with the repository plot authority.

The derived CSVs intentionally keep phase in continuous unwrapped radians.
``josim-plot2.py -j 2pi`` performs the one display conversion to turns.  This
script refuses to overwrite an existing HTML or manifest so a rendered page
cannot silently drift away from its input data.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "scripts"))
from bvmtools.raw import read_csv  # noqa: E402


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
DATA_DIR = EXP / "plots/comparison/data"
PLOT_DIR = EXP / "plots/comparison"
PLOTTER = REPO / "scripts/josim-plot2.py"
MANIFEST = EXP / "plots/plot_manifest.json"

PAGE_TITLES = {
    "SINGLE_VS_ARRAY_OUTPUT": "Single vs array — sensing boundary",
    "SINGLE_VS_ARRAY_RLOOP_LOWER": "Single vs array — lower R-loop",
    "SINGLE_VS_ARRAY_RLOOP_UPPER": "Single vs array — upper R-loop",
    "SINGLE_VS_ARRAY_MEMORY": "Single vs array — memory state",
    "READ_BEFORE_STATE": "G0 vs G1 — same-time pre-READ state [62,70) ps",
    "ARRAY_PRE_READ_STATE": "G2 vs G3 vs G4 — same-time pre-READ state [101,110) ps",
    "DIVERGENCE_TIMELINE": "Single vs array — divergence timeline",
    "ACTIVE_VICTIM_CROSSTALK": "Active-victim shared-SL crosstalk",
    "QUIET_VICTIM_CROSSTALK": "Quiet-victim shared-SL crosstalk",
    "PASSIVE_VS_QB_CROSSTALK": "Passive vs QB-loaded crosstalk",
    "SINGLE_TO_ARRAY_BRIDGE_OVERVIEW": "G0 to G4 single-to-array bridge",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO.resolve()).as_posix()


def now_local() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def source_raw_hashes() -> dict[str, str]:
    source_manifest = EXP / "source/source_manifest.json"
    if not source_manifest.is_file():
        raise RuntimeError("analysis must run before plot rendering")
    manifest = json.loads(source_manifest.read_text(encoding="utf-8"))
    result: dict[str, str] = {}
    for name, record in manifest.get("files", {}).items():
        path = REPO / record["path"]
        if "raw" in name:
            if not path.is_file():
                raise RuntimeError(f"missing source raw: {path}")
            current = sha256(path)
            if current != record["sha256"]:
                raise RuntimeError(f"source raw hash changed before rendering: {path}")
            result[name] = current
    if not result:
        raise RuntimeError("source manifest contains no raw source hashes")
    return result


def validate_html(path: Path, labels: list[str], command: list[str]) -> dict[str, object]:
    if not path.is_file() or path.stat().st_size == 0:
        raise RuntimeError(f"empty or missing HTML: {path}")
    html = path.read_text(encoding="utf-8")
    lowered = html.casefold()
    axis_text = lowered.replace("\\u002f", "/")
    missing = [label for label in labels if label not in html]
    if missing:
        raise RuntimeError(f"HTML is missing plotted labels {missing[:3]}: {path}")
    # Plotly's embedded JavaScript contains generic strings such as
    # ``Unknown encoding``. Only reject an actual axis title set to Unknown.
    if '\"title\":{\"text\":\"unknown\"' in lowered:
        raise RuntimeError(f"HTML contains an Unknown axis/value marker: {path}")
    phase_labels = [label for label in labels if label.startswith("P")]
    phase_axis_ok = not phase_labels or "phase (turns) [rad/2pi]" in axis_text
    if phase_labels and not phase_axis_ok:
        raise RuntimeError(f"phase page lacks turns axis label: {path}")
    jump_ok = "-j" in command and command[command.index("-j") + 1] == "2pi"
    if phase_labels and not jump_ok:
        raise RuntimeError(f"phase page was not rendered with -j 2pi: {path}")
    if any("sfq" in label.casefold() for label in labels):
        raise RuntimeError(f"derived plot label uses SFQ as a count/unit: {path}")
    return {
        "exists_nonempty": True,
        "html_bytes": path.stat().st_size,
        "labels_present": True,
        "unknown_axis_absent": '\"title\":{\"text\":\"unknown\"' not in lowered,
        "phase_axis": "turns" if phase_labels else None,
        "phase_conversion": "rad/(2*pi) via -j 2pi" if phase_labels else None,
    }


def render_page(name: str, source_hashes: dict[str, str]) -> dict[str, object]:
    data_path = DATA_DIR / f"{name}.csv"
    html_path = PLOT_DIR / f"{name}.html"
    if not data_path.is_file():
        raise RuntimeError(f"missing derived plot data: {data_path}")
    if html_path.exists():
        raise RuntimeError(f"refusing to overwrite existing plot: {html_path}")
    trace = read_csv(data_path)
    if trace.duplicate_columns:
        raise RuntimeError(f"derived plot data has duplicate labels: {data_path}")
    labels = list(trace.headers[1:])
    if not labels:
        raise RuntimeError(f"derived plot data has no plotted columns: {data_path}")
    command = [
        sys.executable,
        str(PLOTTER),
        str(data_path),
        "-x",
        str(html_path),
        "-t",
        "sep_comb",
        "-c",
        "dark",
        "-j",
        "2pi",
        "-w",
        PAGE_TITLES[name],
        "-s",
        *labels,
    ]
    completed = subprocess.run(command, cwd=REPO, text=True, capture_output=True)
    if completed.returncode != 0:
        raise RuntimeError(
            f"plotter failed for {name} (exit {completed.returncode}):\n"
            f"stdout={completed.stdout}\nstderr={completed.stderr}"
        )
    html_qa = validate_html(html_path, labels, command)
    return {
        "name": name,
        "data": rel(data_path),
        "data_sha256": sha256(data_path),
        "html": rel(html_path),
        "html_sha256": sha256(html_path),
        "labels": labels,
        "source_raw_hashes_at_render": source_hashes,
        "command": command,
        "exit_code": completed.returncode,
        "qa": html_qa,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    if not args.write:
        raise SystemExit("use --write to render task-local comparison HTML")
    if MANIFEST.exists():
        raise RuntimeError(f"refusing to overwrite plot manifest: {MANIFEST}")
    if not PLOTTER.is_file():
        raise RuntimeError(f"missing plotter: {PLOTTER}")
    source_hashes = source_raw_hashes()
    pages = [render_page(name, source_hashes) for name in PAGE_TITLES]
    manifest = {
        "schema": "bvmsim-single-to-array-causal-audit-plot-manifest-v1",
        "created_at_local": now_local(),
        "experiment_id": EXP.name,
        "renderer": {"path": rel(PLOTTER), "sha256": sha256(PLOTTER)},
        "renderer_options": {"layout": "sep_comb", "color": "dark", "phase": "2pi"},
        "phase_semantics": "derived P columns are continuous unwrapped radians; plotter displays rad/(2*pi) turns",
        "source_raw_hashes_at_render": source_hashes,
        "comparison_html_is_acceptance_artifact": True,
        "pages": pages,
    }
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "page_count": len(pages), "manifest": rel(MANIFEST)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
