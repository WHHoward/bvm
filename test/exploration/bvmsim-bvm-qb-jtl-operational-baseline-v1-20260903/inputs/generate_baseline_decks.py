#!/usr/bin/env python3
"""Generate the original-BQ operational baseline decks.

Historical source files are read only.  The four-BVM deck starts from the
historical fixture and replaces only its active stimulus/print block so the
state-coded BL pulse is explicit.  Single-BVM decks start from the already
reviewed 2x2 topology template, but use BVMSim/BQ.cir directly.  Generated
files are never overwritten.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
HISTORICAL_FOUR = REPO / "BVMSim/test_bvm_mixed_0.cir"
HISTORICAL_BVM = REPO / "BVMSim/bvm_cell.cir"
HISTORICAL_QB = REPO / "BVMSim/BQ.cir"
HISTORICAL_JTL = REPO / "BVMSim/library_josim/jtl2.cir"
SINGLE_TEMPLATES = {
    "S0-R": REPO / "test/exploration/bvmsim-bvm-qb-single-2x2-quick-v1-20260902/inputs/s0-r.cir",
    "S1-R": REPO / "test/exploration/bvmsim-bvm-qb-single-2x2-quick-v1-20260902/inputs/s1-r.cir",
    "S0-J": REPO / "test/exploration/bvmsim-bvm-qb-single-2x2-quick-v1-20260902/inputs/s0-j.cir",
    "S1-J": REPO / "test/exploration/bvmsim-bvm-qb-single-2x2-quick-v1-20260902/inputs/s1-j.cir",
}
SETUPS = (HISTORICAL_FOUR, HISTORICAL_BVM, HISTORICAL_QB, HISTORICAL_JTL, *SINGLE_TEMPLATES.values())


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_new(path: Path, content: str) -> None:
    if path.exists():
        if path.read_text(encoding="utf-8") == content:
            return
        raise RuntimeError(f"refusing to overwrite generated file: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def inc(deck_dir: Path, source: Path) -> str:
    return os.path.relpath(source, deck_dir)


def four_stimulus(state: str) -> str:
    if not re.fullmatch(r"[01]{4}", state):
        raise ValueError(f"state must be four bits: {state}")
    lines = [
        f"* State {state}: b3/b2/b1/b0 -> BVM1/BVM2/BVM3/BVM4; only BL at WRITE1 is state-coded.",
        "* Historical schedule: initial logical-0 write, READ0, state write, READ1.",
    ]
    for index, bit in enumerate(state, start=1):
        bl_write = "+100u" if bit == "1" else "-100u"
        lines.extend(
            [
                f"I_WL{index} 0 WL{index} pwl(0 0 50p 0 51p -100u 60p -100u 61p 0 70p 0 71p 100u 80p 100u 81p 0 90p 0 91p 100u 100p 100u 101p 0 110p 0 111p 100u 120p 100u 121p 0 200p 0)",
                f"I_BL{index} 0 BL{index} pwl(0 0 50p 0 51p -100u 60p -100u 61p 0 90p 0 91p {bl_write} 100p {bl_write} 101p 0 200p 0)",
                f"I_SE{index} 0 SE{index} pwl(0 0 70p 0 71p 100u 80p 100u 81p 0 110p 0 111p 100u 120p 100u 121p 0 200p 0)",
            ]
        )
    return "\n".join(lines) + "\n"


FOUR_PRINTS = """.print I(I_WL1) I(I_BL1) I(I_SE1) I(I_WL2) I(I_BL2) I(I_SE2) I(I_WL3) I(I_BL3) I(I_SE3) I(I_WL4) I(I_BL4) I(I_SE4)
.print P(B_JM1|XBVM1) V(B_JM1|XBVM1) I(B_JM1|XBVM1)
.print P(B_JM2|XBVM1) V(B_JM2|XBVM1) I(B_JM2|XBVM1)
.print P(B_JS1|XBVM1) V(B_JS1|XBVM1) I(B_JS1|XBVM1)
.print P(B_JS2|XBVM1) V(B_JS2|XBVM1) I(B_JS2|XBVM1)
.print V(SL1) I(L_PSL|XBVM1) I(L_SL|XBVM1)
.print V(SL2) I(L_SL|XBVM2)
.print V(SL3) I(L_SL|XBVM3)
.print V(SL4) I(L_SL|XBVM4)
.print P(B_LD4_01) V(B_LD4_01) I(B_LD4_01)
.print P(B_LD4_11) V(B_LD4_11) I(B_LD4_11)
.print P(BVMOUT) V(BVMOUT) I(BVMOUT)
.print V(QBIN) V(QBOUT)
.print I(LIN|XBQ1) P(BJS|XBQ1) V(BJS|XBQ1) I(BJS|XBQ1)
.print P(BJ1|XBQ1) V(BJ1|XBQ1) I(BJ1|XBQ1) I(RJ1|XBQ1)
.print I(L1|XBQ1) I(IB|XBQ1) I(L2|XBQ1)
.print P(BJ2|XBQ1) V(BJ2|XBQ1) I(BJ2|XBQ1) I(RJ2|XBQ1) I(L3|XBQ1)
.print P(B01|XJTL1_1) V(B01|XJTL1_1) P(B02|XJTL1_1) V(B02|XJTL1_1)
.print P(B01|XJTL1_2) V(B01|XJTL1_2) P(B02|XJTL1_2) V(B02|XJTL1_2)
.print P(B01|XJTL1_3) V(B01|XJTL1_3) P(B02|XJTL1_3) V(B02|XJTL1_3)
.print P(B01|XJTL1_4) V(B01|XJTL1_4) P(B02|XJTL1_4) V(B02|XJTL1_4)
.print P(B01|XJTL1_5) V(B01|XJTL1_5) P(B02|XJTL1_5) V(B02|XJTL1_5)
.print P(B01|XJTL1_6) V(B01|XJTL1_6) P(B02|XJTL1_6) V(B02|XJTL1_6)
"""


SINGLE_PRINTS = """.print I(I_WL1) I(I_BL1) I(I_SE1)
.print P(B_JM1|XBVM1) V(B_JM1|XBVM1) I(B_JM1|XBVM1)
.print P(B_JM2|XBVM1) V(B_JM2|XBVM1) I(B_JM2|XBVM1)
.print P(B_JS1|XBVM1) V(B_JS1|XBVM1) I(B_JS1|XBVM1)
.print P(B_JS2|XBVM1) V(B_JS2|XBVM1) I(B_JS2|XBVM1)
.print V(SL1) I(L_PSL|XBVM1) I(L_SL|XBVM1)
.print P(B_LD4_01) V(B_LD4_01) I(B_LD4_01)
.print P(B_LD4_11) V(B_LD4_11) I(B_LD4_11)
.print P(BVMOUT) V(BVMOUT) I(BVMOUT)
.print V(QBIN) V(QBOUT)
.print I(LIN|XBQ1) P(BJS|XBQ1) V(BJS|XBQ1) I(BJS|XBQ1)
.print P(BJ1|XBQ1) V(BJ1|XBQ1) I(BJ1|XBQ1) I(RJ1|XBQ1)
.print I(L1|XBQ1) I(IB|XBQ1) I(L2|XBQ1)
.print P(BJ2|XBQ1) V(BJ2|XBQ1) I(BJ2|XBQ1) I(RJ2|XBQ1) I(L3|XBQ1)
"""


def replace_prints(text: str, block: str) -> str:
    end = text.find("\n.end")
    if end < 0:
        raise RuntimeError(".end not found")
    print_start = text.find("\n.print", 0, end)
    if print_start < 0:
        raise RuntimeError("active .print block not found")
    return text[:print_start + 1] + block + text[end:]


def make_four(state: str, deck_dir: Path) -> str:
    source = HISTORICAL_FOUR.read_text(encoding="utf-8")
    replacements = {
        ".include ./bvm_cell.cir": f".include {inc(deck_dir, HISTORICAL_BVM)}",
        ".include ./BQ.cir": f".include {inc(deck_dir, HISTORICAL_QB)}",
        ".include ./library_josim/jtl2.cir": f".include {inc(deck_dir, HISTORICAL_JTL)}",
    }
    for old, new in replacements.items():
        if old not in source:
            raise RuntimeError(f"historical include missing: {old}")
        source = source.replace(old, new, 1)
    start = source.find("***** 1 ****")
    end = source.find("\nxBQ1 QBin QBout BQ")
    if start < 0 or end < 0 or end <= start:
        raise RuntimeError("historical active stimulus block not found")
    source = source[:start] + four_stimulus(state) + source[end + 1 :]
    source = replace_prints(source, FOUR_PRINTS)
    source = re.sub(r"(?m)^\.tran\s+[^\n]+$", ".tran 0.1p 200p 45p", source)
    metadata = (
        f"* GENERATED OPERATIONAL BASELINE: F4_{state}_R12_T100\n"
        f"* source_class=HISTORICAL_BVMSIM state={state} expected_count={state.count('1')}\n"
        f"* state mapping: b3/b2/b1/b0 -> BL1/BL2/BL3/BL4 at WRITE1 90--101 ps\n"
    )
    return metadata + source


def make_single(run_id: str, deck_dir: Path) -> str:
    template = SINGLE_TEMPLATES[run_id]
    source = template.read_text(encoding="utf-8")
    source = re.sub(r"(?m)^\.include .*circuits/models/jjmit\.cir\n", "", source)
    source = re.sub(
        r"(?m)^\.include .*BVMSim/bvm_cell\.cir$",
        f".include {inc(deck_dir, HISTORICAL_BVM)}",
        source,
    )
    source = re.sub(
        r"(?m)^\.include .*circuits/qb/bq_cell_bvmsim_v1\.cir$",
        f".include {inc(deck_dir, HISTORICAL_QB)}",
        source,
    )
    source = re.sub(
        r"(?m)^\.include .*BVMSim/library_josim/jtl2\.cir$",
        f".include {inc(deck_dir, HISTORICAL_JTL)}",
        source,
    )
    if f".include {inc(deck_dir, HISTORICAL_QB)}" not in source:
        raise RuntimeError(f"original BQ include not installed for {run_id}")
    source = source.replace("I_QB_BIAS 0 QB_BIAS pwl(0 0 1p 250u)\n", "", 1)
    source = source.replace("xBQ1 QBin QBout QB_BIAS BQ_BVMSIM_V1", "xBQ1 QBin QBout BQ", 1)
    source = re.sub(r"(?m)^\.tran\s+[^\n]+$", ".tran 0.1p 200p", source)
    source = replace_prints(source, SINGLE_PRINTS)
    if not re.search(r"(?m)^xBQ1\s+QBin\s+QBout\s+BQ\s*$", source) or re.search(
        r"(?m)^xBQ1\s+QBin\s+QBout\s+QB_BIAS\s+BQ_BVMSIM_V1\s*$", source
    ):
        raise RuntimeError(f"single original BQ instance conversion failed: {run_id}")
    metadata = (
        f"* GENERATED OPERATIONAL BASELINE: {run_id}\n"
        f"* source_class=HISTORICAL_BVMSIM qb=BVMSim/BQ.cir RJ1=12 RJ2=4 IB=250uA\n"
    )
    return metadata + source


def manifest_record(run_id: str, family: str, state: str | None, deck: Path, expected: int, load: str | None) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "family": family,
        "state": state,
        "expected_count": expected,
        "load": load,
        "deck": str(deck.relative_to(REPO)),
        "deck_sha256": sha256(deck),
        "raw": str((deck.parent / "raw/run-01.csv").relative_to(REPO)),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    for path in SETUPS:
        if not path.is_file():
            raise RuntimeError(f"missing setup source: {path}")
    if args.check_only:
        print("baseline source/template check PASS")
        return 0

    records: list[dict[str, Any]] = []
    for state in (f"{number:04b}" for number in range(16)):
        deck = EXP / "runs" / "four" / state / "deck.cir"
        write_new(deck, make_four(state, deck.parent))
        records.append(manifest_record(f"F4_{state}_R12_T100", "four_bvm", state, deck, state.count("1"), "JTL"))
    for run_id in ("S0-R", "S1-R", "S0-J", "S1-J"):
        deck = EXP / "runs" / "single" / run_id / "deck.cir"
        write_new(deck, make_single(run_id, deck.parent))
        records.append(manifest_record(run_id, "single_bvm", None, deck, 0 if run_id.startswith("S0") else 1, "direct" if run_id.endswith("R") else "JTL"))

    source_hashes = {str(path.relative_to(REPO)): sha256(path) for path in SETUPS}
    manifest = {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "generator": str(Path(__file__).relative_to(REPO)),
        "source_hashes": source_hashes,
        "historical_bvm_is_not_canonical": True,
        "state_mapping": "b3/b2/b1/b0 -> BL1/BL2/BL3/BL4 at WRITE1; WL/SE historical schedule unchanged",
        "nominal": {"rj1_ohm": 12.0, "rj2_ohm": 4.0, "qb_bias_uA": 250.0, "timestep_ps": 0.1},
        "baseline_run_count": len(records),
        "runs": records,
        "raw_policy": "raw files are created only by execution and are immutable",
    }
    manifest_path = EXP / "analysis" / "baseline_deck_manifest.json"
    if not manifest_path.exists():
        write_new(manifest_path, json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    write_new(EXP / "source" / "README.md", "# Source snapshot\n\n本目录不复制或修改 BVMSim source；哈希与路径见 `SHA256SUMS.txt`。\n")
    sums = "\n".join(f"{digest}  {path}" for path, digest in source_hashes.items()) + "\n"
    write_new(EXP / "source" / "SHA256SUMS.txt", sums)
    print(f"generated {len(records)} baseline decks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
