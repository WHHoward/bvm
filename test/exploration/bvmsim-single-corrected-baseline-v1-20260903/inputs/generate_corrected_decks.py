#!/usr/bin/env python3
"""Create task-local corrected single-BVM decks without touching old runs."""

from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
BASELINE = REPO / "test/exploration/bvmsim-bvm-qb-jtl-operational-baseline-v1-20260903"
INPUT_DIR = EXP / "inputs"

HISTORICAL_BVM = REPO / "BVMSim/bvm_cell.cir"
HISTORICAL_QB = REPO / "BVMSim/BQ.cir"
HISTORICAL_JTL = REPO / "BVMSim/library_josim/jtl2.cir"
SHARED_JJMIT = REPO / "circuits/models/jjmit.cir"

CONDITIONS = {
    "S0-R-CORRECTED": {"source": "S0-R", "load": "direct", "write": "-100u"},
    "S1-R-CORRECTED": {"source": "S1-R", "load": "direct", "write": "+100u"},
    "S0-J-CORRECTED": {"source": "S0-J", "load": "jtl", "write": "-100u"},
    "S1-J-CORRECTED": {"source": "S1-J", "load": "jtl", "write": "+100u"},
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relpath(path: Path, directory: Path) -> str:
    return os.path.relpath(path, directory)


def replace_include_block(source: str, *, with_jtl: bool) -> str:
    match = re.search(r"(?m)^(?:\.include .*\n)+", source)
    if match is None:
        raise RuntimeError("baseline deck has no contiguous include block")
    sources = [SHARED_JJMIT, HISTORICAL_BVM, HISTORICAL_QB]
    if with_jtl:
        sources.append(HISTORICAL_JTL)
    block = "".join(f".include {relpath(path, INPUT_DIR)}\n" for path in sources)
    return source[: match.start()] + block + source[match.end() :]


def corrected_stimulus(write_amp: str) -> str:
    return (
        "* CORRECTED protocol: WRITE = WL+BL; READ = WL+SE; BL=0 during READ.\n"
        f"I_WL1 0 WL1 pwl(0 0 50p 0 51p {write_amp} 60p {write_amp} 61p 0 70p 0 71p 100u 80p 100u 81p 0 200p 0)\n"
        f"I_BL1 0 BL1 pwl(0 0 50p 0 51p {write_amp} 60p {write_amp} 61p 0 70p 0 71p 0 80p 0 81p 0 200p 0)\n"
        "I_SE1 0 SE1 pwl(0 0 50p 0 51p 0 60p 0 61p 0 70p 0 71p 100u 80p 100u 81p 0 200p 0)\n"
    )


def replace_stimulus(source: str, write_amp: str) -> str:
    pattern = re.compile(
        r"(?m)^\* Existing BVMSim logical-[01] write:[^\n]*\n"
        r"I_WL1 [^\n]*\n"
        r"I_BL1 [^\n]*\n"
        r"\* Existing BVMSim positive READ:[^\n]*\n"
        r"I_SE1 [^\n]*\n"
    )
    updated, count = pattern.subn(corrected_stimulus(write_amp), source, count=1)
    if count != 1:
        raise RuntimeError("baseline deck stimulus block was not found exactly once")
    return updated


def make_deck(condition: str, config: dict[str, str]) -> str:
    baseline_path = BASELINE / "runs/single" / config["source"] / "deck.cir"
    if not baseline_path.is_file():
        raise RuntimeError(f"missing baseline deck: {baseline_path}")
    source = baseline_path.read_text(encoding="utf-8")
    source = re.sub(r"\A\* GENERATED OPERATIONAL BASELINE:.*\n\* source_class=.*\n", "", source)
    source = source.replace("BQ_BVMSIM_V1", "original BVMSim BQ")
    source = replace_include_block(source, with_jtl=config["load"] == "jtl")
    source = replace_stimulus(source, config["write"])
    source = re.sub(r"(?m)^\.tran\s+[^\n]+$", ".tran 0.1p 200p", source)
    metadata = (
        f"* CORRECTED SINGLE-BVM BASELINE: {condition}\n"
        "* source_class=HISTORICAL_BVMSIM; old single raw remains invalid history\n"
        "* corrected_read=WL+SE at 70--81 ps; corrected_write=WL+BL at 50--61 ps\n"
        "* model_closure=top-level circuits/models/jjmit.cir + historical local QB/JTL models\n"
    )
    result = metadata + source

    required = (
        ".include " + relpath(SHARED_JJMIT, INPUT_DIR),
        ".include " + relpath(HISTORICAL_BVM, INPUT_DIR),
        ".include " + relpath(HISTORICAL_QB, INPUT_DIR),
        "XBVM1 WL1 BL1 SE1 SL1 BVM",
        "BVMout   nld4_21 QBin    jjmit area=3.2",
        "xBQ1 QBin QBout BQ",
        ".tran 0.1p 200p",
        "I_WL1 0 WL1 pwl",
        "I_BL1 0 BL1 pwl",
        "I_SE1 0 SE1 pwl",
    )
    for token in required:
        if token not in result:
            raise RuntimeError(f"corrected deck missing required token {token!r}: {condition}")
    if sum(f"B_LD4_{index:02d}" in result for index in range(1, 12)) != 11:
        raise RuntimeError(f"corrected deck does not contain exactly 11 series terminal JJ: {condition}")
    if config["load"] == "jtl" and ".include " + relpath(HISTORICAL_JTL, INPUT_DIR) not in result:
        raise RuntimeError(f"JTL include missing: {condition}")
    if re.search(r"(?m)^(?:\s*I_QB_BIAS|\s*xBQ1[^\n]*BQ_BVMSIM_V1)", result):
        raise RuntimeError(f"corrected deck accidentally uses migrated QB fixture: {condition}")
    return result


def write_new(path: Path, content: str) -> None:
    if path.exists():
        if path.read_text(encoding="utf-8") == content:
            return
        raise RuntimeError(f"refusing to overwrite existing deck: {path}")
    path.write_text(content, encoding="utf-8")


def main() -> int:
    for condition, config in CONDITIONS.items():
        path = INPUT_DIR / f"{condition}.cir"
        write_new(path, make_deck(condition, config))
        print(f"{condition} {sha256(path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
