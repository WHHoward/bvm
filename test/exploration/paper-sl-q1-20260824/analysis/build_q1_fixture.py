#!/usr/bin/env python3
"""Build PAPER-SL-Q1 exact-current replay decks from committed JSL raw data."""

from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INPUTS = ROOT / "inputs"
SOURCES = ROOT / "replay_sources"
PAPER_SL = ROOT.parent / "paper-sl-l0-20260824"

SOURCE_CASES = {
    "paper-j1-logical1-read": PAPER_SL / "raw/logical1-read/run-01.csv",
    "paper-j0-logical0-read": PAPER_SL / "raw/logical0-read/run-01.csv",
    "paper-j1-logical1-read0-control": PAPER_SL / "raw/logical1-read0-control/run-01.csv",
    "paper-j0-logical0-read0-control": PAPER_SL / "raw/logical0-read0-control/run-01.csv",
}
JSL_COLUMNS = [f"I(B_LD{i})" for i in range(1, 13)]


def read_csv(path: Path) -> tuple[list[str], list[list[str]]]:
    with path.open(newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader)
        rows = [row for row in reader if row]
    if not rows:
        raise ValueError(f"empty source CSV: {path}")
    return header, rows


def index(header: list[str], name: str) -> int:
    matches = [i for i, value in enumerate(header) if value.strip() == name]
    if not matches:
        raise KeyError(f"missing {name!r} in {header!r}")
    return matches[0]


def fmt(value: float) -> str:
    return f"{value:.17g}"


def load_current(path: Path) -> tuple[list[tuple[float, float]], dict[str, float]]:
    header, rows = read_csv(path)
    t_i = index(header, "time")
    current_indices = [index(header, name) for name in JSL_COLUMNS]
    samples: list[tuple[float, float]] = []
    max_spread = 0.0
    previous_t = -1.0
    minimum = float("inf")
    maximum = float("-inf")
    for row in rows:
        if len(row) != len(header):
            raise ValueError(f"row/header mismatch in {path}")
        time_ps = float(row[t_i]) * 1e12
        currents = [float(row[i]) for i in current_indices]
        spread = max(currents) - min(currents)
        max_spread = max(max_spread, abs(spread))
        current = currents[0]
        if time_ps <= previous_t:
            raise ValueError(f"non-increasing time in {path}")
        samples.append((time_ps, current))
        previous_t = time_ps
        minimum = min(minimum, current)
        maximum = max(maximum, current)
    return samples, {
        "samples": float(len(samples)),
        "start_ps": samples[0][0],
        "end_ps": samples[-1][0],
        "min_A": minimum,
        "max_A": maximum,
        "max_series_spread_A": max_spread,
    }


def write_snapshot(path: Path, samples: list[tuple[float, float]]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["time_ps", "I_JSL_A"])
        for time_ps, current in samples:
            writer.writerow([fmt(time_ps), fmt(current)])


def pwl_lines(samples: list[tuple[float, float]]) -> list[str]:
    pairs = [f"{fmt(time_ps)}p {fmt(current)}" for time_ps, current in samples]
    chunks = [pairs[i : i + 18] for i in range(0, len(pairs), 18)]
    lines = ["I_REPLAY 0 IN pwl(" + " ".join(chunks[0])]
    for chunk in chunks[1:-1]:
        lines.append("+ " + " ".join(chunk))
    lines.append("+ " + " ".join(chunks[-1]) + ")")
    return lines


def common_tail(stop: str) -> list[str]:
    return [
        "R_LOAD OUT 0 10",
        f"I_IBIAS 0 IBIAS pwl(0p 0 1p 35u 2p 35u {stop} 35u)",
        ".tran 0.0125p 170p",
        ".print P(BJs|XBQ) V(BJs|XBQ) I(BJs|XBQ)",
        ".print P(BJL1|XBQ) V(BJL1|XBQ) I(BJL1|XBQ)",
        ".print P(BJL2|XBQ) V(BJL2|XBQ) I(BJL2|XBQ)",
        ".print I(I_REPLAY) I(I_IBIAS) V(IN) V(OUT) I(R_LOAD)",
        ".print I(Lin|XBQ) I(L0|XBQ) I(L1|XBQ) I(L2|XBQ) I(RB|XBQ) I(RJ1|XBQ) I(RJ2|XBQ)",
        ".end",
    ]


def write_replay_deck(path: Path, label: str, source_name: str, samples: list[tuple[float, float]]) -> None:
    lines = [
        f"* PAPER-SL-Q1 {label}: exact current replay; source={source_name}",
        ".include jjmit.cir",
        ".include bq_cell.cir",
        "XBQ IN OUT IBIAS BQ",
        *pwl_lines(samples),
        *common_tail("170p"),
    ]
    path.write_text("\n".join(lines) + "\n")


def write_positive_control(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "* PAPER-SL-Q1 Q0 68.4 uA standalone positive control",
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
        )
        + "\n"
    )


def main() -> None:
    SOURCES.mkdir(parents=True, exist_ok=True)
    write_positive_control(INPUTS / "q0-68p4u-positive-control.cir")
    manifest: dict[str, dict[str, float | str]] = {}
    for label, source_path in SOURCE_CASES.items():
        samples, stats = load_current(source_path)
        snapshot = SOURCES / f"{label}.csv"
        deck = INPUTS / f"{label}.cir"
        write_snapshot(snapshot, samples)
        write_replay_deck(deck, label, snapshot.name, samples)
        manifest[label] = {"source": str(source_path), **stats}
        print(label, len(samples), samples[0][0], samples[-1][0], stats["min_A"] * 1e6, stats["max_A"] * 1e6, stats["max_series_spread_A"])
    (SOURCES / "source-manifest.json").write_text(__import__("json").dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()

