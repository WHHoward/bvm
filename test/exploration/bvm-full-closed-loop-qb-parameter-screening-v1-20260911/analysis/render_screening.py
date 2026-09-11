#!/usr/bin/env python3
"""Render compact raw-direct navigation pages after screening is complete."""

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
STATE = EXP / "screening/screening_state.json"
MATRIX = EXP / "screening/SCREENING_MATRIX.json"
BASELINE_RAW = {
    "BASELINE_N2_0011": EXP / "references/baseline_rj2p12/ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_0011/raw.csv",
    "BASELINE_N3_0111": EXP / "references/baseline_rj2p12/ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_0111/raw.csv",
}
SIGNAL_LABELS = ("I(I_WL1)", "I(I_BL1)", "I(I_SE1)", "I(I_WL2)", "I(I_BL2)", "I(I_SE2)", "I(I_WL3)", "I(I_BL3)", "I(I_SE3)", "I(I_WL4)", "I(I_BL4)", "I(I_SE4)", "V(COMMON_SL)", "I(B_JSL8)", "V(QBIN)", "V(QBOUT)", "V(JTL1_OUT)", "V(JTL2_OUT)", "V(JTL3_OUT)", "V(JTL4_OUT)", "V(JTL5_OUT)", "V(JTL6_OUT)", "I(R_TERM)")
QB_LABELS = ("V(QBIN)", "I(LIN|XBQ1)", "P(BJS|XBQ1)", "V(BJS|XBQ1)", "I(BJS|XBQ1)", "P(BJ1|XBQ1)", "V(BJ1|XBQ1)", "I(BJ1|XBQ1)", "I(L1|XBQ1)", "I(L2|XBQ1)", "P(BJ2|XBQ1)", "V(BJ2|XBQ1)", "I(BJ2|XBQ1)", "V(QBOUT)")
JTL_LABELS = tuple(["V(QBOUT)"] + [f"P(B01|XJTL1_{stage})" for stage in range(1, 7)] + [f"V(JTL{stage}_OUT)" for stage in range(1, 7)] + ["I(R_TERM)"])


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


def raw_path_from_result(result: dict[str, Any], branch: str) -> Path:
    return REPO / result[branch]["raw_path"]


def raw_header(path: Path) -> tuple[list[str], list[list[str]]]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.reader(stream)
        header = next(reader)
        rows = list(reader)
    return header, rows


def render(raw: Path, output: Path, labels: tuple[str, ...], title: str) -> list[str]:
    missing = [label for label in labels if label not in raw_header(raw)[0]]
    if missing:
        raise RuntimeError(f"visualization labels missing from {raw}: {missing}")
    command = [sys.executable, str(PLOTTER), str(raw), "-x", str(output), "-t", "sep_comb", "-c", "dark", "-j", "2pi", "-w", title, "-s", *labels]
    if output.is_file() and output.stat().st_size > 0:
        return command
    output.parent.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(command, cwd=REPO, capture_output=True, text=True, check=False)
    if completed.returncode != 0 or not output.is_file() or output.stat().st_size == 0:
        raise RuntimeError(f"plot render failed for {raw} -> {output}: {completed.stderr[-1000:]}")
    return command


def standalone_entry(run_id: str, raw: Path, name: str, labels: tuple[str, ...]) -> dict[str, Any]:
    output = EXP / "visualization/plots" / ("baseline" if run_id.startswith("BASELINE_") else "runs") / run_id / f"{name}.html"
    command = render(raw, output, labels, f"{run_id} — {name}")
    return {"stage": "standalone", "run_id": run_id, "name": name, "input_mode": "RAW_DIRECT", "input_raw": exp_rel(raw), "input_raw_sha256": sha256(raw), "output_path": rel(output), "output_sha256": sha256(output), "labels": list(labels), "signal_order": list(labels), "command": command, "renderer": "scripts/josim-plot2.py", "layout": "sep_comb", "color": "dark", "phase_option": "2pi", "phase_convention": "raw P radians; plot2 displays rad/(2*pi) turns; never SFQ count", "window_ps": [0.0, 200.0], "window_semantics": "whole-run raw timestamps", "temporary_input_sha256": None}


def focused_merge(baseline: Path, candidate: Path, labels: tuple[str, ...], output: Path, title: str, baseline_name: str, candidate_name: str) -> dict[str, Any]:
    base_header, base_rows = raw_header(baseline)
    cand_header, cand_rows = raw_header(candidate)
    if base_header != cand_header or len(base_rows) != len(cand_rows):
        raise RuntimeError("focused comparison requires identical raw headers and sample counts")
    if any(left[0] != right[0] for left, right in zip(base_rows, cand_rows)):
        raise RuntimeError("focused comparison requires exact same-time protocol grids")
    base_pos = {name: index for index, name in enumerate(base_header)}
    merged_labels = tuple([f"{label} [{baseline_name}]" for label in labels] + [f"{label} [{candidate_name}]" for label in labels])
    fd, temporary_name = tempfile.mkstemp(prefix="bvm-qb-screen-", suffix=".csv", dir="/tmp")
    os.close(fd)
    temporary = Path(temporary_name)
    try:
        with temporary.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.writer(stream)
            writer.writerow(["time", *merged_labels])
            for left, right in zip(base_rows, cand_rows):
                time_ps = float(left[0]) * 1.0e12
                if 108.0 <= time_ps < 150.0:
                    writer.writerow([left[0], *[left[base_pos[label]] for label in labels], *[right[base_pos[label]] for label in labels]])
        temporary_sha = sha256(temporary)
        command = [sys.executable, str(PLOTTER), str(temporary), "-x", str(output), "-t", "sep_comb", "-c", "dark", "-j", "2pi", "-w", title, "-s", *merged_labels]
        if not (output.is_file() and output.stat().st_size > 0):
            output.parent.mkdir(parents=True, exist_ok=True)
            completed = subprocess.run(command, cwd=REPO, capture_output=True, text=True, check=False)
            if completed.returncode != 0 or not output.is_file() or output.stat().st_size == 0:
                raise RuntimeError(f"focused comparison render failed: {completed.stderr[-1000:]}")
    finally:
        temporary.unlink(missing_ok=True)
    return {"stage": "focused_comparison", "run_ids": [baseline_name, candidate_name], "input_raw_paths": [rel(baseline), rel(candidate)], "input_raw_sha256": [sha256(baseline), sha256(candidate)], "output_path": rel(output), "output_sha256": sha256(output), "labels": list(merged_labels), "command": command, "renderer": "scripts/josim-plot2.py", "layout": "sep_comb", "color": "dark", "phase_option": "2pi", "phase_convention": "P raw radians; plot2 uses rad/(2*pi) display; never SFQ count", "window_ps": [108.0, 150.0], "window_semantics": "exact stored rows in focused window; same-time pair only", "temporary_input_sha256": temporary_sha, "temporary_input_deleted": not temporary.exists(), "input_mode": "TEMPORARY_EXACT_GRID_MERGE_DELETED_AFTER_RENDER"}


def add_case(cases: dict[str, dict[str, Any]], run_id: str, raw: Path, role: str) -> None:
    cases.setdefault(run_id, {"raw": raw, "roles": []})["roles"].append(role)


def main() -> int:
    state = json.loads(STATE.read_text(encoding="utf-8"))
    matrix = json.loads(MATRIX.read_text(encoding="utf-8"))
    if state.get("final_marker") != "EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW":
        raise RuntimeError("rendering is allowed only after screening final marker")
    cases: dict[str, dict[str, Any]] = {}
    for run_id, raw in BASELINE_RAW.items():
        add_case(cases, run_id, raw, "canonical baseline reference")
    selected_result_ids: set[str] = set()
    result_cache: dict[str, dict[str, Any]] = {}
    for point in matrix["points"]:
        path = EXP / "screening/results" / f"{point['point_id']}.json"
        if path.is_file():
            result = json.loads(path.read_text(encoding="utf-8"))
            result_cache[point["point_id"]] = result
            if result.get("candidate_class") in {"S", "A"}:
                selected_result_ids.add(point["point_id"])
                add_case(cases, f"{point['point_id']}_N2_0011", raw_path_from_result(result, "n2"), f"candidate class {result['candidate_class']}")
                add_case(cases, f"{point['point_id']}_N3_0111", raw_path_from_result(result, "n3"), f"candidate class {result['candidate_class']}")
    for class_name in ("C", "D"):
        representative = next((pid for pid, result in result_cache.items() if result.get("candidate_class") == class_name), None)
        if representative is not None:
            result = result_cache[representative]
            add_case(cases, f"{representative}_N2_0011", raw_path_from_result(result, "n2"), f"representative {class_name}")
            add_case(cases, f"{representative}_N3_0111", raw_path_from_result(result, "n3"), f"representative {class_name}")
    # Every physical run gets at least one navigation page so the package
    # builder can prove that all authorized runs have a visual entry.  The
    # additional QB/JTL pages are restricted to baseline and S/A or C/D
    # evidence, keeping the permanent set bounded.
    for run_dir in sorted(path for path in (EXP / "runs").iterdir() if path.is_dir()):
        add_case(cases, run_dir.name, run_dir / "raw.csv", "executed run navigation")

    standalone: list[dict[str, Any]] = []
    navigation_dir = EXP / "visualization/run_summaries"
    navigation_dir.mkdir(parents=True, exist_ok=True)
    for run_id, item in cases.items():
        raw = item["raw"]
        names = [("SIGNAL_PATH", SIGNAL_LABELS)]
        if run_id.startswith("BASELINE_") or any(role.startswith("candidate class") or role.startswith("representative") for role in item["roles"]):
            names.extend([("QB_STATE", QB_LABELS), ("JTL_CHAIN", JTL_LABELS)])
        entries = [standalone_entry(run_id, raw, name, labels) for name, labels in names]
        standalone.extend(entries)
        nav = [f"# {run_id} — visualization navigation", "", "All standalone pages read the immutable raw.csv directly and cover 0–200 ps.", ""]
        for entry in entries:
            output = Path(entry["output_path"])
            relative_link = os.path.relpath(REPO / output, navigation_dir)
            nav.append(f"- [{entry['name']}.html]({relative_link})")
        nav.extend(["", "P traces are raw radians; the registered 2pi display is rad/(2*pi), not an SFQ count.", ""])
        (navigation_dir / f"{run_id}.md").write_text("\n".join(nav), encoding="utf-8")

    comparisons: list[dict[str, Any]] = []
    baseline_n2 = BASELINE_RAW["BASELINE_N2_0011"]
    baseline_n3 = BASELINE_RAW["BASELINE_N3_0111"]
    for pid in sorted(selected_result_ids):
        result = result_cache[pid]
        for branch, baseline, suffix in (("n2", baseline_n2, "N2_0011"), ("n3", baseline_n3, "N3_0111")):
            candidate = raw_path_from_result(result, branch)
            output = EXP / "visualization/plots/comparisons" / f"{pid}_{suffix}_focused_108_150.html"
            comparisons.append(focused_merge(baseline, candidate, ("P(BJ1|XBQ1)", "P(BJ2|XBQ1)", "V(BJ1|XBQ1)", "V(BJ2|XBQ1)", "I(L1|XBQ1)", "I(L2|XBQ1)", "V(QBOUT)", "V(JTL1_OUT)", "V(JTL2_OUT)", "V(JTL3_OUT)", "V(JTL4_OUT)", "V(JTL5_OUT)", "V(JTL6_OUT)", "I(R_TERM)"), output, f"{pid} {suffix} vs baseline focused 108–150 ps", f"BASELINE_{suffix}", f"{pid}_{suffix}"))
    if not comparisons:
        representative = next((pid for pid, result in result_cache.items() if result.get("candidate_class") in {"C", "D", "B"}), None)
        if representative is not None:
            result = result_cache[representative]
            candidate = raw_path_from_result(result, "n3")
            output = EXP / "visualization/plots/comparisons" / f"{representative}_N3_0111_focused_108_150.html"
            comparisons.append(focused_merge(baseline_n3, candidate, ("P(BJ1|XBQ1)", "P(BJ2|XBQ1)", "V(BJ1|XBQ1)", "V(BJ2|XBQ1)", "I(L1|XBQ1)", "I(L2|XBQ1)", "V(QBOUT)", "V(JTL1_OUT)", "V(JTL2_OUT)", "V(JTL3_OUT)", "V(JTL4_OUT)", "V(JTL5_OUT)", "V(JTL6_OUT)", "I(R_TERM)"), output, f"{representative} N3 vs baseline focused 108–150 ps", "BASELINE_N3_0111", f"{representative}_N3_0111"))
    manifest = {"schema": "bvm-full-closed-loop-qb-screening-visualization-manifest-v1", "experiment_id": EXP.name, "created_at_local": now(), "renderer": "scripts/josim-plot2.py", "layout": "sep_comb", "color": "dark", "phase_option": "2pi", "whole_run_window_ps": [0.0, 200.0], "focused_windows": [[108.0, 150.0]] if comparisons else [], "standalone_input_policy": "raw.csv direct; no derived standalone CSV", "comparison_input_policy": "temporary same-grid merged CSV under /tmp, exact rows 108–150 ps, deleted after render", "standalone_entries": standalone, "comparison_entries": comparisons, "raw_hashes": {entry["run_id"]: entry["input_raw_sha256"] for entry in standalone if entry["run_id"] in {path.name for path in (EXP / "runs").iterdir() if path.is_dir()}}, "selected_candidate_result_ids": sorted(selected_result_ids), "permanent_plot_policy": "baseline, all S/A, representative C/D; one SIGNAL_PATH page for every executed run", "plots_not_raw_authority": True, "phase_not_sfq_count": True}
    (EXP / "visualization/manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "standalone_html_count": len(standalone), "comparison_html_count": len(comparisons), "selected_candidate_result_ids": sorted(selected_result_ids), "temporary_comparisons_deleted": all(item["temporary_input_deleted"] for item in comparisons)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
