#!/usr/bin/env python3
"""Build exact ideal-current replays of the registered 12-JSL + W*=12 ps source."""

from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PHASE_B = ROOT / "raw/phase-b/12jsl-12ps"
PAPER_SL = ROOT.parent / "paper-sl-l0-20260824/raw"
QB_SOURCE = ROOT.parent / "paper-sl-q1-20260824/inputs"
INPUTS = ROOT / "inputs/phase-c"
SOURCES = ROOT / "replay_sources"

CASES = {
    "wstar12-logical1-read": PHASE_B / "logical1-read/run-01.csv",
    "wstar12-logical0-read": PHASE_B / "logical0-read/run-01.csv",
    "wstar12-logical1-read0-control": PAPER_SL / "logical1-read0-control/run-01.csv",
    "wstar12-logical0-read0-control": PAPER_SL / "logical0-read0-control/run-01.csv",
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
    for i, value in enumerate(header):
        if value.strip() == name:
            return i
    raise KeyError(f"missing {name!r} in {header!r}")


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
        time_ps = float(row[t_i]) * 1e12
        currents = [float(row[i]) for i in current_indices]
        max_spread = max(max_spread, max(currents) - min(currents))
        if time_ps <= previous_t:
            raise ValueError(f"non-increasing time in {path}")
        samples.append((time_ps, currents[0]))
        previous_t = time_ps
        minimum = min(minimum, currents[0])
        maximum = max(maximum, currents[0])
    return samples, {"samples": len(samples), "start_ps": samples[0][0], "end_ps": samples[-1][0], "min_A": minimum, "max_A": maximum, "max_series_spread_A": max_spread}


def write_snapshot(path: Path, samples: list[tuple[float, float]]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["time_ps", "I_JSL_A"])
        for time_ps, current in samples:
            writer.writerow([fmt(time_ps), fmt(current)])


def pwl_lines(samples: list[tuple[float, float]]) -> list[str]:
    pairs = [f"{fmt(t)}p {fmt(i)}" for t, i in samples]
    chunks = [pairs[i : i + 18] for i in range(0, len(pairs), 18)]
    lines = ["I_REPLAY 0 IN pwl(" + " ".join(chunks[0])]
    lines.extend("+ " + " ".join(chunk) for chunk in chunks[1:])
    lines[-1] += ")"
    return lines


def write_deck(path: Path, label: str, snapshot: str, samples: list[tuple[float, float]]) -> None:
    lines = [
        f"* BVM_JSL_READ_WIDTH_TO_QB_SFQ_V1 Phase-C {label}: exact current replay",
        f"* source snapshot={snapshot}; no scaling/rectify/hold/resample",
        ".include jjmit.cir",
        ".include bq_cell.cir",
        "XBQ IN OUT IBIAS BQ",
        *pwl_lines(samples),
        "R_LOAD OUT 0 10",
        "I_IBIAS 0 IBIAS pwl(0p 0 1p 35u 2p 35u 170p 35u)",
        ".tran 0.0125p 170p",
        ".print P(BJs|XBQ) V(BJs|XBQ) I(BJs|XBQ)",
        ".print P(BJL1|XBQ) V(BJL1|XBQ) I(BJL1|XBQ)",
        ".print P(BJL2|XBQ) V(BJL2|XBQ) I(BJL2|XBQ)",
        ".print I(I_REPLAY) I(I_IBIAS) V(IN) V(OUT) I(R_LOAD)",
        ".print I(Lin|XBQ) I(L0|XBQ) I(L1|XBQ) I(L2|XBQ) I(RB|XBQ) I(RJ1|XBQ) I(RJ2|XBQ)",
        ".end",
    ]
    path.write_text("\n".join(lines) + "\n")


def main() -> None:
    INPUTS.mkdir(parents=True, exist_ok=True)
    SOURCES.mkdir(parents=True, exist_ok=True)
    for name in ("jjmit.cir", "bq_cell.cir"):
        destination = INPUTS / name
        source = QB_SOURCE / name
        if destination.exists():
            if destination.read_bytes() != source.read_bytes():
                raise SystemExit(f"existing model differs: {destination}")
        else:
            shutil.copy2(source, destination)
    manifest: dict[str, object] = {}
    for case_id, source in CASES.items():
        samples, stats = load_current(source)
        snapshot = SOURCES / f"{case_id}.csv"
        deck = INPUTS / f"{case_id}.cir"
        if snapshot.exists() or deck.exists():
            raise SystemExit(f"refusing to overwrite generated fixture: {snapshot} / {deck}")
        write_snapshot(snapshot, samples)
        write_deck(deck, case_id, snapshot.name, samples)
        manifest[case_id] = {"source": str(source), **stats, "snapshot": str(snapshot), "deck": str(deck)}
    (SOURCES / "source-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
