#!/usr/bin/env python3
"""Idempotent experiment commit -> delta package -> checkpoint -> push workflow."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

SERIES = Path(__file__).resolve().parents[1]
REPO = next(path for path in (SERIES, *SERIES.parents) if (path / ".git").exists())
PACKAGE_QA = SERIES / "analysis" / "PACKAGE_QA.json"
CHECKPOINTS = SERIES / "analysis" / "PACKAGE_CHECKPOINTS.json"
LEGACY_HASHES = SERIES / "analysis" / "legacy_raw_hashes.json"
TAG_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")


def run(command: list[str], check: bool = True, capture: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=REPO, text=True, capture_output=capture, check=check)


def sha256(path: Path) -> str:
    import hashlib
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def git_head() -> str:
    return run(["git", "rev-parse", "HEAD"], capture=True).stdout.strip()


def upstream() -> str:
    value = run(["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"], check=False, capture=True)
    if value.returncode != 0 or not value.stdout.strip():
        raise RuntimeError("unable to determine upstream/push target")
    return value.stdout.strip()


def status_lines() -> list[str]:
    return [line for line in run(["git", "status", "--short", "--untracked-files=all"], capture=True).stdout.splitlines() if line.strip()]


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO.resolve()).as_posix()


def safe_tag(tag: str) -> None:
    if not TAG_RE.fullmatch(tag) or tag in {".", ".."}:
        raise RuntimeError(f"invalid TAG: {tag!r}")


def series_status(lines: list[str]) -> tuple[list[str], list[str]]:
    inside, outside = [], []
    prefix = rel(SERIES) + "/"
    for line in lines:
        path = line[3:] if len(line) >= 4 else ""
        (inside if path == rel(SERIES) or path.startswith(prefix) else outside).append(line)
    return inside, outside


def latest_result() -> dict[str, Any]:
    candidates = (SERIES / "LATEST_BATCH_REVIEW.html", SERIES / "LATEST_REVIEW.html")
    valid: list[dict[str, Any]] = []
    for pointer in candidates:
        if not pointer.is_file():
            continue
        text = pointer.read_text(encoding="utf-8", errors="replace")
        match = re.search(r"(?:url=|href=)[\"']?([^\"' >]+)", text)
        if not match:
            continue
        target = (pointer.parent / match.group(1)).resolve()
        if not target.is_file():
            continue
        if pointer.name == "LATEST_BATCH_REVIEW.html":
            batch_root = target.parent
            qa_path = batch_root / "BATCH_QA.json"
            manifest_path = batch_root / "BATCH_MANIFEST.json"
            if not qa_path.is_file() or not manifest_path.is_file():
                raise RuntimeError(f"latest batch is missing QA/manifest: {batch_root}")
            qa = json.loads(qa_path.read_text(encoding="utf-8"))
            if qa.get("status") != "PASS":
                raise RuntimeError(f"latest batch QA is not PASS: {batch_root}")
            valid.append({"kind": "batch", "pointer": rel(pointer), "review": rel(target), "root": batch_root, "qa": qa, "manifest": json.loads(manifest_path.read_text(encoding="utf-8")), "pointer_changed": run(["git", "diff", "--quiet", "HEAD", "--", rel(pointer)], check=False).returncode != 0, "pointer_commit_time": pointer_commit_time(pointer)})
        else:
            valid.append({"kind": "single", "pointer": rel(pointer), "review": rel(target), "root": target.parent, "pointer_changed": run(["git", "diff", "--quiet", "HEAD", "--", rel(pointer)], check=False).returncode != 0, "pointer_commit_time": pointer_commit_time(pointer)})
    if valid:
        # A newly changed pointer is the active evidence entry point. If both
        # pointers are clean, use the one updated by the newest Git commit;
        # filesystem mtime is deliberately not used as authority.
        return max(valid, key=lambda item: (item["pointer_changed"], item["pointer_commit_time"]))
    raise RuntimeError("no valid LATEST_BATCH_REVIEW.html or LATEST_REVIEW.html points to an existing result")


def pointer_commit_time(pointer: Path) -> int:
    result = run(["git", "log", "-1", "--format=%ct", "--", rel(pointer)], check=False, capture=True)
    try:
        return int(result.stdout.strip())
    except ValueError:
        return 0


def verify_legacy_raw() -> None:
    if not LEGACY_HASHES.is_file():
        raise RuntimeError("legacy raw hash registry is missing")
    registry = json.loads(LEGACY_HASHES.read_text(encoding="utf-8"))
    changed = []
    for path_text, expected in registry.items():
        path = REPO / path_text
        if not path.is_file() or sha256(path) != expected:
            changed.append(path_text)
    if changed:
        raise RuntimeError("HISTORICAL_RAW_CHANGED: " + ", ".join(changed))


def verify_latest_evidence(latest: dict[str, Any]) -> None:
    if latest["kind"] == "batch":
        qa = latest["qa"]
        if qa.get("status") != "PASS" or qa.get("failed_points"):
            raise RuntimeError("latest batch is not a valid PASS checkpoint")
        for point in latest["manifest"].get("points", []):
            if point.get("raw_qa_status") and point.get("raw_qa_status") != "PASS":
                raise RuntimeError(f"latest batch contains non-PASS point: {point}")
    result = latest["root"] / "result.json"
    if result.is_file():
        data = json.loads(result.read_text(encoding="utf-8"))
        if data.get("artifact_status") == "INVALID":
            raise RuntimeError("latest result is ARTIFACT_INVALID")


def experiment_files() -> list[str]:
    paths = []
    for path in sorted(SERIES.rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts or path.suffix == ".pyc" or (path.parent.name == "handoff" and path.suffix == ".zip"):
            continue
        paths.append(rel(path))
    return paths


def commit_for_message(message: str) -> str | None:
    result = run(["git", "log", "--all", "--format=%H", "--grep", f"^{message}$"], check=False, capture=True)
    values = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    return values[0] if values else None


def stage_experiment() -> None:
    run(["git", "add", "-A", "--", rel(SERIES)])
    # ZIP artifacts stay outside Git; existing LFS policy remains authoritative.
    run(["git", "reset", "--", rel(SERIES / "handoff")], check=False, capture=True)


def package_dry_run(tag: str, head: str) -> str:
    result = run([sys.executable, str(SERIES / "scripts" / "package.py"), "--mode", "delta", "--tag", tag, "--dry-run"], capture=True)
    if f"head_commit={head}" not in result.stdout:
        raise RuntimeError(f"package dry-run head mismatch; expected {head}\n{result.stdout}")
    return result.stdout


def parse_estimated_bytes(text: str) -> int | None:
    match = re.search(r"estimated_uncompressed_bytes=(\d+)", text)
    return int(match.group(1)) if match else None


def latest_full_size() -> int | None:
    registry = json.loads(CHECKPOINTS.read_text(encoding="utf-8")) if CHECKPOINTS.is_file() else {}
    sizes = []
    for item in registry.get("checkpoints", []):
        if item.get("package_type") == "full":
            path = REPO / item.get("package_path", "")
            if path.is_file() and item.get("package_sha256") == sha256(path):
                sizes.append(path.stat().st_size)
    return max(sizes) if sizes else None


def append_checkpoint(qa: dict[str, Any], tag: str) -> None:
    if not CHECKPOINTS.is_file():
        raise RuntimeError("PACKAGE_CHECKPOINTS.json missing")
    data = json.loads(CHECKPOINTS.read_text(encoding="utf-8"))
    entries = data.setdefault("checkpoints", [])
    for item in entries:
        if item.get("head_commit") == qa.get("head_commit") and item.get("package_sha256") != qa.get("package_sha256"):
            raise RuntimeError("checkpoint conflict: same head_commit already maps to another package")
        if item.get("package_sha256") == qa.get("package_sha256"):
            if item.get("package_name") != Path(qa["package"]).name:
                raise RuntimeError("checkpoint conflict: package SHA already has another name")
            return
    package_path = REPO / qa["package"]
    if not package_path.is_file() or sha256(package_path) != qa["package_sha256"]:
        raise RuntimeError("package checkpoint SHA/path verification failed")
    entries.append({"package_name": package_path.name, "package_path": qa["package"], "package_sha256": qa["package_sha256"], "package_type": qa["package_type"], "head_commit": qa["head_commit"], "base_commit": qa.get("base_commit"), "source": f"{tag} delta checkpoint"})
    CHECKPOINTS.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def print_preview(tag: str, message: str, latest: dict[str, Any], inside: list[str], outside: list[str], dry_run_text: str) -> None:
    print("SUBMIT PREVIEW\n")
    print(f"Tag:\n{tag}\n\nCurrent branch:\n{run(['git','branch','--show-current'], capture=True).stdout.strip()}\n\nCurrent HEAD:\n{git_head()}")
    print(f"\nExperiment evidence:\n{latest['kind']} {latest['review']}\n\nExperiment QA:\nPASS")
    print("\nFiles that would be staged:")
    print("\n".join(inside) or "none")
    print("\nUnrelated changes:")
    print("\n".join(outside) or "none")
    print(f"\nExperiment commit message:\n{message}\n\nPredicted experiment commit:\nnot created in dry-run")
    print("\nDelta package plan:\n" + dry_run_text)
    print("\nCheckpoint registry action:\nappend one checkpoint")
    print("\nPackage metadata commit:\npackage: archive " + tag + " delta evidence")
    print(f"\nPush target:\n{upstream()}")
    print("\nNO FILES MODIFIED\nNO COMMITS CREATED\nNO PACKAGE CREATED\nNO PUSH")


def main() -> int:
    parser = argparse.ArgumentParser(description="Submit an already completed JoSIM experiment")
    parser.add_argument("tag")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--message")
    parser.add_argument("--no-push", action="store_true")
    parser.add_argument("--package-only", action="store_true")
    parser.add_argument("--allow-large-delta", action="store_true")
    args = parser.parse_args()
    safe_tag(args.tag)
    latest = latest_result()
    verify_latest_evidence(latest)
    verify_legacy_raw()
    lines = status_lines()
    inside, outside = series_status(lines)
    if outside:
        # Source-authority changes outside the experiment are unsafe; other unrelated edits are preserved but not staged.
        source_paths = {"circuits/", "build/", "src/", "include/"}
        if any(any(line[3:].startswith(prefix) for prefix in source_paths) for line in outside if len(line) >= 4):
            raise RuntimeError("UNRELATED WORKTREE CHANGES DETECTED in source-authority paths")
    message = args.message or f"experiment: complete {args.tag}"
    existing_experiment_commit = commit_for_message(message)
    if args.package_only:
        print("PACKAGE-ONLY MODE")
        experiment_commit = git_head()
    elif existing_experiment_commit:
        experiment_commit = existing_experiment_commit
    elif not inside:
        if args.dry_run:
            experiment_commit = git_head()
        else:
            raise RuntimeError("no new experiment evidence changes; submit hard stop")
    else:
        experiment_commit = git_head() if args.dry_run else None
    if args.dry_run:
        dry_run_text = package_dry_run(args.tag, experiment_commit)
        estimated = parse_estimated_bytes(dry_run_text); full_size = latest_full_size()
        if estimated and full_size and estimated > full_size * 0.5 and not args.allow_large_delta:
            raise RuntimeError(f"DELTA PACKAGE UNEXPECTEDLY LARGE: estimated {estimated} > 50% of full {full_size}")
        print_preview(args.tag, message, latest, inside, outside, dry_run_text)
        return 0
    if not args.package_only and not existing_experiment_commit:
        stage_experiment()
        run(["git", "commit", "-m", message])
        experiment_commit = git_head()
        remaining_inside, _ = series_status(status_lines())
        if remaining_inside:
            raise RuntimeError("unexplained experiment files remain after experiment commit")
    dry_run_text = package_dry_run(args.tag, experiment_commit)
    estimated = parse_estimated_bytes(dry_run_text); full_size = latest_full_size()
    if estimated and full_size and estimated > full_size * 0.5 and not args.allow_large_delta:
        raise RuntimeError(f"DELTA PACKAGE UNEXPECTEDLY LARGE: estimated {estimated} > 50% of full {full_size}")
    package_command = [sys.executable, str(SERIES / "scripts" / "package.py"), "--mode", "delta", "--tag", args.tag]
    run(package_command)
    if not PACKAGE_QA.is_file():
        raise RuntimeError("PACKAGE_QA.json missing after package")
    qa = json.loads(PACKAGE_QA.read_text(encoding="utf-8"))
    if qa.get("status") != "PASS" or qa.get("package_type") != "delta" or qa.get("head_commit") != experiment_commit or qa.get("package_sha256") != qa.get("mirror_sha256"):
        raise RuntimeError("package QA/head/mirror verification failed")
    append_checkpoint(qa, args.tag)
    run(["git", "add", "--", rel(PACKAGE_QA), rel(CHECKPOINTS), rel(SERIES / "result.json")], check=False)
    package_commit = commit_for_message(f"package: archive {args.tag} delta evidence")
    if not package_commit:
        run(["git", "commit", "-m", f"package: archive {args.tag} delta evidence"])
        package_commit = git_head()
    if not args.no_push:
        pushed = run(["git", "push"], check=False)
        if pushed.returncode != 0:
            print("LOCAL COMPLETE / PUSH FAILED", file=sys.stderr)
            print("git push", file=sys.stderr)
            return 3
    print(json.dumps({"status":"SUBMIT_COMPLETE","experiment_commit":experiment_commit,"package_metadata_commit":package_commit,"package":qa["package"],"package_bytes":qa["package_bytes"],"package_sha256":qa["package_sha256"],"mirror":qa["mirror"],"mirror_sha256":qa["mirror_sha256"],"base_package":qa.get("base_package_name"),"base_commit":qa.get("base_commit"),"registered_checkpoint":True,"push":"PASS" if not args.no_push else "SKIPPED","physical_solves_performed_by_submit":0},ensure_ascii=False,indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
