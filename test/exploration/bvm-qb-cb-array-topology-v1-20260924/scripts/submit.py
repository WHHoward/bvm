#!/usr/bin/env python3
"""Series-local experiment/source commit, package, checkpoint, and push flow."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import package

SERIES = Path(__file__).resolve().parents[1]
REPO = next(path for path in (SERIES, *SERIES.parents) if (path / ".git").exists())
CHECKPOINTS = SERIES / "analysis" / "PACKAGE_CHECKPOINTS.json"
PACKAGE_QA = SERIES / "analysis" / "PACKAGE_QA.json"
TAG_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")


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


def completed_runs() -> list[dict[str, Any]]:
    latest_path = SERIES / "analysis" / "LATEST_RUN.json"
    if not latest_path.is_file():
        raise RuntimeError("no completed run pointer exists")
    latest = json.loads(latest_path.read_text(encoding="utf-8"))
    run_id = str(latest.get("run_id", ""))
    run_dir = (SERIES / "runs" / run_id).resolve()
    try:
        run_dir.relative_to((SERIES / "runs").resolve())
    except ValueError as exc:
        raise RuntimeError("LATEST_RUN.json points outside runs/") from exc
    result_path = run_dir / "result.json"
    if not result_path.is_file():
        raise RuntimeError(f"latest run has no result.json: {run_id}")
    result = json.loads(result_path.read_text(encoding="utf-8"))
    plot_qa = result.get("plot_qa", {})
    if result.get("artifact_status") != "VALID" or plot_qa.get("status") != "PASS":
        raise RuntimeError(f"latest run is not ready for submission: {run_id}")
    if not (run_dir / "raw.csv").is_file():
        raise RuntimeError(f"completed run is missing raw.csv: {run_id}")
    return [{"run_id": run_id, "result_path": result_path,
             "physical_solve_count": int(result.get("physical_solve_count", 0))}]


def build_submission_plan(tag: str, mode: str, source_files: list[str],
                          package_plan: dict[str, Any], *, package_only: bool,
                          no_push: bool) -> dict[str, Any]:
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
    parser.add_argument("--mode", choices=("full", "delta"), default="delta")
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
        runs = completed_runs()
        changes = series_changes()
        if not args.package_only and not changes:
            raise RuntimeError("no new series changes to commit")
        head = current_head()
        package_plan = package.build_plan(args.mode, args.tag, args.base_commit)
        plan = build_submission_plan(args.tag, args.mode, changes, {
            "head_commit": package_plan["head_commit"],
            "base": package_plan["base"],
            "files": [package.rel(path) for path in package_plan["files"]],
            "package_path": package.rel(package_plan["package_path"]),
            "mirror_path": str(package_plan["mirror_path"]),
            "physical_solve_count": sum(item["physical_solve_count"] for item in runs),
        }, package_only=args.package_only, no_push=args.no_push)
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
                       "--mode", args.mode, "--tag", args.tag]
        if args.base_commit:
            package_cmd.extend(["--base-commit", args.base_commit])
        subprocess.run(package_cmd, cwd=REPO, check=True)
        qa = json.loads(PACKAGE_QA.read_text(encoding="utf-8"))
        if (qa.get("status") != "PASS" or qa.get("package_type") != args.mode
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
