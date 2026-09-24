#!/usr/bin/env python3
"""User-facing preview and bounded multi-mask batch runner."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from components import (
    GROUP_KEYS, load_reference, parameter_manifest as make_parameter_manifest,
    verify_reference_sources,
)
from config import ConfigError, STIMULUS_KEYS, USER_CASE_KEYS, load_env, validate_user_case
from run_case import (
    allocate_run_id, json_text, render_case, stable_env, topology_signature,
    execute_run,
)
from stimulus import load_stimulus, validate_stimulus


SERIES = Path(__file__).resolve().parents[1]
REPO = next(path for path in (SERIES, *SERIES.parents) if (path / ".git").exists())
OVERRIDE_KEYS = USER_CASE_KEYS | STIMULUS_KEYS
NAME_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def parse_overrides(items: list[str]) -> dict[str, str]:
    overrides: dict[str, str] = {}
    for item in items:
        if "=" not in item:
            raise ConfigError(f"--set expects KEY=VALUE, got {item!r}")
        key, value = (part.strip() for part in item.split("=", 1))
        if key not in OVERRIDE_KEYS:
            raise ConfigError(f"unknown --set key {key!r}")
        if not value:
            raise ConfigError(f"--set value for {key} must not be empty")
        if key in overrides:
            raise ConfigError(f"duplicate --set key {key}")
        overrides[key] = value
    return overrides


def load_effective(user_path: Path, stimulus_path: Path, override_items: list[str]
                   ) -> tuple[dict[str, str], dict[str, str], dict[str, object], str, str,
                              list[str], dict[str, str], dict[str, Any]]:
    user_values = load_env(user_path, USER_CASE_KEYS)
    stimulus_values = load_stimulus(stimulus_path)
    overrides = parse_overrides(override_items)
    for key, value in overrides.items():
        if key in USER_CASE_KEYS:
            user_values[key] = value
        else:
            stimulus_values[key] = value
    params = validate_user_case(user_values)
    validate_stimulus(stimulus_values, params["STOP_SECONDS"])
    reference = load_reference()
    verify_reference_sources(reference)
    user_text = stable_env(user_values)
    stimulus_text = stable_env(stimulus_values)
    parameter_data = make_parameter_manifest(user_values, params, stimulus_values, stimulus_text)
    parameter_data["overrides"] = [f"{key}={value}" for key, value in overrides.items()]
    return (user_values, stimulus_values, params, user_text, stimulus_text,
            list(parameter_data["overrides"]), reference, parameter_data)


def _render_preflight(user_values: dict[str, str], stimulus_values: dict[str, str],
                      masks: list[str], user_text: str, stimulus_text: str,
                      overrides: list[str], fixtures_root: Path) -> None:
    fixtures_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="try-preflight-", dir=fixtures_root) as tmp:
        for mask in masks:
            render_case(
                user_values, stimulus_values, mask, Path(tmp) / f"M{mask}",
                fixture_only=True, user_snapshot_text=user_text,
                stimulus_snapshot_text=stimulus_text, overrides=overrides,
            )


def _parameter_changes(values: dict[str, str], reference: dict[str, str], role: str) -> list[str]:
    return [f"{key} {reference[key]} -> {values[key]}" for key in sorted(GROUP_KEYS[role])
            if values[key] != reference[key]]


def preview_text(user_values: dict[str, str], stimulus_values: dict[str, str],
                 params: dict[str, object], reference: dict[str, str]) -> str:
    name = user_values["NAME"]
    masks = params["MASKS"]
    assert isinstance(masks, list)
    lines = [
        "CASE", name, "",
        "ARRAY", f"ARRAY_SIZE={params['ARRAY_SIZE']}", f"MASKS={','.join(masks)}",
        "BIT_ORDER=leftmost bit is BVM1; mask affects FINAL READ only", "",
        "TOPOLOGY", f"QB_CB={user_values['QB_CB']}",
        f"SJTL_COUNT={user_values['SJTL_COUNT']}",
        f"POST_SJTL_CB={user_values['POST_SJTL_CB']}", "",
    ]
    for role in ("BVM", "QB", "CB", "SJTL"):
        lines.append(f"{role} PARAMETER CHANGES")
        changed = _parameter_changes(user_values, reference, role)
        lines.extend(changed or ["none"])
        lines.append("")
    stimulus_qa = validate_stimulus(stimulus_values, params["STOP_SECONDS"])
    lines.extend(["STIMULUS SUMMARY"])
    for interval, (stage, fields) in zip(stimulus_qa["stage_intervals_seconds"], (
            ("WRITE0", ("WL", "BL", "SE")), ("READ0", ("WL", "BL", "SE")),
            ("WRITE1", ("WL", "BL", "SE")), ("FINAL_READ", ("ACTIVE_WL", "ACTIVE_BL", "ACTIVE_SE")))):
        prefix = "READ" if stage == "FINAL_READ" else stage
        amp = ", ".join(f"{branch}={stimulus_values[f'{prefix}_{field}']}"
                         for branch, field in zip(("WL", "BL", "SE"), fields))
        lines.append(f"{stage}: start={stimulus_values[f'{prefix}_START']} "
                     f"rise={stimulus_values[f'{prefix}_RISE']} "
                     f"hold={stimulus_values[f'{prefix}_HOLD']} "
                     f"fall={stimulus_values[f'{prefix}_FALL']}; {amp}")
    lines.extend([
        "", "SOLVER", f"path={REPO / 'build' / 'josim-cli'} (not invoked)",
        f"DT={user_values['DT']}", f"STOP={user_values['STOP']}", "",
        "PLANNED PHYSICAL SOLVES", *masks, f"physical_solve_count = {len(masks)}", "",
        "No physical solve executed.",
    ])
    return "\n".join(lines)


def current_head(repo_root: Path = REPO) -> str:
    result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo_root,
                            check=True, capture_output=True, text=True)
    return result.stdout.strip()


def allocate_batch_id(batches_root: Path, name: str) -> str:
    if not NAME_RE.fullmatch(name):
        raise ConfigError("NAME must match [A-Za-z0-9_-]+")
    indices = [int(match.group(1)) for path in batches_root.iterdir() if path.is_dir()
               if (match := re.match(r"^U(\d+)_", path.name))] if batches_root.exists() else []
    return f"U{max(indices, default=0) + 1:03d}_{name}"


def save_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json_text(data), encoding="utf-8")


def _result_row(mask: str, run_id: str, run_dir: Path, return_code: int,
                series_root: Path, exception: str | None = None) -> dict[str, Any]:
    result_path = run_dir / "result.json"
    result: dict[str, Any] = {}
    if result_path.is_file():
        try:
            result = json.loads(result_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            exception = exception or "invalid result.json"
    provenance_path = run_dir / "provenance.json"
    provenance: dict[str, Any] = {}
    if provenance_path.is_file():
        try:
            provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    physical = int(provenance.get("physical_solve_count", result.get("physical_solve_count", 0)))
    raw_path = run_dir / "raw.csv"
    raw_hash = hashlib.sha256(raw_path.read_bytes()).hexdigest() if raw_path.is_file() else None
    plot = result.get("plot_qa", {"status": "NOT_RUN"})
    return {
        "mask": mask, "run_id": run_id,
        "path": run_dir.relative_to(series_root).as_posix() if run_dir.exists() else None,
        "solver_exit": result.get("solver_exit_code", return_code if run_dir.exists() else None),
        "artifact_status": result.get("artifact_status", "NOT_CREATED"),
        "raw_sha256": raw_hash,
        "plot_qa": plot,
        "physical_solve_count": physical,
        "run_status": result.get("status", "NOT_CREATED"),
        "error": exception,
    }


def _write_batch_summary(batch_dir: Path, manifest: dict[str, Any]) -> None:
    lines = [
        f"# {manifest['batch_id']}", "",
        f"- name: `{manifest['name']}`",
        f"- status: `{manifest['status']}` (mechanical completeness only)",
        f"- requested masks: `{', '.join(manifest['requested_masks'])}`",
        f"- physical solves: `{manifest['total_physical_solve_count']}` / "
        f"{len(manifest['requested_masks'])}",
        "- scientific interpretation performed: `false`",
        "- automatic follow-up: `false`", "", "| Mask | Run | Solver exit | Artifact | Plot QA | Solves |",
        "|---|---|---:|---|---|---:|",
    ]
    for run in manifest["runs"]:
        plot = run["plot_qa"].get("status", "UNKNOWN") if isinstance(run["plot_qa"], dict) else run["plot_qa"]
        lines.append(f"| {run['mask']} | {run['run_id']} | {run['solver_exit']} | "
                     f"{run['artifact_status']} | {plot} | {run['physical_solve_count']} |")
    lines.append("")
    (batch_dir / "BATCH_SUMMARY.md").write_text("\n".join(lines), encoding="utf-8")


def refresh_batch_for_run(run_dir: str | Path, series_root: Path = SERIES) -> str | None:
    """Refresh a batch row after same-raw plot repair; never invokes the solver."""
    root = Path(run_dir).resolve()
    latest_path = series_root / "analysis" / "LATEST_BATCH.json"
    if not latest_path.is_file():
        return None
    latest = json.loads(latest_path.read_text(encoding="utf-8"))
    batch_dir = (series_root / str(latest.get("path", ""))).resolve()
    try:
        batch_dir.relative_to((series_root / "batches").resolve())
    except ValueError as exc:
        raise ConfigError("LATEST_BATCH points outside batches/") from exc
    manifest_path = batch_dir / "batch_manifest.json"
    if not manifest_path.is_file():
        raise ConfigError("LATEST_BATCH has no batch_manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    try:
        root.relative_to((series_root / "runs").resolve())
    except ValueError as exc:
        raise ConfigError("plot-repair run path is outside runs/") from exc
    matching = [row for row in manifest.get("runs", []) if row.get("run_id") == root.name]
    if not matching:
        return None
    if len(matching) != 1:
        raise ConfigError(f"batch has duplicate entries for run {root.name}")
    result = json.loads((root / "result.json").read_text(encoding="utf-8"))
    provenance = json.loads((root / "provenance.json").read_text(encoding="utf-8"))
    raw_path = root / "raw.csv"
    raw_sha = hashlib.sha256(raw_path.read_bytes()).hexdigest() if raw_path.is_file() else None
    row = matching[0]
    artifact_status = result.get("artifact_status", "INVALID")
    if raw_sha is None or result.get("raw_sha256") != raw_sha:
        artifact_status = "INVALID"
    row.update({
        "solver_exit": result.get("solver_exit_code"),
        "artifact_status": artifact_status,
        "raw_sha256": raw_sha,
        "plot_qa": result.get("plot_qa", {"status": "NOT_RUN"}),
        "physical_solve_count": int(provenance.get("physical_solve_count", 0)),
        "run_status": result.get("status", "UNKNOWN"),
        "error": None,
    })
    manifest["total_physical_solve_count"] = sum(
        int(entry.get("physical_solve_count", 0)) for entry in manifest.get("runs", [])
    )
    masks = manifest.get("requested_masks", [])
    counts = {mask: sum(1 for entry in manifest.get("runs", []) if entry.get("mask") == mask)
              for mask in masks}
    complete_rows = all(counts.get(mask) == 1 for mask in masks)
    hard_failure = any(
        (int(entry.get("physical_solve_count", 0)) > 0 and entry.get("solver_exit") not in (0, None))
        or entry.get("artifact_status") == "INVALID"
        for entry in manifest.get("runs", [])
    )
    plots_pass = all(isinstance(entry.get("plot_qa"), dict)
                     and entry["plot_qa"].get("status") == "PASS"
                     for entry in manifest.get("runs", []))
    runs_valid = all(entry.get("solver_exit") == 0 and entry.get("artifact_status") == "VALID"
                     and entry.get("physical_solve_count") == 1
                     for entry in manifest.get("runs", []))
    manifest["status"] = (
        "SOLVER_FAILURE" if hard_failure else
        "COMPLETE_MECHANICAL" if complete_rows and runs_valid and plots_pass
        and manifest["total_physical_solve_count"] == len(masks) else "INCOMPLETE"
    )
    save_json(manifest_path, manifest)
    _write_batch_summary(batch_dir, manifest)
    latest["status"] = manifest["status"]
    save_json(latest_path, latest)
    return manifest["status"]


def execute_batch(user_values: dict[str, str], stimulus_values: dict[str, str],
                  params: dict[str, object], user_text: str, stimulus_text: str,
                  overrides: list[str], parameter_data: dict[str, Any], *,
                  series_root: Path = SERIES, head: str | None = None,
                  solver: Path | None = None,
                  runner: Callable[..., int] = execute_run) -> dict[str, Any]:
    masks = params["MASKS"]
    assert isinstance(masks, list)
    _render_preflight(user_values, stimulus_values, masks, user_text, stimulus_text,
                      overrides, series_root / "tests" / "fixtures")
    batches_root = series_root / "batches"
    batches_root.mkdir(parents=True, exist_ok=True)
    batch_id = allocate_batch_id(batches_root, str(user_values["NAME"]))
    batch_dir = batches_root / batch_id
    batch_dir.mkdir(exist_ok=False)
    parameter_text = json_text(parameter_data)
    manifest: dict[str, Any] = {
        "schema": "bvm-qb-cb-array-batch-v1", "batch_id": batch_id,
        "name": user_values["NAME"], "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "parent_head": head or current_head(), "array_size": params["ARRAY_SIZE"],
        "bit_order": "leftmost bit is BVM1; rightmost bit is BVMN",
        "topology_signature": topology_signature(params),
        "effective_user_case_sha256": sha256_text(user_text),
        "effective_stimulus_sha256": sha256_text(stimulus_text),
        "parameter_manifest_sha256": sha256_text(parameter_text),
        "requested_masks": list(masks), "runs": [],
        "total_physical_solve_count": 0, "status": "RUNNING",
        "overrides": list(overrides),
        "scientific_interpretation_performed": False, "automatic_follow_up": False,
    }
    (batch_dir / "USER_CASE.effective.env").write_text(user_text, encoding="utf-8")
    (batch_dir / "STIMULUS.effective.env").write_text(stimulus_text, encoding="utf-8")
    (batch_dir / "parameter_manifest.json").write_text(parameter_text, encoding="utf-8")
    save_json(batch_dir / "batch_manifest.json", manifest)

    stop_remaining = False
    for mask in masks:
        if stop_remaining:
            break
        run_id = allocate_run_id(series_root / "runs", mask, str(manifest["topology_signature"]))
        run_dir = series_root / "runs" / run_id
        return_code = 2
        error = None
        try:
            return_code = runner(
                user_values, stimulus_values, mask, run_id=run_id, solver=solver,
                user_snapshot_text=user_text, stimulus_snapshot_text=stimulus_text,
                overrides=overrides,
            )
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
        row = _result_row(mask, run_id, run_dir, return_code, series_root, error)
        manifest["runs"].append(row)
        manifest["total_physical_solve_count"] += int(row["physical_solve_count"])
        save_json(batch_dir / "batch_manifest.json", manifest)
        # A failed solver/raw artifact is a hard stop. Plot-only failure keeps valid
        # raw immutable; remaining requested masks may still execute once.
        plot_status = row["plot_qa"].get("status") if isinstance(row["plot_qa"], dict) else row["plot_qa"]
        if row["artifact_status"] != "VALID" or row["solver_exit"] not in (0, None):
            stop_remaining = True
        elif error:
            stop_remaining = True
        elif plot_status != "PASS":
            row["run_status"] = "PLOT_REPAIR_REQUIRED"

    all_requested = len(manifest["runs"]) == len(masks)
    hard_failure = any((run["physical_solve_count"] > 0 and run["solver_exit"] not in (0, None))
                       or run["artifact_status"] == "INVALID"
                       for run in manifest["runs"])
    plots_pass = all(isinstance(run["plot_qa"], dict) and run["plot_qa"].get("status") == "PASS"
                     for run in manifest["runs"])
    runs_valid = all(run["solver_exit"] == 0 and run["artifact_status"] == "VALID"
                     and run["physical_solve_count"] == 1 for run in manifest["runs"])
    manifest["status"] = ("SOLVER_FAILURE" if hard_failure else
                          "COMPLETE_MECHANICAL" if all_requested and runs_valid and plots_pass
                          and manifest["total_physical_solve_count"] == len(masks)
                          else "INCOMPLETE")
    save_json(batch_dir / "batch_manifest.json", manifest)
    _write_batch_summary(batch_dir, manifest)
    save_json(series_root / "analysis" / "LATEST_BATCH.json", {
        "schema": "bvm-qb-cb-array-latest-batch-v1", "batch_id": batch_id,
        "path": (Path("batches") / batch_id).as_posix(), "status": manifest["status"],
    })
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Preview or run one configured BVM-array batch")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--set", dest="overrides", action="append", default=[], metavar="KEY=VALUE")
    parser.add_argument("--user-case", default=str(SERIES / "USER_CASE.env"))
    parser.add_argument("--stimulus", default=str(SERIES / "STIMULUS.env"))
    parser.add_argument("--solver")
    args = parser.parse_args(argv)
    try:
        user_values, stimulus_values, params, user_text, stimulus_text, overrides, reference, parameter_data = \
            load_effective(Path(args.user_case), Path(args.stimulus), args.overrides)
        masks = params["MASKS"]
        assert isinstance(masks, list)
        if args.dry_run:
            _render_preflight(user_values, stimulus_values, masks, user_text, stimulus_text,
                              overrides, SERIES / "tests" / "fixtures")
            print(preview_text(user_values, stimulus_values, params, reference))
            return 0
        manifest = execute_batch(
            user_values, stimulus_values, params, user_text, stimulus_text, overrides,
            parameter_data, head=current_head(), solver=Path(args.solver) if args.solver else None,
        )
        print(json.dumps({"status": manifest["status"], "batch_id": manifest["batch_id"],
                          "path": f"batches/{manifest['batch_id']}",
                          "physical_solve_count": manifest["total_physical_solve_count"],
                          "automatic_follow_up": False,
                          "scientific_interpretation_performed": False},
                         ensure_ascii=False, indent=2))
        return 0 if manifest["status"] == "COMPLETE_MECHANICAL" else 2
    except (OSError, ConfigError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
