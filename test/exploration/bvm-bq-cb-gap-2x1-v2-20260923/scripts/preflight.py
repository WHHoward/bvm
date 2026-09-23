#!/usr/bin/env python3
"""No-solver preflight for the exact four-case 2x1 experiment."""

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

from common import (HERE, MATRIX, PLOTTER, REPO, ROOT, SOLVER, SOURCE_PATHS,
                    SOURCE_SNAPSHOT_NAMES, TEMPLATE, cases, current_head,
                    git_status, probe_inventory_errors, probe_signals, read_json, repo_rel, render_deck,
                    sha256, solver_identity, source_records, stimulus_text, write_json)

LOCK = ROOT / "analysis" / "SOURCE_LOCK.json"
PREFLIGHT_MD = ROOT / "PREFLIGHT.md"
EXPERIMENT = ROOT / "experiment.yaml"
MODEL_REFERENCE = REPO / "bvm_0923" / "test_bvm.cir"
METRIC_SPEC = REPO / "docs" / "research" / "METRIC_SPEC_V2.md"
PHASE_AREA_MAPPING = ROOT / "analysis" / "PHASE_AREA_MAPPING.json"
METRIC_SPEC_COPY = ROOT / "references" / "METRIC_SPEC_V2.md"
V1_INCIDENT_COPY = ROOT / "references" / "V1_INCIDENT_REPORT.md"


def frozen_paths() -> list[tuple[str, Path]]:
    script_names = ("common.py", "preflight.py", "run_matrix.py", "analyze_run.py", "independent_verify.py",
                    "plot_run.py", "finalize.py", "package.py", "test_platform.py")
    paths = [("EXPERIMENT", EXPERIMENT), ("PREFLIGHT", PREFLIGHT_MD),
             ("README", ROOT / "README.md"), ("MATRIX", MATRIX),
             ("TOP_TEMPLATE", TEMPLATE), ("PLOTTER", PLOTTER),
             ("EXPERIMENT_GITIGNORE", ROOT / ".gitignore"),
             ("GIT_ATTRIBUTES", REPO / ".gitattributes"),
             ("ADVERSARIAL_REVIEW", ROOT / "analysis" / "REVIEW.md"),
             ("NUMERICAL_REVIEW", ROOT / "analysis" / "NUMERICAL_REVIEW.md")]
    paths.extend((f"SCRIPT_{name.removesuffix('.py').upper()}", HERE / name)
                 for name in script_names)
    paths.extend((role, path) for role, path in SOURCE_PATHS.items())
    paths.append(("MODEL_REFERENCE", MODEL_REFERENCE))
    paths.extend((("METRIC_SPEC", METRIC_SPEC), ("PHASE_AREA_MAPPING", PHASE_AREA_MAPPING)))
    paths.extend((("METRIC_SPEC_COPY", METRIC_SPEC_COPY), ("V1_INCIDENT_COPY", V1_INCIDENT_COPY)))
    return paths


def experiment_parent_head() -> str:
    match = re.search(r"(?m)^parent_head:\s*([0-9a-f]{40})\s*$",
                      EXPERIMENT.read_text(encoding="utf-8"))
    if not match:
        raise ValueError("experiment.yaml parent_head missing/malformed")
    return match.group(1)


def experiment_is_aborted() -> bool:
    return bool(re.search(r"(?m)^execution_status:\s*ABORTED_PENDING_USER_DIRECTION\s*$",
                          EXPERIMENT.read_text(encoding="utf-8")))


def normalized_body(text: str) -> list[str]:
    return [" ".join(line.strip().lower().split()) for line in text.splitlines()
            if line.strip() and not line.lstrip().startswith("*")]


def check_registered_sources() -> list[str]:
    errors = []
    text = EXPERIMENT.read_text(encoding="utf-8")
    registered = {}
    for match in re.finditer(r"(?m)^  - path: ([^\n]+)\n    sha256: ([0-9a-f]{64})\n    provenance: AUTHOR_PROVIDED$", text):
        registered[match.group(1)] = match.group(2)
    expected = {repo_rel(path): sha256(path) for path in SOURCE_PATHS.values()}
    if registered != expected:
        errors.append(f"experiment.yaml source hashes differ from current canonical files: registered={registered}, actual={expected}")
    fixture_lines = [line.strip().lower() for line in MODEL_REFERENCE.read_text(encoding="utf-8").splitlines()
                     if line.strip().lower().startswith(".model jjmit")]
    template_lines = [line.strip().lower() for line in TEMPLATE.read_text(encoding="utf-8").splitlines()
                      if line.strip().lower().startswith(".model jjmit")]
    if len(fixture_lines) != 1 or len(template_lines) != 1 or " ".join(fixture_lines[0].split()) != " ".join(template_lines[0].split()):
        errors.append("top-level jjmit model line does not exactly match bvm_0923/test_bvm.cir")
    metric_hash = sha256(METRIC_SPEC)
    if metric_hash not in text:
        errors.append("experiment.yaml does not hash-bind METRIC_SPEC_V2.md")
    if not METRIC_SPEC_COPY.is_file() or sha256(METRIC_SPEC_COPY) != metric_hash:
        errors.append("experiment-local METRIC_SPEC_V2 copy differs from the frozen canonical file")
    incident_hash = "c1837603a632951099c091322f7682a5a2befc61b3f245c390d4867ce76b6e38"
    if not V1_INCIDENT_COPY.is_file() or sha256(V1_INCIDENT_COPY) != incident_hash or incident_hash not in text:
        errors.append("v1 incident reference copy hash mismatch")
    if ("references/V1_INCIDENT_REPORT.md" not in text or
            "references/METRIC_SPEC_V2.md" not in text):
        errors.append("experiment.yaml does not identify its local provenance references")
    mapping = read_json(PHASE_AREA_MAPPING)
    if mapping.get("metric_spec", {}).get("sha256") != metric_hash:
        errors.append("phase-area mapping registry refers to a different metric spec hash")
    return errors


def check_matrix_static(matrix: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if matrix.get("schema") != "bvm-bq-cb-gap-2x1-matrix-v2" or matrix.get("experiment_id") != "bvm-bq-cb-gap-2x1-v2-20260923":
        errors.append("matrix schema or experiment_id is not the authorized v2")
    expected = ["N0_00", "N1_01", "N1_10", "N2_11"]
    items = matrix.get("cases", [])
    if [item.get("run_id") for item in items] != expected:
        errors.append("matrix run IDs/order differ from the frozen 00/01/10/11 set")
    if matrix.get("authorized_physical_solve_count") != 4 or len(items) != 4:
        errors.append("matrix must authorize exactly four physical solves")
    if matrix.get("dt") != "0.01p" or matrix.get("stop") != "200p" or matrix.get("save_start") != "0p":
        errors.append("matrix DT/STOP/save-start differ from the newly preregistered values")
    bit_map = {item.get("mask"): item.get("active_bvms") for item in items}
    if bit_map != {"00": [], "01": [2], "10": [1], "11": [1, 2]}:
        errors.append(f"mask bit-order mapping is wrong: {bit_map}")
    if matrix.get("scientific_interpretation_performed") is not False:
        errors.append("machine matrix must keep scientific interpretation disabled")
    grid_contract = matrix.get("actual_grid_contract", {})
    if (grid_contract.get("time_column_unit") != "seconds" or
            grid_contract.get("required_start_ps") != 0.0 or
            grid_contract.get("minimum_end_ps") != 199.99):
        errors.append("raw time coverage contract differs from registered START/STOP/DT")
    metric_spec = matrix.get("metric_spec", {})
    if metric_spec.get("path") != repo_rel(METRIC_SPEC) or metric_spec.get("sha256") != sha256(METRIC_SPEC):
        errors.append("matrix does not bind current METRIC_SPEC_V2.md identity")
    expected_instances = ["XBVM1", "XBQ1", "XCB1", "XACC1", "XGAP1",
                         "XBVM2", "XBQ2", "XCB2", "XACC2", "XGAP2"]
    if matrix.get("topology", {}).get("instances") != expected_instances:
        errors.append("matrix cell instance list differs from the exact ten-cell topology")
    if matrix.get("terminal_pointwise_delta_direction") != "V(R_TERM)_case - V(R_TERM)_N0_00":
        errors.append("registered terminal pointwise delta direction is not case minus N0_00")
    mapping = read_json(PHASE_AREA_MAPPING)
    expected_stages = {"BQ1_BJ3", "BQ2_BJ3", "CB1_BJ2", "CB2_BJ2",
                       "ACC1_BJ1", "ACC2_BJ1", "GAP1_BJ1", "GAP2_BJ1"}
    mapping_rows = mapping.get("mappings", [])
    if {row.get("stage") for row in mapping_rows} != expected_stages or len(mapping_rows) != len(expected_stages):
        errors.append("phase-area mapping must cover exactly the eight registered JJ stages")
    if any(row.get("reporting_direction") != 1 or row.get("voltage_to_phase_sign") != 1
           for row in mapping_rows):
        errors.append("registered P/V branch directions differ from the frozen pin-order convention")
    if mapping.get("tolerance_status") != "UNFROZEN; residuals are descriptive only":
        errors.append("phase-area residuals must remain descriptive because tolerance is unfrozen")
    preflight = PREFLIGHT_MD.read_text(encoding="utf-8")
    match = re.search(r"(?m)^Frozen matrix SHA-256:\s*`([0-9a-f]{64})`\s*$", preflight)
    if not match or match.group(1) != sha256(MATRIX):
        errors.append("REGRESSION_MATRIX hash does not match PREFLIGHT.md")
    return errors


def render_case_preview(item: dict[str, Any]) -> dict[str, Any]:
    run_id = item["run_id"]
    with tempfile.TemporaryDirectory(prefix=f"{run_id}_preflight_") as temp:
        temp_root = Path(temp)
        source_dir = temp_root / "snapshot" / "sources"
        source_dir.mkdir(parents=True)
        rendered_sources = {}
        for role, source in SOURCE_PATHS.items():
            target = source_dir / SOURCE_SNAPSHOT_NAMES[role]
            target.write_bytes(source.read_bytes())
            rendered_sources[role] = sha256(target)
        stimulus = stimulus_text(item["mask"])
        stimulus_path = temp_root / "stimulus.inc"
        stimulus_path.write_text(stimulus, encoding="utf-8")
        deck_text = render_deck(stimulus_path.name)
        deck_path = temp_root / "actual_deck.cir"
        deck_path.write_text(deck_text, encoding="utf-8")
        active = ["xbvm1", "xbvm2"]
        if not all(token in "\n".join(normalized_body(deck_text)) for token in active):
            raise ValueError("both BVM instances must be instantiated")
        body = normalized_body(deck_text)
        instances = [line.split()[0] for line in body if line.split()[0].startswith("x")]
        expected_instances = ["xbvm1", "xbq1", "xcb1", "xacc1", "xgap1",
                              "xbvm2", "xbq2", "xcb2", "xacc2", "xgap2"]
        if instances != expected_instances:
            raise ValueError(f"instantiated cell list differs from exact ten-cell topology: {instances}")
        required_links = ("xgap1 acc1_out gap2_in sjtl", "xacc2 cb2_out gap2_in sjtl",
                          "xgap2 gap2_in final_out sjtl", "r_term final_out 0 2")
        if not all(link in body for link in required_links):
            raise ValueError("frozen direct-common GAP2 topology differs from registration")
        expected_local = ("xbvm1 wl1 bl1 se1 bvm1_sl bvm", "xbq1 bvm1_sl qb1_out bq",
                          "xcb1 qb1_out cb1_out cb", "xacc1 cb1_out acc1_out sjtl",
                          "xbvm2 wl2 bl2 se2 bvm2_sl bvm", "xbq2 bvm2_sl qb2_out bq",
                          "xcb2 qb2_out cb2_out cb")
        if not all(link in body for link in expected_local):
            raise ValueError("one or more registered local branches differ")
        prohibited = ("merge", "merget", "common_sl", "jsl", "t1", "old_jtl2", "xgap1_extra")
        if any(token in "\n".join(body) for token in prohibited):
            raise ValueError("forbidden old/shared/T1 topology token found in rendered deck")
        lines = [line.strip() for line in stimulus.splitlines()
                 if line.strip() and not line.lstrip().startswith("*")]
        if len(lines) != 6 or {line.split()[0] for line in lines} != {
                "I_WL1", "I_BL1", "I_SE1", "I_WL2", "I_BL2", "I_SE2"}:
            raise ValueError("stimulus must contain exactly six registered source lines")
        probes = probe_signals()
        inventory_errors = probe_inventory_errors()
        if inventory_errors:
            raise ValueError("probe/source inventory mismatch: " + "; ".join(inventory_errors))
        if len(probes) != len(set(probes)):
            raise ValueError("required probe labels contain duplicates")
        missing = [signal for signal in probes if f".print {signal}".lower() not in deck_text.lower()]
        if missing:
            raise ValueError(f"required probes absent from rendered deck: {missing[:10]}")
        if ".tran 0.01p 200p 0p" not in deck_text.lower():
            raise ValueError("rendered .tran does not match 0.01p/200p/0p")
        if ".model jjmit jj(rtype=1, vg=2.8m, cap=0.07p, r0=160, rn=16, icrit=0.1m)" not in deck_text.lower():
            raise ValueError("jjmit model does not match bvm_0923/test_bvm.cir")
        return {"run_id": run_id, "mask": item["mask"], "active_bvms": item["active_bvms"],
                "purpose": item["purpose"], "probe_count": len(probes),
                "pwl_source_count": len(lines), "stimulus_sha256": sha256(stimulus_path),
                "rendered_deck_sha256": sha256(deck_path),
                "rendered_source_sha256": rendered_sources,
                "read_schedule_ps": [{"start": 110, "end": 121}],
                "registered_windows_ps": read_json(MATRIX)["windows_ps"],
                "actual_grid_contract": read_json(MATRIX)["actual_grid_contract"],
                "dt": "0.01p", "stop": "200p", "no_solver_executed": True}


def freeze_source_lock() -> dict[str, Any]:
    if experiment_is_aborted():
        raise RuntimeError("experiment is incident-aborted; do not freeze a solve source lock")
    missing = [f"{role}: {path}" for role, path in frozen_paths() if not path.is_file()]
    if missing:
        raise RuntimeError(f"cannot freeze source lock; missing files: {missing}")
    parent = experiment_parent_head()
    matrix = read_json(MATRIX)
    static_errors = check_matrix_static(matrix) + check_registered_sources()
    if static_errors:
        raise RuntimeError("cannot freeze source lock: " + "; ".join(static_errors))
    if parent != "286eeaadf92b34c4d6550e6ff748cca3b3841726":
        raise RuntimeError("experiment parent HEAD differs from the confirmed 2026-09-23 start HEAD")
    payload = {
        "schema": "bvm-bq-cb-gap-source-lock-v1",
        "created_at": __import__("datetime").datetime.now().astimezone().isoformat(timespec="seconds"),
        "initial_parent_head": parent,
        "authorized_run_ids": [item["run_id"] for item in matrix["cases"]],
        "authorized_physical_solve_count": 4,
        "regression_matrix_sha256": sha256(MATRIX),
        "source_hashes": {role: {"path": repo_rel(path), "sha256": sha256(path)}
                          for role, path in frozen_paths()},
        "solver": solver_identity(), "scientific_interpretation_performed": False,
    }
    write_json(LOCK, payload)
    return payload


LOCK = ROOT / "analysis" / "SOURCE_LOCK.json"


def build_gate(require_clean: bool) -> dict[str, Any]:
    errors: list[str] = []
    if experiment_is_aborted():
        errors.append("experiment is incident-aborted; new authorization and a fresh versioned experiment are required")
    try:
        matrix = read_json(MATRIX)
        errors.extend(check_matrix_static(matrix))
        errors.extend(check_registered_sources())
        cases_plan = [render_case_preview(item) for item in matrix.get("cases", [])]
    except Exception as exc:
        cases_plan = []
        errors.append(f"render/preflight error: {type(exc).__name__}: {exc}")
    head = current_head()
    parent = experiment_parent_head()
    if subprocess.run(["git", "merge-base", "--is-ancestor", parent, head], cwd=REPO,
                      capture_output=True, check=False).returncode != 0:
        errors.append("current HEAD is not descended from the registered parent HEAD")
    if require_clean and git_status().strip():
        errors.append("physical preflight requires a committed clean worktree")
    if not SOLVER.is_file():
        errors.append(f"solver missing: {SOLVER}")
    if not (ROOT / "analysis" / "SOURCE_LOCK.json").is_file():
        errors.append("analysis/SOURCE_LOCK.json is missing; freeze source closure before solving")
        lock = {}
    else:
        lock = read_json(ROOT / "analysis" / "SOURCE_LOCK.json")
        if lock.get("initial_parent_head") != parent or lock.get("regression_matrix_sha256") != sha256(MATRIX):
            errors.append("source lock parent/matrix identity mismatch")
        for role, path in frozen_paths():
            item = lock.get("source_hashes", {}).get(role, {})
            if item.get("path") != repo_rel(path) or item.get("sha256") != sha256(path):
                errors.append(f"frozen source hash mismatch: {role}")
        solver = solver_identity()
        if lock.get("solver", {}).get("sha256") != solver.get("sha256") or lock.get("solver", {}).get("version") != solver.get("version"):
            errors.append("solver binary/version differs from SOURCE_LOCK.json")
    run_root = ROOT / "runs"
    run_dirs = [path.name for path in run_root.iterdir() if path.is_dir() and path.name != "__pycache__"] if run_root.exists() else []
    if run_dirs:
        errors.append(f"registered runs already exist before preflight: {run_dirs}")
    if (ROOT / "analysis" / "EXECUTION.json").exists():
        errors.append("analysis/EXECUTION.json already exists; refusing to overwrite")
    receipts = ROOT / "analysis" / "receipts"
    if receipts.exists() and any(receipts.iterdir()):
        errors.append("run receipts already exist; refusing a second matrix execution")
    return {
        "schema": "bvm-bq-cb-gap-preflight-v1", "status": "PASS" if not errors else "FAIL",
        "created_at": __import__("datetime").datetime.now().astimezone().isoformat(timespec="seconds"),
        "head": head, "parent_head": parent, "git_dirty": bool(git_status().strip()),
        "solver": solver_identity() if SOLVER.is_file() else {"status": "MISSING"},
        "source_lock_sha256": sha256(LOCK) if LOCK.is_file() else None,
        "authorized_solve_count": 4, "matrix_sha256": sha256(MATRIX),
        "cases": cases_plan, "errors": errors,
        "scientific_interpretation_performed": False, "no_solve_executed": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Preflight the exact N0/N1/N1/N2 BVM-BQ-CB-GAP matrix")
    parser.add_argument("--dry-run", action="store_true", help="validate without writing PREFLIGHT_QA")
    parser.add_argument("--write", action="store_true", help="write analysis/PREFLIGHT_QA.json")
    parser.add_argument("--freeze-source-lock", action="store_true", help="freeze source hashes; no solve")
    parser.add_argument("--static-only", action="store_true", help="validate registration and rendered decks in Python only; does not invoke JoSIM")
    args = parser.parse_args()
    if args.freeze_source_lock:
        print(json.dumps(freeze_source_lock(), ensure_ascii=False, indent=2))
        return 0
    if args.dry_run and args.write:
        raise RuntimeError("--dry-run and --write are mutually exclusive")
    qa = build_gate(require_clean=args.write)
    if args.write:
        write_json(ROOT / "analysis" / "PREFLIGHT_QA.json", qa)
    print(json.dumps(qa, ensure_ascii=False, indent=2))
    if args.static_only:
        remaining = [error for error in qa["errors"]
                     if error != "analysis/SOURCE_LOCK.json is missing; freeze source closure before solving"]
        static_ok = not remaining and bool(qa.get("cases"))
        qa["status"] = "PASS_STATIC_ONLY" if static_ok else "FAIL_STATIC_ONLY"
        qa["errors"] = remaining
        qa["physical_solve_executed"] = False
        print(json.dumps({"static_status": qa["status"], "errors": qa["errors"],
                          "transient_solver_invoked": False,
                          "solver_version_query_only": True,
                          "physical_solve_executed": False}, ensure_ascii=False, indent=2))
        return 0 if static_ok else 2
    return 0 if qa["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
