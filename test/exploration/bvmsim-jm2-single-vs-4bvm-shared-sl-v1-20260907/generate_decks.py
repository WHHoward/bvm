#!/usr/bin/env python3
"""Generate the two preregistered SINGLE/ARRAY decks without touching history."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
EXP = Path(__file__).resolve().parent
VARIANT = REPO / "test/exploration/bvmsim-jm2-connected-single-ab-v1-20260903/variants/bvm_jm2_connected.cir"
HISTORICAL_BVM = REPO / "BVMSim/bvm_cell.cir"
CANONICAL_BVM = REPO / "circuits/bvm/bvm_cell.cir"
JJMIT = REPO / "circuits/models/jjmit.cir"
BQ = REPO / "BVMSim/BQ.cir"
JTL = REPO / "BVMSim/library_josim/jtl2.cir"
SOLVER = REPO / "build/josim-cli"

INCLUDE_BLOCK = (
    ".include ../../../../../circuits/models/jjmit.cir\n"
    ".include ../../../bvmsim-jm2-connected-single-ab-v1-20260903/variants/bvm_jm2_connected.cir\n"
    ".include ../../../../../BVMSim/BQ.cir\n"
    ".include ../../../../../BVMSim/library_josim/jtl2.cir\n"
)

PWL = {
    "WL": "pwl(0 0 50p 0 51p -100u 60p -100u 61p 0 70p 0 71p +100u 80p +100u 81p 0 90p 0 91p +100u 100p +100u 101p 0 110p 0 111p +100u 120p +100u 121p 0 200p 0)",
    "BL": "pwl(0 0 50p 0 51p -100u 60p -100u 61p 0 70p 0 71p 0 80p 0 81p 0 90p 0 91p +100u 100p +100u 101p 0 110p 0 111p 0 120p 0 121p 0 200p 0)",
    "SE": "pwl(0 0 50p 0 51p 0 60p 0 61p 0 70p 0 71p +100u 80p +100u 81p 0 90p 0 91p 0 100p 0 101p 0 110p 0 111p +100u 120p +100u 121p 0 200p 0)",
}
QUIET = {
    "WL": "pwl(0 0 50p 0 51p -100u 60p -100u 61p 0 70p 0 71p +100u 80p +100u 81p 0 90p 0 91p +100u 100p +100u 101p 0 110p 0 111p 0 120p 0 121p 0 200p 0)",
    "BL": "pwl(0 0 50p 0 51p -100u 60p -100u 61p 0 70p 0 71p 0 80p 0 81p 0 90p 0 91p +100u 100p +100u 101p 0 110p 0 111p 0 120p 0 121p 0 200p 0)",
    "SE": "pwl(0 0 50p 0 51p 0 60p 0 61p 0 70p 0 71p +100u 80p +100u 81p 0 90p 0 91p 0 100p 0 101p 0 110p 0 111p 0 120p 0 121p 0 200p 0)",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def write_once(path: Path, content: str) -> None:
    if path.exists():
        if path.read_text(encoding="utf-8") == content:
            return
        raise RuntimeError(f"refusing to overwrite existing artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def bvm_probe(instance: int) -> str:
    h = f"XBVM{instance}"
    lines: list[str] = []
    for jj in ("B_JM1", "B_JM2", "B_JS1", "B_JS2"):
        lines.append(f".print P({jj}|{h}) V({jj}|{h}) I({jj}|{h})")
    for branch in ("L_M1", "L_M2", "L_M3", "L_PM", "R_JM1", "L_S1", "L_S2", "R_S", "L_S3", "R_SE", "L_PSE", "L_PSL", "R_SL", "L_SL"):
        lines.append(f".print I({branch}|{h}) V({branch}|{h})")
    return "\n".join(lines)


def control_probe(instance: int) -> str:
    return " ".join(f"I(I_{name}{instance})" for name in ("WL", "BL", "SE"))


def jsl_block(upstream: str) -> str:
    nodes = [upstream] + [f"JSL_NODE{i}" for i in range(1, 8)] + ["QBIN"]
    return "\n".join(
        f"B_JSL{i} {nodes[i - 1]} {nodes[i]} jjmit area=5.0"
        for i in range(1, 9)
    )


def jsl_probe() -> str:
    return "\n".join(
        f".print P(B_JSL{i}) V(B_JSL{i}) I(B_JSL{i})"
        for i in range(1, 9)
    )


def downstream_block() -> str:
    return "\n".join(
        (
            "* Frozen QB and six-stage JTL are byte-identical in both decks.",
            "XBQ1 QBIN QBOUT BQ",
            "XJTL1_1 QBOUT JTL1_OUT jtl",
            "XJTL1_2 JTL1_OUT JTL2_OUT jtl",
            "XJTL1_3 JTL2_OUT JTL3_OUT jtl",
            "XJTL1_4 JTL3_OUT JTL4_OUT jtl",
            "XJTL1_5 JTL4_OUT JTL5_OUT jtl",
            "XJTL1_6 JTL5_OUT JTL6_OUT jtl",
            "R_TERM JTL6_OUT 0 10",
        )
    )


def qb_jtl_probe() -> str:
    lines = [
        ".print V(QBIN) V(QBOUT)",
        ".print I(LIN|XBQ1) V(LIN|XBQ1) I(L1|XBQ1) V(L1|XBQ1) I(L2|XBQ1) V(L2|XBQ1) I(L3|XBQ1) V(L3|XBQ1)",
        ".print I(RJ1|XBQ1) V(RJ1|XBQ1) I(RJ2|XBQ1) V(RJ2|XBQ1) I(IB|XBQ1) V(IB|XBQ1)",
    ]
    for jj in ("BJS", "BJ1", "BJ2"):
        lines.append(f".print P({jj}|XBQ1) V({jj}|XBQ1) I({jj}|XBQ1)")
    for stage in range(1, 7):
        h = f"XJTL1_{stage}"
        lines.append(f".print P(B01|{h}) V(B01|{h}) I(B01|{h}) P(B02|{h}) V(B02|{h}) I(B02|{h})")
        lines.append(f".print V(JTL{stage}_OUT)")
    lines.append(".print I(R_TERM)")
    return "\n".join(lines)


def build_deck(kind: str) -> str:
    if kind == "single":
        bvm_lines = ["XBVM1 WL1 BL1 SE1 SL1 BVM"]
        control_lines = [f"I_{name}1 0 {name}1 {PWL[name]}" for name in ("WL", "BL", "SE")]
        endpoint = "V(SL1)"
        jsl_upstream = "SL1"
        fixture_comment = "SINGLE: exactly one historical JM2-connected BVM; target controls are the registered protocol."
        instances = (1,)
    elif kind == "array":
        bvm_lines = [f"XBVM{i} WL{i} BL{i} SE{i} COMMON_SL BVM" for i in range(1, 5)]
        control_lines = []
        for i in range(1, 5):
            values = PWL if i == 1 else QUIET
            control_lines.extend(f"I_{name}{i} 0 {name}{i} {values[name]}" for name in ("WL", "BL", "SE"))
        endpoint = "V(COMMON_SL)"
        jsl_upstream = "COMMON_SL"
        fixture_comment = "ARRAY: four identical historical JM2-connected BVMs share COMMON_SL; BVM1 is the selective final-read target."
        instances = (1, 2, 3, 4)
    else:
        raise ValueError(kind)

    probes = [
        "* Full probe is intentionally retained for every BVM and all eight shared/single JSL elements.",
        ".print " + " ".join(control_probe(i) for i in instances),
    ]
    for i in instances:
        probes.append(bvm_probe(i))
    probes.extend(
        [
            f".print {endpoint}",
            jsl_probe(),
            qb_jtl_probe(),
        ]
    )
    return "\n".join(
        [
            f"* GENERATED {kind.upper()} DECK: JM2-connected BVM vs 4-BVM shared-SL experiment",
            "* source_class=HISTORICAL_BVMSIM_JM2_CONNECTED_VARIANT",
            f"* {fixture_comment}",
            "* Registered history: WRITE0 -> ZERO_STATE_READ_CONTROL -> WRITE1 -> selective one-state READ -> TAIL.",
            "",
            INCLUDE_BLOCK.rstrip("\n"),
            "",
            *bvm_lines,
            "",
            jsl_block(jsl_upstream),
            "",
            downstream_block(),
            "",
            *control_lines,
            "",
            ".tran 0.1p 200p",
            "",
            "\n".join(probes),
            ".end",
            "",
        ]
    )


def normalized_downstream(deck: str) -> list[str]:
    lines = deck.splitlines()
    start = next(index for index, line in enumerate(lines) if line.strip() == "XBQ1 QBIN QBOUT BQ")
    end = next(index for index in range(start, len(lines)) if lines[index].strip() == "R_TERM JTL6_OUT 0 10") + 1
    return [line.strip() for line in lines[start:end]]


def source_record(path: Path) -> dict[str, object]:
    return {"path": path.relative_to(REPO).as_posix(), "sha256": sha256(path), "bytes": path.stat().st_size}


def main() -> int:
    required = (VARIANT, HISTORICAL_BVM, CANONICAL_BVM, JJMIT, BQ, JTL, SOLVER)
    for path in required:
        if not path.is_file():
            raise RuntimeError(f"missing required source: {path}")
    historical = HISTORICAL_BVM.read_text(encoding="utf-8").splitlines()
    variant = VARIANT.read_text(encoding="utf-8").splitlines()
    differences = [
        {"line": index + 1, "historical": left, "variant": right}
        for index, (left, right) in enumerate(zip(historical, variant))
        if left != right
    ]
    expected = [{"line": 37, "historical": "L_M2    2       4       24.5P", "variant": "L_M2    2       3       24.5P"}]
    if differences != expected or len(historical) != len(variant):
        raise RuntimeError(f"JM2 variant differs beyond registered connection: {differences}")
    decks: dict[str, str] = {}
    records: dict[str, object] = {}
    for kind in ("single", "array"):
        deck = build_deck(kind)
        path = EXP / "runs" / kind / "deck.cir"
        write_once(path, deck)
        decks[kind] = deck
        records[kind] = {"path": path.relative_to(REPO).as_posix(), "sha256": sha256(path), "bytes": path.stat().st_size}
    if normalized_downstream(decks["single"]) != normalized_downstream(decks["array"]):
        raise RuntimeError("SINGLE and ARRAY downstream blocks are not identical")
    source_manifest = {
        "schema": "jm2-single-vs-4bvm-shared-sl-source-manifest-v1",
        "experiment_id": EXP.name,
        "created_at_local": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "head_before_setup": "36a59701acc535d3ff98ffa590640555ada898ac",
        "sources": {
            "bvm_variant": source_record(VARIANT),
            "historical_bvm_reference_not_used": source_record(HISTORICAL_BVM),
            "canonical_bvm_not_used": source_record(CANONICAL_BVM),
            "jjmit": source_record(JJMIT),
            "qb": source_record(BQ),
            "jtl": source_record(JTL),
            "solver": source_record(SOLVER),
        },
        "variant_diff": {"status": "PASS", "difference_count": 1, "difference": differences[0]},
        "decks": records,
        "downstream_block_sha256": hashlib.sha256("\n".join(normalized_downstream(decks["single"])).encode()).hexdigest(),
        "canonical_bvm_used": False,
    }
    write_once(EXP / "source" / "source_manifest.json", json.dumps(source_manifest, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"status": "PASS", "decks": records, "source_manifest": "source/source_manifest.json"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
