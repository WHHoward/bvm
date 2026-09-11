#!/usr/bin/env python3
"""Render whole-run raw-direct Stage A pages and one closed/replay comparison."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
PLOTTER = REPO / "scripts/josim-plot2.py"
sys.path.insert(0, str(REPO / "scripts"))
from bvmtools.phase import continuous_unwrap  # noqa: E402
from bvmtools.raw import RawTrace, read_csv  # noqa: E402


SOURCE_RUN = "CLOSED_LOOP_N2_REFERENCE"
REPLAY_RUN = "CLOSED_CURRENT_REPLAY_N2_0011_RJ2P12"
SOURCE = EXP / "references/closed_loop_rj2p12/ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_0011/raw.csv"
REPLAY = EXP / "runs/CLOSED_CURRENT_REPLAY_N2_0011_RJ2P12/raw.csv"


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO.resolve()).as_posix()


def trace(path: Path) -> RawTrace:
    value = read_csv(path)
    if value.duplicate_columns:
        raise RuntimeError(f"duplicate raw columns: {path}")
    return value


def pvi(label: str) -> list[str]:
    return [f"P({label})", f"V({label})", f"I({label})"]


def source_specs() -> OrderedDict[str, list[str]]:
    timing = [f"I(I_{kind}{instance})" for instance in range(1, 5) for kind in ("WL", "BL", "SE")]
    bvm = []
    for instance in range(1, 5):
        header = f"XBVM{instance}"
        for junction in ("B_JM1", "B_JM2", "B_JS1", "B_JS2"):
            bvm.extend(pvi(f"{junction}|{header}"))
        bvm.extend((f"I(L_SL|{header})", f"V(L_SL|{header})"))
    boundary = ["V(COMMON_SL)"]
    for index in range(1, 9):
        boundary.extend(pvi(f"B_JSL{index}"))
    return OrderedDict((("01_SIGNAL_TIMING", timing + ["I(B_JSL8)"]), ("02_BVM_STATE", bvm), ("03_SOURCE_BOUNDARY", boundary), ("04_QB_STATE", source_qb()), ("05_JTL_CHAIN", replay_jtl()), ("06_TERMINAL", ["V(QBOUT)", "V(JTL6_OUT)", "I(R_TERM)"])))


def source_qb() -> list[str]:
    labels = ["V(QBIN)", "I(LIN|XBQ1)", "V(LIN|XBQ1)", "I(L1|XBQ1)", "V(L1|XBQ1)", "I(L2|XBQ1)", "V(L2|XBQ1)", "I(L3|XBQ1)", "V(QBOUT)"]
    for junction in ("BJS", "BJ1", "BJ2"):
        labels.extend(pvi(f"{junction}|XBQ1"))
    return labels


def replay_qb() -> list[str]:
    labels = ["V(QBIN)", "I(I_REPLAY)", "I(LIN|XBQ1)", "V(LIN|XBQ1)", "I(L1|XBQ1)", "V(L1|XBQ1)", "I(L2|XBQ1)", "V(L2|XBQ1)", "I(L3|XBQ1)", "V(QBOUT)"]
    for junction in ("BJS", "BJ1", "BJ2"):
        labels.extend(pvi(f"{junction}|XBQ1"))
    return labels


def replay_jtl() -> list[str]:
    labels: list[str] = []
    for stage in range(1, 7):
        handle = f"XJTL1_{stage}"
        labels.extend(pvi(f"B01|{handle}"))
        labels.extend(pvi(f"B02|{handle}"))
        labels.append(f"V(JTL{stage}_OUT)")
    return labels


def replay_specs() -> OrderedDict[str, list[str]]:
    return OrderedDict((("01_SIGNAL_TIMING", ["I(I_REPLAY)", "V(QBIN)", "V(QBOUT)"]), ("04_QB_STATE", replay_qb()), ("05_JTL_CHAIN", replay_jtl()), ("06_TERMINAL", ["V(QBOUT)", "V(JTL6_OUT)", "I(R_TERM)"])))


def run_plot2(source: Path, output: Path, title: str, labels: list[str]) -> list[str]:
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [sys.executable, str(PLOTTER), str(source), "-x", str(output), "-t", "sep_comb", "-c", "dark", "-j", "2pi", "-w", title, "-s", *labels]
    completed = subprocess.run(command, cwd=REPO, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"plot2 failed: {output}\n{completed.stdout}\n{completed.stderr}")
    html = output.read_text(encoding="utf-8", errors="replace")
    if "<html" not in html.casefold() or '"title":{"text":"Unknown"}' in html:
        raise RuntimeError(f"plot HTML failed QA: {output}")
    if any(label.startswith("P(") for label in labels) and "Phase (turns)" not in html:
        raise RuntimeError(f"plot phase display failed QA: {output}")
    return command


def standalone_entry(run_id: str, source: Path, name: str, output: Path, labels: list[str], command: list[str]) -> dict[str, Any]:
    return {"stage": "standalone", "run_id": run_id, "name": name, "input_mode": "RAW_DIRECT", "input_path": rel(source), "input_raw": source.relative_to(EXP).as_posix(), "input_raw_sha256": sha256(source), "output_path": rel(output), "output_sha256": sha256(output), "source_raw_paths": [rel(source)], "source_raw_sha256": [sha256(source)], "labels": labels, "signal_order": labels, "command": command, "renderer": rel(PLOTTER), "layout": "sep_comb", "color": "dark", "phase_option": "2pi", "phase_convention": "raw P radians; display rad/(2*pi) turns; never SFQ count", "window_ps": [0.0, 200.0], "window_semantics": "whole-run raw timestamps; no focused window", "temporary_input_sha256": None}


def merged_csv(path: Path, sources: list[tuple[str, Path, dict[str, str]]], semantics: list[str]) -> tuple[list[str], str]:
    traces = [(case, source, trace(source), mapping) for case, source, mapping in sources]
    base_time = traces[0][2].time
    if any(item[2].time != base_time for item in traces[1:]):
        raise RuntimeError("comparison time grids differ")
    labels: list[str] = []
    columns: list[list[float]] = []
    for semantic in semantics:
        for case, _, item, mapping in traces:
            actual = mapping[semantic]
            if actual not in item.headers:
                raise RuntimeError(f"missing comparison label {actual}: {case}")
            values = list(item.column(actual))
            if actual.startswith("P("):
                values = list(continuous_unwrap(tuple(values)))
            labels.append(f"{actual} [{case}]")
            columns.append(values)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["time", *labels])
        for index, timestamp in enumerate(base_time):
            writer.writerow([f"{timestamp:.17g}", *(f"{column[index]:.17g}" for column in columns)])
    return labels, sha256(path)


def comparison_entry(sources: list[tuple[str, Path, dict[str, str]]], semantics: list[str], output: Path, entries: list[dict[str, Any]]) -> None:
    descriptor, name = tempfile.mkstemp(prefix="bvm-closed-replay-comparison-", suffix=".csv", dir="/tmp")
    os.close(descriptor)
    temp = Path(name)
    try:
        labels, temp_hash = merged_csv(temp, sources, semantics)
        command = run_plot2(temp, output, "CLOSED_VS_CLOSED_CURRENT_REPLAY_N2", labels)
        entries.append({"stage": "comparison", "name": "CLOSED_VS_CLOSED_CURRENT_REPLAY_N2", "input_mode": "TEMPORARY_MERGED_COMPARISON", "input_path": str(temp), "input_sha256": temp_hash, "output_path": rel(output), "output_sha256": sha256(output), "source_raw_paths": [rel(path) for _, path, _ in sources], "source_raw_sha256": [sha256(path) for _, path, _ in sources], "comparison_cases": [case for case, _, _ in sources], "semantic_signals": semantics, "labels": labels, "signal_order": labels, "command": command, "renderer": rel(PLOTTER), "layout": "sep_comb", "color": "dark", "phase_option": "2pi", "phase_convention": "raw P radians; independently unwrapped before comparison; display rad/(2*pi)", "window_ps": [0.0, 200.0], "window_semantics": "whole-run raw timestamps; no focused window", "temporary_input_sha256": temp_hash})
    finally:
        temp.unlink(missing_ok=True)


def write_summary(run_id: str, names: list[str]) -> None:
    path = EXP / "visualization/run_summaries" / f"{run_id}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"# {run_id} — whole-run Stage A evidence", "", "Scientific interpretation: `NOT_PERFORMED`.", "", "Standalone pages read raw CSV directly and cover 0–200 ps.", ""]
    for name in names:
        lines.append(f"- [{name}.html](../plots/runs/{run_id}/{name}.html)")
    lines.extend(["", "P values are raw radians; plot2 `2pi` is a display conversion only. No page is an SFQ/event counter or causal mechanism result.", ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    entries: list[dict[str, Any]] = []
    source_trace = trace(SOURCE)
    replay_trace = trace(REPLAY)
    source_pages = source_specs()
    replay_pages = replay_specs()
    for name, labels in source_pages.items():
        missing = [label for label in labels if label not in source_trace.headers]
        if missing:
            raise RuntimeError(f"{SOURCE_RUN}/{name} missing: {missing}")
        output = EXP / "visualization/plots/runs" / SOURCE_RUN / f"{name}.html"
        command = run_plot2(SOURCE, output, f"{SOURCE_RUN} — {name}", labels)
        entries.append(standalone_entry(SOURCE_RUN, SOURCE, name, output, labels, command))
    for name, labels in replay_pages.items():
        missing = [label for label in labels if label not in replay_trace.headers]
        if missing:
            raise RuntimeError(f"{REPLAY_RUN}/{name} missing: {missing}")
        output = EXP / "visualization/plots/runs" / REPLAY_RUN / f"{name}.html"
        command = run_plot2(REPLAY, output, f"{REPLAY_RUN} — {name}", labels)
        entries.append(standalone_entry(REPLAY_RUN, REPLAY, name, output, labels, command))
    write_summary(REPLAY_RUN, list(replay_pages))
    write_summary(SOURCE_RUN, list(source_pages))
    comparison_semantics = ["source_current", "I(LIN|XBQ1)", "I(L1|XBQ1)", "I(L2|XBQ1)", "P(BJ1|XBQ1)", "V(BJ1|XBQ1)", "P(BJ2|XBQ1)", "V(BJ2|XBQ1)", "V(QBOUT)"] + [f"V(JTL{stage}_OUT)" for stage in range(1, 7)] + ["I(R_TERM)"]
    sources = [("N2_CLOSED_LOOP", SOURCE, {"source_current": "I(B_JSL8)", **{label: label for label in comparison_semantics if label != "source_current"}}), ("N2_CLOSED_CURRENT_REPLAY", REPLAY, {"source_current": "I(I_REPLAY)", **{label: label for label in comparison_semantics if label != "source_current"}})]
    comparisons: list[dict[str, Any]] = []
    comparison_entry(sources, comparison_semantics, EXP / "visualization/plots/comparison/CLOSED_VS_CLOSED_CURRENT_REPLAY_N2.html", comparisons)
    standalone = [entry for entry in entries if entry["stage"] == "standalone"]
    manifest = {"schema": "bvm-closed-boundary-current-replay-stage-a-visualization-manifest-v1", "experiment_id": EXP.name, "created_at_local": now(), "renderer": rel(PLOTTER), "layout": "sep_comb", "color": "dark", "phase_option": "2pi", "whole_run_window_ps": [0.0, 200.0], "focused_windows": [], "standalone_input_policy": "raw.csv direct", "comparison_input_policy": "temporary merged CSV under /tmp deleted after render", "semantic_planes": {"source_reference": ["01_SIGNAL_TIMING", "02_BVM_STATE", "03_SOURCE_BOUNDARY", "04_QB_STATE", "05_JTL_CHAIN", "06_TERMINAL"], "replay": ["01_SIGNAL_TIMING", "04_QB_STATE", "05_JTL_CHAIN", "06_TERMINAL"], "not_applicable_replay_planes": ["02_BVM_STATE", "03_SOURCE_BOUNDARY"]}, "standalone_entries": standalone, "comparison_entries": comparisons, "standalone_entry_count": len(standalone), "comparison_entry_count": len(comparisons), "run_summary_paths": [rel(EXP / "visualization/run_summaries" / f"{REPLAY_RUN}.md")], "raw_hashes": {SOURCE_RUN: sha256(SOURCE), REPLAY_RUN: sha256(REPLAY)}, "scientific_analysis_performed": False, "no_sfq_count_labels": True, "status": "PASS" if len(standalone) == 10 and len(comparisons) == 1 else "FAIL"}
    (EXP / "visualization/manifest.json").parent.mkdir(parents=True, exist_ok=True)
    (EXP / "visualization/manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": manifest["status"], "standalone_html": len(standalone), "comparison_html": len(comparisons), "whole_run_only": True, "scientific_analysis_performed": False}, ensure_ascii=False, indent=2))
    return 0 if manifest["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
