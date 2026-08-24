#!/usr/bin/env python3
"""Create the registered Phase-A READ-width fixtures without touching frozen decks."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT.parent / "bvm-internal-readout-20260819"
INPUTS = ROOT / "inputs"
MAP_PATH = ROOT / "analysis" / "phase-a-case-map.json"

READ_CASES = {
    "logical1-read": SOURCE / "inputs/pos-read-single.cir",
    "logical0-read": SOURCE / "inputs/neg-init-pos-read.cir",
}
ACCEPTED_CONTROLS = {
    "logical1-read0-control": SOURCE / "raw/pos-control/run-01.csv",
    "logical0-read0-control": SOURCE / "raw/neg-control/run-01.csv",
}
WIDTHS = {12: (108, 109), 15: (111, 112), 20: (116, 117)}


def fail_if_exists(path: Path) -> None:
    if path.exists():
        raise SystemExit(f"refusing to overwrite existing path: {path}")


def modify_read(text: str, width: int) -> str:
    end_ps, fall_ps = WIDTHS[width]
    pattern = r"96p \+100U 105p \+100U 106p 0"
    replacement = f"96p +100U {end_ps}p +100U {fall_ps}p 0"
    updated, count = re.subn(pattern, replacement, text)
    if count != 2:
        raise ValueError(f"expected two READ knots, found {count} for width={width}")
    updated = updated.replace(".include jjmit.cir", ".include ../../jjmit.cir")
    updated = updated.replace(".include bvm_cell.cir", ".include ../../bvm_cell.cir")
    return updated.replace(
        "* BVM Internal Readout Survey --",
        f"* BVM_JSL_READ_WIDTH_TO_QB_SFQ_V1 Phase-A {width}ps --",
        1,
    )


def main() -> None:
    INPUTS.mkdir(parents=True, exist_ok=True)
    for source_name in ("jjmit.cir", "bvm_cell.cir"):
        destination = INPUTS / source_name
        fail_if_exists(destination)
        shutil.copy2(SOURCE / "inputs" / source_name, destination)

    case_map: dict[str, object] = {
        "accepted_9ps": {
            "logical1-read": str(SOURCE / "raw/pos-read-single/run-01.csv"),
            "logical0-read": str(SOURCE / "raw/neg-init-pos-read/run-01.csv"),
            **{key: str(value) for key, value in ACCEPTED_CONTROLS.items()},
        },
        "new": {},
    }
    new_cases = case_map["new"]
    assert isinstance(new_cases, dict)
    for width in WIDTHS:
        width_dir = INPUTS / "phase-a" / f"{width}ps"
        width_dir.mkdir(parents=True, exist_ok=True)
        width_cases: dict[str, str] = {}
        for case_id, source_path in READ_CASES.items():
            destination = width_dir / f"{case_id}.cir"
            fail_if_exists(destination)
            destination.write_text(modify_read(source_path.read_text(), width))
            width_cases[case_id] = str(destination)
        new_cases[f"{width}ps"] = width_cases
    MAP_PATH.write_text(json.dumps(case_map, indent=2) + "\n")
    print(json.dumps(case_map, indent=2))


if __name__ == "__main__":
    main()
