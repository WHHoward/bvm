#!/usr/bin/env python3
"""Build the preregistered M1-M5 fixtures independently from accepted parents."""

from __future__ import annotations

import csv
import hashlib
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
EXP = ROOT / "test/exploration/parallel-qb-jtl-interface-mechanism-20260824"
INPUTS = EXP / "inputs"
Q0_DECK = ROOT / "test/exploration/qb-q0-standalone-current-quantized-event-20260824/inputs/scaled-iin-68p4u.cir"
Q0_RAW = ROOT / "test/exploration/qb-q0-standalone-current-quantized-event-20260824/raw/scaled/iin-68p4u.csv"
JJMIT = ROOT / "circuits/models/jjmit.cir"
BQ = ROOT / "circuits/qb/bq_cell.cir"
JTL = ROOT / "circuits/standard/JTL.cir"


STANDARD_JTL_BLOCK = r'''
.include JTL.cir
XJTL1 JTL_IN   JTL_MID THmitll_JTL
XJTL2 JTL_MID  JTL_OUT THmitll_JTL
R_TERM JTL_OUT 0 1

.print P(B1|XJTL1) V(B1|XJTL1) I(B1|XJTL1) P(B2|XJTL1) V(B2|XJTL1) I(B2|XJTL1)
.print P(B1|XJTL2) V(B1|XJTL2) I(B1|XJTL2) P(B2|XJTL2) V(B2|XJTL2) I(B2|XJTL2)
.print I(L1|XJTL1) I(L2|XJTL1) I(L3|XJTL1) I(L4|XJTL1) I(IB1|XJTL1) I(RB1|XJTL1) I(RB2|XJTL1)
.print I(L1|XJTL2) I(L2|XJTL2) I(L3|XJTL2) I(L4|XJTL2) I(IB1|XJTL2) I(RB1|XJTL2) I(RB2|XJTL2)
.print V(JTL_MID) V(JTL_OUT) I(R_TERM) I(L1|XJTL1)
'''.strip()

SCALED_JTL = r'''
* Coherently scaled THmitll diagnostic: s=54/250=0.216.
.subckt THmitll_JTL_SCALED a q
B1 1 2 jjmit area=0.54
B2 5 6 jjmit area=0.54
IB1 0 4 pwl(0 0 5p 75.6u)
LB1 4 3 10.8148148p
L1 a 1 9.5833333p
L2 1 3 9.6666667p
L3 3 5 9.6388889p
L4 5 q 9.5925926p
LP1 2 0 1.4523148p
LP2 6 0 1.4458333p
RB1 1 101 12.7035267
LRB1 101 0 9.4923074p
RB2 5 105 12.7035267
LRB2 105 0 9.4923074p
.ends
'''.strip()

JTL_PROBES = r'''
.print P(B1|XJTL1) V(B1|XJTL1) I(B1|XJTL1) P(B2|XJTL1) V(B2|XJTL1) I(B2|XJTL1)
.print P(B1|XJTL2) V(B1|XJTL2) I(B1|XJTL2) P(B2|XJTL2) V(B2|XJTL2) I(B2|XJTL2)
.print I(L1|XJTL1) I(L2|XJTL1) I(L3|XJTL1) I(L4|XJTL1) I(IB1|XJTL1) I(RB1|XJTL1) I(RB2|XJTL1)
.print I(L1|XJTL2) I(L2|XJTL2) I(L3|XJTL2) I(L4|XJTL2) I(IB1|XJTL2) I(RB1|XJTL2) I(RB2|XJTL2)
.print V(JTL_MID) V(JTL_OUT) I(R_TERM) I(L1|XJTL1)
'''.strip()


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def q0_vout_pwl() -> str:
    with Q0_RAW.open(newline="") as f:
        rows = list(csv.DictReader(f))
    pairs = []
    for row in rows:
        t_ps = float(row["time"]) * 1e12
        value = float(row["V(OUT)"])
        pairs.append(f"{t_ps:.10g}p {value:.12g}")
    return " ".join(pairs)


def source_without_end(text: str) -> str:
    lines = text.rstrip().splitlines()
    if not lines or lines[-1].strip().lower() != ".end":
        raise ValueError("parent deck must end with .end")
    return "\n".join(lines[:-1])


def copy_models(target: Path, *, jtl: bool = False, scaled: bool = False) -> None:
    target.mkdir(parents=True, exist_ok=True)
    shutil.copy2(JJMIT, target / "jjmit.cir")
    shutil.copy2(BQ, target / "bq_cell.cir")
    if jtl:
        if scaled:
            (target / "JTL_SCALED.cir").write_text(SCALED_JTL + "\n")
        else:
            shutil.copy2(JTL, target / "JTL.cir")


def q0_body() -> str:
    return source_without_end(Q0_DECK.read_text())


def q0_fixture(kind: str) -> str:
    body = q0_body()
    if kind == "M2-riso10":
        body = body.replace(".end", "")
        body += "\nR_ISO OUT JTL_IN 10\n" + STANDARD_JTL_BLOCK + "\n.print I(R_ISO) V(JTL_IN)\n"
    elif kind == "M3-rseries10":
        body = body.replace("R_LOAD OUT 0 10\n", "", 1)
        body = body.replace(" I(R_LOAD)", "", 1)
        body += "\nR_SER OUT JTL_IN 10\n" + STANDARD_JTL_BLOCK + "\n.print I(R_SER) V(JTL_IN)\n"
    elif kind == "M4-liso10p":
        body += "\nL_ISO OUT JTL_IN 10p\n" + STANDARD_JTL_BLOCK + "\n.print I(L_ISO) V(JTL_IN)\n"
    elif kind == "M5-q0-scaled":
        body += "\n.include JTL_SCALED.cir\n"
        body += "\nXJTL1 OUT JTL_MID THmitll_JTL_SCALED\nXJTL2 JTL_MID JTL_OUT THmitll_JTL_SCALED\nR_TERM JTL_OUT 0 4.6296296\n"
        body += JTL_PROBES
    else:
        raise ValueError(kind)
    return body + "\n.end\n"


def m1_fixture() -> str:
    return (
        ".include jjmit.cir\n.include JTL.cir\n"
        "V_REPLAY JTL_IN 0 pwl(" + q0_vout_pwl() + ")\n"
        "XJTL1 JTL_IN JTL_MID THmitll_JTL\n"
        "XJTL2 JTL_MID JTL_OUT THmitll_JTL\n"
        "R_TERM JTL_OUT 0 1\n"
        ".tran 0.1p 300p\n"
        ".print I(V_REPLAY) V(JTL_IN) V(JTL_MID) V(JTL_OUT)\n"
        + JTL_PROBES
        + "\n.end\n"
    )


def m5_positive_fixture() -> str:
    return (
        ".include jjmit.cir\n.include JTL_SCALED.cir\n"
        "V_IN IN 0 pwl(0 0 10p 0 11p 1.5m 13p 1.5m 14p 0 170p 0)\n"
        "R_IN IN N1 3\nL_IN N1 SFQ_IN 0.5p\n"
        "XJTL1 SFQ_IN JTL_MID THmitll_JTL_SCALED\n"
        "XJTL2 JTL_MID JTL_OUT THmitll_JTL_SCALED\n"
        "R_TERM JTL_OUT 0 4.6296296\n"
        ".tran 0.0125p 170p\n"
        ".print I(V_IN) V(SFQ_IN) V(JTL_MID) V(JTL_OUT) I(R_IN) I(L_IN) I(R_TERM)\n"
        + JTL_PROBES
        + "\n.end\n"
    )


def write_case(name: str, deck: str, *, jtl: bool = False, scaled: bool = False) -> dict:
    target = INPUTS / name
    copy_models(target, jtl=jtl, scaled=scaled)
    deck_path = target / ("positive-control.cir" if name == "M5-positive-control" else "main.cir")
    deck_path.write_text(deck)
    return {
        "name": name,
        "deck": str(deck_path.relative_to(ROOT)),
        "deck_sha256": sha256(deck_path),
        "model_sha256": sha256(target / "jjmit.cir"),
        "bq_sha256": sha256(target / "bq_cell.cir"),
        "jtl_sha256": sha256(target / ("JTL_SCALED.cir" if scaled else "JTL.cir")) if jtl else None,
    }


def main() -> None:
    cases = [
        write_case("M1-ideal-replay", m1_fixture(), jtl=True),
        write_case("M2-riso10", q0_fixture("M2-riso10"), jtl=True),
        write_case("M3-rseries10", q0_fixture("M3-rseries10"), jtl=True),
        write_case("M4-liso10p", q0_fixture("M4-liso10p"), jtl=True),
        write_case("M5-positive-control", m5_positive_fixture(), jtl=True, scaled=True),
        write_case("M5-q0-scaled", q0_fixture("M5-q0-scaled"), jtl=True, scaled=True),
    ]
    manifest = {
        "parent_head": "d05d96ab3eb13dc19af9dbaa0b7a5d3ac92ac63d",
        "q0_deck": str(Q0_DECK.relative_to(ROOT)),
        "q0_deck_sha256": sha256(Q0_DECK),
        "q0_raw": str(Q0_RAW.relative_to(ROOT)),
        "q0_raw_sha256": sha256(Q0_RAW),
        "jtl_source": str(JTL.relative_to(ROOT)),
        "jtl_source_sha256": sha256(JTL),
        "cases": cases,
    }
    out = INPUTS / "manifest.json"
    out.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
