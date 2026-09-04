#!/usr/bin/env python3
"""Render compact standalone and comparison pages from immutable raw CSVs.

The renderer is deliberately a consumer of raw CSVs only.  All pages use the
repository visual authority ``scripts/josim-plot2.py`` with
``sep_comb + dark + 2pi``.  Derived comparison CSVs retain phase in raw
radians so the renderer performs the single, visible rad/(2*pi) conversion.
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
PLOTTER = REPO / "scripts/josim-plot2.py"
MASKS = ("0000", "0001", "0010", "0100", "1000", "0011", "0111", "1100", "1110", "1111")
ONE_HOT = ("0001", "0010", "0100", "1000")
REPRESENTATIVE = ("0000", "0001", "0011", "0111", "1111")
MULTI_ACTIVE = ("0011", "0111", "1100", "1110", "1111")

sys.path.insert(0, str(REPO / "scripts"))
from bvmtools.phase import continuous_unwrap  # noqa: E402
from bvmtools.raw import RawTrace, read_csv  # noqa: E402


def sig(trace: RawTrace, label: str) -> tuple[float, ...]:
    return trace.column(label)  # type: ignore[return-value]


def sum_lsl(trace: RawTrace) -> tuple[float, ...]:
    rows = [sig(trace, f"I(L_SL|XBVM{instance})") for instance in range(1, 5)]
    return tuple(sum(row[index] for row in rows) for index in range(len(trace.time)))


def phase_raw(trace: RawTrace, label: str) -> tuple[float, ...]:
    return continuous_unwrap(sig(trace, label))


def standalone_specs() -> dict[str, list[str]]:
    controls = [f"I(I_{control}{instance})" for instance in range(1, 5) for control in ("WL", "BL", "SE")]
    internal = [f"P({jj}|XBVM{instance})" for instance in range(1, 5) for jj in ("B_JM1", "B_JM2", "B_JS1", "B_JS2")]
    rloop = [
        f"{quantity}({branch}|XBVM{instance})"
        for instance in range(1, 5)
        for quantity in ("I", "V")
        for branch in ("R_S", "L_S3")
    ]
    output = [
        f"{quantity}({branch}|XBVM{instance})"
        for instance in range(1, 5)
        for quantity in ("I", "V")
        for branch in ("L_PSL", "R_SL", "L_SL")
    ]
    common = [
        "V(COMMON_SL)",
        "I(B_JSL01)", "I(B_JSL06)", "I(B_JSL12)",
        "P(B_JSL01)", "P(B_JSL12)",
        "V(B_JSL01)", "V(B_JSL12)",
    ]
    stack = [
        f"I(B_JSL{index:02d})" for index in (1, 2, 3, 6, 9, 12)
    ] + [
        f"{quantity}(B_JSL{index:02d})" for index in (1, 6, 12) for quantity in ("P", "V")
    ]
    qbin = ["I(B_JSL12)", "I(LIN|XBQ1)", "V(QBIN)", "V(QBOUT)", "I(R_TERM)"]
    qb_internal = [
        f"{quantity}({junction}|XBQ1)"
        for junction in ("BJS", "BJ1", "BJ2")
        for quantity in ("P", "V", "I")
    ] + [f"I({branch}|XBQ1)" for branch in ("L1", "L2", "L3", "RJ1", "RJ2", "IB")]
    jtl = [
        f"{quantity}({junction}|XJTL1_{stage})"
        for stage in range(1, 7)
        for junction in ("B01", "B02")
        for quantity in ("P", "V")
    ]
    return {
        "BVM_STIMULUS_STATE": controls,
        "BVM_INTERNAL": internal,
        "BVM_RLOOP": rloop,
        "BVM_OUTPUT": output,
        "COMMON_SL_JSL": common,
        "JSL_STACK": stack,
        "QBIN_INPUT": qbin,
        "QB_INTERNAL": qb_internal,
        "JTL_TRANSPORT": jtl,
    }


def plot_html(input_path: Path, output_path: Path, labels: list[str], title: str) -> None:
    if output_path.exists():
        raise RuntimeError(f"refusing to overwrite plot: {output_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable,
        str(PLOTTER),
        str(input_path),
        "-x", str(output_path),
        "-t", "sep_comb",
        "-c", "dark",
        "-j", "2pi",
        "-w", title,
        "-s",
        *labels,
    ]
    completed = subprocess.run(command, capture_output=True, text=True)
    if completed.returncode != 0:
        raise RuntimeError(
            f"plot failed for {output_path}: exit={completed.returncode}\n"
            f"stdout={completed.stdout[-2000:]}\nstderr={completed.stderr[-2000:]}"
        )
    if not output_path.is_file() or output_path.stat().st_size == 0:
        raise RuntimeError(f"plotter did not create nonempty output: {output_path}")


def derived_csv(name: str, time: tuple[float, ...], columns: list[tuple[str, tuple[float, ...]]]) -> Path:
    data_dir = EXP / "plots" / "comparison" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    path = data_dir / f"{name}.csv"
    if path.exists():
        raise RuntimeError(f"refusing to overwrite derived comparison data: {path}")
    if any(len(values) != len(time) for _, values in columns):
        raise RuntimeError(f"derived data length mismatch: {name}")
    labels = [label for label, _ in columns]
    if len(labels) != len(set(labels)):
        raise RuntimeError(f"duplicate derived labels: {name}")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["time", *labels])
        for index, current_time in enumerate(time):
            writer.writerow([f"{current_time:.17e}", *(f"{values[index]:.17e}" for _, values in columns)])
    return path


def derived_plot(name: str, time: tuple[float, ...], columns: list[tuple[str, tuple[float, ...]]], title: str) -> dict[str, object]:
    csv_path = derived_csv(name, time, columns)
    # Keep the primary human-facing page at the conventional experiment root;
    # the remaining comparison pages stay grouped under comparison/.
    output = EXP / "plots" / (f"{name}.html" if name == "RESULT_OVERVIEW" else f"comparison/{name}.html")
    plot_html(csv_path, output, [label for label, _ in columns], title)
    return {"name": name, "data": str(csv_path.relative_to(EXP)), "html": str(output.relative_to(EXP)), "labels": [label for label, _ in columns]}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    if not args.write:
        raise SystemExit("use --write to create immutable plot artifacts")

    traces = {mask: read_csv(EXP / "runs" / mask / "raw.csv") for mask in MASKS}
    passive = {mask: read_csv(REPO / "test/exploration/bvmsim-4bvm-paperlike-common-sl-accumulation-isolation-v1-20260904/runs" / mask / "raw.csv") for mask in MASKS}
    time = traces["0000"].time
    if any(trace.time != time for trace in traces.values()) or any(trace.time != time for trace in passive.values()):
        raise RuntimeError("plot comparison requires exact stored time-grid identity")

    manifest: dict[str, object] = {
        "schema": "bvmsim-common-sl-12jsl-qb-plot-manifest-v1",
        "created_at_local": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "renderer": str(PLOTTER.relative_to(REPO)),
        "renderer_options": {"layout": "sep_comb", "color": "dark", "phase": "2pi", "phase_label": "Phase (turns) [rad/2pi]"},
        "raw_policy": "raw.csv files are immutable; derived comparison CSVs are immutable generated inputs",
        "standalone": {},
        "comparison": {},
    }

    specs = standalone_specs()
    for mask in MASKS:
        raw = EXP / "runs" / mask / "raw.csv"
        for name, labels in specs.items():
            # Validate the selected schema against the exact raw header before
            # invoking pandas through the repository plotter.
            missing = sorted(set(labels) - set(traces[mask].headers))
            if missing:
                raise RuntimeError(f"{mask}/{name}: missing raw labels {missing}")
            output = EXP / "plots" / "runs" / mask / f"{name}.html"
            plot_html(raw, output, labels, f"COMMON-SL -> QB integration | {mask} | {name}")
            manifest["standalone"].setdefault(mask, {})[name] = {  # type: ignore[union-attr]
                "html": str(output.relative_to(EXP)),
                "input": str(raw.relative_to(EXP)),
                "labels": labels,
            }

    def I(label: str, mask: str, source: dict[str, RawTrace] = traces) -> tuple[float, ...]:
        return sig(source[mask], label)

    def V(label: str, mask: str, source: dict[str, RawTrace] = traces) -> tuple[float, ...]:
        return sig(source[mask], label)

    def P(label: str, mask: str, source: dict[str, RawTrace] = traces) -> tuple[float, ...]:
        return phase_raw(source[mask], label)

    comparison: list[dict[str, object]] = []
    comparison.append(derived_plot(
        "ONEHOT_SUM_LSL",
        time,
        [(f"I(SUM_LSL|{mask})", sum_lsl(traces[mask])) for mask in ONE_HOT],
        "One-hot common-SL source current | receiver-loaded",
    ))
    comparison.append(derived_plot(
        "ONEHOT_JSL_CURRENT",
        time,
        [(f"I(B_JSL01|{mask})", I("I(B_JSL01)", mask)) for mask in ONE_HOT]
        + [(f"I(B_JSL12|{mask})", I("I(B_JSL12)", mask)) for mask in ONE_HOT],
        "One-hot JSL01/JSL12 current transfer",
    ))
    comparison.append(derived_plot(
        "ONEHOT_QB_INPUT",
        time,
        [(f"I(LIN|{mask})", I("I(LIN|XBQ1)", mask)) for mask in ONE_HOT]
        + [(f"V(QBIN|{mask})", V("V(QBIN)", mask)) for mask in ONE_HOT],
        "One-hot QB input: LIN and QBIN",
    ))
    comparison.append(derived_plot(
        "POPULATION_SUM_LSL",
        time,
        [(f"I(SUM_LSL|{mask})", sum_lsl(traces[mask])) for mask in MASKS],
        "Population response: common-SL source current",
    ))
    comparison.append(derived_plot(
        "POPULATION_JSL_CURRENT",
        time,
        [(f"I(B_JSL01|{mask})", I("I(B_JSL01)", mask)) for mask in MASKS]
        + [(f"I(B_JSL12|{mask})", I("I(B_JSL12)", mask)) for mask in MASKS],
        "Population response: JSL01/JSL12 current",
    ))
    comparison.append(derived_plot(
        "POPULATION_LIN",
        time,
        [(f"I(LIN|{mask})", I("I(LIN|XBQ1)", mask)) for mask in MASKS],
        "Population response: QB LIN current",
    ))
    comparison.append(derived_plot(
        "QB_BJ2_0_TO_4",
        time,
        [(f"P(BJ2|{mask})", P("P(BJ2|XBQ1)", mask)) for mask in REPRESENTATIVE]
        + [(f"V(BJ2|{mask})", V("V(BJ2|XBQ1)", mask)) for mask in REPRESENTATIVE],
        "QB BJ2 trajectory: representative population 0 to 4",
    ))
    comparison.append(derived_plot(
        "BJ2_CROSSING_TIMELINE",
        time,
        [(f"P(BJ2_unwrapped|{mask})", P("P(BJ2|XBQ1)", mask)) for mask in REPRESENTATIVE],
        "BJ2 continuous phase trajectory (turns after rad/2pi conversion)",
    ))
    comparison.append(derived_plot(
        "JTL6_0_TO_4",
        time,
        [(f"P(JTL6_B02|{mask})", P("P(B02|XJTL1_6)", mask)) for mask in REPRESENTATIVE]
        + [(f"V(JTL6_B02|{mask})", V("V(B02|XJTL1_6)", mask)) for mask in REPRESENTATIVE],
        "JTL6 B02 trajectory: representative population 0 to 4",
    ))
    comparison.append(derived_plot(
        "PASSIVE_VS_QB_SUM_LSL",
        time,
        [(f"I(SUM_LSL|QB|{mask})", sum_lsl(traces[mask])) for mask in REPRESENTATIVE]
        + [(f"I(SUM_LSL|passive|{mask})", sum_lsl(passive[mask])) for mask in REPRESENTATIVE],
        "Passive GND boundary vs receiver-loaded common-SL current",
    ))
    comparison.append(derived_plot(
        "PASSIVE_VS_QB_JSL",
        time,
        [(f"I(B_JSL01|QB|{mask})", I("I(B_JSL01)", mask)) for mask in REPRESENTATIVE]
        + [(f"I(B_COL_LOAD01|passive|{mask})", I("I(B_COL_LOAD01)", mask, passive)) for mask in REPRESENTATIVE],
        "Passive terminal load vs receiver-loaded JSL01 current",
    ))
    comparison.append(derived_plot(
        "QB_LOAD_BACKACTION_ONEHOT",
        time,
        [(f"V(COMMON_SL|QB|{mask})", V("V(COMMON_SL)", mask)) for mask in ONE_HOT]
        + [(f"V(COMMON_SL|passive|{mask})", V("V(COMMON_SL)", mask, passive)) for mask in ONE_HOT],
        "QB boundary back-action on one-hot common-SL node",
    ))
    comparison.append(derived_plot(
        "QB_LOAD_BACKACTION_1111",
        time,
        [
            ("I(SUM_LSL|QB|1111)", sum_lsl(traces["1111"])),
            ("I(SUM_LSL|passive|1111)", sum_lsl(passive["1111"])),
            ("I(B_JSL01|QB|1111)", I("I(B_JSL01)", "1111")),
            ("I(B_COL_LOAD01|passive|1111)", I("I(B_COL_LOAD01)", "1111", passive)),
            ("V(COMMON_SL|QB|1111)", V("V(COMMON_SL)", "1111")),
            ("V(COMMON_SL|passive|1111)", V("V(COMMON_SL)", "1111", passive)),
        ],
        "QB boundary back-action on all-four common-SL source",
    ))

    onehot_delta = {mask: tuple(a - b for a, b in zip(sum_lsl(traces[mask]), sum_lsl(traces["0000"]))) for mask in ONE_HOT}
    add_cols: list[tuple[str, tuple[float, ...]]] = []
    for mask in MULTI_ACTIVE:
        active = [ONE_HOT[index] for index in range(4) if mask[index] == "1"]
        actual = tuple(a - b for a, b in zip(sum_lsl(traces[mask]), sum_lsl(traces["0000"])))
        predicted = tuple(sum(onehot_delta[onehot][i] for onehot in active) for i in range(len(actual)))
        add_cols.extend([(f"I(Actual_delta|{mask})", actual), (f"I(OneHot_sum|{mask})", predicted)])
    comparison.append(derived_plot(
        "ADDITIVITY_UNDER_QB_LOAD",
        time,
        add_cols,
        "Actual vs one-hot superposition under QB loading",
    ))
    overview_cols: list[tuple[str, tuple[float, ...]]] = []
    for mask in REPRESENTATIVE:
        overview_cols.extend(
            [
                (f"I(SUM_LSL|{mask})", sum_lsl(traces[mask])),
                (f"I(LIN|{mask})", I("I(LIN|XBQ1)", mask)),
                (f"V(QBIN|{mask})", V("V(QBIN)", mask)),
                (f"P(BJ2|{mask})", P("P(BJ2|XBQ1)", mask)),
                (f"P(JTL6_B02|{mask})", P("P(B02|XJTL1_6)", mask)),
            ]
        )
    comparison.append(derived_plot("RESULT_OVERVIEW", time, overview_cols, "COMMON-SL -> 12-JSL -> frozen QB -> six-stage JTL | overview"))
    manifest["comparison"] = {item["name"]: item for item in comparison}

    output = EXP / "plots" / "plot_manifest.json"
    if output.exists():
        raise RuntimeError(f"refusing to overwrite plot manifest: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "standalone_pages": len(MASKS) * len(specs), "comparison_pages": len(comparison), "manifest": str(output.relative_to(EXP))}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
