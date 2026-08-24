#!/usr/bin/env python3
"""Build Q6 by adding only the frozen R11-A JTL chain to accepted Q5 decks."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
EXP = ROOT / "test/exploration/paper-sl-q6-qb-jtl-compatibility-20260824"
SOURCE = ROOT / "test/exploration/paper-sl-q5-l1-l2-factorial-20260824/inputs/q5-l1-4p50-l2-4p50"
TARGET = EXP / "inputs/q6-q5-to-two-cell-jtl"
JTL_SOURCE = ROOT / "circuits/standard/JTL.cir"
DECKS = (
    "paper-j1-logical1-read0-control.cir",
    "paper-j1-logical1-read.cir",
    "paper-j0-logical0-read.cir",
    "paper-j0-logical0-read0-control.cir",
)

JTL_BLOCK = r'''
.include JTL.cir

* Q6 only: direct QB OUT -> standard JTL input, with Q5 R_LOAD retained.
XJTL1 OUT      JTL_MID THmitll_JTL
XJTL2 JTL_MID  JTL_OUT THmitll_JTL
R_TERM JTL_OUT 0 1

.print P(B1|XJTL1) V(B1|XJTL1) I(B1|XJTL1) P(B2|XJTL1) V(B2|XJTL1) I(B2|XJTL1)
.print P(B1|XJTL2) V(B1|XJTL2) I(B1|XJTL2) P(B2|XJTL2) V(B2|XJTL2) I(B2|XJTL2)
.print I(L1|XJTL1) I(L2|XJTL1) I(L3|XJTL1) I(L4|XJTL1) I(IB1|XJTL1) I(RB1|XJTL1) I(RB2|XJTL1)
.print I(L1|XJTL2) I(L2|XJTL2) I(L3|XJTL2) I(L4|XJTL2) I(IB1|XJTL2) I(RB1|XJTL2) I(RB2|XJTL2)
.print V(JTL_MID) V(JTL_OUT) I(R_TERM) I(L1|XJTL1)
'''


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def add_jtl(source_text: str) -> str:
    if source_text.count(".include bq_cell.cir") != 1:
        raise SystemExit("Q5 deck does not have exactly one local bq_cell include")
    if source_text.count("R_LOAD OUT 0 10") != 1:
        raise SystemExit("Q5 deck does not have exactly one retained 10-ohm load")
    if source_text.count(".tran 0.0125p 170p") != 1:
        raise SystemExit("Q5 timestep/stop is not frozen")
    if source_text.count("\n.end") != 1 or not source_text.rstrip().endswith(".end"):
        raise SystemExit("Q5 deck must have exactly one terminal .end")
    if "XJTL1" in source_text or "THmitll_JTL" in source_text:
        raise SystemExit("Q5 deck already contains JTL content")
    lines = source_text.rstrip().splitlines()
    if lines[-1].strip() != ".end":
        raise SystemExit("Q5 deck terminal line is not .end")
    base = "\n".join(lines[:-1])
    return base + "\n" + JTL_BLOCK.strip("\n") + "\n.end\n"


def main() -> None:
    TARGET.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SOURCE / "bq_cell.cir", TARGET / "bq_cell.cir")
    shutil.copy2(SOURCE / "jjmit.cir", TARGET / "jjmit.cir")
    shutil.copy2(JTL_SOURCE, TARGET / "JTL.cir")
    source_hashes = {}
    generated_hashes = {}
    for name in DECKS:
        source = SOURCE / name
        text = source.read_text()
        source_hashes[name] = sha256(source)
        generated = add_jtl(text)
        target = TARGET / name
        target.write_text(generated)
        generated_hashes[name] = sha256(target)

    manifest = {
        "parent_head": "b92fdb7a37b17cadaa2e9bc96f1689bf45178ceb",
        "source": {
            "directory": str(SOURCE.relative_to(ROOT)),
            "bq_cell_sha256": sha256(SOURCE / "bq_cell.cir"),
            "jjmit_sha256": sha256(SOURCE / "jjmit.cir"),
            "decks_sha256": source_hashes,
        },
        "generated": {
            "directory": str(TARGET.relative_to(ROOT)),
            "bq_cell_sha256": sha256(TARGET / "bq_cell.cir"),
            "jjmit_sha256": sha256(TARGET / "jjmit.cir"),
            "jtl_sha256": sha256(TARGET / "JTL.cir"),
            "decks_sha256": generated_hashes,
        },
        "coupling_change": {
            "connection": "OUT -> XJTL1.a -> XJTL1.q/JTL_MID -> XJTL2.a -> XJTL2.q/JTL_OUT",
            "q5_load": "R_LOAD OUT 0 10 retained in parallel",
            "jtl_termination": "R_TERM JTL_OUT 0 1 retained",
            "extra_conditioner": False,
        },
    }
    (EXP / "inputs/fixture-hashes.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
