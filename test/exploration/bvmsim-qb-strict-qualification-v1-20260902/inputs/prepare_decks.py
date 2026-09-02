#!/usr/bin/env python3
"""Derive the Stage-A migrated decks from the preserved BVMSim fixture.

The source fixture is read-only.  This script performs only the declared
packaging changes: shared jjmit include, imported QB subcircuit, external
QB-bias source, diagnostic print expansion, and the S1 timestep change.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
SOURCE = REPO / "BVMSim" / "test_bvm_mixed_0.cir"
EXPECTED_SOURCE_SHA256 = "09b30458cf2bec3fbe85221e9f34661ecee4c6e28aed18c54aaa30a94ad1f948"

PRINT_BLOCK = """.print I(I_WL1) I(I_BL1) I(I_SE1)
.print I(BVMOUT)
.print V(QBIN) V(QBOUT)
.print V(O1) V(O2) V(O3) V(O4) V(O5) V(O6)
.print I(LIN|XBQ1) I(BJS|XBQ1) P(BJS|XBQ1) V(BJS|XBQ1)
.print I(BJ1|XBQ1) P(BJ1|XBQ1) V(BJ1|XBQ1) I(RJ1|XBQ1)
.print I(L1|XBQ1) I(I_QB_BIAS) I(L2|XBQ1)
.print I(BJ2|XBQ1) P(BJ2|XBQ1) V(BJ2|XBQ1) I(RJ2|XBQ1)
.print I(L3|XBQ1)
.print P(B01|XJTL1_1) V(B01|XJTL1_1) P(B02|XJTL1_1) V(B02|XJTL1_1)
.print P(B01|XJTL1_2) V(B01|XJTL1_2) P(B02|XJTL1_2) V(B02|XJTL1_2)
.print P(B01|XJTL1_3) V(B01|XJTL1_3) P(B02|XJTL1_3) V(B02|XJTL1_3)
.print P(B01|XJTL1_4) V(B01|XJTL1_4) P(B02|XJTL1_4) V(B02|XJTL1_4)
.print P(B01|XJTL1_5) V(B01|XJTL1_5) P(B02|XJTL1_5) V(B02|XJTL1_5)
.print P(B01|XJTL1_6) V(B01|XJTL1_6) P(B02|XJTL1_6) V(B02|XJTL1_6)"""


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def derive(source_text: str, *, timestep: str) -> str:
    text = source_text
    replacements = {
        ".include ./bvm_cell.cir": ".include ../../../../circuits/models/jjmit.cir\n.include ../../../../BVMSim/bvm_cell.cir",
        ".include ./BQ.cir": ".include ../../../../circuits/qb/bq_cell_bvmsim_v1.cir",
        ".include ./library_josim/jtl2.cir": ".include ../../../../BVMSim/library_josim/jtl2.cir",
        "xBQ1 QBin QBout BQ": "I_QB_BIAS 0 QB_BIAS pwl(0 0 1p 250u)\nxBQ1 QBin QBout QB_BIAS BQ_BVMSIM_V1",
        ".tran 0.1p 200p 45p": timestep,
    }
    for old, new in replacements.items():
        if old not in text:
            raise RuntimeError(f"source token not found: {old}")
        text = text.replace(old, new, 1)

    text, model_count = re.subn(r"(?m)^\.model jjmit[^\n]*\n?", "", text)
    if model_count != 1:
        raise RuntimeError(f"expected one historical local jjmit model, found {model_count}")

    start_token = "\n.print I(I_WL1) I(I_BL1) I(I_SE1)\n"
    start = text.find(start_token)
    end = text.find("\n.end", start)
    if start < 0 or end < 0:
        raise RuntimeError("active print block not found")
    text = text[:start] + "\n" + PRINT_BLOCK + text[end:]

    required = (
        "XBVM1 WL1 BL1 SE1 SL1 BVM",
        "XBVM4 WL4 BL4 SE4 SL4 BVM",
        "BVMout    nld4_21 QBin jjmit area=3.2",
        "xjtl1_6 o5 o6 jtl",
        "RBQ1 o6 0 10",
        "I_QB_BIAS 0 QB_BIAS pwl(0 0 1p 250u)",
        "xBQ1 QBin QBout QB_BIAS BQ_BVMSIM_V1",
        ".include ../../../../BVMSim/library_josim/jtl2.cir",
    )
    missing = [token for token in required if token not in text]
    if missing:
        raise RuntimeError(f"derived deck missing required fixture tokens: {missing}")
    if "xBQ1 QBin QBout BQ" in text or re.search(r"(?m)^\.model jjmit", text):
        raise RuntimeError("derived deck still contains the historical QB/model packaging")
    return text


def main() -> None:
    actual = sha256(SOURCE)
    if actual != EXPECTED_SOURCE_SHA256:
        raise SystemExit(f"source hash changed: {actual} != {EXPECTED_SOURCE_SHA256}")
    source_text = SOURCE.read_text(encoding="utf-8")
    m0 = derive(source_text, timestep=".tran 0.1p 200p 45p")
    s1 = derive(source_text, timestep=".tran 0.025p 200p")
    output_dir = EXP / "migrated"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "m0_bvmsim_qb.cir").write_text(m0, encoding="utf-8")
    (output_dir / "s1_bvmsim_qb.cir").write_text(s1, encoding="utf-8")
    print(f"wrote {output_dir / 'm0_bvmsim_qb.cir'} sha256={sha256(output_dir / 'm0_bvmsim_qb.cir')}")
    print(f"wrote {output_dir / 's1_bvmsim_qb.cir'} sha256={sha256(output_dir / 's1_bvmsim_qb.cir')}")


if __name__ == "__main__":
    main()
