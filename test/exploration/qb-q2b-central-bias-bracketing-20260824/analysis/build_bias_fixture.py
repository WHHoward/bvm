#!/usr/bin/env python3
"""Build Q2B bias-only decks from frozen canonical replay voltage sources."""

from __future__ import annotations

import csv
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INPUTS = ROOT / "inputs"
SOURCES = INPUTS / "replay_sources"
Q2A = ROOT.parent / "qb-q2a-source-decoupled-waveform-replay-20260824"
Q1 = ROOT.parent / "qb-q1-canonical-bvm-scaled-qb-compatibility-20260824"


SOURCE_SPECS = {
    "logical1-read": ("C-canonical-logical1-vsl.csv", Q2A / "inputs" / "replay_sources" / "C-canonical-logical1-vsl.csv", None),
    "logical0-read": ("C0-canonical-logical0-vsl.csv", Q2A / "inputs" / "replay_sources" / "C0-canonical-logical0-vsl.csv", None),
    "logical1-read0-control": ("logical1-read0-control-vsl.csv", Q1 / "reference" / "canonical" / "logical1-read0-no-receiver.csv", "I(L_SL|XBVM1)"),
    "logical0-read0-control": ("logical0-read0-control-vsl.csv", Q1 / "reference" / "canonical" / "logical0-read0-no-receiver.csv", "I(L_SL|XBVM1)"),
}
BIAS_POINTS = {30: "30u", 40: "40u"}


def load_csv(path: Path, voltage_name: str = "V(SL1)", current_name: str | None = None) -> list[tuple[float, float, float]]:
    with path.open(newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader)
        rows = list(reader)
    names = [name.strip() for name in header]
    def index(name: str) -> int:
        for i, value in enumerate(names):
            if value == name:
                return i
        raise KeyError(f"{name!r} missing from {path}")
    if "time_ps" in names:
        t_i = index("time_ps")
        v_i = index("V_SL_V")
        c_i = 2
        scale_time = 1.0
    else:
        t_i = index("time")
        v_i = index(voltage_name)
        c_i = index(current_name or "I(L_SL|XBVM1)")
        scale_time = 1e12
    result: list[tuple[float, float, float]] = []
    previous = -1.0
    for row in rows:
        time_ps = float(row[t_i]) * scale_time
        sample = (time_ps, float(row[v_i]), float(row[c_i]))
        if time_ps <= previous:
            raise ValueError(f"non-increasing source time in {path}")
        result.append(sample)
        previous = time_ps
    return result


def fmt(value: float) -> str:
    return f"{value:.17g}"


def write_snapshot(path: Path, samples: list[tuple[float, float, float]], label: str) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["time_ps", "V_SL_V", label])
        for time_ps, voltage, current in samples:
            writer.writerow([fmt(time_ps), fmt(voltage), fmt(current)])


def pwl_lines(samples: list[tuple[float, float, float]]) -> list[str]:
    pairs = [f"{fmt(t)}p {fmt(v)}" for t, v, _ in samples]
    chunks = [pairs[i : i + 18] for i in range(0, len(pairs), 18)]
    lines = ["V_REPLAY IN 0 pwl(" + " ".join(chunks[0])]
    for chunk in chunks[1:]:
        lines.append("+ " + " ".join(chunk))
    lines[-1] += ")"
    return lines


def write_deck(path: Path, case: str, bias: int, samples: list[tuple[float, float, float]], source_name: str) -> None:
    lines = [
        f"* QB-Q2B {case}, IBIAS={bias}uA; frozen canonical voltage replay={source_name}",
        ".include ../jjmit.cir",
        ".include ../bq_cell.cir",
        "XBQ IN OUT IBIAS BQ",
        *pwl_lines(samples),
        "R_LOAD OUT 0 10",
        f"I_IBIAS 0 IBIAS pwl(0p 0 1p {BIAS_POINTS[bias]} 2p {BIAS_POINTS[bias]} 170p {BIAS_POINTS[bias]})",
        ".tran 0.0125p 170p",
        ".print P(BJs|XBQ) V(BJs|XBQ) I(BJs|XBQ)",
        ".print P(BJL1|XBQ) V(BJL1|XBQ) I(BJL1|XBQ)",
        ".print P(BJL2|XBQ) V(BJL2|XBQ) I(BJL2|XBQ)",
        ".print I(Lin|XBQ) I(L0|XBQ) I(L1|XBQ) I(L2|XBQ) I(RB|XBQ) I(RJ1|XBQ) I(RJ2|XBQ)",
        ".print V(IN) I(V_REPLAY) V(OUT) I(R_LOAD)",
        ".end",
    ]
    path.write_text("\n".join(lines) + "\n")


def main() -> None:
    sources: dict[str, list[tuple[float, float, float]]] = {}
    for case, (snapshot_name, source_path, current_name) in SOURCE_SPECS.items():
        if current_name is None:
            shutil.copy2(source_path, SOURCES / snapshot_name)
        samples = load_csv(source_path, current_name=current_name)
        if current_name is not None:
            write_snapshot(SOURCES / snapshot_name, samples, current_name)
        sources[case] = samples
        print(case, len(samples), samples[0][0], samples[-1][0])
    for bias in BIAS_POINTS:
        bias_dir = INPUTS / f"IBIAS{bias}"
        bias_dir.mkdir(exist_ok=True)
        for case, samples in sources.items():
            source_name = SOURCE_SPECS[case][0]
            write_deck(bias_dir / f"{case}.cir", case, bias, samples, source_name)


if __name__ == "__main__":
    main()
