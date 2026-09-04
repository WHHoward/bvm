#!/usr/bin/env python3
"""Render compact classic plots for each common-SL run and key comparisons."""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Mapping, Sequence


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
OLD_EXP = REPO / "test/exploration/bvmsim-4bvm-allone-selective-read-additivity-isolation-v1-20260904"
PLOTTER = REPO / "scripts/josim-plot2.py"
MASKS = ("0000", "0001", "0010", "0100", "1000", "0011", "0111", "1100", "1110", "1111")
ONE_HOT = ("0001", "0010", "0100", "1000")
ONE_HOT_BY_INSTANCE = {1: "1000", 2: "0100", 3: "0010", 4: "0001"}
FORWARD = ("1100", "1110", "1111")
REVERSE = ("0011", "0111", "1111")
READ = (110e-12, 170e-12)

sys.path.insert(0, str(REPO / "scripts"))
from bvmtools.phase import continuous_unwrap, window_indices  # noqa: E402
from bvmtools.raw import RawTrace, read_csv  # noqa: E402


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO.resolve()).as_posix()


def sig(trace: RawTrace, label: str) -> tuple[float, ...]:
    return trace.column(label)  # type: ignore[return-value]


def write_csv(path: Path, time_s: Sequence[float], columns: Mapping[str, Sequence[float]]) -> None:
    lengths = {len(time_s), *(len(values) for values in columns.values())}
    if len(lengths) != 1 or len(columns) == 0 or len(columns) != len(set(columns)):
        raise RuntimeError(f"invalid derived CSV shape: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["time", *columns.keys()])
        for index, timestamp in enumerate(time_s):
            writer.writerow([f"{timestamp:.17g}", *(f"{values[index]:.17g}" for values in columns.values())])


def render(input_path: Path, output_path: Path, title: str, labels: Sequence[str]) -> dict[str, object]:
    trace = read_csv(input_path)
    if trace.duplicate_columns:
        raise RuntimeError(f"duplicate input columns for plot {input_path}: {trace.duplicate_columns}")
    missing = [label for label in labels if label not in trace.headers]
    if missing:
        raise RuntimeError(f"missing plot labels in {input_path}: {missing}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = [sys.executable, str(PLOTTER), str(input_path), "-x", str(output_path), "-t", "sep_comb", "-c", "dark", "-j", "2pi", "-w", title, "-s", *labels]
    completed = subprocess.run(command, cwd=REPO, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"plot failed: {output_path}\nstdout={completed.stdout}\nstderr={completed.stderr}")
    html = output_path.read_text(encoding="utf-8", errors="replace")
    if "<html" not in html.lower() or '"title":{"text":"Unknown"}' in html:
        raise RuntimeError(f"plot QA failed: {output_path}")
    has_phase = any(label.startswith("P") for label in labels)
    if has_phase and ("Phase (turns)" not in html or "2pi" not in html):
        raise RuntimeError(f"phase 2pi QA failed: {output_path}")
    return {
        "path": rel(output_path),
        "input": rel(input_path),
        "input_sha256": digest(input_path),
        "output_sha256": digest(output_path),
        "title": title,
        "labels": list(labels),
        "command": command,
        "exit_code": completed.returncode,
        "qa": {"html": True, "unknown_axis_absent": True, "classic_renderer": True, "phase_display": "rad/(2*pi) turns" if has_phase else "not applicable"},
    }


def run_specs() -> OrderedDict[str, list[str]]:
    controls = [f"I(I_{control}{instance})" for instance in range(1, 5) for control in ("WL", "BL", "SE")]
    phase = [f"P({jj}|XBVM{instance})" for instance in range(1, 5) for jj in ("B_JM1", "B_JM2", "B_JS1", "B_JS2")]
    internal: list[str] = []
    for instance in range(1, 5):
        for jj in ("B_JM1", "B_JM2", "B_JS1", "B_JS2"):
            internal.extend([f"P({jj}|XBVM{instance})", f"V({jj}|XBVM{instance})", f"I({jj}|XBVM{instance})"])
    rloop_current = [f"I({branch}|XBVM{instance})" for instance in range(1, 5) for branch in ("L_M3", "L_S1", "L_S2", "R_S", "L_S3", "L_PSE", "L_PSL", "R_SL", "L_SL")]
    rloop_voltage = [f"V({branch}|XBVM{instance})" for instance in range(1, 5) for branch in ("L_S1", "B_JS1", "L_S2", "B_JS2", "R_S", "L_S3", "L_PSE", "L_PSL", "R_SL", "L_SL")]
    output = [f"I({branch}|XBVM{instance})" for instance in range(1, 5) for branch in ("L_PSL", "R_SL", "L_SL")]
    output += [f"V({branch}|XBVM{instance})" for instance in range(1, 5) for branch in ("L_PSL", "R_SL", "L_SL")]
    output.append("V(COMMON_SL)")
    common = ["V(COMMON_SL)", "I(B_COL_LOAD01)"] + [f"I(L_SL|XBVM{instance})" for instance in range(1, 5)]
    load = [item for index in range(1, 13) for item in (f"P(B_COL_LOAD{index:02d})", f"V(B_COL_LOAD{index:02d})", f"I(B_COL_LOAD{index:02d})")]
    return OrderedDict((
        ("BVM_STIMULUS_AND_STATE", controls + phase),
        ("BVM_INTERNAL_STATE", internal),
        ("BVM_RLOOP_CURRENT", rloop_current),
        ("BVM_RLOOP_VOLTAGE", rloop_voltage),
        ("BVM_OUTPUT_BRANCHES", output),
        ("COMMON_SL", common),
        ("SHARED_JSL_LOAD", load),
    ))


def selected_vectors(trace: RawTrace, bounds: tuple[float, float]) -> tuple[tuple[float, ...], tuple[int, ...]]:
    indices = window_indices(trace.time, *bounds)
    return tuple(trace.time[index] for index in indices), indices


def phase_difference_rad(trace: RawTrace, baseline: RawTrace, label: str) -> tuple[float, ...]:
    return tuple(a - b for a, b in zip(continuous_unwrap(sig(trace, label)), continuous_unwrap(sig(baseline, label))))


def delta(trace: RawTrace, baseline: RawTrace, label: str) -> tuple[float, ...]:
    return tuple(a - b for a, b in zip(sig(trace, label), sig(baseline, label)))


def sum_lsl(trace: RawTrace) -> tuple[float, ...]:
    return tuple(sum(sig(trace, f"I(L_SL|XBVM{instance})")[i] for instance in range(1, 5)) for i in range(trace.sample_count))


def active_instance(mask: str) -> int:
    return next(index for index, bit in enumerate(mask, start=1) if bit == "1")


def add_comparison(records: list[dict[str, object]], name: str, time_s: Sequence[float], columns: OrderedDict[str, Sequence[float]], title: str) -> None:
    csv_path = EXP / "plots/comparison/data" / f"{name}.csv"
    write_csv(csv_path, time_s, columns)
    records.append(render(csv_path, EXP / "plots/comparison" / f"{name}.html", title, list(columns)))


def comparison_specs(traces: Mapping[str, RawTrace], records: list[dict[str, object]]) -> None:
    baseline = traces["0000"]
    read_indices = selected_vectors(baseline, READ)[1]
    read_time = tuple(baseline.time[index] for index in read_indices)
    columns: OrderedDict[str, Sequence[float]] = OrderedDict()
    for mask in ONE_HOT:
        columns[f"I(B_COL_LOAD01) [{mask}]"] = sig(traces[mask], "I(B_COL_LOAD01)")
    columns["I(B_COL_LOAD01) [1111]"] = sig(traces["1111"], "I(B_COL_LOAD01)")
    columns["V(COMMON_SL) [1111]"] = sig(traces["1111"], "V(COMMON_SL)")
    add_comparison(records, "ONEHOT_COMMON_SL_POSITION", baseline.time, columns, "common-SL one-hot position / 1111")

    columns = OrderedDict()
    for mask in ONE_HOT:
        instance = active_instance(mask)
        columns[f"I(R_SL|XBVM{instance}) [{mask}]"] = sig(traces[mask], f"I(R_SL|XBVM{instance})")
        columns[f"I(L_SL|XBVM{instance}) [{mask}]"] = sig(traces[mask], f"I(L_SL|XBVM{instance})")
    add_comparison(records, "ONEHOT_ACTIVE_BVM_OUTPUT", baseline.time, columns, "one-hot active BVM output branches")

    for mask in ("1000", "0001"):
        active = active_instance(mask)
        columns = OrderedDict()
        for victim in range(1, 5):
            if victim == active:
                continue
            h = f"XBVM{victim}"
            columns[f"I(Delta_R_SL|{h}) [{mask}]"] = delta(traces[mask], baseline, f"I(R_SL|{h})")
            columns[f"I(Delta_L_SL|{h}) [{mask}]"] = delta(traces[mask], baseline, f"I(L_SL|{h})")
            columns[f"P(Delta_B_JS1|{h}) [{mask}]"] = phase_difference_rad(traces[mask], baseline, f"P(B_JS1|{h})")
            columns[f"P(Delta_B_JS2|{h}) [{mask}]"] = phase_difference_rad(traces[mask], baseline, f"P(B_JS2|{h})")
        add_comparison(records, f"INACTIVE_ISOLATION_{mask}", baseline.time, columns, f"inactive BVM isolation delta vs 0000 — active {mask}")

    for name, instance, masks in (("ACTIVE_CELL_FORWARD_LOADING", 1, ("1000", "1100", "1110", "1111")), ("ACTIVE_CELL_REVERSE_LOADING", 4, ("0001", "0011", "0111", "1111"))):
        columns = OrderedDict()
        for mask in masks:
            columns[f"I(R_SL|XBVM{instance}) [{mask}]"] = sig(traces[mask], f"I(R_SL|XBVM{instance})")
            columns[f"I(L_SL|XBVM{instance}) [{mask}]"] = sig(traces[mask], f"I(L_SL|XBVM{instance})")
            columns[f"I(B_COL_LOAD01) [{mask}]"] = sig(traces[mask], "I(B_COL_LOAD01)")
        add_comparison(records, name, baseline.time, columns, name.replace("_", " ").lower())

    def additivity_plot(name: str, masks: Sequence[str], title: str) -> None:
        columns = OrderedDict()
        onehot_deltas = {mask: delta(traces[mask], baseline, "I(B_COL_LOAD01)") for mask in ONE_HOT}
        for mask in masks:
            actual = delta(traces[mask], baseline, "I(B_COL_LOAD01)")
            active_onehots = [ONE_HOT_BY_INSTANCE[index] for index, bit in enumerate(mask, start=1) if bit == "1"]
            predicted = tuple(sum(onehot_deltas[onehot][i] for onehot in active_onehots) for i in range(len(actual)))
            residual = tuple(actual[i] - predicted[i] for i in range(len(actual)))
            columns[f"I(Delta_common) actual [{mask}]"] = actual
            columns[f"I(Delta_common) predicted [{mask}]"] = predicted
            columns[f"I(Delta_common) residual [{mask}]"] = residual
        add_comparison(records, name, baseline.time, columns, title)

    additivity_plot("ADDITIVITY_FORWARD", FORWARD, "common-SL additivity — forward cumulative masks")
    additivity_plot("ADDITIVITY_REVERSE", REVERSE, "common-SL additivity — reverse cumulative masks")

    columns = OrderedDict()
    onehot_deltas = {mask: delta(traces[mask], baseline, "I(B_COL_LOAD01)") for mask in ONE_HOT}
    for mask in ("1100", "1110", "1111", "0011", "0111"):
        active_onehots = [ONE_HOT_BY_INSTANCE[index] for index, bit in enumerate(mask, start=1) if bit == "1"]
        actual = delta(traces[mask], baseline, "I(B_COL_LOAD01)")
        predicted = tuple(sum(onehot_deltas[onehot][i] for onehot in active_onehots) for i in range(len(actual)))
        residual = tuple(actual[i] - predicted[i] for i in range(len(actual)))
        summed_mask = sum_lsl(traces[mask])
        summed_base = sum_lsl(baseline)
        summed_onehot = {onehot: sum_lsl(traces[onehot]) for onehot in ONE_HOT}
        summed_residual = tuple(
            (summed_mask[i] - summed_base[i])
            - sum(summed_onehot[onehot][i] - summed_base[i] for onehot in active_onehots)
            for i in range(len(actual))
        )
        columns[f"I(common residual) [{mask}]"] = residual
        columns[f"I(sum-output residual) [{mask}]"] = summed_residual
    add_comparison(records, "SUPERPOSITION_RESIDUAL", baseline.time, columns, "superposition residuals — direct common current and summed BVM output")

    old = {mask: read_csv(OLD_EXP / "runs" / mask / "raw.csv") for mask in MASKS}
    columns = OrderedDict()
    for mask in ONE_HOT:
        instance = active_instance(mask)
        columns[f"I(L_SL|XBVM{instance}) [old distributed {mask}]"] = sig(old[mask], f"I(L_SL|XBVM{instance})")
        columns[f"I(L_SL|XBVM{instance}) [new common-SL {mask}]"] = sig(traces[mask], f"I(L_SL|XBVM{instance})")
    add_comparison(records, "OLD_DISTRIBUTED_VS_COMMONSL_SUMMARY", old["0000"].time, columns, "old distributed endpoint vs new common-SL endpoint — one-hot context")


def main() -> int:
    traces = {mask: read_csv(EXP / "runs" / mask / "raw.csv") for mask in MASKS}
    records: list[dict[str, object]] = []
    for mask, specs in run_specs().items():
        for run_mask in MASKS:
            output = EXP / "plots/runs" / run_mask / f"{mask}.html"
            records.append(render(EXP / "runs" / run_mask / "raw.csv", output, f"{run_mask} — {mask}", specs))
    columns = OrderedDict()
    baseline = traces["0000"]
    for mask in ONE_HOT + ("1111",):
        columns[f"I(B_COL_LOAD01) [{mask}]"] = sig(traces[mask], "I(B_COL_LOAD01)")
    columns["I(SUM_BVM_OUTPUT) [1111]"] = sum_lsl(traces["1111"])
    columns["V(COMMON_SL) [1111]"] = sig(traces["1111"], "V(COMMON_SL)")
    add_comparison(records, "RESULT_OVERVIEW", baseline.time, columns, "historical JM2-connected BVM common-SL topology — overview")
    comparison_specs(traces, records)
    manifest = {
        "schema": "bvmsim-paperlike-common-sl-plot-manifest-v1",
        "renderer": rel(PLOTTER),
        "layout": "sep_comb",
        "color": "dark",
        "phase_option": "2pi",
        "standalone_first": True,
        "record_count": len(records),
        "records": records,
        "qa": {"all_html": all(item["qa"]["html"] for item in records), "all_unknown_axis_absent": all(item["qa"]["unknown_axis_absent"] for item in records)},
    }
    (EXP / "analysis/plot_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "record_count": len(records), "standalone_pages": 70, "comparison_pages": 10, "manifest": rel(EXP / "analysis/plot_manifest.json")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
