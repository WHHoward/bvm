#!/usr/bin/env python3
"""Render second-stage cross-condition comparisons after individual-plot QA."""

from __future__ import annotations

import argparse
import csv
import html
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
PLOTTER = REPO / "scripts/josim-plot2.py"
sys.path.insert(0, str(REPO / "scripts"))

from bvmtools.raw import RawTrace, read_csv  # noqa: E402


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel(path: Path) -> str:
    return str(path.resolve().relative_to(REPO.resolve()))


def json_write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def page_qa_pass(page: dict[str, Any]) -> bool:
    qa = page["qa"]
    if not qa["labels_present"] or qa["unknown_axis_title_present"]:
        return False
    prefixes = {"phase": "P(", "voltage": "V(", "current": "I("}
    return all(
        not any(label.startswith(prefix) for label in page["selected_source_labels"])
        or bool(qa["expected_axis_titles"][kind])
        for kind, prefix in prefixes.items()
    )


def load_context() -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    effective = json.loads((EXP / "analysis/effective_run_manifest.json").read_text(encoding="utf-8"))
    records = {str(item["run_id"]): item for item in effective["runs"]}
    metrics = {
        run_id: json.loads((EXP / "runs" / run_id / "analysis/metrics.json").read_text(encoding="utf-8"))
        for run_id in records
    }
    for run_id, record in records.items():
        record["raw_sha256"] = metrics[run_id]["raw_sha256"]
    plot_manifest = json.loads((EXP / "analysis/plot_manifest.json").read_text(encoding="utf-8"))
    if plot_manifest.get("qa_status") != "PASS" or plot_manifest.get("comparison_gate") != "OPEN":
        raise RuntimeError("individual plot QA is not PASS/OPEN; comparison rendering is blocked")
    if plot_manifest.get("run_count_rendered") != 24:
        raise RuntimeError("not all 24 individual run plot sets are present")
    for item in plot_manifest["runs"]:
        if item.get("qa_status") != "PASS" or len(item.get("pages", [])) != 5:
            raise RuntimeError(f"individual plot QA failed for {item.get('run_id')}")
    if len(records) != 24 or any(item.get("artifact_status") != "VALID" for item in metrics.values()):
        raise RuntimeError("all 24 run metrics must be artifact-valid before comparison")
    return records, metrics


def trace_for(run_id: str, records: dict[str, dict[str, Any]], cache: dict[str, RawTrace]) -> RawTrace:
    if run_id not in cache:
        cache[run_id] = read_csv(REPO / records[run_id]["effective_raw"])
    return cache[run_id]


def common_times(traces: list[RawTrace]) -> list[float]:
    if not traces:
        raise ValueError("comparison requires at least one trace")
    memberships = [set(trace.time) for trace in traces[1:]]
    common = [time_value for time_value in traces[0].time if all(time_value in membership for membership in memberships)]
    if len(common) < 2:
        raise RuntimeError("comparison has fewer than two exact common timestamps; interpolation is prohibited")
    return common


def display_label(run_id: str, source_label: str) -> str:
    if not source_label or source_label[0] not in {"P", "V", "I"}:
        raise ValueError(f"source label must retain P/V/I prefix: {source_label!r}")
    return f"{source_label} [{run_id}]"


def make_projection(
    run_ids: list[str],
    source_labels: list[str],
    records: dict[str, dict[str, Any]],
    cache: dict[str, RawTrace],
    directory: Path,
    name: str,
) -> tuple[Path, list[str], int, dict[str, str]]:
    traces = [trace_for(run_id, records, cache) for run_id in run_ids]
    times = common_times(traces)
    display = [display_label(run_id, label) for run_id in run_ids for label in source_labels]
    if len(set(display)) != len(display):
        raise RuntimeError("comparison display labels are not unique")
    columns: list[tuple[str, dict[float, float]]] = []
    for run_id, trace in zip(run_ids, traces):
        index = {time_value: position for position, time_value in enumerate(trace.time)}
        for label in source_labels:
            values = trace.column(label)
            columns.append((display_label(run_id, label), {time_value: values[index[time_value]] for time_value in times}))
    path = directory / f"{name}.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["time", *display])
        for time_value in times:
            writer.writerow([f"{time_value:.17e}", *[f"{mapping[time_value]:.17e}" for _, mapping in columns]])
    raw_hashes = {run_id: records[run_id]["raw_sha256"] for run_id in run_ids}
    return path, display, len(times), raw_hashes


def render_plot2(
    filename: str,
    title: str,
    run_ids: list[str],
    source_labels: list[str],
    records: dict[str, dict[str, Any]],
    cache: dict[str, RawTrace],
    temporary: Path,
) -> dict[str, Any]:
    output = EXP / "plots/comparison" / filename
    projection, display, sample_count, raw_hashes = make_projection(
        run_ids, source_labels, records, cache, temporary, filename.removesuffix(".html")
    )
    command = [
        sys.executable,
        str(PLOTTER),
        str(projection),
        "-x", str(output),
        "-t", "sep_comb",
        "-c", "dark",
        "-j", "2pi",
        "-w", title,
        "-s", *display,
    ]
    completed = subprocess.run(command, cwd=REPO, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"comparison plot failed {filename}: {completed.stdout}\n{completed.stderr}")
    if not output.is_file() or output.stat().st_size == 0:
        raise RuntimeError(f"empty comparison output: {output}")
    text = output.read_text(encoding="utf-8")
    expected_axis_titles = {
        "phase": "Phase (turns)" in text,
        "voltage": "Voltage (V)" in text,
        "current": "Current (I)" in text,
    }
    unknown_axis_title = bool(re.search(r'"title"\s*:\s*\{\s*"text"\s*:\s*"Unknown[^"}]*"\s*\}', text))
    page = {
        "output": rel(output),
        "sha256": sha256(output),
        "renderer": rel(PLOTTER),
        "renderer_sha256": sha256(PLOTTER),
        "renderer_command": [str(item) for item in command],
        "run_ids": run_ids,
        "selected_source_labels": source_labels,
        "selected_display_labels": display,
        "common_sample_count": sample_count,
        "common_time_grid": "exact timestamp intersection; no interpolation",
        "raw_sha256": raw_hashes,
        "qa": {
            "exists_nonempty": True,
            "labels_present": all(label in text for label in display),
            "missing_labels": [label for label in display if label not in text],
            "expected_axis_titles": expected_axis_titles,
            "unknown_axis_title_present": unknown_axis_title,
        },
    }
    if not page_qa_pass(page):
        raise RuntimeError(f"comparison plot QA failed: {filename}: {page['qa']}")
    return page


def metric_value(metrics: dict[str, Any], key: str) -> Any:
    return metrics["four_bvm_summary"][key]


def heat_style(value: Any, *, center: float = 4.0, scale: float = 1.0) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return ""
    normalized = max(-1.0, min(1.0, (number - center) / scale))
    hue = 210.0 - 170.0 * ((normalized + 1.0) / 2.0)
    return f"background:hsl({hue:.1f} 70% 30%);"


def render_phase_map(metrics: dict[str, dict[str, Any]]) -> dict[str, Any]:
    output = EXP / "plots/comparison/FOUR_BVM_RJ1_TIMESTEP_PHASE_MAP.html"
    rows = []
    for run_id in (
        "F4_R12_T100", "F4_R12_T050", "F4_R12_T025", "F4_R12_T0125",
        "F4_R11P5_T100", "F4_R11P5_T050", "F4_R11P5_T025", "F4_R11P5_T0125",
        "F4_R11_T100", "F4_R11_T050", "F4_R11_T025", "F4_R11_T0125",
    ):
        item = metrics[run_id]
        four = item["four_bvm_summary"]
        transport = item["transport"]["stages"]
        late = "YES" if four["late_complete_count_after_principal"] else "NO"
        rows.append(
            {
                "run_id": run_id,
                "rj1": item["rj1_ohm"],
                "dt": item["timestep_ps"],
                "BJ1 net trajectory (turns)": four["BJ1_READ1_net_turns"],
                "BJ2 net trajectory (turns)": four["BJ2_READ1_net_turns"],
                "JTL1 B01 net trajectory (turns)": transport["JTL1"]["B01_net_phase_turns"],
                "JTL1 B02 net trajectory (turns)": transport["JTL1"]["B02_net_phase_turns"],
                "JTL6 B02 net trajectory (turns)": transport["JTL6"]["B02_net_phase_turns"],
                "BJ2 late complete event": late,
                "branch": four["branch_observation"],
            }
        )
    columns = list(rows[0].keys())
    header_cells = "".join(f"<th>{html.escape(str(column))}</th>" for column in columns)
    body = []
    numeric_columns = {column for column in columns if "turns" in column}
    for row in rows:
        cells = []
        for column in columns:
            value = row[column]
            if column in numeric_columns:
                cells.append(f'<td style="{heat_style(value)}">{float(value):.6f}</td>')
            elif column == "rj1" or column == "dt":
                cells.append(f"<td>{html.escape(str(value))}</td>")
            else:
                cells.append(f"<td>{html.escape(str(value))}</td>")
        body.append("<tr>" + "".join(cells) + "</tr>")
    document = f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>Four-BVM RJ1 × timestep phase map</title>
<style>
body{{margin:2rem;background:#111;color:#eee;font-family:Arial,sans-serif}}
h1{{font-size:1.5rem}}p{{color:#bbb;max-width:1100px;line-height:1.5}}
table{{border-collapse:collapse;font-size:.82rem;white-space:nowrap}}
th,td{{border:1px solid #444;padding:.42rem .55rem;text-align:right}}
th{{background:#222;position:sticky;top:0}}td:last-child,td:nth-last-child(2){{text-align:left}}
caption{{caption-side:bottom;text-align:left;color:#aaa;padding-top:.8rem}}
</style></head><body>
<h1>FOUR_BVM_RJ1_TIMESTEP_PHASE_MAP</h1>
<p>这是 raw-derived 的关键指标 map。所有 “net trajectory” 都是 READ1 窗口端点相位位移，单位为 turns = continuous_unwrap(P raw radians)/(2π)，不是 SFQ event count。late event 指 BJ2 principal event 之后的 complete same-segment event。</p>
<table><thead><tr>{header_cells}</tr></thead><tbody>{''.join(body)}</tbody>
<caption>颜色仅用于快速定位数值，不改变指标定义；完整同 JJ phase/area/event list 位于各 run 的 analysis/metrics.json。</caption></table>
</body></html>
"""
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(document, encoding="utf-8")
    return {
        "output": rel(output),
        "sha256": sha256(output),
        "renderer": "analysis/render_comparison.py inline metric map",
        "run_ids": [row["run_id"] for row in rows],
        "metric_columns": columns,
        "qa": {"exists_nonempty": True, "rows": len(rows), "net_turns_are_not_event_counts": True},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--timestamp", default=None)
    args = parser.parse_args()
    timestamp = args.timestamp or datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    records, metrics = load_context()
    cache: dict[str, RawTrace] = {}
    rendered: list[dict[str, Any]] = []
    output_dir = EXP / "plots/comparison"
    output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="rj1_comparison_") as temporary_name:
        temporary = Path(temporary_name)
        rendered.append(
            render_plot2(
                "FOUR_BVM_BJ2_COMPARE.html",
                "Four-BVM fine timestep BJ2 — RJ1 12 / 11.5 / 11",
                [
                    "F4_R12_T025", "F4_R12_T0125",
                    "F4_R11P5_T025", "F4_R11P5_T0125",
                    "F4_R11_T025", "F4_R11_T0125",
                ],
                ["P(BJ2|XBQ1)", "V(BJ2|XBQ1)"],
                records, cache, temporary,
            )
        )
        rendered.append(
            render_plot2(
                "FOUR_BVM_JTL_COMPARE.html",
                "Four-BVM fine timestep JTL B02 — JTL1 vs JTL6",
                [
                    "F4_R12_T025", "F4_R12_T0125",
                    "F4_R11P5_T025", "F4_R11P5_T0125",
                    "F4_R11_T025", "F4_R11_T0125",
                ],
                ["P(B02|XJTL1_1)", "P(B02|XJTL1_6)"],
                records, cache, temporary,
            )
        )
        for rkey, ohm in (("R12", 12.0), ("R11P5", 11.5), ("R11", 11.0)):
            rendered.append(
                render_plot2(
                    f"RJ1_{rkey}_TIMESTEP_COMPARE.html",
                    f"Four-BVM RJ1={ohm:g} ohm — timestep comparison",
                    [f"F4_{rkey}_{tkey}" for tkey in ("T100", "T050", "T025", "T0125")],
                    ["P(BJ2|XBQ1)", "V(BJ2|XBQ1)"],
                    records, cache, temporary,
                )
            )
        rendered.append(
            render_plot2(
                "SINGLE_BVM_PROTECTION_COMPARE.html",
                "Single-BVM JTL-loaded protection — RJ1 / S0-S1 / timestep",
                [
                    "S1B_R12_T025_S0", "S1B_R12_T025_S1", "S1B_R12_T0125_S0", "S1B_R12_T0125_S1",
                    "S1B_R11P5_T025_S0", "S1B_R11P5_T025_S1", "S1B_R11P5_T0125_S0", "S1B_R11P5_T0125_S1",
                    "S1B_R11_T025_S0", "S1B_R11_T025_S1", "S1B_R11_T0125_S0", "S1B_R11_T0125_S1",
                ],
                ["P(BJ2|XBQ1)", "P(B02|XJTL1_1)", "P(B02|XJTL1_6)"],
                records, cache, temporary,
            )
        )
    rendered.insert(0, render_phase_map(metrics))
    result = {
        "generated_at": timestamp,
        "stage": "comparison_after_all_individual_plot_QA",
        "comparison_gate_input": rel(EXP / "analysis/plot_manifest.json"),
        "renderer_default": rel(PLOTTER),
        "profile": "CLASSIC_LOCKED for waveform comparisons; inline metric table for phase map",
        "layout": "sep_comb",
        "color": "dark",
        "phase_option": "2pi for plot2 waveform pages",
        "interpolation": "none; exact timestamp intersections only",
        "pages": rendered,
        "qa_status": "PASS",
    }
    json_write(EXP / "analysis/comparison_manifest.json", result)
    print(json.dumps({"status": result["qa_status"], "pages": len(rendered)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
