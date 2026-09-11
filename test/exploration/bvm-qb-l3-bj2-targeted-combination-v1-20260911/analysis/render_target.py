#!/usr/bin/env python3
"""Render V2.1 semantic standalone and focused raw-direct comparison pages."""

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
STATE = EXP / "screening/target_state.json"
MATRIX = EXP / "screening/TARGET_MATRIX.json"
SCREENING_MASKS = ("0011", "0111")
REFERENCE_CASES = {
    "CANONICAL_L3_1p3_BJ2_2p0": {"0011": EXP / "references/canonical_l3p13/0011/raw.csv", "0111": EXP / "references/canonical_l3p13/0111/raw.csv"},
    "L3_2p0_BJ2_2p0": {"0011": EXP / "references/l3p20/0011/raw.csv", "0111": EXP / "references/l3p20/0111/raw.csv"},
    "L3_1p3_BJ2_2p2": {"0011": EXP / "references/bj2p22_l3p13/0011/raw.csv", "0111": EXP / "references/bj2p22_l3p13/0111/raw.csv"},
}
VIEW_LABELS = {
    "01_SIGNAL_TIMING": ("I(I_WL1)", "I(I_BL1)", "I(I_SE1)", "I(I_WL2)", "I(I_BL2)", "I(I_SE2)", "I(I_WL3)", "I(I_BL3)", "I(I_SE3)", "I(I_WL4)", "I(I_BL4)", "I(I_SE4)", "V(COMMON_SL)", "I(B_JSL8)", "V(QBIN)", "V(QBOUT)", "I(R_TERM)"),
    "02_BVM_STATE": ("P(B_JM1|XBVM1)", "V(B_JM1|XBVM1)", "I(B_JM1|XBVM1)", "P(B_JM2|XBVM1)", "V(B_JM2|XBVM1)", "I(B_JM2|XBVM1)", "P(B_JS1|XBVM1)", "V(B_JS1|XBVM1)", "I(B_JS1|XBVM1)", "P(B_JS2|XBVM1)", "V(B_JS2|XBVM1)", "I(B_JS2|XBVM1)", "I(L_SL|XBVM1)", "V(L_SL|XBVM1)", "V(COMMON_SL)"),
    "03_JSL_CHAIN": tuple(item for index in range(1, 9) for item in (f"P(B_JSL{index})", f"V(B_JSL{index})", f"I(B_JSL{index})")) + ("V(COMMON_SL)", "V(QBIN)"),
    "04_QB_STATE": ("V(QBIN)", "I(LIN|XBQ1)", "V(LIN|XBQ1)", "I(L1|XBQ1)", "V(L1|XBQ1)", "I(L2|XBQ1)", "V(L2|XBQ1)", "I(L3|XBQ1)", "V(L3|XBQ1)", "P(BJS|XBQ1)", "V(BJS|XBQ1)", "I(BJS|XBQ1)", "P(BJ1|XBQ1)", "V(BJ1|XBQ1)", "I(BJ1|XBQ1)", "P(BJ2|XBQ1)", "V(BJ2|XBQ1)", "I(BJ2|XBQ1)", "V(QBOUT)"),
    "05_JTL_CHAIN": tuple(item for stage in range(1, 7) for item in (f"P(B01|XJTL1_{stage})", f"V(B01|XJTL1_{stage})", f"I(B01|XJTL1_{stage})", f"P(B02|XJTL1_{stage})", f"V(B02|XJTL1_{stage})", f"I(B02|XJTL1_{stage})", f"V(JTL{stage}_OUT)")) + ("I(R_TERM)",),
}
COMPARE_LABELS = ("I(B_JSL8)", "I(L1|XBQ1)", "I(L2|XBQ1)", "I(L3|XBQ1)", "P(BJ1|XBQ1)", "P(BJ2|XBQ1)", "V(QBOUT)", "V(JTL1_OUT)", "V(JTL2_OUT)", "V(JTL3_OUT)", "V(JTL4_OUT)", "V(JTL5_OUT)", "V(JTL6_OUT)", "I(R_TERM)")


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


def plot(raw: Path, output: Path, labels: tuple[str, ...], title: str) -> list[str]:
    actual_header = header(raw)
    missing = [label for label in labels if label not in actual_header]
    if missing:
        raise RuntimeError(f"missing visualization labels {missing}: {raw}")
    command = [sys.executable, str(PLOTTER), str(raw), "-x", str(output), "-t", "sep_comb", "-c", "dark", "-j", "2pi", "-w", title, "-s", *labels]
    output.parent.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(command, cwd=REPO, capture_output=True, text=True, check=False)
    if completed.returncode != 0 or not output.is_file() or output.stat().st_size == 0:
        raise RuntimeError(f"plot failed: {output}: {completed.stderr[-1000:]}")
    return command


def standalone(run_id: str, raw: Path, view: str, labels: tuple[str, ...]) -> dict[str, Any]:
    output = EXP / "visualization/plots" / "runs" / run_id / f"{view}.html"
    command = plot(raw, output, labels, f"{run_id} — {view}")
    return {"stage": "standalone", "semantic_view": view, "run_id": run_id, "input_mode": "RAW_DIRECT", "input_raw": exp_rel(raw), "input_raw_sha256": sha256(raw), "output_path": rel(output), "output_sha256": sha256(output), "labels": list(labels), "signal_order": list(labels), "command": command, "renderer": "scripts/josim-plot2.py", "layout": "sep_comb", "color": "dark", "phase_option": "2pi", "phase_convention": "raw P radians; display rad/(2*pi) turns; never SFQ count", "window_ps": [0.0, 200.0], "temporary_input_sha256": None}


def write_navigation(run_id: str) -> None:
    lines = [f"# {run_id} visualization navigation", "", "Standalone pages read raw.csv directly over 0–200 ps."]
    for view in VIEW_LABELS:
        lines.append(f"- [{view}.html](../plots/runs/{run_id}/{view}.html)")
    lines.extend(["", "P traces are raw radians; rad/(2*pi) is display/navigation only."])
    path = EXP / "visualization/run_summaries" / f"{run_id}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def focused_comparison(cases: list[tuple[str, Path]], branch: str) -> dict[str, Any]:
    actual_headers = [header(raw) for _name, raw in cases]
    if any(item != actual_headers[0] for item in actual_headers[1:]):
        raise RuntimeError(f"comparison headers differ: {branch}")
    positions = {label: index for index, label in enumerate(actual_headers[0])}
    conditioned_labels = tuple(f"{label} [{name}]" for name, _raw in cases for label in COMPARE_LABELS)
    fd, temporary_name = tempfile.mkstemp(prefix="bvm-target-comparison-", suffix=".csv", dir="/tmp")
    os.close(fd)
    temporary = Path(temporary_name)
    output = EXP / "visualization/plots" / "comparisons" / f"{branch}_focused_108_150.html"
    streams = []
    try:
        readers = []
        for _name, raw in cases:
            stream = raw.open(newline="", encoding="utf-8-sig")
            streams.append(stream)
            reader = csv.reader(stream)
            next(reader)
            readers.append(reader)
        with temporary.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.writer(stream)
            writer.writerow(["time", *conditioned_labels])
            for group in zip(*readers):
                if any(abs(float(row[0]) - float(group[0][0])) > 1.0e-24 for row in group[1:]):
                    raise RuntimeError(f"comparison time grids differ: {branch}")
                time_ps = float(group[0][0]) * 1.0e12
                if 108.0 <= time_ps < 150.0:
                    values = []
                    for row in group:
                        values.extend(row[positions[label]] for label in COMPARE_LABELS)
                    writer.writerow([group[0][0], *values])
        temporary_sha = sha256(temporary)
        command = plot(temporary, output, conditioned_labels, f"{branch} — canonical / L3-only / BJ2-only / target — 108–150 ps")
        return {"stage": "focused_comparison", "branch": branch, "cases": [{"name": name, "input_raw": exp_rel(raw), "input_raw_sha256": sha256(raw)} for name, raw in cases], "window_ps": [108.0, 150.0], "input_policy": "temporary exact same-grid rows; no interpolation/resampling", "temporary_input_sha256": temporary_sha, "temporary_input_deleted": True, "output_path": rel(output), "output_sha256": sha256(output), "labels": list(conditioned_labels), "command": command, "renderer": "scripts/josim-plot2.py", "layout": "sep_comb", "color": "dark", "phase_option": "2pi", "phase_convention": "raw P radians; display rad/(2*pi) turns; never SFQ count"}
    finally:
        for stream in streams:
            stream.close()
        if temporary.exists():
            temporary.unlink()


def main() -> int:
    state = json.loads(STATE.read_text(encoding="utf-8"))
    matrix = json.loads(MATRIX.read_text(encoding="utf-8"))
    point = matrix["points"][0]
    raw_by_mask = {mask: REPO / state["screening_cases"][mask]["raw_path"] for mask in SCREENING_MASKS}
    for mask, case in state.get("validation_cases", {}).items():
        raw_by_mask[mask] = REPO / case["raw_path"]
    standalone_entries: list[dict[str, Any]] = []
    for mask, raw in sorted(raw_by_mask.items()):
        run_id = f"TARGET_L3_2_BJ2_2p2_{mask}"
        for view, labels in VIEW_LABELS.items():
            standalone_entries.append(standalone(run_id, raw, view, labels))
        write_navigation(run_id)
    comparison_entries = []
    for mask, branch in (("0011", "N2"), ("0111", "N3")):
        comparison_cases = [(name, cases[mask]) for name, cases in REFERENCE_CASES.items()]
        comparison_cases.append(("TARGET_L3_2_BJ2_2p2", raw_by_mask[mask]))
        comparison_entries.append(focused_comparison(comparison_cases, branch))
    record = {"schema": "bvm-qb-l3-bj2-targeted-combination-visualization-v2.1", "experiment_id": EXP.name, "created_at_local": now(), "renderer": "scripts/josim-plot2.py", "semantic_structure": ["01_SIGNAL_TIMING", "02_BVM_STATE", "03_JSL_CHAIN", "04_QB_STATE", "05_JTL_CHAIN"], "standalone_input_policy": "raw.csv direct; every executed case has all five subsystem views", "comparison_input_policy": "temporary exact same-grid merged CSV, 108<=t<150 ps, deleted after render", "whole_run_window_ps": [0.0, 200.0], "focused_window_ps": [108.0, 150.0], "standalone_entries": standalone_entries, "comparison_entries": comparison_entries, "raw_hashes": {entry["run_id"]: entry["input_raw_sha256"] for entry in standalone_entries if entry["semantic_view"] == "01_SIGNAL_TIMING"}, "plots_not_authority": True, "phase_navigation_only": True, "not_sfq_count": True, "matrix_point_id": point["point_id"]}
    output = EXP / "visualization/manifest.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "standalone_html_count": len(standalone_entries), "comparison_html_count": len(comparison_entries), "semantic_structure": record["semantic_structure"], "temporary_comparisons_deleted": all(item["temporary_input_deleted"] is True for item in comparison_entries) and not list(Path("/tmp").glob("bvm-target-comparison-*.csv"))}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
