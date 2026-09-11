#!/usr/bin/env python3
"""Render the selected-mask flat whole-run BJS400 visualization set.

Standalone pages read each run's raw.csv directly.  Comparison pages use
temporary full-run merged CSV files under /tmp and delete them immediately
after rendering.  This script never invokes JoSIM.
"""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
import tempfile
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
PLOTTER = REPO / "scripts/josim-plot2.py"
sys.path.insert(0, str(REPO / "scripts"))
from bvmtools.phase import continuous_unwrap  # noqa: E402
from bvmtools.raw import RawTrace, read_csv  # noqa: E402


RUN_IDS = (
    "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P10_0111",
)
RUNS = OrderedDict((run_id, f"runs/{run_id}") for run_id in RUN_IDS)
REFERENCE_PATHS = {
    "RJ2P10_0011": EXP / "references/rj2p10/ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P10_0011/raw.csv",
    "RJ2P11_0111": EXP / "references/rj2p11/ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P11_0111/raw.csv",
    "RJ2P12_0111": EXP / "references/rj2p12/ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_0111/raw.csv",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO.resolve()).as_posix()


def raw_path(run_id: str) -> Path:
    return EXP / RUNS[run_id] / "raw.csv"


def read_trace(path: Path) -> RawTrace:
    trace = read_csv(path)
    if trace.duplicate_columns:
        raise RuntimeError(f"duplicate raw columns: {path}: {trace.duplicate_columns}")
    return trace


def add_pvi(labels: list[str], name: str) -> None:
    labels.extend((f"P({name})", f"V({name})", f"I({name})"))


def add_iv(labels: list[str], name: str) -> None:
    labels.extend((f"I({name})", f"V({name})"))


def bvm_instances(topology: str) -> tuple[int, ...]:
    return (1, 2, 3, 4) if topology == "ARRAY" else (1,)


def topology_for(run_id: str) -> str:
    return "ARRAY" if run_id.startswith("ARRAY_") else "SINGLE"


def signal_specs(topology: str) -> OrderedDict[str, list[str]]:
    instances = bvm_instances(topology)
    if topology == "ARRAY":
        controls = [f"I(I_{kind}{instance})" for instance in instances for kind in ("WL", "BL", "SE")]
    else:
        controls = [f"I(I_{kind})" for kind in ("WL", "BL", "SE")]

    signal_path = list(controls)
    signal_path.extend(f"I(L_SL|XBVM{instance})" for instance in instances)
    signal_path.extend(("V(COMMON_SL)", "I(B_JSL1)", "I(B_JSL8)", "V(QBIN)", "V(QBOUT)"))
    signal_path.extend(f"V(JTL{stage}_OUT)" for stage in range(1, 7))
    signal_path.append("I(R_TERM)")

    bvm_state: list[str] = []
    for instance in instances:
        header = f"XBVM{instance}"
        for jj in ("B_JM1", "B_JM2", "B_JS1", "B_JS2"):
            add_pvi(bvm_state, f"{jj}|{header}")
        bvm_state.extend((f"I(L_M3|{header})", f"I(L_S3|{header})"))

    bvm_output: list[str] = []
    for instance in instances:
        header = f"XBVM{instance}"
        for branch in ("L_PSL", "R_SL", "L_SL"):
            add_iv(bvm_output, f"{branch}|{header}")
    bvm_output.append("V(COMMON_SL)")

    jsl_chain = ["V(COMMON_SL)"]
    for index in range(1, 9):
        add_pvi(jsl_chain, f"B_JSL{index}")
    jsl_chain.append("V(QBIN)")

    qb_state = [
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

    jtl_chain: list[str] = []
    for stage in range(1, 7):
        header = f"XJTL1_{stage}"
        for jj in ("B01", "B02"):
            add_pvi(jtl_chain, f"{jj}|{header}")
        jtl_chain.append(f"V(JTL{stage}_OUT)")
    jtl_chain.append("I(R_TERM)")

    return OrderedDict(
        (
            ("SIGNAL_PATH", signal_path),
            ("BVM_STATE", bvm_state),
            ("BVM_OUTPUT", bvm_output),
            ("JSL_CHAIN", jsl_chain),
            ("QB_STATE", qb_state),
            ("JTL_CHAIN", jtl_chain),
        )
    )


def matched_comparison_labels() -> list[str]:
    labels = [
        "V(COMMON_SL)", "I(L_SL|XBVM1)", "I(B_JSL1)", "I(B_JSL8)",
        "V(QBIN)", "V(QBOUT)",
        "P(BJS|XBQ1)", "V(BJS|XBQ1)", "I(BJS|XBQ1)",
        "P(BJ1|XBQ1)", "V(BJ1|XBQ1)", "I(BJ1|XBQ1)",
        "I(RJ1|XBQ1)", "V(RJ1|XBQ1)",
        "I(L1|XBQ1)", "V(L1|XBQ1)", "I(IB|XBQ1)",
        "I(L2|XBQ1)", "V(L2|XBQ1)",
        "P(BJ2|XBQ1)", "V(BJ2|XBQ1)", "I(BJ2|XBQ1)",
        "I(RJ2|XBQ1)", "V(RJ2|XBQ1)",
        "I(L3|XBQ1)", "V(L3|XBQ1)",
    ]
    labels.extend(f"V(JTL{stage}_OUT)" for stage in range(1, 7))
    labels.append("I(R_TERM)")
    return labels


def source_record(path: Path) -> dict[str, object]:
    return {"path": rel(path), "sha256": sha256(path), "bytes": path.stat().st_size}


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


def entry(
    *,
    stage: str,
    name: str,
    input_path: Path,
    output_path: Path,
    labels: list[str],
    source_paths: list[Path],
    command: list[str],
    comparison_cases: list[str] | None = None,
    temp_input_sha256: str | None = None,
) -> dict[str, object]:
    input_name = rel(input_path) if input_path.resolve().is_relative_to(REPO.resolve()) else str(input_path)
    return {
        "stage": stage,
        "name": name,
        "input_path": input_name,
        "input_sha256": sha256(input_path),
        "output_path": rel(output_path),
        "output_sha256": sha256(output_path),
        "source_raw_paths": [rel(path) for path in source_paths],
        "source_raw_sha256": [sha256(path) for path in source_paths],
        "labels": labels,
        "signal_order": labels,
        "comparison_cases": comparison_cases or [],
        "command": command,
        "renderer": rel(PLOTTER),
        "layout": "sep_comb",
        "color": "dark",
        "phase_option": "2pi",
        "phase_convention": "raw P radians; plot2 displays rad/(2*pi) turns; never SFQ count",
        "window_ps": [0.0, 200.0],
        "window_semantics": "whole-run raw timestamps; no focused window",
        "input_mode": "RAW_DIRECT" if stage == "standalone" else "TEMPORARY_MERGED_COMPARISON",
        "temporary_input_sha256": temp_input_sha256,
    }


def write_comparison_csv(path: Path, case_paths: list[Path], case_names: list[str], labels: list[str]) -> str:
    traces = [read_trace(source) for source in case_paths]
    base_time = traces[0].time
    if any(trace.time != base_time for trace in traces[1:]):
        raise RuntimeError("comparison source time grids differ")
    positions: list[tuple[RawTrace, dict[str, int]]] = []
    for trace in traces:
        position = {label: index for index, label in enumerate(trace.headers)}
        missing = [label for label in labels if label not in position]
        if missing:
            raise RuntimeError(f"comparison source missing labels: {missing}")
        positions.append((trace, position))
    phase_columns = {
        (case_index, label): continuous_unwrap(tuple(traces[case_index].column(label)))
        for case_index in range(len(traces))
        for label in labels
        if label.startswith("P(")
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        headers = ["time"]
        headers.extend(f"{label} [{case}]" for label in labels for case in case_names)
        writer.writerow(headers)
        for index, timestamp in enumerate(base_time):
            row: list[object] = [f"{timestamp:.17g}"]
            for label in labels:
                for case_index in range(len(case_names)):
                    trace, position = positions[case_index]
                    if label.startswith("P("):
                        row.append(f"{phase_columns[(case_index, label)][index]:.17g}")
                    else:
                        row.append(f"{trace.column(label)[index]:.17g}")
            writer.writerow(row)
    return sha256(path)


def render_standalone(manifest_entries: list[dict[str, object]]) -> None:
    for run_id, directory in RUNS.items():
        source = raw_path(run_id)
        trace = read_trace(source)
        topology = topology_for(run_id)
        specs = signal_specs(topology)
        for name, labels in specs.items():
            missing = [label for label in labels if label not in trace.headers]
            if missing:
                raise RuntimeError(f"{run_id}/{name} missing labels: {missing}")
            output = EXP / "plots" / "runs" / run_id / f"{name}.html"
            output.parent.mkdir(parents=True, exist_ok=True)
            command = run_plot2(source, output, f"{run_id} — {name}", labels)
            manifest_entries.append(entry(
                stage="standalone",
                name=name,
                input_path=source,
                output_path=output,
                labels=labels,
                source_paths=[source],
                command=command,
            ))


def render_comparison(
    manifest_entries: list[dict[str, object]],
    name: str,
    case_names: list[str],
    case_paths: list[Path],
    labels: list[str],
    output: Path,
) -> None:
    temp_path = Path(tempfile.mkstemp(prefix="bjs400-comparison-", suffix=".csv", dir="/tmp")[1])
    try:
        temp_hash = write_comparison_csv(temp_path, case_paths, case_names, labels)
        output.parent.mkdir(parents=True, exist_ok=True)
        command = run_plot2(temp_path, output, name, [f"{label} [{case}]" for label in labels for case in case_names])
        manifest_entries.append(entry(
            stage="comparison",
            name=name,
            input_path=temp_path,
            output_path=output,
            labels=[f"{label} [{case}]" for label in labels for case in case_names],
            source_paths=case_paths,
            comparison_cases=case_names,
            command=command,
            temp_input_sha256=temp_hash,
        ))
    finally:
        temp_path.unlink(missing_ok=True)


def write_run_summaries() -> list[Path]:
    outputs: list[Path] = []
    summary_root = EXP / "visualization" / "run_summaries"
    summary_root.mkdir(parents=True, exist_ok=True)
    for run_id in RUNS:
        path = summary_root / f"{run_id}.md"
        lines = [
            f"# {run_id} — flat whole-run evidence",
            "",
            "Scientific interpretation: NOT_PERFORMED.",
            "",
            "All six pages are whole-run 0-200ps views generated from raw.csv.",
            "",
        ]
        for name in ("SIGNAL_PATH", "BVM_STATE", "BVM_OUTPUT", "JSL_CHAIN", "QB_STATE", "JTL_CHAIN"):
            lines.append(f"- [{name}.html](../plots/runs/{run_id}/{name}.html)")
        lines.extend(
            [
                "",
                "Phase P values remain raw radians; plot2 uses the registered 2pi display option.",
                "No page is an SFQ/event classifier or mechanism conclusion.",
                "",
            ]
        )
        path.write_text("\n".join(lines), encoding="utf-8")
        outputs.append(path)
    return outputs


def main() -> int:
    manifest_entries: list[dict[str, object]] = []
    render_standalone(manifest_entries)
    new_case = RUN_IDS[0]
    render_comparison(
        manifest_entries,
        "RJ2P10_P11_P12_WEIGHT3.html",
        ["RJ2P10_0111", "RJ2P11_0111", "RJ2P12_0111"],
        [raw_path(new_case), REFERENCE_PATHS["RJ2P11_0111"], REFERENCE_PATHS["RJ2P12_0111"]],
        matched_comparison_labels(),
        EXP / "plots/comparison/RJ2P10_P11_P12_WEIGHT3.html",
    )
    render_comparison(
        manifest_entries,
        "RJ2P10_WEIGHT2_VS_WEIGHT3.html",
        ["RJ2P10_0011", "RJ2P10_0111"],
        [REFERENCE_PATHS["RJ2P10_0011"], raw_path(new_case)],
        matched_comparison_labels(),
        EXP / "plots/comparison/RJ2P10_WEIGHT2_VS_WEIGHT3.html",
    )

    summaries = write_run_summaries()
    standalone = [item for item in manifest_entries if item["stage"] == "standalone"]
    comparisons = [item for item in manifest_entries if item["stage"] == "comparison"]
    manifest = {
        "schema": "bjs400-rj2p10-weight3-flat-visualization-manifest-v1",
        "experiment_id": EXP.name,
        "created_at_local": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "renderer": rel(PLOTTER),
        "layout": "sep_comb",
        "color": "dark",
        "phase_option": "2pi",
        "whole_run_window_ps": [0.0, 200.0],
        "focused_windows": [],
        "standalone_input_policy": "RJ2=10/0111 raw.csv direct; no standalone derived CSV",
        "comparison_input_policy": "temporary merged CSV under /tmp; deleted after render",
        "standalone_names": ["SIGNAL_PATH.html", "BVM_STATE.html", "BVM_OUTPUT.html", "JSL_CHAIN.html", "QB_STATE.html", "JTL_CHAIN.html"],
        "standalone_entries": standalone,
        "comparison_entries": comparisons,
        "standalone_entry_count": len(standalone),
        "comparison_entry_count": len(comparisons),
        "run_summary_paths": [rel(path) for path in summaries],
        "scientific_analysis_performed": False,
        "no_mechanism_plots": True,
        "no_extra_masks": True,
        "comparison_reference_policy": "immutable RJ2=10/11/12 raw only",
        "status": "PASS" if len(standalone) == 6 and len(comparisons) == 2 else "FAIL",
    }
    output = EXP / "visualization" / "manifest.json"
    output.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": manifest["status"],
        "standalone_html": len(standalone),
        "comparison_html": len(comparisons),
        "whole_run_only": True,
        "standalone_derived_csv": False,
        "scientific_analysis_performed": False,
    }, ensure_ascii=False, indent=2))
    return 0 if manifest["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
