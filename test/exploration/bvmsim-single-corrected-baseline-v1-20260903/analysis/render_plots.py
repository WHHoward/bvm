#!/usr/bin/env python3
"""Render focused classic plots for the corrected single-BVM baseline."""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
import tempfile
from collections import OrderedDict
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
PLOTTER = REPO / "scripts/josim-plot2.py"
sys.path.insert(0, str(REPO / "scripts"))
from bvmtools.raw import RawTrace, read_csv  # noqa: E402
from bvmtools.provenance import sha256_file  # noqa: E402


CONDITIONS = OrderedDict(
    (
        ("S0-R-CORRECTED", EXP / "runs/S0-R-CORRECTED/raw/run-01.csv"),
        ("S1-R-CORRECTED", EXP / "runs/S1-R-CORRECTED/raw/run-01.csv"),
        ("S0-J-CORRECTED-RERUN", EXP / "runs/S0-J-CORRECTED-RERUN/raw/run-01.csv"),
        ("S1-J-CORRECTED-RERUN", EXP / "runs/S1-J-CORRECTED-RERUN/raw/run-01.csv"),
    )
)
OLD = EXP.parent / "bvmsim-bvm-qb-jtl-operational-baseline-v1-20260903/runs/single/S1-R/raw/run-01.csv"

PLOTS = OrderedDict(
    (
        (
            "BVM_STIMULUS_AND_STATE",
            ["I(I_WL1)", "I(I_BL1)", "I(I_SE1)", "P(BVMOUT)"],
            "Corrected single-BVM stimulus and state — WRITE WL+BL; READ WL+SE (BL=0)",
        ),
        (
            "BVM_SENSING",
            [
                "P(B_JM1|XBVM1)", "V(B_JM1|XBVM1)", "P(B_JS2|XBVM1)",
                "V(SL1)", "I(L_SL|XBVM1)", "P(B_LD4_01)", "V(B_LD4_01)",
                "P(B_LD4_11)", "V(B_LD4_11)", "P(BVMOUT)", "V(BVMOUT)", "I(BVMOUT)",
            ],
            "Corrected single-BVM sensing line and terminal response",
        ),
        (
            "QB_INTERNAL",
            [
                "V(QBIN)", "V(QBOUT)", "I(LIN|XBQ1)",
                "P(BJS|XBQ1)", "V(BJS|XBQ1)", "I(BJS|XBQ1)",
                "P(BJ1|XBQ1)", "V(BJ1|XBQ1)", "I(BJ1|XBQ1)", "I(RJ1|XBQ1)",
                "P(BJ2|XBQ1)", "V(BJ2|XBQ1)", "I(BJ2|XBQ1)", "I(RJ2|XBQ1)",
                "I(L1|XBQ1)", "I(L2|XBQ1)", "I(L3|XBQ1)", "I(IB|XBQ1)",
            ],
            "Original QB internal phase, voltage and current probes",
        ),
        (
            "QB_BURST",
            [
                "V(QBIN)", "V(QBOUT)", "P(BJS|XBQ1)", "V(BJS|XBQ1)",
                "P(BJ1|XBQ1)", "V(BJ1|XBQ1)", "P(BJ2|XBQ1)", "V(BJ2|XBQ1)",
            ],
            "Original QB READ-associated response — phase is rad/(2pi) turns",
        ),
        (
            "JTL_TRANSPORT",
            sum(
                ([f"P(B01|XJTL1_{stage})", f"V(B01|XJTL1_{stage})", f"P(B02|XJTL1_{stage})", f"V(B02|XJTL1_{stage})"] for stage in range(1, 7)),
                [],
            ),
            "Six-stage historical JTL transport — B01/B02 phase and voltage",
        ),
    )
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_plot(input_path: Path, output_path: Path, title: str, labels: list[str]) -> dict[str, Any]:
    command = [
        sys.executable,
        str(PLOTTER),
        str(input_path),
        "-x", str(output_path),
        "-t", "sep_comb",
        "-c", "dark",
        "-j", "2pi",
        "-w", title,
        "-s", *labels,
    ]
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"plot failed ({result.returncode}): {' '.join(command)}\n{result.stderr}")
    html = output_path.read_text(encoding="utf-8")
    if "Unknown" in html:
        raise RuntimeError(f"plot has Unknown axis: {output_path}")
    if any(label.startswith("P(") for label in labels) and "Phase (turns)" not in html:
        raise RuntimeError(f"plot phase unit QA failed: {output_path}")
    return {
        "output": str(output_path.relative_to(EXP)),
        "input": str(input_path.relative_to(REPO)) if input_path.is_relative_to(REPO) else str(input_path),
        "input_sha256": sha(input_path),
        "output_sha256": sha(output_path),
        "title": title,
        "selected_labels": labels,
        "renderer_command": command,
        "exit_code": result.returncode,
        "qa": {
            "unknown_axis_absent": "Unknown" not in html,
            "phase_turn_label_present": not any(label.startswith("P(") for label in labels) or "Phase (turns)" in html,
            "classic_renderer": True,
        },
    }


def write_derived(path: Path, traces: list[tuple[str, RawTrace, str]]) -> None:
    first = traces[0][1]
    for _, trace, _ in traces[1:]:
        if trace.time != first.time:
            raise RuntimeError("derived plot requires exact shared time grid; no interpolation allowed")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        headers = ["time"] + [label for _, _, label in traces]
        writer.writerow(headers)
        for index, time in enumerate(first.time):
            writer.writerow([time] + [trace.column(source)[index] for source, trace, _ in traces])


def main() -> int:
    traces = {condition: read_csv(path) for condition, path in CONDITIONS.items()}
    old_trace = read_csv(OLD)
    before_hashes = {str(path): sha(path) for path in list(CONDITIONS.values()) + [OLD]}
    manifest: dict[str, Any] = {
        "renderer": str(PLOTTER.relative_to(REPO)),
        "renderer_sha256": sha(PLOTTER),
        "phase_option": "2pi; P(...) raw radians are displayed as turns",
        "raw_immutable_qa": {"before": before_hashes},
        "individual": [],
        "merged": [],
    }
    for condition, input_path in CONDITIONS.items():
        for name, labels, title in PLOTS.items():
            if name == "JTL_TRANSPORT" and "-J-" not in condition:
                continue
            output = EXP / "plots/runs" / condition / f"{name}.html"
            manifest["individual"].append(run_plot(input_path, output, f"{title} — {condition}", labels))

    derived = EXP / "plots/derived"
    merged_specs = [
        (
            "SINGLE_S0_VS_S1_CORRECTED",
            [
                ("I(I_WL1)", traces["S0-R-CORRECTED"], "I(I_WL1) [S0-R]"),
                ("I(I_BL1)", traces["S0-R-CORRECTED"], "I(I_BL1) [S0-R]"),
                ("I(I_SE1)", traces["S0-R-CORRECTED"], "I(I_SE1) [S0-R]"),
                ("P(BVMOUT)", traces["S0-R-CORRECTED"], "P(BVMOUT) [S0-R]"),
                ("P(BVMOUT)", traces["S1-R-CORRECTED"], "P(BVMOUT) [S1-R]"),
                ("V(QBIN)", traces["S0-R-CORRECTED"], "V(QBIN) [S0-R]"),
                ("V(QBIN)", traces["S1-R-CORRECTED"], "V(QBIN) [S1-R]"),
                ("P(BJ2|XBQ1)", traces["S0-R-CORRECTED"], "P(BJ2|XBQ1) [S0-R]"),
                ("P(BJ2|XBQ1)", traces["S1-R-CORRECTED"], "P(BJ2|XBQ1) [S1-R]"),
            ],
            "Corrected single-BVM S0 versus S1 — same WL+SE READ",
            [
                "I(I_WL1) [S0-R]", "I(I_BL1) [S0-R]", "I(I_SE1) [S0-R]",
                "P(BVMOUT) [S0-R]", "P(BVMOUT) [S1-R]", "V(QBIN) [S0-R]",
                "V(QBIN) [S1-R]", "P(BJ2|XBQ1) [S0-R]", "P(BJ2|XBQ1) [S1-R]",
            ],
        ),
        (
            "SINGLE_DIRECT_VS_JTL_CORRECTED",
            [
                ("P(BJ2|XBQ1)", traces["S0-R-CORRECTED"], "P(BJ2|XBQ1) [S0-direct]"),
                ("P(BJ2|XBQ1)", traces["S0-J-CORRECTED-RERUN"], "P(BJ2|XBQ1) [S0-JTL]"),
                ("P(BJ2|XBQ1)", traces["S1-R-CORRECTED"], "P(BJ2|XBQ1) [S1-direct]"),
                ("P(BJ2|XBQ1)", traces["S1-J-CORRECTED-RERUN"], "P(BJ2|XBQ1) [S1-JTL]"),
                ("V(QBIN)", traces["S0-R-CORRECTED"], "V(QBIN) [S0-direct]"),
                ("V(QBIN)", traces["S0-J-CORRECTED-RERUN"], "V(QBIN) [S0-JTL]"),
                ("V(QBIN)", traces["S1-R-CORRECTED"], "V(QBIN) [S1-direct]"),
                ("V(QBIN)", traces["S1-J-CORRECTED-RERUN"], "V(QBIN) [S1-JTL]"),
                ("P(B02|XJTL1_6)", traces["S0-J-CORRECTED-RERUN"], "P(B02|XJTL1_6) [S0-JTL]"),
                ("P(B02|XJTL1_6)", traces["S1-J-CORRECTED-RERUN"], "P(B02|XJTL1_6) [S1-JTL]"),
            ],
            "Corrected single-BVM direct 10 ohm versus six-stage JTL load",
            [
                "P(BJ2|XBQ1) [S0-direct]", "P(BJ2|XBQ1) [S0-JTL]",
                "P(BJ2|XBQ1) [S1-direct]", "P(BJ2|XBQ1) [S1-JTL]",
                "V(QBIN) [S0-direct]", "V(QBIN) [S0-JTL]", "V(QBIN) [S1-direct]", "V(QBIN) [S1-JTL]",
                "P(B02|XJTL1_6) [S0-JTL]", "P(B02|XJTL1_6) [S1-JTL]",
            ],
        ),
    ]
    for name, series, title, labels in merged_specs:
        path = derived / f"{name}.csv"
        write_derived(path, series)
        output = EXP / "plots" / f"{name}.html"
        record = run_plot(path, output, title, labels)
        record["derived_csv"] = str(path.relative_to(EXP))
        record["derived_csv_sha256"] = sha(path)
        manifest["merged"].append(record)

    old_series = []
    for source, label in (("I(I_WL1)", "I(I_WL1) [OLD S1-R INVALID]"), ("I(I_BL1)", "I(I_BL1) [OLD S1-R INVALID]"), ("I(I_SE1)", "I(I_SE1) [OLD S1-R INVALID]")):
        old_series.append((source, old_trace, label))
    for source, label in (("I(I_WL1)", "I(I_WL1) [CORRECTED S1-R]"), ("I(I_BL1)", "I(I_BL1) [CORRECTED S1-R]"), ("I(I_SE1)", "I(I_SE1) [CORRECTED S1-R]")):
        old_series.append((source, traces["S1-R-CORRECTED"], label))
    old_csv = derived / "OLD_INVALID_VS_CORRECTED_STIMULUS.csv"
    write_derived(old_csv, old_series)
    old_labels = [label for _, _, label in old_series]
    old_html = EXP / "plots/OLD_INVALID_VS_CORRECTED_STIMULUS.html"
    old_record = run_plot(
        old_csv,
        old_html,
        "Historical invalid single-BVM versus corrected stimulus — SE-only versus WL+SE READ",
        old_labels,
    )
    old_record["derived_csv"] = str(old_csv.relative_to(EXP))
    old_record["derived_csv_sha256"] = sha(old_csv)
    manifest["merged"].append(old_record)

    after_hashes = {str(path): sha(path) for path in list(CONDITIONS.values()) + [OLD]}
    if before_hashes != after_hashes:
        raise RuntimeError("raw hash changed during visualization")
    manifest["raw_immutable_qa"]["after"] = after_hashes
    manifest["raw_immutable_qa"]["unchanged"] = True
    manifest_path = EXP / "analysis/plot_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"individual_plots": len(manifest["individual"]), "merged_plots": len(manifest["merged"]), "manifest": str(manifest_path.relative_to(EXP))}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
