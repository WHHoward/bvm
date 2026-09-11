#!/usr/bin/env python3
"""Render compact whole-run raw-direct and comparison visualizations."""

from __future__ import annotations

import csv
import hashlib
import json
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


PASSIVE = OrderedDict((
    ("PASSIVE_N2_0011", EXP / "runs/PASSIVE_N2_0011/raw.csv"),
    ("PASSIVE_N3_0111", EXP / "runs/PASSIVE_N3_0111/raw.csv"),
    ("PASSIVE_N4_1111", EXP / "runs/PASSIVE_N4_1111/raw.csv"),
))
REPLAY = OrderedDict((
    ("REPLAY_N2_0011_RJ2P12", EXP / "runs/REPLAY_N2_0011_RJ2P12/raw.csv"),
    ("REPLAY_N3_0111_RJ2P12", EXP / "runs/REPLAY_N3_0111_RJ2P12/raw.csv"),
    ("REPLAY_N4_1111_RJ2P12", EXP / "runs/REPLAY_N4_1111_RJ2P12/raw.csv"),
))
CLOSED = OrderedDict((
    ("ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_0011", EXP / "references/closed_loop_rj2p12/ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_0011/raw.csv"),
    ("ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_0111", EXP / "references/closed_loop_rj2p12/ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_0111/raw.csv"),
    ("ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_1111", EXP / "references/closed_loop_rj2p12/ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_1111/raw.csv"),
))


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
        raise RuntimeError(f"duplicate raw columns: {path}: {value.duplicate_columns}")
    return value


def pvi(label: str) -> list[str]:
    return [f"P({label})", f"V({label})", f"I({label})"]


def passive_specs() -> OrderedDict[str, list[str]]:
    timing = [f"I(I_{kind}{instance})" for instance in range(1, 5) for kind in ("WL", "BL", "SE")]
    bvm: list[str] = []
    for instance in range(1, 5):
        header = f"XBVM{instance}"
        for junction in ("B_JM1", "B_JM2", "B_JS1", "B_JS2"):
            bvm.extend(pvi(f"{junction}|{header}"))
        bvm.extend((f"I(L_SL|{header})", f"V(L_SL|{header})"))
    jsl = ["V(COMMON_SL)"]
    for index in range(1, 9):
        jsl.extend(pvi(f"B_JSL{index}"))
    return OrderedDict((
        ("01_SIGNAL_TIMING", timing + ["V(COMMON_SL)", "I(B_JSL8)"]),
        ("02_BVM_STATE", bvm),
        ("03_JSL_CHAIN", jsl),
    ))


def replay_specs() -> OrderedDict[str, list[str]]:
    qb = ["V(QBIN)", "V(QBOUT)", "I(I_REPLAY)", "I(LIN|XBQ1)", "V(LIN|XBQ1)", "I(L1|XBQ1)", "V(L1|XBQ1)", "I(L2|XBQ1)", "V(L2|XBQ1)", "I(L3|XBQ1)", "V(L3|XBQ1)"]
    for junction in ("BJS", "BJ1", "BJ2"):
        qb.extend(pvi(f"{junction}|XBQ1"))
    jtl: list[str] = []
    for stage in range(1, 7):
        handle = f"XJTL1_{stage}"
        jtl.extend(pvi(f"B01|{handle}"))
        jtl.extend(pvi(f"B02|{handle}"))
        jtl.append(f"V(JTL{stage}_OUT)")
    terminal = ["V(QBOUT)", "V(JTL6_OUT)", "I(R_TERM)"]
    return OrderedDict((("01_SIGNAL_TIMING", ["I(I_REPLAY)", "V(QBIN)", "V(QBOUT)"]), ("04_QB_STATE", qb), ("05_JTL_CHAIN", jtl), ("06_TERMINAL", terminal)))


def run_plot2(input_path: Path, output_path: Path, title: str, labels: list[str]) -> list[str]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = [sys.executable, str(PLOTTER), str(input_path), "-x", str(output_path), "-t", "sep_comb", "-c", "dark", "-j", "2pi", "-w", title, "-s", *labels]
    completed = subprocess.run(command, cwd=REPO, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"plot2 failed for {output_path}:\n{completed.stdout}\n{completed.stderr}")
    if not output_path.is_file() or output_path.stat().st_size == 0:
        raise RuntimeError(f"plot2 did not create {output_path}")
    html = output_path.read_text(encoding="utf-8", errors="replace")
    if "<html" not in html.casefold() or '"title":{"text":"Unknown"}' in html:
        raise RuntimeError(f"plot HTML QA failed: {output_path}")
    if any(label.startswith("P(") for label in labels) and "Phase (turns)" not in html:
        raise RuntimeError(f"phase display QA failed: {output_path}")
    return command


def standalone_entry(run_id: str, source: Path, name: str, output: Path, labels: list[str], command: list[str]) -> dict[str, Any]:
    return {"stage": "standalone", "run_id": run_id, "name": name, "input_mode": "RAW_DIRECT", "input_path": rel(source), "input_raw": rel(source), "input_raw_sha256": sha256(source), "output_path": rel(output), "output_sha256": sha256(output), "source_raw_paths": [rel(source)], "source_raw_sha256": [sha256(source)], "labels": labels, "signal_order": labels, "command": command, "renderer": rel(PLOTTER), "layout": "sep_comb", "color": "dark", "phase_option": "2pi", "phase_convention": "raw P radians; plot2 displays rad/(2*pi) turns; never SFQ count", "window_ps": [0.0, 200.0], "window_semantics": "whole-run raw timestamps; no focused window", "temporary_input_sha256": None}


def write_merged(path: Path, sources: list[tuple[str, Path, dict[str, str]]], semantics: list[str]) -> tuple[list[str], str]:
    traces = [(case, source, trace(source), mapping) for case, source, mapping in sources]
    base_time = traces[0][2].time
    if any(item[2].time != base_time for item in traces[1:]):
        raise RuntimeError("comparison source time grids differ")
    headers = ["time"]
    columns: list[tuple[str, list[float], bool]] = []
    for semantic in semantics:
        for case, _, item, mapping in traces:
            actual = mapping[semantic]
            if actual not in item.headers:
                raise RuntimeError(f"comparison source missing {actual} in {case}")
            values = list(item.column(actual))
            if actual.startswith("P("):
                values = list(continuous_unwrap(tuple(values)))
            output_label = f"{actual} [{case}]"
            headers.append(output_label)
            columns.append((output_label, values, actual.startswith("P(")))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(headers)
        for index, timestamp in enumerate(base_time):
            row: list[Any] = [f"{timestamp:.17g}"]
            row.extend(f"{values[index]:.17g}" for _, values, _ in columns)
            writer.writerow(row)
    return [label for label, _, _ in columns], sha256(path)


def comparison_entry(name: str, sources: list[tuple[str, Path, dict[str, str]]], semantics: list[str], output: Path, title: str, entries: list[dict[str, Any]]) -> None:
    import os
    descriptor, temp_name = tempfile.mkstemp(prefix="bvm-mechanism-comparison-", suffix=".csv", dir="/tmp")
    # mkstemp returns an open descriptor; close it without retaining a plot CSV.
    os.close(descriptor)
    temp = Path(temp_name)
    try:
        labels, temp_hash = write_merged(temp, sources, semantics)
        output.parent.mkdir(parents=True, exist_ok=True)
        command = run_plot2(temp, output, title, labels)
        entries.append({"stage": "comparison", "name": name, "input_mode": "TEMPORARY_MERGED_COMPARISON", "input_path": str(temp), "input_sha256": temp_hash, "output_path": rel(output), "output_sha256": sha256(output), "source_raw_paths": [rel(path) for _, path, _ in sources], "source_raw_sha256": [sha256(path) for _, path, _ in sources], "comparison_cases": [case for case, _, _ in sources], "semantic_signals": semantics, "labels": labels, "signal_order": labels, "command": command, "renderer": rel(PLOTTER), "layout": "sep_comb", "color": "dark", "phase_option": "2pi", "phase_convention": "raw P radians; each source independently unwrapped before comparison plot; display turns via rad/(2*pi)", "window_ps": [0.0, 200.0], "window_semantics": "whole-run raw timestamps; no focused window", "temporary_input_sha256": temp_hash})
    finally:
        temp.unlink(missing_ok=True)


def write_summary(run_id: str, names: list[str]) -> Path:
    path = EXP / "visualization/run_summaries" / f"{run_id}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"# {run_id} — whole-run raw evidence", "", "Scientific interpretation: `NOT_PERFORMED`.", "", "All standalone pages use this run's raw.csv directly and cover 0–200 ps.", ""]
    for name in names:
        lines.append(f"- [{name}.html](../plots/runs/{run_id}/{name}.html)")
    lines.extend(["", "P values are raw radians; the plotter's `2pi` option displays phase as rad/(2*pi) turns. No page is an SFQ/event counter or mechanism conclusion.", ""])
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def main() -> int:
    entries: list[dict[str, Any]] = []
    passive_page_names = list(passive_specs())
    replay_page_names = list(replay_specs())
    for run_id, source in PASSIVE.items():
        item = trace(source)
        for name, labels in passive_specs().items():
            missing = [label for label in labels if label not in item.headers]
            if missing:
                raise RuntimeError(f"{run_id}/{name} missing labels: {missing}")
            output = EXP / "visualization/plots/runs" / run_id / f"{name}.html"
            command = run_plot2(source, output, f"{run_id} — {name}", labels)
            entries.append(standalone_entry(run_id, source, name, output, labels, command))
        write_summary(run_id, passive_page_names)
    for run_id, source in REPLAY.items():
        item = trace(source)
        for name, labels in replay_specs().items():
            missing = [label for label in labels if label not in item.headers]
            if missing:
                raise RuntimeError(f"{run_id}/{name} missing labels: {missing}")
            output = EXP / "visualization/plots/runs" / run_id / f"{name}.html"
            command = run_plot2(source, output, f"{run_id} — {name}", labels)
            entries.append(standalone_entry(run_id, source, name, output, labels, command))
        write_summary(run_id, replay_page_names)

    comparison_entries: list[dict[str, Any]] = []
    comparison_entry("PASSIVE_SOURCE_N2_N4", [(case, path, {"I(B_JSL8)": "I(B_JSL8)"}) for case, path in PASSIVE.items()], ["I(B_JSL8)"], EXP / "visualization/plots/comparison/PASSIVE_SOURCE_N2_N4.html", "PASSIVE_SOURCE_N2_N4 — I(B_JSL8)", comparison_entries)
    replay_common = ["V(QBIN)", "V(QBOUT)", "I(L1|XBQ1)", "I(L2|XBQ1)", "P(BJ1|XBQ1)", "P(BJ2|XBQ1)"]
    comparison_entry("QB_REPLAY_N2_N4", [(case, path, {label: label for label in replay_common}) for case, path in REPLAY.items()], replay_common, EXP / "visualization/plots/comparison/QB_REPLAY_N2_N4.html", "QB_REPLAY_N2_N4 — isolated receiver", comparison_entries)
    jtl_common = [f"V(JTL{stage}_OUT)" for stage in range(1, 7)] + [f"P(B01|XJTL1_{stage})" for stage in range(1, 7)]
    comparison_entry("JTL_REPLAY_N2_N4", [(case, path, {label: label for label in jtl_common}) for case, path in REPLAY.items()], jtl_common, EXP / "visualization/plots/comparison/JTL_REPLAY_N2_N4.html", "JTL_REPLAY_N2_N4 — ordered downstream raw tracks", comparison_entries)
    terminal_common = ["V(QBOUT)", "V(JTL6_OUT)", "I(R_TERM)"]
    comparison_entry("TERMINAL_REPLAY_N2_N4", [(case, path, {label: label for label in terminal_common}) for case, path in REPLAY.items()], terminal_common, EXP / "visualization/plots/comparison/TERMINAL_REPLAY_N2_N4.html", "TERMINAL_REPLAY_N2_N4 — terminal raw tracks", comparison_entries)
    receiver_semantics = ["source_current", "P(BJ1|XBQ1)", "P(BJ2|XBQ1)", "V(QBOUT)", "I(L1|XBQ1)", "I(L2|XBQ1)", "I(LIN|XBQ1)"] + [f"V(JTL{stage}_OUT)" for stage in range(1, 7)] + ["I(R_TERM)"]
    for population in ("N2", "N3", "N4"):
        closed_id = {"N2": "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_0011", "N3": "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_0111", "N4": "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_1111"}[population]
        replay_id = {"N2": "REPLAY_N2_0011_RJ2P12", "N3": "REPLAY_N3_0111_RJ2P12", "N4": "REPLAY_N4_1111_RJ2P12"}[population]
        closed_case = f"{population}_CLOSED_LOOP"
        replay_case = f"{population}_REPLAY"
        sources = [(closed_case, CLOSED[closed_id], {"source_current": "I(B_JSL8)", **{label: label for label in receiver_semantics if label != "source_current"}}), (replay_case, REPLAY[replay_id], {"source_current": "I(I_REPLAY)", **{label: label for label in receiver_semantics if label != "source_current"}})]
        comparison_entry(f"CLOSED_VS_REPLAY_{population}", sources, receiver_semantics, EXP / f"visualization/plots/comparison/CLOSED_VS_REPLAY_{population}.html", f"CLOSED_VS_REPLAY_{population} — whole-run raw comparison", comparison_entries)
    standalone = [item for item in entries if item["stage"] == "standalone"]
    manifest = {"schema": "bvm-population-passive-source-replay-visualization-manifest-v1", "experiment_id": EXP.name, "created_at_local": now(), "renderer": rel(PLOTTER), "layout": "sep_comb", "color": "dark", "phase_option": "2pi", "whole_run_window_ps": [0.0, 200.0], "focused_windows": [], "standalone_input_policy": "each standalone reads corresponding raw.csv directly", "comparison_input_policy": "temporary merged CSV in /tmp, deleted after render", "semantic_planes": {"passive": {"01_SIGNAL_TIMING": "controls -> COMMON_SL -> I(B_JSL8)", "02_BVM_STATE": "BVM storage/core and output branch probes", "03_JSL_CHAIN": "COMMON_SL -> B_JSL1..8 -> ground endpoint", "04_QB_STATE": "NOT_APPLICABLE: receiver removed", "05_JTL_CHAIN": "NOT_APPLICABLE: receiver removed"}, "replay": {"01_SIGNAL_TIMING": "I_REPLAY -> QBIN", "02_BVM_STATE": "NOT_APPLICABLE: source removed", "03_JSL_CHAIN": "NOT_APPLICABLE: source removed", "04_QB_STATE": "QBIN -> QB internal -> QBOUT", "05_JTL_CHAIN": "QBOUT -> JTL1..6 -> R_TERM"}}, "standalone_entries": standalone, "comparison_entries": comparison_entries, "standalone_entry_count": len(standalone), "comparison_entry_count": len(comparison_entries), "run_summary_paths": [rel(EXP / "visualization/run_summaries" / f"{run_id}.md") for run_id in (*PASSIVE.keys(), *REPLAY.keys())], "raw_hashes": {**{run: sha256(path) for run, path in PASSIVE.items()}, **{run: sha256(path) for run, path in REPLAY.items()}}, "scientific_analysis_performed": False, "no_sfq_count_labels": True, "status": "PASS" if len(standalone) == 21 and len(comparison_entries) == 7 else "FAIL"}
    output = EXP / "visualization/manifest.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": manifest["status"], "standalone_html": len(standalone), "comparison_html": len(comparison_entries), "whole_run_only": True, "scientific_analysis_performed": False}, ensure_ascii=False, indent=2))
    return 0 if manifest["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
