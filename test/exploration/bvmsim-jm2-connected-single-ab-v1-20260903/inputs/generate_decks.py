#!/usr/bin/env python3
"""Generate the four JM2-connected decks from immutable corrected references."""

from __future__ import annotations

import difflib
import hashlib
import json
import re
from collections import OrderedDict
from pathlib import Path


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
INPUTS = EXP / "inputs"
VARIANT = EXP / "variants/bvm_jm2_connected.cir"
HISTORICAL_BVM = REPO / "BVMSim/bvm_cell.cir"
REFERENCE_ROOT = REPO / "test/exploration/bvmsim-single-corrected-baseline-v1-20260903"

CONDITIONS = OrderedDict(
    (
        ("S0-R-JM2C", ("S0-R-CORRECTED", False)),
        ("S1-R-JM2C", ("S1-R-CORRECTED", False)),
        ("S0-J-JM2C", ("S0-J-CORRECTED-RERUN", True)),
        ("S1-J-JM2C", ("S1-J-CORRECTED-RERUN", True)),
    )
)

INTERNAL_PATH_PRINT = ".print I(L_M1|XBVM1) I(L_M2|XBVM1) I(L_M3|XBVM1) I(L_PM|XBVM1)"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel(path: Path, directory: Path) -> str:
    return str(path.relative_to(directory)).replace("\\", "/")


def write_once(path: Path, content: str) -> None:
    if path.exists():
        if path.read_text(encoding="utf-8") == content:
            return
        raise RuntimeError(f"refusing to overwrite existing input: {path}")
    path.write_text(content, encoding="utf-8")


def variant_diff() -> dict[str, object]:
    historical = HISTORICAL_BVM.read_text(encoding="utf-8").splitlines()
    connected = VARIANT.read_text(encoding="utf-8").splitlines()
    if len(historical) != len(connected):
        raise RuntimeError("variant line count differs from historical source")
    differences = [
        {"line": index + 1, "historical": left, "connected": right}
        for index, (left, right) in enumerate(zip(historical, connected))
        if left != right
    ]
    expected = {
        "line": 37,
        "historical": "L_M2    2       4       24.5P",
        "connected": "L_M2    2       3       24.5P",
    }
    if differences != [expected]:
        raise RuntimeError(f"variant differs beyond authorized L_M2 connection: {differences}")
    return {
        "status": "PASS",
        "difference_count": len(differences),
        "difference": differences[0],
        "historical_sha256": sha256(HISTORICAL_BVM),
        "connected_variant_sha256": sha256(VARIANT),
    }


def normalize_fixture(text: str) -> list[str]:
    """Remove only the expected include/probe packaging differences."""

    normalized: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("*"):
            continue
        if "BVMSim/bvm_cell.cir" in stripped or "../variants/bvm_jm2_connected.cir" in stripped:
            normalized.append(".include BVM_VARIANT_OR_HISTORICAL")
            continue
        if stripped == INTERNAL_PATH_PRINT:
            continue
        normalized.append(stripped)
    return normalized


def deck_diff(reference: Path, candidate: str) -> dict[str, object]:
    reference_lines = normalize_fixture(reference.read_text(encoding="utf-8"))
    candidate_lines = normalize_fixture(candidate)
    if reference_lines != candidate_lines:
        diff = list(
            difflib.unified_diff(
                reference_lines,
                candidate_lines,
                fromfile=str(reference),
                tofile="candidate",
                lineterm="",
            )
        )
        raise RuntimeError("candidate differs from reference beyond BVM include/probe packaging:\n" + "\n".join(diff))
    return {"status": "PASS", "normalized_line_count": len(candidate_lines), "reference": rel(reference, REPO)}


def required_tokens(candidate: str, *, is_jtl: bool) -> list[str]:
    required = [
        ".include ../../../../circuits/models/jjmit.cir",
        ".include ../variants/bvm_jm2_connected.cir",
        ".include ../../../../BVMSim/BQ.cir",
        "XBVM1 WL1 BL1 SE1 SL1 BVM",
        "BVMout   nld4_21 QBin    jjmit area=3.2",
        "xBQ1 QBin QBout BQ",
        "RBQ1 o6 0 10" if is_jtl else "RBQ1 QBout 0 10",
        ".tran 0.1p 200p",
        "I_WL1 0 WL1 pwl",
        "I_BL1 0 BL1 pwl",
        "I_SE1 0 SE1 pwl",
        INTERNAL_PATH_PRINT,
    ]
    if is_jtl:
        required.append(".include ../../../../BVMSim/library_josim/jtl2.cir")
        required.extend(f"xjtl1_{stage}" for stage in range(1, 7))
        required.extend(f"P(B01|XJTL1_{stage})" for stage in range(1, 7))
        required.extend(f"P(B02|XJTL1_{stage})" for stage in range(1, 7))
    return required


def make_deck(condition: str, reference_name: str, is_jtl: bool) -> tuple[str, dict[str, object]]:
    reference = REFERENCE_ROOT / "runs" / reference_name / "deck.cir"
    if not reference.is_file():
        raise RuntimeError(f"missing immutable reference deck: {reference}")
    source = reference.read_text(encoding="utf-8")
    old_include = ".include ../../../../BVMSim/bvm_cell.cir"
    if source.count(old_include) != 1:
        raise RuntimeError(f"historical BVM include count is not one: {reference}")
    candidate = source.replace(old_include, ".include ../variants/bvm_jm2_connected.cir")
    marker = ".print P(B_JS2|XBVM1) V(B_JS2|XBVM1) I(B_JS2|XBVM1)"
    if candidate.count(marker) != 1:
        raise RuntimeError(f"BVM JJ print marker not found exactly once: {reference}")
    candidate = candidate.replace(marker, marker + "\n" + INTERNAL_PATH_PRINT, 1)
    candidate = (
        f"* TASK-LOCAL JM2-CONNECTED VARIANT: {condition}\n"
        "* source_class=HISTORICAL_BVMSIM_JM2_CONNECTED_VARIANT\n"
        "* only physics change: L_M2 second node 4 -> 3; all other fixture lines are inherited.\n"
        + candidate
    )
    for token in required_tokens(candidate, is_jtl=is_jtl):
        if token not in candidate:
            raise RuntimeError(f"{condition}: missing required token {token!r}")
    if ".include ../../../../BVMSim/bvm_cell.cir" in candidate:
        raise RuntimeError(f"{condition}: historical BVM include remains active")
    if "circuits/bvm/bvm_cell.cir" in candidate:
        raise RuntimeError(f"{condition}: canonical BVM accidentally included")
    if candidate.count("B_LD4_") < 11 or candidate.count("BVMout") < 1:
        raise RuntimeError(f"{condition}: terminal sensing line is incomplete")
    return candidate, deck_diff(reference, candidate)


def main() -> int:
    if not VARIANT.is_file():
        raise RuntimeError(f"missing task-local variant: {VARIANT}")
    variant_record = variant_diff()
    records: list[dict[str, object]] = []
    for condition, (reference_name, is_jtl) in CONDITIONS.items():
        content, diff_record = make_deck(condition, reference_name, is_jtl)
        output = INPUTS / f"{condition}.cir"
        write_once(output, content)
        records.append(
            {
                "condition": condition,
                "reference_deck": rel(REFERENCE_ROOT / "runs" / reference_name / "deck.cir", REPO),
                "input_deck": rel(output, REPO),
                "input_sha256": sha256(output),
                "is_jtl": is_jtl,
                "reference_equivalence": diff_record,
            }
        )
    qa = {
        "schema": "jm2-connected-setup-qa-v1",
        "experiment": "bvmsim-jm2-connected-single-ab-v1-20260903",
        "source_class": "HISTORICAL_BVMSIM_JM2_CONNECTED_VARIANT",
        "variant": variant_record,
        "decks": records,
        "only_authorized_physics_change": True,
        "canonical_bvm_used": False,
        "historical_reference_runs_not_rerun": True,
    }
    qa_path = EXP / "analysis" / "setup_qa.json"
    qa_path.parent.mkdir(parents=True, exist_ok=True)
    qa_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"decks": len(records), "variant_diff": variant_record["status"], "qa": rel(qa_path, REPO)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
