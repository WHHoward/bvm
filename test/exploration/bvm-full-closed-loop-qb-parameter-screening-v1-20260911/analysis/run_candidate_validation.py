#!/usr/bin/env python3
"""Run only the registered 0001/1111 validation for an S screening point."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


EXP = Path(__file__).resolve().parents[1]
REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(EXP / "analysis"))
from prepare_screening import build_deck  # noqa: E402
from run_screening import (  # noqa: E402
    EXP as RUN_EXP,
    MASKS,
    REPO as RUN_REPO,
    SOLVER_SHA256,
    current_head,
    json_write,
    load_gate,
    matrix_point,
    now,
    physical_case,
    rel,
    result_path,
    sha256,
)
from screening_analysis import case_evidence, load  # noqa: E402


VALIDATION_MASKS = ("0001", "0011", "0111", "1111")


def classify_mask(trace: Any, mask: str) -> dict[str, Any]:
    evidence = case_evidence(trace)
    expected = {"0001": 1, "0011": 2, "0111": 3, "1111": 4}[mask]
    count = evidence["complete_response_candidate_count"]
    ordered = evidence["ordered_chain_by_candidate"]
    exact = evidence["control"]["status"] == "CLEAN" and count == expected and all(ordered.get(str(index), False) for index in range(1, expected + 1)) and not ordered.get(str(expected + 1), False)
    return {
        "mask": mask,
        "expected_count": expected,
        "classification": f"MASK_{mask}_{expected}_COMPLETE" if exact else "MASK_NOT_EXPECTED",
        "control_status": evidence["control"]["status"],
        "complete_response_candidate_count": count,
        "ordered_chain_by_candidate": ordered,
        "raw_authority": True,
        "evidence": evidence,
    }


def validation_deck(point: dict[str, Any], mask: str) -> Path:
    variant_name = Path(point["variant_path"]).name
    target = EXP / "screening/validation_decks" / point["point_id"] / f"{mask}.cir"
    text = build_deck(point["parameter"], float(point["value"]), mask, variant_name)
    if target.exists():
        if target.read_text(encoding="utf-8") != text:
            raise RuntimeError(f"refusing to overwrite validation deck: {target}")
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    return target


def raw_for_screening(point_id: str, mask: str) -> Path:
    result = json.loads(result_path(point_id).read_text(encoding="utf-8"))
    branch = "n2" if mask == "0011" else "n3"
    return REPO / result[branch]["raw_path"]


def main() -> int:
    _preflight, matrix, _relation = load_gate()
    candidate_path = EXP / "screening/CANDIDATE_FOUND.json"
    if not candidate_path.is_file():
        raise RuntimeError("candidate validation requested without CANDIDATE_FOUND.json")
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    point = matrix_point(matrix, candidate["point_id"])
    existing = EXP / "screening/validation_summary.json"
    if existing.is_file():
        summary = json.loads(existing.read_text(encoding="utf-8"))
        print(json.dumps({"status": summary["status"], "classification": summary["classification"], "resumed": True}, ensure_ascii=False, indent=2))
        return 0 if summary.get("classification") == "FULL_POPULATION_1_2_3_4_CANDIDATE" else 1

    new_case_records: dict[str, Any] = {}
    for mask in ("0001", "1111"):
        deck = validation_deck(point, mask)
        case = physical_case(point, mask, deck, run_prefix="VALIDATION")
        new_case_records[mask] = case

    raw_paths: dict[str, Path] = {
        "0001": REPO / new_case_records["0001"]["raw_path"],
        "0011": raw_for_screening(point["point_id"], "0011"),
        "0111": raw_for_screening(point["point_id"], "0111"),
        "1111": REPO / new_case_records["1111"]["raw_path"],
    }
    cases: dict[str, Any] = {}
    for mask in VALIDATION_MASKS:
        trace = load(raw_paths[mask])
        cases[mask] = classify_mask(trace, mask)
        cases[mask]["raw_path"] = rel(raw_paths[mask])
        cases[mask]["raw_sha256"] = sha256(raw_paths[mask])
        cases[mask]["physical_solve_this_experiment"] = mask in new_case_records
        if mask in new_case_records:
            cases[mask]["run_id"] = new_case_records[mask]["run_id"]

    counts = {mask: cases[mask]["complete_response_candidate_count"] for mask in VALIDATION_MASKS}
    exact = all(cases[mask]["classification"] == f"MASK_{mask}_{counts[mask]}_COMPLETE" for mask in VALIDATION_MASKS) and counts == {"0001": 1, "0011": 2, "0111": 3, "1111": 4}
    classification = "FULL_POPULATION_1_2_3_4_CANDIDATE" if exact else "FULL_POPULATION_VALIDATION_FAILED"
    summary = {
        "schema": "bvm-full-closed-loop-qb-screening-validation-v1",
        "experiment_id": EXP.name,
        "created_at_local": now(),
        "status": "PASS" if exact else "FAIL_VALIDATION",
        "classification": classification,
        "candidate_point_id": point["point_id"],
        "parameter": point["parameter"],
        "value": point["value"],
        "masks": VALIDATION_MASKS,
        "counts": counts,
        "cases": cases,
        "new_run_ids": [new_case_records[mask]["run_id"] for mask in ("0001", "1111")],
        "new_physical_solve_count": 2,
        "reused_screening_case_count": 2,
        "no_extra_validation_masks": True,
        "no_positional_validation_started": True,
        "no_timestep_robustness_started": True,
        "raw_authority": True,
        "phase_navigation_only": True,
        "not_sfq_count": True,
        "next_action": "stop at full population candidate" if exact else "return to preregistered broad screening; no combination automatically launched",
        "solver_sha256": SOLVER_SHA256,
        "git_head": current_head(),
    }
    json_write(existing, summary)
    md = [
        "# Full-population validation", "", f"- Candidate: `{point['point_id']}`", f"- Parameter: `{point['parameter']}={point['value']:g}`", f"- Classification: **{classification}**", "", "| mask | expected | observed candidate count | control | classification |", "|---|---:|---:|---|---|",
    ]
    for mask in VALIDATION_MASKS:
        case = cases[mask]
        md.append(f"| `{mask}` | {case['expected_count']} | {case['complete_response_candidate_count']} | {case['control_status']} | {case['classification']} |")
    md.extend(["", "Raw phase is in radians; continuous-unwrapped threshold navigation is not an SFQ count. Terminal area is not used as a count.", ""])
    (EXP / "screening/validation_summary.md").write_text("\n".join(md), encoding="utf-8")
    print(json.dumps({"status": summary["status"], "classification": classification, "counts": counts, "new_physical_solves": 2}, ensure_ascii=False, indent=2))
    return 0 if exact else 1


if __name__ == "__main__":
    raise SystemExit(main())
