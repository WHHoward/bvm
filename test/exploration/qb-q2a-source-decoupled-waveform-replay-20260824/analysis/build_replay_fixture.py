#!/usr/bin/env python3
"""Build the frozen QB-Q2A standalone replay decks from committed raw CSVs."""

from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INPUTS = ROOT / "inputs"
SOURCES = INPUTS / "replay_sources"


def read_csv(path: Path) -> tuple[list[str], list[list[str]]]:
    with path.open(newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader)
        rows = [row for row in reader if row]
    if not rows:
        raise ValueError(f"empty source CSV: {path}")
    return header, rows


def col_index(header: list[str], requested: str) -> int:
    matches = [index for index, name in enumerate(header) if name.strip() == requested]
    if not matches:
        raise KeyError(f"{requested!r} not found in {header!r}")
    return matches[0]


def load_source(path: Path, voltage_name: str, current_name: str) -> list[tuple[float, float, float]]:
    header, rows = read_csv(path)
    t_i = col_index(header, "time")
    v_i = col_index(header, voltage_name)
    c_i = col_index(header, current_name)
    output: list[tuple[float, float, float]] = []
    previous_t = -1.0
    for row in rows:
        time_ps = float(row[t_i]) * 1e12
        voltage_v = float(row[v_i])
        current_a = float(row[c_i])
        if time_ps <= previous_t:
            raise ValueError(f"non-increasing time in {path}")
        output.append((time_ps, voltage_v, current_a))
        previous_t = time_ps
    return output


def fmt(value: float) -> str:
    return f"{value:.17g}"


def write_snapshot(path: Path, samples: list[tuple[float, float, float]], current_label: str) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["time_ps", "V_SL_V", current_label])
        for time_ps, voltage_v, current_a in samples:
            writer.writerow([fmt(time_ps), fmt(voltage_v), fmt(current_a)])


def pwl_lines(source_name: str, samples: list[tuple[float, float, float]]) -> list[str]:
    pairs = [f"{fmt(time_ps)}p {fmt(voltage_v)}" for time_ps, voltage_v, _ in samples]
    chunks = [pairs[index : index + 18] for index in range(0, len(pairs), 18)]
    lines = [f"V_REPLAY IN 0 pwl({chunks[0][0]}" + (" " + " ".join(chunks[0][1:]) if len(chunks[0]) > 1 else "")]
    for chunk in chunks[1:]:
        lines.append("+ " + " ".join(chunk))
    lines[-1] += ")"
    return lines


def common_tail(stop: str) -> list[str]:
    return [
        "R_LOAD OUT 0 10",
        "I_IBIAS 0 IBIAS pwl(0p 0 1p 35u 2p 35u " + stop + " 35u)",
        ".tran 0.0125p 170p",
        ".print P(BJs|XBQ) V(BJs|XBQ) I(BJs|XBQ)",
        ".print P(BJL1|XBQ) V(BJL1|XBQ) I(BJL1|XBQ)",
        ".print P(BJL2|XBQ) V(BJL2|XBQ) I(BJL2|XBQ)",
        ".print I(Lin|XBQ) I(L0|XBQ) I(L1|XBQ) I(L2|XBQ) I(RB|XBQ) I(RJ1|XBQ) I(RJ2|XBQ)",
        ".print V(IN) I(V_REPLAY) V(OUT) I(R_LOAD)",
        ".end",
    ]


def write_replay_deck(path: Path, label: str, source_name: str, samples: list[tuple[float, float, float]]) -> None:
    lines = [
        f"* QB-Q2A {label}: ideal source replay; source snapshot={source_name}",
        ".include jjmit.cir",
        ".include bq_cell.cir",
        "XBQ IN OUT IBIAS BQ",
        *pwl_lines(source_name, samples),
        *common_tail("170p"),
    ]
    path.write_text("\n".join(lines) + "\n")


def write_a_deck(path: Path) -> None:
    lines = [
        "* QB-Q2A A: Q0 68.4 uA ideal-current positive control",
        ".include jjmit.cir",
        ".include bq_cell.cir",
        "XBQ IN OUT IBIAS BQ",
        "R_LOAD OUT 0 10",
        "I_IBIAS 0 IBIAS pwl(0p 0 1p 35u 2p 35u 300p 35u)",
        "I_IN 0 IN pulse(0 68.4u 10p 1p 1p 5p 50p)",
        ".tran 0.1p 300p",
        ".print P(BJs|XBQ) V(BJs|XBQ) I(BJs|XBQ)",
        ".print P(BJL1|XBQ) V(BJL1|XBQ) I(BJL1|XBQ)",
        ".print P(BJL2|XBQ) V(BJL2|XBQ) I(BJL2|XBQ)",
        ".print I(I_IN) I(I_IBIAS) V(IN) V(OUT) I(R_LOAD)",
        ".print I(Lin|XBQ) I(L0|XBQ) I(L1|XBQ) I(L2|XBQ) I(RB|XBQ) I(RJ1|XBQ) I(RJ2|XBQ)",
        ".end",
    ]
    path.write_text("\n".join(lines) + "\n")


def main() -> None:
    sources = {
        "B-q1-loaded": (
            ROOT.parent / "qb-q1-canonical-bvm-scaled-qb-compatibility-20260824" / "raw" / "logical1-read.csv",
            "V(SL1)",
            "I(LIN|XBQ)",
            "B-q1-loaded-vsl.csv",
            "B-q1-loaded-ilin.csv",
            "B-q1-loaded-vsl.cir",
        ),
        "C-canonical-logical1": (
            ROOT.parent / "qb-q1-canonical-bvm-scaled-qb-compatibility-20260824" / "reference" / "canonical" / "logical1-read-no-receiver.csv",
            "V(SL1)",
            "I(L_SL|XBVM1)",
            "C-canonical-logical1-vsl.csv",
            "C-canonical-logical1-isls.csv",
            "C-canonical-logical1-vsl.cir",
        ),
        "C0-canonical-logical0": (
            ROOT.parent / "qb-q1-canonical-bvm-scaled-qb-compatibility-20260824" / "reference" / "canonical" / "logical0-read-no-receiver.csv",
            "V(SL1)",
            "I(L_SL|XBVM1)",
            "C0-canonical-logical0-vsl.csv",
            "C0-canonical-logical0-isls.csv",
            "C0-canonical-logical0-vsl.cir",
        ),
    }
    write_a_deck(INPUTS / "A-q0-68p4u-positive-control.cir")
    for label, (path, voltage_name, current_name, voltage_file, current_file, deck_file) in sources.items():
        samples = load_source(path, voltage_name, current_name)
        write_snapshot(SOURCES / voltage_file, samples, current_name)
        write_snapshot(SOURCES / current_file, samples, current_name)
        write_replay_deck(INPUTS / deck_file, label, voltage_file, samples)
        print(label, len(samples), samples[0][0], samples[-1][0])


if __name__ == "__main__":
    main()
