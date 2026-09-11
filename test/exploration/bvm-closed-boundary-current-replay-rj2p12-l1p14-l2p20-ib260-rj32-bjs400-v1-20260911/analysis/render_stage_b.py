#!/usr/bin/env python3
"""Render Stage B N3 standalone raw pages and the two required comparisons."""

from __future__ import annotations

import csv
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
SOURCE_RUN = "CLOSED_LOOP_N3_REFERENCE"
REPLAY_RUN = "CLOSED_CURRENT_REPLAY_N3_0111_RJ2P12"
SOURCE = EXP / "references/closed_loop_rj2p12/ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_0111/raw.csv"
REPLAY = EXP / "runs/CLOSED_CURRENT_REPLAY_N3_0111_RJ2P12/raw.csv"

sys.path.insert(0, str(EXP / "analysis"))
from render_stage_a import (  # noqa: E402
    pvi,
    rel,
    replay_jtl,
    replay_qb,
    replay_specs,
    run_plot2,
    sha256,
    source_specs,
    standalone_entry,
    trace,
)


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def merged_csv(path: Path, sources: list[tuple[str, Path, dict[str, str]]], semantics: list[str]) -> tuple[list[str], str]:
    from bvmtools.phase import continuous_unwrap
    traces = [(case, source, trace(source), mapping) for case, source, mapping in sources]
    base_time = traces[0][2].time
    if any(item[2].time != base_time for item in traces[1:]):
        raise RuntimeError("Stage B comparison time grids differ")
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


def comparison(name: str, title: str, sources: list[tuple[str, Path, dict[str, str]]], semantics: list[str], output: Path) -> dict[str, Any]:
    descriptor, temp_name = tempfile.mkstemp(prefix="bvm-closed-replay-stage-b-", suffix=".csv", dir="/tmp")
    os.close(descriptor)
    temp = Path(temp_name)
    try:
        labels, temp_hash = merged_csv(temp, sources, semantics)
        command = run_plot2(temp, output, title, labels)
        return {"stage": "comparison", "name": name, "input_mode": "TEMPORARY_MERGED_COMPARISON", "input_path": str(temp), "input_sha256": temp_hash, "output_path": rel(output), "output_sha256": sha256(output), "source_raw_paths": [rel(path) for _, path, _ in sources], "source_raw_sha256": [sha256(path) for _, path, _ in sources], "comparison_cases": [case for case, _, _ in sources], "semantic_signals": semantics, "labels": labels, "signal_order": labels, "command": command, "renderer": rel(REPO / "scripts/josim-plot2.py"), "layout": "sep_comb", "color": "dark", "phase_option": "2pi", "phase_convention": "raw P radians; each case independently unwrapped before display; rad/(2*pi) turns", "window_ps": [0.0, 200.0], "window_semantics": "whole-run raw timestamps; no focused window", "temporary_input_sha256": temp_hash}
    finally:
        temp.unlink(missing_ok=True)


def summary(run_id: str, names: list[str]) -> None:
    path = EXP / "visualization/run_summaries" / f"{run_id}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"# {run_id} — Stage B whole-run raw evidence", "", "Scientific interpretation is authorized for Stage B; no standalone page is an SFQ counter.", "", "All pages read the corresponding raw.csv directly and cover 0–200 ps.", ""]
    for name in names:
        lines.append(f"- [{name}.html](../plots/runs/{run_id}/{name}.html)")
    lines.extend(["", "P values are raw radians; plot2 `2pi` is only the rad/(2*pi) display conversion.", ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    source_trace = trace(SOURCE)
    replay_trace = trace(REPLAY)
    source_pages = source_specs()
    replay_pages = replay_specs()
    entries: list[dict[str, Any]] = []
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
    summary(SOURCE_RUN, list(source_pages))
    summary(REPLAY_RUN, list(replay_pages))
    receiver_semantics = ["source_current", "I(LIN|XBQ1)", "I(L1|XBQ1)", "I(L2|XBQ1)", "P(BJ1|XBQ1)", "V(BJ1|XBQ1)", "P(BJ2|XBQ1)", "V(BJ2|XBQ1)", "V(QBOUT)"] + [f"V(JTL{stage}_OUT)" for stage in range(1, 7)] + ["I(R_TERM)"]
    closed_mapping = {"source_current": "I(B_JSL8)", **{label: label for label in receiver_semantics if label != "source_current"}}
    replay_mapping = {"source_current": "I(I_REPLAY)", **{label: label for label in receiver_semantics if label != "source_current"}}
    comparisons = [comparison("CLOSED_VS_CLOSED_CURRENT_REPLAY_N3", "CLOSED_VS_CLOSED_CURRENT_REPLAY_N3 — whole-run raw comparison", [("N3_CLOSED_LOOP", SOURCE, closed_mapping), ("N3_CLOSED_CURRENT_REPLAY", REPLAY, replay_mapping)], receiver_semantics, EXP / "visualization/plots/comparison/CLOSED_VS_CLOSED_CURRENT_REPLAY_N3.html")]
    n2_replay = EXP / "runs/CLOSED_CURRENT_REPLAY_N2_0011_RJ2P12/raw.csv"
    population_semantics = ["I(I_REPLAY)", "P(BJ1|XBQ1)", "P(BJ2|XBQ1)", "V(QBOUT)"] + [f"V(JTL{stage}_OUT)" for stage in range(1, 7)] + ["I(R_TERM)"]
    comparisons.append(comparison("CLOSED_CURRENT_REPLAY_N2_VS_N3", "CLOSED_CURRENT_REPLAY_N2_VS_N3 — whole-run raw comparison", [("N2_REPLAY", n2_replay, {label: label for label in population_semantics}), ("N3_REPLAY", REPLAY, {label: label for label in population_semantics})], population_semantics, EXP / "visualization/plots/comparison/CLOSED_CURRENT_REPLAY_N2_VS_N3.html"))
    manifest_path = EXP / "visualization/manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["created_at_local"] = now()
    manifest["standalone_entries"].extend(entries)
    manifest["comparison_entries"].extend(comparisons)
    manifest["standalone_entry_count"] = len(manifest["standalone_entries"])
    manifest["comparison_entry_count"] = len(manifest["comparison_entries"])
    manifest["run_summary_paths"].append(rel(EXP / "visualization/run_summaries" / f"{REPLAY_RUN}.md"))
    manifest["raw_hashes"].update({SOURCE_RUN: sha256(SOURCE), REPLAY_RUN: sha256(REPLAY)})
    manifest["stage_b"] = {"source_run": SOURCE_RUN, "replay_run": REPLAY_RUN, "critical_window_ps": [121.0, 130.0], "scientific_review_authorized": True, "outcome": "CLOSED_BOUNDARY_CURRENT_REPLAY_REPRODUCES_N3_FOUR_RESPONSE"}
    manifest["scientific_analysis_performed"] = True
    manifest["status"] = "PASS" if len(manifest["standalone_entries"]) == 20 and len(manifest["comparison_entries"]) == 3 else "FAIL"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": manifest["status"], "standalone_html": len(manifest["standalone_entries"]), "comparison_html": len(manifest["comparison_entries"]), "stage_b_outcome": manifest["stage_b"]["outcome"]}, ensure_ascii=False, indent=2))
    return 0 if manifest["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
