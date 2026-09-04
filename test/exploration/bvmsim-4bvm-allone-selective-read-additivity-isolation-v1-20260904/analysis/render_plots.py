#!/usr/bin/env python3
"""Render focused classic plots for the ten array runs and comparisons."""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Callable, Sequence


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
PLOTTER = REPO / "scripts/josim-plot2.py"
MASKS = ("0000", "0001", "0010", "0100", "1000", "0011", "0111", "1100", "1110", "1111")
ONE_HOT = ("0001", "0010", "0100", "1000")
ONE_HOT_BY_INSTANCE = {1: "1000", 2: "0100", 3: "0010", 4: "0001"}
FORWARD = ("1100", "1110", "1111")
REVERSE = ("0011", "0111", "1111")
READ = (110.0e-12, 170.0e-12)

sys.path.insert(0, str(REPO / "scripts"))
from bvmtools.kcl import linear_kcl_residual  # noqa: E402
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


def labels_for_bvm(instance: int, kind: str, names: Sequence[str]) -> list[str]:
    return [f"{kind}({name}|XBVM{instance})" for name in names]


def standalone_specs() -> OrderedDict[str, list[str]]:
    controls = [f"I(I_{control}{instance})" for instance in range(1, 5) for control in ("WL", "BL", "SE")]
    state: list[str] = []
    for instance in range(1, 5):
        for junction in ("JM1", "JM2", "JS1", "JS2"):
            state.extend(labels_for_bvm(instance, "P", (f"B_{junction}",)))
            state.extend(labels_for_bvm(instance, "V", (f"B_{junction}",)))
            state.extend(labels_for_bvm(instance, "I", (f"B_{junction}",)))
        state.extend(labels_for_bvm(instance, "I", ("L_M1", "L_M2", "L_M3", "L_PM", "L_PSL", "L_SL")))
        state.append(f"V(SL{instance})")
    current = []
    for instance in range(1, 5):
        current.extend(labels_for_bvm(instance, "I", ("L_M3", "R_S", "L_S3", "R_SL", "L_SL", "B_JS1", "B_JS2")))
    voltage = []
    for instance in range(1, 5):
        voltage.extend(labels_for_bvm(instance, "V", ("B_JS1", "B_JS2", "R_S", "L_S3", "R_SL", "L_SL")))
    boundary = [
        "P(B_LD01)", "V(B_LD01)", "I(B_LD01)", "P(B_LD12)", "V(B_LD12)", "I(B_LD12)",
        "P(B_LD2_01)", "V(B_LD2_01)", "I(B_LD2_01)", "P(B_LD2_12)", "V(B_LD2_12)", "I(B_LD2_12)",
        "P(B_LD3_01)", "V(B_LD3_01)", "I(B_LD3_01)", "P(B_LD3_12)", "V(B_LD3_12)", "I(B_LD3_12)",
        "P(B_LD4_01)", "V(B_LD4_01)", "I(B_LD4_01)", "P(B_LD4_11)", "V(B_LD4_11)", "I(B_LD4_11)",
        "P(BVMOUT)", "V(BVMOUT)", "I(BVMOUT)",
        *(f"V(SL{instance})" for instance in range(1, 5)),
        *(f"I(L_SL|XBVM{instance})" for instance in range(1, 5)),
        "V(QBIN)", "V(QBOUT)", "I(LIN|XBQ1)",
    ]
    qb = [
        "V(QBIN)", "V(QBOUT)", "I(LIN|XBQ1)",
        "P(BJS|XBQ1)", "V(BJS|XBQ1)", "I(BJS|XBQ1)",
        "P(BJ1|XBQ1)", "V(BJ1|XBQ1)", "I(BJ1|XBQ1)", "I(RJ1|XBQ1)",
        "I(L1|XBQ1)", "I(IB|XBQ1)", "I(L2|XBQ1)",
        "P(BJ2|XBQ1)", "V(BJ2|XBQ1)", "I(BJ2|XBQ1)", "I(RJ2|XBQ1)", "I(L3|XBQ1)",
    ]
    jtl = [
        item
        for stage in range(1, 7)
        for junction in ("B01", "B02")
        for item in (f"P({junction}|XJTL1_{stage})", f"V({junction}|XJTL1_{stage})")
    ]
    return OrderedDict(
        (
            ("CONTROL_TIMING", controls),
            ("BVM_STATE", state),
            ("BVM_RLOOP_CURRENT", current),
            ("BVM_RLOOP_VOLTAGE", voltage),
            ("BVMOUT_QB_INPUT", boundary),
            ("QB_INTERNAL", qb),
            ("JTL_TRANSPORT", jtl),
        )
    )


def write_csv(path: Path, time: Sequence[float], columns: OrderedDict[str, Sequence[float]]) -> None:
    if not columns:
        raise RuntimeError(f"no columns for {path}")
    lengths = {len(time), *(len(values) for values in columns.values())}
    if len(lengths) != 1:
        raise RuntimeError(f"derived CSV length mismatch: {path}: {lengths}")
    if len(set(columns)) != len(columns):
        raise RuntimeError(f"duplicate derived labels: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["time", *columns.keys()])
        for index, timestamp in enumerate(time):
            writer.writerow([f"{timestamp:.17g}", *(f"{values[index]:.17g}" for values in columns.values())])


def add_delta(trace: RawTrace, baseline: RawTrace, label: str) -> tuple[float, ...]:
    if trace.time != baseline.time:
        raise RuntimeError(f"raw time grid mismatch for {label}")
    return tuple(a - b for a, b in zip(sig(trace, label), sig(baseline, label)))


def read_window_indices(trace: RawTrace) -> tuple[int, ...]:
    return window_indices(trace.time, *READ)


def window_relative(trace: RawTrace, values: Sequence[float]) -> tuple[tuple[float, ...], tuple[float, ...]]:
    indices = read_window_indices(trace)
    first = indices[0]
    return (
        tuple(trace.time[index] - trace.time[first] for index in indices),
        tuple(float(values[index]) for index in indices),
    )


def render(input_path: Path, output_path: Path, title: str, labels: list[str]) -> dict[str, object]:
    trace = read_csv(input_path)
    if trace.duplicate_columns:
        raise RuntimeError(f"duplicate columns in plot input {input_path}: {trace.duplicate_columns}")
    missing = [label for label in labels if label not in trace.headers]
    if missing:
        raise RuntimeError(f"missing plot labels in {input_path}: {missing}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable, str(PLOTTER), str(input_path), "-x", str(output_path),
        "-t", "sep_comb", "-c", "dark", "-j", "2pi", "-w", title, "-s", *labels,
    ]
    completed = subprocess.run(command, cwd=REPO, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"plot failed: {output_path}\nstdout={completed.stdout}\nstderr={completed.stderr}")
    html = output_path.read_text(encoding="utf-8", errors="replace")
    if "<html" not in html.lower():
        raise RuntimeError(f"not html: {output_path}")
    if '"title":{"text":"Unknown"}' in html:
        raise RuntimeError(f"Unknown axis in plot: {output_path}")
    has_phase = any(label.startswith("P(") for label in labels)
    if has_phase and "Phase (turns)" not in html:
        raise RuntimeError(f"phase conversion QA failed: {output_path}")
    return {
        "path": rel(output_path),
        "input": rel(input_path),
        "input_sha256": digest(input_path),
        "output_sha256": digest(output_path),
        "title": title,
        "labels": labels,
        "command": command,
        "exit_code": completed.returncode,
        "qa": {"html": True, "unknown_axis_absent": True, "phase_display": "rad/(2*pi) turns" if has_phase else "not applicable", "classic_renderer": True},
    }


def add_comparison(records: list[dict[str, object]], name: str, columns: OrderedDict[str, Sequence[float]], time: Sequence[float], title: str) -> None:
    path = EXP / "plots/comparison/data" / f"{name}.csv"
    write_csv(path, time, columns)
    records.append(render(path, EXP / "plots/comparison" / f"{name}.html", title, list(columns)))


def comparison_plots(traces: Mapping[str, RawTrace], records: list[dict[str, object]]) -> None:
    baseline = traces["0000"]
    # Position dependence is shown only for the key shared input and active
    # RSL/SL source branches.
    columns: OrderedDict[str, Sequence[float]] = OrderedDict()
    for mask in ONE_HOT:
        active = next(index for index, bit in enumerate(mask, start=1) if bit == "1")
        columns[f"V(QBIN) [{mask}]"] = sig(traces[mask], "V(QBIN)")
        columns[f"I(LIN|XBQ1) [{mask}]"] = sig(traces[mask], "I(LIN|XBQ1)")
        columns[f"I(R_SL|XBVM{active}) [{mask}]"] = sig(traces[mask], f"I(R_SL|XBVM{active})")
    add_comparison(records, "ONEHOT_QBIN_POSITION", columns, baseline.time, "one-hot position — QBIN / LIN / active RSL")

    columns = OrderedDict()
    for mask in ONE_HOT:
        active = next(index for index, bit in enumerate(mask, start=1) if bit == "1")
        columns[f"I(R_SL|XBVM{active}) [{mask}]"] = sig(traces[mask], f"I(R_SL|XBVM{active})")
        columns[f"I(Delta_RSL|XBVM{active}) [{mask}]"] = add_delta(traces[mask], baseline, f"I(R_SL|XBVM{active})")
        columns[f"I(L_SL|XBVM{active}) [{mask}]"] = sig(traces[mask], f"I(L_SL|XBVM{active})")
    add_comparison(records, "ONEHOT_RSL_POSITION", columns, baseline.time, "one-hot position — RSL/LSL response")

    single = read_csv(REPO / "test/exploration/bvmsim-jm2-connected-single-rloop-observability-v1-20260904/runs/S1-J-RLOOP/raw.csv")
    # The comparison page uses relative READ time.  All array runs share the
    # same grid; the single reference is paired by equal sample index, with no
    # interpolation.  Absolute offsets make exact float equality inappropriate.
    arr_indices = read_window_indices(baseline)
    rel_time = tuple(baseline.time[index] - baseline.time[arr_indices[0]] for index in arr_indices)
    single_indices = window_indices(single.time, 70e-12, 130e-12)
    single_rel = tuple(single.time[index] - single.time[single_indices[0]] for index in single_indices)
    if len(rel_time) != len(single_rel):
        raise RuntimeError("active-vs-single sample-count mismatch; no interpolation permitted")
    columns = OrderedDict()
    for mask in ONE_HOT:
        active = next(index for index, bit in enumerate(mask, start=1) if bit == "1")
        array = traces[mask]
        for label, phase in (
            (f"I(LIN|XBQ1)", False),
            (f"V(QBIN)", False),
            (f"I(R_SL|XBVM{active})", False),
            (f"I(L_SL|XBVM{active})", False),
            (f"P(B_JS2|XBVM{active})", True),
        ):
            array_values = sig(array, label) if not phase else tuple(value / (2.0 * 3.141592653589793) for value in continuous_unwrap(sig(array, label)))
            if "|XBVM" in label:
                single_label = label.replace(f"|XBVM{active}", "|XBVM1")
            else:
                single_label = label
            single_values = sig(single, single_label) if not phase else tuple(value / (2.0 * 3.141592653589793) for value in continuous_unwrap(sig(single, single_label)))
            ai = read_window_indices(array)
            si = single_indices
            if phase:
                array_values = tuple(array_values[index] - array_values[ai[0]] for index in ai)
                single_values = tuple(single_values[index] - single_values[si[0]] for index in si)
            else:
                array_values = tuple(array_values[index] for index in ai)
                single_values = tuple(single_values[index] for index in si)
            columns[f"{label} [array {mask}]"] = array_values
            columns[f"{single_label} [isolated S1 {mask}]"] = single_values
    add_comparison(records, "ACTIVE_VS_SINGLE_REFERENCE", columns, rel_time, "active BVM vs isolated single S1 — relative READ")

    for mask in ("1000", "0001"):
        active = next(index for index, bit in enumerate(mask, start=1) if bit == "1")
        columns = OrderedDict()
        for victim in range(1, 5):
            if victim == active:
                continue
            for branch in ("R_SL", "L_SL", "R_S", "L_S3", "L_M3"):
                label = f"I({branch}|XBVM{victim})"
                columns[f"I(Delta_{branch}|XBVM{victim}) [{mask}]"] = add_delta(traces[mask], baseline, label)
            for junction in ("B_JS1", "B_JS2"):
                label = f"P({junction}|XBVM{victim})"
                phase_one = tuple(value / (2.0 * 3.141592653589793) for value in continuous_unwrap(sig(traces[mask], label)))
                phase_base = tuple(value / (2.0 * 3.141592653589793) for value in continuous_unwrap(sig(baseline, label)))
                columns[f"P(Delta_{junction}|XBVM{victim}) [{mask}]"] = tuple(a - b for a, b in zip(phase_one, phase_base))
        add_comparison(records, f"INACTIVE_CELL_ISOLATION_{mask}", columns, baseline.time, f"inactive BVM vs 0000 — active {mask}")

    labels = ["I(LIN|XBQ1)", "V(QBIN)", *(f"I(L_SL|XBVM{n})" for n in range(1, 5))]
    delta_one = {mask: {label: add_delta(traces[mask], baseline, label) for label in labels} for mask in ONE_HOT}
    for name, masks in (("ADDITIVITY_FORWARD", FORWARD), ("ADDITIVITY_REVERSE", REVERSE)):
        columns = OrderedDict()
        for mask in masks:
            active_onehots = [ONE_HOT_BY_INSTANCE[index] for index, bit in enumerate(mask, start=1) if bit == "1"]
            for label in ("I(LIN|XBQ1)", "V(QBIN)"):
                actual = add_delta(traces[mask], baseline, label)
                predicted = tuple(sum(delta_one[onehot][label][i] for onehot in active_onehots) for i in range(len(actual)))
                residual = tuple(a - p for a, p in zip(actual, predicted))
                prefix = "I(Delta_LIN)" if label.startswith("I(") else "V(Delta_QBIN)"
                columns[f"{prefix} actual [{mask}]"] = actual
                columns[f"{prefix} predicted [{mask}]"] = predicted
                columns[f"{prefix} residual [{mask}]"] = residual
        add_comparison(records, name, columns, baseline.time, f"{name.lower()} — actual vs one-hot prediction")

    columns = OrderedDict()
    for mask in tuple(dict.fromkeys(FORWARD + REVERSE)):
        active_onehots = [ONE_HOT_BY_INSTANCE[index] for index, bit in enumerate(mask, start=1) if bit == "1"]
        for label, prefix in (("I(LIN|XBQ1)", "I(Superposition_residual_LIN)"), ("V(QBIN)", "V(Superposition_residual_QBIN)"), *( (f"I(L_SL|XBVM{n})", f"I(Superposition_residual_LSL{n})") for n in range(1, 5))):
            actual = add_delta(traces[mask], baseline, label)
            predicted = tuple(sum(delta_one[onehot][label][i] for onehot in active_onehots) for i in range(len(actual)))
            columns[f"{prefix} [{mask}]"] = tuple(a - p for a, p in zip(actual, predicted))
    add_comparison(records, "SUPERPOSITION_RESIDUAL", columns, baseline.time, "one-hot superposition residuals")


def kcl_derived(trace: RawTrace) -> tuple[OrderedDict[str, Sequence[float]], Sequence[float]]:
    equations = OrderedDict(
        (
            ("JM1_shunt", (("B_JM1", 1.0), ("R_JM1", 1.0), ("L_M1", -1.0))),
            ("SE_RLOOP", (("B_JS1", 1.0), ("L_PSE", 1.0), ("R_S", -1.0), ("L_S3", -1.0))),
            ("RLOOP_OUTPUT", (("R_S", 1.0), ("L_S3", 1.0), ("B_JS2", 1.0), ("L_PSL", -1.0))),
            ("SL_SERIES_1", (("L_PSL", 1.0), ("R_SL", -1.0))),
            ("SL_SERIES_2", (("R_SL", 1.0), ("L_SL", -1.0))),
        )
    )
    columns: OrderedDict[str, Sequence[float]] = OrderedDict()
    for instance in range(1, 5):
        for name, terms in equations.items():
            branch_values = {
                f"{branch}|XBVM{instance}": sig(trace, f"I({branch}|XBVM{instance})")
                for branch, _ in terms
            }
            coefficients = {f"{branch}|XBVM{instance}": sign for branch, sign in terms}
            residual = linear_kcl_residual(branch_values, coefficients)
            columns[f"I(KCL_{name}|XBVM{instance})"] = residual
    return columns, trace.time


def main() -> int:
    traces = OrderedDict((mask, read_csv(EXP / "runs" / mask / "raw.csv")) for mask in MASKS)
    raw_before = {mask: digest(EXP / "runs" / mask / "raw.csv") for mask in MASKS}
    records: list[dict[str, object]] = []
    specs = standalone_specs()
    for mask, trace in traces.items():
        for name, labels in specs.items():
            records.append(render(EXP / "runs" / mask / "raw.csv", EXP / "plots/runs" / mask / f"{name}.html", f"{mask} — {name}", labels))
        kcl_columns, kcl_time = kcl_derived(trace)
        kcl_path = EXP / "plots/runs" / mask / "derived" / "BVM_RLOOP_KCL.csv"
        write_csv(kcl_path, kcl_time, kcl_columns)
        records.append(render(kcl_path, kcl_path.with_suffix(".html"), f"{mask} — BVM R-loop KCL residuals", list(kcl_columns)))
    comparison_plots(traces, records)
    raw_after = {mask: digest(EXP / "runs" / mask / "raw.csv") for mask in MASKS}
    if raw_before != raw_after:
        raise RuntimeError("raw hash changed during rendering")
    manifest = {
        "schema": "bvmsim-4bvm-allone-selective-read-plot-manifest-v1",
        "renderer": rel(PLOTTER),
        "renderer_sha256": digest(PLOTTER),
        "plot_driver": rel(Path(__file__)),
        "plot_driver_sha256": digest(Path(__file__)),
        "layout": "sep_comb",
        "color": "dark",
        "phase_jump": "2pi",
        "standalone_before_comparison": True,
        "raw_hash_before": raw_before,
        "raw_hash_after": raw_after,
        "raw_unchanged": raw_before == raw_after,
        "plot_count": len(records),
        "plots": records,
    }
    (EXP / "analysis/plot_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    links = "\n".join(f'<li><a href="{Path(str(item["path"])).relative_to((EXP / "plots").relative_to(REPO)).as_posix()}">{item["title"]}</a></li>' for item in records)
    overview = "<!doctype html>\n<html><head><meta charset=\"utf-8\"><title>ALL-ONE SELECTIVE-READ overview</title></head><body>\n<h1>ALL-ONE SELECTIVE-READ / ADDITIVITY / ISOLATION</h1>\n<p>主问题：active-vs-isolated、inactive-vs-0000、multi-active-vs-one-hot superposition。QB/JTL 是次级诊断。所有 P(...) 由 raw rad 按 continuous_unwrap(rad)/(2*pi) 显示为 turns；图仅作描述，不是 SFQ count authority。</p>\n<p><a href=\"../analysis/REPORT.md\">分析报告</a> · <a href=\"../analysis/metrics.json\">metrics.json</a> · <a href=\"../analysis/independent_check.json\">independent_check.json</a> · <a href=\"../analysis/plot_manifest.json\">plot_manifest.json</a></p>\n<ul>\n" + links + "\n</ul>\n</body></html>\n"
    (EXP / "plots/RESULT_OVERVIEW.html").write_text(overview, encoding="utf-8")
    print(json.dumps({"status": "PASS", "plot_count": len(records), "raw_unchanged": raw_before == raw_after}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
