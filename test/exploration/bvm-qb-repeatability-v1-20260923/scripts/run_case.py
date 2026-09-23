#!/usr/bin/env python3
"""Create and execute one immutable BVM/QB repeatability case."""

from __future__ import annotations

import argparse
import csv
import json
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from common import (REGRESSION_MATRIX, REPO, ROOT, SOLVER, legacy, now, parse_overrides, public_params,
                    read_json, render_deck, repo_rel, resolve_params, resolve_run_dir, safe_run_dir,
                    sha256, snapshot_sources, solver_identity, source_manifest,
                    write_json)


def validate_registered_invocation(case_id: str | None, overrides: dict[str, str],
                                    reference_run: str | None, params: dict[str, Any]) -> dict[str, Any] | None:
    if params["EXECUTION_SCOPE"] == "MANUAL":
        if case_id:
            raise ValueError("--registered-case is only valid with EXECUTION_SCOPE=REGRESSION_MATRIX")
        return None
    if not case_id:
        raise ValueError("REGRESSION_MATRIX scope blocks direct solves; use run_regression.py or provide a registered case")
    matrix = read_json(REGRESSION_MATRIX)
    case = next((item for item in matrix.get("cases", []) if item.get("case_id") == case_id), None)
    if case is None:
        raise ValueError(f"unregistered case ID {case_id!r}; only the frozen A–E matrix is executable in this scope")
    expected = {"NAME": case_id, **{str(k): str(v) for k, v in case.get("overrides", {}).items()}}
    if overrides != expected:
        raise ValueError(f"invocation overrides differ from registered case {case_id}; refusing solve")
    if reference_run != case.get("reference_run"):
        raise ValueError(f"reference-run binding differs from registered case {case_id}")
    preflight_path = ROOT / "analysis" / "PREFLIGHT_QA.json"
    if not preflight_path.is_file():
        raise ValueError("registered solve requires a persisted machine PREFLIGHT_QA.json")
    gate = read_json(preflight_path)
    current_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT.parents[2], text=True).strip()
    if gate.get("status") != "PASS" or gate.get("git", {}).get("head") != current_head:
        raise ValueError("registered PREFLIGHT is absent, failed, or bound to a different HEAD")
    solver = solver_identity()
    if solver.get("sha256") != gate.get("solver", {}).get("sha256") or solver.get("version") != gate.get("solver", {}).get("version"):
        raise ValueError("solver binary/version changed after registered preflight")
    source_lock = ROOT / "analysis" / "PLATFORM_SOURCE_LOCK.json"
    if not source_lock.is_file() or sha256(source_lock) != gate.get("platform_source_lock_sha256"):
        raise ValueError("PLATFORM_SOURCE_LOCK.json changed after registered preflight")
    locked_case = next((item for item in gate.get("cases", []) if item.get("case_id") == case_id), None)
    if locked_case is None or locked_case.get("parameters") != public_params(params):
        raise ValueError(f"resolved case configuration differs from the hash-bound preflight: {case_id}")
    from preflight import frozen_paths
    recorded = gate.get("source_hashes", {})
    for role, path in frozen_paths():
        # The external base ZIP is not in the physical solve's input closure and is 331 MB;
        # it is rehashed by the preflight and again by the packager, not on each solve.
        if role == "PACKAGE_BASE_ARCHIVE":
            continue
        if not path.is_file() or recorded.get(role, {}).get("sha256") != sha256(path):
            raise ValueError(f"source changed after machine preflight: {role}")
    worktree = subprocess.check_output(["git", "status", "--short", "--untracked-files=all"],
                                       cwd=ROOT.parents[2], text=True)
    registered_ids = {item["case_id"] for item in read_json(REGRESSION_MATRIX)["cases"]}
    unexpected_paths = unexpected_registered_worktree_paths(worktree, registered_ids)
    if unexpected_paths:
        raise ValueError(f"unexpected dirty/untracked paths after preflight: {unexpected_paths}")
    if reference_run:
        ref = ROOT.parents[2] / reference_run / "raw.csv"
        expected_refs = {item.get("path"): item.get("actual_sha256")
                         for item in gate.get("historical_reference_raw_checks", [])}
        ref_rel = repo_rel(ref)
        if not ref.is_file() or expected_refs.get(ref_rel) != sha256(ref):
            raise ValueError(f"historical reference raw changed after preflight: {ref_rel}")
    execution_path = ROOT / "analysis" / "REGRESSION_EXECUTION.json"
    if not execution_path.is_file():
        raise ValueError("registered children may only be launched by the A–E regression manager")
    execution = read_json(execution_path)
    matrix = read_json(REGRESSION_MATRIX)
    matrix_ids = [item["case_id"] for item in matrix["cases"]]
    current_index = matrix_ids.index(case_id)
    expected_prior_ids = matrix_ids[:current_index]
    execution_runs = execution.get("runs", [])
    actual_prior_ids = [item.get("case_id") for item in execution_runs]
    if (execution.get("preflight_status") != "PASS" or execution.get("preflight_head") != current_head or
            execution.get("preflight_qa_sha256") != sha256(preflight_path) or
            actual_prior_ids != expected_prior_ids):
        raise ValueError("execution manager ledger does not authorize this next matrix position")
    observed_run_dirs = [path.name for path in (ROOT / "runs").iterdir() if path.is_dir()]
    if set(observed_run_dirs) != set(expected_prior_ids):
        raise ValueError(f"run directory set differs from completed matrix prefix: {observed_run_dirs}")
    for record in execution_runs:
        prior_id = record["case_id"]
        prior_receipt = ROOT / "analysis" / "receipts" / f"{prior_id}.json"
        if not prior_receipt.is_file() or sha256(prior_receipt) != record.get("receipt_sha256"):
            raise ValueError(f"completed-case receipt changed: {prior_id}")
        receipt = read_json(prior_receipt)
        prior_dir = ROOT / "runs" / prior_id
        expected_tree = receipt.get("run_tree_file_sha256", {})
        current_tree = {repo_rel(path): sha256(path) for path in sorted(prior_dir.rglob("*"))
                        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"}
        if current_tree != expected_tree:
            raise ValueError(f"completed run directory changed after its solve receipt: {prior_id}")
    runs_root = ROOT / "runs"
    prior_ids = [path.name for path in runs_root.iterdir() if path.is_dir()
                 and (path.name == case_id or re.fullmatch(re.escape(case_id) + r"_attempt\d+", path.name))]
    if prior_ids:
        raise ValueError(f"registered run already exists; refusing rerun/attempt: {prior_ids}")
    return locked_case


def resolve_reference_path(reference_run: str) -> Path:
    reference = (REPO / reference_run).resolve()
    if not reference.is_relative_to(REPO.resolve()):
        raise ValueError("reference run must be within the repository")
    if not (reference / "raw.csv").is_file():
        raise ValueError(f"reference run raw.csv not found: {reference}")
    return reference


def resolve_run_path(run_id: str) -> Path:
    return resolve_run_dir(run_id)


def unexpected_registered_worktree_paths(status_porcelain: str, case_ids: set[str]) -> list[str]:
    prefix = repo_rel(ROOT)
    allowed = {f"{prefix}/analysis/PREFLIGHT_QA.json",
               f"{prefix}/analysis/REGRESSION_EXECUTION.json",
               f"{prefix}/plots/assets/plotly.min.js"}
    allowed.update(f"{prefix}/analysis/receipts/{case_id}.json" for case_id in case_ids)
    run_prefix = f"{prefix}/runs/"
    unexpected = []
    for line in status_porcelain.splitlines():
        if len(line) < 4:
            continue
        path = line[3:]
        if path in allowed:
            continue
        if path.startswith(run_prefix):
            run_id = path[len(run_prefix):].split("/", 1)[0]
            if run_id in case_ids:
                continue
        unexpected.append(path)
    return unexpected


def render_config(path: Path, params: dict[str, Any], plan: dict[str, Any]) -> None:
    lines = ["# Immutable, fully-expanded run configuration snapshot."]
    for key in sorted(public_params(params)):
        value = params[key]
        if isinstance(value, (list, dict)):
            value = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        lines.append(f"{key}={value}")
    lines.extend((f"READ_STARTS_PS={','.join(f'{x:g}' for x in plan['read_starts_ps'])}",
                  f"LAST_STIMULUS_TIME_PS={plan['last_stimulus_time_ps']:g}",
                  f"TAIL_MARGIN_PS={plan['tail_margin_ps']:g}",
                  f"STOP_PS={plan['stop_ps']:g}"))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_stimulus_snapshot(path: Path, params: dict[str, Any], plan: dict[str, Any]) -> None:
    payload = {
        "schema": "bvm-qb-repeatability-stimulus-snapshot-v1",
        "test_mode": params["TEST_MODE"], "candidate": params["CANDIDATE"],
        "array_size": params["ARRAY_SIZE"], "mask": params["MASK"],
        "bit_order": params["BIT_ORDER"], "read_schedule": plan["schedule"],
        "registered_windows": plan["cycles"],
        "last_stimulus_time_ps": plan["last_stimulus_time_ps"],
        "tail_margin_ps": plan["tail_margin_ps"], "stop_ps": plan["stop_ps"],
        "pwl_source_count": 3 * int(params["ARRAY_SIZE"]),
        "pulses": plan["pulses"],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def preview(params: dict[str, Any], plan: dict[str, Any]) -> None:
    print(f"RUN: {params['NAME']}")
    print(f"MODE: {params['TEST_MODE']}  CANDIDATE: {params['CANDIDATE']}")
    print(f"ARRAY_SIZE: {params['ARRAY_SIZE']}  MASK: {params['MASK']}  BIT_ORDER: {params['BIT_ORDER']}")
    print(f"READ_STARTS_PS: {', '.join(f'{x:g}' for x in plan['read_starts_ps'])}")
    print(f"LAST_STIMULUS_TIME_PS: {plan['last_stimulus_time_ps']:g}")
    print(f"TAIL_MARGIN_PS: {plan['tail_margin_ps']:g}  AUTO_STOP_PS: {plan['stop_ps']:g}")
    print(f"PWL_SOURCE_COUNT: {3 * int(params['ARRAY_SIZE'])}")
    print("STOP_CHECK: PASS; registered candidate search horizon is within STOP")
    print("SOLVE: not executed (--dry-run)")


def make_run(params: dict[str, Any], plan: dict[str, Any], reference_run: Path | None,
             preflight_case: dict[str, Any] | None = None) -> dict[str, Any]:
    run_dir = safe_run_dir(params)
    run_dir.mkdir(parents=True, exist_ok=False)
    (run_dir / "analysis").mkdir()
    (run_dir / "plots").mkdir()
    render_config(run_dir / "config_snapshot.env", params, plan)
    write_stimulus_snapshot(run_dir / "stimulus_snapshot.json", params, plan)
    stimulus_path = run_dir / "stimulus.inc"
    stimulus_path.write_text(plan["text"], encoding="utf-8")

    source_qa = legacy.fan_in.stimulus_source_inventory(plan["text"], int(params["ARRAY_SIZE"]))
    if source_qa.get("status") != "PASS":
        write_json(run_dir / "result.json", {
            "schema": "bvm-qb-repeatability-run-result-v1", "run_id": run_dir.name,
            "execution_status": "PREFLIGHT_FAIL", "artifact_status": "INVALID",
            "physical_solve_count": 0, "stimulus_qa": source_qa,
            "scientific_interpretation_performed": False,
        })
        raise RuntimeError(f"stimulus source inventory failed; preserved {run_dir}")

    source_snapshots = snapshot_sources(run_dir, params)
    deck_text = render_deck(run_dir, params, source_snapshots, stimulus_path)
    actual_deck = run_dir / "actual_deck.cir"
    actual_deck.write_text(deck_text, encoding="utf-8")
    if "{{" in deck_text or "MERGE" in deck_text.upper() or "MERGET" in deck_text.upper():
        raise RuntimeError(f"generated deck failed topology/static assertions; preserved {run_dir}")
    if preflight_case is not None:
        if sha256(stimulus_path) != preflight_case.get("stimulus_sha256"):
            raise RuntimeError("run-time stimulus differs from the persisted registered preflight; no solve started")
        if sha256(actual_deck) != preflight_case.get("rendered_deck_sha256"):
            raise RuntimeError("run-time deck differs from the persisted registered preflight; no solve started")
        expected_sources = preflight_case.get("rendered_source_sha256", {})
        if any(role not in expected_sources or sha256(path) != expected_sources[role]
               for role, path in source_snapshots.items()):
            raise RuntimeError("run-time source snapshot differs from the persisted registered preflight; no solve started")

    manifest = source_manifest(run_dir, params, source_snapshots, reference_run)
    write_json(run_dir / "source_manifest.json", manifest)
    raw = run_dir / "raw.csv"
    command = [str(SOLVER), "-a", "1", "-o", str(raw), str(actual_deck)]
    identity = solver_identity()
    started = now()
    wall_start = time.monotonic()
    completed = subprocess.run(command, cwd=run_dir, capture_output=True, text=True, check=False)
    runtime = time.monotonic() - wall_start
    finished = now()
    (run_dir / "stdout.txt").write_text(completed.stdout, encoding="utf-8")
    (run_dir / "stderr.txt").write_text(completed.stderr, encoding="utf-8")
    (run_dir / "run.log").write_text("\n".join((
        f"experiment={ROOT.name}", f"run_id={run_dir.name}",
        f"test_mode={params['TEST_MODE']}", f"candidate={params['CANDIDATE']}",
        f"started_at={started}", f"finished_at={finished}",
        f"runtime_seconds={runtime:.6f}", f"command={shlex.join(command)}",
        f"exit_code={completed.returncode}", "")), encoding="utf-8")

    solver_ok = completed.returncode == 0 and raw.is_file() and raw.stat().st_size > 0
    metadata: dict[str, Any] = {
        "schema": "bvm-qb-repeatability-run-metadata-v1",
        "experiment": ROOT.name, "run_id": run_dir.name,
        "execution_status": "RUN_PASS" if solver_ok else "RUN_FAIL",
        "created_at": started, "finished_at": finished,
        "runtime_seconds": runtime, "command": command, "solver": identity,
        "git": manifest["git"], "parameters": public_params(params),
        "config_snapshot": {"path": repo_rel(run_dir / "config_snapshot.env"),
                            "sha256": sha256(run_dir / "config_snapshot.env")},
        "stimulus_snapshot": {"path": repo_rel(run_dir / "stimulus_snapshot.json"),
                              "sha256": sha256(run_dir / "stimulus_snapshot.json")},
        "stimulus": {"path": repo_rel(stimulus_path), "sha256": sha256(stimulus_path)},
        "deck": {"path": repo_rel(actual_deck), "sha256": sha256(actual_deck)},
        "source_manifest": {"path": repo_rel(run_dir / "source_manifest.json"),
                            "sha256": sha256(run_dir / "source_manifest.json")},
        "raw": {"path": repo_rel(raw), "sha256": sha256(raw) if raw.is_file() else None,
                "bytes": raw.stat().st_size if raw.is_file() else 0},
        "raw_not_copied_from_history": True,
        "physical_solve_count": 1,
        "scientific_interpretation_performed": False,
        "automatic_follow_up": False,
    }
    write_json(run_dir / "metadata.json", metadata)
    if not solver_ok:
        result = {"schema": "bvm-qb-repeatability-run-result-v1", "run_id": run_dir.name,
                  "execution_status": "RUN_FAIL", "artifact_status": "INVALID",
                  "physical_solve_count": 1, "scientific_interpretation_performed": False,
                  "automatic_follow_up": False, "raw_preserved": raw.is_file()}
        write_json(run_dir / "result.json", result)
        print(json.dumps(result, ensure_ascii=False, indent=2), file=sys.stderr)
        raise RuntimeError(f"JoSIM failed; deck/raw/log/metadata preserved at {run_dir}; no automatic retry")

    try:
        import analyze_case
        analysis = analyze_case.analyze_run(run_dir)
        import plot_case
        plots = plot_case.render_run(run_dir)
    except Exception as exc:
        (run_dir / "analysis" / "analysis_error.txt").write_text(
            f"{type(exc).__name__}: {exc}\nRaw preserved; no solver retry was performed.\n", encoding="utf-8")
        failed_result = {"schema": "bvm-qb-repeatability-run-result-v1", "run_id": run_dir.name,
                         "execution_status": "RUN_PASS", "artifact_status": "INVALID",
                         "physical_solve_count": 1, "raw_sha256": sha256(raw),
                         "analysis_or_plot_error": f"{type(exc).__name__}: {exc}",
                         "scientific_interpretation_performed": False, "automatic_follow_up": False}
        write_json(run_dir / "result.json", failed_result)
        raise RuntimeError(f"post-solve analysis/plot failed; raw preserved at {raw}; do not rerun physics") from exc
    current_raw_hash = sha256(raw)
    valid = analysis.get("status") == "PASS" and plots.get("status") == "PASS" and current_raw_hash == metadata["raw"]["sha256"]
    result = {
        "schema": "bvm-qb-repeatability-run-result-v1", "run_id": run_dir.name,
        "execution_status": "RUN_PASS", "artifact_status": "VALID" if valid else "INVALID",
        "raw_sha256": current_raw_hash, "analysis_status": analysis.get("status"),
        "plot_status": plots.get("status"), "physical_solve_count": 1,
        "scientific_interpretation_performed": False, "automatic_follow_up": False,
        "candidate_counts_are_navigation_only": True,
    }
    write_json(run_dir / "result.json", result)
    metadata["analysis"] = {"status": analysis.get("status"), "raw_sha256_before_after": analysis.get("raw_sha256_before_after")}
    metadata["plots"] = {"status": plots.get("status"), "raw_sha256": plots.get("raw_sha256"),
                          "plot_manifest_sha256": plots.get("plot_manifest_sha256"),
                          "review_page_sha256": plots.get("review_page_sha256"),
                          "stimulus_page_sha256": plots.get("stimulus_page_sha256")}
    write_json(run_dir / "metadata.json", metadata)
    print(json.dumps({"run_id": run_dir.name, "artifact_status": result["artifact_status"],
                      "raw_sha256": current_raw_hash, "analysis_status": result["analysis_status"],
                      "plot_status": result["plot_status"]}, ensure_ascii=False, indent=2))
    if not valid:
        raise RuntimeError(f"analysis or visualization QA failed; raw is preserved at {raw}; do not rerun physics")
    return {"run_dir": run_dir, "result": result, "metadata": metadata}


def analyze_existing(run_id: str) -> int:
    run_dir = resolve_run_path(run_id)
    if not (run_dir / "raw.csv").is_file():
        raise ValueError(f"raw.csv not found for {run_id}")
    try:
        import analyze_case
        analysis = analyze_case.analyze_run(run_dir)
        import plot_case
        plots = plot_case.render_run(run_dir)
    except Exception as exc:
        metadata = read_json(run_dir / "metadata.json")
        result = {"schema": "bvm-qb-repeatability-run-result-v1", "run_id": run_id,
                  "execution_status": metadata.get("execution_status"), "artifact_status": "INVALID",
                  "physical_solve_count": int(metadata.get("physical_solve_count", 1)),
                  "raw_sha256": sha256(run_dir / "raw.csv"),
                  "analysis_or_plot_error": f"{type(exc).__name__}: {exc}",
                  "scientific_interpretation_performed": False, "automatic_follow_up": False,
                  "analysis_only": True}
        write_json(run_dir / "result.json", result)
        print(json.dumps(result, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2
    result = {"schema": "bvm-qb-repeatability-run-result-v1", "run_id": run_id,
              "execution_status": "RUN_PASS", "artifact_status": "VALID" if analysis.get("status") == "PASS" and plots.get("status") == "PASS" else "INVALID",
              "physical_solve_count": int(read_json(run_dir / "metadata.json").get("physical_solve_count", 1)),
              "raw_sha256": sha256(run_dir / "raw.csv"),
              "plot_raw_sha256": plots.get("raw_sha256"),
              "analysis_status": analysis.get("status"),
              "plot_status": plots.get("status"), "scientific_interpretation_performed": False,
              "automatic_follow_up": False, "analysis_only": True}
    write_json(run_dir / "result.json", result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["artifact_status"] == "VALID" else 2


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one immutable BVM-QB repeatability case")
    parser.add_argument("--set", action="append", default=[], metavar="KEY=VALUE", help="ephemeral USER_CASE override")
    parser.add_argument("--reference-run", help="repo-relative historical reference run for descriptive A/B/C comparison")
    parser.add_argument("--registered-case", help="execute one exact case from REGRESSION_MATRIX.json (registered scope only)")
    parser.add_argument("--dry-run", action="store_true", help="resolve configuration and computed schedule without solving")
    parser.add_argument("--analyze-only", metavar="RUN_ID", help="reanalyze an existing immutable raw; never invokes JoSIM")
    args = parser.parse_args()
    if args.analyze_only:
        return analyze_existing(args.analyze_only)
    overrides = parse_overrides(args.set)
    if "EXECUTION_SCOPE" in overrides:
        raise ValueError("EXECUTION_SCOPE can only be changed in USER_CASE.env, never with a per-run --set override")
    params, plan = resolve_params(overrides)
    preview(params, plan)
    if args.dry_run:
        return 0
    preflight_case = validate_registered_invocation(args.registered_case, overrides, args.reference_run, params)
    reference = None
    if args.reference_run:
        reference = resolve_reference_path(args.reference_run)
    make_run(params, plan, reference, preflight_case)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, ValueError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
