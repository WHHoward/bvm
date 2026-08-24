#!/usr/bin/env python3
"""Build Q5 directly from the accepted Q2 40-uA fixture."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
EXP = ROOT / "test/exploration/paper-sl-q5-l1-l2-factorial-20260824"
SOURCE = ROOT / "test/exploration/paper-sl-q2-20260824/inputs/40u"
TARGET = EXP / "inputs/q5-l1-4p50-l2-4p50"
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
    if source_text.count("L1 2 3 3.91p") != 1 or source_text.count("L2 3 4 3.91p") != 1:
        raise SystemExit("Q2 source does not have the expected single L1/L2 lines")
    generated = source_text.replace("L1 2 3 3.91p", "L1 2 3 4.50p", 1)
    generated = generated.replace("L2 3 4 3.91p", "L2 3 4 4.50p", 1)
    if generated.count("L1 2 3 4.50p") != 1 or generated.count("L2 3 4 4.50p") != 1:
        raise SystemExit("Q5 did not produce exactly the requested L1/L2 point")
    if "L1 2 3 3.91p" in generated or "L2 3 4 3.91p" in generated:
        raise SystemExit("Q5 retained an old L1/L2 line")

    TARGET.mkdir(parents=True, exist_ok=True)
    (TARGET / "bq_cell.cir").write_text(generated)
    shutil.copy2(SOURCE / "jjmit.cir", TARGET / "jjmit.cir")
    for name in DECKS:
        shutil.copy2(SOURCE / name, TARGET / name)
        if (TARGET / name).read_bytes() != (SOURCE / name).read_bytes():
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
        "only_circuit_changes": [
            {"file": "bq_cell.cir", "from": "L1 2 3 3.91p", "to": "L1 2 3 4.50p"},
            {"file": "bq_cell.cir", "from": "L2 3 4 3.91p", "to": "L2 3 4 4.50p"},
        ],
    }
    (EXP / "inputs/deck-hashes.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
