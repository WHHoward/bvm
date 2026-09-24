#!/usr/bin/env python3
"""Series-local experiment/source commit, package, checkpoint, and push flow."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import package
from config import USER_CASE_KEYS, load_env

SERIES = Path(__file__).resolve().parents[1]
REPO = next(path for path in (SERIES, *SERIES.parents) if (path / ".git").exists())
CHECKPOINTS = SERIES / "analysis" / "PACKAGE_CHECKPOINTS.json"
PACKAGE_QA = SERIES / "analysis" / "PACKAGE_QA.json"
TAG_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
REQUIRED_PLOT_FILES = {
    "plots/01_overview.html", "plots/02_bvm.html", "plots/03_qb.html",
    "plots/04_cb.html", "plots/05_acc_gap.html",
}


def git(*args: str, check: bool = True, capture: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=REPO, check=check, capture_output=capture, text=True)


def current_head() -> str:
    return git("rev-parse", "HEAD").stdout.strip()


def series_changes() -> list[str]:
    output = git("status", "--short", "--untracked-files=all", "--", SERIES.relative_to(REPO).as_posix()).stdout
    paths = []
    for line in output.splitlines():
        if len(line) < 4:
            continue
        path = line[3:]
        candidate = REPO / path
        if candidate.suffix == ".pyc" or "__pycache__" in candidate.parts:
            continue
        if candidate.parent.name == "handoff" and candidate.suffix.lower() == ".zip":
            continue
        paths.append(path)
    return sorted(set(paths))


def staged_outside_series() -> list[str]:
    output = git("diff", "--cached", "--name-only", "-z").stdout
    prefix = SERIES.relative_to(REPO).as_posix().rstrip("/") + "/"
    return sorted(path for path in output.split("\0") if path and not path.startswith(prefix))


def _read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"BATCH_INCOMPLETE: cannot read {label}: {path}") from exc
    if not isinstance(value, dict):
        raise RuntimeError(f"BATCH_INCOMPLETE: {label} must be a JSON object")
    return value


def _validate_plot_artifacts(run_dir: Path, expected_raw_sha: str) -> str | None:
    qa_path = run_dir / "analysis" / "plot_qa.json"
    if not qa_path.is_file():
        return "analysis/plot_qa.json is missing"
    try:
        qa = _read_json(qa_path, "plot_qa.json")
    except RuntimeError as exc:
        return str(exc)
    if (qa.get("status") != "PASS" or qa.get("page_count") != 5
            or qa.get("raw_immutable") is not True
            or qa.get("shared_asset_reference_pass") is not True
            or qa.get("full_stored_time_range") is not True
            or qa.get("raw_sha256_before") != expected_raw_sha
            or qa.get("raw_sha256_after") != expected_raw_sha):
        return "plot QA does not certify five pages and unchanged raw"
    pages = qa.get("pages")
    if not isinstance(pages, list) or len(pages) != 5:
        return "plot QA page inventory is incomplete"
    observed: set[str] = set()
    for page in pages:
        if not isinstance(page, dict):
            return "plot QA page entry is malformed"
        relative = str(page.get("path", ""))
        if relative not in REQUIRED_PLOT_FILES:
            return f"unexpected plot page path {relative!r}"
        if page.get("status") not in {"PASS", "NO_COMPONENT_PRESENT"}:
            return f"plot page did not pass: {relative}"
        path = (run_dir / relative).resolve()
        try:
            path.relative_to((run_dir / "plots").resolve())
        except ValueError:
            return f"plot page escapes plots/: {relative}"
        if not path.is_file():
            return f"plot page file is missing: {relative}"
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if page.get("sha256") != digest:
            return f"plot page SHA-256 mismatch: {relative}"
        observed.add(relative)
    if observed != REQUIRED_PLOT_FILES:
        return "plot QA does not list the exact five required pages"
    return None


def validate_batch(series_root: Path = SERIES) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Require a mechanically closed LATEST_BATCH; never inspect scientific metrics."""
    latest_path = series_root / "analysis" / "LATEST_BATCH.json"
    if not latest_path.is_file():
        raise RuntimeError("BATCH_INCOMPLETE: analysis/LATEST_BATCH.json is missing")
    latest = _read_json(latest_path, "LATEST_BATCH.json")
    relative_batch = Path(str(latest.get("path", "")))
    batch_dir = (series_root / relative_batch).resolve()
    try:
        batch_dir.relative_to((series_root / "batches").resolve())
    except ValueError as exc:
        raise RuntimeError("BATCH_INCOMPLETE: LATEST_BATCH points outside batches/") from exc
    manifest_path = batch_dir / "batch_manifest.json"
    if not manifest_path.is_file():
        raise RuntimeError("BATCH_INCOMPLETE: batch_manifest.json is missing")
    manifest = _read_json(manifest_path, "batch_manifest.json")
    errors: list[str] = []
    for filename, field in (("USER_CASE.effective.env", "effective_user_case_sha256"),
                            ("STIMULUS.effective.env", "effective_stimulus_sha256"),
                            ("parameter_manifest.json", "parameter_manifest_sha256")):
        artifact = batch_dir / filename
        if not artifact.is_file():
            errors.append(f"batch artifact is missing: {filename}")
        elif hashlib.sha256(artifact.read_bytes()).hexdigest() != manifest.get(field):
            errors.append(f"batch artifact hash mismatch: {filename}")
    try:
        effective_user = load_env(batch_dir / "USER_CASE.effective.env", USER_CASE_KEYS)
        effective_size = int(effective_user["ARRAY_SIZE"])
        effective_masks = [item.strip() for item in effective_user["MASKS"].split(",")]
        if effective_user["NAME"] != manifest.get("name"):
            errors.append("effective USER_CASE NAME disagrees with batch manifest")
        if effective_size != manifest.get("array_size") or effective_masks != manifest.get("requested_masks"):
            errors.append("effective USER_CASE ARRAY_SIZE/MASKS disagree with batch manifest")
    except (OSError, ValueError, RuntimeError) as exc:
        errors.append(f"effective USER_CASE snapshot is invalid: {exc}")
    parameter_path = batch_dir / "parameter_manifest.json"
    if parameter_path.is_file():
        parameter_data = _read_json(parameter_path, "batch parameter_manifest.json")
        required_parameter_groups = {"bvm", "qb", "cb", "sjtl", "topology", "solver", "stimulus_reference"}
        if not required_parameter_groups.issubset(parameter_data):
            errors.append("batch parameter_manifest.json is missing required parameter groups")
    if manifest.get("batch_id") != latest.get("batch_id") or batch_dir.name != latest.get("batch_id"):
        errors.append("latest batch identity does not match its manifest/path")
    if manifest.get("status") != "COMPLETE_MECHANICAL":
        errors.append(f"batch status is {manifest.get('status')!r}, not COMPLETE_MECHANICAL")
    if latest.get("status") != manifest.get("status"):
        errors.append("LATEST_BATCH status disagrees with batch_manifest")

    masks = manifest.get("requested_masks")
    runs = manifest.get("runs")
    array_size = manifest.get("array_size")
    if not isinstance(array_size, int) or array_size < 1:
        errors.append("array_size is invalid")
        array_size = 0
    if not isinstance(masks, list) or not masks or any(
            not isinstance(mask, str) or not re.fullmatch(rf"[01]{{{array_size}}}", mask)
            for mask in masks):
        errors.append("requested_masks is missing or malformed")
        masks = []
    if len(masks) != len(set(masks)):
        errors.append("requested_masks contains duplicates")
    if not isinstance(runs, list):
        errors.append("runs is not a list")
        runs = []

    rows_by_mask: dict[str, list[dict[str, Any]]] = {}
    for row in runs:
        if not isinstance(row, dict):
            errors.append("run entry is not an object")
            continue
        rows_by_mask.setdefault(str(row.get("mask", "")), []).append(row)
    for mask in masks:
        count = len(rows_by_mask.get(mask, []))
        if count != 1:
            errors.append(f"requested mask {mask} has {count} run entries; expected exactly one")
    extras = sorted(set(rows_by_mask) - set(masks))
    if extras:
        errors.append("unrequested run masks present: " + ", ".join(extras))

    verified: list[dict[str, Any]] = []
    solve_total = 0
    for mask in masks:
        entries = rows_by_mask.get(mask, [])
        if len(entries) != 1:
            continue
        row = entries[0]
        run_id = str(row.get("run_id", ""))
        run_dir = (series_root / str(row.get("path", ""))).resolve()
        try:
            run_dir.relative_to((series_root / "runs").resolve())
        except ValueError:
            errors.append(f"mask {mask}: run path escapes runs/")
            continue
        if not run_dir.is_dir():
            errors.append(f"mask {mask}: run directory is missing ({run_id})")
            continue
        result_path = run_dir / "result.json"
        provenance_path = run_dir / "provenance.json"
        raw_path = run_dir / "raw.csv"
        parameter_path = run_dir / "parameter_manifest.json"
        if (not result_path.is_file() or not provenance_path.is_file() or not raw_path.is_file()
                or not parameter_path.is_file()):
            errors.append(f"mask {mask}: result/provenance/parameter/raw artifact is missing")
            continue
        result = _read_json(result_path, f"{run_id}/result.json")
        provenance = _read_json(provenance_path, f"{run_id}/provenance.json")
        parameter_record = provenance.get("parameter_manifest", {})
        parameter_sha = hashlib.sha256(parameter_path.read_bytes()).hexdigest()
        if not isinstance(parameter_record, dict) or parameter_record.get("sha256") != parameter_sha:
            errors.append(f"mask {mask}: parameter manifest SHA-256 is missing or inconsistent")
        actual_raw_sha = hashlib.sha256(raw_path.read_bytes()).hexdigest()
        recorded = row.get("raw_sha256")
        provenance_raw = provenance.get("raw")
        provenance_raw_sha = provenance_raw.get("sha256") if isinstance(provenance_raw, dict) else None
        if (not recorded or recorded != actual_raw_sha or result.get("raw_sha256") != actual_raw_sha
                or provenance_raw_sha != actual_raw_sha):
            errors.append(f"mask {mask}: raw SHA-256 is missing or inconsistent")
        if run_dir.name != run_id or result.get("mask") != mask or result.get("run_id") != run_id:
            errors.append(f"mask {mask}: result identity does not match batch entry")
        if row.get("artifact_status") != "VALID" or result.get("artifact_status") != "VALID":
            errors.append(f"mask {mask}: artifact_status is not VALID")
        row_plot = row.get("plot_qa", {})
        result_plot = result.get("plot_qa", {})
        if not (isinstance(row_plot, dict) and row_plot.get("status") == "PASS"
                and isinstance(result_plot, dict) and result_plot.get("status") == "PASS"):
            errors.append(f"mask {mask}: plot QA is not PASS")
        plot_error = _validate_plot_artifacts(run_dir, actual_raw_sha)
        if plot_error:
            errors.append(f"mask {mask}: {plot_error}")
        if row.get("solver_exit") != 0 or result.get("solver_exit_code") != 0:
            errors.append(f"mask {mask}: solver exit is not zero")
        row_solves = row.get("physical_solve_count")
        run_solves = provenance.get("physical_solve_count")
        if row_solves != 1 or run_solves != 1 or result.get("physical_solve_count") != 1:
            errors.append(f"mask {mask}: physical_solve_count is not exactly one")
        solve_total += int(row_solves) if isinstance(row_solves, int) else 0
        verified.append({"run_id": run_id, "result_path": result_path,
                         "physical_solve_count": int(row_solves or 0), "raw_sha256": actual_raw_sha})
    if manifest.get("total_physical_solve_count") != solve_total:
        errors.append("total_physical_solve_count disagrees with the run entries")
    if solve_total != len(masks):
        errors.append("physical solve total does not equal requested mask count")
    if errors:
        raise RuntimeError("BATCH_INCOMPLETE: " + "; ".join(errors))
    return verified, {"batch_id": manifest["batch_id"], "status": manifest["status"],
                      "requested_masks": masks, "total_physical_solve_count": solve_total,
                      "manifest_path": manifest_path.as_posix()}


def completed_runs(series_root: Path = SERIES) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Prefer full-batch closure; retain the explicit advanced single-run path."""
    latest_batch = series_root / "analysis" / "LATEST_BATCH.json"
    if latest_batch.is_file():
        return validate_batch(series_root)
    latest_path = series_root / "analysis" / "LATEST_RUN.json"
    if not latest_path.is_file():
        raise RuntimeError("BATCH_INCOMPLETE: no LATEST_BATCH or advanced LATEST_RUN pointer exists")
    latest = _read_json(latest_path, "LATEST_RUN.json")
    run_id = str(latest.get("run_id", ""))
    run_dir = (series_root / "runs" / run_id).resolve()
    try:
        run_dir.relative_to((series_root / "runs").resolve())
    except ValueError as exc:
        raise RuntimeError("LATEST_RUN.json points outside runs/") from exc
    result_path = run_dir / "result.json"
    raw_path = run_dir / "raw.csv"
    if not result_path.is_file() or not raw_path.is_file():
        raise RuntimeError(f"advanced run is incomplete: {run_id}")
    result = _read_json(result_path, f"{run_id}/result.json")
    raw_hash = hashlib.sha256(raw_path.read_bytes()).hexdigest()
    plot_qa = result.get("plot_qa")
    if (result.get("artifact_status") != "VALID" or not isinstance(plot_qa, dict)
            or plot_qa.get("status") != "PASS"
            or result.get("raw_sha256") != raw_hash):
        raise RuntimeError(f"advanced run is not ready for submission: {run_id}")
    rows = [{"run_id": run_id, "result_path": result_path,
             "physical_solve_count": int(result.get("physical_solve_count", 0)),
             "raw_sha256": raw_hash}]
    return rows, {"batch_id": None, "status": "ADVANCED_SINGLE_RUN",
                  "requested_masks": [result.get("mask")], "total_physical_solve_count": rows[0]["physical_solve_count"]}


def build_submission_plan(tag: str, mode: str, source_files: list[str],
                          package_plan: dict[str, Any], *, package_only: bool,
                          no_push: bool, batch_validation: dict[str, Any] | None = None) -> dict[str, Any]:
    if not TAG_RE.fullmatch(tag):
        raise RuntimeError(f"invalid submit tag: {tag!r}")
    if mode not in {"full", "delta"}:
        raise RuntimeError(f"invalid package mode: {mode}")
    return {
        "status": "SUBMIT_DRY_RUN_PASS",
        "tag": tag,
        "mode": mode,
        "source_changes": source_files,
        "experiment_commit": "SKIP_PACKAGE_ONLY" if package_only else "WOULD_COMMIT",
        "package_plan": package_plan,
        "package_created": False,
        "solver_invoked": False,
        "mirror_written": False,
        "package_metadata_commit": "WOULD_COMMIT",
        "push": "SKIPPED" if no_push else "WOULD_PUSH",
        "batch_validation": batch_validation,
    }


def append_checkpoint(qa: dict[str, Any], tag: str) -> None:
    data = json.loads(CHECKPOINTS.read_text(encoding="utf-8"))
    entries = data.setdefault("checkpoints", [])
    for entry in entries:
        if entry.get("head_commit") == qa.get("head_commit") and entry.get("package_sha256") != qa.get("package_sha256"):
            raise RuntimeError("checkpoint conflict: same head_commit has a different package SHA")
        if entry.get("package_sha256") == qa.get("package_sha256"):
            if entry.get("package_name") != qa.get("package_name"):
                raise RuntimeError("checkpoint conflict: same package SHA has a different package name")
            return
    entries.append({
        "package_name": qa["package_name"], "package_path": qa["package_path"],
        "package_sha256": qa["package_sha256"], "package_type": qa["package_type"],
        "head_commit": qa["head_commit"], "base_commit": qa.get("base_commit"),
        "source": f"{tag} {qa['package_type']} checkpoint",
    })
    CHECKPOINTS.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Submit completed BVM array evidence")
    parser.add_argument("tag")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--mode", choices=("full", "delta"), default=None)
    parser.add_argument("--base-commit")
    parser.add_argument("--no-push", action="store_true")
    parser.add_argument("--package-only", action="store_true")
    args = parser.parse_args(argv)
    try:
        if not TAG_RE.fullmatch(args.tag):
            raise RuntimeError(f"invalid submit tag: {args.tag!r}")
        outside = staged_outside_series()
        if outside:
            raise RuntimeError("staged changes outside this series: " + ", ".join(outside))
        runs, batch_validation = completed_runs(SERIES)
        changes = series_changes()
        if not args.package_only and not changes:
            raise RuntimeError("no new series changes to commit")
        head = current_head()
        mode = args.mode or ("delta" if package.checkpoint_entries() else "full")
        package_plan = package.build_plan(mode, args.tag, args.base_commit)
        plan = build_submission_plan(args.tag, mode, changes, {
            "head_commit": package_plan["head_commit"],
            "base": package_plan["base"],
            "files": [package.rel(path) for path in package_plan["files"]],
            "package_path": package.rel(package_plan["package_path"]),
            "mirror_path": str(package_plan["mirror_path"]),
            "physical_solve_count": sum(item["physical_solve_count"] for item in runs),
        }, package_only=args.package_only, no_push=args.no_push,
            batch_validation=batch_validation)
        plan["current_head"] = head
        if args.dry_run:
            print(json.dumps(plan, ensure_ascii=False, indent=2))
            return 0

        if not args.package_only:
            git("add", "-A", "--", SERIES.relative_to(REPO).as_posix())
            git("reset", "--", (SERIES / "handoff").relative_to(REPO).as_posix(), check=False)
            git("commit", "-m", f"experiment: complete {args.tag}", capture=False)
        experiment_commit = current_head()

        package_cmd = [sys.executable, str(SERIES / "scripts" / "package.py"),
                       "--mode", mode, "--tag", args.tag]
        if args.base_commit:
            package_cmd.extend(["--base-commit", args.base_commit])
        subprocess.run(package_cmd, cwd=REPO, check=True)
        qa = json.loads(PACKAGE_QA.read_text(encoding="utf-8"))
        if (qa.get("status") != "PASS" or qa.get("package_type") != mode
                or qa.get("head_commit") != experiment_commit
                or qa.get("package_sha256") != qa.get("mirror_sha256")):
            raise RuntimeError("package QA, experiment HEAD, or package/mirror SHA check failed")
        append_checkpoint(qa, args.tag)
        git("add", "--", CHECKPOINTS.relative_to(REPO).as_posix(),
            PACKAGE_QA.relative_to(REPO).as_posix())
        git("commit", "-m", f"package: archive {args.tag} {args.mode} evidence", capture=False)
        if not args.no_push:
            git("push", capture=False)
        print(json.dumps({"status": "SUBMIT_COMPLETE", "experiment_commit": experiment_commit,
                          "package_metadata_commit": current_head(), "package": qa["package_path"],
                          "package_sha256": qa["package_sha256"], "mirror": qa["mirror_path"],
                          "mirror_sha256": qa["mirror_sha256"], "push": "SKIPPED" if args.no_push else "PASS",
                          "scientific_interpretation_performed": False, "stop": True},
                         ensure_ascii=False, indent=2))
        return 0
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
