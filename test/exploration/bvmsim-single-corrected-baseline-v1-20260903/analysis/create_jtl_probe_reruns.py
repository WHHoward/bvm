#!/usr/bin/env python3
"""Create non-overwriting JTL-observability rerun decks.

The first corrected JTL runs were physically executed with the required
topology and model closure, but their decks did not print the six JTL
instances.  This script changes only the .print observables and creates new
input names; it never edits an existing deck or raw file.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path


EXP = Path(__file__).resolve().parents[1]
INPUTS = EXP / "inputs"
RUNS = EXP / "runs"

CASES = {
    "S0-J-CORRECTED-RERUN": "S0-J-CORRECTED",
    "S1-J-CORRECTED-RERUN": "S1-J-CORRECTED",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def jtl_print_block() -> str:
    lines = ["* RERUN OBSERVABILITY: JTL1..JTL6 B01/B02 phase and voltage."]
    for stage in range(1, 7):
        lines.append(
            f".print P(B01|XJTL1_{stage}) V(B01|XJTL1_{stage}) "
            f"P(B02|XJTL1_{stage}) V(B02|XJTL1_{stage})"
        )
    return "\n".join(lines) + "\n"


def build(source_path: Path, condition: str) -> str:
    source = source_path.read_text(encoding="utf-8")
    if "* RERUN OBSERVABILITY: JTL1..JTL6" in source:
        raise RuntimeError(f"source already contains rerun block: {source_path}")
    if source.count(".end") != 1:
        raise RuntimeError(f"expected one .end in {source_path}")
    if source.count("xjtl1_") != 6:
        raise RuntimeError(f"expected six JTL instances in {source_path}")
    if ".include ../../../../BVMSim/library_josim/jtl2.cir" not in source:
        raise RuntimeError(f"historical JTL include missing: {source_path}")
    if ".tran 0.1p 200p" not in source:
        raise RuntimeError(f"fixed transient line missing: {source_path}")
    marker = f"* JTL probe-only rerun: {condition}; no physics/topology change.\n"
    return source.replace(".end\n", marker + jtl_print_block() + ".end\n", 1)


def main() -> int:
    for condition, source_condition in CASES.items():
        source_path = RUNS / source_condition / "deck.cir"
        destination = INPUTS / f"{condition}.cir"
        if not source_path.is_file():
            raise RuntimeError(f"missing preserved source deck: {source_path}")
        content = build(source_path, condition)
        if destination.exists():
            if destination.read_text(encoding="utf-8") != content:
                raise RuntimeError(f"refusing to overwrite {destination}")
        else:
            destination.write_text(content, encoding="utf-8")
        print(f"{condition} {sha256(destination)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
