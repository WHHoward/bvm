#!/usr/bin/env python3
"""Quick qualifying-event check for R2-D sequential runs (same oracle as R2-B/C)."""

from __future__ import annotations

import csv
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PHI0_WB = 2.067833848e-15
TWO_PI = 2.0 * math.pi


def quick_check(pid: str) -> dict:
    path = ROOT / "raw" / pid / "run-01.csv"
    with path.open(newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
        iph = header.index("P(B_OUT|XTRIG)")
        iv = header.index("V(B_OUT|XTRIG)")
        it = header.index("time")
        rows = [(float(r[it]) * 1e12, float(r[iph]), float(r[iv])) for r in reader]
    win = [r for r in rows if 94.0 <= r[0] <= 170.0]
    unw = [0.0] * len(win)
    for i in range(1, len(win)):
        d = win[i][1] - win[i - 1][1]
        d -= TWO_PI * round(d / TWO_PI)
        unw[i] = unw[i - 1] + d
    best = 0.0
    best_info = None
    complete_consistent = False
    i = 0
    n = len(win)
    while i < n - 1:
        j = i
        sgn = 1 if unw[min(i + 1, n - 1)] - unw[i] >= 0 else -1
        while j < n - 1 and (unw[j + 1] - unw[j]) * sgn >= 0:
            j += 1
        turns = abs(unw[j] - unw[i]) / TWO_PI
        if turns > best:
            area_wb = sum(
                0.5 * (win[k][2] + win[k + 1][2]) * (win[k + 1][0] - win[k][0]) * 1e-12
                for k in range(i, j)
            )
            area_turns = area_wb / PHI0_WB
            resid = area_turns - (unw[j] - unw[i]) / TWO_PI
            best = turns
            best_info = {
                "span_ps": [win[i][0], win[j][0]],
                "turns": turns,
                "area_turns": area_turns,
                "residual": resid,
            }
            if turns >= 1.0 and win[i][0] <= 130.0 and abs(resid) <= 0.05:
                complete_consistent = True
        i = j + 1 if j > i else i + 1
    return {
        "id": pid,
        "largest_turns": round(best, 6),
        "info": best_info,
        "qualifying_complete": complete_consistent,
    }


if __name__ == "__main__":
    import sys

    for pid in sys.argv[1:]:
        print(quick_check(pid))
