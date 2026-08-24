#!/usr/bin/env python3
"""Create the registered W*=12 ps external 12-JSL Phase-B fixtures."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT.parent / "paper-sl-l0-20260824" / "inputs"
OUT = ROOT / "inputs" / "phase-b" / "12jsl-12ps"
MAP = ROOT / "analysis" / "phase-b-case-map.json"

CASES = {
    "logical1-read": SOURCE / "logical1-read.cir",
    "logical0-read": SOURCE / "logical0-read.cir",
}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    mapping: dict[str, str] = {}
    for case_id, source in CASES.items():
        destination = OUT / f"{case_id}.cir"
        text = source.read_text()
        updated, count = re.subn(r"96p \+100U 105p \+100U 106p 0", "96p +100U 108p +100U 109p 0", text)
        expected = 2 if case_id == "logical1-read" else 1
        if count != expected:
            raise ValueError(f"expected {expected} READ knot replacements in {source}, got {count}")
        updated = updated.replace(".include jjmit.cir", ".include ../../jjmit.cir")
        updated = updated.replace(".include ../../../../circuits/bvm/bvm_cell.cir", ".include ../../bvm_cell.cir")
        updated = updated.replace(
            "* PAPER-SL-L0:",
            "* BVM_JSL_READ_WIDTH_TO_QB_SFQ_V1 Phase-B W*=12ps:",
            1,
        )
        if destination.exists():
            if destination.read_text() != updated:
                raise SystemExit(f"existing generated deck differs from deterministic output: {destination}")
        else:
            destination.write_text(updated)
        mapping[case_id] = str(destination)
    MAP.write_text(json.dumps({"w_star_ps": 12, "source_fixture": str(SOURCE), "cases": mapping}, indent=2) + "\n")
    print(json.dumps(mapping, indent=2))


if __name__ == "__main__":
    main()
