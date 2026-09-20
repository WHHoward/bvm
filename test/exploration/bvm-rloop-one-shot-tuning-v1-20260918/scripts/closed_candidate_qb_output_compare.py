#!/usr/bin/env python3
"""Render descriptive QB/JTL/terminal overlays for the two CLOSED candidates.

This is a raw-waveform comparison only. It uses each stored time grid directly,
does not interpolate or classify events, and does not make a scientific Gate
or winner decision.
"""

from __future__ import annotations

import csv
import hashlib
import html
import json
import math
from pathlib import Path
from typing import Any


SERIES = Path(__file__).resolve().parents[1]
REPO = next(path for path in (SERIES, *SERIES.parents) if (path / ".git").exists())

CASES = (
    ("performance_14_20", "U038_closed_perf_14_20_full", "#66ccff"),
    ("conservative_12_20", "U039_closed_cons_12_20_full", "#ffcc66"),
)
MASKS = ("CLOSED_N0_0000", "CLOSED_N1_0001", "CLOSED_N2_0011", "CLOSED_N3_0111", "CLOSED_N4_1111")
SIGNALS = (
    ("V(COMMON_SL)", "COMMON_SL voltage", "mV"),
    ("I(B_JSL8)", "JSL8 current", "µA"),
    ("V(B_JSL8)", "JSL8 voltage", "mV"),
    ("V(QBIN)", "QB input boundary", "mV"),
    ("V(QBOUT)", "QB output boundary", "mV"),
    ("V(JTL6_OUT)", "JTL6 output", "mV"),
    ("I(R_TERM)", "terminal current", "µA"),
    ("V(R_TERM)", "terminal voltage", "mV"),
)
WINDOWS = (
    ("zero_read_control_70_81", 70.0, 81.0, "CONTROL"),
    ("final_read_110_121", 110.0, 121.0, "FINAL READ"),
    ("recovery_121_130", 121.0, 130.0, "RECOVERY"),
)
FOCUSED_WINDOWS = (("CONTROL+RECOVERY", 70.0, 90.0), ("FINAL+RECOVERY", 110.0, 130.0))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def repo_rel(path: Path) -> str:
    return path.resolve().relative_to(REPO.resolve()).as_posix()


def load_raw(case_id: str, mask: str) -> dict[str, Any]:
    path = SERIES / "runs" / case_id / "cases" / mask / "raw.csv"
    with path.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.reader(stream)
        headers = next(reader)
        rows = [[float(value) for value in row] for row in reader if row]
    time_index = headers.index("time")
    times = [row[time_index] * 1e12 for row in rows]
    values = {signal: [row[headers.index(signal)] for row in rows] for signal, _, _ in SIGNALS}
    return {"path": path, "headers": headers, "times": times, "values": values, "sha256": sha256(path)}


def display_scale(signal: str) -> tuple[float, str]:
    if signal.startswith("I("):
        return 1e6, "µA"
    if signal.startswith("V("):
        return 1e3, "mV"
    return 1.0, "raw"


def svg_overlay(mask: str, signal: str, label: str, cases: list[tuple[str, dict[str, Any], str]], window: tuple[float, float] = (0.0, 200.0), width: int = 1120, height: int = 270) -> str:
    scale, unit = display_scale(signal)
    start_ps, end_ps = window
    all_values = [
        raw["values"][signal][i] * scale
        for _, raw, _ in cases
        for i, time_ps in enumerate(raw["times"])
        if start_ps <= time_ps <= end_ps and math.isfinite(raw["values"][signal][i])
    ]
    if not all_values:
        raise RuntimeError(f"no finite values for {mask} {signal}")
    low, high = min(all_values), max(all_values)
    if abs(high - low) < 1e-18:
        low -= 1.0
        high += 1.0
    left, right, top, bottom = 82, width - 34, 42, height - 38
    def x(time_ps: float) -> float:
        return left + ((time_ps - start_ps) / (end_ps - start_ps)) * (right - left)
    markers = []
    for _, start, end, marker_label in WINDOWS:
        clipped_start, clipped_end = max(start_ps, start), min(end_ps, end)
        if clipped_end <= clipped_start:
            continue
        x1, x2 = x(clipped_start), x(clipped_end)
        markers.append(f"<rect x='{x1:.2f}' y='{top}' width='{max(1.0, x2-x1):.2f}' height='{bottom-top}' fill='#ffffff' opacity='0.045'/><text x='{(x1+x2)/2:.2f}' y='28' fill='#bbb' font-size='10' text-anchor='middle'>{marker_label}</text>")
    lines = []
    legend = []
    for index, (case_label, raw, color) in enumerate(cases):
        points = []
        indices = [i for i, time_ps in enumerate(raw["times"]) if start_ps <= time_ps <= end_ps]
        stride = max(1, len(indices) // 1200)
        for i in indices[::stride]:
            value = raw["values"][signal][i] * scale
            y = bottom - (value - low) / (high - low) * (bottom - top)
            points.append(f"{x(raw['times'][i]):.2f},{y:.2f}")
        lines.append(f"<polyline fill='none' stroke='{color}' stroke-width='1.5' points='{' '.join(points)}'/>")
        lx = left + index * 210
        legend.append(f"<line x1='{lx}' x2='{lx+24}' y1='13' y2='13' stroke='{color}' stroke-width='3'/><text x='{lx+30}' y='17' fill='#ddd' font-size='11'>{html.escape(case_label)}</text>")
    return (
        f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {width} {height}' style='width:100%;background:#111'>"
        f"<rect width='100%' height='100%' fill='#111'/><text x='{left}' y='17' fill='#fff' font-size='13'>{html.escape(mask)} — {html.escape(label)} [{unit}] — {start_ps:g}–{end_ps:g} ps</text>"
        + "".join(legend) + "".join(markers) + "".join(lines)
        + f"<line x1='{left}' x2='{right}' y1='{bottom}' y2='{bottom}' stroke='#777'/><text x='{left}' y='{height-12}' fill='#aaa' font-size='10'>{start_ps:g} ps</text><text x='{right}' y='{height-12}' fill='#aaa' font-size='10' text-anchor='end'>{end_ps:g} ps</text><text x='{right}' y='{top+10}' fill='#aaa' font-size='10' text-anchor='end'>{high:.5g}</text><text x='{right}' y='{bottom}' fill='#aaa' font-size='10' text-anchor='end'>{low:.5g}</text></svg>"
    )


def main() -> int:
    output = SERIES / "plots" / "CLOSED_CANDIDATE_QB_OUTPUT_COMPARISON.html"
    manifest_path = SERIES / "analysis" / "CLOSED_CANDIDATE_QB_OUTPUT_VIZ_MANIFEST.json"
    qa_path = SERIES / "qa" / "CLOSED_CANDIDATE_QB_OUTPUT_VIZ_QA.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    cases_by_mask: dict[str, list[tuple[str, dict[str, Any], str]]] = {}
    raw_records = []
    missing = []
    time_grid_match: dict[str, bool] = {}
    for mask in MASKS:
        loaded = []
        for label, case_id, color in CASES:
            raw = load_raw(case_id, mask)
            loaded.append((label, raw, color))
            raw_records.append({"case": case_id, "mask": mask, "raw_path": repo_rel(raw["path"]), "raw_sha256": raw["sha256"], "sample_count": len(raw["times"]), "signals": [signal for signal, _, _ in SIGNALS]})
            for signal, _, _ in SIGNALS:
                if signal not in raw["headers"]:
                    missing.append({"case": case_id, "mask": mask, "signal": signal})
        cases_by_mask[mask] = loaded
        time_grid_match[mask] = loaded[0][1]["times"] == loaded[1][1]["times"]
    if missing:
        raise RuntimeError(f"required comparison signals missing: {missing}")
    sections = []
    for mask in MASKS:
        loaded = cases_by_mask[mask]
        sections.append(f"<details open><summary><b>{html.escape(mask)}</b> — actual stored grid match: {time_grid_match[mask]}</summary>")
        sections.extend(f"<div class='panel'>{svg_overlay(mask, signal, label, loaded)}</div>" for signal, label, _ in SIGNALS)
        sections.append("</details>")
    n4_cases = cases_by_mask["CLOSED_N4_1111"]
    sections.append("<details open><summary><b>CLOSED_N4_1111 focused windows</b> — QB/output timing views</summary>")
    for window_label, start_ps, end_ps in FOCUSED_WINDOWS:
        sections.append(f"<h3>{html.escape(window_label)} [{start_ps:g}, {end_ps:g}] ps</h3>")
        sections.extend(f"<div class='panel'>{svg_overlay('CLOSED_N4_1111', signal, label, n4_cases, (start_ps, end_ps))}</div>" for signal, label, _ in SIGNALS)
    sections.append("</details>")
    links = []
    for label, case_id, _ in CASES:
        links.append(f"<li>{html.escape(label)}: <a href='{html.escape(case_id + '/review.html')}'>{html.escape(case_id)} review</a></li>")
    body = """<!doctype html><html><head><meta charset='utf-8'><title>CLOSED candidate QB/output comparison</title><style>body{font-family:Arial,sans-serif;background:#111;color:#eee;margin:20px;line-height:1.4}a{color:#8ecbff}.panel{border:1px solid #444;border-radius:6px;margin:10px 0;padding:8px}details{border:1px solid #555;border-radius:6px;margin:18px 0;padding:12px}summary{cursor:pointer;color:#ffd580}small{color:#aaa}</style></head><body>"""
    body += "<h1>CLOSED candidates — QB and output comparison</h1><p>Descriptive raw-waveform comparison only. Each candidate is plotted against its own actual stored time values; no interpolation, resampling, event counting, Gate decision, or winner selection is performed.</p><h2>Candidate reviews</h2><ul>" + "".join(links) + "</ul>" + "".join(sections) + "<p><small>P(...) is not plotted here; where phase plots exist, raw P values remain radians and rad/(2π) is navigation only. Signals and raw hashes are recorded in the machine-readable manifest.</small></p></body></html>"
    output.write_text(body, encoding="utf-8")
    manifest = {"schema": "bvm-closed-candidate-qb-output-viz-v1", "cases": [case_id for _, case_id, _ in CASES], "masks": list(MASKS), "signals": [signal for signal, _, _ in SIGNALS], "raw_records": raw_records, "time_grid_match": time_grid_match, "focused_masks": ["CLOSED_N4_1111"], "focused_windows": [{"label": label, "start_ps": start, "end_ps": end} for label, start, end in FOCUSED_WINDOWS], "comparison": repo_rel(output), "scientific_interpretation_performed": False, "interpolation": False}
    qa = {"status": "PASS" if not missing else "FAIL", "comparison": repo_rel(output), "case_count": len(CASES), "mask_count": len(MASKS), "required_signal_count": len(SIGNALS), "focused_window_count": len(FOCUSED_WINDOWS), "missing_signals": missing, "raw_hashes_rechecked": all(item["raw_sha256"] == sha256(REPO / item["raw_path"]) for item in raw_records), "time_grid_match": time_grid_match, "descriptive_only": True, "scientific_interpretation_performed": False}
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    qa_path.parent.mkdir(parents=True, exist_ok=True)
    qa_path.write_text(json.dumps(qa, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(qa, ensure_ascii=False, indent=2))
    return 0 if qa["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
