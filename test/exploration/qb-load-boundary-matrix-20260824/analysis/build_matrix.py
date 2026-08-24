#!/usr/bin/env python3
"""Build A-E independently from the accepted Q0 and Q5 source fixtures."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
EXP = ROOT / "test/exploration/qb-load-boundary-matrix-20260824"
TARGET_ROOT = EXP / "inputs-v2"
Q0 = ROOT / "test/exploration/qb-q0-standalone-current-quantized-event-20260824/inputs"
Q5 = ROOT / "test/exploration/paper-sl-q5-l1-l2-factorial-20260824/inputs/q5-l1-4p50-l2-4p50"
JTL = ROOT / "circuits/standard/JTL.cir"

Q0_DECK = "scaled-iin-68p4u.cir"
Q5_DECKS = (
    "paper-j1-logical1-read.cir",
    "paper-j0-logical0-read.cir",
    "paper-j1-logical1-read0-control.cir",
    "paper-j0-logical0-read0-control.cir",
)

JTL_BLOCK = r'''
.include JTL.cir

* Frozen R11-A standard two-cell chain, directly driven by QB OUT.
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
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def source_without_end(text: str) -> str:
    lines = text.rstrip().splitlines()
    if not lines or lines[-1].strip() != ".end":
        raise SystemExit("source deck must end in one .end")
    return "\n".join(lines[:-1])


def transform(text: str, *, retain_load: bool, attach_jtl: bool) -> str:
    if text.count("R_LOAD OUT 0 10") != 1:
        raise SystemExit("source deck must contain exactly one 10-ohm load")
    if not retain_load:
        text = text.replace("R_LOAD OUT 0 10\n", "", 1)
        if text.count("I(R_LOAD)") != 1:
            raise SystemExit("source deck must have exactly one removable R_LOAD probe")
        text = text.replace(" I(R_LOAD)", "", 1)
    base = source_without_end(text)
    if attach_jtl:
        if ".include JTL.cir" in base or "XJTL1" in base:
            raise SystemExit("source deck already contains JTL content")
        base += "\n" + JTL_BLOCK.strip("\n")
    return base + "\n.end\n"


def write_fixture(name: str, source_dir: Path, source_decks: tuple[str, ...], retain_load: bool, attach_jtl: bool) -> dict:
    target = TARGET_ROOT / name
    target.mkdir(parents=True, exist_ok=True)
    for model in ("bq_cell.cir", "jjmit.cir"):
        shutil.copy2(source_dir / model, target / model)
    if attach_jtl:
        shutil.copy2(JTL, target / "JTL.cir")
    generated = []
    for deck in source_decks:
        source = source_dir / deck
        text = source.read_text()
        out_name = deck
        target_deck = target / out_name
        target_deck.write_text(transform(text, retain_load=retain_load, attach_jtl=attach_jtl))
        generated.append({
            "source": str(source.relative_to(ROOT)),
            "source_sha256": sha256(source),
            "generated": str(target_deck.relative_to(ROOT)),
            "generated_sha256": sha256(target_deck),
        })
    return {
        "source": str(source_dir.relative_to(ROOT)),
        "target": str(target.relative_to(ROOT)),
        "retain_load": retain_load,
        "attach_jtl": attach_jtl,
        "source_decks": generated,
        "bq_cell_sha256": sha256(target / "bq_cell.cir"),
        "jjmit_sha256": sha256(target / "jjmit.cir"),
        "jtl_sha256": sha256(target / "JTL.cir") if attach_jtl else None,
    }


def main() -> None:
    fixtures = {
        "A-q0-open": write_fixture("A-q0-open", Q0, (Q0_DECK,), False, False),
        "B-q0-jtl-only": write_fixture("B-q0-jtl-only", Q0, (Q0_DECK,), False, True),
        "C-q0-10ohm-parallel-jtl": write_fixture("C-q0-10ohm-parallel-jtl", Q0, (Q0_DECK,), True, True),
        "D-q5-open": write_fixture("D-q5-open", Q5, Q5_DECKS, False, False),
        "E-q5-jtl-only": write_fixture("E-q5-jtl-only", Q5, Q5_DECKS, False, True),
    }
    manifest = {
        "parent_head": "30590c9d9d4831f98c2a3f1db28ee7f6813eee59",
        "fixtures": fixtures,
        "jtl_source": str(JTL.relative_to(ROOT)),
        "q0_source": str(Q0.relative_to(ROOT)),
        "q5_source": str(Q5.relative_to(ROOT)),
        "independent_outputs": True,
    }
    (TARGET_ROOT / "fixture-hashes.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
