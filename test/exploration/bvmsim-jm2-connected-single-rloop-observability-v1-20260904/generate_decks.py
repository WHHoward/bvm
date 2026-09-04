#!/usr/bin/env python3
"""Mechanically import the two validated JM2-connected JTL decks.

Only include paths are relocated for the new executed-deck location and new
.print expressions are appended.  The physical netlist body and inherited
stimulus are not retyped here.
"""

from __future__ import annotations

import hashlib
import re
from collections import Counter
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
EXP = Path(__file__).resolve().parent
OLD = REPO / "test/exploration/bvmsim-jm2-connected-single-ab-v1-20260903"

EXPECTED_OLD_HASH = {
    "S0-J-RLOOP": "28c4c99eaad687c8905226790bfec7a61a609d9680cf49b0030953d1ef0b07b6",
    "S1-J-RLOOP": "5d8ff1a9314136b9916ef2e472cc5c34688d1d580650e07d8cf04a1cd3f8ccd7",
}

NEW_PROBES = (
    "I(R_JM1|XBVM1)",
    "I(L_S1|XBVM1)",
    "I(L_S2|XBVM1)",
    "I(R_S|XBVM1)",
    "I(L_S3|XBVM1)",
    "I(R_SE|XBVM1)",
    "I(L_PSE|XBVM1)",
    "I(R_SL|XBVM1)",
    "V(R_JM1|XBVM1)",
    "V(R_S|XBVM1)",
    "V(L_S3|XBVM1)",
    "V(R_SE|XBVM1)",
    "V(L_PSE|XBVM1)",
    "V(L_S1|XBVM1)",
    "V(L_S2|XBVM1)",
    "V(L_PSL|XBVM1)",
    "V(R_SL|XBVM1)",
    "V(L_SL|XBVM1)",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def print_expressions(text: str) -> list[str]:
    result: list[str] = []
    for line in text.splitlines():
        if re.match(r"^\s*\.print\b", line, re.I):
            result.extend(re.findall(r"[IVP]\([^\s)]+(?:\|[^\s)]+)?\)", line))
    return result


def relocate_includes(text: str) -> str:
    replacements = {
        ".include ../../../../circuits/models/jjmit.cir":
        ".include ../../../../../circuits/models/jjmit.cir",
        ".include ../variants/bvm_jm2_connected.cir":
        ".include ../../../bvmsim-jm2-connected-single-ab-v1-20260903/variants/bvm_jm2_connected.cir",
        ".include ../../../../BVMSim/BQ.cir":
        ".include ../../../../../BVMSim/BQ.cir",
        ".include ../../../../BVMSim/library_josim/jtl2.cir":
        ".include ../../../../../BVMSim/library_josim/jtl2.cir",
    }
    for old, new in replacements.items():
        if text.count(old) != 1:
            raise RuntimeError(f"expected one include line, found {text.count(old)}: {old}")
        text = text.replace(old, new)
    return text


def add_probes(text: str) -> str:
    existing = print_expressions(text)
    counts = Counter(existing)
    missing = [probe for probe in NEW_PROBES if counts[probe] == 0]
    if any(counts[probe] > 0 for probe in NEW_PROBES):
        raise RuntimeError("new probe already exists in source deck")
    if not missing:
        raise RuntimeError("no new probes to add")
    block = "\n".join(
        (
            "* R-LOOP / SL passive-network observability extension; probe-only.",
            "* Direct element voltages are supported by JoSIM's hierarchical device lookup.",
            ".print " + " ".join(missing[:8]),
            ".print " + " ".join(missing[8:]),
        )
    )
    lines = text.splitlines()
    end_indices = [index for index, line in enumerate(lines) if line.strip().lower() == ".end"]
    if len(end_indices) != 1:
        raise RuntimeError(f"expected exactly one .end, found {len(end_indices)}")
    lines.insert(end_indices[0], block)
    return "\n".join(lines) + "\n"


def main() -> int:
    for condition, old_id in (("S0-J-RLOOP", "S0-J-JM2C"), ("S1-J-RLOOP", "S1-J-JM2C")):
        source = OLD / "runs" / old_id / "deck.cir"
        target = EXP / "runs" / condition / "deck.cir"
        if target.exists():
            raise RuntimeError(f"refusing to overwrite existing executed deck: {target}")
        source_hash = sha256(source)
        if source_hash != EXPECTED_OLD_HASH[condition]:
            raise RuntimeError(f"old authority hash changed for {source}: {source_hash}")
        text = source.read_text(encoding="utf-8")
        text = relocate_includes(text)
        text = add_probes(text)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        print(f"generated {target.relative_to(REPO)} from {source.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
