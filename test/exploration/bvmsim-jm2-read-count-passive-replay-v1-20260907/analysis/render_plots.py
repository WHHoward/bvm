#!/usr/bin/env python3
"""Render per-run and required aggregate JoSIM waveform pages with QA."""

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
BASELINE = REPO / "test/exploration/bvmsim-jm2-passive-capture-replay-v1-20260907"
PLOTTER = REPO / "scripts/josim-plot2.py"
SUMMARY_RENDERER = EXP / "analysis/render_summary.py"
PLOT_INPUTS = EXP / "analysis/plot_inputs.json"
RAW_CASES = {
    "N1_PASSIVE": BASELINE / "runs/array_passive/raw.csv",
    "N2_PASSIVE": EXP / "runs/n2_passive/raw.csv",
    "N3_PASSIVE": EXP / "runs/n3_passive/raw.csv",
    "N4_PASSIVE": EXP / "runs/n4_passive/raw.csv",
    "N1_REPLAY": BASELINE / "runs/replay_array/raw.csv",
    "N2_REPLAY": EXP / "runs/n2_replay/raw.csv",
    "N3_REPLAY": EXP / "runs/n3_replay/raw.csv",
    "N4_REPLAY": EXP / "runs/n4_replay/raw.csv",
}
RUN_PAGES = {
    "N1_PASSIVE": {"input": RAW_CASES["N1_PASSIVE"], "labels": ["I(B_JSL8)", "V(COMMON_SL)", "I(I_WL1)", "I(I_BL1)", "I(I_SE1)"], "source_kind": "immutable_N1_reference_raw"},
    "N2_PASSIVE": {"input": RAW_CASES["N2_PASSIVE"], "labels": ["I(B_JSL8)", "V(COMMON_SL)", "I(I_WL1)", "I(I_BL1)", "I(I_SE1)"], "source_kind": "new_run_raw"},
    "N3_PASSIVE": {"input": RAW_CASES["N3_PASSIVE"], "labels": ["I(B_JSL8)", "V(COMMON_SL)", "I(I_WL1)", "I(I_BL1)", "I(I_SE1)"], "source_kind": "new_run_raw"},
    "N4_PASSIVE": {"input": RAW_CASES["N4_PASSIVE"], "labels": ["I(B_JSL8)", "V(COMMON_SL)", "I(I_WL1)", "I(I_BL1)", "I(I_SE1)"], "source_kind": "new_run_raw"},
    "N1_REPLAY": {"input": RAW_CASES["N1_REPLAY"], "labels": ["I(I_REPLAY)", "V(QBIN)", "P(BJ1|XBQ1)", "P(BJ2|XBQ1)", "I(R_TERM)"], "source_kind": "immutable_N1_reference_raw"},
    "N2_REPLAY": {"input": RAW_CASES["N2_REPLAY"], "labels": ["I(I_REPLAY)", "V(QBIN)", "P(BJ1|XBQ1)", "P(BJ2|XBQ1)", "I(R_TERM)"], "source_kind": "new_run_raw"},
    "N3_REPLAY": {"input": RAW_CASES["N3_REPLAY"], "labels": ["I(I_REPLAY)", "V(QBIN)", "P(BJ1|XBQ1)", "P(BJ2|XBQ1)", "I(R_TERM)"], "source_kind": "new_run_raw"},
    "N4_REPLAY": {"input": RAW_CASES["N4_REPLAY"], "labels": ["I(I_REPLAY)", "V(QBIN)", "P(BJ1|XBQ1)", "P(BJ2|XBQ1)", "I(R_TERM)"], "source_kind": "new_run_raw"},
}
PAGE_TITLES = {
    "N1_PASSIVE": "N1 passive standalone | final READ mask 1000 | WRITE0 50-61 ps | ZERO_STATE_READ_CONTROL 70-81 ps | WRITE1 90-101 ps | FINAL READ 110-121 ps",
    "N2_PASSIVE": "N2 passive standalone | final READ mask 1100 | WRITE0 50-61 ps | ZERO_STATE_READ_CONTROL 70-81 ps | WRITE1 90-101 ps | FINAL READ 110-121 ps",
    "N3_PASSIVE": "N3 passive standalone | final READ mask 1110 | WRITE0 50-61 ps | ZERO_STATE_READ_CONTROL 70-81 ps | WRITE1 90-101 ps | FINAL READ 110-121 ps",
    "N4_PASSIVE": "N4 passive standalone | final READ mask 1111 | WRITE0 50-61 ps | ZERO_STATE_READ_CONTROL 70-81 ps | WRITE1 90-101 ps | FINAL READ 110-121 ps",
    "N1_REPLAY": "N1 replay standalone | final READ mask 1000 | QB/JTL current replay | FINAL READ RESPONSE 110-200 ps",
    "N2_REPLAY": "N2 replay standalone | final READ mask 1100 | QB/JTL current replay | FINAL READ RESPONSE 110-200 ps",
    "N3_REPLAY": "N3 replay standalone | final READ mask 1110 | QB/JTL current replay | FINAL READ RESPONSE 110-200 ps",
    "N4_REPLAY": "N4 replay standalone | final READ mask 1111 | QB/JTL current replay | FINAL READ RESPONSE 110-200 ps",
    "PASSIVE_SOURCE_N1_N4": "Passive source N1-N4 | I(B_JSL8) and V(COMMON_SL) | final READ response 110-200 ps",
    "ARRAY_LSL_BALANCE_N1_N4": "Shared-SL LSL balance N1-N4 | BVM LSL, SUM_LSL, JSL1, JSL8",
    "QB_REPLAY_N1_N4": "QB replay N1-N4 | QBIN, QBOUT, BJ1/BJ2 continuous phase",
    "JTL_REPLAY_N1_N4": "JTL replay N1-N4 | JTL1, JTL6, R_TERM",
    "READ_COUNT_SUMMARY": "Read-count summary N=1..4 | descriptive source/receiver metrics",
}
AGGREGATE_NAMES = ("PASSIVE_SOURCE_N1_N4", "ARRAY_LSL_BALANCE_N1_N4", "QB_REPLAY_N1_N4", "JTL_REPLAY_N1_N4", "READ_COUNT_SUMMARY")
PHASE_PAGES = {"N1_REPLAY", "N2_REPLAY", "N3_REPLAY", "N4_REPLAY", "QB_REPLAY_N1_N4", "JTL_REPLAY_N1_N4", "READ_COUNT_SUMMARY"}


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


def render_one(name: str, input_path: Path, labels: list[str], title: str) -> tuple[dict[str, object], list[str]]:
    failures: list[str] = []
    header = csv_headers(input_path)
    if not set(labels).issubset(set(header[1:])):
        failures.append(f"{name}: requested labels absent from input")
    output_path = EXP / "plots" / f"{name}.html"
    if name == "READ_COUNT_SUMMARY":
        command = [sys.executable, str(SUMMARY_RENDERER), str(input_path), str(output_path)]
    else:
        command = [sys.executable, str(PLOTTER), str(input_path), "-x", str(output_path), "-t", "sep_comb", "-c", "dark", "-j", "2pi", "-w", title, "-s", *labels]
    if output_path.exists():
        completed = subprocess.CompletedProcess(command, 0, "", "")
    else:
        completed = subprocess.run(command, cwd=REPO, text=True, capture_output=True)
    if completed.returncode != 0:
        failures.append(f"{name}: plotter exit {completed.returncode}: {completed.stderr[-500:]}")
    if not output_path.is_file() or output_path.stat().st_size == 0:
        failures.append(f"{name}: missing or empty HTML output")
        return {"input": input_path.relative_to(REPO).as_posix(), "labels": labels, "title": title, "command": command, "returncode": completed.returncode}, failures
    html = output_path.read_text(encoding="utf-8", errors="replace")
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
    return {
        "input": input_path.relative_to(REPO).as_posix(),
        "input_sha256": sha256(input_path),
        "source_kind": "derived_comparison_csv" if name in AGGREGATE_NAMES else RUN_PAGES[name]["source_kind"],
        "renderer": "categorical_plotly_summary" if name == "READ_COUNT_SUMMARY" else "scripts/josim-plot2.py",
        "output": output_path.relative_to(REPO).as_posix(),
        "output_sha256": sha256(output_path),
        "output_bytes": output_path.stat().st_size,
        "labels": labels,
        "title": title,
        "command": command,
        "returncode": completed.returncode,
        "phase_axis_conversion": "rad/(2*pi) displayed as turns" if name in PHASE_PAGES else None,
        "standalone_reads_raw_directly": name in RUN_PAGES,
    }, failures


def main() -> int:
    plot_inputs = json.loads(PLOT_INPUTS.read_text(encoding="utf-8"))
    failures: list[str] = []
    raw_before = {name: sha256(path) for name, path in RAW_CASES.items()}
    pages: dict[str, object] = {}
    for name in (*RUN_PAGES.keys(), *AGGREGATE_NAMES):
        if name in RUN_PAGES:
            spec = RUN_PAGES[name]
            input_path = spec["input"]
            labels = list(spec["labels"])
        else:
            if name not in plot_inputs:
                failures.append(f"missing registered aggregate input: {name}")
                continue
            input_path = REPO / plot_inputs[name]["path"]
            labels = list(plot_inputs[name]["labels"])
        page, page_failures = render_one(name, input_path, labels, PAGE_TITLES[name])
        pages[name] = page
        failures.extend(page_failures)
    raw_after = {name: sha256(path) for name, path in RAW_CASES.items()}
    if raw_before != raw_after:
        failures.append("raw hash changed during plot rendering")
    expected_pages = set(RUN_PAGES) | set(AGGREGATE_NAMES)
    if set(pages) != expected_pages:
        failures.append(f"rendered page set differs: {sorted(expected_pages ^ set(pages))}")
    record = {
        "schema": "jm2-read-count-passive-replay-visualization-qa-v1",
        "experiment_id": EXP.name,
        "created_at_local": now_local(),
        "status": "PASS" if not failures else "FAIL",
        "renderer": {"path": PLOTTER.relative_to(REPO).as_posix(), "sha256": sha256(PLOTTER), "type": "sep_comb", "color": "dark", "phase_jump_option": "2pi", "summary_renderer": SUMMARY_RENDERER.relative_to(REPO).as_posix(), "summary_renderer_sha256": sha256(SUMMARY_RENDERER)},
        "raw_hashes_before": raw_before,
        "raw_hashes_after": raw_after,
        "raw_unchanged": raw_before == raw_after,
        "standalone_run_pages": {name: f"plots/{name}.html" for name in RUN_PAGES},
        "aggregate_pages": {name: f"plots/{name}.html" for name in AGGREGATE_NAMES},
        "pages": pages,
        "standalone_direct_raw": all(page.get("standalone_reads_raw_directly") for name, page in pages.items() if name in RUN_PAGES),
        "phase_rule": "P(...) raw radians; renderer -j 2pi displays rad/(2*pi) as turns",
        "protocol_windows": ["WRITE0 50-61 ps", "ZERO_STATE_READ_CONTROL 70-81 ps", "WRITE1 90-101 ps", "FINAL READ 110-121 ps", "FINAL_READ_RESPONSE 110-200 ps"],
        "visualization_is_descriptive": True,
        "failures": failures,
    }
    write_once(EXP / "analysis/viz_qa.json", json.dumps(record, indent=2, ensure_ascii=False) + "\n")
    manifest = {
        "schema": "jm2-read-count-passive-replay-plot-manifest-v1",
        "experiment_id": EXP.name,
        "created_at_local": now_local(),
        "source_raw_hashes": raw_after,
        "derived_plot_inputs": plot_inputs,
        "standalone_run_pages": {name: {"input": spec["input"].relative_to(REPO).as_posix(), "sha256": sha256(spec["input"]), "labels": spec["labels"], "source_kind": spec["source_kind"]} for name, spec in RUN_PAGES.items()},
        "pages": pages,
        "visualization_is_descriptive": True,
        "phase_rule": "P(...) raw radians; renderer -j 2pi displays rad/(2*pi) as turns",
        "n1_reference_pages_do_not_copy_raw": True,
    }
    write_once(EXP / "plots/plot_manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"status": record["status"], "standalone_pages": len(RUN_PAGES), "aggregate_pages": len(AGGREGATE_NAMES), "failures": failures}, ensure_ascii=False))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
