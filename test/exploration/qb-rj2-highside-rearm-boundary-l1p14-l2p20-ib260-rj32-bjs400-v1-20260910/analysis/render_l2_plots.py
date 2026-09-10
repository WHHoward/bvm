#!/usr/bin/env python3
"""Render the frozen compact RJ2 high-side whole-run visualization set."""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
PLOTTER = REPO / "scripts/josim-plot2.py"
sys.path.insert(0, str(REPO / "scripts"))
from bvmtools.phase import continuous_unwrap  # noqa: E402
from bvmtools.raw import RawTrace, read_csv  # noqa: E402


NEW_RUNS = (
    "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P8_0001", "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P8_0011",
    "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P10_0001", "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P10_0011",
    "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_0001", "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_0011",
)
REUSE_RUNS = ("ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P6_0001", "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P6_0011")
RUN_PATHS = {run_id: EXP / "runs" / run_id for run_id in NEW_RUNS}
RUN_PATHS.update({run_id: EXP / "references/reused" / run_id for run_id in REUSE_RUNS})
COMPARISON_CASES = {
    "0001": [
        "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P6_0001",
        "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P8_0001",
        "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P10_0001",
        "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_0001",
    ],
    "0011": [
        "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P6_0011",
        "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P8_0011",
        "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P10_0011",
        "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_0011",
    ],
}
STANDALONE_NAMES = ("SIGNAL_PATH", "QB_STATE", "JTL_CHAIN")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO.resolve()).as_posix()


def raw_path(run_id: str) -> Path:
    return RUN_PATHS[run_id] / "raw.csv"


def read_trace(path: Path) -> RawTrace:
    trace = read_csv(path)
    if trace.duplicate_columns:
        raise RuntimeError(f"duplicate raw columns: {path}: {trace.duplicate_columns}")
    return trace


def standalone_labels(name: str) -> list[str]:
    if name == "SIGNAL_PATH":
        return [
            "I(I_WL3)", "I(I_BL3)", "I(I_SE3)", "I(I_WL4)", "I(I_BL4)", "I(I_SE4)",
            "I(L_SL|XBVM3)", "I(L_SL|XBVM4)",
            "V(COMMON_SL)", "I(B_JSL8)", "I(LIN|XBQ1)",
            "V(QBIN)", "V(QBOUT)",
            "V(JTL1_OUT)", "V(JTL2_OUT)", "V(JTL3_OUT)",
            "V(JTL4_OUT)", "V(JTL5_OUT)", "V(JTL6_OUT)", "I(R_TERM)",
        ]
    if name == "QB_STATE":
        return [
            "V(QBIN)",
            "I(LIN|XBQ1)", "V(LIN|XBQ1)",
            "P(BJS|XBQ1)", "V(BJS|XBQ1)", "I(BJS|XBQ1)",
            "P(BJ1|XBQ1)", "V(BJ1|XBQ1)", "I(BJ1|XBQ1)",
            "I(RJ1|XBQ1)", "V(RJ1|XBQ1)",
            "I(L1|XBQ1)", "V(L1|XBQ1)",
            "I(IB|XBQ1)",
            "I(L2|XBQ1)", "V(L2|XBQ1)",
            "P(BJ2|XBQ1)", "V(BJ2|XBQ1)", "I(BJ2|XBQ1)",
            "I(RJ2|XBQ1)", "V(RJ2|XBQ1)",
            "I(L3|XBQ1)", "V(L3|XBQ1)",
            "V(QBOUT)",
        ]
    if name == "JTL_CHAIN":
        labels: list[str] = []
        for stage in range(1, 7):
            header = f"XJTL1_{stage}"
            for jj in ("B01", "B02"):
                labels.extend((f"P({jj}|{header})", f"V({jj}|{header})", f"I({jj}|{header})"))
            labels.append(f"V(JTL{stage}_OUT)")
        labels.append("I(R_TERM)")
        return labels
    raise ValueError(name)


def comparison_labels() -> list[str]:
    return [
        "I(I_WL3)", "I(I_BL3)", "I(I_SE3)", "I(I_WL4)", "I(I_BL4)", "I(I_SE4)",
        "I(B_JSL8)", "V(COMMON_SL)", "I(LIN|XBQ1)", "V(QBIN)",
        "P(BJ1|XBQ1)", "V(BJ1|XBQ1)", "I(BJ1|XBQ1)",
        "I(RJ1|XBQ1)",
        "I(L1|XBQ1)", "I(L2|XBQ1)", "V(L2|XBQ1)",
        "P(BJ2|XBQ1)", "V(BJ2|XBQ1)",
        "V(QBOUT)",
        "V(JTL1_OUT)", "V(JTL6_OUT)", "I(R_TERM)",
    ]


def run_plot2(input_path: Path, output_path: Path, title: str, labels: list[str]) -> list[str]:
    command = [
        sys.executable, str(PLOTTER), str(input_path), "-x", str(output_path),
        "-t", "sep_comb", "-c", "dark", "-j", "2pi", "-w", title,
        "-s", *labels,
    ]
    completed = subprocess.run(command, cwd=REPO, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"plot2 failed: {output_path}\n{completed.stdout}\n{completed.stderr}")
    if not output_path.is_file() or output_path.stat().st_size == 0:
        raise RuntimeError(f"plot2 produced no HTML: {output_path}")
    html = output_path.read_text(encoding="utf-8", errors="replace")
    if "<html" not in html.lower() or '"title":{"text":"Unknown"}' in html:
        raise RuntimeError(f"plot HTML QA failed: {output_path}")
    if any(label.startswith("P(") for label in labels) and ("Phase (turns)" not in html or "2pi" not in html):
        raise RuntimeError(f"phase display QA failed: {output_path}")
    return command


def entry(stage: str, name: str, input_path: Path, output_path: Path, labels: list[str], sources: list[Path], command: list[str]) -> dict[str, object]:
    input_name = rel(input_path) if input_path.resolve().is_relative_to(REPO.resolve()) else str(input_path)
    return {
        "stage": stage,
        "name": name,
        "input_path": input_name,
        "input_sha256": sha256(input_path),
        "output_path": rel(output_path),
        "output_sha256": sha256(output_path),
        "labels": labels,
        "signal_order": labels,
        "source_raw_paths": [rel(path) for path in sources],
        "source_raw_sha256": [sha256(path) for path in sources],
        "command": command,
        "renderer": "scripts/josim-plot2.py",
        "layout": "sep_comb",
        "color": "dark",
        "phase_option": "2pi",
        "phase_convention": "raw P radians; plot2 displays rad/(2*pi) turns; never SFQ count",
        "window_ps": [0.0, 200.0],
        "window_semantics": "whole-run raw timestamps; no focused window",
        "input_mode": "RAW_DIRECT" if stage == "standalone" else "TEMPORARY_MERGED_COMPARISON",
    }


def write_comparison_csv(path: Path, case_ids: list[str], labels: list[str]) -> str:
    traces = [read_trace(raw_path(case_id)) for case_id in case_ids]
    base_time = traces[0].time
    if any(item.time != base_time for item in traces[1:]):
        raise RuntimeError("comparison time grids differ")
    for item in traces:
        missing = [label for label in labels if label not in item.headers]
        if missing:
            raise RuntimeError(f"comparison labels missing: {missing}")
    phase_columns = {
        (case_index, label): continuous_unwrap(tuple(traces[case_index].column(label)))
        for case_index in range(len(traces))
        for label in labels
        if label.startswith("P(")
    }
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["time", *(f"{label} [{case_id}]" for label in labels for case_id in case_ids)])
        for index, timestamp in enumerate(base_time):
            row: list[object] = [f"{timestamp:.17g}"]
            for label in labels:
                for case_index, item in enumerate(traces):
                    if label.startswith("P("):
                        row.append(f"{phase_columns[(case_index, label)][index]:.17g}")
                    else:
                        row.append(f"{item.column(label)[index]:.17g}")
            writer.writerow(row)
    return sha256(path)


def render_standalone(entries: list[dict[str, object]]) -> None:
    for run_id in NEW_RUNS:
        source = raw_path(run_id)
        item = read_trace(source)
        for name in STANDALONE_NAMES:
            labels = standalone_labels(name)
            missing = [label for label in labels if label not in item.headers]
            if missing:
                raise RuntimeError(f"{run_id}/{name} missing labels: {missing}")
            output = EXP / "plots/runs" / run_id / f"{name}.html"
            output.parent.mkdir(parents=True, exist_ok=True)
            command = run_plot2(source, output, f"{run_id} — {name}", labels)
            entries.append(entry("standalone", name, source, output, labels, [source], command))


def render_comparison(entries: list[dict[str, object]], name: str, case_ids: list[str]) -> None:
    labels = comparison_labels()
    output = EXP / "plots/comparison" / f"{name}.html"
    temp_path = Path(tempfile.mkstemp(prefix="rj2-damping-", suffix=".csv", dir="/tmp")[1])
    try:
        temp_hash = write_comparison_csv(temp_path, case_ids, labels)
        output.parent.mkdir(parents=True, exist_ok=True)
        plot_labels = [f"{label} [{case_id}]" for label in labels for case_id in case_ids]
        command = run_plot2(temp_path, output, name, plot_labels)
        record = entry("comparison", name, temp_path, output, plot_labels, [raw_path(case_id) for case_id in case_ids], command)
        record["comparison_cases"] = case_ids
        record["temporary_input_sha256"] = temp_hash
        record["temporary_input_deleted"] = True
        entries.append(record)
    finally:
        temp_path.unlink(missing_ok=True)


def write_run_summaries() -> list[Path]:
    root = EXP / "visualization/run_summaries"
    root.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []
    for run_id in NEW_RUNS:
        path = root / f"{run_id}.md"
        lines = [
            f"# {run_id} — RJ2 damping evidence",
            "",
            "Scientific interpretation: NOT_PERFORMED.",
            "",
            "Three raw-direct whole-run 0-200ps pages are registered.",
            "",
        ]
        for name in STANDALONE_NAMES:
            lines.append(f"- [{name}.html](../../plots/runs/{run_id}/{name}.html)")
        lines.extend([
            "",
            "P values remain raw radians; plot2 uses the registered 2pi display option.",
            "Mechanical timing diagnostics are not event times.",
            "",
        ])
        path.write_text("\n".join(lines), encoding="utf-8")
        outputs.append(path)
    return outputs


def main() -> int:
    entries: list[dict[str, object]] = []
    render_standalone(entries)
    render_comparison(entries, "RJ2_HIGHSIDE_0001_COMPARE", COMPARISON_CASES["0001"])
    render_comparison(entries, "RJ2_HIGHSIDE_0011_COMPARE", COMPARISON_CASES["0011"])
    summaries = write_run_summaries()
    standalone = [item for item in entries if item["stage"] == "standalone"]
    comparisons = [item for item in entries if item["stage"] == "comparison"]
    manifest = {
        "schema": "bjs400-rj2-highside-flat-visualization-manifest-v1",
        "experiment_id": EXP.name,
        "created_at_local": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "renderer": "scripts/josim-plot2.py",
        "layout": "sep_comb",
        "color": "dark",
        "phase_option": "2pi",
        "whole_run_window_ps": [0.0, 200.0],
        "focused_windows": [],
        "standalone_input_policy": "raw.csv direct; no standalone derived CSV",
        "comparison_input_policy": "temporary merged CSV under /tmp; deleted after render",
        "standalone_names": [f"{name}.html" for name in STANDALONE_NAMES],
        "standalone_entries": standalone,
        "comparison_entries": comparisons,
        "standalone_entry_count": len(standalone),
        "comparison_entry_count": len(comparisons),
        "run_summary_paths": [rel(path) for path in summaries],
        "rj2_values_new_ohm": [8.0, 10.0, 12.0],
        "rj2_baseline_reused_ohm": 6.0,
        "masks": ["0001", "0011"],
        "scientific_analysis_performed": False,
        "no_focused_window_plots": True,
        "no_extra_comparison_plots": True,
        "status": "PASS" if len(standalone) == 18 and len(comparisons) == 2 else "FAIL",
    }
    (EXP / "visualization/manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": manifest["status"],
        "standalone_html": len(standalone),
        "comparison_html": len(comparisons),
        "whole_run_only": True,
        "temporary_comparison_csv_retained": False,
        "scientific_analysis_performed": False,
    }, ensure_ascii=False, indent=2))
    return 0 if manifest["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
