#!/usr/bin/env python3
"""Render permanent raw-direct whole-run timestep evidence pages."""

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
from prepare_timestep import NEW_RUNS, REUSE_RUNS, RUN_TO_MASK  # noqa: E402


ACTIVE_RUNS = REUSE_RUNS + NEW_RUNS
STANDALONE_NAMES = ("SIGNAL_PATH", "QB_STATE", "JTL_CHAIN")
COMPARISON_CASES = {"0001": [run_id for run_id in ACTIVE_RUNS if RUN_TO_MASK[run_id] == "0001"], "0011": [run_id for run_id in ACTIVE_RUNS if RUN_TO_MASK[run_id] == "0011"]}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO.resolve()).as_posix()


def raw_path(run_id: str) -> Path:
    return EXP / ("references/reused" if run_id in REUSE_RUNS else "runs") / run_id / "raw.csv"


def labels(view: str) -> list[str]:
    if view == "SIGNAL_PATH":
        return ["I(I_WL3)", "I(I_BL3)", "I(I_SE3)", "I(I_WL4)", "I(I_BL4)", "I(I_SE4)", "I(L_SL|XBVM3)", "I(L_SL|XBVM4)", "V(COMMON_SL)", "I(B_JSL8)", "I(LIN|XBQ1)", "V(QBIN)", "V(QBOUT)", "V(JTL1_OUT)", "V(JTL2_OUT)", "V(JTL3_OUT)", "V(JTL4_OUT)", "V(JTL5_OUT)", "V(JTL6_OUT)", "I(R_TERM)"]
    if view == "QB_STATE":
        return ["V(QBIN)", "I(LIN|XBQ1)", "V(LIN|XBQ1)", "P(BJS|XBQ1)", "V(BJS|XBQ1)", "I(BJS|XBQ1)", "P(BJ1|XBQ1)", "V(BJ1|XBQ1)", "I(BJ1|XBQ1)", "I(RJ1|XBQ1)", "V(RJ1|XBQ1)", "I(L1|XBQ1)", "V(L1|XBQ1)", "I(IB|XBQ1)", "I(L2|XBQ1)", "V(L2|XBQ1)", "P(BJ2|XBQ1)", "V(BJ2|XBQ1)", "I(BJ2|XBQ1)", "I(RJ2|XBQ1)", "V(RJ2|XBQ1)", "I(L3|XBQ1)", "V(L3|XBQ1)", "V(QBOUT)"]
    if view == "JTL_CHAIN":
        result: list[str] = []
        for stage in range(1, 7):
            for jj in ("B01", "B02"):
                result.extend((f"P({jj}|XJTL1_{stage})", f"V({jj}|XJTL1_{stage})", f"I({jj}|XJTL1_{stage})"))
            result.append(f"V(JTL{stage}_OUT)")
        result.append("I(R_TERM)")
        return result
    raise ValueError(view)


def comparison_labels() -> list[str]:
    return ["I(I_WL3)", "I(I_BL3)", "I(I_SE3)", "I(I_WL4)", "I(I_BL4)", "I(I_SE4)", "I(B_JSL8)", "V(COMMON_SL)", "I(LIN|XBQ1)", "V(QBIN)", "P(BJ1|XBQ1)", "V(BJ1|XBQ1)", "I(BJ1|XBQ1)", "I(RJ1|XBQ1)", "I(L1|XBQ1)", "I(L2|XBQ1)", "V(L2|XBQ1)", "P(BJ2|XBQ1)", "V(BJ2|XBQ1)", "V(QBOUT)", "V(JTL1_OUT)", "V(JTL6_OUT)", "I(R_TERM)"]


def run_plot(input_path: Path, output: Path, title: str, signal_labels: list[str]) -> list[str]:
    command = [sys.executable, str(PLOTTER), str(input_path), "-x", str(output), "-t", "sep_comb", "-c", "dark", "-j", "2pi", "-w", title, "-s", *signal_labels]
    completed = subprocess.run(command, cwd=REPO, capture_output=True, text=True, check=False)
    if completed.returncode != 0 or not output.is_file() or output.stat().st_size == 0:
        raise RuntimeError(f"plot2 failed: {output}\n{completed.stdout}\n{completed.stderr}")
    html = output.read_text(encoding="utf-8", errors="replace")
    if "<html" not in html.lower() or '"title":{"text":"Unknown"}' in html or (any(label.startswith("P(") for label in signal_labels) and "Phase (turns)" not in html):
        raise RuntimeError(f"visualization QA failed: {output}")
    return command


def entry(stage: str, run_id: str | None, input_path: Path, output: Path, signal_labels: list[str], sources: list[Path], command: list[str]) -> dict[str, Any]:
    return {"stage": stage, "run_id": run_id, "name": output.name, "input_path": rel(input_path) if input_path.is_relative_to(REPO) else str(input_path), "input_sha256": sha256(input_path), "output_path": rel(output), "output_sha256": sha256(output), "labels": signal_labels, "signal_order": signal_labels, "source_raw_paths": [rel(path) for path in sources], "source_raw_sha256": [sha256(path) for path in sources], "command": command, "renderer": "scripts/josim-plot2.py", "layout": "sep_comb", "color": "dark", "phase_option": "2pi", "phase_convention": "raw P radians; plot2 displays rad/(2*pi) turns; never SFQ count", "window_ps": [0.0, 200.0], "window_semantics": "whole-run raw timestamps; no focused window", "input_mode": "RAW_DIRECT" if stage == "standalone" else "TEMPORARY_MERGED_COMPARISON"}


def write_comparison(path: Path, run_ids: list[str], signal_labels: list[str]) -> str:
    traces = [read_csv(raw_path(run_id)) for run_id in run_ids]
    base_time = traces[0].time
    if any(trace.time != base_time for trace in traces[1:]):
        raise RuntimeError("comparison time grids differ")
    phase_values = {(case, label): continuous_unwrap(tuple(trace.column(label))) for case, trace in enumerate(traces) for label in signal_labels if label.startswith("P(")}
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["time", *(f"{label} [{run_id}]" for label in signal_labels for run_id in run_ids)])
        for index, timestamp in enumerate(base_time):
            row: list[Any] = [f"{timestamp:.17g}"]
            for label in signal_labels:
                for case, trace in enumerate(traces):
                    row.append(f"{phase_values[(case, label)][index]:.17g}" if label.startswith("P(") else f"{trace.column(label)[index]:.17g}")
            writer.writerow(row)
    return sha256(path)


def main() -> int:
    execution = json.loads((EXP / "qa/execution_summary.json").read_text(encoding="utf-8"))
    global ACTIVE_RUNS, COMPARISON_CASES
    new_active = tuple(execution.get("run_order", NEW_RUNS))
    ACTIVE_RUNS = REUSE_RUNS + new_active
    COMPARISON_CASES = {mask: [run_id for run_id in ACTIVE_RUNS if run_id.endswith(f"_{mask}")] for mask in ("0001", "0011")}
    entries: list[dict[str, Any]] = []
    for run_id in ACTIVE_RUNS:
        source = raw_path(run_id)
        trace = read_csv(source)
        for view in STANDALONE_NAMES:
            signal_labels = labels(view)
            missing = [label for label in signal_labels if label not in trace.headers]
            if missing:
                raise RuntimeError(f"{run_id}/{view} missing labels: {missing}")
            output = EXP / "plots/cases" / run_id / f"{view}.html"
            output.parent.mkdir(parents=True, exist_ok=True)
            command = run_plot(source, output, f"{run_id} — {view}", signal_labels)
            entries.append(entry("standalone", run_id, source, output, signal_labels, [source], command))
    for mask, run_ids in COMPARISON_CASES.items():
        signal_labels = comparison_labels()
        output = EXP / "plots/comparison" / f"TIMESTEP_{mask}_COMPARE.html"
        temp = Path(tempfile.mkstemp(prefix="timestep-rj2p12-", suffix=".csv", dir="/tmp")[1])
        try:
            temp_hash = write_comparison(temp, run_ids, signal_labels)
            plot_labels = [f"{label} [{run_id}]" for label in signal_labels for run_id in run_ids]
            output.parent.mkdir(parents=True, exist_ok=True)
            command = run_plot(temp, output, f"TIMESTEP_{mask}_COMPARE", plot_labels)
            record = entry("comparison", None, temp, output, plot_labels, [raw_path(run_id) for run_id in run_ids], command)
            record.update({"comparison_mask": mask, "comparison_cases": run_ids, "temporary_input_sha256": temp_hash, "temporary_input_deleted": True})
            entries.append(record)
        finally:
            temp.unlink(missing_ok=True)
    summaries: list[str] = []
    summary_root = EXP / "visualization/run_summaries"
    summary_root.mkdir(parents=True, exist_ok=True)
    for run_id in ACTIVE_RUNS:
        path = summary_root / f"{run_id}.md"
        path.write_text("\n".join([f"# {run_id} — timestep spot-check", "", "Scientific interpretation: NOT_PERFORMED.", "", *[f"- [{view}.html](../../plots/cases/{run_id}/{view}.html)" for view in STANDALONE_NAMES], "", "P values are raw radians; plot2 displays rad/(2*pi) turns. These pages are descriptive evidence, not event or SFQ certification.", ""]), encoding="utf-8")
        summaries.append(rel(path))
    standalone = [item for item in entries if item["stage"] == "standalone"]
    comparisons = [item for item in entries if item["stage"] == "comparison"]
    manifest = {"schema": "bjs400-rj2p12-timestep-visualization-manifest-v1", "experiment_id": EXP.name, "created_at_local": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"), "renderer": "scripts/josim-plot2.py", "layout": "sep_comb", "color": "dark", "phase_option": "2pi", "whole_run_window_ps": [0.0, 200.0], "focused_windows": [], "standalone_input_policy": "raw.csv direct; no derived CSV", "comparison_input_policy": "temporary merged CSV under /tmp; deleted after render", "standalone_names": [f"{view}.html" for view in STANDALONE_NAMES], "standalone_entries": standalone, "comparison_entries": comparisons, "standalone_entry_count": len(standalone), "comparison_entry_count": len(comparisons), "logical_case_count": len(ACTIVE_RUNS), "new_physical_case_count": len(new_active), "reused_case_count": len(REUSE_RUNS), "run_summary_paths": summaries, "timestep_values_ps": [0.1, 0.05, 0.025], "masks": ["0001", "0011"], "scientific_analysis_performed": False, "no_focused_window_plots": True, "no_extra_comparison_plots": True, "status": "PASS" if len(standalone) == len(ACTIVE_RUNS) * 3 and len(comparisons) == 2 else "FAIL"}
    (EXP / "visualization/manifest.json").parent.mkdir(parents=True, exist_ok=True)
    (EXP / "visualization/manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": manifest["status"], "standalone_html": len(standalone), "comparison_html": len(comparisons), "logical_cases": len(ACTIVE_RUNS), "scientific_analysis_performed": False}, ensure_ascii=False, indent=2))
    return 0 if manifest["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
