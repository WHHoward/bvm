#!/usr/bin/env python3
"""Build the single preregistered PAPER-SL-Q3 input fixture.

The four source decks are copied byte-for-byte from the accepted Q2 40-uA
fixture.  Only the local QB snapshot changes the native L1 value.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "test/exploration/paper-sl-q2-20260824/inputs/40u"
TARGET = EXP / "inputs/l1-4p5"
CASES = [
    "paper-j1-logical1-read0-control.cir",
    "paper-j0-logical0-read0-control.cir",
    "paper-j0-logical0-read.cir",
    "paper-j1-logical1-read.cir",
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    TARGET.mkdir(parents=True, exist_ok=True)

    source_bq = SOURCE / "bq_cell.cir"
    original = source_bq.read_text()
    old = "L1 2 3 3.91p"
    new = "L1 2 3 4.50p"
    if original.count(old) != 1:
        raise RuntimeError(f"expected exactly one L1 replacement, found {original.count(old)}")
    modified = original.replace(old, new)
    (TARGET / "bq_cell.cir").write_text(modified)
    shutil.copy2(SOURCE / "jjmit.cir", TARGET / "jjmit.cir")

    records = {
        "source_q2_40u": {},
        "generated": {},
        "replay_identity": "all source decks are copied byte-identically from PAPER-SL-Q2/inputs/40u",
        "only_circuit_change": {"file": "bq_cell.cir", "from": old, "to": new},
    }
    for name in ["bq_cell.cir", "jjmit.cir", *CASES]:
        src = SOURCE / name
        dst = TARGET / name
        if name in CASES:
            shutil.copy2(src, dst)
        records["source_q2_40u"][name] = sha256(src)
        records["generated"][name] = sha256(dst)
        if name in CASES and src.read_bytes() != dst.read_bytes():
            raise RuntimeError(f"source deck changed during copy: {name}")

    (EXP / "inputs/deck-hashes.json").write_text(json.dumps(records, indent=2) + "\n")
    print(json.dumps(records, indent=2))


if __name__ == "__main__":
    main()
