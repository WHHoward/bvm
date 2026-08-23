#!/usr/bin/env python3
"""Build QB-Q2C scaled QB decks from frozen Q2A canonical replay sources."""

from __future__ import annotations

import csv
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INPUTS = ROOT / "inputs"
SOURCES = INPUTS / "replay_sources"
Q2A = ROOT.parent / "qb-q2a-source-decoupled-waveform-replay-20260824"
Q2B = ROOT.parent / "qb-q2b-central-bias-bracketing-20260824"
Q1 = ROOT.parent / "qb-q1-canonical-bvm-scaled-qb-compatibility-20260824"

SCALES = {
    "S085": (0.85, 0.425, 0.306, 0.459, 29.75),
    "S070": (0.70, 0.350, 0.252, 0.378, 24.50),
    "S055": (0.55, 0.275, 0.198, 0.297, 19.25),
}
SOURCE_SPECS = {
    "logical1-read": ("C-canonical-logical1-vsl.csv", Q2A / "inputs/replay_sources/C-canonical-logical1-vsl.csv", None),
    "logical0-read": ("C0-canonical-logical0-vsl.csv", Q2A / "inputs/replay_sources/C0-canonical-logical0-vsl.csv", None),
    "logical1-read0-control": ("logical1-read0-control-vsl.csv", Q1 / "reference/canonical/logical1-read0-no-receiver.csv", "I(L_SL|XBVM1)"),
    "logical0-read0-control": ("logical0-read0-control-vsl.csv", Q1 / "reference/canonical/logical0-read0-no-receiver.csv", "I(L_SL|XBVM1)"),
}


def load_csv(path: Path, current_name: str | None = None) -> list[tuple[float, float, float]]:
    with path.open(newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader)
        rows = list(reader)
    names = [x.strip() for x in header]

    def index(name: str) -> int:
        if name not in names:
            raise KeyError(f"{name!r} missing from {path}")
        return names.index(name)

    if "time_ps" in names:
        ti, vi, ci, scale_time = index("time_ps"), index("V_SL_V"), 2, 1.0
    else:
        ti, vi, ci, scale_time = index("time"), index("V(SL1)"), index(current_name or "I(L_SL|XBVM1)"), 1e12
    out = []
    previous = -1.0
    for row in rows:
        time_ps = float(row[ti]) * scale_time
        if time_ps <= previous:
            raise ValueError(f"non-increasing time in {path}")
        out.append((time_ps, float(row[vi]), float(row[ci])))
        previous = time_ps
    return out


def fmt(value: float) -> str:
    return f"{value:.17g}"


def write_snapshot(path: Path, samples: list[tuple[float, float, float]], label: str) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["time_ps", "V_SL_V", label])
        writer.writerows(([fmt(t), fmt(v), fmt(i)] for t, v, i in samples))


def pwl_lines(samples: list[tuple[float, float, float]]) -> list[str]:
    pairs = [f"{fmt(t)}p {fmt(v)}" for t, v, _ in samples]
    chunks = [pairs[i:i + 18] for i in range(0, len(pairs), 18)]
    lines = ["V_REPLAY IN 0 pwl(" + " ".join(chunks[0])]
    for chunk in chunks[1:]:
        lines.append("+ " + " ".join(chunk))
    lines[-1] += ")"
    return lines


def write_bq_cell(path: Path, bjs: float, bjl1: float, bjl2: float) -> None:
    content = (
        "* QB-Q2C frozen topology with uniform junction scale\n"
        ".subckt BQ IN OUT IB\n"
        "Lin IN 1 0.8p\n"
        "L0 4 OUT 1.323p\n"
        "L1 2 3 3.91p\n"
        "L2 3 4 3.91p\n"
        f"BJs 1 2 jjmit area={bjs:.12g}\n"
        f"BJL1 2 0 jjmit area={bjl1:.12g}\n"
        "RJ1 2 0 33\n"
        f"BJL2 4 0 jjmit area={bjl2:.12g}\n"
        "RJ2 4 0 22\n"
        "RB IB 3 6\n"
        ".ends BQ\n"
    )
    path.write_text(content)


def write_deck(path: Path, case: str, scale_name: str, scale: float, bias_uA: float, samples: list[tuple[float, float, float]], source_name: str) -> None:
    bias_literal = f"{bias_uA:.12g}u"
    lines = [
        f"* QB-Q2C {case}, scale={scale:.2f}, IBIAS={bias_literal}; frozen canonical replay={source_name}",
        ".include ../jjmit.cir",
        ".include bq_cell.cir",
        "XBQ IN OUT IBIAS BQ",
        *pwl_lines(samples),
        "R_LOAD OUT 0 10",
        f"I_IBIAS 0 IBIAS pwl(0p 0 1p {bias_literal} 2p {bias_literal} 170p {bias_literal})",
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
    INPUTS.mkdir(exist_ok=True)
    SOURCES.mkdir(exist_ok=True)
    shutil.copy2(Q2B / "inputs/jjmit.cir", INPUTS / "jjmit.cir")
    sources = {}
    for case, (snapshot, source, current_name) in SOURCE_SPECS.items():
        # Q2B already contains the byte-preserved replay snapshots used for
        # the accepted canonical replay. Copy those snapshots directly;
        # numeric reserialization would weaken the frozen-source claim.
        frozen_snapshot = Q2B / "inputs/replay_sources" / snapshot
        shutil.copy2(frozen_snapshot, SOURCES / snapshot)
        samples = load_csv(frozen_snapshot, current_name)
        sources[case] = samples
        print(case, len(samples), samples[0][0], samples[-1][0])
    for scale_name, (scale, bjs, bjl1, bjl2, bias) in SCALES.items():
        scale_dir = INPUTS / scale_name
        raw_dir = ROOT / "raw" / scale_name
        scale_dir.mkdir(exist_ok=True)
        raw_dir.mkdir(parents=True, exist_ok=True)
        write_bq_cell(scale_dir / "bq_cell.cir", bjs, bjl1, bjl2)
        for case, samples in sources.items():
            write_deck(scale_dir / f"{case}.cir", case, scale_name, scale, bias, samples, SOURCE_SPECS[case][0])


if __name__ == "__main__":
    main()
