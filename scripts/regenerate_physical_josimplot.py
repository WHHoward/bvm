#!/usr/bin/env python3
"""Regenerate the physical BVM->12xJSL->scaled-QB plots with josim-plot2.

This is a visualization-only driver.  It reads existing CSV files, creates
temporary derived comparison CSVs when several cases must share one page, and
delegates every HTML render to ``scripts/josim-plot2.py``.  It never invokes
JoSIM and never changes a raw CSV, netlist, analysis result, or verdict.

The derived comparison CSVs are disposable plotting inputs, not evidence.
Their provenance is recorded in the ignored ``*.metadata.json`` sidecars.
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
EXP = "test/exploration/physical-bvm-jsl12-qb-sfq-closure-v1-20260824"
EXP_ROOT = ROOT / EXP

ROLES = (
    "logical1_read",
    "logical0_read",
    "logical1_no_read_control",
    "logical0_no_read_control",
)
ROLE_LABELS = {
    "logical1_read": "logical1 READ",
    "logical0_read": "logical0 READ",
    "logical1_no_read_control": "logical1 READ=0",
    "logical0_no_read_control": "logical0 READ=0",
}

PHYSICAL_COLUMNS = (
    "I(I_WL1)", "I(I_SE1)",
    "P(B_JM1|XBVM1)", "V(B_JM1|XBVM1)",
    "P(B_JM2|XBVM1)", "V(B_JM2|XBVM1)",
    "P(B_JS1|XBVM1)", "V(B_JS1|XBVM1)",
    "V(N6|XBVM1)", "V(SL1)",
    "I(L_PSL|XBVM1)", "I(L_SL|XBVM1)",
    "I(B_LD1)", "I(B_LD6)", "I(B_LD12)",
    "P(BJS|XBQ)", "V(BJS|XBQ)", "I(BJS|XBQ)",
    "P(BJL1|XBQ)", "V(BJL1|XBQ)", "I(BJL1|XBQ)",
    "P(BJL2|XBQ)", "V(BJL2|XBQ)", "I(BJL2|XBQ)",
    "V(IN)", "V(OUT)", "I(LIN|XBQ)", "I(L0|XBQ)",
    "I(L1|XBQ)", "I(L2|XBQ)", "I(RB|XBQ)",
    "I(RJ1|XBQ)", "I(RJ2|XBQ)", "I(R_LOAD)", "I(I_IBIAS)",
)


def physical_path(width: int, role: str) -> str:
    return f"{EXP}/raw/{width}/{role}/run-01.csv"


def ideal_path(width: int, role: str) -> str:
    return (
        "test/exploration/bvm-read-semantics-audit-and-jsl-width-bracket-v1-20260824/"
        f"raw/replay/{width}ps/{role}/run-01.csv"
    )


def source_path(width: int, role: str) -> str:
    return (
        "test/exploration/bvm-read-semantics-audit-and-jsl-width-bracket-v1-20260824/"
        f"raw/{width}ps/{role.replace('_', '-')}/run-01.csv"
    )


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


def direct_plot(relative_input: str, output: str, title: str, columns: list[str],
                *, phase: bool = True, sources: list[str] | None = None) -> None:
    frame = read_csv(relative_input)
    verify_columns(frame, columns, relative_input)
    command = [
        sys.executable, str(PLOTTER), str(ROOT / relative_input),
        "-t", "sep_comb", "-c", "dark",
        "-j", "2pi" if phase else "rad",
        "-s", *columns,
        "-x", str(ROOT / output),
        "-w", title,
    ]
    run_plotter(command)
    write_metadata(output, {
        "generated_from": "scripts/josim-plot2.py",
        "plot_input_kind": "raw_csv",
        "source_paths": sources or [relative_input],
        "columns": columns,
        "plot_type": "sep_comb",
        "phase_semantics": "continuous_absolute" if phase else None,
        "phase_display": "continuous phase φ/2π (turns)" if phase else "raw JoSIM phase (rad)",
        "scientific_authority": "accepted analysis/report; visualization is not event authority",
    })


def merged_plot(output: str, title: str, sources: list[tuple[str, str]],
                signals: list[tuple[str, str, str]], *, temp_root: Path,
                phase: bool = True) -> None:
    """Render a comparison page via josim-plot2 from a temporary merged CSV.

    ``signals`` contains (kind, raw_column, short_label), where kind is P/V/I.
    The merged column names retain the kind prefix so josim-plot2 assigns the
    correct axis group while still showing the case label in the legend.
    """
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

    derived = temp_root / (Path(output).stem + ".csv")
    merged.to_csv(derived, index=False)
    target = ROOT / output
    command = [
        sys.executable, str(PLOTTER), str(derived),
        "-t", "sep_comb", "-c", "dark",
        "-j", "2pi" if phase else "rad",
        "-s", *output_columns,
        "-x", str(target),
        "-w", title,
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
        "phase_display": "continuous phase φ/2π (turns)" if phase else "raw JoSIM phase (rad)",
        "scientific_authority": "accepted analysis/report; visualization is not event authority",
    })


def run_plotter(command: list[str]) -> None:
    subprocess.run(command, cwd=ROOT, check=True)


def write_metadata(output: str, data: dict) -> None:
    target = ROOT / output
    target.parent.mkdir(parents=True, exist_ok=True)
    target.with_suffix(".metadata.json").write_text(
        json.dumps({"experiment_id": EXP, "plot_id": target.stem, **data}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def physical_sources(widths: Iterable[int], roles: Iterable[str]) -> list[tuple[str, str]]:
    return [
        (f"{width}ps {ROLE_LABELS[role]}", physical_path(width, role))
        for width in widths for role in roles
    ]


def signal_list(*items: tuple[str, str, str]) -> list[tuple[str, str, str]]:
    return list(items)


def generate() -> None:
    EXP_ROOT.joinpath("plots").mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="josimplot-physical-") as temporary:
        temp_root = Path(temporary)

        # Direct pages: the same standard josim-plot2 template used by the
        # accepted Q0 and canonical BVM visualizations.
        for width in (13, 14):
            for role in ROLES:
                relative = physical_path(width, role)
                output = f"{EXP}/plots/cases/{width}ps-{role}.html"
                direct_plot(
                    relative, output,
                    f"Physical BVM → 12×JSL → scaled QB — {width} ps — {ROLE_LABELS[role]}",
                    list(PHYSICAL_COLUMNS),
                    sources=[relative],
                )

        matched_signals = signal_list(
            ("I", "I(L_SL|XBVM1)", "I(L_SL)"),
            ("V", "V(SL1)", "V(SL)"),
            ("V", "V(N6|XBVM1)", "V(N6)"),
            ("P", "P(BJS|XBQ)", "P(BJs)"),
            ("P", "P(BJL1|XBQ)", "P(BJL1)"),
            ("P", "P(BJL2|XBQ)", "P(BJL2)"),
            ("V", "V(BJL2|XBQ)", "V(BJL2)"),
            ("I", "I(BJL2|XBQ)", "I(BJL2)"),
        )
        for width in (13, 14):
            sources = physical_sources([width], ROLES)
            merged_plot(
                f"{EXP}/plots/{width}ps-matched-cases.html",
                f"Physical BVM → 12×JSL → scaled QB — {width} ps — matched cases",
                sources, matched_signals, temp_root=temp_root,
            )

        all_sources = physical_sources((13, 14), ROLES)
        merged_plot(
            f"{EXP}/plots/physical-width-comparison.html",
            "Physical BVM → 12×JSL → scaled QB — 13 ps vs 14 ps",
            all_sources,
            signal_list(
                ("I", "I(L_SL|XBVM1)", "I(L_SL)"),
                ("P", "P(BJS|XBQ)", "P(BJs)"),
                ("P", "P(BJL1|XBQ)", "P(BJL1)"),
                ("P", "P(BJL2|XBQ)", "P(BJL2)"),
                ("I", "I(BJL2|XBQ)", "I(BJL2)"),
                ("V", "V(BJL2|XBQ)", "V(BJL2)"),
            ),
            temp_root=temp_root,
        )

        merged_plot(
            f"{EXP}/plots/physical-source-and-storage-guards.html",
            "Physical BVM → 12×JSL → scaled QB — SL current and source/storage guards",
            all_sources,
            signal_list(
                ("I", "I(L_SL|XBVM1)", "I(L_SL)"),
                ("V", "V(SL1)", "V(SL)"),
                ("V", "V(N6|XBVM1)", "V(N6)"),
                ("P", "P(B_JM1|XBVM1)", "P(JM1)"),
                ("P", "P(B_JM2|XBVM1)", "P(JM2)"),
                ("P", "P(B_JS1|XBVM1)", "P(JS1)"),
                ("P", "P(B_JS2|XBVM1)", "P(JS2)"),
            ),
            temp_root=temp_root,
        )

        # All twelve series JSL currents remain visible.  The case pages show
        # first/middle/last; this page is the complete direct current view.
        merged_plot(
            f"{EXP}/plots/physical-jsl12-current-consistency.html",
            "Physical BVM → 12×JSL → scaled QB — all JSL currents",
            all_sources,
            [("I", f"I(B_LD{index})", f"JSL{index}") for index in range(1, 13)],
            temp_root=temp_root,
            phase=False,
        )

        kcl_sources = physical_sources((13, 14), ("logical1_read", "logical0_read"))
        merged_plot(
            f"{EXP}/plots/physical-qb-routing-and-kcl.html",
            "Physical BVM → 12×JSL → scaled QB — QB routing currents and KCL branches",
            kcl_sources,
            signal_list(
                ("I", "I(BJS|XBQ)", "BJs"),
                ("I", "I(L1|XBQ)", "L1"),
                ("I", "I(BJL1|XBQ)", "BJL1"),
                ("I", "I(RJ1|XBQ)", "RJ1"),
                ("I", "I(RB|XBQ)", "RB"),
                ("I", "I(L2|XBQ)", "L2"),
                ("I", "I(L0|XBQ)", "L0"),
                ("I", "I(BJL2|XBQ)", "BJL2"),
                ("I", "I(RJ2|XBQ)", "RJ2"),
            ),
            temp_root=temp_root,
            phase=False,
        )

        # Physical-vs-ideal comparison.  The ideal replay is explicitly a
        # source reference; it is not presented as a physical cascade result.
        for width in (13, 14):
            sources: list[tuple[str, str]] = []
            for role in ROLES:
                sources.append((f"physical {ROLE_LABELS[role]}", physical_path(width, role)))
            for role in ROLES:
                sources.append((f"ideal replay {ROLE_LABELS[role]}", ideal_path(width, role)))
            merged_plot(
                f"{EXP}/plots/{width}ps-ideal-vs-physical-qb.html",
                f"Physical BVM → 12×JSL → scaled QB — {width} ps ideal replay vs physical",
                sources,
                signal_list(
                    ("P", "P(BJS|XBQ)", "BJs"),
                    ("P", "P(BJL1|XBQ)", "BJL1"),
                    ("P", "P(BJL2|XBQ)", "BJL2"),
                    ("V", "V(BJL2|XBQ)", "BJL2 voltage"),
                ),
                temp_root=temp_root,
            )

            read_sources: list[tuple[str, str]] = []
            for role in ("logical1_read", "logical0_read"):
                read_sources.append((f"source-only {ROLE_LABELS[role]}", source_path(width, role)))
                read_sources.append((f"physical {ROLE_LABELS[role]}", physical_path(width, role)))
            merged_plot(
                f"{EXP}/plots/{width}ps-source-before-vs-after-qb-loading.html",
                f"Physical BVM → 12×JSL → scaled QB — {width} ps source before/after QB loading",
                read_sources,
                signal_list(
                    ("I", "I(L_SL|XBVM1)", "I(L_SL)"),
                    ("V", "V(SL1)", "V(SL)"),
                    ("V", "V(N6|XBVM1)", "V(N6)"),
                ),
                temp_root=temp_root,
            )

        canonical_sources = physical_sources(
            (13, 14), ("logical1_read", "logical0_read")
        )
        merged_plot(
            f"{EXP}/plots/physical-logical1-vs-logical0.html",
            "Physical BVM → 12×JSL → scaled QB — logical1 vs logical0",
            canonical_sources,
            signal_list(
                ("I", "I(L_SL|XBVM1)", "I(L_SL)"),
                ("P", "P(BJS|XBQ)", "BJs"),
                ("P", "P(BJL1|XBQ)", "BJL1"),
                ("P", "P(BJL2|XBQ)", "BJL2"),
                ("I", "I(BJL2|XBQ)", "I(BJL2)"),
            ),
            temp_root=temp_root,
        )

        event_sources = physical_sources(
            (13, 14), ("logical1_read", "logical0_read")
        )
        merged_plot(
            f"{EXP}/plots/bjl2-phase-area-evidence.html",
            "Physical BVM → 12×JSL → scaled QB — BJL2 phase and same-JJ voltage",
            event_sources,
            signal_list(
                ("P", "P(BJS|XBQ)", "BJs"),
                ("P", "P(BJL1|XBQ)", "BJL1"),
                ("P", "P(BJL2|XBQ)", "BJL2"),
                ("V", "V(BJL2|XBQ)", "BJL2 voltage"),
                ("I", "I(BJL2|XBQ)", "BJL2 current"),
            ),
            temp_root=temp_root,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-only", action="store_true", help="validate source headers without rendering")
    args = parser.parse_args()
    if args.check_only:
        for width in (13, 14):
            for role in ROLES:
                verify_columns(read_csv(physical_path(width, role)), PHYSICAL_COLUMNS, physical_path(width, role))
        print("physical source/header check: PASS")
        return
    generate()


if __name__ == "__main__":
    main()
