#!/usr/bin/env python3
"""Build the Q4 fixture from the accepted Q2 40-uA input snapshot.

The only circuit edit is the Q2 BQ subcircuit line changing L2 from 3.91 pH
to 4.50 pH.  In particular, this script deliberately does not derive the
deck from the Q3 sibling fixture, where L1 is 4.50 pH.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
EXP = ROOT / "test/exploration/paper-sl-q4-l1-l2-placement-20260824"
SOURCE = ROOT / "test/exploration/paper-sl-q2-20260824/inputs/40u"
TARGET = EXP / "inputs/q4-l1-3p91-l2-4p50"

DECKS = (
    "paper-j1-logical1-read0-control.cir",
    "paper-j0-logical0-read0-control.cir",
    "paper-j0-logical0-read.cir",
    "paper-j1-logical1-read.cir",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    source_bq = SOURCE / "bq_cell.cir"
    source_text = source_bq.read_text()
    if source_text.count("L1 2 3 3.91p") != 1:
        raise SystemExit("Q2 source does not contain exactly one L1=3.91p line")
    if source_text.count("L2 3 4 3.91p") != 1:
        raise SystemExit("Q2 source does not contain exactly one L2=3.91p line")

    generated_bq = source_text.replace("L2 3 4 3.91p", "L2 3 4 4.50p", 1)
    if generated_bq.count("L1 2 3 3.91p") != 1:
        raise SystemExit("Q4 accidentally changed L1")
    if generated_bq.count("L2 3 4 4.50p") != 1:
        raise SystemExit("Q4 did not produce the requested L2")

    TARGET.mkdir(parents=True, exist_ok=True)
    (TARGET / "bq_cell.cir").write_text(generated_bq)
    shutil.copy2(SOURCE / "jjmit.cir", TARGET / "jjmit.cir")
    for name in DECKS:
        source_deck = SOURCE / name
        target_deck = TARGET / name
        shutil.copy2(source_deck, target_deck)
        if source_deck.read_bytes() != target_deck.read_bytes():
            raise SystemExit(f"deck copy changed bytes: {name}")

    manifest = {
        "source": {
            "directory": str(SOURCE.relative_to(ROOT)),
            "bq_cell_sha256": sha256(source_bq),
            "jjmit_sha256": sha256(SOURCE / "jjmit.cir"),
            "decks_sha256": {name: sha256(SOURCE / name) for name in DECKS},
        },
        "generated": {
            "directory": str(TARGET.relative_to(ROOT)),
            "bq_cell_sha256": sha256(TARGET / "bq_cell.cir"),
            "jjmit_sha256": sha256(TARGET / "jjmit.cir"),
            "decks_sha256": {name: sha256(TARGET / name) for name in DECKS},
        },
        "only_circuit_change": {
            "file": "bq_cell.cir",
            "from": "L2 3 4 3.91p",
            "to": "L2 3 4 4.50p",
            "L1_unchanged": True,
        },
    }
    (EXP / "inputs/deck-hashes.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
