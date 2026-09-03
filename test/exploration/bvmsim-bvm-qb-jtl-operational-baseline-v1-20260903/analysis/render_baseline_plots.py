#!/usr/bin/env python3
"""Render compact, reproducible baseline visualizations with josim-plot2."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
RENDERER = REPO / "scripts/josim-plot2.py"
METRICS = EXP / "analysis/metrics.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def safe_name(value: str) -> str:
    return value.replace("/", "_").replace(" ", "_")


def load_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise RuntimeError(f"missing CSV header: {path}")
        return list(reader.fieldnames), list(reader)


def write_derived(path: Path, time_values: list[str], columns: list[tuple[str, list[str]]]) -> None:
    if path.exists():
        old_hash = sha256(path)
        # Derived plot inputs are reproducible artifacts, not raw evidence.
        # Refuse accidental replacement with different data.
        with path.open(newline="", encoding="utf-8") as handle:
            existing = handle.read()
        import io

        buffer = io.StringIO()
        writer = csv.writer(buffer, lineterminator="\n")
        writer.writerow(["time"] + [name for name, _ in columns])
        for index, time_value in enumerate(time_values):
            writer.writerow([time_value] + [values[index] for _, values in columns])
        if buffer.getvalue() != existing:
            raise RuntimeError(f"refusing to overwrite derived plot input: {path} ({old_hash})")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["time"] + [name for name, _ in columns])
        for index, time_value in enumerate(time_values):
            writer.writerow([time_value] + [values[index] for _, values in columns])


def raw_columns(path: Path, labels: list[str]) -> tuple[list[str], dict[str, list[str]]]:
    headers, rows = load_rows(path)
    if len(headers) != len(set(headers)):
        raise RuntimeError(f"duplicate CSV columns are not accepted by classic plot path: {path}")
    missing = [label for label in labels if label not in headers]
    if missing:
        raise RuntimeError(f"missing plot labels in {path}: {missing}")
    return [row["time"] for row in rows], {label: [row[label] for row in rows] for label in labels}


def plot_one(raw: Path, output: Path, labels: list[str], title: str) -> dict[str, Any]:
    before = sha256(raw)
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "python3",
        str(RENDERER),
        str(raw),
        "-x",
        str(output),
        "-t",
        "sep_comb",
        "-c",
        "dark",
        "-j",
        "2pi",
        "-w",
        title,
        "-s",
        *labels,
    ]
    completed = subprocess.run(command, cwd=REPO, text=True, capture_output=True, check=False)
    after = sha256(raw)
    if completed.returncode != 0:
        raise RuntimeError(f"plot failed for {raw}: exit={completed.returncode}\n{completed.stderr[-2000:]}")
    if before != after:
        raise RuntimeError(f"raw changed while plotting: {raw}")
    html = output.read_text(encoding="utf-8")
    phase_expected = any(label.startswith("P") for label in labels)
    qa = {
        "exit_code": completed.returncode,
        "output_exists": output.is_file(),
        "raw_hash_before": before,
        "raw_hash_after": after,
        "raw_unchanged": before == after,
        # Plotly's embedded JavaScript contains unrelated strings such as
        # "Unknown encoding".  QA only the rendered axis title itself.
        "phase_axis_present": "Phase (turns) [rad" in html and "2pi" in html if phase_expected else True,
        "unknown_axis_absent": re.search(r'"title":\{"text":"Unknown', html) is None,
        "labels": labels,
        "command": command,
        "html_sha256": sha256(output),
    }
    if not all(qa[key] for key in ("output_exists", "raw_unchanged", "phase_axis_present", "unknown_axis_absent")):
        raise RuntimeError(f"plot QA failed: {qa}")
    return qa


def compare_inputs(results: list[dict[str, Any]], labels: list[tuple[str, str]]) -> tuple[Path, list[str]]:
    sources: dict[str, tuple[Path, dict[str, list[str]], list[str]]] = {}
    for run_id, raw_text in ((item["run_id"], item["raw"]) for item in results):
        raw = REPO / raw_text
        requested = [base for base, tag in labels if tag == run_id]
        if not requested:
            continue
        time_values, data = raw_columns(raw, requested)
        sources[run_id] = (raw, data, time_values)
    if not sources:
        raise RuntimeError("no sources for comparison")
    first_time = next(iter(sources.values()))[2]
    for raw, _, time_values in sources.values():
        if time_values != first_time:
            raise RuntimeError(f"comparison grid mismatch: {raw}")
    columns: list[tuple[str, list[str]]] = []
    for base, run_id in labels:
        _, data, _ = sources[run_id]
        columns.append((f"{base} [{run_id}]", data[base]))
    path = EXP / "plots/derived" / ("single_2x2.csv" if len(results) == 4 else "four_key_states.csv")
    write_derived(path, first_time, columns)
    return path, [name for name, _ in columns]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    metrics = json.loads(METRICS.read_text(encoding="utf-8"))["results"]
    records = metrics["four"] + metrics["single"]
    manifest: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "renderer": str(RENDERER.relative_to(REPO)),
        "renderer_sha256": sha256(RENDERER),
        "layout": "sep_comb",
        "color": "dark",
        "phase_option": "-j 2pi; raw P(...) radians are displayed as rad/2pi turns",
        "individual": [],
        "comparisons": [],
    }
    core = [
        "I(BVMOUT)",
        "V(BVMOUT)",
        "P(BVMOUT)",
        "I(LIN|XBQ1)",
        "V(QBIN)",
        "V(QBOUT)",
        "I(BJ2|XBQ1)",
        "V(BJ2|XBQ1)",
        "P(BJ2|XBQ1)",
    ]
    for item in records:
        run_id = item["run_id"]
        raw = REPO / item["raw"]
        labels = list(core)
        if item.get("load") == "JTL" or item["family"] == "four_bvm":
            labels.extend(["V(B02|XJTL1_6)", "P(B02|XJTL1_6)"])
        output = EXP / "plots/runs" / safe_name(run_id) / "RUN_OVERVIEW.html"
        title = f"Historical BVMSim original QB baseline — {run_id} — key signals"
        if args.check_only:
            headers, _ = load_rows(raw)
            missing = [label for label in labels if label not in headers]
            if missing:
                raise RuntimeError(f"missing labels for {run_id}: {missing}")
            qa = {"check_only": True, "labels": labels, "raw_sha256": sha256(raw)}
        else:
            qa = plot_one(raw, output, labels, title)
        entry = {
            "run_id": run_id,
            "family": item["family"],
            "state": item.get("state"),
            "raw": item["raw"],
            "raw_sha256": sha256(raw),
            "output": str(output.relative_to(REPO)),
            "qa": qa,
        }
        manifest["individual"].append(entry)

    four = metrics["four"]
    selected_four = ["0000", "0100", "0001", "1111"]
    state_to_run = {item["state"]: item["run_id"] for item in four}
    four_labels = [("P(BJ2|XBQ1)", state_to_run[state]) for state in selected_four]
    four_labels.append(("P(B02|XJTL1_6)", state_to_run["1111"]))
    four_input, four_plot_labels = compare_inputs(four, four_labels)
    four_output = EXP / "plots/RESULT_OVERVIEW.html"
    if not args.check_only:
        four_qa = plot_one(
            four_input,
            four_output,
            four_plot_labels,
            "Historical BVMSim original QB baseline — representative 4-BVM states",
        )
    else:
        four_qa = {"check_only": True, "input_sha256": sha256(four_input)}
    manifest["comparisons"].append({
        "name": "representative_four_state_overview",
        "input": str(four_input.relative_to(REPO)),
        "output": str(four_output.relative_to(REPO)),
        "labels": four_plot_labels,
        "qa": four_qa,
    })

    single = metrics["single"]
    single_labels = [("P(BJ2|XBQ1)", item["run_id"]) for item in single]
    single_labels.extend(("P(B02|XJTL1_6)", item["run_id"]) for item in single if item.get("load") == "JTL")
    single_input, single_plot_labels = compare_inputs(single, single_labels)
    single_output = EXP / "plots/SINGLE_2X2_OVERVIEW.html"
    if not args.check_only:
        single_qa = plot_one(
            single_input,
            single_output,
            single_plot_labels,
            "Historical BVMSim original QB baseline — single-BVM 2x2 overview",
        )
    else:
        single_qa = {"check_only": True, "input_sha256": sha256(single_input)}
    manifest["comparisons"].append({
        "name": "single_2x2_overview",
        "input": str(single_input.relative_to(REPO)),
        "output": str(single_output.relative_to(REPO)),
        "labels": single_plot_labels,
        "qa": single_qa,
    })

    manifest_path = EXP / "analysis/visualization_manifest.json"
    if not args.check_only:
        manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps({"individual": len(manifest["individual"]), "comparisons": len(manifest["comparisons"])}, ensure_ascii=False))
    else:
        print(json.dumps({"check_only": True, "individual": len(manifest["individual"]), "comparisons": len(manifest["comparisons"])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
