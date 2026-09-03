#!/usr/bin/env python3
"""Generate the six PHASE-B decks directly under runs/<state>.

The historical BVMSim fixture is read-only.  Only its active stimulus and
print section are replaced: the device topology, models, values, solver
settings, and connection order remain historical.  Existing generated decks
are never overwritten.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
EXP = Path(__file__).resolve().parent
HISTORICAL_FIXTURE = REPO / "BVMSim/test_bvm_mixed_0.cir"
HISTORICAL_BVM = REPO / "BVMSim/bvm_cell.cir"
HISTORICAL_QB = REPO / "BVMSim/BQ.cir"
HISTORICAL_JTL = REPO / "BVMSim/library_josim/jtl2.cir"
STATES = ("0000", "1000", "0100", "0010", "0001", "1111")

sys.path.insert(0, str(REPO / "scripts"))
from bvmtools.probes import (  # noqa: E402
    flatten_probe_labels,
    historical_bvm_array_probes,
    historical_jtl_probes,
    original_bvmsim_qb_probes,
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_new(path: Path, content: str) -> None:
    if path.exists():
        if path.read_text(encoding="utf-8") == content:
            return
        raise RuntimeError(f"refusing to overwrite generated deck: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def rel_include(deck_dir: Path, source: Path) -> str:
    return os.path.relpath(source, deck_dir)


def stimulus(state: str) -> str:
    if not re.fullmatch(r"[01]{4}", state):
        raise ValueError(f"invalid state: {state}")
    lines = [
        f"* PHASE B state {state}; b3/b2/b1/b0 -> BVM1/BVM2/BVM3/BVM4",
        "* Historical schedule and amplitudes preserved; only state-coded BL changes at WRITE1.",
    ]
    for number, bit in enumerate(state, start=1):
        bl = "+100u" if bit == "1" else "-100u"
        lines.extend(
            [
                f"I_WL{number} 0 WL{number} pwl(0 0 50p 0 51p -100u 60p -100u 61p 0 70p 0 71p 100u 80p 100u 81p 0 90p 0 91p 100u 100p 100u 101p 0 110p 0 111p 100u 120p 100u 121p 0 200p 0)",
                f"I_BL{number} 0 BL{number} pwl(0 0 50p 0 51p -100u 60p -100u 61p 0 90p 0 91p {bl} 100p {bl} 101p 0 200p 0)",
                f"I_SE{number} 0 SE{number} pwl(0 0 70p 0 71p 100u 80p 100u 81p 0 110p 0 111p 100u 120p 100u 121p 0 200p 0)",
            ]
        )
    return "\n".join(lines) + "\n"


def print_block() -> str:
    bvm_labels = flatten_probe_labels(historical_bvm_array_probes(4))
    qb_labels = flatten_probe_labels(original_bvmsim_qb_probes())
    jtl_labels = flatten_probe_labels(historical_jtl_probes(6))
    stimulus_labels = tuple(
        f"I(I_{control}{number})"
        for number in range(1, 5)
        for control in ("WL", "BL", "SE")
    )
    groups = (
        ("controls", stimulus_labels),
        ("BVM P/V/I and sensing", bvm_labels),
        ("QB", qb_labels),
        ("JTL P/V", jtl_labels),
    )
    return "\n".join(
        f"* {name}\n.print {' '.join(labels)}" for name, labels in groups
    ) + "\n"


def replace_active_prints(text: str, block: str) -> str:
    end = text.find("\n.end")
    if end < 0:
        raise RuntimeError("historical .end not found")
    start = text.find("\n.print", 0, end)
    if start < 0:
        raise RuntimeError("historical active .print section not found")
    return text[: start + 1] + block + text[end:]


def make_deck(state: str, deck_dir: Path) -> str:
    source = HISTORICAL_FIXTURE.read_text(encoding="utf-8")
    for old, path in (
        (".include ./bvm_cell.cir", HISTORICAL_BVM),
        (".include ./BQ.cir", HISTORICAL_QB),
        (".include ./library_josim/jtl2.cir", HISTORICAL_JTL),
    ):
        if old not in source:
            raise RuntimeError(f"historical include missing: {old}")
        source = source.replace(old, f".include {rel_include(deck_dir, path)}", 1)

    start = source.find("***** 1 ****")
    end = source.find("\nxBQ1 QBin QBout BQ")
    if start < 0 or end < 0 or end <= start:
        raise RuntimeError("historical active stimulus block not found")
    source = source[:start] + stimulus(state) + source[end + 1 :]
    source = replace_active_prints(source, print_block())
    source = re.sub(r"(?m)^\.tran\s+[^\n]+$", ".tran 0.1p 200p 45p", source)
    header = (
        f"* GENERATED PHASE B DECK: state={state}\n"
        "* source_class=HISTORICAL_BVMSIM; topology and values unchanged\n"
        "* BVM/QB/JTL source authority remains the historical BVMSim tree\n"
    )
    return header + source


def validate_content(state: str, content: str) -> None:
    required = (
        "XBVM1 WL1 BL1 SE1 SL1 BVM",
        "XBVM2 WL2 BL2 SE2 SL2 BVM",
        "XBVM3 WL3 BL3 SE3 SL3 BVM",
        "XBVM4 WL4 BL4 SE4 SL4 BVM",
        "xBQ1 QBin QBout BQ",
        "xjtl1_6 o5 o6 jtl",
        ".tran 0.1p 200p 45p",
        "P(B_JM1|XBVM4)",
        "P(B_JS2|XBVM4)",
        "P(BJ2|XBQ1)",
        "P(B02|XJTL1_6)",
    )
    for token in required:
        if token not in content:
            raise RuntimeError(f"state {state}: generated deck missing {token}")
    if content.count(".print") < 8:
        raise RuntimeError(f"state {state}: generated probe block unexpectedly short")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    for path in (HISTORICAL_FIXTURE, HISTORICAL_BVM, HISTORICAL_QB, HISTORICAL_JTL):
        if not path.is_file():
            raise RuntimeError(f"missing historical source: {path}")
    generated: list[tuple[str, str]] = []
    for state in STATES:
        deck_dir = EXP / "runs" / state
        content = make_deck(state, deck_dir)
        validate_content(state, content)
        generated.append((state, content))
    if args.check_only:
        print(f"PHASE B deck generator check PASS ({len(generated)} states; no files written)")
        return 0
    for state, content in generated:
        write_new(EXP / "runs" / state / "deck.cir", content)
    print(f"generated {len(generated)} PHASE B decks")
    print(f"historical fixture sha256={sha256(HISTORICAL_FIXTURE)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
