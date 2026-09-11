#!/usr/bin/env python3
"""Render bounded L3 raw-direct whole-run and focused comparison plots."""

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
MATRIX = EXP / "screening/L3_MATRIX.json"
STATE = EXP / "screening/l3_state.json"
REFERENCE = {"0011": EXP / "references/l3_1p6/0011/raw.csv", "0111": EXP / "references/l3_1p6/0111/raw.csv"}
SIGNAL = ("I(I_WL1)", "I(I_BL1)", "I(I_SE1)", "I(I_WL2)", "I(I_BL2)", "I(I_SE2)", "I(I_WL3)", "I(I_BL3)", "I(I_SE3)", "I(I_WL4)", "I(I_BL4)", "I(I_SE4)", "V(COMMON_SL)", "I(B_JSL8)", "V(QBIN)", "V(QBOUT)", "V(JTL1_OUT)", "V(JTL2_OUT)", "V(JTL3_OUT)", "V(JTL4_OUT)", "V(JTL5_OUT)", "V(JTL6_OUT)", "I(R_TERM)")
QB = ("V(QBIN)", "I(LIN|XBQ1)", "P(BJ1|XBQ1)", "V(BJ1|XBQ1)", "I(BJ1|XBQ1)", "I(L1|XBQ1)", "I(L2|XBQ1)", "P(BJ2|XBQ1)", "V(BJ2|XBQ1)", "I(BJ2|XBQ1)", "V(QBOUT)")
JTL = tuple(["V(QBOUT)"] + [f"P(B01|XJTL1_{stage})" for stage in range(1, 7)] + [f"V(JTL{stage}_OUT)" for stage in range(1, 7)] + ["I(R_TERM)"])
COMPARE = ("P(BJ1|XBQ1)", "P(BJ2|XBQ1)", "V(QBOUT)", "V(JTL1_OUT)", "V(JTL2_OUT)", "V(JTL3_OUT)", "V(JTL4_OUT)", "V(JTL5_OUT)", "V(JTL6_OUT)", "I(R_TERM)")


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


def get_header(path: Path) -> list[str]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        return next(csv.reader(stream))


def plot(raw: Path, output: Path, labels: tuple[str, ...], title: str) -> list[str]:
    header = get_header(raw)
    missing = [label for label in labels if label not in header]
    if missing:
        raise RuntimeError(f"missing plot labels {missing}: {raw}")
    command = [sys.executable, str(PLOTTER), str(raw), "-x", str(output), "-t", "sep_comb", "-c", "dark", "-j", "2pi", "-w", title, "-s", *labels]
    if not output.is_file():
        output.parent.mkdir(parents=True, exist_ok=True)
        completed = subprocess.run(command, cwd=REPO, capture_output=True, text=True, check=False)
        if completed.returncode != 0 or not output.is_file() or output.stat().st_size == 0:
            raise RuntimeError(f"plot failed: {output}: {completed.stderr[-1000:]}")
    return command


def standalone(run_id: str, raw: Path, name: str, labels: tuple[str, ...]) -> dict[str, Any]:
    folder = "reference" if run_id.startswith("REFERENCE_") else "runs"
    output = EXP / "visualization/plots" / folder / run_id / f"{name}.html"
    command = plot(raw, output, labels, f"{run_id} — {name}")
    return {"stage": "standalone", "run_id": run_id, "name": name, "input_mode": "RAW_DIRECT", "input_raw": exp_rel(raw), "input_raw_sha256": sha256(raw), "output_path": rel(output), "output_sha256": sha256(output), "labels": list(labels), "signal_order": list(labels), "command": command, "renderer": "scripts/josim-plot2.py", "layout": "sep_comb", "color": "dark", "phase_option": "2pi", "phase_convention": "raw P radians; display rad/(2*pi) turns; never SFQ count", "window_ps": [0.0, 200.0], "temporary_input_sha256": None}


def focused_comparison(cases: list[tuple[str, Path]], output: Path, title: str) -> dict[str, Any]:
    headers = [get_header(raw) for _name, raw in cases]
    if any(item != headers[0] for item in headers[1:]):
        raise RuntimeError("L3 comparison headers differ")
    positions = {label: index for index, label in enumerate(headers[0])}
    labels = tuple(f"{label} [{name}]" for name, _raw in cases for label in COMPARE)
    fd, temporary_name = tempfile.mkstemp(prefix="bvm-l3-highside-", suffix=".csv", dir="/tmp")
    os.close(fd)
    temporary = Path(temporary_name)
    streams = []
    try:
        readers = []
        for _name, raw in cases:
            stream = raw.open(newline="", encoding="utf-8-sig")
            streams.append(stream)
            reader = csv.reader(stream)
            next(reader)
            readers.append(reader)
        with temporary.open("w", newline="", encoding="utf-8") as output_stream:
            writer = csv.writer(output_stream)
            writer.writerow(["time", *labels])
            for group in zip(*readers):
                if any(row[0] != group[0][0] for row in group[1:]):
                    raise RuntimeError("L3 comparison time grids differ")
                time_ps = float(group[0][0]) * 1.0e12
                if 108.0 <= time_ps < 150.0:
                    values = []
                    for row in group:
                        values.extend(row[positions[label]] for label in COMPARE)
                    writer.writerow([group[0][0], *values])
        temporary_sha = sha256(temporary)
        command = [sys.executable, str(PLOTTER), str(temporary), "-x", str(output), "-t", "sep_comb", "-c", "dark", "-j", "2pi", "-w", title, "-s", *labels]
        if not output.is_file():
            output.parent.mkdir(parents=True, exist_ok=True)
            completed = subprocess.run(command, cwd=REPO, capture_output=True, text=True, check=False)
            if completed.returncode != 0 or not output.is_file() or output.stat().st_size == 0:
                raise RuntimeError(f"comparison failed: {output}: {completed.stderr[-1000:]}")
    finally:
        for stream in streams:
            stream.close()
        temporary.unlink(missing_ok=True)
    return {"stage": "focused_comparison", "run_ids": [name for name, _raw in cases], "input_raw_paths": [exp_rel(raw) for _name, raw in cases], "input_raw_sha256": [sha256(raw) for _name, raw in cases], "output_path": rel(output), "output_sha256": sha256(output), "labels": list(labels), "command": command, "renderer": "scripts/josim-plot2.py", "layout": "sep_comb", "color": "dark", "phase_option": "2pi", "phase_convention": "P raw radians; display rad/(2*pi) turns; never SFQ count", "window_ps": [108.0, 150.0], "window_semantics": "exact same-time stored rows", "temporary_input_sha256": temporary_sha, "temporary_input_deleted": not temporary.exists(), "input_mode": "TEMPORARY_EXACT_GRID_MERGE_DELETED_AFTER_RENDER"}


def main() -> int:
    state = json.loads(STATE.read_text(encoding="utf-8"))
    matrix = json.loads(MATRIX.read_text(encoding="utf-8"))
    if state.get("final_marker") != "EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW":
        raise RuntimeError("L3 visualization requires final marker")
    run_dirs = sorted(path for path in (EXP / "runs").iterdir() if path.is_dir())
    entries: list[dict[str, Any]] = []
    for run_dir in run_dirs:
        entries.extend([standalone(run_dir.name, run_dir / "raw.csv", "SIGNAL_TIMING", SIGNAL), standalone(run_dir.name, run_dir / "raw.csv", "QB_STATE", QB), standalone(run_dir.name, run_dir / "raw.csv", "JTL_CHAIN", JTL)])
    entries.extend([standalone("REFERENCE_L3_1p6_0011", REFERENCE["0011"], "SIGNAL_TIMING", SIGNAL), standalone("REFERENCE_L3_1p6_0011", REFERENCE["0011"], "QB_STATE", QB), standalone("REFERENCE_L3_1p6_0011", REFERENCE["0011"], "JTL_CHAIN", JTL), standalone("REFERENCE_L3_1p6_0111", REFERENCE["0111"], "SIGNAL_TIMING", SIGNAL), standalone("REFERENCE_L3_1p6_0111", REFERENCE["0111"], "QB_STATE", QB), standalone("REFERENCE_L3_1p6_0111", REFERENCE["0111"], "JTL_CHAIN", JTL)])
    result_cache = {point["point_id"]: json.loads((EXP / "screening/results" / f"{point['point_id']}_corrected_v2.json").read_text(encoding="utf-8")) for point in matrix["points"] if (EXP / "screening/results" / f"{point['point_id']}_corrected_v2.json").is_file()}
    comparisons: list[dict[str, Any]] = []
    for axis, mask, suffix in (("L3", "0011", "N2_0011"), ("L3", "0111", "N3_0111")):
        cases = [("L3_1p6", REFERENCE[mask])]
        for point in matrix["points"]:
            result = result_cache.get(point["point_id"])
            if result:
                branch = "n2" if mask == "0011" else "n3"
                cases.append((point["point_id"], REPO / result[branch]["raw_path"]))
        if len(cases) >= 2:
            comparisons.append(focused_comparison(cases, EXP / "visualization/plots/comparisons" / f"L3_{suffix}_focused_108_150.html", f"L3 highside {suffix} focused 108–150 ps"))
    navigation = EXP / "visualization/run_summaries"
    navigation.mkdir(parents=True, exist_ok=True)
    for run_dir in run_dirs:
        items = [entry for entry in entries if entry["run_id"] == run_dir.name]
        lines = [f"# {run_dir.name} visualization navigation", "", "Standalone pages read raw.csv directly over 0–200 ps."]
        for entry in items:
            lines.append(f"- [{entry['name']}.html]({os.path.relpath(REPO / entry['output_path'], navigation)})")
        lines.extend(["", "P traces are raw radians; rad/(2*pi) is display/navigation only.", ""])
        (navigation / f"{run_dir.name}.md").write_text("\n".join(lines), encoding="utf-8")
    manifest = {"schema": "bvm-qb-l3-highside-visualization-manifest-v1", "experiment_id": EXP.name, "created_at_local": now(), "renderer": "scripts/josim-plot2.py", "layout": "sep_comb", "color": "dark", "phase_option": "2pi", "whole_run_window_ps": [0.0, 200.0], "focused_windows": [[108.0, 150.0]] if comparisons else [], "standalone_input_policy": "raw.csv direct", "comparison_input_policy": "temporary exact-grid L3 merge under /tmp, deleted after render", "standalone_entries": entries, "comparison_entries": comparisons, "raw_hashes": {entry["run_id"]: entry["input_raw_sha256"] for entry in entries if entry["run_id"] in {path.name for path in run_dirs}}, "phase_not_sfq_count": True}
    (EXP / "visualization/manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "standalone_html_count": len(entries), "comparison_html_count": len(comparisons), "temporary_comparisons_deleted": all(item["temporary_input_deleted"] for item in comparisons)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
