#!/usr/bin/env python3
"""Render the four-run boundary evidence and two-axis focused comparisons."""

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
MATRIX = EXP / "boundary/BOUNDARY_MATRIX.json"
STATE = EXP / "boundary/boundary_state.json"
BASELINE = {"0011": EXP / "references/canonical_baseline/0011/raw.csv", "0111": EXP / "references/canonical_baseline/0111/raw.csv"}
ENDPOINTS = {
    "L2_LOW": {"0011": EXP / "references/endpoints/l2_low_l3p16/0011/raw.csv", "0111": EXP / "references/endpoints/l2_low_l3p16/0111/raw.csv"},
    "L2_HIGH": {"0011": EXP / "references/endpoints/l2_high_l3p16/0011/raw.csv", "0111": EXP / "references/endpoints/l2_high_l3p16/0111/raw.csv"},
    "IB_LOW": {"0011": EXP / "references/endpoints/ib_low_l3p16/0011/raw.csv", "0111": EXP / "references/endpoints/ib_low_l3p16/0111/raw.csv"},
    "IB_HIGH": {"0011": EXP / "references/endpoints/ib_high_l3p16/0011/raw.csv", "0111": EXP / "references/endpoints/ib_high_l3p16/0111/raw.csv"},
}
SIGNAL_LABELS = ("I(I_WL1)", "I(I_BL1)", "I(I_SE1)", "I(I_WL2)", "I(I_BL2)", "I(I_SE2)", "I(I_WL3)", "I(I_BL3)", "I(I_SE3)", "I(I_WL4)", "I(I_BL4)", "I(I_SE4)", "V(COMMON_SL)", "I(B_JSL8)", "V(QBIN)", "V(QBOUT)", "V(JTL1_OUT)", "V(JTL2_OUT)", "V(JTL3_OUT)", "V(JTL4_OUT)", "V(JTL5_OUT)", "V(JTL6_OUT)", "I(R_TERM)")
QB_LABELS = ("V(QBIN)", "I(LIN|XBQ1)", "P(BJ1|XBQ1)", "V(BJ1|XBQ1)", "I(BJ1|XBQ1)", "I(L1|XBQ1)", "I(L2|XBQ1)", "P(BJ2|XBQ1)", "V(BJ2|XBQ1)", "I(BJ2|XBQ1)", "V(QBOUT)")
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
        raise RuntimeError(f"missing plot labels {missing}: {raw}")
    command = [sys.executable, str(PLOTTER), str(raw), "-x", str(output), "-t", "sep_comb", "-c", "dark", "-j", "2pi", "-w", title, "-s", *labels]
    if not output.is_file():
        output.parent.mkdir(parents=True, exist_ok=True)
        completed = subprocess.run(command, cwd=REPO, capture_output=True, text=True, check=False)
        if completed.returncode != 0 or not output.is_file() or output.stat().st_size == 0:
            raise RuntimeError(f"plot failed: {output}: {completed.stderr[-1000:]}")
    return command


def standalone(run_id: str, raw: Path, name: str, labels: tuple[str, ...]) -> dict[str, Any]:
    output = EXP / "visualization/plots" / ("baseline" if run_id.startswith("BASELINE_") else "runs") / run_id / f"{name}.html"
    command = render(raw, output, labels, f"{run_id} — {name}")
    return {"stage": "standalone", "run_id": run_id, "name": name, "input_mode": "RAW_DIRECT", "input_raw": exp_rel(raw), "input_raw_sha256": sha256(raw), "output_path": rel(output), "output_sha256": sha256(output), "labels": list(labels), "signal_order": list(labels), "command": command, "renderer": "scripts/josim-plot2.py", "layout": "sep_comb", "color": "dark", "phase_option": "2pi", "phase_convention": "raw P radians; display rad/(2*pi) turns; never SFQ count", "window_ps": [0.0, 200.0], "window_semantics": "whole-run raw timestamps", "temporary_input_sha256": None}


def comparison(cases: list[tuple[str, Path]], output: Path, title: str) -> dict[str, Any]:
    headers = [header(raw) for _name, raw in cases]
    if any(item != headers[0] for item in headers[1:]):
        raise RuntimeError("comparison requires identical headers")
    positions = {label: index for index, label in enumerate(headers[0])}
    names = [name for name, _raw in cases]
    labels = tuple(f"{label} [{name}]" for name in names for label in COMPARE_LABELS)
    fd, temporary_name = tempfile.mkstemp(prefix="bvm-boundary-", suffix=".csv", dir="/tmp")
    os.close(fd)
    temporary = Path(temporary_name)
    try:
        streams = [case[1].open(newline="", encoding="utf-8-sig") for case in cases]
        readers = [csv.reader(stream) for stream in streams]
        for reader in readers:
            next(reader)
        with temporary.open("w", newline="", encoding="utf-8") as output_stream:
            writer = csv.writer(output_stream)
            writer.writerow(["time", *labels])
            rows = zip(*readers)
            for group in rows:
                if any(row[0] != group[0][0] for row in group[1:]):
                    raise RuntimeError("comparison time grids differ")
                time_ps = float(group[0][0]) * 1.0e12
                if 108.0 <= time_ps < 150.0:
                    values = []
                    for row in group:
                        values.extend(row[positions[label]] for label in COMPARE_LABELS)
                    writer.writerow([group[0][0], *values])
        temporary_sha = sha256(temporary)
        command = [sys.executable, str(PLOTTER), str(temporary), "-x", str(output), "-t", "sep_comb", "-c", "dark", "-j", "2pi", "-w", title, "-s", *labels]
        if not output.is_file():
            output.parent.mkdir(parents=True, exist_ok=True)
            completed = subprocess.run(command, cwd=REPO, capture_output=True, text=True, check=False)
            if completed.returncode != 0 or not output.is_file() or output.stat().st_size == 0:
                raise RuntimeError(f"comparison failed: {output}: {completed.stderr[-1000:]}")
    finally:
        for _name, raw in cases:
            pass
        for stream in locals().get("streams", []):
            stream.close()
        temporary.unlink(missing_ok=True)
    return {"stage": "focused_comparison", "run_ids": names, "input_raw_paths": [exp_rel(raw) for _name, raw in cases], "input_raw_sha256": [sha256(raw) for _name, raw in cases], "output_path": rel(output), "output_sha256": sha256(output), "labels": list(labels), "command": command, "renderer": "scripts/josim-plot2.py", "layout": "sep_comb", "color": "dark", "phase_option": "2pi", "phase_convention": "P raw radians; display rad/(2*pi) turns; never SFQ count", "window_ps": [108.0, 150.0], "window_semantics": "exact same-time stored rows in focused window", "temporary_input_sha256": temporary_sha, "temporary_input_deleted": not temporary.exists(), "input_mode": "TEMPORARY_EXACT_GRID_MERGE_DELETED_AFTER_RENDER"}


def main() -> int:
    state = json.loads(STATE.read_text(encoding="utf-8"))
    matrix = json.loads(MATRIX.read_text(encoding="utf-8"))
    if state.get("final_marker") != "EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW":
        raise RuntimeError("visualization requires final boundary marker")
    physical_runs = sorted(path for path in (EXP / "runs").iterdir() if path.is_dir())
    entries: list[dict[str, Any]] = []
    for run_dir in physical_runs:
        entries.extend([standalone(run_dir.name, run_dir / "raw.csv", "SIGNAL_TIMING", SIGNAL_LABELS), standalone(run_dir.name, run_dir / "raw.csv", "QB_STATE", QB_LABELS), standalone(run_dir.name, run_dir / "raw.csv", "JTL_CHAIN", JTL_LABELS)])
    entries.extend([standalone("BASELINE_N2_0011", BASELINE["0011"], "SIGNAL_TIMING", SIGNAL_LABELS), standalone("BASELINE_N2_0011", BASELINE["0011"], "QB_STATE", QB_LABELS), standalone("BASELINE_N2_0011", BASELINE["0011"], "JTL_CHAIN", JTL_LABELS), standalone("BASELINE_N3_0111", BASELINE["0111"], "SIGNAL_TIMING", SIGNAL_LABELS), standalone("BASELINE_N3_0111", BASELINE["0111"], "QB_STATE", QB_LABELS), standalone("BASELINE_N3_0111", BASELINE["0111"], "JTL_CHAIN", JTL_LABELS)])
    result_cache = {point["point_id"]: json.loads((EXP / "boundary/results" / f"{point['point_id']}_corrected_v2.json").read_text(encoding="utf-8")) for point in matrix["points"] if (EXP / "boundary/results" / f"{point['point_id']}_corrected_v2.json").is_file()}
    midpoint = {"L2": {"0011": None, "0111": None}, "IBias": {"0011": None, "0111": None}}
    for point_id, result in result_cache.items():
        axis = "L2" if point_id.startswith("STAGE_A") else "IBias"
        for mask, branch in (("0011", "n2"), ("0111", "n3")):
            midpoint[axis][mask] = REPO / result[branch]["raw_path"]
    comparisons: list[dict[str, Any]] = []
    for axis, low_name, high_name in (("L2", "L2_LOW", "L2_HIGH"), ("IBias", "IB_LOW", "IB_HIGH")):
        for mask, suffix in (("0011", "N2_0011"), ("0111", "N3_0111")):
            if midpoint[axis][mask] is None:
                continue
            output = EXP / "visualization/plots/comparisons" / f"{axis}_{suffix}_endpoint_midpoint_focused_108_150.html"
            cases = [(low_name, ENDPOINTS[low_name][mask]), (f"{axis}_MIDPOINT", midpoint[axis][mask]), (high_name, ENDPOINTS[high_name][mask])]
            comparisons.append(comparison(cases, output, f"{axis} {suffix} endpoint/midpoint focused 108–150 ps"))
    nav_dir = EXP / "visualization/run_summaries"
    nav_dir.mkdir(parents=True, exist_ok=True)
    for run_dir in physical_runs:
        items = [entry for entry in entries if entry["run_id"] == run_dir.name]
        lines = [f"# {run_dir.name} visualization navigation", "", "All standalone views read this run's raw.csv directly over 0–200 ps."]
        for entry in items:
            lines.append(f"- [{entry['name']}.html]({os.path.relpath(REPO / entry['output_path'], nav_dir)})")
        lines.extend(["", "P traces are raw radians; rad/(2*pi) is display/navigation only.", ""])
        (nav_dir / f"{run_dir.name}.md").write_text("\n".join(lines), encoding="utf-8")
    manifest = {"schema": "bvm-qb-threshold-ordering-boundary-visualization-manifest-v1", "experiment_id": EXP.name, "created_at_local": now(), "renderer": "scripts/josim-plot2.py", "layout": "sep_comb", "color": "dark", "phase_option": "2pi", "whole_run_window_ps": [0.0, 200.0], "focused_windows": [[108.0, 150.0]] if comparisons else [], "standalone_input_policy": "raw.csv direct; no derived standalone CSV", "comparison_input_policy": "temporary exact-grid three-case merge under /tmp, focused 108–150 ps, deleted after render", "standalone_entries": entries, "comparison_entries": comparisons, "raw_hashes": {entry["run_id"]: entry["input_raw_sha256"] for entry in entries if entry["run_id"] in {path.name for path in physical_runs}}, "phase_not_sfq_count": True}
    (EXP / "visualization/manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "standalone_html_count": len(entries), "comparison_html_count": len(comparisons), "temporary_comparisons_deleted": all(item["temporary_input_deleted"] for item in comparisons)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
