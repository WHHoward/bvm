#!/usr/bin/env python3
"""Offline R4-A weak-mutual capture analytic precheck.

This script never invokes JoSIM.  R3-A did not directly probe I(L_TX); the
R3-A source netlist has R_IN -> N_PICK -> L_TX with no other N_PICK branch, so
I(L_TX) is derived from the raw I(R_IN) column by series KCL.
"""

from __future__ import annotations

import csv
import math
from pathlib import Path


REPO = Path(__file__).resolve().parents[4]
RAW = REPO / "test/exploration/bvm-sfq-receiver-r3a-onset-extraction-20260822/raw"
CASES = (
    "read1",
    "read0",
    "logical1-read0-control",
    "logical0-read0-control",
)
PHI0 = 2.067833848e-15
L_TX = 0.20e-12
K = 0.80
L_H = 100.0e-12
JSET_AREA = 0.05
JSET_BIAS = 3.0e-6
M = K * math.sqrt(L_TX * L_H)
IC = 0.1e-3 * JSET_AREA
CAP = 0.07e-12 * JSET_AREA
RN = 16.0 / JSET_AREA
R0 = 160.0 / JSET_AREA
BETA_L = 2.0 * math.pi * L_H * IC / PHI0


def trapz(xs: list[float], ys: list[float]) -> float:
    return sum(
        0.5 * (xs[i + 1] - xs[i]) * (ys[i + 1] + ys[i])
        for i in range(len(xs) - 1)
    )


def load(case: str) -> tuple[list[float], list[float]]:
    path = RAW / case / "run-01.csv"
    with path.open(newline="") as stream:
        reader = csv.DictReader(stream)
        fields = reader.fieldnames or []
        if "I(L_TX|XTRIG)" in fields:
            raise RuntimeError("unexpected direct I(L_TX) probe; update mapping")
        required = {"time", "I(R_IN|XTRIG)"}
        missing = required - set(fields)
        if missing:
            raise RuntimeError(f"{case}: missing columns {sorted(missing)}")
        rows = list(reader)
    # time is seconds in JoSIM CSV; current is A.
    return (
        [float(row["time"]) for row in rows],
        [float(row["I(R_IN|XTRIG)"]) for row in rows],
    )


def window_stats(times: list[float], current: list[float], lo_ps: float, hi_ps: float):
    selected = [
        (t, i)
        for t, i in zip(times, current)
        if lo_ps <= t * 1e12 < hi_ps
    ]
    ts = [t for t, _ in selected]
    xs = [i for _, i in selected]
    phi = [M * i / PHI0 for i in xs]
    positive = [max(i, 0.0) for i in xs]
    negative = [min(i, 0.0) for i in xs]
    q = trapz(ts, xs)
    q_pos = trapz(ts, positive)
    q_neg = trapz(ts, negative)
    q_abs = trapz(ts, [abs(i) for i in xs])
    imax = max(range(len(xs)), key=xs.__getitem__)
    imin = min(range(len(xs)), key=xs.__getitem__)
    return {
        "n": len(xs),
        "i_pos_uA": xs[imax] * 1e6,
        "i_pos_ps": ts[imax] * 1e12,
        "i_neg_uA": xs[imin] * 1e6,
        "i_neg_ps": ts[imin] * 1e12,
        "i_mean_uA": sum(xs) / len(xs) * 1e6,
        "q_fC": q * 1e15,
        "q_pos_fC": q_pos * 1e15,
        "q_neg_fC": q_neg * 1e15,
        "q_abs_fC": q_abs * 1e15,
        "phi_pos": max(phi),
        "phi_neg": min(phi),
        "phi_mean": sum(phi) / len(phi),
        "phi_area_phi0_ps": trapz([t * 1e12 for t in ts], phi),
    }


def main() -> None:
    data = {case: load(case) for case in CASES}
    print(f"M_H={M:.12e} H ({M * 1e12:.9f} pH)")
    print(f"Ic={IC * 1e6:.9f} uA C={CAP * 1e15:.9f} fF RN={RN:.9f} ohm R0={R0:.9f} ohm")
    print(f"beta_L={BETA_L:.12f} bias_ratio={JSET_BIAS / IC:.12f}")
    print("window=97..130 ps")
    for case in CASES:
        print(case, window_stats(*data[case], 97.0, 130.0))

    t1, i1 = data["read1"]
    t0, i0 = data["read0"]
    if t1 != t0:
        raise RuntimeError("read1/read0 time axes differ")
    for lo_ps, hi_ps in ((96.0, 105.0), (97.0, 130.0), (20.0, 170.0)):
        selected = [
            (t, a - b)
            for t, a, b in zip(t1, i1, i0)
            if lo_ps <= t * 1e12 < hi_ps
        ]
        ts = [t for t, _ in selected]
        ds = [d for _, d in selected]
        imax = max(range(len(ds)), key=ds.__getitem__)
        imin = min(range(len(ds)), key=ds.__getitem__)
        print(
            f"sep[{lo_ps},{hi_ps})ps "
            f"max={ds[imax] * 1e6:.9f}uA@{ts[imax] * 1e12:.9f}ps "
            f"min={ds[imin] * 1e6:.9f}uA@{ts[imin] * 1e12:.9f}ps "
            f"mean={sum(ds) / len(ds) * 1e6:.9f}uA "
            f"rms={(sum(d * d for d in ds) / len(ds)) ** 0.5 * 1e6:.9f}uA "
            f"net_q={trapz(ts, ds) * 1e15:.9f}fC "
            f"abs_q={trapz(ts, [abs(d) for d in ds]) * 1e15:.9f}fC"
        )


if __name__ == "__main__":
    main()
