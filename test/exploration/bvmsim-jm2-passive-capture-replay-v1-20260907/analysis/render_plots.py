#!/usr/bin/env python3
"""Render focused HTML waveform pages and perform visualization QA."""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
PLOTTER = REPO / "scripts/josim-plot2.py"
PLOT_INPUTS = EXP / "analysis/plot_inputs.json"
RAW_CASES = {
    "SINGLE_PASSIVE": EXP / "runs/single_passive/raw.csv",
    "ARRAY_PASSIVE": EXP / "runs/array_passive/raw.csv",
    "REPLAY_SINGLE": EXP / "runs/replay_single/raw.csv",
    "REPLAY_ARRAY": EXP / "runs/replay_array/raw.csv",
}
PAGE_TITLES = {
    "SINGLE_PASSIVE": "SINGLE_PASSIVE standalone | WRITE0 50-61 ps | ZERO_STATE_READ_CONTROL 70-81 ps | WRITE1 90-101 ps | FINAL READ 110-121 ps",
    "ARRAY_PASSIVE": "ARRAY_PASSIVE standalone | WRITE0 50-61 ps | ZERO_STATE_READ_CONTROL 70-81 ps | WRITE1 90-101 ps | FINAL READ 110-121 ps",
    "REPLAY_SINGLE": "REPLAY_SINGLE standalone | QB/JTL current replay | WRITE0 50-61 ps | ZERO_STATE_READ_CONTROL 70-81 ps | WRITE1 90-101 ps | FINAL READ 110-121 ps",
    "REPLAY_ARRAY": "REPLAY_ARRAY standalone | QB/JTL current replay | WRITE0 50-61 ps | ZERO_STATE_READ_CONTROL 70-81 ps | WRITE1 90-101 ps | FINAL READ 110-121 ps",
    "PASSIVE_SOURCE_COMPARE": "Passive source comparison | WRITE0 50-61 ps | ZERO_STATE_READ_CONTROL 70-81 ps | WRITE1 90-101 ps | FINAL READ 110-121 ps",
    "ARRAY_CURRENT_BALANCE": "ARRAY_PASSIVE shared-SL current balance | WRITE0 / ZERO_STATE_READ_CONTROL / WRITE1 / FINAL READ",
    "QB_REPLAY_COMPARE": "Current-only QB replay | REPLAY_SINGLE vs REPLAY_ARRAY | WRITE0 / ZERO_STATE_READ_CONTROL / WRITE1 / FINAL READ",
    "JTL_REPLAY_COMPARE": "JTL replay endpoints | REPLAY_SINGLE vs REPLAY_ARRAY | WRITE0 / ZERO_STATE_READ_CONTROL / WRITE1 / FINAL READ",
    "READ_WRITE_CONTROLS": "Read/write controls | WRITE0 50-61 ps | ZERO_STATE_READ_CONTROL 70-81 ps | WRITE1 90-101 ps | FINAL READ 110-121 ps",
}
RUN_PAGES = {
    "SINGLE_PASSIVE": {
        "input": "test/exploration/bvmsim-jm2-passive-capture-replay-v1-20260907/runs/single_passive/raw.csv",
        "labels": ["I(B_JSL8)", "V(SL1)", "I(I_WL1)", "I(I_BL1)", "I(I_SE1)"],
    },
    "ARRAY_PASSIVE": {
        "input": "test/exploration/bvmsim-jm2-passive-capture-replay-v1-20260907/runs/array_passive/raw.csv",
        "labels": ["I(B_JSL8)", "V(COMMON_SL)", "I(I_WL1)", "I(I_BL1)", "I(I_SE1)"],
    },
    "REPLAY_SINGLE": {
        "input": "test/exploration/bvmsim-jm2-passive-capture-replay-v1-20260907/runs/replay_single/raw.csv",
        "labels": ["I(I_REPLAY)", "V(QBIN)", "P(BJ1|XBQ1)", "P(BJ2|XBQ1)", "I(R_TERM)"],
    },
    "REPLAY_ARRAY": {
        "input": "test/exploration/bvmsim-jm2-passive-capture-replay-v1-20260907/runs/replay_array/raw.csv",
        "labels": ["I(I_REPLAY)", "V(QBIN)", "P(BJ1|XBQ1)", "P(BJ2|XBQ1)", "I(R_TERM)"],
    },
}
PHASE_PAGES = {"QB_REPLAY_COMPARE", "JTL_REPLAY_COMPARE", "REPLAY_SINGLE", "REPLAY_ARRAY"}
CONTROL_LABELS = (
    "I(I_WL1)",
    "I(I_BL1)",
    "I(I_SE1)",
    "I(I_WL2)",
    "I(I_BL2)",
    "I(I_SE2)",
    "I(I_WL3)",
    "I(I_BL3)",
    "I(I_SE3)",
    "I(I_WL4)",
    "I(I_BL4)",
    "I(I_SE4)",
)


def now_local() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def write_once(path: Path, content: str) -> None:
    if path.exists():
        if path.read_text(encoding="utf-8") == content:
            return
        raise RuntimeError(f"refusing to overwrite existing artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def csv_headers(path: Path) -> list[str]:
    with path.open(newline="", encoding="utf-8") as handle:
        header = next(csv.reader(handle))
    if not header or header[0] != "time":
        raise RuntimeError(f"plot input does not begin with time column: {path}")
    if len(header) != len(set(header)):
        raise RuntimeError(f"plot input has duplicate labels: {path}")
    return header


def main() -> int:
    plot_inputs = json.loads(PLOT_INPUTS.read_text(encoding="utf-8"))
    failures: list[str] = []
    raw_before = {name: sha256(path) for name, path in RAW_CASES.items()}
    pages: dict[str, object] = {}
    plots_dir = EXP / "plots"
    for name, title in PAGE_TITLES.items():
        if name in RUN_PAGES:
            run_spec = RUN_PAGES[name]
            input_path = REPO / run_spec["input"]
            registered_labels = run_spec["labels"]
            source_kind = "raw_run"
        elif name in plot_inputs:
            input_path = REPO / plot_inputs[name]["path"]
            registered_labels = plot_inputs[name]["labels"]
            source_kind = "derived_comparison_csv"
        else:
            failures.append(f"missing registered plot input: {name}")
            continue
        labels = csv_headers(input_path)[1:]
        if name in RUN_PAGES:
            labels = registered_labels
        if not set(labels).issubset(set(csv_headers(input_path)[1:])):
            failures.append(f"{name}: requested standalone labels are absent from raw header")
        if name not in RUN_PAGES and labels != registered_labels:
            failures.append(f"{name}: header differs from registered plot-input labels")
        output_path = plots_dir / f"{name}.html"
        command = [
            sys.executable,
            str(PLOTTER),
            str(input_path),
            "-x",
            str(output_path),
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
        reused_existing = output_path.exists()
        completed = (
            subprocess.CompletedProcess(command, 0, "", "")
            if reused_existing
            else subprocess.run(command, cwd=REPO, text=True, capture_output=True)
        )
        if completed.returncode != 0:
            failures.append(f"{name}: plotter exit {completed.returncode}: {completed.stderr[-500:]}")
            continue
        if not output_path.is_file() or output_path.stat().st_size == 0:
            failures.append(f"{name}: missing or empty HTML output")
            continue
        html = output_path.read_text(encoding="utf-8", errors="replace")
        # Plotly serializes slash characters in JSON as ``\\u002f``.  Decode
        # that harmless transport escape before checking labels that are
        # visible in the browser.
        visible_html = html.replace("\\u002f", "/")
        missing_html_labels = [label for label in labels if label not in visible_html]
        if missing_html_labels:
            failures.append(f"{name}: labels absent from HTML {missing_html_labels}")
        if '"text":"Unknown"' in visible_html or '"title":{"text":"Unknown"' in visible_html:
            failures.append(f"{name}: HTML contains Unknown axis/label")
        if any(term in html.lower() for term in ("sfq count", "event count")):
            failures.append(f"{name}: HTML contains prohibited event-count wording")
        if name in PHASE_PAGES and "Phase (turns) [rad/2pi]" not in visible_html:
            failures.append(f"{name}: 2pi phase-axis conversion label missing")
        if name == "READ_WRITE_CONTROLS":
            missing_controls = [label for label in CONTROL_LABELS if label not in visible_html]
            if missing_controls:
                failures.append(f"{name}: control labels absent from HTML {missing_controls}")
            for protocol_label in ("WRITE0", "ZERO_STATE_READ_CONTROL", "WRITE1", "FINAL READ"):
                if protocol_label not in visible_html:
                    failures.append(f"{name}: protocol label absent from HTML: {protocol_label}")
        pages[name] = {
            "input": input_path.relative_to(REPO).as_posix(),
            "input_sha256": sha256(input_path),
            "source_kind": source_kind,
            "output": output_path.relative_to(REPO).as_posix(),
            "output_sha256": sha256(output_path),
            "output_bytes": output_path.stat().st_size,
            "labels": labels,
            "title": title,
            "command": command,
            "returncode": completed.returncode,
            "reused_existing_output": reused_existing,
            "phase_axis_conversion": "rad/(2*pi) displayed as turns" if name in PHASE_PAGES else None,
            "read_write_protocol_labels_visible": name == "READ_WRITE_CONTROLS"
            and all(label in visible_html for label in ("WRITE0", "ZERO_STATE_READ_CONTROL", "WRITE1", "FINAL READ")),
        }

    raw_after = {name: sha256(path) for name, path in RAW_CASES.items()}
    raw_unchanged = raw_before == raw_after
    if not raw_unchanged:
        failures.append("raw hash changed during plot rendering")
    required_pages = set(PAGE_TITLES)
    if set(pages) != required_pages:
        failures.append(f"rendered page set differs: {sorted(set(pages) ^ required_pages)}")
    record = {
        "schema": "jm2-passive-capture-replay-visualization-qa-v1",
        "experiment_id": EXP.name,
        "created_at_local": now_local(),
        "status": "PASS" if not failures else "FAIL",
        "renderer": {
            "path": PLOTTER.relative_to(REPO).as_posix(),
            "sha256": sha256(PLOTTER),
            "type": "sep_comb",
            "color": "dark",
            "phase_jump_option": "2pi",
        },
        "raw_hashes_before": raw_before,
        "raw_hashes_after": raw_after,
        "raw_unchanged": raw_unchanged,
        "pages": pages,
        "read_write_page": "plots/READ_WRITE_CONTROLS.html",
        "standalone_run_pages": {
            name: f"plots/{name}.html" for name in RUN_PAGES
        },
        "read_write_protocol": [
            "WRITE0 50-61 ps",
            "ZERO_STATE_READ_CONTROL 70-81 ps",
            "WRITE1 90-101 ps",
            "FINAL READ 110-121 ps",
        ],
        "failures": failures,
    }
    write_once(EXP / "analysis/viz_qa.json", json.dumps(record, indent=2, ensure_ascii=False) + "\n")
    manifest = {
        "schema": "jm2-passive-capture-replay-plot-manifest-v1",
        "experiment_id": EXP.name,
        "created_at_local": now_local(),
        "source_raw_hashes": raw_after,
        "derived_plot_inputs": plot_inputs,
        "standalone_run_pages": RUN_PAGES,
        "pages": pages,
        "visualization_is_descriptive": True,
        "phase_rule": "P(...) raw radians; renderer -j 2pi displays rad/(2*pi) as turns",
        "read_write_controls_included": True,
    }
    write_once(EXP / "plots/plot_manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"status": record["status"], "pages": sorted(pages), "read_write": "plots/READ_WRITE_CONTROLS.html", "failures": failures}, ensure_ascii=False))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
