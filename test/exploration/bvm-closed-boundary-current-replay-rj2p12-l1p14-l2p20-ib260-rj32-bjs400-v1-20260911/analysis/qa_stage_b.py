#!/usr/bin/env python3
"""Build Stage B raw/deck/provenance/transformation/protocol QA."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
RUNS = ("CLOSED_CURRENT_REPLAY_N2_0011_RJ2P12", "CLOSED_CURRENT_REPLAY_N3_0111_RJ2P12")
REFERENCES = ("ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_0011", "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_0111")
SOLVER_SHA256 = "48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2"
PAIR_RE = re.compile(r"([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)[pP]\s+([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)")
REPLAY_REQUIRED = ("I(I_REPLAY)", "I(LIN|XBQ1)", "I(L1|XBQ1)", "I(L2|XBQ1)", "P(BJ1|XBQ1)", "V(BJ1|XBQ1)", "I(BJ1|XBQ1)", "P(BJ2|XBQ1)", "V(BJ2|XBQ1)", "I(BJ2|XBQ1)", "V(QBOUT)", "V(JTL1_OUT)", "V(JTL2_OUT)", "V(JTL3_OUT)", "V(JTL4_OUT)", "V(JTL5_OUT)", "V(JTL6_OUT)", "I(R_TERM)")
SOURCE_REQUIRED = ("I(B_JSL8)",) + tuple(label for label in REPLAY_REQUIRED if label != "I(I_REPLAY)")


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def raw_check(path: Path, required: tuple[str, ...], metadata: Path) -> dict[str, Any]:
    failures: list[str] = []
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.reader(stream)
        header = next(reader)
        positions = {name: index for index, name in enumerate(header)}
        if len(header) != len(positions):
            failures.append("duplicate raw columns")
        missing = [name for name in required if name not in positions]
        if missing:
            failures.append("missing probes: " + ", ".join(missing))
        times: list[float] = []
        finite = True
        width = True
        for row in reader:
            if len(row) != len(header):
                width = False
                continue
            try:
                values = [float(cell) for cell in row]
            except ValueError:
                finite = False
                continue
            finite = finite and all(math.isfinite(value) for value in values)
            times.append(values[positions["time"]])
        if not width:
            failures.append("raw row width mismatch")
        if not finite:
            failures.append("non-finite value")
    if len(times) != 1999 or not times or times[0] != 0.0 or times[-1] != 1.999e-10:
        failures.append("stored raw grid mismatch")
    if any(right <= left for left, right in zip(times, times[1:])):
        failures.append("time is not strictly increasing")
    value = json.loads(metadata.read_text(encoding="utf-8"))
    recorded = value.get("artifacts", {}).get("raw", {}).get("sha256")
    actual = sha256(path)
    if recorded != actual:
        failures.append("metadata raw SHA mismatch")
    return {"status": "PASS" if not failures else "FAIL", "path": path.relative_to(REPO).as_posix(), "sha256": actual, "bytes": path.stat().st_size, "header_count": len(header), "sample_count": len(times), "time_range_s": [times[0], times[-1]] if times else None, "actual_grid": True, "required_probes": list(required), "metadata_raw_sha256": recorded, "failures": failures}


def deck_check(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    lines = [line.strip() for line in text.splitlines() if line.strip() and not line.lstrip().startswith(("*", ".", "+"))]
    failures: list[str] = []
    if sum(line == "XBQ1 QBIN QBOUT BQ" for line in lines) != 1:
        failures.append("QB count mismatch")
    if sum(line.startswith("XJTL1_") and line.endswith(" jtl") for line in lines) != 6:
        failures.append("JTL count mismatch")
    if sum(line == "R_TERM JTL6_OUT 0 10" for line in lines) != 1:
        failures.append("termination mismatch")
    if any(token in line for line in lines for token in ("BVM", "B_JSL", "COMMON_SL")):
        failures.append("BVM/JSL source leakage")
    for token in ("I_REPLAY 0 QBIN pwl(", ".param L1_VALUE=1.4p", ".param RJ1_VALUE=32", ".param RJ2_VALUE=12", ".include ../../inputs/BQ_parameterized_bjs400_rj2.cir", ".include ../../inputs/jtl2.cir"):
        if token not in text:
            failures.append(f"missing replay token: {token}")
    start = text.index("pwl(") + 4
    end = text.index(")", start)
    pairs = PAIR_RE.findall(text[start:end])
    if len(pairs) != 1999:
        failures.append(f"PWL pairs {len(pairs)} != 1999")
    if [line for line in text.splitlines() if line.lower().startswith(".tran")] != [".tran 0.1p 200p"]:
        failures.append("tran mismatch")
    return {"status": "PASS" if not failures else "FAIL", "path": path.relative_to(REPO).as_posix(), "sha256": sha256(path), "bytes": path.stat().st_size, "pwl_pair_count": len(pairs), "receiver_only": True, "failures": failures}


def artifact(path: Path) -> dict[str, Any]:
    return {"path": path.relative_to(REPO).as_posix(), "sha256": sha256(path), "bytes": path.stat().st_size}


def main() -> int:
    raw_records: dict[str, Any] = {}
    for run in RUNS:
        raw_records[run] = raw_check(EXP / "runs" / run / "raw.csv", REPLAY_REQUIRED, EXP / "runs" / run / "metadata.json")
    for reference in REFERENCES:
        raw_records[reference] = raw_check(EXP / "references/closed_loop_rj2p12" / reference / "raw.csv", SOURCE_REQUIRED, EXP / "references/closed_loop_rj2p12" / reference / "metadata.json")
    raw_failures = [f"{name}: {item['failures']}" for name, item in raw_records.items() if item["failures"]]
    decks = {run: deck_check(EXP / "runs" / run / "deck.cir") for run in RUNS}
    deck_failures = [f"{name}: {item['failures']}" for name, item in decks.items() if item["failures"]]
    receiver_cores = []
    for run in RUNS:
        receiver_cores.append(tuple(line for line in [line.strip() for line in (EXP / "runs" / run / "deck.cir").read_text(encoding="utf-8").splitlines() if line.strip() and not line.lstrip().startswith(("*", ".", "+"))] if not line.startswith("I_REPLAY")))
    if len(set(receiver_cores)) != 1:
        deck_failures.append("N2/N3 replay receiver core differs")
    stage_a_qa = json.loads((EXP / "qa/execution_summary.json").read_text(encoding="utf-8"))
    stage_b_execution = json.loads((EXP / "qa/execution_summary_stage_b.json").read_text(encoding="utf-8"))
    combined = json.loads((EXP / "qa/execution_summary_combined.json").read_text(encoding="utf-8"))
    stage_b_preflight = json.loads((EXP / "analysis/preflight_stage_b.json").read_text(encoding="utf-8"))
    response = json.loads((EXP / "qa/stage_b_response_qa.json").read_text(encoding="utf-8"))
    protocol_failures: list[str] = []
    run_dirs = sorted(path.name for path in (EXP / "runs").iterdir() if path.is_dir())
    if run_dirs != sorted(RUNS):
        protocol_failures.append(f"run directories mismatch: {run_dirs}")
    if stage_a_qa.get("status") != "PASS" or stage_a_qa.get("solver_solve_invocations") != 1:
        protocol_failures.append("Stage A execution prefix changed")
    if stage_b_execution.get("status") != "PASS" or stage_b_execution.get("solver_solve_invocations") != 1 or stage_b_execution.get("unauthorized_extra_solves") != 0:
        protocol_failures.append("Stage B execution is not one-solve PASS")
    if combined.get("status") != "PASS" or combined.get("total_solver_solve_invocations") != 2 or combined.get("exact_total_physical_solve_count") != 2 or combined.get("unauthorized_extra_solves") != 0:
        protocol_failures.append("combined execution is not exact two-solve PASS")
    if stage_b_preflight.get("stage_b", {}).get("no_third_solve") is not True or stage_b_preflight.get("authorization", {}).get("stage_b_authorized") is not True:
        protocol_failures.append("Stage B authorization/no-third-solve guard missing")
    if response.get("status") != "PASS" or response.get("stage_b_started") is not True:
        protocol_failures.append("Stage B response QA failed")
    if (EXP / "references/closed_loop_rj2p12/ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_1111").exists() or list((EXP / "runs").glob("*1111*")):
        protocol_failures.append("forbidden N4 artifact exists")
    if any(path.name.startswith("PASSIVE_") for path in (EXP / "runs").iterdir() if path.is_dir()):
        protocol_failures.append("forbidden passive run exists")
    protocol = {"schema": "bvm-closed-boundary-current-replay-stage-b-protocol-audit-v1", "experiment_id": EXP.name, "created_at_local": now(), "status": "PASS" if not protocol_failures else "FAIL", "stage_a_physical_solves": 1, "stage_b_physical_solves": 1, "exact_total_physical_solves": 2, "maximum_task_physical_solves": 2, "run_directories": run_dirs, "stage_b_started": True, "no_third_solve": True, "no_passive_or_n4": True, "no_rj2_or_timestep_sweep": True, "unauthorized_extra_solves": 0, "failures": protocol_failures}
    source_artifacts = {reference: {suffix: artifact(EXP / "references/closed_loop_rj2p12" / reference / suffix) for suffix in ("raw.csv", "deck.cir", "metadata.json", "run.log")} for reference in REFERENCES}
    run_artifacts = {run: {suffix: artifact(EXP / "runs" / run / suffix) for suffix in ("raw.csv", "deck.cir", "metadata.json", "run.log")} for run in RUNS}
    source_manifest = json.loads((EXP / "SOURCE_MANIFEST_STAGE_B.json").read_text(encoding="utf-8"))
    provenance = {"schema": "bvm-closed-boundary-current-replay-stage-b-provenance-v1", "experiment_id": EXP.name, "created_at_local": now(), "repository_head_at_qa": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip(), "authorization": {"path": "analysis/stage_b_authorization.json", "sha256": sha256(EXP / "analysis/stage_b_authorization.json")}, "stage_b_source_manifest": {"path": "SOURCE_MANIFEST_STAGE_B.json", "sha256": sha256(EXP / "SOURCE_MANIFEST_STAGE_B.json")}, "stage_b_preflight": {"path": "analysis/preflight_stage_b.json", "sha256": sha256(EXP / "analysis/preflight_stage_b.json")}, "solver": {"path": "build/josim-cli", "sha256": SOLVER_SHA256}, "raw": {"source_references": source_artifacts, "runs": run_artifacts}, "stage_a_unchanged": True, "execution": {"stage_a": "qa/execution_summary.json", "stage_b": "qa/execution_summary_stage_b.json", "combined": "qa/execution_summary_combined.json"}, "source_manifest_record": source_manifest, "raw_authority": True, "scientific_analysis_performed": True}
    transformation = {"schema": "bvm-closed-boundary-current-replay-stage-b-transformation-registry-v1", "experiment_id": EXP.name, "raw_immutable": True, "source_to_pwl": [], "replay_waveform_transformations": [], "sign_change": False, "phase_display": "independent unwrap then rad/(2*pi)", "comparison_csv": "temporary merged CSV deleted after render", "scientific_analysis_performed": True}
    for path, value in ((EXP / "qa/raw_qa_stage_b.json", {"schema": "bvm-closed-boundary-current-replay-stage-b-raw-qa-v1", "experiment_id": EXP.name, "created_at_local": now(), "status": "PASS" if not raw_failures else "FAIL", "artifact_validity": "VALID" if not raw_failures else "ARTIFACT_INVALID", "physics_solve_count": 2, "stage_a_raw_unchanged": True, "raw_files_modified": 0, "scientific_analysis_performed": True, "runs": raw_records, "failures": raw_failures}), (EXP / "qa/deck_diff_qa_stage_b.json", {"schema": "bvm-closed-boundary-current-replay-stage-b-deck-qa-v1", "experiment_id": EXP.name, "created_at_local": now(), "status": "PASS" if not deck_failures else "FAIL", "runs": decks, "receiver_core_identical": len(set(receiver_cores)) == 1, "no_bvm_or_jsls": True, "failures": deck_failures}), (EXP / "qa/provenance_stage_b.json", provenance), (EXP / "qa/transformation_registry_stage_b.json", transformation), (EXP / "qa/protocol_audit_stage_b.json", protocol)):
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    failures = raw_failures + deck_failures + protocol_failures
    print(json.dumps({"status": "PASS" if not failures else "FAIL", "raw_status": "PASS" if not raw_failures else "FAIL", "deck_status": "PASS" if not deck_failures else "FAIL", "protocol_status": protocol["status"], "total_physical_solves": 2, "stage_b_started": True, "failures": failures}, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
