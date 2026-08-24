#!/usr/bin/env python3
"""Build the two fixed-polarity pulse-5 JTL replay decks.

The source trajectory is copied from the accepted Q0+10-ohm raw CSV without
resampling, amplitude scaling, or waveform shaping.  Absolute time is kept so
the standard JTL has 200 ps of bias-settling time before pulse 5 starts.
"""

from __future__ import annotations

import csv
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
EXP = HERE.parent
SOURCE = EXP / "inputs" / "source" / "q0-scaled-iin-68p4u.csv"

T_START_PS = 200.0
T_END_PS = 260.0
T_STOP_PS = 300.0


def load_pulse5() -> list[tuple[float, float, float]]:
    rows: list[tuple[float, float, float]] = []
    with SOURCE.open(newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            t_s = float(row["time"])
            t_ps = t_s * 1.0e12
            if T_START_PS <= t_ps < T_END_PS:
                rows.append((t_s, t_ps, float(row["V(OUT)"])))
    if not rows:
        raise RuntimeError("pulse-5 source window is empty")
    if any(b[1] <= a[1] for a, b in zip(rows, rows[1:])):
        raise RuntimeError("source pulse time is not strictly increasing")
    return rows


def pspice_time(t_ps: float) -> str:
    return f"{t_ps:.12g}p"


def emit_pwl(rows: list[tuple[float, float, float]], sign: float) -> str:
    pairs = [("0p", "0")]
    pairs.extend((pspice_time(t_ps), f"{sign * value:.12g}") for _, t_ps, value in rows)
    # The source is already at numerical zero by the end of the registered
    # pulse-5 window; the explicit tail only holds the settled endpoint.
    pairs.append((pspice_time(T_STOP_PS), "0"))
    body = " ".join(f"{t} {v}" for t, v in pairs)
    return f"pwl({body})"


def deck(rows: list[tuple[float, float, float]], sign: float) -> str:
    source = emit_pwl(rows, sign)
    polarity = "original" if sign > 0 else "reverse"
    return f"""* JTL transport-gate polarity replay; pulse 5 from accepted Q0+10-ohm raw.
* Polarity: {polarity}; no amplitude scaling or waveform shaping.
.include jjmit.cir
.include JTL.cir

V_REPLAY JTL_IN 0 {source}
XJTL1 JTL_IN JTL_MID THmitll_JTL
XJTL2 JTL_MID JTL_OUT THmitll_JTL
R_TERM JTL_OUT 0 1

.tran 0.0125p 300p
.print I(V_REPLAY) V(JTL_IN) V(JTL_MID) V(JTL_OUT)
.print P(B1|XJTL1) V(B1|XJTL1) I(B1|XJTL1)
.print P(B2|XJTL1) V(B2|XJTL1) I(B2|XJTL1)
.print P(B1|XJTL2) V(B1|XJTL2) I(B1|XJTL2)
.print P(B2|XJTL2) V(B2|XJTL2) I(B2|XJTL2)
.print I(L1|XJTL1) I(L2|XJTL1) I(L3|XJTL1) I(L4|XJTL1)
.print I(IB1|XJTL1) I(RB1|XJTL1) I(RB2|XJTL1)
.print I(L1|XJTL2) I(L2|XJTL2) I(L3|XJTL2) I(L4|XJTL2)
.print I(IB1|XJTL2) I(RB1|XJTL2) I(RB2|XJTL2)
.print I(R_TERM) I(L1|XJTL1)
.end
"""


def main() -> None:
    rows = load_pulse5()
    replay_csv = EXP / "inputs" / "source" / "pulse5_vout.csv"
    with replay_csv.open("w", newline="") as fh:
        writer = csv.writer(fh, lineterminator="\n")
        writer.writerow(["time_s", "time_ps", "V_OUT_V", "V_REPLAY_ORIGINAL_V", "V_REPLAY_REVERSE_V"])
        for t_s, t_ps, value in rows:
            writer.writerow([f"{t_s:.16e}", f"{t_ps:.12g}", f"{value:.16e}", f"{value:.16e}", f"{-value:.16e}"])

    for name, sign in (("original", 1.0), ("reverse", -1.0)):
        path = EXP / "inputs" / name / "main.cir"
        path.write_text(deck(rows, sign), encoding="utf-8")

    print(f"rows={len(rows)}")
    print(f"window_ps={rows[0][1]:.12g}..{rows[-1][1]:.12g}")
    print(f"vout_min_V={min(v for _, _, v in rows):.16e}")
    print(f"vout_max_V={max(v for _, _, v in rows):.16e}")


if __name__ == "__main__":
    main()
