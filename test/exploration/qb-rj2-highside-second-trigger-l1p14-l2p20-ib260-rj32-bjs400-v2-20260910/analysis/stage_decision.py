#!/usr/bin/env python3
"""Run mechanical QA and make the registered CONTINUE/STOP stage decision."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
QA = EXP / "analysis/qa_pipeline.py"
REGISTERED_NEW_RUNS = (
    "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_0001",
    "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_0011",
    "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P14_0001",
    "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P14_0011",
    "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P16_0001",
    "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P16_0011",
)
STAGES = {1: REGISTERED_NEW_RUNS[0:2], 2: REGISTERED_NEW_RUNS[2:4], 3: REGISTERED_NEW_RUNS[4:6]}


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def update_authorized_runs(active: list[str]) -> dict[str, Any]:
    path = EXP / "experiment.yaml"
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("experiment.yaml is not a mapping")
    previous = value.get("authorized_runs")
    value["authorized_runs"] = [f"runs/{run_id}" for run_id in active]
    value["actual_authorized_runs_after_stop"] = [f"runs/{run_id}" for run_id in active]
    value["authorization_update_reason"] = "stage decision STOP; unrun registered decks remain preserved under runs/"
    path.write_text(yaml.safe_dump(value, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return {"previous": previous, "updated": value["authorized_runs"]}


def copy_stage_artifacts(stage: int, decision: dict[str, Any]) -> None:
    target = EXP / "qa/stages"
    target.mkdir(parents=True, exist_ok=True)
    for source_name, target_name in (
        ("raw_qa.json", f"stage{stage}_raw_qa.json"),
        ("deck_diff_qa.json", f"stage{stage}_deck_diff_qa.json"),
        ("execution_summary.json", f"stage{stage}_execution_summary.json"),
        ("protocol_audit.json", f"stage{stage}_protocol_audit.json"),
    ):
        shutil.copy2(EXP / "qa" / source_name, target / target_name)
    shutil.copy2(EXP / "mechanical_summary.json", target / f"stage{stage}_mechanical_summary.json")
    (target / f"stage{stage}_decision.json").write_text(json.dumps(decision, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", type=int, choices=sorted(STAGES), required=True)
    args = parser.parse_args()
    stage = args.stage
    execution = load(EXP / "qa/execution_summary.json")
    expected_pair = STAGES[stage]
    actual_order = tuple(execution.get("run_order", ()))
    if actual_order[-len(expected_pair):] != expected_pair:
        raise RuntimeError(f"stage {stage} was not executed as the final completed pair: {actual_order}")

    qa_run = subprocess.run([sys.executable, str(QA)], cwd=REPO, capture_output=True, text=True, check=False)
    if qa_run.returncode != 0:
        raise RuntimeError(f"mechanical QA failed before stage decision:\n{qa_run.stdout}\n{qa_run.stderr}")
    mechanical = load(EXP / "mechanical_summary.json")
    raw_qa = load(EXP / "qa/raw_qa.json")
    deck_qa = load(EXP / "qa/deck_diff_qa.json")
    protocol = load(EXP / "qa/protocol_audit.json")
    cases = mechanical.get("cases", {})
    stage_cases = {run_id: cases.get(run_id, {}) for run_id in expected_pair}
    execution_failures = [run_id for run_id in expected_pair if run_id not in actual_order or stage_cases[run_id].get("physical_solve_this_experiment") is not True]
    control_failure_cases = [run_id for run_id, case in stage_cases.items() if case.get("CONTROL_HARD_GUARDRAIL", {}).get("status") != "CLEAN"]
    first_response_failure_cases = [run_id for run_id, case in stage_cases.items() if case.get(f"FIRST_RESPONSE_{run_id.rsplit('_', 1)[1]}", {}).get("status") != "BOUNDED_RESULT"]
    first_response_0001_failure_cases = [run_id for run_id in first_response_failure_cases if run_id.endswith("_0001")]
    first_clean = not control_failure_cases and not first_response_failure_cases
    second_response_candidate_cases = [
        run_id for run_id, case in stage_cases.items()
        if first_clean and case.get("SECOND_TRIGGER_ANALYSIS", {}).get("second_complete_multi_evidence_candidate", {}).get("status") == "BOUNDED_RESULT"
    ]
    reasons: list[str] = []
    if execution_failures:
        reasons.append("EXECUTION_FAILURE")
    if raw_qa.get("status") != "PASS" or deck_qa.get("status") != "PASS":
        reasons.append("QA_FAILURE")
    if control_failure_cases:
        reasons.append("CONTROL_FAILURE")
    if first_response_failure_cases:
        reasons.append("FIRST_RESPONSE_FAILURE")
    if second_response_candidate_cases:
        reasons.append("SECOND_RESPONSE_CANDIDATE")
    if protocol.get("status") != "PASS":
        reasons.append("PROTOCOL_AUDIT_FAILURE")
    if not reasons and stage == 3:
        reasons.append("MATRIX_EXHAUSTED")
    decision_value = "STOP" if reasons else "CONTINUE"
    decision = {
        "schema": "bjs400-rj2-highside-second-trigger-stage-decision-v2",
        "experiment_id": EXP.name,
        "stage": stage,
        "rj2_ohm": float(expected_pair[0].split("RJ2P", 1)[1].split("_", 1)[0]),
        "registered_pair": list(expected_pair),
        "execution_run_order": list(actual_order),
        "decision": decision_value,
        "stop_reasons": reasons,
        "execution_failure_cases": execution_failures,
        "control_failure_cases": control_failure_cases,
        "first_response_failure_cases": first_response_failure_cases,
        "first_response_0001_failure_cases": first_response_0001_failure_cases,
        "second_response_candidate_cases": second_response_candidate_cases,
        "second_response_evaluated_only_if_control_and_first_clean": True,
        "protocol_audit_status": protocol.get("status"),
        "qa_status": {"raw": raw_qa.get("status"), "deck": deck_qa.get("status"), "mechanical": mechanical.get("status")},
        "guardrail_policy": "STOP on control/first-response failure or, only when both are clean, a second multi-evidence candidate; otherwise CONTINUE until stage 3 matrix exhaustion",
        "created_at_local": now(),
        "scientific_interpretation_performed": False,
    }

    if decision_value == "STOP":
        execution["early_stop_reason"] = f"STAGE_{reasons[0]}:stage{stage}"
        execution["stop_stage"] = stage
        execution["stop_reasons"] = reasons
        execution["registered_unrun_values"] = [run_id for run_id in REGISTERED_NEW_RUNS if run_id not in actual_order]
        authorization_update = update_authorized_runs(list(actual_order))
        decision["authorized_runs_update"] = authorization_update
    execution.setdefault("stage_decisions", []).append(decision)
    execution["last_stage_decision"] = decision_value
    execution["finished_at_local"] = now()
    (EXP / "qa/execution_summary.json").write_text(json.dumps(execution, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # Re-run only arithmetic/mechanical QA after the decision metadata changes;
    # no raw or deck is touched and no solver is invoked.
    qa_after = subprocess.run([sys.executable, str(QA)], cwd=REPO, capture_output=True, text=True, check=False)
    if qa_after.returncode != 0:
        raise RuntimeError(f"mechanical QA failed after stage decision:\n{qa_after.stdout}\n{qa_after.stderr}")
    decision["qa_after_decision_status"] = load(EXP / "qa/raw_qa.json").get("status")
    copy_stage_artifacts(stage, decision)
    (EXP / "qa/stages" / f"stage{stage}_decision.json").write_text(json.dumps(decision, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "stage": stage, "decision": decision_value, "stop_reasons": reasons, "control_failure_cases": control_failure_cases, "first_response_failure_cases": first_response_failure_cases, "second_response_candidate_cases": second_response_candidate_cases, "scientific_analysis_performed": False}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
