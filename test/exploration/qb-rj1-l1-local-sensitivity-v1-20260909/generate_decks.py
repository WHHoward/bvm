#!/usr/bin/env python3
"""Generate the five preregistered parameterized QB decks without touching history."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
EXP = Path(__file__).resolve().parent
TEMPLATE = EXP / "inputs/array_fixture_template.cir"
BQ_SOURCE = EXP / "inputs/BQ_source.cir"
BQ_PARAMETERIZED = EXP / "inputs/BQ_parameterized.cir"

RUNS = {
    "nominal": {"run_id": "NOMINAL", "rj1": "12", "l1": "2p", "purpose": "matched internal baseline"},
    "l1_down": {"run_id": "L1_DOWN", "rj1": "12", "l1": "1.9p", "purpose": "L1 decrease"},
    "l1_up": {"run_id": "L1_UP", "rj1": "12", "l1": "2.1p", "purpose": "opposite-direction L1 control"},
    "rj1_up_05": {"run_id": "RJ1_UP_05", "rj1": "12.5", "l1": "2p", "purpose": "small RJ1 increase"},
    "rj1_up_10": {"run_id": "RJ1_UP_10", "rj1": "13", "l1": "2p", "purpose": "larger RJ1 increase"},
}

OLD_INCLUDE_BLOCK = (
    ".include ../../../../../circuits/models/jjmit.cir\n"
    ".include ../../../bvmsim-jm2-connected-single-ab-v1-20260903/variants/bvm_jm2_connected.cir\n"
    ".include ../../../../../BVMSim/BQ.cir\n"
    ".include ../../../../../BVMSim/library_josim/jtl2.cir"
)
LOCAL_INCLUDE_BLOCK = (
    ".include ../../inputs/jjmit.cir\n"
    ".include ../../inputs/bvm_jm2_connected.cir\n"
    ".include ../../inputs/BQ_parameterized.cir\n"
    ".include ../../inputs/jtl2.cir"
)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def write_once(path: Path, content: str) -> None:
    if path.exists():
        if path.read_text(encoding="utf-8") == content:
            return
        raise RuntimeError(f"refusing to overwrite existing artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def build_deck(rj1: str, l1: str) -> str:
    template = TEMPLATE.read_text(encoding="utf-8")
    if template.count(OLD_INCLUDE_BLOCK) != 1:
        raise RuntimeError("fixture template include block is not unique")
    parameter_block = f".param RJ1_VALUE={rj1}\n.param L1_VALUE={l1}\n"
    result = template.replace(OLD_INCLUDE_BLOCK, parameter_block + LOCAL_INCLUDE_BLOCK, 1)
    if result.count(".param RJ1_VALUE=") != 1 or result.count(".param L1_VALUE=") != 1:
        raise RuntimeError("parameter block was not inserted exactly once")
    if OLD_INCLUDE_BLOCK in result or "../../../../../BVMSim/BQ.cir" in result:
        raise RuntimeError("authoritative BQ include was not replaced by the registered local parameterized source")
    return result


def main() -> int:
    for path in (TEMPLATE, BQ_SOURCE, BQ_PARAMETERIZED):
        if not path.is_file():
            raise RuntimeError(f"missing input: {path}")
    if sha256(BQ_SOURCE) != "f3dcbf5f9bb3898faf5194b5f7c4771df3fa1ed16150496de4b52cb6f7256dfd":
        raise RuntimeError("BQ_source.cir is not the recorded BVMSim/BQ.cir copy")
    decks = {}
    for directory, spec in RUNS.items():
        path = EXP / "runs" / directory / "deck.cir"
        deck = build_deck(spec["rj1"], spec["l1"])
        write_once(path, deck)
        decks[spec["run_id"]] = {
            "directory": f"runs/{directory}",
            "path": path.relative_to(REPO).as_posix(),
            "sha256": sha256(path),
            "bytes": path.stat().st_size,
            "parameter_line_RJ1": f".param RJ1_VALUE={spec['rj1']}",
            "parameter_line_L1": f".param L1_VALUE={spec['l1']}",
            "RJ1_ohm": float(spec["rj1"]),
            "L1_pH": float(spec["l1"].removesuffix("p")),
            "purpose": spec["purpose"],
        }
    manifest = {
        "schema": "qb-rj1-l1-local-sensitivity-deck-generation-v1",
        "experiment_id": EXP.name,
        "created_at_local": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "head_at_generation": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip(),
        "fixture_template": {"path": TEMPLATE.relative_to(REPO).as_posix(), "sha256": sha256(TEMPLATE)},
        "bq_source": {"path": BQ_SOURCE.relative_to(REPO).as_posix(), "sha256": sha256(BQ_SOURCE)},
        "bq_parameterized": {"path": BQ_PARAMETERIZED.relative_to(REPO).as_posix(), "sha256": sha256(BQ_PARAMETERIZED)},
        "parameterization": "only active BQ L1 and RJ1 element values are global parameter references",
        "decks": decks,
    }
    write_once(EXP / "analysis/deck_generation.json", json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"status": "PASS", "run_count": len(decks), "decks": decks}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
