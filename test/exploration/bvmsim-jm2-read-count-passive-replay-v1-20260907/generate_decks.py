#!/usr/bin/env python3
"""Generate the three new four-cell passive read-count capture decks."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
EXP = Path(__file__).resolve().parent
BASELINE = REPO / "test/exploration/bvmsim-jm2-passive-capture-replay-v1-20260907"
VARIANT = REPO / "test/exploration/bvmsim-jm2-connected-single-ab-v1-20260903/variants/bvm_jm2_connected.cir"
HISTORICAL_BVM = REPO / "BVMSim/bvm_cell.cir"
CANONICAL_BVM = REPO / "circuits/bvm/bvm_cell.cir"
JJMIT = REPO / "circuits/models/jjmit.cir"
QB = REPO / "BVMSim/BQ.cir"
JTL = REPO / "BVMSim/library_josim/jtl2.cir"
SOLVER = REPO / "build/josim-cli"

HEAD_AT_SETUP = "217305580f1c9cec17839896730fbe9b1016c837"
READ_COUNTS = (2, 3, 4)
N1_REFERENCES = {
    "N1_PASSIVE": BASELINE / "runs/array_passive/raw.csv",
    "N1_REPLAY": BASELINE / "runs/replay_array/raw.csv",
}

INCLUDE_BLOCK = (
    ".include ../../../../../circuits/models/jjmit.cir\n"
    ".include ../../../bvmsim-jm2-connected-single-ab-v1-20260903/variants/bvm_jm2_connected.cir\n"
)

# These are the previously registered WRITE0 -> zero-state read -> WRITE1
# controls. Only the final read segment is changed in the new cases.
ACTIVE_FINAL = {
    "WL": "pwl(0 0 50p 0 51p -100u 60p -100u 61p 0 70p 0 71p +100u 80p +100u 81p 0 90p 0 91p +100u 100p +100u 101p 0 110p 0 111p +100u 120p +100u 121p 0 200p 0)",
    "BL": "pwl(0 0 50p 0 51p -100u 60p -100u 61p 0 70p 0 71p 0 80p 0 81p 0 90p 0 91p +100u 100p +100u 101p 0 110p 0 111p 0 120p 0 121p 0 200p 0)",
    "SE": "pwl(0 0 50p 0 51p 0 60p 0 61p 0 70p 0 71p +100u 80p +100u 81p 0 90p 0 91p 0 100p 0 101p 0 110p 0 111p +100u 120p +100u 121p 0 200p 0)",
}
QUIET_FINAL = {
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
    nodes = ["COMMON_SL"] + [f"JSL_NODE{i}" for i in range(1, 8)] + ["0"]
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


def build_deck(read_count: int) -> str:
    if read_count not in READ_COUNTS:
        raise ValueError(read_count)
    bvm_lines = [f"XBVM{i} WL{i} BL{i} SE{i} COMMON_SL BVM" for i in range(1, 5)]
    controls: list[str] = []
    for instance in range(1, 5):
        controls.extend(control_lines(instance, ACTIVE_FINAL if instance <= read_count else QUIET_FINAL))
    probes = [
        "* Full passive probe: every BVM, every control, COMMON_SL, and all eight JSL P/V/I.",
        ".print " + " ".join(f"I(I_{name}{i})" for i in range(1, 5) for name in ("WL", "BL", "SE")),
        *(bvm_probe(i) for i in range(1, 5)),
        ".print V(COMMON_SL)",
        jsl_probe(),
    ]
    return "\n".join(
        [
            f"* GENERATED N{read_count}_PASSIVE DECK: read-count passive source capture",
            "* source_class=HISTORICAL_BVMSIM_JM2_CONNECTED_VARIANT",
            f"* Four BVMs share COMMON_SL; final READ mask is {'1' * read_count + '0' * (4 - read_count)}.",
            "* Registered history: WRITE0 -> ZERO_STATE_READ_CONTROL -> WRITE1 -> final READ -> TAIL.",
            "* No QB, JTL or termination is present in this passive fixture.",
            "",
            INCLUDE_BLOCK.rstrip("\n"),
            "",
            *bvm_lines,
            "",
            jsl_block(),
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
        if line.strip() and not line.lstrip().startswith(("*", ".", "+"))
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
    for name, path in N1_REFERENCES.items():
        if not path.is_file():
            raise RuntimeError(f"missing N1 reference raw: {name}: {path}")

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

    decks: dict[str, dict[str, object]] = {}
    deck_texts: dict[int, str] = {}
    for read_count in READ_COUNTS:
        case = f"n{read_count}_passive"
        deck = build_deck(read_count)
        path = EXP / "runs" / case / "deck.cir"
        write_once(path, deck)
        deck_texts[read_count] = deck
        elements = normalized_elements(deck)
        bvm = [line for line in elements if line.endswith("BVM")]
        jsl = [line for line in elements if line.startswith("B_JSL")]
        if len(bvm) != 4 or len(jsl) != 8 or jsl[-1].split()[2] != "0":
            raise RuntimeError(f"unexpected passive topology in N{read_count}")
        if any(token in line.lower() for line in elements for token in ("bq", "jtl", "r_term")):
            raise RuntimeError(f"forbidden downstream element in N{read_count}")
        decks[f"N{read_count}_PASSIVE"] = {
            "path": path.relative_to(REPO).as_posix(),
            "sha256": sha256(path),
            "bytes": path.stat().st_size,
            "read_count": read_count,
            "final_read_mask": f"{'1' * read_count}{'0' * (4 - read_count)}",
        }

    # Register that all passive decks share the exact non-final-read history;
    # this is a mechanical check on the generated control source text.
    for left_count, right_count in ((2, 3), (3, 4)):
        left = deck_texts[left_count].split(".tran", 1)[0]
        right = deck_texts[right_count].split(".tran", 1)[0]
        for instance in range(1, 5):
            for name in ("WL", "BL", "SE"):
                left_value = left.split(f"I_{name}{instance} 0 {name}{instance}", 1)[1].split("\n", 1)[0]
                right_value = right.split(f"I_{name}{instance} 0 {name}{instance}", 1)[1].split("\n", 1)[0]
                if instance <= left_count and instance <= right_count and left_value != right_value:
                    raise RuntimeError("non-final control history changed between read-count decks")

    manifest = {
        "schema": "jm2-read-count-passive-replay-source-manifest-v1",
        "experiment_id": EXP.name,
        "created_at_local": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "head_at_setup": HEAD_AT_SETUP,
        "sources": {
            "bvm_variant": source_record(VARIANT),
            "historical_bvm_reference": source_record(HISTORICAL_BVM),
            "canonical_bvm_not_used": source_record(CANONICAL_BVM),
            "jjmit": source_record(JJMIT),
            "qb": source_record(QB),
            "jtl": source_record(JTL),
            "solver": source_record(SOLVER),
        },
        "variant_diff": {"status": "PASS", "difference_count": 1, "difference": differences[0]},
        "n1_reference": {
            name: {
                "path": path.relative_to(REPO).as_posix(),
                "sha256": sha256(path),
                "source_experiment": BASELINE.relative_to(REPO).as_posix(),
                "rerun": False,
            }
            for name, path in N1_REFERENCES.items()
        },
        "passive_decks": decks,
        "new_physical_solve_count": 6,
        "replay_generation": "PENDING_N2_N4_PASSIVE_CAPTURE",
        "canonical_bvm_used": False,
        "transformations": [],
    }
    write_once(EXP / "source" / "source_manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"status": "PASS", "decks": decks, "source_manifest": "source/source_manifest.json"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
