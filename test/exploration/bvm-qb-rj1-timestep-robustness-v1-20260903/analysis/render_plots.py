#!/usr/bin/env python3
"""Render one compact classic plot set for every effective run.

No cross-condition data are mixed here.  Each temporary projection contains
one raw trace only.  Comparison rendering is a separate second-stage script
and is allowed to run only after this script's manifest reports all runs QA.
"""

from __future__ import annotations

import argparse
import csv
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


PAGE_SELECTIONS = {
    "BVM_INTERFACE.html": (
        "BVM / QB interface",
        ("P(BVMOUT)", "V(BVMOUT)", "I(BVMOUT)", "V(QBIN)"),
    ),
    "QB_INTERNAL.html": (
        "QB internal key signals",
        ("P(BJS|XBQ1)", "P(BJ1|XBQ1)", "P(BJ2|XBQ1)", "V(BJ2|XBQ1)", "V(QBOUT)"),
    ),
    "BJ2_EVENT.html": (
        "QB BJ2 phase / voltage / current",
        ("P(BJ2|XBQ1)", "V(BJ2|XBQ1)", "I(BJ2|XBQ1)"),
    ),
    "JTL_TRANSPORT_VOLTAGE.html": (
        "BJ2 -> JTL output-facing voltage (JTL1 / JTL3 / JTL6)",
        ("V(BJ2|XBQ1)", "V(B02|XJTL1_1)", "V(B02|XJTL1_3)", "V(B02|XJTL1_6)"),
    ),
    "JTL_TRANSPORT_PHASE.html": (
        "BJ2 -> JTL output-facing phase turns (JTL1 / JTL3 / JTL6)",
        ("P(BJ2|XBQ1)", "P(B02|XJTL1_1)", "P(B02|XJTL1_3)", "P(B02|XJTL1_6)"),
    ),
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel(path: Path) -> str:
    return str(path.resolve().relative_to(REPO.resolve()))


def json_write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def display_label(run_id: str, source_label: str) -> str:
    if not source_label or source_label[0] not in {"P", "V", "I"}:
        raise ValueError(f"plot signal must retain P/V/I prefix: {source_label!r}")
    return f"{source_label} [{run_id}]"


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


def projection(trace: RawTrace, run_id: str, labels: tuple[str, ...], directory: Path) -> tuple[Path, list[str]]:
    display = [display_label(run_id, label) for label in labels]
    if len(set(display)) != len(display):
        raise ValueError(f"duplicate display labels for {run_id}")
    path = directory / f"{run_id}_projection.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["time", *display])
        columns = [trace.column(label) for label in labels]
        for index, time_value in enumerate(trace.time):
            writer.writerow([f"{time_value:.17e}", *[f"{values[index]:.17e}" for values in columns]])
    return path, display


def render_one(run: dict[str, Any], trace: RawTrace, output_dir: Path, temporary: Path) -> dict[str, Any]:
    run_id = str(run["run_id"])
    page_records = []
    for filename, (description, labels) in PAGE_SELECTIONS.items():
        csv_path, display = projection(trace, run_id, labels, temporary)
        output = output_dir / filename
        command = [
            sys.executable,
            str(PLOTTER),
            str(csv_path),
            "-x", str(output),
            "-t", "sep_comb",
            "-c", "dark",
            "-j", "2pi",
            "-w", f"{run_id} — {description}",
            "-s", *display,
        ]
        completed = subprocess.run(command, cwd=REPO, capture_output=True, text=True, check=False)
        if completed.returncode != 0:
            raise RuntimeError(f"josim-plot2 failed for {run_id}/{filename}: {completed.stdout}\n{completed.stderr}")
        if not output.is_file() or output.stat().st_size == 0:
            raise RuntimeError(f"empty plot output: {output}")
        html = output.read_text(encoding="utf-8")
        missing_labels = [label for label in display if label not in html]
        expected_axis_titles = {
            "phase": "Phase (turns)" in html,
            "voltage": "Voltage (V)" in html,
            "current": "Current (I)" in html,
        }
        unknown_axis_title = bool(re.search(r'"title"\s*:\s*\{\s*"text"\s*:\s*"Unknown[^"}]*"\s*\}', html))
        page_records.append(
            {
                "output": rel(output),
                "sha256": sha256(output),
                "renderer": rel(PLOTTER),
                "renderer_sha256": sha256(PLOTTER),
                "renderer_command": [str(item) for item in command],
                "source_raw": rel(Path(run["effective_raw"])),
                "selected_source_labels": list(labels),
                "selected_display_labels": display,
                "phase_conversion": "P raw radians -> turns via josim-plot2 -j 2pi" if any(label.startswith("P(") for label in labels) else "not applicable",
                "interpolation": "none",
                "qa": {
                    "exists_nonempty": True,
                    "labels_present": not missing_labels,
                    "missing_labels": missing_labels,
                    "expected_axis_titles": expected_axis_titles,
                    "unknown_axis_title_present": unknown_axis_title,
                },
            }
        )
    return {
        "run_id": run_id,
        "output_dir": rel(output_dir),
        "raw": rel(Path(run["effective_raw"])),
        "raw_sha256": run["raw_sha256"],
        "pages": page_records,
        "qa_status": "PASS" if all(page_qa_pass(page) for page in page_records) else "FAIL",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--timestamp", default=None)
    args = parser.parse_args()
    timestamp = args.timestamp or datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    manifest = json.loads((EXP / "analysis/effective_run_manifest.json").read_text(encoding="utf-8"))
    plot_runs = []
    failures = []
    with tempfile.TemporaryDirectory(prefix="rj1_run_plots_") as temporary_name:
        temporary = Path(temporary_name)
        for run in manifest["runs"]:
            run_id = str(run["run_id"])
            run_metrics = EXP / "runs" / run_id / "analysis/metrics.json"
            metrics = json.loads(run_metrics.read_text(encoding="utf-8"))
            run["raw_sha256"] = metrics["raw_sha256"]
            run["effective_raw"] = str(REPO / metrics["raw_path"])
            output_dir = EXP / "runs" / run_id / "plots"
            output_dir.mkdir(parents=True, exist_ok=True)
            try:
                trace = read_csv(run["effective_raw"])
                rendered = render_one(run, trace, output_dir, temporary)
                plot_runs.append(rendered)
                json_write(output_dir / "manifest.json", rendered)
            except Exception as exc:  # noqa: BLE001 - retain all run failures in manifest
                failures.append({"run_id": run_id, "error": str(exc)})
    result = {
        "generated_at": timestamp,
        "stage": "individual_runs_before_comparison",
        "renderer": rel(PLOTTER),
        "profile": "CLASSIC_LOCKED",
        "layout": "sep_comb",
        "color": "dark",
        "phase_option": "2pi",
        "raw_immutable": True,
        "run_count_expected": len(manifest["runs"]),
        "run_count_rendered": len(plot_runs),
        "runs": plot_runs,
        "failures": failures,
        "qa_status": "PASS" if len(plot_runs) == len(manifest["runs"]) and not failures and all(page["qa_status"] == "PASS" for item in plot_runs for page in [item]) else "FAIL",
        "comparison_gate": "OPEN" if len(plot_runs) == len(manifest["runs"]) and not failures else "CLOSED",
    }
    json_write(EXP / "analysis/plot_manifest.json", result)
    print(json.dumps({"status": result["qa_status"], "rendered": len(plot_runs), "failures": failures}, ensure_ascii=False))
    return 0 if result["qa_status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
