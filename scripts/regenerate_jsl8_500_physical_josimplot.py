#!/usr/bin/env python3
"""Render the JSL8 physical recheck with the repository josim-plot2 pipeline.

Only existing raw CSVs are read.  Comparison CSVs are temporary plotting
inputs and are never stored as evidence.  Every HTML page gets a metadata
sidecar naming its raw sources and its phase semantics.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Iterable

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PLOTTER = ROOT / "scripts/josim-plot2.py"
EXP = "test/exploration/bvm-jsl8-500-physical-qb-recheck-v1-20260824"
REFERENCE_EXP = "test/exploration/physical-bvm-jsl12-qb-sfq-closure-v1-20260824"
EXP_ROOT = ROOT / EXP
ROLES = ("logical1_read", "logical0_read", "logical1_no_read_control", "logical0_no_read_control")
ROLE_LABELS = {
    "logical1_read": "logical1 READ",
    "logical0_read": "logical0 READ",
    "logical1_no_read_control": "logical1 READ=0",
    "logical0_no_read_control": "logical0 READ=0",
}

CASE_COLUMNS = (
    "I(I_WL1)", "I(I_SE1)",
    "P(B_JM1|XBVM1)", "V(B_JM1|XBVM1)", "P(B_JM2|XBVM1)", "V(B_JM2|XBVM1)",
    "P(B_JS1|XBVM1)", "V(B_JS1|XBVM1)", "P(B_JS2|XBVM1)", "V(B_JS2|XBVM1)",
    "V(N6|XBVM1)", "V(SL1)", "I(L_PSL|XBVM1)", "I(L_SL|XBVM1)",
    *[item for index in range(1, 9) for item in (f"P(B_LD{index})", f"V(B_LD{index})", f"I(B_LD{index})")],
    "P(BJS|XBQ)", "V(BJS|XBQ)", "I(BJS|XBQ)",
    "P(BJL1|XBQ)", "V(BJL1|XBQ)", "I(BJL1|XBQ)",
    "P(BJL2|XBQ)", "V(BJL2|XBQ)", "I(BJL2|XBQ)",
    "V(IN)", "V(OUT)", "I(LIN|XBQ)", "I(L0|XBQ)", "I(L1|XBQ)", "I(L2|XBQ)",
    "I(RB|XBQ)", "I(RJ1|XBQ)", "I(RJ2|XBQ)", "I(R_LOAD)", "I(I_IBIAS)",
)


def new_path(role: str) -> str:
    return f"{EXP}/raw/13/{role}/run-01.csv"


def reference_path(role: str) -> str:
    return f"{REFERENCE_EXP}/raw/13/{role}/run-01.csv"


def read_csv(relative: str) -> pd.DataFrame:
    path = ROOT / relative
    if not path.exists():
        raise FileNotFoundError(path)
    frame = pd.read_csv(path)
    frame.columns = [str(column).strip('"') for column in frame.columns]
    if "time" not in frame.columns:
        raise ValueError(f"missing time column: {path}")
    return frame


def verify_columns(frame: pd.DataFrame, columns: Iterable[str], source: str) -> None:
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise KeyError(f"{source}: missing columns {missing}")


def run_plotter(command: list[str]) -> None:
    subprocess.run(command, cwd=ROOT, check=True)


def write_metadata(output: str, data: dict) -> None:
    target = ROOT / output
    target.parent.mkdir(parents=True, exist_ok=True)
    target.with_suffix(".metadata.json").write_text(
        json.dumps({"experiment_id": EXP, "plot_id": target.stem, **data}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def direct_plot(relative_input: str, output: str, title: str, columns: list[str], *, phase: bool = True) -> None:
    frame = read_csv(relative_input)
    verify_columns(frame, columns, relative_input)
    command = [
        sys.executable, str(PLOTTER), str(ROOT / relative_input),
        "-t", "sep_comb", "-c", "dark", "-j", "2pi" if phase else "rad",
        "-s", *columns, "-x", str(ROOT / output), "-w", title,
    ]
    run_plotter(command)
    write_metadata(output, {
        "generated_from": "scripts/josim-plot2.py",
        "plot_input_kind": "raw_csv",
        "source_paths": [relative_input],
        "columns": columns,
        "plot_type": "sep_comb",
        "phase_semantics": "continuous_absolute" if phase else None,
        "phase_display": "continuous phase φ/2π (turns)" if phase else "raw JoSIM phase/current/voltage units",
        "scientific_authority": "raw evidence is analyzed separately; visualization is not event authority",
    })


def merged_plot(output: str, title: str, sources: list[tuple[str, str]], signals: list[tuple[str, str, str]], *, temp_root: Path, phase: bool = True) -> None:
    frames = [(label, relative, read_csv(relative)) for label, relative in sources]
    reference_time = frames[0][2]["time"]
    merged = pd.DataFrame({"time": reference_time})
    output_columns: list[str] = []
    for label, relative, frame in frames:
        if len(frame) != len(reference_time) or not frame["time"].equals(reference_time):
            raise ValueError(f"time grid mismatch for comparison source: {relative}")
        verify_columns(frame, [raw for _, raw, _ in signals], relative)
        for kind, raw, short in signals:
            name = f"{kind}({label} · {short})"
            if name in merged:
                raise ValueError(f"duplicate derived plot column: {name}")
            merged[name] = frame[raw].to_numpy(copy=True)
            output_columns.append(name)
    derived = temp_root / f"{Path(output).stem}.csv"
    merged.to_csv(derived, index=False)
    command = [
        sys.executable, str(PLOTTER), str(derived),
        "-t", "sep_comb", "-c", "dark", "-j", "2pi" if phase else "rad",
        "-s", *output_columns, "-x", str(ROOT / output), "-w", title,
    ]
    run_plotter(command)
    write_metadata(output, {
        "generated_from": "scripts/josim-plot2.py",
        "plot_input_kind": "derived_comparison_csv",
        "derived_input_not_raw_evidence": True,
        "source_paths": [relative for _, relative in sources],
        "columns": output_columns,
        "plot_type": "sep_comb",
        "phase_semantics": "continuous_absolute" if phase else None,
        "phase_display": "continuous phase φ/2π (turns)" if phase else "raw current/voltage units",
        "scientific_authority": "raw evidence is analyzed separately; visualization is not event authority",
    })


def signal_list(*items: tuple[str, str, str]) -> list[tuple[str, str, str]]:
    return list(items)


def sources_for(root_fn, roles: Iterable[str] = ROLES) -> list[tuple[str, str]]:
    return [(ROLE_LABELS[role], root_fn(role)) for role in roles]


def generate() -> None:
    EXP_ROOT.joinpath("plots/cases").mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="josimplot-jsl8-") as temporary:
        temp_root = Path(temporary)
        for role in ROLES:
            relative = new_path(role)
            direct_plot(relative, f"{EXP}/plots/cases/13ps-{role}.html", f"Physical BVM → 8×500 JSL → scaled QB — 13 ps — {ROLE_LABELS[role]}", list(CASE_COLUMNS))

        new_sources = sources_for(new_path)
        reference_sources = [(f"12×320 {ROLE_LABELS[role]}", reference_path(role)) for role in ROLES]
        paired_sources = [(f"12×320 {ROLE_LABELS[role]}", reference_path(role)) for role in ROLES] + [(f"8×500 {ROLE_LABELS[role]}", new_path(role)) for role in ROLES]

        source_signals = signal_list(
            ("I", "I(L_SL|XBVM1)", "I(L_SL)"),
            ("V", "V(SL1)", "V(SL)"),
            ("V", "V(N6|XBVM1)", "V(N6)"),
            ("I", "I(L_PSL|XBVM1)", "I(L_PSL)"),
        )
        merged_plot(f"{EXP}/plots/12x320-vs-8x500-source-loadline.html", "12×320 vs 8×500 — BVM source and SL load-line", paired_sources, source_signals, temp_root=temp_root, phase=False)

        qb_signals = signal_list(
            ("P", "P(BJS|XBQ)", "BJs"), ("P", "P(BJL1|XBQ)", "BJL1"), ("P", "P(BJL2|XBQ)", "BJL2"),
            ("V", "V(BJS|XBQ)", "BJs V"), ("V", "V(BJL1|XBQ)", "BJL1 V"), ("V", "V(BJL2|XBQ)", "BJL2 V"),
            ("I", "I(BJS|XBQ)", "BJs I"), ("I", "I(BJL1|XBQ)", "BJL1 I"), ("I", "I(BJL2|XBQ)", "BJL2 I"),
            ("V", "V(IN)", "V(IN)"), ("I", "I(LIN|XBQ)", "I(Lin)"),
            ("I", "I(L1|XBQ)", "L1"), ("I", "I(L2|XBQ)", "L2"), ("I", "I(L0|XBQ)", "L0"),
            ("I", "I(RB|XBQ)", "RB"), ("I", "I(RJ1|XBQ)", "RJ1"), ("I", "I(RJ2|XBQ)", "RJ2"),
        )
        merged_plot(f"{EXP}/plots/12x320-vs-8x500-qb-transfer.html", "12×320 vs 8×500 — QB transfer, phase/area context and current partition", paired_sources, qb_signals, temp_root=temp_root)

        merged_plot(f"{EXP}/plots/12x320-vs-8x500-port-trajectory.html", "12×320 vs 8×500 — time-parametrized QB V(IN)–I(Lin) port trajectory", paired_sources, signal_list(("V", "V(IN)", "V(IN)"), ("I", "I(LIN|XBQ)", "I(Lin)")), temp_root=temp_root, phase=False)

        jsl_signals = [("I", f"I(B_LD{index})", f"JSL{index} current") for index in range(1, 9)]
        jsl_signals += [("P", "P(B_LD1)", "JSL1 phase"), ("P", "P(B_LD4)", "JSL4 phase"), ("P", "P(B_LD8)", "JSL8 phase")]
        merged_plot(f"{EXP}/plots/12x320-vs-8x500-jsl-current-phase.html", "12×320 vs 8×500 — matched JSL current and representative phase", paired_sources, jsl_signals, temp_root=temp_root, phase=True)

        matched_signals = signal_list(
            ("I", "I(L_SL|XBVM1)", "I(L_SL)"), ("V", "V(IN)", "V(IN)"), ("I", "I(LIN|XBQ)", "I(Lin)"),
            ("P", "P(BJS|XBQ)", "BJs"), ("P", "P(BJL1|XBQ)", "BJL1"), ("P", "P(BJL2|XBQ)", "BJL2"),
            ("I", "I(BJL2|XBQ)", "BJL2 I"), ("V", "V(BJL2|XBQ)", "BJL2 V"),
        )
        merged_plot(f"{EXP}/plots/13ps-matched-cases.html", "BVM → 8×500 JSL → scaled QB — 13 ps matched cases", new_sources, matched_signals, temp_root=temp_root)
        merged_plot(f"{EXP}/plots/13ps-bjl2-phase-area-evidence.html", "BVM → 8×500 JSL → scaled QB — BJL2 phase and same-JJ voltage", new_sources, signal_list(("P", "P(BJL2|XBQ)", "BJL2 phase"), ("V", "V(BJL2|XBQ)", "BJL2 voltage"), ("I", "I(BJL2|XBQ)", "BJL2 current")), temp_root=temp_root)


def check_only() -> None:
    for root_fn, label in ((new_path, "8x500"), (reference_path, "12x320")):
        for role in ROLES:
            frame = read_csv(root_fn(role))
            columns = CASE_COLUMNS if label == "8x500" else tuple(item for item in CASE_COLUMNS if not item.startswith("P(B_LD") and not item.startswith("V(B_LD") and not item.startswith("I(B_LD"))
            verify_columns(frame, columns, root_fn(role))
    print("JSL8/12 reference source/header check: PASS")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    if args.check_only:
        check_only()
    else:
        generate()


if __name__ == "__main__":
    main()
