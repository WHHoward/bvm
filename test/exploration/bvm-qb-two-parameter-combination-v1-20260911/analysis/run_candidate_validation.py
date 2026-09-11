#!/usr/bin/env python3
"""Run the only permitted full-population validation after an S point."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


EXP = Path(__file__).resolve().parents[1]
REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(EXP / "analysis"))
from combination_analysis import case_evidence, load  # noqa: E402
from prepare_combination import build_deck  # noqa: E402
from run_combination import current_head, load_gate, rel, run_physical, sha256, write_json  # noqa: E402


VALIDATION_MASKS = ("0001", "0011", "0111", "1111")


def validation_deck(point: dict[str, Any], mask: str) -> Path:
    variant = Path(point["variant_path"]).name
    target = EXP / "screening/validation_decks" / point["point_id"] / f"{mask}.cir"
    content = build_deck(point["point_id"], point["changes"], mask, variant)
    if target.exists() and target.read_text(encoding="utf-8") != content:
        raise RuntimeError(f"refusing to overwrite validation deck: {target}")
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    return target


def mask_evidence(raw: Path, mask: str) -> dict[str, Any]:
    evidence = case_evidence(load(raw))
    expected = {"0001": 1, "0011": 2, "0111": 3, "1111": 4}[mask]
    ordered = evidence["ordered_chain_by_candidate"]
    exact = evidence["control"]["status"] == "CLEAN" and evidence["complete_response_candidate_count"] == expected and all(ordered.get(str(index), False) for index in range(1, expected + 1)) and not ordered.get(str(expected + 1), False)
    return {"mask": mask, "expected_count": expected, "classification": f"MASK_{mask}_{expected}_COMPLETE" if exact else "MASK_NOT_EXPECTED", "control_status": evidence["control"]["status"], "complete_response_candidate_count": evidence["complete_response_candidate_count"], "ordered_chain_by_candidate": ordered, "raw_path": rel(raw), "raw_sha256": sha256(raw), "evidence": evidence}


def main() -> int:
    _preflight, matrix, _relation = load_gate()
    candidate_path = EXP / "screening/CANDIDATE_FOUND.json"
    if not candidate_path.is_file():
        raise RuntimeError("candidate validation requested without a candidate record")
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    point = next(item for item in matrix["points"] if item["point_id"] == candidate["point_id"])
    summary_path = EXP / "screening/validation_summary.json"
    if summary_path.is_file():
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        return 0 if summary.get("classification") == "FULL_POPULATION_1_2_3_4_CANDIDATE" else 1
    new_cases: dict[str, Any] = {}
    for mask in ("0001", "1111"):
        new_cases[mask] = run_physical(point, mask, validation_deck(point, mask), prefix="VALIDATION")
    state = json.loads((EXP / "screening/combination_state.json").read_text(encoding="utf-8"))
    point_state = state["points"][point["point_id"]]
    raw_paths = {mask: REPO / new_cases[mask]["raw_path"] for mask in ("0001", "1111")}
    raw_paths["0011"] = REPO / point_state["cases"]["0011"]["raw_path"]
    raw_paths["0111"] = REPO / point_state["cases"]["0111"]["raw_path"]
    cases = {mask: mask_evidence(raw_paths[mask], mask) for mask in VALIDATION_MASKS}
    counts = {mask: cases[mask]["complete_response_candidate_count"] for mask in VALIDATION_MASKS}
    exact = counts == {"0001": 1, "0011": 2, "0111": 3, "1111": 4} and all(cases[mask]["classification"] == f"MASK_{mask}_{counts[mask]}_COMPLETE" for mask in VALIDATION_MASKS)
    classification = "FULL_POPULATION_1_2_3_4_CANDIDATE" if exact else "FULL_POPULATION_VALIDATION_FAILED"
    summary = {"schema": "bvm-qb-two-parameter-combination-validation-v1", "experiment_id": EXP.name, "created_at_local": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"), "status": "PASS" if exact else "FAIL_VALIDATION", "classification": classification, "candidate_point_id": point["point_id"], "changes": point["changes"], "cases": cases, "counts": counts, "new_run_ids": [new_cases["0001"]["run_id"], new_cases["1111"]["run_id"]], "new_physical_solve_count": 2, "reused_screening_case_count": 2, "no_positional_validation_started": True, "no_timestep_robustness_started": True, "no_third_parameter_started": True, "raw_authority": True, "phase_navigation_only": True, "not_sfq_count": True, "git_head": current_head()}
    write_json(summary_path, summary)
    lines = ["# Full population validation", "", f"Candidate: {point['point_id']}", f"Classification: {classification}", "", "| mask | expected | observed | control | classification |", "|---|---:|---:|---|---|"]
    for mask in VALIDATION_MASKS:
        case = cases[mask]
        lines.append(f"| {mask} | {case['expected_count']} | {case['complete_response_candidate_count']} | {case['control_status']} | {case['classification']} |")
    lines.extend(["", "Phase values remain raw-radian navigation diagnostics; no phase or terminal area is treated as an SFQ count.", ""])
    (EXP / "screening/validation_summary.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"status": summary["status"], "classification": classification, "counts": counts, "new_physical_solves": 2}, ensure_ascii=False, indent=2))
    return 0 if exact else 1


if __name__ == "__main__":
    raise SystemExit(main())
