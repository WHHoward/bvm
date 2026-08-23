#!/usr/bin/env python3
"""Generate classic native JoSIM viewers for the accepted PAPER-SL-L0 raw."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[2]
SOURCE = ROOT.parent / "paper-sl-l0-20260824"
OUT = ROOT / "plots/paper-sl-l0-classic"
PLOTTER = REPO / "scripts/josim-plot2.py"
CASES = ["logical1-read", "logical0-read", "logical1-read0-control", "logical0-read0-control"]
SIGNALS = [
    "I(I_WL1)", "I(I_SE1)",
    "P(B_JS1|XBVM1)", "V(B_JS1|XBVM1)",
    "P(B_JS2|XBVM1)", "V(B_JS2|XBVM1)",
    "V(N6|XBVM1)", "V(SL1)",
    "I(L_PSL|XBVM1)", "I(L_SL|XBVM1)",
    "I(B_LD1)", "P(B_LD1)", "V(B_LD1)", "I(B_LD12)",
]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for case in CASES:
        source = SOURCE / f"raw/{case}/run-01.csv"
        target = OUT / f"{case}.html"
        command = [
            sys.executable, str(PLOTTER), str(source),
            "-t", "sep_comb", "-c", "dark", "-j", "2pi",
            "-s", *SIGNALS,
            "-x", str(target),
            "-w", f"PAPER-SL-L0 classic viewer — {case}",
        ]
        subprocess.run(command, check=True)
        print(target)


if __name__ == "__main__":
    main()

