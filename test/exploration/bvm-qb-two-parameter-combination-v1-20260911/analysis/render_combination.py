#!/usr/bin/env python3
"""Render bounded raw-direct visualization evidence for the combination run."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
PLOTTER = REPO / "scripts/josim-plot2.py"
MATRIX = EXP / "screening/COMBINATION_MATRIX.json"
STATE = EXP / "screening/combination_state.json"
BASELINE = {"0011": EXP / "references/baseline_rj2p12/ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_0011/raw.csv", "0111": EXP / "references/baseline_rj2p12/ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_0111/raw.csv"}
SIGNAL_LABELS = ("I(I_WL1)", "I(I_BL1)", "I(I_SE1)", "I(I_WL2)", "I(I_BL2)", "I(I_SE2)", "I(I_WL3)", "I(I_BL3)", "I(I_SE3)", "I(I_WL4)", "I(I_BL4)", "I(I_SE4)", "V(COMMON_SL)", "I(B_JSL8)", "V(QBIN)", "V(QBOUT)", "V(JTL1_OUT)", "V(JTL2_OUT)", "V(JTL3_OUT)", "V(JTL4_OUT)", "V(JTL5_OUT)", "V(JTL6_OUT)", "I(R_TERM)")
QB_LABELS = ("V(QBIN)", "I(LIN|XBQ1)", "P(BJS|XBQ1)", "V(BJS|XBQ1)", "I(BJS|XBQ1)", "P(BJ1|XBQ1)", "V(BJ1|XBQ1)", "I(BJ1|XBQ1)", "I(L1|XBQ1)", "I(L2|XBQ1)", "P(BJ2|XBQ1)", "V(BJ2|XBQ1)", "I(BJ2|XBQ1)", "V(QBOUT)")
JTL_LABELS = tuple(["V(QBOUT)"] + [f"P(B01|XJTL1_{stage})" for stage in range(1, 7)] + [f"V(JTL{stage}_OUT)" for stage in range(1, 7)] + ["I(R_TERM)"])
COMPARE_LABELS = ("P(BJ1|XBQ1)", "P(BJ2|XBQ1)", "V(QBOUT)", "V(JTL1_OUT)", "V(JTL2_OUT)", "V(JTL3_OUT)", "V(JTL4_OUT)", "V(JTL5_OUT)", "V(JTL6_OUT)", "I(R_TERM)")


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


def exp_rel(path: Path) -> str:
    return path.resolve().relative_to(EXP.resolve()).as_posix()


def header(path: Path) -> list[str]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        return next(csv.reader(stream))


def render(raw: Path, output: Path, labels: tuple[str, ...], title: str) -> list[str]:
    missing = [label for label in labels if label not in header(raw)]
    if missing:
        raise RuntimeError(f"missing visualization labels {missing} in {raw}")
    command = [sys.executable, str(PLOTTER), str(raw), "-x", str(output), "-t", "sep_comb", "-c", "dark", "-j", "2pi", "-w", title, "-s", *labels]
    if not output.is_file():
        output.parent.mkdir(parents=True, exist_ok=True)
        completed = subprocess.run(command, cwd=REPO, capture_output=True, text=True, check=False)
        if completed.returncode != 0 or not output.is_file() or output.stat().st_size == 0:
            raise RuntimeError(f"plot failed {output}: {completed.stderr[-1000:]}")
    return command


def standalone(run_id: str, raw: Path, name: str, labels: tuple[str, ...]) -> dict[str, Any]:
    output = EXP / "visualization/plots" / ("baseline" if run_id.startswith("BASELINE_") else "runs") / run_id / f"{name}.html"
    command = render(raw, output, labels, f"{run_id} — {name}")
    return {"stage": "standalone", "run_id": run_id, "name": name, "input_mode": "RAW_DIRECT", "input_raw": exp_rel(raw), "input_raw_sha256": sha256(raw), "output_path": rel(output), "output_sha256": sha256(output), "labels": list(labels), "signal_order": list(labels), "command": command, "renderer": "scripts/josim-plot2.py", "layout": "sep_comb", "color": "dark", "phase_option": "2pi", "phase_convention": "raw P radians; display rad/(2*pi) turns; never SFQ count", "window_ps": [0.0, 200.0], "window_semantics": "whole-run raw timestamps", "temporary_input_sha256": None}


def comparison(left: Path, right: Path, left_name: str, right_name: str, output: Path, window: tuple[float, float] | None, title: str) -> dict[str, Any]:
    left_header = header(left)
    right_header = header(right)
    if left_header != right_header:
        raise RuntimeError("comparison requires identical raw headers")
    positions = {label: index for index, label in enumerate(left_header)}
    fd, temporary_name = tempfile.mkstemp(prefix="bvm-combination-", suffix=".csv", dir="/tmp")
    os.close(fd)
    temporary = Path(temporary_name)
    merged_labels = tuple([f"{label} [{left_name}]" for label in COMPARE_LABELS] + [f"{label} [{right_name}]" for label in COMPARE_LABELS])
    try:
        with left.open(newline="", encoding="utf-8-sig") as left_stream, right.open(newline="", encoding="utf-8-sig") as right_stream, temporary.open("w", newline="", encoding="utf-8") as output_stream:
            left_reader, right_reader = csv.reader(left_stream), csv.reader(right_stream)
            next(left_reader)
            next(right_reader)
            writer = csv.writer(output_stream)
            writer.writerow(["time", *merged_labels])
            for left_row, right_row in zip(left_reader, right_reader):
                if left_row[0] != right_row[0]:
                    raise RuntimeError("comparison raw time grids differ")
                time_ps = float(left_row[0]) * 1.0e12
                if window is None or window[0] <= time_ps < window[1]:
                    writer.writerow([left_row[0], *[left_row[positions[label]] for label in COMPARE_LABELS], *[right_row[positions[label]] for label in COMPARE_LABELS]])
        temporary_sha = sha256(temporary)
        command = [sys.executable, str(PLOTTER), str(temporary), "-x", str(output), "-t", "sep_comb", "-c", "dark", "-j", "2pi", "-w", title, "-s", *merged_labels]
        if not output.is_file():
            output.parent.mkdir(parents=True, exist_ok=True)
            completed = subprocess.run(command, cwd=REPO, capture_output=True, text=True, check=False)
            if completed.returncode != 0 or not output.is_file() or output.stat().st_size == 0:
                raise RuntimeError(f"comparison plot failed {output}: {completed.stderr[-1000:]}")
    finally:
        temporary.unlink(missing_ok=True)
    return {"stage": "comparison", "run_ids": [left_name, right_name], "input_raw_paths": [exp_rel(left), exp_rel(right)], "input_raw_sha256": [sha256(left), sha256(right)], "output_path": rel(output), "output_sha256": sha256(output), "labels": list(merged_labels), "command": command, "renderer": "scripts/josim-plot2.py", "layout": "sep_comb", "color": "dark", "phase_option": "2pi", "phase_convention": "P raw radians; display rad/(2*pi) turns; never SFQ count", "window_ps": list(window) if window else [0.0, 200.0], "window_semantics": "exact same-time stored rows", "temporary_input_sha256": temporary_sha, "temporary_input_deleted": not temporary.exists(), "input_mode": "TEMPORARY_EXACT_GRID_MERGE_DELETED_AFTER_RENDER"}


def main() -> int:
    state = json.loads(STATE.read_text(encoding="utf-8"))
    matrix = json.loads(MATRIX.read_text(encoding="utf-8"))
    if state.get("final_marker") != "EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW":
        raise RuntimeError("visualization allowed only after combination final marker")
    physical_runs = sorted(path for path in (EXP / "runs").iterdir() if path.is_dir())
    if not physical_runs:
        raise RuntimeError("no physical runs to visualize")
    entries: list[dict[str, Any]] = []
    for run_dir in physical_runs:
        entries.append(standalone(run_dir.name, run_dir / "raw.csv", "SIGNAL_TIMING", SIGNAL_LABELS))
    relevant_ids: set[str] = {"BASELINE_N2_0011", "BASELINE_N3_0111"}
    result_cache: dict[str, dict[str, Any]] = {}
    for point in matrix["points"]:
        result_path = EXP / "screening/results" / f"{point['point_id']}.json"
        if result_path.is_file():
            result = json.loads(result_path.read_text(encoding="utf-8"))
            result_cache[point["point_id"]] = result
            if result.get("candidate_class") in {"S", "A"}:
                relevant_ids.update({f"{point['point_id']}_N2_0011", f"{point['point_id']}_N3_0111"})
    for class_name in ("C",):
        point_id = next((pid for pid, result in result_cache.items() if result.get("candidate_class") == class_name), None)
        if point_id:
            relevant_ids.update({f"{point_id}_N2_0011", f"{point_id}_N3_0111"})
    extra_case_paths: dict[str, Path] = {"BASELINE_N2_0011": BASELINE["0011"], "BASELINE_N3_0111": BASELINE["0111"]}
    for point_id, result in result_cache.items():
        extra_case_paths[f"{point_id}_N2_0011"] = REPO / result["n2"]["raw_path"]
        extra_case_paths[f"{point_id}_N3_0111"] = REPO / result["n3"]["raw_path"]
    for run_id in sorted(relevant_ids - set(path.name for path in physical_runs)):
        if run_id in extra_case_paths:
            entries.extend([standalone(run_id, extra_case_paths[run_id], "QB_STATE", QB_LABELS), standalone(run_id, extra_case_paths[run_id], "JTL_CHAIN", JTL_LABELS)])
    for run_dir in physical_runs:
        run_id = run_dir.name
        if run_id in relevant_ids:
            entries.extend([standalone(run_id, run_dir / "raw.csv", "QB_STATE", QB_LABELS), standalone(run_id, run_dir / "raw.csv", "JTL_CHAIN", JTL_LABELS)])
    comparisons: list[dict[str, Any]] = []
    for point in matrix["points"]:
        result = result_cache.get(point["point_id"])
        if result is None:
            continue
        left = REPO / result["n2"]["raw_path"]
        right = REPO / result["n3"]["raw_path"]
        output = EXP / "visualization/plots/comparisons" / f"{point['point_id']}_N2_vs_N3.html"
        comparisons.append(comparison(left, right, f"{point['point_id']}_N2_0011", f"{point['point_id']}_N3_0111", output, None, f"{point['point_id']} N2 vs N3 whole-run comparison"))
        if result.get("candidate_class") in {"S", "A"}:
            for branch, baseline, suffix in (("n2", BASELINE["0011"], "N2_0011"), ("n3", BASELINE["0111"], "N3_0111")):
                candidate = REPO / result[branch]["raw_path"]
                focused_output = EXP / "visualization/plots/comparisons" / f"{point['point_id']}_{suffix}_focused_108_150.html"
                comparisons.append(comparison(baseline, candidate, f"BASELINE_{suffix}", f"{point['point_id']}_{suffix}", focused_output, (108.0, 150.0), f"{point['point_id']} {suffix} vs baseline focused 108–150 ps"))
    navigation_dir = EXP / "visualization/run_summaries"
    navigation_dir.mkdir(parents=True, exist_ok=True)
    actual_by_run = {path.name: path for path in physical_runs}
    for run_id, run_dir in actual_by_run.items():
        run_entries = [entry for entry in entries if entry["run_id"] == run_id]
        lines = [f"# {run_id} visualization navigation", "", "Standalone pages read raw.csv directly over 0–200 ps."]
        for entry in run_entries:
            output = REPO / entry["output_path"]
            lines.append(f"- [{entry['name']}.html]({os.path.relpath(output, navigation_dir)})")
        lines.extend(["", "P traces are raw radians; 2pi is rad/(2*pi) display only.", ""])
        (navigation_dir / f"{run_id}.md").write_text("\n".join(lines), encoding="utf-8")
    manifest = {"schema": "bvm-qb-two-parameter-combination-visualization-manifest-v1", "experiment_id": EXP.name, "created_at_local": now(), "renderer": "scripts/josim-plot2.py", "layout": "sep_comb", "color": "dark", "phase_option": "2pi", "whole_run_window_ps": [0.0, 200.0], "focused_windows": [[108.0, 150.0]] if any(item["window_ps"] == [108.0, 150.0] for item in comparisons) else [], "standalone_input_policy": "raw.csv direct; no derived standalone CSV", "comparison_input_policy": "temporary exact-grid merged CSV under /tmp, deleted after render", "standalone_entries": entries, "comparison_entries": comparisons, "raw_hashes": {entry["run_id"]: entry["input_raw_sha256"] for entry in entries if entry["run_id"] in actual_by_run}, "permanent_plot_policy": "one whole-run signal page for every physical run; baseline, C/A and representative C receive QB/JTL pages", "phase_not_sfq_count": True}
    (EXP / "visualization/manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "standalone_html_count": len(entries), "comparison_html_count": len(comparisons), "temporary_comparisons_deleted": all(item["temporary_input_deleted"] for item in comparisons)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
