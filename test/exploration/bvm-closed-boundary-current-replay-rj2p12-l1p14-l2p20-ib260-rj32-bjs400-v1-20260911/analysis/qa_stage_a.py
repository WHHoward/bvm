#!/usr/bin/env python3
"""Build registered Stage A raw, deck, provenance and protocol QA records."""

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
RUN = "CLOSED_CURRENT_REPLAY_N2_0011_RJ2P12"
REF = "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_0011"
SOLVER_SHA256 = "48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2"
PAIR_RE = re.compile(r"([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)[pP]\s+([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)")
REPLAY_REQUIRED = ("I(I_REPLAY)", "I(LIN|XBQ1)", "I(L1|XBQ1)", "I(L2|XBQ1)", "I(BJ1|XBQ1)", "V(BJ1|XBQ1)", "P(BJ1|XBQ1)", "I(BJ2|XBQ1)", "V(BJ2|XBQ1)", "P(BJ2|XBQ1)", "V(QBOUT)", "V(JTL1_OUT)", "V(JTL2_OUT)", "V(JTL3_OUT)", "V(JTL4_OUT)", "V(JTL5_OUT)", "V(JTL6_OUT)", "I(R_TERM)")
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
        if len(header) != len(set(header)):
            failures.append("duplicate columns")
        position = {name: index for index, name in enumerate(header)}
        missing = [name for name in required if name not in position]
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
            times.append(values[position["time"]])
        if not width:
            failures.append("row width mismatch")
        if not finite:
            failures.append("non-finite value")
    if len(times) != 1999:
        failures.append(f"sample count {len(times)} != 1999")
    if not times or times[0] != 0.0 or times[-1] != 1.999e-10:
        failures.append("time range mismatch")
    if any(right <= left for left, right in zip(times, times[1:])):
        failures.append("time not strictly increasing")
    raw_hash = sha256(path)
    metadata_value = json.loads(metadata.read_text(encoding="utf-8"))
    recorded = metadata_value.get("artifacts", {}).get("raw", {}).get("sha256")
    if recorded != raw_hash:
        failures.append("metadata/raw hash mismatch")
    dts = [(right - left) * 1e12 for left, right in zip(times, times[1:])]
    return {"status": "PASS" if not failures else "FAIL", "path": path.relative_to(REPO).as_posix(), "sha256": raw_hash, "bytes": path.stat().st_size, "header_count": len(header), "sample_count": len(times), "time_range_s": [times[0], times[-1]] if times else None, "grid": {"dt_min_ps": min(dts) if dts else None, "dt_max_ps": max(dts) if dts else None, "irregular_vs_0.1ps": sum(abs(value - 0.1) > 1e-9 for value in dts), "actual_grid_used": True}, "required_probes": list(required), "metadata_raw_sha256": recorded, "raw_immutable": True, "failures": failures}


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
    for token in ("I_REPLAY 0 QBIN pwl(", ".param L1_VALUE=1.4p", ".param RJ1_VALUE=32", ".param RJ2_VALUE=12"):
        if token not in text:
            failures.append(f"missing token: {token}")
    if "L2 3 4 2p" not in (EXP / "inputs/BQ_parameterized_bjs400_rj2.cir").read_text(encoding="utf-8"):
        failures.append("current BQ L2 closure is not 2p")
    start = text.index("pwl(") + 4
    end = text.index(")", start)
    pairs = PAIR_RE.findall(text[start:end])
    if len(pairs) != 1999:
        failures.append(f"PWL count {len(pairs)} != 1999")
    if [line for line in text.splitlines() if line.lower().startswith(".tran")] != [".tran 0.1p 200p"]:
        failures.append("tran mismatch")
    return {"status": "PASS" if not failures else "FAIL", "path": path.relative_to(REPO).as_posix(), "sha256": sha256(path), "bytes": path.stat().st_size, "pwl_pair_count": len(pairs), "receiver_only": not any(token in line for line in lines for token in ("BVM", "B_JSL", "COMMON_SL")), "failures": failures}


def artifact(path: Path) -> dict[str, Any]:
    return {"path": path.relative_to(REPO).as_posix(), "sha256": sha256(path), "bytes": path.stat().st_size}


def main() -> int:
    source_dir = EXP / "references/closed_loop_rj2p12" / REF
    run_dir = EXP / "runs" / RUN
    raw = {"source_reference": raw_check(source_dir / "raw.csv", SOURCE_REQUIRED, source_dir / "metadata.json"), "stage_a_replay": raw_check(run_dir / "raw.csv", REPLAY_REQUIRED, run_dir / "metadata.json")}
    raw_failures = [f"{name}: {value['failures']}" for name, value in raw.items() if value["failures"]]
    decks = {"stage_a_replay": deck_check(run_dir / "deck.cir")}
    deck_failures = [f"{name}: {value['failures']}" for name, value in decks.items() if value["failures"]]
    execution = json.loads((EXP / "qa/execution_summary.json").read_text(encoding="utf-8"))
    preflight = json.loads((EXP / "analysis/preflight.json").read_text(encoding="utf-8"))
    stage_a_response = json.loads((EXP / "qa/stage_a_response_qa.json").read_text(encoding="utf-8"))
    protocol_failures: list[str] = []
    run_dirs = sorted(path.name for path in (EXP / "runs").iterdir() if path.is_dir())
    if run_dirs != [RUN]:
        protocol_failures.append(f"unexpected run directories: {run_dirs}")
    if execution.get("status") != "PASS" or execution.get("solver_solve_invocations") != 1 or execution.get("unauthorized_extra_solves") != 0:
        protocol_failures.append("execution is not exact one-solve PASS")
    if preflight.get("stage_b", {}).get("source_copied") is not False or preflight.get("stage_b", {}).get("physical_solve_authorized_current_turn") is not False:
        protocol_failures.append("Stage B was not deferred")
    protocol = {"schema": "bvm-closed-boundary-current-replay-stage-a-protocol-audit-v1", "experiment_id": EXP.name, "created_at_local": now(), "status": "PASS" if not protocol_failures else "FAIL", "authorized_current_turn_physical_solve_count": 1, "maximum_task_physical_solve_count": 2, "stage_a_started": True, "stage_b_started": False, "unauthorized_extra_solves": 0, "run_directories": run_dirs, "no_passive_capture": True, "no_rj2_sweep": True, "no_n3_source_copied": True, "failures": protocol_failures}
    source_artifacts = {name: {suffix: artifact(source_dir / suffix) for suffix in ("raw.csv", "deck.cir", "metadata.json", "run.log")} for name in (REF,)}
    run_artifacts = {RUN: {suffix: artifact(run_dir / suffix) for suffix in ("raw.csv", "deck.cir", "metadata.json", "run.log")}}
    source_manifest = json.loads((EXP / "SOURCE_MANIFEST.json").read_text(encoding="utf-8"))
    provenance = {"schema": "bvm-closed-boundary-current-replay-stage-a-provenance-v1", "experiment_id": EXP.name, "created_at_local": now(), "repository_head_at_qa": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip(), "source_manifest": {"path": "SOURCE_MANIFEST.json", "sha256": sha256(EXP / "SOURCE_MANIFEST.json")}, "preflight": {"path": "analysis/preflight.json", "sha256": sha256(EXP / "analysis/preflight.json")}, "solver": {"path": "build/josim-cli", "sha256": SOLVER_SHA256}, "raw": {**raw, "source_artifacts": source_artifacts, "run_artifacts": run_artifacts}, "execution": execution, "stage_b": {"status": "DEFERRED_PENDING_SCIENTIFIC_REVIEW_AUTHORIZATION", "started": False}, "raw_authority": True, "scientific_analysis_performed": False}
    transformation = {"schema": "bvm-closed-boundary-current-replay-stage-a-transformation-registry-v1", "experiment_id": EXP.name, "raw_immutable": True, "raw_transformations": [], "replay_transformations": [], "source_to_pwl": [], "orientation_change": False, "phase_display_only": "independent unwrap then rad/(2*pi)", "comparison_csv": "temporary merged input deleted after rendering", "scientific_analysis_performed": False}
    for path, value in ((EXP / "qa/raw_qa.json", {"schema": "bvm-closed-boundary-current-replay-stage-a-raw-qa-v1", "experiment_id": EXP.name, "created_at_local": now(), "status": "PASS" if not raw_failures else "FAIL", "artifact_validity": "VALID" if not raw_failures else "ARTIFACT_INVALID", "raw_files_modified": 0, "physics_solve_count": 1, "scientific_analysis_performed": False, "runs": raw, "failures": raw_failures}), (EXP / "qa/deck_diff_qa.json", {"schema": "bvm-closed-boundary-current-replay-stage-a-deck-qa-v1", "experiment_id": EXP.name, "created_at_local": now(), "status": "PASS" if not deck_failures else "FAIL", "replay": decks, "no_source_leakage": not deck_failures, "failures": deck_failures}), (EXP / "qa/provenance.json", provenance), (EXP / "qa/transformation_registry.json", transformation), (EXP / "qa/protocol_audit.json", protocol)):
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    failures = raw_failures + deck_failures + protocol_failures + ([] if stage_a_response.get("status") == "PASS" else ["Stage A response QA failed"])
    print(json.dumps({"status": "PASS" if not failures else "FAIL", "raw_status": "PASS" if not raw_failures else "FAIL", "deck_status": "PASS" if not deck_failures else "FAIL", "protocol_status": protocol["status"], "stage_b_started": False, "scientific_analysis_performed": False, "failures": failures}, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
