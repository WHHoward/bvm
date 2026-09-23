#!/usr/bin/env python3
"""Machine execution gate for the exact five-case A–E platform batch."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from common import (JJ_SOURCE, JTL_SOURCE, PLOTTER, PROFILES, REFERENCE,
                    REGRESSION_MATRIX, REPO, ROOT, SOLVER, USER_CASE, legacy,
                    file_record, git_snapshot, read_json, render_deck,
                    resolve_params, sha256, snapshot_sources, solver_identity,
                    write_json)
LOCK_PATH = ROOT / "analysis" / "PLATFORM_SOURCE_LOCK.json"
EXPERIMENT = ROOT / "experiment.yaml"


def commit_exists(commit: str) -> bool:
    return subprocess.run(["git", "cat-file", "-e", f"{commit}^{{commit}}"], cwd=ROOT.parents[2],
                          capture_output=True, check=False).returncode == 0


def frozen_paths() -> list[tuple[str, Path]]:
    paths = [
        ("USER_CASE", USER_CASE), ("REFERENCE", REFERENCE), ("CANDIDATE_PROFILES", PROFILES),
        ("REGRESSION_MATRIX", REGRESSION_MATRIX), ("PREFLIGHT_SCOPE", ROOT / "analysis" / "REFERENCE_ANALYSIS_SCOPE.json"),
        ("PACKAGE_CHECKPOINTS", ROOT / "analysis" / "PACKAGE_CHECKPOINTS.json"),
        ("PLATFORM_NUMERICAL_QA", ROOT / "analysis" / "PLATFORM_NUMERICAL_QA.json"),
        ("PACKAGE_BASE_ARCHIVE", ROOT.parents[2] / "test" / "exploration" / "bvm-qb-50ghz-merge-v1-20260922" / "handoff" / "bvm-qb-50ghz-merge-v1-20260922_raw_handoff_classic-v4.zip"),
        ("EXPERIMENT", EXPERIMENT), ("PREFLIGHT_MARKDOWN", ROOT / "PREFLIGHT.md"),
        ("README", ROOT / "README.md"), ("GIT_ATTRIBUTES", ROOT.parents[2] / ".gitattributes"),
        ("BVM_TEMPLATE", ROOT / "circuits" / "bvm_tunable.cir"),
        ("QB_TEMPLATE", ROOT / "circuits" / "bq_tunable.cir"),
        ("TOP_TEMPLATE", ROOT / "circuits" / "top_template.cir"),
        ("JJ_MODEL", JJ_SOURCE), ("JTL", JTL_SOURCE), ("PLOTTER", PLOTTER),
        ("RUNNER", ROOT / "scripts" / "run_case.py"),
        ("COMMON", ROOT / "scripts" / "common.py"), ("STIMULUS", ROOT / "scripts" / "stimulus.py"),
        ("ANALYZER", ROOT / "scripts" / "analyze_case.py"), ("PLOT_CASE", ROOT / "scripts" / "plot_case.py"),
        ("PREFLIGHT", ROOT / "scripts" / "preflight.py"),
        ("REGRESSION_RUNNER", ROOT / "scripts" / "run_regression.py"),
        ("SWEEP_RUNNER", ROOT / "scripts" / "run_sweep.py"),
        ("FINALIZER", ROOT / "scripts" / "finalize.py"), ("PACKAGER", ROOT / "scripts" / "package.py"),
        ("PLATFORM_TESTS", ROOT / "tests" / "test_platform.py"),
        ("ONE_SHOT_RENDERER", ROOT.parents[2] / "test" / "exploration" / "bvm-rloop-one-shot-tuning-v1-20260918" / "scripts" / "run_candidate.py"),
        ("ONE_SHOT_ARRAY_MASK_HELPER", ROOT.parents[2] / "test" / "exploration" / "bvm-rloop-one-shot-tuning-v1-20260918" / "scripts" / "fan_in.py"),
        ("ONE_SHOT_BVM_TEMPLATE", ROOT.parents[2] / "test" / "exploration" / "bvm-rloop-one-shot-tuning-v1-20260918" / "circuits" / "bvm_tunable.cir"),
        ("ONE_SHOT_QB_TEMPLATE", ROOT.parents[2] / "test" / "exploration" / "bvm-rloop-one-shot-tuning-v1-20260918" / "circuits" / "bq_tunable.cir"),
        ("ONE_SHOT_TOP_TEMPLATE", ROOT.parents[2] / "test" / "exploration" / "bvm-rloop-one-shot-tuning-v1-20260918" / "circuits" / "closed_top.cir"),
    ]
    matrix = read_json(REGRESSION_MATRIX)
    for case in matrix.get("cases", []):
        reference = case.get("reference_run")
        if not reference:
            continue
        run = REPO / reference
        suffix = str(case["case_id"])
        paths.extend([
            (f"{suffix}_REFERENCE_METADATA", run / "metadata.json"),
            (f"{suffix}_REFERENCE_DECK", run / "actual_deck.cir"),
            (f"{suffix}_REFERENCE_STIMULUS", run / "stimulus.inc"),
            (f"{suffix}_REFERENCE_SOURCE_MANIFEST", run / "source_manifest.json"),
            (f"{suffix}_REFERENCE_BVM", run / "snapshot" / "sources" / "bvm_tunable.cir"),
            (f"{suffix}_REFERENCE_QB", run / "snapshot" / "sources" / "bq_tunable.cir"),
            (f"{suffix}_REFERENCE_JJ", run / "snapshot" / "sources" / "jjmit.cir"),
            (f"{suffix}_REFERENCE_JTL", run / "snapshot" / "sources" / "jtl2.cir"),
        ])
    return paths


def authorized_ids_from_experiment() -> list[str]:
    text = EXPERIMENT.read_text(encoding="utf-8")
    match = re.search(r"(?ms)^authorized_regression_cases:\s*\n((?:^[ \t]+-\s+[^\n]+\n)+)", text)
    if not match:
        raise ValueError("experiment.yaml has no authorized_regression_cases sequence")
    return [item.strip() for item in re.findall(r"^[ \t]+-\s+(.+?)\s*$", match.group(1), flags=re.MULTILINE)]


def freeze_source_lock() -> dict[str, Any]:
    missing = [f"{role}={path}" for role, path in frozen_paths() if not path.is_file()]
    if missing:
        raise RuntimeError(f"cannot freeze source lock; required source(s) missing: {missing}")
    parent_match = re.search(r"(?m)^parent_head:\s*([0-9a-f]{40})\s*$", EXPERIMENT.read_text(encoding="utf-8"))
    if not parent_match:
        raise RuntimeError("experiment.yaml parent_head is missing or malformed")
    matrix = read_json(REGRESSION_MATRIX)
    case_ids = [case.get("case_id") for case in matrix.get("cases", [])]
    if case_ids != authorized_ids_from_experiment() or len(case_ids) != 5 or matrix.get("authorized_solve_count") != 5:
        raise RuntimeError("cannot freeze source lock: A–E matrix differs from the experiment authorization")
    preflight_text = (ROOT / "PREFLIGHT.md").read_text(encoding="utf-8")
    matrix_lock = re.search(r"(?m)^Frozen A–E matrix SHA-256:\s*`([0-9a-f]{64})`\s*$", preflight_text)
    if not matrix_lock or matrix_lock.group(1) != sha256(REGRESSION_MATRIX):
        raise RuntimeError("cannot freeze source lock: REGRESSION_MATRIX hash differs from PREFLIGHT.md")
    lock = {"schema": "bvm-qb-repeatability-platform-source-lock-v1",
            "created_at": __import__("datetime").datetime.now().astimezone().isoformat(timespec="seconds"),
            "initial_parent_head": parent_match.group(1),
            "authorized_case_ids": case_ids, "authorized_solve_count": 5,
            "regression_matrix_sha256": sha256(REGRESSION_MATRIX),
            "source_hashes": {role: {"path": path.relative_to(ROOT.parents[2]).as_posix(), "sha256": sha256(path)}
                              for role, path in frozen_paths()},
            "solver": solver_identity(),
            "scientific_interpretation_performed": False}
    write_json(LOCK_PATH, lock)
    return lock


def build_gate(require_clean: bool = False) -> dict[str, Any]:
    errors: list[str] = []
    matrix = read_json(REGRESSION_MATRIX)
    cases = matrix.get("cases", [])
    authorized = int(matrix.get("authorized_solve_count", -1))
    if authorized != 5 or len(cases) != 5:
        errors.append(f"exact A–E matrix must contain five cases, got declared={authorized}, actual={len(cases)}")
    case_ids = [case.get("case_id") for case in cases]
    if len(set(case_ids)) != len(case_ids):
        errors.append("REGRESSION_MATRIX.json contains duplicate case_id values")
    if matrix.get("scientific_interpretation_performed") is not False:
        errors.append("regression matrix must prohibit scientific interpretation")
    parent_match = None
    try:
        authorized_ids = authorized_ids_from_experiment()
        if case_ids != authorized_ids:
            errors.append(f"REGRESSION_MATRIX case IDs/order differ from experiment.yaml authority: {case_ids} != {authorized_ids}")
        parent_match = re.search(r"(?m)^parent_head:\s*([0-9a-f]{40})\s*$", EXPERIMENT.read_text(encoding="utf-8"))
        if not parent_match:
            errors.append("experiment.yaml parent_head is missing or malformed")
        elif subprocess.run(["git", "merge-base", "--is-ancestor", parent_match.group(1),
                             subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT.parents[2], text=True).strip()],
                             cwd=ROOT.parents[2], capture_output=True, check=False).returncode != 0:
            errors.append("current HEAD is not descended from experiment.yaml parent_head")
    except Exception as exc:
        errors.append(f"authority check failed: {type(exc).__name__}: {exc}")

    try:
        preflight_text = (ROOT / "PREFLIGHT.md").read_text(encoding="utf-8")
        matrix_lock = re.search(r"(?m)^Frozen A–E matrix SHA-256:\s*`([0-9a-f]{64})`\s*$", preflight_text)
        if not matrix_lock or matrix_lock.group(1) != sha256(REGRESSION_MATRIX):
            errors.append("REGRESSION_MATRIX.json hash differs from the preregistered PREFLIGHT.md hash")
    except OSError as exc:
        errors.append(f"cannot read preflight matrix authority: {exc}")
    user = ROOT / "USER_CASE.env"
    # An enabled sweep is never implicit in the registered A–E runner.
    from common import load_env
    if load_env(user).get("SWEEP_ENABLED", "no").lower() != "no":
        errors.append("SWEEP_ENABLED must be no for the registered platform build")

    scope_path = ROOT / "analysis" / "REFERENCE_ANALYSIS_SCOPE.json"
    scope = read_json(scope_path)
    reference_records = []
    for item in scope.get("authorized_inputs", []):
        path = (ROOT.parents[2] / item["path"]).resolve()
        if not path.is_file():
            errors.append(f"historical reference raw missing: {item['path']}")
            continue
        actual_hash = sha256(path)
        reference_records.append({"path": item["path"], "expected_sha256": item["sha256"], "actual_sha256": actual_hash})
        if actual_hash != item["sha256"]:
            errors.append(f"historical reference raw hash changed: {item['path']}")

    planned: list[dict[str, Any]] = []
    for case in cases:
        case_id = str(case.get("case_id", ""))
        overrides = {str(k): str(v) for k, v in case.get("overrides", {}).items()}
        overrides["NAME"] = case_id
        try:
            params, plan = resolve_params(overrides)
            if case_id != params["NAME"]:
                errors.append(f"{case_id}: resolved NAME differs")
            if len(plan["text"].splitlines()) != 2 + 3 * int(params["ARRAY_SIZE"]):
                errors.append(f"{case_id}: generated PWL source-line count is wrong")
            source_qa = legacy.fan_in.stimulus_source_inventory(plan["text"], int(params["ARRAY_SIZE"]))
            if source_qa.get("status") != "PASS":
                errors.append(f"{case_id}: stimulus source inventory failed: {source_qa}")
            if plan["stop_ps"] <= plan["last_stimulus_time_ps"]:
                errors.append(f"{case_id}: STOP does not cover final stimulus")
            if plan["stop_ps"] < plan["last_stimulus_time_ps"] + float(params["LATENCY_MAX_PS"]):
                errors.append(f"{case_id}: STOP truncates terminal search horizon")
            # Render in a disposable directory: no repository run artifact is created by preflight.
            with tempfile.TemporaryDirectory(prefix="bvm_repeat_preflight_") as temporary:
                temp_run = Path(temporary)
                stimulus_path = temp_run / "stimulus.inc"
                stimulus_path.write_text(plan["text"], encoding="utf-8")
                sources = snapshot_sources(temp_run, params)
                deck_text = render_deck(temp_run, params, sources, stimulus_path)
                if any(token in deck_text.upper() for token in ("MERGE", "MERGET")):
                    errors.append(f"{case_id}: forbidden topology token in generated deck")
                required = [row[0] for row in legacy.requested_signals("closed", params)]
                missing = sorted(set(signal for signal in required if signal not in deck_text))
                if missing:
                    errors.append(f"{case_id}: required probes absent from rendered deck: {missing[:10]}")
                rendered_sources = {key: sha256(value) for key, value in sources.items()}
                deck_hash = __import__("hashlib").sha256(deck_text.encode("utf-8")).hexdigest()
            reference_run = case.get("reference_run")
            reference_raw = None
            if reference_run:
                reference_raw_path = ROOT.parents[2] / reference_run / "raw.csv"
                reference_raw = {"path": reference_run + "/raw.csv",
                                 "sha256": sha256(reference_raw_path) if reference_raw_path.is_file() else None}
                if not reference_raw_path.is_file():
                    errors.append(f"{case_id}: named historical raw missing: {reference_raw_path}")
                if not params["TEST_MODE"] == "REPEAT_READ":
                    errors.append(f"{case_id}: only A/B/C may bind a Phase-A reference raw")
            elif params["TEST_MODE"] == "REPEAT_READ" and case_id in {"REG_A_QB2X1_N1", "REG_B_QB2X1_N2", "REG_C_QB3X1_N3"}:
                errors.append(f"{case_id}: required historical raw reference missing")
            planned.append({"case_id": case_id, "purpose": case.get("purpose"),
                            "parameters": {k: v for k, v in params.items() if not k.startswith("_")},
                            "schedule": plan["schedule"], "cycle_windows": plan["cycles"],
                            "last_stimulus_time_ps": plan["last_stimulus_time_ps"],
                            "tail_margin_ps": plan["tail_margin_ps"], "stop_ps": plan["stop_ps"],
                            "stimulus_sha256": __import__("hashlib").sha256(plan["text"].encode("utf-8")).hexdigest(),
                            "rendered_deck_sha256": deck_hash, "rendered_source_sha256": rendered_sources,
                            "source_inventory": source_qa, "reference_raw": reference_raw})
            if (ROOT / "runs" / case_id).exists():
                errors.append(f"{case_id}: run ID already exists; preflight will not overwrite it")
        except Exception as exc:  # preserve all gate diagnostics in one report
            errors.append(f"{case_id}: {type(exc).__name__}: {exc}")

    parent = git_snapshot()
    if require_clean and parent["working_tree_dirty"]:
        errors.append("execution preflight requires committed sources and a clean worktree")
    if require_clean:
        existing = [path.name for path in (ROOT / "runs").iterdir()
                    if path.is_dir() and ((path / "metadata.json").exists() or (path / "raw.csv").exists())]
        if existing:
            errors.append(f"registered execution preflight requires an empty runs/ directory: {existing}")
        if (ROOT / "analysis" / "REGRESSION_EXECUTION.json").exists() or (
                ROOT / "analysis" / "receipts").exists() and any((ROOT / "analysis" / "receipts").iterdir()):
            errors.append("registered execution receipts already exist; refusing a second regression execution")
    solver = solver_identity() if SOLVER.is_file() else {"path": str(SOLVER), "status": "MISSING"}
    if solver.get("status") == "MISSING":
        errors.append(f"solver missing: {SOLVER}")
    source_paths = frozen_paths()
    source_hashes = {role: {"path": str(path.relative_to(ROOT.parents[2])), "sha256": sha256(path)}
                     for role, path in source_paths if path.is_file()}
    for role, path in source_paths:
        if not path.is_file():
            errors.append(f"required preflight source missing: {role}={path}")
    if not LOCK_PATH.is_file():
        errors.append("PLATFORM_SOURCE_LOCK.json missing; source closure is not frozen")
        lock = {}
    else:
        lock = read_json(LOCK_PATH)
        locked = lock.get("source_hashes", {})
        if lock.get("regression_matrix_sha256") != sha256(REGRESSION_MATRIX) or lock.get("authorized_case_ids") != case_ids or lock.get("authorized_solve_count") != 5:
            errors.append("registered matrix identity differs from PLATFORM_SOURCE_LOCK.json")
        for role, path in source_paths:
            actual = sha256(path) if path.is_file() else None
            record = locked.get(role, {})
            expected_path = path.relative_to(ROOT.parents[2]).as_posix()
            if record.get("path") != expected_path or record.get("sha256") != actual:
                errors.append(f"frozen source hash mismatch: {role}")
        if lock.get("solver", {}).get("sha256") != solver.get("sha256") or lock.get("solver", {}).get("version") != solver.get("version"):
            errors.append("solver binary/version differs from PLATFORM_SOURCE_LOCK.json")
        if not parent_match or lock.get("initial_parent_head") != parent_match.group(1):
            errors.append("source lock and experiment.yaml parent_head disagree")
    checkpoints = read_json(ROOT / "analysis" / "PACKAGE_CHECKPOINTS.json").get("checkpoints", [])
    for checkpoint in checkpoints:
        package_path = ROOT.parents[2] / checkpoint.get("package_path", "")
        if not package_path.is_file() or sha256(package_path) != checkpoint.get("package_sha256"):
            errors.append(f"delta base package identity mismatch: {checkpoint.get('package_name')}")
        if not checkpoint.get("head_commit") or not commit_exists(str(checkpoint["head_commit"])):
            errors.append(f"delta base commit is absent: {checkpoint.get('head_commit')}")
    return {
        "schema": "bvm-qb-repeatability-preflight-qa-v1",
        "status": "PASS" if not errors else "FAIL",
        "created_at": __import__("datetime").datetime.now().astimezone().isoformat(timespec="seconds"),
        "git": parent, "solver": solver, "source_hashes": source_hashes,
        "platform_source_lock_sha256": sha256(LOCK_PATH) if LOCK_PATH.is_file() else None,
        "authorized_solve_count": authorized, "planned_case_count": len(planned),
        "cases": planned, "historical_reference_raw_checks": reference_records,
        "errors": errors, "no_solve_executed": True,
        "scientific_interpretation_performed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Preflight the exact registered five-run matrix")
    parser.add_argument("--write", action="store_true", help="persist analysis/PREFLIGHT_QA.json")
    parser.add_argument("--freeze-source-lock", action="store_true", help="freeze source hashes before committing the platform; no solver runs")
    args = parser.parse_args()
    if args.freeze_source_lock:
        lock = freeze_source_lock()
        print(json.dumps(lock, ensure_ascii=False, indent=2))
        return 0
    qa = build_gate(require_clean=args.write)
    if args.write:
        write_json(ROOT / "analysis" / "PREFLIGHT_QA.json", qa)
    print(json.dumps(qa, ensure_ascii=False, indent=2))
    return 0 if qa["status"] == "PASS" else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, ValueError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
