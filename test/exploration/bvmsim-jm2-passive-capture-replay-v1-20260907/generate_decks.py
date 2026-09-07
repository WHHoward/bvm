#!/usr/bin/env python3
"""Generate the two passive capture decks for the preregistered replay study."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
EXP = Path(__file__).resolve().parent
VARIANT = REPO / "test/exploration/bvmsim-jm2-connected-single-ab-v1-20260903/variants/bvm_jm2_connected.cir"
HISTORICAL_BVM = REPO / "BVMSim/bvm_cell.cir"
CANONICAL_BVM = REPO / "circuits/bvm/bvm_cell.cir"
JJMIT = REPO / "circuits/models/jjmit.cir"
QB = REPO / "BVMSim/BQ.cir"
JTL = REPO / "BVMSim/library_josim/jtl2.cir"
SOLVER = REPO / "build/josim-cli"

HEAD_AT_SETUP = "510cb59ebaa237268980133435aa2ff32468c935"

INCLUDE_BLOCK = (
    ".include ../../../../../circuits/models/jjmit.cir\n"
    ".include ../../../bvmsim-jm2-connected-single-ab-v1-20260903/variants/bvm_jm2_connected.cir\n"
)

PWL = {
    "WL": "pwl(0 0 50p 0 51p -100u 60p -100u 61p 0 70p 0 71p +100u 80p +100u 81p 0 90p 0 91p +100u 100p +100u 101p 0 110p 0 111p +100u 120p +100u 121p 0 200p 0)",
    "BL": "pwl(0 0 50p 0 51p -100u 60p -100u 61p 0 70p 0 71p 0 80p 0 81p 0 90p 0 91p +100u 100p +100u 101p 0 110p 0 111p 0 120p 0 121p 0 200p 0)",
    "SE": "pwl(0 0 50p 0 51p 0 60p 0 61p 0 70p 0 71p +100u 80p +100u 81p 0 90p 0 91p 0 100p 0 101p 0 110p 0 111p +100u 120p +100u 121p 0 200p 0)",
}
QUIET = {
    "WL": "pwl(0 0 50p 0 51p -100u 60p -100u 61p 0 70p 0 71p +100u 80p +100u 81p 0 90p 0 91p +100u 100p +100u 101p 0 110p 0 111p 0 120p 0 121p 0 200p 0)",
    "BL": "pwl(0 0 50p 0 51p -100u 60p -100u 61p 0 70p 0 71p 0 80p 0 81p 0 90p 0 91p +100u 100p +100u 101p 0 110p 0 111p 0 120p 0 121p 0 200p 0)",
    "SE": "pwl(0 0 50p 0 51p 0 60p 0 61p 0 70p 0 71p 0 80p 0 81p 0 90p 0 91p 0 100p 0 101p 0 110p 0 111p 0 120p 0 121p 0 200p 0)",
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
    handle = f"XBVM{instance}"
    lines: list[str] = []
    for jj in ("B_JM1", "B_JM2", "B_JS1", "B_JS2"):
        lines.append(f".print P({jj}|{handle}) V({jj}|{handle}) I({jj}|{handle})")
    for branch in (
        "L_M1", "L_M2", "L_M3", "L_PM", "R_JM1", "L_S1", "L_S2", "R_S",
        "L_S3", "R_SE", "L_PSE", "L_PSL", "R_SL", "L_SL",
    ):
        lines.append(f".print I({branch}|{handle}) V({branch}|{handle})")
    return "\n".join(lines)


def jsl_block() -> str:
    nodes = ["SL1_OR_COMMON_SL"] + [f"JSL_NODE{i}" for i in range(1, 8)] + ["0"]
    return "\n".join(
        f"B_JSL{i} {nodes[i - 1]} {nodes[i]} jjmit area=5.0"
        for i in range(1, 9)
    )


def jsl_probe() -> str:
    return "\n".join(
        f".print P(B_JSL{i}) V(B_JSL{i}) I(B_JSL{i})"
        for i in range(1, 9)
    )


def control_lines(instance: int, values: dict[str, str]) -> list[str]:
    return [f"I_{name}{instance} 0 {name}{instance} {values[name]}" for name in ("WL", "BL", "SE")]


def build_deck(kind: str) -> str:
    if kind == "single_passive":
        bvm_lines = ["XBVM1 WL1 BL1 SE1 SL1 BVM"]
        controls = control_lines(1, PWL)
        endpoint = "SL1"
        instances = (1,)
        description = "SINGLE_PASSIVE: one historical JM2-connected BVM, eight JSLs, final JSL node grounded."
    elif kind == "array_passive":
        bvm_lines = [f"XBVM{i} WL{i} BL{i} SE{i} COMMON_SL BVM" for i in range(1, 5)]
        controls: list[str] = []
        for i in range(1, 5):
            controls.extend(control_lines(i, PWL if i == 1 else QUIET))
        endpoint = "COMMON_SL"
        instances = (1, 2, 3, 4)
        description = "ARRAY_PASSIVE: four identical historical JM2-connected BVMs share COMMON_SL; final-read target is BVM1."
    else:
        raise ValueError(kind)

    probes = [
        "* Full passive probe: every present BVM, all controls, boundary, and all eight JSL P/V/I.",
        ".print " + " ".join(f"I(I_{name}{i})" for i in instances for name in ("WL", "BL", "SE")),
        *(bvm_probe(i) for i in instances),
        f".print V({endpoint})",
        jsl_probe(),
    ]
    return "\n".join(
        [
            f"* GENERATED {kind.upper()} DECK: passive BVM/JSL source capture",
            "* source_class=HISTORICAL_BVMSIM_JM2_CONNECTED_VARIANT",
            f"* {description}",
            "* Registered history: WRITE0 -> ZERO_STATE_READ_CONTROL -> WRITE1 -> selective one-state READ -> TAIL.",
            "* No QB, JTL or termination is present in this passive fixture.",
            "",
            INCLUDE_BLOCK.rstrip("\n"),
            "",
            *bvm_lines,
            "",
            jsl_block().replace("SL1_OR_COMMON_SL", endpoint),
            "",
            *controls,
            "",
            ".tran 0.1p 200p",
            "",
            "\n".join(probes),
            ".end",
            "",
        ]
    )


def normalized_elements(deck: str) -> list[str]:
    return [
        line.strip()
        for line in deck.splitlines()
        if line.strip() and not line.lstrip().startswith(("*", "."))
    ]


def source_record(path: Path) -> dict[str, object]:
    return {
        "path": path.relative_to(REPO).as_posix(),
        "sha256": sha256(path),
        "bytes": path.stat().st_size,
    }


def main() -> int:
    required = (VARIANT, HISTORICAL_BVM, CANONICAL_BVM, JJMIT, QB, JTL, SOLVER)
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
    for kind in ("single_passive", "array_passive"):
        deck = build_deck(kind)
        path = EXP / "runs" / kind / "deck.cir"
        write_once(path, deck)
        decks[kind] = deck
        records[kind] = {"path": path.relative_to(REPO).as_posix(), "sha256": sha256(path), "bytes": path.stat().st_size}

    for kind, deck in decks.items():
        elements = normalized_elements(deck)
        expected_bvm = 1 if kind == "single_passive" else 4
        if sum(line.endswith("BVM") for line in elements) != expected_bvm:
            raise RuntimeError(f"unexpected BVM count in {kind}")
        if sum(line.startswith("B_JSL") for line in elements) != 8:
            raise RuntimeError(f"unexpected JSL count in {kind}")
        if any("BQ" in line or "jtl" in line.lower() or "R_TERM" in line for line in elements):
            raise RuntimeError(f"passive deck contains forbidden downstream element: {kind}")
        if any("COMMON_SL" in line for line in elements) != (kind == "array_passive"):
            raise RuntimeError(f"COMMON_SL endpoint check failed: {kind}")

    source_manifest = {
        "schema": "jm2-passive-capture-replay-source-manifest-v1",
        "experiment_id": EXP.name,
        "created_at_local": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "head_at_setup": HEAD_AT_SETUP,
        "sources": {
            "bvm_variant": source_record(VARIANT),
            "historical_bvm_reference_not_used": source_record(HISTORICAL_BVM),
            "canonical_bvm_not_used": source_record(CANONICAL_BVM),
            "jjmit": source_record(JJMIT),
            "qb": source_record(QB),
            "jtl": source_record(JTL),
            "solver": source_record(SOLVER),
        },
        "variant_diff": {"status": "PASS", "difference_count": 1, "difference": differences[0]},
        "passive_decks": records,
        "replay_generation": "PENDING_PASSIVE_CAPTURE",
        "canonical_bvm_used": False,
    }
    write_once(EXP / "source" / "source_manifest.json", json.dumps(source_manifest, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"status": "PASS", "decks": records, "source_manifest": "source/source_manifest.json"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
